# Analysis: Story Cache Population Gap

**Date**: 2026-02-20
**Author**: Architect
**Status**: CONCEPTUAL ANALYSIS (no ADR/TDD)
**Context**: Post-remediation gap in TDD-SECTION-TIMELINE-REMEDIATION-001

---

## Part 1: Cache Architecture Mental Model

### 1.1 The Two Cache Systems

The architecture contains two independent cache systems serving fundamentally different use cases (per ADR-0067, 12 of 14 dimensions intentionally divergent):

| System | Cache Unit | Hot Tier | Cold Tier | Key Space | Primary Consumer |
|--------|-----------|----------|-----------|-----------|-----------------|
| **Entity Cache** | `dict[str, Any]` (raw API responses) | Redis (shared across ECS replicas) | S3 JSON | `{type}:{gid}` per-entity | Query engine, entity resolution, request handlers |
| **DataFrame Cache** | `pl.DataFrame` (columnar tables) | In-process `OrderedDict` (LRU) | S3 Parquet | `{type}:{project_gid}` per-project | Query router, analytics, reconciliation |

### 1.2 Entity Cache: Entry Types and Flows

The entity cache stores 17 distinct `EntryType` members. Relevant to this analysis:

| EntryType | Write Path | Read Path | TTL |
|-----------|-----------|-----------|-----|
| `TASK` | `UnifiedTaskStore` (6-step: API -> process -> cache) | Request handlers, resolution strategies | 300s (default, entity-specific overrides) |
| `STORIES` | `load_stories_incremental()` only | `read_cached_stories()`, `read_stories_batch()`, `StoriesClient.list_for_task_cached()` | **300s (5 min, hardcoded default from CacheEntry)** |
| `SUBTASKS` | `UnifiedTaskStore` | Resolution strategies | 300s |
| `DETECTION` | Detection facade | Resolution strategies | 3600s |
| `DERIVED_TIMELINE` | `store_derived_timelines()` | `get_cached_timelines()` | 300s |
| `PROJECT_SECTIONS` | Section enumeration | Resolution strategies | 1800s |
| `GID_ENUMERATION` | GID enumeration | Resolution strategies | 300s |

### 1.3 Story Cache: Sole Write Path

There is exactly ONE code path that writes story cache entries:

```
StoriesClient.list_for_task_cached()      [clients/stories.py:342]
    |
    v
load_stories_incremental()                [cache/integration/stories.py:102]
    |
    +-- cache miss -> API fetch -> _create_stories_entry() -> cache.set_versioned()
    +-- cache hit  -> API incremental fetch -> merge -> _create_stories_entry() -> cache.set_versioned()
    +-- cache hit + max_cache_age_seconds -> return cached (no write)
```

`_create_stories_entry()` creates a `CacheEntry` with `EntryType.STORIES` and the default TTL of 300 seconds (5 minutes).

### 1.4 Story Cache: Read Paths

Two consumers read story cache entries:

1. **`read_cached_stories(task_gid, cache)`** -- single task, pure read, returns `list[dict]` or None
2. **`read_stories_batch(task_gids, cache)`** -- multi-task via `get_batch()`, pure read, returns `dict[gid, list[dict] | None]`

Both are pure-read operations. Neither writes to the cache. Both were introduced by the remediation as "Gap 1" and "Gap 4" primitives.

### 1.5 Lambda Warmer: DataFrames Only

The Lambda warmer (`lambda_handlers/cache_warmer.py`) operates exclusively on the DataFrame cache:

```
CacheWarmer.warm_entity_async()           [cache/dataframe/warmer.py:419]
    |
    v
_warm_entity_type_async()                 [warmer.py:297]
    |
    v
strategy._build_dataframe()              -> DataFrame
    |
    v
cache.put_async()                         -> DataFrameCache (Memory + S3 Parquet)
```

It warms entity types: unit, business, offer, contact, asset_edit, asset_edit_holder, unit_holder. It produces **DataFrames**, not story cache entries. It has zero interaction with `EntryType.STORIES`.

### 1.6 ECS Lifespan Startup

After the remediation, the ECS lifespan (`api/lifespan.py`) runs:

1. Shared CacheProvider initialization
2. ClientPool initialization
3. Entity project discovery
4. DataFrameCache initialization
5. Schema provider registration
6. MutationInvalidator initialization
7. EntityWriteRegistry initialization
8. Workflow config registration
9. **Background task**: `_preload_dataframe_cache_progressive()` -- progressive DataFrame cache warming from S3/API

