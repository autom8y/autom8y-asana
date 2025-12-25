# REF: Cache Usage Patterns and Optimization

## Metadata

**Document ID**: REF-CACHE-PATTERNS
**Type**: Reference
**Status**: Active
**Created**: 2025-12-24
**Supersedes**: PRD-CACHE-OPTIMIZATION-P2, PRD-CACHE-OPTIMIZATION-P3, PRD-CACHE-PERF-DETECTION, PRD-CACHE-PERF-FETCH-PATH, PRD-CACHE-PERF-HYDRATION, PRD-CACHE-PERF-STORIES

---

## Overview

This document describes proven patterns for effective cache utilization in the autom8_asana SDK. Following these patterns achieves >90% cache hit rates and <1s warm operation latency for typical workloads.

---

## Pattern 1: DataFrame Cold Start Optimization

### Problem

First DataFrame extraction from a project takes 10-20 seconds due to serial API pagination.

### Solution: Parallel Section Fetch

Fetch tasks from all sections concurrently rather than sequentially:

```python
# Cold start with parallel fetch
df = await project.to_dataframe_parallel_async(client)
# ~10s (vs ~20s serial)

# Warm cache (second call)
df = await project.to_dataframe_parallel_async(client)
# <1s (>95% cache hit rate)
```

### Implementation Pattern

```python
async def build_with_parallel_fetch_async(
    project: Project,
    client: AsanaClient,
) -> pl.DataFrame:
    """Build DataFrame using parallel section fetch with automatic caching."""

    # 1. Enumerate sections (cached separately)
    sections = await client.sections.list_for_project_async(project.gid)

    # 2. Fetch tasks from all sections concurrently
    async with asyncio.Semaphore(8):  # Limit concurrent requests
        tasks_by_section = await asyncio.gather(*[
            fetch_section_tasks(client, section.gid)
            for section in sections
        ])

    # 3. Flatten and deduplicate (multi-homed tasks)
    all_tasks = deduplicate_by_gid(itertools.chain(*tasks_by_section))

    # 4. Auto-populate cache (happens transparently)
    # Each task is cached with key: {task_gid}:{project_gid}

    # 5. Build DataFrame from tasks
    return builder.build(all_tasks)
```

### Performance Profile

| Stage | Cold | Warm |
|-------|------|------|
| Section enumeration | ~500ms | <50ms (cached) |
| GID enumeration | ~2s | <50ms (cached) |
| Task fetch | ~7s | <100ms (cache hits) |
| DataFrame build | ~500ms | ~500ms |
| **Total** | **~10s** | **<1s** |

---

## Pattern 2: Incremental Story Loading

### Problem

Fetching all stories for a task repeatedly wastes bandwidth - most stories don't change.

### Solution: Since Parameter + Merge

Use Asana's `since` parameter to fetch only new stories, merge with cached:

```python
# First fetch: Full load
stories = await client.stories.list_for_task_cached_async(task_gid)
# Cache populated with all stories, last_fetched timestamp stored

# Second fetch: Incremental
stories = await client.stories.list_for_task_cached_async(task_gid)
# API call: GET /tasks/{gid}/stories?since={last_fetched}
# Returns only new stories (typically 0-5)
# Merged with cached stories, deduplicated by GID
```

### Implementation Pattern

```python
async def list_for_task_cached_async(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
) -> list[Story]:
    """Fetch stories with incremental caching."""

    # Check cache for existing stories
    entry = self._cache.get(task_gid, EntryType.STORIES)

    if entry:
        # Incremental fetch since last_fetched
        last_fetched = entry.metadata.get("last_fetched")
        new_stories = await self._fetch_stories_since(task_gid, last_fetched)

        # Merge: cached + new, deduplicate by GID
        all_stories = _merge_stories(entry.data, new_stories)

        # Update cache with merged result
        self._cache.set(task_gid, make_entry(all_stories, task_modified_at))

        return [Story.model_validate(s) for s in all_stories]
    else:
        # Cold fetch: All stories
        all_stories = await self._fetch_all_stories(task_gid)
        self._cache.set(task_gid, make_entry(all_stories, task_modified_at))
        return [Story.model_validate(s) for s in all_stories]
```

### Bandwidth Savings

| Scenario | Full Payload | Incremental | Savings |
|----------|--------------|-------------|---------|
| 100 stories, 2 new | ~50KB | ~1KB | 98% |
| 100 stories, 0 new | ~50KB | ~200 bytes | 99.6% |

