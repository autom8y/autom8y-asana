---
domain: feat/lambda-handlers
generated_at: "2026-03-18T12:39:28Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/lambda_handlers/**/*.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "2c604fa"
confidence: 0.92
format_version: "1.0"
---

# AWS Lambda Function Handlers

## Purpose and Design Rationale

### Why This Feature Exists

The AWS Lambda handlers exist to solve a structural tension in the autom8y-asana system: the application runs as both a persistent ECS/FastAPI HTTP server and as event-driven Lambda functions. These are fundamentally different execution models. The Lambda handlers represent the **event-driven, scheduled, and maintenance** side of the system -- tasks that are not user-request-driven and must be triggered by time schedules or operational events.

The primary problem the handlers solve is **cache pre-warming and maintenance**. The ECS server serves Asana data from an S3/Redis/memory cache. If that cache is cold when the server starts, response latency is unacceptable and Asana API rate limits would be hit during serving. The Lambda handlers pre-populate the cache before ECS startup and maintain it on schedule.

The secondary problem is **workflow automation**: periodic data workflows (insights export to the data service, conversation audit) must run on a schedule without blocking the HTTP server.

### Design Decisions That Shaped It

**Dual-mode entry via single container image**: Rather than building separate container images for ECS and Lambda, the system uses a single image and a shared entrypoint (`src/autom8_asana/entrypoint.py`). Mode is selected by detecting the `AWS_LAMBDA_RUNTIME_API` environment variable at runtime. When present, `awslambdaric.main()` is called with the handler path from `sys.argv[1]`. This avoids image proliferation at the cost of a slightly heavier Lambda cold-start image.

**Handler path as argv[1]**: The entrypoint does not hardcode a handler. Any of the 7 handler modules can be targeted by passing its dotted path as an argument (e.g., `autom8_asana.lambda_handlers.cache_warmer.handler`). This makes the Lambda deployment configuration explicit and auditable in deployment YAML/CDK, not embedded in code.

**Resume-on-retry via S3 checkpoint**: Cache warming over 6 entity types can exceed a Lambda's 15-minute timeout. Rather than simply failing, `cache_warmer` saves a checkpoint to S3 after each entity type completes, then self-invokes asynchronously with the remaining entities. This was a deliberate design decision (ADR-0064) to handle the reality that a single Lambda invocation cannot always complete the work.

**DRY workflow factory pattern**: `insights_export.py` and `conversation_audit.py` were originally 95% identical boilerplate. They were refactored (per ADR-DRY-WORKFLOW-001) into a `WorkflowHandlerConfig` + `create_workflow_handler()` factory in `workflow_handler.py`. New workflow handlers now require only a config struct and a workflow factory callable.

**Non-blocking side effects**: Both story cache warming and GID mapping push happen after the main DataFrame cache warming. They are non-blocking: failures are caught and logged but never propagate to affect the warmer's success status. This was an explicit isolation decision.

**Dead-man's-switch metric**: Both `cache_warmer` and the workflow handlers emit a `emit_success_timestamp()` metric on success. A Grafana alert fires if the metric is absent or stale beyond a threshold (24h for cache warmer), providing operational alerting without a separate monitoring system.

---

## Conceptual Model

### The Dual-Mode Mental Model

Think of the system as one codebase, two runtime personalities:
- **ECS mode**: Long-lived process, serves HTTP requests, runs `uvicorn`, consumes the cache.
- **Lambda mode**: Short-lived function, handles a single event, typically **populates** or **maintains** the cache or runs a scheduled workflow.

The cache-warming handlers run **before** ECS starts serving, filling S3/Redis/memory so the server's first requests are cache hits.

### Handler Categories

There are two categories of handlers:

**Cache maintenance handlers** (stateful, direct cache operations):
- `cache_warmer`: Hydrates S3 cache with DataFrame snapshots of all Asana entity types. Primary pre-deployment workhorse.
- `cache_invalidate`: Clears task cache (Redis + S3) or dataframe cache, or invalidates a specific project's manifest. Used to force a rebuild when cached data is stale/corrupt.
- `checkpoint`: S3-backed checkpoint manager for cache warmer resume-on-retry. Not invoked directly as a Lambda; provides `CheckpointManager` and `CheckpointRecord` types.

