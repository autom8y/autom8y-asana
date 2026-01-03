# Integration Map: autom8y-telemetry

**Assessment ID**: INTMAP-autom8y-telemetry
**Date**: 2025-12-31
**Author**: Integration Researcher (rnd-pack)
**Status**: COMPLETE
**Upstream**: SCOUT-autom8y-telemetry (Technology Scout)
**Downstream**: Prototype Engineer

---

## Executive Summary

This integration map analyzes the extraction of transport layer primitives from autom8_asana for reuse in autom8y-telemetry. The analysis reveals **4 extractable components** with varying degrees of coupling to autom8_asana internals. The recommended approach is a **phased extraction** with Protocol-based abstractions to enable transparent replacement.

**Key findings:**

| Component | Lines | Hard Dependencies | Extraction Complexity |
|-----------|-------|-------------------|----------------------|
| TokenBucketRateLimiter | 116 | 1 (ConfigurationError) | Low |
| RetryHandler | 91 | 1 (RetryConfig) | Low |
| CircuitBreaker | 226 | 2 (Config + Exception) | Medium |
| AsyncHTTPClient | 562 | 6 (Asana-specific) | High |

**Estimated total effort**: 4-5 weeks (medium confidence)

---

## 1. Extraction Analysis

### 1.1 Transport Layer Components

The transport layer (`src/autom8_asana/transport/`) contains 5 modules:

```
transport/
  __init__.py          # Public exports
  http.py              # AsyncHTTPClient - main orchestrator (562 lines)
  circuit_breaker.py   # CircuitBreaker state machine (226 lines)
  rate_limiter.py      # TokenBucketRateLimiter (116 lines)
  retry.py             # RetryHandler with backoff (91 lines)
  sync.py              # sync_wrapper utility (69 lines)
```

### 1.2 Hard Dependencies Analysis

#### TokenBucketRateLimiter
**File**: `src/autom8_asana/transport/rate_limiter.py`
**Coupling**: **LOW**

| Import | Type | Extractable? |
|--------|------|--------------|
| `ConfigurationError` | Exception | Yes - generic error |
| `LogProvider` (TYPE_CHECKING) | Protocol | Yes - already abstract |

**Asana-specific code**: Default values (1500 requests/60s) are Asana limits but parameterized.

**Verdict**: Fully extractable with minimal changes.

#### RetryHandler
**File**: `src/autom8_asana/transport/retry.py`
**Coupling**: **LOW**

| Import | Type | Extractable? |
|--------|------|--------------|
| `RetryConfig` (TYPE_CHECKING) | Dataclass | Yes - can define protocol |
| `LogProvider` (TYPE_CHECKING) | Protocol | Yes - already abstract |

**Asana-specific code**: None. Generic exponential backoff implementation.

**Verdict**: Fully extractable. RetryConfig protocol needed.

#### CircuitBreaker
**File**: `src/autom8_asana/transport/circuit_breaker.py`
**Coupling**: **MEDIUM**

| Import | Type | Extractable? |
|--------|------|--------------|
| `CircuitBreakerConfig` (TYPE_CHECKING) | Dataclass | Yes - can define protocol |
| `LogProvider` (TYPE_CHECKING) | Protocol | Yes - already abstract |
| `CircuitBreakerOpenError` | Exception | Needs abstraction |

**Asana-specific code**: None. Per ADR-0048, generic pattern.

**Verdict**: Extractable with exception abstraction.

#### AsyncHTTPClient
**File**: `src/autom8_asana/transport/http.py`
**Coupling**: **HIGH**

| Import | Type | Extractable? |
|--------|------|--------------|
| `AsanaConfig` (TYPE_CHECKING) | Dataclass | Needs protocol |
| `AuthProvider` (TYPE_CHECKING) | Protocol | Already abstract |
| `LogProvider` (TYPE_CHECKING) | Protocol | Already abstract |
| `AsanaError` | Exception | Asana-specific |
| `RateLimitError` | Exception | Asana-specific |
| `ServerError` | Exception | Asana-specific |
| `TimeoutError` | Exception | Asana-specific |
| `CircuitBreaker` | Class | Extracting |
| `TokenBucketRateLimiter` | Class | Extracting |
| `RetryHandler` | Class | Extracting |

