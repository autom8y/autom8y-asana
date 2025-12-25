# TDD-0012: SDK Functional Parity Initiative

## Metadata
- **TDD ID**: TDD-0012
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **PRD Reference**: [PRD-0007](../requirements/PRD-0007-sdk-functional-parity.md)
- **Related TDDs**:
  - [TDD-0010](TDD-0010-save-orchestration.md) - Save Orchestration Layer (foundation)
  - [TDD-0011](TDD-0011-action-endpoint-support.md) - Action Endpoint Support (current implementation)
- **Related ADRs**:
  - [ADR-0042](../decisions/ADR-0042-action-operation-types.md) - Separate ActionType Enum
  - [ADR-0044](../decisions/ADR-0044-extra-params-field.md) - extra_params Field Design
  - [ADR-0045](../decisions/ADR-0045-like-operations-without-target.md) - Like Operations Without Target GID
  - [ADR-0046](../decisions/ADR-0046-comment-text-storage.md) - Comment Text Storage Strategy
  - [ADR-0047](../decisions/ADR-0047-positioning-validation-timing.md) - Positioning Validation Timing

## Overview

This design extends the Save Orchestration Layer (TDD-0010) and Action Endpoint Support (TDD-0011) to achieve functional parity with Asana's task action API endpoints. The extension adds 7 new ActionTypes (followers, dependents, likes, comments), extends ActionOperation with an `extra_params` field for positioning and comment text storage, and introduces a `PositioningConflictError` for fail-fast validation. All changes follow existing patterns exactly, requiring modifications to only 4 source files.

## Requirements Summary

This design addresses [PRD-0007](../requirements/PRD-0007-sdk-functional-parity.md) v1.0, which defines:

- **53 functional requirements** across Positioning (FR-POS-*), Followers (FR-FOL-*), Dependents (FR-DEP-*), Likes (FR-LIK-*), Comments (FR-CMT-*), and Error Handling (FR-ERR-*) domains
- **16 non-functional requirements** covering type safety (NFR-TYPE-*), performance (NFR-PERF-*), reliability (NFR-REL-*), and backward compatibility (NFR-COMPAT-*)
- **Key constraints**: One ActionOperation per follower, deferred comment execution, fail-fast positioning validation, backward-compatible method signatures

Key requirements driving this design:

| Requirement | Summary | Design Impact |
|-------------|---------|---------------|
| FR-FOL-001 | `add_follower(task, user)` method | New SaveSession method + ADD_FOLLOWER ActionType |
| FR-DEP-001 | `add_dependent(task, dependent_task)` method | New SaveSession method + ADD_DEPENDENT ActionType |
| FR-LIK-001 | `add_like(task)` without user parameter | ADD_LIKE ActionType with target_gid=None |
| FR-CMT-001 | `add_comment(task, text)` with deferred execution | ADD_COMMENT ActionType with text in extra_params |
| FR-POS-001 | `add_to_project()` with `insert_before` parameter | extra_params field on ActionOperation |
| FR-POS-003 | Raise error when both positioning params specified | PositioningConflictError exception |

## System Context

The SDK Functional Parity extension integrates seamlessly with existing Save Orchestration infrastructure:

```
+-----------------------------------------------------------------------------+
|                              EXISTING INFRASTRUCTURE                         |
+-----------------------------------------------------------------------------+

                            +------------------------+
                            |    SDK Consumers       |
                            |  (autom8, services)    |
                            +-----------+------------+
                                        |
                           async with SaveSession(client):
                               session.add_follower(task, user)
                               session.add_comment(task, "Hello")
                               session.add_to_project(task, proj, insert_after=other)
                               await session.commit()
                                        |
                                        v
+-----------------------------------------------------------------------------+
|                         Save Orchestration Layer                             |
|                                                                              |
|  +------------------------------------------------------------------+       |
|  |                    SaveSession (EXTENDED)                         |       |
|  |  - add_follower(), remove_follower()      # NEW                  |       |
|  |  - add_followers(), remove_followers()    # NEW                  |       |
|  |  - add_dependent(), remove_dependent()    # NEW                  |       |
|  |  - add_like(), remove_like()              # NEW                  |       |
|  |  - add_comment()                          # NEW                  |       |
|  |  - add_to_project(..., insert_before=, insert_after=)  # EXTENDED|       |
|  |  - move_to_section(..., insert_before=, insert_after=) # EXTENDED|       |
|  +------------------------------------------------------------------+       |
|                                        |                                     |
|                                        v                                     |
|  +------------------------------------------------------------------+       |
|  |              ActionOperation (EXTENDED)                           |       |
|  |  + extra_params: dict[str, Any]   # NEW                          |       |
|  |  + target_gid: str | None         # CHANGED (was required)       |       |
|  +------------------------------------------------------------------+       |
|                                        |                                     |
|                                        v                                     |
|  +------------------------------------------------------------------+       |
|  |                    ActionExecutor (UNCHANGED)                     |       |
|  |  - execute_async(actions, gid_map)                               |       |
|  |  - Uses ActionOperation.to_api_call()                            |       |
|  +------------------------------------------------------------------+       |
+-----------------------------------------------------------------------------+
```

