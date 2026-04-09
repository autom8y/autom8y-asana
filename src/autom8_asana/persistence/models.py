"""Data models for Save Orchestration Layer.

Per TDD-0010: Core data structures for entity state tracking,
operation planning, and result reporting.

Per TDD-0011: Action operation types for tag, project, dependency,
and section management via non-batch API endpoints.

Per TDD-TRIAGE-FIXES: Cascade result tracking in SaveResult.

Per TDD-DETECTION/ADR-0095: Self-healing models for entity repair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import TYPE_CHECKING, Any

from autom8_asana.patterns import RetryableErrorMixin

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.models.common import NameGid
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
    Per TDD-DETECTION/ADR-0095: Includes healing operation report.
    Per TDD-AUTOMATION-LAYER/FR-007: Includes automation operation results.

    Attributes:
        succeeded: List of entities that were saved successfully (CRUD operations)
        failed: List of SaveError for entities that failed (CRUD operations)
        action_results: List of ActionResult for action operations (tags, projects,
                       dependencies, sections, etc.). Populated after commit.
        cascade_results: List of CascadeResult for cascade operations. Populated after
                        cascade execution during commit.
        healing_report: Report of self-healing operations. Populated when auto_heal=True.
        automation_results: List of AutomationResult for automation rule executions.
                           Populated after Phase 5 automation during commit.
    """

    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    action_results: list[ActionResult] = field(default_factory=list)
    cascade_results: list[CascadeResult] = field(default_factory=list)
    healing_report: HealingReport | None = None
    automation_results: list[AutomationResult] = field(default_factory=list)

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
    def automation_succeeded(self) -> int:
        """Count of successful automation rule executions (TDD-AUTOMATION-LAYER).

        Returns:
            Number of automation rules that executed successfully (not skipped).
        """
        return sum(
            1 for r in self.automation_results if r.success and not r.was_skipped
        )

    @property
    def automation_failed(self) -> int:
        """Count of failed automation rule executions (TDD-AUTOMATION-LAYER).

        Returns:
            Number of automation rules that failed.
        """
        return sum(1 for r in self.automation_results if not r.success)

    @property
    def automation_skipped(self) -> int:
        """Count of skipped automation rules (loop prevention) (TDD-AUTOMATION-LAYER).

        Returns:
            Number of automation rules skipped due to loop prevention.
        """
        return sum(1 for r in self.automation_results if r.was_skipped)

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
# Self-Healing Models (TDD-DETECTION/ADR-0095)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HealingResult:
    """Outcome of a healing operation.

    Per ADR-0095/0118/TDD-SPRINT-5-CLEANUP: Unified result for all healing contexts.

    Healing adds missing project memberships to entities that were
    detected via fallback tiers (2-5) instead of deterministic Tier 1.

    This is the canonical HealingResult type used by both:
    - HealingManager (SaveSession integration)
    - heal_entity_async/heal_entities_async (standalone API)

    Attributes:
        entity_gid: GID of the entity that was healed (or would be).
        entity_type: Type name of the entity (e.g., "Contact", "Offer").
        project_gid: GID of the project entity was added to.
        success: True if healing succeeded (or would succeed in dry_run).
        dry_run: True if this was a dry-run (no actual API call).
        error: Error message if healing failed, None otherwise.
    """

    entity_gid: str
    entity_type: str
    project_gid: str
    success: bool
    dry_run: bool = False
    error: str | None = None

    def __bool__(self) -> bool:
        """Return True if healing succeeded."""
        return self.success

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        status = "success" if self.success else f"failed: {self.error}"
        if self.dry_run:
            status = f"dry_run: {status}"
        return f"HealingResult({self.entity_type}, {self.entity_gid} -> {self.project_gid}, {status})"


@dataclass
class HealingReport:
    """Aggregate report of all healing operations.

    Per TDD-DETECTION/ADR-0095: Summary of healing outcomes for SaveResult.

    Attributes:
        attempted: Total number of healing operations attempted.
        succeeded: Number of successful healing operations.
        failed: Number of failed healing operations.
        results: List of individual HealingResult objects.
    """

    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    results: list[HealingResult] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        """True if all healing operations succeeded.

        Returns True if at least one healing was attempted and all succeeded.
        Returns False if no healing was attempted (attempted == 0).
        """
        return self.failed == 0 and self.attempted > 0

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"HealingReport(attempted={self.attempted}, succeeded={self.succeeded}, failed={self.failed})"


# ---------------------------------------------------------------------------
# Action Types (TDD-0011)
# ---------------------------------------------------------------------------


