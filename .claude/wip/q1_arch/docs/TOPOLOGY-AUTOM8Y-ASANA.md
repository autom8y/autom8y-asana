# Topology Inventory: autom8y-asana

**Date**: 2026-02-18
**Review ID**: ARCH-REVIEW-1 (formalization)
**Commit**: `be4c23a` (main)
**Scope**: Single-repo analysis unit -- `autom8y-asana` (~111K LOC, 383 Python files, 27 packages)
**Classification**: Application + SDK hybrid (service + library)

---

## 1. Service / Module Catalog

### Unit Classification

| # | Package | Path (relative to `src/autom8_asana/`) | LOC | Classification | Role Description | Confidence |
|---|---------|----------------------------------------|-----|----------------|------------------|------------|
| 1 | `__init__` | `__init__.py` | 236 | **core** | Root re-exports, lazy DataFrame loading via `__getattr__` | High |
| 2 | `client` | `client.py` | 1,041 | **core** | `AsanaClient` facade -- primary SDK entry point | High |
| 3 | `config` | `config.py` | -- | **core** | Configuration loading (env vars, settings) | High |
| 4 | `settings` | `settings.py` | -- | **core** | Pydantic Settings model | High |
| 5 | `exceptions` | `exceptions.py` | -- | **core** | SDK exception hierarchy | High |
| 6 | `entrypoint` | `entrypoint.py` | 97 | **infrastructure** | Dual-mode dispatcher (ECS uvicorn / Lambda awslambdaric) | High |
| 7 | `api` | `api/` | 8,880 | **API** | FastAPI app factory, routes, middleware, lifespan, preload | High |
| 8 | `auth` | `auth/` | 667 | **infrastructure** | Authentication providers (PAT, JWT/S2S dual-mode) | High |
| 9 | `automation` | `automation/` | 9,318 | **domain** | Pipeline rules, seeding, events, polling, workflows | High |
| 10 | `batch` | `batch/` | 687 | **domain** | Batch operations against Asana API | High |
| 11 | `cache` | `cache/` | 15,658 | **infrastructure** | Multi-tier caching subsystem (Redis+S3 entity, Memory+S3 DataFrame) | High |
| 12 | `clients` | `clients/` | 11,245 | **integration** | Asana API clients (tasks, tags, sections, projects, etc.) | High |
| 13 | `core` | `core/` | 2,911 | **core** | Entity registry, exception tuples, timing, creation primitives | High |
| 14 | `dataframes` | `dataframes/` | 13,728 | **domain** | Polars DataFrames, builders, extractors, schemas, S3 persistence | High |
| 15 | `lambda_handlers` | `lambda_handlers/` | 1,977 | **infrastructure** | Cache warmer, cache invalidate, insights export, conversation audit | High |
| 16 | `lifecycle` | `lifecycle/` | 4,032 | **domain** | Lifecycle engine, creation, seeding, webhook handler | High |
| 17 | `metrics` | `metrics/` | 616 | **infrastructure** | Metrics collection (Prometheus) | High |
| 18 | `models` | `models/` | 15,356 | **domain** | Business entity models, detection (5 tiers), matching, hydration | High |
| 19 | `observability` | `observability/` | 343 | **infrastructure** | W3C trace propagation, log-trace correlation | High |
| 20 | `patterns` | `patterns/` | 444 | **core** | Reusable patterns (shared base classes) | High |
| 21 | `persistence` | `persistence/` | 8,137 | **domain** | SaveSession UoW, change tracking, cascade execution | High |
| 22 | `protocols` | `protocols/` | 610 | **core** | Protocol definitions (CacheProvider, AuthProvider, LogProvider, ItemLoader, ObservabilityHook) | High |
| 23 | `query` | `query/` | 1,935 | **domain** | Query engine, predicate AST compiler, guards, joins, aggregation | High |
| 24 | `resolution` | `resolution/` | 1,799 | **domain** | Entity resolution (GID lookup, hierarchy-aware resolution) | High |
| 25 | `search` | `search/` | 925 | **domain** | Search functionality | Medium |
| 26 | `services` | `services/` | 5,695 | **domain** | Query service, resolver, universal strategy, field write service | High |
| 27 | `transport` | `transport/` | 1,700 | **integration** | HTTP transport, instrumented Asana client | High |

