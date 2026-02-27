# Architecture Assessment: Cache Subsystem

**Scope**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/` -- cache architectural health
**Date**: 2026-02-27
**Upstream Artifacts**: TOPOLOGY-CACHE.md (26 cache locations), DEPENDENCY-CACHE.md (tier systems, freshness propagation, coupling)
**Complexity**: DEEP-DIVE
**Agent**: structure-evaluator

---

## Table of Contents

1. [Anti-Pattern Findings](#1-anti-pattern-findings)
2. [Boundary Assessment](#2-boundary-assessment)
3. [Single Points of Failure (SPOF) Register](#3-single-points-of-failure-register)
4. [Risk Register](#4-risk-register)
5. [Architectural Philosophy Extraction](#5-architectural-philosophy-extraction)
6. [Unknowns](#6-unknowns)

---

## 1. Anti-Pattern Findings

### AP-1: SaveSession / MutationInvalidator Invalidation Asymmetry

**Severity**: HIGH
**Confidence**: HIGH
**Affected Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py` (lines 160-195)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py` (lines 170-181, 347-363)

**Description**: Two parallel invalidation paths exist for cache management: `CacheInvalidator` (used by SaveSession batch operations) and `MutationInvalidator` (used by REST mutation endpoints). These two paths invalidate different scopes of cache:

| Invalidation Path | Entity Cache (System A) | Per-Task DataFrame (System A) | Project-Level DataFrameCache (System B) |
|---|---|---|---|
| MutationInvalidator (REST routes) | TASK, SUBTASKS, DETECTION | Yes (per-task DF entries) | Yes (structural mutations only) |
| CacheInvalidator (SaveSession) | TASK, SUBTASKS, DETECTION | Yes (per-task DF entries) | **NO** |

When SaveSession commits a structural change (task CREATE/DELETE), the project-level DataFrameCache (MemoryTier) is NOT invalidated. The stale DataFrame remains in memory until its entity-aware TTL expires (e.g., 180s for offers, 900s for contacts) or the SWR grace window elapses (3x TTL).

**Evidence**: `CacheInvalidator._invalidate_dataframe_caches()` at line 160 calls `invalidate_task_dataframes()` only. It does not import or reference `DataFrameCache` at all. Meanwhile, `MutationInvalidator._handle_task_mutation()` at lines 174-181 explicitly calls `self._invalidate_project_dataframes()` for structural mutations.

**False-positive check**: This asymmetry is documented in the dependency map (section 3.2) as a known difference, but the DEPENDENCY-CACHE.md lists it as an "Unknown" -- meaning the upstream analyst could not determine if this is intentional or a gap. The SaveSession `CacheInvalidator` was extracted per ADR-0059 for SRP, but ADR-0059 scope did not mention DataFrameCache. The gap predates the MutationInvalidator's introduction of DataFrameCache invalidation, suggesting it was never backported.

**Impact**: After a SaveSession batch commit that creates or deletes tasks, API consumers may receive stale DataFrame data for up to 540s (offer: 180s TTL * 3.0 SWR grace) or 2,700s (contact: 900s TTL * 3.0). Row counts, aggregations, and entity listings will be incorrect during this window.

---

### AP-2: Derived Timeline Cache -- No Upstream-Triggered Invalidation

**Severity**: MEDIUM
**Confidence**: HIGH
**Affected Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` (lines 30-32, 106-124)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py` (no reference to derived cache)

**Description**: The derived timeline cache uses a fixed 300s TTL (`_DERIVED_TIMELINE_TTL = 300` at line 32) with no upstream-triggered invalidation. When stories change, no signal propagates to invalidate the derived timeline entries. MutationInvalidator does not reference the derived cache at all. The only freshness mechanism is passive TTL expiry.

**Evidence**: `store_derived_timelines()` at line 115 sets `ttl=_DERIVED_TIMELINE_TTL` (300s). The `MutationInvalidator` class does not contain any reference to `EntryType.DERIVED_TIMELINE`, `derived`, or timeline invalidation. The `CacheInvalidator` (SaveSession) similarly has no derived timeline awareness.

**False-positive check**: The 300s TTL is documented as a balance between "freshness (stories may update) vs. computation cost (~2-4s for 3,800 entities)" (line 31 comment). This may be an intentional trade-off -- timeline data is an analytics/reporting surface where eventual consistency within 5 minutes is acceptable. However, this makes the section-timelines API response potentially 5 minutes stale relative to task movements.

**Impact**: API consumers calling the section-timelines endpoint may receive data up to 300s behind actual task state. For real-time dashboards or operational decision-making, this staleness may be significant.

---

### AP-3: Unlimited LKG Staleness (LKG_MAX_STALENESS_MULTIPLIER = 0.0)

**Severity**: MEDIUM
**Confidence**: HIGH
**Affected Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/config.py` (line 102)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframe_cache.py` (lines 444-465)

**Description**: The `LKG_MAX_STALENESS_MULTIPLIER` is set to `0.0`, which per the comment means "unlimited (serve forever if schema/watermark valid)". The code at `dataframe_cache.py` line 450 confirms: `if LKG_MAX_STALENESS_MULTIPLIER > 0:` -- meaning the max-age check is never executed. Any DataFrame entry that passes the schema version and watermark checks will be served indefinitely, regardless of age.

**Evidence**: `config.py` line 100-102:
```python
# 0.0 = unlimited (serve forever if schema/watermark valid)
# >0.0 = serve for up to LKG_MAX_STALENESS_MULTIPLIER * entity_TTL seconds
LKG_MAX_STALENESS_MULTIPLIER: float = 0.0
```

The `_check_freshness_and_serve()` method at line 450 enters the `if LKG_MAX_STALENESS_MULTIPLIER > 0:` block only when the multiplier is positive. At 0.0, the entry is always served as LKG with a warning log and SWR refresh trigger.

**False-positive check**: This is likely an intentional availability-over-freshness trade-off. The system prefers serving stale data over returning errors. Combined with SWR background refresh, the expectation is that stale data is temporary -- an SWR task will eventually update the entry. However, if SWR consistently fails (e.g., Asana API down), the system will serve arbitrarily stale data without bound.

**Impact**: If SWR refresh fails persistently AND the circuit breaker opens (after 3 failures), the system will serve last-known-good data indefinitely. For entity types with short TTLs like `offer` (180s) or `process` (60s), this could mean serving data hours or days old after an extended outage.

---

### AP-4: Dual Coalescing Systems (DataFrameCacheCoalescer + BuildCoordinator)

**Severity**: LOW
**Confidence**: HIGH
**Affected Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/coalescer.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/build_coordinator.py`

