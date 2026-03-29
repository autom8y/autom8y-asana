---
domain: conventions
generated_at: "2026-03-29T18:30:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "905fe4b"
confidence: 0.95
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "1471b813f0f58342c542d2e8c9cd92aba095afec134846cda625c3fa545ec9fe"
---

# Codebase Conventions

**Language**: Python 3.12 (confirmed via `pyproject.toml`, `requires-python = ">=3.12"`)
**Package root**: `src/autom8_asana/` (424+ source files across 18 top-level sub-packages)
**Framework**: FastAPI (async-first), Pydantic v2, Polars dataframes
**Tooling**: `mypy --strict`, `ruff` (88-char lines, rules E/F/I/UP/B/G/LOG/TCH/TID/SIM)

## Error Handling Style

### Error Hierarchy Architecture

The project uses a **layered exception hierarchy** with five distinct exception families, each scoped to a domain:

```
Exception (Python built-in)
|-- AsanaError  (src/autom8_asana/exceptions.py)
|   |-- AuthenticationError, ForbiddenError, NotFoundError, GoneError
|   |-- RateLimitError  (with retry_after attr + from_response classmethod)
|   |-- ServerError, TimeoutError, ConfigurationError
|   |-- CircuitBreakerOpenError  (backend + operation attrs)
|   |-- NameNotFoundError  (resource_type, name, scope, suggestions, available_names)
|   |-- HydrationError  (entity_gid, entity_type, phase, partial_result, cause)
|   |-- ResolutionError  (entity_gid, strategies_tried, cause)
|   |-- InsightsError -> InsightsValidationError, InsightsNotFoundError, InsightsServiceError
|   |-- ExportError  (office_phone, reason)
|   +-- SaveOrchestrationError  (src/autom8_asana/persistence/exceptions.py)
|       |-- SessionClosedError, CyclicDependencyError, DependencyResolutionError
|       |-- PartialSaveError  (result: SaveResult, is_retryable, retryable_count)
|       |-- UnsupportedOperationError  (field_name, suggested_methods)
|       |-- PositioningConflictError  (insert_before, insert_after)
|       |-- GidValidationError, SaveSessionError
|
|-- RuntimeError (Python built-in)
|   +-- SyncInAsyncContextError  (method_name, async_method_name)
|
|-- Autom8Error  (src/autom8_asana/core/exceptions.py)
|   |-- TransportError  (transient=True, backend, operation)
|   |   |-- S3TransportError  (error_code, bucket, key; transient is property)
|   |   +-- RedisTransportError
|   |-- CacheError  (transient=False, cache_key)
|   |   +-- CacheConnectionError  (transient=True)
|   +-- AutomationError  (entity_gid)
|       |-- RuleExecutionError, SeedingError, PipelineActionError
|
|-- ServiceError  (src/autom8_asana/services/errors.py)
|   |-- EntityNotFoundError -> UnknownEntityError, UnknownSectionError,
|   |   TaskNotFoundError, EntityTypeMismatchError
|   |-- EntityValidationError -> InvalidFieldError, InvalidParameterError, NoValidFieldsError
|   |-- CacheNotReadyError, CascadeNotReadyError, ServiceNotConfiguredError
|
|-- QueryEngineError  (src/autom8_asana/query/errors.py)  [uses @dataclass]
|   +-- QueryTooComplexError, UnknownFieldError, InvalidOperatorError,
|       CoercionError, UnknownSectionError, AggregationError,
|       AggregateGroupLimitError, ClassificationError, JoinError
|
+-- DataFrameError  (src/autom8_asana/dataframes/exceptions.py)
    +-- SchemaNotFoundError, ExtractionError, TypeCoercionError,
        SchemaVersionError, DataFrameConstructionError
```

### Error Creation Patterns

Custom exception classes are the rule. Raw `raise ValueError(...)` is used only in validation guards; `raise RuntimeError(...)` is rare. Error classes carry structured context:

- **`AsanaError`**: takes `message: str` plus keyword-only `status_code`, `response`, `errors` list. All kwargs optional.
- **`Autom8Error`**: takes `message: str` plus keyword-only `context: dict[str, Any]`, `cause: Exception`. Has class-level `transient: bool` for retry classification.
- **`ServiceError`**: takes `message: str` only. Subclasses carry strongly-typed context as `__init__` arguments (e.g., `InvalidFieldError(invalid_fields: list[str], available_fields: list[str])`). Provides `error_code: str` (machine-readable uppercase), `status_hint: int` (HTTP status) as `@property` overrides, and `to_dict() -> dict[str, Any]` for JSON serialization.
- **`QueryEngineError`**: subclasses use `@dataclass` syntax. Each defines `to_dict()` returning `{"error": "CONSTANT_CODE", "message": "..."}` plus domain fields.
- **`DataFrameError`**: takes `message: str` plus keyword-only `context: dict[str, Any]`. Subclasses carry typed attributes (e.g., `ExtractionError(task_gid, field_name, original_error)`).

**`SERVICE_ERROR_MAP: dict[type[ServiceError], int]`** at `src/autom8_asana/services/errors.py:346` provides O(1) HTTP status lookup. `get_status_for_error()` walks MRO for most specific match, falling back to `error.status_hint`.

### Factory Classmethods

Factory classmethods create exceptions from raw inputs at transport boundaries:

| Factory | Location | Input |
|---------|----------|-------|
| `AsanaError.from_response(response)` | `src/autom8_asana/exceptions.py:62` | HTTP response -> most specific `AsanaError` subclass via `_STATUS_CODE_MAP` |
| `RateLimitError.from_response(response)` | `src/autom8_asana/exceptions.py:155` | HTTP response -> extracts `Retry-After` header |
| `S3TransportError.from_boto_error(error, *, operation, bucket, key)` | `src/autom8_asana/core/exceptions.py:131` | botocore exception -> extracts `error_code` from `ClientError.response` |
| `RedisTransportError.from_redis_error(error, *, operation)` | `src/autom8_asana/core/exceptions.py:177` | redis exception -> wraps with operation context |

### Error Wrapping and Propagation

**Cause chaining**: `self.__cause__ = cause` (explicit assignment in `__init__`) rather than `raise X from Y` when wrapping vendor exceptions. Seen consistently in `HydrationError`, `ResolutionError`, `DependencyResolutionError`, `TransportError`.

**Vendor isolation via error tuples**: `src/autom8_asana/core/exceptions.py` exports pre-built tuples for `except` clauses:
- `S3_TRANSPORT_ERRORS` -- `(S3TransportError, BotoCoreError, ClientError, ConnectionError, TimeoutError, OSError)`
- `REDIS_TRANSPORT_ERRORS` -- `(RedisTransportError, RedisError)`
- `ALL_TRANSPORT_ERRORS` -- union of S3 + Redis
- `CACHE_TRANSIENT_ERRORS` -- `ALL_TRANSPORT_ERRORS + (CacheConnectionError,)`
- `ASANA_API_ERRORS` -- `(AsanaError, ConnectionError, TimeoutError)`

Import-safe: tuples degrade gracefully via `try/except ImportError` when optional dependencies (`botocore`, `redis`) are absent.

**Transient classification**: `Autom8Error` carries `transient: bool = False` at class level. `TransportError` overrides to `True`. `S3TransportError.transient` is a `@property` checking `error_code` against a permanent-codes set. `PartialSaveError.is_retryable` delegates to `SaveResult.has_retryable_failures`.

**Degraded mode**: `DegradedModeMixin` at `src/autom8_asana/cache/models/errors.py:110` provides a state machine for cache backends (`enter_degraded_mode()`, `should_attempt_reconnect()`, `exit_degraded_mode()`). Error classification helpers `is_connection_error()`, `is_s3_not_found_error()`, `is_s3_retryable_error()` in the same module.

**Graceful degradation** is the preferred pattern for cache failures: catch, log at `warning`, return `None` or continue. Referenced as `NFR-DEGRADE-001`.

### Error Handling at Boundaries

