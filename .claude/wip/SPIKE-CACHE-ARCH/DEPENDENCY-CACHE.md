# Dependency Map: Cache Subsystem

**Scope**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/` -- cache data flow, tier interactions, freshness propagation
**Date**: 2026-02-27
**Upstream**: TOPOLOGY-CACHE.md (26 cache locations across 7 areas)
**Complexity**: DEEP-DIVE (critical path analysis + data flow diagrams)

---

## Table of Contents

1. [Cache Tier Dependency Graph](#1-cache-tier-dependency-graph)
2. [Freshness Propagation Chains](#2-freshness-propagation-chains)
3. [Cache Invalidation Paths](#3-cache-invalidation-paths)
4. [Coupling Analysis](#4-coupling-analysis)
5. [Standalone vs Connected Caches](#5-standalone-vs-connected-caches)
6. [SWR Data Flow (Deep Dive)](#6-swr-data-flow-deep-dive)
7. [Critical Path Analysis](#7-critical-path-analysis)
8. [Shared Model Registry](#8-shared-model-registry)
9. [Integration Pattern Catalog](#9-integration-pattern-catalog)
10. [Unknowns](#10-unknowns)

---

## 1. Cache Tier Dependency Graph

### 1.1 Two Independent Tier Systems

The codebase contains two distinct tiered cache systems that serve different data types and have different tier compositions. They share S3 as a persistence backend but otherwise operate independently.

```
SYSTEM A: Entity Cache (Task/Story/Detection data)
=================================================

    TieredCacheProvider
    (cache/providers/tiered.py)
         |
    +----+----+
    |         |
    v         v
  Redis     S3CacheProvider
  (hot)     (cold)
    |         |
    v         v
  ElastiCache   S3 JSON/gzip
  HASH keys     {prefix}/tasks/{gid}/{entry_type}.json[.gz]


SYSTEM B: DataFrame Cache (Polars entity DataFrames)
====================================================

    DataFrameCache
    (cache/integration/dataframe_cache.py)
         |
    +----+----+
    |         |
    v         v
  MemoryTier    ProgressiveTier
  (hot)         (cold)
    |              |
    v              v
  In-process       S3 Parquet
  OrderedDict      dataframes/{project_gid}/
```

**Confidence**: High -- explicit in source code at `tiered.py:62-97` and `dataframe_cache.py:147-185`.

### 1.2 System A: Entity Cache Tier Interactions

**Provider**: `TieredCacheProvider` at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/providers/tiered.py`

| Operation | Hot (Redis) | Cold (S3) | Promotion/Demotion |
|-----------|-------------|-----------|---------------------|
| `get_versioned()` | Check first | Fallback on miss | Cold hit -> promote to hot with `promotion_ttl=3600s` (line 228-241) |
| `set_versioned()` | Always write | Write-through if enabled | Both tiers written simultaneously (line 260-276) |
| `get_batch()` | Check all first | Check missed keys | Batch promote cold hits to hot (line 321-342) |
| `invalidate()` | Always invalidate | Invalidate if S3 enabled | Both tiers invalidated (line 413-437) |
| `get()` (simple) | Hot only | Not checked | No promotion for simple keys (line 130-143) |
| `set()` (simple) | Hot only | Not written | No write-through for simple keys (line 145-157) |
| `check_freshness()` | Hot only | Not checked | Returns stale if not in hot tier (line 392-411) |

**Miss cascade**: Redis miss -> S3 lookup -> promote to Redis with 3600s TTL -> return entry. S3 miss -> return None.

**Write-through**: Controlled by `TieredConfig.write_through` (default: True) and `TieredConfig.s3_enabled` (default: False). When both are True, writes go to Redis AND S3. S3 failures are logged but never fail operations (line 266-276).

**Health**: Only hot tier (Redis) health determines overall health (line 439-448). S3 is for durability, not availability.

**Confidence**: High -- direct code reading of `tiered.py`.

### 1.3 System B: DataFrame Cache Tier Interactions

**Provider**: `DataFrameCache` at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframe_cache.py`

| Operation | Memory (OrderedDict) | Progressive (S3 Parquet) | Flow |
|-----------|---------------------|--------------------------|------|
| `get_async()` | Check first (line 279) | Fallback on miss (line 292) | S3 hit -> hydrate memory (line 300) |
| `put_async()` | Write second (line 559) | Write first (line 556) | S3 is source of truth |
| `invalidate()` | Remove entry (line 596) | NOT deleted (line 597) | Memory-only invalidation |
| `invalidate_project()` | Remove all entity types (line 609-622) | NOT deleted | Memory-only invalidation |
| `invalidate_on_schema_change()` | Clear entire tier (line 640) | NOT cleared | Schema bump = memory wipe |

**Critical asymmetry**: `invalidate()` only removes from MemoryTier. S3 entries are NOT deleted -- they are superseded on next write (comment at line 597: "Note: S3 entries not deleted, just superseded on next write"). This means S3 always contains a potentially-stale-but-schema-valid LKG entry.

**Write order**: S3 first (source of truth) -> Memory second. This is the reverse of the read order (Memory first -> S3 fallback). This ensures that if the process crashes between S3 write and memory write, S3 has the data and memory will hydrate on next read.

**Freshness gating**: Before returning an entry, `_check_freshness()` (line 803-869) performs:
1. Schema version check via `SchemaRegistry` -- hard reject on mismatch
2. Watermark check against `current_watermark` -- hard reject if behind
3. Entity-aware TTL check with SWR grace window (entity TTL * 3.0x)

**Confidence**: High -- direct code reading of `dataframe_cache.py`.

### 1.4 System A+B Bridge: UnifiedTaskStore

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/providers/unified.py`

`UnifiedTaskStore` wraps System A's `CacheProvider` (typically `TieredCacheProvider`) with:
- **HierarchyIndex**: Parent-child relationship tracking for cascade invalidation
- **FreshnessCoordinator**: Batch `modified_at` checks via Asana Batch API
- **CompletenessLevel**: Checks that cached entries have sufficient opt_fields

It does NOT interact with System B (DataFrameCache). The two systems are bridged only at the application layer where both are consumed by resolution strategies and the preload pipeline.

**Confidence**: High -- `unified.py` only imports `CacheProvider`, never `DataFrameCache`.

---

## 2. Freshness Propagation Chains

### 2.1 Chain: Task Cache -> DataFrame Cache -> Story Cache -> Timeline Cache

