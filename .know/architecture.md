---
domain: architecture
generated_at: "2026-04-01T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "24d8e44"
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

**Language**: Python 3.12. Build tool: Hatchling. Package manager: uv. Source root: `src/autom8_asana/`. Entry CLI: `autom8-query` (-> `src/autom8_query_cli.py`).

**Total packages (directories with `__init__.py`)**: 34. **Total Python files**: 476.

## Package Structure

### Top-Level Package: `src/autom8_asana/`

Root-level files (6 files):
- `__init__.py` — top-level public API; exports `AsanaClient`
- `client.py` — `AsanaClient` facade; the primary entry point for SDK consumers
- `config.py` — SDK configuration dataclasses (`AsanaConfig`, `CacheConfig`, `RateLimitConfig`, etc.); also delegates `DEFAULT_ENTITY_TTLS` via facade to `core.entity_registry`
- `settings.py` — Pydantic `BaseSettings` singleton (`get_settings()`); reads all `ASANA_*` env vars
- `entrypoint.py` — Dual-mode ECS/Lambda entrypoint; detects `AWS_LAMBDA_RUNTIME_API` and routes to uvicorn or awslambdaric
- `exceptions.py` — Root exception hierarchy

### Sub-Packages

| Package | Files | Purpose | Classification |
|---------|-------|---------|----------------|
| `api/` | 10 + sub-pkgs | FastAPI application factory, middleware, route registration, lifespan, OpenAPI enrichment | **Surface/hub** |
| `api/middleware/` | 2 | `RequestIDMiddleware`, `RequestLoggingMiddleware`, `IdempotencyMiddleware` | leaf |
| `api/preload/` | 3 | Progressive DataFrame cache preload during startup | leaf |
| `api/routes/` | 22 | All REST route handlers (tasks, projects, sections, users, workspaces, dataframes, webhooks, workflows, resolver, query, admin, internal, matching, intake-*) | leaf |
| `auth/` | ~3 | JWT validation (`dual_mode.py`), bot PAT retrieval (`bot_pat.py`) | leaf |
| `automation/` | 10 | Rule engine (`AutomationEngine`), pipeline conversion, seeding, template discovery, waiter | hub |
| `automation/events/` | 6 | EventBridge event emission (`AutomationEventEmitter`), envelope types | leaf |
| `automation/polling/` | 6 | Development-mode polling scheduler (yaml-driven); production uses cron Lambda | leaf |
| `automation/workflows/` | 7 + sub-pkgs | Registered automation workflows (base, registry, mixins, bridge_base) | hub |
| `automation/workflows/conversation_audit/` | 1 | Conversation audit workflow | leaf |
| `automation/workflows/insights/` | 3 | Insights export workflow (tables, formatter) | leaf |
| `automation/workflows/payment_reconciliation/` | 2 | Payment reconciliation workflow (Excel output via openpyxl) | leaf |
| `batch/` | 1 | `BatchClient` for Asana batch API | leaf |
| `cache/` | 1 | Package init | hub |
| `cache/backends/` | 4 | `base.py`, `memory.py`, `redis.py`, `s3.py` — pluggable backends | leaf |
| `cache/dataframe/` | 6 + sub-pkgs | Tiered DataFrame cache (build coordinator, coalescer, circuit breaker, warmer) | hub |
| `cache/dataframe/tiers/` | 2 | Memory tier and progressive (S3) tier implementations | leaf |
| `cache/integration/` | 11 | Adapter wiring (`factory.py`, `dataframe_cache.py`, `mutation_invalidator.py`, `hierarchy_warmer.py`, `freshness_coordinator.py`, `staleness_coordinator.py`) | hub |
| `cache/models/` | 10 | Cache data models (`CacheEntry`, `FreshnessIntent`, `FreshnessStamp`, `CacheMetrics`, `VersionInfo`, etc.) | leaf |
| `cache/policies/` | 5 | Freshness policy, staleness, hierarchy, coalescer, lightweight checker | leaf |
| `cache/providers/` | 2 | `UnifiedTaskStore` (tiered), `tiered.py` | leaf |
| `clients/` | 18 | Typed resource clients (`TasksClient`, `ProjectsClient`, `SectionsClient`, etc.); all extend `BaseClient` | hub |
| `clients/data/` | 9 | `DataServiceClient` for cross-service data integration; sub-endpoints (batch, export, insights, reconciliation, simple) | leaf |
| `clients/utils/` | 1 | PII utilities | leaf |
| `core/` | 18 | Foundational utilities: `EntityRegistry`, `EntityDescriptor`, `project_registry.py`, concurrency, retry, logging, string utils, datetime utils | **leaf (imported by all)** |
| `dataframes/` | 1 + sub-pkgs | Public DataFrame API (builders, extractors, schemas, resolver, models, cache integration, views) | hub |
| `dataframes/builders/` | 3 | `DataFrameBuilder`, `ProgressiveProjectBuilder`, `SectionDataFrameBuilder` | leaf |
| `dataframes/extractors/` | ~3 | `BaseExtractor`, `UnitExtractor`, `ContactExtractor` | leaf |
| `dataframes/models/` | ~3 | `DataFrameSchema`, `ColumnDef`, row models (`TaskRow`, `UnitRow`, `ContactRow`) | leaf |
| `dataframes/resolver/` | ~3 | `CustomFieldResolver`, `DefaultCustomFieldResolver`, `NameNormalizer` | leaf |
| `dataframes/schemas/` | ~3 | Built-in schemas (`BASE_SCHEMA`, `UNIT_SCHEMA`, `CONTACT_SCHEMA`) | leaf |
| `dataframes/views/` | ~2 | DataFrame view definitions | leaf |
| `lambda_handlers/` | ~5 | Lambda handler entrypoints: `cache_warmer`, `cache_invalidate`, `conversation_audit`, `insights_export`, `payment_reconciliation` | leaf |
| `lifecycle/` | ~2 | Service lifecycle helpers | leaf |
| `metrics/` | ~3 | Prometheus metric registration, CloudWatch metrics; `__main__.py` for CLI compute | leaf |
| `metrics/definitions/` | ~2 | Metric definitions | leaf |
| `models/` | 12 + sub-pkgs | Pydantic models for Asana resources (`Task`, `Project`, `Section`, `User`, etc.) and base `AsanaResource` | **leaf (imported broadly)** |
| `models/business/` | 18 + sub-pkgs | Domain entity models (`Business`, `Unit`, `Contact`, `Offer`, `Process`, etc.); `_bootstrap.py` registers the model registry | hub |
| `models/business/detection/` | 7 | Tiered detection logic (tier1-tier4), facade, config, types | leaf |
| `models/business/matching/` | 6 | Fuzzy matching engine (blocking, comparators, normalizers, config) | leaf |
| `models/contracts/` | 1 | Cross-service contracts (`phone_vertical.py`) | leaf |
| `observability/` | ~2 | OpenTelemetry helpers | leaf |
| `patterns/` | ~2 | Shared behavioral patterns | leaf |
| `persistence/` | ~8 | Unit of Work / `SaveSession` implementation (cascade, healing, models, session, exceptions) | hub |
| `protocols/` | 8 | Protocol interfaces for dependency injection (`AuthProvider`, `CacheProvider`, `DataFrameProvider`, `LogProvider`, `ObservabilityHook`, etc.) | **leaf (imported as DI boundary)** |
| `query/` | ~10 | Composable query engine (`QueryEngine`, `PredicateCompiler`, `AggregationCompiler`, join, guards, hierarchy) | hub |
| `reconciliation/` | ~3 | Payment reconciliation processing | leaf |
| `resolution/` | ~4 | Entity resolution and write registry | leaf |
| `search/` | ~2 | `SearchService` | leaf |
| `services/` | 21 | Business-logic services wiring clients+cache+models (`entity_service.py`, `resolver.py`, `dataframe_service.py`, `matching_service.py`, `query_service.py`, etc.) | hub |
| `transport/` | 6 | HTTP transport: `AsanaHttpClient` (wraps `autom8y-http`), `AsyncAdaptiveSemaphore`, `ConfigTranslator`, `AsanaResponseHandler` | leaf |
| `_defaults/` | ~3 | Default implementations of protocol interfaces (`EnvAuthProvider`, `DefaultLogProvider`, `NullObservabilityHook`) | leaf |

