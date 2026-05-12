---
domain: feat/workflow-invoke-api
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/workflows.py"
  - "./src/autom8_asana/lambda_handlers/workflow_handler.py"
  - "./src/autom8_asana/api/lifespan.py"
  - "./tests/unit/api/routes/test_workflows.py"
  - "./tests/unit/lambda_handlers/test_workflow_handler.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.92
format_version: "1.0"
---

# Workflow Invocation API (HTTP-facing Workflow Dispatch Surface)

## Purpose

The Workflow Invocation API is the HTTP-facing surface for dispatching registered
workflows against a list of Asana entity GIDs. It exists to bridge the Lambda
execution model (EventBridge-triggered, async, batch-scoped) with a synchronous
HTTP caller surface, enabling on-demand workflow execution without requiring direct
Lambda invocation access.

**Problem it solves**: Lambda handlers are event-driven and require AWS SDK or
EventBridge access to trigger. Operators and services need an HTTP endpoint to
invoke workflows ad hoc — for backfill runs, dry-run previews, debugging, or
integration with CI-level orchestration. The API endpoint provides that surface.

**Design decisions**:
- Per `TDD-ENTITY-SCOPE-001 Section 2.7`: the endpoint reuses `WorkflowHandlerConfig`
  from Lambda handlers — the same config objects that create Lambda handlers also
  register with the API invoke surface. This is the **dual-use config** pattern.
- **Separation from automation-engine execution**: The API invoke surface handles
  HTTP request lifecycle (auth, rate limiting, timeout, audit logging), while the
  automation engine handles scheduled polling and trigger evaluation. These are
  distinct execution paths that share the same `WorkflowAction` interface.
- **202-pattern intent vs 200 actuality**: The endpoint executes synchronously
  (within a 120-second timeout) and returns 200 with a completed `WorkflowResult`.
  It does not use 202/async dispatch. The feature was designed for synchronous
  workflows short enough to complete within the hard 120s limit.
- `ADR-DRY-WORKFLOW-001` (referenced in `workflow_handler.py` header) established
  the `WorkflowHandlerConfig` abstraction to eliminate handler-level boilerplate
  extracted from `insights_export.py` and `conversation_audit.py`, which were 95%
  identical before the refactor.

**Alternatives rejected** (inferred from code structure): per-workflow custom
endpoints were rejected in favor of a single generic `/{workflow_id}/invoke` route.
Config-driven registration at startup avoids conditional routing and allows new
workflows to be added without route changes.

---

## Conceptual Model

### Core Abstractions

**`WorkflowHandlerConfig`** (`lambda_handlers/workflow_handler.py`) — Frozen dataclass.
The unit of workflow registration. Contains:
- `workflow_factory: Callable[(asana_client, data_client) -> WorkflowAction]` —
  deferred construction (cold-start optimization; Lambda module-import-time is hot).
- `workflow_id: str` — primary key in the registry (`_WORKFLOW_CONFIGS` dict).
- `log_prefix: str` — structured-log event prefix for all log events.
- `default_params: dict[str, Any]` — merged with request overrides; event-overridable.
- `response_metadata_keys: tuple[str, ...]` — keys from `WorkflowResult.metadata` to
  surface in the HTTP response body.
- `requires_data_client: bool` — whether to init `DataServiceClient` (default True).
- `dms_namespace: str | None` — CloudWatch dead-man's-switch namespace (optional).
- `fleet_namespace: str | None` — defaults to `"Autom8y/AsanaBridgeFleet"`. All
  bridge handlers participate in fleet observability unless `fleet_namespace=None`.

**`WorkflowInvokeRequest`** (`api/routes/workflows.py`) — Pydantic model with
`extra="forbid"`. Fields:
- `entity_ids: list[str]` — 1–100 numeric Asana GIDs; validated by `field_validator`.
  Non-numeric GIDs and empty list both raise 422 (Pydantic-level).
- `dry_run: bool` — default False. When True, `EntityScope.dry_run=True` propagates
  to all write operations downstream.
- `params: dict[str, Any]` — caller-provided overrides; merged on top of
  `WorkflowHandlerConfig.default_params` at invocation time.

**`WorkflowInvokeResponse`** (`api/routes/workflows.py`) — Pydantic model. Fields:
- `request_id` — correlation ID for tracing.
- `invocation_source` — always `"api"` (distinguishes from Lambda invocation).
- `workflow_id`, `dry_run`, `entity_count` — echo back the invocation parameters.
- `result` — serialized `WorkflowResult` via `to_response_dict()`, optionally
  extended with `response_metadata_keys` from config.

