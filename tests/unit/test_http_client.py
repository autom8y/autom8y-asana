"""Tests for AsyncHTTPClient transport layer."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from autom8_asana.config import (
    AsanaConfig,
    ConcurrencyConfig,
    RetryConfig,
)
from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    ForbiddenError,
    GoneError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)
from autom8_asana.transport.http import AsyncHTTPClient


class MockAuthProvider:
    """Mock auth provider for testing."""

    def get_secret(self, key: str) -> str:
        return "test-token-12345"


class MockLogger:
    """Mock logger that records calls."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("debug", msg))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("info", msg))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("warning", msg))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("error", msg))

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("exception", msg))


@pytest.fixture
def config() -> AsanaConfig:
    """Default test configuration."""
    return AsanaConfig(
        base_url="https://app.asana.com/api/1.0",
        retry=RetryConfig(
            max_retries=3,
            base_delay=0.01,  # Fast retries for tests
            max_delay=1.0,
            jitter=False,  # Deterministic for testing
        ),
        concurrency=ConcurrencyConfig(read_limit=10, write_limit=5),
    )


@pytest.fixture
def auth_provider() -> MockAuthProvider:
    """Mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def logger() -> MockLogger:
    """Mock logger."""
    return MockLogger()


@pytest.fixture
def client(config: AsanaConfig, auth_provider: MockAuthProvider) -> AsyncHTTPClient:
    """Create HTTP client for testing."""
    return AsyncHTTPClient(config, auth_provider)


class TestRequestSuccessUnwrapsData:
    """Test that successful responses have 'data' unwrapped."""

    @respx.mock
    async def test_request_success_unwraps_data(
        self, client: AsyncHTTPClient
    ) -> None:
        """Successful response returns unwrapped 'data' field."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"gid": "123", "name": "Test Task"}},
            )
        )

        result = await client.get("/tasks/123")

        assert result == {"gid": "123", "name": "Test Task"}
        await client.close()

    @respx.mock
    async def test_request_success_no_data_wrapper(
        self, client: AsyncHTTPClient
    ) -> None:
        """Response without 'data' wrapper is returned as-is."""
        respx.get("https://app.asana.com/api/1.0/events").mock(
            return_value=httpx.Response(
                200,
                json={"sync": "token123", "has_more": False},
            )
        )

        result = await client.get("/events")

        assert result == {"sync": "token123", "has_more": False}
        await client.close()


class TestRequestErrorCreatesTypedException:
    """Test that HTTP errors create appropriate exception types."""

    @respx.mock
    async def test_request_error_401_authentication(
        self, client: AsyncHTTPClient
    ) -> None:
        """401 response raises AuthenticationError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                401,
                json={"errors": [{"message": "Invalid token"}]},
            )
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await client.get("/tasks/123")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.message
        await client.close()

    @respx.mock
    async def test_request_error_403_forbidden(
        self, client: AsyncHTTPClient
    ) -> None:
        """403 response raises ForbiddenError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                403,
                json={"errors": [{"message": "Access denied"}]},
            )
        )

        with pytest.raises(ForbiddenError) as exc_info:
            await client.get("/tasks/123")

        assert exc_info.value.status_code == 403
        await client.close()

    @respx.mock
    async def test_request_error_404_not_found(
        self, client: AsyncHTTPClient
    ) -> None:
        """404 response raises NotFoundError."""
        respx.get("https://app.asana.com/api/1.0/tasks/999").mock(
            return_value=httpx.Response(
                404,
                json={"errors": [{"message": "Task not found"}]},
            )
        )

        with pytest.raises(NotFoundError) as exc_info:
            await client.get("/tasks/999")

        assert exc_info.value.status_code == 404
        await client.close()

    @respx.mock
    async def test_request_error_410_gone(
        self, client: AsyncHTTPClient
    ) -> None:
        """410 response raises GoneError."""
        respx.get("https://app.asana.com/api/1.0/tasks/deleted").mock(
            return_value=httpx.Response(
                410,
                json={"errors": [{"message": "Resource permanently deleted"}]},
            )
        )

        with pytest.raises(GoneError) as exc_info:
            await client.get("/tasks/deleted")

        assert exc_info.value.status_code == 410
        await client.close()

    @respx.mock
    async def test_request_error_429_rate_limit(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """429 response raises RateLimitError when retries exhausted."""
        # Configure no retries to test immediate error
        no_retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(max_retries=0),
        )
        client = AsyncHTTPClient(no_retry_config, auth_provider)

        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                429,
                json={"errors": [{"message": "Rate limit exceeded"}]},
                headers={"Retry-After": "30"},
            )
        )

        with pytest.raises(RateLimitError) as exc_info:
            await client.get("/tasks/123")

        assert exc_info.value.status_code == 429
        await client.close()

    @respx.mock
    async def test_request_error_500_server_error(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """500 response raises ServerError when not retryable."""
        # 500 is not in default retryable_status_codes, so it should error immediately
        no_retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(max_retries=0),
        )
        client = AsyncHTTPClient(no_retry_config, auth_provider)

        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                json={"errors": [{"message": "Internal server error"}]},
            )
        )

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        assert exc_info.value.status_code == 500
        await client.close()


