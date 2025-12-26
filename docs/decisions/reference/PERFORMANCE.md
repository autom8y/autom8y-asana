# ADR Summary: Performance Optimization

> Consolidated decision record for optimization strategies, batching, async operations, and performance improvements. Individual ADRs archived.

## Overview

The autom8_asana SDK implements an async-first architecture optimized for I/O-bound operations against the Asana API. Performance decisions focus on three pillars: efficient concurrency through async patterns, intelligent batching to minimize API calls, and lazy evaluation for memory efficiency at scale.

The SDK's performance strategy evolved from basic sequential operations to sophisticated optimizations including parallel section fetching, request coalescing, and incremental data loading. All optimizations maintain backward compatibility through sync wrappers while delivering dramatic performance improvements for async-aware code.

Key principles guide all performance work: respect Asana's rate limits, fail fast with clear errors, provide predictable behavior through consistent patterns, and optimize for real-world usage patterns rather than theoretical edge cases.

## Key Decisions

### 1. Concurrency Model: Async-First with Sync Wrappers
**Context**: SDK must support both async and sync codebases while maintaining optimal I/O performance

**Decision**: Implement async-first with fail-fast sync wrappers
- All I/O operations implemented as async methods
- Sync wrappers use `@sync_wrapper` decorator with `asyncio.run()`
- Sync methods detect async context and raise RuntimeError with guidance
- SaveSession and all clients follow this pattern

**Source ADRs**: ADR-0002, ADR-0038

**Why this works**: Async is optimal for I/O-bound HTTP operations. Fail-fast prevents hidden bugs from nested event loops while providing clear error messages directing users to async methods. This maintains a single implementation path (async) with thin sync compatibility layer.

**Trade-offs**: Sync callers must install event loop machinery (handled transparently). Async-in-async detection adds small overhead but prevents catastrophic failures from nested loops.

### 2. Batching Strategy: Sequential Chunks
**Context**: Asana Batch API limits to 10 actions per request; large operations require multiple chunks

**Decision**: Execute batch chunks sequentially, not in parallel
- Split large batches into ceil(N/10) chunks of max 10 actions
- Execute chunk N fully before starting chunk N+1
- Aggregate results in original request order
- Rate limiter naturally throttles chunk execution

**Source ADRs**: ADR-0010, ADR-0039

**Why this works**: Sequential execution provides predictable ordering (critical for dependent operations like create-parent-then-subtask), simpler error handling (clear failure points), and consistent behavior with SDK's established patterns. Performance is still excellent - 10 actions per request is 10x better than individual calls.

**Trade-offs**: Suboptimal throughput for large independent batches. 100 actions = 10 sequential requests taking ~1 second vs theoretical ~200ms parallel. Accepted because dependency ordering requirements make parallel execution unsafe for common use cases.

### 3. Batch API Request Format
**Context**: Batch API endpoint requires specific JSON structure

**Decision**: Wrap batch actions in `{"data": {"actions": [...]}}` envelope
- All batch requests use outer `data` wrapper
- Matches Asana's response format convention
- HTTP client unwraps responses but doesn't auto-wrap requests

**Source ADR**: ADR-0015

**Why this works**: Corrects 400 Bad Request errors from missing envelope. Documents API format expectations explicitly to prevent regression.

**Trade-offs**: None - this is the correct API format per Asana specification.

### 4. Incremental Loading: Stories with `since` Parameter
**Context**: Tasks with hundreds of stories waste API quota and latency re-fetching unchanged data

**Decision**: Use Asana's `since` parameter for incremental story loading
- Cache stores `last_story_at` metadata
- Subsequent fetches use `GET /tasks/{gid}/stories?since={last_story_at}`
- Merge new stories with cached, update atomically
- Stories are immutable (no updates, only additions)

**Source ADR**: ADR-0020

**Why this works**: For tasks with 200 stories and 2 new comments, this reduces from 3 API calls fetching 200 stories to 1 API call fetching 2 stories. Dramatic efficiency improvement for common case of checking for updates.

