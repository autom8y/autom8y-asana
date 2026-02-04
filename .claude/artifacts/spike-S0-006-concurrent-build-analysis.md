# Spike S0-006: Concurrent Build Frequency Analysis

**Date**: 2026-02-04
**Scope**: Opportunity A3 (DataFrame Build Coalescing) risk assessment
**Status**: Complete

---

## 1. Build Path Diagram

All code paths that can trigger a DataFrame build for a given `(project_gid, entity_type)`:

```
                        +--------------------------+
                        |   ENTRY POINTS           |
                        +--------------------------+
                                |
        +-----------------------+-----------------------+-------------------+
        |                       |                       |                   |
        v                       v                       v                   v
  POST /v1/resolve       POST /v1/query          POST /v1/query        POST /v1/admin
  /{entity_type}         /{entity_type}           /{et}/rows            /cache/refresh
  (resolver.py)          (query.py)               (query.py)            (admin.py)
        |                       |                       |                   |
        v                       v                       v                   v
  strategy.resolve()     EntityQueryService      QueryEngine          _perform_cache_
        |                .query()                .execute_rows()       refresh() [bg]
        |                       |                       |                   |
        |                       |                       v                   |
        |                       |              EntityQueryService            |
        |                       |              .get_dataframe()              |
        |                       |                       |                   |
        +----------+------------+-----------+-----------+                   |
                   |                        |                               |
                   v                        v                               |
           @dataframe_cache          UniversalResolution                    |
           decorator                 Strategy._get_dataframe()              |
           (decorator.py)                   |                               |
                   |              +---------+---------+                     |
                   |              |         |         |                     |
                   |              v         v         v                     |
                   |         [1] check  [2] check [3] trigger              |
                   |         _cached_   DataFr.   legacy                   |
                   |         dataframe  Cache     strategy                 |
                   |              |     .get()    .resolve()               |
                   |              |         |         |                     |
                   |              |         v         v                     |
                   |              |    Memory->S3  @dataframe_cache         |
                   |              |    tier lookup  decorator wraps         |
                   |              |         |       resolve()               |
                   |              |         |         |                     |
                   v              v         v         v                     |
           +----------------------------------------------+                |
           |         CACHE MISS -> BUILD PATH              |                |
           +----------------------------------------------+                |
                             |                                              |
                +------------+------------+                                 |
                |                         |                                 |
                v                         v                                 v
         decorator path            UniversalStrategy       CacheWarmer.warm_all_async()
         acquire_build_lock        ._build_entity_          (warmer.py)
         -> build -> put_async      dataframe()             [sequential by entity_type]
         -> release_lock                  |                         |
                                          v                         |
                                   ProgressiveProject               |
                                   Builder.build_                   |
                                   progressive_async()              |
                                          |                         |
                                          v                         v
                                  +----------------------------+
                                  | DataFrameCache.put_async() |
                                  | Memory + S3 tier write     |
                                  +----------------------------+


ADDITIONAL ENTRY: Startup preload (api/main.py)
  _preload_dataframe_cache_progressive()
    -> asyncio.gather() with Semaphore(3)
    -> ProgressiveProjectBuilder per project
    -> DataFrameCache.put_async()

ADDITIONAL ENTRY: SWR background refresh (dataframe_cache.py)
  _trigger_swr_refresh()
    -> asyncio.create_task()
    -> acquire_build_lock_async()
    -> _build_callback() or no-op
    -> release_build_lock_async()
```

## 2. Concurrency Analysis

### 2.1 Which paths can execute simultaneously for the same (project_gid, entity_type)?

**Concurrent-capable paths** (same key, same process):

| Path A | Path B | Can overlap? | Protection? |
|--------|--------|-------------|-------------|
| API resolve request 1 | API resolve request 2 | YES (async) | `@dataframe_cache` decorator uses coalescer |
| API query request 1 | API query request 2 | YES (async) | UniversalStrategy._get_dataframe has NO lock |
| API resolve request | API query request | YES (async) | **DIFFERENT code paths, DIFFERENT protection** |
| API request | SWR background refresh | YES (async) | SWR uses coalescer; API resolve uses decorator coalescer; API query has NO lock |
| API request | Startup preload | YES (async) | Preload has no coordination with API paths |
| API request | Admin cache refresh | YES (async) | Admin refresh runs in background task |
| Startup preload project A | Startup preload project B | YES (bounded by Semaphore(3)) | Different keys, no conflict |
| Startup preload project A | Startup preload project A | NO | Same project appears once in config |