```
Asana API (source of truth)
    |
    | modified_at timestamp
    v
UnifiedTaskStore (System A)
    |
    | Task data cached with version=modified_at
    | Freshness: FreshnessCoordinator batch check (Batch API)
    v
Per-Task DataFrame Cache (cache/integration/dataframes.py)
    |
    | Computed row cached with version=modified_at
    | Key: {task_gid}:{project_gid}
    | Staleness: version comparison against current modified_at
    v
Project DataFrame Cache (System B - DataFrameCache)
    |
    | Full entity DataFrame (all tasks merged)
    | Key: {entity_type}:{project_gid}
    | Staleness: entity-aware TTL + SWR grace
    v
Story Cache (cache/integration/stories.py)
    |
    | Per-task story lists with incremental fetch (since cursor)
    | Key: task_gid, EntryType.STORIES
    | Staleness: version comparison against task modified_at
    v
Derived Timeline Cache (cache/integration/derived.py)
    |
    | Pre-computed SectionTimeline data
    | Key: timeline:{project_gid}:{classifier_name}
    | Staleness: fixed 300s TTL
    v
API Response
```

**Freshness propagation is NOT automatic.** When a task changes in Asana:
1. The task cache (System A) does NOT push invalidation to downstream caches.
2. Per-task DataFrame entries are invalidated only when `MutationInvalidator` fires (REST mutations) or when `load_dataframe_cached()` detects a `modified_at` mismatch at read time.
3. Project DataFrames are invalidated via `DataFrameCache.invalidate_project()` only for structural mutations (CREATE/DELETE/MOVE), not for field updates.
4. Story cache entries are NOT explicitly invalidated on task update -- `load_stories_incremental()` uses `is_stale(current_modified_at)` at read time to detect staleness and then does an incremental fetch.
5. Timeline cache has a fixed 300s TTL with no upstream-triggered invalidation.

**Confidence**: High -- traced through all files.

### 2.2 Chain: Build Result -> Memory Promotion -> S3 Write-Through

```
ProgressiveProjectBuilder.build_progressive_async()
    |
    | Returns BuildResult (frozen dataclass)
    | build_result.py line 107-261
    v
BuildResult.total_rows (property)
    |
    | Line 166-175: Uses len(self.dataframe) when dataframe is not None
    | Falls back to sum of SUCCESS section row_counts
    v
[Decision gate in factory.py line 91]
    |
    if result.total_rows > 0 and result.dataframe is not None:
    |
    v
DataFrameCache.put_async()
    |
    | Line 556: ProgressiveTier.put_async() -- S3 parquet write (source of truth)
    | Line 559: MemoryTier.put() -- in-process OrderedDict
    | Line 562: CircuitBreaker.close() -- reset failure counter
    v
Both tiers populated
```

**The SWR Memory Promotion Bug (fixed)**: The MEMORY.md documents that `BuildResult.total_rows` previously returned 0 on resume because it counted only SUCCESS sections, not SKIPPED (resumed) sections. The fix at `build_result.py:166-175` now uses `len(self.dataframe)` when the DataFrame is available, which covers resumed sections. The `fetched_rows` property (line 179-180) still counts only SUCCESS section rows, providing the API-work metric.

**Confidence**: High -- read the fixed code at `build_result.py:166-175` and the gate at `factory.py:91`.

### 2.3 Chain: Mutation -> MutationInvalidator -> Downstream Caches

```
REST Mutation Endpoint (e.g., update_task, move_task)
    |
    | Constructs MutationEvent(entity_kind, entity_gid, mutation_type, project_gids)
    v
TaskService / SectionService / FieldWriteService
    |
    | fire_and_forget(event) -- asyncio.create_task
    | (services/task_service.py line 496, 557, 587, 618)
    | (services/section_service.py line 179, 264)
    | (services/field_write_service.py line 216)
    v
MutationInvalidator.invalidate_async(event)
    |
    +-- Task Mutation:
    |   |
    |   +-- Step 1: entity cache TASK/SUBTASKS/DETECTION (hard invalidate or soft mark)
    |   |   (mutation_invalidator.py line 153)
    |   |
    |   +-- Step 1b: STORIES -- hard-delete ONLY on task DELETE (line 158-165)
    |   |   UPDATE/MOVE preserve stories for incremental fetch (ADR-0020)
    |   |
    |   +-- Step 2: per-task DataFrame entries {task_gid}:{project_gid}
    |   |   (mutation_invalidator.py line 168-169)
    |   |   -> invalidate_task_dataframes() in cache/integration/dataframes.py
    |   |
    |   +-- Step 3: project-level DataFrameCache (MemoryTier only)
    |       ONLY for structural mutations: CREATE/DELETE/MOVE/ADD_MEMBER/REMOVE_MEMBER
    |       (mutation_invalidator.py line 174-181)
    |       -> DataFrameCache.invalidate_project() clears MemoryTier for all entity types
    |
    +-- Section Mutation:
        |
        +-- Step 1: entity cache SECTION entry (line 206)
        +-- Step 2: project DataFrameCache (MemoryTier only) (line 214-215)
        +-- Step 3: if ADD_MEMBER, also invalidate the added task's entity entries (line 219-220)
```

**Key observation**: MutationInvalidator does NOT invalidate story cache for UPDATE mutations. This is intentional per ADR-0020 -- story entries are preserved so `load_stories_incremental()` can use the `since` cursor for cheap incremental fetches.

**Key observation**: MutationInvalidator does NOT invalidate derived timeline cache. Timelines depend on a fixed 300s TTL only.

**Key observation**: MutationInvalidator invalidates DataFrameCache (System B) only for structural mutations, not field updates. Field updates invalidate per-task DataFrame entries (System A) but not the project-level DataFrameCache (System B). This means a field update to a task will not refresh the project-level DataFrame until its TTL expires or SWR triggers.

**Confidence**: High -- traced through `mutation_invalidator.py`, `task_service.py`, `section_service.py`, `field_write_service.py`.

---

## 3. Cache Invalidation Paths

### 3.1 All Invalidation Entry Points

