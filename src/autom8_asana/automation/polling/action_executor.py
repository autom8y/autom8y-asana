"""Action executor for polling-based automation.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Executes actions on tasks that matched
rule conditions. Supports add_tag, add_comment, and change_section actions.

Example - Execute Add Tag Action:
    from autom8_asana.automation.polling import ActionExecutor, ActionConfig

    executor = ActionExecutor(client)
    action = ActionConfig(type="add_tag", params={"tag_gid": "1234567890123"})

    result = await executor.execute_async("task-123", action)
    if result.success:
        print(f"Action {result.action_type} completed on {result.task_gid}")
    else:
        print(f"Action failed: {result.error}")

Example - Execute Add Comment:
    action = ActionConfig(type="add_comment", params={"text": "Escalated by automation"})
    result = await executor.execute_async("task-456", action)

Example - Execute Change Section:
    action = ActionConfig(type="change_section", params={"section_gid": "9876543210987"})
    result = await executor.execute_async("task-789", action)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8_asana.automation.polling.structured_logger import StructuredLogger

if TYPE_CHECKING:
    from autom8_asana.automation.polling.config_schema import ActionConfig

    pass

__all__ = ["ActionExecutor", "ActionResult"]

# Supported action types with their required parameters
_SUPPORTED_ACTIONS: dict[str, list[str]] = {
    "add_tag": ["tag_gid"],
    "add_comment": ["text"],
    "change_section": ["section_gid"],
}


@dataclass
class ActionResult:
    """Result of action execution.

    Captures the outcome of executing an action on a task, including
    success/failure status, error messages, and execution details.

    Attributes:
        success: True if action executed successfully, False otherwise.
        action_type: Type of action that was executed (e.g., "add_tag").
        task_gid: GID of the task the action was executed on.
        error: Error message if action failed, None on success.
        details: Additional details about the execution (e.g., tag_gid added).

    Example:
        result = ActionResult(
            success=True,
            action_type="add_tag",
            task_gid="1234567890123",
            details={"tag_gid": "9876543210987"},
        )
    """

    success: bool
    action_type: str
    task_gid: str
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class ActionExecutor:
    """Executes actions on tasks that matched rule conditions.

    Supports executing automation actions (add_tag, add_comment, change_section)
    using the provided AsanaClient. Each action is executed asynchronously and
    results are captured in ActionResult for logging and error handling.

    Actions are designed to be isolated - if one action fails, it does not
    prevent other actions from being executed.

    Attributes:
        _client: AsanaClient instance for API operations.
        _logger: StructuredLogger for action execution logging.

    Example:
        executor = ActionExecutor(client)
        result = await executor.execute_async("task-123", action_config)
    """

    def __init__(self, client: Any) -> None:
        """Initialize with AsanaClient for API operations.

        Args:
            client: AsanaClient instance with tags, stories, and sections
                sub-clients for executing actions.
        """
        self._client = client
        self._logger = StructuredLogger.get_logger(component="action_executor")

    async def execute_async(
        self,
        task_gid: str,
        action: ActionConfig,
    ) -> ActionResult:
        """Execute an action on a task.

        Validates the action type and parameters, then executes the appropriate
        API call. Errors are caught and wrapped in ActionResult with success=False.

        Args:
            task_gid: GID of the task to execute the action on.
            action: ActionConfig containing action type and parameters.

        Returns:
            ActionResult with success=True if action executed, or success=False
            with error message if action failed.

        Raises:
            ValueError: If action type is not supported or required params are missing.

        Example:
            action = ActionConfig(type="add_tag", params={"tag_gid": "123"})
            result = await executor.execute_async("task-456", action)
        """
        action_type = action.type
        params = action.params

        # Validate action type
        if action_type not in _SUPPORTED_ACTIONS:
            raise ValueError(
                f"Unsupported action type: '{action_type}'. "
                f"Supported types: {list(_SUPPORTED_ACTIONS.keys())}"
            )

        # Validate required parameters
        required_params = _SUPPORTED_ACTIONS[action_type]
        missing_params = [p for p in required_params if p not in params]
        if missing_params:
            raise ValueError(f"Missing required params for '{action_type}': {missing_params}")

        # Log action start
        self._logger.info(
            "action_execution_started",
            task_gid=task_gid,
            action_type=action_type,
            params=params,
        )

        try:
            # Dispatch to action handler
            if action_type == "add_tag":
                await self._execute_add_tag(task_gid, params)
            elif action_type == "add_comment":
                await self._execute_add_comment(task_gid, params)
            elif action_type == "change_section":
                await self._execute_change_section(task_gid, params)

            # Log success
            self._logger.info(
                "action_execution_succeeded",
                task_gid=task_gid,
                action_type=action_type,
            )

            return ActionResult(
                success=True,
                action_type=action_type,
                task_gid=task_gid,
                details=params,
            )

        except Exception as exc:  # BROAD-CATCH: isolation -- single action failure returns error result, never propagates  # noqa: BLE001
            # Log failure
            error_message = str(exc)
            self._logger.error(
                "action_execution_failed",
                task_gid=task_gid,
                action_type=action_type,
                error=error_message,
            )

            return ActionResult(
                success=False,
                action_type=action_type,
                task_gid=task_gid,
                error=error_message,
                details=params,
            )

    async def _execute_add_tag(
        self,
        task_gid: str,
        params: dict[str, Any],
    ) -> None:
        """Execute add_tag action.

        Adds the specified tag to the task using the tags client.

        Args:
            task_gid: Task GID to add tag to.
            params: Action params containing 'tag_gid'.
        """
        tag_gid = params["tag_gid"]
        await self._client.tags.add_to_task_async(task_gid, tag=tag_gid)

    async def _execute_add_comment(
        self,
        task_gid: str,
        params: dict[str, Any],
    ) -> None:
        """Execute add_comment action.

        Creates a comment on the task using the stories client.

        Args:
            task_gid: Task GID to add comment to.
            params: Action params containing 'text'.
        """
        text = params["text"]
        await self._client.stories.create_comment_async(task=task_gid, text=text)

    async def _execute_change_section(
        self,
        task_gid: str,
        params: dict[str, Any],
    ) -> None:
        """Execute change_section action.

        Moves the task to the specified section using the sections client.

        Args:
            task_gid: Task GID to move.
            params: Action params containing 'section_gid'.
        """
        section_gid = params["section_gid"]
        await self._client.sections.add_task_async(section_gid, task=task_gid)