**API layer** (`src/autom8_asana/api/errors.py`):
- `register_exception_handlers(app)` registers all `AsanaError` subclass handlers with FastAPI in specificity order (most specific first, catch-all `Exception` last).
- Handlers return structured JSON: `{"error": {"code": "...", "message": "..."}, "meta": {"request_id": "..."}}`
- `raise_api_error(request_id, status_code, code, message, *, details, headers) -> Never` -- Tier 3 route-level validation. Raises `HTTPException`.
- `raise_service_error(request_id, error: ServiceError, *, headers) -> Never` -- converts `ServiceError` to `HTTPException`, preserving `error.to_dict()` fields plus `request_id`. Uses `get_status_for_error()` for status code.

**Service layer**: Services raise `ServiceError` subclasses only -- never HTTP exceptions. Routes catch `ServiceError` and call `raise_service_error()`. Per `TDD-SERVICE-LAYER-001` / `ADR-SLE-003`.

**Route handler pattern** (canonical example from `src/autom8_asana/api/routes/tasks.py:123`):
```python
try:
    result = await task_service.list_tasks(client, ...)
except ServiceError as e:
    raise_service_error(request_id, e)
```

### Logging at Error Sites

- `logger.warning(...)` for expected transient failures (cache miss, rate limit, degraded mode entry).
- `logger.error(...)` for upstream failures (5xx, network errors).
- `logger.exception(...)` for catch-all handler only (includes stack trace automatically).
- `logger.info(...)` for auth failures (expected but notable).
- All log calls use `extra={}` dict for structured output. Event names are `snake_case` strings: `"manifest_parse_failed"`, `"authentication_failed"`, `"upstream_timeout"`.
- `autom8y_log.get_logger(__name__)` pattern is universal -- 176+ files use `get_logger`, assigned to module-level `logger` variable.

### Known Exception Hierarchy Violations

- `CacheNotWarmError` at `src/autom8_asana/services/query_service.py:240` -- module-local, not in `services/errors.py` hierarchy.
- `MissingConfigurationError(Exception)` at `src/autom8_asana/cache/integration/autom8_adapter.py:57` -- does not inherit from `Autom8Error` or `AsanaError`.
- `ResolutionError(Exception)` at `src/autom8_asana/resolution/context.py:440` -- standalone definition that duplicates `exceptions.py:ResolutionError`.

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
| `api/` | FastAPI routes, models, middleware, dependencies, lifespan, client_pool, startup |
| `auth/` | Authentication providers (JWT, PAT, dual-mode, audit) |
| `automation/` | Automation engine, workflows, events, polling, seeding, templates |
| `batch/` | Batch API client and models |
| `cache/` | Cache backends, providers, integration, dataframe cache, models, policies |
| `clients/` | Per-resource Asana API clients (tasks, projects, sections, etc.) + `data/` for external service |
| `core/` | Cross-cutting utilities: entity registry, retry, datetime, types, concurrency, scope |
| `dataframes/` | Polars DataFrame pipeline: builders, extractors, schemas, storage, resolvers, views |
| `lambda_handlers/` | AWS Lambda handler entry points |
| `lifecycle/` | Task lifecycle state machine (creation, completion, sections, wiring) |
| `metrics/` | Metrics computation and expression engine |
| `models/` | Pydantic models for Asana API resources; `models/business/` for domain models |
| `observability/` | `@error_handler` decorator, tracing, and correlation context |
| `patterns/` | Reusable cross-cutting patterns (`async_method.py`, `error_classification.py`) |
| `persistence/` | Save session, dependency graph, action executor, healing, cascade |
| `protocols/` | `Protocol` interfaces for dependency injection |
| `query/` | Query engine: compiler, engine, fetcher, models, errors, join, aggregator |
| `reconciliation/` | Payment reconciliation (currently empty Python package) |
| `resolution/` | Entity resolution strategies, context, field resolver, write registry |
| `search/` | Text search service and models |
| `services/` | Business service layer between routes and clients |
| `transport/` | HTTP transport, adaptive semaphore, sync wrapper, config translator |
| `_defaults/` | Default factory implementations (`_` prefix = internal) |