**`WorkflowEntry`** (`api/routes/workflows.py`) — List metadata model. Used by
`GET /api/v1/workflows/` to enumerate registered workflows. Surfaces
`workflow_id`, `log_prefix`, `requires_data_client`, `response_metadata_keys`.

**`_WORKFLOW_CONFIGS`** (`api/routes/workflows.py`) — Module-level dict
`dict[str, WorkflowHandlerConfig]`. The live registry. Populated at startup via
`register_workflow_config()`. Keyed by `workflow_id`.

### Registration Lifecycle

1. At app startup (step 12 of the 13-step `lifespan.py` sequence), `register_workflow_config()` is called twice:
   - `register_workflow_config(insights_config)` — registers `"insights-export"` workflow.
   - `register_workflow_config(audit_config)` — registers `"conversation-audit"` workflow.
2. Both configs are imported from the Lambda handler modules
   (`lambda_handlers/insights_export._config`, `lambda_handlers/conversation_audit._config`).
3. `app.state.workflow_configs_registered = True` signals health check readiness;
   `set_workflow_configs_registered(True)` gates `/health/ready`.
4. On registration failure (broad-catch), `workflow_configs_registered = False` and
   `/api/v1/workflows/{id}/invoke` returns 404 for all workflows.

### Invocation Execution Model

```
POST /api/v1/workflows/{workflow_id}/invoke
  → rate check (10/minute per client)
  → audit log "workflow_invoke_api"
  → _get_workflow_factory(workflow_id) → WorkflowHandlerConfig or None
    → None → raise 404 WORKFLOW_NOT_FOUND
  → EntityScope(entity_ids=tuple(...), dry_run=...)
  → params = {**config.default_params, **body.params, workflow_id=..., **scope.to_params()}
  → AsanaClient(token=auth_context.asana_pat)  [per-request, no pool]
  → if requires_data_client:
      async with DataServiceClient() as data_client:
        workflow = config.workflow_factory(asana_client, data_client)
        result = await _validate_enumerate_execute(workflow, scope, params, ..., 120s)
    else:
      workflow = config.workflow_factory(asana_client, None)
      result = await _validate_enumerate_execute(workflow, scope, params, ..., 120s)
  → on TimeoutError → raise 504 WORKFLOW_TIMEOUT
  → emit_metric("WorkflowInvokeCount", 1, dimensions={workflow_id, source="api", dry_run})
  → audit log "workflow_invoke_completed"
  → return SuccessResponse[WorkflowInvokeResponse]
```

**`_validate_enumerate_execute`** (internal coroutine in `workflows.py`):
1. `await workflow.validate_async()` — pre-flight check; 422 if errors returned.
2. `entities = await workflow.enumerate_async(scope)` — enumerate target entities.
3. `result = await workflow.execute_async(entities, params)` — execute.
4. Entire step 2+3 wrapped in `asyncio.wait_for(..., timeout=120)`.

### Registered Workflows (at `8980bcd7`)

| workflow_id | Handler module | `requires_data_client` | `dms_namespace` | key `response_metadata_keys` |
|---|---|---|---|---|
| `"insights-export"` | `lambda_handlers/insights_export.py` | True (default) | `"Autom8y/AsanaInsights"` | `("total_tables_succeeded", "total_tables_failed")` |
| `"conversation-audit"` | `lambda_handlers/conversation_audit.py` | True (default) | `"Autom8y/AsanaAudit"` | `("truncated_count",)` |

---

## Implementation Map

### Files

| File | Role in this feature |
|------|---------------------|
| `src/autom8_asana/api/routes/workflows.py` | Route handlers (`GET /api/v1/workflows/`, `POST /{id}/invoke`), request/response models, `_WORKFLOW_CONFIGS` registry, `register_workflow_config()` function. 461 LOC. |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | `WorkflowHandlerConfig` dataclass, `create_workflow_handler()` factory (Lambda path). Config objects here are the dual-use registration units. |
| `src/autom8_asana/api/lifespan.py` | Calls `register_workflow_config()` ×2 at startup (step 12 of 13). Lines 207–240. |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Defines `_config` (`WorkflowHandlerConfig` for `"insights-export"`). Dual-registered as Lambda handler AND API invoke config. |
| `src/autom8_asana/lambda_handlers/conversation_audit.py` | Defines `_config` (`WorkflowHandlerConfig` for `"conversation-audit"`). Same dual-registration pattern. |
| `tests/unit/api/routes/test_workflows.py` | Full API-layer test suite: success, 404, 422 (validation), 401, 422 (pre-flight), dry-run, params-merge, response shape, audit log. 468 LOC. |
| `tests/unit/lambda_handlers/test_workflow_handler.py` | Lambda handler tests. Pinned to `xdist_group("workflow_handler")` per SCAR-W1E-LOADGROUP-001. |

### Key Entry Points