### Classification Summary

| Classification | Count | Packages |
|----------------|-------|----------|
| **core** | 7 | `__init__`, `client`, `config`, `settings`, `exceptions`, `core`, `patterns`, `protocols` |
| **domain** | 10 | `automation`, `batch`, `dataframes`, `lifecycle`, `models`, `persistence`, `query`, `resolution`, `search`, `services` |
| **infrastructure** | 6 | `entrypoint`, `auth`, `cache`, `lambda_handlers`, `metrics`, `observability` |
| **integration** | 2 | `clients`, `transport` |
| **API** | 1 | `api` |
| **Total** | **27** | (includes `config` + `settings` counted as separate units per package map) |

### Deployment Boundaries

| Deployment Mode | Runtime | Entry Point | Packages Active |
|-----------------|---------|-------------|-----------------|
| **ECS** (API server) | uvicorn + FastAPI | `entrypoint.py` -> `run_ecs_mode()` -> `api.main:create_app` | All 27 |
| **Lambda** (cache warmer) | awslambdaric | `entrypoint.py` -> `run_lambda_mode()` -> `lambda_handlers.cache_warmer.handler` | core, cache, clients, models, dataframes, lambda_handlers, transport |
| **Lambda** (cache invalidate) | awslambdaric | `entrypoint.py` -> `run_lambda_mode()` -> `lambda_handlers.cache_invalidate.handler` | core, cache, clients, models, lambda_handlers, transport |
| **Lambda** (insights export) | awslambdaric | `entrypoint.py` -> `run_lambda_mode()` -> `lambda_handlers.insights_export.handler` | core, automation, clients, models, lambda_handlers, transport |
| **Lambda** (conversation audit) | awslambdaric | `entrypoint.py` -> `run_lambda_mode()` -> `lambda_handlers.conversation_audit.handler` | core, automation, clients, models, lambda_handlers, transport |

---

## 2. Tech Stack Inventory

### Language and Runtime

| Component | Technology | Version Constraint | Source | Confidence |
|-----------|-----------|-------------------|--------|------------|
| Language | Python | >=3.11 | `pyproject.toml` requires-python | High |
| Async runtime | asyncio | stdlib (3.11+) | Codebase-wide `async/await` | High |
| Type checking | mypy | >=1.0.0 | `pyproject.toml` [tool.mypy] strict=true | High |
| Linter/formatter | ruff | >=0.1.0 | `pyproject.toml` [tool.ruff] | High |

### Frameworks and Libraries

| Component | Technology | Version Constraint | Dependency Group | Confidence |
|-----------|-----------|-------------------|-----------------|------------|
| Models | Pydantic | >=2.0.0 | core | High |
| Settings | pydantic-settings | >=2.0.0 | core | High |
| DataFrames | Polars | >=0.20.0 | core | High |
| HTTP client | httpx | >=0.25.0 | core | High |
| API framework | FastAPI | >=0.109.0 | optional [api] | High |
| ASGI server | uvicorn | >=0.27.0 | optional [api] | High |
| Rate limiting | slowapi | >=0.1.9 | optional [api] | High |
| Structured logging | structlog | >=24.1.0 | optional [api] | High |
| Date handling | arrow | >=1.3.0 | core | High |
| Asana SDK | asana | >=5.0.3 | core | High |
| Redis | redis | >=5.0.0 | optional [redis] | High |
| Redis C parser | hiredis | >=2.0.0 | optional [redis] | High |
| AWS SDK | boto3 | >=1.42.19 | core (S3 progressive cache) | High |
| Lambda runtime | awslambdaric | >=2.2.0 | optional [lambda] | High |
| Scheduler | apscheduler | >=3.10.0 | optional [scheduler] | High |
| OpenTelemetry httpx | opentelemetry-instrumentation-httpx | >=0.42b0 | core | High |

### Platform Dependencies (autom8y-* packages)