### Per-Package File Naming Conventions

Consistent naming within packages:
- `base.py` -- abstract base classes or shared mixins (`cache/backends/base.py`, `clients/base.py`, `dataframes/builders/base.py`, `dataframes/extractors/base.py`, `automation/workflows/base.py`, `automation/base.py`)
- `models.py` -- Pydantic data models or dataclasses for the package domain
- `errors.py` or `exceptions.py` -- exception hierarchy for the package. `errors.py` in `services/`, `query/`, `api/`, `cache/models/`; `exceptions.py` in `persistence/`, `dataframes/`, `core/`, top-level
- `config.py` -- `*Config` or `*Settings` dataclass for the package
- `engine.py` -- primary orchestration/execution class (`query/engine.py`, `automation/engine.py`, `lifecycle/engine.py`)
- `registry.py` -- registry/catalog patterns
- `factory.py` -- factory functions or classes
- `protocol.py` -- `Protocol` interfaces (inside packages; top-level `protocols/` package holds shared protocols)
- `__init__.py` -- explicit `__all__` exports; rarely contains implementation logic (exception: `models/__init__.py` does `model_rebuild` orchestration)

### Sub-Package Depth Pattern

Packages nest by concern layer:
- `cache/` has `backends/`, `providers/`, `integration/`, `dataframe/`, `models/`, `policies/`
- `api/routes/` is flat with route modules and co-located `{route}_models.py`
- `clients/data/` has `_endpoints/` sub-package for endpoint-specific logic with `_` prefix private modules
- `models/business/` has `detection/`, `matching/` sub-packages
- `automation/` has `events/`, `polling/`, `workflows/` (workflows further nests per-workflow packages)

### Route-Model Co-location Pattern

`api/routes/` co-locates Pydantic models with their route handler:
- `intake_create.py` + `intake_create_models.py`
- `intake_resolve.py` + `intake_resolve_models.py`
- `intake_custom_fields.py` + `intake_custom_fields_models.py`
- `resolver.py` + `resolver_models.py` + `resolver_schema.py`
- `matching.py` + `matching_models.py`

### Private Module Convention

Single-underscore prefix signals package-private modules: `clients/data/_retry.py`, `_response.py`, `_cache.py`, `_policy.py`, `_pii.py`, `_normalize.py`, `_metrics.py`. The `_defaults/` package uses underscore prefix for internal wiring defaults.

### `__init__.py` Exports

All public modules use explicit `__all__`. Top-level `src/autom8_asana/__init__.py` exports the SDK public surface with lazy `__getattr__` for dataframe exports (avoids pulling in Polars for consumers that only need core API). Sub-package `__init__.py` files export the stable package API.

### File-Level Header Pattern

All files use:
1. Module docstring with ADR/TDD references (e.g., `Per TDD-SERVICE-LAYER-001`, `Per ADR-SLE-003`)
2. `from __future__ import annotations` (396 files -- universal)
3. Stdlib imports, then third-party, then local (enforced by ruff isort, `known-first-party = ["autom8_asana"]`)
4. `if TYPE_CHECKING:` block for type-only imports
5. `__all__` at module top or bottom
6. `logger = get_logger(__name__)` as first binding after imports (in files that log)

## Domain-Specific Idioms

### 1. GID as the Primary Key

All Asana entities are identified by `gid: str` (not `id`, not `uuid`). `AsanaResource` at `src/autom8_asana/models/base.py:30` mandates `gid: str` with description "Globally unique identifier... A 16-digit numeric string." Variable names use `{entity}_gid` suffix: `workspace_gid`, `project_gid`, `task_gid`, `section_gid`, `entity_gid`, `user_gid`. The field on the model is `gid` (no prefix). GID validation is enforced at track-time via `GidValidationError` (per `ADR-0049`, `FR-VAL-001`).

### 2. DataFrame Source Annotation Protocol

`ColumnDef.source` uses a string DSL:
- `"gid"` / `"name"` / `"created_at"` etc. -- direct Asana task attributes
- `"cf:Field Name"` -- resolves to a custom field named "Field Name" in Asana
- `"cascade:Field Name"` -- cascades from a parent entity's field
- `source=None` -- derived column (custom extraction logic in extractor)

