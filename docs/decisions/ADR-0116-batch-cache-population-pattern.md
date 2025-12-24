# ADR-0116: Batch Cache Population Pattern

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-WATERMARK-CACHE, TDD-WATERMARK-CACHE, ADR-0021 (DataFrame Caching Strategy), ADR-0115 (Parallel Section Fetch)

---

## Context

When `build_async()` fetches tasks via parallel section fetch, we need to decide how to integrate with the DataFrame cache. The cache uses per-task entries with key format `{task_gid}:{project_gid}` per ADR-0021.

For a 3,500-task project, this means:
- 3,500 potential cache keys to check
- 3,500 potential cache entries to write after fetch

The `CacheProvider` protocol defines `get_batch()` and `set_batch()` methods for efficient bulk operations. We need to decide:
1. When to check cache (before or after fetch?)
2. How to handle partial cache (some hits, some misses)
3. When to populate cache (during fetch or after?)

**Forces at play**:
- Minimize API calls (cache should prevent unnecessary fetches)
- Minimize latency (batch operations faster than individual)
- Handle partial cache scenarios (typical in multi-project environments)
- Maintain staleness detection via `modified_at` versioning
- Current `get_batch()` implementation loops internally (not atomic)

---

## Decision

We will implement the **Check-Fetch-Populate** pattern:

1. **Check cache first**: Call `get_batch()` with all expected task keys before any API call
2. **Fetch only misses**: If partial cache hit, fetch only missing tasks via parallel section fetch
3. **Populate after fetch**: Call `set_batch()` with all newly fetched tasks
4. **Merge results**: Combine cached data with fresh fetch for final DataFrame

```python
# Check cache
cache_keys = [make_dataframe_key(task_gid, project_gid) for task_gid in expected_task_gids]
cached_entries = cache.get_batch(cache_keys, EntryType.DATAFRAME)

# Partition
cache_hits = {k: v for k, v in cached_entries.items() if v is not None and not v.is_stale(current_version)}
cache_misses = {k for k in cache_keys if k not in cache_hits}

# Fetch only misses (if any)
if cache_misses:
    missing_gids = [parse_key(k)[0] for k in cache_misses]
    fetched_tasks = await parallel_fetch(missing_gids)

    # Populate cache with fetched data
    new_entries = {
        make_dataframe_key(t.gid, project_gid): create_cache_entry(t)
        for t in fetched_tasks
    }
    cache.set_batch(new_entries)

# Merge cached + fetched
all_data = merge(cache_hits, new_entries)
```

**Key design points**:
- Cache key format: `{task_gid}:{project_gid}` (per ADR-0021)
- Entry version: `task.modified_at` for staleness detection
- Default TTL: 300 seconds (5 minutes)
- Graceful degradation: Cache failures do not fail the operation

---

## Rationale

**Why check before fetch?**

The primary goal is reducing API calls. A warm cache should result in zero API calls (except the initial task enumeration). Checking cache first enables:
- Full cache hit: Skip fetch entirely
- Partial cache hit: Fetch only missing/stale entries
- Cold cache: Full parallel fetch (no worse than no-cache case)

**Why batch operations?**

For 3,500 tasks:
- Individual `get()` calls: 3,500 method calls, O(n) latency
- `get_batch()`: 1 method call, amortized O(1) latency

Even if the underlying implementation loops internally (as `EnhancedInMemoryCacheProvider` does), the batch API:
- Reduces function call overhead
- Enables future optimization (Redis MGET, etc.)
- Provides clear semantics for bulk operations

**Why populate after fetch?**

Populating during fetch would require callback-style integration. Populating after:
- Simpler control flow
- All data available for batch operation
- Cache population doesn't slow down fetch

**Why `{task_gid}:{project_gid}` key format?**

Per ADR-0021: Custom field values vary by project context. A task in Project A may have different extracted row data than the same task in Project B (different custom fields visible). The project GID in the key ensures correct cache isolation.

---

## Alternatives Considered

### Alternative 1: Fetch-Then-Cache (No Pre-Check)

- **Description**: Always fetch from API, then populate cache, use cache only on subsequent calls
- **Pros**: Simpler flow; no partial cache complexity
- **Cons**:
  - Warm cache still triggers full API fetch
  - Misses the primary optimization (reduce API calls)
- **Why not chosen**: Defeats the purpose of caching for warm scenarios

### Alternative 2: Individual Cache Operations

- **Description**: Use `get()`/`set()` for each task individually
- **Pros**: Simpler API surface; no batch protocol requirement
- **Cons**:
  - O(n) method call overhead for 3,500 tasks
  - Cannot leverage Redis MGET/MSET
  - Poor performance for large projects
- **Why not chosen**: Unacceptable performance for target use case

### Alternative 3: Cache Entire Project Result

- **Description**: Cache the complete DataFrame as a single entry keyed by project GID
- **Pros**: Single cache key; simple check/populate
- **Cons**:
  - Any task change invalidates entire cache
  - No partial staleness detection
  - Per ADR-0021 rejected due to cache thrashing under write patterns
- **Why not chosen**: Already rejected in exploration phase

### Alternative 4: Async Pipeline Operations for Redis

- **Description**: Implement true Redis MGET/MSET via pipeline
- **Pros**: Optimal Redis performance
- **Cons**:
  - Additional complexity in CacheProvider
  - In-memory provider doesn't benefit
  - Most deployments use in-memory cache
- **Why not chosen**: Deferred optimization; sequential loops acceptable for now

---

## Consequences

### Positive

- **Optimal API usage**: Zero API calls for full cache hit
- **Partial cache support**: Fetches only what's needed
- **Batch efficiency**: Single batch call vs N individual calls
- **Staleness detection**: Per-task versioning via `modified_at`
- **Future optimization**: Batch API enables Redis MGET/MSET later

### Negative

- **Initial task enumeration**: Need task GIDs before cache check (may require lightweight call)
- **Memory overhead**: Holding all cache entries during merge
- **Complexity**: Partial cache logic more complex than all-or-nothing

### Neutral

- **Sequential batch implementation**: In-memory `get_batch()` loops internally (acceptable)
- **Redis optimization deferred**: Pipeline support not in initial implementation

---

## Compliance

To ensure this decision is followed:

1. **Code Review**: Verify `get_batch()` called before API fetch
2. **Staleness Check**: Verify `is_stale()` or `is_current()` called on cached entries
3. **Batch Population**: Verify `set_batch()` used (not individual `set()` calls)
4. **Error Handling**: Verify cache failures don't fail the operation
5. **Unit Tests**: Test full hit, partial hit, full miss, and cache failure scenarios
