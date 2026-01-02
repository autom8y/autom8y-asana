# PRD: DataFrame Materialization Layer

## Overview

Eliminate DataFrame cold-start latency and inefficient hourly full-rebuild patterns by implementing a centralized Watermark Repository with `modified_since` incremental sync. This architectural change transforms request-time data construction (3-300 seconds) into startup-time preloading with sub-second incremental refreshes.

## Metadata

| Field | Value |
|-------|-------|
| Artifact ID | PRD-materialization-layer |
| Status | Draft |
| Author | Requirements Analyst |
| Created | 2026-01-01 |
| Sprint | sprint-materialization-001 |
| Session | session-20251231-134242-00b4d145 |
| Complexity | Medium-High |
| Upstream | SPIKE-materialization-layer, SPIKE-entity-resolver-timeout |

---

## Problem Statement

The autom8_asana service suffers from two critical performance issues that degrade user experience and waste infrastructure resources:

### Problem 1: Cold-Start Latency (3-300 seconds)

The `_gid_index_cache` starts empty on container boot. The first request to each container triggers a full Asana API fetch, blocking the request for 3-300 seconds depending on project size:

| Project Size | Cold Start Time | Impact |
|--------------|-----------------|--------|
| 100 tasks | 3-5 seconds | Minor UX degradation |
| 1,000 tasks | 22-30 seconds | **Timeout risk** |
| 5,000 tasks | 100-150 seconds | **Request failure** |
| 10,000+ tasks | 200-300 seconds | **Minutes of latency** |

### Problem 2: Inefficient Full Rebuilds (Every Hour)

Every hour on TTL expiry (3600 seconds), the system does a FULL rebuild of all tasks even when only 1 task changed. The `modified_since` parameter exists in `tasks.list_async()` but is currently **unused**.

**Current request flow (problematic)**:
```
POST /v1/resolve/unit
    _get_or_build_index() finds cache MISS or STALE
        _build_dataframe() called
            ProjectDataFrameBuilder.build_with_parallel_fetch_async()
                Fetches ALL sections via Asana API
                Fetches ALL tasks with custom fields
                For 1000+ task project: 30+ seconds
```

### Root Cause

Two distinct architectural gaps:

1. **No startup preloading**: The cache is never pre-populated. Startup discovery only stores project GID mappings, not the actual index data.

2. **No incremental sync**: Despite `modified_since` being available in the Asana API and already included in `_BASE_OPT_FIELDS` (line 39: `"modified_at"`), it is never used for filtering.

### Affected Consumers

All DataFrame consumers suffer from these patterns:

| Consumer | Location | Current Impact |
|----------|----------|----------------|
| Entity Resolver | `services/resolver.py` | 30-300s cold start per entity type |
| Search Service | `services/search.py` | Same full rebuild pattern |
| API Routes | `routes/*.py` | Inherit resolver latency |
| Model Methods | `models/*.py` | Inherit resolver latency |

---

## Background

### Technical Context

The infrastructure for solving this problem is **80% complete**:

| Component | Location | Status |
|-----------|----------|--------|
| `_gid_index_cache` | `services/resolver.py:59` | Exists - module-level cache dict |
| `GidLookupIndex` | `services/gid_lookup.py` | Exists - O(1) phone/vertical lookup |
| `ProjectDataFrameBuilder` | `dataframes/builders/project.py` | Exists - parallel section fetch |
| `modified_since` parameter | `clients/tasks.py:582` | Exists - **UNUSED** |
| `modified_at` in opt_fields | `dataframes/builders/project.py:39` | Exists - already fetched |
| Health check endpoint | `api/routes/health.py` | Exists - needs warming state |
| Lifespan startup | `api/main.py:69-133` | Exists - discovery only, no preload |

### Selected Solution (from Spike)

**Option B + C**: Centralized Watermark Repository + `modified_since` incremental sync with optional S3 baseline persistence for restart resilience.

**Why this solution**:
- Option A (startup only) shifts latency but still does hourly full rebuilds
- Option B fixes both cold-start AND hourly rebuild problems
- Option C adds restart resilience if needed later (~$0.65/month)
- Redis explicitly rejected as overkill (1-2s latency acceptable, sub-millisecond not needed)

---

## User Stories

### US-001: Fast First Request

**As a** service consumer calling the Entity Resolver
**I want** first requests to complete in under 500ms after the container is ready
**So that** I don't experience multi-second or multi-minute delays on new container deployments

