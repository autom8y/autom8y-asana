# SPIKE: Entity Resolver Timeout Investigation

**Date**: 2026-01-01
**Status**: Complete
**Author**: Architect (spike investigation)

## Executive Summary

The Entity Resolver is timing out (>30s) because the `GidLookupIndex` is built **on every request** rather than at startup. Despite having a module-level cache (`_gid_index_cache`), the cache starts empty on each container instance, and the first request triggers a full DataFrame build from Asana API.

**Root Cause**: Request-time DataFrame construction instead of startup-time index population.

**Impact**: First request to each container takes 30+ seconds; subsequent requests are fast (<10ms).

---

## Investigation Findings

### 1. Architecture Analysis

#### Expected Architecture (Per TDD)
```
┌─────────────────────────────────────────────────────────────────┐
│                        STARTUP                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. Discover project GIDs (EntityProjectRegistry)               │
│  2. Fetch all tasks from Unit project via Asana API             │
│  3. Build DataFrame from tasks                                  │
│  4. Build GidLookupIndex from DataFrame                         │
│  5. Cache index in _gid_index_cache                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        REQUEST TIME                             │
├─────────────────────────────────────────────────────────────────┤
│  1. Get cached GidLookupIndex (O(1))                            │
│  2. Lookup phone/vertical -> GID (O(1))                         │
│  3. Return result (<10ms)                                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Actual Architecture (Current Implementation)
```
┌─────────────────────────────────────────────────────────────────┐
│                        STARTUP                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. Discover project GIDs (EntityProjectRegistry)               │
│  2. Store registry in app.state                                 │
│  3. *** INDEX NOT BUILT ***                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIRST REQUEST (SLOW)                         │
├─────────────────────────────────────────────────────────────────┤
│  1. _get_or_build_index() finds cache MISS                      │
│  2. _build_dataframe() called                                   │
│  3. ProjectDataFrameBuilder.build_with_parallel_fetch_async()   │
│     - Fetches ALL sections via Asana API                        │
│     - Fetches ALL tasks with custom fields                      │
│     - For 1000+ task project: 30+ seconds                       │
│  4. GidLookupIndex.from_dataframe() builds index                │
│  5. Cache index in _gid_index_cache                             │
│  6. Perform lookup (finally)                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SUBSEQUENT REQUESTS (FAST)                      │
├─────────────────────────────────────────────────────────────────┤
│  1. _get_or_build_index() finds cache HIT                       │
│  2. Perform lookup (O(1))                                       │
│  3. Return result (<10ms)                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Code Evidence

#### resolver.py - Cache Miss on First Request (lines 430-456)
```python
async def _get_or_build_index(
    self,
    project_gid: str,
    client: "AsanaClient",
) -> GidLookupIndex | None:
    global _gid_index_cache

    # Check for cached index
    cached_index = _gid_index_cache.get(project_gid)

    if cached_index is not None and not cached_index.is_stale(_INDEX_TTL_SECONDS):
        # CACHE HIT - fast path
        return cached_index

    # CACHE MISS - triggers full DataFrame build
    df = await self._build_dataframe(project_gid, client)
    # ... builds index from DataFrame
```

**Problem**: `_gid_index_cache` is an empty module-level dict. On container startup, it has no entries. The first request triggers the expensive `_build_dataframe()` path.

#### resolver.py - DataFrame Building (lines 495-560)
```python
async def _build_dataframe(
    self,
    project_gid: str,
    client: "AsanaClient",
) -> Any:
    # ... imports ProjectDataFrameBuilder

    builder = ProjectDataFrameBuilder(
        project=project_proxy,
        task_type="Unit",
        schema=UNIT_SCHEMA,
        resolver=resolver,
    )

    # This fetches ALL tasks from Asana API
    df = await builder.build_with_parallel_fetch_async(client)
```

**Problem**: `build_with_parallel_fetch_async()` makes multiple Asana API calls:
1. List all sections in project
2. For each section, list all task GIDs
3. Fetch full task details for all tasks (with custom fields)

For a project with 1000+ tasks across multiple sections, this easily takes 30+ seconds.

#### main.py - Startup Discovery Does NOT Build Index (lines 135-246)
```python
async def _discover_entity_projects(app: FastAPI) -> None:
    # ... discovers project GIDs

    for entity_type, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            project_gid = workspace_registry.get_by_name(pattern)
            if project_gid:
                entity_registry.register(
                    entity_type=entity_type,
                    project_gid=project_gid,  # Only stores the GID
                    project_name=pattern,
                )

    # Store registry in app.state
    app.state.entity_project_registry = entity_registry

    # *** NO INDEX BUILDING HERE ***
```

**Problem**: Startup only stores project GIDs in the registry. It does NOT:
- Fetch the tasks
- Build the DataFrame
- Build the GidLookupIndex
- Populate `_gid_index_cache`

### 3. Performance Breakdown

For a Unit project with ~1000 tasks:

| Operation | Time | When |
|-----------|------|------|
| Startup: Project discovery | ~2s | Container boot |
| First request: Section enumeration | ~1s | Request |
| First request: Task GID enumeration | ~3s | Request |
| First request: Task detail fetch (1000 tasks) | ~25s | Request |
| First request: DataFrame construction | ~0.5s | Request |
| First request: Index building | ~0.1s | Request |
| First request: Lookup | <1ms | Request |
| **First request total** | **~30s** | |
| Subsequent request: Cached lookup | <10ms | Request |

### 4. Why This Wasn't Caught

1. **Local testing**: Developers likely tested with small projects (<100 tasks) where the DataFrame build is fast
2. **Warm cache illusion**: After the first slow request, all subsequent requests are fast
3. **Deployment pattern**: Fresh container deployments always start with cold cache
4. **Load balancer**: Multiple containers mean multiple cold-start events

---

## Root Cause Summary

**The cache exists but is never pre-populated.**

The `_gid_index_cache` module-level dictionary is intended to cache the `GidLookupIndex` for 1 hour (TTL). However:

1. On container startup, the cache is empty
2. Startup discovery only stores project GID mappings, not the actual index
3. The first request to hit each container triggers a full Asana API fetch

This creates a "cold start" penalty of 30+ seconds for the first request to each new container.

---

## Recommendations

### Option A: Startup Index Pre-population (Recommended)

Add index building to `_discover_entity_projects()` in `main.py`:

```python
async def _discover_entity_projects(app: FastAPI) -> None:
    # ... existing discovery code ...

    # NEW: Pre-build GidLookupIndex for Unit entity type
    unit_gid = entity_registry.get_project_gid("unit")
    if unit_gid:
        logger.info("Pre-building GidLookupIndex for unit project")
        strategy = get_strategy("unit")
        await strategy._get_or_build_index(unit_gid, client)
        logger.info("GidLookupIndex pre-built successfully")
```

**Pros:**
- Moves slow operation to startup (acceptable for ECS task startup)
- Requests are always fast
- Simple implementation

**Cons:**
- Increases container startup time by ~30s
- May hit ECS health check timeout (configure grace period)

### Option B: Background Index Refresh

Start a background task that builds the index after startup completes:

```python
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ... existing startup ...

    # Start background index builder
    asyncio.create_task(_background_index_builder(app))

    yield

    # ... shutdown ...
```

**Pros:**
- Container starts quickly
- Index builds in background
- First requests may hit warm cache if build completes

**Cons:**
- Race condition: early requests still hit cold cache
- More complex error handling

### Option C: Hybrid Approach (Best)

Combine startup pre-population with shorter health check:

1. Pre-build index at startup
2. Configure ECS health check grace period to 60s
3. Use `/health` endpoint that returns 503 until index is ready

```python
@router.get("/health")
async def health_check(request: Request):
    registry = request.app.state.entity_project_registry
    if not _gid_index_cache:  # Index not yet built
        return JSONResponse(
            status_code=503,
            content={"status": "warming", "message": "Index building"}
        )
    return {"status": "healthy"}
```

**Pros:**
- Requests always fast once healthy
- Load balancer only routes to warm containers
- Clear operational semantics

**Cons:**
- Requires ECS/ALB configuration changes

---

## Performance Targets

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Cold start (first request) | 30+ seconds | <500ms | Pre-populated index |
| Warm request | <10ms | <10ms | Already meeting target |
| Index build time (startup) | N/A | <45s | Acceptable for startup |
| Index memory footprint | ~1MB | <5MB | 1000 entries @ ~1KB each |
| Index TTL | 1 hour | 1 hour | Keep current setting |

---

## Implementation Priority

1. **P0 (Immediate)**: Implement Option A - move index build to startup
2. **P1 (Short-term)**: Update ECS health check configuration
3. **P2 (Medium-term)**: Add observability for index build timing
4. **P3 (Long-term)**: Consider Option C for zero-downtime deployments

---

## Files to Modify

| File | Change |
|------|--------|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Add index pre-population to `_discover_entity_projects()` |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Make `_get_or_build_index` public or add wrapper |
| ECS Task Definition | Increase health check grace period |
| ALB Target Group | Configure deregistration delay |

---

## Verification Plan

1. Deploy fix to staging
2. Restart container and measure startup time
3. Immediately hit `/v1/resolve/unit` endpoint
4. Verify response time <500ms
5. Check logs for "Pre-building GidLookupIndex" message
6. Monitor ECS health check status during startup

---

## Appendix: Relevant Code Paths

### Request Flow (Current)
```
POST /v1/resolve/unit
    └── resolve_entities() [routes/resolver.py:247]
        └── strategy.resolve() [resolver.py:305]
            └── _get_or_build_index() [resolver.py:413]
                └── _build_dataframe() [resolver.py:495]  ← SLOW
                    └── ProjectDataFrameBuilder.build_with_parallel_fetch_async()
                        └── ParallelSectionFetcher.fetch_all() ← MANY API CALLS
```

### Cache Location
```
Module: autom8_asana.services.resolver
Variable: _gid_index_cache (dict[str, GidLookupIndex])
Scope: Module-level (process-lifetime)
TTL: 3600 seconds (1 hour)
```
