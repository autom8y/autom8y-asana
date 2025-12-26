# ADR-0028: Parallelization and Request Optimization

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0057, ADR-0073, ADR-0115, ADR-0132
- **Related**: PRD-SDKDEMO, PRD-RESOLUTION, PRD-WATERMARK-CACHE, TDD-0002, TDD-RESOLUTION, TDD-WATERMARK-CACHE, ADR-0021 (DataFrame Caching Strategy)

## Context

As the SDK evolved, several opportunities emerged for optimizing request patterns through parallelization and intelligent batching:

1. **Subtasks Access**: Business models and demos need paginated subtask fetching
2. **Batch Resolution**: Resolving multiple AssetEdits to Units/Offers is high-frequency
3. **Parallel Section Fetch**: Project DataFrame extraction takes 52-59s due to serial pagination
4. **Request Coalescing**: Multiple expired cache entries need staleness checks within short time windows

All these scenarios share common themes: reduce API calls, minimize latency, and respect rate limits.

**Forces at play**:
- Asana rate limit: 1500 requests per minute (25 req/s)
- Network latency dominates fetch time for I/O operations
- Sections provide natural parallelization boundaries
- Burst access patterns can trigger many identical requests
- Memory constraints limit unbounded batching
- Complexity must be justified by measurable benefits

## Decision

**Implement targeted parallelization and batching optimizations for specific high-value scenarios while maintaining safe defaults.**

### 1. Subtasks Pagination Method

Add `subtasks_async()` method to TasksClient following the `list_async()` pattern:

```python
def subtasks_async(
    self,
    task_gid: str,
    *,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Task]:
    """Get subtasks of a parent task with automatic pagination.

    Returns a PageIterator that lazily fetches pages as you iterate.

    Example:
        # Iterate all subtasks
        async for subtask in client.tasks.subtasks_async(parent_gid):
            print(subtask.name)

        # Collect all
        all_subtasks = await client.tasks.subtasks_async(parent_gid).collect()
    """
    self._log_operation("subtasks_async", task_gid)

    async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
        """Fetch a single page of subtasks."""
        params = self._build_opt_fields(opt_fields)
        params["limit"] = min(limit, 100)  # Asana max is 100
        if offset:
            params["offset"] = offset

        data, next_offset = await self._http.get_paginated(
            f"/tasks/{task_gid}/subtasks", params=params
        )
        tasks = [Task.model_validate(t) for t in data]
        return tasks, next_offset

    return PageIterator(fetch_page, page_size=min(limit, 100))
```

**No sync wrapper**: PageIterator is inherently async; sync version would require collecting all results, changing API contract.

### 2. Batch Resolution with Shared Lookups

Module-level functions for batch resolution of AssetEdits to Units/Offers:

```python
# Module functions in src/autom8_asana/models/business/resolution.py

async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Batch resolve multiple AssetEdits to Units.

    Optimizations:
    1. Group by Business: Identify unique Businesses
    2. Bulk hydration: Fetch each Business.units once
    3. Concurrent dependents: For DEPENDENT_TASKS strategy
    4. Shared lookups: Batch fetch unique offer_ids

    Returns:
        Dict mapping asset_edit.gid to ResolutionResult
    """
    # 1. Collect unique Businesses
    businesses = _collect_unique_businesses(asset_edits)

    # 2. Ensure all Businesses have units hydrated
    await asyncio.gather(*[
        _ensure_units_hydrated(b, client) for b in businesses.values()
    ])

    # 3. Pre-fetch strategy-specific data concurrently
    if strategy in (ResolutionStrategy.AUTO, ResolutionStrategy.DEPENDENT_TASKS):
        dependents_map = await _batch_fetch_dependents(asset_edits, client)

    # 4. Resolve each AssetEdit using pre-fetched data
    results = {}
    for ae in asset_edits:
        result = await _resolve_single_with_context(
            ae, client, strategy,
            dependents=dependents_map.get(ae.gid, []),
            business=businesses.get(ae._business.gid if ae._business else None),
        )
        results[ae.gid] = result

    return results
```

**Return type**: Dictionary mapping `asset_edit.gid` to `ResolutionResult` for O(1) lookup.

**Module-level function rationale**: Natural for collection operations (vs class methods operating on single instance); clearer signature; matches `asyncio.gather()` pattern.

