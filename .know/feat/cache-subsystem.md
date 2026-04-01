---
domain: feat/cache-subsystem
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/cache/**/*.py"
  - "./src/autom8_asana/protocols/cache.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.83
format_version: "1.0"
---

# Multi-Tier Intelligent Cache Subsystem

## Purpose and Design Rationale

The cache subsystem reduces Asana API call volume 90%+ for stable workloads. Its design contract: cache failures must degrade gracefully, never cause 500s or data loss.

Two distinct caching surfaces: **Entity cache** (individual task/project/section by GID, versioned by `modified_at`) and **DataFrame cache** (computed Polars DataFrames by `(entity_type, project_gid)`, versioned by watermark).

Default freshness: `FreshnessIntent.EVENTUAL` (Stale-While-Revalidate). Progressive TTL extension doubles TTL on each successful `modified_at` comparison, up to 24h ceiling (ADR-0133).

## Conceptual Model

### Three-Tier Stack

Tier 0: Models (CacheEntry, FreshnessIntent/State, CacheSettings, CacheMetrics)
Tier 1: Policies (FreshnessPolicy, HierarchyIndex, LightweightChecker, RequestCoalescer)
Tier 2: Providers (EnhancedInMemory, Redis, S3, Tiered, UnifiedTaskStore)
Tier 3: Integration (Factory, DataFrameCache, MutationInvalidator, FreshnessCoordinator, StalenessCheckCoordinator)

### Provider Selection Chain (4-step)

1. `config.enabled=False` -> NullCacheProvider
2. `config.provider` explicit -> exact provider
3. `AUTOM8Y_ENV=production` + `REDIS_HOST` -> Redis
4. Fallback -> EnhancedInMemory

### Entity-Type TTLs

Business 3600s, Unit/Contact 900s, Offer 180s, Process 60s, Stories 600s, DataFrame 300s, PROJECT_SECTIONS 1800s.

## Implementation Map

52+ files across: backends/ (base, memory, redis, s3), providers/ (tiered, unified), dataframe/ (build_coordinator, coalescer, circuit_breaker, warmer, factory, tiers/memory, tiers/progressive), integration/ (factory, dataframe_cache, mutation_invalidator, freshness_coordinator, staleness_coordinator, hierarchy_warmer, schema_providers, autom8_adapter, stories, derived, dataframes, batch, loader, upgrader), models/ (entry, freshness_unified, completeness, metrics, settings), policies/ (freshness_policy, staleness, hierarchy, coalescer, lightweight_checker).

### Active Design Tensions

- **TENSION-001**: Dual cache providers (legacy + unified), migration incomplete
- **TENSION-002**: Dual preload strategy (progressive + legacy fallback)
- **TENSION-008**: Freshness enum type aliases for backward compat

## Boundaries and Failure Modes

- Single shared CacheProvider at `app.state` is load-bearing (SCAR-004)
- S3 `NoSuchKey` must not feed circuit breaker (SCAR-S3-LOOP)
- MutationInvalidator fires both entity and DataFrame invalidation paths
- DataFrame BuildCoordinator uses asyncio.Future for thundering-herd prevention
- Per-project circuit breaker (3 failures -> open, 60s reset)

## Knowledge Gaps

1. Several integration layer files not read in detail (loader, batch, upgrader, stories, derived).
2. Soft invalidation production posture undocumented.
3. DataFrame SWR rebuild failure handling not confirmed.
