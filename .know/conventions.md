---
domain: conventions
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "1471b813f0f58342c542d2e8c9cd92aba095afec134846cda625c3fa545ec9fe"
---

# Codebase Conventions

## Error Handling Style

### Two Parallel Exception Hierarchies (+ a third at service layer)

This project maintains **multiple** root exception hierarchies that coexist by design:

**1. Asana API hierarchy** (`src/autom8_asana/errors.py`)
- Root: `AsanaError(Exception)` — for all Asana HTTP/API failures
- Carries: `message`, `status_code`, `response`, `errors`
- Subclasses: `AuthenticationError` (401), `ForbiddenError` (403), `NotFoundError` (404), `GoneError` (410), `RateLimitError` (429), `ServerError` (5xx), `TimeoutError`, `ConfigurationError`, `CircuitBreakerOpenError`, `NameNotFoundError`, `HydrationError`, `ResolutionError`
- Domain groupings: `InsightsError` → `InsightsValidationError`, `InsightsNotFoundError`, `InsightsServiceError`; `ExportError`
- Factory classmethod `AsanaError.from_response(response)` maps HTTP status via `_STATUS_CODE_MAP` (errors.py:262–272)
- `RateLimitError` overrides `from_response` to capture `retry_after` from headers

**2. Infrastructure hierarchy** (`src/autom8_asana/core/errors.py`)
- Root: `Autom8Error(Exception)` — for transport, cache, automation infrastructure
- Carries: `message`, `context: dict`, `cause: Exception | None` (set as `__cause__`)
- Has `transient: bool` class attribute (False by default)
- Subclasses: `TransportError` (transient=True) → `S3TransportError`, `RedisTransportError`; `CacheError` → `CacheConnectionError` (transient=True); `AutomationError` → `RuleExecutionError`, `SeedingError`, `PipelineActionError`
- Each transport subclass provides `from_*_error()` factory classmethod wrapping vendor exceptions at boundary

**3. Service layer hierarchy** (`src/autom8_asana/services/errors.py`)
- Root: `ServiceError(Exception)` — used exclusively in the service layer
- Provides `error_code: str`, `status_hint: int`, `to_dict()` method
- Route handlers catch `ServiceError` and convert via `raise_service_error(request_id, e)` (seen on all 14 exception catch sites in `tasks.py`)
- Services must **never** import FastAPI or raise `HTTPException` (per TDD-SERVICE-LAYER-001)

**4. Catch-tuple constants** (`core/errors.py:280–329`)
- `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`, `CACHE_TRANSIENT_ERRORS`, `ASANA_API_ERRORS` — import-safe tuples used at catch sites instead of importing botocore/redis types
- Pattern: `try: from botocore... S3_TRANSPORT_ERRORS = (..., BotoCoreError, ClientError, ...) except ImportError: pass`

### Error Context Propagation

- Cause chaining uses `self.__cause__ = cause` in `Autom8Error.__init__` — NOT native `raise X from Y` at call sites
- Rich context stored in `context: dict[str, Any]` on `Autom8Error` subclasses
- `NameNotFoundError` carries `suggestions`, `available_names` for debugging

### API Boundary Error Handling

- Routes call `raise_service_error(request_id, e)` converting `ServiceError` → `HTTPException` with envelope format
- `raise_api_error(request_id, code, message)` for precondition/validation errors in routes
- All handlers registered in `register_exception_handlers(app)` (`api/errors.py:728`)
- ADRs: `ADR-ASANA-004` (Error Handling and HTTP Mapping), `ADR-I6-001` (API Error Response Convention)

### Exception Files Pattern

Each domain package has its own `errors.py`:
- `src/autom8_asana/errors.py` — SDK/Asana API
- `src/autom8_asana/core/errors.py` — Infrastructure
- `src/autom8_asana/services/errors.py` — Service layer
- `src/autom8_asana/dataframes/errors.py` — DataFrame errors (`DataFrameError` → `SchemaNotFoundError`, `ExtractionError`, `TypeCoercionError`, `SchemaVersionError`, `DataFrameConstructionError`, `ParallelFetchError`)
- `src/autom8_asana/persistence/errors.py` — `SaveOrchestrationError(AsanaError)`, `SessionClosedError`
- `src/autom8_asana/api/exception_types.py` — Typed HTTP exceptions (`ApiError`, `ApiAuthError`, `ApiDataFrameBuildError`, `ApiServiceUnavailableError`) replacing bare `HTTPException` raises

### Future Annotations

411 of 478 files (86%) use `from __future__ import annotations` — treat it as effectively mandatory for new files.

