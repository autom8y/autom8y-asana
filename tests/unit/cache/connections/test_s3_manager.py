"""Tests for S3ConnectionManager.

Verifies lazy client creation, health check caching, circuit breaker
integration, double-check locking, and lifecycle management.

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from autom8_asana.cache.backends.s3 import S3Config
from autom8_asana.core.connections import ConnectionManager, ConnectionState
from autom8_asana.core.exceptions import CacheConnectionError
from autom8_asana.core.retry import CBState, CircuitBreaker, CircuitBreakerConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_boto3_module() -> MagicMock:
    """Mock boto3 module with client factory."""
    mock = MagicMock()
    mock_client = MagicMock()
    mock_client.head_bucket.return_value = {}
    mock.client.return_value = mock_client
    return mock


@pytest.fixture
def s3_config() -> S3Config:
    return S3Config(bucket="test-bucket", region="us-east-1")


@pytest.fixture
def make_manager(s3_config: S3Config, mock_boto3_module: MagicMock):
    """Factory that creates an S3ConnectionManager with mocked boto3."""
    from autom8_asana.cache.connections.s3 import S3ConnectionManager

    def _make(
        circuit_breaker: CircuitBreaker | None = None,
        health_check_cache_ttl: float = 30.0,
        bucket: str | None = None,
    ) -> S3ConnectionManager:
        config = s3_config
        if bucket is not None:
            config = S3Config(bucket=bucket, region=s3_config.region)

        mgr = S3ConnectionManager.__new__(S3ConnectionManager)
        mgr._config = config
        mgr._circuit_breaker = circuit_breaker
        mgr._health_cache_ttl = health_check_cache_ttl
        mgr._connect_timeout = 10
        mgr._read_timeout = 30
        mgr._lock = __import__("threading").Lock()
        mgr._client = None
        mgr._boto3_module = mock_boto3_module
        mgr._last_health = None
        mgr._closed = False
        return mgr

    return _make


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestS3ManagerProtocol:
    """Verify S3ConnectionManager satisfies ConnectionManager protocol."""

    def test_satisfies_connection_manager_protocol(self, make_manager: object) -> None:
        mgr = make_manager()
        assert isinstance(mgr, ConnectionManager)

    def test_name_is_s3(self, make_manager: object) -> None:
        mgr = make_manager()
        assert mgr.name == "s3"


# ---------------------------------------------------------------------------
# Client management (lazy creation)
# ---------------------------------------------------------------------------


class TestS3ClientManagement:
    """Verify lazy client creation and double-check locking."""

    def test_get_client_creates_lazily(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        mgr = make_manager()
        # No client yet
        assert mgr._client is None

        client = mgr.get_client()
        assert client is mock_boto3_module.client.return_value
        assert mgr._client is not None

    def test_get_client_reuses_existing_client(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        mgr = make_manager()
        client1 = mgr.get_client()
        client2 = mgr.get_client()
        assert client1 is client2
        # Should only call boto3.client once (lazy creation)
        mock_boto3_module.client.assert_called_once()

    def test_get_client_raises_after_close(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr.close()
        with pytest.raises(CacheConnectionError, match="closed"):
            mgr.get_client()

    def test_get_client_raises_when_creation_fails(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        # Make client creation return None by having boto3.client raise
        mock_boto3_module.client.side_effect = OSError("network error")
        mgr = make_manager()
        with pytest.raises(CacheConnectionError, match="Failed to create"):
            mgr.get_client()


# ---------------------------------------------------------------------------
# State property
# ---------------------------------------------------------------------------


class TestS3ManagerState:
    """Verify state property reflects client and circuit breaker state."""

    def test_state_healthy_by_default(self, make_manager: object) -> None:
        mgr = make_manager()
        assert mgr.state == ConnectionState.HEALTHY

    def test_state_disconnected_after_close(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr.close()
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_state_disconnected_when_no_bucket(self, make_manager: object) -> None:
        mgr = make_manager(bucket="")
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_state_disconnected_when_boto3_unavailable(
        self, make_manager: object
    ) -> None:
        mgr = make_manager()
        mgr._boto3_module = None
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_state_disconnected_when_circuit_open(self, make_manager: object) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, name="s3"))
        mgr = make_manager(circuit_breaker=cb)
        cb.record_failure(Exception("fail"))
        assert cb.state == CBState.OPEN
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_state_degraded_when_circuit_half_open(self, make_manager: object) -> None:
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0.0,
                name="s3",
            )
        )
        mgr = make_manager(circuit_breaker=cb)
        cb.record_failure(Exception("fail"))
        time.sleep(0.01)
        assert cb.state == CBState.HALF_OPEN
        assert mgr.state == ConnectionState.DEGRADED


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestS3HealthCheck:
    """Verify health check probing, caching, and circuit breaker gating."""

    def test_health_check_returns_healthy_on_success(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        mgr = make_manager()
        result = mgr.health_check()
        assert result.state == ConnectionState.HEALTHY
        assert result.latency_ms > 0.0
        mock_boto3_module.client.return_value.head_bucket.assert_called_once_with(
            Bucket="test-bucket"
        )

    def test_health_check_caching_avoids_duplicate_probes(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        """Call health_check() twice within TTL, verify HeadBucket runs only once."""
        mgr = make_manager(health_check_cache_ttl=30.0)

        mgr.health_check()
        call_count = mock_boto3_module.client.return_value.head_bucket.call_count

        mgr.health_check()
        assert (
            mock_boto3_module.client.return_value.head_bucket.call_count == call_count
        )

    def test_health_check_force_bypasses_cache(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        mgr = make_manager(health_check_cache_ttl=30.0)

        mgr.health_check()
        count_after_first = mock_boto3_module.client.return_value.head_bucket.call_count

        mgr.health_check(force=True)
        assert (
            mock_boto3_module.client.return_value.head_bucket.call_count
            > count_after_first
        )

    def test_health_check_returns_disconnected_on_failure(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        mock_boto3_module.client.return_value.head_bucket.side_effect = OSError(
            "connection refused"
        )
        mgr = make_manager()
        result = mgr.health_check()
        assert result.state == ConnectionState.DISCONNECTED
        assert "connection refused" in result.detail

    def test_health_check_circuit_breaker_open_no_probe(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        """When circuit is OPEN, health check returns DISCONNECTED without I/O."""
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, name="s3"))
        mgr = make_manager(circuit_breaker=cb)

        # Trip circuit
        cb.record_failure(Exception("fail"))

        mock_boto3_module.client.return_value.head_bucket.reset_mock()

        result = mgr.health_check()
        assert result.state == ConnectionState.DISCONNECTED
        assert result.detail == "circuit_breaker_open"
        mock_boto3_module.client.return_value.head_bucket.assert_not_called()

    def test_health_check_no_boto3(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr._boto3_module = None
        result = mgr.health_check(force=True)
        assert result.state == ConnectionState.DISCONNECTED
        assert result.detail == "boto3_not_available"

    def test_health_check_no_bucket(self, make_manager: object) -> None:
        mgr = make_manager(bucket="")
        result = mgr.health_check(force=True)
        assert result.state == ConnectionState.DISCONNECTED
        assert result.detail == "no_bucket_configured"


# ---------------------------------------------------------------------------
# Close / lifecycle
# ---------------------------------------------------------------------------


class TestS3ManagerClose:
    """Verify close behavior and idempotency."""

    def test_close_nulls_client(
        self, make_manager: object, mock_boto3_module: MagicMock
    ) -> None:
        mgr = make_manager()
        mgr.get_client()  # Create client
        assert mgr._client is not None

        mgr.close()
        assert mgr._client is None
        assert mgr._closed is True

    def test_close_is_idempotent(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr.close()
        mgr.close()  # Second close should not raise
        assert mgr._closed is True

    def test_close_async(self, make_manager: object) -> None:
        mgr = make_manager()
        asyncio.run(mgr.close_async())
        assert mgr._closed is True

    def test_context_manager_sync(self, make_manager: object) -> None:
        mgr = make_manager()
        with mgr as m:
            assert m is mgr
        assert mgr._closed is True

    def test_context_manager_async(self, make_manager: object) -> None:
        async def _test() -> None:
            mgr = make_manager()
            async with mgr as m:
                assert m is mgr
            assert mgr._closed is True

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Health check async
# ---------------------------------------------------------------------------


class TestS3HealthCheckAsync:
    """Verify async health check variant."""

    def test_health_check_async_returns_result(self, make_manager: object) -> None:
        mgr = make_manager()
        result = asyncio.run(mgr.health_check_async())
        assert result.state == ConnectionState.HEALTHY
