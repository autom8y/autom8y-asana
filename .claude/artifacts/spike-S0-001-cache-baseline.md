# Spike S0-001: Cache Instrumentation Baseline

**Date**: 2026-02-04
**Objective**: Establish baseline understanding of cache behavior before building Unified Cache Invalidation Pipeline (Opportunity A1)
**Scope**: Read-only analysis -- no production code changes

---

## 1. Cache Architecture Summary

The system implements **two independent caching subsystems** operating at different abstraction levels, with limited cross-tier coordination.

### 1.1 Task-Level Cache (UnifiedTaskStore)

**Location**: `src/autom8_asana/cache/unified.py`
**Storage**: TieredCacheProvider (Redis hot + S3 cold)
**Entry Type**: `CacheEntry` (frozen dataclass in `cache/entry.py`)

```
Client Request
    |
    v
UnifiedTaskStore
    |-- FreshnessCoordinator (batch modified_at checks via Asana Batch API)
    |-- HierarchyIndex (parent-child relationship tracking, wraps autom8y_cache.HierarchyTracker)
    |-- CompletenessLevel tracking (UNKNOWN < MINIMAL < STANDARD < FULL)
    |
    v
TieredCacheProvider (cache/tiered.py)
    |-- Hot Tier: RedisCacheProvider (cache/backends/redis.py)
    |       Key pattern: asana:tasks:{gid}:{entry_type}
    |       Eviction: TTL-based (default 300s), configurable per EntryType
    |
    |-- Cold Tier: S3CacheProvider (cache/backends/s3.py) [feature-flagged]
    |       Strategy: Write-through on set, cache-aside with promotion on get
    |       Promotion TTL: 3600s (1 hour)
    |
    |-- Fallback: EnhancedInMemoryCacheProvider (cache/backends/memory.py)
            Strategy: LRU eviction at max_size, TTL-based expiration
```

**Entry Types** (from `cache/entry.py`): TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DATAFRAME, PROJECT, SECTION, USER, CUSTOM_FIELD, DETECTION, PROJECT_SECTIONS, GID_ENUMERATION, INSIGHTS

**Freshness Modes** (two separate enums exist):
- `cache/freshness.py` -- Freshness enum (STRICT, EVENTUAL, IMMEDIATE) used by task-level staleness
- `cache/freshness_coordinator.py` -- FreshnessMode enum (STRICT, EVENTUAL, IMMEDIATE) used by UnifiedTaskStore

**Eviction Policies**:
- Redis: TTL-based. Default 300s. Per-entity overrides in `config.py`:
  - business: 3600s, contact: 900s, unit: 900s (others defined in DEFAULT_ENTITY_TTLS)
- S3: No eviction. Entries are overwritten on next write, not explicitly deleted
- Memory backend: LRU + TTL. Max 10,000 entries

### 1.2 DataFrame-Level Cache (DataFrameCache)

**Location**: `src/autom8_asana/cache/dataframe_cache.py`
**Storage**: Memory tier + Progressive tier (S3 via SectionPersistence)
**Entry Type**: `dataframe_cache.CacheEntry` (separate from task-level CacheEntry)

```
Resolution/Query Request
    |
    v
DataFrameCache (dataframe_cache.py)
    |-- MemoryTier (cache/dataframe/tiers/memory.py)
    |       Strategy: LRU + heap-based limits (max_heap_percent)
    |       Container-aware: reads cgroup memory limits
    |
    |-- ProgressiveTier (cache/dataframe/tiers/progressive.py)
    |       Storage: S3 via SectionPersistence
    |       Source of truth: writes go here first
    |
    |-- DataFrameCacheCoalescer (cache/dataframe/coalescer.py)
    |       Prevents thundering herd on concurrent builds
    |
    |-- CircuitBreaker (cache/dataframe/circuit_breaker.py)
    |       Per-project failure isolation
    |       LKG fallback when circuit is open
```

