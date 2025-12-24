# TDD: Cache Optimization Phase 2 - Fetch Path Cache Integration

## Metadata
- **TDD ID**: TDD-CACHE-OPT-P2
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: [PRD-CACHE-OPTIMIZATION-P2](/docs/requirements/PRD-CACHE-OPTIMIZATION-P2.md)
- **Related TDDs**:
  - [TDD-CACHE-PERF-FETCH-PATH](/docs/design/TDD-CACHE-PERF-FETCH-PATH.md) - P1 foundation
- **Related ADRs**:
  - [ADR-0119](/docs/decisions/ADR-0119-dataframe-task-cache-integration.md) - Task cache integration strategy
  - [ADR-0130](/docs/decisions/ADR-0130-cache-population-location.md) - Cache population location (NEW)

---

## Overview

This TDD defines the technical approach to close the **10x cache performance gap** where warm DataFrame fetch operations take 8.84s instead of the expected <1s. The design addresses three root causes identified in discovery:

1. **`list_async()` does not populate cache** (CRITICAL)
2. **Miss handling fetches ALL tasks** (HIGH)
3. **GID enumeration not cached** (MEDIUM - SHOULD priority)

The solution enhances the existing `TaskCacheCoordinator` pattern with post-fetch population and targeted miss handling, achieving <1s warm fetch latency with >90% cache hit rate.

---

## Requirements Summary

Per [PRD-CACHE-OPTIMIZATION-P2](/docs/requirements/PRD-CACHE-OPTIMIZATION-P2.md):

| Category | Key Requirements | Priority |
|----------|-----------------|----------|
| Cache Population | FR-POP-001 to FR-POP-005 | Must |
| Miss Handling | FR-MISS-001 to FR-MISS-005 | Must |
| GID Enumeration | FR-ENUM-001 to FR-ENUM-005 | Should |
| Observability | FR-OBS-001 to FR-OBS-004 | Must/Should |
| Performance | NFR-PERF-001: <1s warm fetch | Must |
| Compatibility | NFR-COMPAT-001/002: No breaking changes | Must |

---

## System Context

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   DataFrame Build Path                   │
                    └─────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────┐    ┌──────────────────────────────────────────────────────┐
│  SDK Consumer   │───▶│          ProjectDataFrameBuilder                     │
│                 │    │  build_with_parallel_fetch_async()                   │
└─────────────────┘    └──────────────────────────────────────────────────────┘
                                              │
                          ┌───────────────────┴───────────────────┐
                          ▼                                       ▼
        ┌──────────────────────────────┐        ┌──────────────────────────────┐
        │    TaskCacheCoordinator      │        │   ParallelSectionFetcher     │
        │  - lookup_tasks_async()      │        │  - fetch_all()               │
        │  - populate_tasks_async()    │        │  - fetch_section_task_gids() │
        │  - merge_results()           │        │  - fetch_by_gids() [NEW]     │
        └──────────────────────────────┘        └──────────────────────────────┘
                          │                                       │
                          ▼                                       ▼
        ┌──────────────────────────────┐        ┌──────────────────────────────┐
        │      CacheProvider           │        │       TasksClient            │
        │  - get_batch()               │        │  - list_async()              │
        │  - set_batch()               │        │                              │
        └──────────────────────────────┘        └──────────────────────────────┘
