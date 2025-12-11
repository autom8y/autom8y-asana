"""Action executor for non-batch API operations.

Per TDD-0011: Action operations (tags, projects, dependencies, sections)
cannot be batched and require individual API calls executed sequentially.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
)

if TYPE_CHECKING:
    from autom8_asana.transport.http import AsyncHTTPClient


class ActionExecutor:
    """Executes action operations via individual API calls.

    Per TDD-0011: Actions like add_tag, remove_tag, add_to_project, etc.
    cannot be batched and must be executed as individual POST requests.

    The executor:
    - Executes actions sequentially (not batched)
    - Resolves temp GIDs to real GIDs before execution
    - Reports success/failure for each action individually

    Example:
        executor = ActionExecutor(http_client)

        actions = [
            ActionOperation(task, ActionType.ADD_TAG, "tag_gid"),
            ActionOperation(task, ActionType.MOVE_TO_SECTION, "section_gid"),
        ]

        results = await executor.execute_async(actions, gid_map={})
        for result in results:
            if result.success:
                print(f"Action {result.action.action.value} succeeded")
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        """Initialize executor with HTTP client.

        Args:
            http_client: The AsyncHTTPClient for making API requests.
        """
        self._http = http_client

    async def execute_async(
        self,
        actions: list[ActionOperation],
        gid_map: dict[str, str],
    ) -> list[ActionResult]:
        """Execute action operations sequentially.

        Per TDD-0011: Actions are executed one at a time since they
        cannot be batched. Temp GIDs are resolved using the provided map.

        Args:
            actions: List of ActionOperation to execute.
            gid_map: Map of temp GIDs to real GIDs for resolution.
                    Keys are temp_xxx strings, values are real GIDs.

        Returns:
            List of ActionResult in the same order as input actions.
            Each result indicates success or failure with details.
        """
        results: list[ActionResult] = []

        for action in actions:
            result = await self._execute_single_action(action, gid_map)
            results.append(result)

        return results

    async def _execute_single_action(
        self,
        action: ActionOperation,
        gid_map: dict[str, str],
    ) -> ActionResult:
        """Execute a single action operation.

        Args:
            action: The ActionOperation to execute.
            gid_map: Map of temp GIDs to real GIDs.

        Returns:
            ActionResult with success status and any error/response data.
        """
        try:
            # Resolve temp GID if needed
            resolved_action = self._resolve_temp_gids(action, gid_map)

            # Get API call parameters
            method, endpoint, payload = resolved_action.to_api_call()

            # Execute the request
            response = await self._http.request(
                method=method,
                path=endpoint,
                json=payload,
            )

            return ActionResult(
                action=action,
                success=True,
                response_data=response,
            )

        except Exception as e:
            return ActionResult(
                action=action,
                success=False,
                error=e,
            )

    def _resolve_temp_gids(
        self,
        action: ActionOperation,
        gid_map: dict[str, str],
    ) -> ActionOperation:
        """Resolve temp GIDs in action to real GIDs.

        Creates a new ActionOperation with resolved GIDs if the target
        was a temp GID that has been resolved.

        Args:
            action: The ActionOperation that may contain temp GIDs.
            gid_map: Map of temp GIDs to real GIDs.

        Returns:
            ActionOperation with resolved GIDs. If no resolution needed,
            returns the original action (no new object created).
        """
        target_gid = action.target_gid

        # Resolve target_gid if it's a temp GID
        if target_gid is not None and target_gid.startswith("temp_") and target_gid in gid_map:
            target_gid = gid_map[target_gid]

        # Resolve task GID if it's a temp GID
        task = action.task
        task_gid = task.gid
        resolved_task = task

        if task_gid and task_gid.startswith("temp_"):
            temp_key = task_gid
            if temp_key in gid_map:
                # Create a new task reference with resolved GID
                # We use object.__setattr__ because the model may be frozen
                resolved_task = self._resolve_task_gid(task, gid_map[temp_key])

        # Only create new ActionOperation if something changed
        if target_gid != action.target_gid or resolved_task is not task:
            return ActionOperation(
                task=resolved_task,
                action=action.action,
                target_gid=target_gid,
                extra_params=action.extra_params,
            )

        return action

    def _resolve_task_gid(
        self,
        task: Any,
        real_gid: str,
    ) -> Any:
        """Create task copy with resolved GID.

        Args:
            task: The original task with temp GID.
            real_gid: The real GID to use.

        Returns:
            Task with resolved GID. If model_copy is available (Pydantic),
            uses that. Otherwise returns original with modified GID.
        """
        # For Pydantic models, use model_copy for proper copying
        if hasattr(task, "model_copy"):
            return task.model_copy(update={"gid": real_gid})

        # Fallback: directly update gid (may require unfreezing)
        try:
            object.__setattr__(task, "gid", real_gid)
        except (TypeError, AttributeError):
            pass  # Can't modify, use original

        return task