| Package | Version Constraint | Registry | Purpose | Confidence |
|---------|-------------------|----------|---------|------------|
| autom8y-config | >=0.3.0 | CodeArtifact | Configuration management | High |
| autom8y-http | >=0.4.0 (with [otel]) | CodeArtifact | Instrumented HTTP transport | High |
| autom8y-cache | >=0.4.0 | CodeArtifact | Cache primitives, schema versioning | High |
| autom8y-log | >=0.5.5 | CodeArtifact | Structured logging | High |
| autom8y-core | >=1.1.0 | CodeArtifact | Core shared primitives | High |
| autom8y-telemetry | >=0.3.0 (with [fastapi]) | CodeArtifact | Platform observability (metrics, tracing) | High |
| autom8y-auth | >=1.1.0 (with [observability]) | CodeArtifact | JWT/S2S authentication | High |

### Build and Packaging

| Component | Technology | Configuration |
|-----------|-----------|---------------|
| Build backend | Hatchling | `pyproject.toml` [build-system] |
| Package manager | uv | `pyproject.toml` [tool.uv] with index-strategy |
| Private registry | AWS CodeArtifact | `autom8y-*` packages via `autom8y` index |
| Public registry | PyPI | Default index |

### Infrastructure-as-Code

| Component | Technology | Location | Confidence |
|-----------|-----------|----------|------------|
| Container | Docker | `/Dockerfile` (single image, dual-mode ECS/Lambda) | High |
| Compute (API) | AWS ECS | Referenced in `entrypoint.py`, deployment docs | High |
| Compute (async) | AWS Lambda | Referenced in `lambda_handlers/`, `entrypoint.py` | High |
| Cache (hot) | AWS ElastiCache (Redis) | Referenced in `cache/backends/redis.py` | High |
| Storage (cold) | AWS S3 | Referenced in `cache/backends/s3.py`, `dataframes/storage.py` | High |
| Monitoring | AWS CloudWatch | Referenced in `lambda_handlers/cloudwatch.py` | High |
| Scheduling | AWS EventBridge | Referenced in `lambda_handlers/insights_export.py` docstring | Medium |

### CI/CD

| Component | Technology | Location | Confidence |
|-----------|-----------|----------|------------|
| CI pipeline | GitHub Actions | `.github/workflows/test.yml` | High |
| Deployment dispatch | GitHub Actions | `.github/workflows/satellite-dispatch.yml` | High |
| Test runner | pytest | `pyproject.toml` [tool.pytest.ini_options] asyncio_mode=auto | High |

---

## 3. API Surface Map

### HTTP Endpoints (FastAPI Routes)

All routes registered in `src/autom8_asana/api/main.py:create_app()` via `app.include_router()`.

#### Health (unauthenticated)

Router prefix: (none -- root-level)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| GET | `/health` | Liveness probe | None | High |
| GET | `/health/ready` | Readiness probe (503 until cache warm) | None | High |
| GET | `/health/s2s` | S2S authentication dependency check | None | High |

#### Users (`/api/v1/users`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| GET | `/api/v1/users/me` | Get current authenticated user | PAT/JWT | High |
| GET | `/api/v1/users/{gid}` | Get user by GID | PAT/JWT | High |
| GET | `/api/v1/users` | List users in workspace | PAT/JWT | High |

#### Workspaces (`/api/v1/workspaces`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| GET | `/api/v1/workspaces` | List all workspaces | PAT/JWT | High |
| GET | `/api/v1/workspaces/{gid}` | Get workspace by GID | PAT/JWT | High |

#### Tasks (`/api/v1/tasks`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| GET | `/api/v1/tasks` | List tasks by project or section | PAT/JWT | High |
| GET | `/api/v1/tasks/{gid}` | Get task by GID | PAT/JWT | High |
| POST | `/api/v1/tasks` | Create a new task | PAT/JWT | High |
| PUT | `/api/v1/tasks/{gid}` | Update a task | PAT/JWT | High |
| DELETE | `/api/v1/tasks/{gid}` | Delete a task | PAT/JWT | High |
| GET | `/api/v1/tasks/{gid}/subtasks` | List subtasks of a task | PAT/JWT | High |
| GET | `/api/v1/tasks/{gid}/dependents` | List dependent tasks | PAT/JWT | High |
| POST | `/api/v1/tasks/{gid}/duplicate` | Duplicate a task | PAT/JWT | High |
| POST | `/api/v1/tasks/{gid}/tags` | Add tag to task | PAT/JWT | High |
| DELETE | `/api/v1/tasks/{gid}/tags/{tag_gid}` | Remove tag from task | PAT/JWT | High |
| POST | `/api/v1/tasks/{gid}/section` | Move task to section | PAT/JWT | High |
| PUT | `/api/v1/tasks/{gid}/assignee` | Set task assignee | PAT/JWT | High |
| POST | `/api/v1/tasks/{gid}/projects` | Add task to project | PAT/JWT | High |
| DELETE | `/api/v1/tasks/{gid}/projects/{project_gid}` | Remove task from project | PAT/JWT | High |

