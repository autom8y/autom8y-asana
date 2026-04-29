---
domain: obs
generated_at: "2026-04-29T14:30Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "6b303485"
confidence: 0.82
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Observability

**Vendor Detection**: Multi-protocol stack detected.

- **Protocol 1**: OTel SDK (`autom8y-telemetry[otlp]>=0.6.1` + `opentelemetry-instrumentation-httpx>=0.42b0`) — push-HTTP via OTLP
- **Protocol 2**: Prometheus (`prometheus_client` via `create_fleet_app`/`instrument_app`) — scrape-pull, served via `/metrics`
- **Protocol 3**: CloudWatch (`boto3.client("cloudwatch")`) — vendor-native push, Lambda mode only
- **Deployment modes**: ECS/FastAPI (Prometheus + OTel), Lambda (CloudWatch + `autom8y_telemetry.aws`)

---

## OBS-EXPORTS-001: Exports Route Instrumentation Gap (P2)

**Status**: OPEN | **Severity**: P2 | **Pre-GA Deadline**: 2026-06-15

### Anchor

- `src/autom8_asana/api/routes/exports.py:91` — `logger = get_logger(__name__)` (log correlation only)
- `src/autom8_asana/api/routes/exports.py` — zero `metric.`, `tracer.`, `counter.`, `histogram.`, or `span.` calls (grep count: 0, verified at source_hash `6b303485`)
- `src/autom8_asana/api/routes/_exports_helpers.py` — three logger calls (column-source warning, identity-suppression warning, no-matching-columns warning) but zero metric/span calls
- Inherited surface: `add_otel_trace_ids` OTel processor wired in `api/lifespan.py` (log correlation only — no child span wraps the exports handler)

### Symptom

