# TDD-WS2: Cache Reliability Hardening

**Author**: Architect (WS2-Arch)
**Date**: 2026-02-17
**Initiative**: SSoT Convergence & Reliability Hardening
**Workstream**: WS2 (Cache Reliability)
**Status**: DRAFT
**Checkpoint**: `.claude/wip/WS2-CHECKPOINT.md`

---

## 1. Problem Statement

The cache subsystem (29 files, ~91 except clauses) is architecturally stable and well-tested at 10,575 tests. However, a full audit reveals three categories of reliability debt:

1. **Exception handling inconsistency**: While the exception hierarchy (`core/exceptions.py`) provides well-designed error tuples (`CACHE_TRANSIENT_ERRORS`, `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`), and 9 BROAD-CATCH sites are intentionally annotated, the codebase has no outstanding bare `except Exception` clauses that need narrowing. All catch sites either use specific error tuples or are annotated as intentional broad catches.

2. **Invalidation partial failure paths**: `MutationInvalidator` handles partial failures with per-entry and per-project isolation loops (BROAD-CATCH: isolation). The soft invalidation path (`_soft_invalidate_entity_entries`) performs a read-modify-write cycle per entry type with a fallback to hard invalidation. This is correct, but the inner fallback's BROAD-CATCH at line 304 catches bare `Exception` with only a `pass` -- the most fragile catch site in the invalidation pipeline.

3. **Unified store consistency under error**: `UnifiedTaskStore.put_batch_async()` performs `cache.set_batch()` followed by hierarchy registration, followed by optional parent warming. If `set_batch()` succeeds but parent warming fails, the hierarchy index and cache can diverge -- hierarchy may reference GIDs not in cache, or cache may contain tasks whose parent chain is incomplete.

### Current Failure Modes by Subpackage

| Subpackage | Files | Except Clauses | Primary Failure Mode |
|---|---|---|---|
| backends/ | base.py, s3.py, redis.py, memory.py | 19 | Transport errors -> degraded mode transitions |
| providers/ | tiered.py, unified.py | 13 | S3 write-through failures; hierarchy warming divergence |
| integration/ | mutation_invalidator.py, staleness_coordinator.py, freshness_coordinator.py, hierarchy_warmer.py, autom8_adapter.py, dataframe_cache.py, loader.py, upgrader.py, schema_providers.py | 17 | Invalidation partial failures; SWR refresh background crashes |
| policies/ | coalescer.py, lightweight_checker.py | 3 | Unresolved futures if batch check fails unexpectedly |
| dataframe/ | decorator.py, coalescer.py, warmer.py, build_coordinator.py, factory.py, tiers/progressive.py, tiers/memory.py | 16 | Progressive tier vendor-polymorphic errors; build timeout cascades |
| models/ | entry.py, versioning.py, completeness.py, metrics.py, freshness.py | 7 | Datetime parsing edge cases; metrics callback isolation |

---

## 2. Exception Narrowing Audit

### Methodology

Grepped all `except ` clauses across `src/autom8_asana/cache/`. Classified each into four categories:

- **(a) Already using error tuples** -- no change needed
- **(b) Should narrow to error tuples** -- needs change
- **(c) BROAD-CATCH annotated** -- intentional, keep as-is
- **(d) Boundary guard without annotation** -- keep but annotate

### Complete Audit Inventory

#### Category (a): Already Using Error Tuples (58 sites) -- NO CHANGE

