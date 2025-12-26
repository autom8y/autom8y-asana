# ADR-0049: Batch Operations and GID Enumeration Caching

## Metadata
- **Status**: Accepted
- **Author**: Tech Writer (consolidation)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0116, ADR-0131
- **Related**: reference/CACHE.md, ADR-0046 (Cache Protocol Extension)

## Context

DataFrame generation for large projects revealed two performance bottlenecks:

**Problem 1: Task Cache Population** (ADR-0116)
Building DataFrame for 3,500-task project requires checking and populating 3,500 cache entries. Individual cache operations create O(n) latency penalty:
- 3,500 individual get calls: 3,500 × 2ms = 7 seconds
- 3,500 individual set calls: 3,500 × 2ms = 7 seconds
- Total overhead: 14 seconds just for cache operations

**Problem 2: GID Enumeration** (ADR-0131)
Even with task-level caching, warm DataFrame fetch took 9.67s instead of <1s target. Profiling revealed root cause: GID enumeration (list sections, fetch section task GIDs) not cached—35+ API calls before task cache even consulted:
- List sections: 1 API call
- Fetch tasks for each section: 34 API calls (for 34 sections)
- Only then: Check task cache (mostly hits)

Second DataFrame fetch should be <1s with fully warm cache, but GID enumeration repeated every time.

## Decision

**Implement two-tier optimization: batch cache operations + GID enumeration caching.**

### Part 1: Batch Cache Operations

Extend `CacheProvider` protocol with batch methods (ADR-0046):

```python
class CacheProvider(Protocol):
    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Batch retrieve cache entries.

        Returns dict mapping keys to entries (None if missing).
        Single call for N keys vs N individual calls.
        """

    def set_batch(self, entries: dict[str, CacheEntry]) -> None:
        """Batch store cache entries.

        Single call for N entries vs N individual calls.
        """
```

Implement check-fetch-populate pattern in DataFrame builder:

```python
async def build_async(self, project_gid: str, ...) -> pd.DataFrame:
    """Build DataFrame with batch cache optimization."""

    # Phase 1: Enumerate task GIDs (see Part 2)
    section_tasks = await self._fetcher.enumerate_gids(project_gid)
    all_gids = [gid for tasks in section_tasks.values() for gid in tasks]

    # Phase 2: Batch check cache for all expected tasks
    cached_entries = self._cache.get_batch(all_gids, EntryType.DATAFRAME)

    # Phase 3: Identify cache misses
    cache_hits = {k: v.data for k, v in cached_entries.items() if v is not None}
    cache_misses = [gid for gid in all_gids if gid not in cache_hits]

    # Phase 4: Fetch only cache misses via parallel section fetch
    if cache_misses:
        fresh_tasks = await self._fetcher.fetch_sections_parallel(
            project_gid,
            opt_fields=self._opt_fields,
        )
    else:
        fresh_tasks = []

    # Phase 5: Batch populate newly fetched tasks
    if fresh_tasks:
        new_entries = {
            task["gid"]: CacheEntry(
                key=f"{task['gid']}:{project_gid}",
                data=task,
                entry_type=EntryType.DATAFRAME,
                ...
            )
            for task in fresh_tasks
        }
        self._cache.set_batch(new_entries)

    # Phase 6: Merge cached + fetched results
    all_tasks = list(cache_hits.values()) + fresh_tasks
    return self._build_dataframe(all_tasks)
```

**Key characteristics**:
- 1 batch get call vs 3,500 individual calls
- 1 batch set call vs N individual calls (N = cache misses)
- Handles partial cache scenarios efficiently
- Per-task versioning via `modified_at` preserved

### Part 2: GID Enumeration Caching

Cache section list and GID enumeration at fetcher level using two-tier structure:

```python
class ProjectDataFrameFetcher:
    """Fetcher with GID enumeration caching."""

    async def enumerate_gids(
        self,
        project_gid: str,
    ) -> dict[str, list[str]]:
        """Get section -> task_gids mapping with caching."""

        # Tier 1: Check section list cache
        sections_key = f"project:{project_gid}:sections"
        sections_entry = self._cache.get_versioned(
            sections_key,
            EntryType.PROJECT_SECTIONS,
        )

        if sections_entry:
            sections = sections_entry.data
        else:
            # Cache miss: fetch sections
            sections = await self._client.sections.list_async(
                project_gid,
                opt_fields=["name", "gid"],
            )
            self._cache.set_versioned(
                sections_key,
                CacheEntry(
                    key=sections_key,
                    data=sections,
                    entry_type=EntryType.PROJECT_SECTIONS,
                    ttl=1800,  # 30 minutes (stable)
                    ...
                ),
            )

        # Tier 2: Check GID enumeration cache
        enum_key = f"project:{project_gid}:gid_enumeration"
        enum_entry = self._cache.get_versioned(
            enum_key,
            EntryType.GID_ENUMERATION,
        )

        if enum_entry:
            return enum_entry.data  # dict[section_gid, list[task_gid]]

        # Cache miss: fetch GIDs for each section
        section_tasks = {}
        for section in sections:
            tasks = await self._client.tasks.list_async(
                section_gid=section["gid"],
                opt_fields=["gid"],  # Minimal fetch
            )
            section_tasks[section["gid"]] = [t["gid"] for t in tasks]

        # Store enumeration
        self._cache.set_versioned(
            enum_key,
            CacheEntry(
                key=enum_key,
                data=section_tasks,
                entry_type=EntryType.GID_ENUMERATION,
                ttl=300,  # 5 minutes (more volatile)
                ...
            ),
        )

        return section_tasks
```

