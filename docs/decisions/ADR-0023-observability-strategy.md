# ADR-0023: Observability Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team, User
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [ADR-0001](ADR-0001-protocol-extensibility.md)

## Context

The intelligent caching layer needs observability to answer questions like:
- What is our cache hit rate?
- How much API call reduction are we achieving?
- Are there latency issues with Redis?
- Which tasks are causing overflow skips?
- When did the cache degrade to no-cache mode?

**Requirements**:
- FR-CACHE-081: Extend `LogProvider` with `log_cache_event()` method
- FR-CACHE-082: Emit events for hit, miss, write, evict, expire
- FR-CACHE-083: Include metadata: key, entry_type, latency_ms
- FR-CACHE-084: Provide `CacheMetrics` aggregation helper
- FR-CACHE-085: Support callback registration for cache events

**Constraints**:
- SDK must be agnostic to metrics destination (CloudWatch, DataDog, Prometheus, etc.)
- Cannot add direct dependencies on specific metrics libraries
- Must work with existing `LogProvider` protocol pattern (ADR-0001)

**User decision**: Consumer callback via LogProvider protocol extension. SDK emits events; consumers route to their destination.

## Decision

**Extend `LogProvider` protocol with `log_cache_event()` method and provide `CacheMetrics` helper class for aggregation. Consumers register callbacks to receive events and route them to their preferred destination.**

### Extended LogProvider Protocol

```python
from typing import Protocol, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CacheEvent:
    """Structured cache event for observability.

    Attributes:
        event_type: Type of event (hit, miss, write, evict, expire, error, degrade, restore)
        key: Cache key involved
        entry_type: Type of cache entry (task, subtasks, etc.)
        latency_ms: Operation latency in milliseconds
        timestamp: When the event occurred
        correlation_id: Request correlation ID for tracing
        metadata: Additional event-specific data
    """
    event_type: str
    key: str
    entry_type: str | None
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LogProvider(Protocol):
    """Extended logging protocol with cache event support.

    The log_cache_event method has a default implementation that
    calls info() with a formatted message. Custom implementations
    can send events to CloudWatch, DataDog, or any metrics system.
    """

    # === Original methods (unchanged) ===
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    # === New cache event method ===
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

### Default Log Provider Extension

```python
class DefaultLogProvider:
    """Default log provider with cache event support."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("autom8_asana")

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    # ... other methods ...

    def log_cache_event(self, event: CacheEvent) -> None:
        """Format cache event as structured log."""
        extra = {
            "event_type": event.event_type,
            "cache_key": event.key,
            "entry_type": event.entry_type,
            "latency_ms": event.latency_ms,
            "correlation_id": event.correlation_id,
            **event.metadata,
        }
        self._logger.info(
            "cache.%s key=%s type=%s latency=%.2fms",
            event.event_type,
            event.key,
            event.entry_type,
            event.latency_ms,
            extra=extra,
        )
```

### CacheMetrics Aggregator

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
        """Register callback for cache events.

        Callbacks receive all cache events in real-time.
        Use for streaming to external metrics systems.
        """
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

    def reset(self) -> None:
        """Reset all counters for new measurement window."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._writes = 0
            self._evictions = 0
            self._errors = 0
            self._total_latency_ms = 0.0
            self._operation_count = 0
            self._overflow_skips.clear()
            # Don't reset _degraded - that's current state
```

### Consumer Integration Example

```python
# Example: Route cache events to CloudWatch
class CloudWatchCacheProvider:
    """autom8's cache provider with CloudWatch metrics."""

    def __init__(self, cloudwatch_client):
        self._cw = cloudwatch_client
        self._redis = RedisCacheProvider(...)
        self._metrics = CacheMetrics()

        # Register callback to send to CloudWatch
        self._metrics.on_event(self._send_to_cloudwatch)

    def _send_to_cloudwatch(self, event: CacheEvent) -> None:
        """Send cache event to CloudWatch."""
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
                    "Dimensions": [
                        {"Name": "EntryType", "Value": event.entry_type or "unknown"},
                    ],
                },
            ],
        )

    def get_versioned(self, key: str, entry_type: EntryType, ...) -> CacheEntry | None:
        """Get with metrics recording."""
        start = time.perf_counter()
        result = self._redis.get_versioned(key, entry_type, ...)
        latency_ms = (time.perf_counter() - start) * 1000

        event = CacheEvent(
            event_type="hit" if result else "miss",
            key=key,
            entry_type=entry_type.value,
            latency_ms=latency_ms,
        )
        self._metrics.record_event(event)

        return result
