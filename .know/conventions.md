---
domain: conventions
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

# Codebase Conventions

**Language**: Python 3.12 (confirmed via `pyproject.toml`, `requires-python = ">=3.12"`)
**Package root**: `src/autom8_asana/` (424 source files)
**Framework**: FastAPI (async-first), Pydantic v2, Polars dataframes
**Tooling**: `mypy --strict`, `ruff` (88-char lines, rules E/F/I/UP/B/G/LOG/TCH/TID/SIM)

## Error Handling Style

### Error Hierarchy Architecture

The project uses a **layered exception hierarchy** with four distinct exception families, each scoped to a domain:

```
Exception (Python built-in)
├── AsanaError  (src/autom8_asana/exceptions.py)
│   ├── AuthenticationError, ForbiddenError, NotFoundError, GoneError
│   ├── RateLimitError  (with retry_after attr)
│   ├── ServerError, TimeoutError, ConfigurationError
│   ├── CircuitBreakerOpenError, NameNotFoundError
│   ├── HydrationError, ResolutionError
│   ├── InsightsError -> InsightsValidationError, InsightsNotFoundError, InsightsServiceError
│   ├── ExportError
│   └── SaveOrchestrationError  (src/autom8_asana/persistence/exceptions.py)
│       ├── SessionClosedError, CyclicDependencyError, DependencyResolutionError
│       ├── PartialSaveError, UnsupportedOperationError, PositioningConflictError
│       ├── GidValidationError, SaveSessionError
│
├── Autom8Error  (src/autom8_asana/core/exceptions.py)
│   ├── TransportError  (transient=True)
│   │   ├── S3TransportError  (transient depends on error_code)
│   │   └── RedisTransportError
│   ├── CacheError  (transient=False)
│   │   └── CacheConnectionError  (transient=True)
│   └── AutomationError
│       ├── RuleExecutionError, SeedingError, PipelineActionError
│
├── ServiceError  (src/autom8_asana/services/errors.py)
│   ├── EntityNotFoundError -> UnknownEntityError, UnknownSectionError, TaskNotFoundError, EntityTypeMismatchError
│   ├── EntityValidationError -> InvalidFieldError, InvalidParameterError, NoValidFieldsError
│   ├── CacheNotReadyError, ServiceNotConfiguredError
│
├── QueryEngineError  (src/autom8_asana/query/errors.py)
│   └── QueryTooComplexError, UnknownFieldError, InvalidOperatorError, CoercionError, etc.
│
└── DataFrameError  (src/autom8_asana/dataframes/exceptions.py)
    └── SchemaNotFoundError, ExtractionError, TypeCoercionError, SchemaVersionError
```

### Error Creation Patterns

**Custom exception classes** are the rule -- raw `raise ValueError(...)` or `raise RuntimeError(...)` is rare. Error classes carry structured context:

- `AsanaError` and `Autom8Error` take `message: str` plus keyword-only context attributes (e.g., `entity_gid`, `cause`, `context: dict`).
- `ServiceError` subclasses carry strongly-typed context (e.g., `InvalidFieldError(invalid_fields, available_fields)`).
- `QueryEngineError` subclasses use `@dataclass` syntax to define fields.
- All hierarchies provide `to_dict()` for JSON serialization to API responses.

**Factory classmethods** are used at transport boundaries:
- `AsanaError.from_response(response)` parses HTTP responses into the most specific subclass.
- `S3TransportError.from_boto_error(error, *, operation, bucket, key)` wraps botocore at the boundary.
- `RedisTransportError.from_redis_error(error, *, operation)` wraps redis exceptions.

### Error Wrapping and Propagation

**Cause chaining** uses `self.__cause__ = cause` (not `raise X from Y`) when wrapping vendor exceptions. Example in `src/autom8_asana/persistence/exceptions.py:DependencyResolutionError.__init__`.

**Vendor isolation via error tuples**: `src/autom8_asana/core/exceptions.py` exports:
- `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`, `CACHE_TRANSIENT_ERRORS`, `ASANA_API_ERRORS`