**Acceptance Criteria**:
- [ ] Container starts and completes cache warming before accepting requests
- [ ] Health check returns 503 ("warming") until cache is ready
- [ ] Health check returns 200 ("healthy") once cache is populated
- [ ] First request after healthy status completes in <500ms
- [ ] No request ever triggers a cold DataFrame build

**Measurable Targets**:
| Metric | Before | After |
|--------|--------|-------|
| First request latency (1K tasks) | 22-30s | <500ms |
| First request latency (5K tasks) | 100-150s | <500ms |
| First request latency (10K tasks) | 200-300s | <500ms |

### US-002: Efficient Hourly Refresh

**As a** service consumer
**I want** hourly cache refreshes to complete in under 5 seconds
**So that** I don't experience periodic latency spikes when the cache expires

**Acceptance Criteria**:
- [ ] Cache refresh uses `modified_since` parameter to fetch only changed tasks
- [ ] Refresh fetches only tasks modified since last watermark timestamp
- [ ] Refresh merges delta into existing DataFrame (no full rebuild)
- [ ] Refresh completes in <5 seconds for typical workloads (<1% change rate)
- [ ] Asana API calls reduced by 90%+ compared to full rebuild

**Measurable Targets**:
| Metric | Before | After |
|--------|--------|-------|
| Hourly refresh time (1K tasks, 1% changed) | 22-30s | <5s |
| API calls per refresh | 100% of tasks | ~1-5% changed |
| Request latency during refresh | 22-30s spike | <100ms |

### US-003: Centralized Cache Benefit

**As a** developer adding new DataFrame consumers
**I want** all consumers to share the same centralized cache
**So that** I don't need to implement per-consumer caching logic

**Acceptance Criteria**:
- [ ] WatermarkRepository is a singleton accessible to all consumers
- [ ] Entity Resolver uses centralized cache
- [ ] Search Service uses centralized cache
- [ ] New consumers can access cache via standard interface
- [ ] Cache metrics are aggregated across all consumers

### US-004: Operator Visibility

**As a** service operator
**I want** visibility into cache warming status and refresh metrics
**So that** I can monitor service health and troubleshoot issues

**Acceptance Criteria**:
- [ ] Health endpoint includes cache warming status
- [ ] Structured logs emitted for: warming started, warming complete, refresh started, refresh complete
- [ ] Log entries include: project_gid, task_count, duration_ms, strategy (full/incremental)
- [ ] Observable signals defined for alerting thresholds

### US-005: Container Startup Within ECS Timeout

**As a** DevOps engineer
**I want** containers to start within ECS health check timeout (60 seconds)
**So that** deployments succeed without increasing grace period

**Acceptance Criteria**:
- [ ] Container startup (including cache warming) completes in <60 seconds
- [ ] Health check returns 503 until ready (prevents premature traffic)
- [ ] Health check returns 200 when ready (enables traffic routing)
- [ ] ECS task definition does not require extended health check grace period

---

## Functional Requirements

### Must Have

#### FR-001: WatermarkRepository

The system shall implement a centralized `WatermarkRepository` class that tracks per-project sync timestamps:

```python
class WatermarkRepository:
    """Centralized watermark tracking for incremental sync."""

    def get_watermark(self, project_gid: str) -> datetime | None:
        """Get last sync timestamp for project."""

    def set_watermark(self, project_gid: str, timestamp: datetime) -> None:
        """Update watermark after successful sync."""

    def get_all_watermarks(self) -> dict[str, datetime]:
        """Get all watermarks for observability."""
```

**Location**: `src/autom8_asana/dataframes/watermark.py`

**Design constraints**:
- Thread-safe singleton pattern (consistent with existing registries)
- In-memory storage (no external dependencies)
- Global instance accessible via module-level variable or `app.state`

#### FR-002: Incremental DataFrame Refresh

The system shall implement an incremental refresh method in `ProjectDataFrameBuilder`:

```python
async def refresh_incremental(
    self,
    client: AsanaClient,
    watermark: datetime | None,
) -> tuple[pl.DataFrame, datetime]:
    """Fetch only tasks modified since watermark.

    Returns:
        Tuple of (updated DataFrame, new watermark timestamp)
    """
```

**Behavior**:
- If `watermark is None`: Perform full fetch (first sync)
- If `watermark` provided: Fetch only tasks with `modified_since=watermark`
- Merge changed tasks into existing DataFrame
- Return new watermark for next refresh

**API usage**:
```python
modified_tasks = await client.tasks.list_async(
    project_gid=self.project.gid,
    modified_since=watermark.isoformat(),  # Use the existing parameter!
    opt_fields=_BASE_OPT_FIELDS,
).collect()
```

