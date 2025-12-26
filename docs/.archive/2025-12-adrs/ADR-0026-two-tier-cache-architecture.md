# ADR-0026: Two-Tier Cache Architecture (Redis + S3)

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, User
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [ADR-0017](ADR-0017-redis-backend-architecture.md) (superseded for S3 aspect)

## Context

ADR-0017 established Redis as the sole cache backend. After production analysis and user feedback, this decision is being revised to add an S3 cold tier. This ADR documents the architecture pivot from Redis-only to a full two-tier caching system.

**Current State**:
- Redis backend fully implemented (`src/autom8_asana/cache/backends/redis.py`)
- 328 tests passing, production-ready
- Implements `CacheProvider` protocol with versioned operations

**Why the Pivot**:

1. **Durability is critical**: User operations depend on cached data surviving Redis restarts. Computed STRUC data is expensive to rebuild (multiple API calls per task). Redis is ephemeral; S3 is durable.

2. **Cost analysis reveals inefficiency**:
   | Tier | Estimated Size | Monthly Cost |
   |------|----------------|--------------|
   | Redis (current) | 13GB | ~$92 (ElastiCache) |
   | S3 (proposed cold) | 1GB | ~$0.03 |

   80%+ of data is accessed infrequently but stored in expensive memory tier.

3. **Heterogeneous access patterns**: Data types have vastly different access frequencies:

   | Data Type | Access Frequency | Change Frequency | Ideal Tier |
   |-----------|-----------------|------------------|------------|
   | Modification timestamps | Very High (every check) | Constant | Redis |
   | Active task metadata | High | Moderate | Redis |
   | STRUC (computed) | Medium | Low | S3 -> Redis on access |
   | Subtasks/Dependencies | Low | Very Low | S3 only |
   | Project dataframes | Low (batch) | Low | S3 only |

4. **User decision**: After architectural review, user explicitly chose "Option B: Refactor to Redis+S3 Now" over shipping Redis-only. Rationale: durability is mandatory, there is time to get architecture right, correct architecture now beats premature shipping.

## Decision

**Implement a two-tier cache architecture with Redis as the hot tier and S3 as the cold tier, coordinated by a new `TieredCacheProvider`.**

### Architecture Overview

```
+---------------------------------------------------------------------+
|                          APPLICATION                                  |
|                                                                      |
|  +----------------------------------------------------------------+  |
|  |              In-Memory (Process-Local)                          |  |
|  |                                                                 |  |
|  |  - ModificationCheckCache (25s TTL) - Already implemented       |  |
|  |  - LRU for ultra-hot data                                       |  |
|  +----------------------------------------------------------------+  |
|                               |                                      |
+-------------------------------+--------------------------------------+
                                |
                                v
+---------------------------------------------------------------------+
|                     TieredCacheProvider                               |
|                  (implements CacheProvider)                           |
|                                                                      |
|   +-----------------------+         +-----------------------+        |
|   |   RedisCacheProvider  |         |   S3CacheProvider     |        |
|   |     (Hot Tier)        |<------->|    (Cold Tier)        |        |
|   |                       | promote |                       |        |
|   | - Mod timestamps      |         | - Full task data      |        |
|   | - Active metadata     |         | - STRUC (durable)     |        |
|   | - Hot STRUC           |         | - Subtasks            |        |
|   | - Coordination        |         | - Dependencies        |        |
|   |                       |         | - Project DFs         |        |
|   | TTL: 1-24h            |         | TTL: 7-30d            |        |
|   | Size: ~100MB          |         | Size: 1GB+            |        |
|   | Cost: ~$25/mo         |         | Cost: ~$0.05/mo       |        |
|   +-----------------------+         +-----------------------+        |
|                                                                      |
+---------------------------------------------------------------------+
```

### Key Architectural Decisions

#### 1. Write Strategy: Write-Through to Both Tiers

All writes go to both Redis and S3:

```
set(key, entry_type, data)
    |
    +-> Write to Redis (hot, short TTL)
    |
    +-> Async write to S3 (cold, long TTL, durable)
            |
            +-> If S3 fails -> Log warning, don't fail operation
```

