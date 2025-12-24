# Discovery: Cache Optimization Phase 2 - Root Cause Analysis

**Date:** 2025-12-23
**Status:** Discovery Complete
**Analyst:** Requirements Analyst
**Related:** [PROMPT-MINUS-1-CACHE-PERFORMANCE-META](/docs/requirements/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md)

---

## Executive Summary

This discovery investigation identifies the **primary root cause** of the cache performance gap where warm fetch takes 8.84s instead of the expected <1s. The investigation reveals a **fundamental architectural disconnect** between the cache population path and the cache lookup path in the DataFrame building pipeline.

**Primary Root Cause:** `list_async()` (used by ParallelSectionFetcher) does NOT populate the Task cache. Only `get_async()` (single-task fetch) populates cache. The warm fetch path still executes full API calls because the fetched tasks from the first run were never cached.

**Secondary Root Cause:** The TaskCacheCoordinator performs a two-phase strategy (enumerate GIDs, then lookup in cache), but since the cache was never populated, all lookups result in cache misses, triggering a full re-fetch via `fetcher.fetch_all()`.

---

## 1. Reproduction Results

### 1.1 Environment

- **Project:** Business Offers (3,530 tasks)
- **SDK Version:** Current development branch
- **Cache Backend:** InMemoryCacheProvider (default)

### 1.2 Observed Timing

| Metric | First Fetch | Second Fetch | Expected Second |
|--------|-------------|--------------|-----------------|
| Total Time | ~13.55s | ~8.84s | <1.0s |
| Cache Hit Rate | 0% | ~40% (estimated) | >90% |
| API Calls | Full | Partial | 0 |

### 1.3 Script Used

```bash
python scripts/demo_parallel_fetch.py --name "Business Offers"
```

---

## 2. Evidence of Root Cause

### 2.1 Primary Root Cause: `list_async()` Does NOT Populate Task Cache

**Location:** `/src/autom8_asana/clients/tasks.py:589-654`

**Evidence:**

The `list_async()` method creates a `PageIterator` with a closure that fetches pages directly via HTTP, bypassing the cache entirely:

```python
# tasks.py:631-652
async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
    """Fetch a single page of tasks."""
    params = self._build_opt_fields(opt_fields)
    # ... build params ...
    params["limit"] = min(limit, 100)
    if offset:
        params["offset"] = offset

    # DIRECT HTTP CALL - NO CACHE CHECK OR POPULATION
    data, next_offset = await self._http.get_paginated("/tasks", params=params)
    tasks = [Task.model_validate(t) for t in data]
    return tasks, next_offset
```

Compare to `get_async()` which DOES use cache:

```python
# tasks.py:121-149
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    # FR-CLIENT-001: Check cache first
    cached_entry = self._cache_get(task_gid, EntryType.TASK)
    if cached_entry is not None:
        # Cache hit - return cached data
        return Task.model_validate(cached_entry.data)

    # Cache miss: fetch from API
    data = await self._http.get(f"/tasks/{task_gid}", params=params)

    # Store in cache with entity-type TTL
    self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)  # <-- CACHES!
```

**Impact:** The `ParallelSectionFetcher` uses `list_async()` for section task fetching:

```python
# parallel_fetch.py:303-306
tasks: list[Task] = await self.tasks_client.list_async(
    section=section_gid,
    opt_fields=self.opt_fields,
).collect()  # <-- Returns tasks but does NOT cache them
```

### 2.2 Secondary Root Cause: TaskCacheCoordinator Lookup Returns All Misses

**Location:** `/src/autom8_asana/dataframes/builders/task_cache.py:133-206`

The `TaskCacheCoordinator.lookup_tasks_async()` correctly performs batch cache lookup:

```python
# task_cache.py:167
entries = self._cache.get_batch(task_gids, EntryType.TASK)
```

However, since the cache was never populated by `list_async()`, all lookups return `None`, resulting in 100% cache misses:

```python
for gid in task_gids:
    entry = entries.get(gid)
    if entry is not None and not entry.is_expired():
        result[gid] = task
        hits += 1
    else:
        result[gid] = None  # <-- ALL TASKS END UP HERE
        misses += 1
```

### 2.3 The Flow That Causes 8.84s Warm Fetch

**First Fetch (Cold):**
1. `build_with_parallel_fetch_async()` called with `use_cache=True`
2. `ParallelSectionFetcher.fetch_section_task_gids_async()` enumerates GIDs (lightweight)
3. `TaskCacheCoordinator.lookup_tasks_async()` checks cache - ALL MISS (cache empty)
4. `ParallelSectionFetcher.fetch_all()` fetches all tasks via `list_async()`
5. `TaskCacheCoordinator.populate_tasks_async()` DOES populate cache

