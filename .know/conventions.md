---
domain: conventions
generated_at: "2026-05-08T00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
update_mode: "time-only"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Conventions

> Regenerated 2026-05-04 (FULL mode). Source hash: `20ef7952`.
> Updated: CacheNotWarmError anti-pattern resolved (moved to `services/errors.py`).
> New: dual structured logging styles documented. `_logger` private-name outliers noted.

## Error Handling Style

This codebase has a well-layered exception hierarchy with two root bases, domain-specific error modules, and clear boundary-mapping conventions.

### Exception Hierarchy

**Two root bases coexist:**

1. `AsanaError(Exception)` — root for all Asana SDK-facing errors, defined in `src/autom8_asana/errors.py`. Carries `message`, `status_code`, `response`, `errors`. Provides `from_response(cls, response)` class method that maps HTTP status codes to specific subclasses via `_STATUS_CODE_MAP`.

2. `Autom8Error(Exception)` — root for cross-cutting infrastructure errors, defined in `src/autom8_asana/core/errors.py`. Carries `message`, `context: dict`, `cause: Exception | None` (explicit chaining via `__cause__`). Each subclass declares `transient: bool` class variable.

**Per-domain error modules:**
- `src/autom8_asana/errors.py` — SDK-level Asana errors (`AuthenticationError`, `ForbiddenError`, `NotFoundError`, `RateLimitError`, `ServerError`, `TimeoutError`, `ConfigurationError`, `SyncInAsyncContextError`, `CircuitBreakerOpenError`, `NameNotFoundError`, `HydrationError`, `ResolutionError`, `InsightsError`, `ExportError`)
- `src/autom8_asana/core/errors.py` — infrastructure errors (`TransportError`, `S3TransportError`, `RedisTransportError`, `CacheError`, `CacheConnectionError`, `AutomationError`, `RuleExecutionError`, `SeedingError`, `PipelineActionError`)
- `src/autom8_asana/services/errors.py` — service-layer errors (`ServiceError`, `EntityNotFoundError`, `UnknownEntityError`, `TaskNotFoundError`, `EntityTypeMismatchError`, `EntityValidationError`, `InvalidFieldError`, `InvalidParameterError`, `NoValidFieldsError`, `CacheNotReadyError`, `CascadeNotReadyError`, `ServiceNotConfiguredError`, `CacheNotWarmError`)
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
- `raise ... from e` pattern used at transport boundaries: `raise TimeoutError(...) from e` in `transport/asana_http.py`, `raise ConfigurationError(...) from e` in `automation/polling/config_loader.py`
- `raise ... from None` used in CLI error conversion to suppress chained traceback for user-facing errors: `src/autom8_asana/query/__main__.py:120`
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
  - `raise_api_error(request_id, status_code, code, message, details, headers)` — route-level validation/precondition errors
  - `raise_service_error(request_id, error, headers)` — converts `ServiceError` with request_id context
  - Global exception handlers registered via `register_exception_handlers(app)` map `AsanaError`, `FleetError`, and `ApiError` hierarchies to canonical `ErrorResponse` envelopes with `request_id`
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
- `__all__` is present in all major `__init__.py` files: `core/`, `cache/`, `transport/`, `dataframes/`, `clients/`, `lambda_handlers/`, `patterns/`, `metrics/`, `reconciliation/`
- Empty `__init__.py` valid for marking package boundary

## Domain-Specific Idioms

### Dual Sync/Async Surface

The SDK exposes both sync and async methods. Convention is `_async` suffix on async variants:
- `client.tasks.get(gid)` (sync) / `client.tasks.get_async(gid)` (async)
- `validate_cascade_fields_async()` in `dataframes/builders/cascade_validator.py`
- `warm_cache_async()` in `client.py`

When calling sync inside async is detected at runtime, `SyncInAsyncContextError` is raised (`errors.py:189`, `transport/sync.py`). Async usage is pervasive: 2,381 `async def` / `await` occurrences across source.

### GID as String Convention

Asana Global IDs (GIDs) are always `str`, never `int`. Validation pattern: `r"^\d{1,64}$"` (production; relaxed in test/local environments). Variables and parameters named `gid` (lowercase). `workspace_gid` is the canonical parameter name. `GidStr` is the Pydantic v2 annotated type alias defined in `api/models.py` using `Annotated[str, StringConstraints(pattern=...)]` — environment-aware (strict in prod, permissive in test/local).

### Configuration as Frozen Dataclasses