```

### Event Types

| Event Type | Description | When Emitted |
|------------|-------------|--------------|
| `hit` | Cache read found data | `get_versioned` returns entry |
| `miss` | Cache read found nothing | `get_versioned` returns None |
| `write` | Cache write completed | `set_versioned` succeeds |
| `evict` | Explicit invalidation | `invalidate()` or `delete()` called |
| `expire` | TTL-based expiration | Entry expired during read |
| `error` | Cache operation failed | Redis error, connection timeout |
| `overflow_skip` | Write skipped due to overflow | Entry exceeds threshold |
| `degrade` | Switched to fallback mode | Redis connection lost |
| `restore` | Restored from fallback | Redis connection recovered |

## Rationale

**Why extend LogProvider rather than new protocol?**

Per ADR-0001, we use `typing.Protocol` for extensibility. Extending `LogProvider`:
- Maintains single logging protocol
- Natural fit (cache events are log-like)
- Existing consumers already inject LogProvider
- No new protocol to manage

**Why callbacks instead of direct metrics integration?**

SDK agnostic approach:
- autom8 uses CloudWatch
- Other consumers may use DataDog, Prometheus, StatsD
- SDK shouldn't depend on any specific metrics library
- Callbacks let consumers route to any destination

**Why CacheMetrics helper class?**

Common aggregation logic shouldn't be reimplemented by every consumer:
- Hit rate calculation
- Latency averaging
- Overflow tracking
- Thread-safe counters

Consumers can use CacheMetrics directly or just the callbacks.

**Why include correlation_id?**

Links cache events to originating API requests:
- Trace a request through cache hit/miss
- Debug slow requests
- Correlate with Asana API metrics

## Alternatives Considered

### Alternative 1: Direct CloudWatch Integration

- **Description**: SDK emits metrics directly to CloudWatch via boto3.
- **Pros**:
  - No consumer code needed
  - Consistent metrics format
  - Easy for AWS users
- **Cons**:
  - AWS dependency in SDK
  - Doesn't work for non-AWS consumers
  - Requires AWS credentials in SDK
  - Couples SDK to specific infrastructure
- **Why not chosen**: User explicitly chose consumer callback approach. SDK must be infrastructure-agnostic.

### Alternative 2: OpenTelemetry Integration

- **Description**: Use OpenTelemetry SDK for metrics and tracing.
- **Pros**:
  - Industry standard
  - Supports multiple backends
  - Rich tracing capabilities
  - Growing ecosystem
- **Cons**:
  - Heavy dependency
  - Requires OTel collector setup
  - Learning curve for consumers
  - Overkill for simple cache metrics
- **Why not chosen**: Too heavy for SDK scope. Consumers can use callbacks to feed OTel if desired.

### Alternative 3: Prometheus Metrics Endpoint

- **Description**: SDK exposes /metrics endpoint in Prometheus format.
- **Pros**:
  - Standard Prometheus format
  - Easy to scrape
  - Works with Grafana
- **Cons**:
  - Requires HTTP server in SDK
  - Not appropriate for library (SDK isn't a service)
  - Push model doesn't fit Prometheus
- **Why not chosen**: SDK is a library, not a service. Can't run HTTP server.

### Alternative 4: StatsD Protocol

- **Description**: Emit metrics via StatsD UDP protocol.
- **Pros**:
  - Simple UDP packets
  - Low overhead
  - Wide agent support
- **Cons**:
  - Requires StatsD agent
  - UDP can lose packets
  - Another dependency
  - Only supports counters/gauges
- **Why not chosen**: Adds infrastructure requirement. Callbacks are more flexible.

### Alternative 5: Log-Only Approach

- **Description**: Only emit structured logs, no metrics aggregation.
- **Pros**:
  - Simple implementation
  - Works with any log infrastructure
  - No new types or protocols
- **Cons**:
  - No in-SDK aggregation (hit rate, etc.)
  - Consumers must parse logs for metrics
  - Real-time dashboards harder to build
- **Why not chosen**: Aggregation is valuable. CacheMetrics provides common calculations consumers would need anyway.

## Consequences

### Positive

- **Infrastructure agnostic**: Works with CloudWatch, DataDog, Prometheus, etc.
- **Low coupling**: SDK doesn't depend on any metrics library
- **Flexible consumption**: Callbacks, aggregation, or logs
- **Rich events**: All cache operations observable
- **Thread-safe**: CacheMetrics handles concurrency
- **Correlation support**: Events link to requests

### Negative

- **Consumer work required**: Must register callbacks and route to destination
- **No out-of-box dashboards**: Consumers build their own
- **Callback overhead**: Each event invokes callbacks
- **Protocol extension**: LogProvider grows by one method

### Neutral

- **CacheEvent dataclass**: New type for event structure
- **CacheMetrics optional**: Consumers can use or ignore
- **Default logs to info**: Structured log message for each event

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - All cache operations emit events
   - Events include latency_ms
   - Correlation IDs propagated when available

2. **Testing requirements**:
   - Unit tests verify event emission
   - Unit tests verify CacheMetrics calculations
   - Integration tests verify callback invocation

3. **Documentation**:
   - README shows callback registration example
   - Example CloudWatch integration provided
   - CacheMetrics usage documented

4. **Consumer checklist**:
   - Implement log_cache_event if using custom LogProvider
   - Register callbacks for metrics routing
   - Set up dashboards for hit rate, latency, errors