| # | Trigger | Source File | Caches Affected | Mechanism |
|---|---------|------------|-----------------|-----------|
| I-1 | REST task mutation | `services/task_service.py:496,557,587,618` | Entity (TASK/SUBTASKS/DETECTION), per-task DF, project DF (structural only), STORIES (delete only) | MutationInvalidator fire-and-forget |
| I-2 | REST section mutation | `services/section_service.py:179,264` | Entity (SECTION), project DF, task entity (ADD_MEMBER) | MutationInvalidator fire-and-forget |
| I-3 | REST field write | `services/field_write_service.py:216` | Entity (TASK/SUBTASKS/DETECTION), per-task DF | MutationInvalidator via asyncio.create_task |
| I-4 | SaveSession commit | `persistence/cache_invalidator.py:50-95` | Entity (TASK/SUBTASKS/DETECTION), per-task DF | CacheInvalidator synchronous after commit |
| I-5 | Lambda clear_tasks | `lambda_handlers/cache_invalidate.py:115-150` | Entity cache (Redis+S3) via TieredCacheProvider.clear_all_tasks() | SCAN-based Redis clear + S3 delete |
| I-6 | Lambda clear_dataframes | `lambda_handlers/cache_invalidate.py:152-166` | DataFrameCache MemoryTier (all entries) | Schema version bump trick |
| I-7 | Lambda invalidate_project | `lambda_handlers/cache_invalidate.py:171-195` | S3 manifest + section parquets for specific project | SectionPersistence delete |
| I-8 | Schema version change | `dataframe_cache.py:624-641` | DataFrameCache MemoryTier (all entries) | memory_tier.clear() |
| I-9 | Staleness check: CHANGED | `staleness_coordinator.py:209-211` | Entity cache entry for the checked GID | Returns None (caller re-fetches) |
| I-10 | Staleness check: ERROR/DELETED | `staleness_coordinator.py:167-182` | Entity cache entry (hard invalidate) | cache_provider.invalidate() |
| I-11 | Freshness check: SCHEMA_INVALID | `dataframe_cache.py:486-497` | DataFrameCache MemoryTier entry | memory_tier.remove() |
| I-12 | Freshness check: LKG_MAX exceeded | `dataframe_cache.py:450-465` | DataFrameCache MemoryTier entry | memory_tier.remove() |
| I-13 | UnifiedTaskStore cascade | `unified.py:807-850` | Entity cache (TASK) for GID + all descendants | hierarchy-based cascade |
| I-14 | CircuitBreaker record_failure | `circuit_breaker.py` (indirect) | Prevents builds, serves LKG | State machine CLOSED->OPEN |
| I-15 | DataFrameCache.invalidate_project() | `dataframe_cache.py:609-622` | DataFrameCache MemoryTier (all entity types for project) | memory_tier.remove() per entity type |
| I-16 | ModificationCheckCache TTL expiry | `cache/integration/batch.py` | 25s TTL on cached modification timestamps | Passive expiry on read |

**Confidence**: High -- each entry point traced to source file and line.

### 3.2 SaveSession Write Pipeline Invalidation

```
SaveSession.__aenter__()
    -> registers entities for CRUD
    |
SaveSession.commit_async()
    |
    +-- Phase 0: Validate & lock
    +-- Phase 1: Execute CRUD operations against Asana API
    +-- Phase 1.5: Cache invalidation (persistence/cache_invalidator.py)
    |   |
    |   +-- CacheInvalidator.invalidate_for_commit()
    |   |   |
    |   |   +-- _collect_affected_gids(): Union of CRUD succeeded + Action succeeded GIDs
    |   |   +-- _invalidate_entity_caches(): Per-GID invalidation of TASK/SUBTASKS/DETECTION
    |   |   |   -> cache_provider.invalidate(gid, [TASK, SUBTASKS, DETECTION])
    |   |   |   -> Goes to TieredCacheProvider -> Redis + S3
    |   |   |
    |   |   +-- _invalidate_dataframe_caches(): Per-GID, per-project DataFrame invalidation
    |   |       -> invalidate_task_dataframes(gid, project_gids, cache)
    |   |       -> Goes to TieredCacheProvider (System A per-task DF entries)
    |   |       NOTE: Does NOT invalidate DataFrameCache (System B)
    |   |
    +-- Phase 2: Execute actions
    +-- Phase 3: Return results
```

**Key gap**: SaveSession's CacheInvalidator invalidates per-task DataFrame entries (System A) but does NOT invalidate the project-level DataFrameCache (System B). This means after a SaveSession commit, the project-level DataFrame in MemoryTier may serve stale data until its entity-aware TTL expires.

This contrasts with MutationInvalidator (used by REST routes), which DOES invalidate DataFrameCache for structural mutations. The distinction is:
- **SaveSession** (batch operations, typically automation pipeline): Entity cache + per-task DF only
- **MutationInvalidator** (individual REST mutations): Entity cache + per-task DF + project DF (structural)

**Confidence**: High -- traced through `persistence/session.py:807-914` and `persistence/cache_invalidator.py:50-95`.

### 3.3 Lambda Cache Invalidation Operations

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_invalidate.py`

Three independent invalidation modes:

| Mode | Parameter | What Gets Cleared | How |
|------|-----------|--------------------|-----|
| `clear_tasks` | `clear_tasks=true` (default) | All entity cache entries in Redis + S3 | `TieredCacheProvider.clear_all_tasks()` which uses SCAN on Redis + DeleteObject on S3 |
| `clear_dataframes` | `clear_dataframes=true` | DataFrameCache MemoryTier (entire tier) | Schema version bump: `invalidate_on_schema_change(f"invalidate-{id}")` sets version to unique string, causing all entries to fail schema check |
| `invalidate_project` | `invalidate_project="12345"` | S3 section parquets + manifest for specific project | `SectionPersistence.delete_section_files_async()` + `delete_manifest_async()` |

**Schema version bump trick** (line 159): The `clear_dataframes` mode does not actually delete S3 parquets. It sets `DataFrameCache.schema_version` to a unique string (`invalidate-{invocation_id}`), which causes `_check_freshness()` to return `SCHEMA_INVALID` for all cached entries because their `schema_version` will not match the new version. This effectively invalidates all memory-tier entries. S3 entries remain but will be rejected on load due to schema mismatch.

**Confidence**: High -- direct code reading.

### 3.4 ModificationCheckCache (25s TTL) Staleness Detection

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/batch.py`

This cache sits in front of the Asana API for `modified_at` timestamp checks. It prevents redundant API calls within a 25s window by caching the fetched `modified_at` per task GID.

```
Task fetch request
    |
    v
ModificationCheckCache
    |
    +-- Cache hit (< 25s old): Return cached modified_at
    |   -> Downstream uses this to check entity cache freshness
    |
    +-- Cache miss (> 25s old or first check):
        -> Fetch modified_at from Asana API
        -> Store in cache with 25s TTL
        -> Return fresh modified_at
```

This cache is process-scoped (in-process dict) with per-run isolation via `run_id` (hostname:PID). It does not interact with Redis or S3. It is reset via `SystemContext.reset_all()`.

**Confidence**: High -- from topology inventory section 3.1.25.

### 3.5 FreshnessCoordinator and StalenessCheckCoordinator

These are two parallel freshness-checking systems for entity cache entries:

**FreshnessCoordinator** (`cache/integration/freshness_coordinator.py`):
- Used by `UnifiedTaskStore` for get/get_batch operations
- Checks freshness via Asana Batch API (`GET /tasks/{gid}?opt_fields=modified_at`)
- Chunked by 10 (Asana batch limit)
- Three modes: IMMEDIATE (no API call), EVENTUAL (check only expired), STRICT (always check)
- Returns `FreshnessResult` with action recommendation (use_cache, fetch, extend_ttl)

**StalenessCheckCoordinator** (`cache/integration/staleness_coordinator.py`):
- Used by `BaseClient` for individual entity cache lookups
- Composes `RequestCoalescer` (50ms batching window) + `LightweightChecker` (batch API)
- Progressive TTL extension: `min(base * 2^count, max)` on UNCHANGED result
- Three outcomes: UNCHANGED (extend TTL), CHANGED (return None, force fetch), ERROR (invalidate + None)

