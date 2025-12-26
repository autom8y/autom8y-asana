# TDD-05: Observability & Telemetry

> Consolidated Technical Design Document for logging, metrics, correlation, and event hooks.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-0007 (Observability Enhancements)
- **Related ADRs**: ADR-0003 (Request Correlation), ADR-0004 (Observability Hooks), ADR-0005 (Overflow Metrics)

---

## Overview

The observability layer provides request tracing, structured logging, and extensible metrics hooks for the autom8_asana SDK. Engineers can trace any SDK operation through all activity layers (cache, API, retries) using SDK-generated correlation IDs, while consuming applications route telemetry to their preferred monitoring infrastructure (CloudWatch, DataDog, Prometheus, etc.) via protocol-based hooks.

**Key outcomes**:
- Consistent request tracing via correlation IDs across cache lookups, API calls, and retries
- Zero-cost logging when disabled (lazy formatting pattern)
- Infrastructure-agnostic metrics via `ObservabilityHook` protocol
- Cache event tracking with overflow detection and threshold management
- Exception enrichment with correlation context for debugging

---

## Design Goals

1. **Traceable operations**: Every SDK operation gets a unique correlation ID visible in logs and exceptions
2. **Zero overhead when disabled**: Lazy formatting ensures no string construction when logging is off
3. **Infrastructure agnostic**: Protocol-based hooks let consumers route to any monitoring system
4. **Consistent patterns**: `@error_handler` decorator applies uniformly across all client methods
5. **Bounded cache behavior**: Overflow detection prevents outlier tasks from consuming excessive resources

---

## Logging Architecture

### Logger Naming Convention

All SDK modules use hierarchical `__name__` logging for consistent filtering:

```python
import logging
logger = logging.getLogger(__name__)

# Examples:
# autom8_asana.transport.http
# autom8_asana.persistence.session
# autom8_asana.models.business.contact
```

**Benefits**:
- Automatic namespacing via Python module path
- Hierarchical filtering: set level for `autom8_asana` (all) or `autom8_asana.transport` (specific)
- Standard Python convention used by most libraries
- No magic strings to maintain

### Zero-Cost Logging Pattern

```python
# WRONG: Eager formatting (string always created, even when debug disabled)
logger.debug(f"Processing entity {gid} with {len(fields)} fields")

# CORRECT: Lazy formatting (zero overhead when debug disabled)
logger.debug("Processing entity %s with %s fields", gid, len(fields))

# For expensive computations, guard with level check
if logger.isEnabledFor(logging.DEBUG):
    summary = compute_expensive_summary(entity)
    logger.debug("Entity summary: %s", summary)
```

**Performance comparison** (debug disabled):

| Pattern | Overhead |
|---------|----------|
| f-string formatting | ~0.5 microseconds (string always created) |
| %-style formatting | ~0.02 microseconds (string created) |
| `logger.debug("%s", arg)` | ~0.01 microseconds (string never created) |

### Log Levels

| Event | Level | Condition |
|-------|-------|-----------|
| Operation start | DEBUG | Always |
| Operation success | DEBUG | Always |
| Retry attempt | WARNING | On retry |
| Rate limit wait | WARNING | On rate limit |
| Cache overflow | WARNING | On threshold exceeded (once per task per session) |
| Operation failure | ERROR | On exception |

---

## Correlation IDs

### ID Format

```
sdk-{timestamp_hex}-{random_hex}

Examples:
  sdk-192f3a1b-4c7e
  sdk-192f3a1c-8d2f
```

**Components**:
- `sdk-` prefix: Distinguishes from Asana's X-Request-Id
- `timestamp_hex`: Lower 32 bits of Unix milliseconds (8 hex chars)
- `random_hex`: Random component for uniqueness (4 hex chars)

**Properties**:
- 18 characters total (short enough for readable logs)
- Temporally ordered (earlier operations sort first)
- Collision-resistant (~1/65536 per millisecond)
- Fast generation (no locks, no I/O)

### CorrelationContext

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CorrelationContext:
    """Immutable context for a single SDK operation."""

    correlation_id: str
    """SDK-generated correlation ID for this operation."""

    operation: str
    """Operation name, e.g., 'TasksClient.get_async'."""

    started_at: float
    """Unix timestamp when operation started."""

    resource_gid: str | None = None
    """Optional GID of the resource being operated on."""

    asana_request_id: str | None = None
    """X-Request-Id from Asana response (set after request completes)."""

    @staticmethod
    def generate(operation: str, resource_gid: str | None = None) -> "CorrelationContext":
        """Create new context with fresh correlation ID."""
        ...

    def with_asana_request_id(self, request_id: str) -> "CorrelationContext":
        """Return new context with Asana request ID set."""
        ...

    def format_log_prefix(self) -> str:
        """Format prefix for log messages, e.g., '[sdk-abc123-4567]'."""
        ...
```

### Log Format

**Standard format**:
```
[{correlation_id}] {operation}({resource_gid}) {message}

