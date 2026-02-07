"""Action executor for API operations with batch support.

Per TDD-0011, corrected by TDD-GAP-05: Action operations are routed through
the Batch API when a BatchClient is available. Falls back to individual API
calls when batch_client is None or the batch endpoint fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.batch.models import BatchRequest, BatchResult
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.action_ordering import resolve_order
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
)

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.transport.asana_http import AsanaHttpClient


# --- Module-Level Conversion Functions ---


def action_to_batch_request(action: ActionOperation) -> BatchRequest:
    """Convert a resolved ActionOperation to a BatchRequest.

    The action MUST have resolved GIDs (no temp_ prefixes) before calling.

    to_api_call() returns (method, endpoint, payload) where payload has a
    "data" key wrapping the actual parameters. BatchRequest expects
    (relative_path, method, data) where data is the UNWRAPPED content.

    Args:
        action: A resolved ActionOperation.

    Returns:
        BatchRequest ready for BatchClient.execute_async().
    """
    method, endpoint, payload = action.to_api_call()
    # Unwrap the "data" key -- BatchClient re-wraps it in the batch envelope
    unwrapped_data = payload.get("data")
    return BatchRequest(
        relative_path=endpoint,
        method=method,
        data=unwrapped_data,
    )


def batch_result_to_action_result(
    action: ActionOperation,
    batch_result: BatchResult,
) -> ActionResult:
    """Map a BatchResult back to an ActionResult.

    Args:
        action: The original ActionOperation (for the .action field).
        batch_result: The BatchResult from BatchClient.

    Returns:
        ActionResult with the same shape as sequential execution produces.
    """
    if batch_result.success:
        return ActionResult(
            action=action,
            success=True,
            response_data=batch_result.data,
        )
    else:
        return ActionResult(
            action=action,
            success=False,
            error=batch_result.error,
        )


def _chunk_actions(
    actions: list[ActionOperation],
    chunk_size: int,
) -> list[list[ActionOperation]]:
    """Split actions into chunks of at most chunk_size.

    Args:
        actions: Actions to chunk.
        chunk_size: Maximum actions per chunk.

    Returns:
        List of chunks, each containing at most chunk_size actions.
    """
    if not actions:
        return []
    return [
        actions[i : i + chunk_size]
        for i in range(0, len(actions), chunk_size)
    ]


class ActionExecutor:
    """Executes action operations via batch or individual API calls.

    Per TDD-0011, corrected by TDD-GAP-05: Actions are batched via
    BatchClient when available, with chunk-level fallback to individual
    POST requests.

    The executor:
    - Batches actions when batch_client is available and count >= 2
    - Resolves temp GIDs to real GIDs before execution
    - Falls back to sequential execution per-chunk on batch failure
    - Reports success/failure for each action individually

    Example:
        executor = ActionExecutor(http_client, batch_client)

        actions = [
            ActionOperation(task, ActionType.ADD_TAG, "tag_gid"),
            ActionOperation(task, ActionType.MOVE_TO_SECTION, "section_gid"),
        ]

        results = await executor.execute_async(actions, gid_map={})
        for result in results:
            if result.success:
                print(f"Action {result.action.action.value} succeeded")
    """

    def __init__(
        self,
        http_client: AsanaHttpClient,
        batch_client: BatchClient | None = None,
    ) -> None:
        """Initialize executor with HTTP client and optional batch client.

        Args:
            http_client: The AsanaHttpClient for making individual API requests
                        (used for sub-threshold execution and chunk-level fallback).
            batch_client: Optional BatchClient for batch execution. When None,
                         all actions are executed sequentially via http_client.
        """
        self._http = http_client
        self._batch_client = batch_client
        self._log = getattr(http_client, "_log", None)

    async def execute_async(
        self,
        actions: list[ActionOperation],
        gid_map: dict[str, str],
    ) -> list[ActionResult]:
        """Execute action operations, batched when possible.

        Per TDD-GAP-05: Actions are batched when batch_client is available
        and action count >= 2. Sequential execution is used as fallback.

        Signature UNCHANGED from TDD-0011 contract.

        Args:
            actions: List of ActionOperation to execute.
            gid_map: Map of temp GIDs to real GIDs for resolution.
                    Keys are temp_xxx strings, values are real GIDs.

        Returns:
            List of ActionResult in the same order as input actions.
            Each result indicates success or failure with details.
        """
        if not actions:
            return []

        # Sub-threshold or no batch client: sequential (original behavior)
        if self._batch_client is None or len(actions) < 2:
            results: list[ActionResult] = []
            for action in actions:
                result = await self._execute_single_action(action, gid_map)
                results.append(result)
            return results

        # Batch path
        return await self._execute_batched(actions, gid_map)

    async def _execute_batched(
        self,
        actions: list[ActionOperation],
        gid_map: dict[str, str],
    ) -> list[ActionResult]:
        """Batch execution: resolve, order, chunk, execute, collect.

        Args:
            actions: List of ActionOperation (at least 2).
            gid_map: Temp GID -> real GID mapping.

        Returns:
            ActionResult list in the same order as input actions.
        """
        # Step 1: Resolve all temp GIDs up front (FR-005)
        resolved_actions = [self._resolve_temp_gids(a, gid_map) for a in actions]

        # Build index map: resolved_action -> original position
        # This lets us restore original ordering after tier/chunk reordering
        action_index: dict[int, int] = {id(r): i for i, r in enumerate(resolved_actions)}

        # Step 2: Ordering resolution (FR-002)
        tiers = resolve_order(resolved_actions)

        # Step 3-5: Execute tiers, chunking within each
        indexed_results: list[tuple[int, ActionResult]] = []
        chunks_total = 0
        chunks_fallback = 0

        for tier in tiers:
            chunks = _chunk_actions(tier, 10)

            for chunk in chunks:
                chunks_total += 1
                chunk_results, fell_back = await self._execute_chunk_batched(chunk)

                if fell_back:
                    chunks_fallback += 1

                for action, result in zip(chunk, chunk_results):
                    original_idx = action_index[id(action)]
                    indexed_results.append((original_idx, result))

        # Step 6: Restore original ordering
        indexed_results.sort(key=lambda pair: pair[0])

        # Metrics logging
        if self._log:
            batch_succeeded = sum(1 for _, r in indexed_results if r.success)
            batch_failed = len(actions) - batch_succeeded
            self._log.info(
                "action_batch_complete",
                total_actions=len(actions),
                batch_succeeded=batch_succeeded,
                batch_failed=batch_failed,
                sequential_fallback=chunks_fallback,
                tiers=len(tiers),
                chunks_total=chunks_total,
                chunks_fallback=chunks_fallback,
            )

        return [result for _, result in indexed_results]

    async def _execute_chunk_batched(
        self,
        chunk: list[ActionOperation],
    ) -> tuple[list[ActionResult], bool]:
        """Execute a single chunk via BatchClient, with fallback.

        Args:
            chunk: List of resolved ActionOperation (max 10).

        Returns:
            Tuple of (list of ActionResult in chunk order, whether fallback was used).
        """
        batch_requests = [action_to_batch_request(a) for a in chunk]

        try:
            batch_results = await self._batch_client.execute_async(batch_requests)  # type: ignore[union-attr]

            # Defensive: result count must match request count.
            # A mismatch indicates a batch endpoint issue (partial response,
            # protocol error, or misconfigured mock). Treat as batch failure
            # and fall back to sequential for this chunk.
            if len(batch_results) != len(chunk):
                raise ValueError(
                    f"Batch result count mismatch: expected {len(chunk)}, "
                    f"got {len(batch_results)}"
                )

            results = [
                batch_result_to_action_result(action, br)
                for action, br in zip(chunk, batch_results)
            ]
            return results, False
        except Exception as exc:  # BROAD-CATCH: intentional -- ANY batch endpoint failure triggers chunk-level fallback
            # Chunk-level fallback (FR-006, MUST)
            if self._log:
                self._log.warning(
                    "action_batch_chunk_fallback",
                    chunk_size=len(chunk),
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

            # Fall back to sequential for this chunk only
            results = []
            for action in chunk:
                # Actions are already resolved; _execute_single_action calls
                # _resolve_temp_gids which is idempotent on resolved actions.
                result = await self._execute_single_action(action, {})
                results.append(result)
            return results, True

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

        except Exception as e:  # BROAD-CATCH: isolation -- action execution returns error result, never propagates
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

        Per ADR-0107: ActionOperation.target is now NameGid | None.
        Creates a new ActionOperation with resolved GIDs if the target
        was a temp GID that has been resolved.

        Args:
            action: The ActionOperation that may contain temp GIDs.
            gid_map: Map of temp GIDs to real GIDs.

        Returns:
            ActionOperation with resolved GIDs. If no resolution needed,
            returns the original action (no new object created).
        """
        # Per ADR-0107: target is now NameGid | None
        target = action.target
        resolved_target = target

        # Resolve target.gid if it's a temp GID
        if (
            target is not None
            and target.gid.startswith("temp_")
            and target.gid in gid_map
        ):
            # Preserve name and resource_type during resolution
            resolved_target = NameGid(
                gid=gid_map[target.gid],
                name=target.name,
                resource_type=target.resource_type,
            )

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
        if resolved_target is not target or resolved_task is not task:
            return ActionOperation(
                task=resolved_task,
                action=action.action,
                target=resolved_target,
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