Both coordinators call the same Asana Batch API endpoint but are wired at different levels of the stack.

**Confidence**: High -- direct code reading of both files.

---

## 4. Coupling Analysis

### 4.1 Coupling Scoring Methodology

For each cache pair, coupling is scored on a 0-5 scale across four dimensions:
- **Data coupling** (shared data format/model): 0-5
- **Stamp coupling** (shared data structure passed between): 0-5
- **Control coupling** (one controls behavior of another): 0-5
- **Temporal coupling** (must happen in sequence): 0-5

**Composite score** = max(individual scores). Scores >= 3 are flagged for further analysis.

### 4.2 Coupling Pairs

#### Pair 1: DataFrameCache <-> ProgressiveTier/SectionPersistence
- **Data coupling**: 5 -- share `DataFrameCacheEntry` model, parquet format, watermark JSON
- **Control coupling**: 4 -- DataFrameCache writes S3 first (source of truth), controls read order
- **Temporal coupling**: 4 -- put_async must write S3 before memory; read must hydrate memory from S3 on hit
- **Directionality**: Unidirectional (DataFrameCache -> ProgressiveTier)
- **Bounded context check**: Same bounded context (DataFrame caching). **Intentional cohesion.**
- **Intentionality check**: Designed coupling (ProgressiveTier is an explicit component of DataFrameCache)
- **Composite score**: 5 (data)
- **Assessment**: Context-aware intentional coupling. Not a hotspot.
- **Confidence**: High

#### Pair 2: TieredCacheProvider <-> Redis/S3 Backends
- **Data coupling**: 5 -- share `CacheEntry` model, serialization format
- **Control coupling**: 4 -- TieredCacheProvider controls read/write ordering and promotion
- **Temporal coupling**: 3 -- write-through requires both tiers written; promotion requires cold-read then hot-write
- **Directionality**: Unidirectional (TieredCacheProvider -> backends)
- **Bounded context check**: Same bounded context (entity caching). **Intentional cohesion.**
- **Intentionality check**: Designed coupling (explicit composition pattern)
- **Composite score**: 5 (data)
- **Assessment**: Context-aware intentional coupling. Not a hotspot.
- **Confidence**: High

#### Pair 3: MutationInvalidator <-> DataFrameCache + TieredCacheProvider
- **Data coupling**: 2 -- shares GID strings and project_gids, not data models
- **Stamp coupling**: 3 -- passes `MutationEvent` which carries entity_kind, mutation_type, project_gids
- **Control coupling**: 4 -- MutationInvalidator decides WHICH caches to invalidate based on mutation type
- **Temporal coupling**: 1 -- fire-and-forget, no ordering guarantee
- **Directionality**: Unidirectional (MutationInvalidator -> caches)
- **Bounded context check**: Crosses bounded contexts (mutation handling -> cache management)
- **Intentionality check**: Designed (explicit invalidation contract per ADR-003)
- **Composite score**: 4 (control)
- **Assessment**: Cross-context but intentional. The control coupling is by design -- MutationInvalidator is the translation layer between mutation semantics and cache invalidation semantics. Not a hotspot.
- **Confidence**: High

#### Pair 4: CacheInvalidator (SaveSession) <-> TieredCacheProvider
- **Data coupling**: 2 -- shares GIDs and EntryTypes
- **Control coupling**: 3 -- CacheInvalidator decides which entry types to invalidate
- **Temporal coupling**: 3 -- must happen after CRUD commit but before response
- **Directionality**: Unidirectional (CacheInvalidator -> TieredCacheProvider)
- **Bounded context check**: Crosses bounded contexts (persistence/UoW -> cache management)
- **Intentionality check**: Designed (ADR-0059 extraction)
- **Composite score**: 3 (control + temporal)
- **Assessment**: Cross-context, intentional. Not a hotspot.
- **Confidence**: High

#### Pair 5: DataFrameCache <-> SchemaRegistry
- **Data coupling**: 2 -- shares schema version strings
- **Control coupling**: 4 -- SchemaRegistry version determines whether DataFrameCache entries are valid
- **Temporal coupling**: 3 -- SchemaRegistry must be initialized before DataFrameCache can serve
- **Directionality**: Unidirectional (SchemaRegistry -> DataFrameCache, via `_get_schema_version_for_entity()`)
- **Bounded context check**: Crosses bounded contexts (schema management -> caching)
- **Intentionality check**: Designed (explicit version check per TDD)
- **Composite score**: 4 (control)
- **Assessment**: Cross-context but intentional. SchemaRegistry controls cache validity by design. Not a hotspot -- but changing a schema version has a blast radius of invalidating ALL cached DataFrames for that entity type.
- **Confidence**: High

#### Pair 6: SWR Build Callback <-> Full Application Stack
- **Data coupling**: 3 -- callback requires AsanaClient, schema, resolver, persistence
- **Stamp coupling**: 4 -- passes through BuildResult, which carries DataFrame + watermark + quality metadata
- **Control coupling**: 3 -- callback failure triggers circuit breaker recording
- **Temporal coupling**: 2 -- asynchronous background task, no blocking dependency
- **Directionality**: DataFrameCache -> SWR callback -> full stack -> DataFrameCache.put_async()
- **Bounded context check**: **Circular data flow** -- DataFrameCache triggers callback that writes back to DataFrameCache
- **Intentionality check**: Designed (explicit SWR pattern)
- **Composite score**: 4 (stamp)
- **Assessment**: The circular data flow is intentional (SWR pattern), but the callback's dependency on the full application stack (`AsanaClient`, `ProgressiveProjectBuilder`, `SectionPersistence`, `SchemaRegistry`, `CustomFieldResolver`) creates a wide coupling surface. Changes to any of these components could break SWR background refreshes.
- **Confidence**: High

#### Pair 7: Lambda Warmer <-> DataFrameCache + Story Cache + GID Push
- **Data coupling**: 3 -- shares DataFrames, task GIDs, entity types
- **Control coupling**: 3 -- warmer orchestrates multiple cache populations
- **Temporal coupling**: 4 -- sequential: DataFrame warm -> story warm -> GID push
- **Directionality**: Unidirectional (Lambda warmer -> caches)
- **Bounded context check**: Crosses multiple contexts (warming -> DF cache, story cache, GID service)
- **Intentionality check**: Designed (explicit warming orchestration)
- **Composite score**: 4 (temporal)
- **Assessment**: Cross-context, intentional. The temporal coupling is by design -- stories depend on task GIDs from DataFrames, so ordering is necessary. Not a hotspot, but Lambda timeout handling adds complexity (checkpoint + self-invoke continuation).
- **Confidence**: High

