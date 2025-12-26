# ADR-0131: GID Enumeration Cache Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-CACHE-OPT-P3, TDD-CACHE-OPTIMIZATION-P3, ADR-0130 (Cache Population Location), ADR-0026 (Two-Tier Cache Architecture)

## Context

Phase 2 cache optimization (ADR-0130, TDD-CACHE-OPT-P2) achieved task-level caching, but warm DataFrame fetch still takes 9.67s instead of the target <1s. A three-agent triage audit with unanimous consensus identified the root cause: **GID enumeration is NOT cached**.

### Current Flow (Problem)

```
fetch_section_task_gids_async()
    |
    +-- _list_sections()              [1 API call - NOT CACHED]
    |
    +-- _fetch_section_gids() x N     [N API calls - NOT CACHED]
    |
    v
Returns: dict[str, list[str]]         [35+ API calls total]
```

Even with 100% task cache hit rate, 35+ API calls occur for GID enumeration before the task cache is even consulted. This accounts for 9.5s of the 9.67s warm fetch latency.

### Forces at Play

| Force | Description |
|-------|-------------|
| **Performance** | Must achieve <1s warm fetch (currently 9.67s) |
| **Surgical Scope** | PRD limits changes to `parallel_fetch.py` and `entry.py` |
| **Pattern Consistency** | Should follow Phase 2 patterns (graceful degradation, structured logging) |
| **Cache Granularity** | Per-project vs per-section caching trade-off |
| **TTL Differences** | Section structure (stable) vs task membership (changes more often) |
| **PRD Specification** | PRD specifies two entry types: `PROJECT_SECTIONS` and `GID_ENUMERATION` |

### Key Questions

1. **Where** should cache lookup/populate occur?
2. **What granularity** - cache entire GID enumeration or per-section?
3. **How** does `ParallelSectionFetcher` access the cache provider?
4. **Whether** to cache section list separately or derive from GID enumeration?

## Decision

**Cache GID enumeration at the fetcher level using constructor-injected cache provider, with two-tier caching: section list (long TTL) and GID enumeration (short TTL).**

### Specific Decisions

| Aspect | Decision |
|--------|----------|
| Cache Location | Inside `ParallelSectionFetcher` methods |
| Cache Provider Access | Constructor parameter: `cache_provider: CacheProvider | None = None` |
| Section List Cache | `EntryType.PROJECT_SECTIONS`, key `project:{gid}:sections`, TTL 1800s |
| GID Enumeration Cache | `EntryType.GID_ENUMERATION`, key `project:{gid}:gid_enumeration`, TTL 300s |
| Granularity | Per-project (not per-section) |
| Cache Entry Format | Section list: `list[dict]`, GID enum: `dict[str, list[str]]` |

### Cache Flow (Target State)

```
fetch_section_task_gids_async()
    |
    +-- Check cache: project:{gid}:gid_enumeration
    |
    +-- HIT? Return cached result (0 API calls, <10ms)
    |
    +-- MISS?
           |
           +-- _list_sections()
           |      +-- Check cache: project:{gid}:sections
           |      +-- HIT? Return cached sections
           |      +-- MISS? API call, populate cache
           |
           +-- _fetch_section_gids() x N [API calls]
           |
           +-- Populate gid_enumeration cache
           |
           v
    Returns: dict[str, list[str]]
```

### Entry Type Additions

```python
class EntryType(str, Enum):
    # ... existing types ...

    # Per PRD-CACHE-OPT-P3: GID enumeration caching
    PROJECT_SECTIONS = "project_sections"   # TTL: 1800s (30 min)
    GID_ENUMERATION = "gid_enumeration"     # TTL: 300s (5 min)
```

## Rationale

### Why Cache at Fetcher Level (Not Builder Level)?

| Factor | Fetcher Level | Builder Level |
|--------|---------------|---------------|
| **Encapsulation** | GID enumeration is fetcher's concern | Leaks implementation detail |
| **Reusability** | Any caller of `fetch_section_task_gids_async()` benefits | Only builder benefits |
| **Surgical Scope** | Changes confined to `parallel_fetch.py` | Spreads changes across files |
| **Pattern** | Mirrors client-level caching (get_async) | Different from existing patterns |

The fetcher owns the GID enumeration operation; it should own its caching.

### Why Constructor Injection (Not Global Registry)?

| Factor | Constructor Injection | Global Registry |
|--------|----------------------|-----------------|
| **Testability** | Easy to mock/replace | Harder to test |
| **Explicitness** | Dependency is visible | Hidden dependency |
| **Consistency** | Matches TaskCacheCoordinator pattern | New pattern |
| **Flexibility** | Different providers per instance | Single global instance |

Constructor injection is the established pattern in this codebase.

### Why Per-Project Granularity (Not Per-Section)?

