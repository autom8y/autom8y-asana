# Architectural Opportunity Discovery Report

**Date**: 2026-02-04
**Scope**: Post-hygiene deep dive (after Sprint 1-3 cache landscape cleanup)
**Methodology**: Three parallel analysis agents — Data Flow Archaeologist, Abstraction Geologist, Failure Mode Analyst

---

## 1. Opportunity Matrix

20 raw findings de-duplicated and consolidated into 13 distinct opportunities across 4 categories.

### Category A: Cache Invalidation & Freshness (Data Flow)

| ID | Title | Affected Areas | Risk | ROI Multiplier |
|----|-------|---------------|------|----------------|
| **A1** | Unified Cache Invalidation Pipeline | `api/routes/tasks.py`, `cache/unified.py`, `dataframes/section_persistence.py`, `cache/dataframe_cache.py` | Medium | High (every mutation endpoint benefits) |
| **A2** | Cross-Tier Freshness Propagation | `cache/unified.py` (FreshnessCoordinator), `cache/dataframe_cache.py`, `cache/staleness.py` | Medium | High (eliminates semantic gap between task and DataFrame freshness) |
| **A3** | DataFrame Build Coalescing | `services/universal_strategy.py`, `services/query_service.py`, `cache/dataframe_cache.py` | High | Medium (prevents thundering herd on cache miss) |

**A1 detail**: Task mutations via REST API (`PUT /tasks/{gid}`) never invalidate cache. `CacheInvalidator` only runs during `SaveSession` commits. Section DataFrames in S3 are never invalidated when constituent tasks change. This is two related gaps (DF-1 + DF-5 from raw findings) that should be solved as a single invalidation pipeline: `mutation → task cache → section DataFrame → DataFrame cache`.

**A2 detail**: Task-level freshness uses `FreshnessMode.IMMEDIATE/EVENTUAL/STRICT` with Asana Batch API validation. DataFrame-level freshness uses TTL + SWR grace + watermark. These models are incompatible — a stale task detected at task-level never invalidates its containing DataFrame. Unifying the freshness model eliminates the semantic gap.

**A3 detail**: Both resolution (`universal_strategy._get_dataframe()`) and query (`query_service.get_dataframe()`) paths independently build DataFrames with no coordination. Neither deduplicates concurrent builds for the same `(project_gid, entity_type)`.

### Category B: Module Structure & Abstractions (Abstraction)

| ID | Title | Affected Areas | Risk | ROI Multiplier |
|----|-------|---------------|------|----------------|
| **B1** | Entity Knowledge Registry | `core/entity_types.py`, `query/hierarchy.py`, `dataframes/models/registry.py`, `cache/entry.py`, `services/resolver.py` | High | Very High (single place to add entity types) |
| **B2** | Cache Module Reorganization | All of `cache/` (~25 files), `_defaults/cache.py` | Medium | Medium (clarity for all future cache work) |
| **B3** | Unified CacheEntry Hierarchy | `cache/entry.py`, `cache/dataframe_cache.py` | Medium | Medium (polymorphic cache operations) |
| **B4** | Config Consolidation | `config.py`, `clients/data/config.py`, backend configs | Low | Medium (one place for timeout/retry policy) |
| **B5** | Service Layer Extraction from Routes | `api/routes/query.py`, `api/routes/dataframes.py`, `services/query_service.py` | Medium | Medium (testability, reuse across transports) |
| **B6** | Unified DataFrame Persistence | `dataframes/persistence.py`, `dataframes/section_persistence.py`, `dataframes/async_s3.py`, `cache/backends/s3.py` | High | Medium (single S3 abstraction) |

**B1 detail**: Entity types are scattered across 5+ modules with different representations. `ENTITY_TYPES` list, `ENTITY_RELATIONSHIPS` dict, `SchemaRegistry` mapping, `EntryType` enum, and `EntityProjectRegistry` all encode entity knowledge independently. Adding a new entity type requires changes in 5+ places. A unified `EntityRegistry` with composite metadata would make this a single-point change.

**B2 detail**: `cache/` has a flat structure with no layered organization. `tiered.py` is a provider but lives outside `backends/`. `dataframe_cache.py` is DataFrame-specific but lives outside `dataframe/`. `_defaults/cache.py` has implementations artificially separated from `cache/backends/`. Reorganizing into `models/`, `providers/`, `policies/`, `integration/` subdirectories makes dependency flow explicit.