- **Route registration**: `api/main.py` mounts `workflows_router` (from `api/routes/workflows.py`) at `/api/v1/workflows` with PAT auth. See architecture router inventory.
- **Config registration**: `api/lifespan.py:207–240` — startup step 12.
- **`register_workflow_config(config)`** at `api/routes/workflows.py:196` — the public registration function called from lifespan; also used directly in tests to inject test configs.
- **`_get_workflow_factory(workflow_id)`** at `api/routes/workflows.py:205` — internal lookup, returns `None` for unknown IDs.

### Data Flow (API invoke path)

```
HTTP POST /api/v1/workflows/{id}/invoke
  ↓ SlowAPI rate limiter (10/min)
  ↓ FastAPI dependency injection: AuthContextDep, RequestId
  ↓ invoke_workflow() handler
    ↓ _WORKFLOW_CONFIGS.get(workflow_id)  [O(1) dict lookup]
    ↓ EntityScope(entity_ids, dry_run)
    ↓ params merge: default_params ← body.params ← scope.to_params()
    ↓ AsanaClient(token=asana_pat)  [per-request, from AuthContext]
    ↓ DataServiceClient() [async context manager, if required]
    ↓ workflow_factory(asana_client, data_client)  [deferred import inside]
    ↓ _validate_enumerate_execute(workflow, scope, params, request_id, 120s)
      ↓ workflow.validate_async()
      ↓ asyncio.wait_for(enumerate_async + execute_async, timeout=120)
    ↓ emit_metric("WorkflowInvokeCount")
    ↓ SuccessResponse[WorkflowInvokeResponse]
```

### Public API Surface

- `GET /api/v1/workflows/` → `SuccessResponse[list[WorkflowEntry]]`
- `POST /api/v1/workflows/{workflow_id}/invoke` → `SuccessResponse[WorkflowInvokeResponse]`
- `register_workflow_config(config: WorkflowHandlerConfig) -> None` — called from lifespan and test setup.

### Consuming Packages

`api/lifespan.py` is the only production caller of `register_workflow_config()`. Tests call it directly. No other packages import from `api/routes/workflows.py` except for test files and `api/routes/health.py` (via `set_workflow_configs_registered()`).

### Test Coverage

- `tests/unit/api/routes/test_workflows.py` — 8 test classes, ~17 test methods. Covers: success (200), unknown workflow (404), empty/non-numeric/oversized entity_ids (422), missing auth (401), pre-flight validation failure (422), dry_run propagation, params merge, full response envelope shape, audit log emission.
- `tests/unit/lambda_handlers/test_workflow_handler.py` — Lambda handler path. xdist-pinned per SCAR-W1E-LOADGROUP-001.

---

## Boundaries and Failure Modes

### Scope Boundaries (IN)

- HTTP-level invocation of registered workflows: auth, rate limiting, request parsing, timeout enforcement, audit logging, metric emission.
- Registry management: `register_workflow_config()`, `_get_workflow_factory()`.
- Discovery surface: `GET /api/v1/workflows/` lists all registered configs.
- Dry-run flag propagation into `EntityScope.dry_run`.
- Per-request `AsanaClient` construction from authenticated PAT.

### Scope Boundaries (OUT)

- **Actual workflow execution logic** — handled by `WorkflowAction.execute_async()` in `automation/workflows/`. This feature does NOT contain workflow business logic.
- **Lambda execution lifecycle** — `create_workflow_handler()` in `workflow_handler.py` wraps workflows for Lambda; this is the Lambda path, not the API path.
- **Scheduling and polling** — EventBridge triggers and `automation/` polling are outside this surface.
- **Workflow registration decisions** — which workflows to register is decided in `lifespan.py`, not in this feature's code.
- **CloudWatch fleet metrics** — `BridgeFleetHealth` and `emit_success_timestamp()` are emitted only on the Lambda path (`_validate_enumerate_and_run`), NOT on the API path. The API path emits only `WorkflowInvokeCount`.

### Failure Modes

| Failure | HTTP code | Error code | Source |
|---------|-----------|------------|--------|
| Unknown `workflow_id` | 404 | `WORKFLOW_NOT_FOUND` | `_get_workflow_factory()` returns None |
| Empty `entity_ids` | 422 | Pydantic validation | `field_validator` on `WorkflowInvokeRequest` |
| Non-numeric GID in `entity_ids` | 422 | Pydantic validation | `field_validator` |
| More than 100 `entity_ids` | 422 | Pydantic validation | `field_validator` |
| Missing/invalid auth | 401 | (middleware) | `AuthContextDep` / JWTAuthMiddleware |
| Pre-flight validation failure | 422 | `WORKFLOW_VALIDATION_FAILED` | `workflow.validate_async()` returns errors |
| Execution timeout (>120s) | 504 | `WORKFLOW_TIMEOUT` | `asyncio.wait_for` raises `TimeoutError` |
| Rate limit exceeded | 429 | SlowAPI | `@limiter.limit("10/minute")` |
| Workflow configs not registered at startup | 404 | `WORKFLOW_NOT_FOUND` | `_WORKFLOW_CONFIGS` is empty; broad-catch in lifespan degrades to False |

