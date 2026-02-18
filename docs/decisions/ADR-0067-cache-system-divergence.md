# ADR-0067: Cache System Divergence -- 14-Dimension Classification

**Date**: 2026-02-18
**Status**: ACCEPTED
**Deciders**: Architecture Sprint (U-005/SI-5/U-001)
**Supersedes**: None
**Extends**: ADR-DATAFRAME-CACHE-DISPOSITION (2026-02-05)

---

## Context

The Q1 2026 architecture assessment (AP-008) identified 31 caching concepts across
~15,900 LOC in the cache subsystem. Two parallel cache systems exist:

- **Entity cache**: `CacheProvider` protocol, Redis+S3, synchronous, TTL-based, per-entity
- **DataFrame cache**: concrete `DataFrameCache` class, Memory+S3 Parquet, async, SWR, per-project

ADR-DATAFRAME-CACHE-DISPOSITION established that the separation is intentional based on
5 impedance mismatches. This ADR extends that analysis with a systematic 14-dimension
comparison to determine, per dimension, whether the divergence is **intentional**
(different use cases demand it), **convergeable** (could unify without losing
functionality), or **accidental** (historical drift with no design justification).

---

## 14-Dimension Comparison

| # | Dimension | Entity Cache | DataFrame Cache | Verdict |
|---|-----------|-------------|-----------------|---------|
| 1 | Cache unit | `dict[str, Any]` (raw Asana API response) | `pl.DataFrame` (Polars columnar) | **INTENTIONAL** |
| 2 | Key space | `type:gid` (per-entity) | `type:project_gid` (per-project) | **INTENTIONAL** |
| 3 | Interface contract | `CacheProvider` Protocol (structural typing) | `DataFrameCache` concrete class | **CONVERGEABLE** |
| 4 | Hot tier | Redis (shared across ECS replicas) | In-process `OrderedDict` (`MemoryTier`) | **INTENTIONAL** |
| 5 | Cold tier | S3 JSON (flat key-value) | S3 Parquet (domain key structure via `SectionPersistence`) | **INTENTIONAL** |
| 6 | Eviction | TTL expiry (Redis `EXPIRE`) | LRU by heap size (`max_heap_percent * container_memory`) | **INTENTIONAL** |
| 7 | Freshness model | 3-mode `FreshnessMode` (caller-controlled) | 6-state `FreshnessStatus` + SWR (entry-driven) | **INTENTIONAL** |
| 8 | Staleness detection | Batch API (`GET /tasks/{gid}?opt_fields=modified_at`) | Watermark comparison (`max(modified_at)` across project) | **INTENTIONAL** |
| 9 | Invalidation granularity | Per-entity GID | Per-project (all entity types) | **INTENTIONAL** |
| 10 | Schema versioning | Absent | `SchemaRegistry` version string, hard-reject on mismatch | **INTENTIONAL** |
| 11 | Build coordination | Absent | `CircuitBreaker` + `DataFrameCacheCoalescer` | **INTENTIONAL** |
| 12 | Completeness tracking | `CompletenessLevel` (MINIMAL/STANDARD/FULL) | Absent (binary valid/invalid via schema version) | **INTENTIONAL** |
| 13 | Async model | Sync protocol (async wrapper in `UnifiedTaskStore`) | Native async throughout | **INTENTIONAL** |
| 14 | Singleton pattern | Factory-injected `CacheProvider` | Module-level `_dataframe_cache` singleton | **ACCIDENTAL** |

**Tally: 11 intentional, 1 convergeable, 1 accidental.**

Dimensions 3 and 14 are two views of the same gap: the DataFrame cache lacks a protocol
interface and uses a module-level singleton instead of dependency injection. The effective
count is 12 intentional, 1 convergeable (interface + injection).

---

## Dimension-by-Dimension Evidence

### 1. Cache unit -- INTENTIONAL

Entity cache stores raw Asana API responses (one dict per resource). DataFrame cache stores
multi-row analytical tables built from many API responses. Converting between them would
lose schema type information, memory size estimation, and watermark semantics
(per ADR-DATAFRAME-CACHE-DISPOSITION).

**Evidence**: `CacheProvider.get() -> dict[str, Any]` (protocols/cache.py:41).
`DataFrameCacheEntry.dataframe: pl.DataFrame` (dataframe_cache.py:130).

### 2. Key space -- INTENTIONAL

Entity cache answers "what is task X?" (per-GID). DataFrame cache answers "what are all
units in project Y?" (per-project+type). A GID-keyed store cannot satisfy the DataFrame
use case without a full table scan; a project-keyed store cannot satisfy individual lookup
without row extraction.