#### Projects (`/api/v1/projects`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| GET | `/api/v1/projects` | List projects by workspace | PAT/JWT | High |
| GET | `/api/v1/projects/{gid}` | Get project by GID | PAT/JWT | High |
| POST | `/api/v1/projects` | Create a new project | PAT/JWT | High |
| PUT | `/api/v1/projects/{gid}` | Update a project | PAT/JWT | High |
| DELETE | `/api/v1/projects/{gid}` | Delete a project | PAT/JWT | High |
| GET | `/api/v1/projects/{gid}/sections` | List sections in project | PAT/JWT | High |
| POST | `/api/v1/projects/{gid}/members` | Add members to project | PAT/JWT | High |
| DELETE | `/api/v1/projects/{gid}/members` | Remove members from project | PAT/JWT | High |

#### Sections (`/api/v1/sections`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| GET | `/api/v1/sections/{gid}` | Get section by GID | PAT/JWT | High |
| POST | `/api/v1/sections` | Create a new section | PAT/JWT | High |
| PUT | `/api/v1/sections/{gid}` | Update a section | PAT/JWT | High |
| DELETE | `/api/v1/sections/{gid}` | Delete a section | PAT/JWT | High |
| POST | `/api/v1/sections/{gid}/tasks` | Add task to section | PAT/JWT | High |
| POST | `/api/v1/sections/{gid}/reorder` | Reorder section within project | PAT/JWT | High |

#### DataFrames (`/api/v1/dataframes`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| GET | `/api/v1/dataframes/project/{gid}` | Get project tasks as dataframe | PAT/JWT | High |
| GET | `/api/v1/dataframes/section/{gid}` | Get section tasks as dataframe | PAT/JWT | High |

#### Webhooks (`/api/v1/webhooks`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| POST | `/api/v1/webhooks/inbound` | Receive inbound webhook from Asana | Asana HMAC | High |

#### Admin (`/v1/admin`, `include_in_schema=False`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| POST | `/v1/admin/cache/refresh` | Trigger cache refresh | S2S JWT | High |

#### Query (`/v1/query`, `include_in_schema=False`)

Unified router from `api/routes/query.py` (hygiene sprint commit f6e08e5 merged `query_v2.py` into `query.py`).

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| POST | `/v1/query/{entity_type}` | Query entities — deprecated, sunset 2026-06-01 | S2S JWT | High |
| POST | `/v1/query/{entity_type}/rows` | Query entity rows with composable predicates | S2S JWT | High |
| POST | `/v1/query/{entity_type}/aggregate` | Aggregate entity data with grouping | S2S JWT | High |

#### Resolver (`/v1/resolve`, `include_in_schema=False`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| POST | `/v1/resolve/{entity_type}` | Resolve entities by criteria | S2S JWT | High |
| GET | `/v1/resolve/{entity_type}/schema` | Schema discovery (queryable fields) | S2S JWT | High |

#### Entity Write (`/api/v1/entity`, `include_in_schema=False`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| PATCH | `/api/v1/entity/{entity_type}/{gid}` | Write entity fields | S2S JWT | High |

#### Internal (`/api/v1/internal`, `include_in_schema=False`)

No route handlers defined -- module provides `require_service_claims` dependency and `ServiceClaims` model used by other S2S routes.

#### Lifecycle Webhook (outside `api/` package)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| POST | `/api/v1/webhooks/asana` | Asana webhook receiver (lifecycle) | Asana HMAC | Medium |

**Note**: This router is defined in `src/autom8_asana/lifecycle/webhook.py`, not in the `api/routes/` directory. It is unclear whether it is registered with the main app. Its prefix (`/api/v1/webhooks`) overlaps with the webhooks router. Flagged as unknown below.

### Route Summary

