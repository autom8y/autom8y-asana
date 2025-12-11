# PRD: Parent & Subtask Operations

## Metadata
- **PRD ID**: PRD-0008
- **Status**: Draft
- **Version**: 1.0
- **Author**: Requirements Analyst
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **Stakeholders**: autom8 team, SDK consumers, workflow automation developers
- **Related PRDs**:
  - [PRD-0007](PRD-0007-sdk-functional-parity.md) (SDK Functional Parity - completed prerequisite)
  - [PRD-0005](PRD-0005-save-orchestration.md) (Save Orchestration Layer - foundation)
- **Related TDDs**:
  - TDD-0012 (SDK Functional Parity - implementation reference)
- **Related ADRs**:
  - [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) (Unit of Work Pattern)
  - [ADR-0047](../decisions/ADR-0047-positioning-validation-timing.md) (Positioning Validation Timing)

---

## Problem Statement

With PRD-0007 complete and 7 ActionTypes implemented, users cannot reparent tasks or reorder subtasks through the SaveSession Unit of Work pattern. These operations require direct API calls, losing type safety and consistency with other SDK operations.

**Current Gap**:

| Operation | Asana API | SaveSession Support |
|-----------|-----------|---------------------|
| Convert task to subtask | `POST /tasks/{gid}/setParent` | Not supported |
| Promote subtask to top-level | `POST /tasks/{gid}/setParent` with `parent: null` | Not supported |
| Move subtask to different parent | `POST /tasks/{gid}/setParent` | Not supported |
| Reorder subtask within parent | `POST /tasks/{gid}/setParent` with positioning | Not supported |

**Current Workaround**:
```python
# Developers must exit SaveSession for reparenting
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)
    task.name = "Updated"
    await session.commit_async()

# Separate call outside SaveSession - loses deferred execution benefits
await client.http._request(
    "POST",
    f"/tasks/{task.gid}/setParent",
    json={"data": {"parent": "new_parent_gid"}}
)
```

**Impact of Not Solving**:
1. Developers bypass SaveSession for common parent/subtask operations
2. Loss of type safety when making raw API calls
3. Inconsistent execution model (some ops deferred, some immediate)
4. Cannot atomically update task properties and reparent in same session

---

## Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API coverage | 100% of setParent operations | Endpoint audit |
| New method count | 2 methods (`set_parent`, `reorder_subtask`) | API surface review |
| Backward compatibility | 0 regressions | All existing tests pass |
| Type safety | 100% mypy strict compliance | CI mypy check |
| Documentation coverage | 100% of new methods documented | Docstring audit |

---

## Scope

### In Scope

**Core Operations**:
- `set_parent(task, parent)` - Set parent task (convert to subtask)
- `set_parent(task, None)` - Remove parent (promote to top-level)
- `reorder_subtask(task, insert_before=..., insert_after=...)` - Reorder within current parent

**Positioning Support**:
- `insert_before` parameter for positioning before sibling
- `insert_after` parameter for positioning after sibling

**ActionType**:
- Single `SET_PARENT` ActionType for all parent operations

### Out of Scope

**Explicitly Excluded**:
- `duplicate_task()` - Does not fit deferred execution pattern (returns new GID immediately, may require file handles for attachments)
- Section reordering within projects - Different API endpoint (`POST /projects/{gid}/sections/insert`)
- Bulk reparenting operations - Can be achieved via multiple `set_parent()` calls
- `POST /tasks/{gid}/subtasks` for subtask creation - Already handled via `parent` field in standard CRUD

---

## Requirements