No story cache warming occurs at startup. The lifespan comment at line 252-255 explicitly states:

> "Per TDD-SECTION-TIMELINE-REMEDIATION: Section timeline warm-up pipeline REMOVED. Timeline data is now computed on first request and served from derived cache on subsequent requests. No app.state keys for timeline data, no startup-time story cache warming, no readiness gates."

### 1.7 Cache Tier Interaction for Stories

Story entries follow the standard entity cache 6-step pattern:

```
write:  load_stories_incremental()
            -> cache.set_versioned(task_gid, entry)
            -> TieredCacheProvider:
                -> Redis (hot): SET with TTL=300s
                -> S3 (cold): PUT (write-through)

read:   read_stories_batch(task_gids, cache)
            -> cache.get_batch(chunk, EntryType.STORIES)
            -> TieredCacheProvider:
                -> Redis pipeline MGET (hot)
                -> S3 fallback for misses (cold)
                -> promote cold hits to hot
```

**Critical detail**: S3 cold tier entries do NOT expire via TTL. They persist until explicitly deleted or overwritten. However, the TieredCacheProvider promotes S3 entries to Redis with `promotion_ttl = 3600` (1 hour). So even S3-persisted stories get served, but only if: (a) the S3 entry exists, AND (b) the S3 provider is configured and healthy.

---

## Part 2: The Gap Analysis

### 2.1 Which Entry Types Are Orphaned?

**`EntryType.STORIES` is the only orphaned entry type.** It has two active readers (`read_cached_stories`, `read_stories_batch`) but the sole writer (`load_stories_incremental` via `StoriesClient.list_for_task_cached`) is no longer called by any active code path.

Before the remediation, stories were populated by:
- The warm-up pipeline (`warm_story_caches()`) which called `list_for_task_cached_async()` for each of ~3,800 offers
- Individual `build_timeline_for_offer()` calls which also called `list_for_task_cached_async()`

After the remediation:
- `warm_story_caches()` was removed (Phase 5 cleanup)
- `build_timeline_for_offer()` still exists but is only called from the endpoint path for individual offer timeline queries, NOT from `get_or_compute_timelines()` (the batch path)
- `get_or_compute_timelines()` uses `read_stories_batch()` which is pure-read
- Nothing actively calls `list_for_task_cached_async()` in a bulk context

### 2.2 Decay Timeline

Story cache entries have a **5-minute TTL** in Redis (the default `CacheEntry.ttl = 300`).

- **T+0** (deployment): Existing story entries in Redis are live (populated by previous warm-up pipeline)
- **T+5m**: All Redis story entries expire. Redis returns None for all story reads.
- **T+5m onward**: `read_stories_batch()` returns `{gid: None}` for every task.

**S3 cold tier complication**: If S3 is enabled (`ASANA_CACHE_S3_ENABLED=true`), story entries written by the previous warm-up pipeline also exist in S3 with no TTL expiration. The TieredCacheProvider will:
1. Miss in Redis (expired)
2. Find entry in S3 (never expires)
3. Promote to Redis with `promotion_ttl = 3600` (1 hour)
4. Return the S3 entry

This means S3 provides a **one-time safety net**: the first `get_batch()` after Redis expiry will find stories in S3 and promote them to Redis for 1 hour. But those promoted entries will expire after 1 hour, and S3 entries will never be refreshed. Over time, the S3 entries become increasingly stale (stories created after the last warm-up run will be missing). New offers added after the last warm-up will have no story entries at all.

**Effective decay timeline**:

| Time After Deploy | Redis State | S3 State | `read_stories_batch` Result |
|------------------|-------------|----------|---------------------------|
| T+0 to T+5m | Live (from prior warm-up) | Live (from prior warm-up) | Full cache hits |
| T+5m to T+65m | Promoted from S3 (1h TTL) | Stale but present | Full hits, but stale |
| T+65m onward | Expired | Stale, never refreshed | S3 promotion on each batch read; data increasingly stale |
| After S3 cleanup/rotation | Expired | Gone | All misses, zero story data |

Without S3, the decay is a hard cliff at T+5m.

### 2.3 Blast Radius

**What depends on story caches?**