---

## Pattern 3: Detection Result Caching

### Problem

Entity type detection with `allow_structure_inspection=True` fetches subtasks (~200ms) every time for the same task.

### Solution: Cache Detection Results

Cache the `DetectionResult` after Tier 4 execution:

```python
# First detection: Tier 4 execution
result = await detect_entity_type_async(
    task,
    client,
    allow_structure_inspection=True,
)
# ~200ms (subtask fetch + detection logic)
# Result cached with key: {task_gid}, entry_type: DETECTION

# Second detection: Cache hit
result = await detect_entity_type_async(task, client, allow_structure_inspection=True)
# <5ms (cache hit)
```

### Implementation Pattern

```python
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Detect entity type with caching for Tier 4."""

    # Tiers 1-3: Fast, no cache needed
    result = _try_tiers_1_through_3(task)
    if result:
        return result

    # Tier 4: Structure inspection (expensive)
    if allow_structure_inspection:
        # Check cache before fetching subtasks
        cached = client._cache.get(task.gid, EntryType.DETECTION)
        if cached and not cached.is_expired():
            return DetectionResult(**cached.data)

        # Cache miss: Execute Tier 4
        subtasks = await client.tasks.subtasks_async(task.gid).collect()
        result = _detect_from_subtask_structure(subtasks)

        # Cache the result
        client._cache.set(
            task.gid,
            make_entry(dataclasses.asdict(result), task.modified_at),
            EntryType.DETECTION,
        )

        return result

    # Tier 5: Unknown (do not cache)
    return DetectionResult(entity_type="unknown", ...)
```

### Performance Impact on Hydration

Hydration traverses multiple levels - each requires detection:

| Level | First Hydration | Cached Hydration |
|-------|----------------|------------------|
| Offer (start) | ~200ms (Tier 4) | <5ms (cache) |
| Unit (parent) | ~200ms (Tier 4) | <5ms (cache) |
| Contact (parent) | ~200ms (Tier 4) | <5ms (cache) |
| Business (parent) | ~200ms (Tier 4) | <5ms (cache) |
| **Total** | **~800ms** | **<20ms** |

---

## Pattern 4: Hydration Field Normalization

### Problem

Tasks fetched via different paths (get_async, subtasks_async, list_async) may have different opt_fields. Cached entries missing `parent.gid` break upward traversal.

### Solution: Standard Field Set

Define a unified field set used across all fetch paths:

```python
STANDARD_TASK_OPT_FIELDS = (
    # Core identification
    "name",
    "parent.gid",  # Required for traversal
    # Detection (Tier 1)
    "memberships.project.gid",
    "memberships.project.name",
    # Custom fields (cascading)
    "custom_fields",
    "custom_fields.name",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.display_value",
    "custom_fields.number_value",
    "custom_fields.text_value",
    "custom_fields.resource_subtype",
    "custom_fields.people_value",  # Required for Owner cascading
)
```

### Usage

```python
# All fetch paths use standard fields
task = await client.tasks.get_async(gid, opt_fields=STANDARD_TASK_OPT_FIELDS)
subtasks = await client.tasks.subtasks_async(parent_gid, include_detection_fields=True)
# include_detection_fields=True applies STANDARD_TASK_OPT_FIELDS

# Cached tasks always have parent.gid and people_value
# Traversal succeeds regardless of how task was first fetched
```

---

## Pattern 5: Batch Cache Operations

### Problem

Individual cache get/set for 3,500 tasks takes >5 seconds. Serial loops don't scale.

### Solution: Batch Operations

Use `get_batch()` and `set_batch()` for bulk operations:

```python
# Bad: Serial gets (3,500 calls)
tasks = []
for gid in task_gids:
    entry = cache.get(gid, EntryType.TASK)
    if entry:
        tasks.append(Task.model_validate(entry.data))
# ~5 seconds

# Good: Batch get (1 call)
entries = cache.get_batch(task_gids, EntryType.TASK)
tasks = [
    Task.model_validate(entry.data)
    for gid, entry in entries.items()
    if entry is not None
]
# ~100ms
```

### Batch Population

```python
# After parallel fetch, populate cache in single batch
await parallel_fetch_all_sections()  # Returns 3,500 tasks

# Batch write
cache.set_batch({
    task.gid: make_entry(task.to_dict(), task.modified_at)
    for task in all_tasks
})
# ~100ms vs ~5s serial
```

