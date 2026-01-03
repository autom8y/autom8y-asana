# INTEGRATE-dataframe-materialization

**Date**: 2026-01-01
**Status**: Ready for Prototype Selection
**Author**: Integration Researcher (rnd-pack)
**Upstream**: SPIKE-entity-resolver-timeout

## Overview

This integration map analyzes how five DataFrame materialization options connect with the existing autom8_asana codebase to eliminate the 30-second cold-start penalty identified in the Entity Resolver timeout spike. The goal is to pre-populate the `_gid_index_cache` before the first request arrives.

**Problem Statement**: The `GidLookupIndex` is built on-demand at request time, causing 30+ second latency on the first request to each container instance.

**Target Outcome**: First request latency under 500ms with warm `GidLookupIndex`.

---

## Current State

### Architecture

```
                           CURRENT ARCHITECTURE

  Container Start                              First Request
  +--------------+                             +-----------------+
  | 1. Import    |                             | 1. POST /resolve|
  | 2. Discover  |---(GID stored)---+          | 2. _get_or_     |
  |    Projects  |                  |          |    build_index()|
  | 3. Ready     |                  |          | 3. CACHE MISS   |
  +--------------+                  |          | 4. Build DF     |<-- 30s
                                    v          | 5. Build Index  |
                           +----------------+  | 6. Lookup       |
                           | _gid_index_    |  +-----------------+
                           | cache = {}     |
                           | (EMPTY)        |
                           +----------------+
```

### Integration Points

| System | Interface | Data Flow | Frequency |
|--------|-----------|-----------|-----------|
| `S3CacheProvider` | `get_versioned()`/`set_versioned()` | CacheEntry (JSON+gzip) | Per task/row |
| `TieredCacheProvider` | Write-through Redis+S3 | CacheEntry | Per task/row |
| `RedisCacheProvider` | HGET/HSET with pipeline | CacheEntry | Per task/row |
| `ProjectDataFrameBuilder` | `build_with_parallel_fetch_async()` | Polars DataFrame | Per project |
| `GidLookupIndex` | `from_dataframe()` | Dict[PhoneVerticalPair, str] | Per project |
| `EntityProjectRegistry` | `get_project_gid()` | str (GID) | Startup + per-request |
| `WebhooksClient` | `create_async()`/`verify_signature()` | Webhook events | Per Asana change |

### Dependencies

```
Entity Resolver Cold Start Dependencies
========================================

resolver.py::_get_or_build_index()
    |
    +-- _gid_index_cache (module-level dict) -----> EMPTY on startup
    |
    +-- resolver.py::_build_dataframe()
        |
        +-- ProjectDataFrameBuilder
            |
            +-- ParallelSectionFetcher.fetch_all()
            |   |
            |   +-- SectionsClient.list_async()    ~1s
            |   +-- TasksClient.list_tasks_for_section_async() x N   ~3s
            |
            +-- TaskCacheCoordinator (if cache enabled)
            |   |
            |   +-- RedisCacheProvider.get_batch()  ~10ms warm
            |   +-- S3CacheProvider.get_batch()     ~100ms warm
            |
            +-- API fetch for cache misses          ~25s cold
            |
            +-- Polars DataFrame construction       ~500ms
        |
        +-- GidLookupIndex.from_dataframe()         ~100ms
```

### Hidden Dependencies (Not in Documentation)

| Dependency | Impact | Discovery Method |
|------------|--------|------------------|
| `_gid_index_cache` is module-level, not process-shared | Each container starts cold | Code inspection |
| `GidLookupIndex.is_stale()` uses `created_at`, not `modified_at` | TTL is from index creation, not data freshness | Code inspection |
| `ProjectDataFrameBuilder` requires `AsanaClient` instance | Cannot build at import time | Code inspection |
| Redis connection pool initializes on first use | First cache access adds ~50ms | Performance testing |
| S3 client lazy-initializes boto3 | First S3 access adds ~200ms | Performance testing |
| `EntityProjectRegistry` is singleton but per-process | No shared state across containers | Architecture review |

---

## Target State

### Desired Architecture

