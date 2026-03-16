"""Tests for Batch API module.

Per TDD-0005: Batch API for Bulk Operations.
Per ADR-0010: Sequential chunk execution for batch operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autom8_asana.batch import BatchClient, BatchRequest, BatchResult, BatchSummary
from autom8_asana.batch.client import BATCH_SIZE_LIMIT, _chunk_requests, _count_chunks
from autom8_asana.exceptions import AsanaError, SyncInAsyncContextError

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig

# --- Test Fixtures ---


@pytest.fixture
def batch_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> BatchClient:
    """Create BatchClient with mocked dependencies."""
    return BatchClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


# --- BatchRequest Tests ---


class TestBatchRequest:
    """Tests for BatchRequest model."""

    def test_batch_request_valid_post(self) -> None:
        """BatchRequest accepts valid POST configuration."""
        req = BatchRequest(
            relative_path="/tasks",
            method="POST",
            data={"name": "Test Task"},
        )
        assert req.relative_path == "/tasks"
        assert req.method == "POST"
        assert req.data == {"name": "Test Task"}
        assert req.options is None

    def test_batch_request_valid_get_with_options(self) -> None:
        """BatchRequest accepts GET with options."""
        req = BatchRequest(
            relative_path="/tasks/123",
            method="GET",
            options={"opt_fields": "name,completed"},
        )
        assert req.relative_path == "/tasks/123"
        assert req.method == "GET"
        assert req.data is None
        assert req.options == {"opt_fields": "name,completed"}

    def test_batch_request_valid_put(self) -> None:
        """BatchRequest accepts PUT method."""
        req = BatchRequest(
            relative_path="/tasks/123",
            method="PUT",
            data={"completed": True},
        )
        assert req.method == "PUT"

    def test_batch_request_valid_delete(self) -> None:
        """BatchRequest accepts DELETE method."""
        req = BatchRequest(
            relative_path="/tasks/123",
            method="DELETE",
        )
        assert req.method == "DELETE"

    def test_batch_request_invalid_method(self) -> None:
        """BatchRequest rejects invalid HTTP method."""
        with pytest.raises(ValueError) as exc_info:
            BatchRequest(relative_path="/tasks", method="PATCH")
        assert "method must be one of" in str(exc_info.value)
        assert "PATCH" in str(exc_info.value)

    def test_batch_request_path_without_slash(self) -> None:
        """BatchRequest rejects path not starting with /."""
        with pytest.raises(ValueError) as exc_info:
            BatchRequest(relative_path="tasks", method="GET")
        assert "relative_path must start with '/'" in str(exc_info.value)

    def test_batch_request_to_action_dict_minimal(self) -> None:
        """to_action_dict produces correct minimal format."""
        req = BatchRequest(relative_path="/tasks/123", method="get")
        action = req.to_action_dict()
        assert action == {
            "relative_path": "/tasks/123",
            "method": "GET",  # Uppercased
        }

    def test_batch_request_to_action_dict_full(self) -> None:
        """to_action_dict includes data and options when present."""
        req = BatchRequest(
            relative_path="/tasks",
            method="post",
            data={"name": "Task"},
            options={"opt_fields": "gid,name"},
        )
        action = req.to_action_dict()
        assert action == {
            "relative_path": "/tasks",
            "method": "POST",
            "data": {"name": "Task"},
            "options": {"opt_fields": "gid,name"},
        }

    def test_batch_request_is_immutable(self) -> None:
        """BatchRequest is frozen (immutable)."""
        req = BatchRequest(relative_path="/tasks", method="GET")
        with pytest.raises(AttributeError):
            req.method = "POST"  # type: ignore[misc]

    def test_batch_request_method_case_insensitive_validation(self) -> None:
        """BatchRequest accepts lowercase methods."""
        req = BatchRequest(relative_path="/tasks", method="get")
        assert req.method == "get"  # Stored as-is
        assert req.to_action_dict()["method"] == "GET"  # Uppercased in output


# --- BatchResult Tests ---


class TestBatchResult:
    """Tests for BatchResult model."""

    def test_batch_result_success_200(self) -> None:
        """BatchResult with 200 status is successful."""
        result = BatchResult(status_code=200, body={"data": {"gid": "123"}})
        assert result.success is True
        assert result.error is None
        assert result.data == {"gid": "123"}

    def test_batch_result_success_201(self) -> None:
        """BatchResult with 201 status is successful."""
        result = BatchResult(status_code=201, body={"data": {"gid": "new"}})
        assert result.success is True
        assert result.error is None

    def test_batch_result_success_299(self) -> None:
        """BatchResult with 299 status is successful."""
        result = BatchResult(status_code=299)
        assert result.success is True

    def test_batch_result_failure_400(self) -> None:
        """BatchResult with 400 status is failure."""
        result = BatchResult(
            status_code=400,
            body={"errors": [{"message": "Bad request"}]},
        )
        assert result.success is False
        assert result.error is not None
        assert isinstance(result.error, AsanaError)
        assert "Bad request" in result.error.message

    def test_batch_result_failure_404(self) -> None:
        """BatchResult with 404 status is failure."""
        result = BatchResult(
            status_code=404,
            body={"errors": [{"message": "Task not found"}]},
        )
        assert result.success is False
        assert result.error is not None
        assert result.error.status_code == 404
        assert "Task not found" in result.error.message

    def test_batch_result_failure_500(self) -> None:
        """BatchResult with 500 status is failure."""
        result = BatchResult(status_code=500, body={})
        assert result.success is False
        assert result.error is not None

    def test_batch_result_data_property_unwraps(self) -> None:
        """data property unwraps Asana's data wrapper."""
        result = BatchResult(
            status_code=200,
            body={"data": {"gid": "123", "name": "Task"}},
        )
        assert result.data == {"gid": "123", "name": "Task"}

    def test_batch_result_data_property_no_wrapper(self) -> None:
        """data property returns body if no data wrapper."""
        result = BatchResult(
            status_code=200,
            body={"gid": "123", "name": "Task"},
        )
        assert result.data == {"gid": "123", "name": "Task"}

    def test_batch_result_data_property_failed(self) -> None:
        """data property returns None for failed results."""
        result = BatchResult(status_code=404, body={"error": "Not found"})
        assert result.data is None

    def test_batch_result_data_property_no_body(self) -> None:
        """data property returns None if no body."""
        result = BatchResult(status_code=200, body=None)
        assert result.data is None

    def test_batch_result_from_asana_response(self) -> None:
        """from_asana_response creates correct BatchResult."""
        response_item = {
            "status_code": 201,
            "body": {"data": {"gid": "created123"}},
            "headers": {"X-Request-Id": "abc123"},
        }
        result = BatchResult.from_asana_response(response_item, request_index=5)
        assert result.status_code == 201
        assert result.body == {"data": {"gid": "created123"}}
        assert result.headers == {"X-Request-Id": "abc123"}
        assert result.request_index == 5

    def test_batch_result_from_asana_response_defaults(self) -> None:
        """from_asana_response handles missing fields with defaults."""
        result = BatchResult.from_asana_response({}, request_index=0)
        assert result.status_code == 500
        assert result.body is None
        assert result.headers is None

    def test_batch_result_error_multiple_messages(self) -> None:
        """error property joins multiple error messages."""
        result = BatchResult(
            status_code=400,
            body={"errors": [{"message": "Error 1"}, {"message": "Error 2"}]},
        )
        assert result.error is not None
        assert "Error 1" in result.error.message
        assert "Error 2" in result.error.message

    def test_batch_result_is_immutable(self) -> None:
        """BatchResult is frozen (immutable)."""
        result = BatchResult(status_code=200)
        with pytest.raises(AttributeError):
            result.status_code = 404  # type: ignore[misc]


