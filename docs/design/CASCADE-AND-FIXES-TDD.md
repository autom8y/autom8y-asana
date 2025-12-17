# TDD: QA Findings Cascade Integration and Critical Fixes

## Metadata
- **TDD ID**: TDD-TRIAGE-FIXES
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-12
- **Last Updated**: 2025-12-12
- **PRD Reference**: [TRIAGE-FIXES-REQUIREMENTS.md](/docs/requirements/TRIAGE-FIXES-REQUIREMENTS.md)
- **Related TDDs**: TDD-0011 (Action Operations), TDD-0010 (Save Orchestration)
- **Related ADRs**: ADR-0054 (Cascading Custom Fields), ADR-0055 (Action Result Integration), ADR-0040 (Partial Failure Handling), ADR-0065 (SaveSessionError Exception), ADR-0066 (Selective Action Clearing), ADR-0067 (Custom Field Snapshot Detection)

---

## Overview

This TDD provides minimal, targeted technical designs for 5 critical/high severity issues identified in the QA Adversarial Review. The designs fix confirmed root causes without over-engineering, enabling implementation with clear guidance while preserving the existing 2,769+ tests.

---

## Requirements Summary

| Issue | Severity | Summary | Root Cause |
|-------|----------|---------|------------|
| **11** | CRITICAL | Cascade operations not executed | `commit_async()` never invokes CascadeExecutor |
| **14** | CRITICAL | `model_dump()` silent data loss | Direct custom field modifications ignored |
| **5** | HIGH | P1 methods ignore `SaveResult.success` | Failed actions silently lost |
| **2** | HIGH | Double API fetch in P1 methods | `get_async()` called twice per operation |
| **10** | HIGH | Actions cleared before checking success | `_pending_actions.clear()` unconditional |

**Total Estimated Effort**: 13.5-17 hours

---

## Implementation Phases

```
Phase 1 (Session 3) - Critical Fixes:
  |-- ISSUE 11: Cascade execution integration (6-8h)
  |-- ISSUE 14: Direct custom field detection (2-3h)
      [Can be parallelized - no interdependencies]

Phase 2 (Session 4) - High Priority Fixes:
  |-- ISSUE 5: SaveResult.success checks (1.5-2h)
  |   [Must complete before Issue 2]
  |-- ISSUE 2: Double fetch optimization (1.5-2h)
  |   [Depends on Issue 5 - same methods]
  |-- ISSUE 10: Selective action clearing (2-3h)
      [Independent]
```

---

## Component: ISSUE 11 - Cascade Operations Not Executed

### Overview

The cascade feature exists (`CascadeExecutor` at `cascade.py:80-128`) but is never invoked during `commit_async()`. This design integrates cascade execution into the commit flow.

### Design

#### System Context

```
SaveSession.commit_async()
    |
    v
1. Execute CRUD operations
    |
    v
2. Execute Action operations
    |
    v
3. Execute Cascade operations  <-- MISSING: Must add
    |
    v
4. Return SaveResult (with cascade_results)
```

#### Data Model Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py`

Add `cascade_results` field to `SaveResult`:

```python
from autom8_asana.persistence.cascade import CascadeResult

@dataclass
class SaveResult:
    """Result of a commit operation.

    Per FR-ERROR-002: Provides succeeded, failed, and aggregate info.
    Per ADR-0055: Includes action operation results.
    Per TDD-TRIAGE-FIXES: Includes cascade operation results.
    """

    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    action_results: list[ActionResult] = field(default_factory=list)
    cascade_results: list[CascadeResult] = field(default_factory=list)  # NEW

    @property
    def success(self) -> bool:
        """True if all operations succeeded (CRUD, actions, AND cascades).

        Returns:
            True if no CRUD failures, all actions succeeded, and all cascades succeeded.
        """
        crud_ok = len(self.failed) == 0
        actions_ok = all(r.success for r in self.action_results)
        cascades_ok = all(r.success for r in self.cascade_results)
        return crud_ok and actions_ok and cascades_ok

    @property
    def cascade_succeeded(self) -> int:
        """Count of successful cascade operations."""
        return sum(1 for r in self.cascade_results if r.success)

    @property
    def cascade_failed(self) -> int:
        """Count of failed cascade operations."""
        return sum(1 for r in self.cascade_results if not r.success)
```

#### Interface Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`

