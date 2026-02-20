# ADR-0148: Warm-Up Pipeline Removal and Compute-on-Read Model

## Status

Proposed

## Context

The SectionTimeline feature currently uses a warm-up pipeline that runs at ECS container startup:

1. **Phase 1**: `warm_story_caches()` iterates ~3,800 offers with bounded concurrency (Semaphore(5)), calling `list_for_task_cached_async()` for each to populate the incremental story cache. Duration: 12-15 minutes.
2. **Phase 2**: `build_all_timelines()` enumerates tasks again and builds `SectionTimeline` for each using cached stories. Duration: 1-2 minutes (all cache hits after Phase 1).
3. **Result**: Stored on `app.state.offer_timelines` for zero-I/O request serving.
4. **Readiness gate**: Endpoint returns 503 TIMELINE_NOT_READY until >= 50% of offers are warmed, or 503 TIMELINE_WARM_FAILED if the pipeline times out.

This architecture was forced by four missing cache primitives. With ADR-0146 (pure-read mode + batch reads) and ADR-0147 (derived cache entries), three of the four gaps are closed. The warm-up pipeline is no longer necessary.

### Production Incident History

The warm-up pipeline caused 13 iterative production deployments:
- DEF-004: 291 rate_limit_429 events (Semaphore(20) too aggressive)
- DEF-005: Warm data invisible to request handlers (separate cache provider instances)
- DEF-006: Per-request I/O exceeded 60s ALB timeout (all I/O at request time before pre-compute fix)
- DEF-007: Warm-up timeout at 600s (3,800 offers at Semaphore(5) takes ~12 min)
- DEF-008: 50% readiness gate never firing (progress tracked at completion, not incrementally)
- 659 rate_limit_429 events from concurrent DataFrame + story warm-up

Each incident required a production deployment to fix. The complexity budget for warm-up infrastructure -- 130 lines in lifespan.py, 5 app.state keys, progress tracking, failure detection, sequential staggering -- is significant for what amounts to a startup optimization.

### Ambiguity Resolved

- **AMB-4 (Response time targets)**: Stakeholder confirmed <2s for warm cache, <5s for cold derived cache (on-demand computation).

## Decision

### 1. Remove the warm-up pipeline entirely

Remove from `src/autom8_asana/api/lifespan.py` (lines 251-386):
- `_warm_section_timeline_stories()` async function
- `timeline_warm_task` creation
- `app.state.timeline_warm_count`, `timeline_total`, `timeline_warm_failed` initialization

Remove from `src/autom8_asana/services/section_timeline_service.py`:
- `warm_story_caches()` function
- `build_all_timelines()` function
- `compute_timeline_entries()` function
- `_WARM_CONCURRENCY`, `_BUILD_CONCURRENCY`, `_WARM_TIMEOUT_SECONDS` constants

### 2. Adopt compute-on-read-then-cache model

On first request after derived cache expiry (or cold start):
1. Enumerate tasks via Asana API (~2s, one paginated call)
2. Batch-read cached stories from Redis (~500ms via get_batch)
3. Build timelines from cached stories (~100ms, pure CPU)
4. Store result as DerivedTimelineCacheEntry (5-min TTL)
5. Compute day counts and return response

Subsequent requests within the TTL window serve from the derived cache entry (<2s).

### 3. Remove readiness gate and 503 error codes

Remove from `src/autom8_asana/api/routes/section_timelines.py`:
- `_check_readiness()` function
- `_READINESS_THRESHOLD`, `_RETRY_AFTER_SECONDS` constants
- `_READY`, `_NOT_READY`, `_WARM_FAILED` constants
- 503 TIMELINE_NOT_READY error handling
- 503 TIMELINE_WARM_FAILED error handling

The endpoint always returns 200 with available data. Empty results on cold cache are a valid degraded response.

### 4. Remove all app.state timeline keys

No `app.state` keys for timeline data: `offer_timelines`, `timeline_warm_count`, `timeline_total`, `timeline_warm_failed`, `timeline_build_count`, `timeline_build_total`.

## Alternatives Considered