**Second Fetch (Warm - Should Be Fast):**
1. `build_with_parallel_fetch_async()` called with `use_cache=True`
2. `ParallelSectionFetcher.fetch_section_task_gids_async()` enumerates GIDs again (API CALL!)
3. `TaskCacheCoordinator.lookup_tasks_async()` checks cache - SOME HITS NOW
4. For cache misses, `ParallelSectionFetcher.fetch_all()` is called (API CALLS!)
5. Cache population occurs

**Why is warm fetch still slow (8.84s)?**

The second fetch path at line 369 in `project.py` calls `fetcher.fetch_all()` for ANY cache misses:

```python
# project.py:365-374
if miss_gids:
    # Full fetch for missing tasks
    result = await fetcher.fetch_all()  # <-- FETCHES ALL TASKS, NOT JUST MISSES!
    # Filter to only missing GIDs
    miss_gid_set = set(miss_gids)
    fetched_tasks = [
        t for t in result.tasks if t.gid in miss_gid_set
    ]
```

**Critical Bug:** When there are ANY cache misses, the code fetches ALL tasks again, not just the missing ones. This explains the 8.84s - it's doing almost a full re-fetch.

---

## 3. Actual vs. Expected Data Flow

### 3.1 Expected Flow (Target State)

```
First Fetch:
  enumerate_gids() -> lookup_cache() [all miss] -> fetch_all() -> populate_cache()

Second Fetch:
  enumerate_gids() [CACHED] -> lookup_cache() [all HIT] -> return cached -> 0 API calls

Time: <1s (cache deserialize only)
```

### 3.2 Actual Flow (Current State)

```
First Fetch:
  enumerate_gids() [API] -> lookup_cache() [all miss] -> fetch_all() [API] -> populate_cache()

Second Fetch:
  enumerate_gids() [API!] -> lookup_cache() [partial hit] -> fetch_all() [API!] -> merge

Time: 8.84s (multiple API calls still happen)
```

### 3.3 Flow Diagram

```
                    FIRST FETCH                          SECOND FETCH
                    ============                         =============
                         |                                    |
                         v                                    v
               [ParallelSectionFetcher]              [ParallelSectionFetcher]
               fetch_section_task_gids_async()       fetch_section_task_gids_async()
                         |                                    |
                    API CALL                              API CALL!
                  (enumerate GIDs)                      (re-enumerate)
                         |                                    |
                         v                                    v
               [TaskCacheCoordinator]                [TaskCacheCoordinator]
               lookup_tasks_async()                  lookup_tasks_async()
                         |                                    |
                    CACHE MISS                           PARTIAL HIT
                    (0% hit)                             (~40% hit)
                         |                                    |
                         v                                    v
               [ParallelSectionFetcher]              [ParallelSectionFetcher]
               fetch_all()                           fetch_all()  <-- FETCHES ALL!
                         |                                    |
                    API CALLS                             API CALLS!
               (all section tasks)                   (re-fetch everything)
                         |                                    |
                         v                                    v
               [TaskCacheCoordinator]                [Filter to miss_gids only]
               populate_tasks_async()                         |
                         |                                    v
                    CACHE WRITE                              Done
                         |
                         v
                        Done
```

---

## 4. Specific Code Paths Where Bypass Occurs

### 4.1 GID Enumeration Not Cached

**File:** `/src/autom8_asana/dataframes/builders/parallel_fetch.py`
**Lines:** 200-257 (`fetch_section_task_gids_async`)

The GID enumeration phase always makes API calls - there is no cache for section-to-task-GID mappings.

### 4.2 Full Fetch Instead of Targeted Fetch

**File:** `/src/autom8_asana/dataframes/builders/project.py`
**Lines:** 365-377

When cache has ANY misses, the code calls `fetcher.fetch_all()` which fetches ALL tasks from ALL sections, not just the missing GIDs:

```python
if miss_gids:
    result = await fetcher.fetch_all()  # BUG: Fetches ALL, not just miss_gids
```

### 4.3 list_async Bypasses Cache Entirely

**File:** `/src/autom8_asana/clients/tasks.py`
**Lines:** 589-654 (`list_async`)

The pagination iterator directly calls HTTP without cache integration.

---

## 5. Impact Assessment

### 5.1 Affected Operations

