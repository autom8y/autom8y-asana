"""Tests for RedisConnectionManager.

Verifies pool creation, connection management, health check caching,
circuit breaker integration, and lifecycle management.

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.cache.backends.redis import RedisConfig
from autom8_asana.core.connections import ConnectionManager, ConnectionState
from autom8_asana.core.exceptions import CacheConnectionError
from autom8_asana.core.retry import CBState, CircuitBreaker, CircuitBreakerConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis_module() -> MagicMock:
    """Mock redis module with ConnectionPool and Redis classes."""
    mock = MagicMock()
    mock.ConnectionPool.return_value = MagicMock()
    mock_conn = MagicMock()
    mock_conn.ping.return_value = True
    mock.Redis.return_value = mock_conn
    return mock


@pytest.fixture
def redis_config() -> RedisConfig:
    return RedisConfig(host="localhost", port=6379, db=0)


@pytest.fixture
def make_manager(redis_config: RedisConfig, mock_redis_module: MagicMock):
    """Factory that creates a RedisConnectionManager with mocked redis module."""
    from autom8_asana.cache.connections.redis import RedisConnectionManager

    def _make(
        circuit_breaker: CircuitBreaker | None = None,
        health_check_cache_ttl: float = 10.0,
    ) -> RedisConnectionManager:
        with patch(
            "autom8_asana.cache.connections.redis.RedisConnectionManager._import_redis"
        ) as mock_import:

            def set_module(self_ref: RedisConnectionManager = None) -> None:  # noqa: ARG001
                pass

            mgr = RedisConnectionManager.__new__(RedisConnectionManager)
            mgr._config = redis_config
            mgr._circuit_breaker = circuit_breaker
            mgr._health_cache_ttl = health_check_cache_ttl
            mgr._lock = __import__("threading").Lock()
            mgr._pool = None
            mgr._redis_module = mock_redis_module
            mgr._last_health = None
            mgr._closed = False
            # Create pool using the mock module
            mgr._pool = mock_redis_module.ConnectionPool(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                socket_timeout=redis_config.socket_timeout,
                socket_connect_timeout=redis_config.socket_connect_timeout,
                max_connections=redis_config.max_connections,
                retry_on_timeout=redis_config.retry_on_timeout,
                decode_responses=redis_config.decode_responses,
                ssl=redis_config.ssl,
                ssl_cert_reqs=None,
            )
            return mgr

        return _make  # pragma: no cover -- unreachable due to patch

    return _make


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestRedisManagerProtocol:
    """Verify RedisConnectionManager satisfies ConnectionManager protocol."""

    def test_satisfies_connection_manager_protocol(self, make_manager: object) -> None:
        mgr = make_manager()
        assert isinstance(mgr, ConnectionManager)

    def test_name_is_redis(self, make_manager: object) -> None:
        mgr = make_manager()
        assert mgr.name == "redis"


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


class TestRedisConnectionManagement:
    """Verify get_connection, pool lifecycle."""

    def test_get_connection_returns_redis_client(
        self, make_manager: object, mock_redis_module: MagicMock
    ) -> None:
        mgr = make_manager()
        conn = mgr.get_connection()
        mock_redis_module.Redis.assert_called_with(connection_pool=mgr._pool)
        assert conn is mock_redis_module.Redis.return_value

    def test_get_connection_raises_after_close(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr.close()
        with pytest.raises(CacheConnectionError, match="closed"):
            mgr.get_connection()

    def test_get_connection_raises_when_pool_is_none(
        self, make_manager: object
    ) -> None:
        mgr = make_manager()
        mgr._pool = None
        with pytest.raises(CacheConnectionError, match="not initialized"):
            mgr.get_connection()


# ---------------------------------------------------------------------------
# State property
# ---------------------------------------------------------------------------


class TestRedisManagerState:
    """Verify state property reflects pool and circuit breaker state."""

    def test_state_healthy_by_default(self, make_manager: object) -> None:
        mgr = make_manager()
        assert mgr.state == ConnectionState.HEALTHY

    def test_state_disconnected_after_close(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr.close()
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_state_disconnected_when_pool_is_none(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr._pool = None
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_state_disconnected_when_circuit_open(self, make_manager: object) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, name="redis"))
        mgr = make_manager(circuit_breaker=cb)

        # Trip the circuit breaker
        cb.record_failure(Exception("fail"))
        assert cb.state == CBState.OPEN
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_state_degraded_when_circuit_half_open(self, make_manager: object) -> None:
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0.0,  # Immediate recovery to HALF_OPEN
                name="redis",
            )
        )
        mgr = make_manager(circuit_breaker=cb)

        # Trip and wait for HALF_OPEN
        cb.record_failure(Exception("fail"))
        time.sleep(0.01)
        assert cb.state == CBState.HALF_OPEN
        assert mgr.state == ConnectionState.DEGRADED


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestRedisHealthCheck:
    """Verify health check probing, caching, and circuit breaker gating."""

    def test_health_check_returns_healthy_on_success(
        self, make_manager: object
    ) -> None:
        mgr = make_manager()
        result = mgr.health_check()
        assert result.state == ConnectionState.HEALTHY
        assert result.latency_ms > 0
        assert result.detail == ""

    def test_health_check_caching_avoids_duplicate_probes(
        self, make_manager: object, mock_redis_module: MagicMock
    ) -> None:
        """Call health_check() twice within TTL, verify probe runs only once."""
        mgr = make_manager(health_check_cache_ttl=10.0)

        result1 = mgr.health_check()
        # Reset call count after first probe
        ping_call_count = mock_redis_module.Redis.return_value.ping.call_count

        result2 = mgr.health_check()
        # Should return cached result, no additional ping
        assert mock_redis_module.Redis.return_value.ping.call_count == ping_call_count
        assert result2.state == ConnectionState.HEALTHY

    def test_health_check_force_bypasses_cache(
        self, make_manager: object, mock_redis_module: MagicMock
    ) -> None:
        """force=True should always probe, even if cache is fresh."""
        mgr = make_manager(health_check_cache_ttl=10.0)

        mgr.health_check()
        call_count_after_first = mock_redis_module.Redis.return_value.ping.call_count

        mgr.health_check(force=True)
        assert (
            mock_redis_module.Redis.return_value.ping.call_count
            > call_count_after_first
        )

    def test_health_check_returns_disconnected_on_ping_failure(
        self, make_manager: object, mock_redis_module: MagicMock
    ) -> None:
        import redis

        mock_redis_module.Redis.return_value.ping.side_effect = redis.RedisError(
            "conn refused"
        )
        mgr = make_manager()
        result = mgr.health_check()
        assert result.state == ConnectionState.DISCONNECTED
        assert "conn refused" in result.detail

    def test_health_check_circuit_breaker_open_no_probe(
        self, make_manager: object, mock_redis_module: MagicMock
    ) -> None:
        """When circuit is OPEN, health check returns DISCONNECTED without I/O."""
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, name="redis"))
        mgr = make_manager(circuit_breaker=cb)

        # Trip circuit
        cb.record_failure(Exception("fail"))

        # Reset mock to verify no probe happens
        mock_redis_module.Redis.return_value.ping.reset_mock()

        result = mgr.health_check()
        assert result.state == ConnectionState.DISCONNECTED
        assert result.detail == "circuit_breaker_open"
        mock_redis_module.Redis.return_value.ping.assert_not_called()

    def test_health_check_pool_not_initialized(self, make_manager: object) -> None:
        mgr = make_manager()
        mgr._pool = None
        result = mgr.health_check(force=True)
        assert result.state == ConnectionState.DISCONNECTED
        assert result.detail == "pool_not_initialized"


# ---------------------------------------------------------------------------
# Close / lifecycle
# ---------------------------------------------------------------------------


class TestRedisManagerClose:
    """Verify close behavior and idempotency."""

    def test_close_disconnects_pool(self, make_manager: object) -> None:
        mgr = make_manager()
        pool = mgr._pool
        mgr.close()
        pool.disconnect.assert_called_once()
        assert mgr._pool is None
        assert mgr._closed is True

    def test_close_is_idempotent(self, make_manager: object) -> None:
        mgr = make_manager()
        pool = mgr._pool
        mgr.close()
        mgr.close()  # Second close should not raise
        pool.disconnect.assert_called_once()  # Only called once

    def test_close_async(self, make_manager: object) -> None:
        mgr = make_manager()
        asyncio.run(mgr.close_async())
        assert mgr._closed is True

    def test_context_manager_sync(self, make_manager: object) -> None:
        mgr = make_manager()
        with mgr as m:
            assert m is mgr
            assert m.state == ConnectionState.HEALTHY
        assert mgr._closed is True
        assert mgr.state == ConnectionState.DISCONNECTED

    def test_context_manager_async(self, make_manager: object) -> None:
        async def _test() -> None:
            mgr = make_manager()
            async with mgr as m:
                assert m is mgr
                assert m.state == ConnectionState.HEALTHY
            assert mgr._closed is True

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Health check async
# ---------------------------------------------------------------------------


class TestRedisHealthCheckAsync:
    """Verify async health check variant."""

    def test_health_check_async_returns_result(self, make_manager: object) -> None:
        mgr = make_manager()
        result = asyncio.run(mgr.health_check_async())
        assert result.state == ConnectionState.HEALTHY