### 3. Parallel Section Fetch

Fetch tasks from sections in parallel with semaphore control:

```python
# Enumerate sections in project
sections = await sections_client.list_for_project_async(project_gid).collect()

# Limit concurrent requests to 8
semaphore = asyncio.Semaphore(8)

async def fetch_section(section_gid):
    async with semaphore:
        return await tasks_client.list_async(section=section_gid).collect()

# Execute all sections concurrently
results = await asyncio.gather(
    *[fetch_section(s.gid) for s in sections],
    return_exceptions=True
)

# Check for exceptions, fallback if any
if any(isinstance(r, Exception) for r in results):
    logger.warning("parallel_fetch_failed_fallback_to_serial")
    tasks = await tasks_client.list_async(project=project_gid).collect()
else:
    tasks = deduplicate_by_gid(flatten(results))
```

**Semaphore limit (8)**:
- Asana rate limit: 1500 req/60s = 25 req/s
- With 8 concurrent at ~500ms each: 16 req/s (safe margin)
- Typical project has 8-12 sections, so 8 concurrent covers most in single batch

**Fail-all with fallback**: Partial results are dangerous (missing sections = missing tasks). On any parallel fetch failure:
1. Fail the entire parallel fetch
2. Automatically fall back to serial project-level fetch
3. Log warning for observability
4. Ensures correctness over performance

### 4. Request Coalescing

Time-bounded coalescing with 50ms window, 100-entry max batch, immediate flush on max:

```python
class RequestCoalescer:
    """Batches staleness check requests within a time window."""

    async def request_check_async(self, entry: CacheEntry) -> str | None:
        async with self._lock:
            gid = entry.key

            # Deduplication: if GID already pending, reuse its future
            if gid in self._pending:
                existing_entry, existing_future = self._pending[gid]
                return await existing_future

            # Create new future for this request
            future: asyncio.Future[str | None] = asyncio.get_event_loop().create_future()
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

**Coalescing parameters**:
- **50ms window**: Balances latency vs batching efficiency (typical DataFrame ops: 100-500ms, so 50ms is small fraction)
- **100-entry max**: Memory-bounded (~100KB), translates to 10 Asana batch requests (10 actions each)
- **Immediate flush at max**: Prevents unbounded wait for large bursts
- **GID deduplication**: Same GID appears once, all callers get same result

## Rationale

### Why Subtasks Method Named `subtasks_async`

**Consistency with usage**:
- Demo script already uses `subtasks_async()`
- Business model comments reference this name
- More concise than `list_subtasks_async()`

**Pattern consideration**:
- `list_*` suggests collection of top-level resources
- `subtasks_async()` clearly indicates relationship traversal
- Other SDKs commonly use `subtasks()` rather than `list_subtasks()`

### Why Module-Level Functions for Batch Resolution

**No natural class home**:
- Batch resolution operates on a collection, not a single entity
- Cleaner signature than `AssetEdit.resolve_units_batch_async(...)`
- Similar to how `asyncio.gather()` is a module function

**Separation from transport layer**:
- Resolution is business model logic, not transport
- Entity-specific, not a general task operation
- Consistency with business model patterns

**Flexibility**:
- Works with any collection of AssetEdits
- Not limited to single holder's children
- Callers may have mixed collections from different sources

### Why Section-Parallel Over Page-Parallel

**Natural parallelization unit**:

| Approach | Pros | Cons |
|----------|------|------|
| **Section-parallel** | Independent sections, API-supported, simple coordination | Requires section enum call, doesn't parallelize large sections |
| Page-parallel | Could parallelize within sections | Complex offset coordination, depends on knowing total count, race conditions |
| Task-level parallel | Maximum parallelism | Excessive API calls, rate limit exhaustion |

Sections are the right abstraction: independent, API-supported, typical project has 8-12 sections providing sufficient parallelism.

### Why 50ms Coalescing Window

**Latency vs batching tradeoff**:

| Window | Batching Potential | Added Latency | Use Case |
|--------|-------------------|---------------|----------|
| 10ms | Low | Minimal | Low-latency single operations |
| **50ms** | **Medium-High** | **Acceptable** | **DataFrame refresh, parallel access** |
| 100ms | High | Noticeable | Extreme batch optimization |

50ms provides good batching (typical DataFrame ops: 100-500ms, so 50ms is small fraction) while keeping added latency imperceptible.

### Why 100 Max Batch for Coalescing

**Memory and performance balance**:

| Max Batch | Memory | Chunks | Latency Risk |
|-----------|--------|--------|--------------|
| 50 | Low | 5 | Low |
| **100** | **Medium** | **10** | **Medium** |
| 500 | High | 50 | High |

100 entries = 10 Asana batch requests (10 actions each):
- Sufficient for most DataFrame operations
- Memory-bounded (~100KB for 100 CacheEntry references)
- Reasonable processing time (~1-2s for 10 sequential batch calls)
- Immediate flush prevents long waits for bursts

## Alternatives Considered

### For Parallel Section Fetch

#### Alternative 1: Page-Parallel Fetch

**Description**: Parallelize pagination within a single project query by predicting page offsets.

**Pros**: Could parallelize even single-section projects

**Cons**:
- Requires knowing total task count upfront (additional API call)
- Page boundaries may shift during parallel fetch
- Complex offset coordination

**Why not chosen**: Too complex; section-parallel achieves 80% of benefit with 20% of complexity.

#### Alternative 2: No Parallelization (Optimize Serial)

**Description**: Keep serial fetch, optimize page size, reduce opt_fields.

**Pros**: No coordination complexity, no rate limit risk

**Cons**: Still O(pages) latency, cannot achieve <10s target for 3,500 tasks

**Why not chosen**: Cannot meet performance requirements.

### For Request Coalescing

#### Alternative 1: No Coalescing (Individual Requests)

**Description**: Each expired entry triggers immediate lightweight check.

**Pros**: Simplest, zero added latency

**Cons**: No bandwidth savings, rate limit risk, defeats purpose of lightweight checks

**Why not chosen**: Batching is fundamental to efficiency gains.

#### Alternative 2: Count-Based Batching (No Time Window)

**Description**: Batch flushes only when reaching N entries, with timeout fallback.

**Pros**: Optimal batch sizes, simpler timing

**Cons**: Single request waits up to 5s for batch companions, poor latency for low-volume

**Why not chosen**: Time-bounded coalescing provides predictable latency (max 50ms).

#### Alternative 3: Adaptive Window (Dynamic Timing)

**Description**: Adjust window based on request rate.

**Pros**: Optimal for all traffic patterns, automatic tuning

**Cons**: Complex implementation, requires rate tracking, harder to reason about

**Why not chosen**: Fixed 50ms window is simpler and sufficient. Adaptive tuning can be added later.

## Consequences

### Positive

**Subtasks Method**:
- Demo works correctly
- Business hierarchy prefetching unlocked
- Pattern consistent with `list_async()`
- Memory efficient (PageIterator avoids loading all at once)

**Batch Resolution**:
- Clear API (module function with explicit inputs)
- Efficient (shared lookups, concurrent fetches)
- Flexible (works with any collection)
- Composable (results can be filtered, merged, iterated)
- For 100 AssetEdit resolutions: 100+ API calls → ~12 API calls (88% reduction)

**Parallel Section Fetch**:
- 80% latency reduction (52s → ~8s for 3,500-task project)
- Rate-limit safe (8 concurrent with semaphore stays under limits)
- Graceful degradation (automatic fallback preserves correctness)
- No external dependencies (uses asyncio primitives)
- Backward compatible (new `build_async()` method)

**Request Coalescing**:
- Efficient batching (multiple requests combined)
- Predictable latency (max 50ms added wait)
- Memory-bounded (100-entry limit)
- Deduplication (same GID checked once)
- Responsive (immediate flush at max prevents long waits)
- For 100 staleness checks: 100 GET requests → 10 batch requests (90% reduction)

### Negative

**Subtasks Method**:
- No sync version (PageIterator is inherently async)
- Name precedent establishes `subtasks_async` over `list_subtasks_async`

**Batch Resolution**:
- Import required (callers must import from resolution module)
- Less discoverable (not visible on entity or client)
- New pattern (introduces module-function pattern)

**Parallel Section Fetch**:
- Additional API call (section enumeration adds 1 call)
- Increased complexity (more error handling paths)
- Memory overhead (holding tasks from all sections before merge)
- Not optimal for single-section projects

**Request Coalescing**:
- 0-50ms added latency for first request in batch
- Async coordination complexity (careful locking required)
- Debugging complexity (batch timing)
- Pending batch lost on process crash

### Neutral

**Subtasks Method**:
- API expansion (one new public method)
- Test coverage required

**Batch Resolution**:
- Sync wrappers follow same pattern
- Documentation provides examples
- Batch functions exported from `models.business` for discoverability

**Parallel Section Fetch**:
- Async-only (only via `build_async()`)
- New `max_concurrent_sections` config option

**Request Coalescing**:
- Configurable (window and max batch tunable)
- Observable (metrics for batch size, window utilization)
- Testable (clear flush triggers)

## Performance Characteristics

### Latency Improvements

| Operation | Before | After | Improvement | Optimization |
|-----------|--------|-------|-------------|--------------|
| Project DataFrame (3,500 tasks) | 52-59s | ~8s | 80% reduction | Parallel section fetch |
| 100 AssetEdit resolutions | 100+ API calls | ~12 API calls | 88% reduction | Batch resolution |
| 100 staleness checks (burst) | 100 GET requests | 10 batched requests | 90% reduction | Request coalescing |

### Throughput Improvements

- Parallel section fetch: ~6x faster for multi-section projects
- Batch resolution: ~8x fewer API calls when resolving collections
- Request coalescing: ~10x fewer requests for burst access patterns

## Implementation Patterns

### Parallel with Semaphore

```python
async def fetch_parallel(sections: list[Section]) -> list[Task]:
    """Fetch section tasks in parallel with rate limiting."""
    semaphore = asyncio.Semaphore(8)

    async def fetch_section(section: Section) -> list[Task]:
        async with semaphore:
            return await tasks_client.list_async(section=section.gid).collect()

    results = await asyncio.gather(
        *[fetch_section(s) for s in sections],
        return_exceptions=True
    )

    if any(isinstance(r, Exception) for r in results):
        return await fallback_serial_fetch()

    return deduplicate_by_gid(flatten(results))
