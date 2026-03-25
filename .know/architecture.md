---
domain: architecture
generated_at: "2026-03-25T01:56:07Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "c6bcef6"
confidence: 0.75
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Architecture

## Package Structure

**Language**: Python 3.12. Package manager: `uv`. Build backend: `hatchling`. Main package: `src/autom8_asana/` (443 `.py` files across 55+ subdirectories). CLI entry point: `autom8-query` mapped to `autom8_query_cli:main`.

The codebase is an async-first Asana API client and integration service. It runs as either an ECS/uvicorn HTTP API or Lambda handlers, both served from the same Docker image via a dual-mode entrypoint.

### Top-Level Package Map

| Directory | Files | Purpose |
|-----------|-------|---------|
| `src/autom8_asana/core/` | 19 | Entity registry, type definitions, shared utilities (leaf package — imports no siblings) |
| `src/autom8_asana/models/` | ~40 | Pydantic v2 Asana resource models (Task, Project, Section, User, Webhook, etc.) |
| `src/autom8_asana/models/business/` | ~25 | Domain business entity models (Business, Unit, Contact, Offer, AssetEdit) |
| `src/autom8_asana/models/business/detection/` | 8 | Tiered entity type detection (Tiers 1-4 + facade) |
| `src/autom8_asana/models/business/matching/` | 6 | Business entity fuzzy matching |
| `src/autom8_asana/protocols/` | 8 | Protocol (interface) definitions for DI boundaries |
| `src/autom8_asana/api/` | 42 | FastAPI application: app factory, middleware, dependency injection |
| `src/autom8_asana/api/routes/` | 20 | HTTP route handlers (15 routers) |
| `src/autom8_asana/api/preload/` | 4 | Cache preload strategies |
| `src/autom8_asana/services/` | 20 | Business-logic services: resolver, entity service, dynamic index |
| `src/autom8_asana/transport/` | 5 | HTTP transport: Asana HTTP wrapper, adaptive semaphore, sync wrapper |
| `src/autom8_asana/cache/` | ~25 | Multi-tier caching: Memory, S3, Redis backends |
| `src/autom8_asana/cache/dataframe/` | ~8 | DataFrame-specific cache: coalescer, circuit breaker, tiers |
| `src/autom8_asana/dataframes/` | ~35 | Polars DataFrame layer: schemas, builders, extractors, views, resolver |
| `src/autom8_asana/dataframes/schemas/` | 9 | Schema definitions per entity (base, unit, contact, offer, asset_edit, asset_edit_holder, business) |
| `src/autom8_asana/dataframes/builders/` | ~8 | DataFrame build pipeline (progressive, section-level, cascade validator) |
| `src/autom8_asana/dataframes/extractors/` | ~5 | Row extractors per entity type |
| `src/autom8_asana/persistence/` | ~20 | Unit-of-Work save pipeline (SaveSession, SavePipeline, 5-phase execution) |
| `src/autom8_asana/automation/` | ~15 | Automation rule engine, event emission, polling scheduler |
| `src/autom8_asana/automation/workflows/` | ~5 | Workflow implementations (conversation audit, insights, payment reconciliation) |
| `src/autom8_asana/lifecycle/` | 10 | Asana task lifecycle management (creation, completion, dispatch, seeding) |
| `src/autom8_asana/resolution/` | 7 | Entity resolution strategies, budget, context |
| `src/autom8_asana/metrics/` | 7 | Domain metrics registry, computation, expression engine |
| `src/autom8_asana/observability/` | 4 | Correlation context, decorators, log-trace linking |
| `src/autom8_asana/auth/` | 5 | JWT validation, PAT-based bot auth, dual-mode auth |
| `src/autom8_asana/search/` | 3 | Workspace task search |
| `src/autom8_asana/batch/` | ~3 | Asana Batch API client |
| `src/autom8_asana/clients/` | ~8 | Typed Asana data endpoint clients, name resolver |
| `src/autom8_asana/lambda_handlers/` | 8 | Lambda entry points: cache warmer, invalidator, workflow handler, CloudWatch, etc. |
| `src/autom8_asana/_defaults/` | 4 | Default provider implementations (env auth, secrets manager auth) |
| `src/autom8_asana/patterns/` | 3 | Shared patterns: async method wrapper, error classification |
| `src/autom8_asana/query/` | ~15 | Query engine: compiler, aggregator, join, timeline |

