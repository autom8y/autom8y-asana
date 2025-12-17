# Root Cause Analysis Report: SDK Demo Bug Fix Sprint

**Initiative**: SDK Demo Bug Fix Sprint
**Session**: 1 of 7 - Discovery
**Role**: Requirements Analyst
**Date**: 2025-12-12

---

## Executive Summary

Investigation of 4 critical bugs in the SDK Demonstration Suite reveals:

| Bug | Root Cause | Severity | Fix Scope |
|-----|-----------|----------|-----------|
| **BUG-1** | Action results not merged into SaveResult | Critical | `pipeline.py` |
| **BUG-2** | Custom fields use wrong API format (array vs dict) | Critical | `custom_field_accessor.py` |
| **BUG-3** | `subtasks_async()` method does not exist | Critical | `clients/tasks.py` |
| **BUG-4** | Demo displays GIDs instead of human-readable names | Low | `_demo_utils.py` |

**Key Finding**: BUG-1 and BUG-2 are **SDK bugs** that affect all users. BUG-3 is a **missing feature**. BUG-4 is a **demo script presentation issue** only.

---

## BUG-1: Dependency/Dependent Operations Show `SaveResult(succeeded=0, failed=0)`

### Symptom
When using `session.add_dependency()` or `session.add_dependent()`, the SaveResult shows `succeeded=0, failed=0` even though operations may have executed.

### Root Cause Location
**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/pipeline.py`
**Lines**: 546-593

### Root Cause Analysis

The `execute_with_actions()` method returns a tuple `(crud_result, action_results)`:

```python
# pipeline.py line 546-593
async def execute_with_actions(
    self,
    entities: list[AsanaResource],
    actions: list[ActionOperation],
) -> tuple[SaveResult, list[ActionResult]]:
    """Execute CRUD operations and actions together."""
    # ... CRUD execution ...
    crud_result = await self._execute_crud(entities)

    # ... Action execution ...
    action_results = await self._action_executor.execute(actions)

    return crud_result, action_results  # Actions NOT merged into result!
```

However, in `session.py` `commit_async()` (lines 520-553), only `crud_result` is returned:

```python
# session.py line 526-553
crud_result, action_results = await self._pipeline.execute_with_actions(...)
# ... logging ...
return crud_result  # action_results DISCARDED!
```

**The action_results are computed but never merged into the SaveResult.**

### Code Path Trace

1. `session.add_dependency(task, dependency)` - Registers action in session
2. `session.commit_async()` - Calls pipeline
3. `pipeline.execute_with_actions()` - Executes actions, returns `(crud_result, action_results)`
4. `session.commit_async()` returns ONLY `crud_result` - **action_results lost**

### Expected vs. Actual Behavior

| Aspect | Expected | Actual |
|--------|----------|--------|
| SaveResult.succeeded | Includes action successes | Only CRUD successes |
| SaveResult.failed | Includes action failures | Only CRUD failures |
| Action execution | Visible in result | Silent execution |

### Recommended Fix Scope

**Minimal**: Merge action results into SaveResult before returning:
```python
# In session.py commit_async()
crud_result, action_results = await self._pipeline.execute_with_actions(...)
# Count action successes/failures
action_succeeded = sum(1 for r in action_results if r.success)
action_failed = sum(1 for r in action_results if not r.success)
# Merge into result
crud_result.succeeded += action_succeeded
crud_result.failed += action_failed
return crud_result
```

**Design Decision for Architect**: Should SaveResult have separate `action_succeeded`/`action_failed` counts, or merge with CRUD counts?

---

## BUG-2: Custom Field Writes Fail with `SaveResult(succeeded=0, failed=1)`

### Symptom
All custom field modifications fail when committed through SaveSession. BatchClient reports 0/1 succeeded.

### Root Cause Location
**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`
**Method**: `to_list()` (lines 97-125)

### Root Cause Analysis

The `to_list()` method produces an **array** format:
```python
def to_list(self) -> list[dict[str, Any]]:
    """Convert to API payload format."""
    result: list[dict[str, Any]] = []
    # ...
    result.append({"gid": gid, "value": self._modifications[gid]})
    # ...
    return result
```

This produces:
```json
[
  {"gid": "4578152156", "value": "High"},
  {"gid": "5678904321", "value": 1000}
]
```

**But Asana API expects a dict with GID keys:**
```json
{
  "custom_fields": {
    "4578152156": "High",
    "5678904321": 1000
  }
}
```

### Asana API Documentation Reference

