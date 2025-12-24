# TDD: DataFrame Fetch Path Cache Integration

## Metadata
- **TDD ID**: TDD-CACHE-PERF-FETCH-PATH
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: [PRD-CACHE-PERF-FETCH-PATH](/docs/requirements/PRD-CACHE-PERF-FETCH-PATH.md)
- **Related TDDs**: TDD-WATERMARK-CACHE, TDD-CACHE-INTEGRATION
- **Related ADRs**: [ADR-0119](/docs/decisions/ADR-0119-dataframe-task-cache-integration.md)

## Overview

This design integrates Task-level cache lookup and population into the DataFrame fetch path. The implementation adds a two-phase cache strategy at the `ProjectDataFrameBuilder` level: enumerate section task GIDs, perform batch cache lookup, fetch only missing tasks from API, then merge results and populate cache. This achieves <1s warm cache latency (down from 11.56s) without modifying `TasksClient.list_async()`.

## Requirements Summary

From PRD-CACHE-PERF-FETCH-PATH:

| Requirement | Summary |
|-------------|---------|
| FR-POPULATE | Cache Task objects after parallel fetch using `set_batch()` |
| FR-LOOKUP | Check Task cache before API fetch using `get_batch()` |
| FR-PARTIAL | Handle mixed cache hit/miss scenarios |
| FR-DEGRADE | Graceful degradation on cache failures |
| FR-CONFIG | Configuration via `use_cache` parameter |
| NFR-LATENCY | <1s warm cache, no regression cold cache |
| NFR-COMPAT | No breaking changes to public API |

**Key Constraint**: Must use `{task_gid}` as cache key with `EntryType.TASK` for consistency with `TasksClient.get_async()`.

## System Context

```
+-------------------+     +-----------------------+     +----------------+
|                   |     |                       |     |                |
| SDK Consumer      |---->| ProjectDataFrameBuilder|---->| ParallelSection|
| to_dataframe_     |     | build_with_parallel_  |     | Fetcher        |
| parallel_async()  |     | fetch_async()         |     |                |
|                   |     |                       |     +-------+--------+
+-------------------+     +----------+------------+             |
                                     |                          v
                          +----------v------------+     +----------------+
                          |                       |     |                |
                          | TaskCacheCoordinator  |     | TasksClient    |
                          | (NEW)                 |     | list_async()   |
                          |                       |     |                |
                          +----------+------------+     +----------------+
                                     |
                          +----------v------------+
                          |                       |
                          | CacheProvider         |
                          | get_batch/set_batch   |
                          |                       |
                          +-------------------------+
```

### Integration Points

1. **Upstream**: `ProjectDataFrameBuilder.build_with_parallel_fetch_async()` - entry point
2. **Downstream**: `ParallelSectionFetcher.fetch_all()` - current fetch implementation
3. **Lateral**: `CacheProvider` - existing cache infrastructure
4. **Reference**: `TasksClient.get_async()` - cache pattern to follow

## Design

### Component Architecture

```
ProjectDataFrameBuilder
    |
    +-- TaskCacheCoordinator (NEW)
    |       |
    |       +-- _lookup_cached_tasks()    [FR-LOOKUP]
    |       +-- _populate_task_cache()    [FR-POPULATE]
    |       +-- _merge_results()          [FR-PARTIAL]
    |
    +-- ParallelSectionFetcher (existing)
    |       |
    |       +-- fetch_all()
    |       +-- fetch_section_gids_only() [NEW - lightweight]
    |
    +-- DataFrameCacheIntegration (existing - row cache)
```

| Component | Responsibility | Changes |
|-----------|----------------|---------|
| `ProjectDataFrameBuilder` | Orchestrates cache-aware fetch | Add cache coordination logic |
| `TaskCacheCoordinator` | Task-level cache operations | **NEW** - encapsulates cache logic |
| `ParallelSectionFetcher` | Parallel section enumeration | Add lightweight GID-only fetch |
| `CacheProvider` | Cache storage operations | No changes |
| `DataFrameCacheIntegration` | Row cache operations | No changes (orthogonal) |

