# ADR-0005: Overflow Detection and Metrics

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0022 (Overflow Management)
- **Related**: reference/OBSERVABILITY.md, reference/CACHE.md, ADR-0004 (Cache Events)

## Context

Some Asana tasks have extreme numbers of relationships that create operational challenges when cached:
- Tasks with 200+ subtasks (project breakdown tasks)
- Tasks with 500+ stories (highly-discussed issues)
- Tasks with 100+ attachments (documentation tasks)

Caching these outliers causes problems:
- **Memory bloat**: Single task can consume MB of cache space
- **Slow operations**: Large payloads increase serialization/deserialization time
- **Low reuse**: Outliers are rare; cache space wasted on infrequently-accessed data
- **Redis pressure**: Large values impact cluster performance and eviction rates

Legacy autom8 implementation established a pattern: skip caching for relationships exceeding configured thresholds. This prevents outliers from dominating cache resources while allowing normal-sized relationships to benefit from caching.

**Key requirement**: Need visibility into overflow occurrences to tune thresholds for specific workloads and identify chronic overflow tasks.

## Decision

**Implement per-relationship overflow thresholds that skip caching when exceeded. Emit `overflow_skip` events through the observability system for metrics tracking. Log warnings once per task per session to prevent spam.**

### Overflow Configuration

```python
from dataclasses import dataclass

@dataclass
class OverflowSettings:
    """Per-relationship overflow thresholds.

    When a relationship count exceeds its threshold, caching is skipped.
    Set to None to disable threshold for a relationship type.
    """
    subtasks: int | None = 40
    dependencies: int | None = 40
    dependents: int | None = 40
    stories: int | None = 100
    attachments: int | None = 40

    def is_overflow(self, entry_type: str, count: int) -> bool:
        """Check if count exceeds threshold for entry type."""
        threshold = getattr(self, entry_type, None)
        if threshold is None:
            return False
        return count > threshold
```

### Overflow Manager

```python
class OverflowManager:
    """Centralized overflow threshold management."""

    def __init__(
        self,
        settings: OverflowSettings,
        metrics: CacheMetrics,
        log: LogProvider,
    ) -> None:
        self._settings = settings
        self._metrics = metrics
        self._log = log
        self._warned_tasks: set[str] = set()  # Session-scoped deduplication

    def should_cache(
        self,
        task_gid: str,
        entry_type: str,
        count: int,
    ) -> bool:
        """Determine if entry should be cached based on overflow.

        Returns:
            True if should cache, False if overflow detected
        """
        if not self._settings.is_overflow(entry_type, count):
            return True

        # Overflow detected - emit event
        self._metrics.record_event(
            CacheEvent(
                event_type="overflow_skip",
                key=task_gid,
                entry_type=entry_type,
                latency_ms=0.0,
                metadata={"count": count, "threshold": getattr(self._settings, entry_type)},
            )
        )

        # Log warning once per task per session
        warn_key = f"{task_gid}:{entry_type}"
        if warn_key not in self._warned_tasks:
            self._warned_tasks.add(warn_key)
            self._log.warning(
                "Overflow: task %s has %d %s (threshold: %d), skipping cache",
                task_gid,
                count,
                entry_type,
                getattr(self._settings, entry_type),
            )

        return False
```

### Client Integration

```python
class TasksClient:
    """Tasks client with overflow management."""

    async def get_subtasks(
        self,
        task_gid: str,
        use_cache: bool = True,
    ) -> list[Task]:
        """Get subtasks with overflow handling."""
        if use_cache:
            cached = await self._cache.get_versioned(
                task_gid,
                EntryType.SUBTASKS,
            )
            if cached is not None:
                return [Task.model_validate(t) for t in cached.data["subtasks"]]

        # Fetch from API
        subtasks = await self._fetch_subtasks(task_gid)

        # Check overflow before caching
        if not self._overflow_mgr.should_cache(task_gid, "subtasks", len(subtasks)):
            return subtasks  # Skip cache, return fresh data

        # Cache the result
        await self._cache_subtasks(task_gid, subtasks)
        return subtasks
```

### Threshold Defaults