```

**Key Integration Points:**
- `ProjectDataFrameBuilder` orchestrates the build workflow
- `TaskCacheCoordinator` handles cache operations (lookup, populate, merge)
- `ParallelSectionFetcher` handles API fetches (sections and tasks)
- `CacheProvider` provides batch get/set operations
- `TasksClient.list_async()` fetches tasks from Asana API (unchanged)

---

## Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ProjectDataFrameBuilder (Enhanced)                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  build_with_parallel_fetch_async()                                      ││
│  │  ┌───────────────────────────────────────────────────────────────────┐  ││
│  │  │  1. Enumerate GIDs     (ParallelSectionFetcher)                   │  ││
│  │  │  2. Cache Lookup       (TaskCacheCoordinator.lookup_tasks_async)  │  ││
│  │  │  3. Fetch Misses       (ParallelSectionFetcher.fetch_by_gids) NEW │  ││
│  │  │  4. Populate Cache     (TaskCacheCoordinator.populate_tasks_async)│  ││
│  │  │  5. Merge Results      (TaskCacheCoordinator.merge_results)       │  ││
│  │  │  6. Build DataFrame    (existing extraction logic)                │  ││
│  │  └───────────────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    ParallelSectionFetcher (Enhanced)                         │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  fetch_all() [existing]      │  │  fetch_by_gids() [NEW]               │ │
│  │  - Fetches ALL tasks         │  │  - Fetches ONLY specified GIDs       │ │
│  │  - Used for cold cache       │  │  - Used for warm cache misses        │ │
│  └──────────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  fetch_section_task_gids_async() [existing - extended]               │   │
│  │  - Can cache enumeration results via EnumerationCacheCoordinator     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                 EnumerationCacheCoordinator [NEW - SHOULD]                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  - lookup_section_gids_async(section_gids: list[str])                   ││
│  │  - populate_section_gids_async(section_gid_map: dict[str, list[str]])   ││
│  │  - Uses EntryType.SECTION_TASKS [NEW entry type]                        ││
│  │  - TTL: 1800s (matches section cache)                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

| Component | Responsibility | Changes |
|-----------|---------------|---------|
| `ProjectDataFrameBuilder` | Orchestrates build flow, calls cache + fetch | FIX miss handling to call `fetch_by_gids()` instead of `fetch_all()` |
| `TaskCacheCoordinator` | Cache lookup, populate, merge | No changes - reuse existing |
| `ParallelSectionFetcher` | Section enumeration, task fetch | ADD `fetch_by_gids()` method |
| `EnumerationCacheCoordinator` | Cache section-to-GID mappings | NEW component (SHOULD priority) |
| `EntryType` | Cache entry type enum | ADD `SECTION_TASKS` (if SHOULD implemented) |

---

### Data Model

#### Existing Models (No Changes)

```python
# CacheEntry (cache/entry.py) - unchanged
@dataclass(frozen=True)
class CacheEntry:
    key: str
    data: dict[str, Any]
    entry_type: EntryType
    version: datetime
    cached_at: datetime
    ttl: int | None = 300

# TaskCacheResult (task_cache.py) - unchanged
@dataclass
class TaskCacheResult:
    cached_tasks: list[Task]
    fetched_tasks: list[Task]
    cache_hits: int
    cache_misses: int
    all_tasks: list[Task]
```

#### New/Extended Models

```python
# EntryType (cache/entry.py) - ADD new type for SHOULD items
class EntryType(str, Enum):
    TASK = "task"
    # ... existing types ...
    SECTION_TASKS = "section_tasks"  # NEW - section-to-GID mapping

# EnumerationCacheResult (NEW - dataframes/builders/enumeration_cache.py)
@dataclass
class EnumerationCacheResult:
    """Result of section GID enumeration cache operations."""
    section_gids: dict[str, list[str]]  # section_gid -> task_gids
    cache_hits: int                      # sections found in cache
    cache_misses: int                    # sections needing API fetch

    @property
    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
