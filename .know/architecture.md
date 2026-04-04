---
domain: architecture
generated_at: "2026-04-04T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "55aaab5"
confidence: 0.85
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "ccac1bdf21a076abac37f960cd0d2210bee78a023d780c7374cb6d5c087c9c5b"
---

# Codebase Architecture

## Package Structure

**Language**: Python 3.12. Build system: `hatchling`. Dependency manager: `uv`. Primary source root: `src/autom8_asana/` (476 files). Secondary CLI entrypoint: `src/autom8_query_cli.py`.

The package is `autom8y-asana` (pip name) / `autom8_asana` (import name), described as "Async-first Asana API client extracted from autom8". It publishes both a Python SDK (importable library) and a FastAPI service deployable as ECS or Lambda.

### Top-Level Sub-packages (23 packages)

| Package | Purpose |
|---|---|
| `_defaults/` | Platform-specific default providers (auth, cache, log, observability) for standalone SDK use |
| `api/` | FastAPI application: factory, middleware, routes, lifespan, preload subsystem |
| `auth/` | Authentication adapters: JWT validator, bot PAT, dual-mode detection, service token |
| `automation/` | Rule-based automation engine, polling scheduler, workflow registry |
| `batch/` | Asana Batch API client and models |
| `cache/` | Multi-tier cache subsystem (backends, policies, integration, models, providers) |
| `clients/` | Per-resource Asana API clients (tasks, projects, sections, users, etc.) |
| `core/` | Shared utilities: types, exceptions, registries, concurrency, timing, string utils |
| `dataframes/` | Polars DataFrame layer: builders, extractors, schemas, resolvers, views |
| `exceptions.py` | Public SDK exception hierarchy |
| `lambda_handlers/` | AWS Lambda entry points (cache warmer, workflow handler, push orchestrator, etc.) |
| `lifecycle/` | 4-phase lifecycle pipeline for entity creation/transition orchestration |
| `metrics/` | Business metric definitions, expression DSL, computation, registry |
| `models/` | Pydantic v2 domain models (Asana primitives + business domain hierarchy) |
| `observability/` | Correlation context, decorators, OTel integration wiring |
| `patterns/` | Reusable async method patterns and error classification utilities |
| `persistence/` | SaveSession (Unit of Work), action execution, cascade, dependency graph |
| `protocols/` | Protocol (interface) definitions for DI boundaries |
| `query/` | Composable query engine: compiler, predicates, joins, aggregation, saved queries |
| `reconciliation/` | Payment reconciliation pipeline: processor, executor, engine |
| `resolution/` | Field resolution strategies, write registry, budget, context |
| `search/` | Full-text search service over DataFrames |
| `services/` | Application services: entity service, resolver, dataframe service, intake services |
| `settings.py` | Unified Pydantic Settings — all environment variable binding |
| `transport/` | HTTP transport: `AsanaHttpClient` wrapping `autom8y-http` platform SDK |

### File counts by package (approximate)

- `cache/` — ~55 files (most complex sub-package)
- `dataframes/` — ~55 files
- `models/` — ~50 files
- `api/` — ~40 files (routes + middleware + preload)
- `clients/` — ~35 files
- `automation/` — ~30 files
- `lifecycle/` — ~16 files
- `persistence/` — ~20 files
- `services/` — ~22 files
- `query/` — ~17 files

---

## Layer Boundaries

The codebase follows a descending dependency hierarchy. Cross-layer imports go top-to-bottom only; bottom layers do not import from top layers.

