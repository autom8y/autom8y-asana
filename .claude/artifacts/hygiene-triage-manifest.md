# Hygiene Triage Manifest

**Date**: 2026-02-04
**Session**: session-20260204-170818-5363b6da
**Phase**: HYG-006 (Architect Enforcer triage)
**Input Scans**: HYG-001 (dead code, 103), HYG-002 (SOLID/DRY, 22), HYG-003 (error handling, 134), HYG-004 (doc debt, 82), HYG-005 (architecture, 18)
**Governing Ruleset**: `hygiene-triage-rules.yaml`

---

## 1. Executive Summary

### Finding Totals by Source Scan

| Source Scan | Total Findings | Fix-Now | Refactor | Defer |
|-------------|---------------|---------|----------|-------|
| HYG-001: Dead Code | 103 | 97 | 1 | 5 |
| HYG-002: SOLID/DRY | 22 | 8 | 8 | 6 |
| HYG-003: Error Handling | 134 | 15 | 2 | 117 |
| HYG-004: Doc Debt | 82 | 12 | 0 | 70 |
| HYG-005: Architecture | 18 | 6 | 3 | 9 |
| **Total** | **359** | **138** | **14** | **207** |

Note: Some findings are cross-referenced between scans. The totals above count each finding ID once in its source scan. See Section 6 for cross-references.

### Classification Breakdown

| Classification | Count | % |
|---------------|-------|---|
| **fix-now** | 138 | 38% |
| **refactor** | 14 | 4% |
| **defer** | 207 | 58% |

### Estimated Commit Count for Fix-Now Batches

**12 commits** organized into 12 logical batch groups (see Section 2).

---

## 2. Fix-Now Batches

### Batch Summary

| Batch ID | Batch Name | Finding IDs | File Count | Description |
|----------|-----------|-------------|------------|-------------|
| B01 | Force-fix: critical runtime & observability | DOC-001, SW-001, SW-002 | 3 | Surgical fixes to force-fix items (read-only zone overrides) |
| B02 | Delete unreferenced shim | DC-031 | 1 | Remove completely dead `cache/upgrader.py` shim |
| B03 | Migrate test imports from shims, delete test-only shims | DC-019 to DC-030 | ~20 | Update ~36 test import sites to canonical paths, then delete 12 shim files |
| B04 | Migrate production imports from shims (models/) | DC-001, DC-004, DC-005, DC-008, DC-011, DC-012, DC-018, HYG-005-04 (partial), HYG-005-09, HYG-005-10 | ~25 | Update production imports for cache/models/ subpackage shims |
| B05 | Migrate production imports from shims (integration/) | DC-003, DC-006, DC-007, DC-009, DC-010, DC-013, DC-014, DC-015, HYG-005-04 (partial), HYG-005-05 | ~20 | Update production imports for cache/integration/ subpackage shims |
| B06 | Migrate production imports from shims (policies/, providers/) | DC-002, DC-016, DC-017, HYG-005-04 (partial), HYG-005-16, HYG-005-17, HYG-005-18 | ~10 | Update production imports for cache/policies/ and cache/providers/ shims |
| B07 | Delete all production shims after migration | DC-001 to DC-018 (delete phase) | 18 | Remove all 18 production-referenced shim files after B04-B06 complete |
| B08 | Clean unused test imports | UI-001 to UI-006 + 41 additional | ~41 | Remove 66 unused imports across test files |
| B09 | Fix swallowed exceptions (non-read-only) | SW-003 to SW-010, SW-012, SW-013, IH-001 | ~10 | Add logging to 13 silent exception sites |
| B10 | Fix logging inconsistency in new modules | HYG-005-14 | 4 | Replace stdlib logging with autom8y_log.get_logger() |
| B11 | Extract magic numbers to named constants | DOC-079, DOC-080, DOC-081, DOC-082, DOC-085 | 5 | Replace inline TTL/config magic numbers with named constants or config references |
| B12 | Add docstrings to public SDK methods (sections client) | DOC-008 to DOC-019 | 1 | Add docstrings to 12 public methods in clients/sections.py |

---

### B01: Force-Fix -- Critical Runtime & Observability

**Commit message**: `fix: resolve critical runtime bug and silent exception gaps`

These items override read-only zone restrictions per the triage ruleset.

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DOC-001 | `src/autom8_asana/lambda_handlers/cache_invalidate.py` | 105 | todo-marker | critical | `TieredCacheProvider()` called without required `hot_tier` argument; `type: ignore[call-arg]` suppresses the error. Runtime failure if Lambda invoked. | Surgical fix: add required `hot_tier` argument to the constructor call. Minimal change in read-only zone. |
| SW-001 | `src/autom8_asana/models/business/detection/facade.py` | 167 | swallowed-exception | critical | `except Exception: pass` with no logging at all. Cache storage failure completely invisible. | Add `logger.warning("...", exc_info=True)` before `pass`. Change `pass` to logged degradation. Minimal change in read-only zone. |
| SW-002 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 309 | swallowed-exception | critical | `except Exception: pass` on hard-invalidation fallback. If both soft and hard invalidation fail, there is zero trace. | Add `logger.warning("...", exc_info=True)` before `pass`. Not in a read-only zone despite being force-fix. |

---

### B02: Delete Unreferenced Shim

