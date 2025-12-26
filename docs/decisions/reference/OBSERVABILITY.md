# ADR Summary: Observability

> Consolidated decision record for logging, monitoring, correlation, and debugging support. Individual ADRs archived.

## Overview

The SDK's observability strategy provides visibility into system behavior through structured logging, request tracing, and metrics integration. The approach balances three priorities: infrastructure agnostic design (consumers choose CloudWatch, DataDog, Prometheus, etc.), minimal overhead (zero-cost when disabled), and rich contextual information (correlation IDs, timing, structured events).

The observability system operates at three levels: correlation IDs for request tracing, structured logging for debugging, and lifecycle hooks for metrics. Correlation IDs link SDK operations across cache hits, API calls, retries, and errors. Structured logging uses the standard library `logging` module with hierarchical naming and lazy formatting for zero overhead. Protocol-based hooks allow consumers to integrate telemetry backends without SDK modifications.

All observability mechanisms follow the SDK's protocol extensibility pattern (ADR-0001), ensuring consumers can inject custom implementations without adding SDK dependencies.

## Key Decisions

### 1. Foundation: Structured Observability with Hooks
**Context**: Need visibility into cache performance, API requests, resilience events, and debugging information without coupling to specific metrics infrastructure.

**Decision**: Extend `LogProvider` protocol with `log_cache_event()` method for cache observability and define `ObservabilityHook` protocol for request lifecycle events. Provide helper classes (`CacheMetrics`) for common aggregations. Consumers register callbacks to route events to their preferred destination.

**Rationale**: SDK must work with any metrics backend. Protocol-based extension allows consumers to integrate CloudWatch, DataDog, Prometheus, or any telemetry system without SDK changes. Default implementations (NullObservabilityHook, DefaultLogProvider) ensure zero overhead when not used.

**Source ADRs**: ADR-0023 (Observability Strategy), ADR-0085 (ObservabilityHook Protocol Design)

### 2. Correlation: Request Tracing with SDK-Generated IDs
**Context**: Need to trace SDK operations through cache layers, API calls, retries, and errors. Asana's X-Request-Id is insufficient because it's only available after requests complete, changes on retries, and paginated operations have multiple IDs.

**Decision**: Generate SDK correlation IDs using format `sdk-{timestamp_hex}-{random_hex}`. Each top-level SDK operation gets one correlation ID. All HTTP requests, retries, and pagination within that operation share the same ID. IDs are injected via `@error_handler` decorator on client methods.

**Rationale**: Timestamp prefix (8 hex chars from Unix milliseconds) provides temporal ordering for debugging. Random suffix (4 hex chars) prevents collisions within the same millisecond. Short format (18 characters) is log-friendly. SDK-generated IDs are available before any HTTP request and consistent across retries and pagination.

**Implications**: Correlation IDs enable tracing single operations through all activity layers. Consumers can log SDK correlation IDs alongside their own tracing systems. Small collision risk (~1/65536 per millisecond) is acceptable for debugging purposes.

**Source ADRs**: ADR-0013 (Correlation ID Strategy for SDK Observability)

### 3. Logging: Standardization with Hierarchical Naming
**Context**: Inconsistent logging patterns across 22+ SDK modules made filtering difficult. Some modules used `__name__`, others used literal strings, some used inline imports. No standard for structured context or zero-cost formatting.

**Decision**: Standardize on `autom8_asana.{module_path}` logger naming using `logging.getLogger(__name__)` pattern. Use lazy formatting (`logger.debug("msg %s", arg)` not `f"msg {arg}"`) for zero overhead. Support structured context via `extra` dict parameter with `LogContext` dataclass helper.

**Rationale**: Using `__name__` provides automatic hierarchical namespacing (`autom8_asana.transport.http`, `autom8_asana.persistence.session`). Hierarchical naming allows users to filter by setting levels on `autom8_asana` (all logs) or specific sub-modules. Lazy formatting prevents string creation when log level is disabled. Standard `extra` dict works with JSON formatters and external sinks without custom interfaces.

**Implications**: Users can easily configure SDK logging with `logging.getLogger("autom8_asana").setLevel(DEBUG)`. Structured fields (correlation_id, entity_gid, duration_ms) enable integration with log aggregation systems. Existing code requires migration from f-strings to lazy formatting.

**Source ADRs**: ADR-0086 (Logging Standardization)

### 4. Hooks: Protocol-Based Lifecycle Events
**Context**: Teams want to integrate metrics libraries (Prometheus, DataDog, OpenTelemetry) without modifying SDK internals. Need standardized hooks for request-level metrics, rate limit events, circuit breaker state changes, and retry attempts.

**Decision**: Define `ObservabilityHook` as `typing.Protocol` with async methods for request lifecycle events (`on_request_start`, `on_request_end`, `on_request_error`, `on_rate_limit`, `on_circuit_breaker_state_change`, `on_retry`). Provide `NullObservabilityHook` default implementation for zero overhead.

**Rationale**: Protocol follows SDK pattern for dependency injection (matches `LogProvider`, `CacheProvider`). Async methods support non-blocking telemetry backends. Null object pattern eliminates conditionals (SDK calls hooks unconditionally, null handles no-op case). Structural typing allows duck-typing without inheritance requirements.

**Implications**: Teams can plug in any metrics library by implementing the protocol. No SDK changes needed for new integrations. Zero overhead when no hook registered (null implementation is pass statements). Each hook method is a method call (minimal overhead compared to HTTP requests).

**Source ADRs**: ADR-0085 (ObservabilityHook Protocol Design)

### 5. Overflow: Detection and Metrics Tracking
**Context**: Tasks with extreme relationship counts (200+ subtasks, 500+ stories) cause memory bloat and performance issues when cached. Need visibility into overflow occurrences to tune thresholds.

