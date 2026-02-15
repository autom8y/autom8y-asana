"""Unit tests for cache backend integration with ConnectionManagers.

Per TDD-CONNECTION-LIFECYCLE-001 Phase 1:
Verifies RedisCacheProvider and S3CacheProvider correctly delegate
to connection managers when provided, and work unchanged without them.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch


from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig
from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config
from autom8_asana.core.connections import ConnectionState, HealthCheckResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_redis_config() -> RedisConfig:
    """Create test Redis config."""
    return RedisConfig(host="localhost", port=6379, db=0)


def _make_s3_config() -> S3Config:
    """Create test S3 config."""
    return S3Config(
        bucket="test-bucket",
        prefix="test-cache/",
        region="us-east-1",
        endpoint_url="http://localhost:4566",
    )


def _make_redis_manager_mock(
    state: ConnectionState = ConnectionState.HEALTHY,
) -> MagicMock:
    """Create a mock RedisConnectionManager."""
    manager = MagicMock()
    manager.name = "redis"
    manager.state = state

    mock_conn = MagicMock()
    mock_conn.ping.return_value = True
    manager.get_connection.return_value = mock_conn

    manager.health_check.return_value = HealthCheckResult(
        state=state,
        checked_at=time.monotonic(),
        latency_ms=1.0,
    )
    return manager


def _make_s3_manager_mock(
    state: ConnectionState = ConnectionState.HEALTHY,
) -> MagicMock:
    """Create a mock S3ConnectionManager."""
    manager = MagicMock()
    manager.name = "s3"
    manager.state = state
    manager.get_client.return_value = MagicMock()
    manager.health_check.return_value = HealthCheckResult(
        state=state,
        checked_at=time.monotonic(),
        latency_ms=5.0,
    )
    return manager


# ---------------------------------------------------------------------------
# Redis Backend with Manager
# ---------------------------------------------------------------------------


class TestRedisCacheProviderWithManager:
    """Test RedisCacheProvider with injected RedisConnectionManager."""

    @patch("redis.ConnectionPool")
    @patch("redis.Redis")
    def test_get_connection_delegates_to_manager(
        self, mock_redis: MagicMock, mock_pool: MagicMock
    ) -> None:
        """_get_connection delegates to manager.get_connection when provided."""
        manager = _make_redis_manager_mock()

        provider = RedisCacheProvider(
            config=_make_redis_config(),
            connection_manager=manager,
        )

        conn = provider._get_connection()
        manager.get_connection.assert_called_once()
        assert conn == manager.get_connection.return_value

    @patch("redis.ConnectionPool")
    def test_is_healthy_delegates_to_manager(self, mock_pool: MagicMock) -> None:
        """is_healthy delegates to manager.health_check when provided."""
        manager = _make_redis_manager_mock(state=ConnectionState.HEALTHY)

        provider = RedisCacheProvider(
            config=_make_redis_config(),
            connection_manager=manager,
        )

        assert provider.is_healthy() is True
        manager.health_check.assert_called_once()

    @patch("redis.ConnectionPool")
    def test_is_healthy_returns_false_when_manager_disconnected(
        self, mock_pool: MagicMock
    ) -> None:
        """is_healthy returns False when manager reports DISCONNECTED."""
        manager = _make_redis_manager_mock(state=ConnectionState.DISCONNECTED)

        provider = RedisCacheProvider(
            config=_make_redis_config(),
            connection_manager=manager,
        )

        assert provider.is_healthy() is False

    @patch("redis.ConnectionPool")
    def test_no_pool_created_when_manager_provided(self, mock_pool: MagicMock) -> None:
        """No internal pool is created when connection_manager is provided."""
        manager = _make_redis_manager_mock()

        provider = RedisCacheProvider(
            config=_make_redis_config(),
            connection_manager=manager,
        )

        # _initialize_pool should NOT have been called
        mock_pool.assert_not_called()


class TestRedisCacheProviderBackwardCompat:
    """Verify RedisCacheProvider works without connection_manager (backward compat)."""

    @patch("redis.ConnectionPool")
    def test_default_construction_works(self, mock_pool: MagicMock) -> None:
        """Provider without connection_manager creates pool normally."""
        provider = RedisCacheProvider(config=_make_redis_config())

        assert provider._connection_manager is None
        mock_pool.assert_called_once()


# ---------------------------------------------------------------------------
# S3 Backend with Manager
# ---------------------------------------------------------------------------


class TestS3CacheProviderWithManager:
    """Test S3CacheProvider with injected S3ConnectionManager."""

    @patch("boto3.client")
    def test_get_client_delegates_to_manager(self, mock_boto: MagicMock) -> None:
        """_get_client delegates to manager.get_client when provided."""
        manager = _make_s3_manager_mock()

        provider = S3CacheProvider(
            config=_make_s3_config(),
            connection_manager=manager,
        )

        client = provider._get_client()
        manager.get_client.assert_called_once()
        assert client == manager.get_client.return_value

    @patch("boto3.client")
    def test_is_healthy_delegates_to_manager(self, mock_boto: MagicMock) -> None:
        """is_healthy delegates to manager.health_check when provided."""
        manager = _make_s3_manager_mock(state=ConnectionState.HEALTHY)

        provider = S3CacheProvider(
            config=_make_s3_config(),
            connection_manager=manager,
        )

        assert provider.is_healthy() is True
        manager.health_check.assert_called_once()

    @patch("boto3.client")
    def test_is_healthy_returns_false_when_manager_disconnected(
        self, mock_boto: MagicMock
    ) -> None:
        """is_healthy returns False when manager reports DISCONNECTED."""
        manager = _make_s3_manager_mock(state=ConnectionState.DISCONNECTED)

        provider = S3CacheProvider(
            config=_make_s3_config(),
            connection_manager=manager,
        )

        assert provider.is_healthy() is False

    @patch("boto3.client")
    def test_no_client_created_when_manager_provided(
        self, mock_boto: MagicMock
    ) -> None:
        """No internal boto3 client is created when connection_manager is provided."""
        manager = _make_s3_manager_mock()

        provider = S3CacheProvider(
            config=_make_s3_config(),
            connection_manager=manager,
        )

        # _initialize_client should NOT have been called
        mock_boto.assert_not_called()


class TestS3CacheProviderBackwardCompat:
    """Verify S3CacheProvider works without connection_manager (backward compat)."""

    @patch("boto3.client")
    def test_default_construction_works(self, mock_boto: MagicMock) -> None:
        """Provider without connection_manager creates client normally."""
        provider = S3CacheProvider(config=_make_s3_config())

        assert provider._connection_manager is None
        mock_boto.assert_called_once()
