---
domain: feat/cache-subsystem
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/cache/"
  - "./src/autom8_asana/protocols/cache.py"
  - "./.know/architecture.md"
  - "./.know/scar-tissue.md"
  - "./.know/design-constraints.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.97
format_version: "1.0"
---

# Multi-Tier Intelligent Cache Subsystem

## Purpose and Design Rationale

The cache subsystem reduces Asana API call volume 90%+ for stable workloads. Its design
contract: **cache failures must degrade gracefully — never cause 500s or data loss.**

Two distinct caching surfaces coexist:

- **Entity cache**: Individual task/project/section by GID, versioned by `modified_at`
  timestamp. Backed by Redis or EnhancedInMemory. Accessed via `CacheProvider` protocol.
- **DataFrame cache**: Computed Polars DataFrames keyed by `(entity_type, project_gid)`,
  versioned by watermark (max modified_at across all tasks in the project). Backed by
  Memory + progressive (S3/SectionPersistence) tiers. Accessed via `DataFrameCache`.

Default freshness intent: `FreshnessIntent.EVENTUAL` (Stale-While-Revalidate). Progressive
TTL extension doubles TTL on each successful `modified_at` comparison, up to 24h ceiling
(ADR-0133 origin).

**Why two surfaces?** Entity cache is GID-keyed and optimized for low-latency individual
lookups with version validation. DataFrame cache is project-keyed and optimized for bulk
read (schema-driven extraction of hundreds of rows), with SWR for background rebuilds
that are expensive (~2-4s for 3,800 entities).

**ADR-0025 (Big-bang S3 cutover)**: Legacy S3 entity cache cut over to Redis without
fallback. `autom8_adapter.py` embodies the migration surface — `create_autom8_cache_provider()`
wraps `RedisCacheProvider` with env-var resolution for the legacy `autom8` caller.

**ADR-0018**: Batch modification checking uses a 25-second in-memory TTL
(`ModificationCheckCache`) to prevent Asana batch API spam for freshness probes.

**ADR-0020**: Stories loaded incrementally using Asana `since` parameter; `last_fetched`
cursor stored in entry `metadata`.

**Completeness model** (TDD-CACHE-COMPLETENESS-001 / ADR-COMPLETENESS-001/002/003): Three
tiered levels — MINIMAL (GID only), STANDARD (GID + core fields for DataFrame extraction),
FULL (all fields). Cache entries tagged in `metadata["completeness_level"]`. Legacy entries
without tracking are UNKNOWN and conservatively treated as requiring re-fetch for STANDARD+.

## Conceptual Model

### Four-Tier Conceptual Stack

```
Tier 0: Models (CacheEntry, FreshnessIntent/State, CacheSettings, CacheMetrics, events,
         completeness, versioning, freshness_stamp, staleness_settings, mutation_event)
Tier 1: Policies (FreshnessPolicy, HierarchyIndex, LightweightChecker, RequestCoalescer,
         StalenessPolicy)
Tier 2: Backends / Providers (EnhancedInMemory, Redis, S3 backend, TieredCacheProvider,
         UnifiedTaskStore)
Tier 3: Integration (Factory, DataFrameCache, MutationInvalidator, FreshnessCoordinator,
         StalenessCheckCoordinator, HierarchyWarmer, ForceWarm, autom8_adapter,
         Batch/Loader/Stories/Derived/Dataframes helpers, Upgrader, SchemaProviders)
```

### Provider Selection Chain (CacheProviderFactory — ADR-0123)

1. `explicit_provider` parameter passed directly → use as-is
2. `config.enabled=False` → NullCacheProvider
3. `config.provider` explicit string → exact provider ("memory", "redis", "tiered", "none")
4. `settings.is_production=True` + `REDIS_HOST` → RedisCacheProvider
5. Fallback → EnhancedInMemoryCacheProvider

**Phase 1 note (GAP-003)**: `ASANA_CACHE_PROVIDER=tiered` in Phase 1 maps to Redis only.
S3 cold tier (TieredCacheProvider) is planned Phase 3 (EC-003 in design-constraints.md).

### Entity-Type TTLs (from `config.py:DEFAULT_ENTITY_TTLS`)

