---
domain: obs
generated_at: "2026-05-08T00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./pyproject.toml"
  - "./.ledge/specs/cache-freshness-observability.md"
  - "./.ledge/specs/cache-freshness-runbook.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.84
format_version: "1.0"
update_mode: "incremental"
incremental_cycle: 1
max_incremental_cycles: 3
---

# Codebase Observability

**Vendor Detection**: Multi-protocol stack detected.

- **Protocol 1**: OTel SDK (`autom8y-telemetry[otlp,fastapi,aws]>=0.6.1` + `opentelemetry-instrumentation-httpx>=0.42b0`) — push-HTTP via OTLP
- **Protocol 2**: Prometheus (`prometheus_client` via `create_fleet_app`/`instrument_app()`) — scrape-pull, served via `/metrics`
- **Protocol 3**: CloudWatch (`boto3.client("cloudwatch")`) — vendor-native push, Lambda mode only
- **Deployment modes**: ECS/FastAPI (Prometheus + OTel), Lambda (CloudWatch + `autom8y_telemetry.aws`)

---

## OBS-EXPORTS-001: Exports Route Instrumentation Gap (P2)

**Status**: PARTIAL — request span + 3 structured logs (Required Instrumentation §1-4) landed 2026-06-01 (branch `sre-ob2-exports-observability-2026-06-01`); metric counters/histograms, SLO targets, and alert rules remain. | **Severity**: P2 | **Pre-GA Deadline**: 2026-06-15

### Anchor

- `src/autom8_asana/api/routes/exports.py:92` — `logger = get_logger(__name__)` (log correlation only)
- `src/autom8_asana/api/routes/exports.py` — zero `metric.`, `tracer.`, `counter.`, `histogram.`, or `span.` calls (grep count: 0, verified at source_hash `8980bcd7`)
- `src/autom8_asana/api/routes/_exports_helpers.py` — three logger calls (column-source warning, identity-suppression warning, no-matching-columns warning) but zero metric/span calls (grep count: 0, verified at source_hash `8980bcd7`)
- Inherited surface: `add_otel_trace_ids` OTel processor wired in `api/lifespan.py` (log correlation only — no child span wraps the exports handler)

### Verification Against SHA 8980bcd7

Commits `8980bcd7..f37802f2` (Sprint-3 hygiene, xdist activation, persistence test budget, autom8y-core lower-bound lift) do not touch `exports.py` or `_exports_helpers.py`. The `autom8y-core>=4.2.0` lower-bound bump (`f6864435`) is a token/config SDK — it carries no observability surface. Grep at HEAD (`8980bcd7`) returned 0 matches for all instrumentation patterns in both files. **UPDATE 2026-06-01:** Required Instrumentation §1-4 (request span + 3 structured logs) are now implemented — one `exports.request` span opened in the shared `export_handler` (mirrors `resolver.py`), carrying the six contracted attributes, plus the three trigger-gated logs. Branch `sre-ob2-exports-observability-2026-06-01`. **Residual (still open):** metric counters/histograms, SLO targets, and alert rules.

### Symptom

The `/v1/exports` and `/api/v1/exports` routes are LIVE on `main` carrying Phase 1 of `project-asana-pipeline-extraction` (telos deadline 2026-05-11). The routes have:

- 0 metric counters/histograms (no `request_duration_seconds`, no `predicate_split_outcome`, no `format_negotiation_fallback_total`, no `identity_suppressed_count`)
- 0 explicit tracer spans (only auto-instrumentation via OTel FastAPI middleware — no child spans within handler)
- 0 SLO targets defined
- 0 alert rules

### Required Instrumentation (§1-4 implemented 2026-06-01; metrics/SLO/alerts residual)

1. **Request span** — emit `exports_request_complete` with fields: `entity_type`, `row_count_pre_dedup`, `row_count_post_dedup`, `date_filter_applied`, `section_default_applied`, `identity_suppressed_count`. Anchor: `src/autom8_asana/api/routes/exports.py` handler function.
2. **`exports_section_default_injected` log** when `apply_active_default_section_predicate` returns `default_applied=True`.
3. **`exports_identity_rows_suppressed` log** in `filter_incomplete_identity` when `include=False`.
4. **`exports_date_filter_applied` log** in `translate_date_predicates` when `date_filter_expr is not None`.

