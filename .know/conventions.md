---
domain: conventions
generated_at: "2026-03-25T01:56:07Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "c6bcef6"
confidence: 0.93
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Conventions

**Language**: Python 3.12 (confirmed via `pyproject.toml`, `requires-python = ">=3.12"`)
**Package root**: `src/autom8_asana/` (424+ source files across 18 top-level sub-packages)
**Framework**: FastAPI (async-first), Pydantic v2, Polars dataframes
**Tooling**: `mypy --strict`, `ruff` (88-char lines, rules E/F/I/UP/B/G/LOG/TCH/TID/SIM)

## Error Handling Style

### Error Hierarchy Architecture

The project uses a **layered exception hierarchy** with four distinct exception families, each scoped to a domain:

```
Exception (Python built-in)
|-- AsanaError  (src/autom8_asana/exceptions.py)
|   |-- AuthenticationError, ForbiddenError, NotFoundError, GoneError
|   |-- RateLimitError  (with retry_after attr)
|   |-- ServerError, TimeoutError, ConfigurationError
|   |-- CircuitBreakerOpenError, NameNotFoundError
|   |-- HydrationError, ResolutionError
|   |-- InsightsError -> InsightsValidationError, InsightsNotFoundError, InsightsServiceError
|   |-- ExportError
|   +-- SaveOrchestrationError  (src/autom8_asana/persistence/exceptions.py)
|       |-- SessionClosedError, CyclicDependencyError, DependencyResolutionError
|       |-- PartialSaveError, UnsupportedOperationError, PositioningConflictError
|       |-- GidValidationError, SaveSessionError
|
|-- Autom8Error  (src/autom8_asana/core/exceptions.py)
|   |-- TransportError  (transient=True)
|   |   |-- S3TransportError  (transient depends on error_code)
|   |   +-- RedisTransportError
|   |-- CacheError  (transient=False)
|   |   +-- CacheConnectionError  (transient=True)
|   +-- AutomationError
|       |-- RuleExecutionError, SeedingError, PipelineActionError
|
|-- ServiceError  (src/autom8_asana/services/errors.py)
|   |-- EntityNotFoundError -> UnknownEntityError, UnknownSectionError,
|   |   TaskNotFoundError, EntityTypeMismatchError
|   |-- EntityValidationError -> InvalidFieldError, InvalidParameterError, NoValidFieldsError
|   |-- CacheNotReadyError, CascadeNotReadyError, ServiceNotConfiguredError
|
|-- QueryEngineError  (src/autom8_asana/query/errors.py)
|   +-- QueryTooComplexError, UnknownFieldError, InvalidOperatorError,
|       CoercionError, UnknownSectionError, AggregationError,
|       AggregateGroupLimitError, ClassificationError, JoinError
|
+-- DataFrameError  (src/autom8_asana/dataframes/exceptions.py)
    +-- SchemaNotFoundError, ExtractionError, TypeCoercionError, SchemaVersionError
```

### Error Creation Patterns

Custom exception classes are the rule. Raw `raise ValueError(...)` is used only in validation guards; `raise RuntimeError(...)` is rare. Error classes carry structured context:

- `AsanaError` and `Autom8Error` take `message: str` plus keyword-only context attributes (e.g., `entity_gid`, `cause`, `context: dict`).
- `ServiceError` subclasses carry strongly-typed context as `__init__` arguments (e.g., `InvalidFieldError(invalid_fields: list[str], available_fields: list[str])`).
- `QueryEngineError` subclasses use `@dataclass` syntax to define fields.
- All hierarchies provide `to_dict()` for JSON serialization to API responses.
- `ServiceError` subclasses provide `error_code: str` (machine-readable, uppercase) and `status_hint: int` (HTTP status) as `@property` overrides.
- `SERVICE_ERROR_MAP: dict[type[ServiceError], int]` in `src/autom8_asana/services/errors.py` provides O(1) HTTP status lookup; `get_status_for_error()` walks MRO for most specific match.

**Factory classmethods** are used at transport boundaries:
- `AsanaError.from_response(response)` -- parses HTTP responses into the most specific subclass.
- `S3TransportError.from_boto_error(error, *, operation, bucket, key)` -- wraps botocore at boundary.
- `RedisTransportError.from_redis_error(error, *, operation)` -- wraps redis exceptions.

