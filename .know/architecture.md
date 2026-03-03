---
domain: architecture
generated_at: "2026-02-27T11:21:29Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "73b6e61"
confidence: 0.9
format_version: "1.0"
---

# Codebase Architecture

## Package Structure

The project is a Python 3.11+ package (`autom8y-asana`) located at `src/autom8_asana/` with 421 source files totaling ~120K lines. It is an async-first Asana API client and automation platform deployed as a FastAPI service on ECS and AWS Lambda.

### Top-Level Packages

| Package | Purpose | File Count | Key Types |
|---------|---------|------------|-----------|
| `api/` | FastAPI application, routes, middleware, dependencies, lifespan | ~25 | `create_app()`, route handlers, `AuthContext` |
| `api/routes/` | 15 route modules covering health, query, admin, webhooks, etc. | 15 | `query_router`, `health_router`, `resolver_router` |
| `api/preload/` | Cache warm-up at startup: legacy (fallback) and progressive | 4 | `_preload_dataframe_cache_progressive()` |
| `auth/` | Dual-mode authentication (JWT + PAT), bot PAT resolution | 4 | `AuthMode`, `detect_token_type()`, `get_bot_pat()` |
| `automation/` | Lifecycle automation, webhook dispatch, polling, event-based workflows | ~15 | `AutomationEngine`, `AutomationDispatch`, `PipelineConversionRule` |
| `automation/events/` | Event-driven automation handlers | 4 | Event handler classes |
| `automation/polling/` | Polling scheduler for dev mode | 4 | `StructuredLogger` |
| `automation/workflows/` | Workflow templates and execution | 4 | Workflow classes |
| `batch/` | Batch API client for parallelized Asana operations | 4 | `BatchClient`, `BatchRequest`, `BatchResult` |
| `cache/` | Multi-tier cache system (Memory, S3, Redis) | ~50 | `DataFrameCache`, `FreshnessPolicy`, `StalenessCoordinator` |
| `cache/backends/` | Storage backends: memory, redis, s3 | 4 | `MemoryBackend`, `RedisBackend`, `S3Backend` |
| `cache/dataframe/` | DataFrame-specific cache with circuit breaker, warming, coalescing | 8 | `BuildCoordinator`, `CacheWarmer`, `CircuitBreaker` |
| `cache/integration/` | Cache integration layer: factories, adapters, derived data, schema providers | 12 | `DataFrameCacheIntegration`, `MutationInvalidator`, `HierarchyWarmer` |
| `cache/models/` | Cache data models: entries, freshness, staleness, versioning | 10 | `FreshnessStamp`, `CacheEntry`, `StalenessSettings` |
| `cache/policies/` | Cache policies: freshness, staleness, hierarchy, coalescing | 5 | `FreshnessPolicy`, `StalenessPolicy`, `HierarchyPolicy` |
| `cache/providers/` | Cache provider implementations | 3 | `TieredProvider`, `UnifiedTaskStore` |
| `clients/` | Asana resource clients: tasks, projects, sections, etc. | ~15 | `TasksClient`, `ProjectsClient`, `SectionsClient` |
| `clients/data/` | DataServiceClient (autom8y-data integration): 7 focused modules | 10 | `DataServiceClient`, `_pii.py`, `_cache.py`, `_retry.py` |
| `core/` | Foundational utilities: concurrency, entity registry, types, field utils | 18 | `SystemContext`, `EntityRegistry`, `EntityDescriptor`, `gather_with_semaphore()` |
| `dataframes/` | DataFrame layer: builders, extractors, schemas, views, resolver | ~30 | `DataFrameBuilder`, `SchemaRegistry`, `UnitExtractor` |
| `dataframes/builders/` | DataFrame construction: progressive, section-level, cascade validation | 6 | `ProgressiveProjectBuilder`, `SectionDataFrameBuilder`, `CascadeValidator` |
| `dataframes/extractors/` | Row extraction from Asana tasks to typed rows | 6 | `BaseExtractor`, `UnitExtractor`, `ContactExtractor` |
| `dataframes/models/` | Row models, schemas, column definitions | 8 | `TaskRow`, `UnitRow`, `ContactRow`, `DataFrameSchema`, `ColumnDef` |
| `dataframes/resolver/` | Custom field resolution for extraction | 4 | `CustomFieldResolver`, `DefaultCustomFieldResolver` |
| `dataframes/schemas/` | Schema definitions per entity type | 6 | `BASE_SCHEMA`, `UNIT_SCHEMA`, `CONTACT_SCHEMA` |
| `dataframes/views/` | DataFrame view transformations | 4 | View functions |
| `lambda_handlers/` | AWS Lambda entry points | 8 | `cache_warmer`, `cache_invalidate`, `insights_export`, `workflow_handler` |
| `lifecycle/` | Lifecycle engine: transition handling, cascading sections, seeding, wiring | ~15 | `LifecycleEngine`, `EntityCreationService`, `CascadingSectionService` |
| `metrics/` | Business metrics computation | 6 | `compute_metric()`, `SectionClassifier`, metric definitions |
| `metrics/definitions/` | Individual metric definitions (MRR, ad spend, etc.) | 3 | Metric definition classes |
| `models/` | Pydantic v2 models for Asana resources | ~18 | `Task`, `Project`, `Section`, `User`, `AsanaResource` |
| `models/business/` | Business entity domain models | ~10 | `BusinessEntity`, `Unit`, `Contact`, `Offer` |
| `models/business/detection/` | Entity type detection via pattern matching | 4 | Detection classes |
| `models/business/matching/` | Business entity matching logic | 4 | Matching classes |
| `models/contracts/` | Data contract models | 4 | Contract types |
| `observability/` | Correlation context, error handling hooks | 4 | `CorrelationContext`, `error_handler` |
| `patterns/` | Shared code patterns: async method, error classification | 3 | `async_method`, `error_classification` |
| `persistence/` | SaveSession (Unit of Work), action execution, dependency graph, healing | 18 | `SaveSession`, `ActionExecutor`, `DependencyGraph`, `HealingManager` |
| `protocols/` | Protocol interfaces for DI boundaries | 9 | `AuthProvider`, `CacheProvider`, `DataFrameProvider`, `LogProvider` |
| `query/` | QueryEngine, CLI, offline provider, temporal queries, saved queries | 18 | `QueryEngine`, `PredicateCompiler`, `OfflineDataFrameProvider` |
| `resolution/` | Field resolution, write strategies, budget tracking | 7 | `FieldResolver`, `ResolutionStrategy`, `WriteBudget` |
| `search/` | Search service | 3 | `SearchService` |
| `services/` | Service layer: query, entity, resolver, field write, GID lookup | 16 | `EntityQueryService`, `EntityService`, `UniversalResolutionStrategy` |
| `transport/` | HTTP transport: Asana HTTP client, sync wrappers, adaptive semaphore | 6 | `AsanaHttpClient`, `sync_wrapper`, `AdaptiveSemaphore` |
| `_defaults/` | Default provider implementations for standalone usage | 4 | `EnvAuthProvider`, `DefaultLogProvider` |

