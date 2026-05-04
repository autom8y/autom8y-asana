---
domain: architecture
generated_at: "2026-05-04T12:48Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "20ef7952"
confidence: 0.92
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
| `settings.py` | `Settings` + `get_settings()` — global pydantic-settings singleton (~50 env vars, `@lru_cache`) |
| `errors.py` | Top-level error types: `AsanaError`, `RateLimitError`, `ServerError`, `TimeoutError`, `InsightsServiceError` |

### Package Inventory

**`_defaults/`** (4 files) — Platform default providers: `auth.py` (`EnvAuthProvider`), `cache.py`, `log.py` (`DefaultLogProvider`), `observability.py` (`NullObservabilityHook`).

**`api/`** (11 direct files + 4 sub-packages) — FastAPI application layer. Hub package. Key files:
- `main.py` — `create_app()` factory: mounts all 22 routers, wires middleware, builds OpenAPI spec with 3 security schemes + OAuth2 scope pilot
- `lifespan.py` — startup/shutdown context manager: 13-step initialization sequence (see Data Flow §5)
- `models.py` — Re-exports fleet-standard `SuccessResponse`, `ErrorResponse`, `ErrorDetail`, `PaginationMeta` from `autom8y_api_schemas`; adds `ExportsSuccessResponse` typed variant with field-level examples (added `20ef7952`)
- `client_pool.py` — `ClientPool` for per-token `AsanaClient` resilience (IMP-19)
- `dependencies.py` — FastAPI DI: `AuthContextDep`, `EntityServiceDep`, `RequestId`, `DataServiceClient` injection
- `fleet_query_adapter.py` — Translates FleetQuery DSL → EntityQueryService kwargs
- `middleware/` — `core.py` (RequestLoggingMiddleware), `idempotency.py` (DynamoDB/InMemory/Noop stores)
- `preload/` — `progressive.py` (parallel project warm-up with resume), `legacy.py`, `constants.py`

**`api/routes/`** (26 files) — Route handlers. Notable:
- `tasks.py`, `projects.py`, `sections.py`, `users.py`, `workspaces.py` — CRUD routes (PAT auth)
- `dataframes.py` — Schema-based DataFrame extraction (PAT auth)
- `exports.py` — Phase-1 BI export pipeline, dual-mount `/v1/exports` + `/api/v1/exports`
- `_exports_helpers.py` — Predicate transformation helpers: `attach_identity_complete`, `dedupe_by_key`, `apply_active_default_section_predicate`, `_walk_predicate` visitor
- `fleet_query.py` — FleetQuery surface, dual-mount (S2S auth)
- `resolver.py`, `intake_*.py` — Entity resolution and intake pipeline (S2S)
- `query.py` — Query introspection + row/aggregate endpoints (S2S)
- `_security.py` — `pat_router`, `s2s_router` factory
- Co-located `*_models.py` files contain Pydantic request/response models shared with service layer (TENSION-002)

**`auth/`** (5 files) — `bot_pat.py`, `jwt_validator.py`, `dual_mode.py`, `service_token.py`, `audit.py`.

**`automation/`** (~25 files) — Automation engine + workflows + events + polling (APScheduler-based).

**`batch/`** (3 files) — `BatchClient`, `models.py`.

**`cache/`** (~35 files, 5 sub-packages) — Largest single subsystem. Tiered cache:
- `backends/` — `base.py` (template-method ABC), `memory.py`, `redis.py`, `s3.py`
- `models/` — entry, errors, freshness_stamp, freshness_unified (FreshnessState enum), metrics, mutation_event, settings, versioning, staleness_settings, completeness, events
- `policies/` — freshness_policy, staleness, hierarchy, coalescer, lightweight_checker
- `dataframe/` — `DataFrameCache`, build_coordinator, circuit_breaker, coalescer, decorator, factory, warmer; tiers (memory, progressive)
- `integration/` — 15 files including `dataframe_cache.py`, `factory.py`, loader, staleness/freshness coordinators, mutation_invalidator, hierarchy_warmer, force_warm, batch, dataframes, derived, stories, upgrader
- `providers/` — `tiered.py`, `unified.py`

