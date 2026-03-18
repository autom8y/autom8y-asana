---
domain: architecture
generated_at: "2026-03-18T11:50:56Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "d234795"
confidence: 0.82
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Architecture

## Package Structure

This is a Python package (`autom8_asana`) under `src/autom8_asana/`. The project is a dual-mode Asana API SDK that runs as both an ECS/FastAPI HTTP server and AWS Lambda function handlers. It uses `pyproject.toml` with `hatchling` build backend and `uv` for dependency resolution.

**Top-Level Packages and Modules:**

| Package/Module | Purpose | File Count (approx) |
|---|---|---|
| `src/autom8_asana/__init__.py` | Public API surface — exports `AsanaClient`, all models, protocols, exceptions | 1 |
| `src/autom8_asana/client.py` | `AsanaClient` facade — main SDK entry point, lazy-initializes resource clients | 1 |
| `src/autom8_asana/entrypoint.py` | Dual-mode entry — detects ECS vs Lambda via `AWS_LAMBDA_RUNTIME_API` env var | 1 |
| `src/autom8_asana/settings.py` | Pydantic `Settings` singleton — `AsanaSettings`, `CacheSettings`, `RedisSettings`, `S3Settings`, `PacingSettings`, etc. | 1 |
| `src/autom8_asana/config.py` | `AsanaConfig` dataclass — SDK-level configuration (rate limits, retry, timeouts) | 1 |
| `src/autom8_asana/exceptions.py` | Top-level exception hierarchy — `AsanaError`, `RateLimitError`, `NotFoundError`, etc. | 1 |

**Sub-packages:**