**Asana-specific code**:
1. `{"data": ...}` response unwrapping (lines 229-232)
2. Error parsing via `AsanaError.from_response()` (line 185)
3. Retry-After header handling specific to Asana (lines 188-194)
4. Asana-specific exception hierarchy

**Verdict**: Requires significant refactoring. Create TelemetryHTTPClient base class, leave Asana-specific behaviors in AsyncHTTPClient as subclass.

### 1.3 Parameterization Requirements

To make components generic, the following need parameterization:

| Component | Parameter | Current | Target |
|-----------|-----------|---------|--------|
| RateLimiter | Default rate | 1500/60s (Asana) | Configurable |
| RetryHandler | Retryable codes | {429, 503, 504} | Configurable set |
| CircuitBreaker | Failure threshold | 5 | Configurable |
| HTTPClient | Response parser | `{"data": ...}` | Hook/Strategy |
| HTTPClient | Error mapper | AsanaError.from_response | Hook/Strategy |

### 1.4 Generalizable vs. Asana-Specific Patterns

**Generalizable (extract to autom8y-http)**:
- Token bucket rate limiting algorithm
- Exponential backoff with jitter
- Circuit breaker state machine (CLOSED/OPEN/HALF_OPEN)
- Connection pooling configuration
- Timeout configuration
- Concurrency semaphores (read/write split)
- Lazy client initialization with double-checked locking

**Asana-Specific (keep in autom8_asana)**:
- `{"data": ...}` response unwrapping
- `AsanaError.from_response()` error parsing
- Asana exception hierarchy
- Bearer token authorization header format
- Retry-After header handling for 429s (generic pattern but with Asana exceptions)

---

## 2. Protocol Definitions

### 2.1 RateLimiter Protocol

```python
from typing import Protocol, Any

class RateLimiterProtocol(Protocol):
    """Protocol for rate limiting implementations."""

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire.
        """
        ...

    @property
    def available_tokens(self) -> float:
        """Current available tokens (approximate)."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Return rate limiter statistics for monitoring.

        Returns:
            Dictionary with available_tokens, max_tokens,
            refill_rate, utilization.
        """
        ...
```

### 2.2 RetryPolicy Protocol

```python
from typing import Protocol

class RetryPolicyProtocol(Protocol):
    """Protocol for retry decision logic."""

    def should_retry(self, status_code: int, attempt: int) -> bool:
        """Determine if request should be retried.

        Args:
            status_code: HTTP status code received.
            attempt: Current attempt number (0-indexed).

        Returns:
            True if should retry, False otherwise.
        """
        ...

    def get_delay(self, attempt: int, retry_after: int | None = None) -> float:
        """Calculate delay before next retry.

        Args:
            attempt: Current attempt number (0-indexed).
            retry_after: Server-provided Retry-After value.

        Returns:
            Delay in seconds.
        """
        ...

    async def wait(self, attempt: int, retry_after: int | None = None) -> None:
        """Wait before retry.

        Args:
            attempt: Current attempt number.
            retry_after: Optional Retry-After header value.
        """
        ...
```

### 2.3 CircuitBreaker Protocol

```python
from typing import Protocol
from enum import Enum

class CircuitStateEnum(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerProtocol(Protocol):
    """Protocol for circuit breaker implementations."""

    @property
    def state(self) -> CircuitStateEnum:
        """Current circuit state."""
        ...

    @property
    def enabled(self) -> bool:
        """Whether circuit breaker is active."""
        ...

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        ...

    async def check(self) -> None:
        """Pre-request guard.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
        """
        ...

    async def record_success(self) -> None:
        """Record successful request."""
        ...

    async def record_failure(self, error: Exception) -> None:
        """Record failed request."""
        ...
```

### 2.4 TelemetryHook Protocol

```python
from typing import Protocol

class TelemetryHookProtocol(Protocol):
    """Protocol for telemetry/observability integration.

    Extends existing ObservabilityHook with OTel-specific methods.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """Called before HTTP request is sent."""
        ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """Called after HTTP request completes."""
        ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        """Called when HTTP request fails."""
        ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """Called when rate limit is received."""
        ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """Called when circuit breaker state changes."""
        ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        """Called before retry attempt."""
        ...

    # OTel-specific additions
    def inject_trace_context(self, headers: dict[str, str]) -> None:
        """Inject W3C Trace Context into outgoing headers."""
        ...

    def extract_trace_context(self, headers: dict[str, str]) -> None:
        """Extract W3C Trace Context from incoming headers."""
        ...
```

