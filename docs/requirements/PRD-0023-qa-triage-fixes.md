# QA Findings Triage & Fix - Requirements Specification

**Initiative**: QA Findings Triage & Fix
**Version**: 1.0
**Date**: 2024-12-12
**Author**: Requirements Analyst
**Status**: READY FOR ARCHITECT REVIEW

---

## Executive Summary

This document provides detailed, implementable specifications for 5 critical/high severity issues identified in the QA Adversarial Review. Each issue includes confirmed root cause with code evidence, fix approach, acceptance criteria, and test plan.

**Decisions Locked In**:
- Cascade feature: OPTION B - Implement (not delete)
- model_dump() fix: Detect + merge direct modifications
- Failed actions: Keep in pending + return in result

---

## ISSUE 11: Cascade Operations Not Executed

### Summary

`SaveSession.cascade_field()` exists and queues cascade operations in `_cascade_operations`, but the cascade operations are never executed during `commit_async()`. The `commit_async()` method calls `_pipeline.execute_with_actions()` which handles CRUD and action operations, but cascades are never passed to the pipeline or a cascade executor. This renders the entire cascade feature non-functional.

### Root Cause

- **File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
- **Lines**: 1610-1684 (cascade methods), 547-578 (commit_async)
- **Code evidence** (cascade_field queues but never executes):

```python
# Lines 1648-1661: cascade_field() queues operations
def cascade_field(
    self,
    entity: T,
    field_name: str,
    *,
    target_types: tuple[type, ...] | None = None,
) -> SaveSession:
    # ...
    op = CascadeOperation(
        source_entity=entity,
        field_name=field_name,
        target_types=target_types,
    )

    # Store cascade operations for execution at commit time
    if not hasattr(self, "_cascade_operations"):
        self._cascade_operations: list[CascadeOperation] = []
    self._cascade_operations.append(op)  # <-- Queued here
    # ...
    return self
```

```python
# Lines 547-555: commit_async() NEVER touches _cascade_operations
async def commit_async(self) -> SaveResult:
    # ...
    # Execute CRUD operations and actions together
    crud_result, action_results = await self._pipeline.execute_with_actions(
        entities=dirty_entities,
        actions=pending_actions,  # Only actions, NOT cascades
        action_executor=self._action_executor,
    )

    # Clear pending actions after commit (regardless of success)
    self._pending_actions.clear()  # Clears actions
    # BUG: _cascade_operations is NEVER cleared, processed, or passed anywhere
```

- **Why it happens**: The cascade feature was added (methods exist at lines 1610-1684, `CascadeExecutor` exists in `cascade.py`) but the integration point in `commit_async()` was never completed. There is no code path that:
  1. Retrieves `_cascade_operations`
  2. Instantiates or uses `CascadeExecutor`
  3. Executes the cascades
  4. Clears `_cascade_operations` after commit

### Fix Approach

**Option chosen**: OPTION B - Implement cascade execution (LOCKED IN per Prompt 0)

**Changes required**:

1. **Integrate CascadeExecutor into SaveSession**:
   - Add `_cascade_executor: CascadeExecutor` to `__init__`
   - Instantiate with client reference

2. **Modify commit_async() to execute cascades**:
   - After `execute_with_actions()` returns successfully
   - Before transitioning to COMMITTED state
   - Call `_cascade_executor.execute(self._cascade_operations)`
   - Store cascade results in SaveResult (or separate property)
   - Clear `_cascade_operations` after execution

3. **Update SaveResult to include cascade results**:
   - Add `cascade_results: list[CascadeResult]` field
   - Update `success` property to check cascade success

4. **Handle failed cascades appropriately**:
   - Keep failed cascades in `_cascade_operations` for retry (consistent with Issue 10 fix)
   - Include errors in result for user inspection