From [Asana API - Custom Fields](https://developers.asana.com/reference/custom-fields):
> Custom fields should be an object where each key is a Custom Field gid and each value is an enum gid, string, or number.

### Code Path Trace

1. `task.get_custom_fields().set("Priority", "High")` - Stores modification
2. `task.model_dump()` calls `to_list()` - Produces array format
3. Pipeline builds payload with `task.model_dump()` - Includes wrong format
4. BatchClient sends to API - **Asana rejects as invalid**

### Expected vs. Actual Behavior

| Aspect | Expected (Asana API) | Actual (SDK) |
|--------|----------------------|--------------|
| Format | `{"gid": value}` dict | `[{"gid": ..., "value": ...}]` array |
| Key | GID string | Object with "gid" key |
| Value location | Direct value | Nested under "value" key |

### Recommended Fix Scope

**Rename/Replace Method**: Create `to_api_dict()` method:
```python
def to_api_dict(self) -> dict[str, Any]:
    """Convert to Asana API format: {gid: value, ...}"""
    result = {}
    for gid, value in self._modifications.items():
        result[gid] = value
    return result
```

**Update Task.model_dump()**: Use new method for API payload:
```python
if self._custom_fields_accessor.has_changes():
    data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
```

**Design Decision for Architect**: Should `to_list()` be deprecated or kept for other uses? How to handle unchanged fields (include or omit)?

---

## BUG-3: `AttributeError: 'TasksClient' object has no attribute 'subtasks_async'`

### Symptom
Demo script fails with AttributeError when trying to fetch subtasks:
```python
iterator = client.tasks.subtasks_async(parent_gid)
# AttributeError: 'TasksClient' object has no attribute 'subtasks_async'
```

### Root Cause Location
**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
**Issue**: Method does not exist

### Root Cause Analysis

The `TasksClient` class has `list_async()` which accepts a `parent` parameter:
```python
# tasks.py line 421-481
def list_async(
    self,
    project: str | None = None,
    section: str | None = None,
    workspace: str | None = None,
    assignee: str | None = None,
    # ... other filters ...
) -> PageIterator[Task]:
```

However, there is **no dedicated `subtasks_async()` method**. The demo script (and business model code) expects:
```python
client.tasks.subtasks_async(parent_gid)  # Does not exist!
```

### Pattern Comparison

Other clients have dedicated list methods for related resources:

| Client | Method | Exists |
|--------|--------|--------|
| `TagsClient` | `list_for_task_async()` | Yes |
| `AttachmentsClient` | `list_for_task_async()` | Yes |
| `StoriesClient` | `list_for_task_async()` | Yes |
| `SectionsClient` | `list_for_project_async()` | Yes |
| `TasksClient` | `subtasks_async()` | **NO** |

### Expected Asana API Endpoint

The Asana API provides: `GET /tasks/{task_gid}/subtasks`

From Asana API documentation, this endpoint returns subtasks of a task.

### Recommended Fix Scope

**Add Method**: Create `subtasks_async()` following existing patterns:
```python
def subtasks_async(
    self,
    task_gid: str,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Task]:
    """Get subtasks of a task.

    Args:
        task_gid: Parent task GID.
        opt_fields: Fields to include in response.
        limit: Maximum results per page.

    Returns:
        PageIterator[Task] - async iterator over subtasks.
    """
    self._log_operation("subtasks_async", task_gid)

    async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
        params = {"limit": min(limit, 100)}
        if opt_fields:
            params["opt_fields"] = ",".join(opt_fields)
        if offset:
            params["offset"] = offset

        response = await self._http.get(
            f"/tasks/{task_gid}/subtasks",
            params=params,
        )
        # ... parse response, return tasks and next_offset ...

    return PageIterator(fetch_page, page_size=min(limit, 100))
```

---

## BUG-4: People Field Shows GIDs, Multi-Enum Shows String Instead of List

### Symptom
When displaying people custom field values, the demo shows raw GIDs like `['1203504488912318']` instead of user names like `['John Smith']`.

### Root Cause Location
**File**: `/Users/tomtenuta/Code/autom8_asana/scripts/_demo_utils.py`
**Method**: `find_custom_field_by_type()` (lines 950-952)

### Root Cause Analysis

The `find_custom_field_by_type()` function correctly extracts GIDs for internal use:
```python
# _demo_utils.py line 950-952
elif field_type == "people":
    people_vals = cf.get("people_value") or []
    current_value = [p.get("gid") for p in people_vals if p.get("gid")]
```

The demo script then displays this directly:
```python
# demo_sdk_operations.py line 809
logger.info(f"Original value (user GIDs): {original_value}")
```

**This is a display/presentation issue in the demo script, not an SDK bug.**

The `CustomFieldAccessor._extract_value()` method (lines 182-183) returns the full people data:
```python
if "people_value" in field and field["people_value"]:
    return field["people_value"]  # Returns full list with names
```

So the SDK accessor returns `[{"gid": "123", "name": "John Smith"}, ...]` but the demo utility extracts only GIDs for state tracking.

### Expected vs. Actual Behavior

| Aspect | Expected | Actual |
|--------|----------|--------|
| SDK `_extract_value()` | Returns full people data | Works correctly |
| Demo state capture | Stores GIDs for restoration | Works correctly |
| Demo display | Show human-readable names | Shows GIDs only |

### Assessment

**This is NOT an SDK bug.** The SDK returns correct data. The demo script's `find_custom_field_by_type()` extracts GIDs for state management (which is correct), but the demo should additionally extract names for display purposes.

### Recommended Fix Scope

**Demo Script Enhancement** (not SDK fix):
```python
# In _demo_utils.py, add display_names to CustomFieldInfo
@dataclass
class CustomFieldInfo:
    # ... existing fields ...
    people_names: list[str] = field(default_factory=list)  # Add this

# In find_custom_field_by_type()
elif field_type == "people":
    people_vals = cf.get("people_value") or []
    current_value = [p.get("gid") for p in people_vals if p.get("gid")]
    # Add: capture names for display
    people_names = [p.get("name") for p in people_vals if p.get("name")]
```

---

## Regression Risk Assessment

### Working Operations That Must Remain Safe

| Operation | Risk Level | Notes |
|-----------|------------|-------|
| `session.add_tag()` | Low | BUG-1 fix should not affect |
| `session.remove_tag()` | Low | Uses same action executor |
| `session.move_to_section()` | Low | Uses same action executor |
| CRUD create/update/delete | Low | Separate code path |
| `list_async()` pagination | None | Unrelated to bugs |
| Model validation | None | Unrelated to bugs |

### Regression Test Coverage Needed

1. **For BUG-1 fix**: Test that existing CRUD results still work, action counts are correct
2. **For BUG-2 fix**: Test all custom field types (text, number, enum, multi_enum, people, date)
3. **For BUG-3 fix**: Test that new method follows existing patterns, doesn't break `list_async(parent=...)`

---

## Open Questions for Architect

### BUG-1 Design Decisions

1. **Should SaveResult have separate action counts?**
   - Option A: Single `succeeded`/`failed` counts (merge CRUD + actions)
   - Option B: Add `action_succeeded`/`action_failed` fields
   - Option C: Add nested `ActionResult` list to SaveResult

2. **Should action failures stop the commit?**
   - Current: CRUD and actions execute independently
   - Alternative: Fail entire commit if any action fails

### BUG-2 Design Decisions

1. **Should `to_list()` be renamed or deprecated?**
   - It produces wrong format for API but may be used elsewhere

2. **How to handle unchanged custom fields?**
   - Option A: Only send modified fields (current behavior intent)
   - Option B: Send all fields to ensure consistency

3. **What about field type-specific formatting?**
   - Enum fields need GID, not name
   - Multi-enum needs array of GIDs
   - People needs array of GIDs
   - Should `to_api_dict()` handle these transformations?

### BUG-3 Design Decisions

1. **Method naming convention?**
   - `subtasks_async()` (matches demo expectation)
   - `list_subtasks_async()` (matches `list_async` pattern)
   - `get_subtasks_async()` (matches business model expectation in docs)

2. **Should this deprecate `list_async(parent=...)`?**
   - Having both adds flexibility but potential confusion

---

## Summary Table

| Bug | Confirmed Root Cause | File:Line | Fix Complexity |
|-----|---------------------|-----------|----------------|
| BUG-1 | Action results discarded | `session.py:526-553` | Medium |
| BUG-2 | Wrong custom field format | `custom_field_accessor.py:97-125` | Medium |
| BUG-3 | Missing method | `clients/tasks.py` (add new) | Low |
| BUG-4 | Demo display issue | `_demo_utils.py:950-952` | Low |

---

## References

### Asana API Documentation
- [Custom Fields](https://developers.asana.com/reference/custom-fields) - Expected format for custom field updates
- [Update Task](https://developers.asana.com/reference/updatetask) - Task update payload structure
- [Get Subtasks](https://developers.asana.com/reference/getsubtasksfortask) - Subtasks endpoint

### SDK Source Files Analyzed
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/pipeline.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
- `/Users/tomtenuta/Code/autom8_asana/scripts/_demo_utils.py`
- `/Users/tomtenuta/Code/autom8_asana/scripts/demo_sdk_operations.py`