class ActionType(StrEnum):
    """Type of action operation for non-batch API endpoints.

    Per TDD-0011: Action endpoints for relationship management.
    Per TDD-0012: Extended with follower, dependent, like, and comment operations.
    Per TDD-0013: Extended with parent/subtask operations.

    These operations are batched via the Batch API (TDD-GAP-05) when available.
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


def _build_positioning_data(
    base_data: dict[str, Any], extra_params: dict[str, Any]
) -> dict[str, Any]:
    """Augment payload data with positioning parameters from extra_params.

    Per ADR-0044: Include insert_before/insert_after for ordering.

    Args:
        base_data: Base payload data dict to augment.
        extra_params: Extra parameters that may contain positioning keys.

    Returns:
        The base_data dict, augmented with any positioning keys present.
    """
    if "insert_before" in extra_params:
        base_data["insert_before"] = extra_params["insert_before"]
    if "insert_after" in extra_params:
        base_data["insert_after"] = extra_params["insert_after"]
    return base_data


def _build_comment_data(extra_params: dict[str, Any]) -> dict[str, Any]:
    """Build comment payload from extra_params.

    Per TDD-0012/ADR-0046: Text stored in extra_params.

    Args:
        extra_params: Parameters containing 'text' and optional 'html_text'.

    Returns:
        Comment payload dict.
    """
    data: dict[str, Any] = {"text": extra_params.get("text", "")}
    if extra_params.get("html_text"):
        data["html_text"] = extra_params["html_text"]
    return data


# Dispatch table for ActionType -> API call generation.
# Each entry maps to: (endpoint_suffix, payload_key, payload_style)
# payload_style values:
#   "single"      - {"data": {key: target_gid}}  # noqa: ERA001
#   "list"        - {"data": {key: [target_gid]}}  # noqa: ERA001
#   "positioning" - {"data": {key: target_gid, +positioning}} via task path
#   "section"     - {"data": {"task": task_gid, +positioning}} via section path (MOVE_TO_SECTION)
#   "parent"      - {"data": {"parent": extra_params["parent"], +positioning}}
#   "no_target"   - {"data": {}}  # noqa: ERA001
#   "comment"     - {"data": _build_comment_data(extra_params)}  # noqa: ERA001
_ACTION_SPECS: dict[ActionType, tuple[str, str, str]] = {
    ActionType.ADD_TAG: ("addTag", "tag", "single"),
    ActionType.REMOVE_TAG: ("removeTag", "tag", "single"),
    ActionType.REMOVE_FROM_PROJECT: ("removeProject", "project", "single"),
    ActionType.ADD_TO_PROJECT: ("addProject", "project", "positioning"),
    ActionType.MOVE_TO_SECTION: ("addTask", "task", "section"),
    ActionType.SET_PARENT: ("setParent", "parent", "parent"),
    ActionType.ADD_DEPENDENCY: ("addDependencies", "dependencies", "list"),
    ActionType.REMOVE_DEPENDENCY: ("removeDependencies", "dependencies", "list"),
    ActionType.ADD_FOLLOWER: ("addFollowers", "followers", "list"),
    ActionType.REMOVE_FOLLOWER: ("removeFollowers", "followers", "list"),
    ActionType.ADD_DEPENDENT: ("addDependents", "dependents", "list"),
    ActionType.REMOVE_DEPENDENT: ("removeDependents", "dependents", "list"),
    ActionType.ADD_LIKE: ("addLike", "", "no_target"),
    ActionType.REMOVE_LIKE: ("removeLike", "", "no_target"),
    ActionType.ADD_COMMENT: ("stories", "", "comment"),
}


@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation for non-batch API endpoints.

    Per TDD-0011: Actions are executed via individual API calls after
    CRUD batch operations complete. They manage relationships between
    tasks and other resources (tags, projects, sections, dependencies).

    Per TDD-0012/ADR-0044: Extended with extra_params for positioning.
    Per TDD-0012/ADR-0045: target is optional for some operations.
    Per ADR-0107: Uses NameGid for target to preserve name information.

    Attributes:
        task: The task being acted upon (source of the action).
        action: The type of action to perform.
        target: The target resource reference (tag, project, section,
                or dependency task). Uses NameGid to preserve both gid
                and name. May contain a temp GID for newly created
                resources that will be resolved before execution. Optional
                for like operations and comments where no target is needed.
        extra_params: Additional parameters for the action. Used for positioning
                     (insert_before, insert_after) in add_to_project and
                     move_to_section. Also used for comment text storage.
    """

    task: AsanaResource
    action: ActionType
    target: NameGid | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)

    def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
        """Convert action to API call parameters.

        Uses _ACTION_SPECS dispatch table to map action types to API
        call parameters, replacing per-case branching with data-driven
        lookup.

        Returns:
            Tuple of (HTTP method, endpoint path, payload dict).

        Raises:
            ValueError: If action type is not recognized.
        """
        task_gid = self.task.gid

        # Per ADR-0107: Extract GID from NameGid target
        target_gid = self.target.gid if self.target else None

        spec = _ACTION_SPECS.get(self.action)
        if spec is None:
            raise ValueError(f"Unknown action type: {self.action}")

        endpoint_suffix, payload_key, style = spec

        # MOVE_TO_SECTION: path uses target_gid, data uses task_gid (reversed)
        if style == "section":
            path = f"/sections/{target_gid}/{endpoint_suffix}"
            data = _build_positioning_data({payload_key: task_gid}, self.extra_params)
        elif style == "positioning":
            path = f"/tasks/{task_gid}/{endpoint_suffix}"
            data = _build_positioning_data({payload_key: target_gid}, self.extra_params)
        elif style == "parent":
            path = f"/tasks/{task_gid}/{endpoint_suffix}"
            parent_gid = self.extra_params.get("parent")
            data = _build_positioning_data({payload_key: parent_gid}, self.extra_params)
        elif style == "list":
            path = f"/tasks/{task_gid}/{endpoint_suffix}"
            data = {payload_key: [target_gid]}
        elif style == "no_target":
            path = f"/tasks/{task_gid}/{endpoint_suffix}"
            data = {}
        elif style == "comment":
            path = f"/tasks/{task_gid}/{endpoint_suffix}"
            data = _build_comment_data(self.extra_params)
        else:  # "single"
            path = f"/tasks/{task_gid}/{endpoint_suffix}"
            data = {payload_key: target_gid}

        return ("POST", path, {"data": data})

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        task_type = type(self.task).__name__
        task_gid = self.task.gid
        target_repr = self.target.gid if self.target else None
        return (
            f"ActionOperation({self.action.value}, "
            f"{task_type}(gid={task_gid}), target={target_repr})"
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


# ---------------------------------------------------------------------------
# Automation Result Models (TDD-AUTOMATION-LAYER)
# ---------------------------------------------------------------------------


@dataclass
class AutomationResult:
    """Result of automation rule execution.

    Per TDD-AUTOMATION-LAYER/FR-007: Included in SaveResult after automation.
    Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT/FR-ERR-004: Enhancement tracking.
    Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT/ADR-0018: Validation tracking.

    Attributes:
        rule_id: Unique identifier of the rule that executed.
        rule_name: Human-readable rule name.
        triggered_by_gid: GID of entity that triggered the rule.
        triggered_by_type: Type name of triggering entity.
        actions_executed: List of action type names executed.
        entities_created: GIDs of newly created entities.
        entities_updated: GIDs of entities that were updated.
        success: True if all actions succeeded.
        error: Error message if failed (per Open Question 2).
        execution_time_ms: Time taken to execute rule.
        skipped_reason: Reason if rule was skipped (e.g., "circular_reference_prevented").
        enhancement_results: Per-step success tracking for pipeline enhancements.
            Keys include: "hierarchy_placement", "assignee_set", "comment_created".
        pre_validation: Result of pre-transition validation, if performed.
            None if validation was not configured or not performed.
        post_validation: Result of post-transition validation, if performed.
            None if validation was not configured or not performed.
    """

    rule_id: str
    rule_name: str
    triggered_by_gid: str
    triggered_by_type: str
    actions_executed: list[str] = field(default_factory=list)
    entities_created: list[str] = field(default_factory=list)
    entities_updated: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    execution_time_ms: float = 0.0
    skipped_reason: str | None = None
    enhancement_results: dict[str, bool | int] = field(default_factory=dict)
    pre_validation: Any | None = (
        None  # ValidationResult, using Any to avoid circular import
    )
    post_validation: Any | None = (
        None  # ValidationResult, using Any to avoid circular import
    )

    def __repr__(self) -> str:
        """Return string representation."""
        status = "success" if self.success else f"failed: {self.error}"
        if self.skipped_reason:
            status = f"skipped: {self.skipped_reason}"
        return f"AutomationResult({self.rule_name}, {status})"

    @property
    def was_skipped(self) -> bool:
        """True if rule was skipped (loop prevention, etc.)."""
        return self.skipped_reason is not None
