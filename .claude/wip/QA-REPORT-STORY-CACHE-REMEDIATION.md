# QA Report: Story Cache Remediation

## Overview
- **Test Period**: 2026-02-20
- **Tester**: QA Adversary
- **Build/Version**: Commits `41dd3a5`, `4e64cde`, `67d668a` on main
- **Scope**: Lambda story warming, bounded self-healing, modified_at probe, DELETE-only invalidation

## Test Execution

All 82 unit tests pass (0 failures, 0 errors, 0.29s).

---

## Area 1: Lambda Story Warming

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py` (lines 235-395)

### TC-001: Duplicate GIDs in DataFrame

**Verdict**: PASS (by design, acceptable)

If a DataFrame contains duplicate task GIDs (e.g., `["task-1", "task-1", "task-2"]`), the function will call `list_for_task_cached_async` twice for `task-1`. Because `list_for_task_cached_async` uses `max_cache_age_seconds=7200`, the second call will be a cache hit (no API call). The `total_tasks` stat will be inflated (3 instead of 2) but this is purely cosmetic in CloudWatch metrics. No data corruption, no runtime error. The overhead is one redundant cache read per duplicate -- trivial.

**Risk**: LOW. Cosmetic metric inflation only.

### TC-002: Empty DataFrame (zero rows)

**Verdict**: PASS

When a DataFrame has a `gid` column but zero rows, `df["gid"].to_list()` returns `[]`. The `range(0, 0, 100)` loop produces zero iterations. The function proceeds to the next entity type cleanly. `total_tasks` stays 0 for that entity. Tested implicitly by `test_empty_completed_entities_is_noop`.

### TC-003: DataFrame entry is None vs DataFrame.dataframe is None

**Verdict**: PASS

Line 287: `if entry is None or entry.dataframe is None: continue` -- both cases handled. Tested by `test_skips_entity_with_no_dataframe`.

### TC-004: Timeout detection granularity

**Verdict**: PASS (with observation)

Timeout is checked at chunk boundaries (every 100 tasks). In the worst case, up to 100 concurrent `list_for_task_cached_async` calls may be in-flight when timeout triggers on the *next* chunk boundary. Given Semaphore(3), at most 3 are truly concurrent at any moment; the `asyncio.gather` for the current 100-task chunk will complete before the timeout check runs again. This is bounded and acceptable.

**Observation**: If a single `list_for_task_cached_async` call hangs (e.g., Asana API timeout), the current chunk's `asyncio.gather` will block until that call completes or its own timeout fires. There is no per-call timeout. The Lambda's global timeout is the backstop. This is by design (Strategy E: piggyback, best-effort).

### TC-005: Closure variable capture in _warm_story

**Verdict**: PASS

Line 299: `async def _warm_story(task_gid: str, _et: str = entity_type) -> bool:` uses a default argument `_et` to capture `entity_type` at definition time. This is the correct Python pattern for closure variable capture in loops. The `task_gid` parameter is passed directly by the caller. No late-binding bug.

### TC-006: Triple-layered isolation

**Verdict**: PASS

- **Per-task**: Lines 308-318, `except Exception` inside `_warm_story` catches individual failures.
- **Per-entity**: Lines 350-360, `except Exception` catches entity-level failures (e.g., `get_async` fails).
- **Fatal**: Lines 382-394, outermost `except Exception` catches anything unexpected.

All three layers return/continue without raising. The function always returns a `dict`.

### TC-007: Test coverage for Lambda warming

**Verdict**: PASS

10 tests covering: happy path (all GIDs), timeout exit, failure isolation, no DataFrame, no GID column, no project GID, CloudWatch metrics, empty entities, fatal error, multiple entities. Good coverage.

**Gap identified (LOW severity)**: No test for duplicate GIDs in DataFrame. Acceptable -- the behavior is trivially correct (cache hit on second call).

---

## Area 2: Self-Healing Concurrency

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` (lines 440-485)