## File Organization

### Package Structure and Responsibilities

The `src/autom8_asana/` package is **large** (478 Python files, 26+ subpackages). Organization follows a **domain-layer** model, not simple CRUD grouping:

| Package | Contents |
|---------|----------|
| `api/` | FastAPI app (`main.py`), routes (`routes/`), models, middleware, lifespan, errors, preload |
| `api/routes/` | One file per route group (e.g., `tasks.py`, `projects.py`); paired `*_models.py` for request/response types |
| `clients/` | Per-resource Asana API clients; `data/` for data-service clients |
| `clients/data/` | Internal data service integration; internal modules prefixed with `_` |
| `clients/data/_endpoints/` | Per-endpoint modules (`insights.py`, `batch.py`, `export.py`, `reconciliation.py`, `simple.py`) |
| `core/` | Cross-cutting utilities: `logging.py`, `errors.py`, `retry.py`, `entity_registry.py`, `concurrency.py`, `connections.py`, `types.py`, `timing.py` |
| `models/` | Domain model hierarchy; `models/business/` = entity classes; `models/contracts/` = cross-service contracts |
| `models/business/` | `BusinessEntity` base, entity classes (`Business`, `Unit`, `Contact`, `Offer`, `Process`, `AssetEdit`), descriptors, mixins, holder factory, registry |
| `services/` | Service classes (one per domain concern); `errors.py` for service exceptions |
| `dataframes/` | Polars DataFrame pipeline: `builders/`, `extractors/`, `models/`, `resolver/`, `schemas/`, `views/` |
| `cache/` | Cache subsystem: `backends/`, `dataframe/`, `integration/`, `models/`, `policies/`, `providers/` |
| `persistence/` | Write/save pipeline: `actions.py`, `executor.py`, `cascade.py`, `session.py`, `tracker.py`, `pipeline.py` |
| `resolution/` | Field resolution system: `strategies.py`, `context.py`, `result.py`, `field_resolver.py`, `write_registry.py` |
| `automation/` | Automation engine: `engine.py`, `pipeline.py`, `events/`, `polling/`, `workflows/` |
| `lifecycle/` | Task lifecycle management: `engine.py`, `completion.py`, `reopen.py`, `creation.py`, `seeding.py` |
| `protocols/` | Protocol (structural typing) interfaces |
| `_defaults/` | Default provider registrations: `auth.py`, `cache.py`, `log.py`, `observability.py` |
| `transport/` | HTTP transport: `asana_http.py`, `adaptive_semaphore.py`, `sync.py`, `response_handler.py` |
| `patterns/` | Reusable patterns: `error_classification.py`, `async_method.py` |
| `observability/` | Observability hooks: `decorators.py`, `context.py`, `correlation.py` |
| `lambda_handlers/` | AWS Lambda entry points |
| `query/` | Query engine with `__main__.py` entry point |

### File Naming Conventions

- Internal/private modules at package level use `_` prefix: `_defaults/`, `_endpoints/`, `_cache.py`, `_response.py`, `_retry.py`, `_policy.py`, `_pii.py`
- Security-related helpers in routes: `_security.py`
- Route-paired model files: `intake_create.py` + `intake_create_models.py`, `resolver.py` + `resolver_models.py`, `resolver_schema.py`
- Build result types live in dedicated `build_result.py` within their package

### `__init__.py` Export Pattern

- Top-level `__init__.py` is a comprehensive public API — exports `AsanaClient`, `BatchClient`, all error types, all model types, observability hooks, protocols
- Subpackage `__init__.py` files are selective: `api/__init__.py` exports `create_app` and key models; `services/__init__.py` exports only `GidLookupIndex`; most others export little or nothing
- `core/__init__.py` exports only `gather_with_semaphore`, `get_logger`, `configure`, `reset_logging`

### Entry Points

- API: `src/autom8_asana/api/main.py` → `create_app()` factory function (FastAPI)
- CLI query tool: `src/autom8_asana/query/__main__.py`
- AWS Lambda: `src/autom8_asana/lambda_handlers/`
- Automation polling: `src/autom8_asana/automation/polling/cli.py`

### Config vs Settings Separation

