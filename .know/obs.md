---
domain: obs
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
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

## Instrumentation Depth

### SDK Adoption

The `autom8y-telemetry` platform SDK is initialized in 14 source files. Direct usage breakdown:

| Instrumented Surface | Mechanism | Files |
|----------------------|-----------|-------|
| Query engine | `@trace_computation` | `query/engine.py`, `query/fetcher.py`, `query/join.py`, `query/compiler.py` |
| Services | `get_tracer()` + `@trace_computation` | `services/query_service.py`, `services/universal_strategy.py` |
| API resolver route | `get_tracer()` | `api/routes/resolver.py` |
| DataFrame cache | `@trace_computation("cache.get")` | `cache/integration/dataframe_cache.py` |
| DataFrame builders | `@trace_computation("progressive.build")` | `dataframes/builders/progressive.py` |
| Business metrics | `trace_computation` | `metrics/compute.py` |
| Lambda: cache warmer | `instrument_lambda`, `emit_success_timestamp` | `lambda_handlers/cache_warmer.py` |
| Lambda: workflow handler | `autom8y_telemetry.aws` | `lambda_handlers/workflow_handler.py` |
| Payment reconciliation | `trace_reconciliation` | `automation/workflows/payment_reconciliation/workflow.py` |

**Known instrumentation gap**: `automation/workflows/bridge_base.py` documents a TODO: `trace_computation` not applied (not yet available in version `0.6.1`). The bridge base (foundation for all Lambda workflow bridges) is uninstrumented.

**Uninstrumented lambda handlers**: 10 of 13 non-shared handlers have no `autom8y_telemetry` import beyond CloudWatch via shared `emit_metric()` utility: `pipeline_stage_aggregator.py`, `reconciliation_runner.py`, `checkpoint.py`, `payment_reconciliation.py`, `insights_export.py`, `push_orchestrator.py`, `conversation_audit.py`, `story_warmer.py`, `cache_invalidate.py`, `timeout.py`.

### Auto-Instrumentation

`HTTPXClientInstrumentor().instrument()` called at startup in `api/lifespan.py`, enabling automatic W3C `traceparent` propagation on all httpx clients. Platform SDK (`autom8y-http[otel]>=0.6.0`) provides additional transport-level instrumentation via `InstrumentedTransport`.

Graceful degradation: `ImportError` on `opentelemetry.instrumentation.httpx` caught with structured warning log.

### Trace Propagation

W3C Trace Context (`traceparent`) propagation confirmed:
- `HTTPXClientInstrumentor` auto-instruments all outbound httpx calls
- `api/lifespan.py:82` documents `"impact": "Direct httpx clients will not propagate W3C traceparent"` as degradation signal

Cross-service propagation: only one service surface in scope. Verification of parent-child spans across two independent services cannot be confirmed from this codebase alone.

### Log-Trace Correlation

Confirmed wired: `api/lifespan.py` injects `add_otel_trace_ids` as a structlog processor at startup (`additional_processors=[add_otel_trace_ids, ...]`). This processor adds `trace_id` and `span_id` fields to every log event inside an active span context.

**Gap**: Log-trace correlation only fires for HTTP API path (ECS mode). Lambda handlers emit CloudWatch metrics but do not wire `add_otel_trace_ids`.

**Namespace separation**: Two distinct ID namespaces coexist without bridging: HTTP request IDs (UUID hex 16 chars, `X-Request-ID`) and SDK correlation IDs (`sdk-{ts}-{rand}` 18 chars).

### Sampling

No sampler configuration found in project source. OTLP sampling fully delegated to the `autom8y-telemetry` SDK. No `OTEL_TRACES_SAMPLER` env var set in `.env`, `.envrc`, or the env example file. Sampling rate unconfirmed and undocumented at satellite level.

**Completeness**: 70% — SDK wired on ECS critical paths; Lambda instrumentation shallow (CloudWatch-only for 10/13 handlers); sampling undocumented; cross-service span verification not achievable from this codebase alone.

**Grade: C**

## Credential Topology Integrity

### Push Endpoint Enumeration

This service binds against the following multi-protocol push surfaces:

**Protocol 1 — OTLP (via `autom8y-telemetry[otlp]`):**
- Endpoint: delegated entirely to the `autom8y-telemetry` platform SDK. No `OTEL_EXPORTER_OTLP_ENDPOINT` env var set or documented in any local config.
- Auth-routing-field: unknown — no OTLP header credentials configured at satellite level.
- Protocol tuple: `(push-HTTP/OTLP, scope=unknown, auth-routing-field=unknown)` — **undeclared at satellite level**.

