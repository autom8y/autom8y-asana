# ADR-0027: Incremental Loading and Lazy Evaluation

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0020, ADR-0031
- **Related**: PRD-0002 (FR-CACHE-025, FR-CACHE-041-043), PRD-0003 (Design Decision 3), TDD-0008, TDD-0009, ADR-0028 (Polars DataFrame Library)

## Context

The SDK faces two related optimization challenges for handling large data volumes:

1. **Incremental Loading**: Tasks accumulate hundreds of stories (comments, activity logs) over time. Re-fetching all stories when only a few are new wastes API quota and bandwidth.

2. **Lazy Evaluation**: Polars DataFrame operations can be eager (immediate execution) or lazy (deferred with query optimization). For large datasets, lazy evaluation provides significant memory and performance benefits through predicate pushdown, projection optimization, and parallelization.

Both challenges share a common theme: optimize resource usage by loading or processing only what's needed, when it's needed.

**Forces at play**:
- **Bandwidth efficiency**: Full story reload for 200 stories wastes ~99% of bandwidth if only 2 are new
- **Memory efficiency**: Materializing all intermediate DataFrame operations for 10,000 tasks causes memory pressure
- **Performance**: Lazy evaluation enables 20-40% faster query execution through optimization
- **Debugging**: Eager evaluation provides clearer error messages and intermediate inspection
- **API capabilities**: Asana `since` parameter enables incremental story fetching
- **Data immutability**: Stories are append-only (never updated or deleted)

## Decision

**Implement incremental loading for immutable append-only data (stories) and auto-select lazy vs eager evaluation based on a 100-task threshold.**

### Incremental Story Loading

Use Asana API `since` parameter to fetch only new stories, merge with cached stories, and update cache atomically.

```python
async def get_stories(
    self,
    task_gid: str,
    use_cache: bool = True,
) -> list[Story]:
    """Get all stories for a task with incremental loading."""
    if not use_cache:
        return await self._fetch_all_stories(task_gid)

    # Try to get cached stories
    cached = await self._cache.get_versioned(task_gid, EntryType.STORIES)

    if cached is None:
        # No cache, full fetch
        stories = await self._fetch_all_stories(task_gid)
        await self._cache_stories(task_gid, stories)
        return stories

    # Incremental fetch
    last_story_at = cached.metadata.get("last_story_at")
    new_stories = await self._fetch_stories_since(task_gid, last_story_at)

    if not new_stories:
        # No new stories, return cached
        return [Story.model_validate(s) for s in cached.data["stories"]]

    # Merge: cached + new (new are appended, already in order)
    all_stories = cached.data["stories"] + [s.model_dump() for s in new_stories]

    # Update cache atomically
    await self._cache_stories(task_gid, all_stories)
    return [Story.model_validate(s) for s in all_stories]

async def _fetch_stories_since(
    self,
    task_gid: str,
    since: datetime,
) -> list[Story]:
    """Fetch stories created after given timestamp."""
    params = {
        "since": since.isoformat(),
        "opt_fields": "created_at,created_by,text,type,resource_subtype",
    }
    async for page in self._http.paginate(f"/tasks/{task_gid}/stories", params):
        for story_data in page:
            stories.append(Story.model_validate(story_data))
    return stories
```

**Cache structure**:
```
asana:tasks:{gid}:stories
    data: {"stories": [...]}
    version: <last_story_at>
    cached_at: <cache write timestamp>
    metadata: {"last_story_at": "2025-12-09T10:30:00Z"}
```

**Merge algorithm**:
```
Cached Stories:  [S1, S2, S3, S4, S5]  (last_story_at = S5.created_at)
                       ↓
API Call: GET /tasks/{gid}/stories?since=S5.created_at
                       ↓
New Stories:     [S6, S7]  (created after S5)
                       ↓
Merged Result:   [S1, S2, S3, S4, S5, S6, S7]
                       ↓
Cache Updated:   stories = merged, last_story_at = S7.created_at
```

