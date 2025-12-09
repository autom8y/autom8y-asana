# autom8 Cache Migration Guide

> Migrating from S3-based TaskCache to Redis-based SDK intelligent caching.

**Migration Strategy**: Big-bang cutover per [ADR-0025](../decisions/ADR-0025-migration-strategy.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Code Changes](#code-changes)
5. [Cutover Procedure](#cutover-procedure)
6. [Monitoring](#monitoring)
7. [Rollback Plan](#rollback-plan)
8. [FAQ](#faq)

---

## Overview

### What's Changing

| Aspect | Legacy (S3) | New (Redis) |
|--------|-------------|-------------|
| Backend | S3 bucket with JSON files | AWS ElastiCache Redis |
| Staleness detection | modified_at comparison | Version-aware with 25s TTL cache |
| TTL management | Manual expiration | Automatic TTL per entry type |
| Batch operations | Individual S3 GETs | Pipelined Redis operations |
| Metrics | Limited | Built-in hit/miss/latency metrics |

### Migration Timeline

```
T-7 days: Provision Redis infrastructure (ElastiCache)
T-3 days: Deploy SDK to staging with Redis
T-1 day:  Performance test in staging
T-0:      Production deployment (cutover)
T+15min:  Monitor cache warm-up
T+1hr:    Verify hit rate stabilizing
T+24hr:   Confirm normal operations
T+7 days: Decommission S3 cache
```

### Expected Impact

- **T+0**: 100% cache miss rate (cold cache)
- **T+15min**: ~50% hit rate as frequently accessed tasks cache
- **T+1hr**: ~80% hit rate (target stabilization)
- **T+24hr**: Normal operations, comparable to S3 hit rate

---

## Prerequisites

### 1. AWS ElastiCache Cluster

Provision a Redis cluster with these specifications:

| Setting | Recommended Value | Notes |
|---------|-------------------|-------|
| Engine | Redis 7.x | Latest stable version |
| Node type | cache.r6g.large | Adjust based on load |
| Number of nodes | 2 (primary + replica) | Multi-AZ for HA |
| Encryption in-transit | Enabled | TLS required |
| Encryption at-rest | Enabled | Recommended |
| VPC | Same as autom8 services | For low latency |
| Security group | Allow from autom8 services | Port 6379 |

### 2. SDK Version

Ensure `autom8_asana` SDK version >= 1.0.0 (with caching layer):

```bash
pip install "autom8_asana>=1.0.0"
```

### 3. Dependencies

The SDK's Redis backend requires the `redis` package:

```bash
pip install redis>=4.0.0
```

---

## Environment Configuration

### Required Environment Variables

```bash
# Redis connection (required)
export REDIS_HOST="your-elasticache-cluster.xxxxx.use1.cache.amazonaws.com"

# Optional (defaults shown)
export REDIS_PORT="6379"
export REDIS_SSL="true"
export REDIS_PASSWORD=""  # If auth enabled
```

### AWS ElastiCache Connection

For ElastiCache, use the **Primary Endpoint** hostname:

```bash
# From AWS Console: ElastiCache > Redis clusters > your-cluster
# Copy "Primary endpoint" (without port)
export REDIS_HOST="your-cluster.xxxxx.use1.cache.amazonaws.com"
export REDIS_SSL="true"  # ElastiCache uses TLS by default
```

### Local Development

For local development, use a local Redis instance:

```bash
# Start Redis locally
docker run -d -p 6379:6379 redis:7

# Configure for local
export REDIS_HOST="localhost"
export REDIS_SSL="false"
```

---

## Code Changes

### Before: Legacy S3 Cache

```python
# Legacy autom8 code (to be replaced)
from apis.aws_api.services.s3.models.asana_cache import TaskCache

async def load_task_collection(task_dicts: list[dict]) -> list[dict]:
    """Legacy S3-based task loading."""
    cache = TaskCache()

    for task in task_dicts:
        gid = task.get("gid")
        cached = await cache.get(gid)
        if cached and not is_stale(cached, task):
            # Use cached version
            ...
        else:
            # Fetch from API and cache
            fresh = await fetch_from_api(gid)
            await cache.set(gid, fresh)

    return results
```

### After: SDK Redis Cache

```python
# New autom8 code using SDK
from autom8_asana.cache.autom8_adapter import (
    create_autom8_cache_provider,
    migrate_task_collection_loading,
    MigrationResult,
)

# Initialize once (typically at module level or in DI container)
_cache = None

def get_cache():
    """Get or create cache provider singleton."""
    global _cache
    if _cache is None:
        _cache = create_autom8_cache_provider()
    return _cache


async def load_task_collection(task_dicts: list[dict]) -> list[dict]:
    """New Redis-based task loading using SDK."""
    cache = get_cache()

    result: MigrationResult = await migrate_task_collection_loading(
        task_dicts=task_dicts,
        cache=cache,
        batch_api=get_batch_modifications,  # Your batch API wrapper
        task_fetcher=fetch_tasks_from_api,  # Your task fetch function
    )

    # Optional: Log metrics
    log.info(
        "Task collection loaded",
        total=result.total_tasks,
        cache_hits=result.cache_hits,
        cache_misses=result.cache_misses,
        hit_rate=f"{result.hit_rate:.1f}%",
    )

    return result.tasks


async def get_batch_modifications(gids: list[str]) -> dict[str, str]:
    """Fetch modified_at timestamps via Asana batch API.

    This function wraps your existing batch API call.
    Returns dict mapping GID to modified_at ISO timestamp.
    """
    # Your existing batch API implementation
    # e.g., using asana-python or direct API calls
    response = await asana_client.batch.create_request({
        "actions": [
            {"method": "GET", "relative_path": f"/tasks/{gid}?opt_fields=modified_at"}
            for gid in gids
        ]
    })

    return {
        action["data"]["gid"]: action["data"]["modified_at"]
        for action in response["data"]
        if action.get("status_code") == 200
    }


async def fetch_tasks_from_api(gids: list[str]) -> list[dict]:
    """Fetch full task data for given GIDs.

    This function wraps your existing task fetch logic.
    """
    # Your existing task fetch implementation
    tasks = []
    for gid in gids:
        task = await asana_client.tasks.get_task(gid, opt_fields="...")
        tasks.append(task)
    return tasks
```

### Integration Points

The migration adapter needs two callback functions:

1. **`batch_api`**: Fetches `modified_at` timestamps for staleness checking
   - Input: `list[str]` (GIDs)
   - Output: `dict[str, str]` (GID -> modified_at)
   - Called with in-memory 25s TTL cache

2. **`task_fetcher`**: Fetches full task data for stale tasks
   - Input: `list[str]` (stale GIDs)
   - Output: `list[dict]` (task dicts)
   - Called only for tasks needing refresh

---

## Cutover Procedure

### Pre-Deployment Checklist

```markdown
- [ ] ElastiCache cluster provisioned and healthy
- [ ] Security groups allow autom8 services to connect
- [ ] REDIS_HOST environment variable configured in all environments
- [ ] SDK version >= 1.0.0 deployed
- [ ] redis Python package installed
- [ ] Monitoring dashboards ready
- [ ] Rollback procedure documented
- [ ] Team notified of expected performance impact
```

### Deployment Steps

```bash
# 1. Verify Redis connectivity (from autom8 service)
python -c "
from autom8_asana.cache.autom8_adapter import create_autom8_cache_provider, check_redis_health
cache = create_autom8_cache_provider()
print(check_redis_health(cache))
"

# 2. Deploy updated code
# (Your standard deployment process)

# 3. Verify deployment
curl http://your-service/health  # Should return healthy

# 4. Monitor metrics
# (See Monitoring section)
```

### Post-Deployment Warming (Optional)

For high-traffic projects, pre-warm the cache:

```python
from autom8_asana.cache.autom8_adapter import (
    create_autom8_cache_provider,
    warm_project_tasks,
)

async def warm_high_traffic_projects():
    """Pre-warm cache for frequently accessed projects."""
    cache = create_autom8_cache_provider()

    # Your high-traffic project GIDs
    high_traffic_projects = [
        "project_gid_1",
        "project_gid_2",
        # ...
    ]

    for project_gid in high_traffic_projects:
        warmed = await warm_project_tasks(
            cache=cache,
            project_gid=project_gid,
            task_fetcher=lambda p: fetch_all_project_tasks(p),
        )
        print(f"Warmed {warmed} tasks for project {project_gid}")

# Run after deployment
asyncio.run(warm_high_traffic_projects())
```

---

## Monitoring

### Key Metrics

| Metric | Expected at T+0 | Expected at T+1hr | Alert Threshold |
|--------|-----------------|-------------------|-----------------|
| Cache hit rate | 0% | >= 80% | < 70% at T+1hr |
| Redis connection errors | 0 | 0 | > 0 sustained |
| API call rate | +100% vs baseline | Normal | > 150% at T+1hr |
| p99 latency | +50% vs baseline | Normal | > 200% at T+1hr |
| Redis memory | Growing | Stable | > 80% capacity |

### Accessing SDK Metrics

```python
from autom8_asana.cache.autom8_adapter import create_autom8_cache_provider

cache = create_autom8_cache_provider()
metrics = cache.get_metrics()

# Log or expose via /metrics endpoint
print(f"Hit rate: {metrics.hit_rate:.1f}%")
print(f"Total hits: {metrics.total_hits}")
print(f"Total misses: {metrics.total_misses}")
print(f"Total errors: {metrics.total_errors}")
print(f"Avg read latency: {metrics.avg_read_latency:.2f}ms")
```

### Health Check Endpoint

Add to your service's health check:

```python
from autom8_asana.cache.autom8_adapter import check_redis_health

@app.route("/health")
async def health_check():
    cache_health = check_redis_health(get_cache())

    return {
        "status": "healthy" if cache_health["healthy"] else "degraded",
        "cache": cache_health,
    }
```

---

## Rollback Plan

### Immediate Mitigation (< 5 minutes)

If Redis issues detected, disable caching entirely:

```python
# Emergency disable - SDK operates without cache
from autom8_asana.cache.settings import CacheSettings

settings = CacheSettings(enabled=False)
cache = create_autom8_cache_provider(settings=settings)
# SDK continues operating with 100% cache miss (all API calls)
```

### Code Rollback (< 30 minutes)

1. Revert deployment to previous version
2. Services restore to S3 cache (if still functional)
3. Investigate and fix issue
4. Redeploy

### Rollback Decision Criteria

Roll back if any of these occur:

- Redis connection failures sustained > 1 minute
- Cache hit rate < 50% after 2 hours
- Asana API rate limits exhausted
- User-reported latency issues affecting operations

---

## FAQ

### Q: What happens if Redis goes down?

**A**: The SDK enters "degraded mode":
- All cache operations fail gracefully (return miss/no-op)
- API calls continue to function (100% miss)
- No data loss (cache is not source of truth)
- SDK automatically attempts reconnection

### Q: How long until cache hit rate stabilizes?

**A**: Typically:
- 15 minutes: 50% hit rate (frequently accessed tasks cached)
- 1 hour: 80% hit rate (most active tasks cached)
- 24 hours: 85%+ hit rate (comparable to legacy)

### Q: Can we run S3 and Redis simultaneously?

**A**: No. Per ADR-0025, big-bang cutover with no dual-read. This avoids:
- Complex dual-read logic
- Potential data inconsistency
- Extended tech debt

### Q: What about struc caching?

**A**: Struc caching uses the same Redis backend with composite keys:
```
asana:struc:{task_gid}:{project_gid}
```
Migration is automatic when using SDK cache methods.

### Q: How do we decommission S3 cache?

**A**: After T+7 days with stable Redis:
1. Disable S3 cache writes (remove code)
2. Monitor for 1 week with no S3 writes
3. Archive S3 bucket (optional)
4. Delete S3 bucket (final)

### Q: What's the 25-second TTL for?

**A**: Per ADR-0018, modification checks are cached in-memory for 25 seconds to prevent spamming Asana's batch API. This is separate from Redis TTL:
- **In-memory 25s TTL**: Modification timestamp checks
- **Redis 300s TTL**: Full task data

---

## Support

For issues during migration:

1. Check SDK documentation: `autom8_asana/docs/`
2. Review ADR-0025 for architecture decisions
3. Check Redis connection with `check_redis_health()`
4. Review SDK metrics for anomalies
