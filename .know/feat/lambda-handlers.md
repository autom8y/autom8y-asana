---
domain: feat/lambda-handlers
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/lambda_handlers/"
  - "./src/autom8_asana/entrypoint.py"
  - "./pyproject.toml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# AWS Lambda Function Handlers

## Purpose and Design Rationale

Fleet of 13 Lambda entry points for scheduled and event-driven workloads that cannot run inside
the ECS API server. Complements the REST API by handling long-running, batch, and
infrastructure-maintenance operations without blocking ECS capacity or ECS request latency
budgets.

**Dual-mode container**: Same Docker image serves both ECS (uvicorn) and Lambda (awslambdaric)
modes. Detection: presence of `AWS_LAMBDA_RUNTIME_API` environment variable in `entrypoint.py`.
When absent: `run_ecs_mode()` → uvicorn. When present: `run_lambda_mode(handler)` →
`awslambdaric.main()` with handler module path from `sys.argv[1]`.

**Optional dependency**: `pyproject.toml` `[project.optional-dependencies]` section: `lambda =
["awslambdaric>=2.2.0"]`. Not included in the default `autom8_asana` install. Must be installed
explicitly when building Lambda container images.

**Design decisions documented in source**:
- TDD-DATAFRAME-CACHE-001 §5.7 and TDD-lambda-cache-warmer §3.6 — cache warming spec
- TDD-DETECTION-FIX — cache invalidation rationale
- TDD-CASCADE-FAILURE-FIXES-001 Fix 1 — targeted project manifest invalidation
- ADR-0064 — S3-backed checkpoint rationale
- ADR-DRY-WORKFLOW-001 — `workflow_handler` factory extracted from 95%-identical insights_export
  and conversation_audit (per docstring)
- ADR-bridge-invocation-model, ADR-bridge-dispatch-model, ADR-bridge-observability-fleet —
  workflow bridge handler patterns
- FLAG-1 — architectural constraint: `push_orchestrator.py`, `pipeline_stage_aggregator.py`,
  `reconciliation_runner.py` reside in `lambda_handlers/` (not `services/`) to avoid circular
  import; service modules own the implementations being called

**Rejected alternative — pre-warm deletion** (documented in `cache_warmer.py:449-459`): An
earlier version of TDD-cache-freshness-remediation Fix 2 deleted the S3 manifest after warming so
ECS would do a "fresh build" on restart. Rejected because ECS preload found no manifest and either
OOM'd or left an empty in-memory cache (503 errors). Staleness now handled by watermark freshness
check in the preload path (Fix 3); manifests are preserved for resumption.

---

## Conceptual Model

### Handler Taxonomy (13 files, 4 roles)

| Role | Files | Invocation Pattern |
|------|-------|-------------------|
| Infrastructure maintenance | `cache_warmer`, `cache_invalidate` | Manual or scheduled; hand-written `asyncio.run()` |
| Bridge handlers (data-attachment-bridge) | `insights_export`, `conversation_audit`, `payment_reconciliation` | EventBridge scheduled; use `create_workflow_handler` factory |
| Post-warm side-effects | `push_orchestrator`, `story_warmer`, `pipeline_stage_aggregator`, `reconciliation_runner` | Called internally by `cache_warmer`; NOT standalone Lambda handlers |
| Handler infrastructure | `workflow_handler` (factory), `checkpoint` (S3 state), `cloudwatch` (shared metric emit), `timeout` (early-exit detection) | Shared utilities; no standalone Lambda entry point |

### Two Implementation Patterns

**Pattern A — Manual** (`cache_warmer`, `cache_invalidate`):
- Top-level `handler(event, context)` decorated with `@instrument_lambda` (cache_warmer only;
  cache_invalidate does NOT use `@instrument_lambda`)
- Calls `asyncio.run(_..._async(...))` internally
- Lazy bootstrap via `_ensure_bootstrap()` / deferred imports for cold-start optimization
- `WarmResponse` / `InvalidateResponse` dataclasses as structured return types

**Pattern B — Factory** (`insights_export`, `conversation_audit`, `payment_reconciliation`):
- Module-level `bootstrap()` called at import time (eager, not deferred — contrast with Pattern A)
- `WorkflowHandlerConfig` frozen dataclass specifies: `workflow_factory`, `workflow_id`,
  `log_prefix`, `default_params`, `response_metadata_keys`, `dms_namespace`, `fleet_namespace`