**Description**: Two separate coalescing mechanisms exist for DataFrame builds:
1. **DataFrameCacheCoalescer**: `asyncio.Event`-based wait/notify pattern, keyed by cache key string, 60s timeout, used by DataFrameCache directly via `acquire_build_lock_async()` / `release_build_lock_async()`.
2. **BuildCoordinator**: `asyncio.Future`-based result sharing, keyed by `(project_gid, entity_type)` tuple, 60s timeout, max 4 concurrent builds via `Semaphore`, mutation-aware stale rejection via `mark_invalidated()`.

The BuildCoordinator explicitly documents itself as wrapping the existing DataFrameCacheCoalescer (line 8: "Wraps the existing DataFrameCacheCoalescer (ADR-BC-002) rather than replacing it, allowing incremental migration across phases").

**Evidence**: Both classes are initialized in `factory.py` -- `DataFrameCacheCoalescer` is passed to `DataFrameCache` constructor (line 170-172), and `BuildCoordinator` exists as a separate module. The coalescer is directly wired into DataFrameCache while BuildCoordinator is used by the `@dataframe_cache` decorator path.

**False-positive check**: This is explicitly documented as an incremental migration pattern (ADR-BC-002). The BuildCoordinator adds capabilities the coalescer lacks (Future-based result sharing, global concurrency limits, stale rejection). However, the migration appears to be incomplete -- both systems remain active simultaneously, creating cognitive complexity for maintainers and subtle behavior differences depending on the code path (decorator vs. direct DataFrameCache usage).