| Category | Route Count | Auth Model |
|----------|-------------|------------|
| Health (public) | 3 | None |
| CRUD (user-facing) | 36 | PAT or JWT |
| Query/Resolve (S2S) | 6 | S2S JWT only |
| Admin (S2S) | 1 | S2S JWT only |
| Entity Write (S2S) | 1 | S2S JWT only |
| Webhooks | 1-2 | Asana HMAC |
| **Total** | **48-49** | |

### Lambda Handler Entry Points

| Handler | Module Path | Trigger | Signature | Confidence |
|---------|------------|---------|-----------|------------|
| cache_warmer | `autom8_asana.lambda_handlers.cache_warmer.handler` | EventBridge schedule | `handler(event: dict, context: Any) -> dict` | High |
| cache_invalidate | `autom8_asana.lambda_handlers.cache_invalidate.handler` | Event-driven | `handler(event: dict, context: Any) -> dict` | High |
| insights_export | `autom8_asana.lambda_handlers.insights_export.handler` | EventBridge (daily 6:00 AM ET) | `handler(event: dict, context: Any) -> dict` (via `create_workflow_handler`) | High |
| conversation_audit | `autom8_asana.lambda_handlers.conversation_audit.handler` | EventBridge schedule | `handler(event: dict, context: Any) -> dict` (via `create_workflow_handler`) | High |

### Library Exports (SDK Surface)

Primary SDK entry point: `autom8_asana.client.AsanaClient`

Key public exports from `src/autom8_asana/__init__.py`:

| Export | Type | Purpose | Confidence |
|--------|------|---------|------------|
| `AsanaClient` | class | Facade for all Asana API operations | High |
| Entity models (Business, Unit, Contact, Offer, Process, etc.) | classes | Pydantic v2 frozen models | High |
| `EntityType` | enum | 17-value entity type enumeration | High |
| `SaveSession` | class | Unit-of-work for persistence operations | High |
| DataFrames subsystem (lazy-loaded via `__getattr__`) | module | Polars analytical views | High |

### Protocol Definitions (Integration Contracts)

Source: `src/autom8_asana/protocols/__init__.py`

| Protocol | Purpose | Confidence |
|----------|---------|------------|
| `CacheProvider` | Cache backend abstraction | High |
| `AuthProvider` | Authentication provider abstraction | High |
| `LogProvider` | Logging provider abstraction | High |
| `ItemLoader` | Entity loading abstraction | High |
| `ObservabilityHook` | Observability integration point | High |

---

## 4. Entry Point Catalog

### Application Entry Points

| Entry Point | File | Function | Mode | Description | Confidence |
|-------------|------|----------|------|-------------|------------|
| **Primary dispatcher** | `src/autom8_asana/entrypoint.py` | `main()` | Both | Detects `AWS_LAMBDA_RUNTIME_API` env var; dispatches to ECS or Lambda mode | High |
| **ECS mode** | `src/autom8_asana/entrypoint.py` | `run_ecs_mode()` | ECS | Starts `uvicorn` with `autom8_asana.api.main:create_app` factory | High |
| **Lambda mode** | `src/autom8_asana/entrypoint.py` | `run_lambda_mode(handler)` | Lambda | Invokes `awslambdaric.main()` with handler module path from `sys.argv[1]` | High |
| **App factory** | `src/autom8_asana/api/main.py` | `create_app()` | ECS | Constructs FastAPI app, registers middleware stack, includes all 14 routers | High |
| **Direct uvicorn** | `src/autom8_asana/api/main.py` | `__main__` block | Dev | `uvicorn.run()` with reload=True for local development | High |

### Initialization Flow (ECS / API Server)