Based on legacy autom8 analysis and workload profiling:

| Entry Type | Default Threshold | Rationale |
|------------|-------------------|-----------|
| subtasks | 40 | >99% of tasks have <40 subtasks based on usage data |
| dependencies | 40 | Most tasks have <10 dependencies; 40 covers edge cases |
| dependents | 40 | Most tasks have <10 dependents; 40 covers edge cases |
| stories | 100 | Covers typical comment threads; active discussions can exceed |
| attachments | 40 | Most tasks have <10 attachments; docs tasks may exceed |

### Behavior Matrix

| Relationship | Count | Threshold | Action |
|--------------|-------|-----------|--------|
| subtasks | 25 | 40 | Cache normally |
| subtasks | 50 | 40 | Skip cache, log warning, emit overflow_skip event |
| subtasks | 100 | None (disabled) | Cache normally (threshold disabled) |
| stories | 150 | 100 | Skip cache, log warning, emit overflow_skip event |

## Rationale

### Why Skip Caching Rather Than Partial Caching?

Partial caching introduces complexity:
- How to handle pagination across cached/uncached portions?
- How to merge partial results with fresh API data?
- How to determine freshness of partial data?
- Inconsistent user experience (sometimes paginated, sometimes not)

Skipping entirely is simpler and clearer:
- Cache hit: Return cached data (under threshold)
- Cache miss or overflow: Fetch fresh from API
- No mixed cached/uncached state to manage
- Consistent behavior: either cached or not

### Why Per-Relationship Thresholds?

Different relationships have different typical sizes and growth patterns:
- **Stories** accumulate over time (higher threshold appropriate)
- **Subtasks** typically bounded by initial task breakdown (lower threshold)
- **Dependencies** usually small, rarely change (lower threshold)

Single global threshold would be either:
- Too restrictive (blocks caching for normal stories)
- Too permissive (allows memory bloat from excessive subtasks)

### Why Log Warning Only Once Per Task?

Tasks that exceed thresholds are likely accessed multiple times in a session:
- First access: Log warning (alerts operator to outlier)
- Subsequent accesses: Silent skip (already logged, no need to spam)

This prevents log spam for known-overflow tasks while still providing visibility on first occurrence.

### Why Configurable Thresholds?

Different organizations have different patterns:
- Some teams use deep subtask hierarchies (need higher subtask threshold)
- Some projects have extensive documentation (many attachments)
- Development vs. production workloads may differ

Configuration allows consumers to tune for their specific use cases without SDK changes.

### Why Emit Metrics Events?

Metrics tracking enables:
- **Threshold tuning**: Analyze which relationship types frequently overflow
- **Capacity planning**: Identify which tasks are chronic overflows
- **Alerting**: Notify if overflow rate exceeds expected percentage
- **Dashboard visibility**: Track overflow trends over time

## Alternatives Considered

### Alternative 1: No Overflow Limits
- **Description**: Cache everything regardless of size
- **Pros**: Consistent caching behavior, no configuration complexity, maximum cache coverage
- **Cons**: Redis memory bloat for outliers, single large task can consume disproportionate resources, performance degradation with large payloads
- **Why not chosen**: Unbounded cache growth is operationally risky. Outliers waste shared resources and can degrade Redis performance for all users.

### Alternative 2: LRU Eviction Instead
- **Description**: Rely on Redis LRU eviction to remove large entries automatically
- **Pros**: Automatic memory management, no threshold configuration, Redis handles complexity
- **Cons**: LRU may evict useful small entries before useless large ones (no size awareness), large entries still stored initially (wastes bandwidth), no control over what gets evicted
- **Why not chosen**: LRU doesn't distinguish entry size. Better to prevent storage of outliers than rely on eviction.

### Alternative 3: Compression for Large Entries
- **Description**: Compress large payloads (gzip, zstd) before caching
- **Pros**: Reduces storage size, all entries cached, consistent behavior
- **Cons**: Adds CPU overhead for compression/decompression, large entries still slow to serialize, JSON compression ratio varies (not predictable), doesn't solve serialization performance
- **Why not chosen**: Addresses storage but not serialization performance or API response parsing time. Skipping is simpler and more effective.

