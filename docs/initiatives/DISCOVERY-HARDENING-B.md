# Discovery Document: Architecture Hardening Initiative B - Custom Field Unification

**Initiative**: Architecture Hardening Sprint - Custom Field Unification
**Session**: Discovery
**Date**: 2025-12-16
**Author**: Requirements Analyst
**Scope**: Issues #2 (dual change tracking) and #10 (naming confusion) from Architecture Hardening Prompt -1

---

## Executive Summary

This discovery document audits the dual custom field change tracking systems to understand exactly how they work, where they interact, and where they conflict. The SDK currently has **two independent systems** for tracking custom field changes:

1. **System 1 (ChangeTracker)**: Snapshot-based dirty detection at entity level via `model_dump()` comparison
2. **System 2 (CustomFieldAccessor)**: Explicit dirty flag tracking via `_modifications` dict

These systems were designed for different purposes but create complexity at their intersection. The `Task.model_dump()` override attempts to reconcile them, but edge cases exist where behavior is surprising or conflicting.

**Key Findings**:
- Both systems track changes independently with no shared state
- `Task.model_dump()` reconciles conflicts by giving precedence to accessor changes
- A third mechanism exists: `Task._original_custom_fields` snapshot for direct list mutations
- Naming is confusing: `get_custom_fields()` returns accessor, `custom_fields` is the raw list
- Reset behavior after commit is incomplete - only accessor `_modifications` is cleared in `refresh_async()`
- ChangeTracker snapshot is updated via `mark_clean()`, but accessor snapshot (`_original_custom_fields`) is not

---

## System 1: Snapshot-Based Tracking (ChangeTracker)

### Location
`/src/autom8_asana/persistence/tracker.py`

### Mechanism
ChangeTracker captures a snapshot of the entire entity via `entity.model_dump()` at `track()` time. Dirty detection compares current state to snapshot:

```python
def _is_modified(self, entity: AsanaResource) -> bool:
    original = self._snapshots[entity_id]
    current = entity.model_dump()
    return original != current
```

### Lifecycle

| Phase | What Happens |
|-------|--------------|
| **Initialization** | `track(entity)` captures `entity.model_dump()` as snapshot |
| **Detection** | `get_dirty_entities()` compares current `model_dump()` to snapshot |
| **Commit** | `mark_clean(entity)` updates snapshot to current `model_dump()` |
| **Reset** | `untrack(entity)` removes entity from tracking |

### Custom Field Behavior
Since `Task.model_dump()` is overridden to include accessor changes, the snapshot comparison **does** detect custom field changes made via accessor. However:
- Initial snapshot captures the raw `custom_fields` list format
- After accessor changes, `model_dump()` returns API dict format
- Comparison always shows "different" even if semantically identical

### Key Methods

| Method | Purpose |
|--------|---------|
| `track(entity)` | Capture initial snapshot |
| `get_state(entity)` | Returns CLEAN, MODIFIED, NEW, or DELETED |
| `get_changes(entity)` | Returns `{field: (old, new)}` for all changed fields |
| `get_changed_fields(entity)` | Returns `{field: new_value}` for API payload |
| `mark_clean(entity)` | Update snapshot, set state to CLEAN |

---

## System 2: Dirty Flag Tracking (CustomFieldAccessor)

### Location
`/src/autom8_asana/models/custom_field_accessor.py`

### Mechanism
CustomFieldAccessor maintains an explicit `_modifications` dict that records every change:

```python
def set(self, name_or_gid: str, value: Any) -> None:
    gid = self._resolve_gid(name_or_gid)
    self._modifications[gid] = value

def has_changes(self) -> bool:
    return len(self._modifications) > 0
```

### Lifecycle

| Phase | What Happens |
|-------|--------------|
| **Initialization** | `Task.get_custom_fields()` creates accessor with task's `custom_fields` |
| **Modification** | `set()/remove()` adds entry to `_modifications` |
| **Detection** | `has_changes()` checks if `_modifications` is non-empty |
| **Serialization** | `to_api_dict()` returns `{gid: value}` for modified fields only |
| **Reset** | `clear_changes()` empties `_modifications` |

### Key Methods

| Method | Purpose |
|--------|---------|
| `get(name)` | Returns value (from modifications or original data) |
| `set(name, value)` | Adds to `_modifications`, marks dirty |
| `remove(name)` | Sets `_modifications[gid] = None` |
| `has_changes()` | True if any modifications pending |
| `to_api_dict()` | Converts modifications to API format |
| `clear_changes()` | Empties `_modifications` dict |

---

## System 3: Direct Modification Detection (Task Snapshot)

### Location
`/src/autom8_asana/models/task.py` (lines 127-220)

### Mechanism
Per ADR-0067/TDD-TRIAGE-FIXES: A third system exists specifically to detect **direct mutations** to the `custom_fields` list (bypassing the accessor):

