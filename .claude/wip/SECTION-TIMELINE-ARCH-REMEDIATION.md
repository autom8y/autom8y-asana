# Section Timeline Architecture Remediation

**Status**: SEED (ready for deep-dive session)
**Created**: 2026-02-20
**Trigger**: SectionTimeline shipped with forced local architecture; 13 iterative production deployments exposed 4 fundamental cache primitive gaps.

---

## Problem Statement

The SectionTimeline feature works (1.4s response, 3,769 offers, 0 invariant violations) but the implementation is a collection of band-aids around missing cache layer primitives. The architecture should support a **generic entity storyline primitive** -- any entity type with section classifiers should be able to derive timeline data from cached stories without a dedicated warm-up pipeline, in-memory state, or startup-time I/O storms.

The current forced solution:
- 12-15 minute warm-up pipeline at ECS startup
- In-memory `app.state.offer_timelines` dict that dies on every restart
- `max_cache_age_seconds` bolt-on to prevent per-entity API calls on batch reads
- Readiness gates (503 NOT_READY / WARM_FAILED) for the warm-up window
- Bounded concurrency constants to avoid Asana rate limits during warm-up
- Sequential staggering with DataFrame cache warming to avoid thundering herd

## Four Cache Primitive Gaps

Every production incident in the 13-deployment series traces back to one of these:

### Gap 1: No pure-read mode for story cache

`load_stories_incremental()` always makes a live Asana API call -- even on cache "hit" it fetches stories since `last_fetched`. There is no way to say "just give me what's cached, do not touch the network."

The `max_cache_age_seconds` parameter (lines 91-95 of `stories.py`) is the hack: if the cached entry is younger than the threshold, skip the API call. This is a time-based approximation of a pure-read mode.

**File**: `src/autom8_asana/cache/integration/stories.py:35-109`
**The hack**: Lines 91-95 (`max_cache_age_seconds` short-circuit)

### Gap 2: No cached project membership enumeration

`client.tasks.list_async(project=...)` always hits the Asana API. Enumerating ~3,800 tasks in the Business Offers project is uncacheable. The warm-up pipeline calls this twice (once in `warm_story_caches`, once in `build_all_timelines`).

**File**: `src/autom8_asana/services/section_timeline_service.py:359-363` (first call)
**File**: `src/autom8_asana/services/section_timeline_service.py:452-455` (second call)
**EntryType exists but unused**: `EntryType.GID_ENUMERATION` is defined in `entry.py:48` but `tasks.list_async()` does not use it.

### Gap 3: No derived/computed cache entries

SectionTimeline is a pure function of stories (already in S3). But the cache layer only stores raw Asana API responses. There is no concept of a materialized view computed from cached data. The entire warm-up pipeline exists because there is no way to cache the derived SectionTimeline alongside the raw stories it was computed from.

**No file**: This primitive does not exist yet.
**Natural extension point**: `EntryType` enum in `src/autom8_asana/cache/models/entry.py:20-51` -- add `DERIVED_TIMELINE` or a generic `MATERIALIZED_VIEW` type.
**CacheEntry subclass pattern**: `entry.py:354-580` shows `__init_subclass__` auto-registration -- a `DerivedCacheEntry` subclass would fit naturally.

### Gap 4: No batch cache reads

Reading 3,800 individual cache entries from S3 per-request is slow. `CacheProvider.get_batch()` exists in the protocol (`protocols/cache.py:108-124`) but the story cache path (`load_stories_incremental`) operates one task at a time. No composite/aggregate cache entry for "all stories for all tasks in project X."

**Protocol method exists**: `src/autom8_asana/protocols/cache.py:108-124` (`get_batch`)
**Not used by story path**: `load_stories_incremental` in `stories.py` takes a single `task_gid`

## Production Incident History

13 iterative deployments. Key failure modes:

| Deployment | Failure | Root Cause | Fix Applied |
|-----------|---------|------------|-------------|
| DEF-004 | 291 rate_limit_429 events | Semaphore(20) too aggressive for 3,771 offers | Reduced to Semaphore(5) |
| DEF-005 | Warm data invisible to request handlers | `warm_client` vs DI client had separate InMemoryCacheProvider instances | Shared `app.state.cache_provider` |
| DEF-006 | Per-request 3,773 task enumeration exceeded 60s ALB timeout | All I/O happening at request time | Pre-compute at warm-up, serve from memory |
| DEF-007 | Warm-up timeout at 600s | 3,800 offers at Semaphore(5) takes ~12 min | Increased timeout to 1800s |
| DEF-008 | 50% readiness gate never firing | Progress tracked only at completion | Incremental progress counter |
| (early) | 659 rate_limit_429 events | Concurrent warm-up: DataFrame cache + story warm | Sequential staggering |

**Scale characteristics**: ~3,800 offers (growing), 60s ALB timeout, Asana rate limit ~150 req/min per token, S3 per-object latency ~50-100ms.

## Existing Architecture Artifacts

Read these before starting design work:

| Artifact | Path | Relevance |
|----------|------|-----------|
| Cache architecture review | `.claude/wip/q1_arch/ARCH-REVIEW-1-CACHE.md` | Cache layer strengths/weaknesses |
| Cache divergence ADR | `docs/decisions/ADR-0067-*.md` | Why cache tiers differ (intentional) |
| Section timeline TDD | `.claude/wip/TDD-SECTION-TIMELINE.md` | Original design (pre-incidents) |
| Section timeline PRD | `.claude/wip/PRD-SECTION-TIMELINE.md` | Requirements and stakeholder decisions |
| Caching spike | `docs/spikes/SPIKE-section-timeline-caching-strategy.md` | Initial caching strategy |
| Debt ledger | `docs/debt/LEDGER-cleanup-modernization.md` | Related deferred items |

## Key Source Files

### Current band-aid implementation
- `src/autom8_asana/services/section_timeline_service.py` -- warm-up pipeline, pre-computation, day counting
- `src/autom8_asana/api/routes/section_timelines.py` -- endpoint reading `app.state.offer_timelines`
- `src/autom8_asana/api/lifespan.py:251-386` -- warm-up orchestration (background tasks, staggering, failure handling)
- `src/autom8_asana/api/client_pool.py` -- shared cache_provider plumbing

### Cache layer (where gaps live)
- `src/autom8_asana/cache/integration/stories.py` -- `load_stories_incremental()` with `max_cache_age_seconds` hack
- `src/autom8_asana/cache/integration/factory.py` -- provider factory (tiered, redis, memory, null)
- `src/autom8_asana/cache/models/entry.py` -- `EntryType` enum, `CacheEntry` subclass hierarchy
- `src/autom8_asana/protocols/cache.py` -- `CacheProvider` protocol (has `get_batch` already)
- `src/autom8_asana/clients/stories.py` -- `StoriesClient.list_for_task_cached` calling `load_stories_incremental`

### Domain models (keep as-is)
- `src/autom8_asana/models/business/section_timeline.py` -- `SectionInterval`, `SectionTimeline`, `OfferTimelineEntry` (frozen dataclasses, pure logic, no changes needed)
- `src/autom8_asana/models/business/activity.py` -- `SectionClassifier`, `AccountActivity`, `OFFER_CLASSIFIER`, `UNIT_CLASSIFIER`, `CLASSIFIERS` dict

### Extension points
- `SectionClassifier` already supports multiple entity types via `CLASSIFIERS` dict (line 264-267 of `activity.py`)
- `CacheEntry.__init_subclass__` auto-registration (line 110-124 of `entry.py`) supports adding new entry types
- `CacheProvider.get_batch()` protocol method exists but is unused by the story path

## Architectural Questions

1. **Pure-read mode**: Should `load_stories_incremental()` gain a `read_only=True` parameter that returns cached data or None without an API call? Or should this be a separate function (`read_cached_stories`) to preserve the existing incremental contract?

2. **Derived cache entries**: Should derived data (SectionTimeline computed from stories) be a new `EntryType.DERIVED` with a `DerivedCacheEntry` subclass? Or should it use the existing `EntryType.DATAFRAME` / `DataFrameMetaCacheEntry` pattern since it is project-scoped?

