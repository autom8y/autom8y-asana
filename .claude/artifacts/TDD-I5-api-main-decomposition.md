# TDD-I5: API Main Decomposition

**Initiative**: I5 API Main Decomposition (Wave 3)
**Session**: session-20260204-195700-0f38ebf6
**Status**: PROPOSED
**Date**: 2026-02-05

---

## 1. Current Structure Analysis

`src/autom8_asana/api/main.py` is 1520 lines containing 6 distinct concerns:

### Concern Map (by line range)

| Concern | Lines | Count | Functions/Symbols |
|---------|-------|-------|-------------------|
| **Imports + module docstring** | 1-81 | 81 | Module-level imports, side-effect import |
| **Initialization helpers** | 84-176 | 93 | `_initialize_dataframe_cache()`, `_register_schema_providers()`, `_initialize_mutation_invalidator()` |
| **Lifespan manager** | 178-311 | 134 | `lifespan()`, logger declaration |
| **Entity discovery** | 314-331 | 18 | `_discover_entity_projects()` |
| **Legacy preload** | 333-704 | 372 | `_preload_dataframe_cache()`, `_do_incremental_catchup()`, `_do_full_rebuild()` |
| **Progressive preload** | 897-1392 | 496 | Constants, `_invoke_cache_warmer_lambda_from_preload()`, `_preload_dataframe_cache_progressive()` |
| **App factory + entrypoint** | 1394-1520 | 127 | `create_app()`, `__main__` block |

**Key observation**: The preload subsystem (legacy + progressive) accounts for **868 lines** (57% of the file). The app factory and lifespan together are only 261 lines.

### Bare-Except Sites (12 total)

| Line | Function | Context | Sprint |
|------|----------|---------|--------|
| 167 | `_initialize_mutation_invalidator` | Boundary guard (graceful degradation) | S1 - moves with init helpers |
| 229 | `lifespan` | Entity discovery fail-fast | S1 - moves with lifespan |
| 290 | `lifespan` | Cache warming cancel error | S1 - moves with lifespan |
| 301 | `lifespan` | Connection registry shutdown error | S1 - moves with lifespan |
| 498 | `_preload_dataframe_cache` | Index recovery failure | S1 - moves with preload |
| 664 | `_preload_dataframe_cache` | Per-project failure | S1 - moves with preload |
| 675 | `_preload_dataframe_cache` | Top-level failure | S1 - moves with preload |
| 799 | `_do_incremental_catchup` | Catchup failure fallback | S1 - moves with preload |
| 885 | `_do_full_rebuild` | Rebuild failure | S1 - moves with preload |
| 939 | `_invoke_cache_warmer_lambda_from_preload` | Lambda invocation failure | S1 - moves with preload |
| 1295 | `_preload_dataframe_cache_progressive` | Per-project failure | S1 - moves with preload |
| 1358 | `_preload_dataframe_cache_progressive` | Top-level failure | S1 - moves with preload |

**Decision**: These bare-except sites move with their functions during decomposition. They are NOT narrowed in this initiative -- that is I6's scope. Each site is tagged with a `# BROAD-CATCH:` comment if not already present, per the I4 convention.

---

## 2. Extraction Plan

### Target Architecture

After full decomposition (S1 + S2), main.py becomes a thin routing shell:

```
src/autom8_asana/api/
  main.py              (~150 lines - app factory, middleware, routes, entrypoint)
  lifespan.py          (~140 lines - lifespan context manager, startup/shutdown)
  startup.py           (~100 lines - initialization helpers)
  preload/
    __init__.py         (public API: preload_dataframe_cache_progressive)
    legacy.py           (~380 lines - _preload_dataframe_cache, _do_incremental_catchup, _do_full_rebuild)
    progressive.py      (~500 lines - progressive preload with parallel projects)
    constants.py        (~15 lines - PROJECT_CONCURRENCY, HEARTBEAT_INTERVAL_SECONDS, etc.)
```

### Why a `preload/` Subpackage

The preload subsystem is 868 lines with 7 functions, internal constants, and two distinct strategies (legacy + progressive). A flat file would still be 868 lines. A subpackage with `legacy.py` and `progressive.py` gives clean separation: legacy can be deleted entirely when no longer needed, without touching the progressive code.

---

## 3. Sprint 1 Scope: Mechanical Extractions

Sprint 1 extracts all code from main.py into new modules. Every extraction is a pure move-and-reexport pattern with no behavioral changes.