**Files to modify**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py` (SaveResult)

### Acceptance Criteria

- [ ] `SaveSession.cascade_field()` queues operations in `_cascade_operations` (already works)
- [ ] `commit_async()` passes cascade operations to CascadeExecutor
- [ ] Cascades execute in correct sequence (after CRUD and actions)
- [ ] `get_pending_cascades()` returns empty list after successful commit
- [ ] Failed cascades are preserved and can be inspected
- [ ] CascadeResult is accessible in SaveResult
- [ ] No regressions in existing 2,769+ tests
- [ ] Reproduction guide scenario (from QA docs) passes

### Test Plan

**Unit tests**:
- Test cascade operations are queued correctly
- Test cascades are passed to executor during commit
- Test cascades are cleared after successful commit
- Test failed cascades remain in pending list
- Test CascadeResult is included in SaveResult

**Integration tests**:
- Test end-to-end cascade: Business -> Contacts, Units, Offers
- Test cascade with target_types filter
- Test cascade with allow_override filtering
- Test partial cascade failure handling

### Dependencies

- **Blocks**: None
- **Blocked by**: None (can be implemented first)

### Effort Estimate

**Medium-High** (6-8 hours)
- CascadeExecutor already exists and works
- Main work is integration in commit_async
- Need tests for all cascade paths
- Must verify Business model integration

---

## ISSUE 14: Task.model_dump() Silent Data Loss on Direct Custom Field Modifications

### Summary

Users can modify `task.custom_fields` list directly (e.g., `task.custom_fields[0]['text_value'] = "X"`), but `model_dump()` only checks the `_custom_fields_accessor` for changes. If the accessor was never created or has no tracked modifications, direct changes to the underlying list are silently lost when the task is serialized for API save.

### Root Cause

- **File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`
- **Lines**: 141-163 (model_dump), 137-139 (get_custom_fields)
- **Code evidence**:

```python
# Lines 137-139: Accessor is created lazily, only when get_custom_fields() is called
def get_custom_fields(self) -> CustomFieldAccessor:
    if self._custom_fields_accessor is None:
        self._custom_fields_accessor = CustomFieldAccessor(self.custom_fields)
    return self._custom_fields_accessor
```

```python
# Lines 141-163: model_dump only checks accessor, not the actual list
def model_dump(self, **kwargs: Any) -> dict[str, Any]:
    data = super().model_dump(**kwargs)
    # If accessor exists and has changes, use its output
    # Per ADR-0056: Use to_api_dict() format for API payload
    if (
        self._custom_fields_accessor is not None  # <-- Only if accessor exists
        and self._custom_fields_accessor.has_changes()  # <-- Only if accessor has changes
    ):
        data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
    return data
    # BUG: If user modified task.custom_fields directly without calling
    # get_custom_fields() first, those changes are NOT detected!
```

- **Why it happens**: The code assumes all custom field modifications go through the accessor. But `task.custom_fields` is a public list that users can (and do) modify directly. The `model_dump()` method doesn't compare the current list state to any original snapshot - it only checks if the accessor has tracked changes.

### Fix Approach

**Option chosen**: OPTION A - Detect and merge direct modifications (RECOMMENDED per Prompt 0)

**Changes required**:

1. **Snapshot original custom_fields at initialization**:
   - Store a deep copy of `custom_fields` in a private attribute when task is created/loaded
   - `self._original_custom_fields = copy.deepcopy(self.custom_fields)`

2. **Detect direct modifications in model_dump()**:
   - Compare current `custom_fields` with `_original_custom_fields`
   - If different and accessor has no changes, use current list
   - If different and accessor HAS changes, merge both (accessor takes precedence for conflicts)

3. **Update model_dump() logic**:
   ```python
   def model_dump(self, **kwargs: Any) -> dict[str, Any]:
       data = super().model_dump(**kwargs)

       # Check for accessor changes
       accessor_changes = (
           self._custom_fields_accessor is not None
           and self._custom_fields_accessor.has_changes()
       )

       # Check for direct modifications
       direct_changes = self._has_direct_custom_field_changes()

       if accessor_changes:
           # Accessor changes take precedence
           data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
       elif direct_changes:
           # Direct modifications - convert to API format
           data["custom_fields"] = self._convert_direct_changes_to_api()

       return data
   ```

4. **Handle merge when both accessor AND direct changes exist**:
   - Accessor modifications take precedence (explicit API usage)
   - Log warning if both types of changes exist

**Files to modify**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

### Acceptance Criteria

- [ ] Direct modifications to `task.custom_fields` list are detected
- [ ] Direct modifications are persisted when task is saved
- [ ] Accessor modifications still work as before
- [ ] When both accessor and direct modifications exist, accessor takes precedence
- [ ] Warning is logged if both modification types detected (for user awareness)
- [ ] No data loss under any modification pattern
- [ ] Reproduction guide scenario passes
- [ ] No regressions in custom field tests

### Test Plan

**Unit tests**:
- Test direct modification without accessor is detected
- Test direct modification is persisted via model_dump
- Test accessor modification still works
- Test both modifications: accessor takes precedence
- Test empty custom_fields list (edge case)
- Test None custom_fields (edge case)

**Integration tests**:
- Test save_async() persists direct modifications
- Test full workflow: get task, modify directly, save, verify in API

### Dependencies

