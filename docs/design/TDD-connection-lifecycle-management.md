# TDD: Connection Lifecycle Management

**TDD ID**: TDD-CONNECTION-LIFECYCLE-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**Sprint**: S4 (Architectural Opportunities -- Wave 4)
**Task**: S4-004
**PRD Reference**: Architectural Opportunities Initiative
**Depends On**: C1 (Exception Hierarchy -- implemented), C3 (Retry Orchestrator -- implemented)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Goals and Non-Goals](#3-goals-and-non-goals)
4. [Proposed Architecture](#4-proposed-architecture)
5. [Component Design: ConnectionManager Protocol](#5-component-design-connectionmanager-protocol)
6. [Component Design: RedisConnectionManager](#6-component-design-redisconnectionmanager)
7. [Component Design: S3ConnectionManager](#7-component-design-s3connectionmanager)
8. [Component Design: ConnectionRegistry](#8-component-design-connectionregistry)
9. [Health Check Integration with Circuit Breakers](#9-health-check-integration-with-circuit-breakers)
10. [Shutdown Ordering](#10-shutdown-ordering)
11. [Integration Points](#11-integration-points)
12. [Configuration](#12-configuration)
13. [Data Flow Diagrams](#13-data-flow-diagrams)
14. [Migration Plan](#14-migration-plan)
15. [Module Placement](#15-module-placement)
16. [Interface Contracts](#16-interface-contracts)
17. [Test Strategy](#17-test-strategy)
18. [Risk Assessment](#18-risk-assessment)
19. [ADRs](#19-adrs)
20. [Success Criteria](#20-success-criteria)

---

## 1. Overview

### 1.1 Problem Statement

Connection lifecycle for Redis and S3 backends is managed ad-hoc with three independent patterns, no coordinated shutdown, and no unified health reporting.

**Redis** (`cache/backends/redis.py`):
- Creates a `redis.ConnectionPool` eagerly in `__init__` via `_initialize_pool()` (line 147).
- Gets connections via `self._redis_module.Redis(connection_pool=self._pool)` on every operation.
- Each operation manually calls `conn.close()` in a `finally` block (e.g., lines 373, 404).
- Health check (`is_healthy()`, line 743) creates a new connection, pings, closes it -- every call.
- Reconnection is managed by `DegradedModeMixin.should_attempt_reconnect()` with a time-gated attempt.
- No `close()` method exists. The connection pool is never explicitly shut down.

**S3 Cache Backend** (`cache/backends/s3.py`):
- Creates a single `boto3.client("s3")` lazily under `threading.Lock` via `_initialize_client()` (line 173).
- The client is reused across all operations (`_get_client()` returns `self._client`).
- Health check (`is_healthy()`, line 792) calls `head_bucket()` on every invocation.
- No `close()` method. The boto3 client is never explicitly shut down.

**AsyncS3Client** (`dataframes/async_s3.py`):
- Creates a `boto3.client("s3")` lazily via `_ensure_initialized()` (line 214) in a thread.
- Has an async context manager (`__aenter__`/`__aexit__`) and a `close()` method (line 275).
- Implements its own retry logic separate from `RetryOrchestrator` (per-operation retry loop).
- Degraded mode uses `self._last_error_time` with a hardcoded 60-second reconnect interval.
- Health check via `head_bucket_async()` but no formal `is_healthy()` method.

**What is wrong:**

| Issue | Impact |
|-------|--------|
| No coordinated shutdown | Redis pool leaks connections on app stop; boto3 sessions are not drained |
| Health checks are ad-hoc | `is_healthy()` creates new connections and performs I/O on every call. No caching, no integration with circuit breakers |
| DegradedModeMixin duplicated | Three backends each implement degraded mode with slightly different semantics (60s vs configurable reconnect interval, `time.time()` vs `time.monotonic()`) |
| No connection state reporting | The API `/health` endpoint has no way to report per-backend connection status (healthy/degraded/disconnected) |
| Circuit breakers not connected to health | `RetryOrchestrator` circuit breakers (C3) exist but health checks do not consult them. A circuit-open backend still receives health-check probes |
| Two S3 client lifecycles diverge | `S3CacheProvider._client` and `AsyncS3Client._client` are independent boto3 clients with different config, different timeout settings, and no shared session |

### 1.2 Solution Summary

A `ConnectionManager` protocol with Redis and S3 implementations that:
1. Own their backend's connection lifecycle (create, health-check, close).
2. Integrate with existing `CircuitBreaker` instances for health state.
3. Register with a `ConnectionRegistry` for coordinated shutdown.
4. Report connection state as an enum (`HEALTHY`, `DEGRADED`, `DISCONNECTED`).
5. Cache health check results with configurable staleness to avoid per-call I/O.

### 1.3 Key Design Principle

**Wrap, do not replace.** The `ConnectionManager` wraps existing connection patterns (redis-py `ConnectionPool`, boto3 client) rather than reimplementing them. Existing backend code (`RedisCacheProvider`, `S3CacheProvider`, `AsyncS3Client`) retains its internal structure. The manager is injected as a dependency, and backends call `manager.get_connection()` instead of managing their own pool/client.

---

## 2. Problem Statement

### 2.1 The Shutdown Gap

Currently, when the FastAPI application shuts down (`lifespan` context manager exits):

```
api/main.py lifespan():
    yield  # <-- app is serving requests

    # Shutdown begins
    # Cancel cache warming task
    if hasattr(app.state, "cache_warming_task"):
        task.cancel()

    logger.info("api_stopping")
    # <-- function returns, Python GC collects everything
```

No cache backends are explicitly closed. Redis connections in the pool remain open until the process exits. boto3 clients hold HTTP connections in urllib3 connection pools that are never drained. During rolling deployments, this creates a window where old connections linger on the server side.

### 2.2 Health Check Overhead

Every call to `RedisCacheProvider.is_healthy()` (line 743):
1. Gets a connection from the pool
2. Sends `PING`
3. Closes the connection

Every call to `S3CacheProvider.is_healthy()` (line 792):
1. Gets the boto3 client
2. Sends `HeadBucket` (an HTTP roundtrip to S3)
3. Returns True/False

For the `/health` API endpoint, this means two I/O roundtrips on every probe. With Kubernetes/ECS health checks running every 10-30 seconds, this is tolerable. But during degraded mode, `_attempt_reconnect()` compounds with health checks, creating redundant probes.

### 2.3 Divergent S3 Patterns

Two independent boto3 clients exist:

| Property | `S3CacheProvider._client` | `AsyncS3Client._client` |
|----------|--------------------------|------------------------|
| Created by | `boto3.client("s3")` in `_initialize_client()` | `boto3.client("s3")` in `_ensure_initialized()` via `asyncio.to_thread` |
| Config source | `S3Config` dataclass | `AsyncS3Config` dataclass |
| Timeouts | boto3 defaults (60s connect, 60s read) | Custom `botocore.config.Config(connect_timeout=10, read_timeout=30)` |
| Retries | boto3 default (standard mode, 3 attempts) | Disabled (`retries={"max_attempts": 0}`), custom retry loop |
| Thread safety | Single client, Lock on creation | Single client, assumed thread-safe |
| Close | None | `close()` sets `self._client = None` |

These two clients should share a boto3 `Session` for connection pooling and consistent configuration.

---

## 3. Goals and Non-Goals

### 3.1 Goals

1. **G1**: Define a `ConnectionManager` protocol that all connection-backed resources implement.
2. **G2**: Implement `RedisConnectionManager` wrapping redis-py `ConnectionPool` with explicit lifecycle.
3. **G3**: Implement `S3ConnectionManager` wrapping a shared boto3 session/client with explicit lifecycle.
4. **G4**: Integrate health checks with `CircuitBreaker` state -- do not probe a circuit-open backend.
5. **G5**: Add cached health check results to avoid redundant I/O on rapid health probes.
6. **G6**: Implement graceful shutdown via `ConnectionRegistry` with ordered close.
7. **G7**: Report per-backend connection state (`HEALTHY`/`DEGRADED`/`DISCONNECTED`) for observability.
8. **G8**: Wire shutdown into FastAPI `lifespan` context manager.

### 3.2 Non-Goals

- **NG1**: Replacing `autom8y_http` transport retry for the Asana API client. HTTP connection management is handled by the platform SDK.
- **NG2**: Connection pooling for boto3. boto3 uses urllib3 internally with its own connection pooling. We manage client lifecycle, not individual HTTP connections.
- **NG3**: Changing `RedisCacheProvider` or `S3CacheProvider` internal data structures. They continue to store entries, serialize/deserialize, and manage keys as before.
- **NG4**: Automatic reconnection beyond what already exists in `DegradedModeMixin`. The managers formalize the existing pattern, not invent a new one.

### 3.3 Constraints

- Must not break existing `RedisCacheProvider`, `S3CacheProvider`, or `AsyncS3Client` behavior.
- Must be adoptable incrementally -- backends can opt in to the manager one at a time.
- Python 3.11+ (per `pyproject.toml`).
- `ConnectionManager` must support both sync and async callers (Redis is sync, AsyncS3Client is async).

---

## 4. Proposed Architecture

### 4.1 Component Diagram

```
                     ┌──────────────────────────┐
                     │    ConnectionRegistry     │
                     │  (ordered shutdown, state │
                     │   aggregation)            │
                     └────────┬────────┬─────────┘
                              │        │
               ┌──────────────┘        └──────────────┐
               │                                      │
    ┌──────────▼───────────┐             ┌────────────▼──────────┐
    │ RedisConnectionManager│             │  S3ConnectionManager  │
    │                       │             │                       │
    │ - ConnectionPool      │             │ - boto3 Session       │
    │ - CircuitBreaker ref  │             │ - sync client         │
    │ - cached health state │             │ - async client        │
    │ - close()             │             │ - CircuitBreaker ref  │
    └──────────┬────────────┘             │ - cached health state │
               │                          │ - close()             │
    ┌──────────▼───────────┐              └───────────┬───────────┘
    │  RedisCacheProvider   │                         │
    │  (uses manager for    │              ┌──────────┴────────────┐
    │   connections)        │              │                       │
    └──────────────────────┘    ┌─────────▼────────┐  ┌───────────▼────────┐
                                │ S3CacheProvider  │  │  AsyncS3Client     │
                                │ (uses manager    │  │  (uses manager     │
                                │  for client)     │  │   for client)      │
                                └──────────────────┘  └────────────────────┘
```

### 4.2 Relationship to Existing Infrastructure

| Existing Component | New Relationship |
|-------------------|-----------------|
| `RetryOrchestrator` (core/retry.py) | ConnectionManagers hold a reference to the subsystem's CircuitBreaker; health checks consult `circuit_breaker.state` |
| `DegradedModeMixin` (cache/models/errors.py) | ConnectionManagers implement degraded-mode logic natively; backends delegate to manager instead of mixing in |
| `CacheSettings.reconnect_interval` | ConnectionManager uses this value for health check cache TTL and reconnect gating |
| FastAPI `lifespan` | Shutdown phase calls `ConnectionRegistry.close_all()` before logging "api_stopping" |

---

## 5. Component Design: ConnectionManager Protocol

### 5.1 Connection State Enum

```python
"""Connection lifecycle management for cache backends.

Module: src/autom8_asana/core/connections.py
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class ConnectionState(enum.Enum):
    """Connection health states reported by ConnectionManagers."""

    HEALTHY = "healthy"           # Backend is responsive
    DEGRADED = "degraded"         # Backend is partially available or recovering
    DISCONNECTED = "disconnected" # Backend is unavailable
```

### 5.2 HealthCheckResult

```python
@dataclass(frozen=True)
class HealthCheckResult:
    """Cached result of a health check probe.

    Attributes:
        state: Current connection state.
        checked_at: Monotonic timestamp when check was performed.
        latency_ms: Probe latency in milliseconds (0.0 if not measured).
        detail: Optional human-readable detail string.
    """

    state: ConnectionState
    checked_at: float            # time.monotonic()
    latency_ms: float = 0.0
    detail: str = ""

    def is_stale(self, max_age_seconds: float) -> bool:
        """Check if this result is older than max_age_seconds."""
        return (time.monotonic() - self.checked_at) > max_age_seconds
```

### 5.3 ConnectionManager Protocol

```python
@runtime_checkable
class ConnectionManager(Protocol):
    """Protocol for backend connection lifecycle management.

    Implementations own the creation, health monitoring, and shutdown
    of connections to a specific backend (Redis, S3, etc.).

    ConnectionManagers are long-lived objects (application singleton scope).
    They are created during app startup and closed during shutdown.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this connection manager (e.g., 'redis', 's3')."""
        ...

    @property
    def state(self) -> ConnectionState:
        """Current connection state. Uses cached health check if available."""
        ...

    def health_check(self, *, force: bool = False) -> HealthCheckResult:
        """Perform a health check, returning a cached result if fresh.

        Args:
            force: If True, bypass cache and perform a live probe.

        Returns:
            HealthCheckResult with current state and latency.
        """
        ...

    async def health_check_async(self, *, force: bool = False) -> HealthCheckResult:
        """Async variant of health_check for async callers.

        Args:
            force: If True, bypass cache and perform a live probe.

        Returns:
            HealthCheckResult with current state and latency.
        """
        ...

    def close(self) -> None:
        """Release all resources held by this manager.

        After close(), the manager is in DISCONNECTED state.
        Calling close() multiple times is safe (idempotent).
        """
        ...

    async def close_async(self) -> None:
        """Async variant of close for async callers."""
        ...

    def __enter__(self) -> ConnectionManager:
        """Sync context manager entry."""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Sync context manager exit -- calls close()."""
        ...

    async def __aenter__(self) -> ConnectionManager:
        """Async context manager entry."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit -- calls close_async()."""
        ...
```

### 5.4 Design Decision: Sync + Async Dual Interface

The protocol requires both sync and async variants of `health_check` and `close`. This is necessary because:
- `RedisCacheProvider` is entirely synchronous (redis-py is sync).
- `AsyncS3Client` is entirely asynchronous.
- `S3CacheProvider` is synchronous.
- The FastAPI shutdown is async (`lifespan` is an async context manager).

The sync `health_check()` performs I/O directly. The async `health_check_async()` wraps it via `asyncio.to_thread()` for Redis, and calls boto3 via `asyncio.to_thread()` for S3. This matches the existing pattern in `AsyncS3Client`.

---

## 6. Component Design: RedisConnectionManager

### 6.1 Class Definition

```python
"""Redis connection lifecycle manager.

Module: src/autom8_asana/core/connections.py (or cache/connections/redis.py)
"""

from threading import Lock


class RedisConnectionManager:
    """Manages Redis connection pool lifecycle with circuit breaker integration.

    Owns the redis.ConnectionPool instance. Provides connections to
    RedisCacheProvider via get_connection(). Performs cached health checks
    that consult the circuit breaker before probing.

    Thread Safety:
        Pool creation and health checks are protected by a Lock.
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
        return "redis"

    @property
    def state(self) -> ConnectionState:
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
        if not force and self._last_health and not self._last_health.is_stale(self._health_cache_ttl):
            return self._last_health

        # Probe
        result = self._probe()
        self._last_health = result
        return result

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

    def close(self) -> None:
        """Disconnect all pooled connections and mark manager as closed."""
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

    # Context managers delegate to close()
    def __enter__(self) -> RedisConnectionManager: return self
    def __exit__(self, *args: Any) -> None: self.close()
    async def __aenter__(self) -> RedisConnectionManager: return self
    async def __aexit__(self, *args: Any) -> None: await self.close_async()

    # Private helpers
    def _import_redis(self) -> None:
        try:
            import redis
            self._redis_module = redis
        except ImportError:
            logger.warning("redis_package_not_installed")

    def _create_pool(self) -> None:
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
```

### 6.2 Integration with RedisCacheProvider

`RedisCacheProvider` receives a `RedisConnectionManager` as an optional constructor argument. When provided, it delegates connection management:

```python
class RedisCacheProvider(DegradedModeMixin):
    def __init__(
        self,
        config: RedisConfig | None = None,
        settings: CacheSettings | None = None,
        *,
        connection_manager: RedisConnectionManager | None = None,
        # ... existing kwargs
    ) -> None:
        # ... existing init code ...
        self._connection_manager = connection_manager

    def _get_connection(self) -> Any:
        # New path: delegate to manager
        if self._connection_manager is not None:
            return self._connection_manager.get_connection()

        # Legacy path: existing self._pool logic
        # ... (unchanged) ...

    def is_healthy(self) -> bool:
        if self._connection_manager is not None:
            result = self._connection_manager.health_check()
            return result.state == ConnectionState.HEALTHY

        # Legacy path
        # ... (unchanged) ...
```

This is backward compatible: existing code that creates `RedisCacheProvider()` without a manager works exactly as before. New code that provides a manager gets lifecycle management.

---

## 7. Component Design: S3ConnectionManager

### 7.1 Shared boto3 Session

The key change for S3 is that both `S3CacheProvider` and `AsyncS3Client` share a single boto3 `Session` and client, eliminating the divergent timeout/retry configuration.

```python
class S3ConnectionManager:
    """Manages boto3 S3 client lifecycle with shared session.

    Provides both sync and async access to a single boto3 S3 client.
    The client is created lazily on first access and closed on shutdown.

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
        self._botocore_module: ModuleType | None = None
        self._last_health: HealthCheckResult | None = None
        self._closed = False

        self._import_boto3()

    @property
    def name(self) -> str:
        return "s3"

    @property
    def state(self) -> ConnectionState:
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
            boto3 S3 client.

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
        """
        if self._circuit_breaker and not self._circuit_breaker.allow_request():
            result = HealthCheckResult(
                state=ConnectionState.DISCONNECTED,
                checked_at=time.monotonic(),
                detail="circuit_breaker_open",
            )
            self._last_health = result
            return result

        if not force and self._last_health and not self._last_health.is_stale(self._health_cache_ttl):
            return self._last_health

        result = self._probe()
        self._last_health = result
        return result

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

    def close(self) -> None:
        """Close the boto3 client and release resources."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            # boto3 clients do not require explicit close, but we clear state
            # to prevent further usage and allow GC of urllib3 pools
            self._client = None
            logger.info("s3_connection_manager_closed")

    async def close_async(self) -> None:
        import asyncio
        await asyncio.to_thread(self.close)

    async def health_check_async(self, *, force: bool = False) -> HealthCheckResult:
        """Async health check -- runs sync probe in thread pool."""
        import asyncio
        return await asyncio.to_thread(self.health_check, force=force)

    # Context managers
    def __enter__(self) -> S3ConnectionManager: return self
    def __exit__(self, *args: Any) -> None: self.close()
    async def __aenter__(self) -> S3ConnectionManager: return self
    async def __aexit__(self, *args: Any) -> None: await self.close_async()

    # Private helpers
    def _import_boto3(self) -> None:
        try:
            import boto3
            import botocore.exceptions
            self._boto3_module = boto3
            self._botocore_module = botocore.exceptions
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
```

### 7.2 Integration with S3CacheProvider and AsyncS3Client

Both `S3CacheProvider` and `AsyncS3Client` receive an optional `S3ConnectionManager`:

```python
class S3CacheProvider(DegradedModeMixin):
    def __init__(
        self,
        config: S3Config | None = None,
        settings: CacheSettings | None = None,
        *,
        connection_manager: S3ConnectionManager | None = None,
        # ... existing kwargs
    ) -> None:
        self._connection_manager = connection_manager
        # ... existing init ...

    def _get_client(self) -> Any:
        if self._connection_manager is not None:
            return self._connection_manager.get_client()
        # Legacy path unchanged
        # ...
```

```python
class AsyncS3Client(DegradedModeMixin):
    def __init__(
        self,
        config: AsyncS3Config | None = None,
        *,
        connection_manager: S3ConnectionManager | None = None,
        # ... existing kwargs
    ) -> None:
        self._connection_manager = connection_manager
        # ... existing init ...

    def _get_client(self) -> S3Client:
        if self._connection_manager is not None:
            return self._connection_manager.get_client()
        # Legacy path unchanged
        # ...
```

---

## 8. Component Design: ConnectionRegistry

### 8.1 Purpose

The `ConnectionRegistry` holds references to all `ConnectionManager` instances and provides:
1. Coordinated shutdown (`close_all()`).
2. Aggregated health reporting.
3. Named lookup for diagnostics.

### 8.2 Class Definition

```python
class ConnectionRegistry:
    """Registry for coordinated connection lifecycle management.

    Managers are registered during app startup and closed in reverse
    order during shutdown (LIFO -- last registered, first closed).
    This ensures dependent services shut down before their dependencies.

    Thread Safety:
        Registration and close are protected by a Lock.
    """

    def __init__(self) -> None:
        self._managers: list[ConnectionManager] = []
        self._lock = Lock()

    def register(self, manager: ConnectionManager) -> None:
        """Register a connection manager for lifecycle coordination.

        Args:
            manager: ConnectionManager to register.
        """
        with self._lock:
            self._managers.append(manager)
            logger.info(
                "connection_manager_registered",
                extra={"name": manager.name},
            )

    def get(self, name: str) -> ConnectionManager | None:
        """Look up a manager by name.

        Args:
            name: Manager identifier (e.g., 'redis', 's3').

        Returns:
            ConnectionManager or None if not found.
        """
        for mgr in self._managers:
            if mgr.name == name:
                return mgr
        return None

    def health_report(self) -> dict[str, HealthCheckResult]:
        """Aggregate health check results from all registered managers.

        Returns:
            Dict mapping manager name to HealthCheckResult.
        """
        return {mgr.name: mgr.health_check() for mgr in self._managers}

    async def health_report_async(self) -> dict[str, HealthCheckResult]:
        """Async health report -- runs checks in parallel."""
        import asyncio
        results = await asyncio.gather(
            *[mgr.health_check_async() for mgr in self._managers],
            return_exceptions=True,
        )
        report: dict[str, HealthCheckResult] = {}
        for mgr, result in zip(self._managers, results):
            if isinstance(result, Exception):
                report[mgr.name] = HealthCheckResult(
                    state=ConnectionState.DISCONNECTED,
                    checked_at=time.monotonic(),
                    detail=str(result),
                )
            else:
                report[mgr.name] = result
        return report

    def close_all(self) -> None:
        """Close all managers in reverse registration order (LIFO).

        Errors during individual manager close are logged and swallowed
        to ensure all managers get a chance to close.
        """
        with self._lock:
            for mgr in reversed(self._managers):
                try:
                    mgr.close()
                except Exception as e:
                    logger.warning(
                        "connection_manager_close_failed",
                        extra={"name": mgr.name, "error": str(e)},
                    )
            self._managers.clear()

    async def close_all_async(self) -> None:
        """Async close -- closes managers sequentially in LIFO order.

        Sequential (not parallel) because shutdown ordering matters
        and we want deterministic cleanup.
        """
        with self._lock:
            for mgr in reversed(self._managers):
                try:
                    await mgr.close_async()
                except Exception as e:
                    logger.warning(
                        "connection_manager_close_failed",
                        extra={"name": mgr.name, "error": str(e)},
                    )
            self._managers.clear()

    @property
    def all_healthy(self) -> bool:
        """True if all registered managers report HEALTHY state."""
        return all(mgr.state == ConnectionState.HEALTHY for mgr in self._managers)
```

### 8.3 Shutdown Ordering Rationale

Managers close in **reverse registration order** (LIFO). The expected registration order during startup is:

1. `S3ConnectionManager` (registered first -- cold tier, no dependencies)
2. `RedisConnectionManager` (registered second -- hot tier, may have read-through from S3)

On shutdown:
1. `RedisConnectionManager` closes first (stops accepting cache reads/writes)
2. `S3ConnectionManager` closes second (any pending S3 operations from before Redis close can complete)

This matches the principle that consumers close before providers.

---

## 9. Health Check Integration with Circuit Breakers

### 9.1 Decision: Circuit Breaker State Gates Health Probes

When a circuit breaker is OPEN, the connection manager returns `DISCONNECTED` immediately without performing I/O. This prevents health checks from creating load on an already-failing backend.

When a circuit breaker transitions to HALF_OPEN, the connection manager reports `DEGRADED` and allows a health probe through. If the probe succeeds, the circuit breaker receives `record_success()` and may transition to CLOSED.

```
Circuit CLOSED  --> health_check() probes, returns HEALTHY/DISCONNECTED
Circuit OPEN    --> health_check() returns DISCONNECTED immediately (no I/O)
Circuit HALF_OPEN -> health_check() probes (acts as circuit breaker test probe)
```

### 9.2 Health Check Caching Strategy

| Backend | Default Cache TTL | Rationale |
|---------|-------------------|-----------|
| Redis | 10 seconds | PING is cheap (sub-ms). 10s prevents rapid-fire probes while keeping state fresh. |
| S3 | 30 seconds | HeadBucket is an HTTP roundtrip (~50-200ms). 30s aligns with typical health check intervals. |

The TTL is configurable via `health_check_cache_ttl` constructor parameter.

### 9.3 Sequence Diagram: Health Check Flow

```
/health endpoint        ConnectionRegistry      RedisConnectionMgr      CircuitBreaker
    |                        |                        |                      |
    |-- health_report() ---->|                        |                      |
    |                        |-- health_check() ----->|                      |
    |                        |                        |-- allow_request() -->|
    |                        |                        |<-- True (CLOSED) ----|
    |                        |                        |                      |
    |                        |                        | [check cache freshness]
    |                        |                        | [cache is stale]
    |                        |                        |                      |
    |                        |                        |-- PING Redis ------->|
    |                        |                        |<-- PONG (2ms) -------|
    |                        |                        |                      |
    |                        |                        | [cache result]
    |                        |<-- HEALTHY (2ms) ------|                      |
    |                        |                        |                      |
    |<-- {"redis": HEALTHY,  |                        |                      |
    |     "s3": HEALTHY}     |                        |                      |
```

---

## 10. Shutdown Ordering

### 10.1 FastAPI Lifespan Integration

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    configure_structlog()

    # Create connection managers
    registry = ConnectionRegistry()
    s3_manager = S3ConnectionManager(config=s3_config, circuit_breaker=s3_cb)
    redis_manager = RedisConnectionManager(config=redis_config, circuit_breaker=redis_cb)
    registry.register(s3_manager)
    registry.register(redis_manager)
    app.state.connection_registry = registry

    # ... existing startup (entity discovery, cache warming, etc.) ...

    yield

    # Shutdown -- BEFORE existing cleanup
    # 1. Cancel background tasks
    if hasattr(app.state, "cache_warming_task"):
        task = app.state.cache_warming_task
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    # 2. Close connections (ordered)
    if hasattr(app.state, "connection_registry"):
        await app.state.connection_registry.close_all_async()

    logger.info("api_stopping")
```

### 10.2 Shutdown Sequence

```
1. SIGTERM received by uvicorn
2. FastAPI lifespan __aexit__ begins
3. Cancel cache_warming_task (if running)
4. ConnectionRegistry.close_all_async():
   a. RedisConnectionManager.close_async()
      - pool.disconnect() releases all pooled connections
   b. S3ConnectionManager.close_async()
      - client = None allows GC of urllib3 connection pool
5. Log "api_stopping"
6. Process exits
```

---

## 11. Integration Points

### 11.1 Where Managers Plug In

| Consumer | Current Pattern | With Manager |
|----------|----------------|-------------|
| `RedisCacheProvider._get_connection()` | Creates `Redis(connection_pool=self._pool)` | Calls `self._connection_manager.get_connection()` |
| `RedisCacheProvider.is_healthy()` | Ping via new connection | Calls `self._connection_manager.health_check().state == HEALTHY` |
| `RedisCacheProvider._initialize_pool()` | Creates `ConnectionPool` directly | Delegated to manager constructor |
| `S3CacheProvider._get_client()` | Returns `self._client` | Calls `self._connection_manager.get_client()` |
| `S3CacheProvider.is_healthy()` | `head_bucket()` | Calls `self._connection_manager.health_check().state == HEALTHY` |
| `AsyncS3Client._get_client()` | Returns `self._client` | Calls `self._connection_manager.get_client()` |
| `AsyncS3Client.close()` | Sets `self._client = None` | Delegates to manager (but manager may outlive any single AsyncS3Client) |

### 11.2 DegradedModeMixin Relationship

With connection managers, the degraded mode state machine moves from the cache provider to the manager. However, for backward compatibility during migration, `DegradedModeMixin` remains on the providers. The providers check manager state when available:

```python
# In RedisCacheProvider
@property
def _degraded(self) -> bool:
    if self._connection_manager is not None:
        return self._connection_manager.state != ConnectionState.HEALTHY
    return self.__degraded  # fallback to mixin attribute
```

This is a Phase 2 concern. Phase 1 keeps `DegradedModeMixin` behavior unchanged and adds manager as an optional dependency.

---

## 12. Configuration

### 12.1 Configuration Sources

No new configuration classes are needed. Managers reuse existing configs:

| Manager | Config Class | Source |
|---------|-------------|--------|
| `RedisConnectionManager` | `RedisConfig` | `cache/backends/redis.py` (existing) |
| `S3ConnectionManager` | `S3Config` | `cache/backends/s3.py` (existing) |

### 12.2 New Parameters

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `health_check_cache_ttl` | Manager constructor | 10s (Redis), 30s (S3) | Time before cached health result is considered stale |
| `connect_timeout` | `S3ConnectionManager` | 10 | boto3 connect timeout in seconds |
| `read_timeout` | `S3ConnectionManager` | 30 | boto3 read timeout in seconds |

These are constructor-time values, not Pydantic Settings fields. They can be surfaced to environment variables in a later sprint if needed.

---

## 13. Data Flow Diagrams

### 13.1 Connection Lifecycle: Startup to Shutdown

```
App Startup                              App Running                          App Shutdown
───────────                              ──────────                          ────────────

S3ConnectionManager()                    S3CacheProvider.get()               SIGTERM
  |-- import boto3                         |-- manager.get_client()
  |-- (defer client creation)              |   |-- lazy create boto3 client  Registry.close_all_async()
  |                                        |   |-- return client               |
RedisConnectionManager()                   |                                   |-- Redis.close_async()
  |-- import redis                       AsyncS3Client.put_object_async()      |   |-- pool.disconnect()
  |-- create ConnectionPool                |-- manager.get_client()            |
  |                                        |-- asyncio.to_thread(put)          |-- S3.close_async()
Registry.register(s3_mgr)                                                      |   |-- client = None
Registry.register(redis_mgr)             /health                              |
                                           |-- registry.health_report()        logger.info("stopped")
                                           |   |-- redis.health_check()
                                           |   |-- s3.health_check()
```

### 13.2 Health Check Decision Tree

```
health_check(force=False)
    |
    v
circuit_breaker.allow_request()?
    |
    +-- False (OPEN) --> return DISCONNECTED (no I/O)
    |
    +-- True (CLOSED or HALF_OPEN)
        |
        v
    cached result fresh? (within TTL)
        |
        +-- Yes and not force --> return cached result
        |
        +-- No or force
            |
            v
        probe backend (PING / HeadBucket)
            |
            +-- success --> cache HEALTHY, return
            |
            +-- failure --> cache DISCONNECTED, return
```

---

## 14. Migration Plan

### 14.1 Phase 1: Add Managers as Optional Dependencies (This Sprint)

1. Create `src/autom8_asana/core/connections.py` with `ConnectionState`, `HealthCheckResult`, `ConnectionManager` protocol.
2. Create `src/autom8_asana/cache/connections/redis.py` with `RedisConnectionManager`.
3. Create `src/autom8_asana/cache/connections/s3.py` with `S3ConnectionManager`.
4. Create `src/autom8_asana/cache/connections/registry.py` with `ConnectionRegistry`.
5. Add `connection_manager` parameter to `RedisCacheProvider.__init__()`, `S3CacheProvider.__init__()`, `AsyncS3Client.__init__()`.
6. When `connection_manager is not None`, delegate `_get_connection()` / `_get_client()` to it.
7. Wire `ConnectionRegistry` into FastAPI `lifespan` shutdown.

All changes are backward compatible. Existing code that does not pass a `connection_manager` works exactly as before.

### 14.2 Phase 2: Migrate DegradedModeMixin to Managers (Future Sprint)

1. Connection managers own the degraded/reconnect state machine.
2. Providers query `manager.state` instead of maintaining `self._degraded`.
3. Remove `DegradedModeMixin` from providers that use managers.
4. Remove duplicate `_initialize_pool()` / `_initialize_client()` / `_attempt_reconnect()` from providers.

### 14.3 Phase 3: Unify S3 Clients (Future Sprint)

1. Both `S3CacheProvider` and `AsyncS3Client` use the same `S3ConnectionManager`.
2. Remove `AsyncS3Config` -- use `S3Config` with the manager's timeout settings.
3. Remove `AsyncS3Client._ensure_initialized()` -- manager handles this.

---

## 15. Module Placement

### 15.1 New Files

| File | Contents |
|------|----------|
| `src/autom8_asana/core/connections.py` | `ConnectionState`, `HealthCheckResult`, `ConnectionManager` protocol |
| `src/autom8_asana/cache/connections/__init__.py` | Package init, re-exports |
| `src/autom8_asana/cache/connections/redis.py` | `RedisConnectionManager` |
| `src/autom8_asana/cache/connections/s3.py` | `S3ConnectionManager` |
| `src/autom8_asana/cache/connections/registry.py` | `ConnectionRegistry` |

### 15.2 Modified Files

| File | Change |
|------|--------|
| `src/autom8_asana/cache/backends/redis.py` | Add `connection_manager` param, delegate when present |
| `src/autom8_asana/cache/backends/s3.py` | Add `connection_manager` param, delegate when present |
| `src/autom8_asana/dataframes/async_s3.py` | Add `connection_manager` param, delegate when present |
| `src/autom8_asana/api/main.py` | Create managers and registry in `lifespan`, close on shutdown |

### 15.3 Rationale: Protocol in `core/`, Implementations in `cache/connections/`

The `ConnectionManager` protocol lives in `core/connections.py` because it is a cross-cutting contract that could be implemented by non-cache backends in the future (e.g., an HTTP connection pool manager). The concrete implementations live in `cache/connections/` because they are specific to cache backends and import cache-specific types (`RedisConfig`, `S3Config`).

---

## 16. Interface Contracts

### 16.1 ConnectionManager Protocol Compliance

Any class implementing `ConnectionManager` must:
1. Return a stable `name` string unique within a registry.
2. Return `ConnectionState` from `state` without performing I/O.
3. Return `HealthCheckResult` from `health_check()` with I/O only when cache is stale.
4. Be safe to call `close()` multiple times (idempotent).
5. After `close()`, `state` must return `DISCONNECTED`.
6. After `close()`, `get_connection()`/`get_client()` must raise `CacheConnectionError`.

### 16.2 ConnectionRegistry Contracts

1. `register()` is append-only during startup. Do not register during request handling.
2. `close_all()` / `close_all_async()` clears the registry. After close, the registry is empty.
3. `health_report()` returns results for all registered managers, never raises.

---

## 17. Test Strategy

### 17.1 Unit Tests

| Test Module | Tests |
|-------------|-------|
| `tests/unit/core/test_connections.py` | `HealthCheckResult.is_stale()` with fixed timestamps, `ConnectionState` enum values |
| `tests/unit/cache/connections/test_redis_manager.py` | Pool creation, `get_connection()` returns client, `close()` disconnects pool, `health_check()` caching, circuit breaker gating, double-close idempotency, `CacheConnectionError` after close |
| `tests/unit/cache/connections/test_s3_manager.py` | Lazy client creation, `get_client()` double-check locking, `close()` nulls client, `health_check()` caching, circuit breaker gating, idempotent close |
| `tests/unit/cache/connections/test_registry.py` | LIFO close ordering, `health_report()` aggregation, `close_all()` handles individual failures, empty registry edge case |

### 17.2 Integration with Existing Backends

| Test Module | Tests |
|-------------|-------|
| `tests/unit/cache/test_redis_with_manager.py` | `RedisCacheProvider` with injected `RedisConnectionManager` -- `get()`/`set()` work, `is_healthy()` delegates, backward compat without manager |
| `tests/unit/cache/test_s3_with_manager.py` | `S3CacheProvider` with injected `S3ConnectionManager` -- same pattern |

### 17.3 Mocking Strategy

All tests mock the underlying `redis` and `boto3` modules at the import boundary, following the existing pattern in `tests/unit/clients/test_*_cache.py`. The connection managers are testable without live Redis/S3 instances.

Circuit breaker integration tests use the real `CircuitBreaker` class with a low `failure_threshold` to verify state transitions affect health check behavior.

### 17.4 Key Test Scenarios

1. **Circuit breaker OPEN prevents health probe**: Set circuit to OPEN, call `health_check()`, verify no I/O (no PING/HeadBucket call), verify returns DISCONNECTED.
2. **Health check caching**: Call `health_check()` twice within TTL, verify probe runs only once.
3. **Force bypasses cache**: Call `health_check(force=True)`, verify probe runs even if cache is fresh.
4. **Close prevents further usage**: Call `close()`, then `get_connection()`, verify `CacheConnectionError`.
5. **Registry LIFO ordering**: Register [A, B, C], call `close_all()`, verify close order is C, B, A.
6. **Registry tolerates close failures**: Register [A, B], make A.close() raise, verify B still closes.
7. **Backward compatibility**: Create `RedisCacheProvider()` without `connection_manager`, verify all existing behavior unchanged.

---

## 18. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Manager injection breaks existing backend tests | Low | Medium -- test failures in CI | Phase 1 is opt-in: `connection_manager=None` is the default. All existing tests pass without changes. |
| Health check caching masks real failures | Medium | Low -- stale health for 10-30s | TTL is conservative (10s Redis, 30s S3). `force=True` available for critical paths. Circuit breaker provides sub-second failure detection independently. |
| boto3 client shared between sync/async callers causes threading issues | Low | High -- data corruption or deadlocks | boto3 S3 clients are documented as thread-safe for S3 operations. Existing `AsyncS3Client` already shares a single client across async tasks via `asyncio.to_thread`. |
| Shutdown ordering wrong (Redis closes after S3) | Low | Low -- some S3 writes fail during shutdown | LIFO ordering is deterministic. Register S3 first, Redis second. Even if ordering is wrong, the impact is limited to a few seconds during graceful shutdown. |
| Dual interface (sync+async) increases protocol surface | Medium | Low -- implementation burden | Both variants delegate to the same underlying logic. Async variants use `asyncio.to_thread` for sync backends. This is a standard pattern used throughout the codebase. |

---

## 19. ADRs

### ADR-CONN-001: ConnectionManager as Protocol, Not ABC

**Context**: Connection managers need a shared interface. The choice is between a Protocol (structural typing) and an ABC (nominal typing).

**Decision**: Use `typing.Protocol` with `@runtime_checkable`.

**Alternatives Considered**:
1. **ABC (`abc.ABC`)**: Requires explicit inheritance. Every manager must `class Foo(ConnectionManager)`. This creates coupling to the base class and makes it harder to adapt third-party classes.
2. **Protocol (structural typing)**: Any class with the right methods satisfies the protocol. Consistent with the existing `CacheProvider` protocol in `protocols/cache.py` and `RetryPolicy` protocol in `core/retry.py`.

**Consequences**: Managers do not need to inherit from a base class. Testing with mock objects is straightforward. Runtime checking via `isinstance()` works with `@runtime_checkable`. Consistent with existing patterns in the codebase.

---

### ADR-CONN-002: Health Check Caching Over Periodic Background Checks

**Context**: Health checks perform I/O (PING, HeadBucket). Two strategies are viable:
1. **Cached on-demand**: Check when asked, cache the result with a TTL.
2. **Periodic background**: Run a background task that probes every N seconds, store the last result.

**Decision**: Cached on-demand (option 1).

**Alternatives Considered**:
1. **Periodic background**: Requires managing a background task (asyncio.create_task or threading.Timer) with proper cancellation during shutdown. Adds complexity and another resource to clean up. The cache warming task already demonstrates the complexity of background task lifecycle.
2. **No caching**: Probe on every call. Simple but creates unnecessary I/O load when health endpoints are polled frequently.

**Consequences**: Health checks are lazy -- no probes happen until someone asks. The first call after TTL expiry takes longer (includes I/O). This is acceptable because health endpoints are not latency-critical and circuit breaker state provides instant failure detection.

---

### ADR-CONN-003: Shared boto3 Client for S3CacheProvider and AsyncS3Client

**Context**: Two S3 client instances exist with different configurations. `S3CacheProvider` uses boto3 defaults (60s timeouts, standard retry mode). `AsyncS3Client` uses custom timeouts (10s connect, 30s read) and disables boto3 retries.

**Decision**: `S3ConnectionManager` creates a single boto3 client with the `AsyncS3Client` timeout configuration (10s connect, 30s read) and disabled retries. Both consumers share this client.

**Rationale**:
- The `AsyncS3Client` configuration is more defensive (shorter timeouts, external retry via `RetryOrchestrator`).
- boto3's internal retry and the `RetryOrchestrator`'s retry would double-count retry attempts if both are active. Disabling boto3 retries and using `RetryOrchestrator` exclusively is the correct approach (per C3 design).
- A single client reduces the number of urllib3 connection pools.

**Consequences**: `S3CacheProvider` operations will have shorter timeouts (30s read instead of boto3's 60s default). This is an improvement -- long-hanging S3 operations will fail faster and trigger degraded mode sooner.

---

### ADR-CONN-004: LIFO Shutdown Order

**Context**: Connection managers must be closed in an order that respects dependencies.

**Decision**: Close in reverse registration order (LIFO).

**Rationale**: Registration happens during startup. In the cache tier architecture, the cold tier (S3) is a dependency of the hot tier (Redis -- cache-aside reads promote from S3 to Redis). Registering S3 first and Redis second means Redis closes first on shutdown. This prevents new cache operations that would require S3 reads while S3 is already closed.

**Alternatives Considered**:
1. **Explicit dependency graph**: Managers declare dependencies, registry topologically sorts. Over-engineered for two managers. Would be appropriate if we had 5+ managers with complex dependencies.
2. **Parallel close**: Close all managers simultaneously. Faster but does not respect dependencies. A Redis operation in progress might try to promote from an already-closed S3 client.

**Consequences**: Shutdown is sequential and deterministic. For two managers, the time difference between parallel and sequential close is negligible (both are sub-second).

---

## 20. Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| All existing tests pass without modification | CI green on all `tests/unit/cache/`, `tests/unit/clients/`, `tests/unit/dataframes/` |
| Connection managers are optional | `RedisCacheProvider()` and `S3CacheProvider()` work without `connection_manager` param |
| Health check caching reduces I/O | Unit test verifies probe count equals 1 for N calls within TTL |
| Circuit breaker gates health probes | Unit test verifies zero probes when circuit is OPEN |
| Graceful shutdown closes all connections | Integration test verifies `pool.disconnect()` called during lifespan exit |
| Connection state is reportable | `ConnectionRegistry.health_report()` returns per-backend state |
| No performance regression | Health check latency < 5ms when cached (no I/O) |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| Redis backend (current) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Read |
| S3 backend (current) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Read |
| AsyncS3Client (current) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py` | Read |
| Exception hierarchy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py` | Read |
| Retry orchestrator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/retry.py` | Read |
| DegradedModeMixin | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/errors.py` | Read |
| FastAPI lifespan | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Read |
| API dependencies | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | Read |
| Tiered cache provider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/providers/tiered.py` | Read |
| Exception hierarchy TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-exception-hierarchy.md` | Read |
| Retry orchestrator TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unified-retry-orchestrator.md` | Read |
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-connection-lifecycle-management.md` | Written |
