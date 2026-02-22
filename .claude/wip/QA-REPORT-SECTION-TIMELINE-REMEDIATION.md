# Test Summary: Section Timeline Architecture Remediation

## Overview
- **Test Period**: 2026-02-20
- **Tester**: QA Adversary
- **Build/Version**: main branch, post-implementation of TDD-SECTION-TIMELINE-REMEDIATION

## Results Summary

| Category | Pass | Fail | Blocked | Not Run |
|----------|------|------|---------|---------|
| Acceptance Criteria (SC-1 through SC-8) | 8 | 0 | 0 | 0 |
| Edge Cases (EC-1 through EC-8) | 8 | 0 | 0 | 0 |
| New Unit Tests | 55 | 0 | 0 | 0 |
| Regression (Full Suite) | 10,739 | 0 | 0 | 0 |
| Code Quality Checks | 7 | 0 | 0 | 0 |

**Total**: 10,817 pass, 0 fail, 46 skipped (pre-existing), 2 xfailed (pre-existing)

---

## Success Criteria Validation

### SC-1: Endpoint responds without warm-up pipeline PASS

**Verification method**: Code inspection of `lifespan.py` (lines 250-253) + endpoint test.

The warm-up pipeline (`_warm_section_timeline_stories`, `warm_story_caches`, `build_all_timelines`) has been completely removed from `lifespan.py`. Lines 250-253 contain only a comment confirming the removal. The endpoint handler (`section_timelines.py`) calls `get_or_compute_timelines()` which computes on demand from the cache layer. No startup-time I/O for timeline purposes.

**Evidence**: `TestSuccessResponse.test_200_returns_timelines` passes. `TestCacheHitPath.test_returns_entries_from_cached_timelines` confirms the endpoint works with derived cache alone. No warm-up code exists in `src/`.

### SC-2: No app.state keys for timeline data PASS

**Verification method**: `grep` for `app.state.offer_timelines`, `timeline_warm_count`, `timeline_total`, `timeline_warm_failed` in `src/`.

All four `app.state` keys have been removed. Zero references found in `src/`. The endpoint no longer takes a `Request` parameter and has no `app.state` access.

**Evidence**: Grep returns zero matches for all four keys in `src/`.

### SC-3: Unit timelines with UNIT_CLASSIFIER, zero new code PASS

**Verification method**: Code inspection + test.

`get_or_compute_timelines()` accepts `(project_gid, classifier_name)` as parameters. The `CLASSIFIERS` dict resolves `"unit"` to `UNIT_CLASSIFIER`. `_is_cross_project_noise()` and `_build_intervals_from_stories()` both accept `classifier: SectionClassifier` parameter. No entity-specific code paths exist.

**Evidence**: `TestGenericParameterization.test_unit_classifier` passes -- unit timelines work by passing `classifier_name="unit"`. `TestGenericParameterization.test_different_classifiers_use_different_cache_keys` confirms independent cache keys.

### SC-4: Zero additional Asana API calls for cached entities PASS

**Verification method**: Code inspection + test.

`read_cached_stories()` calls only `cache.get_versioned()` -- no fetcher parameter, no API call capability by design. `read_stories_batch()` calls only `cache.get_batch()`. The only API call in the compute path is `tasks.list_async()` for enumeration (once per request on cache miss, not per-entity).

**Evidence**: `TestReadCachedStories.test_does_not_modify_cache` confirms no writes. `TestCacheHitPath.test_returns_entries_from_cached_timelines` confirms no task enumeration or batch read on cache hit.

### SC-5: Cold derived cache with warm story cache returns valid response PASS

**Verification method**: Test of cache miss path.

When derived cache misses, `get_or_compute_timelines()` enumerates tasks, batch-reads cached stories, builds timelines from them, stores the derived entry, and returns computed results.

**Evidence**: `TestCacheMissPath.test_enumerates_tasks_on_miss` exercises the full cold-derived-warm-stories path and verifies task enumeration, batch read, store, and result return.

### SC-6: Both caches cold degrades gracefully PASS

**Verification method**: Test of double-miss path.

When both derived and story caches are cold, `get_or_compute_timelines()` imputes timelines from task enumeration data (created_at + current section). Returns partial results, not 500/503.

**Evidence**: `TestCacheMissPath.test_cache_miss_with_no_stories_imputes` verifies imputation. `TestSuccessResponse.test_200_empty_timelines` verifies the endpoint returns 200 with empty list (not 503).

### SC-7: Existing callers of load_stories_incremental() unaffected PASS

**Verification method**: Code inspection + regression tests.

