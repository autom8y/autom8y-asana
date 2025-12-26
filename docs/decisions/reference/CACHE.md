# ADR Summary: Cache Architecture

> Consolidated decision record for caching strategies, staleness detection, TTL management, and cache invalidation. Individual ADRs provide detailed alternatives analysis and implementation guidance.

## Overview

The autom8_asana SDK implements a sophisticated caching layer that transforms API access patterns from "fetch every time" to "fetch once, serve many." This journey from 4,000 lines of dormant infrastructure to a production-ready, observable, gracefully degrading cache spans 25 architectural decisions across 12 months.

The cache architecture evolved in four phases: (1) foundation building with protocol design and two-tier storage, (2) task-level caching with entity-aware TTLs, (3) DataFrame optimization with batch operations and GID enumeration caching, and (4) staleness detection with progressive TTL extension. Each phase addressed specific performance bottlenecks revealed through production profiling and TDD-driven discovery.

The result is a system that reduces API calls by 79% for stable entities, achieves sub-1-second warm DataFrame fetches for 3,500-task projects, and maintains correctness through automatic invalidation hooks and lightweight freshness checks. The architecture prioritizes graceful degradation—cache failures never prevent operations from completing—and observability through structured logging and metrics.

## Key Decisions

### 1. Cache Protocol: Extensible Provider Interface
**Context**: Need to evolve from basic get/set/delete to versioned operations with batch support and staleness checking without breaking existing implementations.

**Decision**: Extend the existing `CacheProvider` protocol with new versioned methods while preserving original methods. All new methods have default no-op implementations for backward compatibility.

**Rationale**: Python's structural subtyping allows gradual adoption. Existing `NullCacheProvider` and `InMemoryCacheProvider` continue working. New `RedisCacheProvider` can leverage backend-specific optimizations (MGET, MSET) while maintaining protocol compliance.

**Alternatives Rejected**: Separate `VersionedCacheProvider` protocol (adds complexity), inheritance-based extension (violates protocol pattern), wrapper/decorator (prevents backend optimization).

**Source ADRs**: ADR-0016

**Impact**: Foundation for all subsequent cache features. Zero breaking changes while enabling 8 new methods.

---

### 2. Storage Architecture: Two-Tier Redis + S3
**Context**: Redis-only approach (ADR-0017) proved insufficient after production analysis revealed 80% of data is cold but stored in expensive memory tier. Computed STRUC data must survive Redis restarts.

**Decision**: Implement two-tier cache with Redis (hot, ephemeral, 1-24h TTL) and S3 (cold, durable, 7-30d TTL). Write-through to both tiers, cache-aside reads with automatic promotion.

**Rationale**:
- **Durability**: S3 survives Redis restarts; STRUC rebuilding requires hours of API calls
- **Cost**: $25/month vs $92/month for 13GB
- **Performance**: Hot data stays fast in Redis, cold data economically stored in S3
- **Feature flag**: `ASANA_CACHE_S3_ENABLED` enables safe rollout with instant rollback

