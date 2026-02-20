# ADR-0146: Pure-Read Mode for Story Cache and Batch Reads

## Status

Proposed

## Context

The SectionTimeline feature requires reading cached stories for ~3,800 entities without triggering Asana API calls. The current `load_stories_incremental()` function (`src/autom8_asana/cache/integration/stories.py:35-109`) always makes a live API call -- even on cache "hit" it fetches stories since `last_fetched`. The `max_cache_age_seconds` parameter (lines 91-95) was added as a workaround to suppress API calls when the cache entry is fresh enough, but this is a time-based approximation of a pure-read mode, not a true read-only operation.

Additionally, reading stories for an entire project's entities (3,800 tasks) requires individual cache lookups. The `CacheProvider.get_batch()` protocol method exists (`src/autom8_asana/protocols/cache.py:108-124`) and is implemented in all backends (Redis uses pipelined HGETALL, S3 uses sequential per-key, Tiered coordinates hot-first with cold fallback), but the story cache path does not use it.

### Constraints

- `load_stories_incremental()` must remain unchanged for existing callers (DataFrame computation path uses it with API calls)
- Redis MGET pipeline has practical throughput limits (~12-25MB per pipeline response)
- S3 `get_batch` is sequential per key -- not a true batch operation
- The derived timeline computation needs stories for 3,800 entities within a 60s ALB timeout

### Ambiguities Resolved

- **AMB-2 (Batch read granularity)**: Should batch reads use per-entity MGET or per-project composite entries?
- **AMB-5 (Batch size limits)**: How should 3,800 keys be chunked for `get_batch()`?

## Decision

### 1. Add `read_cached_stories()` as a separate function (not a parameter on `load_stories_incremental`)

```python
def read_cached_stories(
    task_gid: str,
    cache: CacheProvider,
) -> list[dict[str, Any]] | None:
```

This function calls `cache.get_versioned(task_gid, EntryType.STORIES)` and returns the story list if cached, or `None` on cache miss. It does NOT call the Asana API. It does NOT write to cache.

### 2. Add `read_stories_batch()` for efficient bulk reads

```python
def read_stories_batch(
    task_gids: list[str],
    cache: CacheProvider,
    *,
    chunk_size: int = 500,
) -> dict[str, list[dict[str, Any]] | None]:
```

This function chunks the input GIDs into groups of 500 and calls `cache.get_batch()` for each chunk. Returns a mapping of `task_gid -> story list | None`.

### 3. Per-entity MGET (not per-project composite)

Batch reads operate on individual per-entity cache keys using the existing `EntryType.STORIES` entries, not a new per-project composite entry.

### 4. Chunk size of 500 keys

Batch reads are chunked at 500 keys per `get_batch()` call.

## Alternatives Considered

### Option A: Add `read_only=True` parameter to `load_stories_incremental()`

- Pros: Single function, no new API surface
- Cons: Complicates an already complex function (5 code paths: full fetch, incremental, max_cache_age short-circuit, now read-only). The read-only path has fundamentally different semantics (no writes, no API calls) that do not belong in the same function. Violates SRP.

### Option B: Per-project composite cache entry

- Pros: Single cache read per project instead of 3,800 individual reads
- Cons: Requires new storage format, new invalidation logic, duplicates data already stored per-entity. When stories update for one entity, the entire composite must be recomputed. Does not compose with the existing per-entity Lambda warmer that populates stories one task at a time.

### Option C: No chunking (single MGET of 3,800 keys)

- Pros: Single round-trip
- Cons: Redis pipeline response of 3,800 x ~25KB = ~95MB risks timeout and memory pressure. S3 fallback path would sequentially read all 3,800 keys without any concurrency limit.

## Rationale

1. **Separate function over parameter**: `read_cached_stories()` has a clear single responsibility: read from cache, return data or None. This is easier to test, easier to reason about, and avoids adding a sixth code path to `load_stories_incremental()`.

2. **Per-entity over composite**: The entire cache infrastructure is built around per-entity keys. Stories are warmed, invalidated, and TTL-managed per entity. A composite entry would create a parallel storage model that drifts from the per-entity truth. Per-entity batch reads (`get_batch`) are the natural composition of existing primitives.

3. **500-key chunks**: Conservative choice that keeps each Redis pipeline response under ~12.5MB (500 x 25KB), completing in <100ms per pipeline. For S3 fallback, 500 sequential reads at ~100ms each = ~50s -- within the 60s ALB timeout for a single chunk. Multiple chunks execute sequentially, but in practice the Redis hot tier handles most reads.

## Consequences

### Positive

- `load_stories_incremental()` is unchanged -- zero risk to existing callers
- `read_cached_stories()` is trivially testable (mock cache, assert return)
- `read_stories_batch()` composes naturally with existing `CacheProvider.get_batch()` implementations
- Chunk size is configurable for tuning without code changes
- Both functions are synchronous (no async needed -- cache reads are synchronous in the current provider API)

### Negative

- Two new exported functions in the stories integration module (minimal API surface increase)
- S3 fallback for batch reads remains sequential per key -- no improvement over individual reads
- Chunk size of 500 is a heuristic; may need tuning based on production metrics (story sizes vary)

### Neutral

- `max_cache_age_seconds` can be removed from `load_stories_incremental()` once the pure-read function replaces its only usage (in `build_timeline_for_offer`). This is a separate cleanup step (FR-7).
