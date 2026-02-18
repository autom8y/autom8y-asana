# ADR-010: Cache System Divergence Assessment

**Status**: Proposed
**Date**: 2026-02-18
**Deciders**: Architecture review (SI-5 from ARCH-REVIEW-1)

## Context

The autom8y-asana codebase contains two parallel cache systems under the `cache/` package (15,658 LOC):

1. **Entity cache**: Caches individual Asana API responses (tasks, subtasks, dependencies) using a `CacheProvider` protocol backed by Redis (hot tier) and S3 JSON (cold tier). Implemented in `cache/providers/tiered.py`, consumed via `cache/providers/unified.py` (the `UnifiedTaskStore`).

2. **DataFrame cache**: Caches Polars DataFrames built from project-level entity aggregations. Uses an in-process `OrderedDict` (hot tier) and S3 Parquet via `ProgressiveTier` (cold tier). Implemented in `cache/integration/dataframe_cache.py`.

The Q1 2026 architecture review (ARCH-REVIEW-1) identified "31 cache concepts" as the primary cognitive load driver in the codebase -- 14 entry types, 7 freshness-related types, 6 freshness states, 5 providers, 4 tiers, 4 completeness levels. The review flagged Unknown U-002: whether the divergence between the two systems is intentional, convergeable, or accidental. This ADR resolves that unknown.

### Why two systems exist

The entity cache predates the DataFrame cache. It was designed for the SDK's core use case: looking up individual Asana entities by GID and checking their freshness against the Asana API's `modified_at` field. The `CacheProvider` protocol (`protocols/cache.py`) defines a synchronous interface returning `dict[str, Any]` payloads.

The DataFrame cache was introduced later for the analytics/query path. Instead of caching individual entities, it builds Polars DataFrames containing all entities of a given type within a project and caches those materialized views. This required fundamentally different storage (columnar Parquet), different eviction (heap-aware LRU), and different coordination (build coalescing to prevent thundering herd on cache miss).

The `MutationInvalidator` (`cache/integration/mutation_invalidator.py`) bridges the two systems: a single mutation event triggers invalidation in both the entity cache (per-entity key eviction) and the DataFrame cache (per-project invalidation).

## Dimension Analysis

The following table evaluates 14 dimensions where the two cache systems diverge. Each dimension is classified as:

- **Intentional**: The divergence reflects genuinely different requirements.
- **Convergeable**: The divergence adds cognitive load without technical justification and could be unified.
- **Accidental**: The divergence arose from independent development with no design rationale.