**Impact**: Low operational risk since both systems serve the same purpose (prevent thundering herd). The risk is primarily cognitive -- a developer modifying build coalescing behavior must understand both systems and which paths use which.

---

### AP-5: `lru_cache` Without Invalidation on API Config

**Severity**: LOW
**Confidence**: MEDIUM
**Affected Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/config.py` (line 90-97)

**Description**: The `get_settings()` function in `api/config.py` uses `@lru_cache` (unbounded) to cache `ApiSettings`. This persists for the entire process lifetime with no invalidation mechanism. Unlike `bot_pat.py` which provides `clear_bot_pat_cache()`, `api/config.py` has no equivalent.

**Evidence**: Line 90-97: `@lru_cache` without `maxsize` on `get_settings() -> ApiSettings()`. No `cache_clear()` call exists for this function anywhere in the codebase.

**False-positive check**: Environment-derived configuration in a containerized deployment (ECS) is immutable for the process lifetime. Containers are replaced on configuration changes, not reconfigured in-place. This is standard practice and likely intentional. The Bot PAT's `cache_clear()` exists primarily for testing, not runtime use.

**Impact**: Negligible in production (containers restart on config changes). The only concern is test isolation, but `ApiSettings` is not registered with `SystemContext.reset_all()`, which could cause test pollution if tests modify environment variables.

---

### AP-6: `clear_all_tasks()` Blast Radius Wider Than Name Implies

**Severity**: INFORMATIONAL
**Confidence**: HIGH
**Affected Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/redis.py` (lines 751, 93)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/redis.py` (line 250)

**Description**: `RedisCacheProvider.clear_all_tasks()` uses the SCAN pattern `asana:tasks:*`. Per `_make_key()` at line 250, ALL entry types EXCEPT `EntryType.DATAFRAME` (which uses `asana:struc:*` prefix) are stored under `asana:tasks:{key}:{entry_type}`. This means `clear_all_tasks()` clears TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DETECTION, PROJECT, SECTION, USER, CUSTOM_FIELD, PROJECT_SECTIONS, GID_ENUMERATION, INSIGHTS, and DERIVED_TIMELINE entries -- not just "tasks."

**Evidence**: `_make_key()` at line 247-250: only DATAFRAME entries go to `STRUC_PREFIX`; all others go to `TASK_PREFIX`. The SCAN pattern `asana:tasks:*` at line 751 matches everything under this prefix.

**False-positive check**: The naming is a historical artifact. The intent is "clear all entity cache entries," which is exactly what it does. The name `clear_all_tasks` is misleading but the behavior is correct for its intended purpose (Lambda cache invalidation).

**Impact**: No operational impact (behavior is correct). Cognitive risk only -- a developer reading `clear_all_tasks()` might assume it clears only task data, not story/timeline/detection data. After a Lambda `clear_tasks` invalidation, ALL incrementally-fetched story cache entries are destroyed, forcing full re-fetches on next access (loss of `since` cursor optimization per ADR-0020).

---

## 2. Boundary Assessment

### 2.1 System A / System B Boundary

**Assessment**: WELL-DEFINED
**Confidence**: HIGH

The dependency map identifies two independent tier systems:
- **System A** (Entity Cache): TieredCacheProvider -> Redis + S3, serving CacheEntry objects (tasks, stories, detections, timelines)
- **System B** (DataFrame Cache): DataFrameCache -> MemoryTier + ProgressiveTier, serving DataFrameCacheEntry objects (polars DataFrames)

These systems share S3 as a persistence backend but use different key namespaces (`asana:tasks/` vs `dataframes/`), different data models (`CacheEntry` vs `DataFrameCacheEntry`), and different freshness mechanisms (version-based vs TTL+watermark). This separation aligns with ADR-0067 (intentional cache divergence across 12/14 dimensions).

**Coherence concern**: The two systems are bridged only at the application layer (resolution strategies consume both). There is no cross-system invalidation signal: when entity data in System A changes, System B's DataFrames built FROM that entity data do not receive an invalidation signal. System B relies entirely on its own TTL/SWR cycle to detect staleness.

**Domain alignment**: The boundary aligns with the data model boundary: System A caches individual Asana API entities (task-level granularity), while System B caches aggregated business views (project-level granularity). This is a natural domain split -- they serve different read patterns (point lookup vs. analytical query).

### 2.2 Cache Integration Layer Boundary

**Assessment**: WELL-DEFINED WITH ABSTRACTION LEAKS
**Confidence**: HIGH

The `cache/integration/` directory contains 8 modules that bridge between raw cache providers and application semantics: stories.py, derived.py, dataframes.py, dataframe_cache.py, batch.py, factory.py, mutation_invalidator.py, freshness_coordinator.py, staleness_coordinator.py.

These modules correctly encapsulate domain-specific cache behavior (e.g., incremental story merging, SWR lifecycle, mutation-triggered invalidation). However, two abstraction leaks are observable:

1. **Invalidation path duplication**: Both `CacheInvalidator` (in `persistence/`) and `MutationInvalidator` (in `cache/integration/`) independently call `invalidate_task_dataframes()` from `cache/integration/dataframes.py`. The invalidation logic is split across two bounded contexts (persistence UoW and cache integration) with no shared contract defining "what must be invalidated after a mutation."

2. **DataFrameCache singleton access**: `factory.py` exposes `_dataframe_cache` as a module-level singleton with `get_dataframe_cache()`, `set_dataframe_cache()`, and `reset_dataframe_cache()`. Multiple callers access the singleton directly (Lambda warmer, preload, MutationInvalidator, `@dataframe_cache` decorator). This is a gravity well -- any change to DataFrameCache initialization affects all consumers implicitly.

### 2.3 Legacy Preload Boundary (ADR-011)

**Assessment**: COHERENT WITH PRIMARY PATH
**Confidence**: HIGH

The legacy preload at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/legacy.py` loads watermarks from S3, loads DataFrames from S3 parquets, performs incremental catch-up via `ProgressiveProjectBuilder`, and populates the DataFrameCache singleton's MemoryTier. This is the same target cache and the same S3 source as the primary `DataFrameCache.get_async() -> ProgressiveTier` path.

