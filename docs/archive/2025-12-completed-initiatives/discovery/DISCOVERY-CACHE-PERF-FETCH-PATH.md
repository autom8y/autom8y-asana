# Discovery: Cache Performance - Fetch Path Root Cause Analysis

> **Session 1 Deliverable**: Root cause identification for why second DataFrame fetch takes 11.56s instead of <1s.

**Date**: 2025-12-23
**Author**: Requirements Analyst
**Status**: Complete
**Initiative**: CACHE-PERF-FETCH-PATH (Sub-initiative of CACHE-PERF-META)

---

## Executive Summary

**ROOT CAUSE CONFIRMED**: The Orchestrator's preliminary findings are **CORRECT**. The cache bypass occurs because:

1. **`ParallelSectionFetcher.fetch_all()` makes raw API calls with NO cache interaction** - it fetches Task objects directly from Asana API without checking or populating any cache
2. **`DataFrameCacheIntegration` caches extracted DataFrame ROWS, not raw Task objects** - these are orthogonal concerns; row caching doesn't prevent repeated API calls
3. **There is NO Task-level cache integration in the parallel fetch path** - unlike `TasksClient.get_async()` which has cache check/populate, the `list_async()` path used by parallel fetch bypasses caching entirely

**Impact**: Every call to `project.to_dataframe_parallel_async()` results in full API fetch, regardless of cache state. The cache infrastructure exists but is not wired into the fetch path.

---

## 1. Current Flow Diagram

### What Actually Happens (Root Cause)

```
project.to_dataframe_parallel_async(client) [1st call]
    |
    v
ProjectDataFrameBuilder.build_with_parallel_fetch_async()
    |
    v
ParallelSectionFetcher.fetch_all()
    |
    +---> SectionsClient.list_for_project_async()  [API call]
    |
    +---> For each section (parallel, max 8 concurrent):
    |         |
    |         v
    |     TasksClient.list_async(section=...)  [API call - NO CACHE CHECK]
    |         |
    |         v
    |     HTTP GET /tasks?section=...  [Direct API, no cache]
    |
    v
Tasks returned (raw API response)
    |
    v
_build_from_tasks_with_cache() [ONLY caches DataFrame rows, NOT tasks]
    |
    +---> For each task: _extract_row() -> dict
    |
    +---> DataFrameCacheIntegration.cache_batch_async() [Caches ROWS only]
    |
    v
DataFrame built (13.55s)


project.to_dataframe_parallel_async(client) [2nd call]
    |
    v
ProjectDataFrameBuilder.build_with_parallel_fetch_async()
    |
    v
ParallelSectionFetcher.fetch_all()  [REPEATS ALL API CALLS]
    |
    +---> Same API calls happen AGAIN
    |     (No cache lookup for Task objects)
    |
    v
Tasks returned (from API AGAIN)
    |
    v
_build_from_tasks_with_cache()
    |
    +---> DataFrameCacheIntegration.get_cached_batch_async() [ROW cache HIT]
    |     (Rows are cached, extraction is skipped)
    |
    v
DataFrame built (11.56s)  <-- Only ~2s saved from row cache
```

### Why Second Fetch is Still Slow

The 2-second improvement (13.55s -> 11.56s) comes from the **row cache hit** - extraction is skipped for cached rows. However, the **API fetch time** (~11s) is NOT reduced because:

1. Tasks are fetched from API every time
2. Task-level cache is NEVER checked in the fetch path
3. Task-level cache is NEVER populated in the fetch path

---

## 2. Cache Integration Map

### Where Cache IS Used

| Component | Cache Integration | Evidence |
|-----------|------------------|----------|
| `TasksClient.get_async()` | **YES** - check before HTTP, populate after | `tasks.py` lines 117-140 |
| `DataFrameCacheIntegration` | **YES** - caches extracted rows | `cache_integration.py` entire file |
| `ProjectDataFrameBuilder._build_from_tasks_with_cache()` | **YES** - uses row cache | `project.py` lines 479-627 |

### Where Cache IS NOT Used (THE GAP)

