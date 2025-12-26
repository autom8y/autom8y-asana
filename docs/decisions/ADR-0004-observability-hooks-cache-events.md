# ADR-0004: Observability Hooks and Cache Events

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0023 (Observability Strategy), ADR-0085 (ObservabilityHook Protocol)
- **Related**: reference/OBSERVABILITY.md, ADR-0001 (Protocol Extensibility), ADR-0003 (Correlation IDs)

## Context

The SDK requires extensible observability for operational monitoring without coupling to specific metrics infrastructure. Teams need visibility into:
- Cache performance (hit rates, latency, overflow events)
- API request metrics (latency, status codes, failures)
- Resilience events (rate limits, circuit breaker state, retry attempts)
- Request lifecycle for custom telemetry integration (Prometheus, DataDog, OpenTelemetry)

Key constraints:
- SDK must be infrastructure-agnostic (consumers choose CloudWatch, DataDog, Prometheus, etc.)
- Cannot add dependencies on specific metrics libraries
- Must work with existing `LogProvider` protocol pattern (ADR-0001)
- Zero overhead when observability features not used

The SDK already uses `typing.Protocol` for dependency injection, establishing a pattern to follow.

## Decision

**Extend `LogProvider` protocol with `log_cache_event()` method for cache observability and define `ObservabilityHook` protocol for request lifecycle events. Provide helper classes (`CacheMetrics`) for common aggregations. Consumers register callbacks to route events to their preferred destination.**

### Cache Event Protocol Extension

Extend existing `LogProvider` with cache event support:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, Any

@dataclass
class CacheEvent:
    """Structured cache event for observability."""
    event_type: str  # hit, miss, write, evict, expire, error, overflow_skip, degrade, restore
    key: str
    entry_type: str | None
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class LogProvider(Protocol):
    """Extended logging protocol with cache event support."""

    # Original methods (unchanged)
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    # New cache event method
    def log_cache_event(self, event: CacheEvent) -> None:
        """Log structured cache event.

        Default implementation formats as info log.
        Override to send to metrics system.
        """
        self.info(
            "cache.%s key=%s type=%s latency=%.2fms",
            event.event_type,
            event.key,
            event.entry_type,
            event.latency_ms,
        )
```

### ObservabilityHook Protocol

Define protocol for request lifecycle and resilience events:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ObservabilityHook(Protocol):
    """Protocol for observability integration.

    Implement this protocol to receive SDK operation events for metrics,
    tracing, or logging integration. All methods are async to support
    non-blocking telemetry backends.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """Called before an HTTP request is made."""
        ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """Called after an HTTP request completes."""
        ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        """Called when an HTTP request fails with an exception."""
        ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """Called when rate limit (429) is encountered."""
        ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """Called when circuit breaker changes state."""
        ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        """Called before a retry attempt."""
        ...
```

### Null Implementation (Zero Overhead)

```python
class NullObservabilityHook:
    """No-op observability hook (default).

    All methods are effectively zero-cost since they return immediately.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        pass

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        pass

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        pass

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        pass

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        pass

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        pass
```

### CacheMetrics Aggregator

Helper class for common cache metrics calculations:

```python
from threading import Lock
from typing import Callable

class CacheMetrics:
    """Thread-safe cache metrics aggregator.

    Collects cache events and provides aggregated statistics.
    Supports callback registration for real-time event streaming.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._writes = 0
        self._evictions = 0
        self._errors = 0
        self._total_latency_ms = 0.0
        self._operation_count = 0
        self._overflow_skips: dict[str, int] = {}
        self._callbacks: list[Callable[[CacheEvent], None]] = []
        self._degraded = False

    def record_event(self, event: CacheEvent) -> None:
        """Record a cache event and notify callbacks."""
        with self._lock:
            self._operation_count += 1
            self._total_latency_ms += event.latency_ms

            match event.event_type:
                case "hit":
                    self._hits += 1
                case "miss":
                    self._misses += 1
                case "write":
                    self._writes += 1
                case "evict" | "expire":
                    self._evictions += 1
                case "error":
                    self._errors += 1
                case "overflow_skip":
                    entry_type = event.entry_type or "unknown"
                    self._overflow_skips[entry_type] = (
                        self._overflow_skips.get(entry_type, 0) + 1
                    )
                case "degrade":
                    self._degraded = True
                case "restore":
                    self._degraded = False

        # Notify callbacks outside lock
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass  # Don't let callback errors affect operation

    def on_event(self, callback: Callable[[CacheEvent], None]) -> None:
        """Register callback for cache events."""
        self._callbacks.append(callback)

    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        with self._lock:
            total = self._hits + self._misses
            return (self._hits / total * 100) if total > 0 else 0.0

    def avg_latency_ms(self) -> float:
        """Calculate average operation latency."""
        with self._lock:
            return (
                self._total_latency_ms / self._operation_count
                if self._operation_count > 0
                else 0.0
            )

    def get_stats(self) -> dict[str, Any]:
        """Get all statistics as a dictionary."""
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "writes": self._writes,
                "evictions": self._evictions,
                "errors": self._errors,
                "hit_rate": self.hit_rate(),
                "avg_latency_ms": self.avg_latency_ms(),
                "overflow_skips": dict(self._overflow_skips),
                "degraded": self._degraded,
            }
```

### Client Integration

```python
class AsanaClient:
    def __init__(
        self,
        *,
        auth: AuthProvider,
        observability_hook: ObservabilityHook | None = None,
        log_provider: LogProvider | None = None,
    ) -> None:
        self._observability = observability_hook or NullObservabilityHook()
        self._log = log_provider or DefaultLogProvider()

    @property
    def observability(self) -> ObservabilityHook:
        """Observability hook for metrics and tracing."""
        return self._observability
```

## Rationale

### Why Extend LogProvider for Cache Events?

Per ADR-0001, the SDK uses `typing.Protocol` for extensibility. Extending LogProvider:
- Maintains single logging protocol (no new protocol to manage)
- Natural fit (cache events are log-like structured data)
- Existing consumers already inject LogProvider
- Default implementation provides zero-overhead logging

### Why Separate ObservabilityHook Protocol?

Request lifecycle events differ from cache events:
- Cache events: High volume, storage-focused, primarily for logging/metrics
- Request events: Lower volume, network-focused, need async support for telemetry backends
- Separation allows consumers to implement only what they need

### Why Protocol over Abstract Base Class?

| Aspect | Protocol | ABC |
|--------|----------|-----|
| Structural typing | Yes (duck-typing) | No (inheritance required) |
| SDK pattern | Matches LogProvider, CacheProvider | Would break consistency |
| Flexibility | Any object with matching methods | Must inherit from ABC |
| Runtime checking | Optional (`@runtime_checkable`) | Always enforced |

Protocol chosen for consistency with existing SDK patterns and duck-typing support.

### Why Async Methods for ObservabilityHook?

1. **Non-blocking telemetry**: Metrics backends (HTTP, gRPC) benefit from async I/O
2. **SDK consistency**: SDK is async-first per design
3. **Forward compatibility**: Easy to add async-only features later
4. **Sync compatibility**: Sync consumers can wrap or ignore async aspect

### Why Null Object Pattern?

Benefits:
- **No conditionals**: Call hooks unconditionally; null handles no-op case
- **Type safety**: `self._observability` is always non-None
- **Performance**: Method call overhead is negligible compared to HTTP requests
- **Clean API**: No `if self._observability:` checks throughout codebase

### Why Callbacks Instead of Direct Metrics Integration?

SDK agnostic approach:
- Different teams use CloudWatch, DataDog, Prometheus, StatsD, OpenTelemetry
- SDK cannot depend on any specific metrics library (violates dependency constraints)
- Callbacks let consumers route events to any destination
- CacheMetrics helper provides common aggregations without forcing implementation