**Startup degradation pattern**: The registration block in `lifespan.py:207–240` is wrapped in a broad-catch. If `insights_export._config` or `conversation_audit._config` fails to import, `workflow_configs_registered` is set to False and `/health/ready` returns 503. All `invoke` calls return 404 until the app restarts successfully.

**xdist isolation (SCAR-W1E-LOADGROUP-001)**: `test_workflow_handler.py` is pinned to `xdist_group("workflow_handler")` via `pytestmark`. Rationale: `AsyncMock(spec=DataServiceClient)` teardown executes inside the event loop spawned by `asyncio.run()` in the production handler path; cross-worker interleaving under `--dist=load` caused worker crashes. The `--dist=loadgroup` strategy is ACTIVE in `pyproject.toml:105` at HEAD.

**Metric asymmetry**: The API path emits `WorkflowInvokeCount` (not `WorkflowExecutionCount`). The Lambda path emits `WorkflowExecutionCount`. These are distinct metrics. An observer monitoring only `WorkflowExecutionCount` will not see API-originated invocations.

**DataServiceClient lifecycle on API path**: `DataServiceClient()` is constructed as an async context manager per-invocation (not pooled). For Lambda, the same pattern applies inside `_execute()`. This means every API-invoked workflow that `requires_data_client=True` opens and closes an HTTP client session on each request.

**Interaction with `EntityScope`**: `scope.to_params()` injects `dry_run` into the params dict. The `entity_ids` are stored on the scope as a tuple, not passed through params — they are consumed by `workflow.enumerate_async(scope)` directly.

**No 202 / async dispatch**: The endpoint executes synchronously under a 120s hard ceiling. There is no queuing, no job ID, no poll-for-status pattern. If a workflow exceeds 120s, the caller receives 504 and the workflow execution is abandoned (no cleanup hook).

**SCAR-CANDIDATE-C (resolved)**: An earlier version of `list_workflows` was missing `response_model` on the route decorator. Fixed at commit `bb97a744`. The fix location is `api/routes/workflows.py` (now present; confirmed in source at `8980bcd7`).

```metadata
domain: feat/workflow-invoke-api
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.92
criteria_grades:
  purpose_and_design_rationale:
    grade: B
    pct: 85
    weight: 0.30
    notes: >
      Problem statement and dual-use config pattern clearly documented from TDD references
      and code comments. ADR-DRY-WORKFLOW-001 rationale present. Synchronous-vs-202 design
      decision articulated. No explicit ADR file found in docs/ for this feature; rationale
      reconstructed from code comments and TDD references.
  conceptual_model:
    grade: A
    pct: 92
    weight: 0.25
    notes: >
      All 5 core types documented with field-level detail. Lifecycle (registration → invocation
      → dispatch → result) mapped. Inter-feature relationships (automation-engine, lambda-handlers,
      lifespan, health) with direction specified. Registry and dual-use config pattern fully
      articulated.
  implementation_map:
    grade: A
    pct: 93
    weight: 0.25
    notes: >
      All 7 implementing files identified with roles. Data flow traced step by step from HTTP
      request to response. Public API surface listed with response types. Test locations and
      coverage described. Key entry points (route registration, lifespan registration)
      cross-referenced with architecture.md line-level evidence.
  boundaries_and_failure_modes:
    grade: A
    pct: 92
    weight: 0.20
    notes: >
      Explicit IN/OUT scope statements. All 8 failure modes tabulated with HTTP codes and
      error codes sourced from production code. SCAR-W1E-LOADGROUP-001 xdist isolation documented.
      Metric asymmetry (API vs Lambda paths), DataServiceClient lifecycle, no-202 constraint,
      and startup degradation pattern all documented. SCAR-CANDIDATE-C resolution noted.
overall_grade: A
overall_pct: 91
notes: >
  Feature fully observable from source code and test coverage. Primary gap: no ADR document
  found in docs/ for this feature; design rationale was reconstructed from code comments
  (TDD-ENTITY-SCOPE-001 refs, ADR-DRY-WORKFLOW-001 in workflow_handler.py header) rather than
  a first-class decision record. Grade B on Purpose criterion reflects this evidential gap.
  Two registered workflows documented at source_hash 8980bcd7: insights-export and
  conversation-audit.
```
