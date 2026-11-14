---
domain: obs
generated_at: "2026-11-14T18:16:48Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "gitidx-v1:5a15438a45d829aa10eb9e8b5c92b387fa17dfd228b999cba199073a9191b1e9"
source_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d"
evidence_hash: "gitidx-v1:afa4bc27138c2e0115cdec15692fac0ee688dc7e0121cf211cff4aae1636d183"
anchor_source: "stamp-pin"
stamp: {pin_id: "d55b30ac3e8e8159", pin_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d", body_sha256: "8dfe113390a5a76903b87507f98546638a5b3347b16bd50999db4acea82f40fc"}
confidence: 0.80
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@584c8f79"
---

# Codebase Observability

> Observed at `origin/main@584c8f79` (clean detached worktree; 3,056 tracked files after the env/secret name floor, including 628 Python files under `src/`, 50 under `mcp/`, 845 under `tests/` and 8 files under `terraform/`). Method: AST walks of `src/` and `mcp/` for metric, span and `emit_metric` call sites (constants resolved), a stdlib line search over the manifest file list, a per-package regex coverage sweep, a read of every Terraform and alarm-bearing file, and a read of each emitter module named below. This pass made no outward or live calls, so no statement here is about live AWS, Grafana or AMP state; live facts recorded by the prior pass (2026-10-05) are not carried forward and are listed under Knowledge Gaps. Code and IaC at this ref are the authority. Paths are relative to the repo root; `monorepo:` means the `autom8y` parent repo, which is not in this checkout.

**Stack detection (pre-check)**: observability stack detected. Signals: OpenTelemetry imports in `src/` and `mcp/`, `prometheus_client` in `src/autom8_asana/observability/prometheus_metrics.py:20`, CloudWatch `put_metric_data` at 6 call sites, an AMP remote-write emitter (`src/autom8_asana/lambda_handlers/offer_warm_amp.py`), a prior `.know/obs.md`. No Grafana, Prometheus server, Datadog, New Relic, Honeycomb, Loki, Tempo, Mimir or Pyroscope config file exists in the manifest (checked by file-name pattern), and the compose and Docker files carry no collector or backend service.

**Surfaces at a glance**

| # | Surface | Protocol class | Bound at | State at this ref |
|---|---------|----------------|----------|-------------------|
| P1 | OTel traces and HTTP server metrics via `autom8y-telemetry[aws,fastapi,otlp,remote-write]>=0.10.0` | SDK-managed push (exporter, endpoint, auth not declared in-repo) | `pyproject.toml:41`, `src/autom8_asana/api/main.py:953` | Exporter and sampler configuration invisible from the repo |
| P2 | Prometheus text exposition at `/metrics` | scrape-pull | `instrument_app(...)` at `src/autom8_asana/api/main.py:953`; 22 domain series in `src/autom8_asana/observability/prometheus_metrics.py` | Scraper identity not in-repo |
| P3 | CloudWatch `PutMetricData` | vendor-native HTTPS, IAM role | 6 direct call sites plus the `emit_metric` helper | Emitting code present; live state not checkable |
| P4 | AMP Prometheus remote-write | remote-write, SigV4 | `src/autom8_asana/lambda_handlers/offer_warm_amp.py:65` | Flag-gated, default OFF |
| P5 | CloudWatch EMF JSON line on stdout | log-driver extraction | `src/autom8_asana/observability/prometheus_metrics.py:373` | Ship-dark (flag default OFF) |
| P6 | MCP sidecar spans | OTel API only | `mcp/asana_mcp/observability.py:579` | No SDK or exporter in the runtime dependency set |
| P7 | CloudWatch Logs metric filters (log to metric) | in-AWS | 3 filter resources in `terraform/services/asana/` | Code-of-record only; no apply pipeline in this repo |

**Deployment modes**: ECS FastAPI service (`src/autom8_asana/entrypoint.py` ECS branch, `src/autom8_asana/api/main.py` `create_app`); Lambda family (`src/autom8_asana/lambda_handlers/`, 21 modules, 11 entry-point handlers); MCP sidecar (`mcp/asana_mcp/`, `mcp/serve_stdio.py`); CLIs (`python -m autom8_asana.metrics`, polling and backfill CLIs). `src/autom8_asana/entrypoint.py:15-31` has its own print-based JSON `log()` that does not use the `autom8y_log` SDK.

## Instrumentation Depth

### SDK adoption

Dependency floors (`pyproject.toml`): `autom8y-telemetry[aws,fastapi,otlp,remote-write]>=0.10.0` (`:41`), `autom8y-http[otel]>=0.6.0` (`:22`), `opentelemetry-instrumentation-httpx>=0.42b0` (`:26`), `autom8y-log>=0.7.0,<1.0.0` (`:24`). The comment block at `pyproject.toml:27-40` records why each floor exists: 0.6.0 for `trace_computation`, 0.8.0 for the `route_class` metric label, 0.10.0 for the `autom8y_build_info` emitting floor and `RemoteWriteConfig`. `autom8y_telemetry` is imported in 20 `src/` modules and `opentelemetry` directly in 14 (AST and line search over `src/`, `mcp/`).

| Surface | Mechanism | Anchor |
|---------|-----------|--------|
| FastAPI app (ECS) | `instrument_app(app, InstrumentationConfig(service_name="asana"))`: adds `MetricsMiddleware` as the outermost layer and mounts `/metrics`. The explicit `service_name="asana"` is load-bearing: without it the HTTP duration metric labels default to a generic service name and the per-service SLI is unselectable | `src/autom8_asana/api/main.py:48,941-953` |
| Request-ID middleware | `RequestIDMiddleware` writes `request.state.request_id` and the `X-Request-ID` response header | `src/autom8_asana/api/main.py:604`, `src/autom8_asana/api/middleware/core.py:63-98` |
| Business metric compute | `@trace_computation("metric.compute", ...)` | `src/autom8_asana/metrics/compute.py:19` |
| Cache read | `@trace_computation("cache.get", engine="autom8y-asana")` | `src/autom8_asana/cache/integration/dataframe_cache.py:241` |
| Progressive builder | `@trace_computation("progressive.build")` | `src/autom8_asana/dataframes/builders/progressive.py:1004` |
| Query layer | `entity.query_rows` (`src/autom8_asana/query/engine.py:129`), `entity.query_aggregate` (`src/autom8_asana/query/engine.py:383`), `predicate.compile` (`src/autom8_asana/query/compiler.py:164`), `entity.join` (`src/autom8_asana/query/join.py:90`), `data_service.fetch_join` (`src/autom8_asana/query/fetcher.py:40`), `entity_query.get_dataframe` (`src/autom8_asana/services/query_service.py:586`); all under `src/autom8_asana/` | decorator sites |
| Strategy resolution | manual spans `strategy.resolution.resolve` and `.resolve_group` | `src/autom8_asana/services/universal_strategy.py:201,330` |
| Resolver route | manual span `resolver.entities.resolve` | `src/autom8_asana/api/routes/resolver.py:351` |
| Exports route | manual span `exports.request` with `record_exception=False, set_status_on_exception=False` | `src/autom8_asana/api/routes/exports.py:352-355` |
| Payment reconciliation | `@trace_reconciliation("payment_reconciliation.process_entity")` | `src/autom8_asana/automation/workflows/payment_reconciliation/workflow.py:164` |
| Lambda entry points | `@instrument_lambda` (SDK) | table below |
| Outbound HTTP | global `HTTPXClientInstrumentor().instrument()` at lifespan start; `ImportError` degrades to a warning | `src/autom8_asana/api/lifespan.py:135-137` |
| MCP sidecar | one `execute_tool {name}` span per tool call, per-client `HTTPXClientInstrumentor().instrument_client(ctx.http)` | `mcp/asana_mcp/observability.py:579-604,754-778` |

Span totals (AST walk): 9 `@trace_computation` sites, 1 `@trace_reconciliation`, 4 manual `start_as_current_span` sites in `src/`, plus 1 in `mcp/`: 15 span-producing sites. Three modules enrich the current span without opening a new one (`src/autom8_asana/dataframes/builders/null_number_recovery.py:111`, `src/autom8_asana/dataframes/builders/post_build_population_receipt.py:36`, `src/autom8_asana/dataframes/builders/cascade_validator.py:20`).

### Lambda entry-point instrumentation

Entry-point handlers: 11 (7 modules define `def handler(event, context)`; 4 more are `handler = create_workflow_handler(...)` assignments). `@instrument_lambda` covers 7:

| Handler | Instrumented | Anchor |
|---------|--------------|--------|
| `cache_warmer` | yes | `src/autom8_asana/lambda_handlers/cache_warmer.py:1273` |
| `cache_invalidate` | yes | `src/autom8_asana/lambda_handlers/cache_invalidate.py:298` |
| `prov_sweep` | yes | `src/autom8_asana/lambda_handlers/prov_sweep.py:221` |
| `conversation_audit`, `insights_export`, `onboarding_walkthrough`, `payment_reconciliation` | yes, via `create_workflow_handler` | `src/autom8_asana/lambda_handlers/workflow_handler.py:96`; assignments at `src/autom8_asana/lambda_handlers/conversation_audit.py:52`, `src/autom8_asana/lambda_handlers/insights_export.py:59`, `src/autom8_asana/lambda_handlers/onboarding_walkthrough.py:118`, `src/autom8_asana/lambda_handlers/payment_reconciliation.py:60` |
| `scheduling_stratum_snapshot` | NO | `src/autom8_asana/lambda_handlers/scheduling_stratum_snapshot.py:1245` |
| `traffic_offer_divergence_tripwire` | NO | `src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py:1083` |
| `enrollment_intent_bridge` | NO | `src/autom8_asana/lambda_handlers/enrollment_intent_bridge.py:699` |
| `leads_consumer` | NO | `src/autom8_asana/lambda_handlers/leads_consumer.py:50` |

The four uninstrumented handlers do emit CloudWatch heartbeat or epoch metrics (see Metric inventory), so they are observable by metric but not by span. 7 of 11 is 63.6% span coverage at the entry-point level.

### Auto-instrumentation

Only `HTTPXClientInstrumentor` is wired (global on ECS at `src/autom8_asana/api/lifespan.py:137`; per client in the MCP at `mcp/asana_mcp/observability.py:774`); `autom8y-http[otel]` adds transport-level propagation inside the SDK. No boto3/botocore, Redis, or database instrumentor appears in `pyproject.toml` or `src/`, so S3 and Redis calls are not auto-traced. The `src/autom8_asana/automation/workflows/bridge_base.py:191-197` comment still says `trace_computation` is unavailable in SDK 0.6.1; the pin is now 0.10.0 and `trace_computation` is imported in 8 modules (9 decorator sites), so the stated blocker is obsolete while the gap (no span on bridge `execute_async`) remains.

### Trace propagation

Outbound W3C `traceparent` is injected by the httpx instrumentors named above. The only explicit `propagate.inject` is the MCP carrier path (`mcp/asana_mcp/observability.py:570-575`); there is no `propagate.extract` anywhere in `src/` or `mcp/`, so inbound extraction on the ECS app is delegated to `instrument_app` inside the SDK [INFERRED: SDK source not in this tree]. `mcp/tests/test_span_and_traceparent.py` and `mcp/tests/test_assembly_floor.py` prove span creation and header injection against an `InMemorySpanExporter`; that is a fake-collector test and is not evidence of a real cross-service trace. No sample production trace was obtained.

### MCP island

`mcp/pyproject.toml:36-37` lists `opentelemetry-api` and `opentelemetry-instrumentation-httpx`; `opentelemetry-sdk` appears only in the `dev` extra (`:49`). No `TracerProvider`, exporter or `set_tracer_provider` exists in `mcp/asana_mcp/` (line search). With only the API installed, `trace.get_tracer(...)` returns a no-op tracer, so the `gen_ai.*` and `com.autom8y.mcp.*` attributes (`mcp/asana_mcp/observability.py:125-134`) and the honesty attributes are produced but exported nowhere unless the host process installs a provider [INFERRED from OTel API semantics]. The MCP has no logging (no `logging` or `get_logger` use in `mcp/asana_mcp/`) and no metrics; refusals (`RateCapExceeded`, `asyncio.timeout` guard) attach `com.autom8y.mcp.refusal.cause` to the span only (`:670,:686`). The module self-describes as a reference-posture prototype (`:3`) with six listed shortcuts (`:35-60`). Opt-in content capture is `ASANA_MCP_OTEL_CAPTURE_CONTENT` (`:137`), default off.

### Logging

- Setup: `src/autom8_asana/core/logging.py:41-111` wraps `autom8y_log` (`LogConfig(backend="structlog", format="auto", intercept_stdlib=True)`), and calls `reset_logging()` before `configure_logging` so processors passed in are not dropped by the SDK's import-time auto-config (`:97-109`). The only runtime call is the ECS lifespan at `src/autom8_asana/api/lifespan.py:124-128` with `additional_processors=[add_otel_trace_ids, _filter_sensitive_data]`. Log level comes from `ApiSettings.log_level` (env `ASANA_API_LOG_LEVEL`, `src/autom8_asana/core/api_settings.py:63`); `debug` selects console format (`src/autom8_asana/api/lifespan.py:126`).
- CLIs call `configure(...)` directly (`src/autom8_asana/automation/polling/cli.py:236`, `src/autom8_asana/automation/forwarding_stage_backfill/cli.py:197`, `src/autom8_asana/automation/polling/polling_scheduler.py:630`); the polling package also keeps a parallel `StructuredLogger` facade (`src/autom8_asana/automation/polling/structured_logger.py`) that delegates to the same SDK configure at `:95-98`.
- No Lambda handler calls `configure()`. Lambda logs therefore ride the SDK's first-use auto-config and whatever `instrument_lambda` does inside the SDK; the satellite's `_filter_sensitive_data` redaction processor is wired on the ECS surface only [INFERRED: Lambda-side behavior depends on SDK code not in this tree].
- Redaction: `SENSITIVE_FIELDS = {authorization, token, pat, password, secret}` substring match on log keys (`src/autom8_asana/api/middleware/core.py:32-56`).
- Import ban: ruff `flake8-tidy-imports.banned-api` forbids `loguru`, `structlog`, stdlib `logging`, `logging.getLogger` and raw `httpx` (`pyproject.toml:510-522`). Stdlib `logging` still appears in `src/autom8_asana/_defaults/log.py:9,54` (the SDK-default provider shim). `get_logger` is referenced in 257 of 628 `src/` Python files (regex over the manifest).
- Request access logging: `RequestLoggingMiddleware` is defined (`src/autom8_asana/api/middleware/core.py:101`) and re-exported but is not mounted by `create_app`; only `SecurityHeadersMiddleware`, `RequestIDMiddleware` and the idempotency middleware are added by this repo (`src/autom8_asana/api/main.py:591,604`, `extra_middleware` at `:543-545`). Whether `create_fleet_app` (external) mounts its own access log is not visible here.
- Log-trace correlation: `add_otel_trace_ids` is wired on ECS only (`src/autom8_asana/api/lifespan.py:15,127`). `trace_id`/`span_id` appear as fields in `src/autom8_asana/observability/rail_delivery/delivery_receipt.py:78` and `src/autom8_asana/observability/rung_receipts/schema.py:209` as receipt data, not log correlation. HTTP `X-Request-ID` (16 hex chars, `src/autom8_asana/api/middleware/core.py:92`) and the SDK `CorrelationContext` ids (`src/autom8_asana/observability/correlation.py:14-33`) are separate namespaces and are not bridged.
- Rate-limit 429 namespace logging (PR #537 range): `rate_limit_exceeded_namespace_handler` (`src/autom8_asana/api/errors.py:723`) computes the key namespace, calls `record_rate_limit_429(namespace)` (`:758-760`, fire-and-forget), then logs `rate_limit_exceeded` with only `namespace` and `method` (`:766-769`, never the key), then delegates to SlowAPI (`:773-775`). It is registered for `RateLimitExceeded` at `:818`. Namespaces: `sa` (`src/autom8_asana/api/rate_limit.py:83`), `jwt` (`:101`), `pat`, `ip`; the metric collapses anything else to `other` (`src/autom8_asana/observability/prometheus_metrics.py:306`).

### Sampling

No sampler is configured in-repo. A git-grep with the floor exclusions found no `OTEL_EXPORTER`, `OTEL_SERVICE_NAME`, `OTEL_TRACES` or `OTEL_RESOURCE` string in any non-test tracked file outside `.know/` and a prototype README (`prototypes/autom8y_telemetry/README.md:163`); the same command and pathspec found `ASR_AMP_EMIT_ENABLED` and `AMP_REMOTE_WRITE_ENDPOINT` in `src/autom8_asana/lambda_handlers/offer_warm_amp.py:31,90` (positive control). Sampling rate, exporter and endpoint are therefore delegated to the SDK and the deployed task or function environment.

### Instrumentation gaps (measured)

Per-package regex sweep over `src/autom8_asana/` (counts of non-trivial `.py` files with at least one logger call, span site, or metric emit; package init files under 5 non-empty lines are skipped; the metric regex is deliberately broad, so the metric column is an upper bound):

| Package | Files | With logger | With span | With metric emit |
|---------|-------|-------------|-----------|------------------|
| `batch` | 3 | 0 | 0 | 0 |
| `contracts`, `domain`, `patterns`, `readout` | 2, 3, 3, 4 | 0 | 0 | 0 |
| `protocols` | 9 | 0 | 0 | 1 (the emitter port) |
| `trigger` (dark D6 package) | 7 | 4 | 0 | 0 |
| `lifecycle` | 18 | 15 | 0 | 2 |
| `models` | 61 | 21 | 0 | 0 |
| `persistence` | 20 | 6 | 0 | 0 |
| `resolution` | 19 | 11 | 0 | 0 |
| `api` | 63 | 36 | 3 | 8 |
| `lambda_handlers` | 21 | 16 | 4 | 13 |

Notable: `src/autom8_asana/trigger/` (the D6 webhook shadow receiver; its docstring states nothing in production constructs it, `src/autom8_asana/trigger/__init__.py:1-21`) has structured log events in `src/autom8_asana/trigger/hook_environment.py`, `src/autom8_asana/trigger/hook_registry.py`, `src/autom8_asana/trigger/hook_store.py` and `src/autom8_asana/trigger/registration.py` and no metric or span anywhere; `src/autom8_asana/trigger/ports_webhooks.py` and `src/autom8_asana/trigger/watched_projects.py` have no logging. The receiver route, signature check and decision engine are not yet in the tree, so there is no instrumented request path to compare. Other gaps: the generic bridge `execute_async` (no span); `AccountStatusPushLoop` (`src/autom8_asana/api/status_push.py:231`, 7 logger calls, no span or metric); the 4 uninstrumented Lambda handlers above; the whole `lifecycle/` engine (logs only; transitions persist to parquet via `StageTransitionEmitter`, `src/autom8_asana/lifecycle/observation.py`, which is a data record, not telemetry); S3 and Redis clients.

**Completeness self-assessment**: SDK adoption, span inventory, Lambda coverage, logging setup, propagation and gaps are all documented from code with anchors. Not obtained: a sampled trace, a log-to-trace join, the sampler, and the exporter protocol.

## Credential Topology Integrity

### Interpretation and limits

This section records, from code and non-floored config only, every telemetry binding the repo makes as a tuple of (protocol, scope, auth-routing-field), the env-var and settings NAMES that carry endpoints and auth, where each is read, and how each binds to its receiver. No value, token, account id or internal hostname is recorded. Two inputs the criterion asks for were not available: (a) the `credential-topology-matrix` schema file exists in the operator's pinakes skill directory but its file name matches the credential name floor, so it was not opened; no matrix instance exists in this repo (manifest search for the file-name pattern returned nothing); (b) the OTLP binding's routing axis is delegated to the SDK and is not declared anywhere in this tree. Per the rubric's floor clause, binding (b) is recorded as an explicitly declared unknown rather than an omitted axis; a stricter reader would apply the F floor to it.

### Push and pull bindings: (protocol, scope, auth-routing-field)

| ID | Binding | protocol | scope | auth-routing-field | Names read (where) |
|----|---------|----------|-------|--------------------|--------------------|
| T1 | CloudWatch `PutMetricData` from ECS and Lambda (6 call sites: `src/autom8_asana/cache/dataframe/coalescer.py:50`, `src/autom8_asana/lambda_handlers/cloudwatch.py:68`, `src/autom8_asana/metrics/cloudwatch_emit.py:217`, `src/autom8_asana/substrate/observe.py:519,673`, `src/autom8_asana/substrate/serve.py:341`, all under `src/autom8_asana/`) | vendor-native HTTPS, SigV4 | CloudWatch metric namespace (literal per emitter) | ambient task or execution role identity; a datapoint's alarm binding is the exact triple (namespace, metric name, dimension set), with no tenant or stack axis | `ASANA_CW_NAMESPACE` and `ASANA_CW_ENVIRONMENT` via `ObservabilitySettings` (`src/autom8_asana/settings.py:766-796`, prefix at `:783`, alias at `:791`, default `staging` at `:794`); `AWS_REGION` or `ASANA_CACHE_S3_REGION` (`src/autom8_asana/metrics/cloudwatch_emit.py:116`, `src/autom8_asana/substrate/observe.py:459`) |
| T2 | AMP Prometheus remote-write of `autom8y_offer_warm_complete_timestamp{entity_type}` | Prometheus remote-write over HTTPS, snappy, SigV4 | AMP workspace plus region, encoded in the endpoint | SigV4 identity from `resolve_credentials()` (`src/autom8_asana/lambda_handlers/offer_warm_amp.py:108,125-132`); workspace routing is the endpoint URL | `ASR_AMP_EMIT_ENABLED`, `AMP_REMOTE_WRITE_ENDPOINT`, `AWS_REGION`, all read inside the SDK's `RemoteWriteConfig.from_env()` (`src/autom8_asana/lambda_handlers/offer_warm_amp.py:30-32,87`); gate is `cfg.is_active` (`:88-100`) |
| T3 | OTLP traces (and any metrics or logs the SDK exports) | push-HTTP or push-gRPC, not determinable from this repo | not determinable | not determinable (declared unknown; see limits) | no name read in-repo; `pyproject.toml:41` extra `otlp` |
| T4 | `/metrics` scrape | pull | in-process default registry | none on the producer side in-repo; whether `/metrics` is JWT-excluded depends on the external `DEFAULT_EXCLUDE_PATHS` (`src/autom8_asana/api/main.py:46,461`); the repo adds only `/redoc`, webhook, and PAT-route exclusions (`:462-479`) | none |
| T5 | EMF line to stdout, extracted by the log driver | log-driver | log group, plus EMF namespace `Autom8y/AsanaReceiverSLI` and dimension `arm` | log-group IAM; extraction pipeline is not in this repo | `RECEIVER_SLI_EMF_ENABLED` read at call time (`src/autom8_asana/observability/prometheus_metrics.py:355-370`) |
| T6 | CloudWatch Logs metric filters to alarms | in-AWS | log group | none (AWS-internal) | variable `asana_service_log_group` (`terraform/services/asana/observability_alarms.tf:438-442`), `warmer_log_groups` (`terraform/services/asana/warmer_cache_degraded_alarm.tf:48-60`) |
| T7 | Alarm action targets | SNS publish | SNS topic | topic identifier supplied by variable | `ticket_sns_topic_arn`, `page_sns_topic_arn`, `create_ticket_topic` (`terraform/services/asana/observability_alarms.tf:94-142`), `story_warm_dead_notify_topic_arn` and `story_warm_dead_page_topic_arn` (`terraform/services/asana/story_warm_dead_alarm.tf:64-78`), `warmer_cache_degraded_topic_arn` (`terraform/services/asana/warmer_cache_degraded_alarm.tf:37-46`); the three non-AL defaults are literal topic identifiers in the `.tf` and are not transcribed here |
| T8 | CI red-detector: nightly live smoke publishes to the notify-tier SNS topic when red | SNS publish from a GitHub Actions job | the fleet notify topic | a long-lived key pair "bridged" from a CI secret in Secrets Manager into step outputs (masked), because the OIDC role cannot read the durable-cache S3 path; the OIDC role itself is chosen by repo variables `LIVE_SMOKE_ROLE` or `AWS_ACCOUNT_ID` | `.github/workflows/nightly-live-smoke.yml:113-146` (OIDC and bridge), `:257-277` (page-on-red), env names `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` at the page step; the header (`:60-72`) states the exit plan (delete the bridge when a dedicated smoke role exists) and an honest limit: a failure before the bridge step cannot page |
| T9 | MCP traceparent hop to the satellite | W3C trace context over httpx | per-request header on `ctx.http` | none of its own; the traced hop is authenticated by the MCP's S2S token mint (`mcp/asana_mcp/bridge.py`), which is not a telemetry credential | `ASANA_MCP_BASE_URL`, `AUTOM8Y_ASANA_URL` (`mcp/asana_mcp/settings.py:39-40`) |

Other telemetry-adjacent env names (not credentials): `ASANA_API_LOG_LEVEL`, `ASANA_API_DEBUG` (`src/autom8_asana/core/api_settings.py:63-72`); `ASANA_SLI_HEARTBEAT_DISABLED` (`src/autom8_asana/api/sli_heartbeat.py:93`); `SUBSTRATE_PROV_ENVIRONMENT`, `SUBSTRATE_V2_S3_BUCKET` (`src/autom8_asana/lambda_handlers/prov_sweep.py:180-181`); `AUTOM8_LEADS_BRIDGE_ENABLED` (`src/autom8_asana/lambda_handlers/leads_consumer.py:38`); `TRAFFIC_OFFER_DIVERGENCE_*` (`src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py:120-136`); `ASANA_MCP_RATE_*` and `ASANA_MCP_PAT_*` (`mcp/asana_mcp/observability.py:159-165`). `LOG_LEVEL`, `LOG_FORMAT`, `NO_COLOR`, `FORCE_COLOR` are documented as SDK-read overrides (`src/autom8_asana/core/logging.py:11-14`).

### Matrix cross-reference and bind-time fixtures

- Matrix entries: none in this repo (BLOCKING per the rubric for every row above).
- Bind-time fixtures that do exist are name-and-dimension binding tests, not credential validity tests: `tests/unit/substrate/test_observe.py:784` (`test_terraform_alarms_bind_to_emitted_metric_identities`, a textual parse of the `.tf` diffed against `build_metric_data`) pins namespace, metric name and dimension-key set for the substrate alarms; `tests/unit/lambda_handlers/test_scheduling_stratum_snapshot_durability.py:338` pins the stratum `ALARM_BOUND_METRICS` set against its monorepo alarm half; `tests/unit/lambda_handlers/test_offer_warm_amp.py` guards the AMP series name and label; `tests/unit/api/test_receiver_sli_emf_export.py` covers the EMF document; `tests/unit/api/test_build_info_seal.py` seals `autom8y_build_info`. No fixture validates T1, T3 or T8 at bind time, and none exercises a known-bad credential.

### Expected success and failure responses per tuple

- T1: success is a normal `put_metric_data` return. Every failure collapses into a swallowed exception and a warning log: `metric_emit_error` (`src/autom8_asana/lambda_handlers/cloudwatch.py:79-85`), `coalescer_dedup_metric_failed` (`src/autom8_asana/cache/dataframe/coalescer.py:65`), `substrate_provability_emit_failed` (`src/autom8_asana/substrate/observe.py:525`), `substrate_data_quality_emit_failed` (`:678`), `substrate_serve_emit_failed` (`src/autom8_asana/substrate/serve.py:344`), or a stderr line in the CLI (`src/autom8_asana/metrics/cloudwatch_emit.py:228`). An access-denied on an out-of-grant namespace, a missing region, and a throttle are indistinguishable at the metric layer; only logs carry them. Precedent: the comment at `src/autom8_asana/lambda_handlers/cache_warmer.py:81-96` records that the dead-man timestamp was once emitted to a namespace outside the role's grant and silently dropped until the namespace was resolved from settings (`_dms_namespace`, `:99-107`).
- T2: success is a 2xx from the workspace. Failure is deliberately loud: error logs `offer_warm_amp_failed_no_credentials` (`:132`) and `offer_warm_amp_emission_failed` (`:151`) plus the CloudWatch counter `OfferWarmAmpFailed{entity_type, reason}` with `reason` in `no_credentials` or `push_failed` (`:173`). Disabled or unconfigured is a debug-level skip, `offer_warm_amp_skipped_disabled` (`:94`).
- T3, T4, T6, T7: not observable from this repo. T5: the stdout write is wrapped so it never raises; a serialization failure logs `receiver_sli_emf_emit_failed` at debug (`src/autom8_asana/observability/prometheus_metrics.py:438-446`). T8: failure before the bridge step is documented as un-pageable.

### Bake-at-apply coupling and rotation

- T1 and T2 use role identity, so there is no secret to rotate in-repo; rotation is an IAM or deploy-environment change outside this tree (no debt-ledger pointer exists in this repo).
- Namespace and `environment` literals are baked in three places that must agree by convention: the function or task env (`ASANA_CW_NAMESPACE`, `ASANA_CW_ENVIRONMENT`), the emitter constants, and the alarm definitions. `ASANA_CW_ENVIRONMENT` defaults to `staging` (`src/autom8_asana/settings.py:794`), so any function that omits it stamps `environment=staging` on every `emit_metric` datapoint. The repo documents this drift in two places: `terraform/services/asana/story_warm_dead_alarm.tf:33-41` hard-codes `environment = "staging"` on purpose because the production warmer is described as not setting the variable, and `src/autom8_asana/lambda_handlers/scheduling_stratum_snapshot.py:244-251` says the stratum producer was fixed by setting it in the paired infra change.
- Namespaces are defined in 16 literal places in `src/` (list under Signal Pipe Contracts) plus 3 in Terraform; a rename on either side silently un-wires an alarm. Four modules state the byte-exact seam in comments: `src/autom8_asana/lambda_handlers/scheduling_stratum_snapshot.py:233-246`, `src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py:160-166`, `src/autom8_asana/substrate/observe.py:400-404`, `src/autom8_asana/lambda_handlers/enrollment_intent_bridge.py:150-166` (the last states that no alarm half exists yet).

### 2-axis bifurcation check

Within this repo every telemetry binding routes on the same axis (IAM identity plus namespace), so there is no protocol-level split of the kind the rubric describes; the OTLP axis cannot be evaluated here. A different, in-repo bifurcation exists on the dimension axis of the same receiver: `emit_metric` stamps `environment` from `ASANA_CW_ENVIRONMENT` (default `staging`, `src/autom8_asana/lambda_handlers/cloudwatch.py:52-54`), while the substrate emitters stamp `environment` from their own constructor argument defaulting to `production` (`src/autom8_asana/substrate/observe.py:415`, `src/autom8_asana/substrate/serve.py:233`, `SUBSTRATE_PROV_ENVIRONMENT` at `src/autom8_asana/lambda_handlers/prov_sweep.py:181`), and the matching alarm variable defaults to `production` (`terraform/services/asana/observability_alarms.tf:38-42`). A Lambda that emits through both paths can write the same logical `environment` dimension with two different values. This is flagged, not resolved.

**Completeness self-assessment**: 8 of 9 bindings decomposed into tuples with in-repo evidence; the OTLP axis is declared unknown; no matrix instance or schema read; no credential-validity fixture exists.

## Signal Pipe Contracts

### Per-signal-class contract

| Signal class | Producer | Wire protocol | Endpoint / sink | Auth surface | Consumer | Hops and retry posture |
|---|---|---|---|---|---|---|
| Traces (ECS) | `autom8y_telemetry` SDK, 9 `@trace_computation`, 1 `@trace_reconciliation`, 4 manual spans | SDK-managed OTLP (HTTP vs gRPC not determinable) | not declared in-repo | not declared in-repo (T3) | not determinable | direct push assumed; collector presence unknown |
| Traces (Lambda) | `@instrument_lambda` on 7 of 11 handlers | SDK-managed | not declared in-repo | not declared in-repo | not determinable | per-invocation flush behavior is SDK-internal |
| Traces (MCP) | `opentelemetry-api` only | none | none | none | none unless the host installs a provider | zero hops by default |
| Metrics, domain (ECS) | `prometheus_client` default registry, 22 series | scrape-pull text | `/metrics` mounted by `instrument_app` | none producer-side (T4) | scraper not in-repo | in-memory, fire-and-forget (`src/autom8_asana/observability/prometheus_metrics.py:1-10`) |
| Metrics, platform (ECS) | `instrument_app` `MetricsMiddleware`: `autom8y_http_request_duration_seconds` with `service="asana"` and `route_class`, a requests counter, an in-flight gauge, `autom8y_build_info` | scrape-pull | `/metrics` | none producer-side | monorepo SLO rules (not in this tree) | `SliHeartbeat` re-observes a probe-class sample every 30 s (`src/autom8_asana/api/sli_heartbeat.py:62,112-148`) |
| Metrics, CloudWatch (ECS and Lambda) | `emit_metric` helper plus 5 direct `put_metric_data` sites | AWS JSON over HTTPS | CloudWatch in the function's region | SigV4 role (T1) | CloudWatch and alarms | synchronous, best-effort, exceptions swallowed to a warning log, no retry beyond SDK defaults, no buffer |
| Metrics, AMP | `emit_offer_warm_complete` | remote-write, snappy | endpoint from env (T2) | SigV4 | monorepo recording rules (named in comments at `src/autom8_asana/lambda_handlers/offer_warm_amp.py:15-21`; not in this tree) | 1 hop, 1 POST per entity on `WarmResult.SUCCESS`; failure becomes the `OfferWarmAmpFailed` counter |
| Metrics, EMF | `emit_receiver_sli_emf` | one JSON line on stdout | log driver then extraction | log-group IAM (T5) | deploy gate and monorepo alarm (contract name at `src/autom8_asana/observability/prometheus_metrics.py:352-354`) | off unless `RECEIVER_SLI_EMF_ENABLED` is truthy; swallows all errors |
| Logs | `autom8y_log` structlog, JSON when no TTY | stdout | ECS log group named in `terraform/services/asana/observability_alarms.tf:438-442`; Lambda log groups named in `terraform/services/asana/warmer_cache_degraded_alarm.tf:55-59` | IAM | CloudWatch Logs; 3 metric-filter resources | 1 hop; indexing downstream not in-repo |
| Profiles | none | n/a | n/a | n/a | n/a | n/a |
| Events | EventBridge domain events from `_publish_bridge_event` (`src/autom8_asana/lambda_handlers/workflow_handler.py:390`) | n/a | n/a | n/a | not telemetry | n/a |

Two synchronous CloudWatch calls sit on the ECS request path: `src/autom8_asana/api/routes/workflows.py:399` (once per workflow invoke, after the awaited workflow) and `src/autom8_asana/api/middleware/idempotency.py:787` (only on a finalize failure). Both call the blocking boto3 helper from async code; the Prometheus module's own contract is "no synchronous I/O" (`src/autom8_asana/observability/prometheus_metrics.py:7`), so these two are the exceptions.

### Metric inventory (measured)

**Prometheus domain series: 22** (AST walk of `src/autom8_asana/observability/prometheus_metrics.py`: 10 Counters, 6 Gauges, 6 Histograms). `src/autom8_asana/api/metrics.py` is now a re-export shim (`:1`) and `src/autom8_asana/api/main.py:555` imports it only to trigger registration.

| Series | Type | Labels | Defined | Emitted at |
|---|---|---|---|---|
| `autom8y_asana_dataframe_build_duration_seconds` | Histogram | entity_type | `:24` | no call site |
| `autom8y_asana_dataframe_cache_operations_total` | Counter | entity_type, tier, result | `:31` | `src/autom8_asana/cache/integration/dataframe_cache.py:312,333,615,641,755` |
| `autom8y_asana_dataframe_rows_cached` | Gauge | entity_type | `:37` | `src/autom8_asana/cache/integration/dataframe_cache.py:973` |
| `autom8y_asana_dataframe_swr_refreshes_total` | Counter | entity_type, result | `:43` | `src/autom8_asana/cache/integration/dataframe_cache.py:1344` |
| `autom8y_asana_dataframe_circuit_breaker_state` | Gauge | project_gid | `:49` | no call site |
| `autom8y_asana_api_calls_total` | Counter | method, path_pattern, status_code | `:59` | no call site |
| `autom8y_asana_api_call_duration_seconds` | Histogram | method, path_pattern | `:65` | no call site |
| `autom8y_asana_cache_lookup_outcome_total` | Counter | entity_type, outcome | `:81` | `src/autom8_asana/services/universal_strategy.py:859,888` |
| `autom8y_asana_build_coordinator_semaphore_utilization` | Gauge | none | `:90` | `src/autom8_asana/services/universal_strategy.py:1089,1109` |
| `autom8y_asana_rate_limit_429_total` | Counter | namespace | `:98` | `src/autom8_asana/api/errors.py:760` |
| `autom8y_asana_receiver_query_outcome_total` | Counter | entity_type, outcome | `:108` | `src/autom8_asana/api/routes/query.py:533` |
| `autom8y_asana_receiver_query_fallback_cause_total` | Counter | entity_type, cause | `:140` | `src/autom8_asana/api/routes/query.py:535` |
| `autom8y_asana_event_loop_lag_seconds` | Histogram | none | `:523` | `src/autom8_asana/api/event_loop_monitor.py:52,84` |
| `autom8y_asana_cpu_thread_semaphore_in_use` / `_waiting` / `_max` | Gauge x3 | none | `:534,538,542` | `src/autom8_asana/dataframes/concurrency.py:82` |
| `autom8y_asana_serving_stale_total` | Counter | entity_type | `:550` | `src/autom8_asana/cache/integration/dataframe_cache.py:764` |
| `autom8y_asana_lkg_serve_age_seconds` | Histogram | entity_type | `:556` | `src/autom8_asana/cache/integration/dataframe_cache.py:764` |
| `autom8y_asana_exports_request_duration_seconds` | Histogram | entity_type, format | `:724` | `src/autom8_asana/api/routes/exports.py:581` |
| `autom8y_asana_exports_predicate_split_outcome_total` | Counter | entity_type, date_filter_applied, section_default_applied | `:736` | `src/autom8_asana/api/routes/exports.py:550` |
| `autom8y_asana_exports_identity_rows_suppressed_total` | Counter | entity_type | `:745` | `src/autom8_asana/api/routes/exports.py:555` |
| `autom8y_asana_exports_rows` | Histogram | entity_type, stage | `:755` | `src/autom8_asana/api/routes/exports.py:559` |

Search of `src/` and `mcp/` (call sites and direct constant use) found no caller for the 4 series marked "no call site" or for their helpers `record_build_duration`, `record_circuit_breaker_state`, `record_api_call`; the same search shape found callers for the other recorders (positive control). Those 4 are defined, exported by the shim, and never incremented. Label vocabulary notes: S7 `cause` is closed to `cadence_503 | capacity_502 | honest_refusal | data_2xx` (`src/autom8_asana/observability/prometheus_metrics.py:154-162`, mapper `:177`); `record_rate_limit_429` folds unknown namespaces to `other` (`:306`). The honest-rate accessor `success_rate_with_stale_context` (`:650`) returns the success rate only together with `serving_stale_total`.

**CloudWatch via `emit_metric` (`src/autom8_asana/lambda_handlers/cloudwatch.py:31`): 88 distinct metric names** across 14 emitting modules (AST walk of `emit_metric`, `_emit` and `_emit_status_push_skipped` call sites with module constants resolved: 86 names, plus the two names `SchedulingStratumSnapshotPushed` and `...DryRun` that come from one conditional expression at `src/autom8_asana/lambda_handlers/scheduling_stratum_snapshot.py:617`). The helper always stamps an `environment` dimension from `ASANA_CW_ENVIRONMENT` (`src/autom8_asana/lambda_handlers/cloudwatch.py:52-54`) and adds caller dimensions. Unit is `Count` unless noted.

| Emitter module (under `src/autom8_asana/`) | Namespace | Metric names (dimensions beyond `environment`) | First call lines |
|---|---|---|---|
| `src/autom8_asana/lambda_handlers/cache_warmer.py` | settings default (see namespaces) | `WarmSuccess`, `WarmFailure`, `RowsWarmed`, `WarmDuration` (ms) all with `entity_type`; `CheckpointSaved`, `CheckpointResumed`, `WarmerCheckpointCleared`, `WarmerKeysCovered`, `WarmerKeysEnumerated`, `WarmerAimdEngaged`, `WarmerKeyBudgetExhausted`, `WarmerDeadlineYield`, `TotalDuration` (ms): 13 | `:439-1220` |
| `src/autom8_asana/lambda_handlers/cloudwatch.py` | settings default | `WarmerCoverageRate` (Percent), emitted from `src/autom8_asana/lambda_handlers/cache_warmer.py:485` | `:109` |
| `src/autom8_asana/lambda_handlers/story_warmer.py` | settings default | `StoryWarmEntityTaskCount`, `StoryWarmEntitySuccess`, `StoryWarmEntityFailure`, `StoryWarmEntityReached` (per-entity dimensions), `StoryWarmSuccess`, `StoryWarmFailure`, `StoriesWarmed`, `StoryWarmDuration` (ms): 8 | `:210-213,459-495` |
| `src/autom8_asana/lambda_handlers/cache_invalidate.py` | settings default | `InvalidateSuccess` (`type`), `KeysCleared` (`tier`), `ProjectManifestInvalidated` (`project_gid`), `InvalidateFailure`, `InvalidateDuration` (ms): 5 | `:156-276` |
| `src/autom8_asana/lambda_handlers/timeout.py` | settings default | `SelfContinuationInvoked` | `:133` |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | settings default; `Autom8y/AsanaBridgeFleet` for `BridgeFleetHealth` | `WorkflowExecutionError`, `WorkflowExecutionCount`, `WorkflowValidationSkipped`, `WorkflowDuration` (Seconds), `WorkflowSuccessRate` (Percent), all with `workflow_id`; `BridgeFleetHealth` (`workflow_id`) | `:115-378` |
| `src/autom8_asana/lambda_handlers/push_orchestrator.py` | settings default; fleet namespace for two | `GidPushSuccess`, `GidPushFailure` (`entity_type`), `StatusPushSuccess` (`entry_count`), `StatusPushFailure`; fleet: `StatusPushUnmappedEntities`, `StatusPushSkipped` (`skip_reason`) | `:92-252` |
| `src/autom8_asana/services/gid_push.py` | `Autom8y/AsanaBridgeFleet` (`:44`) | `StatusPushSkipped` (`skip_reason`), `StatusPushRowsSkipped` (`skip_class`), `VocabSyncRefused`, `VocabSyncSkipped`, `VocabSyncContractParseFailed` (`field_key`), `VocabSyncDriftDetected` | `:75,1058-1311` |
| `src/autom8_asana/lambda_handlers/offer_warm_amp.py` | settings default | `OfferWarmAmpFailed` (`entity_type`, `reason`) | `:173` |
| `src/autom8_asana/lambda_handlers/scheduling_stratum_snapshot.py` | settings default, deliberately dimension-free apart from `environment` (`:244-251`) | 16 names: `...SnapshotRunEpoch`, `PushEpoch`, `PushFailed`, `Refused`, `Skipped`, `SchemaLag`, `ShadowRun`, `DegenerateSource`, `Error`, `...Pushed`/`DryRun` (carries `office_count`, unalarmable by construction per `:252-262`), `SchedulingStratumUniverseCensus`, `...UniverseDropped`, `...PostureSignalRows`, `...PostureUniverseRows`, `...StatusDrift` | `:290-371,459,617,1030-1270` |
| `src/autom8_asana/lambda_handlers/enrollment_intent_bridge.py` | `Autom8y/AsanaEnrollmentBridge` (`:168`) | 16 names, constants at `:171-201` (`LastRunEpoch`, `EvaluationRefused`, `DeltaCeilingTripped`, `InScopeOffices`, `IntentDeltaCount`, `ConfigWritesApplied`, `NoopOffices`, `UnresolvedOfficeCount`, `NotConfiguredOfficeCount`, `EnrollmentPrereqRefusedCount` with `reason`, `WriteDeniedCount`, `InvalidPhoneFormatCount`, `BridgeErrorCount`, `GuidNullInScopeCount`, `RosterOnlyPhoneCount`, `StatusDriftPhoneCount`) | `:288-346,739` |
| `src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py` | `Autom8y/AsanaOfferDivergence` (`:166`) | 10 names: `LastRunEpoch`, `EvaluationRefused`, `TradingWithoutActiveOfferCount`, `NewlyTradingWithoutActiveOfferCount`, `ActiveOfferRosterSize`, `TradingWithoutActiveOfferBookings`, `TradingWithoutActiveOfferByClass` (`class`), `TrafficOfficesEvaluated`, `TrafficLegUnavailable` (`leg`), `TrafficOfferDivergenceError` | `:680-770,1107` |
| `src/autom8_asana/api/routes/workflows.py` | settings default | `WorkflowInvokeCount` (`workflow_id`, `source`, `dry_run`) | `:399` |
| `src/autom8_asana/api/middleware/idempotency.py` | settings default | `IdempotencyFinalizeFailure` (`endpoint`, `service_name`) | `:787` |

Module-name pairs sum to 89; `StatusPushSkipped` is emitted from two modules into the same namespace, which gives the 88 distinct names. `WorkflowDuration` is also emitted a second time through the SDK helper `emit_business_metric` into the per-workflow namespace (`src/autom8_asana/lambda_handlers/workflow_handler.py:344-358`), with `EntitiesProcessed`.

**Direct `put_metric_data` emitters: 20 series.**

| Emitter | Namespace | Series (dimensions) | Anchor |
|---|---|---|---|
| Freshness probe CLI batch (single call per ADR-006) | `Autom8y/FreshnessProbe` (`src/autom8_asana/metrics/cloudwatch_emit.py:40`) | `MaxParquetAgeSeconds`, `SectionCount`, `SectionAgeP95Seconds`, `SectionCoverageDelta`, `ForceWarmLatencySeconds` (`metric_name`, `project_gid`) | `:217`; invoked from `src/autom8_asana/metrics/__main__.py:280,494,1026` |
| Cache coalescer | `autom8y/cache-warmer` (`src/autom8_asana/cache/dataframe/coalescer.py:30`) | `CoalescerDedupCount` (`coalescer_key`, unbounded cardinality, no `environment`) | `:50` |
| Provability sweep and data-quality emitter | `Autom8y/SubstrateProvability` (`src/autom8_asana/substrate/observe.py:404`) | 12 names (`UnprovableCount`, `ProvableCount`, `MaxStalenessAgeSeconds`, `Completeness`, `EvaluatorHeartbeat`, `ExpectedSetMismatchCount`, `ExpectedCount`, `EvaluatedCount`, `EvaluationFailed`, `FutureDatedProofCount`, `ArtifactProvable`, `ActiveRowEconomicNullCount`); run-level dimension `{environment}`, `ArtifactProvable` adds `project_gid`, `entity_type` | `:419-444,519,673` |
| Serve-side refusal emitter | `Autom8y/SubstrateServe` (`src/autom8_asana/substrate/serve.py:226`) | `SubstrateRefusalCount` (`environment`, plus a second series with `reason`), `FutureDatedProofCount` | `:239-244,341` |

`CloudWatchProvabilityEmitter` is constructed only by `src/autom8_asana/substrate/prov_sweep.py:116` (reached from the `prov_sweep` Lambda). `CloudWatchDataQualityEmitter` is constructed only at `src/autom8_asana/substrate/parity_run.py:363`; that module's docstring says it is an operator tool, "Not imported by any deployed path" (`:38-39`), so `ActiveRowEconomicNullCount` has no scheduled emitter. `CloudWatchRefusalEmitter` has no construction outside its own module; `src/autom8_asana/substrate/serve.py:405` defaults to `NullRefusalEmitter`, so both `Autom8y/SubstrateServe` series are defined but not emitted by any deployed path.

**Other emitters.**
- EMF (flag-gated, default off): `ReceiverQueryOutcomeSuccess`, `ReceiverQueryOutcomeServerError`, `ServingStaleTotal` in `Autom8y/AsanaReceiverSLI`, dimension `arm` (`src/autom8_asana/observability/prometheus_metrics.py:354,408-437`), called from `src/autom8_asana/api/routes/query.py:539`. The co-read rule puts `ServingStaleTotal` in the same document as the outcome counts.
- AMP (flag-gated, default off): gauge `autom8y_offer_warm_complete_timestamp{entity_type}` (`src/autom8_asana/lambda_handlers/offer_warm_amp.py:56`), called from `src/autom8_asana/lambda_handlers/cache_warmer.py:594,980`.
- SDK helpers: `emit_success_timestamp` into per-workflow dead-man namespaces and the fleet namespace (`src/autom8_asana/lambda_handlers/workflow_handler.py:367,386`), the warmer's settings-resolved namespace (`src/autom8_asana/lambda_handlers/cache_warmer.py:1420`) and `Autom8y/AsanaLeadsBridge` (`src/autom8_asana/lambda_handlers/leads_consumer.py:40,140`); metric name and dimensions are SDK-internal [INFERRED `LastSuccessTimestamp` from the alarm that reads it, `terraform/services/asana/observability_alarms.tf:291`].
- Log-derived (Terraform metric filters): `OfferFrameAgeSeconds{project_gid}`, `OfficePhoneStampUnresolved`, `CacheDegradedMode` (see Alerting).
- Hook-only metrics that production never wires: `DataServiceClient` emits 7 names (`insights_request_total`, `insights_request_latency_ms`, `insights_request_error_total`, `insights_batch_total`, `insights_batch_size`, `insights_batch_success_count`, `insights_batch_failure_count`) only through `metrics_hook` (`src/autom8_asana/clients/data/client.py:127,153,685-695`; `src/autom8_asana/clients/data/_metrics.py:19-54`); every production construction omits it (`src/autom8_asana/api/dependencies.py:577`, `src/autom8_asana/api/routes/workflows.py:372`, `src/autom8_asana/lambda_handlers/leads_consumer.py:105`). The leads consumer's `grain_bridge_leads_skipped_total` (`src/autom8_asana/automation/workflows/leads_skip.py:31,75`) has the same shape: `GrainBridgeLeadsConsumer` is built without a hook (`src/autom8_asana/lambda_handlers/leads_consumer.py:107-111`). The `ObservabilityHook` protocol's methods are implemented only by `NullObservabilityHook` (`src/autom8_asana/_defaults/observability.py:9-47`) and no `src/` code calls `on_request_start`, `on_rate_limit` or the other hook methods.

**Totals.** Code-defined series with a distinct name: 22 Prometheus + 88 `emit_metric` + 20 direct `put_metric_data` + 3 EMF + 1 AMP = 134, plus 4 SDK platform families, 8 hook-only, 3 log-derived and the SDK dead-man timestamp. At default flags 11 of the 134 have no deployed emitting path: 4 Prometheus series with no call site, 2 `SubstrateServe` series, 3 EMF series (flag off), 1 AMP series (flag off), and `ActiveRowEconomicNullCount` (operator tool only).

### Namespaces

16 literal namespaces in `src/`: the settings default `autom8/lambda` (`src/autom8_asana/settings.py:788-792`); `autom8y/cache-warmer` (`src/autom8_asana/cache/dataframe/coalescer.py:30`); `autom8y/cache-warmer-bulk` (fallback, `src/autom8_asana/lambda_handlers/cache_warmer.py:96`); `Autom8y/AsanaBridgeFleet`; `Autom8y/AsanaEnrollmentBridge`; `Autom8y/AsanaOfferDivergence`; `Autom8y/AsanaLeadsBridge`; `Autom8y/FreshnessProbe`; `Autom8y/AsanaReceiverSLI`; `Autom8y/SubstrateProvability`; `Autom8y/SubstrateServe`; four per-workflow dead-man namespaces `Autom8y/AsanaInsights`, `Autom8y/AsanaAudit`, `Autom8y/AsanaWalkthrough`, `Autom8y/AsanaReconciliation` (`src/autom8_asana/lambda_handlers/insights_export.py:56`, `src/autom8_asana/lambda_handlers/conversation_audit.py:49`, `src/autom8_asana/lambda_handlers/onboarding_walkthrough.py:115`, `src/autom8_asana/lambda_handlers/payment_reconciliation.py:57`); and `BridgeWorkflows` (fallback, `src/autom8_asana/lambda_handlers/workflow_handler.py:345,352`). Terraform adds `Autom8y/AsanaSubstrateFreshness`, `Autom8y/AsanaIntakeCF`, `Autom8y/AsanaWarmerCache`. The deployed value of `ASANA_CW_NAMESPACE` is not in the repo; comments cite a lowercase `autom8y/cache-warmer` value for the warmer family (`src/autom8_asana/cache/dataframe/coalescer.py:27`, `terraform/services/asana/story_warm_dead_alarm.tf:36-37`) [INFERRED].

### Load-bearing log events

Events that a Terraform metric filter (or a documented monorepo filter) keys on; renaming any of them silently un-wires a monitor.

| Event | Emitted at | Consumed by |
|---|---|---|
| `dataframe_cache_{tier}_lkg_serve` with `tier` in `memory`, `s3` | `src/autom8_asana/cache/integration/dataframe_cache.py:768` (tier values at `:300,319`) | AL-5 filter, which pins the `memory` spelling (`terraform/services/asana/observability_alarms.tf:451`) |
| `cache_degraded_mode` | `src/autom8_asana/cache/backends/redis.py:173,258` | F-1 filter (`terraform/services/asana/warmer_cache_degraded_alarm.tf:71`) |
| `office_phone_cf_not_found`, `office_phone_cf_stamp_failed` | `src/autom8_asana/services/intake_create_service.py:373,388` | AL-6 filter (`terraform/services/asana/observability_alarms.tf:690`) |
| `section_name_contract_violation`, `section_last_verified_stamp_failed` | `src/autom8_asana/dataframes/builders/progressive.py:625,637,651` | documented live filter in `docs/runbooks/RUNBOOK-freshness-verification-recency.md:100-112` (filter not in this repo) |
| `population_receipt_below_floor`, `population_receipt_ok` | `src/autom8_asana/dataframes/builders/post_build_population_receipt.py:240,242` | no in-repo consumer |
| `cascade_loop_detected` | `src/autom8_asana/dataframes/resolver/cascading.py:313` | no in-repo consumer |
| `exports_handler_complete` | `src/autom8_asana/api/routes/exports.py:566` | no in-repo consumer |
| `rate_limit_exceeded` (new) | `src/autom8_asana/api/errors.py:766` | no in-repo consumer; carries `namespace`, `method` |
| `write_authz_allowed`, `write_authz_would_deny`, `write_authz_denied` | `src/autom8_asana/api/write_authz.py:339,353` (the call at `:353` picks `denied` or `would_deny` by mode) | none: log-only |
| `metric_emit_error` | `src/autom8_asana/lambda_handlers/cloudwatch.py:83` | none: the only record of a dropped CloudWatch emission |

### Contract-drift log (code-visible)

| ID | Drift | Evidence | State |
|----|-------|----------|-------|
| DRIFT-AL5-TIER | AL-5's filter pins `dataframe_cache_memory_lkg_serve`; the code builds the event name from the tier and serves LKG from both tiers, so an `s3`-tier LKG serve produces `dataframe_cache_s3_lkg_serve`, which the filter does not match | `src/autom8_asana/cache/integration/dataframe_cache.py:299-301,317-319,768` vs `terraform/services/asana/observability_alarms.tf:451` | open |
| DRIFT-AL1-INVALID-KEY | AL-1 authors an alarm instance for `skip_reason=invalid_key`; the value is retired for the status push ("nothing emits it today") and is emitted only on the separate `VocabSyncSkipped` series | `terraform/services/asana/observability_alarms.tf:218-223`, `src/autom8_asana/services/gid_push.py:50-53,1560` | open: 1 of 4 AL-1 instances binds a value no `StatusPushSkipped` emitter produces |
| DRIFT-ENV-DIM | two `environment` conventions (see Credential Topology, bifurcation check) | `src/autom8_asana/settings.py:794`, `src/autom8_asana/substrate/observe.py:415`, `terraform/services/asana/story_warm_dead_alarm.tf:86-88` | open, documented in comments |
| DRIFT-DMS-NS | the warmer dead-man timestamp once targeted a namespace outside the role's grant | `src/autom8_asana/lambda_handlers/cache_warmer.py:81-107` | resolved in code (namespace from settings); the retired namespace string survives in a CLI wait message (`src/autom8_asana/metrics/__main__.py:445`) |
| DRIFT-SLO3 | SLO-3 in the spec names a `DMS_NAMESPACE` constant in `src/autom8_asana/lambda_handlers/cache_warmer.py`; no such constant exists now | `.ledge/specs/cache-freshness-observability.md:143` vs `src/autom8_asana/lambda_handlers/cache_warmer.py:96-107` | open |
| DRIFT-EMITTER-DARK | emitters that exist but have no deployed path: 4 Prometheus series, `SubstrateServe`, `ActiveRowEconomicNullCount`, hook-only metrics, flagged EMF and AMP | see Totals | open |

**Completeness self-assessment**: every signal class this repo produces has a producer, wire protocol, sink and auth surface documented; the metric inventory is complete by AST walk with explicit totals; the consumer side for traces and scrapes, and the live state of every sink, are outside the repo.

## SLO/SLI Maturity

### Status of the SLO source

The only SLO catalog in this repo is `.ledge/specs/cache-freshness-observability.md` (frontmatter `status: draft`, authored 2026-04-27 by the thermal-monitor role, `:1-14`). Its last change was commit `46c322ba` ("close cache-freshness-procession", #30). It was never ratified in the file. All three SLOs cover the Lambda warmer and the freshness CLI, not the ECS API surface. No API availability, latency or error-rate SLO target is defined anywhere in `src/`, `terraform/`, `config/`, `docs/runbooks/` or `.github/` (search for `SLO`, `SLI`, burn-rate and error-budget terms returned only the spec-derived references below, receiver-SLI comments in code, and `docs/runbooks/RUNBOOK-freshness-verification-recency.md`).

### SLO inventory (from the spec; measurement code re-checked at this ref)

| SLO | Target, window, denominator | SLI and signal source | Spec anchor | Code state at this ref |
|---|---|---|---|---|
| SLO-1 ParquetMaxAgeSLO | 95% of CLI invocations over a rolling 7 days report `MaxParquetAgeSeconds < 21600` for the ACTIVE-classifier fleet; denominator is CLI invocations (spec assumes O(5)/day); error budget 5% | `MaxParquetAgeSeconds` in `Autom8y/FreshnessProbe`, one batch per CLI run (`src/autom8_asana/metrics/cloudwatch_emit.py:217`) | `:105-119` | emitter present; the CLI emits no invocation counter, so the denominator is not measurable from metrics |
| SLO-2 WarmSuccessRateSLO | `WarmSuccess/(WarmSuccess+WarmFailure)` for `entity_type=offer` at or above 95% over a rolling 7 days | `WarmSuccess`, `WarmFailure` with dimension `entity_type` (`src/autom8_asana/lambda_handlers/cache_warmer.py:590,601,972,1004,1097`) | `:123-135` | emitters present; spec's line anchors (`:473,501`) have rotted; `emit_metric` always adds `environment`, which the spec's dimension set omits |
| SLO-3 WarmHeartbeatSLO | at least 1 dead-man timestamp per rolling 24 hours | `emit_success_timestamp` (`src/autom8_asana/lambda_handlers/cache_warmer.py:1420`) | `:139-149` | the spec names a `DMS_NAMESPACE` constant that no longer exists; the namespace now comes from settings (`src/autom8_asana/lambda_handlers/cache_warmer.py:99-107`) |

SLI rationale as written in the spec: SLO-1 chooses freshness because `active_mrr` is internal and operational (eventual consistency tolerable, DEF-3 anchor, `:113`); SLO-2 is availability of the warm action; SLO-3 is liveness of the warmer (`:147`). The runbook `docs/runbooks/RUNBOOK-freshness-verification-recency.md:41-61` defines the successor freshness SLI, `verification_age = now - min(last_verified_at)` over active-classified sections, replaces mutation-age as the alarmable gauge, and keeps `mutation_age` as context only (do not alarm). Its threshold guidance (`:63-85`) says the ceiling should be a small multiple of the warm cadence and records that the `verification_age` ceiling alarm "is a separate (future) alarm" not yet wired.

Per-class freshness thresholds that act as in-code SLO constants: `active` 21600 s, `warm` 43200 s, `cold` 86400 s, `near-empty` 604800 s (`src/autom8_asana/metrics/sla_profile.py:66-74`), mirrored in `.know/cache-freshness-ttl-manifest.yaml:9-12`; override order sidecar over manifest over built-ins (`src/autom8_asana/metrics/sla_profile.py:7-9`).

### SLI substrate defined in code (targets sit outside this repo)

| SLI | Definition in code | Target stated in a code comment | Anchor |
|---|---|---|---|
| Receiver mirror success rate | `2xx / (2xx + 5xx)` per arm from `autom8y_asana_receiver_query_outcome_total`, 4xx excluded, zero denominator returns `None` rather than a fabricated 100% | deploy gate at or above 99% on both arms for 10 minutes (`src/autom8_asana/observability/prometheus_metrics.py:314,330`) | `:108-112,605-637` |
| Honesty co-read | success rate is returned only together with `serving_stale_total` | structural, `success_rate_with_stale_context` | `:550-556,650-665` |
| S7 fallback cause | `receiver_query_fallback_cause_total` split into `cadence_503`, `capacity_502`, `honest_refusal`, plus `data_2xx` | verdict reads cause, not a collapsed total | `:140-186,473-506` |
| Emitting-floor denominator | probe-class samples on the platform HTTP duration histogram keep `autom8y_http_request_duration_seconds_count{service="asana"}` non-zero while idle; `route_class="probe"` keeps the business denominator clean (G-DENOM) | the alarm that consumes it is in the monorepo | `src/autom8_asana/api/sli_heartbeat.py:1-48,85,112-148` |
| Event-loop starvation precondition | event-loop lag above 0.5 s and a non-empty offload-gate wait queue | threshold constant `EVENT_LOOP_LAG_STARVATION_THRESHOLD_SECONDS = 0.5` | `src/autom8_asana/observability/prometheus_metrics.py:675,678-705` |
| Substrate provability | `UnprovableCount`, `Completeness`, `EvaluatorHeartbeat`, `ExpectedSetMismatchCount`, `ExpectedCount`, `FutureDatedProofCount`, `MaxStalenessAgeSeconds` | alarm thresholds in `terraform/services/asana/substrate_v2_provability_alarms.tf` | `src/autom8_asana/substrate/observe.py:404-444` |
| Serve-side refusal | `SubstrateRefusalCount` counted at the serve choke point so refusals do not burn the availability SLO (`src/autom8_asana/substrate/serve.py:225-236`) | emitter not wired (see Signal Pipe Contracts) | `src/autom8_asana/substrate/serve.py:239,413` |
| Offer freshness | AMP gauge `autom8y_offer_warm_complete_timestamp{entity_type}` feeding monorepo recording rules named in comments | rules not in this tree | `src/autom8_asana/lambda_handlers/offer_warm_amp.py:15-21,56` |
| Per-GID served-frame age | log-derived `OfferFrameAgeSeconds{project_gid}` with a stale threshold variable defaulting to 7200 s | the alarm text itself says the 7200 value has no current justification and is pending re-baseline (`terraform/services/asana/observability_alarms.tf:391-424,465-525`) | AL-5 |
| Warmer coverage | `WarmerCoverageRate = keys_completed / total_enumerated * 100`, zero denominator returns 0.0, not 100 (`src/autom8_asana/lambda_handlers/cloudwatch.py:88-109`) | none | emitted at `src/autom8_asana/lambda_handlers/cache_warmer.py:485` |

### Burn-rate alerting

None. There is no multi-window multi-burn-rate construct in the repo. The spec's ALERT-2 is labeled an SLO budget burn alert but is a single-threshold persistence rule (`MaxParquetAgeSeconds` above 21600 for 6 evaluation periods of 300 s, `:184-205`). AL-5 was retuned three times against flapping; its final 3-of-4 over 3600 s with `treat_missing_data = "missing"` and no `ok_actions` damps but does not remove the flap, per the file's own "HONEST LIMIT" (`terraform/services/asana/observability_alarms.tf:600-611`).

### Error-budget policy

The spec states budget arithmetic (SLO-1: 5% of invocations, about 1.75 stale reads per week at its assumed volume, `:119`) and per-SLO breach actions, but no deployment-freeze or rollback policy, no named governance owner, and no policy file exists in the repo (search for freeze, owner, policy and governance terms in the spec returned nothing).

### Current burn-rate state

Not obtainable from the repo, and not read from any live source in this pass. The SLO-1 spec's own realism lens states it "will breach immediately in the current production state" because the warmer cadence was unknown when it was written (`:400-403`); that statement is spec-time, not a current reading. Live readings from the prior pass (2026-10-05) are recorded as unverified history under Knowledge Gaps.

**Completeness self-assessment**: SLO inventory, windows, denominators, rationale, absence of burn-rate rules and of an error-budget policy are documented with anchors, and each SLO was cross-checked against the code that would measure it (two of three have drifted anchors or constants). The SLOs are an unratified draft, the ECS service has no in-repo SLO, and no current readings exist.

## Alerting & Runbook Coverage

### What exists in the repo

`terraform/services/asana/` holds 4 `.tf` files (plus a surfaced-levers note and an example variables file): 19 resource blocks, of which 15 are `aws_cloudwatch_metric_alarm` (18 alarm instances at default variables, because AL-1 expands to 4), 3 are `aws_cloudwatch_log_metric_filter`, and 1 is an optional `aws_sns_topic` (count of resource blocks per file by line search: `terraform/services/asana/observability_alarms.tf` 9, `terraform/services/asana/substrate_v2_provability_alarms.tf` 7, `terraform/services/asana/story_warm_dead_alarm.tf` 1, `terraform/services/asana/warmer_cache_degraded_alarm.tf` 2). There is no Terraform backend, no state and no apply pipeline in this repo (`terraform/services/asana/warmer_cache_degraded_alarm.tf:18-24`, `terraform/services/asana/story_warm_dead_alarm.tf:53-58`); `terraform/services/asana/observability_alarms.tf:8-22` labels the suite "AUTHORED / UN-DEPLOYED / UN-ARMED", and the `.gitignore` in that directory excludes state, plan and local tfvars. Every alarm below is therefore code-of-record. No Prometheus alerting-rule file, no Grafana rule, and no CloudWatch dashboard resource exists in the tree (search for `aws_cloudwatch_dashboard` and dashboard definitions in `terraform/`, `src/`, `.github/`, `config/`, `docker/` found only unrelated `dashboard_uuid` schema fields; the same search shape found alarm resources, positive control).

### Alarm inventory with emitter cross-check

Columns: metric read (namespace, name, dimension keys), statistic and threshold, period x evaluations, missing-data treatment, default action wiring, runbook tag in the alarm text, and whether code at this ref emits that exact metric.

| Alarm (instances) | Reads | Condition | Missing data | Default actions | Runbook tag | Emitter in this repo |
|---|---|---|---|---|---|---|
| AL-1 `asana-AL1-StatusPushSkipped-{reason}` (4: `feature_disabled`, `url_absent`, `invalid_key`, `three_way_denominator_null`) `terraform/services/asana/observability_alarms.tf:226-247` | `Autom8y/AsanaBridgeFleet`, `StatusPushSkipped`, `{environment, skip_reason}` | Sum > 0, 3600 s x 1 | `notBreaching` | ticket tier (empty unless `ticket_sns_topic_arn` set) | `RB-STATUSPUSH-SKIP` | yes for 3 reasons (`src/autom8_asana/services/gid_push.py:1104,1113`, `src/autom8_asana/lambda_handlers/push_orchestrator.py:255`); NO for `invalid_key` (retired for the status push, `src/autom8_asana/services/gid_push.py:50-53`) |
| AL-2 `asana-AL2-recon-invocation-gap` `:256-274` | `AWS/Lambda`, `Invocations`, `{FunctionName}` | Sum < 1, 28800 s x 1 | `breaching` | ticket tier; page needs `recon_rule_enabled` (default false) | `RB-RECON-GAP` | AWS-native metric, no code emitter needed |
| AL-3 `asana-AL3-insights-LastSuccessTimestamp-stale` `:287-306` | `Autom8y/AsanaInsights`, `LastSuccessTimestamp`, no dimensions | Max < 1, 93600 s x 1 | `breaching` | ticket tier | `RB-INSIGHTS-STALE` | the call site exists (`src/autom8_asana/lambda_handlers/workflow_handler.py:367`, namespace `src/autom8_asana/lambda_handlers/insights_export.py:56`, gated on `succeeded > 0`); the metric's name and dimensions are set inside the SDK helper |
| AL-4 `asana-AL4-prod-BridgeFleetHealth-{workflow}` (1: `insights-export`) `:323-344` | `Autom8y/AsanaBridgeFleet`, `BridgeFleetHealth`, `{environment, workflow_id}` | Min < 1, 3600 s x 1 | `missing` | ticket tier | `RB-BRIDGEFLEET` | yes (`src/autom8_asana/lambda_handlers/workflow_handler.py:304,378`); matches only if the function's `ASANA_CW_ENVIRONMENT` equals the alarm's `environment` variable (default `production`) |
| AL-5 `asana-AL5-offer-frame-stale-{gid}` (1) `:527-675` | `Autom8y/AsanaSubstrateFreshness`, `OfferFrameAgeSeconds`, `{project_gid}`, produced by log-metric-filter `:446-462` | Max > 7200, 3-of-4 x 3600 s | `missing` | ticket tier; `ok_actions = []` | `RB-SUBSTRATE-FRESHNESS` | yes, but the filter matches only `dataframe_cache_memory_lkg_serve`; the `s3`-tier serve has a different event name (DRIFT-AL5-TIER) |
| AL-6 `asana-AL6-office-phone-stamp-unresolved` `:700-717` | `Autom8y/AsanaIntakeCF`, `OfficePhoneStampUnresolved`, no dimensions, filter `:687-698` | Sum > 0, 3600 s x 1 | `notBreaching` | ticket tier | `RB-INTAKE-CF-1` | yes (`src/autom8_asana/services/intake_create_service.py:373,388`) |
| PROV-1 `asana-PROV-1-unprovable` `terraform/services/asana/substrate_v2_provability_alarms.tf:114-130` | `Autom8y/SubstrateProvability`, `UnprovableCount`, `{environment}` | Max > 0, 900 s x 1 | `notBreaching` | ticket tier | `RB-SUBSTRATE-PROVABILITY` | yes (`prov_sweep` Lambda via `src/autom8_asana/substrate/prov_sweep.py:116`) |
| PROV-2 `...-heartbeat-absence` `:143-159` | `EvaluatorHeartbeat`, `{environment}` | Sum < 1, 3600 s x 1 | `breaching` | ticket tier | `RB-SUBSTRATE-EVALUATOR-DOWN` | yes (same sweep; the operator tool `src/autom8_asana/substrate/parity_run.py` also runs an in-process sweep) |
| PROV-3 `...-incomplete` `:171-187` | `Completeness`, `{environment}` | Min < 100, 900 s x 1 | `notBreaching` | ticket tier | `RB-SUBSTRATE-INCOMPLETE` | yes |
| PROV-4 `...-expected-set-mismatch` `:200-216` | `ExpectedSetMismatchCount` | Max > 0, 900 s x 1 | `notBreaching` | ticket tier | `RB-SUBSTRATE-SET-DRIFT` | yes |
| PROV-5 `...-expected-floor` `:231-247` | `ExpectedCount` | Min < 1, 900 s x 1 | `notBreaching` | ticket tier | `RB-SUBSTRATE-EMPTY-EXPECTED` | yes |
| PROV-6 `...-future-dated-proof` `:261-277` | `FutureDatedProofCount` (the `SubstrateProvability` series, not the unwired `SubstrateServe` one) | Max > 0, 900 s x 1 | `notBreaching` | ticket tier | `RB-SUBSTRATE-FUTURE-STAMP` | yes |
| PROV-7 `...-data-quality-nulls` `:302-318` | `ActiveRowEconomicNullCount`, `{environment}` | Max > 0, 900 s x 1 | `notBreaching` | ticket tier | `RB-SUBSTRATE-DATA-QUALITY` | only from the operator parity tool (`src/autom8_asana/substrate/parity_run.py:363`), which is "not imported by any deployed path"; no scheduled emitter |
| F-1 `asana-F1-warmer-cache-degraded-mode` `terraform/services/asana/warmer_cache_degraded_alarm.tf:82-102` (+ 3 filters, one per warmer log group) | `Autom8y/AsanaWarmerCache`, `CacheDegradedMode`, no dimensions | Sum > 0, 300 s x 1 | `notBreaching` | one notify-tier topic by variable; no `ok_actions` | inline "RB:" text, no tag | yes (`src/autom8_asana/cache/backends/redis.py:173,258`); silent when healthy by design |
| `autom8y-asana-story-warm-dead` `terraform/services/asana/story_warm_dead_alarm.tf:80-106` | `autom8y/cache-warmer`, `StoryWarmSuccess`, `{environment="staging"}` hard-coded | Sum <= 0, 2-of-2 x 7200 s | `breaching` | notify topic plus the SEV-1 paging topic, both on alarm and ok | runbook named in a monorepo path, no in-repo tag | yes (`src/autom8_asana/lambda_handlers/story_warmer.py:459`, emitted unconditionally per run); the namespace and the `staging` label depend on function env set outside the repo |

State, binding and arming levers: the master kill-switch is `arm_paging` (default false) plus per-alarm membership in `paging_armed_alarms` (default empty); `ticket_sns_topic_arn` defaults to an empty string, which resolves every non-armed alarm's action list to empty (the "binding-blind" class documented at `terraform/services/asana/observability_alarms.tf:100-119`). `require_alarm_binding` defaults false and is enforced only for AL-5 (`:144-153,669-674`). The always-on `alarm_binding_report` output lists AL-1..6 and PROV-1..6 but omits PROV-7 even though `prov7_actions` exists (`terraform/services/asana/observability_alarms.tf:761-778` vs `terraform/services/asana/substrate_v2_provability_alarms.tf:101,316-317`). The example variables file states AL-5 defaults of 7200 / 1800 / 8, while `terraform/services/asana/observability_alarms.tf:652-655` sets 7200 / 3600 / 4 / 3 (threshold, period, evaluation periods, datapoints) (`terraform/services/asana/terraform.tfvars.example:74-85`).

**Alarms whose metric has no emitter at this ref (from the repo alone)**: 1 instance, AL-1 `invalid_key`. **Alarms whose emitter exists only on a non-deployed or operator path**: PROV-7. **Alarms whose emitter is a log event the filter only partly matches**: AL-5. **Alarms whose metric is produced by an SDK helper the repo does not contain, so name and dimensions are unverifiable here**: AL-3. **Alarms that depend on an environment label set outside the repo**: AL-4 (`production`), story-warm-dead (`staging`). Of 18 alarm instances: 11 have an in-repo emitter whose metric identity matches with no external assumption (AL-1 x3, AL-6, PROV-1..6, F-1; PROV-1..6 are additionally pinned by `tests/unit/substrate/test_observe.py:784`); 1 reads an AWS-native metric (AL-2); 6 are the exceptions listed above (AL-1 `invalid_key`, AL-3, AL-4, AL-5, PROV-7, story-warm-dead).

**What cannot be checked from the repo**: whether any alarm exists live, its state, its actions or whether its series has datapoints. Live-state alarm facts from the prior pass (2026-10-05) are not carried forward; see Knowledge Gaps.

### Alarms named outside this repo's Terraform

- Stratum producer: `src/autom8_asana/lambda_handlers/scheduling_stratum_snapshot.py:233-246` names the counterpart alarm file in the monorepo and pins `ALARM_BOUND_METRICS` (7 names, `:383-392`); the `tests/unit/lambda_handlers/test_scheduling_stratum_snapshot_durability.py:338` test freezes that set. The R7 tripwire does the same (`src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py:160-192`).
- Enrollment bridge: `src/autom8_asana/lambda_handlers/enrollment_intent_bridge.py:150-166` states that no alarm half exists and that its 16 metrics, including the dead-man `LastRunEpoch` and `EvaluationRefused`, "page nobody".
- Freshness: the runbook documents one live alarm, `autom8-asana-section-name-contract-violation-error`, fed by a log filter (`docs/runbooks/RUNBOOK-freshness-verification-recency.md:100-115`); neither the alarm nor the filter is in this repo's Terraform. The spec's ALERT-1..6 (`.ledge/specs/cache-freshness-observability.md:153-290`) are likewise design text, not Terraform here.
- Stage-1 receiver alerts named only in code comments: A1 miss-rate spike (`src/autom8_asana/observability/prometheus_metrics.py:77-80,261`), A3 SA-bucket 429 (`:95-97,296`), A5 semaphore saturation above 0.80 for 5 minutes (`:87-89`), A8 mirror-SLI degradation (`src/autom8_asana/api/routes/query.py:459`). No rule file in the repo reads the Prometheus series behind them.

### Runbook linkage

- 13 distinct `RB-*` identifiers appear in alarm descriptions: `RB-STATUSPUSH-SKIP`, `RB-RECON-GAP`, `RB-INSIGHTS-STALE`, `RB-BRIDGEFLEET`, `RB-SUBSTRATE-FRESHNESS`, `RB-INTAKE-CF-1`, and the seven `RB-SUBSTRATE-*` tags for PROV-1..7. 0 of 13 resolve to a runbook file or heading in `docs/runbooks/`, `runbooks/` or `.ledge/`; the only other file naming any of them is `.ledge/reviews/sre-observability-design.md` (4 mentions, design prose). The alarm descriptions carry prose IDs, not links.
- Runbooks that do exist: nine runbook files (named RUNBOOK-<topic>) under `docs/runbooks/` (batch-operations, business-model-navigation, cache-troubleshooting, detection-troubleshooting, freshness-verification-recency, onboard-deck, pipeline-automation, rate-limiting, savesession-debugging) plus its `README.md`, the draft `.ledge/specs/cache-freshness-runbook.md` (scenarios Stale-1, Warmer-1, DMS-1, ForceWarm-1, S3-1), and the Atuin Desktop API-ops notebooks under `runbooks/atuin/` (operations, not alert response). `docs/runbooks/RUNBOOK-rate-limiting.md` is the nearest match for the new 429 signals but predates them: it greps logs for `rate_limit_429_received` and does not mention `rate_limit_exceeded`, the `namespace` label or `autom8y_asana_rate_limit_429_total` (line search of that file).
- The story-warm alarm cites a runbook by file name in the monorepo (`terraform/services/asana/story_warm_dead_alarm.tf:50-51`); F-1 carries inline recovery text (`terraform/services/asana/warmer_cache_degraded_alarm.tf:84`).

### Synthetic monitoring

- Probes in the repo: container `HEALTHCHECK` on `/health` (`Dockerfile:174-175`); platform probe routes `/health`, `/ready`, `/health/deps` (`src/autom8_asana/api/routes/health.py:387,417,525`); the in-process `SliHeartbeat` (synthetic samples, not a probe of a critical path).
- Scheduled checks: `.github/workflows/nightly-live-smoke.yml` (cron `15 9 * * *`, `:79`) runs two read-only live smoke suites against durable storage, fails the job if any test skips (anti-theater assertion, `:223`), and on red publishes to the notify-tier SNS topic (`:257-277`); it cannot page on a failure before its credential-bridge step (header `:64-72`). `.github/workflows/aegis-synthetic-coverage.yml` is a CI coverage and memory gate on `src/**` changes, not a runtime monitor. `mcp/canary/test_broken_fixture_canary.py` is a CI fixture test.
- No scheduled synthetic probe of the ECS API's business paths exists in the repo.

### Alert-fatigue signals and on-call

- Recorded in comments, not re-measured: AL-5 produced about 10 to 12.6 state transitions per day before the 2026-08-12 flap cure (`terraform/services/asana/observability_alarms.tf:485-493,546-552`); the story-warm design rejected a failure-count alarm because `StoryWarmFailure` is routinely nonzero (`terraform/services/asana/story_warm_dead_alarm.tf:13-22`). No per-alarm fire counts exist in the repo.
- On-call: no rotation, escalation policy or owner is documented in-repo. The notify tier and paging tier are SNS topics named by variable; their subscriptions are described only in comments (`terraform/services/asana/terraform.tfvars.example`, `terraform/services/asana/story_warm_dead_alarm.tf:70-78`).

### Dashboard surface

None in the repo. The spec's "Cache Freshness - Overview" dashboard design (`.ledge/specs/cache-freshness-observability.md:325-350`) has no corresponding resource or JSON in the tree.

**Completeness self-assessment**: every alarm resource, log filter and alarm-bearing doc in the repo is inventoried with its metric identity, emitter status and runbook tag; the live alarm state, history, subscriptions and on-call ownership are not in the repo and were not read.

## Knowledge Gaps

1. **Live state of every sink and alarm (not checkable from the repo, by design of this pass).** Whether any alarm in `terraform/services/asana/` exists live, its state, its action wiring, whether its metric has datapoints, SNS subscriptions, CloudWatch dashboards, AMP series, and Prometheus scrape targets were not read. This pass made no AWS, Grafana or HTTP calls and did not describe any task definition (barred fleet-wide). Every alarm statement above is about code at `584c8f79`, not about live behavior.
2. **OTLP binding and sampler (BLOCKING per the rubric).** Exporter protocol, endpoint, auth-routing field and sampler are SDK-managed and are not declared in this tree (search shape and positive control under Sampling). They would be visible in the deployed task or function environment and in the `autom8y-telemetry` source.
3. **Credential-topology matrix.** The matrix schema file exists in the operator's pinakes skill directory; its name matches the credential name floor, so it was not opened (not read: floored name, operator's act). No matrix instance exists in this repo.
4. **Land inputs.** No land input was injected. Of the two land files mapped to this domain, the observability-posture file does not exist, and the other has a floored name (it matches the credential pattern), so it was not opened (not read: floored name, operator's act). No `[EXPERIENTIAL]` claim appears in this document.
5. **External SDK behavior not visible in this tree.** `instrument_app` inbound trace extraction and its `/metrics` auth exclusion (`autom8y_auth` `DEFAULT_EXCLUDE_PATHS`), `instrument_lambda` span and log behavior, the metric name and dimensions written by `emit_success_timestamp` and `emit_business_metric`, whether `create_fleet_app` mounts an access log, and whether Lambda logs carry `trace_id`. Items tagged `[INFERRED]` in the body depend on these.
6. **Deployed environment values.** `ASANA_CW_NAMESPACE`, `ASANA_CW_ENVIRONMENT`, `SUBSTRATE_PROV_ENVIRONMENT`, the AMP flag and endpoint, and `RECEIVER_SLI_EMF_ENABLED` are set outside the repo. Whether AL-4 and story-warm-dead bind to series that exist depends on them.
7. **Monorepo halves.** The stratum producer alarms, the R7 divergence alarm, the enrollment-bridge alarm half (stated absent), SLO recording rules (`slo_offer_freshness`, the emitting-floor dead-man), the documented freshness log filters, and the paging runbook are in the `autom8y` parent repo and were not read.
8. **Approximate measurements.** AST counts (22 Prometheus series, 88 `emit_metric` names, 15 span sites, 11 Lambda handlers) are exact for the patterns walked. The per-package coverage table and the `get_logger` file count are regex sweeps and the metric column is an upper bound. Dynamic metric names that no AST pass can resolve (other than the one conditional at `src/autom8_asana/lambda_handlers/scheduling_stratum_snapshot.py:617`) would be missed; none was found.
9. **Related knowledge files not relied on.** `.know/feat/observability.md` and `.know/feat/business-metrics.md` exist but were not read for this pass. The `src/autom8_asana/metrics/` package is business-metric computation and the freshness CLI, covered here only where it emits CloudWatch series.
10. **Prior-pass live observations, unverified history.** The 2026-10-05 pass recorded read-only AWS observations (about five weeks before this pass): the Lambda family silent since early September, 73 asana-named alarms of which 20 had actions disabled and 9 had no actions, 9 metric alarms with zero datapoints in 390 days (three ElastiCache alarms with a wrong dimension key, a warmer-failure alarm whose dimension set omits `environment`, a client-id-drift alarm and three unit-reconciliation alarms with no emitter in `src/`), two live provability alarms (PROV-8, PROV-9) with no in-repo Terraform, a three-widget service dashboard, and SLO-1 and SLO-2 readings. They could not be re-verified and are not carried into the sections above. The code-side facts that explain two of them are re-derived above: no `CredClientIdDrift` or unit-reconciliation emitter exists in `src/` (search returned nothing, with a positive control for the bridge-fleet namespace), and `emit_metric` always adds `environment` (`src/autom8_asana/lambda_handlers/cloudwatch.py:52-54`).

### Corrections to the prior pass (c29f58f4 -> 584c8f79)

| Prior claim | Finding at `584c8f79` | Evidence |
|---|---|---|
| Domain Prometheus series, EMF namespace and flag live in `src/autom8_asana/api/metrics.py` (anchors `:24-760`, `:354-425`) | The canonical module is now `src/autom8_asana/observability/prometheus_metrics.py` (857 lines); `src/autom8_asana/api/metrics.py` is a 128-line re-export shim. Anchors moved: series `:24-755`, EMF `:354-446`. | `src/autom8_asana/api/metrics.py:1-60`; `src/autom8_asana/observability/prometheus_metrics.py:24,354` |
| `instrument_app` at `src/autom8_asana/api/main.py:941` | Call at `:953`, comment block `:941-952` | `src/autom8_asana/api/main.py:941-953` |
| Direct-import counts: `autom8y_telemetry` in 21 modules; `get_logger` in 251 of 610 files; `trace_computation` used in 8 other modules | `autom8y_telemetry` in 20 modules; `get_logger` in 257 of 628 files; `trace_computation` in 8 modules (9 decorator sites) | AST and regex passes over the manifest |
| Ruff import ban at `pyproject.toml:351-361` | Now `:510-522` (the dependency block grew by 159 lines) | `pyproject.toml:510-522` |
| 22 Prometheus series all emit | 18 have call sites; `dataframe_build_duration`, `dataframe_circuit_breaker_state`, `api_calls_total`, `api_call_duration_seconds` and their helpers have no caller in `src/` or `mcp/` | Metric inventory table |
| Rate-limit namespaces `sa/pat/ip/other` | The key function now also yields a verified-identity `jwt:` namespace, and `record_rate_limit_429` accepts `sa`, `jwt`, `pat`, `ip`, folding the rest to `other`; a `rate_limit_exceeded` log event (namespace and method only) was added | `src/autom8_asana/api/rate_limit.py:101,221-267`; `src/autom8_asana/observability/prometheus_metrics.py:293-307`; `src/autom8_asana/api/errors.py:766-769` |
| AL-1 authors 4 skip reasons, implied all emitted | `invalid_key` is retired for the status push and has no `StatusPushSkipped` emitter (emitted only on `VocabSyncSkipped`) | `src/autom8_asana/services/gid_push.py:50-53,1560`; `terraform/services/asana/observability_alarms.tf:218-223` |
| PROV-7 emitter is a normal deployed emitter | `CloudWatchDataQualityEmitter` is constructed only in the operator parity tool, which says it is not imported by any deployed path | `src/autom8_asana/substrate/parity_run.py:38-39,363` |
| "No Prometheus alerting rules in-repo" | Still true, but four Stage-1 alert names (A1, A3, A5, A8) appear only in code comments with no rule file | `src/autom8_asana/observability/prometheus_metrics.py:77-97,261,296`; `src/autom8_asana/api/routes/query.py:459` |
| Dark emitters: data-client hook, serve emitter, EMF | Confirmed unchanged and extended: the leads-skip counter has the same unwired-hook shape; `ObservabilityHook` methods are never called by `src/` | `src/autom8_asana/automation/workflows/leads_skip.py:31,75`; `src/autom8_asana/lambda_handlers/leads_consumer.py:107-111` |
| Entry-point instrumentation 7 of 11 | Re-verified unchanged | `@instrument_lambda` sites listed above |
| AL-5 matches only the `memory` tier | Re-verified; tier values `memory` and `s3` both flow through the same f-string | `src/autom8_asana/cache/integration/dataframe_cache.py:299-301,317-319,768` |
| 13 `RB-*` tags, 0 resolve; `alarm_binding_report` omits PROV-7; 4 TF files / 15 alarm blocks / 18 instances | Re-verified | Alerting section |
| New since the prior pass | `src/autom8_asana/trigger/` (7 files, D6 shadow receiver, dark, 4 modules log, no metric or span); `src/autom8_asana/core/api_settings.py` now holds `ASANA_API_LOG_LEVEL` and `ASANA_API_DEBUG`; verified-identity rate-limit keying | `src/autom8_asana/trigger/__init__.py`; `src/autom8_asana/core/api_settings.py:36-72` |
| Live-observed alarm, datapoint, dashboard and SLO-reading statements (prior sections "OBS-LAMBDA-DARK-001", "Alarms that cannot fire", live inventory, "Current readings") | Dropped as unverifiable in this pass; see Knowledge Gaps item 10 | no outward calls permitted |
| Receiver-reliability gap table (RECV-BULK-001..003) | Dropped: outside the obs criteria, not re-derived | n/a |