The preload's cache behavior is coherent with the primary path because:
- Both paths populate the same MemoryTier instance (same singleton)
- Both paths read from the same S3 location (`dataframes/{project_gid}/`)
- Both paths apply the same schema version checks
- Watermarks are loaded into the same WatermarkRepository singleton

No divergence detected between fallback and primary path cache behavior.

### 2.4 Offline Query Boundary

**Assessment**: CLEANLY ISOLATED
**Confidence**: HIGH

`OfflineDataFrameProvider` at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/offline_provider.py` is fully isolated from the tiered cache system. It reads S3 parquets directly (bypassing Redis, MemoryTier, SWR, circuit breaker), uses an in-process dict with no TTL, and is scoped to CLI usage only. This is a clean, intentional boundary -- the CLI context does not need distributed cache behavior.

---

## 3. Single Points of Failure Register

### SPOF-1: DataFrameCache Module-Level Singleton

**Severity**: MEDIUM
**Confidence**: HIGH
**Cascade Path**: `factory.py:_dataframe_cache` -> every API request that uses `@dataframe_cache` decorator -> every resolution strategy -> all entity query endpoints

**Description**: The DataFrameCache is a module-level singleton (`_dataframe_cache` in `factory.py`). If `initialize_dataframe_cache()` fails (e.g., S3 bucket not configured), `get_dataframe_cache()` returns None, and every `@dataframe_cache`-decorated resolution strategy falls back to building DataFrames on every request from the Asana API. This is a degraded but functional mode.

**Failure modes**:
- S3 misconfiguration -> singleton is never created -> every request builds from API (severe latency impact but not a total outage)
- Singleton reset via `SystemContext.reset_all()` during runtime (should only happen in tests, but registered)
- Python import ordering issues could theoretically affect singleton registration

**Mitigation present**: The `@dataframe_cache` decorator handles `cache_provider=None` gracefully (builds without caching). The system is designed to function without caching, just with worse performance.

### SPOF-2: Redis (ElastiCache) for Entity Cache Hot Tier

**Severity**: MEDIUM
**Confidence**: HIGH
**Cascade Path**: Redis down -> TieredCacheProvider hot tier fails -> S3 fallback (cold tier) for entity data -> 50-200ms latency increase per entity lookup -> API response time degradation

**Description**: Redis is the hot tier for all entity cache operations (System A). `TieredCacheProvider` health is defined as hot tier health only (line 439-448 of `tiered.py`). If Redis goes down:
- `RedisCacheProvider` enters degraded mode (reconnect attempts every 30s)
- Reads fall through to S3CacheProvider (cold tier) with promotion disabled
- Simple key operations (`get`/`set`) have NO cold tier fallback (hot tier only)
- All `check_freshness()` operations return stale (hot tier only)

**Mitigation present**: Degraded mode with reconnect attempts. S3 fallback for versioned operations. Circuit breaker for per-project build failures. However, **simple key operations and freshness checks have no cold tier fallback**, which affects Insights cache and staleness detection.

### SPOF-3: SWR Build Callback Dependency Width

**Severity**: LOW
**Confidence**: HIGH
**Cascade Path**: Any component in {AsanaClient, ProgressiveProjectBuilder, SectionPersistence, SchemaRegistry, CustomFieldResolver, BotPAT} fails -> SWR background refresh fails -> circuit breaker records failure -> after 3 failures, circuit opens -> LKG serves indefinitely

**Description**: The SWR build callback at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/factory.py` lines 40-97 depends on 8+ components. Any failure in this chain causes the SWR refresh to fail silently (caught by the broad except at `dataframe_cache.py:928`). Three consecutive SWR failures open the per-project circuit breaker.