### 2.5 HTTPClientConfig Protocol

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass(frozen=True)
class TimeoutConfig:
    connect: float = 5.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 10.0

@dataclass(frozen=True)
class ConnectionPoolConfig:
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0

@dataclass(frozen=True)
class ConcurrencyConfig:
    read_limit: int = 50
    write_limit: int = 15

class HTTPClientConfigProtocol(Protocol):
    """Protocol for HTTP client configuration."""

    @property
    def base_url(self) -> str: ...

    @property
    def timeout(self) -> TimeoutConfig: ...

    @property
    def connection_pool(self) -> ConnectionPoolConfig: ...

    @property
    def concurrency(self) -> ConcurrencyConfig: ...
```

---

## 3. Dependency Graph

### 3.1 Current Import Relationships

```
                         autom8_asana
                              |
        +---------------------+---------------------+
        |                     |                     |
    exceptions.py         config.py           protocols/
        |                     |                     |
        v                     v                     v
  +----------+        +------------+         +----------+
  |AsanaError|        |AsanaConfig |         |LogProvider|
  |RateLimit |        |RetryConfig |         |AuthProvider|
  |ServerErr |        |CircuitBrkr |         +----------+
  +----------+        +------------+
        |                     |
        +----------+----------+
                   |
                   v
            transport/
                   |
     +-------------+-------------+
     |             |             |
     v             v             v
rate_limiter  circuit_breaker  retry
     |             |             |
     +-------------+-------------+
                   |
                   v
              http.py
                   |
                   v
           AsyncHTTPClient
                   |
     +-------------+-------------+
     |             |             |
     v             v             v
