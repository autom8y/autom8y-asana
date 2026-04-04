---
domain: conventions
generated_at: "2026-04-04T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "55aaab5"
confidence: 0.82
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "1471b813f0f58342c542d2e8c9cd92aba095afec134846cda625c3fa545ec9fe"
---

# Codebase Conventions

**Project**: autom8y-asana — an async-first Asana API client (Python 3.12+)
**Primary Language**: Python, managed with `uv` and `hatchling`
**Package root**: `src/autom8_asana/` (476 source files)

---

## Error Handling Style

### Exception Hierarchy Model

The project uses a **three-tier exception hierarchy** organized by domain boundary:

**Tier 1 — SDK/API errors** (`src/autom8_asana/exceptions.py`):
- Base: `AsanaError(Exception)` — all Asana API surface errors
- HTTP-mapped subclasses: `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `GoneError`, `RateLimitError`, `ServerError`, `TimeoutError`, `ConfigurationError`, `CircuitBreakerOpenError`, `NameNotFoundError`, `HydrationError`, `ResolutionError`
- Domain-specific: `InsightsError` (+ `InsightsValidationError`, `InsightsNotFoundError`, `InsightsServiceError`), `ExportError`
- `AsanaError.from_response(response)` — class method that parses HTTP response and returns the most specific subclass

**Tier 2 — Infrastructure errors** (`src/autom8_asana/core/exceptions.py`):
- Base: `Autom8Error(Exception)` — cross-cutting infrastructure (transport, cache, automation)
- Each exception carries `context: dict[str, Any]` and `cause: Exception | None`
- `transient: bool` class attribute classifies retry eligibility
- Transport subtree: `TransportError(transient=True)` -> `S3TransportError`, `RedisTransportError`
- Cache subtree: `CacheError` -> `CacheConnectionError`
- Automation subtree: `AutomationError` -> `RuleExecutionError`, `SeedingError`, `PipelineActionError`

**Tier 3 — Service-layer errors** (`src/autom8_asana/services/errors.py`):
- Base: `ServiceError(Exception)` — business logic errors, never carries HTTP framework imports
- Each error exposes `error_code: str` (machine-readable), `status_hint: int` (HTTP suggestion), and `to_dict() -> dict`
- Subtree: `EntityNotFoundError` (-> `UnknownEntityError`, `UnknownSectionError`, `TaskNotFoundError`, `EntityTypeMismatchError`), `EntityValidationError` (-> `InvalidFieldError`, `InvalidParameterError`, `NoValidFieldsError`), `CacheNotReadyError`, `CascadeNotReadyError`, `ServiceNotConfiguredError`

**Tier 4 — Save orchestration errors** (`src/autom8_asana/persistence/exceptions.py`):
- Base: `SaveOrchestrationError(AsanaError)`
- Subclasses: `SessionClosedError`, `CyclicDependencyError`, `DependencyResolutionError`, `PartialSaveError`, `UnsupportedOperationError`, `PositioningConflictError`, `GidValidationError`, `SaveSessionError`

**Domain-local errors**: Each major subsystem defines its own error module:
- `src/autom8_asana/query/errors.py`: `QueryEngineError` -> `QueryTooComplexError`, `UnknownFieldError`, `InvalidOperatorError`, `CoercionError`, `AggregationError`, etc.
- `src/autom8_asana/dataframes/exceptions.py`: `DataFrameError` (base) -> `ParallelFetchError`
- `src/autom8_asana/cache/models/errors.py`: cache model errors
- `src/autom8_asana/auth/bot_pat.py`: `BotPATError`

### Error Propagation Pattern

**Services never import HTTP framework types.** Per ADR-SLE-003 documented in `src/autom8_asana/services/errors.py`:
- Services raise `ServiceError` subclasses
- Route handlers map service errors to HTTP via `raise_service_error()` in `src/autom8_asana/api/errors.py`
- `raise_service_error(request_id, error)` converts `ServiceError.error_code` + `ServiceError.status_hint` into `HTTPException`
- `raise_api_error(request_id, status_code, code, message)` for route-level validation errors (never in service layer)

**FastAPI exception handler registration** (`src/autom8_asana/api/errors.py`, `register_exception_handlers()`):
- Most-specific handlers registered first (e.g., `NotFoundError` before `AsanaError`)
- Catch-all `generic_error_handler` registered last — returns 500, hides stack trace, logs full exception
- All error responses include `request_id` for correlation (per FR-ERR-008)

### Exception Context Convention

Infrastructure exceptions (`Autom8Error` subclasses) use keyword-only `cause=` to preserve cause chain:
```python
raise S3TransportError("Failed to write", backend="s3", operation="put", cause=original_exc)
```
Standard `raise ... from` is used in lower-level code; `__cause__` is set manually when wrapping vendor exceptions.

### Exception Handling Patterns

- Broad `except Exception` is used only in the catch-all API handler and background tasks
- Narrowed exception tuples are defined as module-level constants (e.g., `CACHE_TRANSIENT_ERRORS`, `_INDEX_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError,)` in `src/autom8_asana/services/universal_strategy.py`)
- `exc_info=True` passed to logger calls when re-raising or swallowing for context preservation

---

## File Organization

### Package Layout

```
src/
  autom8_asana/
    __init__.py            # Package root
    client.py              # Top-level AsanaClient facade
    config.py              # SDK configuration (AsanaConfig, dataclasses)
    exceptions.py          # SDK/API exception hierarchy (Tier 1)
    settings.py            # Platform settings (pydantic-settings)
    entrypoint.py          # Application entry point
    _defaults/             # Platform SDK default providers
    api/                   # FastAPI application layer
      main.py              # FastAPI app factory
      lifespan.py          # Startup/shutdown lifecycle
      dependencies.py      # FastAPI dependency injection
      errors.py            # Exception handlers + raise_* helpers
      exceptions.py        # API-layer typed exceptions
      models.py            # Request/response Pydantic models
      middleware/           # Core middleware + idempotency middleware
      routes/               # One file per resource/feature
        tasks.py
        sections.py
        query.py
        intake_create.py
        intake_resolve.py
        {route}_models.py   # Route-colocated Pydantic models
      preload/             # Progressive preloading strategies
    auth/                  # Authentication adapters
    automation/            # Automation engine, workflows, events, polling
    batch/                 # Batch operation client and models
    cache/                 # Tiered cache subsystem
      backends/            # Redis, S3, memory, base
      dataframe/           # DataFrame-specific cache
      integration/         # Cache integration adapters
      models/              # Cache data models
      policies/            # Freshness, staleness, hierarchy policies
      providers/           # Tiered and unified providers
    clients/               # Resource API clients (one per Asana resource)
      base.py              # BaseClient class
      tasks.py, sections.py, projects.py, ...
      data/                # DataServiceClient
    core/                  # Cross-cutting infrastructure
      exceptions.py        # Infrastructure exception hierarchy (Tier 2)
      logging.py           # Logging configuration wrapper
      retry.py             # Retry logic
      entity_registry.py, project_registry.py, ...
    dataframes/            # Polars DataFrame build/query system
    lambda_handlers/       # AWS Lambda entry points
    lifecycle/             # Entity lifecycle handlers
    metrics/               # Business metrics computation
    models/                # Pydantic models (Asana resources + business domain)
      base.py              # AsanaResource base
      business/            # Domain business entity models
        detection/         # Tiered detection logic
        matching/          # Entity matching engine
      contracts/           # Cross-service contracts
    observability/         # OTel decorators and correlation
    patterns/              # Async method patterns, error classification
    persistence/           # Save orchestration (SaveSession, actions)
    protocols/             # Structural typing Protocols
    query/                 # Query engine
    reconciliation/        # Data reconciliation engine
    resolution/            # Field and GID resolution
    search/                # Search service
    services/              # Business logic services
      errors.py            # Service-layer exception hierarchy (Tier 3)
      {name}_service.py    # One service per domain concern
    transport/             # HTTP transport