## Design

### Component Architecture

No new components. Extensions to existing components only.

| Component | Changes | Owner |
|-----------|---------|-------|
| `ActionType` enum | +7 new values | persistence/models.py |
| `ActionOperation` dataclass | +extra_params field, target_gid optional | persistence/models.py |
| `SaveSession` class | +9 new methods, 2 extended methods | persistence/session.py |
| `UNSUPPORTED_FIELDS` dict | +"followers" entry | persistence/pipeline.py |
| `PositioningConflictError` | NEW exception class | persistence/exceptions.py |

### Data Model Changes

#### ActionType Enum Extension

```python
class ActionType(str, Enum):
    # Existing (TDD-0011)
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MOVE_TO_SECTION = "move_to_section"

    # New (TDD-0012)
    ADD_FOLLOWER = "add_follower"
    REMOVE_FOLLOWER = "remove_follower"
    ADD_DEPENDENT = "add_dependent"
    REMOVE_DEPENDENT = "remove_dependent"
    ADD_LIKE = "add_like"
    REMOVE_LIKE = "remove_like"
    ADD_COMMENT = "add_comment"
```

#### ActionOperation Dataclass Extension

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class ActionOperation:
    """Represents a single action to be executed via Asana action endpoints.

    Attributes:
        task: The task entity this action operates on.
        action: The type of action (ADD_FOLLOWER, ADD_LIKE, etc.).
        target_gid: The GID of the target entity (user, task, project, etc.).
                   Optional for like operations which use authenticated user.
        extra_params: Additional parameters for the API call (positioning, comment text).
    """
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None  # Changed: Optional for likes
    extra_params: dict[str, Any] = field(default_factory=dict)  # NEW

    def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
        """Generate the HTTP method, endpoint path, and payload for this action."""
        task_gid = self.task.gid if hasattr(self.task, 'gid') else str(self.task)

        match self.action:
            # Existing cases (unchanged except ADD_TO_PROJECT, MOVE_TO_SECTION)
            case ActionType.ADD_TAG:
                return ("POST", f"/tasks/{task_gid}/addTag",
                        {"data": {"tag": self.target_gid}})
            case ActionType.REMOVE_TAG:
                return ("POST", f"/tasks/{task_gid}/removeTag",
                        {"data": {"tag": self.target_gid}})
            case ActionType.ADD_TO_PROJECT:
                payload: dict[str, Any] = {"data": {"project": self.target_gid}}
                if self.extra_params.get("insert_before"):
                    payload["data"]["insert_before"] = self.extra_params["insert_before"]
                if self.extra_params.get("insert_after"):
                    payload["data"]["insert_after"] = self.extra_params["insert_after"]
                return ("POST", f"/tasks/{task_gid}/addProject", payload)
            case ActionType.REMOVE_FROM_PROJECT:
                return ("POST", f"/tasks/{task_gid}/removeProject",
                        {"data": {"project": self.target_gid}})
            case ActionType.ADD_DEPENDENCY:
                return ("POST", f"/tasks/{task_gid}/addDependencies",
                        {"data": {"dependencies": [self.target_gid]}})
            case ActionType.REMOVE_DEPENDENCY:
                return ("POST", f"/tasks/{task_gid}/removeDependencies",
                        {"data": {"dependencies": [self.target_gid]}})
            case ActionType.MOVE_TO_SECTION:
                payload = {"data": {"task": task_gid}}
                if self.extra_params.get("insert_before"):
                    payload["data"]["insert_before"] = self.extra_params["insert_before"]
                if self.extra_params.get("insert_after"):
                    payload["data"]["insert_after"] = self.extra_params["insert_after"]
                return ("POST", f"/sections/{self.target_gid}/addTask", payload)

            # New cases (TDD-0012)
            case ActionType.ADD_FOLLOWER:
                return ("POST", f"/tasks/{task_gid}/addFollowers",
                        {"data": {"followers": [self.target_gid]}})
            case ActionType.REMOVE_FOLLOWER:
                return ("POST", f"/tasks/{task_gid}/removeFollowers",
                        {"data": {"followers": [self.target_gid]}})
            case ActionType.ADD_DEPENDENT:
                return ("POST", f"/tasks/{task_gid}/addDependents",
                        {"data": {"dependents": [self.target_gid]}})
            case ActionType.REMOVE_DEPENDENT:
                return ("POST", f"/tasks/{task_gid}/removeDependents",
                        {"data": {"dependents": [self.target_gid]}})
            case ActionType.ADD_LIKE:
                return ("POST", f"/tasks/{task_gid}/addLike",
                        {"data": {}})
            case ActionType.REMOVE_LIKE:
                return ("POST", f"/tasks/{task_gid}/removeLike",
                        {"data": {}})
            case ActionType.ADD_COMMENT:
                comment_data: dict[str, Any] = {"text": self.extra_params.get("text", "")}
                if self.extra_params.get("html_text"):
                    comment_data["html_text"] = self.extra_params["html_text"]
                return ("POST", f"/tasks/{task_gid}/stories",
                        {"data": comment_data})
            case _:
                raise ValueError(f"Unknown action type: {self.action}")