1. Add `CascadeExecutor` initialization in `__init__`:

```python
def __init__(
    self,
    client: AsanaClient,
    batch_size: int = 10,
    max_concurrent: int = 15,
) -> None:
    # ... existing code ...

    # TDD-TRIAGE-FIXES: Cascade executor for field propagation
    from autom8_asana.persistence.cascade import CascadeExecutor
    self._cascade_executor = CascadeExecutor(client)

    # Initialize cascade operations list in __init__ (not lazily)
    self._cascade_operations: list[CascadeOperation] = []
```

2. Modify `commit_async()` to execute cascades:

```python
async def commit_async(self) -> SaveResult:
    """Execute all pending changes (async).

    Per FR-UOW-003: Execute pending changes.
    Per TDD-TRIAGE-FIXES: Execute cascade operations after actions.
    """
    self._ensure_open()

    dirty_entities = self._tracker.get_dirty_entities()
    pending_actions = list(self._pending_actions)
    pending_cascades = list(self._cascade_operations)

    if not dirty_entities and not pending_actions and not pending_cascades:
        if self._log:
            self._log.warning(
                "commit_empty_session",
                message="No tracked entities, pending actions, or cascades to commit.",
            )
        return SaveResult()

    if self._log:
        self._log.info(
            "session_commit_start",
            entity_count=len(dirty_entities),
            action_count=len(pending_actions),
            cascade_count=len(pending_cascades),
        )

    # Phase 1: Execute CRUD operations and actions together
    crud_result, action_results = await self._pipeline.execute_with_actions(
        entities=dirty_entities,
        actions=pending_actions,
        action_executor=self._action_executor,
    )

    # Phase 2: Clear successful actions (Issue 10 fix - selective clearing)
    self._clear_successful_actions(action_results)

    # Phase 3: Execute cascade operations
    cascade_results: list[CascadeResult] = []
    if pending_cascades:
        cascade_result = await self._cascade_executor.execute(pending_cascades)
        cascade_results = [cascade_result]

        # Clear successful cascades, keep failed
        if cascade_result.success:
            self._cascade_operations.clear()
        # Failed cascades remain for retry

    # Reset state for successful entities
    for entity in crud_result.succeeded:
        self._tracker.mark_clean(entity)

    self._state = SessionState.COMMITTED

    # Build final result
    crud_result.action_results = action_results
    crud_result.cascade_results = cascade_results

    if self._log:
        action_failures = sum(1 for r in action_results if not r.success)
        cascade_failures = sum(1 for r in cascade_results if not r.success)
        self._log.info(
            "session_commit_complete",
            succeeded=len(crud_result.succeeded),
            failed=len(crud_result.failed),
            action_succeeded=len(action_results) - action_failures,
            action_failed=action_failures,
            cascade_succeeded=len(cascade_results) - cascade_failures,
            cascade_failed=cascade_failures,
        )

    return crud_result
```

3. Fix `cascade_field()` to use initialized list:

```python
def cascade_field(
    self,
    entity: T,
    field_name: str,
    *,
    target_types: tuple[type, ...] | None = None,
) -> SaveSession:
    """Queue a cascade operation for the commit phase."""
    self._ensure_open()

    from autom8_asana.persistence.cascade import CascadeOperation

    op = CascadeOperation(
        source_entity=entity,
        field_name=field_name,
        target_types=target_types,
    )

    # Use pre-initialized list (not hasattr check)
    self._cascade_operations.append(op)

    if self._log:
        self._log.debug(
            "session_cascade_field",
            entity_type=type(entity).__name__,
            entity_gid=entity.gid,
            field_name=field_name,
        )

    return self
```

#### Sequence Diagram

```
User                SaveSession           Pipeline           CascadeExecutor
  |                     |                    |                      |
  |--cascade_field()-->|                    |                      |
  |                     |--append to        |                      |
  |                     |  _cascade_ops     |                      |
  |                     |                    |                      |
  |--commit_async()-->  |                    |                      |
  |                     |--execute_with_actions()-->               |
  |                     |<--crud_result, action_results--          |
  |                     |                    |                      |
  |                     |--execute(pending_cascades)------------->|
  |                     |                    |     For each op:    |
  |                     |                    |     _execute_single |
  |                     |<--cascade_result-----------------------|
  |                     |                    |                      |
  |<--SaveResult--------|                    |                      |
```

