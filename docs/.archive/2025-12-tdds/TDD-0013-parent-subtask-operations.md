# TDD-0013: Parent & Subtask Operations

## Metadata
- **TDD ID**: TDD-0013
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **PRD Reference**: [PRD-0008](../requirements/PRD-0008-parent-subtask-operations.md)
- **Related TDDs**:
  - [TDD-0010](TDD-0010-save-orchestration.md) - Save Orchestration Layer (foundation)
  - [TDD-0011](TDD-0011-action-endpoint-support.md) - Action Endpoint Support (pattern reference)
  - [TDD-0012](TDD-0012-sdk-functional-parity.md) - SDK Functional Parity (implementation reference)
- **Related ADRs**:
  - [ADR-0044](../decisions/ADR-0044-extra-params-field.md) - extra_params Field Design
  - [ADR-0045](../decisions/ADR-0045-like-operations-without-target.md) - Optional target_gid Pattern
  - [ADR-0047](../decisions/ADR-0047-positioning-validation-timing.md) - Positioning Validation Timing

## Overview

This design extends the Save Orchestration Layer with parent/subtask operations via a single `SET_PARENT` ActionType. The extension adds 2 new SaveSession methods (`set_parent`, `reorder_subtask`) and 1 new ActionType, following established patterns exactly. All changes require modifications to only 2 source files.

## Requirements Summary

This design addresses [PRD-0008](../requirements/PRD-0008-parent-subtask-operations.md) v1.0:

| Requirement | Summary | Design Impact |
|-------------|---------|---------------|
| FR-PAR-001 | `set_parent(task, parent)` method | New SaveSession method |
| FR-PAR-002 | `set_parent(task, None)` promotes subtask | `parent: null` in API payload |
| FR-PAR-003/004 | `insert_before`/`insert_after` positioning | extra_params field (per ADR-0044) |
| FR-PAR-005 | PositioningConflictError on conflict | Reuse existing exception (per ADR-0047) |
| FR-PAR-006 | `reorder_subtask()` convenience method | Wrapper calling set_parent() |
| FR-PAR-007 | ValueError if reorder_subtask on top-level | Validation in method |
| FR-PAR-008 | SET_PARENT ActionType | +1 enum value |
| FR-PAR-009 | Correct `to_api_call()` generation | +1 match case |

## Design

### ActionType Enum Extension

```python
class ActionType(str, Enum):
    # Existing (14 values from TDD-0011/TDD-0012)
    ADD_TAG = "add_tag"
    # ... (omitted for brevity)
    ADD_COMMENT = "add_comment"

    # New (TDD-0013)
    SET_PARENT = "set_parent"  # POST /tasks/{gid}/setParent
```

### ActionOperation.to_api_call() Case

```python
case ActionType.SET_PARENT:
    # Per PRD-0008: parent_gid can be None (promote to top-level) or a task GID
    parent_gid = self.extra_params.get("parent")  # None or GID string
    data: dict[str, Any] = {"parent": parent_gid}
    if "insert_before" in self.extra_params:
        data["insert_before"] = self.extra_params["insert_before"]
    if "insert_after" in self.extra_params:
        data["insert_after"] = self.extra_params["insert_after"]
    return (
        "POST",
        f"/tasks/{task_gid}/setParent",
        {"data": data},
    )
```

### SaveSession.set_parent() Method

```python
def set_parent(
    self,
    task: AsanaResource,
    parent: AsanaResource | str | None,
    *,
    insert_before: AsanaResource | str | None = None,
    insert_after: AsanaResource | str | None = None,
) -> SaveSession:
    """Set or change the parent of a task.

    Use this to:
    - Convert a task to a subtask: set_parent(task, parent_task)
    - Promote a subtask to top-level: set_parent(task, None)
    - Move subtask to different parent: set_parent(task, new_parent)
    - Position within siblings: set_parent(task, parent, insert_after=sibling)

    Args:
        task: The task to reparent.
        parent: New parent task, GID string, or None to promote to top-level.
        insert_before: Position before this sibling (mutually exclusive).
        insert_after: Position after this sibling (mutually exclusive).

    Returns:
        Self for fluent chaining.

    Raises:
        PositioningConflictError: If both insert_before and insert_after specified.
        SessionClosedError: If session is closed.
    """
    self._ensure_open()

    # Per ADR-0047: Fail-fast validation for positioning conflict
    if insert_before is not None and insert_after is not None:
        before_gid = insert_before if isinstance(insert_before, str) else insert_before.gid
        after_gid = insert_after if isinstance(insert_after, str) else insert_after.gid
        raise PositioningConflictError(before_gid, after_gid)

    # Resolve parent GID (None means promote to top-level)
    parent_gid: str | None = None
    if parent is not None:
        parent_gid = parent if isinstance(parent, str) else parent.gid

    # Build extra_params (per ADR-0044)
    extra_params: dict[str, Any] = {"parent": parent_gid}
    if insert_before is not None:
        extra_params["insert_before"] = (
            insert_before if isinstance(insert_before, str) else insert_before.gid
        )
    if insert_after is not None:
        extra_params["insert_after"] = (
            insert_after if isinstance(insert_after, str) else insert_after.gid
        )

    action = ActionOperation(
        task=task,
        action=ActionType.SET_PARENT,
        target_gid=None,  # Per ADR-0045: Not used for SET_PARENT
        extra_params=extra_params,
    )
    self._pending_actions.append(action)

    if self._log:
        self._log.debug(
            "session_set_parent",
            task_gid=task.gid,
            parent_gid=parent_gid,
        )

    return self
```