All runtime configuration is `@dataclass(frozen=True)` in `config.py`. Validation in `__post_init__`. Distinct from `settings.py` (Pydantic-settings for env binding). Examples: `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `S3LocationConfig`, `DataFrameConfig`, `CacheConfig`, `AsanaConfig`.

### Logging via `autom8y_log`

All modules use `from autom8y_log import get_logger` then `logger = get_logger(__name__)` at module level. Project-wide logger factory (not stdlib `logging`).

**Two coexisting call styles** (both syntactically valid):

1. **Keyword-arg style** (autom8y_log native / structlog-style) — preferred in most source:
   ```python
   logger.warning("circuit_breaker_state_change", name=self._config.name, state="open")
   logger.debug("Bulk API call failed", error=str(r))
   ```

2. **`extra={}` dict style** (stdlib logging compat) — used in `api/errors.py` and some cache/dataframe paths:
   ```python
   logger.info("authentication_failed", extra={"request_id": request_id, "error_code": "INVALID_CREDENTIALS"})
   ```

Both forms are accepted. The keyword form is the majority convention; `extra={}` appears to be used where stdlib logging handler compatibility is required. **New code should prefer the keyword form** unless working inside `api/errors.py` context where `extra={}` is the established style.

**2 private-naming outliers**: `dataframes/cache_integration.py:40` and `models/business/fields.py:20` use `_logger` (underscore-prefixed). Do not replicate — canonical module-level name is `logger`.

### Protocol-Based Dependency Interfaces

When a subsystem needs an interface without coupling to a concrete type, a `Protocol` (from `typing`) is defined:
- `DataFrameStorage(Protocol)` in `dataframes/storage.py`
- `CustomFieldResolver(Protocol)` in `dataframes/resolver/protocol.py`
- `RetryPolicy(Protocol)` in `core/retry.py`
- `IdempotencyStore(Protocol)` in `api/middleware/idempotency.py`
- `CreationServiceProtocol`, `SectionServiceProtocol` in `lifecycle/engine.py`
- `ConnectionManager(Protocol)` in `core/connections.py`

`@runtime_checkable` added when `isinstance()` checks are needed.

### Result Types as Dataclasses

Operations returning multiple outcome values use `@dataclass` result types (not tuples or dicts):
- `ResolutionResult` in `services/resolution_result.py`
- `WriteFieldsResult` in `services/field_write_service.py`
- `BackfillResult` in `services/vertical_backfill.py`
- `CascadeValidationResult`, `CascadeHealthResult` in `dataframes/builders/cascade_validator.py`
- `DataFrameResult` in `services/dataframe_service.py`
- `QueryResult` in `services/query_service.py`
- `ReconciliationResult`, `ProcessorResult`, `ExecutionResult` in `reconciliation/`

### Cascade Pattern (Dataframes)

`cascade_validator.py` represents project-specific pattern for validating hierarchical data completeness. "Cascade" = parent→child field dependency chains. Audit functions prefixed `audit_`: `audit_cascade_key_nulls`, `audit_cascade_display_nulls`, `audit_phone_e164_compliance`. Health checks use `check_`: `check_cascade_health`.

### ErrorResponse Envelope

All API error responses use `ErrorResponse` envelope (from `autom8y_api_schemas`, re-exported via `api/models.py`) containing `ErrorDetail` and `ResponseMeta`. `request_id` always present. Enforced via `FleetError` + `fleet_error_to_response` from `autom8y_api_schemas.errors`. `build_success_response()` and `build_error_response()` are fleet-standard factories for response construction.

### Import-Safe Tuple Constants

Error type tuples in `core/errors.py` use try/except ImportError to build progressively — module loads cleanly whether or not optional backends are installed. Pattern:
```python
REDIS_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (RedisTransportError,)
try:
    from redis import RedisError
    REDIS_TRANSPORT_ERRORS = (RedisTransportError, RedisError)
except ImportError:
    pass
