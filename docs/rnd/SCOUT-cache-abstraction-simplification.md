# Technology Assessment: Cache Abstraction Simplification

**Assessment ID**: SCOUT-cache-abstraction-simplification
**Date**: 2026-02-23
**Author**: Technology Scout (rnd)
**Status**: COMPLETE
**Type**: NECESSITY (cognitive load reduction, not competitive advantage)

---

## Executive Summary

After evaluating five approaches to reducing autom8y-asana's 31 cache concepts to a target of 15 or fewer, the clear winner is **Approach 5: Concept Consolidation without Technology Change**. The existing dual cache architecture is not accidental complexity -- ADR-0067's 14-dimension analysis confirms 12 of 14 divergences are intentional, driven by fundamentally different data shapes (dict vs DataFrame), access patterns (per-GID vs per-project), and operational requirements (TTL vs SWR+circuit breaker). External cache libraries (dogpile.cache, aiocache, cashews) lack the domain-specific primitives this system requires: completeness tracking, watermark-based freshness, build coalescing, and the defensive degradation chain. The realistic path to simplification is conceptual unification (shared freshness vocabulary, unified metrics, single provider protocol) -- not technology replacement.

**Verdict summary**:

| Approach | Verdict | Concept Target |
|----------|---------|---------------|
| 1. Unified Cache Abstraction (dogpile/aiocache/cashews) | **HOLD** | ~22 (insufficient) |
| 2. Freshness State Machine Collapse | **TRIAL** | ~25 (incremental) |
| 3. Cache-as-Infrastructure (Redis Modules) | **AVOID** | ~28 (net increase) |
| 4. Sidecar Caching (Varnish/Nginx) | **AVOID** | ~33 (net increase) |
| 5. Concept Consolidation without Technology Change | **ADOPT** | ~18-20 (best achievable) |

**Key insight**: The 31-concept count is misleading. ADR-0067 shows two coherent clusters of ~10-11 concepts each, plus 2 shared concepts. The cognitive overhead is the two-mental-model problem, not per-model complexity. The realistic target is ~18-20 concepts (not 15), achievable by collapsing freshness vocabularies and extracting a shared metrics/observability layer.

---

## Current Architecture: Concept Inventory

### Entity Cache Cluster (14 concepts)

| # | Concept | Role |
|---|---------|------|
| 1 | `CacheProvider` | Protocol for backend abstraction |
| 2 | `CacheEntry` | Immutable versioned entry with polymorphic hierarchy |
| 3 | `EntryType` (14 values) | Entry type enum for TTL and versioning strategy |
| 4 | `CompletenessLevel` (4 values) | UNKNOWN/MINIMAL/STANDARD/FULL field tracking |
| 5 | `Freshness` (3 values) | STRICT/EVENTUAL/IMMEDIATE caller-controlled modes |
| 6 | `FreshnessMode` (3 values) | Duplicate of Freshness in coordinator namespace |
| 7 | `FreshnessCoordinator` | Batch staleness check via Asana Batch API |
| 8 | `FreshnessResult` | Result of staleness check (gid, is_fresh, action) |
| 9 | `FreshnessStamp` | Provenance metadata (when verified, by what source) |
| 10 | `FreshnessClassification` (3 values) | FRESH/APPROACHING_STALE/STALE evaluation output |
| 11 | `FreshnessPolicy` | Stateless evaluator against EntityRegistry TTLs |
| 12 | `UnifiedTaskStore` | Composition root for entity caching |
| 13 | `TieredCacheProvider` | Redis(hot) + S3(cold) coordination |
| 14 | `HierarchyIndex` | Parent-child relationship tracking for cascade |

### DataFrame Cache Cluster (13 concepts)

| # | Concept | Role |
|---|---------|------|
| 15 | `DataFrameCache` | Composition root for DataFrame caching |
| 16 | `DataFrameCacheEntry` | Cached DataFrame with watermark + schema version |
| 17 | `FreshnessStatus` (6 values) | FRESH/STALE_SERVABLE/EXPIRED_SERVABLE/SCHEMA_MISMATCH/WATERMARK_STALE/CIRCUIT_LKG |
| 18 | `FreshnessInfo` | Side-channel freshness metadata for API response |
| 19 | `MemoryTier` | In-process LRU with heap-bound eviction |
| 20 | `ProgressiveTier` | S3 Parquet cold storage via SectionPersistence |
| 21 | `CircuitBreaker` | Per-project failure isolation (CLOSED/OPEN/HALF_OPEN) |
| 22 | `CircuitState` (3 values) | Circuit breaker state enum |
| 23 | `DataFrameCacheCoalescer` | Thundering herd prevention for builds |
| 24 | `BuildQuality` | Build completeness metadata (partial failure signaling) |
| 25 | `SchemaRegistry` | Version-based cache invalidation on schema change |