### Hub Packages (High Import Count)

- `core/` -- Imported by nearly every package. Contains entity registry, types, field utils, system context.
- `models/` -- Imported by services, persistence, dataframes, API routes.
- `exceptions.py` -- Root exception hierarchy, imported by all layers.
- `protocols/` -- Interface definitions consumed by services, cache, and DI.
- `config.py` -- Central configuration, imported by API, clients, services.

### Leaf Packages (Minimal Internal Imports)

- `_defaults/` -- Self-contained default providers.
- `lambda_handlers/` -- Entry points that import from other packages but are not imported.
- `patterns/` -- Standalone utility patterns.
- `search/` -- Isolated search service.

## Layer Boundaries

The codebase follows a layered architecture with clear directional dependencies:

### Layer Model

```
Lambda Handlers / CLI
        |
    API Layer (FastAPI routes, middleware, dependencies)
        |
    Service Layer (query_service, entity_service, resolver, field_write)
        |
    Domain Layer (lifecycle, persistence/SaveSession, automation)
        |
    DataFrame Layer (builders, extractors, schemas, cache integration)
        |
    Core Layer (entity_registry, types, field_utils, system_context)
        |
    SDK Client Layer (AsanaClient, resource clients, transport)
        |
    Protocol Layer (auth, cache, log, observability interfaces)
```

### Import Direction

- **API routes** import from services, models, query engine, and dependencies
- **Services** import from core, models, cache, and clients (never from API)
- **Persistence (SaveSession)** imports from clients, models, core (never from API or services)
- **Lifecycle** imports from persistence, models, core (peer to persistence)
- **DataFrames** import from models, core, cache (never from services or API)
- **Core** imports only from protocols and external libraries
- **Protocols** have zero internal imports (leaf of the dependency tree)

### Circular Dependency Avoidance

The codebase has ~915 deferred imports (`from __future__ import annotations` + `TYPE_CHECKING` blocks) to break circular dependencies. Key patterns:

1. **TYPE_CHECKING guards**: Heavy use of `if TYPE_CHECKING:` blocks for type-only imports
2. **Protocol interfaces**: `protocols/` package provides DI boundaries
3. **String annotations**: `from __future__ import annotations` is standard in every file
4. **Deferred imports at function scope**: Used in `client.py`, `config.py`, `dependencies.py`, `resolver.py`
5. **Entity registry dotted-path resolution**: `_resolve_dotted_path()` avoids import-time circular deps

There are 6 known structural import cycles that remain. These are documented as deferred (trigger: production incident or greenfield rewrite). See `SI-3` in the debt ledger.

## Entry Points and API Surface

### HTTP API (FastAPI)

Entry point: `src/autom8_asana/api/main.py` -> `create_app()` factory.

The API serves 15 route groups:

| Router | Prefix | Auth | Purpose |
|--------|--------|------|---------|
| `health_router` | `/health`, `/ready` | None | Health checks, readiness |
| `query_router` | `/v1/query/` | S2S JWT | Entity queries: rows, aggregate, introspection |
| `dataframes_router` | `/v1/dataframes/` | PAT/JWT | DataFrame CRUD |
| `tasks_router` | `/v1/tasks/` | PAT | Task operations |
| `projects_router` | `/v1/projects/` | PAT | Project operations |
| `sections_router` | `/v1/sections/` | PAT | Section operations |
| `users_router` | `/v1/users/` | PAT | User operations |
| `workspaces_router` | `/v1/workspaces/` | PAT | Workspace operations |
| `resolver_router` | `/v1/resolver/` | S2S JWT | Entity resolution |
| `internal_router` | `/v1/internal/` | S2S JWT | Internal service endpoints |
| `admin_router` | `/v1/admin/` | S2S JWT | Cache admin, diagnostics |
| `webhooks_router` | `/v1/webhooks/` | mixed | Webhook management |
| `workflows_router` | `/v1/workflows/` | S2S JWT | Workflow automation |
| `entity_write_router` | `/v1/entities/` | S2S JWT | Entity field writes |
| `section_timelines_router` | `/v1/section-timelines/` | S2S JWT | Section timeline queries |

### CLI Entry Points

1. **Query CLI**: `python -m autom8_asana.query` or `autom8-query` (console_scripts)
   - Offline query engine using `OfflineDataFrameProvider` (reads S3 directly)
   - Subcommands: `rows`, `aggregate`, `entities`, `fields`, `relations`, `sections`, `timeline`, `list-queries`
   - CLI wrapper: `src/autom8_query_cli.py` sets env defaults before import

2. **Metrics CLI**: `python -m autom8_asana.metrics`
   - Business metric computation (MRR, ad spend, etc.)
   - Uses `OfflineDataFrameProvider` for S3 data access

### Lambda Handlers

- `cache_warmer.py` -- Scheduled cache warming
- `cache_invalidate.py` -- Cache invalidation events
- `insights_export.py` -- Export insights reports
- `conversation_audit.py` -- Audit conversation data
- `workflow_handler.py` -- Workflow automation triggers
- `checkpoint.py` -- Checkpoint operations
- `cloudwatch.py` -- CloudWatch integration

### SDK Client

`AsanaClient` (in `client.py`) is the main SDK entry point:
- 13 resource clients: tasks, projects, sections, users, workspaces, tags, stories, webhooks, goals, portfolios, teams, custom_fields, attachments
- Provider-based DI: `AuthProvider`, `CacheProvider`, `LogProvider`, `ObservabilityHook`
- Async context manager support
- `SaveSession` for batched write operations (Unit of Work pattern)
- `BatchClient` for parallel API calls

### Key Exported Interfaces

| Interface | Package | Consumers |
|-----------|---------|-----------|
| `AuthProvider` | `protocols/auth.py` | `AsanaClient`, `_defaults/auth.py`, `auth/` |
| `CacheProvider` | `protocols/cache.py` | `AsanaClient`, `cache/`, `api/lifespan.py` |
| `DataFrameProvider` | `protocols/dataframe_provider.py` | `QueryEngine`, `OfflineDataFrameProvider` |
| `LogProvider` | `protocols/log.py` | `AsanaClient`, `_defaults/log.py` |
| `ObservabilityHook` | `protocols/observability.py` | `AsanaClient`, telemetry integration |
| `MetricsEmitter` | `protocols/metrics.py` | Metrics subsystem |
| `InsightsProvider` | `protocols/insights.py` | Insights API |
| `ItemLoader` | `protocols/item_loader.py` | DataFrameBuilder |

