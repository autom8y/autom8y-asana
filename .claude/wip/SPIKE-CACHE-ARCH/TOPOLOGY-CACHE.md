# Topology Inventory: Cache Subsystem

**Scope**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/` -- all caching layers
**Analysis unit**: Single repo, directory-focused
**Date**: 2026-02-27
**Confidence methodology**: High = explicit build manifests/config; Medium = structural corroboration; Low = grep-only inference

---

## Table of Contents

1. [Service Catalog](#1-service-catalog)
2. [Tech Stack Inventory](#2-tech-stack-inventory)
3. [Cache Location Catalog](#3-cache-location-catalog)
   - [3.1 Formal Cache Subsystem (cache/)](#31-formal-cache-subsystem)
   - [3.2 In-Process Caching](#32-in-process-caching)
   - [3.3 External Cache Surfaces](#33-external-cache-surfaces)
   - [3.4 Cache-Adjacent Patterns](#34-cache-adjacent-patterns)
   - [3.5 Offline Caching](#35-offline-caching)
   - [3.6 Lambda Cache Operations](#36-lambda-cache-operations)
   - [3.7 Client-Side Caching](#37-client-side-caching)
4. [API Surface Map](#4-api-surface-map)
5. [Entry Point Catalog](#5-entry-point-catalog)
6. [TTL Configuration Reference](#6-ttl-configuration-reference)
7. [Singleton Reset Coordination](#7-singleton-reset-coordination)
8. [Unknowns](#8-unknowns)

---

## 1. Service Catalog

The cache subsystem is a library layer within the `autom8_asana` package, not an independent service. It spans six subdirectories under `cache/` plus scattered caching patterns throughout the codebase.

| Unit | Classification | Confidence |
|------|---------------|------------|
| `cache/` | Library (multi-tier caching layer) | High |
| `cache/backends/` | Library (storage adapters: memory, Redis, S3) | High |
| `cache/dataframe/` | Library (DataFrame-specific cache with SWR, circuit breaker, coalescing) | High |
| `cache/integration/` | Library (integration glue: factories, loaders, staleness coordination) | High |
| `cache/models/` | Library (data models: CacheEntry hierarchy, settings, freshness enums) | High |
| `cache/policies/` | Library (policy layer: staleness, coalescing, hierarchy, lightweight checks) | High |
| `cache/providers/` | Library (composite providers: tiered, unified store) | High |
| `_defaults/cache.py` | Library (fallback providers: NullCacheProvider, InMemoryCacheProvider) | High |
| `clients/data/_cache.py` | Module (insights response caching for DataServiceClient) | High |
| `lambda_handlers/cache_warmer.py` | Infrastructure (Lambda handler for cache pre-warming) | High |
| `lambda_handlers/cache_invalidate.py` | Infrastructure (Lambda handler for cache invalidation) | High |
| `api/preload/legacy.py` | Library (legacy cold-start preload, ADR-011 active fallback) | High |
| `query/offline_provider.py` | Library (in-process dict cache for CLI query mode) | High |
| `dataframes/watermark.py` | Library (watermark repository singleton for incremental sync tracking) | High |

---

## 2. Tech Stack Inventory

| Aspect | Detail | Confidence |
|--------|--------|------------|
| Language | Python 3.11+ | High |
| Framework | FastAPI (API layer), AWS Lambda (cache warming/invalidation) | High |
| Data format | Polars DataFrames (entity data), JSON dicts (task/story/detection entries) | High |
| External caches | Redis (ElastiCache), S3 (parquet + JSON), In-memory (dict/OrderedDict) | High |
| SDK primitives | `autom8y_cache` (HierarchyTracker, Freshness), `autom8y_log`, `autom8y_http` | High |
| Async framework | asyncio (SWR background refresh, batch API calls, Lambda self-invoke) | High |
| Thread safety | `threading.Lock` / `threading.RLock` (memory caches), `asyncio.Lock` (coalescer) | High |
| Serialization | JSON (Redis HASH values, S3 objects), Parquet (S3 DataFrames), gzip compression (S3 backend > 1024 bytes) | High |

---

## 3. Cache Location Catalog

### 3.1 Formal Cache Subsystem

#### 3.1.1 EnhancedInMemoryCacheProvider

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/memory.py`
- **Cache type**: In-process dict (thread-safe via `threading.Lock`)
- **What is cached**: CacheEntry objects (task data, subtasks, dependencies, stories, etc.)
- **TTL/invalidation**: Per-entry TTL (default 300s), TTL-based expiration on read, 10% LRU eviction at max_size (default 10,000)
- **Key structure**: Two separate dicts: `_simple_cache` (str -> value) and `_versioned_cache` (str -> {entry_type -> CacheEntry}), plus `_version_metadata` (str -> {entry_type -> metadata})
- **Entry points**: `get()`, `set()`, `get_versioned()`, `set_versioned()`, `get_batch()`, `invalidate()`
- **Exit points**: None (in-process only)
- **Tier relationship**: Standalone or hot tier in `TieredCacheProvider`
- **Confidence**: High