| File | Line(s) | Catch Clause | Notes |
|---|---|---|---|
| backends/base.py | 151, 177, 194, 220 | `self._transport_errors` | Template method pattern |
| backends/s3.py | 174 | `ImportError` | Optional dependency guard |
| backends/s3.py | 203, 251, 497, 510, 658, 692, 704, 730, 869 | `S3_TRANSPORT_ERRORS` | S3 transport boundary |
| backends/s3.py | 380 | `(json.JSONDecodeError, ValueError, KeyError, gzip.BadGzipFile)` | Deserialization |
| backends/redis.py | 151 | `ImportError` | Optional dependency guard |
| backends/redis.py | 179, 228, 443, 518, 561, 622, 662, 691, 780 | `REDIS_TRANSPORT_ERRORS` | Redis transport boundary |
| backends/redis.py | 332 | `(json.JSONDecodeError, ValueError, KeyError)` | Deserialization |
| providers/tiered.py | 169, 215, 233, 265, 311, 335, 365, 431, 483, 493 | `CACHE_TRANSIENT_ERRORS` | Tier coordination |
| providers/unified.py | 287, 378, 606 | `CACHE_TRANSIENT_ERRORS` | Unified store operations |
| integration/mutation_invalidator.py | 195, 238, 325 | `CACHE_TRANSIENT_ERRORS` | Invalidation primitives |
| integration/staleness_coordinator.py | 133, 173, 195 | `CACHE_TRANSIENT_ERRORS` | Staleness check flow |
| integration/freshness_coordinator.py | 249, 480 | `CACHE_TRANSIENT_ERRORS` | Freshness check flow |
| integration/hierarchy_warmer.py | 95 | `CACHE_TRANSIENT_ERRORS` | Hierarchy warming |
| integration/autom8_adapter.py | 313, 450 | `CACHE_TRANSIENT_ERRORS` | Adapter operations |
| integration/autom8_adapter.py | 475 | `ValueError` | Config validation |
| integration/loader.py | 329 | `ValueError` | Entry type parsing |
| integration/upgrader.py | 145 | `CACHE_TRANSIENT_ERRORS` | Cache upgrade |
| integration/upgrader.py | 208 | `ValueError` | Version parsing |
| integration/schema_providers.py | 43 | `ImportError` | Optional dependency |
| integration/dataframe_cache.py | 27 | `ImportError` | Metrics optional |
| policies/lightweight_checker.py | 129 | `CACHE_TRANSIENT_ERRORS` | Batch check |
| policies/coalescer.py | 135, 160, 263 | `asyncio.CancelledError` | Timer cancellation |
| dataframe/decorator.py | 232 | `HTTPException` | Re-raise at API boundary |
| dataframe/coalescer.py | 168 | `TimeoutError` | Wait timeout |
| dataframe/tiers/memory.py | 38 | `ValueError` | Env var parsing |
| dataframe/tiers/memory.py | 52 | `(FileNotFoundError, ValueError, PermissionError)` | cgroup file access |
| dataframe/tiers/progressive.py | 124, 223, 283, 306 | `ValueError` | Key parsing |
| dataframe/tiers/progressive.py | 146, 264, 290, 330 | `S3_TRANSPORT_ERRORS` | S3 transport |
| dataframe/warmer.py | 244 | `RuntimeError` | Strict mode re-raise |
| dataframe/warmer.py | 248, 384, 475 | `CACHE_TRANSIENT_ERRORS` | Warm operations |
| dataframe/build_coordinator.py | 286 | `TimeoutError` | Build timeout |
| dataframe/build_coordinator.py | 352 | `CACHE_TRANSIENT_ERRORS` | Build execution |
| dataframe/factory.py | 55 | `BotPATError` | Auth error |
| models/entry.py | 267, 283 | `ValueError` | Datetime parsing |
| models/versioning.py | 148, 164 | `ValueError` | Version parsing |
| models/completeness.py | 249 | `ValueError` | Level parsing |
| models/freshness.py | 17 | `ImportError` | Optional dependency |
| __init__.py | 174 | `ImportError` | SDK import guard |

#### Category (b): Should Narrow to Error Tuples -- NONE FOUND

All non-annotated catch sites already use specific error types or error tuples. The WS1/I4-S1 exception narrowing work and the error tuple architecture in `core/exceptions.py` have already addressed this category comprehensively.

#### Category (c): BROAD-CATCH Annotated (9 sites) -- KEEP AS-IS