```
1. entrypoint.main()
   |-- Detect AWS_LAMBDA_RUNTIME_API absent
   |-- run_ecs_mode()
       |-- uvicorn.run("autom8_asana.api.main:create_app", factory=True)

2. create_app()  [api/main.py]
   |-- SIDE EFFECT: import autom8_asana.models.business
   |   |-- Triggers _bootstrap.register_all_models()
   |   |-- Populates ProjectTypeRegistry for Tier 1 detection
   |-- get_settings() -> Pydantic Settings from env vars
   |-- FastAPI(lifespan=lifespan)
   |-- instrument_app() (autom8y-telemetry, graceful if missing)
   |-- Middleware stack (CORS, SlowAPI, RequestLogging, RequestID)
   |-- Include 14 routers
   |-- register_exception_handlers()

3. lifespan()  [api/lifespan.py]
   STARTUP:
   |-- configure_logging()
   |-- HTTPXClientInstrumentor().instrument() (graceful if missing)
   |-- ClientPool initialization -> app.state.client_pool
   |-- _discover_entity_projects() -> FAIL-FAST on error
   |-- _initialize_dataframe_cache()
   |-- _register_schema_providers()
   |-- _initialize_mutation_invalidator()
   |-- EntityWriteRegistry initialization -> app.state.entity_write_registry
   |-- asyncio.create_task(_preload_dataframe_cache_progressive)
   |     (background, non-blocking -- /health returns 200, /health/ready returns 503 until complete)
   SHUTDOWN:
   |-- Cancel cache_warming_task
   |-- client_pool.close_all()
   |-- connection_registry.close_all_async()
```

### Initialization Flow (Lambda)

```
1. entrypoint.main()
   |-- Detect AWS_LAMBDA_RUNTIME_API present
   |-- Handler from sys.argv[1] (e.g., "autom8_asana.lambda_handlers.cache_warmer.handler")
   |-- run_lambda_mode(handler)
       |-- awslambdaric.main()

2. Handler invocation (e.g., cache_warmer.handler)
   |-- _ensure_bootstrap()
   |   |-- register_all_models() (idempotent, once per cold start)
   |-- handler(event, context) -> dict
       |-- asyncio.run(handler_async(event, context))
```

### Configuration Loading

| Pattern | Source | Mechanism | Confidence |
|---------|--------|-----------|------------|
| API settings | `api/config.py` | `get_settings()` -> Pydantic Settings, env vars | High |
| SDK config | `config.py` | Module-level configuration | High |
| Lambda env vars | `lambda_handlers/*.py` | Direct `os.environ.get()` for ASANA_PAT, S3 bucket, etc. | High |
| Platform config | autom8y-config | `autom8y-config>=0.3.0` for shared platform settings | High |

### Bootstrap / Registration

| Pattern | Source | Trigger | Side Effect | Confidence |
|---------|--------|---------|-------------|------------|
| `register_all_models()` | `models/business/_bootstrap.py` | Import of `models.business` (module-level call in `__init__.py`) | Populates `ProjectTypeRegistry`, `EntityRegistry` facades | High |
| `is_bootstrap_complete()` | `models/business/_bootstrap.py` | Called by `tier1.py` detection as safety check | Guard: triggers `register_all_models()` if not yet run | High |
| `_ensure_bootstrap()` | `lambda_handlers/cache_warmer.py` | Lambda cold start | Module-level `_bootstrap_initialized` flag | High |
| `SchemaRegistry._ensure_initialized()` | `dataframes/models/registry.py` | First access to schema registry | Auto-discovers schemas via `EntityDescriptor.schema_module_path` | High |

---

## 5. Unit Structure Profile

### Directory Organization

```
autom8y-asana/
    src/autom8_asana/           # Source root (27 packages, ~111K LOC)
    tests/                      # Test root (10,583 tests)
    docs/                       # Documentation root (30+ subdirectories)
    .github/workflows/          # CI/CD (2 workflow files)
    .claude/                    # Knossos orchestration config
    pyproject.toml              # Build/dependency manifest
    Dockerfile                  # Single dual-mode container image
```

### Test Structure

**Framework**: pytest with `asyncio_mode=auto`, 60s timeout, thread-based timeout method

| Test Category | Location | Subdirectory Count | Test File Count | Confidence |
|---------------|----------|-------------------|-----------------|------------|
| **Unit tests** | `tests/unit/` | 18 subdirectories | ~290 files | High |
| **Integration tests** | `tests/integration/` | 3 subdirectories | ~9 files | High |
| **QA tests** | `tests/qa/` | -- | 1 file | High |
| **Validation tests** | `tests/validation/` | 1 subdirectory | -- | High |
| **Benchmarks** | `tests/benchmarks/` | -- | 3 files | High |
| **Service tests** | `tests/services/` | -- | 1 file | High |
| **Shared fixtures** | `tests/_shared/` | -- | -- | High |
| **Root conftest** | `tests/conftest.py` | -- | 1 file | High |