class TestRequestRateLimitRetry:
    """Test retry behavior for 429 rate limit responses."""

    @respx.mock
    async def test_request_rate_limit_retry_with_retry_after(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """429 with Retry-After header triggers retry and eventually succeeds."""
        # Configure with retries enabled
        retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(max_retries=3, base_delay=0.01, jitter=False),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks/123")
        # First call returns 429, second returns success
        route.side_effect = [
            httpx.Response(
                429,
                json={"errors": [{"message": "Rate limit"}]},
                headers={"Retry-After": "1"},
            ),
            httpx.Response(
                200,
                json={"data": {"gid": "123", "name": "Task"}},
            ),
        ]

        result = await client.get("/tasks/123")

        assert result == {"gid": "123", "name": "Task"}
        assert route.call_count == 2
        await client.close()


class TestRequestServerErrorRetry:
    """Test retry behavior for server errors (503, 504)."""

    @respx.mock
    async def test_request_server_error_retry_503(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """503 Service Unavailable triggers retry."""
        retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(
                max_retries=3,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks/123")
        route.side_effect = [
            httpx.Response(503, json={"errors": [{"message": "Service unavailable"}]}),
            httpx.Response(200, json={"data": {"gid": "123"}}),
        ]

        result = await client.get("/tasks/123")

        assert result == {"gid": "123"}
        assert route.call_count == 2
        await client.close()

    @respx.mock
    async def test_request_server_error_retry_504(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """504 Gateway Timeout triggers retry."""
        retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(
                max_retries=3,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks/123")
        route.side_effect = [
            httpx.Response(504, json={"errors": [{"message": "Gateway timeout"}]}),
            httpx.Response(504, json={"errors": [{"message": "Gateway timeout"}]}),
            httpx.Response(200, json={"data": {"gid": "123"}}),
        ]

        result = await client.get("/tasks/123")

        assert result == {"gid": "123"}
        assert route.call_count == 3
        await client.close()


class TestRequestTimeoutRetry:
    """Test retry behavior for request timeouts."""

    @respx.mock
    async def test_request_timeout_retry_success(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Timeout triggers retry and succeeds on subsequent attempt."""
        retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(
                max_retries=3,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks/123")
        route.side_effect = [
            httpx.TimeoutException("Connection timed out"),
            httpx.Response(200, json={"data": {"gid": "123"}}),
        ]

        result = await client.get("/tasks/123")

        assert result == {"gid": "123"}
        assert route.call_count == 2
        await client.close()

    @respx.mock
    async def test_request_timeout_raises_timeout_error(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Timeout after all retries raises TimeoutError."""
        retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks/123")
        route.side_effect = [
            httpx.TimeoutException("Timeout 1"),
            httpx.TimeoutException("Timeout 2"),
            httpx.TimeoutException("Timeout 3"),
        ]

        with pytest.raises(TimeoutError) as exc_info:
            await client.get("/tasks/123")

        assert "timed out" in str(exc_info.value).lower()
        await client.close()


class TestRequestMaxRetriesExceeded:
    """Test behavior when max retries are exceeded."""

    @respx.mock
    async def test_request_max_retries_exceeded_raises_error(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Error is raised after exhausting all retries."""
        retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        client = AsyncHTTPClient(retry_config, auth_provider)

        route = respx.get("https://app.asana.com/api/1.0/tasks/123")
        route.side_effect = [
            httpx.Response(503, json={"errors": [{"message": "Unavailable"}]}),
            httpx.Response(503, json={"errors": [{"message": "Unavailable"}]}),
            httpx.Response(503, json={"errors": [{"message": "Unavailable"}]}),
        ]

        with pytest.raises(ServerError):
            await client.get("/tasks/123")

        # 1 initial + 2 retries = 3 total
        assert route.call_count == 3
        await client.close()


class TestRequestUsesCorrectSemaphore:
    """Test that GET uses read semaphore, mutations use write semaphore."""

    @respx.mock
    async def test_request_uses_correct_semaphore_get(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """GET request uses read semaphore."""
        # Create client with very limited concurrency to observe behavior
        limited_config = AsanaConfig(
            base_url=config.base_url,
            concurrency=ConcurrencyConfig(read_limit=2, write_limit=1),
        )
        client = AsyncHTTPClient(limited_config, auth_provider)

        # Verify semaphore values
        assert client._read_semaphore._value == 2
        assert client._write_semaphore._value == 1

        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(200, json={"data": {"gid": "123"}})
        )

        await client.get("/tasks/123")

        # Read semaphore should be released
        assert client._read_semaphore._value == 2
        await client.close()

    @respx.mock
    async def test_request_uses_correct_semaphore_post(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """POST request uses write semaphore."""
        limited_config = AsanaConfig(
            base_url=config.base_url,
            concurrency=ConcurrencyConfig(read_limit=2, write_limit=1),
        )
        client = AsyncHTTPClient(limited_config, auth_provider)

        respx.post("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(201, json={"data": {"gid": "456"}})
        )

        await client.post("/tasks", json={"data": {"name": "New Task"}})

        # Write semaphore should be released
        assert client._write_semaphore._value == 1
        await client.close()


class TestConvenienceMethods:
    """Test GET, POST, PUT, DELETE convenience methods."""

    @respx.mock
    async def test_get_convenience_method(self, client: AsyncHTTPClient) -> None:
        """GET convenience method works correctly."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(200, json={"data": {"gid": "123"}})
        )

        result = await client.get("/tasks/123", params={"opt_fields": "name"})

        assert result == {"gid": "123"}
        await client.close()

    @respx.mock
    async def test_post_convenience_method(self, client: AsyncHTTPClient) -> None:
        """POST convenience method works correctly."""
        respx.post("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(201, json={"data": {"gid": "new123"}})
        )

        result = await client.post(
            "/tasks",
            json={"data": {"name": "New Task"}},
            params={"opt_fields": "name"},
        )

        assert result == {"gid": "new123"}
        await client.close()

    @respx.mock
    async def test_put_convenience_method(self, client: AsyncHTTPClient) -> None:
        """PUT convenience method works correctly."""
        respx.put("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(200, json={"data": {"gid": "123", "name": "Updated"}})
        )

        result = await client.put("/tasks/123", json={"data": {"name": "Updated"}})

        assert result == {"gid": "123", "name": "Updated"}
        await client.close()

    @respx.mock
    async def test_delete_convenience_method(self, client: AsyncHTTPClient) -> None:
        """DELETE convenience method works correctly."""
        respx.delete("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )

        result = await client.delete("/tasks/123")

        assert result == {}
        await client.close()


class TestClientLifecycle:
    """Test client creation and cleanup."""

    @respx.mock
    async def test_close_releases_client(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """close() releases the underlying httpx client."""
        client = AsyncHTTPClient(config, auth_provider)

        # Trigger lazy client creation
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        await client.get("/tasks/123")

        # Client should exist
        assert client._client is not None

        # Close client
        await client.close()

        # Client should be None
        assert client._client is None

    async def test_lazy_client_creation(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """HTTP client is created lazily on first request."""
        client = AsyncHTTPClient(config, auth_provider)

        # No client yet
        assert client._client is None

        # Internal method creates client
        http_client = await client._get_client()
        assert http_client is not None
        assert client._client is http_client

        # Subsequent calls return same client
        http_client2 = await client._get_client()
        assert http_client2 is http_client

        await client.close()


class TestInvalidJSONResponse:
    """Test handling of invalid JSON responses on success status codes."""

    @respx.mock
    async def test_invalid_json_raises_asana_error(
        self, client: AsyncHTTPClient
    ) -> None:
        """Invalid JSON response raises AsanaError with context."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                200,
                content=b"This is not JSON",
                headers={"X-Request-Id": "req-abc123"},
            )
        )

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert "Invalid JSON response" in str(error)
        assert "HTTP 200" in str(error)
        assert "req-abc123" in str(error)
        assert "This is not JSON" in str(error)
        await client.close()

    @respx.mock
    async def test_invalid_json_no_request_id(
        self, client: AsyncHTTPClient
    ) -> None:
        """Invalid JSON response without X-Request-Id includes 'unknown'."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                200,
                content=b"<html>Bad Gateway</html>",
            )
        )

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert "request_id=unknown" in str(error)
        assert "<html>Bad Gateway</html>" in str(error)
        await client.close()

    @respx.mock
    async def test_invalid_json_empty_body(
        self, client: AsyncHTTPClient
    ) -> None:
        """Empty response body shows '(empty)' in error."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                200,
                content=b"",
            )
        )

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert "(empty)" in str(error)
        await client.close()


class TestRequestIdInErrors:
    """Test that X-Request-Id is included in error responses."""

    @respx.mock
    async def test_request_id_included_in_404_error(
        self, client: AsyncHTTPClient
    ) -> None:
        """404 error includes X-Request-Id in message."""
        respx.get("https://app.asana.com/api/1.0/tasks/999").mock(
            return_value=httpx.Response(
                404,
                json={"errors": [{"message": "Task not found"}]},
                headers={"X-Request-Id": "req-404-xyz"},
            )
        )

        with pytest.raises(NotFoundError) as exc_info:
            await client.get("/tasks/999")

        assert "req-404-xyz" in str(exc_info.value)
        await client.close()

    @respx.mock
    async def test_request_id_included_in_500_error(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """500 error includes X-Request-Id in message."""
        no_retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(max_retries=0),
        )
        client = AsyncHTTPClient(no_retry_config, auth_provider)

        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                json={"errors": [{"message": "Internal error"}]},
                headers={"X-Request-Id": "req-500-abc"},
            )
        )

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        assert "req-500-abc" in str(exc_info.value)
        await client.close()

    @respx.mock
    async def test_request_id_included_in_rate_limit_error(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """429 rate limit error includes X-Request-Id in message."""
        no_retry_config = AsanaConfig(
            base_url=config.base_url,
            retry=RetryConfig(max_retries=0),
        )
        client = AsyncHTTPClient(no_retry_config, auth_provider)

        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                429,
                json={"errors": [{"message": "Rate limit exceeded"}]},
                headers={
                    "X-Request-Id": "req-429-ratelimit",
                    "Retry-After": "30",
                },
            )
        )

        with pytest.raises(RateLimitError) as exc_info:
            await client.get("/tasks/123")

        assert "req-429-ratelimit" in str(exc_info.value)
        await client.close()

    @respx.mock
    async def test_error_without_request_id_does_not_show_header(
        self, client: AsyncHTTPClient
    ) -> None:
        """Error without X-Request-Id does not include request_id in message."""
        respx.get("https://app.asana.com/api/1.0/tasks/999").mock(
            return_value=httpx.Response(
                404,
                json={"errors": [{"message": "Task not found"}]},
            )
        )

        with pytest.raises(NotFoundError) as exc_info:
            await client.get("/tasks/999")

        # Should not have request_id in message when header is absent
        assert "request_id=" not in str(exc_info.value)
        await client.close()
