# Hygiene Audit Report -- HYG-012

**Date:** 2026-02-04 (re-audit 2026-02-04)
**Auditor:** audit-lead
**Session:** session-20260204-170818-5363b6da
**Scope:** 12 remediation batches (B01--B12) from deep hygiene sprint + corrective fixes

---

## 1. Test Suite Results

### Summary

| Metric | Baseline (committed) | Initial Audit | After Corrective Fix | Delta vs Baseline |
|--------|---------------------|---------------|---------------------|-------------------|
| Passed | 6848 | 7452 | 7490 | +642 |
| Failed | 6 | 44 | 6 | 0 |
| Skipped | 178 | 178 | 178 | 0 |
| xfailed | 1 | 1 | 1 | 0 |
| Total | 7033 | 7675 | 7675 | +642 |

### Pre-existing Failures (6, unchanged)

All 6 exist on committed code and are NOT regressions:

- `tests/unit/dataframes/builders/test_adversarial_pacing.py` -- 4 failures (checkpoint `put_object_async` not called)
- `tests/unit/dataframes/builders/test_paced_fetch.py` -- 2 failures (checkpoint metadata assertions)

### Previous Regressions -- RESOLVED

**Regression Category 1 (FINDING-001): Missing backward-compat shims -- FIXED**

The corrective fix created 4 backward-compat shim files at the cache root to preserve read-only zone import paths. All 4 shims verified (see Section 9 below). The 4 API test failures in `test_preload_parquet_fallback.py` are now passing.

**Regression Category 2 (FINDING-002): Test state pollution -- FIXED**

An `autouse` fixture `_isolate_type_registry` was added to `tests/unit/cache/test_cacheentry_hierarchy.py` that saves and restores `CacheEntry._type_registry` around each test. The 34 downstream test failures caused by registry pollution are now resolved. Full suite confirms 0 new regressions.

---

## 2. Force-Fix Verification

### DOC-001: TieredCacheProvider broken call -- PASS

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py`
**Line 105-108:**
```python
from autom8_asana.cache.backends.redis import RedisCacheProvider
hot_tier = RedisCacheProvider()
cache = TieredCacheProvider(hot_tier=hot_tier)
```

Previously `TieredCacheProvider()` was called with no arguments, which would fail at runtime. Now correctly passes `hot_tier` keyword argument. Verified.

### SW-001: Silent except-pass in detection/facade.py -- PASS

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection/facade.py`
**Lines 168-178:**
```python
except Exception:
    # Per FR-DEGRADE-002: Cache storage failures don't prevent detection
    logger.warning(
        "detection_cache_store_failed_silent",
        extra={
            "task_gid": task.gid,
            "entry_type": EntryType.DETECTION.value,
        },
        exc_info=True,
    )
    pass
```

Previously a bare `except: pass` with no logging. Now logs a structured warning with context fields and `exc_info=True` for stack trace. Business justification documented in comment. Verified.

### SW-002: Silent except-pass in mutation_invalidator.py -- PASS

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/mutation_invalidator.py`
**Lines 309-318:**
```python
except Exception:
    logger.warning(
        "hard_invalidation_fallback_failed",
        extra={
            "gid": gid,
            "entry_type": entry_type.value,
        },
        exc_info=True,
    )
    pass
