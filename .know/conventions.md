---
domain: conventions
generated_at: "2026-02-27T11:21:29Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "73b6e61"
confidence: 0.85
format_version: "1.0"
---

# Codebase Conventions

## Error Handling Style

### Exception Hierarchy

The codebase uses a two-tier exception hierarchy:

**Tier 1 -- SDK Exceptions** (`src/autom8_asana/exceptions.py`):
- `AsanaError` is the root exception for all Asana API errors
- HTTP status-specific subclasses: `AuthenticationError` (401), `ForbiddenError` (403), `NotFoundError` (404), `GoneError` (410), `RateLimitError` (429), `ServerError` (5xx), `TimeoutError`
- Factory method: `AsanaError.from_response(response)` maps HTTP status to specific exception via `_STATUS_CODE_MAP`
- Domain exceptions: `HydrationError`, `ResolutionError`, `NameNotFoundError`
- Feature-specific hierarchies: `InsightsError` -> `InsightsValidationError` / `InsightsNotFoundError` / `InsightsServiceError`
- Non-API errors: `ConfigurationError` (inherits `AsanaError`), `SyncInAsyncContextError` (inherits `RuntimeError`), `CircuitBreakerOpenError`

**Tier 2 -- Service Layer Exceptions** (`src/autom8_asana/services/errors.py`):
- `ServiceError` is the root for business logic errors (separate from `AsanaError`)
- Each subclass has: `error_code` property (machine-readable), `status_hint` property (suggested HTTP status), `to_dict()` method
- Subclasses: `EntityNotFoundError` (404), `UnknownEntityError`, `UnknownSectionError`, `TaskNotFoundError`, `EntityTypeMismatchError`, `EntityValidationError` (400/422), `InvalidFieldError` (422), `InvalidParameterError` (400), `CacheNotReadyError` (503), `ServiceNotConfiguredError` (503)
- Error mapping: `SERVICE_ERROR_MAP` dict + `get_status_for_error()` walks MRO for most specific mapping

### Error Creation Patterns

- **SDK errors**: Created via `AsanaError.from_response(response)` factory (parses JSON body, extracts `errors` array, builds context string with HTTP status and request_id)
- **Service errors**: Constructed with domain-specific attributes (e.g., `UnknownEntityError(entity_type, available)`)
- **Route-level errors**: Use canonical helpers in `src/autom8_asana/api/errors.py`:
  - `raise_api_error(request_id, status_code, code, message)` -- for validation/precondition errors
  - `raise_service_error(request_id, error)` -- for `ServiceError` conversion to `HTTPException`
  - `_ERROR_STATUS` dict mapping + `_raise_query_error()` helper in query routes

### Error Propagation

- **Service -> API boundary**: Services raise `ServiceError` subclasses. Route handlers catch them and convert via `raise_service_error()`. SDK errors (`AsanaError` subclasses) are caught by registered exception handlers in `register_exception_handlers()`.
- **Exception handler chain**: Most specific first (NotFound, Auth, Forbidden, RateLimit, Validation, Server, Timeout) -> generic `AsanaError` -> catch-all `Exception`. Each returns structured JSON: `{error: {code, message, details}, meta: {request_id}}`.
- **Error context enrichment**: All error responses include `request_id` for correlation (per FR-ERR-008). SDK errors include HTTP status and Asana request_id. Service errors include domain-specific fields via `to_dict()`.

### Error Handling at Boundaries

- **API routes**: All errors mapped to structured JSON responses with machine-readable error codes. 500 responses hide implementation details (per FR-ERR-009).
- **Logging**: Errors logged with structured fields: `request_id`, `error_code`, `error_type`, `upstream_status`. Uses `logger.exception()` for unhandled exceptions to capture stack traces.
- **Circuit breaker**: `CircuitBreakerOpenError` for fast-fail when upstream is degraded (per ADR-0048).

## File Organization

### Package Structure Convention

