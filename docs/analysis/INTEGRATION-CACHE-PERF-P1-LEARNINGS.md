# Integration Document: P1 Fetch Path Cache - Learnings for P2-P4

## Metadata

- **Document ID**: INTEGRATION-CACHE-PERF-P1-LEARNINGS
- **Status**: Complete
- **Author**: QA Adversary
- **Created**: 2025-12-23
- **Related Initiative**: [PROMPT-MINUS-1-CACHE-PERFORMANCE-META](/docs/initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md)

---

## Purpose

This document captures patterns, components, and learnings from the P1 (Fetch Path Investigation) sub-initiative that should inform the remaining sub-initiatives:

| Sub-Initiative | Status | Applicability |
|----------------|--------|---------------|
| **P1: Fetch Path** | COMPLETE | Source of learnings |
| P2: Detection | Pending | High - same coordinator pattern |
| P3: Hydration | Pending | High - opt_fields normalization |
| P4: Stories | Pending | Medium - batch operations |

---

## 1. Patterns Established

### 1.1 Two-Phase Cache Strategy

**Pattern**: Enumerate-then-lookup before fetching.

```
Phase 1: Enumerate GIDs (lightweight)
    |
    v
Phase 2: Batch cache lookup
    |
    v
Phase 3: Fetch only misses from API
    |
    v
Phase 4: Batch cache populate
    |
    v
Phase 5: Merge cached + fetched
```

**Why This Works**:
- GID enumeration uses minimal `opt_fields=["gid"]` (fast, small payload)
- Batch lookup is O(n) in-memory operation
- API calls only for cache misses
- Batch populate amortizes write overhead

**Applicability to P2-P4**:
| Sub-Initiative | Applicability | Notes |
|----------------|---------------|-------|
| P2: Detection | HIGH | Detection results can use same enumerate-lookup pattern with `EntryType.DETECTION` |
| P3: Hydration | MEDIUM | Traversal uses known GIDs; lookup before each hop |
| P4: Stories | HIGH | Story GIDs known upfront; batch lookup before incremental fetch |

### 1.2 Coordinator Pattern

**Pattern**: Encapsulate cache operations in a dedicated coordinator class.

```python
class TaskCacheCoordinator:
    """Coordinates Task-level cache operations for DataFrame builds."""

    async def lookup_tasks_async(self, task_gids: list[str]) -> dict[str, Task | None]
    async def populate_tasks_async(self, tasks: list[Task]) -> int
    def merge_results(self, task_gids_ordered, cache_hits, fetched_tasks) -> list[Task]
```

**Benefits**:
- Single responsibility for cache operations
- Testable in isolation (41 unit tests)
- Reusable across different fetch paths
- Encapsulates graceful degradation logic

**Recommendation for P2-P4**:

| Sub-Initiative | Coordinator Name | Key Methods |
|----------------|------------------|-------------|
| P2: Detection | `DetectionCacheCoordinator` | `lookup_detection_async()`, `cache_detection_async()` |
| P3: Hydration | `HydrationCacheCoordinator` or extend existing | `lookup_chain_async()`, `cache_traversal_async()` |
| P4: Stories | `StoryCacheCoordinator` | `lookup_batch_async()`, `cache_incremental_async()` |

### 1.3 Graceful Degradation

**Pattern**: Cache failures MUST NOT break primary operations.

```python
try:
    result = await cache_provider.get_batch(keys)
except Exception as e:
    logger.warning("Cache lookup failed", error=str(e))
    result = {}  # Treat all as misses
```

**Implementation Requirements**:
1. All cache operations wrapped in try/except
2. Failures logged at WARNING level (not ERROR)
3. Return safe default (empty dict, 0, etc.)
4. Primary operation continues successfully

**Tests Required**:
- `test_lookup_graceful_degradation`
- `test_populate_graceful_degradation`
- `test_workflow_with_cache_failure`

### 1.4 Batch Operations

**Pattern**: Use batch get/set instead of individual operations.

```python
# Good: Batch operation
result = cache_provider.get_batch(task_gids)

# Bad: Individual lookups
for gid in task_gids:
    result[gid] = cache_provider.get(gid)  # N round trips
```

**P1 Evidence**:
- `test_large_batch_lookup`: 500 entries without issue
- `test_large_batch_populate`: 500 entries without issue

**API Contract**:
```python
CacheProvider.get_batch(keys: list[str]) -> dict[str, CacheEntry | None]
CacheProvider.set_batch(entries: list[CacheEntry]) -> int
```

### 1.5 Structured Observability

**Pattern**: Include cache metrics in all log messages.

```python
logger.info(
    "DataFrame build completed",
    project_gid=project_gid,
    task_count=len(tasks),
    task_cache_hits=cache_result.cache_hits,
    task_cache_misses=cache_result.cache_misses,
    task_cache_hit_rate=round(cache_result.hit_rate, 3),
)
```