**Trade-offs**: Deleted stories not detected until TTL expiration. Merge complexity requires atomic Redis WATCH/MULTI transactions to prevent race conditions. Accepted because story deletion is rare and cache TTL provides eventual consistency.

### 5. Evaluation Strategy: Lazy vs Eager with 100-Task Threshold
**Context**: Polars supports both eager (immediate) and lazy (deferred) evaluation modes

**Decision**: Auto-select based on 100-task threshold with override parameter
- Tasks ≤ 100: Eager DataFrame (simpler debugging)
- Tasks > 100: LazyFrame with automatic `.collect()` (query optimization)
- `lazy: bool | None` parameter allows explicit override
- Always return `pl.DataFrame`, never expose `LazyFrame` in public API

**Source ADR**: ADR-0031

**Why this works**: 100-task threshold aligns with concurrency model (10 workers x 10 tasks). Below threshold, query planning overhead exceeds benefits. Above threshold, lazy evaluation provides 20-40% performance improvement through predicate pushdown, projection optimization, and parallel execution.

**Trade-offs**: Two code paths to test and maintain. Threshold is somewhat arbitrary (though empirically validated). Hidden mode-switching could surprise users who expect consistent behavior. Accepted because sensible defaults serve 90% of users while power users can override.

### 6. Async Methods: Task Subtasks
**Context**: Business model code and demos require fetching subtasks with pagination

**Decision**: Add `subtasks_async()` method to TasksClient
- Returns `PageIterator[Task]` for lazy pagination
- Follows exact pattern of `list_async()` method
- No sync wrapper (PageIterator is inherently async)
- Supports `opt_fields` for field selection

**Source ADR**: ADR-0057

**Why this works**: Consistent API pattern across all list operations. Memory-efficient lazy iteration for large subtask lists. Named `subtasks_async` rather than `list_subtasks_async` for conciseness and demo compatibility.

**Trade-offs**: No sync version available (would require collecting all results, changing API contract). Users must use async context or collect to list manually.

### 7. Batch Resolution API Design
**Context**: Resolving multiple AssetEdits to Units/Offers is high-frequency use case

**Decision**: Module-level functions for batch resolution
- `resolve_units_async(asset_edits, client)` in `resolution.py`
- Returns `dict[str, ResolutionResult[Unit]]` keyed by AssetEdit GID
- Optimizes by grouping by Business and bulk hydrating units once
- Concurrent dependent task fetching when using DEPENDENT_TASKS strategy

**Source ADR**: ADR-0073

**Why this works**: Module functions are natural for collection operations (vs class methods operating on single instance). Dict return type enables O(1) lookup by GID. Shared lookups dramatically reduce API calls - single units fetch per Business instead of per AssetEdit.

**Trade-offs**: Less discoverable than class/client methods (requires import). Introduces new pattern of module-level batch functions. Accepted because the API clarity and efficiency gains outweigh discoverability concerns.

### 8. Parallel Section Fetch
**Context**: Project DataFrame extraction takes 52-59 seconds for 3,500-task projects due to serial pagination

**Decision**: Fetch tasks from sections in parallel with semaphore control
- Enumerate sections via `SectionsClient.list_for_project_async()`
- Fetch each section's tasks concurrently with `asyncio.gather()`
- Semaphore limits concurrent requests (default 8)
- Deduplicate multi-homed tasks by GID
- Fall back to serial project-level fetch on any failure

**Source ADR**: ADR-0115

**Why this works**: Reduces cold-start latency from 52s to ~8s (80% improvement). Sections are natural parallelization unit - independent, API-supported, typical project has 8-12 sections. Semaphore prevents rate limit exhaustion (8 concurrent at ~500ms each = 16 req/s, well under 25 req/s limit).

**Trade-offs**: Adds one section enumeration API call. Increased complexity with parallel error handling. Higher memory overhead holding all sections before merge. No benefit for single-section projects. Accepted because dramatic latency improvement for common multi-section projects.

