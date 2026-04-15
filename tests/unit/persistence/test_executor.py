"""Tests for BatchExecutor.

Per TDD-0010: Verify batch execution delegation and result correlation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchRequest, BatchResult
from autom8_asana.models import Task
from autom8_asana.persistence.executor import BatchExecutor
from autom8_asana.persistence.models import OperationType

# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def create_mock_batch_client(responses: list[BatchResult] | None = None) -> MagicMock:
    """Create a mock BatchClient with configurable responses."""
    mock_client = MagicMock()
    mock_client.execute_async = AsyncMock(return_value=responses or [])
    return mock_client


def create_success_result(
    gid: str = "123",
    request_index: int = 0,
) -> BatchResult:
    """Create a successful BatchResult."""
    return BatchResult(
        status_code=200,
        body={"data": {"gid": gid, "name": "Test"}},
        request_index=request_index,
    )


def create_failure_result(
    message: str = "Not found",
    status_code: int = 404,
    request_index: int = 0,
) -> BatchResult:
    """Create a failed BatchResult."""
    return BatchResult(
        status_code=status_code,
        body={"errors": [{"message": message}]},
        request_index=request_index,
    )


# ---------------------------------------------------------------------------
# Execute Level Tests
# ---------------------------------------------------------------------------


class TestExecuteLevel:
    """Tests for execute_level() method."""

    async def test_execute_level_empty(self) -> None:
        """execute_level() with empty list returns empty."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        result = await executor.execute_level([])

        assert result == []
        mock_client.execute_async.assert_not_called()

    async def test_execute_level_single_create(self) -> None:
        """execute_level() handles single CREATE operation."""
        success = create_success_result(gid="new_123")
        mock_client = create_mock_batch_client([success])
        executor = BatchExecutor(mock_client)

        task = Task(gid="temp_1", name="New Task")
        operations = [(task, OperationType.CREATE, {"name": "New Task"})]

        results = await executor.execute_level(operations)

        assert len(results) == 1
        entity, op_type, batch_result = results[0]
        assert entity is task
        assert op_type == OperationType.CREATE
        assert batch_result.success
        assert batch_result.data["gid"] == "new_123"

    async def test_execute_level_single_update(self) -> None:
        """execute_level() handles single UPDATE operation."""
        success = create_success_result(gid="123")
        mock_client = create_mock_batch_client([success])
        executor = BatchExecutor(mock_client)

        task = Task(gid="123", name="Updated Task")
        operations = [(task, OperationType.UPDATE, {"name": "Updated Task"})]

        results = await executor.execute_level(operations)

        assert len(results) == 1
        entity, op_type, batch_result = results[0]
        assert entity is task
        assert op_type == OperationType.UPDATE
        assert batch_result.success

    async def test_execute_level_single_delete(self) -> None:
        """execute_level() handles single DELETE operation."""
        success = BatchResult(status_code=204, body=None, request_index=0)
        mock_client = create_mock_batch_client([success])
        executor = BatchExecutor(mock_client)

        task = Task(gid="123", name="To Delete")
        operations = [(task, OperationType.DELETE, {})]

        results = await executor.execute_level(operations)

        assert len(results) == 1
        entity, op_type, batch_result = results[0]
        assert entity is task
        assert op_type == OperationType.DELETE
        assert batch_result.success

    async def test_execute_level_correlates_results(self) -> None:
        """execute_level() correlates results to correct entities."""
        results_data = [
            create_success_result(gid="111", request_index=0),
            create_success_result(gid="222", request_index=1),
            create_success_result(gid="333", request_index=2),
        ]
        mock_client = create_mock_batch_client(results_data)
        executor = BatchExecutor(mock_client)

        task1 = Task(gid="111", name="Task 1")
        task2 = Task(gid="222", name="Task 2")
        task3 = Task(gid="333", name="Task 3")

        operations = [
            (task1, OperationType.UPDATE, {"name": "Task 1"}),
            (task2, OperationType.UPDATE, {"name": "Task 2"}),
            (task3, OperationType.UPDATE, {"name": "Task 3"}),
        ]

        results = await executor.execute_level(operations)

        assert len(results) == 3
        # Verify correlation
        assert results[0][0] is task1
        assert results[1][0] is task2
        assert results[2][0] is task3

    async def test_execute_level_mixed_results(self) -> None:
        """execute_level() handles mix of success and failure."""
        results_data = [
            create_success_result(gid="111", request_index=0),
            create_failure_result("Not found", 404, request_index=1),
            create_success_result(gid="333", request_index=2),
        ]
        mock_client = create_mock_batch_client(results_data)
        executor = BatchExecutor(mock_client)

        task1 = Task(gid="111", name="Task 1")
        task2 = Task(gid="222", name="Task 2")
        task3 = Task(gid="333", name="Task 3")

        operations = [
            (task1, OperationType.UPDATE, {"name": "Task 1"}),
            (task2, OperationType.UPDATE, {"name": "Task 2"}),
            (task3, OperationType.UPDATE, {"name": "Task 3"}),
        ]

        results = await executor.execute_level(operations)

        assert len(results) == 3
        assert results[0][2].success
        assert not results[1][2].success
        assert results[1][2].error is not None
        assert results[2][2].success