- `create_workflow_handler(config)` returns a decorated `handler(event, context)` function
- Factory internals: `EntityScope.from_event(event)` → client init → `workflow.validate_async()`
  → `workflow.enumerate_async(scope)` → `workflow.execute_async(entities, params)` → metric
  emission → DMS `emit_success_timestamp` → fleet-level `BridgeFleetHealth` metric →
  `BridgeExecutionComplete` domain event (fire-and-forget via `autom8y-events` optional dep)

### Cache Warmer Orchestration Pipeline (7 stages)

Stages 1 is synchronous and gates `WarmResponse.success`. Stages 2–7 are non-blocking: failures
are caught, logged, and do NOT affect `WarmResponse.success`.

1. **DataFrame warming** — per entity, `cascade_warm_order()` order (providers first: business,
   unit before offer, contact, asset_edit, etc.), with checkpoint-resume and timeout detection.
   Entity types: `unit`, `business`, `offer`, `contact`, `asset_edit`, `asset_edit_holder`.
2. **GID mapping push** — `push_orchestrator._push_gid_mappings_for_completed_entities()` →
   `services/gid_push.push_gid_mappings_to_data_service()`. Only entity types with `office_phone`,
   `vertical`, `gid` columns produce GID mappings.
3. **Account status push** — `push_orchestrator._push_account_status_for_completed_entities()` →
   `services/gid_push.extract_status_from_dataframe()` + `push_status_to_data_service()`.
4. **Story cache warming** (Strategy E: piggyback on DataFrame warmer) —
   `story_warmer._warm_story_caches_for_completed_entities()`. Semaphore-bounded (3 concurrent),
   chunk size 100, timeout-checked per chunk.
5. **Vertical backfill** — `_run_vertical_backfill()`. Calls `VerticalBackfillService` for unit
   entity types. Guarded by `ASANA_VERTICAL_BACKFILL_ENABLED` env var (default: disabled).
6. **Pipeline stage aggregation** — `pipeline_stage_aggregator._aggregate_pipeline_stages()`.
   Scans all `process_*` entity DataFrames. Groups by `(office_phone, vertical)`, selects latest
   active process. Output: ephemeral `pl.DataFrame | None` (NOT cached to S3).
7. **Reconciliation shadow** — `reconciliation_runner._run_reconciliation_shadow()`. Requires both
   `unit` and `offer` in `completed_entities`. Runs `ReconciliationConfig(dry_run=True)` → engine
   → executor → report/metrics. Guarded by `ASANA_RECONCILIATION_SHADOW_ENABLED` env var.

### Checkpoint-Resume Protocol (ADR-0064)

- S3 key: `s3://{bucket}/cache-warmer/checkpoints/latest.json`
- Checkpoint saved after EACH entity type (to enable fine-grained resume)
- Staleness window: 1 hour (configurable via `CheckpointManager.staleness_hours`); stale
  checkpoints silently return `None`, warming restarts from scratch
- Single-writer assumption: enforced by `reserved_concurrent_executions=1` on the Lambda; no
  locking mechanism in code
- On timeout (`_should_exit_early` triggers with 2 minutes remaining):
  1. Save checkpoint with current progress
  2. Self-invoke via `Lambda.invoke(InvocationType="Event")` with remaining entities
  3. Return partial `WarmResponse(success=False)` from current invocation

### Feature Groupings (Cross-Feature Relations)

- **gid-data-sync-pipeline** feature: `push_orchestrator` + `pipeline_stage_aggregator` are the
  primary mechanisms for pushing warmed DataFrame data to autom8y-data
- **data-attachment-bridge** feature: `insights_export`, `conversation_audit`,
  `payment_reconciliation` are bridge handlers feeding data into the autom8y-data bridge pipeline
- **cache warming subsystem**: `cache_warmer`, `checkpoint`, `timeout`, `story_warmer`,
  `reconciliation_runner`, `pipeline_stage_aggregator`, `cloudwatch` form the complete cache
  warming apparatus

---

## Implementation Map

### Public Exports (`__init__.py`)

5 handlers exported: `cache_warmer_handler`, `cache_invalidate_handler`,
`insights_export_handler`, `conversation_audit_handler`, `payment_reconciliation_handler`.
The 8 internal modules (`cloudwatch`, `checkpoint`, `timeout`, `workflow_handler`,
`push_orchestrator`, `story_warmer`, `pipeline_stage_aggregator`, `reconciliation_runner`) are NOT
exported from `__init__.py` — they are private utilities.

### Handler-by-Handler Reference