```

### File Naming Conventions

- **`_private.py`** prefix: internal implementation details not exported (e.g., `_cache.py`, `_endpoints/`, `_metrics.py`, `_normalize.py`, `_pii.py`, `_policy.py`, `_response.py`, `_retry.py`)
- **`{resource}s.py`** pattern: Asana resource clients are plural nouns (`tasks.py`, `sections.py`, `projects.py`)
- **`{name}_service.py`** pattern: service layer files (`task_service.py`, `dataframe_service.py`)
- **`errors.py`** per module: domain-local exception modules (present in `services/`, `query/`, `api/`, `dataframes/`, `cache/models/`, `persistence/`)
- **`models.py`** co-located: route-level Pydantic models live as `{route}_models.py` alongside their route file
- **`protocols/`** directory: structural Protocols isolated to their own package

### `__init__.py` Exports

Each package uses `__init__.py` for controlled public exports. `__all__` is defined in modules with public APIs. `TYPE_CHECKING` guard in `__init__.py` is present in 250 of 476 files — the dominant pattern for circular import avoidance.

### `from __future__ import annotations`

Present in essentially all source files (250 files confirmed). This is a universal convention — every new file should include it as the first import.

---

## Domain-Specific Idioms

### 1. Platform SDK-Only Imports (Enforced by Ruff TID251)

The project enforces platform primitive usage over raw libraries via `pyproject.toml` `[tool.ruff.lint.flake8-tidy-imports.banned-api]`:

| Banned | Required alternative |
|--------|---------------------|
| `loguru`, `structlog` | `autom8y_log.get_logger()` |
| `httpx`, `httpx.AsyncClient`, `httpx.Client` | `autom8y_http.Autom8yHttpClient` |
| `requests`, `urllib.request` | `autom8y_http` |

### 2. Structured Logging with Event Keys

Log calls use a **snake_case event key as the first argument**, followed by keyword arguments for structured context:
```python
logger.info("cache_warm_complete", project_gid=gid, duration_ms=elapsed)
logger.warning("section_cache_degradation", exc_info=True)
logger.error("event_routing_config_invalid", error=str(e))
```

`get_logger(__name__)` is called at module level in 186 of 476 files:
```python
logger = get_logger(__name__)
```

Some older code passes `extra={}` dict instead of keyword arguments — this is the legacy pattern still present in ~24 files. New code uses keyword-only kwargs directly.

### 3. Async-First

The project is async-first: `await` appears 2349 times across 215 files. All client methods, service methods, and route handlers are `async def`. Synchronous compatibility is provided via `src/autom8_asana/transport/sync.py`. `asyncio_mode = "auto"` in pytest config — all tests are async by default.

### 4. `TYPE_CHECKING` Guard Pattern

250 files use `TYPE_CHECKING` to defer imports that would create circular dependencies:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from autom8_asana.models.task import Task
    from autom8_asana.cache.models.entry import CacheEntry
```
This is mandatory for cross-package model imports.