### Functional Requirements (FR-PAR-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-PAR-001 | `set_parent()` shall accept task and parent parameters | Must | `set_parent(task, parent_task)` queues SET_PARENT action |
| FR-PAR-002 | `set_parent()` shall accept `None` as parent to promote subtask | Must | `set_parent(task, None)` queues action with `parent: null` in payload |
| FR-PAR-003 | `set_parent()` shall support `insert_before` positioning | Must | Parameter accepts Task, NameGid, or GID string |
| FR-PAR-004 | `set_parent()` shall support `insert_after` positioning | Must | Parameter accepts Task, NameGid, or GID string |
| FR-PAR-005 | SDK shall raise `PositioningConflictError` when both `insert_before` and `insert_after` specified | Must | Reuse existing exception from PRD-0007 |
| FR-PAR-006 | `reorder_subtask()` shall reorder within current parent | Must | Calls `set_parent()` with task's current parent |
| FR-PAR-007 | `reorder_subtask()` shall raise `ValueError` if task has no parent | Must | Error message: "Cannot reorder task without parent. Use set_parent() to assign a parent first." |
| FR-PAR-008 | `SET_PARENT` ActionType shall be added to enum | Must | Single ActionType handles all parent operations |
| FR-PAR-009 | `to_api_call()` shall generate correct `POST /tasks/{gid}/setParent` | Must | Payload includes `parent` (GID or null) and optional positioning |
| FR-PAR-010 | Operations shall be deferred until `commit()` | Must | No API calls made until commit is called |
| FR-PAR-011 | `set_parent()` shall return self for fluent chaining | Should | `session.set_parent(a, b).set_parent(c, d)` chains correctly |
| FR-PAR-012 | Methods shall accept Task model or GID string for task parameter | Must | Both input types work correctly |
| FR-PAR-013 | Methods shall support temp GID resolution for newly-created tasks | Must | Temp GIDs resolved before API call |

### Non-Functional Requirements (NFR-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | 100% mypy strict compliance | 0 errors | CI mypy --strict |
| NFR-002 | All new methods have docstrings | 100% coverage | Docstring audit |
| NFR-003 | Backward compatible with existing SaveSession usage | 0 breaking changes | API diff analysis |
| NFR-004 | Individual set_parent operation | < 500ms p95 | Profiler excluding network |

---

## User Stories

### US-001: Convert Task to Subtask

As a workflow automation developer, I want to convert a top-level task to a subtask so that I can organize tasks hierarchically through SaveSession.

**Scenario**:
```python
async with SaveSession(client) as session:
    task = await client.tasks.get_async("task_gid")
    parent = await client.tasks.get_async("parent_gid")

    session.set_parent(task, parent)
    result = await session.commit_async()
```

**Acceptance**: Task becomes subtask of parent via `POST /tasks/{gid}/setParent`.

### US-002: Promote Subtask to Top-Level Task

As a workflow automation developer, I want to promote a subtask back to a top-level task so that it appears independently in project views.

**Scenario**:
```python
async with SaveSession(client) as session:
    subtask = await client.tasks.get_async("subtask_gid")

    session.set_parent(subtask, None)  # Promote to top-level
    result = await session.commit_async()
```

**Acceptance**: Subtask becomes top-level task via `POST /tasks/{gid}/setParent` with `parent: null`.

### US-003: Reorder Subtasks Within Parent

As a workflow automation developer, I want to reorder subtasks within their parent so that the subtask list reflects priority order.

**Scenario**:
```python
async with SaveSession(client) as session:
    # Move urgent_subtask to top of subtask list
    session.reorder_subtask(urgent_subtask, insert_before=first_subtask)

    # Move completed_subtask to bottom
    session.reorder_subtask(completed_subtask, insert_after=last_subtask)

    result = await session.commit_async()
```

**Acceptance**: Subtasks reordered within parent; uses current parent GID automatically.

---

## Acceptance Criteria

### FR-PAR-001: set_parent accepts task and parent
- **Given** a tracked task and parent task
- **When** `session.set_parent(task, parent)` is called
- **Then** SET_PARENT action is queued with task GID and parent GID

### FR-PAR-002: set_parent with None promotes subtask
- **Given** a subtask with existing parent
- **When** `session.set_parent(subtask, None)` is called
- **Then** SET_PARENT action is queued with `parent: null` in payload

### FR-PAR-003/004: Positioning parameters
- **Given** a task being reparented
- **When** `session.set_parent(task, parent, insert_after=sibling)` is called
- **Then** `insert_after` is included in API payload

