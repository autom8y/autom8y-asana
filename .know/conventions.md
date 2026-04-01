---
domain: conventions
generated_at: "2026-04-01T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "24d8e44"
confidence: 0.92
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

### Exception Hierarchy Architecture

The codebase maintains four distinct exception hierarchies, one per layer:

**1. SDK-level: `AsanaError` tree** (`src/autom8_asana/exceptions.py`)

Root is `AsanaError(Exception)`. All Asana API errors inherit from it. Factory method `AsanaError.from_response(response)` constructs the most specific subclass from an HTTP response using `_STATUS_CODE_MAP`.

```
AsanaError
  AuthenticationError (401)
  ForbiddenError (403)
  NotFoundError (404)
  GoneError (410)
  RateLimitError (429) -- adds retry_after attribute, overrides from_response()
  ServerError (5xx)
  TimeoutError
  ConfigurationError
  CircuitBreakerOpenError -- adds backend/operation attributes
  NameNotFoundError -- rich context: resource_type, name, scope, suggestions
  HydrationError -- adds entity_gid, phase, partial_result, __cause__
  ResolutionError -- adds entity_gid, strategies_tried, __cause__
  InsightsError -> InsightsValidationError, InsightsNotFoundError, InsightsServiceError
  ExportError -- adds office_phone, reason
```

The `SaveOrchestrationError` tree also inherits `AsanaError`:
```
SaveOrchestrationError
  SessionClosedError, CyclicDependencyError, DependencyResolutionError
  PartialSaveError, UnsupportedOperationError, PositioningConflictError
  GidValidationError, SaveSessionError
```

**2. Service-layer: `ServiceError` tree** (`src/autom8_asana/services/errors.py`)

Services raise `ServiceError` subclasses, never HTTP or framework exceptions. Each subclass carries `error_code` (machine-readable string), `status_hint` (suggested HTTP code), and `to_dict()` for serialization.

`SERVICE_ERROR_MAP: dict[type[ServiceError], int]` at `src/autom8_asana/services/errors.py:346` provides O(1) HTTP status lookup. `get_status_for_error()` walks MRO for most specific match.

**3. API-layer: `ApiError` tree** (`src/autom8_asana/api/exceptions.py`)

Replaces bare `HTTPException` raises. Each carries `code`, `message`, `status_code`, `details`, `headers`.

**4. Infrastructure: `Autom8Error` tree** (`src/autom8_asana/core/exceptions.py`)

For transport and cache subsystem errors. Carries `transient: bool` class attribute for retry classification, and `context: dict` for structured logging.

**5. Domain-specific hierarchies:**

- `DataFrameError` (`src/autom8_asana/dataframes/exceptions.py`) -- carries `context: dict`
- `QueryEngineError` (`src/autom8_asana/query/errors.py`) -- uses `@dataclass`, carries `to_dict()` for HTTP bodies

### Error Propagation Rules

**Services never import HTTP types.** Per ADR-SLE-003, services raise `ServiceError` subclasses. Route handlers convert via `raise_service_error(request_id, e)`.

**Routes never use bare `HTTPException`.** All error sites use typed exceptions caught by registered handlers in `src/autom8_asana/api/errors.py`.

The route pattern is:
```python
try:
    result = await task_service.some_operation(...)
except ServiceError as e:
    raise_service_error(request_id, e)
```

For route-level validation:
```python
raise_api_error(request_id, 400, "INVALID_ENTITY_TYPE", "message")
```

### Two-Tier Error Handling at API Boundary

Per ADR-I6-001:
- **Tier 1**: Registered exception handlers (automatic, catches SDK/AsanaError/ApiError)
- **Tier 2**: `raise_service_error(request_id, e)` in route `except ServiceError` blocks
- **Tier 3**: `raise_api_error(request_id, status, code, message)` for route-specific validation

### Error Codes

