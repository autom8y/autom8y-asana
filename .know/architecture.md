---
domain: architecture
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "ccac1bdf21a076abac37f960cd0d2210bee78a023d780c7374cb6d5c087c9c5b"
---

# Codebase Architecture

**Source hash**: `acff02ab` | **Evaluation date**: 2026-04-24

## Package Structure

The `autom8_asana` package lives at `src/autom8_asana/` and contains 478 Python source files across 40+ sub-packages. The project is a FastAPI service that also exposes Lambda handlers and an SDK facade, deployed as a dual-mode container (ECS via uvicorn, or Lambda via awslambdaric).

### Top-Level Packages and Purpose

| Package | Files | Purpose | Category |
|---|---|---|---|
| `api/` | ~50 | FastAPI app factory, routers, middleware, DI, lifespan | API surface (hub) |
| `api/routes/` | 25 | Route handlers and co-located request/response models | API surface |
| `api/middleware/` | 3 | Idempotency middleware, core middleware utilities | API infrastructure |
| `api/preload/` | 4 | Progressive/legacy DataFrame cache preload at startup | Startup |
| `automation/` | ~20 | Automation engine, event emitter, workflow base classes | Domain logic |
| `automation/events/` | 6 | Event envelope, emitter, transport, rule evaluation | Events |
| `automation/polling/` | 7 | Polling scheduler, config loader, action executor, trigger evaluator | Background workers |
| `automation/workflows/` | ~12 | Concrete workflow implementations (insights, payment recon, conversation audit) | Domain workflows |
| `batch/` | 3 | Batch API client and models for Asana batch requests | Infrastructure |
| `cache/` | ~45 | Tiered cache subsystem: backends, policies, models, integration adapters | Infrastructure (hub) |
| `cache/backends/` | 5 | `CacheBackendBase` + Memory, Redis, S3 concrete backends | Cache leaf |
| `cache/dataframe/` | 8 | DataFrame-specific cache coordination, circuit breaker, factory | Cache integration |
| `cache/integration/` | 15 | High-level adapters bridging SDK cache to specific subsystems | Cache hub |
| `cache/models/` | 11 | `CacheEntry`, `CacheSettings`, versioning, metrics, mutation events | Cache data types |
| `cache/policies/` | 5 | Freshness policy, staleness, hierarchy coalescer | Cache policies |
| `cache/providers/` | 2 | Tiered and unified provider aggregators | Cache providers |
| `clients/` | ~20 | Per-resource Asana API clients (tasks, projects, sections, etc.) | SDK clients |
| `clients/data/` | 10 | DataService cross-service client with retry, PII, normalize | External client |
| `core/` | 16 | Foundation types, registries, error constants, utilities | Core (leaf) |
| `dataframes/` | ~45 | DataFrame extraction pipeline: builders, extractors, schemas, resolver, views | Domain (hub) |
| `dataframes/builders/` | 10 | `DataFrameBuilder` ABC and concrete section/progressive builders | DataFrame build |
| `dataframes/extractors/` | 10 | Per-entity-type field extractors (`BaseExtractor` ABC) | DataFrame extract |
| `dataframes/models/` | 4 | `SchemaRegistry`, schema defs, typed row models (e.g., `BusinessRow`) | DataFrame schema |
| `dataframes/resolver/` | 7 | Custom field resolution protocol and default/cascading implementations | DataFrame resolve |
| `dataframes/schemas/` | 9 | Per-entity schema constant definitions (`BUSINESS_SCHEMA`, etc.) | DataFrame schema |
| `dataframes/views/` | 4 | `DataFrameView`, `CascadeView`, custom field utils | DataFrame views |
| `lambda_handlers/` | 12 | Lambda entry points (cache warmer, workflow handler, push orchestrator, etc.) | Entry points |
| `lifecycle/` | 14 | Business entity lifecycle engine: creation, completion, observation, wiring | Domain logic |
| `metrics/` | 8 | Business metric definitions, expression DSL, compute engine | Analytics |
| `models/` | ~55 | Pydantic domain models: Asana API models + business model hierarchy | Data models |
| `models/business/` | ~30 | `Business`, `Unit`, `Contact`, `Offer`, `Process`; holder classes; detection tiers | Core domain models |
| `models/business/detection/` | 7 | 4-tier entity type detection facade | Detection |
| `models/business/matching/` | 6 | Fuzzy matching engine and comparators | Matching |
| `observability/` | 4 | OTel context propagation, correlation, decorators | Infrastructure |
| `patterns/` | 2 | Async method utilities, error classification | Utilities |
| `persistence/` | 16 | `SavePipeline`, `SaveSession`, action executor, dependency graph, holder ensurer | Write pipeline |
| `protocols/` | 9 | Protocol interfaces: `AuthProvider`, `CacheProvider`, `DataFrameProvider`, etc. | Contracts (leaf) |
| `query/` | 15 | Composable query engine, compiler, join, aggregator, temporal | Query system |
| `reconciliation/` | 5 | Payment/data reconciliation engine, report generation | Domain logic |
| `resolution/` | 7 | Entity resolution strategies, context, budget, `EntityWriteRegistry` | Resolution |
| `search/` | 3 | Full-text search service | Domain |
| `services/` | 22 | Application service layer: entity, task, dataframe, resolver, intake services | Service layer (hub) |
| `transport/` | 5 | `AsanaHttpClient`, adaptive semaphore, response handler, config translator | HTTP transport |
| `_defaults/` | 4 | Default implementations: auth, cache, log, observability providers | Defaults |

