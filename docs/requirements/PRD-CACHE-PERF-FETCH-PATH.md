---
status: superseded
superseded_by: /docs/reference/REF-cache-patterns.md
superseded_date: 2025-12-24
---

# PRD: DataFrame Fetch Path Cache Integration

## Metadata
- **PRD ID**: PRD-CACHE-PERF-FETCH-PATH
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **Stakeholders**: SDK consumers, autom8 platform team
- **Related PRDs**: PRD-WATERMARK-CACHE, PRD-CACHE-UTILIZATION
- **Discovery Document**: [DISCOVERY-CACHE-PERF-FETCH-PATH.md](/docs/analysis/DISCOVERY-CACHE-PERF-FETCH-PATH.md)

---

## Problem Statement

### What Problem Are We Solving?

The second call to `project.to_dataframe_parallel_async()` takes 11.56 seconds when it should take less than 1 second. The cache infrastructure exists but is not wired into the DataFrame fetch path.

### For Whom?

SDK consumers who repeatedly fetch DataFrames from the same project within a short time window (e.g., dashboard refreshes, iterative analysis, pipeline reruns).

### Root Cause (from Discovery)

1. **`TasksClient.list_async()` has NO cache integration** - unlike `get_async()` which has full cache check/populate
2. **`ParallelSectionFetcher._fetch_section()` calls `list_async()` exclusively** - bypassing all cache infrastructure
3. **`DataFrameCacheIntegration` caches extracted DataFrame ROWS, not Task objects** - provides ~2s improvement but doesn't prevent ~11s API fetch

### Impact of Not Solving

- **Performance**: 10x+ slower than achievable for repeated fetches
- **API Usage**: Unnecessary Asana API calls consume rate limits
- **User Experience**: Dashboard and pipeline operations are unacceptably slow
- **Cost**: Wasted compute and API resources

---

## Goals & Success Metrics

### Primary Goal

Enable Task-level cache integration in the DataFrame fetch path so that a second fetch returns in <1 second instead of 11.56 seconds.

### Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Second fetch latency (warm cache) | 11.56s | <1.0s | Benchmark script |
| First fetch latency (cold cache) | 13.55s | No regression | Benchmark script |
| Cache hit rate (warm cache) | ~10% (rows only) | >95% (tasks + rows) | Cache metrics logging |
| API calls on warm cache | ~50 (per section) | 0 | API call counter |

---

## Scope

### In Scope

- Task-level cache population after `ParallelSectionFetcher.fetch_all()` returns
- Task-level cache lookup before API fetch (when feasible)
- Cache key consistency with existing `TasksClient.get_async()` pattern
- Graceful degradation when cache is unavailable or fails
- Structured logging for cache hit/miss observability
- Partial cache scenario handling (some tasks cached, some not)

### Out of Scope

- Modifying `TasksClient.list_async()` to add cache integration (architectural decision for Architect)
- Changes to `DataFrameCacheIntegration` row cache (remains orthogonal)
- Cache invalidation strategy (covered by TDD-WATERMARK-CACHE)
- New cache entry types (use existing `EntryType.TASK`)
- Changes to public `to_dataframe_parallel_async()` signature
- Multi-project cache coordination

---

## Requirements

### Functional Requirements