```python
# Captured at Task initialization via model_validator
_original_custom_fields: list[dict[str, Any]] | None = PrivateAttr(default=None)

def _has_direct_custom_field_changes(self) -> bool:
    return self.custom_fields != self._original_custom_fields
```

### Purpose
Users might directly modify `task.custom_fields[0]["text_value"] = "new"` instead of using the accessor. This system ensures such changes are not lost.

### Lifecycle

| Phase | What Happens |
|-------|--------------|
| **Initialization** | `model_validator` captures `deepcopy(custom_fields)` |
| **Detection** | `_has_direct_custom_field_changes()` compares to snapshot |
| **Serialization** | `_convert_direct_changes_to_api()` generates API payload |
| **Reset** | **NOT IMPLEMENTED** - snapshot is never updated post-commit |

---

## Interaction Point Analysis

### 1. Initial Load (API Response -> Task)

```
API Response
    |
    v
Task.model_validate(response)
    |
    +--> custom_fields = [...list from API...]
    +--> _original_custom_fields = deepcopy(custom_fields)  [System 3]
    +--> _custom_fields_accessor = None (lazy)              [System 2]
    |
SaveSession.track(task)
    |
    +--> ChangeTracker captures model_dump()                [System 1]
```

**Key Observation**: At this point, all three systems have independent snapshots. No synchronization between them.

### 2. Modification via Accessor

```
task.get_custom_fields().set("Priority", "High")
    |
    +--> Creates accessor if None (lazy init)
    +--> Adds {"gid": "High"} to _modifications          [System 2]
    |
    +--> task.custom_fields UNCHANGED                    [System 3 sees no change]
    +--> ChangeTracker snapshot UNCHANGED                [System 1 sees change at model_dump() time]
```

**Key Observation**: Only System 2 is immediately aware of the change. System 1 will detect it when `model_dump()` is called.

### 3. Modification via Direct List Access

```
task.custom_fields[0]["text_value"] = "New Value"
    |
    +--> _modifications UNCHANGED                        [System 2 unaware]
    +--> _original_custom_fields UNCHANGED               [System 3 will detect at compare time]
    +--> ChangeTracker snapshot UNCHANGED                [System 1 will detect at model_dump() time]
```

**Key Observation**: System 2 (accessor) is completely unaware of this change. Systems 1 and 3 will detect it.

### 4. Dirty Detection at Commit Time

```
SaveSession.commit_async()
    |
    +--> ChangeTracker.get_dirty_entities()
           |
           +--> For each tracked entity:
                  entity.model_dump()                    [Triggers Task override]
                  compare to snapshot
    |
    +--> Task.model_dump()
           |
           +--> accessor_changes = accessor.has_changes()   [System 2]
           +--> direct_changes = _has_direct_custom_field_changes()  [System 3]
           |
           +--> if accessor_changes AND direct_changes:
                  LOG WARNING, use accessor (precedence)
           +--> elif accessor_changes:
                  return accessor.to_api_dict()
           +--> elif direct_changes:
                  return _convert_direct_changes_to_api()
```

**Key Observation**: `Task.model_dump()` reconciles the three systems with explicit precedence rules.

### 5. Reset After Successful Commit

```
SaveSession.commit_async() SUCCESS
    |
    +--> ChangeTracker.mark_clean(entity)
           |
           +--> _snapshots[entity_id] = entity.model_dump()  [System 1 reset]
           +--> _states[entity_id] = CLEAN
    |
    +--> accessor._modifications is NOT cleared              [System 2 NOT reset]
    +--> _original_custom_fields is NOT updated              [System 3 NOT reset]
```

**CRITICAL BUG**: After commit, Systems 2 and 3 retain their "dirty" state. This means:
- `accessor.has_changes()` will still return `True` after commit
- `_has_direct_custom_field_changes()` will still return `True` after commit
- Only the ChangeTracker snapshot is updated

### 6. Reset via `refresh_async()`

```
task.refresh_async()
    |
    +--> Fetch fresh data from API
    +--> Update all fields
    +--> accessor._modifications.clear()                 [System 2 reset]
    |
    +--> _original_custom_fields is NOT updated          [System 3 NOT reset]
    +--> ChangeTracker snapshot is NOT updated           [System 1 NOT reset]
```

**Key Observation**: `refresh_async()` only partially resets state. System 3 snapshot is never updated.

---

## Conflict Scenarios

### Scenario 1: Accessor + Direct Modification (Same Field)

```python
task = await client.tasks.get(gid)
task.custom_fields[0]["text_value"] = "Direct"  # System 3 detects
task.get_custom_fields().set("Priority", "Accessor")  # System 2 detects

result = task.model_dump()
# Accessor wins per ADR-0067, warning logged
# Result: {"custom_fields": {"456": "Accessor"}}  # Direct change lost!
```

