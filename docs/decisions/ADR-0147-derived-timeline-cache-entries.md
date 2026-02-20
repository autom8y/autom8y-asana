# ADR-0147: Derived Timeline Cache Entries

## Status

Proposed

## Context

The SectionTimeline feature computes timeline data by:
1. Reading raw stories from the cache layer (per-entity `EntryType.STORIES` entries)
2. Filtering, sorting, and building `SectionInterval` lists
3. Aggregating into `SectionTimeline` objects
4. Computing day counts for a query period

This computation touches ~3,800 entities and takes 2-4 seconds. Currently, the result is stored in `app.state.offer_timelines` (in-memory, dies on restart) after a 12-15 minute warm-up pipeline. The cache layer has no concept of storing computed/derived data -- only raw Asana API responses.

The CacheEntry hierarchy (`src/autom8_asana/cache/models/entry.py`) supports `__init_subclass__` auto-registration (lines 110-124) and has 16 existing entry types. Adding a new type is a proven extension pattern used by `EntityCacheEntry`, `RelationshipCacheEntry`, `DataFrameMetaCacheEntry`, and `DetectionCacheEntry`.

### Constraints

- Derived entries must use the existing `CacheProvider` protocol (no new provider methods)
- `__init_subclass__` registration must work for the new type
- JSON serialization (consistent with existing entries -- no Pickle, no Protobuf)
- The entry must carry provenance metadata (when computed, from how many entities, etc.) for observability
- Invalidation must be eventual-consistent (TTL-based acceptable)

### Ambiguities Resolved

- **AMB-1 (Derived cache invalidation)**: TTL-only vs. story-write-triggered recomputation
- **AMB-3 (Concurrent computation guard)**: asyncio.Lock vs. distributed lock
- **AMB-6 (Serialization format)**: JSON dict vs. Pickle vs. custom

## Decision

### 1. New `EntryType.DERIVED_TIMELINE` enum member

Add to the `EntryType` enum:

```python
DERIVED_TIMELINE = "derived_timeline"  # TTL: 300s (5 min)
```

### 2. New `DerivedTimelineCacheEntry` subclass

A frozen dataclass subclass of `CacheEntry` registered via `entry_types=(EntryType.DERIVED_TIMELINE,)`. Carries observability fields: `classifier_name`, `source_entity_count`, `source_cache_hits`, `source_cache_misses`, `computation_duration_ms`.

### 3. TTL-only invalidation (5-minute TTL)

Derived entries expire after 5 minutes. There is no invalidation triggered by story cache writes. When a request arrives after TTL expiry, the entry is recomputed from current cached stories.

### 4. In-process `asyncio.Lock` for concurrent computation guard

A `defaultdict(asyncio.Lock)` keyed by `(project_gid, classifier_name)` prevents multiple concurrent requests from computing the same derived entry simultaneously.

### 5. JSON dict serialization

`SectionTimeline` objects are serialized to JSON dicts with `AccountActivity.value` strings for classification and ISO 8601 strings for timestamps.

### 6. Cache key format: `timeline:{project_gid}:{classifier_name}`

Examples: `timeline:1143843662099250:offer`, `timeline:1234567890000000:unit`.

## Alternatives Considered

### AMB-1: Story-write-triggered invalidation

- Pros: Fresher derived data (invalidated within seconds of story update)
- Cons: Requires coupling `load_stories_incremental()` to the derived entry lifecycle. Every story cache write would need to check whether the task belongs to a project with derived entries and invalidate the appropriate derived key. This adds latency to every story write path, violates layer separation (raw cache operations should not know about derived computations), and is architecturally fragile (new derived types would each need their own invalidation hooks).
- Decision: Rejected. Section moves happen at most a few times per day per entity. 5-minute staleness is acceptable for day-count aggregation. The cost/complexity of write-triggered invalidation is not justified.

### AMB-3: Distributed lock (Redis SETNX)

- Pros: Prevents cross-container duplicate computation
- Cons: Adds Redis dependency for lock management. Lock expiry/deadlock handling adds complexity. Each ECS container already serves its own traffic -- duplicate computation across containers produces the same result (idempotent), so the "wasted work" is bounded (at most one extra computation per container per TTL cycle). A distributed lock is over-engineering for this use case.
- Decision: Rejected. In-process `asyncio.Lock` is sufficient. The thundering herd problem is within a single container (multiple concurrent requests to the same endpoint), not across containers.

### AMB-6: Pickle serialization

- Pros: Zero-effort serialization of Python objects, faster than JSON
- Cons: Not portable across Python versions. Security risk (arbitrary code execution on deserialize). Inconsistent with every other cache entry in the system (all use JSON dicts). Cannot be inspected in Redis CLI for debugging.
- Decision: Rejected. JSON dict is consistent with existing patterns and enables debugging via Redis CLI inspection.

### AMB-6: Storing `OfferTimelineEntry` (with day counts) instead of `SectionTimeline`

- Pros: Endpoint can serve directly without day-count computation
- Cons: Day counts are period-specific. Caching `OfferTimelineEntry(period_start=X, period_end=Y)` only helps requests with the same period. `SectionTimeline` is period-independent and can serve any period query. One cached `SectionTimeline` serves all period combinations.
- Decision: Rejected. Cache the period-independent `SectionTimeline`, compute day counts at request time (pure CPU, <100ms for 3,800 entries).

## Rationale

1. **TTL-only invalidation** is the simplest correct approach. The use case (day counting for reconciliation) tolerates 5-minute staleness. Story updates are rare (section moves happen a few times per day). The complexity cost of write-triggered invalidation (coupling across cache layers) vastly outweighs the marginal freshness benefit.

2. **In-process asyncio.Lock** matches the deployment model (independent ECS containers). Cross-container duplicate computation is idempotent and bounded. The lock prevents the actual problem: 5 concurrent requests to the same endpoint all triggering 2-4 second computations simultaneously.

3. **JSON dict serialization** is consistent, debuggable, and portable. `SectionTimeline` is a simple frozen dataclass with primitive fields -- JSON serialization is trivial.

4. **`SectionTimeline` over `OfferTimelineEntry`** makes the derived entry period-independent. One cache entry serves all period queries, maximizing cache hit rate.

## Consequences

### Positive

- Derived timeline data persists across ECS restarts (in Redis/S3, not in-memory `app.state`)
- Any entity type with a `SectionClassifier` can have derived timelines via `(project_gid, classifier_name)` parameterization
- Observability fields on the entry enable monitoring of computation cost and cache hit rates
- `__init_subclass__` auto-registration means `CacheEntry.from_dict()` dispatches to `DerivedTimelineCacheEntry` automatically
- 5-minute TTL means the worst case is a 2-4 second computation every 5 minutes -- amortized over all requests in that window

### Negative

- One new `EntryType` member (17th, from 16) -- minimal complexity increase
- JSON serialization of 3,800 timelines is ~760KB per cache entry -- within Redis limits but non-trivial
- TTL-only invalidation means data can be up to 5 minutes stale after a section move -- acceptable for the use case but would not work for real-time requirements

### Neutral

- The `DerivedTimelineCacheEntry` follows the exact same pattern as `DetectionCacheEntry` and `DataFrameMetaCacheEntry` -- no new architectural concepts introduced
- The `asyncio.Lock` dict will grow by one entry per unique (project, classifier) pair -- in practice, 2-3 entries (one per entity type)