```

Previously a bare `except: pass` in the hard-invalidation fallback path. Now logs a structured warning with context. Verified.

---

## 3. Shim Deletion Verification -- PASS (UPDATED)

After corrective fixes, the cache root now contains `__init__.py` plus 4 retained backward-compat shims required by read-only zones (`api/main.py`, `lambda_handlers/cache_invalidate.py`):

```
src/autom8_asana/cache/__init__.py
src/autom8_asana/cache/factory.py            (shim -> integration/factory.py)
src/autom8_asana/cache/mutation_invalidator.py (shim -> integration/mutation_invalidator.py)
src/autom8_asana/cache/schema_providers.py    (shim -> integration/schema_providers.py)
src/autom8_asana/cache/tiered.py              (shim -> providers/tiered.py)
```

These 4 shims are a necessary consequence of the read-only zone constraint and are NOT a defect. Each contains only a single `from ... import *` re-export with a docstring documenting the rationale.

All other shim files have been successfully deleted and moved to their new subpackage locations:

- `cache/models/` -- entry.py, errors.py, events.py, completeness.py, freshness.py, metrics.py, settings.py, staleness_settings.py, versioning.py
- `cache/integration/` -- autom8_adapter.py, batch.py, dataframe_cache.py, dataframes.py, factory.py, freshness_coordinator.py, hierarchy_warmer.py, loader.py, schema_providers.py, staleness_coordinator.py, stories.py, upgrader.py
- `cache/policies/` -- coalescer.py, hierarchy.py, lightweight_checker.py, staleness.py
- `cache/providers/` -- tiered.py, unified.py

---

## 4. Import Health Check -- PASS

```
$ python -c "import autom8_asana"
OK: autom8_asana imported

$ python -c "from autom8_asana.cache import CacheProviderFactory, MutationInvalidator, TieredCacheProvider"
OK: all 3 cache symbols imported

$ python -c "from autom8_asana.cache.factory import CacheProviderFactory"
factory shim: OK

$ python -c "from autom8_asana.cache.mutation_invalidator import MutationInvalidator"
mutation_invalidator shim: OK

$ python -c "from autom8_asana.cache.schema_providers import AsanaSchemaProvider, register_asana_schemas"
schema_providers shim: OK