| Consumer | Impact of Empty Story Cache | Severity |
|----------|---------------------------|----------|
| `get_or_compute_timelines()` | All tasks return `cache_misses++`. Only imputed intervals are produced (based on current section position). Historical section movement data is lost. Day counts are inaccurate. | **HIGH** -- This is the primary consumer and the timeline feature is non-functional without stories. |
| `build_timeline_for_offer()` | Uses `list_for_task_cached_async()` which calls `load_stories_incremental()` and IS self-healing (fetches from API on cache miss). Not affected -- but this is the per-offer path, not used by the batch endpoint. | LOW -- Self-healing, but not used by the main code path. |
| Other features | No other features currently read from `EntryType.STORIES` cache. | NONE |

The blast radius is concentrated: the section timeline batch endpoint (`/api/v1/offers/section-timelines`) degrades to imputed-only results, losing all historical section movement data.

### 2.4 Regression or Latent?

**This is a regression introduced by the remediation.** Specifically:

1. The TDD (Section 8.1, EC-2) explicitly addresses the "both caches cold" scenario and treats it as an acceptable degraded response: "Enumerate tasks (~2s). Batch-read returns all misses. Return empty/partial results."

2. ADR-0148 states: "The Lambda warmer continues to run on its existing schedule, populating story caches. This is unchanged."

3. However, **this statement is incorrect**. The Lambda warmer has NEVER populated story caches. It populates DataFrames. The warm-up pipeline (now removed) was the only bulk story cache writer. The ADR contains a factual error about the Lambda warmer's scope.

4. The TDD's "compute-on-read amortization" rationale (Section 2 of ADR-0148) states: "The Lambda warmer ensures story caches are populated, so the derived computation is always fast (batch-reading from Redis, not fetching from Asana API)." This is the incorrect assumption that created the gap.

**Root cause**: The remediation's design assumed story caches are a Lambda warmer responsibility. In reality, story caches were exclusively populated by the warm-up pipeline that was removed. The ADR's factual error about the Lambda warmer's scope was not caught during review.

---

## Part 3: Strategy Conceptualization

### 3.1 Framing: Where Should Story Warming Live?

To answer this, consider the taxonomy of cache population patterns in the system:

| Pattern | Example | Trigger | Scope |
|---------|---------|---------|-------|
| **Request-driven (cache-aside)** | `UnifiedTaskStore` 6-step | API request | Per-entity |
| **Background warming (Lambda)** | DataFrame CacheWarmer | Cron schedule | Per-project |
| **Startup preload** | `_preload_dataframe_cache_progressive` | ECS container start | All projects |
| **Write-through** | `TieredCacheProvider.set_versioned` | Any write operation | Per-entry |
| **Mutation-triggered** | `MutationInvalidator` | SDK mutation | Per-entity invalidation (not population) |

Stories do not fit cleanly into any existing pattern:
- They are too numerous for request-driven population (3,800 tasks, each needing API calls)
- They are not DataFrames, so they do not belong in the DataFrame warmer
- They are task-scoped raw data, not project-scoped aggregates
- They change slowly (section moves are infrequent) but need to be present for analytics

### 3.2 Strategy A: Extend Lambda Warmer with Story Warming Phase

**Concept**: Add a story warming phase to the existing Lambda cache warmer, running after DataFrame warming completes. For each project, enumerate tasks and call `load_stories_incremental()` for each task.

**Assessment**:

- **Alignment**: The Lambda warmer already has entity-type iteration, checkpoint resume, timeout detection, and self-continuation. Adding a story phase extends an existing pattern.
- **Complexity**: Medium. Requires adding a new warming phase to `_warm_cache_async()`, plus a story-specific warmer function. The checkpoint system needs to track per-entity-type progress for stories (3,800 individual API calls is a different granularity than 7 DataFrame builds).
- **Operations**: Lambda has a 15-minute timeout. Story warming for 3,800 offers at 5 concurrency takes ~12 minutes. This consumes most of a Lambda invocation. Self-continuation may be needed. Rate limit pressure with DataFrame warming adds risk.
- **Rate limits**: This is the critical problem. DataFrame warming already uses significant API budget. Adding 3,800 story API calls to the same Lambda invocation window creates the same rate limit pressure that caused DEF-004 (291 rate_limit_429 events). The Lambda would need staggering or a separate invocation.
- **Scope**: Solves the timeline gap specifically, but story warming is inherently feature-coupled (which tasks to warm stories for depends on which projects need timeline data). This moves story warming from ECS startup to Lambda, but the coupling remains.
- **Effort**: ~2-3 days (warmer extension, checkpoint integration, rate limit coordination, testing)

