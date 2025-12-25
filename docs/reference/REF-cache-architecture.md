# REF: Cache Architecture

## Metadata

**Document ID**: REF-CACHE-ARCHITECTURE
**Type**: Reference
**Status**: Active
**Created**: 2025-12-24
**Supersedes**: PRD-0002, PRD-CACHE-INTEGRATION, PRD-WATERMARK-CACHE, TDD-0008, TDD-CACHE-INTEGRATION

---

## Overview

The autom8_asana SDK cache architecture provides multi-tier, versioned caching with intelligent staleness detection. The system is designed for zero-configuration operation with automatic provider selection, graceful degradation, and comprehensive observability.

### Design Principles

1. **Zero Configuration**: Works out-of-the-box with sensible defaults
2. **Graceful Degradation**: Cache failures never break operations
3. **Automatic Invalidation**: Mutations transparently invalidate affected entries
4. **Multi-Entry Type Support**: Different TTLs and behaviors per entity type
5. **Versioned Entries**: Modified-at tracking prevents stale reads

---

## Architecture Layers

### Provider Abstraction Layer

The cache system uses a protocol-based design with four provider implementations:

```
CacheProvider Protocol
├── NullCacheProvider (no-op, testing)
├── InMemoryCacheProvider (LRU, process-local)
├── RedisCacheProvider (distributed, production)
└── TieredCacheProvider (hot/warm/cold layers)
```

#### Provider Selection Priority

1. **Explicit Parameter**: `AsanaClient(cache_provider=MyProvider())`
2. **Environment Variable**: `ASANA_CACHE_PROVIDER` (memory|redis|tiered|none)
3. **Auto-Detection**: Based on `ASANA_ENVIRONMENT` and `REDIS_HOST` availability
4. **Fallback**: InMemoryCacheProvider (development default)

### Entry Types

The system supports seven specialized entry types, each with distinct behavior:

| Entry Type | TTL (default) | Use Case | Key Format |
|------------|---------------|----------|------------|
| `TASK` | 300s (5min) | Individual task data | `{task_gid}` |
| `SUBTASKS` | 300s | Task subtask list | `{parent_gid}` |
| `DEPENDENCIES` | 300s | Task dependencies | `{task_gid}` |
| `DEPENDENTS` | 300s | Tasks depending on this | `{task_gid}` |
| `STORIES` | 600s (10min) | Task comments/activity | `{task_gid}` |
| `ATTACHMENTS` | 300s | Task file attachments | `{task_gid}` |
| `DATAFRAME` | 300s | Extracted DataFrame rows | `{task_gid}:{project_gid}` |
| `DETECTION` | 300s | Entity type detection result | `{task_gid}` |
| `PROJECT_SECTIONS` | 1800s (30min) | Project section list | `project:{project_gid}:sections` |
| `GID_ENUMERATION` | 300s | Section-to-task GID mapping | `project:{project_gid}:gid_enumeration` |

---

## Cache Entry Structure

### CacheEntry Dataclass

```python
@dataclass
class CacheEntry:
    """Versioned cache entry with metadata."""

    data: dict[str, Any]          # The cached data (JSON-serializable)
    entry_type: EntryType          # Type of cached entry
    version: datetime              # modified_at or equivalent
    cached_at: datetime            # When entry was cached
    ttl: int | None               # TTL in seconds (None = no expiration)
    metadata: dict[str, Any]       # Entry-specific metadata
```

### Metadata Fields

Common metadata fields across entry types:

- `extension_count`: Progressive TTL extension counter (staleness detection)
- `last_fetched`: Timestamp of last API fetch (stories incremental)
- `project_gid`: Project context (DataFrame entries)
- `section_count`: Number of sections (GID enumeration)
- `total_gid_count`: Total task GIDs (GID enumeration)

---

## Configuration

### AsanaConfig Integration

Cache configuration is nested within the main SDK configuration:

```python
from autom8_asana import AsanaConfig, CacheConfig

config = AsanaConfig(
    cache=CacheConfig(
        enabled=True,                  # Master enable/disable
        provider="redis",              # Explicit provider selection
        freshness=Freshness.EVENTUAL,  # Default freshness mode
        ttl=TTLSettings(
            default_ttl=300,
            entity_type_ttls={
                "business": 3600,      # 1 hour for Business entities
                "contact": 900,        # 15 min for Contacts
                "unit": 900,           # 15 min for Units
                "offer": 180,          # 3 min for Offers
                "process": 60,         # 1 min for Processes
            }
        ),
        overflow=OverflowSettings(
            subtasks=40,
            dependencies=40,
            dependents=40,
            stories=100,
            attachments=40,
        ),
    )
)

client = AsanaClient(config=config)
```