**Rationale**: Write-through ensures durability. S3 always has the latest data. If Redis evicts or restarts, S3 provides recovery.

#### 2. Read Strategy: Cache-Aside with Promotion

Reads check Redis first, fall back to S3, and promote on hit:

```
get(key, entry_type)
    |
    +-> Check Redis
            |
            +-> HIT -> Return (fast path)
            |
            +-> MISS -> Check S3
                    |
                    +-> HIT -> Promote to Redis, Return
                    |
                    +-> MISS -> Return None (caller fetches from API)
```

**Rationale**: Hot data stays fast (Redis). Cold data in S3 is promoted to Redis on access, automatically adapting to access patterns.

#### 3. Failure Mode: Graceful Degradation

S3 failures do not break Redis operations:

- **S3 write fails**: Log warning, operation succeeds (Redis has data)
- **S3 read fails**: Treat as cache miss, proceed to API
- **Redis fails**: Fall back to S3 (slower but functional)
- **Both fail**: Full cache miss, direct to API

**Rationale**: Cache is optimization, not critical path. Availability over consistency.

#### 4. Feature Flag: Gradual Rollout

```python
ASANA_CACHE_S3_ENABLED=true/false  # Default: false
```

When disabled:
- `TieredCacheProvider` behaves as Redis-only
- S3 operations are no-ops
- No behavior change from current implementation

**Rationale**: Enables safe production rollout. If issues arise, disable S3 tier without code changes.

#### 5. Compression: Gzip for Large Objects

```python
# Objects > 1KB are gzip compressed before S3 storage
COMPRESSION_THRESHOLD = 1024  # bytes
```

- Reduces S3 storage costs
- Reduces S3 transfer costs
- Negligible CPU overhead for cache operations
- Redis stores uncompressed (latency-sensitive)

#### 6. TTL Strategy

| Tier | Data Type | TTL | Rationale |
|------|-----------|-----|-----------|
| Redis | Modification timestamps | 25s | Existing in-memory cache |
| Redis | Active task metadata | 1h | Frequently accessed |
| Redis | Promoted STRUC | 1h | Temporarily hot |
| Redis | Rate limit counters | 1m | Coordination data |
| S3 | Full task snapshots | 7d | Recovery buffer |
| S3 | STRUC | 30d | Expensive to compute |
| S3 | Subtasks/Dependencies | 30d | Stable data |
| S3 | Project dataframes | 24h | Batch computation |

### Tier Placement

**Redis (Hot Tier)** - Fast, ephemeral:
- Modification timestamps (already in-memory, 25s TTL)
- Active task metadata (1h TTL)
- Rate limit counters (1m TTL)
- Recently accessed STRUC (promoted from S3, 1h TTL)

**S3 (Cold Tier)** - Durable, cheap:
- Full task snapshots (7d TTL)
- All STRUC data (30d TTL) - promoted to Redis on access
- Subtasks, dependencies (30d TTL)
- Project dataframes (24h TTL)
- Stories, attachments (7d TTL)

### Component Design

#### S3CacheProvider

New class implementing `CacheProvider` protocol:

```python
class S3CacheProvider(CacheProvider):
    """S3-backed cache for cold/durable data storage."""

    # Key structure: s3://{bucket}/asana-cache/{entry_type}/{gid}.json.gz
    # Version tracking via S3 object metadata (x-amz-meta-version)
    # Gzip compression for objects > 1KB
```

**Key structure**:
```
s3://{bucket}/asana-cache/
    tasks/{gid}.json.gz
    subtasks/{gid}.json.gz
    dependencies/{gid}.json.gz
    dependents/{gid}.json.gz
    stories/{gid}.json.gz
    attachments/{gid}.json.gz
    struc/{task_gid}/{project_gid}.json.gz
    dataframes/{project_gid}/{type}.parquet.gz
```

#### TieredCacheProvider

Coordinator implementing `CacheProvider` protocol:

```python
class TieredCacheProvider(CacheProvider):
    """Coordinates Redis (hot) + S3 (cold) tiers."""

    def __init__(
        self,
        redis: RedisCacheProvider,
        s3: S3CacheProvider,
        s3_enabled: bool = False,  # Feature flag
    ):
        self._hot = redis
        self._cold = s3
        self._s3_enabled = s3_enabled
```