**Metrics to Include**:
| Metric | Type | Purpose |
|--------|------|---------|
| `cache_hits` | int | Number of cache hits |
| `cache_misses` | int | Number of cache misses |
| `cache_hit_rate` | float | Ratio for monitoring |
| `fetch_time_ms` | float | Latency tracking |
| `api_call_count` | int | API utilization |

---

## 2. Reusable Components

### 2.1 TaskCacheCoordinator

**Location**: `/src/autom8_asana/dataframes/builders/task_cache.py`

**Public API**:
```python
class TaskCacheCoordinator:
    def __init__(self, cache_provider: CacheProvider | None)

    async def lookup_tasks_async(
        self, task_gids: list[str]
    ) -> dict[str, Task | None]

    async def populate_tasks_async(
        self, tasks: list[Task], ttl_resolver: Callable | None = None
    ) -> int

    def merge_results(
        self,
        task_gids_ordered: list[str],
        cache_hits: dict[str, Task | None],
        fetched_tasks: list[Task],
    ) -> list[Task]
```

**Reuse in P2-P4**: Template for other coordinator classes.

### 2.2 TaskCacheResult

**Location**: `/src/autom8_asana/dataframes/builders/task_cache.py`

```python
@dataclass
class TaskCacheResult:
    """Cache operation result with metrics."""
    task_gids: list[str]
    cache_hits: dict[str, Task | None]
    cache_hits_count: int
    cache_misses: int

    @property
    def hit_rate(self) -> float

    @property
    def total_tasks(self) -> int
```

**Pattern for P2-P4**: Create analogous result classes (`DetectionCacheResult`, `StoryCacheResult`).

### 2.3 fetch_section_task_gids_async

**Location**: `/src/autom8_asana/dataframes/builders/parallel_fetch.py`

**Purpose**: Lightweight GID enumeration for two-phase strategy.

```python
async def fetch_section_task_gids_async(self) -> dict[str, list[str]]:
    """Enumerate task GIDs per section using minimal opt_fields."""
```

**Key Feature**: Uses `opt_fields=["gid"]` for minimal payload.

**Applicability**:
| Sub-Initiative | Enumeration Need | Recommendation |
|----------------|------------------|----------------|
| P2: Detection | Task GIDs in project | Reuse this method |
| P3: Hydration | Chain of GIDs (parent->child) | Already known from traversal |
| P4: Stories | Story GIDs for task | New lightweight enumerate method |

---

## 3. Considerations for P2-P4

### 3.1 P2: Detection Flow Investigation

**Current Problem**: `detect_entity_type_async()` makes Tier 4 API calls repeatedly; results discarded.

**Recommended Approach**:
1. Create `DetectionCacheCoordinator` following TaskCacheCoordinator pattern
2. Add `EntryType.DETECTION` to cache entry types
3. Cache key format: `{task_gid}:detection` or `detection:{task_gid}`
4. TTL: Consider longer TTL (entity type rarely changes)

**Key Learnings to Apply**:
- Two-phase strategy: Check cache before detection
- Batch operations: If detecting multiple tasks, batch lookup first
- Graceful degradation: Detection must work without cache

**Test Cases to Include**:
```python
test_detection_cache_hit_skips_api
test_detection_cache_miss_populates
test_detection_graceful_degradation
test_detection_batch_lookup
```

### 3.2 P3: Hydration Caching Investigation

**Current Problem**: `_traverse_upward_async()` uses `_DETECTION_OPT_FIELDS` which bypass client cache.

**Recommended Approach**:
1. Normalize opt_fields to match cached entries
2. Check cache before each traversal hop
3. Consider caching traversal chains (parent->grandparent mapping)

**Key Learnings to Apply**:
- Cache key consistency: Ensure hydration uses same keys as get_async()
- opt_fields alignment: Must match cached entry's opt_fields exactly
- Chain caching: Could cache "task X's holder chain is [A, B, C]"

**Considerations**:
- Hydration is hierarchical; may need chain-aware caching
- opt_fields mismatch is the root cause - focus on normalization first

### 3.3 P4: Stories/Metrics Caching Investigation

**Current Problem**: `cache/stories.py` has infrastructure; `StoriesClient` does not use it.

**Recommended Approach**:
1. Wire `IncrementalStoriesLoader` to `StoriesClient`
2. Create `StoryCacheCoordinator` if needed
3. Implement batch lookup for story GIDs

**Key Learnings to Apply**:
- Two-phase strategy: Enumerate story GIDs, batch lookup, fetch only new
- Incremental loading: Stories loader already supports sync/anchor
- Batch operations: Stories are typically fetched in bulk

**Existing Infrastructure**:
- `cache/stories.py` - IncrementalStoriesLoader exists
- Just needs wiring to StoriesClient