### Error Wrapping and Propagation

**Cause chaining**: `self.__cause__ = cause` (not `raise X from Y`) when wrapping vendor exceptions. Seen in `src/autom8_asana/persistence/exceptions.py`.

**Vendor isolation via error tuples**: `src/autom8_asana/core/exceptions.py` exports:
- `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`, `CACHE_TRANSIENT_ERRORS`, `ASANA_API_ERRORS`

These tuples are used in `except` clauses across the codebase so upstream code never imports `botocore` or `redis` directly.

**Graceful degradation** is the preferred pattern for cache failures: catch, log at `warning`, return `None` or continue. This is referenced as `NFR-DEGRADE-001` in comments.

**Transient classification**: `Autom8Error` carries class-level `transient: bool = False`. Subclasses override it. `PartialSaveError.is_retryable` uses this for retry logic.

### Error Handling at Boundaries

**API layer** (`src/autom8_asana/api/errors.py`):
- `register_exception_handlers(app)` registers all `AsanaError` subclass handlers with FastAPI in specificity order (most specific first, catch-all last).
- Handlers return structured JSON: `{"error": {"code": "...", "message": "..."}, "meta": {"request_id": "..."}}`
- `raise_api_error(request_id, status_code, code, message)` -- Tier 3 route-level validation.
- `raise_service_error(request_id, error: ServiceError)` -- converts `ServiceError` to `HTTPException`, preserving `error.to_dict()` fields plus `request_id`.

**Service layer**: Services raise `ServiceError` subclasses only -- never HTTP exceptions. Routes call `raise_service_error()` and never construct `HTTPException` directly. Per `TDD-SERVICE-LAYER-001` / `ADR-SLE-003`.

### Logging at Error Sites

- `logger.warning(...)` for expected transient failures (cache miss, rate limit).
- `logger.error(...)` for upstream failures.
- `logger.exception(...)` for catch-all handler (includes stack trace automatically).
- All log calls use `extra={}` dict or keyword arguments for structured output.
- `autom8y_log.get_logger(__name__)` pattern is universal -- 162 files use `get_logger` (confirmed by grep count), assigned to module-level `logger` variable.

### Known Violations

- `CacheNotWarmError` at `src/autom8_asana/services/query_service.py:240` is a module-local exception not part of `services/errors.py` hierarchy.
- `MissingConfigurationError(Exception)` at `src/autom8_asana/cache/integration/autom8_adapter.py:57` does not inherit from `Autom8Error` or `AsanaError`.
- `ResolutionError(Exception)` at `src/autom8_asana/resolution/context.py:440` is a standalone definition that duplicates `AsanaError.ResolutionError` from `exceptions.py`.

## File Organization

### Top-Level Package Structure

`src/autom8_asana/` top-level modules and sub-packages:

| Path | Contents |
|------|----------|
| `client.py` | Public `AsanaClient` facade (SDK entry point) |
| `config.py` | `AsanaConfig` dataclass (runtime config object) |
| `settings.py` | `Autom8yBaseSettings`-derived settings classes (env var parsing) |
| `exceptions.py` | SDK-level `AsanaError` hierarchy |
| `entrypoint.py` | ASGI/Lambda entry point |
| `api/` | FastAPI routes, models, middleware, dependencies, lifespan |
| `auth/` | Authentication providers (JWT, PAT, dual-mode) |
| `automation/` | Automation engine, workflows, events, polling |
| `batch/` | Batch API client and models |
| `cache/` | Cache backends, providers, integration, dataframe cache, models, policies |
| `clients/` | Per-resource Asana API clients (tasks, projects, sections, etc.) |
| `core/` | Cross-cutting utilities: entity registry, retry, datetime, types |
| `dataframes/` | Polars DataFrame pipeline: builders, extractors, schemas, storage, resolvers, views |
| `lambda_handlers/` | AWS Lambda handler entry points |
| `lifecycle/` | Task lifecycle state machine (creation, completion, sections, wiring) |
| `metrics/` | Metrics computation and expression engine |
| `models/` | Pydantic models for Asana API resources; `models/business/` for domain models |
| `observability/` | Tracing decorators and correlation context |
| `patterns/` | Reusable cross-cutting patterns (`async_method.py`, `error_classification.py`) |
| `persistence/` | Save session, dependency graph, action executor, healing |
| `protocols/` | `Protocol` interfaces for dependency injection |
| `query/` | Query engine: compiler, engine, fetcher, models, errors |
| `resolution/` | Entity resolution strategies and context |
| `search/` | Text search service |
| `services/` | Business service layer between routes and clients |
| `transport/` | HTTP transport, adaptive semaphore, sync wrapper |
| `_defaults/` | Default factory implementations (`_` prefix = internal) |