**Hub packages** (import from many siblings):
- `src/autom8_asana/api/main.py` — imports all 15 routers, middleware, lifespan
- `src/autom8_asana/api/lifespan.py` — imports startup helpers, preload, client pool
- `src/autom8_asana/persistence/session.py` — imports from tracker, pipeline, graph, actions, events, healing

**Leaf packages** (imported widely, import few siblings):
- `src/autom8_asana/core/` — imported by models, services, api; imports only `autom8y_log`
- `src/autom8_asana/protocols/` — imported by client, cache, services; defines Protocol classes only
- `src/autom8_asana/models/` (Asana resource types) — imported by services, api; imports only pydantic and core

---

## Layer Boundaries

The codebase follows a strict inward-import discipline. The layer model (from outermost to innermost):

```
Layer 1: api/routes/         (HTTP surface — depends on services, models, core)
Layer 2: api/                (app factory, middleware, DI — depends on services)
Layer 3: lambda_handlers/    (Lambda surface — depends on services, cache, automation)
Layer 4: services/           (business logic — depends on core, models, dataframes, cache)
Layer 5: persistence/        (save pipeline — depends on models, transport, batch)
Layer 6: automation/         (rule engine — depends on models, persistence, services)
Layer 7: lifecycle/          (task lifecycle — depends on models, services, persistence)
Layer 8: dataframes/         (Polars layer — depends on core, models, transport indirectly)
Layer 9: cache/              (caching — depends on core, models, protocols)
Layer 10: models/            (domain types — depends on core, protocols)
Layer 11: transport/         (HTTP client — depends on protocols, exceptions)
Layer 12: core/              (registry, types, utils — imports no siblings)
Layer 13: protocols/         (interface definitions — imports nothing from autom8_asana)
```

**Import direction evidence:**

- `src/autom8_asana/api/routes/resolver.py` imports from `core.entity_types`, `services.resolver`, `models.*` — never from `persistence/` or `automation/`
- `src/autom8_asana/services/universal_strategy.py` imports from `core.exceptions`, `models.business.activity`, `services.dynamic_index`, `settings` — never from `api/`
- `src/autom8_asana/persistence/session.py` imports from `persistence.*`, `transport.sync`, `clients.name_resolver`, `models.*` — never from `api/` or `automation/`
- `src/autom8_asana/core/entity_registry.py` imports from `autom8y_log` only (true leaf)
- `src/autom8_asana/protocols/__init__.py` imports only from sibling protocol files — no internal domain imports

**Boundary enforcement patterns:**

1. **`TYPE_CHECKING` guards**: Used extensively (e.g., `from autom8_asana.client import AsanaClient` under `if TYPE_CHECKING:`) to break circular imports at runtime while preserving type hints.
2. **Deferred imports**: `_bind_entity_types()` in `core/entity_registry.py` uses `from autom8_asana.core.types import EntityType` inside a function (not at module top) to avoid circular dependency between `core <-> models`.
3. **Lazy dataframe exports**: `__init__.py` uses `__getattr__` to defer `import autom8_asana.dataframes` until first use, so Polars is not loaded for consumers that only need the HTTP client.
4. **Protocol package**: `protocols/` defines abstract interfaces (`AuthProvider`, `CacheProvider`, `ItemLoader`, etc.) that both `services/` and `cache/` implement, avoiding direct coupling.

**Circular import mitigation**: `core/entity_registry.py` explicitly notes that schema/extractor modules must NOT import from `core.entity_registry` to avoid circular load-time imports. Path resolution is deferred to test time.

---

## Entry Points and API Surface

### Application Entry Points

