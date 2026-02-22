# Architectural Review 1: Architectural Philosophy

**Date**: 2026-02-18
**Scope**: Philosophy extraction, caching cross-cut, consistency model, complexity budget, failure modes, cognitive load
**Methodology**: Remediation planner agents with philosophical analysis overlay
**Review ID**: ARCH-REVIEW-1

---

## 1. What the Codebase Values Most

### Primary Value: Operational Resilience

Every major architectural decision in autom8y-asana optimizes for continued operation under adverse conditions:

| Decision | Resilience Pattern |
|----------|-------------------|
| Two-tier cache (Redis+S3) | Redis down -> S3 fallback; S3 down -> Redis only |
| 4:2 servable-to-reject freshness ratio | Serve stale data rather than error |
| Per-project circuit breakers | One project's failure does not cascade |
| Container-aware memory sizing | Prevent OOM kills under memory pressure |
| Checkpoint-resume in Lambda warmer | Recover from timeout without losing progress |
| Legacy preload fallback | Progressive fails -> legacy path |
| Defensive Freshness import | `autom8y_cache` unavailable -> local enum fallback |

The system is designed to degrade gracefully rather than fail catastrophically.

### Secondary Value: API Call Minimization

Asana API rate limits (150 requests/minute per PAT) are the binding external constraint. The architecture treats API calls as a scarce resource:

| Mechanism | API Calls Saved |
|-----------|----------------|
| Entity cache (Redis/S3) | Avoids re-fetching cached entities |
| DataFrame cache (Memory/S3) | Avoids rebuilding DataFrames from entity data |
| LIS-optimized reordering | Minimizes subtask reorder API calls |
| Watermark incremental sync | Only fetches modified tasks since last sync |
| Cache warming (Lambda) | Pre-populates cache before API requests arrive |
| Batch API support | Multiple operations in single API call |

---

## 2. Consistent Trade-Offs

The codebase repeatedly makes the same trade-offs:

### Complexity Over Simplicity

When given a choice between a simple implementation and a more complex one that handles more edge cases, the codebase consistently chooses complexity:

| Choice | Simple Alternative | Complex Chosen | Rationale |
|--------|-------------------|----------------|-----------|
| 5-tier detection | Single detection function | 5 tiers with confidence | Genuine ambiguity requires graduated response |
| 6 freshness states | Binary fresh/stale | 6-state lifecycle | Nuanced caching decisions require nuanced state |
| Phase-based SaveSession | Simple sequential writes | 6-phase UoW | Data dependency ordering prevents inconsistency |
| Descriptor system | Manual properties | Metaclass-level descriptors | DRY at scale (800 -> 50 lines) |

### Availability Over Consistency

The system is explicitly AP (Availability + Partition-tolerance) in CAP terms:

| Situation | Availability Choice | Consistency Sacrifice |
|-----------|--------------------|-----------------------|
| Cache stale but servable | Serve stale data | Data may be minutes old |
| S3 unavailable | Serve from Redis only | No cold-tier durability |
| Redis unavailable | Serve from S3 or API | Higher latency |
| API rate-limited | Serve from cache | Cache may be beyond TTL |

### Defense-in-Depth

Multiple overlapping protection mechanisms:

| Protection Layer | What It Protects |
|-----------------|------------------|
| TTL expiration | Against unbounded staleness |
| MutationInvalidator | Against SDK-mutation staleness |
| CacheInvalidator | Against post-commit staleness |
| Circuit breaker | Against cascading S3 failures |
| Retry with backoff | Against transient network errors |
| Degraded mode mixin | Against complete cache failure |
| Completeness tracking | Against partial data serving |

### Backward Compatibility

The codebase preserves backward compatibility aggressively:

| Compatibility Pattern | Example |
|----------------------|---------|
| Deprecated aliases with warnings | `ReconciliationsHolder` (removed in WS5) |
| Backward-compatible facades | `ENTITY_TYPES`, `DEFAULT_ENTITY_TTLS` delegating to EntityRegistry |
| `extra="ignore"` on models | Accept unknown Asana API fields |
| Defensive imports with fallback | `Freshness` enum fallback when `autom8y_cache` unavailable |
| `EntityType.RECONCILIATIONS_HOLDER` kept | Enum value preserved even after alias class removed |

