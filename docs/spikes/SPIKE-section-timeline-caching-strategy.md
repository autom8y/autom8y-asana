# SPIKE: Section Timeline Caching Strategy

```yaml
id: SPIKE-SECTION-TIMELINE-CACHE
status: COMPLETE
date: 2026-02-19
timebox: 2h
author: spike
relates_to: [TDD-SECTION-TIMELINE-001, PRD-SECTION-TIMELINE-001]
```

---

## Question

How should the SectionTimeline feature leverage the existing caching infrastructure? Specifically:
1. Can we rely on already-cached story data rather than building separate caching?
2. Is the TDD's pre-warm design optimal given what's already in place?
3. What opportunities exist to reduce cold-start latency or eliminate the pre-warm entirely?

## Decision This Informs

Whether to:
- (A) Keep the TDD's standalone pre-warm + 503 gate design as-is
- (B) Simplify by leaning on the existing cache infrastructure with minor refinements
- (C) Add a new cache tier for computed SectionTimeline results

---

## Findings

### 1. Stories Are Already Cached — Completely

The entity cache already stores stories via `EntryType.STORIES` in the tiered provider (Redis hot + S3 cold). The full lifecycle:

```
Request → StoriesClient.list_for_task_cached()
           → load_stories_incremental()
               → cache.get_versioned(task_gid, EntryType.STORIES)
               → Redis hit? → return cached
               → Redis miss, S3 hit? → promote to Redis, return
               → Both miss? → Asana API fetch → write-through to both
```

**Key facts:**
- S3 path: `{prefix}/tasks/{gid}/stories.json.gz` (gzipped >1024 bytes)
- Data format: `{"stories": [list of story dicts]}` with `metadata.last_fetched`
- Deduplication: `_merge_stories()` dedupes by GID, sorts by `created_at`
- `section_changed` is already in `DEFAULT_STORY_TYPES` (line 25 of `cache/integration/stories.py`)
- Write-through: writes go to both Redis AND S3 when `TieredConfig.write_through=True`

**The user's intuition was correct**: SectionTimeline is purely a CPU translation of already-persisted story data.

### 2. The Lambda Cache Warmer Does NOT Warm Stories

The `cache_warmer.py` Lambda and `CacheWarmer` class only warm **DataFrames** for entity types (`"offer"`, `"unit"`, `"business"`, `"contact"`). Stories are populated lazily — they enter the cache on first access via `list_for_task_cached()`.

This means:
- **First deployment ever**: S3 is empty, Redis is empty. Every offer needs a full Asana API fetch.
- **Subsequent deployments**: S3 has stories from prior runs. Redis may be cold (ECS task restart), but S3 promotes on miss.
- **Steady state**: Redis has hot stories, S3 has durable copies. Incremental fetches add only new stories since `last_fetched`.

### 3. Cost Analysis of the SectionTimeline Computation

The timeline computation breaks into two phases:

| Phase | Operation | Cost |
|-------|-----------|------|
| **I/O** | Fetch stories per offer via `list_for_task_cached()` | Cache hit: ~1-5ms (Redis), ~50-200ms (S3 promotion) |
| **CPU** | Filter `section_changed`, classify, walk intervals, count days | < 1ms per offer |

For 500 offers with warm caches:
- **Redis hot**: 500 × 3ms = ~1.5s total I/O + ~0.5s CPU = **~2s**
- **S3 cold (Redis evicted)**: 500 × 100ms = ~50s total (sequential) — exceeds NFR-1

This confirms the pre-warm is necessary for the Redis-miss scenario, but not for correctness — only for latency.

### 4. Cold-Start Scenarios

| Scenario | Redis | S3 | API Calls | Time | Frequency |
|----------|-------|-----|-----------|------|-----------|
| **Brand new deployment** | Empty | Empty | ~500 full fetches (~19 pages avg) | ~2-5 min | Once ever |
| **ECS task restart** | Empty | Populated | 0 API calls (S3 promotion) | ~50s sequential | Per deploy |
| **Steady state** | Hot | Populated | 0-few incremental | ~2s | Every request |

The critical insight: **after the first-ever warm, S3 has all stories**. Every subsequent ECS restart only needs Redis promotion, not Asana API calls.

### 5. Evaluation of the TDD's Pre-Warm Design

The TDD proposes `warm_story_caches()` — a background `asyncio.Task` that sequentially calls `list_for_task_cached_async()` for every offer during lifespan startup, with a 50% readiness gate.

**What it does well:**
- Reuses existing `list_for_task_cached()` — no new cache infrastructure
- Sequential fetching respects rate limits
- Progress tracking via callback is clean and decoupled
- 503 + Retry-After is a proper HTTP contract

**What could be refined:**
- It treats every startup as if Redis is empty, even when S3 has warm data
- Sequential S3 promotions (500 × ~100ms = 50s) could be parallelized since S3 reads don't hit Asana rate limits
- The 50% threshold could be lower for the S3-promotion case (data is already complete, just slower to serve)