#### FR-POPULATE: Cache Population After Fetch

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-POPULATE-001 | After `ParallelSectionFetcher.fetch_all()` returns tasks, all fetched Task objects SHALL be written to the Task cache. | Must | GIVEN a cold cache WHEN `build_with_parallel_fetch_async()` completes THEN each returned task is cached with key `{task_gid}` and `EntryType.TASK`. |
| FR-POPULATE-002 | Task cache population SHALL use batch operations for efficiency. | Must | GIVEN 500 tasks to cache WHEN population occurs THEN a single batch write is used (not 500 individual writes). |
| FR-POPULATE-003 | Each cached Task entry SHALL include `modified_at` as the version for staleness detection. | Must | GIVEN a task with `modified_at: "2025-01-01T00:00:00Z"` WHEN cached THEN `CacheEntry.version` equals that timestamp. |
| FR-POPULATE-004 | Task cache entries SHALL use TTL consistent with `TasksClient.get_async()` behavior (entity-type based TTL). | Should | GIVEN a Unit entity task WHEN cached THEN TTL is 900s; GIVEN a Business entity task WHEN cached THEN TTL is 3600s. |
| FR-POPULATE-005 | Task cache population SHALL occur regardless of row cache state. | Must | GIVEN row cache is disabled via `use_cache=False` WHEN fetch completes THEN Task objects are still cached. |

#### FR-LOOKUP: Cache Lookup Before Fetch

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-LOOKUP-001 | On subsequent `build_with_parallel_fetch_async()` calls, the system SHALL check the Task cache before making API calls. | Must | GIVEN a warm cache with all tasks WHEN second build is called THEN zero API calls are made to `/tasks` endpoints. |
| FR-LOOKUP-002 | Cache lookup SHALL use batch operations for efficiency. | Must | GIVEN 500 task GIDs to check WHEN lookup occurs THEN a single batch read is used (not 500 individual reads). |
| FR-LOOKUP-003 | Cache lookup SHALL validate entry freshness using `modified_at` version comparison when available. | Should | GIVEN a cached task with version `T1` AND current task has `modified_at: T2 > T1` WHEN lookup occurs THEN cache entry is considered stale. |
| FR-LOOKUP-004 | Cache lookup SHALL use existing `EntryType.TASK` entry type for consistency with `TasksClient.get_async()`. | Must | GIVEN a task cached via `get_async()` WHEN DataFrame build occurs THEN that cached entry is found and used. |

#### FR-PARTIAL: Partial Cache Handling

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-PARTIAL-001 | When some tasks are cached and some are not, the system SHALL fetch only the uncached tasks from API. | Must | GIVEN 500 tasks where 400 are cached WHEN build occurs THEN only 100 tasks are fetched from API. |
| FR-PARTIAL-002 | Cached and freshly-fetched tasks SHALL be merged to produce the complete result set. | Must | GIVEN partial cache scenario WHEN build completes THEN the final task list contains all 500 tasks. |
| FR-PARTIAL-003 | Task order in the merged result SHALL match the order that would be returned from a fresh API fetch. | Should | GIVEN tasks A, B, C in section order WHEN B is cached and A, C are fetched THEN result order is A, B, C. |
| FR-PARTIAL-004 | Newly fetched tasks in a partial scenario SHALL be added to cache. | Must | GIVEN 100 uncached tasks are fetched WHEN fetch completes THEN those 100 tasks are added to cache. |

#### FR-DEGRADE: Graceful Degradation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DEGRADE-001 | Cache lookup failures SHALL NOT prevent DataFrame extraction from completing. | Must | GIVEN cache provider throws exception WHEN lookup is attempted THEN fetch proceeds with API calls and returns valid DataFrame. |
| FR-DEGRADE-002 | Cache population failures SHALL NOT prevent DataFrame extraction from completing. | Must | GIVEN cache provider throws exception during population WHEN write is attempted THEN DataFrame is returned successfully without caching. |
| FR-DEGRADE-003 | Cache failures SHALL be logged at WARNING level with error details. | Must | GIVEN cache failure occurs WHEN operation completes THEN log contains warning with exception type and message. |
| FR-DEGRADE-004 | When cache provider is None (not configured), the system SHALL proceed with API fetch without errors. | Must | GIVEN `cache_provider=None` in client WHEN build is called THEN DataFrame is returned from API fetch with no cache-related errors. |