### Extraction 1: `api/startup.py` (Initialization Helpers)

**What moves**:
- `_initialize_dataframe_cache()` (lines 84-113)
- `_register_schema_providers()` (lines 116-128)
- `_initialize_mutation_invalidator()` (lines 131-175)
- `_discover_entity_projects()` (lines 314-331)

**Line count**: ~100 lines

**Import changes in main.py**:
```python
from .startup import (
    _discover_entity_projects,
    _initialize_dataframe_cache,
    _initialize_mutation_invalidator,
    _register_schema_providers,
)
```

**Risk**: LOW. These are standalone functions called only from `lifespan()`. No external consumers import them.

### Extraction 2: `api/lifespan.py` (Lifespan Manager)

**What moves**:
- `lifespan()` async context manager (lines 181-311)

**Dependencies on main.py after extraction**: None -- `lifespan()` calls the startup helpers (extracted in Extraction 1) and the preload function (extracted in Extraction 3). All become cross-module imports within the `api/` package.

**Import changes in main.py**:
```python
from .lifespan import lifespan
```

**Line count**: ~140 lines (including docstring)

**Risk**: LOW. The `lifespan` function is referenced only by `create_app()` in main.py. The conftest patches `autom8_asana.api.main._discover_entity_projects` which would need updating (see Test Impact below).

### Extraction 3: `api/preload/` Subpackage

**What moves to `api/preload/constants.py`**:
- `PROJECT_CONCURRENCY` (line 901)
- `HEARTBEAT_INTERVAL_SECONDS` (line 904)
- `PRELOAD_EXCLUDE_PROJECT_GIDS` (line 909)

**What moves to `api/preload/legacy.py`**:
- `_preload_dataframe_cache()` (lines 333-704)
- `_do_incremental_catchup()` (lines 707-810)
- `_do_full_rebuild()` (lines 813-894)

**What moves to `api/preload/progressive.py`**:
- `_invoke_cache_warmer_lambda_from_preload()` (lines 912-946)
- `_preload_dataframe_cache_progressive()` (lines 949-1391)

**What goes in `api/preload/__init__.py`**:
```python
"""Cache preload subsystem for DataFrame warming at startup."""

from .progressive import _preload_dataframe_cache_progressive

__all__ = ["_preload_dataframe_cache_progressive"]
```

**Line count**: ~870 lines total across subpackage

**Risk**: MEDIUM. The progressive preload imports from the legacy preload as a fallback (line 1137: `await _preload_dataframe_cache(app)`). This becomes a cross-module import within the subpackage. Test files import individual functions from `autom8_asana.api.main` and need updating.

### Extraction 4: Update `create_app()` imports

After extractions 1-3, `create_app()` remains in main.py with updated imports. The `__main__` block stays. The `models.business` side-effect import stays (it must run at module level).

**Post-extraction main.py structure** (~150 lines):
```python
"""FastAPI application factory."""

# Side-effect import for bootstrap
import autom8_asana.models.business  # noqa: F401

from .config import get_settings
from .errors import register_exception_handlers
from .lifespan import lifespan
from .middleware import ...
from .rate_limit import limiter
from .routes import ...

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    ...

if __name__ == "__main__":
    ...
```

---

## 4. Sprint 2 Scope (Wave 4)

Sprint 2 addresses cleanup that depends on S1 being stable in production:

1. **Delete backward-compat shims** (4 files):
   - `cache/factory.py` -- main.py's import at line 147, 1118 updated to `cache.integration.factory`
   - `cache/mutation_invalidator.py` -- main.py's import at line 148 updated to `cache.integration.mutation_invalidator`
   - `cache/schema_providers.py` -- main.py's import at line 126 updated to `cache.integration.schema_providers`
   - `cache/tiered.py` -- used by `lambda_handlers/cache_invalidate.py` (separate read-only zone, out of scope)

   **Note**: `cache/tiered.py` serves `lambda_handlers/`, not main.py. It can only be deleted when lambda_handlers is also updated. Three of the four shims serve main.py and can be deleted after S1.

2. **ProgressiveProjectBuilder factory** (R01): Extract the 7-step instantiation ceremony (lines 1161-1179 in progressive preload) into a factory function in `dataframes/builders/progressive.py`. This eliminates duplication between `_do_incremental_catchup`, `_do_full_rebuild`, and `_preload_dataframe_cache_progressive`.

3. **Delete legacy preload**: Once progressive preload is confirmed stable (no fallback to legacy needed), `api/preload/legacy.py` can be removed entirely.

