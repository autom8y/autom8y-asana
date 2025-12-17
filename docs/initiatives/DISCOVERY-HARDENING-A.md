# Discovery Document: Architecture Hardening Initiative A - Foundation

**Initiative**: Architecture Hardening Sprint - Foundation Issues
**Session**: 1 (Discovery)
**Date**: 2025-12-16
**Author**: Requirements Analyst
**Scope**: Issues 9-14 from Architecture Hardening Prompt -1

---

## Executive Summary

This discovery document audits the current SDK state to identify all instances of 6 foundation issues from the Architecture Hardening Sprint. The audit covers exception hierarchy inconsistencies, naming inconsistencies, private function exports, incomplete stub holders, minimal logging, and missing observability hooks.

**Key Findings**:
- 3 private functions exported in `models/business/__init__.py` `__all__`
- Exception hierarchy has 2 parallel inheritance chains (design issue)
- ValidationError naming conflict with Pydantic
- Logging coverage is inconsistent across modules (13 modules with direct logging, 14 clients use `_log_operation` only for list methods)
- 4 stub holders return untyped `Task` children
- No structured observability hooks beyond `@error_handler` decorator

---

## Issue 9: Exception Hierarchy Inconsistent

### Current State

The SDK has two exception files:
1. `/src/autom8_asana/exceptions.py` - Main exception hierarchy
2. `/src/autom8_asana/persistence/exceptions.py` - Save-specific exceptions

### Exception Inventory

#### Main Exceptions (`exceptions.py`)

| Exception | Parent | Attributes | Notes |
|-----------|--------|------------|-------|
| `AsanaError` | `Exception` | `message`, `status_code`, `response`, `errors` | Base for API errors |
| `AuthenticationError` | `AsanaError` | (inherited) | HTTP 401 |
| `ForbiddenError` | `AsanaError` | (inherited) | HTTP 403 |
| `NotFoundError` | `AsanaError` | (inherited) | HTTP 404 |
| `GoneError` | `AsanaError` | (inherited) | HTTP 410 |
| `RateLimitError` | `AsanaError` | `retry_after` | HTTP 429 |
| `ServerError` | `AsanaError` | (inherited) | HTTP 5xx |
| `TimeoutError` | `AsanaError` | (inherited) | Request timeout |
| `ConfigurationError` | `AsanaError` | (inherited) | SDK config error |
| `SyncInAsyncContextError` | `RuntimeError` | - | **Not** an AsanaError! |
| `CircuitBreakerOpenError` | `AsanaError` | `time_until_recovery` | Circuit breaker |
| `NameNotFoundError` | `AsanaError` | `resource_type`, `name`, `scope`, `suggestions`, `available_names` | Name resolution |
| `HydrationError` | `AsanaError` | `entity_gid`, `entity_type`, `phase`, `partial_result`, `__cause__` | Hydration failures |
| `ResolutionError` | `AsanaError` | `entity_gid`, `strategies_tried`, `__cause__` | Resolution failures |

#### Persistence Exceptions (`persistence/exceptions.py`)

| Exception | Parent | Attributes | Notes |
|-----------|--------|------------|-------|
| `SaveOrchestrationError` | `AsanaError` | (inherited) | Base for save errors |
| `SessionClosedError` | `SaveOrchestrationError` | - | Session reuse |
| `CyclicDependencyError` | `SaveOrchestrationError` | `cycle` | Dep cycle |
| `DependencyResolutionError` | `SaveOrchestrationError` | `entity`, `dependency`, `__cause__` | Dep failed |
| `PartialSaveError` | `SaveOrchestrationError` | `result` | Some ops failed |
| `UnsupportedOperationError` | `SaveOrchestrationError` | `field_name`, `suggested_methods` | Action required |
| `PositioningConflictError` | `SaveOrchestrationError` | `insert_before`, `insert_after` | Position conflict |
| `ValidationError` | `SaveOrchestrationError` | (inherited) | **Naming conflict!** |
| `SaveSessionError` | `SaveOrchestrationError` | `result` | P1 method failure |