- **Blocks**: None
- **Blocked by**: None (can be implemented in parallel with Issue 11)

### Effort Estimate

**Medium** (2-3 hours)
- Need to add snapshot mechanism
- Update model_dump logic
- Write tests for all modification patterns
- Edge cases for empty/None lists

---

## ISSUE 5: P1 Direct Methods Don't Check SaveResult.success

### Summary

Convenience methods like `add_tag_async()`, `remove_tag_async()`, etc. don't check `SaveResult.success` after calling `commit_async()`. If the action fails (e.g., 422 error for non-existent tag), the error is captured in `SaveResult.action_results` but ignored. The method returns a task as if the operation succeeded.

### Root Cause

- **File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
- **Lines**: 586-607 (add_tag_async), and similarly 629-651, 673-700, 770-799, 826-848
- **Code evidence** (add_tag_async):

```python
# Lines 586-607: SaveResult is completely ignored
@error_handler
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task without explicit SaveSession."""
    async with SaveSession(self._client) as session:  # type: ignore[arg-type]
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        await session.commit_async()  # <-- Returns SaveResult, but NOT checked!

    return await self.get_async(task_gid)  # <-- Always returns task
    # BUG: If tag doesn't exist, action_results contains failure,
    # but we return a task as if everything succeeded!
```

- **Why it happens**: The methods were written with happy-path focus. The commit happens, but no one checks if it actually succeeded. The `SaveResult.success` property correctly checks both CRUD and action results, but these methods don't use it.

**Affected methods** (6 total in tasks.py):
1. `add_tag_async()` - line 586
2. `remove_tag_async()` - line 629
3. `move_to_section_async()` - line 673
4. `add_to_project_async()` - line 770
5. `remove_from_project_async()` - line 826
6. `set_assignee_async()` - line 725 (different pattern, uses HTTP PUT directly)

Note: `set_assignee_async` at line 725 uses a direct HTTP PUT, not SaveSession, so it doesn't have this specific issue.

### Fix Approach

**Changes required**:

1. **Store and check SaveResult after commit**:
   ```python
   async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
       async with SaveSession(self._client) as session:
           task = await self.get_async(task_gid)
           session.add_tag(task, tag_gid)
           result = await session.commit_async()

           # Check for failures
           if not result.success:
               # Raise appropriate error with details
               raise SaveSessionError(result)

       return await self.get_async(task_gid)
   ```

2. **Create SaveSessionError exception** (if not exists):
   - Add to `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/exceptions.py`
   - Include SaveResult for inspection
   - Include human-readable error message with failed action details

3. **Update all 5 affected P1 methods**:
   - `add_tag_async()`
   - `remove_tag_async()`
   - `move_to_section_async()`
   - `add_to_project_async()`
   - `remove_from_project_async()`

4. **Ensure sync wrappers propagate exceptions**:
   - Verify `_add_tag_sync()` etc. don't swallow exceptions

**Files to modify**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/exceptions.py` (add SaveSessionError)

### Acceptance Criteria

- [ ] Each P1 method checks `result.success` after commit
- [ ] If `result.success` is False, raises `SaveSessionError`
- [ ] Error message includes details of failed actions
- [ ] Valid operations still succeed normally
- [ ] Invalid operations (non-existent tag/project) raise exception
- [ ] Sync wrappers propagate exceptions correctly
- [ ] No regressions in existing P1 method tests

### Test Plan

**Unit tests** (for each of 5 methods):
- Test valid operation succeeds and returns task
- Test invalid target (non-existent GID) raises SaveSessionError
- Test error message includes action details
- Test sync wrapper propagates exception

**Integration tests**:
- Test with real invalid tag GID
- Test with real invalid project GID
- Test with permission denied scenario

### Dependencies

- **Blocks**: Issue 2 (double fetch optimization builds on same methods)
- **Blocked by**: None

### Effort Estimate

**Low** (1.5-2 hours)
- Simple conditional check in 5 methods
- Create one new exception class
- Write tests for each method

---

## ISSUE 2: Double API Fetch in P1 Direct Methods

### Summary

P1 methods like `add_tag_async()` call `get_async()` twice - once before commit to get the task, and once after commit to refresh it. The second fetch is unnecessary because `SaveResult` already contains the updated task from the API response.

### Root Cause

- **File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
- **Lines**: 586-607 (add_tag_async), and similarly in other P1 methods
- **Code evidence**:

```python
# Lines 586-607: Two get_async() calls
@error_handler
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)          # <-- Fetch 1: Get current state
        session.add_tag(task, tag_gid)
        await session.commit_async()

    return await self.get_async(task_gid)              # <-- Fetch 2: Unnecessary refresh!