### 9. Batch Request Coalescing
**Context**: Multiple expired cache entries need staleness checks; individual requests waste API calls

**Decision**: Time-bounded coalescing with 50ms window and 100-entry max batch
- First request starts 50ms timer
- Subsequent requests join pending batch
- Flush triggers: timer expires (50ms) OR max batch reached (100)
- GID deduplication within batch (same GID → single API call, shared result)
- Results distributed to all waiting callers

**Source ADR**: ADR-0132

**Why this works**: 50ms window provides good batching efficiency (typical DataFrame ops take 100-500ms, so 50ms is small fraction) while keeping added latency imperceptible. 100-entry max translates to 10 Asana batch requests (10 actions each) - sufficient for most operations, memory-bounded, reasonable processing time. Immediate flush at max prevents long waits for bursts.

**Trade-offs**: 0-50ms added latency for first request in batch. Async coordination complexity with careful locking. Pending batch lost on process crash. Accepted because batching efficiency gains (reducing hundreds of individual requests to tens of batch requests) justify small latency cost.

## Cross-References

**Related Summaries**:
- ADR-SUMMARY-CACHE: Caching strategies that complement these performance optimizations
- ADR-SUMMARY-SAVESESSION: Save orchestration using async-first and batching patterns

**Related ADRs**:
- ADR-0018: Batch Modification Checking (cache staleness detection)
- ADR-0048: Circuit Breaker Pattern (resilience for performance under failure)
- ADR-0070: Hydration Partial Failure Handling (graceful degradation)
- ADR-0133: Progressive TTL Extension Algorithm (cache performance tuning)

## Performance Characteristics

### Latency Improvements

| Operation | Before | After | Improvement | Decision |
|-----------|--------|-------|-------------|----------|
| Project DataFrame (3,500 tasks) | 52-59s | ~8s | 80% reduction | Parallel section fetch |
| Task with 200 stories, 2 new | 3 API calls (200 stories) | 1 API call (2 stories) | 67% reduction in calls, 99% bandwidth savings | Incremental story loading |
| 100 independent AssetEdit resolutions | 100+ API calls | ~12 API calls (1 per Business + prefetch) | 88% reduction | Batch resolution |
| 100 staleness checks (burst) | 100 individual GET requests | 10 batched requests | 90% reduction | Request coalescing |

### Throughput Improvements

| Scenario | Before | After | Improvement | Decision |
|----------|--------|-------|-------------|----------|
| 50 task updates | 50 requests | 5 batch requests (10 each) | 10x fewer requests | Sequential batching |
| Large DataFrame (500+ tasks) | Eager evaluation | Lazy with optimization | 20-40% faster | Lazy evaluation |
| Async save operations | Blocking I/O | Non-blocking async | N x concurrent operations | Async-first |

### Memory Efficiency

| Scenario | Before | After | Improvement | Decision |
|----------|--------|-------|-------------|----------|
| 10,000-task DataFrame | All rows materialized | Lazy with projection pushdown | 40-60% memory reduction | Lazy evaluation |
| Story cache (200 stories, 2 new) | 200 stories re-fetched | 2 stories appended | 99% bandwidth savings | Incremental loading |

## Implementation Patterns

### Async-First Pattern

```python
class TasksClient:
    async def get_async(self, task_gid: str) -> Task:
        """Primary async implementation."""
        return await self._http.get(f"/tasks/{task_gid}")

    @sync_wrapper
    async def _get_sync(self, task_gid: str) -> Task:
        return await self.get_async(task_gid)

    def get(self, task_gid: str) -> Task:
        """Sync wrapper with fail-fast detection."""
        return self._get_sync(task_gid)
```

**When to use**: All I/O-bound operations (HTTP requests, database queries)

**When NOT to use**: CPU-bound operations, pure computation, non-async contexts without fallback

### Sequential Batching Pattern

