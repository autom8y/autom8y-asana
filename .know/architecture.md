---
domain: architecture
generated_at: "2026-03-29T18:30:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "905fe4b"
confidence: 0.93
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "ccac1bdf21a076abac37f960cd0d2210bee78a023d780c7374cb6d5c087c9c5b"
---

# Codebase Architecture

**autom8y-asana** is an async-first Asana API client and satellite service. It is a Python 3.12 project using FastAPI, Pydantic v2, and Polars. The package is published as `autom8y-asana` from `src/autom8_asana/` using Hatchling. It runs as both an ECS service (uvicorn) and AWS Lambda (awslambdaric) from a single dual-mode Docker image.

Total source: ~460 Python files across 24 top-level packages under `src/autom8_asana/`.

## Package Structure

### Top-Level Packages (sorted by file count, descending)

| Package | Files | Purpose | Hub/Leaf |
|---------|-------|---------|----------|
| `models/` | 60 | Pydantic v2 models for Asana resources + business domain entities | Hub |
| `dataframes/` | 54 | Schema-driven extraction of Asana tasks into typed Polars DataFrames | Hub |
| `cache/` | 52 | Multi-tier caching (Memory, Redis, S3) with versioned entries and staleness detection | Hub |
| `api/` | 47 | FastAPI service layer: routes, middleware, lifespan, dependencies | Hub |
| `automation/` | 42 | Rule-based automation engine (events, workflows, pipeline conversion) | Hub |
| `clients/` | 39 | Typed resource API clients (Tasks, Projects, Sections, etc.) + cross-service data client | Leaf |
| `services/` | 21 | Service layer: resolution, query, dataframe, intake, matching, entity writes | Hub |
| `persistence/` | 20 | Unit of Work pattern: SaveSession, cascade operations, self-healing | Hub |
| `query/` | 19 | Composable predicate query engine over cached DataFrames | Hub |
| `core/` | 19 | Foundational: concurrency, logging, entity registry, timing, string utils | Leaf |
| `lifecycle/` | 16 | Data-driven lifecycle engine for pipeline automation (YAML config) | Hub |
| `lambda_handlers/` | 12 | AWS Lambda entry points (cache warmer, insights export, conversation audit, etc.) | Leaf |
| `metrics/` | 10 | Declarative metric computation layer over DataFrames | Leaf |
| `protocols/` | 9 | Protocol definitions (AuthProvider, CacheProvider, LogProvider, etc.) | Leaf |
| `resolution/` | 8 | Entity resolution primitives (strategies, budgets, selection predicates) | Leaf |
| `transport/` | 6 | HTTP transport: AsanaHttpClient wrapper over autom8y-http SDK | Leaf |
| `auth/` | 6 | Dual-mode auth: JWT (S2S) + PAT pass-through, bot PAT, audit logging | Leaf |
| `_defaults/` | 5 | Default provider implementations: EnvAuthProvider, NullCacheProvider, etc. | Leaf |
| `observability/` | 4 | Correlation IDs, error handling decorators, LogContext | Leaf |
| `search/` | 3 | Field-based search over cached Polars DataFrames | Leaf |
| `patterns/` | 3 | Reusable design patterns: async/sync method pairs, error classification | Leaf |
| `batch/` | 3 | Asana Batch API client for bulk operations (chunks of 10) | Leaf |
| `reconciliation/` | 0 | Payment reconciliation (empty -- logic lives in `automation/workflows/payment_reconciliation/`) | Leaf |

### Key Sub-Package Structures

**`models/`** has three sub-packages:
- `models/business/` (30+ files) -- Business domain entities: Business, Contact, Unit, Offer, Process, Location, Hours, DNA, AssetEdit, Videography, Reconciliation. Each with typed fields extracted from Asana custom fields. Detection, hydration, resolution, seeding, and activity classification logic.
- `models/business/detection/` -- Entity type detection from task metadata.
- `models/business/matching/` -- Scored business candidate matching.
- `models/contracts/` -- Cross-service contracts (PhoneVerticalPair).

**`cache/`** has four tiers:
- `cache/models/` -- Entry, Freshness, Metrics, Versioning, Staleness data models.
- `cache/policies/` -- Staleness checking, hierarchy indexing, request coalescing, lightweight checks.
- `cache/providers/` -- TieredCacheProvider (Redis hot + S3 cold), UnifiedTaskStore.
- `cache/integration/` -- Factory, batch loading, dataframe caching, mutation invalidation, story loading, schema providers.
- `cache/dataframe/` -- DataFrame-specific caching with S3 tier and coalescing.
- `cache/backends/` -- Redis adapter implementation.

