# ADR-0119: DataFrame Task Cache Integration Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-CACHE-PERF-FETCH-PATH, TDD-CACHE-PERF-FETCH-PATH, ADR-0115 (Parallel Section Fetch)

## Context

The second call to `project.to_dataframe_parallel_async()` takes 11.56 seconds when it should take less than 1 second. Discovery analysis (DISCOVERY-CACHE-PERF-FETCH-PATH) confirmed the root cause:

1. **`TasksClient.list_async()` has NO cache integration** - unlike `get_async()` which has full cache check/populate
2. **`ParallelSectionFetcher._fetch_section()` calls `list_async()` exclusively** - bypassing all cache infrastructure
3. **`DataFrameCacheIntegration` caches extracted DataFrame ROWS, not Task objects** - provides ~2s improvement but doesn't prevent ~11s API fetch

The existing row cache saves extraction time but every fetch still hits the Asana API for Task objects. We need Task-level cache integration in the DataFrame fetch path.

### Forces at Play

1. **Performance**: SDK consumers expect repeated fetches to be fast (<1s)
2. **Consistency**: Cache should use same keys/patterns as `TasksClient.get_async()`
3. **Minimal Scope**: PRD constraint prohibits modifying `TasksClient.list_async()`
4. **Backward Compatibility**: Public API must remain unchanged
5. **Graceful Degradation**: Cache failures must not break fetch operations

### Key Design Questions

1. **Where to add cache integration?** (TasksClient vs ParallelSectionFetcher vs ProjectDataFrameBuilder)
2. **Lookup strategy?** (Populate-only vs Two-phase with pre-fetch lookup)
3. **How to handle partial cache scenarios?**

## Decision

**Integrate Task-level cache at the `ProjectDataFrameBuilder` level using a two-phase lookup strategy:**

1. **Phase 1 (Enumerate)**: Use lightweight section enumeration to get task GIDs
2. **Phase 2 (Lookup)**: Batch lookup tasks in cache using `CacheProvider.get_batch()`
3. **Phase 3 (Fetch)**: Fetch only cache-miss tasks from API
4. **Phase 4 (Populate)**: Populate cache with newly fetched tasks using `CacheProvider.set_batch()`
5. **Phase 5 (Merge)**: Merge cached and fetched tasks preserving section order

This is implemented via a new `TaskCacheCoordinator` class that encapsulates all Task-level cache operations for the DataFrame build path.

### Cache Key Strategy

Use `{task_gid}` as the cache key with `EntryType.TASK` - identical to `TasksClient.get_async()`. This ensures:
- Tasks cached by `get_async()` are reusable by DataFrame build
- Tasks cached by DataFrame build are reusable by `get_async()`
- Single cache entry per task (no duplication)

### TTL Strategy

Use entity-type based TTLs consistent with `TasksClient.get_async()`:
- Business entities: 3600s (1 hour)
- Contact/Unit entities: 900s (15 min)
- Offer entities: 180s (3 min)
- Process entities: 60s (1 min)
- Generic tasks: 300s (5 min)

### Opt_fields Standardization

Cached Task data must include `_BASE_OPT_FIELDS` to be usable for DataFrame extraction:
```python
_BASE_OPT_FIELDS = [
    "gid", "name", "resource_subtype", "completed", "completed_at",
    "created_at", "modified_at", "due_on", "tags", "tags.name",
    "memberships.section.name", "memberships.project.gid",
]
```

Tasks cached with fewer fields will be treated as cache misses for DataFrame purposes.

## Rationale

### Why `ProjectDataFrameBuilder` (not `TasksClient.list_async()`)?

1. **PRD Constraint**: PRD explicitly prohibits modifying `TasksClient.list_async()` to minimize change scope
2. **Global vs Local**: Modifying `list_async()` would affect ALL callers, not just DataFrame building
3. **Pagination Complexity**: `list_async()` returns `PageIterator` - cache integration would complicate pagination state
4. **GID Unknown**: `list_async()` doesn't know task GIDs before fetching - can't do pre-fetch lookup
5. **Opt_fields Variability**: Different callers use different `opt_fields`; builder knows exact requirements

### Why Two-Phase (not Populate-Only)?