**Mitigation present**: Circuit breaker (3 failures / 60s reset). LKG fallback. Error logging. The chain is wrapped in broad exception handling so SWR failures never affect the serving path. However, if the root cause is persistent (e.g., Asana API rate limit), the circuit stays open and LKG serves indefinitely (see AP-3 regarding unlimited LKG).

### SPOF-4: SchemaRegistry Version Mismatch (Deployment-Time)

**Severity**: LOW
**Confidence**: MEDIUM
**Cascade Path**: Schema version change during deploy -> all MemoryTier entries fail schema check -> mass SCHEMA_INVALID -> all entries evicted from memory -> cold start flood to S3 -> cache stampede

**Description**: When a code deploy introduces a new schema version, the SchemaRegistry returns the new version while all cached entries still carry the old version. `_check_freshness()` returns `SCHEMA_INVALID`, `_check_freshness_and_serve()` removes entries from MemoryTier. If many requests arrive during this window, all hit S3 simultaneously.

**Mitigation present**: The ProgressiveTier (S3) contains entries that may also have the old schema version, so they too would be rejected, triggering full builds. The coalescer prevents concurrent builds for the same key. The `max_concurrent_builds=4` semaphore limits total concurrent builds. These mitigations are sufficient for the typical entity count. This is more of a cold-start-like event than a true SPOF.

---

## 4. Risk Register