#### 3.1.2 RedisCacheProvider

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/redis.py`
- **Cache type**: External Redis (ElastiCache)
- **What is cached**: CacheEntry objects serialized as JSON in Redis HASH structures
- **TTL/invalidation**: Per-key TTL via Redis EXPIRE, WATCH/MULTI for atomic versioned updates, SCAN-based `clear_all_tasks()`
- **Key structure**:
  - Tasks: `asana:tasks:{gid}:{entry_type}` (HASH)
  - DataFrames: `asana:struc:{task_gid}:{project}` (HASH)
  - Version metadata: `asana:tasks:{gid}:_meta` (HASH)
  - Simple keys: `asana:simple:{key}` (STRING)
- **Entry points**: `get()`, `set()`, `get_versioned()`, `set_versioned()`, `get_batch()` (pipeline), `invalidate()`
- **Exit points**: Redis connection pool
- **Tier relationship**: Hot tier in `TieredCacheProvider`; standalone when selected via `CacheProviderFactory`
- **Degraded mode**: Yes -- tracks degraded state, reconnects after `reconnect_interval` (30s)
- **Confidence**: High

#### 3.1.3 S3CacheProvider

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/s3.py`
- **Cache type**: External S3 object storage
- **What is cached**: CacheEntry objects as JSON, gzip-compressed above 1024 bytes
- **TTL/invalidation**: Default TTL 604,800s (7 days), version metadata in S3 object metadata, HEAD-based freshness check
- **Key structure**:
  - Tasks: `{prefix}/tasks/{gid}/{entry_type}.json[.gz]`
  - DataFrames: `{prefix}/dataframe/{key}.json`
  - Simple: `{prefix}/simple/{key}.json`
- **Entry points**: `get()`, `set()`, `get_versioned()`, `set_versioned()`
- **Exit points**: S3 API calls (GetObject, PutObject, HeadObject, DeleteObject)
- **Tier relationship**: Cold tier in `TieredCacheProvider`
- **Confidence**: High

#### 3.1.4 TieredCacheProvider

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/providers/tiered.py`
- **Cache type**: Composite (Redis hot + S3 cold)
- **What is cached**: All CacheEntry types, coordinated across tiers
- **TTL/invalidation**: Write-through to both tiers. Read: hot first, cold fallback, promote to hot with `promotion_ttl=3600`. S3 failures never fail operations. Health = hot tier health only.
- **Key structure**: Delegates to underlying providers
- **Entry points**: `get()`, `set()`, `get_versioned()`, `set_versioned()`, `clear_all_tasks()`
- **Exit points**: Redis + S3 via composed providers
- **Tier relationship**: Top-level composite provider (ADR-0026)
- **Confidence**: High

#### 3.1.5 UnifiedTaskStore

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/providers/unified.py`
- **Cache type**: Composite (CacheProvider + HierarchyIndex + FreshnessCoordinator)
- **What is cached**: Task data with hierarchy awareness and completeness tracking
- **TTL/invalidation**: Freshness modes (IMMEDIATE/EVENTUAL/STRICT), completeness level checking, cascade invalidation via hierarchy, parent chain resolution
- **Key structure**: Delegates to underlying CacheProvider
- **Entry points**: `get_async()`, `get_batch_async()`, `put_async()`, `invalidate_async()`, `invalidate_cascade_async()`
- **Exit points**: CacheProvider + Asana Batch API (for freshness checks via FreshnessCoordinator)
- **Tier relationship**: Wraps any CacheProvider with hierarchy and freshness semantics
- **Confidence**: High

#### 3.1.6 NullCacheProvider

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/_defaults/cache.py` (line 25)
- **Cache type**: No-op (all operations succeed silently, never store)
- **What is cached**: Nothing
- **TTL/invalidation**: N/A
- **Entry points**: All CacheProvider interface methods (no-op implementations)
- **Tier relationship**: Used when caching is disabled (`CacheConfig.enabled=False` or `ASANA_CACHE_PROVIDER=none`)
- **Confidence**: High

#### 3.1.7 InMemoryCacheProvider (defaults)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/_defaults/cache.py` (line 136)
- **Cache type**: In-process dict with TTL and versioning
- **What is cached**: CacheEntry objects (simple key-value and versioned)
- **TTL/invalidation**: Per-entry TTL, thread-safe for basic usage
- **Entry points**: All CacheProvider interface methods
- **Tier relationship**: Default fallback when no Redis available; development/test default
- **Confidence**: High

---

#### 3.1.8 DataFrameCache

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframe_cache.py`
- **Cache type**: Composite (MemoryTier + ProgressiveTier), entity-type-aware SWR
- **What is cached**: `DataFrameCacheEntry` (polars DataFrame + watermark + schema_version + build_quality per project per entity type)
- **TTL/invalidation**: Entity-aware TTLs from `DEFAULT_ENTITY_TTLS` + `SWR_GRACE_MULTIPLIER` (3.0x) grace window. 6-state FreshnessState: FRESH, APPROACHING_STALE, STALE, SCHEMA_INVALID, WATERMARK_BEHIND, CIRCUIT_FALLBACK. SWR background refresh via `asyncio.create_task`. LKG (last-known-good) serves with `LKG_MAX_STALENESS_MULTIPLIER=0.0` (unlimited). Circuit breaker fallback.
- **Key structure**: `{entity_type}:{project_gid}` (e.g., `offer:1234567890`)
- **Entry points**: `get_async()`, `put_async()`, `get_or_build_async()`, `invalidate_project()`
- **Exit points**: MemoryTier (in-process), ProgressiveTier (S3 via SectionPersistence)
- **Tier relationship**: Two-tier: MemoryTier (hot) -> ProgressiveTier (cold/S3)
- **FreshnessInfo side-channel**: Thread-local `FreshnessInfo` for observability of freshness state per request
- **Confidence**: High

#### 3.1.9 MemoryTier (DataFrame)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/tiers/memory.py`
- **Cache type**: In-process OrderedDict with LRU eviction
- **What is cached**: `DataFrameCacheEntry` (polars DataFrames with metadata)
- **TTL/invalidation**: Entry-level TTL, heap-based memory limits (container memory detection via cgroup v2/v1, env var fallback, default 1GB), max entry count. LRU eviction via OrderedDict move-to-end.
- **Key structure**: `{entity_type}:{project_gid}`
- **Entry points**: `get_async()`, `put_async()`, `invalidate()`
- **Thread safety**: `threading.RLock`
- **Tier relationship**: Hot tier of DataFrameCache
- **Default config**: 30% heap fraction, 100 max entries (from `factory.py`)
- **Confidence**: High