Machine-readable error codes use `SCREAMING_SNAKE_CASE`: `RESOURCE_NOT_FOUND`, `INVALID_CREDENTIALS`, `FORBIDDEN`, `RATE_LIMITED`, `VALIDATION_ERROR`, `UPSTREAM_ERROR`, `UPSTREAM_TIMEOUT`, `INTERNAL_ERROR`, `CACHE_NOT_WARMED`, `CASCADE_NOT_READY`, `MISSING_AUTH`, `INVALID_SCHEME`, `MISSING_TOKEN`, `INVALID_TOKEN`, `S2S_NOT_CONFIGURED`, `CACHE_BUILD_IN_PROGRESS`, `DATAFRAME_BUILD_UNAVAILABLE`.

### Error Response Format

All API error responses use the `ErrorResponse` envelope:
```json
{
  "error": {"code": "RESOURCE_NOT_FOUND", "message": "..."},
  "meta": {"request_id": "..."}
}
```

Exception handlers registered in order, most specific first. Registration in `register_exception_handlers()` in `src/autom8_asana/api/errors.py`.

### Cause Chaining

When wrapping external exceptions, use `self.__cause__ = cause` (not `raise ... from ...` at class level) in custom exception `__init__` methods.

### Convenience Error Tuples

For `except` clauses that need to catch vendor errors:
- `S3_TRANSPORT_ERRORS` -- includes `S3TransportError` + botocore types (import-safe)
- `REDIS_TRANSPORT_ERRORS` -- includes `RedisTransportError` + redis types
- `ALL_TRANSPORT_ERRORS`, `CACHE_TRANSIENT_ERRORS`, `ASANA_API_ERRORS` -- all in `src/autom8_asana/core/exceptions.py`

### Logging at Error Sites

- `logger.warning(...)` for expected transient failures
- `logger.error(...)` for upstream failures (5xx, network errors)
- `logger.exception(...)` for catch-all handler only
- `logger.info(...)` for auth failures (expected but notable)
- All log calls use `extra={}` dict for structured output
- Event names are `snake_case` strings: `"manifest_parse_failed"`, `"authentication_failed"`, `"upstream_timeout"`
- `autom8y_log.get_logger(__name__)` pattern is universal -- 178+ files, assigned to module-level `logger`

### Known Exception Hierarchy Violations

- `CacheNotWarmError` at `src/autom8_asana/services/query_service.py:240` -- module-local
- `MissingConfigurationError(Exception)` at `src/autom8_asana/cache/integration/autom8_adapter.py:57` -- not in hierarchy
- `ResolutionError(Exception)` at `src/autom8_asana/resolution/context.py:440` -- duplicates `exceptions.py:ResolutionError`

## File Organization

### Top-Level Package Structure

| Package | Role |
|---------|------|
| `api/` | FastAPI service layer: routes, dependencies, middleware, error handlers, models |
| `clients/` | Low-level Asana API clients (one per resource type) |
| `services/` | Business logic services (one per use case) |
| `models/` | Pydantic domain models; `models/business/` for complex business entities |
| `persistence/` | Save orchestration layer (Unit of Work, dependency graph, actions) |
| `cache/` | Multi-tier cache subsystem (backends, policies, integration, dataframe) |
| `dataframes/` | DataFrame build pipeline (builders, extractors, views, resolver, schemas) |
| `lifecycle/` | Entity lifecycle orchestration (creation, completion, wiring, seeding) |
| `automation/` | Automation rules, workflows, polling, events |
| `resolution/` | Field/GID resolution strategies |
| `query/` | Composable query engine |
| `search/` | Search service |
| `reconciliation/` | Payment reconciliation bridge |
| `metrics/` | Business metric computation |
| `core/` | Cross-cutting infrastructure: logging, retry, registry, types, concurrency |
| `_defaults/` | Default provider implementations (log, cache, auth, observability) |
| `protocols/` | Protocol definitions (log, cache, metrics, observability) |
| `patterns/` | Shared patterns: `@async_method`, `RetryableErrorMixin` |
| `lambda_handlers/` | AWS Lambda entry points |
| `transport/` | HTTP transport layer |
| `auth/` | Authentication helpers (bot PAT, JWT, dual mode) |
| `batch/` | Batch operation support |
| `observability/` | Correlation and tracing |