**Hub packages** (many consumers): `api/`, `cache/`, `dataframes/`, `services/`, `core/`
**Leaf packages** (few or no internal imports): `protocols/`, `core/types.py`, `core/errors.py`, `models/base.py`, `transport/`

## Layer Boundaries

The project maps to a 5-layer model in Python terms:

```
Layer 1: API surface (api/, api/routes/, entrypoint.py)
Layer 2: Services (services/)
Layer 3: Domain logic (lifecycle/, automation/, persistence/, resolution/, query/, reconciliation/, dataframes/)
Layer 4: SDK clients + models (client.py, clients/, models/)
Layer 5: Infrastructure (cache/, transport/, core/, protocols/, _defaults/)
```

### Import Graph Direction (observed)

**Layer 1 → 2/3/4/5**: `api/routes/dataframes.py` imports `services/dataframe_service.py`, `dataframes/schemas/`, `api/dependencies.py`. `api/routes/resolver.py` imports `services/resolver.py`. `api/dependencies.py` imports from `clients/`, `services/`, `cache/`, `auth/`, `resolution/`. `api/lifespan.py` imports `cache/`, `dataframes/`, `resolution/`, `lifecycle/`, `core/`.

**Layer 2 → 3/4/5**: `services/resolver.py` imports `core/entity_registry.py`, `dataframes/`, `services/resolution_result.py`. `services/dataframe_service.py` uses `dataframes/models/registry.py` (`SchemaRegistry`). `services/entity_service.py` imports from `services/entity_context.py`.

**Layer 3 → 4/5**: `lifecycle/engine.py` imports `persistence/`, `resolution/`, `core/`. `automation/workflows/base.py` is leaf within automation; concrete workflows import from `clients/`. `dataframes/builders/base.py` imports `dataframes/extractors/`. `persistence/pipeline.py` imports `batch/`, `persistence/executor/`, `persistence/models`. `resolution/strategies.py` imports `models/business/`, `resolution/result.py`.

**Layer 4 → 5**: `client.py` (AsanaClient facade) imports `clients/`, `cache/integration/`, `transport/`, `_defaults/`, `protocols/`. `models/business/business.py` imports `models/business/base.py`, `models/business/contact.py`.

**Layer 5 leaf**: `protocols/` defines Protocol interfaces only. `core/types.py` defines `EntityType` enum. `core/errors.py` defines error constants. `transport/asana_http.py` imports from `errors.py`, `transport/` siblings, `protocols/` (TYPE_CHECKING only).

### Circular Dependency Avoidance Patterns

1. **`TYPE_CHECKING` guards**: `client.py` uses `if TYPE_CHECKING` to import `AutomationEngine`, `SearchService`, protocol types.
2. **Lazy imports inside functions**: `api/dependencies.py` lazily imports `jwt_validator`, `TaskService`, `SectionService` inside function bodies.
3. **Extracted `EntityType` to `core/types.py`**: Broke `core ↔ models` bidirectional dependency.
4. **`_bind_entity_types()` after module load**: `core/entity_registry.py` uses `object.__setattr__` on frozen dataclasses to avoid circular imports from `core` → `models`.

