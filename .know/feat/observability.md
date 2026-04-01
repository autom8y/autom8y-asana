---
domain: feat/observability
generated_at: "2026-04-01T17:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/observability/**/*.py"
  - "./src/autom8_asana/api/metrics.py"
  - "./src/autom8_asana/protocols/observability.py"
  - "./src/autom8_asana/lambda_handlers/cloudwatch.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.85
format_version: "1.0"
---

# Observability (Correlation IDs, Metrics, Telemetry)

## Purpose and Design Rationale

Three capabilities: **correlation ID tracking** (SDK-level request tracing), **Prometheus metrics** (ECS/API mode), **CloudWatch metrics** (Lambda mode). OpenTelemetry distributed tracing integrated via `autom8y-telemetry` platform SDK.

**Design tension**: `ObservabilityHook` protocol is the external SDK integration point for consumers (e.g., Datadog APM). Internal API Prometheus metrics and Lambda CloudWatch emission are parallel planes, not routed through that protocol.

## Conceptual Model

### SDK Correlation (`observability/`)

`generate_correlation_id()` -> `sdk-{timestamp_hex}-{random_hex}` (18 chars). `CorrelationContext` (frozen dataclass) captures correlation_id, operation, resource_gid, asana_request_id. `@error_handler` decorator on 12 resource client classes generates fresh correlation IDs, times calls, enriches exceptions.

**Two distinct ID namespaces**: HTTP request IDs (UUID hex 16 chars, `X-Request-ID`) and SDK correlation IDs (`sdk-{ts}-{rand}` 18 chars). No bridging mechanism between them.

### ECS Prometheus Metrics (`api/metrics.py`)

7 metric objects: `asana_dataframe_build_duration_seconds`, `asana_dataframe_cache_operations_total`, `asana_dataframe_rows_cached`, `asana_dataframe_swr_refreshes_total`, `asana_dataframe_circuit_breaker_state`, `asana_api_calls_total`, `asana_api_call_duration_seconds`. `PrometheusMetricsEmitter` satisfies `MetricsEmitter` protocol (breaks `cache -> api` circular import).

### Lambda CloudWatch (`lambda_handlers/cloudwatch.py`)

`emit_metric()` -- shared utility, lazy boto3 client, always adds `environment` dimension. Broad-catch: metric failures never fail handlers.

### ObservabilityHook Protocol (`protocols/observability.py`)

6 async hooks: `on_request_start`, `on_request_end`, `on_request_error`, `on_rate_limit`, `on_circuit_breaker_state_change`, `on_retry`. Default: `NullObservabilityHook`. Actual hook firing is in `autom8y-http` transport layer, not in this service's source.

### OTel Integration

`add_otel_trace_ids` structlog processor injects trace_id into log records. `HTTPXClientInstrumentor().instrument()` propagates W3C `traceparent` headers. Graceful degradation if OTel packages unavailable.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/observability/correlation.py` | `generate_correlation_id()`, `CorrelationContext` |
| `src/autom8_asana/observability/decorators.py` | `@error_handler` -- applied to 12 client classes |
| `src/autom8_asana/observability/context.py` | `LogContext` dataclass for structured log extra fields |
| `src/autom8_asana/api/metrics.py` | 7 Prometheus metrics + `PrometheusMetricsEmitter` |
| `src/autom8_asana/protocols/observability.py` | `ObservabilityHook` protocol (6 hooks) |
| `src/autom8_asana/protocols/metrics.py` | `MetricsEmitter` protocol (cache-api decoupling) |
| `src/autom8_asana/lambda_handlers/cloudwatch.py` | `emit_metric()` CloudWatch utility |
| `src/autom8_asana/api/middleware/core.py` | `RequestIDMiddleware`, `RequestLoggingMiddleware` |

## Boundaries and Failure Modes

- `ObservabilityHook` is NOT called from within this service -- it's called by `autom8y-http`
- `CorrelationContext` is NOT used by `@error_handler` (parallel designs)
- `LogContext` is defined and exported but only used in `_defaults/log.py`
- No unified trace context propagation between HTTP request IDs and SDK correlation IDs
- All metric recording is fire-and-forget (silent on failure)

## Knowledge Gaps

1. `ObservabilityHook` actual call sites in `autom8y-http` not visible from this codebase.
2. `record_api_call()` call sites not found -- may be dead code.
3. `@error_handler` applied to clients only (not services) -- rationale undocumented.
4. CloudWatch-to-Prometheus metric mapping across deployment modes undocumented.