**Verdict**: Operationally risky. Reintroduces the rate limit problem in a different runtime context.

### 3.3 Strategy B: Separate Story Warming Lambda

**Concept**: A dedicated Lambda function for story cache warming, invoked on its own cron schedule (offset from DataFrame warmer to avoid rate limit overlap). Enumerates tasks per project and calls `load_stories_incremental()` for each.

**Assessment**:

- **Alignment**: Lambda is the established off-band warming mechanism. A separate function avoids coupling to DataFrame warmer lifecycle. Follows the "single responsibility" pattern.
- **Complexity**: Medium-high. New Lambda handler, CloudFormation/Terraform changes for the new function, separate cron schedule, separate checkpoint management, separate CloudWatch metrics. Significant infrastructure overhead for what is essentially "call the same API in a loop."
- **Operations**: Separate cron means story TTL can be tuned independently. Offset scheduling avoids rate limit collision. But monitoring, alerting, and operational overhead doubles.
- **Rate limits**: Can be scheduled in a dedicated rate limit budget window (e.g., stories warm at T+15m, DataFrames at T+0m). Still consumes ~3,800 API calls per invocation.
- **Scope**: Still feature-coupled (must know which projects to warm stories for). Does not improve the broader cache architecture -- it is a point solution for the story gap.
- **Effort**: ~3-4 days (new Lambda handler, infrastructure, testing, monitoring)

**Verdict**: Clean separation but high operational overhead. A whole new Lambda function is disproportionate to the problem.

### 3.4 Strategy C: Self-Healing Compute-on-Read (Fetch on Miss)

**Concept**: When `get_or_compute_timelines()` encounters a story cache miss during batch read (step 4), it falls back to fetching stories via API and writing them to cache as a side effect. The first request pays the full cost; subsequent requests serve from cache.

**Assessment**:

- **Alignment**: This is the purest cache-aside pattern -- read through with write-on-miss. It is how the entity cache already works for tasks (the 6-step pattern). It extends that pattern to stories in the timeline computation context.
- **Complexity**: Low-medium. The infrastructure already exists: `load_stories_incremental()` performs the fetch-and-cache operation. The change is to have `get_or_compute_timelines()` call it for cache misses instead of just imputing. Bounded concurrency (Semaphore) prevents API storm.
- **Operations**: First request after total cache cold start takes longer (bounded by concurrency and rate limits). But this is a one-time cost per 5-minute TTL window. The cold-start latency concern was already acknowledged in TDD Section 8.1 (EC-1: <5s for derived cold). With API fetching, this would be more like 30-120s for a full cold start. That exceeds the 60s ALB timeout.
- **Rate limits**: 3,800 API calls during a single request is the exact problem the warm-up pipeline had. Even with bounded concurrency, a single request cannot absorb this within the ALB timeout.
- **Scope**: Generic cache-layer concern -- any consumer that encounters a story miss can trigger population. Not coupled to timelines specifically.
- **Effort**: ~1-2 days (add fallback fetch to the computation loop, bounded concurrency, timeout handling)
- **Critical flaw**: The ALB 60-second timeout makes full cold-start self-healing impossible in a single request. 3,800 API calls at Semaphore(5) takes ~12 minutes.

**Verdict**: Cannot work for full cold start due to ALB timeout. Could work as a partial solution for incremental cache misses (new offers added since last warm), but not as the sole population mechanism.

### 3.5 Strategy D: Hybrid -- Lambda Story Warmer + Self-Healing Backfill

**Concept**: Two-part approach:
1. **Lambda story warmer**: Extends the existing Lambda warmer (or runs as a phase within it) to bulk-populate story caches on a schedule.
2. **Self-healing backfill**: `get_or_compute_timelines()` identifies cache misses and, for a bounded number of misses, fetches stories inline. If misses exceed a threshold, it returns partial results and logs a warning (indicating the Lambda warmer has not run recently enough).

**Assessment**:

- **Alignment**: Combines background warming (Lambda responsibility) with request-time self-healing (cache-aside). This mirrors the DataFrame cache's SWR pattern conceptually: serve what you have, refresh in the background. The Lambda handles bulk population; the request path handles stragglers.
- **Complexity**: Medium. Lambda extension for story warming + bounded inline fetching in the computation path. The bounded fetch limit prevents the ALB timeout issue from Strategy C.
- **Operations**: Lambda populates the majority of stories. Request-time fetching handles edge cases (new offers, Lambda failures, TTL gaps). The bounded threshold (e.g., max 50 inline fetches) keeps request latency predictable.
- **Rate limits**: Lambda warming runs in its own budget window. Inline fetching is bounded and infrequent (only for misses that Lambda did not cover).
- **Scope**: Lambda warming is project-scoped (knows which projects to warm). Inline backfill is generic (any consumer can trigger it). The combination is principled: warm proactively, self-heal reactively.
- **Effort**: ~3-4 days total (Lambda phase ~2d, inline backfill ~1-2d)

**Verdict**: Robust and architecturally sound, but the most complex option.

### 3.6 Strategy E: Piggyback on DataFrame Warmer -- Story Pre-Fetch During Build

**Concept**: During DataFrame warming (`CacheWarmer._warm_entity_type_async`), the resolution strategy already fetches all tasks for a project to build the DataFrame. After building the DataFrame, iterate the fetched task GIDs and call `load_stories_incremental()` for each to populate the story cache as a side effect of DataFrame warming.

**Assessment**:

- **Alignment**: This is the highest-alignment strategy. The DataFrame warmer already iterates every task in every project. Adding story population to this existing iteration adds no new infrastructure and reuses the existing warming lifecycle (checkpoint resume, timeout detection, self-continuation). The task GIDs are already in memory from the DataFrame build.
- **Complexity**: Low. The DataFrame warmer already has the task GID list. Adding `load_stories_incremental()` calls in a bounded-concurrency loop after `put_async()` is a small code change. The existing checkpoint mechanism already tracks per-entity-type progress. Story warming for a project can be checkpointed at the task GID level.
- **Operations**: Story warming inherits the Lambda's operational properties: CloudWatch metrics, timeout detection, self-continuation. No new infrastructure. Rate limit pressure increases (story API calls added to DataFrame build window), but stories can be fetched with lower concurrency (Semaphore(3) instead of the build's Semaphore(5)).
- **Rate limits**: The key concern. DataFrame warming + story warming in the same Lambda invocation window doubles the API call budget. The Lambda already uses ~70% of its timeout for DataFrame builds. Adding 3,800 story fetches would require self-continuation (the Lambda saves a checkpoint after DataFrames complete, self-invokes for stories). This is a supported pattern (self-continuation already exists).
- **Scope**: Feature-neutral from the cache layer's perspective. Stories are populated as part of the standard warming lifecycle, available to any consumer. Not coupled to timelines.
- **Interaction with derived cache**: If stories are fresh (populated by Lambda on schedule), the derived timeline cache's TTL can be set more aggressively (longer TTL, since underlying data is reliable). The 5-minute derived TTL was conservative because story freshness was uncertain.
- **Effort**: ~1.5-2 days (add story warming phase to `_warm_entity_type_async` or `_warm_cache_async`, bounded concurrency, testing)

**Verdict**: Strongest alignment with existing architecture. Lowest new infrastructure. Inherits operational maturity of the DataFrame warmer.

### 3.7 Strategy F: Background Story Refresh as ECS Periodic Task

**Concept**: APScheduler (already used for dev-mode cache warming) runs a periodic story refresh task in the ECS container. Every N minutes, it iterates known task GIDs and calls `load_stories_incremental()` for those with expired or missing story cache entries.

**Assessment**:

- **Alignment**: APScheduler is already in the codebase for dev-mode warming. Extending it to production story warming adds a new lifecycle concern to ECS (background tasks alongside request handling).
- **Complexity**: Medium. APScheduler integration, task scheduling, rate limit coordination with request handling.
- **Operations**: ECS containers are ephemeral (restart on deploy). A background task competes for CPU/memory with request handling. Rate limit budget is shared with request-time API calls.
- **Rate limits**: Story warming in ECS shares the rate limit budget with all request-time API calls. Contention risk is high.
- **Scope**: Per-container isolation means each ECS task warms independently. With N replicas, this causes N-fold API call amplification (each replica warms the same stories). Redis cache sharing mitigates this (only the first replica to warm populates Redis for all), but the API calls still happen.
- **Effort**: ~2-3 days