- `config.py` — root: frozen `@dataclass` types (`RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `CircuitBreakerConfig`, `DataFrameConfig`, `CacheConfig`, `AsanaConfig`) — runtime config objects
- `settings.py` — pydantic-settings classes (`AsanaSettings`, `CacheSettings`, `RedisSettings`, `S3Settings`, etc.) inheriting from `Autom8yBaseSettings` — read environment variables

> Test conventions: See `.know/test-coverage.md` for test file organization, fixture patterns, and coverage gaps.

## Domain-Specific Idioms

### 1. PhoneVerticalPair (pvp) — Central Domain Concept

`PhoneVerticalPair` (abbreviated `pvp`) is the primary keying concept for the data service. Pairs phone number (`office_phone`) with a business vertical (e.g., "Medical"). Canonical key format: `pv1:{phone}:{vertical.lower()}`.

- Defined in `autom8y_core.models.data_service` (external), re-exported via `src/autom8_asana/models/contracts/phone_vertical.py`
- Utility: `pvp_from_business(business)` in `models/contracts/phone_vertical.py`
- Abbreviation `pvp` is universal: `pvp.canonical_key`, `pvp_by_key`, `results[pvp.canonical_key]`

### 2. GID — Asana Graph ID

`GID` (Asana's Global ID) is a numeric string (10–20 digits in production, relaxed in test). Naming convention: always suffix parameter/field names with `_gid` (e.g., `task_gid`, `project_gid`, `workspace_gid`, `entity_gid`, `section_gid`). Never bare `id`.

- Validated via `GidStr` Pydantic type alias (`api/models.py:47–50`) — numeric-only in production, relaxed in test/local via `AUTOM8Y_ENV`
- Pattern `^\d{1,64}$` for regex validation

### 3. `raw: Literal[True/False]` Overload Pattern

Client methods that can return either a parsed model or raw dict use `@overload` with `raw: Literal[False] = ...` and `raw: Literal[True]`. Appears ~200 times in `clients/`. An agent adding a new client method must replicate all three overloads.

### 4. `*_async` Suffix Naming

Methods named `foo_async` are primary async entry points (e.g., `get_async`, `create_async`, `update_async`). Plain `foo` is the sync wrapper. `async def foo(...)` (no suffix, async) is used for iterator/generator interfaces (e.g., `list_async`, `subtasks_async`). 380 `_async`-suffixed methods exist; 357 are actually `async def`.

### 5. Descriptor Pattern for Custom Fields

Custom field access on `BusinessEntity` subclasses uses Python descriptors (`src/autom8_asana/models/business/descriptors.py`):
- `CustomFieldDescriptor[T]` is the generic base
- Concrete types: `TextField`, `EnumField`, `MultiEnumField`, `NumberField`, `IntField`, `PeopleField`, `DateField`
- Assigned as class attributes; `__set_name__` registers them at definition time
- Usage: `business.my_field` reads via `__get__`, translating Asana custom field payload to typed Python value

### 6. HolderFactory Pattern

Task subtree ownership modelled with `HolderFactory` (`models/business/holder_factory.py`). Subclasses specify `child_type` and `parent_ref` as class kwargs:
```python
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    ...
```
Mixins control nesting: `UnitNestedHolderMixin`, `HolderMixin[T]`.

### 7. Registry Pattern

Multiple registries follow a consistent class structure with `register()` / `get()` / `lookup()` methods:
- `EntityRegistry` (`core/entity_registry.py`)
- `ProjectTypeRegistry` (`models/business/registry.py`) — decorator `@register_entity_class` pattern
- `SchemaRegistry` (`dataframes/models/registry.py`)
- `WorkflowRegistry` (`automation/workflows/registry.py`)
- `EntityWriteRegistry` (`resolution/write_registry.py`)

### 8. BuildResult Pattern

Complex pipeline operations return typed `*Result` dataclasses:
- `BuildResult` (both `dataframes/builders/` and `cache/dataframe/`)
- `ReconciliationResult`, `ExecutionResult`, `ProcessorResult`
- `LifecycleActionResult`, `TransitionResult`, `CreationResult`, `SeedingResult`

These are plain `@dataclass` or `@dataclass(frozen=True)`, not Pydantic models.

### 9. Polars DataFrames (not Pandas)

Uses `polars` (imported as `pl`) throughout the dataframes layer. All DataFrame operations use Polars syntax (`pl.DataFrame`, `pl.col()`, `pl.lit()`, `df.with_columns(...)`, `df["col"]`). Never Pandas.

### 10. structlog Logging

Uses `autom8y_log.get_logger(__name__)` directly (NOT `logging.getLogger`). Module-level: `logger = get_logger(__name__)`. Structured context passed as keyword arguments (structlog pattern). Import: `from autom8y_log import get_logger` (not from `autom8_asana.core.logging`, which is a re-export shim).

### 11. Fleet Envelope Types

API responses always use `SuccessResponse`/`ErrorResponse` from `autom8y_api_schemas`. Imported in `api/models.py` and re-exported for backward compatibility. `build_success_response()` and `build_error_response()` are standard constructors.

### 12. `transient` Flag on Errors

`Autom8Error` subclasses expose a `transient: bool` class attribute. Retry logic reads this to distinguish transient (can retry) from permanent errors. `TransportError.transient = True`, `CacheError.transient = False`, `CacheConnectionError.transient = True`. `S3TransportError.transient` is a `@property` returning False for permanent AWS error codes.

## Naming Patterns

### Type Names

- **Config dataclasses**: `*Config` suffix — `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `CircuitBreakerConfig`, `DataFrameConfig`, `CacheConfig`, `AsanaConfig`
- **Settings (pydantic)**: `*Settings` suffix — `AsanaSettings`, `CacheSettings`, `RedisSettings`, `S3Settings`, `DataServiceSettings`, `ObservabilitySettings`, `RuntimeSettings`
- **Results**: `*Result` suffix — `BuildResult`, `ReconciliationResult`, `ExecutionResult`, `CreationResult`, `SeedingResult`, `LifecycleActionResult`, `MatchResult`, `CascadeValidationResult`
- **Errors**: `*Error` suffix — universal; no `*Exception` names (except `SyncInAsyncContextError`)
- **Protocols**: Noun phrases without suffix — `AuthProvider`, `CacheProvider`, `MetricsEmitter`, `DataFrameProvider`, `ObservabilityHook`, `ItemLoader`, `InsightsProvider`
- **Enums**: `StrEnum` preferred for string-valued (`FreshnessIntent`, `FreshnessState`, `VerificationSource`, `SectionStatus`, `ProbeVerdict`, `AuthMode`); `Enum` for non-string; `IntEnum` for integer (`CompletenessLevel`)
- **Mixins**: `*Mixin` suffix — `SharedCascadingFieldsMixin`, `FinancialFieldsMixin`, `UpwardTraversalMixin`, `UnitNavigableEntityMixin`, `UnitNestedHolderMixin`, `HolderMixin`
- **Requests (Pydantic)**: `*Request` suffix — `CreateTaskRequest`, `UpdateTaskRequest`, `MoveSectionRequest`, `ListTasksParams` (params suffix for query param models)
- **Responses (Pydantic)**: `*Response` suffix — `SuccessResponse`, `ErrorResponse`, `InsightsResponse`, `BatchInsightsResponse`, `QueryResponse`

### Variable Naming

- GID parameters always use `*_gid` suffix: never bare `id`
- `pvp` is the universal abbreviation for `PhoneVerticalPair`
- `df` is the universal variable name for Polars DataFrames

### Acronym Conventions

- `GID` (not `Gid`, not `Id`) — Asana Graph ID, always uppercase in identifiers
- `PVP` or `pvp` — PhoneVerticalPair shorthand; lowercase `pvp` preferred in variable names
- `URL` not `Url`; `HTTP` not `Http` in class names (e.g., `HTTPException`)
- `ID` and `GID` are both uppercase; never `Id` or `Gid`

### Module/Package Naming

- Packages are singular nouns: `cache`, `client`, `core`, `model` → plural only for genuine collections: `clients`, `models`, `protocols`, `metrics`, `patterns`
- Internal packages/modules start with `_`: `_defaults`, `_endpoints`, `_cache`, `_policy`, `_retry`, `_pii`, `_security`
- No `utils` at top level; utility code goes into named modules (`core/string_utils.py`, `core/field_utils.py`, `core/datetime_utils.py`)

### Naming Anti-Patterns to Avoid

- Do not use `id` for Asana identifiers — always `*_gid`
- Do not name a module `utils.py` at top level — use specific names
- Do not mix `*Settings` and `*Config` — `Settings` reads env vars, `Config` is a frozen dataclass for runtime wiring
- Do not use `get_logger` from `autom8_asana.core.logging` in new code — import directly from `autom8y_log`
- Do not name async methods without `_async` suffix when a sync variant exists at the same level

## Knowledge Gaps

1. **`clients/data/_pii.py`** — Not read; PII handling conventions in the data client undocumented here.
2. **`patterns/error_classification.py`** — Not read in depth; `RetryableErrorMixin` and `HasError` protocol details.
3. **`automation/workflows/`** — Workflow-specific idioms (conversation_audit, insights, payment_reconciliation) not explored.
4. **`lambda_handlers/`** — Entry-point and handler naming patterns in Lambda context not audited.
5. **`cache/policies/`** — Cache policy naming and application pattern not documented.
6. **Test conventions** — Deferred to `.know/test-coverage.md` per domain separation.