**`dataframes/`** has six sub-packages:
- `dataframes/models/` -- TaskRow, UnitRow, ContactRow, ColumnDef, DataFrameSchema, SchemaRegistry.
- `dataframes/schemas/` -- Built-in schemas: base, unit, contact, offer, business, asset_edit, asset_edit_holder.
- `dataframes/extractors/` -- BaseExtractor, UnitExtractor, ContactExtractor, etc.
- `dataframes/builders/` -- DataFrameBuilder, ProgressiveProjectBuilder, SectionDataFrameBuilder.
- `dataframes/resolver/` -- CustomFieldResolver, DefaultCustomFieldResolver for dynamic field GID mapping.
- `dataframes/views/` -- CascadeViewPlugin, DataFrameViewPlugin for unified cache materialization.

**`api/`** has four sub-packages:
- `api/routes/` (20 route modules) -- health, tasks, projects, sections, users, workspaces, dataframes, resolver, query, admin, webhooks, workflows, entity_write, intake_resolve, intake_custom_fields, intake_create, matching, section_timelines, internal.
- `api/middleware/` -- RequestIDMiddleware, RequestLoggingMiddleware, IdempotencyMiddleware.
- `api/preload/` -- Progressive DataFrame cache warming on startup.
- `api/` root -- main.py (app factory), lifespan.py (startup/shutdown), dependencies.py (DI), config.py (API settings), errors.py (exception handlers).

**`automation/`** has three sub-packages:
- `automation/events/` -- Event types and setup_event_emission for EventBridge.
- `automation/polling/` -- Polling scheduler for development mode.
- `automation/workflows/` -- Conversation audit, insights export, payment reconciliation workflow implementations.

**`clients/`** has sub-packages:
- `clients/data/` -- DataServiceClient for cross-service communication with autom8_data.
- `clients/data/_endpoints/` -- Endpoint-specific client methods.
- `clients/utils/` -- Client utilities.

### Root-Level Source Files

| File | Purpose |
|------|---------|
| `src/autom8_asana/__init__.py` | Public API surface: exports AsanaClient, all models, all exceptions, dataframes (lazy-loaded) |
| `src/autom8_asana/client.py` | `AsanaClient` facade: central entry point, lazy-init resource clients with thread-safe double-checked locking |
| `src/autom8_asana/config.py` | Frozen dataclass configs: RateLimitConfig, RetryConfig, ConcurrencyConfig, TimeoutConfig, CacheConfig, AsanaConfig |
| `src/autom8_asana/settings.py` | Pydantic Settings for env var parsing (ASANA_*, REDIS_*, AUTOM8Y_DATA_*, etc.) |
| `src/autom8_asana/exceptions.py` | Exception hierarchy: AsanaError -> AuthenticationError, NotFoundError, RateLimitError, etc. |

## Layer Boundaries

### Layer Model (outside-in)

```
API Layer (api/)
  |
  v
Service Layer (services/, lifecycle/)
  |
  v
Domain Layer (models/, models/business/, automation/)
  |
  v
Data Access Layer (clients/, cache/, dataframes/, persistence/)
  |
  v
Infrastructure Layer (transport/, _defaults/, protocols/, core/)
```

### Import Direction Rules

1. **API -> Services**: Route handlers inject services via FastAPI `Depends()`. Route files import from `services/`, `cache/`, `models/`, and `api/dependencies`.
2. **Services -> Domain + Data Access**: Services import from `models/`, `clients/`, `cache/`, `dataframes/`, `core/`.
3. **Domain -> Data Access**: Business models (`models/business/`) import from `cache/`, `clients/`, `core/`.
4. **Data Access -> Infrastructure**: Clients import from `transport/`, `protocols/`, `config`.
5. **Infrastructure -> nothing internal**: `transport/` depends only on `exceptions` and `config`. `protocols/` has zero internal dependencies.

### Circular Import Avoidance Patterns

The codebase uses several explicit patterns to break circular imports:

- **`__getattr__` lazy loading**: `automation/__init__.py` defers `PipelineConversionRule` import. `cache/__init__.py` defers `register_asana_schemas`. `__init__.py` root defers all DataFrame exports.
- **TYPE_CHECKING guards**: `client.py` imports `AutomationEngine`, `CacheMetrics`, `UnifiedTaskStore`, `SearchService` under `TYPE_CHECKING` only.
- **Explicit bootstrap**: `models/business/_bootstrap.py` provides `bootstrap()` called at app startup rather than import-time registration. Prevents `models.business.__init__ -> cache -> config -> automation -> pipeline -> models.business` cycle.
- **Delayed imports in functions**: `config.py` uses `from autom8_asana.core.entity_registry import get_registry` at module level but `CacheConfig.from_env()` uses lazy imports of `TTLSettings`.

### Key Import Graph Edges

- `transport/asana_http.py` imports: `exceptions`, `transport.adaptive_semaphore`, `transport.config_translator`, `transport.response_handler`
- `clients/base.py` imports: `core.exceptions`, `cache.models.entry`, `config`, `protocols.*`, `transport.asana_http` (all under TYPE_CHECKING)
- `services/resolver.py` imports: `core.string_utils`, `core.entity_registry`, `dataframes.exceptions`, `dataframes.models.registry`
- `lifecycle/engine.py` imports: `core.timing`, `lifecycle.*` submodules, `persistence.models`, `resolution.context`
- `api/dependencies.py` imports: `autom8_asana` root, `auth.*`, `cache.integration.mutation_invalidator`, `services.*` (lazy)

## Entry Points and API Surface

### 1. FastAPI Application (ECS mode)

**Entry point**: `src/autom8_asana/api/main.py` -- `create_app()` factory.

**Startup sequence** (`api/lifespan.py`):
1. Call `bootstrap()` to register business model types
2. Configure structured logging with OTEL trace ID processors
3. Instrument httpx for W3C traceparent propagation
4. Create shared `CacheProvider` on `app.state.cache_provider`
5. Initialize `ClientPool` on `app.state.client_pool` (token-keyed for S2S resilience)
6. Discover entity projects from live workspace (`_discover_entity_projects`)
7. Validate cross-registry consistency
8. Initialize `DataFrameCache`, register schema providers, wire `MutationInvalidator`
9. Build `EntityWriteRegistry` on `app.state.entity_write_registry`
10. Register workflow configs (insights-export, conversation-audit)
11. Validate cascade warm-up ordering
12. Start background cache warming task (`_preload_dataframe_cache_progressive`)

**Router inventory** (20 routers, 3 auth modes):

| Router | Prefix | Auth Mode | In Schema |
|--------|--------|-----------|-----------|
| `health_router` | `/health`, `/ready`, `/health/deps` | None | Yes |
| `tasks_router` | `/api/v1/tasks` | PAT Bearer | Yes |
| `projects_router` | `/api/v1/projects` | PAT Bearer | Yes |
| `sections_router` | `/api/v1/sections` | PAT Bearer | Yes |
| `users_router` | `/api/v1/users` | PAT Bearer | Yes |
| `workspaces_router` | `/api/v1/workspaces` | PAT Bearer | Yes |
| `dataframes_router` | `/api/v1/dataframes` | PAT Bearer | Yes |
| `webhooks_router` | `/api/v1/webhooks` | URL Token | Yes |
| `workflows_router` | `/api/v1/workflows` | PAT Bearer | Yes |
| `resolver_router` | `/v1/resolve/{entity_type}` | S2S JWT | Yes |
| `intake_resolve_router` | `/v1/resolve/business`, `/v1/resolve/contact` | S2S JWT | Yes |
| `query_introspection_router` | `/v1/query/{entity_type}/*` GET | S2S JWT | Yes |
| `query_router` | `/v1/query/{entity_type}/rows`, `/aggregate` POST | S2S JWT | No |
| `admin_router` | `/v1/admin/*` | S2S JWT | No |
| `internal_router` | `/api/v1/internal/*` | S2S JWT | No |
| `entity_write_router` | `/api/v1/entity/*` | S2S JWT | No |
| `intake_custom_fields_router` | `/v1/tasks/{gid}/custom-fields` | S2S JWT | No |
| `intake_create_router` | `/v1/intake/business`, `/v1/intake/route` | S2S JWT | No |
| `matching_router` | `/v1/matching/query` | S2S JWT | No |
| `section_timelines_router` | `/api/v1/section-timelines/*` | PAT Bearer | Yes |

**Middleware stack** (outer to inner execution order):
1. CORSMiddleware (if configured)
2. IdempotencyMiddleware (DynamoDB / memory / noop)
3. SlowAPIMiddleware (rate limiting)
4. RequestLoggingMiddleware
5. RequestIDMiddleware (innermost)
Note: MetricsMiddleware from `instrument_app()` wraps the entire stack.