#### 3.1.10 ProgressiveTier (DataFrame)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/tiers/progressive.py`
- **Cache type**: S3 storage via SectionPersistence
- **What is cached**: Polars DataFrames + watermark JSON
- **TTL/invalidation**: No TTL (persistence layer). Invalidation via `delete_async()`. Schema version tracked from watermark metadata.
- **Key structure**: `{entity_type}:{project_gid}` parsed to S3 path `dataframes/{project_gid}/`
- **Entry points**: `get_async()`, `put_async()`, `exists_async()`, `delete_async()`
- **Exit points**: S3 via `DataFrameStorage.load_dataframe()` / `SectionPersistence.write_final_artifacts_async()`
- **Tier relationship**: Cold tier of DataFrameCache; shares S3 location with `ProgressiveProjectBuilder`
- **Stats tracking**: reads, writes, read_errors, write_errors, bytes_read, bytes_written, not_found
- **Confidence**: High

#### 3.1.11 DataFrameCache Singleton (factory)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/factory.py`
- **Cache type**: Module-level singleton (`_dataframe_cache`)
- **What is cached**: Single DataFrameCache instance (manages MemoryTier + ProgressiveTier + coalescer + circuit breaker)
- **TTL/invalidation**: Singleton reset via `reset_dataframe_cache()`, registered with `SystemContext.reset_all()`
- **Initialization config**: MemoryTier (30% heap, 100 entries), ProgressiveTier (SectionPersistence), DataFrameCacheCoalescer (60s wait), CircuitBreaker (3 failures, 60s reset)
- **Entry points**: `initialize_dataframe_cache()`, `get_dataframe_cache()`, `set_dataframe_cache()`, `reset_dataframe_cache()`
- **SWR callback**: `_swr_build_callback` -- builds DataFrame via resolution strategy and puts into cache
- **Confidence**: High

---

#### 3.1.12 CacheEntry Hierarchy (Models)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/entry.py`
- **Cache type**: Data model (frozen dataclass hierarchy with `__init_subclass__` auto-registration)
- **What is cached**: N/A (model definition, not a cache location)
- **Subclass hierarchy**:
  - `CacheEntry` (base) -- directly constructible, backward compatible
  - `EntityCacheEntry` -- TASK, PROJECT, SECTION, USER, CUSTOM_FIELD; has completeness_level, opt_fields
  - `RelationshipCacheEntry` -- SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS; has parent_gid, relationship_count
  - `DataFrameMetaCacheEntry` -- DATAFRAME, PROJECT_SECTIONS, GID_ENUMERATION; requires project_gid, has schema_version
  - `DetectionCacheEntry` -- DETECTION; has detection_type
  - `DerivedTimelineCacheEntry` -- DERIVED_TIMELINE; has classifier_name, computation stats
- **EntryType enum**: TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DATAFRAME, PROJECT, SECTION, USER, CUSTOM_FIELD, DETECTION, PROJECT_SECTIONS, GID_ENUMERATION, INSIGHTS, DERIVED_TIMELINE
- **Polymorphic dispatch**: `CacheEntry.from_dict()` dispatches via `_type_registry` populated by `__init_subclass__`
- **Confidence**: High

#### 3.1.13 FreshnessIntent / FreshnessState (Models)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/freshness_unified.py`
- **Cache type**: Enum definitions
- **FreshnessIntent**: STRICT (always validate), EVENTUAL (serve within TTL), IMMEDIATE (serve without validation)
- **FreshnessState**: FRESH, APPROACHING_STALE, STALE, SCHEMA_INVALID, WATERMARK_BEHIND, CIRCUIT_FALLBACK
- **Confidence**: High

#### 3.1.14 CacheSettings / TTLSettings / OverflowSettings (Models)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/settings.py`
- **Cache type**: Configuration dataclasses
- **TTLSettings**: Resolution priority: project-specific > entry-type-specific > default (300s)
- **OverflowSettings**: Per-relationship thresholds (subtasks: 40, dependencies: 40, dependents: 40, stories: 100, attachments: 40). Above threshold = skip caching.
- **CacheSettings**: enabled=True, batch_check_ttl=25, reconnect_interval=30, max_batch_size=100
- **Confidence**: High

---

#### 3.1.15 CacheProviderFactory

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/factory.py`
- **Cache type**: Factory (not a cache location)
- **Provider selection chain** (per ADR-0123):
  1. Explicit `cache_provider` parameter
  2. `CacheConfig.enabled=False` -> NullCacheProvider
  3. `CacheConfig.provider` setting (memory, redis, tiered, none)
  4. Environment auto-detection: production+REDIS_HOST -> Redis; else -> InMemory
  5. InMemoryCacheProvider fallback
- **Also creates**: `UnifiedTaskStore` via `create_unified_store()`
- **Confidence**: High

#### 3.1.16 FreshnessCoordinator

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/freshness_coordinator.py`
- **Cache type**: Coordination layer (not a cache location)
- **What it does**: Batch freshness checks via Asana Batch API (`GET /tasks/{gid}?opt_fields=modified_at`), chunked by 10 (Asana limit)
- **Modes**: IMMEDIATE (return fresh without API call), EVENTUAL (check only expired entries), STRICT (always check via API)
- **Hierarchy check**: `check_hierarchy_async()` -- single root entity check covers all descendants
- **Stats**: total_checks, api_calls, fresh_count, stale_count, error_count, immediate_returns
- **Confidence**: High

