---
domain: architecture
generated_at: "2026-04-29T23:15Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "80256049"
confidence: 0.90
format_version: "1.0"
update_mode: "incremental"
incremental_cycle: 1
max_incremental_cycles: 3
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
- `tasks.py`, `dataframes.py`, `exports.py` (Phase-1 BI export pipeline, dual-mount, LIVE post-PR38)
- `_exports_helpers.py` (predicate transformation helpers, co-located with exports handler)
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

The `*_models.py` files in `api/routes/` are de facto shared contract files. Known structural tension (see design-constraints TENSION-002).

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

**exports router** (`api/routes/exports.py`): LIVE post-PR38 (merge commit `80256049`). Dual-mounted at `/v1/exports` and `/api/v1/exports`. Mount order is load-bearing: must precede `query_router` in `api/main.py:431-441` because `query_router` uses wildcard `/v1/query/{entity_type}` that would shadow `/v1/exports` if mounted later (see design-constraints TENSION-009).

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

## Design Patterns

### `_walk_predicate` — Recursive Predicate Visitor (NEW — T-04b)

**Location**: `src/autom8_asana/api/routes/_exports_helpers.py`

**Introduced**: Commit `d9abbc1f` (T-04b, Sprint-3). Eliminates 3 duplicate `isinstance` ladder branches that previously appeared independently in `predicate_references_field`, `_contains_date_op`, and `_split_date_predicates`.

**Purpose**: Generic recursive traversal of the `PredicateNode` discriminated union (`Comparison | AndGroup | OrGroup | NotGroup`). Callers supply typed callbacks rather than re-implementing the isinstance dispatch logic themselves.

**Signature**:
```python
def _walk_predicate(
    node: PredicateNode | None,
    *,
    on_comparison: Callable[[Comparison], _T],
    default: _T,
    combine: Callable[[list[_T]], _T],
) -> _T:
```

**Dispatch logic**:
- `None` → returns `default`
- `Comparison` → calls `on_comparison(node)`
- `AndGroup` → recurses into `node.and_` children, combines with `combine`
- `OrGroup` → recurses into `node.or_` children, combines with `combine`
- `NotGroup` → recurses into `node.not_` single child, wraps in `combine`

**Consumers (3 helpers)**:

| Consumer | on_comparison | combine | Purpose |
|---|---|---|---|
| `predicate_references_field` | `lambda c: c.field == field_name` | `any` | Field presence check |
| `_contains_date_op` | `lambda c: _is_date_op(c.op)` | `any` | Date op detection |
| `validate_section_values` | `_validate_section_comparison` (raises on invalid) | `_exhaust` (no-op) | Section vocabulary guard |

Note: `_split_date_predicates` does NOT use `_walk_predicate` directly — it needs to reconstruct the cleaned `PredicateNode` tree while extracting date expressions, which requires structural mutation that the generic visitor cannot express without returning two values per node. It handles the isinstance dispatch manually.

**Property test**: `tests/unit/api/test_exports_helpers_walk_predicate_property.py` — 36 effective tests post-CHANGE-001 (Hypothesis-based).

**Cross-reference**: SCAR-DISCRIMINATOR-001 in `scar-tissue.md` — the visitor handles all four `PredicateNode` variants correctly when given pre-validated trees, but Pydantic's `_predicate_discriminator` (in `query/models.py:97-112`) is dict-only. Constructing `NotGroup(not_=AndGroup(...))` via model-instance kwargs falls through to `"comparison"` and fails Pydantic validation. The visitor is safe given valid input; the discriminator bug affects construction, not traversal.

### Frozen-Range Importer Topology

**Purpose**: Catalog of all files that import from the P1-C-04 frozen ranges in `query/`. Any modification to frozen ranges requires coordinating with all importers to assess blast radius.

**Frozen modules** (P1-C-04 per `api/routes/exports.py:14` docstring):
- `src/autom8_asana/query/engine.py:139-178,181` — `execute_rows` steps 6-9, aggregate logic
- `src/autom8_asana/query/join.py` — full module
- `src/autom8_asana/query/compiler.py:53-63,192-241` — `OPERATOR_MATRIX`, `_compile_node`, `_compile_comparison`

**Importer catalog** (verified at source_hash `6b303485`/`80256049`):
- `src/autom8_asana/api/routes/exports.py:65` — imports `PredicateCompiler` from `query.compiler` (NEW post-PR38, added by T-09, `d9abbc1f`)
- `src/autom8_asana/api/routes/query.py:38` — imports `QueryEngine` from `query.engine`
- `src/autom8_asana/query/__init__.py:17-18,38` — re-exports `PredicateCompiler`, `QueryEngine`, `execute_join`
- `src/autom8_asana/query/__main__.py:513,669` — lazy-imports `QueryEngine` in CLI subcommands
- `src/autom8_asana/services/query_service.py:236` — lazy-imports `strip_section_predicates` from `query.compiler`

**Cross-reference**: `design-constraints.md` FROZEN-RANGE-IMPORTERS-001 and EC-011. The `_walk_predicate` visitor in `_exports_helpers.py` does NOT import frozen ranges — it operates on `PredicateNode` from `query/models.py`, which is outside the frozen range.

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

### 4. Exports Pipeline (Phase 1 — LIVE post-PR38)