```

### API Contracts

#### New SaveSession Methods

```python
class SaveSession:
    # --- Follower Methods ---

    def add_follower(
        self,
        task: Task | str,
        user: User | NameGid | str,
    ) -> SaveSession:
        """Add a follower to a task.

        Args:
            task: Task entity or GID string.
            user: User entity, NameGid, or user GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
        """
        self._ensure_open()
        user_gid = user if isinstance(user, str) else user.gid
        action = ActionOperation(
            task=task if isinstance(task, AsanaResource) else self._resolve_task(task),
            action=ActionType.ADD_FOLLOWER,
            target_gid=user_gid,
        )
        self._pending_actions.append(action)
        return self

    def remove_follower(
        self,
        task: Task | str,
        user: User | NameGid | str,
    ) -> SaveSession:
        """Remove a follower from a task."""
        # Same pattern as add_follower with REMOVE_FOLLOWER
        ...

    def add_followers(
        self,
        task: Task | str,
        users: list[User | NameGid | str],
    ) -> SaveSession:
        """Add multiple followers. Creates one ActionOperation per user."""
        for user in users:
            self.add_follower(task, user)
        return self

    def remove_followers(
        self,
        task: Task | str,
        users: list[User | NameGid | str],
    ) -> SaveSession:
        """Remove multiple followers."""
        for user in users:
            self.remove_follower(task, user)
        return self

    # --- Dependent Methods ---

    def add_dependent(
        self,
        task: Task | str,
        dependent_task: Task | str,
    ) -> SaveSession:
        """Add a task as dependent (it depends on this task).

        This is the inverse of add_dependency. After this call,
        dependent_task will be blocked until task is completed.

        Args:
            task: Task entity or GID (the prerequisite task).
            dependent_task: Task entity or GID (the task that depends on this one).
        """
        self._ensure_open()
        dep_gid = dependent_task if isinstance(dependent_task, str) else dependent_task.gid
        action = ActionOperation(
            task=task if isinstance(task, AsanaResource) else self._resolve_task(task),
            action=ActionType.ADD_DEPENDENT,
            target_gid=dep_gid,
        )
        self._pending_actions.append(action)
        return self

    def remove_dependent(
        self,
        task: Task | str,
        dependent_task: Task | str,
    ) -> SaveSession:
        """Remove a task as dependent."""
        # Same pattern with REMOVE_DEPENDENT
        ...

    # --- Like Methods ---

    def add_like(self, task: Task | str) -> SaveSession:
        """Like a task as the current authenticated user.

        No user parameter needed; uses OAuth token's user.
        Liking an already-liked task is idempotent (no error).
        """
        self._ensure_open()
        action = ActionOperation(
            task=task if isinstance(task, AsanaResource) else self._resolve_task(task),
            action=ActionType.ADD_LIKE,
            target_gid=None,  # No target needed for likes
        )
        self._pending_actions.append(action)
        return self

    def remove_like(self, task: Task | str) -> SaveSession:
        """Unlike a task. Idempotent (no error if not liked)."""
        # Same pattern with REMOVE_LIKE
        ...

    # --- Comment Methods ---

    def add_comment(
        self,
        task: Task | str,
        text: str,
        *,
        html_text: str | None = None,
    ) -> SaveSession:
        """Add a comment to a task.

        Comments are created via deferred execution. The comment
        will be created when commit() is called.

        Args:
            task: Task entity or GID string.
            text: Plain text comment content.
            html_text: Optional rich text in Asana's HTML format.

        Raises:
            ValueError: If text is empty and html_text is None.
            SessionClosedError: If session is closed.
        """
        self._ensure_open()
        if not text and not html_text:
            raise ValueError("Comment must have text or html_text")

        task_entity = task if isinstance(task, AsanaResource) else self._resolve_task(task)
        action = ActionOperation(
            task=task_entity,
            action=ActionType.ADD_COMMENT,
            target_gid=task_entity.gid if hasattr(task_entity, 'gid') else task,
            extra_params={"text": text, "html_text": html_text},
        )
        self._pending_actions.append(action)
        return self

    # --- Extended Methods with Positioning ---

    def add_to_project(
        self,
        task: Task | str,
        project: Project | NameGid | str,
        *,
        insert_before: Task | NameGid | str | None = None,
        insert_after: Task | NameGid | str | None = None,
    ) -> SaveSession:
        """Add a task to a project with optional positioning.

        Args:
            task: Task entity or GID string.
            project: Project entity, NameGid, or GID string.
            insert_before: Position task before this task (mutually exclusive).
            insert_after: Position task after this task (mutually exclusive).

        Raises:
            PositioningConflictError: If both insert_before and insert_after specified.
            SessionClosedError: If session is closed.
        """
        self._ensure_open()

        # Validate positioning parameters
        if insert_before is not None and insert_after is not None:
            before_gid = insert_before if isinstance(insert_before, str) else insert_before.gid
            after_gid = insert_after if isinstance(insert_after, str) else insert_after.gid
            raise PositioningConflictError(before_gid, after_gid)

        project_gid = project if isinstance(project, str) else project.gid

        extra_params: dict[str, Any] = {}
        if insert_before is not None:
            extra_params["insert_before"] = insert_before if isinstance(insert_before, str) else insert_before.gid
        if insert_after is not None:
            extra_params["insert_after"] = insert_after if isinstance(insert_after, str) else insert_after.gid

        action = ActionOperation(
            task=task if isinstance(task, AsanaResource) else self._resolve_task(task),
            action=ActionType.ADD_TO_PROJECT,
            target_gid=project_gid,
            extra_params=extra_params,
        )
        self._pending_actions.append(action)
        return self

    def move_to_section(
        self,
        task: Task | str,
        section: Section | NameGid | str,
        *,
        insert_before: Task | NameGid | str | None = None,
        insert_after: Task | NameGid | str | None = None,
    ) -> SaveSession:
        """Move a task to a section with optional positioning."""
        # Same pattern as add_to_project with MOVE_TO_SECTION
        ...