**Hub packages** (imported by many siblings): `core/`, `models/`, `protocols/`, `settings.py`, `config.py`

**Leaf packages** (no internal imports): `transport/`, `cache/backends/`, `cache/models/`, `dataframes/schemas/`, `_defaults/`

## Layer Boundaries

This codebase implements a layered architecture with four named tiers, enforced by import direction:

```
API Layer         api/routes/, api/main.py             <- REST surface
Services Layer    services/                             <- Orchestration
Domain Layer      models/, dataframes/, query/,         <- Business logic
                  automation/, persistence/
Infrastructure    clients/, transport/, cache/,          <- External I/O
                  protocols/, core/, settings.py
```

**Import direction rules** (observed in codebase):

- `api/` imports from `services/`, `models/`, `core/`, `protocols/`, `cache/integration/`, `auth/`
- `services/` imports from `models/`, `core/`, `clients/`, `cache/`, `protocols/`, `dataframes/`
- `models/` imports from `core/` only (no service/client imports)
- `clients/` imports from `models/`, `core/`, `protocols/`, `transport/` (injects `AsanaHttpClient`)
- `transport/` imports from `autom8y-http` platform SDK and `protocols/` — no internal upward imports
- `cache/` imports from `settings.py`, `protocols/` — no client or service imports
- `protocols/` imports nothing internal (pure protocol definitions)
- `core/` imports nothing internal except within itself

