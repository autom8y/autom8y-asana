# ADR-0030: Cache Infrastructure

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0017, ADR-0024, ADR-0026
- **Related**: TDD-0008 (Intelligent Caching), PRD-0002 (Intelligent Caching)

## Context

The autom8_asana system requires high-performance caching to meet stringent latency requirements while maintaining durability for expensive computed data. The cache infrastructure must handle:

- **Performance**: <5ms p99 read latency, <10ms p99 write latency
- **Concurrency**: Thread-safe operations across multi-threaded servers and ECS tasks
- **Durability**: Computed STRUC data must survive Redis restarts
- **Cost efficiency**: 80%+ of data accessed infrequently but valuable
- **Atomic operations**: Version tracking without race conditions

Legacy S3-backed caching served well but has 50-200ms latency, no native TTL support, and no atomic operations.

## Decision

We implement a **three-tier cache infrastructure** with Redis (hot tier), S3 (cold tier), and coordinated two-tier access using optimistic locking for atomicity.

### 1. Redis Backend Architecture

**Use Redis as the hot-tier cache with structured keys and connection pooling.**

**Key structure**:
```
# Task data by entry type
asana:tasks:{gid}:task          -> JSON (full task data)
asana:tasks:{gid}:subtasks      -> JSON array
asana:tasks:{gid}:dependencies  -> JSON array
asana:tasks:{gid}:stories       -> JSON array

# Struc with project context
asana:struc:{task_gid}:{project_gid} -> JSON (computed structural data)

# Version tracking (Redis HASH per task for atomic access)
asana:tasks:{gid}:_meta
    task          -> ISO timestamp (modified_at)
    subtasks      -> ISO timestamp
    dependencies  -> ISO timestamp
    stories       -> ISO timestamp (last_story_at)
    cached_at     -> ISO timestamp
```

**Connection configuration**:
```python
@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = True  # TLS enabled by default
    socket_timeout: float = 1.0  # 1s operation timeout
    socket_connect_timeout: float = 5.0  # 5s connect timeout
    max_connections: int = 10  # Pool size
    retry_on_timeout: bool = True
    health_check_interval: int = 30  # seconds
```