**`clients/`** (~20 files + `data/` sub-package) — Asana API wrappers.
- `base.py` (`BaseClient`) — check-before-HTTP, store-on-miss cache pattern
- One file per resource: tasks, projects, sections, users, workspaces, attachments, custom_fields, goals, portfolios, stories, tags, teams, webhooks, etc.
- `data/` — `DataServiceClient` wraps autom8y-data HTTP API; sub-modules: `client.py`, `config.py`, `models.py`, `_cache.py`, `_metrics.py`, `_normalize.py`, `_pii.py`, `_policy.py`, `_response.py`, `_retry.py`; `_endpoints/` (batch, export, insights, reconciliation, simple)

**`core/`** (~13 files) — Cross-cutting utilities and registries:
- `entity_registry.py` — `EntityDescriptor` (frozen dataclass), `EntityRegistry` singleton (O(1) lookup by name/GID/`EntityType`)
- `project_registry.py` — Project GID constants (9 pipeline projects)
- `system_context.py` — `SystemContext.reset_all()`; xdist-worker-keyed `_reset_registry: dict[str, list[...]]` (updated `20ef7952`)
- concurrency, connections, creation, datetime_utils, entity_types, errors, field_utils, logging, registry, registry_validation, retry, scope, string_utils, timing, types

**`dataframes/`** (~45 files, 5 sub-packages) — Second-largest subsystem. Schema-driven:
- `builders/` — `base.py` (DataFrameBuilder ABC, `gather_with_limit` for max-25 concurrent), progressive (concrete), parallel_fetch, section, task_cache, freshness, hierarchy_warmer, cascade_validator (5%/20% null thresholds), post_build_validation, build_result, fields
- `schemas/` — base, business, contact, offer, unit, asset_edit, asset_edit_holder, process
- `extractors/` — base, default, business, contact, offer, unit, asset_edit, asset_edit_holder, process, schema
- `models/` — registry (SchemaRegistry singleton), schema (DataFrameSchema), task_row
- `resolver/` — protocol (CustomFieldResolver), cascading, coercer, default, mock, normalizer
- `views/` — cascade_view (CascadeViewPlugin), dataframe_view, cf_utils
- Direct: annotations, cache_integration, cascade_utils, errors, offline, section_persistence, storage, watermark

**`lambda_handlers/`** (13 files) — AWS Lambda handlers, each independently deployable: `cache_warmer`, `cache_invalidate`, `workflow_handler`, `insights_export`, `conversation_audit`, `payment_reconciliation`, `reconciliation_runner`, `push_orchestrator`, `pipeline_stage_aggregator`, `story_warmer`, `checkpoint`, `cloudwatch`, `timeout`.

**`lifecycle/`** (~13 files) — Task lifecycle state machine:
- `engine.py` (`LifecycleEngine`) — 4-phase pipeline: Create → Configure → Actions → Wire; fail-forward
- completion, creation, dispatch, init_actions, loop_detector, observation, observation_store, reopen, sections, seeding, webhook, webhook_dispatcher, wiring, config

**`metrics/`** (8 files + `definitions/`) — Business metrics:
- `compute.py` — CLI computation tool
- metric, registry, resolve (SectionIndex), expr, freshness, sla_profile, cloudwatch_emit
- `definitions/` — lifecycle, offer

**`models/`** (~20 files + `business/` sub-package) — Pydantic domain models:
- Direct: task (hub type), project, section, story, user, workspace, tag, webhook, goal, portfolio, team, attachment, custom_field, custom_field_accessor, base, common
- `business/` — Rich entity models (business, contact, offer, unit, process, asset_edit, activity, sections, section_timeline, dna, hours, location, videography, descriptors, mixins, patterns, reconciliation, registry, resolution, seeder, holder_factory, hydration)
- `business/fields.py` — `CascadingFieldDef`, `InheritedFieldDef`; migrated to `autom8y_log` in `20ef7952`
- `business/detection/` — 4-tier detection: facade (orchestrator), tier1 (project membership), tier2 (name pattern), tier3 (parent inference), tier4 (structure inspection), types, config
- `business/matching/` — Fellegi-Sunter probabilistic matching: engine, blocking, comparators (exact/fuzzy/TF-adjuster), normalizers, config, models
- `contracts/` — `phone_vertical.py`