---

## 4. Common Test Patterns

### 4.1 Cache Hit Test Pattern

```python
async def test_cache_hit_skips_api(self):
    """Verify 100% cache hit makes zero API calls."""
    # Setup: Pre-populate cache with all needed entries
    cache.set_batch([entry1, entry2, entry3])

    # Action: Perform operation
    result = await coordinator.lookup_async(gids)

    # Assert: No API calls made
    mock_client.list_async.assert_not_called()
    assert result.cache_hits == 3
```

### 4.2 Cache Miss Test Pattern

```python
async def test_cache_miss_populates(self):
    """Verify cache miss fetches from API and populates cache."""
    # Setup: Empty cache
    cache = InMemoryCacheProvider()

    # Action: Perform operation
    result = await coordinator.fetch_and_cache_async(gids)

    # Assert: API was called and cache was populated
    mock_client.list_async.assert_called()
    assert cache.get(key) is not None
```

### 4.3 Graceful Degradation Test Pattern

```python
async def test_graceful_degradation(self):
    """Verify cache failure does not break operation."""
    # Setup: Cache that raises on all operations
    failing_cache = MagicMock()
    failing_cache.get_batch = MagicMock(side_effect=Exception("Redis down"))

    # Action: Perform operation
    result = await coordinator.lookup_async(gids)

    # Assert: Operation succeeded (treats all as misses)
    assert result is not None
    assert result.cache_misses == len(gids)
```

### 4.4 Large Batch Test Pattern

```python
async def test_large_batch(self):
    """Verify batch operations handle 500+ entries."""
    gids = [f"task{i}" for i in range(500)]

    result = await coordinator.lookup_async(gids)

    assert len(result) == 500
```

---

## 5. Documentation Requirements

Each P2-P4 sub-initiative should produce:

| Document | Template | Location |
|----------|----------|----------|
| Discovery | DISCOVERY-CACHE-PERF-{AREA}.md | `/docs/analysis/` |
| PRD | PRD-CACHE-PERF-{AREA}.md | `/docs/requirements/` |
| TDD | TDD-CACHE-PERF-{AREA}.md | `/docs/design/` |
| ADR (if architectural decisions) | ADR-012X-*.md | `/docs/decisions/` |
| Validation Report | VP-CACHE-PERF-{AREA}.md | `/docs/validation/` |

---

## 6. Quality Gates

### Pre-Implementation

- [ ] Discovery document complete
- [ ] Root cause identified and traced to code
- [ ] PRD approved with acceptance criteria
- [ ] TDD approved with implementation plan

### Post-Implementation

- [ ] All acceptance criteria have passing tests
- [ ] Edge cases covered
- [ ] Graceful degradation tested
- [ ] No Critical or High defects
- [ ] Validation report PASS
- [ ] INDEX.md updated

### Performance Validation

- [ ] Cache hit rate > 90% on warm cache
- [ ] Second fetch latency meets target
- [ ] No regression on first fetch latency

---

## 7. Coordination Points

### Shared Components

| Component | Owner | Used By |
|-----------|-------|---------|
| `CacheProvider` | Core SDK | P1, P2, P3, P4 |
| `EntryType` enum | Core SDK | P1, P2 (needs DETECTION) |
| Structured logging | Core SDK | All |

### Integration Risks

| Risk | Mitigation |
|------|------------|
| Cache key collisions | Unique prefixes per entry type |
| TTL conflicts | Entity-type TTL resolution (ADR-0126) |
| Memory pressure | LRU eviction, bounded cache size |
| Cascading failures | Graceful degradation pattern |

---

## Appendix A: P1 Deliverables Reference

| Deliverable | Location |
|-------------|----------|
| Discovery | `/docs/analysis/DISCOVERY-CACHE-PERF-FETCH-PATH.md` |
| PRD | `/docs/requirements/PRD-CACHE-PERF-FETCH-PATH.md` |
| TDD | `/docs/design/TDD-CACHE-PERF-FETCH-PATH.md` |
| ADR | `/docs/decisions/ADR-0119-dataframe-task-cache-integration.md` |
| Validation | `/docs/validation/VP-CACHE-PERF-FETCH-PATH.md` |
| Implementation | `/src/autom8_asana/dataframes/builders/task_cache.py` |
| Tests | `/tests/unit/dataframes/test_task_cache.py` |

---

## Appendix B: Test Coverage Summary (P1)

| Test File | Tests | Focus Area |
|-----------|-------|------------|
| test_task_cache.py | 41 | TaskCacheCoordinator unit tests |
| test_project_async.py | 32 | Builder integration with cache |
| test_parallel_fetch.py | 18 | Parallel fetch unit tests |

**Total P1 Tests**: 91 passing
**Code Coverage**: 92% on target modules
