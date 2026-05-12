---
domain: feat/observability
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/observability/"
  - "./src/autom8_asana/api/metrics.py"
  - "./src/autom8_asana/protocols/observability.py"
  - "./src/autom8_asana/lambda_handlers/cloudwatch.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.91
format_version: "1.0"
---

# Observability (Correlation IDs, Metrics, Telemetry)

## Purpose and Design Rationale

### Problem Statement

The service spans two deployment modes — ECS/FastAPI (long-running API server) and Lambda (event-driven cache warmers, workflow handlers) — each with different telemetry backends and different tracing needs. A single-plane observability model would require conditional code in every layer; instead, the design separates concerns into three parallel planes.

### Design Decisions

**Three-protocol stack** (ADR-0013 and TDD-SDK-ALIGNMENT Path 3):
1. **OTel / `autom8y-telemetry`** — distributed tracing and log-trace correlation for ECS mode. Push-HTTP/OTLP. Abstracts backend choice (Grafana Tempo, Jaeger, etc.) behind the platform SDK.
2. **Prometheus / `prometheus_client`** — domain-specific metric counters/histograms/gauges for the ECS API surface. Scrape-pull via `/metrics`. Zero synchronous I/O; fire-and-forget recording.
3. **CloudWatch / `boto3`** — metric emission for Lambda mode. Vendor-native push. Deployed via `emit_metric()` utility in `lambda_handlers/cloudwatch.py`.

**SDK Correlation IDs** (TDD-0007, ADR-0013): The SDK generates its own correlation IDs (`sdk-{ts}-{rand}` format) independent of Asana's `X-Request-Id`. This decouples SDK tracing from Asana's internal ID namespace and allows correlation even when Asana's response is unavailable (e.g., timeout before response headers arrive). The tradeoff: two ID namespaces coexist without a bridge.

**ObservabilityHook protocol** (TDD-HARDENING-A, FR-OBS-001 through FR-OBS-007): An external extension point so SDK consumers (e.g., Datadog APM integration) can receive structured event notifications without the SDK hard-coding vendor telemetry. The actual hook firing is in the `autom8y-http` transport layer — this service only defines the protocol interface and the `NullObservabilityHook` default.

**MetricsEmitter protocol** (TDD-SDK-ALIGNMENT Path 3): Introduced to break the circular import Cycle 5 (`cache -> api`). `DataFrameCache` accepts any `MetricsEmitter` via constructor injection rather than importing `api/metrics.py` directly.

**LogContext dataclass** (TDD-HARDENING-A, FR-LOG-002): Structured log extra fields for SDK operations. All fields optional; `to_dict()` drops None values. Used via `logger.info("...", extra=ctx.to_dict())`. Currently only consumed in `_defaults/log.py`.

### Rejected / Not-Present Alternatives

- **Unified trace context bridge**: HTTP request IDs (UUID hex 16 chars, `X-Request-ID` header) and SDK correlation IDs (`sdk-{ts}-{rand}` 18 chars) are not bridged. No unified propagation record exists. Rationale: not documented; gap acknowledged in scar tissue.
- **Lambda OTel-only**: Lambda handlers do not wire `add_otel_trace_ids` — log-trace correlation is ECS-only. CloudWatch is the Lambda metric sink.

### Tradeoffs Accepted

- SDK correlation IDs are generated fresh per decorated method call, not per HTTP request. Two calls within one request get two different IDs — fine for per-call tracing, lossy for request-scoped aggregation.
- `record_api_call()` in `api/metrics.py` is defined but has zero call sites in source (dead code since TDD-SDK-ALIGNMENT Path 3 — the API call counters and duration histograms exist as objects but are not wired to any call path).
- OTLP push endpoint and auth-routing-field fully delegated to `autom8y-telemetry` platform SDK — opaque at satellite level (OTLP-ENDPOINT-OPACITY gap, P2).

---

## Conceptual Model

### Three Observability Planes