Examples:
[sdk-192f3a1b-4c7e] TasksClient.get_async(1234567890) starting
[sdk-192f3a1b-4c7e] TasksClient.get_async(1234567890) completed in 142ms
```

**Error format**:
```
[{correlation_id}] {operation}({resource_gid}) failed: {error_type}: {message}
  Asana request_id: {asana_request_id}
  Duration: {duration_ms}ms

Example:
[sdk-192f3a1b-4c7e] TasksClient.get_async(1234567890) failed: NotFoundError: No task found
  Asana request_id: abc123-def456
  Duration: 89ms
```

---

## Metrics & Events

### Cache Event Protocol

The `LogProvider` protocol is extended with cache event support:

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
    """Logging protocol with cache event support."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def log_cache_event(self, event: CacheEvent) -> None:
        """Log structured cache event."""
        ...
```

**Event Types**:

| Event Type | Description | Emitted By |
|------------|-------------|------------|
| `hit` | Cache read found data | `get_versioned()` |
| `miss` | Cache read found nothing | `get_versioned()` |
| `write` | Cache write completed | `set_versioned()` |
| `evict` | Explicit invalidation | `invalidate()` |
| `expire` | TTL-based expiration | `get_versioned()` |
| `error` | Cache operation failed | All cache operations |
| `overflow_skip` | Write skipped (threshold exceeded) | Relationship fetch |
| `degrade` | Switched to fallback mode | Cache provider |
| `restore` | Restored from fallback | Cache provider |

### ObservabilityHook Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ObservabilityHook(Protocol):
    """Protocol for observability integration.

    Implement to receive SDK operation events for metrics,
    tracing, or logging integration. All methods are async
    to support non-blocking telemetry backends.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None: ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None: ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None: ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None: ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None: ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None: ...
```

### CacheMetrics Aggregator

Thread-safe helper for common cache statistics:

```python
class CacheMetrics:
    """Thread-safe cache metrics aggregator."""

    def record_event(self, event: CacheEvent) -> None:
        """Record event and notify callbacks."""
        ...

    def on_event(self, callback: Callable[[CacheEvent], None]) -> None:
        """Register callback for cache events."""
        ...

    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        ...

    def avg_latency_ms(self) -> float:
        """Calculate average operation latency."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get all statistics as dictionary."""
        # Returns: {"hits": 150, "misses": 50, "hit_rate": 75.0,
        #           "avg_latency_ms": 2.3, "overflow_skips": {"subtasks": 12}}
        ...
```

### Overflow Detection

Tasks with extreme relationship counts skip caching to prevent resource bloat:

```python
@dataclass
class OverflowSettings:
    """Per-relationship overflow thresholds."""
    subtasks: int | None = 40
    dependencies: int | None = 40
    dependents: int | None = 40
    stories: int | None = 100
    attachments: int | None = 40