#### Error Handling

- **Cascade failures do NOT rollback CRUD/actions**: Partial success is acceptable
- **Failed cascades remain in `_cascade_operations`**: User can inspect via `get_pending_cascades()` and retry
- **`SaveResult.success` reflects cascade status**: Returns `False` if any cascade failed

### Implementation Notes

1. **Import order**: Import `CascadeExecutor` inside methods or at top with TYPE_CHECKING to avoid circular imports
2. **Backward compatibility**: `cascade_results` defaults to empty list, existing code unaffected
3. **Logging**: Add cascade counts to existing commit logging

### Test Approach

**Unit Tests** (`tests/unit/persistence/test_session_cascade.py`):
- `test_cascade_operations_queued_correctly`: Verify `cascade_field()` adds to list
- `test_cascades_executed_during_commit`: Mock executor, verify `execute()` called
- `test_cascades_cleared_on_success`: After successful commit, `get_pending_cascades()` empty
- `test_cascades_preserved_on_failure`: After failed cascade, operations remain
- `test_cascade_result_in_save_result`: Verify `result.cascade_results` populated
- `test_save_result_success_includes_cascades`: `result.success` is `False` when cascade fails

**Integration Tests** (`tests/integration/test_cascade_e2e.py`):
- `test_cascade_business_office_phone`: End-to-end cascade from Business to descendants
- `test_cascade_with_target_types_filter`: Cascade only to specified types
- `test_cascade_allow_override_filtering`: Override opt-in behavior works

### Risks

| Risk | Mitigation |
|------|------------|
| Circular import with CascadeExecutor | Import inside method body |
| Large hierarchy causes rate limiting | CascadeExecutor already handles batching |
| Failed cascade obscures successful CRUD | Log cascade failures distinctly |

---

## Component: ISSUE 14 - model_dump() Silent Data Loss

### Overview

Direct modifications to `task.custom_fields` list are ignored because `model_dump()` only checks the accessor. This design adds snapshot-based detection of direct modifications.

### Design

#### Data Model Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

Add snapshot storage and detection logic:

```python
import copy
from typing import TYPE_CHECKING, Any

from pydantic import Field, PrivateAttr, model_validator

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient


class Task(AsanaResource):
    """Asana Task resource model."""

    # ... existing fields ...

    # Private accessor instance (not serialized)
    _custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)
    # Private client reference for save/refresh operations (not serialized)
    _client: Any = PrivateAttr(default=None)
    # NEW: Snapshot of original custom_fields for direct modification detection
    _original_custom_fields: list[dict[str, Any]] | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _capture_custom_fields_snapshot(self) -> "Task":
        """Capture snapshot of custom_fields at initialization.

        Per TDD-TRIAGE-FIXES: Enable detection of direct modifications.
        """
        if self.custom_fields is not None:
            self._original_custom_fields = copy.deepcopy(self.custom_fields)
        return self

    def _has_direct_custom_field_changes(self) -> bool:
        """Check if custom_fields was modified directly (not via accessor).

        Returns:
            True if custom_fields differs from original snapshot.
        """
        if self._original_custom_fields is None:
            # No snapshot means no custom_fields at init
            return self.custom_fields is not None and len(self.custom_fields) > 0

        if self.custom_fields is None:
            # Had custom_fields, now None
            return True

        # Compare current to snapshot
        return self.custom_fields != self._original_custom_fields

    def _convert_direct_changes_to_api(self) -> dict[str, Any]:
        """Convert direct custom_fields modifications to API format.

        Returns:
            Dict of {field_gid: value} for modified fields.
        """
        if self.custom_fields is None:
            return {}

        # Build lookup of original values by GID
        original_by_gid: dict[str, dict[str, Any]] = {}
        if self._original_custom_fields:
            for field in self._original_custom_fields:
                gid = field.get("gid")
                if gid:
                    original_by_gid[gid] = field

        # Find changed fields
        result: dict[str, Any] = {}
        for field in self.custom_fields:
            gid = field.get("gid")
            if not gid:
                continue

            original = original_by_gid.get(gid)
            if original is None or field != original:
                # Field is new or changed - extract value
                value = self._extract_field_value(field)
                result[gid] = value

        return result

    def _extract_field_value(self, field: dict[str, Any]) -> Any:
        """Extract the appropriate value from a custom field dict.

        Args:
            field: Custom field dict from Asana API.

        Returns:
            Value suitable for API update payload.
        """
        # Check each value type in order of specificity
        if "text_value" in field:
            return field["text_value"]
        if "number_value" in field:
            return field["number_value"]
        if "enum_value" in field and field["enum_value"]:
            # Enum: extract GID
            return field["enum_value"].get("gid")
        if "multi_enum_value" in field and field["multi_enum_value"]:
            # Multi-enum: extract list of GIDs
            return [v.get("gid") for v in field["multi_enum_value"] if v.get("gid")]
        if "people_value" in field and field["people_value"]:
            # People: extract list of GIDs
            return [v.get("gid") for v in field["people_value"] if v.get("gid")]
        if "date_value" in field and field["date_value"]:
            return field["date_value"]
        # Default: None (field cleared)
        return None

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to include custom field modifications.

        Per ADR-0056: Use to_api_dict() format for API payload.
        Per TDD-TRIAGE-FIXES: Detect and merge direct modifications.
        """
        data = super().model_dump(**kwargs)

        # Check for accessor changes
        accessor_changes = (
            self._custom_fields_accessor is not None
            and self._custom_fields_accessor.has_changes()
        )

        # Check for direct modifications
        direct_changes = self._has_direct_custom_field_changes()

        if accessor_changes and direct_changes:
            # Both types of changes - accessor takes precedence
            # Log warning for user awareness
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Task %s has both accessor and direct custom_field modifications. "
                "Accessor changes take precedence.",
                self.gid,
            )
            data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
        elif accessor_changes:
            # Only accessor changes
            data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
        elif direct_changes:
            # Only direct changes
            data["custom_fields"] = self._convert_direct_changes_to_api()

        return data
```

