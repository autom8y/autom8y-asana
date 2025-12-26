# ADR-0008: Custom Field API Format and Change Tracking

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0056, ADR-0067, ADR-0074
- **Related**: reference/CUSTOM-FIELDS.md

## Context

Custom fields require correct API payload formatting and comprehensive change detection across multiple modification paths. The SDK must handle:

1. **API format conversion**: Asana API expects `{gid: value}` dict, not array of objects
2. **Multiple modification paths**: Via CustomFieldAccessor OR direct list mutation
3. **Change tracking coordination**: Three independent systems must reset after successful commit

### The API Format Problem

`CustomFieldAccessor.to_list()` produced format incompatible with Asana API:

```python
# to_list() produces (WRONG):
[{"gid": "123456", "value": "High"}, {"gid": "789012", "value": 1000}]

# API requires:
{"custom_fields": {"123456": "High", "789012": 1000}}
```

Type-specific value requirements:

| Field Type | API Value Format | Example |
|------------|-----------------|---------|
| Text | string | `"High Priority"` |
| Number | number | `1000.50` |
| Enum | option GID string | `"1234567890"` |
| Multi-enum | array of option GIDs | `["111", "222"]` |
| People | array of user GIDs | `["333", "444"]` |
| Date | date object | `{"date": "2024-12-31"}` |

### The Change Detection Problem

Two modification paths exist:

```
Path A: Via Accessor (Detected)          Path B: Direct (NOT Detected)
------------------------                  ---------------------------
task.get_custom_fields().set(...)        task.custom_fields[0]["text_value"] = ...
    |                                        |
    v                                        v
accessor._modifications[gid] = value     list item mutated in place
    |                                        |
    v                                        v
model_dump() checks has_changes()        model_dump() sees no accessor changes
    |                                        |
    v                                        v
Changes serialized correctly             CHANGES LOST (BUG)
```

### The Reset Coordination Problem

Three independent systems track custom field changes:

| System | Mechanism | Location | Reset After Commit? |
|--------|-----------|----------|---------------------|
| **System 1** | ChangeTracker snapshot comparison | `persistence/tracker.py` | Yes (via `mark_clean()`) |
| **System 2** | CustomFieldAccessor `_modifications` dict | `models/custom_field_accessor.py` | **NO** (BUG) |
| **System 3** | Task `_original_custom_fields` deepcopy | `models/task.py` | **NO** (BUG) |

After successful `SaveSession.commit_async()`, Systems 2 and 3 retained state, causing duplicate API calls and cross-session pollution.

## Decision

**Implement three complementary mechanisms:**

1. **API Format Conversion**: Add `to_api_dict()` method to CustomFieldAccessor
2. **Snapshot Change Detection**: Capture deep copy at initialization to detect direct mutations
3. **Unified Reset Coordination**: SaveSession coordinates reset across all three systems after successful commit

### 1. API Format Conversion

Add new `to_api_dict()` method that produces correct API format. Keep `to_list()` unchanged for backward compatibility.

```python
def to_api_dict(self) -> dict[str, Any]:
    """Convert modifications to API-compatible dict format.

    Per ADR-0008: Asana API expects custom_fields as a dict mapping
    field GID to value, not an array of objects.

    Returns:
        Dict of {field_gid: value} for API payload.

    Example:
        >>> accessor.set("Priority", "High")  # GID: 123456
        >>> accessor.set("MRR", 1000)         # GID: 789012
        >>> accessor.to_api_dict()
        {"123456": "High", "789012": 1000}
    """
    result: dict[str, Any] = {}
    for gid, value in self._modifications.items():
        result[gid] = self._normalize_value_for_api(value)
    return result

def _normalize_value_for_api(self, value: Any) -> Any:
    """Normalize a value for API submission.

    Handles type-specific value formatting:
    - Enum: Extract GID from {"gid": "...", "name": "..."} dict
    - Multi-enum/People: Extract GIDs from list of dicts
    - Text/number/date: Return as-is
    """
    if value is None:
        return None

    # Enum values: if dict with 'gid', extract the GID
    if isinstance(value, dict) and "gid" in value:
        return value["gid"]

    # Multi-enum/People: if list of dicts with 'gid', extract GIDs
    if isinstance(value, list):
        if all(isinstance(item, dict) and "gid" in item for item in value):
            return [item["gid"] for item in value]
        return value

    # Text, number, date: return as-is
    return value
```

Update `Task.model_dump()` to use `to_api_dict()`:

```python
data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
```

### 2. Snapshot Change Detection

Capture deep copy snapshot at Task initialization to detect direct mutations:

```python
class Task(AsanaResource):
    # Private snapshot for direct modification detection
    _original_custom_fields: list[dict[str, Any]] | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _capture_custom_fields_snapshot(self) -> "Task":
        """Capture snapshot at initialization."""
        if self.custom_fields is not None:
            self._original_custom_fields = copy.deepcopy(self.custom_fields)
        return self

    def _has_direct_custom_field_changes(self) -> bool:
        """Check if custom_fields was modified directly."""
        if self._original_custom_fields is None:
            return self.custom_fields is not None and len(self.custom_fields) > 0

        if self.custom_fields is None:
            return True

        return self.custom_fields != self._original_custom_fields
```

### 3. Unified Reset Coordination

**CustomFieldAccessor is the authoritative system for change tracking**. SaveSession coordinates reset across all three systems after successful commit.

Add reset method to Task:

```python
def reset_custom_field_tracking(self) -> None:
    """Reset custom field change tracking after successful commit.

    Clears both accessor modifications and updates the snapshot.
    Called by SaveSession after successful entity commit.
    """
    if self._custom_fields_accessor is not None:
        self._custom_fields_accessor._modifications.clear()

    if self.custom_fields is not None:
        self._original_custom_fields = copy.deepcopy(self.custom_fields)
    else:
        self._original_custom_fields = None
```

SaveSession calls reset after successful commit:

```python
async def _commit_entity(self, entity: AsanaResource) -> None:
    """Commit single entity and reset change tracking on success."""
    # Execute commit
    await self._execute_commit(entity)

    # Reset all three systems
    self._tracker.mark_clean(entity)  # System 1
    if isinstance(entity, Task):
        entity.reset_custom_field_tracking()  # Systems 2 and 3
```

### Precedence When Both Paths Modified

When both accessor and direct modifications occur:

```python
def model_dump(self, **kwargs: Any) -> dict[str, Any]:
    data = super().model_dump(**kwargs)

    accessor_changes = (
        self._custom_fields_accessor is not None
        and self._custom_fields_accessor.has_changes()
    )
    direct_changes = self._has_direct_custom_field_changes()

    if accessor_changes and direct_changes:
        # Both modified - accessor takes precedence, log warning
        logger.warning("Both accessor and direct modifications; using accessor")
        data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
    elif accessor_changes:
        data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
    elif direct_changes:
        data["custom_fields"] = self._convert_direct_changes_to_api()

    return data
```

**Accessor precedence rationale**:
1. Explicit API: Using `get_custom_fields().set()` is intentional
2. Conflict resolution: Clear rule for overlapping changes
3. Logging: Warning alerts user to potential issue
4. Recoverable: User can inspect both if needed

## Rationale

### Why to_api_dict() Instead of Modifying to_list()?

| Approach | Pros | Cons |
|----------|------|------|
| Modify `to_list()` | Single method | Breaking change; name becomes misleading |
| Add format parameter | Single method with flexibility | Awkward API; harder to type hint |
| Convert in pipeline | No accessor changes | Wrong layer; duplicated logic |
| **New `to_api_dict()` method** | Clean separation; backward compatible | Two methods to maintain |

**Decision**: Separate methods for reading (`to_list()`) vs writing (`to_api_dict()`) provide clear intent without breaking existing code.

### Why Deep Copy for Snapshot?

```python
# Shallow copy FAILS
shallow = list(self.custom_fields)
# shallow[0] is SAME dict object
self.custom_fields[0]["text_value"] = "Modified"
# shallow[0]["text_value"] is also "Modified"!

# Deep copy WORKS
deep = copy.deepcopy(self.custom_fields)
# deep[0] is NEW dict object
# Modification doesn't affect deep copy
```

Deep copy is required because the list contains mutable dicts.

### Why model_validator (Not __init__)?

Pydantic v2 `model_validator(mode="after")` runs after all field validation:
1. All fields populated: `custom_fields` is guaranteed to exist
2. Pydantic-native: Uses recommended pattern
3. Works with model_validate: Captures snapshot for both construction methods

### Why SaveSession Coordinates Reset?

| Option | Pros | Cons |
|--------|------|------|
| ChangeTracker.mark_clean() | Centralized | Generic system becomes Task-aware |
| Task.model_dump() side effect | No SaveSession changes | Side effects in serialization are surprising |
| **SaveSession._commit_entity()** | Clear ownership; success-aware | Requires SaveSession to know about Task |