1. **Target Achievement**: Populate-only doesn't achieve <1s warm cache (still fetches from API)
2. **Cache Utilization**: Populate-only wastes cache infrastructure (write but never read)
3. **GID Availability**: Section enumeration provides GIDs at low cost (lightweight API call)
4. **Partial Benefit**: Two-phase enables benefit even with partial cache hits

### Why New Coordinator Class (not inline logic)?

1. **Single Responsibility**: Separates cache coordination from DataFrame building
2. **Testability**: Coordinator can be unit tested with mock CacheProvider
3. **Reusability**: Pattern could be applied to other bulk operations
4. **Encapsulation**: Hides cache complexity from builder

## Alternatives Considered

### Alternative 1: Cache Integration in `TasksClient.list_async()`

**Description**: Add `_cache_get`/`_cache_set` calls to `list_async()` method.

**Pros**:
- All list operations benefit from caching
- Consistent pattern with `get_async()`
- Single point of change

**Cons**:
- PRD prohibits this approach
- Global scope affects all consumers
- PageIterator complicates cache key management
- Can't do pre-fetch lookup (GIDs unknown)
- Different callers need different opt_fields

**Why not chosen**: PRD constraint and global scope risk.

### Alternative 2: Populate-Only (No Pre-Fetch Lookup)

**Description**: After `ParallelSectionFetcher.fetch_all()`, populate Task cache. No cache check before fetch.

**Pros**:
- Simpler implementation
- No GID enumeration overhead
- Always gets fresh data

**Cons**:
- Does not achieve <1s target
- Cache populated but never read
- Every fetch still hits API

**Why not chosen**: Does not satisfy NFR-LATENCY-001.

### Alternative 3: Cache at `ParallelSectionFetcher` Level

**Description**: Add cache integration directly to `ParallelSectionFetcher._fetch_section()`.

**Pros**:
- Close to API call site
- Natural integration point

**Cons**:
- Fetcher is infrastructure, not application logic
- Would need cache provider injection
- Mixes concerns (fetching vs caching)
- Less control over full operation

**Why not chosen**: Violates single responsibility; builder has more context.

### Alternative 4: Fetch by Individual Task GID

**Description**: For cache misses, fetch each task individually via `TasksClient.get_async()`.

**Pros**:
- Leverages existing cache integration in `get_async()`
- Simple conceptually

**Cons**:
- N API calls for N misses (inefficient)
- No batch fetch endpoint in Asana API
- Cold cache = massive API call count

**Why not chosen**: API efficiency - bulk fetch is essential for cold cache.

## Consequences

### Positive

1. **Performance**: Second fetch achieves <1s (target met)
2. **Cache Coherence**: Tasks cached by DataFrame build are usable by `get_async()` and vice versa
3. **Minimal Scope**: Changes isolated to DataFrame building subsystem
4. **Backward Compatible**: No public API changes
5. **Observable**: Structured logging provides cache hit/miss metrics

### Negative

1. **GID Enumeration Overhead**: Adds lightweight API calls for section enumeration (~100-200ms)
2. **Complexity**: Two-phase adds coordination logic
3. **Partial Cache Edge Cases**: Some tasks cached, some not - merge logic needed
4. **Opt_fields Coupling**: Cached tasks must include `_BASE_OPT_FIELDS` for DataFrame use

### Neutral

1. **`use_cache` Semantics Change**: Now controls both Task cache and row cache (documented)
2. **Cache Size**: Task objects larger than row dicts - slightly more memory usage
3. **TTL Alignment**: Task cache and row cache may have different TTLs for same task

## Compliance

### How This Decision Will Be Enforced

1. **Code Review**: Changes to `ProjectDataFrameBuilder` require review for cache pattern adherence
2. **Unit Tests**: `TaskCacheCoordinator` must have >90% coverage
3. **Integration Tests**: Cache hit/miss scenarios must be tested
4. **Performance Benchmark**: CI includes benchmark verifying <1s warm cache

### Documentation

- TDD-CACHE-PERF-FETCH-PATH provides implementation details
- Inline code comments reference this ADR for rationale
- SDK documentation updated to describe caching behavior
