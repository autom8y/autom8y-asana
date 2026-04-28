---
domain: conventions
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
  - ".sos/land/workflow-patterns.md"
land_hash: "9db9c6f33d48f5c2fce398de7d3359fef30a0a0bd809044f7259f792ee6c4b9e"
---

# Codebase Conventions

## Error Handling Style

This codebase has a well-layered exception hierarchy with two root bases, domain-specific error modules, and clear boundary-mapping conventions.

### Exception Hierarchy

**Two root bases coexist:**

1. `AsanaError(Exception)` — root for all Asana SDK-facing errors, defined in `src/autom8_asana/errors.py`. Carries `message`, `status_code`, `response`, `errors`. Provides `from_response(cls, response)` class method that maps HTTP status codes to specific subclasses via `_STATUS_CODE_MAP`.

2. `Autom8Error(Exception)` — root for cross-cutting infrastructure errors, defined in `src/autom8_asana/core/errors.py`. Carries `message`, `context: dict`, `cause: Exception | None` (explicit chaining via `__cause__`). Each subclass declares `transient: bool` class variable.

**Per-domain error modules:**
- `src/autom8_asana/errors.py` — SDK-level Asana errors (`AuthenticationError`, `ForbiddenError`, `NotFoundError`, `RateLimitError`, `ServerError`, `TimeoutError`, `ConfigurationError`, `SyncInAsyncContextError`, `CircuitBreakerOpenError`, `NameNotFoundError`, `HydrationError`, `ResolutionError`, `InsightsError`, `ExportError`)
- `src/autom8_asana/core/errors.py` — infrastructure errors (`TransportError`, `S3TransportError`, `RedisTransportError`, `CacheError`, `CacheConnectionError`, `AutomationError`, `RuleExecutionError`, `SeedingError`, `PipelineActionError`)
- `src/autom8_asana/services/errors.py` — service-layer errors (`ServiceError`, `EntityNotFoundError`, `UnknownEntityError`, `TaskNotFoundError`, `EntityTypeMismatchError`, `EntityValidationError`, `InvalidFieldError`, `InvalidParameterError`, `NoValidFieldsError`, `CacheNotReadyError`, `CascadeNotReadyError`, `ServiceNotConfiguredError`)
- `src/autom8_asana/persistence/errors.py` — save orchestration errors (`SaveOrchestrationError`, `SessionClosedError`, `CyclicDependencyError`, `DependencyResolutionError`, `PartialSaveError`, `UnsupportedOperationError`, `PositioningConflictError`, `GidValidationError`, `SaveSessionError`)
- `src/autom8_asana/dataframes/errors.py` — DataFrame errors (`DataFrameError`, `SchemaNotFoundError`, `ExtractionError`, `TypeCoercionError`, `SchemaVersionError`, `DataFrameConstructionError`)
- `src/autom8_asana/query/errors.py` — query engine errors (`QueryEngineError` and subclasses)
- `src/autom8_asana/api/exception_types.py` — API-layer errors (`ApiError`, `ApiAuthError`, `ApiServiceUnavailableError`, `ApiDataFrameBuildError`)

### Error Creation

- **Domain errors** use `raise DomainSpecificError("message")` or `raise DomainSpecificError(f"message with {field}")` — always with f-strings for context
- **Config validation**: `raise ConfigurationError(f"field must be positive, got {self.field}")` inside `__post_init__` of frozen dataclasses
- **Transport boundary wrapping**: vendor errors (botocore, redis) wrapped into `TransportError` subclasses at backend boundaries so upstream code never imports vendor types
- **No bare `raise Exception("...")` or `raise RuntimeError("...")` at domain logic** — only in guard conditions

### Error Wrapping / Chaining

- `Autom8Error.__init__` accepts `cause: Exception | None` and explicitly sets `__cause__`. Use when wrapping vendor exception at layer boundary: `raise S3TransportError(..., cause=original_exc)`
- Transport error tuple constants in `src/autom8_asana/core/errors.py`:
  - `CACHE_TRANSIENT_ERRORS` — all S3/redis transport errors plus `CacheConnectionError`
  - `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS` — progressively composed tuples
  - Built with try/except ImportError so module loads cleanly when optional backends are absent