**Evidence**: Protocol docstring `"Cache keys: '{resource_type}:{gid}'"` (protocols/cache.py:32).
`DataFrameCache._build_key() -> f"{entity_type}:{project_gid}"` (dataframe_cache.py:822).

### 3. Interface contract -- CONVERGEABLE

Entity cache uses a Protocol for dependency injection, enabling swappable backends.
DataFrame cache uses a concrete class with no protocol. There is no design reason it could
not define a `DataFrameCacheProtocol` for the same DI benefits (e.g., a `NullDataFrameCache`
for testing). Since there is currently only one implementation, this has not caused pain.

**Evidence**: `class CacheProvider(Protocol)` (protocols/cache.py:14).
`@dataclass class DataFrameCache` (dataframe_cache.py:169).

### 4. Hot tier -- INTENTIONAL

Entity cache uses Redis because entities are shared across ECS replicas. DataFrame cache
uses in-process memory because DataFrames are large binary objects -- Redis
serialization/deserialization would be prohibitively expensive.

**Evidence**: `MemoryTier._estimate_size(entry)` uses `entry.dataframe.estimated_size()`
(memory.py:264). Eviction is per-container heap, not per-cluster.

### 5. Cold tier -- INTENTIONAL

JSON is appropriate for small entity dicts. Parquet/columnar is appropriate for
DataFrames. The S3 key structures are necessarily different: flat `resource_type:gid` vs
hierarchical `dataframes/{project_gid}/` with manifest and watermark sidecars.

### 6. Eviction -- INTENTIONAL

Entity cache entries are small dicts -- TTL delegates memory management to Redis (`EXPIRE`).
DataFrame entries can be hundreds of MB -- TTL alone cannot prevent container OOM. The
heap-based limit (`max_heap_percent=0.3`) is the only safe eviction policy for large
binary objects.

**Evidence**: `CacheEntry.ttl: int = 300` (entry.py:101).
`MemoryTier._should_evict(new_entry_size)`: `current_bytes + new_entry_size > max_bytes`
(memory.py:226-232).

### 7. Freshness model -- INTENTIONAL

Entity cache freshness is caller-controlled (STRICT/EVENTUAL/IMMEDIATE at call time).
DataFrame cache freshness is entry-driven (6-state including SCHEMA_MISMATCH and
CIRCUIT_LKG). SWR is appropriate for DataFrames because builds are expensive (5-30s)
and the read path is latency-sensitive. Entity cache entries are cheap to re-fetch
(single API call) and used in write paths where stale data causes correctness issues.

**Evidence**: `FreshnessMode` (3 values) in freshness_coordinator.py:30-41.
`FreshnessStatus` (6 values) + `_trigger_swr_refresh()` in dataframe_cache.py:43-51.

### 8. Staleness detection -- INTENTIONAL

Entity cache checks per-GID `modified_at` via Asana Batch API (most precise).
DataFrame cache uses project-level watermark (`max(modified_at)` across all tasks)
because checking each of hundreds of tasks individually would defeat the cache's purpose.

### 9. Invalidation granularity -- INTENTIONAL

Entity entries are independent -- invalidating task A does not affect task B. A DataFrame
contains all tasks in a project -- changing any one task makes the entire DataFrame stale.
The granularity difference is driven by the atomicity of the cached unit.

**Evidence**: `MutationInvalidator._hard_invalidate_entity_entries(gid)` vs
`MutationInvalidator._invalidate_project_dataframes(project_gids)` (mutation_invalidator.py).

### 10. Schema versioning -- INTENTIONAL

Entity cache stores raw API dicts whose "schema" is the Asana API (not application-controlled).
DataFrame entries have application-defined schemas (Polars column names, dtypes, `cf:` prefix
conventions) that evolve with development. Schema versioning is the only safe mechanism
to detect and evict structurally incompatible cached DataFrames.

### 11. Build coordination -- INTENTIONAL

Entity cache entries are populated by single API calls. A DataFrame is built from N section
fetches across M pages -- potentially dozens of API calls over 5-30 seconds. Without
coalescing, N concurrent requests would trigger N parallel builds, each consuming N*M API
calls. The `CircuitBreaker` prevents hammering a temporarily unavailable project.

### 12. Completeness tracking -- INTENTIONAL

Asana entities can be fetched with different `opt_fields` -- a task fetched with `["gid"]`
is a different (partial) view from the same task fetched with full fields. The completeness
model prevents serving minimal views when full views are needed. DataFrames have a fixed
schema per entity type -- there is no partial DataFrame concept.