**Decision**: SaveSession owns coordination because:
- Already calls `mark_clean()` for System 1
- Knows success/failure state
- Encapsulation via Task method minimizes coupling

## Alternatives Considered

### Alternative 1: Proxy Object for custom_fields

**Description**: Wrap `custom_fields` in a change-tracking proxy list

**Pros**:
- Real-time tracking of all modifications
- No comparison needed

**Cons**:
- Complex proxy implementation
- Affects all list operations
- May break JSON serialization
- Over-engineering

**Why not chosen**: Snapshot comparison is simpler and sufficient.

### Alternative 2: Hash-Based Change Detection

**Description**: Store hash of original, compare hashes

**Pros**:
- More efficient for large lists
- No storage of full copy

**Cons**:
- Dicts aren't directly hashable
- Must serialize to compute hash
- Hash collision risk

**Why not chosen**: Deep copy is simpler and reliable.

### Alternative 3: Disable Direct Modification

**Description**: Make `custom_fields` property read-only

**Pros**:
- No ambiguity
- Clear API

**Cons**:
- Major breaking change
- Users expect list mutability
- Against Pydantic conventions

**Why not chosen**: Too disruptive; detection is less invasive.

### Alternative 4: Make ChangeTracker Custom-Field-Aware

**Description**: Modify ChangeTracker to call accessor reset in `mark_clean()`

**Pros**:
- Centralized change tracking

**Cons**:
- Violates single responsibility
- ChangeTracker becomes Task-aware
- Complicates future entity types

**Why not chosen**: ChangeTracker should remain generic.

### Alternative 5: Event-Based Reset

**Description**: CustomFieldAccessor subscribes to SaveSession events

**Pros**:
- Decoupled

**Cons**:
- Complex wiring
- Accessor needs SaveSession reference
- Event ordering issues

**Why not chosen**: Over-engineered; simple method call is sufficient.

## Consequences

### Positive

1. **Correct API format**: Custom field updates work correctly
2. **Both modification paths work**: No data loss via direct mutation
3. **No duplicate API calls**: Re-commit detects no changes
4. **Cross-session clean state**: Entity tracked in new session has no stale modifications
5. **Partial failure safety**: Failed entities retain modifications for retry
6. **Clear precedence**: Accessor wins when both paths used
7. **Backward compatible**: `to_list()` unchanged for existing callers
8. **Type-aware formatting**: Handles enum GID extraction automatically

### Negative

1. **Memory overhead**: Deep copy of custom_fields list
2. **Comparison cost**: List comparison on every model_dump
3. **SaveSession-Task coupling**: SaveSession must know to call Task-specific method
4. **API surface increase**: New public methods on Task and CustomFieldAccessor
5. **isinstance check**: SaveSession needs `isinstance(entity, Task)` check

### Neutral

1. **Performance**: Deep copy overhead (~1KB memory, microseconds) negligible compared to HTTP
2. **Only modifications sent**: `to_api_dict()` only includes modified fields (correct for minimal payloads)
3. **Behavioral change**: Direct modifications previously ignored, now persisted
4. **System 3 remains**: Direct mutation detection still works; reset is coordinated

## Compliance

### How This Decision Is Enforced

1. **Unit tests**:
   - [ ] `to_api_dict()` output format for all field types
   - [ ] Direct modification detected via snapshot comparison
   - [ ] Accessor takes precedence when both modified
   - [ ] Accessor cleared after successful commit
   - [ ] Snapshot updated after successful commit
   - [ ] Warning logged on conflict

2. **Integration tests**:
   - [ ] Demo script successfully updates custom fields
   - [ ] No duplicate API calls on re-commit
   - [ ] Cross-session clean state verified
   - [ ] Direct changes appear in model_dump output

3. **Type checking**:
   - [ ] mypy validates `to_api_dict()` return type `dict[str, Any]`
   - [ ] Snapshot type validated

4. **Code review checklist**:
   - [ ] Use `to_api_dict()` for API payloads, `to_list()` for display
   - [ ] Don't modify `to_list()` return type
   - [ ] Reset method called after successful commit only
   - [ ] Deep copy used for snapshot (not shallow)

5. **Documentation**:
   - [ ] Explain when to use `to_api_dict()` vs `to_list()`
   - [ ] Document both modification paths
   - [ ] Document precedence behavior
   - [ ] Explain reset coordination across three systems
