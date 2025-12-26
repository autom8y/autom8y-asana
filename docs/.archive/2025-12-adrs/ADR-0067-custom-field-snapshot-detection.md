# ADR-0067: Custom Field Snapshot Detection Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: Architect, Principal Engineer
- **Related**: TDD-TRIAGE-FIXES, ADR-0056 (Custom Field API Format), ADR-0030 (Custom Field Typing)

## Context

Issue 14 from the QA Adversarial Review identified that `Task.model_dump()` silently loses direct modifications to `task.custom_fields`. The current implementation only checks `_custom_fields_accessor.has_changes()`, missing direct list modifications.

### Current Behavior (BUG)

```python
# User modifies custom_fields directly
task.custom_fields[0]["text_value"] = "New Value"

# model_dump() doesn't detect this
data = task.model_dump()
# custom_fields is original, not modified!
```

### Why This Happens

1. `model_dump()` only checks accessor for changes (line 158-162)
2. Accessor is created lazily - only if `get_custom_fields()` is called
3. Direct list modifications bypass the accessor entirely
4. No comparison to original state

### Two Modification Paths

```
Path A: Via Accessor (Detected)          Path B: Direct (NOT Detected)
------------------------                  ---------------------------
task.get_custom_fields().set(...)        task.custom_fields[0][...] = ...
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

### Forces at Play

1. **User expectation**: Both modification paths should work
2. **Performance**: Don't add overhead to every Task instantiation
3. **Accessor precedence**: When both paths used, accessor should win (explicit API)
4. **Pydantic integration**: Must work with model validation lifecycle
5. **Deep vs shallow**: List contains dicts; shallow copy won't detect nested changes

## Decision

**Capture a deep copy snapshot of `custom_fields` at Task initialization using `model_validator`.** Compare current state to snapshot in `model_dump()` to detect direct modifications.

### Snapshot Strategy

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
```

### Detection Logic

```python
def _has_direct_custom_field_changes(self) -> bool:
    """Check if custom_fields was modified directly."""
    if self._original_custom_fields is None:
        return self.custom_fields is not None and len(self.custom_fields) > 0

    if self.custom_fields is None:
        return True

    return self.custom_fields != self._original_custom_fields
```

### model_dump() Integration

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

### Precedence Decision

**Accessor changes take precedence over direct changes.** Rationale:

1. **Explicit API**: Using `get_custom_fields().set()` is intentional
2. **Conflict resolution**: Clear rule for overlapping changes
3. **Logging**: Warning alerts user to potential issue
4. **Recoverable**: User can inspect both if needed

## Rationale

### Why Deep Copy (Not Shallow)?

```python
# Original custom_fields
[{"gid": "123", "text_value": "Original"}]

# Shallow copy
shallow = list(self.custom_fields)
# shallow[0] is SAME dict object

# User modifies
self.custom_fields[0]["text_value"] = "Modified"
# shallow[0]["text_value"] is also "Modified"!

# Deep copy
deep = copy.deepcopy(self.custom_fields)
# deep[0] is NEW dict object
# Modification doesn't affect deep copy
```

Deep copy is required because the list contains mutable dicts.

### Why model_validator (Not __init__)?

Pydantic v2 `model_validator(mode="after")` runs after all field validation:

1. **All fields populated**: `custom_fields` is guaranteed to exist
2. **Pydantic-native**: Uses recommended pattern
3. **Works with model_validate**: Captures snapshot for both direct construction and `.model_validate()`

### Why Not Track Changes in custom_fields Setter?

Pydantic models don't have custom setters for fields. We'd need:
- `__setattr__` override (complex, affects all fields)
- Custom field type (over-engineering)
- Proxy object wrapping list (adds indirection)

Snapshot comparison is simpler and sufficient.

### Why Log Warning on Conflict (Not Error)?

1. **Non-fatal**: Both sets of changes are valid, just need to pick one
2. **User awareness**: Warning helps debugging
3. **Forward progress**: Operation completes, doesn't block

## Alternatives Considered

### Alternative A: Proxy Object for custom_fields

**Description**: Wrap `custom_fields` in a change-tracking proxy list

**Pros**:
- Real-time tracking of all modifications
- No comparison needed

**Cons**:
- Complex proxy implementation
- Affects all list operations
- May break JSON serialization

**Why not chosen**: Over-engineering for this use case

### Alternative B: Hash-Based Change Detection

**Description**: Store hash of original, compare hashes

**Pros**:
- More efficient for large lists
- No storage of full copy

**Cons**:
- Dicts aren't directly hashable
- Must serialize to compute hash
- Hash collision (unlikely but possible)

**Why not chosen**: Deep copy is simpler and reliable

### Alternative C: Track Only Specific Value Keys

**Description**: Snapshot only `text_value`, `number_value`, etc.

**Pros**:
- Smaller snapshot
- Faster comparison

**Cons**:
- Must maintain list of value keys
- New field types would need updates
- May miss structural changes

**Why not chosen**: Full snapshot is more robust

### Alternative D: Disable Direct Modification

**Description**: Make `custom_fields` property read-only, force accessor use

**Pros**:
- No ambiguity
- Clear API

**Cons**:
- Major breaking change
- Users expect list mutability
- Against Pydantic model conventions

**Why not chosen**: Too disruptive; detection is less invasive

## Consequences

### Positive

1. **Direct modifications work**: Users can modify list directly
2. **No data loss**: Both modification paths persist changes
3. **Clear precedence**: Accessor wins when both used
4. **Debuggable**: Warning on conflict helps users understand

### Negative

1. **Memory overhead**: Deep copy of custom_fields list
2. **Comparison cost**: List comparison on every model_dump
3. **Behavioral change**: Previously ignored, now persisted

### Performance Analysis

Typical `custom_fields` list:
- 10-50 custom field objects
- Each object: ~10 key-value pairs
- Deep copy: ~1KB memory, microseconds to copy
- Comparison: O(n * m) where n=fields, m=keys

This overhead is negligible compared to HTTP round-trips.

## Edge Cases

### Empty custom_fields

```python
task = Task(gid="123", custom_fields=[])
```

- Snapshot: `[]`
- Comparison: `[] != []` is False
- Result: No false positive

### None custom_fields

```python
task = Task(gid="123")  # custom_fields defaults to None
```

- Snapshot: `None`
- If user sets to list: `None != [...]` is True
- Result: Change detected correctly

### Replaced List

```python
task.custom_fields = [{"gid": "new", "text_value": "X"}]
```

- Original snapshot unchanged
- New list != original
- Result: Change detected

## Test Verification

1. `test_direct_modification_detected`: Modify list item, `_has_direct_custom_field_changes()` returns True
2. `test_no_modification_no_change`: No changes, returns False
3. `test_snapshot_is_deep_copy`: Modifying list doesn't affect snapshot
4. `test_accessor_takes_precedence`: Both modified, accessor output used
5. `test_warning_logged_on_conflict`: Both modified, warning logged
6. `test_direct_changes_in_model_dump`: Direct changes appear in output
7. `test_none_to_list_detected`: Setting None to list is detected
8. `test_empty_list_no_false_positive`: Empty list unchanged is not a change

## Compliance

### Enforcement

- **Unit tests**: Cover all modification patterns
- **Integration test**: End-to-end save with direct modifications
- **Type checking**: mypy validates snapshot type

### Documentation

- Update Task docstring to explain both modification paths
- Add example showing accessor vs direct modification
- Document precedence behavior