**Freshness Model** (5-state, entity-aware):
- `FRESH`: Within entity TTL. Serve immediately.
- `STALE_SERVABLE`: Past TTL, within SWR grace window (TTL * SWR_GRACE_MULTIPLIER=3.0). Serve stale, trigger background refresh.
- `EXPIRED_SERVABLE`: Beyond grace, schema/watermark valid (LKG). Serve with warning if under LKG_MAX_STALENESS_MULTIPLIER limit.
- `SCHEMA_MISMATCH`: Hard reject. Schema version changed.
- `WATERMARK_STALE`: Hard reject. Source has newer data (watermark comparison).

**Build Trigger**: `@dataframe_cache` decorator (cache/dataframe/decorator.py) wraps strategy resolve() methods. Returns 503 on cache miss while build runs.

**Warming**: Lambda handler (`lambda_handlers/cache_warmer.py`) pre-populates DataFrames for known projects. Emits CloudWatch metrics.

### 1.3 Additional Cache Layers

| Layer | Location | Purpose |
|-------|----------|---------|
| DynamicIndexCache | `services/dynamic_index.py` | In-memory index of DataFrame columns for O(1) lookups. TTL 3600s, max 5 per entity type. |
| StalenessCheckCoordinator | `cache/staleness_coordinator.py` | Legacy: coordinates lightweight modified_at checks with progressive TTL extension. Separate from FreshnessCoordinator. |
| CacheInvalidator (persistence) | `persistence/cache_invalidator.py` | Invalidates task + DataFrame caches after SaveSession commits |
| Lambda cache_invalidate | `lambda_handlers/cache_invalidate.py` | Bulk invalidation via Lambda (clears Redis + S3) |

### 1.4 Invalidation Paths

**Currently implemented**:
1. **SaveSession commit** -> `CacheInvalidator.invalidate_for_commit()` -> task cache + DataFrame cache
2. **Schema version bump** -> `DataFrameCache.invalidate_on_schema_change()` -> memory tier clear
3. **Manual/Lambda** -> `cache_invalidate.handler` -> Redis clear_all_tasks + optional DataFrame clear
4. **TTL expiration** -> passive, on next read

**NOT implemented (the A1 gap)**:
- REST API mutations (`PUT /tasks/{gid}`) do NOT trigger cache invalidation
- Task-level staleness detection does NOT propagate to DataFrame cache
- Section DataFrames in S3 are never invalidated when constituent tasks change
- No webhook-driven invalidation path exists

---

## 2. Current Instrumentation

### 2.1 Task-Level Cache Metrics

**UnifiedTaskStore._stats** (in-memory dict, `unified.py` line 91-99):
```python
{
    "get_hits": 0,
    "get_misses": 0,
    "put_count": 0,
    "invalidate_count": 0,
    "parent_chain_lookups": 0,
    "completeness_misses": 0,
    "upgrade_count": 0,
}
```
Accessible via `get_stats()` / `reset_stats()`. Not exported to any monitoring system.

**FreshnessCoordinator._stats** (`freshness_coordinator.py` line 100-107):
```python
{
    "total_checks": 0,
    "api_calls": 0,
    "fresh_count": 0,
    "stale_count": 0,
    "error_count": 0,
    "immediate_returns": 0,
}
```
Accessible via `get_stats()`. Not exported externally.

**CacheMetrics** (`cache/metrics.py`):
- Thread-safe aggregator with: hits, misses, writes, evictions, errors, promotions, incremental_fetches, full_fetches, overflow_skips
- Supports `on_event()` callbacks for external integration
- `snapshot()` returns all metrics as dict including computed hit_rate and average_latency_ms
- Used by Redis backend, S3 backend, and TieredCacheProvider
- **Integration**: `cache/events.py` provides `create_metrics_callback()` to route CacheEvent to CacheLoggingProvider (ADR-0023)

**StalenessCheckCoordinator._stats** (`staleness_coordinator.py` line 74):
- Separate stats dict (checks, extensions, fetches, errors). Not exported.

### 2.2 DataFrame-Level Cache Metrics

**DataFrameCache._stats** per entity type (`dataframe_cache.py` lines 208-221):
```python
{
    "memory_hits": 0,
    "memory_misses": 0,
    "s3_hits": 0,
    "s3_misses": 0,
    "builds_triggered": 0,
    "builds_coalesced": 0,
    "circuit_breaks": 0,
    "invalidations": 0,
    "swr_serves": 0,
    "swr_refreshes_triggered": 0,
    "lkg_serves": 0,
    "lkg_circuit_serves": 0,
}
```
Accessible via `get_stats()`. Not exported to CloudWatch or any monitoring system.

