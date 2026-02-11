"""Tests for Batch API module.

Per TDD-0005: Batch API for Bulk Operations.
Per ADR-0010: Sequential chunk execution for batch operations.
"""

from __future__ import annotations

import pytest

from autom8_asana.batch import BatchClient, BatchRequest, BatchResult, BatchSummary
from autom8_asana.batch.client import BATCH_SIZE_LIMIT, _chunk_requests, _count_chunks
from autom8_asana.config import AsanaConfig
from autom8_asana.exceptions import AsanaError, SyncInAsyncContextError

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

        # Check info and debug messages were logged
        info_messages = [msg for level, msg in logger.messages if level == "info"]
        debug_messages = [msg for level, msg in logger.messages if level == "debug"]

        assert any("Starting batch" in msg for msg in info_messages)
        assert any("complete" in msg for msg in info_messages)
        assert any("Chunk" in msg for msg in debug_messages)


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