```
+-------------------------------------------------------------+
|  ENTRY POINTS                                               |
|  entrypoint.py (ECS/Lambda dual-mode)                       |
|  api/main.py + api/lifespan.py (FastAPI)                    |
|  lambda_handlers/*.py (AWS Lambda)                          |
|  src/autom8_query_cli.py (CLI)                              |
+---------------------------+---------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  API LAYER (api/)                                           |
|  Routes -> Services (via FastAPI Depends)                   |
|  auth/, api/dependencies.py (DI + auth resolution)          |
+---------------------------+---------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  SERVICES LAYER (services/)                                 |
|  DataFrameService, EntityService, ResolverService,          |
|  IntakeCreateService, IntakeResolveService, QueryService    |
|  Orchestrates: clients/ + dataframes/ + cache/ + lifecycle/ |
+---------------------------+---------------------------------+
                            |
                            v
+--------------+----------------+----------------------------+
| DOMAIN LOGIC |  DOMAIN LOGIC  |  DOMAIN LOGIC              |
| lifecycle/   |  automation/   |  query/ + reconciliation/  |
| (4-phase     |  (rule engine, |  (query engine,            |
|  pipeline)   |   workflows)   |   reconciliation pipeline) |
+------+-------+--------+------+--------+-------------------+
       |                 |               |
       v                 v               v
+-------------------------------------------------------------+
|  CLIENT LAYER (clients/)                                    |
|  BaseClient -> per-resource clients (tasks, projects, etc.) |
|  clients/data/ (autom8_data service client)                 |
+---------------------------+---------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  TRANSPORT LAYER (transport/)                               |
|  AsanaHttpClient wraps autom8y-http Autom8yHttpClient       |
|  Adaptive semaphore, config translator, response handler    |
+---------------------------+---------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  PLATFORM SDK LAYER (external packages via CodeArtifact)    |
|  autom8y-http, autom8y-log, autom8y-auth, autom8y-cache    |
|  autom8y-config, autom8y-core, autom8y-telemetry            |
|  autom8y-events, autom8y-interop                            |
+-------------------------------------------------------------+
```

**Cross-cutting packages** (used at all levels):
- `core/` — shared types, exceptions, utilities
- `models/` — Pydantic data models consumed across layers
- `protocols/` — Protocol interfaces (DI boundaries between layers)
- `cache/` — Cache subsystem used by clients, services, and lifecycle
- `observability/` — OTel tracing decorators used across layers
- `settings.py` — Singleton settings; consulted at config/startup

**Known boundary exceptions** (documented in code):
- `src/autom8_asana/client.py` and `config.py` use delayed imports (E402) to avoid circular import between client facade and per-resource clients
- `api/dependencies.py` uses delayed imports for same reason
- `services/resolver.py` and `services/universal_strategy.py` use delayed imports

---

## Entry Points and API Surface

### Runtime Entry Points

| Entry Point | File | Mode |
|---|---|---|
| ECS uvicorn server | `src/autom8_asana/entrypoint.py:run_ecs_mode()` | ECS |
| Lambda generic handler | `src/autom8_asana/entrypoint.py:run_lambda_mode()` | Lambda |
| FastAPI app factory | `src/autom8_asana/api/main.py:create_app()` | ECS |
| CLI query tool | `src/autom8_query_cli.py:main()` | CLI |
| Automation polling CLI | `src/autom8_asana/automation/polling/cli.py` | CLI |
| Metrics CLI | `src/autom8_asana/metrics/__main__.py` | CLI |
| Query REPL | `src/autom8_asana/query/__main__.py` | CLI |

**Dual-mode detection**: `entrypoint.py` checks `AWS_LAMBDA_RUNTIME_API` environment variable. Absent = ECS (starts uvicorn). Present = Lambda (invokes `awslambdaric` with handler path from `sys.argv[1]`).

### Lambda Handlers (12 handlers in `lambda_handlers/`)

| Handler | File | Purpose |
|---|---|---|
| `cache_warmer.handler` | `lambda_handlers/cache_warmer.py` | Pre-warm S3/Redis DataFrame cache |
| `cache_invalidate.handler` | `lambda_handlers/cache_invalidate.py` | Invalidate stale cache entries |
| `workflow_handler.handler` | `lambda_handlers/workflow_handler.py` | Execute automation workflows |
| `push_orchestrator.handler` | `lambda_handlers/push_orchestrator.py` | Orchestrate data push operations |
| `insights_export.handler` | `lambda_handlers/insights_export.py` | Export insights to external system |
| `payment_reconciliation.handler` | `lambda_handlers/payment_reconciliation.py` | Run payment reconciliation workflow |
| `reconciliation_runner.handler` | `lambda_handlers/reconciliation_runner.py` | Run general reconciliation |
| `story_warmer.handler` | `lambda_handlers/story_warmer.py` | Warm Asana stories cache |
| `conversation_audit.handler` | `lambda_handlers/conversation_audit.py` | Audit conversation records |
| `checkpoint.handler` | `lambda_handlers/checkpoint.py` | Checkpoint-based resume support |
| `cloudwatch.handler` | `lambda_handlers/cloudwatch.py` | CloudWatch metric emission |
| `pipeline_stage_aggregator.handler` | `lambda_handlers/pipeline_stage_aggregator.py` | Aggregate pipeline stage data |
| `timeout.handler` | `lambda_handlers/timeout.py` | Lambda timeout detection |