**Cache structure**:
- `PROJECT_SECTIONS`: `project:{gid}:sections` → section metadata (1800s TTL)
- `GID_ENUMERATION`: `project:{gid}:gid_enumeration` → `dict[section_gid, list[task_gid]]` (300s TTL)

**Independent TTLs**:
- Section structure: 30 minutes (stable)
- Task membership: 5 minutes (more volatile)
- Partial refresh: Section cache hits even when GID enum expired

## Rationale

### Why Batch Operations?

Individual cache operations for 3,500 tasks:
- Network roundtrips: 3,500 × (latency per call)
- Serialization overhead: 3,500 × (encode/decode time)
- Lock contention: 3,500 separate acquisitions

Batch operations:
- Single network roundtrip
- Amortized serialization
- Single lock acquisition
- Backend-specific optimizations (Redis `MGET`/`MSET`)

### Why Check-Fetch-Populate Pattern?

| Pattern | Warm Cache | Cold Cache | Partial Cache |
|---------|------------|------------|---------------|
| Fetch-then-cache | Always fetches API | Efficient | Always fetches API |
| **Check-fetch-populate** | **Zero API calls** | **Single fetch** | **Fetch misses only** |

Check-fetch-populate handles all scenarios optimally.

### Why Two-Tier GID Enumeration?

Section structure changes rarely (project reorganizations). Task membership changes more frequently (task creation/deletion). Independent TTLs optimize for access patterns:
- Section list cached 30 minutes (stable)
- GID enumeration cached 5 minutes (more volatile)

Alternative single-tier caching:
- Long TTL: Stale task lists
- Short TTL: Unnecessary section refetches

### Why Fetcher-Level Caching?

| Level | Pros | Cons |
|-------|------|------|
| Client | Transparent to all callers | Too coarse-grained |
| **Fetcher** | **Operation-specific, right scope** | **Requires constructor injection** |
| Builder | Simple access | Wrong responsibility |

Fetcher owns enumeration operation, appropriate scope for caching.

### Why No Coordinator for GID Enumeration?

Batch task cache uses `TaskCacheCoordinator` for orchestration. GID enumeration doesn't need coordinator because:
- Simpler operation (just enumeration, not hydration)
- ~25 lines inline vs 50-line coordinator
- Single consumer (ProjectDataFrameFetcher)
- No complex invalidation logic

Inline logic is clearer and more maintainable for this use case.

## Alternatives Considered

### Alternative 1: Individual Cache Operations
**Rejected**: Unacceptable latency for large projects. 14-second overhead for 3,500 tasks.

### Alternative 2: Cache Entire Project Result
**Rejected**: Cache thrashing. Single task modification invalidates entire 3,500-task cache. Hit rate plummets.

### Alternative 3: Single-Tier GID Enumeration
**Rejected**: Can't have different TTLs for stable vs volatile data. Forced to choose between staleness and efficiency.

### Alternative 4: Per-Section GID Caching
**Rejected**: Higher overhead (34 cache entries vs 1). More invalidation complexity. No clear benefit.

### Alternative 5: Builder-Level GID Caching
**Rejected**: Wrong responsibility. Fetcher owns enumeration operation.

## Consequences

### Positive
- Warm DataFrame fetch: 9.67s → <1s (10x speedup)
- Batch operations: 1 call vs 3,500 individual calls
- Zero API calls for fully warm cache
- Partial refresh: Section structure can stay cached when GIDs expire
- Per-task versioning maintained (correctness preserved)
- Backend optimization enabled (Redis `MGET`/`MSET`)

### Negative
- Batch operations require protocol extension (ADR-0046)
- Two-tier enumeration adds conceptual complexity
- Cache key proliferation: Additional PROJECT_SECTIONS and GID_ENUMERATION entry types
- Fetcher requires cache provider injection via constructor

### Neutral
- Memory overhead: Minimal (GID enumeration ~10KB for 3,500 tasks)
- TTL tuning: May need adjustment based on project volatility patterns
- Invalidation: GID enumeration expires via TTL (no hook-based invalidation)

## Impact

Production metrics after implementation:
- First DataFrame build: No change (cold cache)
- Second DataFrame build: 9.67s → <1s (90% improvement)
- API calls per warm fetch: 35+ → 0 (100% reduction)
- Cache hit rate for stable projects: 99%+

Combined with progressive TTL (ADR-0048), achieves <1s warm fetch target for 3,500-task projects.

## Compliance

**Enforcement mechanisms**:
1. Code review: DataFrame builders use batch operations, not individual cache calls
2. Testing: Integration tests verify batch behavior, warm fetch <1s target
3. Monitoring: Metrics on `cache_batch_size`, `gid_enum_cache_hit_rate`
4. Performance: CI benchmark tests enforce <1s warm fetch regression detection

**Configuration**:
```python
@dataclass
class CacheConfig:
    # Batch operation tuning
    max_batch_size: int = 5000

    # GID enumeration TTLs
    section_list_ttl: int = 1800    # 30 minutes
    gid_enumeration_ttl: int = 300  # 5 minutes
```