**Circular import avoidance patterns**:
1. `TYPE_CHECKING` guards: Used extensively in `client.py`, `config.py`, `transport/asana_http.py`, `cache/integration/factory.py` to defer heavy imports to type-check time only.
2. `__getattr__` lazy loading: `automation/__init__.py` defers `PipelineConversionRule` import to break the `models.business` -> `cache` -> `config` -> `automation` -> `models.business` cycle.
3. Facade modules: `core/entity_types.py` and the `DEFAULT_ENTITY_TTLS` in `config.py` delegate to `core/entity_registry.py` to avoid re-declaration.
4. `ruff` TID251 banned imports: `httpx`, `loguru`, `structlog`, `requests` are banned at lint-time, enforcing platform SDK usage.

**Boundary enforcement observed**:
- `src/autom8_asana/api/dependencies.py` has `# noqa: E402` for delayed imports (documented in `pyproject.toml` ruff config)
- `src/autom8_asana/client.py` has `# noqa: E402` for same reason
- `services/resolver.py` registers `reset_contexts` at module load time with `core/system_context.py`

**Platform SDK dependencies** (external, not internal packages):
- `autom8y-http` — HTTP client (`Autom8yHttpClient`, circuit breaker, rate limiter)
- `autom8y-cache` — Cache primitives
- `autom8y-log` — Structured logging (`get_logger`)
- `autom8y-config` — Config primitives
- `autom8y-auth` — JWT validation (JWKS-backed)
- `autom8y-telemetry` — OpenTelemetry instrumentation
- `autom8y-events` — EventBridge publishing
- `autom8y-core` — Platform core types

## Entry Points and API Surface

### Primary Entry Points

1. **`src/autom8_asana/entrypoint.py`** — Dual-mode container entry point
   - ECS mode: calls `models.business._bootstrap.bootstrap()` then launches uvicorn targeting `autom8_asana.api.main:create_app`
   - Lambda mode: delegates to `awslambdaric` with handler path from `sys.argv[1]`
   - Detection: `AWS_LAMBDA_RUNTIME_API` env var presence

2. **`src/autom8_asana/api/main.py`** — FastAPI `create_app()` factory
   - Returns a configured `FastAPI` instance
   - Middleware stack (outer -> inner execution): CORSMiddleware -> `IdempotencyMiddleware` -> `SlowAPIMiddleware` -> `RequestLoggingMiddleware` -> `RequestIDMiddleware`
   - Lifespan: `src/autom8_asana/api/lifespan.py`

3. **SDK entry point**: `from autom8_asana import AsanaClient` (direct SDK use without API server)

4. **CLI tool**: `autom8-query` -> `src/autom8_query_cli.py`

### REST Routes (all under `/api/v1/` prefix)

