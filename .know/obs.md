---
domain: obs
generated_at: "2026-10-05T03:31:41Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/__init__.py"
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/config.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./src/autom8_asana/errors.py"
  - "./src/autom8_asana/settings.py"
  - "./src/autom8_asana/storage_namespace.py"
  - "./pyproject.toml"
  - "./.ledge/specs/cache-freshness-observability.md"
  - "./.ledge/specs/cache-freshness-runbook.md"
generator: theoros
source_hash: "af02adbfdcc62241eb90f3f1ed940f657a8fadc0e5166d4a754969b32f486458"
confidence: 0.78
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@c29f58f4"
---

# Codebase Observability

> Observed at `origin/main` = `c29f58f4` (detached worktree). Code/IaC is the authority; every AWS statement is labelled **LIVE-OBSERVED** with a timestamp (read-only `aws cloudwatch` / `aws logs` calls, account <acct>, us-east-1, 2026-10-05 ~03:15-03:55Z). Anything not directly read is labelled **UV-P** (unverified, with the method that would verify it). Paths are relative to the repo root unless prefixed `monorepo:` (the `autom8y` parent repo, NOT in this checkout).

**Vendor / stack detection**: observability stack detected (OTel SDK imports, `prometheus_client`, CloudWatch, AMP remote-write). Four live push/pull surfaces plus one ship-dark surface:

| # | Surface | Protocol class | Where bound | State at `c29f58f4` |
|---|---------|----------------|-------------|---------------------|
| P1 | OTel traces via `autom8y-telemetry[aws,fastapi,otlp,remote-write]>=0.10.0` | push OTLP (exporter, endpoint, auth all SDK-managed) | `pyproject.toml:41`, `api/main.py:941` | Endpoint/headers/sampler NOT declared anywhere in-repo (UV-P) |
| P2 | Prometheus text exposition at `/metrics` | scrape-pull | `instrument_app(...)` `api/main.py:941`; 22 domain series in `api/metrics.py` | Scraper identity not in-repo (UV-P) |
| P3 | CloudWatch `PutMetricData` (6 emitter sites) | vendor-native push, IAM role | see §Signal Pipe Contracts | LIVE (ECS + Lambda) but Lambda fleet dark since 2026-09-05 (OBS-LAMBDA-DARK-001) |
| P4 | AMP Prometheus remote-write (SigV4) | remote-write | `lambda_handlers/offer_warm_amp.py:65-148` | Flag-gated default OFF; live arming UV-P |
| P5 | CloudWatch EMF JSON to stdout | log-driver extraction | `api/metrics.py:354-425` | Ship-dark (`RECEIVER_SLI_EMF_ENABLED` unset): LIVE-OBSERVED zero metrics in `Autom8y/AsanaReceiverSLI` |
| P6 | MCP sidecar spans | OTel API only (no SDK/exporter) | `mcp/asana_mcp/observability.py:579-603`, `mcp/pyproject.toml:36-37` | Spans are no-ops unless a host installs a TracerProvider (code-inferred) |

**Deployment modes**: ECS/FastAPI service `autom8y-asana-service` (Prometheus + OTel + log-metric-filters); Lambda family (`src/autom8_asana/lambda_handlers/`, 21 modules; CloudWatch + `autom8y_telemetry.aws`); MCP stdio/HTTP sidecar (`mcp/`); CLI (`python -m autom8_asana.metrics`, CloudWatch batch).

**Headline (read this first)**
1. The 2026-05-08 headline gap (OBS-EXPORTS-001) is CLOSED in-repo: `exports.request` span, 3-4 structured logs and 4 Prometheus series now ship (`api/routes/exports.py:352`, `api/metrics.py:724-760`).
2. The alarm plane is the weak surface, not the instrumentation plane. LIVE-OBSERVED: of 73 asana-named alarms, 16 are in ALARM, 20 have `ActionsEnabled=false` (7 of those in ALARM, including the SEV-1 `autom8y-asana-story-warm-dead`), 9 have zero `AlarmActions`, 9 of 71 metric alarms have **zero datapoints in 390 days**, and 8 more have not seen a datapoint in >30 days.
3. The whole Lambda family stopped emitting between 2026-09-04T10Z and 2026-09-05T08Z (LIVE-OBSERVED last `AWS/Lambda Invocations` datapoints) and has been dark ~29 days at observation time; the ECS service kept emitting. Nothing in this repo can say whether that is intended.
4. Only 9 of the 18 alarm instances the in-repo Terraform defines exist live; 2 live alarms (PROV-8, PROV-9) have no in-repo Terraform; the other 62 of the 73 asana-named live alarms are not defined in this repo's Terraform (authorship UV-P: presumed monorepo, which was not read). There is no apply pipeline in this repo (`terraform/services/asana/story_warm_dead_alarm.tf:53-58`).

---

## OBS-EXPORTS-001: Exports Route Instrumentation Gap (P2)

**Status**: CLOSED in-repo (was OPEN at 8980bcd7 on 2026-05-08; closed 2026-06-01, branch `sre-ob2-exports-observability-2026-06-01`). Residual (SLO targets + burn-rate rules) is cross-repo.

### Anchor (current)
- Span: one `exports.request` span wraps the shared `export_handler`, `record_exception=False, set_status_on_exception=False` (`api/routes/exports.py:352-356`); tracer from `autom8y_telemetry.get_tracer` (`api/routes/exports.py:44,101`). Both delegating routes (`post_export_v1`, `post_export_api_v1`) inherit it.
- Structured logs: `exports_section_default_injected` (`exports.py:393`), `exports_date_filter_applied` (`:416`), `exports_identity_rows_suppressed` (`:512`), `exports_handler_complete` (`:565-566`), plus three helper warnings in `api/routes/_exports_helpers.py:130,161,188` and `exports_left_preservation_guard_noop` (`exports.py:283`).
- Metrics (all in `api/metrics.py`): `autom8y_asana_exports_request_duration_seconds` Histogram `{entity_type,format}` (`:724-729`); `..._predicate_split_outcome_total` Counter `{entity_type,date_filter_applied,section_default_applied}` (`:736-740`); `..._identity_rows_suppressed_total` Counter `{entity_type}` (`:745-749`); `autom8y_asana_exports_rows` Histogram `{entity_type,stage}` (`:755-760`). Recording sites `exports.py:550-581`. `exports_format_negotiation_fallback_total` was deliberately dropped (no real seam; note at `api/metrics.py:762-768`).
- Downstream consumer (LIVE-OBSERVED 2026-10-05): the log event `exports_handler_complete` is turned into CloudWatch metric `autom8y/asana-exports ExportsHandlerComplete` by a **log metric filter** `autom8-asana-exports-request-presence` on `/ecs/autom8y-asana-service` (filter pattern `{ $.event = "exports_handler_complete" }`). That filter is NOT defined in this repo's Terraform (UV-P: monorepo). The metric has 1321 hourly datapoints in 55d, last value 0.0 at 2026-10-04T23:15-04:00 (the filter emits dense zeros), so it is alive.

### Residual
- Alarm `autom8-asana-exports-request-presence-DMS` is LIVE-OBSERVED in ALARM since 2026-06-12 with `ActionsEnabled=false`; it asserts Sum<1 over 12x2h periods (`breaching` on missing). It cannot page anyone.
- SLO targets / burn-rate alert rules for `/v1/exports`: none defined anywhere in this repo (0 `.tf` mention exports).
- Verified risk reduction: regression in `_walk_predicate`/date translation is no longer 100% reactive (span attributes + per-request histograms exist). Still no alert reads the duration histogram.

---

## OBS-LAMBDA-DARK-001: The Lambda fleet stopped emitting ~2026-09-05 (NEW, P1 for the alarm plane)

- LIVE-OBSERVED 2026-10-05 ~03:30Z, `get-metric-statistics` period 3600, last non-empty hour (UTC): `autom8-asana-cache-warmer` Invocations 2026-09-05T06:00Z; `-cache-warmer-bulk` 2026-09-05T08:00Z; `-prov-sweep` 2026-09-05T06:00Z; `-scheduling-stratum-snapshot` 2026-09-05T05:00Z; `-insights-export` 2026-09-04T10:00Z. `Autom8y/SubstrateProvability EvaluatorHeartbeat{environment=production}` last 2026-09-05T06:00Z. `autom8y/cache-warmer StoryWarmSuccess{environment=staging}` last 2026-09-05T06:00Z.
- Alarm consequence (LIVE-OBSERVED): `asana-PROV-2-heartbeat-absence` ALARM since 2026-09-05 (correctly), `asana-stratum-producer-dead`, `-substrate-stale`, `-universe-collapse`, `asana-r7-evaluator-dead`, five `*-lambda-liveness` alarms, `autom8y-asana-story-warm-dead` all ALARM with state-change dates 2026-09-05..09-13.
- The ECS service is NOT dark: `AWS/ECS CPUUtilization` for `autom8y-asana-service` has data to 2026-10-04T23:15-04:00; `OfferFrameAgeSeconds{project_gid=1143843662099250}` (ECS-emitted via log filter) has data to the same hour.
- What the repo can and cannot say: nothing in `c29f58f4` documents a deliberate pause. Whether EventBridge rules are DISABLED or the functions were removed is **UV-P** (method: `aws events list-rules` + `aws lambda get-function`). The related memory note (operator) of an intake outage since 2026-09-26 is a different surface.
- Implication for every Lambda-sourced SLI/alarm below: "OK" alarm states on Lambda-sourced metrics with `notBreaching` after 2026-09-05 are OK-by-absence, not OK-by-evidence.

---

## Instrumentation Depth

### SDK Adoption

`autom8y-telemetry[aws,fastapi,otlp,remote-write]>=0.10.0` (`pyproject.toml:41`; was `[otlp,fastapi,aws]>=0.6.1` in the prior pass), `autom8y-http[otel]>=0.6.0` (`:22`), `opentelemetry-instrumentation-httpx>=0.42b0` (`:26`), `autom8y-log>=0.7.0,<1.0.0` (`:24`). `autom8y_telemetry` is imported in 21 source modules; `opentelemetry` directly in 14 (lazy `from opentelemetry import trace` to read the current span).