**Protocol 2 — Prometheus (via `instrument_app()` in `autom8y-api-middleware`):**
- Endpoint: scrape-pull at `/metrics`, served locally. No remote-write configured.
- Auth-routing-field: none (scrape-pull; auth controlled by scraper).
- Protocol tuple: `(scrape-pull, scope=local, auth-routing-field=N/A)`.

**Protocol 3 — CloudWatch (via `boto3.client("cloudwatch")`):**
- Endpoint: `cloudwatch.{region}.amazonaws.com` (AWS SDK auto-resolution).
- Auth-routing-field: IAM role/credentials via boto3 credential chain.
- Namespace: `ASANA_CW_NAMESPACE` env var (default: `autom8y/lambda`).
- Protocol tuple: `(vendor-native/CloudWatch, scope=namespace, auth-routing-field=IAM-role)`.

### Credential Topology Matrix Cross-Reference

No satellite-level `credential-topology-matrix.yaml` file exists in this repository. The schema file (`credential-topology-matrix.schema.yaml`) is present as a framework artifact (under `.claude/skills/pinakes/schemas/`), but no instance data exists.

**BLOCKING FINDING**: The OTLP push credential topology is opaque at the satellite level — the entire auth-binding is delegated to the platform SDK (`autom8y-telemetry`). If the platform SDK performs a multi-protocol push (traces to one backend, metrics to another), the (protocol × scope × auth-routing-field) tuples are not declared or visible here.

### Bind-Time Fixture

No bind-time fixture found that validates credential tuples before first runtime invocation. All three protocols bind lazily (OTLP via SDK init, CloudWatch via lazy boto3 client, Prometheus via module-level `Counter/Histogram/Gauge`).

### Bake-at-Apply Coupling

OTLP credentials presumably baked at deploy-time via platform SDK's configuration surface. No debt-ledger pointer or rotation procedure documented in this repository.

CloudWatch: IAM role rotation is infrastructure-level; not tracked here.

### 2-Axis Bifurcation

Cannot be determined. The OTLP push topology is opaque.

**Completeness**: 30% — Prometheus and CloudWatch tuples inferable; OTLP tuple fully opaque; no credential-topology-matrix instance; no bind-time fixture; no rotation documentation.

**Grade: F** (multi-protocol binding with undeclared auth-routing-field axis for OTLP — automatic F per criterion grade floor)

## Signal Pipe Contracts

| Signal Class | Producer SDK | Wire Protocol | Endpoint | Consumer Backend |
|---|---|---|---|---|
| Traces | `autom8y_telemetry` (OTel) | OTLP push-HTTP | Unknown (SDK-managed) | Unknown (OTLP-compatible backend) |
| Metrics (ECS) | `prometheus_client` | HTTP scrape-pull | `/metrics` (local) | Unknown (scraper not configured here) |
| Metrics (Lambda) | CloudWatch via boto3 | vendor-native push | `cloudwatch.{region}.amazonaws.com` | AWS CloudWatch |
| Metrics (Lambda 2) | `autom8y_telemetry.aws` | vendor-native | AWS-mediated | AWS CloudWatch |
| Logs | `autom8y_log` + structlog | stdout (structured JSON) | Stdout capture (ECS log driver) | Unknown (log router not specified) |
| Profiles | None detected | — | — | — |

### Pipeline Topology

**ECS (API) mode**:
- Traces: service → (OTel SDK) → OTLP exporter → [unknown backend, 1+ hops, unspecified]
- Metrics: in-process `prometheus_client` registry → `/metrics` endpoint → [scraper → unknown backend]
- Logs: structlog → stdout → ECS log driver → [log aggregation unknown]

**Lambda mode**:
- Metrics: `emit_metric()` → boto3 CloudWatch → direct push (1 hop)
- Traces: `instrument_lambda` wrapper → [OTLP or CloudWatch X-Ray, unclear]

### Auth Surface per Hop

- CloudWatch: IAM instance role (no explicit credential in code; boto3 credential chain)
- OTLP: unknown (SDK-managed)
- Prometheus scrape: no auth from producer side; consumer-side auth undocumented

### SCAR Log

No documented contract-drift incidents (404/401 pipeline failures) found. No SCAR log for signal-pipe failures exists in the knowledge base.

**Completeness**: 45% — CloudWatch contract complete; Prometheus scrape protocol documented but consumer unknown; OTLP backend/auth opaque; no SCAR log; log consumer unknown.

**Grade: F**

## SLO/SLI Maturity

No SLO definitions found in any source file, YAML configuration, documentation, or knowledge file. Search across all YAML, markdown, and Python files for `SLO`, `error_budget`, `burn_rate`, and `availability.*target` returned zero results in project source.

### Metric Surface Available for SLI Construction

Metrics that could support SLIs:

- `autom8y_asana_dataframe_build_duration_seconds` — latency SLI candidate
- `autom8y_asana_dataframe_cache_operations_total` — freshness/availability SLI candidate
- `autom8y_asana_api_calls_total` + `autom8y_asana_api_call_duration_seconds` — availability + latency SLI candidates
- CloudWatch namespace `autom8y/lambda` — Lambda success/failure rate

No SLO statements declared, no measurement windows defined, no denominators specified, no burn-rate alerts exist, no error-budget policy documented.

**Completeness**: 5% — raw metric surface exists but zero SLO/SLI discipline present.

**Grade: F**

## Alerting & Runbook Coverage

### Alert Rules

No alert rule definitions found (no Prometheus alerting rules YAML, no AlertManager config, no CloudWatch alarms in code). Runbook documents contain informal threshold guidance in prose ("alert if >5%", "alert if >1%") but not machine-actionable alert rule definitions.

### Runbook Inventory

Operational runbooks in `docs/runbooks/`:
- `RUNBOOK-pipeline-automation.md` — pipeline escalation (P2)
- `RUNBOOK-cache-troubleshooting.md` — cache hit rate monitoring, SWR staleness
- `RUNBOOK-detection-troubleshooting.md` — detection failure rate
- `RUNBOOK-savesession-debugging.md` — save operation duration
- `RUNBOOK-rate-limiting.md`
- `RUNBOOK-batch-operations.md`
- `RUNBOOK-business-model-navigation.md`

Development-operation runbooks in `runbooks/atuin/` (bootstrap, auth, API operations, troubleshooting).

**Gap**: No alert-to-runbook linkage exists. Runbooks not linked from any alert rule (no alert rules exist). No on-call escalation policy or rotation ownership documented.

### Synthetic Monitoring

None detected.

### Alert Fatigue

Not assessable (no alert rules exist to evaluate).

**Completeness**: 20% — runbooks exist but are not linked from alert rules; alert rules do not exist; no synthetic monitors; no on-call documentation.

**Grade: F**

## Knowledge Gaps

1. **OTLP backend identity**: Which observability backend does `autom8y-telemetry[otlp]` push to? Credential-binding surface, endpoint URL, auth-routing-field, push protocol opaque at satellite level. Primary blocker for Criterion 2.
2. **Prometheus scraper identity**: What scrapes `/metrics`? No scraper configuration in-repo. Consumer backend for ECS Prometheus metrics unknown.
3. **Log aggregation backend**: Where do stdout logs go after ECS log driver? No log-router configuration in-repo.
4. **Sampling configuration**: No `OTEL_TRACES_SAMPLER` or equivalent configured at satellite level. Sampling rate and strategy unknown.
5. **Lambda trace backend**: `autom8y_telemetry.aws`'s `instrument_lambda` — emits traces to CloudWatch X-Ray or OTLP? Determines whether Lambda has distributed tracing or only CloudWatch metrics.
6. **Bridging gap**: `bridge_base.py` `trace_computation` TODO documented in code but has no tracking issue or ticket reference. 10 Lambda handlers have no `autom8y_telemetry` instrumentation beyond CloudWatch.
7. **Credential topology matrix instance**: No `.sos/` or `.know/` credential-topology-matrix YAML for this satellite exists. Authoritative schema is present but unpopulated.
8. **SLO definitions**: No SLOs, SLIs, or error-budget policy exist. Raw metric surface is present to construct them.
9. **Alert rules**: No machine-actionable alert definitions exist. Runbooks reference thresholds in prose but no alert rule YAML ties them.
10. **On-call documentation**: No on-call rotation, escalation policy, or ownership documentation exists.

**[KNOW-CANDIDATE]** The `autom8y-telemetry[aws,fastapi,otlp]` multi-protocol SDK delegates OTLP credential binding entirely to the platform layer, making credential topology opaque at satellite level — a systematic pattern affecting all autom8y satellite repos.

**[KNOW-CANDIDATE]** The `bridge_base.py` trace gap (trace_computation not applied, documented as version-availability TODO) is a known instrumentation debt point with no tracking reference.

---

### Grade Derivation

| Criterion | Grade | Weight | Contribution |
|---|---|---|---|
| Instrumentation Depth | C (75%) | 25% | 18.75 |
| Credential Topology Integrity | F (30%) | 25% | 7.50 |
| Signal Pipe Contracts | F (45%) | 20% | 9.00 |
| SLO/SLI Maturity | F (5%) | 20% | 1.00 |
| Alerting & Runbook Coverage | F (20%) | 10% | 2.00 |
| **Total** | | | **38.25 → F** |

**Confidence 0.82 (not 0.95)**: The OTLP credential topology and backend identity are opaque — managed by `autom8y-telemetry`, a private platform SDK not readable from this repository. A higher confidence would require reading the `autom8y-telemetry` SDK source or observing a running deployment.
