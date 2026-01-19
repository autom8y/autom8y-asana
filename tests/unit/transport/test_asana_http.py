"""Unit tests for AsanaHttpClient.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-001: Tests the Asana HTTP client wrapper
that provides backward-compatible API while using autom8y-http platform SDK.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from autom8_asana.config import AsanaConfig
from autom8_asana.exceptions import (
    RateLimitError,
    ServerError,
    TimeoutError,
)
from autom8_asana.transport.asana_http import AsanaHttpClient


class MockAuthProvider:
    """Mock auth provider for tests."""

    def __init__(self, token: str = "test_token"):
        self._token = token

    def get_secret(self, key: str) -> str:
        return self._token


class TestAsanaHttpClientInit:
    """Test AsanaHttpClient initialization."""

    def test_creates_rate_limiter_from_config(self):
        """Creates rate limiter when not provided."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        assert client._rate_limiter is not None
        # The rate limiter should have correct config
        stats = client._rate_limiter.get_stats()
        assert stats["max_tokens"] == 1500

    def test_uses_provided_rate_limiter(self):
        """Uses injected rate limiter."""
        from autom8y_http import TokenBucketRateLimiter, RateLimiterConfig

        config = AsanaConfig()
        auth = MockAuthProvider()
        custom_limiter = TokenBucketRateLimiter(
            config=RateLimiterConfig(max_tokens=100)
        )

        client = AsanaHttpClient(config, auth, rate_limiter=custom_limiter)
        assert client._rate_limiter is custom_limiter

    def test_creates_circuit_breaker_from_config(self):
        """Creates circuit breaker when not provided."""
        from autom8_asana.config import CircuitBreakerConfig

        config = AsanaConfig(circuit_breaker=CircuitBreakerConfig(enabled=True))
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        assert client._circuit_breaker is not None

    def test_creates_retry_policy_from_config(self):
        """Creates retry policy when not provided."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        assert client._retry_policy is not None
        assert client._retry_policy.max_attempts == 4  # 3 retries + 1 initial

    def test_creates_concurrency_semaphores(self):
        """Creates read/write semaphores from config."""
        from autom8_asana.config import ConcurrencyConfig

        config = AsanaConfig(
            concurrency=ConcurrencyConfig(read_limit=10, write_limit=5)
        )
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        assert client._read_semaphore._value == 10
        assert client._write_semaphore._value == 5


def _create_mock_platform_client(mock_response):
    """Create a properly mocked platform client with _client attribute."""
    # Create mock httpx client
    mock_httpx_client = AsyncMock()
    mock_httpx_client.request = AsyncMock(return_value=mock_response)

    # Create platform client mock with _client attribute
    mock_platform = AsyncMock()
    mock_platform._client = mock_httpx_client

    return mock_platform, mock_httpx_client


class TestAsanaHttpClientRequest:
    """Test request methods."""

    @pytest.fixture
    def client(self):
        """Create client with mocked platform client."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)
        return client

    @pytest.mark.asyncio
    async def test_get_returns_unwrapped_data(self, client):
        """GET request unwraps {"data": ...} envelope."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"gid": "123", "name": "Task"}}

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        result = await client.get("/tasks/123")
        assert result == {"gid": "123", "name": "Task"}

    @pytest.mark.asyncio
    async def test_post_includes_json_body(self, client):
        """POST request sends JSON body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"gid": "456"}}

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        result = await client.post("/tasks", json={"name": "New Task"})
        assert result == {"gid": "456"}

        # Verify json was passed
        mock_raw.request.assert_called_with(
            "POST",
            "/tasks",
            params=None,
            json={"name": "New Task"},
            data=None,
        )

    @pytest.mark.asyncio
    async def test_put_request(self, client):
        """PUT request works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"gid": "123", "name": "Updated"}}

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        result = await client.put("/tasks/123", json={"name": "Updated"})
        assert result == {"gid": "123", "name": "Updated"}

    @pytest.mark.asyncio
    async def test_delete_request(self, client):
        """DELETE request works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        result = await client.delete("/tasks/123")
        assert result == {}


class TestAsanaHttpClientPagination:
    """Test paginated request handling."""

    @pytest.fixture
    def client(self):
        """Create client with mocked platform client."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)
        return client

    @pytest.mark.asyncio
    async def test_get_paginated_returns_data_and_offset(self, client):
        """get_paginated returns tuple of (data, next_offset)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"gid": "1"}, {"gid": "2"}],
            "next_page": {"offset": "abc123"},
        }

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        data, next_offset = await client.get_paginated("/tasks")
        assert data == [{"gid": "1"}, {"gid": "2"}]
        assert next_offset == "abc123"

    @pytest.mark.asyncio
    async def test_get_paginated_returns_none_on_last_page(self, client):
        """get_paginated returns None offset on last page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"gid": "3"}],
            "next_page": None,
        }

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        data, next_offset = await client.get_paginated("/tasks")
        assert data == [{"gid": "3"}]
        assert next_offset is None


class TestAsanaHttpClientErrors:
    """Test error handling."""

    @pytest.fixture
    def client(self):
        """Create client with mocked platform client."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)
        return client

    @pytest.mark.asyncio
    async def test_raises_rate_limit_error(self, client):
        """Raises RateLimitError on 429."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {
            "Retry-After": "30",
            "X-Request-Id": "abc",
            "retry-after": "30",
        }
        mock_response.json.return_value = {"errors": [{"message": "Rate limited"}]}
        mock_response.text = '{"errors": [{"message": "Rate limited"}]}'

        mock_platform, mock_httpx = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform
        # Disable retry for this test
        client._retry_policy = None

        with pytest.raises(RateLimitError):
            await client.get("/tasks")

    @pytest.mark.asyncio
    async def test_raises_server_error(self, client):
        """Raises ServerError on 5xx."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {"X-Request-Id": "abc"}
        mock_response.json.return_value = {"errors": [{"message": "Server error"}]}
        mock_response.text = '{"errors": [{"message": "Server error"}]}'

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform
        # Disable retry for this test
        client._retry_policy = None

        with pytest.raises(ServerError):
            await client.get("/tasks")

    @pytest.mark.asyncio
    async def test_raises_timeout_error(self, client):
        """Raises TimeoutError on httpx.TimeoutException."""
        mock_httpx_client = AsyncMock()
        mock_httpx_client.request = AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )

        mock_platform = AsyncMock()
        mock_platform._client = mock_httpx_client
        client._platform_client = mock_platform
        # Disable retry for this test
        client._retry_policy = None

        with pytest.raises(TimeoutError):
            await client.get("/tasks")


class TestAsanaHttpClientRateLimiting:
    """Test rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_acquires_rate_limit_token(self):
        """Request acquires rate limit token."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        # Replace rate limiter with mock
        mock_limiter = AsyncMock()
        mock_limiter.acquire = AsyncMock()
        client._rate_limiter = mock_limiter

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}

        mock_platform, mock_raw = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        await client.get("/tasks")
        mock_limiter.acquire.assert_called_once()


class TestAsanaHttpClientClose:
    """Test client cleanup."""

    @pytest.mark.asyncio
    async def test_close_releases_resources(self):
        """close() releases platform client resources."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        # Create mock platform client
        mock_platform = AsyncMock()
        mock_platform.close = AsyncMock()
        client._platform_client = mock_platform

        await client.close()

        mock_platform.close.assert_called_once()
        assert client._platform_client is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """close() can be called multiple times safely."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        # No platform client created yet
        await client.close()  # Should not raise
        await client.close()  # Should not raise