```

### Pydantic v2 `Field(examples=[...])` Convention (CSI-001 discharged 2026-04-29)

**Canonical form**: `Field(examples=["value"])` — plural array form for all Pydantic model fields exposed in the OpenAPI schema.

**Rationale**: Pydantic v2 generates OpenAPI 3.1 spec using `examples` (plural, array). Using the singular `example` key in a `Field()` call produces no effect — only the array form is recognized by the Pydantic v2 JSON schema generator.

**Evidence**: T-08 (commit `4d4097c3`) lifted 13 hand-edited `"example":` keys from `docs/api-reference/openapi.json` to source-level `Field(examples=[...])` declarations. Verified present at:
- `src/autom8_asana/models/base.py:50` — `AsanaResource.gid`
- `src/autom8_asana/models/common.py:52` — `NameGid.gid`
- `src/autom8_asana/models/task.py:47,54,59,70,85` — `resource_type`, `name`, `notes`, `completed`, `due_on`
- `src/autom8_asana/api/routes/resolver_schema.py:72,76,346,350` — `SchemaFieldInfo.name/type`, `EnumValueInfo.value/meaning`
- `src/autom8_asana/api/routes/workflows.py:175,180` — `WorkflowEntry.workflow_id`, `log_prefix`

**Exception — pre-CSI-001 raw-dict inline OpenAPI annotations**: Two sites in `dataframes.py` use the singular `"example":` key inside raw `responses={...}` dict annotations passed directly to the FastAPI route decorator:
- `src/autom8_asana/api/routes/dataframes.py:511`
- `src/autom8_asana/api/routes/dataframes.py:632`

These are NOT Pydantic `Field()` calls. They are OpenAPI 3.0-style inline response annotations that predate CSI-001. They are not regressions — they are pre-existing divergent patterns. **Do not replicate this singular form in new `Field()` declarations.** Future Pydantic field declarations MUST use `examples=[...]` (plural array).

### Pydantic v2 Discriminated Union — Callable Discriminator Discipline (SCAR-DISCRIMINATOR-001)

**Pattern location**: `src/autom8_asana/query/models.py:97-135`

When using `Discriminator(callable)` for a Pydantic v2 discriminated union, the callable MUST handle BOTH dict inputs AND model-instance inputs. The current `_predicate_discriminator` function handles only `isinstance(v, dict)` — model-instance inputs fall through to `return "comparison"` (line 112), causing incorrect discriminator resolution for nested model instances.

**Failure mode**: `NotGroup(not_=AndGroup(...))` — passing an `AndGroup` model instance as the child of `NotGroup.not_` will silently misparse as `Comparison` type, failing Pydantic validation.

**Fix pattern** (not yet applied — T-06 follow-up scope):
```python
def _predicate_discriminator(v: Any) -> str:
    if isinstance(v, dict):
        # ... existing dict branch
    elif isinstance(v, BaseModel):
        # inspect model_fields keys to determine variant
        fields = set(v.model_fields.keys())
        if "and_" in fields or hasattr(v, "and_"):
            return "and"
        # ... etc.
    return "comparison"