### Risk

A regression in `_walk_predicate` visitor or date-predicate translation would surface only via 500s in production. Production-side regression detection is currently 100% reactive for the exports surface.

### Owner & Cadence

- Owner-rite: SRE
- Cadence: pre-GA (before /exports moves Phase 1 → Phase 2)
- Verification target: M-02 telos deadline 2026-06-15

---

## Instrumentation Depth

### SDK Adoption

`autom8y-telemetry` platform SDK is imported and active in 14 source files. Direct usage breakdown:

| Instrumented Surface | Mechanism | Files |
|----------------------|-----------|-------|
| Query engine | `@trace_computation` | `src/autom8_asana/query/engine.py`, `query/fetcher.py`, `query/join.py`, `query/compiler.py` |
| Query service | `@trace_computation` | `services/query_service.py` (line 559) |
| Strategy resolution | `get_tracer()` + `start_as_current_span` | `services/universal_strategy.py` (lines 177, 306) |
| API resolver route | `get_tracer()` + `start_as_current_span` | `api/routes/resolver.py` (line 351) |
| DataFrame cache | `@trace_computation("cache.get")` | `cache/integration/dataframe_cache.py` (line 234) |
| DataFrame builders | `@trace_computation("progressive.build")` | `dataframes/builders/progressive.py` (line 445) |
| Business metrics | `@trace_computation("metric.compute")` | `metrics/compute.py` (lines 19-21) |
| Lambda: cache warmer | `@instrument_lambda`, `emit_success_timestamp` | `lambda_handlers/cache_warmer.py` (lines 45, 740, 845) |
| Lambda: workflow handler | `autom8y_telemetry.aws` `instrument_lambda`, `emit_success_timestamp` | `lambda_handlers/workflow_handler.py` (lines 36-39, 95, 316, 330) |
| Payment reconciliation | `@trace_reconciliation` | `automation/workflows/payment_reconciliation/workflow.py` (line 164) |

**Instrumentation gap — exports route (OBS-EXPORTS-001)**: `api/routes/exports.py` and `api/routes/_exports_helpers.py` are LIVE on main with zero `autom8y_telemetry` span instrumentation. Verified at source_hash `8980bcd7`.

**Instrumentation gap — bridge_base (H-006)**: `src/autom8_asana/automation/workflows/bridge_base.py:191-195` documents `trace_computation` not applied with the comment "H-006 gap: trace_computation decorator is NOT available in version 0.6.1". This is the foundation for all Lambda workflow bridges. Gap remains open at source_hash `8980bcd7`.

**Uninstrumented Lambda handlers**: 10 of 13 non-shared handlers have no `autom8y_telemetry` import beyond CloudWatch via shared `emit_metric()` utility: `pipeline_stage_aggregator`, `reconciliation_runner`, `checkpoint`, `payment_reconciliation`, `insights_export`, `push_orchestrator`, `conversation_audit`, `story_warmer`, `cache_invalidate`, `timeout`.

### Auto-Instrumentation

`HTTPXClientInstrumentor().instrument()` called at startup in `api/lifespan.py:85-94`, enabling automatic W3C `traceparent` propagation on all httpx clients. Platform SDK (`autom8y-http[otel]>=0.6.0`) provides additional transport-level instrumentation via `InstrumentedTransport`. Graceful degradation: `ImportError` caught with structured warning log at `api/lifespan.py:91-94`.

### Trace Propagation

W3C Trace Context (`traceparent`) propagation confirmed active via `HTTPXClientInstrumentor`. Cross-service propagation verification not achievable from this codebase in isolation (only one service surface in scope). `autom8y_telemetry.aws`'s `instrument_lambda` wraps all Lambda handlers where applied.

### Log-Trace Correlation

Confirmed wired: `api/lifespan.py:15` imports `add_otel_trace_ids` from `autom8y_log.processors`; line 77 injects it as a structlog processor at startup. Every module using `autom8y_log.get_logger()` (the mandated logger per `pyproject.toml:295-302` import-guard rules) inherits OTel trace ID injection.

