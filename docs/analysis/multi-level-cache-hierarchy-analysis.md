# Multi-Level Cache Hierarchy Analysis

**Date**: 2025-12-22
**Author**: Architect
**Status**: Analysis Document
**Related ADRs**: ADR-0021, ADR-0026, ADR-0032

---

## Executive Summary

This document analyzes the multi-level cache hierarchy design pattern for the autom8_asana SDK, evaluating the trade-offs between task-level, section-level, and project-level caching. The analysis concludes that the **current per-task granularity with project context** (as documented in ADR-0032) is optimal, and that adding section-level or project-level aggregate caches would constitute **over-caching** given the SDK's access patterns and invalidation requirements.

---

## 1. Cache Level Trade-offs Matrix

| Level | Read Pattern | Write Pattern | Memory Overhead | Invalidation Cost | Hit Rate | Complexity |
|-------|--------------|---------------|-----------------|-------------------|----------|------------|
| **Task** | O(1) lookup per task | O(1) write per task | 1x (baseline) | O(1) surgical | Highest (99%+ unmodified) | Low |
| **Section** | O(1) lookup, returns N tasks | O(N) aggregate on write | 2x (task + section copies) | O(N) per section on any task change | Medium (any task change = miss) | Medium |
| **Project** | O(1) lookup, returns all tasks | O(N) aggregate on write | 3x (task + section + project copies) | O(N) cascade invalidation | Low (frequent invalidation) | High |
| **Hybrid (Current)** | O(1) task + O(N) batch | O(1) task-level writes | ~1x (deduped via task-level) | O(1) per modified task | Highest | Medium-Low |

### Analysis by Level

#### Task-Level (Current Implementation)

**Characteristics**:
- Key: `{task_gid}:{project_gid}`
- Stores: Single extracted row per task-project combination
- Versioned by: Task's `modified_at` timestamp

**Strengths**:
- Surgical invalidation: Only modified task is invalidated
- Maximum cache reuse: Unchanged tasks remain cached across requests
- Memory efficient: Only stores what's needed
- Natural batch aggregation: `get_batch()` retrieves multiple tasks in single operation

**Weaknesses**:
- Requires batch retrieval for project-level operations
- Key construction requires both task and project GID

#### Section-Level (Hypothetical)

**Characteristics**:
- Key: `section:{section_gid}:{project_gid}`
- Stores: List of all task rows in section
- Versioned by: Maximum `modified_at` of contained tasks

**Strengths**:
- Single read retrieves all tasks in section
- Natural grouping for section-based workflows

**Weaknesses**:
- **Cache thrashing**: Any task change invalidates entire section
- **Data duplication**: Same task data stored in task cache AND section cache
- **Multi-homed task complexity**: Task in multiple sections = multiple copies
- **Staleness amplification**: Version must track all contained tasks

**Invalidation analysis** for a section with 50 tasks:
```
Task T1 modified
  -> Invalidate task:T1:P1 (O(1))
  -> Invalidate section:S1:P1 (contains 50 tasks) (O(1) delete, but...)
  -> Next request rebuilds entire section (O(50) extractions)
```

#### Project-Level (Hypothetical)

**Characteristics**:
- Key: `project:{project_gid}`
- Stores: Full DataFrame for project (all tasks, all sections)
- Versioned by: Maximum `modified_at` across all project tasks

**Strengths**:
- Single read retrieves entire project DataFrame
- Optimal for batch reporting operations

**Weaknesses**:
- **Catastrophic invalidation**: Any task change invalidates ALL cached data
- **Memory explosion**: Full DataFrame duplicates all task data
- **Version tracking nightmare**: Must track all tasks' versions
- **Cold start penalty**: Full project rebuild on any cache miss

**Invalidation analysis** for a project with 1000 tasks:
```
Task T1 modified
  -> Invalidate task:T1:P1 (O(1))
  -> Invalidate section:S1:P1 (O(1) but loses 50 tasks)
  -> Invalidate project:P1 (O(1) but loses 1000 tasks)
  -> Next project request: O(1000) extractions = cold start
```

---

## 2. Waterfall Invalidation Design

### Current Flow (Task-Level Only)

When `SaveSession.commit()` updates task X in section S in project P:

```
commit() executes
    |
    v
Task X updated via API
    |
    v
_invalidate_cache_for_results() called
    |
    v
cache.invalidate(X, [EntryType.TASK, EntryType.SUBTASKS])
    |
    v
Redis DEL asana:task:X
Redis DEL asana:subtasks:X
    |
    v
S3 DELETE (async, if enabled)
    |
    v
DONE - Other tasks unaffected
```

**Invalidation cost**: O(1) per modified entity

### Hypothetical Multi-Level Waterfall

If section-level and project-level caches existed:

```
Task X updated
    |
    v
Task cache invalidation
    cache.invalidate(task:X:P)                    [O(1)]
    |
    v
Section cache invalidation (cascade)
    section_gid = lookup_section(X, P)           [O(1) lookup]
    cache.invalidate(section:S:P)                [O(1) delete]
    |
    v
Project cache invalidation (cascade)
    cache.invalidate(project:P)                  [O(1) delete]
    |
    v
DONE - But next reads trigger:
    - Section S rebuild: O(50) tasks
    - Project P rebuild: O(1000) tasks
```

**Total invalidation cost**: O(1) delete, but O(N) rebuild on next access

### Incremental Update Alternative

Instead of full invalidation, could we do incremental updates?

```
Task X updated (new data: X')
    |
    v
Task cache: SET task:X:P = X'                    [O(1)]
    |
    v
Section cache:
    section_data = GET section:S:P               [O(1)]
    section_data[X] = X'                         [O(1) in-memory]
    SET section:S:P = section_data               [O(N) serialize]
    |
    v
Project cache:
    project_data = GET project:P                 [O(1)]
    project_data[X] = X'                         [O(1) in-memory]
    SET project:P = project_data                 [O(N) serialize]
```

**Problems with incremental updates**:
1. **Race conditions**: Concurrent updates to same section/project
2. **Atomic operation complexity**: Read-modify-write is not atomic
3. **Serialization cost**: Large aggregate structures expensive to serialize
4. **Partial update failures**: What if section update succeeds but project fails?
5. **Cache coherence**: Aggregate may drift from task-level truth

**Verdict**: Incremental updates add complexity without proportional benefit.

---

## 3. Over-Caching Analysis

### When Does Multi-Level Caching Become Counterproductive?

#### 3.1 Cache Coherence Complexity

**Definition**: Ensuring all cache levels agree on the same data.

With multi-level caching:
```
task:T1:P1     = {"name": "Task A", "status": "done"}
section:S1:P1  = {"T1": {"name": "Task A", "status": "done"}, ...}
project:P1     = {"T1": {"name": "Task A", "status": "done"}, ...}
```

**Coherence failure scenario**:
1. Task T1 updated to `status: "in_progress"`
2. Task cache invalidated successfully
3. Section cache invalidation fails (network blip)
4. Project cache invalidated successfully
5. **Result**: Task cache and project cache show "in_progress", section cache shows "done"

**Coherence complexity**: O(L) where L = number of cache levels
- 1 level (task only): No coherence issues
- 2 levels (task + section): 2 sources of truth to synchronize
- 3 levels (task + section + project): 3 sources of truth, exponential failure modes

#### 3.2 Memory Overhead Analysis

**Scenario**: Project with 1000 tasks, 20 sections (50 tasks each)

| Caching Strategy | Task Entries | Section Entries | Project Entries | Total Memory |
|------------------|--------------|-----------------|-----------------|--------------|
| Task-only | 1000 | 0 | 0 | 1x |
| Task + Section | 1000 | 20 (duplicated data) | 0 | ~1.5x |
| Task + Section + Project | 1000 | 20 | 1 (all data duplicated) | ~2.5x |
| **Current (Task with project context)** | 1000 | 0 | 0 | **1x** |

**Memory duplication problem**:
```
# Task-level (1KB per task)
task:T1:P1 = {"gid": "T1", "name": "Task", "custom_fields": {...}}  # 1KB

# Section-level (duplicates task data)
section:S1:P1 = {
    "T1": {"gid": "T1", "name": "Task", "custom_fields": {...}},  # +1KB
    "T2": {...},
    ...50 tasks total  # +50KB
}

# Project-level (duplicates again)
project:P1 = {
    "T1": {...}, "T2": {...}, ... "T1000": {...}  # +1000KB
}

# Total for T1: 3KB instead of 1KB
# Total for project: 2.5MB instead of 1MB
```

#### 3.3 Invalidation Storms

**Definition**: Rapid cascade invalidation triggered by normal operations.

**High-churn project scenario**:
- Project P1 has 1000 tasks
- 10 tasks modified per hour (normal workflow)
- Multi-level cache with section + project aggregates

**Without multi-level caching**:
```
Hour 1: 10 tasks modified -> 10 cache invalidations
Hour 2: 10 tasks modified -> 10 cache invalidations
...
```

**With multi-level caching**:
```
Hour 1:
  Task T1 modified -> invalidate T1, S1, P1 (3 invalidations)
  Task T2 modified -> invalidate T2, S2, P1 (already invalidated, but still processed)
  ...10 tasks across 5 sections...
  Total: 10 task + 5 section + 1 project = 16 invalidations
  Plus: 5 section rebuilds (250 extractions) + 1 project rebuild (1000 extractions)

Hour 2: Same pattern repeats because P1 was rebuilt with Task T11, then T11 changes
  -> Another cascade
```