### 5. Pydantic v2 Model Configuration

All Asana resource models inherit from `AsanaResource(BaseModel)` (`src/autom8_asana/models/base.py`) with:
```python
model_config = ConfigDict(
    extra="ignore",        # Forward compatibility with new Asana fields
    populate_by_name=True, # Accept both alias and Python name
    str_strip_whitespace=True,
)
```
Settings classes inherit from `pydantic_settings.BaseSettings`. 111 Pydantic model classes across 28 files.

### 6. Protocol-Based Dependency Injection

`src/autom8_asana/protocols/` contains `Protocol` classes for injectable dependencies: `CacheProvider`, `DataFrameCacheProtocol`, `AuthProvider`, `LogProvider`, `ItemLoader`, `InsightsProtocol`, `ObservabilityProtocol`. 27 files use `Protocol` or `@runtime_checkable`.

### 7. Dataclass vs Pydantic Boundary

128 files use `@dataclass`. `@dataclass` is for: configuration objects, lightweight result containers, internal data structures. `BaseModel` is for: API contracts, Asana resource models.

### 8. GID as the Universal Key

`gid: str` is the universal resource identifier. Cache keys: `"{resource_type}:{gid}"`. Entity registries, resolution, and persistence all use `gid`. 1430 occurrences of `.gid` across 216 files.