```

- **Why it happens**: The pattern was written defensively - always refresh after mutation to ensure latest state. But action operations in Asana don't return the full updated task in their response body (unlike CRUD operations). The `ActionResult.response_data` contains the action response, not the full task.

**Analysis of SaveResult/ActionResult**:
Looking at `persistence/models.py` lines 416-438:
```python
@dataclass
class ActionResult:
    action: ActionOperation
    success: bool
    error: Exception | None = None
    response_data: dict[str, Any] | None = None  # API response - NOT full task
```

The Asana API action endpoints (like `/tasks/{gid}/addTag`) return `{}` on success, not the full updated task. So we DO need to fetch the task again to get its current state with the new tag.

**However**, we can optimize by:
1. Returning the task we already have (before commit) - it's still valid, just missing the new relationship
2. Using the task from SaveResult.succeeded (if CRUD ops were done)
3. Only fetching once if we need the fully updated state

### Fix Approach

**Changes required** (Two options):

**OPTION A: Return existing task** (faster, but stale relationship data):
```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        result = await session.commit_async()

        if not result.success:
            raise SaveSessionError(result)

    # Return the task we already have - caller can refresh if needed
    return task
```

**OPTION B: Fetch once after all operations** (correct data, still 2 calls but documented):
- Keep the pattern but document it clearly
- Users who need optimization can use SaveSession directly

**OPTION C: Hybrid approach** (RECOMMENDED):
- For methods that only do action operations (no CRUD), return existing task
- Document that returned task may not reflect new relationships
- Add `refresh: bool = False` parameter for users who need fresh data:
```python
async def add_tag_async(
    self, task_gid: str, tag_gid: str, *, refresh: bool = False
) -> Task:
    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        result = await session.commit_async()

        if not result.success:
            raise SaveSessionError(result)

    if refresh:
        return await self.get_async(task_gid)
    return task
```

**Recommendation**: OPTION C - gives users control without breaking existing behavior

**Files to modify**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

### Acceptance Criteria

- [ ] Default behavior: single API GET call (not 2)
- [ ] `refresh=True` parameter available for explicit refresh
- [ ] Returned task is valid (original task if not refreshing)
- [ ] Documentation clarifies that task.tags may not reflect new additions
- [ ] Works correctly for all 5 P1 methods
- [ ] No regressions in functionality
- [ ] Performance test verifies reduced API calls

### Test Plan

**Unit tests**:
- Test default behavior makes 1 GET call
- Test `refresh=True` makes 2 GET calls
- Test returned task is valid
- Test error handling still works

**Performance tests**:
- Mock HTTP client, count API calls
- Verify single add_tag_async = 1 GET + 1 POST (not 2 GET + 1 POST)

### Dependencies

- **Blocks**: None
- **Blocked by**: Issue 5 (same methods need SaveResult check first)

### Effort Estimate

**Low-Medium** (1.5-2 hours)
- Simple refactor of 5 methods
- Add optional parameter
- Update docstrings
- Write performance tests

---

## ISSUE 10: Pending Actions Cleared Before Checking Success

### Summary

In `SaveSession.commit_async()`, `_pending_actions.clear()` is called unconditionally after the pipeline executes, regardless of whether any actions failed. Failed actions are discarded and cannot be retried or inspected from the session.

### Root Cause

- **File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
- **Lines**: 547-555
- **Code evidence**:

```python
# Lines 547-555: Actions cleared regardless of success
async def commit_async(self) -> SaveResult:
    # ...
    # Execute CRUD operations and actions together
    crud_result, action_results = await self._pipeline.execute_with_actions(
        entities=dirty_entities,
        actions=pending_actions,
        action_executor=self._action_executor,
    )

    # Clear pending actions after commit (regardless of success)
    self._pending_actions.clear()  # <-- BUG: Clears ALL actions, even failed ones!

    # action_results might contain failures here, but we can't retry
    # because the original ActionOperations are gone