### Lazy vs Eager Evaluation

Auto-select evaluation mode based on 100-task threshold with explicit override:

```python
def _should_use_lazy(task_count: int, lazy: bool | None) -> bool:
    """Determine evaluation mode based on threshold.

    Args:
        task_count: Number of tasks to process
        lazy: Explicit override (True/False) or None for auto

    Returns:
        True if lazy evaluation should be used
    """
    if lazy is not None:
        return lazy  # Explicit override wins
    return task_count > LAZY_THRESHOLD  # Auto-select based on threshold

LAZY_THRESHOLD = 100  # Configurable via environment

class DataFrameBuilder:
    def build(
        self,
        tasks: list[Task],
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        task_count = len(tasks)
        use_lazy = self._should_use_lazy(task_count, lazy)

        if use_lazy:
            return self._build_lazy(tasks)
        else:
            return self._build_eager(tasks)

    def _build_eager(self, tasks: list[Task]) -> pl.DataFrame:
        """Eager path: Build DataFrame directly from rows."""
        rows = [self._extract_row(task) for task in tasks]
        return pl.DataFrame(rows, schema=self._schema.to_polars_schema())

    def _build_lazy(self, tasks: list[Task]) -> pl.DataFrame:
        """Lazy path: Build LazyFrame, then collect."""
        rows = [self._extract_row(task) for task in tasks]
        lf = pl.LazyFrame(rows, schema=self._schema.to_polars_schema())
        optimized = lf.select(self._schema.column_names())
        return optimized.collect()  # Return DataFrame, not LazyFrame
```

**API signature**:
```python
def to_dataframe(
    self,
    task_type: str | None = None,
    concurrency: int = 10,
    use_cache: bool = True,
    lazy: bool | None = None,  # None = auto, True = force lazy, False = force eager
) -> pl.DataFrame:
    """Generate typed DataFrame from project tasks.

    Args:
        lazy: Evaluation mode override.
            - None (default): Auto-select based on 100-task threshold
            - True: Force lazy evaluation (LazyFrame.collect())
            - False: Force eager evaluation (DataFrame)

    Returns:
        Always returns pl.DataFrame (LazyFrame is collected internally)
    """
```

## Rationale

### Why Incremental Loading for Stories

**Dramatic efficiency gains**:

| Scenario | Full Reload | Incremental | Savings |
|----------|-------------|-------------|---------|
| 200 stories, 2 new | 3 API calls, 200 stories transferred | 1 API call, 2 stories transferred | 67% API calls, 99% bandwidth |
| 50 stories, 5 new | 1 API call, 50 stories | 1 API call, 5 stories | Same calls, 90% bandwidth |

**Why use `created_at` as version**:
- Stories are immutable: once created, never modified
- No updates, only additions
- `created_at` uniquely identifies story age
- Newest story's `created_at` (`last_story_at`) serves as version marker
- Simple comparison for staleness
- Reliable `since` parameter for API

**Why atomic cache update**:

Race condition without atomicity:
```
1. Process A reads cache, fetches new stories
2. Process B reads cache, fetches new stories
3. Process A writes merged result
4. Process B writes merged result (overwrites A's additions!)
```

With Redis WATCH/MULTI:
```
1. WATCH the stories key
2. Read current value
3. Merge with new stories
4. MULTI: SET new value
5. EXEC (fails if key changed since WATCH)
6. On failure, retry from step 1
```

### Why 100-Task Threshold for Lazy Evaluation

**Aligns with concurrency model**:

| Factor | Value | Calculation |
|--------|-------|-------------|
| Default concurrency | 10 workers | From PRD-0003 |
| Batch size | ~10 tasks/worker | Balanced distribution |
| Threshold | 100 tasks | 10 workers × 10 tasks |