| Surface | Mechanism | Anchor |
|---------|-----------|--------|
| FastAPI app (ECS) | `instrument_app(app, InstrumentationConfig(service_name="asana"))`: MetricsMiddleware outermost + `/metrics` mount; explicit `service_name="asana"` is load-bearing for per-service SLI selection | `api/main.py:48,941` |
| Business metric compute | `@trace_computation("metric.compute", record_dataframe_shape=True, df_param="df")` | `metrics/compute.py:19-21` |
| DataFrame cache | `@trace_computation("cache.get")` | `cache/integration/dataframe_cache.py:241` |
| Progressive builder | `@trace_computation("progressive.build")` | `dataframes/builders/progressive.py:1004` |
| Query engine | `entity.query_rows` (`query/engine.py:129`), `entity.query_aggregate` (`:383`), `predicate.compile` (`query/compiler.py:164`), `entity.join` (`query/join.py:90`), `data_service.fetch_join` (`query/fetcher.py:40`) | |
| Query service | `entity_query.get_dataframe` | `services/query_service.py:586` |
| Strategy resolution | manual spans `strategy.resolution.resolve` / `.resolve_group` (records exception + `StatusCode.ERROR`) | `services/universal_strategy.py:201,330,358-359` |
| Resolver route | manual span `resolver.entities.resolve` | `api/routes/resolver.py:351` |
| Exports route | manual span `exports.request` | `api/routes/exports.py:352` |
| Payment reconciliation | `@trace_reconciliation("payment_reconciliation.process_entity")` | `automation/workflows/payment_reconciliation/workflow.py:164` |
| Lambda entry points | `@instrument_lambda` | see Lambda table |
| Outbound HTTP | global `HTTPXClientInstrumentor().instrument()` at lifespan start, `ImportError` degrades to a warning | `api/lifespan.py:135-137` |
| MCP sidecar | per-tool `execute_tool {name}` span (`gen_ai.*` + `com.autom8y.mcp.*` attrs), per-client `HTTPXClientInstrumentor().instrument_client(ctx.http)` | `mcp/asana_mcp/observability.py:579-603,754-774` |

**Spans per critical path**: request handlers (resolver, exports, query via engine/service), cache read (`cache.get`), build (`progressive.build`), resolution strategy, reconciliation workflow, Lambda invocation. Not span-covered: the generic bridge `execute_async` (see H-006 below), `api/routes/*` other than resolver/exports (rely on `instrument_app` HTTP server spans only), the account-status push loop, the MCP-to-satellite hop beyond header injection.

### Lambda entry-point instrumentation (denominator re-derived)

Entry-point handler functions (`def handler(event, context)`) in `lambda_handlers/`: **11**. `@instrument_lambda` applied to **7**:

| Handler | Instrumented | Anchor |
|---------|--------------|--------|
| `cache_warmer` | yes (direct) | `lambda_handlers/cache_warmer.py:1273` |
| `cache_invalidate` | yes (direct) | `cache_invalidate.py:298` |
| `prov_sweep` | yes (direct) | `prov_sweep.py:221` |
| `conversation_audit`, `insights_export`, `onboarding_walkthrough`, `payment_reconciliation` | yes (transitive via `create_workflow_handler`) | `workflow_handler.py:96`; `conversation_audit.py:52`, `insights_export.py:59`, `onboarding_walkthrough.py:118`, `payment_reconciliation.py:60` |
| `scheduling_stratum_snapshot` | **NO** | `scheduling_stratum_snapshot.py:1245` |
| `traffic_offer_divergence_tripwire` | **NO** | `traffic_offer_divergence_tripwire.py:1083` |
| `enrollment_intent_bridge` | **NO** | `enrollment_intent_bridge.py:699` |
| `leads_consumer` | **NO** | `leads_consumer.py:50` |

Helper modules (not entry points): `cloudwatch.py`, `offer_warm_amp.py`, `story_warmer.py` (invoked from the warmer), `checkpoint.py`, `reconciliation_runner.py`, `pipeline_stage_aggregator.py`, `push_orchestrator.py`, `timeout.py`. [CORRECTION vs prior LAMBDA-OBS-001 "6 of 6": the entry-point set grew; 4 of 11 are now uninstrumented. The four uninstrumented handlers are exactly the ones whose alarms are the SEV-1 pagers (stratum, R7).]

### Auto-Instrumentation

`HTTPXClientInstrumentor` (global, ECS) at `api/lifespan.py:135-137`; platform `autom8y-http[otel]` `InstrumentedTransport` adds transport-level propagation. The MCP wires the instrumentor per client (never default headers, to avoid stale-traceparent leakage): `mcp/asana_mcp/observability.py:754-774`. No other library instrumentors (no botocore/boto3, no redis, no SQLAlchemy/psycopg) are installed: S3 and Redis calls are not auto-traced.

### Trace Propagation

W3C `traceparent` injected on outbound httpx calls (ECS global instrumentor; MCP per-client). Inbound extraction is performed by the platform `instrument_app` middleware (SDK-internal, UV-P: not read here). The MCP test `mcp/tests/test_span_and_traceparent.py` proves span creation and header injection against an `InMemorySpanExporter` in a fake-collector setup; it is NOT evidence of a production cross-service trace. No sample production trace spanning MCP -> ALB -> satellite was obtained (UV-P: Tempo/OTLP backend identity unknown from this repo).

### Log-Trace Correlation