### Identified Issues

1. **Parallel Inheritance Chain**: `SyncInAsyncContextError` inherits from `RuntimeError`, not `AsanaError`. This breaks the pattern of catching all SDK errors with `except AsanaError`.

2. **ValidationError Naming Conflict**: `persistence/exceptions.py` defines `ValidationError` which conflicts with `pydantic.ValidationError`. Users importing both will have shadowing issues.

3. **Inconsistent `__cause__` Usage**: Some exceptions set `__cause__` directly in `__init__`, others don't. Should be consistent.

4. **Missing from `__all__` in persistence**: `PositioningConflictError` and `ValidationError` are defined but not exported in `persistence/__init__.py`.

### Proposed Corrections

| Issue | Current | Proposed |
|-------|---------|----------|
| SyncInAsyncContextError parent | `RuntimeError` | Keep as-is (intentional per ADR-0002) OR document why |
| ValidationError naming | `ValidationError` | Rename to `GidValidationError` or `EntityValidationError` |
| `__cause__` consistency | Inconsistent | Add `cause: Exception | None` param to all exceptions that chain |
| Missing exports | Not in `__all__` | Add `PositioningConflictError`, `ValidationError` to persistence `__all__` |

---

## Issue 10: Naming Inconsistencies

### Client Method Naming Audit

All clients follow consistent patterns:
- `get_async()` / `get()` - Single resource
- `create_async()` / `create()` - Create resource
- `update_async()` / `update()` - Update resource
- `delete_async()` / `delete()` - Delete resource
- `list_async()` / `list_for_*_async()` - List resources

**Inconsistency Found**: List method naming varies:
- `TasksClient.list_async()` - generic
- `TagsClient.list_for_workspace_async()` / `list_for_task_async()` - specific
- `SectionsClient.list_for_project_async()` - specific

This is actually **intentional** (context-specific listing), but should be documented.

### Model Naming Audit

**No issues found** - Models follow `AsanaResource` -> specific type pattern consistently.

### Exception Naming Audit

| Current Name | Issue | Proposed Name |
|--------------|-------|---------------|
| `ValidationError` | Conflicts with Pydantic | `GidValidationError` |
| `TimeoutError` | Shadows built-in | Keep (intentional SDK-specific) |

### Internal Naming Audit

Private methods consistently use `_` prefix. Sync wrapper methods use `_*_sync` pattern.

---

## Issue 11: Private Functions in `__all__`

### Audit Results

#### `/src/autom8_asana/models/business/__init__.py` - **3 ISSUES FOUND**

```python
__all__ = [
    # ...
    # Hydration (Phase 2 - Upward Traversal)
    "_traverse_upward_async",       # PRIVATE - should not be exported
    "_convert_to_typed_entity",     # PRIVATE - should not be exported
    # ...
    "_is_recoverable",              # PRIVATE - should not be exported
    # ...
]
```

**Private functions incorrectly exported**:
1. `_traverse_upward_async` - Internal traversal function
2. `_convert_to_typed_entity` - Internal conversion function
3. `_is_recoverable` - Internal error classification

#### All Other `__init__.py` Files - **NO ISSUES**

Checked files:
- `/src/autom8_asana/__init__.py` - Clean
- `/src/autom8_asana/clients/__init__.py` - Clean
- `/src/autom8_asana/models/__init__.py` - Clean
- `/src/autom8_asana/persistence/__init__.py` - Clean (but missing some exceptions)
- `/src/autom8_asana/batch/__init__.py` - Clean
- `/src/autom8_asana/cache/__init__.py` - Clean
- `/src/autom8_asana/observability/__init__.py` - Clean
- `/src/autom8_asana/protocols/__init__.py` - Clean
- `/src/autom8_asana/transport/__init__.py` - Clean
- `/src/autom8_asana/dataframes/__init__.py` - Clean
- `/src/autom8_asana/_defaults/__init__.py` - Clean
- `/src/autom8_asana/cache/backends/__init__.py` - Clean
- `/src/autom8_asana/dataframes/models/__init__.py` - Clean