**Evidence**: `CompletenessLevel` enum (UNKNOWN=0, MINIMAL=10, STANDARD=20, FULL=30) in
completeness.py:110. No equivalent in DataFrameCache.

### 13. Async model -- INTENTIONAL

Redis I/O is fast enough to be synchronous; the sync protocol supports both sync and async
callers. S3 I/O for multi-MB Parquet files benefits from async execution. ADR-DATAFRAME-
CACHE-DISPOSITION explicitly rejected the sync adapter pattern for this reason.

### 14. Singleton pattern -- ACCIDENTAL

Entity cache uses factory injection (consistent with the codebase's DI pattern).
DataFrame cache uses a module-level singleton (`_dataframe_cache: DataFrameCache | None`
with `get_dataframe_cache()`/`set_dataframe_cache()`). The architecture assessment
(AP-009) identifies this as part of the "Singleton Constellation" anti-pattern. No design
reason prevents factory injection for `DataFrameCache`.

**Evidence**: `UnifiedTaskStore(cache: CacheProvider, ...)` (unified.py:71).
`_dataframe_cache` module-level singleton (dataframe_cache.py:962).

---

## Decision

**Accept the divergence with one convergence action.**

### Overall Assessment: Accept Divergence (12 of 14 dimensions intentional)

The two cache systems serve fundamentally different use cases:
- Entity cache: individual API response caching for correctness-sensitive write paths
- DataFrame cache: project-level analytical table caching for latency-sensitive read paths

11 of 14 dimensions are driven by these different requirements. The remaining gap
(dimensions 3 + 14, really one gap) is a DI consistency issue, not a cache architecture
issue.

### Convergence Action: Introduce DataFrameCache Protocol + DI

| Action | Effort | Impact |
|--------|--------|--------|
| Define `DataFrameCacheProtocol` in `protocols/` | ~2 hours | Enables `NullDataFrameCache` for testing, aligns with codebase DI pattern |
| Replace module-level singleton with factory injection | ~4 hours | Eliminates AP-009 instance, improves testability |
| **Total** | **~1 day** | Low risk, high consistency gain |

This is a standalone cleanup item, not a prerequisite for other work.

### On the "31 Cache Concepts" Concern (AP-008)

The 31 concepts are not a sign of accidental complexity. They fall into two coherent
clusters:

| Cluster | Concepts | Purpose |
|---------|----------|---------|
| Entity cache | CacheProvider, CacheEntry, EntryType, CompletenessLevel, FreshnessMode, FreshnessCoordinator, UnifiedTaskStore, WarmResult, TieredCacheProvider, HierarchyIndex | Per-GID API response caching with version-based freshness |
| DataFrame cache | DataFrameCache, DataFrameCacheEntry, FreshnessStatus, FreshnessInfo, MemoryTier, ProgressiveTier, SectionPersistence, SchemaRegistry, CircuitBreaker, Coalescer, BuildQuality | Per-project analytical DataFrame caching with SWR |
| Shared | MutationInvalidator, InvalidationEvent | Cross-system invalidation on mutations |

The concept count per cluster (~10-11 each) is proportionate to the complexity of each
system. The cognitive overhead comes from understanding two mental models, not from
unnecessary abstraction within either system. The existing `MutationInvalidator` correctly
bridges both systems at their only integration point.

**Recommendation**: Do not attempt to reduce concept count. Instead, improve discoverability
by documenting the two-cluster mental model (this ADR serves that purpose).

---

## Consequences

### Positive
1. The 14-dimension analysis provides a permanent reference for future cache questions
2. Engineers can quickly determine whether a divergence is by-design or accidental
3. The single convergence action (Protocol + DI) is scoped and low-risk

### Negative
1. Two caching mental models remain (accepted as inherent to the domain)
2. The convergence action adds one more protocol to `protocols/`

### Neutral
1. ADR-DATAFRAME-CACHE-DISPOSITION remains valid; this ADR extends rather than supersedes it

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| ADR-DATAFRAME-CACHE-DISPOSITION | Prior disposition decision (this ADR extends it) |
| AP-008 (Architecture Assessment) | Identified 31 cache concepts as cognitive overhead |
| AP-009 (Architecture Assessment) | Singleton Constellation anti-pattern (dimension 14) |
| `protocols/cache.py` | Entity cache CacheProvider protocol |
| `cache/integration/dataframe_cache.py` | DataFrame cache implementation |
| `cache/integration/mutation_invalidator.py` | Cross-system invalidation bridge |
| `cache/providers/unified.py` | Entity cache composition (UnifiedTaskStore) |
| `cache/dataframe/tiers/memory.py` | MemoryTier LRU + heap-bound eviction |
