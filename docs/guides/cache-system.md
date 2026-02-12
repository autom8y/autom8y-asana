# Cache System Guide

## Overview

The autom8_asana SDK cache system reduces API calls by 90%+ for stable workloads through multi-tier, versioned caching with automatic staleness detection. The system operates with zero configuration in most environments.

### Key Features

- **Multi-tier architecture**: In-memory (fast), Redis (distributed), S3 (durable)
- **Automatic provider selection**: Environment-aware defaults
- **Versioned entries**: Prevents serving stale data via modified-at tracking
- **Graceful degradation**: Cache failures never break operations
- **Progressive TTL**: Exponentially increasing TTL for stable entities

### Architecture Diagram

```
                    ┌─────────────────────────┐
                    │   AsanaClient           │
                    │   - tasks.get_async()   │
                    │   - to_dataframe()      │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  CacheProvider Protocol │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
    ┌─────────▼────────┐ ┌─────▼──────┐ ┌────────▼────────┐
    │ InMemoryProvider │ │   Redis    │ │   Tiered        │
    │ (dev default)    │ │ (prod)     │ │ (Redis+S3)      │
    └──────────────────┘ └────────────┘ └─────────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                    Hot (Redis)     Cold (S3)
```

## Cache Providers

### InMemoryCacheProvider

Process-local LRU cache with TTL expiration.

**Characteristics**:
- Thread-safe via locks
- LRU eviction at max_size (default 10,000 entries)
- Zero external dependencies
- Lost on process restart

**When to use**:
- Development environments
- Single-process applications
- Testing
- Fallback when Redis unavailable

**Configuration**:
```python
from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider

cache = EnhancedInMemoryCacheProvider(
    max_size=10000,      # Maximum entries before LRU eviction
    default_ttl=300,     # 5 minutes
)
```

### RedisCacheProvider

Distributed cache using Redis/Valkey backend.

**Characteristics**:
- Multi-process shared state
- Persistent across restarts
- Connection pooling
- TLS support
- Atomic operations via WATCH/MULTI

**When to use**:
- Production deployments
- Multi-process applications (ECS, Lambda)
- Shared cache across services
- Long-running sessions

**Configuration**:
```python
from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig

config = RedisConfig(
    host="cache.example.com",
    port=6379,
    password="secret",
    ssl=True,
    socket_timeout=1.0,
    max_connections=10,
)

cache = RedisCacheProvider(config=config)
```

**Environment variables**:
```bash
REDIS_HOST=cache.example.com
REDIS_PORT=6379
REDIS_PASSWORD=secret
REDIS_SSL=true
```

**Key structure**:
```
asana:tasks:{gid}:{entry_type}
    ├── data: <JSON blob>
    ├── version: <modified_at timestamp>
    ├── cached_at: <cache write timestamp>
    ├── ttl: <TTL in seconds>
    └── metadata: <Entry-specific fields>
```

### TieredCacheProvider

Multi-level cache with hot (Redis) and cold (S3) tiers.

**Characteristics**:
- Hot tier: In-memory/Redis (fast, volatile)
- Cold tier: S3 (slow, persistent, cost-effective)
- Automatic promotion on cold hits
- Write-through to both tiers

**When to use**:
- Very large datasets (millions of tasks)
- Cost optimization (S3 cheaper than Redis)
- Archival requirements
- Multi-region deployments

**Configuration**:
```python
from autom8_asana.cache.providers.tiered import TieredCacheProvider, TieredConfig

config = TieredConfig(
    s3_enabled=True,
    promotion_ttl=3600,      # 1 hour when promoting from S3
    write_through=True,
)

cache = TieredCacheProvider(
    hot_tier=redis_provider,
    cold_tier=s3_provider,
    config=config,
)
```

**Read strategy** (cache-aside with promotion):
1. Check hot tier (Redis)
2. On hit: return immediately
3. On miss: check cold tier (S3) if enabled
4. On cold hit: promote to hot tier with promotion_ttl
5. On miss: return None (caller fetches from API)

## TTL Strategy

### Default TTLs by Entry Type