---

## 5. Dependency Map

### Import Graph (current)

```
api/main.py
  imports from:
    api/config.py             (get_settings)
    api/errors.py             (register_exception_handlers)
    api/middleware.py          (RequestIDMiddleware, RequestLoggingMiddleware, configure_structlog)
    api/rate_limit.py         (limiter)
    api/routes/__init__.py    (12 routers)
    api/routes/health.py      (set_cache_ready - from preload functions)
    cache/factory.py          [SHIM -> cache/integration/factory.py]
    cache/mutation_invalidator.py  [SHIM -> cache/integration/mutation_invalidator.py]
    cache/schema_providers.py [SHIM -> cache/integration/schema_providers.py]
    cache/dataframe/factory.py
    dataframes/persistence.py
    dataframes/storage.py
    dataframes/watermark.py
    dataframes/builders/progressive.py
    dataframes/models/registry.py
    dataframes/resolver.py
    dataframes/section_persistence.py
    services/discovery.py
    services/gid_lookup.py
    services/resolver.py
    auth/bot_pat.py
    config.py (S3LocationConfig, CacheConfig)
    settings.py

  imported by:
    api/__init__.py           (create_app)
    tests/api/conftest.py     (create_app)
    tests/api/test_startup_preload.py (preload functions)
    tests/unit/api/test_preload_lambda_delegation.py (progressive preload)
    tests/unit/api/test_preload_parquet_fallback.py (progressive preload)
    tests/integration/test_entity_resolver_e2e.py (create_app)
```

### Backward-Compat Shim Usage

| Shim File | Consumer in main.py | Consumer Elsewhere | Can Delete in S1? |
|-----------|--------------------|--------------------|-------------------|
| `cache/factory.py` | Lines 147, 1118 | None | YES (update import path) |
| `cache/mutation_invalidator.py` | Line 148 | None | YES (update import path) |
| `cache/schema_providers.py` | Line 126 | None | YES (update import path) |
| `cache/tiered.py` | None | `lambda_handlers/cache_invalidate.py` | NO (lambda_handlers is read-only) |

**Revised plan**: We can delete 3 of 4 shims in S1 by updating imports during the extraction. The `cache/tiered.py` shim stays until lambda_handlers is addressed (I7 or later).

---

## 6. Per-Module Specifications

### 6.1 `api/startup.py`

| Attribute | Value |
|-----------|-------|
| Target file | `src/autom8_asana/api/startup.py` |
| Functions to move | `_initialize_dataframe_cache`, `_register_schema_providers`, `_initialize_mutation_invalidator`, `_discover_entity_projects` |
| Source lines | 84-175, 314-331 |
| Target line count | ~100 |
| Imports needed | `autom8y_log`, `fastapi.FastAPI` |
| Internal imports | Uses lazy imports (inside function bodies) -- these move as-is |
| Public API | All 4 functions (consumed by `lifespan.py`) |
| Tests affected | `conftest.py` patches `_discover_entity_projects` |

### 6.2 `api/lifespan.py`

| Attribute | Value |
|-----------|-------|
| Target file | `src/autom8_asana/api/lifespan.py` |
| Functions to move | `lifespan` |
| Source lines | 181-311 |
| Target line count | ~140 |
| Imports needed | `asyncio`, `collections.abc.AsyncGenerator`, `contextlib.asynccontextmanager`, `autom8y_log`, `fastapi.FastAPI` |
| Internal imports | `.startup` (4 init helpers), `.preload` (progressive preload function), `.config` (get_settings), `.middleware` (configure_structlog) |
| Public API | `lifespan` (consumed by `create_app()`) |
| Tests affected | `conftest.py` patches `_discover_entity_projects` at old path |

### 6.3 `api/preload/__init__.py`

| Attribute | Value |
|-----------|-------|
| Target file | `src/autom8_asana/api/preload/__init__.py` |
| Line count | ~10 |
| Public API | Re-exports `_preload_dataframe_cache_progressive` from `.progressive` |

### 6.4 `api/preload/constants.py`

| Attribute | Value |
|-----------|-------|
| Target file | `src/autom8_asana/api/preload/constants.py` |
| Symbols to move | `PROJECT_CONCURRENCY`, `HEARTBEAT_INTERVAL_SECONDS`, `PRELOAD_EXCLUDE_PROJECT_GIDS` |
| Source lines | 900-909 |
| Target line count | ~15 |

### 6.5 `api/preload/legacy.py`

