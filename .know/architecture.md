---
domain: architecture
generated_at: "2026-04-28T21:55:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "8c58f930"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "62e88f60226e924b7fc0298605ce934fc6c36a3b4090ed524a4ef0d3cc4a05ff"
---

# Codebase Architecture

## Package Structure

The `autom8_asana` package lives under `src/autom8_asana/` and is a large Python SDK + FastAPI service. There are **33 top-level packages/sub-packages** organized into functional tiers.

### Root-Level Coordination Files

| File | Purpose |
|------|---------|
| `client.py` | `AsanaClient` facade — aggregates all sub-clients into a single SDK entry point |
| `entrypoint.py` | Dual-mode entrypoint (ECS/uvicorn vs Lambda/awslambdaric) — detects `AWS_LAMBDA_RUNTIME_API` env var |
| `config.py` | `AsanaConfig` — Pydantic settings for the SDK (PAT, workspace GID, base URL) |
| `settings.py` | `Settings` + `get_settings()` — global pydantic-settings singleton (~50 env vars) |
| `errors.py` | Top-level error types: `AsanaError`, `RateLimitError`, `ServerError`, `TimeoutError`, `InsightsServiceError` |

### Package Inventory

**`_defaults/`** (4 files) — Platform default providers. Thin wrapper classes satisfying protocols when no explicit injection is provided.

**`api/`** (11 direct files + 4 sub-packages) — FastAPI application layer. Hub package. Key files:
- `main.py` — `create_app()` factory: mounts all routers, wires middleware, builds OpenAPI spec
- `lifespan.py` — startup/shutdown context manager: 13-step initialization sequence
- `client_pool.py` — `ClientPool` for per-token `AsanaClient` resilience
- `middleware/` — `core.py`, `idempotency.py` (`DynamoDBIdempotencyStore`, `InMemoryIdempotencyStore`, `NoopIdempotencyStore`)
- `preload/` — `progressive.py`, `legacy.py`, `constants.py`

**`api/routes/`** (26 files) — Route handlers, one per domain. Notable:
- `tasks.py`, `dataframes.py`, `exports.py` (Phase-1 BI export pipeline, dual-mount)
- `fleet_query.py` (FleetQuery surface, dual-mount), `resolver.py`, `intake_*.py`
- Co-located `*_models.py` files contain Pydantic request/response models **shared with service layer** (anti-pattern: services import from `api.routes.*_models`)

**`auth/`** (5 files), **`automation/`** (~25 files, engine + workflows + events + polling), **`batch/`** (3 files).

**`cache/`** (~35 files, 5 sub-packages) — Largest single subsystem. Tiered cache: `backends/` (memory/redis/s3), `models/`, `policies/`, `dataframe/`, `integration/`.

**`clients/`** (~20 files + `data/` sub-package) — Asana API wrappers. One file per resource type. `clients/data/` contains `DataServiceClient` for autom8_data.

**`core/`** (~13 files) — Cross-cutting utilities and registries: `entity_registry.py`, `project_registry.py`, `entity_types.py`, `concurrency.py`, `retry.py`, etc.

**`dataframes/`** (~45 files, 5 sub-packages) — Second-largest subsystem. Schema-driven DataFrame construction: `builders/`, `schemas/`, `extractors/`, `models/`, `resolver/`, `views/`.

**`lambda_handlers/`** (12 files) — AWS Lambda function handlers, each deployable: `cache_warmer`, `cache_invalidate`, `workflow_handler`, `insights_export`, `conversation_audit`, `payment_reconciliation`, `reconciliation_runner`, `push_orchestrator`, `pipeline_stage_aggregator`, `story_warmer`, `checkpoint`, `cloudwatch`, `timeout`.

**`lifecycle/`** (~13 files) — Task lifecycle state machine. `engine.py` (`LifecycleEngine`, 4-phase: Create → Configure → Actions → Wire).

**`metrics/`** (6 files + `definitions/`) — Business metrics. `compute.py` is CLI computation tool.

**`models/`** (~20 files + `business/` sub-package) — Pydantic domain models. `business/` has rich entity models, detection (4-tier), matching engine, contracts.