These tuples are used in `except` clauses across the codebase so that upstream code never imports `botocore` or `redis` directly. Pattern seen in `src/autom8_asana/clients/base.py`:
```python
except CACHE_TRANSIENT_ERRORS as exc:
    logger.warning("cache_get_failed", ...)
    return None
```

**Graceful degradation** is the preferred pattern for cache failures: catch, log at `warning`, and return `None` or continue. This is called out explicitly as `NFR-DEGRADE-001` in comments.

### Error Handling at Boundaries

**API layer** (`src/autom8_asana/api/errors.py`): All `AsanaError` subclasses are registered with FastAPI's `exception_handler` in order (most specific first, catch-all last). Handlers return structured JSON:
```json
{"error": {"code": "RESOURCE_NOT_FOUND", "message": "..."}, "meta": {"request_id": "..."}}
```

Two utility functions used by route handlers:
- `raise_api_error(request_id, status_code, code, message)` -- for Tier 3 route-level validation.
- `raise_service_error(request_id, error: ServiceError)` -- converts `ServiceError` to `HTTPException`, preserving `error.to_dict()` fields.

**Service layer**: Services raise `ServiceError` subclasses only -- never HTTP exceptions. `ServiceError` carries `error_code` (machine-readable), `status_hint` (HTTP status), and `to_dict()`. Routes import `raise_service_error()` and never construct `HTTPException` directly.

**Error codes**: All exception types in `src/autom8_asana/services/errors.py` have uppercase snake-case `error_code` properties (e.g., `"UNKNOWN_ENTITY_TYPE"`, `"INVALID_FIELD"`, `"CACHE_NOT_WARMED"`). `SERVICE_ERROR_MAP` maps exception classes to HTTP status codes.

### Logging at Error Sites

`logger.warning(...)` for expected transient failures (cache miss, rate limit). `logger.error(...)` for upstream failures and unhandled SDK errors. `logger.exception(...)` for catch-all handler (includes stack trace). All logging uses keyword `extra={}` dict with `request_id` and `error_code` for structured output. The `autom8y_log.get_logger(__name__)` pattern is universal -- 155 files use it (100% compliance in significant files).

## File Organization

### Top-Level Package Structure

`src/autom8_asana/` contains these top-level modules and sub-packages:

| Path | Contents |
|------|----------|
| `client.py` | Public `AsanaClient` facade (entry point for SDK users) |
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
| `_defaults/` | Default factory implementations (prefixed `_` means internal) |
| `lambda_handlers/` | AWS Lambda handler entry points |

### Per-Package File Conventions

**Consistent naming idioms within packages:**
- `base.py` -- abstract base classes or shared mixins (`cache/backends/base.py`, `clients/base.py`, `dataframes/builders/base.py`, `dataframes/extractors/base.py`, `automation/workflows/base.py`)
- `models.py` -- Pydantic data models for the package domain
- `errors.py` or `exceptions.py` -- exception hierarchy for the package (`services/errors.py`, `persistence/exceptions.py`, `query/errors.py`, `dataframes/exceptions.py`)
- `config.py` -- `*Config` or `*Settings` dataclass for the package
- `engine.py` -- primary orchestration/execution class
- `registry.py` -- registry/catalog patterns
- `factory.py` -- factory functions or classes
- `protocol.py` -- `Protocol` interfaces (used inside packages alongside `protocols/` top-level)
- `__init__.py` -- explicit `__all__` exports; rarely contains implementation

**Sub-package depth pattern**: Packages nest logically, not arbitrarily. Example: `cache/` has `backends/`, `providers/`, `integration/`, `dataframe/`, `models/`, `policies/` sub-packages -- each representing a distinct concern layer.

**Private sub-packages**: `_defaults/` uses the `_` prefix to signal internal wiring defaults not intended for external import.