**Workflow handlers** (stateless, execute a `WorkflowAction`):
- `insights_export`: Exports Asana insights data to the autom8_data service. Triggered by EventBridge on a daily schedule (6:00 AM ET).
- `conversation_audit`: Audits conversation data in Asana. Triggered by EventBridge on a configured schedule.
- `workflow_handler`: Generic factory (not a handler itself). Provides `WorkflowHandlerConfig` and `create_workflow_handler()` for any `WorkflowAction`.

`cloudwatch.py` is a shared utility module, not a handler. It provides `emit_metric()` used across all handlers.

### Cache Warming Lifecycle

```
Trigger (EventBridge / manual invocation)
  -> cache_warmer.handler()
    -> _ensure_bootstrap()        [lazy model registry init]
    -> CheckpointManager.load_async()  [resume if checkpoint exists and fresh]
    -> cascade_warm_order()        [entity priority: providers before consumers]
    -> FOR each entity_type:
         _should_exit_early(context)  [2-minute timeout buffer]
         IF near timeout:
           CheckpointManager.save_async()   [persist progress to S3]
           _self_invoke_continuation()       [async self-invocation]
           RETURN partial result
         warmer.warm_entity_async()   [DataFrameBuilder -> S3 cache]
         CheckpointManager.save_async()   [save after each entity]
    -> _push_gid_mappings_for_completed_entities()   [non-blocking]
    -> _warm_story_caches_for_completed_entities()   [non-blocking]
    -> CheckpointManager.clear_async()   [clear on full completion]
    -> emit_success_timestamp(DMS_NAMESPACE)   [dead-man's-switch]
```

### EntityScope -- Cross-Cutting Invocation Contract

`EntityScope` (`src/autom8_asana/core/scope.py`) is a frozen dataclass that flows from the Lambda event boundary into workflow execution. It carries targeting parameters: `entity_ids`, `section_filter`, `limit`, `dry_run`. `EntityScope.from_event()` is called at the handler boundary; `scope.to_params()` passes `dry_run` into workflow params. This allows the same workflow code to be used from Lambda, API, and CLI.

### Workflow Handler Pattern

```
WorkflowHandlerConfig(
    workflow_factory=callable,    # (asana_client, data_client) -> WorkflowAction
    workflow_id="insights-export",
    default_params={...},
    dms_namespace="Autom8y/AsanaInsights",
)
  -> create_workflow_handler(config)
    -> handler(event, context)   [decorated with @instrument_lambda]
      -> EntityScope.from_event(event)
      -> AsanaClient() + DataServiceClient()
      -> workflow.validate_async()
      -> workflow.enumerate_async(scope)
      -> workflow.execute_async(entities, params)
      -> emit metrics
      -> emit_success_timestamp(dms_namespace)  [if dms_namespace set]
```

### Relationship to Other Features

- **Cache system** (`src/autom8_asana/cache/`): `cache_warmer` and `cache_invalidate` are the primary consumers of `TieredCacheProvider`, `RedisCacheProvider`, `DataFrameCache`.
- **DataFrame builders** (`src/autom8_asana/dataframes/`): `CacheWarmer` from `src/autom8_asana/cache/dataframe/warmer.py` drives `DataFrameBuilder.build_async()` for each entity type.
- **Automation workflows** (`src/autom8_asana/automation/workflows/`): `InsightsExportWorkflow` and `ConversationAuditWorkflow` are the concrete `WorkflowAction` implementations that the workflow handler factory wraps.
- **Entity registry** (`src/autom8_asana/core/entity_registry.py`): `EntityProjectRegistry` provides project GID lookups during cache warming. `_ensure_bootstrap()` initializes the model registry (required for detection to work).
- **GID push** (`src/autom8_asana/services/gid_push.py`): After warming, GID mappings are pushed to the autom8_data service.

---

## Implementation Map

### File Inventory