| Operation | Severity | Impact Description |
|-----------|----------|-------------------|
| DataFrame warm fetch | HIGH | 8.84s instead of <1s |
| Repeated project extraction | HIGH | No benefit from cache |
| GID enumeration | MEDIUM | Always API calls |
| Cache population efficiency | MEDIUM | Correct but underutilized |

### 5.2 Resource Waste

- **Unnecessary API calls:** ~35+ per warm fetch (section enumeration + task fetches)
- **Wasted bandwidth:** Fetching same 3,530 tasks repeatedly
- **User experience:** Unacceptable latency for "cached" operations

### 5.3 Cache Infrastructure Utilization

The following cache components exist but are UNDERUTILIZED:

| Component | Status | Utilization |
|-----------|--------|-------------|
| `TaskCacheCoordinator` | Implemented | LOW - lookups fail due to empty cache |
| `CacheProvider.get_batch()` | Implemented | LOW - returns all misses |
| `CacheProvider.set_batch()` | Implemented | WORKS - population is correct |
| `EntryType.TASK` | Defined | LOW - rarely populated |
| `EntryType.DETECTION` | Defined | UNUSED in DataFrame path |

---

## 6. Root Causes Summary

| # | Root Cause | Severity | Location |
|---|------------|----------|----------|
| 1 | `list_async()` does not populate cache | **CRITICAL** | `tasks.py:589-654` |
| 2 | Miss handling fetches ALL tasks, not just misses | **HIGH** | `project.py:365-377` |
| 3 | GID enumeration is not cached | **MEDIUM** | `parallel_fetch.py:200-257` |
| 4 | Detection results not cached in DataFrame path | **LOW** | `facade.py` (already addressed in P2) |

---

## 7. Recommendations for Session 2

### 7.1 Must Fix (Blocking Performance Target)

1. **Populate Task cache from `list_async()` results**
   - After `fetch_all()` completes, batch-populate cache with returned tasks
   - Use existing `TaskCacheCoordinator.populate_tasks_async()`
   - This alone should achieve ~90% hit rate on second fetch

2. **Fix miss handling to fetch only missing GIDs**
   - Change `fetcher.fetch_all()` to targeted fetch for `miss_gids` only
   - Consider adding `fetch_gids(gids: list[str])` method to ParallelSectionFetcher

### 7.2 Should Fix (Incremental Improvement)

3. **Cache section-to-GID mappings**
   - New `EntryType.SECTION_TASKS` for GID enumeration results
   - TTL matching section cache (1800s)
   - Eliminates enumeration API calls on warm fetch

4. **Use `modified_since` for incremental sync**
   - If project unchanged, skip enumeration entirely
   - Requires project-level watermark tracking

### 7.3 Could Fix (Future Optimization)

5. **Pre-warm cache during project load**
   - When project is fetched, also fetch task GIDs
   - Reduces cold start latency

6. **Add cache hit/miss metrics to demo script**
   - Improve observability for future investigations

---

## 8. Appendix: Key File References

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/autom8_asana/clients/tasks.py` | TasksClient with cache integration | 91-155 (get_async), 589-654 (list_async) |
| `src/autom8_asana/dataframes/builders/project.py` | DataFrame builder | 326-497 (build_with_parallel_fetch_async) |
| `src/autom8_asana/dataframes/builders/task_cache.py` | Task cache coordinator | 133-206 (lookup), 208-290 (populate) |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Parallel fetcher | 109-187 (fetch_all), 200-257 (fetch_gids) |
| `src/autom8_asana/cache/entry.py` | Cache entry types | 11-33 (EntryType enum) |
| `src/autom8_asana/clients/base.py` | Base client with cache helpers | 82-120 (_cache_get), 122-179 (_cache_set) |

---

## 9. Open Questions

1. **Should `list_async()` populate cache?**
   - Pro: Consistent caching across all fetch paths
   - Con: Memory pressure for large result sets
   - Recommendation: Yes, with opt-out parameter

2. **What is the expected cache key for section-task mappings?**
   - Option A: `section:{gid}:task_gids`
   - Option B: `project:{gid}:section_tasks`
   - Needs architecture decision

3. **Should TaskCacheCoordinator be the only cache population point?**
   - Currently, `get_async()` also populates cache
   - Need consistent design

---

## 10. Next Steps

1. Create PRD for Session 2 implementation with requirements from Section 7
2. Design TDD with specific implementation steps
3. Implement fixes in priority order (7.1 first)
4. Validate with benchmark script targeting <1s warm fetch

---

*This discovery document provides the evidence base for the Cache Optimization Phase 2 implementation session.*