### 2.2 The Critical Gap: Two Separate Build Paths

There are **two distinct build mechanisms** that lack mutual coordination:

1. **`@dataframe_cache` decorator** (`cache/dataframe/decorator.py`):
   - Used by the resolve endpoint via `legacy_strategy.resolve()`
   - Uses `DataFrameCache.acquire_build_lock_async()` and `wait_for_build_async()`
   - Properly coalesces concurrent resolve requests

2. **`UniversalResolutionStrategy._get_dataframe()`** (`services/universal_strategy.py`):
   - Used by query endpoints (via `EntityQueryService`) and `QueryEngine`
   - On cache miss (line 430-449): calls `legacy_strategy.resolve([], ...)` which triggers decorator
   - But the strategy itself has **no build lock** -- it just calls the legacy path and hopes it populates
   - If the legacy strategy also misses, or if two query requests hit simultaneously before the legacy strategy completes, both will attempt builds

3. **`_build_entity_dataframe()`** (`universal_strategy.py` line 486-558):
   - Direct build method on UniversalResolutionStrategy
   - Called by `_build_dataframe()` (line 462-484)
   - Called by CacheWarmer (warmer.py line 345)
   - Has **no build lock or coalescing**

### 2.3 Scenario: Concurrent Query Requests on Cold Cache

```
Time  Request A (query/offer)              Request B (query/offer)
----  ---------------------------          ---------------------------
T0    EntityQueryService.query()           EntityQueryService.query()
T1    strategy._get_dataframe()            strategy._get_dataframe()
T2    _cached_dataframe = None             _cached_dataframe = None
T3    cache.get_async() -> None            cache.get_async() -> None
T4    legacy_strategy.resolve([])          legacy_strategy.resolve([])
T5    -> @dataframe_cache decorator        -> @dataframe_cache decorator
T6    -> acquire_build_lock -> True        -> acquire_build_lock -> False
T7    -> BUILD STARTS                      -> wait_for_build(timeout=30s)
T8    -> build complete, put_async()       -> build complete, returns entry
T9    -> cache.get_async() -> entry        -> resolve returns []
T10   returns DataFrame                    strategy._get_dataframe() retries?
                                           NO -- it just returns None on line 449
                                           -> CacheNotWarmError raised!
```

**Wait.** Looking more carefully at the flow: Request B at T5 enters the `@dataframe_cache` decorator wrapping `legacy_strategy.resolve()`. The decorator at line 121-132 handles the "not acquired" case: it calls `wait_for_build_async()` and then if the build succeeds, injects the cached DataFrame and calls `original_resolve()`. But `original_resolve()` for the legacy strategy returns `[]` (empty resolve results since criteria was `[]`). Then control returns to `UniversalResolutionStrategy._get_dataframe()` at line 440-449, which does `cache.get_async()` again -- and this time finds the entry because Request A's build stored it.

So **for the resolve/legacy decorator path, coalescing works correctly** for concurrent requests.

### 2.4 Scenario: Query + Resolve Concurrent on Same Key

Both use the same `DataFrameCacheCoalescer` instance (singleton via the `DataFrameCache` singleton). The coalescer keys on `entity_type:project_gid`. So even if one request comes through the query path and another through the resolve path, they share the same coalescer. This is correct.

### 2.5 Scenario: SWR Background Refresh + API Request

The `_trigger_swr_refresh()` method (dataframe_cache.py line 792-821):
- Checks `coalescer.is_building(cache_key)` first -- if building, returns (deduped)
- Fires `asyncio.create_task(_swr_refresh_async())`
- `_swr_refresh_async()` acquires build lock via coalescer
- Uses `_build_callback` if registered, otherwise no-op

The SWR refresh properly uses the coalescer. If an API request triggers a build through the decorator, the SWR refresh will see `is_building=True` and skip.