**Internal client sub-package**: `clients/data/` contains data-service client internals prefixed with `_` (e.g., `_retry.py`, `_response.py`, `_cache.py`, `_policy.py`, `_endpoints/`) following a convention that single-underscore filenames are private implementation details within the package.

### `__init__.py` Exports

Top-level `src/autom8_asana/__init__.py` exports the public SDK surface. Sub-package `__init__.py` files export the stable public API for that package using explicit `__all__`. The `services/errors.py` file ends with a canonical `__all__` list. This is the expected pattern for all public modules.

### Generated and Special Files

No generated code patterns are present in `src/`. The `_defaults/` directory holds default factory functions (not generated code). Lambda handlers in `lambda_handlers/` are one-file-per-handler with no shared state.

## Domain-Specific Idioms

### 1. GID (Globally Unique Identifier) as the Primary Key

All Asana entities are identified by `gid: str` (not `id`, not `uuid`). `AsanaResource` (base Pydantic model at `src/autom8_asana/models/base.py`) mandates `gid: str` on every resource. GID appears 649+ times across model files. New entity types must use `gid` as the identifier field name. Variable names throughout use `*_gid` (e.g., `workspace_gid`, `project_gid`, `task_gid`).

### 2. `@async_method` Descriptor (patterns/async_method.py)

`src/autom8_asana/patterns/async_method.py` defines the `@async_method` decorator, which auto-generates `{name}_async()` and `{name}()` pairs from a single async implementation. This is a project-specific metaprogramming pattern used across 154 files. Usage:
```python
@async_method
async def get(self, gid: str) -> Model:
    ...
# Generates: get_async(gid) -> coroutine, get(gid) -> blocking
```
When stacking, `@async_method` must be outermost (before `@error_handler`). The sync variant raises `SyncInAsyncContextError` if called from an async context (per ADR-0002).

### 3. Protocol-Driven Dependency Injection

Instead of concrete type injection, the project uses `Protocol` classes in `src/autom8_asana/protocols/` (`CacheProvider`, `AuthProvider`, `LogProvider`, `MetricsEmitter`, `DataFrameProvider`, `InsightsProvider`, `ItemLoader`, `ObservabilityHook`). Constructor arguments accept `Protocol | None` with graceful fallback when `None`. This is why `BaseClient.__init__` takes `cache_provider: CacheProvider | None = None`.

### 4. `RetryableErrorMixin` / Transient Classification

`Autom8Error` carries a class-level `transient: bool = False` attribute. Subclasses override it (`TransportError.transient = True`, `CacheConnectionError.transient = True`). `PartialSaveError.is_retryable` and `SaveResult.retryable_failures` use this to distinguish retryable from permanent failures. `S3TransportError.transient` is a property that checks `error_code` against a set of permanent AWS error codes.

### 5. `*Result` Return Objects (Not Exceptions for Partial Failures)

Operations that can partially succeed return `*Result` dataclasses rather than raising exceptions:
- `SaveResult` (persistence/models.py) -- contains `succeeded`, `failed`, `action_results`, `retryable_failures`
- `PartialSaveError` wraps `SaveResult` for callers that prefer exception-based handling
- `HealingResult`, `ProgressiveProjectBuilder` results, `FetchResult`, `BuildResult`

This avoids silent failures while keeping the happy path clean. Exception raising from result objects is explicit: `result.raise_on_failure()`.

### 6. `EntityRegistry` / Descriptor-Driven Registration

`src/autom8_asana/core/entity_registry.py` implements a singleton registry where entity types are registered as `EntityDescriptor` frozen dataclasses. The registry provides O(1) lookup by name, project GID, and `EntityType`. Downstream systems (schema discovery, extractor resolution, ENTITY_RELATIONSHIPS) are driven by the registry -- no hardcoded `match/case` branches. Import-time integrity validation catches triad inconsistencies (schema/extractor/row model).

### 7. `StrEnum` for Domain Enums