**OpenAPI spec**: v3.2.0 with custom post-processing. Three security schemes: `PersonalAccessToken`, `ServiceJWT`, `WebhookToken`. Tag-based security classification. Webhook definition for `asanaTaskChanged`.

### 2. AWS Lambda Handlers

**Entry points** in `src/autom8_asana/lambda_handlers/`:

| Handler | File | Purpose |
|---------|------|---------|
| `cache_warmer_handler` | `cache_warmer.py` | Pre-deployment cache warming |
| `cache_invalidate_handler` | `cache_invalidate.py` | Cache invalidation on demand |
| `conversation_audit_handler` | `conversation_audit.py` | Conversation audit export workflow |
| `insights_export_handler` | `insights_export.py` | Insights data export workflow |
| `payment_reconciliation_handler` | `payment_reconciliation.py` | Payment reconciliation bridge |
| `push_orchestrator` | `push_orchestrator.py` | GID push orchestration |
| `story_warmer` | `story_warmer.py` | Story cache warming |
| `workflow_handler` | `workflow_handler.py` | Generic workflow execution |

Supporting modules: `checkpoint.py` (S3 checkpointing), `cloudwatch.py` (metric emission), `timeout.py` (Lambda timeout handling).

### 3. CLI Entry Point

`src/autom8_query_cli.py` provides the `autom8-query` CLI command (registered in `pyproject.toml` under `[project.scripts]`).

### 4. SDK Public API (`AsanaClient`)

`src/autom8_asana/client.py` -- `AsanaClient` is the main SDK entry point.

**Resource clients** (lazy-initialized with thread-safe double-checked locking):

| Property | Client Type | Tier |
|----------|-------------|------|
| `client.tasks` | `TasksClient` | 1 |
| `client.projects` | `ProjectsClient` | 1 |
| `client.sections` | `SectionsClient` | 1 |
| `client.custom_fields` | `CustomFieldsClient` | 1 |
| `client.users` | `UsersClient` | 1 |
| `client.workspaces` | `WorkspacesClient` | 1 |
| `client.webhooks` | `WebhooksClient` | 2 |
| `client.teams` | `TeamsClient` | 2 |
| `client.attachments` | `AttachmentsClient` | 2 |
| `client.tags` | `TagsClient` | 2 |
| `client.goals` | `GoalsClient` | 2 |
| `client.portfolios` | `PortfoliosClient` | 2 |
| `client.stories` | `StoriesClient` | 2 |
| `client.batch` | `BatchClient` | Specialized |
| `client.search` | `SearchService` | Specialized |
| `client.unified_store` | `UnifiedTaskStore` | Specialized |
| `client.automation` | `AutomationEngine` | Specialized |

**Key methods**: `save_session()` returns `SaveSession` (Unit of Work), `warm_cache_async()` / `warm_cache()` for cache pre-population.

### 5. FastAPI Dependency Injection (api/dependencies.py)

**Primary dependencies** (injected via `Depends()`):

| Dependency | Type | Lifecycle |
|------------|------|-----------|
| `get_auth_context` | `AuthContext` | Per-request |
| `get_asana_client_from_context` | `AsanaClient` | Pooled (token-keyed ClientPool) |
| `get_mutation_invalidator` | `MutationInvalidator` | Singleton (app.state) |
| `get_entity_service` | `EntityService` | Singleton (app.state) |
| `get_task_service` | `TaskService` | Per-request |
| `get_section_service` | `SectionService` | Per-request |
| `get_dataframe_service` | `DataFrameService` | Per-request |
| `get_dataframe_cache` | `DataFrameCache` | Singleton (app.state) |
| `get_data_service_client` | `DataServiceClient` | Singleton (app.state) |
| `get_entity_write_registry` | `EntityWriteRegistry` | Singleton (app.state) |

**Type aliases**: `AsanaClientDualMode`, `AuthContextDep`, `MutationInvalidatorDep`, `RequestId`, `EntityServiceDep`, `TaskServiceDep`, `SectionServiceDep`, `DataFrameServiceDep`, `DataFrameCacheDep`, `DataServiceClientDep`.

## Key Abstractions

### 1. `AsanaClient` (client.py)
Facade that owns all resource clients, the HTTP transport, shared rate limiter, circuit breaker, retry policy, and cache provider. Thread-safe lazy initialization of 15+ sub-clients. Supports both sync and async context managers.