#### FR-CONFIG: Configuration

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CONFIG-001 | Task-level cache integration SHALL be enabled by default. | Must | GIVEN default configuration WHEN `build_with_parallel_fetch_async()` is called THEN Task cache is used. |
| FR-CONFIG-002 | Task-level cache integration SHALL be disableable via existing `use_cache` parameter. | Should | GIVEN `use_cache=False` WHEN build is called THEN no Task cache lookup or population occurs. |
| FR-CONFIG-003 | The `use_cache` parameter semantics SHALL remain backward compatible. | Must | GIVEN existing code using `use_cache=True` for row caching WHEN code runs after this change THEN behavior is enhanced (Task + row caching) not broken. |

### Non-Functional Requirements

#### NFR-LATENCY: Performance Targets

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-LATENCY-001 | Second fetch latency (warm cache, 3,500 tasks) SHALL be under 1.0 second. | <1.0s | Benchmark: `time(second_call) < 1.0` |
| NFR-LATENCY-002 | First fetch latency (cold cache, 3,500 tasks) SHALL not regress from current baseline. | <=13.55s | Benchmark: `time(first_call) <= baseline * 1.05` |
| NFR-LATENCY-003 | Cache batch operations SHALL complete in under 100ms for 500 entries. | <100ms | Benchmark: batch read/write timing |

#### NFR-COMPAT: Backward Compatibility

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-COMPAT-001 | Public API signature of `to_dataframe_parallel_async()` SHALL remain unchanged. | No changes | Code review: method signature unchanged |
| NFR-COMPAT-002 | Existing consumers SHALL not require code changes to benefit from this enhancement. | Zero changes | Integration test: existing test code passes |
| NFR-COMPAT-003 | Existing tests SHALL continue to pass without modification. | 100% pass | CI: all tests green |

#### NFR-OBSERVE: Observability

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-OBSERVE-001 | Cache hit/miss events SHALL be logged with structured fields. | Structured JSON | Log inspection: fields present |
| NFR-OBSERVE-002 | Log events SHALL include: `project_gid`, `cache_hits`, `cache_misses`, `fetch_time_ms`. | All fields | Log inspection |
| NFR-OBSERVE-003 | Cache metrics SHALL be aggregatable for monitoring dashboards. | Numeric values | Metrics inspection |

---

## User Stories / Use Cases

### UC-1: Dashboard Refresh

**As a** dashboard operator,
**I want** repeated DataFrame fetches to be fast,
**So that** dashboard refresh times are acceptable for users.

**Scenario**:
1. Dashboard loads, fetches 3,500-task project DataFrame (13.55s, cold cache)
2. User clicks refresh button 30 seconds later
3. Second fetch returns in <1s (warm cache)
4. User sees updated data nearly instantly

### UC-2: Iterative Analysis

**As a** data analyst,
**I want** to refetch project data during iterative analysis,
**So that** I can explore data without long wait times.

**Scenario**:
1. Analyst runs `df = await project.to_dataframe_parallel_async(client)`
2. Analyst inspects `df`, decides to filter differently
3. Analyst re-runs the same call
4. Second call returns in <1s, enabling rapid iteration

### UC-3: Pipeline Rerun

**As a** pipeline operator,
**I want** pipeline reruns to be fast,
**So that** failure recovery doesn't take as long as initial runs.