`load_stories_incremental()` contract is unchanged. `read_cached_stories()` and `read_stories_batch()` are new additive functions that do not modify `load_stories_incremental()`. The `max_cache_age_seconds` parameter remains intact. `build_timeline_for_offer()` still calls `list_for_task_cached_async()` with `max_cache_age_seconds=7200`.

**Evidence**: Full test suite passes (10,739 tests). `tests/unit/cache/test_stories.py` (existing tests for `load_stories_incremental`) all pass.

### SC-8: max_cache_age_seconds status confirmed PASS (retained, not removed)

**Verification method**: `grep` in `src/`.

`max_cache_age_seconds` is still present in:
- `stories.py:107` (parameter definition)
- `section_timeline_service.py:299` (usage in `build_timeline_for_offer`)
- `clients/stories.py:348,419` (passthrough)

**Status**: FR-7 was SHOULD priority. The parameter remains because `build_timeline_for_offer()` still uses it. This is the correct outcome per the TDD Section 6.4 risk note: "If any caller is discovered during implementation, defer removal." The parameter is harmless when unused (defaults to None). This is a documented deferral, not a defect.

---

## Edge Case Validation

### EC-1: Cold derived, warm stories -> compute on demand PASS

Tested by `TestCacheMissPath.test_enumerates_tasks_on_miss`. Derived cache miss triggers full computation from cached stories.

### EC-2: Both cold -> partial/empty results PASS

Tested by `TestCacheMissPath.test_cache_miss_with_no_stories_imputes` (imputation path) and `TestSuccessResponse.test_200_empty_timelines` (endpoint returns 200, not 500/503).

### EC-3: Concurrent first-request -> lock prevents thundering herd PASS

Tested by `TestLockRecheck.test_second_request_finds_cache_after_lock`. Simulates the pattern where first call misses cache before lock, second call finds cache after lock. Confirms `store_derived_timelines` is not called (no redundant computation).

Code inspection confirms `_computation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)` pattern is correctly implemented at module level.

### EC-4: Story updated after derived cached -> stale until TTL PASS

Verified by design inspection. `DerivedTimelineCacheEntry` has `ttl=300` (5 minutes). No invalidation coupling between story writes and derived entries. Per ADR-0147, this is the intended behavior.

### EC-5: Partial batch hit -> mix of hits and misses PASS

Tested by `TestReadStoriesBatch.test_mix_of_hits_and_misses`. Returns hits as story lists and misses as None. The service layer (`get_or_compute_timelines` lines 457-521) handles both paths: stories present -> build intervals, stories None -> impute.

### EC-6: Entity with zero stories -> impute if data available PASS

Tested by `TestCacheMissPath.test_cache_miss_with_no_stories_imputes`. When `raw_stories is None` and `task_created_at is not None and section_name is not None`, the code builds an imputed interval.

### EC-7: New entity after derived built -> next TTL cycle PASS

Verified by design inspection. Derived cache has TTL=300s. After expiry, next request triggers full recomputation with fresh task enumeration, which includes new entities.

### EC-8: Large project -> chunked batch reads PASS

Tested by `TestReadStoriesBatch.test_chunking_splits_large_batch` (7 keys, chunk_size=3 -> 3 chunks) and `TestReadStoriesBatch.test_large_batch_over_500` (600 keys, default chunk_size=500 -> 2 chunks). Chunking logic verified at both sub-default and super-default sizes.

---

## Code Quality Checks

| Check | Result | Evidence |
|-------|--------|----------|
| No `app.state.offer_timelines` in src/ | PASS | grep returns 0 matches |
| No `_check_readiness` or readiness gate constants | PASS | grep returns 0 matches |
| No `warm_story_caches` or `build_all_timelines` | PASS | grep returns 0 matches |
| `_is_cross_project_noise` accepts classifier parameter | PASS | Line 107: `classifier: SectionClassifier \| None = None` |
| `_build_intervals_from_stories` accepts classifier parameter | PASS | Line 161: `classifier: SectionClassifier \| None = None` |
| `DerivedTimelineCacheEntry.__init_subclass__` registration | PASS | `TestDerivedTimelineRegistration.test_registered_in_type_registry` passes |
| Serialization round-trip preserves all data | PASS | 9 round-trip tests pass (all field types, nulls, empties) |
| Lock uses `defaultdict(asyncio.Lock)` pattern | PASS | Line 47: `_computation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)` |

---

## Test Files Written