**FreshnessInfo** side-channel (`dataframe_cache.py` line 40-50):
- `freshness` (status string), `data_age_seconds`, `staleness_ratio`
- Stored per cache key in `_last_freshness` dict
- Designed for API response headers but unclear if actually surfaced

### 2.3 Structured Logging

Extensive structured logging exists throughout, using `autom8y_log.get_logger()`:

| Log Event | Location | Level | Key Extra Fields |
|-----------|----------|-------|------------------|
| `cache_completeness_insufficient` | unified.py | DEBUG | gid, cached_level, required_level |
| `unified_store_put` | unified.py | DEBUG | gid, has_parent, ttl, completeness_level |
| `unified_store_put_batch` | unified.py | DEBUG | task_count, cached_count, warm_hierarchy |
| `unified_store_cascade_invalidate` | unified.py | DEBUG | gid, descendant_count |
| `cache_entry_upgraded` | unified.py | INFO | gid, target_level |
| `dataframe_cache_*_hit` | dataframe_cache.py | DEBUG | project_gid, entity_type, row_count |
| `dataframe_cache_*_swr_serve` | dataframe_cache.py | INFO | project_gid, entity_type, age_seconds |
| `dataframe_cache_*_lkg_serve` | dataframe_cache.py | WARNING | project_gid, entity_type, age_seconds |
| `dataframe_cache_put` | dataframe_cache.py | INFO | project_gid, entity_type, row_count, watermark |
| `dataframe_cache_circuit_open` | dataframe_cache.py | WARNING | project_gid, entity_type |
| `swr_refresh_triggered` | dataframe_cache.py | INFO | project_gid, entity_type |
| `freshness_check_batch_failure` | freshness_coordinator.py | WARNING | chunk_size, error_type |
| `cache_invalidation_complete` | cache_invalidator.py | DEBUG | invalidated_count |
| `s3_write_through_failed` | tiered.py | WARNING | key, entry_type, error |

### 2.4 External Monitoring

- **CloudWatch**: Only the cache warmer Lambda (`lambda_handlers/cache_warmer.py`) emits CloudWatch metrics
- **CacheLoggingProvider**: ADR-0023 integration exists (`cache/events.py`) but routes to structured logging, not CloudWatch/DataDog
- **No Prometheus/StatsD/DataDog integration** found in the codebase

---

## 3. Identified Gaps

### 3.1 Missing Measurements

| Gap | Description | Impact |
|-----|-------------|--------|
| **G1: No runtime metric export** | UnifiedTaskStore, FreshnessCoordinator, DataFrameCache stats are in-memory dicts never emitted to CloudWatch/monitoring | Cannot measure cache effectiveness in production. No alerting on degradation. |
| **G2: No per-request cache timing** | `CacheMetrics` tracks average latency but no p50/p95/p99 distribution | Cannot identify latency spikes or tail latencies |
| **G3: No cross-tier correlation** | Task cache hits/misses are not correlated with DataFrame cache behavior | Cannot trace a stale DataFrame back to which constituent tasks changed |
| **G4: No staleness duration tracking** | We know IF something is stale but not HOW LONG it was stale before detection | Cannot measure staleness exposure window |
| **G5: No invalidation latency** | Time from mutation to invalidation is not measured | Cannot set SLOs for data freshness |
| **G6: No build duration tracking** | DataFrame build times (progressive builder) are not captured in cache stats | Cannot optimize or set timeouts for builds |
| **G7: No SWR effectiveness** | SWR refresh count is tracked but success/failure and refresh latency are not | Cannot tell if SWR is actually keeping data fresh |
| **G8: No memory tier utilization** | MemoryTier tracks entries but not bytes, heap percentage utilization, or eviction pressure | Cannot size memory tier appropriately |
| **G9: No DynamicIndex hit rates** | DynamicIndexCache has no stats at all | Cannot measure index reuse vs rebuild frequency |
| **G10: No watermark age distribution** | DataFrame watermarks are stored but age distribution is never computed | Cannot tell how fresh cached DataFrames actually are across the fleet |