**Plane 1 — OTel Distributed Tracing (ECS)**
- SDK: `autom8y-telemetry[otlp,fastapi,aws]>=0.6.1` + `opentelemetry-instrumentation-httpx>=0.42b0`
- Primary decorator: `@trace_computation(span_name)` from `autom8y_telemetry`
- Manual spans: `get_tracer().start_as_current_span(name)` context manager
- Auto-instrumentation: `HTTPXClientInstrumentor().instrument()` propagates W3C `traceparent` on all outbound httpx calls
- Log correlation: `add_otel_trace_ids` structlog processor injects `trace_id` and `span_id` fields into every log record when inside an active span

**Plane 2 — Prometheus Metrics (ECS)**
- 7 domain metrics in `api/metrics.py` (see Implementation Map)
- `PrometheusMetricsEmitter` is the concrete implementation of `MetricsEmitter` protocol, injected into `DataFrameCache` at startup
- Served at `/metrics` alongside platform-level `autom8y_http_*` metrics from `instrument_app()`

**Plane 3 — CloudWatch Metrics (Lambda)**
- `emit_metric()` in `lambda_handlers/cloudwatch.py`: lazy boto3 client, always adds `environment` dimension, broad-catch prevents Lambda handler failure
- Default namespace `autom8/lambda` (via `ASANA_CW_NAMESPACE` env var)
- DMS heartbeat namespace `Autom8y/AsanaCacheWarmer`
- Freshness probe namespace `Autom8y/FreshnessProbe` (in `metrics/cloudwatch_emit.py`)

### SDK Correlation Subsystem

Two distinct ID namespaces:
- **HTTP request IDs**: UUID hex 16 chars, from `X-Request-ID` header, managed by `RequestIDMiddleware` in `api/middleware/core.py`
- **SDK correlation IDs**: `sdk-{timestamp_hex}-{random_hex}` 18 chars (actual length: 17), generated by `generate_correlation_id()` in `observability/correlation.py`