**Gap — Lambda mode**: Lambda handlers emit CloudWatch metrics but do not wire `add_otel_trace_ids` — log-trace correlation only fires in ECS mode.

**Gap — namespace bridging**: HTTP request IDs (`X-Request-ID`, UUID hex 16 chars) and SDK correlation IDs (`sdk-{ts}-{rand}`, 18 chars) coexist without bridging.

### Sampling

No sampler configuration found in-repo. No `OTEL_TRACES_SAMPLER` env var set in `.env`, `.envrc`, or any env example file. Sampling configuration fully delegated to the `autom8y-telemetry` platform SDK. Sampling rate unconfirmed at satellite level.

**Completeness**: 60% — SDK wired on ECS critical paths; /exports route uninstrumented at span level; Lambda instrumentation shallow for most handlers; `bridge_base.py` has documented TODO gap; sampling undocumented.

**Grade: D**

---

## Credential Topology Integrity

### Push Endpoint Enumeration

**Protocol 1 — OTLP** (via `autom8y-telemetry[otlp]`):
- Tuple: `(push-HTTP/OTLP, scope=unknown, auth-routing-field=unknown)` — **undeclared at satellite level**.
- Endpoint delegated entirely to platform SDK. No `OTEL_EXPORTER_OTLP_ENDPOINT` env var configured in any in-repo file.
- Auth-routing-field: unknown. The platform SDK's Grafana Cloud binding (if in use) would require `stack_id` for the OTLP HTTP gateway — but this is not declared or verified at satellite level.

**Protocol 2 — Prometheus** (via `instrument_app()` in `autom8y-api-middleware`):
- Tuple: `(scrape-pull, scope=local, auth-routing-field=N/A)`.
- Endpoint: `/metrics` (served locally by FastAPI app). No auth required on the scrape endpoint from app side; scraper identity unknown.
- No bind-time credential validation needed (pull model, no push credential).

**Protocol 3 — CloudWatch** (via `boto3.client("cloudwatch")` in `lambda_handlers/cloudwatch.py:22-28`):
- Tuple: `(vendor-native/CloudWatch, scope=namespace, auth-routing-field=IAM-role)`.
- Endpoint: `cloudwatch.{region}.amazonaws.com` (region from `AWS_REGION` or `ASANA_CACHE_S3_REGION` env var, default `us-east-1`).
- Auth: IAM role/credentials (ambient from Lambda execution role). No explicit credential field in code.
- Namespaces in use: `autom8/lambda` (default via `ASANA_CW_NAMESPACE`), `Autom8y/FreshnessProbe` (freshness CLI), `Autom8y/AsanaCacheWarmer` (DMS heartbeat), `autom8y/cache-warmer` (coalescer-side per ADR-006).

### Credential Topology Matrix Cross-Reference

No satellite-level `credential-topology-matrix.yaml` instance exists. The schema file is present at `.claude/skills/pinakes/schemas/credential-topology-matrix.schema.yaml` (framework artifact only). No instance data populates the matrix for this satellite.

**BLOCKING FINDING**: OTLP push credential topology is opaque at satellite level — entire auth-binding delegated to platform SDK. The 2-axis bifurcation between OTLP HTTP gateway auth-routing-field (`stack_id`) and direct signal-instance push auth-routing-field (`signal_instance_id`) is not declared or verified locally.

### Bind-Time Fixture

No bind-time fixture validates credential tuples before first runtime invocation. All three protocols bind lazily at first I/O:
- CloudWatch: `_get_cloudwatch_client()` lazy-init pattern (`lambda_handlers/cloudwatch.py:21-28`).
- Prometheus: bound at `instrument_app()` call (startup), no credential required.
- OTLP: bound by platform SDK on first span export; timing and auth validation opaque locally.

### Bake-At-Apply Coupling

OTLP credentials are bake-at-apply via the platform SDK (credentials likely embedded in ECS task definition or Lambda environment at deploy time). No rotation procedure documented at satellite level. CloudWatch auth is IAM-role-bound (no rotation concern for ambient role; rotation would require IAM policy update external to this codebase).