#### 3.1.17 StalenessCheckCoordinator

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/staleness_coordinator.py`
- **Cache type**: Coordination layer (composes RequestCoalescer + LightweightChecker)
- **What it does**: Lightweight staleness detection with progressive TTL extension (ADR-0133/0134)
- **TTL extension formula**: `min(base * 2^count, max)` via immutable CacheEntry replacement
- **Actions on result**: UNCHANGED -> extend TTL, CHANGED -> return None (force refresh), ERROR -> invalidate + None
- **Confidence**: High

#### 3.1.18 RequestCoalescer

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/policies/coalescer.py`
- **Cache type**: Request batching layer (not a cache location)
- **What it does**: Batches staleness check requests within a 50ms window (ADR-0132). Deduplicates by GID. Immediate flush at max batch (100). `asyncio.Future`-based result distribution.
- **Window**: 50ms default, configurable
- **Max batch**: 100 default, configurable
- **Stats**: total_requests, total_batches, total_deduped
- **Confidence**: High

#### 3.1.19 LightweightChecker

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/policies/lightweight_checker.py`
- **Cache type**: API query layer (not a cache location)
- **What it does**: Batch `modified_at` checks via Asana Batch API with minimal payload (`opt_fields=modified_at`). Chunks into groups of 10.
- **Graceful degradation**: Returns None for failed/malformed/404 responses
- **Stats**: total_checks, total_api_calls
- **Confidence**: High

#### 3.1.20 Staleness Policy Functions

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/policies/staleness.py`
- **Cache type**: Pure functions (not a cache location)
- **Functions**: `check_entry_staleness()`, `check_batch_staleness()`, `partition_by_staleness()`
- **Logic**: EVENTUAL mode checks TTL only; STRICT mode also verifies against current `modified_at`
- **Confidence**: High

#### 3.1.21 HierarchyIndex

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/policies/hierarchy.py`
- **Cache type**: In-process index (wraps `autom8y_cache.HierarchyTracker`)
- **What is cached**: Bidirectional parent-child task relationships
- **TTL/invalidation**: No TTL (index grows, cleared on reset)
- **Thread safety**: Yes (via underlying HierarchyTracker)
- **Used for**: Cascade invalidation, parent chain resolution, ancestor traversal
- **Confidence**: High

---

#### 3.1.22 Story Cache (integration)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py`
- **Cache type**: CacheProvider-backed (Redis/S3 via versioned entries)
- **What is cached**: Story lists per task GID (CacheEntry with EntryType.STORIES)
- **TTL/invalidation**: Versioned by task `modified_at`. Incremental fetch via Asana `since` parameter. `max_cache_age_seconds` short-circuit (skip API when cache entry is young enough). Merge on incremental: dedupe by story GID, newer takes precedence, sort by `created_at`.
- **Key structure**: Task GID as key, `EntryType.STORIES`
- **Entry points**: `load_stories_incremental()`, `read_cached_stories()`, `read_stories_batch()`, `filter_relevant_stories()`, `get_latest_story_timestamp()`
- **Batch operations**: `read_stories_batch()` uses `cache.get_batch()` with chunking (500 per MGET)
- **Default story types**: assignee_changed, due_date_changed, section_changed, added_to_project, removed_from_project, marked_complete, marked_incomplete, enum_custom_field_changed, number_custom_field_changed
- **Confidence**: High

#### 3.1.23 Derived Timeline Cache (integration)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py`
- **Cache type**: CacheProvider-backed (Redis/S3 via versioned entries)
- **What is cached**: Pre-computed SectionTimeline data per (project_gid, classifier_name)
- **TTL/invalidation**: 300s (5 min) default TTL. EntryType.DERIVED_TIMELINE.
- **Key structure**: `timeline:{project_gid}:{classifier_name}`
- **Entry points**: `get_cached_timelines()`, `store_derived_timelines()`, `make_derived_timeline_key()`
- **Metadata**: entity_count, cache_hits, cache_misses, computation_duration_ms
- **Confidence**: High

#### 3.1.24 Per-Task DataFrame Cache (integration)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframes.py`
- **Cache type**: CacheProvider-backed (Redis/S3 via versioned entries)
- **What is cached**: Computed row (dataframe dict) per task+project combination
- **TTL/invalidation**: Versioned by task `modified_at`. Default TTL 300s. Force refresh option.
- **Key structure**: `{task_gid}:{project_gid}`, EntryType.DATAFRAME
- **Entry points**: `load_dataframe_cached()`, `load_batch_dataframes_cached()`, `invalidate_dataframe()`, `invalidate_task_dataframes()`, `make_dataframe_key()`, `parse_dataframe_key()`
- **Batch operations**: `load_batch_dataframes_cached()` runs all loads concurrently via `asyncio.gather()`
- **Confidence**: High