### 3.2 Missing Invalidation Instrumentation

| Gap | Description |
|-----|-------------|
| **I1: No mutation-to-serve latency** | Cannot measure time between an Asana task change and when the cache serves updated data |
| **I2: No cascade invalidation tracking** | `UnifiedTaskStore.invalidate(cascade=True)` counts descendants but does not track which DataFrames were affected |
| **I3: No invalidation failure tracking** | `CacheInvalidator` swallows errors; no counter for failed invalidations |
| **I4: No REST mutation tracking** | API PUT/POST/DELETE operations do not record which cache entries they should have invalidated |

---

## 4. Staleness Vectors

These are code paths where cached data can become stale without the system detecting or acting on it.

### Vector S1: REST API Mutations (CRITICAL -- the A1 gap)

**Path**: `api/routes/tasks.py` PUT/POST handlers -> Asana API -> success response
**Problem**: Cache entries for the mutated task remain in Redis/S3 with old `modified_at`. No invalidation call is made. Next read returns stale data until TTL expires.
**Staleness Window**: Up to TTL (300s for tasks, 3600s for business entities). With SWR grace (3x), a business entity could serve stale data for up to 3 hours.
**Affected Entries**: TASK, SUBTASKS, DEPENDENCIES, DETECTION

### Vector S2: DataFrame Isolation from Task Changes (CRITICAL)

**Path**: Task is updated (via any path) -> task cache is invalidated or expires -> DataFrameCache still holds old DataFrame
**Problem**: DataFrameCache freshness is based on its own TTL/watermark, which is the max(modified_at) from build time. It never checks if constituent tasks have been updated since build.
**Staleness Window**: Entity TTL (900s for unit/contact, 3600s for business) + SWR grace (3x) = up to 4500s (1.25 hours) for units, up to 10800s (3 hours) for business.
**Affected Entries**: All DATAFRAME type entries; DynamicIndex entries that were built from stale DataFrames

### Vector S3: Hierarchy Chain Staleness

**Path**: Parent task updated -> child tasks' cascade-resolved fields become stale -> child DataFrame rows have wrong inherited values
**Problem**: `UnifiedTaskStore.invalidate(cascade=True)` only invalidates task cache entries. It does not invalidate DataFrames that include the child tasks. The HierarchyIndex tracks relationships but is not consulted during DataFrame invalidation.
**Staleness Window**: Same as S2, but the trigger is a parent change (harder to detect since child modified_at does not change).

### Vector S4: Completeness Level Mismatch Silent Serve

**Path**: Task cached at MINIMAL level -> reader requests STANDARD -> returns None -> fallback to legacy strategy -> builds DataFrame from API -> caches DataFrame -> original MINIMAL entry still in task cache
**Problem**: The MINIMAL task cache entry is never upgraded or invalidated. Future task-level reads that request MINIMAL will return the stale MINIMAL data even if the full data has changed.
**Staleness Window**: TTL-based, but the MINIMAL entry may mask changes detected at STANDARD level.

### Vector S5: S3 Cold Tier Stale Promotion

**Path**: Entry written to Redis + S3 -> Redis entry expires (TTL) -> S3 entry has no TTL -> next read promotes S3 entry back to Redis with `promotion_ttl=3600s`
**Problem**: The promoted entry may have been stale for an arbitrary amount of time in S3. Promotion resets `cached_at` but preserves the original `version` (modified_at). Staleness is only detected if FreshnessMode is STRICT (which requires an API call).
**Staleness Window**: Potentially unbounded. S3 entries have no eviction policy.

### Vector S6: DynamicIndex Stale-After-DataFrame-Rebuild

**Path**: DataFrame is rebuilt with new data -> new DataFrame stored in cache -> DynamicIndex built from old DataFrame is still in DynamicIndexCache (TTL 3600s)
**Problem**: `DynamicIndexCache` entries are keyed by (entity_type, key_columns) with a 3600s TTL. When a DataFrame is rebuilt, stale DynamicIndex entries are not invalidated.
**Staleness Window**: Up to 3600s after DataFrame rebuild.