```

- **Why it happens**: The code was written with "clear after execution" semantics, assuming users would inspect `SaveResult.action_results` for failures. But this loses the original `ActionOperation` objects, making retry difficult.

**Current behavior**:
1. 5 actions queued
2. commit_async() executes all
3. 2 actions fail (in action_results)
4. ALL 5 cleared from _pending_actions
5. User has ActionResult with error, but cannot retry without reconstructing ActionOperation

### Fix Approach

**Option chosen**: Keep failed actions in pending + return in result (RECOMMENDED per Prompt 0)

**Changes required**:

1. **Modify commit_async() to selectively clear actions**:
   ```python
   async def commit_async(self) -> SaveResult:
       # ...
       crud_result, action_results = await self._pipeline.execute_with_actions(...)

       # Only clear successful actions
       successful_action_gids = {
           r.action.task.gid
           for r in action_results
           if r.success
       }
       self._pending_actions = [
           a for a in self._pending_actions
           if a.task.gid not in successful_action_gids
       ]
       # Failed actions remain in _pending_actions for retry
   ```

2. **Alternative: Clear all but track in SaveResult**:
   - Add `failed_actions: list[ActionOperation]` to SaveResult
   - Populate with failed ActionOperations before clearing
   - User can retry from result.failed_actions

3. **Preferred approach** (simpler, matches issue description):
   - Track which actions succeeded by matching ActionResult back to ActionOperation
   - Only remove succeeded actions from _pending_actions
   - Failed actions remain for inspection via `get_pending_actions()`

**Files to modify**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`

### Acceptance Criteria

- [ ] Failed actions remain in `_pending_actions` after commit
- [ ] Successful actions are cleared from `_pending_actions`
- [ ] `get_pending_actions()` returns only failed actions after partial failure
- [ ] User can inspect failed actions and retry
- [ ] ActionResult still contains error details for diagnosis
- [ ] Full success scenario clears all actions (as before)
- [ ] Full failure scenario keeps all actions
- [ ] No regressions in existing tests

### Test Plan

**Unit tests**:
- Test all-success: all actions cleared
- Test all-failure: all actions remain
- Test partial: only failed remain
- Test get_pending_actions() returns correct list
- Test retry scenario: re-commit succeeds

**Integration tests**:
- Test with mix of valid/invalid tag operations
- Test retry workflow end-to-end

### Dependencies

- **Blocks**: None
- **Blocked by**: None (can be implemented independently)

### Effort Estimate

**Medium** (2-3 hours)
- Need careful logic for matching results to operations
- Must handle edge cases (duplicate operations, etc.)
- Tests for all permutations of success/failure

---

## Implementation Sequence

Based on dependencies and complexity:

```
Phase 1 (Session 3):
  ├── ISSUE 11: Cascade operations (Medium-High, 6-8h)
  └── ISSUE 14: model_dump() data loss (Medium, 2-3h)
       [Can be parallelized - no interdependencies]

Phase 2 (Session 4):
  ├── ISSUE 5: SaveResult.success checks (Low, 1.5-2h)
  │   [Must complete before Issue 2]
  ├── ISSUE 2: Double fetch optimization (Low-Medium, 1.5-2h)
  │   [Depends on Issue 5 being in same methods]
  └── ISSUE 10: Actions cleared before check (Medium, 2-3h)
       [Independent]
```

**Total Estimated Effort**: 13.5-17 hours (aligns with 2-session estimate)

---

## Open Questions

None. All blocking questions resolved in Prompt 0.

---

## Appendix A: File Reference

| File | Issues | Lines of Interest |
|------|--------|-------------------|
| `src/autom8_asana/persistence/session.py` | 11, 10 | 117-161, 491-578, 1610-1684 |
| `src/autom8_asana/models/task.py` | 14 | 117-163, 210-258 |
| `src/autom8_asana/clients/tasks.py` | 5, 2 | 586-607, 629-651, 673-700, 770-799, 826-848 |
| `src/autom8_asana/persistence/models.py` | 10, 11 | 112-191, 416-438 |
| `src/autom8_asana/persistence/cascade.py` | 11 | 80-128 |
| `src/autom8_asana/persistence/pipeline.py` | 11 | 546-593 |

---

## Appendix B: Related Documents

- [QA Adversarial Review](/docs/validation/QA-ADVERSARIAL-REVIEW.md)
- [Issue Reproduction Guide](/docs/validation/ISSUE-REPRODUCTION-GUIDE.md)
- [Prompt 0](/docs/initiatives/qa-findings-triage-prompt-0.md)
- [Tech Debt Backlog](/docs/requirements/TECH-DEBT.md)

---

## Quality Gate Checklist

- [x] Problem statement is clear for each issue
- [x] Root cause confirmed with code evidence (file, line, snippet)
- [x] Fix approach is specific and implementable
- [x] Acceptance criteria are testable
- [x] Test plan covers unit and integration scenarios
- [x] Dependencies mapped
- [x] Effort estimates provided
- [x] No blocking open questions remain
- [x] Architect can begin design without clarification