- `add_otel_trace_ids` + `_filter_sensitive_data` passed as `additional_processors` at `api/lifespan.py:124-127` (imported `:15`). `core/logging.py:90-109` builds `LogConfig(backend="structlog", format="auto", intercept_stdlib=True)` and calls `reset_logging()` BEFORE configure so the custom processors are not dropped by SDK auto-config (fix PR #89; the prior pass recorded this as a root cause under LOG-TRACE-LAMBDA).
- Per the prior RESOLVED record, `add_otel_trace_ids` is already in the SDK's default base chain, so Lambda logs carry `trace_id` when inside a span. Not re-verified against a live log line this pass (UV-P; method: `aws logs filter-log-events` on a `/aws/lambda/...` stream, which now has no recent events, see OBS-LAMBDA-DARK-001).
- Import guard banning direct `structlog`/`logging`/`loguru`: `pyproject.toml:351-359` (ruff `flake8-tidy-imports.banned-api`). Exceptions still exist: `_defaults/log.py:9,54` (`logging.getLogger`, the SDK-default protocol shim), `cache/models/events.py:126` (docstring only).
- `get_logger` is used in 251 of 610 `src` Python files.
- The MCP has NO logging at all (`grep logging|get_logger mcp/asana_mcp/*.py` returns nothing): tool executions emit spans only.
- Namespace gap persists: HTTP `X-Request-ID` (`uuid4().hex[:16]`, `api/middleware/core.py:92-96`) vs SDK `CorrelationContext` ids (`observability/correlation.py:14-33`) are not bridged.

### Sampling

No sampler configured in-repo: no `OTEL_TRACES_SAMPLER*`, `OTEL_EXPORTER_*` or `OTEL_SERVICE_NAME` string appears in any `.py/.toml/.yml/.tf/Dockerfile/.env*` file (grep, 2026-10-05; only `ASANA_MCP_OTEL_CAPTURE_CONTENT` at `mcp/asana_mcp/observability.py:137` matches `OTEL_`). Sampling rate and exporter are delegated to `autom8y-telemetry` and the ECS task definition (UV-P; method: `aws ecs describe-task-definition`).

### MCP sidecar: instrumentation without a pipe (NEW, OBS-MCP-NOEXPORT-001)

`mcp/pyproject.toml:36-37` depends on `opentelemetry-api` and `opentelemetry-instrumentation-httpx` only; `opentelemetry-sdk` is in the `dev` extra only (`:49`). No `TracerProvider`, exporter or `set_tracer_provider` exists in `mcp/asana_mcp/` (grep). With only the API installed, `tracer.start_as_current_span` is a no-op tracer: spans, gen_ai attributes and the honesty attributes (`com.autom8y.mcp.honesty.*`, `observability.py:117,132,603`) are produced but exported nowhere unless the host process installs a provider. The module self-describes as "REFERENCE-POSTURE PROTOTYPE ... NOT production code" (`observability.py:2-3`) with 6 listed shortcuts (S1-S6). No metrics, no logs. Rate-cap refusal (`RateCapExceeded`) and timeout guard (`asyncio.timeout`) attach refusal-cause attributes to the span only (`observability.py:670,686`), so the MCP's refusals have no counter.

### Known gaps registry for this criterion
- H-006 (bridge_base): `automation/workflows/bridge_base.py:191-197` still carries the "trace_computation not available in 0.6.1" TODO; the dependency is now `>=0.10.0` and `trace_computation` is used in 8 other modules, so the stated blocker is obsolete while the gap (no span on `execute_async`) remains. Open.
- Client libraries uninstrumented: S3 (boto3), Redis, Asana HTTP via SDK `AsanaClient` (covered only via global httpx instrumentor).

**Completeness**: 80%. Grade B (see metadata). Basis: SDK/adoption/auto-instrumentation/log-correlation documented from code with anchors; no live trace or log-to-trace join sampled; sampler undocumented.

---

## Credential Topology Integrity

### Interpretation note
The rubric contains an automatic-F floor for "multi-protocol binding with undeclared auth-routing-field axis". This pass interprets that clause as applying to a binding whose axis is silently omitted; the OTLP binding's axis is recorded below as **explicitly UV-P/BLOCKING** rather than omitted, so it is graded as a documented gap (D), not the F floor. A stricter reader would apply the floor; the metadata records both. The `credential-topology-matrix` schema file named in the criteria (`knossos/mena/pinakes/schemas/credential-topology-matrix.schema.yaml`) does not exist at that path on this machine, and no instance exists in the repo (`find . -iname '*credential-topology*'` finds only a `.ledge` receipt about the Asana PAT topology, unrelated to telemetry).

### Push-endpoint tuples: (protocol, scope, auth-routing-field)

| ID | Endpoint / producer | protocol | scope | auth-routing-field | Credential source | Evidence |
|----|---------------------|----------|-------|--------------------|-------------------|----------|
| T1 | `cloudwatch.{region}.amazonaws.com` PutMetricData, ECS + Lambda emitters (`emit_metric`, `put_metric_data` x6) | vendor-native HTTPS, SigV4 | **namespace** (IAM `cloudwatch:namespace` StringEquals condition on the role) | IAM role identity + namespace string; there is no tenant/stack routing axis | ambient task/execution role, no static secret | `lambda_handlers/cloudwatch.py:27,68`; namespace-condition grant described at `lambda_handlers/cache_warmer.py:81-95` (cites monorepo `autom8y/asana/main.tf:1096`) |
| T2 | AMP workspace remote-write (`AMP_REMOTE_WRITE_ENDPOINT`), series `autom8y_offer_warm_complete_timestamp{entity_type}` | Prometheus remote-write over HTTPS, snappy, SigV4 | workspace (encoded in endpoint URL) + region | SigV4 credential identity (execution role); workspace routing is the URL path (UV-P: value not in-repo) | `autom8y_telemetry.aws.remote_write.resolve_credentials()` | `lambda_handlers/offer_warm_amp.py:36-37,82-122`; gate `RemoteWriteConfig.from_env().is_active` (`ASR_AMP_EMIT_ENABLED` + `AMP_REMOTE_WRITE_ENDPOINT`), default OFF |
| T3 | OTLP traces (and possibly metrics/logs), SDK-managed | OTLP push-HTTP or push-gRPC (UV-P which) | UV-P | **UV-P - BLOCKING**: the 2-axis bifurcation concern (gateway stack axis vs direct signal-instance axis) cannot be confirmed or excluded from this repo | SDK-resolved | no `OTEL_EXPORTER_OTLP_*` anywhere in repo; `pyproject.toml:41` extra `otlp` |
| T4 | `/metrics` scrape | pull | local | none on producer side; scraper identity UV-P | n/a | `api/main.py:941` |
| T5 | EMF line on stdout -> awslogs driver -> CloudWatch Logs extraction | log-driver | log group | IAM on the log group; extraction pipeline is cross-repo | n/a | `api/metrics.py:354-425`; LIVE-OBSERVED zero metrics in `Autom8y/AsanaReceiverSLI` |
| T6 | Log-metric-filters (CloudWatch Logs -> metric) | in-AWS | log group | none (AWS-internal) | n/a | `terraform/services/asana/observability_alarms.tf:446-462,687-698`; `warmer_cache_degraded_alarm.tf:66-80`; LIVE-OBSERVED 3 filters on `/ecs/autom8y-asana-service`, 5 on `/aws/lambda/autom8-asana-cache-warmer` |
| T7 | Alarm action targets (SNS) | SNS publish | topic | topic ARN | n/a | `story_warm_dead_alarm.tf:64-78`; `observability_alarms.tf:100-142` |

SNS topics in use (LIVE-OBSERVED across 73 alarms): `autom8y-platform-alerts` (64 alarm-action bindings; notify tier, Slack lambda + email per `terraform.tfvars.example:20-27`, verified there 2026-08-11) and `autom8y-platform-sre-sev1` (16 bindings; paging tier, SMS+email per `story_warm_dead_alarm.tf:70-76`, verified 2026-08-14). Topic subscriptions were not re-queried this pass (UV-P; method `aws sns list-subscriptions-by-topic`).

### Expected success / failure responses per tuple
- T1: success = HTTP 200 with empty body; failure shapes: `AccessDenied` when the namespace is outside the IAM condition (silent drop - `emit_metric` swallows the exception and logs `metric_emit_error`, `cloudwatch.py:79-85`), `NoRegionError` at client creation (also swallowed, `:60-66`). Failure is **observable only in logs**, never as a metric. Precedent: the DMS `LastSuccessTimestamp` was silently denied until the namespace was re-pointed to the granted one (comment `cache_warmer.py:81-95`, "C2 fix").
- T2: success = 2xx from the AMP workspace; failure is deliberately loud: error log `offer_warm_amp_failed_no_credentials` / `offer_warm_amp_emission_failed` plus CloudWatch counter `OfferWarmAmpFailed{entity_type,reason}` (`offer_warm_amp.py:106-148,153-184`). Disabled = silent `debug` skip (`:84-99`), by design: absence is caught by a downstream freshness alert (monorepo, UV-P).
- T3/T4/T5: not observable from this repo.

### Bind-time fixture
None for any tuple. T1 binds lazily on first emit (`cloudwatch.py:21-28`, cached module global). T2 resolves credentials per call (`offer_warm_amp.py:106`) and has a unit canary (`tests/unit/lambda_handlers/test_offer_warm_amp.py`, two-sided per module docstring `:20-24`); that tests series name/label, not credential validity. No equivalent for T1/T3.

### Bake-at-apply and rotation
- T1/T2 use role identity: no secret to rotate in-repo; rotation = IAM policy change in the monorepo (cross-repo debt, no ledger pointer in this repo).
- Namespace/dimension literals are **baked in two places** and must match by convention: the Lambda env `ASANA_CW_NAMESPACE` / `ASANA_CW_ENVIRONMENT` (`settings.py:766-790`) and the alarm definitions. `ASANA_CW_ENVIRONMENT` defaults to `"staging"` (`settings.py:793-795`); a Lambda that omits it stamps `environment=staging` on every metric. Live evidence: `autom8y-asana-story-warm-dead` deliberately alarms on `environment=staging` because the PRODUCTION warmer carries that label (`story_warm_dead_alarm.tf:33-41`); the stratum producer was fixed 2026-08-06 (`scheduling_stratum_snapshot.py:245-251`). `WarmSuccess`/`WarmFailure` LIVE-OBSERVED exist ONLY under `environment=staging` (129 and 11 day-buckets in the last 200d) and zero under `production`.
- Namespace tri-partition (documented in ADR-006/ADR-007, `.ledge/decisions/`): `autom8/lambda` (default), `autom8y/cache-warmer` (lowercase, coalescer + warmer runtime), `Autom8y/...` (Pascal: freshness probe, substrate, bridge fleet). Six places hard-code a namespace; a rename silently un-wires alarms (see GAP-012 in design-constraints).

### 2-axis bifurcation check
Within this repo's own surfaces the routing axis is uniform (IAM + namespace). The only place a bifurcation could exist is T3 vs T4/T2 on a shared receiver platform, and that cannot be evaluated here. Flagged, not resolved.

**Completeness**: 62% (D). Basis: 6 of 7 tuples decomposed with evidence; OTLP axis unknown (BLOCKING); no matrix instance; no bind-time fixture; rotation documented only as role-identity.

---

## Signal Pipe Contracts

### Per-signal-class contract table

| Signal class | Producer side | Wire protocol | Endpoint | Auth surface | Consumer side | Hops / retry posture |
|---|---|---|---|---|---|---|
| Traces (ECS) | `autom8y_telemetry` OTel SDK, `@trace_computation` + manual spans | OTLP (HTTP vs gRPC UV-P) | UV-P (SDK-managed) | UV-P (T3) | UV-P (OTLP-compatible backend) | Direct push assumed; collector presence UV-P |
| Traces (Lambda) | `@instrument_lambda` | UV-P (OTLP or X-Ray via SDK) | UV-P | UV-P | UV-P | Per-invocation flush UV-P |
| Traces (MCP) | `opentelemetry-api` only | none (no exporter) | none | none | none unless host provider | 0 hops: no-op by default (OBS-MCP-NOEXPORT-001) |
| Metrics (ECS, domain) | `prometheus_client` in-process registry, 22 series in `api/metrics.py` | scrape-pull text | `/metrics` mounted by `instrument_app` | none producer-side | unknown scraper (UV-P) | In-memory, fire-and-forget, no I/O (`api/metrics.py:7`) |
| Metrics (ECS, platform) | `instrument_app` MetricsMiddleware: `autom8y_http_request_duration_seconds{service="asana",route_class}`, `autom8y_build_info` (SDK >=0.10.0) | scrape-pull | `/metrics` | none | monorepo SLO rules, e.g. `EcsServiceDenominatorAbsent{service=asana,slo=emitting_floor}` (`api/sli_heartbeat.py:3-12`; rule itself UV-P) | `SliHeartbeat` re-observes every 30s (`sli_heartbeat.py:62`) |
| Metrics (CloudWatch, any mode) | 6 `put_metric_data` sites (below) | AWS JSON/HTTPS | `monitoring.{region}.amazonaws.com` | SigV4 IAM, namespace condition (T1) | CloudWatch + alarms | Synchronous, best-effort, exceptions swallowed to a warning log; no retry beyond botocore defaults |
| Metrics (AMP) | `emit_offer_warm_complete` | remote-write snappy | `AMP_REMOTE_WRITE_ENDPOINT` | SigV4 (T2) | monorepo `slo_offer_freshness` recording rules + node-4 alerts (UV-P) | 1 hop, 1 POST/entity/success; failure -> `OfferWarmAmpFailed` CW counter |
| Metrics (EMF) | `emit_receiver_sli_emf` | EMF JSON line on stdout | ECS awslogs -> CloudWatch Logs extraction | log-group IAM | deploy-gate / monorepo alarm (contract name `ADR-RECEIVER-SLI-METRIC-CONTRACT`, `api/metrics.py:352-355`) | Ship-dark; flag `RECEIVER_SLI_EMF_ENABLED` |
| Logs | `autom8y_log` structlog, JSON when no TTY | stdout | ECS awslogs `/ecs/autom8y-asana-service`; Lambda `/aws/lambda/<fn>` | IAM | CloudWatch Logs; 3 metric filters ECS-side, 5 on the warmer Lambda log group (LIVE-OBSERVED) | 1 hop to CloudWatch; indexing/Insights downstream UV-P |
| Profiles | none | n/a | n/a | n/a | n/a | n/a |
| Events | EventBridge for bridge events (`_publish_bridge_event`, `workflow_handler.py:230,390`) - domain events, not telemetry | n/a | n/a | n/a | n/a | n/a |

### CloudWatch `put_metric_data` sites (6 independent)

| # | Site | Namespace | Dimensions stamped | Anchor |
|---|------|-----------|--------------------|--------|
| 1 | CLI freshness probe (atomic 5-metric batch, ADR-006) | `Autom8y/FreshnessProbe` | `metric_name`, `project_gid` | `metrics/cloudwatch_emit.py:40,217` |
| 2 | Shared Lambda/ECS helper `emit_metric` (13+ importers incl. `api/middleware/idempotency.py:787`, `services/gid_push.py:75`, `api/routes/workflows.py:399`) | `settings.observability.cloudwatch_namespace` = `autom8/lambda` default, overridable per call | **always** `environment` (default `"staging"`) + caller dims | `lambda_handlers/cloudwatch.py:31-85` |
| 3 | Cache coalescer dedup | `autom8y/cache-warmer` | `coalescer_key` (unbounded cardinality) | `cache/dataframe/coalescer.py:30,50` |
| 4 | Provability evaluator + data-quality emitter | `Autom8y/SubstrateProvability` | `environment` (+ `project_gid`,`entity_type` on `ArtifactProvable` only) | `substrate/observe.py:404,519,673` |
| 5 | Serve-side refusal emitter | `Autom8y/SubstrateServe` | `environment`, `reason` | `substrate/serve.py:226,341` |
| 6 | `autom8y_telemetry.aws` helpers: `emit_success_timestamp`, `emit_business_metric`, `instrument_lambda` | per caller (`dms_namespace`, `fleet_namespace`) | SDK-defined | `workflow_handler.py:300-390`, `cache_warmer.py:1420` |

Plus a log-derived metric family via CloudWatch Logs metric filters (T6) and the ship-dark EMF path. LIVE-OBSERVED namespace emptiness (list-metrics returns only metrics with data in the last ~2 weeks): `Autom8y/AsanaReceiverSLI` 0, `Autom8y/SubstrateServe` 0 (emitter `CloudWatchRefusalEmitter` is defined at `substrate/serve.py:269` and referenced by NO production wiring in `src/`; the default is `NullRefusalEmitter`), `Autom8y/AsanaIntakeCF` 0 (AL-6 filter/alarm not applied), `Autom8y/AsanaWarmerCache` 0 (expected: quiet when healthy), `autom8y/cache-warmer` only `CoalescerDedupCount` (Lambda family dark).

### Pipeline topology
- ECS: app -> stdout -> awslogs -> CloudWatch Logs -> {metric filters -> CloudWatch metrics -> alarms -> SNS}; app -> `/metrics` -> scraper (UV-P); app -> OTLP (UV-P); app -> `put_metric_data` direct (coalescer, idempotency failure, gid_push, workflow route).
- Lambda: handler -> `emit_metric`/SDK -> CloudWatch directly (1 hop); logs -> CloudWatch Logs -> metric filters; warmer -> AMP (flag-gated).
- Buffering: none anywhere in-process; emission failures are logged (`metric_emit_error`) and dropped. CloudWatch is the only sink with a break-glass role (`OfferWarmAmpFailed`).

### Contract-drift log (SCAR-style, cited)
| ID | Drift | Receiver response / symptom | Resolution class |
|----|-------|-----------------------------|------------------|
| DRIFT-NS-DMS | Warmer DMS emitted to `Autom8y/AsanaCacheWarmer` while IAM grant allowed only the env namespace | silent `AccessDenied` swallowed; DMS alarm watched an empty namespace; orphan `autom8-asana-cache-warmer-DMS-24h` LIVE-OBSERVED in ALARM since 2026-06-04, last datapoint 2026-06-02 | re-bind (resolve namespace from settings, `cache_warmer.py:81-111`); orphan alarm retirement staged as L-7 (`observability_alarms.SURFACED.md`) |
| DRIFT-ENV-STAGING | production Lambda stamps `environment=staging` | alarms bound to `production` read INSUFFICIENT_DATA/OK-by-absence | matrix update (alarm re-pointed to `staging`, `story_warm_dead_alarm.tf:33-41`) or env fix (stratum, 2026-08-06) |
| DRIFT-DIM-WARMFAIL | Alarm `autom8-asana-cache-warmer-failure-offer` pins `{entity_type=offer}` but `emit_metric` always adds `environment` | zero datapoints in 390d (LIVE-OBSERVED); series exists only as `{environment=staging, entity_type=offer}` | UNRESOLVED (see OBS-DEAD-ALARMS-001) |
| DRIFT-AL5-TIER | AL-5 filter pins event `dataframe_cache_memory_lkg_serve`; code builds the name as `f"dataframe_cache_{tier}_lkg_serve"` | an `s3`-tier LKG serve is invisible to AL-5 (code-inferred, `cache/integration/dataframe_cache.py:768` vs `observability_alarms.tf:451`) | OPEN |
| DRIFT-BINDING | `ticket_sns_topic_arn` default `""` -> alarm with `AlarmActions=[]` | "alarm detects, notifies nobody" (SCAR-ALARM-BINDING-001, N=5) | structural cure `eb9dfc09` on main; default still non-enforcing (`observability_alarms.tf:144-153`) |

**Completeness**: 80%. Grade B. Basis: all emitted signal classes have a documented producer->consumer contract; trace and scrape consumers remain UV-P; AMP live arming UV-P.

---

## Metric Inventory

### ECS / Prometheus domain series (22, all in `api/metrics.py`; prior pass listed 7)

| Series | Type | Labels | Line |
|---|---|---|---|
| `autom8y_asana_dataframe_build_duration_seconds` | Histogram | entity_type | 24 |
| `..._dataframe_cache_operations_total` | Counter | entity_type, tier, result | 31 |
| `..._dataframe_rows_cached` | Gauge | entity_type | 37 |
| `..._dataframe_swr_refreshes_total` | Counter | entity_type, result | 43 |
| `..._dataframe_circuit_breaker_state` | Gauge | project_gid (0/1/2) | 49 |
| `..._api_calls_total` / `..._api_call_duration_seconds` | Counter / Histogram | method, path_pattern, status_code | 59 / 65 |
| `..._cache_lookup_outcome_total` | Counter | entity_type, outcome | 81 |
| `..._build_coordinator_semaphore_utilization` | Gauge | none | 90 |
| `..._rate_limit_429_total` | Counter | namespace (sa/pat/ip/other) | 98 |
| `..._receiver_query_outcome_total` | Counter | entity_type, outcome (deploy-gate SLI denominator) | 108 |
| `..._receiver_query_fallback_cause_total` | Counter | entity_type, cause (cadence_503 / capacity_502 / honest_refusal / data_2xx) | 140 |
| `..._event_loop_lag_seconds` | Histogram | none (fed by `EventLoopLagMonitor`, `api/event_loop_monitor.py:31`) | 523 |
| `..._cpu_thread_semaphore_{in_use,waiting,max}` | Gauge x3 | none | 534-542 |
| `..._serving_stale_total` / `..._lkg_serve_age_seconds` | Counter / Histogram | entity_type | 550 / 556 |
| `..._exports_request_duration_seconds`, `..._exports_predicate_split_outcome_total`, `..._exports_identity_rows_suppressed_total`, `..._exports_rows` | Histogram/Counter | see OBS-EXPORTS-001 | 724-760 |

Plus platform series from `instrument_app`: `autom8y_http_request_duration_seconds`/`_requests_total`/in-flight with `service="asana"` and `route_class` (needs autom8y-telemetry >=0.8.0, `pyproject.toml:30-33`), `autom8y_build_info` (>=0.10.0). The synthetic `route_class="probe"` series `/__sli_heartbeat__` is written every 30s by `SliHeartbeat` (`api/sli_heartbeat.py:62-85,140-146`; started at `api/lifespan.py:373-377`; disable env `ASANA_SLI_HEARTBEAT_DISABLED`); it exists solely so the monorepo emitting-floor dead-man can distinguish "idle" from "down" (`sli_heartbeat.py:1-30`), and is excluded from the business denominator by `route_class` (G-DENOM).

### CloudWatch metrics by namespace

| Namespace | Metrics (emitter) | Alarmed live? (LIVE-OBSERVED 2026-10-05) |
|---|---|---|
| `autom8/lambda` (default `ASANA_CW_NAMESPACE`) | stratum snapshot: `SchedulingStratumSnapshot{RunEpoch,PushEpoch,PushFailed,Refused,Skipped,SchemaLag,ShadowRun,DegenerateSource,Error}`, `SchedulingStratumUniverseCensus`, `SchedulingStratumPostureSignalRows/UniverseRows`, `SchedulingStratumStatusDrift` (`scheduling_stratum_snapshot.py:290-371,1030-1088,1260`); `InvalidateSuccess/Failure/Duration`, `KeysCleared`, `ProjectManifestInvalidated` (`cache_invalidate.py:156-276`); `SelfContinuationInvoked` (`timeout.py:133`); `IdempotencyFinalizeFailure` (`api/middleware/idempotency.py:787`); `WorkflowInvokeCount` (`api/routes/workflows.py:399`); `StatusPush*`, `GidPush*`, `VocabSync*` (`push_orchestrator.py`, `services/gid_push.py:1058-1311`) | stratum series alarmed by 7 `asana-stratum-*` alarms (monorepo-authored, UV-P) |
| `autom8y/cache-warmer` (Lambda env) | `WarmSuccess`, `WarmFailure`, `RowsWarmed`, `CheckpointSaved/Resumed`, `WarmerKeysCovered/Enumerated`, `WarmerCheckpointCleared`, `WarmerAimdEngaged`, `WarmerKeyBudgetExhausted`, `WarmerDeadlineYield`, `TotalDuration`, `WarmerCoverageRate` (`cache_warmer.py:439-651,1220`; `cloudwatch.py:88-109`); `StoryWarmSuccess/Failure`, `StoriesWarmed`, `StoryWarmDuration`, `StoryWarmEntity{TaskCount,Success,Failure}` (`story_warmer.py:210-213,459-495`); `CoalescerDedupCount` (`coalescer.py:50`) | `autom8y-asana-story-warm-dead` (SEV-1, ActionsEnabled=false, ALARM); `...-failure-offer` (wrong dims, never fires); `cache-warmer-bulk-cadence-DMS` on `autom8y/cache-warmer-bulk WarmerCheckpointCleared` (ALARM, actions disabled) |
| `Autom8y/FreshnessProbe` | CLI batch: `MaxParquetAgeSeconds`, `ForceWarmLatencySeconds`, `SectionCount`, `SectionAgeP95Seconds`, `SectionCoverageDelta` (`cloudwatch_emit.py:40-60`); log-derived from the warmer log group: `ActiveOfferRows`, `PopulationFloorBreach`, `ResolverCascadeLoop`, `SectionNameContractViolationError` | `cache-freshness-warning` / `-sustained-p1` + 4 log-derived alarms (`active-offer-rows-collapse`, `population-receipt-below-floor`, `resolver-cascade-loop`, `section-name-contract-violation-error`): all 6 have ActionsEnabled=false; `SectionCoverageDelta` alarm-forbidden by `c6_guard_check` (`cloudwatch_emit.py:88-106`) |
| `Autom8y/AsanaCacheWarmer` | `LastSuccessTimestamp` (retired namespace; the warmer now writes DMS into `_dms_namespace()`) | orphan `autom8-asana-cache-warmer-DMS-24h` (ALARM, no datapoints since 2026-06-02) |
| `Autom8y/AsanaBridgeFleet` | `BridgeFleetHealth`, `LastSuccessTimestamp`, `StatusPushSkipped`, `StatusPushUnmappedEntities` (`workflow_handler.py:300-390`, `push_orchestrator.py:184,252`, `gid_push.py:44,79`) | AL-1/AL-4 authored, NOT live (no `asana-AL1/2/3/4/6` alarms live) |
| `Autom8y/AsanaInsights` (+ `AsanaAudit`, `AsanaWalkthrough`, `AsanaReconciliation`) | per-workflow DMS namespaces: `LastSuccessTimestamp`, `EntitiesProcessed`, `WorkflowDuration` | AL-3 authored, NOT live |
| `Autom8y/AsanaOfferDivergence` | R7 tripwire: `TradingWithoutActiveOfferCount`, `NewlyTradingWithoutActiveOfferCount`, `ActiveOfferRosterSize`, `EvaluationRefused`, `LastRunEpoch`, `...Bookings`, `...ByClass`, `TrafficOfficesEvaluated`, `TrafficLegUnavailable` (`traffic_offer_divergence_tripwire.py:166-188`) | 5 `asana-r7-*` alarms (2 in ALARM: `active-offer-roster-floor`, `evaluator-dead`; all 5 ActionsEnabled=false) |
| `Autom8y/AsanaEnrollmentBridge` | 16 metrics (`enrollment_intent_bridge.py:168-201`) | none found |
| `Autom8y/SubstrateProvability` | `UnprovableCount`, `ProvableCount`, `MaxStalenessAgeSeconds`, `Completeness`, `EvaluatorHeartbeat`, `ExpectedSetMismatchCount`, `ExpectedCount`, `EvaluatedCount`, `EvaluationFailed`, `FutureDatedProofCount`, `ArtifactProvable`, `ActiveRowEconomicNullCount` (`substrate/observe.py:404-440`) | PROV-1..6, 8, 9 live; PROV-7 authored not live |
| `Autom8y/SubstrateServe` | `SubstrateRefusalCount`, `FutureDatedProofCount` (`serve.py:226-244`) | none; emitter unwired |
| `Autom8y/AsanaSubstrateFreshness` | `OfferFrameAgeSeconds{project_gid}` (log-derived, TF `observability_alarms.tf:446-462`) | AL-5 live (ActionsEnabled=false) |
| `Autom8y/AsanaIntakeCF` | `OfficePhoneStampUnresolved` (log-derived, AL-6) | not live |
| `Autom8y/AsanaWarmerCache` | `CacheDegradedMode` (log-derived) | F-1 live; 0 datapoints ever (quiet-when-healthy by design) |
| `Autom8y/AsanaReceiverSLI` | EMF `ReceiverQueryOutcomeSuccess/ServerError`, `ServingStaleTotal` | none; ship-dark |
| `autom8y/asana` | `autom8y-asana-service-error-count` (log filter `ERROR` on service log group) | `autom8y-asana-service-error-count-high` live, actions enabled |
| `autom8y/asana-exports` | `ExportsHandlerComplete` (log filter) | `...-exports-request-presence-DMS` (ALARM, actions disabled) |

### Structurally dark emitters
- **OBS-DATACLIENT-HOOK-001 (NEW)**: `DataServiceClient` metrics (`insights_request_total`, `insights_request_error_total`, `insights_request_latency_ms`, retry counters) pass through `metrics_hook` (`clients/data/client.py:127,153,695`; `_metrics.py:15-40`). `grep metrics_hook= src/` returns zero production wirings (10 in `tests/`), so these metrics are never emitted in production (code-inferred; the only emission path is a hook nobody supplies).
- **OBS-SERVE-EMITTER-DARK-001 (NEW)**: `CloudWatchRefusalEmitter` (`substrate/serve.py:269`) has no construction outside its module; `Autom8y/SubstrateServe` is empty live. Refusals (the "feature not an outage" SLI, `serve.py:228-232`) are therefore uncounted.
- **OBS-EMF-DARK-001**: receiver-SLI EMF is off (`api/metrics.py:354-373`; call site `api/routes/query.py:539`); the deploy-gate claim ("10-min >=99%") cannot be self-proved from a durable sink while it is off.

---

## Trace Inventory

| Span name | Source | Notes |
|---|---|---|
| `metric.compute` | `metrics/compute.py:19` | `record_dataframe_shape=True` |
| `cache.get` | `cache/integration/dataframe_cache.py:241` | enriches current span at `:269-271` |
| `progressive.build` | `dataframes/builders/progressive.py:1004` | span enrichment `:1264` |
| `entity.query_rows` / `entity.query_aggregate` | `query/engine.py:129,383` | span enrichment `:165,422` |
| `predicate.compile` | `query/compiler.py:164` | |
| `entity.join` | `query/join.py:90` | |
| `data_service.fetch_join` | `query/fetcher.py:40` | |
| `entity_query.get_dataframe` | `services/query_service.py:586` | |
| `strategy.resolution.resolve` / `.resolve_group` | `services/universal_strategy.py:201,330` | errors set `StatusCode.ERROR` |
| `resolver.entities.resolve` | `api/routes/resolver.py:351` | attrs: entity_type, criteria_count, project_gid, caller_service |
| `exports.request` | `api/routes/exports.py:352` | six contracted attrs |
| `payment_reconciliation.process_entity` | `automation/workflows/payment_reconciliation/workflow.py:164` | |
| `execute_tool {name}` | `mcp/asana_mcp/observability.py:590-591` | no-op without provider |
| Lambda invocation spans | `@instrument_lambda` (7 of 11 entry points) | exporter UV-P |
| HTTP server/client spans | `instrument_app`, `HTTPXClientInstrumentor` | |
| Span-enrichment helpers (read current span only, no new span) | `dataframes/builders/null_number_recovery.py:111`, `post_build_population_receipt.py:36`, `cascade_validator.py:20` | |

Not instrumented: `bridge_base.execute_async` (H-006), S3/Redis clients, account-status push loop, scheduler/ticker coroutines, `lifecycle/` engine.

---

## Log Inventory

### SDK and configuration
- `autom8y_log` is the mandated primitive; ruff bans `structlog`, `logging`, `loguru`, `httpx` (`pyproject.toml:351-361`). Configuration: `core/logging.py:51-111` (`LogConfig(backend="structlog", level, format="auto", intercept_stdlib=True)` then `reset_logging()` first, `:106-109`). Console when TTY, JSON otherwise.
- Processors: `add_otel_trace_ids`, `_filter_sensitive_data` at `api/lifespan.py:124-127`.

### Log events that are load-bearing for alarms (renaming any of these silently un-wires a monitor)
| Event | Emitted at | Consumed by (LIVE-OBSERVED filter or TF) |
|---|---|---|
| `dataframe_cache_{tier}_lkg_serve` (`memory`/`s3`) | `cache/integration/dataframe_cache.py:768` | AL-5 filter (memory tier only) `observability_alarms.tf:451` |
| `exports_handler_complete` | `api/routes/exports.py:566` | live filter `autom8-asana-exports-request-presence` |
| `cache_degraded_mode` | `cache/backends/redis.py:173,258` | `warmer_cache_degraded_alarm.tf:71` (live) |
| `population_receipt_below_floor` / `population_receipt_ok` | `dataframes/builders/post_build_population_receipt.py:240,242` | live filters on the warmer log group |
| `cascade_loop_detected` | `dataframes/resolver/cascading.py:313` | live filter -> `ResolverCascadeLoop` |
| `section_name_contract_violation` | `dataframes/builders/progressive.py:625,637` | live filter (requires `extra.reseed_window IS FALSE` and level error) |
| `office_phone_cf_not_found` / `office_phone_cf_stamp_failed` | `services/intake_create_service.py:373,388` | AL-6 filter (TF only; not live) |
| `write_authz_would_deny` / `write_authz_denied` / `write_authz_allowed` | `api/write_authz.py:338-362` | NONE (log-only: no metric filter, no alarm; OBSERVE mode computes the same decision and proceeds, `:325-366`) |
| `metric_emit_error` | `lambda_handlers/cloudwatch.py:82` | NONE: the only record of a dropped CloudWatch emission |
| `ERROR` (any level-error line) | everywhere | live filter `autom8y-asana-service-errors` -> `autom8y-asana-service-error-count` -> alarm `autom8y-asana-service-error-count-high` (>10 sum/60s x5, OK) |

### Gaps
- No Lambda-mode custom processor gap remains (RESOLVED, PR #89), but there is no Lambda log pipeline view: all Lambda log groups are quiet since 2026-09-05.
- `exports.py` logs carry `request_id` in `extra` but no `trace_id` in event body; correlation relies on the processor.

---

## SLO Catalog

### Status of the SLO source
`.ledge/specs/cache-freshness-observability.md` (738 lines) is still `status: draft`, authored 2026-04-27 by `thermal-monitor` (frontmatter lines 1-14), last touched by commit `46c322ba` (2026-04-28). It was never ratified in the file. All three SLOs below cover the **Lambda warmer / freshness CLI surface**; there are no API-surface (latency/availability/error-rate) SLO targets in this repo. SLOs for the ECS service live in the monorepo (e.g. the `EcsServiceDenominatorAbsent{service=asana,slo=emitting_floor}` rule referenced at `api/sli_heartbeat.py:3-12`; rule body UV-P).

| SLO | Target / window / denominator | SLI & source | Anchor |
|---|---|---|---|
| SLO-1 ParquetMaxAgeSLO | 95% of CLI invocations over rolling 7d with `MaxParquetAgeSeconds < 21600`; denominator = CLI invocations (assumed O(5)/day) ; error budget 5% (~1.75 stale reads/week); operational tier; tightens to 99%/1h if `active_mrr` is reclassified investor-grade (DEF-3) | `MaxParquetAgeSeconds`, `Autom8y/FreshnessProbe`, emitted by CLI batch `metrics/cloudwatch_emit.py:217` | spec `:105-121` |
| SLO-2 WarmSuccessRateSLO | `WarmSuccess/(WarmSuccess+WarmFailure)` for `entity_type=offer` >= 95% rolling 7d | `cache_warmer.py:590,601` | spec `:123-137` |
| SLO-3 WarmHeartbeatSLO | >= 1 DMS heartbeat per rolling 24h | `emit_success_timestamp(_dms_namespace())` `cache_warmer.py:1420` | spec `:139-151` |

### Other SLI substrate with SLOs defined cross-repo (UV-P on the target numbers)
- Receiver deploy-gate SLI: `RECEIVER_QUERY_OUTCOME{outcome=success|server_error}` with 4xx not counted (`api/metrics.py:108-112,320-322`) plus `serving_stale_total` as the co-read honesty term (`:550-556`; EMF twin `:373-425` is dark). Gate claim in the code comments: >=99% on both arms, 10-min window (`api/metrics.py:314,330`).
- Emitting-floor denominator: `autom8y_http_request_duration_seconds_count{service="asana"}` kept lit by `SliHeartbeat` (probe-class).
- Substrate provability SLIs: `UnprovableCount`, `Completeness`, `EvaluatorHeartbeat` etc. (PROV-1..7) and `MaxStalenessAgeSeconds` (live PROV-8, threshold 7200, 3-of-4 x900s).
- Offer freshness: `autom8y_offer_warm_complete_timestamp{entity_type=offer}` to AMP feeding monorepo `slo_offer_freshness` (`offer_warm_amp.py:15-21`).
- Refusal SLI `SubstrateRefusalCount` (`serve.py:239`): emitter unwired.

### SLI rationale
SLO-1 chooses freshness because `active_mrr` is "internal/operational ... eventual consistency tolerable" (spec DEF-3 anchor); SLO-2 availability of the warm action; SLO-3 liveness of the warmer. Known SLI-validity scars recorded by sibling knowledge: SCAR-FRESHCLOCK-001 (freshness clocks anchored on non-data-age) and AL-5's axis mismatch with the ASR gate (the AL-5 description states it is "NOT an ASR-abort predictor", `observability_alarms.tf:531`).

### Burn-rate alerting
None. ALERT-2 is labelled "SLO Budget Burn" in the spec (`:184`) but is a single-threshold persistence rule (Maximum > 21600 for 6 x 300s), not a multi-window multi-burn-rate construct. AL-5 was tuned three times against flap (history in `observability_alarms.tf:465-651`); the final 3-of-4 x 3600s with `treat_missing_data=missing` and `ok_actions=[]` reduces but does not eliminate flapping (author's own "HONEST LIMIT" at `:600-611`).

### Error-budget policy
The spec states budget arithmetic and per-SLO "breach action" lines (P2 Slack / P1 page) but no freeze/rollback policy and no named governance owner. No policy file exists in the repo.

### Current readings (LIVE-OBSERVED 2026-10-05)
- **SLO-1**: series `MaxParquetAgeSeconds{project_gid=1143843662099250,metric_name=active_mrr}` has data on only 12 of the last 45 days. Daily Maxima: 7 days = 1000.0 (<21600) and 5 days = 5,749,348 to 8,268,952 s (66 to 96 days) on 2026-08-23, 08-25, 09-13, 09-20, 09-21. By day-max that is 7/12 = 58% compliant against a 95% target; true per-invocation compliance is not computable (invocation counts are not emitted). The 1000.0 value recurs exactly and looks like a sentinel/fixture value (UV-P: method = read the CLI call that emits it). Actual invocation cadence (<=12 days in 45) is far below the spec's O(5)/day assumption, so the "5% budget = 1.75 reads/week" arithmetic does not apply.
- **SLO-2**: `WarmSuccess{environment=staging,entity_type=offer}` and `WarmFailure{...}` last datapoints 2026-09-05 / 2026-08-27; zero under `environment=production`. SLO-2 is not computable post 2026-09-05 (dark) and was only ever computable under the `staging` label.
- **SLO-3**: DMS metric namespace `Autom8y/AsanaCacheWarmer` retired; SLO-3 as written is unmeasurable. Successor is PROV-2 heartbeat (also dark since 2026-09-05).

**Completeness**: 72%. Grade C. Basis: SLO inventory, windows, denominators, rationale, budget, current readings and absence of burn-rate/policy all documented with evidence; but the SLOs themselves are draft and unratified, SLO-2/3 are unmeasurable, and cross-repo SLO rule bodies were not read.

---

## Alert Rules

### A. In-repo Terraform (4 files, 15 resource blocks, 18 alarm instances at default variables) vs live

`terraform/services/asana/` has no backend/state and no apply pipeline (`warmer_cache_degraded_alarm.tf:18-24`, `story_warm_dead_alarm.tf:53-58`). Every file is a code-of-record; live resources were created by CLI/another repo. `observability_alarms.tf:8-22` self-labels "AUTHORED / UN-DEPLOYED / UN-ARMED".

| TF alarm | Metric / expression (TF) | Defaults | Live? | Live actions |
|---|---|---|---|---|
| AL-1 x4 `asana-AL1-StatusPushSkipped-{reason}` | `Autom8y/AsanaBridgeFleet StatusPushSkipped{environment,skip_reason}` Sum>0, 3600s (`observability_alarms.tf:226-247`) | ticket tier, `notBreaching` | **No** (metric exists live) | n/a |
| AL-2 `asana-AL2-recon-invocation-gap` | `AWS/Lambda Invocations` <1 per 8h, `breaching` (`:256-274`); PAGE gated on `recon_rule_enabled` (default false) | | **No** | |
| AL-3 `asana-AL3-insights-LastSuccessTimestamp-stale` | `LastSuccessTimestamp` Max <1 over 26h `breaching` (`:287-306`) | | **No** | |
| AL-4 `asana-AL4-prod-BridgeFleetHealth-insights-export` | Min <1, 3600s, `missing` (`:323-344`); needs AI-5 `environment` dimension | | **No** | |
| AL-5 `asana-AL5-offer-frame-stale-{gid}` | `OfferFrameAgeSeconds{project_gid}` Max >7200, 3-of-4 x3600s, `missing`, `ok_actions=[]` (`:527-675`) | | **Yes** | 1 action (`platform-alerts`), **ActionsEnabled=false**, state OK |
| AL-6 `asana-AL6-office-phone-stamp-unresolved` | log-filter `OfficePhoneStampUnresolved` Sum>0, `notBreaching` (`:687-717`) | | **No** (and 0 metrics in `Autom8y/AsanaIntakeCF`) | |
| PROV-1..6 | `Autom8y/SubstrateProvability` UnprovableCount, EvaluatorHeartbeat, Completeness, ExpectedSetMismatchCount, ExpectedCount, FutureDatedProofCount `{environment}` (`substrate_v2_provability_alarms.tf:114-277`) | | **Yes** x6 | **0 AlarmActions on all six**; PROV-2 in ALARM since 2026-09-05 |
| PROV-7 `asana-PROV-7-data-quality-nulls` | `ActiveRowEconomicNullCount` Max>0 (`:302-318`) | | **No** | |
| F-1 `asana-F1-warmer-cache-degraded-mode` | log-filter `CacheDegradedMode` Sum>0, 300s, `notBreaching`, no ok_actions (`warmer_cache_degraded_alarm.tf:82-102`) | | **Yes** | 1 action, enabled, OK; 0 datapoints ever (quiet-by-design) |
| `autom8y-asana-story-warm-dead` | `autom8y/cache-warmer StoryWarmSuccess{environment=staging}` Sum<=0, 2-of-2 x7200s, `breaching`, dual-routed `platform-alerts` + `platform-sre-sev1` (`story_warm_dead_alarm.tf:80-106`) | | **Yes** | 2 actions, **ActionsEnabled=false**, state ALARM since 2026-09-05T10:30 |

Counts: 9 of 18 TF-defined instances are live (AL-5, PROV-1..6, F-1, story-warm-dead); 9 are authored-only (AL-1 x4, AL-2, AL-3, AL-4, AL-6, PROV-7). Live without in-repo TF: `asana-PROV-8-offer-content-stale` (Max>7200, 3-of-4 x900s on `MaxStalenessAgeSeconds`) and `asana-PROV-9-offer-artifact-uncovered` (`ArtifactProvable` Min<1, 4-of-4 x900s, `breaching`; ALARM since 2026-08-19); both ActionsEnabled=false (TF header claims PROV-1..PROV-7, `substrate_v2_provability_alarms.tf:2`). **OBS-BINDING-REPORT-GAP-001**: the always-on `alarm_binding_report` output lists AL-1..6 and PROV-1..6 but omits PROV-7 even though `prov7_actions` is defined (`observability_alarms.tf:761-778` vs `substrate_v2_provability_alarms.tf:101,316-317`), so an unbound PROV-7 would not appear in the report.

Binding cure state: `ticket_sns_topic_arn` default `""` (`observability_alarms.tf:100-119`), `require_alarm_binding` default `false` (`:144-153`, enforced only for AL-5 at `:669-674`). LIVE-OBSERVED: PROV-1..6 still carry zero `AlarmActions` six weeks after the cure merged (the 2026-08-11 measurement in the TF comment named PROV-2 and AL-5 as the unobserved ALARMs; PROV-2 is ALARM again today with no action). This is persistence of SCAR-ALARM-BINDING-001 occurrence 4 (the systemic 'zero-action' count), not a new occurrence.

### B. Live inventory, all asana-named alarms (73; LIVE-OBSERVED 2026-10-05T03:15-03:55Z via `describe-alarms` on prefixes `asana`, `autom8y-asana`, `autom8-asana`)

| Class | Count | Notes |
|---|---|---|
| State: OK / ALARM | 57 / 16 | |
| `ActionsEnabled=false` | 20 (13 OK, **7 ALARM**) | 7 in ALARM and silent: PROV-9, r7-active-offer-roster-floor, r7-evaluator-dead, DMS-24h, bulk-cadence-DMS, exports-request-presence-DMS, **story-warm-dead (SEV-1)** |
| Zero `AlarmActions` | 9 | PROV-1..6, `service-canary-5xx`, `canary-healthy-host-serving`, `canary-response-time` |
| Targets | `autom8y-platform-alerts` 64 bindings; `autom8y-platform-sre-sev1` 16 bindings | |
| Families | Lambda `*-lambda-errors` / `*-lambda-liveness` / `*-dlq-not-empty` for warmer, bulk, section, conversation-audit, insights-export, onboarding-walkthrough, prov-sweep, scheduling-stratum-snapshot, traffic-offer-divergence, unit-reconciliation; 7 `asana-stratum-*`; 5 `asana-r7-*`; PROV-1..6,8,9; ECS cpu/mem/5xx/error-count/canary; redis x3; freshness x6; story-warm-dead; F-1; AL-5 | Authorship of non-TF alarms UV-P (monorepo) |
| Dashboards | 1 asana dashboard `autom8y-asana-service` (3 widgets: ECS CPU, ECS memory, Error Count) among 17 account dashboards | none in-repo; the spec's "Cache Freshness - Overview" (spec `:325-351`) was never built |

### C. Alarms that cannot fire (LIVE-OBSERVED, "which alarms can actually fire")

Method (two questions per alarm): (1) does the metric+exact dimension set the alarm reads have any datapoint? (2) when was the last one? Over 71 metric alarms (2 are metric-math):

**OBS-DEAD-ALARMS-001 - 9 alarms with ZERO datapoints in 390d**
| Alarm | Defect class | Evidence |
|---|---|---|
| `autom8y-asana-redis-cpu` / `-evictions` / `-memory` | **wrong dimension key**: alarm pins `ReplicationGroupId=autom8y-asana-redis`; `AWS/ElastiCache` emits `CacheClusterId=autom8y-asana-redis-001` (list-metrics) | cannot fire; replication group `autom8y-asana-redis` exists |
| `autom8-asana-cache-warmer-failure-offer` | **wrong dimension set**: pins `{entity_type=offer}`; `emit_metric` always adds `environment`, so the series is `{environment=staging,entity_type=offer}`; the spec itself defines the dims without `environment` (`cache-freshness-observability.md` ALERT-3 "Dimensions: entity_type=offer") | cannot fire; real series has 11 day-buckets since 2026-08 |
| `autom8-asana-dataframe-resolver-clientid-drift` | **emitter never landed in this repo**: `CredClientIdDrift` appears nowhere in `src/` | never fired |
| `autom8-asana-unit-reconciliation-duration` / `-failure` / `-move-count-spike` | **orphaned/foreign emitter**: namespace `autom8y/unit-reconciliation` empty; no emitter in `src/` | never fired |
| `asana-F1-warmer-cache-degraded-mode` | quiet-by-design (filter exists on all 3 warmer log groups, LIVE-OBSERVED); has never been exercised end-to-end, so its teeth are unproven | not necessarily dead |

**8 more alarms with no datapoint in the last 30 days** (dark inputs; will read OK/INSUFFICIENT/ALARM by missing-data rule only): `cache-warmer-DMS-24h` (last 2026-06-02), `cache-warmer-section-lambda-errors` (2026-06-03), `conversation-audit-lambda-errors`, `insights-export-lambda-errors`, `insights-export-lambda-liveness`, `onboarding-walkthrough-lambda-errors`, `unit-reconciliation-lambda-errors`, `unit-reconciliation-lambda-liveness`. A further 34 alarms have all of their last-30-day datapoints inside the first 24h bucket of the window (2026-09-05T03:15Z-09-06T03:15Z) and none after: PROV-1..6,8,9; 5 r7; 7 stratum; warmer/bulk/prov-sweep/stratum/traffic Lambda-errors+liveness; 4 log-derived freshness alarms; bulk-cadence-DMS; story-warm-dead; canary-5xx (count-only metric, benign). See OBS-LAMBDA-DARK-001.

**Cannot-fire-by-construction (TF-visible)**: any `treat_missing_data=notBreaching` alarm on a Lambda-emitted metric is OK-by-absence while the Lambda is dark: PROV-1/3/4/5/6, the 4 stratum fire-only alarms, `asana-r7-trading-*`.

Hazard sentences (code-visible, not yet fired): AL-5's filter matches only the `memory` tier (`dataframe_cache.py:768` builds `dataframe_cache_{tier}_lkg_serve`; filter pins `..._memory_lkg_serve`), so an s3-tier LKG serve never produces an AL-5 datapoint. `emit_metric` stamps `environment=staging` unless `ASANA_CW_ENVIRONMENT` is set, so every alarm that pins `environment=production` on a Lambda metric depends on an env var that lives outside this repo.

### D. Runbook linkage
- 13 distinct `RB-*` identifiers appear in alarm descriptions (`RB-STATUSPUSH-SKIP`, `RB-RECON-GAP`, `RB-INSIGHTS-STALE`, `RB-BRIDGEFLEET`, `RB-SUBSTRATE-FRESHNESS`, `RB-INTAKE-CF-1`, `RB-SUBSTRATE-{PROVABILITY,EVALUATOR-DOWN,INCOMPLETE,SET-DRIFT,EMPTY-EXPECTED,FUTURE-STAMP,DATA-QUALITY}`). **0 of 13 resolve to a runbook heading** anywhere in the repo; only 4 are even mentioned outside the Terraform (in `.ledge/reviews/sre-observability-design.md`). (`grep` over `*.md/*.py`, 2026-10-05.)
- Resolving runbooks that do exist: `.ledge/specs/cache-freshness-runbook.md` (400 lines; scenarios Stale-1, Warmer-1, DMS-1, ForceWarm-1, S3-1; alert->runbook table at `:374-383`; also `status: draft`); `docs/runbooks/RUNBOOK-{pipeline-automation,cache-troubleshooting,detection-troubleshooting,freshness-verification-recency,rate-limiting,batch-operations,savesession-debugging,business-model-navigation}.md`; incident runbooks under `.ledge/reviews/` (e.g. `sre-insights-incident-runbook-2026-06-24.md`, `RUNBOOK-read-the-name-s1-2026-09-14.md`). `runbooks/` at repo root contains only Atuin Desktop API-ops notebooks (`runbooks/atuin/*`), not alert runbooks.
- `story-warm-dead` cites `RUNBOOK-platform-sre-sev1-paging-response.md` in the monorepo (UV-P).
- No machine link (annotation/URL) from any alarm to a runbook exists; descriptions embed prose IDs only.

### E. Synthetic monitoring
No scheduled synthetic probe in-repo. Closest: live Lambda `autom8-asana-conversation-audit-freshness-prober` (liveness alarm, last datapoint 2026-10-03, alive), ALB canary alarms (`autom8y-asana-service-canary-*`, targetgroup `a8-asana-green`, 0 actions), `SliHeartbeat` (synthetic in-process, not a probe), and `mcp/canary/test_broken_fixture_canary.py` (CI test).

### F. Alert-fatigue candidates
AL-5 historically 10-12.6 transitions/day (`observability_alarms.tf:485-493,546-552`); mitigated, `ok_actions` dropped by operator ruling 2026-08-12 (`:658-662`). No fire/run counts were collected this pass (UV-P: `describe-alarm-history` per alarm). 

### G. On-call
Not documented in-repo. SNS tiers: notify (`platform-alerts`) and page (`platform-sre-sev1`, SMS+email per TF comment). Escalation policy/rotation owner: UV-P (monorepo `docs/reliability/runbooks/`).

**Completeness**: 80%. Grade B. Basis: every TF alarm plus all 73 live alarms inventoried with state, actions, datapoint liveness; runbook linkage and on-call documented as absent; expressions of monorepo-authored alarms taken from `describe-alarms` rather than source.

---

## Dashboard Surface

None in-repo (no Grafana, CloudWatch dashboard JSON, or `aws_cloudwatch_dashboard` resource in the tree). LIVE-OBSERVED: `autom8y-asana-service` CloudWatch dashboard exists with 3 widgets (ECS CPU, ECS memory, `autom8y/asana` error count) among 17 dashboards in the account. The spec's "Cache Freshness - Overview" dashboard (`cache-freshness-observability.md:325-351`) is unbuilt (no matching dashboard name). Grafana-side dashboards fed by the Prometheus/AMP series: UV-P.

---

## Receiver-Reliability Gaps from the Prior Pass (re-verified)

| ID | Prior claim | Status at `c29f58f4` |
|----|-------------|----------------------|
| RECV-BULK-001 bulk fan-out starves a `max_concurrent_builds=4` coordinator | cap hard-coded 4 | Cap is now a setting `dataframe_max_concurrent_builds` (env `ASANA_DF_MAX_CONCURRENT_BUILDS`), default still 4 (`settings.py:304-310`; `cache/dataframe/build_coordinator.py:133-143`); the settings comment says task resize is "OQ-1-gated ... NOT applied". Receiver semaphore utilization gauge now exists (`api/metrics.py:90`). Partially mitigated, sizing open. |
| RECV-BULK-002 SIGTERM orphans in-flight builds | open | **RESOLVED in-repo**: bounded drain `_drain_background_builds` (`api/lifespan.py:34-80`), `BUILD_DRAIN_TIMEOUT_SECONDS` default 25.0 (`settings.py:871-880`); invariant drain <= ECS deregistration_delay is infra-config and unenforced in code |
| RECV-BULK-003 singleflight coalescing unproven live | open | Code path `build_coordinator_coalesced` still at `cache/dataframe/build_coordinator.py:206`; `Retry-After` on 503 is wired (`api/errors.py:597-610`); no live receipt of a `coalesced` event was sought this pass (UV-P). |

---

## Instrumentation Gaps Registry

| ID | Surface | Sev | Status at `c29f58f4` |
|---|---|---|---|
| OBS-EXPORTS-001 | exports route | P2 | CLOSED in-repo (span, logs, 4 metrics); SLO/alert residual cross-repo |
| H-006 | `automation/workflows/bridge_base.py:191-197` no span on `execute_async` | P3 | OPEN; stated blocker (SDK 0.6.1) obsolete since SDK floor is 0.10.0 |
| LAMBDA-OBS-001 | Lambda entry-point spans | P3 | REOPENED-PARTIAL: 7 of 11 entry points instrumented; stratum, R7 tripwire, enrollment bridge, leads consumer uninstrumented |
| LOG-TRACE-LAMBDA | log-trace in Lambda | P3 | RESOLVED (SDK default chain; PR #89 root fix) - not re-verified live |
| SAMPLING-UNDOC | no sampler config in-repo | P3 | OPEN |
| SLO-API-SURFACE | no ECS/API SLO targets in-repo | P2 | OPEN in-repo (monorepo rules referenced, UV-P) |
| CRED-TOPOLOGY-MATRIX | no matrix instance / no schema path on this machine | P2 | OPEN |
| OTLP-ENDPOINT-OPACITY | OTLP endpoint + auth axis unknown | P2 | OPEN (BLOCKING per rubric) |
| OBS-LAMBDA-DARK-001 (new) | Lambda fleet silent since ~2026-09-05; 34 alarms read OK/ALARM by absence | P1 | OPEN, cause UV-P |
| OBS-ACTIONS-DISABLED-001 (new) | 20 of 73 live alarms `ActionsEnabled=false`; 7 in ALARM incl. SEV-1 story-warm-dead and AL-5 | P1 | OPEN; whether intentional (soak/mute) not recorded in-repo |
| OBS-DEAD-ALARMS-001 (new) | 9 alarms with zero datapoints ever in 390d (3 redis wrong-dimension, 1 warmer wrong-dimension set, 1 clientid-drift no emitter, 3 unit-reconciliation foreign emitter, F-1 quiet-by-design) | P2 | OPEN |
| OBS-ALARM-BINDING-001 (new, persistence) | PROV-1..6 + 3 canary alarms zero `AlarmActions`; `require_alarm_binding` default false | P1 | OPEN; sibling SCAR-ALARM-BINDING-001 |
| OBS-BINDING-REPORT-GAP-001 (new) | `alarm_binding_report` omits PROV-7 | P3 | OPEN |
| OBS-IAC-LIVE-DRIFT-001 (new) | IaC vs live: AL-1..4, AL-6, PROV-7 authored not live; PROV-8/9 live not in IaC; AL-5 live `ActionsEnabled=false` while TF default enabled; story-warm-dead live disabled while TF has no `actions_enabled`; `terraform.tfvars.example:79` says AL-5 defaults are 7200/1800/8 but the file sets 3600/4/3 | P2 | OPEN |
| OBS-AL5-TIER-001 (new) | AL-5 metric-filter pins `memory` tier of an f-string event name; s3-tier serve is invisible | P2 | OPEN (code-inferred) |
| OBS-MCP-NOEXPORT-001 (new) | MCP spans produced, no SDK/exporter/provider; no logs/metrics | P2 | OPEN; module self-labelled prototype |
| OBS-DATACLIENT-HOOK-001 (new) | `DataServiceClient` metrics hook has zero prod wirings | P3 | OPEN (code-inferred) |
| OBS-SERVE-EMITTER-DARK-001 (new) | `CloudWatchRefusalEmitter` unwired; `Autom8y/SubstrateServe` empty | P2 | OPEN |
| OBS-EMF-DARK-001 (new) | receiver EMF ship-dark; `Autom8y/AsanaReceiverSLI` empty | P3 | OPEN, intentional ship-dark |
| OBS-WRITEAUTHZ-001 (new) | `write_authz_would_deny`/`denied` log-only: no filter, no metric, no alarm | P2 | OPEN |
| OBS-RB-UNRESOLVED-001 (new) | 13 `RB-*` runbook IDs in alarm text, 0 resolve | P2 | OPEN |
| OBS-HIGHCARD-001 (new) | `CoalescerDedupCount` dimension `coalescer_key` (unbounded) | P3 | OPEN; unalarmed by design |
| OBS-ENV-LABEL-001 (new) | `ASANA_CW_ENVIRONMENT` default `"staging"`; prod Lambdas mislabelled; `WarmSuccess/Failure` exist only under `staging` | P2 | OPEN (class: workflows-env-tag-drift) |

---

## Knowledge Gaps

1. **OTLP backend, endpoint, auth-routing-field, sampler**: invisible from this repo. Verify: `aws ecs describe-task-definition --task-definition autom8y-asana-service` (env), `autom8y-telemetry` SDK source, backend console.
2. **Prometheus scraper identity** and whether the 22 domain series reach any dashboard/alert (no in-repo rule uses them).
3. **Why the Lambda fleet is dark** (OBS-LAMBDA-DARK-001): `aws events list-rules`, `aws lambda list-event-source-mappings`, deploy history.
4. **Whether `ActionsEnabled=false` on 20 alarms is a deliberate mute**: no in-repo record.
5. **AMP arming state** (`ASR_AMP_EMIT_ENABLED`, `AMP_REMOTE_WRITE_ENDPOINT` on the warmer): not read; AMP workspace not queried.
6. **SNS subscriptions** for `autom8y-platform-alerts` and `autom8y-platform-sre-sev1` were not re-queried; claims are from TF comments dated 2026-08-11/14.
7. **Authorship of the 62 non-TF live alarms**: presumed monorepo `autom8y/asana/main.tf` (cited at `cache_warmer.py:81-95`); source not read.
8. **Alarm history/fire counts** (alert-fatigue evidence) not collected.
9. **Cross-repo SLO rule bodies** (`EcsServiceDenominatorAbsent`, `slo_offer_freshness`) not read.
10. **Live trace/log join** (no sample trace or log-to-trace join obtained).

### Changes since prior version (2026-05-08, hash 8980bcd7 -> c29f58f4)

- **OBS-EXPORTS-001: OPEN -> CLOSED in-repo.** Prior anchors (`exports.py:92`, 0 spans/metrics) are obsolete.
- **Prometheus inventory 7 -> 22** series (`api/metrics.py`); prior table was materially incomplete (receiver SLI, S7 cause, event-loop, CPU semaphore, LKG, exports, 429 split, cache outcome, semaphore utilization).
- **CloudWatch**: prior listed 3 namespaces and 1 `put_metric_data` helper; main has 6 emitter sites and ~16 namespaces (substrate provability/serve, offer divergence, enrollment bridge, bridge fleet, per-workflow DMS, receiver-SLI EMF).
- **New surfaces absent from the prior pass**: AMP remote-write (`offer_warm_amp.py`), `SliHeartbeat`, EMF export, MCP sidecar observability, S7 disaggregated cause, substrate provability suite.
- **Prior "No CloudWatch alarm IaC found in-repo" is wrong at main**: `terraform/services/asana/` has 4 files / 15 alarm resource blocks (never applied by a pipeline from this repo). **Prior "No Prometheus alerting rules" remains true in-repo.**
- **Prior "Dashboard: none" refined**: no in-repo dashboards; one live 3-widget dashboard.
- **Dependency lift**: `autom8y-telemetry` floor 0.6.1 -> 0.10.0 (+`remote-write`), `autom8y-log` 0.5.6 -> 0.7.0. H-006's stated blocker (SDK 0.6.1) no longer holds.
- **LAMBDA-OBS-001 "6 of 6" -> 7 of 11** (entry-point set grew by stratum, R7 tripwire, enrollment bridge, leads consumer).
- **Prior line anchors rotted**: `lifespan.py:77/85` -> `:124-127/:135-137`; `cache_warmer.py:473-504` WarmSuccess -> `:590-601`; `cloudwatch_emit.py:88-106` unchanged. Prior "DMS-1 alarm specified in spec only, no IaC" is superseded: live orphan DMS-24h exists (ALARM, actions disabled) and was superseded by PROV-2.
- **SLO**: the spec is unchanged (still draft). Prior statement "alarms deployment status unverified" is now LIVE-OBSERVED: ALERT-1/2 exist live with `ActionsEnabled=false`; ALERT-3 exists with wrong dimensions (cannot fire); ALERT-4 exists as an orphan; ALERT-2 routes to the notify topic only, not PagerDuty as the spec requires.
- **Prior grade F (45.25) -> C**: the change is evidence-driven (live alarm plane inventoried, signal contracts documented, instrumentation closed), not a claim that the posture improved; the live alarm plane is in worse operational shape (OBS-LAMBDA-DARK-001, OBS-ACTIONS-DISABLED-001).
