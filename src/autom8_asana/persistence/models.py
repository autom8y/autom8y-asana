"""Data models for Save Orchestration Layer.

Per TDD-0010: Core data structures for entity state tracking,
operation planning, and result reporting.

Per TDD-0011: Action operation types for tag, project, dependency,
and section management via non-batch API endpoints.

Per TDD-TRIAGE-FIXES: Cascade result tracking in SaveResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

from autom8_asana.patterns import RetryableErrorMixin

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.cascade import CascadeResult


class EntityState(Enum):
    """Lifecycle state of a tracked entity.

    Per FR-UOW-008: Track entity lifecycle state.

    States:
        NEW: Entity has no GID or temp GID, will be created via POST
        CLEAN: Entity is tracked but unmodified since last save/track
        MODIFIED: Entity has pending changes that need to be saved
        DELETED: Entity is marked for deletion via DELETE
    """

    NEW = "new"
    CLEAN = "clean"
    MODIFIED = "modified"
    DELETED = "deleted"


class OperationType(Enum):
    """Type of operation to perform.

    Per FR-BATCH-007: Build appropriate BatchRequest per type.

    Operations:
        CREATE: POST request to create new resource
        UPDATE: PUT request to update existing resource
        DELETE: DELETE request to remove resource
    """

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass(frozen=True)
class PlannedOperation:
    """A planned operation returned by preview().

    Per FR-DRY-002: Contains entity, operation type, payload, and
    dependency level for dry-run inspection.

    Attributes:
        entity: The AsanaResource to be operated on
        operation: The type of operation (CREATE, UPDATE, DELETE)
        payload: The data payload to send with the request
        dependency_level: The level in the dependency graph (0 = no deps)
    """

    entity: AsanaResource
    operation: OperationType
    payload: dict[str, Any]
    dependency_level: int

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        entity_type = type(self.entity).__name__
        entity_gid = self.entity.gid
        return (
            f"PlannedOperation({self.operation.value}, "
            f"{entity_type}(gid={entity_gid}), level={self.dependency_level})"
        )


@dataclass
class SaveError(RetryableErrorMixin):
    """Error information for a failed operation.

    Per FR-ERROR-003: Attribute errors to specific entities.
    Per ADR-0079: Provides is_retryable classification and recovery hints.
    Per Initiative DESIGN-PATTERNS-B: Uses RetryableErrorMixin for error classification.

    Attributes:
        entity: The entity that failed to save
        operation: The type of operation that was attempted
        error: The exception that occurred
        payload: The payload that was sent (for debugging)
    """

    entity: AsanaResource
    operation: OperationType
    error: Exception
    payload: dict[str, Any]

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        entity_type = type(self.entity).__name__
        entity_gid = self.entity.gid
        error_type = type(self.error).__name__
        return (
            f"SaveError({self.operation.value}, "
            f"{entity_type}(gid={entity_gid}), {error_type})"
        )

    def _get_error(self) -> Exception | None:
        """Return the error for classification.

        Per RetryableErrorMixin contract: Returns the error to classify.
        SaveError always has an error (required field).

        Returns:
            The exception that caused this save error.
        """
        return self.error


@dataclass
class SaveResult:
    """Result of a commit operation.

    Per FR-ERROR-002: Provides succeeded, failed, and aggregate info.
    Per ADR-0055: Includes action operation results for complete reporting.
    Per TDD-TRIAGE-FIXES: Includes cascade operation results.

    Attributes:
        succeeded: List of entities that were saved successfully (CRUD operations)
        failed: List of SaveError for entities that failed (CRUD operations)
        action_results: List of ActionResult for action operations (tags, projects,
                       dependencies, sections, etc.). Populated after commit.
        cascade_results: List of CascadeResult for cascade operations. Populated after
                        cascade execution during commit.
    """

    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    action_results: list[ActionResult] = field(default_factory=list)
    cascade_results: list[CascadeResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if all operations succeeded (FR-ERROR-002, ADR-0055, TDD-TRIAGE-FIXES).

        Returns:
            True if no CRUD failures, all actions succeeded, and all cascades succeeded.
        """
        crud_ok = len(self.failed) == 0
        actions_ok = all(r.success for r in self.action_results)
        cascades_ok = all(r.success for r in self.cascade_results)
        return crud_ok and actions_ok and cascades_ok

    @property
    def partial(self) -> bool:
        """True if some but not all operations succeeded.

        Returns:
            True if there are both successes and failures.
        """
        return len(self.succeeded) > 0 and len(self.failed) > 0

    @property
    def total_count(self) -> int:
        """Total number of operations attempted.

        Returns:
            Sum of succeeded and failed operation counts.
        """
        return len(self.succeeded) + len(self.failed)

    @property
    def action_succeeded(self) -> int:
        """Count of successful action operations (ADR-0055).

        Returns:
            Number of action operations that succeeded.
        """
        return sum(1 for r in self.action_results if r.success)

    @property
    def action_failed(self) -> int:
        """Count of failed action operations (ADR-0055).

        Returns:
            Number of action operations that failed.
        """
        return sum(1 for r in self.action_results if not r.success)

    @property
    def cascade_succeeded(self) -> int:
        """Count of successful cascade operations (TDD-TRIAGE-FIXES).

        Returns:
            Number of cascade operations that succeeded.
        """
        return sum(1 for r in self.cascade_results if r.success)

    @property
    def cascade_failed(self) -> int:
        """Count of failed cascade operations (TDD-TRIAGE-FIXES).

        Returns:
            Number of cascade operations that failed.
        """
        return sum(1 for r in self.cascade_results if not r.success)

    @property
    def failed_count(self) -> int:
        """Number of failed CRUD operations (FR-FH-007).

        Returns:
            Count of SaveError entries in the failed list.
        """
        return len(self.failed)

    @property
    def retryable_failures(self) -> list[SaveError]:
        """Get errors that may be retried (FR-FH-006).

        Per ADR-0079: Filters failed operations to those with is_retryable=True.

        Returns:
            List of SaveErrors where is_retryable is True.
        """
        return [error for error in self.failed if error.is_retryable]

    @property
    def non_retryable_failures(self) -> list[SaveError]:
        """Get errors that should not be retried.

        Returns:
            List of SaveErrors where is_retryable is False.
        """
        return [error for error in self.failed if not error.is_retryable]

    @property
    def has_retryable_failures(self) -> bool:
        """Check if any failures are retryable.

        Returns:
            True if at least one failed operation is retryable.
        """
        return any(error.is_retryable for error in self.failed)

    def get_failed_entities(self) -> list[AsanaResource]:
        """Get entities that failed to save (FR-FH-005).

        Returns:
            List of entities from failed operations.
        """
        return [error.entity for error in self.failed]

    def get_retryable_errors(self) -> list[SaveError]:
        """Get errors that may be retried (FR-FH-006).

        Alias for retryable_failures property for API consistency with TDD.

        Returns:
            List of SaveErrors where is_retryable is True.
        """
        return self.retryable_failures

    def get_recovery_summary(self) -> str:
        """Generate a summary of all errors with recovery guidance.

        Useful for logging or displaying to users. Groups errors by
        retryability and includes recovery hints.

        Returns:
            Multi-line string summarizing all failures with recovery hints.
        """
        if not self.failed:
            return "No failures."

        lines: list[str] = []
        lines.append(f"Total failures: {self.failed_count}")

        retryable = self.retryable_failures
        non_retryable = self.non_retryable_failures

        if retryable:
            lines.append(f"\nRetryable ({len(retryable)}):")
            for err in retryable:
                entity_type = type(err.entity).__name__
                lines.append(
                    f"  - {entity_type}(gid={err.entity.gid}): {err.recovery_hint}"
                )

        if non_retryable:
            lines.append(f"\nNon-retryable ({len(non_retryable)}):")
            for err in non_retryable:
                entity_type = type(err.entity).__name__
                lines.append(
                    f"  - {entity_type}(gid={err.entity.gid}): {err.recovery_hint}"
                )

        return "\n".join(lines)

    def raise_on_failure(self) -> None:
        """Raise PartialSaveError if any operations failed (FR-ERROR-010).

        Raises:
            PartialSaveError: If any operations failed.
        """
        if self.failed:
            from autom8_asana.persistence.exceptions import PartialSaveError

            raise PartialSaveError(self)

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return (
            f"SaveResult(succeeded={len(self.succeeded)}, failed={len(self.failed)}, "
            f"actions={self.action_succeeded}/{len(self.action_results)})"
        )


