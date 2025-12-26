# PRD-10: Quality & Triage

> PRD for QA findings and bug triage.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-0023 (QA Findings Triage & Fix)
- **Related TDD**: N/A (standalone)
- **Original Author**: Requirements Analyst
- **Original Version**: 1.0

---

## Executive Summary

This PRD consolidates the requirements for addressing 5 critical/high severity issues identified during QA adversarial review. Each issue has confirmed root cause with code evidence, validated fix approach, and acceptance criteria. All blocking questions have been resolved through Prompt 0 triage.

**Scope**: 5 critical/high issues requiring 13.5-17 hours total effort across 2 implementation sessions.

**Decisions Locked**:
- Cascade feature: Implement (not delete)
- model_dump() fix: Detect + merge direct modifications
- Failed actions: Keep in pending + return in result

---

## Problem Statement

The QA adversarial review identified 5 issues that compromise data integrity, cause silent failures, or result in unnecessary API overhead:

1. **ISSUE 11**: Cascade operations are queued but never executed, rendering the entire cascade feature non-functional
2. **ISSUE 14**: Direct modifications to `task.custom_fields` are silently lost when serializing for API save
3. **ISSUE 5**: P1 convenience methods ignore SaveResult.success, returning tasks as if operations succeeded when they failed
4. **ISSUE 2**: P1 methods make unnecessary double API fetches, impacting performance
5. **ISSUE 10**: Failed actions are cleared from pending list, preventing retry or inspection

These issues affect core functionality used by developers building Asana integrations.

---

## Goals & Non-Goals

### Goals

- Fix all 5 identified issues with verified root causes
- Maintain backward compatibility with existing test suite (2,769+ tests)
- Provide clear error messages when operations fail
- Enable retry workflows for failed actions
- Optimize API call patterns in convenience methods

### Non-Goals

- Refactoring unrelated code paths
- Adding new features beyond the fix scope
- Changing public API signatures (except adding optional parameters)
- Performance optimization beyond the double-fetch fix

---

## Requirements

### REQ-1: Cascade Operation Execution (Issue 11)

**Priority**: Critical

**Problem**: `SaveSession.cascade_field()` queues operations in `_cascade_operations`, but `commit_async()` never executes them.

**Requirements**:
- R1.1: Integrate `CascadeExecutor` into `SaveSession.__init__`
- R1.2: Execute cascades in `commit_async()` after CRUD and action operations
- R1.3: Store cascade results in `SaveResult.cascade_results`
- R1.4: Clear `_cascade_operations` only after successful execution
- R1.5: Preserve failed cascades for inspection and retry

**Files**: `persistence/session.py`, `persistence/models.py`

**Effort**: 6-8 hours

---

### REQ-2: Custom Field Direct Modification Detection (Issue 14)

**Priority**: Critical

**Problem**: Direct modifications to `task.custom_fields` list bypass the accessor and are lost in `model_dump()`.

**Requirements**:
- R2.1: Snapshot original `custom_fields` at task initialization via deep copy
- R2.2: Detect direct modifications by comparing current state to snapshot
- R2.3: In `model_dump()`, merge direct changes when accessor has no tracked changes
- R2.4: Accessor modifications take precedence when both exist
- R2.5: Log warning when both direct and accessor modifications detected

**Files**: `models/task.py`

**Effort**: 2-3 hours

---

### REQ-3: SaveResult Success Checking (Issue 5)

**Priority**: High

**Problem**: P1 methods (`add_tag_async`, etc.) don't check `SaveResult.success`, returning tasks despite operation failures.

**Requirements**:
- R3.1: Check `result.success` after every `commit_async()` in P1 methods
- R3.2: Raise `SaveSessionError` with result details when success is False
- R3.3: Create `SaveSessionError` exception class in `persistence/exceptions.py`
- R3.4: Include human-readable error message with failed action details
- R3.5: Ensure sync wrappers propagate exceptions correctly

**Affected Methods**:
- `add_tag_async()`
- `remove_tag_async()`
- `move_to_section_async()`
- `add_to_project_async()`
- `remove_from_project_async()`

**Files**: `clients/tasks.py`, `persistence/exceptions.py`

**Effort**: 1.5-2 hours

---

### REQ-4: Double Fetch Optimization (Issue 2)

**Priority**: High

**Problem**: P1 methods call `get_async()` twice - before and after commit - wasting an API call.

**Requirements**:
- R4.1: Default behavior returns existing task without second fetch
- R4.2: Add `refresh: bool = False` parameter to all 5 P1 methods
- R4.3: When `refresh=True`, perform second fetch to get updated state
- R4.4: Document that returned task may not reflect new relationships without refresh
- R4.5: Verify single add_tag_async = 1 GET + 1 POST (not 2 GET + 1 POST)