### FR-PAR-005: Positioning conflict detection
- **Given** both `insert_before` and `insert_after` are specified
- **When** `session.set_parent(task, parent, insert_before=a, insert_after=b)` is called
- **Then** `PositioningConflictError` is raised immediately

### FR-PAR-006: reorder_subtask uses current parent
- **Given** a subtask with parent GID "parent_123"
- **When** `session.reorder_subtask(subtask, insert_after=sibling)` is called
- **Then** SET_PARENT action is queued with `parent: "parent_123"`

### FR-PAR-007: reorder_subtask requires parent
- **Given** a top-level task with no parent
- **When** `session.reorder_subtask(task, insert_after=other)` is called
- **Then** `ValueError` is raised with descriptive message

### FR-PAR-009: Correct API call generation
- **Given** a queued SET_PARENT action with parent "p_123" and insert_after "s_456"
- **When** `to_api_call()` is called
- **Then** Returns POST to `/tasks/{gid}/setParent` with body `{"data": {"parent": "p_123", "insert_after": "s_456"}}`

### FR-PAR-010: Deferred execution
- **Given** `session.set_parent(task, parent)` is called
- **When** No commit has been called
- **Then** No HTTP request is made

---

## Design Decisions

### Decision 1: Single SET_PARENT ActionType

**Decision**: Use one `SET_PARENT` ActionType for all parent operations (set, clear, reorder).

**Rationale**: The Asana API uses a single endpoint (`POST /tasks/{gid}/setParent`) for all these operations. The `parent` field value (GID or null) and positioning parameters determine the specific behavior. Multiple ActionTypes would add complexity without benefit.

### Decision 2: reorder_subtask as Convenience Method

**Decision**: `reorder_subtask()` is a convenience wrapper that calls `set_parent()` with the task's current parent.

**Rationale**: This provides a clearer API for the common case of reordering without changing parent, while keeping the implementation simple. Developers don't need to manually track and pass the current parent GID.

### Decision 3: Reuse PositioningConflictError

**Decision**: Reuse the existing `PositioningConflictError` from PRD-0007 for positioning validation.

**Rationale**: The error semantics are identical (both `insert_before` and `insert_after` specified is always invalid). Reusing the exception maintains consistency and reduces API surface.

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| `setParent` accepts null for parent to promote subtask | Asana API documentation |
| `insert_before` and `insert_after` are mutually exclusive | Asana API behavior; same as other positioning endpoints |
| Task's current parent is accessible via `task.parent.gid` | Existing Task model structure |
| Action endpoints remain non-batch-eligible | Confirmed in PRD-0006 |

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| SaveSession (PRD-0005) | autom8 team | Complete | Foundation layer |
| ActionExecutor (PRD-0006/0007) | autom8 team | Complete | 7 ActionTypes implemented |
| PositioningConflictError | autom8 team | Complete | Defined in PRD-0007 |
| Task model with parent field | autom8 team | Complete | `src/autom8_asana/models/task.py` |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-001: reorder_subtask on stale parent data | Incorrect ordering | Medium | Document that task should be freshly fetched; consider validation |
| R-002: Circular parent relationships | API error | Low | Asana API validates; surface error clearly |

---

## Open Questions

None - all design decisions confirmed by user.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Requirements Analyst | Initial draft |

---

## Appendix A: Asana API Reference

### setParent Endpoint

```
POST /tasks/{task_gid}/setParent

Request Body:
{
    "data": {
        "parent": "parent_task_gid",  // Required: new parent GID or null
        "insert_before": "sibling_gid", // Optional: position before sibling
        "insert_after": "sibling_gid"   // Optional: position after sibling
    }
}

Response:
{
    "data": {
        "gid": "task_gid",
        "name": "Task Name",
        "parent": {
            "gid": "parent_task_gid",
            "name": "Parent Task"
        },
        ...
    }
}
```

### Use Cases

| Use Case | parent | insert_before | insert_after |
|----------|--------|---------------|--------------|
| Convert to subtask | parent_gid | - | - |
| Promote to top-level | null | - | - |
| Move to different parent | new_parent_gid | - | - |
| Reorder within parent | current_parent_gid | sibling_gid | - |
| Reorder within parent | current_parent_gid | - | sibling_gid |