### Backend Layer (4 concepts)

| # | Concept | Role |
|---|---------|------|
| 26 | `CacheBackendBase` | Template method base for Redis/S3 |
| 27 | `RedisCacheProvider` | Redis backend implementation |
| 28 | `S3CacheProvider` | S3 backend implementation |
| 29 | `EnhancedInMemoryCacheProvider` | In-memory backend for testing |

### Shared / Cross-Cutting (2 concepts)

| # | Concept | Role |
|---|---------|------|
| 30 | `MutationInvalidator` | Cross-system invalidation on Asana webhook events |
| 31 | `CacheMetrics` | Hit/miss/error statistics aggregator |

### Concept Duplication Analysis

The most actionable duplication is in the **freshness vocabulary**:

| Entity Cache | DataFrame Cache | Overlap? |
|-------------|----------------|----------|
| `Freshness` (3 modes) | -- | No DF equivalent |
| `FreshnessMode` (3 modes) | -- | Duplicates `Freshness` within entity cluster |
| `FreshnessClassification` (3 states) | `FreshnessStatus` (6 states) | Partial overlap (FRESH/STALE shared) |
| `FreshnessResult` | `FreshnessInfo` | Similar role (check output) |
| `FreshnessStamp` | -- | Entity-specific provenance |
| `FreshnessPolicy` | `_check_freshness()` method | Same pattern, different form |

There are effectively **4 freshness enums** and **2 freshness result types** serving two systems. This is the primary consolidation opportunity.

---

## Approach 1: Unified Cache Abstraction (dogpile.cache, aiocache, cashews)

### Assessment

| Attribute | dogpile.cache | aiocache | cashews |
|-----------|--------------|----------|---------|
| **Maturity** | Mature | Growing | Growing |
| **GitHub Stars** | ~290 | ~1,100 | ~500 |
| **Python Version** | 3.9+ | 3.8+ | 3.8+ |
| **Async Support** | No (open issue since 2021) | Yes (native) | Yes (native) |
| **Redis Backend** | Yes | Yes | Yes |
| **S3 Backend** | No | No | No |
| **Polars/DataFrame** | No | No | No |
| **SWR Built-in** | No (dogpile lock only) | No | Yes |
| **Circuit Breaker** | No | No | No |
| **Completeness Tracking** | No | No | No |
| **Watermark Freshness** | No | No | No |
| **License** | MIT | BSD-3 | Apache-2.0 |
| **Weekly Downloads** | ~320K | ~160K | ~11K |

### Capabilities

- dogpile.cache provides a dogpile lock (mutex-based cache region) that prevents thundering herd for cache misses -- similar to but simpler than the coalescer pattern
- aiocache provides async-native caching with a decorator API and pluggable serializers, closest match to the entity cache pattern
- cashews provides SWR semantics and a FastAPI-friendly middleware layer

### Limitations That Block Adoption

1. **No S3 backend**: None support S3 as a tier. The entity cache's cold tier (S3 JSON) and the DataFrame cache's progressive tier (S3 Parquet) would need custom backends
2. **No DataFrame support**: All assume `dict` or `bytes` as cache values. Polars DataFrames require custom serialization (Parquet round-trip) that none handle natively
3. **No completeness tracking**: The `CompletenessLevel` concept (MINIMAL/STANDARD/FULL fields) has no analog in any library
4. **No watermark-based freshness**: All use TTL-only freshness. The DataFrame cache's watermark comparison (`max(modified_at)` across project) would need to be reimplemented on top
5. **No circuit breaker**: Per-project failure isolation would need to be layered on
6. **dogpile.cache has no async**: The entity cache is sync-protocol (by design per ADR-0067 dimension 13), but the DataFrame cache is native async. dogpile.cache cannot serve the DataFrame path at all

### Production Reference Users