**Impact**: User data loss if they mix modification patterns.

### Scenario 2: Track After Modification

```python
task = await client.tasks.get(gid)
task.get_custom_fields().set("Priority", "High")  # Before tracking!

with SaveSession(client) as session:
    session.track(task)  # Snapshot captures modified state
    # ...
    result = await session.commit_async()  # No changes detected!
```

**Impact**: Changes made before `track()` are invisible to ChangeTracker because the snapshot already includes them.

### Scenario 3: Re-Commit Same Entity

```python
with SaveSession(client) as session:
    session.track(task)
    task.get_custom_fields().set("Priority", "High")
    await session.commit_async()  # Succeeds

    # Second commit of same entity
    await session.commit_async()  # accessor.has_changes() STILL TRUE!
```

**Impact**: Repeated API calls because accessor `_modifications` is not cleared.

### Scenario 4: Multiple Sessions, Same Entity

```python
task = await client.tasks.get(gid)

# Session 1
with SaveSession(client) as s1:
    s1.track(task)
    task.get_custom_fields().set("Priority", "High")
    await s1.commit_async()  # Succeeds

# Session 2 - same task object
with SaveSession(client) as s2:
    s2.track(task)  # Fresh snapshot
    # accessor._modifications still has "Priority": "High"
    # Will try to commit again!
```

**Impact**: Duplicate commits across sessions.

---

## Naming Audit

### Issue #10: Naming Confusion

| Name | Type | Returns | Confusion Level |
|------|------|---------|-----------------|
| `task.custom_fields` | Property | `list[dict]` - raw API format | Low |
| `task.get_custom_fields()` | Method | `CustomFieldAccessor` | **HIGH** |
| `accessor.get(name)` | Method | Field value (any type) | Medium |
| `accessor.set(name, value)` | Method | None (mutates) | Low |
| `accessor.to_api_dict()` | Method | `dict[str, Any]` - API format | Low |
| `accessor.to_list()` | Method | `list[dict]` - merged format | Medium |
| `accessor._modifications` | Private attr | `dict[str, Any]` - changes only | Low |
| `accessor._data` | Private attr | `list[dict]` - copy of original | Low |

### Primary Confusion Points

1. **`get_custom_fields()` sounds like a getter, but returns an accessor object**
   - Expected: Returns the custom fields list
   - Actual: Returns `CustomFieldAccessor` for fluent API
   - User confusion: "Why can't I iterate over `get_custom_fields()`?"

2. **`custom_fields` vs `get_custom_fields()` semantic difference**
   - `custom_fields` - Read-only access to raw data
   - `get_custom_fields()` - Read-write access via accessor
   - No indication which to use when

3. **`to_list()` vs `to_api_dict()` format confusion**
   - `to_list()` returns `[{gid, value}, ...]` format
   - `to_api_dict()` returns `{gid: value, ...}` format
   - API actually wants `to_api_dict()` format (per ADR-0056)

### Business Layer Naming

The business layer consistently uses `get_custom_fields()` for both reading and writing:

```python
# Reading
value = self.get_custom_fields().get(self.Fields.PRIORITY)

# Writing
self.get_custom_fields().set(self.Fields.PRIORITY, value)
```

This is the **correct pattern** per SDK design, but the method name doesn't suggest it.

---

## Edge Case Catalog

### Edge Case 1: Setting Field to Current Value

```python
# Field already has value "High"
accessor.set("Priority", "High")  # Sets _modifications even though no change

# Result: has_changes() returns True, unnecessary API call
```

**Impact**: Performance - unnecessary API calls for no-op changes.

### Edge Case 2: Multiple Changes to Same Field

```python
accessor.set("Priority", "Low")
accessor.set("Priority", "Medium")
accessor.set("Priority", "High")

# Only "High" is sent (correct behavior)
# _modifications[gid] = "High"
```

**Impact**: None - last value wins, correct behavior.

### Edge Case 3: Null/Empty Handling

```python
# Setting to None
accessor.set("Priority", None)  # _modifications[gid] = None
accessor.remove("Priority")      # _modifications[gid] = None

# Both produce same API payload: {"gid": None}
```

**Impact**: None - consistent behavior.

### Edge Case 4: Type Coercion

```python
# Number field
accessor.set("MRR", Decimal("1000.50"))
# Stored as Decimal in _modifications
# Converted to float in _format_value_for_api()

# Enum field
accessor.set("Status", {"gid": "123", "name": "Done"})
# Stored as dict in _modifications
# Converted to "123" (GID only) in _format_value_for_api()
```

**Impact**: Potential precision loss for Decimal. Users may be surprised by conversion.

### Edge Case 5: Accessor Created Before Custom Fields Set