$ python -c "from autom8_asana.cache.tiered import TieredCacheProvider"
tiered shim: OK
```

Top-level package, key cache symbols, and all 4 backward-compat shim import paths verified working.

---

## 5. Spot-Check Results

### B09: Swallowed Exception Fixes -- PASS

SW-001 and SW-002 verified above. Both follow the correct pattern:
- Structured log event name (snake_case)
- `extra={}` dict with relevant context fields
- `exc_info=True` for stack trace capture
- Comment explaining business rationale where applicable

### B11: Magic Number Extractions -- NOT VERIFIED

Could not spot-check B11 in detail within scope. Advisory only -- magic number extraction is low-risk.

### B12: Docstrings -- NOT VERIFIED

Could not spot-check B12 docstring additions within scope. Advisory only -- docstring additions are low-risk.

---

## 6. Residual Findings

### FINDING-001: Missing `cache.factory` backward-compat proxy -- RESOLVED

**Severity:** Was Blocking, now RESOLVED
**Batch:** B07 (shim deletion)
**Resolution:** 4 backward-compat shim files created at cache root (`factory.py`, `mutation_invalidator.py`, `schema_providers.py`, `tiered.py`). Each contains a single `from ... import *` re-export to the new subpackage location with a docstring explaining the HYG-012 rationale. All 4 verified via direct import.

### FINDING-002: Test state pollution from new test modules -- RESOLVED

**Severity:** Was Blocking, now RESOLVED
**Batch:** test_cacheentry_hierarchy.py
**Resolution:** An `autouse` fixture `_isolate_type_registry` was added at module level in `tests/unit/cache/test_cacheentry_hierarchy.py`. The fixture copies `CacheEntry._type_registry` before each test and restores it afterward, preventing global state pollution. Verified: the file passes in isolation (66 passed) and contributes zero failures to the full suite run.

---

## 7. Deferred Items Summary

Per the triage ruleset (`hygiene-triage-rules.yaml`):

| Category | Deferred | Rationale |
|----------|----------|-----------|
| Bare-except replacements | 106 sites | Follow-up initiative |
| Exception hierarchy | Full wiring | Follow-up initiative |
| Orphaned modules | 7 modules | Classified by architect-enforcer |
| TODO marker resolution | Best effort | Not a sprint blocker |
| Full docstring coverage | Best effort | Not a sprint blocker |
| `api/main.py` refactoring | Entire file | 1466-line god module, separate initiative |

---

## 8. Signoff Recommendation

### Verdict: APPROVED WITH NOTES

**Re-audit date:** 2026-02-04
**Previous verdict:** REVISION REQUIRED (2 blocking findings)
**Current verdict:** APPROVED WITH NOTES

**Rationale:**

Both blocking findings from the initial audit have been resolved and verified:

1. **FINDING-001** (missing backward-compat shims) -- RESOLVED. Four shim files created at cache root to preserve read-only zone import paths. All 4 verified via direct import. No production regression.

2. **FINDING-002** (test state pollution) -- RESOLVED. Autouse isolation fixture added to `test_cacheentry_hierarchy.py`. Full suite failure count returned to baseline (6 pre-existing).

The hygiene sprint accomplished substantial structural improvement:
- 642 new tests added (7490 passing vs 6848 baseline)
- Cache module reorganized into 4 clean subpackages (models/, integration/, policies/, providers/)
- 3 force-fix items correctly resolved (DOC-001, SW-001, SW-002)
- All import paths verified working (both new subpackage paths and backward-compat shims)
- Swallowed exceptions fixed with proper structured logging

**Advisory notes (non-blocking):**

1. **4 retained shims at cache root.** `factory.py`, `mutation_invalidator.py`, `schema_providers.py`, and `tiered.py` remain as backward-compat shims because `api/main.py` and `lambda_handlers/cache_invalidate.py` are read-only zones. These shims should be removed when those consumers are refactored in a future initiative.

2. **6 pre-existing test failures.** `test_adversarial_pacing.py` (4) and `test_paced_fetch.py` (2) continue to fail as they did before the hygiene sprint. These are pre-existing and unrelated to the refactoring.

3. **B11 (magic numbers) and B12 (docstrings) not spot-checked.** Low-risk changes, advisory only.

---

## 9. Corrective Fix Verification (Re-Audit)

### FINDING-001 Verification

**Method:** Direct import of each shim's primary export.

| Shim File | Import Path | Export Verified | Status |
|-----------|------------|-----------------|--------|
| `cache/factory.py` | `autom8_asana.cache.factory` | `CacheProviderFactory` | PASS |
| `cache/mutation_invalidator.py` | `autom8_asana.cache.mutation_invalidator` | `MutationInvalidator` | PASS |
| `cache/schema_providers.py` | `autom8_asana.cache.schema_providers` | `AsanaSchemaProvider`, `register_asana_schemas` | PASS |
| `cache/tiered.py` | `autom8_asana.cache.tiered` | `TieredCacheProvider` | PASS |

Each shim file contains:
- Docstring explaining HYG-012 FINDING-001 rationale
- Single `from autom8_asana.cache.<subpackage>.<module> import *` re-export
- Appropriate `noqa` comments for F403/F401

### FINDING-002 Verification

**Method:** Run `test_cacheentry_hierarchy.py` in isolation AND confirm zero regressions in full suite.

| Check | Result |
|-------|--------|
| Isolation run | 66 passed, 0 failed |
| Full suite run | Not in failed test list (6 failures all pre-existing) |
| Fixture present | `_isolate_type_registry` autouse fixture at module scope |
| Mechanism | Copies/restores `CacheEntry._type_registry` ClassVar dict |

### Full Suite Confirmation

```
6 failed, 7490 passed, 178 skipped, 1 xfailed in 121.70s
```

Failed tests (all pre-existing):
- `test_adversarial_pacing.py::TestSectionSizeBoundaries::test_section_with_10000_tasks`
- `test_adversarial_pacing.py::TestConfigurationBoundaries::test_checkpoint_every_page`
- `test_adversarial_pacing.py::TestDataIntegrity::test_checkpoint_df_has_correct_schema`
- `test_adversarial_pacing.py::TestMixedCheckpointResults::test_first_checkpoint_fails_second_succeeds`
- `test_paced_fetch.py::TestCheckpointWriteAtIntervals::test_checkpoint_write_at_intervals`
- `test_paced_fetch.py::TestCheckpointMetadataUpdated::test_checkpoint_metadata_updated`