```python
async def execute_batch(requests: list[Request]) -> list[Result]:
    """Execute batch in sequential chunks of 10."""
    chunks = [requests[i:i+10] for i in range(0, len(requests), 10)]
    results = []

    for chunk in chunks:
        # Execute one chunk at a time
        chunk_results = await self._batch_client.execute_async(chunk)
        results.extend(chunk_results)

    return results
```

**When to use**: Asana Batch API operations, dependency-ordered operations

**When NOT to use**: Independent operations that could safely run in parallel

### Incremental Loading Pattern

```python
async def get_stories(self, task_gid: str) -> list[Story]:
    """Fetch stories incrementally using 'since' parameter."""
    cached = await self._cache.get_versioned(task_gid, EntryType.STORIES)

    if cached is None:
        # No cache, full fetch
        return await self._fetch_all_stories(task_gid)

    # Incremental fetch
    last_story_at = cached.metadata.get("last_story_at")
    new_stories = await self._fetch_stories_since(task_gid, last_story_at)

    if not new_stories:
        return cached.data["stories"]

    # Merge and update cache atomically
    all_stories = cached.data["stories"] + new_stories
    await self._cache_stories(task_gid, all_stories)
    return all_stories
```

**When to use**: Immutable append-only data (stories, activity), large collections with infrequent updates

**When NOT to use**: Frequently modified data, data with deletions requiring detection

### Parallel Fetch with Semaphore Pattern

```python
async def fetch_parallel(self, sections: list[Section]) -> list[Task]:
    """Fetch section tasks in parallel with rate limiting."""
    semaphore = asyncio.Semaphore(8)  # Limit concurrent requests

    async def fetch_section(section: Section) -> list[Task]:
        async with semaphore:
            return await self._tasks.list_async(section=section.gid).collect()

    # Execute all sections concurrently (bounded by semaphore)
    results = await asyncio.gather(
        *[fetch_section(s) for s in sections],
        return_exceptions=True
    )

    # Check for failures, fall back if any
    if any(isinstance(r, Exception) for r in results):
        logger.warning("parallel_fetch_failed_fallback_to_serial")
        return await self._fetch_serial()

    # Deduplicate multi-homed tasks
    return self._deduplicate_by_gid(flatten(results))
```

**When to use**: Independent API calls, multiple sections/projects, read-heavy operations

**When NOT to use**: Dependent operations (create parent before child), write-heavy operations, rate-limit-constrained scenarios

### Request Coalescing Pattern

```python
class RequestCoalescer:
    """Batch requests within time window."""

    async def request_check_async(self, entry: CacheEntry) -> str | None:
        async with self._lock:
            gid = entry.key

            # Deduplication: reuse existing future for same GID
            if gid in self._pending:
                existing_future = self._pending[gid][1]
                return await existing_future

            # Create future for this request
            future = asyncio.get_event_loop().create_future()
            self._pending[gid] = (entry, future)

            # Start timer on first request
            if self._timer_task is None or self._timer_task.done():
                self._timer_task = asyncio.create_task(self._timer_flush())

            # Immediate flush if max batch reached
            if len(self._pending) >= self.max_batch:
                await self._flush_batch()

        return await future

    async def _timer_flush(self) -> None:
        """Wait for window, then flush."""
        await asyncio.sleep(self.window_ms / 1000)
        async with self._lock:
            if self._pending:
                await self._flush_batch()
```

**When to use**: Bursty request patterns, lightweight cache checks, deduplicable operations

**When NOT to use**: Latency-critical operations where 50ms wait is unacceptable, single-request scenarios

## Configuration

Performance-related settings are tunable via environment variables and client configuration:

```python
# Async concurrency
ASYNC_CONCURRENCY_LIMIT = 10  # asyncio.Semaphore limit

# Batch settings
BATCH_SIZE = 10  # Asana API hard limit, not configurable
BATCH_SEQUENTIAL = True  # Per ADR-0010, parallel not supported

# Lazy evaluation threshold
LAZY_THRESHOLD = 100  # Tasks; eager below, lazy above

# Parallel section fetch
PARALLEL_SECTION_FETCH_ENABLED = True
MAX_CONCURRENT_SECTIONS = 8  # Semaphore limit
SECTION_FETCH_FALLBACK_ENABLED = True

# Request coalescing
COALESCE_WINDOW_MS = 50  # Time window for batching
COALESCE_MAX_BATCH = 100  # Maximum entries per batch

# Rate limiting (existing)
RATE_LIMIT_REQUESTS_PER_MINUTE = 1500  # Asana default
```