`StrEnum` (Python 3.11+) is the preferred enum base class for string-valued enums throughout the codebase: `EntryType`, `MutationType`, `EntityKind`, `FreshnessIntent`, `FreshnessState`, `ResolutionStatus`, `SectionStatus`, `Op`, `AggFunction`, `EventType`, `AuthMode`, etc. `IntEnum` is used rarely (only `CompletenessLevel`). Bare `Enum` is used for non-string state machines (`CircuitState`, `BuildStatus`, `WarmResult`). Non-standard pattern: `DispatchType(Enum)` in `src/autom8_asana/automation/workflows/insights_tables.py` (inconsistency -- most dispatch-like enums use `StrEnum`).

### 8. Event Envelope Pattern

`src/autom8_asana/automation/events/envelope.py` defines `EventEnvelope` -- a `frozen=True` dataclass with a `build()` static factory method (not `__init__` for caller use). This pattern of `@staticmethod def build(...)` on frozen dataclasses is repeated for objects that need auto-generated fields (UUID, timestamp).

### 9. `Autom8yBaseSettings` for All Configuration

Settings classes extend `autom8y_config.Autom8yBaseSettings` (not `pydantic_settings.BaseSettings` directly). 11 settings classes in `src/autom8_asana/settings.py` follow this pattern. Config is loaded once and accessed via `get_settings()` / `reset_settings()` (settings-module-level singleton pattern).

### 10. ADR/TDD Comment Markers

Source files consistently reference `Per ADR-XXXX:`, `Per TDD-XXXX:`, `Per FR-XXX:`, `Per PRD-XXX:` in docstrings to trace design decisions. This is load-bearing for understanding why code is shaped the way it is. Agent-generated code should include these markers if applicable.

## Naming Patterns

### Type Naming Conventions

**Exported type suffixes** are tightly standardized:
- `*Result` -- return types from operations that can partially fail (`SaveResult`, `HealingResult`, `BuildResult`, `FetchResult`, `WarmResult`)
- `*Config` -- configuration dataclasses (`RetryConfig`, `CircuitBreakerConfig`, `DataFrameConfig`, `TimeoutConfig`, `AIMDConfig`, `TieredConfig`)
- `*Settings` -- `Autom8yBaseSettings` subclasses for env-var-driven config (`AsanaSettings`, `CacheSettings`, `RedisSettings`, `ObservabilitySettings`)
- `*Error` / `*Exception` -- exception hierarchy classes (see Error Handling section)
- `*Registry` -- singleton lookup/catalog objects (`EntityRegistry`, `SchemaRegistry`, `WorkflowRegistry`, `MetricRegistry`)
- `*Provider` -- Protocol classes for DI (`CacheProvider`, `AuthProvider`, `LogProvider`, `DataFrameProvider`)
- `*Request` / `*Response` -- Pydantic API models (`CreateTaskRequest`, `SuccessResponse`, `ErrorResponse`)
- `*Builder` -- classes that construct complex objects step-by-step (`DataFrameBuilder`, `ProgressiveProjectBuilder`, `ActionBuilder`)
- `*Service` -- service classes in `services/` package (`EntityService`, `TaskService`, `QueryService`)
- `*Client` -- API client classes (`BaseClient`, `AsanaClient`, `DataServiceClient`)

### GID Variable Names

Entity-specific GID variables always use `{entity}_gid` suffix: `workspace_gid`, `project_gid`, `task_gid`, `section_gid`, `user_gid`. The field name on `AsanaResource` is `gid` (no prefix). This is the one place in the codebase where `ID` abbreviation appears: `gid` is always lowercase, never `GID` as a variable.

### Method Naming

- Async client methods: `get_async()`, `list_async()`, `create_async()`, `delete_async()`, `update_async()` -- generated by `@async_method`, with corresponding sync `get()`, `list()`, etc.
- Service methods: verb + noun (e.g., `get_entity_type()`, `write_fields_async()`, `fetch_tasks_async()`)
- Cache helper privates use `_cache_get()`, `_cache_set()`, `_cache_invalidate()` prefix
- Private methods use leading `_` per Python convention; no `__` (double underscore) mangling seen in non-dunder contexts

