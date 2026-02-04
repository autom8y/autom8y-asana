# HYG-005: Architectural Consistency & Pattern Scan

**Date**: 2026-02-04
**Scope**: `src/autom8_asana/` -- architectural inconsistencies and pattern violations
**Prior art**: `architectural-opportunities.md` (13 opportunities). This report focuses on concrete file-level findings, not strategic opportunities.

---

## Summary

| Category | Critical | Moderate | Minor | Total |
|----------|----------|----------|-------|-------|
| orphaned-module | 1 | 2 | 0 | 3 |
| inconsistent-pattern | 0 | 4 | 4 | 8 |
| config-inconsistency | 0 | 1 | 1 | 2 |
| logging-inconsistency | 0 | 1 | 1 | 2 |
| layer-violation | 0 | 0 | 3 | 3 |
| circular-import | 0 | 0 | 0 | 0 |
| **Total** | **1** | **8** | **9** | **18** |

No circular imports were detected. The codebase uses TYPE_CHECKING guards and lazy imports extensively, which prevents import cycles.

---

## Findings

### Orphaned Modules (defined but never wired into production code)

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| HYG-005-01 | `src/autom8_asana/cache/connections/` (all 4 files) | - | orphaned-module | critical | `RedisConnectionManager`, `S3ConnectionManager`, `ConnectionRegistry` are defined and exported from `__init__.py` but zero production files import them. Only consumed by their own `__init__.py` and test files (`tests/unit/cache/connections/`). These implement TDD-connection-lifecycle-management but were never wired into `cache/backends/redis.py` or `cache/backends/s3.py` which still manage their own connections inline. |
| HYG-005-02 | `src/autom8_asana/services/task_service.py`, `section_service.py`, `entity_service.py` | - | orphaned-module | moderate | `TaskService`, `SectionService`, `EntityService` are fully implemented service-layer classes (per TDD-SERVICE-LAYER-001) but are never imported or used by `api/routes/tasks.py`, `api/routes/sections.py`, or any other production module. Only consumed by their own cross-references and test files. The `task_service.py` docstring explicitly states "Route wiring is Phase 3/4 work per the migration plan" -- confirming this is intentional incomplete migration. |
| HYG-005-03 | `src/autom8_asana/dataframes/storage.py` | - | orphaned-module | moderate | `DataFrameStorage` protocol and `S3DataFrameStorage` implementation (TDD-UNIFIED-DF-PERSISTENCE-001) are defined but only imported by `tests/unit/dataframes/test_storage.py`. Zero production consumers. The docstring confirms "Phase 1: Additive introduction. No existing consumers are modified." |

**Not orphaned (verified wired in)**:
- `core/entity_registry.py` -- actively used by `core/entity_types.py`, `services/resolver.py`, `config.py`, `services/universal_strategy.py`, `cache/policies/freshness_policy.py`
- `core/exceptions.py` -- imported by 16 production files across `clients/`, `cache/`, `dataframes/`
- `core/connections.py` -- used by `cache/connections/redis.py`, `cache/connections/s3.py`, `cache/connections/registry.py` (though those are themselves orphaned per HYG-005-01)
- `core/retry.py` -- used by `cache/connections/redis.py`, `cache/connections/s3.py`, `dataframes/storage.py`
- `cache/dataframe/build_coordinator.py` -- exported via `cache/dataframe/__init__.py` but only consumed by test files (borderline orphan; has test coverage but no production callers)
- `cache/integration/mutation_invalidator.py` -- wired in via shim at `cache/mutation_invalidator.py`, used by `api/dependencies.py` and `api/main.py`
- `services/errors.py`, `services/entity_context.py` -- used by the service modules (which are themselves orphaned)
- `dataframes/builders/build_result.py` -- used by `builders/progressive.py` and `cache/integration/dataframe_cache.py`

---

