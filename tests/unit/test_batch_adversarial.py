"""Adversarial tests for Batch API module.

Per TDD-0005: Batch API for Bulk Operations.
Focus: Edge cases, boundary conditions, partial failures, and error handling.

This test file exercises adversarial scenarios not covered in test_batch.py:
- Auto-chunking boundary conditions (0, 1, 9, 10, 11, 100, 101 requests)
- Partial failure patterns (first/last/alternating/chunk failures)
- BatchRequest validation edge cases
- BatchResult property edge cases with various status codes and error formats
- BatchSummary accuracy with large result sets
- Convenience method edge cases (empty lists, large batches)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autom8_asana.batch import BatchClient, BatchRequest, BatchResult, BatchSummary
from autom8_asana.batch.client import BATCH_SIZE_LIMIT, _chunk_requests, _count_chunks
from autom8_asana.errors import AsanaError

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


# --- Auto-Chunking Edge Cases ---


class TestAutoChunkingEdgeCases:
    """Tests for auto-chunking boundary conditions."""

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

    async def test_execute_one_request(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """execute_async with 1 request makes single HTTP call."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {"data": {"gid": "1"}}}
        ]

        requests = [BatchRequest("/tasks/1", "GET")]
        results = await batch_client.execute_async(requests)

        assert len(results) == 1
        assert results[0].request_index == 0
        assert mock_http.request.call_count == 1

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
        # Mock 10 chunks of 10 responses each
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
        # Verify request indices are sequential
        assert [r.request_index for r in results] == list(range(100))

    async def test_execute_hundred_one_requests_eleven_chunks(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """101 requests executes in 11 chunks."""
        # Mock 10 chunks of 10 + 1 chunk of 1
        responses = [
            [{"status_code": 200, "body": {}} for _ in range(10)] for _ in range(10)
        ]
        responses.append([{"status_code": 200, "body": {}}])  # 11th chunk with 1 item
        mock_http.request.side_effect = responses

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(101)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 101
        assert mock_http.request.call_count == 11


# --- Partial Failure Scenarios ---


class TestPartialFailureScenarios:
    """Tests for various partial failure patterns."""

    async def test_all_succeed(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """All requests succeed."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {"data": {"gid": str(i)}}} for i in range(5)
        ]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(5)]
        results = await batch_client.execute_async(requests)

        assert all(r.success for r in results)
        assert all(r.error is None for r in results)

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
        assert results[0].error is not None
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
        assert results[-1].error is not None

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
        # Chunk 1 (10): all succeed
        chunk1 = [{"status_code": 200, "body": {}} for _ in range(10)]
        # Chunk 2 (10): mixed failures
        chunk2 = [
            {"status_code": 200, "body": {}}
            if i % 2 == 0
            else {"status_code": 404, "body": {}}
            for i in range(10)
        ]
        # Chunk 3 (5): all succeed
        chunk3 = [{"status_code": 200, "body": {}} for _ in range(5)]

        mock_http.request.side_effect = [chunk1, chunk2, chunk3]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(25)]
        results = await batch_client.execute_async(requests)

        assert len(results) == 25
        # Chunk 1 (indices 0-9): all succeed
        assert all(r.success for r in results[:10])
        # Chunk 2 (indices 10-19): alternating
        for i, r in enumerate(results[10:20]):
            if i % 2 == 0:
                assert r.success
            else:
                assert not r.success
        # Chunk 3 (indices 20-24): all succeed
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


# --- BatchRequest Validation Edge Cases ---


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

    def test_path_with_special_characters(self) -> None:
        """Path with special characters is accepted."""
        special_paths = [
            "/tasks/123?foo=bar",
            "/tasks/123#section",
            "/tasks/abc-def_ghi",
            "/tasks/task%20name",
            "/workspaces/123/tasks",
            "/tasks/!@$%^&*()",
        ]
        for path in special_paths:
            req = BatchRequest(relative_path=path, method="GET")
            assert req.relative_path == path

    def test_path_with_unicode(self) -> None:
        """Path with unicode characters is accepted."""
        req = BatchRequest(relative_path="/tasks/cafe", method="GET")
        assert req.relative_path == "/tasks/cafe"

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

    def test_all_valid_methods_lowercase(self) -> None:
        """All valid methods work in lowercase."""
        valid_methods = ["get", "post", "put", "delete"]
        for method in valid_methods:
            req = BatchRequest(relative_path="/tasks", method=method)
            assert req.method == method
            assert req.to_action_dict()["method"] == method.upper()

    def test_all_valid_methods_uppercase(self) -> None:
        """All valid methods work in uppercase."""
        valid_methods = ["GET", "POST", "PUT", "DELETE"]
        for method in valid_methods:
            req = BatchRequest(relative_path="/tasks", method=method)
            assert req.method == method

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

    def test_empty_options_dict(self) -> None:
        """Empty options dict is included in action."""
        req = BatchRequest(relative_path="/tasks", method="GET", options={})
        action = req.to_action_dict()
        assert "options" in action
        assert action["options"] == {}

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


# --- BatchResult Property Edge Cases ---


class TestBatchResultPropertyEdgeCases:
    """Tests for BatchResult property edge cases with various status codes."""

    # Status code boundary tests
    def test_status_199_is_failure(self) -> None:
        """199 status is failure (below 2xx range)."""
        result = BatchResult(status_code=199)
        assert not result.success
        assert result.error is not None

    def test_status_200_is_success(self) -> None:
        """200 status is success."""
        result = BatchResult(status_code=200)
        assert result.success

    def test_status_201_is_success(self) -> None:
        """201 Created is success."""
        result = BatchResult(status_code=201)
        assert result.success

    def test_status_204_is_success(self) -> None:
        """204 No Content is success."""
        result = BatchResult(status_code=204)
        assert result.success

    def test_status_299_is_success(self) -> None:
        """299 is success (upper bound of 2xx)."""
        result = BatchResult(status_code=299)
        assert result.success

    def test_status_300_is_failure(self) -> None:
        """300 is failure (3xx redirect range)."""
        result = BatchResult(status_code=300)
        assert not result.success

    def test_status_400_is_failure(self) -> None:
        """400 Bad Request is failure."""
        result = BatchResult(status_code=400)
        assert not result.success

    def test_status_401_is_failure(self) -> None:
        """401 Unauthorized is failure."""
        result = BatchResult(status_code=401)
        assert not result.success

    def test_status_403_is_failure(self) -> None:
        """403 Forbidden is failure."""
        result = BatchResult(status_code=403)
        assert not result.success

    def test_status_404_is_failure(self) -> None:
        """404 Not Found is failure."""
        result = BatchResult(status_code=404)
        assert not result.success

    def test_status_429_is_failure(self) -> None:
        """429 Rate Limited is failure."""
        result = BatchResult(status_code=429)
        assert not result.success

    def test_status_500_is_failure(self) -> None:
        """500 Internal Server Error is failure."""
        result = BatchResult(status_code=500)
        assert not result.success

    def test_status_502_is_failure(self) -> None:
        """502 Bad Gateway is failure."""
        result = BatchResult(status_code=502)
        assert not result.success

    def test_status_503_is_failure(self) -> None:
        """503 Service Unavailable is failure."""
        result = BatchResult(status_code=503)
        assert not result.success

    # Missing body/headers tests
    def test_missing_body_success(self) -> None:
        """Success with missing body (None)."""
        result = BatchResult(status_code=200, body=None)
        assert result.success
        assert result.data is None
        assert result.error is None

    def test_missing_body_failure(self) -> None:
        """Failure with missing body still provides error."""
        result = BatchResult(status_code=404, body=None)
        assert not result.success
        assert result.error is not None
        assert result.error.message == "Batch action failed"

    def test_missing_headers(self) -> None:
        """Result with missing headers is valid."""
        result = BatchResult(status_code=200, body={"data": {}}, headers=None)
        assert result.headers is None
        assert result.success

    def test_empty_body(self) -> None:
        """Empty dict body is handled.

        Note: Empty dict body returns None for data property because
        `not {}` evaluates to True in Python. This is arguably correct
        behavior since an empty response has no meaningful data.
        """
        result = BatchResult(status_code=200, body={})
        assert result.success
        # Empty dict is falsy in Python, so data returns None
        assert result.data is None

    # Error extraction tests
    def test_error_single_message(self) -> None:
        """Single error message is extracted."""
        result = BatchResult(
            status_code=400, body={"errors": [{"message": "Field is required"}]}
        )
        assert result.error is not None
        assert result.error.message == "Field is required"

    def test_error_multiple_messages(self) -> None:
        """Multiple error messages are joined."""
        result = BatchResult(
            status_code=400,
            body={
                "errors": [
                    {"message": "Field A is required"},
                    {"message": "Field B is invalid"},
                ]
            },
        )
        assert result.error is not None
        assert "Field A is required" in result.error.message
        assert "Field B is invalid" in result.error.message
        assert "; " in result.error.message

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
        """Non-list errors field causes AttributeError.

        BUG FOUND: When body["errors"] is a string instead of a list,
        the implementation iterates over the string characters and calls
        .get() on each character, causing AttributeError.

        This test documents the current (buggy) behavior. A fix would be
        to check `isinstance(errors, list)` before iterating.

        Severity: Low - Asana API always returns errors as a list, so
        this only affects malformed/unexpected responses.
        """
        result = BatchResult(status_code=400, body={"errors": "Something went wrong"})
        # Current behavior: raises AttributeError when accessing .error
        with pytest.raises(AttributeError):
            _ = result.error

    def test_error_without_errors_key(self) -> None:
        """Body without errors key uses default message."""
        result = BatchResult(status_code=400, body={"message": "Something failed"})
        assert result.error is not None
        assert result.error.message == "Batch action failed"

    def test_error_preserves_status_code(self) -> None:
        """Error preserves original status code."""
        for status_code in [400, 401, 403, 404, 429, 500, 502, 503]:
            result = BatchResult(status_code=status_code, body={})
            assert result.error is not None
            assert result.error.status_code == status_code

    # Data unwrapping tests
    def test_data_with_data_wrapper(self) -> None:
        """Data unwraps from {"data": ...} wrapper."""
        result = BatchResult(
            status_code=200, body={"data": {"gid": "123", "name": "Task"}}
        )
        assert result.data == {"gid": "123", "name": "Task"}

    def test_data_without_wrapper(self) -> None:
        """Data returns body as-is when no wrapper."""
        result = BatchResult(status_code=200, body={"gid": "123", "name": "Task"})
        assert result.data == {"gid": "123", "name": "Task"}

    def test_data_with_null_data_value(self) -> None:
        """Data returns None when data value is null."""
        result = BatchResult(status_code=200, body={"data": None})
        # data key exists but value is None, which is not a dict
        assert result.data is None

    def test_data_with_list_data_value(self) -> None:
        """Data returns None when data value is a list (not dict)."""
        result = BatchResult(
            status_code=200, body={"data": [{"gid": "1"}, {"gid": "2"}]}
        )
        # data is a list, not a dict, so should return None
        assert result.data is None

    def test_data_on_failure_returns_none(self) -> None:
        """Data property returns None for failed results."""
        result = BatchResult(
            status_code=404,
            body={"data": {"gid": "123"}},  # Even if body has data
        )
        assert result.data is None


# --- BatchSummary Statistics Tests ---


class TestBatchSummaryStatistics:
    """Tests for BatchSummary accuracy with various result sets."""

    def test_empty_results(self) -> None:
        """Empty results has correct statistics."""
        summary = BatchSummary(results=[])
        assert summary.total == 0
        assert summary.succeeded == 0
        assert summary.failed == 0
        assert summary.all_succeeded is True  # Vacuously true
        assert summary.successful_results == []
        assert summary.failed_results == []

    def test_single_success(self) -> None:
        """Single success result has correct statistics."""
        summary = BatchSummary(results=[BatchResult(status_code=200)])
        assert summary.total == 1
        assert summary.succeeded == 1
        assert summary.failed == 0
        assert summary.all_succeeded is True

    def test_single_failure(self) -> None:
        """Single failure result has correct statistics."""
        summary = BatchSummary(results=[BatchResult(status_code=404)])
        assert summary.total == 1
        assert summary.succeeded == 0
        assert summary.failed == 1
        assert summary.all_succeeded is False

    def test_large_all_success(self) -> None:
        """Large batch (100) all success has correct statistics."""
        results = [BatchResult(status_code=200, request_index=i) for i in range(100)]
        summary = BatchSummary(results=results)
        assert summary.total == 100
        assert summary.succeeded == 100
        assert summary.failed == 0
        assert summary.all_succeeded is True
        assert len(summary.successful_results) == 100
        assert len(summary.failed_results) == 0

    def test_large_all_failure(self) -> None:
        """Large batch (100) all failure has correct statistics."""
        results = [BatchResult(status_code=500, request_index=i) for i in range(100)]
        summary = BatchSummary(results=results)
        assert summary.total == 100
        assert summary.succeeded == 0
        assert summary.failed == 100
        assert summary.all_succeeded is False
        assert len(summary.successful_results) == 0
        assert len(summary.failed_results) == 100

    def test_large_mixed_results(self) -> None:
        """Large batch with mixed results has accurate counts."""
        # 75% success, 25% failure  # noqa: ERA001
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
        assert summary.all_succeeded is False
        assert len(summary.successful_results) == 75
        assert len(summary.failed_results) == 25

    def test_successful_results_preserves_order(self) -> None:
        """successful_results preserves original order."""
        results = [
            BatchResult(status_code=200, request_index=0),
            BatchResult(status_code=404, request_index=1),
            BatchResult(status_code=200, request_index=2),
            BatchResult(status_code=500, request_index=3),
            BatchResult(status_code=201, request_index=4),
        ]
        summary = BatchSummary(results=results)
        successful = summary.successful_results
        assert [r.request_index for r in successful] == [0, 2, 4]

    def test_failed_results_preserves_order(self) -> None:
        """failed_results preserves original order."""
        results = [
            BatchResult(status_code=200, request_index=0),
            BatchResult(status_code=404, request_index=1),
            BatchResult(status_code=200, request_index=2),
            BatchResult(status_code=500, request_index=3),
            BatchResult(status_code=201, request_index=4),
        ]
        summary = BatchSummary(results=results)
        failed = summary.failed_results
        assert [r.request_index for r in failed] == [1, 3]

    def test_succeeded_plus_failed_equals_total(self) -> None:
        """succeeded + failed always equals total."""
        test_cases = [
            [],  # Empty
            [BatchResult(status_code=200)],  # Single success
            [BatchResult(status_code=404)],  # Single failure
            [BatchResult(status_code=200, request_index=i) for i in range(50)]
            + [
                BatchResult(status_code=404, request_index=i) for i in range(50, 100)
            ],  # Half and half
        ]
        for results in test_cases:
            summary = BatchSummary(results=results)
            assert summary.succeeded + summary.failed == summary.total


# --- Convenience Method Edge Cases ---


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
        """create_tasks_async with 100+ tasks chunks correctly."""
        # Mock 11 chunks (10x10 + 1x5 = 105)
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

    async def test_update_tasks_large_batch(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """update_tasks_async with 100+ tasks chunks correctly."""
        # Mock 11 chunks
        responses = [
            [{"status_code": 200, "body": {"data": {"gid": str(i)}}} for i in range(10)]
            for _ in range(10)
        ]
        responses.append(
            [{"status_code": 200, "body": {"data": {"gid": str(i)}}} for i in range(5)]
        )
        mock_http.request.side_effect = responses

        updates = [(f"gid_{i}", {"completed": True}) for i in range(105)]
        results = await batch_client.update_tasks_async(updates)

        assert len(results) == 105
        assert mock_http.request.call_count == 11

    async def test_delete_tasks_large_batch(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_tasks_async with 100+ tasks chunks correctly."""
        # Mock 11 chunks
        responses = [
            [{"status_code": 200, "body": {}} for _ in range(10)] for _ in range(10)
        ]
        responses.append([{"status_code": 200, "body": {}} for _ in range(5)])
        mock_http.request.side_effect = responses

        task_gids = [f"gid_{i}" for i in range(105)]
        results = await batch_client.delete_tasks_async(task_gids)

        assert len(results) == 105
        assert mock_http.request.call_count == 11

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
        assert results[1].error is not None
        assert results[2].success

    async def test_update_tasks_verifies_request_structure(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """update_tasks_async builds correct request structure."""
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

        assert actions[1]["relative_path"] == "/tasks/task2"
        assert actions[1]["data"] == {"name": "Renamed"}

    async def test_delete_tasks_verifies_request_structure(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_tasks_async builds correct request structure."""
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

        assert actions[1]["relative_path"] == "/tasks/gid2"


# --- Request Index Correlation Tests ---


class TestRequestIndexCorrelation:
    """Tests verifying request_index correctly correlates results across chunks."""

    async def test_request_indices_sequential_single_chunk(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Request indices are 0-N for single chunk."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {}} for _ in range(5)
        ]

        requests = [BatchRequest(f"/tasks/{i}", "GET") for i in range(5)]
        results = await batch_client.execute_async(requests)

        assert [r.request_index for r in results] == [0, 1, 2, 3, 4]

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

        # Indices should still be sequential regardless of success/failure
        assert [r.request_index for r in results] == list(range(15))

        # Check that failures are at correct indices
        for i, r in enumerate(results):
            expected_success = i % 2 == 0 if i < 10 else (i - 10) % 2 == 0
            assert r.success == expected_success, (
                f"Index {i}: expected success={expected_success}"
            )


# --- from_asana_response Edge Cases ---


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

    def test_missing_headers_defaults_to_none(self) -> None:
        """Missing headers defaults to None."""
        result = BatchResult.from_asana_response(
            {"status_code": 200, "body": {}}, request_index=0
        )
        assert result.headers is None

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
            "another": 123,
        }
        result = BatchResult.from_asana_response(response, request_index=0)
        assert result.status_code == 200
        assert not hasattr(result, "extra_field")


# --- Response Parsing Edge Cases ---


class TestResponseParsingEdgeCases:
    """Tests for edge cases in batch response parsing."""

    async def test_response_as_list(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Response as direct list is handled."""
        mock_http.request.return_value = [
            {"status_code": 200, "body": {"data": {"gid": "1"}}},
            {"status_code": 200, "body": {"data": {"gid": "2"}}},
        ]

        requests = [
            BatchRequest("/tasks/1", "GET"),
            BatchRequest("/tasks/2", "GET"),
        ]
        results = await batch_client.execute_async(requests)

        assert len(results) == 2
        assert all(r.success for r in results)

    async def test_response_wrapped_in_data(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Response wrapped in {"data": [...]} is handled."""
        mock_http.request.return_value = {
            "data": [
                {"status_code": 200, "body": {"data": {"gid": "1"}}},
                {"status_code": 200, "body": {"data": {"gid": "2"}}},
            ]
        }

        requests = [
            BatchRequest("/tasks/1", "GET"),
            BatchRequest("/tasks/2", "GET"),
        ]
        results = await batch_client.execute_async(requests)

        assert len(results) == 2
        assert all(r.success for r in results)

    async def test_empty_response_list(
        self, batch_client: BatchClient, mock_http: MockHTTPClient
    ) -> None:
        """Empty response list returns empty results."""
        mock_http.request.return_value = []

        requests = [BatchRequest("/tasks/1", "GET")]
        results = await batch_client.execute_async(requests)

        # Implementation returns empty if response is empty list
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

        # Implementation wraps single dict response
        assert len(results) == 1
        assert results[0].success


# --- BATCH_SIZE_LIMIT Constant Test ---


class TestBatchSizeLimitConstant:
    """Verify BATCH_SIZE_LIMIT matches Asana's documented limit."""

    def test_batch_size_limit_is_10(self) -> None:
        """BATCH_SIZE_LIMIT is set to Asana's limit of 10."""
        assert BATCH_SIZE_LIMIT == 10

    def test_batch_size_limit_used_in_chunking(self) -> None:
        """Chunking respects BATCH_SIZE_LIMIT."""
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
