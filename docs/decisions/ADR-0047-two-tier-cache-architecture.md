# ADR-0047: Two-Tier Cache Architecture (Redis + S3)

## Metadata
- **Status**: Accepted
- **Author**: Tech Writer (consolidation)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer, User
- **Consolidated From**: ADR-0026
- **Related**: reference/CACHE.md, ADR-0046 (Cache Protocol Extension)

## Context

Initial cache architecture used Redis as sole backend (ADR-0017). Production analysis revealed critical gaps:

**Durability Crisis**: Computed STRUC data requires hours of API calls to rebuild. Redis restarts meant complete cache loss and expensive reconstruction.

**Cost Inefficiency**: 13GB of cached data at $92/month ElastiCache pricing. Analysis showed 80% of data accessed infrequently but stored in expensive memory tier.

**Heterogeneous Access Patterns**:

| Data Type | Access Frequency | Change Frequency | Storage Cost |
|-----------|------------------|------------------|--------------|
| Modification timestamps | Very High | Constant | High |
| Active task metadata | High | Moderate | High |
| STRUC (computed) | Medium | Low | Should be low |
| Subtasks/Dependencies | Low | Very Low | Should be low |
| Project dataframes | Low (batch) | Low | Should be low |

User decision: "Option B - Refactor to Redis+S3 Now" over shipping Redis-only. Rationale: durability is mandatory, architecture correctness beats premature shipping.

## Decision

**Implement two-tier cache architecture with Redis as hot tier and S3 as cold tier, coordinated by `TieredCacheProvider`.**

### Architecture Overview

```
Application Layer
    └─> In-Memory (Process-Local)
         └─> ModificationCheckCache (25s TTL, already implemented)

    └─> TieredCacheProvider (implements CacheProvider protocol)
         ├─> RedisCacheProvider (Hot Tier)
         │    - Modification timestamps
         │    - Active metadata
         │    - Hot STRUC (promoted from S3)
         │    - TTL: 1-24h
         │    - Size: ~100MB
         │    - Cost: ~$25/month
         │
         └─> S3CacheProvider (Cold Tier)
              - Full task snapshots
              - STRUC (durable)
              - Subtasks/Dependencies
              - Project DataFrames
              - TTL: 7-30d
              - Size: 1GB+
              - Cost: ~$0.05/month
```

### Key Architectural Patterns

#### 1. Write Strategy: Write-Through to Both Tiers

```
set(key, entry_type, data)
    |
    +-> Write to Redis (hot, short TTL) - synchronous
    |
    +-> Async write to S3 (cold, long TTL, durable)
         |
         +-> If S3 fails -> Log warning, don't fail operation
```

**Rationale**: Write-through ensures durability. S3 always has latest data. Redis evictions or restarts don't cause data loss.

#### 2. Read Strategy: Cache-Aside with Promotion

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

**Rationale**: Hot data stays fast in Redis. Cold data in S3 automatically promotes on access, adapting to changing access patterns.

#### 3. Failure Mode: Graceful Degradation

- S3 write fails: Log warning, operation succeeds (Redis has data)
- S3 read fails: Treat as cache miss, proceed to API
- Redis fails: Fall back to S3 (slower but functional)
- Both fail: Full cache miss, direct to API

**Rationale**: Cache is optimization, not critical path. Availability over consistency.

#### 4. Feature Flag: Gradual Rollout

```python
ASANA_CACHE_S3_ENABLED=true/false  # Default: false
```

When disabled: `TieredCacheProvider` behaves as Redis-only. S3 operations are no-ops.

**Rationale**: Enables safe production rollout with instant rollback capability.

### Tier Placement

**Redis (Hot Tier)** - Fast, ephemeral:
- Modification timestamps (existing in-memory, 25s TTL)
- Active task metadata (1h TTL)
- Rate limit counters (1m TTL)
- Recently accessed STRUC (promoted from S3, 1h TTL)

**S3 (Cold Tier)** - Durable, cheap:
- Full task snapshots (7d TTL)
- All STRUC data (30d TTL) - promoted to Redis on access
- Subtasks, dependencies (30d TTL)
- Project dataframes (24h TTL)
- Stories, attachments (7d TTL)

### Storage Structure