```

#### Cache Key Formats

| Entry Type | Key Format | TTL | Example |
|------------|-----------|-----|---------|
| `TASK` | `{task_gid}` | Entity-based (60-3600s) | `"1234567890123"` |
| `SECTION_TASKS` | `section:{section_gid}` | 1800s | `"section:9876543210987"` |

---

### Data Flow

#### Cold Fetch Flow (First Call)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ProjectDataFrameBuilder.build_with_parallel_fetch_async()                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. Enumerate GIDs                                                           │
│     fetcher.fetch_section_task_gids_async()                                 │
│     Returns: {"section1": ["t1", "t2"], "section2": ["t3", "t4"]}           │
│     API Calls: 1 (sections list) + N (section task GIDs)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. Cache Lookup                                                             │
│     coordinator.lookup_tasks_async(["t1", "t2", "t3", "t4"])                │
│     Returns: {t1: None, t2: None, t3: None, t4: None}  (all misses)         │
│     API Calls: 0                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. Fetch ALL (Cold Cache - No Tasks Cached)                                 │
│     fetcher.fetch_all() [existing path]                                      │
│     Returns: [Task1, Task2, Task3, Task4] with full opt_fields              │
│     API Calls: N (section fetches)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. Populate Cache [NEW - FR-POP-001]                                        │
│     coordinator.populate_tasks_async([Task1, Task2, Task3, Task4])          │
│     Writes: 4 cache entries with entity-based TTL                            │
│     API Calls: 0                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. Build DataFrame                                                          │
│     (existing extraction logic)                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Cold Fetch Total Time:** ~13s (as before - no regression)

---

#### Warm Fetch Flow (Second Call) - TARGET STATE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ProjectDataFrameBuilder.build_with_parallel_fetch_async()                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. Enumerate GIDs                                                           │
│     fetcher.fetch_section_task_gids_async()                                 │
│     Returns: {"section1": ["t1", "t2"], "section2": ["t3", "t4"]}           │
│     API Calls: ~35 (sections + task GIDs) - Can be cached (SHOULD)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. Cache Lookup                                                             │
│     coordinator.lookup_tasks_async(["t1", "t2", "t3", "t4"])                │
│     Returns: {t1: Task1, t2: Task2, t3: Task3, t4: Task4} (all HITS!)       │
│     API Calls: 0                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. Check Miss GIDs                                                          │
│     miss_gids = []  (empty - all cached!)                                   │
│     SKIP fetch_by_gids() - no API calls needed                              │
│     API Calls: 0                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. Build DataFrame from Cached Tasks                                        │
│     (extraction from in-memory Task objects)                                 │
│     API Calls: 0                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Warm Fetch Target Time:** <1s (with SHOULD: <0.5s)

---

#### Partial Cache Flow (Some Misses)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. Cache Lookup                                                             │
│     Returns: {t1: Task1, t2: None, t3: Task3, t4: None}                     │
│     cached = {t1: Task1, t3: Task3}, miss_gids = ["t2", "t4"]               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. Fetch ONLY Misses [NEW - FR-MISS-001/002]                               │
│     fetcher.fetch_by_gids(["t2", "t4"])                                     │
│     Returns: [Task2, Task4] - only missing tasks fetched                    │
│     API Calls: 2 (only sections containing t2, t4)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. Populate Cache with Fetched                                              │
│     coordinator.populate_tasks_async([Task2, Task4])                        │
│     Writes: 2 cache entries                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. Merge Results [FR-MISS-003]                                              │
│     coordinator.merge_results(["t1","t2","t3","t4"], cached, fetched)       │
│     Returns: TaskCacheResult with all_tasks in original order               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### API Contracts

#### New Method: `ParallelSectionFetcher.fetch_by_gids()`

```python
async def fetch_by_gids(
    self,
    task_gids: list[str],
    section_gid_map: dict[str, list[str]] | None = None,
) -> FetchResult:
    """Fetch only specified task GIDs from the project.

    Per FR-MISS-002: Targeted fetch for cache misses only, avoiding
    full re-fetch of all section tasks.

    Strategy:
    - If section_gid_map provided, filter to sections containing target GIDs
    - Fetch only those sections, filter results to target GIDs
    - More efficient than N individual get_async() calls

    Args:
        task_gids: List of task GIDs to fetch.
        section_gid_map: Optional mapping of section_gid -> task_gids.
            If provided, used to determine which sections to query.
            If None, queries all sections and filters.

    Returns:
        FetchResult containing only the requested tasks.

    Example:
        >>> miss_gids = ["task1", "task3"]
        >>> result = await fetcher.fetch_by_gids(miss_gids, section_gid_map)
        >>> assert all(t.gid in miss_gids for t in result.tasks)
    """