| File | Role | Entry Point | Key Types | Notes |
|------|------|-------------|-----------|-------|
| `cache_warmer.py` | Primary infrastructure maintenance | `handler(event, ctx)` / `handler_async` | `WarmResponse` | Pattern A; `@instrument_lambda`; lazy `_ensure_bootstrap()`; 7-stage pipeline |
| `cache_invalidate.py` | Task/DataFrame cache clearing | `handler(event, ctx)` / `handler_async` | `InvalidateResponse` | Pattern A; no `@instrument_lambda`; `clear_tasks` (default True), `clear_dataframes` (default False), `invalidate_project` (targeted S3 manifest delete) |
| `workflow_handler.py` | Bridge handler factory | `create_workflow_handler(config) -> handler` | `WorkflowHandlerConfig`, `create_workflow_handler` | Pattern B factory; `EntityScope.from_event`; DMS/fleet metric emission; domain event publish |
| `insights_export.py` | Daily BI export bridge | `handler` (via factory) | `InsightsExportWorkflow` | EventBridge 6:00 AM ET daily; DMS: `Autom8y/AsanaInsights` |
| `conversation_audit.py` | Conversation audit bridge | `handler` (via factory) | `ConversationAuditWorkflow` | EventBridge scheduled; DMS: `Autom8y/AsanaAudit`; `attachment_pattern="conversations_*.csv"` |
| `payment_reconciliation.py` | Payment reconciliation bridge | `handler` (via factory) | `PaymentReconciliationWorkflow` | EventBridge Monday 8:00 AM ET; DMS: `Autom8y/AsanaReconciliation` |
| `cloudwatch.py` | Shared CloudWatch emit | `emit_metric(name, value, unit, dims, ns)` | — | Lazy `boto3.client("cloudwatch")`; BROAD-CATCH swallows CloudWatch errors; shared by all other handlers |
| `checkpoint.py` | S3 checkpoint persistence | `CheckpointManager.load_async()` / `save_async()` / `clear_async()` | `CheckpointRecord`, `CheckpointManager` | S3 key: `cache-warmer/checkpoints/latest.json`; 1h staleness window |
| `timeout.py` | Timeout detection + self-invoke | `_should_exit_early(ctx)`, `_self_invoke_continuation(ctx, pending, id)` | — | Buffer: 2 minutes (`TIMEOUT_BUFFER_MS = 120_000`); uses `context.invoked_function_arn` for self-invoke ARN |
| `push_orchestrator.py` | GID + status push side-effects | `_push_gid_mappings_for_completed_entities()`, `_push_account_status_for_completed_entities()` | — | FLAG-1 placement; calls `services/gid_lookup.py`, `services/gid_push.py` |
| `story_warmer.py` | Story cache population | `_warm_story_caches_for_completed_entities()` | — | Strategy E; semaphore(3); chunk 100; timeout-aware |
| `pipeline_stage_aggregator.py` | Pipeline stage aggregation | `_aggregate_pipeline_stages()` | — | FLAG-1 placement; processes `process_*` entities; ephemeral Polars DataFrame output |
| `reconciliation_runner.py` | Reconciliation shadow mode | `_run_reconciliation_shadow()` | — | FLAG-1 placement; requires `unit` + `offer`; `ASANA_RECONCILIATION_SHADOW_ENABLED` guard; always `dry_run=True` |

### Entrypoint Wiring (`entrypoint.py`)

```
entrypoint.main()
  AWS_LAMBDA_RUNTIME_API present? → run_lambda_mode(sys.argv[1])
                                      → awslambdaric.main()
                                         handler path: autom8_asana.lambda_handlers.{module}.handler
  absent?                           → run_ecs_mode() → uvicorn
```

Handler path validation in `run_lambda_mode`: alphanumeric + `.` and `_` only; rejects other characters with `sys.exit(1)`.

### Key External Calls

- `services/gid_lookup.GidLookupIndex.from_dataframe()` — GID mapping index construction
- `services/gid_push.push_gid_mappings_to_data_service()` — push to autom8y-data sync endpoint
- `services/gid_push.extract_status_from_dataframe()` / `push_status_to_data_service()`
- `services/vertical_backfill.VerticalBackfillService.backfill_from_dataframe()`
- `reconciliation/engine.run_reconciliation()` / `reconciliation/executor.execute_actions()`
- `reconciliation/report.build_report()` / `emit_report_metrics()`
- `cache/dataframe/warmer.CacheWarmer.warm_entity_async()`
- `dataframes/cascade_utils.cascade_warm_order()` — entity processing order
- `core/registry_validation.validate_cross_registry_consistency()` — bootstrap guard
- `autom8y_telemetry.aws.instrument_lambda` / `emit_success_timestamp` / `emit_business_metric`
- `autom8y_config.lambda_extension.resolve_secret_from_env()` — Lambda secrets extension