**Empirical performance data**:
- 10-50 tasks: Eager ~5% faster (no planning overhead)
- 100 tasks: ~Equal performance
- 500+ tasks: Lazy 20-40% faster (optimization benefits)

**Memory inflection point**:
- At 100 tasks with 32 columns, memory footprint becomes significant
- Lazy evaluation reduces peak memory through projection pushdown
- Below 100: memory is not a constraint

**Best of both worlds**:
- Small extractions (≤100): Simple debugging with eager mode
- Large extractions (>100): Performance optimization with lazy mode
- Power users can override when needed

### Why Always Return DataFrame (Not LazyFrame)

**Simpler API**:
- Users don't need to handle two types
- Consistent return type
- Type annotations are unambiguous

**Prevents user error**:
- Users can't forget `.collect()`
- No accidentally holding uncollected LazyFrame

**Internal optimization**:
- Lazy evaluation is implementation detail
- Users get ready-to-use DataFrame

## Alternatives Considered

### For Incremental Loading

#### Alternative 1: Always Full Reload

**Description**: Fetch all stories on every request, no incremental logic.

**Pros**:
- Simple implementation
- No merge complexity
- Always consistent

**Cons**:
- Wasteful for large story collections
- Unnecessary API calls
- Higher latency for heavily-commented tasks

**Why not chosen**: Inefficient for the common case of few new stories on subsequent reads.

#### Alternative 2: Story-Level Caching

**Description**: Cache each story individually by GID.

**Pros**:
- Fine-grained cache control
- Individual story invalidation

**Cons**:
- Many cache keys (one per story)
- Complex to collect all stories for a task
- No benefit since stories are immutable
- Higher Redis memory overhead

**Why not chosen**: Over-engineered for immutable resources. List caching is simpler and sufficient.

#### Alternative 3: Webhook-Triggered Story Updates

**Description**: Use webhooks to push new stories to cache in real-time.

**Pros**:
- Real-time updates
- No polling or `since` queries
- Cache always current

**Cons**:
- Requires webhook infrastructure
- Webhook delivery not guaranteed
- SDK becomes dependent on consumer webhook setup
- Complex webhook event processing

**Why not chosen**: Webhooks are optional. SDK must work without them.

### For Lazy Evaluation

#### Alternative 1: Always Lazy

**Description**: Use LazyFrame for all extractions, regardless of size.

**Pros**:
- Consistent behavior
- Always optimized
- Simpler implementation (one path)

**Cons**:
- Debugging difficulty for all cases
- Query planning overhead for small datasets
- Errors surface at `.collect()`, not at operation
- Overkill for 10-task extractions

**Why not chosen**: Debugging ease for small extractions is valuable. Fixed overhead not justified for small datasets.

#### Alternative 2: Always Eager

**Description**: Use DataFrame for all extractions, regardless of size.

**Pros**:
- Simplest implementation
- Best debugging experience
- Immediate error feedback

**Cons**:
- Performance penalty at scale
- Higher memory usage for large extractions
- No query optimization
- Doesn't meet NFR-PERF-009 (10,000 tasks without OOM)

**Why not chosen**: Performance and memory requirements for large projects demand lazy evaluation.

#### Alternative 3: User Always Chooses

**Description**: Require `lazy=True` or `lazy=False` parameter with no default.

**Pros**:
- Explicit user control
- No hidden magic

**Cons**:
- Burden on every API call
- Users must learn lazy vs eager
- Most users don't care / shouldn't need to care
- Friction for simple use cases

**Why not chosen**: SDK should have sensible defaults. Most users just want a DataFrame.

#### Alternative 4: Return LazyFrame with User Collect

**Description**: Return `LazyFrame`; let users call `.collect()` when ready.

**Pros**:
- Maximum flexibility
- Users can add operations before collect
- Polars-idiomatic

**Cons**:
- Breaking change from expected DataFrame return
- Users must remember to collect
- Type annotation complexity
- Easy to accidentally hold uncollected LazyFrame

