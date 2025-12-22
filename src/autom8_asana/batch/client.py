"""BatchClient for Asana Batch API operations.

Per TDD-0005: Batch API for Bulk Operations.
Per ADR-0010: Sequential chunk execution for batch operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.batch.models import BatchRequest, BatchResult, BatchSummary
from autom8_asana.clients.base import BaseClient
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    pass

# Asana batch API limit
BATCH_SIZE_LIMIT = 10


class BatchClient(BaseClient):
    """Client for Asana Batch API operations.

    Enables efficient bulk operations by batching multiple requests
    into single API calls. Automatically handles:
    - Chunking requests into groups of 10 (Asana's limit)
    - Sequential chunk execution for rate limit compliance
    - Partial failure handling (one failure doesn't fail the batch)
    - Result correlation with original request order

    Example - Basic batch execution:
        requests = [
            BatchRequest("/tasks", "POST", data={"name": "Task 1", "projects": ["123"]}),
            BatchRequest("/tasks", "POST", data={"name": "Task 2", "projects": ["123"]}),
            BatchRequest("/tasks/456", "PUT", data={"completed": True}),
        ]

        results = await client.batch.execute_async(requests)

        for i, result in enumerate(results):
            if result.success:
                print(f"Request {i} succeeded: {result.data}")
            else:
                print(f"Request {i} failed: {result.error}")

    Example - Convenience methods:
        # Batch create tasks
        tasks_data = [
            {"name": "Task 1", "projects": ["123"]},
            {"name": "Task 2", "projects": ["123"], "assignee": "456"},
        ]
        results = await client.batch.create_tasks_async(tasks_data)

        # Batch update tasks
        updates = [
            ("task_gid_1", {"completed": True}),
            ("task_gid_2", {"assignee": "789"}),
        ]
        results = await client.batch.update_tasks_async(updates)
    """

    # --- Core Async Methods ---

    async def execute_async(
        self,
        requests: list[BatchRequest],
    ) -> list[BatchResult]:
        """Execute batch of requests with auto-chunking.

        Processes requests in chunks of 10 (Asana's limit), executing
        chunks sequentially to respect rate limits. Results are returned
        in the same order as input requests.

        Args:
            requests: List of BatchRequest objects to execute

        Returns:
            List of BatchResult objects, one per request, in order

        Raises:
            AsanaError: If the batch endpoint itself fails (not individual actions)

        Note:
            Individual action failures are captured in BatchResult.error,
            not raised as exceptions. This allows partial success.
        """
        if not requests:
            return []

        self._log_operation("execute_async")
        if self._log:
            self._log.info(
                f"BatchClient.execute: Starting batch of {len(requests)} requests "
                f"in {_count_chunks(len(requests))} chunks"
            )

        # Chunk requests per ADR-0010 (sequential execution)
        chunks = _chunk_requests(requests)
        all_results: list[BatchResult] = []
        base_index = 0

        for chunk_num, chunk in enumerate(chunks, 1):
            if self._log:
                self._log.debug(
                    f"BatchClient.execute: Chunk {chunk_num}/{len(chunks)}: "
                    f"{len(chunk)} actions"
                )

            chunk_results = await self._execute_chunk(chunk, base_index)
            all_results.extend(chunk_results)

            succeeded = sum(1 for r in chunk_results if r.success)
            failed = len(chunk_results) - succeeded
            if self._log:
                self._log.debug(
                    f"BatchClient.execute: Chunk {chunk_num}/{len(chunks)} complete: "
                    f"{succeeded} succeeded, {failed} failed"
                )

            base_index += len(chunk)

        total_succeeded = sum(1 for r in all_results if r.success)
        if self._log:
            self._log.info(
                f"BatchClient.execute: Batch complete: "
                f"{total_succeeded}/{len(requests)} succeeded"
            )

        return all_results

    async def execute_with_summary_async(
        self,
        requests: list[BatchRequest],
    ) -> BatchSummary:
        """Execute batch and return summary with aggregate statistics.

        Same as execute_async but returns a BatchSummary with
        convenience methods for analyzing results.

        Args:
            requests: List of BatchRequest objects to execute

        Returns:
            BatchSummary with results and statistics
        """
        results = await self.execute_async(requests)
        return BatchSummary(results=results)

    # --- Task-Specific Convenience Methods ---

    async def create_tasks_async(
        self,
        tasks: list[dict[str, Any]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Batch create multiple tasks.

        Convenience method that builds BatchRequest objects for
        task creation. Equivalent to calling execute_async with
        POST /tasks requests.

        Args:
            tasks: List of task data dicts, each containing:
                - name (required): Task name
                - projects: List of project GIDs
                - assignee: Assignee user GID
                - notes: Task description
                - due_on: Due date (YYYY-MM-DD)
                - parent: Parent task GID (for subtasks)
                - custom_fields: Dict of custom field GID -> value
                - ... (any other valid task fields)
            opt_fields: Fields to include in response

        Returns:
            List of BatchResult objects for each create operation

        Example:
            results = await client.batch.create_tasks_async([
                {"name": "Task 1", "projects": ["123"]},
                {"name": "Task 2", "projects": ["123"], "due_on": "2024-01-15"},
            ])

            created_gids = [
                r.data["gid"] for r in results if r.success and r.data
            ]
        """
        self._log_operation("create_tasks_async")

        options: dict[str, Any] | None = None
        if opt_fields:
            options = {"opt_fields": ",".join(opt_fields)}

        requests = [
            BatchRequest(
                relative_path="/tasks",
                method="POST",
                data=task_data,
                options=options,
            )
            for task_data in tasks
        ]

        return await self.execute_async(requests)

    async def update_tasks_async(
        self,
        updates: list[tuple[str, dict[str, Any]]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Batch update multiple tasks.

        Convenience method that builds BatchRequest objects for
        task updates. Each update is a tuple of (task_gid, data).

        Args:
            updates: List of (task_gid, update_data) tuples where:
                - task_gid: GID of task to update
                - update_data: Dict of fields to update:
                    - name: New task name
                    - completed: Completion status
                    - assignee: New assignee GID
                    - due_on: New due date
                    - ... (any updatable task fields)
            opt_fields: Fields to include in response

        Returns:
            List of BatchResult objects for each update operation

        Example:
            results = await client.batch.update_tasks_async([
                ("task_gid_1", {"completed": True}),
                ("task_gid_2", {"assignee": "user_gid"}),
                ("task_gid_3", {"name": "Renamed Task"}),
            ])

            failed = [r for r in results if not r.success]
            if failed:
                print(f"{len(failed)} updates failed")
        """
        self._log_operation("update_tasks_async")

        options: dict[str, Any] | None = None
        if opt_fields:
            options = {"opt_fields": ",".join(opt_fields)}

        requests = [
            BatchRequest(
                relative_path=f"/tasks/{task_gid}",
                method="PUT",
                data=update_data,
                options=options,
            )
            for task_gid, update_data in updates
        ]

        return await self.execute_async(requests)

    async def delete_tasks_async(
        self,
        task_gids: list[str],
    ) -> list[BatchResult]:
        """Batch delete multiple tasks.

        Args:
            task_gids: List of task GIDs to delete

        Returns:
            List of BatchResult objects for each delete operation
        """
        self._log_operation("delete_tasks_async")

        requests = [
            BatchRequest(
                relative_path=f"/tasks/{task_gid}",
                method="DELETE",
            )
            for task_gid in task_gids
        ]

        return await self.execute_async(requests)

    # --- Sync Wrappers ---

    def execute(self, requests: list[BatchRequest]) -> list[BatchResult]:
        """Sync wrapper for execute_async."""
        return self._execute_sync(requests)

    @sync_wrapper("execute_async")
    async def _execute_sync(self, requests: list[BatchRequest]) -> list[BatchResult]:
        """Internal sync wrapper implementation."""
        return await self.execute_async(requests)

    def execute_with_summary(self, requests: list[BatchRequest]) -> BatchSummary:
        """Sync wrapper for execute_with_summary_async."""
        return self._execute_with_summary_sync(requests)

    @sync_wrapper("execute_with_summary_async")
    async def _execute_with_summary_sync(
        self, requests: list[BatchRequest]
    ) -> BatchSummary:
        """Internal sync wrapper implementation."""
        return await self.execute_with_summary_async(requests)

    def create_tasks(
        self,
        tasks: list[dict[str, Any]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Sync wrapper for create_tasks_async."""
        return self._create_tasks_sync(tasks, opt_fields=opt_fields)

    @sync_wrapper("create_tasks_async")
    async def _create_tasks_sync(
        self,
        tasks: list[dict[str, Any]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Internal sync wrapper implementation."""
        return await self.create_tasks_async(tasks, opt_fields=opt_fields)

    def update_tasks(
        self,
        updates: list[tuple[str, dict[str, Any]]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Sync wrapper for update_tasks_async."""
        return self._update_tasks_sync(updates, opt_fields=opt_fields)

    @sync_wrapper("update_tasks_async")
    async def _update_tasks_sync(
        self,
        updates: list[tuple[str, dict[str, Any]]],
        *,
        opt_fields: list[str] | None = None,
    ) -> list[BatchResult]:
        """Internal sync wrapper implementation."""
        return await self.update_tasks_async(updates, opt_fields=opt_fields)

    def delete_tasks(self, task_gids: list[str]) -> list[BatchResult]:
        """Sync wrapper for delete_tasks_async."""
        return self._delete_tasks_sync(task_gids)

    @sync_wrapper("delete_tasks_async")
    async def _delete_tasks_sync(self, task_gids: list[str]) -> list[BatchResult]:
        """Internal sync wrapper implementation."""
        return await self.delete_tasks_async(task_gids)

    # --- Internal Methods ---

    async def _execute_chunk(
        self,
        chunk: list[BatchRequest],
        base_index: int,
    ) -> list[BatchResult]:
        """Execute a single chunk of requests.

        Args:
            chunk: List of requests (max 10)
            base_index: Starting index for result correlation

        Returns:
            List of BatchResult objects with correct request_index values
        """
        actions = [req.to_action_dict() for req in chunk]

        # POST to /batch endpoint
        # The batch endpoint expects {"data": {"actions": [...]}} format
        # and returns the raw response array, not wrapped in {"data": ...}
        response = await self._http.request(
            "POST",
            "/batch",
            json={"data": {"actions": actions}},
        )

        # Parse results, preserving order
        results: list[BatchResult] = []

        # Response from batch endpoint is a list
        if isinstance(response, list):
            for i, item in enumerate(response):
                results.append(
                    BatchResult.from_asana_response(
                        response_item=item,
                        request_index=base_index + i,
                    )
                )
        elif isinstance(response, dict):
            # Handle case where response might be wrapped
            response_list = response.get("data", [response])
            if not isinstance(response_list, list):
                response_list = [response_list]
            for i, item in enumerate(response_list):
                results.append(
                    BatchResult.from_asana_response(
                        response_item=item,
                        request_index=base_index + i,
                    )
                )

        return results


def _chunk_requests(
    requests: list[BatchRequest],
) -> list[list[BatchRequest]]:
    """Split requests into chunks of BATCH_SIZE_LIMIT.

    Args:
        requests: All requests to chunk

    Returns:
        List of chunks, each with at most BATCH_SIZE_LIMIT requests

    Example:
        >>> _chunk_requests([r1, r2, ..., r25])
        [[r1..r10], [r11..r20], [r21..r25]]
    """
    if not requests:
        return []

    return [
        requests[i : i + BATCH_SIZE_LIMIT]
        for i in range(0, len(requests), BATCH_SIZE_LIMIT)
    ]


def _count_chunks(request_count: int) -> int:
    """Count number of chunks needed for a given request count."""
    if request_count == 0:
        return 0
    return (request_count + BATCH_SIZE_LIMIT - 1) // BATCH_SIZE_LIMIT