# ---------------------------------------------------------------------------
# Action Types (TDD-0011)
# ---------------------------------------------------------------------------


class ActionType(str, Enum):
    """Type of action operation for non-batch API endpoints.

    Per TDD-0011: Action endpoints for relationship management.
    Per TDD-0012: Extended with follower, dependent, like, and comment operations.
    Per TDD-0013: Extended with parent/subtask operations.

    These operations cannot be batched and require individual API calls.
    They manage relationships between tasks and other resources.

    Actions:
        ADD_TAG: Add a tag to a task
        REMOVE_TAG: Remove a tag from a task
        ADD_TO_PROJECT: Add a task to a project
        REMOVE_FROM_PROJECT: Remove a task from a project
        ADD_DEPENDENCY: Add a dependency (task depends on another task)
        REMOVE_DEPENDENCY: Remove a dependency
        MOVE_TO_SECTION: Move a task to a section within a project
        ADD_FOLLOWER: Add a follower (user) to a task
        REMOVE_FOLLOWER: Remove a follower (user) from a task
        ADD_DEPENDENT: Add a dependent task (inverse of add_dependency)
        REMOVE_DEPENDENT: Remove a dependent task
        ADD_LIKE: Like a task (uses authenticated user)
        REMOVE_LIKE: Unlike a task (uses authenticated user)
        ADD_COMMENT: Add a comment/story to a task
        SET_PARENT: Set or change the parent of a task (reparent, promote, reorder)
    """

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
    SET_PARENT = "set_parent"