**`observability/`** (3 files), **`patterns/`** (2 files), **`persistence/`** (~16 files: `pipeline.py` `SavePipeline` 4/5-phase, `session.py` `SaveSession`, `executor.py` `BatchExecutor`, `graph.py` `DependencyGraph`).

**`protocols/`** (8 files) — Protocol (structural typing) interfaces used as DI boundaries.

**`query/`** (~14 files) — Composable query engine (S2S): `models.py` (`Op` StrEnum, `PredicateNode` discriminated union), `engine.py`, `compiler.py`, `fetcher.py`, `aggregator.py`, `join.py`.

**`reconciliation/`** (5 files), **`resolution/`** (7 files: `result.py` `ResolutionResult`, `context.py`, `field_resolver.py`, `strategies.py`, `selection.py`, `write_registry.py`, `budget.py`).

**`search/`** (2 files), **`services/`** (~22 files — business-logic services).

**`transport/`** (5 files) — HTTP transport: `asana_http.py`, `adaptive_semaphore.py` (AIMD), `config_translator.py`, `response_handler.py`, `sync.py`.

**`src/autom8_query_cli.py`** — Standalone CLI script (`autom8-query` entrypoint) using direct httpx (intentionally not the platform SDK).

## Layer Boundaries

```
┌─ ENTRY POINTS ─ entrypoint.py, api/main.py, lambda_handlers/, autom8_query_cli.py
        ↓
┌─ API LAYER (api/) ─ Routes, middleware, DI, OpenAPI enrichment
        ↓
┌─ SERVICE LAYER (services/) ─ Business logic; lifecycle/, automation/, query/, persistence/
        ↓
┌─ DOMAIN LAYER (models/, dataframes/, resolution/, reconciliation/)
        ↓
┌─ INFRASTRUCTURE (clients/, transport/, cache/, batch/)
        ↓
└─ CROSS-CUTTING (core/, protocols/, observability/, patterns/)
```

**Import direction**: `api/routes/*` → `services/*` → `clients/*` → `transport/*`. `services/*` → `models/`, `resolution/`, `dataframes/`. `cache/*` imported by `clients/`, `services/`, `dataframes/`, `api/lifespan.py`. `protocols/` is a leaf — imported widely, imports nothing internal.

**Layer boundary violation (documented)**: Several `services/*.py` import request/response models from `api/routes/*_models.py`:
- `services/intake_resolve_service.py` → `api/routes/intake_resolve_models.py`
- `services/intake_create_service.py` → `api/routes/intake_create_models.py`
- `services/intake_custom_field_service.py` → `api/routes/intake_custom_fields_models.py`
- `services/matching_service.py` → `api/routes/matching_models.py`

The `*_models.py` files in `api/routes/` are de facto shared contract files. Known structural tension (see design-constraints).

**Hub packages**: `core/entity_registry.py`, `protocols/cache.py`, `settings.py`, `models/task.py`, `api/models.py`, `cache/integration/factory.py`.

**Leaf packages**: `core/` utilities (timing, string_utils, datetime_utils, errors), `protocols/*`, `models/base.py`, `patterns/async_method.py`.

## Entry Points and API Surface

### Primary Entry Points

**ECS mode (uvicorn)**:
```
entrypoint.py:main()
  → run_ecs_mode()
  → models/business/_bootstrap.bootstrap()
  → uvicorn.run("autom8_asana.api.main:create_app", factory=True)
```

**Lambda mode (awslambdaric)**:
```
entrypoint.py:main()
  → run_lambda_mode(handler)
  → awslambdaric.main()
```
Handler paths: `autom8_asana.lambda_handlers.{name}.handler`.

**FastAPI app factory** (`api/main.py:create_app`): builds idempotency store → `create_fleet_app()` → `register_exception_handlers()` → `register_validation_handler(service_code_prefix="ASANA")` → `SecurityHeadersMiddleware` → `fleet_error_handler` → `custom_openapi()`.

### Router Inventory (22 routers, 2 dual-mounted)