**Why not chosen**: SDK should return ready-to-use DataFrame. Users who want LazyFrame can use Polars directly.

## Consequences

### Positive

**Incremental Loading**:
- Significant API call reduction for story-heavy tasks
- Lower latency (less data transferred)
- Efficient cache usage (only store/transfer what's needed)
- Consistent ordering (stories always chronological)
- Simple mental model (cache = all stories, fetch = what's new)

**Lazy Evaluation**:
- Optimal performance by default for large extractions
- Easy debugging for small cases (eager mode)
- User control available (`lazy` parameter)
- Consistent return type (always `pl.DataFrame`)
- Memory efficiency (large extractions benefit from lazy)
- Transparent (users don't need to learn unless they want to)

### Negative

**Incremental Loading**:
- Story deletion not detected (mitigated by TTL expiration; rare in practice)
- Merge complexity (requires atomic updates)
- Story count changes trigger full refresh
- `since` parameter precision required

**Lazy Evaluation**:
- Two code paths to test and maintain (eager and lazy)
- Threshold is somewhat arbitrary (though empirically validated)
- Hidden behavior (mode switching could surprise users)
- Slight overhead for threshold check

### Neutral

**Incremental Loading**:
- Metadata field added (`last_story_at` in cache entry)
- Version field overloaded (uses `last_story_at` as version)
- Full refresh available (`refresh_stories()` method)

**Lazy Evaluation**:
- Configurable post-MVP (threshold can become configurable)
- Documentation needed (users should understand threshold exists)
- Logging recommended (log which mode selected for observability)

## Performance Characteristics

### Incremental Loading Impact

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Task with 200 stories, 2 new | 3 API calls (200 stories) | 1 API call (2 stories) | 67% fewer calls, 99% bandwidth savings |

### Lazy Evaluation Impact

| Scenario | Eager | Lazy | Improvement |
|----------|-------|------|-------------|
| 500 tasks, filter + select | 100% | 60-80% | 20-40% faster |
| 10,000 tasks, projection | High memory | Low memory | 40-60% memory reduction |

## Compliance

### Incremental Loading

1. **Code Review**:
   - Story fetching uses incremental loading by default
   - Cache metadata includes `last_story_at`
   - Atomic updates use Redis WATCH/MULTI

2. **Testing**:
   - Unit tests for merge algorithm
   - Unit tests for concurrent update handling
   - Integration tests with mock API returning `since` results

3. **Edge Cases**:
   - Empty story list (no stories)
   - First fetch (no cache)
   - Story deletion detection (full refresh trigger)
   - Pagination of incremental results

4. **Documentation**:
   - Explain incremental loading in API docs
   - Document `refresh_stories()` for forced full reload
   - Clarify story deletion handling behavior

### Lazy Evaluation

1. **Code Review**:
   - `to_dataframe()` accepts `lazy: bool | None` parameter
   - Threshold logic uses `_should_use_lazy()` helper
   - Both eager and lazy paths tested
   - Return type is always `pl.DataFrame`

2. **Unit Tests**:
   - Test auto-selects eager below threshold
   - Test auto-selects lazy above threshold
   - Test `lazy=True` forces lazy mode
   - Test `lazy=False` forces eager mode

3. **Logging**:
   ```python
   logger.debug(
       "dataframe_build_mode",
       task_count=len(tasks),
       lazy_override=lazy,
       selected_mode="lazy" if use_lazy else "eager",
       threshold=LAZY_THRESHOLD,
   )
   ```

4. **Documentation**:
   - API docs explain `lazy` parameter
   - Docstring mentions 100-task threshold
   - Example shows override usage

## Cross-References

- **ADR-0133**: Progressive TTL extension uses incremental loading principles
- **ADR-SUMMARY-CACHE**: Caching strategies that leverage incremental loading
- **ADR-SUMMARY-DATA-MODEL**: DataFrame layer uses lazy evaluation