```
POST /v1/exports or /api/v1/exports
  → exports handler (api/routes/exports.py)
  → apply_active_default_section_predicate(predicate)  [DEFER-WATCH-3]
  → validate_section_values(predicate)                 [TDD §9.4 — InvalidSectionError → HTTP 400]
  → translate_date_predicates(predicate)               [ESC-1 — splits BETWEEN/DATE_GTE/DATE_LTE]
  → PredicateCompiler(cleaned_predicate).compile()     [query/compiler.py — P1-C-04 frozen]
  → DataFrameBuilder → fetch + extract
  → attach_identity_complete(df)                       [P1-C-05 single source-of-truth]
  → filter_incomplete_identity(df, include=...)        [opt-in suppression per PRD AC-6]
  → dedupe_by_key(df, keys=...)                        [most-recent-by-modified_at policy]
  → apply date_filter_expr (from ESC-1 split)
  → Response (Polars-serialized, eager pl.DataFrame only — P1-C-06)
```

### 5. Startup Initialization Sequence (`api/lifespan.py`)

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

### 6. Cache Invalidation Flow

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

## Defer-Watch Active Entries <!-- GLINT-010 | anchor: .know/defer-watch.yaml:1-79 | provenance: VERDICT-eunomia-final-adjudication-2026-04-29.md §4 -->

> Cross-reference summary of `.know/defer-watch.yaml` active entries as of 2026-04-29 close.
> Registry hygiene is OWNED by the `defer-watch-manifest` legomenon; this section provides
> discoverability for agents reading architecture.md without a separate defer-watch.yaml read.
> Both entries adjudicated KEEP-OPEN (EUN-005 audit, VERDICT §4). Watch-triggers fire 2026-05-29.

| Entry ID | Scope | Status | Watch Trigger | Deadline | Escalation |
|---|---|---|---|---|---|
| `DEFER-WS4-T3-2026-04-29` | `_defaults/log.py` migration to autom8y_log SDK; blocked on SDK lacking stdlib `logging.Logger` compat | DEFERRED-pending-upstream-SDK-enhancement | 2026-05-29 | 2026-Q3 | rnd-rite (autom8y-log SDK enhancement) |
| `lockfile-propagator-prod-ci-confirmation` | Production-CI green confirmation for lockfile-propagator path-resolution fix; Notify-Satellite-Repos step SKIPPED on last 2 post-merge runs (CodeArtifact 409 at earlier Publish step) | DEFERRED-pending-natural-trigger | 2026-05-29 | 2026-07-29 | 10x-dev rite (next SDK publish on fresh version) or sre rite |

**DEFER-WS4-T3-2026-04-29** unblock signal: autom8y-log SDK ships `StdlibLoggerAdapter` or equivalent stdlib-compat layer. Retry action: re-enter WS-4 T3, remove `pyproject.toml:272` TID251 exemption, replace `_defaults/log.py:81` stdlib call with SDK shim. Anchored at `scar-tissue.md` SCAR-LOG-001.

**lockfile-propagator-prod-ci-confirmation** close condition: a `sdk-publish-v2.yml` run where Publish step succeeds AND Notify-Satellite-Repos records `status=SUCCESS` for at least 1 satellite AND the uv-lock step inside that satellite completes without emitting `"Distribution not found at: file:///tmp/lockfile-propagator-..."`. If no natural trigger fires by 2026-07-29 deadline, re-engage with authority to push a no-op autom8y-config patch bump to force the confirmation. Anchored at `scar-tissue.md` SCAR-LP-001 and `ADR-lockfile-propagator-source-stubbing.md §Status`.

## Experiential Observations (from session history)

The cross-session corpus shows 18 wrapped sessions across 15 initiative clusters with project-asana-pipeline-extraction Phase 0/1 carrying the first explicit telos discipline (telos_deadline 2026-05-11). Cross-rite handoff patterns observed: review→10x-dev→sre (offer-data-gaps), hygiene↔10x-dev (project-crucible), rnd→10x-dev (asana-pipeline-extraction). Hot path artifacts cluster around `api/{models.py, routes/tasks.py}`, `clients/data/{client.py, config.py}`, `services/{gid_push.py, resolution_result.py, universal_strategy.py}`, `dataframes/builders/cascade_validator.py`.

The 13-step startup sequence in `lifespan.py` deliberately moves cache warm-up to a background task to avoid blocking ECS health checks — a defensive pattern from prior production failure.

Post-PR38 (merge commit `80256049`): `exports.py` route is LIVE, dual-mounted, and now the newest importer of `query/compiler.py` (via `PredicateCompiler` at line 65). The `_exports_helpers.py` module introduces the `_walk_predicate` visitor pattern — the first generic predicate-tree traversal abstraction in this codebase.

## Knowledge Gaps

- `clients/data/_endpoints/` — 5 endpoint sub-modules not individually read
- `models/business/matching/` — internals (`blocking.py`, `comparators.py`, `normalizers.py`) not fully read
- `automation/polling/` — APScheduler integration patterns unknown
- `cache/dataframe/` — full `DataFrameCache` implementation not deeply traced
- `reconciliation/` — processor and executor logic not read in depth
- `autom8_query_cli.py` — exact CLI argument structure unknown
- `exports.py` observability — zero span/metric instrumentation; OBS-EXPORTS-001 named incident in `obs.md`; deadline 2026-06-15