**Commit message**: `chore: remove dead cache/upgrader.py shim (0 refs)`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DC-031 | `src/autom8_asana/cache/upgrader.py` | 1 | duplicate-file | moderate | Shim to `cache/integration/upgrader.py`. Zero production refs, zero test refs. `cache/__init__.py` imports directly from canonical path. | Delete file. |

---

### B03: Migrate Test Imports, Delete Test-Only Shims

**Commit message**: `chore: migrate test imports to canonical cache paths, remove 12 shims`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DC-019 | `src/autom8_asana/cache/freshness_stamp.py` | 1 | duplicate-file | moderate | Shim; 0 prod refs, 8 test refs | Update 8 test import sites to `cache.models.freshness_stamp`, then delete shim |
| DC-020 | `src/autom8_asana/cache/staleness.py` | 1 | duplicate-file | moderate | Shim; 0 prod refs, 4 test refs | Update 4 test sites to `cache.policies.staleness`, delete shim |
| DC-021 | `src/autom8_asana/cache/hierarchy.py` | 1 | duplicate-file | moderate | Shim; 0 prod refs, 5 test refs | Update 5 test sites to `cache.policies.hierarchy`, delete shim |
| DC-022 | `src/autom8_asana/cache/batch.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 4 test refs | Update 4 test sites to `cache.integration.batch`, delete shim |
| DC-023 | `src/autom8_asana/cache/coalescer.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 3 test refs | Update 3 test sites, delete shim |
| DC-024 | `src/autom8_asana/cache/lightweight_checker.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 3 test refs | Update 3 test sites, delete shim |
| DC-025 | `src/autom8_asana/cache/hierarchy_warmer.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 3 test refs | Update 3 test sites, delete shim |
| DC-026 | `src/autom8_asana/cache/staleness_coordinator.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 3 test refs | Update 3 test sites, delete shim |
| DC-027 | `src/autom8_asana/cache/events.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 2 test refs | Update 2 test sites, delete shim |
| DC-028 | `src/autom8_asana/cache/freshness_policy.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 2 test refs | Update 2 test sites, delete shim |
| DC-029 | `src/autom8_asana/cache/autom8_adapter.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 1 test ref | Update 1 test site, delete shim |
| DC-030 | `src/autom8_asana/cache/loader.py` | 1 | duplicate-file | minor | Shim; 0 prod refs, 1 test ref | Update 1 test site, delete shim |

---

### B04: Migrate Production Imports -- cache/models/ Shims

**Commit message**: `refactor: migrate production imports to canonical cache.models paths`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DC-001 | `src/autom8_asana/cache/entry.py` | 1 | duplicate-file | minor | Shim to `cache/models/entry.py`. 17 production refs. Highest-traffic shim. | Update all 17 import sites to `cache.models.entry` |
| DC-004 | `src/autom8_asana/cache/freshness.py` | 1 | duplicate-file | minor | Shim to `cache/models/freshness.py`. 5 production refs. | Update 5 import sites |
| DC-005 | `src/autom8_asana/cache/metrics.py` | 1 | duplicate-file | minor | Shim to `cache/models/metrics.py`. 5 production refs. | Update 5 import sites |
| DC-008 | `src/autom8_asana/cache/settings.py` | 1 | duplicate-file | minor | Shim to `cache/models/settings.py`. 4 production refs. | Update 4 import sites |
| DC-011 | `src/autom8_asana/cache/versioning.py` | 1 | duplicate-file | minor | Shim to `cache/models/versioning.py`. 2 production refs. | Update 2 import sites |
| DC-012 | `src/autom8_asana/cache/completeness.py` | 1 | duplicate-file | minor | Shim to `cache/models/completeness.py`. 2 production refs. | Update 2 import sites |
| DC-018 | `src/autom8_asana/cache/errors.py` | 1 | duplicate-file | minor | Shim to `cache/models/errors.py`. 1 production ref. | Update 1 import site |
| HYG-005-09 | `src/autom8_asana/protocols/cache.py` | 9 | inconsistent-pattern | minor | Protocol TYPE_CHECKING imports use old shim paths for entry, freshness, metrics. | Update to canonical cache.models.* paths |
| HYG-005-10 | `src/autom8_asana/_defaults/cache.py` | various | inconsistent-pattern | minor | NullCacheProvider uses old shim paths for entry, freshness, metrics, versioning. | Update to canonical cache.models.* paths |

**Note**: Import sites in `api/main.py` are in a read-only zone. Those specific imports will NOT be migrated; `api/main.py` will continue using shims until its future refactoring. The shim files themselves remain after B04 and are only deleted in B07 once ALL non-read-only callers are migrated. The `api/main.py` imports via `cache/__init__.py` re-exports will continue to work after shim deletion because `cache/__init__.py` already imports from canonical paths.

---

### B05: Migrate Production Imports -- cache/integration/ Shims