**Verdict**: Multi-replica amplification and rate limit contention make this a poor fit for production. Acceptable for dev/staging only.

### 3.8 Strategy G: Event-Driven Story Population (Webhook)

**Concept**: Asana webhooks notify the system when stories are created on tasks. On receiving a story-creation webhook, fetch and cache the story for that task.

**Assessment**:

- **Alignment**: Event-driven is the most architecturally pure approach -- data flows into the cache exactly when it changes. No polling, no bulk warming, no stale data.
- **Complexity**: High. Requires: (a) Asana webhook registration for story events, (b) a webhook handler endpoint, (c) webhook signature verification, (d) idempotency handling, (e) backfill strategy for historical data not covered by webhooks.
- **Operations**: Webhook delivery is not guaranteed (Asana may drop webhooks under load). Requires a backfill mechanism for the initial population and for webhook gaps.
- **Rate limits**: Near-zero -- cache is populated by push, not pull. Only the backfill mechanism uses API calls.
- **Scope**: Solves the freshness problem entirely (stories are cached as they are created). But the webhook infrastructure is a significant investment for a single cache entry type.
- **Effort**: ~5-7 days (webhook registration, handler, verification, backfill, monitoring)

**Verdict**: Architecturally ideal but disproportionate investment for the current problem. Better suited as a future platform capability, not a targeted gap fix.

---

## Part 4: Recommendation (Ranked)

### Evaluation Matrix

| # | Strategy | Arch. Soundness | Op. Robustness | Simplicity | Time | Overall |
|---|----------|----------------|----------------|------------|------|---------|
| E | Piggyback on DataFrame Warmer | **A** | **A-** | **A** | **1.5-2d** | **1st** |
| D | Hybrid Lambda + Self-Healing | A | A | B | 3-4d | 2nd |
| B | Separate Story Lambda | B+ | B+ | C | 3-4d | 3rd |
| A | Extend Lambda Warmer (separate phase) | B+ | B | B+ | 2-3d | 4th |
| C | Self-Healing Compute-on-Read | A- | C (ALB timeout) | A | 1-2d | 5th |
| F | ECS Periodic Task | C | C | B | 2-3d | 6th |
| G | Event-Driven Webhook | A+ | B | D | 5-7d | 7th |

### Primary Recommendation: Strategy E -- Piggyback on DataFrame Warmer

**Why it wins on every axis**:

1. **Architectural soundness**: Stories are populated during the same warming lifecycle as DataFrames. No new infrastructure, no new cron schedules, no new Lambda functions. The existing CacheWarmer checkpoint/resume/self-continuation handles the operational complexity. Story warming is a cache-layer concern (warming entity data alongside other entity data), not a feature concern.

2. **Operational robustness**: Inherits all of the Lambda warmer's operational properties: CloudWatch metrics, timeout detection, checkpoint resume, self-continuation. If story warming fails or times out, the Lambda saves a checkpoint and self-continues exactly as it does for DataFrames.

3. **Implementation simplicity**: The task GIDs are already enumerated during DataFrame building. Adding `load_stories_incremental()` calls in a bounded-concurrency loop is a minimal code change. The existing infrastructure handles everything else.

4. **Time to implement**: 1.5-2 days. The smallest implementation surface of any strategy that actually solves the problem for bulk population.

### Implementation Sketch (Strategy E)

The cleanest integration point is as a new warming phase in `_warm_cache_async()`, executed after all DataFrame entity types complete:

```
_warm_cache_async()
    |
    +-- For each entity_type in priority:
    |       warm_entity_async()     # DataFrames (existing)
    |
    +-- Checkpoint: DataFrames complete
    |
    +-- Story warming phase (NEW):
    |       For each project with timeline-eligible entity types:
    |           enumerate task GIDs (from cached DataFrame or API)
    |           For each task_gid (bounded concurrency Semaphore(3)):
    |               load_stories_incremental(task_gid, cache, fetcher)
    |           Checkpoint per-project progress
    |
    +-- Clear checkpoint, emit metrics
```