### 9. OpenTelemetry Tracing

- `get_tracer(__name__)` in high-value paths
- `@trace_computation` decorator in 11 files (query engine, dataframe builders, cache, workflows)
- `src/autom8_asana/observability/` contains correlation and decorator utilities

### 10. ADR/TDD Reference Comments

Files consistently reference design decisions using `Per TDD-XXXX`, `Per ADR-XXXX`, or `Per PRD-XXXX`. Always include the relevant reference when adding code that implements a design decision.

---

## Naming Patterns

### Module and Package Names
- All lowercase with underscores: `task_service.py`, `field_write_service.py`
- Private modules prefixed with `_`: `_cache.py`, `_response.py`, `_endpoints/`
- Plural nouns for resource client modules: `tasks.py`, `sections.py`, `projects.py`
- `errors.py` convention for domain exception modules (not `exceptions.py` at domain level — only `exceptions.py` at package root)
- `config.py` for configuration, `settings.py` for pydantic-settings

### Class Names
- `PascalCase` throughout
- Services: `{Domain}Service` (e.g., `TaskService`, `DataFrameService`)
- Clients: `{Resource}sClient` (e.g., `TasksClient`, `SectionsClient`) inheriting `BaseClient`
- Exceptions: `{Domain}Error` suffix dominates (60+ exception classes)
- Protocols: `{Name}Protocol` or `{Name}Provider` (e.g., `CacheProvider`, `DataFrameCacheProtocol`)
- Pydantic models: noun phrases in PascalCase (`AsanaResource`, `Task`, `ErrorResponse`)
- Configuration dataclasses: `{Domain}Config` (e.g., `RateLimitConfig`, `CacheConfig`)
- Base classes: `Base{Name}` (e.g., `BaseClient`) or plain abstract names

### Function and Method Names
- `snake_case` throughout
- Async methods use `_async` suffix when a sync counterpart exists
- Private methods prefixed with `_`
- Class methods: `from_{source}` pattern for constructors
- FastAPI route handlers: verb + noun (e.g., `get_tasks`, `create_task`)

### Variable Names
- `snake_case` throughout
- Module-level logger: always `logger = get_logger(__name__)`
- Module-level tracer: always `_tracer = get_tracer(__name__)` (private)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TTL`, `ACTIVITY_PRIORITY`)
- Exception tuples for `except` clauses: `UPPER_SNAKE_CASE` (e.g., `CACHE_TRANSIENT_ERRORS`)

### File Naming vs Class Naming

| Pattern | Example File | Example Class |
|---------|-------------|---------------|
| Service | `task_service.py` | `TaskService` |
| Client | `tasks.py` | `TasksClient` |
| Exception module | `errors.py` | `ServiceError`, `EntityNotFoundError` |
| Config | `config.py` | `AsanaConfig`, `CacheConfig` |
| Protocol | `protocols/cache.py` | `CacheProvider` |

---

## Knowledge Gaps

1. **`__all__` completeness**: Not all modules define `__all__`. Coverage of which packages export clean public APIs was not fully audited.
2. **Logging style consistency**: Both kwarg style and extra dict style coexist. The relative prevalence across all 184 files with logger calls was not exhaustively measured.
3. **`@dataclass(slots=True)` vs plain `@dataclass`**: Slot usage in dataclasses was not systematically checked.
4. **API route response models**: The `_models.py` co-location pattern was observed in routes but not exhaustively confirmed across all 19 route files.
5. **`asyncio.to_thread` vs `asyncio.run` usage**: Both patterns exist for sync/async bridging; exact distribution not mapped.