**Commit message**: `refactor: migrate production imports to canonical cache.integration paths`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DC-003 | `src/autom8_asana/cache/mutation_invalidator.py` | 1 | duplicate-file | minor | Shim to `cache/integration/mutation_invalidator.py`. 5 production refs. | Update 5 import sites (excluding api/main.py read-only zone) |
| DC-006 | `src/autom8_asana/cache/mutation_event.py` | 1 | duplicate-file | minor | Shim to `cache/models/mutation_event.py`. 4 production refs. | Update 4 import sites |
| DC-007 | `src/autom8_asana/cache/factory.py` | 1 | duplicate-file | minor | Shim to `cache/integration/factory.py`. 4 production refs. | Update non-read-only import sites |
| DC-009 | `src/autom8_asana/cache/dataframe_cache.py` | 1 | duplicate-file | minor | Shim to `cache/integration/dataframe_cache.py`. 2 production refs. | Update 2 import sites |
| DC-010 | `src/autom8_asana/cache/dataframes.py` | 1 | duplicate-file | minor | Shim to `cache/integration/dataframes.py`. 2 production refs. | Update 2 import sites |
| DC-013 | `src/autom8_asana/cache/freshness_coordinator.py` | 1 | duplicate-file | minor | Shim to `cache/integration/freshness_coordinator.py`. 1 production ref. | Update 1 import site |
| DC-014 | `src/autom8_asana/cache/schema_providers.py` | 1 | duplicate-file | minor | Shim to `cache/integration/schema_providers.py`. 1 production ref. | Update 1 import site (may be in api/main.py -- skip if read-only) |
| DC-015 | `src/autom8_asana/cache/stories.py` | 1 | duplicate-file | minor | Shim to `cache/integration/stories.py`. 1 production ref. | Update 1 import site |
| HYG-005-05 | `src/autom8_asana/api/routes/tasks.py`, `sections.py`, `dependencies.py` | various | inconsistent-pattern | moderate | API layer imports MutationEvent and MutationInvalidator from shim paths. | Update to canonical paths (api/main.py excluded as read-only) |

---

### B06: Migrate Production Imports -- cache/policies/ and cache/providers/ Shims

**Commit message**: `refactor: migrate production imports to canonical cache.policies and cache.providers paths`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DC-002 | `src/autom8_asana/cache/unified.py` | 1 | duplicate-file | minor | Shim to `cache/providers/unified.py`. 6 production refs. | Update non-read-only import sites |
| DC-016 | `src/autom8_asana/cache/tiered.py` | 1 | duplicate-file | minor | Shim to `cache/providers/tiered.py`. 1 production ref. | Update 1 import site |
| DC-017 | `src/autom8_asana/cache/staleness_settings.py` | 1 | duplicate-file | minor | Shim to `cache/models/staleness_settings.py`. 1 production ref. | Update 1 import site |
| HYG-005-16 | `src/autom8_asana/api/routes/dataframes.py` | 42 | layer-violation | minor | Route imports from `cache.unified` (shim). | Update to `cache.providers.unified` |
| HYG-005-17 | `src/autom8_asana/api/main.py` | 126,147 | layer-violation | minor | **SKIP**: api/main.py is read-only. Excluded from migration. | No action (read-only zone) |
| HYG-005-18 | `src/autom8_asana/dataframes/views/dataframe_view.py` | 440 | layer-violation | minor | View imports from deprecated shim paths. | Update to canonical paths |

---

### B07: Delete All Production Shims After Migration

**Commit message**: `chore: remove 18 backward-compatibility shim files (all callers migrated)`

This batch executes AFTER B04-B06 are verified. Delete all 18 shim files (DC-001 through DC-018). The janitor must verify that `cache/__init__.py` re-exports cover any remaining callers (e.g., `api/main.py` in read-only zone) before deletion.

| Finding ID | File | Category | Fix Approach |
|-----------|------|----------|-------------|
| DC-001 | `src/autom8_asana/cache/entry.py` | duplicate-file | Delete after B04 |
| DC-002 | `src/autom8_asana/cache/unified.py` | duplicate-file | Delete after B06 |
| DC-003 | `src/autom8_asana/cache/mutation_invalidator.py` | duplicate-file | Delete after B05 |
| DC-004 | `src/autom8_asana/cache/freshness.py` | duplicate-file | Delete after B04 |
| DC-005 | `src/autom8_asana/cache/metrics.py` | duplicate-file | Delete after B04 |
| DC-006 | `src/autom8_asana/cache/mutation_event.py` | duplicate-file | Delete after B05 |
| DC-007 | `src/autom8_asana/cache/factory.py` | duplicate-file | Delete after B05 |
| DC-008 | `src/autom8_asana/cache/settings.py` | duplicate-file | Delete after B04 |
| DC-009 | `src/autom8_asana/cache/dataframe_cache.py` | duplicate-file | Delete after B05 |
| DC-010 | `src/autom8_asana/cache/dataframes.py` | duplicate-file | Delete after B05 |
| DC-011 | `src/autom8_asana/cache/versioning.py` | duplicate-file | Delete after B04 |
| DC-012 | `src/autom8_asana/cache/completeness.py` | duplicate-file | Delete after B04 |
| DC-013 | `src/autom8_asana/cache/freshness_coordinator.py` | duplicate-file | Delete after B05 |
| DC-014 | `src/autom8_asana/cache/schema_providers.py` | duplicate-file | Delete after B05 |
| DC-015 | `src/autom8_asana/cache/stories.py` | duplicate-file | Delete after B05 |
| DC-016 | `src/autom8_asana/cache/tiered.py` | duplicate-file | Delete after B06 |
| DC-017 | `src/autom8_asana/cache/staleness_settings.py` | duplicate-file | Delete after B06 |
| DC-018 | `src/autom8_asana/cache/errors.py` | duplicate-file | Delete after B04 |

**Pre-deletion verification**: The janitor MUST confirm that `cache/__init__.py` exports all symbols that `api/main.py` (read-only zone) imports. If `api/main.py` imports a symbol from a shim path that is NOT re-exported by `cache/__init__.py`, the janitor must add the re-export to `cache/__init__.py` before deleting the shim.

