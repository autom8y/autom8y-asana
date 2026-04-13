"""Exception hierarchy for Save Orchestration Layer.

Per TDD-0010 and PRD Appendix B: All save-specific errors inherit
from SaveOrchestrationError, which itself inherits from AsanaError.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.errors import AsanaError

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.models import SaveResult


class SaveOrchestrationError(AsanaError):
    """Base exception for save orchestration errors.

    Per PRD Appendix B: All save-specific errors inherit from this.
    This allows consumers to catch all save-related errors with a
    single except clause while still allowing granular handling.
    """

    def __init__(self, message: str) -> None:
        """Initialize with error message.

        Args:
            message: Human-readable error description.
        """
        super().__init__(message)


class SessionClosedError(SaveOrchestrationError):
    """Raised when operating on a closed session.

    Per FR-UOW-006: Prevent re-use after commit or context exit.
    Once a SaveSession exits its context manager, all operations
    on it should fail with this exception.
    """

    def __init__(self) -> None:
        """Initialize with standard closed session message."""
        super().__init__("Session is closed. Cannot perform operations.")


class CyclicDependencyError(SaveOrchestrationError):
    """Raised when dependency graph contains cycles.

    Per FR-DEPEND-003: Clear message indicating cycle participants.
    Cycles make it impossible to determine a valid save order.

    Attributes:
        cycle: List of entities involved in the cycle.
    """

    def __init__(self, cycle: list[AsanaResource]) -> None:
        """Initialize with cycle participants.

        Args:
            cycle: List of entities involved in the cycle.
        """
        self.cycle = cycle
        entities = " -> ".join(f"{type(e).__name__}(gid={e.gid})" for e in cycle)
        super().__init__(f"Cyclic dependency detected: {entities}")


class DependencyResolutionError(SaveOrchestrationError):
    """Raised when a dependency cannot be resolved.

    Per FR-ERROR-006: Raised when a dependent entity's save fails
    because its dependency failed. This enables cascading failure
    tracking in partial save scenarios.

    Attributes:
        entity: The entity that couldn't be saved.
        dependency: The dependency that failed.
    """

    def __init__(
        self,
        entity: AsanaResource,
        dependency: AsanaResource,
        cause: Exception,
    ) -> None:
        """Initialize with entity, dependency, and cause.

        Args:
            entity: The entity that couldn't be saved.
            dependency: The dependency that failed.
            cause: The underlying exception that caused the failure.
        """
        self.entity = entity
        self.dependency = dependency
        self.__cause__ = cause
        super().__init__(
            f"Cannot save {type(entity).__name__}(gid={entity.gid}): "
            f"dependency {type(dependency).__name__}(gid={dependency.gid}) failed"
        )


class PartialSaveError(SaveOrchestrationError):
    """Raised when some operations in a commit fail.

    Per FR-ERROR-004: Contains SaveResult with full outcome.
    Per ADR-0079: Enhanced with retryable error classification.
    This exception is raised by SaveResult.raise_on_failure() when
    the caller wants exception-based error handling instead of
    inspecting the result directly.

    Attributes:
        result: The SaveResult containing success and failure details.
    """

    def __init__(self, result: SaveResult) -> None:
        """Initialize with SaveResult.

        Args:
            result: The SaveResult containing success/failure details.
        """
        self.result = result
        failed_count = len(result.failed)
        total = result.total_count

        # Build enhanced message with retryable counts
        retryable_count = len(result.retryable_failures)
        non_retryable_count = len(result.non_retryable_failures)

        message = f"Partial save: {failed_count}/{total} operations failed"
        if failed_count > 0:
            message += f" ({retryable_count} retryable, {non_retryable_count} non-retryable)"

        super().__init__(message)

    @property
    def is_retryable(self) -> bool:
        """Whether any failures in this partial save are retryable.

        Per ADR-0079: Returns True if at least one failure is retryable,
        indicating that a partial retry may recover some operations.

        Returns:
            True if any failed operation is retryable.
        """
        return self.result.has_retryable_failures

    @property
    def retryable_count(self) -> int:
        """Count of retryable failures.

        Returns:
            Number of SaveErrors that are retryable.
        """
        return len(self.result.retryable_failures)

    @property
    def non_retryable_count(self) -> int:
        """Count of non-retryable failures.

        Returns:
            Number of SaveErrors that are not retryable.
        """
        return len(self.result.non_retryable_failures)


class UnsupportedOperationError(SaveOrchestrationError):
    """Raised when user modifies a field that requires action endpoints.

    Per TDD-0011: Certain fields (tags, projects, memberships, dependencies)
    cannot be modified directly via PUT/PATCH. Instead, they require
    dedicated action endpoints (addTag, removeTag, etc.).

    This exception guides users to the correct methods for managing
    these relationships.

    Attributes:
        field_name: The name of the field that cannot be directly modified.
        suggested_methods: List of methods that should be used instead.
    """

    def __init__(self, field_name: str, suggested_methods: list[str]) -> None:
        """Initialize with field name and suggested methods.

        Args:
            field_name: The field that cannot be directly modified.
            suggested_methods: Methods to use instead (e.g., ["add_tag", "remove_tag"]).
        """
        self.field_name = field_name
        self.suggested_methods = suggested_methods
        methods_str = ", ".join(suggested_methods)
        message = (
            f"Direct modification of '{field_name}' is not supported. "
            f"Use {methods_str} instead. "
            f"See: docs/guides/limitations.md#unsupported-direct-field-modifications"
        )
        super().__init__(message)


class PositioningConflictError(SaveOrchestrationError):
    """Raised when both insert_before and insert_after are specified.

    Per ADR-0047: Fail-fast validation at queue time. The Asana API does not
    support specifying both positioning parameters simultaneously.

    Attributes:
        insert_before: The insert_before value that was provided.
        insert_after: The insert_after value that was provided.
    """

    def __init__(self, insert_before: str, insert_after: str) -> None:
        """Initialize with the conflicting positioning values.

        Args:
            insert_before: The insert_before value that was provided.
            insert_after: The insert_after value that was provided.
        """
        self.insert_before = insert_before
        self.insert_after = insert_after
        super().__init__(
            f"Cannot specify both insert_before and insert_after. "
            f"Got insert_before={insert_before}, insert_after={insert_after}"
        )


class GidValidationError(SaveOrchestrationError):
    """Raised when entity GID validation fails at track time.

    Per ADR-0049: Fail-fast on invalid GIDs.
    Per FR-VAL-001: Validate GID format at track() time.
    Per TDD-HARDENING-A/FR-EXC-001: Renamed from ValidationError to avoid
    conflict with pydantic.ValidationError.

    This exception is raised when an entity fails validation during tracking,
    such as having an invalid GID format. The error message provides actionable
    guidance on how to fix the issue.

    Attributes:
        message: Human-readable validation failure description.
    """

    def __init__(self, message: str) -> None:
        """Initialize with validation error message.

        Args:
            message: Actionable description of validation failure.
        """
        super().__init__(message)


class SaveSessionError(SaveOrchestrationError):
    """Raised when a SaveSession commit fails in a convenience method.

    Per TDD-TRIAGE-FIXES/ADR-0065: P1 methods must propagate failures to callers.

    This exception wraps the SaveResult so callers can inspect what succeeded
    and what failed. It is raised by P1 convenience methods (add_tag_async,
    remove_tag_async, etc.) when the underlying SaveSession commit fails.

    Attributes:
        result: The SaveResult containing success/failure details.
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

        message = f"SaveSession commit failed. {len(failures)} failure(s): " + "; ".join(
            failures[:3]
        )
        if len(failures) > 3:
            message += f" ... and {len(failures) - 3} more"

        super().__init__(message)