No circular imports observed between packages; `TYPE_CHECKING` + deferred-import patterns are the enforcement mechanism.

## Entry Points and API Surface

### Primary Entry Point

`src/autom8_asana/entrypoint.py` — Dual-mode dispatcher:
- `main()` reads `AWS_LAMBDA_RUNTIME_API` env var
- **ECS mode** (var absent): `run_ecs_mode()` → bootstraps business models → starts `uvicorn` serving `autom8_asana.api.main:create_app` (factory pattern)
- **Lambda mode** (var present): `run_lambda_mode(handler)` → invokes `awslambdaric` with the handler path from `sys.argv[1]`

### FastAPI Application Factory

`src/autom8_asana/api/main.py` — `create_app() -> FastAPI` called by uvicorn with `factory=True`. Uses `create_fleet_app()` (platform middleware). Registers routers, lifespan, middleware, custom OpenAPI spec enrichment.

### Lifespan Startup Sequence (`api/lifespan.py`)

1. Bootstrap business model registry (`models/business/_bootstrap.py`)
2. Configure structured logging
3. Activate OTEL httpx instrumentation
4. Create shared `CacheProvider` → `app.state.cache_provider`
5. Create token-keyed `ClientPool` → `app.state.client_pool`
6. Entity resolver startup discovery (workspace project GID scan)
7. Cross-registry consistency validation
8. Initialize `DataFrameCache` → `app.state.dataframe_cache`
9. Register schema providers with SDK
10. Initialize `MutationInvalidator` → `app.state.mutation_invalidator`
11. Build `EntityWriteRegistry` → `app.state.entity_write_registry`
12. Register workflow configs for API invocation
13. Validate cascade warm-up ordering
14. Start background `asyncio.Task` for progressive DataFrame cache warming → `app.state.cache_warming_task`

Shutdown: cancel cache warming task, close `ClientPool`, close `connection_registry`.

### API Route Groups (22 routers)

| Router | Prefix | Auth | Tags |
|---|---|---|---|
| `health_router` | `/health`, `/ready`, `/health/deps` | None | `health` |
| `users_router` | `/api/v1/users` | PAT Bearer | `users` |
| `workspaces_router` | `/api/v1/workspaces` | PAT Bearer | `workspaces` |
| `dataframes_router` | `/api/v1/dataframes` | PAT Bearer | `dataframes` |
| `tasks_router` | `/api/v1/tasks` | PAT Bearer | `tasks` |
| `projects_router` | `/api/v1/projects` | PAT Bearer | `projects` |
| `sections_router` | `/api/v1/sections` | PAT Bearer | `sections` |
| `section_timelines_router` | `/api/v1/section-timelines` | PAT Bearer | `offers` |
| `webhooks_router` | `/api/v1/webhooks` | URL token (`?token=`) | `webhooks` |
| `workflows_router` | `/api/v1/workflows` | PAT Bearer | `workflows` |
| `intake_resolve_router` | `/v1/intake/resolve/...` | S2S JWT | `intake-resolve` |
| `resolver_router` | `/v1/resolve/{entity_type}` | S2S JWT | `resolver` |
| `query_introspection_router` | `/v1/query/...` GET | S2S JWT | `query` |
| `fleet_query_router_v1` | `/v1/query/entities` | S2S JWT | `query` |
| `fleet_query_router_api_v1` | `/api/v1/query/entities` | S2S JWT | `query` |
| `query_router` | `/v1/query/{entity_type}` | S2S JWT | `query` |
| `admin_router` | `/v1/admin` | S2S JWT | `admin` |
| `internal_router` | `/v1/internal` | S2S JWT | `internal` |
| `entity_write_router` | `/v1/entity-write` | S2S JWT | `entity-write` |
| `intake_custom_fields_router` | `/v1/intake/custom-fields` | S2S JWT | `intake-custom-fields` |
| `intake_create_router` | `/v1/intake/create` | S2S JWT | `intake-create` |
| `matching_router` | `/v1/matching` | S2S JWT | `matching` |