---

## Appendix B: New Method Signatures

```python
class SaveSession:
    def set_parent(
        self,
        task: Task | str,
        parent: Task | NameGid | str | None,
        *,
        insert_before: Task | NameGid | str | None = None,
        insert_after: Task | NameGid | str | None = None,
    ) -> SaveSession:
        """Set or clear the parent of a task.

        Use this to:
        - Convert a task to a subtask: set_parent(task, parent_task)
        - Promote a subtask to top-level: set_parent(task, None)
        - Move subtask to different parent: set_parent(task, new_parent)
        - Position within siblings: set_parent(task, parent, insert_after=sibling)

        Args:
            task: Task entity or GID string.
            parent: Parent task, NameGid, GID string, or None to remove parent.
            insert_before: Position before this sibling (mutually exclusive with insert_after).
            insert_after: Position after this sibling (mutually exclusive with insert_before).

        Returns:
            Self for fluent chaining.

        Raises:
            PositioningConflictError: If both insert_before and insert_after specified.
            SessionClosedError: If session is closed.

        Example:
            # Convert task to subtask
            session.set_parent(task, parent_task)

            # Promote subtask to top-level
            session.set_parent(subtask, None)

            # Reparent with positioning
            session.set_parent(task, new_parent, insert_after=first_sibling)
        """
        ...

    def reorder_subtask(
        self,
        task: Task | str,
        *,
        insert_before: Task | NameGid | str | None = None,
        insert_after: Task | NameGid | str | None = None,
    ) -> SaveSession:
        """Reorder a subtask within its current parent.

        Convenience method that calls set_parent() with the task's current parent.
        At least one of insert_before or insert_after must be specified.

        Args:
            task: Task entity or GID string (must have a parent).
            insert_before: Position before this sibling (mutually exclusive with insert_after).
            insert_after: Position after this sibling (mutually exclusive with insert_before).

        Returns:
            Self for fluent chaining.

        Raises:
            ValueError: If task has no parent.
            PositioningConflictError: If both insert_before and insert_after specified.
            SessionClosedError: If session is closed.

        Example:
            # Move urgent subtask to top of list
            session.reorder_subtask(urgent, insert_before=first_subtask)
        """
        ...
```

---

## Appendix C: ActionType Addition

```python
class ActionType(str, Enum):
    # Existing (PRD-0006/0007)
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MOVE_TO_SECTION = "move_to_section"
    ADD_FOLLOWER = "add_follower"
    REMOVE_FOLLOWER = "remove_follower"
    ADD_DEPENDENT = "add_dependent"
    REMOVE_DEPENDENT = "remove_dependent"
    ADD_LIKE = "add_like"
    REMOVE_LIKE = "remove_like"
    ADD_COMMENT = "add_comment"

    # New (PRD-0008)
    SET_PARENT = "set_parent"
```

---

## Appendix D: Traceability Matrix

| Requirement | Implementation Component | Test File |
|-------------|--------------------------|-----------|
| FR-PAR-001 | `SaveSession.set_parent()` | `test_parent_operations.py` |
| FR-PAR-002 | `SaveSession.set_parent()` | `test_parent_operations.py` |
| FR-PAR-003 | `SaveSession.set_parent()` | `test_parent_operations.py` |
| FR-PAR-004 | `SaveSession.set_parent()` | `test_parent_operations.py` |
| FR-PAR-005 | `PositioningConflictError` | `test_parent_operations.py` |
| FR-PAR-006 | `SaveSession.reorder_subtask()` | `test_parent_operations.py` |
| FR-PAR-007 | `SaveSession.reorder_subtask()` | `test_parent_operations.py` |
| FR-PAR-008 | `ActionType.SET_PARENT` | `test_action_types.py` |
| FR-PAR-009 | `ActionOperation.to_api_call()` | `test_parent_operations.py` |
| FR-PAR-010 | Deferred execution | `test_parent_operations.py` |
| NFR-001 | All new methods | `mypy --strict` |
| NFR-003 | Existing tests | CI test suite |