| Attribute | Value |
|-----------|-------|
| Target file | `src/autom8_asana/api/preload/legacy.py` |
| Functions to move | `_preload_dataframe_cache`, `_do_incremental_catchup`, `_do_full_rebuild` |
| Source lines | 333-894 |
| Target line count | ~370 |
| Tests affected | `test_startup_preload.py` imports all 3 functions from `autom8_asana.api.main` |

### 6.6 `api/preload/progressive.py`

| Attribute | Value |
|-----------|-------|
| Target file | `src/autom8_asana/api/preload/progressive.py` |
| Functions to move | `_invoke_cache_warmer_lambda_from_preload`, `_preload_dataframe_cache_progressive` |
| Source lines | 912-1391 |
| Target line count | ~490 |
| Internal imports | `.constants` (3 constants), `.legacy._preload_dataframe_cache` (fallback) |
| Tests affected | `test_preload_lambda_delegation.py`, `test_preload_parquet_fallback.py` |

### 6.7 `api/main.py` (post-extraction)

| Attribute | Value |
|-----------|-------|
| Target line count | ~150 |
| Remaining content | `create_app()`, `__main__` block, side-effect import, logger |
| Imports from new modules | `.lifespan.lifespan` |

---

## 7. Test Impact and Verification Strategy

### Patch Path Updates

Tests currently patch functions at their old locations. After extraction, patch targets must change:

| Test File | Current Patch Target | New Patch Target |
|-----------|---------------------|------------------|
| `tests/api/conftest.py` | `autom8_asana.api.main._discover_entity_projects` | `autom8_asana.api.startup._discover_entity_projects` |
| `tests/api/test_startup_preload.py` | `autom8_asana.api.main._preload_dataframe_cache` | `autom8_asana.api.preload.legacy._preload_dataframe_cache` |
| `tests/api/test_startup_preload.py` | `autom8_asana.api.main._do_incremental_catchup` | `autom8_asana.api.preload.legacy._do_incremental_catchup` |
| `tests/api/test_startup_preload.py` | `autom8_asana.api.main._do_full_rebuild` | `autom8_asana.api.preload.legacy._do_full_rebuild` |
| `tests/unit/api/test_preload_lambda_delegation.py` | `autom8_asana.api.main.*` | `autom8_asana.api.preload.progressive.*` |
| `tests/unit/api/test_preload_parquet_fallback.py` | `autom8_asana.api.main._preload_dataframe_cache_progressive` | `autom8_asana.api.preload.progressive._preload_dataframe_cache_progressive` |

### Backward-Compatibility Shim for Test Transition

To avoid breaking all tests in a single commit, the extraction commits should:
1. Create the new module with the extracted code
2. In main.py, replace the function body with a re-export:
   ```python
   from .preload.legacy import _preload_dataframe_cache  # noqa: F401 - re-export
   ```
3. In a follow-up commit, update test patch targets and remove re-exports

This two-step approach means any commit can be reverted independently.

### Verification Protocol

For each extraction commit:
1. Run `pytest tests/api/ -x -q --timeout=60` -- all API tests must pass
2. Run `pytest tests/unit/api/ -x -q --timeout=60` -- all unit API tests must pass
3. Run `python -c "from autom8_asana.api import create_app; print('OK')"` -- import succeeds
4. Verify main.py line count is decreasing toward target

**Final verification**:
- Full test suite: `.venv/bin/pytest tests/ -x -q --timeout=60`
- Pre-existing failures excluded: `test_adversarial_pacing.py`, `test_paced_fetch.py`, `test_parallel_fetch.py::test_cache_errors_logged_as_warnings`

---

## 8. Success Criteria

| Criterion | Target |
|-----------|--------|
| main.py line count | Under 200 lines (from 1520) |
| New modules created | 6 files (startup.py, lifespan.py, preload/__init__.py, preload/constants.py, preload/legacy.py, preload/progressive.py) |
| Backward-compat shims deleted | 3 of 4 (factory, mutation_invalidator, schema_providers) |
| Test regressions | Zero |
| Behavioral changes | Zero (pure structural refactor) |
| Import path `autom8_asana.api.create_app` | Still works (api/__init__.py unchanged) |
| Bare-except sites | Preserved as-is (tagged for I6) |

---

## 9. Commit Plan (Sprint 1)