### 6. Opportunity: Parallel S3 Promotion

When stories exist in S3 but not Redis, the pre-warm doesn't touch the Asana API at all — it's purely S3 → Redis promotion. This means we can safely parallelize with bounded concurrency:

```
Sequential S3 promotion:  500 × 100ms = 50s
Parallel (10 concurrent):  50 batches × 100ms = 5s
Parallel (50 concurrent):  10 batches × 100ms = 1s
```

The rate limit concern (sequential to avoid saturation) only applies to Asana API calls, not S3 reads.

### 7. Opportunity: No Separate Timeline Cache Tier

Caching the computed `OfferTimelineEntry` results would add:
- A new `EntryType.SECTION_TIMELINE` to the enum
- Cache key design (what invalidates it? any story change)
- TTL management
- ~10 lines of cache miss/hit logic

For a computation that costs < 1ms per offer. **Not worth it.** The CPU cost of re-deriving from cached stories on every request is negligible compared to the complexity of maintaining a derived cache.

---

## Comparison Matrix

| Strategy | Complexity | Cold Start | Steady State | Risk |
|----------|-----------|------------|--------------|------|
| **(A) TDD as-is** (sequential pre-warm + 503 gate) | Low | ~50s (S3) / ~2-5min (empty) | ~2s | Rate limit on first-ever deploy |
| **(B) Parallel S3 promotion + sequential API fallback** | Medium | ~5s (S3) / ~2-5min (empty) | ~2s | Concurrency tuning needed |
| **(C) Add timeline result cache** | High | Same as A/B + new cache layer | < 1s (cache hit) | Cache invalidation complexity, negligible gain |
| **(D) Skip pre-warm, serve from S3 inline** | Minimal | N/A (no startup cost) | ~50s first request | Unacceptable first-request latency |

---

## Recommendation

**Strategy B: Parallel S3 promotion with sequential Asana API fallback.**

Refine the TDD's pre-warm to distinguish between the two warm-up paths:

1. **S3-backed warm (most deploys)**: Use `asyncio.Semaphore(20)` to parallelize S3 → Redis promotion. Target: ~5s to warm 500 offers. This eliminates the cold-deploy latency concern for normal operations.

2. **API-backed warm (first-ever or after S3 wipe)**: Keep sequential fetching to respect Asana rate limits. This is a one-time cost.

3. **Detection**: The existing `list_for_task_cached()` already handles this transparently — it checks Redis, then S3, then API. No new detection logic needed. The parallelism just needs bounded concurrency to avoid overwhelming S3 or Redis.

4. **No new cache tier**: Derive SectionTimeline from cached stories on every request. The < 1ms per offer CPU cost makes a result cache unnecessary complexity.

5. **Lower the readiness threshold for S3-warm path**: When stories are promoted from S3 (not fetched from API), data completeness is already 100% from the prior deployment. Consider 0% threshold (serve immediately) since any individual offer miss is a ~100ms S3 read, not a multi-second API call.

### Implementation Delta from TDD

The changes to the TDD's `warm_story_caches()` are minimal:

```python
# Current TDD (sequential):
for task in tasks:
    await client.stories.list_for_task_cached_async(task.gid, ...)

# Refined (bounded parallel):
sem = asyncio.Semaphore(20)

async def warm_one(gid: str) -> bool:
    async with sem:
        await client.stories.list_for_task_cached_async(gid, ...)
        return True

results = await asyncio.gather(
    *[warm_one(t.gid) for t in tasks],
    return_exceptions=True,
)
```

The `list_for_task_cached()` internals handle S3-vs-API detection automatically. If the call hits the Asana API (no cache), it still works — just slower. The semaphore bounds concurrent API calls, which is safer than unbounded parallel but faster than fully sequential.

### What NOT To Do

- **Don't add `EntryType.SECTION_TIMELINE`** — the derived computation is too cheap to justify caching.
- **Don't modify `load_stories_incremental()`** — it's correct as-is for the SectionTimeline use case.
- **Don't add story warming to the Lambda cache warmer** — the Lambda warms DataFrames on a schedule; story warming is an ECS startup concern with different lifecycle semantics.
- **Don't remove the 503 readiness gate** — even with fast S3 promotion, the first request shouldn't block while 500 S3 reads complete.

---

## Follow-Up Actions

1. **Update TDD Section 4.1**: Change `warm_story_caches()` from sequential to bounded-parallel (`asyncio.Semaphore(20)` + `asyncio.gather`).
2. **Update TDD Section 6.2**: Note that the 50% threshold is conservative for S3-warm scenarios; consider exposing as a config value for future tuning.
3. **No new files or cache types needed** — all caching infrastructure is already in place.
4. **Proceed to implementation** — the cache strategy doesn't block or change the fundamental architecture. The principal engineer should implement Strategy B directly.