### Inconsistent Patterns

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| HYG-005-04 | 64 import sites across `src/autom8_asana/` (excluding `cache/` internal) | various | inconsistent-pattern | moderate | **Deprecated shim imports still dominant.** The cache module was reorganized into `models/`, `policies/`, `providers/`, `integration/` subpackages, with backward-compatibility shims at the old paths. However, 64 import statements across production code still use the old shim paths (e.g., `from autom8_asana.cache.entry import EntryType` instead of `from autom8_asana.cache.models.entry import EntryType`). Key offenders: `clients/base.py`, `config.py`, `dataframes/cache_integration.py`, `dataframes/builders/task_cache.py`, `dataframes/views/dataframe_view.py`. The shims work via `sys.modules` replacement, so behavior is correct, but the inconsistency means some files use canonical paths while others use deprecated paths. |
| HYG-005-05 | `src/autom8_asana/api/routes/tasks.py:54`, `sections.py:39`, `dependencies.py:33`, `main.py:148` | 54,39,33,148 | inconsistent-pattern | moderate | **API layer imports from deprecated shim paths for new cache modules.** `api/routes/tasks.py` and `sections.py` import `MutationEvent` from `cache.mutation_event` (shim) instead of `cache.models.mutation_event`. `api/dependencies.py` and `api/main.py` import `MutationInvalidator` from `cache.mutation_invalidator` (shim) instead of `cache.integration.mutation_invalidator`. These are recent additions (TDD-CACHE-INVALIDATION-001) that should have used canonical paths from the start. |
| HYG-005-06 | `src/autom8_asana/api/routes/` (all route files) | - | inconsistent-pattern | moderate | **Mixed error handling: `HTTPException` vs centralized handlers.** The API has a centralized error handler system in `api/errors.py` (`register_exception_handlers`) that maps SDK exceptions (NotFoundError, AuthenticationError, etc.) to structured JSON responses. However, route files also raise raw `HTTPException` directly (~80+ sites across routes). Some routes mix both patterns in the same file. For example, `routes/query.py` raises `HTTPException` for validation errors (lines 164, 260, 289, etc.) but relies on centralized handlers for SDK exceptions. This is arguably intentional (validation = HTTPException, SDK = handlers) but there is no documented convention, and `routes/resolver.py` raises HTTPException even for what could be SDK-level errors. |
| HYG-005-07 | `src/autom8_asana/api/routes/` (all route files) | - | inconsistent-pattern | moderate | **No route files import from `api/errors.py`.** Zero route files use `from autom8_asana.api.errors import ...`. Error handling is either raw `HTTPException` or implicit via the registered exception handlers on the FastAPI app. This means route-level errors have no structured error code consistency (`ErrorDetail`, `ErrorResponse` models from `api/models.py` are only used by the centralized handlers). |
| HYG-005-08 | `src/autom8_asana/cache/backends/memory.py` vs `redis.py` vs `s3.py` | - | inconsistent-pattern | minor | **Cache backend logger inconsistency.** `memory.py` does not import or use a logger at all. `redis.py` and `s3.py` both import `get_logger` from `autom8y_log` and define `logger = get_logger(__name__)`. All three implement the same `CacheProvider` protocol via `DegradedModeMixin` and share the same import structure for models, but the absence of logging in the memory backend means debug/error paths behave differently. |
| HYG-005-09 | `src/autom8_asana/protocols/cache.py:9-11` | 9 | inconsistent-pattern | minor | **Protocol TYPE_CHECKING imports use old shim paths.** `protocols/cache.py` imports `CacheEntry`, `EntryType`, `Freshness`, `CacheMetrics` from old flat paths (`cache.entry`, `cache.freshness`, `cache.metrics`) rather than canonical subpackage paths. As the defining protocol for all cache backends, this should be the first module to use canonical paths. |
| HYG-005-10 | `src/autom8_asana/_defaults/cache.py` | various | inconsistent-pattern | minor | **NullCacheProvider uses old shim paths.** The null/default cache implementation imports from `cache.entry`, `cache.freshness`, `cache.metrics`, `cache.versioning` (all deprecated shim paths). This module is loaded at import time as part of the defaults system, making it a high-visibility import path. |
| HYG-005-11 | `src/autom8_asana/cache/dataframe/build_coordinator.py` | - | inconsistent-pattern | minor | **BuildCoordinator exported but has zero production callers.** Exported via `cache/dataframe/__init__.py` and has comprehensive test coverage (800+ lines in `test_build_coordinator.py`), but no production module instantiates or calls it. Similar to HYG-005-02 (incomplete migration), but less severe because it is at least reachable via the package export. |

---

### Configuration Access Inconsistencies

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| HYG-005-12 | 30+ files across `src/autom8_asana/` | various | config-inconsistency | moderate | **Three distinct configuration patterns coexist.** (1) `settings.py` (Pydantic Settings, `get_settings()`) -- used by `_defaults/auth.py`, `cache/integration/factory.py`, `cache/backends/s3.py`, `client.py`, `dataframes/section_persistence.py`, `dataframes/async_s3.py`. (2) `config.py` (manual dataclass `AsanaConfig` with `os.environ` parsing) -- used by `clients/base.py`, `transport/`, `cache/integration/dataframe_cache.py`, `dataframes/builders/progressive.py`. (3) Direct `os.environ.get()` calls -- 35+ sites across `api/main.py` (5 sites), `lambda_handlers/cache_warmer.py` (4 sites), `api/routes/admin.py`, `api/routes/health.py`, `cache/dataframe/factory.py`, `cache/dataframe/decorator.py`, `cache/dataframe/tiers/memory.py`, `dataframes/builders/progressive.py`, `entrypoint.py`, `clients/data/config.py`, `services/discovery.py`. The `settings.py` docstring explicitly says it "Replaces scattered os.environ.get() calls" but many scattered calls remain. |
| HYG-005-13 | `src/autom8_asana/clients/data/config.py:242,299,306` | 242 | config-inconsistency | minor | **Data client has its own config system.** `DataClientConfig` reads `AUTOM8_DATA_URL`, `AUTOM8_DATA_CACHE_TTL` directly from `os.environ` via `from_env()` classmethod, completely independent of both `settings.py` and `config.py`. This is a fourth config pattern specific to one subsystem. |

