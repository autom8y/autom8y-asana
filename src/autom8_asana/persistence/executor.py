"""Batch executor for save operations.

Per FR-BATCH-002: Delegate to existing BatchClient.
Per ADR-0010: Sequential chunk execution.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.batch.models import BatchRequest, BatchResult
from autom8_asana.persistence.models import OperationType

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.models.base import AsanaResource


class BatchExecutor:
    """Executes batched operations via BatchClient.

    Per FR-BATCH-002: Delegate to existing BatchClient.
    Per FR-BATCH-003: Execute chunks sequentially per ADR-0010.
    Per FR-BATCH-006: Respect 10-action batch limit (handled by BatchClient).

    Responsibilities:
    - Build BatchRequest objects per operation type
    - Execute operations via BatchClient
    - Correlate BatchResult back to entities
    - Map resource types to API paths

    The BatchClient handles chunking into batches of 10 and sequential
    execution. This class focuses on building requests and correlating
    results.

    Example:
        executor = BatchExecutor(batch_client)

        operations = [
            (task1, OperationType.CREATE, {"name": "New Task"}),
            (task2, OperationType.UPDATE, {"name": "Updated"}),
        ]

        results = await executor.execute_level(operations)
        for entity, op_type, batch_result in results:
            if batch_result.success:
                print(f"Saved {entity.gid}")
    """

    def __init__(
        self,
        batch_client: BatchClient,
        batch_size: int = 10,
    ) -> None:
        """Initialize executor with BatchClient.

        Args:
            batch_client: The BatchClient instance to use for execution.
            batch_size: Maximum operations per batch (default: 10, Asana limit).
                       This is passed through to BatchClient but typically
                       not needed as BatchClient handles chunking.
        """
        self._client = batch_client
        self._batch_size = batch_size

    async def execute_level(
        self,
        operations: list[tuple[AsanaResource, OperationType, dict[str, Any]]],
    ) -> list[tuple[AsanaResource, OperationType, BatchResult]]:
        """Execute all operations for a dependency level.

        Per FR-BATCH-004: Correlate responses to entities.
        Per FR-BATCH-005: Update entity GIDs after creation.

        Operations within a level have no dependencies on each other,
        so they can be executed in any order. BatchClient handles
        chunking into groups of 10.

        Args:
            operations: List of (entity, operation_type, payload) tuples.
                       All operations in the list should be at the same
                       dependency level.

        Returns:
            List of (entity, operation_type, batch_result) tuples.
            Results are in the same order as input operations.
        """
        if not operations:
            return []

        # Build BatchRequests, tracking which entity each belongs to
        batch_requests: list[BatchRequest] = []
        request_map: list[tuple[AsanaResource, OperationType]] = []

        for entity, op_type, payload in operations:
            request = self._build_request(entity, op_type, payload)
            batch_requests.append(request)
            request_map.append((entity, op_type))

        # Execute via BatchClient (handles chunking per ADR-0010)
        batch_results = await self._client.execute_async(batch_requests)

        # Correlate results back to entities
        results: list[tuple[AsanaResource, OperationType, BatchResult]] = []

        for i, batch_result in enumerate(batch_results):
            entity, op_type = request_map[i]
            results.append((entity, op_type, batch_result))

        return results

    def _build_request(
        self,
        entity: AsanaResource,
        op_type: OperationType,
        payload: dict[str, Any],
    ) -> BatchRequest:
        """Build BatchRequest for entity operation.

        Per FR-BATCH-007: Map operation types to HTTP methods.
        Per FR-BATCH-008: Include custom field values in payload.

        Args:
            entity: The entity to build a request for.
            op_type: The type of operation (CREATE, UPDATE, DELETE).
            payload: The data payload for the request.

        Returns:
            BatchRequest configured for the operation.
        """
        resource_type = getattr(entity, "resource_type", "task") or "task"

        # Normalize resource type to API path
        resource_path = self._resource_to_path(resource_type)

        if op_type == OperationType.CREATE:
            return BatchRequest(
                relative_path=f"/{resource_path}",
                method="POST",
                data=payload,
            )
        elif op_type == OperationType.UPDATE:
            return BatchRequest(
                relative_path=f"/{resource_path}/{entity.gid}",
                method="PUT",
                data=payload,
            )
        else:  # DELETE
            return BatchRequest(
                relative_path=f"/{resource_path}/{entity.gid}",
                method="DELETE",
            )

    def _resource_to_path(self, resource_type: str) -> str:
        """Convert resource_type to API path.

        Handles singular to plural conversion for common resource types.

        Args:
            resource_type: The resource_type field from an AsanaResource.

        Returns:
            The API path segment (e.g., "tasks", "projects").
        """
        # Handle common cases with explicit mapping
        mapping: dict[str, str] = {
            "task": "tasks",
            "project": "projects",
            "section": "sections",
            "tag": "tags",
            "user": "users",
            "workspace": "workspaces",
            "team": "teams",
            "story": "stories",
            "attachment": "attachments",
            "custom_field": "custom_fields",
            "portfolio": "portfolios",
            "goal": "goals",
        }

        lower_type = resource_type.lower()
        if lower_type in mapping:
            return mapping[lower_type]

        # Default: add 's' for pluralization
        # This handles cases like "tasks" -> "tasks" (already plural)
        if lower_type.endswith("s"):
            return lower_type
        return lower_type + "s"