### Data Model

#### Task Cache Entry Structure

Uses existing `CacheEntry` with `EntryType.TASK`:

```python
CacheEntry(
    key="1234567890",                    # task_gid
    data={                               # Full task dict from API
        "gid": "1234567890",
        "name": "Task Name",
        "modified_at": "2025-01-01T00:00:00Z",
        "completed": False,
        # ... all fields from _BASE_OPT_FIELDS
    },
    entry_type=EntryType.TASK,
    version=datetime(2025, 1, 1, ...),   # From task.modified_at
    cached_at=datetime.now(UTC),
    ttl=300,                             # Default 300s, entity-type varies
)
```

#### TaskCacheCoordinator Interface

```python
@dataclass
class TaskCacheResult:
    """Result of task cache lookup/population."""
    cached_tasks: list[Task]     # Tasks retrieved from cache
    fetched_tasks: list[Task]    # Tasks fetched from API
    cache_hits: int              # Count of cache hits
    cache_misses: int            # Count of cache misses
    all_tasks: list[Task]        # Merged list preserving order

class TaskCacheCoordinator:
    """Coordinates Task-level cache operations for DataFrame building."""

    def __init__(
        self,
        cache_provider: CacheProvider | None,
        default_ttl: int = 300,
    ) -> None: ...

    async def lookup_tasks_async(
        self,
        task_gids: list[str],
    ) -> dict[str, Task | None]:
        """Batch lookup tasks from cache."""
        ...

    async def populate_tasks_async(
        self,
        tasks: list[Task],
        ttl_resolver: Callable[[Task], int] | None = None,
    ) -> int:
        """Batch populate cache with fetched tasks."""
        ...

    def merge_results(
        self,
        task_gids_ordered: list[str],
        cached: dict[str, Task],
        fetched: list[Task],
    ) -> TaskCacheResult:
        """Merge cached and fetched tasks preserving order."""
        ...
```

### API Contracts

#### Modified: `build_with_parallel_fetch_async()`

No signature change (NFR-COMPAT), but internal behavior changes:

```python
async def build_with_parallel_fetch_async(
    self,
    client: AsanaClient,
    *,
    use_parallel_fetch: bool = True,
    use_cache: bool = True,           # Now controls BOTH row cache AND task cache
    max_concurrent_sections: int | None = None,
    lazy: bool | None = None,
) -> pl.DataFrame:
    """Build DataFrame with cache-aware parallel fetch.

    When use_cache=True (default):
    1. Enumerate section task GIDs (lightweight)
    2. Batch lookup tasks in cache
    3. Fetch only cache-miss tasks from API
    4. Populate cache with newly fetched tasks
    5. Build DataFrame from merged task list
    6. Cache extracted rows (existing behavior)

    When use_cache=False:
    - Bypasses both Task cache and row cache
    """
```

#### New: `ParallelSectionFetcher.fetch_section_task_gids_async()`

```python
async def fetch_section_task_gids_async(self) -> dict[str, list[str]]:
    """Enumerate task GIDs per section without full task data.

    Returns:
        Dict mapping section_gid -> list of task_gids in that section.

    Note:
        Uses minimal opt_fields (just 'gid') for efficiency.
        API calls: 1 (section list) + N (one per section, lightweight).
    """
```

### Data Flow

#### Cache Hit Path (Warm Cache)

```
build_with_parallel_fetch_async()
    |
    v
[1] ParallelSectionFetcher.fetch_section_task_gids_async()
    |-- API: GET /sections?project={gid}
    |-- API: GET /tasks?section={gid}&opt_fields=gid (per section, parallel)
    |
    v
[2] TaskCacheCoordinator.lookup_tasks_async(all_task_gids)
    |-- CacheProvider.get_batch(keys, EntryType.TASK)
    |-- Return: {task_gid: Task, ...} for hits, None for misses
    |
    v
[3] All tasks found in cache (100% hit rate)
    |-- Skip API fetch entirely
    |
    v
[4] TaskCacheCoordinator.merge_results()
    |-- Reconstruct Task list in section order
    |
    v
[5] _build_from_tasks_with_cache(tasks)
    |-- Row cache lookup/extraction (existing)
    |
    v
DataFrame returned (<1s)
```