22 routers covering health, tasks, projects, sections, users, workspaces, dataframes, exports (dual-mount), fleet_query (dual-mount), webhooks, workflows, section_timelines, resolver, intake_resolve, query (+ introspection), admin, internal, entity_write, intake_custom_fields, intake_create, matching.

### Lambda Handlers (12)

`cache_warmer`, `cache_invalidate`, `workflow_handler`, `insights_export`, `conversation_audit`, `payment_reconciliation`, `reconciliation_runner`, `push_orchestrator`, `pipeline_stage_aggregator`, `story_warmer`, `checkpoint`, `cloudwatch`, `timeout`.

### CLI Entrypoint

`autom8-query` (from `pyproject.toml` scripts) → `src/autom8_query_cli.py:main()`.

## Key Abstractions

**`AsanaClient`** (`client.py`) — Main SDK facade. Aggregates all sub-clients, `BatchClient`, `SaveSession`, cache. Async context manager. All sub-clients share `AsanaHttpClient` + `CacheProvider` injected at construction.

**`EntityDescriptor`** (`core/entity_registry.py`) — Frozen dataclass capturing entity metadata. `EntityRegistry` singleton provides O(1) lookup by name, project GID, `EntityType`.

**`ResolutionResult`** (`services/resolution_result.py`) — Frozen dataclass: `gids: tuple[str, ...]`, `match_count`, `status_annotations`, `total_match_count`. Factory methods: `not_found()`, `from_gids()`, `from_gids_with_status()`, `error_result()`.

**`DataFrameBuilder`** (`dataframes/builders/base.py`) — Abstract base. Concrete in `progressive.py`. `gather_with_limit()` for bounded parallel extraction (max 25 concurrent).

**`DataFrameSchema`** (`dataframes/models/schema.py`) — Defines column types, extractors, cascade configuration. Consumed by `SchemaRegistry` (auto-discovered via `EntityDescriptor.schema_module_path`).

**`CacheProvider` protocol** (`protocols/cache.py`) — Structural typing interface: `get/set/delete`, `get_versioned/set_versioned`, `get_batch/set_batch`, `warm()`, `check_freshness()`, `invalidate()`, `is_healthy()`.

**`SavePipeline`** (`persistence/pipeline.py`) — 4/5-phase save: Validate → Prepare → Execute → Actions → Confirm. `SaveSession` is user-facing entry.

**`LifecycleEngine`** (`lifecycle/engine.py`) — 4-phase pipeline for new entity creation: Create → Configure → Actions → Wire. Routes DNC transitions. Fail-forward design.

**`UniversalResolutionStrategy`** (`services/universal_strategy.py`) — Schema-driven resolution using `DynamicIndex` for O(1) lookups. Replaces 4 per-entity strategies. Status-aware (`AccountActivity`: `ACTIVE`, `ACTIVATING`). Sorts by `ACTIVITY_PRIORITY`. Max concurrent index builds: 10.

**`PredicateNode`** discriminated union (`query/models.py`) — Pydantic v2 over `Comparison | AndGroup | OrGroup | NotGroup`. `Op` StrEnum with 13 operators including Sprint-2 additions (`BETWEEN`, `DATE_GTE`, `DATE_LTE`).

**`CascadeViewPlugin`** (`dataframes/views/cascade_view.py`) — Cross-project field inheritance via section-level cascade. Consumed by `cascade_validator.py` (5% warn, 20% error null thresholds).

**Design Patterns**: Protocol-based DI, Discriminated union (`PredicateNode`), Singleton registry (`EntityRegistry`, `get_settings`, `SchemaRegistry`), Factory + environment detection (`CacheProviderFactory`), Dual-mount routers (exports, fleet_query at both `/v1/` and `/api/v1/`), Co-located contract models (`api/routes/*_models.py`), Progressive/tiered caching.

## Data Flow

### 1. API Request Pipeline

```
HTTP request
  → SecurityHeadersMiddleware
  → JWTAuthMiddleware (excludes PAT routes)
  → IdempotencyMiddleware
  → RequestLoggingMiddleware
  → SlowAPI rate limiter
  → FastAPI route handler
  → DI: get_auth_context() [PAT or JWT]
  → DI: get_*_service()
  → Service layer
  → Client layer
  → AsanaHttpClient → Asana API
```