| File | Tests | Description |
|------|-------|-------------|
| `tests/unit/cache/test_derived_cache.py` (NEW) | 22 | Key format, serialization round-trip, cache hit/miss, store, entry round-trip, registration |
| `tests/unit/cache/test_stories_batch.py` (NEW) | 13 | read_cached_stories hit/miss, read_stories_batch empty/hits/misses/chunking |
| `tests/unit/services/test_get_or_compute_timelines.py` (NEW) | 13 | Cache hit/miss paths, lock re-check, error cases, generic parameterization |
| `tests/unit/api/test_routes_section_timelines.py` (UPDATED) | 7 | 200 success, 422 validation, 502 upstream error |
| **Total new tests** | **55** | |

---

## Defects Found

None.

---

## Risk Areas

### R-1: max_cache_age_seconds Retained (Low Risk)

`max_cache_age_seconds` remains in the codebase because `build_timeline_for_offer()` still passes it. This function is used by the original per-offer story fetch path, which is retained for backward compatibility. The parameter defaults to `None` (no-op) when not explicitly passed, so it causes no harm.

**Recommendation**: File as follow-on work item per FR-7. No action needed for this release.

### R-2: _computation_locks Memory Growth (Low Risk)

`_computation_locks` is a `defaultdict(asyncio.Lock)` that grows unboundedly. Each unique `(project_gid, classifier_name)` pair creates a new key. In practice, there are only 2 classifiers (offer, unit) and a small number of projects, so growth is bounded. However, there is no cleanup mechanism.

**Recommendation**: Acceptable for current scale. If the number of projects grows significantly, consider LRU eviction.

### R-3: S3 Fallback for get_batch is Sequential (Known, Accepted)

Per TDD Risk R-2: S3 `get_batch` falls back to sequential per-key reads. Redis is the hot tier, so S3 fallback is rare after Lambda warmer runs. Chunk size of 500 limits worst-case. Accepted per architecture decision.

### R-4: build_timeline_for_offer Still Uses API-Call Path (Informational)

`build_timeline_for_offer()` at line 266 still calls `client.stories.list_for_task_cached_async()` with `max_cache_age_seconds=7200`. This function is NOT used by `get_or_compute_timelines()` (which uses the pure-read batch path). It remains for the original single-offer timeline use case. No defect -- just documenting that two paths exist.

---

## Documentation Impact Assessment

No user-facing changes to commands, APIs, or deprecation of functionality. The HTTP endpoint contract (`GET /api/v1/offers/section-timelines`) is identical -- same path, same query parameters, same response format. The only behavioral change is:
- Removed: 503 TIMELINE_NOT_READY and 503 TIMELINE_WARM_FAILED responses
- Added: 200 with empty/partial results when caches are cold (graceful degradation)

This is a behavioral improvement (no more 503 during startup) that does not require documentation updates.

---

## Release Recommendation

**GO**

**Rationale**:
1. All 8 acceptance criteria (SC-1 through SC-8) are verified and passing.
2. All 8 edge cases (EC-1 through EC-8) are verified and passing.
3. 55 new unit tests cover all identified gaps with 100% pass rate.
4. Full regression suite (10,739 tests) passes with zero failures.
5. All old warm-up infrastructure is cleanly removed -- no stale references.
6. Code quality checks (7/7) pass.
7. No defects found during adversarial testing.
8. Known risks are all Low severity and documented.

The implementation faithfully matches the TDD specification and satisfies all PRD requirements. The compute-on-read-then-cache architecture eliminates the warm-up pipeline, `app.state` dependency, and readiness gates while maintaining backward compatibility with existing callers.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| QA Report (this document) | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/QA-REPORT-SECTION-TIMELINE-REMEDIATION.md` | Written |
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-SECTION-TIMELINE-REMEDIATION.md` | Read-verified |
| TDD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-SECTION-TIMELINE-REMEDIATION.md` | Read-verified |
| stories.py (Gap 1 + Gap 4) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py` | Read-verified |
| derived.py (Gap 3) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` | Read-verified |
| entry.py (EntryType + subclass) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/entry.py` | Read-verified |
| section_timeline_service.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` | Read-verified |
| section_timelines.py (endpoint) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py` | Read-verified |
| lifespan.py (warm-up removed) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py` | Read-verified |
| test_derived_cache.py (NEW) | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/cache/test_derived_cache.py` | Written, 22 tests pass |
| test_stories_batch.py (NEW) | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/cache/test_stories_batch.py` | Written, 13 tests pass |
| test_get_or_compute_timelines.py (NEW) | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/services/test_get_or_compute_timelines.py` | Written, 13 tests pass |
| test_routes_section_timelines.py (UPDATED) | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/api/test_routes_section_timelines.py` | Updated, 7 tests pass |