```python
task = Task(gid="123")  # custom_fields = None
accessor = task.get_custom_fields()  # _data = []
task.custom_fields = [{"gid": "456", ...}]  # Set later

# accessor._data is still empty!
# accessor won't find "456" in name index
```

**Impact**: Accessor and task out of sync if custom_fields set after accessor creation.

### Edge Case 6: Case-Insensitive Name Lookup

```python
accessor.set("PRIORITY", "High")    # Resolves to GID
accessor.set("priority", "Medium")  # Same GID!
accessor.set("Priority", "Low")     # Same GID!

# Only one entry in _modifications: {resolved_gid: "Low"}
```

**Impact**: Correct behavior - case normalization works as expected.

---

## Recommendation: Authoritative System

### Current State
There is no single authoritative system. `Task.model_dump()` performs ad-hoc reconciliation with precedence rules.

### Recommendation

**Make CustomFieldAccessor (`_modifications`) the authoritative system** for custom field changes.

Rationale:
1. Accessor is the intended public API for custom field modifications
2. Direct list mutation is discouraged (legacy pattern)
3. Accessor has explicit change tracking with clear semantics
4. ChangeTracker should delegate to accessor for custom fields

### Proposed Changes

1. **Unify reset behavior**: When `mark_clean()` is called, also:
   - Clear `accessor._modifications`
   - Update `Task._original_custom_fields` snapshot

2. **Eliminate System 3**: Remove `_original_custom_fields` snapshot tracking. Instead:
   - Document that direct list mutation is unsupported
   - Or, update accessor when list is mutated (complex)

3. **Rename `get_custom_fields()`**: Consider `custom_field_accessor()` or property `cf`

4. **Add value comparison in `set()`**: Skip modification if value equals current
   ```python
   def set(self, name_or_gid: str, value: Any) -> None:
       if self.get(name_or_gid) == value:
           return  # No-op, don't mark dirty
       self._modifications[gid] = value
   ```

---

## Open Questions for PRD

1. **Backward Compatibility**: If we deprecate direct list mutation, what is the migration path for existing code?

2. **Performance**: Should `set()` compare values to avoid no-op changes, or is the overhead not worth it?

3. **Accessor Lifecycle**: Should accessor be invalidated when `custom_fields` is re-assigned? Currently they can drift.

4. **Naming Decision**: What should `get_custom_fields()` be renamed to?
   - Option A: `custom_field_accessor()` (explicit)
   - Option B: `cf` property (short but obscure)
   - Option C: Keep as-is with better documentation

5. **Reset Behavior**: Should `commit()` automatically clear accessor modifications, or require explicit `clear_changes()`?

6. **Type Coercion**: Should Decimal precision be preserved (send as string) or continue converting to float?

---

## Appendix: Files Audited

### Core Files

| File | Purpose |
|------|---------|
| `/src/autom8_asana/models/task.py` | Task model with custom field handling |
| `/src/autom8_asana/models/custom_field_accessor.py` | CustomFieldAccessor class |
| `/src/autom8_asana/persistence/tracker.py` | ChangeTracker snapshot comparison |
| `/src/autom8_asana/persistence/session.py` | SaveSession integration |
| `/src/autom8_asana/persistence/pipeline.py` | Save pipeline with change detection |

### Test Files

| File | Purpose |
|------|---------|
| `/tests/unit/models/test_custom_field_accessor.py` | Accessor unit tests |
| `/tests/unit/models/test_task_custom_fields.py` | Task custom field integration tests |

### Business Layer Files (Using Accessor)

| File | Usage Pattern |
|------|---------------|
| `/src/autom8_asana/models/business/contact.py` | Property getters/setters via accessor |
| `/src/autom8_asana/models/business/unit.py` | Property getters/setters via accessor |
| `/src/autom8_asana/models/business/business.py` | Property getters/setters via accessor |
| `/src/autom8_asana/models/business/offer.py` | Property getters/setters via accessor |
| `/src/autom8_asana/models/business/process.py` | Property getters/setters via accessor |
| `/src/autom8_asana/models/business/location.py` | Property getters/setters via accessor |
| `/src/autom8_asana/models/business/hours.py` | Property getters/setters via accessor |
| `/src/autom8_asana/models/business/asset_edit.py` | Property getters/setters via accessor |

---

## Summary

The dual (actually triple) change tracking system works but has edge cases:

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| Accessor not cleared after commit | High | Fix reset behavior |
| Direct mutation snapshot not cleared | Medium | Deprecate or unify |
| Naming confusion (`get_custom_fields()`) | Medium | Rename or document |
| No-op changes marked dirty | Low | Add value comparison |
| Accessor/list can drift | Low | Document or invalidate |

**Next Steps**:
1. Create PRD-HARDENING-B.md with requirements based on this analysis
2. Prioritize reset behavior fix (highest impact)
3. Decide on naming changes (breaking change consideration)
4. Create ADR for authoritative system decision