### FastAPI HTTP API Surface

Routes registered in `api/main.py:create_app()`, defined in `api/routes/`:

| Router | Tag | Auth | Representative Paths |
|---|---|---|---|
| `health_router` | health | None | `GET /health`, `GET /ready`, `GET /health/deps` |
| `users_router` | users | PAT Bearer | `GET /api/v1/users/me`, `GET /api/v1/users/{gid}` |
| `workspaces_router` | workspaces | PAT Bearer | `GET /api/v1/workspaces` |
| `dataframes_router` | dataframes | PAT Bearer | `GET /api/v1/dataframes/schemas` |
| `tasks_router` | tasks | PAT Bearer | `/api/v1/tasks/*` (CRUD, subtasks, dependents) |
| `projects_router` | projects | PAT Bearer | `/api/v1/projects/*` (CRUD, sections, members) |
| `sections_router` | sections | PAT Bearer | `/api/v1/sections/*` (CRUD, task add, reorder) |
| `webhooks_router` | webhooks | URL token | `POST /webhooks/inbound` |
| `resolver_router` | resolver | S2S JWT | `POST /v1/resolve/{entity_type}` |
| `intake_resolve_router` | intake-resolve | S2S JWT | `POST /v1/resolve/business` |
| `intake_custom_fields_router` | intake-custom-fields | S2S JWT | `/v1/intake/custom-fields/*` |
| `intake_create_router` | intake-create | S2S JWT | `POST /v1/intake/create` |
| `query_router` | query (internal) | S2S JWT | `POST /v1/query/{entity_type}/rows` |
| `query_introspection_router` | query | S2S JWT | `GET /v1/query/schemas` |
| `admin_router` | admin | S2S JWT | `/v1/admin/*` |
| `internal_router` | internal | S2S JWT | `/v1/internal/*` |
| `entity_write_router` | entity-write | S2S JWT | `POST /v1/entity-write` |
| `workflows_router` | workflows | PAT Bearer | `GET /api/v1/workflows` |
| `section_timelines_router` | offers | PAT Bearer | Section timeline endpoints |
| `matching_router` | matching | S2S JWT | `POST /v1/matching/query` |

Three auth modes: `PersonalAccessToken` (PAT Bearer), `ServiceJWT` (S2S JWT), `WebhookToken` (URL query parameter).

### SDK Public API (via `__init__.py`)

Top-level exports in `src/autom8_asana/__init__.py`:
- `AsanaClient` — primary facade (`src/autom8_asana/client.py`)
- `AsanaConfig`, `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`
- All exception types (`AsanaError`, `AuthenticationError`, etc.)
- All Pydantic model types (`Task`, `Project`, `Section`, `User`, etc.)
- Protocol types (`AuthProvider`, `CacheProvider`, `ItemLoader`, `LogProvider`, `ObservabilityHook`)
- Auth providers (`EnvAuthProvider`, `SecretsManagerAuthProvider`)
- Batch API (`BatchClient`, `BatchRequest`, `BatchResult`, `BatchSummary`)
- DataFrame layer (lazy-loaded via `__getattr__` to avoid pulling polars for core-only consumers)

---

## Key Abstractions

### 1. `AsanaClient` (SDK Facade)
**File**: `src/autom8_asana/client.py`

The root SDK object. Accepts optional `token`, `workspace_gid`, `auth_provider`, `cache_provider`, `log_provider`, `observability_hook`. Composes per-resource clients (`TasksClient`, `ProjectsClient`, etc.), `BatchClient`, `UnifiedTaskStore`, `AutomationEngine`, `SearchService`, `SaveSession`.

### 2. `AsanaResource` (Base Model)
**File**: `src/autom8_asana/models/base.py`

Pydantic v2 BaseModel with `extra="ignore"` (forward-compat), `populate_by_name=True`, `str_strip_whitespace=True`. All resource models inherit from this. Key fields: `gid: str`, `resource_type: str | None`.

### 3. `BaseClient`
**File**: `src/autom8_asana/clients/base.py`

Common base for all per-resource clients. Holds `_http: AsanaHttpClient`, `_config: AsanaConfig`, `_auth: AuthProvider`, `_cache: CacheProvider | None`, `_log: LogProvider | None`. Provides cache check-before-HTTP and store-on-miss helpers.