### Per-Package File Naming Conventions

- `base.py` -- abstract base classes or shared mixins
- `models.py` -- Pydantic data models or dataclasses for the package domain
- `errors.py` or `exceptions.py` -- exception hierarchy for the package
- `config.py` -- `*Config` or `*Settings` dataclass
- `engine.py` -- primary orchestration/execution class
- `registry.py` -- registry/catalog patterns
- `factory.py` -- factory functions or classes
- `__init__.py` -- explicit `__all__` exports; rarely contains implementation logic

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

All public modules use explicit `__all__`. Top-level `src/autom8_asana/__init__.py` exports the SDK public surface with lazy `__getattr__` for dataframe exports (avoids pulling in Polars for consumers that only need core API).

### File-Level Header Pattern

1. Module docstring with ADR/TDD references (e.g., `Per TDD-SERVICE-LAYER-001`, `Per ADR-SLE-003`)
2. `from __future__ import annotations` (universal)
3. Stdlib imports, then third-party, then local (enforced by ruff isort)
4. `if TYPE_CHECKING:` block for type-only imports
5. `__all__` at module top or bottom
6. `logger = get_logger(__name__)` as first binding after imports

## Domain-Specific Idioms

### 1. Async/Sync Method Pairs via `@async_method`

`src/autom8_asana/patterns/async_method.py` defines `@async_method`, which generates `{name}_async()` (coroutine) and `{name}()` (sync wrapper). Sync variant raises `SyncInAsyncContextError` if called from async context (per ADR-0002).

Stacking rule: `@async_method` must be outermost when combined with `@error_handler`:
```python
@async_method  # outermost
@error_handler
async def get(self, gid: str) -> Model:
    ...
```

### 2. GID as Domain Term

All Asana entities identified by `gid: str`. Variable names use `{entity}_gid` suffix. `GidValidationError` for invalid GIDs. Never abbreviated as `id`.

### 3. `Annotated` Typed Dependency Aliases

FastAPI dependencies aliased as `Annotated` type aliases:
```python
RequestId = Annotated[str, Depends(get_request_id)]
TaskServiceDep = Annotated["TaskService", Depends(get_task_service)]
```

### 4. `SuccessResponse[T]` Envelope

All successful API responses use `SuccessResponse[T]` from `autom8y_api_schemas`. The helper `build_success_response(data=..., request_id=...)` constructs it. Never return raw dicts.

### 5. `ServiceError.to_dict()` Serialization Contract

Service errors serialize via `to_dict()` which returns `{"error": self.error_code, "message": self.message, ...extra_fields}`. Route handlers inject `request_id`.

### 6. Protocol-Driven Dependency Injection

`src/autom8_asana/protocols/` holds shared `Protocol` classes: `CacheProvider`, `AuthProvider`, `LogProvider`, `MetricsEmitter`, `DataFrameProvider`, etc. Constructor arguments accept `Protocol | None` with graceful fallback.

### 7. `*Result` Return Objects for Partial Failures

Operations that can partially succeed return `*Result` dataclasses: `SaveResult`, `BuildResult`, `HydrationResult`, `ResolutionResult`, `CascadeResult`, etc. Pattern: `result.raise_on_failure()` is explicit opt-in for exception conversion.

### 8. `EntityRegistry` / Descriptor-Driven Registration

`src/autom8_asana/core/entity_registry.py` implements a singleton registry. Entity types registered as `EntityDescriptor` frozen dataclasses. Registry provides O(1) lookup by name, project GID, and `EntityType`. Import-time integrity validation.

### 9. `StrEnum` for Domain Enums

`StrEnum` (Python 3.11+) is the preferred base for string-valued enums. Plain `Enum` for non-string state machines.

### 10. `Autom8yBaseSettings` for All Configuration

All settings extend `autom8y_config.Autom8yBaseSettings`. Accessed via `@lru_cache`-wrapped `get_settings()`.

### 11. ADR/TDD Comment Markers