| ID | Risk | Severity | Likelihood | Leverage | Classification | Evidence |
|----|------|----------|------------|----------|---------------|----------|
| R-1 | SaveSession structural mutations serve stale DataFrames for up to 3x entity TTL | HIGH | MEDIUM | **HIGH** (high impact, low effort to fix) | Quick Win | AP-1: `CacheInvalidator` at `persistence/cache_invalidator.py` never calls `DataFrameCache.invalidate_project()` |
| R-2 | Section-timelines API returns data up to 300s stale after task section changes | MEDIUM | HIGH | MEDIUM (medium impact, low effort) | Quick Win | AP-2: `derived.py` line 32, `_DERIVED_TIMELINE_TTL = 300`, no upstream invalidation |
| R-3 | Unlimited LKG staleness during extended outage serves arbitrarily old data | MEDIUM | LOW | LOW (low likelihood, medium effort to calibrate) | Strategic Investment | AP-3: `config.py:102`, `LKG_MAX_STALENESS_MULTIPLIER: float = 0.0` |
| R-4 | Cross-entity coherence gap: Offer change does not invalidate related BusinessEntity/Contact DataFrames | MEDIUM | MEDIUM | LOW (requires cross-entity invalidation design) | Long-Term Transformation | Dependency map section 2.1: "Freshness propagation is NOT automatic." Each entity type's DataFrame is cached independently by `{entity_type}:{project_gid}`. No cross-entity invalidation exists. |
| R-5 | `clear_all_tasks()` destroys incremental story fetch cursors, forcing full re-fetch | LOW | LOW (Lambda invalidation is rare, operational action) | LOW | Accepted Trade-Off | AP-6: SCAN pattern `asana:tasks:*` matches STORIES entries. Post-invalidation, `load_stories_incremental()` performs full fetches instead of incremental. |
| R-6 | Dual coalescing systems create cognitive maintenance burden | LOW | LOW | LOW (works correctly, complexity is documentation-addressable) | Accepted Trade-Off | AP-4: `DataFrameCacheCoalescer` + `BuildCoordinator` both active. Per ADR-BC-002, migration is incremental. |
| R-7 | SWR callback wide dependency surface amplifies failure blast radius | LOW | LOW | LOW (mitigated by circuit breaker + LKG) | Accepted Trade-Off | SPOF-3: 8+ component dependency chain, any failure -> circuit breaker -> LKG |
| R-8 | Schema version change during deploy causes temporary cache stampede to S3 | LOW | MEDIUM | LOW (coalescer + semaphore mitigate) | Accepted Trade-Off | SPOF-4: All MemoryTier entries fail schema check simultaneously on deploy |
| R-9 | Redis failure degrades simple-key operations (Insights cache) with no fallback | LOW | LOW | LOW (Insights cache TTL-only, graceful degradation logs) | Accepted Trade-Off | SPOF-2: `TieredCacheProvider` simple `get()`/`set()` hot tier only (lines 130-157). `_cache.py` `get_stale_response()` provides application-level fallback. |

### Leverage Scoring Methodology

- **Impact**: How many users/requests are affected if the risk materializes
- **Effort**: Engineering effort to address (hours to days = low; days to weeks = medium; weeks to months = high)
- **Leverage** = Impact / Effort

### Quick Wins (R-1, R-2)

**R-1**: Adding `DataFrameCache.invalidate_project()` calls to `CacheInvalidator._invalidate_dataframe_caches()` is a localized code change. The pattern already exists in `MutationInvalidator` and can be directly replicated.

**R-2**: Adding `MutationInvalidator` awareness of `EntryType.DERIVED_TIMELINE` (invalidate on section mutations) is a small addition to the existing invalidation path.

### Strategic Investments (R-3)

**R-3**: Setting a non-zero `LKG_MAX_STALENESS_MULTIPLIER` requires choosing a value that balances availability against data accuracy. This needs operational data (how often SWR fails, how long outages last) to calibrate properly.

### Long-Term Transformations (R-4)

**R-4**: Cross-entity coherence requires a domain-level understanding of entity relationships (Offer -> BusinessEntity, Offer -> Contact). The current architecture caches each entity type independently per project. Adding cross-entity invalidation signals would require new dependency metadata (which entity types are derived from which) and additional invalidation paths. This is a structural change, not a quick fix.

---

## 5. Architectural Philosophy Extraction

### 5.1 Implicit Design Philosophy

The cache subsystem follows an **availability-first, eventually-consistent** philosophy. Evidence:

1. **LKG (Last-Known-Good) over errors**: `LKG_MAX_STALENESS_MULTIPLIER = 0.0` means "serve stale data forever rather than return an error." The system will never fail to serve data if any cache tier has a schema-valid entry.

2. **SWR (Stale-While-Revalidate) as primary freshness mechanism**: Rather than synchronous cache-aside invalidation, the system serves potentially stale data immediately and refreshes asynchronously in the background. Response latency is never blocked by cache refresh.

3. **Fire-and-forget invalidation**: `MutationInvalidator.fire_and_forget()` uses `asyncio.create_task` with `_log_task_exception` callback. Invalidation failures never block mutation responses.