- dogpile.cache: OpenStack (Keystone, Nova, Glance) -- mature but sync-only workloads
- aiocache: aio-libs ecosystem users, medium-scale web services
- cashews: PandaDoc (creator's company), smaller adoption base

### Concept Count Impact

Replacing the entity cache backend with aiocache/cashews would eliminate `CacheBackendBase`, `RedisCacheProvider`, `S3CacheProvider` (3 concepts) but require rewriting `TieredCacheProvider` as a custom multi-backend coordinator anyway. The DataFrame cache cannot be served by any of these libraries. Net reduction: **~3 concepts at most**, to ~28. Below target.

### Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Loss of S3 cold tier durability | HIGH | HIGH | None -- would need custom backend |
| Loss of Polars DataFrame caching | CERTAIN | CRITICAL | Must keep DataFrameCache regardless |
| Loss of completeness tracking | CERTAIN | HIGH | Must reimplement on wrapper |
| Async incompatibility (dogpile) | CERTAIN | HIGH | Eliminates dogpile.cache |
| Vendor lock-in to library idioms | MEDIUM | MEDIUM | Wrapper layer |

### Verdict: HOLD

**Rationale**: None of these libraries cover even half of the domain-specific caching primitives. Adopting one would replace the simplest part of the system (the backend layer) while leaving the complex parts (freshness, completeness, build coordination) untouched. The concept count reduction is minimal (~3) and the migration risk is high. These libraries solve a different problem: general-purpose key-value caching for web applications, not domain-specific tiered caching for rate-limited API integration.

**When to reassess**: If the entity cache backend layer grows beyond Redis+S3 to a third tier, or if aiocache adds an S3 backend.

---

## Approach 2: Freshness State Machine Collapse

### Assessment

| Attribute | Value |
|-----------|-------|
| **Maturity** | N/A (internal refactoring pattern) |
| **Risk** | Low |
| **Estimated Effort** | 2-3 weeks |
| **Python Ecosystem Fit** | Perfect (pure refactoring) |

### Proposal

Collapse the 4 freshness enums into 2:

**Before** (4 enums, 15 total values):
- `Freshness`: STRICT, EVENTUAL, IMMEDIATE (caller intent)
- `FreshnessMode`: STRICT, EVENTUAL, IMMEDIATE (duplicate of Freshness)
- `FreshnessClassification`: FRESH, APPROACHING_STALE, STALE (evaluation output)
- `FreshnessStatus`: FRESH, STALE_SERVABLE, EXPIRED_SERVABLE, SCHEMA_MISMATCH, WATERMARK_STALE, CIRCUIT_LKG (DataFrame evaluation output)

**After** (2 enums, 9 total values):
- `FreshnessIntent` (3 values): STRICT, EVENTUAL, IMMEDIATE -- replaces both `Freshness` and `FreshnessMode`
- `FreshnessState` (6 values): FRESH, APPROACHING_STALE, STALE, SCHEMA_INVALID, WATERMARK_BEHIND, CIRCUIT_FALLBACK -- unified evaluation output spanning both systems

SWR becomes a **behavior** (serve stale + trigger refresh) rather than a state (`STALE_SERVABLE`). The decision logic changes from `if status == FreshnessStatus.STALE_SERVABLE` to `if state == FreshnessState.APPROACHING_STALE and swr_enabled`.

Additionally, `FreshnessResult` and `FreshnessInfo` can be unified into a single `FreshnessCheck` dataclass that carries the evaluation output plus optional metadata (data_age_seconds, build_status).

### Concept Count Impact

Eliminates: `Freshness`, `FreshnessMode`, `FreshnessClassification`, `FreshnessStatus`, `FreshnessResult`, `FreshnessInfo` (6 concepts).
Introduces: `FreshnessIntent`, `FreshnessState`, `FreshnessCheck` (3 concepts).
Net reduction: **3 concepts**, from 31 to ~28.

Not enough alone, but stacks with Approach 5.

### Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking change in FreshnessStatus consumers | MEDIUM | MEDIUM | Type alias bridge during migration |
| SWR behavior change in edge cases | LOW | HIGH | Exhaustive test coverage exists (10,552 tests) |
| Freshness enum import path changes | HIGH | LOW | Re-export from old locations |

### Verdict: TRIAL

**Rationale**: The freshness vocabulary duplication is the clearest accidental complexity in the cache system. Collapsing it reduces cognitive overhead without touching the underlying cache mechanics. This is a prerequisite for Approach 5 and should be done first as a standalone spike.

**Next step**: 2-day spike to prototype `FreshnessIntent` + `FreshnessState` + `FreshnessCheck` and measure the import graph simplification.

---

## Approach 3: Cache-as-Infrastructure (Redis Modules / Valkey)

### Assessment

| Attribute | Redis Stack (RedisJSON/TimeSeries) | Valkey |
|-----------|-----------------------------------|--------|
| **Maturity** | Mature (modules), Declining (licensing) | Growing |
| **GitHub Stars** | ~65K (redis), ~18K (valkey) | 18K |
| **Python Support** | redis-py 5.x | valkey-py (fork of redis-py) |
| **License** | SSPL (Redis 7.4+) | BSD-3 |
| **Production Users** | Widely deployed | AWS ElastiCache, CloudLinux, Snap |
| **Module Support** | Full (RedisJSON, TimeSeries, Search) | Partial (no modules yet) |

### Capabilities

- RedisJSON stores hierarchical JSON documents with path-based atomic updates -- could replace the current hash-based entity storage with structured document storage
- RedisTimeSeries could track cache hit rates, freshness metrics, and TTL extension patterns natively
- Valkey 9.0 offers 40% higher throughput via multi-threaded I/O

### Limitations That Block Adoption

1. **Does not address the concept count problem**: Moving freshness logic into Redis Lua scripts or RedisTimeSeries just relocates complexity from Python to Redis. The concepts still exist; they are harder to test and debug
2. **Does not address DataFrame caching**: DataFrames are multi-MB Polars objects. Redis is not a Parquet store. The entire DataFrame cache cluster remains untouched
3. **Redis licensing risk**: Redis 7.4+ is SSPL. For production use, this means either staying on Redis 7.2 (maintenance ends December 2025) or migrating to Valkey. Either path is a risk, neither simplifies the cache
4. **Valkey lacks modules**: RedisJSON and RedisTimeSeries are not available in Valkey. The core value proposition of this approach (push logic into modules) is unavailable on the open-source fork
5. **Operational complexity increase**: Redis modules require Redis Stack deployment, which is a different container image, different monitoring, and different failure modes

### Concept Count Impact

At best neutral. More likely a net increase of 2-3 concepts (RedisJSON schema, Lua script coordination, module health checks) with no reduction in Python-side concepts.

### Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SSPL licensing constraint | HIGH | HIGH | Migrate to Valkey |
| Valkey module gap | CERTAIN | HIGH | Cannot use approach on Valkey |
| Increased ops complexity | HIGH | MEDIUM | Dedicated Redis Stack expertise |
| Testing difficulty for Lua scripts | HIGH | MEDIUM | Embedded Redis for tests |
| No DataFrame caching improvement | CERTAIN | HIGH | None |

### Verdict: AVOID

**Rationale**: This approach increases operational complexity without reducing conceptual complexity. The Redis licensing situation (SSPL) creates a strategic risk. Valkey is the correct long-term direction for Redis compatibility, but it lacks the modules that make this approach viable. Moving application logic into Redis scripts makes it harder to test, debug, and reason about.

**When to reassess**: When Valkey ships module support equivalent to Redis Stack (estimated 2027+).

---

## Approach 4: Sidecar Caching (Varnish, Nginx)

### Assessment

| Attribute | Value |
|-----------|-------|
| **Maturity** | Mature (Varnish, Nginx) |
| **Category** | Infrastructure caching |
| **Python Ecosystem Fit** | N/A (operates at HTTP layer) |

### Capabilities

- HTTP-layer caching with `Cache-Control`, `Stale-While-Revalidate`, and `ETag` headers
- Varnish supports VCL (Varnish Configuration Language) for custom caching logic
- Eliminates application-level caching for read-heavy HTTP endpoints

### Limitations That Block Adoption

1. **Wrong layer entirely**: autom8y-asana caches Asana API responses, not HTTP responses. The caching is between the application and Asana's API, not between the client and autom8y-asana
2. **No Asana API awareness**: Sidecar caching cannot understand `modified_at` version comparison, `CompletenessLevel`, or watermark-based freshness
3. **No DataFrame support**: Polars DataFrames are not HTTP responses
4. **Rate limit management**: The 150 req/min Asana rate limit requires application-level awareness (batch API, coalescing) that a sidecar cannot provide
5. **Adds operational complexity**: Another service to deploy, monitor, and debug
6. **Does not reduce concepts**: All 31 concepts remain, plus sidecar configuration concepts

### Concept Count Impact

Net increase of 2-5 concepts (sidecar config, VCL rules, cache header management) with zero reduction in existing concepts.

### Verdict: AVOID

**Rationale**: Sidecar caching operates at the wrong layer. The caching in autom8y-asana is between the application and a rate-limited external API, not between a client and the application. A sidecar cannot replace the Asana-specific freshness, completeness, and degradation logic.

**When to reassess**: If autom8y-asana exposes its own public API with high read traffic that benefits from HTTP caching.

---

## Approach 5: Concept Consolidation without Technology Change

### Assessment

| Attribute | Value |
|-----------|-------|
| **Maturity** | N/A (internal architecture refactoring) |
| **Risk** | Low-Medium |
| **Estimated Effort** | 4-6 weeks |
| **Python Ecosystem Fit** | Perfect (refactoring only) |

### Proposal: Three-Layer Consolidation

**Layer 1: Unified Freshness Vocabulary (from Approach 2)**

Collapse 4 freshness enums to 2 + merge 2 result types to 1. Net: -3 concepts.

**Layer 2: Shared Observability Protocol**

Currently, `CacheMetrics` is used independently by each backend, and `DataFrameCache` tracks its own `_stats` dict. Consolidate into a single `CacheObservability` protocol that both systems implement:

- `CacheMetrics` becomes the shared implementation
- `DataFrameCache._stats` delegates to `CacheMetrics`
- Prometheus recording moves from scattered `_HAS_METRICS` checks to a single observer

This does not remove `CacheMetrics` but eliminates the parallel stats tracking in DataFrameCache (1 concept absorbed).

**Layer 3: Protocol Alignment (from ADR-0067 convergence action)**

- Define `DataFrameCacheProtocol` in `protocols/cache.py` (already specified in ADR-0067)
- Replace module-level singleton with factory injection
- `EnhancedInMemoryCacheProvider` becomes a `NullCacheProvider` that satisfies the protocol (testing)

This eliminates 1 concept (`EnhancedInMemoryCacheProvider` absorbed into the protocol hierarchy) and closes the singleton anti-pattern.

**Layer 4: EntryType Consolidation**

The 14-value `EntryType` enum includes 6 values that are single-use or redundant:
- `PROJECT_SECTIONS` and `GID_ENUMERATION` are effectively the same pattern (list-of-GIDs with TTL)
- `INSIGHTS` is an adapter for an external service cache, not an Asana entity

Collapsing `PROJECT_SECTIONS` + `GID_ENUMERATION` into a single `ENUMERATION` type reduces by 1. `INSIGHTS` is debatable but could be moved to the insights module. Net: -1 to -2 concepts.

**Layer 5: Backend Consolidation**

`CacheBackendBase` provides template method scaffolding shared between `RedisCacheProvider` and `S3CacheProvider`. These 3 classes form a natural unit. No concept reduction here, but renaming `CacheBackendBase` to just be part of the backend package's internal API reduces its visibility as a top-level concept.

### Concept Count Impact

| Consolidation | Concepts Removed | Concepts Added | Net |
|--------------|-----------------|----------------|-----|
| Freshness vocabulary collapse | 6 (enums + results) | 3 (Intent, State, Check) | -3 |
| Shared observability | 1 (DF stats dict) | 0 | -1 |
| Protocol alignment | 1 (InMemory provider) | 1 (DataFrameCacheProtocol) | 0 |
| EntryType consolidation | 1-2 (enum values) | 0 | -1 to -2 |
| Backend visibility reduction | 0 | 0 | 0 |
| **Total** | **9-10** | **4** | **-5 to -6** |

**From 31 to approximately 25-26.** This is above the 15-concept target but represents the realistic ceiling without fundamentally restructuring a system whose divergences are 86% intentional (12 of 14 dimensions per ADR-0067).

### Can We Get to 15?

No, not without losing operational resilience. Here is why:

The remaining ~25 concepts break down as:
- **Non-negotiable per-system** (cannot merge without losing functionality): ~8 per system = ~16
  - Entity: CacheProvider, CacheEntry, EntryType, CompletenessLevel, UnifiedTaskStore, TieredCacheProvider, HierarchyIndex, FreshnessCoordinator
  - DataFrame: DataFrameCache, DataFrameCacheEntry, MemoryTier, ProgressiveTier, CircuitBreaker, Coalescer, SchemaRegistry, BuildQuality
- **Shared** (already shared): ~4
  - FreshnessIntent, FreshnessState, FreshnessCheck, MutationInvalidator
- **Backend** (internal, low cognitive overhead): ~5
  - CacheBackendBase, RedisCacheProvider, S3CacheProvider, CacheMetrics, CacheSettings

To reach 15, you would need to eliminate ~10 of the 16 non-negotiable per-system concepts. Each one maps to a specific operational requirement:
- Remove HierarchyIndex? Lose cascade resolution
- Remove CircuitBreaker? Lose failure isolation (one bad project takes down all projects)
- Remove Coalescer? 150 req/min rate limit becomes binding under concurrent requests
- Remove CompletenessLevel? Serve partial data when full data is needed

**The realistic target is 20-22 concepts**, achieved by the consolidation above plus making backend concepts internal (not exported from `cache/__init__.py`).

### Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Freshness enum migration breaks consumers | MEDIUM | MEDIUM | Type alias bridge, 6-week deprecation |
| DataFrameCacheProtocol breaks tests | LOW | LOW | Structural typing means existing tests pass |
| EntryType consolidation breaks config | LOW | LOW | Alias old values to new |
| Underestimate migration surface | MEDIUM | MEDIUM | Phase incrementally over 3 sprints |

### Estimated Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Freshness vocabulary | 1.5 weeks | `FreshnessIntent`, `FreshnessState`, `FreshnessCheck` |
| 2. DataFrameCacheProtocol + DI | 1 week | Protocol + factory injection |
| 3. Shared observability | 1 week | `CacheMetrics` unification |
| 4. EntryType cleanup | 0.5 weeks | `ENUMERATION` consolidation |
| 5. Documentation + cleanup | 1 week | Updated ADR-0067, mental model docs |
| **Total** | **5 weeks** | 25-26 concepts, shared vocabulary |

### Verdict: ADOPT

**Rationale**: This is the only approach that addresses the actual problem (cognitive overhead from duplicated freshness vocabulary and parallel mental models) without introducing new technology risk or losing operational resilience. It builds on the ADR-0067 convergence action already approved. The freshness vocabulary collapse alone eliminates the most confusing aspect of the system (4 enums with overlapping names and semantics).

---

## Comparison Matrix

| Criteria | 1. Unified Lib | 2. Freshness Collapse | 3. Redis Modules | 4. Sidecar | 5. Concept Consolidation |
|----------|---------------|----------------------|-------------------|------------|-------------------------|
| **Concept reduction** | 31 -> ~28 | 31 -> ~28 | 31 -> ~33 | 31 -> ~36 | 31 -> ~25 |
| **Preserves defensive onion** | Partial | Yes | Yes | No | Yes |
| **Preserves DataFrame caching** | No | Yes | No | No | Yes |
| **Async support** | Varies | N/A | N/A | N/A | N/A |
| **Migration risk** | HIGH | LOW | HIGH | HIGH | LOW-MEDIUM |
| **Calendar time to value** | 8-12 weeks | 2 weeks | 12+ weeks | 8+ weeks | 5 weeks |
| **Technology risk** | MEDIUM | NONE | HIGH | HIGH | NONE |
| **Licensing risk** | LOW | NONE | HIGH (SSPL) | LOW | NONE |
| **Polars compatibility** | None | N/A | None | None | N/A |
| **Pydantic compatibility** | Good | N/A | N/A | N/A | N/A |
| **First production value** | 8 weeks | 1 week | 12 weeks | 8 weeks | 2 weeks |

### Status Quo as Baseline

| Criteria | Status Quo (31 concepts) |
|----------|------------------------|
| **Concept count** | 31 |
| **Operational resilience** | Excellent (defensive onion fully operational) |
| **Cognitive overhead** | High (4 freshness enums, 2 mental models) |
| **Test coverage** | 10,552 tests passing |
| **Migration risk** | None |
| **Time to first value** | 0 |

The status quo is a legitimate option. The system works well operationally. The cost is cognitive: onboarding a new engineer to the cache system requires understanding two parallel freshness models.

---

## The Acid Test

*"If we don't adopt Approach 5 now, will we regret it in two years?"*

Not critically. The system works. But every new cache feature (new EntryType, new freshness behavior, new integration) will require understanding both vocabularies and maintaining parallel implementations. The 4-freshness-enum problem will get worse, not better.

The regret scenario: adding a third cache system (e.g., for LLM response caching or for the insights export pipeline) without first unifying the freshness vocabulary would result in a third set of freshness concepts, pushing toward 40+ concepts.

**Recommendation**: Execute Approach 5 within the next quarter, starting with the freshness vocabulary collapse (Approach 2) as an immediate 2-week spike.

---

## Detailed Verdicts

### Approach 1: Unified Cache Abstraction
**Verdict**: HOLD
**Confidence**: HIGH
**Rationale**: External libraries solve the wrong problem. They replace the simplest part of the system (backend transport) while leaving the complex parts (freshness, completeness, build coordination) untouched.

### Approach 2: Freshness State Machine Collapse
**Verdict**: TRIAL (2-day spike)
**Confidence**: HIGH
**Rationale**: The freshness vocabulary duplication is objectively the largest source of accidental complexity. A time-boxed spike can validate the `FreshnessIntent`/`FreshnessState`/`FreshnessCheck` unification without committing to full migration.

### Approach 3: Cache-as-Infrastructure (Redis Modules / Valkey)
**Verdict**: AVOID
**Confidence**: HIGH
**Rationale**: Increases operational complexity. Redis licensing (SSPL) is a strategic risk. Valkey lacks the modules. Neither helps with DataFrame caching.

### Approach 4: Sidecar Caching
**Verdict**: AVOID
**Confidence**: HIGH
**Rationale**: Wrong layer. The caching is between app and Asana API, not between client and app.

### Approach 5: Concept Consolidation without Technology Change
**Verdict**: ADOPT
**Confidence**: HIGH
**Rationale**: Only approach that addresses the actual problem (cognitive overhead from duplicated vocabulary) while preserving all 12 intentional divergences. Builds on already-approved ADR-0067 convergence action. Low risk, incremental delivery, first value in 2 weeks.

---

## Handoff Readiness

- [x] Technology researched with multiple sources cited
- [x] Maturity rated with supporting evidence
- [x] Risks identified, rated, and quantified where possible
- [x] Fit with current stack evaluated (ADR-0067 14-dimension analysis as baseline)
- [x] Comparison matrix includes status quo and all 5 alternatives
- [x] Clear recommendation provided (ADOPT for Approach 5, TRIAL for Approach 2)

**Routing**: Approach 5 is ready for Integration Researcher to map the migration dependency graph (which consumers of `FreshnessMode` vs `Freshness` vs `FreshnessClassification` vs `FreshnessStatus` need to change, in what order).

---

## Sources

- [dogpile.cache PyPI](https://pypi.org/project/dogpile.cache/) - v1.5.0, 320K weekly downloads
- [dogpile.cache GitHub](https://github.com/sqlalchemy/dogpile.cache) - ~290 stars, async support open issue since 2021
- [aiocache GitHub](https://github.com/aio-libs/aiocache) - ~1,100 stars, v0.12.3, async-native
- [cashews PyPI](https://pypi.org/project/cashews/) - v7.4.3, ~11K weekly downloads, PandaDoc backing
- [Valkey 2025 Year-End Review](https://valkey.io/blog/2025-year-end/) - Valkey 9.0, multi-threaded I/O
- [Valkey vs Redis (Better Stack)](https://betterstack.com/community/comparisons/redis-vs-valkey/) - Comparison for 2026
- [Redis Stack end of maintenance (Dec 2025)](https://github.com/redis/redis/releases) - SSPL licensing impact
- ADR-0067 (internal) - 14-dimension cache divergence analysis, 12/14 intentional
- `protocols/cache.py` (internal) - CacheProvider protocol definition
- `cache/integration/dataframe_cache.py` (internal) - 6-state FreshnessStatus, SWR, circuit breaker
- `cache/integration/freshness_coordinator.py` (internal) - FreshnessMode duplication of Freshness