| Package | Purpose | Key Types |
|---|---|---|
| `_defaults/` | Default provider implementations for standalone usage | `EnvAuthProvider`, `SecretsManagerAuthProvider`, `NullCacheProvider`, `NullObservabilityHook` |
| `api/` | FastAPI application — HTTP server surface | `create_app()`, routers, middleware, lifespan, `StartupContext` |
| `api/routes/` | Route handlers per resource | `health_router`, `tasks_router`, `projects_router`, `query_router`, `resolver_router`, `webhooks_router`, `dataframes_router`, `workflows_router`, `entity_write_router`, `section_timelines_router` (~14 routers) |
| `api/preload/` | Cache pre-warming at startup | `LegacyPreloader`, `ProgressivePreloader` |
| `auth/` | Auth strategies for API layer | `JWTValidator`, `BotPATAuth`, `DualModeAuth`, `ServiceToken` |
| `automation/` | Automation rule engine | `AutomationEngine`, `AutomationRule`, `AutomationContext`, `AutomationConfig` |
| `automation/events/` | Async event emission pipeline | `EventEmitter`, `EventEnvelope`, `EventType`, `EventRule` |
| `automation/polling/` | Polling-based automation scheduler | `PollingScheduler`, `TriggerEvaluator`, `ActionExecutor` |
| `automation/workflows/` | Concrete workflow implementations | `PipelineTransitionWorkflow`, `InsightsExportWorkflow`, `ConversationAuditWorkflow`, workflow `registry` |
| `batch/` | Batch Asana API client | `BatchClient`, `BatchRequest`, `BatchResult` |
| `cache/` | Cache subsystem (large, multi-tier) | — |
| `cache/backends/` | Raw storage backends | `BaseBackend`, `MemoryBackend`, `RedisBackend`, `S3Backend` |
| `cache/dataframe/` | DataFrame-specific tiered cache | `DataFrameCache`, `BuildCoordinator`, `CircuitBreaker`, `Coalescer`, `Warmer` |
| `cache/integration/` | High-level cache orchestration | `DataFrameCache`, `FreshnessCoordinator`, `StalenessCoordinator`, `MutationInvalidator`, `HierarchyWarmer`, `CacheProviderFactory` |
| `cache/models/` | Cache data models | `CacheEntry`, `EntryType`, `FreshnessStamp`, `CacheMetrics`, `CacheSettings` |
| `cache/policies/` | Freshness and coalesce policies | `FreshnessPolicy`, `StalenessPolicy`, `HierarchyPolicy` |
| `cache/providers/` | Provider composition | `TieredCacheProvider`, `UnifiedTaskStore` |
| `clients/` | Thin resource clients (leaf packages) | `TasksClient`, `ProjectsClient`, `SectionsClient`, `UsersClient`, `WorkspacesClient`, `WebhooksClient`, etc. |
| `clients/data/` | `autom8_data` satellite service client | `DataServiceClient`, endpoint modules (`batch`, `export`, `insights`, `reconciliation`, `simple`) |
| `core/` | Shared utilities (leaf package) | `EntityRegistry`, `EntityDescriptor`, `EntityType`, `SystemContext`, `ConcurrencyUtils`, `RetryUtils` |
| `dataframes/` | DataFrame layer (Polars-based analytics) | `DataFrameBuilder`, `SectionDataFrameBuilder`, `ProgressiveProjectBuilder`, `SchemaRegistry` |
| `dataframes/builders/` | DataFrame build strategies | `DataFrameBuilder`, `ProgressiveProjectBuilder`, `SectionDataFrameBuilder` |
| `dataframes/extractors/` | Task-to-row extractors | `BaseExtractor`, `UnitExtractor`, `ContactExtractor` |
| `dataframes/models/` | Row models and schema | `TaskRow`, `UnitRow`, `ContactRow`, `DataFrameSchema`, `ColumnDef`, `SchemaRegistry` |
| `dataframes/resolver/` | Custom field resolver | `CustomFieldResolver`, `DefaultCustomFieldResolver`, `NameNormalizer` |
| `dataframes/schemas/` | Built-in schema definitions | `BASE_SCHEMA`, `UNIT_SCHEMA`, `CONTACT_SCHEMA`, `OFFER_SCHEMA`, etc. |
| `dataframes/views/` | DataFrame view helpers | `DataFrameView`, `CascadeView` |
| `lambda_handlers/` | AWS Lambda entry points | `cache_warmer`, `cache_invalidate`, `cloudwatch`, `checkpoint`, `workflow_handler`, `insights_export`, `conversation_audit` |
| `lifecycle/` | Entity lifecycle pipeline (4-phase) | `LifecycleEngine`, `CreationResult`, `CompletionResult`, `ReopenResult`, `WiringResult` |
| `metrics/` | Business metrics computation | `MetricRegistry`, `MetricDefinition`, `MetricComputer` |
| `metrics/definitions/` | Built-in metric definitions | `offer` metrics |
| `models/` | Pydantic v2 Asana resource models | `AsanaResource`, `Task`, `Project`, `Section`, `User`, `CustomField`, `Webhook`, `Goal`, `Portfolio` |
| `models/business/` | Domain business entity models | `Business`, `Unit`, `Contact`, `Offer`, `Process`, `Location`, `Hours`, `AssetEdit` + holder types |
| `models/business/detection/` | Entity type detection logic | `DetectionFacade`, tiers 1-4 |
| `models/business/matching/` | Fuzzy matching engine | `MatchingEngine`, `BlockingStrategy`, `Comparators` |
| `models/contracts/` | Cross-service contracts | `PhoneVertical` |
| `observability/` | Correlation IDs and decorators | `CorrelationContext`, `error_handler`, `generate_correlation_id` |
| `patterns/` | Reusable async/error patterns | `async_method`, `error_classification` |
| `persistence/` | Save orchestration layer (Unit of Work) | `SaveSession`, `HealingManager`, `CascadeExecutor`, `ActionExecutor` |
| `protocols/` | Protocol (interface) definitions for DI | `AuthProvider`, `CacheProvider`, `LogProvider`, `ObservabilityHook`, `DataFrameProvider`, `ItemLoader` |
| `query/` | Query engine (compiled predicates over DataFrames) | `QueryEngine`, `PredicateCompiler`, `QueryFetcher`, `RowsRequest`, `AggregateRequest` |
| `resolution/` | Field value resolution strategies | `FieldResolver`, `ResolutionContext`, `UniversalStrategy` |
| `search/` | Search service over cached DataFrames | `SearchService`, `SearchResult` |
| `services/` | Service layer orchestration | `EntityQueryService`, `UniversalResolutionStrategy`, `SectionService`, `TaskService`, `EntityService`, `GidLookup`, `DiscoveryService` |
| `transport/` | HTTP transport wrapping autom8y-http | `AsanaHttpClient`, `AdaptiveSemaphore`, `ResponseHandler`, `ConfigTranslator` |

**Hub packages** (imported by many): `core/`, `protocols/`, `models/`, `settings.py`, `config.py`