4. **Circuit breaker with LKG fallback**: When builds fail repeatedly, the system switches to serving last-known-good data rather than attempting builds that will likely fail. This is an explicit availability choice over correctness.

5. **Graceful degradation at every layer**: Redis degraded mode, S3 failures logged but not propagated, cache misses trigger builds rather than errors, broad exception handling at background task boundaries.

### 5.2 Where Practice Diverges from Philosophy

The availability-first philosophy is consistently applied, but two areas show tension:

1. **Schema version changes cause hard rejects** (`SCHEMA_INVALID`): This is the ONE place where the system chooses correctness over availability. A schema mismatch causes the entry to be evicted with no LKG fallback for that specific entry. This is architecturally appropriate -- serving data with the wrong schema could cause downstream processing errors worse than a cache miss.

2. **Watermark check causes hard rejects** (`WATERMARK_BEHIND`): When a newer watermark is known, older entries are rejected rather than served. This is also correctness-over-availability but only triggered when a fresher data source is known to exist, which is a reasonable gate.

These two hard-reject paths are the necessary exceptions that prevent the availability-first philosophy from becoming "serve garbage forever."

### 5.3 Module-to-Domain Alignment

| Domain Concern | Module(s) | Alignment Score |
|---|---|---|
| Entity data caching (tasks, stories) | `cache/backends/`, `cache/providers/` | 5/5 -- clean tiered provider pattern |
| DataFrame caching (business views) | `cache/dataframe/`, `cache/integration/dataframe_cache.py` | 4/5 -- well-structured but singleton management leaks |
| Freshness detection | `cache/policies/staleness.py`, `cache/integration/freshness_coordinator.py`, `cache/integration/staleness_coordinator.py` | 3/5 -- two parallel freshness systems (FreshnessCoordinator + StalenessCheckCoordinator) for the same concern |
| Cache invalidation | `cache/integration/mutation_invalidator.py`, `persistence/cache_invalidator.py` | 3/5 -- split across bounded contexts with asymmetric behavior (AP-1) |
| Build coordination | `cache/dataframe/coalescer.py`, `cache/dataframe/build_coordinator.py` | 3/5 -- dual systems in incremental migration (AP-4) |
| Cache warming | `cache/dataframe/warmer.py`, `lambda_handlers/cache_warmer.py` | 4/5 -- clear separation of concern (domain warming vs. Lambda orchestration) |
| Cache configuration | `config.py`, `cache/models/settings.py` | 4/5 -- centralized TTL configuration, entity-aware |

**Overall module-to-domain alignment**: 3.7/5. The cache subsystem has strong domain alignment in its core tiered provider patterns but shows fragmentation in freshness detection, invalidation, and build coordination -- areas where historical evolution has produced parallel systems that serve overlapping purposes.

### 5.4 Complexity Assessment: 26 Cache Locations

The topology inventory identifies 26 cache locations. These decompose as:

| Category | Count | Purpose | Redundancy Assessment |
|---|---|---|---|
| Formal tiered system (System A) | 7 | Entity data caching | Intentional composition (tiered provider + backends + wrappers) |
| Formal tiered system (System B) | 5 | DataFrame caching | Intentional composition (DataFrameCache + tiers + factory) |
| Cache-adjacent patterns | 7 | Coordination (coalescer, circuit breaker, warmer, preload, SWR, decorator) | Supporting infrastructure, not redundant |
| In-process `lru_cache` | 4 | Pure value/transform caching | Lightweight, appropriate |
| Lambda operations | 2 | Warming + invalidation | Infrastructure, not application caching |
| Offline/client caching | 1 | CLI query mode | Isolated, appropriate |

**Assessment**: The 26 locations are NOT over-engineered. They decompose into two coherent tier systems (7+5 = 12), seven coordination patterns that support those tier systems, four lightweight process-scoped caches, and three infrastructure concerns. Each serves a distinct purpose.

The complexity concern is not the count but the **interplay between systems**: two tier systems with different freshness models, two invalidation paths with different scopes, two coalescing systems in migration, and two freshness checking systems for entity cache. The individual components are well-designed; the systemic complexity arises from their interaction.

