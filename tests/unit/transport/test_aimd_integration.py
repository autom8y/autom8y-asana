"""Integration tests for AIMD adaptive semaphore with AsanaHttpClient.

Per TDD-GAP-04/Section 8.3: Tests verifying AIMD behavior through the
AsanaHttpClient request path with mocked HTTP responses.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from autom8_asana.config import AsanaConfig, ConcurrencyConfig
from autom8_asana.transport.adaptive_semaphore import (
    AsyncAdaptiveSemaphore,
    FixedSemaphoreAdapter,
)
from autom8_asana.transport.asana_http import AsanaHttpClient


class MockAuthProvider:
    """Mock auth provider for tests."""

    def __init__(self, token: str = "test_token"):
        self._token = token

    def get_secret(self, key: str) -> str:
        return self._token


def _create_mock_platform_client(mock_response):
    """Create a properly mocked platform client with _client attribute."""
    mock_httpx_client = AsyncMock()
    mock_httpx_client.request = AsyncMock(return_value=mock_response)

    mock_platform = AsyncMock()
    mock_platform._client = mock_httpx_client

    return mock_platform, mock_httpx_client


def _make_429_response(retry_after: int = 30) -> MagicMock:
    """Create a mock 429 response."""
    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {
        "Retry-After": str(retry_after),
        "X-Request-Id": "test-req-id",
        "retry-after": str(retry_after),
    }
    resp.json.return_value = {"errors": [{"message": "Rate limited"}]}
    resp.text = '{"errors": [{"message": "Rate limited"}]}'
    return resp


def _make_200_response(data: dict | None = None) -> MagicMock:
    """Create a mock 200 response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": data or {"gid": "123"}}
    return resp


class TestAIMDIntegration429:
    """Tests for 429 triggering AIMD decrease through _request()."""

    @pytest.mark.asyncio
    async def test_429_triggers_aimd_decrease_in_request(self):
        """Mock 429 response, verify semaphore window decreased."""
        config = AsanaConfig(
            concurrency=ConcurrencyConfig(read_limit=50, write_limit=15)
        )
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)
        # Disable retry so the 429 raises immediately
        client._retry_policy = None

        mock_response = _make_429_response()
        mock_platform, _ = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        # Verify initial state
        assert client._read_semaphore.current_limit == 50

        from autom8_asana.exceptions import RateLimitError

        with pytest.raises(RateLimitError):
            await client.get("/tasks/123")

        # AIMD should have halved the read window
        assert client._read_semaphore.current_limit == 25

    @pytest.mark.asyncio
    async def test_success_triggers_aimd_increase_in_request(self):
        """Mock 200 response, verify semaphore window increased after decrease."""
        config = AsanaConfig(
            concurrency=ConcurrencyConfig(
                read_limit=50,
                write_limit=15,
                aimd_grace_period_seconds=0.0,
                aimd_increase_interval_seconds=0.0,
            )
        )
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        mock_platform_429, _ = _create_mock_platform_client(_make_429_response())
        client._platform_client = mock_platform_429
        client._retry_policy = None

        from autom8_asana.exceptions import RateLimitError

        with pytest.raises(RateLimitError):
            await client.get("/tasks/123")
        assert client._read_semaphore.current_limit == 25

        # Now send a 200
        mock_platform_200, _ = _create_mock_platform_client(
            _make_200_response({"gid": "123"})
        )
        client._platform_client = mock_platform_200

        result = await client.get("/tasks/123")
        assert result == {"gid": "123"}

        # Window should have increased by 1
        assert client._read_semaphore.current_limit == 26

    @pytest.mark.asyncio
    async def test_429_does_not_affect_other_pool(self):
        """Mock 429 on read, verify write semaphore unchanged."""
        config = AsanaConfig(
            concurrency=ConcurrencyConfig(read_limit=50, write_limit=15)
        )
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)
        client._retry_policy = None

        mock_response = _make_429_response()
        mock_platform, _ = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        from autom8_asana.exceptions import RateLimitError

        with pytest.raises(RateLimitError):
            await client.get("/tasks/123")  # GET uses read semaphore

        # Read semaphore halved, write semaphore unchanged
        assert client._read_semaphore.current_limit == 25
        assert client._write_semaphore.current_limit == 15