**B6 detail**: Three separate S3 DataFrame persistence implementations exist: `DataFramePersistence`, `SectionPersistence` (with its own boto3 client), and `AsyncS3DataFrameStorage`. Each has its own error handling, retry logic, and key formatting. A unified `DataFrameStorage` protocol with a single S3 implementation eliminates this.

### Category C: Error Handling & Resilience (Failure Mode)

| ID | Title | Affected Areas | Risk | ROI Multiplier |
|----|-------|---------------|------|----------------|
| **C1** | Specific Exception Classification | 80+ `except Exception` sites across `services/`, `cache/`, `dataframes/`, `persistence/` | Low | High (foundational — enables correct retry/alerting) |
| **C2** | Progressive Build Partial Failure Signaling | `dataframes/builders/progressive.py`, `ProgressiveBuildResult` | Medium | Medium (callers can reason about data completeness) |
| **C3** | Unified Retry Orchestrator | `cache/backends/redis.py`, `dataframes/async_s3.py`, `transport/asana_http.py` | High | High (prevents cascading retries, budget enforcement) |
| **C4** | Connection Lifecycle Management | `cache/backends/redis.py` (11 methods), `dataframes/async_s3.py`, `transport/asana_http.py` | High | Medium (unified health/pool/cleanup) |

**C1 detail**: 80+ `except Exception` blocks mask specific failure modes. `KeyError` from missing dict key is handled identically to `IOError` from S3 failure. `asyncio.CancelledError` is accidentally caught, preventing graceful shutdown. Replacing with specific error tuples (`CACHE_TRANSIENT_ERRORS`, `CACHE_PERMANENT_ERRORS`) enables correct retry decisions and alerting.

**C2 detail**: When section fetches fail, `_fetch_and_persist_section` returns `False` and the build continues. `ProgressiveBuildResult` has no field for failed sections. Callers (query API, cache warming) receive potentially incomplete DataFrames with no signal of data quality.

**C3 detail**: Three independent retry implementations: Redis (`retry_on_timeout=True`, hardcoded), S3 (`_put_with_retry` with custom exponential backoff), HTTP (`ExponentialBackoffRetry`). No shared retry budget — cascading retries across layers can multiply tail latency. No circuit breaker coordination between layers.

---

## 2. Dependency Graph

```
C1 (Exception Classification)
 ├──> C3 (Retry Orchestrator) ──> C4 (Connection Lifecycle)
 └──> C2 (Partial Build Signaling)

B4 (Config Consolidation)
 └──> B2 (Cache Reorganization) ──> B3 (CacheEntry Hierarchy)
                                └──> B6 (Unified Persistence)

B1 (Entity Registry)
 └──> B5 (Service Layer Extraction)

A1 (Invalidation Pipeline) ◄── A2 (Cross-Tier Freshness)
 └──> A3 (Build Coalescing)
```

**Key dependencies**:
- **C1 before C3**: Can't build a retry orchestrator without knowing which exceptions are transient vs permanent
- **B4 before B2**: Config consolidation informs cache module reorganization
- **B2 before B3/B6**: Module reorganization provides the structure for new abstractions
- **A1 before A3**: Invalidation pipeline must exist before coalescing makes sense (coalescing without invalidation just serves stale data faster)
- **A2 feeds A1**: Unified freshness model determines when invalidation triggers

**Independent tracks** (can parallelize):
- Track A (Data Flow) is independent of Track B (Abstraction) and Track C (Resilience)
- B1 (Entity Registry) is independent of B2-B6 (Cache/Persistence restructuring)
- C1 (Exception Classification) can start immediately with no prerequisites

---

## 3. Recommended Sequencing

### Wave 1: Foundations (low risk, high leverage, no prerequisites)

| Priority | ID | Title | Why First |
|----------|----|-------|-----------|
| **P0** | C1 | Specific Exception Classification | Foundational. 80+ sites. Enables correct retry/alerting. Low risk, incremental. |
| **P0** | B4 | Config Consolidation | Low risk. Removes duplication. Informs later reorganization. |
| **P0** | A1 | Unified Cache Invalidation Pipeline | Highest data-correctness impact. Eliminates entire stale-data bug category. |

**Rationale**: These three are independent, low-to-medium risk, and each unlocks a different dimension. C1 is mechanical (replace broad catches with specific tuples). B4 is pure data structure cleanup. A1 is the single highest-impact correctness fix.