### Environment Variables

| Variable | Values | Effect |
|----------|--------|--------|
| `ASANA_CACHE_ENABLED` | true/false | Master switch |
| `ASANA_CACHE_PROVIDER` | memory/redis/tiered/none | Provider selection |
| `ASANA_CACHE_TTL_DEFAULT` | seconds | Default TTL |
| `ASANA_ENVIRONMENT` | production/development | Auto-detection hint |
| `REDIS_HOST` | hostname | Redis connection (if provider=redis) |
| `REDIS_PORT` | port | Redis port (default: 6379) |
| `REDIS_PASSWORD` | password | Redis AUTH |
| `REDIS_SSL` | true/false | Enable TLS (default: true) |

---

## Provider Implementations

### InMemoryCacheProvider

Process-local LRU cache with TTL expiration.

**Characteristics**:
- Thread-safe with locks
- LRU eviction when max_size reached (default: 10,000 entries)
- TTL enforcement on read
- No cross-process sharing
- Zero external dependencies

**Use Cases**:
- Development environments
- Single-process applications
- Testing
- Fallback when Redis unavailable

**Configuration**:
```python
from autom8_asana.cache import InMemoryCacheProvider

cache = InMemoryCacheProvider(
    max_size=10000,      # Maximum entries before LRU eviction
    default_ttl=300,     # Default TTL in seconds
)
```

### RedisCacheProvider

Distributed cache using Redis/Valkey backend.

**Characteristics**:
- Multi-process shared state
- Persistent across restarts
- WATCH/MULTI for atomic operations
- Connection pooling
- TLS support
- Cluster mode support

**Use Cases**:
- Production deployments
- Multi-process applications (ECS, Lambda)
- Shared cache across services
- Long-running sessions

**Configuration**:
```python
from autom8_asana.cache import RedisCacheProvider

cache = RedisCacheProvider(
    host="cache.example.com",
    port=6379,
    password="secret",
    ssl=True,
    pool_size=10,
    connect_timeout=5,
    operation_timeout=1,
)
```

**Key Structure**:
```
asana:tasks:{gid}:{entry_type}
    ├── data: <JSON blob>
    ├── version: <modified_at timestamp>
    ├── cached_at: <cache write timestamp>
    ├── ttl: <TTL in seconds>
    └── metadata: <Entry-specific fields>
```

### TieredCacheProvider

Multi-level cache with hot/warm/cold tiers.

**Characteristics**:
- Hot tier: In-memory (fast, volatile)
- Warm tier: Redis (medium, shared)
- Cold tier: S3 (slow, persistent)
- Automatic promotion/demotion
- Overflow management

**Use Cases**:
- Very large datasets
- Cost optimization (S3 cheaper than Redis)
- Archival requirements
- Multi-region deployments

**Configuration**:
```python
from autom8_asana.cache import TieredCacheProvider

cache = TieredCacheProvider(
    hot=InMemoryCacheProvider(max_size=1000),
    warm=RedisCacheProvider(host="redis.local"),
    cold=S3CacheProvider(bucket="cache-bucket"),
)
```

---

## Integration Points

### TasksClient Integration

Tasks are cached automatically in `get_async()` and can be populated via `list_async()`:

```python
# Automatic cache check/populate
task = await client.tasks.get_async("1234567890")
# Cache hit on repeat: <5ms latency

# List with cache population (DataFrame path)
tasks = await fetch_all_sections()  # Populates cache
# Subsequent gets use cache
```

### SaveSession Integration

Mutations automatically invalidate affected cache entries:

```python
session = SaveSession(client)
session.track(task)
task.name = "Updated"

await session.commit_async()
# Cache invalidated for:
# - EntryType.TASK: task_gid
# - EntryType.SUBTASKS: task_gid (if task has subtasks)
# - EntryType.DATAFRAME: task_gid:project_gid (all projects)
# - EntryType.DETECTION: task_gid
```

### DataFrame Integration

DataFrame operations use both task cache and dedicated DataFrame cache:

```python
# First call: Cold fetch, populates both caches
df = await project.to_dataframe_parallel_async(client)  # ~10s

# Second call: Warm cache, hits task + DataFrame cache
df = await project.to_dataframe_parallel_async(client)  # <1s
```

---

## Batch Operations

### Batch Read

Efficient bulk retrieval for large datasets:

```python
# Batch lookup (single operation, not N individual gets)
entries = cache.get_batch(
    keys=["task1", "task2", "task3"],
    entry_type=EntryType.TASK,
)

# Returns: dict[str, CacheEntry | None]
# Missing keys have None values
```

### Batch Write

Efficient bulk population:

```python
# Batch write (single operation, not N individual sets)
cache.set_batch({
    "task1": CacheEntry(...),
    "task2": CacheEntry(...),
    "task3": CacheEntry(...),
})
```

**Performance**:
- InMemory: O(N) sequential loop
- Redis: O(N) sequential (pipeline support deferred)
- Target: <100ms for 500 entries

---

## Graceful Degradation

The cache system never breaks operations - all failures are caught and logged:

### Cache Provider Unavailable

```python
# Redis connection fails
client = AsanaClient(cache_provider=RedisCacheProvider(...))

# Operations continue, fall back to NullCacheProvider
task = await client.tasks.get_async("123")  # Success, logs warning
```

### Cache Operation Failures

```python
# Read failure during get_async
try:
    entry = cache.get("key", EntryType.TASK)
except Exception as e:
    logger.warning(f"Cache read failed: {e}")
    # Proceed with API fetch, operation succeeds
```

### Write Failure Handling

```python
# Write failure during population
try:
    cache.set("key", entry)
except Exception as e:
    logger.warning(f"Cache write failed: {e}")
    # Return data anyway, operation succeeds
```

---

## Observability

### Structured Logging

Cache operations emit structured log events:

```python
{
    "event": "cache_hit",
    "cache_source": "task_cache",
    "task_gid": "1234567890",
    "entry_type": "TASK",
    "latency_ms": 2.3,
}

{
    "event": "cache_miss",
    "cache_source": "task_cache",
    "task_gid": "1234567890",
    "entry_type": "TASK",
    "fetch_time_ms": 187.4,
}
```

### Cache Metrics

Aggregate metrics via `CacheMetrics` helper:

```python
metrics = CacheMetrics()

# Accumulates events over time window
metrics.hit_rate()  # Percentage
metrics.hit_count  # Integer
metrics.miss_count  # Integer
metrics.avg_latency  # Milliseconds
```

### Event Callbacks

Register callbacks for custom monitoring:

```python
def on_cache_event(event: CacheEvent):
    # Send to CloudWatch, DataDog, etc.
    cloudwatch.put_metric(
        name=event.type,
        value=1,
        dimensions={"entry_type": event.entry_type},
    )

cache.on_cache_event(on_cache_event)
```

---

## Performance Targets

| Operation | Target | Actual (InMemory) | Actual (Redis) |
|-----------|--------|-------------------|----------------|
| Cache hit latency | <5ms | ~1ms | ~3ms |
| Cache miss overhead | <10ms | ~2ms | ~5ms |
| Batch read (500 entries) | <100ms | ~15ms | ~50ms |
| Batch write (500 entries) | <100ms | ~20ms | ~60ms |
| Warm DataFrame fetch (3,500 tasks) | <1s | ~0.6s | ~0.8s |
| Cold DataFrame fetch (3,500 tasks) | <10s | ~9.5s | ~9.8s |

---

## Migration Guide

### From Legacy autom8 S3 Cache

The SDK drops S3 backend support in favor of Redis-only:

**Breaking Change**: S3-backed cache data is not migrated
**Impact**: Cache miss spike at deployment (one-time cost)
**Mitigation**: Accept big-bang cutover; cache warms within 5-10 minutes

### From No Cache to Cached

Enabling cache is automatic with zero code changes:

```python
# Before: No explicit cache configuration
client = AsanaClient(token="...")

# After: Automatic InMemory cache in development
client = AsanaClient(token="...")  # Same code, now cached!

# Production: Set environment variables
# ASANA_ENVIRONMENT=production
# REDIS_HOST=cache.example.com
# Now uses Redis automatically
```

---

## Related Documents

- [REF-cache-invalidation.md](REF-cache-invalidation.md) - Staleness detection and TTL patterns
- [REF-cache-patterns.md](REF-cache-patterns.md) - Usage patterns and optimization techniques
- [ADR-0026](../decisions/ADR-0026-two-tier-cache-architecture.md) - Two-tier architecture decision
- [ADR-0016](../decisions/ADR-0016-cache-protocol-extension.md) - Protocol extension design
- [ADR-0123](../decisions/ADR-0123-cache-provider-selection.md) - Provider selection strategy

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | Tech Writer | Initial consolidation from PRD-0002, PRD-CACHE-INTEGRATION, TDD-0008, TDD-CACHE-INTEGRATION |
