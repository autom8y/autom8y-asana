"""Event hook registration and emission.

Per FR-EVENT-001 through FR-EVENT-005.
Per ADR-0041: Synchronous event hooks with async support.
Per TDD-AUTOMATION-LAYER/FR-002: Post-commit hooks for automation.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.persistence.models import OperationType

logger = get_logger(__name__)

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.models import SaveResult


# Type aliases for hook signatures
PreSaveHook = (
    Callable[["AsanaResource", OperationType], None]
    | Callable[["AsanaResource", OperationType], Coroutine[Any, Any, None]]
)

PostSaveHook = (
    Callable[["AsanaResource", OperationType, Any], None]
    | Callable[["AsanaResource", OperationType, Any], Coroutine[Any, Any, None]]
)

ErrorHook = (
    Callable[["AsanaResource", OperationType, Exception], None]
    | Callable[["AsanaResource", OperationType, Exception], Coroutine[Any, Any, None]]
)

# Per TDD-AUTOMATION-LAYER/FR-002: Post-commit hook receives full SaveResult
PostCommitHook = (
    Callable[["SaveResult"], None] | Callable[["SaveResult"], Coroutine[Any, Any, None]]
)


class EventSystem:
    """Event hook registration and emission.

    Per FR-EVENT-001 through FR-EVENT-005.
    Per ADR-0041: Synchronous event hooks with async support.

    Responsibilities:
    - Register pre_save, post_save, and error hooks
    - Support both sync functions and async coroutines
    - Invoke hooks at appropriate times during save pipeline

    Pre-save hooks can raise exceptions to abort the save operation.
    Post-save and error hooks swallow exceptions to not interfere with
    the save pipeline.

    Example:
        events = EventSystem()

        @events.register_pre_save
        def validate_task(entity: AsanaResource, op: OperationType) -> None:
            if op == OperationType.CREATE and not entity.name:
                raise ValueError("Task must have a name")

        @events.register_post_save
        async def log_save(entity: AsanaResource, op: OperationType, data: Any) -> None:
            await log_to_service(entity.gid, op)
    """

    def __init__(self) -> None:
        """Initialize empty hook lists."""
        self._pre_save_hooks: list[PreSaveHook] = []
        self._post_save_hooks: list[PostSaveHook] = []
        self._error_hooks: list[ErrorHook] = []
        self._post_commit_hooks: list[PostCommitHook] = []

    def register_pre_save(
        self,
        func: PreSaveHook,
    ) -> Callable[..., Any]:
        """Register pre-save hook.

        Per FR-EVENT-001: Hook called before each entity save.
        Per FR-EVENT-004: Receives entity and operation context.
        Per FR-EVENT-005: Support both function and coroutine hooks.

        Pre-save hooks can raise exceptions to abort the save operation
        for that entity. The exception will propagate up to the caller.

        Args:
            func: Hook function receiving (entity, operation_type).
                  Can be sync or async.

        Returns:
            The decorated function (for decorator usage).
        """
        self._pre_save_hooks.append(func)
        return func

    def register_post_save(
        self,
        func: PostSaveHook,
    ) -> Callable[..., Any]:
        """Register post-save hook.

        Per FR-EVENT-002: Called after successful entity save with result.

        Post-save hooks cannot abort the save (it already happened).
        Any exceptions raised by post-save hooks are swallowed to
        prevent interfering with subsequent saves.

        Args:
            func: Hook function receiving (entity, operation_type, response_data).
                  Can be sync or async.

        Returns:
            The decorated function (for decorator usage).
        """
        self._post_save_hooks.append(func)
        return func

    def register_error(
        self,
        func: ErrorHook,
    ) -> Callable[..., Any]:
        """Register error hook.

        Per FR-EVENT-003: Called when save fails.

        Error hooks are for logging/notification purposes only.
        Any exceptions raised by error hooks are swallowed to
        prevent interfering with error handling.

        Args:
            func: Hook function receiving (entity, operation_type, exception).
                  Can be sync or async.

        Returns:
            The decorated function (for decorator usage).
        """
        self._error_hooks.append(func)
        return func

    async def emit_pre_save(
        self,
        entity: AsanaResource,
        operation: OperationType,
    ) -> None:
        """Emit pre-save event to all registered hooks.

        Per FR-EVENT-005: Handle both sync and async hooks.

        Hooks are called in registration order. If any hook raises
        an exception, it propagates immediately (aborting the save).

        Args:
            entity: The entity about to be saved.
            operation: The operation type (CREATE, UPDATE, DELETE).

        Raises:
            Any exception raised by a pre-save hook.
        """
        for hook in self._pre_save_hooks:
            result = hook(entity, operation)
            if asyncio.iscoroutine(result):
                await result

    async def emit_post_save(
        self,
        entity: AsanaResource,
        operation: OperationType,
        data: Any,
    ) -> None:
        """Emit post-save event to all registered hooks.

        Post-save hooks cannot fail the operation (save already succeeded).
        All exceptions are swallowed and hooks continue to execute.

        Args:
            entity: The entity that was saved.
            operation: The operation type that was performed.
            data: The response data from the API.
        """
        for hook in self._post_save_hooks:
            try:
                result = hook(entity, operation, data)
                if asyncio.iscoroutine(result):
                    await result
            except (
                Exception
            ):  # BROAD-CATCH: hook -- post-save hooks must not fail the operation
                logger.warning(
                    "post_save_hook_failed",
                    exc_info=True,
                    extra={
                        "hook": getattr(hook, "__name__", repr(hook)),
                        "entity_gid": getattr(entity, "gid", None),
                        "operation": operation.value,
                    },
                )

    async def emit_error(
        self,
        entity: AsanaResource,
        operation: OperationType,
        error: Exception,
    ) -> None:
        """Emit error event to all registered hooks.

        Error hooks are for logging/notification purposes only.
        All exceptions are swallowed and hooks continue to execute.

        Args:
            entity: The entity that failed to save.
            operation: The operation type that was attempted.
            error: The exception that occurred.
        """
        for hook in self._error_hooks:
            try:
                result = hook(entity, operation, error)
                if asyncio.iscoroutine(result):
                    await result
            except (
                Exception
            ):  # BROAD-CATCH: hook -- error hooks must not fail the operation
                logger.warning(
                    "error_hook_failed",
                    exc_info=True,
                    extra={
                        "hook": getattr(hook, "__name__", repr(hook)),
                        "entity_gid": getattr(entity, "gid", None),
                        "operation": operation.value,
                        "original_error": type(error).__name__,
                    },
                )

    def register_post_commit(
        self,
        func: PostCommitHook,
    ) -> Callable[..., Any]:
        """Register post-commit hook.

        Per TDD-AUTOMATION-LAYER/FR-002: Called after entire commit completes
        with full SaveResult (including automation results).

        Post-commit hooks are called after all phases of commit complete:
        - CRUD operations
        - Action operations
        - Cascade operations
        - Healing operations
        - Automation operations

        Post-commit hooks cannot fail the commit (it already succeeded).
        All exceptions are swallowed and hooks continue to execute.

        Args:
            func: Hook function receiving (SaveResult). Can be sync or async.

        Returns:
            The decorated function (for decorator usage).

        Example:
            @session.on_post_commit
            async def log_automation(result: SaveResult) -> None:
                for auto_result in result.automation_results:
                    logger.info("Rule %s: %s", auto_result.rule_name, auto_result.success)
        """
        self._post_commit_hooks.append(func)
        return func

    async def emit_post_commit(self, result: SaveResult) -> None:
        """Emit post-commit event with full SaveResult.

        Per TDD-AUTOMATION-LAYER/FR-002: Called after all commit phases complete.

        Post-commit hooks cannot fail the commit (it already succeeded).
        All exceptions are swallowed and hooks continue to execute.

        Args:
            result: The complete SaveResult from commit.
        """
        for hook in self._post_commit_hooks:
            try:
                hook_result = hook(result)
                if asyncio.iscoroutine(hook_result):
                    await hook_result
            except (
                Exception
            ):  # BROAD-CATCH: hook -- post-commit hooks must not fail the operation
                logger.warning(
                    "post_commit_hook_failed",
                    exc_info=True,
                    extra={
                        "hook": getattr(hook, "__name__", repr(hook)),
                    },
                )

    def clear_hooks(self) -> None:
        """Clear all registered hooks.

        Useful for testing or resetting state.
        """
        self._pre_save_hooks.clear()
        self._post_save_hooks.clear()
        self._error_hooks.clear()
        self._post_commit_hooks.clear()