### Configuration

```python
@dataclass
class TieredCacheConfig:
    """Configuration for two-tier cache."""

    # Feature flag
    s3_enabled: bool = False

    # S3 configuration
    s3_bucket: str = "asana-cache"
    s3_prefix: str = "cache/"
    s3_region: str = "us-east-1"

    # Compression
    compression_threshold: int = 1024  # bytes

    # TTLs (seconds)
    redis_task_ttl: int = 3600        # 1 hour
    redis_promoted_ttl: int = 3600    # 1 hour
    s3_task_ttl: int = 604800         # 7 days
    s3_struc_ttl: int = 2592000       # 30 days
    s3_dataframe_ttl: int = 86400     # 24 hours

    # Promotion
    promote_on_access: bool = True
```

### Invalidation Strategy

```
invalidate(key, entry_type)
    |
    +-> Delete from Redis
    |
    +-> Delete from S3 (or version bump)
```

Both tiers invalidated together to maintain consistency. S3 deletion is async; Redis deletion is sync.

## Rationale

**Why two tiers over Redis-only (ADR-0017)?**

ADR-0017 chose Redis-only for simplicity. New information changes the calculus:

| Factor | Redis-Only (ADR-0017) | Two-Tier (This ADR) |
|--------|----------------------|---------------------|
| Durability | None (ephemeral) | S3 survives restarts |
| Cost (13GB) | ~$92/month | ~$25/month |
| Rebuild time | Hours (API calls) | Minutes (S3 restore) |
| Complexity | Low | Medium |
| User requirement | Acceptable risk | Durability mandatory |

User explicitly prioritized durability over simplicity.

**Why write-through over write-back?**

- Write-back: Better write performance, but data loss risk on failure
- Write-through: Slightly slower writes, but guaranteed durability

For cache operations with sub-10ms Redis writes, the additional S3 write (async) adds minimal latency to the caller while ensuring durability.

**Why cache-aside with promotion over read-through?**

- Read-through: Cache always has data, complex invalidation
- Cache-aside: Explicit control, simpler reasoning, natural promotion

Cache-aside matches existing `CacheProvider` semantics and is simpler to reason about.

**Why feature flag?**

S3 tier is additive complexity. Feature flag enables:
- Safe production rollout
- Quick rollback without deployment
- A/B testing of performance impact
- Gradual migration from Redis-only

## Alternatives Considered

### Alternative 1: Keep Redis-Only (ADR-0017 Status Quo)

- **Description**: Don't add S3 tier. Accept Redis ephemeral nature.
- **Pros**:
  - No additional complexity
  - Implementation complete
  - Team familiarity
- **Cons**:
  - No durability (STRUC lost on restart)
  - Higher cost ($92/month vs $25/month)
  - User explicitly rejected
- **Why not chosen**: User requirement for durability cannot be met.

### Alternative 2: S3-Only (Revert to Legacy)

- **Description**: Replace Redis with S3-only backend like legacy autom8.
- **Pros**:
  - Durability
  - Lower cost
  - Simpler (one tier)
- **Cons**:
  - 50-200ms latency (fails NFR-PERF-002)
  - No atomic operations
  - No native TTL
  - Regression from current implementation
- **Why not chosen**: Fails latency requirements. Would throw away working Redis implementation.

### Alternative 3: Redis with RDB/AOF Persistence

- **Description**: Enable Redis persistence (RDB snapshots or AOF log).
- **Pros**:
  - Single tier
  - Data survives restarts
  - Team familiarity
- **Cons**:
  - RDB: Point-in-time snapshots, data loss window
  - AOF: Performance impact, still single-node bound
  - Both: Doesn't reduce memory costs
  - ElastiCache persistence adds complexity
- **Why not chosen**: Doesn't address cost issue. Persistence != durable (single-node failure still loses data). S3 is more durable.

### Alternative 4: DynamoDB as Cold Tier

- **Description**: Use DynamoDB instead of S3 for cold tier.
- **Pros**:
  - Lower latency than S3 (single-digit ms)
  - Native TTL
  - Managed service