### 2. DataFrame Build Pipeline

```
GET /api/v1/dataframes/{schema}
  → DataFrameService.get_dataframe(entity_type, project_gid)
  → DataFrameCache.get_async() [Memory → S3 progressive → None]
  → On miss: DataFrameBuilder
    → parallel_fetch (batched, semaphore-limited)
    → extractor chain
    → cascade_validator.validate_cascade_fields_async()
    → safe_dataframe_construct()
    → post_build_validation
  → DataFrameCache.put_async()
  → Response (JSON or Polars-serialized)
```

### 3. Entity Resolution Pipeline (S2S)

```
POST /v1/resolve/{entity_type}
  → UniversalResolutionStrategy.resolve_batch(criteria, entity_type)
  → DynamicIndexCache.get_or_build(entity_type, project_gid)
  → On miss: DataFrameBuilder
  → DynamicIndex.lookup(criteria) → O(1)
  → ResolutionResult(gids, status_annotations, total_match_count)
  → AccountActivity filter (active_only=True)
  → Sort by ACTIVITY_PRIORITY
```

### 4. Startup Initialization Sequence (`api/lifespan.py`)

1. `configure_logging()`
2. `HTTPXClientInstrumentor().instrument()`
3. `create_cache_provider()` → `app.state.cache_provider`
4. `ClientPool()` → `app.state.client_pool`
5. `_discover_entity_projects(app)` [fail-fast]
6. `validate_cross_registry_consistency()`
7. `_initialize_dataframe_cache(app)`
8. `_register_schema_providers()`
9. `_initialize_mutation_invalidator(app)`
10. `EntityWriteRegistry()` → `app.state.entity_write_registry`
11. `register_workflow_config()` ×2
12. `validate_cascade_ordering()`
13. `asyncio.create_task(_preload_dataframe_cache_progressive)` [background]

`/health` returns 200 immediately; `/ready` returns 503 until cache warm.

### 5. Cache Invalidation Flow

```
POST /api/v1/webhooks/inbound
  → verify URL token (timing-safe)
  → background task: cache.invalidate(task_gid)
  → MutationInvalidator.invalidate_task(task_gid)
  → CacheProvider.invalidate(key, entry_types)
  → DataFrameCache.invalidate_project(project_gid)
  → DynamicIndexCache eviction
```

### Configuration Merge Points

Settings via `get_settings()` (cached singleton, `@lru_cache`). Override chain: `pyproject.toml` deps → env vars → `Settings` → `AsanaConfig` per-client → `DataServiceConfig` → Lambda secrets via `resolve_secret_from_env()` from `autom8y-config`.

## Experiential Observations (from session history)

The cross-session corpus shows 18 wrapped sessions across 15 initiative clusters with project-asana-pipeline-extraction Phase 0/1 carrying the first explicit telos discipline (telos_deadline 2026-05-11). Cross-rite handoff patterns observed: review→10x-dev→sre (offer-data-gaps), hygiene↔10x-dev (project-crucible), rnd→10x-dev (asana-pipeline-extraction). Hot path artifacts cluster around `api/{models.py, routes/tasks.py}`, `clients/data/{client.py, config.py}`, `services/{gid_push.py, resolution_result.py, universal_strategy.py}`, `dataframes/builders/cascade_validator.py`.

The 13-step startup sequence in `lifespan.py` deliberately moves cache warm-up to a background task to avoid blocking ECS health checks — a defensive pattern from prior production failure.

## Knowledge Gaps

- `clients/data/_endpoints/` — 5 endpoint sub-modules not individually read
- `models/business/matching/` — internals (`blocking.py`, `comparators.py`, `normalizers.py`) not fully read
- `automation/polling/` — APScheduler integration patterns unknown
- `cache/dataframe/` — full `DataFrameCache` implementation not deeply traced
- `reconciliation/` — processor and executor logic not read in depth
- `autom8_query_cli.py` — exact CLI argument structure unknown