---

### B08: Clean Unused Test Imports

**Commit message**: `chore: remove 66 unused imports across test files`

| Finding ID | File | Line(s) | Category | Severity | Description | Fix Approach |
|-----------|------|---------|----------|----------|-------------|-------------|
| UI-001 | `tests/unit/cache/test_reorg_imports.py` | 16,18,22-24,75 | unused-import | minor | 7 unused imports. File tests import resolution -- names imported but never called. | Remove unused imports. If entire file becomes empty assertions, evaluate whether file itself is now dead (it may be testing that imports resolve, in which case keep the imports but USE them in assertions). |
| UI-002 | `tests/unit/query/test_adversarial_aggregate.py` | 19,23,26,32,41 | unused-import | minor | 5 unused imports. | Remove unused imports |
| UI-003 | `tests/unit/query/test_guards.py` | 19 | unused-import | minor | 3 unused. | Remove |
| UI-004 | `tests/unit/query/test_engine.py` | 21 | unused-import | minor | 4 unused. | Remove |
| UI-005 | `tests/unit/query/test_compiler.py` | 5,22 | unused-import | minor | 3 unused. | Remove |
| UI-006 | `tests/qa/test_poc_query_evaluation.py` | 13,43,49 | unused-import | minor | 3 unused. | Remove |
| UI-007+ | 35 additional test files | various | unused-import | minor | 41 additional unused imports (1-2 per file). | Remove all. Mechanical cleanup. |

**Special case: UI-001** (`test_reorg_imports.py`). This file may exist solely to verify that import paths resolve. If so, the "unused" imports are the test itself. The janitor should inspect the file: if it contains only import statements and no assertions, convert it to explicit `assert` statements that verify imports rather than bare import lines. If it has assertions already, just remove truly unused ones.

---

### B09: Fix Swallowed Exceptions (Non-Read-Only)

**Commit message**: `fix: add logging to 13 silently swallowed exceptions`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| SW-003 | `src/autom8_asana/cache/models/metrics.py` | 572 | swallowed-exception | moderate | `except Exception: pass` -- callback errors silenced | Add `logger.warning("Metrics callback failed", exc_info=True)` |
| SW-004 | `src/autom8_asana/clients/data/client.py` | 1392 | swallowed-exception | moderate | `except Exception: pass` -- response body parse failure silenced | Add `logger.debug("Response body parsing failed", exc_info=True)` |
| SW-005 | `src/autom8_asana/clients/sections.py` | 336 | swallowed-exception | moderate | `except Exception: pass` -- no logging despite ADR-0127 reference | Add `logger.warning("Section cache degradation", exc_info=True)` |
| SW-006 | `src/autom8_asana/clients/data/models.py` | 268 | swallowed-exception | moderate | `except Exception: pass` -- dtype cast silenced; comment says "log warning" but no log | Add `logger.warning("dtype cast failed", exc_info=True)` as the comment requests |
| SW-007 | `src/autom8_asana/models/business/detection/facade.py` | 108 | swallowed-exception | moderate | `except Exception: return None` -- cache lookup silenced | Add `logger.debug("Detection cache lookup failed", exc_info=True)` |
| SW-008 | `src/autom8_asana/models/business/detection/facade.py` | 204 | swallowed-exception | moderate | `except Exception: return None` -- no logging | Add `logger.debug("Detection result fetch failed", exc_info=True)` |
| SW-009 | `src/autom8_asana/services/universal_strategy.py` | 572 | swallowed-exception | moderate | `except Exception` -- no error variable captured | Capture as `except Exception as e:` and add `logger.warning("Custom field resolver fallback", exc_info=True)` |
| SW-010 | `src/autom8_asana/cache/dataframe/tiers/progressive.py` | 179 | swallowed-exception | moderate | `except Exception` -- watermark parse failure silently defaults to now() | Add `logger.warning("Watermark parse failed, defaulting to now()", exc_info=True)` |
| SW-012 | `src/autom8_asana/cache/integration/dataframe_cache.py` | 910 | swallowed-exception | minor | `except Exception` -- SWR refresh. Already logs via .exception(). | No action needed (already logged). Verify logging is present. |
| SW-013 | `src/autom8_asana/client.py` | 891 | swallowed-exception | minor | `except Exception` -- increments counter but no error details logged | Add `logger.debug("Bulk API call failed", exc_info=True)` alongside counter increment |
| IH-001 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 297+309 | inconsistent-handling | moderate | Double-catch inconsistency. SW-002 (in B01) fixes the inner pass. This entry covers reviewing the outer catch at line 297 for consistency. | Verify the outer catch at 297 logs properly. The inner catch at 309 is fixed in B01. |

**Note on SW-007, SW-008**: These files are in `models/business/detection/` which is NOT the same as the read-only `detection/` zone (which refers to `src/autom8_asana/detection/`). The HYG-004 finding SW-001 at `models/business/detection/facade.py:167` is the force-fix item. SW-007 and SW-008 are at different lines in the same file and are regular fix-now items.

---

### B10: Fix Logging Inconsistency in New Modules