`CorrelationContext` (frozen dataclass) binds both: `correlation_id` (SDK-generated), `operation`, `started_at`, `resource_gid`, `asana_request_id` (Asana's `X-Request-Id` from response, set post-request via `with_asana_request_id()`).

The `@error_handler` decorator (not `CorrelationContext`) is what actually generates correlation IDs in practice. `CorrelationContext` is a richer model but is not used by `@error_handler` — parallel designs, not integrated.

### Lifecycle / State Transitions

`@error_handler` lifecycle per decorated call:
1. Generate fresh `correlation_id`
2. Derive `operation = "{ClassName}.{method_name}"`
3. Extract `resource_gid` from first positional str arg (if present)
4. Log `[{cid}] {operation}({gid}) starting` at DEBUG
5. Record `start_time = time.monotonic()`
6. `await func(...)` — on success: log `completed in {N}ms` at DEBUG; return result
7. On exception: enrich exception with `.correlation_id` and `.operation` attrs; log `failed: {e}` at ERROR; re-raise

### Inter-Feature Relationships

**Provides to**:
- `cache/integration/dataframe_cache.py` — accepts `MetricsEmitter` (provided by `PrometheusMetricsEmitter` from `api/metrics.py`)
- `query/engine.py`, `query/fetcher.py`, `query/join.py`, `query/compiler.py`, `services/query_service.py`, `services/universal_strategy.py`, `api/routes/resolver.py`, `metrics/compute.py`, `dataframes/builders/progressive.py` — all use `@trace_computation` or manual spans
- `lambda_handlers/cache_warmer.py`, `lambda_handlers/workflow_handler.py` — use `@instrument_lambda`, `emit_success_timestamp`, `emit_metric()`
- Any client class decorated with `@error_handler` — receives correlation ID generation and exception enrichment

**Consumes from**:
- `autom8y-telemetry` platform SDK — OTel instrumentation primitives
- `autom8y-log` — structured logging pipeline; `add_otel_trace_ids` processor
- `autom8y-http[otel]>=0.6.0` — transport-level `InstrumentedTransport`, `ObservabilityHook` firing
- `boto3` — CloudWatch metric emission
- `prometheus_client` — Prometheus metric objects

**External boundary**: `ObservabilityHook` protocol is defined here but fired by `autom8y-http` transport layer (external package, not in this repo). The hook firing sites are not visible from this codebase.

---

## Implementation Map

| File | Role | Key Exports |
|------|------|-------------|
| `src/autom8_asana/observability/correlation.py` | Correlation ID generation and context | `generate_correlation_id()`, `CorrelationContext` |
| `src/autom8_asana/observability/decorators.py` | Error handler decorator | `error_handler` (applied to async client methods) |
| `src/autom8_asana/observability/context.py` | Structured log context dataclass | `LogContext` |
| `src/autom8_asana/api/metrics.py` | 7 Prometheus metrics + `PrometheusMetricsEmitter` + 6 recording functions | `DATAFRAME_BUILD_DURATION`, `DATAFRAME_CACHE_OPS`, `DATAFRAME_ROWS_CACHED`, `DATAFRAME_SWR_REFRESHES`, `DATAFRAME_CIRCUIT_BREAKER`, `ASANA_API_CALLS`, `ASANA_API_DURATION`, `PrometheusMetricsEmitter`, `record_build_duration()`, `record_cache_op()`, `record_rows_cached()`, `record_swr_refresh()`, `record_circuit_breaker_state()`, `record_api_call()` (dead) |
| `src/autom8_asana/protocols/observability.py` | External telemetry extension point protocol | `ObservabilityHook` (6 async hooks: `on_request_start`, `on_request_end`, `on_request_error`, `on_rate_limit`, `on_circuit_breaker_state_change`, `on_retry`) |
| `src/autom8_asana/protocols/metrics.py` | Cache-layer metrics decoupling protocol | `MetricsEmitter` (3 methods: `record_cache_op`, `record_rows_cached`, `record_swr_refresh`) |
| `src/autom8_asana/lambda_handlers/cloudwatch.py` | Lambda CloudWatch emission utility | `emit_metric()` |
| `src/autom8_asana/_defaults/observability.py` | Default no-op hook | `NullObservabilityHook` |
| `src/autom8_asana/api/middleware/core.py` | HTTP request ID middleware | `RequestIDMiddleware`, `RequestLoggingMiddleware` |
| `src/autom8_asana/api/lifespan.py` | OTel wiring at ECS startup | Wires `add_otel_trace_ids` (line 77), `HTTPXClientInstrumentor` (lines 85–94) |

### Data Flow

**ECS trace path**:
`api/lifespan.py` startup → `HTTPXClientInstrumentor().instrument()` (auto-propagates W3C `traceparent`) + `add_otel_trace_ids` injected into structlog → decorated handler/service → `@trace_computation` span → OTLP push → platform SDK backend (opaque)

**ECS metrics path**:
`PrometheusMetricsEmitter` injected into `DataFrameCache` at startup → `record_cache_op()`, `record_rows_cached()`, `record_swr_refresh()` called on cache events → Prometheus counters/gauges in memory → `/metrics` scrape endpoint

**Lambda metrics path**:
Lambda handler → `emit_metric(metric_name, value)` → `boto3.client("cloudwatch").put_metric_data()` → AWS CloudWatch namespace

**SDK correlation path**:
Client method decorated with `@error_handler` → `generate_correlation_id()` → correlation ID on log lines and exception attributes

### Prometheus Metric Inventory

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `autom8y_asana_dataframe_build_duration_seconds` | Histogram | `entity_type` | `record_build_duration()` |
| `autom8y_asana_dataframe_cache_operations_total` | Counter | `entity_type`, `tier`, `result` | `record_cache_op()` / `PrometheusMetricsEmitter` |
| `autom8y_asana_dataframe_rows_cached` | Gauge | `entity_type` | `record_rows_cached()` / `PrometheusMetricsEmitter` |
| `autom8y_asana_dataframe_swr_refreshes_total` | Counter | `entity_type`, `result` | `record_swr_refresh()` / `PrometheusMetricsEmitter` |
| `autom8y_asana_dataframe_circuit_breaker_state` | Gauge | `project_gid` | `record_circuit_breaker_state()` |
| `autom8y_asana_api_calls_total` | Counter | `method`, `path_pattern`, `status_code` | `record_api_call()` — **DEAD CODE: zero call sites** |
| `autom8y_asana_api_call_duration_seconds` | Histogram | `method`, `path_pattern` | `record_api_call()` — **DEAD CODE: zero call sites** |

### OTel Span Inventory (as of SHA 8980bcd7)

| Span Name | Mechanism | File |
|-----------|-----------|------|
| `metric.compute` | `@trace_computation` | `metrics/compute.py:19` |
| `cache.get` | `@trace_computation` | `cache/integration/dataframe_cache.py:234` |
| `progressive.build` | `@trace_computation` | `dataframes/builders/progressive.py:445` |
| `predicate.compile` | `@trace_computation` | `query/compiler.py:164` |
| `entity.query_rows` | `@trace_computation` | `query/engine.py:76` |
| `entity.query_aggregate` | `@trace_computation` | `query/engine.py:242` |
| `data.fetch` | `@trace_computation` | `query/fetcher.py:40` |
| `join.*` | `@trace_computation` | `query/join.py:90` |
| `query_service.*` | `@trace_computation` | `services/query_service.py:559` |
| `strategy.resolution.resolve` | manual `get_tracer()` | `services/universal_strategy.py:177` |
| `strategy.resolution.resolve_group` | manual `get_tracer()` | `services/universal_strategy.py:306` |
| resolver route | manual `get_tracer()` | `api/routes/resolver.py:351` |
| `payment_reconciliation.process_entity` | `@trace_reconciliation` | `automation/workflows/payment_reconciliation/workflow.py:164` |

### Test Coverage

Primary test file: `tests/unit/test_observability.py` — covers `generate_correlation_id()` (format, length, uniqueness, prefix, timestamp component, random component), `CorrelationContext` (generate, resource_gid, `with_asana_request_id`, `format_log_prefix`, `format_operation`, immutability), and `@error_handler` (log start/complete, log error, exception enrichment, no-log-provider, functools.wraps, timing, ID uniqueness across calls).

Also covered tangentially: `tests/test_computation_spans.py` (OTel span behavior).

Not covered by dedicated tests: `LogContext`, `MetricsEmitter` protocol, `NullObservabilityHook`, `PrometheusMetricsEmitter`, `emit_metric()` CloudWatch utility, `record_api_call()` dead code.

---

## Boundaries and Failure Modes

### Explicit Scope Boundaries

This feature does NOT:
- Fire `ObservabilityHook` methods — hook dispatch is in `autom8y-http` transport layer (external package)
- Provide unified trace context between HTTP request IDs and SDK correlation IDs — no bridge exists
- Instrument the `/v1/exports` or `/api/v1/exports` handlers at span level (OBS-EXPORTS-001 — P2, deadline 2026-06-15, 38 days as of 2026-05-08)
- Wire `add_otel_trace_ids` in Lambda mode — log-trace correlation is ECS-only
- Configure sampling (`OTEL_TRACES_SAMPLER` undeclared; delegated to platform SDK)
- Declare a credential-topology-matrix instance (CRED-TOPOLOGY-MATRIX gap — schema exists, no instance)

### Instrumentation Gaps Registry

| ID | Surface | Severity | Deadline | Status |
|----|---------|----------|----------|--------|
| OBS-EXPORTS-001 | `api/routes/exports.py`, `api/routes/_exports_helpers.py` | P2 | 2026-06-15 | OPEN — zero instrumentation at SHA 8980bcd7 |
| H-006 | `automation/workflows/bridge_base.py:191-195` | P3 | Unknown | OPEN — `trace_computation` not available in 0.6.1; inline TODO |
| LAMBDA-OBS-001 | 10 of 13 Lambda handlers (no `autom8y_telemetry` span) | P3 | None | OPEN — CloudWatch-only for uninstrumented handlers |
| SLO-API-SURFACE | Zero ECS/API SLOs defined | P2 | None | OPEN |
| CRED-TOPOLOGY-MATRIX | No satellite-level credential topology instance | P2 | None | OPEN |
| OTLP-ENDPOINT-OPACITY | OTLP push endpoint and auth opaque at satellite | P2 | None | OPEN |

**Uninstrumented Lambda handlers** (10 of 13 non-shared): `pipeline_stage_aggregator`, `reconciliation_runner`, `checkpoint`, `payment_reconciliation`, `insights_export`, `push_orchestrator`, `conversation_audit`, `story_warmer`, `cache_invalidate`, `timeout`. CloudWatch emission via shared `emit_metric()` only.

### Known Failure Modes

**Metric recording**: All `record_*` functions and `emit_metric()` are fire-and-forget with no error propagation. CloudWatch emission wraps `boto3.put_metric_data` in a broad `except Exception` that logs a WARNING and swallows the error (`lambda_handlers/cloudwatch.py:74`). Prometheus recording has no explicit error handling — failures would raise `prometheus_client` internal errors silently.

**Exception enrichment in `@error_handler`**: Attempts `e.correlation_id = value` directly; falls back to `object.__setattr__`. If both fail (e.g., truly immutable exception), the attribute is silently skipped — the exception is still re-raised without enrichment. No test covers this double-fallback path.

**OTel graceful degradation**: `HTTPXClientInstrumentor` import is wrapped in `try/except ImportError` at `api/lifespan.py:85-94`. If `opentelemetry-instrumentation-httpx` is unavailable, a structured WARNING is logged and startup continues. Auto-instrumentation silently disabled.

**`record_api_call()` dead code**: The `ASANA_API_CALLS` and `ASANA_API_DURATION` Prometheus metrics are registered on the default `REGISTRY` at import time but `record_api_call()` is never called from any source file. The metrics appear in `/metrics` output with zero observations. Any code depending on these counters for API call monitoring will receive zeroes.

### Configuration Boundaries

`ObservabilitySettings` (in `settings.py:582-613`) governs:
- `ASANA_CW_NAMESPACE` env var → `cloudwatch_namespace` (default `autom8/lambda`)
- `ASANA_CW_ENVIRONMENT` env var → `environment` dimension (default `staging`)

Region resolution for CloudWatch: `AWS_REGION` env var → `ASANA_CACHE_S3_REGION` → default `us-east-1` (`metrics/cloudwatch_emit.py:116-117`).

OTLP endpoint: not configured at satellite level — entirely delegated to `autom8y-telemetry`.

### Interaction Points With Other Features

- **Cache subsystem**: `DataFrameCache` calls `metrics_emitter.record_cache_op()`, `record_rows_cached()`, `record_swr_refresh()` — `PrometheusMetricsEmitter` is the concrete wiring. Changing metric label shapes requires updates in both `api/metrics.py` (Prometheus registration) and any dashboards reading those labels.
- **Lambda handlers**: `cache_warmer.py` has the richest metric emission (WarmSuccess, WarmDuration, WarmFailure, CheckpointResumed, CheckpointSaved, DMS heartbeat). All via `emit_metric()`.
- **HTTP transport**: `ObservabilityHook` hook sites are in `autom8y-http` — changes to hook method signatures must be coordinated with that external package.
- **API middleware**: `RequestIDMiddleware` manages `X-Request-ID` header separately from SDK correlation IDs. The two ID namespaces are not bridged and appear as parallel fields in log records.

```metadata
confidence: 0.91
observation_mode: refresh
source_hash: "8980bcd7"
prior_source_hash: "c213958"
delta_obs_relevant: false
obs_exports_001_status: OPEN
obs_exports_001_deadline_days_remaining: 38
h006_status: OPEN
lambda_uninstrumented_count: 10
lambda_total_non_shared: 13
record_api_call_dead_code: true
null_observability_hook_location: "_defaults/observability.py"
metrics_emitter_protocol_location: "protocols/metrics.py"
otel_graceful_degradation: true
log_trace_correlation_ecs_only: true
```
