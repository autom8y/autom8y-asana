# ADR-0017: Redis Backend Architecture

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team, User
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [ADR-0016](ADR-0016-cache-protocol-extension.md)

## Context

PRD-0002 requires a production-ready cache backend for the intelligent caching layer. The legacy autom8 system uses S3-backed caching (TaskCache), which has served well but has limitations:

**Legacy S3 approach**:
- ~50-200ms latency per operation
- No native TTL support (manual expiration logic)
- No atomic operations (race condition potential)
- Higher cost for frequent small reads/writes
- Works well for large blob storage, less ideal for frequent cache operations

**Requirements for intelligent caching**:
- <5ms p99 read latency (NFR-PERF-002)
- <10ms p99 write latency (NFR-PERF-003)
- Atomic operations for version tracking (FR-CACHE-014)
- Native TTL support (FR-CACHE-063)
- Connection pooling (FR-CACHE-015)
- Batch operations (FR-CACHE-006, FR-CACHE-007)

**User decision**: Redis-only backend. S3 backend dropped. This is a **breaking change** from legacy autom8.

## Decision

**Use Redis as the sole cache backend with the following architecture:**

### Key Structure

```
# Task data by entry type
asana:tasks:{gid}:task          -> JSON (full task data)
asana:tasks:{gid}:subtasks      -> JSON array
asana:tasks:{gid}:dependencies  -> JSON array
asana:tasks:{gid}:dependents    -> JSON array
asana:tasks:{gid}:stories       -> JSON array
asana:tasks:{gid}:attachments   -> JSON array

# Struc with project context (custom fields vary by project)
asana:struc:{task_gid}:{project_gid} -> JSON (computed structural data)

# Version tracking (Redis HASH per task for atomic access)
asana:tasks:{gid}:_meta
    task          -> ISO timestamp (modified_at)
    subtasks      -> ISO timestamp
    dependencies  -> ISO timestamp
    dependents    -> ISO timestamp
    stories       -> ISO timestamp (last_story_at)
    attachments   -> ISO timestamp
    cached_at     -> ISO timestamp

# Per-project TTL configuration (optional)
asana:config:ttl:{project_gid}  -> Integer (TTL in seconds)
```

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

### Connection Configuration

```python
@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = True  # TLS enabled by default
    ssl_cert_reqs: str = "required"
    socket_timeout: float = 1.0  # 1s operation timeout
    socket_connect_timeout: float = 5.0  # 5s connect timeout
    max_connections: int = 10  # Pool size
    retry_on_timeout: bool = True
    health_check_interval: int = 30  # seconds
```

### Data Serialization

- **JSON encoding**: All cache data serialized with `orjson` for performance
- **Datetime format**: ISO 8601 strings (`2025-12-09T10:30:00Z`)
- **Compression**: Not applied (data typically small; adds latency)

## Rationale

**Why Redis over S3?**

| Factor | Redis | S3 |
|--------|-------|-----|
| Read latency | <5ms | 50-200ms |
| Write latency | <10ms | 100-500ms |
| Native TTL | Yes | No (manual) |
| Atomic operations | WATCH/MULTI | No |
| Batch operations | MGET, PIPELINE | Separate requests |
| Cost model | Memory-based | Request + storage |
| Ideal for | Frequent small reads | Large blob storage |

Redis is purpose-built for caching workloads. The latency requirements (NFR-PERF-002, NFR-PERF-003) cannot be met with S3.

**Why HASH for metadata?**

Using a Redis HASH (`asana:tasks:{gid}:_meta`) for version tracking allows:
- Atomic read of all entry type versions in one command (`HGETALL`)
- Atomic update of specific entry type (`HSET`)
- Reduced key count (one meta key per task vs. seven)
- Natural grouping of related version data

**Why separate keys per entry type?**

Storing task data separately from subtasks/stories/etc. enables:
- Independent TTL per entry type (stories may cache longer)
- Selective invalidation (update task without invalidating stories)
- Reduced payload size per operation
- Parallel fetching when multiple types needed

## Alternatives Considered

### Alternative 1: S3-Only Backend (Legacy Approach)

- **Description**: Continue using S3 as in legacy autom8 TaskCache.
- **Pros**:
  - No new infrastructure required
  - Proven at scale
  - Lower memory costs for large caches
  - Durable storage