#### Pair 8: Story Cache <-> Derived Timeline Cache
- **Data coupling**: 3 -- timelines are computed FROM stories
- **Control coupling**: 0 -- no mutual control
- **Temporal coupling**: 3 -- timeline computation reads story cache; if stories are stale, timelines are stale
- **Directionality**: Unidirectional (Story cache -> Timeline cache, via computation)
- **Bounded context check**: Different bounded contexts (entity caching -> derived computation)
- **Intentionality check**: Designed (timeline is explicitly derived from stories)
- **Composite score**: 3 (data + temporal)
- **Assessment**: Intentional derivation relationship. Timeline cache has no invalidation mechanism tied to story cache changes -- it relies on its own 300s TTL. This means timelines can be up to 300s stale relative to story changes.
- **Confidence**: High

### 4.3 Coupling Hotspots

No incidental, circular, or cross-bounded-context coupling rises to hotspot level. All coupling is intentional by design. The highest-risk coupling is:

1. **SWR callback wide dependency surface** (Pair 6, score 4): Changes to `AsanaClient`, `ProgressiveProjectBuilder`, `SchemaRegistry`, or `SectionPersistence` could break background SWR refreshes silently (errors are caught and logged, not propagated).

2. **SaveSession vs MutationInvalidator asymmetry** (Pairs 3+4): SaveSession does NOT invalidate DataFrameCache (System B), while MutationInvalidator DOES for structural mutations. This is an intentional design choice but creates a subtle behavioral difference between batch operations (automation pipeline) and individual REST mutations.

---

## 5. Standalone vs Connected Caches

### 5.1 Standalone (Isolated) Caches

| Cache | File | Isolation Mechanism | Connected To |
|-------|------|---------------------|-------------|
| `lru_cache: Bot PAT` | `auth/bot_pat.py` | `functools.lru_cache(maxsize=1)`, process-lifetime | Nothing -- pure value cache |
| `lru_cache: API Config` | `api/config.py` | `functools.lru_cache`, process-lifetime | Nothing -- pure config cache |
| `lru_cache: Field Normalizer` | `dataframes/resolver/normalizer.py` | `functools.lru_cache(maxsize=1024)` | Nothing -- pure transform cache |
| `lru_cache: Tier2 Detection` | `models/business/detection/tier2.py` | `functools.lru_cache(maxsize=128)` | Nothing -- compiled regex cache |
| `OfflineDataFrameProvider` | `query/offline_provider.py` | In-process dict, CLI context only | S3 (read-only, no Redis, no tiered) |
| `DataServiceClient Insights Cache` | `clients/data/_cache.py` | CacheProvider.set()/get() (simple keys) | TieredCacheProvider hot tier only (simple keys bypass S3) |
| `ModificationCheckCache` | `cache/integration/batch.py` | In-process dict, 25s TTL, process-scoped | Asana API (read), entity cache freshness checks (consume) |
| `HierarchyIndex` | `cache/policies/hierarchy.py` | In-process, no TTL, grows until reset | UnifiedTaskStore (bidirectional registration + lookup) |

**Confidence**: High for all.

### 5.2 Connected (Interconnected Tier System) Caches

| Cache | System | Role in Tier | Upstream Dependencies | Downstream Consumers |
|-------|--------|-------------|----------------------|---------------------|
| `TieredCacheProvider` | A (Entity) | Composite | Redis + S3 backends | UnifiedTaskStore, CacheInvalidator, MutationInvalidator, stories.py, dataframes.py, derived.py |
| `RedisCacheProvider` | A (Entity) | Hot tier | ElastiCache | TieredCacheProvider |
| `S3CacheProvider` | A (Entity) | Cold tier | S3 JSON/gzip | TieredCacheProvider |
| `UnifiedTaskStore` | A (Entity) | Wrapper | TieredCacheProvider + HierarchyIndex + FreshnessCoordinator | Resolution strategies, SWR callback, Lambda warmer |
| `DataFrameCache` | B (DataFrame) | Composite | MemoryTier + ProgressiveTier + Coalescer + CircuitBreaker | Resolution strategies, preload, Lambda warmer, MutationInvalidator |
| `MemoryTier` | B (DataFrame) | Hot tier | In-process OrderedDict | DataFrameCache |
| `ProgressiveTier` | B (DataFrame) | Cold tier | S3 parquet via SectionPersistence | DataFrameCache |
| `WatermarkRepository` | Cross-system | Tracking | In-process dict + S3 write-through | Preload pipeline, incremental sync |
| `Story Cache` (stories.py) | A (Entity) | Integration | TieredCacheProvider (via CacheProvider.get_versioned/set_versioned) | Timeline computation, Lambda warmer |
| `Derived Timeline Cache` (derived.py) | A (Entity) | Integration | TieredCacheProvider (via CacheProvider.get_versioned/set_versioned) | API section-timelines endpoint |
| `Per-Task DataFrame Cache` (dataframes.py) | A (Entity) | Integration | TieredCacheProvider (via CacheProvider.get_versioned/set_versioned) | Resolution strategies |

**Confidence**: High for all.

### 5.3 Notable Isolation Patterns

**OfflineDataFrameProvider**: Completely isolated from the tiered cache system. Reads S3 parquets directly using `load_project_dataframe_with_meta()` (sync), bypassing all caching layers, freshness checks, and SWR. In-process dict cache keyed by `project_gid` with no TTL. Used only by CLI (`python -m autom8_asana.query`).

**Insights Cache**: Uses `CacheProvider.set()/get()` (simple key-value), NOT `set_versioned()/get_versioned()`. In `TieredCacheProvider`, simple `set()`/`get()` operates on hot tier ONLY (lines 130-157). This means insights responses are cached in Redis but NOT written through to S3. They have no version tracking, no freshness coordination, and no staleness detection beyond Redis key TTL.

**Confidence**: High -- verified in `tiered.py` lines 130-157 and `_cache.py` lines 68-98.

---

## 6. SWR Data Flow (Deep Dive)

### 6.1 SWR Lifecycle