Source files reference `Per ADR-XXXX:`, `Per TDD-XXXX:`, `Per FR-XXX:`, `Per PRD-XXX:` in docstrings. 1358+ occurrences. New code should include them when applicable.

### 12. SDK-Only Import Enforcement (ruff TID251)

`pyproject.toml` bans direct imports: `loguru`, `structlog`, `httpx`. Use platform wrappers: `autom8y_log.get_logger()`, `autom8y_http.Autom8yHttpClient`, etc. Violations are CI-blocking.

### 13. `@dataclass(frozen=True)` for Value Objects

Configuration, result, and scope objects use `@dataclass(frozen=True)` for immutability: all `*Config` in `config.py`, `CorrelationContext`, `DataFrameResult`, `EntityDescriptor`. Mutable accumulators use `@dataclass` without `frozen`.

### 14. `frozenset` for Constant Membership Sets

Immutable sets of string constants use `frozenset[str]` with `SCREAMING_SNAKE_CASE`. Module-private sets use leading `_` prefix.

## Naming Patterns

### Exported Type Suffixes

| Suffix | Usage | Examples |
|--------|-------|---------|
| `*Result` | Partial-failure return types | `SaveResult`, `BuildResult`, `HydrationResult` |
| `*Config` | Configuration dataclasses | `RetryConfig`, `CircuitBreakerConfig` |
| `*Settings` | `Autom8yBaseSettings` subclasses | `StalenessCheckSettings`, `CacheSettings` |
| `*Error` | Exception hierarchy classes | `ServiceError`, `DataFrameError` |
| `*Registry` | Singleton lookup objects | `EntityRegistry`, `SchemaRegistry` |
| `*Provider` | Protocol classes for DI | `CacheProvider`, `AuthProvider` |
| `*Request` / `*Response` | Pydantic API models | `CreateTaskRequest`, `SuccessResponse` |
| `*Builder` | Step-by-step construction | `DataFrameBuilder`, `ProgressiveProjectBuilder` |
| `*Service` | Service-layer classes | `TaskService`, `EntityService` |
| `*Client` | API client classes | `BaseClient`, `AsanaClient` |
| `*Mixin` | Mixin classes | `HolderMixin`, `DegradedModeMixin` |

### GID Variable Convention

Entity-specific GID variables: `{entity}_gid`. In class names, `Gid` (not `GID`): `GidValidationError`, `validate_gid()`.

### Method Naming

- Async client methods: `get_async()`, `list_async()` -- generated by `@async_method`, with sync variants `get()`, `list()`
- Service methods: verb + noun (`get_entity_type()`, `write_fields_async()`)
- Private helpers: leading `_`

### Module-Level Logger

```python
from autom8y_log import get_logger
logger = get_logger(__name__)
```
178+ files, 100% consistent name. Never `logging.getLogger()`.

### Acronym Conventions

- `GID`: `gid` in variables, `Gid` in class names
- `PAT`: `pat` in attributes, `PAT` in class names
- `TTL`: `ttl` in variables, `TTL` in constants
- `URL`: lowercase `url` in attributes
- `API`: `Api` in class names (not `API`)

### Existing Naming Anti-Patterns (Do Not Spread)

- `CacheNotWarmError` at `src/autom8_asana/services/query_service.py:240` -- module-local
- `MissingConfigurationError(Exception)` at `src/autom8_asana/cache/integration/autom8_adapter.py:57`
- `ResolutionError(Exception)` at `src/autom8_asana/resolution/context.py:440` -- duplicates `exceptions.py`
- Two `ResolutionResult` classes across packages (naming collision)

## Knowledge Gaps

1. **`patterns/error_classification.py`** -- `RetryableErrorMixin` behavior not fully inspected.
2. **`observability/@error_handler`** -- decorator used in clients not fully documented.
3. **`lifecycle/` and `automation/`** -- large subsystems with own internal conventions not read in depth.
4. **`models/business/` detection tiers** -- tier1 through tier4 not read.
5. **`cache/dataframe/` warming pipeline** -- builder and warming conventions not read in depth.