- `AsanaError.from_response(response)` is the canonical factory for HTTP responses

### Transient / Permanent Classification

- `Autom8Error` subclasses declare `transient: bool = True/False` as class variable
- `TransportError` defaults `transient = True`; `CacheError` defaults `transient = False`
- `RetryableErrorMixin` in `src/autom8_asana/patterns/error_classification.py` provides `is_retryable`, `recovery_hint`, `retry_after_seconds` based on HTTP status semantics (ADR-0079): 429 and 5xx = retryable; other 4xx = not retryable
- `SaveError` and `ActionResult` (in `persistence/models.py`) inherit `RetryableErrorMixin`

### Error Propagation Style

- **Service layer** raises `ServiceError` subclasses; callers do not catch and re-raise generically
- **API boundary** maps service and SDK errors to HTTP via two functions in `src/autom8_asana/api/errors.py`:
  - `raise_api_error(request, code, message, status_code, details, headers)` — route-level validation/precondition errors
  - `raise_service_error(request, error, status_code)` — converts `ServiceError` with request_id context
  - Global exception handlers registered via `setup_exception_handlers(app)` map `AsanaError` and `FleetError` hierarchies to canonical `ErrorResponse` envelopes with `request_id`
- ADR-ASANA-004 documents the full SDK-to-HTTP mapping (NotFoundError→404, AuthenticationError→401, RateLimitError→429, ServerError→502, TimeoutError→504)

### Error Handling at Catch Sites

- **Cache degradation**: `except CACHE_TRANSIENT_ERRORS as exc: logger.warning(...)` — swallow transient cache errors; never swallow domain errors
- **Inline guard**: `except ValueError: pass` used sparingly for format-fallback
- **Exception logging**: `logger.exception(...)` for unexpected; `logger.error(...)` for permanent; `logger.warning(...)` for transient degradation
- **`except Exception` catch-alls**: rare and only at top-level handlers
- Avoid bare `except:` (not observed)

## File Organization

### Top-Level Package Layout

`src/autom8_asana/` contains flat modules for SDK surface and sub-packages for domain logic:

| Module/Package | Purpose |
|---|---|
| `client.py` | `AsanaClient` — main SDK entry |
| `errors.py` | SDK-level exception hierarchy |
| `config.py` | Frozen dataclasses for configuration |
| `settings.py` | Pydantic-settings `AsanaSettings` for env var binding |
| `models/` | Pydantic model types for Asana resources |
| `api/` | FastAPI application (routes, middleware, lifespan, errors, models) |
| `clients/` | Thin HTTP client wrappers per Asana resource type |
| `core/` | Cross-cutting infrastructure (retry, registry, entity types, datetime) |
| `services/` | Business-logic orchestration |
| `dataframes/` | Polars DataFrame pipeline (builders, extractors, schemas, models, resolver) |
| `cache/` | Cache backends, providers, policies, integration adapters |
| `transport/` | HTTP transport layer (httpx adapters, response handler, adaptive semaphore) |
| `persistence/` | Save session orchestration |
| `query/` | Query engine (AST, models, errors, CLI) |
| `resolution/` | Entity resolution context and budget management |
| `reconciliation/` | Section reconciliation engine |
| `automation/` | Workflow automation (events, polling, workflows) |
| `batch/` | Batch API client |
| `metrics/` | Business metrics system |
| `auth/` | Authentication helpers |
| `search/` | Search client |
| `patterns/` | Shared design patterns |
| `protocols/` | Typed protocol interfaces |
| `observability/` | OpenTelemetry integration |
| `lifecycle/` | Task lifecycle engine |
| `lambda_handlers/` | AWS Lambda handler entry points |
| `_defaults/` | Default factory helpers |

### File Naming Conventions