```
[1] Request arrives for entity DataFrame
    |
    v
[2] DataFrameCache.get_async(project_gid, entity_type)
    |
    +-- [3] Memory tier check -> entry found
    |   |
    |   v
    |   [4] _check_freshness(entry, current_watermark)
    |       |
    |       +-- FRESH (age <= entity_ttl):
    |       |   -> Return entry immediately (no background work)
    |       |
    |       +-- APPROACHING_STALE (entity_ttl < age <= entity_ttl * 3.0):
    |       |   -> [5] Return stale entry immediately to caller
    |       |   -> [6] _trigger_swr_refresh() fires asyncio.create_task
    |       |   |
    |       |   v
    |       |   [7] _swr_refresh_async()
    |       |       |
    |       |       +-- [8] acquire_build_lock_async() via coalescer
    |       |       |   (deduplication: if build already in progress, return)
    |       |       |
    |       |       +-- [9] _build_callback(project_gid, entity_type)
    |       |       |   = factory.py:_swr_build_callback()
    |       |       |   |
    |       |       |   +-- [10] Acquire AsanaClient + schema + resolver + persistence
    |       |       |   +-- [11] ProgressiveProjectBuilder.build_progressive_async(resume=True)
    |       |       |   +-- [12] Gate: result.total_rows > 0 AND result.dataframe is not None
    |       |       |   +-- [13] DataFrameCache.put_async()
    |       |       |       -> S3 parquet write (source of truth)
    |       |       |       -> MemoryTier write (hot cache)
    |       |       |       -> CircuitBreaker.close()
    |       |       |
    |       |       +-- [14] release_build_lock_async(success=True/False)
    |       |           -> Notify all waiters via coalescer
    |       |           -> On failure: CircuitBreaker.record_failure()
    |       |
    |       +-- STALE (age > entity_ttl * 3.0, but schema/watermark valid):
    |       |   -> Return stale entry as LKG (last-known-good) with warning
    |       |   -> Also triggers SWR refresh (same path as APPROACHING_STALE)
    |       |
    |       +-- SCHEMA_INVALID or WATERMARK_BEHIND:
    |           -> Hard reject, remove from MemoryTier, return None
    |           -> Caller must trigger full build
    |
    +-- [3b] Memory tier miss -> S3/Progressive tier check
        |
        +-- S3 hit: hydrate memory tier, then run freshness check
        +-- S3 miss: return None (caller triggers build)
```

### 6.2 SWR Build Callback Dependency Chain

The SWR build callback at `factory.py:40-97` has the following dependency chain:

```
_swr_build_callback(cache, project_gid, entity_type)
    |
    +-- get_bot_pat() -- auth/bot_pat.py (lru_cache singleton)
    +-- get_workspace_gid() -- config.py
    +-- AsanaClient(token, workspace_gid) -- client.py
    |   +-- unified_store (UnifiedTaskStore) -- available via client
    |
    +-- to_pascal_case(entity_type) -- core/string_utils.py
    +-- get_schema(task_type) -- dataframes/models/registry.py
    +-- DefaultCustomFieldResolver() -- dataframes/resolver
    +-- create_section_persistence() -- dataframes/section_persistence.py
    |   +-- S3 bucket config
    |
    +-- ProgressiveProjectBuilder -- dataframes/builders/
    |   +-- client, project_gid, entity_type, schema, persistence, resolver, store, index_builder
    |
    +-- builder.build_progressive_async(resume=True) -> BuildResult
    |
    +-- [GATE] result.total_rows > 0 AND result.dataframe is not None
    |
    +-- cache.put_async(project_gid, entity_type, result.dataframe, result.watermark)
```

**Failure isolation**: The entire SWR refresh runs inside a try/except that catches `Exception` (line 928 in `dataframe_cache.py`). Failures are logged as `swr_refresh_failed` and the build lock is released with `success=False`, which records a failure in the circuit breaker. After 3 failures in 60s, the circuit breaker opens and the project serves LKG only.

### 6.3 The Fixed SWR Memory Promotion Bug

**Before fix** (per MEMORY.md): `BuildResult.total_rows` was computed as `sum(s.row_count for s in self.sections if s.is_success)`. On resume builds, most sections have outcome `SKIPPED` (loaded from manifest), not `SUCCESS`. So `total_rows` returned 0 even when a valid DataFrame with rows was produced. The gate at `factory.py:91` (`if result.total_rows > 0`) would fail, and the DataFrame would NOT be promoted to DataFrameCache.

**After fix** (`build_result.py:166-175`):
```python
@property
def total_rows(self) -> int:
    if self.dataframe is not None:
        return len(self.dataframe)
    return sum(s.row_count for s in self.sections if s.is_success)
```

Now `total_rows` uses `len(self.dataframe)` when available, which correctly counts all rows including those from resumed (SKIPPED) sections. The `fetched_rows` property preserves the old behavior for API-work metrics.

**Current status**: The fix is committed locally but the MEMORY.md still notes "Fix committed locally, not yet pushed." The gate at `factory.py:91` should now pass correctly for resume builds.

**Confidence**: High -- read the fixed code.

---

## 7. Critical Path Analysis

### 7.1 Request-Time Critical Path (API GET)

```
API Request (e.g., GET /v1/query/{entity_type}/rows)
    |
    v
Resolution Strategy (e.g., OfferResolutionStrategy)
    |
    +-- @dataframe_cache decorator checks DataFrameCache
    |   |
    |   +-- MemoryTier HIT (p99: <1ms): Return DataFrame
    |   |
    |   +-- MemoryTier MISS -> ProgressiveTier (S3):
    |       |
    |       +-- S3 HIT (p99: ~50-200ms): Load parquet, hydrate memory, return
    |       |
    |       +-- S3 MISS: Trigger full build
    |           |
    |           +-- Coalescer: acquire build lock
    |           +-- BuildCoordinator: max 4 concurrent builds
    |           +-- ProgressiveProjectBuilder: fetch from Asana API
    |           +-- put_async: write S3 -> write memory -> close circuit
    |           +-- Return to caller (p99: 5-30s for cold build)
    |
    v
Per-Task Processing (for each task in DataFrame):
    |
    +-- UnifiedTaskStore.get_async() or get_batch_async()
    |   -> TieredCacheProvider: Redis first, S3 fallback, promote
    |   -> FreshnessCoordinator: batch modified_at check
    |
    +-- load_stories_incremental() (for timeline data)
    |   -> CacheProvider.get_versioned(task_gid, STORIES)
    |   -> If cache hit + max_cache_age_seconds short-circuit: no API call
    |   -> If stale: incremental fetch via Asana API since cursor
    |
    v
API Response with FreshnessInfo side-channel
```

### 7.2 Cold Start Critical Path (ECS Deploy)

```
ECS Container Start
    |
    v
API Lifespan startup (api/lifespan.py)
    |
    +-- Initialize CacheProviderFactory -> create TieredCacheProvider
    +-- Initialize DataFrameCache singleton (factory.py)
    +-- Initialize UnifiedTaskStore
    +-- Initialize MutationInvalidator
    |
    v
Legacy Preload (api/preload/legacy.py)   [target: <5s]
    |
    +-- Load watermarks from S3 (bulk)
    +-- For each registered project:
    |   |
    |   +-- Load GidLookupIndex from S3
    |   +-- Load DataFrame from S3 (parquet)
    |   +-- Get watermark from repo
    |   |
    |   +-- If all 3 exist: Incremental catch-up
    |   |   -> ProgressiveProjectBuilder(resume=True)
    |   |   -> Merge deltas into existing DataFrame
    |   |   -> DataFrameCache.put_async() -- populate MemoryTier
    |   |
    |   +-- If missing: Full rebuild via API
    |       -> ProgressiveProjectBuilder(resume=False)
    |       -> DataFrameCache.put_async() -- populate MemoryTier
    |
    v
set_cache_ready(True) -- health check returns 200
```

### 7.3 Lambda Warming Critical Path