**Alternatives Rejected**: Redis-only (no durability), S3-only (50-200ms latency fails NFR), Redis persistence (doesn't reduce cost), DynamoDB (more expensive than S3 for cold data).

**Source ADRs**: ADR-0026

**Impact**: 80-90% cost reduction while achieving durability requirement. Enables scale to petabytes without memory ceiling.

---

### 3. Granularity: Per-Task with Project Context
**Context**: DataFrame extraction requires task data, but the same task may have different custom field values in different projects (multi-homed tasks).

**Decision**: Cache extracted rows at per-task granularity with project context: `{task_gid}:{project_gid}`. Each task+project combination gets independent cache entry.

**Rationale**:
- **Precision**: Task modification invalidates only that task, not entire project
- **Correctness**: Multi-homed tasks have different section/custom field values per project
- **Hit rate**: Per-task caching maximizes cache hits (99% for 10 task modifications out of 1000)

**Alternatives Rejected**: Per-project (poor hit rate, invalidates all on any change), per-section (still coarse-grained), per-task without context (silent data corruption for multi-homed tasks).

**Source ADRs**: ADR-0021, ADR-0032

**Impact**: Enables correct caching for multi-project scenarios while maintaining high hit rates.

---

### 4. Staleness Detection: Lightweight Checks with Progressive TTL
**Context**: Cache entries need freshness guarantees without expensive full-fetch validation. Different operations tolerate different staleness levels.

**Decision**: Use `modified_at` comparison with `Freshness` parameter (STRICT vs EVENTUAL). STRICT mode fetches current `modified_at` from API before returning cache. Progressive TTL extension: exponential doubling from 300s to 86400s ceiling based on repeated unchanged checks.

**Rationale**:
- **Flexibility**: EVENTUAL (fast, may be seconds stale) for dataframes, STRICT (slow, always current) for user edits
- **Efficiency**: Fetching only `modified_at` (not full payload) is 95% cheaper than full fetch
- **Progressive TTL**: 79% API call reduction for stable entities over 2-hour session

**Alternatives Rejected**: TTL-only (no freshness guarantee), ETag-based (Asana API doesn't support), polling (too complex), webhook-driven (optional infrastructure).

**Source ADRs**: ADR-0019, ADR-0133

**Impact**: Enables both fast eventual consistency and strong consistency for critical paths. Progressive extension dramatically reduces API calls for stable reference data.

---

### 5. Batch Operations: Check-Fetch-Populate Pattern
**Context**: DataFrame build for 3,500-task project requires checking and populating 3,500 cache entries. Individual operations would be O(n) latency.

**Decision**: Implement check-fetch-populate pattern using `get_batch()` and `set_batch()`:
1. Batch check all expected keys before API call
2. Fetch only cache misses via parallel section fetch
3. Batch populate newly fetched tasks
4. Merge cached + fetched results

**Rationale**:
- **Performance**: 1 batch call vs 3,500 individual calls
- **Partial cache**: Handles mixed hit/miss scenarios efficiently
- **Staleness**: Per-task versioning via `modified_at`

**Alternatives Rejected**: Fetch-then-cache (warm cache still hits API), individual operations (unacceptable latency), cache entire project result (thrashing).

**Source ADRs**: ADR-0116, ADR-0120

**Impact**: Sub-1-second warm fetches for large projects. Enables practical DataFrame caching.

---

### 6. TTL Management: Entity-Type Resolution
**Context**: Business entities change weekly, Process entities change every minute. Single TTL suboptimal for all.

**Decision**: Config-driven TTL resolution with priority: project-specific > entity-type > entry-type > default. Entity type detection at cache store time.

**TTL Defaults**:
- Business: 3600s (1 hour) - root entity, metadata only
- Contact/Unit: 900s (15 min) - low update frequency
- Offer: 180s (3 min) - pipeline movement
- Process: 60s (1 min) - state machine transitions
- Default: 300s (5 min) - balanced

**Rationale**: Entity semantics predict change frequency better than recent modification time. Configurable per-project for special cases (archive: 24h, active pipeline: 30s).

**Alternatives Rejected**: Hardcoded constants (not customizable), single global TTL (suboptimal for all), custom field detection (fragile), user callback (complex), modified-at-based (ignores semantics).

**Source ADRs**: ADR-0126

**Impact**: Optimized cache hit rates across heterogeneous entity types without manual configuration.

---

### 7. Invalidation: Post-Commit Hook with Multi-Project Awareness
**Context**: SaveSession modifications make cached data stale. Task can be multi-homed in multiple projects.

**Decision**: Extend `_invalidate_cache_for_results()` to invalidate both `EntryType.TASK` and `EntryType.DATAFRAME` entries. Query task memberships to invalidate all project-specific DataFrame entries.

**Rationale**:
- **Immediate consistency**: Self-writes via SaveSession invalidate immediately
- **Multi-project**: Memberships query ensures all contexts invalidated
- **Resilience**: Invalidation failures logged but don't fail commit

**Alternatives Rejected**: Event-based (over-engineered), direct pipeline injection (tight coupling), invalidation in state reset (misses actions), pre-commit (wrong timing).

**Source ADRs**: ADR-0125, ADR-0137

**Impact**: Write-then-read pattern sees fresh data. Multi-homed tasks correctly invalidated across all projects.

---

### 8. GID Enumeration Caching: Two-Tier Section + Enumeration
**Context**: Warm DataFrame fetch still taking 9.67s instead of <1s target. Root cause: GID enumeration (list sections, fetch section GIDs) not cached—35+ API calls before task cache consulted.

**Decision**: Cache section list (30-min TTL, stable) and GID enumeration (5-min TTL, more volatile) at fetcher level using constructor-injected cache provider.

**Cache Structure**:
- `PROJECT_SECTIONS`: `project:{gid}:sections` → section metadata (1800s TTL)
- `GID_ENUMERATION`: `project:{gid}:gid_enumeration` → `dict[section_gid, list[task_gid]]` (300s TTL)

**Rationale**:
- **10x speedup**: Warm fetch <1s (was 9.67s)
- **Independent TTLs**: Section structure stable, task membership changes more
- **Partial refresh**: Section cache can hit even when GID enum expired

**Alternatives Rejected**: Single-tier (can't have different TTLs), per-section caching (higher overhead), builder-level (wrong scope), no coordinator (correct for simple operation).

**Source ADRs**: ADR-0131

**Impact**: Achieves <1s warm fetch target. Zero API calls for fully warm cache.

---

### 9. Client Integration: Inline Check with Helper Methods
**Context**: TasksClient.get_async() always hits API. Cache infrastructure dormant. Need consistent pattern across all SDK clients.

**Decision**: Use inline check with `BaseClient` helper methods (`_cache_get`, `_cache_set`, `_cache_invalidate`). Check cache first, fetch on miss, store result.

**Pattern**:
```python
cached = self._cache_get(task_gid, EntryType.TASK)
if cached:
    return cached.data
# Fetch from API
data = await self._http.get(...)
self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)
```

**Rationale**:
- **Reusability**: Helpers used by TasksClient, ProjectsClient, SectionsClient, etc.
- **Encapsulation**: Error handling in helpers, not repeated
- **Visibility**: Cache check explicit in method body for code review

**Alternatives Rejected**: Decorator (loses `raw` parameter, complex), middleware (too coarse), AOP (uncommon in Python), separate cached client (doubles classes).

**Source ADRs**: ADR-0119, ADR-0124

**Impact**: Uniform caching pattern across SDK. Graceful degradation built into helpers.

---

### 10. Graceful Degradation: Logged Warning with Metric
**Context**: Cache operations can fail (Redis down, memory full, corrupt entry). SDK must continue functioning.

**Decision**: Catch all exceptions in cache helpers, log at WARNING level, increment error metric, return gracefully (None for get, no-op for set). No retries.

**Rationale**:
- **Resilience**: SDK works even when cache completely fails
- **Observability**: WARNING logs visible but not ERROR (cache is optional)
- **Simplicity**: No complex circuit breaker (providers handle transient failures)

**Alternatives Rejected**: Silent failure (invisible problems), raise to caller (breaks user code), ERROR level (overstates severity), metrics-only (loses debugging), circuit breaker (redundant with provider).

**Source ADRs**: ADR-0127

**Impact**: Cache failures never prevent operations. Clear visibility into cache health through logs and metrics.

---

### 11. Default Provider Selection: Environment-Aware Detection
**Context**: 4,000 lines of cache infrastructure dormant because `AsanaClient.__init__()` defaults to `NullCacheProvider`.

**Decision**: Environment-aware detection chain:
1. Explicit `cache_provider` parameter (highest priority)
2. `ASANA_CACHE_PROVIDER` environment variable
3. Auto-detect (production+REDIS_HOST → Redis, else InMemory)
4. InMemory fallback (default)

**Rationale**:
- **Zero-config**: Developers get InMemory cache automatically
- **Production-ready**: Auto-detects Redis in production
- **Backward compatible**: Explicit parameter unchanged
- **Graceful**: Missing Redis in production falls back to InMemory with warning

**Alternatives Rejected**: Static default (no environment awareness), env var only (requires config for every environment), auto-detect only (can't override), config file (over-engineered).

**Source ADRs**: ADR-0123

**Impact**: Cache enabled by default. 12-factor app compliant configuration.

---

### 12. Task Cache Population: Builder-Level Orchestration
**Context**: P1 cache optimization established two-phase lookup but cache was never populated because `list_async()` doesn't populate cache.

**Decision**: Populate Task cache at `ProjectDataFrameBuilder` level after `fetch_all()` completes, using `TaskCacheCoordinator.populate_tasks_async()`.

**Rationale**:
- **PRD compliance**: Prohibits modifying `TasksClient.list_async()`
- **Context**: Builder knows exact opt_fields needed for DataFrame
- **Consistency**: Follows P1 pattern where builder owns cache orchestration

**Alternatives Rejected**: Client-level (violates PRD), fetcher-level (wrong responsibility), wrapper client (over-engineered).

**Source ADRs**: ADR-0130, ADR-0140

**Impact**: Second DataFrame fetch uses cached tasks. Achieves <1s warm fetch.

---

### 13. Detection Result Caching: Inline Before Tier 4
**Context**: `detect_entity_type_async()` with Tier 4 (subtask inspection) makes 200ms API call every time. Hydration traverses hierarchy, calling detection repeatedly.

**Decision**: Cache check AFTER Tiers 1-3 (fast path), BEFORE Tier 4 execution. Extract cache from `client` parameter. Serialize with `asdict()`, inline logic (no coordinator).

**Rationale**:
- **No fast path regression**: Tiers 1-3 (O(1) operations) unchanged
- **40x speedup**: Tier 4 detection 200ms → <5ms on cache hit
- **Simplicity**: ~25 lines inline vs 50-line coordinator

**Alternatives Rejected**: Cache at entry (adds overhead to fast path), coordinator class (over-engineered), cache all tiers (no benefit for O(1) ops), new parameter (breaking change).

**Source ADRs**: ADR-0143

**Impact**: Hydration operations dramatically faster for repeated hierarchy traversal.

---

## Architecture Evolution Timeline

| Date | Decision | Phase | Impact |
|------|----------|-------|--------|
| 2025-12-09 | ADR-0016: Cache Protocol Extension | Foundation | Enables versioned operations, batch support |
| 2025-12-09 | ADR-0018: Batch Modification Checking | Foundation | 90% API reduction for staleness checks |
| 2025-12-09 | ADR-0019: Staleness Detection Algorithm | Foundation | STRICT vs EVENTUAL freshness modes |
| 2025-12-09 | ADR-0021: DataFrame Caching Strategy | Foundation | Per-task+project granularity |
| 2025-12-09 | ADR-0026: Two-Tier Architecture | Foundation | Redis + S3, 80% cost reduction |
| 2025-12-09 | ADR-0032: Cache Granularity | Foundation | Surgical invalidation, 99.9% hit rate |
| 2025-12-11 | ADR-0052: Bidirectional Reference Caching | Model | O(1) upward navigation |
| 2025-12-12 | ADR-0060: Name Resolution Caching | Clients | Per-session name→GID cache |
| 2025-12-16 | ADR-0072: Resolution Caching Decision | Clients | No caching (different semantics) |
| 2025-12-16 | ADR-0076: Auto-Invalidation Strategy | Model | Descriptor-triggered invalidation |
| 2025-12-22 | ADR-0123: Default Provider Selection | Integration | Environment-aware auto-detection |
| 2025-12-22 | ADR-0124: Client Cache Pattern | Integration | Inline check with BaseClient helpers |
| 2025-12-22 | ADR-0125: SaveSession Invalidation | Integration | Post-commit hook, multi-project aware |
| 2025-12-22 | ADR-0126: Entity-Type TTL Resolution | Integration | 60s-3600s based on entity volatility |
| 2025-12-22 | ADR-0127: Graceful Degradation | Integration | Logged warning, never fail operations |
| 2025-12-23 | ADR-0116: Batch Cache Population | Optimization | Check-fetch-populate for DataFrames |
| 2025-12-23 | ADR-0119: Client Cache Integration | Optimization | TasksClient, ProjectsClient caching |
| 2025-12-23 | ADR-0120: Bulk Fetch Population | Optimization | List operations warm cache |
| 2025-12-23 | ADR-0129: Stories Client Wiring | Optimization | New cached method (backward compatible) |
| 2025-12-23 | ADR-0130: Cache Population Location | Optimization | Builder-level orchestration |
| 2025-12-23 | ADR-0131: GID Enumeration Caching | Optimization | Two-tier section+enum, <1s warm fetch |
| 2025-12-23 | ADR-0137: Post-Commit Invalidation | Optimization | DataFrame cache invalidation hooks |
| 2025-12-23 | ADR-0140: DataFrame Task Cache | Optimization | Task-level cache in DataFrame path |
| 2025-12-23 | ADR-0143: Detection Result Caching | Optimization | Inline before Tier 4, 40x speedup |
| 2025-12-24 | ADR-0133: Progressive TTL Extension | Optimization | Exponential doubling, 79% reduction |

## Design Patterns

### 1. Cache-Aside with Promotion
Two-tier architecture uses cache-aside reads with automatic promotion from S3 to Redis on access. Writes are write-through to both tiers.

### 2. Graceful Degradation
All cache operations wrapped in try/except. Failures log warnings and continue. Cache is optimization, never critical path.

### 3. Batch Operations
Amortize overhead: `get_batch()` and `set_batch()` for bulk operations. Single call for 3,500 entries vs 3,500 individual calls.

### 4. Progressive TTL Extension
Exponential doubling (300s → 600s → 1200s → ... → 86400s) for repeatedly unchanged entities. Minimizes API calls for stable data.

### 5. Entity-Aware TTLs
Entity type detection at cache store time determines appropriate TTL. Business: 1h, Process: 1min, balancing freshness vs performance.

## Cross-References

**Related PRDs** (archived after consolidation):
- PRD-0002: Intelligent Caching (foundational requirements)
- PRD-CACHE-INTEGRATION: Client integration patterns
- PRD-CACHE-OPTIMIZATION-P2: DataFrame optimization
- PRD-CACHE-OPTIMIZATION-P3: GID enumeration caching
- PRD-CACHE-LIGHTWEIGHT-STALENESS: Progressive TTL
- PRD-WATERMARK-CACHE: DataFrame cache integration

**Related TDDs** (archived after consolidation):
- TDD-0008: Intelligent Caching (technical design)
- TDD-CACHE-INTEGRATION: Client integration implementation
- TDD-CACHE-OPTIMIZATION-P2: Task cache in DataFrame path
- TDD-CACHE-OPTIMIZATION-P3: GID enumeration implementation
- TDD-CACHE-LIGHTWEIGHT-STALENESS: Progressive TTL algorithm
- TDD-WATERMARK-CACHE: DataFrame cache technical design

**Related Summaries**:
- ADR-SUMMARY-SAVESESSION: Cache invalidation hooks, post-commit pattern
- ADR-SUMMARY-PERFORMANCE: Batch operations, parallel fetching
- ADR-SUMMARY-DATAFRAME: DataFrame extraction, struc caching

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0016 | Cache Protocol Extension | 2025-12-09 | Extensible provider with versioned methods |
| ADR-0018 | Batch Modification Checking | 2025-12-09 | 25-second in-memory TTL, 90% API reduction |
| ADR-0019 | Staleness Detection Algorithm | 2025-12-09 | STRICT vs EVENTUAL with `modified_at` |
| ADR-0021 | DataFrame Caching Strategy | 2025-12-09 | Per-task+project key `struc:{task}:{project}` |
| ADR-0026 | Two-Tier Cache Architecture | 2025-12-09 | Redis (hot) + S3 (cold), 80% cost reduction |
| ADR-0032 | Cache Granularity | 2025-12-09 | Per-task with project context for correctness |
| ADR-0052 | Bidirectional Reference Caching | 2025-12-11 | Cache upward refs with invalidation |
| ADR-0060 | Name Resolution Caching | 2025-12-12 | Per-SaveSession cache for name→GID |
| ADR-0072 | Resolution Caching Decision | 2025-12-16 | No caching (different semantics than navigation) |
| ADR-0076 | Auto-Invalidation Strategy | 2025-12-16 | Descriptor-triggered, auto-discovery via `__init_subclass__` |
| ADR-0116 | Batch Cache Population | 2025-12-23 | Check-fetch-populate pattern for DataFrames |
| ADR-0119 | Client Cache Integration | 2025-12-23 | Inline check with BaseClient helpers |
| ADR-0120 | Bulk Fetch Population | 2025-12-23 | List operations populate per-page |
| ADR-0123 | Default Provider Selection | 2025-12-22 | Environment-aware detection chain |
| ADR-0124 | Client Cache Pattern | 2025-12-22 | Standardized integration across clients |
| ADR-0125 | SaveSession Invalidation | 2025-12-22 | Post-commit hook with GID collection |
| ADR-0126 | Entity-Type TTL Resolution | 2025-12-22 | Config-driven with entity detection |
| ADR-0127 | Graceful Degradation | 2025-12-22 | Logged warning, never fail operations |
| ADR-0129 | Stories Client Wiring | 2025-12-23 | New `list_for_task_cached_async()` method |
| ADR-0130 | Cache Population Location | 2025-12-23 | Builder-level orchestration |
| ADR-0131 | GID Enumeration Caching | 2025-12-23 | Two-tier section+enum, fetcher-level |
| ADR-0133 | Progressive TTL Extension | 2025-12-24 | Exponential doubling 300s→86400s |
| ADR-0137 | Post-Commit Invalidation Hook | 2025-12-23 | DataFrame cache invalidation |
| ADR-0140 | DataFrame Task Cache | 2025-12-23 | Two-phase lookup at builder level |
| ADR-0143 | Detection Result Caching | 2025-12-23 | Inline before Tier 4, 40x speedup |

## Performance Impact Summary

**API Call Reduction**:
- Batch modification checking: 90% reduction (1,000 tasks: 10 calls instead of 1,000)
- Progressive TTL: 79% reduction for stable entities over 2-hour session
- GID enumeration: 100% reduction on warm cache (0 calls vs 35+)
- Detection caching: 95% reduction for repeated hierarchy traversal

**Latency Improvements**:
- Warm DataFrame fetch: 9.67s → <1s (10x speedup)
- Tier 4 detection: 200ms → <5ms (40x speedup)
- Cache-aside read: <2ms (Redis) or <10ms (promoted from S3)

**Cost Optimization**:
- Storage: $92/month → $25/month (73% reduction for 13GB)
- Scalability: Memory-bound → S3 scales to petabytes

## Migration Notes

For teams adopting this architecture:

1. **Enable caching gradually**: Use `ASANA_CACHE_S3_ENABLED=false` initially (Redis-only)
2. **Monitor metrics**: Track cache hit rates, error rates, TTL distribution
3. **Tune TTLs**: Start with defaults, adjust based on entity update patterns
4. **Invalidation hooks**: Ensure SaveSession integration for correctness
5. **S3 tier**: Enable after Redis stability confirmed

## Future Considerations

**Potential Enhancements**:
- Circuit breaker at SDK level (currently relies on provider implementation)
- Compression for large cache entries (>10KB)
- Cache warming API for predictable workloads
- Multi-region S3 replication for global deployments
- Cache entry versioning for schema evolution

**Known Limitations**:
- Progressive TTL resets on process restart (in-memory extension state)
- S3 tier not recommended for GID enumeration (too volatile)
- Name resolution cache cleared on SaveSession exit (no cross-session benefit)
- Detection caching requires client parameter (implicit coupling)