### Vector S7: SWR Background Refresh Failure

**Path**: Entry past TTL -> SWR serves stale -> triggers background refresh -> refresh fails -> no retry
**Problem**: `_swr_refresh_async()` records circuit breaker failure but does not retry. The stale entry continues to be served. If LKG_MAX_STALENESS_MULTIPLIER is 0.0 (current default), it serves forever.
**Staleness Window**: Unbounded when refresh keeps failing and LKG_MAX_STALENESS_MULTIPLIER=0.0.

### Vector S8: Concurrent Build Race

**Path**: Two requests for same (project_gid, entity_type) -> both check cache -> both miss -> coalescer lets one build -> second waits -> first builds with data at T1 -> between T1 and cache write, task changes at T2 -> cached DataFrame reflects T1, not T2
**Problem**: Normal race condition. The built DataFrame is stale from the moment it is written. This is expected behavior, but with no instrumentation there is no way to measure how often this occurs.
**Staleness Window**: Duration of build + propagation delay.

---

## 5. Recommendations for Instrumentation Additions (Pre-Sprint 1)

These additions should be made before building the Unified Cache Invalidation Pipeline to establish baselines and enable before/after comparison.

### Priority 1: Metric Export (addresses G1, G2)

**Add CloudWatch metric emission** from existing in-memory stats. The infrastructure pattern already exists in `cache_warmer.py`.

Recommended metrics to emit (per entity type where applicable):
- `cache.task.hit_rate` (gauge, from UnifiedTaskStore._stats)
- `cache.task.completeness_misses` (counter)
- `cache.dataframe.hit_rate` (gauge, per entity type from DataFrameCache._stats)
- `cache.dataframe.swr_serves` (counter)
- `cache.dataframe.lkg_serves` (counter)
- `cache.dataframe.circuit_breaks` (counter)
- `cache.dataframe.build_duration_ms` (timer -- needs new instrumentation in builder)
- `cache.freshness.api_calls` (counter, from FreshnessCoordinator._stats)
- `cache.freshness.stale_detected` (counter)
- `cache.tiered.promotions` (counter, from TieredCacheProvider._metrics)

**Implementation**: Create a `cache/metric_exporter.py` module with a periodic flush (e.g., every 60s) or on-demand snapshot that calls CloudWatch PutMetricData. Register as CacheMetrics callback via `on_event()`.

### Priority 2: Staleness Duration Tracking (addresses G4, G5, I1)

**Add timestamp tracking** at invalidation boundaries:
- Record `last_mutated_at` when a mutation occurs (REST API or SaveSession)
- On next cache read that detects staleness, compute `staleness_duration = detection_time - last_mutated_at`
- Emit as `cache.staleness_duration_seconds` histogram

This is the single most important metric for the A1 initiative: it quantifies the problem.

### Priority 3: REST Mutation Cache Impact Logging (addresses I4, S1)

**Add structured log event** to REST API mutation handlers:
```python
logger.info("rest_mutation_cache_impact", extra={
    "task_gid": gid,
    "mutation_type": "update",
    "cache_entry_exists": bool(cache.get_versioned(gid, EntryType.TASK)),
    "entry_age_seconds": age_if_cached,
})
```

This quantifies how often REST mutations leave stale cache entries (the primary A1 gap).

### Priority 4: DataFrame Build Timing (addresses G6)

**Wrap ProgressiveProjectBuilder.build_progressive_async()** with timing:
- Start timer before build
- Record duration, row count, sections fetched, sections failed
- Emit as `cache.dataframe.build_duration_ms` with entity_type dimension

### Priority 5: Cross-Tier Correlation ID (addresses G3)

**Propagate a correlation_id** through cache operations:
- CacheMetrics already supports `correlation_id` on every record method
- Generate a request-scoped ID in API middleware
- Pass through UnifiedTaskStore -> TieredCacheProvider -> DataFrameCache
- Enables log correlation: "request X hit task cache but missed DataFrame cache"

### Priority 6: DynamicIndex Stats (addresses G9)