**`observability/`** (3 files) — context, correlation, decorators.

**`patterns/`** (2 files) — `async_method.py`, `error_classification.py`.

**`persistence/`** (~16 files) — Entity write pipeline:
- `pipeline.py` (`SavePipeline`) — 4/5-phase save: Validate → Prepare → Execute → Actions → Confirm
- `session.py` (`SaveSession`) — user-facing entry
- executor (BatchExecutor), graph (DependencyGraph), actions, action_executor, action_ordering, cache_invalidator, cascade, errors, events, healing, holder_concurrency, holder_construction, holder_ensurer, models (AutomationResult), reorder, tracker, validation

**`protocols/`** (8 files) — Protocol (structural typing) interfaces; pure leaf:
- auth (AuthProvider), cache (CacheProvider, DataFrameCacheProtocol, WarmResult), dataframe_provider (DataFrameProvider), insights (InsightsProvider), item_loader (ItemLoader), log (LogProvider), metrics (MetricsEmitter), observability (ObservabilityHook)

**`query/`** (~15 files) — Composable query engine (S2S):
- `models.py` — `Op` StrEnum (13 operators incl. BETWEEN, DATE_GTE, DATE_LTE), `PredicateNode` discriminated union, `RowsRequest`, `AggregateRequest`, `RowsResponse`, `AggregateResponse`, `JoinSpec`
- `engine.py` (`QueryEngine`) — orchestrates cache access → schema validation → predicate compilation → section scoping → response shaping
- `compiler.py` (`PredicateCompiler`) — `OPERATOR_MATRIX`, `_compile_node`; P1-C-04 frozen
- fetcher, aggregator, join (P1-C-04 frozen), introspection, hierarchy, guards (`QueryLimits`, `predicate_depth`), errors, saved, temporal, timeline_provider, offline_provider, data_service_entities, formatters
- `__main__.py` — CLI dispatcher (10 subcommands: rows, aggregate, entities, fields, relations, sections, data-sources, timeline, list-queries, run); migrated to `autom8y_log` in `20ef7952`

**`reconciliation/`** (5 files) — engine, executor, processor, report, section_registry.

**`resolution/`** (7 files) — result (ResolutionResult), context (ResolutionContext), field_resolver, strategies, selection, write_registry (EntityWriteRegistry), budget.

**`search/`** (2 files) — models, service (SearchService).

**`services/`** (~22 files) — Business-logic services:
- `query_service.py` (`EntityQueryService`)
- `universal_strategy.py` (`UniversalResolutionStrategy`) — schema-driven O(1) resolution via `DynamicIndex`; replaces 4 per-entity strategies
- dataframe_service, entity_service, entity_context, discovery, dynamic_index (DynamicIndex, DynamicIndexCache)
- resolver, resolution_result, intake_resolve_service, intake_create_service, intake_custom_field_service
- section_service, section_timeline_service, task_service
- field_write_service, gid_lookup, gid_push, matching_service, vertical_backfill
- `errors.py` (`CacheNotWarmError`, `InvalidFieldError`, `ServiceError`)

**`transport/`** (5 files) — HTTP transport:
- `asana_http.py` (`AsanaHttpClient`) — wraps `autom8y_http.Autom8yHttpClient` with Asana-specific response unwrapping
- adaptive_semaphore (AIMD), config_translator, response_handler, sync

**`src/autom8_query_cli.py`** — Standalone CLI (`autom8-query` entrypoint) using direct httpx (TID251-exempt).

## Layer Boundaries

```
ENTRY POINTS ─ entrypoint.py, api/main.py, lambda_handlers/, query/__main__.py, autom8_query_cli.py
        ↓
API LAYER (api/) ─ Routes, middleware, DI, OpenAPI enrichment
        ↓
SERVICE LAYER (services/) ─ Business logic; lifecycle/, automation/, query/, persistence/
        ↓
DOMAIN LAYER (models/, dataframes/, resolution/, reconciliation/)
        ↓
INFRASTRUCTURE (clients/, transport/, cache/, batch/)
        ↓
CROSS-CUTTING (core/, protocols/, observability/, patterns/)
```

