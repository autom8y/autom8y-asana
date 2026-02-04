# TDD: Unified Retry Orchestrator

**TDD ID**: TDD-RETRY-ORCHESTRATOR-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**Sprint**: S3 (Architectural Opportunities -- Wave 3)
**Task**: C3
**PRD Reference**: Architectural Opportunities Initiative
**Spike References**: S0-002 (Exception Audit), S0-006 (Concurrent Build Analysis)
**Depends On**: C1 (Exception Hierarchy -- implemented), B4 (Config Consolidation), A1 (Invalidation Pipeline)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Goals and Non-Goals](#3-goals-and-non-goals)
4. [Proposed Architecture](#4-proposed-architecture)
5. [Component Design: RetryPolicy](#5-component-design-retrypolicy)
6. [Component Design: RetryBudget](#6-component-design-retrybudget)
7. [Component Design: CircuitBreaker](#7-component-design-circuitbreaker)
8. [Component Design: RetryOrchestrator](#8-component-design-retryorchestrator)
9. [Integration Points](#9-integration-points)
10. [Configuration](#10-configuration)
11. [Observability](#11-observability)
12. [Data Flow Diagrams](#12-data-flow-diagrams)
13. [Migration Plan](#13-migration-plan)
14. [Module Placement](#14-module-placement)
15. [Interface Contracts](#15-interface-contracts)
16. [Non-Functional Considerations](#16-non-functional-considerations)
17. [Test Strategy](#17-test-strategy)
18. [Risk Assessment](#18-risk-assessment)
19. [ADRs](#19-adrs)
20. [Success Criteria](#20-success-criteria)

---

## 1. Overview

### 1.1 Problem Statement

The codebase has three independent retry implementations with no coordination:

| Backend | Implementation | Location | Strategy | Budget | Circuit Breaker |
|---------|---------------|----------|----------|--------|-----------------|
| **Redis** | `retry_on_timeout=True` in redis-py client config | `cache/backends/redis.py:55` | Single immediate retry (redis-py built-in) | None | None (degraded mode mixin) |
| **S3** | Custom `for attempt in range(max_retries)` loop | `dataframes/async_s3.py:319-389` | Exponential backoff (0.5s base, 3 max retries) | None | None (degraded mode mixin) |
| **HTTP/Asana** | `ExponentialBackoffRetry` from `autom8y_http` | `transport/asana_http.py:146-149` | Exponential backoff (0.5s base, 5 max retries, jitter) | None | Separate `CircuitBreaker` from `autom8y_http` |

A partial S3 outage triggers retries at the async_s3 layer, the persistence layer, and the cache backend layer simultaneously. Each layer's retries multiply the others. Without a shared retry budget, a 30-second infrastructure hiccup produces minutes of amplified load, compounding tail latency across the entire request path.

### 1.2 Solution Summary

A unified retry orchestrator providing:

| Component | Purpose |
|-----------|---------|
| `RetryPolicy` | Protocol defining retry strategy (exponential, linear, immediate) |
| `RetryBudget` | Shared token-bucket budget preventing cascade amplification |
| `CircuitBreaker` | Per-backend state machine (closed/open/half-open) coordinated with budget |
| `RetryOrchestrator` | Facade combining policy, budget, and circuit breaker for a single `execute_with_retry()` call |

### 1.3 Key Design Principle

**Composition over replacement.** The orchestrator does not replace `autom8y_http`'s `ExponentialBackoffRetry` for HTTP transport. It wraps the existing retry mechanisms at the coordination layer, adding budget enforcement and circuit breaker integration. This means the HTTP transport path gains budget awareness without reimplementing the platform SDK's retry logic.

---

## 2. Problem Statement

### 2.1 Cascade Amplification Scenario

Consider a partial S3 outage (elevated latency, 50% failure rate):

```
API Request: GET /query/tasks?project=12345
  |
  +-- TaskCacheCoordinator._cache_get()  --> Redis: OK (cache miss)
  |
  +-- universal_strategy._get_dataframe()
  |     |
  |     +-- DataFramePersistence.load()   --> S3: TIMEOUT (retry 1, 2, 3)
  |     |                                     Total: 3 attempts x 2s avg = ~6s
  |     |
  |     +-- AsyncS3Client.get_object()    --> S3: TIMEOUT (retry 1, 2, 3)
  |     |                                     Total: 3 attempts x 2s avg = ~6s
  |     |
  |     +-- SectionPersistence.load()     --> S3: TIMEOUT (retry 1, 2, 3)
  |                                           Total: 3 attempts x 2s avg = ~6s
  |
  Total S3 attempts: 9 (3 layers x 3 retries)
  Total wall time: ~18s (serialized) or ~6s (parallel) + backoff delays
  Actual useful work: 0 (all failed)
```

With N concurrent requests, the system generates 9N S3 requests during the outage window, accelerating the failure. Each retry consumes a connection pool slot, potentially starving healthy requests.

### 2.2 Missing Coordination Points

1. **No cross-layer budget**: Redis retry knows nothing about S3 retry. Both can exhaust simultaneously.
2. **No circuit breaker for S3/Redis**: Only HTTP transport has a circuit breaker (via `autom8y_http`). S3 and Redis rely on `DegradedModeMixin` which is a per-instance boolean with fixed reconnect interval -- not a proper state machine.
3. **No retry classification integration**: C1 exception hierarchy provides `TransportError.transient` property, but no retry mechanism consults it.
4. **No observability**: Retry attempts are logged as individual warnings with no aggregate view of retry pressure.

---

## 3. Goals and Non-Goals

### 3.1 Goals

| ID | Goal | Addresses |
|----|------|-----------|
| G1 | Shared retry budget across S3, Redis, and HTTP subsystems with configurable per-subsystem and global caps | Cascade amplification |
| G2 | Per-backend circuit breakers for S3 and Redis (HTTP already has one via autom8y_http) | Missing S3/Redis circuit breaker |
| G3 | RetryPolicy protocol that consults C1 `transient` property for retryability classification | C1 integration |
| G4 | Budget exhaustion triggers circuit breaker open, preventing further retries system-wide | Coordinated degradation |
| G5 | Structured log events for retry attempts, budget utilization, and circuit breaker state transitions | Observability |
| G6 | Backward-compatible integration -- existing callers see no API changes | Migration safety |

### 3.2 Non-Goals

- **Replacing `autom8y_http` retry/circuit breaker for HTTP transport.** The platform SDK manages HTTP retry internally. We wrap it with budget awareness, not replace it.
- **Distributed retry coordination.** Budget is process-local. Multi-process coordination (e.g., via Redis) is out of scope.
- **Rate limiting.** Rate limiting is a separate concern already handled by `TokenBucketRateLimiter` for HTTP and by Redis connection pool limits. This design is about retry coordination, not request admission.
- **Retry for business logic errors.** Only transport/infrastructure errors trigger retries. `CacheReadError` (serialization failure) and `AutomationError` are permanent and not retried.

---

## 4. Proposed Architecture

### 4.1 Component Relationships

```
                    +---------------------+
                    |  RetryOrchestrator  |  <-- Facade
                    +---------------------+
                    |  execute_with_retry |
                    +-----+-------+-------+
                          |       |
               +----------+       +----------+
               |                             |
    +----------v-----------+    +------------v-----------+
    |     RetryPolicy      |    |     RetryBudget        |
    +----------------------+    +------------------------+
    | strategy: BackoffType|    | subsystem_budgets{}    |
    | max_attempts: int    |    | global_budget          |
    | should_retry(exc)    |    | try_acquire(subsystem) |
    | delay_for(attempt)   |    | release(subsystem)     |
    +----------------------+    | is_exhausted()         |
                                +----------+-------------+
                                           |
                                +----------v-------------+
                                |    CircuitBreaker      |
                                +------------------------+
                                | state: CBState         |
                                | record_success()       |
                                | record_failure()       |
                                | allow_request()        |
                                +------------------------+
```

### 4.2 Integration Architecture

```
+------------------+     +------------------+     +------------------+
|  Redis Backend   |     |  S3 Backend      |     |  HTTP Transport  |
|  (redis.py)      |     |  (async_s3.py)   |     |  (asana_http.py) |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         |  uses                  |  uses                  |  wraps
         v                        v                        v
+--------+---------+     +--------+---------+     +--------+---------+
| RetryOrchestrator|     | RetryOrchestrator|     | BudgetAware      |
| (subsystem=redis)|     | (subsystem=s3)   |     | RetryPolicy      |
+--------+---------+     +--------+---------+     | (wraps platform) |
         |                        |                +--------+---------+
         +----------+    +--------+                        |
                    |    |                                  |
              +-----v----v-----+                           |
              |  RetryBudget   |<--------------------------+
              |  (shared)      |
              +----------------+
```

---

## 5. Component Design: RetryPolicy

### 5.1 Protocol

```python
# src/autom8_asana/core/retry.py

from __future__ import annotations

import enum
from typing import Protocol, runtime_checkable


class BackoffType(enum.Enum):
    """Retry backoff strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    IMMEDIATE = "immediate"
    NONE = "none"  # No retry (passthrough)


@runtime_checkable
class RetryPolicy(Protocol):
    """Protocol for retry decision-making.

    Implementations determine whether a failed operation should be retried
    and how long to wait before the next attempt.
    """

    @property
    def max_attempts(self) -> int:
        """Maximum number of attempts (including the initial attempt)."""
        ...

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if the operation should be retried.

        Consults the C1 exception hierarchy's `transient` property when
        the error is an Autom8Error subclass. For non-domain exceptions,
        falls back to isinstance checks against known transient types.

        Args:
            error: The exception that caused the failure.
            attempt: The current attempt number (1-indexed).

        Returns:
            True if retry should be attempted.
        """
        ...

    def delay_for(self, attempt: int) -> float:
        """Calculate delay in seconds before the next retry attempt.

        Args:
            attempt: The current attempt number (1-indexed).

        Returns:
            Delay in seconds. 0.0 for immediate retry.
        """
        ...
```

### 5.2 Default Implementation

```python
@dataclass(frozen=True)
class RetryPolicyConfig:
    """Configuration for the default retry policy.

    Attributes:
        backoff_type: Strategy for calculating delays.
        max_attempts: Maximum attempts including initial (1 = no retry).
        base_delay: Base delay in seconds for backoff calculation.
        max_delay: Maximum delay cap in seconds.
        jitter: Whether to add random jitter to delays (prevents thundering herd).
    """
    backoff_type: BackoffType = BackoffType.EXPONENTIAL
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    jitter: bool = True


class DefaultRetryPolicy:
    """Default retry policy with configurable backoff.

    Integrates with C1 exception hierarchy:
    - Autom8Error subclasses: consults `transient` property
    - botocore/redis errors: classified via error tuple membership
    - Unknown exceptions: not retried (fail-fast)
    """

    def __init__(self, config: RetryPolicyConfig | None = None) -> None:
        self._config = config or RetryPolicyConfig()

    @property
    def max_attempts(self) -> int:
        return self._config.max_attempts

    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self._config.max_attempts:
            return False
        return self._is_transient(error)

    def delay_for(self, attempt: int) -> float:
        if self._config.backoff_type == BackoffType.IMMEDIATE:
            return 0.0
        if self._config.backoff_type == BackoffType.LINEAR:
            delay = self._config.base_delay * attempt
        else:  # EXPONENTIAL
            delay = self._config.base_delay * (2 ** (attempt - 1))

        delay = min(delay, self._config.max_delay)

        if self._config.jitter:
            import random
            delay *= random.uniform(0.5, 1.5)

        return delay

    @staticmethod
    def _is_transient(error: Exception) -> bool:
        """Classify error transience using C1 hierarchy.

        Priority:
        1. Autom8Error.transient property (authoritative)
        2. Known transient error tuples (migration compatibility)
        3. Default: not transient (fail-fast)
        """
        from autom8_asana.core.exceptions import Autom8Error

        if isinstance(error, Autom8Error):
            return error.transient

        # Migration compatibility: check error tuple membership
        from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS
        if isinstance(error, CACHE_TRANSIENT_ERRORS):
            return True

        return False
```

### 5.3 Rationale

The `should_retry` method consults C1's `transient` property as the single source of truth for retryability classification. This means:
- `S3TransportError` with `error_code="NoSuchKey"` returns `transient=False` -- not retried.
- `S3TransportError` with `error_code="SlowDown"` returns `transient=True` -- retried.
- `RedisTransportError` returns `transient=True` -- retried.
- `CacheReadError` (deserialization failure) returns `transient=False` -- not retried.

This eliminates the duplicated `is_s3_retryable_error()` and `is_connection_error()` functions in `cache/errors.py`. Those functions remain for backward compatibility during migration but are superseded by the C1 hierarchy.

---

## 6. Component Design: RetryBudget

### 6.1 Concept

A retry budget is a token-bucket rate limiter applied to retry attempts (not requests). Each subsystem has a local budget, and a global budget caps total retry pressure across all subsystems. Tokens replenish over a sliding time window.

The key insight: **most of the time, retries are fine.** The budget only bites during cascading failures when multiple subsystems are retrying simultaneously. In steady state, the budget is effectively unlimited.

### 6.2 Interface

```python
class Subsystem(enum.Enum):
    """Subsystem identifiers for retry budget allocation."""
    REDIS = "redis"
    S3 = "s3"
    HTTP = "http"


@dataclass(frozen=True)
class BudgetConfig:
    """Configuration for retry budget.

    Attributes:
        per_subsystem_max: Maximum retry tokens per subsystem per window.
        global_max: Maximum retry tokens across all subsystems per window.
        window_seconds: Sliding window duration for token replenishment.
        min_tokens_for_probe: Minimum tokens reserved for circuit breaker probes.
    """
    per_subsystem_max: int = 20
    global_max: int = 50
    window_seconds: float = 60.0
    min_tokens_for_probe: int = 2


class RetryBudget:
    """Shared retry budget preventing cascade amplification.

    Thread-safe. Uses a sliding window counter for each subsystem
    and a global counter. When either budget is exhausted, further
    retries are denied, forcing fail-fast behavior.

    When the global budget is exhausted, it signals associated
    circuit breakers to open (coordinated degradation).
    """

    def __init__(self, config: BudgetConfig | None = None) -> None: ...

    def try_acquire(self, subsystem: Subsystem) -> bool:
        """Attempt to acquire a retry token.

        Returns False if:
        - Subsystem budget exhausted
        - Global budget exhausted

        Thread-safe via threading.Lock.

        Args:
            subsystem: Which subsystem is requesting the retry.

        Returns:
            True if retry is permitted, False if budget exhausted.
        """
        ...

    def release(self, subsystem: Subsystem) -> None:
        """Release a retry token (on success after retry).

        Optional: calling this after a successful retry
        gives the budget some breathing room.
        """
        ...

    def utilization(self, subsystem: Subsystem) -> float:
        """Current utilization ratio for a subsystem (0.0 to 1.0)."""
        ...

    def global_utilization(self) -> float:
        """Current global utilization ratio (0.0 to 1.0)."""
        ...

    def is_exhausted(self, subsystem: Subsystem | None = None) -> bool:
        """Check if budget is exhausted.

        Args:
            subsystem: Check specific subsystem. None checks global.
        """
        ...

    def reset(self) -> None:
        """Reset all budgets. For testing only."""
        ...
```

### 6.3 Implementation Notes

**Sliding window counter**: Use a deque of timestamps. On `try_acquire`, evict entries older than `window_seconds`, then check count against limit. This provides smooth replenishment without discrete window boundaries.

**Thread safety**: `threading.Lock` is sufficient. Budget operations are O(1) amortized (deque eviction) and non-blocking for callers. No need for asyncio locks since the budget is consulted from both sync (Redis) and async (S3, HTTP) code paths.

**Global exhaustion signal**: When `global_utilization() > 0.95`, emit a structured log event. When `global_utilization() == 1.0`, the orchestrator can notify circuit breakers to transition to open state. This is the coordinated degradation mechanism.

---

## 7. Component Design: CircuitBreaker

### 7.1 State Machine

```
         +--success-->[ CLOSED ]<--probe success--+
         |               |                         |
         |          failure_count >= threshold      |
         |               |                         |
         |               v                    +----+----+
         |           [ OPEN ]--recovery_timeout-->[ HALF_OPEN ]
         |               ^                         |
         |               +-----probe failure-------+
         |               |
         +--budget exhausted (coordinated)
```

### 7.2 Interface

```python
class CBState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration.

    Attributes:
        failure_threshold: Consecutive failures to trigger OPEN.
        recovery_timeout: Seconds before OPEN -> HALF_OPEN transition.
        half_open_max_probes: Successful probes to close circuit.
        name: Identifier for logging (e.g., "redis", "s3").
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_probes: int = 2
    name: str = "unknown"


class CircuitBreaker:
    """Per-backend circuit breaker with budget coordination.

    Unlike DegradedModeMixin (which is a boolean flag with time-based
    reconnect), this is a proper 3-state machine that:
    - Counts consecutive failures (not just checking a boolean)
    - Has an explicit half-open probe state
    - Coordinates with RetryBudget for system-wide degradation
    - Emits state transition events for observability

    Thread-safe.
    """

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        budget: RetryBudget | None = None,
    ) -> None: ...

    @property
    def state(self) -> CBState: ...

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns:
            True if circuit is CLOSED or HALF_OPEN (probe allowed).
            False if circuit is OPEN and recovery timeout not elapsed.
        """
        ...

    def record_success(self) -> None:
        """Record a successful operation.

        In HALF_OPEN: increments probe success counter.
            If enough probes succeed, transitions to CLOSED.
        In CLOSED: resets consecutive failure counter.
        """
        ...

    def record_failure(self, error: Exception) -> None:
        """Record a failed operation.

        In CLOSED: increments failure counter.
            If threshold reached, transitions to OPEN.
        In HALF_OPEN: transitions immediately to OPEN.
        """
        ...

    def force_open(self, reason: str) -> None:
        """Force circuit to OPEN state (e.g., budget exhaustion).

        Args:
            reason: Why the circuit was forced open (for logging).
        """
        ...
```

### 7.3 Relationship with DegradedModeMixin

The existing `DegradedModeMixin` in `cache/errors.py` is a simpler degradation mechanism:
- Binary state: `_degraded = True/False`
- Time-based reconnect: `_reconnect_interval` with `should_attempt_reconnect()`
- No failure counting, no half-open probing

The `CircuitBreaker` replaces the DegradedModeMixin's role in retry decisions. However, `DegradedModeMixin` also serves a different purpose in backends: it prevents any operations (not just retries) when the backend is unreachable. The two can coexist:

- `CircuitBreaker`: Controls retry decisions via `RetryOrchestrator`.
- `DegradedModeMixin`: Controls whether the backend is skipped entirely (return None / no-op).

During migration, backends continue using `DegradedModeMixin` for operational bypass. The `CircuitBreaker` adds coordinated retry control on top. Post-migration, `DegradedModeMixin.enter_degraded_mode()` can be triggered by `CircuitBreaker` state transitions (see Section 9).

---

## 8. Component Design: RetryOrchestrator

### 8.1 Facade Interface

```python
class RetryOrchestrator:
    """Facade combining retry policy, budget, and circuit breaker.

    Provides a single `execute_with_retry()` method that:
    1. Checks circuit breaker state
    2. Executes the operation
    3. On failure: checks policy, checks budget, waits, retries
    4. On success: records success with circuit breaker
    5. On exhaustion: records failure, potentially opens circuit

    Supports both sync and async callables.
    """

    def __init__(
        self,
        policy: RetryPolicy,
        budget: RetryBudget,
        circuit_breaker: CircuitBreaker,
        subsystem: Subsystem,
    ) -> None: ...

    def execute_with_retry(
        self,
        operation: Callable[[], T],
        *,
        operation_name: str = "unknown",
    ) -> T:
        """Execute a synchronous operation with retry orchestration.

        Args:
            operation: Callable to execute.
            operation_name: For logging/observability.

        Returns:
            Result of the operation.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open.
            Original exception: After all retries exhausted.
        """
        ...

    async def execute_with_retry_async(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        operation_name: str = "unknown",
    ) -> T:
        """Execute an async operation with retry orchestration.

        Same semantics as execute_with_retry but uses asyncio.sleep
        for delays.
        """
        ...
```

### 8.2 Execution Flow

```python
# Pseudocode for execute_with_retry_async
async def execute_with_retry_async(self, operation, *, operation_name="unknown"):
    for attempt in range(1, self._policy.max_attempts + 1):
        # 1. Check circuit breaker
        if not self._circuit_breaker.allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker open for {self._subsystem.value}",
                backend=self._subsystem.value,
                operation=operation_name,
            )

        try:
            # 2. Execute operation
            result = await operation()

            # 3. Record success
            self._circuit_breaker.record_success()
            if attempt > 1:
                self._budget.release(self._subsystem)
                logger.info("retry_succeeded", ...)
            return result

        except Exception as exc:
            # 4. Record failure with circuit breaker
            self._circuit_breaker.record_failure(exc)

            # 5. Check if retryable via policy
            if not self._policy.should_retry(exc, attempt):
                raise

            # 6. Check budget
            if not self._budget.try_acquire(self._subsystem):
                logger.warning("retry_budget_exhausted", ...)
                raise  # Budget exhausted, fail fast

            # 7. Calculate delay and wait
            delay = self._policy.delay_for(attempt)
            logger.warning("retry_attempt", ...)
            await asyncio.sleep(delay)

    # Should not reach here, but defensive
    raise RuntimeError("Retry loop exited without result or exception")
```

---

## 9. Integration Points

### 9.1 Redis Backend Integration

**Current**: `redis.py` uses `retry_on_timeout=True` in the redis-py `ConnectionPool` constructor and wraps operations in `try/except REDIS_TRANSPORT_ERRORS`.

**Target**: Remove `retry_on_timeout=True`. Wrap each Redis operation call in `orchestrator.execute_with_retry()`.

```python
# BEFORE (cache/backends/redis.py)
def get(self, key: str) -> dict[str, Any] | None:
    try:
        conn = self._get_connection()
        try:
            data = conn.get(key)
            ...
        finally:
            conn.close()
    except REDIS_TRANSPORT_ERRORS as e:
        self._handle_redis_error(e, operation="get")
        return None

# AFTER
def get(self, key: str) -> dict[str, Any] | None:
    try:
        return self._retry_orchestrator.execute_with_retry(
            lambda: self._do_get(key),
            operation_name="redis_get",
        )
    except (RedisTransportError, CircuitBreakerOpenError):
        return None  # Graceful degradation preserved

def _do_get(self, key: str) -> dict[str, Any] | None:
    conn = self._get_connection()
    try:
        data = conn.get(key)
        ...
        return result
    finally:
        conn.close()
```

**Backward compatibility**: The public API of `RedisCacheProvider` does not change. Callers still call `get()`, `set()`, etc. The retry orchestrator is an internal implementation detail.

**DegradedModeMixin coordination**: When the circuit breaker transitions to OPEN, the orchestrator calls `self.enter_degraded_mode(reason)`. When it transitions to CLOSED (after successful half-open probes), it calls `self.exit_degraded_mode()`. This synchronizes the two mechanisms.

### 9.2 S3 Backend Integration

**Current**: `async_s3.py` has an inline retry loop with `for attempt in range(self._config.max_retries)` and manual exponential backoff in `put_object_async()` and `get_object_async()`.

**Target**: Replace inline retry loops with `orchestrator.execute_with_retry_async()`.

```python
# BEFORE (dataframes/async_s3.py)
async def put_object_async(self, key, body, ...):
    for attempt in range(self._config.max_retries):
        try:
            client = self._get_client()
            response = await asyncio.to_thread(client.put_object, ...)
            return S3WriteResult(success=True, ...)
        except S3_TRANSPORT_ERRORS as e:
            if self._is_retryable_error(e) and attempt < self._config.max_retries - 1:
                delay = self._config.base_retry_delay * (2**attempt)
                await asyncio.sleep(delay)
            else:
                return S3WriteResult(success=False, ...)

# AFTER
async def put_object_async(self, key, body, ...):
    start_time = time.monotonic()
    try:
        response = await self._retry_orchestrator.execute_with_retry_async(
            lambda: self._do_put_object(key, body, content_type, metadata),
            operation_name="s3_put_object",
        )
        duration_ms = (time.monotonic() - start_time) * 1000
        return S3WriteResult(success=True, key=key, ...)
    except (S3TransportError, CircuitBreakerOpenError) as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        self._handle_error(e, "put_object", key)
        return S3WriteResult(success=False, key=key, error=str(e), ...)
```

**Backward compatibility**: `S3WriteResult` and `S3ReadResult` return types unchanged. The `AsyncS3Config.max_retries` and `base_retry_delay` fields are preserved for backward compatibility but are superseded by the orchestrator policy. During migration, the config fields map to `RetryPolicyConfig`.

### 9.3 HTTP Transport Integration

**Current**: `asana_http.py` creates `ExponentialBackoffRetry` from `autom8y_http` and manages retry, rate limiting, and circuit breaker independently via the platform SDK.

**Target**: Wrap the existing platform retry policy with budget awareness. Do NOT replace the platform SDK's retry mechanism.

```python
# NEW: BudgetAwareRetryPolicy wrapping platform ExponentialBackoffRetry
class BudgetAwareRetryPolicy:
    """Wraps autom8y_http ExponentialBackoffRetry with budget enforcement.

    Delegates retry decisions to the platform policy but gates them
    through the shared RetryBudget. If budget is exhausted, retry
    is denied regardless of what the platform policy says.
    """

    def __init__(
        self,
        inner: RetryPolicyProtocol,
        budget: RetryBudget,
        subsystem: Subsystem = Subsystem.HTTP,
    ) -> None:
        self._inner = inner
        self._budget = budget
        self._subsystem = subsystem

    def should_retry(self, error, attempt) -> bool:
        if not self._inner.should_retry(error, attempt):
            return False
        return self._budget.try_acquire(self._subsystem)

    # Delegate all other protocol methods to inner
```

**Integration in AsanaHttpClient**:

```python
# transport/asana_http.py
def _create_retry_policy(self) -> BudgetAwareRetryPolicy:
    retry_config = ConfigTranslator.to_retry_config(self._config)
    inner = ExponentialBackoffRetry(config=retry_config, logger=self._logger)
    return BudgetAwareRetryPolicy(
        inner=inner,
        budget=self._shared_budget,
        subsystem=Subsystem.HTTP,
    )
```

**Backward compatibility**: Full. `AsanaHttpClient` still exposes the same public API. The budget wrapping is invisible to callers.

---

## 10. Configuration

### 10.1 Config Location

Configuration lives in `src/autom8_asana/config.py` alongside existing `RetryConfig`, `CircuitBreakerConfig`, etc. New dataclasses:

```python
@dataclass(frozen=True)
class RetryOrchestratorConfig:
    """Unified retry orchestrator configuration.

    Per TDD-RETRY-ORCHESTRATOR-001: Consolidates retry behavior
    across Redis, S3, and HTTP subsystems.

    Attributes:
        budget: Shared retry budget configuration.
        redis_policy: Retry policy for Redis operations.
        s3_policy: Retry policy for S3 operations.
        redis_circuit_breaker: Circuit breaker for Redis backend.
        s3_circuit_breaker: Circuit breaker for S3 backend.
    """
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    redis_policy: RetryPolicyConfig = field(
        default_factory=lambda: RetryPolicyConfig(
            backoff_type=BackoffType.EXPONENTIAL,
            max_attempts=3,
            base_delay=0.1,
            max_delay=2.0,
            jitter=True,
        )
    )
    s3_policy: RetryPolicyConfig = field(
        default_factory=lambda: RetryPolicyConfig(
            backoff_type=BackoffType.EXPONENTIAL,
            max_attempts=3,
            base_delay=0.5,
            max_delay=30.0,
            jitter=True,
        )
    )
    redis_circuit_breaker: CircuitBreakerConfig = field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=30.0,
            half_open_max_probes=2,
            name="redis",
        )
    )
    s3_circuit_breaker: CircuitBreakerConfig = field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_probes=1,
            name="s3",
        )
    )
```

Note: HTTP retry/circuit breaker config is NOT duplicated here. It remains in `AsanaConfig.retry` and `AsanaConfig.circuit_breaker`, translated via `ConfigTranslator`. The orchestrator only adds budget awareness to the HTTP path.

### 10.2 Default Values Rationale

| Parameter | Redis | S3 | Why |
|-----------|-------|-----|-----|
| max_attempts | 3 | 3 | Matches S3 current behavior. Redis was 1 (immediate retry via redis-py). 3 is the sweet spot: enough to survive transient blips, not enough to cause cascade. |
| base_delay | 0.1s | 0.5s | Redis operations are sub-ms; 100ms is generous. S3 operations are 50-500ms; 500ms base matches current behavior. |
| max_delay | 2.0s | 30.0s | Redis: if 2s of retrying hasn't worked, the backend is down. S3: transient throttling can last 10-20s. |
| failure_threshold | 5 | 5 | 5 consecutive failures indicates a real problem, not a blip. |
| recovery_timeout | 30s | 60s | Redis recovers faster (reconnect). S3 outages tend to last longer. |
| budget per_subsystem | 20 | 20 | 20 retries per minute per subsystem. Across 3 subsystems, that is 60 retries/min global budget (capped at 50). |

### 10.3 Environment Variable Overrides

Following the existing pattern from `CacheConfig.from_env()`:

| Env Var | Type | Default | Description |
|---------|------|---------|-------------|
| `ASANA_RETRY_BUDGET_PER_SUBSYSTEM` | int | 20 | Per-subsystem retry budget per window |
| `ASANA_RETRY_BUDGET_GLOBAL` | int | 50 | Global retry budget per window |
| `ASANA_RETRY_BUDGET_WINDOW_SECONDS` | float | 60.0 | Budget replenishment window |
| `ASANA_RETRY_REDIS_MAX_ATTEMPTS` | int | 3 | Redis max retry attempts |
| `ASANA_RETRY_S3_MAX_ATTEMPTS` | int | 3 | S3 max retry attempts |

---

## 11. Observability

### 11.1 Structured Log Events

All events use `autom8y_log.get_logger(__name__)` following codebase conventions.

| Event | Level | When | Fields |
|-------|-------|------|--------|
| `retry_attempt` | WARNING | Each retry attempt | subsystem, operation, attempt, max_attempts, delay_seconds, error, error_type |
| `retry_succeeded` | INFO | Retry succeeds after failure | subsystem, operation, total_attempts, total_duration_ms |
| `retry_exhausted` | ERROR | All retries failed | subsystem, operation, total_attempts, total_duration_ms, final_error |
| `retry_budget_exhausted` | WARNING | Budget denies retry | subsystem, utilization, global_utilization |
| `circuit_breaker_state_change` | WARNING | State transition | name, from_state, to_state, reason, failure_count |
| `circuit_breaker_probe` | INFO | Half-open probe attempt | name, probe_number, max_probes |
| `retry_budget_high_utilization` | WARNING | Utilization > 80% | subsystem, utilization, global_utilization |

### 11.2 Metrics Surface

The orchestrator exposes a `RetryMetrics` dataclass for integration with health endpoints:

```python
@dataclass
class RetryMetrics:
    """Snapshot of retry orchestrator state for health/diagnostics."""
    budget_utilization: dict[str, float]  # subsystem -> 0.0-1.0
    global_budget_utilization: float
    circuit_breaker_states: dict[str, str]  # name -> "closed"/"open"/"half_open"
    total_retries_last_window: dict[str, int]  # subsystem -> count
    total_budget_denials_last_window: int
```

This can be exposed via the existing `/health` endpoint or a new `/health/resilience` endpoint.

---

## 12. Data Flow Diagrams

### 12.1 Normal Operation (All Circuits Closed)

```
Request --> RetryOrchestrator.execute_with_retry_async()
  |
  +-- CircuitBreaker.allow_request() --> True (CLOSED)
  |
  +-- operation() --> SUCCESS
  |
  +-- CircuitBreaker.record_success()
  |
  +-- Return result
```

### 12.2 Transient Failure with Successful Retry

```
Request --> RetryOrchestrator.execute_with_retry_async()
  |
  +-- CircuitBreaker.allow_request() --> True (CLOSED)
  |
  +-- operation() --> FAIL (S3TransportError, transient=True)
  |
  +-- CircuitBreaker.record_failure()
  +-- RetryPolicy.should_retry() --> True
  +-- RetryBudget.try_acquire(s3) --> True (12/20 used)
  +-- delay_for(1) --> 0.5s
  +-- asyncio.sleep(0.5)
  |
  +-- CircuitBreaker.allow_request() --> True (CLOSED, 1 failure < 5 threshold)
  |
  +-- operation() --> SUCCESS
  |
  +-- CircuitBreaker.record_success()
  +-- RetryBudget.release(s3) --> (11/20 used)
  |
  +-- Return result
```

### 12.3 Cascade Prevention (Budget Exhausted)

```
Request --> RetryOrchestrator.execute_with_retry_async()
  |
  +-- CircuitBreaker.allow_request() --> True (CLOSED)
  |
  +-- operation() --> FAIL (S3TransportError, transient=True)
  |
  +-- CircuitBreaker.record_failure()
  +-- RetryPolicy.should_retry() --> True
  +-- RetryBudget.try_acquire(s3) --> FALSE (20/20 used)
  |
  +-- Log: retry_budget_exhausted
  +-- Raise original S3TransportError (fail-fast)
```

### 12.4 Circuit Breaker Open

```
Request --> RetryOrchestrator.execute_with_retry_async()
  |
  +-- CircuitBreaker.allow_request() --> False (OPEN, recovery_timeout not elapsed)
  |
  +-- Raise CircuitBreakerOpenError
  |
  Caller handles graceful degradation (return None, use stale data, etc.)
```

---

## 13. Migration Plan

### 13.1 Phase 1: Infrastructure (No Behavioral Change)

1. Create `src/autom8_asana/core/retry.py` with `RetryPolicy`, `DefaultRetryPolicy`, `RetryBudget`, `CircuitBreaker`, `RetryOrchestrator`.
2. Create `RetryOrchestratorConfig` in `config.py`.
3. Unit tests for all components in isolation.

**Risk**: Zero. No existing code is modified.

### 13.2 Phase 2: Redis Integration

1. Add `RetryOrchestrator` as optional constructor parameter to `RedisCacheProvider`.
2. When orchestrator is provided, remove `retry_on_timeout=True` from ConnectionPool config.
3. Wrap each public method's internal call in `execute_with_retry()`.
4. Wire circuit breaker state changes to `enter_degraded_mode()` / `exit_degraded_mode()`.

**Backward compatibility**: When `RetryOrchestrator` is None (default), existing behavior is preserved unchanged. The `retry_on_timeout` parameter is only removed when the orchestrator is active.

**Risk**: Low. Redis retry was a single immediate retry. The orchestrator provides 3 retries with backoff, which is strictly better for transient failures.

### 13.3 Phase 3: S3 Integration

1. Add `RetryOrchestrator` as optional constructor parameter to `AsyncS3Client`.
2. When orchestrator is provided, replace inline retry loops in `put_object_async()` and `get_object_async()` with `execute_with_retry_async()`.
3. Preserve `S3WriteResult` / `S3ReadResult` return types.

**Backward compatibility**: When `RetryOrchestrator` is None, existing inline retry loop is used. The `AsyncS3Config.max_retries` and `base_retry_delay` fields continue to work.

**Risk**: Medium. The S3 retry loop has edge cases around `_is_not_found_error` (404 should not retry). The `DefaultRetryPolicy._is_transient()` handles this via `S3TransportError.transient` property, which returns `False` for `NoSuchKey`. Must verify the error wrapping happens before the retry check.

### 13.4 Phase 4: HTTP Budget Wrapping

1. Create `BudgetAwareRetryPolicy` wrapper.
2. In `AsanaHttpClient.__init__()`, wrap the platform retry policy with budget awareness when a shared budget is provided.
3. Wire through `AsanaClient` initialization.

**Backward compatibility**: Full. The platform SDK's retry behavior is unchanged. Budget only gates retries, never adds them.

**Risk**: Low. The wrapper is a transparent pass-through that only denies retries when budget is exhausted.

### 13.5 Phase 5: Wiring

1. Create shared `RetryBudget` instance in `AsanaClient.__init__()` or `api/dependencies.py`.
2. Create per-subsystem `CircuitBreaker` instances.
3. Create per-subsystem `RetryOrchestrator` instances.
4. Inject into `RedisCacheProvider`, `AsyncS3Client`, `AsanaHttpClient`.
5. Expose `RetryMetrics` on health endpoint.

---

## 14. Module Placement

### 14.1 File Structure

```
src/autom8_asana/core/
    exceptions.py          # Existing (C1 exception hierarchy)
    retry.py               # NEW: RetryPolicy, DefaultRetryPolicy, RetryPolicyConfig,
                           #       BackoffType, RetryBudget, BudgetConfig, Subsystem,
                           #       CircuitBreaker, CircuitBreakerConfig, CBState,
                           #       RetryOrchestrator, RetryMetrics
    entity_registry.py     # Existing (B1)

src/autom8_asana/transport/
    asana_http.py          # MODIFIED: BudgetAwareRetryPolicy wrapper
    budget_aware_retry.py  # NEW: BudgetAwareRetryPolicy (if too large for inline)

src/autom8_asana/config.py # MODIFIED: RetryOrchestratorConfig added

tests/unit/core/
    test_retry_policy.py   # NEW
    test_retry_budget.py   # NEW
    test_circuit_breaker.py # NEW
    test_retry_orchestrator.py # NEW

tests/integration/
    test_retry_integration.py  # NEW: End-to-end with mocked backends
```

### 14.2 Placement Rationale

The `core/retry.py` placement follows the same pattern as `core/exceptions.py`: cross-cutting infrastructure that does not belong to a single subsystem. The retry module is consumed by `cache/backends/redis.py`, `dataframes/async_s3.py`, and `transport/asana_http.py` -- three different packages. Placing it in `core/` avoids creating a circular dependency.

This placement also informs B2 (Cache Module Reorganization): when the cache module is reorganized, the retry/circuit breaker logic lives outside `cache/`, so backends can import it cleanly without intra-package dependency tangles.

---

## 15. Interface Contracts

### 15.1 RetryOrchestrator Construction

```python
# Standard construction for Redis backend
redis_orchestrator = RetryOrchestrator(
    policy=DefaultRetryPolicy(config.retry_orchestrator.redis_policy),
    budget=shared_budget,  # Same instance across all subsystems
    circuit_breaker=CircuitBreaker(
        config=config.retry_orchestrator.redis_circuit_breaker,
        budget=shared_budget,
    ),
    subsystem=Subsystem.REDIS,
)
```

### 15.2 Shared Budget Contract

The `RetryBudget` instance MUST be shared across all subsystems. A single `RetryBudget` object is created once (typically in `AsanaClient.__init__()` or `api/dependencies.py`) and passed to all `RetryOrchestrator` and `CircuitBreaker` instances.

```python
# In api/dependencies.py or client.py
shared_budget = RetryBudget(config=config.retry_orchestrator.budget)

redis_cb = CircuitBreaker(config=..., budget=shared_budget)
s3_cb = CircuitBreaker(config=..., budget=shared_budget)

redis_orchestrator = RetryOrchestrator(
    policy=..., budget=shared_budget, circuit_breaker=redis_cb, subsystem=Subsystem.REDIS
)
s3_orchestrator = RetryOrchestrator(
    policy=..., budget=shared_budget, circuit_breaker=s3_cb, subsystem=Subsystem.S3
)
```

### 15.3 Error Handling Contract

| Scenario | Orchestrator Behavior |
|----------|-----------------------|
| Operation succeeds on first attempt | Return result, no retry machinery involved |
| Transient error, budget available | Retry with backoff, up to max_attempts |
| Transient error, budget exhausted | Raise original exception immediately |
| Permanent error (transient=False) | Raise immediately, no retry attempted |
| Circuit breaker open | Raise `CircuitBreakerOpenError` before attempting operation |
| All retries exhausted | Raise last exception |

---

## 16. Non-Functional Considerations

### 16.1 Performance

**Overhead in happy path**: Near-zero. `allow_request()` is a timestamp comparison. `record_success()` is a counter decrement. No locks in the hot path when circuit is CLOSED and budget is not near exhaustion.

**Budget check cost**: O(1) amortized. Deque eviction happens lazily during `try_acquire()`. In steady state (budget well under limit), this is a deque length check.

**Memory**: `RetryBudget` stores one deque of timestamps per subsystem (3 deques). At 20 entries/minute, this is negligible.

### 16.2 Thread Safety

All shared state (`RetryBudget`, `CircuitBreaker`) uses `threading.Lock`. This is correct because:
- Redis operations are synchronous (called from sync code or via threads)
- S3 operations use `asyncio.to_thread()` (run in thread pool)
- The lock contention is negligible: budget/circuit breaker operations are O(1)

Async code paths use `execute_with_retry_async()` which calls `asyncio.sleep()` for delays. Sync code paths use `execute_with_retry()` which calls `time.sleep()`.

### 16.3 Testing

The `RetryBudget` and `CircuitBreaker` expose `reset()` methods for test isolation. The `RetryOrchestrator` accepts all dependencies via constructor injection, making it fully testable with mocks.

---

## 17. Test Strategy

### 17.1 Unit Tests

| Component | Test Cases | Priority |
|-----------|-----------|----------|
| `DefaultRetryPolicy` | Transient Autom8Error retried; permanent Autom8Error not retried; unknown exception not retried; max_attempts honored; delay calculation for each backoff type; jitter within bounds | P0 |
| `RetryBudget` | Acquire within limit; acquire denied at limit; window expiration replenishes; global cap independent of per-subsystem; utilization calculation; thread-safety under concurrent access | P0 |
| `CircuitBreaker` | CLOSED->OPEN after threshold failures; OPEN->HALF_OPEN after timeout; HALF_OPEN->CLOSED after probes; HALF_OPEN->OPEN on probe failure; force_open; thread-safety | P0 |
| `RetryOrchestrator` | Happy path (no retry); retry on transient error; budget denial stops retry; circuit breaker open raises; async variant; operation_name in logs | P0 |
| `BudgetAwareRetryPolicy` | Delegates to inner when budget available; denies when budget exhausted; passes through non-retry decisions | P1 |

### 17.2 Integration Tests

| Scenario | What It Validates |
|----------|-------------------|
| Redis backend with orchestrator, simulated timeout | Retry happens, circuit breaker tracks failures |
| S3 backend with orchestrator, simulated throttle | Exponential backoff, budget consumption |
| Budget exhaustion across subsystems | S3 retries consume budget, Redis retry denied by global cap |
| Circuit breaker recovery | OPEN -> HALF_OPEN -> CLOSED transition under simulated recovery |
| HTTP budget wrapping | Platform retry policy gated by shared budget |

### 17.3 Chaos/Stress Tests (Post-Implementation)

| Scenario | Expected Behavior |
|----------|-------------------|
| 50% S3 failure rate, 10 concurrent requests | Total S3 attempts bounded by budget (not 10x3=30) |
| Redis down, S3 healthy | Redis circuit opens within 5 failures, S3 unaffected |
| All backends degraded | Global budget exhaustion triggers fail-fast across all paths |

---

## 18. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Retry budget too conservative (denies retries that would have succeeded) | Medium | Medium | Default of 20 retries/min/subsystem is generous. Monitor `retry_budget_exhausted` events. Make configurable via env vars. |
| Circuit breaker false positive (opens on transient blip) | Low | High | Threshold of 5 consecutive failures is conservative. Must be truly consecutive, not sampled. |
| Thread-safety bug in budget/circuit breaker | Low | High | Comprehensive concurrent unit tests. Use `threading.Lock` not `asyncio.Lock` (correct for mixed sync/async). |
| S3 error wrapping race: error classified before wrapping to S3TransportError | Medium | Medium | Ensure `S3TransportError.from_boto_error()` is called before `should_retry()`. The orchestrator wraps the operation, so the inner function must raise domain exceptions. |
| Redis `retry_on_timeout` removal breaks edge cases | Low | Low | Phase 2 is opt-in (orchestrator=None preserves old behavior). Integration tests before removing the flag. |
| `autom8y_http` platform SDK compatibility with BudgetAwareRetryPolicy wrapper | Low | Medium | BudgetAwareRetryPolicy implements `RetryPolicyProtocol` from `autom8y_http`. Verify protocol conformance in tests. |

---

## 19. ADRs

### ADR-C3-001: Budget Enforcement Strategy

**Status**: Proposed

**Context**: We need a mechanism to prevent cascading retries across Redis, S3, and HTTP subsystems during partial infrastructure failures. Options considered:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Token-bucket budget (selected)** | Sliding-window counter per subsystem + global cap | Simple, predictable, low overhead, configurable | Process-local (no multi-process coordination) |
| B. Adaptive rate limiting | Dynamically adjust retry rate based on success ratio | Responds to conditions automatically | Complex, hard to reason about, delayed reaction |
| C. Fixed retry count per request | Each request gets N total retries across all subsystems | Prevents per-request amplification | Does not prevent system-wide amplification; unfair to requests arriving during recovery |
| D. No budget (circuit breaker only) | Rely solely on circuit breakers opening | Simpler | Circuit breaker opening takes N failures; during ramp-up, all requests retry freely |

**Decision**: Option A -- Token-bucket retry budget.

**Rationale**: The problem is specifically about aggregate retry volume during infrastructure degradation. A token-bucket counter directly measures and limits this volume. The implementation is straightforward (deque of timestamps), configurable via env vars, and the process-local constraint is acceptable because this application runs as a single-process FastAPI server (no multi-worker deployment currently).

Option B is over-engineered for the problem. Option C solves per-request fairness but not system-wide amplification. Option D leaves a gap between the first failure and circuit breaker opening where uncontrolled retry amplification occurs.

**Consequences**:
- Retry pressure is bounded regardless of concurrent request count.
- During recovery, the budget replenishes naturally via the sliding window.
- If multi-process deployment is needed later, the budget can be backed by Redis (but this is not needed now).

---

### ADR-C3-002: Circuit Breaker Scope

**Status**: Proposed

**Context**: We need circuit breakers for S3 and Redis backends. The HTTP transport already has one from `autom8y_http`. Options for the S3/Redis circuit breakers:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Per-backend instance (selected)** | One circuit breaker per backend type (redis CB, s3 CB) | Simple, matches failure domains; S3 outage does not affect Redis | Coarse-grained (all S3 operations share one circuit) |
| B. Per-operation instance | Separate CB for s3_get, s3_put, redis_get, redis_set | Fine-grained isolation; read-only operations can continue during write failures | Many instances to manage; most S3/Redis failures are backend-wide, not operation-specific |
| C. Per-key-prefix instance | Separate CB for different S3 prefixes or Redis key patterns | Maximum isolation | Over-engineering; S3 failures are rarely prefix-specific |

**Decision**: Option A -- Per-backend instance.

**Rationale**: S3 and Redis failures are almost always backend-wide (network timeout, service unavailable, connection pool exhaustion). A per-operation granularity would only help in the rare case where S3 reads work but writes fail, which is not a realistic failure mode for S3. Per-backend matches the actual failure domain.

This also matches the existing `DegradedModeMixin` pattern, which is per-backend-instance.

**Consequences**:
- When the S3 circuit opens, all S3 operations fail fast (read and write).
- This is acceptable because S3 failures are typically backend-wide.
- If future evidence shows operation-specific failure modes, the architecture supports refinement without changing the orchestrator interface.

---

### ADR-C3-003: Async vs Sync Retry Execution

**Status**: Proposed

**Context**: The codebase has both sync (Redis) and async (S3, HTTP) code paths. The retry orchestrator must support both.

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Dual methods (selected)** | `execute_with_retry()` (sync) and `execute_with_retry_async()` (async) | Clear, type-safe, no runtime detection | Two methods to maintain |
| B. Single async method, sync callers use `asyncio.run()` | One async implementation | DRY | Sync callers (Redis) would need an event loop; breaks thread-pool callers |
| C. Single method with runtime callable detection | Inspect callable, auto-dispatch | One method | `inspect.iscoroutinefunction` is fragile with decorators; confusing semantics |
| D. Callback-based | Orchestrator provides a callback for "wait" behavior | Maximum flexibility | Awkward API, leaks abstraction |

**Decision**: Option A -- Dual methods.

**Rationale**: The Redis backend is synchronous (uses `threading.Lock`, no event loop). The S3 and HTTP backends are asynchronous. These are fundamentally different calling conventions. Trying to bridge them with a single method creates more complexity than maintaining two methods that share the same core logic via a private helper.

The shared logic (policy check, budget check, circuit breaker check) is extracted into `_should_attempt()` and `_handle_failure()` private methods. Only the sleep mechanism differs: `time.sleep()` vs `asyncio.sleep()`.

**Consequences**:
- Callers choose the appropriate method based on their execution context.
- Core retry logic is not duplicated (shared private methods).
- Adding a third execution model (e.g., trio) would require a third method, but this is unlikely.

---

## 20. Success Criteria

### 20.1 Functional

| Criterion | Measurement |
|-----------|-------------|
| S3 retries are budget-limited | Under simulated 50% S3 failure, total retry count stays within budget (20/min) regardless of concurrent request count |
| Redis retries replace `retry_on_timeout` | `retry_on_timeout=False` in ConnectionPool config when orchestrator is active, with equivalent or better retry behavior |
| HTTP retries are budget-aware | Platform `ExponentialBackoffRetry` retries are gated by shared budget |
| Circuit breaker opens on sustained failure | After 5 consecutive failures, circuit opens and requests fail fast |
| Circuit breaker recovers | After recovery timeout, half-open probes succeed, circuit closes |
| Budget exhaustion stops all retries | When global budget hits 50/min, no subsystem can acquire retry tokens |
| C1 integration works | `S3TransportError(error_code="NoSuchKey")` is not retried; `S3TransportError(error_code="SlowDown")` is retried |

### 20.2 Non-Functional

| Criterion | Target |
|-----------|--------|
| Happy-path overhead | < 0.1ms per operation (circuit breaker check + no retry) |
| Retry budget memory | < 1KB per subsystem |
| Thread-safety | No data races under 100 concurrent operations in stress test |
| Backward compatibility | All existing tests pass without modification |

### 20.3 Observability

| Criterion | Measurement |
|-----------|-------------|
| Retry events logged | Every retry attempt produces a structured log event |
| Budget utilization visible | Health endpoint exposes per-subsystem utilization |
| Circuit breaker state visible | Health endpoint exposes per-backend circuit state |
| State transitions logged | Every CLOSED->OPEN, OPEN->HALF_OPEN, HALF_OPEN->CLOSED transition logged |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unified-retry-orchestrator.md` | Written |
| C1 Exception Hierarchy (dependency) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py` | Read |
| Redis Backend (integration target) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Read |
| S3 Backend (integration target) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py` | Read |
| HTTP Transport (integration target) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/asana_http.py` | Read |
| Config (modification target) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Read |
| Cache Errors (DegradedModeMixin) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/errors.py` | Read |
| Error Classification Mixin | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/error_classification.py` | Read |
| Exception Audit Spike | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-002-exception-audit.md` | Read |
| Architectural Opportunities | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/architectural-opportunities.md` | Read |
| C1 TDD (dependency) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-exception-hierarchy.md` | Read |
| A1 TDD (sibling) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cache-invalidation-pipeline.md` | Read |
