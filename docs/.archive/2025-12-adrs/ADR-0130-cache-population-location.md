# ADR-0130: Cache Population Location Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-CACHE-OPTIMIZATION-P2, TDD-CACHE-OPTIMIZATION-P2, ADR-0119 (DataFrame Task Cache Integration)

## Context

The P1 cache optimization work (ADR-0119) established a two-phase Task cache strategy for DataFrame building: enumerate GIDs, lookup cache, fetch misses, populate cache, merge results. However, **cache population was never triggered** because the implementation assumed `list_async()` would populate the cache. Discovery analysis reveals:

1. `TasksClient.list_async()` does NOT call `_cache_set()` - only `get_async()` does
2. `ParallelSectionFetcher.fetch_all()` uses `list_async()` exclusively
3. The cache was being read but never written from the DataFrame fetch path

This creates a **critical gap**: tasks fetched in the first call are not cached, so the second call still makes full API requests (8.84s instead of <1s target).

### Forces at Play

| Force | Description |
|-------|-------------|
| **PRD Constraint** | PRD-CACHE-OPTIMIZATION-P2 explicitly prohibits modifying `TasksClient.list_async()` to minimize change scope |
| **Consistency** | P1 design (ADR-0119) established cache keys at Task GID level, compatible with `get_async()` |
| **Separation of Concerns** | `TasksClient` handles API access; caching policy belongs at application level |
| **Opt_fields Variability** | Different callers of `list_async()` use different `opt_fields`; no single "correct" set |
| **Population Overhead** | Batch cache writes should be amortized (<100ms for 3,530 tasks) |

### Key Question

**Where should cache population occur to ensure tasks fetched via `list_async()` are cached for subsequent lookups?**

Options:
1. Inside `TasksClient.list_async()` (at the client level)
2. Inside `ParallelSectionFetcher._fetch_section()` (at the fetcher level)
3. Inside `ProjectDataFrameBuilder.build_with_parallel_fetch_async()` (at the builder level)

## Decision

**Populate the Task cache at the `ProjectDataFrameBuilder` level, after `fetch_all()` completes, using the existing `TaskCacheCoordinator.populate_tasks_async()` method.**

Specifically:
- After line 369 in `project.py` (after `result = await fetcher.fetch_all()`)
- Call `await task_cache_coordinator.populate_tasks_async(result.tasks)`
- Similarly for the miss-handling path: populate newly fetched tasks

This follows the P1 pattern where the builder owns cache orchestration.

```python
# project.py: build_with_parallel_fetch_async()

# Phase 3: Fetch missing tasks from API
fetched_tasks: list[Task] = []
if miss_gids:
    result = await fetcher.fetch_all()
    miss_gid_set = set(miss_gids)
    fetched_tasks = [t for t in result.tasks if t.gid in miss_gid_set]

    # Phase 4: Populate cache with newly fetched [ADR-0130]
    await task_cache_coordinator.populate_tasks_async(fetched_tasks)
```

## Rationale

### Why Builder Level (Not Client Level)?

| Factor | Client Level | Builder Level |
|--------|-------------|---------------|
| **PRD Compliance** | Violates constraint | Compliant |
| **Change Scope** | Global (all `list_async()` callers) | Local (DataFrame path only) |
| **Opt_fields Control** | Unknown which fields to cache | Builder knows exact requirements (`_BASE_OPT_FIELDS`) |
| **Cache Policy** | Embedded in infrastructure | Application-level decision |
| **Pagination Complexity** | Must handle PageIterator state | Already has complete task list |

The PRD explicitly prohibits modifying `TasksClient.list_async()`. Beyond that, the builder has context that the client lacks: it knows the exact opt_fields needed for DataFrame extraction.

### Why Builder Level (Not Fetcher Level)?

| Factor | Fetcher Level | Builder Level |
|--------|--------------|---------------|
| **Responsibility** | Fetch infrastructure | Application orchestration |
| **Cache Provider Access** | Would need injection | Already available via coordinator |
| **TTL Resolution** | Would need entity detection | Coordinator already handles |
| **Consistency** | New pattern | Follows P1 pattern (ADR-0119) |

`ParallelSectionFetcher` is infrastructure - it should fetch, not make caching decisions. The builder already owns the `TaskCacheCoordinator` and cache orchestration.

### Why Use Existing `TaskCacheCoordinator`?

The P1 implementation created `TaskCacheCoordinator` with:
- `lookup_tasks_async()` - already used for cache reads
- `populate_tasks_async()` - **exists but was never called from fetch path**
- Entity-type TTL resolution matching `TasksClient.get_async()`
- Graceful degradation on cache failures
- Batch operations via `CacheProvider.set_batch()`