| # | Commit | What | Impact |
|---|--------|------|--------|
| 1 | Extract `api/startup.py` | Move 4 init helpers; add re-exports in main.py | main.py -100 lines |
| 2 | Extract `api/preload/` subpackage | Move legacy + progressive preload; add re-exports in main.py | main.py -870 lines |
| 3 | Extract `api/lifespan.py` | Move lifespan manager; add re-exports in main.py | main.py -140 lines |
| 4 | Update test patch targets | Change all test patch paths to new module locations; remove re-exports from main.py | main.py reaches ~150 lines |
| 5 | Delete 3 backward-compat shims | Update imports in startup.py to canonical paths; delete shim files | -3 files, import hygiene |

---

## ADR-I5-001: Preload as Subpackage vs Flat Module

**Status**: ACCEPTED

**Context**: The preload subsystem is 868 lines with two strategies (legacy + progressive), shared constants, and the progressive strategy depends on the legacy strategy as a fallback. We considered three options:
1. Single flat file `api/preload.py` (868 lines)
2. Subpackage `api/preload/` with legacy.py and progressive.py
3. Move preload entirely outside api/ into a top-level `preload/` package

**Decision**: Option 2 -- subpackage within api/.

**Rationale**:
- A flat 868-line file just moves the problem without solving it
- The legacy strategy is a deletion candidate once progressive is stable; separate files make this a clean operation
- Keeping preload within api/ reflects its role: it is startup behavior tightly coupled to the FastAPI app lifecycle
- Constants are shared between strategies and deserve their own tiny module

**Consequences**:
- Slightly deeper import paths (`api.preload.progressive`)
- Clear deletion path for legacy code
- Each strategy can be tested in isolation

---

## ADR-I5-002: Re-Export Shims During Extraction

**Status**: ACCEPTED

**Context**: 8 test files import private functions from `autom8_asana.api.main`. Moving those functions changes the patch target, breaking tests. We could either update all tests atomically or use temporary re-exports.

**Decision**: Use temporary re-exports in main.py during extraction, then remove them in a dedicated test-update commit.

**Rationale**:
- Each extraction commit is independently revertible
- Test failures during extraction would create noise and slow progress
- The re-export pattern is already used by the backward-compat shims (proven approach)
- Re-exports are explicitly temporary and removed in the same sprint

**Consequences**:
- Intermediate commits have re-exports in main.py (slightly inflated line count)
- Final commit removes re-exports and updates tests (clean end state)
- Git bisect works correctly across all commits

---

## ADR-I5-003: Delete 3 Shims in S1, Keep 1 for Lambda

**Status**: ACCEPTED

**Context**: Four backward-compat shims exist in cache/ because main.py (previously read-only) imported from pre-reorganization paths. Now that main.py is being decomposed, three shims can be eliminated by updating imports. The fourth (`cache/tiered.py`) serves `lambda_handlers/cache_invalidate.py`, which is a separate read-only zone.

**Decision**: Delete `cache/factory.py`, `cache/mutation_invalidator.py`, and `cache/schema_providers.py` in Sprint 1. Keep `cache/tiered.py` until lambda_handlers is addressed.

**Rationale**:
- Each shim is a wildcard re-export (`from ... import *`) which obscures the dependency graph
- Three shims serve only main.py; updating imports during extraction is zero additional risk
- The fourth shim serves a different read-only zone; coupling its deletion to this initiative adds unnecessary scope
- Deleting 3 of 4 shims is a meaningful cleanup with bounded risk

**Consequences**:
- 3 fewer shim files in cache/
- Import graph is cleaner (direct paths instead of indirection)
- `cache/tiered.py` remains as a documented exception until I7

---

## Artifact Attestation

| Artifact | Absolute Path | Verified via Read |
|----------|--------------|-------------------|
| TDD-I5 (this document) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/TDD-I5-api-main-decomposition.md` | Written by architect |
| Source: api/main.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | YES (1520 lines) |
| Source: api/__init__.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/__init__.py` | YES |
| Source: api/dependencies.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | YES |
| Source: tests/api/conftest.py | `/Users/tomtenuta/Code/autom8_asana/tests/api/conftest.py` | YES |
| Source: tests/api/test_startup_preload.py | `/Users/tomtenuta/Code/autom8_asana/tests/api/test_startup_preload.py` | YES |
| Shim: cache/factory.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/factory.py` | YES |
| Shim: cache/mutation_invalidator.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/mutation_invalidator.py` | YES |
| Shim: cache/schema_providers.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/schema_providers.py` | YES |
| Shim: cache/tiered.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py` | YES |
| Roadmap | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/deferred-work-roadmap.md` | YES |