---

### Logging Inconsistencies

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| HYG-005-14 | `services/task_service.py:20,36`, `services/section_service.py:18,32`, `services/entity_service.py:23,36`, `core/entity_registry.py:25,30` | various | logging-inconsistency | moderate | **New modules use stdlib `logging.getLogger()` instead of `autom8y_log.get_logger()`.** The codebase standard is `from autom8y_log import get_logger` (used by 102 files). Four new modules from the architectural initiative use raw `import logging` + `logging.getLogger(__name__)` instead. This bypasses the structured logging configuration provided by `autom8y_log` (which wraps `autom8y_log` for JSON output, log level management, etc.). The `api/middleware.py` module also uses `structlog.get_logger()` directly, but that is intentional for the middleware layer. |
| HYG-005-15 | `src/autom8_asana/api/middleware.py:99` | 99 | logging-inconsistency | minor | **Middleware uses `structlog.get_logger()` directly.** While all other API modules use `autom8y_log.get_logger()`, the middleware uses `structlog.get_logger(__name__)` directly. This is the only production module outside `automation/polling/` that directly instantiates a structlog logger. The polling subsystem has its own `StructuredLogger` wrapper class that also uses structlog directly, but that is a self-contained subsystem. |

---

### Layer Violations (minor)

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| HYG-005-16 | `src/autom8_asana/api/routes/dataframes.py:42` | 42 | layer-violation | minor | **Route imports directly from `cache.unified` (shim path).** Should go through `cache` package public API or use the canonical `cache.providers.unified` path. Other route files import cache types through `api/dependencies.py` or via the `cache` package `__init__.py`. |
| HYG-005-17 | `src/autom8_asana/api/main.py:126,147` | 126 | layer-violation | minor | **App startup imports from deprecated `cache.schema_providers` and `cache.factory` shim paths.** These are the entry points for cache initialization. While the shim indirection works, the app startup is the ideal place to use canonical import paths (`cache.integration.schema_providers`, `cache.integration.factory`). |
| HYG-005-18 | `src/autom8_asana/dataframes/views/dataframe_view.py:440` | 440 | layer-violation | minor | **View imports `CompletenessLevel` from `cache.completeness` (deprecated shim).** `dataframe_view.py` already imports `FreshnessMode` from `cache.freshness_coordinator` (also a shim). Both should use canonical `cache.models.completeness` and `cache.integration.freshness_coordinator` respectively. |

---

## Cross-References to Architectural Opportunities

Several findings here map to opportunities documented in `architectural-opportunities.md`:

| Finding | Opportunity | Relationship |
|---------|-------------|--------------|
| HYG-005-01 (connections orphaned) | D1 (Connection Lifecycle Management) | Connection module was built per TDD but never integrated |
| HYG-005-02 (services orphaned) | B5 (Service Layer Extraction) | Service layer was built per TDD but route wiring not done |
| HYG-005-03 (storage orphaned) | B6 (Unified DataFrame Persistence) | Storage protocol was built per TDD but no consumers migrated |
| HYG-005-04/05 (shim imports) | B2 (Cache Module Reorganization) | Reorg completed structurally but import migration incomplete |
| HYG-005-12 (config patterns) | B4 (Config Consolidation) | Three config systems documented in B4; 35+ raw os.environ remain |
| HYG-005-06/07 (error handling) | New finding | Not covered in architectural opportunities |
| HYG-005-14 (logging) | New finding | Not covered in architectural opportunities |

---

## Priority Ranking (by cleanup ROI)

| Rank | Finding | ROI Rationale |
|------|---------|---------------|
| 1 | HYG-005-14 (logging) | 4 files, trivial fix (replace `import logging` with `from autom8y_log import get_logger`), high consistency value |
| 2 | HYG-005-04/05 (shim imports) | 64+ sites, mechanical find-and-replace, eliminates deprecated path usage |
| 3 | HYG-005-08/09/10 (minor pattern) | Small fixes that improve consistency |
| 4 | HYG-005-12 (config) | High blast radius but complex fix; document convention first |
| 5 | HYG-005-06/07 (error handling) | Needs design decision before fixing |
| 6 | HYG-005-01 (connections) | Requires architectural decision: wire in or remove |
| 7 | HYG-005-02/03 (services/storage) | Intentionally incomplete; needs Phase 3/4 migration plan |