| Router | Auth | Endpoints | File |
|--------|------|-----------|------|
| `health_router` | None | `/health`, `/ready`, `/health/deps` | `api/routes/health.py` |
| `tasks_router` | PAT Bearer | CRUD + subtasks, duplicates, tags, sections, assignees, memberships | `api/routes/tasks.py` |
| `projects_router` | PAT Bearer | CRUD + sections, members | `api/routes/projects.py` |
| `sections_router` | PAT Bearer | CRUD + task add, reorder | `api/routes/sections.py` |
| `users_router` | PAT Bearer | Current user, lookup by GID, list workspace users | `api/routes/users.py` |
| `workspaces_router` | PAT Bearer | List, get by GID | `api/routes/workspaces.py` |
| `dataframes_router` | PAT Bearer | Schema discovery + entity DataFrame fetch | `api/routes/dataframes.py` |
| `webhooks_router` | URL token (`?token=`) | `/webhooks/inbound` | `api/routes/webhooks.py` |
| `workflows_router` | PAT Bearer | List workflows, invoke by ID (dry-run, param overrides) | `api/routes/workflows.py` |
| `resolver_router` | S2S JWT | `/v1/resolve/{entity_type}` — entity resolution | `api/routes/resolver.py` |
| `intake_resolve_router` | S2S JWT | `/v1/resolve/business`, `/v1/resolve/contact` | `api/routes/intake_resolve.py` |
| `query_introspection_router` | S2S JWT | `/v1/query/types`, `/v1/query/{entity_type}/fields`, etc. | `api/routes/query.py` |
| `query_router` | S2S JWT | `/v1/query/{entity_type}/rows`, `/v1/query/{entity_type}/aggregate` | `api/routes/query.py` |
| `admin_router` | S2S JWT | Admin operations | `api/routes/admin.py` |
| `internal_router` | S2S JWT | Internal service operations | `api/routes/internal.py` |
| `entity_write_router` | S2S JWT | Entity write operations | `api/routes/entity_write.py` |
| `section_timelines_router` | PAT (offers) | Offer section timeline | `api/routes/section_timelines.py` |
| `intake_custom_fields_router` | S2S JWT | Intake custom field writes | `api/routes/intake_custom_fields.py` |
| `intake_create_router` | S2S JWT | Intake business creation + process routing | `api/routes/intake_create.py` |
| `matching_router` | S2S JWT (hidden) | `/v1/matching/query` — scored business candidates | `api/routes/matching.py` |

**Security schemes** (injected into OpenAPI spec):
- `PersonalAccessToken` — Bearer token (Asana PAT), used by PAT-tagged routes
- `ServiceJWT` — Bearer JWT (S2S), used by resolver/query/admin/internal routes
- `WebhookToken` — API key in query parameter `?token=`, used by webhooks

### Lambda Entry Points

Five handlers in `src/autom8_asana/lambda_handlers/`:
- `cache_warmer` — Pre-warm DataFrame cache before traffic
- `cache_invalidate` — Invalidate stale cache entries
- `conversation_audit` — Conversation audit workflow
- `insights_export` — Insights export workflow
- `payment_reconciliation` — Payment reconciliation workflow (Excel output)

### Startup Initialization Sequence (`api/lifespan.py`)

1. `models.business._bootstrap.bootstrap()` — register business model registry
2. Configure structured logging + OTel trace ID injection
3. Activate global httpx OTel instrumentation
4. Create shared `CacheProvider` (stored on `app.state.cache_provider`)
5. Initialize `ClientPool` (token-keyed, shares cache provider)
6. `_discover_entity_projects(app)` — resolve project GIDs from live workspace (fail-fast)
7. Cross-registry consistency validation (`validate_cross_registry_consistency`)
8. `_initialize_dataframe_cache(app)` — tiered DataFrame cache on `app.state.dataframe_cache`
9. `_register_schema_providers()` — bridge satellite `SchemaRegistry` to SDK
10. `_initialize_mutation_invalidator(app)` — wire REST cache invalidation
11. Initialize `EntityWriteRegistry` on `app.state.entity_write_registry`
12. Register workflow configs (insights, conversation-audit) for API invocation
13. `validate_cascade_ordering()` — validate DataFrame warm-up ordering
14. Launch background `cache_warming` task (`_preload_dataframe_cache_progressive`)