---

## 3. Architectural Metaphor: The Defensive Onion

The caching architecture can be understood as concentric rings of defense:

```
Ring 5 (outermost): Asana API
    |
    v
Ring 4: Circuit Breaker + Retry + Rate Limit
    |   (protects against API failures and rate limits)
    v
Ring 3: S3 Cold Tier
    |   (protects against Redis failure and cold starts)
    v
Ring 2: Redis Hot Tier
    |   (protects against API latency)
    v
Ring 1: Memory Cache (DataFrame)
    |   (protects against Redis latency for analytical queries)
    v
Ring 0 (core): Application Logic
    (always receives data, possibly stale)
```

Each ring absorbs a class of failure:
- **Ring 4** absorbs API outages and rate limits
- **Ring 3** absorbs Redis failures and cold starts
- **Ring 2** absorbs API latency
- **Ring 1** absorbs Redis latency for DataFrames

The system degrades by losing outer rings while inner rings continue operating.

---

## 4. Philosophy Contradictions

### Contradiction 1: Freshness as First-Class but Invalidation as Best-Effort

**The aspiration**: 3 freshness modes, 6 freshness states, SWR semantics, watermark tracking -- freshness is treated as a first-class concern with sophisticated modeling.

**The reality**: For external mutations (Asana UI changes), the only invalidation mechanism is TTL expiration. No webhooks, no polling for changes, no event-driven invalidation.

**Diagnosis**: The freshness model describes the *observable states* of cache entries but does not improve the *transition rate* between states. Stale data transitions to fresh only via TTL expiration or SDK-driven refresh, regardless of how precisely the freshness state is tracked.

### Contradiction 2: Unified Aspiration vs. Bifurcated Reality

**The aspiration**: A unified caching layer that handles all data types consistently.

**The reality**: Two separate cache systems (entity and DataFrame) with different:
- Freshness models (3-mode vs 6-state)
- Storage formats (JSON vs Parquet)
- Eviction policies (TTL vs LRU)
- Invalidation strategies (mutation-driven vs SWR)

The `CacheProvider` protocol provides a unified interface for the *entity* cache, but the DataFrame cache does not use it. There is no unified protocol that spans both systems.

### Contradiction 3: Immutability Aspiration vs. Mutable Singletons

**The aspiration**: Entity models are `frozen=True` Pydantic v2 models. Immutability is a stated architectural principle.

**The reality**: 6+ mutable singletons (`EntityRegistry._instance`, `SchemaRegistry._instance`, `ProjectTypeRegistry._instance`, `EntityProjectRegistry._instance`, `WatermarkRepository._instance`, `_BOOTSTRAP_COMPLETE`) hold mutable global state that any code path can read and some can modify.

The entity *models* are frozen, but the *registries that manage them* are mutable singletons. Immutability stops at the model boundary.

---

## 5. Consistency Model Analysis

### AP Semantics

The system operates under AP (Availability + Partition-tolerance) semantics:

| Property | Implementation |
|----------|---------------|
| Availability | Always serve data (4:2 servable ratio) |
| Partition tolerance | Graceful degradation when Redis/S3/API unavailable |
| Consistency | Eventual -- stale data served with bounded staleness (TTL) |

### Consistency Windows by Scenario

| Scenario | Consistency Window | Data Source |
|----------|-------------------|-------------|
| SDK mutation | ~0 seconds | CacheInvalidator fires immediately post-commit |
| External mutation (Asana UI) | 0 to TTL (entity-type-specific) | TTL expiration only |
| Process entity (external) | 0 to 1 minute | 1m TTL |
| Contact entity (external) | 0 to 15 minutes | 15m TTL |
| Business entity (external) | 0 to 1 hour | 1h TTL |
| Cache warming | 0 to warming interval | Lambda schedule |
| Cold start | 0 to first warm | S3 cold tier hydration |