### TC-008: Race condition between inline fetch and concurrent requests

**Verdict**: PASS (by design)

The entire computation (including self-healing) runs inside the `async with lock:` block (line 408). A second concurrent request for the same (project_gid, classifier_name) will wait on the lock, then find the derived cache populated by the first request (lock re-check at line 410). The inline fetch is serialized by the lock. No race condition.

### TC-009: Self-healing threshold boundary (exactly 50 misses)

**Verdict**: PASS

Line 447: `if 0 < len(misses) <= MAX_INLINE_STORY_FETCHES:` -- exactly 50 misses triggers inline fetch. 51 misses does not. This is correct per the spec.

### TC-010: Self-healing with all fetches failing

**Verdict**: PASS

Lines 453-458: Each `_fetch_story` has `except Exception: logger.warning(...)`. If all 50 inline fetches fail, the re-read batch (line 463) will still show all misses. The function proceeds to build timelines with imputation for missing stories. No crash, no unhandled exception. Tested by `test_inline_fetch_failure_is_caught_per_task`.

### TC-011: Semaphore(5) vs Semaphore(3) discrepancy

**Verdict**: PASS (intentional design difference)

Lambda warming uses `Semaphore(3)` (line 276) -- conservative for Lambda's constrained environment. Self-healing uses `Semaphore(5)` (line 448) -- higher concurrency acceptable since it's request-time on ECS with more resources, and the max is 50 tasks.

### TC-012: Test coverage for self-healing

**Verdict**: PASS

4 tests: zero misses (no fetch), below threshold (triggers fetch + re-read), above threshold (logs warning, no fetch), fetch failure caught. Good boundary coverage.

**Gap identified (LOW severity)**: No test for exactly 50 misses (boundary value). The `<= 50` condition is tested implicitly by the below-threshold test (2 misses), but not at the exact boundary.

---

## Area 3: modified_at Probe Correctness

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py` (lines 157-166)

### TC-013: current_modified_at is None

**Verdict**: PASS

Line 160: `if current_modified_at is not None and cached_entry.is_stale(current_modified_at):` -- when `current_modified_at` is `None`, the entire condition short-circuits to `False`. Execution falls through to the `elif max_cache_age_seconds` branch. This preserves the existing behavior exactly. Tested by `test_modified_at_probe_no_change_when_none`.

### TC-014: Stale entry bypasses max_cache_age_seconds

**Verdict**: PASS

When `is_stale()` returns `True`, the `pass` at line 161 falls through to the incremental fetch at line 169. The `since` cursor (from `last_fetched` metadata) is preserved -- the fetcher is called with `(task_gid, last_fetched)`, NOT `(task_gid, None)`. Tested by `test_modified_at_probe_bypasses_max_age_when_stale` and `test_incremental_fetch_uses_since_cursor`.

### TC-015: Edge case -- cached version equals current_modified_at

**Verdict**: PASS

`is_current()` returns `True` when `cached_version >= current_version`. So if they're equal, `is_stale()` returns `False`, and the `max_cache_age_seconds` check proceeds normally. This is correct -- same version means no mutation occurred. Tested by `test_modified_at_probe_allows_age_skip_when_current`.

### TC-016: Edge case -- malformed current_modified_at string

**Verdict**: PASS (with observation)

`is_stale()` calls `is_current()` which calls `_parse_datetime(current_version)`. If `current_modified_at` is a non-parseable string, `_parse_datetime` will raise `ValueError`. This propagates up through `load_stories_incremental`. However, `current_modified_at` comes from Asana's `task.modified_at` field, which is always ISO 8601 or `None`. A malformed string would indicate a deeper upstream bug. Acceptable risk.

### TC-017: Edge case -- cached_entry has no cached_at

**Verdict**: PASS

Line 162: `elif max_cache_age_seconds is not None and cached_entry.cached_at is not None:` -- if `cached_at` is `None`, both conditions must be true for the age check. When `cached_at` is `None`, the branch is skipped and execution falls through to the incremental fetch. This is the safe behavior -- if we don't know when it was cached, fetch fresh.

### TC-018: Test coverage for modified_at probe

**Verdict**: PASS

4 tests: stale bypasses max_age, None preserves behavior, current allows skip, since cursor preserved. Excellent coverage of the key scenarios.

---

## Area 4: DELETE-Only Story Invalidation

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py` (lines 155-165)