- **Cons**:
  - More expensive than S3 for storage
  - More complex API than S3
  - Overkill for cold data
  - No advantage over S3 for infrequent access
- **Why not chosen**: S3 is cheaper and sufficient for cold data access patterns. DynamoDB's latency advantage irrelevant for data accessed hourly/daily.

### Alternative 5: Redis Cluster with Replication

- **Description**: Multi-node Redis cluster for durability.
- **Pros**:
  - Data replicated across nodes
  - Survives single-node failure
  - Fast failover
- **Cons**:
  - Much higher cost (2-3x for replicas)
  - Still memory-bound pricing
  - Operational complexity
  - Doesn't address heterogeneous access patterns
- **Why not chosen**: Cost prohibitive. Paying 3x memory prices for cold data that should be in S3.

## Consequences

### Positive

- **Durability achieved**: STRUC and computed data survive Redis restarts via S3
- **80-90% cost reduction**: ~$25/month vs ~$92/month for 13GB equivalent
- **Scale headroom**: S3 scales to petabytes; no memory ceiling
- **Graceful degradation**: S3 failures don't break Redis operations
- **Natural tiering**: Hot data stays fast, cold data stays cheap
- **Feature flag safety**: Gradual rollout with instant rollback
- **Protocol compatibility**: Both new providers implement existing `CacheProvider`

### Negative

- **Added complexity**: Two tiers to understand, monitor, debug
- **New infrastructure**: S3 bucket configuration, IAM policies
- **Cache coherence challenges**: Two sources of truth during promotion
- **Latency variance**: S3 misses add 50-200ms (but only for cold data)
- **Testing complexity**: Need to test Redis-only, S3-only, and combined paths

### Neutral

- **Migration from Redis-only**: Feature flag makes this backward compatible
- **S3 eventual consistency**: Acceptable for cache (not source of truth)
- **Compression CPU**: Negligible for cache-sized objects

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| S3 latency impacts user experience | Medium | Low | Only cold data in S3; hot path stays in Redis |
| Cache coherence bugs | High | Medium | Comprehensive integration tests; feature flag for rollback |
| S3 costs unexpectedly high | Low | Low | Monitor PUT/GET request costs; adjust TTLs if needed |
| Complexity slows debugging | Medium | Medium | Clear logging; tier-aware metrics; runbook |
| S3 outage during high load | Medium | Very Low | Graceful degradation; Redis continues functioning |

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - New cache operations use `TieredCacheProvider`
   - Direct `S3CacheProvider` usage only in tiered coordinator
   - Feature flag respected for S3 operations
   - Async S3 writes don't block callers

2. **Testing requirements**:
   - Unit tests for S3CacheProvider (mocked boto3)
   - Unit tests for TieredCacheProvider (mocked Redis + S3)
   - Integration tests with localstack S3
   - Feature flag behavior tests (enabled/disabled)

3. **Monitoring requirements**:
   - Tier hit/miss ratios (Redis vs S3 vs total miss)
   - Promotion count (S3 -> Redis)
   - S3 operation latencies
   - S3 error rates (for graceful degradation verification)

4. **Operational requirements**:
   - S3 bucket with lifecycle policies matching TTLs
   - IAM role with minimal S3 permissions
   - CloudWatch alarms for S3 errors
   - Runbook for cache debugging

## Implementation Notes

**Estimated effort**:

| Component | Lines of Code | Time |
|-----------|---------------|------|
| S3CacheProvider | ~500 | 4-6 hours |
| TieredCacheProvider | ~400 | 4-6 hours |
| Configuration | ~100 | 1-2 hours |
| Tests | ~600 | 4-6 hours |
| Integration | ~200 | 2-4 hours |
| **Total** | ~1,800 | **2-3 days** |

**Files to create**:
- `src/autom8_asana/cache/backends/s3.py` - S3CacheProvider
- `src/autom8_asana/cache/tiered.py` - TieredCacheProvider
- `tests/unit/cache/test_s3_backend.py`
- `tests/unit/cache/test_tiered.py`

**Files to modify**:
- `src/autom8_asana/cache/__init__.py` - Add exports
- `src/autom8_asana/cache/config.py` - Add tiered configuration