**Decision**: Emit `overflow_skip` events through observability system when relationship counts exceed thresholds. Track overflow occurrences by entry type in `CacheMetrics`. Log warnings once per task per session to prevent log spam.

**Rationale**: Overflow events enable monitoring which relationship types frequently exceed thresholds. Metrics help operators tune threshold configuration for their workload. Warning deduplication prevents log spam for known-overflow tasks while still alerting on first occurrence.

**Implications**: Consumers can set up alerts if overflow rate exceeds expected percentage. Overflow metrics inform threshold tuning decisions. Dashboard visibility into which tasks are chronic overflows guides capacity planning.

**Source ADRs**: ADR-0022 (Overflow Management), ADR-0023 (Observability Strategy)

### 6. State Capture: Demo Restoration Debugging
**Context**: SDK demonstration suite requires reversible operations. Need to capture entity state for restoration while minimizing memory and complexity.

**Decision**: Implement shallow copy state capture with GID references. Capture scalar fields by value, relationships as GID references only. Use SDK action operations for restoration (add_tag, set_parent, move_to_section).

**Rationale**: GID-based restoration is memory efficient (16-20 bytes per GID vs. potentially KB per object). Restoration via SDK actions is idempotent (adding existing tag is no-op). Aligns with SDK patterns (SaveSession already works with GIDs). Enables differential restoration by comparing GID sets.

**Implications**: State snapshots are easily testable and comparable. Restoration depends on SDK action operations working correctly. Related entity changes during demo not detected (tag rename), but GID restoration is still correct. Manual state tracking required (developer must update current state after operations).

**Source ADRs**: ADR-0088 (State Capture Strategy for Demo Restoration)

## Event Types Reference

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

## Configuration Patterns

### Hierarchical Logging
```python
import logging

# Enable all SDK logs at DEBUG level
logging.getLogger("autom8_asana").setLevel(logging.DEBUG)

# Enable only transport logs
logging.getLogger("autom8_asana.transport").setLevel(logging.DEBUG)
logging.getLogger("autom8_asana").setLevel(logging.WARNING)
```

### Structured Context
```python
from autom8_asana.logging import LogContext

ctx = LogContext(
    correlation_id="sdk-abc123-def4",
    operation="track",
    entity_gid="123456",
)
logger.info("Tracking entity", extra=ctx.to_dict())
```

### Metrics Integration
```python
class PrometheusHook:
    async def on_request_end(self, method: str, path: str, status: int, duration_ms: float) -> None:
        self.requests.labels(method=method, status=str(status)).inc()
        self.latency.observe(duration_ms / 1000)

client = AsanaClient(
    auth=BearerAuth(token),
    observability_hook=PrometheusHook(),
)
```

### Cache Metrics Aggregation
```python
metrics = CacheMetrics()
metrics.on_event(lambda event: send_to_cloudwatch(event))

# Later
stats = metrics.get_stats()
# {"hits": 150, "misses": 50, "hit_rate": 75.0, "avg_latency_ms": 2.3}
```

## Cross-References

**Related Summaries**:
- ADR-SUMMARY-PATTERNS: Protocol extensibility, error handling decorators
- ADR-SUMMARY-API-INTEGRATION: Request lifecycle, retry behavior
- ADR-SUMMARY-CACHING: Cache operations, overflow management

**Integration Points**:
- Correlation IDs propagate through cache, transport, and error handling layers
- ObservabilityHook receives events from transport (requests), rate limiter, circuit breaker, retry handler
- LogProvider extension (log_cache_event) receives cache events from cache provider
- CacheMetrics aggregates events for dashboard consumption

## Compliance Verification

**Code Review Checklist**:
- All cache operations emit events (hit, miss, write, evict, expire, error)
- Events include latency_ms measurement
- Correlation IDs propagated when available
- Transport layer calls ObservabilityHook at request start/end/error
- Rate limiter calls on_rate_limit hook
- Circuit breaker calls on_circuit_breaker_state_change hook
- Retry handler calls on_retry hook
- All loggers use `logging.getLogger(__name__)` pattern
- No f-strings in logger calls (use lazy formatting)
- Overflow warnings deduplicated per task per session

**Testing Requirements**:
- Unit tests verify event emission for all cache operations
- Unit tests verify CacheMetrics calculations (hit_rate, avg_latency_ms)
- Unit tests verify correlation ID generation and propagation
- Integration tests verify callback invocation
- Integration tests verify hooks called with correct arguments in each scenario

**Monitoring Setup**:
- Dashboard for cache hit rate, latency, errors
- Dashboard for overflow skip rates by entry type
- Alert if overflow rate exceeds expected percentage
- Alert if cache error rate spikes
- Track which tasks are chronic overflows

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0013 | Correlation ID Strategy for SDK Observability | 2025-12-08 | Generate SDK correlation IDs with format `sdk-{timestamp_hex}-{random_hex}` per operation |
| ADR-0022 | Overflow Management | 2025-12-09 | Per-relationship thresholds skip caching when exceeded, emit overflow_skip events |
| ADR-0023 | Observability Strategy | 2025-12-09 | Extend LogProvider with log_cache_event, provide CacheMetrics aggregator, consumer callbacks |
| ADR-0085 | ObservabilityHook Protocol Design | 2025-12-16 | Define Protocol for request lifecycle hooks, NullObservabilityHook default |
| ADR-0086 | Logging Standardization | 2025-12-16 | Standardize on `autom8_asana.*` naming, lazy formatting, structured context via extra dict |
| ADR-0088 | State Capture Strategy for Demo Restoration | 2025-12-12 | Shallow copy state capture with GID references, restoration via SDK actions |