**Commit message**: `fix: replace stdlib logging with autom8y_log in 4 new modules`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| HYG-005-14 | `src/autom8_asana/services/task_service.py` | 20,36 | logging-inconsistency | moderate | Uses `import logging` + `logging.getLogger(__name__)` | Replace with `from autom8y_log import get_logger` + `logger = get_logger(__name__)` |
| HYG-005-14 | `src/autom8_asana/services/section_service.py` | 18,32 | logging-inconsistency | moderate | Same pattern | Same fix |
| HYG-005-14 | `src/autom8_asana/services/entity_service.py` | 23,36 | logging-inconsistency | moderate | Same pattern | Same fix |
| HYG-005-14 | `src/autom8_asana/core/entity_registry.py` | 25,30 | logging-inconsistency | moderate | Same pattern | Same fix |

---

### B11: Extract Magic Numbers to Named Constants

**Commit message**: `refactor: extract TTL and config magic numbers to named constants`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DOC-079 | `src/autom8_asana/clients/custom_fields.py` | 96 | magic-number | moderate | Inline `ttl=1800` (30 min). Same value at `sections.py:112,331`. | Extract `CUSTOM_FIELD_CACHE_TTL = 1800` constant (or reference existing config) |
| DOC-080 | `src/autom8_asana/clients/users.py` | 90 | magic-number | moderate | Inline `ttl=3600` (1 hour). | Extract `USER_CACHE_TTL = 3600` constant |
| DOC-081 | `src/autom8_asana/cache/models/settings.py` | 151 | magic-number | moderate | `batch_check_ttl: int = 25` -- unexplained. | Add explanatory comment documenting the rationale |
| DOC-082 | `src/autom8_asana/cache/models/settings.py` | 152 | magic-number | moderate | `reconnect_interval: int = 30` -- unexplained. | Add explanatory comment |
| DOC-085 | `src/autom8_asana/services/universal_strategy.py` | 603 | magic-number | minor | Inline `ttl_seconds=3600`. | Reference shared constant or config value |

---

### B12: Add Docstrings to Public SDK Methods (Sections Client)

**Commit message**: `docs: add docstrings to 12 public methods in clients/sections.py`

| Finding ID | File | Line | Category | Severity | Description | Fix Approach |
|-----------|------|------|----------|----------|-------------|-------------|
| DOC-008 | `src/autom8_asana/clients/sections.py` | 32 | missing-docstring | moderate | `get_async` overload 1 | Add concise docstring |
| DOC-009 | `src/autom8_asana/clients/sections.py` | 41 | missing-docstring | moderate | `get_async` overload 2 | Add concise docstring |
| DOC-010 | `src/autom8_asana/clients/sections.py` | 50 | missing-docstring | moderate | `get` overload 1 | Add concise docstring |
| DOC-011 | `src/autom8_asana/clients/sections.py` | 59 | missing-docstring | moderate | `get` overload 2 | Add concise docstring |
| DOC-012 | `src/autom8_asana/clients/sections.py` | 121 | missing-docstring | moderate | `create_async` overload 1 | Add concise docstring |
| DOC-013 | `src/autom8_asana/clients/sections.py` | 132 | missing-docstring | moderate | `create_async` overload 2 | Add concise docstring |
| DOC-014 | `src/autom8_asana/clients/sections.py` | 143 | missing-docstring | moderate | `create` overload 1 | Add concise docstring |
| DOC-015 | `src/autom8_asana/clients/sections.py` | 154 | missing-docstring | moderate | `create` overload 2 | Add concise docstring |
| DOC-016 | `src/autom8_asana/clients/sections.py` | 203 | missing-docstring | moderate | `update_async` overload 1 | Add concise docstring |
| DOC-017 | `src/autom8_asana/clients/sections.py` | 212 | missing-docstring | moderate | `update_async` overload 2 | Add concise docstring |
| DOC-018 | `src/autom8_asana/clients/sections.py` | 221 | missing-docstring | moderate | `update` overload 1 | Add concise docstring |
| DOC-019 | `src/autom8_asana/clients/sections.py` | 230 | missing-docstring | moderate | `update` overload 2 | Add concise docstring |

---

## 3. Refactor Items

Items requiring design decisions, multi-module coordination, or TDD-level planning. Too complex for a cleanup sprint.