**Leaf packages** (few or no internal imports): `_defaults/`, `models/`, `models/business/detection/`, `models/business/matching/`, `core/`, `cache/backends/`

## Layer Boundaries

The codebase has a clear layered architecture:

```
Layer 0: Entrypoint / Lambda / API
  src/autom8_asana/entrypoint.py
  src/autom8_asana/api/main.py
  src/autom8_asana/lambda_handlers/

Layer 1: Service / Strategy (orchestration)
  src/autom8_asana/services/
  src/autom8_asana/automation/
  src/autom8_asana/lifecycle/

Layer 2: Domain Logic (SDK surface)
  src/autom8_asana/client.py  (AsanaClient facade)
  src/autom8_asana/clients/   (resource clients)
  src/autom8_asana/persistence/
  src/autom8_asana/query/
  src/autom8_asana/resolution/
  src/autom8_asana/dataframes/
  src/autom8_asana/metrics/

Layer 3: Infrastructure / Support
  src/autom8_asana/transport/
  src/autom8_asana/cache/
  src/autom8_asana/auth/
  src/autom8_asana/observability/

Layer 4: Shared Primitives (no internal imports)
  src/autom8_asana/models/
  src/autom8_asana/protocols/
  src/autom8_asana/core/
  src/autom8_asana/settings.py
  src/autom8_asana/config.py
  src/autom8_asana/exceptions.py
```

**Import directions observed:**

- `api/` -> `services/` -> `client.py` -> `clients/` -> `transport/`
- `client.py` -> `cache/integration/factory` -> `cache/backends/`
- `services/universal_strategy.py` -> `services/dynamic_index.py` -> `cache/integration/`
- `services/query_service.py` -> `dataframes/models/registry.py` -> `core/entity_registry.py`
- `query/engine.py` -> `query/compiler.py`, `query/join.py` -> `dataframes/models/registry.py`
- `persistence/session.py` -> `persistence/pipeline.py` -> `clients/*`
- `automation/engine.py` -> `automation/context.py` -> `persistence/models.py`
- `lifecycle/engine.py` -> `lifecycle/creation.py`, `lifecycle/wiring.py`, `lifecycle/sections.py`

**Boundary-enforcement patterns:**

1. `protocols/` contains only `Protocol` definitions -- no implementations -- preventing tight coupling between consumers.
2. All cross-cutting dependencies (auth, cache, log) are injected at construction time via `BaseClient.__init__` parameters.
3. `TYPE_CHECKING` guards are used extensively to avoid circular imports (e.g., `client.py` type-checks `AutomationEngine`, `SearchService`, `UnifiedTaskStore` but imports them lazily).
4. `core/system_context.py` maintains a reset registry for singleton clearing during tests, and `settings.py` self-registers via `register_reset(reset_settings)`.
5. The `_defaults/` package provides standalone implementations so that the SDK works without the full platform SDK stack (e.g., `EnvAuthProvider` for token-based auth without `autom8y-auth`).

**Circular import avoidance:**
- `dataframes/` imports in `__init__.py` must not import from `core/entity_registry.py` (which happens to import back through `builders -> config -> entity_registry`). Path resolution in `entity_registry.py` is deferred to runtime via `importlib.import_module`.
- `client.py` uses `E402` exception in ruff config for delayed imports.

## Entry Points and API Surface

### Dual-Mode Entrypoint

`src/autom8_asana/entrypoint.py` is the container entry point:
- **ECS mode** (no `AWS_LAMBDA_RUNTIME_API` env var): Bootstraps business models via `models.business._bootstrap.bootstrap()`, then starts `uvicorn` serving `autom8_asana.api.main:create_app`.
- **Lambda mode** (has `AWS_LAMBDA_RUNTIME_API`): Passes the handler path (argv[1]) to `awslambdaric.main()`.

### FastAPI Application

`src/autom8_asana/api/main.py:create_app()` builds the FastAPI app:

**Middleware stack** (outer to inner):
1. `CORSMiddleware` (if `cors_origins_list` configured)
2. `SlowAPIMiddleware` (rate limiting via `slowapi`)
3. `RequestLoggingMiddleware`
4. `RequestIDMiddleware` (sets X-Request-ID)
5. `MetricsMiddleware` (from `autom8y_telemetry.instrument_app()`, wraps all)

**Registered routes:**