## Key Abstractions

### EntityRegistry and EntityDescriptor

`core/entity_registry.py` is the single source of truth for entity metadata. `EntityDescriptor` (frozen dataclass) captures: name, project GID, schema path, extractor path, row model path, TTL, category, join keys, and more. The registry provides O(1) lookup by name, project GID, or `EntityType`. Four major consumers are descriptor-driven: SchemaRegistry, extractor creation, entity relationships, and cascading fields.

### SaveSession (Unit of Work)

`persistence/session.py` implements a Unit of Work pattern for batched Asana operations. It has 14 collaborators (documented as a Coordinator, NOT a god object -- do not decompose). It manages: change tracking, action building, dependency graph ordering, action execution, cache invalidation, and self-healing.

### QueryEngine

`query/engine.py` orchestrates filtered row retrieval. Composes: cache access via `DataFrameProvider` protocol, schema validation, predicate compilation (`PredicateCompiler`), section scoping, join execution, and response shaping. Decoupled from services layer via protocol.

### DataFrameBuilder and Extractors

`dataframes/builders/` construct Polars DataFrames from Asana tasks. `ProgressiveProjectBuilder` handles incremental building. Extractors (`BaseExtractor`, `UnitExtractor`, `ContactExtractor`) map Asana task data to typed row models (`TaskRow`, `UnitRow`, `ContactRow`).

### LifecycleEngine

`lifecycle/engine.py` handles state transitions in the business domain. Composed of: `EntityCreationService`, `CascadingSectionService`, `CompletionService`, `DependencyWiringService`, `ReopenService`, `AutoCascadeSeeder`. Configured via YAML (`config/lifecycle_stages.yaml`).

### DataFrameCache (Multi-Tier)

`cache/integration/dataframe_cache.py` provides the main cache interface. Backed by Memory -> S3 -> Redis tiers. Features: SWR (stale-while-revalidate), circuit breaker, build coalescing, freshness policy, staleness coordination.

### Pydantic v2 Models

All Asana resource models (`models/`) use Pydantic v2 with `from __future__ import annotations`. `AsanaResource` is the base class. Business entity models (`models/business/`) extend `Task` with domain-specific logic (detection, matching, cascading fields).

## Data Flow

### Request Processing (API)

```
HTTP Request
  -> RequestIDMiddleware (sets X-Request-ID)
  -> RequestLoggingMiddleware (structured logging)
  -> SlowAPIMiddleware (rate limiting)
  -> CORSMiddleware (preflight handling)
  -> Route Handler
    -> DI: get_auth_context() -> AuthContext (JWT or PAT mode)
    -> DI: per-request AsanaClient (per ADR-ASANA-007)
    -> Service layer (EntityQueryService, EntityService, etc.)
    -> Response
```

### DataFrame Cache Pipeline

```
Startup (lifespan):
  1. _discover_entity_projects() -- maps entity types to Asana project GIDs
  2. _register_schema_providers() -- registers per-entity schemas
  3. _initialize_dataframe_cache() -- creates cache infrastructure
  4. _preload_dataframe_cache_progressive() -- warms cache from S3

Runtime (query path):
  Request -> EntityQueryService -> UniversalResolutionStrategy._get_dataframe()
    -> Layer 1: Decorator-injected cache check
    -> Layer 2: DataFrameCache (Memory -> S3)
    -> Layer 3: Cache miss -> build fresh (self-refresh)
    -> Polars operations (filter, select, aggregate)
    -> Response
```

### Lifecycle Automation Pipeline

```
Asana Webhook -> AutomationDispatch.dispatch_async()
  -> LifecycleEngine.handle_transition_async()
    -> Stage config lookup (lifecycle_stages.yaml)
    -> Init actions (comment, entity creation, products check, etc.)
    -> CascadingSectionService (propagate section changes)
    -> DependencyWiringService (set up task dependencies)
    -> SaveSession.commit_async() (batch write to Asana)
```

### Offline Data Pipeline (CLI)

```
CLI invocation -> OfflineDataFrameProvider
  -> S3 paginated listing (boto3)
  -> Parquet file reading
  -> QueryEngine (same as API, different provider)
  -> Formatted output (table, json, csv)
```

## Knowledge Gaps

- The exact count of deferred imports per package was not audited file-by-file (estimated at ~915 based on prior analysis).
- The `automation/workflows/` package internals were not deeply explored.
- Lambda handler implementations beyond the file listing were not read in detail.
- The exact Redis cache backend usage pattern (vs. Memory + S3) was not traced through configuration.