| ID | Description | Finding IDs | Complexity | Notes |
|----|------------|-------------|------------|-------|
| R01 | **ProgressiveProjectBuilder factory function** -- Extract the 7-step instantiation ceremony duplicated 8+ times into a factory | HYG-002-001, HYG-002-002 | Medium | Touches 6 files, 8+ call sites. Requires deciding factory location (new module vs existing). TDD-SERVICE-LAYER-001 may subsume this. |
| R02 | **FreshnessStamp serialization consolidation** -- Extract `to_dict()`/`from_dict()` classmethods to eliminate duplication between Redis and S3 backends | HYG-002-005, HYG-002-006 | Low-Medium | Changes model class + 2 backends. Low risk but crosses module boundaries. |
| R03 | **S3 config dataclass consolidation** -- Adopt `S3LocationConfig` across all 5 config dataclasses | HYG-002-007 | Medium | Touches 5 files in different subsystems. Needs coordinated migration. |
| R04 | **Schema lookup ceremony extraction** -- Extract `to_pascal_case() + SchemaRegistry.get_instance().get_schema()` to a single helper | HYG-002-010 | Low | 15+ sites across 9 files. Straightforward but large blast radius. Consider for next sprint. |
| R05 | **Workspace GID retrieval consolidation** -- Replace raw `os.environ.get("ASANA_WORKSPACE_GID")` with `get_settings().asana.workspace_gid` | HYG-002-018, HYG-005-12 (partial) | Low | 5+ sites. Simple but some are in read-only zones. |
| R06 | **Duplicate CircuitBreakerOpenError consolidation** -- Merge `core/retry.py` and `exceptions.py` definitions | EM-002 | Medium | 6 files import one or the other. Needs careful aliasing during transition. |
| R07 | **Orphaned modules: wire or remove services layer** -- `EntityService`, `TaskService`, `SectionService` need route wiring (Phase 3/4) or removal | OM-001, OM-002, OM-003, OM-004, OM-005, HYG-005-02 | High | Explicitly marked as "Phase 3/4 work" in docstrings. Keep as-is until service layer migration proceeds. |
| R08 | **Orphaned modules: wire or remove cache/connections** -- Connection managers not integrated into backends | OM-007, HYG-005-01 | High | Per TDD-connection-lifecycle-management. Backends manage own connections. Integration is a separate initiative. |
| R09 | **Orphaned module: wire or remove dataframes/storage.py** -- Storage protocol not adopted by any consumer | OM-006, HYG-005-03 | Medium | Per TDD-UNIFIED-DF-PERSISTENCE-001. Phase 1 complete, Phase 2 not started. |
| R10 | **Unused exception types: wire automation exceptions** -- `AutomationError`, `RuleExecutionError`, `SeedingError`, `PipelineActionError` defined but never raised | UE-001, UE-002, UE-003, UE-004 | Medium | Requires coordinating raises in pipeline.py, engine.py, seeding.py with catches in callers. Part of exception hierarchy initiative. |
| R11 | **Unused exception types: wire cache semantic errors** -- `CacheReadError`, `CacheWriteError` defined but never raised | UE-005 | Medium | Requires backends to raise specific errors instead of generic `Exception`. |
| R12 | **Bot PAT acquisition boilerplate consolidation** -- Repeated 12 times across 9 files | HYG-002-004 | Medium | Each site handles errors differently; requires analyzing which variations are intentional. |
| R13 | **API error handling pattern unification** -- Mixed `HTTPException` vs centralized handlers | HYG-005-06, HYG-005-07 | High | Needs documented convention, then systematic migration. |
| R14 | **Three S3 persistence implementations** -- DataFramePersistence, S3DataFrameStorage, AsyncS3Client overlap | HYG-002-020 | High | TDD exists but migration not started. |

---

## 4. Defer Items

Items explicitly out of scope per the triage ruleset, in read-only zones, or too low-ROI for this sprint.

### 4a. Deferred by Ruleset: Bare-Except Replacements (106 items)

Per `error_handling_scope: silent_failures_only`, all 106 `except Exception` sites that are NOT swallowed exceptions are deferred to a follow-up exception-handling initiative.

| ID | Description | Finding IDs | Rationale |
|----|------------|-------------|-----------|
| D01 | Bare-except sites in api/main.py (11) | BE-001 to BE-011 | Read-only zone + bare-except scope deferred |
| D02 | Bare-except sites in api/routes/ (10) | BE-012 to BE-022 | Bare-except scope deferred |
| D03 | Bare-except sites in services/universal_strategy.py (6) | BE-023 to BE-028 | Bare-except scope deferred (SW-009 handled separately in B09) |
| D04 | Bare-except sites in clients/data/client.py (7) | BE-029 to BE-035 | Bare-except scope deferred (SW-004 handled separately in B09) |
| D05 | Bare-except sites in lambda_handlers/ (11) | BE-036 to BE-046 | Read-only zone + bare-except scope deferred |
| D06 | Bare-except sites in cache/ subsystem (21) | BE-047 to BE-067 | Bare-except scope deferred (SW-002, SW-003, SW-010 handled in B01/B09) |
| D07 | Bare-except sites in cache/integration/mutation_invalidator.py (7) | BE-068 to BE-074 | Bare-except scope deferred (SW-002/IH-001 handled in B01/B09) |
| D08 | Bare-except sites in cache/connections/registry.py (3) | BE-075 to BE-077 | Bare-except scope deferred; module also orphaned (HYG-005-01) |
| D09 | Bare-except sites in persistence/ (10) | BE-078 to BE-087 | Bare-except scope deferred |
| D10 | Bare-except sites in dataframes/ (21) | BE-088 to BE-108 | Bare-except scope deferred |
| D11 | Bare-except sites in automation/ (19) | BE-109 to BE-127 | Bare-except scope deferred |
| D12 | Bare-except sites in models/ (20) | BE-128 to BE-148 | Bare-except scope deferred (SW-001, SW-007, SW-008 handled in B01/B09) |
| D13 | Bare-except sites in other files (11) | BE-149 to BE-159 | Bare-except scope deferred |

### 4b. Deferred by Read-Only Zone

| ID | Description | Finding IDs | Rationale |
|----|------------|-------------|-----------|
| D14 | api/main.py god module refactoring | HYG-002-003, HYG-002-008 | `api/main.py` is a read-only zone. SRP violations require full module extraction. |
| D15 | api/main.py ProgressiveProjectBuilder duplication | HYG-002-001 (3 sites in main.py) | Read-only zone. The factory refactor (R01) addresses non-main.py sites. |
| D16 | api/main.py import migration | HYG-005-17 | Read-only zone. Shim imports in main.py stay until future refactoring. |
| D17 | metrics/ commented-out imports | DOC-005 | `metrics/` is a read-only zone. |
| D18 | lambda_handlers/ bare-except sites | BE-036 to BE-046 | Read-only zone (DOC-001 is the only force-fix override). |
| D19 | lambda_handlers/ missing docstrings | DOC-066 | Read-only zone. |