| Router | Path prefix / purpose |
|---|---|
| `health_router` | `/health`, `/ready`, `/health/deps` |
| `users_router` | Users endpoint |
| `workspaces_router` | Workspaces endpoint |
| `dataframes_router` | DataFrame export/query |
| `tasks_router` | Task CRUD |
| `projects_router` | Project operations |
| `sections_router` | Section operations |
| `internal_router` | Internal/admin operations |
| `resolver_router` | Entity resolver (GID lookup by field) |
| `query_router` | `/rows`, `/aggregate`, and deprecated `POST /{entity_type}` |
| `admin_router` | Admin operations |
| `webhooks_router` | Asana webhook management |
| `workflows_router` | Automation workflow triggers |
| `entity_write_router` | Entity mutation operations |
| `section_timelines_router` | Section timeline queries |

### AWS Lambda Handlers

`src/autom8_asana/lambda_handlers/`:
- `cache_warmer.py` -- warm entity caches from S3
- `cache_invalidate.py` -- cache invalidation trigger
- `cloudwatch.py` -- CloudWatch metrics emission
- `checkpoint.py` -- checkpoint writes for long-running builds
- `workflow_handler.py` -- automation workflow dispatch
- `insights_export.py` -- export workflow for analytics
- `conversation_audit.py` -- audit workflow

### SDK Entry Point

`src/autom8_asana/client.py:AsanaClient` is the primary user-facing object:
- Constructed with optional `token`, `workspace_gid`, `auth_provider`, `cache_provider`, `log_provider`, `config`, `observability_hook`.
- Lazy-initializes resource clients via `threading.Lock` double-checked locking.
- Properties: `.tasks`, `.projects`, `.sections`, `.custom_fields`, `.users`, `.workspaces`, `.webhooks`, `.teams`, `.attachments`, `.tags`, `.goals`, `.portfolios`, `.stories`, `.batch`, `.search`, `.unified_store`, `.automation`.
- Methods: `save_session()`, `warm_cache_async()`, `warm_cache()`, `close()`, async/sync context manager.

### Exported Protocols (Key Interfaces)

`src/autom8_asana/protocols/`:
- `AuthProvider` -- `get_secret(key: str) -> str`
- `CacheProvider` -- `get/set/delete`, `get_versioned/set_versioned`, `get_batch/set_batch`, `warm`, `check_freshness`, `invalidate`, `is_healthy`, `get_metrics`
- `LogProvider` -- logging abstraction
- `ObservabilityHook` -- metrics/tracing hook
- `DataFrameProvider` -- `get_dataframe_async(entity_type, project_gid)`
- `ItemLoader` -- generic item loading abstraction
- `MetricsEmitter` -- metric emission interface

## Key Abstractions

### 1. `AsanaClient` -- `src/autom8_asana/client.py`
The SDK facade. All resource access flows through this object. Thread-safe via per-client locks. Supports both sync and async usage. Wires together all providers at construction time.

### 2. `AsanaResource` -- `src/autom8_asana/models/base.py`
Base Pydantic v2 model for all Asana API responses. Config: `extra="ignore"` (forward compatibility), `populate_by_name=True`, `str_strip_whitespace=True`. All models extend this. Key child: `Task`, `Project`, `Section`, `User`, `CustomField`, `Webhook`, `Goal`, `Portfolio`.

### 3. `EntityDescriptor` / `EntityRegistry` -- `src/autom8_asana/core/entity_registry.py`
Frozen dataclass holding all metadata for one business entity type. `EntityRegistry` is a module-level singleton providing O(1) lookup by name, project GID, or `EntityType` enum. The single source of truth for entity knowledge: schema paths, extractor paths, row model paths, cache TTLs, join keys, holder relationships. Currently registers 17 entity descriptors (business, unit, contact, offer, asset_edit, process, location, hours + 9 holder types).

### 4. `Settings` / `get_settings()` -- `src/autom8_asana/settings.py`
Pydantic-settings singleton. Composed of sub-settings: `AsanaSettings`, `CacheSettings`, `RedisSettings`, `S3Settings`, `PacingSettings`, `RateLimitSettings`, `S3RetrySettings`, `WebhookSettings`, `DataServiceSettings`, `ObservabilitySettings`, `RuntimeSettings`. Use `get_settings()` for singleton access, `reset_settings()` for test cleanup.