```
Lambda Invocation (scheduled or self-invoke continuation)
    |
    v
Bootstrap: _ensure_bootstrap() -- lazy model registration
    |
    v
Initialize DataFrameCache singleton
    |
    v
Discover entity projects (if EntityProjectRegistry not ready)
    |
    v
For each entity type in priority order (unit, business, offer, contact, ...):
    |
    +-- Check timeout (_should_exit_early: 2 min buffer)
    |   -> If approaching timeout: save checkpoint, self-invoke continuation
    |
    +-- CacheWarmer.warm_entity_async()
    |   -> ProgressiveProjectBuilder.build_progressive_async(resume=True)
    |   -> DataFrameCache.put_async() -- S3 + memory
    |
    +-- Save checkpoint to S3 (after each entity)
    |
    v
After all entities complete:
    |
    +-- Clear checkpoint from S3
    +-- Push GID mappings to autom8_data service
    +-- Warm story caches (piggyback on completed DataFrames)
    |   -> For each task GID in each warmed DataFrame:
    |       -> client.stories.list_for_task_cached_async(max_cache_age_seconds=7200)
    |       -> Bounded concurrency (Semaphore(3))
    |       -> Chunked by 100, with timeout check between chunks
    |
    v
Return WarmResponse
```

---

## 8. Shared Model Registry

### 8.1 Shared Data Models Across Cache Boundaries

| Model | Definition | Used By | Sharing Mechanism |
|-------|-----------|---------|-------------------|
| `CacheEntry` | `cache/models/entry.py` | TieredCacheProvider, UnifiedTaskStore, stories.py, dataframes.py, derived.py, CacheInvalidator, MutationInvalidator, StalenessCheckCoordinator | Shared library (single definition) |
| `EntryType` (enum) | `cache/models/entry.py` | All cache consumers | Shared library |
| `FreshnessIntent` | `cache/models/freshness_unified.py` | UnifiedTaskStore, TieredCacheProvider, FreshnessCoordinator | Shared library |
| `FreshnessState` | `cache/models/freshness_unified.py` | DataFrameCache | Shared library (System B only) |
| `DataFrameCacheEntry` | `cache/integration/dataframe_cache.py` | DataFrameCache, MemoryTier, ProgressiveTier | Shared within System B |
| `FreshnessInfo` | `cache/integration/dataframe_cache.py` | DataFrameCache, OfflineDataFrameProvider, API response layer | Shared library (cross-system) |
| `MutationEvent` | `cache/models/mutation_event.py` | MutationInvalidator, TaskService, SectionService, FieldWriteService | Shared library |
| `BuildResult` / `BuildQuality` | `dataframes/builders/build_result.py` | SWR callback, DataFrameCache.put_async, CacheWarmer | Shared library |
| `CacheProvider` protocol | `protocols/cache.py` | All System A consumers | Protocol (interface contract) |

**Divergence note**: There are TWO distinct "DataFrameCacheEntry" types in the codebase:
1. `cache/integration/dataframe_cache.py:DataFrameCacheEntry` -- holds actual `pl.DataFrame` + watermark (System B)
2. `cache/models/entry.py:DataFrameMetaCacheEntry` -- versioned Redis/S3 cache entry for DataFrame metadata (System A)

These are distinct types used in different contexts. The naming collision is documented in the code (line 79 comment in `dataframe_cache.py`).

**Confidence**: High.

### 8.2 Schema/Contract Sharing

| Contract | Producer | Consumers | Versioning |
|----------|----------|-----------|------------|
| Schema version string | `dataframes/models/registry.py:SchemaRegistry` | DataFrameCache freshness check, Lambda invalidation (schema bump trick) | Per entity type, from EntityDescriptor |
| Watermark (datetime) | `dataframes/watermark.py:WatermarkRepository` | DataFrameCache, preload, incremental sync | Per project, monotonically increasing |
| S3 parquet format | `dataframes/section_persistence.py` | ProgressiveTier, OfflineDataFrameProvider, S3DataFrameStorage | Implicit (Polars parquet) |
| S3 key layout: `dataframes/{project_gid}/` | `SectionPersistence` | ProgressiveTier, OfflineDataFrameProvider, Lambda invalidate_project | Convention-based |

**Confidence**: High.

---

## 9. Integration Pattern Catalog

### 9.1 Intra-Subsystem Integration Patterns

| # | Pattern | From | To | Classification | Confidence |
|---|---------|------|-----|----------------|------------|
| P-1 | Composition (tiered) | TieredCacheProvider | Redis + S3 backends | Composite provider | High |
| P-2 | Composition (tiered) | DataFrameCache | MemoryTier + ProgressiveTier | Composite provider | High |
| P-3 | Wrapper | UnifiedTaskStore | TieredCacheProvider + HierarchyIndex + FreshnessCoordinator | Semantic overlay | High |
| P-4 | Decorator | @dataframe_cache | Resolution strategies | Cache-aside | High |
| P-5 | Observer (fire-and-forget) | MutationInvalidator | TieredCacheProvider + DataFrameCache | asyncio.create_task | High |
| P-6 | Observer (fire-and-forget) | CacheInvalidator (SaveSession) | TieredCacheProvider | Synchronous within commit | High |
| P-7 | Callback | SWR refresh | DataFrameCache -> _swr_build_callback -> DataFrameCache | Registered callback via set_build_callback() | High |
| P-8 | Singleton | DataFrameCache factory | Module-level _dataframe_cache | get/set/reset pattern with SystemContext | High |
| P-9 | Singleton | WatermarkRepository | Class-level _instance with threading.Lock | get_instance/reset pattern | High |
| P-10 | Singleton | ModificationCheckCache | Module-level with threading.Lock | get/reset pattern with SystemContext | High |
| P-11 | Coalescing | DataFrameCacheCoalescer | Build requests | asyncio.Event wait/notify | High |
| P-12 | Coalescing | BuildCoordinator | Concurrent builds | asyncio.Future + Semaphore(4) | High |
| P-13 | Coalescing | RequestCoalescer | Staleness checks | 50ms window batching | High |
| P-14 | Circuit breaker | CircuitBreaker | Per-project DataFrameCache builds | 3 failures / 60s reset | High |
| P-15 | Write-through | TieredCacheProvider | Redis -> S3 | Synchronous, S3 failures non-fatal | High |
| P-16 | Write-through | WatermarkRepository | In-memory -> S3 | Fire-and-forget asyncio.create_task | High |
| P-17 | Promotion | TieredCacheProvider | S3 -> Redis on cold hit | promotion_ttl=3600s | High |
| P-18 | Hydration | DataFrameCache | S3 -> Memory on cold hit | Immediate, same request | High |
| P-19 | LKG fallback | DataFrameCache | Stale entry served with warning | When circuit open or past grace window | High |

### 9.2 External Integration Patterns