**Scenario**:
1. Pipeline stage fetches project DataFrame (13.55s)
2. Pipeline fails in subsequent stage
3. Operator fixes issue and reruns pipeline
4. DataFrame fetch returns in <1s (tasks still cached from first run)

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Task cache TTL (300s default) is sufficient for typical use cases | Existing `TasksClient.get_async()` uses same default |
| Opt_fields used by parallel fetch are consistent with cache expectations | Discovery analysis confirmed `_BASE_OPT_FIELDS` is used consistently |
| CacheProvider supports batch operations (`get_batch`, `set_batch`) | Existing `CacheProvider` protocol includes these methods |
| Task GIDs are available after section enumeration | ParallelSectionFetcher returns Task objects with GIDs |
| Memory is sufficient to cache 3,500 tasks per project | Existing row cache handles similar scale |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `CacheProvider` protocol with `get_batch`/`set_batch` | SDK Team | Available |
| `EntryType.TASK` entry type | SDK Team | Available |
| `_cache_get`/`_cache_set` helper methods in `BaseClient` | SDK Team | Available |
| TDD-WATERMARK-CACHE cache infrastructure | SDK Team | Complete |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should `list_async()` populate cache generally, or only DataFrame path? | Architect | Session 3 | Deferred to TDD - recommend DataFrame path only for minimal change |
| How to handle cache lookup when task GIDs are unknown before section enumeration? | Architect | Session 3 | Populate-only strategy (no pre-fetch lookup) OR two-phase: enumerate sections, check cache, fetch missing |
| Should Task cache and row cache use same or different TTLs? | Architect | Session 3 | Recommend same TTL (300s default) for simplicity |
| What is the opt_fields requirement for cached tasks to be usable? | Architect | Session 3 | Must include `_BASE_OPT_FIELDS` at minimum |

---

## Constraints

### Technical Constraints

1. **Must use existing cache infrastructure** - No new cache backends or entry types
2. **Must use `EntryType.TASK`** - Consistency with `TasksClient.get_async()`
3. **Must not modify `TasksClient.list_async()`** - Minimal change scope
4. **Cache key must be `{task_gid}`** - Consistency with existing pattern

### Business Constraints

1. **No breaking changes** - Existing consumers must continue working
2. **Default enabled** - Performance improvement should be automatic
3. **Opt-out available** - Must be disableable for edge cases

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Stale cache data returned | Medium | Medium | Use `modified_at` versioning; honor TTL expiration |
| Memory pressure from large projects | Medium | Low | Rely on existing TTL-based eviction |
| Cache key collision between projects | Low | Medium | Key is `{task_gid}` which is globally unique in Asana |
| Breaking existing tests | Low | Low | Tests use mocks; graceful degradation handles missing cache |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Requirements Analyst | Initial draft based on Discovery findings |

---

## Appendix A: Discovery Summary

### Root Cause

```
TasksClient.get_async()     TasksClient.list_async()
[CACHE ENABLED]             [NO CACHE]
- _cache_get() before HTTP  - Direct HTTP call
- _cache_set() after HTTP   - No cache interaction
        |                           |
        v                           v
   Single task fetch          Bulk task fetch
   (Direct gets)              (DataFrame build) <-- THE GAP
```

### Performance Breakdown

| Phase | Time | Cache Status |
|-------|------|--------------|
| API Fetch (sections + tasks) | ~11s | NOT cached (root cause) |
| Row Extraction | ~2s | Cached (existing DataFrameCacheIntegration) |
| **Total (second call)** | **11.56s** | Should be <1s |

### Fix Location

Add Task-level cache integration at `ProjectDataFrameBuilder` level:
1. After `ParallelSectionFetcher.fetch_all()` - populate Task cache
2. Before subsequent fetches - check Task cache, fetch only missing

---

## Appendix B: Acceptance Criteria Verification Matrix

| Requirement | Test Type | Automation |
|-------------|-----------|------------|
| FR-POPULATE-001 | Integration | pytest fixture with mock cache |
| FR-POPULATE-002 | Unit | Mock CacheProvider, assert batch call |
| FR-LOOKUP-001 | Integration | Two sequential builds, assert API calls |
| FR-LOOKUP-002 | Unit | Mock CacheProvider, assert batch call |
| FR-PARTIAL-001 | Integration | Partial cache setup, assert fetch count |
| FR-DEGRADE-001 | Unit | CacheProvider raises, assert DataFrame returned |
| NFR-LATENCY-001 | Benchmark | Timed benchmark script |
| NFR-COMPAT-001 | Code review | Manual verification |