```

### Batch with Shared Lookups

```python
async def resolve_batch(entities: list[Entity]) -> dict[str, Result]:
    """Resolve with shared lookups."""
    # 1. Collect unique lookup keys
    unique_keys = _collect_unique(entities)

    # 2. Bulk fetch shared data
    await asyncio.gather(*[_fetch(key) for key in unique_keys])

    # 3. Resolve each entity using pre-fetched data
    return {e.gid: _resolve(e) for e in entities}
```

### Time-Bounded Coalescing

```python
class Coalescer:
    async def request(self, item) -> Result:
        async with self._lock:
            if item in self._pending:
                return await self._pending[item]

            future = create_future()
            self._pending[item] = future

            if not self._timer_task:
                self._timer_task = create_task(self._timer_flush())

            if len(self._pending) >= self.max_batch:
                await self._flush()

        return await future
```

## Compliance

### Subtasks Method

- Method MUST be named `subtasks_async()`
- Return type MUST be `PageIterator[Task]`
- MUST follow `list_async()` pattern exactly
- No sync wrapper (PageIterator is async-only)

### Batch Resolution

- Batch functions MUST be module-level in `resolution.py`
- Return type MUST be `dict[str, ResolutionResult[T]]`
- Every input MUST have entry in result dict
- MUST optimize shared lookups
- MUST be exported from `models.business.__init__.py`

### Parallel Section Fetch

- MUST use `asyncio.gather()` with `return_exceptions=True`
- MUST wrap section fetches with semaphore
- MUST implement fallback to serial on any failure
- MUST deduplicate multi-homed tasks by GID
- Unit tests for parallel, fallback, deduplication

### Request Coalescing

- Window MUST default to 50ms
- Max batch MUST default to 100 entries
- MUST flush immediately at max batch
- MUST deduplicate by GID
- MUST use asyncio.Future for result distribution

## Cross-References

- **ADR-0025**: Async-first pattern enables parallelization
- **ADR-0026**: Sequential batching within parallel operations
- **ADR-0018**: Batch modification checking uses coalescing
- **ADR-SUMMARY-CACHE**: Caching strategies using these optimizations
- **ADR-SUMMARY-DATA-MODEL**: DataFrame layer uses parallel section fetch