## Key Abstractions

### 1. `AsanaClient` — `src/autom8_asana/client.py`
The top-level SDK facade. Aggregates all resource clients (tasks, projects, sections, users, workspaces, attachments, custom fields, goals, portfolios, stories, tags, teams, webhooks) and optional subsystems (`batch`, `automation`, `search`, `persistence`). Accepts injected `auth_provider`, `cache_provider`, `log_provider`, `observability_hook` for platform integration. Exposes sync wrappers over async methods. Used as: `AsanaClient(token=pat)`.

### 2. `AsanaResource` — `src/autom8_asana/models/base.py`
Pydantic v2 base class (`extra="ignore"`, `populate_by_name=True`, `str_strip_whitespace=True`) for all Asana API response models. Fields: `gid` (str), `resource_type` (str | None). All domain models (`Task`, `Project`, `Section`, `User`, etc.) extend this.

### 3. `EntityDescriptor` / `EntityRegistry` — `src/autom8_asana/core/entity_registry.py`
Frozen dataclass `EntityDescriptor` captures all metadata for one business entity type (name, pascal_name, category, Asana project GID, model class path, schema/extractor/row model paths, cache TTL, warm priority, join keys, aliases). `EntityRegistry` is a singleton with O(1) lookup by name, project GID, and `EntityType`. This is the **single source of truth** for entity configuration. Entity categories: ROOT (Business), COMPOSITE (Unit), LEAF (Contact, Offer, Process, etc.), HOLDER, OBSERVATION.

### 4. `BaseClient` — `src/autom8_asana/clients/base.py`
Base class for all 13+ resource-specific clients. Accepts injected `AsanaHttpClient` (transport), `AsanaConfig`, `AuthProvider`, `CacheProvider`, `LogProvider`. Provides cache check-before-HTTP, store-on-miss pattern.

### 5. `AsanaHttpClient` — `src/autom8_asana/transport/asana_http.py`
Thin transport wrapper over `autom8y-http`'s `Autom8yHttpClient`. Handles Asana-specific response unwrapping, error translation (`RateLimitError`, `ServerError`, `TimeoutError`). Uses `AsyncAdaptiveSemaphore` (AIMD: halves concurrency on 429, increments on success) for read/write concurrency control.

### 6. `CacheProvider` / `CacheEntry` — `src/autom8_asana/protocols/cache.py`, `src/autom8_asana/cache/models/entry.py`
Protocol defining versioned cache operations (get/set/delete, get_versioned/set_versioned, batch ops, warm, check_freshness, invalidate, is_healthy). Concrete implementations: `NullCacheProvider`, `InMemoryCacheProvider`, `RedisCacheProvider`, `UnifiedTaskStore` (tiered).

### 7. `SaveSession` — `src/autom8_asana/persistence/session.py`
Unit of Work context manager for batched Asana API writes. Tracks entities, computes dependency graph, commits in optimal order, provides pre/post-save hooks. Supports sync and async patterns.

### 8. `DataFrameSchema` / `SchemaRegistry` — `src/autom8_asana/dataframes/models/`
`DataFrameSchema` defines column definitions for typed Polars DataFrame extraction. `SchemaRegistry` maps entity type keys to schemas. Auto-discovered via `EntityDescriptor.schema_module_path`.

### 9. `QueryEngine` — `src/autom8_asana/query/engine.py`
Composable query engine over cached DataFrames. Accepts `RowsRequest` (predicate AST) or `AggregateRequest`. Compiled by `PredicateCompiler` to Polars expressions. Supports cross-entity joins via `EntityRelationship`.

### 10. `AsanaConfig` — `src/autom8_asana/config.py`
Master configuration dataclass composing: `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig` (with AIMD params), `TimeoutConfig`, `ConnectionPoolConfig`, `CircuitBreakerConfig`, `CacheConfig`, `DataFrameConfig`, `AutomationConfig`.

### Design Patterns

