"""S3 connection lifecycle manager.

Wraps a shared boto3 S3 client with explicit lifecycle management,
cached health checks, and circuit breaker integration. Provides a
single boto3 client for S3CacheProvider and S3DataFrameStorage.

Thread Safety:
    Client creation is protected by a Lock. The boto3 S3 client
    is thread-safe for S3 operations.

Module: src/autom8_asana/cache/connections/s3.py

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from __future__ import annotations

import time
from threading import Lock
from types import ModuleType
from typing import Any

from autom8y_log import get_logger

from autom8_asana.cache.backends.s3 import S3Config
from autom8_asana.core.connections import ConnectionState, HealthCheckResult
from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS, CacheConnectionError
from autom8_asana.core.retry import CBState, CircuitBreaker

logger = get_logger(__name__)


class S3ConnectionManager:
    """Manages boto3 S3 client lifecycle with shared session.

    Provides both sync and async access to a single boto3 S3 client.
    The client is created lazily on first access and closed on shutdown.

    Configuration:
        Uses unified timeout config (10s connect, 30s read) and disables
        boto3 retries so RetryOrchestrator handles retries externally.

    Args:
        config: S3 cache configuration with bucket, region, and endpoint.
        circuit_breaker: Optional circuit breaker for health state gating.
        health_check_cache_ttl: Seconds before cached health result is stale.
            Default 30s (HeadBucket is an HTTP roundtrip, more expensive than PING).
        connect_timeout: boto3 connect timeout in seconds.
        read_timeout: boto3 read timeout in seconds.

    Thread Safety:
        Client creation is protected by a Lock. The boto3 S3 client
        is thread-safe for S3 operations.
    """

    def __init__(
        self,
        config: S3Config,
        circuit_breaker: CircuitBreaker | None = None,
        *,
        health_check_cache_ttl: float = 30.0,
        connect_timeout: int = 10,
        read_timeout: int = 30,
    ) -> None:
        self._config = config
        self._circuit_breaker = circuit_breaker
        self._health_cache_ttl = health_check_cache_ttl
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._lock = Lock()
        self._client: Any = None
        self._boto3_module: ModuleType | None = None
        self._last_health: HealthCheckResult | None = None
        self._closed = False

        self._import_boto3()

    @property
    def name(self) -> str:
        """Unique identifier for this connection manager."""
        return "s3"

    @property
    def state(self) -> ConnectionState:
        """Current connection state derived from client availability and circuit breaker.

        Does not perform I/O. Checks closed flag, boto3 availability,
        bucket configuration, and circuit breaker state.
        """
        if self._closed:
            return ConnectionState.DISCONNECTED
        if self._boto3_module is None or not self._config.bucket:
            return ConnectionState.DISCONNECTED
        if self._circuit_breaker and self._circuit_breaker.state == CBState.OPEN:
            return ConnectionState.DISCONNECTED
        if self._circuit_breaker and self._circuit_breaker.state == CBState.HALF_OPEN:
            return ConnectionState.DEGRADED
        return ConnectionState.HEALTHY

    def get_client(self) -> Any:
        """Get the boto3 S3 client, creating lazily if needed.

        Returns:
            boto3 S3 client instance.

        Raises:
            CacheConnectionError: If manager is closed or boto3 unavailable.
        """
        if self._closed:
            raise CacheConnectionError("S3ConnectionManager is closed")

        if self._client is not None:
            return self._client

        with self._lock:
            if self._client is not None:  # Double-check after lock
                return self._client
            self._create_client()
            if self._client is None:
                raise CacheConnectionError("Failed to create S3 client")
            return self._client

    def health_check(self, *, force: bool = False) -> HealthCheckResult:
        """Cached health check using HeadBucket.

        S3 health checks are more expensive (HTTP roundtrip) so the
        default cache TTL is longer (30s vs 10s for Redis).

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
        """Async health check -- runs sync probe in thread pool."""
        import asyncio

        return await asyncio.to_thread(self.health_check, force=force)

    def close(self) -> None:
        """Close the boto3 client and release resources.

        Idempotent: calling close() multiple times is safe.
        boto3 clients do not require explicit close, but we clear state
        to prevent further usage and allow GC of urllib3 pools.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._client = None
            logger.info("s3_connection_manager_closed")

    async def close_async(self) -> None:
        """Async variant -- delegates to sync close() via to_thread."""
        import asyncio

        await asyncio.to_thread(self.close)

    def __enter__(self) -> S3ConnectionManager:
        """Sync context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Sync context manager exit -- calls close()."""
        self.close()

    async def __aenter__(self) -> S3ConnectionManager:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit -- calls close_async()."""
        await self.close_async()

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _import_boto3(self) -> None:
        """Import boto3 module. Handles ImportError gracefully."""
        try:
            import boto3

            self._boto3_module = boto3
        except ImportError:
            logger.warning("boto3_package_not_installed")

    def _create_client(self) -> None:
        """Create boto3 S3 client with unified config. Must hold lock."""
        if self._boto3_module is None:
            return
        if not self._config.bucket:
            return

        try:
            from botocore.config import Config as BotoConfig

            boto_config = BotoConfig(
                connect_timeout=self._connect_timeout,
                read_timeout=self._read_timeout,
                retries={"max_attempts": 0},  # RetryOrchestrator handles retries
            )

            client_kwargs: dict[str, Any] = {
                "region_name": self._config.region,
                "config": boto_config,
            }
            if self._config.endpoint_url:
                client_kwargs["endpoint_url"] = self._config.endpoint_url

            self._client = self._boto3_module.client("s3", **client_kwargs)
        except S3_TRANSPORT_ERRORS as e:
            logger.error("s3_client_creation_failed", extra={"error": str(e)})

    def _probe(self) -> HealthCheckResult:
        """HeadBucket probe against configured bucket."""
        if self._boto3_module is None or not self._config.bucket:
            return HealthCheckResult(
                state=ConnectionState.DISCONNECTED,
                checked_at=time.monotonic(),
                detail="boto3_not_available" if not self._boto3_module else "no_bucket_configured",
            )

        start = time.monotonic()
        try:
            client = self.get_client()
            client.head_bucket(Bucket=self._config.bucket)
            latency_ms = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                state=ConnectionState.HEALTHY,
                checked_at=time.monotonic(),
                latency_ms=latency_ms,
            )
        except S3_TRANSPORT_ERRORS as e:
            latency_ms = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                state=ConnectionState.DISCONNECTED,
                checked_at=time.monotonic(),
                latency_ms=latency_ms,
                detail=str(e),
            )
        except CacheConnectionError:
            # Manager is closed or client creation failed
            return HealthCheckResult(
                state=ConnectionState.DISCONNECTED,
                checked_at=time.monotonic(),
                detail="client_unavailable",
            )