| Entity Type | TTL (seconds) |
|-------------|--------------|
| Business | 3600 |
| Unit / Contact | 900 |
| Offer | 180 |
| Process | 60 |
| Stories | 600 |
| DataFrame | 300 |
| PROJECT_SECTIONS | 1800 |

`SWR_GRACE_MULTIPLIER = 3.0` (LBC-005): grace window = TTL × 3.0. Entry in grace window
triggers background refresh but is served immediately (APPROACHING_STALE state).
`LKG_MAX_STALENESS_MULTIPLIER = 0.0` (LBC-005): when 0.0, max-staleness eviction check is
skipped entirely in `_check_freshness_and_serve`. Both are load-bearing constants — changing
them is a behavioral regression risk.

### FreshnessState Six-State Classification

| State | Meaning | Action |
|-------|---------|--------|
| FRESH | Within entity TTL | Serve immediately |
| APPROACHING_STALE | Past TTL, within SWR grace window | Serve + trigger background refresh |
| STALE | Beyond grace window, schema/watermark valid (LKG) | Serve with warning + trigger refresh |
| SCHEMA_INVALID | Schema version mismatch | Hard reject, evict from memory |
| WATERMARK_BEHIND | Source has newer data (watermark check) | Hard reject |
| CIRCUIT_FALLBACK | Circuit breaker open, serving LKG | Serve any valid cached entry |

### DataFrameCache Entry Lifecycle

```
get_async(project_gid, entity_type):
  1. Check circuit_breaker.is_open(project_gid) → if open: _get_circuit_lkg()
  2. memory_tier.get(cache_key) → check freshness → FRESH/SWR/LKG/reject
  3. progressive_tier.get_async(cache_key) → same freshness check
  4. Return None (caller triggers build via acquire_build_lock_async)

put_async(project_gid, entity_type, dataframe, watermark):
  1. progressive_tier.put_async() (source of truth)
  2. memory_tier.put()
  3. circuit_breaker.close(project_gid)
```

SWR background refresh: `asyncio.create_task(_swr_refresh_async)` deduped via
`coalescer.is_building(cache_key)`. Build callback registered via `set_build_callback()`.

### Stories Incremental Loading (ADR-0020)

`load_stories_incremental()` in `stories.py`:
1. Read cached stories + `metadata["last_fetched"]` cursor
2. If `max_cache_age_seconds` set and cache fresh enough → skip API call
3. Otherwise fetch only `since=last_fetched` (incremental)
4. Merge by GID (new overwrites old), sort by `created_at`
5. Update cache with new `last_fetched` cursor

Story entries NOT evicted on task UPDATE/MOVE mutations (preserves `since` cursor for
cheap incremental fetches). Only DELETE mutations hard-evict story entries.

### Derived Timeline Cache (TDD-SECTION-TIMELINE-REMEDIATION)

`derived.py` stores pre-computed `SectionTimeline` objects as `DerivedTimelineCacheEntry`
keyed by `"timeline:{project_gid}:{classifier_name}"`. TTL = 5 minutes. Computation cost
~2-4s for 3,800 entities; cached to avoid per-request rebuild.

### CompletenessLevel and Upgrader

`AsanaTaskUpgrader` (upgrader.py) implements `autom8y_cache.CompletenessUpgrader` protocol.
When a cached entry exists but has insufficient `CompletenessLevel` for the requested
operation, the upgrader fetches the task with expanded `opt_fields` and replaces the entry.
Levels: UNKNOWN(0), MINIMAL(10), STANDARD(20), FULL(30). STANDARD is recommended default
for DataFrame extraction (has `custom_fields`, `parent`, `memberships`).

## Implementation Map

### Package Inventory (52 files, `src/autom8_asana/cache/`)

**`backends/`** (4 files)
- `base.py` — `CacheBackendBase` template-method ABC. check-before-HTTP, store-on-miss pattern.
- `memory.py` — `EnhancedInMemoryCacheProvider` — thread-safe in-memory, LRU-style.
- `redis.py` — `RedisCacheProvider` — production backend. STRICT freshness responsibility
  documented: `redis.py:432` — "For STRICT freshness, caller must validate against source."
  (RISK-009)