#### State Diagram

```
                    +------------------+
                    |    Task Init     |
                    |  (from API)      |
                    +--------+---------+
                             |
                             v
              +-----------------------------+
              |  _original_custom_fields    |
              |  = deepcopy(custom_fields)  |
              +-----------------------------+
                             |
          +------------------+------------------+
          |                                     |
          v                                     v
+-------------------+                 +-------------------+
| Direct Modify     |                 | Use Accessor      |
| task.custom_fields|                 | task.get_custom_  |
| [0]['text_value'] |                 | fields().set()    |
+--------+----------+                 +--------+----------+
         |                                     |
         v                                     v
+-------------------+                 +-------------------+
| _has_direct_      |                 | accessor.         |
| custom_field_     |                 | has_changes()     |
| changes() = True  |                 | = True            |
+--------+----------+                 +--------+----------+
         |                                     |
         +------------------+------------------+
                            |
                            v
                  +-------------------+
                  |   model_dump()    |
                  | Detects & merges  |
                  +-------------------+
```

#### Error Handling

- **No exception on conflict**: Accessor takes precedence, warning logged
- **Empty custom_fields handled**: Snapshot is `None`, detection works correctly
- **None values supported**: Clearing a field via direct modification is detected

### Implementation Notes

1. **Deep copy performance**: Only happens once at initialization, negligible overhead
2. **Comparison semantics**: Uses `!=` which works for list of dicts
3. **Pydantic validator**: `model_validator(mode="after")` ensures all fields populated before snapshot
4. **Logging import**: Use `logging.getLogger` to avoid import issues

### Test Approach

**Unit Tests** (`tests/unit/models/test_task_custom_fields.py`):
- `test_direct_modification_detected`: Modify list directly, verify `_has_direct_custom_field_changes()` returns True
- `test_accessor_modification_detected`: Use accessor, verify `has_changes()` returns True
- `test_no_modification_detected`: No changes, both methods return False
- `test_direct_changes_persisted_in_model_dump`: Direct changes appear in output
- `test_accessor_takes_precedence_over_direct`: Both modified, accessor wins
- `test_warning_logged_on_conflict`: Both modified, warning logged
- `test_empty_custom_fields_handled`: `custom_fields=None` or `[]` works
- `test_snapshot_is_deep_copy`: Modifying list doesn't affect snapshot

**Integration Tests**:
- `test_save_async_persists_direct_modifications`: Full save workflow with direct changes

### Risks