Key design decisions:
- **Concurrency**: Semaphore(3) -- lower than DataFrame building to leave rate limit headroom
- **Task GID source**: Read from the just-warmed DataFrame (no additional API call) or enumerate via API if DataFrame is not available
- **Checkpoint granularity**: Per-project (not per-task) for checkpoint size management
- **Timeout handling**: Standard self-continuation pattern -- save checkpoint, invoke continuation Lambda with "story_warming" phase
- **Entry type list**: Configurable. Initially just "offer" (the timeline project). Extensible to other entity types.
- **Failure isolation**: Story warming failure does NOT fail the overall warming run. DataFrames are already warm; stories are a best-effort addition.

### Secondary Recommendation: Add Bounded Self-Healing to get_or_compute_timelines()

Regardless of which bulk population strategy is chosen, the compute-on-read path should be resilient to cache gaps. Add a bounded inline fetch for a limited number of cache misses:

```python
# In get_or_compute_timelines(), after read_stories_batch():
MAX_INLINE_FETCHES = 50
misses = [gid for gid, stories in stories_by_gid.items() if stories is None]

if len(misses) <= MAX_INLINE_FETCHES:
    # Fetch stories for misses inline (bounded, won't blow ALB timeout)
    sem = asyncio.Semaphore(5)
    async def fetch_one(gid):
        async with sem:
            await client.stories.list_for_task_cached_async(gid)
    await asyncio.gather(*[fetch_one(gid) for gid in misses])
    # Re-read batch after population
    stories_by_gid.update(read_stories_batch(misses, cache))
```

This handles:
- New offers added between Lambda warming runs (typically <50)
- Lambda warmer failures (if only a few tasks were missed)
- Story cache expiry between Lambda runs (if only a few have expired)

When misses exceed the threshold, the system returns partial results (imputed only) and logs a WARNING -- this signals that the Lambda warmer needs attention.

**Effort for self-healing addition**: ~0.5-1 day.

### Combined Recommendation: Strategy E + Bounded Self-Healing

| Component | Effort | Role |
|-----------|--------|------|
| Piggyback story warming on Lambda warmer | 1.5-2d | Bulk population on schedule |
| Bounded self-healing in compute-on-read | 0.5-1d | Edge case coverage + resilience |
| **Total** | **2-3d** | Complete story cache lifecycle |

### What NOT to Do

1. **Do not reintroduce a feature-coupled warm-up pipeline.** The remediation was correct to remove it. Story warming should be a cache-layer concern, not a timeline-layer concern.

2. **Do not make story warming block ECS startup.** The progressive DataFrame preload already runs as a background task. Story warming should follow the same pattern (Lambda or background task, not blocking).

3. **Do not introduce a new Lambda function.** The existing CacheWarmer is the right home for story warming. A separate function doubles operational overhead for no architectural benefit.

4. **Do not rely solely on self-healing.** A full cold start (3,800 tasks with zero cached stories) cannot be self-healed within the ALB timeout. Bulk warming is necessary for the base case.

### ADR-0148 Correction

The factual error in ADR-0148 ("The Lambda warmer continues to run on its existing schedule, populating story caches. This is unchanged.") should be corrected. The Lambda warmer has never populated story caches -- it populates DataFrames. This correction should be made as part of the implementation work, not as a standalone change.

---

## Appendix A: File Reference

| File | Role in This Analysis |
|------|----------------------|
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py` | Sole story cache write path (`load_stories_incremental`), read paths (`read_cached_stories`, `read_stories_batch`) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/stories.py` | `StoriesClient.list_for_task_cached()` -- caller of `load_stories_incremental` |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Lambda warmer -- DataFrames only, zero story involvement |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/warmer.py` | CacheWarmer internals -- proposed integration point for story warming |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py` | ECS startup -- no story warming after remediation |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` | `get_or_compute_timelines()` -- consumer of story cache, proposed self-healing integration point |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` | Derived timeline cache -- TTL interaction with story freshness |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/entry.py` | `EntryType.STORIES`, `CacheEntry.ttl = 300` default |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/providers/tiered.py` | TieredCacheProvider -- S3 cold tier extends story lifetime beyond Redis TTL |
| `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ARCH-REVIEW-1-CACHE.md` | Authoritative cache architecture overview |
| `/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0067-cache-system-divergence.md` | Cache divergence analysis (14 dimensions) |
| `/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0148-warm-up-pipeline-removal.md` | Warm-up removal decision (contains factual error about Lambda warmer scope) |
| `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-SECTION-TIMELINE-REMEDIATION.md` | TDD that drove the remediation |