**Cache thrashing**: Cache entries are invalidated faster than they can provide value.

**Diminishing returns threshold**: When invalidation frequency exceeds useful cache lifetime, caching provides negative value (CPU for serialization/deserialization without read benefit).

#### 3.4 Diminishing Returns Calculation

**Cache utility formula**:
```
Utility = (Reads_served_from_cache * Read_cost_saved) - (Cache_maintenance_cost)

Where:
  Cache_maintenance_cost = Writes * Write_overhead + Invalidations * Rebuild_cost
```

**For task-level caching**:
```
Read_cost_saved = API_call_time - Cache_read_time = 50ms - 1ms = 49ms
Write_overhead = Cache_write_time = 1ms
Rebuild_cost = 0 (no aggregate to rebuild)

1000 tasks, 100 reads/hour, 10 writes/hour:
Utility = (100 * 49ms) - (10 * 1ms) = 4890ms saved per hour
```

**For project-level aggregate caching**:
```
Read_cost_saved = Build_dataframe_time - Cache_read_time = 500ms - 5ms = 495ms
Write_overhead = Cache_write_time + Aggregate_serialization = 1ms + 50ms = 51ms
Rebuild_cost = Full_extraction_time = 1000 * 50ms = 50,000ms

1000 tasks, 10 project reads/hour, 10 writes/hour:
Utility = (10 * 495ms) - (10 * 51ms) - (10 * 50,000ms rebuild amortized to fraction)
```

If each write invalidates the project cache:
```
Utility = 4950ms - 510ms - (probability_of_read_before_next_write * 0 + (1-p) * 50000ms)
```

With 10 writes/hour and 10 reads/hour, ~50% of reads hit a fresh cache:
```
Utility = 4950ms - 510ms - (0.5 * 50000ms) = 4440ms - 25000ms = -20,560ms
```

**The project-level cache has negative utility under typical write patterns.**

---

## 4. Optimal Strategy Recommendation

### Given Requirements

| Use Case | Frequency | Current Solution | Optimal Solution |
|----------|-----------|------------------|------------------|
| Project-level DataFrames | Frequent reads | `get_batch()` + aggregation | Per-task cache + batch retrieval |
| Section-level operations | Moderate | Section-filtered batch | Per-task cache + section filter |
| Individual task access | Moderate | Direct task cache | Per-task cache |
| SaveSession batch commits | Primary write | Task-level invalidation | Task-level invalidation |

### Recommendation: Maintain Current Architecture

The current architecture (ADR-0032) is optimal:

```
                    +------------------------+
                    |   Application Layer    |
                    +------------------------+
                              |
                              v
                    +------------------------+
                    | DataFrameCacheIntegration |
                    | - get_batch()           |
                    | - cache_row()           |
                    +------------------------+
                              |
                              v
                    +------------------------+
                    |  TieredCacheProvider   |
                    |  (Redis hot + S3 cold) |
                    +------------------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
      +---------------+               +---------------+
      | Redis (Hot)   |               | S3 (Cold)     |
      | Per-task rows |               | Per-task rows |
      | TTL: 1-24h    |               | TTL: 7-30d    |
      +---------------+               +---------------+
```

**Key design points**:

1. **Single source of truth**: Task-level cache entries only
2. **Batch aggregation at application layer**: `get_batch()` retrieves multiple tasks efficiently
3. **No redundant aggregate caches**: Avoids coherence issues and memory duplication
4. **Tiered storage**: Hot data in Redis, cold data in S3 (per ADR-0026)
5. **Surgical invalidation**: Only modified tasks invalidated

### Implementation Guidelines

#### For Project DataFrame Reads

```python
async def get_project_dataframe(project_gid: str, task_gids: list[str]) -> DataFrame:
    """Efficient project DataFrame retrieval using batch cache."""

    # Batch retrieve all task rows (single Redis MGET)
    cache_results = await cache.get_batch(
        keys=[f"{gid}:{project_gid}" for gid in task_gids],
        entry_type=EntryType.DATAFRAME,
    )

    # Identify cache misses
    hits = {k: v for k, v in cache_results.items() if v is not None}
    misses = [gid for gid in task_gids if f"{gid}:{project_gid}" not in hits]

    # Fetch and cache misses (parallel API calls)
    if misses:
        fresh_data = await fetch_and_extract(misses, project_gid)
        await cache.set_batch({
            f"{gid}:{project_gid}": entry for gid, entry in fresh_data.items()
        })
        hits.update(fresh_data)

    # Aggregate into DataFrame (application layer, no caching)
    return build_dataframe(hits.values())
```

#### For SaveSession Invalidation