```
                           TARGET ARCHITECTURE

  Container Start                              First Request
  +--------------+                             +-----------------+
  | 1. Import    |                             | 1. POST /resolve|
  | 2. Discover  |---(GID stored)---+          | 2. _get_or_     |
  |    Projects  |                  |          |    build_index()|
  | 3. PREFETCH  |---+              |          | 3. CACHE HIT    |
  | 4. BUILD IDX |   |              |          | 4. O(1) Lookup  |<-- <10ms
  | 5. Ready     |   |              v          +-----------------+
  +--------------+   |     +----------------+
                     +---->| _gid_index_    |
                           | cache[unit_gid]|
                           | = GidLookupIdx |
                           +----------------+
```

---

## Option Analysis

### Option A: Startup Index Preloading

**Description**: Build `GidLookupIndex` during container startup in `_discover_entity_projects()`.

#### Dependency Diagram

```
Option A: Startup Preloading
============================

main.py::lifespan()
    |
    +-- _discover_entity_projects()
        |
        +-- EntityProjectRegistry.register()  (existing)
        |
        +-- [NEW] _prefetch_gid_index()
            |
            +-- get_strategy("unit")
            |   +-- UnitResolutionStrategy (already registered)
            |
            +-- strategy._get_or_build_index(unit_gid, client)
                |
                +-- _build_dataframe()           ~30s
                +-- GidLookupIndex.from_dataframe()
                +-- _gid_index_cache[unit_gid] = index
```

#### Existing Code Reuse

| Component | Reuse | Notes |
|-----------|-------|-------|
| `UnitResolutionStrategy._get_or_build_index()` | 100% | Use directly |
| `ProjectDataFrameBuilder` | 100% | Already used by strategy |
| `_gid_index_cache` | 100% | Target cache |
| `EntityProjectRegistry` | 100% | Source of project GIDs |
| `AsanaClient` | 100% | Already created in lifespan |

**Reuse Percentage**: ~95%

#### New Components Needed

| Component | Effort | Description |
|-----------|--------|-------------|
| `_prefetch_gid_index()` | 0.5 days | ~20 lines, call existing methods |
| Health check modification | 0.25 days | Return 503 until index ready |
| ECS task definition update | 0.25 days | Increase health check grace period |

#### Integration Points

```python
# main.py - Addition to _discover_entity_projects()
async def _prefetch_gid_index(
    registry: EntityProjectRegistry,
    client: AsanaClient,
) -> None:
    """Pre-build GidLookupIndex at startup."""
    from autom8_asana.services.resolver import get_strategy, _gid_index_cache

    unit_gid = registry.get_project_gid("unit")
    if unit_gid:
        strategy = get_strategy("unit")
        # This populates _gid_index_cache
        await strategy._get_or_build_index(unit_gid, client)
```

#### Breaking Changes

None. Purely additive.

#### Effort Estimate

| Component | Effort | Confidence | Assumptions |
|-----------|--------|------------|-------------|
| Code changes | 1 day | High | Simple integration |
| Testing | 0.5 days | High | Existing test patterns |
| ECS configuration | 0.5 days | High | Familiar infrastructure |
| **Total** | **2 days** | **High** | |

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Startup timeout | Medium | High | Configure 60s health check grace |
| Asana API rate limit during startup | Low | Medium | Already using parallel fetch |
| Index build failure blocks startup | Medium | High | Add timeout + fallback |

---

### Option B: S3 DataFrame Persistence

**Description**: Serialize `GidLookupIndex` to S3, load at startup, refresh in background.

#### Dependency Diagram

```
Option B: S3 DataFrame Persistence
==================================

Startup Path (Fast)                    Background Refresh
-----------------                      ------------------
main.py::lifespan()                    asyncio.create_task()
    |                                      |
    +-- _load_cached_index()               +-- _refresh_index_loop()
        |                                      |
        +-- S3CacheProvider.get_versioned()    +-- sleep(TTL/2)
        |   Key: "dataframe/gid_index/unit"    |
        |                                      +-- _build_and_cache_index()
        +-- GidLookupIndex.deserialize()           |
        |                                          +-- _build_dataframe()
        +-- _gid_index_cache[unit] = index         +-- serialize_to_s3()

        If miss: fallback to Option A path
```

