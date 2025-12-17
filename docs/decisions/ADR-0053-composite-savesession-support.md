# ADR-0053: Composite SaveSession Support

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-11
- **Deciders**: Architect
- **Related**: [TDD-0015](../architecture/business-model-tdd.md), [ADR-0035](ADR-0035-unit-of-work-pattern.md)

## Context

When a developer tracks a Business entity, should SaveSession automatically track its children (ContactHolder, UnitHolder, contacts, units, etc.)?

The existing DependencyGraph uses Kahn's algorithm to order saves based on `parent` field dependencies. The question is how entities get into the graph in the first place.

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Convenience | Automatic (less code) |
| Explicitness | Manual (clear intent) |
| Memory control | Manual (developer chooses scope) |
| Debug-ability | Manual (preview shows exactly what's tracked) |
| Common use case | Automatic (save business + contacts is common) |
| Surprise avoidance | Manual (no hidden side effects) |

### Options Considered

| Option | Behavior | Code Required | Memory Footprint |
|--------|----------|---------------|------------------|
| A: Manual | Track each entity explicitly | High | Developer-controlled |
| B: Automatic | `track(business)` tracks entire tree | Low | Potentially large |
| C: Optional flag | `track(business, recursive=True)` | Medium | Developer-controlled |

## Decision

**Provide optional recursive tracking via `track(entity, recursive=True)` flag, defaulting to `recursive=False`.**

### Implementation

```python
class SaveSession:
    def track(
        self,
        entity: T,
        recursive: bool = False,
        prefetch_holders: bool = True,
    ) -> T:
        """Track entity for change detection.

        Args:
            entity: AsanaResource to track
            recursive: If True, also track all children (subtasks).
                      For Business entities, tracks all holders and their
                      children recursively.
            prefetch_holders: If True and entity is Business, fetch holder
                             subtasks from API (requires async context).

        Returns:
            The tracked entity (for chaining)

        Example:
            # Track only the business
            session.track(business)

            # Track business and entire hierarchy
            session.track(business, recursive=True)

            # Track specific branch
            session.track(business)
            session.track(business.contact_holder, recursive=True)
        """
        self._tracker.track(entity)

        if recursive:
            self._track_recursive(entity)

        if prefetch_holders and isinstance(entity, Business):
            self._pending_prefetch.append(entity)

        return entity

    def _track_recursive(self, entity: Task) -> None:
        """Recursively track all children in the hierarchy."""
        # For entities with HOLDER_KEY_MAP (Business, Unit)
        if hasattr(entity, 'HOLDER_KEY_MAP'):
            for holder_name in entity.HOLDER_KEY_MAP:
                holder = getattr(entity, f'_{holder_name}', None)
                if holder is not None:
                    self._tracker.track(holder)
                    self._track_recursive(holder)

        # For holder entities with children list
        children = getattr(entity, '_children', [])
        for child in children:
            self._tracker.track(child)
            self._track_recursive(child)
```

### Usage Patterns

```python
# Pattern 1: Save entire business hierarchy
async with client.save_session() as session:
    session.track(business, recursive=True)
    business.company_id = "NEW123"
    contact = business.contacts[0]
    contact.full_name = "Jane Doe"
    result = await session.commit_async()
    # Both business and contact saved

# Pattern 2: Save only specific entities
async with client.save_session() as session:
    session.track(business)
    session.track(contact)
    business.company_id = "NEW123"
    contact.full_name = "Jane Doe"
    result = await session.commit_async()

# Pattern 3: Save business + contacts, not units
async with client.save_session() as session:
    session.track(business)
    session.track(business.contact_holder, recursive=True)
    # Units not tracked, won't be saved even if modified
```

## Rationale

### Why Optional Flag (Option C)?

1. **Explicit is better than implicit**: Python Zen principle. Auto-tracking could pull thousands of tasks into memory without developer awareness:
   ```python
   # With auto-tracking (dangerous)
   session.track(business)  # Silently tracks 500 units, 2000 processes
   ```

2. **Memory control**: Developer explicitly opts into large memory footprint:
   ```python
   # Developer consciously chooses to load full hierarchy
   session.track(business, recursive=True)  # Clear intent
   ```

3. **Debug-ability**: `session.preview()` shows exactly what will be saved:
   ```python
   ops, _ = session.preview()
   # With explicit tracking, this list is predictable
   ```

4. **DependencyGraph handles ordering**: Once entities are tracked (however they got there), the existing DependencyGraph ensures correct save order via Kahn's algorithm.

5. **Flexibility for common patterns**: Developers can:
   - Track only modified entities (minimal)
   - Track full hierarchy (comprehensive)
   - Track specific branches (balanced)

### Why Not Manual Only (Option A)?

Too verbose for the common case of "save this business and its modified contacts":
```python
# Would require this every time
session.track(business)
session.track(business.contact_holder)
for contact in business.contacts:
    session.track(contact)
session.track(business.unit_holder)
for unit in business.units:
    session.track(unit)
    # And nested holders...
```

### Why Not Automatic (Option B)?

Violates principle of least surprise:
```python
session.track(business)
# Developer thinks: "I'm tracking the business"
# Reality: 500 units and 2000 processes now in memory

unit = business.units[0]
unit.mrr = Decimal("0")  # Accidental change
await session.commit_async()  # Surprise! Unit saved too
```

Auto-tracking could cause:
- Unintended saves of accidentally-modified entities
- Memory exhaustion for large hierarchies
- Confusing error messages when unrelated entities fail

### Why Default to `recursive=False`?

Principle of least surprise. Tracking a single entity should track that entity:
```python
session.track(business)  # Tracks business only
session.track(business, recursive=True)  # Tracks hierarchy
```

Developers who want recursive tracking must opt in explicitly.

## Consequences

### Positive
- Explicit control over what's tracked and saved
- Works with existing DependencyGraph ordering
- Debug-friendly via `preview()`
- Flexible for different use cases
- Memory footprint controlled by developer

### Negative
- Extra parameter for common recursive case
- Developer must understand hierarchy to track correctly
- More verbose than automatic tracking

### Mitigation
- Document common patterns in SDK guide
- Provide `track_business(business)` convenience method that defaults to recursive
- Log warning if tracked entity has untracked modified children

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] `track()` defaults to `recursive=False`
   - [ ] Recursive tracking documented in docstring
   - [ ] No auto-tracking of children

2. **Unit tests**:
   ```python
   def test_track_default_not_recursive():
       """Default track only tracks the entity itself."""
       session.track(business)
       assert business in session._tracker._entities.values()
       assert business.contact_holder not in session._tracker._entities.values()

   def test_track_recursive_tracks_children():
       """recursive=True tracks entire hierarchy."""
       session.track(business, recursive=True)
       assert business in session._tracker._entities.values()
       assert business.contact_holder in session._tracker._entities.values()
       assert business.contacts[0] in session._tracker._entities.values()

   def test_preview_shows_tracked_only():
       """preview() only shows explicitly tracked entities."""
       session.track(business)
       business.company_id = "NEW"
       business.contacts[0].full_name = "Changed"  # Not tracked
       ops, _ = session.preview()
       assert len(ops) == 1  # Only business
   ```

3. **Documentation**:
   - [ ] "Tracking Hierarchies" section in SaveSession guide
   - [ ] Code examples for common patterns
   - [ ] Warning about untracked modified children