| Factor | Per-Project | Per-Section |
|--------|-------------|-------------|
| **Cache Entries** | 1 entry per project | N entries per project |
| **Lookup Overhead** | 1 cache read | N cache reads |
| **Invalidation** | Single key to clear | Multiple keys to clear |
| **Memory** | Slightly larger entries | More entries, similar total |
| **Complexity** | Simple | More complex |

Per-project caching provides the same benefit with simpler implementation.

### Why Two-Tier Caching (Not Single Tier)?

The PRD specifies different TTLs for section structure vs task membership:

| Data | Volatility | TTL | Rationale |
|------|------------|-----|-----------|
| Section list | Low | 1800s (30 min) | Sections rarely added/removed |
| GID enumeration | Medium | 300s (5 min) | Tasks move between sections more often |

Two-tier caching allows:
1. Section list to be reused even after GID enumeration expires
2. Appropriate freshness guarantees for each data type
3. Faster partial cache refresh (only re-enumerate GIDs, not sections)

### Trade-off: Section List Redundancy

The GID enumeration cache entry implicitly contains section GIDs (as dict keys). Caching sections separately creates redundancy. However:

1. **PRD Compliance**: PRD specifies both entry types
2. **Independent TTLs**: Section structure can outlive GID mapping
3. **Partial Refresh**: On GID cache miss, section cache can still hit
4. **Future Use**: Other callers of `_list_sections()` can benefit

The redundancy is acceptable given these benefits.

## Alternatives Considered

### Alternative 1: Cache Only GID Enumeration (Single Tier)

**Description**: Cache only the complete `dict[str, list[str]]` result with single TTL.

**Pros**:
- Simpler implementation (one cache entry type)
- No redundant data
- Single cache key to manage

**Cons**:
- Cannot have different TTLs for sections vs GIDs
- Section list refetched even when only GID mapping expired
- Deviates from PRD specification

**Why not chosen**: PRD explicitly specifies two entry types with different TTLs. The optimization is not worth the deviation.

### Alternative 2: Per-Section GID Caching

**Description**: Cache GID list per section: `section:{section_gid}:task_gids`.

```python
# Instead of one entry:
# project:123:gid_enumeration -> {s1: [t1,t2], s2: [t3,t4]}

# N entries:
# section:s1:task_gids -> [t1, t2]
# section:s2:task_gids -> [t3, t4]
```

**Pros**:
- Finer-grained invalidation
- Partial cache hits possible (some sections cached, some not)
- Aligns with section-level operations

**Cons**:
- N cache lookups instead of 1 (higher overhead)
- More complex cache population logic
- Harder to determine "all cached" state
- Section list still needs separate caching

**Why not chosen**: Overhead of N lookups outweighs marginal benefit of finer granularity.

### Alternative 3: Cache at Builder Level

**Description**: Handle GID caching in `ProjectDataFrameBuilder`, similar to task cache coordination.

**Pros**:
- Consistent with Phase 2 task cache pattern
- Builder already has cache provider
- Centralized cache orchestration

**Cons**:
- Leaks fetcher implementation details to builder
- Builder becomes responsible for fetcher's caching
- Other callers of `fetch_section_task_gids_async()` don't benefit
- Violates surgical scope (changes to project.py)

**Why not chosen**: Fetcher should own its caching; keeps changes surgical.

### Alternative 4: New GIDEnumerationCacheCoordinator Class

**Description**: Create a coordinator class similar to `TaskCacheCoordinator`.

**Pros**:
- Consistent pattern with task caching
- Encapsulates all GID cache logic
- Reusable by other components

**Cons**:
- Over-engineered for simple operation
- Only one consumer (ParallelSectionFetcher)
- Adds new file and class to maintain
- Coordinator pattern suited for complex operations

**Why not chosen**: Simple inline caching in fetcher is sufficient.

## Consequences

### Positive

1. **10x Speedup Achieved**: Warm fetch <1s (currently 9.67s)
2. **Zero API Calls on Warm**: Complete cache hit = 0 enumeration API calls
3. **Surgical Scope**: Changes limited to `parallel_fetch.py` and `entry.py`
4. **Pattern Consistency**: Follows graceful degradation pattern from Phase 2
5. **Observable**: Structured logging for cache hits/misses
6. **PRD Compliant**: Both entry types implemented as specified

### Negative

1. **Cache Size**: GID enumeration entries can be large (3,530 GIDs = ~70KB)
2. **Staleness Window**: 5-minute TTL means task moves not immediately reflected
3. **Two Cache Entries**: Section list cached redundantly (also in GID enum keys)
4. **Fetcher Complexity**: ParallelSectionFetcher gains caching responsibility

### Neutral