| # | Dimension | Entity Cache | DataFrame Cache | Verdict | Rationale |
|---|-----------|-------------|----------------|---------|-----------|
| 1 | Cache unit | `dict[str, Any]` (single entity JSON) | `pl.DataFrame` (columnar table, N rows) | **Intentional** | The entity cache serves point lookups ("get task X"). The DataFrame cache serves analytical queries ("get all units in project Y"). These are fundamentally different data shapes -- a dict cannot hold a DataFrame, and wrapping every DataFrame cell in a dict would destroy Polars' zero-copy performance. |
| 2 | Key space | Per-entity GID (e.g., `task:1234567890`) | Per-project + entity type (e.g., `unit:project-123`) | **Intentional** | Entity cache keys are scoped to individual resources because the Asana API returns one resource per GID lookup. DataFrame cache keys are scoped to project + type because each DataFrame materializes all entities of one type within one project. The key space follows from the data shape. |
| 3 | Interface contract | `CacheProvider` protocol (`protocols/cache.py`) -- structural typing via `Protocol` | `DataFrameCache` concrete dataclass (`cache/integration/dataframe_cache.py`) -- no protocol abstraction | **Convergeable** | The entity cache uses a Protocol, enabling NullCacheProvider (no-op), InMemoryCacheProvider (testing), and TieredCacheProvider (production) to be swapped without changing call sites. The DataFrame cache has no protocol; the concrete `DataFrameCache` class is used directly, and tests must mock the concrete class. Introducing a `DataFrameCacheProtocol` would improve testability and follow the same pattern as the entity cache, with minimal effort. |
| 4 | Hot tier | Redis (ElastiCache, external service) | In-process `OrderedDict` with `threading.RLock` (`cache/dataframe/tiers/memory.py`) | **Intentional** | Entity cache entries are small JSON dicts (typically 1-10 KB) accessed across multiple ECS tasks and Lambda invocations -- Redis provides shared, persistent hot storage. DataFrame cache entries are large Polars DataFrames (potentially tens of MB) that are expensive to serialize/deserialize over the network. In-process memory avoids serialization overhead and provides sub-millisecond access for the analytics path. Different data sizes and access patterns justify different hot tier implementations. |
| 5 | Cold tier | S3 JSON (via `S3CacheProvider` in `cache/backends/s3.py`) | S3 Parquet (via `ProgressiveTier` using `SectionPersistence`) | **Intentional** | JSON is the natural serialization for entity dicts (preserves schema, human-readable, matches API response format). Parquet is the natural serialization for columnar DataFrames (preserves types, enables predicate pushdown, 5-10x smaller than JSON for tabular data). Using JSON for DataFrames or Parquet for entity dicts would be actively harmful. |
| 6 | Eviction | TTL-based expiration (entry carries `ttl` field, checked on read via `is_expired()`) | LRU by heap size (evicts least-recently-used entry when `current_bytes + new_entry_size > max_bytes`) | **Intentional** | Entity cache entries are small and numerous (thousands of tasks). TTL expiration naturally fits: each entry has a predictable lifetime, and Redis handles TTL natively. DataFrame cache entries are large and few (one per project + entity type). Memory pressure, not time, is the binding constraint -- a single large DataFrame can consume hundreds of MB. LRU by heap size prevents OOM while keeping the most-accessed DataFrames warm. The MemoryTier also supports time-based eviction via `evict_stale()`, but LRU by size is the primary mechanism. |
| 7 | Freshness model | 3-mode: `STRICT` (always validate via API), `EVENTUAL` (TTL-based), `IMMEDIATE` (return cached, no validation) -- defined in `cache/models/freshness.py` and `FreshnessMode` enum in `freshness_coordinator.py` | 6-state: `FRESH`, `STALE_SERVABLE` (within SWR grace), `EXPIRED_SERVABLE` (beyond grace, schema valid), `SCHEMA_MISMATCH` (hard reject), `WATERMARK_STALE` (hard reject), `CIRCUIT_LKG` (circuit breaker open, serving last known good) -- defined in `FreshnessStatus` enum in `dataframe_cache.py` | **Accidental** | The entity cache's 3-mode model describes *caller intent* (how strict should validation be?). The DataFrame cache's 6-state model describes *entry health* (what is the current freshness of this entry?). These are orthogonal concepts that answer different questions. The entity cache could benefit from health states (it currently has no way to express "stale but servable" or "schema mismatch"). The DataFrame cache could benefit from caller-intent modes (it currently always runs full freshness evaluation). The two models should have been designed as complementary layers (caller intent x entry health), not as alternatives. The current state forces developers to learn two unrelated freshness vocabularies. |
| 8 | Staleness detection | Asana Batch API call (`FreshnessCoordinator.check_batch_async()` fetches `modified_at` via Batch API, compares against cached `version` field) | Watermark comparison (`entry.watermark >= current_watermark` where watermark = `max(modified_at)` across all rows in the DataFrame) | **Intentional** | Entity staleness requires calling the Asana API because a single entity's `modified_at` can only be known by asking Asana. DataFrame staleness can be checked locally: if the caller already knows the current watermark (from a recent API call or webhook), it compares against the cached watermark without an API roundtrip. The entity cache's batch API approach consumes rate limit budget; the DataFrame cache's watermark approach is zero-cost when the watermark is available. Different detection mechanisms match the different access patterns. |
| 9 | Invalidation granularity | Per-entity GID: `cache.invalidate(gid, [EntryType.TASK])` removes one entity's cache entries | Per-project: `dataframe_cache.invalidate_project(project_gid)` removes all entity types for an entire project | **Convergeable** | The granularity difference is partially intentional (a task update affects one entity but may affect an entire project's DataFrame) but the gap is wider than necessary. The DataFrame cache has no mechanism to invalidate a single row within a DataFrame -- it evicts the entire project. For task field updates that change one row in one entity type, this is overly aggressive. A row-level invalidation (mark one row stale within the DataFrame) would reduce unnecessary rebuilds. The entity cache, conversely, has no concept of "invalidate everything for project X" -- the `MutationInvalidator` must enumerate affected entity types. Both systems would benefit from supporting both granularity levels. |
| 10 | Schema versioning | None. Entity cache entries carry no schema version. If the SDK's field expectations change, cached entries silently serve stale shapes until TTL expires. | `SchemaRegistry` integration. DataFrame cache entries carry a `schema_version` field checked via `_get_schema_version_for_entity()`. Schema mismatch is a hard reject (`FreshnessStatus.SCHEMA_MISMATCH`). | **Accidental** | The DataFrame cache's schema versioning is clearly superior. It prevents serving structurally invalid data after a schema change. The entity cache has no equivalent protection -- a schema change in the SDK could cause the entity cache to serve entries with missing or renamed fields until TTL expires. The `CacheEntry` class (`cache/models/entry.py`) has no `schema_version` field, though `DataFrameMetaCacheEntry` has one for its Redis/S3 tier. Schema versioning should be retrofitted to the entity cache. |
| 11 | Build coordination | None. The entity cache has no build coordination. Concurrent requests for the same missing entity each independently fetch from the Asana API. | `CircuitBreaker` + `DataFrameCacheCoalescer`. First request acquires a build lock and builds; concurrent requests wait via `asyncio.Event`. Circuit breaker opens after repeated failures, serving last-known-good data. | **Intentional** | Entity cache misses trigger individual API calls that are cheap (one GET request per entity, ~100ms). DataFrame cache misses trigger expensive build operations (fetching all tasks in a project, transforming to Polars, persisting to S3, potentially minutes). The thundering herd problem is severe for DataFrame builds but negligible for entity lookups. Build coordination is justified for expensive operations and unnecessary overhead for cheap ones. |
| 12 | Completeness tracking | `CompletenessLevel` enum (UNKNOWN, MINIMAL, STANDARD, FULL) in `cache/models/completeness.py`. Entity cache entries carry completeness metadata so consumers can request upgrades when cached data has insufficient field coverage. | Absent. DataFrame cache has no completeness concept. DataFrames are always built with the full schema for their entity type. | **Intentional** | Entity cache entries vary in field coverage because different callers fetch different `opt_fields` (e.g., `ParallelSectionFetcher` fetches GID-only, while `DataFrameViewPlugin` needs custom_fields). Completeness tracking prevents silent failures when a minimal entry is used where a full entry is needed. DataFrame builds always extract the full schema defined in `SchemaRegistry`, so there is no partial-build scenario. Completeness tracking would add complexity with no benefit. |
| 13 | Async model | Synchronous protocol. `CacheProvider` methods (`get`, `set`, `delete`, `get_versioned`, `set_versioned`) are all sync. `UnifiedTaskStore` wraps them in async methods but the protocol itself is sync. | Fully async. `DataFrameCache.get_async()`, `put_async()`, `acquire_build_lock_async()` are all async. The `MemoryTier.get()` is sync (in-process), but the `ProgressiveTier.get_async()` is async (S3 I/O). | **Accidental** | The entity cache protocol was designed when the codebase had a sync-first architecture. The `CacheProvider` protocol uses sync methods even though the backing Redis and S3 calls are inherently async. The 88 sync bridges documented in ARCH-REVIEW-1 are a consequence of this design. The DataFrame cache, designed later, correctly uses async from the start. Both systems now run in an async FastAPI application. The sync protocol forces the entity cache to block the event loop during Redis/S3 I/O (or use sync bridges), while the DataFrame cache cooperates with the event loop natively. The entity cache protocol should have been async from the start, or migrated to async when the application moved to FastAPI. |
| 14 | Singleton pattern | Factory-injected. `TieredCacheProvider` is created during `api/lifespan.py` startup and passed to `UnifiedTaskStore` via constructor injection. No module-level singleton. | Module-level singleton. `_dataframe_cache` module variable in `dataframe_cache.py`, accessed via `get_dataframe_cache()` / `set_dataframe_cache()`. | **Convergeable** | The entity cache uses dependency injection, making it testable and explicit about its lifecycle. The DataFrame cache uses a module-level singleton with getter/setter functions, which makes testing harder (requires `reset_dataframe_cache()` in fixtures) and hides the dependency in global state. The singleton pattern was likely chosen for convenience during the DataFrame cache's initial development. Moving to constructor injection (matching the entity cache pattern) would improve testability and reduce the global mutable state that ARCH-REVIEW-1 flagged as a test isolation concern (R-017). |