**One concern per file**:
- Service files: `{entity}_service.py`
- Client files: `{resource_type}s.py` (plural)
- Error modules: `errors.py` per package
- Route model files: `{route_name}_models.py`
- Route files: `{domain}.py`
- Internal/private helpers: `_`-prefixed (e.g., `_exports_helpers.py`, `_security.py`)
- CLI entry points: `__main__.py`
- Bootstrap/internal helpers: `_bootstrap.py`

### Within-Package Organization

**`services/`**: One file per service class. Result types live in the same file as the service that produces them. Shared result types get their own file (`resolution_result.py`).

**`api/routes/`**: One route file per resource. Route models that are only used by one route live in `{name}_models.py` sibling. Generic models in `api/models.py`. Helper utilities `_`-prefixed.

**`dataframes/`**: Sub-packages per functional layer (`builders/`, `extractors/`, `models/`, `resolver/`, `schemas/`, `views/`). Flat utility modules at root (`annotations.py`, `cascade_utils.py`, `storage.py`).

**`core/`**: Flat utility modules; no sub-packages. One concern per file.

**`config.py` vs `settings.py`**: `config.py` holds frozen dataclasses for runtime configuration with `__post_init__` validation. `settings.py` holds Pydantic-settings for environment variable binding.

### `__init__.py` Export Policy

- Top-level `src/autom8_asana/__init__.py` is the public SDK surface — explicit imports and re-exports with `__all__`
- Sub-package `__init__.py` export selectively (e.g., `services/__init__.py` exports only `GidLookupIndex`)
- Empty `__init__.py` valid for marking package boundary

## Domain-Specific Idioms

### Dual Sync/Async Surface

The SDK exposes both sync and async methods. Convention is `_async` suffix on async variants:
- `client.tasks.get(gid)` (sync) / `client.tasks.get_async(gid)` (async)
- `validate_cascade_fields_async()` in `dataframes/builders/cascade_validator.py`

When calling sync inside async is detected at runtime, `SyncInAsyncContextError` is raised (`errors.py:189`, `transport/sync.py`).

### GID as String Convention

Asana Global IDs (GIDs) are always `str`, never `int`. Validation pattern: `r"^\d{10,}$"`. Variables and parameters named `gid` (lowercase). `workspace_gid` is the canonical parameter name.

### Configuration as Frozen Dataclasses

All runtime configuration is `@dataclass(frozen=True)` in `config.py`. Validation in `__post_init__`. Distinct from `settings.py` (Pydantic-settings for env binding).

### Logging via `autom8y_log`

All modules use `from autom8y_log import get_logger` then `logger = get_logger(__name__)` at module level. Project-wide logger factory (not stdlib `logging`). Structured kwargs: `logger.warning("event", key=value, key2=value2)`.

### Protocol-Based Dependency Interfaces

When a subsystem needs an interface without coupling to a concrete type, a `Protocol` (from `typing`) is defined:
- `DataFrameStorage(Protocol)` in `dataframes/storage.py`
- `CustomFieldResolver(Protocol)` in `dataframes/resolver/protocol.py`
- `RetryPolicy(Protocol)` in `core/retry.py`
- `IdempotencyStore(Protocol)` in `api/middleware/idempotency.py`
- `CreationServiceProtocol`, `SectionServiceProtocol` in `lifecycle/engine.py`

`@runtime_checkable` added when `isinstance()` checks are needed.

### Result Types as Dataclasses

Operations returning multiple outcome values use `@dataclass` result types (not tuples or dicts):
- `ResolutionResult` in `services/resolution_result.py`
- `WriteFieldsResult` in `services/field_write_service.py`
- `BackfillResult` in `services/vertical_backfill.py`
- `CascadeValidationResult`, `CascadeHealthResult` in `dataframes/builders/cascade_validator.py`
- `DataFrameResult` in `services/dataframe_service.py`
- `QueryResult` in `services/query_service.py`

### Cascade Pattern (Dataframes)

`cascade_validator.py` represents project-specific pattern for validating hierarchical data completeness. "Cascade" = parent→child field dependency chains. Audit functions prefixed `audit_`: `audit_cascade_key_nulls`, `audit_cascade_display_nulls`, `audit_phone_e164_compliance`. Health checks use `check_`: `check_cascade_health`.