```

#### New Component: `EnumerationCacheCoordinator` (SHOULD Priority)

```python
class EnumerationCacheCoordinator:
    """Coordinates section-to-GID enumeration cache operations.

    Per FR-ENUM-001: Caches section-task-GID mappings to avoid
    repeated enumeration API calls on warm fetches.

    Example:
        >>> coord = EnumerationCacheCoordinator(cache_provider)
        >>> cached = await coord.lookup_section_gids_async(section_gids)
        >>> # cached = {section1: ["t1", "t2"], section2: None}
    """

    ENTRY_TTL: int = 1800  # 30 minutes (matches section cache)

    async def lookup_section_gids_async(
        self,
        section_gids: list[str],
    ) -> dict[str, list[str] | None]:
        """Batch lookup section-to-GID mappings from cache.

        Args:
            section_gids: List of section GIDs to lookup.

        Returns:
            Dict mapping section_gid -> list of task_gids (or None if miss).
        """

    async def populate_section_gids_async(
        self,
        section_gid_map: dict[str, list[str]],
    ) -> int:
        """Batch populate cache with section-to-GID mappings.

        Args:
            section_gid_map: Dict mapping section_gid -> task_gids.

        Returns:
            Count of sections cached.
        """
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Where cache population occurs | Builder level (after `fetch_all()`) | PRD constraint on `list_async()`; builder has context | [ADR-0130](/docs/decisions/ADR-0130-cache-population-location.md) |
| Miss fetch strategy | `fetch_by_gids()` with section filtering | More efficient than N `get_async()`; uses bulk fetch | PRD FR-MISS-002 |
| GID enumeration caching | New EntryType.SECTION_TASKS | Distinct key space; appropriate TTL | FR-ENUM-002 |
| TTL for enumeration cache | 1800s (30 min) | Matches section cache; sections change infrequently | FR-ENUM-003 |
| Merge order preservation | Use `task_gids_ordered` from enumeration | Maintains section ordering in DataFrame | FR-MISS-003 |

---

## Complexity Assessment

**Level: Module**

This is an enhancement to an existing subsystem, not a new service:

| Factor | Assessment |
|--------|-----------|
| Scope | Single subsystem (DataFrame building) |
| Components | Extends 2 existing components, adds 1 optional new one |
| External Dependencies | Uses existing cache infrastructure |
| Data Model Changes | One new EntryType (SHOULD items only) |
| Breaking Changes | None |
| Test Complexity | Unit tests sufficient; integration test for E2E |

**Escalation Check:**
- No new service boundaries
- No new external integrations
- No infrastructure changes
- Stays within Module complexity

---

## Implementation Plan

### Phase 1: Cache Population Fix (MUST - Critical Path)

**Goal:** Tasks fetched via `list_async()` are cached for subsequent lookups.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 1.1 Add cache population after fetch_all() | `project.py` | Add `populate_tasks_async()` call after line 369 | 1h |
| 1.2 Update structured logging | `project.py` | Add `populated_count`, `population_time_ms` | 0.5h |
| 1.3 Unit tests for population | `test_project_async.py` | `test_cache_populated_after_fetch` | 1h |
| 1.4 Integration test | `test_cache_warm_fetch.py` | New file for E2E validation | 2h |

**Acceptance Criteria:**
- After first fetch, cache contains all fetched tasks
- Second fetch shows >90% hit rate
- `CacheMetrics.hit_rate` observable in logs

---

### Phase 2: Miss Handling Optimization (MUST - High Priority)

**Goal:** When cache has partial hits, fetch only missing GIDs.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 2.1 Implement `fetch_by_gids()` | `parallel_fetch.py` | New method with section filtering | 2h |
| 2.2 Fix builder miss handling | `project.py` | Replace `fetch_all()` with `fetch_by_gids()` on line 369 | 1h |
| 2.3 Handle 100% cache hit | `project.py` | Skip API fetch entirely | 0.5h |
| 2.4 Handle 0% cache hit | `project.py` | Fall back to `fetch_all()` | 0.5h |
| 2.5 Unit tests | `test_parallel_fetch.py`, `test_project_async.py` | Test all edge cases | 2h |