**Import direction**: `api/routes/*` → `services/*` → `clients/*` → `transport/*`. `services/*` → `models/`, `resolution/`, `dataframes/`. `cache/*` imported by clients, services, dataframes, api/lifespan. `protocols/` is a pure leaf.

**Layer boundary violation (TENSION-002, documented)**: Services import request/response models from `api/routes/*_models.py`:
- `services/intake_resolve_service.py` → `api/routes/intake_resolve_models.py`
- `services/intake_create_service.py` → `api/routes/intake_create_models.py`
- `services/intake_custom_field_service.py` → `api/routes/intake_custom_fields_models.py`
- `services/matching_service.py` → `api/routes/matching_models.py`

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

**FastAPI app factory** (`api/main.py:create_app`): builds idempotency store (DynamoDB/memory/noop, env-selected) → CORS config → JWTAuthConfig → `create_fleet_app()` → `register_exception_handlers()` → `register_validation_handler(service_code_prefix="ASANA")` → `SecurityHeadersMiddleware` → `fleet_error_handler` → `custom_openapi()` (injects security schemes, OAuth2 pilot, QUERY method candidates, Task schema, registry types, webhook definition).

### Router Inventory (22 routers, 4 dual-mounted)

| Router | Auth | Namespace |
|--------|------|-----------|
| `health_router` | none | `/health`, `/ready`, `/health/deps` |
| `users_router` | PAT | `/api/v1/users` |
| `workspaces_router` | PAT | `/api/v1/workspaces` |
| `dataframes_router` | PAT | `/api/v1/dataframes` |
| `tasks_router` | PAT | `/api/v1/tasks` |
| `projects_router` | PAT | `/api/v1/projects` |
| `sections_router` | PAT | `/api/v1/sections` |
| `section_timelines_router` | PAT | `/api/v1/offers` |
| `webhooks_router` | URL token | `/api/v1/webhooks` |
| `workflows_router` | PAT | `/api/v1/workflows` |
| `exports_router_v1` | PAT | `/v1/exports` (dual-mount) |
| `exports_router_api_v1` | PAT | `/api/v1/exports` (dual-mount) |
| `fleet_query_router_v1` | S2S | `/v1/query/entities` (dual-mount) |
| `fleet_query_router_api_v1` | S2S | `/api/v1/query/entities` (dual-mount) |
| `intake_resolve_router` | S2S | `/v1/intake/resolve/*` (must mount BEFORE resolver) |
| `resolver_router` | S2S | `/v1/resolve/{entity_type}` (wildcard) |
| `query_introspection_router` | S2S | `/v1/query` |
| `query_router` | S2S | `/v1/query/{entity_type}` (must mount AFTER fleet+exports) |
| `admin_router` | S2S | `/v1/admin` |
| `internal_router` | S2S | `/v1/internal` |
| `entity_write_router` | S2S | `/v1/entity-write` |
| `intake_custom_fields_router` | S2S | `/v1/intake/custom-fields` |
| `intake_create_router` | S2S | `/v1/intake/create` |
| `matching_router` | S2S | `/v1/matching` |

**CRITICAL mount order**: `fleet_query_router_*` and `exports_router_*` MUST mount BEFORE `query_router` because `query_router` uses wildcard `/v1/query/{entity_type}` that would shadow `/v1/exports` and `/v1/query/entities`. FastAPI matches in registration order.

### Lambda Handlers (13)

cache_warmer, cache_invalidate, workflow_handler, insights_export, conversation_audit, payment_reconciliation, reconciliation_runner, push_orchestrator, pipeline_stage_aggregator, story_warmer, checkpoint, cloudwatch, timeout.

### CLI Entrypoints

**`python -m autom8_asana.query`** (`query/__main__.py`) — 10 subcommands: rows, aggregate, entities, fields, relations, sections, data-sources, timeline, list-queries, run. `--live` flag uses `autom8y_core.TokenManager` for S2S JWT then hits HTTP API; offline default uses `OfflineDataFrameProvider`.

**`autom8-query`** (`src/autom8_query_cli.py`) — Standalone CLI using direct httpx (TID251-exempt).

## Key Abstractions

**`AsanaClient`** (`client.py`) — Main SDK facade. Aggregates all sub-clients, `BatchClient`, `SaveSession`, cache. Async context manager.