1. **Constructor Change**: `ParallelSectionFetcher` gains optional `cache_provider` param
2. **Future Extensibility**: Other methods can leverage same cache provider
3. **Test Updates**: Need new tests for cache behavior
4. **Tiered Storage**: When `TieredCacheProvider` is used:
   - `PROJECT_SECTIONS` entries stored in both Redis and S3 tiers (appropriate due to stability)
   - `GID_ENUMERATION` entries stored in Redis; S3 storage is optional (see Integration section)
   - S3 storage implications are minimal (~1KB per project for sections; GID enumeration S3 storage not recommended)

## Compliance

### How This Decision Will Be Enforced

1. **Code Review**: Changes to GID enumeration caching require ADR reference
2. **Unit Tests**: Test cache hit/miss paths for both entry types
3. **Integration Tests**: Validate warm fetch latency <1s
4. **Performance CI**: Benchmark script validates 10x speedup

### Code Location

```python
# /src/autom8_asana/dataframes/builders/parallel_fetch.py

@dataclass
class ParallelSectionFetcher:
    # ... existing fields ...
    cache_provider: CacheProvider | None = None  # NEW: Per ADR-0131

    async def fetch_section_task_gids_async(self) -> dict[str, list[str]]:
        # Per ADR-0131: Check GID enumeration cache first
        if self.cache_provider is not None:
            cached = self._get_cached_gid_enumeration()
            if cached is not None:
                return cached

        # ... existing enumeration logic ...

        # Per ADR-0131: Populate cache before returning
        if self.cache_provider is not None:
            self._cache_gid_enumeration(result)

        return result
```

### Cache Key Formats

| Entry Type | Key Format | Example |
|------------|------------|---------|
| `PROJECT_SECTIONS` | `project:{project_gid}:sections` | `project:1234567890:sections` |
| `GID_ENUMERATION` | `project:{project_gid}:gid_enumeration` | `project:1234567890:gid_enumeration` |

### TTL Configuration

| Entry Type | TTL | Rationale |
|------------|-----|-----------|
| `PROJECT_SECTIONS` | 1800s (30 min) | Section structure stable |
| `GID_ENUMERATION` | 300s (5 min) | Task membership changes more often |

## Integration with Tiered Cache Architecture

Per ADR-0026, the caching infrastructure uses a two-tier architecture:
- **Redis (Hot Tier)**: Fast access, 1-24h TTL, ephemeral
- **S3 (Cold Tier)**: Durable storage, 7-30d TTL, with cache-aside promotion

### Tier Appropriateness for New Entry Types

| Entry Type | Redis (Hot) | S3 (Cold) | Rationale |
|------------|-------------|-----------|-----------|
| `PROJECT_SECTIONS` | Yes | Yes | Section structure is stable (30min TTL). S3 storage appropriate since sections rarely change and rebuilding requires API calls. |
| `GID_ENUMERATION` | Yes | No (recommended) | GID enumeration has short TTL (5min) due to task membership volatility. S3 cold storage provides minimal benefit since data expires quickly and promotion overhead exceeds rebuild cost. |

### S3 Cold Tier Considerations

**PROJECT_SECTIONS**:
- **Appropriate for S3**: Section lists are stable and inexpensive to store (~1KB per project)
- **S3 TTL recommendation**: 24h (longer than Redis 30min, but bounded since sections can change)
- **Promotion behavior**: On S3 hit, promotes to Redis with 1h promotion TTL per ADR-0026

**GID_ENUMERATION**:
- **Not recommended for S3**: The 5-minute TTL indicates high volatility. By the time data is promoted from S3, it may already be stale.
- **S3 storage overhead**: GID enumeration entries are larger (~70KB for 3,530 tasks). Storing in S3 with 5-minute effective TTL wastes storage I/O.
- **Recommendation**: Configure `TieredCacheProvider` to skip S3 writes for `GID_ENUMERATION` entry type, or accept that S3 data will rarely be used before expiration.

### TTL Strategy for Tiered Context

| Entry Type | Redis TTL | S3 TTL | Promotion TTL | Notes |
|------------|-----------|--------|---------------|-------|
| `PROJECT_SECTIONS` | 1800s (30min) | 86400s (24h) | 3600s (1h) | S3 provides durability; longer TTL acceptable |
| `GID_ENUMERATION` | 300s (5min) | N/A or 300s | N/A | S3 storage not recommended due to volatility |

### Implementation Guidance

When `TieredCacheProvider` is in use:

1. **PROJECT_SECTIONS**: Standard two-tier behavior
   - Write-through to both Redis and S3
   - Cache-aside read with promotion
   - Benefit: Survives Redis restarts, reduces API calls on cold start

2. **GID_ENUMERATION**: Redis-only recommended
   - Write to Redis only (or write-through with acceptance of S3 waste)
   - Read from Redis only (S3 fallback unlikely to provide fresh data)
   - Benefit: Simpler, avoids S3 I/O for rapidly-changing data

This can be implemented via entry-type-aware tier routing in `TieredCacheProvider`, or by accepting the inefficiency of standard write-through behavior for simplicity.