| Risk | Mitigation |
|------|------------|
| Deep copy performance on large custom_fields | Asana limits custom fields per project; negligible |
| Comparison false positives (ordering) | Asana API returns consistent ordering |
| User confusion on precedence | Warning log + documentation |

---

## Component: ISSUE 5 - P1 Direct Methods Don't Check SaveResult.success

### Overview

P1 convenience methods ignore `SaveResult.success`, silently losing failed actions. This design adds proper error checking and introduces `SaveSessionError`.

### Design

#### Data Model Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/exceptions.py`

Add new exception class:

```python
class SaveSessionError(SaveOrchestrationError):
    """Raised when a SaveSession commit fails in a convenience method.

    Per TDD-TRIAGE-FIXES: P1 methods must propagate failures to callers.

    This exception wraps the SaveResult so callers can inspect
    what succeeded and what failed.

    Attributes:
        result: The SaveResult containing success/failure details.
        message: Human-readable summary of failures.
    """

    def __init__(self, result: SaveResult) -> None:
        """Initialize with SaveResult.

        Args:
            result: The SaveResult from commit_async().
        """
        self.result = result

        # Build descriptive message
        failures: list[str] = []

        # CRUD failures
        for err in result.failed:
            failures.append(
                f"CRUD {err.operation.value} on {type(err.entity).__name__}"
                f"(gid={err.entity.gid}): {err.error}"
            )

        # Action failures
        for action_result in result.action_results:
            if not action_result.success:
                failures.append(
                    f"Action {action_result.action.action.value} on task "
                    f"{action_result.action.task.gid}: {action_result.error}"
                )

        message = f"SaveSession commit failed. {len(failures)} failure(s): " + "; ".join(failures[:3])
        if len(failures) > 3:
            message += f" ... and {len(failures) - 3} more"

        super().__init__(message)
```

Update `__all__` in exceptions module to export `SaveSessionError`.

#### Interface Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

Update all 5 affected P1 methods. Pattern for each:

```python
@error_handler
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task without explicit SaveSession.

    Args:
        task_gid: Target task GID
        tag_gid: Tag GID to add

    Returns:
        Updated Task from API

    Raises:
        APIError: If task or tag not found
        SaveSessionError: If the action operation fails

    Example:
        >>> task = await client.tasks.add_tag_async(task_gid, tag_gid)
    """
    from autom8_asana.persistence.exceptions import SaveSessionError

    async with SaveSession(self._client) as session:  # type: ignore[arg-type]
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        result = await session.commit_async()

        # Per TDD-TRIAGE-FIXES: Check for failures
        if not result.success:
            raise SaveSessionError(result)

    return await self.get_async(task_gid)
```

**Methods to update** (same pattern):
1. `add_tag_async()` - line 586
2. `remove_tag_async()` - line 629
3. `move_to_section_async()` - line 673
4. `add_to_project_async()` - line 770
5. `remove_from_project_async()` - line 826

#### Error Handling

- **Exception type**: New `SaveSessionError` wraps `SaveResult`
- **Error message**: Includes first 3 failure details, count of additional
- **Result inspection**: `SaveSessionError.result` provides full details

### Implementation Notes

1. **Import location**: Import `SaveSessionError` inside method to avoid circular import
2. **Sync wrappers**: Will automatically propagate exception (no change needed)
3. **Backward compatibility**: Previously silent failures now raise - this is intentional

### Test Approach

**Unit Tests** (`tests/unit/clients/test_tasks_p1_methods.py`):
- `test_add_tag_success`: Valid operation succeeds, returns task
- `test_add_tag_invalid_gid_raises`: Non-existent tag GID raises `SaveSessionError`
- `test_save_session_error_message_format`: Error message includes details
- `test_save_session_error_result_accessible`: Can inspect `error.result`
- Same tests for each of the 5 methods

**Integration Tests**:
- `test_add_invalid_tag_raises_descriptive_error`: Real API rejection handled

### Risks

| Risk | Mitigation |
|------|------------|
| Breaking change (silent -> exception) | Documented behavior change; correct behavior |
| Import cycle with SaveSessionError | Import inside method body |

---

## Component: ISSUE 2 - Double API Fetch in P1 Methods

### Overview

P1 methods call `get_async()` twice (before and after commit). Add `refresh` parameter for user control.

### Design

#### Interface Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

Update all 5 affected P1 methods. Pattern for each:

```python
@error_handler
async def add_tag_async(
    self, task_gid: str, tag_gid: str, *, refresh: bool = False
) -> Task:
    """Add tag to task without explicit SaveSession.

    Args:
        task_gid: Target task GID
        tag_gid: Tag GID to add
        refresh: If True, fetch fresh task state after commit. If False (default),
                 return the task fetched before commit. Note: the returned task
                 may not reflect the newly added tag relationship until refreshed.

    Returns:
        Task object (refreshed if refresh=True, otherwise pre-commit state)

    Raises:
        APIError: If task or tag not found
        SaveSessionError: If the action operation fails

    Example:
        >>> # Default: single GET (faster, but task.tags may be stale)
        >>> task = await client.tasks.add_tag_async(task_gid, tag_gid)
        >>>
        >>> # With refresh: two GETs (slower, but task.tags is current)
        >>> task = await client.tasks.add_tag_async(task_gid, tag_gid, refresh=True)
    """
    from autom8_asana.persistence.exceptions import SaveSessionError

    async with SaveSession(self._client) as session:  # type: ignore[arg-type]
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        result = await session.commit_async()

        if not result.success:
            raise SaveSessionError(result)

    # Per TDD-TRIAGE-FIXES: Only refresh if explicitly requested
    if refresh:
        return await self.get_async(task_gid)
    return task
```

**Methods to update** (same pattern):
1. `add_tag_async(task_gid, tag_gid, *, refresh=False)`
2. `remove_tag_async(task_gid, tag_gid, *, refresh=False)`
3. `move_to_section_async(task_gid, section_gid, project_gid, *, refresh=False)`
4. `add_to_project_async(task_gid, project_gid, section_gid=None, *, refresh=False)`
5. `remove_from_project_async(task_gid, project_gid, *, refresh=False)`

**Sync wrappers** - Add `refresh` parameter:

```python
def add_tag(self, task_gid: str, tag_gid: str, *, refresh: bool = False) -> Task:
    """Add tag to task without explicit SaveSession (sync)."""
    return self._add_tag_sync(task_gid, tag_gid, refresh=refresh)

@sync_wrapper("add_tag_async")
async def _add_tag_sync(
    self, task_gid: str, tag_gid: str, *, refresh: bool = False
) -> Task:
    """Internal sync wrapper for add_tag_async."""
    return await self.add_tag_async(task_gid, tag_gid, refresh=refresh)
```

### Implementation Notes

1. **Default `refresh=False`**: Optimizes for performance by default
2. **Keyword-only**: `*` forces `refresh` to be passed by name, preventing positional errors
3. **Documentation**: Docstring explains staleness trade-off
4. **Backward compatible**: Default behavior changes (2 GET -> 1 GET), but callers can opt into old behavior

### Test Approach

**Unit Tests** (`tests/unit/clients/test_tasks_p1_methods.py`):
- `test_add_tag_default_single_get`: Mock HTTP, verify 1 GET + 1 POST
- `test_add_tag_refresh_true_double_get`: Mock HTTP, verify 2 GET + 1 POST
- `test_returned_task_is_valid`: Returned task has correct GID
- Same pattern for all 5 methods

### Risks

| Risk | Mitigation |
|------|------------|
| User expects fresh task | Docstring clearly explains staleness |
| Breaking change in return value | Task is still valid, just pre-commit state |

---

## Component: ISSUE 10 - Pending Actions Cleared Before Checking Success

### Overview

`_pending_actions.clear()` runs unconditionally, discarding failed actions. This design implements selective clearing based on `ActionResult.success`.

### Design

#### Interface Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`

Add helper method and update `commit_async()`:

```python
def _clear_successful_actions(self, action_results: list[ActionResult]) -> None:
    """Remove only successful actions from pending list.

    Per TDD-TRIAGE-FIXES: Failed actions remain for inspection/retry.

    Args:
        action_results: Results from action execution.
    """
    if not action_results:
        # No actions executed, clear all (original behavior)
        self._pending_actions.clear()
        return

    # Build set of successful action identities
    # Identity = (task.gid, action_type, target_gid)
    successful_identities: set[tuple[str, ActionType, str | None]] = set()
    for result in action_results:
        if result.success:
            action = result.action
            identity = (action.task.gid, action.action, action.target_gid)
            successful_identities.add(identity)

    # Keep only failed actions
    self._pending_actions = [
        action for action in self._pending_actions
        if (action.task.gid, action.action, action.target_gid) not in successful_identities
    ]
```