```

**Cross-reference**: SCAR-DISCRIMINATOR-001 in `.know/scar-tissue.md`.

### MockTask Import Convention (HYG-003 — discharged 2026-04-30)

**Rule**: New tests requiring `MockTask` MUST import from the canonical
`tests/_shared/mocks` module. Bespoke redefinition is forbidden.

**Canonical location**: `tests/_shared/mocks.py:10`. The class is a strict
superset of all attribute schemas observed across the 11 prior bespoke
variants (cascading-resolver family, automation family, integration family,
plus dict-wrapper paradigm via `_data` kwarg + `model_dump()` method).

**Import form**: `from tests._shared.mocks import MockTask`

**Rationale**: Prevents schema fragmentation. Prior to HYG-003, 11 bespoke
`class MockTask` definitions diverged across `tests/unit/dataframes/`,
`tests/unit/automation/`, and `tests/integration/`. Schema drift between
bespoke variants caused silent attribute-not-found surprises.

**Extension protocol**: if a future test needs an attribute not in the
superset, EXTEND the canonical (additive only — no breaking changes to
existing kwargs). Do NOT mint a new bespoke.

### `from __future__ import annotations` Convention

417 of 484 source files (86%) use `from __future__ import annotations` as the first import. This defers type annotation evaluation and enables forward references without string quoting. All new files in the source root should include this import.

## Naming Patterns

| Pattern | Convention | Examples |
|---|---|---|
| Service classes | `{Noun}Service` | `TaskService`, `EntityService`, `SectionService`, `EntityQueryService` |
| Request models | `{Action}{Resource}Request` | `CreateTaskRequest`, `UpdateProjectRequest` |
| Response models | `{Resource}Response` or `{Action}{Resource}Response` | `CacheRefreshResponse`, `WorkflowInvokeResponse` |
| Result dataclasses | `{Noun}Result` | `ResolutionResult`, `WriteFieldsResult`, `QueryResult` |
| Error classes | `{Specific}Error` | `EntityNotFoundError`, `InvalidFieldError`, `CacheNotWarmError` |
| Config dataclasses | `{Domain}Config` | `RateLimitConfig`, `CircuitBreakerConfig`, `DataServiceConfig` |
| Client classes | `{Resource}sClient` | `TasksClient`, `SectionsClient`, `TagsClient` |
| Protocol classes | `{Noun}Protocol` or bare noun | `CreationServiceProtocol`, `RetryPolicy`, `DataFrameStorage` |

### Method Naming

- Async: `_async` suffix (`get_async()`, `execute_async()`, `commit_async()`, `warm_cache_async()`)
- Private helpers: single `_` prefix (`_build_error_response()`, `_is_transient()`)
- Audit functions: `audit_` prefix in dataframes domain
- Health checks: `check_` prefix
- Lazy accessors: `_` prefix + `@functools.cache` decorator (e.g., `_detection_cache_ttl()`)

### Variable Naming

- Logger: `logger = get_logger(__name__)` — module-level canonical name (unprefixed). **Exception**: `_logger` exists in 2 files (`dataframes/cache_integration.py`, `models/business/fields.py`) — do not replicate.
- GIDs: always `gid` (lowercase), never `id` or `gid_str`
- `workspace_gid` canonical for workspace identifiers
- Module-level private constants: all-caps with `_` prefix (`_ASANA_GID_PATTERN`, `_MINIMUM_OPT_FIELDS`, `_STATUS_CODE_MAP`)
- Module-level public constants: all-caps without prefix (`PHASE_1_DEFAULT_COLUMNS`, `BASE_SCHEMA`)

### `logger` Parameter Naming Convention (T-06 — autom8y_log SDK)

**Canonical form**: `logger` (not `log`) as the parameter name when passing an `autom8y_log` logger instance to a constructor or function.

**Background**: T-06 (commit `5b2e3b2d`) renamed `log` → `logger` across 6 files to align with autom8y_log SDK conventions. This establishes `logger` as the canonical parameter name project-wide.

**T-06 follow-up scope — 4 violators remain** (NOT yet aligned; pre-existing `log:` parameter sites not covered by T-06):

| File | Line | Pattern |
|---|---|---|
| `src/autom8_asana/clients/data/_response.py` | 65 | `log: LogProvider \| Any \| None` (function parameter) |
| `src/autom8_asana/clients/data/_response.py` | 197 | `log: LogProvider \| Any \| None` (function parameter) |
| `src/autom8_asana/persistence/holder_ensurer.py` | 72 | `log: Any \| None = None` (constructor parameter) |
| `src/autom8_asana/persistence/cache_invalidator.py` | 41 | `log: Any \| None = None` (constructor parameter) |
| `src/autom8_asana/services/vertical_backfill.py` | 63 | `log: Any \| None = None` (constructor parameter) |

**Rule**: All new code MUST use `logger` as the parameter name. The 4 violator files above are pending T-06 follow-up remediation. Do not replicate the `log:` parameter form in new code.

### Acronym Conventions

- `gid` (lowercase) in code, `GID` in docstrings/comments
- `URL`, `HTTP`, `S3`, `API`, `ADR`, `GID` — all uppercase in comments
- Error codes in machine-readable strings: `SCREAMING_SNAKE_CASE` (`RESOURCE_NOT_FOUND`, `VALIDATION_ERROR`, `MISSING_AUTH`)

### Package Naming

- All packages: `snake_case`
- Private helper modules: `_` prefix (`_defaults`, `_exports_helpers.py`, `_security.py`, `_bootstrap.py`)

### Anti-Patterns to Avoid

- Do not use `log` as the logger variable or parameter name — use `logger` (see T-06 convention above; 4 legacy sites pending cleanup)
- Do not raise `Exception` or `RuntimeError` for domain logic failures
- Do not define `CacheNotWarmError` locally — import from `services/errors.py` (resolved in `20ef7952`; `query_service.py` now re-exports with `noqa: F401`)
- Do not define result types outside the service file unless shared across multiple callers
- Do not use singular `"example":` key inside Pydantic `Field()` — use `examples=[...]` (plural array); the two sites in `dataframes.py:511,632` are pre-CSI-001 raw-dict exceptions, not the canonical form
- Do not use `_logger` as the module-level logger name — use `logger` (unprefixed)
- Do not replicate the `extra={}` logging style outside `api/errors.py` context — prefer keyword-arg form `logger.warning("event", key=value)`

### Pattern 1 — Configuration-During-Init Anti-Pattern (GLINT-002)

**Rule**: `get_settings()` — and any call that resolves Pydantic-settings, secret-backed
fields, or ARN lookups — MUST NOT execute at module-import time. Defer to handler-call
scope or use a `@cache`-decorated lazy accessor.

**Rationale**: In AWS Lambda, the Parameters and Secrets Lambda Extension HTTP listener
(`http://127.0.0.1:2773`) is NOT guaranteed to be ready when the runtime imports user
modules. Settings resolution at import time silently passes in local/unit-test
environments (where the extension is absent and boto3/env fallbacks succeed) but fails
in production Lambda on the first cold-start that hits an unready extension. Detection
latency can reach ~30 days — the failure signal is *absence* of expected CloudWatch
events rather than an explicit error.