### TC-019: DELETE correctly invalidates stories

**Verdict**: PASS

Lines 158-165: `if event.mutation_type == MutationType.DELETE:` triggers `self._cache.invalidate(gid, [EntryType.STORIES])`. Tested by `test_delete_mutation_invalidates_stories`.

### TC-020: UPDATE does NOT invalidate stories

**Verdict**: PASS

The `if` condition on line 158 only matches DELETE. UPDATE falls through without touching stories. Tested by `test_update_mutation_does_not_invalidate_stories`.

### TC-021: MOVE does NOT invalidate stories

**Verdict**: PASS

MOVE is not DELETE, so stories are preserved. This is correct -- a section move generates a new story (section_changed) which will be picked up by the next incremental fetch via the `since` cursor. Tested by `test_move_mutation_does_not_invalidate_stories`.

### TC-022: Should CREATE invalidate stories?

**Verdict**: PASS (correct as-is)

CREATE represents a brand new task. A newly created task has zero stories, so there's nothing in the story cache to invalidate. Even if by some race condition a story cache entry existed for a GID that was reused (Asana GIDs are not reused), the next `load_stories_incremental` call would do a full fetch (cache miss) or incremental fetch that picks up everything. No risk.

### TC-023: Should ADD_MEMBER / REMOVE_MEMBER invalidate stories?

**Verdict**: PASS (correct as-is)

Adding/removing a task from a project does not change the task's story history. Stories are per-task, not per-project-membership. The incremental story fetch uses the `since` cursor against the task GID, which is unaffected by project membership changes. Preserving the story cache is correct.

### TC-024: Story invalidation failure isolation

**Verdict**: PASS

Lines 161-165: `except CACHE_TRANSIENT_ERRORS as exc: logger.warning(...)` -- story invalidation failure is caught and logged. The outer `except Exception` at line 112 is also present as a backstop. Tested by `test_story_invalidation_failure_does_not_propagate`.

### TC-025: _TASK_ENTRY_TYPES does NOT include STORIES

**Verdict**: PASS (critical design decision)

Line 36: `_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]`. STORIES is deliberately excluded to preserve the `since` cursor. The DELETE-specific branch at line 158 handles the only case where story removal is correct (structural garbage cleanup). This is the correct design.

### TC-026: Test coverage for DELETE-only invalidation

**Verdict**: PASS

4 tests: DELETE invalidates, UPDATE does not, MOVE does not, failure does not propagate. Covers the essential matrix.

**Gap identified (LOW severity)**: No explicit test for CREATE and ADD_MEMBER/REMOVE_MEMBER not invalidating stories. These are implicitly covered by the fact that the code only has a DELETE branch, but explicit tests would strengthen confidence.

---

## Area 5: Error Isolation

### TC-027: Lambda story warming never fails the overall warmer

**Verdict**: PASS

`_warm_story_caches_for_completed_entities` is called at line 893 in `_warm_cache_async`. It is called *after* the entity warming loop completes and `all_success` is determined. Its return value (stats dict) is not used to influence the WarmResponse success field. Even if it raises (caught by the outermost except at line 382), the Lambda warmer would catch it and return an error response -- but this won't happen because the function has its own triple-layer isolation.

### TC-028: Self-healing never fails the timeline computation

**Verdict**: PASS

The inline fetch loop at lines 450-458 catches `Exception` per-task. Even if all fetches fail, the function proceeds to build timelines. The only failure that propagates is task enumeration (line 424: `raise`), which is correct -- if we can't enumerate tasks, we can't compute timelines.