### 2. `BaseClient` (clients/base.py)
Abstract base for all 13 resource clients. Receives `AsanaHttpClient`, `AsanaConfig`, `AuthProvider`, `CacheProvider`, `LogProvider`. Provides cache check-before-HTTP / store-on-miss pattern.

### 3. `AsanaHttpClient` (transport/asana_http.py)
Wraps `autom8y-http` platform SDK. Provides `get_async()`, `post_async()`, etc. with Asana-specific response handling. Uses `AsyncAdaptiveSemaphore` (AIMD concurrency control) and shared `TokenBucketRateLimiter`.

### 4. `SaveSession` (persistence/session.py)
Unit of Work pattern. Tracks entity changes, computes diffs, batches mutations via Asana Batch API. Supports dependency ordering (parent before child), partial failure handling, pre/post save hooks, and cascade operations.

### 5. `BusinessEntity` / `HolderMixin` (models/business/base.py)
Base class for all domain entities (Business, Contact, Unit, Offer, Process, Location, Hours). Descriptor-based navigation. ClassVar configuration for custom field mappings. `HolderMixin` provides typed children access for holder tasks.

### 6. `EntityRegistry` (core/entity_registry.py)
Singleton registry of `EntityDescriptor` frozen dataclasses. Single source of truth for entity metadata (name, project GID, TTL, schema path, extractor path, join keys). O(1) lookup by name, GID, or EntityType enum. Import-time validation checks.

### 7. `SchemaRegistry` (dataframes/models/registry.py)
Maps entity types to `DataFrameSchema` definitions. Auto-discovers schemas from `EntityDescriptor.schema_module_path`. Drives the entire DataFrame extraction pipeline.

### 8. `AutomationEngine` (automation/engine.py)
Orchestrates rule evaluation and execution after SaveSession commits. Registers `AutomationRule` implementations. Manages cascade depth to prevent loops. Connected to EventBridge via `setup_event_emission()`.

### 9. `LifecycleEngine` (lifecycle/engine.py)
Data-driven pipeline automation. Reads YAML config (`config/lifecycle_stages.yaml`). Handles transitions, entity creation, cascading section moves, dependency wiring, reopening, and auto-cascade seeding.

### 10. `QueryEngine` (query/engine.py)
Composable predicate filtering over cached DataFrames. Supports `RowsRequest` / `AggregateRequest` with compiled Polars expressions. Join support across entity types via `ENTITY_RELATIONSHIPS`.

### Design Patterns in Use

- **Facade**: `AsanaClient` wraps 15+ clients behind a single interface
- **Unit of Work**: `SaveSession` collects changes and commits in batches
- **Strategy**: `ResolutionStrategy` chain for entity resolution, `DataFrameSchema` for extraction
- **Protocol (structural typing)**: `AuthProvider`, `CacheProvider`, `LogProvider`, `ObservabilityHook`, `WebhookDispatcher`
- **Registry**: `EntityRegistry`, `SchemaRegistry`, `ProjectTypeRegistry`, `WorkspaceProjectRegistry`
- **Factory**: `CacheProviderFactory`, `create_app()`, `create_cache_provider()`
- **Lazy initialization**: Thread-safe double-checked locking on all client properties
- **Tiered caching**: Memory -> Redis -> S3 with freshness modes (Strict, Eventual, SWR)
- **AIMD**: Adaptive Increase / Multiplicative Decrease concurrency control on HTTP semaphores

## Data Flow

### 1. HTTP Request Flow (PAT mode)

```
HTTP Request
  -> RequestIDMiddleware (set X-Request-ID)
  -> RequestLoggingMiddleware (log request/response)
  -> SlowAPIMiddleware (rate limit check)
  -> IdempotencyMiddleware (check/store idempotency key)
  -> CORSMiddleware (preflight handling)
  -> Route handler
    -> get_auth_context() extracts Bearer token, detects PAT vs JWT
    -> get_asana_client_from_context() gets/creates pooled AsanaClient
    -> Service layer (TaskService, DataFrameService, etc.)
    -> Resource client (TasksClient.get_async())
      -> Cache check (CacheProvider.get_versioned())
      -> If miss: AsanaHttpClient.get_async() -> Asana API
      -> Cache store (CacheProvider.set_versioned())
    -> Pydantic model response
```

### 2. DataFrame Pipeline