### ErrorResponse Envelope

All API error responses use `ErrorResponse` envelope (from `api/models.py`) containing `ErrorDetail` and `ResponseMeta`. `request_id` always present. Enforced via `FleetError` + `fleet_error_to_response` from `autom8y_api_schemas.errors`.

### Import-Safe Tuple Constants

Error type tuples in `core/errors.py` use try/except ImportError to build progressively — module loads cleanly whether or not optional backends are installed.

## Naming Patterns

| Pattern | Convention | Examples |
|---|---|---|
| Service classes | `{Noun}Service` | `TaskService`, `EntityService`, `SectionService` |
| Request models | `{Action}{Resource}Request` | `CreateTaskRequest`, `UpdateProjectRequest` |
| Response models | `{Resource}Response` or `{Action}{Resource}Response` | `CacheRefreshResponse`, `WorkflowInvokeResponse` |
| Result dataclasses | `{Noun}Result` | `ResolutionResult`, `WriteFieldsResult` |
| Error classes | `{Specific}Error` | `EntityNotFoundError`, `InvalidFieldError` |
| Protocol classes | `{Noun}Protocol` or bare suffix optional | `CreationServiceProtocol`, `RetryPolicy`, `DataFrameStorage` |

### Method Naming

- Async: `_async` suffix (`get_async()`, `execute_async()`, `commit_async()`)
- Private helpers: single `_` prefix (`_build_error_response()`, `_is_transient()`)
- Audit functions: `audit_` prefix in dataframes domain
- Health checks: `check_` prefix

### Variable Naming

- Logger: `logger = get_logger(__name__)` — module-level. (Anti-pattern: `log` variant in `clients/data/_retry.py`, `_cache.py` — should be normalized)
- GIDs: always `gid` (lowercase), never `id` or `gid_str`
- `workspace_gid` canonical for workspace identifiers
- Module-level private constants: all-caps with `_` prefix (`_ASANA_GID_PATTERN`, `_MINIMUM_OPT_FIELDS`)

### Acronym Conventions

- `gid` (lowercase) in code, `GID` in docstrings/comments
- `URL`, `HTTP`, `S3`, `API`, `ADR`, `GID` — all uppercase in comments
- Error codes in machine-readable strings: `SCREAMING_SNAKE_CASE` (`RESOURCE_NOT_FOUND`, `VALIDATION_ERROR`)

### Package Naming

- All packages: `snake_case`
- Private helper modules: `_` prefix (`_defaults`, `_exports_helpers.py`, `_security.py`)

### Anti-Patterns to Avoid

- Do not use `log` as the logger variable name — use `logger`
- Do not raise `Exception` or `RuntimeError` for domain logic failures
- Do not import `CacheNotWarmError` from `services/query_service.py` (defined ad-hoc) — should relocate to `services/errors.py`
- Do not define result types outside the service file unless shared across multiple callers

## Experiential Observations (from session history)

The cross-session corpus (18 wrapped sessions, confidence 0.75) shows Bash dominates tool calls (65% of grepped). Edit usage correlates with productive sessions — project-crucible ran 8h25m with 36+ commits across 6 sprints. SCAR test cluster (33 inviolable tests) is documented as a sacred constraint.

Coverage floor is `>=80%` non-negotiable per project-crucible. Parametrize rate target `>=8%` (current 0.90% per session-layer view; 11.6% per static analysis). 86.8% local fixture ratio identified as anti-pattern.

Cross-rite transitions: `ari sync --rite=...` documented in session-20260415-032649 (hygiene↔10x-dev), session-20260427-232025 (rnd→10x-dev planned).

## Knowledge Gaps

- The `patterns/` package has only `error_classification.py` observed
- `lifecycle/engine.py` Protocol inventory is grep-based; full lifecycle idioms not fully traced
- `automation/` sub-packages (`events/`, `polling/`, `workflows/`) not individually inspected
- `search/`, `batch/` full API surface not traced