**Acceptance Criteria:**
- Partial cache hit fetches only miss GIDs
- 100% cache hit = 0 API calls
- 0% cache hit = same behavior as current (full fetch)

---

### Phase 3: GID Enumeration Caching (SHOULD - Enhancement)

**Goal:** Cache section-to-GID mappings to eliminate enumeration API calls.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 3.1 Add `EntryType.SECTION_TASKS` | `cache/entry.py` | New enum value | 0.5h |
| 3.2 Create `EnumerationCacheCoordinator` | `dataframes/builders/enumeration_cache.py` | New coordinator class | 2h |
| 3.3 Integrate with builder | `project.py` | Cache lookup/populate for enumeration | 1h |
| 3.4 Unit tests | `test_enumeration_cache.py` | New test file | 2h |

**Acceptance Criteria:**
- Second enumeration returns from cache (0 API calls)
- Graceful degradation if cache unavailable
- TTL of 1800s applied

---

### Phase 4: Observability Enhancement (Should)

**Goal:** Complete observability for cache operations.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 4.1 Add `api_calls_saved` metric | `project.py` | Calculate based on hit count | 0.5h |
| 4.2 Add `cache_source` field | `project.py` | Distinguish task vs enumeration cache | 0.5h |
| 4.3 Update demo script | `scripts/demo_parallel_fetch.py` | Print cache metrics | 1h |

---

### Dependency Graph

```
Phase 1 (Population) ──────────────────────────────────┐
                                                       ▼
Phase 2 (Miss Handling) ─────────────────────────────▶ Phase 4 (Observability)
                                                       ▲
Phase 3 (Enumeration - SHOULD) ───────────────────────┘
```

Phase 1 and 2 are independent; Phase 3 is optional; Phase 4 depends on 1+2.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Cache population adds latency to cold fetch | Low | Medium | Async batch operation; target <100ms |
| `fetch_by_gids()` complex section filtering | Medium | Low | Fallback to `fetch_all()` if implementation issues |
| opt_fields mismatch between fetch and cache | High | Medium | Validate `_BASE_OPT_FIELDS` included in cached entries |
| GID enumeration cache stale after task moves | Low | Low | 1800s TTL; section-level scope limits impact |
| Memory pressure from caching 3,530+ tasks | Medium | Low | Existing TTL eviction; bounded by project size |
| Breaking existing tests | High | Low | Run full test suite in CI before merge |

---

## Observability

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `task_cache_hits` | Counter | Tasks found in cache |
| `task_cache_misses` | Counter | Tasks not found in cache |
| `task_cache_hit_rate` | Gauge | Ratio of hits to total lookups |
| `tasks_fetched_from_api` | Counter | Tasks fetched (API calls) |
| `population_time_ms` | Histogram | Time to populate cache |
| `api_calls_saved` | Counter | API calls avoided by cache |

### Logging

```python
# Build started
logger.info(
    "dataframe_build_started",
    extra={
        "project_gid": project_gid,
        "use_cache": True,
        "task_cache_enabled": True,
    },
)

# Build completed
logger.info(
    "dataframe_build_completed",
    extra={
        "project_gid": project_gid,
        "task_count": 3530,
        "fetch_time_ms": 850.0,
        "task_cache_hits": 3500,
        "task_cache_misses": 30,
        "task_cache_hit_rate": 0.991,
        "tasks_fetched_from_api": 30,
        "api_calls_saved": 35,
        "populated_count": 30,
        "population_time_ms": 45.0,
    },
)
```

### Alerting

| Alert | Condition | Action |
|-------|-----------|--------|
| Cache hit rate degradation | hit_rate < 0.5 on warm fetch | Investigate cache eviction/TTL |
| Population failure | `task_cache_population_failed` logged | Check cache provider health |

---

## Testing Strategy

### Unit Tests