**Files**: `clients/tasks.py`

**Effort**: 1.5-2 hours

**Depends On**: REQ-3 (same methods need SaveResult check first)

---

### REQ-5: Selective Action Clearing (Issue 10)

**Priority**: High

**Problem**: `_pending_actions.clear()` runs unconditionally, discarding failed actions before they can be retried.

**Requirements**:
- R5.1: Only clear actions that succeeded from `_pending_actions`
- R5.2: Failed actions remain in `_pending_actions` for retry
- R5.3: `get_pending_actions()` returns only remaining (failed) actions after partial failure
- R5.4: Full success clears all actions (preserve existing behavior)
- R5.5: Full failure keeps all actions

**Files**: `persistence/session.py`

**Effort**: 2-3 hours

---

## User Stories

### US-1: Cascade Execution
**As a** developer using Business entities
**I want** cascade operations to actually execute when I commit
**So that** related entities (Contacts, Units, Offers) receive the cascaded field values

### US-2: Custom Field Safety
**As a** developer modifying task custom fields
**I want** my direct list modifications to persist
**So that** I don't lose data when the task is saved

### US-3: Operation Failure Visibility
**As a** developer using P1 convenience methods
**I want** exceptions raised when operations fail
**So that** I can handle errors appropriately instead of assuming success

### US-4: API Efficiency
**As a** developer concerned about rate limits
**I want** P1 methods to minimize API calls
**So that** my application stays within Asana's limits

### US-5: Action Retry
**As a** developer handling partial failures
**I want** failed actions to remain pending
**So that** I can inspect, fix, and retry them without reconstructing the operations

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Suite Pass Rate | 100% | All 2,769+ existing tests pass |
| New Test Coverage | 100% | Each fix has unit and integration tests |
| Reproduction Scenarios | Pass | All QA reproduction scenarios pass |
| API Call Reduction | 50% | P1 methods reduce from 2 GET to 1 GET |
| Zero Data Loss | 100% | No custom field modifications lost |

---

## Dependencies

### Implementation Sequence

```
Phase 1 (Session 3):
  +-- REQ-1: Cascade operations (6-8h)
  +-- REQ-2: model_dump() fix (2-3h)
       [Parallelizable - no interdependencies]

Phase 2 (Session 4):
  +-- REQ-3: SaveResult checks (1.5-2h) [Must complete first]
  +-- REQ-4: Double fetch (1.5-2h) [Depends on REQ-3]
  +-- REQ-5: Action clearing (2-3h) [Independent]
```

### File Reference

| File | Requirements | Key Lines |
|------|--------------|-----------|
| `persistence/session.py` | REQ-1, REQ-5 | 117-161, 491-578, 1610-1684 |
| `models/task.py` | REQ-2 | 117-163, 210-258 |
| `clients/tasks.py` | REQ-3, REQ-4 | 586-607, 629-651, 673-700, 770-799, 826-848 |
| `persistence/models.py` | REQ-1, REQ-5 | 112-191, 416-438 |
| `persistence/cascade.py` | REQ-1 | 80-128 |
| `persistence/exceptions.py` | REQ-3 | New file or addition |

### Related Documents

- QA Adversarial Review: `/docs/validation/QA-ADVERSARIAL-REVIEW.md`
- Issue Reproduction Guide: `/docs/validation/ISSUE-REPRODUCTION-GUIDE.md`
- Tech Debt Backlog: `/docs/requirements/TECH-DEBT.md`

---

## Appendix: Code Evidence Summary

### Issue 11 - Cascade Never Executed
```python
# session.py:547-555 - commit_async() NEVER touches _cascade_operations
async def commit_async(self) -> SaveResult:
    crud_result, action_results = await self._pipeline.execute_with_actions(
        entities=dirty_entities,
        actions=pending_actions,  # Only actions, NOT cascades
        action_executor=self._action_executor,
    )
    self._pending_actions.clear()
    # BUG: _cascade_operations is NEVER cleared, processed, or passed anywhere
```

### Issue 14 - Silent Data Loss
```python
# task.py:141-163 - model_dump only checks accessor
def model_dump(self, **kwargs: Any) -> dict[str, Any]:
    if (
        self._custom_fields_accessor is not None
        and self._custom_fields_accessor.has_changes()
    ):
        data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
    return data
    # BUG: Direct modifications to task.custom_fields NOT detected
```

### Issue 5 - SaveResult Ignored
```python
# tasks.py:586-607 - SaveResult completely ignored
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        await session.commit_async()  # Returns SaveResult, but NOT checked!
    return await self.get_async(task_gid)  # Always returns task
```

### Issue 10 - Actions Cleared Unconditionally
```python
# session.py:547-555 - Actions cleared regardless of success
self._pending_actions.clear()  # BUG: Clears ALL actions, even failed ones
```