**Auth model (dual-mode)**:
- PAT Bearer: user's Asana Personal Access Token passed through to Asana API
- S2S JWT: service JWT validated against JWKS; bot PAT used for downstream Asana calls
- URL token: `ASANA_WEBHOOK_INBOUND_TOKEN` env var, timing-safe comparison

### Lambda Entry Points (`src/autom8_asana/lambda_handlers/`)

| Handler module | Purpose |
|---|---|
| `cache_warmer.py` | Pre-warm entity DataFrame caches from S3 |
| `cache_invalidate.py` | Invalidate stale cache entries on mutation events |
| `workflow_handler.py` | Run automation workflows |
| `push_orchestrator.py` | Orchestrate push operations across entities |
| `reconciliation_runner.py` | Payment reconciliation pipeline |
| `insights_export.py` | Export Asana insights data |
| `conversation_audit.py` | Audit conversation entities |
| `pipeline_stage_aggregator.py` | Aggregate process pipeline stage data |
| `story_warmer.py` | Pre-warm story cache |
| `checkpoint.py` | Checkpoint / incremental state save |
| `cloudwatch.py` | CloudWatch metrics emission |
| `timeout.py` | Timeout handler |

### CLI Surface

`pyproject.toml` registers one console script: `autom8-query = "autom8_query_cli:main"` at `src/autom8_query_cli.py`.

Python `-m` entry points:
- `python -m autom8_asana.query` — development query tool
- `python -m autom8_asana.metrics` — metrics compute CLI
- `src/autom8_asana/automation/polling/cli.py` — polling scheduler CLI

### Key DI Dependencies (`api/dependencies.py`)

| Dependency | Factory | Lifecycle |
|---|---|---|
| `AsanaClientDualMode` | `get_asana_client_from_context` | Per-request (from `ClientPool`) |
| `AuthContextDep` | `get_auth_context` | Per-request |
| `EntityServiceDep` | `get_entity_service` | Singleton on `app.state` |
| `TaskServiceDep` | `get_task_service` | Per-request |
| `SectionServiceDep` | `get_section_service` | Per-request |
| `DataFrameServiceDep` | `get_dataframe_service` | Per-request (stateless) |
| `MutationInvalidatorDep` | `get_mutation_invalidator` | Singleton on `app.state` |
| `DataFrameCacheDep` | `get_dataframe_cache` | Singleton on `app.state` |
| `DataServiceClientDep` | `get_data_service_client` | Lazy singleton on `app.state` |
| `EntityWriteRegistryDep` | `get_entity_write_registry` | Singleton on `app.state` |

## Key Abstractions

### 1. `AsanaClient` (`src/autom8_asana/client.py`)

The SDK facade. Accepts `token`, `auth_provider`, `cache_provider`, `log_provider`, `config`, `observability_hook`. Composed of per-resource sub-clients: `TasksClient`, `ProjectsClient`, `SectionsClient`, `UsersClient`, `WorkspacesClient`, `StoriesClient`, `AttachmentsClient`, `WebhooksClient`, `PortfoliosClient`, `GoalsClient`, `TagsClient`, `TeamsClient`, `CustomFieldsClient`. Also exposes `BatchClient`, `AsanaHttpClient`, `SaveSession`.

### 2. `EntityDescriptor` + `EntityRegistry` (`src/autom8_asana/core/entity_registry.py`)

Single source of truth for 30+ entity types. `EntityDescriptor` is a frozen dataclass capturing: name, pascal_name, EntityType, category (ROOT/COMPOSITE/LEAF/HOLDER/OBSERVATION), Asana project GID, model class path, DataFrame schema/extractor/row model paths, cache TTL, warm priority, join keys, key columns.

`EntityRegistry` is a module-level singleton. Used throughout: DataFrame pipeline, entity detection, resolver, cache warming, query engine.