**Unit test subdirectory breakdown** (test file counts):

| Subdirectory | Files | Coverage Target |
|--------------|-------|-----------------|
| `cache` | 53 | Cache subsystem (15,658 LOC) |
| `automation` | 40 | Automation/pipeline rules (9,318 LOC) |
| `models` | 36 | Entity models (15,356 LOC) |
| `dataframes` | 34 | DataFrame subsystem (13,728 LOC) |
| `persistence` | 26 | SaveSession UoW (8,137 LOC) |
| `clients` | 17 | Asana API clients (11,245 LOC) |
| `lifecycle` | 13 | Lifecycle engine (4,032 LOC) |
| `services` | 12 | Services layer (5,695 LOC) |
| `query` | 10 | Query engine (1,935 LOC) |
| `api` | 9 | FastAPI routes (8,880 LOC) |
| `resolution` | 8 | Entity resolution (1,799 LOC) |
| `lambda_handlers` | 7 | Lambda handlers (1,977 LOC) |
| `metrics` | 7 | Metrics (616 LOC) |
| `core` | 6 | Core module (2,911 LOC) |
| `transport` | 6 | HTTP transport (1,700 LOC) |
| `search` | 3 | Search (925 LOC) |
| `patterns` | 2 | Patterns (444 LOC) |
| `detection` | 1 | Detection (standalone) |

**Total reported passing**: 10,583 tests (per ARCH-REVIEW-1 findings)

### Documentation Structure

**Root**: `docs/` contains 30+ subdirectories organized by document type.

| Category | Location | Count | Description | Confidence |
|----------|----------|-------|-------------|------------|
| ADRs | `docs/adr/` | 9 files | Architecture Decision Records (ADR-001 through ADR-009) | High |
| TDDs | `docs/tdd/` | 1 file | Technical Design Documents (auth-v1-migration) | High |
| Design docs | `docs/design/` | -- | Design specifications | Medium |
| API reference | `docs/api-reference/` | -- | API documentation | Medium |
| SDK reference | `docs/sdk-reference/` | -- | SDK documentation | Medium |
| Guides | `docs/guides/` | -- | Developer guides | Medium |
| Getting started | `docs/getting-started/` | -- | Onboarding docs | Medium |
| Architecture | `docs/architecture/` | -- | Architecture docs | Medium |
| Contracts | `docs/contracts/` | -- | Interface contracts | Medium |
| Test plans | `docs/test-plans/` | -- | Test planning docs | Medium |
| Test reports | `docs/test-reports/` | -- | Test result reports | Medium |
| Runbooks | `docs/runbooks/` | -- | Operational runbooks | Medium |
| Releases | `docs/releases/` | -- | Release notes | Medium |
| Spikes | `docs/spikes/` | -- | Technical spike docs | Medium |
| Plans | `docs/plans/` | -- | Planning docs | Medium |
| Debt | `docs/debt/` | -- | Tech debt tracking | Medium |
| Reports | `docs/reports/` | -- | Various reports | Medium |
| PRD | `docs/prd/` | -- | Product requirements | Medium |

**Additional architecture docs**: The `.claude/wip/` directory contains working architecture review artifacts (ARCH-REVIEW-1 series, smell reports, refactoring plans, checkpoints).

### Middleware Stack (execution order, outermost first)

Per `src/autom8_asana/api/main.py` -- Starlette executes middleware in reverse order of addition:

| Order | Middleware | Purpose |
|-------|-----------|---------|
| 0 | MetricsMiddleware (via instrument_app) | Platform-standard request metrics |
| 1 | CORSMiddleware | Preflight handling (if configured) |
| 2 | SlowAPIMiddleware | Service-level rate limiting |
| 3 | RequestLoggingMiddleware | Structured request logging |
| 4 | RequestIDMiddleware | X-Request-ID propagation (innermost) |

---

## 6. Unknowns

### Unknown: Lifecycle webhook router registration

- **Question**: Is the router defined in `src/autom8_asana/lifecycle/webhook.py` (prefix `/api/v1/webhooks`, POST `/asana`) registered with the main FastAPI application?
- **Why it matters**: If registered, it adds an additional webhook endpoint. If not, it is dead code. Its prefix overlaps with the `api/routes/webhooks.py` router.
- **Evidence**: The router is defined with `APIRouter(prefix="/api/v1/webhooks")` but is not imported in `api/routes/__init__.py` or `api/main.py`. The main `webhooks_router` from `api/routes/webhooks.py` is the one registered.
- **Suggested source**: Code author or deployment configuration