| File | Role | Key Types / Functions |
|------|------|-----------------------|
| `src/autom8_asana/entrypoint.py` | Dual-mode entry point | `main()`, `run_lambda_mode()` |
| `src/autom8_asana/lambda_handlers/__init__.py` | Public re-exports | `cache_warmer_handler`, `cache_invalidate_handler`, etc. |
| `src/autom8_asana/lambda_handlers/cache_warmer.py` | Primary cache warming handler | `WarmResponse`, `handler`, `handler_async`, `_warm_cache_async`, `_should_exit_early`, `_self_invoke_continuation`, `_warm_story_caches_for_completed_entities`, `_push_gid_mappings_for_completed_entities` |
| `src/autom8_asana/lambda_handlers/cache_invalidate.py` | Cache invalidation handler | `InvalidateResponse`, `handler`, `handler_async`, `_invalidate_cache_async` |
| `src/autom8_asana/lambda_handlers/cloudwatch.py` | Shared metric emission | `emit_metric()` |
| `src/autom8_asana/lambda_handlers/checkpoint.py` | Checkpoint persistence | `CheckpointRecord`, `CheckpointManager` |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | Generic workflow handler factory | `WorkflowHandlerConfig`, `create_workflow_handler()` |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Insights export workflow handler | `handler` (created by factory) |
| `src/autom8_asana/lambda_handlers/conversation_audit.py` | Conversation audit workflow handler | `handler` (created by factory) |
| `src/autom8_asana/core/scope.py` | Cross-cutting invocation scope | `EntityScope`, `EntityScope.from_event()` |

### Key Types and Signatures

**`WarmResponse`** (cache_warmer.py):
```python
@dataclass
class WarmResponse:
    success: bool
    message: str
    entity_results: list[dict[str, Any]]
    total_rows: int
    duration_ms: float
    timestamp: str
    checkpoint_cleared: bool
    invocation_id: str | None
    def to_dict(self) -> dict[str, Any]: ...
```

**`InvalidateResponse`** (cache_invalidate.py):
```python
@dataclass
class InvalidateResponse:
    success: bool
    message: str
    tasks_cleared: dict[str, int]   # {"redis": N, "s3": N}
    dataframes_cleared: int
    projects_invalidated: int
    duration_ms: float
    timestamp: str
    invocation_id: str | None
```

**`CheckpointRecord`** (checkpoint.py):
```python
@dataclass
class CheckpointRecord:
    invocation_id: str
    completed_entities: list[str]
    pending_entities: list[str]
    entity_results: list[dict[str, Any]]
    created_at: datetime
    expires_at: datetime
    def is_stale(self) -> bool: ...
    def to_json(self) -> str: ...
    @classmethod def from_json(cls, data: str) -> CheckpointRecord: ...
```

**`CheckpointManager`** (checkpoint.py):
```python
@dataclass
class CheckpointManager:
    bucket: str                         # defaults from settings.s3.bucket
    prefix: str = "cache-warmer/checkpoints/"
    s3_client: S3Client | None = None
    staleness_hours: float = 1.0        # default 1 hour
    async def load_async(self) -> CheckpointRecord | None: ...
    async def save_async(self, invocation_id, completed_entities, pending_entities, entity_results) -> bool: ...
    async def clear_async(self) -> bool: ...
```

**`WorkflowHandlerConfig`** (workflow_handler.py):
```python
@dataclass(frozen=True)
class WorkflowHandlerConfig:
    workflow_factory: Callable[..., WorkflowAction]
    workflow_id: str
    log_prefix: str
    default_params: dict[str, Any]
    response_metadata_keys: tuple[str, ...]
    requires_data_client: bool = True
    dms_namespace: str | None = None
```

**`create_workflow_handler`** (workflow_handler.py):
```python
def create_workflow_handler(
    config: WorkflowHandlerConfig,
) -> Callable[[dict[str, Any], Any], dict[str, Any]]:
    # Returns handler(event, context) -> dict decorated with @instrument_lambda
```

**`emit_metric`** (cloudwatch.py):
```python
def emit_metric(
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: dict[str, str] | None = None,
    namespace: str | None = None,
) -> None: ...
```

**`EntityScope`** (core/scope.py):
```python
@dataclass(frozen=True)
class EntityScope:
    entity_ids: tuple[str, ...]
    section_filter: frozenset[str]
    limit: int | None
    dry_run: bool
    @classmethod def from_event(cls, event: dict[str, Any]) -> EntityScope: ...
    def to_params(self) -> dict[str, Any]: ...
```

### Lambda Handler Entry Points (dotted paths for deployment)

| Handler | Entry Point |
|---------|------------|
| Cache warmer | `autom8_asana.lambda_handlers.cache_warmer.handler` |
| Cache invalidate | `autom8_asana.lambda_handlers.cache_invalidate.handler` |
| Insights export | `autom8_asana.lambda_handlers.insights_export.handler` |
| Conversation audit | `autom8_asana.lambda_handlers.conversation_audit.handler` |

### Entrypoint Mode Detection