### Per-Package File Naming Conventions

Consistent naming within packages:
- `base.py` -- abstract base classes or shared mixins (`cache/backends/base.py`, `clients/base.py`, `dataframes/builders/base.py`, `dataframes/extractors/base.py`, `automation/workflows/base.py`)
- `models.py` -- Pydantic data models for the package domain
- `errors.py` or `exceptions.py` -- exception hierarchy for the package (both names exist; `errors.py` used in `services/` and `query/`; `exceptions.py` used in `persistence/`, `dataframes/`)
- `config.py` -- `*Config` or `*Settings` dataclass for the package
- `engine.py` -- primary orchestration/execution class
- `registry.py` -- registry/catalog patterns
- `factory.py` -- factory functions or classes
- `protocol.py` -- `Protocol` interfaces (inside packages; top-level `protocols/` package holds shared protocols)
- `__init__.py` -- explicit `__all__` exports; rarely contains implementation logic

### Sub-Package Depth Pattern

Packages nest by concern layer. `cache/` has `backends/`, `providers/`, `integration/`, `dataframe/`, `models/`, `policies/`. `api/routes/` is flat with route modules and co-located `{route}_models.py` for Pydantic request/response models.

### Route-Model Co-location Pattern

`api/routes/` co-locates Pydantic models with their route handler:
- `intake_create.py` + `intake_create_models.py`
- `intake_resolve.py` + `intake_resolve_models.py`
- `intake_custom_fields.py` + `intake_custom_fields_models.py`
- `resolver.py` + `resolver_models.py` + `resolver_schema.py`

### Private Module Convention

Single-underscore prefix signals package-private modules: `clients/data/_retry.py`, `_response.py`, `_cache.py`, `_policy.py`. The `_defaults/` package uses underscore prefix for internal wiring defaults.

### `__init__.py` Exports

All 146 public modules use explicit `__all__`. Top-level `src/autom8_asana/__init__.py` exports the SDK public surface. Sub-package `__init__.py` files export the stable package API.

### File-Level Header Pattern

All files use:
1. Module docstring with ADR/TDD references (e.g., `Per TDD-SERVICE-LAYER-001`, `Per ADR-SLE-003`)
2. `from __future__ import annotations` (378 files -- universal in significant modules)
3. Stdlib imports, then third-party, then local (enforced by ruff isort)
4. `if TYPE_CHECKING:` block for type-only imports (484 files use it)
5. `__all__` at module top or bottom (146 files)
6. `logger = get_logger(__name__)` as first binding after imports (in files that log)

## Domain-Specific Idioms

### 1. GID as the Primary Key

All Asana entities are identified by `gid: str` (not `id`, not `uuid`). `AsanaResource` at `src/autom8_asana/models/base.py:30` mandates `gid: str`. Variable names use `{entity}_gid` suffix: `workspace_gid`, `project_gid`, `task_gid`, `section_gid`. The field on the model is `gid` (no prefix). GID appears in 161+ usages across model files alone.

### 2. DataFrame Source Annotation Protocol

`ColumnDef.source` uses a string DSL:
- `"gid"` / `"name"` / `"created_at"` etc. -- direct Asana task attributes
- `"cf:Field Name"` -- resolves to a custom field named "Field Name" in Asana
- `"cascade:Field Name"` -- cascades from a parent entity's field
- `source=None` -- derived column (custom extraction logic in extractor)