- `s3.py` — `S3CacheProvider` — S3 cold-tier backend. Permanent S3 error codes
  (`_PERMANENT_S3_ERROR_CODES` at `core/retry.py:198`) must NOT feed circuit breaker
  (SCAR-S3-LOOP). S3 backend also has STRICT responsibility: `s3.py:505`.

**`models/`** (11 files)
- `entry.py` — `CacheEntry` (base), `DerivedTimelineCacheEntry` (subclass with
  classifier_name, source_entity_count, computation_duration_ms). `EntryType` enum:
  TASK, SUBTASKS, SECTION, STORIES, DETECTION, STRUC, DERIVED_TIMELINE.
- `freshness_unified.py` — `FreshnessIntent` (STRICT/EVENTUAL/IMMEDIATE) and
  `FreshnessState` (six-state). Consolidates four legacy enums. Zero external deps.
  Type aliases at old locations for backward compat (TENSION-008).
- `completeness.py` — `CompletenessLevel` IntEnum, field sets (MINIMAL/STANDARD/FULL),
  `infer_completeness_level()`, `get_entry_completeness()`, `is_entry_sufficient()`,
  `create_completeness_metadata()`.
- `settings.py` — `CacheSettings` Pydantic model.
- `metrics.py` — `CacheMetrics` (hit/miss/write/error counters + `hit_rate` property).
- `mutation_event.py` — `MutationEvent`, `EntityKind` (TASK/SECTION), `MutationType`
  (CREATE/UPDATE/DELETE/MOVE/ADD_MEMBER/REMOVE_MEMBER).
- `freshness_stamp.py` — `FreshnessStamp` with `with_staleness_hint()` for soft invalidation.
- `staleness_settings.py`, `versioning.py`, `events.py`, `errors.py` — supporting models.

**`policies/`** (5 files)
- `freshness_policy.py` — `FreshnessPolicy` — TTL/SWR decision logic.
- `staleness.py` — `check_batch_staleness()`, `partition_by_staleness()`,
  `check_entry_staleness()` — staleness detection for entity-cache operations.
- `hierarchy.py` — `HierarchyIndex` — parent chain traversal for cascade warming.
- `coalescer.py` — `RequestCoalescer` — policy-layer request coalescing.
- `lightweight_checker.py` — `LightweightChecker` — fast staleness probe without full fetch.