#### 3.1.25 ModificationCheckCache (integration)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/batch.py`
- **Cache type**: In-process dict singleton with short TTL
- **What is cached**: Asana API modification timestamps per task GID
- **TTL/invalidation**: 25s TTL (per ADR-0018), monotonic time, per-run isolation via run_id (ECS metadata -> hostname:PID)
- **Key structure**: `{run_id}:{gid}` -> `ModificationCheck(modified_at, fetched_at)`
- **Entry points**: `fetch_task_modifications()`, `get_modification_cache()`, `reset_modification_cache()`
- **Thread safety**: `threading.Lock` for singleton init
- **Singleton reset**: `reset_modification_cache()` registered with SystemContext
- **Decorator**: `@ttl_cached_modifications` wraps fetcher functions
- **Confidence**: High

#### 3.1.26 MutationInvalidator (integration)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py`
- **Cache type**: Stateless invalidation service
- **What it does**: Fire-and-forget cache invalidation from REST mutation endpoints via `asyncio.create_task`
- **Invalidation scope**:
  - Task mutations: entity cache (TASK, SUBTASKS, DETECTION) + per-task DataFrame + project-level DataFrameCache
  - Section mutations: SECTION entry + project DataFrames
- **Soft invalidation**: Configurable (disabled by default)
- **Entry points**: `invalidate_task_mutation()`, `invalidate_section_mutation()`, `fire_and_forget()`
- **Confidence**: High

---

### 3.2 In-Process Caching

#### 3.2.1 lru_cache: Bot PAT

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/auth/bot_pat.py`
- **Cache type**: `functools.lru_cache(maxsize=1)`
- **What is cached**: Bot Personal Access Token (single value)
- **TTL/invalidation**: None (process-lifetime)
- **Confidence**: Medium (from grep, pattern typical for singleton secrets)

#### 3.2.2 lru_cache: API Config

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/config.py`
- **Cache type**: `functools.lru_cache` (unbounded)
- **What is cached**: API configuration
- **TTL/invalidation**: None (process-lifetime)
- **Confidence**: Medium

#### 3.2.3 lru_cache: Field Normalizer

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/resolver/normalizer.py`
- **Cache type**: `functools.lru_cache(maxsize=1024)`
- **What is cached**: Normalized field name mappings
- **TTL/invalidation**: None (LRU eviction at 1024 entries)
- **Confidence**: Medium

#### 3.2.4 lru_cache: Tier2 Detection Patterns

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/detection/tier2.py`
- **Cache type**: `functools.lru_cache(maxsize=128)`
- **What is cached**: Compiled tier2 detection patterns
- **TTL/invalidation**: None (LRU eviction at 128 entries)
- **Confidence**: Medium

#### 3.2.5 WatermarkRepository Singleton

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/watermark.py`
- **Cache type**: In-process singleton (thread-safe via `threading.Lock`)
- **What is cached**: Per-project last-sync datetime watermarks (`dict[str, datetime]`)
- **TTL/invalidation**: No TTL. Write-through to S3 on `set_watermark()`. Loaded from S3 on startup via `load_from_persistence()`. Singleton reset via class method.
- **Persistence**: Optional S3 via DataFrameStorage
- **Thread safety**: Class-level lock for singleton creation, instance-level lock for operations
- **Confidence**: High

---

### 3.3 External Cache Surfaces

#### 3.3.1 Redis (ElastiCache)

- **Access via**: `RedisCacheProvider` (backend), `TieredCacheProvider` (hot tier), `CacheProviderFactory.create()`
- **Environment config**: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_SSL`
- **Key namespaces**:
  - `asana:tasks:{gid}:{entry_type}` -- versioned task data (HASH)
  - `asana:tasks:{gid}:_meta` -- version metadata (HASH)
  - `asana:struc:{task_gid}:{project}` -- DataFrame metadata (HASH)
  - `asana:simple:{key}` -- simple key-value (STRING)
- **Operations**: Pipeline for atomic HSET+EXPIRE, SCAN-based cleanup, WATCH/MULTI for optimistic locking
- **Confidence**: High

#### 3.3.2 S3 (Parquet + JSON)

- **Access via**: `S3CacheProvider` (backend), `ProgressiveTier` (DataFrame cold tier), `SectionPersistence`, `DataFrameStorage`
- **Key namespaces**:
  - `{prefix}/tasks/{gid}/{entry_type}.json[.gz]` -- versioned task data (via S3CacheProvider)
  - `{prefix}/dataframe/{key}.json` -- DataFrame metadata (via S3CacheProvider)
  - `dataframes/{project_gid}/` -- polars DataFrames as parquet + watermark JSON (via ProgressiveTier/SectionPersistence)
- **Compression**: gzip for JSON above 1024 bytes (S3CacheProvider)
- **Format**: parquet for DataFrames, JSON for watermarks and metadata
- **Confidence**: High

#### 3.3.3 In-Memory (process-scoped)

- **Access via**: `EnhancedInMemoryCacheProvider`, `InMemoryCacheProvider`, `MemoryTier`, various singleton dicts
- **Lifetime**: Process lifetime (cleared on restart or `SystemContext.reset_all()`)
- **Thread safety**: Varies by location (Lock, RLock, or none for single-threaded contexts)
- **Confidence**: High

---

### 3.4 Cache-Adjacent Patterns

#### 3.4.1 DataFrameCacheCoalescer (Thundering Herd Prevention)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/coalescer.py`
- **Pattern type**: `asyncio.Event`-based wait/notify
- **What it does**: Prevents thundering herd on cache miss. First request acquires build lock; concurrent requests wait on Event. Release notifies all waiters. Cleanup after 5s delay.
- **Default config**: 60s wait timeout (from factory.py)
- **Confidence**: High