#### Cache Miss Path (Cold Cache)

```
build_with_parallel_fetch_async()
    |
    v
[1] ParallelSectionFetcher.fetch_all()
    |-- API: GET /sections?project={gid}
    |-- API: GET /tasks?section={gid}&opt_fields=full (per section, parallel)
    |-- Return: list[Task] with full data
    |
    v
[2] TaskCacheCoordinator.populate_tasks_async(tasks)
    |-- Build CacheEntry for each task
    |-- CacheProvider.set_batch(entries)
    |
    v
[3] _build_from_tasks_with_cache(tasks)
    |-- Row extraction and caching (existing)
    |
    v
DataFrame returned (~13s, same as baseline)
```

#### Partial Cache Path

```
build_with_parallel_fetch_async()
    |
    v
[1] ParallelSectionFetcher.fetch_section_task_gids_async()
    |-- Returns: {section_gid: [task_gid, ...], ...}
    |
    v
[2] TaskCacheCoordinator.lookup_tasks_async(all_task_gids)
    |-- Returns: {gid1: Task, gid2: None, gid3: Task, ...}
    |-- Identify misses: [gid2, ...]
    |
    v
[3] ParallelSectionFetcher.fetch_tasks_by_gid_async(miss_gids)
    |-- API: GET /tasks/{gid} for each miss (or batch if available)
    |-- Or: Fetch by section, filter to misses
    |
    v
[4] TaskCacheCoordinator.populate_tasks_async(newly_fetched)
    |-- Cache only the newly fetched tasks
    |
    v
[5] TaskCacheCoordinator.merge_results(ordered_gids, cached, fetched)
    |-- Merge preserving original order
    |
    v
[6] _build_from_tasks_with_cache(all_tasks)
    |
    v
DataFrame returned
```

### Sequence Diagram: Cache-Aware Fetch