## Monitoring and Observability

Key metrics for performance monitoring:

```python
# Latency metrics
"operation_duration_ms": Histogram  # All async operations
"parallel_fetch_duration_ms": Histogram  # Section-parallel fetches
"coalesce_window_utilization_ms": Histogram  # Actual wait time in coalescing

# Throughput metrics
"batch_chunk_count": Histogram  # Chunks per batch operation
"batch_requests_per_operation": Histogram  # API calls per batch
"parallel_section_fetch_count": Counter  # Parallel fetches executed

# Efficiency metrics
"stories_incremental_fetch_saved_stories": Histogram  # Bandwidth savings
"coalesce_batch_size": Histogram  # Entries per coalesced batch
"coalesce_dedup_count": Counter  # Duplicate GID requests avoided
"lazy_evaluation_memory_savings_bytes": Histogram  # Memory reduction

# Fallback metrics
"parallel_fetch_fallback_count": Counter  # Fallbacks to serial
"sync_wrapper_async_context_error": Counter  # Fail-fast triggers
```

## Testing Strategy

Performance decisions require specific test coverage:

### Unit Tests
- Async-first: Verify sync wrapper detects async context and fails fast
- Batching: Verify chunking into 10s, sequential execution order
- Incremental loading: Test merge algorithm, atomic updates, deduplication
- Lazy evaluation: Test threshold logic, both eager and lazy paths
- Coalescing: Test timer flush, max batch flush, GID deduplication

### Integration Tests
- Parallel section fetch: Verify latency improvement, fallback on failure
- Batch resolution: Verify shared lookups, concurrent fetching
- Incremental stories: Verify `since` parameter usage, merge correctness
- Request coalescing: Verify batching efficiency under load

### Performance Tests
- Benchmark cold-start latency (DataFrame extraction)
- Measure batch operation throughput
- Profile memory usage with lazy vs eager
- Validate rate limit compliance under heavy load

## Common Pitfalls

### 1. Calling Sync Methods from Async Context

**Problem**: `RuntimeError: Cannot call sync method from async context`

**Cause**: Sync wrapper detects running event loop (fail-fast per ADR-0002)

**Fix**: Use async variant:
```python
# Bad
async def process():
    task = client.tasks.get(gid)  # Error!

# Good
async def process():
    task = await client.tasks.get_async(gid)
```

### 2. Excessive Batch Size

**Problem**: Attempting to batch more than 10 operations in single request

**Cause**: Asana API limit of 10 actions per batch request

**Fix**: SDK automatically chunks; no user action needed. If manually constructing BatchRequest, split into chunks of 10.

### 3. Parallel Section Fetch Disabled

**Problem**: DataFrame extraction still slow despite parallel fetch feature

**Cause**: `PARALLEL_SECTION_FETCH_ENABLED=False` or client initialized before feature