| Component | Cache Integration | Evidence |
|-----------|------------------|----------|
| `TasksClient.list_async()` | **NO** - direct API call, no cache | `tasks.py` lines 574-639 |
| `ParallelSectionFetcher._fetch_section()` | **NO** - calls list_async() | `parallel_fetch.py` lines 200-224 |
| `ParallelSectionFetcher.fetch_all()` | **NO** - no cache awareness | `parallel_fetch.py` lines 109-187 |

### Visual Summary

```
                    CACHE INTEGRATION STATUS

+---------------------------+     +---------------------------+
|   TasksClient.get_async() |     |  TasksClient.list_async() |
|   [CACHE ENABLED]         |     |  [NO CACHE]               |
|   - check _cache_get()    |     |  - direct HTTP call       |
|   - populate _cache_set() |     |  - returns PageIterator   |
+---------------------------+     +---------------------------+
           |                                   |
           v                                   v
    Single task fetch                  Bulk task fetch
    (Used by: direct get)              (Used by: DataFrame build)
                                       <--- THE GAP
```

---

## 3. Root Cause Identification

### Evaluating the 5 Hypotheses from Prompt 0

| # | Hypothesis | Status | Evidence |
|---|------------|--------|----------|
| 1 | Cache Population Not Happening | **CONFIRMED (Task-level)** | `ParallelSectionFetcher._fetch_section()` calls `list_async()` which has NO `_cache_set()` |
| 2 | Cache Lookup Not Happening | **CONFIRMED (Task-level)** | `list_async()` has NO `_cache_get()` check before HTTP |
| 3 | Opt_fields Mismatch | **NOT THE ROOT CAUSE** | Opt_fields are consistent; issue is cache not being used at all |
| 4 | Cache Key Mismatch | **NOT THE ROOT CAUSE** | Keys don't matter if cache is never called |
| 5 | TTL Already Expired | **NOT THE ROOT CAUSE** | Back-to-back calls, TTL is 300s |

### Primary Root Cause

**Hypothesis 1+2 Combined**: `TasksClient.list_async()` has NO cache integration, unlike `get_async()`.

**Code Evidence**:

`TasksClient.get_async()` (lines 87-140):
```python
@error_handler
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    # FR-CLIENT-001: Check cache first
    cached_entry = self._cache_get(task_gid, EntryType.TASK)  # <-- CACHE CHECK
    if cached_entry is not None:
        # Cache hit
        data = cached_entry.data
        ...

    # Cache miss: fetch from API
    data = await self._http.get(f"/tasks/{task_gid}", params=params)

    # Store in cache
    self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)  # <-- CACHE POPULATE
```

`TasksClient.list_async()` (lines 574-639):
```python
def list_async(self, *, project: str | None = None, section: str | None = None, ...):
    async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
        params = self._build_opt_fields(opt_fields)
        ...
        data, next_offset = await self._http.get_paginated("/tasks", params=params)
        # NO CACHE CHECK
        # NO CACHE POPULATE
        tasks = [Task.model_validate(t) for t in data]
        return tasks, next_offset

    return PageIterator(fetch_page, page_size=min(limit, 100))
```

### Secondary Observation

`DataFrameCacheIntegration` caches **extracted rows** (dictionaries), not **Task objects**. This is a separate cache layer that:
- Saves extraction CPU time
- Does NOT save API fetch time

---

## 4. Evidence Summary

### File-by-File Analysis

#### `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

| Method | Cache Check | Cache Populate | Notes |
|--------|-------------|----------------|-------|
| `get_async()` | YES (line 118) | YES (line 134) | Full cache integration |
| `list_async()` | **NO** | **NO** | Direct HTTP, no cache |
| `subtasks_async()` | **NO** | **NO** | Direct HTTP, no cache |
| `create_async()` | N/A | N/A | Write operation |
| `update_async()` | N/A | N/A | Write operation |

#### `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/parallel_fetch.py`

| Method | Cache Interaction | Notes |
|--------|-------------------|-------|
| `fetch_all()` | **NONE** | Orchestrates section fetch, no cache |
| `_list_sections()` | **NONE** | Calls SectionsClient, no cache |
| `_fetch_section()` | **NONE** | Calls `tasks_client.list_async()` |