```
Consumer            Builder              Coordinator          Fetcher           Cache
   |                   |                     |                   |                |
   | build_with_parallel_fetch_async()       |                   |                |
   |------------------>|                     |                   |                |
   |                   |                     |                   |                |
   |                   | [use_cache=True?]   |                   |                |
   |                   |-------------------->|                   |                |
   |                   |                     |                   |                |
   |                   |                     | fetch_section_task_gids_async()    |
   |                   |                     |------------------>|                |
   |                   |                     |                   |-- API calls -->|
   |                   |                     |<------------------|                |
   |                   |                     | {section: [gids]} |                |
   |                   |                     |                   |                |
   |                   |                     | lookup_tasks_async(gids)           |
   |                   |                     |--------------------------------------->|
   |                   |                     |<---------------------------------------|
   |                   |                     | {gid: Task|None}  |                |
   |                   |                     |                   |                |
   |                   |                     | [partial hits?]   |                |
   |                   |                     | fetch_missing()   |                |
   |                   |                     |------------------>|                |
   |                   |                     |<------------------|                |
   |                   |                     |                   |                |
   |                   |                     | populate_tasks_async(fetched)      |
   |                   |                     |--------------------------------------->|
   |                   |                     |                   |                |
   |                   |                     | merge_results()   |                |
   |                   |<--------------------|                   |                |
   |                   | TaskCacheResult     |                   |                |
   |                   |                     |                   |                |
   |                   | _build_from_tasks_with_cache()          |                |
   |                   |-------------------->|                   |                |
   |<------------------|                     |                   |                |
   | DataFrame         |                     |                   |                |
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Cache integration location | `ProjectDataFrameBuilder` (not `TasksClient.list_async`) | Minimal scope, no global side effects | ADR-0119 |
| Lookup strategy | Two-phase (enumerate GIDs, check cache, fetch missing) | Enables partial cache benefit, not just populate-only | ADR-0119 |
| Cache key format | `{task_gid}` | Consistency with `TasksClient.get_async()` cache | Existing |
| Entry type | `EntryType.TASK` | Reuse existing infrastructure | Existing |
| TTL strategy | Entity-type based (via `_resolve_entity_ttl`) | Consistency with `get_async()` | Existing |
| Opt_fields | Standardize on `_BASE_OPT_FIELDS` | Ensures cached tasks usable for DataFrame | ADR-0119 |
| Graceful degradation | try/except with logging, never propagate | Per existing FR-CACHE-008 pattern | Existing |

## Complexity Assessment

**Level: Module**

Justification:
- Encapsulated change within DataFrame building subsystem
- No new external dependencies
- Reuses existing cache infrastructure
- Clear API boundaries (TaskCacheCoordinator)
- Single deployment unit (SDK library)

Not Service level because:
- No new network protocols
- No independent deployment
- No new persistence layer

Not Script level because:
- Requires coordination between components
- Has defined interfaces
- Needs unit and integration tests

## Implementation Plan

### Phase 1: Task Cache Coordinator (2-3 days)

**Deliverables:**
- `TaskCacheCoordinator` class in `src/autom8_asana/dataframes/builders/task_cache.py`
- Unit tests for coordinator in isolation
- Mock-based tests for cache operations

**Dependencies:** None (uses existing CacheProvider protocol)

### Phase 2: Lightweight Section Enumeration (1-2 days)

**Deliverables:**
- `fetch_section_task_gids_async()` method in `ParallelSectionFetcher`
- Unit tests for GID enumeration
- Integration tests with mock API

**Dependencies:** Phase 1 (coordinator needs GID list)

### Phase 3: Builder Integration (2-3 days)

**Deliverables:**
- Modified `build_with_parallel_fetch_async()` with cache coordination
- Integration of TaskCacheCoordinator into build flow
- Updated structured logging with cache metrics

**Dependencies:** Phase 1, Phase 2

### Phase 4: Testing & Validation (1-2 days)

**Deliverables:**
- Integration tests with real cache provider
- Performance benchmark script
- Validation against NFR-LATENCY targets

**Dependencies:** Phase 3

### Migration Strategy

No migration needed - this is a transparent enhancement:
1. Existing consumers continue calling `build_with_parallel_fetch_async()`
2. Default `use_cache=True` enables new behavior automatically
3. No public API changes
4. Cache population is additive (doesn't break existing cache entries)

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Stale cache data | Medium | Medium | Use `modified_at` versioning; TTL expiration; cache shared with `get_async()` |
| Memory pressure | Low | Medium | Rely on existing TTL-based eviction; no new retention policies |
| Partial cache inconsistency | Low | Low | Always merge in section order; fetch missing ensures completeness |
| GID enumeration overhead | Low | Low | Lightweight API call (`opt_fields=gid` only); only runs when cache enabled |
| Breaking `use_cache` semantics | Medium | Low | `use_cache=False` disables both Task and row cache (documented behavior) |

## Observability

### Metrics

Extend existing structured logging:

```python
logger.info(
    "dataframe_build_completed",
    extra={
        "project_gid": project_gid,
        "task_count": task_count,
        "fetch_strategy": "parallel",
        "fetch_time_ms": elapsed_ms,
        "sections_fetched": sections_fetched,
        # NEW metrics:
        "task_cache_hits": cache_result.cache_hits,
        "task_cache_misses": cache_result.cache_misses,
        "task_cache_hit_rate": cache_result.hit_rate,
        "tasks_fetched_from_api": len(cache_result.fetched_tasks),
    },
)
```

### Logging

| Event | Level | Fields |
|-------|-------|--------|
| Task cache lookup started | DEBUG | `project_gid`, `task_count` |
| Task cache lookup complete | DEBUG | `hits`, `misses`, `lookup_time_ms` |
| Task cache population started | DEBUG | `task_count` |
| Task cache population complete | DEBUG | `populated_count`, `populate_time_ms` |
| Task cache failure (graceful) | WARNING | `operation`, `error_type`, `error_message` |

### Alerting

No new alerts needed - existing cache health monitoring applies.

## Testing Strategy

### Unit Testing

- `TaskCacheCoordinator` in isolation with mock `CacheProvider`
- `merge_results()` with various hit/miss combinations
- TTL resolution logic
- Graceful degradation on cache failures

### Integration Testing

- Cache-aware build with `InMemoryCacheProvider`
- Partial cache scenarios (some tasks cached, some not)
- Cold cache path (verify population occurs)
- Warm cache path (verify no API calls)
- `use_cache=False` bypass verification

### Performance Testing

Benchmark script to verify:
- First fetch latency: <= 13.55s (no regression)
- Second fetch latency: < 1.0s (target)
- Cache hit rate: > 95% on warm cache

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should GID enumeration use existing `list_async` or new lightweight method? | Engineer | Implementation | Recommend new lightweight method for efficiency |
| How to handle tasks that exist in cache but are no longer in section (removed)? | Engineer | Implementation | Trust section enumeration as source of truth; stale cache entries expire via TTL |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial draft |

---

## Appendix A: PRD Requirement Traceability

| PRD Requirement | TDD Section | Implementation |
|-----------------|-------------|----------------|
| FR-POPULATE-001 | Data Flow: Cache Miss Path | `TaskCacheCoordinator.populate_tasks_async()` |
| FR-POPULATE-002 | API Contracts | Uses `CacheProvider.set_batch()` |
| FR-POPULATE-003 | Data Model | `CacheEntry.version` from `task.modified_at` |
| FR-POPULATE-004 | Technical Decisions | Entity-type TTL via `_resolve_entity_ttl()` |
| FR-LOOKUP-001 | Data Flow: Cache Hit Path | `TaskCacheCoordinator.lookup_tasks_async()` |
| FR-LOOKUP-002 | API Contracts | Uses `CacheProvider.get_batch()` |
| FR-LOOKUP-004 | Technical Decisions | `EntryType.TASK` |
| FR-PARTIAL-001 | Data Flow: Partial Cache Path | Fetch only missing tasks |
| FR-PARTIAL-002 | Component Architecture | `merge_results()` |
| FR-PARTIAL-003 | Data Flow | Order preserved via `task_gids_ordered` |
| FR-DEGRADE-001 | Risks & Mitigations | try/except in all cache operations |
| FR-CONFIG-001 | API Contracts | `use_cache=True` default |
| FR-CONFIG-002 | API Contracts | `use_cache=False` disables |
| NFR-LATENCY-001 | Implementation Plan Phase 4 | Benchmark validation |
| NFR-COMPAT-001 | API Contracts | No signature changes |

## Appendix B: Alternative Approaches Considered

### Option A: Populate-Only (No Pre-Fetch Lookup)

**Approach**: After fetch, populate cache. No cache check before fetch.

**Pros**:
- Simpler implementation
- No GID enumeration overhead
- Always gets fresh data

**Cons**:
- Every fetch hits API (no cache benefit on second call)
- Wastes cache - populated but never read
- Does not achieve <1s target

**Why rejected**: Does not satisfy NFR-LATENCY-001 (<1s warm cache).

### Option B: Modify `TasksClient.list_async()`

**Approach**: Add cache integration directly to `list_async()`.

**Pros**:
- All list operations benefit
- Consistent with `get_async()` pattern
- Single point of change

**Cons**:
- Global side effect (affects all consumers)
- `list_async()` doesn't know GIDs upfront
- Pagination complicates cache keys
- Higher risk of regression

**Why rejected**: PRD constraint "Must not modify `TasksClient.list_async()`" and global scope is too broad.

### Option C: Cache at Row Level Only

**Approach**: Keep existing row cache, don't add Task cache.

**Pros**:
- No new code
- Already implemented

**Cons**:
- Only saves extraction time (~2s), not API time (~11s)
- Does not achieve <1s target

**Why rejected**: Discovery confirmed this is insufficient (11.56s second fetch).