Examples in `src/autom8_asana/dataframes/schemas/unit.py` and `src/autom8_asana/dataframes/schemas/contact.py`. This DSL is unique to this project.

### 3. `@async_method` Descriptor

`src/autom8_asana/patterns/async_method.py` defines the `@async_method` decorator, which auto-generates `{name}_async()` and `{name}()` pairs from a single async implementation. When stacking, `@async_method` must be outermost. The sync variant raises `SyncInAsyncContextError` if called from an async context (per `ADR-0002`).

### 4. Protocol-Driven Dependency Injection

`src/autom8_asana/protocols/` holds shared `Protocol` classes: `CacheProvider`, `AuthProvider`, `LogProvider`, `MetricsEmitter`, `DataFrameProvider`, `InsightsProvider`, `ItemLoader`, `ObservabilityHook`. Constructor arguments accept `Protocol | None` with graceful fallback when `None`.

### 5. `*Result` Return Objects for Partial Failures

Operations that can partially succeed return `*Result` dataclasses rather than raising exceptions:
- `SaveResult` (`persistence/models.py`) -- `succeeded`, `failed`, `action_results`, `retryable_failures`
- `PartialSaveError` wraps `SaveResult` for callers preferring exception-based handling
- `HealingResult`, `BuildResult`, `FetchResult`, `WarmResult`

Pattern: `result.raise_on_failure()` is the explicit opt-in for exception conversion.

### 6. `EntityRegistry` / Descriptor-Driven Registration

`src/autom8_asana/core/entity_registry.py` implements a singleton registry. Entity types are registered as `EntityDescriptor` frozen dataclasses (`@dataclass(frozen=True, slots=True)`). Registry provides O(1) lookup by name, project GID, and `EntityType`. All downstream systems (schema discovery, extractor resolution, `ENTITY_RELATIONSHIPS`) are driven by the registry -- no hardcoded `match/case` branches. Import-time integrity validation catches schema/extractor/row model triad inconsistencies.

### 7. `StrEnum` for Domain Enums

`StrEnum` (Python 3.11+) is the preferred base class for string-valued enums: `EntityCategory`, `MutationType`, `ResolutionStatus`, `SectionStatus`, `FreshnessIntent`, `FreshnessState`, `AuthMode`, etc. `Enum` is used for non-string state machines (`CircuitState`, `BuildStatus`).

### 8. `EventEnvelope` Pattern

`src/autom8_asana/automation/events/envelope.py` defines `EventEnvelope` -- a `frozen=True` dataclass with a `build()` static factory method (not direct `__init__` use). Pattern: `@staticmethod def build(...)` on frozen dataclasses for objects with auto-generated fields (UUID, timestamp).

### 9. `Autom8yBaseSettings` for All Configuration

All settings classes extend `autom8y_config.Autom8yBaseSettings`. `src/autom8_asana/settings.py` contains 11 settings classes. Config accessed via `get_settings()` / `reset_settings()` singleton pattern. Never use `pydantic_settings.BaseSettings` directly.

### 10. ADR/TDD Comment Markers

Source files consistently reference `Per ADR-XXXX:`, `Per TDD-XXXX:`, `Per FR-XXX:`, `Per PRD-XXX:` in docstrings to trace design decisions. These are load-bearing references -- new code should include them when applicable.

### 11. SDK-Only Import Enforcement (ruff TID251)

`pyproject.toml` bans direct imports of `loguru`, `structlog`, `httpx`, and `httpx.AsyncClient` via ruff's `flake8-tidy-imports` banned-api feature. Use `autom8y_log.get_logger()`, `autom8y_http.Autom8yHttpClient` instead. Violations are CI-blocking. The only exemption is `src/autom8_asana/query/__main__.py` (CLI dev tool).

## Naming Patterns

### Exported Type Suffixes

