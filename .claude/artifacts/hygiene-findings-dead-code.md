# HYG-001: Dead Code & Unused Import Findings

**Scan Date**: 2026-02-04
**Scope**: `src/autom8_asana/` (348 Python files), `tests/` (test suite)
**Scanned By**: Code Smeller (code-smeller agent)

---

## Executive Summary

| Category | Critical | Moderate | Minor | Total |
|----------|----------|----------|-------|-------|
| duplicate-file | 0 | 4 | 27 | 31 |
| orphaned-module | 0 | 5 | 1 | 6 |
| unused-import | 0 | 0 | 66 | 66 |
| unreachable-function | 0 | 0 | 0 | 0 |
| dead-branch | 0 | 0 | 0 | 0 |
| commented-code | 0 | 0 | 0 | 0 |
| **Total** | **0** | **9** | **94** | **103** |

**Blast Radius**: ~31 shim files (341 lines), 5 unwired service/infrastructure modules, 66 unused test imports.

**Key Insight**: The codebase is mid-reorganization. A large cache module refactoring moved 27 files into subpackages (`models/`, `policies/`, `providers/`, `integration/`) and left backward-compatibility shims at the old paths. Additionally, 4 new shim files were created for new modules (`freshness_stamp`, `freshness_policy`, `mutation_event`, `mutation_invalidator`). Five new modules (`services/entity_service.py`, `services/task_service.py`, `services/section_service.py`, `dataframes/storage.py`, `cache/connections/`) have tests but are not wired into production code.

---

## Findings

### Duplicate Files (Backward-Compatibility Shims)

All shim files follow the same pattern: a 10-11 line `importlib.import_module()` + `sys.modules` redirect to the canonical new location. They exist to preserve old import paths for callers and `mock.patch()` targets.

#### Shims Still Referenced from Production Code (keep for now, migrate callers)

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| DC-001 | `src/autom8_asana/cache/entry.py` | 1 | duplicate-file | minor | Shim to `cache/models/entry.py`. 17 production refs via old path. Highest-traffic shim. |
| DC-002 | `src/autom8_asana/cache/unified.py` | 1 | duplicate-file | minor | Shim to `cache/providers/unified.py`. 6 production refs. |
| DC-003 | `src/autom8_asana/cache/mutation_invalidator.py` | 1 | duplicate-file | minor | Shim to `cache/integration/mutation_invalidator.py`. 5 production refs. |
| DC-004 | `src/autom8_asana/cache/freshness.py` | 1 | duplicate-file | minor | Shim to `cache/models/freshness.py`. 5 production refs. |
| DC-005 | `src/autom8_asana/cache/metrics.py` | 1 | duplicate-file | minor | Shim to `cache/models/metrics.py`. 5 production refs. |
| DC-006 | `src/autom8_asana/cache/mutation_event.py` | 1 | duplicate-file | minor | Shim to `cache/models/mutation_event.py`. 4 production refs. |
| DC-007 | `src/autom8_asana/cache/factory.py` | 1 | duplicate-file | minor | Shim to `cache/integration/factory.py`. 4 production refs. |
| DC-008 | `src/autom8_asana/cache/settings.py` | 1 | duplicate-file | minor | Shim to `cache/models/settings.py`. 4 production refs. |
| DC-009 | `src/autom8_asana/cache/dataframe_cache.py` | 1 | duplicate-file | minor | Shim to `cache/integration/dataframe_cache.py`. 2 production refs. |
| DC-010 | `src/autom8_asana/cache/dataframes.py` | 1 | duplicate-file | minor | Shim to `cache/integration/dataframes.py`. 2 production refs. |
| DC-011 | `src/autom8_asana/cache/versioning.py` | 1 | duplicate-file | minor | Shim to `cache/models/versioning.py`. 2 production refs. |
| DC-012 | `src/autom8_asana/cache/completeness.py` | 1 | duplicate-file | minor | Shim to `cache/models/completeness.py`. 2 production refs. |
| DC-013 | `src/autom8_asana/cache/freshness_coordinator.py` | 1 | duplicate-file | minor | Shim to `cache/integration/freshness_coordinator.py`. 1 production ref. |
| DC-014 | `src/autom8_asana/cache/schema_providers.py` | 1 | duplicate-file | minor | Shim to `cache/integration/schema_providers.py`. 1 production ref. |
| DC-015 | `src/autom8_asana/cache/stories.py` | 1 | duplicate-file | minor | Shim to `cache/integration/stories.py`. 1 production ref. |
| DC-016 | `src/autom8_asana/cache/tiered.py` | 1 | duplicate-file | minor | Shim to `cache/providers/tiered.py`. 1 production ref. |
| DC-017 | `src/autom8_asana/cache/staleness_settings.py` | 1 | duplicate-file | minor | Shim to `cache/models/staleness_settings.py`. 1 production ref. |
| DC-018 | `src/autom8_asana/cache/errors.py` | 1 | duplicate-file | minor | Shim to `cache/models/errors.py`. 1 production ref. |

