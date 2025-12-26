# ADR-0052: Bidirectional Reference Caching

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-11
- **Deciders**: Architect
- **Related**: [TDD-0015](../architecture/business-model-tdd.md)

## Context

Business model entities need bidirectional navigation:
- **Downward**: `business.contact_holder.contacts` (parent to children)
- **Upward**: `contact.business`, `contact.contact_holder` (child to parent)

Upward navigation requires resolving parent references, which could be implemented via caching or computation.

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Access speed | Caching (O(1)) |
| Memory efficiency | Compute (no storage) |
| Reference freshness | Compute (always current) |
| Loop performance | Caching (avoid repeated walks) |
| GC behavior | Weak refs or compute |
| Session-scoped validity | Caching (refs stable within session) |

### Options Considered

| Option | Approach | Access Time | Memory | Freshness |
|--------|----------|-------------|--------|-----------|
| A: Cache upward refs | Store `_business`, `_contact_holder` | O(1) | 8 bytes/ref | Stale possible |
| B: Compute on access | Walk `parent.parent` chain | O(depth) | None | Always fresh |
| C: Weak references | `weakref.ref()` to parents | O(1) | ~40 bytes/ref | GC dependent |

## Decision

**Cache upward references with explicit invalidation on hierarchy changes.**

### Implementation

```python
from pydantic import PrivateAttr

class Contact(Task):
    """Contact entity with cached upward references."""

    # Private cached references (not serialized)
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: Task | None = PrivateAttr(default=None)

    @property
    def business(self) -> Business | None:
        """Navigate to containing Business (cached)."""
        if self._business is None:
            self._business = self._resolve_business()
        return self._business

    @property
    def contact_holder(self) -> Task | None:
        """Navigate to containing ContactHolder (cached)."""
        if self._contact_holder is None and self.parent:
            # Immediate parent is ContactHolder
            self._contact_holder = self.parent
        return self._contact_holder

    def _resolve_business(self) -> Business | None:
        """Walk up the tree to find Business root."""
        current = self.parent
        while current is not None:
            if isinstance(current, Business):
                return current
            # Handle NameGid parent reference
            if hasattr(current, 'gid') and not hasattr(current, 'parent'):
                break  # Can't navigate further without full object
            current = getattr(current, 'parent', None)
        return None

    def _invalidate_refs(self) -> None:
        """Invalidate cached references (call on hierarchy change)."""
        self._business = None
        self._contact_holder = None
```

### Invalidation Points

References are invalidated when:
1. `set_parent()` is called on the entity
2. Entity is moved to a different holder
3. Session is closed (entities should not be reused across sessions)

```python
def set_parent(self, new_parent: Task | NameGid | None) -> None:
    """Set parent with reference invalidation."""
    super().set_parent(new_parent)
    self._invalidate_refs()
```

## Rationale

### Why Caching (Option A)?

1. **Common access pattern**: Upward navigation is frequent in business logic:
   ```python
   for contact in contacts:
       print(f"{contact.full_name} at {contact.business.name}")
   ```
   Without caching, this walks the tree N times.

2. **Session-scoped validity**: Within a SaveSession, the hierarchy is stable. References only become stale if:
   - Entity is used across sessions (documented antipattern)
   - Hierarchy is modified without using SDK methods

3. **Memory is cheap**: A reference is 8 bytes on 64-bit Python:
   - 1000 contacts = 8 KB for business refs
   - 1000 contacts = 8 KB for contact_holder refs
   - Total: 16 KB - trivial

4. **Explicit invalidation is predictable**: Developers can reason about when refs update:
   - After `set_parent()` - refs invalidated
   - After `track()` with prefetch - refs populated
   - Within session - refs stable

### Why Not Compute on Access (Option B)?

For loops over large collections, O(depth) per access is wasteful:

```python
# With caching: O(n) total
for contact in contacts:  # n contacts
    _ = contact.business  # O(1) cached

# Without caching: O(n * d) total
for contact in contacts:  # n contacts
    _ = contact.business  # O(d) walk, d = tree depth
```

For 1000 contacts with depth 3, that's 3000 parent lookups vs 1000.

### Why Not Weak References (Option C)?

`weakref.ref()` adds complexity without benefit:

1. **GC unpredictability**: A weakref can become invalid mid-operation if the referent has no strong references:
   ```python
   business = contact.business  # Returns Business
   del all_businesses_list      # Strong refs gone
   gc.collect()                 # GC runs
   _ = contact.business         # Could return None!
   ```

2. **API confusion**: `weakref.ref()` returns a callable, not the object:
   ```python
   # With weakref
   business = contact._business()  # Must call to dereference
   if business is None:
       # Reference was GC'd - now what?
   ```

3. **Memory savings minimal**: `weakref.ref` is ~40 bytes per reference (PyObject overhead), vs 8 bytes for a direct reference. Actually costs more memory.

## Consequences

### Positive
- O(1) upward navigation
- Predictable performance in loops
- Simple implementation with PrivateAttr
- Session-scoped stability is well-defined

### Negative
- Stale references possible if hierarchy modified outside SDK methods
- Developer must understand session-scoped validity
- Must call `_invalidate_refs()` on all hierarchy changes

### Mitigation
- Document that navigation properties assume session-scoped consistency
- Provide `refresh()` method to force re-resolution
- Add warning in `_resolve_business()` if resolution fails unexpectedly

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] Upward navigation uses cached PrivateAttr
   - [ ] `set_parent()` calls `_invalidate_refs()`
   - [ ] No `weakref` usage for parent references

2. **Unit tests**:
   ```python
   def test_cached_navigation():
       """Second access returns cached reference."""
       contact = create_contact_in_hierarchy()
       business1 = contact.business
       business2 = contact.business
       assert business1 is business2  # Same object

   def test_invalidation_on_reparent():
       """set_parent invalidates cached refs."""
       contact = create_contact_in_hierarchy()
       old_business = contact.business
       contact.set_parent(new_holder)
       new_business = contact.business
       assert new_business is not old_business

   def test_navigation_performance():
       """Cached navigation is O(1)."""
       contacts = [create_contact() for _ in range(1000)]
       start = time.perf_counter()
       for c in contacts:
           _ = c.business
       elapsed = time.perf_counter() - start
       assert elapsed < 0.01  # Should be very fast
   ```

3. **Documentation**:
   - [ ] Document session-scoped validity in property docstrings
   - [ ] Add "Hierarchy Navigation" section to SDK guide
   - [ ] Warn against reusing entities across sessions