# ---------------------------------------------------------------------------
# Build Request Tests
# ---------------------------------------------------------------------------


class TestBuildRequest:
    """Tests for _build_request() method."""

    def test_build_request_create(self) -> None:
        """_build_request() creates POST request for CREATE."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        task = Task(gid="temp_1", name="New Task")
        payload = {"name": "New Task", "projects": ["proj_123"]}

        request = executor._build_request(task, OperationType.CREATE, payload)

        assert request.relative_path == "/tasks"
        assert request.method == "POST"
        assert request.data == payload

    def test_build_request_update(self) -> None:
        """_build_request() creates PUT request for UPDATE."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        task = Task(gid="123", name="Updated")
        payload = {"name": "Updated"}

        request = executor._build_request(task, OperationType.UPDATE, payload)

        assert request.relative_path == "/tasks/123"
        assert request.method == "PUT"
        assert request.data == payload

    def test_build_request_delete(self) -> None:
        """_build_request() creates DELETE request for DELETE."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        task = Task(gid="123", name="To Delete")

        request = executor._build_request(task, OperationType.DELETE, {})

        assert request.relative_path == "/tasks/123"
        assert request.method == "DELETE"
        assert request.data is None


# ---------------------------------------------------------------------------
# Resource Path Mapping Tests
# ---------------------------------------------------------------------------


class TestResourceToPath:
    """Tests for _resource_to_path() method."""

    @pytest.mark.parametrize(
        "resource,expected_path",
        [
            pytest.param("task", "tasks", id="task"),
            pytest.param("project", "projects", id="project"),
            pytest.param("section", "sections", id="section"),
            pytest.param("tag", "tags", id="tag"),
            pytest.param("user", "users", id="user"),
            pytest.param("story", "stories", id="story"),
        ],
    )
    def test_resource_to_path(self, resource: str, expected_path: str) -> None:
        """Verify singular resource type maps to correct plural path."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        assert executor._resource_to_path(resource) == expected_path

    def test_resource_to_path_already_plural(self) -> None:
        """Already plural resource types returned as-is."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        assert executor._resource_to_path("tasks") == "tasks"
        assert executor._resource_to_path("projects") == "projects"

    def test_resource_to_path_case_insensitive(self) -> None:
        """Resource type mapping is case insensitive."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        assert executor._resource_to_path("Task") == "tasks"
        assert executor._resource_to_path("PROJECT") == "projects"

    def test_resource_to_path_unknown(self) -> None:
        """Unknown resource types get 's' appended."""
        mock_client = create_mock_batch_client()
        executor = BatchExecutor(mock_client)

        assert executor._resource_to_path("widget") == "widgets"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration tests verifying full flow."""

    async def test_batch_client_receives_correct_requests(self) -> None:
        """Verify BatchClient receives correctly built requests."""
        mock_client = create_mock_batch_client(
            [
                create_success_result(gid="new_1", request_index=0),
                create_success_result(gid="222", request_index=1),
            ]
        )
        executor = BatchExecutor(mock_client)

        task1 = Task(gid="temp_1", name="New Task")
        task2 = Task(gid="222", name="Updated Task")

        operations = [
            (task1, OperationType.CREATE, {"name": "New Task"}),
            (task2, OperationType.UPDATE, {"name": "Updated Task"}),
        ]

        await executor.execute_level(operations)

        # Verify the requests passed to BatchClient
        call_args = mock_client.execute_async.call_args
        requests: list[BatchRequest] = call_args[0][0]

        assert len(requests) == 2

        # First request: CREATE
        assert requests[0].relative_path == "/tasks"
        assert requests[0].method == "POST"
        assert requests[0].data == {"name": "New Task"}

        # Second request: UPDATE
        assert requests[1].relative_path == "/tasks/222"
        assert requests[1].method == "PUT"
        assert requests[1].data == {"name": "Updated Task"}