**Completeness**: 30%. **Grade: F**.

---

## Signal Pipe Contracts

| Signal Class | Producer SDK | Wire Protocol | Endpoint | Consumer Backend |
|---|---|---|---|---|
| Traces | `autom8y_telemetry` (OTel) | OTLP push-HTTP | Unknown (SDK-managed) | Unknown (OTLP-compatible) |
| Metrics (ECS) | `prometheus_client` | HTTP scrape-pull | `/metrics` (local, served by app) | Unknown scraper |
| Metrics (Lambda) | CloudWatch via `boto3` | vendor-native push | `cloudwatch.{region}.amazonaws.com` | AWS CloudWatch |
| Metrics (Lambda DMS) | `autom8y_telemetry.aws` `emit_success_timestamp` | vendor-native | AWS CloudWatch | AWS CloudWatch |
| Logs | `autom8y_log` + structlog | stdout (structured JSON) | stdout capture | Unknown (ECS log driver / Lambda CloudWatch Logs) |
| Profiles | None detected | — | — | — |

### Pipeline Topology

**ECS (API) mode**:
- Traces → OTel SDK → OTLP push → unknown backend (1-hop, no local collector confirmed)
- Metrics → `prometheus_client` → `/metrics` scrape-pull → unknown Prometheus-compatible scraper (1-hop)
- Logs → stdout → ECS log driver → unknown aggregation backend

**Lambda mode**:
- Metrics → `emit_metric()` → `boto3.client("cloudwatch").put_metric_data()` → AWS CloudWatch (direct 1-hop)
- DMS Heartbeat → `emit_success_timestamp(DMS_NAMESPACE)` → AWS CloudWatch (direct 1-hop)
- Traces → `instrument_lambda` → unknown (OTLP or X-Ray via platform SDK; opaque at satellite)
- Logs → stdout → Lambda CloudWatch Logs (direct capture)

### Auth Surface Per Hop

- OTLP push: bearer auth or header-routed — auth-routing-field unknown
- Prometheus scrape: no auth on producer side
- CloudWatch: IAM ambient role — no bearer token
- Lambda CloudWatch Logs: IAM ambient — no bearer token

### SCAR Log

No documented signal-pipe contract-drift incidents (404/401 pipeline failures). No SCAR log for signal-pipe failures exists at this satellite.

**Completeness**: 45%. **Grade: F**.

---

## Metric Inventory

### ECS/Prometheus Custom Metrics (`src/autom8_asana/api/metrics.py`)

| Metric Name | Type | Labels | Description |
|---|---|---|---|
| `autom8y_asana_dataframe_build_duration_seconds` | Histogram | `entity_type` | DataFrame build latency; buckets: 0.5s to 120s |
| `autom8y_asana_dataframe_cache_operations_total` | Counter | `entity_type`, `tier`, `result` | Cache ops by tier (memory/s3) and result (hit/miss/error) |
| `autom8y_asana_dataframe_rows_cached` | Gauge | `entity_type` | Current row count in most recent cached DataFrame |
| `autom8y_asana_dataframe_swr_refreshes_total` | Counter | `entity_type`, `result` | Stale-while-revalidate refresh attempts |
| `autom8y_asana_dataframe_circuit_breaker_state` | Gauge | `project_gid` | Circuit breaker state (0=closed, 1=open, 2=half_open) |
| `autom8y_asana_api_calls_total` | Counter | `method`, `path_pattern`, `status_code` | Asana API calls by endpoint pattern and HTTP status |
| `autom8y_asana_api_call_duration_seconds` | Histogram | `method`, `path_pattern` | Asana API call duration; buckets: 0.1s to 10s |

Platform-level Prometheus metrics (`autom8y_http_*`) provided by `instrument_app()` and supplemented by domain metrics above.

### CloudWatch Lambda Metrics (`src/autom8_asana/lambda_handlers/`)

**Namespace `autom8/lambda`** (default via `ASANA_CW_NAMESPACE` env var, dimensions: `environment`):