**ECS (uvicorn) mode:**
```
python -m autom8_asana.entrypoint
  -> autom8_asana/entrypoint.py: main()
      -> run_ecs_mode()
          |-- models.business._bootstrap.bootstrap()   # model registration
          +-- uvicorn.run("autom8_asana.api.main:create_app", factory=True)
              +-- api/main.py: create_app()
                  |-- instrument_app() (autom8y_telemetry)
                  |-- Middleware stack (CORS, SlowAPI, RequestLogging, RequestID)
                  |-- 15 routers included
                  +-- register_exception_handlers()
```

**Lambda mode:**
```
python -m autom8_asana.entrypoint <handler_path>
  -> run_lambda_mode(handler)
      -> awslambdaric.main()
          -> Dispatches to lambda_handlers/{handler}.py
```

**CLI:**
```
autom8-query  ->  autom8_query_cli:main  ->  src/autom8_query_cli.py
```

### FastAPI Route Surface (15 routers)

| Router | Prefix | Auth | Tag |
|--------|--------|------|-----|
| `health_router` | `/health`, `/ready`, `/health/deps` | None | health |
| `users_router` | `/api/v1/users` | PAT Bearer | tasks |
| `workspaces_router` | `/api/v1/workspaces` | PAT Bearer | workspaces |
| `dataframes_router` | `/api/v1/dataframes` | PAT Bearer | dataframes |
| `tasks_router` | `/api/v1/tasks` | PAT Bearer | tasks |
| `projects_router` | `/api/v1/projects` | PAT Bearer | projects |
| `sections_router` | `/api/v1/sections` | PAT Bearer | sections |
| `internal_router` | `/v1/internal` | S2S JWT | internal |
| `intake_resolve_router` | `/v1/resolve/business`, `/v1/resolve/contact` | S2S JWT | intake-resolve |
| `resolver_router` | `/v1/resolve/{entity_type}` | S2S JWT | resolver |
| `query_router` | `/v1/query/rows`, `/v1/query/aggregate` | S2S JWT | query |
| `admin_router` | `/v1/admin` | S2S JWT | admin |
| `webhooks_router` | `/api/v1/webhooks/inbound` | Token query param | webhooks |
| `workflows_router` | `/api/v1/workflows` | PAT Bearer | workflows |
| `entity_write_router` | `/v1/entity-write` | S2S JWT | entity-write |
| `section_timelines_router` | `/api/v1/section-timelines` | PAT Bearer | offers |
| `intake_custom_fields_router` | `/v1/intake/custom-fields` | S2S JWT | intake-custom-fields |
| `intake_create_router` | `/v1/intake/create` | S2S JWT | intake-create |

**Auth model**: Two auth modes operate in parallel.
- `BearerAuth` (PAT): User-supplied Asana PAT; passed directly to Asana API. Used for resource endpoints (`/api/v1/*`).
- `ServiceJWT` (S2S JWT): Service-to-service JWT; validated against JWKS. Service uses a bot PAT for Asana calls. Used for internal endpoints (`/v1/*`).

### Lambda Handlers

Located in `src/autom8_asana/lambda_handlers/`:
- `cache_warmer.py` — Warms entity DataFrame caches from S3
- `cache_invalidate.py` — Invalidates cache entries
- `checkpoint.py` — Progressive build checkpointing
- `cloudwatch.py` — CloudWatch metric emission
- `conversation_audit.py` — Conversation audit workflow
- `insights_export.py` — Insights data export
- `payment_reconciliation.py` — Payment reconciliation workflow
- `workflow_handler.py` — Generic workflow dispatch

### Key Exported Interfaces (`__init__.py`)

The public SDK surface exported from `src/autom8_asana/__init__.py`:
- `AsanaClient` — Main HTTP client
- `AsanaConfig`, `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig` — Configuration
- `AuthProvider`, `CacheProvider`, `ItemLoader`, `LogProvider`, `ObservabilityHook` — Protocol interfaces
- Full Asana resource model set: `Task`, `Project`, `Section`, `User`, `Workspace`, `CustomField`, `Webhook`, etc.
- Dataframe layer (lazy-loaded): `DataFrameBuilder`, `ProgressiveProjectBuilder`, `SchemaRegistry`, etc.