#### 3.4.2 BuildCoordinator (Future-based Coalescing)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/build_coordinator.py`
- **Pattern type**: `asyncio.Future`-based (result sharing)
- **What it does**: Coalesces concurrent build requests by key `(project_gid, entity_type)`. `build_or_wait_async()` with global concurrency semaphore (`max_concurrent_builds=4`). `mark_invalidated()` for mutation-aware stale rejection. Deadlock prevention via lock ordering.
- **Confidence**: High

#### 3.4.3 CircuitBreaker (Per-Project Failure Isolation)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/circuit_breaker.py`
- **Pattern type**: Per-project `ProjectCircuit` state machine
- **States**: CLOSED -> OPEN (after `failure_threshold=3`) -> HALF_OPEN (after `reset_timeout_seconds=60`) -> CLOSED (on success)
- **What it does**: Prevents repeated build attempts for failing projects. Allows LKG fallback while circuit is open.
- **Default config**: 3 failures to open, 60s reset timeout (from factory.py)
- **Confidence**: High

#### 3.4.4 @dataframe_cache Decorator

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/decorator.py`
- **Pattern type**: Class decorator for resolution strategies
- **What it does**: Wraps `resolve()` method with cache-check -> acquire lock -> wait-or-build flow. Returns 503 HTTPException on timeout/failure with `retry_after_seconds`. Injects `self._cached_dataframe`.
- **Confidence**: High

#### 3.4.5 CacheWarmer (Pre-Deployment Warming)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/warmer.py`
- **Pattern type**: Priority-based warming
- **What it does**: Warms DataFrameCache for all entity types in priority order: offer, unit, business, contact, asset_edit, asset_edit_holder. Strict mode fails on any warm failure.
- **Entry point**: `warm_all_async()`
- **Confidence**: High

#### 3.4.6 Legacy Preload (ADR-011 Active Fallback)

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/legacy.py`
- **Pattern type**: Cold-start preload
- **What it does**: Loads watermarks from S3, loads DataFrames + indices from S3DataFrameStorage, incremental catch-up via ProgressiveProjectBuilder, populates DataFrameCache singleton + watermark repo + GidLookupIndex. Target <5s cold start.
- **Entry point**: `_preload_dataframe_cache()`
- **Tier relationship**: Populates DataFrameCache singleton (MemoryTier) from S3 on cold start
- **Confidence**: High

#### 3.4.7 SWR (Stale-While-Revalidate)

- **Implemented in**: `DataFrameCache.get_async()` (`cache/integration/dataframe_cache.py`)
- **Pattern type**: Background refresh via `asyncio.create_task`
- **What it does**: When freshness state is APPROACHING_STALE, serves stale data immediately and triggers background rebuild. Grace window = `SWR_GRACE_MULTIPLIER` (3.0) * entity TTL. Build callback in `factory.py` (`_swr_build_callback`).
- **Confidence**: High

---

### 3.5 Offline Caching

#### 3.5.1 OfflineDataFrameProvider

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/offline_provider.py`
- **Cache type**: In-process dict (`_cache: dict[str, pl.DataFrame]`)
- **What is cached**: Polars DataFrames keyed by project_gid
- **TTL/invalidation**: None (process-lifetime). Single-threaded CLI context.
- **Entry points**: `get_dataframe()` -- checks cache, loads from S3 parquets on miss
- **Exit points**: S3 via `load_project_dataframe_with_meta()`
- **Used by**: `python -m autom8_asana.query` CLI
- **Confidence**: High

---

### 3.6 Lambda Cache Operations

#### 3.6.1 Lambda Cache Warmer

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py`
- **Pattern type**: Scheduled Lambda (cache pre-warming)
- **What it does**: Timeout detection (2 min buffer), checkpoint-based resume via S3 CheckpointManager, self-invoke continuation for long warming runs, story cache warming piggybacked on DataFrame warming, GID mapping push. CloudWatch metrics emission.
- **Caches warmed**: DataFrameCache (all entity types), story cache (per-task)
- **Confidence**: High

#### 3.6.2 Lambda Cache Invalidation

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_invalidate.py`
- **Pattern type**: On-demand Lambda (cache clearing)
- **What it does**: Three invalidation modes:
  - `clear_tasks`: Redis + S3 via `TieredCacheProvider.clear_all_tasks()`
  - `clear_dataframes`: Schema version bump trick (forces schema mismatch -> hard reject)
  - `invalidate_project`: Targeted manifest + section parquet deletion via SectionPersistence
- **Confidence**: High

---

### 3.7 Client-Side Caching