```
API request: GET /api/v1/dataframes/{project_gid}?schema_type=unit
  -> DataFrameService.get_dataframe()
    -> SchemaRegistry.get_schema("unit") -> DataFrameSchema
    -> DataFrameCache check (S3-backed)
      -> If miss: ProgressiveProjectBuilder
        -> Fetch sections (parallel, max_concurrent_sections=8)
        -> For each section: paginated task fetch with AIMD pacing
        -> UnitExtractor.extract(task, schema) -> UnitRow
        -> CustomFieldResolver maps field names -> GIDs
        -> Build Polars DataFrame
      -> Cache store (DataFrameCache -> S3 Parquet)
    -> Return as JSON records or Polars serialized
```

### 3. Webhook Inbound Pipeline

```
POST /api/v1/webhooks/inbound?token=<secret>
  -> Timing-safe token verification
  -> Parse raw JSON -> Task model (Pydantic validation)
  -> Background task:
    -> Cache invalidation (TASK, SUBTASKS, DETECTION entry types)
    -> WebhookDispatcher.dispatch(task) (extensible via Protocol)
  -> Return 200 immediately (prevent Asana retries)
```

### 4. Save Pipeline (Unit of Work)

```
async with client.save_session() as session:
    session.track(entity)
    entity.name = "Updated"
    result = await session.commit_async()
      -> Compute diffs (EntityState tracking)
      -> Topological sort (parent dependencies first)
      -> Batch mutations (chunks of 10 via Asana Batch API)
      -> Resolve temporary GIDs -> real GIDs
      -> Execute automation rules (AutomationEngine)
      -> Return SaveResult (succeeded, failed, skipped)
```

### 5. Entity Resolution (S2S)

```
POST /v1/resolve/business  (S2S JWT auth)
  -> IntakeResolveService
    -> Build search criteria from phone + vertical
    -> SearchService.find_async() over cached DataFrame
    -> Score candidates using matching algorithms
    -> ResolutionResult with match confidence
```

### 6. Cache Warming (Startup)

```
lifespan startup:
  -> _preload_dataframe_cache_progressive(app)
    -> For each warmable entity (by warm_priority):
      -> ProgressiveProjectBuilder fetches all sections
      -> Builds Polars DataFrames
      -> Stores to DataFrameCache (S3)
    -> Sets app.state.cache_ready = True
    -> /ready endpoint returns 200 (was 503 during warming)
```

### 7. Lambda Execution

```
Lambda invocation (via AWS event):
  -> handler(event, context)
    -> bootstrap() business models
    -> Create AsanaClient with bot PAT
    -> Execute workflow (e.g., insights export)
    -> Emit CloudWatch metrics
    -> Return result
```

### 8. Configuration Flow

```
Environment variables (ASANA_*, REDIS_*, etc.)
  -> settings.py (Pydantic Settings with validation)
  -> config.py (frozen dataclasses: AsanaConfig, CacheConfig, etc.)
  -> AsanaClient.__init__() (composes all configs)
  -> ConfigTranslator (maps domain configs -> platform SDK configs)
  -> autom8y-http, autom8y-cache, autom8y-auth SDK calls
```

## Knowledge Gaps

1. **`reconciliation/` package**: Directory exists with only `__pycache__`, but payment reconciliation logic lives in `automation/workflows/payment_reconciliation/`. The package may be vestigial or planned for migration.

2. **`clients/utils/` contents**: Not deeply examined. Contains client helper utilities referenced by resource clients.

3. **Full automation rule inventory**: The exact set of registered `AutomationRule` implementations beyond `PipelineConversionRule` was not exhaustively enumerated. The rule registration happens at `AsanaClient.__init__` time via `setup_event_emission()`.

4. **Redis cache provider implementation details**: The `cache/backends/` Redis adapter was not fully examined. Its configuration and connection management specifics are known only through the settings layer.

5. **`clients/data/_endpoints/` specifics**: The individual endpoint modules for the `DataServiceClient` were not read. They implement specific HTTP calls to the autom8_data service.

6. **Full Pydantic Settings model**: `settings.py` was read partially (first 60 lines of ~300+). The complete set of environment variables and their Pydantic models is extensive; the module header documents ~60+ variables.

7. **Test structure**: Tests live in `tests/` (not in scope) but are configured with `pytest-asyncio` in auto mode, 60s timeout, and markers for slow/integration/benchmark.

```metadata
overall_grade: A
overall_percentage: 91.0%
confidence: 0.93
criteria_grades:
  package_structure: A
  layer_boundaries: A
  entry_points_and_api_surface: A
  key_abstractions: A
  data_flow: A
```