3. **Project membership caching**: `EntryType.GID_ENUMERATION` already exists. Should `tasks.list_async(project=...)` check cache first with a configurable TTL (e.g., 5 min)? What invalidation strategy -- TTL only, or event-driven via webhook?

4. **Batch story reads**: Should a new `load_stories_batch(task_gids, cache)` function use `CacheProvider.get_batch()` to read all stories in one round-trip? Or should derived entries eliminate the need for batch reads by pre-computing at cache-write time?

5. **Generic vs. specific**: The user wants a generic "entity storyline" primitive. `SectionClassifier` already maps entity types. Should the timeline builder be parameterized by `(project_gid, classifier)` rather than hardcoded to offers? What is the interface for `EntityStoryline[T]`?

6. **Migration path**: What can be removed from `lifespan.py` once clean primitives exist? Target: zero warm-up pipeline, zero `app.state` for timelines, endpoint reads directly from cache layer.

## Phased Work Plan

### Phase 1: Analysis (~0.5 day)

**Deliverables**: Gap analysis document confirming extension points.

- Map `CacheProvider` implementations to verify `get_batch` works end-to-end (Redis MGET, S3 multi-get)
- Trace `load_stories_incremental` call chain to identify all callers and their pure-read needs
- Audit `EntryType.GID_ENUMERATION` -- is it wired anywhere? What TTL is configured?
- Measure: how many S3 reads does a cold-start timeline build require? What is the aggregate latency?

### Phase 2: Design (~1 day)

**Deliverables**: 2-3 ADRs for cache primitive extensions.

- ADR: Pure-read mode for story cache (read_only param vs. separate function)
- ADR: Derived cache entries (new EntryType, invalidation strategy, staleness model)
- ADR: Project membership caching (GID_ENUMERATION activation, TTL, invalidation)
- Optional ADR: Generic entity storyline primitive (parameterized builder)

### Phase 3: Implementation (~2 days)

**Deliverables**: Working cache primitives, endpoint migrated off app.state.

- Implement pure-read story cache function
- Implement batch story reads via `get_batch`
- Implement derived timeline cache entry (compute on story-cache write or on first read)
- Wire GID_ENUMERATION into `tasks.list_async(project=...)` for membership caching
- Migrate `section_timelines.py` endpoint to read from cache layer instead of `app.state`

### Phase 4: Cleanup (~0.5 day)

**Deliverables**: Warm-up pipeline removed, lifespan simplified.

- Remove `warm_story_caches()` and `build_all_timelines()` from `section_timeline_service.py`
- Remove `_warm_section_timeline_stories()` from `lifespan.py` (lines 251-386)
- Remove `app.state.offer_timelines`, `timeline_warm_count`, `timeline_total`, `timeline_warm_failed`
- Remove `_WARM_CONCURRENCY`, `_BUILD_CONCURRENCY`, `_WARM_TIMEOUT_SECONDS` constants
- Remove readiness gate logic from `section_timelines.py` (lines 55-87)
- Remove `max_cache_age_seconds` parameter from `load_stories_incremental()` if no longer needed

## Anti-Patterns (Do NOT)

- **Do NOT re-introduce a warm-up pipeline.** The goal is cache primitives that make warm-up unnecessary.
- **Do NOT add more app.state.** Derived data belongs in the cache layer, not in process memory.
- **Do NOT add more `max_cache_age_seconds` hacks.** A proper pure-read mode replaces this.
- **Do NOT hardcode to offers.** The solution should work for any entity type with a `SectionClassifier`.
- **Do NOT break the existing story cache contract.** `load_stories_incremental()` is used by other callers for DataFrame computation -- the incremental-with-API-call behavior must remain available.
- **Do NOT ignore the Lambda cache warmer.** It already runs periodically for DataFrames -- explore whether it can also trigger derived timeline materialization.

## Success Criteria

- `GET /api/v1/offers/section-timelines` responds in <2s without a warm-up pipeline
- No `app.state` for timeline data
- The same primitive can produce timelines for Units (using `UNIT_CLASSIFIER`) with zero new code beyond configuration
- Zero additional Asana API calls at request time for cached entities
- Graceful degradation when cache is cold (stale-while-revalidate or on-demand computation)