### Proposed Fix

Remove private functions from `models/business/__init__.py`:

```python
# Remove from __all__:
# "_traverse_upward_async"
# "_convert_to_typed_entity"
# "_is_recoverable"
```

---

## Issue 12: Stub Holders Incomplete

### Stub Holder Inventory

Located in `/src/autom8_asana/models/business/business.py`:

| Holder Class | CHILD_TYPE | Children Property | Status |
|--------------|------------|-------------------|--------|
| `DNAHolder` | `Task` | `children: list[Task]` | **STUB** - Returns untyped Task |
| `ReconciliationsHolder` | `Task` | `children: list[Task]` | **STUB** - Returns untyped Task |
| `VideographyHolder` | `Task` | `children: list[Task]` | **STUB** - Returns untyped Task |
| `AssetEditHolder` | `Task`* | `asset_edits: list[AssetEdit]` | **TYPED** - Upgraded in Phase 4 |

*Note: `AssetEditHolder.CHILD_TYPE` is still `Task` at class level but returns typed `AssetEdit` at runtime.

### Typed Holders (Complete)

| Holder Class | Location | CHILD_TYPE | Status |
|--------------|----------|------------|--------|
| `ContactHolder` | `contact.py` | `Contact` | Complete |
| `UnitHolder` | `unit.py` | `Unit` | Complete |
| `LocationHolder` | `location.py` | `Location` | Complete |
| `OfferHolder` | `offer.py` | `Offer` | Complete |
| `ProcessHolder` | `process.py` | `Process` | Complete |

### Incompleteness Details

Stub holders are intentionally minimal per FR-HOLDER-007:
- Return `list[Task]` instead of typed children
- Have `_populate_children()` but just store raw tasks
- Set `_business` reference properly
- Have `invalidate_cache()` method