```

#### New Exception

```python
class PositioningConflictError(SaveOrchestrationError):
    """Raised when both insert_before and insert_after are specified.

    Attributes:
        insert_before: The insert_before value that was provided.
        insert_after: The insert_after value that was provided.
    """

    def __init__(
        self,
        insert_before: str,
        insert_after: str,
    ) -> None:
        self.insert_before = insert_before
        self.insert_after = insert_after
        super().__init__(
            "Cannot specify both insert_before and insert_after. "
            f"Got insert_before={insert_before}, insert_after={insert_after}"
        )
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| extra_params storage | `dict[str, Any]` with default_factory | Flexible, type-safe at runtime, frozen-compatible | ADR-0044 |
| Like target_gid | `Optional[str]` (None for likes) | Simpler than sentinel value, explicit intent | ADR-0045 |
| Comment text storage | Via extra_params | Consistent with positioning, no new dataclass | ADR-0046 |
| Positioning validation | Fail-fast at queue time | Better DX than late commit-time errors | ADR-0047 |

## Complexity Assessment

**Level**: Module (extension to existing service)

**Justification**:
- No new infrastructure components
- All changes follow established patterns exactly
- Only 4 source files modified
- Estimated 7-8 hours implementation

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 1 | ActionType enum +7 values, to_api_call() +7 cases | None | 1 hour |
| 2 | ActionOperation +extra_params, target_gid optional | Phase 1 | 30 min |
| 3 | Follower methods (4 methods) | Phases 1-2 | 1 hour |
| 4 | Dependent methods (2 methods) | Phases 1-2 | 30 min |
| 5 | Like methods (2 methods) | Phases 1-2 | 30 min |
| 6 | Comment method | Phases 1-2 | 30 min |
| 7 | Positioning extensions (2 methods) | Phases 1-2 | 1 hour |
| 8 | PositioningConflictError | None | 15 min |
| 9 | UNSUPPORTED_FIELDS update | None | 5 min |
| 10 | Unit tests | Phases 1-9 | 2-3 hours |

**Total**: 7-8 hours

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Frozen dataclass with mutable default | High | Medium | Use `field(default_factory=dict)` |
| Breaking existing tests | High | Low | Run full test suite after each change |
| API payload format differences | Medium | Low | Verify against Asana API documentation |
| Temp GID resolution edge cases | Medium | Medium | Comprehensive integration tests |

## Observability

No new observability requirements. Existing logging and metrics cover new action types automatically through ActionExecutor.

## Testing Strategy

### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `test_models.py` | ActionType enum values, to_api_call() for all 14 action types |
| `test_session.py` | All 9 new methods + 2 extended methods |
| `test_exceptions.py` | PositioningConflictError |

### Integration Tests

| Test File | Coverage |
|-----------|----------|
| `test_live_api.py` | Full round-trip for followers, dependents, likes, comments, positioning |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All questions resolved in PRD-0007 |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Architect | Initial draft |