---

## Key Abstractions

### 1. `EntityDescriptor` and `EntityRegistry`
**File**: `src/autom8_asana/core/entity_registry.py`
**Purpose**: Single source of truth for all entity type metadata. `EntityDescriptor` is a frozen dataclass holding identity, project GID, model class path, cache TTL, join keys, DataFrame schema/extractor paths, and category (ROOT/COMPOSITE/LEAF/HOLDER). `EntityRegistry` provides O(1) lookup by name, project GID, or `EntityType` enum. The singleton `_REGISTRY` is built at module load with import-time integrity validation (7 validation checks).
**Consuming packages**: `services/resolver.py`, `services/dynamic_index.py`, `api/startup.py`, `dataframes/builders/`, `cache/`

### 2. `EntityType` enum
**File**: `src/autom8_asana/core/types.py`
**Purpose**: Complete enumeration of all business entity types: BUSINESS (root), UNIT (composite), CONTACT/OFFER/PROCESS/LOCATION/HOURS (leaf), and 9 holder variants. Extracted from `models.business.detection.types` to break circular dependencies.
**Consuming packages**: `models/business/detection/`, `core/entity_registry.py`, `services/`, `dataframes/`

### 3. `AsanaHttpClient`
**File**: `src/autom8_asana/transport/asana_http.py`
**Purpose**: Thin wrapper over `autom8y_http.Autom8yHttpClient` (platform SDK). Handles Asana-specific response unwrapping (`data` envelope), error translation (`429 -> RateLimitError`, `5xx -> ServerError`), adaptive semaphore-based concurrency, and shared rate limiter/circuit breaker injection.
**Consuming packages**: `client.py`, `batch/`

### 4. `SaveSession` (Unit of Work)
**File**: `src/autom8_asana/persistence/session.py`
**Purpose**: Unit-of-Work pattern for batched Asana write operations. Wraps `ChangeTracker`, `DependencyGraph`, `SavePipeline`, `ActionExecutor`, `CacheInvalidator`, `EventSystem`, and `HealingManager`. Executes a 5-phase pipeline: VALIDATE -> PREPARE -> EXECUTE -> ACTIONS -> CONFIRM. Thread-safe via `RLock`.
**Consuming packages**: `api/routes/entity_write.py`, `lifecycle/`, `automation/`

### 5. `UniversalResolutionStrategy`
**File**: `src/autom8_asana/services/universal_strategy.py`
**Purpose**: Schema-driven GID resolution for any entity type. Replaces per-entity strategy classes. Uses `DynamicIndex` for O(1) multi-column key lookups. Accepts batch criteria (`[{phone, vertical}, ...]`) and resolves each to Asana task GIDs. Emits OTel spans.
**Consuming packages**: `api/routes/resolver.py`, `services/resolver.py`

### 6. `DynamicIndex` / `DynamicIndexCache`
**File**: `src/autom8_asana/services/dynamic_index.py`
**Purpose**: Generic in-memory lookup index over arbitrary column combinations from Polars DataFrames. `DynamicIndexKey` uses versioned cache key format (`idx1:col1=val1:col2=val2`). `DynamicIndexCache` is an LRU cache for index instances (TTL: 1 hour configurable).
**Consuming packages**: `services/universal_strategy.py`, `services/resolver.py`

### 7. `DataFrameSchema` / `ColumnDef` / `SchemaRegistry`
**File**: `src/autom8_asana/dataframes/models/schema.py`
**Purpose**: Type-safe column definitions for Polars DataFrames. `ColumnDef` describes a column name, dtype, nullable flag, and source (`cf:FieldName` for custom fields). `DataFrameSchema` is a registry key and column collection. `SchemaRegistry` auto-discovers schemas via `EntityDescriptor.schema_module_path` (dotted paths — no hardcoded imports).
**Consuming packages**: `dataframes/builders/`, `dataframes/extractors/`, `api/routes/dataframes.py`