**Entity hierarchy**:
- ROOT: `business`
- COMPOSITE: `unit`
- LEAF: `contact`, `offer`, `asset_edit`, `process*`, `location`, `hours`
- HOLDER: `contact_holder`, `unit_holder`, `offer_holder`, `process_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `asset_edit_holder`, `videography_holder`
- OBSERVATION: `stage_transition` (virtual)
- Pipeline entities: `process_sales`, `process_outreach`, `process_onboarding`, `process_implementation`, `process_month1`, `process_retention`, `process_reactivation`, `process_account_error`, `process_expansion`

### 3. Protocol interfaces (`src/autom8_asana/protocols/`)

Pure Python `Protocol` classes defining DI contracts: `AuthProvider`, `CacheProvider` + `DataFrameCacheProtocol` + `WarmResult`, `DataFrameProvider`, `InsightsProvider`, `ItemLoader`, `LogProvider`, `MetricsEmitter`, `ObservabilityHook`. These are IoC boundaries enabling test mocking and pluggable implementations.

### 4. `SchemaRegistry` (`src/autom8_asana/dataframes/models/registry.py`)

Module-level singleton mapping entity pascal names to Polars DataFrame schemas. Auto-discovers schemas via `EntityDescriptor.schema_module_path`.

### 5. `DataFrameBuilder` ABC (`src/autom8_asana/dataframes/builders/base.py`)

ABC for entity DataFrame construction. Concrete: `SectionDataFrameBuilder`, `ProgressiveDataFrameBuilder`. Builders call `BaseExtractor` subclasses, feeding results into typed row models.

### 6. `BaseExtractor` ABC (`src/autom8_asana/dataframes/extractors/base.py`)

Per-entity-type extractor. Concrete: `BusinessExtractor`, `UnitExtractor`, `ContactExtractor`, `OfferExtractor`, `AssetEditExtractor`, `AssetEditHolderExtractor`, `ProcessExtractor`.

### 7. `AsanaHttpClient` (`src/autom8_asana/transport/asana_http.py`)

Low-level transport wrapper around `autom8y-http` SDK. Provides `AdaptiveSemaphore` concurrency control, `AsanaResponseHandler`, rate limit detection, retry logic.

### 8. `SavePipeline` / `SaveSession` (`src/autom8_asana/persistence/`)

`SaveSession` is the transactional write context for persisting business model mutations. `SavePipeline` orchestrates action ordering, dependency graph resolution, holder construction, batch execution via `BatchClient`, event emission.

### 9. `EntityWriteRegistry` (`src/autom8_asana/resolution/write_registry.py`)

Maps writable entity type names to write handlers. Built at startup from `EntityRegistry`. Used by `entity_write_router`.

### 10. `AuthContext` (`src/autom8_asana/api/dependencies.py`)

Request-scoped object carrying `mode` (PAT or JWT), `asana_pat` (resolved token), optional `caller_service`. Dual-mode authentication abstraction.

### Design Patterns

- **Descriptor registry pattern**: `EntityRegistry` + `EntityDescriptor` as frozen dataclasses — single source of truth with import-time integrity validation.
- **Protocol-based DI**: `protocols/` contracts; `_defaults/` implementations; tests substitute mocks.
- **Tiered cache pattern**: `cache/backends/` composed by `cache/providers/` orchestrated by `cache/integration/` adapters.
- **Lazy singleton on `app.state`**: Built once at startup, accessed per-request via DI.
- **Background task cache warming**: `asyncio.Task` in lifespan; `/health` returns 200 immediately while `/health/ready` gates on warming completion.
- **Cascade field propagation**: `Business` and `Unit` expose `CascadingFieldDef` inner classes driving cross-entity field inheritance (e.g., `office_phone` flowing Business → Unit → Offer).

## Data Flow

### 1. Inbound API Request (PAT mode — DataFrames)

```
HTTP POST /api/v1/dataframes/{schema}
  → FastAPI route dispatch (api/routes/dataframes.py)
  → [Middleware: IdempotencyMiddleware, SecurityHeaders, JWTAuthMiddleware (excluded), RateLimit]
  → get_auth_context() DI: extract Bearer token → AuthContext(mode=PAT, asana_pat=token)
  → get_asana_client_from_context() DI: ClientPool.get_or_create(pat) → AsanaClient
  → DataFrameService.get_dataframe(schema, project_gid)
      → SchemaRegistry.get(schema) → Polars schema definition
      → DataFrameBuilder.build(project_gid, client)
          → TasksClient.list_project_tasks() via AsanaHttpClient
          → BaseExtractor.extract(task_dict) → typed TaskRow
      → Polars DataFrame assembled
  → _format_dataframe_response() → JSON records or Polars-serialized binary
  → HTTP 200 response
