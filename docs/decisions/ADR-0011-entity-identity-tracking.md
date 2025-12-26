# ADR-0011: Entity Identity and Tracking

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0006, ADR-0049, ADR-0078
- **Related**: reference/DATA-MODEL.md

## Context

The SDK needs to track Asana entities across API operations and maintain identity semantics. Three critical identity challenges emerged:

1. **Reference Representation**: Asana API returns lightweight resource references (assignee, followers, projects) as `{gid, name, resource_type}` dicts
2. **Entity Tracking**: The same Asana resource fetched multiple times creates separate Python objects, leading to duplicate tracking and race conditions in SaveSession
3. **GID Validation**: Invalid GIDs cause confusing errors deep in the API call stack or create cache key collisions

Without proper identity handling:
```python
async with SaveSession(client) as session:
    task_a = await client.tasks.get_async("12345")
    task_b = await client.tasks.get_async("12345")  # Same GID, different Python object

    session.track(task_a)
    session.track(task_b)  # Tracked SEPARATELY due to id(task_a) != id(task_b)

    task_a.name = "Change A"
    task_b.notes = "Change B"

    await session.commit_async()
    # PROBLEM: Two UPDATE operations sent for same task, race condition
```

## Decision

Implement GID-based entity identity with three components:

1. **NameGid as standalone frozen model** for lightweight references
2. **GID-based tracking** instead of Python object identity
3. **GID format validation** at track() time

### NameGid Model

```python
class NameGid(BaseModel):
    model_config = ConfigDict(
        frozen=True,     # Immutable
        extra="ignore",  # Forward compatibility
    )

    gid: str
    name: str | None = None
    resource_type: str | None = None

    def __hash__(self) -> int:
        return hash(self.gid)  # Equality by GID only

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NameGid):
            return self.gid == other.gid
        return NotImplemented
```

### GID-Based Tracking

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

### GID Validation

```python
GID_PATTERN = re.compile(r"^(temp_\d+|\d+)$")

def _validate_gid_format(self, gid: str | None) -> None:
    """Validate GID format at track() time.

    Valid GIDs:
    - "1234567890" (numeric Asana GID)
    - "temp_1" (temporary GID for new entity)
    - None (new entity, GID assigned by API)

    Invalid GIDs:
    - "" (empty string)
    - "not-a-gid" (non-numeric)
    - "12345abc" (alphanumeric mix)
    """
    if gid is None:
        return  # New entities have no GID
    if gid == "":
        raise ValidationError("GID cannot be empty string. Use None for new entities.")
    if not GID_PATTERN.match(gid):
        raise ValidationError(
            f"Invalid GID format: {gid!r}. "
            f"GID must be a numeric string or temp_<number> for new entities."
        )
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

## Rationale

### Why NameGid as Standalone Frozen Model?

**Semantic difference**: A NameGid is a *reference* to a resource, not a *resource* itself.

| Property | NameGid | AsanaResource |
|----------|---------|---------------|
| Inheritance | None (standalone) | BaseModel |
| Frozen | True | False |
| Hashable | Yes (enables sets/dict keys) | No |
| Equality | Based on gid | Based on all fields |
| Purpose | Immutable identifier | Mutable resource |

**Benefits of frozen:**
```python
# Deduplicate followers across multiple tasks
all_followers = {f for task in tasks for f in task.followers or []}