#### Shims Referenced Only from Tests (safe to remove after test migration)

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| DC-019 | `src/autom8_asana/cache/freshness_stamp.py` | 1 | duplicate-file | moderate | Shim to `cache/models/freshness_stamp.py`. 0 production refs, 8 test refs. |
| DC-020 | `src/autom8_asana/cache/staleness.py` | 1 | duplicate-file | moderate | Shim to `cache/policies/staleness.py`. 0 production refs, 4 test refs. |
| DC-021 | `src/autom8_asana/cache/hierarchy.py` | 1 | duplicate-file | moderate | Shim to `cache/policies/hierarchy.py`. 0 production refs, 5 test refs. |
| DC-022 | `src/autom8_asana/cache/batch.py` | 1 | duplicate-file | minor | Shim to `cache/integration/batch.py`. 0 production refs, 4 test refs. |
| DC-023 | `src/autom8_asana/cache/coalescer.py` | 1 | duplicate-file | minor | Shim to `cache/policies/coalescer.py`. 0 production refs, 3 test refs. |
| DC-024 | `src/autom8_asana/cache/lightweight_checker.py` | 1 | duplicate-file | minor | Shim to `cache/policies/lightweight_checker.py`. 0 production refs, 3 test refs. |
| DC-025 | `src/autom8_asana/cache/hierarchy_warmer.py` | 1 | duplicate-file | minor | Shim to `cache/integration/hierarchy_warmer.py`. 0 production refs, 3 test refs. |
| DC-026 | `src/autom8_asana/cache/staleness_coordinator.py` | 1 | duplicate-file | minor | Shim to `cache/integration/staleness_coordinator.py`. 0 production refs, 3 test refs. |
| DC-027 | `src/autom8_asana/cache/events.py` | 1 | duplicate-file | minor | Shim to `cache/models/events.py`. 0 production refs, 2 test refs. |
| DC-028 | `src/autom8_asana/cache/freshness_policy.py` | 1 | duplicate-file | minor | Shim to `cache/policies/freshness_policy.py`. 0 production refs, 2 test refs. |
| DC-029 | `src/autom8_asana/cache/autom8_adapter.py` | 1 | duplicate-file | minor | Shim to `cache/integration/autom8_adapter.py`. 0 production refs, 1 test ref. |
| DC-030 | `src/autom8_asana/cache/loader.py` | 1 | duplicate-file | minor | Shim to `cache/integration/loader.py`. 0 production refs, 1 test ref. |

#### Completely Unreferenced Shim

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| DC-031 | `src/autom8_asana/cache/upgrader.py` | 1 | duplicate-file | moderate | Shim to `cache/integration/upgrader.py`. **0 production refs, 0 test refs.** `cache/__init__.py` imports directly from `cache/integration/upgrader`. This file is dead. |

---

### Orphaned Modules (Not Wired into Production)

These modules exist with tests but are not imported by any production code outside their own package. They appear to be pre-built for a future integration.

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| OM-001 | `src/autom8_asana/services/entity_service.py` | 1 | orphaned-module | moderate | `EntityService` class. Only imported by `tests/unit/services/test_entity_service.py` and peer service files. Not wired into API routes or app factory. |
| OM-002 | `src/autom8_asana/services/task_service.py` | 1 | orphaned-module | moderate | `TaskService` class. Only imported by its test file. Not wired into API routes. |
| OM-003 | `src/autom8_asana/services/section_service.py` | 1 | orphaned-module | moderate | `SectionService` class. Only imported by its test file. Not wired into API routes. |
| OM-004 | `src/autom8_asana/services/entity_context.py` | 1 | orphaned-module | minor | `EntityContext` class. Only imported by `entity_service.py` and its test. |
| OM-005 | `src/autom8_asana/services/errors.py` | 1 | orphaned-module | moderate | `InvalidParameterError` etc. Only imported by peer service files and tests. |
| OM-006 | `src/autom8_asana/dataframes/storage.py` | 1 | orphaned-module | moderate | Storage abstraction. Only imported by `tests/unit/dataframes/test_storage.py`. Not used by any production code. |

**Related**: The `cache/connections/` package (redis.py, s3.py, registry.py) is also only imported from test code, not wired into production. However, it is internally consistent and may be awaiting integration.

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| OM-007 | `src/autom8_asana/cache/connections/__init__.py` | 1 | orphaned-module | moderate | Entire `cache/connections/` package (4 files). Only imported from `tests/unit/cache/connections/`. Not wired into any production code (cache backends still manage their own connections). |

---

### Unused Imports in Test Files

66 unused imports across test files. These are imports that appear only once in the file (on the import line itself), suggesting they are not used in any test function.