Examples in `src/autom8_asana/dataframes/schemas/unit.py` and `src/autom8_asana/dataframes/schemas/contact.py`. This DSL is unique to this project.

### 3. `@async_method` Descriptor

`src/autom8_asana/patterns/async_method.py` defines `@async_method`, which generates `{name}_async()` (coroutine) and `{name}()` (sync wrapper via `asyncio.run()`) from a single async implementation. Uses `__set_name__` descriptor protocol to inject both methods at class definition time. Sync variant raises `SyncInAsyncContextError` if called from an async context (per `ADR-0002`).

**Stacking rule**: `@async_method` must be outermost when combined with `@error_handler`:
```python
@async_method  # outermost
@error_handler
async def get(self, gid: str) -> Model:
    ...
```

### 4. `@error_handler` Decorator

`src/autom8_asana/observability/decorators.py` defines `@error_handler` for async client methods. Provides: correlation ID generation, consistent error logging, exception enrichment with correlation data, operation timing. Applied to all client methods (tasks, sections, projects, etc.). Expects decorated method's class to have `_log` attribute (`LogProvider | None`).

### 5. Protocol-Driven Dependency Injection

`src/autom8_asana/protocols/` holds shared `Protocol` classes: `CacheProvider`, `AuthProvider`, `LogProvider`, `MetricsEmitter`, `DataFrameProvider`, `InsightsProvider`, `ItemLoader`, `ObservabilityHook`, `DataFrameCacheProtocol`. Constructor arguments accept `Protocol | None` with graceful fallback when `None`. All protocols are exported via `protocols/__init__.py` with `__all__`.

### 6. `*Result` Return Objects for Partial Failures

Operations that can partially succeed return `*Result` dataclasses rather than raising exceptions:
- `SaveResult` (`persistence/models.py`) -- `succeeded`, `failed`, `action_results`, `retryable_failures`, `non_retryable_failures`
- `BuildResult` (`dataframes/builders/build_result.py`) -- section results with success/failure tracking
- `HydrationResult`, `ResolutionResult`, `CascadeResult`, `WarmResult`, `WriteFieldsResult`, `QueryResult`, `DataFrameResult`, `FreshnessResult`

**Pattern**: `result.raise_on_failure()` is the explicit opt-in for exception conversion. `PartialSaveError` wraps `SaveResult` for callers preferring exception-based handling.

### 7. `EntityRegistry` / Descriptor-Driven Registration

`src/autom8_asana/core/entity_registry.py` implements a singleton registry accessed via `get_registry()`. Entity types are registered as `EntityDescriptor` frozen dataclasses (`@dataclass(frozen=True, slots=True)`) in `ENTITY_DESCRIPTORS` tuple. Registry provides O(1) lookup by name, project GID, and `EntityType`. All downstream systems are driven by descriptor paths:
- `schema_module_path` -- dotted path to schema constant (auto-discovered, no hardcoded imports)
- `extractor_class_path` -- dotted path to extractor class
- `row_model_class_path` -- dotted path to row model
- `model_class_path` -- dotted path to business model class
- `custom_field_resolver_class_path` -- dotted path to resolver

Import-time integrity validation (checks 6a-6f) catches schema/extractor/row model triad inconsistencies.

### 8. `StrEnum` for Domain Enums

`StrEnum` (Python 3.11+) is the preferred base class for string-valued enums: `EntityCategory`, `MutationType`, `EntityKind`, `ResolutionStatus`, `SectionStatus`, `FreshnessIntent`, `FreshnessState`, `AuthMode`, `ActionType`, `EventType`, `Op`, `AggFunction`, `BuildOutcome`, `ProbeVerdict`, `ProcessType`, `ProcessSection`, `OfferSection`, `AccountActivity`. Plain `Enum` is used for non-string state machines.

### 9. `EventEnvelope` Pattern