The infrastructure is complete; it just needs to be wired up.

## Alternatives Considered

### Alternative 1: Cache Integration in `TasksClient.list_async()`

**Description**: Add cache population inside the `fetch_page` closure in `list_async()`.

```python
# tasks.py: list_async()
async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
    data, next_offset = await self._http.get_paginated("/tasks", params=params)
    tasks = [Task.model_validate(t) for t in data]

    # Populate cache for each task
    for task in tasks:
        self._cache_set(task.gid, task.model_dump(), EntryType.TASK, ttl=...)

    return tasks, next_offset
```

**Pros**:
- All `list_async()` consumers benefit
- Consistent with `get_async()` pattern
- Single point of change

**Cons**:
- PRD prohibits this approach
- Global scope - affects analytics, reports, all list operations
- Opt_fields vary by caller - which fields to cache?
- Would need to detect/resolve TTL per task in hot path
- Pagination state complicates cache key management

**Why not chosen**: PRD constraint and global scope risk.

### Alternative 2: Cache Integration in `ParallelSectionFetcher._fetch_section()`

**Description**: Populate cache inside the fetcher after each section fetch.

```python
# parallel_fetch.py: _fetch_section()
async with semaphore:
    self._api_call_count += 1
    tasks = await self.tasks_client.list_async(
        section=section_gid,
        opt_fields=self.opt_fields,
    ).collect()

    # Populate cache for fetched tasks
    await self._cache_coordinator.populate_tasks_async(tasks)

    return tasks
```

**Pros**:
- Close to fetch operation
- Caches as soon as data arrives

**Cons**:
- Fetcher is infrastructure, not application logic
- Would need cache coordinator injection
- Parallel population could cause contention
- Mixes fetching and caching concerns
- Less control over full operation timing

**Why not chosen**: Violates separation of concerns; builder is natural orchestration point.

### Alternative 3: New `PopulatingTasksClient` Wrapper

**Description**: Create a decorating wrapper that adds cache population to `list_async()`.

```python
class PopulatingTasksClient:
    def __init__(self, tasks_client, cache_coordinator):
        self._inner = tasks_client
        self._cache = cache_coordinator

    def list_async(self, **kwargs) -> PageIterator[Task]:
        iterator = self._inner.list_async(**kwargs)
        return CachePopulatingIterator(iterator, self._cache)
```

**Pros**:
- Does not modify original client
- Opt-in for specific use cases
- Clean separation

**Cons**:
- Over-engineered for the problem
- PageIterator wrapping is complex
- Adds new component to maintain
- TTL resolution still needed

**Why not chosen**: Adds complexity without proportional benefit.

## Consequences

### Positive

1. **Target Achieved**: Second fetch achieves <1s warm cache latency
2. **PRD Compliant**: No changes to `TasksClient.list_async()`
3. **Minimal Change**: ~10 lines added to `project.py`
4. **Reuses Infrastructure**: Leverages existing `TaskCacheCoordinator`
5. **Consistent Pattern**: Follows P1 design (ADR-0119)
6. **Observable**: Population metrics logged via coordinator

### Negative

1. **Not Universal**: Only DataFrame fetch path benefits; other `list_async()` callers do not
2. **Opt_fields Coupling**: Cached tasks must include `_BASE_OPT_FIELDS` to be useful
3. **Population Latency**: Adds ~50-100ms to cold fetch (batch write overhead)

### Neutral

1. **Future Extensibility**: If other callers need caching, they can follow this pattern
2. **Cache Key Consistency**: Uses same keys as `get_async()` - shared cache entries

## Compliance

### How This Decision Will Be Enforced

1. **Code Review**: Changes to `project.py` cache integration require ADR reference
2. **Unit Tests**: `test_cache_populated_after_fetch` validates population occurs
3. **Integration Tests**: `test_warm_fetch_uses_cache` validates end-to-end
4. **Performance CI**: Benchmark script validates <1s warm fetch

### Code Location

```python
# /src/autom8_asana/dataframes/builders/project.py
# build_with_parallel_fetch_async(), after line 369

# Per ADR-0130: Cache population occurs at builder level
await task_cache_coordinator.populate_tasks_async(fetched_tasks)
```

### Test Coverage

```python
# Required tests per ADR-0130
def test_cache_populated_after_fetch(self):
    """Verify tasks are cached after fetch_all()."""

def test_warm_fetch_uses_cached_tasks(self):
    """Verify second fetch uses cached tasks."""

def test_population_graceful_degradation(self):
    """Verify cache failure does not break fetch."""
```