### Alternative 4: Partial Caching
- **Description**: Cache first N items, mark entry as partial, fetch remainder on access
- **Pros**: Faster initial access, some caching benefit, could be useful for pagination
- **Cons**: Complex merge logic with fresh data, partial cache staleness detection, unclear freshness semantics, user may get inconsistent data, pagination state management
- **Why not chosen**: Complexity doesn't justify benefit. Either cache fully or fetch fully provides clearer semantics.

### Alternative 5: Memory-Based Limits
- **Description**: Limit by estimated memory size (bytes) rather than item count
- **Pros**: More accurate resource management, accounts for varying item sizes, direct relationship to Redis memory
- **Cons**: Harder to estimate JSON size before serialization, count is simpler and correlates well with size, legacy pattern uses count successfully
- **Why not chosen**: Count is sufficient approximation. Size estimation adds complexity without proportional benefit.

## Consequences

### Positive
- **Bounded cache size**: Outliers don't bloat Redis memory
- **Predictable performance**: Large entries don't slow serialization/deserialization
- **Configurable limits**: Tune thresholds per organization/project workload
- **Observable**: Metrics track overflow occurrences for analysis
- **Proven pattern**: Matches legacy autom8 behavior (well-tested)
- **Prevents cascading failures**: Outliers can't trigger Redis OOM or cluster degradation
- **Dashboard visibility**: Track which tasks and relationship types cause overflows

### Negative
- **Some data not cached**: Overflow tasks always fetch from API (higher latency)
- **Threshold tuning**: Defaults may not fit all use cases (requires monitoring and adjustment)
- **Session-scoped warnings**: Log spam possible across process restarts (not persistent)
- **No partial benefit**: Overflow tasks get zero caching benefit (all-or-nothing)
- **Configuration burden**: Users must understand threshold implications

### Neutral
- **Defaults from legacy**: Well-tested thresholds based on real workload analysis
- **None disables threshold**: Setting threshold to None provides full control per relationship
- **Metrics per entry type**: Track which types overflow most to guide threshold tuning
- **Per-session deduplication**: Warning state not shared across processes

## Compliance

How we ensure this decision is followed:

**Code Review Checklist**:
- All relationship caching calls `should_cache()` before storing
- Overflow warnings logged only once per task per session
- Metrics recorded for all overflow skips via `overflow_skip` event
- Thresholds configurable via `OverflowSettings` dataclass
- Default thresholds match documented values

**Testing Requirements**:
- Unit tests for threshold checking logic (`is_overflow()` method)
- Unit tests for warning deduplication (verify `_warned_tasks` set)
- Unit tests verify metrics emission on overflow
- Integration tests with overflow scenarios (count > threshold)
- Integration tests verify cache skip behavior (data fetched fresh, not cached)

**Monitoring Setup**:
- Dashboard for overflow skip rates by entry type
- Alert if overflow rate exceeds expected percentage (e.g., >5% of requests)
- Track which specific task GIDs are chronic overflows
- Graph overflow trends over time to identify workload changes

**Configuration Example**:

```python
# Custom threshold configuration
overflow_settings = OverflowSettings(
    subtasks=60,      # Raise threshold for teams with deep hierarchies
    stories=200,      # Higher for very active discussions
    dependencies=40,  # Keep default
    dependents=40,    # Keep default
    attachments=None, # Disable threshold (cache all attachments)
)

client = AsanaClient(
    auth=BearerAuth(token),
    cache_provider=RedisCacheProvider(...),
    overflow_settings=overflow_settings,
)
```

**Metrics Query Examples**:

```python
# Get overflow statistics
stats = metrics.get_stats()
overflow_by_type = stats["overflow_skips"]
# {"subtasks": 12, "stories": 45, "attachments": 3}

# Check if overflow rate is too high
total_operations = stats["hits"] + stats["misses"]
overflow_total = sum(overflow_by_type.values())
overflow_rate = (overflow_total / total_operations * 100) if total_operations > 0 else 0
if overflow_rate > 5.0:
    logger.warning("High overflow rate: %.1f%% (threshold: 5%%)", overflow_rate)
```
