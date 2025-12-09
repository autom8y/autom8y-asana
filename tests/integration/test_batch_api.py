"""Integration tests for Batch API.

Tests batch operations against the real Asana API.
Requires ASANA_PAT and ASANA_PROJECT_GID environment variables.
"""

import os

import pytest

from autom8_asana import AsanaClient
from autom8_asana.batch.models import BatchRequest


@pytest.mark.integration
class TestBatchAPIIntegration:
    """Integration tests for batch API operations."""

    @pytest.fixture
    def project_gid(self) -> str:
        """Get project GID from environment."""
        gid = os.getenv("ASANA_PROJECT_GID")
        if not gid:
            pytest.skip("ASANA_PROJECT_GID not set")
        return gid

    async def test_batch_create_tasks(self, project_gid: str) -> None:
        """Test batch task creation with the real API.

        This test verifies the fix for the 400 Bad Request error.
        The batch endpoint expects {"data": {"actions": [...]}} format.
        """
        async with AsanaClient() as client:
            # Create 3 tasks in a batch
            tasks_data = [
                {
                    "name": f"Integration Test Task {i}",
                    "projects": [project_gid],
                    "notes": f"Created via batch API test #{i}",
                }
                for i in range(1, 4)
            ]

            # Execute batch create
            results = await client.batch.create_tasks_async(tasks_data)

            # Verify all succeeded
            assert len(results) == 3
            assert all(r.success for r in results), "All batch creates should succeed"

            # Extract created GIDs
            created_gids = [r.data["gid"] for r in results if r.data]
            assert len(created_gids) == 3

            # Cleanup: delete the created tasks
            delete_results = await client.batch.delete_tasks_async(created_gids)
            assert all(r.success for r in delete_results)

    async def test_batch_request_format(self, project_gid: str) -> None:
        """Test that batch requests use the correct format.

        Verifies the fix: requests must be wrapped in {"data": {"actions": [...]}}.
        """
        async with AsanaClient() as client:
            # Create a single BatchRequest manually
            requests = [
                BatchRequest(
                    relative_path="/tasks",
                    method="POST",
                    data={
                        "name": "Format Test Task",
                        "projects": [project_gid],
                    },
                )
            ]

            # Execute - this should work with the fixed format
            results = await client.batch.execute_async(requests)

            # Verify success
            assert len(results) == 1
            assert results[0].success
            assert results[0].data is not None

            # Cleanup
            task_gid = results[0].data["gid"]
            await client.tasks.delete_async(task_gid)

    async def test_batch_mixed_operations(self, project_gid: str) -> None:
        """Test batch with mixed operation types (create, update, delete)."""
        async with AsanaClient() as client:
            # First, create a task to update
            task = await client.tasks.create_async(
                name="Task for batch update",
                projects=[project_gid],
            )

            # Build batch requests: create + update + delete
            requests = [
                # Create a new task
                BatchRequest(
                    relative_path="/tasks",
                    method="POST",
                    data={"name": "Batch Created Task", "projects": [project_gid]},
                ),
                # Update the existing task
                BatchRequest(
                    relative_path=f"/tasks/{task.gid}",
                    method="PUT",
                    data={"completed": True},
                ),
                # Delete the existing task
                BatchRequest(
                    relative_path=f"/tasks/{task.gid}",
                    method="DELETE",
                ),
            ]

            # Execute batch
            results = await client.batch.execute_async(requests)

            # Verify all operations succeeded
            assert len(results) == 3
            assert results[0].success  # Create
            assert results[1].success  # Update
            assert results[2].success  # Delete

            # Cleanup the created task
            if results[0].data:
                created_gid = results[0].data["gid"]
                await client.tasks.delete_async(created_gid)