### SaveSession.reorder_subtask() Method

```python
def reorder_subtask(
    self,
    task: AsanaResource,
    *,
    insert_before: AsanaResource | str | None = None,
    insert_after: AsanaResource | str | None = None,
) -> SaveSession:
    """Reorder a subtask within its current parent.

    Convenience method that calls set_parent() with the task's current parent.
    Task must be a subtask (have a parent).

    Args:
        task: The subtask to reorder (must have task.parent set).
        insert_before: Position before this sibling.
        insert_after: Position after this sibling.

    Returns:
        Self for fluent chaining.

    Raises:
        ValueError: If task has no parent (is not a subtask).
        PositioningConflictError: If both insert_before and insert_after specified.
        SessionClosedError: If session is closed.
    """
    # Per FR-PAR-007: Task must have a parent to be reordered
    if not hasattr(task, 'parent') or task.parent is None:
        raise ValueError(
            f"Cannot reorder task without parent. Use set_parent() to assign a parent first."
        )

    return self.set_parent(
        task,
        task.parent,
        insert_before=insert_before,
        insert_after=insert_after,
    )
```

## Technical Decisions

No new ADRs required. This design follows established patterns:

| Decision | Pattern Used | Reference |
|----------|--------------|-----------|
| Parent GID storage | extra_params field | ADR-0044 |
| target_gid=None | Optional target for some actions | ADR-0045 |
| Positioning validation | Fail-fast at queue time | ADR-0047 |

## Complexity Assessment

**Level**: Module (minimal extension)

**Justification**:
- 1 new ActionType enum value
- 1 new to_api_call() case
- 2 new SaveSession methods
- Only 2 source files modified
- Estimated 1-2 hours implementation

## Implementation Plan

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 1 | ActionType.SET_PARENT + to_api_call() case | None | 20 min |
| 2 | SaveSession.set_parent() method | Phase 1 | 30 min |
| 3 | SaveSession.reorder_subtask() method | Phase 2 | 15 min |
| 4 | Unit tests | Phases 1-3 | 45 min |

**Total**: 1.5-2 hours

## Files to Modify

| File | Changes |
|------|---------|
| `src/autom8_asana/persistence/models.py` | +1 ActionType, +1 to_api_call() case |
| `src/autom8_asana/persistence/session.py` | +2 methods (set_parent, reorder_subtask) |
| `tests/unit/persistence/test_models.py` | +3 tests for SET_PARENT to_api_call() |
| `tests/unit/persistence/test_session.py` | +6 tests for new methods |

## Testing Strategy

### Unit Tests

| Test | Description |
|------|-------------|
| `test_set_parent_action_type_exists` | SET_PARENT in ActionType enum |
| `test_to_api_call_set_parent_basic` | Generates correct POST /tasks/{gid}/setParent |
| `test_to_api_call_set_parent_with_positioning` | Includes insert_before/insert_after in payload |
| `test_to_api_call_set_parent_promote` | parent: null when promoting to top-level |
| `test_set_parent_queues_action` | ActionOperation created with correct fields |
| `test_set_parent_positioning_conflict` | Raises PositioningConflictError |
| `test_set_parent_returns_self` | Fluent chaining works |
| `test_reorder_subtask_delegates` | Calls set_parent with current parent |
| `test_reorder_subtask_no_parent_error` | ValueError on top-level task |

## Open Questions

None - all design decisions resolved by PRD-0008 and existing ADRs.

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Architect | Initial draft |