| Metric Name | Emission Source | Notes |
|---|---|---|
| `WarmSuccess` | `cache_warmer.py:473-477` | Per entity type warmed successfully; dimension `entity_type` |
| `WarmDuration` | `cache_warmer.py:478-483` | Per entity warm duration in milliseconds |
| `WarmFailure` | `cache_warmer.py:501-504`, `566-569` | Per entity type failed warm |
| `CheckpointResumed` | `cache_warmer.py:358` | Count=1 when resume-from-checkpoint activates |
| `CheckpointSaved` | `cache_warmer.py:422`, `525`, `545`, `580` | Count=1 per checkpoint write |

**Namespace `Autom8y/AsanaCacheWarmer`** (DMS heartbeat):

| Metric Name | Emission Source | Notes |
|---|---|---|
| `emit_success_timestamp` | `cache_warmer.py:845` | Dead-man's-switch; fires only on full successful warm |

**Namespace `Autom8y/FreshnessProbe`** (freshness CLI, `src/autom8_asana/metrics/cloudwatch_emit.py`):

| Metric Name | Alarmed? | Dimensions | Notes |
|---|---|---|---|
| `MaxParquetAgeSeconds` | YES (ALERT-1, ALERT-2) | `metric_name`, `project_gid` | Primary freshness SLI |
| `ForceWarmLatencySeconds` | NO (alarmable in principle) | `metric_name`, `project_gid` | FLAG-1 boundary latency; emitted only on `--force-warm --wait` |
| `SectionCount` | NO | `metric_name`, `project_gid` | Parquet count per prefix |
| `SectionAgeP95Seconds` | NO | `metric_name`, `project_gid` | P95 section age |
| `SectionCoverageDelta` | FORBIDDEN (C-6 constraint) | `metric_name`, `project_gid` | Informational only; `c6_guard_check()` raises `C6ConstraintViolation` if wired to alarm |

**C-6 mechanical guard**: `metrics/cloudwatch_emit.py:88-106` implements `c6_guard_check(metric_name)` — raises `C6ConstraintViolation` when alarm-wiring code targets `SectionCoverageDelta`. `ALARMED_METRICS` frozenset explicitly excludes `SectionCoverageDelta`.

### Business Metrics Registry (`src/autom8_asana/metrics/`)

`MetricRegistry` singleton (`metrics/registry.py`) with lazy-loaded definitions from `metrics/definitions/` (offer, lifecycle). Metric definitions accessed via `MetricRegistry().get_metric(name)`. Current registered metrics include `active_mrr` and related offer-level aggregations.

---

## Trace Inventory

### OTel Spans (via `autom8y_telemetry`)

| Span Name | Decorator/Method | File | Notes |
|---|---|---|---|
| `metric.compute` | `@trace_computation` | `metrics/compute.py:19` | `record_dataframe_shape=True`, `df_param="df"` |
| `cache.get` | `@trace_computation` | `cache/integration/dataframe_cache.py:234` | — |
| `progressive.build` | `@trace_computation` | `dataframes/builders/progressive.py:445` | — |
| `predicate.compile` | `@trace_computation` | `query/compiler.py:164` | — |
| `entity.query_rows` | `@trace_computation` | `query/engine.py:76` | `record_dataframe_shape=True` |
| `entity.query_aggregate` | `@trace_computation` | `query/engine.py:242` | — |
| `data.fetch` | `@trace_computation` | `query/fetcher.py:40` | — |
| `join.*` | `@trace_computation` | `query/join.py:90` | — |
| `query_service.*` | `@trace_computation` | `services/query_service.py:559` | — |
| `strategy.resolution.resolve` | `get_tracer()` + `start_as_current_span` | `services/universal_strategy.py:177` | Manual span |
| `strategy.resolution.resolve_group` | `get_tracer()` + `start_as_current_span` | `services/universal_strategy.py:306` | Manual span |
| `(resolver route)` | `get_tracer()` + `start_as_current_span` | `api/routes/resolver.py:351` | Manual span |
| `payment_reconciliation.process_entity` | `@trace_reconciliation` | `automation/workflows/payment_reconciliation/workflow.py:164` | — |

**Gap — exports handler**: No spans for `POST /v1/exports` or `POST /api/v1/exports` (OBS-EXPORTS-001).