| # | Pattern | From | To | Classification | Confidence |
|---|---------|------|-----|----------------|------------|
| E-1 | Batch API | FreshnessCoordinator | Asana Batch API | GET /tasks/{gid}?opt_fields=modified_at, chunked by 10 | High |
| E-2 | Batch API | LightweightChecker | Asana Batch API | Same endpoint, for StalenessCheckCoordinator | High |
| E-3 | REST API | SWR callback | Asana API | Full task fetch via AsanaClient | High |
| E-4 | S3 Object Storage | S3CacheProvider | S3 | GetObject/PutObject/HeadObject/DeleteObject | High |
| E-5 | S3 Object Storage | ProgressiveTier | S3 via SectionPersistence | Parquet read/write | High |
| E-6 | S3 Object Storage | WatermarkRepository | S3 via DataFrameStorage | JSON watermark persistence | High |
| E-7 | Redis | RedisCacheProvider | ElastiCache | HSET/HGET/EXPIRE/SCAN/WATCH/MULTI | High |
| E-8 | Lambda self-invoke | Cache warmer | Own Lambda ARN | InvocationType=Event for continuation | High |
| E-9 | S3 checkpoint | CheckpointManager | S3 | Warming checkpoint for resume | High |
| E-10 | REST API | GID push | autom8_data service | POST sync endpoint after warming | High |

---

## 10. Unknowns

### Unknown: SaveSession DataFrameCache invalidation gap

- **Question**: Is it intentional that SaveSession's CacheInvalidator does NOT invalidate DataFrameCache (System B), while MutationInvalidator (REST routes) DOES for structural mutations? Or is this a gap that could lead to stale DataFrames after automation pipeline commits?
- **Why it matters**: If automation pipeline creates/deletes tasks (structural changes) via SaveSession, the project-level DataFrame in MemoryTier will not be invalidated until entity TTL expires. This could serve stale row counts for up to 3x the entity TTL (SWR grace window).
- **Evidence**: `persistence/cache_invalidator.py` calls `invalidate_task_dataframes()` but never calls `DataFrameCache.invalidate_project()`. `mutation_invalidator.py` calls both. The SaveSession CacheInvalidator does not import or reference DataFrameCache at all.
- **Suggested source**: Design intent from ADR-0059 or the original SaveSession author.

### Unknown: Insights cache TTL source

- **Question**: What TTL value is passed to `cache_response()` for insights caching? The `_cache.py` module takes `ttl: int` as a parameter.
- **Why it matters**: Without knowing the TTL, the insights cache freshness behavior is incomplete.
- **Evidence**: `clients/data/_cache.py:49` takes `ttl: int` as parameter. Topology inventory notes `EntryType.INSIGHTS` docstring says "TTL: 300s (default, configurable via AUTOM8_DATA_CACHE_TTL)" but this was not verified in the caller.
- **Suggested source**: Read `clients/data/client.py` or the DataServiceClient caller.

### Unknown: Story cache invalidation on non-mutation data changes

- **Question**: How are story cache entries invalidated when Asana webhooks deliver changes that did NOT originate from this service? MutationInvalidator handles REST mutations, but what about external changes (user actions in Asana UI)?
- **Why it matters**: If a user moves a task in Asana UI, the story cache may not reflect the new section_changed story until the stories are re-fetched. The `max_cache_age_seconds` parameter in `load_stories_incremental()` controls how long the short-circuit window is, but there's no push-based invalidation for external changes.
- **Evidence**: `load_stories_incremental()` at `stories.py:103-181` has a freshness probe (`is_stale(current_modified_at)`) that bypasses the `max_cache_age_seconds` short-circuit when the task's `modified_at` has changed. But this only works if the task cache itself is fresh, which depends on the entity cache TTL and freshness mode.
- **Suggested source**: Webhook handler code (if any), or the Lambda warmer which re-warms stories periodically.

### Unknown: Derived timeline invalidation on story update

- **Question**: When story cache entries are updated (via incremental fetch or Lambda warming), does anything invalidate the derived timeline cache? Or do timelines rely solely on their 300s TTL?
- **Why it matters**: A 300s staleness window for timelines could mean the section-timelines API returns outdated data for up to 5 minutes after a task moves to a new section.
- **Evidence**: `derived.py` has no invalidation mechanism beyond TTL. It is not referenced by `MutationInvalidator` or `CacheInvalidator`. `store_derived_timelines()` sets `ttl=300` with no upstream-triggered invalidation.
- **Suggested source**: API route handlers that compute and cache timelines.

### Unknown: Circuit breaker state persistence

- **Question**: Is circuit breaker state (per-project OPEN/CLOSED/HALF_OPEN) persisted across process restarts, or does it reset to CLOSED on cold start?
- **Why it matters**: If a project is in OPEN state due to repeated build failures, a container restart would reset the circuit breaker. This could be beneficial (retry after restart) or harmful (immediately re-trigger the same failures).
- **Evidence**: `CircuitBreaker` in `cache/dataframe/circuit_breaker.py` uses in-process `ProjectCircuit` state machines. No persistence mechanism was found in the code.
- **Suggested source**: Read `cache/dataframe/circuit_breaker.py`.

### Unknown: Redis SCAN-based clear_all_tasks scope

- **Question**: Does `RedisCacheProvider.clear_all_tasks()` clear ALL keys matching the `asana:tasks:*` pattern, including stories (STORIES entry type) and per-task DataFrames (DATAFRAME entry type)? Or only TASK/SUBTASKS/DETECTION?
- **Why it matters**: If `clear_all_tasks()` clears stories, it would force full story re-fetches for all tasks on the next warm cycle (no incremental `since` cursor). If it clears per-task DataFrames, it would force recomputation of all per-task rows.
- **Evidence**: Lambda `cache_invalidate.py:133` calls `TieredCacheProvider.clear_all_tasks()` which delegates to `RedisCacheProvider.clear_all_tasks()`. The name suggests "tasks" but the SCAN pattern is not visible in the topology inventory.
- **Suggested source**: Read `cache/backends/redis.py:clear_all_tasks()`.

---

## Handoff Readiness Checklist

- [x] Dependency-map artifact exists with all required sections (dependency graph, coupling analysis, shared model registry, integration pattern catalog)
- [x] Cross-cache dependency graph covers all 26 cache locations identified in topology-inventory
- [x] Coupling scores assigned to all connected cache pairs (8 pairs analyzed)
- [x] Confidence ratings (high/medium/low) assigned to all dependency findings and coupling scores
- [x] Coupling context checks (bounded context, intentionality, directionality) performed before scoring
- [x] Integration patterns classified for all intra-subsystem and external communication channels (19 internal + 10 external)
- [x] Shared models/schemas that appear across cache boundaries registered (9 shared models, 4 schema contracts)
- [x] Unknowns section documents ambiguous dependencies and unresolvable questions (6 unknowns)
- [x] (DEEP-DIVE) Critical path analysis for request-time, cold start, and Lambda warming
- [x] (DEEP-DIVE) SWR data flow diagram with complete lifecycle tracing including the fixed memory promotion bug