Each package follows a consistent pattern:
- `__init__.py` exports public API via `__all__`
- Modules named by responsibility (not by type): `engine.py`, `service.py`, `models.py`, `errors.py`, `config.py`
- Private modules prefixed with `_` (e.g., `_pii.py`, `_cache.py`, `_retry.py` in `clients/data/`)
- `conftest.py` in test directories provides package-scoped fixtures

### File Naming Conventions

| Pattern | Convention | Example |
|---------|-----------|---------|
| Models | Named by resource type | `task.py`, `project.py`, `section.py` |
| Services | Named by concern | `query_service.py`, `entity_service.py` |
| Routes | Named by resource or feature | `query.py`, `health.py`, `resolver.py` |
| Utilities | Named by function | `string_utils.py`, `field_utils.py`, `datetime_utils.py` |
| Config | `config.py` per package | `api/config.py`, `clients/data/config.py` |
| Errors | `errors.py` or `exceptions.py` | `services/errors.py`, `persistence/exceptions.py` |
| Tests | Mirror source structure | `tests/unit/services/test_query_service.py` |

### Source Layout

```
src/
  autom8_asana/        # Main package
    __init__.py        # Public API + lazy-loaded DataFrame exports
    client.py          # Main SDK client (AsanaClient)
    config.py          # Central configuration
    exceptions.py      # Root exception hierarchy
    settings.py        # Pydantic settings
  autom8_query_cli.py  # CLI entry point (sets env defaults before import)
tests/
  conftest.py          # Root fixtures (MockHTTPClient, MockClientBuilder)
  unit/                # Unit tests (416 files)
  integration/         # Integration tests (38 files)
  validation/          # Validation tests (8 files)
  benchmarks/          # Performance benchmarks (4 files)
  _shared/             # Shared test utilities
```

### `__init__.py` Conventions

- Root `__init__.py` uses `__getattr__` for lazy-loading DataFrame exports (avoids pulling in polars for core SDK consumers)
- Package `__init__.py` files re-export the public API via `__all__`
- Comment annotations reference TDD/ADR document IDs (e.g., `# Per TDD-0009`, `# Per ADR-VAULT-001`)

### Internal vs Public Boundaries

- `_defaults/` prefixed with `_` to signal internal-only
- `clients/data/_endpoints/` uses `_` prefix for endpoint submodules
- `cache/dataframe/tiers/` contains implementation details not exported at package level
- Private modules within `clients/data/` (`_cache.py`, `_pii.py`, `_retry.py`, etc.) are implementation details of `DataServiceClient`

## Domain-Specific Idioms

### Canonical DI Pattern

Dependencies are injected via FastAPI's `Annotated[T, Depends(...)]` pattern:
```python
RequestId = Annotated[str, Depends(get_request_id)]
DataServiceClientDep = Annotated[DataServiceClient, Depends(...)]
EntityServiceDep = Annotated[EntityService, Depends(...)]
```

### Protocol-Based Interface Contracts

The `protocols/` package defines all DI boundaries as `typing.Protocol` classes:
- `AuthProvider` -- credential retrieval
- `CacheProvider` -- cache operations (get, put, warm)
- `DataFrameProvider` -- DataFrame access (decouples QueryEngine from services)
- `LogProvider` -- structured logging
- `ObservabilityHook` -- metrics/tracing hooks
- `MetricsEmitter` -- metric emission
- `InsightsProvider` -- insights data access

### EntityDescriptor-Driven Design

All entity metadata is declared once in `EntityDescriptor` frozen dataclasses in `core/entity_registry.py`. Four consumers are descriptor-driven (no hardcoded switch/case):
1. Schema auto-discovery via `schema_module_path`
2. Extractor creation via `extractor_class_path`
3. Entity relationships via `join_keys`
4. Cascading fields via `cascading_field_provider` flag

### SystemContext Reset Pattern