| Test Case | File | Validates |
|-----------|------|-----------|
| `test_cache_populated_after_fetch` | `test_project_async.py` | FR-POP-001 |
| `test_warm_fetch_uses_cache` | `test_project_async.py` | FR-MISS-004, NFR-PERF-001 |
| `test_partial_cache_hit_fetches_only_misses` | `test_project_async.py` | FR-MISS-001 |
| `test_fetch_by_gids_returns_only_requested` | `test_parallel_fetch.py` | FR-MISS-002 |
| `test_100_percent_cache_hit_zero_api_calls` | `test_project_async.py` | FR-MISS-004 |
| `test_0_percent_cache_hit_full_fetch` | `test_project_async.py` | FR-MISS-005 |
| `test_population_graceful_degradation` | `test_task_cache.py` | NFR-DEGRADE-001 |
| `test_enumeration_cache_hit` | `test_enumeration_cache.py` | FR-ENUM-001 |

### Integration Tests

| Test Case | File | Validates |
|-----------|------|-----------|
| `test_warm_fetch_latency_under_1s` | `test_cache_warm_fetch.py` | NFR-PERF-001 |
| `test_cold_fetch_no_regression` | `test_cache_warm_fetch.py` | NFR-PERF-003 |
| `test_cache_population_overhead` | `test_cache_warm_fetch.py` | NFR-PERF-004 |

### Performance Validation

```bash
# Run benchmark script
python scripts/demo_parallel_fetch.py --name "Business Offers"

# Expected output (warm fetch):
# First fetch: ~13.55s (cold)
# Second fetch: <1.0s (warm) - TARGET
# Cache hit rate: >90%
```

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should `fetch_by_gids()` use section filtering or individual `get_async()`? | Architect | Resolved | Section filtering (more efficient, preserves batch semantics) |
| What if section_gid_map not available when calling `fetch_by_gids()`? | Architect | Resolved | Accept optional param; if None, fetch all sections and filter |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial draft based on PRD-CACHE-OPTIMIZATION-P2 |

---

## Appendix A: Current vs Target Fetch Flow

### Current State (Problem)

```
First Fetch:
  enumerate_gids() [API] -> lookup_cache() [all miss] -> fetch_all() [API] -> populate_cache()
  Time: ~13.55s

Second Fetch:
  enumerate_gids() [API!] -> lookup_cache() [partial] -> fetch_all() [API!] -> filter -> merge
  Time: ~8.84s  <-- PROBLEM: Still fetching ALL tasks
```

### Target State (Solution)

```
First Fetch:
  enumerate_gids() [API] -> lookup_cache() [all miss] -> fetch_all() [API] -> populate_cache() [NEW]
  Time: ~13.55s (no regression)

Second Fetch:
  enumerate_gids() [API or cache] -> lookup_cache() [all HIT] -> skip fetch -> build from cache
  Time: <1.0s  <-- TARGET ACHIEVED
```

---

## Appendix B: Key File Locations

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/autom8_asana/dataframes/builders/project.py` | DataFrame builder | 326-497 (`build_with_parallel_fetch_async`) |
| `src/autom8_asana/dataframes/builders/task_cache.py` | Task cache coordinator | 133-206 (lookup), 208-290 (populate) |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Parallel fetcher | 109-187 (`fetch_all`), 200-257 (`fetch_section_task_gids`) |
| `src/autom8_asana/cache/entry.py` | Cache entry types | 11-33 (`EntryType` enum) |
| `tests/unit/dataframes/test_project_async.py` | Builder tests | Existing |
| `tests/unit/dataframes/test_task_cache.py` | Cache coordinator tests | Existing |

---

## Appendix C: Backward Compatibility Checklist

- [x] No changes to `ProjectDataFrameBuilder` constructor signature
- [x] No changes to `build_with_parallel_fetch_async()` parameters
- [x] No changes to `TasksClient.list_async()` behavior
- [x] `use_cache=False` still bypasses all caching
- [x] Graceful degradation when cache_provider is None
- [x] Existing tests pass without modification