**Rationale**: Redis provides sub-5ms latency (vs S3's 50-200ms), native TTL support, atomic operations via WATCH/MULTI, and efficient batch operations. Using HASH for metadata allows atomic read of all entry type versions in one command (`HGETALL`). Separate keys per entry type enable independent TTL and selective invalidation.

### 2. Thread Safety via Optimistic Locking

**Use Redis WATCH/MULTI for atomic cache updates and per-operation connections from pool.**

**WATCH/MULTI pattern for read-modify-write**:
```python
class RedisCacheProvider:
    """Thread-safe Redis cache provider using connection pooling."""

    def __init__(self, config: RedisConfig) -> None:
        self._pool = redis.ConnectionPool(
            host=config.host,
            port=config.port,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            ssl=config.ssl,
        )

    def _get_connection(self) -> redis.Redis:
        """Get a connection from the pool for this operation."""
        return redis.Redis(connection_pool=self._pool)

    async def update_versioned_atomic(
        self,
        key: str,
        entry_type: EntryType,
        update_fn: Callable[[CacheEntry | None], CacheEntry],
        max_retries: int = 3,
    ) -> CacheEntry:
        """Atomically update a cache entry using optimistic locking."""
        redis_key = self._make_key(key, entry_type)

        for attempt in range(max_retries):
            conn = self._get_connection()
            try:
                # WATCH the key for changes
                conn.watch(redis_key)

                # Read current value
                current_data = conn.hgetall(redis_key)
                current_entry = self._deserialize(current_data) if current_data else None

                # Apply update function
                new_entry = update_fn(current_entry)

                # Start transaction
                pipe = conn.pipeline()
                pipe.hset(redis_key, mapping=self._serialize(new_entry))
                if new_entry.ttl:
                    pipe.expire(redis_key, new_entry.ttl)

                # Execute transaction
                pipe.execute()
                return new_entry

            except redis.WatchError:
                # Another client modified the key, retry
                if attempt < max_retries - 1:
                    continue
                raise ConcurrentModificationError(
                    f"Failed to update {redis_key} after {max_retries} attempts"
                )
            finally:
                conn.close()
```

**In-memory cache thread safety**:
```python
from threading import Lock

class BatchModificationChecker:
    """Thread-safe batch modification checker."""

    def __init__(self) -> None:
        self._check_cache: dict[str, tuple[datetime, bool]] = {}
        self._lock = Lock()

    def _is_recently_checked(self, gid: str) -> bool:
        """Thread-safe check for recent modification check."""
        with self._lock:
            if gid not in self._check_cache:
                return False
            checked_at, _ = self._check_cache[gid]
            elapsed = (datetime.utcnow() - checked_at).total_seconds()
            if elapsed > self._ttl:
                del self._check_cache[gid]
                return False
            return True
```

**Rationale**: WATCH/MULTI provides optimistic locking across all clients (ECS tasks, processes). Connection pooling enables concurrent operations without the overhead of creating connections per operation. Threading.Lock is sufficient for process-local in-memory caches.

**Why WATCH/MULTI over client-side locking**: Client-side locks (`threading.Lock`) only work within a single process. Redis WATCH/MULTI provides optimistic locking across all clients, enabling safe concurrent access from multiple ECS tasks and Lambda invocations.

### 3. Two-Tier Cache Architecture

**Implement Redis (hot) + S3 (cold) coordinated by `TieredCacheProvider`.**

**Architecture overview**:
```
+----------------------------------------------------------------------+
|                     TieredCacheProvider                              |
|                  (implements CacheProvider)                          |
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
+----------------------------------------------------------------------+
```

**Write strategy**: Write-through to both tiers
```
set(key, entry_type, data)
    |
    +-> Write to Redis (hot, short TTL)
    |
    +-> Async write to S3 (cold, long TTL, durable)
            |
            +-> If S3 fails -> Log warning, don't fail operation
```

**Read strategy**: Cache-aside with promotion
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

**Failure mode**: Graceful degradation
- S3 write fails: Log warning, operation succeeds (Redis has data)
- S3 read fails: Treat as cache miss, proceed to API
- Redis fails: Fall back to S3 (slower but functional)
- Both fail: Full cache miss, direct to API

**Feature flag**: `ASANA_CACHE_S3_ENABLED=true/false` (default: false)
- When disabled, `TieredCacheProvider` behaves as Redis-only
- No behavior change from current implementation
- Safe production rollout with instant rollback

**TTL strategy**:

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

**Rationale**:
- **Durability is mandatory**: User operations depend on cached data surviving Redis restarts. Computed STRUC data is expensive to rebuild (multiple API calls per task).
- **Cost efficiency**: ~$25/month vs ~$92/month for Redis-only (80-90% reduction). 80%+ of data is accessed infrequently but stored in expensive memory tier.
- **Heterogeneous access patterns**: Modification timestamps accessed constantly; STRUC accessed periodically; subtasks rarely. Different tiers optimize for different patterns.
- **Write-through ensures durability**: S3 always has the latest data. If Redis evicts or restarts, S3 provides recovery.
- **Cache-aside with promotion**: Hot data stays fast (Redis). Cold data in S3 is promoted to Redis on access, automatically adapting to access patterns.

## Consequences

### Positive

**Redis Backend**:
- Sub-5ms read latency meets NFR-PERF-002
- Atomic operations prevent race conditions
- Native TTL simplifies expiration logic
- Batch efficiency via MGET and pipelining
- Operational familiarity (team knows Redis/ElastiCache)
- Valkey compatible (AWS ElastiCache Valkey works identically)

**Thread Safety**:
- Race-free updates via WATCH/MULTI
- Cross-process safety across ECS tasks and Lambda invocations
- Efficient connection pooling
- Retry on conflict recovers from contention

**Two-Tier Architecture**:
- Durability achieved (STRUC survives Redis restarts)
- 80-90% cost reduction (~$25/month vs ~$92/month)
- Scale headroom (S3 scales to petabytes)
- Graceful degradation (S3 failures don't break Redis)
- Natural tiering (hot data fast, cold data cheap)
- Feature flag safety (gradual rollout with instant rollback)

### Negative

**Redis Backend**:
- New infrastructure required (ElastiCache cluster)
- S3 cache data abandoned (no migration path, big-bang cutover)
- Memory costs higher than S3 for equivalent data
- Single point of failure (mitigated by graceful degradation)
- Breaking change from legacy (existing S3 cache consumers must migrate)

**Thread Safety**:
- Retry overhead on conflicts (rare in practice)
- Pool sizing tuning required (max_connections for workload)
- Connection per operation (slightly higher connection churn)
- Lock contention possible for in-memory caches

**Two-Tier Architecture**:
- Added complexity (two tiers to understand, monitor, debug)
- New infrastructure (S3 bucket configuration, IAM policies)
- Cache coherence challenges during promotion
- Latency variance (S3 misses add 50-200ms for cold data)
- Testing complexity (Redis-only, S3-only, and combined paths)

### Neutral

**Redis Backend**:
- Redis cluster mode optional (single-node sufficient for typical workloads)
- Encryption at rest delegated to ElastiCache configuration
- Persistence (Redis RDB/AOF) optional, not required for caching

**Thread Safety**:
- max_retries configurable (default 3 retries for WATCH conflicts)
- Pool managed by redis-py (standard library handles lifecycle)
- Error on max retries (raises ConcurrentModificationError)

**Two-Tier Architecture**:
- Discovery only runs once per process lifetime (projects are stable)
- S3 eventual consistency acceptable for cache (not source of truth)
- Compression CPU negligible for cache-sized objects

## Implementation Notes

### Redis Operations Mapping

| SDK Operation | Redis Commands |
|---------------|----------------|
| `get_versioned(key, TASK)` | `HGETALL asana:tasks:{key}:task` |
| `set_versioned(key, entry)` | `HSET asana:tasks:{key}:{type} ...` + `EXPIRE` |
| `get_batch(keys, type)` | `MGET` or pipelined `HGETALL` |
| `set_batch(entries)` | `PIPELINE` with multiple `HSET` + `EXPIRE` |
| `check_freshness(key, type, version)` | `HGET asana:tasks:{key}:_meta {type}` |
| `invalidate(key, types)` | `DEL` keys or `HDEL` from meta |
| `is_healthy()` | `PING` |

### S3 Key Structure

```
s3://{bucket}/asana-cache/
    tasks/{gid}.json.gz
    subtasks/{gid}.json.gz
    dependencies/{gid}.json.gz
    struc/{task_gid}/{project_gid}.json.gz
    dataframes/{project_gid}/{type}.parquet.gz
```

### Compression

Objects > 1KB are gzip compressed before S3 storage:
```python
COMPRESSION_THRESHOLD = 1024  # bytes
```
- Reduces S3 storage costs
- Reduces S3 transfer costs
- Negligible CPU overhead for cache operations
- Redis stores uncompressed (latency-sensitive)

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

## Compliance

### Infrastructure Checklist
- ElastiCache Redis/Valkey cluster provisioned before deployment
- TLS enabled on cluster
- AUTH password configured and securely stored
- S3 bucket with lifecycle policies matching TTLs
- IAM role with minimal S3 permissions

### Code Review Checklist
- Read-modify-write operations use WATCH/MULTI
- Simple writes use pipelined HSET + EXPIRE
- In-memory caches use threading.Lock
- Connections obtained from pool, not created directly
- New cache operations use `TieredCacheProvider`
- Direct `S3CacheProvider` usage only in tiered coordinator
- Feature flag respected for S3 operations
- Async S3 writes don't block callers

### Testing Requirements
- Integration tests run against real Redis (Docker)
- fakeredis used for unit tests
- Performance benchmarks verify latency targets
- Concurrent access tests with multiple threads
- WATCH conflict simulation and retry verification
- Pool exhaustion handling
- Unit tests for S3CacheProvider (mocked boto3)
- Unit tests for TieredCacheProvider (mocked Redis + S3)
- Integration tests with localstack S3
- Feature flag behavior tests (enabled/disabled)

### Monitoring Requirements
- Redis connection pool metrics exposed
- Operation latencies tracked via CacheMetrics
- ElastiCache CloudWatch metrics monitored
- Tier hit/miss ratios (Redis vs S3 vs total miss)
- Promotion count (S3 -> Redis)
- S3 operation latencies
- S3 error rates (for graceful degradation verification)

## Related Decisions

**Foundation**: See ADR-0029 for CacheProvider protocol definition that this infrastructure implements.

**Patterns**: See ADR-SUMMARY-CACHE for staleness detection, TTL strategies, and invalidation patterns that build on this infrastructure.

**Persistence**: See ADR-SUMMARY-PERSISTENCE for SaveSession integration with cache infrastructure.

## References

**Original ADRs**:
- ADR-0017: Redis Backend Architecture (2025-12-09)
- ADR-0024: Thread-Safety Guarantees (2025-12-09)
- ADR-0026: Two-Tier Cache Architecture (2025-12-09)

**Technical Design**:
- TDD-0008: Intelligent Caching

**Requirements**:
- PRD-0002: Intelligent Caching
- NFR-PERF-002: <5ms p99 read latency
- NFR-PERF-003: <10ms p99 write latency
- FR-CACHE-014: WATCH/MULTI for atomicity
- FR-CACHE-063: Native TTL support
