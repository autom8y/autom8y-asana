# ADR-0078: GID-Based Entity Identity Strategy

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Author** | Architect |
| **Date** | 2025-12-16 |
| **Deciders** | Architect, Principal Engineer |
| **Related** | PRD-HARDENING-F, TDD-HARDENING-F, SPIKE-HARDENING-F |

---

## Context

The `ChangeTracker` class uses Python's `id()` function as the tracking key for entities:

```python
# Current implementation (tracker.py)
self._snapshots: dict[int, dict[str, Any]] = {}  # id(entity) -> snapshot
self._states: dict[int, EntityState] = {}        # id(entity) -> state
self._entities: dict[int, AsanaResource] = {}    # id(entity) -> entity
```

This creates a **critical bug** when the same Asana resource is fetched multiple times within a session:

```python
async with SaveSession(client) as session:
    task_a = await client.tasks.get_async("12345")
    task_b = await client.tasks.get_async("12345")  # Same GID, different Python object

    session.track(task_a)
    session.track(task_b)  # Tracked SEPARATELY due to id(task_a) != id(task_b)

    task_a.name = "Change A"
    task_b.notes = "Change B"

    await session.commit_async()
    # PROBLEM: Two UPDATE operations sent for same task
    # Race condition: one change is lost
```

**Impact**:
- Data loss through silent overwrite
- Duplicate API operations (wasted quota)
- Confusing error attribution
- Memory inefficiency (multiple snapshots for same entity)

The challenge is handling several edge cases:
1. **New entities** have `temp_*` prefixed GIDs until created
2. **GID-less entities** (edge case) have no GID at all
3. **GID transition** occurs when temp GID becomes real GID after CREATE

---

## Decision

**Replace `id(entity)` with GID-based registry, with fallback to `__id_{id(entity)}` for GID-less entities.**

### Key Generation Strategy

```python
def _get_key(self, entity: AsanaResource) -> str:
    """Generate tracking key for entity.

    Priority:
    1. Use entity's GID if it exists (works for real and temp_ GIDs)
    2. Fall back to f"__id_{id(entity)}" for truly GID-less entities
    """
    gid = getattr(entity, 'gid', None)
    if gid:
        return gid  # Works for both real GIDs and temp_ GIDs
    return f"__id_{id(entity)}"
```

### Data Structures

```python
class ChangeTracker:
    def __init__(self) -> None:
        # Primary storage: key -> entity reference
        self._entities: dict[str, AsanaResource] = {}
        # key -> snapshot at track time
        self._snapshots: dict[str, dict[str, Any]] = {}
        # key -> lifecycle state
        self._states: dict[str, EntityState] = {}
        # Maps temp_gid -> real_gid after creation
        self._gid_transitions: dict[str, str] = {}
        # Reverse lookup: id(entity) -> key
        self._entity_to_key: dict[int, str] = {}
```

### Duplicate Handling

When the same GID is tracked twice:
1. Update entity reference to the new object
2. Preserve original snapshot (tracks changes from first track)
3. Emit DEBUG log for observability

### GID Transition

When a temp GID becomes a real GID after successful CREATE:
1. Re-key all data structures from temp GID to real GID
2. Record the transition in `_gid_transitions` map
3. Allow lookup by either temp or real GID

---

## Rationale

### Why GID-based?

1. **Asana guarantees GID uniqueness** - GIDs are globally unique within Asana
2. **Matches domain semantics** - One Asana resource should be tracked once
3. **Enables deduplication** - Natural solution to the duplicate tracking bug
4. **Enables new capabilities** - `find_by_gid()` lookup becomes possible

### Why not pure GID (without fallback)?

Edge cases exist where entities might not have GIDs:
- Programmatically constructed entities before any API call
- Test doubles/mocks without GID assignment

The `__id_` prefix fallback handles these gracefully while keeping the primary path clean.

### Why `__id_` prefix (not bare id)?

Asana GIDs are numeric strings like `"1234567890"`. A bare `id()` value like `140123456789` could theoretically collide with a GID. The `__id_` prefix makes collision impossible.

---

## Alternatives Considered

### Alternative 1: Maintain `id()` with deduplication layer

- **Description**: Keep `id()` as key but add a separate `gid -> entity` index
- **Pros**: Minimal change to existing code
- **Cons**: Two sources of truth; complexity; harder to reason about
- **Why not chosen**: Introduces unnecessary complexity; GID is the natural key

### Alternative 2: Require unique GID on track()

- **Description**: Raise error if GID already tracked
- **Pros**: Explicit behavior; no silent merging
- **Cons**: Breaking change; forces users to check before tracking
- **Why not chosen**: Too disruptive; common pattern is track-then-check

### Alternative 3: Deep merge changes from duplicate tracks

- **Description**: When same GID tracked twice, merge all field changes
- **Pros**: All changes preserved regardless of which object they're on
- **Cons**: Complex merge logic; unclear precedence; potential conflicts
- **Why not chosen**: Over-engineering; update-reference approach is simpler and sufficient

---

## Consequences

### Positive

1. **Bug fixed**: Same Asana resource tracked once regardless of Python object count
2. **Data preserved**: Changes from multiple references are captured
3. **New capability**: `find_by_gid()` and `is_tracked()` methods enabled
4. **Performance maintained**: O(1) lookup preserved (dict access)
5. **Memory efficient**: Single snapshot per resource

### Negative

1. **Silent behavior change**: Users who relied on duplicate tracking might be surprised
   - *Mitigation*: DEBUG log on duplicate; CHANGELOG entry
2. **Snapshot from first track**: Changes to first object before second track might be captured unexpectedly
   - *Mitigation*: Document behavior; this is actually the correct semantics

### Neutral

1. Internal type change (`int` -> `str` keys) requires updating all internal methods
2. New `_gid_transitions` map adds minor memory overhead (bounded by session lifetime)
3. `_entity_to_key` reverse lookup adds minor memory overhead

---

## Compliance

### How to enforce this decision

1. **Code review**: Ensure all entity tracking uses GID-based keys
2. **Unit tests**: Test duplicate GID scenario explicitly
3. **Integration tests**: End-to-end test for duplicate fetch scenario

### Validation

- [ ] All `ChangeTracker` tests pass with string keys
- [ ] Duplicate GID test demonstrates single UPDATE
- [ ] Temp GID transition test passes
- [ ] Backward compatibility tests pass (existing test suite)