**Top offenders by file** (files with 3+ unused imports):

| ID | File | Line(s) | Category | Severity | Description |
|----|------|---------|----------|----------|-------------|
| UI-001 | `tests/unit/cache/test_reorg_imports.py` | 16,18,22-24,75 | unused-import | minor | 7 unused imports (`TieredConfig`, `OverflowSettings`, `TTLSettings`, `check_batch_staleness`, `load_task_entries`, `load_task_entry`, etc). File appears to test that imports resolve without error -- names are imported but never called. |
| UI-002 | `tests/unit/query/test_adversarial_aggregate.py` | 19,23,26,32,41 | unused-import | minor | 5 unused: `MagicMock`, `TypeAdapter`, `AGG_COMPATIBILITY`, `PredicateCompiler`, `PredicateNode`. |
| UI-003 | `tests/unit/query/test_guards.py` | 19 | unused-import | minor | 3 unused: `Comparison`, `NotGroup`, `Op`, `OrGroup`. |
| UI-004 | `tests/unit/query/test_engine.py` | 21 | unused-import | minor | 4 unused: `AggFunction`, `AggSpec`, `Comparison`, `Op`. |
| UI-005 | `tests/unit/query/test_compiler.py` | 5,22 | unused-import | minor | 3 unused: `timezone`, `AndGroup`, `NotGroup`, `OrGroup`. |
| UI-006 | `tests/qa/test_poc_query_evaluation.py` | 13,43,49 | unused-import | minor | 3 unused: `timezone`, `ENTITY_RELATIONSHIPS`, `execute_join`. |

**Remaining**: 41 additional unused imports scattered across 35 test files (1-2 per file). Full list available in scan data.

---

### Unreachable Functions

No truly unreachable functions found. All standalone functions are either:
- FastAPI route handlers (registered via `@router.get/post/...` decorators)
- Entrypoint functions called by `__main__` block
- Library/SDK public API functions with tests

### Dead Branches

No `if False:`, `if True:`, or constant-guarded dead branches found in production code.

### Commented-Out Code

No commented-out function definitions, class definitions, or import blocks found. Two placeholder comments exist in `metrics/definitions/__init__.py` for future metric modules (lines 14-15) -- these are intentional planning comments, not dead code.

---

## Priority Ranking (ROI)

| Priority | ID(s) | Action | Effort | Impact |
|----------|-------|--------|--------|--------|
| 1 | DC-031 | Delete `cache/upgrader.py` shim -- completely unreferenced | Trivial | Clean |
| 2 | DC-019 to DC-030 | Migrate 12 test files to new import paths, then delete 12 shims | Low | Eliminates 12 shim files |
| 3 | DC-001 to DC-018 | Migrate ~50 production import sites to new paths, then delete 18 shims | Medium | Eliminates 18 shim files, completes reorg |
| 4 | OM-001 to OM-007 | Evaluate: wire into production or explicitly mark as pending-integration | Low | Clarifies intent |
| 5 | UI-001 to UI-006 | Clean up 66 unused test imports | Low | Cleaner test code, faster linting |

---

## Notes for Architect Enforcer

1. **Shim Migration Strategy**: The 31 shim files are a natural consequence of the cache module reorganization. The recommended approach is: (a) update all import sites to use canonical paths, (b) delete shims in a single follow-up PR. The shims use `sys.modules` aliasing which works but adds import-time overhead and confuses IDE navigation.

2. **Unwired Service Layer**: `services/entity_service.py`, `task_service.py`, and `section_service.py` appear to be a service-layer extraction that was built and tested but never integrated into the API routes. The API routes still contain inline business logic. This is an architectural decision point: either wire them in or remove them.

3. **Unwired Infrastructure**: `cache/connections/` and `dataframes/storage.py` are infrastructure modules with tests but no production consumers. Similar decision needed.

4. **No Critical Issues**: No dead branches, no truly unreachable functions, no commented-out code. The codebase is well-maintained aside from the in-progress reorganization artifacts.

---

## Verification Attestation

| Artifact | Verified | Method |
|----------|----------|--------|
| Shim file existence (31 files) | Yes | `diff -q` confirmed both old and new paths exist for all pairs |
| Shim content pattern | Yes | Read tool confirmed `importlib.import_module` + `sys.modules` pattern |
| Import reference counts | Yes | `grep -rn` across `src/` and `tests/` for each module path |
| Orphan module status | Yes | `grep -rl` confirmed no production imports outside own package |
| Unused test imports | Yes | AST-based scan with `ast.parse()` + occurrence counting |
| Dead branch scan | Yes | Regex scan for `if False:`, `if True:`, `if 0:`, `if 1:` patterns |
| Commented-out code scan | Yes | Regex scan for `^# def`, `^# class`, `^# import` patterns |