```python
async def _invalidate_cache_for_results(self, result: SaveResult) -> None:
    """Invalidate only modified task entries (current implementation)."""

    for entity in result.succeeded:
        if hasattr(entity, "gid") and entity.gid:
            # O(1) invalidation per modified entity
            cache.invalidate(entity.gid, [EntryType.TASK, EntryType.SUBTASKS])

    # NO section-level invalidation
    # NO project-level invalidation
    # Aggregate structures are not cached
```

### Deduplication Strategy (Why NOT to Store Task Data Multiple Times)

**Reference-based aggregation** (if section/project views are ever needed):

```python
# WRONG: Duplicate data
section_cache = {
    "section:S1:P1": {
        "T1": {"gid": "T1", "name": "Task", ...},  # Duplicate
        "T2": {...},
    }
}

# RIGHT: Reference-based (if needed)
section_index = {
    "section_index:S1:P1": ["T1", "T2", "T3", ...],  # GID list only
}

# To get section data:
task_gids = cache.get("section_index:S1:P1")
task_data = cache.get_batch([f"{gid}:P1" for gid in task_gids])
```

**However**: Even reference-based indices add invalidation complexity. The current batch retrieval pattern is sufficient without explicit indices.

### TTL Strategy Per Level

| Cache Entry Type | Redis TTL | S3 TTL | Rationale |
|------------------|-----------|--------|-----------|
| Task row (DATAFRAME) | 1h | 30d | Frequently accessed, cheap to rebuild |
| Task metadata (TASK) | 1h | 7d | API response caching |
| Subtasks | 1h | 30d | Structural data, stable |
| Stories | 4h | 7d | Historical, rarely changes |

No aggregate-level caching means no aggregate-level TTLs to manage.

---

## 5. Conclusion

### Summary of Findings

| Question | Answer |
|----------|--------|
| Should we add section-level caching? | **No** - Invalidation cost exceeds benefit |
| Should we add project-level caching? | **No** - Cache thrashing under normal write patterns |
| Is the current task-level approach optimal? | **Yes** - Maximizes hit rate, minimizes invalidation cost |
| What is "over-caching"? | Caching at granularities where invalidation frequency exceeds read frequency |
| Does multi-level caching help for our use case? | **No** - Write patterns (SaveSession commits) would constantly invalidate aggregates |

### Key Insight

The legacy system's multi-level caching was designed for a read-heavy, write-rare access pattern. The autom8_asana SDK has a **write-frequent** pattern due to SaveSession batch commits. In write-frequent systems, aggregate caching provides negative value.

**Rule of thumb**: Cache at the granularity of your modification unit. Since SaveSession modifies individual tasks, cache at task level.

### Recommendations

1. **Keep current architecture** (ADR-0032 per-task with project context)
2. **Do not add section-level caching**
3. **Do not add project-level DataFrame caching**
4. **Use batch retrieval** for aggregate access patterns
5. **Rely on tiered storage** (Redis+S3 per ADR-0026) for cost optimization
6. **Monitor cache hit rates** to validate these assumptions in production

---

## Appendix A: Access Pattern Analysis

### Read Patterns (Observed)

| Operation | Frequency | Granularity | Cache Benefit |
|-----------|-----------|-------------|---------------|
| Get single task | Medium | Task | High |
| Get project tasks (DataFrame) | High | Task batch | High (via MGET) |
| Get section tasks | Low | Task batch | High (via MGET) |
| Get task subtasks | Medium | Task | High |

### Write Patterns (Observed)

| Operation | Frequency | Invalidation Scope |
|-----------|-----------|-------------------|
| SaveSession.commit() (single task) | High | 1 task |
| SaveSession.commit() (batch) | High | N tasks |
| Task moved between sections | Low | 1 task |
| Project custom field change | Very Low | All tasks in project |

### Invalidation Frequency vs. Read Frequency

For typical project (1000 tasks, 10 modifications/hour, 100 reads/hour):

| Cache Level | Invalidations/Hour | Reads Between Invalidations | Utility |
|-------------|-------------------|----------------------------|---------|
| Task | 10 | ~10 reads per modified task | High |
| Section (if cached) | 10 (cascade) | ~1 read per section | Low |
| Project (if cached) | 10 (cascade) | ~10 reads total, most stale | Negative |

---

## Appendix B: Cost-Benefit Summary

| Strategy | Memory | Invalidation Complexity | Hit Rate | Coherence Risk | Recommendation |
|----------|--------|------------------------|----------|----------------|----------------|
| Task-only (current) | 1x | O(1) | 99%+ | None | **Keep** |
| Task + Section | 1.5x | O(N) | 90% | Medium | Avoid |
| Task + Section + Project | 2.5x | O(N) | 70% | High | Avoid |
| Task with batch retrieval | 1x | O(1) | 99%+ | None | **Optimal** |