# --- BatchSummary Tests ---


class TestBatchSummary:
    """Tests for BatchSummary model."""

    def test_batch_summary_empty(self) -> None:
        """BatchSummary handles empty results."""
        summary = BatchSummary(results=[])
        assert summary.total == 0
        assert summary.succeeded == 0
        assert summary.failed == 0
        assert summary.all_succeeded is True  # vacuously true

    def test_batch_summary_all_succeeded(self) -> None:
        """BatchSummary counts all successes correctly."""
        results = [
            BatchResult(status_code=200),
            BatchResult(status_code=201),
            BatchResult(status_code=200),
        ]
        summary = BatchSummary(results=results)
        assert summary.total == 3
        assert summary.succeeded == 3
        assert summary.failed == 0
        assert summary.all_succeeded is True

    def test_batch_summary_all_failed(self) -> None:
        """BatchSummary counts all failures correctly."""
        results = [
            BatchResult(status_code=400),
            BatchResult(status_code=404),
            BatchResult(status_code=500),
        ]
        summary = BatchSummary(results=results)
        assert summary.total == 3
        assert summary.succeeded == 0
        assert summary.failed == 3
        assert summary.all_succeeded is False

    def test_batch_summary_mixed(self) -> None:
        """BatchSummary handles mixed results correctly."""
        results = [
            BatchResult(status_code=200),
            BatchResult(status_code=404),
            BatchResult(status_code=201),
            BatchResult(status_code=400),
        ]
        summary = BatchSummary(results=results)
        assert summary.total == 4
        assert summary.succeeded == 2
        assert summary.failed == 2
        assert summary.all_succeeded is False

    def test_batch_summary_successful_results(self) -> None:
        """successful_results filters to only successes."""
        results = [
            BatchResult(status_code=200, request_index=0),
            BatchResult(status_code=404, request_index=1),
            BatchResult(status_code=201, request_index=2),
        ]
        summary = BatchSummary(results=results)
        successful = summary.successful_results
        assert len(successful) == 2
        assert all(r.success for r in successful)
        assert [r.request_index for r in successful] == [0, 2]

    def test_batch_summary_failed_results(self) -> None:
        """failed_results filters to only failures."""
        results = [
            BatchResult(status_code=200, request_index=0),
            BatchResult(status_code=404, request_index=1),
            BatchResult(status_code=400, request_index=2),
        ]
        summary = BatchSummary(results=results)
        failed = summary.failed_results
        assert len(failed) == 2
        assert all(not r.success for r in failed)
        assert [r.request_index for r in failed] == [1, 2]


# --- Chunking Tests ---


class TestChunking:
    """Tests for request chunking functions."""

    def test_chunk_requests_empty(self) -> None:
        """_chunk_requests returns empty list for empty input."""
        assert _chunk_requests([]) == []

    def test_chunk_requests_under_limit(self) -> None:
        """_chunk_requests returns single chunk for < 10 requests."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(5)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 1
        assert len(chunks[0]) == 5

    def test_chunk_requests_exactly_limit(self) -> None:
        """_chunk_requests returns single chunk for exactly 10 requests."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(10)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 1
        assert len(chunks[0]) == 10

    def test_chunk_requests_over_limit(self) -> None:
        """_chunk_requests splits into multiple chunks for > 10 requests."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(11)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 1

    def test_chunk_requests_exact_multiple(self) -> None:
        """_chunk_requests handles exact multiples of limit."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(20)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10

    def test_chunk_requests_preserves_order(self) -> None:
        """_chunk_requests preserves request order across chunks."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(25)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 3

        # Flatten and verify order
        flattened = [req for chunk in chunks for req in chunk]
        assert len(flattened) == 25
        for i, req in enumerate(flattened):
            assert req.relative_path == f"/tasks/{i}"

    def test_count_chunks(self) -> None:
        """_count_chunks calculates correct chunk count."""
        assert _count_chunks(0) == 0
        assert _count_chunks(1) == 1
        assert _count_chunks(9) == 1
        assert _count_chunks(10) == 1
        assert _count_chunks(11) == 2
        assert _count_chunks(20) == 2
        assert _count_chunks(21) == 3
        assert _count_chunks(100) == 10

    def test_batch_size_limit_is_10(self) -> None:
        """BATCH_SIZE_LIMIT is set to Asana's limit of 10."""
        assert BATCH_SIZE_LIMIT == 10