```

### 2. Inbound Webhook (Asana Rules action)

```
POST /api/v1/webhooks/inbound?token=<secret>
  → verify_webhook_token(): timing-safe compare vs ASANA_WEBHOOK_INBOUND_TOKEN
  → receive_inbound_webhook():
      → request.json() → Task Pydantic model
      → background_tasks.add_task(_process_inbound_task, task, cache_provider)
      → JSONResponse({"status": "accepted"})  ← immediate 200
  → Background: invalidate_stale_task_cache() → CacheProvider.evict(TASK/SUBTASKS/DETECTION)
  → Background: WebhookDispatcher.dispatch(task) → registered handler (no-op in V1)
```

### 3. S2S Resolution Request

```
POST /v1/resolve/{entity_type}
  → JWTAuthMiddleware: validate Bearer JWT → require business_scope
  → get_auth_context(): validate JWT → get_bot_pat() → AuthContext(JWT mode)
  → get_asana_client_from_context(): ClientPool.get_or_create(bot_pat, is_s2s=True)
  → resolve_entities():
      → EntityProjectRegistry.get(entity_type) → project GID
      → ResolutionContext with budget, strategies
      → ResolutionStrategy chain (SessionCache → NavigationRef → DependencyShortcut → HierarchyTraversal)
      → TasksClient / cache lookup → matched entity GID
  → SuccessResponse[ResolveResponse]
```

### 4. Lambda: Cache Warming

```
Lambda event → cache_warmer.handler(event, context)
  → bootstrap() (business model registry)
  → EntityRegistry.warmable_entities() → sorted by warm_priority (1→18)
  → For each warmable entity:
      → DataFrameBuilder.build(entity.primary_project_gid, AsanaClient(bot_pat))
          → TasksClient.list_project_tasks() via Asana REST API
          → BaseExtractor.extract() per task → DataFrame
      → CacheProvider.set(entity_key, dataframe_bytes) → S3 backend
```

### 5. Config / Settings Flow

```
Environment variables
  → autom8y-config BaseSettings (pydantic-settings)
  → AsanaSettings (settings.py): log_level, debug, rate_limit_rpm, api_host, api_port, cors_origins
  → CacheSettings: backend (memory/redis/s3), TTL, staleness config
  → S3Settings: bucket name, region, prefix for DataFrame cache
  → api/config.py: get_settings() (functools.lru_cache singleton)
  → api/lifespan.py: consumes settings during startup
  → AsanaConfig (config.py): per-client config (rate limits, retry, circuit breaker, timeouts)
```

### 6. Persistence Write Pipeline

```
Business model mutation (e.g., lifecycle creation)
  → SaveSession(client) context manager
  → SaveSession.add_action(UpdateTaskAction | CreateTaskAction)
  → SaveSession.save():
      → SavePipeline.execute(actions)
          → DependencyGraph.resolve() → topological order
          → ActionExecutor.execute_batch(ordered_actions, BatchClient)
          → BatchClient → Asana /batch API endpoint
          → EventSystem.emit(mutation_events)
          → MutationInvalidator.invalidate(affected_gids) → CacheProvider.evict()
```

## Knowledge Gaps

1. **`automation/engine.py`**: `AutomationEngine` class imported only under `TYPE_CHECKING` in `client.py` — full interface, trigger evaluation, and integration with polling scheduler untraced.
2. **`models/business/detection/` tier logic**: 4-tier entity detection system not read in detail; facade observed but internal tier logic untraced.
3. **`query/` internals beyond engine.py**: `PredicateCompiler`, `join.execute_join`, temporal provider, `timeline_provider` modules identified but not read.
4. **`reconciliation/` pipeline**: Engine, executor, processor logic identified but not traced in depth.
5. **`metrics/` DSL**: Expression DSL (`metrics/expr.py`) and compute engine identified but not read.
6. **`clients/data/` (DataServiceClient)**: Cross-service endpoints (batch, export, insights, reconciliation, simple) not read in detail.
7. **Fleet-query adapter** (`api/fleet_query_adapter.py`): Adapter mapping fleet-canonical query format to internal query engine not read.
8. **`cache/dataframe/tiers/progressive.py`**: Progressive cache tier strategy not read in detail.
