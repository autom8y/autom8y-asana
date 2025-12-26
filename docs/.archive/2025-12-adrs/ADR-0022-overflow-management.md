# ADR-0022: Overflow Management

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team, User
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md)

## Context

Some Asana tasks have extreme numbers of relationships:
- Tasks with 200+ subtasks (project breakdown tasks)
- Tasks with 500+ stories (highly-discussed issues)
- Tasks with 100+ attachments (documentation tasks)

Caching these outliers causes problems:
- **Memory bloat**: Single task can consume MB of cache
- **Slow operations**: Large payloads increase serialization time
- **Low reuse**: Outliers are rare; cache space wasted on rarely-accessed data
- **Redis pressure**: Large values impact cluster performance

**Legacy autom8 pattern**: Skip caching for relationships exceeding thresholds:
- Subtasks > 40: Don't cache subtask list
- Stories > 100: Don't cache story list
- Dependencies/dependents/attachments > 40: Don't cache

**User decision**: Per-relationship thresholds with skip-caching behavior. Defaults from legacy autom8.

**Requirements**:
- FR-CACHE-071: Define per-relationship overflow thresholds
- FR-CACHE-072: Default thresholds from legacy (subtasks=40, stories=100, etc.)
- FR-CACHE-073: Skip caching when count exceeds threshold
- FR-CACHE-074: Configurable thresholds via settings

## Decision

**Implement per-relationship overflow thresholds that skip caching when exceeded, with configurable limits and metrics tracking.**

### Configuration

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

### Implementation

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
        if self._is_overflow("subtasks", len(subtasks)):
            self._log.warning(
                "Overflow: task %s has %d subtasks (threshold: %d), skipping cache",
                task_gid,
                len(subtasks),
                self._settings.overflow.subtasks,
            )
            self._metrics.record_overflow_skip("subtasks")
            return subtasks

        # Cache the result
        await self._cache_subtasks(task_gid, subtasks)
        return subtasks

    def _is_overflow(self, entry_type: str, count: int) -> bool:
        """Check if count exceeds overflow threshold."""
        return self._settings.overflow.is_overflow(entry_type, count)


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
        self._warned_tasks: set[str] = set()

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

        # Overflow detected
        self._metrics.record_overflow_skip(entry_type)

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

    def get_overflow_stats(self) -> dict[str, int]:
        """Get count of overflow skips by entry type."""
        return self._metrics.get_overflow_stats()
```

### Threshold Defaults

| Entry Type | Default Threshold | Rationale |
|------------|-------------------|-----------|
| subtasks | 40 | >99% of tasks have <40 subtasks |
| dependencies | 40 | Most tasks have <10 dependencies |
| dependents | 40 | Most tasks have <10 dependents |
| stories | 100 | Covers typical comment threads |
| attachments | 40 | Most tasks have <10 attachments |

### Behavior Matrix

| Relationship | Count | Threshold | Action |
|--------------|-------|-----------|--------|
| subtasks | 25 | 40 | Cache normally |
| subtasks | 50 | 40 | Skip cache, log warning |
| subtasks | 100 | None | Cache normally (disabled) |
| stories | 150 | 100 | Skip cache, log warning |

## Rationale

**Why skip caching rather than partial caching?**

Partial caching creates complexity:
- How to handle pagination across cached/uncached portions?
- How to merge partial results?
- How to determine freshness of partial data?

Skipping entirely is simpler:
- Cache hit: return cached data
- Cache miss: fetch from API
- No mixed cached/uncached state

**Why per-relationship thresholds?**

Different relationships have different typical sizes:
- Stories accumulate over time (higher threshold)
- Subtasks are typically bounded by task breakdown (lower threshold)
- One threshold for all would be too restrictive or too permissive

**Why log warning only once per task?**

A task that exceeds thresholds will likely be accessed multiple times:
- First access: Log warning
- Subsequent accesses: Silent skip (already logged)
- Prevents log spam for known-overflow tasks

**Why configurable thresholds?**

Different organizations have different patterns:
- Some teams use deep subtask hierarchies
- Some projects have extensive documentation (many attachments)
- Allowing configuration lets consumers tune for their use cases

## Alternatives Considered

### Alternative 1: No Overflow Limits

- **Description**: Cache everything regardless of size.
- **Pros**:
  - Consistent caching behavior
  - No configuration complexity
  - Maximum cache coverage
- **Cons**:
  - Redis memory bloat for outliers
  - Single large task can consume disproportionate resources
  - Performance degradation with large payloads
- **Why not chosen**: Unbounded cache growth is operationally risky. Outliers waste shared resources.

### Alternative 2: LRU Eviction Instead

- **Description**: Rely on Redis LRU eviction to remove large entries.
- **Pros**:
  - Automatic memory management
  - No threshold configuration
  - Redis handles complexity
- **Cons**:
  - LRU may evict useful small entries before useless large ones
  - No control over what gets evicted
  - Large entries still stored initially
- **Why not chosen**: LRU doesn't distinguish entry size. Better to prevent storage than rely on eviction.

### Alternative 3: Compression for Large Entries

- **Description**: Compress large payloads before caching.
- **Pros**:
  - Reduces storage size
  - All entries cached
  - Consistent behavior
- **Cons**:
  - Adds CPU overhead for compression/decompression
  - Large entries still slow to serialize
  - JSON compression ratio varies
- **Why not chosen**: Addresses storage but not serialization performance. Skipping is simpler and more effective.

### Alternative 4: Partial Caching

- **Description**: Cache first N items, mark as partial.
- **Pros**:
  - Faster initial access
  - Some caching benefit
  - Could be useful for pagination
- **Cons**:
  - Complex merge with fresh data
  - Partial cache staleness detection
  - Unclear freshness semantics
  - User may get inconsistent data
- **Why not chosen**: Complexity doesn't justify benefit. Either cache fully or fetch fully.

### Alternative 5: Memory-Based Limits

- **Description**: Limit by estimated memory size (bytes) rather than count.
- **Pros**:
  - More accurate resource management
  - Accounts for varying item sizes
  - Direct relationship to Redis memory
- **Cons**:
  - Harder to estimate JSON size before serialization
  - Count is simpler and correlates with size
  - Legacy pattern uses count successfully
- **Why not chosen**: Count is sufficient approximation. Size estimation adds complexity.

## Consequences

### Positive

- **Bounded cache size**: Outliers don't bloat Redis
- **Predictable performance**: Large entries don't slow operations
- **Configurable limits**: Tune per organization/project
- **Observable**: Metrics track overflow occurrences
- **Proven pattern**: Matches legacy autom8 behavior

### Negative

- **Some data not cached**: Overflow tasks always fetch from API
- **Threshold tuning**: Defaults may not fit all use cases
- **Session-scoped warnings**: Log spam possible across process restarts
- **No partial benefit**: Overflow tasks get zero caching benefit

### Neutral

- **Defaults from legacy**: Well-tested thresholds
- **None disables threshold**: Full control per relationship
- **Metrics per entry type**: Track which types overflow most

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - All relationship caching checks overflow before storing
   - Overflow warnings logged only once per task per session
   - Metrics recorded for all skips

2. **Testing requirements**:
   - Unit tests for threshold checking
   - Unit tests for warning deduplication
   - Integration tests with overflow scenarios

3. **Monitoring**:
   - Dashboard for overflow skip rates by entry type
   - Alert if overflow rate exceeds expected percentage
   - Track which tasks are chronic overflows

4. **Documentation**:
   - Document default thresholds in README
   - Explain how to configure custom thresholds
   - Clarify behavior for overflow tasks