**Tiers that could potentially be collapsed**: None without losing capability. The two tier systems (Entity vs DataFrame) serve fundamentally different data types (JSON entities vs polars DataFrames) with different access patterns (point lookup vs. analytical scan). The topology inventory and ADR-0067 document this divergence as intentional across 12/14 dimensions.

---

## 6. Unknowns

### Unknown: SaveSession DataFrameCache Invalidation -- Intentional or Gap?

- **Question**: Was the omission of `DataFrameCache.invalidate_project()` from `CacheInvalidator` (SaveSession path) an intentional design decision or an oversight that was never backported after MutationInvalidator added this capability?
- **Why it matters**: If intentional, it suggests the automation pipeline path deliberately accepts eventual consistency for DataFrames (TTL-based refresh only). If a gap, it is a concrete staleness bug affecting batch operations.
- **Evidence**: `CacheInvalidator` was extracted per ADR-0059 before MutationInvalidator gained DataFrameCache awareness. No ADR or TDD document discusses this asymmetry as a design choice. The dependency map (section 3.2) flagged it as an unresolved unknown.
- **Suggested source**: Original author of ADR-0059 or the MutationInvalidator implementation.

### Unknown: Derived Timeline Cache Staleness Acceptability

- **Question**: Is the 300s staleness window for derived timeline data acceptable to the business consumers of the section-timelines API? Or is near-real-time timeline freshness expected?
- **Why it matters**: Determines whether AP-2 is a real risk or an accepted trade-off. If consumers expect real-time data, 300s staleness is a problem. If consumers use timelines for daily/weekly reporting, 300s is negligible.
- **Evidence**: The 300s TTL is documented with a rationale ("freshness vs. computation cost") but no consumer SLA or business requirement is referenced.
- **Suggested source**: Product owner or the team consuming section-timelines API data.

### Unknown: Circuit Breaker State After Container Restart

- **Question**: Is it beneficial or harmful that circuit breaker state resets to CLOSED on container restart? A restart could either heal a transient issue (beneficial) or re-trigger the same failure pattern (harmful).
- **Why it matters**: Affects whether ECS container restarts are a reliable recovery mechanism for persistent build failures, or whether they cause repeated failure storms.
- **Evidence**: `CircuitBreaker` at `cache/dataframe/circuit_breaker.py` uses in-process `ProjectCircuit` state machines with no persistence. Container restart clears all state.
- **Suggested source**: Operational runbooks or incident post-mortems for cache build failures.

### Unknown: Cross-Entity DataFrame Invalidation Requirements

- **Question**: When an Offer's data changes, do the related BusinessEntity or Contact DataFrames need to be refreshed? What are the actual data dependencies between entity type DataFrames?
- **Why it matters**: R-4 assumes cross-entity coherence is needed, but the actual data dependencies are not documented. If each entity type's DataFrame is truly independent (no derived columns from other entity types), cross-entity invalidation is unnecessary.
- **Evidence**: Each entity type is cached independently by `{entity_type}:{project_gid}`. The dependency map notes "Freshness propagation is NOT automatic" between entity types but does not establish whether cross-entity data dependencies exist at the schema level.
- **Suggested source**: Entity schema definitions in `dataframes/models/registry.py` and resolution strategy implementations.

---

## Handoff Readiness Checklist

- [x] Architecture-assessment artifact exists with all required sections (anti-pattern findings, boundary assessments, SPOF register, risk register)
- [x] Each anti-pattern finding includes evidence (file paths, code references) and affected repos
- [x] Risk register entries have leverage scores and impact/effort classifications (quick win, strategic investment, long-term transformation)
- [x] Confidence ratings (high/medium/low) assigned to all findings
- [x] False-positive context check performed for all anti-pattern findings
- [x] SPOF register identifies cascade paths
- [x] Boundary assessments reference both topology-inventory service classifications and dependency-map coupling data
- [x] Unknowns section documents structural decisions requiring human context
- [x] (DEEP-DIVE) Architectural philosophy extraction and module-to-domain alignment scoring complete