### Why Include Correlation IDs?

Links cache and request events to originating operations:
- Trace single operation through all activity layers
- Debug slow requests by correlating cache hits with API calls
- Integrate with external tracing systems by logging SDK correlation IDs

## Alternatives Considered

### Alternative 1: Direct CloudWatch Integration
- **Description**: SDK emits metrics directly to CloudWatch via boto3
- **Pros**: No consumer code needed, consistent format, easy for AWS users
- **Cons**: AWS dependency, doesn't work for non-AWS users, requires credentials in SDK
- **Why not chosen**: SDK must be infrastructure-agnostic. Protocol + callbacks supports all backends.

### Alternative 2: OpenTelemetry Integration
- **Description**: Use OpenTelemetry SDK for metrics and tracing
- **Pros**: Industry standard, supports multiple backends, rich ecosystem
- **Cons**: Heavy dependency, requires OTel collector, learning curve, overkill for SDK scope
- **Why not chosen**: Too heavy. Consumers can feed OTel using callbacks if desired.

### Alternative 3: Prometheus Metrics Endpoint
- **Description**: SDK exposes `/metrics` endpoint in Prometheus format
- **Pros**: Standard format, easy to scrape, works with Grafana
- **Cons**: Requires HTTP server in SDK (inappropriate for library), push model doesn't fit Prometheus
- **Why not chosen**: SDK is a library, not a service. Cannot run HTTP server.

### Alternative 4: StatsD Protocol
- **Description**: Emit metrics via StatsD UDP protocol
- **Pros**: Simple UDP packets, low overhead, wide agent support
- **Cons**: Requires StatsD agent, UDP packet loss, another dependency, only counters/gauges
- **Why not chosen**: Adds infrastructure requirement. Callbacks are more flexible.

### Alternative 5: Log-Only Approach
- **Description**: Only emit structured logs, no metrics aggregation
- **Pros**: Simple, works with any log infrastructure, no new types
- **Cons**: No in-SDK aggregation (hit rate, etc.), consumers parse logs for metrics
- **Why not chosen**: CacheMetrics provides valuable aggregations consumers would need anyway.

### Alternative 6: Callback Dict Pattern
- **Description**: Dict of `{event_name: callable}` passed to client
- **Pros**: Simple, no class needed, familiar pattern
- **Cons**: No type safety, no IDE completion, easy to misspell event names
- **Why not chosen**: Protocol provides better developer experience with type checking.

### Alternative 7: Event Emitter Pattern
- **Description**: `client.events.on('request_start', handler)` like Node.js
- **Pros**: Familiar pattern, supports multiple handlers
- **Cons**: Dynamic registration, no type safety, magic strings
- **Why not chosen**: Protocol provides compile-time type checking.

## Consequences

### Positive
- **Infrastructure agnostic**: Works with CloudWatch, DataDog, Prometheus, OpenTelemetry, custom systems
- **Low coupling**: SDK has zero dependencies on metrics libraries
- **Flexible consumption**: Consumers choose callbacks, aggregation, logs, or all three
- **Rich events**: All cache and request operations observable with structured metadata
- **Thread-safe**: CacheMetrics handles concurrent event recording
- **Correlation support**: Events link to correlation IDs for request tracing
- **Zero overhead**: NullObservabilityHook and default LogProvider are effectively no-op
- **Type safety**: Protocol ensures correct method signatures at compile time
- **Consistent pattern**: Matches existing SDK protocol-based extensibility

### Negative
- **Consumer work required**: Must implement callbacks/hooks and route to destination
- **No out-of-box dashboards**: Consumers build their own monitoring
- **Callback overhead**: Each event invokes callbacks (minimal compared to HTTP)
- **Protocol extension**: LogProvider grows by one method
- **Async requirement**: Sync-only consumers must wrap hooks in async adapters
- **Verbosity**: 6 methods to implement for full ObservabilityHook support