- **Cons**:
  - 50-200ms latency (fails NFR-PERF-002)
  - No native TTL (manual expiration code)
  - No atomic operations (race conditions)
  - Higher operational cost for frequent operations
- **Why not chosen**: User decision. Performance requirements cannot be met. Breaking change accepted.

### Alternative 2: DynamoDB Backend

- **Description**: Use AWS DynamoDB with on-demand capacity.
- **Pros**:
  - Managed service
  - TTL support
  - Consistent single-digit ms latency
  - Durable storage
  - Pay-per-request pricing
- **Cons**:
  - More complex API than Redis
  - No atomic multi-key operations
  - Higher latency than Redis (<10ms vs <5ms)
  - More expensive for high-throughput workloads
  - Requires DynamoDB-specific code
- **Why not chosen**: Overkill for caching use case. Redis provides simpler API and lower latency. Team already familiar with Redis/ElastiCache.

### Alternative 3: Redis + S3 Hybrid (Two-Tier Cache)

- **Description**: Redis for hot data (L1), S3 for cold data (L2).
- **Pros**:
  - Best of both: fast + durable
  - Handles large datasets efficiently
  - Warm cache survives Redis restarts
- **Cons**:
  - Significant complexity (two backends)
  - Complex invalidation across tiers
  - Higher operational burden
  - User explicitly rejected dual-read approach
- **Why not chosen**: User decision for simplicity. Big-bang migration preferred over hybrid complexity.

### Alternative 4: Memcached

- **Description**: Use Memcached (or ElastiCache Memcached mode).
- **Pros**:
  - Simple key-value model
  - Very fast
  - Multi-threaded
  - ElastiCache support
- **Cons**:
  - No data structures (no HASH, LIST)
  - No atomic operations
  - No persistence option
  - No cluster mode (manual sharding)
  - No Lua scripting
- **Why not chosen**: Lacks Redis data structures needed for version tracking and atomic operations.

### Alternative 5: In-Memory Only (No External Cache)

- **Description**: Enhance `InMemoryCacheProvider` with all features, no Redis.
- **Pros**:
  - Zero infrastructure
  - No network latency
  - Simple deployment
- **Cons**:
  - Not shared across instances
  - Lost on process restart
  - Memory bound to process
  - Not suitable for multi-service deployments
- **Why not chosen**: SDK is used by multiple services and ECS tasks. Shared cache is required for efficiency.

## Consequences

### Positive

- **Sub-5ms read latency**: Meets NFR-PERF-002 requirement
- **Atomic operations**: WATCH/MULTI prevents race conditions
- **Native TTL**: Simplifies expiration logic
- **Batch efficiency**: MGET and pipelining reduce round trips
- **Operational familiarity**: Team knows Redis/ElastiCache
- **Valkey compatible**: AWS ElastiCache Valkey works identically

### Negative

- **New infrastructure required**: Must provision Redis/ElastiCache cluster
- **S3 cache data abandoned**: No migration path (big-bang cutover)
- **Memory costs**: Redis is memory-bound, more expensive than S3
- **Single point of failure**: Redis outage affects all caching (mitigated by graceful degradation)
- **Breaking change from legacy**: Existing S3 cache consumers must migrate

### Neutral

- **Redis cluster mode optional**: Single-node sufficient for typical workloads
- **Encryption at rest**: Delegated to ElastiCache configuration
- **Persistence**: Redis RDB/AOF optional, not required for caching

## Compliance

To ensure this decision is followed:

1. **Infrastructure checklist**:
   - ElastiCache Redis/Valkey cluster provisioned before deployment
   - TLS enabled on cluster
   - AUTH password configured and securely stored

2. **Code review checklist**:
   - All Redis operations use connection pooling
   - Timeouts configured on all operations
   - No blocking operations in async context

3. **Testing requirements**:
   - Integration tests run against real Redis (Docker)
   - fakeredis used for unit tests
   - Performance benchmarks verify latency targets

4. **Monitoring requirements**:
   - Redis connection pool metrics exposed
   - Operation latencies tracked via CacheMetrics
   - ElastiCache CloudWatch metrics monitored