Update `commit_async()` to use the new method (shown in Issue 11 design).

#### Action Identity Model

An action is uniquely identified by the tuple:
```
(task.gid, action_type, target_gid)
```

**Examples**:
- `("task_123", ActionType.ADD_TAG, "tag_456")` - Add specific tag to specific task
- `("task_123", ActionType.ADD_LIKE, None)` - Like operation (no target_gid)

**Edge case - Duplicate operations**: If user queues same action twice:
- First execution: succeeds, added to `successful_identities`
- Second operation in `_pending_actions`: Also matches identity, removed
- Result: Both cleared (correct behavior - duplicate was redundant)

#### Sequence Diagram

```
commit_async()
    |
    v
execute_with_actions() -> action_results
    |
    v
_clear_successful_actions(action_results)
    |
    +-- For each ActionResult:
    |       if success: add identity to successful_set
    |
    +-- Filter _pending_actions:
    |       keep only actions NOT in successful_set
    |
    v
Failed actions remain in _pending_actions
User can:
  - Inspect via get_pending_actions()
  - Retry via another commit_async()
```

#### Error Handling

- **All success**: `_pending_actions` becomes empty
- **All failure**: `_pending_actions` unchanged
- **Partial**: Only failed actions remain
- **No actions**: Original `clear()` behavior (empty list)

### Implementation Notes

1. **Identity comparison**: Uses tuple for hashable set membership
2. **Order preserved**: Failed actions maintain original order
3. **Retry semantics**: User can call `commit_async()` again to retry failed actions

### Test Approach

**Unit Tests** (`tests/unit/persistence/test_session_actions.py`):
- `test_all_success_clears_all_actions`: 3 actions succeed, list empty
- `test_all_failure_keeps_all_actions`: 3 actions fail, list unchanged
- `test_partial_keeps_only_failed`: 2 succeed, 1 fails, 1 remains
- `test_get_pending_actions_returns_failed_after_commit`: Can inspect failures
- `test_retry_succeeds_after_fix`: Re-commit succeeds after fixing issue
- `test_duplicate_operations_both_cleared`: Same action queued twice, both removed on success

### Risks

| Risk | Mitigation |
|------|------------|
| Memory leak if user never handles failures | Failed actions are bounded by user's queue size |
| Identity collision (different actions same tuple) | Tuple includes all relevant fields |
| Performance with many actions | Set membership is O(1) |

---

## Technical Decisions Summary

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Cascade execution after actions | Phase 3 in commit flow | Cascades may depend on newly created entities | ADR-0054 |
| SaveSessionError exception | New exception wrapping SaveResult | Provides details while being catchable | ADR-0065 |
| Custom field snapshot timing | model_validator(mode="after") | All fields populated before snapshot | ADR-0067 |
| Action identity model | (task.gid, action_type, target_gid) tuple | Uniquely identifies action for matching | ADR-0066 |
| P1 refresh parameter | Default False, keyword-only | Performance by default, explicit opt-in for freshness | - |

---

## Complexity Assessment

**Level**: Module

**Justification**:
- Fixes are scoped changes to existing components
- No new architectural patterns introduced
- No external dependencies added
- All changes are within existing module boundaries
- Tests remain in existing test structure

---

## Observability

**Logging**:
- Cascade execution counts in `session_commit_complete`
- Warning when both accessor and direct custom field changes detected
- Existing action logging unchanged

**Metrics** (future consideration):
- `cascade_operations_total` counter
- `cascade_operations_failed_total` counter
- `p1_method_refresh_rate` (percentage using refresh=True)

---

## Testing Strategy Summary

| Component | Unit Tests | Integration Tests |
|-----------|------------|-------------------|
| Issue 11 (Cascade) | 6 tests | 3 tests |
| Issue 14 (model_dump) | 8 tests | 1 test |
| Issue 5 (SaveResult check) | 5 tests per method = 25 | 1 test |
| Issue 2 (Double fetch) | 4 tests per method = 20 | - |
| Issue 10 (Selective clear) | 6 tests | - |

**Total**: ~65 new tests

---

## Open Questions

None. All design decisions resolved.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Architect | Initial draft |