### Neutral
- **CacheEvent dataclass**: New type for event structure
- **CacheMetrics optional**: Consumers can use, ignore, or build custom aggregator
- **Default logs to info**: Structured log message emitted for each event if using DefaultLogProvider
- **Optional integration**: Hooks are opt-in; existing code unaffected

## Compliance

How we ensure this decision is followed:

**Code Review Checklist**:
- All cache operations emit events (hit, miss, write, evict, expire, error)
- Events include `latency_ms` measurement
- Correlation IDs propagated to events when available
- Transport layer calls `ObservabilityHook` at request start/end/error
- Rate limiter calls `on_rate_limit` hook
- Circuit breaker calls `on_circuit_breaker_state_change` hook
- Retry handler calls `on_retry` hook

**Testing Requirements**:
- Unit tests verify event emission for all cache operations
- Unit tests verify CacheMetrics calculations (hit_rate, avg_latency_ms)
- Unit tests verify callback invocation with correct arguments
- Integration tests verify hooks called at correct lifecycle points
- Integration tests verify correlation ID propagation through events

**Event Types Reference**:

| Event Type | Description | Emitted By | Metadata |
|------------|-------------|------------|----------|
| `hit` | Cache read found data | get_versioned | key, entry_type, latency_ms |
| `miss` | Cache read found nothing | get_versioned | key, entry_type, latency_ms |
| `write` | Cache write completed | set_versioned | key, entry_type, latency_ms |
| `evict` | Explicit invalidation | invalidate/delete | key, entry_type |
| `expire` | TTL-based expiration | get_versioned | key, entry_type |
| `error` | Cache operation failed | all cache ops | key, entry_type, error |
| `overflow_skip` | Write skipped due to overflow | relationship fetch | entry_type, count, threshold |
| `degrade` | Switched to fallback mode | cache provider | reason |
| `restore` | Restored from fallback | cache provider | reason |

**Consumer Integration Examples**:

```python
# Example 1: Route cache events to CloudWatch
class CloudWatchLogProvider(DefaultLogProvider):
    def __init__(self, cloudwatch_client):
        super().__init__()
        self._cw = cloudwatch_client

    def log_cache_event(self, event: CacheEvent) -> None:
        # Send to CloudWatch Metrics
        self._cw.put_metric_data(
            Namespace="Autom8/Cache",
            MetricData=[
                {
                    "MetricName": f"Cache{event.event_type.capitalize()}",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "EntryType", "Value": event.entry_type or "unknown"},
                    ],
                },
                {
                    "MetricName": "CacheLatency",
                    "Value": event.latency_ms,
                    "Unit": "Milliseconds",
                },
            ],
        )
        # Also log as structured message
        super().log_cache_event(event)

# Example 2: Prometheus hook for request metrics
from prometheus_client import Counter, Histogram

class PrometheusHook:
    def __init__(self):
        self.requests = Counter(
            'asana_requests_total',
            'Total requests',
            ['method', 'status']
        )
        self.latency = Histogram(
            'asana_request_duration_seconds',
            'Request latency'
        )

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        pass  # Could start a span here

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        self.requests.labels(method=method, status=str(status)).inc()
        self.latency.observe(duration_ms / 1000)

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        self.requests.labels(method=method, status='error').inc()

    # ... implement other methods as needed
    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        pass

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        pass

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        pass

# Example 3: CacheMetrics aggregation
metrics = CacheMetrics()
metrics.on_event(lambda event: send_to_monitoring(event))

# Later, get aggregated stats
stats = metrics.get_stats()
# {"hits": 150, "misses": 50, "hit_rate": 75.0, "avg_latency_ms": 2.3}

# Example 4: Client initialization
client = AsanaClient(
    auth=BearerAuth(token),
    observability_hook=PrometheusHook(),
    log_provider=CloudWatchLogProvider(cw_client),
)
```