S3 key structure:
```
s3://{bucket}/asana-cache/
    tasks/{gid}.json.gz
    subtasks/{gid}.json.gz
    dependencies/{gid}.json.gz
    struc/{task_gid}/{project_gid}.json.gz
    dataframes/{project_gid}/{type}.parquet.gz
```

Compression: Gzip for objects > 1KB (reduces storage and transfer costs, negligible CPU overhead).

## Rationale

### Why Two Tiers Over Redis-Only?

| Factor | Redis-Only | Two-Tier |
|--------|-----------|----------|
| Durability | None (ephemeral) | S3 survives restarts |
| Cost (13GB) | ~$92/month | ~$25/month |
| Rebuild time | Hours (API calls) | Minutes (S3 restore) |
| Complexity | Low | Medium |
| User requirement | Acceptable risk | Durability mandatory |

User explicitly prioritized durability over simplicity.

### Why Write-Through Over Write-Back?

- Write-back: Better write performance, data loss risk on failure
- Write-through: Slightly slower writes, guaranteed durability

For cache operations with sub-10ms Redis writes, additional async S3 write adds minimal latency while ensuring durability.

### Why Cache-Aside Over Read-Through?

- Read-through: Cache always has data, complex invalidation
- Cache-aside: Explicit control, simpler reasoning, natural promotion

Cache-aside matches existing `CacheProvider` semantics and is easier to reason about.

## Alternatives Considered

### Alternative 1: Keep Redis-Only
**Rejected**: No durability (STRUC lost on restart), higher cost, user explicitly rejected.

### Alternative 2: S3-Only
**Rejected**: 50-200ms latency fails NFR-PERF-002, regression from working Redis implementation.

### Alternative 3: Redis with RDB/AOF Persistence
**Rejected**: Doesn't reduce memory costs. Persistence doesn't equal durability (single-node failure). S3 more durable.

### Alternative 4: DynamoDB as Cold Tier
**Rejected**: More expensive than S3 for cold data storage. Latency advantage irrelevant for infrequent access.

### Alternative 5: Redis Cluster with Replication
**Rejected**: Cost prohibitive (2-3x for replicas). Still memory-bound pricing. Doesn't address heterogeneous access patterns.

## Consequences

### Positive
- 80-90% cost reduction ($92/month → $25/month for 13GB)
- STRUC and computed data survive Redis restarts
- Scale headroom: S3 scales to petabytes without memory ceiling
- Graceful degradation: S3 failures don't break Redis operations
- Natural tiering: Hot data stays fast, cold data stays cheap
- Feature flag enables safe rollout with instant rollback
- Both providers implement existing `CacheProvider` protocol

### Negative
- Added complexity: Two tiers to understand, monitor, debug
- New infrastructure: S3 bucket configuration, IAM policies required
- Cache coherence challenges: Two sources of truth during promotion
- Latency variance: S3 misses add 50-200ms (cold data only)
- Testing complexity: Need to test Redis-only, S3-only, and combined paths

### Neutral
- Migration from Redis-only: Feature flag makes backward compatible
- S3 eventual consistency: Acceptable for cache (not source of truth)
- Compression CPU overhead: Negligible for cache-sized objects

## Impact

Production metrics after rollout:
- API call reduction: 79% for stable entities over 2-hour sessions
- Warm DataFrame fetch latency: 9.67s → <1s (10x improvement)
- Storage cost: 73% reduction
- Durability: STRUC rebuild time from hours to minutes

## Compliance

**Enforcement mechanisms**:
1. Code review: New cache operations use `TieredCacheProvider`
2. Testing: Unit tests for S3CacheProvider (mocked boto3), integration tests with localstack
3. Monitoring: Tier hit/miss ratios, promotion counts, S3 operation latencies
4. Operations: S3 bucket lifecycle policies, IAM minimal permissions, CloudWatch alarms

**Configuration**:
```python
@dataclass
class TieredCacheConfig:
    s3_enabled: bool = False
    s3_bucket: str = "asana-cache"
    s3_prefix: str = "cache/"
    compression_threshold: int = 1024  # bytes
    redis_task_ttl: int = 3600         # 1 hour
    s3_struc_ttl: int = 2592000        # 30 days
```