@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation for non-batch API endpoints.

    Per TDD-0011: Actions are executed via individual API calls after
    CRUD batch operations complete. They manage relationships between
    tasks and other resources (tags, projects, sections, dependencies).

    Per TDD-0012/ADR-0044: Extended with extra_params for positioning.
    Per TDD-0012/ADR-0045: target_gid is optional for some operations.

    Attributes:
        task: The task being acted upon (source of the action).
        action: The type of action to perform.
        target_gid: The GID of the target resource (tag, project, section,
                   or dependency task). May be a temp GID for newly created
                   resources that will be resolved before execution. Optional
                   for follower operations where user GID is in extra_params.
        extra_params: Additional parameters for the action. Used for positioning
                     (insert_before, insert_after) in add_to_project and
                     move_to_section. Also used for follower operations.
    """

    task: AsanaResource
    action: ActionType
    target_gid: str | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)

    def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
        """Convert action to API call parameters.

        Returns:
            Tuple of (HTTP method, endpoint path, payload dict).

        Raises:
            ValueError: If action type is not recognized.
        """
        task_gid = self.task.gid

        match self.action:
            case ActionType.ADD_TAG:
                return (
                    "POST",
                    f"/tasks/{task_gid}/addTag",
                    {"data": {"tag": self.target_gid}},
                )
            case ActionType.REMOVE_TAG:
                return (
                    "POST",
                    f"/tasks/{task_gid}/removeTag",
                    {"data": {"tag": self.target_gid}},
                )
            case ActionType.ADD_TO_PROJECT:
                # Per ADR-0044: Include positioning from extra_params
                data: dict[str, Any] = {"project": self.target_gid}
                if "insert_before" in self.extra_params:
                    data["insert_before"] = self.extra_params["insert_before"]
                if "insert_after" in self.extra_params:
                    data["insert_after"] = self.extra_params["insert_after"]
                return (
                    "POST",
                    f"/tasks/{task_gid}/addProject",
                    {"data": data},
                )
            case ActionType.REMOVE_FROM_PROJECT:
                return (
                    "POST",
                    f"/tasks/{task_gid}/removeProject",
                    {"data": {"project": self.target_gid}},
                )
            case ActionType.ADD_DEPENDENCY:
                return (
                    "POST",
                    f"/tasks/{task_gid}/addDependencies",
                    {"data": {"dependencies": [self.target_gid]}},
                )
            case ActionType.REMOVE_DEPENDENCY:
                return (
                    "POST",
                    f"/tasks/{task_gid}/removeDependencies",
                    {"data": {"dependencies": [self.target_gid]}},
                )
            case ActionType.MOVE_TO_SECTION:
                # Per ADR-0044: Include positioning from extra_params
                section_data: dict[str, Any] = {"task": task_gid}
                if "insert_before" in self.extra_params:
                    section_data["insert_before"] = self.extra_params["insert_before"]
                if "insert_after" in self.extra_params:
                    section_data["insert_after"] = self.extra_params["insert_after"]
                return (
                    "POST",
                    f"/sections/{self.target_gid}/addTask",
                    {"data": section_data},
                )
            case ActionType.ADD_FOLLOWER:
                # Per TDD-0012: Add follower to task
                return (
                    "POST",
                    f"/tasks/{task_gid}/addFollowers",
                    {"data": {"followers": [self.target_gid]}},
                )
            case ActionType.REMOVE_FOLLOWER:
                # Per TDD-0012: Remove follower from task
                return (
                    "POST",
                    f"/tasks/{task_gid}/removeFollowers",
                    {"data": {"followers": [self.target_gid]}},
                )
            case ActionType.ADD_DEPENDENT:
                # Per TDD-0012: Add dependent task (inverse of add_dependency)
                return (
                    "POST",
                    f"/tasks/{task_gid}/addDependents",
                    {"data": {"dependents": [self.target_gid]}},
                )
            case ActionType.REMOVE_DEPENDENT:
                # Per TDD-0012: Remove dependent task
                return (
                    "POST",
                    f"/tasks/{task_gid}/removeDependents",
                    {"data": {"dependents": [self.target_gid]}},
                )
            case ActionType.ADD_LIKE:
                # Per TDD-0012/ADR-0045: No target_gid needed, uses authenticated user
                return (
                    "POST",
                    f"/tasks/{task_gid}/addLike",
                    {"data": {}},
                )
            case ActionType.REMOVE_LIKE:
                # Per TDD-0012/ADR-0045: No target_gid needed, uses authenticated user
                return (
                    "POST",
                    f"/tasks/{task_gid}/removeLike",
                    {"data": {}},
                )
            case ActionType.ADD_COMMENT:
                # Per TDD-0012/ADR-0046: Text stored in extra_params
                comment_data: dict[str, Any] = {"text": self.extra_params.get("text", "")}
                if self.extra_params.get("html_text"):
                    comment_data["html_text"] = self.extra_params["html_text"]
                return (
                    "POST",
                    f"/tasks/{task_gid}/stories",
                    {"data": comment_data},
                )
            case ActionType.SET_PARENT:
                # Per TDD-0013: Parent stored in extra_params (can be None for promote)
                parent_gid = self.extra_params.get("parent")
                parent_data: dict[str, Any] = {"parent": parent_gid}
                if "insert_before" in self.extra_params:
                    parent_data["insert_before"] = self.extra_params["insert_before"]
                if "insert_after" in self.extra_params:
                    parent_data["insert_after"] = self.extra_params["insert_after"]
                return (
                    "POST",
                    f"/tasks/{task_gid}/setParent",
                    {"data": parent_data},
                )
            case _:
                raise ValueError(f"Unknown action type: {self.action}")

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        task_type = type(self.task).__name__
        task_gid = self.task.gid
        return (
            f"ActionOperation({self.action.value}, "
            f"{task_type}(gid={task_gid}), target={self.target_gid})"
        )


@dataclass
class ActionResult(RetryableErrorMixin):
    """Result of an action operation execution.

    Per TDD-0011: Track success/failure of individual action operations.
    Per ADR-0079: Enhanced with retryable error classification.
    Per Initiative DESIGN-PATTERNS-B: Uses RetryableErrorMixin for error classification.

    Attributes:
        action: The ActionOperation that was executed.
        success: Whether the action succeeded.
        error: The exception if the action failed, None otherwise.
        response_data: API response data on success, None on failure.
    """

    action: ActionOperation
    success: bool
    error: Exception | None = None
    response_data: dict[str, Any] | None = None

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        status = "success" if self.success else "failed"
        return f"ActionResult({self.action.action.value}, {status})"

    def _get_error(self) -> Exception | None:
        """Return the error for classification.

        Per RetryableErrorMixin contract: Returns the error to classify.
        Returns None for successful actions (is_retryable will be False).

        Returns:
            The exception if action failed, None if successful.
        """
        if self.success:
            return None
        return self.error