### 4. `AsanaHttpClient`
**File**: `src/autom8_asana/transport/asana_http.py`

Thin wrapper around `autom8y-http.Autom8yHttpClient`. Handles Asana-specific response unwrapping (`data.data` envelope), error mapping to domain exceptions. Composes `AsyncAdaptiveSemaphore` (AIMD algorithm for concurrency control) and `AsanaResponseHandler`.

### 5. Protocol Interfaces (`protocols/`)
**Files**: `src/autom8_asana/protocols/*.py`

DI boundary interfaces using Python Protocol (structural typing): `AuthProvider`, `CacheProvider`, `DataFrameCacheProtocol`, `DataFrameProvider`, `ItemLoader`, `LogProvider`, `MetricsEmitter`, `ObservabilityHook`.

### 6. `SaveSession` (Unit of Work)
**File**: `src/autom8_asana/persistence/session.py`

Implements ADR-0035 (Unit of Work Pattern). Thread-safe via RLock. State machine: `OPEN -> COMMITTED`. Composes `ActionBuilder`, `ActionExecutor`, `DependencyGraph`, `CacheInvalidator`, `HealingManager`, `SavePipeline`, `ChangeTracker`.

### 7. `EntityType` (Business Domain Enum)
**File**: `src/autom8_asana/core/types.py`

Canonical enum: `BUSINESS` (root), `UNIT` (composite), `CONTACT`, `OFFER`, `PROCESS`, `LOCATION`, `HOURS` (leaves), `*_HOLDER` variants (containers), `UNKNOWN` (fallback). Extracted to `core/` to break circular dependency.

### 8. `UnifiedTaskStore`
**File**: `src/autom8_asana/cache/providers/unified.py`

Per TDD-UNIFIED-CACHE-001: Single source of truth for task data. Composes `CacheProvider`, `HierarchyIndex`, and `FreshnessCoordinator`.

### 9. `DataFrameBuilder` (abstract)
**File**: `src/autom8_asana/dataframes/builders/base.py`

Abstract base for schema-driven Polars DataFrame construction. Manages extractor lifecycle, lazy/eager evaluation, bounded concurrency via `gather_with_limit()`.

### 10. `QueryEngine`
**File**: `src/autom8_asana/query/engine.py`

Composable query engine. Accepts `DataFrameProvider` protocol. Executes: schema validation -> predicate compilation -> section scoping -> DataFrame filtering -> optional joins -> aggregation. Decorated with `@trace_computation`.

### 11. `LifecycleEngine`
**File**: `src/autom8_asana/lifecycle/engine.py`

4-phase pipeline orchestrator: `Create -> Configure -> Actions -> Wire`. Routes DNC transitions: create_new, reopen, deferred. Fail-forward design.

### 12. `CacheBackendBase`
**File**: `src/autom8_asana/cache/backends/base.py`

Template method base for S3 and Redis backends. Shared resilience scaffolding (degraded mode, timing, metrics, error handling). Delegates to abstract `_do_*` methods.

### 13. `Settings` (Pydantic Settings)
**File**: `src/autom8_asana/settings.py`

Singleton via `get_settings()` / `reset_settings()`. Centralizes all environment variable binding. Sub-settings: `asana`, `cache`, `runtime`, `pacing`, `s3`, `redis`, `cloudwatch`.

---

## Data Flow

### Flow 1: Inbound API Request (PAT mode — e.g., GET tasks)

```
HTTP Request
  -> RequestIDMiddleware (assigns X-Request-ID)
  -> RequestLoggingMiddleware (structured log)
  -> SlowAPIMiddleware (rate limiting)
  -> IdempotencyMiddleware (RFC 8791 store-and-replay)
  -> Route handler (api/routes/tasks.py)
  -> get_auth_context() dependency (api/dependencies.py)
       -> detect_token_type() -> PAT mode
       -> Extract Bearer token from Authorization header
  -> get_client() dependency
       -> AsanaClient(token=pat, cache_provider=app.state.cache_provider)
  -> TaskService or direct client call
  -> AsanaClient.tasks.get(gid)
  -> BaseClient._cache.get() [cache check]
       -> HIT: return cached data
       -> MISS: AsanaHttpClient.get("/tasks/{gid}")
            -> Autom8yHttpClient (platform SDK)
            -> Asana API
            -> AsanaResponseHandler.unwrap() (data.data envelope)
            -> pydantic model parse (Task.model_validate)
       -> store in cache
  -> SuccessResponse[Task] returned as JSON
```