#### Existing Code Reuse

| Component | Reuse | Notes |
|-----------|-------|-------|
| `S3CacheProvider` | 80% | Need new key pattern for index |
| `S3Config` | 100% | Already configured |
| `EntryType.DATAFRAME` | 100% | Already exists |
| `CacheEntry` serialization | 90% | Extend for index format |
| `TieredCacheProvider` | 70% | Can use for hot tier too |

**Reuse Percentage**: ~75%

#### New Components Needed

| Component | Effort | Description |
|-----------|--------|-------------|
| `GidLookupIndex.serialize()`/`deserialize()` | 1 day | JSON serialization of dict |
| `_load_cached_index()` | 0.5 days | S3 fetch + deserialization |
| `_refresh_index_loop()` | 0.5 days | Background refresh task |
| S3 key pattern for index | 0.25 days | Extend `_make_key()` |
| Version tracking for index | 0.5 days | Track last Asana sync time |

#### Integration Points

```python
# resolver.py - New serialization
class GidLookupIndex:
    def serialize(self) -> dict:
        return {
            "version": 1,
            "created_at": self.created_at.isoformat(),
            "entries": {
                f"{pvp.office_phone}:{pvp.vertical}": gid
                for pvp, gid in self._index.items()
            }
        }

    @classmethod
    def deserialize(cls, data: dict) -> "GidLookupIndex":
        # Reconstruct from serialized format
        ...

# cache/backends/s3.py - Extended key pattern
def _make_key(self, key: str, entry_type: EntryType) -> str:
    if entry_type == EntryType.DATAFRAME:
        # Support nested keys for index
        return f"{self._config.prefix}/dataframe/{key}.json"
    # ... existing logic
```

#### Breaking Changes

None. New functionality.

#### Effort Estimate

| Component | Effort | Confidence | Assumptions |
|-----------|--------|------------|-------------|
| Serialization methods | 1 day | High | Simple JSON |
| S3 integration | 1 day | Medium | May need testing with gzip |
| Background refresh | 1 day | Medium | Async task management |
| Testing | 1 day | Medium | Need S3 mocking |
| **Total** | **4 days** | **Medium** | S3 access is reliable |

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| S3 unavailable at startup | Low | High | Fallback to API build |
| Stale S3 index | Medium | Low | Background refresh + TTL |
| Serialization format changes | Low | Medium | Version field in payload |
| Concurrent refresh race | Low | Low | Single writer pattern |

---

### Option C: Webhook-Driven Refresh

**Description**: Use Asana webhooks to trigger index invalidation on data changes.

#### Dependency Diagram

```
Option C: Webhook-Driven Refresh
================================

Asana Task Changed
       |
       v
POST /webhooks/asana
       |
       +-- WebhooksClient.verify_signature()
       |
       +-- [NEW] webhook_handler()
           |
           +-- extract_project_gid(event)
           |
           +-- invalidate_gid_index(project_gid)
           |   |
           |   +-- _gid_index_cache.pop(project_gid)
           |   +-- [Optional] trigger_rebuild()
           |
           +-- [Optional] Publish to Redis Pub/Sub
               (notify other containers)
```

#### Existing Code Reuse

| Component | Reuse | Notes |
|-----------|-------|-------|
| `WebhooksClient` | 90% | CRUD + signature verification |
| `verify_signature()` | 100% | HMAC-SHA256 already implemented |
| `extract_handshake_secret()` | 100% | Header extraction |
| Webhook model | 100% | Pydantic models exist |

**Reuse Percentage**: ~60%

#### New Components Needed

| Component | Effort | Description |
|-----------|--------|-------------|
| `/webhooks/asana` endpoint | 1 day | FastAPI route + handler |
| Webhook registration logic | 0.5 days | Create webhooks for unit project |
| Secret storage | 0.5 days | Store handshake secret |
| Event filtering | 0.5 days | Only react to relevant changes |
| Cross-container notification | 2 days | Redis Pub/Sub or similar |
| Webhook handshake handler | 0.25 days | Respond to initial setup |