| File | Line | Annotation | Category | Rationale |
|---|---|---|---|---|
| policies/coalescer.py | 208 | `BROAD-CATCH: boundary` | boundary | RF-006: widened to prevent unresolved futures causing hangs |
| dataframe/decorator.py | 235 | `BROAD-CATCH: boundary` | boundary | Catch-all converts to HTTPException at API boundary |
| dataframe/tiers/progressive.py | 153 | `BROAD-CATCH: vendor-polymorphic` | vendor-polymorphic | `load_dataframe` may raise diverse errors from Polars/S3/JSON |
| integration/mutation_invalidator.py | 112 | `BROAD-CATCH: isolation` | isolation | Background task boundary, must never propagate |
| integration/mutation_invalidator.py | 292 | `BROAD-CATCH: isolation` | isolation | Per-entry loop with fallback to hard invalidation |
| integration/mutation_invalidator.py | 304 | `BROAD-CATCH: isolation` | isolation | Last-resort fallback, must not fail |
| integration/mutation_invalidator.py | 347 | `BROAD-CATCH: isolation` | isolation | Per-project loop, single failure must not abort batch |
| integration/dataframe_cache.py | 952 | `BROAD-CATCH: isolation` | isolation | SWR refresh callback can throw any error |
| models/metrics.py | 576 | `BROAD-CATCH: hook` | hook | Metrics callbacks must not break cache operations |

#### Category (d): Boundary Guard Without Annotation -- NONE FOUND

All broad catch sites already carry BROAD-CATCH annotations with category labels. No annotation work needed.

### Audit Conclusion

**The exception handling landscape is clean.** Prior work (I4-S1, RF-006, RF-008) already narrowed all applicable sites and annotated all intentional broad catches. WS2 does NOT need an exception narrowing sprint. The reliability work focuses instead on invalidation correctness, warm-up resilience, and unified store consistency.

---

## 3. Invalidation Correctness

### 3.1 MutationInvalidator Analysis

The `MutationInvalidator` (integration/mutation_invalidator.py) handles cache invalidation for REST mutation endpoints via a fire-and-forget pattern.

#### Current Error Handling Strategy

```
invalidate_async(event)
  |
  +-- BROAD-CATCH (line 112): isolation -- top-level boundary
  |
  +-- _handle_task_mutation(event)
  |     +-- _invalidate_entity_entries(gid, event)
  |     |     +-- _hard_invalidate_entity_entries(gid)
  |     |     |     +-- CACHE_TRANSIENT_ERRORS (line 238): log warning, continue
  |     |     +-- _soft_invalidate_entity_entries(gid, event)
  |     |           +-- per-entry loop: BROAD-CATCH (line 292)
  |     |                 +-- fallback: BROAD-CATCH (line 304): last-resort
  |     +-- _invalidate_per_task_dataframes(gid, project_gids)
  |     |     +-- CACHE_TRANSIENT_ERRORS (line 325): log warning
  |     +-- _invalidate_project_dataframes(project_gids)
  |           +-- per-project loop: BROAD-CATCH (line 347)
  |
  +-- _handle_section_mutation(event)
        +-- CACHE_TRANSIENT_ERRORS (line 195): log warning
        +-- _invalidate_project_dataframes(project_gids)
```

#### Partial Failure Safety Assessment

**Verdict: SAFE with one hardening opportunity.**

The three-layer defense (top-level boundary catch, per-entry isolation, per-project isolation) ensures that:

1. A failure invalidating one entry type (TASK, SUBTASKS, DETECTION) does not prevent attempts on the other types.
2. A failure invalidating one project's DataFrame does not prevent attempts on other projects.
3. The soft invalidation path's read-modify-write cycle correctly falls back to hard invalidation on any error.

**Hardening opportunity**: The soft invalidation fallback at line 304 catches bare `Exception` with `pass`. While annotated as BROAD-CATCH, the `pass` swallows the exception entirely after logging. This is correct behavior (last-resort fallback) but the logging could include the error type and message for diagnosability. Currently `exc_info=True` is used, which is sufficient.