Singletons self-register their reset functions: `register_reset(SchemaRegistry.reset)`. Test fixtures call `SystemContext.reset_all()` before/after each test for complete isolation. This is the canonical approach -- do not use `importlib.reload()` or manual singleton clearing.

### Shared Creation Primitives

`core/creation.py` provides free functions (not classes) for entity creation. This is the canonical shared creation surface.

### Coordinator Pattern (SaveSession)

`SaveSession` in `persistence/session.py` coordinates 14 collaborators as a Coordinator pattern. This is documented as NOT a god object -- it orchestrates `ChangeTracker`, `ActionBuilder`, `ActionExecutor`, `DependencyGraph`, `HealingManager`, `CacheInvalidator`, `EventSystem`, etc. Do not decompose.

### MockClientBuilder Pattern

Tests use a builder pattern (`MockClientBuilder` in `tests/conftest.py`) for constructing mock `AsanaClient` instances with explicit opt-in for each capability (batch, http, cache, projects, tasks).

### Section Classification

`SectionClassifier` groups entity records into classification groups (active, activating, inactive, ignored) based on Asana section membership. Used by the metrics system for filtering (Step 0.5 filter before column select, matching QueryEngine pattern).

## Naming Patterns

### Module and Package Naming

- Snake_case for all module names
- Packages named by domain noun: `lifecycle`, `persistence`, `automation`, `resolution`
- Private modules prefixed with `_`: `_defaults`, `_pii.py`, `_cache.py`

### Type Naming

- PascalCase for all classes
- `*Error` suffix for exceptions: `AsanaError`, `ServiceError`, `CacheNotReadyError`
- `*Config` suffix for configuration dataclasses: `AsanaConfig`, `LifecycleConfig`, `ConcurrencyConfig`
- `*Result` suffix for operation results: `SaveResult`, `CreationResult`, `CascadeResult`, `WarmResult`
- `*Service` suffix for service classes: `EntityQueryService`, `EntityCreationService`, `SearchService`
- `*Client` suffix for API clients: `AsanaClient`, `DataServiceClient`, `BatchClient`, `TasksClient`
- `*Provider` suffix for protocol implementations: `EnvAuthProvider`, `TieredProvider`
- `*Strategy` suffix for strategy pattern: `UniversalResolutionStrategy`
- `*Handler` suffix for event/action handlers: `InitActionHandler`, `CommentHandler`

### Function Naming

- Async functions: `*_async` suffix (e.g., `get_async`, `commit_async`, `handle_transition_async`)
- Sync wrappers: Same name without suffix, uses `sync_wrapper` from `transport/sync.py`
- Private helpers: `_` prefix (e.g., `_build_error_response`, `_resolve_dotted_path`)
- Factory functions: `create_*` prefix (e.g., `create_app`, `create_cache_provider`)
- Validation functions: `validate_*` prefix (e.g., `validate_fields`, `validate_project_env_vars`)

### Constant Naming

- UPPER_SNAKE_CASE for module-level constants: `ENTITY_TYPES`, `_STATUS_CODE_MAP`, `CASCADE_CRITICAL_FIELDS`
- Private constants: `_` prefix (e.g., `_DATAFRAME_EXPORTS`, `_reset_registry`)

### ADR/TDD Reference Convention

Comments reference design documents with standard prefixes:
- `# Per ADR-NNNN:` for architecture decision records
- `# Per TDD-*:` for technical design documents
- `# Per FR-*:` for functional requirements
- `# Per PRD-*:` for product requirements documents

### GID Convention

Asana Global IDs are always strings (never integers), stored in fields named `*_gid`: `project_gid`, `workspace_gid`, `entity_gid`, `task_gid`. Validated by `GidValidationError` at persistence boundary.

## Knowledge Gaps

- The full set of domain-specific terms (e.g., "holder", "cascading field", "seeding") was not exhaustively cataloged with definitions.
- Import conventions for the `automation/workflows/` subpackage were not examined in detail.
- The exact pattern for `_defaults/` provider selection (env-based vs explicit) was not fully traced.