**Critical Code Path** (lines 200-224):
```python
async def _fetch_section(self, section_gid: str, semaphore: asyncio.Semaphore) -> list[Task]:
    async with semaphore:
        self._api_call_count += 1
        tasks: list[Task] = await self.tasks_client.list_async(
            section=section_gid,
            opt_fields=self.opt_fields,
        ).collect()  # <-- API call, NO CACHE
        return tasks
```

#### `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py`

| Method | Cache Interaction | Notes |
|--------|-------------------|-------|
| `build_with_parallel_fetch_async()` | ROW cache only | Uses DataFrameCacheIntegration |
| `_build_serial_async()` | ROW cache only | Uses DataFrameCacheIntegration |
| `_build_from_tasks_with_cache()` | ROW cache only | Caches extracted dict rows |

**Important**: The cache parameters in this file (`use_cache=True`) refer to **DataFrame row cache**, NOT Task object cache.

#### `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py`

| Class | What It Caches | Notes |
|-------|----------------|-------|
| `CachedRow` | Extracted row dict | `data: dict[str, Any]` |
| `DataFrameCacheIntegration` | Row entries | `EntryType.DATAFRAME` |

**Key Point**: This module caches the OUTPUT of extraction, not the INPUT (Task objects).

---

## 5. Proposed Fix Location

### Option A: Cache Integration in `TasksClient.list_async()` (RECOMMENDED)

**Location**: `src/autom8_asana/clients/tasks.py` lines 574-639

**Approach**:
1. After fetching tasks from API, populate cache for each task
2. Before fetching, check cache for known task GIDs (if available)

**Pros**:
- Consistent with `get_async()` pattern
- All list operations benefit from cache
- Single point of change

**Cons**:
- `list_async()` doesn't know task GIDs upfront (can't check cache before fetch)
- Would need to populate cache AFTER fetch (write-through pattern)

### Option B: Cache Integration in `ParallelSectionFetcher`

**Location**: `src/autom8_asana/dataframes/builders/parallel_fetch.py`

**Approach**:
1. Inject cache provider into fetcher
2. Populate cache after fetch
3. Optionally check cache if task GIDs are known

**Pros**:
- DataFrame-specific optimization
- Can be coordinated with row cache

**Cons**:
- Duplicates cache logic
- Doesn't benefit other list operations

### Option C: New Cache Layer Between Fetch and Build (SIMPLEST)

**Location**: New method in `ProjectDataFrameBuilder`

**Approach**:
1. After `fetcher.fetch_all()` returns tasks
2. Populate Task cache with fetched tasks
3. On subsequent calls, check Task cache BEFORE calling fetcher

**Pros**:
- Minimal changes to existing code
- Clear separation of concerns
- Can be implemented incrementally

**Cons**:
- Requires tracking task GIDs for cache lookup
- May need watermark/invalidation strategy

---

## 6. Impact Assessment

### What Changes Are Needed

| Component | Change Required | Scope |
|-----------|-----------------|-------|
| `TasksClient.list_async()` | Add cache population after fetch | Medium |
| `ParallelSectionFetcher` | No direct changes | N/A |
| `ProjectDataFrameBuilder` | Add cache check before fetch | Medium |
| `DataFrameCacheIntegration` | No changes | N/A |

### What Stays the Same

| Component | Status |
|-----------|--------|
| Row cache integration | Unchanged - continues to cache extracted rows |
| `TasksClient.get_async()` cache | Unchanged - already works |
| Cache infrastructure | Unchanged - `CacheProvider` protocol is sufficient |
| DataFrame public API | Unchanged - `to_dataframe_parallel_async()` signature stable |

### Expected Performance Improvement

| Metric | Current | Expected After Fix |
|--------|---------|-------------------|
| Second fetch latency | 11.56s | <1s |
| Cache hit rate (warm) | ~10% (rows only) | >95% (tasks + rows) |
| API calls (warm cache) | ~50 (per section) | 0 |

---

## 7. Risk Assessment

### Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache key collision | Low | Medium | Use consistent key format: `{task_gid}` |
| Stale cache data | Medium | Medium | Use `modified_at` for versioning |
| Memory pressure (large projects) | Medium | Low | Existing TTL-based eviction |
| Breaking existing tests | Low | Low | Existing cache tests use mocks |

### Design Risks

| Risk | Concern | Mitigation |
|------|---------|------------|
| Partial cache scenarios | Some tasks cached, some not | Fetch uncached, merge with cached |
| Opt_fields consistency | Different opt_fields = different data | Normalize to standard field set for cache |
| Cache invalidation | When to invalidate after updates | Use watermark pattern from TDD-WATERMARK-CACHE |

### Non-Risks

| Concern | Why Not a Risk |
|---------|----------------|
| TTL expiration | 300s default TTL is sufficient for back-to-back calls |
| Cache provider unavailable | Graceful degradation already implemented |
| Row cache interference | Row cache and Task cache are independent |

---

## 8. Recommendations for Next Session

### Session 2: Requirements Definition

The PRD should address:

1. **FR-POPULATE-***: Task cache population after parallel fetch
2. **FR-LOOKUP-***: Task cache lookup before fetch
3. **FR-KEY-***: Cache key structure (use `{task_gid}` for consistency with `get_async()`)
4. **FR-PARTIAL-***: Handling partial cache scenarios
5. **FR-DEGRADE-***: Graceful degradation requirements
6. **NFR-LATENCY-***: <1s target for warm cache fetch

### Key Design Decisions Needed

1. **Where to add cache integration**: Recommend Option C (new layer in builder)
2. **Cache key format**: Use existing `{task_gid}` format from `get_async()`
3. **Opt_fields handling**: Standardize on `_BASE_OPT_FIELDS` for cache
4. **Partial cache strategy**: Fetch only uncached tasks

### Questions for Architect

1. Should `list_async()` populate cache at all, or only parallel fetch path?
2. How to handle cache lookup when task GIDs are unknown before fetch?
3. Should row cache and task cache use same or different TTLs?

---

## Appendix: Key Code References

### TasksClient.get_async() - Cache Pattern Reference

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
**Lines**: 87-140

```python
@error_handler
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    # FR-CLIENT-001: Check cache first
    cached_entry = self._cache_get(task_gid, EntryType.TASK)
    if cached_entry is not None:
        data = cached_entry.data
        if raw:
            return data
        task = Task.model_validate(data)
        task._client = self._client
        return task

    # Cache miss: fetch from API
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/tasks/{task_gid}", params=params)

    # Store in cache with entity-type TTL
    ttl = self._resolve_entity_ttl(data)
    self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)
    ...
```

### ParallelSectionFetcher._fetch_section() - The Gap

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/parallel_fetch.py`
**Lines**: 200-224

```python
async def _fetch_section(
    self,
    section_gid: str,
    semaphore: asyncio.Semaphore,
) -> list[Task]:
    async with semaphore:
        self._api_call_count += 1
        tasks: list[Task] = await self.tasks_client.list_async(
            section=section_gid,
            opt_fields=self.opt_fields,
        ).collect()
        return tasks  # <-- NO CACHE POPULATE
```

### DataFrameCacheIntegration - Row Cache (Not Task Cache)

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py`
**Lines**: 41-81

```python
@dataclass(frozen=True)
class CachedRow:
    """Immutable representation of a cached dataframe row."""
    task_gid: str
    project_gid: str
    data: dict[str, Any]  # <-- Extracted row data, NOT Task object
    schema_version: str
    cached_at: datetime
    version: datetime
```

---

## Conclusion

The root cause of the 11.56s second fetch time is confirmed:

**`TasksClient.list_async()` has NO cache integration, unlike `get_async()`. The parallel fetch path calls `list_async()` exclusively, bypassing all cache infrastructure.**

The existing `DataFrameCacheIntegration` caches extracted rows, which provides ~2s improvement, but the ~11s API fetch time is repeated every call because Task objects are never cached.

**Recommendation**: Add Task-level cache population to the parallel fetch path, following the existing pattern in `TasksClient.get_async()`. This is a targeted fix with low risk and high impact.