**Missing Functionality**:
1. No typed child model (DNA, Reconciliation, Videography entities don't exist)
2. No custom field accessors for children
3. No convenience properties on children
4. No bidirectional navigation from child to Business

### Proposed Path Forward

Per FR-HOLDER-007, stub holders are **intentionally deferred**. Options:

1. **Keep as stubs** (current) - Children remain `Task`, typed later when domain model defined
2. **Create minimal typed models** - Define `DNA`, `Reconciliation`, `Videography` as thin `Task` subclasses
3. **Document stub pattern** - Add docstrings explaining stub vs typed holders

**Recommendation**: Option 3 (Document) for now. Creating typed models requires domain knowledge about what custom fields and behaviors these entities have.

---

## Issue 13: Logging is Minimal

### Logging Coverage Map

#### Modules with Direct Logging (via `import logging`)

| Module | Logger | Log Levels Used | Notes |
|--------|--------|-----------------|-------|
| `_defaults/log.py` | `autom8_asana` | debug, info, warning, error | Default provider |
| `_compat.py` | `autom8_asana._compat` | warning | Deprecation warnings |
| `persistence/session.py` | via `self._log` | debug, warning, info, error | Session operations |
| `batch/client.py` | via `self._log` | debug, info | Batch operations |
| `dataframes/cache_integration.py` | `__name__` | debug, error | Cache ops |
| `dataframes/resolver/default.py` | `__name__` | debug, warning | Resolution |
| `transport/rate_limiter.py` | via `self._logger` | info, warning | Rate limiting |
| `transport/http.py` | via `self._logger` | debug, warning | HTTP requests |
| `transport/circuit_breaker.py` | via `self._log` | info | Circuit state |
| `transport/retry.py` | via `self._logger` | warning | Retry attempts |
| `cache/tiered.py` | `__name__` | warning | Tiered cache |
| `cache/backends/s3.py` | `__name__` | warning, error, info | S3 ops |
| `cache/backends/redis.py` | `__name__` | warning, error, info | Redis ops |
| `models/task.py` | `__name__` | warning | Custom field issues |
| `models/business/detection.py` | `__name__` | debug, warning | Entity detection |
| `models/business/hydration.py` | `__name__` | debug, warning, info | Hydration |
| `models/business/asset_edit.py` | `__name__` | debug, warning, info | Resolution |
| `models/business/resolution.py` | `__name__` | warning | Batch resolution |
| `models/business/contact.py` | inline import | warning | Owner detection |
| `models/business/offer.py` | inline import | warning | Ad status |
| `models/business/unit.py` | inline import | warning | Field access |
| `models/business/business.py` | inline import | warning | Hydration failure |

#### Modules Using `_log_operation()` Only

All client modules (`clients/*.py`) use `_log_operation()` which logs at debug level via `self._log`. However, this only logs operation **start**, not completion or errors for non-async methods.

| Client | Logged Operations |
|--------|-------------------|
| `TasksClient` | list_async, subtasks_async, dependents_async |
| `ProjectsClient` | list_async, get_sections_async |
| `SectionsClient` | list_for_project_async |
| `TagsClient` | get_async, create_async, update_async, delete_async, list_for_workspace_async, list_for_task_async, add_to_task_async, remove_from_task_async |
| `UsersClient` | (similar pattern) |
| `WorkspacesClient` | (similar pattern) |
| (etc.) | |

### Identified Gaps

1. **No logging in models** (except business layer): Standard models like `Task`, `Project`, `Section` don't log
2. **No structured logging**: Messages are format strings, not structured key-value
3. **No log levels configurable**: Hard-coded levels in each module
4. **Inconsistent logger naming**: Mix of `__name__`, `autom8_asana.*`, and provider injection
5. **Missing operation completion logs**: `_log_operation` logs start but not end
6. **No request/response logging**: HTTP layer logs minimally

### Proposed Improvements

| Gap | Recommendation | Priority |
|-----|----------------|----------|
| Structured logging | Use `extra={}` dict for structured context | Medium |
| Logger naming | Standardize on `autom8_asana.{module}` pattern | Low |
| Operation completion | Enhance `_log_operation` or use `@error_handler` consistently | Medium |
| Request/response | Add opt-in verbose logging in transport layer | Low |

---

## Issue 14: No Observability Hooks

### Current Observability

1. **`@error_handler` decorator** (`observability/decorators.py`)
   - Generates correlation IDs
   - Logs start/end/error
   - Enriches exceptions with correlation context
   - Measures operation timing

2. **`CorrelationContext`** (`observability/correlation.py`)
   - Context var for correlation ID propagation
   - `generate_correlation_id()` function

3. **`LogProvider` protocol** (`protocols/log.py`)
   - Abstract logging interface
   - Implemented by `DefaultLogProvider`

4. **`CacheMetrics`** (`cache/metrics.py`)
   - Hit/miss tracking
   - Event callbacks

### Missing Observability Hooks

| Hook Type | Current State | Recommended Placement |
|-----------|---------------|----------------------|
| **Pre-request hook** | None | `AsyncHTTPClient._request()` |
| **Post-request hook** | None | `AsyncHTTPClient._request()` |
| **Pre-save hook** | Exists (session.on_pre_save) | Adequate |
| **Post-save hook** | Exists (session.on_post_save) | Adequate |
| **Cache event hook** | Exists (CacheMetrics callback) | Adequate |
| **Rate limit event** | Logged only | Add callback hook |
| **Circuit breaker event** | Logged only | Add callback hook |
| **Retry event** | Logged only | Add callback hook |
| **Batch operation hook** | None | `BatchClient.execute_async()` |
| **Hydration event hook** | None | Hydration functions |
| **Resolution event hook** | None | Resolution functions |

### Proposed Hook Architecture

```python
# Protocol for observability hooks
class ObservabilityHook(Protocol):
    async def on_request(self, method: str, path: str, correlation_id: str) -> None: ...
    async def on_response(self, method: str, path: str, status: int, elapsed_ms: float) -> None: ...
    async def on_error(self, method: str, path: str, error: Exception) -> None: ...
    async def on_rate_limit(self, retry_after: int) -> None: ...
    async def on_circuit_open(self, time_until_recovery: float) -> None: ...
    async def on_retry(self, attempt: int, max_attempts: int) -> None: ...
```

### Integration Points

1. **Transport Layer** (`transport/http.py`)
   - Hook into `_request()` method
   - Pre/post request callbacks
   - Error callbacks

2. **Rate Limiter** (`transport/rate_limiter.py`)
   - Hook on rate limit hit

3. **Circuit Breaker** (`transport/circuit_breaker.py`)
   - Hook on state transitions

4. **Retry Handler** (`transport/retry.py`)
   - Hook on retry attempts

---

## Summary of Findings

### Critical Issues (Must Fix)

| Issue | Location | Impact |
|-------|----------|--------|
| Private functions in `__all__` | `models/business/__init__.py` | API pollution |
| ValidationError naming conflict | `persistence/exceptions.py` | Import shadowing |
| Missing exception exports | `persistence/__init__.py` | Incomplete API |

### Moderate Issues (Should Fix)

| Issue | Location | Impact |
|-------|----------|--------|
| SyncInAsyncContextError inheritance | `exceptions.py` | Catching inconsistency |
| Inconsistent logger naming | Multiple modules | Debugging difficulty |
| No observability hooks | Transport layer | Monitoring gaps |

### Low Priority Issues (Nice to Have)

| Issue | Location | Impact |
|-------|----------|--------|
| Stub holders incomplete | `business.py` | Deferred functionality |
| List method naming variance | Clients | Minor inconsistency |
| No structured logging | All modules | Log parsing difficulty |

---

## Blocking Questions

1. **ValidationError Rename**: Confirm new name `GidValidationError` or alternative?
2. **Stub Holder Strategy**: Keep as stubs or create minimal typed models?
3. **Observability Hook Priority**: Which hooks are highest priority for the sprint?
4. **SyncInAsyncContextError**: Confirm this should remain as `RuntimeError` (per ADR-0002)?

---

## Next Steps

1. **Requirements Phase**: Create PRD-HARDENING-A.md with requirements for each fix
2. **Architecture Phase**: Create TDD for observability hook system
3. **Implementation Phase**: Fix critical issues first, then moderate, then low

---

## Appendix: Files Audited

### Exception Files
- `/src/autom8_asana/exceptions.py`
- `/src/autom8_asana/persistence/exceptions.py`

### `__init__.py` Files
- `/src/autom8_asana/__init__.py`
- `/src/autom8_asana/clients/__init__.py`
- `/src/autom8_asana/models/__init__.py`
- `/src/autom8_asana/persistence/__init__.py`
- `/src/autom8_asana/batch/__init__.py`
- `/src/autom8_asana/cache/__init__.py`
- `/src/autom8_asana/cache/backends/__init__.py`
- `/src/autom8_asana/observability/__init__.py`
- `/src/autom8_asana/protocols/__init__.py`
- `/src/autom8_asana/transport/__init__.py`
- `/src/autom8_asana/dataframes/__init__.py`
- `/src/autom8_asana/dataframes/models/__init__.py`
- `/src/autom8_asana/_defaults/__init__.py`
- `/src/autom8_asana/models/business/__init__.py`

### Client Files
- `/src/autom8_asana/clients/base.py`
- `/src/autom8_asana/clients/tasks.py`
- `/src/autom8_asana/clients/projects.py`
- `/src/autom8_asana/clients/sections.py`
- `/src/autom8_asana/clients/tags.py`
- (and all other client files)

### Model Files
- `/src/autom8_asana/models/business/business.py`
- `/src/autom8_asana/models/business/base.py`
- (and all business model files)

### Observability Files
- `/src/autom8_asana/observability/decorators.py`
- `/src/autom8_asana/observability/correlation.py`