### 4c. Deferred by Low ROI or Out-of-Scope

| ID | Description | Finding IDs | Rationale |
|----|------------|-------------|-----------|
| D20 | Minor missing docstrings (business model properties) | DOC-020 to DOC-030 | 11 property docstrings on business model. Self-documenting from types. Low ROI. |
| D21 | Minor missing docstrings (query error to_dict) | DOC-031 to DOC-038 | 8 `to_dict` methods. Method name is self-documenting. Low ROI. |
| D22 | Minor missing docstrings (service error properties) | DOC-039 to DOC-052 | 14 error class properties. Parent class docstring covers pattern. Low ROI. |
| D23 | Minor missing docstrings (internal helpers) | DOC-053 to DOC-065, DOC-067 to DOC-077, DOC-078 | 24 internal/private function docstrings. Inner functions, helpers, dynamically generated methods. Low ROI for cleanup sprint. |
| D24 | Commented-out dead-branch note | DOC-006 | Minor. Comment documents an unreachable branch; not actual dead code. |
| D25 | Commented-out narrative comment | DOC-007 | Minor. Inline documentation comment, not dead code. |
| D26 | TODO stubs in extractors/unit.py | DOC-002, DOC-003, DOC-004 | Intentionally deferred feature stubs awaiting business input. Not cleanup debt. |
| D27 | Minor magic numbers | DOC-084, DOC-086 | Low-impact: PAT min-length check (DOC-084) and fallback TTL in error handler (DOC-086). Not worth the churn. |
| D28 | metrics/ magic numbers | DOC-083 | Read-only zone (`metrics/`). |
| D29 | CACHE_TRANSIENT_ERRORS exception pattern duplication | HYG-002-014, HYG-002-015 | 14 identical try/except blocks. Could use decorator/context manager but low severity. Refactor candidate for follow-up. |
| D30 | MutationEvent fire-and-forget boilerplate | HYG-002-021 | 14 mutation endpoints. Low severity DRY violation. |
| D31 | Cache-check-before-HTTP pattern duplication | HYG-002-022 | 3+ client classes. Template method refactor. Low severity. |
| D32 | list_subtasks/list_dependents endpoint duplication | HYG-002-009 | 2 endpoints in tasks.py. Minor DRY. |
| D33 | ISP violation: warm() no-op stubs | HYG-002-019 | Protocol design decision. Low impact. |
| D34 | OCP violations: hardcoded entity mappings | HYG-002-016, HYG-002-017 | 2 sites. Registry-based extension would be ideal but is low priority for cleanup sprint. |
| D35 | SRP violations: large classes | HYG-002-011, HYG-002-012, HYG-002-013 | SaveSession (1604 lines), DataClient (1551 lines), ProgressiveProjectBuilder (1223 lines). Architectural refactors requiring dedicated initiatives. |
| D36 | CancelledError guard additions | CE-001, CE-002 | Defensive improvement. Safe on Python 3.12+ (current target). Low urgency. |
| D37 | Broad try block decomposition | BT-001 | pipeline.py. Would improve error attribution but is a behavioral change risk. |
| D38 | Redundant exception catch hierarchy | EM-001 | `except (KeyError, AttributeError, Exception)`. Cosmetic fix but low impact. |
| D39 | Unused ServiceNotConfiguredError | UE-006 | Part of orphaned service layer (R07). Resolves when services are wired. |
| D40 | Config access inconsistency (3 patterns) | HYG-005-12, HYG-005-13 | Systemic architectural issue. Needs config consolidation initiative. |
| D41 | Memory backend missing logger | HYG-005-08 | Minor inconsistency. Memory backend is test/dev only. |
| D42 | Middleware structlog direct usage | HYG-005-15 | Intentional per middleware requirements. Not a bug. |
| D43 | BuildCoordinator exported but unused | HYG-005-11 | Borderline orphan. Has test coverage, awaiting integration. |
| D44 | API error handling pattern inconsistency | HYG-005-06, HYG-005-07 | Needs design decision before fixing. Classified as R13 refactor. |
| D45 | Swallowed exceptions in read-only zones | SW-011, SW-014 | SW-011 (`normalizers.py:75`) is minor/acceptable. SW-014 (`health.py:219`) already logs via `.exception()`. |

---

## 5. Read-Only Zone Findings

All findings that touch read-only zones (`lambda_handlers/`, `metrics/`, `detection/`, `api/main.py`), showing classification.

### lambda_handlers/ (read-only)

| Finding ID | Description | Classification | Notes |
|-----------|-------------|----------------|-------|
| **DOC-001** | Broken `TieredCacheProvider()` call in `cache_invalidate.py:105` | **FORCE-FIX (B01)** | Runtime failure. Override granted. Surgical fix only. |
| BE-036 to BE-041 | 6 bare-except sites in `cache_warmer.py` | Defer (D05) | Bare-except scope deferred |
| BE-042, BE-043 | 2 bare-except sites in `cache_invalidate.py` | Defer (D05) | Bare-except scope deferred |
| BE-044 to BE-046 | 3 bare-except sites in `checkpoint.py` | Defer (D05) | Bare-except scope deferred |
| DOC-066 | Missing docstring in `cache_warmer.py` | Defer (D19) | Read-only zone |

### metrics/ (read-only)