**`dataframe/`** (8 files including `tiers/`)
- `dataframe_cache.py` (at `integration/`) — `DataFrameCache` primary class (see Integration).
  Also defines `DataFrameCacheEntry` (memory/progressive tier, distinct from
  `cache/models/entry.py`'s `CacheEntry`) and `FreshnessInfo` side-channel.
- `circuit_breaker.py` — `CircuitBreaker`, `ProjectCircuit`, `CircuitState`
  (CLOSED/OPEN/HALF_OPEN). Per-project granularity. Thresholds: `failure_threshold=3`,
  `reset_timeout_seconds=60`, `success_threshold=1`. Stats: failures, opens, closes, rejects.
- `coalescer.py` — `DataFrameCacheCoalescer` — asyncio.Future-based thundering-herd prevention.
  `try_acquire_async()` / `release_async()` / `wait_async()` / `is_building()`.
- `build_coordinator.py` — `DataFrameBuildCoordinator` — orchestrates build + coalescer + cache.
- `warmer.py` — `DataFrameWarmer` — background warm-up orchestration.
- `factory.py` — `DataFrameCacheFactory` — creates DataFrameCache from config.
- `decorator.py` — `@dataframe_cache` decorator for client-layer caching.
  **Note (TENSION-008 / GAP-008)**: `decorator.py:147,184,204,223` contains four inline
  function-body imports from `api/exception_types.py` — undocumented runtime dep on API layer.
- `tiers/memory.py` — `MemoryTier` — dynamic heap-based limits, removes entries on overflow.
- `tiers/progressive.py` — `ProgressiveTier` — cold storage via SectionPersistence location.

**`integration/`** (15 files)
- `dataframe_cache.py` — **Hub**: `DataFrameCache` class (tiered get/put/invalidate/SWR),
  `DataFrameCacheEntry`, `FreshnessInfo`. Lookup: memory → progressive → None. Write:
  progressive (source of truth) → memory. Schema version from `SchemaRegistry` per entity type.
- `factory.py` — `CacheProviderFactory` (hub: wired from `api/lifespan.py:108`),
  `create_cache_provider()`. 4-step detection chain. Phase 1 tiered = Redis only.
- `mutation_invalidator.py` — `MutationInvalidator` — routes `MutationEvent` to entity
  cache invalidation + per-task DataFrame invalidation + project-level DataFrameCache
  invalidation. `fire_and_forget()` uses `asyncio.create_task`. `SoftInvalidationConfig`
  disabled by default (hard eviction is default behavior).
- `freshness_coordinator.py` — `FreshnessCoordinator` — coordinates freshness checks.
- `staleness_coordinator.py` — `StalenessCheckCoordinator` — staleness check orchestration.
- `hierarchy_warmer.py` — `HierarchyWarmer` — warms parent hierarchy chains.
- `force_warm.py` — Force-warm entry point for Lambda and admin routes.
- `autom8_adapter.py` — **Migration adapter (677 LOC, subsumed by census)**.
  `create_autom8_cache_provider()` — builds `RedisCacheProvider` from env vars for legacy
  `autom8` caller. `migrate_task_collection_loading()` — replaces legacy S3-based staleness
  checking with Redis-based intelligent caching. `warm_project_tasks()` for pre-warm.
  `check_redis_health()` for deployment verification. Per ADR-0025 big-bang cutover.
- `batch.py` — `ModificationCheckCache` (25s TTL, per-process singleton, thread-safe),
  `fetch_task_modifications()`, `ttl_cached_modifications()` decorator. ADR-0018 pattern.
- `loader.py` — `load_task_entry()`, `load_task_entries()` (concurrent via asyncio.gather),
  `load_batch_entries()` — unified cache-miss/stale-fetch patterns for entity-type loading.
- `stories.py` — `read_cached_stories()`, `read_stories_batch()` (chunked, chunk_size=500
  to avoid oversized Redis MGET — AMB-5 resolution), `load_stories_incremental()`,
  `filter_relevant_stories()`. ADR-0020 incremental loading.
- `derived.py` — `get_cached_timelines()`, `store_derived_timelines()`,
  `serialize_timeline()`, `deserialize_timeline()` for `SectionTimeline` ↔ cache dict.
  Key format: `"timeline:{project_gid}:{classifier_name}"`. TTL 5 minutes.
- `dataframes.py` — Per-task DataFrame invalidation helpers.
- `upgrader.py` — `AsanaTaskUpgrader` — `upgrade_async()` fetches task with expanded
  `opt_fields` at target `CompletenessLevel`. Tracks upgrade_calls/success/failure stats.
- `schema_providers.py` — Bridges SchemaRegistry to SDK entity registry (lifespan step 9).

**`providers/`** (2 files)
- `tiered.py` — `TieredCacheProvider` — Redis hot + S3 cold tier. S3 cold tier is Phase 3
  (GAP-003, EC-003). Currently only Redis tier active.
- `unified.py` — `UnifiedTaskStore` — unified entity access: wraps `CacheProvider` +
  optional `BatchClient` + default `FreshnessIntent`. Provides `get_async()` with completeness
  checking and `get_with_upgrade_async()` for transparent upgrade.

### Protocol Surface (`protocols/cache.py`)

`CacheProvider` protocol (structural typing, pure leaf):
- Basic: `get/set/delete`
- Versioned: `get_versioned/set_versioned`
- Batch: `get_batch/set_batch`
- Control: `warm()`, `check_freshness()`, `invalidate()`, `is_healthy()`, `get_metrics()`,
  `reset_metrics()`, `clear_all_tasks()`

`DataFrameCacheProtocol` protocol:
- `get_async(project_gid, entity_type, current_watermark) → DataFrameCacheEntry | None`
- `put_async(project_gid, entity_type, dataframe, watermark, build_result)`
- `invalidate(project_gid, entity_type)`
- `invalidate_project(project_gid)`
- `invalidate_on_schema_change(new_version)`
- `get_freshness_info(project_gid, entity_type) → FreshnessInfo | None`

`WarmResult` dataclass: `warmed`, `failed`, `skipped`, `total` property.

### Data Flow: Entity Cache (Read Path)

```
BaseClient.get_cached(task_gid, entry_type)
  → CacheProvider.get_versioned(task_gid, entry_type, freshness=EVENTUAL)
  → FreshnessIntent.STRICT: validates modified_at against current API value
  → FreshnessIntent.EVENTUAL: serves within TTL without API validation
  → On miss: fetch from Asana API → CacheProvider.set_versioned(task_gid, entry)
```

### Data Flow: DataFrame Cache (Build Path)

```
DataFrameService.get_dataframe(entity_type, project_gid)
  → DataFrameCache.get_async(project_gid, entity_type)
  → Memory hit (FRESH/SWR/LKG/circuit) → return entry
  → Progressive (S3) hit → hydrate memory tier → return entry
  → MISS:
      acquire_build_lock_async() → if acquired: caller builds
                                 → if not acquired: wait_for_build_async(timeout=30s)
      Build: DataFrameBuilder.build() → parallel fetch + extract + validate
      → DataFrameCache.put_async(project_gid, entity_type, df, watermark, build_result)
```

### Data Flow: Mutation Invalidation (Webhook Path)

```
POST /api/v1/webhooks/inbound
  → MutationInvalidator.fire_and_forget(MutationEvent)
    → asyncio.create_task(invalidate_async(event))
    → TASK mutation: invalidate TASK/SUBTASKS/DETECTION entries
                     → only DELETE: also invalidate STORIES
                     → CREATE/DELETE/MOVE/ADD_MEMBER/REMOVE_MEMBER:
                       DataFrameCache.invalidate_project(project_gid)
    → SECTION mutation: invalidate SECTION entry
                        → DataFrameCache.invalidate_project(project_gid)
```

### Test Coverage

63 unit test files in `tests/unit/cache/` plus sub-directories:
- `tests/unit/cache/dataframe/` — 11 files: `test_dataframe_cache.py`,
  `test_circuit_breaker.py`, `test_coalescer.py`, `test_memory_tier.py`,
  `test_progressive_tier.py`, `test_schema_version_validation.py`, `test_warmer.py`,
  `test_decorator.py`, `test_cache_entry.py`, `test_coalescer_dedup_metric.py`,
  `test_memory_tier_cgroup.py`
- `tests/unit/cache/integration/` — `test_force_warm.py`
- `tests/unit/cache/providers/` — `test_unified_parent_chain.py`
- Root unit cache files: `test_autom8_adapter.py`, `test_batch.py`, `test_build_coordinator.py`,
  `test_mutation_invalidator.py`, `test_mutation_soft_invalidation.py`, `test_stories.py`,
  `test_stories_batch.py`, `test_derived_cache.py`, `test_loader.py`, `test_unified.py`,
  `test_tiered.py`, `test_tiered_freshness.py`, `test_staleness.py`,
  `test_staleness_coordinator.py`, `test_freshness_coordinator.py`, `test_freshness_stamp.py`,
  `test_memory_backend.py`, `test_redis_backend.py`, `test_s3_backend.py`, `test_entry.py`,
  `test_factory.py`, `test_concurrency.py`, `test_dataframes.py`, + more.

Integration tests: `tests/integration/test_unified_cache_integration.py`,
`test_unified_cache_success_criteria.py`, `test_stories_cache_integration.py`,
`test_staleness_flow.py`, `test_hydration_cache_integration.py`.

## Boundaries and Failure Modes

### Scope Boundaries (what this subsystem does NOT do)

- Does NOT implement the DataFrame build pipeline (that is `dataframes/builders/`).
- Does NOT manage the preload warm-up orchestration (that is `api/preload/progressive.py`
  and `api/preload/legacy.py`).
- Does NOT handle cascade field resolution logic (that is `dataframes/builders/cascade_validator.py`).
- `TieredCacheProvider` S3 cold tier is **not implemented** in Phase 1 (GAP-003, EC-003).
  `ASANA_CACHE_PROVIDER=tiered` currently routes to Redis only.
- Soft invalidation (`SoftInvalidationConfig`) is **disabled by default** — config exists
  but production posture is hard eviction.

### SCAR Cluster (Cache Coherence — 6 scars)

| SCAR | Failure | Fix Location |
|------|---------|-------------|
| SCAR-003 | Stale S3 cache served after data change | Historical |
| SCAR-004 / DEF-005 | Warm-up and request path used separate CacheProvider instances (cache split) | `api/lifespan.py:108,126` (single shared instance) |
| SCAR-005 | CascadingFieldResolver 30% null rate — cascade warm-up ordering violated | `dataframes/builders/progressive.py:161,466`, `cascade_utils.py:27,289` |
| SCAR-006 | Cascade hierarchy warming gaps — parent GID not stored | `088fe332`, `4d652720` |
| SCAR-007 | S3 build_result schema version drift — stale parquet deserialization | Historical |
| SCAR-S3-LOOP | Permanent S3 error codes fed to circuit-breaker retry loop — infinite retry storm | `core/retry.py:198` `_PERMANENT_S3_ERROR_CODES` frozenset |

**DEF-005 invariant (SCAR-004 origin)**: A single `CacheProvider` instance MUST be created
at startup (`api/lifespan.py:108`) and shared across ALL paths:
- `app.state.cache_provider` (entity cache, created at step 4)
- `ClientPool` (`api/client_pool.py:201`)
- `MutationInvalidator` wired at step 10
- DataFrameCache wired at step 8

Any code path that creates a new `CacheProvider` instead of reusing `app.state.cache_provider`
recreates the SCAR-004 cache split.

### SCAR-S3-LOOP Defense

`_PERMANENT_S3_ERROR_CODES: frozenset[str]` at `core/retry.py:198`. S3 `NoSuchKey`,
`NoSuchBucket`, and related 4xx permanent codes must NOT enter the circuit-breaker retry
loop. These are permanent conditions that retrying cannot resolve. Regression test cluster
in `tests/unit/dataframes/test_storage.py`.

### Circuit Breaker Behavior (DataFrameCache)

- CLOSED → OPEN: after `failure_threshold=3` failures for a project
- OPEN → HALF_OPEN: after `reset_timeout_seconds=60`
- HALF_OPEN → CLOSED: on first success
- HALF_OPEN → OPEN: on failure
- When OPEN: `_get_circuit_lkg()` serves from memory or S3 without freshness check
  (LKG = Last Known Good). `CIRCUIT_FALLBACK` state in `FreshnessInfo`.

### Build Lock Coalescer

`DataFrameCacheCoalescer` uses `asyncio.Future` per cache key. `try_acquire_async()` returns
`True` to the first caller (should build), `False` to concurrent callers (should wait).
`wait_async(timeout=30s)` waits for the in-progress build. Deduplication via `is_building()`.
This prevents thundering-herd on cold cache startup.

### Configuration Boundaries

| Setting | Effect | Violation Risk |
|---------|--------|---------------|
| `SWR_GRACE_MULTIPLIER = 3.0` (LBC-005) | Grace window = TTL × 3.0 | Changing alters which entries serve stale vs. hard-reject |
| `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (LBC-005) | When 0.0, no max-staleness eviction | Non-zero value enables hard eviction of very stale entries |
| `config.enabled=False` | NullCacheProvider throughout | Disables all caching (safe for tests) |
| `ASANA_CACHE_PROVIDER=tiered` | Phase 1: maps to Redis. Phase 3: S3 cold tier | Callers expecting S3 behavior will not get it in Phase 1 |
| `REDIS_HOST` absent in production | Falls back to InMemory with warning | In-memory is non-durable and per-process |

### Error Path Analysis

- Cache transient errors (`CACHE_TRANSIENT_ERRORS` from `core/errors.py`): logged as WARNING,
  operation proceeds without cache (graceful degradation).
- `MutationInvalidator.fire_and_forget()`: background task. Errors logged via
  `_log_task_exception` done-callback. Never propagated to route handler.
- `DataFrameCache._swr_refresh_async()`: BROAD-CATCH at `dataframe_cache.py:1019` — must
  not crash background task. Failure increments SWR failure metric.
- `AsanaTaskUpgrader.upgrade_async()`: returns `None` on transient error. Caller decides
  whether to re-fetch or return partial result.
- `load_stories_incremental()`: full re-fetch on corrupted `last_fetched` metadata (missing
  cursor falls back to full fetch, not failure).

### Soft Invalidation (Disabled by Default)

`SoftInvalidationConfig(enabled=False)`. When enabled for specific entity kinds and mutation
types: reads entry, applies `freshness_stamp.with_staleness_hint(hint)`, writes back. Falls
back to hard eviction if entry not found or `freshness_stamp` is None (legacy entries).
ADR-003 fire-and-forget pattern.

### Integration Points (Boundaries Blur)

| Boundary | Location | Risk |
|----------|---------|------|
| `cache/dataframe/decorator.py` imports from `api/exception_types` | decorator.py:147,184,204,223 | TENSION-008 / GAP-008 — runtime dep on API layer |
| `DataFrameCache._check_freshness_and_serve()` imports from `config.py` | Inline function-body import | Circular risk mitigated by late import |
| `derived.py` imports from `models/business/section_timeline.py` | Line 20 | Crosses cache→models layer boundary |
| `upgrader.py` imports `autom8y_cache.CacheEntry` (external SDK) | Line 17 | Must not drift from internal `CacheEntry` contract |
| `autom8_adapter.py` — external-facing migration surface | No version gate | External callers (legacy autom8) call this directly |

```metadata
domain: feat/cache-subsystem
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.97
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 95
    weight: 0.30
    notes: >
      ADR-0025 (big-bang S3 cutover), ADR-0018 (25s TTL batch check), ADR-0020 (incremental
      stories), ADR-0123 (provider selection chain), completeness ADRs all documented.
      Two-surface design rationale (entity vs DataFrame) clearly stated. Tradeoffs noted
      (Phase 3 S3 cold tier deferred, soft invalidation disabled).
  conceptual_model:
    grade: A
    pct: 93
    weight: 0.25
    notes: >
      Four-tier conceptual stack mapped. FreshnessState six-state classification fully
      documented. SWR/LKG/circuit-fallback lifecycle described. Stories incremental cursor
      semantics documented. CompletenessLevel model and upgrader explained. Inter-feature
      relationships with dataframes/, clients/, api/lifespan fully mapped.
  implementation_map:
    grade: A
    pct: 95
    weight: 0.25
    notes: >
      All 52 source files inventoried across 5 sub-packages. Key types, entry points, and
      data flow for entity + DataFrame paths traced. Protocol surface documented. 63 unit
      test files in tests/unit/cache/ confirmed. Integration tests listed. All prior gaps
      (loader, batch, upgrader, stories, derived, autom8_adapter) now covered.
  boundaries_and_failure_modes:
    grade: A
    pct: 95
    weight: 0.20
    notes: >
      All 6 cache-coherence SCARs documented with fix locations. DEF-005 invariant stated
      explicitly with the single-shared-instance constraint. SCAR-S3-LOOP defense explained.
      Circuit breaker states and thresholds documented. Build coalescer thundering-herd
      defense described. Configuration load-bearing constants noted (LBC-005). Soft
      invalidation production posture clarified (disabled). Integration points where layer
      boundaries blur explicitly called out.
overall_grade: A
overall_pct: 94
prior_gaps_resolved:
  - "loader, batch, upgrader, stories, derived — all now documented"
  - "autom8_adapter 677-LOC migration adapter — purpose and API surface documented"
  - "soft invalidation production posture — disabled by default, SoftInvalidationConfig exists"
  - "DataFrame SWR rebuild failure handling — confirmed: BROAD-CATCH + build callback path"
  - "DerivedTimelineCacheEntry — new entry type for section timeline pre-computation"
  - "CompletenessLevel model — four levels, STANDARD for DataFrame extraction"
  - "DataFrameCacheProtocol — new structural protocol for DI"
  - "FreshnessState CIRCUIT_FALLBACK — documented LKG path on circuit open"
remaining_known_gaps:
  - "TENSION-001 migration (domain dataclasses → platform primitives) not cache-specific"
  - "UnifiedTaskStore.get_with_upgrade_async() internal logic not deeply traced"
```