```python
# src/autom8_asana/entrypoint.py
runtime_api = os.environ.get("AWS_LAMBDA_RUNTIME_API")
if not runtime_api:
    run_ecs_mode()  # uvicorn
else:
    handler = sys.argv[1]  # e.g. "autom8_asana.lambda_handlers.cache_warmer.handler"
    run_lambda_mode(handler)  # awslambdaric.main()
```

Handler name is validated with: `all(c.isalnum() or c in "._" for c in handler)`.

### Test Coverage

Tests live in `tests/unit/lambda_handlers/`:
- `test_cache_warmer.py` -- main cache warmer flow
- `test_cache_warmer_gid_push.py` -- GID mapping push after warming
- `test_cache_warmer_self_continuation.py` -- self-invocation continuation path
- `test_cache_invalidate.py` -- invalidation paths (tasks, dataframes, project manifest)
- `test_checkpoint.py` -- `CheckpointManager` load/save/clear/staleness
- `test_insights_export.py` -- insights export workflow handler
- `test_workflow_handler.py` -- generic workflow factory
- `test_story_warming.py` -- story cache warming after DataFrame warm
- `test_warmer_manifest_clearing.py` -- manifest preservation behavior

No dedicated `test_conversation_audit.py` was found in scope, but the conversation_audit handler uses the same `create_workflow_handler` factory tested in `test_workflow_handler.py`.

### External Dependencies (Lambda-Specific)

- `awslambdaric` -- Lambda runtime interface client (wraps Lambda runtime API)
- `autom8y_config.lambda_extension.resolve_secret_from_env` -- resolves secrets from env
- `autom8y_log.get_logger` -- structured logging
- `autom8y_telemetry.aws.instrument_lambda` -- Lambda instrumentation decorator
- `autom8y_telemetry.aws.emit_success_timestamp` -- dead-man's-switch metric emission
- `boto3` -- CloudWatch, S3, Lambda clients (all lazily initialized)

---

## Boundaries and Failure Modes

### Scope Limitations

**`src/autom8_asana/lambda_handlers/` is rated "Safe" for changeability** (confirmed in design-constraints.md): these are entry points with no internal dependents. Changes within the `lambda_handlers/` package do not ripple into other packages.

However, the handlers have wide **outgoing** dependencies:
- `cache_warmer` imports from `cache/`, `services/`, `dataframes/`, `models/`, `auth/`
- `workflow_handler` imports from `automation/workflows/`, `clients/data/`, `core/`
- Changes to those downstream packages can break handler behavior

**Not covered by this feature**: The `CacheWarmer` implementation itself lives in `src/autom8_asana/cache/dataframe/warmer.py`. The `WorkflowAction` base class and concrete workflow implementations live in `src/autom8_asana/automation/workflows/`. The handlers are thin invocation wrappers around those components.

### Timeout Behavior (RISK-007)

`_should_exit_early(context)` checks `context.get_remaining_time_in_millis() < 120_000`. When `context is None` (local/test mode), it always returns `False`. **There is no timeout enforcement in test mode.** A mock context with `get_remaining_time_in_millis()` must be passed explicitly to test timeout paths.

### Checkpoint Staleness

`CheckpointRecord` has a default staleness window of 1 hour. A checkpoint older than 1 hour is ignored and warming restarts from scratch. This window is configurable via `CheckpointManager.staleness_hours`. The checkpoint key is fixed: `s3://{bucket}/cache-warmer/checkpoints/latest.json` -- only one checkpoint exists at a time.

Thread safety: `CheckpointManager` is not thread-safe, but Lambda reserved concurrency must be `1` for the cache warmer to prevent race conditions on the checkpoint. This is documented in `checkpoint.py` but is enforced externally (not in code).

### Broad-Catch Patterns (Intentional)

Every handler has two levels of exception catching:

1. **Inner isolation catches** (`# BROAD-CATCH: isolation`): Per-entity or per-task failures do not abort the batch. Story warming failures, GID push failures, and self-invocation failures are all swallowed and logged.
2. **Outer boundary catches** (`# BROAD-CATCH: boundary`): The top-level `handler()` function always returns a structured dict rather than raising. Lambda never sees an uncaught exception. The response `statusCode` is 500 on failure but the response body is always well-formed.

This is an intentional design: Lambda must not crash on unhandled exceptions because that triggers a generic error response without structured logging.

### `clear_all_tasks()` Blast Radius