### Implications

- **Within-SDK consistency**: Strong. `SaveSession.commit_async()` invalidates affected cache entries, and subsequent reads get fresh data.
- **Cross-system consistency**: Eventual. External mutations rely on TTL. The consistency window equals the entity's TTL.
- **Read-your-writes**: Guaranteed only for SDK-mediated writes. External writes have no read-your-writes guarantee within the TTL window.

---

## 6. Complexity Budget

### Cache Subsystem Size

| Component | LOC | % of Codebase |
|-----------|-----|---------------|
| `cache/` | 15,658 | 14.1% |
| `dataframes/` (cache integration) | ~2,000 (est.) | 1.8% |
| `lambda_handlers/` (cache warming) | 1,977 | 1.8% |
| Cache-related in `persistence/` | ~200 (est.) | 0.2% |
| **Total cache-related** | **~19,835** | **~17.9%** |

### Proportionality Assessment

| Perspective | Verdict |
|------------|---------|
| **For a caching layer over a rate-limited API**: Proportionate. Asana's 150 req/min limit and the system's sub-second response requirement justify sophisticated caching. |
| **For a typical CRUD application**: Over-engineered. Most applications need 1-2 cache tiers, not 4, and 2 freshness states, not 6. |
| **For the domain requirements**: Justified at the edge. The 14.1% allocation to `cache/` alone is high, but it implements 5 distinct strategies (null, memory, Redis, S3, tiered) plus invalidation, warming, completeness, and metrics. |
| **Conceptual density**: Over-budget. 31 distinct caching concepts for ~111K LOC means 1 caching concept per ~3,600 LOC. A more typical ratio would be 1 per ~10,000 LOC. |

---

## 7. Failure Modes Inventory

### Entity Cache Failure Modes (6)

| # | Failure | Trigger | Impact | Recovery |
|---|---------|---------|--------|----------|
| 1 | Redis connection lost | Network partition, Redis restart | Hot tier unavailable; fall back to S3 cold tier | Auto-reconnect via Redis client; serve from S3 |
| 2 | Redis OOM | Insufficient memory, TTL not expiring | Writes fail; reads degrade to S3 | Redis eviction policy kicks in; monitor memory |
| 3 | S3 access denied | IAM role change, key rotation | Cold tier unavailable; Redis-only operation | Circuit breaker opens; alert on access denied |
| 4 | S3 throttling | High request rate | Writes delayed; reads may timeout | Retry with backoff; circuit breaker |
| 5 | TTL misconfiguration | Config error, deployment issue | Entities cached too long (stale) or too short (excessive API calls) | Configuration validation at startup |
| 6 | Entry type mismatch | Code version skew | Cached entry has different schema than expected | Version metadata enables detection; stale entry evicted |

### DataFrame Cache Failure Modes (8)

| # | Failure | Trigger | Impact | Recovery |
|---|---------|---------|--------|----------|
| 1 | Memory LRU full | Too many sections cached | Eviction of less-used sections | LRU eviction; re-fetch on next access |
| 2 | Container OOM | Memory cache + application memory exceeds limit | Container killed | Container-aware sizing should prevent; restart recovers |
| 3 | S3 Parquet corruption | Interrupted write, storage error | Section cannot be loaded from S3 | Re-build from entity data; checkpoint-resume |
| 4 | Schema version mismatch | Schema changed since DataFrame was built | Columns missing or extra | SchemaVersionError detected; invalidate and rebuild |
| 5 | SWR background refresh fail | API error during revalidation | Stale data served longer | Extend stale TTL; retry on next SWR cycle |
| 6 | Watermark corruption | S3 write interrupted | Incremental sync starts from wrong point | Full sync triggered (watermark=None) |
| 7 | Section manifest inconsistency | Lambda timeout during checkpoint | Manifest claims section built, but Parquet is incomplete | Manifest validation on load; rebuild if inconsistent |
| 8 | Extractor error | Entity data shape changed | DataFrame build fails for section | Error logged; section skipped; partial DataFrame served |

### CircuitBreaker Thread Safety

