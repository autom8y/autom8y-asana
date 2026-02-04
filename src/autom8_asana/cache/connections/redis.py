"""Redis connection lifecycle manager.

Wraps redis-py ConnectionPool with explicit lifecycle management,
cached health checks, and circuit breaker integration.

Thread Safety:
    Pool creation and health checks are protected by a Lock.
    The underlying redis.ConnectionPool is itself thread-safe.

Module: src/autom8_asana/cache/connections/redis.py

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import time
from threading import Lock
from types import ModuleType
from typing import Any

from autom8y_log import get_logger

from autom8_asana.cache.backends.redis import RedisConfig
from autom8_asana.core.connections import ConnectionState, HealthCheckResult
from autom8_asana.core.exceptions import REDIS_TRANSPORT_ERRORS, CacheConnectionError
from autom8_asana.core.retry import CBState, CircuitBreaker

logger = get_logger(__name__)


class RedisConnectionManager:
    """Manages Redis connection pool lifecycle with circuit breaker integration.

    Owns the redis.ConnectionPool instance. Provides connections to
    RedisCacheProvider via get_connection(). Performs cached health checks
    that consult the circuit breaker before probing.

    Args:
        config: Redis connection configuration.
        circuit_breaker: Optional circuit breaker for health state gating.
        health_check_cache_ttl: Seconds before cached health result is stale.
            Default 10s (PING is cheap, sub-ms).

    Thread Safety:
        Pool creation and close are protected by a Lock.
        The underlying redis.ConnectionPool is itself thread-safe.
    """

    def __init__(
        self,
        config: RedisConfig,
        circuit_breaker: CircuitBreaker | None = None,
        *,
        health_check_cache_ttl: float = 10.0,
    ) -> None:
        self._config = config
        self._circuit_breaker = circuit_breaker
        self._health_cache_ttl = health_check_cache_ttl
        self._lock = Lock()
        self._pool: Any = None
        self._redis_module: ModuleType | None = None
        self._last_health: HealthCheckResult | None = None
        self._closed = False

        self._import_redis()
        self._create_pool()

    @property
    def name(self) -> str:
        """Unique identifier for this connection manager."""
        return "redis"

    @property
    def state(self) -> ConnectionState:
        """Current connection state derived from pool and circuit breaker state.

        Does not perform I/O. Checks closed flag, pool availability, and
        circuit breaker state to determine the connection state.
        """
        if self._closed:
            return ConnectionState.DISCONNECTED
        if self._pool is None or self._redis_module is None:
            return ConnectionState.DISCONNECTED
        if self._circuit_breaker and self._circuit_breaker.state == CBState.OPEN:
            return ConnectionState.DISCONNECTED
        if self._circuit_breaker and self._circuit_breaker.state == CBState.HALF_OPEN:
            return ConnectionState.DEGRADED
        if self._last_health and self._last_health.state == ConnectionState.DEGRADED:
            return ConnectionState.DEGRADED
        return ConnectionState.HEALTHY

    def get_connection(self) -> Any:
        """Get a Redis client from the managed pool.

        Returns:
            redis.Redis instance bound to the pool.

        Raises:
            CacheConnectionError: If manager is closed or pool unavailable.
        """
        if self._closed:
            raise CacheConnectionError("RedisConnectionManager is closed")
        if self._pool is None or self._redis_module is None:
            raise CacheConnectionError("Redis connection pool not initialized")
        return self._redis_module.Redis(connection_pool=self._pool)

    def health_check(self, *, force: bool = False) -> HealthCheckResult:
        """Perform a cached health check.

        If circuit breaker is OPEN, returns DISCONNECTED without probing.
        If cached result is fresh (within health_check_cache_ttl), returns it.
        Otherwise performs a PING and caches the result.

        Args:
            force: If True, bypass cache and perform a live probe.

        Returns:
            HealthCheckResult with current state and latency.
        """
        # Fast path: circuit breaker says no
        if self._circuit_breaker and not self._circuit_breaker.allow_request():
            result = HealthCheckResult(
                state=ConnectionState.DISCONNECTED,
                checked_at=time.monotonic(),
                detail="circuit_breaker_open",
            )
            self._last_health = result
            return result

        # Fast path: cached result is fresh
        if (
            not force
            and self._last_health is not None
            and not self._last_health.is_stale(self._health_cache_ttl)
        ):
            return self._last_health

        # Probe
        result = self._probe()
        self._last_health = result
        return result

    async def health_check_async(self, *, force: bool = False) -> HealthCheckResult:
        """Async variant of health_check -- runs sync probe in thread pool."""
        import asyncio

        return await asyncio.to_thread(self.health_check, force=force)

    def close(self) -> None:
        """Disconnect all pooled connections and mark manager as closed.

        Idempotent: calling close() multiple times is safe.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._pool is not None:
                self._pool.disconnect()
                self._pool = None
            logger.info("redis_connection_manager_closed")

    async def close_async(self) -> None:
        """Async variant -- delegates to sync close() via to_thread."""
        import asyncio

        await asyncio.to_thread(self.close)

    def __enter__(self) -> RedisConnectionManager:
        """Sync context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Sync context manager exit -- calls close()."""
        self.close()

    async def __aenter__(self) -> RedisConnectionManager:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit -- calls close_async()."""
        await self.close_async()

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _import_redis(self) -> None:
        """Import redis module. Handles ImportError gracefully."""
        try:
            import redis

            self._redis_module = redis
        except ImportError:
            logger.warning("redis_package_not_installed")

    def _create_pool(self) -> None:
        """Create the redis ConnectionPool from config."""
        if self._redis_module is None:
            return
        try:
            self._pool = self._redis_module.ConnectionPool(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password,
                socket_timeout=self._config.socket_timeout,
                socket_connect_timeout=self._config.socket_connect_timeout,
                max_connections=self._config.max_connections,
                retry_on_timeout=self._config.retry_on_timeout,
                decode_responses=self._config.decode_responses,
                ssl=self._config.ssl,
                ssl_cert_reqs=self._config.ssl_cert_reqs if self._config.ssl else None,
            )
        except REDIS_TRANSPORT_ERRORS as e:
            logger.error("redis_pool_creation_failed", extra={"error": str(e)})

    def _probe(self) -> HealthCheckResult:
        """Actually ping Redis and measure latency."""
        if self._pool is None or self._redis_module is None:
            return HealthCheckResult(
                state=ConnectionState.DISCONNECTED,
                checked_at=time.monotonic(),
                detail="pool_not_initialized",
            )

        start = time.monotonic()
        try:
            conn = self._redis_module.Redis(connection_pool=self._pool)
            try:
                conn.ping()
            finally:
                conn.close()
            latency_ms = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                state=ConnectionState.HEALTHY,
                checked_at=time.monotonic(),
                latency_ms=latency_ms,
            )
        except REDIS_TRANSPORT_ERRORS as e:
            latency_ms = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                state=ConnectionState.DISCONNECTED,
                checked_at=time.monotonic(),
                latency_ms=latency_ms,
                detail=str(e),
            )