### 5. `CacheProvider` Protocol -- `src/autom8_asana/protocols/cache.py`
Structural typing protocol defining the cache contract. Three implementations: `NullCacheProvider` (testing), `InMemoryCacheProvider` (development), `RedisCacheProvider` (production). Includes both simple key-value (`get/set/delete`) and advanced versioned operations (`get_versioned/set_versioned`, batch operations, freshness checks).

### 6. `DataFrameCache` -- `src/autom8_asana/cache/integration/dataframe_cache.py`
Tiered cache for Polars DataFrames. Two tiers: Memory (hot) -> Progressive/S3 (cold). Implements `DataFrameCacheProtocol`. Includes `BuildCoordinator` (prevents duplicate builds), `CircuitBreaker` (auto-disables on repeated failures), `Coalescer` (merges concurrent build requests).

### 7. `SaveSession` -- `src/autom8_asana/persistence/session.py`
Unit of Work context manager for batched Asana mutations. Tracks entity changes via `session.track()`, executes deferred `commit_async()` / `commit()`. Handles dependency ordering via `action_ordering.py`, partial failure via `PartialSaveError`, cascade operations via `CascadeExecutor`. After commit, optionally fires `AutomationEngine.evaluate_async()`.

### 8. `BaseClient` -- `src/autom8_asana/clients/base.py`
Base class for all 13+ resource clients. Holds references to `AsanaHttpClient`, `AsanaConfig`, `AuthProvider`, `CacheProvider`, `LogProvider`. Provides cache helper pattern: check-before-HTTP, store-on-miss.

### 9. `AsanaHttpClient` -- `src/autom8_asana/transport/asana_http.py`
Thin wrapper over `autom8y_http.Autom8yHttpClient`. Handles Asana-specific response unwrapping (`{"data": ...}` envelope). Accepts shared `TokenBucketRateLimiter`, `CircuitBreaker`, `ExponentialBackoffRetry` instances (created once in `AsanaClient.__init__`, shared across all sub-clients).

### 10. `QueryEngine` / `PredicateCompiler` -- `src/autom8_asana/query/engine.py`, `src/autom8_asana/query/compiler.py`
`QueryEngine` orchestrates filtered row retrieval from DataFrame cache. Accepts `DataFrameProvider` protocol for loose coupling. `PredicateCompiler` compiles `RowsRequest` filter expressions into Polars expression trees. Supports `RowsRequest` and `AggregateRequest` via `RowsResponse` and `AggregateResponse`.

### Design Patterns

**Descriptor-driven registry**: `EntityDescriptor` in `src/autom8_asana/core/entity_registry.py` -- all DataFrame layer consumers (schema registry, extractor factory, join key resolver, cascading field registry) are driven from a single descriptor definition, eliminating hardcoded match/case branches.

**Lazy initialization with double-checked locking**: All resource clients in `AsanaClient` use the pattern:
```python
if self._tasks is not None:
    return self._tasks
with self._tasks_lock:
    if self._tasks is None:
        self._tasks = TasksClient(...)
return self._tasks
```

**Deferred import pattern (circular avoidance)**: `TYPE_CHECKING` guards defer imports; lazy imports inside methods for circular-import-prone code (e.g., `client.py` imports `AutomationEngine` inside `__init__`).

**SDK-only imports enforcement**: `ruff` `TID251` rule bans direct `loguru`, `structlog`, `httpx` imports, routing all usages through `autom8y_log`, `autom8y_http` platform SDKs.

## Data Flow

### 1. SDK Read Path (API call with cache)

```
User code -> AsanaClient.tasks.get_async("gid")
  -> TasksClient.get_async()
    -> BaseClient._cache.get_versioned(key, EntryType.TASK)
      -> HIT: return deserialized Task
      -> MISS: AsanaHttpClient.get("/tasks/{gid}")
                -> autom8y_http.Autom8yHttpClient (rate limiter -> circuit breaker -> retry -> HTTP)
                -> Asana API response {"data": {...}}
                -> AsanaResponseHandler.unwrap_response()
                -> Task.model_validate(data)
                -> BaseClient._cache.set_versioned(key, CacheEntry)
                -> return Task
```

### 2. DataFrame Query Path