#### Integration Points

```python
# api/routes/webhooks.py - New route
@router.post("/webhooks/asana")
async def handle_asana_webhook(
    request: Request,
    x_hook_signature: str = Header(...),
):
    body = await request.body()

    # Verify signature
    if not WebhooksClient.verify_signature(body, x_hook_signature, secret):
        raise HTTPException(status_code=401)

    # Parse event and invalidate cache
    events = json.loads(body)["events"]
    for event in events:
        if event["resource"]["resource_type"] == "task":
            project_gid = _get_project_from_event(event)
            _gid_index_cache.pop(project_gid, None)
```

#### Breaking Changes

None. New functionality requires deployment configuration.

#### Effort Estimate

| Component | Effort | Confidence | Assumptions |
|-----------|--------|------------|-------------|
| Webhook endpoint | 1 day | High | Standard FastAPI |
| Webhook registration | 1 day | Medium | Asana API documentation |
| Secret management | 0.5 days | High | Existing patterns |
| Cross-container sync | 3 days | Low | Requires Pub/Sub |
| Testing | 2 days | Low | Webhook testing is complex |
| **Total** | **7.5 days** | **Low** | Cross-container is hard |

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Webhook delivery delays | Medium | Low | Combine with TTL |
| Cross-container sync complexity | High | High | Consider Redis Pub/Sub |
| Webhook quota limits | Low | Medium | Filter events aggressively |
| Handshake failures | Medium | Medium | Retry logic + monitoring |

---

### Option D: Redis Pub/Sub Coordination

**Description**: Use Redis Pub/Sub to coordinate index state across containers.

#### Dependency Diagram

```
Option D: Redis Pub/Sub Coordination
====================================

Container A (Leader)                 Container B (Follower)
-------------------                  ---------------------
Build Index                          Subscribe to channel
    |                                    |
    +-- _gid_index_cache[unit] = idx     +-- on_message("index_ready")
    |                                    |
    +-- redis.publish(                   +-- _load_index_from_redis()
    |       "index:ready",               |   |
    |       {"project": "unit",          |   +-- redis.get("index:unit")
    |        "version": "2026-01-01"}    |   +-- deserialize()
    |   )                                |   +-- _gid_index_cache[unit] = idx
    |                                    |
    +-- redis.set("index:unit", blob)    +-- (index loaded without API call)
```

#### Existing Code Reuse

| Component | Reuse | Notes |
|-----------|-------|-------|
| `RedisCacheProvider` | 60% | Need Pub/Sub extension |
| `RedisConfig` | 100% | Connection config |
| Connection pooling | 100% | Already implemented |
| `CacheEntry` serialization | 80% | Adapt for index |

**Reuse Percentage**: ~55%

#### New Components Needed

| Component | Effort | Description |
|-----------|--------|-------------|
| Redis Pub/Sub wrapper | 1.5 days | Publish/Subscribe abstraction |
| Leader election (optional) | 2 days | Only one builder at a time |
| Index serialization to Redis | 1 day | Large value handling |
| Subscriber background task | 1 day | Async listener |
| Fallback on subscriber failure | 0.5 days | Degrade gracefully |

#### Integration Points

```python
# cache/backends/redis.py - Pub/Sub extension
class RedisCacheProvider:
    async def publish(self, channel: str, message: dict) -> None:
        conn = self._get_connection()
        await conn.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str, handler: Callable) -> None:
        pubsub = self._get_connection().pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                await handler(json.loads(message["data"]))

# resolver.py - Coordinator
class IndexCoordinator:
    async def notify_index_ready(self, project_gid: str) -> None:
        await redis.publish("index:ready", {"project": project_gid})

    async def on_index_ready(self, message: dict) -> None:
        project_gid = message["project"]
        index = await self._load_from_redis(project_gid)
        _gid_index_cache[project_gid] = index
```

#### Breaking Changes

None. Purely additive.

#### Effort Estimate

