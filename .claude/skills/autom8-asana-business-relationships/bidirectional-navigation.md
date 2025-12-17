# Bidirectional Navigation

> Navigating up and down the business hierarchy (ADR-0052)

---

## Decision Summary

**Cache upward references with explicit invalidation on hierarchy changes.**

Benefits:
- O(1) access for common navigation patterns
- Predictable performance in loops
- Session-scoped validity (stable within SaveSession)

---

## Navigation Directions

### Downward (Parent to Children)

Via holder properties and shortcuts:

```python
# Full path
business.contact_holder.contacts

# Shortcut
business.contacts

# Iteration
for contact in business.contacts:
    print(contact.full_name)
```

### Upward (Child to Parent)

Via cached reference properties:

```python
# Contact to holder
contact.contact_holder  # ContactHolder

# Contact to root
contact.business       # Business

# Chain navigation
unit.business.contacts  # All contacts in same business
```

---

## Cached Reference Pattern

Children cache their upward references:

```python
from pydantic import PrivateAttr

class Contact(Task):
    """Contact with cached parent references."""

    # Cached references (not serialized)
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    @property
    def business(self) -> Business | None:
        """Navigate to containing Business (cached)."""
        if self._business is None:
            self._business = self._resolve_business()
        return self._business

    @property
    def contact_holder(self) -> ContactHolder | None:
        """Navigate to immediate parent holder (cached)."""
        if self._contact_holder is None and self.parent:
            # Immediate parent is the holder
            self._contact_holder = self.parent
        return self._contact_holder
```

---

## Resolution Logic

Walk up the tree to find Business root:

```python
def _resolve_business(self) -> Business | None:
    """Walk up the parent chain to find Business."""
    current = self.parent
    while current is not None:
        # Check if we've reached Business
        if isinstance(current, Business):
            return current

        # Handle NameGid references (partial object)
        if hasattr(current, 'gid') and not hasattr(current, 'parent'):
            # Can't navigate further with partial ref
            break

        # Move up
        current = getattr(current, 'parent', None)

    return None
```

---

## Invalidation

Cached references invalidated when hierarchy changes:

```python
def _invalidate_refs(self) -> None:
    """Invalidate all cached references."""
    self._business = None
    self._contact_holder = None

def set_parent(self, new_parent: Task | NameGid | None) -> None:
    """Override to invalidate refs on parent change."""
    super().set_parent(new_parent)
    self._invalidate_refs()
```

### Invalidation Triggers

1. `set_parent()` called on entity
2. Entity moved to different holder
3. Session closed (entities shouldn't be reused)

---

## Performance Comparison

Without caching (O(n) per access):
```python
# 1000 contacts, depth 2 = 2000 parent lookups
for contact in contacts:
    _ = contact.business  # Walks up each time
```

With caching (O(1) per access):
```python
# 1000 contacts = 1000 cache hits after first resolution
for contact in contacts:
    _ = contact.business  # Returns cached ref
```

---

## Cross-Navigation

Navigate between siblings via common parent:

```python
# Get all contacts in same business as this unit
def get_sibling_contacts(unit: Unit) -> list[Contact]:
    """Get contacts in the same Business as this Unit."""
    business = unit.business
    if business is None:
        return []
    return business.contacts

# Example usage
unit = business.units[0]
contacts = get_sibling_contacts(unit)
```

---

## Session-Scoped Validity

References are valid within a SaveSession:

```python
async with client.save_session() as session:
    session.track(business)

    # References stable throughout session
    contact = business.contacts[0]
    assert contact.business is business  # Always true

    # Modifications tracked
    contact.full_name = "Updated"
    await session.commit_async()

# After session, refs may become stale
# Don't reuse entities across sessions
```

---

## Avoiding Stale References

### Do:
```python
# Fetch fresh within each session
async with client.save_session() as session:
    business = await fetch_business(client, gid)
    session.track(business)
    # Work with fresh data
```

### Don't:
```python
# Anti-pattern: reusing entities across sessions
business = await fetch_business(client, gid)

async with client.save_session() as session1:
    session1.track(business)
    await session1.commit_async()

async with client.save_session() as session2:
    # BAD: business may have stale refs
    session2.track(business)
```

---

## Refresh Method

Force re-resolution of cached references:

```python
def refresh_refs(self) -> None:
    """Force re-resolution of all references."""
    self._invalidate_refs()
    # Next access will re-resolve
    _ = self.business  # Triggers fresh resolution
    _ = self.contact_holder
```

---

## Related

- [holder-pattern.md](holder-pattern.md) - Downward navigation structure
- [lazy-loading.md](lazy-loading.md) - When references become available
- [composite-pattern.md](composite-pattern.md) - Nested holder navigation