**Canonical worked example**: `_detection_cache_ttl()` lazy accessor in
`src/autom8_asana/models/business/detection/facade.py`:

```python
from functools import cache

@cache
def _detection_cache_ttl() -> int:
    """Resolve settings lazily — cached after first call, never at import."""
    return get_settings().cache.ttl_detection
```

`@cache` ensures settings resolution happens exactly once per process (preserving
module-level-constant semantics) while deferring resolution until the first handler
invocation.

**Evidence of recurrence**: Anti-pattern recurred 3× in the 2026-04-29 cascade —
PR autom8y-asana#35 (`facade.py` lazy-load fix), PR autom8y-asana#36 (`config.py`
lazy-load fix), PR autom8y-asana#37 (`discovery.py` ARN-resolution fix).

**Regression gate**: `tests/unit/lambda_handlers/test_import_safety.py` (CP-01
carry-forward from VERDICT §6.1 — not yet authored; future `/10x-dev` scope).

**Cross-reference**: SCAR-LOG-001 in `.know/scar-tissue.md` (defensive pattern record).

**Sources**: GLINT-002 (H) · file:line anchor `src/autom8_asana/models/business/detection/facade.py:78` ·
VERDICT-eunomia-final-adjudication-2026-04-29.md §6.1 CP-01.

---

### Dockerfile Stage-0 / Stage-2 Canonical Pattern (GLINT-008)

**Origin**: PR autom8y-asana#34 introduced this pattern after `autom8y-config 2.0.1`
IPv4 fix mandated embedding the AWS Parameters and Secrets Lambda Extension binary
into container-image Lambdas (which cannot use Lambda Layers).

**Stage-0** (`secrets-extension` builder stage): downloads and unpacks the
AWS Parameters and Secrets Lambda Extension binary into `/opt/extensions/` using an
Amazon Linux minimal base. Accepts `SECRETS_EXT_LAYER_URL` as a build-arg; no-ops
gracefully (emits empty `/opt/extensions/`) when the arg is unset (ECS-only builds).

**Stage-2** (runtime stage): copies the extension binary from stage-0 using
`COPY --link --from=secrets-extension`:

```dockerfile
COPY --link --from=secrets-extension /opt/extensions/ /opt/extensions/
```

`--link` preserves layer cache independence — the runtime image is not invalidated
when only the extension binary changes.

**Canonical file**: `Dockerfile` at repo root (lines 25-55 Stage-0; line 109 Stage-2
`COPY --link`).

**Enforcement status — CULTURALLY ENFORCED ONLY**: No hadolint rule, grep gate, or
CI step currently verifies this pattern. Deviations are not caught automatically.
An ADR-justification requirement for deviations is recommended; a hadolint or
custom-grep CI step is a deferred M-16 carry-forward (routed to `/sre` via
VERDICT §7).

**Sources**: GLINT-008 (M) · file:line anchor `Dockerfile:44,109` ·
VERDICT-eunomia-final-adjudication-2026-04-29.md §7 M-16 (routed to /sre).


## Experiential Observations (from session history)

The cross-session corpus (18+ wrapped sessions) shows Bash dominates tool calls (65% of grepped). Edit usage correlates with productive sessions — project-crucible ran 8h25m with 36+ commits across 6 sprints. SCAR test cluster (33 inviolable tests) is documented as a sacred constraint.

Coverage floor is `>=80%` non-negotiable per project-crucible. Parametrize rate target `>=8%`. 86.8% local fixture ratio identified as anti-pattern.

## Knowledge Gaps

- The `patterns/` package has only `error_classification.py` and `async_method.py` observed; full idiom inventory not traced
- `lifecycle/engine.py` Protocol inventory is grep-based; full lifecycle idioms not fully traced
- `automation/` sub-packages (`events/`, `polling/`, `workflows/`) not individually inspected
- `search/`, `batch/` full API surface not traced
- Dual logging styles (`extra={}` vs keyword-arg) origin not fully traced — may have autom8y_log SDK version dependency

```metadata
confidence: 0.93
error_handling_style_grade: A
file_organization_grade: A
domain_specific_idioms_grade: A
naming_patterns_grade: B
overall_grade: A
source_hash: "20ef7952"
generated_at: "2026-05-04T00:00Z"
```