**No code changes required for invalidation correctness.**

### 3.2 DataFrameCache.invalidate_project() Analysis

`DataFrameCache.invalidate_project()` delegates to `invalidate()` which removes entries from the memory tier only. S3 entries are "not deleted, just superseded on next write" (comment at line 624). This is a correct design choice -- S3 invalidation would be both expensive and unnecessary since the next `put_async()` will overwrite the stale S3 data.

**Risk**: If the memory tier is cleared but the S3 tier retains a stale entry with a matching schema version, a subsequent `get_async()` after a memory eviction could promote the stale S3 entry back to memory. However, the watermark-based freshness check in `_check_freshness()` would detect this and trigger an SWR refresh, so the system self-heals.

**No code changes required.**

---

## 4. Warm-up Resilience

### 4.1 CacheWarmer (dataframe/warmer.py)

The `CacheWarmer` handles Lambda pre-deployment warming. Current error handling:

- **Strict mode**: Any `CACHE_TRANSIENT_ERRORS` during `_warm_entity_type_async()` raises `RuntimeError` to fail the Lambda warm.
- **Non-strict mode**: Failures are logged and returned as `WarmResult.FAILURE` status objects.
- The `RuntimeError` re-raise at line 244 is correctly placed before `CACHE_TRANSIENT_ERRORS` catch at line 248.

**Assessment: CORRECT.** Warm failures are handled appropriately for both modes. No silent failures.

### 4.2 DataFrameCache SWR Refresh (integration/dataframe_cache.py)

The `_swr_refresh_async()` method (line 928-963) runs as a background `asyncio.create_task`. Its error handling:

```python
except Exception:  # BROAD-CATCH: isolation
    logger.exception("swr_refresh_failed", ...)
    record_swr_refresh(entity_type, "failure")
    await self.release_build_lock_async(..., success=False)
```

**Assessment: CORRECT.** The build lock is always released (via explicit calls in both `except` and `else` branches). The circuit breaker records the failure via `release_build_lock_async(success=False)`.