### TC-029: modified_at probe never corrupts cache

**Verdict**: PASS

The probe only affects *whether* an API call is made. The cache write path (lines 169-180) is the same regardless of whether the probe triggered or the age check triggered. The `since` cursor is always preserved because the fetcher receives `last_fetched` (not `None`).

---

## Area 6: Test Coverage Gaps

### Summary of gaps identified

| Gap | Severity | Area | Description |
|-----|----------|------|-------------|
| GAP-001 | LOW | Lambda warming | No test for duplicate GIDs in DataFrame |
| GAP-002 | LOW | Self-healing | No test for exactly 50 misses (boundary) |
| GAP-003 | LOW | Invalidation | No explicit test for CREATE/ADD_MEMBER not invalidating stories |
| GAP-004 | LOW | Lambda warming | No test for per-call timeout (single hung API call) |
| GAP-005 | LOW | Self-healing | No test verifying `_computation_locks` dict grows unboundedly |

### GAP-005 detail (memory leak potential)

`_computation_locks` at line 47 is a `defaultdict(asyncio.Lock)` at module scope. Each unique `(project_gid, classifier_name)` pair creates a new entry that is never evicted. With the current deployment (small number of project/classifier combos), this is not a concern. But if the function were called with user-supplied project GIDs, it could grow unboundedly. Current risk: NONE (project GIDs are from a fixed registry).

---

## Results Summary

| Category | Pass | Fail | Blocked | Not Run |
|----------|------|------|---------|---------|
| Lambda Story Warming (TC-001 to TC-007) | 7 | 0 | 0 | 0 |
| Self-Healing Concurrency (TC-008 to TC-012) | 5 | 0 | 0 | 0 |
| modified_at Probe (TC-013 to TC-018) | 6 | 0 | 0 | 0 |
| DELETE-Only Invalidation (TC-019 to TC-026) | 8 | 0 | 0 | 0 |
| Error Isolation (TC-027 to TC-029) | 3 | 0 | 0 | 0 |
| **Total** | **29** | **0** | **0** | **0** |

## Critical Defects

None found.

## Known Issues (acceptable for release)

1. **Duplicate GIDs in DataFrame** cause redundant (but harmless) cache reads and inflated CloudWatch metric counts. LOW severity, cosmetic only.
2. **No per-call timeout** on `list_for_task_cached_async` in Lambda warming. Lambda global timeout is the backstop. Acceptable for Strategy E (best-effort piggyback).
3. **`_computation_locks` dict grows monotonically**. Not a concern with current fixed registry, but would need a TTL-eviction strategy if project GIDs became dynamic.

## Release Recommendation

**GO**

The implementation is solid across all four components. Error isolation is thorough (triple-layered in Lambda, per-task in self-healing, fault-tolerant in invalidation). The modified_at probe correctly preserves the `since` cursor while detecting staleness. The DELETE-only invalidation design is correct -- no other mutation types should invalidate story cache entries.

The 5 test coverage gaps identified are all LOW severity and represent defense-in-depth improvements, not functional risks. The existing 82 tests provide strong coverage of happy paths, error paths, boundary conditions, and concurrency scenarios.

No critical or high severity defects found. No security vulnerabilities. No data corruption risks.

## Documentation Impact

No user-facing behavior changes. No API contract changes. No deprecations. Internal cache behavior changes are transparent to callers.

## Not Tested

- **Integration/E2E**: No integration test run against live Asana API or real S3/Redis. This is expected for unit-level QA.
- **Performance under load**: No benchmark of Lambda warming with 3,800+ tasks. Mitigated by the existing production data point (3,769 offers, <1.5s) from the SectionTimeline feature launch.
- **CloudWatch metric accuracy**: Metric emission is mocked in all tests. Verified structurally (correct metric names emitted) but not end-to-end.