client.py    data/client.py   clients/*
```

### 3.2 Proposed Post-Extraction Structure

```
autom8y-http (new package)
    |
    +-- protocols/
    |       rate_limiter.py    # RateLimiterProtocol
    |       retry.py           # RetryPolicyProtocol
    |       circuit_breaker.py # CircuitBreakerProtocol
    |       telemetry.py       # TelemetryHookProtocol
    |
    +-- implementations/
    |       rate_limiter.py    # TokenBucketRateLimiter
    |       retry.py           # RetryHandler
    |       circuit_breaker.py # CircuitBreaker
    |
    +-- client.py              # TelemetryHTTPClient (base)
    +-- exceptions.py          # Generic transport exceptions

autom8y-telemetry (new package)
    |
    +-- config.py              # Unified OTel configuration
    +-- hooks.py               # OTelTelemetryHook implementation
    +-- logging/
    |       structlog.py       # structlog + OTel integration
    +-- tracing/
            setup.py           # OTel SDK initialization

autom8_asana (updated)
    |
    +-- transport/
    |       http.py            # AsyncHTTPClient extends TelemetryHTTPClient
    |                          # Adds Asana-specific behaviors
    |
    +-- Imports from autom8y-http for protocols
    +-- Imports from autom8y-telemetry for observability
```

### 3.3 Breaking Changes Analysis

| Change | Consumers Affected | Mitigation |
|--------|-------------------|------------|
| Import path change | Direct transport imports | Re-export from autom8_asana.transport |
| Config class location | AsanaConfig users | Keep AsanaConfig, compose with protocols |
| Exception location | Exception handlers | Re-export CircuitBreakerOpenError |

**Transparent replacement possible**: Yes, via re-exports in `autom8_asana.transport.__init__.py`

---

## 4. Collector Architecture

### 4.1 Deployment Pattern Evaluation

| Pattern | Description | Pros | Cons |
|---------|-------------|------|------|
| **Sidecar** | Collector per pod | Isolated, simple | Resource overhead |
| **Gateway** | Centralized cluster | Efficient, central config | Single point of failure |
| **Agent** | Per-node daemon | Efficient for k8s | Not ideal for ECS |

### 4.2 Recommendation: Gateway Pattern for autom8 Satellites

For AWS ECS/Fargate deployment (autom8 architecture):

```
+------------------+     +------------------+     +------------------+
|  autom8_asana    |     |  autom8_data     |     |  autom8y-auth    |
|  (ECS Service)   |     |  (ECS Service)   |     |  (ECS Service)   |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         |  OTLP/gRPC            |  OTLP/gRPC             |
         |  :4317                |  :4317                  |
         v                        v                        v
+-------------------------------------------------------------------------+
|                     OTel Collector Gateway                               |
|                     (ECS Service, 2+ tasks)                              |
|  +------------------+  +------------------+  +------------------+        |
|  | Traces Receiver  |  | Metrics Receiver |  | Logs Receiver    |        |
|  +--------+---------+  +--------+---------+  +--------+---------+        |
|           |                     |                     |                  |
|           v                     v                     v                  |
|  +----------------------------------------------------------+           |
|  |                    Batch Processor                        |           |
|  |                    (200 spans/batch)                      |           |
|  +----------------------------------------------------------+           |
|           |                     |                     |                  |
|           v                     v                     v                  |
|  +------------------+  +------------------+  +------------------+        |
|  | Tempo Exporter   |  | Prometheus Exp   |  | CloudWatch Exp   |        |
|  +--------+---------+  +--------+---------+  +--------+---------+        |
+-------------------------------------------------------------------------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
|  Grafana Tempo   |     |  Prometheus      |     |  CloudWatch      |
|  (Trace Backend) |     |  (Metrics)       |     |  (Logs)          |
+------------------+     +------------------+     +------------------+
```

**Rationale**:
1. **ECS native**: Gateway runs as ECS service, no sidecar overhead in Fargate
2. **Central sampling**: Apply head/tail sampling at gateway, not per-service
3. **Multi-backend**: Fan-out to Tempo, Prometheus, CloudWatch from single collector
4. **Cost efficiency**: Batch processing reduces egress costs

### 4.3 Configuration Approach

**Environment-based configuration** (12-factor app):

```bash
# Service configuration (set in ECS task definition)
OTEL_SERVICE_NAME=autom8_asana
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.internal:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling in production
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production,service.namespace=autom8
```

**Collector configuration** (mounted as ConfigMap or ECS volume):

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    send_batch_size: 200
    timeout: 5s

  # Tail-based sampling for traces
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow_requests
        type: latency
        latency: {threshold_ms: 1000}
      - name: probabilistic
        type: probabilistic
        probabilistic: {sampling_percentage: 10}

exporters:
  otlp/tempo:
    endpoint: tempo.internal:4317
    tls:
      insecure: true

  prometheus:
    endpoint: 0.0.0.0:8889

  awscloudwatchlogs:
    log_group_name: /autom8/otel-logs
    log_stream_name: collector

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, tail_sampling]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [awscloudwatchlogs]
```

---

## 5. Migration Plan

### Phase 1: Extract Transport Primitives (Week 1-2)

**Scope**: Create autom8y-http package with extracted components

| Task | Effort | Risk |
|------|--------|------|
| Create autom8y-http package structure | 2h | Low |
| Define Protocol interfaces | 4h | Low |
| Extract TokenBucketRateLimiter | 4h | Low |
| Extract RetryHandler | 4h | Low |
| Extract CircuitBreaker + exceptions | 8h | Medium |
| Write unit tests for extracted components | 8h | Low |
| **Phase 1 Total** | **30h (~1 week)** | **Low-Medium** |

**Rollback Point**: autom8_asana still contains original code, no external dependency

### Phase 2: Add OTel Instrumentation (Week 2-3)

**Scope**: Create autom8y-telemetry package with OTel integration

| Task | Effort | Risk |
|------|--------|------|
| Create autom8y-telemetry package structure | 2h | Low |
| Implement OTel SDK initialization | 8h | Medium |
| Implement TelemetryHook with OTel | 12h | Medium |
| Add structlog + trace context processor | 8h | Low |
| Create TelemetryHTTPClient base class | 16h | Medium |
| Write integration tests | 8h | Medium |
| **Phase 2 Total** | **54h (~1.5 weeks)** | **Medium** |

**Rollback Point**: autom8_asana can still use internal transport, autom8y-telemetry optional

### Phase 3: Update autom8_asana Imports (Week 3-4)

**Scope**: Wire autom8_asana to use autom8y-http and autom8y-telemetry

| Task | Effort | Risk |
|------|--------|------|
| Add autom8y-http dependency | 2h | Low |
| Update AsyncHTTPClient to extend TelemetryHTTPClient | 16h | Medium |
| Maintain backward-compatible re-exports | 4h | Low |
| Update DataServiceClient to use shared components | 8h | Low |
| Integration testing with Asana API | 8h | Medium |
| Performance benchmarking | 8h | Low |
| **Phase 3 Total** | **46h (~1.2 weeks)** | **Medium** |

**Rollback Point**: Can revert to internal transport via import path change

### Phase 4: autom8_data Client Update (Week 4-5)

**Scope**: Update autom8_data to use autom8y-telemetry

| Task | Effort | Risk |
|------|--------|------|
| Add autom8y-http + autom8y-telemetry dependencies | 2h | Low |
| Configure OTel SDK in autom8_data | 4h | Low |
| Verify trace propagation across services | 8h | Medium |
| Deploy OTel Collector gateway | 8h | Medium |
| End-to-end distributed tracing test | 8h | Medium |
| **Phase 4 Total** | **30h (~1 week)** | **Medium** |

**Rollback Point**: autom8_data can disable OTel via environment variable

### Total Effort Summary

| Phase | Duration | Effort | Confidence |
|-------|----------|--------|------------|
| Phase 1: Extract | 1 week | 30h | High (90%) |
| Phase 2: Instrument | 1.5 weeks | 54h | Medium (75%) |
| Phase 3: Integrate autom8_asana | 1.2 weeks | 46h | Medium (70%) |
| Phase 4: Integrate autom8_data | 1 week | 30h | Medium (75%) |
| **Total** | **4-5 weeks** | **160h** | **Medium (70%)** |

**Confidence Assumptions**:
- Team familiarity with OTel: Medium (learning curve factored in)
- No blocking issues with httpx instrumentation
- Collector deployment in existing AWS infrastructure
- No major refactoring surprises in autom8_asana transport layer

---

## 6. Risk Assessment

### 6.1 Breaking Changes

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import path changes break consumers | Medium | High | Re-export from original paths |
| Protocol incompatibility | Low | Medium | Protocol tests, type checking |
| Performance regression | Low | High | Benchmark before/after, sampling |
| OTel version conflicts | Medium | Medium | Pin versions, single source of truth |

### 6.2 Hidden Dependencies

**Discovered during analysis**:

1. **Implicit config coupling**: `AsyncHTTPClient` directly accesses `config.rate_limit.max_requests` - needs protocol abstraction

2. **Exception hierarchy**: `AsanaError.from_response()` factory method tightly coupled to Asana error format - keep in autom8_asana

3. **Pagination logic**: `get_paginated()` method has Asana-specific `{"data": [], "next_page": {"offset": ...}}` format - keep in autom8_asana

4. **Multipart encoding**: `post_multipart()` uses Asana-specific attachment handling - keep in autom8_asana

5. **DataServiceClient duplication**: `clients/data/client.py` re-implements rate limiting, circuit breaker, retry logic separately - consolidate in Phase 3

### 6.3 Mitigation Strategies

| Risk | Strategy |
|------|----------|
| Breaking changes | Feature flag for new transport, gradual rollout |
| Performance regression | Shadow mode: run both transports, compare metrics |
| OTel overhead | Sampling configuration, disable in dev |
| Learning curve | Wrapper hides OTel complexity from service code |

---

## 7. POC Scope and Success Criteria

### 7.1 POC Scope

**In Scope**:
1. Extract TokenBucketRateLimiter to autom8y-http
2. Implement TelemetryHTTPClient with OTel spans
3. Wire single endpoint in autom8_asana to use extracted transport
4. Verify trace appears in local Jaeger/Tempo

**Out of Scope for POC**:
- Full autom8_asana migration
- Production collector deployment
- structlog integration
- Metrics instrumentation

### 7.2 Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Component extraction | TokenBucketRateLimiter passes original test suite |
| Trace generation | Single request generates valid OTel span |
| Protocol compliance | Type checker (mypy) passes with protocols |
| No regression | Benchmark shows <5% latency increase |
| Backward compat | Existing autom8_asana tests pass |

### 7.3 POC Estimated Effort

**Time-boxed**: 3 days (24 hours)

| Day | Task |
|-----|------|
| Day 1 | Create autom8y-http, extract RateLimiter, write tests |
| Day 2 | Add OTel span generation, create TelemetryHTTPClient |
| Day 3 | Wire to single autom8_asana endpoint, verify traces |

---

## 8. Artifact Verification

| Artifact | Path | Verified |
|----------|------|----------|
| Scout Assessment | docs/rnd/SCOUT-autom8y-telemetry.md | Read via Read tool |
| Transport HTTP | src/autom8_asana/transport/http.py | Read via Read tool |
| Circuit Breaker | src/autom8_asana/transport/circuit_breaker.py | Read via Read tool |
| Retry Handler | src/autom8_asana/transport/retry.py | Read via Read tool |
| Rate Limiter | src/autom8_asana/transport/rate_limiter.py | Read via Read tool |
| Exceptions | src/autom8_asana/exceptions.py | Read via Read tool |
| Config | src/autom8_asana/config.py | Read via Read tool |
| Protocols (Log) | src/autom8_asana/protocols/log.py | Read via Read tool |
| Protocols (Auth) | src/autom8_asana/protocols/auth.py | Read via Read tool |
| Protocols (Obs) | src/autom8_asana/protocols/observability.py | Read via Read tool |
| Data Client | src/autom8_asana/clients/data/client.py | Read via Read tool |
| Data Config | src/autom8_asana/clients/data/config.py | Read via Read tool |
| Default Log | src/autom8_asana/_defaults/log.py | Read via Read tool |

---

## 9. Next Phase: Prototype Engineer

### Handoff Deliverables

1. **Protocol definitions** (Section 2): Copy to autom8y-http/protocols/
2. **Extraction checklist**: TokenBucketRateLimiter first, then RetryHandler, then CircuitBreaker
3. **POC scope** (Section 7): 3-day time-box, single endpoint validation
4. **Success criteria**: Trace in Jaeger, <5% latency, tests pass

### Questions to Answer in Prototype

1. Does httpx instrumentation conflict with custom transport middleware?
2. What's the actual latency overhead of OTel span generation?
3. Can we use contextvars for trace propagation without explicit injection?
4. Is structlog's OTel handler stable enough for production?

---

## Appendix A: Code Snippets

### A.1 Current Rate Limiter Instantiation

```python
# src/autom8_asana/transport/http.py:52-57
self._rate_limiter = TokenBucketRateLimiter(
    max_tokens=config.rate_limit.max_requests,
    refill_period=config.rate_limit.window_seconds,
    logger=logger,
)
```

### A.2 Current Circuit Breaker Hook Pattern

```python
# src/autom8_asana/transport/circuit_breaker.py:81-89
def on_state_change(
    self, callback: Callable[[CircuitState, CircuitState], Any]
) -> None:
    """Register callback for state transitions."""
    self._on_state_change_hooks.append(callback)
```

This hook pattern maps directly to TelemetryHookProtocol.on_circuit_breaker_state_change().

### A.3 Proposed TelemetryHTTPClient Base

```python
# autom8y-http/client.py (proposed)
class TelemetryHTTPClient:
    """Base HTTP client with telemetry integration."""

    def __init__(
        self,
        config: HTTPClientConfigProtocol,
        rate_limiter: RateLimiterProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
        retry_policy: RetryPolicyProtocol | None = None,
        telemetry_hook: TelemetryHookProtocol | None = None,
        logger: LogProvider | None = None,
    ) -> None:
        self._config = config
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._retry_policy = retry_policy
        self._telemetry_hook = telemetry_hook
        self._logger = logger
        # ... client setup ...

    async def request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Make HTTP request with telemetry."""
        # 1. Circuit breaker check
        # 2. Inject trace context
        # 3. Acquire rate limiter
        # 4. Execute with retry
        # 5. Record metrics
        # Return raw response (subclass handles parsing)
        ...
```

Subclass in autom8_asana:

```python
# src/autom8_asana/transport/http.py (proposed)
class AsyncHTTPClient(TelemetryHTTPClient):
    """Asana-specific HTTP client."""

    async def request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        response = await super().request(method, path, **kwargs)

        # Asana-specific: unwrap {"data": ...} response
        result = response.json()
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return result
```