### Test Coverage

All 13 files have test coverage (confirmed in prior observation; 18 test files in
`tests/unit/lambda_handlers/`). `test_workflow_handler.py` carries `pytestmark =
[pytest.mark.xdist_group("workflow_handler")]` per SCAR-W1E-LOADGROUP-001 fix (commit
`149d3673`) to prevent AsyncMock teardown state corruption under `--dist=loadgroup`.

---

## Boundaries and Failure Modes

### Scope Boundaries — What Handlers Do NOT Do

- Handlers do NOT perform entity writes to Asana (read-only cache maintenance + data push)
- `cache_warmer` does NOT clear the task cache (that is `cache_invalidate`'s job)
- `cache_warmer` does NOT clear DataFrames by default — it writes them
- `cache_invalidate` does NOT clear DataFrames unless `clear_dataframes=True` is passed
- Post-warm side-effects (stages 2–7) do NOT affect `WarmResponse.success` — they are fire-and-forget
- `reconciliation_runner` runs in `dry_run=True` mode ONLY — it never mutates Asana state
- The 8 internal helper modules are NOT standalone Lambda handlers — they have no `handler()` top-level function

### Known Risks and Failure Modes

**SCAR-CW-001** (5-onion-layer cold-start, PRs #28-#37): Cache-warmer Lambda cold-start failure
chain: Errno 97 (no UNIX socket) → Errno 111 (connection refused) → HTTP 400 URL-encoding → HTTP
400 init-time config → EntityProjectRegistry ARN-resolution failure. Fixed by 5 sequential
remediations. Mitigated by lazy `_ensure_bootstrap()` and deferred imports in Pattern A handlers.

**Bootstrap discrepancy**: Pattern A handlers (`cache_warmer`, `cache_invalidate`) defer
`bootstrap()` lazily via `_ensure_bootstrap()`. Pattern B handlers (`insights_export`,
`conversation_audit`, `payment_reconciliation`) call `bootstrap()` eagerly at module import time.
An agent must know which pattern is in use before modifying initialization order.

**`cache_invalidate` blast radius**: `clear_tasks=True` (default) invokes
`TieredCacheProvider.clear_all_tasks()` which destroys ALL entry types under `asana:tasks:*`
including story incremental cursors (ADR-0020). Recovery: 5–30 minutes via `cache_warmer`. Story
fetches become full-history until warmer re-populates. Does NOT clear DataFrameCache.

**Targeted manifest invalidation** (`invalidate_project`): Deletes S3 section parquets and
manifest for a specific project GID. Triggers full rebuild on next warm cycle. Does NOT clear task
cache or DataFrame memory cache.

**Checkpoint single-writer assumption**: `CheckpointManager` performs no locking. Correctness
requires `reserved_concurrent_executions=1` on the Lambda in infrastructure (not verifiable from
source). Concurrent invocations would corrupt checkpoint state.

**Self-invocation requires `invoked_function_arn`**: `_self_invoke_continuation()` silently
no-ops if `context.invoked_function_arn` is absent (e.g., local testing). No error, no metric.
`SelfContinuationInvoked` metric fires only on successful invocation.

**SCAR-W1E-LOADGROUP-001**: `workflow_handler.py` uses `@instrument_lambda` which wraps the
handler in state that is sensitive to `AsyncMock(spec=DataServiceClient)` context-manager teardown
ordering under pytest-xdist. Mitigated by `xdist_group("workflow_handler")` marker.

**FLAG-1 circular dependency constraint**: `push_orchestrator`, `pipeline_stage_aggregator`, and
`reconciliation_runner` MUST remain in `lambda_handlers/` (not `services/`). Moving them to
`services/` would create a circular import because `services/` already owns the implementations
being called. TENSION-004 documents this.

**LAMBDA-OBS-001 instrumentation gap** (from `.know/obs.md`): 10 of 13 handlers have no
`autom8y_telemetry` import beyond shared `emit_metric()` CloudWatch utility. Only `cache_warmer`
(`@instrument_lambda`, `emit_success_timestamp`) and `workflow_handler` (`instrument_lambda`,
`emit_success_timestamp`, `emit_business_metric`) have span-level telemetry. Uninstrumented:
`cache_invalidate`, `cloudwatch`, `checkpoint`, `timeout`, `push_orchestrator`, `story_warmer`,
`pipeline_stage_aggregator`, `reconciliation_runner`, `insights_export`, `conversation_audit`,
`payment_reconciliation` (the last three are instrumented only via the `workflow_handler` factory).

**Lambda log-trace correlation gap**: Lambda handlers emit CloudWatch metrics but do NOT wire
`add_otel_trace_ids` — log-trace correlation only fires in ECS mode.

### Configuration Boundaries

| Env Var | Required By | Effect |
|---------|-------------|--------|
| `AWS_LAMBDA_RUNTIME_API` | `entrypoint.py` | Triggers Lambda mode (must be present) |
| `ASANA_PAT` | All handlers | Asana API credentials |
| `ASANA_WORKSPACE_GID` | `cache_warmer` | Workspace for entity discovery |
| `ASANA_CACHE_S3_BUCKET` | `cache_warmer`, `cache_invalidate`, `checkpoint` | S3 bucket for cache and checkpoint storage |
| `ASANA_CACHE_S3_PREFIX` | `cache_warmer`, `cache_invalidate` | S3 key prefix (default: `"asana-cache"`) |
| `REDIS_HOST` | `cache_invalidate` | Hot tier cache |
| `AUTOM8Y_DATA_URL` | Bridge handlers | autom8y-data base URL |
| `AUTOM8Y_DATA_API_KEY` | Bridge handlers | autom8y-data API key |
| `ASANA_VERTICAL_BACKFILL_ENABLED` | `cache_warmer` | Enables vertical backfill stage (default: disabled) |
| `ASANA_RECONCILIATION_SHADOW_ENABLED` | `cache_warmer` → `reconciliation_runner` | Enables reconciliation shadow stage (default: disabled) |
| `AUTOM8_EXPORT_ENABLED` | `insights_export` | Feature flag (default: enabled) |
| `AUTOM8_AUDIT_ENABLED` | `conversation_audit` | Feature flag (default: `"true"`) |
| `AUTOM8_RECONCILIATION_ENABLED` | `payment_reconciliation` | Feature flag (default: enabled) |
| `CLOUDWATCH_NAMESPACE` | `cloudwatch.emit_metric` | Override CloudWatch namespace (default: `autom8/lambda`) |

### Interaction Points with Other Features

- **cache subsystem** (`cache/dataframe/`, `cache/providers/`, `cache/backends/`): `cache_warmer`
  and `cache_invalidate` directly operate on `DataFrameCache` and `TieredCacheProvider`
- **services layer** (`services/gid_lookup.py`, `services/gid_push.py`,
  `services/vertical_backfill.py`, `services/discovery.py`, `services/resolver.py`): All called
  by `cache_warmer` and its orchestration helpers
- **reconciliation subsystem** (`reconciliation/engine.py`, `executor.py`, `report.py`): Called by
  `reconciliation_runner`; boundary risk: `_REQUIRED_ENTITIES = frozenset({"unit", "offer"})` is
  hardcoded — adding a required entity type requires changing this constant
- **automation/workflows** (`automation/workflows/insights.py`,
  `automation/workflows/conversation_audit.py`,
  `automation/workflows/payment_reconciliation/workflow.py`): Consumed by the three bridge
  handlers via `WorkflowHandlerConfig.workflow_factory`
- **autom8y-events** (optional dep): `workflow_handler` imports from `autom8y_events` with a
  try/except ImportError guard; absence silently skips domain event publication

---

## Knowledge Gaps

1. `cascade_warm_order()` exact entity list and ordering algorithm not read (`dataframes/cascade_utils.py`)
2. `EntityScope.from_event()` schema — which event keys are parsed and how scope is derived
3. `WorkflowAction.enumerate_async()` + `execute_async()` contract (abstract base in `automation/workflows/base.py`)
4. Lambda timeout/concurrency config not in source (IaC only) — `reserved_concurrent_executions=1` for checkpoint single-writer assumption is undeclared in code
5. `autom8y_telemetry.aws.instrument_lambda` internals — what exactly it wraps and whether it is safe to apply to Pattern A handlers globally
6. Fleet namespace `Autom8y/AsanaBridgeFleet` — default on all `WorkflowHandlerConfig` instances; opting out requires `fleet_namespace=None`; no in-source documentation of which handlers have opted out

```metadata
confidence_basis: All 13 handler files fully read; entrypoint.py fully read; supporting .know/ files
cross-referenced (obs.md LAMBDA-OBS-001, scar-tissue.md SCAR-CW-001 + SCAR-W1E-LOADGROUP-001,
design-constraints.md TENSION-004 FLAG-1). Test directory listed (18 test files confirmed).
pyproject.toml lambda optional dep confirmed. Primary gaps: IaC config, cascade_warm_order internals,
EntityScope.from_event schema.
```