**Gap — bridge_base**: `src/autom8_asana/automation/workflows/bridge_base.py:191-195` has documented TODO; all Lambda workflow bridges uninstrumented at bridge layer.

### HTTP Auto-Instrumentation

`opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor().instrument()` active at ECS startup (`api/lifespan.py:85`). Propagates W3C `traceparent` on all outbound httpx calls automatically.

---

## Log Inventory

### SDK

`autom8y_log` SDK (`autom8y-log>=0.5.6`) is the mandated and enforced logging primitive. Import-guard in `pyproject.toml:295-302` bans `loguru`, `structlog`, `logging`, `logging.getLogger` — any import triggers a lint error.

### Configuration

`src/autom8_asana/core/logging.py` — `configure()` function initializes `LogConfig(backend="structlog", level=..., format="auto", intercept_stdlib=True)`. Auto-format: colored console when TTY (development), JSON when no TTY (CI/production). `intercept_stdlib=True` reroutes all third-party stdlib logging through the structured pipeline.

### OTel Trace Correlation Injection

`autom8y_log.processors.add_otel_trace_ids` injected at startup in `api/lifespan.py:77`. Injects `trace_id` and `span_id` fields into every log record when executing inside an active OTel span.

**Gap — Lambda mode**: Lambda handlers use `autom8y_log.get_logger()` but the startup path does not call `configure(additional_processors=[add_otel_trace_ids])`. Log-trace correlation is ECS-mode only.

### Sensitive Data Filtering

`_filter_sensitive_data` processor injected alongside `add_otel_trace_ids` in `api/lifespan.py:77`. Filters sensitive fields from structured log output.

---

## SLO Catalog

### Source

Defined in `.ledge/specs/cache-freshness-observability.md` (status: draft, authored 2026-04-27). These SLOs cover the Lambda cache-warmer / freshness-probe surface, **not** the ECS/FastAPI API surface. No API-surface SLOs exist.

### SLO-1: ParquetMaxAgeSLO (Primary Freshness)

- **SLI**: `MaxParquetAgeSeconds` (from `metrics/freshness.py:250` — age of oldest S3 parquet under prefix)
- **Target**: 95% of CLI invocations over rolling 7-day window report `MaxParquetAgeSeconds < 21600` (6h)
- **Window**: Rolling 7-day
- **Denominator**: CLI invocations (frequency: O(1-10/day), estimated; actual cadence unvalidated)
- **Error budget**: 5% — ≈1.75 stale readings/week at O(5/day) cadence
- **SLO tier**: Operational (internal tooling; no external SLA)
- **DEF-3 anchor**: `active_mrr` is internal/operational; if reclassified investor-grade, target tightens to 99% and threshold may drop to 1h

### SLO-2: WarmSuccessRateSLO (Warmer Availability)

- **SLI**: `WarmSuccessRate` for `entity_type=offer` = `sum(WarmSuccess) / (sum(WarmSuccess) + sum(WarmFailure))`
- **Target**: >= 95% over rolling 7-day window
- **Emission anchors**: `cache_warmer.py:473` (WarmSuccess), `cache_warmer.py:501` (WarmFailure)
- **DEF-2 dependency**: Warmer schedule cadence unknown (AP-1 gap); SLO's practical meaning depends on P3 schedule confirmation
- **SLO tier**: Operational

### SLO-3: WarmHeartbeatSLO (Dead-Man's-Switch)

- **SLI**: Presence of `emit_success_timestamp("Autom8y/AsanaCacheWarmer")` at `cache_warmer.py:845`
- **Target**: At least 1 successful DMS heartbeat in every rolling 24-hour window
- **SLO tier**: Operational (highest urgency — 24h absence = full missed warmer cycle)

### Open Questions

- **Freshness SLO for ECS/API**: No API-surface SLOs defined (no latency, availability, or error-rate targets for any FastAPI route).
- **Exports SLO**: Zero SLO targets for the exports surface (OBS-EXPORTS-001).
- **Warmer cadence (DEF-2)**: Schedule not documented; SLO-2 and SLO-3 have ambiguous practical thresholds until confirmed.
- **Burn-rate alerting**: No multi-window multi-burn-rate alerts configured. Single-threshold CloudWatch alarms only (ALERT-1, ALERT-2).