### Option A: Keep warm-up pipeline alongside cache primitives

- Pros: Guaranteed warm cache on startup. Zero first-request latency.
- Cons: Retains all the complexity (130 lines, 5 app.state keys, failure handling, staggering). Still subject to rate limit issues on restart. Defeats the purpose of the remediation -- if the warm-up pipeline is still needed, the cache primitives have not solved the problem.
- Decision: Rejected. The cache primitives make the warm-up pipeline unnecessary. The Lambda warmer already populates story caches on a schedule -- the warm-up pipeline was redundant once the Lambda warmer existed.

### Option B: Replace warm-up pipeline with Lambda warmer integration (FR-8)

- Pros: Pre-computes derived timelines in Lambda, so first ECS request is always a cache hit.
- Cons: Adds Lambda warmer complexity (derived entry computation, checkpoint resume). Couples timeline logic to the Lambda handler. This is an optimization over compute-on-read, not a prerequisite.
- Decision: Deferred to FR-8 (COULD priority). The compute-on-read model must work standalone first. Lambda integration can be added later as a performance optimization.

### Option C: Keep readiness gate with cache-layer backing

- Pros: Clients know when data is available vs. still computing
- Cons: The cache-layer model does not have a "warming" state -- data is either cached or it is not. A readiness gate implies a warm-up process, which we are removing. The endpoint should always return whatever data is available.
- Decision: Rejected. The endpoint returns 200 with partial or empty results when caches are cold. Clients can check the response `timelines` array length to determine data completeness.

## Rationale

1. **Elimination over optimization**: The warm-up pipeline has been the source of 13 production incidents. The correct fix is not to optimize the pipeline but to eliminate the need for it. Cache primitives (pure-read, batch reads, derived entries) provide the same functionality without startup-time infrastructure.

2. **Compute-on-read amortization**: A 2-4 second computation every 5 minutes is negligible compared to a 12-15 minute warm-up on every restart. Story caches are populated by a dedicated warming phase that piggybacks on the Lambda DataFrame warmer (added post-remediation). When story caches are warm, the derived computation is fast (batch-reading from Redis, not fetching from Asana API). A bounded self-healing mechanism handles small gaps.

3. **Graceful degradation over readiness gates**: A 503 response provides no value to the caller -- they must retry later. A 200 with partial results (or empty) provides what data is available immediately. The caller can decide whether to retry based on the response content.

4. **Response time targets**: <2s for warm derived cache (cache hit, deserialize, compute day counts). <5s for cold derived cache (enumerate tasks, batch-read stories, compute timelines, store derived entry). Both are within the 60s ALB timeout and are acceptable for the reconciliation use case.

## Consequences

### Positive

- 130 lines removed from lifespan.py (warm-up orchestration)
- 5 app.state keys eliminated (offer_timelines, timeline_warm_count, timeline_total, timeline_warm_failed, timeline_warm_task)
- 3 functions removed from section_timeline_service.py (warm_story_caches, build_all_timelines, compute_timeline_entries)
- Zero Asana API calls at ECS startup for timeline purposes
- Zero rate limit risk during deployment
- Zero warm-up timeout risk
- Container startup is faster (no 12-15 minute background task)
- Timeline data persists across restarts (in Redis/S3, not in-memory)

### Negative

- First request after derived cache expiry takes 2-4 seconds instead of sub-second
- If Lambda warmer has not populated story caches, first request returns empty/partial results instead of 503 with Retry-After
- Clients must handle empty results gracefully (previously they got 503 and knew to retry)

### Neutral

- The Lambda warmer now includes a story warming phase added post-remediation. This phase iterates task GIDs from warmed DataFrames and populates story caches with bounded concurrency. The DataFrame warming schedule is unchanged.
- The `max_cache_age_seconds` parameter on `load_stories_incremental()` can be removed as a follow-up (FR-7, SHOULD priority) since `build_timeline_for_offer()` no longer passes it.
- Task enumeration (`tasks.list_async(project=...)`) still hits the Asana API on every cold computation. This is Gap 2 (project membership caching), which is deferred.