## Summary Statistics

| Classification | Count | Dimensions |
|---------------|-------|------------|
| **Intentional** | 8 | #1 (cache unit), #2 (key space), #4 (hot tier), #5 (cold tier), #6 (eviction), #8 (staleness detection), #11 (build coordination), #12 (completeness tracking) |
| **Convergeable** | 3 | #3 (interface contract), #9 (invalidation granularity), #14 (singleton pattern) |
| **Accidental** | 3 | #7 (freshness model), #10 (schema versioning), #13 (async model) |

**Note on dimension #6 (eviction)**: Classified as Intentional because the primary eviction mechanisms (TTL vs. LRU-by-heap) are justified by the different data sizes. The MemoryTier already supports `evict_stale()` for time-based eviction in addition to LRU, showing that the two mechanisms are not mutually exclusive. The entity cache could benefit from memory-pressure awareness, but this is an enhancement opportunity, not a divergence defect.

**Overall assessment**: The divergence is **predominantly intentional** at the data-layer level (what is cached, where it is stored, how it is evicted) and **predominantly accidental** at the abstraction-layer level (how freshness is modeled, how the interface is typed, how instances are managed). The two systems solve genuinely different problems with appropriately different implementations, but the programming model around them diverged unnecessarily.

## Decision

**Partially converge.** Accept the data-layer divergence as load-bearing architecture. Converge the abstraction-layer divergence to reduce cognitive overhead.