---

## Alert Rules

### CloudWatch Alarms (from `.ledge/specs/cache-freshness-observability.md §3`)

These alarms are specified as desired-state in the observability spec. Whether they are deployed as live CloudWatch alarm resources is unverified (no IaC found in-repo). Evidence: spec only.

**ALERT-1: Freshness Breach — WARNING**
- Condition: `MaxParquetAgeSeconds` > 21600 (6h), any single invocation
- Namespace: `Autom8y/FreshnessProbe`; Statistic: Maximum; Period: 300s; Evaluation periods: 1
- Severity: P2; Channel: Slack `#autom8y-ops`; No PagerDuty page
- Missing data treatment: `notBreaching`

**ALERT-2: Sustained Freshness Breach — CRITICAL**
- Condition: `MaxParquetAgeSeconds` > 21600 sustained for 30 minutes
- Severity: P1; Channel: PagerDuty on-call page
- (Per runbook `cache-freshness-runbook.md` §Stale-1)

**DMS-1: Warmer Heartbeat Absent — CRITICAL**
- Condition: No `emit_success_timestamp` in rolling 24h window in `Autom8y/AsanaCacheWarmer`
- Severity: P1; Leading indicator of freshness SLO-1 breach

### Runbook Linkage

| Alert | Runbook | Linkage Status |
|---|---|---|
| ALERT-1 + ALERT-2 | `.ledge/specs/cache-freshness-runbook.md` §Stale-1 | Documented in spec — informal prose link |
| DMS-1 | `.ledge/specs/cache-freshness-runbook.md` §DMS-1 | Documented in spec — informal prose link |
| (ECS API alerts) | `docs/runbooks/RUNBOOK-pipeline-automation.md`, `RUNBOOK-cache-troubleshooting.md`, `RUNBOOK-detection-troubleshooting.md` | No alert rule definitions exist — runbooks not machine-linked |

### Alert Coverage Gaps

- No Prometheus alerting rules YAML (no `PrometheusRule` resource, no AlertManager config)
- No CloudWatch alarm IaC (no CDK, CloudFormation, or Terraform in-repo)
- No alert rules for ECS/API surface (no latency, error rate, or circuit breaker alerts)
- No alert-to-runbook linkage automation (runbooks exist as prose; no annotation pointing from alert name to runbook URL)
- No on-call rotation documentation or ownership assignment

---

## Dashboard Surface

No Grafana dashboards, CloudWatch dashboards, or other dashboard definitions found in-repo. All observability tooling visualization (if any) is external to this satellite.

---

## Credential Topology

### CloudWatch IAM

- Lambda handlers: ambient IAM execution role (`lambda_handlers/cloudwatch.py:22-28` uses `boto3.client("cloudwatch")` without explicit credential configuration — relies on Lambda execution role ambient creds)
- Region resolution: `AWS_REGION` env var fallback to `ASANA_CACHE_S3_REGION`, default `us-east-1` (`metrics/cloudwatch_emit.py:116-117`)
- Namespace configuration: `ASANA_CW_NAMESPACE` env var (default `autom8/lambda`) + `ASANA_CW_ENVIRONMENT` env var (default `staging`) via `ObservabilitySettings` in `settings.py:582-613`

### OTLP Endpoint