### Flow 2: DataFrame Request (S2S mode — e.g., POST /v1/query/{entity_type}/rows)

```
HTTP Request (S2S JWT in Authorization header)
  -> Middleware stack
  -> Query route handler (api/routes/query.py)
  -> get_auth_context() -> S2S mode
       -> autom8y-auth JWT validation (JWKS endpoint)
       -> get_bot_pat() (retrieve bot PAT from SecretsManager)
  -> QueryService.execute_rows(request, client)
  -> QueryEngine.query_rows(RowsRequest, dataframe_provider)
  -> DataFrameProvider.get_dataframe(entity_type)
       -> UnifiedTaskStore or DataFrameCacheIntegration
       -> Cache hit: return cached Polars DataFrame
       -> Cache miss: DataFrameBuilder.build_async()
            -> AsanaClient.tasks (paginated fetch)
            -> Extractor.extract(task) per task row
            -> coerce_rows_to_schema() -> pl.DataFrame
       -> Store in cache (S3 + memory tiers)
  -> PredicateCompiler.compile(predicates) -> Polars expressions
  -> df.filter(compiled_predicates)
  -> Optional join (execute_join)
  -> RowsResponse with serialized records
```

### Flow 3: Entity Write (SaveSession)

```
API call to entity_write_router or direct SDK use
  -> service constructs SaveSession(client)
  -> session.update(entity, field=value) [ChangeTracker records delta]
  -> session.commit()
       -> ActionBuilder.build() -> list[PlannedOperation]
       -> DependencyGraph.order() -> topological sort
       -> ActionExecutor.execute_all(ordered_actions)
            -> Per action type: tasks.update(), tasks.add_project(), etc.
            -> On success: ChangeTracker records result
       -> CacheInvalidator.invalidate(affected_gids)
       -> HealingManager.heal_if_needed(entities)
       -> AutomationEngine.evaluate_async(save_result, client)
            -> Rule.evaluate(context) per registered rule
  -> SaveResult returned
```

### Flow 4: Lambda Cache Warmer

```
Lambda invocation (scheduled EventBridge or manual)
  -> entrypoint.py detects AWS_LAMBDA_RUNTIME_API -> Lambda mode
  -> awslambdaric dispatches to lambda_handlers/cache_warmer.handler
  -> resolve_secret_from_env() fetches ASANA_PAT from SecretsManager
  -> AsanaClient(token=pat, cache_provider=S3CacheProvider)
  -> For each entity_type (unit, offer, business, etc.):
       -> ProgressiveProjectBuilder.build_async(project_gid)
            -> Paginated task fetch
            -> Extractor.extract() per task
            -> pl.DataFrame
       -> S3CacheProvider.set(entity_type_key, serialized_df)
  -> Emit CloudWatch metrics (hit rate, entry count, duration)
  -> Return WarmResponse (success/failure per entity_type)
```

### Flow 5: Webhook Inbound

```
POST /webhooks/inbound?token=<secret>
  -> WebhookToken auth: timing-safe compare against ASANA_WEBHOOK_INBOUND_TOKEN
  -> webhooks route handler
  -> Background task queued (FastAPI BackgroundTasks)
       -> CacheInvalidator.invalidate(task_gid)
       -> Lifecycle dispatch if configured
  -> Immediate 200 response (prevent Asana retry)
```

---

## Knowledge Gaps

1. **`clients/data/` sub-package**: The autom8_data service client was read at a high level. Exact endpoint contracts between autom8_asana and autom8_data were not fully explored.
2. **`models/business/` hierarchy**: The business domain model types were identified but full Pydantic field schemas and inter-model relationships were not read in depth.
3. **`cache/integration/` sub-package** (~16 files): Integration adapters were identified but not read individually.
4. **`api/preload/`**: The progressive cache preload subsystem was referenced but not read.
5. **`resolution/`** strategies: `resolution/strategies.py` was not read; only module names are known.
6. **`metrics/` DSL**: The metric expression DSL was identified but not read.
7. **External platform SDKs**: `autom8y-auth`, `autom8y-cache`, `autom8y-config`, `autom8y-core`, `autom8y-telemetry` APIs are known only from usage in this codebase, not from their source.