| Entry Type | TTL | Rationale |
|------------|-----|-----------|
| TASK (generic) | 300s (5 min) | Balanced freshness vs cache hit rate |
| TASK (Business) | 3600s (1 hour) | Stable hierarchy entities |
| TASK (Contact/Unit) | 900s (15 min) | Moderate change frequency |
| TASK (Offer) | 180s (3 min) | High churn in sales pipeline |
| TASK (Process) | 60s (1 min) | Frequent state transitions |
| STORIES | 600s (10 min) | Comments less dynamic than tasks |
| DATAFRAME | 300s (5 min) | Matches task TTL |
| DETECTION | 300s (5 min) | Subtask structure stable |
| PROJECT_SECTIONS | 1800s (30 min) | Section structure rarely changes |
| GID_ENUMERATION | 300s (5 min) | Task-section membership dynamic |

### Progressive TTL Extension

Stable entities exponentially extend their TTL on successful staleness checks.

**Algorithm**:
1. Check if cached version matches API version via lightweight check
2. If unchanged: double TTL (up to max 24 hours)
3. If changed: reset to base TTL

**Progression table**:

| Extension | TTL | Cumulative Time | API Calls (2h period) |
|-----------|-----|-----------------|----------------------|
| 0 (base) | 300s (5 min) | 0 | 24 |
| 1 | 600s (10 min) | 5 min | 12 |
| 2 | 1200s (20 min) | 15 min | 6 |
| 3 | 2400s (40 min) | 35 min | 3 |
| 4 | 4800s (80 min) | 1h 15min | 2 |
| 5 | 9600s (160 min) | 2h 35min | 1 |
| 6+ | 86400s (24h) | Ceiling | Minimal |

**API call reduction**: 79% for 2-hour stable entity (5 calls vs 24 with fixed TTL).

### Configuration

```python
from autom8_asana.config import CacheConfig, TTLSettings

config = CacheConfig(
    ttl=TTLSettings(
        default_ttl=300,
        entity_type_ttls={
            "business": 3600,
            "contact": 900,
            "unit": 900,
            "offer": 180,
            "process": 60,
        },
        staleness_check_max_ttl=86400,  # 24 hours
    )
)
```

## Cache Warming

### Startup Warmup

Warm cache before handling production traffic (Lambda pre-deployment).

**Priority order** (configurable):
1. Offer (highest churn, warm first)
2. Unit
3. Business
4. Contact

**Example**:
```python
from autom8_asana.cache.dataframe.warmer import CacheWarmer, WarmResult

warmer = CacheWarmer(
    cache=dataframe_cache,
    priority=["offer", "unit", "business", "contact"],
    strict=True,  # Fail if any entity type fails
)

results = await warmer.warm_all_async(
    client=client,
    project_gid_provider=lambda et: registry.get_project_gid(et),
)

for result in results:
    if result.result == WarmResult.SUCCESS:
        print(f"{result.entity_type}: {result.row_count} rows in {result.duration_ms}ms")
```

### Admin Endpoints

Manual cache warming via API endpoint.

**Endpoint**: `POST /api/v1/internal/cache/warm`

**Payload**:
```json
{
  "entity_types": ["offer", "unit"],
  "project_gids": {
    "offer": "1234567890",
    "unit": "0987654321"
  }
}
```

**Response**:
```json
{
  "results": [
    {
      "entity_type": "offer",
      "result": "success",
      "row_count": 5000,
      "duration_ms": 2500
    }
  ]
}
```

### Background Refresh

Automatically refresh cache entries before TTL expiration.

**Not implemented in Phase 1**. Planned for Phase 2 with background worker pattern.

## Staleness Detection

### Version-Based Validation

Compare cached `version` (modified_at) against API `modified_at`.

```python
# Cache entry
entry = cache.get_versioned("task_gid", EntryType.TASK)
# entry.version = 2025-12-23T10:00:00Z

# API response
fresh_task = await client.tasks.get_async("task_gid")
# fresh_task.modified_at = 2025-12-23T11:30:00Z

# Comparison
if fresh_task.modified_at > entry.version:
    # Stale: fetch fresh data
else:
    # Fresh: use cached data
```