| Finding ID | Description | Classification | Notes |
|-----------|-------------|----------------|-------|
| DOC-005 | Commented-out imports in `definitions/__init__.py` | Defer (D17) | Read-only zone |
| DOC-083 | Magic numbers in `compute.py` | Defer (D28) | Read-only zone |

### detection/ (read-only -- note: `models/business/detection/` is NOT in this zone)

| Finding ID | Description | Classification | Notes |
|-----------|-------------|----------------|-------|
| **SW-001** | Silent `except Exception: pass` in `detection/facade.py:167` | **FORCE-FIX (B01)** | Observability gap. Override granted. Add logging only. |
| BE-135 | Same site as SW-001 (bare-except aspect) | Defer | Bare-except scope deferred; swallowed-exception aspect fixed via SW-001 |

**Clarification on `detection/` vs `models/business/detection/`**: The read-only zone is `src/autom8_asana/detection/`. The file `models/business/detection/facade.py` referred to in SW-001 appears to be at path `src/autom8_asana/models/business/detection/facade.py`. The force-fix override applies to whichever path this file is actually at. SW-007, SW-008 (other findings in the same facade.py) are classified as fix-now in B09 because `models/business/detection/` is NOT a read-only zone.

### api/main.py (read-only)

| Finding ID | Description | Classification | Notes |
|-----------|-------------|----------------|-------|
| BE-001 to BE-011 | 11 bare-except sites | Defer (D01) | Read-only + bare-except deferred |
| HYG-002-001 | ProgressiveProjectBuilder duplication (3 sites in main.py) | Defer (D15) | Read-only zone |
| HYG-002-003 | God module (1466 lines, 6+ responsibilities) | Defer (D14) | Read-only zone. Architectural refactor. |
| HYG-002-008 | Near-duplicate `_do_incremental_catchup`/`_do_full_rebuild` | Defer (D14) | Read-only zone |
| HYG-005-17 | Import from deprecated shim paths | Defer (D16) | Read-only zone |

---

## 6. Cross-References

Findings that appear in multiple scans or have significant overlap.

| Primary Finding | Cross-Referenced With | Relationship |
|----------------|----------------------|-------------|
| DC-001 to DC-031 (HYG-001 shims) | HYG-005-04, HYG-005-05, HYG-005-09, HYG-005-10, HYG-005-16, HYG-005-17, HYG-005-18 (HYG-005 inconsistent patterns) | Same root cause: cache module reorg incomplete. HYG-001 catalogs the shim files; HYG-005 catalogs the import sites still using deprecated paths. Both resolved by B03-B07. |
| OM-001 to OM-007 (HYG-001 orphaned modules) | HYG-005-01, HYG-005-02, HYG-005-03, HYG-005-11 (HYG-005 orphaned modules) | Same modules found by both scans. HYG-001 catalogs them as dead code; HYG-005 evaluates architectural intent. Classified as R07/R08/R09 (refactor -- intentionally incomplete migrations). |
| SW-001, SW-002 (HYG-003 swallowed exceptions) | BE-135, BE-072 (HYG-003 bare-except) | Same code sites. The bare-except aspect (BE-*) is deferred; the swallowed-exception aspect (SW-*) is force-fixed. |
| HYG-002-005/006 (FreshnessStamp DRY) | SM-S3-007 (prior smell report) | Extends prior finding to identify root cause as missing serialization abstraction. Classified as R02. |
| HYG-002-007 (S3 config DRY) | SM-S3-004, HYG-005-12 | Config proliferation spans multiple scans. Classified as R03 + D40. |
| HYG-002-018 (workspace GID DRY) | SM-L031, HYG-005-12 | Inline env var access pattern. Classified as R05. |
| DOC-079/080/085 (magic numbers) | HYG-002-018 (DRY violation) | TTL magic numbers are a special case of config inconsistency. Classified as fix-now (B11). |
| HYG-005-14 (logging inconsistency) | OM-001 to OM-003 (orphaned service modules) | The 4 modules with wrong logger are all from the same architectural initiative. Logging fix (B10) is independent of the wiring decision (R07). |

---

## Appendix: Batch Execution Order and Dependencies

```
B01 (force-fixes)           -- no dependencies, execute first
B02 (delete dead shim)      -- no dependencies
B10 (logging fix)           -- no dependencies
B11 (magic numbers)         -- no dependencies
B12 (docstrings)            -- no dependencies
B09 (swallowed exceptions)  -- no dependencies
B08 (unused test imports)   -- no dependencies
B03 (test shim migration)   -- no dependencies
B04 (prod imports: models/) -- after B03 (to avoid conflicts)
B05 (prod imports: integration/) -- after B03 (to avoid conflicts)
B06 (prod imports: policies/providers/) -- after B03
B07 (delete prod shims)     -- MUST follow B04 + B05 + B06
```

**Parallelizable groups**:
- Group A (independent, can run in any order): B01, B02, B08, B09, B10, B11, B12
- Group B (sequential): B03 -> B04 -> B05 -> B06 -> B07

The janitor should execute Group A first (7 commits), then Group B (5 commits), totaling 12 commits.

---

## Appendix: Verification Checklist for Janitor

For each batch, after committing:
1. Run full test suite: `pytest tests/`
2. Verify no import errors: `python -c "import autom8_asana"`
3. For shim-related batches (B02-B07): verify `grep -r` confirms no remaining references to deleted files
4. For B07 specifically: verify `api/main.py` still works by checking its imports resolve through `cache/__init__.py`
5. No coverage regression vs baseline