- **Protocol-based DI**: `protocols/` defines structural interfaces; `_defaults/` provides null/env-based implementations; `AsanaClient` accepts injected providers.
- **Factory pattern**: `CacheProviderFactory.create(config)` selects backend based on env detection chain.
- **Facade pattern**: `config.py:DEFAULT_ENTITY_TTLS`, `core/entity_types.py:ENTITY_TYPES` — thin delegators to `EntityRegistry`.
- **Descriptor-driven auto-discovery**: `EntityDescriptor` stores dotted paths for schema, extractor, row model; resolved lazily at runtime via `importlib`.
- **AIMD congestion control**: `transport/adaptive_semaphore.py` implements TCP-inspired adaptive semaphore for Asana rate limit compliance.
- **Stale-While-Revalidate (SWR)**: Cache freshness model with `FreshnessIntent.EVENTUAL` default.

## Data Flow

### Primary Flow: API Request -> Asana -> Cache

```
HTTP Request
    -> RequestIDMiddleware (assigns X-Request-ID)
    -> RequestLoggingMiddleware (structured log)
    -> SlowAPIMiddleware (rate limiting)
    -> IdempotencyMiddleware (RFC 8791 store-and-replay)
    -> CORSMiddleware
    -> Route handler
        -> api/dependencies.py::get_auth_context()
            -> detect_token_type() -> PAT or S2S JWT path
        -> AsanaClient per-request instantiation (via ClientPool or direct)
        -> service layer (e.g., services/task_service.py)
            -> clients/tasks.py::TasksClient
                -> CacheProvider.get_versioned() [check]
                -> on miss: AsanaHttpClient.get() -> Asana API
                -> CacheProvider.set_versioned() [store]
        -> Pydantic model serialization -> JSON response
```

### Secondary Flow: DataFrame Cache Warm-Up

```
startup lifespan
    -> _preload_dataframe_cache_progressive(app) [background task]
        -> EntityRegistry.warmable_entities() [discover entity types]
        -> for each entity: clients/data/ or clients/ fetch sections
            -> DataFrameBuilder.build() -> Polars DataFrame
            -> DataFrameCache.put_async(project_gid, entity_type, df, watermark)
                -> progressive tier (S3)
                -> memory tier
/ready -> 503 until cache_warming_task completes
```

### Tertiary Flow: S2S Query

```
POST /v1/query/{entity_type}/rows
    -> S2S JWT validation via autom8y_auth
    -> api/routes/query.py -> services/query_service.py
        -> QueryEngine.rows(request: RowsRequest)
            -> DataFrameProvider.get(entity_type)  [from cache]
            -> PredicateCompiler.compile(predicates) -> pl.Expr
            -> Polars filter -> serialize rows
```

### Configuration Merge Points

```
Environment Variables (ASANA_*)
    -> settings.py::Settings (Pydantic singleton, get_settings())
        -> config.py::AsanaConfig (dataclasses, composed from Settings)
            -> AsanaClient.__init__() (accepts explicit or auto-created config)
                -> CacheConfig -> CacheProviderFactory.create()
                -> ConcurrencyConfig -> AsyncAdaptiveSemaphore
                -> RetryConfig -> ExponentialBackoffRetry
```

**Key merge point**: `api/lifespan.py` creates a single shared `AsanaConfig()` and shared `CacheProvider` that is passed to `ClientPool`. Per-request clients inherit this shared cache and circuit-breaker state.

## Knowledge Gaps

1. **`search/` package**: Files not read in detail; `SearchService` purpose and method signatures not documented.
2. **`reconciliation/` package**: Only top-level structure known; reconciliation processor logic not read.
3. **`resolution/` package**: Only `write_registry.py` referenced; full resolution model not traced.
4. **`lifecycle/` package**: Contents not read; lifecycle hook types unknown.
5. **`patterns/` package**: Contents not read; behavioral pattern types unknown.
6. **`observability/` package**: Contents not read beyond naming.
7. **`_defaults/`**: `EnvAuthProvider`, `DefaultLogProvider`, `NullObservabilityHook` mentioned in `client.py` imports but not read in detail.
8. **`clients/data/client.py`**: `DataServiceClient` (cross-service data integration) not fully traced; interacts with an external `autom8y-data` service at `AUTOM8Y_DATA_URL`.
9. **`dataframes/views/`**: View definitions not read.
10. **`models/business/` depth**: The 18-file business domain model (detection tiers, matching engine, DNA, hydration) not fully traced — high complexity, only top-level structure documented.