#### FR-003: Startup Preloading

The system shall preload all registered entity project DataFrames at startup before accepting requests:

```python
# In api/main.py lifespan
async def _preload_dataframe_cache(app: FastAPI) -> None:
    """Pre-build GidLookupIndex for all entity types."""
    registry = app.state.entity_project_registry

    for entity_type in registry.get_all_entity_types():
        project_gid = registry.get_project_gid(entity_type)
        # Build and cache index
        await strategy._get_or_build_index(project_gid, client)
```

**Execution order**:
1. `_discover_entity_projects()` - discover project GIDs (existing)
2. `_preload_dataframe_cache()` - warm the cache (new)
3. Set `app.state.cache_ready = True`
4. Yield (container ready)

#### FR-004: Health Check Enhancement

The system shall enhance the health check to return 503 until warming is complete:

```python
@router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    cache_ready = getattr(request.app.state, "cache_ready", False)

    if not cache_ready:
        return JSONResponse(
            content={"status": "warming", "message": "Cache warming in progress"},
            status_code=503,
        )

    return JSONResponse(
        content={"status": "healthy", "version": API_VERSION},
        status_code=200,
    )
```

**Behavior**:
- Before cache ready: Return 503 with `status: "warming"`
- After cache ready: Return 200 with `status: "healthy"`
- ECS/ALB will not route traffic until 200 is returned

#### FR-005: Resolver Integration

The system shall modify `_get_or_build_index()` to use incremental sync:

```python
async def _get_or_build_index(self, project_gid, client):
    from autom8_asana.dataframes.watermark import get_watermark_repo

    watermark_repo = get_watermark_repo()
    cached_index = _gid_index_cache.get(project_gid)
    watermark = watermark_repo.get_watermark(project_gid)

    if cached_index is not None and not cached_index.is_stale(_INDEX_TTL_SECONDS):
        return cached_index  # Cache hit

    # INCREMENTAL refresh instead of full rebuild
    df, new_watermark = await builder.refresh_incremental(client, watermark)

    # Update watermark
    watermark_repo.set_watermark(project_gid, new_watermark)

    # Build and cache index
    index = GidLookupIndex.from_dataframe(df)
    _gid_index_cache[project_gid] = index

    return index
```

#### FR-006: Delta Merge Logic

The system shall implement DataFrame delta merge:

```python
def _merge_deltas(
    self,
    existing_df: pl.DataFrame,
    changed_tasks: list[Task],
) -> pl.DataFrame:
    """Merge changed tasks into existing DataFrame.

    Strategy:
    1. Convert changed tasks to rows
    2. Remove existing rows with matching GIDs
    3. Append changed task rows
    4. Return merged DataFrame
    """
```

**Edge cases**:
- Task deleted: Not tracked by `modified_since` (acceptable staleness)
- Task created: Appears in modified list, appended to DataFrame
- Task updated: Existing row replaced with new data

### Should Have

#### FR-007: S3 Baseline Persistence (Optional Phase 2)

The system should support optional S3 persistence for restart resilience:

```python
class S3BaselinePersistence:
    """Optional S3 persistence for DataFrame state."""

    async def save_baseline(self, project_gid: str, df: pl.DataFrame, watermark: datetime):
        """Persist DataFrame and watermark to S3."""

    async def load_baseline(self, project_gid: str) -> tuple[pl.DataFrame, datetime] | None:
        """Load persisted state from S3."""
```

**Usage pattern**:
1. On startup: Try loading from S3 (1-2s) before full fetch
2. On successful full fetch: Persist to S3 for next restart
3. Cost: ~$0.65/month for storage and requests

#### FR-008: Parallel Entity Preloading

The system should preload multiple entity types concurrently:

```python
async def _preload_dataframe_cache(app: FastAPI) -> None:
    entity_types = registry.get_all_entity_types()

    # Preload all entity types in parallel
    await asyncio.gather(*[
        _preload_entity(entity_type, registry, client)
        for entity_type in entity_types
    ])
```

**Benefit**: Reduce total startup time when multiple entity types are registered.

### Could Have

#### FR-009: Configurable TTL per Entity Type

Allow different refresh intervals per entity type:

```python
TTL_CONFIG = {
    "unit": 3600,      # 1 hour (default)
    "contact": 1800,   # 30 minutes (higher change rate)
    "offer": 7200,     # 2 hours (lower change rate)
}
```

#### FR-010: Cache Warming Progress Reporting

Report detailed warming progress in health check:

```json
{
  "status": "warming",
  "progress": {
    "total_entity_types": 4,
    "completed": 2,
    "current": "offer",
    "elapsed_seconds": 15
  }
}
```

---

## Non-Functional Requirements

### NFR-001: Latency

| Metric | Target | Measurement |
|--------|--------|-------------|
| First request after ready | <500ms | P95 latency |
| Incremental refresh (typical) | <5s | P95 duration |
| Health check response | <10ms | P99 latency |
| Cache lookup | <1ms | P99 latency |

### NFR-002: Resource Efficiency

| Metric | Target | Measurement |
|--------|--------|-------------|
| API call reduction | 90%+ | Calls per hour vs. baseline |
| Memory per project | <10MB | DataFrame + index footprint |
| Startup time | <60s | Total time before ready |

### NFR-003: Reliability

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache hit rate | >99% | After warm-up |
| Refresh success rate | >99.9% | Excluding Asana outages |
| Startup success rate | 100% | After discovery completes |

### NFR-004: Observability

The system shall emit structured logs for:

| Event | Log Level | Required Fields |
|-------|-----------|-----------------|
| `cache_warming_started` | INFO | entity_types, project_count |
| `cache_warming_entity_complete` | INFO | entity_type, project_gid, task_count, duration_ms |
| `cache_warming_complete` | INFO | total_duration_ms, entity_count, task_count |
| `cache_refresh_started` | DEBUG | project_gid, watermark, reason (ttl_expired/manual) |
| `cache_refresh_complete` | INFO | project_gid, changed_count, total_count, duration_ms, strategy |
| `incremental_sync_fallback` | WARN | project_gid, reason, fallback_action |

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| First startup (no watermark) | Full fetch, set initial watermark |
| Asana API timeout during warming | Retry with backoff, fail startup after 3 attempts |
| No tasks modified since watermark | Return existing DataFrame unchanged, update watermark to now |
| Task deleted since last sync | Not detected (acceptable staleness until next full rebuild) |
| Container killed mid-refresh | Next startup will full-rebuild (no partial state) |
| Watermark in future (clock skew) | Log warning, perform full rebuild |
| Zero tasks in project | Return empty DataFrame, set watermark |
| Entity type not registered | Skip preloading, log warning |
| Concurrent refresh requests | Second request waits for first, returns shared result |
| Health check before discovery | Return 503 with "initializing" status |

---

## Success Criteria

### Implementation Complete

- [ ] `WatermarkRepository` class created and tested
- [ ] `refresh_incremental()` method implemented in `ProjectDataFrameBuilder`
- [ ] `_preload_dataframe_cache()` added to startup lifespan
- [ ] Health check returns 503 until cache ready
- [ ] Resolver uses incremental sync for cache refresh
- [ ] Delta merge logic handles create/update cases

### Performance Targets Met

- [ ] First request latency <500ms after container ready
- [ ] Container starts within ECS health check timeout (60s)
- [ ] Hourly refresh completes in <5 seconds
- [ ] Asana API calls reduced by 90%+

### Quality Gates

- [ ] All existing tests pass
- [ ] New tests achieve >90% coverage for materialization components
- [ ] Integration tests verify end-to-end cache warming
- [ ] Load tests confirm latency targets under concurrent load

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Redis hot cache | OVERKILL: 1-2s latency acceptable; sub-millisecond not needed; adds $12+/month |
| Webhook-based sync | Complexity vs. polling benefit; at-most-once delivery adds failure modes |
| Real-time push notifications | Not required by current consumers |
| Multi-container cache sharing | Each container warms independently; acceptable for 1-2 container deployment |
| Task deletion detection | Requires expensive full-scan or separate deletion tracking; acceptable staleness |
| S3 persistence (Phase 1) | Can be added later if restart frequency increases |
| GraphQL subscription | REST polling sufficient for hourly refresh |

---

## Open Questions

*All questions should be resolved before handoff to Architecture.*

**None** - All questions resolved in upstream spike:
- Selected solution: Option B (Watermark + `modified_since`)
- No Redis needed (1-2s latency acceptable)
- S3 baseline deferred to Phase 2 if needed

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `tasks.list_async(modified_since=...)` | Implemented | Parameter exists, currently unused |
| `modified_at` in `_BASE_OPT_FIELDS` | Implemented | Already fetched in task data |
| `_gid_index_cache` | Implemented | Module-level cache in resolver |
| `GidLookupIndex` | Implemented | O(1) lookup structure |
| `EntityProjectRegistry` | Implemented | Startup discovery |
| `ProjectDataFrameBuilder` | Implemented | Parallel fetch |
| Health check endpoint | Implemented | Needs warming state |
| Lifespan startup hook | Implemented | Needs preload step |