`src/autom8_asana/automation/events/envelope.py` defines `EventEnvelope` -- a `frozen=True` dataclass with immutable fields (`schema_version`, `event_id`, `event_type`, `entity_type`, `entity_gid`, `timestamp`, `source`, `correlation_id`, `causation_id`, `payload`). Uses `build()` static factory method (not direct `__init__`) for objects with auto-generated fields (UUID, timestamp).

### 10. `Autom8yBaseSettings` for All Configuration

All settings classes extend `autom8y_config.Autom8yBaseSettings` (not `pydantic_settings.BaseSettings` directly). `src/autom8_asana/settings.py` contains settings classes covering 60+ environment variables. Config accessed via `get_settings()` / `reset_settings()` singleton pattern. `ruff` marks `pydantic.BaseModel` and `pydantic_settings.BaseSettings` as `runtime-evaluated-base-classes` for type-checking import optimization.

### 11. ADR/TDD Comment Markers

Source files consistently reference `Per ADR-XXXX:`, `Per TDD-XXXX:`, `Per FR-XXX:`, `Per PRD-XXX:` in docstrings to trace design decisions. 1358+ occurrences across 250+ files. These are load-bearing references -- new code should include them when applicable.

### 12. SDK-Only Import Enforcement (ruff TID251)

`pyproject.toml` bans direct imports via ruff's `flake8-tidy-imports.banned-api`:
- `loguru`, `loguru.logger` -- use `autom8y_log.get_logger()` instead
- `structlog` -- use `autom8y_log.get_logger()` instead
- `httpx`, `httpx.AsyncClient`, `httpx.Client` -- use `autom8y_http.Autom8yHttpClient` instead

Violations are CI-blocking. The platform SDK layer (`autom8y_http`, `autom8y_log`, `autom8y_config`, `autom8y_cache`, `autom8y_core`) wraps all vendor dependencies.

### 13. Pydantic v2 Model Configuration

`AsanaResource` base model at `src/autom8_asana/models/base.py` uses `ConfigDict(extra="ignore", populate_by_name=True, str_strip_whitespace=True)`. `extra="ignore"` ensures forward compatibility when Asana adds new API fields. All resource models inherit this. `NameGid` forward references require `model_rebuild(_types_namespace=...)` orchestrated in `models/__init__.py`.

### 14. `@dataclass(frozen=True)` for Value Objects

Configuration, result, and scope objects use `@dataclass(frozen=True)` for immutability and thread safety: all `*Config` in `config.py`, `CorrelationContext`, `DataFrameResult`, `ResolutionResult`, `EntityDescriptor`, `HealthCheckResult`, `ActionConfig`. Mutable result accumulators (builders, coordinators) use `@dataclass` without `frozen`.

## Naming Patterns

### Exported Type Suffixes

Tightly standardized naming suffixes:

| Suffix | Usage | Examples |
|--------|-------|---------|
| `*Result` | Return types from partial-failure operations | `SaveResult`, `BuildResult`, `HydrationResult` |
| `*Config` | Configuration dataclasses | `RetryConfig`, `CircuitBreakerConfig`, `DataFrameConfig` |
| `*Settings` | `Autom8yBaseSettings` subclasses | `StalenessCheckSettings`, `CacheSettings`, `TTLSettings` |
| `*Error` | Exception hierarchy classes | `ServiceError`, `DataFrameError`, `TransportError` |
| `*Registry` | Singleton lookup/catalog objects | `EntityRegistry`, `SchemaRegistry`, `WorkflowRegistry` |
| `*Provider` | Protocol classes for DI | `CacheProvider`, `AuthProvider`, `DataFrameProvider` |
| `*Request` / `*Response` | Pydantic API models | `CreateTaskRequest`, `SuccessResponse`, `ErrorResponse` |
| `*Builder` | Step-by-step construction | `DataFrameBuilder`, `ActionBuilder`, `ProgressiveProjectBuilder` |
| `*Service` | Service-layer classes | `TaskService`, `EntityService`, `FieldWriteService` |
| `*Client` | API client classes | `BaseClient`, `AsanaClient`, `DataServiceClient` |
| `*Mixin` | Mixin classes | `HolderMixin`, `DegradedModeMixin` |
| `*Descriptor` | Entity metadata classes | `EntityDescriptor` |