### 8. `Business` / `BusinessEntity` hierarchy
**File**: `src/autom8_asana/models/business/business.py` (and `base.py`)
**Purpose**: Root domain model. `Business` (ROOT) has 7 holder types as lazy-loaded private attributes (`_contact_holder`, `_unit_holder`, etc.), 19 custom fields, and cascading field definitions. Holder classes (`DNAHolder`, `AssetEditHolder`, etc.) use the `HolderFactory` pattern.
**Consuming packages**: `models/business/hydration.py`, `services/`, `lifecycle/`, `automation/`

### 9. Detection Tier Chain
**Files**: `src/autom8_asana/models/business/detection/` (facade, tier1-4, config, types)
**Purpose**: 4-tier entity type detection from Asana task data.
- Tier 1: Project GID membership lookup (O(1), no API)
- Tier 2: Task name pattern matching
- Tier 3: Parent task inference
- Tier 4: Structure inspection (async, optional API call)
**Consuming packages**: `services/entity_service.py`, `models/business/hydration.py`, `api/routes/`

### 10. `AuthProvider` protocol and implementations
**Files**: `src/autom8_asana/protocols/auth.py`, `src/autom8_asana/_defaults/auth.py`, `src/autom8_asana/auth/`
**Purpose**: Protocol for PAT token resolution. Implementations: `EnvAuthProvider` (reads `ASANA_PAT`), `SecretsManagerAuthProvider` (reads from AWS Secrets Manager per ADR-VAULT-001), `JWTValidator` (S2S service JWT), `BotPAT` (bot user PAT for service endpoints).

### Design Patterns

**Registry pattern**: `EntityRegistry` (entity metadata), `SchemaRegistry` (DataFrame schemas), `ProjectRegistry` (project GID lookup), `MetricsRegistry` (metrics definitions).

**Protocol-based DI**: `protocols/` defines `AuthProvider`, `CacheProvider`, `ItemLoader`, `LogProvider`, `ObservabilityHook`, `DataFrameProvider`, `InsightsProvider`, `MetricsEmitter`. Consumers depend on protocols, not concrete implementations.

**Descriptor-driven layer**: `EntityDescriptor` drives four separate subsystems (SchemaRegistry, extractor creation, join key resolution, cascading field registry) through dotted-path references — no hardcoded match/case branches.

**HolderFactory pattern**: `src/autom8_asana/models/business/holder_factory.py` — holder types declared via class `HolderFactory[child_type="DNA"]` rather than hand-wiring each holder class.

**Cascade fields**: Business-level fields propagated down to leaf entities (Unit -> Offer, Business -> Contact) via `CascadingFields` inner class on models. Cascade validation runs post-build in `dataframes/builders/cascade_validator.py`.

**`if TYPE_CHECKING` guard**: Used in 50+ files to break runtime circular imports while preserving static typing.

---

## Data Flow

### 1. HTTP API Request Pipeline (PAT auth path)

```
Client request (Authorization: Bearer <PAT>)
  -> RequestIDMiddleware     (sets X-Request-ID)
  -> RequestLoggingMiddleware (structured log)
  -> SlowAPIMiddleware        (rate limit check)
  -> CORSMiddleware
  -> FastAPI route handler
      +-- dependencies.py: get_asana_client()
          +-- Creates AsanaClient(config=<from settings>) per-request (ADR-ASANA-007)
              +-- transport/asana_http.py: AsanaHttpClient
                  +-- autom8y_http.Autom8yHttpClient (W3C traceparent propagation)
                      -> Asana API
```

### 2. DataFrame Preload Pipeline (startup)