### Module-Level Logger

Every non-trivial module declares a module-level logger as the **first binding after imports**:
```python
logger = get_logger(__name__)
```
149 of 155 files with `from autom8y_log import get_logger` follow this exact variable name `logger`. The `__name__` argument is universal -- no custom logger names.

### Package / Module Naming

- All packages: `snake_case`, singular nouns (not `clients` as a plural exception -- this is the only plural top-level package name). Most packages are singular: `cache`, `query`, `persistence`, `model` etc. But `clients` and `models` are plural (existing patterns; do not create new plural packages).
- Private modules inside packages: `_underscore_prefix.py` (e.g., `clients/data/_retry.py`, `clients/data/_response.py`)
- `_defaults/` package: underscore-prefixed package name for internal wiring defaults

### Acronym Conventions

- `GID` in type names: abbreviated as `gid` in variable names, `Gid` in class names (`GidValidationError`, not `GIDValidationError`).
- `PAT` (Personal Access Token): appears as `pat` in attribute names (`settings.asana.pat`), `PAT` in class names (`BotPATError`).
- `TTL` (Time-to-live): `ttl` in variable names, `TTL` in constants (`DEFAULT_TTL`).
- `API` in class names: uppercase (`ApiSettings`, not `APISettings` -- one inconsistency: `api/` package is lowercase but `ApiSettings` not `APISettings`).
- `URL` in attribute names: lowercase `url` (e.g., `base_url`, `endpoint_url`).
- `GID`, `ID`, `URL`, `TTL` -- never uppercased mid-word in Python identifiers (follows PEP 8 style: treat as words).

### Anti-Patterns (Existing, Do Not Spread)

- `DispatchType(Enum)` in `src/autom8_asana/automation/workflows/insights_tables.py` uses base `Enum` instead of `StrEnum` -- inconsistent with all other dispatch-like enums.
- `CacheNotWarmError` in `src/autom8_asana/services/query_service.py:240` is a module-local exception not part of the `services/errors.py` hierarchy -- violates the pattern of centralizing service errors in `errors.py`.
- `MissingConfigurationError(Exception)` in `src/autom8_asana/cache/integration/autom8_adapter.py:57` does not inherit from `Autom8Error` or `AsanaError` -- inconsistent with the project hierarchy.
- Two different `ResolutionResult` classes exist: one in `src/autom8_asana/services/resolution_result.py` and one in `src/autom8_asana/resolution/result.py` -- naming collision across packages.

## Knowledge Gaps

1. **`_defaults/` package purpose**: Observed that `_defaults/` contains `auth.py`, `cache.py`, `log.py`, `observability.py` but did not read all four files to fully characterize the factory/default-wiring pattern. Likely returns provider instances for SDK users who do not want to provide their own.

2. **`@error_handler` decorator**: Referenced in `src/autom8_asana/patterns/async_method.py` docstring but not found in `src/autom8_asana/patterns/`. May live in transport or client package. Not fully characterized.

3. **`src/autom8_query_cli.py`**: Standalone CLI entry point (`pyproject.toml` scripts). Contains `from __future__ import annotations` and likely violates `TID251` (raw httpx) by design -- pyproject.toml explicitly exempts `"src/autom8_asana/query/__main__.py"` for `TID251`. Not read.

4. **`lifecycle/` state machine details**: The lifecycle package (`creation.py`, `completion.py`, `sections.py`, `wiring.py`, etc.) implements a task state machine but the exact transition triggers and guard conditions were not read.

5. **`models/business/` sub-model depth**: `models/business/` contains 40+ files with `business.py`, `unit.py`, `offer.py`, `contact.py`, `detection/`, `matching/` -- domain-specific business entity models. The full taxonomy was not read; detection tiers (`tier1.py` through `tier4.py`) suggest a cascaded entity type detection system.