Per-project circuit breakers maintain state (failure count, state machine) that is accessed from multiple threads (sync bridges create threads). The `threading.Lock` on each circuit breaker may contend under high concurrency, and the state machine transition (`CLOSED -> OPEN -> HALF_OPEN`) is not atomic.

**Potential failure**: Two concurrent requests both see the circuit breaker in `HALF_OPEN` state and both attempt the probe request, leading to double counting of success/failure.

---

## 8. Observability Assessment

### What Is Visible

| Observable | Mechanism | Coverage |
|-----------|-----------|----------|
| Cache hit/miss rates | `CacheMetrics` aggregator | All entity cache operations |
| Cache latency | Structured logging with `elapsed_ms` | All cache read/write paths |
| API call counts | Transport-level metrics | All Asana API calls |
| Circuit breaker state | Structured logging | Per-project state transitions |
| DataFrame build times | Structured logging | Builder operations |
| Lambda warmer progress | Checkpoint manifest | Per-section progress |
| W3C trace propagation | `observability/` module | Cross-service traces |
| Log-trace correlation | `observability/` module | Log entries linked to traces |

### What Is Hidden

| Hidden State | Risk | Remedy |
|-------------|------|--------|
| Singleton population status | Cannot verify all registries are populated without querying each | Startup health check querying each registry |
| Cross-registry consistency | No validation that 3 registries agree | Cross-registry integrity check at startup |
| Stale data age | Cache entries know their TTL but not how far past TTL they are | Add `stale_for_seconds` to cache metrics |
| DataFrame completeness gaps | If an extractor silently skips fields, DataFrame has missing columns | Schema validation at build time (partially exists) |
| Import-time registration success | `register_all_models()` succeeds or fails silently (idempotency guard) | Explicit registration count logging |
| Circular dependency cycle state | Lazy imports mask circular deps until specific code paths execute | Import-time cycle detection (not implemented) |

---

## 9. Cognitive Load Analysis

### 31 Distinct Caching Concepts

A developer modifying cache behavior must understand:

**Tier 1 -- Must know (10 concepts)**:
1. CacheProvider protocol
2. Redis hot tier
3. S3 cold tier
4. TieredCacheProvider (coordinates hot+cold)
5. CacheEntry base model
6. EntryType enum (14 types)
7. TTL (entity-type-specific)
8. Cache-aside read pattern
9. Write-through pattern
10. MutationInvalidator

**Tier 2 -- Should know (12 concepts)**:
11. Freshness enum (STRICT/EVENTUAL/IMMEDIATE)
12. 6 freshness states (DataFrame cache)
13. SWR semantics
14. Memory LRU tier (DataFrame)
15. S3 Parquet tier (DataFrame)
16. SectionManifest (checkpoint-resume)
17. WatermarkRepository (incremental sync)
18. CompletenessLevel (4 levels)
19. CacheInvalidator (post-commit)
20. Circuit breaker (per-project)
21. Container-aware sizing
22. Promotion (S3 -> Redis)

**Tier 3 -- Nice to know (9 concepts)**:
23. NullCacheProvider
24. InMemoryCacheProvider
25. CacheMetrics aggregator
26. DegradedModeMixin
27. DetectionCacheEntry
28. RelationshipCacheEntry
29. DataFrameMetaCacheEntry
30. Cache event integration (ADR-0023)
31. Lambda warmer self-continuation

### Cognitive Load Comparison

| System | Approximate Caching Concepts | LOC |
|--------|------------------------------|-----|
| Typical Flask/Django app | 5-8 | 10-50K |
| Medium API service | 10-15 | 50-100K |
| **autom8y-asana** | **31** | **111K** |
| Large distributed system | 20-40 | 500K+ |

The caching concept density (31 concepts / 111K LOC) is comparable to systems 3-5x larger. This is the most significant cognitive load concern identified in the review.

### Onboarding Impact

A new developer working on cache-related code faces a ~2-3 day learning curve to understand the caching subsystem, compared to the ~0.5-1 day typical for applications of this size. This is not blocking but is a measurable productivity cost.