class TestAIMDDisabled:
    """Tests for aimd_enabled=False fallback."""

    def test_aimd_disabled_uses_fixed_semaphore(self):
        """Set aimd_enabled=False, verify FixedSemaphoreAdapter used."""
        config = AsanaConfig(
            concurrency=ConcurrencyConfig(
                read_limit=50, write_limit=15, aimd_enabled=False
            )
        )
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        assert isinstance(client._read_semaphore, FixedSemaphoreAdapter)
        assert isinstance(client._write_semaphore, FixedSemaphoreAdapter)
        assert client._read_semaphore.ceiling == 50
        assert client._write_semaphore.ceiling == 15

    def test_aimd_enabled_uses_adaptive_semaphore(self):
        """Default (aimd_enabled=True) uses AsyncAdaptiveSemaphore."""
        config = AsanaConfig(
            concurrency=ConcurrencyConfig(read_limit=50, write_limit=15)
        )
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        assert isinstance(client._read_semaphore, AsyncAdaptiveSemaphore)
        assert isinstance(client._write_semaphore, AsyncAdaptiveSemaphore)


class TestExistingAPIUnchanged:
    """Verify public API signatures remain unchanged."""

    @pytest.mark.asyncio
    async def test_existing_client_api_unchanged(self):
        """Verify .get(), .post(), .put(), .delete(), .get_paginated(), .request()
        signatures unchanged."""
        config = AsanaConfig()
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        mock_response = _make_200_response({"gid": "123"})
        mock_platform, _ = _create_mock_platform_client(mock_response)
        client._platform_client = mock_platform

        # All should work without error
        result = await client.get("/tasks/123")
        assert result == {"gid": "123"}

        result = await client.post("/tasks", json={"name": "New"})
        assert result == {"gid": "123"}

        result = await client.put("/tasks/123", json={"name": "Updated"})
        assert result == {"gid": "123"}

        result = await client.delete("/tasks/123")
        assert result == {"gid": "123"}

        result = await client.request("GET", path="/tasks/123")
        assert result == {"gid": "123"}

        # Paginated
        paginated_response = MagicMock()
        paginated_response.status_code = 200
        paginated_response.json.return_value = {
            "data": [{"gid": "1"}],
            "next_page": None,
        }
        mock_platform2, _ = _create_mock_platform_client(paginated_response)
        client._platform_client = mock_platform2

        data, offset = await client.get_paginated("/tasks")
        assert data == [{"gid": "1"}]
        assert offset is None


class TestRetryReacquiresSlot:
    """Test that retry loop properly reacquires slots."""

    @pytest.mark.asyncio
    async def test_retry_loop_reacquires_slot(self):
        """Mock 429 then 200, verify two slot acquisitions."""
        config = AsanaConfig(
            concurrency=ConcurrencyConfig(
                read_limit=50,
                write_limit=15,
                aimd_grace_period_seconds=0.0,
                aimd_increase_interval_seconds=0.0,
            )
        )
        auth = MockAuthProvider()
        client = AsanaHttpClient(config, auth)

        # First call returns 429, second returns 200
        resp_429 = _make_429_response()
        resp_200 = _make_200_response({"gid": "456"})

        mock_httpx = AsyncMock()
        mock_httpx.request = AsyncMock(side_effect=[resp_429, resp_200])

        mock_platform = AsyncMock()
        mock_platform._client = mock_httpx
        client._platform_client = mock_platform

        # Patch retry wait to be instant
        client._wait_for_retry = AsyncMock()

        result = await client.get("/tasks/456")
        assert result == {"gid": "456"}

        # Should have made 2 requests (429 + 200)
        assert mock_httpx.request.call_count == 2

        # Read semaphore should have decreased (from 429) then increased (from 200)
        # 50 -> 25 (reject) -> 26 (succeed)
        assert client._read_semaphore.current_limit == 26