### GID Variable Convention

Entity-specific GID variables always use `{entity}_gid` suffix: `workspace_gid`, `project_gid`, `task_gid`, `section_gid`, `user_gid`, `entity_gid`. The field name on `AsanaResource` is `gid` (unprefixed). In class names, `Gid` (not `GID`): `GidValidationError`, `validate_gid()`.

### Method Naming

- **Async client methods**: `get_async()`, `list_async()`, `create_async()`, `delete_async()`, `update_async()` -- generated by `@async_method`, with corresponding sync variants `get()`, `list()`, etc.
- **Service methods**: verb + noun (`get_entity_type()`, `write_fields_async()`, `fetch_tasks_async()`).
- **Private helpers**: leading `_` per Python convention; no `__` double-underscore mangling in non-dunder contexts.

### Module-Level Logger

Every non-trivial module declares a module-level logger as the first binding after imports:
```python
from autom8y_log import get_logger
logger = get_logger(__name__)
```
176+ files use `get_logger`, assigned to variable `logger` (100% consistent name). The `__name__` argument is universal. Never `logging.getLogger()`.

### Log Message Naming (Structured Events)

Logging event names use `snake_case` strings naming the event being observed (not interpolated): `"manifest_parse_failed"`, `"cascade_key_null_audit"`, `"event_emission_disabled"`, `"authentication_failed"`, `"pipeline_using_fixed_assignee"`, `"upstream_timeout"`, `"backend_entering_degraded_mode"`. Context is passed as keyword arguments or `extra={}` dict, not embedded in the message string.

### Package / Module Naming

- All packages: `snake_case`. Most are singular nouns. `clients` and `models` are plural (existing pattern -- do not create new plural packages).
- Private modules inside packages: `_underscore_prefix.py`.
- `_defaults/` package uses underscore-prefixed package name.

### Acronym Conventions

- `GID`: `gid` in variable names, `Gid` in class names (`GidValidationError`).
- `PAT` (Personal Access Token): `pat` in attribute names, `PAT` in class names (`BotPATError`).
- `TTL`: `ttl` in variable names, `TTL` in constants (`DEFAULT_TTL`).
- `URL`: lowercase `url` in attribute names (`base_url`, `endpoint_url`).
- `API`: `Api` in class names (not `API`), lowercase in package names.
- `HTTP`: lowercase `http` in variable names (`self._http`).

### Existing Naming Anti-Patterns (Do Not Spread)

- `CacheNotWarmError` at `src/autom8_asana/services/query_service.py:240` -- module-local, not in `services/errors.py`.
- `MissingConfigurationError(Exception)` at `src/autom8_asana/cache/integration/autom8_adapter.py:57` -- not in hierarchy.
- `ResolutionError(Exception)` at `src/autom8_asana/resolution/context.py:440` -- duplicates `exceptions.py:ResolutionError`.
- Two `ResolutionResult` classes exist across packages (naming collision: `services/resolution_result.py` vs `resolution/result.py` vs `models/business/resolution.py`).

## Knowledge Gaps

1. **`lifecycle/` transition guards**: The exact state machine triggers and guard conditions for creation/completion/sections/wiring were not read in detail. Known to exist but internal logic not documented.
2. **`models/business/detection/` tier taxonomy**: `tier1.py` through `tier4.py` suggest a cascaded entity type detection system. The exact scoring or heuristic logic at each tier was not read.
3. **`automation/workflows/` workflow lifecycle**: Individual workflow implementations (`conversation_audit`, `payment_reconciliation`, `pipeline_transition`, `section_resolution`, `insights`) were not read for internal conventions.
4. **`reconciliation/` package**: Currently appears empty (only `__pycache__`). May be pending implementation.

```metadata
overall_grade: A
overall_percentage: 94.5%
confidence: 0.95
criteria_grades:
  error_handling_style: A
  file_organization: A
  domain_specific_idioms: A
  naming_patterns: A
```