Tightly standardized naming suffixes:
- `*Result` -- return types from operations that can partially fail
- `*Config` -- configuration dataclasses (`RetryConfig`, `CircuitBreakerConfig`, `DataFrameConfig`)
- `*Settings` -- `Autom8yBaseSettings` subclasses
- `*Error` / `*Exception` -- exception hierarchy classes
- `*Registry` -- singleton lookup/catalog objects (`EntityRegistry`, `SchemaRegistry`, `WorkflowRegistry`)
- `*Provider` -- Protocol classes for DI
- `*Request` / `*Response` -- Pydantic API models (in `api/routes/` and `api/models.py`)
- `*Builder` -- classes that construct complex objects step-by-step
- `*Service` -- service classes in `services/`
- `*Client` -- API client classes (`BaseClient`, `AsanaClient`, `DataServiceClient`)
- `*Mixin` -- mixin classes (`HolderMixin`, `RetryableErrorMixin`, `DegradedModeMixin`)
- `*Descriptor` -- descriptor protocol classes (`EntityDescriptor`, `CustomFieldDescriptor`)

### GID Variable Convention

Entity-specific GID variables always use `{entity}_gid` suffix: `workspace_gid`, `project_gid`, `task_gid`, `section_gid`, `user_gid`. The field name on `AsanaResource` is `gid` (unprefixed). In class names, `Gid` (not `GID`): `GidValidationError`.

### Method Naming

- Async client methods: `get_async()`, `list_async()`, `create_async()`, `delete_async()`, `update_async()` -- generated by `@async_method`, with corresponding sync variants.
- Service methods: verb + noun (`get_entity_type()`, `write_fields_async()`, `fetch_tasks_async()`).
- Private helpers: leading `_` per Python convention; no `__` double-underscore mangling in non-dunder contexts.

### Module-Level Logger

Every non-trivial module declares a module-level logger as the first binding after imports:
```python
logger = get_logger(__name__)
```
162 files use `get_logger`, assigned to variable `logger` (100% consistent name). The `__name__` argument is universal.

### Log Message Naming (Structured Events)

Logging event names use `snake_case` strings that name the event being observed (not interpolated): `"manifest_parse_failed"`, `"cascade_key_null_audit"`, `"event_emission_disabled"`, `"authentication_failed"`, `"pipeline_using_fixed_assignee"`. Context is passed as keyword arguments or `extra={}` dict, not embedded in the message string.

### Package / Module Naming

- All packages: `snake_case`. Most are singular nouns. `clients` and `models` are plural (existing pattern -- do not create new plural packages).
- Private modules inside packages: `_underscore_prefix.py`.
- `_defaults/` package uses underscore-prefixed package name.

### Acronym Conventions

- `GID`: `gid` in variable names, `Gid` in class names.
- `PAT` (Personal Access Token): `pat` in attribute names, `PAT` in class names (`BotPATError`).
- `TTL`: `ttl` in variable names, `TTL` in constants (`DEFAULT_TTL`).
- `URL`: lowercase `url` in attribute names (`base_url`, `endpoint_url`).
- `API`: `Api` in class names (not `API`), lowercase in package names.

### Existing Naming Anti-Patterns (Do Not Spread)

- `CacheNotWarmError` at `src/autom8_asana/services/query_service.py:240` -- module-local, not in `services/errors.py`.
- `MissingConfigurationError(Exception)` at `src/autom8_asana/cache/integration/autom8_adapter.py:57` -- not in hierarchy.
- `ResolutionError(Exception)` at `src/autom8_asana/resolution/context.py:440` -- duplicates `exceptions.py:ResolutionError`.
- Two `ResolutionError` classes exist (naming collision across packages).

## Knowledge Gaps

1. **`_defaults/` full characterization**: `_defaults/auth.py`, `_defaults/cache.py`, `_defaults/log.py`, `_defaults/observability.py` hold default provider factory functions. `auth.py` was partially observed (secrets cache pattern). The full factory signatures were not read for all four.
2. **`@error_handler` decorator**: Referenced in `patterns/` docstrings but not located. May live in transport or client package.
3. **`lifecycle/` transition guards**: The exact state machine triggers and guard conditions for creation/completion/sections/wiring were not read. Known to exist but not documented in detail.
4. **`models/business/detection/` tier taxonomy**: `tier1.py` through `tier4.py` suggest a cascaded entity type detection system. The exact scoring or heuristic logic at each tier was not read.
5. **`src/autom8_query_cli.py`**: Standalone CLI entry point (`pyproject.toml` scripts). Not read.