### Accept as intentional (no change)

These dimensions reflect genuine architectural requirements. Attempting to unify them would produce a worse system.

| # | Dimension | Why it stays |
|---|-----------|-------------|
| 1 | Cache unit (dict vs. DataFrame) | Different data shapes serve different query patterns |
| 2 | Key space (per-entity vs. per-project) | Follows from the data shape |
| 4 | Hot tier (Redis vs. in-process) | Network serialization cost prohibitive for DataFrames |
| 5 | Cold tier (JSON vs. Parquet) | Format matches data shape |
| 8 | Staleness detection (Batch API vs. watermark) | Different cost profiles for different access patterns |
| 11 | Build coordination (none vs. coalescer) | Only justified for expensive operations |
| 12 | Completeness tracking (present vs. absent) | Only meaningful when partial entries exist |

### Converge (recommended actions)

These changes reduce the "31 cache concepts" cognitive load without disrupting the load-bearing architecture.

**C1: Introduce a `DataFrameCacheProtocol`** (dimension #3)
- Extract a Protocol from `DataFrameCache` matching the public API (`get_async`, `put_async`, `invalidate`, `invalidate_project`).
- Tests and consumers depend on the Protocol, not the concrete class.
- Effort: 1-2 days. Low risk.

**C2: Unify freshness vocabulary** (dimension #7)
- The entity cache's 3-mode model (caller intent) and the DataFrame cache's 6-state model (entry health) should coexist as two layers of a single freshness model, not as competing alternatives.
- Define a shared `FreshnessIntent` enum (STRICT, EVENTUAL, IMMEDIATE) and a shared `FreshnessHealth` enum (FRESH, STALE_SERVABLE, EXPIRED, REJECTED) that both systems use.
- The entity cache gains health states. The DataFrame cache gains intent modes.
- Effort: 3-5 days. Medium risk (touches freshness evaluation in both systems).

**C3: Add schema versioning to entity cache** (dimension #10)
- Add an optional `schema_version` field to `CacheEntry`.
- On read, compare against the expected schema version. Hard-reject on mismatch (matching the DataFrame cache behavior).
- Effort: 2-3 days. Low risk (additive change, backward compatible via optional field).

**C4: Replace DataFrame cache singleton with injection** (dimension #14)
- Pass `DataFrameCache` via constructor injection (matching entity cache pattern) instead of module-level `get_dataframe_cache()` / `set_dataframe_cache()`.
- Remove `_dataframe_cache` module global. Wire via `app.state` in lifespan.
- Effort: 1-2 days. Low risk.

**C5: Migrate entity cache protocol to async** (dimension #13)
- Define `AsyncCacheProvider` protocol with async method signatures.
- Implement async versions in `TieredCacheProvider` (Redis and S3 clients already support async).
- This is a larger effort that aligns with the broader sync-to-async migration noted in ARCH-REVIEW-1.
- Effort: 5-8 days. High risk (touches all CacheProvider consumers). Defer to a dedicated workstream.

### Estimated total effort

| Action | Effort | Risk | Priority |
|--------|--------|------|----------|
| C1: DataFrameCache protocol | 1-2 days | Low | High (quick win) |
| C4: Singleton to injection | 1-2 days | Low | High (quick win) |
| C3: Entity schema versioning | 2-3 days | Low | Medium |
| C2: Unified freshness vocabulary | 3-5 days | Medium | Medium |
| C5: Async entity cache protocol | 5-8 days | High | Low (defer) |

Total for C1-C4: **7-12 days**. This reduces the conceptual overhead from 31 concepts to approximately 24 (by unifying freshness vocabulary and eliminating duplicate patterns).

## Consequences

### If we converge (C1-C4)

- Developers working on "caching" learn one freshness vocabulary instead of two.
- The `DataFrameCache` becomes testable without mocking a concrete class.
- Entity cache entries gain schema version protection, closing a silent-stale-data gap.
- Global mutable state decreases by one singleton, improving test isolation.
- The two cache systems remain architecturally distinct where they need to be (data shape, storage, eviction) but share a common programming model where they can.

### If we do not converge

- The "31 cache concepts" cognitive load persists.
- New engineers must learn two independent mental models for caching.
- Entity cache entries remain vulnerable to schema changes until TTL expires.
- The DataFrame cache remains harder to test than necessary.
- Risk of further accidental divergence increases as each system evolves independently.

### What this ADR does not change

- The two-system architecture persists. This ADR does not propose merging entity cache and DataFrame cache into one system.
- The data-layer choices (Redis vs. in-process, JSON vs. Parquet, TTL vs. LRU) remain unchanged.
- The `MutationInvalidator` continues to bridge both systems for invalidation.

## References

- ARCH-REVIEW-1 Section 2.2 (Caching Subsystem): identified the "31 cache concepts" concern and the undocumented bifurcation
- ARCH-REVIEW-1 Unknown U-002: "Cache system key scheme divergence: intentional or evolutionary?"
- ARCH-REVIEW-1 Recommendation SI-5: "Write ADR documenting entity cache vs. DataFrame cache divergence"
- `src/autom8_asana/protocols/cache.py`: `CacheProvider` protocol (entity cache interface)
- `src/autom8_asana/cache/integration/dataframe_cache.py`: `DataFrameCache` class and `FreshnessStatus` enum
- `src/autom8_asana/cache/models/entry.py`: `CacheEntry` hierarchy and `EntryType` enum
- `src/autom8_asana/cache/providers/tiered.py`: `TieredCacheProvider` (Redis + S3 entity cache)
- `src/autom8_asana/cache/dataframe/tiers/memory.py`: `MemoryTier` (in-process DataFrame hot cache)
- `src/autom8_asana/cache/integration/mutation_invalidator.py`: `MutationInvalidator` (bridges both systems)
- `src/autom8_asana/cache/models/freshness.py`: `Freshness` enum (entity cache modes)
- `src/autom8_asana/cache/integration/freshness_coordinator.py`: `FreshnessMode` and `FreshnessCoordinator`
- `src/autom8_asana/cache/models/completeness.py`: `CompletenessLevel` enum (entity cache only)
- `src/autom8_asana/core/schema.py`: `get_schema_version()` (DataFrame cache schema validation)