**Fix**: Verify configuration, use `build_async()` method (sync `build()` doesn't use parallel fetch)

### 4. Coalescing Window Too Long

**Problem**: Individual requests experiencing high latency

**Cause**: `COALESCE_WINDOW_MS` set too high (e.g., 500ms)

**Fix**: Use default 50ms or tune based on access patterns. For latency-critical operations, disable coalescing.

### 5. LazyFrame Exposed in API

**Problem**: Users receiving `pl.LazyFrame` instead of `pl.DataFrame`

**Cause**: Custom code not calling `.collect()` on lazy path

**Fix**: Always return `pl.DataFrame` from public APIs. Call `.collect()` internally on lazy path.

## Future Optimizations

Potential performance improvements not yet implemented:

### Parallel Batch Execution (Opt-In)
- **Description**: Execute batch chunks in parallel instead of sequentially
- **Benefit**: 5x throughput for large independent batches
- **Complexity**: High (error handling, result correlation, rate limit management)
- **Decision**: Deferred - sequential is sufficient for current use cases (ADR-0010)

### Adaptive Coalescing Window
- **Description**: Adjust window based on request rate (more requests = shorter window)
- **Benefit**: Automatic tuning for different traffic patterns
- **Complexity**: Medium (rate tracking, dynamic timing)
- **Decision**: Deferred - fixed 50ms window is sufficient (ADR-0132)

### Background Pre-Fetch
- **Description**: Background process continuously fetches and caches hot data
- **Benefit**: Near-instant response from warm cache
- **Complexity**: Very High (infrastructure, freshness management, resource usage)
- **Decision**: Deferred - parallel section fetch achieves <10s without background processes

### Streaming DataFrame Builder
- **Description**: Yield DataFrame rows as they're fetched (generator pattern)
- **Benefit**: Lower memory for huge projects, faster time-to-first-row
- **Complexity**: Medium (API change, user code changes)
- **Decision**: Deferred - dict/list return is sufficient for expected sizes

## Related Documentation

- **PRD-0001**: SDK Extraction (async-first requirement)
- **PRD-0005**: Save Orchestration (batching requirements)
- **PRD-0002**: Intelligent Caching (incremental loading requirements)
- **TDD-0005**: Batch API for Bulk Operations
- **TDD-0008**: Intelligent Caching
- **TDD-0010**: Save Orchestration

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| [ADR-0002](ADR-0002-sync-wrapper-strategy.md) | Fail-Fast Strategy for Sync Wrappers in Async Contexts | 2025-12-08 | Sync wrappers detect async context and fail with helpful error |
| [ADR-0010](ADR-0010-batch-chunking-strategy.md) | Sequential Chunk Execution for Batch Operations | 2025-12-08 | Execute batch chunks sequentially (not parallel) for predictable ordering |
| [ADR-0015](ADR-0015-batch-api-request-format.md) | Batch API Request Format Fix | 2025-12-09 | Wrap batch actions in `{"data": {"actions": [...]}}` envelope |
| [ADR-0020](ADR-0020-incremental-story-loading.md) | Incremental Story Loading | 2025-12-09 | Use `since` parameter to fetch only new stories, merge with cached |
| [ADR-0031](ADR-0031-lazy-eager-evaluation.md) | Lazy vs Eager Evaluation | 2025-12-09 | Auto-select lazy (>100 tasks) vs eager (≤100) with override parameter |
| [ADR-0038](ADR-0038-save-concurrency-model.md) | Async-First Concurrency for Save Operations | 2025-12-10 | SaveSession uses async-first with sync wrappers per ADR-0002 pattern |
| [ADR-0039](ADR-0039-batch-execution-strategy.md) | Fixed-Size Sequential Batch Execution | 2025-12-10 | Fixed 10-action batches, sequential per dependency level |
| [ADR-0057](ADR-0057-subtasks-async-method.md) | Add subtasks_async Method to TasksClient | 2025-12-12 | Add `subtasks_async()` returning `PageIterator[Task]` |
| [ADR-0073](ADR-0073-batch-resolution-api-design.md) | Batch Resolution API Design | 2025-12-16 | Module-level functions for batch resolution with shared lookups |
| [ADR-0115](ADR-0115-parallel-section-fetch-strategy.md) | Parallel Section Fetch Strategy | 2025-12-23 | Fetch sections in parallel with semaphore (8 concurrent, 50s → 8s) |
| [ADR-0132](ADR-0132-batch-request-coalescing-strategy.md) | Batch Request Coalescing Strategy | 2025-12-24 | 50ms window, 100-entry max batch, immediate flush at max |

---

**Consolidation Date**: 2025-12-25
**Maintainer**: Architecture Team
**Next Review**: Q1 2026 (or when new performance patterns emerge)