# --- BatchClient Tests ---


class TestBatchClientExecuteAsync:
    """Tests for BatchClient.execute_async()."""

    async def test_execute_async_empty_list(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async returns empty list for empty input."""
        result = await batch_client.execute_async([])
        assert result == []
        mock_http.request.assert_not_called()

    async def test_execute_async_single_request(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async handles single request."""
        mock_http.request.return_value = [
            {"status_code": 201, "body": {"data": {"gid": "new123"}}}
        ]

        requests = [BatchRequest("/tasks", "POST", data={"name": "Task 1"})]
        results = await batch_client.execute_async(requests)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].data == {"gid": "new123"}
        assert results[0].request_index == 0
        mock_http.request.assert_called_once()

    async def test_execute_async_multiple_requests(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async handles multiple requests in single chunk."""
        mock_http.request.return_value = [
            {"status_code": 201, "body": {"data": {"gid": "1"}}},
            {"status_code": 201, "body": {"data": {"gid": "2"}}},
            {"status_code": 201, "body": {"data": {"gid": "3"}}},
        ]

        requests = [
            BatchRequest("/tasks", "POST", data={"name": f"Task {i}"}) for i in range(3)
        ]
        results = await batch_client.execute_async(requests)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.request_index for r in results] == [0, 1, 2]
        mock_http.request.assert_called_once()

    async def test_execute_async_auto_chunking(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async automatically chunks requests > 10."""
        # First chunk response (10 items)
        chunk1_response = [
            {"status_code": 201, "body": {"data": {"gid": str(i)}}} for i in range(10)
        ]
        # Second chunk response (5 items)
        chunk2_response = [
            {"status_code": 201, "body": {"data": {"gid": str(i)}}}
            for i in range(10, 15)
        ]
        mock_http.request.side_effect = [chunk1_response, chunk2_response]

        requests = [
            BatchRequest("/tasks", "POST", data={"name": f"Task {i}"})
            for i in range(15)
        ]
        results = await batch_client.execute_async(requests)

        assert len(results) == 15
        assert all(r.success for r in results)
        assert mock_http.request.call_count == 2
        # Verify request indices are correct across chunks
        assert [r.request_index for r in results] == list(range(15))

    async def test_execute_async_partial_failure(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async handles partial failures gracefully."""
        mock_http.request.return_value = [
            {"status_code": 201, "body": {"data": {"gid": "1"}}},
            {"status_code": 404, "body": {"errors": [{"message": "Not found"}]}},
            {"status_code": 201, "body": {"data": {"gid": "3"}}},
        ]

        requests = [
            BatchRequest("/tasks", "POST", data={"name": "Task 1"}),
            BatchRequest("/tasks/invalid", "PUT", data={"completed": True}),
            BatchRequest("/tasks", "POST", data={"name": "Task 3"}),
        ]
        results = await batch_client.execute_async(requests)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error is not None
        assert "Not found" in results[1].error.message
        assert results[2].success is True

    async def test_execute_async_all_failed(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async returns all failures without raising."""
        mock_http.request.return_value = [
            {"status_code": 400, "body": {"errors": [{"message": "Bad request"}]}},
            {"status_code": 404, "body": {"errors": [{"message": "Not found"}]}},
        ]

        requests = [
            BatchRequest("/tasks/bad", "PUT", data={}),
            BatchRequest("/tasks/missing", "GET"),
        ]
        results = await batch_client.execute_async(requests)

        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all(r.error is not None for r in results)

    async def test_execute_async_builds_correct_request_body(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async sends correct batch request format."""
        mock_http.request.return_value = [{"status_code": 200, "body": {}}]

        requests = [
            BatchRequest(
                "/tasks",
                "POST",
                data={"name": "Task"},
                options={"opt_fields": "gid,name"},
            )
        ]
        await batch_client.execute_async(requests)

        mock_http.request.assert_called_once_with(
            "POST",
            "/batch",
            json={
                "data": {
                    "actions": [
                        {
                            "relative_path": "/tasks",
                            "method": "POST",
                            "data": {"name": "Task"},
                            "options": {"opt_fields": "gid,name"},
                        }
                    ]
                }
            },
        )


class TestBatchClientExecuteWithSummary:
    """Tests for BatchClient.execute_with_summary_async()."""

    async def test_execute_with_summary_returns_summary(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_with_summary_async returns BatchSummary."""
        mock_http.request.return_value = [
            {"status_code": 201, "body": {}},
            {"status_code": 404, "body": {}},
        ]

        requests = [
            BatchRequest("/tasks", "POST", data={"name": "Task"}),
            BatchRequest("/tasks/missing", "GET"),
        ]
        summary = await batch_client.execute_with_summary_async(requests)

        assert isinstance(summary, BatchSummary)
        assert summary.total == 2
        assert summary.succeeded == 1
        assert summary.failed == 1


# --- Convenience Method Tests ---


class TestBatchClientConvenienceMethods:
    """Tests for BatchClient convenience methods."""

    async def test_create_tasks_async(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """create_tasks_async builds correct requests."""
        mock_http.request.return_value = [
            {"status_code": 201, "body": {"data": {"gid": "1"}}},
            {"status_code": 201, "body": {"data": {"gid": "2"}}},
        ]

        results = await batch_client.create_tasks_async(
            [
                {"name": "Task 1", "projects": ["proj123"]},
                {"name": "Task 2", "assignee": "user456"},
            ]
        )

        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify request structure
        call_args = mock_http.request.call_args
        actions = call_args[1]["json"]["data"]["actions"]
        assert len(actions) == 2
        assert actions[0]["relative_path"] == "/tasks"
        assert actions[0]["method"] == "POST"
        assert actions[0]["data"] == {"name": "Task 1", "projects": ["proj123"]}
        assert actions[1]["data"] == {"name": "Task 2", "assignee": "user456"}

    async def test_create_tasks_async_with_opt_fields(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """create_tasks_async passes opt_fields."""
        mock_http.request.return_value = [
            {"status_code": 201, "body": {"data": {"gid": "1", "name": "Task"}}}
        ]

        await batch_client.create_tasks_async(
            [{"name": "Task"}],
            opt_fields=["gid", "name", "completed"],
        )

        call_args = mock_http.request.call_args
        actions = call_args[1]["json"]["data"]["actions"]
        assert actions[0]["options"] == {"opt_fields": "gid,name,completed"}

    async def test_update_tasks_async(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """update_tasks_async builds correct requests."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {"data": {"gid": "1", "completed": True}}},
            {"status_code": 200, "body": {"data": {"gid": "2", "name": "Renamed"}}},
        ]

        results = await batch_client.update_tasks_async(
            [
                ("task_gid_1", {"completed": True}),
                ("task_gid_2", {"name": "Renamed"}),
            ]
        )

        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify request structure
        call_args = mock_http.request.call_args
        actions = call_args[1]["json"]["data"]["actions"]
        assert actions[0]["relative_path"] == "/tasks/task_gid_1"
        assert actions[0]["method"] == "PUT"
        assert actions[0]["data"] == {"completed": True}
        assert actions[1]["relative_path"] == "/tasks/task_gid_2"
        assert actions[1]["data"] == {"name": "Renamed"}

    async def test_delete_tasks_async(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_tasks_async builds correct requests."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {}},
            {"status_code": 200, "body": {}},
        ]

        results = await batch_client.delete_tasks_async(["gid1", "gid2"])

        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify request structure
        call_args = mock_http.request.call_args
        actions = call_args[1]["json"]["data"]["actions"]
        assert actions[0]["relative_path"] == "/tasks/gid1"
        assert actions[0]["method"] == "DELETE"
        assert actions[1]["relative_path"] == "/tasks/gid2"


# --- Sync Wrapper Tests ---


class TestBatchClientSyncWrappers:
    """Tests for BatchClient sync wrappers."""

    def test_execute_sync_works_outside_async(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """execute() works outside async context."""
        client = BatchClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.request.return_value = [
            {"status_code": 201, "body": {"data": {"gid": "1"}}}
        ]

        results = client.execute(
            [BatchRequest("/tasks", "POST", data={"name": "Task"})]
        )

        assert len(results) == 1
        assert results[0].success is True

    async def test_execute_sync_fails_in_async_context(
        self, batch_client: BatchClient
    ) -> None:
        """execute() raises SyncInAsyncContextError in async context."""
        with pytest.raises(SyncInAsyncContextError) as exc_info:
            batch_client.execute([])
        assert "execute_async" in str(exc_info.value)

    def test_execute_with_summary_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """execute_with_summary() works outside async context."""
        client = BatchClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.request.return_value = [{"status_code": 201, "body": {}}]

        summary = client.execute_with_summary(
            [BatchRequest("/tasks", "POST", data={"name": "Task"})]
        )

        assert isinstance(summary, BatchSummary)
        assert summary.total == 1

    def test_create_tasks_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create_tasks() works outside async context."""
        client = BatchClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.request.return_value = [{"status_code": 201, "body": {}}]

        results = client.create_tasks([{"name": "Task"}])

        assert len(results) == 1

    def test_update_tasks_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """update_tasks() works outside async context."""
        client = BatchClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.request.return_value = [{"status_code": 200, "body": {}}]

        results = client.update_tasks([("gid", {"completed": True})])

        assert len(results) == 1

    def test_delete_tasks_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """delete_tasks() works outside async context."""
        client = BatchClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.request.return_value = [{"status_code": 200, "body": {}}]

        results = client.delete_tasks(["gid1"])

        assert len(results) == 1


# --- Logging Tests ---


class TestBatchClientLogging:
    """Tests for BatchClient logging."""

    async def test_operations_are_logged(
        self, batch_client: BatchClient, mock_http: MockHTTPClient, logger: MockLogger
    ) -> None:
        """Batch operations log their execution."""
        mock_http.request.return_value = [{"status_code": 201, "body": {}}]

        await batch_client.execute_async(
            [BatchRequest("/tasks", "POST", data={"name": "Task"})]
        )

        # Check info and debug messages were logged (SDK MockLogger: .entries with .level/.event)
        info_events = [e.event for e in logger.get_events("info")]
        debug_events = [e.event for e in logger.get_events("debug")]

        assert any("Starting batch" in ev for ev in info_events)
        assert any("complete" in ev for ev in info_events)
        assert any("Chunk" in ev for ev in debug_events)


# --- Edge Case Tests ---


class TestBatchClientEdgeCases:
    """Edge case tests for BatchClient."""

    async def test_exactly_10_requests_single_chunk(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Exactly 10 requests results in single chunk."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {}} for _ in range(10)
        ]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(10)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 10
        assert mock_http.request.call_count == 1

    async def test_11_requests_two_chunks(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """11 requests results in two chunks (10 + 1)."""
        chunk1 = [{"status_code": 200, "body": {}} for _ in range(10)]
        chunk2 = [{"status_code": 200, "body": {}}]
        mock_http.request.side_effect = [chunk1, chunk2]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(11)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 11
        assert mock_http.request.call_count == 2

    async def test_handles_dict_response(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Handle case where response might be dict wrapped."""
        # Some batch responses might be wrapped in {"data": [...]}
        mock_http.request.return_value = {
            "data": [{"status_code": 200, "body": {"data": {"gid": "1"}}}]
        }

        results = await batch_client.execute_async([BatchRequest("/tasks", "GET")])

        assert len(results) == 1
        assert results[0].success is True


# =============================================================================
# Auto-Chunking Boundary Conditions (merged from test_batch_adversarial.py)
# =============================================================================


class TestAutoChunkingEdgeCases:
    """Tests for auto-chunking boundary conditions (0, 1, 9, 10, 11, 100, 101 items)."""

    def test_chunk_zero_requests(self) -> None:
        """0 requests results in empty list of chunks."""
        chunks = _chunk_requests([])
        assert chunks == []
        assert _count_chunks(0) == 0

    def test_chunk_one_request(self) -> None:
        """1 request results in single chunk with 1 item."""
        requests = [BatchRequest("/tasks/1", "GET")]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 1
        assert len(chunks[0]) == 1
        assert _count_chunks(1) == 1

    def test_chunk_nine_requests(self) -> None:
        """9 requests (just under limit) results in single chunk."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(9)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 1
        assert len(chunks[0]) == 9
        assert _count_chunks(9) == 1

    def test_chunk_ten_requests(self) -> None:
        """10 requests (exactly at limit) results in single chunk."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(10)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 1
        assert len(chunks[0]) == 10
        assert _count_chunks(10) == 1

    def test_chunk_eleven_requests(self) -> None:
        """11 requests (just over limit) results in 2 chunks (10 + 1)."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(11)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 1
        assert _count_chunks(11) == 2

    def test_chunk_hundred_requests(self) -> None:
        """100 requests results in exactly 10 chunks."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(100)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 10
        assert all(len(c) == 10 for c in chunks)
        assert _count_chunks(100) == 10

    def test_chunk_hundred_one_requests(self) -> None:
        """101 requests results in 11 chunks (10x10 + 1)."""
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(101)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 11
        assert all(len(c) == 10 for c in chunks[:10])
        assert len(chunks[10]) == 1
        assert _count_chunks(101) == 11

    async def test_execute_zero_requests(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async with 0 requests returns empty list without HTTP call."""
        results = await batch_client.execute_async([])
        assert results == []
        mock_http.request.assert_not_called()

    async def test_execute_nine_requests_single_chunk(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """9 requests executes in single chunk."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {}} for _ in range(9)
        ]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(9)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 9
        assert mock_http.request.call_count == 1

    async def test_execute_hundred_requests_ten_chunks(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """100 requests executes in 10 chunks sequentially."""
        mock_http.request.side_effect = [
            [
                {"status_code": 200, "body": {"data": {"gid": str(i + j * 10)}}}
                for i in range(10)
            ]
            for j in range(10)
        ]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(100)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 100
        assert mock_http.request.call_count == 10
        assert [r.request_index for r in results] == list(range(100))

    async def test_execute_hundred_one_requests_eleven_chunks(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """101 requests executes in 11 chunks."""
        responses = [
            [{"status_code": 200, "body": {}} for _ in range(10)] for _ in range(10)
        ]
        responses.append([{"status_code": 200, "body": {}}])  # 11th chunk
        mock_http.request.side_effect = responses

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(101)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 101
        assert mock_http.request.call_count == 11


# =============================================================================
# Partial Failure Scenarios (merged from test_batch_adversarial.py)
# =============================================================================


class TestPartialFailureScenarios:
    """Tests for various partial failure patterns in multi-chunk batches."""

    async def test_all_fail(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """All requests fail."""
        mock_http.request.return_value = [
            {"status_code": 404, "body": {"errors": [{"message": f"Not found {i}"}]}}
            for i in range(5)
        ]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(5)]
        results = await batch_client.execute_async(requests)

        assert all(not r.success for r in results)
        assert all(r.error is not None for r in results)

    async def test_first_fails_rest_succeed(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """First request fails, rest succeed."""
        responses = [
            {"status_code": 400, "body": {"errors": [{"message": "Bad request"}]}},
        ] + [
            {"status_code": 200, "body": {"data": {"gid": str(i)}}} for i in range(1, 5)
        ]
        mock_http.request.return_value = responses

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(5)]
        results = await batch_client.execute_async(requests)

        assert not results[0].success
        assert all(r.success for r in results[1:])

    async def test_last_fails_rest_succeed(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Last request fails, rest succeed."""
        responses = [
            {"status_code": 200, "body": {"data": {"gid": str(i)}}} for i in range(4)
        ] + [
            {"status_code": 500, "body": {"errors": [{"message": "Server error"}]}},
        ]
        mock_http.request.return_value = responses

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(5)]
        results = await batch_client.execute_async(requests)

        assert all(r.success for r in results[:-1])
        assert not results[-1].success

    async def test_alternating_success_failure(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Alternating success/failure pattern."""
        responses = []
        for i in range(6):
            if i % 2 == 0:
                responses.append(
                    {"status_code": 200, "body": {"data": {"gid": str(i)}}}
                )
            else:
                responses.append(
                    {"status_code": 404, "body": {"errors": [{"message": "Not found"}]}}
                )
        mock_http.request.return_value = responses

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(6)]
        results = await batch_client.execute_async(requests)

        for i, result in enumerate(results):
            if i % 2 == 0:
                assert result.success, f"Expected success at index {i}"
            else:
                assert not result.success, f"Expected failure at index {i}"

    async def test_middle_chunk_has_failures(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Middle chunk in multi-chunk batch has failures."""
        chunk1 = [{"status_code": 200, "body": {}} for _ in range(10)]
        chunk2 = [
            {"status_code": 200, "body": {}}
            if i % 2 == 0
            else {"status_code": 404, "body": {}}
            for i in range(10)
        ]
        chunk3 = [{"status_code": 200, "body": {}} for _ in range(5)]

        mock_http.request.side_effect = [chunk1, chunk2, chunk3]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(25)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 25
        assert all(r.success for r in results[:10])
        for i, r in enumerate(results[10:20]):
            if i % 2 == 0:
                assert r.success
            else:
                assert not r.success
        assert all(r.success for r in results[20:])

    async def test_chunk_endpoint_failure_raises_exception(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Batch endpoint 5xx failure raises AsanaError, not BatchResult."""
        mock_http.request.side_effect = AsanaError(
            "Service unavailable",
            status_code=503,
        )

        requests = [BatchRequest("/tasks/1", "GET")]
        with pytest.raises(AsanaError) as exc_info:
            await batch_client.execute_async(requests)
        assert exc_info.value.status_code == 503


# =============================================================================
# BatchRequest Validation Edge Cases (merged from test_batch_adversarial.py)
# =============================================================================


class TestBatchRequestValidationEdgeCases:
    """Tests for BatchRequest validation edge cases."""

    def test_empty_path_rejected(self) -> None:
        """Empty path is rejected (doesn't start with /)."""
        with pytest.raises(ValueError) as exc_info:
            BatchRequest(relative_path="", method="GET")
        assert "relative_path must start with '/'" in str(exc_info.value)

    def test_path_with_only_slash(self) -> None:
        """Path with only slash is accepted."""
        req = BatchRequest(relative_path="/", method="GET")
        assert req.relative_path == "/"

    def test_very_long_path(self) -> None:
        """Very long path (1000+ chars) is accepted."""
        long_path = "/" + "a" * 1000
        req = BatchRequest(relative_path=long_path, method="GET")
        assert req.relative_path == long_path
        assert len(req.to_action_dict()["relative_path"]) == 1001

    def test_method_variations_invalid(self) -> None:
        """Invalid HTTP methods are rejected."""
        invalid_methods = [
            "PATCH",
            "OPTIONS",
            "HEAD",
            "CONNECT",
            "TRACE",
            "",
            " ",
            "GE T",
        ]
        for method in invalid_methods:
            with pytest.raises(ValueError) as exc_info:
                BatchRequest(relative_path="/tasks", method=method)
            assert "method must be one of" in str(exc_info.value)

    def test_all_valid_methods_mixed_case(self) -> None:
        """All valid methods work in mixed case."""
        mixed_methods = ["Get", "pOsT", "PuT", "DeLeTe"]
        for method in mixed_methods:
            req = BatchRequest(relative_path="/tasks", method=method)
            assert req.method == method
            assert req.to_action_dict()["method"] == method.upper()

    def test_large_data_payload(self) -> None:
        """Large data payload is accepted."""
        large_data = {
            "name": "A" * 10000,
            "notes": "B" * 50000,
            "custom_fields": {f"field_{i}": f"value_{i}" for i in range(100)},
        }
        req = BatchRequest(relative_path="/tasks", method="POST", data=large_data)
        assert req.data == large_data
        action = req.to_action_dict()
        assert action["data"] == large_data

    def test_empty_data_dict(self) -> None:
        """Empty data dict is included in action."""
        req = BatchRequest(relative_path="/tasks", method="POST", data={})
        action = req.to_action_dict()
        assert "data" in action
        assert action["data"] == {}

    def test_nested_data_structure(self) -> None:
        """Deeply nested data structure is preserved."""
        nested_data = {
            "level1": {"level2": {"level3": {"level4": {"value": [1, 2, 3]}}}}
        }
        req = BatchRequest(relative_path="/tasks", method="POST", data=nested_data)
        action = req.to_action_dict()
        assert action["data"]["level1"]["level2"]["level3"]["level4"]["value"] == [
            1,
            2,
            3,
        ]


# =============================================================================
# BatchResult Status Code Boundary Tests (merged from test_batch_adversarial.py)
# =============================================================================


class TestBatchResultPropertyEdgeCases:
    """Tests for BatchResult property edge cases with various status codes."""

    def test_status_199_is_failure(self) -> None:
        """199 status is failure (below 2xx range)."""
        result = BatchResult(status_code=199)
        assert not result.success
        assert result.error is not None

    def test_status_300_is_failure(self) -> None:
        """300 is failure (3xx redirect range)."""
        result = BatchResult(status_code=300)
        assert not result.success

    def test_status_429_is_failure(self) -> None:
        """429 Rate Limited is failure."""
        result = BatchResult(status_code=429)
        assert not result.success

    def test_status_502_is_failure(self) -> None:
        """502 Bad Gateway is failure."""
        result = BatchResult(status_code=502)
        assert not result.success

    def test_missing_body_failure(self) -> None:
        """Failure with missing body still provides default error message."""
        result = BatchResult(status_code=404, body=None)
        assert not result.success
        assert result.error is not None
        assert result.error.message == "Batch action failed"

    def test_missing_headers(self) -> None:
        """Result with missing headers is valid."""
        result = BatchResult(status_code=200, body={"data": {}}, headers=None)
        assert result.headers is None
        assert result.success

    def test_error_empty_errors_array(self) -> None:
        """Empty errors array uses default message."""
        result = BatchResult(status_code=400, body={"errors": []})
        assert result.error is not None
        assert result.error.message == "Batch action failed"

    def test_error_missing_message_field(self) -> None:
        """Missing message field in error uses default."""
        result = BatchResult(status_code=400, body={"errors": [{"code": "INVALID"}]})
        assert result.error is not None
        assert "Unknown error" in result.error.message

    def test_error_with_non_list_errors(self) -> None:
        """Non-list errors field causes AttributeError (documents known behavior).

        BUG FOUND: When body["errors"] is a string instead of a list,
        the implementation iterates over the string characters and calls
        .get() on each character, causing AttributeError.

        Severity: Low - Asana API always returns errors as a list.
        """
        result = BatchResult(status_code=400, body={"errors": "Something went wrong"})
        with pytest.raises(AttributeError):
            _ = result.error

    def test_error_preserves_status_code(self) -> None:
        """Error preserves original status code."""
        for status_code in [400, 401, 403, 404, 429, 500, 502, 503]:
            result = BatchResult(status_code=status_code, body={})
            assert result.error is not None
            assert result.error.status_code == status_code

    def test_data_with_list_data_value(self) -> None:
        """Data returns None when data value is a list (not dict)."""
        result = BatchResult(
            status_code=200, body={"data": [{"gid": "1"}, {"gid": "2"}]}
        )
        assert result.data is None

    def test_data_on_failure_returns_none(self) -> None:
        """Data property returns None for failed results even if body has data."""
        result = BatchResult(
            status_code=404,
            body={"data": {"gid": "123"}},
        )
        assert result.data is None


# =============================================================================
# BatchSummary Statistics Tests (merged from test_batch_adversarial.py)
# =============================================================================


class TestBatchSummaryStatistics:
    """Tests for BatchSummary accuracy with large result sets."""

    def test_large_all_success(self) -> None:
        """Large batch (100) all success has correct statistics."""
        results = [BatchResult(status_code=200, request_index=i) for i in range(100)]
        summary = BatchSummary(results=results)
        assert summary.total == 100
        assert summary.succeeded == 100
        assert summary.failed == 0
        assert summary.all_succeeded is True

    def test_large_all_failure(self) -> None:
        """Large batch (100) all failure has correct statistics."""
        results = [BatchResult(status_code=500, request_index=i) for i in range(100)]
        summary = BatchSummary(results=results)
        assert summary.total == 100
        assert summary.succeeded == 0
        assert summary.failed == 100
        assert summary.all_succeeded is False

    def test_large_mixed_results(self) -> None:
        """Large batch with 75%/25% mixed results has accurate counts."""
        results = []
        for i in range(100):
            if i % 4 == 0:
                results.append(BatchResult(status_code=404, request_index=i))
            else:
                results.append(BatchResult(status_code=200, request_index=i))

        summary = BatchSummary(results=results)
        assert summary.total == 100
        assert summary.succeeded == 75
        assert summary.failed == 25

    def test_succeeded_plus_failed_equals_total(self) -> None:
        """succeeded + failed always equals total across various result sets."""
        test_cases = [
            [],
            [BatchResult(status_code=200)],
            [BatchResult(status_code=404)],
            [BatchResult(status_code=200, request_index=i) for i in range(50)]
            + [BatchResult(status_code=404, request_index=i) for i in range(50, 100)],
        ]
        for results in test_cases:
            summary = BatchSummary(results=results)
            assert summary.succeeded + summary.failed == summary.total


# =============================================================================
# Convenience Method Edge Cases (merged from test_batch_adversarial.py)
# =============================================================================


class TestConvenienceMethodEdgeCases:
    """Tests for convenience method edge cases."""

    async def test_create_tasks_empty_list(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """create_tasks_async with empty list returns empty without HTTP call."""
        results = await batch_client.create_tasks_async([])
        assert results == []
        mock_http.request.assert_not_called()

    async def test_update_tasks_empty_list(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """update_tasks_async with empty list returns empty without HTTP call."""
        results = await batch_client.update_tasks_async([])
        assert results == []
        mock_http.request.assert_not_called()

    async def test_delete_tasks_empty_list(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_tasks_async with empty list returns empty without HTTP call."""
        results = await batch_client.delete_tasks_async([])
        assert results == []
        mock_http.request.assert_not_called()

    async def test_create_tasks_large_batch(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """create_tasks_async with 105 tasks chunks correctly (11 chunks)."""
        responses = [
            [{"status_code": 201, "body": {"data": {"gid": str(i)}}} for i in range(10)]
            for _ in range(10)
        ]
        responses.append(
            [{"status_code": 201, "body": {"data": {"gid": str(i)}}} for i in range(5)]
        )
        mock_http.request.side_effect = responses

        tasks = [{"name": f"Task {i}"} for i in range(105)]
        results = await batch_client.create_tasks_async(tasks)

        assert len(results) == 105
        assert mock_http.request.call_count == 11
        assert all(r.success for r in results)

    async def test_create_tasks_partial_failure(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """create_tasks_async handles partial failures."""
        mock_http.request.return_value = [
            {"status_code": 201, "body": {"data": {"gid": "1"}}},
            {"status_code": 400, "body": {"errors": [{"message": "Missing name"}]}},
            {"status_code": 201, "body": {"data": {"gid": "3"}}},
        ]

        tasks = [
            {"name": "Task 1", "projects": ["proj1"]},
            {},  # Missing required name
            {"name": "Task 3", "projects": ["proj1"]},
        ]
        results = await batch_client.create_tasks_async(tasks)

        assert len(results) == 3
        assert results[0].success
        assert not results[1].success
        assert results[2].success

    async def test_update_tasks_verifies_request_structure(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """update_tasks_async builds correct request structure with opt_fields."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {"data": {"gid": "task1"}}},
            {"status_code": 200, "body": {"data": {"gid": "task2"}}},
        ]

        updates = [
            ("task1", {"completed": True, "assignee": "user1"}),
            ("task2", {"name": "Renamed"}),
        ]
        await batch_client.update_tasks_async(updates, opt_fields=["gid", "name"])

        call_args = mock_http.request.call_args
        actions = call_args[1]["json"]["data"]["actions"]

        assert actions[0]["relative_path"] == "/tasks/task1"
        assert actions[0]["method"] == "PUT"
        assert actions[0]["data"] == {"completed": True, "assignee": "user1"}
        assert actions[0]["options"] == {"opt_fields": "gid,name"}

    async def test_delete_tasks_verifies_request_structure(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_tasks_async builds correct request structure (no data key)."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {}},
            {"status_code": 200, "body": {}},
        ]

        await batch_client.delete_tasks_async(["gid1", "gid2"])

        call_args = mock_http.request.call_args
        actions = call_args[1]["json"]["data"]["actions"]

        assert actions[0]["relative_path"] == "/tasks/gid1"
        assert actions[0]["method"] == "DELETE"
        assert "data" not in actions[0]  # DELETE has no data


# =============================================================================
# Request Index Correlation Tests (merged from test_batch_adversarial.py)
# =============================================================================


class TestRequestIndexCorrelation:
    """Tests verifying request_index correctly correlates results across chunks."""

    async def test_request_indices_sequential_multi_chunk(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Request indices are 0-N across multiple chunks."""
        chunk1 = [{"status_code": 200, "body": {}} for _ in range(10)]
        chunk2 = [{"status_code": 200, "body": {}} for _ in range(10)]
        chunk3 = [{"status_code": 200, "body": {}} for _ in range(5)]
        mock_http.request.side_effect = [chunk1, chunk2, chunk3]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(25)]
        results = await batch_client.execute_async(requests)

        assert [r.request_index for r in results] == list(range(25))

    async def test_request_indices_preserved_with_failures(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Request indices are correct even when some requests fail."""
        chunk1 = [
            {"status_code": 200 if i % 2 == 0 else 404, "body": {}} for i in range(10)
        ]
        chunk2 = [
            {"status_code": 200 if i % 2 == 0 else 500, "body": {}} for i in range(5)
        ]
        mock_http.request.side_effect = [chunk1, chunk2]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(15)]
        results = await batch_client.execute_async(requests)

        assert [r.request_index for r in results] == list(range(15))

        for i, r in enumerate(results):
            expected_success = i % 2 == 0 if i < 10 else (i - 10) % 2 == 0
            assert r.success == expected_success, (
                f"Index {i}: expected success={expected_success}"
            )


# =============================================================================
# from_asana_response Edge Cases (merged from test_batch_adversarial.py)
# =============================================================================


class TestFromAsanaResponseEdgeCases:
    """Tests for BatchResult.from_asana_response edge cases."""

    def test_missing_status_code_defaults_to_500(self) -> None:
        """Missing status_code defaults to 500."""
        result = BatchResult.from_asana_response({}, request_index=0)
        assert result.status_code == 500

    def test_missing_body_defaults_to_none(self) -> None:
        """Missing body defaults to None."""
        result = BatchResult.from_asana_response({"status_code": 200}, request_index=0)
        assert result.body is None

    def test_all_fields_present(self) -> None:
        """All fields are correctly mapped."""
        response = {
            "status_code": 201,
            "body": {"data": {"gid": "123"}},
            "headers": {"X-Custom": "value"},
        }
        result = BatchResult.from_asana_response(response, request_index=42)

        assert result.status_code == 201
        assert result.body == {"data": {"gid": "123"}}
        assert result.headers == {"X-Custom": "value"}
        assert result.request_index == 42

    def test_extra_fields_ignored(self) -> None:
        """Extra fields in response are ignored."""
        response = {
            "status_code": 200,
            "body": {},
            "headers": {},
            "extra_field": "ignored",
        }
        result = BatchResult.from_asana_response(response, request_index=0)
        assert result.status_code == 200
        assert not hasattr(result, "extra_field")


# =============================================================================
# Response Parsing Edge Cases (merged from test_batch_adversarial.py)
# =============================================================================


class TestResponseParsingEdgeCases:
    """Tests for edge cases in batch response parsing."""

    async def test_empty_response_list(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Empty response list returns empty results."""
        mock_http.request.return_value = []

        requests = [BatchRequest("/tasks/1", "GET")]
        results = await batch_client.execute_async(requests)

        assert results == []

    async def test_response_dict_without_data(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Response dict without 'data' key wraps as single result."""
        mock_http.request.return_value = {
            "status_code": 200,
            "body": {"data": {"gid": "1"}},
        }

        requests = [BatchRequest("/tasks/1", "GET")]
        results = await batch_client.execute_async(requests)

        assert len(results) == 1
        assert results[0].success


# =============================================================================
# BATCH_SIZE_LIMIT Constant (merged from test_batch_adversarial.py)
# =============================================================================


class TestBatchSizeLimitConstant:
    """Verify BATCH_SIZE_LIMIT matches Asana's documented limit."""

    def test_batch_size_limit_used_in_chunking(self) -> None:
        """Chunking respects BATCH_SIZE_LIMIT at both boundary values."""
        # Test at boundary
        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(BATCH_SIZE_LIMIT)]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 1
        assert len(chunks[0]) == BATCH_SIZE_LIMIT

        # Test just over boundary
        requests = [
            BatchRequest(f"/tasks/{i}", "GET") for i in range(BATCH_SIZE_LIMIT + 1)
        ]
        chunks = _chunk_requests(requests)
        assert len(chunks) == 2
        assert len(chunks[0]) == BATCH_SIZE_LIMIT
        assert len(chunks[1]) == 1