**`EntityDescriptor`** (`core/entity_registry.py`) — Frozen dataclass. `EntityRegistry` singleton: O(1) lookup by name/project GID/`EntityType`. Auto-discovers schemas via `schema_module_path`.

**`ResolutionResult`** (`services/resolution_result.py`) — Frozen dataclass: `gids`, `match_count`, `status_annotations`, `total_match_count`. Factories: `not_found()`, `from_gids()`, `from_gids_with_status()`, `error_result()`.

**`DataFrameBuilder`** (`dataframes/builders/base.py`) — Abstract base. `gather_with_limit()` for bounded parallel extraction (max 25 concurrent).

**`DataFrameSchema`** (`dataframes/models/schema.py`) — Defines column types, extractors, cascade configuration. Consumed by `SchemaRegistry`.

**`CacheProvider` protocol** (`protocols/cache.py`) — `get/set/delete`, `get_versioned/set_versioned`, `get_batch/set_batch`, `warm()`, `check_freshness()`, `invalidate()`, `is_healthy()`. Implemented by `S3CacheProvider`, `RedisCacheProvider`, `EnhancedInMemoryCacheProvider`, `TieredCacheProvider`.

**`SavePipeline`** (`persistence/pipeline.py`) — 4/5-phase save: Validate → Prepare → Execute → Actions → Confirm.

**`LifecycleEngine`** (`lifecycle/engine.py`) — 4-phase pipeline: Create → Configure → Actions → Wire. Routes DNC transitions. Fail-forward; hard fail only on Phase 1 creation failure.

**`UniversalResolutionStrategy`** (`services/universal_strategy.py`) — Schema-driven via `DynamicIndex`. Replaces 4 per-entity strategies. Status-aware (`AccountActivity`).

**`PredicateNode`** (`query/models.py`) — Pydantic v2 discriminated union over `Comparison | AndGroup | OrGroup | NotGroup`. `Op` StrEnum with 13 operators including BETWEEN, DATE_GTE, DATE_LTE.

**`CascadeViewPlugin`** (`dataframes/views/cascade_view.py`) — Cross-project field inheritance. `cascade_validator.py` enforces 5%/20% null thresholds.

**`ExportsSuccessResponse`** (`api/models.py`) — Typed `SuccessResponse[list[dict[str, Any]]]` variant with field-level examples for OpenAPI M-02_field_example metric. Added in `20ef7952`.

**`SystemContext`** (`core/system_context.py`) — Singleton reset coordination. `_reset_registry` is `dict[str, list[...]]` keyed by `PYTEST_XDIST_WORKER` for parallel xdist worker isolation (updated `20ef7952`).

**Design Patterns**:
- Protocol-based DI (`protocols/` as leaf)
- Discriminated union (`PredicateNode`)
- Singleton registry (`EntityRegistry`, `get_settings`, `SchemaRegistry`)
- Factory + environment detection (`CacheProviderFactory`)
- Dual-mount routers (exports, fleet_query)
- Co-located contract models (`api/routes/*_models.py`)
- Progressive/tiered caching (memory → S3 → None)
- Template method base class (`CacheBackendBase`)
- `_walk_predicate` generic recursive predicate visitor

### `_walk_predicate` — Recursive Predicate Visitor

**Location**: `src/autom8_asana/api/routes/_exports_helpers.py`

```python
def _walk_predicate(
    node: PredicateNode | None,
    *,
    on_comparison: Callable[[Comparison], _T],
    default: _T,
    combine: Callable[[list[_T]], _T],
) -> _T:
```

Consumers: `predicate_references_field`, `_contains_date_op`, `validate_section_values`. `_split_date_predicates` does NOT use it because it requires structural mutation.

### Frozen-Range Importers (P1-C-04)

Frozen modules per `exports.py` docstring:
- `query/engine.py:139-178,181` — `execute_rows` steps 6-9, aggregate logic
- `query/join.py` — full module
- `query/compiler.py:53-63,192-241` — `OPERATOR_MATRIX`, `_compile_node`, `_compile_comparison`