```
HTTP POST /rows  ->  api/routes/query.py:query_rows()
  -> services/query_service.py:EntityQueryService.query_rows_async()
    -> services/universal_strategy.py:UniversalResolutionStrategy._get_dataframe()
      -> cache/integration/dataframe_cache.py:DataFrameCache.get_async()
        -> Memory tier: dict lookup
        -> S3/Progressive tier: dataframes/storage.py
        -> MISS: dataframes/builders/progressive.py:ProgressiveProjectBuilder
                  -> clients/tasks.py (paginated Asana API calls)
                  -> dataframes/extractors/*.py: task -> row
                  -> polars.DataFrame construction
      -> query/engine.py:QueryEngine.execute_rows()
        -> query/compiler.py:PredicateCompiler (Polars expressions)
        -> optional: query/join.py (cross-entity joins)
        -> RowsResponse with filtered rows
```

### 3. Save/Mutation Path

```
User code -> SaveSession.track(entity)
  -> entity field mutation
  -> SaveSession.commit_async()
    -> persistence/action_ordering.py (dependency sort)
    -> persistence/pipeline.py (batch execution)
      -> batch/client.py:BatchClient.execute_async()
        -> AsanaHttpClient.post("/batch")
        -> Asana Batch API (up to 10 operations/request)
    -> persistence/cache_invalidator.py (invalidate affected entries)
    -> AutomationEngine.evaluate_async(save_result, client) [if automation enabled]
      -> automation/engine.py: evaluate registered rules
        -> automation/workflows/*.py: execute workflow
          -> optional: automation/events/emitter.py: emit events
```

### 4. Cache Warming Path (Lambda)

```
Lambda trigger -> lambda_handlers/cache_warmer.py
  -> cache/integration/hierarchy_warmer.py:HierarchyWarmer
    -> EntityRegistry.warmable_entities() [sorted by warm_priority]
    -> For each entity: DataFrameBuilder.build_async()
      -> clients/tasks.py (paginated fetch with pacing)
        -> ASANA_PACING_* settings control backpressure
      -> dataframes/extractors/*.py
      -> cache/integration/dataframe_cache.py:put_async()
        -> Progressive tier (S3 storage via dataframes/storage.py)
        -> Memory tier
```

### 5. Settings / Config Flow

```
Environment variables
  -> settings.py:Settings (Pydantic Settings parsing with prefixes)
    -> AsanaSettings (ASANA_*)
    -> CacheSettings (ASANA_CACHE_*)
    -> RedisSettings (REDIS_*)
    -> S3Settings (ASANA_CACHE_S3_*)
    -> PacingSettings (ASANA_PACING_*)
    -> RuntimeSettings (ASANA_RUNTIME_*)
  -> get_settings() singleton
  -> AsanaClient(config=AsanaConfig()) for SDK config
    -> transport/config_translator.py:ConfigTranslator
      -> rate_limiter_config, circuit_breaker_config, retry_config
  -> api/config.py:get_settings() for API-layer settings
```

### 6. Webhook / Automation Event Path

```
Asana webhook event -> POST /webhooks/inbound (api/routes/webhooks.py)
  -> webhook token validation (WEBHOOK_INBOUND_TOKEN)
  -> lifecycle/webhook.py: determine event type
  -> lifecycle/engine.py:LifecycleEngine.handle_transition_async()
    -> Phase 1: lifecycle/creation.py (create entity if needed)
    -> Phase 2: lifecycle/config.py (configure sections)
    -> Phase 3: lifecycle/init_actions.py (run init actions)
    -> Phase 4: lifecycle/wiring.py (wire holder relationships)
  -> AutomationEngine.evaluate_async() -> rules -> workflows
```

## Knowledge Gaps

1. `src/autom8_asana/api/lifespan.py` was not read in detail -- startup/shutdown sequence within FastAPI lifespan not fully traced.
2. `src/autom8_asana/api/startup.py` and `src/autom8_asana/api/dependencies.py` not read -- exact dependency injection wiring for request-scoped `AsanaClient` not documented.
3. `src/autom8_asana/models/business/detection/` (tiers 1-4) not read in depth -- the multi-tier detection algorithm is not fully mapped.
4. `src/autom8_asana/services/resolver.py` and `src/autom8_asana/resolution/strategies.py` not read in detail -- resolution strategy cascade is partially documented.
5. `src/autom8_asana/clients/data/client.py` not read in depth -- the `autom8_data` satellite service integration shape is not fully documented.
6. No `cmd/` or `internal/` directories exist (this is Python, not Go) -- the Go-oriented criteria references were adapted appropriately.