When `cache_invalidate` runs with `clear_tasks=True` (the default), it clears ALL task cache entries (`asana:tasks:*`) from both Redis and S3. The inline comment in `cache_invalidate.py` documents the consequence: **story incremental cursors (ADR-0020) are destroyed**. All subsequent story fetches become full-history fetches until the cache_warmer re-populates. Recovery time is 5-30 minutes depending on entity count. Cache invalidate should always be followed by a cache_warmer invocation.

**Per-task DataFrame entries (`asana:struc:*`) are NOT cleared by `clear_tasks=True`**. Dataframe invalidation requires the separate `clear_dataframes=True` flag.

### Project-Targeted Manifest Invalidation

`cache_invalidate` accepts `invalidate_project: str` to surgically delete a single project's S3 section parquets and manifest. This is the recovery mechanism for SCAR-006 (cascade hierarchy warming gaps). It deletes `section_files` first, then the `manifest`, ensuring a full rebuild on next warm-up. It does not affect the task cache or dataframe memory cache.

### `bootstrap()` Lazy Initialization Pattern

`cache_warmer.py` calls `_ensure_bootstrap()` lazily on each `handler()` invocation (guarded by a module-level `_bootstrap_initialized` flag). This defers model registry initialization to avoid cold-start import failures (SCAR-013 pattern). `insights_export.py` calls `bootstrap()` at module import time (line 19 and line 33 -- called twice, second is a no-op). `conversation_audit.py` calls `bootstrap()` at module import time (line 23).

### Event Payload Shape -- No Validation

Neither `cache_invalidate.handler` nor `workflow_handler.create_workflow_handler` validate the event payload shape beyond `event.get(key, default)`. Unknown keys are silently ignored (this is intentional for forward compatibility per the `EntityScope.from_event` design). Invalid values for known keys (e.g., `strict="yes"` instead of `True`) will silently use the string as-is and may cause unexpected behavior downstream.

### CloudWatch Client -- Global Singleton

`cloudwatch.py` uses a module-level `_cloudwatch_client` global with lazy initialization. This is a singleton that persists across warm Lambda invocations. If the CloudWatch client fails, the error is caught and logged as a warning (`# BROAD-CATCH: metrics`) -- metrics loss never fails a handler.

### Self-Invocation Dependency

The self-continuation path in `cache_warmer._self_invoke_continuation()` requires `context.invoked_function_arn`. In test/local environments, `context` is typically `None` or lacks `invoked_function_arn`, so self-continuation is silently skipped. This means the multi-invocation resume path is only exercisable in a real Lambda environment.

### `insights_export.py` Double Bootstrap

`insights_export.py` calls `bootstrap()` at module import time twice (lines 19 and 33). The second call is harmless because `bootstrap()` is idempotent (guarded internally), but it is a code smell noted for completeness.

### Cascade Warm Order Dependency

`cache_warmer._warm_cache_async()` calls `cascade_warm_order()` from `src/autom8_asana/dataframes/cascade_utils.py` to determine entity processing order. This order ensures that cascade providers (business, unit) warm before consumers (offer, contact, asset_edit). If a new entity type is added that has cascade dependencies, it must be registered in `cascade_warm_order()` output or it will warm in an arbitrary position.

## Knowledge Gaps

1. **No example file for cache warming**: The census referenced `examples/09-cache-warming.py`, but this file does not exist in the repository. The actual example file at `examples/09_protocol_adapters.py` covers a different topic. The cache warming knowledge comes entirely from source code and tests.

2. **`conversation_audit` has no dedicated test file**: No `tests/unit/lambda_handlers/test_conversation_audit.py` was found. Coverage relies on the shared `test_workflow_handler.py`.

3. **Deployment configuration not documented in code**: There is no infrastructure-as-code (CDK/Terraform) in this repository showing EventBridge trigger schedules, Lambda timeout settings, reserved concurrency settings, or memory allocations. The 15-minute Lambda timeout is referenced in code but its actual configured value in deployment is not visible here.

4. **`checkpoint.py` not in `__all__`**: `CheckpointManager` and `CheckpointRecord` are not exported from `lambda_handlers/__init__.py`. The module is an internal utility but is used directly by `cache_warmer` via explicit import. This is intentional but creates an asymmetry with the public-facing handlers.

5. **`_self_invoke_continuation` concurrency safety**: The self-continuation path fires `InvocationType=Event` asynchronously before the current invocation returns. If the Lambda reserved concurrency is not `1`, a previous invocation that has not yet completed and the new invocation could run concurrently, both writing to the same S3 checkpoint key. The safety guarantee relies entirely on the deployment configuration.