Importers verified at `20ef7952`:
- `api/routes/exports.py:66`
- `api/routes/query.py:38`
- `query/__init__.py` — re-exports
- `query/__main__.py:513,669` — lazy imports
- `services/query_service.py:236` — lazy import

## Data Flow

### 1. API Request Pipeline

```
HTTP request
  → SecurityHeadersMiddleware
  → JWTAuthMiddleware (excludes PAT routes, webhooks, health, docs)
  → IdempotencyMiddleware
  → RequestLoggingMiddleware
  → SlowAPI rate limiter
  → FastAPI route handler
  → DI: get_auth_context() [PAT or JWT dual-mode]
  → DI: get_*_service()
  → Service layer → Client layer → AsanaHttpClient → Asana API
```

### 2. DataFrame Build Pipeline

```
GET /api/v1/dataframes/{schema}
  → DataFrameService.get_dataframe(entity_type, project_gid)
  → DataFrameCache.get_async() [Memory → S3 progressive → None]
  → On miss: DataFrameBuilder
    → parallel_fetch (semaphore-limited, max 25 concurrent)
    → extractor chain (schema-dispatched)
    → cascade_validator.validate_cascade_fields_async()
    → safe_dataframe_construct()
    → post_build_validation
  → DataFrameCache.put_async()
  → Response (JSON or Polars-serialized, Accept negotiation)
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

### 4. Exports Pipeline (Phase 1)

```
POST /v1/exports or /api/v1/exports
  → exports handler
  → apply_active_default_section_predicate(predicate)
  → validate_section_values(predicate)
  → translate_date_predicates(predicate) [splits BETWEEN/DATE_GTE/DATE_LTE]
  → PredicateCompiler(cleaned_predicate).compile() [P1-C-04 frozen]
  → DataFrameBuilder → fetch + extract
  → attach_identity_complete(df) [P1-C-05]
  → filter_incomplete_identity(df, include=...)
  → dedupe_by_key(df, keys=...)
  → apply date_filter_expr (from ESC-1 split)
  → Response (Polars-serialized; json/csv/parquet)
```

### 5. Startup Initialization Sequence (`api/lifespan.py`)

1. `models/business/_bootstrap.bootstrap()` — registers entity types
2. `configure_logging()` — structured logging with OTel processors
3. `HTTPXClientInstrumentor().instrument()` — W3C traceparent on all httpx clients
4. `create_cache_provider()` → `app.state.cache_provider`
5. `ClientPool()` → `app.state.client_pool` (per-token resilience; DEF-005)
6. `_discover_entity_projects(app)` — workspace discovery; **fail-fast**
7. `validate_cross_registry_consistency()` — EntityRegistry vs EntityProjectRegistry divergence check
8. `_initialize_dataframe_cache(app)` — tiered cache setup
9. `_register_schema_providers()` — bridges SchemaRegistry to SDK registry
10. `_initialize_mutation_invalidator(app)` — wires cache invalidation into REST routes
11. `EntityWriteRegistry()` → `app.state.entity_write_registry`
12. `register_workflow_config()` ×2 (insights-export, conversation-audit)
13. `validate_cascade_ordering()` — fails fast on warm_priority graph conflicts
14. `asyncio.create_task(_preload_dataframe_cache_progressive)` — **background** cache warm (non-blocking)

`/health` returns 200 immediately; `/ready` returns 503 until cache warm.

### 6. Cache Invalidation Flow

```
POST /api/v1/webhooks/inbound
  → verify URL token (timing-safe vs ASANA_WEBHOOK_INBOUND_TOKEN)
  → background task: cache.invalidate(task_gid)
  → MutationInvalidator.invalidate_task(task_gid)
  → CacheProvider.invalidate(key, entry_types)
  → DataFrameCache.invalidate_project(project_gid)
  → DynamicIndexCache eviction
```

### Configuration Merge Points

```
pyproject.toml deps
  → env vars (~50 ASANA_* and AUTOM8Y_* vars)
  → Settings singleton (@lru_cache)
  → AsanaConfig (per-client)
  → DataServiceConfig
  → Lambda secrets via resolve_secret_from_env() [autom8y_config.lambda_extension]