#### 3.7.1 DataServiceClient Insights Cache

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_cache.py`
- **Cache type**: CacheProvider-backed (delegates to whatever provider is injected)
- **What is cached**: `InsightsResponse` objects (serialized to dict with data, metadata, request_id, warnings, cached_at timestamp)
- **TTL/invalidation**: Configurable TTL passed by caller. No explicit invalidation (TTL-based expiry only).
- **Key structure**: `insights:{factory}:{canonical_key}` (e.g., `insights:account:pv1:+17705753103:chiropractic`)
- **Entry points**: `cache_response()`, `get_stale_response()`, `build_cache_key()`
- **Stale fallback**: `get_stale_response()` returns stale data with `is_stale=True` and `cached_at` on service failure (graceful degradation)
- **PII**: Cache keys are PII-masked in logs via `mask_pii_in_string()`
- **Error handling**: Graceful degradation -- cache failures logged but never break requests
- **Confidence**: High

---

## 4. API Surface Map

### Public Python API (cache package)

The `cache/__init__.py` exports 80+ symbols organized in 4 tiers. Key public interfaces:

| Export | Module | Interface Type | Confidence |
|--------|--------|---------------|------------|
| `CacheEntry`, `EntryType` | `models/entry.py` | Data model | High |
| `Freshness` (alias: `FreshnessIntent`) | `models/freshness_unified.py` / `autom8y_cache` | Enum | High |
| `FreshnessIntent`, `FreshnessState` | `models/freshness_unified.py` | Enum | High |
| `CacheSettings`, `TTLSettings`, `OverflowSettings` | `models/settings.py` | Config | High |
| `CacheMetrics`, `CacheEvent` | `models/metrics.py` | Observability | High |
| `check_entry_staleness`, `check_batch_staleness`, `partition_by_staleness` | `policies/staleness.py` | Pure functions | High |
| `RequestCoalescer` | `policies/coalescer.py` | Batching | High |
| `HierarchyIndex` | `policies/hierarchy.py` | Index | High |
| `LightweightChecker` | `policies/lightweight_checker.py` | API checker | High |
| `TieredCacheProvider`, `TieredConfig` | `providers/tiered.py` | Composite provider | High |
| `UnifiedTaskStore` | `providers/unified.py` | Unified store | High |
| `CacheProviderFactory` | `integration/factory.py` | Factory | High |
| `MutationInvalidator` | `integration/mutation_invalidator.py` | Invalidation | High |
| `load_task_entry`, `load_task_entries`, `load_batch_entries` | `integration/loader.py` | Multi-entry loading | High |
| `load_stories_incremental`, `read_cached_stories`, `read_stories_batch` | `integration/stories.py` | Story cache ops | High |
| `load_dataframe_cached`, `invalidate_dataframe` | `integration/dataframes.py` | Per-task DF cache | High |
| `get_cached_timelines`, `store_derived_timelines` | `integration/derived.py` | Timeline cache | High |
| `create_autom8_cache_provider`, `check_redis_health` | `integration/autom8_adapter.py` | Redis setup | High |
| `register_asana_schemas` | `integration/schema_providers.py` | Lazy import via `__getattr__` | High |

### Lazy Import (circular dependency break)

`register_asana_schemas` is resolved via `__getattr__` in `cache/__init__.py` to break the cycle: `schema_providers -> dataframes -> models.business -> cache`.

### Defensive Imports

Two imports from `autom8y_cache` are wrapped in try/except for Lambda compatibility:
- `Freshness` -- falls back to local `FreshnessIntent`
- `HierarchyTracker` -- falls back to `None`

---

## 5. Entry Point Catalog

### Initialization Flows

| Entry Point | What It Initializes | Where |
|-------------|-------------------|-------|
| `CacheProviderFactory.create(config)` | Creates appropriate CacheProvider (Null/Memory/Redis/Tiered) based on env | `integration/factory.py` |
| `CacheProviderFactory.create_unified_store()` | Creates UnifiedTaskStore with provider + batch client + freshness mode | `integration/factory.py` |
| `initialize_dataframe_cache()` | Creates DataFrameCache singleton with MemoryTier + ProgressiveTier + coalescer + circuit breaker | `dataframe/factory.py` |
| `get_dataframe_cache()` | Returns existing singleton or raises | `dataframe/factory.py` |
| `get_modification_cache()` | Returns ModificationCheckCache singleton (creates on first call) | `integration/batch.py` |
| `get_watermark_repo()` | Returns WatermarkRepository singleton (creates on first call) | `dataframes/watermark.py` |

### Configuration Loading

| Config | Source | Key Env Vars |
|--------|--------|-------------|
| `CacheConfig` | `config.py` dataclass with env overrides | `ASANA_CACHE_ENABLED`, `ASANA_CACHE_PROVIDER`, `ASANA_CACHE_TTL_DEFAULT`, `ASANA_ENVIRONMENT` |
| `DEFAULT_TTL` | `config.py` constant | None (hardcoded 300) |
| `DEFAULT_ENTITY_TTLS` | `config.py` derived from EntityRegistry | None (code-defined per entity type) |
| `SWR_GRACE_MULTIPLIER` | `config.py` constant | None (hardcoded 3.0) |
| `LKG_MAX_STALENESS_MULTIPLIER` | `config.py` constant | None (hardcoded 0.0 = unlimited) |
| Redis connection | `settings.py` | `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_SSL` |
| S3 location | `S3LocationConfig` | `AUTOM8_S3_BUCKET`, `AUTOM8_S3_PREFIX` |

### Cold Start Paths

1. **Progressive preload** (primary): Loads watermarks + DataFrames from S3 into MemoryTier
2. **Legacy preload** (ADR-011 fallback): Same target, different loading strategy, <5s budget
3. **Lambda warmer**: Scheduled pre-deployment warm of all entity types

---

## 6. TTL Configuration Reference

### Entity-Level TTLs (from CacheConfig / EntityRegistry)

| Entity Type | Default TTL | Source |
|-------------|------------|--------|
| Default fallback | 300s (5 min) | `config.py:DEFAULT_TTL` |
| business | 3600s (1 hour) | EntityRegistry |
| contact | 900s (15 min) | EntityRegistry |
| unit | 900s (15 min) | EntityRegistry |
| offer | 180s (3 min) | EntityRegistry |
| process | 60s (1 min) | EntityRegistry |
| location | 3600s (1 hour) | EntityRegistry |
| hours | 3600s (1 hour) | EntityRegistry |

### System-Level TTLs

| Parameter | Value | Source |
|-----------|-------|--------|
| Default CacheEntry TTL | 300s | `models/entry.py` |
| S3CacheProvider default TTL | 604,800s (7 days) | `backends/s3.py` |
| SWR grace multiplier | 3.0x entity TTL | `config.py:SWR_GRACE_MULTIPLIER` |
| LKG max staleness | 0.0 (unlimited) | `config.py:LKG_MAX_STALENESS_MULTIPLIER` |
| ModificationCheckCache TTL | 25s | `integration/batch.py` |
| Derived timeline TTL | 300s (5 min) | `integration/derived.py` |
| Redis reconnect interval | 30s | `models/settings.py` |
| TieredCacheProvider promotion TTL | 3600s (1 hour) | `providers/tiered.py` |
| Coalescer window | 50ms | `policies/coalescer.py` |
| Circuit breaker reset timeout | 60s | `dataframe/circuit_breaker.py` |
| Circuit breaker failure threshold | 3 failures | `dataframe/circuit_breaker.py` |
| Coalescer wait timeout | 60s | `dataframe/factory.py` |
| Max concurrent builds | 4 | `dataframe/build_coordinator.py` |

### Overflow Thresholds (skip caching above)

| Relationship Type | Threshold |
|-------------------|-----------|
| subtasks | 40 |
| dependencies | 40 |
| dependents | 40 |
| stories | 100 |
| attachments | 40 |

---

## 7. Singleton Reset Coordination

All cache-relevant singletons register with `SystemContext.reset_all()` for test isolation:

| Singleton | Reset Function | File |
|-----------|---------------|------|
| DataFrameCache | `reset_dataframe_cache()` | `cache/dataframe/factory.py` |
| ModificationCheckCache | `reset_modification_cache()` | `cache/integration/batch.py` |
| Settings | `reset_settings()` | `settings.py` |
| EntityProjectRegistry | `EntityProjectRegistry.reset()` | `services/resolver.py` |
| MetricRegistry | `MetricRegistry.reset()` | `metrics/registry.py` |
| HolderRegistry | `reset_holder_registry()` | `persistence/holder_construction.py` |
| EntityRegistry | `_reset_entity_registry()` | `core/entity_registry.py` |
| Business Bootstrap | `reset_bootstrap()` | `models/business/_bootstrap.py` |

---

## 8. Unknowns

### Unknown: Entity-specific TTL values from EntityRegistry

- **Question**: What are the exact TTL values for all entity types registered in `core/entity_registry.py`? The `DEFAULT_ENTITY_TTLS` dict is dynamically built from `EntityRegistry.all_descriptors()` at import time. The values documented in `CacheConfig` docstring (business=3600, contact=900, etc.) may be stale relative to the actual registry.
- **Why it matters**: Accurate TTL values are needed to understand cache freshness behavior per entity type.
- **Evidence**: `config.py` line 108-112 builds `DEFAULT_ENTITY_TTLS` dynamically from registry. Docstring values may not match runtime values.
- **Suggested source**: Read `core/entity_registry.py` EntityDescriptor definitions.

### Unknown: connection_manager delegation in RedisCacheProvider

- **Question**: What is the `connection_manager` parameter in `RedisCacheProvider` and when is it used vs. direct Redis connection?
- **Why it matters**: Affects understanding of Redis connection lifecycle and pooling behavior.
- **Evidence**: `backends/redis.py` accepts optional `connection_manager` parameter. Mentioned as "forward scaffolding" in COMPAT-PURGE.
- **Suggested source**: Read `cache/backends/redis.py` constructor and any ConnectionManager class.

### Unknown: CacheWarmer resolution strategy internals

- **Question**: What resolution strategies does `CacheWarmer` invoke for each entity type? The warmer calls `_build_dataframe` methods but the actual resolution strategy classes were not scanned.
- **Why it matters**: Understanding the build path is needed to trace the full warm-through pipeline.
- **Evidence**: `dataframe/warmer.py` references resolution strategies by entity type.
- **Suggested source**: Read `dataframes/resolver/` directory for strategy implementations.

### Unknown: Insights cache TTL source

- **Question**: Where is the TTL for insights caching (`EntryType.INSIGHTS`) configured? The `_cache.py` module receives TTL as a parameter from the caller.
- **Why it matters**: Without knowing the caller's TTL source, the insights cache freshness behavior is incomplete.
- **Evidence**: `clients/data/_cache.py` line 49 takes `ttl: int` as a parameter. EntryType.INSIGHTS docstring says "TTL: 300s (default, configurable via AUTOM8_DATA_CACHE_TTL)".
- **Suggested source**: Read `clients/data/client.py` or DataServiceClient to find where TTL is passed.

### Unknown: S3 checkpoint format for Lambda warmer

- **Question**: What does the S3 CheckpointManager store and how does the resume protocol work across Lambda invocations?
- **Why it matters**: Understanding checkpoint format is needed to trace the full Lambda warming lifecycle.
- **Evidence**: `lambda_handlers/cache_warmer.py` references CheckpointManager for checkpoint-based resume.
- **Suggested source**: Read the CheckpointManager class definition.

---

## Handoff Readiness Checklist

- [x] Topology-inventory artifact exists with all required sections
- [x] Every target unit has been scanned and classified (26 cache locations cataloged)
- [x] Confidence ratings assigned to all classifications and API surface identifications
- [x] API surfaces identified with endpoint paths, protocols, and interface detail
- [x] Tech stack inventory includes dependency manager information (autom8y_cache, autom8y_log, autom8y_http SDK primitives)
- [x] Unknowns section documents units that could not be fully scanned or classified (5 unknowns)
- [x] No target unit was skipped without documented reason