### Lightweight Batch Staleness Check

Check `modified_at` via batch API instead of full payload fetch.

**Request coalescing**:
- Collect expired entries within 50ms window
- Single batch API call with `opt_fields=modified_at` only
- ~100 bytes per task vs ~5KB full payload

**Batch API call**:
```http
POST /batch
{
  "data": {
    "actions": [
      {"method": "GET", "relative_path": "/tasks/A", "options": {"opt_fields": "modified_at"}},
      {"method": "GET", "relative_path": "/tasks/B", "options": {"opt_fields": "modified_at"}},
      {"method": "GET", "relative_path": "/tasks/C", "options": {"opt_fields": "modified_at"}}
    ]
  }
}
```

**Constraints**:
- Max 10 actions per request (auto-chunked if >10)
- Counts as 1 API request for rate limiting
- Concurrent caller deduplication

### Freshness Modes

**EVENTUAL (default)**:
- Trust TTL without version validation
- Data at most TTL seconds stale
- <5ms cache hits
- Use for: dashboards, reporting, batch processing

**STRICT**:
- Validate version before returning cached data
- Always current data (assuming modified_at reliable)
- <100ms for lightweight check
- Use for: critical operations, audit trails

```python
from autom8_asana.cache.models.freshness import Freshness

# STRICT mode
entry = cache.get_versioned(
    "task_gid",
    EntryType.TASK,
    freshness=Freshness.STRICT,
)
# Validates version via lightweight check before returning
```

## Invalidation

### Mutation Hooks (Automatic)

SaveSession automatically invalidates affected cache entries after commits.

```python
from autom8_asana.client import AsanaClient
from autom8_asana.save_session import SaveSession

session = SaveSession(client)

# Track mutations
session.track(task)
task.name = "Updated Name"

# Commit triggers automatic invalidation
await session.commit_async()

# Invalidates:
# - EntryType.TASK for task.gid
# - EntryType.DATAFRAME for task.gid:project_gid (all projects)
# - EntryType.DETECTION for task.gid
# - EntryType.SUBTASKS for task.gid (if has subtasks)
```

**Multi-project tasks**:
```python
# Task in 3 projects
task.memberships = [
    {"project": {"gid": "proj_a"}},
    {"project": {"gid": "proj_b"}},
    {"project": {"gid": "proj_c"}},
]

session.track(task)
task.custom_fields = [...]

await session.commit_async()

# Invalidates DataFrame cache for all 3 projects:
# - {task_gid}:proj_a
# - {task_gid}:proj_b
# - {task_gid}:proj_c
```

### Manual Invalidation

Invalidate specific entries or patterns.

**Single entry**:
```python
cache.invalidate("task_gid", entry_types=[EntryType.TASK])
```

**All entry types for a key**:
```python
cache.invalidate("task_gid")  # entry_types=None invalidates all
```

**Clear all tasks** (emergency):
```python
count = cache.clear_all_tasks()
print(f"Deleted {count} task entries")
```

### TTL Expiry

Automatic expiration based on cached_at + ttl.

**TTL reset on change**:
- Detected change resets TTL to base value
- Extension counter reset to 0
- Prevents long TTL on recently changed entities

## Troubleshooting

For detailed troubleshooting procedures, see [RUNBOOK: Cache Troubleshooting](../runbooks/RUNBOOK-cache-troubleshooting.md).

### Quick Diagnosis

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| High cache miss rate | TTL too short | Increase base TTL or enable progressive TTL |
| Stale data served | Staleness detection disabled | Enable STRICT freshness mode |
| Cache errors in logs | Redis connection issues | Check Redis health, verify REDIS_HOST |
| Slow API calls despite cache | Cache not being populated | Verify cache provider initialization |

### Common Issues

**Cache misses**:
```bash
# Check cache hit rate
redis-cli INFO stats
# Look for: keyspace_hits, keyspace_misses
# Calculate: hit_rate = hits / (hits + misses)
```

**Stale data**:
```python
# Enable staleness detection
config = CacheConfig(
    enable_staleness_checks=True,
    staleness_check_coalesce_window_ms=50,
)
```