**Hardening opportunity**: The success path calls `release_build_lock_async(success=True)` but if THIS call raises, the lock is never released. This is extremely unlikely (it's a local method call) but technically a defect. A `finally` block would be more robust.

### 4.3 Hierarchy Warming (providers/unified.py)

`UnifiedTaskStore._fetch_immediate_parents()` uses `asyncio.gather()` with per-parent semaphore-guarded fetches. Each individual fetch catches `CACHE_TRANSIENT_ERRORS` and returns `False`. This is correct -- individual parent failures don't abort the batch.

`_warm_ancestors()` delegates to `warm_ancestors_async()` in hierarchy_warmer.py, which also catches `CACHE_TRANSIENT_ERRORS` per-fetch.

**Assessment: CORRECT.** Pacing support (batch delay) was added per ADR-hierarchy-backpressure-hardening.

### 4.4 Recommended Hardening

1. **SWR build lock guarantee**: Wrap `_swr_refresh_async()` in a `try/finally` for `release_build_lock_async()` instead of relying on `try/except/else`.
2. **Warm-up metrics**: Add a structured log event on warm completion summarizing which entity types succeeded/failed, so operators can distinguish partial warm from full warm.

---

## 5. Unified Store Consistency

### 5.1 UnifiedTaskStore Error Paths

`UnifiedTaskStore` composes three systems:

| Component | Storage | Error Handling |
|---|---|---|
| `cache` (CacheProvider) | Redis/S3 tiered | Catches `CACHE_TRANSIENT_ERRORS`, enters degraded mode |
| `_hierarchy` (HierarchyIndex) | In-memory dict | No I/O errors possible |
| `_freshness` (FreshnessCoordinator) | Asana Batch API | Catches `CACHE_TRANSIENT_ERRORS`, returns "fetch" action |

#### Consistency Scenarios

**Scenario 1: `put_async()` -- cache.set_versioned succeeds, hierarchy.register succeeds**
- Consistent. Normal path.

**Scenario 2: `put_async()` -- cache.set_versioned raises (caught by caller)**
- The caller catches `CACHE_TRANSIENT_ERRORS` from the tiered provider. The hierarchy index is NOT updated (register comes after set_versioned). This is safe -- a stale hierarchy is better than a hierarchy pointing to missing cache entries.

**Scenario 3: `put_batch_async()` -- cache.set_batch succeeds, hierarchy warming fails**
- Hierarchy index has entries registered (line 510, before set_batch), and cache has entries stored (line 516). But parent warming fails. Result: hierarchy may reference parent GIDs that are not in cache. `get_parent_chain_async()` handles this correctly by stopping at the first missing ancestor (line 754).

**Scenario 4: `invalidate()` with `cascade=True` -- cache.invalidate succeeds for root, fails for descendant**
- The loop at line 815 does not catch errors per-descendant. A `CACHE_TRANSIENT_ERRORS` from `cache.invalidate(desc_gid, ...)` would propagate up. Then `hierarchy.remove(gid)` at line 827 would not execute, leaving stale hierarchy entries.

**Scenario 5: `get_batch_async()` -- cache.get_batch returns partial results, freshness check fails**
- FreshnessCoordinator catches `CACHE_TRANSIENT_ERRORS` per-chunk and returns `action="fetch"` for the failed chunk. This is correct -- callers treat unfresh entries as cache misses.

### 5.2 Identified Issues

**Issue 1 (P2): Cascade invalidation is not per-descendant isolated.**

In `UnifiedTaskStore.invalidate()` (line 796), when `cascade=True`, the descendant invalidation loop does not catch per-descendant errors:

```python
if cascade:
    descendant_gids = self._hierarchy.get_descendant_gids(gid)
    for desc_gid in descendant_gids:
        self.cache.invalidate(desc_gid, [EntryType.TASK])  # can raise
```

If `cache.invalidate()` raises for one descendant, remaining descendants are not invalidated, AND `hierarchy.remove(gid)` at line 827 is never called.

**Fix**: Add per-descendant `try/except CACHE_TRANSIENT_ERRORS` with warning log.

**Issue 2 (P3): Hierarchy register before cache write in put_batch_async.**

In `put_batch_async()` (line 510), `hierarchy.register(task)` is called inside the entry-building loop BEFORE `cache.set_batch(entries)` at line 516. If `set_batch` fails, the hierarchy index contains entries that are not in cache. This is a minor inconsistency since `get_parent_chain_async()` handles missing entries gracefully, but it means the hierarchy index can grow unbounded with phantom entries.

**Fix**: Move hierarchy registration to after `set_batch()` succeeds. This is a low-risk reorder.

---

## 6. Sprint Decomposition

### Sprint 1: Unified Store Hardening (4-6 files)

**Objective**: Fix the two identified consistency issues in UnifiedTaskStore and harden the SWR build lock.

**File Manifest**:

| File | Change |
|---|---|
| `src/autom8_asana/cache/providers/unified.py` | (1) Add per-descendant try/except in `invalidate()` cascade loop. (2) Move `hierarchy.register()` to after `set_batch()` in `put_batch_async()`. |
| `src/autom8_asana/cache/integration/dataframe_cache.py` | Refactor `_swr_refresh_async()` to use `try/finally` for build lock release. |
| `tests/unit/cache/providers/test_unified.py` | Add test: cascade invalidation partial failure does not prevent hierarchy cleanup. Add test: put_batch hierarchy registration ordering. |
| `tests/unit/cache/integration/test_dataframe_cache.py` | Add test: SWR refresh build lock released on unexpected error in build callback. |

**Green gate**: 10,575 baseline + new tests, 0 regressions.

### Sprint 2: Observability and Documentation (3-5 files)

**Objective**: Add structured logging for warm-up outcomes, document BROAD-CATCH inventory, and resolve the pre-existing test failure (per ADR-WS2-001 below).

**File Manifest**:

| File | Change |
|---|---|
| `src/autom8_asana/cache/dataframe/warmer.py` | Add structured summary log event at end of `warm_all_async()` including per-entity-type success/failure/skip breakdown (already partially exists at line 282, but add entity_types detail). |
| `tests/unit/dataframes/test_parallel_fetch.py` | Fix `test_cache_errors_logged_as_warnings` -- update assertion to use structured logging verification instead of caplog (per ADR-WS2-001). |
| `docs/design/TDD-WS2-CACHE-RELIABILITY.md` | Update status from DRAFT to APPROVED after implementation. |

**Green gate**: 10,575 baseline + fixed test (net +1 passing), 0 regressions.

### Sprint 3: QA Validation

**Objective**: QA adversary runs full test suite, validates green gate, and confirms no regressions across all cache subpackages.

**QA Scope**:
- Full pytest run: `.venv/bin/pytest tests/ -x -q --timeout=60`
- Targeted cache tests: `.venv/bin/pytest tests/unit/cache/ -v --timeout=60`
- Targeted dataframe tests: `.venv/bin/pytest tests/unit/dataframes/ -v --timeout=60`
- Confirm pre-existing failures are either fixed (test_cache_errors_logged_as_warnings) or still pre-existing (test_adversarial_pacing, test_paced_fetch).

**No file modifications in Sprint 3** -- QA only.

---

## 7. ADR-WS2-001: test_cache_errors_logged_as_warnings

### Context

`tests/unit/dataframes/test_parallel_fetch.py::test_cache_errors_logged_as_warnings` is a pre-existing failure. The test verifies FR-DEGRADE-004 (cache errors logged as warnings) but uses `caplog` to capture log output, which is incompatible with the project's structured logging (`autom8y_log`).

The test is in the `dataframes/` directory, NOT in `cache/`. It tests `ParallelFetcher` behavior when a mock cache provider raises `RedisTransportError`.

### Decision

**Fix in WS2 Sprint 2.** Rationale:

1. The test verifies cache error degradation behavior, which is squarely within WS2's reliability scope.
2. The fix is mechanical (swap caplog assertion for structured log verification or mock-based assertion) and low-risk.
3. Deferring to a later workstream creates indefinite technical debt with no clear owner.
4. Fixing it brings the test suite to a consistent green baseline (10,576 passing, accounting for the +1).

### Consequences

- Sprint 2 takes ownership of a test in `dataframes/`, not `cache/`. This is acceptable because the test validates cache reliability behavior.
- The fix pattern (structured logging assertion) should be consistent with how other tests in the codebase verify log output.

---

## 8. Risk Matrix

| Subpackage | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| providers/unified.py | Cascade invalidation partial failure leaves stale hierarchy | Medium | Low (hierarchy self-heals on next put) | Sprint 1: add per-descendant isolation |
| providers/unified.py | put_batch hierarchy/cache divergence | Low | Low (get_parent_chain handles gracefully) | Sprint 1: reorder registration |
| integration/dataframe_cache.py | SWR build lock leak on unexpected error | Very Low | Medium (lock never released, builds coalesce forever) | Sprint 1: try/finally pattern |
| dataframe/warmer.py | Warm failure diagnosis difficulty | Medium | Low (logs exist but lack summary) | Sprint 2: structured summary |
| dataframes/test_parallel_fetch.py | Pre-existing test failure masks real regressions | High | Low (single test, well-understood root cause) | Sprint 2: fix test |
| All backends | Transport error storm during degraded mode transition | Low | Medium (reconnect attempts are rate-limited by reconnect_interval) | No change needed -- existing backoff is sufficient |
| integration/mutation_invalidator.py | Soft invalidation fallback swallows errors | Low | Very Low (exc_info=True captures stack trace) | No change needed |

---

## 9. Test Strategy

### New Tests (Sprint 1)

| Test | File | What It Validates |
|---|---|---|
| `test_cascade_invalidation_partial_failure` | `tests/unit/cache/providers/test_unified.py` | When `cache.invalidate()` raises for one descendant, other descendants are still invalidated and `hierarchy.remove()` is still called. |
| `test_put_batch_hierarchy_after_cache` | `tests/unit/cache/providers/test_unified.py` | Hierarchy registration occurs after `set_batch()` succeeds. If `set_batch()` raises, hierarchy is not polluted with phantom entries. |
| `test_swr_build_lock_released_on_error` | `tests/unit/cache/integration/test_dataframe_cache.py` | When `_build_callback` raises an unexpected error, the build lock is still released via `release_build_lock_async(success=False)`. |

### Modified Tests (Sprint 2)

| Test | File | Change |
|---|---|---|
| `test_cache_errors_logged_as_warnings` | `tests/unit/dataframes/test_parallel_fetch.py` | Replace `caplog` assertion with structured logging verification compatible with `autom8y_log`. |

### Existing Tests Affected

No existing tests should break. All changes are additive (new error handling paths) or reordering (hierarchy registration). The green gate of 10,575 must hold through Sprint 1 and improve to 10,576+ through Sprint 2.

### Test Mock Compatibility

Per WS1/I4-S1 lessons: test mocks in this codebase use `side_effect=ConnectionError(...)` or `side_effect=RedisTransportError(...)`, NOT bare `side_effect=Exception(...)`. All existing catch sites are compatible with these mock patterns. No mock updates are required.

---

## 10. Out of Scope

The following are explicitly NOT in WS2 scope:

1. **Cache architecture redesign**: The tier organization (Tier 0-3, Backends) is stable. No new abstractions.
2. **New error types**: The exception hierarchy in `core/exceptions.py` is complete for cache use cases.
3. **Exception narrowing sprint**: The audit (Section 2) found zero sites needing narrowing.
4. **WS3 traversal consolidation**: CascadeViewPlugin integration with UnifiedTaskStore is deferred to WS3.
5. **Performance optimization**: No profiling or latency work.
6. **Backend-level reconnection changes**: The existing `should_attempt_reconnect()` / `reconnect_interval` pattern is sufficient.

---

## Appendix A: File Manifest Summary

### Files Modified in WS2

| Sprint | File | Lines Changed (est.) |
|---|---|---|
| S1 | `src/autom8_asana/cache/providers/unified.py` | ~20 |
| S1 | `src/autom8_asana/cache/integration/dataframe_cache.py` | ~10 |
| S1 | `tests/unit/cache/providers/test_unified.py` | ~80 (new tests) |
| S1 | `tests/unit/cache/integration/test_dataframe_cache.py` | ~40 (new test) |
| S2 | `src/autom8_asana/cache/dataframe/warmer.py` | ~10 |
| S2 | `tests/unit/dataframes/test_parallel_fetch.py` | ~15 |

**Total**: 6 files, ~175 lines changed.

### Files NOT Modified (confirmed clean by audit)

All 29 cache files not listed above require zero changes. The exception audit confirms full coverage.

---

## Appendix B: Design References

| Document | Relevance to WS2 |
|---|---|
| `docs/design/TDD-exception-hierarchy.md` | Error tuple architecture, BROAD-CATCH taxonomy |
| `docs/design/TDD-cache-invalidation-pipeline.md` | MutationInvalidator design, fire-and-forget pattern |
| `docs/design/TDD-cache-freshness-remediation.md` | SWR grace window, LKG serve policy |
| `docs/design/TDD-unified-progressive-cache.md` | ProgressiveTier, dual-location fix |
| `docs/design/TDD-dataframe-cache.md` | DataFrameCache tiered storage design |
| `docs/spikes/SPIKE-deferred-todo-triage.md` | CascadeViewPlugin context for UnifiedTaskStore (WS3) |
| `.claude/wip/WS2-CHECKPOINT.md` | WS2 coordination checkpoint |
| `.claude/wip/TODO.md` | WS2/WS3 scope boundaries |