### 2.6 Scenario: Startup Preload + API Request (Race Window)

```
Time  Startup Preload                     Incoming API Request
----  ---------------------------          ---------------------------
T0    asyncio.gather() starts              (blocked by health check = 503)
T1    builder.build_progressive_async()    ...
T2    ...                                  ...
T3    dataframe_cache.put_async()          ...
T4    set_cache_ready(True)                /health/ready -> 200
T5    ...                                  resolve request arrives
T6                                         @dataframe_cache -> cache hit
```

The race window here is between `set_cache_ready(True)` (T4) and `put_async()` (T3). Since `set_cache_ready` is called in the `finally` block (line 1272), it happens AFTER all `put_async()` calls complete. API requests only arrive after health check passes. **This path is safe.**

However, if startup preload fails for an entity type (returns False) and `set_cache_ready(True)` is still called (line 1272), then API requests arrive and hit a cold cache. The decorator path handles this gracefully via build + coalescing.

### 2.7 Scenario: Admin Refresh + API Request

Admin refresh (`admin.py`) runs `_perform_cache_refresh()` as a FastAPI `BackgroundTasks` task. This:
- Invalidates memory cache (`cache.invalidate()`)
- Triggers a rebuild (either incremental or full/Lambda)

During the invalidation window, API requests may see cache misses and trigger builds through the decorator. The coalescer handles this if both go through `acquire_build_lock_async()`. However, the admin incremental rebuild uses `ProgressiveProjectBuilder` directly (not through the coalescer). This creates a potential for **parallel builds for the same key**: one from the admin background task, one from an API request's decorator-triggered build.

**This is a real gap**, but the impact is low because admin refreshes are operator-initiated (rare, intentional).

## 3. Current Protection Mechanisms

| Mechanism | Location | Scope | Effective? |
|-----------|----------|-------|------------|
| **DataFrameCacheCoalescer** | `cache/dataframe/coalescer.py` | Build lock with asyncio.Event-based waiter notification | YES - properly prevents thundering herd for @dataframe_cache decorator path |
| **@dataframe_cache decorator** | `cache/dataframe/decorator.py` | Wraps `resolve()` method; acquire/wait/release pattern | YES - coalesces concurrent resolve requests |
| **SWR dedup check** | `dataframe_cache.py:803` | `coalescer.is_building()` check before scheduling refresh | YES - prevents duplicate SWR refreshes |
| **Semaphore(3) for preload** | `api/main.py:1062` | Bounds concurrent project builds during startup | YES - but operates on different (project_gid, entity_type) keys |
| **Circuit breaker** | `cache/dataframe/circuit_breaker.py` | Per-project failure isolation | YES - prevents repeated build attempts after failures |
| **Memory + S3 tiering** | `dataframe_cache.py` get_async | Falls through Memory -> S3 -> None | YES - reduces build frequency by preserving S3 state |

### Mechanisms NOT present:

| Missing | Impact |
|---------|--------|
| Build lock on `UniversalResolutionStrategy._build_entity_dataframe()` | Low: callers go through decorator which has lock |
| Coordination between admin refresh and API build paths | Low: admin refreshes are rare operator actions |
| Cross-process locking (e.g., DynamoDB lock) | N/A: single ECS task per deployment |
| Request deduplication at API gateway level | N/A: each request is distinct |

## 4. Risk Assessment

### 4.1 Likelihood

| Scenario | Likelihood | Reasoning |
|----------|-----------|-----------|
| Concurrent resolve requests, same key, cold cache | **LOW** | Cache is pre-warmed at startup; TTLs are 3-60 minutes; coalescer protects |
| Concurrent query requests, same key, cold cache | **LOW** | Same reasoning; query path delegates to legacy strategy which has coalescer |
| SWR refresh overlapping API request | **VERY LOW** | SWR checks `is_building()` before starting; uses same coalescer |
| Admin refresh + API request collision | **VERY LOW** | Admin is operator-initiated; rare event |
| Startup preload race with API traffic | **NEGLIGIBLE** | Health check gates traffic until preload completes |
| Cross-instance thundering herd | **N/A** | Single ECS task architecture; no multi-instance deployments |

### 4.2 Impact if Thundering Herd Occurs