---

## Technical References

### Key Code Locations

| Component | Path | Relevance |
|-----------|------|-----------|
| Resolver cache | `services/resolver.py:59` | `_gid_index_cache` dict |
| Index build | `services/resolver.py:413-493` | `_get_or_build_index()` |
| DataFrame build | `services/resolver.py:495-560` | `_build_dataframe()` |
| Parallel fetch | `dataframes/builders/project.py:229-616` | `build_with_parallel_fetch_async()` |
| Tasks API | `clients/tasks.py:574-639` | `list_async()` with `modified_since` |
| Base opt fields | `dataframes/builders/project.py:32-59` | Includes `modified_at` |
| Startup hook | `api/main.py:69-133` | Lifespan with discovery |
| Health check | `api/routes/health.py` | Current implementation |

### API Reference

```python
# Existing API (unused modified_since parameter)
client.tasks.list_async(
    project=project_gid,
    modified_since="2026-01-01T10:30:00Z",  # <-- KEY: Use this!
    opt_fields=_BASE_OPT_FIELDS,
)
```

### Related Documents

| Document | Path |
|----------|------|
| Materialization Spike | `docs/rnd/SPIKE-materialization-layer.md` |
| Entity Resolver Timeout Spike | `docs/spikes/SPIKE-entity-resolver-timeout.md` |
| Entity Resolver PRD | `docs/requirements/PRD-entity-resolver.md` |

---

## Appendix A: Architecture Diagram

### Current State (Problem)

```
Container Start                 Every Hour (TTL Expiry)
    |                                 |
    v                                 v
+----------+                  +-----------------+
| Cache    |                  |  FULL REBUILD   |  <-- 30s-300s
| EMPTY    |                  |  (all tasks)    |      per project
+----+-----+                  +--------+--------+
     |                                 |
     v                                 v
First Request                   Some Unlucky
= FULL BUILD                    Request = SLOW
```

### Target State (Solution)

```
Container Start                 Every Hour (TTL Expiry)
    |                                 |
    v                                 v
+-------------------+         +-------------------+
| PRELOAD           |         | INCREMENTAL SYNC  |
| (during startup)  |         | modified_since    |
+--------+----------+         +---------+---------+
         |                              |
         v                              v
    Health: 503              Only fetch changed
    "warming"                tasks (1-5% of total)
         |                              |
         v                              v
    Health: 200              Merge into existing
    "healthy"                DataFrame (<5s)
         |
         v
    First Request
    <500ms
```

---

## Appendix B: Metrics Dashboard

### Observable Signals

| Signal | Threshold | Action |
|--------|-----------|--------|
| Task count | >500K | Scale optimization (partitioning) |
| Incremental refresh time P95 | >10s | Investigate watermark gaps |
| `modified_since` miss rate | >10% | Check watermark persistence |
| User staleness complaints | >3/month | Consider webhooks or shorter TTL |
| Asana API announcements | Streaming/GraphQL | Evaluate early adoption |
| Startup time P95 | >45s | Optimize parallel preloading |
| Cache hit rate | <95% | Investigate TTL configuration |

### Expected Metrics (Post-Implementation)

| Metric | Before | After |
|--------|--------|-------|
| Cold start (first request) | 30s-300s | 0ms (preloaded) |
| Hourly refresh | 30s-300s FULL | 1-5s INCREMENTAL |
| API calls per refresh | 100% tasks | ~1-5% changed |
| Affected consumers | All services | All services benefit |
| Monthly cost | $0 | $0 |
| Effort | - | 3-4 days |

---

## Appendix C: Implementation Plan

### Phase 1: Core Implementation (3-4 days)

| Day | Task | Owner |
|-----|------|-------|
| 1 | Create `WatermarkRepository` class | Engineer |
| 1 | Add startup preloading to `main.py` | Engineer |
| 2 | Implement `refresh_incremental()` in builder | Engineer |
| 2 | Add delta merge logic for DataFrames | Engineer |
| 3 | Wire incremental sync into resolver | Engineer |
| 3 | Update health check for "warming" state | Engineer |
| 4 | Testing, deployment to staging | QA |
| 4 | Deploy to production | DevOps |

### Rollback Plan

Remove watermark usage, revert to full rebuild (2-way door). Changes are additive and backward compatible.

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-01 | 1.0 | Requirements Analyst | Initial PRD |