---

## Pattern 6: GID Enumeration Caching

### Problem

Enumerating section-to-task-GID mappings takes 35+ API calls per project on every DataFrame build.

### Solution: Cache Enumeration Results

Cache the complete GID enumeration separately from task objects:

```python
# First build: Enumerate sections and GIDs
gid_map = await enumerate_section_task_gids(project_gid)
# {
#   "section_a": ["task1", "task2", ...],
#   "section_b": ["task5", "task6", ...],
# }
# Cached with key: project:{project_gid}:gid_enumeration
# 35+ API calls

# Second build: Cache hit
gid_map = cache.get(f"project:{project_gid}:gid_enumeration", EntryType.GID_ENUMERATION)
# 0 API calls, <50ms
```

### TTL Rationale

- **Section list**: 1800s (30 min) - Section structure rarely changes
- **GID enumeration**: 300s (5 min) - Task-section membership more dynamic

---

## Pattern 7: Partial Cache Handling

### Problem

If only 90% of tasks are cached, re-fetching all 100% wastes API bandwidth.

### Solution: Fetch Only Missing

Identify missing GIDs, fetch only those:

```python
async def build_with_partial_cache(
    task_gids: list[str],
    client: AsanaClient,
) -> list[Task]:
    """Handle partial cache scenario efficiently."""

    # Batch cache lookup
    entries = cache.get_batch(task_gids, EntryType.TASK)

    # Identify hits and misses
    cached_tasks = [
        Task.model_validate(entry.data)
        for gid, entry in entries.items()
        if entry is not None
    ]
    missing_gids = [gid for gid in task_gids if entries.get(gid) is None]

    if not missing_gids:
        # 100% cache hit
        return cached_tasks

    # Fetch only missing tasks
    fresh_tasks = await fetch_by_gids(client, missing_gids)

    # Populate cache with fresh tasks
    cache.set_batch({
        task.gid: make_entry(task.to_dict(), task.modified_at)
        for task in fresh_tasks
    })

    # Merge cached + fresh, preserve order
    return merge_preserving_order(cached_tasks, fresh_tasks, task_gids)
```

### Performance: 90% Cache Hit

| Stage | API Calls | Latency |
|-------|-----------|---------|
| Batch cache lookup (3,500 GIDs) | 0 | ~100ms |
| Fetch missing (350 GIDs) | ~12 | ~2s |
| **Total** | **12** | **~2s** |

vs 100% miss: 35+ API calls, ~10s

---

## Pattern 8: SaveSession Invalidation

### Problem

After updating tasks via SaveSession, cached entries are stale until TTL expires.

### Solution: Post-Commit Invalidation Hook

SaveSession automatically invalidates affected cache entries:

```python
session = SaveSession(client)

# Track mutations
session.track(task1)
task1.name = "Updated"

session.track(task2)
session.delete(task2)

# Commit triggers invalidation
result = await session.commit_async()

# Automatic invalidation:
# - task1: TASK, DATAFRAME (all projects), DETECTION
# - task2: TASK, DATAFRAME (all projects), DETECTION

# Next fetch gets fresh data immediately
fresh_task1 = await client.tasks.get_async(task1.gid)
# Cache miss, fetches from API, reflects "Updated" name
```

### Multi-Project Tasks

```python
# Task is member of 3 projects
task.memberships = [
    {"project": {"gid": "proj_a"}},
    {"project": {"gid": "proj_b"}},
    {"project": {"gid": "proj_c"}},
]

session.track(task)
task.custom_fields = [...]

await session.commit_async()

# Invalidates DataFrame cache for all 3 projects:
# - {task_gid}:proj_a
# - {task_gid}:proj_b
# - {task_gid}:proj_c
```

---

## Pattern 9: Graceful Degradation

### Problem

Cache failures (Redis down, disk full, network timeout) should not break application functionality.

### Solution: Try-Except with Logging

All cache operations are wrapped in defensive exception handling:

```python
async def get_async(self, task_gid: str) -> Task:
    """Get task with cache, gracefully degrade on failure."""

    # Attempt cache lookup
    try:
        entry = self._cache.get(task_gid, EntryType.TASK)
        if entry and not entry.is_expired():
            return Task.model_validate(entry.data)
    except Exception as e:
        logger.warning(f"Cache read failed for {task_gid}: {e}")
        # Continue to API fetch

    # Fetch from API
    try:
        response = await self._http_client.get(f"/tasks/{task_gid}")
        task_data = response["data"]
    except Exception as e:
        # API failure is fatal (cannot proceed)
        raise

    # Attempt cache write
    try:
        self._cache.set(
            task_gid,
            make_entry(task_data, task_data.get("modified_at")),
            EntryType.TASK,
        )
    except Exception as e:
        logger.warning(f"Cache write failed for {task_gid}: {e}")
        # Proceed without caching

    return Task.model_validate(task_data)
```

### Degradation Scenarios

| Failure Point | Behavior |
|---------------|----------|
| Cache read exception | Log warning, fetch from API |
| Cache write exception | Log warning, return data without caching |
| Cache provider None | Skip cache operations entirely |
| Redis connection lost | Fall back to NullCacheProvider |

---

## Pattern 10: Opt-Out Mechanisms

### Problem

Some operations need to bypass cache (testing, debugging, force refresh).

### Solution: Explicit Disable Parameters

Provide opt-out at operation and configuration levels:

```python
# Per-operation opt-out
df = await project.to_dataframe_parallel_async(client, use_cache=False)
# Skips cache lookup and population, always fetches fresh

# Client-level opt-out
client = AsanaClient(cache_provider=NullCacheProvider())
# All operations proceed without cache

# Environment variable opt-out
# ASANA_CACHE_ENABLED=false
# Forces NullCacheProvider regardless of configuration
```

---

## Performance Benchmarks

### DataFrame Extraction (3,500 tasks)

| Scenario | API Calls | Latency | Cache Hit Rate |
|----------|-----------|---------|----------------|
| Cold start (no cache) | 35+ | ~10s | 0% |
| Warm cache (all cached) | 0 | <1s | 100% |
| Partial (90% cached) | ~12 | ~2s | 90% |
| After SaveSession (10 tasks updated) | ~10 | ~1.5s | ~99.7% |

### Individual Operations

| Operation | Cold | Warm | Speedup |
|-----------|------|------|---------|
| Task get | ~200ms | <5ms | 40x |
| Stories fetch (100 stories) | ~500ms | ~100ms (incremental) | 5x |
| Detection (Tier 4) | ~200ms | <5ms | 40x |
| Hydration (5 levels) | ~1000ms | <50ms | 20x |

---

## Anti-Patterns (Avoid These)

### Anti-Pattern 1: Excessive TTL

```python
# Bad: TTL too long, risk of stale data
cache.set(key, entry, ttl=86400)  # 24 hours

# Good: Use progressive TTL for stable entities
# Starts at 300s, extends to 24h only after repeated unchanged checks
```

### Anti-Pattern 2: Ignoring `modified_at`

```python
# Bad: Cache without version tracking
entry = CacheEntry(data=task_data, version=None, ...)

# Good: Always use modified_at for versioning
entry = CacheEntry(data=task_data, version=task.modified_at, ...)
```

### Anti-Pattern 3: Serial Operations

```python
# Bad: Serial gets
for gid in task_gids:
    entry = cache.get(gid, EntryType.TASK)

# Good: Batch operation
entries = cache.get_batch(task_gids, EntryType.TASK)
```

### Anti-Pattern 4: Forgetting Invalidation

```python
# Bad: Manual mutation without invalidation
await http_client.put(f"/tasks/{gid}", json={"name": "New"})
# Cache still has old name

# Good: Use SaveSession for automatic invalidation
session.track(task)
task.name = "New"
await session.commit_async()  # Auto-invalidates
```

---

## Related Documents

- [REF-cache-architecture.md](REF-cache-architecture.md) - Overall cache architecture
- [REF-cache-invalidation.md](REF-cache-invalidation.md) - Staleness detection and TTL patterns
- [ADR-0115](../decisions/ADR-0115-parallel-section-fetch-strategy.md) - Parallel fetch design
- [ADR-0120](../decisions/ADR-0120-batch-cache-population-on-bulk-fetch.md) - Batch population pattern
- [ADR-0129](../decisions/ADR-0129-stories-client-cache-wiring.md) - Stories incremental caching

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | Tech Writer | Initial consolidation from P2/P3 optimization PRDs and performance PRDs |