### Unknown: Internal router has no route handlers

- **Question**: Is the `internal` router (`/api/v1/internal`) intended to have route handlers, or is it purely a dependency/model provider?
- **Why it matters**: The router is registered with `app.include_router()` but defines no `@router.get/post` decorated functions. It only exports `ServiceClaims` and `require_service_claims` used by other routers.
- **Evidence**: `src/autom8_asana/api/routes/internal.py` contains only the router declaration, model class, and dependency functions -- no route handlers.
- **Suggested source**: Original author or related TDD document

### ~~Unknown: Query v1 vs v2 coexistence~~ — RESOLVED (commit f6e08e5)

- **Resolution**: The hygiene sprint (commit f6e08e5) merged `query_v2.py` into `query.py`. A single unified router now registers all three endpoints under `/v1/query`: the deprecated `POST /{entity_type}`, the active `POST /{entity_type}/rows`, and `POST /{entity_type}/aggregate`. No routing ambiguity remains. See updated API surface map above (Section 3).

---

## 7. Provenance

This topology-inventory formalizes findings from **ARCH-REVIEW-1** (2026-02-18), a comprehensive architectural review conducted via 17-agent swarm (10 exploration + 7 architectural analysis). The following source artifacts were used:

| Source Artifact | Contribution |
|----------------|-------------|
| `ARCH-REVIEW-1-TOPOLOGY.md` | Package map, entity model, section classification, DataFrame architecture, query engine, intelligence loop, key files (Sections 1-7) |
| `ARCH-REVIEW-1-CACHE.md` | Cache provider hierarchy, entity/DataFrame cache architecture, invalidation paths, warming, watermarks, completeness (Sections 1-12) |
| `ARCH-REVIEW-1-INDEX.md` | Executive summary, codebase metrics, tech stack overview, methodology |

### Targeted Gap-Fill Scans

The following targeted codebase scans were performed to produce explicit tabular inventories where ARCH-REVIEW-1 had only high-level coverage:

| Scan | Method | Files Examined | Output |
|------|--------|---------------|--------|
| FastAPI route definitions | Grep for `@router.(get\|post\|put\|delete\|patch)` + `APIRouter` in `src/autom8_asana/api/routes/` | 14 route modules | Section 3 route tables (48-49 endpoints) |
| Lambda handler signatures | Grep for `def handler` in `lambda_handlers/` + Read of handler files | 7 handler files | Section 3 Lambda handler table (4 handlers) |
| Entry point dispatch | Read of `entrypoint.py`, `api/main.py`, `api/lifespan.py` | 3 files | Section 4 initialization flows |
| Bootstrap registration | Grep for `register_all_models\|_bootstrap` across `src/` | 6 files with matches | Section 4 bootstrap table |
| Test directory structure | Bash `ls` + `find` on `tests/` | All test subdirectories | Section 5 test structure tables |
| Documentation layout | Bash `ls` on `docs/` + count of ADR/TDD files | `docs/` root + `docs/adr/` + `docs/tdd/` | Section 5 documentation table |
| Dependency versions | Read of `pyproject.toml` | 1 file | Section 2 version constraints |
| CI/CD workflows | Glob for `.github/workflows/*.yml` | 2 workflow files | Section 2 CI/CD table |
| Dockerfile | Glob for `Dockerfile*` | 1 file | Section 2 IaC table |

### Handoff Readiness

- [x] All 27 packages classified with role labels
- [x] Confidence ratings assigned to all classifications and API surface identifications
- [x] Tech stack table with version constraints from `pyproject.toml`
- [x] API surface table with 48-49 route paths, methods, and auth requirements
- [x] Lambda handler table with module paths and trigger types
- [x] Entry point table with initialization flow descriptions
- [x] Bootstrap/registration patterns documented
- [x] Test structure summary with per-subdirectory file counts
- [x] Documentation presence cataloged
- [x] Unknowns section documents 3 items that could not be fully resolved from code alone
- [x] No target unit skipped