```
lifespan() startup
  -> _discover_entity_projects(app)      # Discover project GIDs from workspace
  -> _initialize_dataframe_cache(app)    # Create Memory+S3 DataFrameCache -> app.state
  -> _register_schema_providers()        # Register schemas with SDK autom8y_cache
  -> _preload_dataframe_cache_progressive()  # Background: warm cache from S3
      +-- api/preload/progressive.py
          +-- ProgressiveProjectBuilder (dataframes/builders/progressive.py)
              -> Asana API: fetch tasks section-by-section
              -> SectionPersistence: write each section to S3 as it completes
              -> cascade_validator: validate cascade-critical fields post-merge
              -> MemoryTier: load completed DataFrame into memory
```

### 3. Entity Resolution Pipeline (S2S path)

```
POST /v1/resolve/{entity_type}
  -> resolver.py route handler
      -> require_service_claims()        # Validate S2S JWT
      -> get_strategy(entity_type)       # Factory -> UniversalResolutionStrategy
      -> strategy.resolve_batch(criteria)
          +-- DynamicIndex.lookup(key)  # O(1) from in-memory DataFrame
              |-- Cache HIT: return immediately
              +-- Cache MISS:
                  -> DataFrameCache.get(entity_type)
                      |-- MemoryTier HIT: return DataFrame
                      +-- S3 (ProgressiveTier) HIT: deserialize, warm memory tier
                          +-- MISS: ProgressiveProjectBuilder.build() -> Asana API
```

### 4. Webhook Inbound Pipeline

```
POST /api/v1/webhooks/inbound?token=<secret>
  -> Token timing-safe comparison (hmac.compare_digest)
  -> Parse task JSON -> Task model
  -> BackgroundTasks.add_task():
      -> CacheInvalidator.invalidate([TASK, SUBTASKS, DETECTION] entry types)
      -> WebhookDispatcher.dispatch(task)   # V1: no-op log; GAP-03 scope
  -> Return 200 immediately (prevent Asana retries)
```

### 5. Save (Write) Pipeline

```
SaveSession context manager
  -> session.add(entity)      # ChangeTracker records diff
  -> session.commit()
      -> SavePipeline.execute()
          Phase 1: VALIDATE   - DependencyGraph cycle detection + field validation
          Phase 2: PREPARE    - Build PlannedOperations, assign temp GIDs
          Phase 3: EXECUTE    - BatchExecutor (CRUD via Asana Batch API)
          Phase 4: ACTIONS    - ActionExecutor (tags, projects, dependencies)
          Phase 5: CONFIRM    - Resolve temp GIDs -> real GIDs
      -> CacheInvalidator.invalidate(affected GIDs)
      -> EventSystem.emit() -> AutomationEngine.evaluate_async()
```

### 6. Configuration Merge Flow

```
Environment variables (ASANA_PAT, ASANA_CACHE_*, REDIS_*, API_HOST, etc.)
  -> settings.py: get_settings() -> pydantic-settings: Settings (cached singleton)
      |-- AsanaSettings (PAT, workspace GID, base URL)
      |-- CacheSettings (enabled, provider, TTL per entity type, circuit breaker thresholds)
      |-- RuntimeSettings (dataframe_cache_bypass, container_memory_mb, section_freshness_probe)
      +-- ... (12+ sub-settings groups)
```

---

## Knowledge Gaps

1. **`src/autom8_asana/query/` package** (15 files): The query engine (compiler, aggregator, join, temporal, hierarchy) was not read in detail. It appears to implement a structured query language over DataFrames for the `/v1/query/rows` and `/v1/query/aggregate` endpoints.
2. **`src/autom8_asana/metrics/` package**: Domain metrics computation (expr engine, metric registry, definitions/offer.py) not deeply read. Appears to compute business metrics from DataFrames.
3. **`src/autom8_asana/lifecycle/` package**: The 10-file task lifecycle orchestration (creation, completion, dispatch, seeding, sections, webhook wiring) was not fully traced.
4. **`src/autom8_asana/clients/data/`**: Data service client (for `autom8_data` external service, insights integration) not read.
5. **`src/autom8_asana/cache/backends/`**: Redis and in-memory backend implementations not examined.
6. **`src/autom8_asana/automation/polling/`**: Polling scheduler and YAML config schema not read.
7. **`src/autom8_query_cli.py`**: CLI entry point not read.