```

**Threshold defaults** (based on workload analysis):

| Entry Type | Threshold | Rationale |
|------------|-----------|-----------|
| subtasks | 40 | >99% of tasks have <40 subtasks |
| dependencies | 40 | Most tasks have <10 dependencies |
| dependents | 40 | Most tasks have <10 dependents |
| stories | 100 | Active discussions may exceed |
| attachments | 40 | Documentation tasks may exceed |

---

## Hook Integration

### @error_handler Decorator

The `@error_handler` decorator provides consistent observability for all client methods:

```python
def error_handler(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Decorator for consistent error handling on client methods.

    Provides:
    1. Correlation ID generation and propagation
    2. Consistent error logging with context
    3. Exception enrichment with correlation data
    4. Operation timing (debug level)
    """
```

**Decorator behavior**:

1. **Before operation**: Generate correlation ID, log start (DEBUG)
2. **On success**: Log completion with duration (DEBUG)
3. **On error**: Log with full context, enrich exception, re-raise

**Application pattern** (explicit on async methods):

```python
class TasksClient(BaseClient):
    @error_handler
    async def get_async(self, task_gid: str, ...) -> Task:
        ...

    @sync_wrapper("get_async")
    def get(self, task_gid: str, ...) -> Task:
        # Delegates to get_async which has error handling
        ...
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
        overflow_settings: OverflowSettings | None = None,
    ) -> None:
        self._observability = observability_hook or NullObservabilityHook()
        self._log = log_provider or DefaultLogProvider()
        self._overflow = overflow_settings or OverflowSettings()
```

### Structured Context

```python
@dataclass
class LogContext:
    """Structured logging context via extra parameter."""
    correlation_id: str | None = None
    operation: str | None = None
    entity_gid: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

# Usage
ctx = LogContext(
    correlation_id="sdk-abc123-def4",
    operation="track",
    entity_gid=task.gid,
)
logger.info("Tracking entity", extra=ctx.to_dict())
```

---

## Testing Strategy

### Unit Tests

```python
# Correlation ID tests
def test_correlation_id_format():
    ctx = CorrelationContext.generate("TestClient.method")
    assert ctx.correlation_id.startswith("sdk-")
    assert len(ctx.correlation_id) == 18

def test_correlation_context_immutable():
    ctx = CorrelationContext.generate("TestClient.method")
    ctx2 = ctx.with_asana_request_id("abc123")
    assert ctx.asana_request_id is None
    assert ctx2.asana_request_id == "abc123"

# Decorator tests
async def test_error_handler_logs_success():
    log = MockLogProvider()
    client = make_test_client(log_provider=log)
    await client.get_async("123")
    assert any("[sdk-" in msg for msg in log.debug_messages)
    assert any("completed" in msg for msg in log.debug_messages)

async def test_error_handler_enriches_exception():
    client = make_failing_client()
    with pytest.raises(NotFoundError) as exc_info:
        await client.get_async("nonexistent")
    assert exc_info.value.correlation_id.startswith("sdk-")
    assert exc_info.value.operation == "TasksClient.get_async"

# Cache metrics tests
def test_cache_metrics_hit_rate():
    metrics = CacheMetrics()
    metrics.record_event(CacheEvent("hit", "key1", "tasks", 1.0))
    metrics.record_event(CacheEvent("hit", "key2", "tasks", 1.0))
    metrics.record_event(CacheEvent("miss", "key3", "tasks", 2.0))
    assert metrics.hit_rate() == pytest.approx(66.67, rel=0.01)

# Overflow tests
def test_overflow_detection():
    settings = OverflowSettings(subtasks=40)
    assert not settings.is_overflow("subtasks", 25)
    assert settings.is_overflow("subtasks", 50)
```

### Integration Tests

```python
async def test_sync_and_async_paths_both_get_correlation():
    """Verify both sync and async paths get error handling."""
    log = MockLogProvider()
    client = make_real_client(log_provider=log)

    # Async path
    await client.tasks.get_async("123")
    async_logs = list(log.debug_messages)
    log.clear()

    # Sync path
    client.tasks.get("123")
    sync_logs = list(log.debug_messages)

    # Both should have correlation IDs
    assert any("[sdk-" in msg for msg in async_logs)
    assert any("[sdk-" in msg for msg in sync_logs)

async def test_observability_hook_receives_events():
    """Verify hook methods called at correct lifecycle points."""
    hook = MockObservabilityHook()
    client = AsanaClient(observability_hook=hook, ...)

    await client.tasks.get_async("123")

    assert hook.request_starts == 1
    assert hook.request_ends == 1
    assert len(hook.correlation_ids) == 1
```

---

## Consumer Integration Examples

### CloudWatch

```python
class CloudWatchLogProvider(DefaultLogProvider):
    def __init__(self, cloudwatch_client):
        super().__init__()
        self._cw = cloudwatch_client

    def log_cache_event(self, event: CacheEvent) -> None:
        self._cw.put_metric_data(
            Namespace="Autom8/Cache",
            MetricData=[
                {"MetricName": f"Cache{event.event_type.capitalize()}", "Value": 1},
                {"MetricName": "CacheLatency", "Value": event.latency_ms, "Unit": "Milliseconds"},
            ],
        )
        super().log_cache_event(event)
```

### Prometheus

```python
from prometheus_client import Counter, Histogram

class PrometheusHook:
    def __init__(self):
        self.requests = Counter('asana_requests_total', 'Total requests', ['method', 'status'])
        self.latency = Histogram('asana_request_duration_seconds', 'Request latency')

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        self.requests.labels(method=method, status=str(status)).inc()
        self.latency.observe(duration_ms / 1000)
```

### JSON Structured Logging

```python
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ["correlation_id", "entity_gid", "operation", "duration_ms"]:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("autom8_asana").addHandler(handler)
```

---

## Cross-References

### Related TDDs

| TDD | Relationship |
|-----|--------------|
| [TDD-01](./TDD-01-foundation-architecture.md) | Defines LogProvider protocol extended here |
| [TDD-02](./TDD-02-data-layer.md) | Uses correlation IDs in persistence operations |
| [TDD-03](./TDD-03-resource-clients.md) | Client methods decorated with `@error_handler` |
| [TDD-04](./TDD-04-batch-save-operations.md) | Batch operations emit cache events |

### Related ADRs

| ADR | Decision |
|-----|----------|
| [ADR-0003](../decisions/ADR-0003-request-correlation-structured-logging.md) | Correlation ID format and structured logging patterns |
| [ADR-0004](../decisions/ADR-0004-observability-hooks-cache-events.md) | ObservabilityHook protocol and cache event types |
| [ADR-0005](../decisions/ADR-0005-overflow-detection-metrics.md) | Overflow threshold management and metrics |

### Archived Source Documents

| Original | Archive Location |
|----------|------------------|
| TDD-0007-observability.md | `docs/.archive/2025-12-tdds/TDD-0007-observability.md` |

---

**Last Updated**: 2025-12-25 (Consolidated from TDD-0007)