The `/v1/exports` and `/api/v1/exports` routes are LIVE on `main` (post-PR #38, merge commit `80256049`) carrying Phase 1 of `project-asana-pipeline-extraction` (telos deadline 2026-05-11). The route has:

- 0 metric counters/histograms (no `request_duration_seconds`, no `predicate_split_outcome`, no `format_negotiation_fallback_total`, no `identity_suppressed_count`)
- 0 explicit tracer spans (only auto-instrumentation via OTel FastAPI middleware — no child spans within handler)
- 0 SLO targets defined
- 0 alert rules

### Root Cause

Phase 1 prioritized correctness (P1-C-04 frozen ranges, behavior-preserving refactor T-04b) over observability. The hygiene rite explicitly deferred obs work to the SRE rite via handoff `.sos/wip/handoffs/HANDOFF-hygiene-to-sre-exports-obs-2026-04-28.md`.

### Required Instrumentation (per SRE handoff — DESIRED state, not current)

1. **Add request span to the `/exports` handler** — emit `exports_request_complete` with fields: `entity_type`, `row_count_pre_dedup`, `row_count_post_dedup`, `date_filter_applied` (bool), `section_default_applied` (bool), `identity_suppressed_count` (int). Anchor: `src/autom8_asana/api/routes/exports.py` handler function.

2. **Add `exports_section_default_injected` log** in the handler when `apply_active_default_section_predicate` returns `default_applied=True`. Anchor: `src/autom8_asana/api/routes/exports.py` (call site for `apply_active_default_section_predicate`).

3. **Add `exports_identity_rows_suppressed` log** in `filter_incomplete_identity` when `include=False` — emit the count of suppressed rows. Anchor: `src/autom8_asana/api/routes/_exports_helpers.py` (`filter_incomplete_identity` function).

4. **Add `exports_date_filter_applied` log** in `translate_date_predicates` when `date_filter_expr is not None` — emit field name and operator type. Anchor: `src/autom8_asana/api/routes/exports.py` (`translate_date_predicates` function).

### Risk

A regression in `_walk_predicate` visitor (commit `d9abbc1f`) or the date-predicate translation in `exports.py:translate_date_predicates` would surface only via 500s in production, not via SLO burn alerts. The eunomia rite's CHANGE-001 already surfaced one such latent bug (SCAR-DISCRIMINATOR-001) — production-side regression detection is currently 100% reactive for the exports surface.

### Owner & Cadence

- Owner-rite: SRE
- Cadence: pre-GA (before /exports moves from Phase 1 to Phase 2)
- Verification: post-instrumentation, M-02 telos deadline 2026-06-15

---

## Instrumentation Depth

### SDK Adoption

The `autom8y-telemetry` platform SDK is initialized in 14 source files. Direct usage breakdown:

| Instrumented Surface | Mechanism | Files |
|----------------------|-----------|-------|
| Query engine | `@trace_computation` | `src/autom8_asana/query/engine.py`, `query/fetcher.py`, `query/join.py`, `query/compiler.py` |
| Services | `get_tracer()` + `@trace_computation` | `services/query_service.py`, `services/universal_strategy.py` |
| API resolver route | `get_tracer()` | `api/routes/resolver.py` |
| DataFrame cache | `@trace_computation("cache.get")` | `cache/integration/dataframe_cache.py` |
| DataFrame builders | `@trace_computation("progressive.build")` | `dataframes/builders/progressive.py` |
| Business metrics | `trace_computation` | `metrics/compute.py` |
| Lambda: cache warmer | `instrument_lambda`, `emit_success_timestamp` | `lambda_handlers/cache_warmer.py` |
| Lambda: workflow handler | `autom8y_telemetry.aws` | `lambda_handlers/workflow_handler.py` |
| Payment reconciliation | `trace_reconciliation` | `automation/workflows/payment_reconciliation/workflow.py` |

**New route surface — instrumentation gap (OBS-EXPORTS-001)**: The Phase 1 exports route (`api/routes/exports.py` and helper `_exports_helpers.py`) is LIVE on main post-PR #38 (commit `80256049`). These files use `autom8y_log.get_logger()` for structured logging (which receives OTel trace correlation via the lifespan-injected `add_otel_trace_ids` processor) but have **zero direct `autom8y_telemetry` span instrumentation** — no `@trace_computation`, no `get_tracer()`, no manual span creation. The two export routes (`POST /api/v1/exports`, `POST /v1/exports`) are uninstrumented at the span level. Verified: `grep -c 'metric\.\|tracer\.\|counter\.\|histogram\.\|span\.'` returns 0 at `exports.py` and `_exports_helpers.py`.

**Known instrumentation gap — bridge_base**: `automation/workflows/bridge_base.py:191-195` documents `trace_computation` not applied (not yet available in version `0.6.1`). The bridge base (foundation for all Lambda workflow bridges) is uninstrumented.

**Uninstrumented lambda handlers**: 10 of 13 non-shared handlers have no `autom8y_telemetry` import beyond CloudWatch via shared `emit_metric()` utility: `pipeline_stage_aggregator`, `reconciliation_runner`, `checkpoint`, `payment_reconciliation`, `insights_export`, `push_orchestrator`, `conversation_audit`, `story_warmer`, `cache_invalidate`, `timeout`.

### Auto-Instrumentation

`HTTPXClientInstrumentor().instrument()` called at startup in `api/lifespan.py`, enabling automatic W3C `traceparent` propagation on all httpx clients. Platform SDK (`autom8y-http[otel]>=0.6.0`) provides additional transport-level instrumentation via `InstrumentedTransport`.

Graceful degradation: `ImportError` on `opentelemetry.instrumentation.httpx` caught with structured warning log at `api/lifespan.py:91-94`.

### Trace Propagation

W3C Trace Context (`traceparent`) propagation confirmed via `HTTPXClientInstrumentor`. Cross-service propagation verification not achievable from this codebase alone (only one service surface in scope).

### Log-Trace Correlation

Confirmed wired: `api/lifespan.py` injects `add_otel_trace_ids` as a structlog processor at startup. The new exports route uses `autom8y_log.get_logger()` at `exports.py:91` and inherits this correlation when executed inside a FastAPI request span. However, no manual `get_tracer()` span wraps the exports handler itself, so correlation depth depends entirely on the parent FastAPI middleware span.

**Gap**: Log-trace correlation only fires for HTTP API path (ECS mode). Lambda handlers emit CloudWatch metrics but do not wire `add_otel_trace_ids`.

**Namespace separation**: HTTP request IDs (UUID hex 16 chars, `X-Request-ID`) and SDK correlation IDs (`sdk-{ts}-{rand}` 18 chars) coexist without bridging.

### Sampling

No sampler configuration found. OTLP sampling fully delegated to the `autom8y-telemetry` SDK. No `OTEL_TRACES_SAMPLER` env var set in `.env`, `.envrc`, or env example file. Sampling rate unconfirmed at satellite level.

**Completeness**: 60% — SDK wired on ECS critical paths; /exports route (now LIVE on main) uninstrumented at span level; Lambda instrumentation shallow; `bridge_base.py` documented TODO gap; sampling undocumented. Post-PR38 adds more uninstrumented critical surface.

**Grade: D**

---

## Credential Topology Integrity

### Push Endpoint Enumeration

**Protocol 1 — OTLP** (via `autom8y-telemetry[otlp]`): Endpoint delegated entirely to platform SDK. No `OTEL_EXPORTER_OTLP_ENDPOINT` env var configured. Auth-routing-field unknown. Tuple: `(push-HTTP/OTLP, scope=unknown, auth-routing-field=unknown)` — **undeclared at satellite level**.

**Protocol 2 — Prometheus** (via `instrument_app()` in `autom8y-api-middleware`): Scrape-pull at `/metrics`. Tuple: `(scrape-pull, scope=local, auth-routing-field=N/A)`.

**Protocol 3 — CloudWatch** (via `boto3.client("cloudwatch")`): Endpoint `cloudwatch.{region}.amazonaws.com`. Auth via IAM role/credentials. Namespace: `ASANA_CW_NAMESPACE` env var (default: `autom8y/lambda`). Tuple: `(vendor-native/CloudWatch, scope=namespace, auth-routing-field=IAM-role)`.

### Credential Topology Matrix Cross-Reference

No satellite-level `credential-topology-matrix.yaml` exists. Schema file present as framework artifact under `.claude/skills/pinakes/schemas/`, but no instance data.

**BLOCKING FINDING**: OTLP push credential topology is opaque at satellite level — entire auth-binding delegated to platform SDK.

### Bind-Time Fixture

No bind-time fixture validates credential tuples before first runtime invocation. All three protocols bind lazily.

**Completeness**: 30%. **Grade: F**.

---

## Signal Pipe Contracts

| Signal Class | Producer SDK | Wire Protocol | Endpoint | Consumer Backend |
|---|---|---|---|---|
| Traces | `autom8y_telemetry` (OTel) | OTLP push-HTTP | Unknown (SDK-managed) | Unknown (OTLP-compatible) |
| Metrics (ECS) | `prometheus_client` | HTTP scrape-pull | `/metrics` (local) | Unknown |
| Metrics (Lambda) | CloudWatch via boto3 | vendor-native push | `cloudwatch.{region}.amazonaws.com` | AWS CloudWatch |
| Metrics (Lambda 2) | `autom8y_telemetry.aws` | vendor-native | AWS-mediated | AWS CloudWatch |
| Logs | `autom8y_log` + structlog | stdout (structured JSON) | Stdout capture | Unknown |
| Profiles | None detected | — | — | — |

### Pipeline Topology

**ECS (API) mode**: traces → OTLP exporter → unknown backend; metrics → `/metrics` → unknown scraper; logs → stdout → ECS log driver → unknown aggregation.

**Lambda mode**: metrics → boto3 CloudWatch direct push; traces → `instrument_lambda` → OTLP or X-Ray (unclear).

### SCAR Log

No documented contract-drift incidents (404/401 pipeline failures). No SCAR log for signal-pipe failures exists.

**Completeness**: 45%. **Grade: F**.

---

## SLO/SLI Maturity

No SLO definitions found in any source file, YAML, documentation, or knowledge file. Search across `SLO`, `error_budget`, `burn_rate`, `availability.*target` returned zero results.

### Metric Surface Available for SLI Construction

- `autom8y_asana_dataframe_build_duration_seconds` (`api/metrics.py:20`) — latency SLI candidate
- `autom8y_asana_dataframe_cache_operations_total` (`api/metrics.py:27`) — freshness/availability SLI candidate
- `autom8y_asana_dataframe_rows_cached` (`api/metrics.py:33`) — capacity SLI candidate
- `autom8y_asana_dataframe_swr_refreshes_total` (`api/metrics.py:39`) — freshness SLI candidate
- `autom8y_asana_dataframe_circuit_breaker_state` (`api/metrics.py:45`) — availability SLI candidate
- `autom8y_asana_api_calls_total` (`api/metrics.py:55`) — availability SLI candidate
- `autom8y_asana_api_call_duration_seconds` (`api/metrics.py:61`) — latency SLI candidate
- CloudWatch namespace `autom8y/lambda` — Lambda success/failure rate
- **GAP**: Zero metric candidates for `/exports` route (OBS-EXPORTS-001 — no counters/histograms defined)

No SLO statements declared, no measurement windows defined, no denominators specified, no burn-rate alerts, no error-budget policy.

**Completeness**: 5%. **Grade: F**.

---

## Alerting & Runbook Coverage

### Alert Rules

No alert rule definitions found (no Prometheus alerting rules YAML, no AlertManager config, no CloudWatch alarms in code). Runbooks contain informal threshold guidance in prose.

### Runbook Inventory

`docs/runbooks/`:
- `RUNBOOK-pipeline-automation.md` — pipeline escalation (P2)
- `RUNBOOK-cache-troubleshooting.md` — cache hit rate, SWR staleness
- `RUNBOOK-detection-troubleshooting.md` — detection failure rate
- `RUNBOOK-savesession-debugging.md` — save operation duration
- `RUNBOOK-rate-limiting.md`, `RUNBOOK-batch-operations.md`, `RUNBOOK-business-model-navigation.md`

Development-operation runbooks in `runbooks/atuin/` (bootstrap, auth, API operations, troubleshooting).

**Gap**: No alert-to-runbook linkage. No on-call escalation policy or rotation ownership documented.

**Completeness**: 20%. **Grade: F**.

---

## Overall Observability Grade

**Grade: F (35.8%)**

Weighted average:
- Instrumentation Depth: D (65%) × 25% = 16.25
- Credential Topology Integrity: F (30%) × 25% = 7.50
- Signal Pipe Contracts: F (45%) × 20% = 9.00
- SLO/SLI Maturity: F (5%) × 20% = 1.00
- Alerting & Runbook Coverage: F (20%) × 10% = 2.00
- **Total: 35.75% → F**

**Why no improvement post-PR #38**: The exports route merge (commit `80256049`) added more uninstrumented critical surface (`exports.py`, `_exports_helpers.py`) with no accompanying instrumentation. The grade is unchanged from source_hash `8c58f930` and may be considered slightly worse given that a new LIVE route now operates in a zero-observability posture.

**Post-OBS-EXPORTS-001 discharge target**: D or better — when the 4 SRE actions complete (request span, section-default log, identity-suppression log, date-filter log), the instrumentation depth score rises to approximately 70%, shifting the weighted average to approximately 40-45%.

---

## Knowledge Gaps

1. **OTLP backend identity**: Which observability backend does `autom8y-telemetry[otlp]` push to? Credential-binding surface, endpoint URL, auth-routing-field, push protocol opaque at satellite level.
2. **Prometheus scraper identity**: What scrapes `/metrics`? No scraper configuration in-repo.
3. **Log aggregation backend**: Where do stdout logs go after ECS log driver?
4. **Sampling configuration**: No `OTEL_TRACES_SAMPLER` configured at satellite level.
5. **Lambda trace backend**: `autom8y_telemetry.aws`'s `instrument_lambda` — emits to CloudWatch X-Ray or OTLP?
6. **OBS-EXPORTS-001**: New `api/routes/exports.py` and `_exports_helpers.py` (LIVE on main post-PR #38) have zero span-level instrumentation. Structured logs correlate with parent span only. See named incident above.
7. **Bridging gap**: `automation/workflows/bridge_base.py:191-195` `trace_computation` TODO has no tracking issue or ticket reference.
8. **Credential topology matrix instance**: No `.sos/` or `.know/` credential-topology-matrix YAML for this satellite exists.
9. **SLO definitions**: No SLOs, SLIs, or error-budget policy exist.
10. **Alert rules**: No machine-actionable alert definitions exist.
11. **On-call documentation**: No on-call rotation, escalation policy, or ownership documentation exists.
12. **Exports metric name catalog**: No metric names defined for the exports surface (`exports_request_complete`, `exports_identity_suppressed_count`, etc. are desired state only — not yet implemented).