- Endpoint: opaque — delegated to `autom8y-telemetry` platform SDK
- No `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, or `OTEL_SERVICE_NAME` found in any in-repo configuration file
- Auth-routing-field: unknown at satellite level

### Prometheus Scraper

- Endpoint: `/metrics` (local, served by FastAPI app on ECS port 8000 or as configured)
- No scraper configuration in-repo; scraper identity unknown

---

## Instrumentation Gaps Registry

| ID | Surface | Severity | Deadline | Status |
|---|---|---|---|---|
| OBS-EXPORTS-001 | `api/routes/exports.py`, `api/routes/_exports_helpers.py` | P2 | 2026-06-15 (38 days) | OPEN — unaddressed in SHA 8980bcd7 |
| H-006 | `src/autom8_asana/automation/workflows/bridge_base.py:191-195` | P3 | Unknown | OPEN — `trace_computation` not available in 0.6.1; inline TODO persists at SHA 8980bcd7 |
| LAMBDA-OBS-001 | 10 of 13 Lambda handlers (no `autom8y_telemetry` span instrumentation) | P3 | None declared | OPEN — CloudWatch only |
| LOG-TRACE-LAMBDA | Lambda handlers: `add_otel_trace_ids` not wired | P3 | None declared | OPEN |
| SAMPLING-UNDOC | No `OTEL_TRACES_SAMPLER` env var configured | P3 | None declared | OPEN |
| SLO-API-SURFACE | Zero ECS/API SLOs defined | P2 | None declared | OPEN |
| CRED-TOPOLOGY-MATRIX | No credential-topology-matrix instance | P2 | None declared | OPEN — schema exists, no instance |
| OTLP-ENDPOINT-OPACITY | OTLP push endpoint and auth-routing-field opaque | P2 | None declared | OPEN |

---

## Knowledge Gaps

1. **OTLP backend identity**: Which observability backend does `autom8y-telemetry[otlp]` push to? Endpoint URL, auth-routing-field, and push credential opaque at satellite level.
2. **Prometheus scraper identity**: What scrapes `/metrics`? No scraper configuration in-repo.
3. **Log aggregation backend**: Where do ECS stdout logs go after the ECS log driver? What aggregation or indexing backend?
4. **Lambda trace backend**: `instrument_lambda` — emits to CloudWatch X-Ray, Grafana Tempo via OTLP, or other? Not declared at satellite level.
5. **Warmer schedule cadence (DEF-2)**: Lambda cache-warmer invocation frequency not documented (AP-1 gap). Affects practical interpretation of SLO-2 and SLO-3 thresholds.
6. **CloudWatch alarm deployment status**: ALERT-1, ALERT-2, DMS-1 are specified in observability spec but no IaC creates them. Live alarm state unverified.
7. **Grafana dashboard existence**: No dashboard definitions in-repo. External tooling state unknown.
8. **On-call ownership**: No escalation policy or rotation ownership documented for any alert.
9. **OBS-EXPORTS-001 timeline**: SRE sprint timeline for instrumentation implementation not confirmed beyond pre-GA deadline 2026-06-15 (38 days as of 2026-05-08).

```metadata
confidence: 0.84
observation_mode: incremental
source_hash: "8980bcd7"
prior_source_hash: "20ef7952"
delta_obs_relevant: false
obs_exports_001_status: OPEN
obs_exports_001_deadline_days_remaining: 38
h006_status: OPEN
lambda_uninstrumented_count: 10
lambda_total_non_shared: 13
autom8y_core_version_bump_obs_impact: none
grades:
  instrumentation_depth: D
  credential_topology_integrity: F
  signal_pipe_contracts: F
  slo_sli_maturity: D
  alerting_runbook_coverage: D
overall_grade: F
weighted_score: 45.25
criteria_weights:
  instrumentation_depth: 0.25
  credential_topology_integrity: 0.25
  signal_pipe_contracts: 0.20
  slo_sli_maturity: 0.20
  alerting_runbook_coverage: 0.10
score_components:
  instrumentation_depth: 65
  credential_topology_integrity: 30
  signal_pipe_contracts: 45
  slo_sli_maturity: 40
  alerting_runbook_coverage: 45
score_calculation:
  - "65 x 0.25 = 16.25"
  - "30 x 0.25 = 7.50"
  - "45 x 0.20 = 9.00"
  - "40 x 0.20 = 8.00"
  - "45 x 0.10 = 4.50"
  - "total: 45.25 → F"
change_from_prior:
  source_hash: "20ef7952 → 8980bcd7"
  obs_exports_001: "still OPEN — zero instrumentation hits at HEAD; deadline countdown updated to 38 days"
  h006: "still OPEN — bridge_base.py:191-195 TODO persists"
  autom8y_core_bump: "autom8y-core>=4.2.0 lower-bound lift (f6864435) carries no observability surface; no grade impact"
  overall: "no change — F(45.25%) maintained"
```