| Impact | Severity | Notes |
|--------|----------|-------|
| Duplicate Asana API calls | **MEDIUM** | Each build fetches all tasks from all sections of a project; rate limit risk |
| Memory spike | **LOW-MEDIUM** | Two concurrent builds would roughly double memory for that entity's DataFrame; entity DFs are typically 5-50MB |
| Increased latency for waiting requests | **LOW** | Coalescer timeout is 30s; 503 returned on timeout |
| Asana API rate limiting | **MEDIUM** | Multiple concurrent builds multiply API calls; Asana has per-PAT rate limits |
| Incorrect data | **NONE** | Builds are idempotent; last-write-wins semantics are safe |

### 4.3 Overall Risk Rating: **LOW**

The existing `DataFrameCacheCoalescer` effectively prevents thundering herd for the primary build path (`@dataframe_cache` decorator). The secondary paths (query service, admin refresh) either delegate to the primary path or are infrequent enough to not pose a material risk.

The main risk vector would be a **cache invalidation event affecting multiple entity types simultaneously** (e.g., schema version bump via `invalidate_on_schema_change()`), but:
- Schema changes are deployment-time events, not runtime
- The startup preload rebuilds all caches sequentially (business first, then others in parallel)
- Entity types have different project GIDs, so coalescer keys are distinct

### 4.4 Realistic Load Pattern Analysis

Based on the architecture:
- **Normal operation**: Cache is warm from startup preload. All requests hit Memory tier (sub-ms). No builds triggered.
- **SWR window** (TTL expired, within grace): Stale data served immediately. Single background refresh fires. Coalescer prevents duplicates.
- **LKG window** (beyond grace): Stale data served with warning. Background refresh fires. Coalescer prevents duplicates.
- **Cold start** (new deployment): Startup preload builds all caches before accepting traffic. Health check gates API requests.
- **Post-admin-refresh**: Brief cache miss window. First request triggers build through decorator with coalescing. Others wait or get 503 with retry guidance.

## 5. Recommendation

### Should A3 (Build Coalescing) remain in Sprint 4 or be elevated?

**Recommendation: Keep A3 in Sprint 4 (no elevation needed).**

**Rationale:**

1. **The coalescer already exists and works.** The `DataFrameCacheCoalescer` in `cache/dataframe/coalescer.py` properly implements the first-builds-others-wait pattern with asyncio.Event notification. The `@dataframe_cache` decorator correctly integrates it with acquire/wait/release semantics.

2. **The thundering herd risk is already mitigated** for the primary code paths (resolve and query endpoints). The secondary paths (admin, startup) are either gated by health checks or are infrequent operator actions.

3. **The real A3 value is not preventing thundering herd** (that is already done) but rather:
   - Unifying the build path so `UniversalResolutionStrategy._build_entity_dataframe()` always goes through the coalescer (not just when called via the decorator)
   - Adding observability: the coalescer tracks `builds_coalesced` stats but they are not currently surfaced in metrics
   - Adding cross-entity-type awareness (e.g., if Unit and Business share a project GID, coordinating their builds)

4. **Sprint 4 timing is appropriate** because:
   - No production incidents attributable to concurrent builds
   - The existing protection is sufficient for current load
   - Sprint 4 allows proper design with the Architect to rationalize the dual-path build architecture

### Minor Improvement Suggestions (can be done independently of A3):

1. **Log coalescer statistics on each build** -- add `builds_coalesced` to the existing `dataframe_cache_put` log event for operational visibility.
2. **Add a metric for `_get_dataframe` cache miss rate** in `UniversalResolutionStrategy` to track how often the build path is actually invoked in production.

---

**Artifacts Referenced:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/coalescer.py` -- DataFrameCacheCoalescer
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` -- @dataframe_cache decorator
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` -- DataFrameCache with SWR/LKG/circuit breaker
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/warmer.py` -- CacheWarmer for Lambda warming
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` -- UniversalResolutionStrategy
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` -- EntityQueryService
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py` -- QueryEngine
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` -- Startup preload with asyncio.gather
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py` -- Resolve endpoint
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py` -- Query endpoints
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/admin.py` -- Admin cache refresh