| Component | Effort | Confidence | Assumptions |
|-----------|--------|------------|-------------|
| Pub/Sub wrapper | 1.5 days | Medium | redis-py supports async |
| Index storage in Redis | 1 day | Medium | Need to handle large values |
| Subscriber task | 1 day | Medium | Background task patterns |
| Leader election | 2 days | Low | May not be needed |
| Testing | 2 days | Low | Pub/Sub testing is complex |
| **Total** | **7.5 days** | **Low** | Redis connection is stable |

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pub/Sub message loss | Medium | Medium | Combine with polling |
| Redis value size limits | Medium | Medium | Use hash or split |
| Race conditions | Medium | Low | Eventual consistency |
| Complexity for single-instance | N/A | N/A | Overkill for simple deploy |

---

### Option E: Hybrid Approach (Recommended)

**Description**: Combine Startup Preloading (A) + S3 Persistence (B) for fast startup + durability.

#### Dependency Diagram

```
Option E: Hybrid (A + B)
========================

Cold Start (New Container)           Warm Start (Restart)
----------------------               -------------------
main.py::lifespan()                  main.py::lifespan()
    |                                    |
    +-- _load_cached_index()             +-- _load_cached_index()
    |   |                                |   |
    |   +-- S3.get("index:unit")         |   +-- S3.get("index:unit")
    |   |   --> MISS                     |   |   --> HIT (1-2s)
    |   |                                |   |
    |   +-- Fallback to API build        |   +-- deserialize()
    |       |                            |   |
    |       +-- _build_dataframe() ~30s  |   +-- _gid_index_cache[unit]=idx
    |       +-- S3.set("index:unit")     |
    |       +-- _gid_index_cache[unit]=idx
    |                                    +-- (Ready in 1-2s!)
    +-- Background refresh task
        |
        +-- Every TTL/2, rebuild and sync to S3
```

#### Existing Code Reuse

| Component | Reuse | Notes |
|-----------|-------|-------|
| All Option A components | 100% | Startup preloading |
| All Option B components | 100% | S3 persistence |
| `S3CacheProvider` | 80% | Existing with extensions |
| `_gid_index_cache` | 100% | Target cache |

**Reuse Percentage**: ~80%

#### New Components Needed

| Component | Effort | Description |
|-----------|--------|-------------|
| All from Option A | 1 day | Startup preloading |
| All from Option B | 3 days | S3 persistence (minus what overlaps) |
| Coordinator logic | 0.5 days | Decision: S3 vs API |

#### Integration Points

```python
# resolver.py - Hybrid loader
async def _load_or_build_index(
    project_gid: str,
    client: AsanaClient,
    s3_cache: S3CacheProvider,
) -> GidLookupIndex:
    """Hybrid: S3 first, then API fallback."""

    # Try S3 cache first
    cached = await s3_cache.get_versioned(
        key=f"gid_index/{project_gid}",
        entry_type=EntryType.DATAFRAME,
    )

    if cached and not cached.is_expired():
        index = GidLookupIndex.deserialize(cached.data)
        logger.info("Loaded index from S3", extra={"project_gid": project_gid})
        return index

    # Fallback: Build from API
    logger.info("Building index from API", extra={"project_gid": project_gid})
    index = await _build_index_from_api(project_gid, client)

    # Persist to S3 for next time
    await _persist_index_to_s3(index, project_gid, s3_cache)

    return index
```

#### Breaking Changes

None. Purely additive.

#### Effort Estimate

| Component | Effort | Confidence | Assumptions |
|-----------|--------|------------|-------------|
| Startup preloading (A) | 1 day | High | Simple |
| S3 persistence (B) | 3 days | Medium | Serialization work |
| Integration/coordination | 1 day | High | Clear logic |
| Testing | 1 day | Medium | S3 mocking patterns exist |
| **Total** | **6 days** | **Medium** | |

#### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| S3 stale on first deploy | Guaranteed | Low | Fallback to API |
| S3 + API both fail | Very Low | High | Log + continue (no index) |
| Complexity increase | Medium | Low | Clear separation of concerns |

---

## Comparison Matrix