**Cache errors**:
```bash
# Check Redis connectivity
redis-cli PING
# Should return: PONG

# Check application logs
grep "CacheError\|ConnectionError" application.log | tail -50
```

**Cache not working**:
```python
# Verify cache provider wired
print(f"Cache provider: {client._cache}")  # Should not be None

# Check cache keys
redis-cli KEYS task:*
```

### Emergency Procedures

**Clear entire cache**:
```bash
# WARNING: Clears ALL cached data
redis-cli FLUSHDB

# Or from Python
await cache.clear()
```

**Disable cache** (emergency fallback):
```python
# In config or environment
CACHE_ENABLED = False

# Or in code
client = AsanaClient(cache_provider=None)
```

## Configuration Examples

### Development (default)

```python
from autom8_asana.client import AsanaClient

# Automatic InMemoryCacheProvider
client = AsanaClient(token="...")
# No configuration needed
```

### Production with Redis

```bash
# Environment variables
export ASANA_ENVIRONMENT=production
export REDIS_HOST=cache.example.com
export REDIS_PORT=6379
export REDIS_PASSWORD=secret
export REDIS_SSL=true
```

```python
from autom8_asana.client import AsanaClient

# Automatic RedisCacheProvider selection
client = AsanaClient(token="...")
```

### Custom Configuration

```python
from autom8_asana.client import AsanaClient
from autom8_asana.config import AsanaConfig, CacheConfig, TTLSettings

config = AsanaConfig(
    cache=CacheConfig(
        enabled=True,
        provider="redis",  # Explicit selection
        ttl=TTLSettings(
            default_ttl=300,
            entity_type_ttls={
                "business": 3600,
                "contact": 900,
                "unit": 900,
                "offer": 180,
                "process": 60,
            },
        ),
    )
)

client = AsanaClient(config=config)
```

### Disable Caching

```python
from autom8_asana.client import AsanaClient
from autom8_asana.config import AsanaConfig, CacheConfig

config = AsanaConfig(
    cache=CacheConfig(enabled=False)
)

client = AsanaClient(config=config)
```

## Performance Targets

### Individual Operations

| Operation | Cold | Warm | Speedup |
|-----------|------|------|---------|
| Task get | ~200ms | <5ms | 40x |
| Stories fetch (100 stories) | ~500ms | ~100ms (incremental) | 5x |
| Detection (Tier 4) | ~200ms | <5ms | 40x |
| Hydration (5 levels) | ~1000ms | <50ms | 20x |

### DataFrame Extraction (3,500 tasks)

| Scenario | API Calls | Latency | Cache Hit Rate |
|----------|-----------|---------|----------------|
| Cold start (no cache) | 35+ | ~10s | 0% |
| Warm cache (all cached) | 0 | <1s | 100% |
| Partial (90% cached) | ~12 | ~2s | 90% |
| After SaveSession (10 updated) | ~10 | ~1.5s | ~99.7% |

### Batch Operations

| Operation | Target | Actual (InMemory) | Actual (Redis) |
|-----------|--------|-------------------|----------------|
| Cache hit latency | <5ms | ~1ms | ~3ms |
| Batch read (500 entries) | <100ms | ~15ms | ~50ms |
| Batch write (500 entries) | <100ms | ~20ms | ~60ms |

## Related Documentation

- [REF: Cache Architecture](../reference/REF-cache-architecture.md) - Detailed architecture and provider specifications
- [REF: Cache Patterns](../reference/REF-cache-patterns.md) - Usage patterns and optimization techniques
- [REF: Cache Invalidation](../reference/REF-cache-invalidation.md) - Staleness detection algorithms
- [RUNBOOK: Cache Troubleshooting](../runbooks/RUNBOOK-cache-troubleshooting.md) - Detailed troubleshooting procedures
- [ADR-0026](../adr/ADR-0026-two-tier-cache-architecture.md) - Two-tier architecture decision
- [ADR-0123](../adr/ADR-0123-cache-provider-selection.md) - Provider selection strategy

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-12 | Tech Writer | Initial guide synthesizing REF-cache-architecture, REF-cache-patterns, REF-cache-invalidation, and source code |