**Add basic stats to DynamicIndexCache**:
- `index_hits`, `index_misses`, `index_rebuilds`
- Log on build: entity_type, key_columns, row_count, build_duration_ms

---

## Appendix A: File Reference

| File | Role |
|------|------|
| `src/autom8_asana/cache/unified.py` | UnifiedTaskStore -- single source of truth for task data |
| `src/autom8_asana/cache/dataframe_cache.py` | DataFrameCache -- tiered DataFrame caching with SWR |
| `src/autom8_asana/cache/tiered.py` | TieredCacheProvider -- Redis + S3 coordination |
| `src/autom8_asana/cache/backends/redis.py` | RedisCacheProvider -- hot tier |
| `src/autom8_asana/cache/backends/s3.py` | S3CacheProvider -- cold tier |
| `src/autom8_asana/cache/backends/memory.py` | EnhancedInMemoryCacheProvider -- in-process fallback |
| `src/autom8_asana/cache/freshness.py` | Freshness enum (STRICT/EVENTUAL/IMMEDIATE) |
| `src/autom8_asana/cache/freshness_coordinator.py` | FreshnessCoordinator -- batch staleness checks |
| `src/autom8_asana/cache/staleness.py` | Staleness detection helpers |
| `src/autom8_asana/cache/staleness_coordinator.py` | StalenessCheckCoordinator -- legacy lightweight checks |
| `src/autom8_asana/cache/entry.py` | CacheEntry + EntryType definitions |
| `src/autom8_asana/cache/versioning.py` | Version comparison utilities |
| `src/autom8_asana/cache/metrics.py` | CacheMetrics aggregator with callback support |
| `src/autom8_asana/cache/events.py` | CacheEvent -> LogProvider bridge |
| `src/autom8_asana/cache/completeness.py` | Completeness level tracking |
| `src/autom8_asana/cache/hierarchy.py` | HierarchyIndex for parent-child relationships |
| `src/autom8_asana/cache/dataframe/tiers/memory.py` | MemoryTier with heap-based limits |
| `src/autom8_asana/cache/dataframe/tiers/progressive.py` | ProgressiveTier (S3 via SectionPersistence) |
| `src/autom8_asana/cache/dataframe/coalescer.py` | Build deduplication |
| `src/autom8_asana/cache/dataframe/circuit_breaker.py` | Per-project failure isolation |
| `src/autom8_asana/cache/dataframe/decorator.py` | @dataframe_cache class decorator |
| `src/autom8_asana/persistence/cache_invalidator.py` | CacheInvalidator for SaveSession commits |
| `src/autom8_asana/lambda_handlers/cache_invalidate.py` | Lambda: bulk cache invalidation |
| `src/autom8_asana/lambda_handlers/cache_warmer.py` | Lambda: pre-deployment cache warming |
| `src/autom8_asana/services/universal_strategy.py` | UniversalResolutionStrategy -- DataFrame consumer |
| `src/autom8_asana/config.py` | DEFAULT_TTL, DEFAULT_ENTITY_TTLS, SWR_GRACE_MULTIPLIER |

## Appendix B: Key Configuration Values

| Parameter | Value | Location |
|-----------|-------|----------|
| DEFAULT_TTL | 300s (5 min) | config.py |
| business TTL | 3600s (1 hr) | config.py DEFAULT_ENTITY_TTLS |
| contact TTL | 900s (15 min) | config.py DEFAULT_ENTITY_TTLS |
| unit TTL | 900s (15 min) | config.py DEFAULT_ENTITY_TTLS |
| SWR_GRACE_MULTIPLIER | 3.0 | config.py |
| LKG_MAX_STALENESS_MULTIPLIER | 0.0 (unlimited) | config.py |
| S3 promotion TTL | 3600s (1 hr) | tiered.py TieredConfig |
| DynamicIndex TTL | 3600s (1 hr) | universal_strategy.py |
| DynamicIndex max per entity | 5 | universal_strategy.py |
| Hierarchy max depth | 5 | unified.py |
| Asana batch limit | 10 | freshness_coordinator.py |
| FreshnessCoordinator coalesce window | 50ms | unified.py |
| Memory backend max entries | 10,000 | memory.py |