| Criteria | Option A | Option B | Option C | Option D | Option E |
|----------|----------|----------|----------|----------|----------|
| **Effort** | 2 days | 4 days | 7.5 days | 7.5 days | 6 days |
| **Confidence** | High | Medium | Low | Low | Medium |
| **Cold Start Time** | 30s | 1-2s (warm) | 30s | 30s | 1-2s (warm) |
| **Code Reuse** | 95% | 75% | 60% | 55% | 80% |
| **Operational Complexity** | Low | Medium | High | High | Medium |
| **Cross-Container Sync** | No | Partial | Yes | Yes | Partial |
| **Rollback Ease** | Easy | Easy | Medium | Medium | Easy |
| **Webhook Reactivity** | No | No | Yes | No | No |

---

## Recommended Approach

### Primary Recommendation: Option A (Startup Preloading)

**Rationale**:
1. **Lowest risk**: 95% code reuse, 2-day implementation
2. **Highest confidence**: Simple integration with existing code
3. **Immediate value**: Solves the problem directly
4. **Clear rollback**: Just remove the startup call

### Secondary Recommendation: Option E (Hybrid) for Phase 2

**Rationale**:
1. **Warm restarts**: S3 persistence enables 1-2s startup after first build
2. **Durability**: Index survives container restarts
3. **Foundation**: Sets up infrastructure for future webhook integration

### Why Not Others

- **Option C (Webhooks)**: Solves a different problem (reactivity) and adds significant complexity
- **Option D (Redis Pub/Sub)**: Overkill for current single-container deployment
- **Option B alone**: Missing the startup preload means first deploy is still slow

---

## Migration Plan

### Phase 1: Immediate Fix (Option A)
**Duration**: 1 week
**Effort**: 2 person-days

1. **Day 1**: Implement `_prefetch_gid_index()` in `main.py`
2. **Day 1**: Update health check to return 503 until index ready
3. **Day 2**: Update ECS task definition (health check grace period)
4. **Day 2**: Deploy to staging, verify <500ms first request

**Rollback Point**: Revert `main.py` changes

### Phase 2: Warm Restart (Option B additions)
**Duration**: 2 weeks
**Effort**: 4 person-days

1. **Week 1**: Implement `GidLookupIndex` serialization
2. **Week 1**: Add S3 load/save for index
3. **Week 2**: Add background refresh task
4. **Week 2**: Deploy to staging, verify 1-2s warm restart

**Rollback Point**: Remove S3 persistence, fall back to API-only

### Phase 3 (Future): Event-Driven Refresh
**Duration**: TBD
**Effort**: TBD

Consider Option C (Webhooks) when:
- Index staleness becomes a user-facing issue
- Real-time data freshness is required
- Cross-container coordination is needed

---

## Success Criteria

### Phase 1 (Option A)
- [ ] First request latency < 500ms after container ready
- [ ] Container starts within ECS health check timeout
- [ ] No increase in Asana API rate limit errors
- [ ] Monitoring shows index build completes at startup

### Phase 2 (Option E)
- [ ] Warm restart latency < 2s
- [ ] S3 index is present after first successful build
- [ ] Background refresh runs without errors
- [ ] Index TTL is respected (no stale data > 1 hour)

---

## Artifact Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| S3CacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Read |
| TieredCacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py` | Read |
| RedisCacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Read |
| Entity Resolver | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Read |
| ProjectDataFrameBuilder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py` | Read |
| WebhooksClient | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py` | Read |
| Spike Document | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-entity-resolver-timeout.md` | Read |
| CacheEntry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py` | Read |
| CacheProvider Protocol | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py` | Read |

---

## Handoff to Prototype Engineer

**Ready for prototyping**: Option A (Startup Preloading)

**POC Scope**:
1. Add `_prefetch_gid_index()` to `main.py` lifespan
2. Add "warming" state to health check
3. Measure startup time and first-request latency

**POC Success Criteria**:
1. Startup completes within 60s
2. First request < 500ms
3. Health check returns 200 only after index ready
4. No regression in subsequent request performance

**Key Files to Modify**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` (make `_get_or_build_index` accessible)

**Risk Areas to Validate**:
- ECS health check timing with 30s index build
- Asana API behavior under startup load
- Error handling if index build fails