# Use as dict keys
user_task_count = {task.assignee: 0 for task in tasks if task.assignee}
```

**Identity by GID enables correct deduplication:**
```python
ref1 = NameGid(gid="123", name="Alice")
ref2 = NameGid(gid="123")  # Same resource, no name
assert ref1 == ref2
assert {ref1, ref2} == {ref1}  # Deduplicates correctly
```

### Why GID-Based Tracking?

1. **Asana guarantees GID uniqueness** - GIDs are globally unique within Asana
2. **Matches domain semantics** - One Asana resource should be tracked once
3. **Enables deduplication** - Natural solution to duplicate tracking bug
4. **Enables new capabilities** - `find_by_gid()` lookup becomes possible
5. **Bug fixed**: Same Asana resource tracked once regardless of Python object count

### Why Validate at track() Time?

1. **Earliest Entry Point**: track() is where entities enter the persistence layer
2. **Single Location**: Centralized validation in one place
3. **Fail-Fast**: User sees error immediately, not after queuing operations
4. **Before Side Effects**: No actions queued for invalid entities

### Why Allow temp_\d+ Pattern?

The SDK uses temporary GIDs for dependency resolution:
```python
new_task = Task(name="New Task", gid=None)
session.track(new_task)
# Internally assigned: gid = "temp_1"
# After API create: gid = "1234567890"
```

Pattern `temp_\d+` matches these internal assignments while preventing injection attacks.

## Alternatives Considered

### Alternative 1: NameGid Inherits from AsanaResource

- **Description**: `class NameGid(AsanaResource): ...`
- **Pros**: Shared config; consistent inheritance hierarchy
- **Cons**: Wrong semantics (reference vs resource); AsanaResource is mutable; would need to override frozen behavior
- **Why not chosen**: Semantic mismatch - NameGid is not a resource

### Alternative 2: Keep as dict[str, Any]

- **Description**: Continue using untyped dicts for references
- **Pros**: No code changes; maximum flexibility; no validation overhead
- **Cons**: No type safety; no IDE support; defensive coding required; doesn't satisfy requirements
- **Why not chosen**: Typed model is explicitly required for type safety

### Alternative 3: Maintain id() with Deduplication Layer

- **Description**: Keep `id()` as key but add separate `gid -> entity` index
- **Pros**: Minimal change to existing code
- **Cons**: Two sources of truth; complexity; harder to reason about
- **Why not chosen**: Introduces unnecessary complexity; GID is the natural key

### Alternative 4: Stricter Pattern (Numeric Only)

- **Description**: Only allow `^\d+$`, reject temp GIDs
- **Pros**: Simpler pattern
- **Cons**: Breaks internal temp GID mechanism; user must handle new entity GIDs differently
- **Why not chosen**: temp GIDs are essential for dependency resolution

### Alternative 5: No Validation (Current State)

- **Description**: Accept any string, let API reject invalid
- **Pros**: Zero overhead; flexibility
- **Cons**: Confusing errors deep in stack; hash collisions possible; injection risk; empty string causes KeyError
- **Why not chosen**: Fails-late with unclear errors

## Consequences

### Positive

- **Type safety**: IDE autocomplete, type checking for reference fields
- **Cleaner API**: `task.assignee.gid` instead of `task.assignee["gid"]`
- **Deduplication**: Can use sets for unique references
- **Dict keys**: Can index by reference
- **Validation**: Pydantic validates reference structure
- **Forward compatible**: Unknown fields in API response are ignored
- **Bug fixed**: Same Asana resource tracked once regardless of Python object count
- **Data preserved**: Changes from multiple references are captured
- **New capability**: `find_by_gid()` and `is_tracked()` methods enabled
- **Performance maintained**: O(1) lookup preserved (dict access)
- **Memory efficient**: Single snapshot per resource
- **Fail-fast on invalid GIDs**: Clear error messages with fix guidance
- **Injection prevention**: Regex validation blocks malicious inputs

### Negative

- **Breaking change**: Code using dict access (`task.assignee["gid"]`) must update to attribute access
- **Migration effort**: Update all Task field accesses in autom8
- **Slightly more memory**: NameGid object vs dict (negligible)
- **Silent behavior change**: Users who relied on duplicate tracking might be surprised (DEBUG log mitigates)
- **Small performance overhead**: GID validation at track() time
- **Could reject future Asana GID formats**: Mitigated by regex update capability

### Neutral

- **Serialization unchanged**: `model_dump()` produces dict, same as before
- **Comparison semantics clear**: Equality by gid is documented and expected
- **Internal type change**: `int` -> `str` keys requires updating all internal methods
- **New `_gid_transitions` map**: Minor memory overhead bounded by session lifetime
- **None remains valid**: For new entities without assigned GIDs
- **Pattern matches current format**: Asana's current GID format

## Compliance

### Model Validation

1. **Type checking**: mypy enforces NameGid type on reference fields
2. **Code review**: Reject new `dict[str, Any]` for simple resource references
3. **Documentation**: Docstrings explain NameGid usage
4. **Migration guide**: Document dict-to-attribute access changes
5. **Tests**: Verify hashing, equality, and Pydantic integration

### Tracking Validation

1. **Code review**: Ensure all entity tracking uses GID-based keys
2. **Unit tests**: Test duplicate GID scenario explicitly
3. **Integration tests**: End-to-end test for duplicate fetch scenario
4. **All ChangeTracker tests pass**: With string keys
5. **Backward compatibility tests pass**: Existing test suite

### GID Validation

1. **Implementation**: Validation in `ChangeTracker.track()`
2. **Testing**: Unit tests for all valid/invalid patterns
3. **Boundary Tests**: Empty string, None, temp GIDs, injection attempts
4. **Error Messages**: Include format hint in ValidationError
5. **Documentation**: Document valid GID formats in limitations.md