```

## External Dependencies

| SDK | Package | Role |
|-----|---------|------|
| `autom8y_api_middleware` | `autom8y-api-middleware[rate-limit]>=0.3.0` | `create_fleet_app()`, CORS, JWT auth, rate limit |
| `autom8y_api_schemas` | `autom8y-api-schemas>=1.9.0` | Fleet envelope types: SuccessResponse, ErrorResponse, FleetQuery, OfficePhone |
| `autom8y_auth` | `autom8y-auth[observability]>=3.3.0` | JWT validation, exclude paths |
| `autom8y_config` | `autom8y-config>=2.0.1` | `resolve_secret_from_env()` (Lambda extension), `Config.from_env()` |
| `autom8y_http` | `autom8y-http[otel]>=0.6.0` | `Autom8yHttpClient`, `CircuitBreaker`, `ExponentialBackoffRetry` |
| `autom8y_cache` | `autom8y-cache>=0.4.0` | SDK cache protocol, schema versioning |
| `autom8y_log` | `autom8y-log>=0.5.6` | `get_logger()`, `configure_logging()`, `add_otel_trace_ids` |
| `autom8y_telemetry` | `autom8y-telemetry[aws,fastapi,otlp]>=0.6.1` | `trace_computation()`, `get_tracer()` |
| `autom8y_core` | `autom8y-core>=4.0.0,<5.0.0` | `TokenManager`, `Config` (query CLI live mode) |
| `autom8y_events` | `autom8y-events>=1.2.0,<2.0.0` | Optional; automation event transport |
| Asana API | Direct HTTP | All Asana resource operations via `AsanaHttpClient` |
| autom8y-data service | `DataServiceClient` | Insights, exports, reconciliation, batch |

## Defer-Watch Active Entries

| Entry | Scope | Status | Deadline |
|-------|-------|--------|----------|
| `DEFER-WS4-T3-2026-04-29` | `_defaults/log.py` stdlib logging migration; blocked on autom8y_log lacking stdlib `logging.Logger` compat | DEFERRED-pending-upstream | 2026-Q3 |
| `lockfile-propagator-prod-ci-confirmation` | Lockfile propagator path-resolution fix CI confirmation | DEFERRED-pending-natural-trigger | 2026-07-29 |

## Experiential Observations (from session history)

Cross-session corpus: 18 sessions (2026-03-02 to 2026-04-28), 15 initiative clusters. project-asana-pipeline-extraction Phase 0/1 carries the first explicit telos discipline (telos_deadline 2026-05-11). Cross-rite handoff patterns: review→10x-dev→sre (offer-data-gaps), hygiene↔10x-dev (project-crucible), rnd→10x-dev (asana-pipeline-extraction). Hot path artifacts cluster around `api/{models.py, routes/tasks.py}`, `clients/data/{client.py, config.py}`, `services/{gid_push.py, resolution_result.py, universal_strategy.py}`, `dataframes/builders/cascade_validator.py`.

The 13-step startup sequence in `lifespan.py` deliberately moves cache warm-up to a background task (step 14) to avoid blocking ECS health checks. The `validate_cascade_ordering()` call at step 13 is a fail-fast guard added post-hoc after misconfiguration caused silent warm-up ordering bugs.

The `autom8y_log` SDK migration (`20ef7952`) progresses two modules: `query/__main__.py` and `models/business/fields.py`. The `_defaults/log.py` migration remains blocked (DEFER-WS4-T3-2026-04-29). The `core/system_context.py` xdist isolation (`20ef7952`) enables true parallel test worker isolation without singleton state contamination.

## Knowledge Gaps

- `clients/data/_endpoints/` — 5 endpoint sub-modules (`batch.py`, `export.py`, `insights.py`, `reconciliation.py`, `simple.py`) not individually read; request/response patterns, PII handling (`_pii.py`), retry logic unknown
- `automation/polling/` — APScheduler integration patterns, trigger evaluator logic, config schema structure not traced
- `autom8_query_cli.py` — standalone CLI argument structure and exact behavior not read
- `reconciliation/` — processor and executor logic not read in depth
- `cache/dataframe/` — full `DataFrameCache` internal build/coalescing/circuit-breaker logic not deeply traced
- `models/business/matching/` — `comparators.py`/`normalizers.py` algorithm detail unknown