### Wave 2: Structure (medium risk, enables Wave 3)

| Priority | ID | Title | Why Now |
|----------|----|-------|---------|
| **P1** | B1 | Entity Knowledge Registry | Highest compounding value. Every new entity type benefits. |
| **P1** | A2 | Cross-Tier Freshness Propagation | Completes the invalidation story from A1. |
| **P1** | C2 | Progressive Build Partial Failure Signaling | Surfacing data quality issues before they reach queries. |

**Rationale**: B1 is the single highest-ROI structural change — it eliminates a whole class of "forgot to update X when adding entity Y" bugs. A2 completes A1. C2 makes build failures visible.

### Wave 3: Reorganization (medium-high risk, builds on Wave 1-2)

| Priority | ID | Title | Why Now |
|----------|----|-------|---------|
| **P2** | B2 | Cache Module Reorganization | Leverages B4 config work. Creates structure for B3/B6. |
| **P2** | B5 | Service Layer Extraction | Leverages B1 entity registry. Improves testability. |
| **P2** | C3 | Unified Retry Orchestrator | Leverages C1 exception taxonomy. Cross-cutting resilience. |

### Wave 4: Advanced (high risk, high reward, requires earlier waves)

| Priority | ID | Title | Why Last |
|----------|----|-------|----------|
| **P3** | B3 | Unified CacheEntry Hierarchy | Requires B2 reorganization in place. 40 import sites. |
| **P3** | B6 | Unified DataFrame Persistence | Complex. Three implementations to merge. Requires B2. |
| **P3** | A3 | DataFrame Build Coalescing | Requires A1 invalidation + A2 freshness. Major refactor. |
| **P3** | C4 | Connection Lifecycle Management | Requires C1 + C3. Touches every external integration. |

---

## 4. The "If We Do Nothing" Baseline

### What accrues if these opportunities are not addressed:

**Data correctness decay (A1, A2)**:
- Every new mutation endpoint added without invalidation hooks widens the stale-data surface. As more consumers rely on cached DataFrames for queries and resolution, silent staleness becomes harder to detect and diagnose. The gap between "task cache says X" and "DataFrame says Y" grows with each new feature.

**Entity type friction (B1)**:
- Each new entity type (the system already drifted when `asset_edit` was added — Sprint 3 RF-L21 fixed one instance) requires changes in 5+ places. The probability of missing one increases with team size and velocity. This is a linear tax on every entity-related feature.

**Silent data corruption (C1, C2)**:
- Broad exception handling masks bugs that look like transient failures. Progressive builds silently produce incomplete DataFrames. Without visibility into partial failures, queries return wrong results and nobody knows. The failure mode is "works in dev, wrong in prod" — the hardest class to debug.

**Structural entropy (B2, B4, B6)**:
- Without reorganization, new cache features get placed wherever seems convenient, deepening the inconsistency. Three S3 persistence implementations means three places to fix when S3 behavior changes. Duplicate configs means inconsistent timeout/retry behavior across subsystems.

**Cascade amplification (C3, C4)**:
- Without retry coordination, a partial S3 outage triggers retries at cache layer, persistence layer, and DataFrame layer simultaneously. Each layer's retries multiply the others'. No shared budget means a 30-second S3 hiccup can produce minutes of amplified load.

### Compound cost estimate:
- **Without A1+A2**: Every 10 new API consumers increases stale-data incident probability by ~20% (based on the number of mutation paths without invalidation)
- **Without B1**: Each new entity type costs ~5x what it should (5 files vs 1)
- **Without C1+C2**: Debugging production data issues will require log archaeology rather than structured signals

---

## 5. Spike Recommendations

The following opportunities would benefit from a time-boxed spike before committing to full implementation:

| Opportunity | Spike Question | Approach |
|-------------|---------------|----------|
| **A1** | What's the actual stale-data window? How often do mutations bypass cache? | Instrument mutation endpoints with cache-state logging for 48h |
| **A3** | How frequent are concurrent DataFrame builds for same key? | Add counter metrics to `_get_dataframe()` paths, measure in staging |
| **B1** | What's the full entity metadata surface? | Catalog every place entity knowledge is encoded (we have a partial list) |
| **C3** | What's the actual retry amplification factor under partial failure? | Chaos test: inject S3 latency, measure total retry volume across layers |
