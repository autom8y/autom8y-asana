# Cache Troubleshooting Runbook

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| High cache miss rate | TTL too short, invalidation too aggressive | [Cache Misses](#problem-1-cache-misses) |
| Stale data served | Staleness detection disabled, TTL too long | [Stale Data](#problem-2-stale-data) |
| Cache errors in logs | Redis connection issues, serialization failures | [Cache Errors](#problem-3-cache-errors) |
| Slow API calls despite cache | Cache not being populated, key mismatch | [Cache Not Working](#problem-4-cache-not-working) |

## Problem 1: Cache Misses

### Symptoms
- Metrics show high miss rate (>50%)
- API latency increased
- Logs show "cache miss" frequently
- Performance degraded compared to baseline

### Investigation Steps

1. **Check cache hit rate metrics**
   ```bash
   # If using Redis
   redis-cli INFO stats
   # Look for: keyspace_hits, keyspace_misses
   # Calculate: hit_rate = hits / (hits + misses)
   ```

2. **Check TTL configuration**
   ```python
   # In code or config
   # Expected base TTLs:
   # - Task: 3600s (1 hour)
   # - Project: 7200s (2 hours)
   # - Portfolio: 14400s (4 hours)
   ```

3. **Check cache key consistency**
   ```bash
   # Redis CLI
   KEYS task:*
   # Verify expected keys exist
   # Pattern should be: {entity_type}:{gid}
   ```

4. **Check invalidation strategy**
   - Review logs for cache.delete() calls
   - Look for post-commit invalidation hooks
   - Check if invalidation scope too broad

### Resolution

**If TTL too short**:
- Increase base TTL for entity type (see [REF-cache-ttl-strategy](../reference/REF-cache-ttl-strategy.md))
- Enable progressive TTL extension for stable entities
- Monitor staleness to ensure data still fresh

**If key mismatch**:
- Fix cache key generation to match pattern: `{entity_type}:{gid}`
- Clear cache and repopulate: `redis-cli FLUSHDB` (WARNING: clears all data)
- Verify client code constructs keys correctly

**If over-invalidation**:
- Review invalidation hooks (post-commit, webhook handlers)
- Reduce invalidation scope (only invalidate changed entity, not collections)
- Consider watermark-based staleness instead of invalidation

### Prevention
- Monitor cache hit rate (alert if <70%)
- Set TTL based on entity change frequency analysis
- Use progressive TTL for stable entity types
- Log cache key generation in debug mode

## Problem 2: Stale Data

### Symptoms
- Users report seeing outdated data
- Entity changes not reflected immediately
- Staleness detection logs show stale hits
- Data inconsistencies between cache and API

### Investigation Steps

1. **Check when data was last updated**
   ```bash
   # Redis CLI
   TTL task:1234567890123456
   # If high TTL remaining, may be serving stale data

   GET task:1234567890123456
   # Check modified_at timestamp in cached data
   ```

2. **Check staleness detection configuration**
   ```python
   # Is staleness detection enabled?
   # Check Freshness mode: STRICT (validates) or EVENTUAL (trusts cache)
   freshness = Freshness.STRICT  # Expected for critical data
   ```

3. **Verify cache invalidation on writes**
   - Check logs for cache.delete() after update operations
   - Verify post-commit hooks fire correctly
   - Test: update entity via API, check if cache invalidated

4. **Compare cached vs. API data**
   ```python
   # Compare modified_at timestamps
   cached_data = await cache.get("task:123")
   api_data = await client.tasks.get_task("123")

   print(f"Cached modified_at: {cached_data['modified_at']}")
   print(f"API modified_at: {api_data['modified_at']}")
   ```

### Resolution

**If staleness detection disabled**:
- Enable lightweight staleness checks in STRICT mode
- See [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md)
- Use `freshness=Freshness.STRICT` for critical operations

**If TTL too long**:
- Reduce base TTL for frequently-changing entities
- Use watermark-based staleness for collections
- Enable progressive TTL reset on entity change

**If invalidation missing**:
- Add post-commit invalidation hook:
  ```python
  async def update_task(self, gid, data):
      result = await self.api.update_task(gid, data)
      await self.cache.delete(f"task:{gid}")  # Invalidate
      return result
  ```
- See [ADR-0117](../decisions/ADR-0117-post-commit-invalidation-hook.md) for pattern

**If clock skew**:
- Verify server and client times aligned
- Use API-provided timestamps, not client time
- Check for timezone issues in datetime comparison

### Prevention
- Enable staleness detection for critical data paths
- Set appropriate TTL based on entity volatility
- Monitor staleness metrics (log when stale data detected)
- Add alerts for staleness rate >1%

## Problem 3: Cache Errors

### Symptoms
- Exceptions in logs: `CacheError`, `ConnectionError`, `SerializationError`
- Cache operations failing but API fallback working
- Intermittent errors on cache access
- Redis/cache backend health degraded

### Investigation Steps

1. **Check cache backend connectivity**
   ```bash
   # Redis
   redis-cli PING
   # Should return: PONG

   # Check connection from application server
   telnet redis-host 6379
   ```

2. **Check application logs for error details**
   ```bash
   grep "CacheError\|ConnectionError\|SerializationError" application.log | tail -50
   # Look for patterns: specific keys, entity types, operations
   ```

3. **Check serialization issues**
   - Review error stack trace for serialization failures
   - Check if data structure changed (new fields, types)
   - Verify JSON serialization compatibility

4. **Check Redis server health**
   ```bash
   redis-cli INFO server
   redis-cli INFO memory
   # Look for: used_memory, maxmemory, eviction policy
   ```

### Resolution

**If Redis unavailable**:
- Check Redis server status: `systemctl status redis`
- Verify network connectivity between app and Redis
- Check firewall rules and security groups
- Verify Redis authentication credentials
- Graceful degradation should be active (see [ADR-0127](../decisions/ADR-0127-graceful-degradation.md))

**If serialization error**:
- Identify problematic data type in error message
- Ensure all cached objects are JSON-serializable
- Add custom JSON encoder for datetime/special types:
  ```python
  json.dumps(value, default=str)  # Handle datetime
  ```
- Clear specific problematic key: `redis-cli DEL {key}`

**If memory pressure**:
- Check Redis memory usage: `redis-cli INFO memory`
- Review eviction policy (should be `allkeys-lru` for cache)
- Increase Redis max memory or optimize cache usage
- Reduce TTLs to expire data faster

**If connection pool exhausted**:
- Increase Redis connection pool size
- Check for connection leaks (connections not released)
- Review async client initialization

### Prevention
- Monitor Redis health metrics (memory, connections, ops/sec)
- Alert on cache error rate >1%
- Test serialization for new entity types before deployment
- Implement graceful degradation (always fall back to API)

## Problem 4: Cache Not Working

### Symptoms
- Cache appears healthy (no errors)
- API calls slow despite cache being enabled
- No cache hits in metrics (hit rate = 0%)
- Expected performance improvement not seen

### Investigation Steps

1. **Check if cache is wired into client code**
   ```python
   # Verify CacheProvider passed to client
   task_client = TaskClient(api_client, cache_provider=cache)
   # Check: is cache_provider None?

   print(f"Cache provider: {task_client.cache}")  # Should not be None
   ```

2. **Check cache key generation**
   ```python
   # Log generated cache keys
   cache_key = f"{entity_type}:{gid}"
   logger.debug(f"Cache key: {cache_key}")

   # Verify keys exist in Redis
   # redis-cli KEYS task:*
   ```

3. **Check cache population**
   - Review code: is `cache.set()` called after API fetch?
   - Check logs for "cache populated" messages
   - Manually verify: fetch entity, then check Redis for key

4. **Check cache reads**
   - Add logging before `cache.get()` calls
   - Verify cache.get() actually called in code path
   - Check if cache reads short-circuited by logic error

### Resolution

**If cache not wired**:
- Integrate CacheProvider into client initialization:
  ```python
  cache = RedisCacheProvider(redis_url)
  task_client = TaskClient(api_client, cache_provider=cache)
  ```
- Follow [REF-cache-provider-protocol](../reference/REF-cache-provider-protocol.md)
- Use client cache pattern ([ADR-0124](../decisions/ADR-0124-client-cache-pattern.md))

**If cache not populated**:
- Add `cache.set()` after successful API fetch:
  ```python
  task = await self.api.tasks.get_task(gid)
  await self.cache.set(f"task:{gid}", task, ttl=3600)
  ```
- Use batch population for collections:
  ```python
  tasks = await self.api.tasks.get_tasks(project=project_gid)
  await self.cache.set_multi(
      {f"task:{t['gid']}": t for t in tasks},
      ttl=3600
  )
  ```

**If logic prevents cache use**:
- Review conditional logic around cache access
- Check for flags that disable caching
- Verify environment variables (e.g., `CACHE_ENABLED=true`)

**If configuration issue**:
- Verify Redis URL correct: `redis://localhost:6379/0`
- Check environment-specific configs (dev vs. prod)
- Validate cache provider initialization

### Prevention
- Add cache integration tests for new clients
- Monitor cache population rate (keys added per minute)
- Log cache hits/misses at INFO level during development
- Add health check endpoint that tests cache connectivity

## Emergency Procedures

### Clear Entire Cache

**WARNING**: This clears ALL cached data. Cache will rebuild gradually.

```bash
# Redis CLI
redis-cli FLUSHDB

# Or from Python
await cache.clear()
```

**When to use**:
- Systematic cache corruption
- Schema change requires cache rebuild
- Testing cache population logic

**Impact**:
- All cache misses for ~30 minutes (cache warmup period)
- Increased API load during rebuild
- Temporary performance degradation

### Disable Cache (Emergency Fallback)

**When cache backend completely down**:

```python
# In config or environment
CACHE_ENABLED = False

# Or in code
task_client = TaskClient(api_client, cache_provider=None)
```

**Impact**:
- All requests hit API directly
- Increased latency (~200ms per call)
- Increased API quota consumption
- No cache-related errors

**Recovery**:
1. Fix cache backend issue
2. Re-enable caching
3. Monitor cache population
4. Verify cache hit rate returns to normal

### Force Cache Refresh

**Refresh specific entity without waiting for TTL**:

```bash
# Delete stale entry
redis-cli DEL task:1234567890123456

# Next access will fetch from API and repopulate
```

**For collection**:

```bash
# Delete all tasks in project
redis-cli KEYS "task:collection:project:*" | xargs redis-cli DEL
```

## Related Documentation

- [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md) - Cache architecture and implementation
- [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md) - Staleness detection algorithms
- [REF-cache-ttl-strategy](../reference/REF-cache-ttl-strategy.md) - TTL calculation and tuning
- [REF-cache-provider-protocol](../reference/REF-cache-provider-protocol.md) - Cache provider interface
- [ADR-0127: Graceful Degradation](../decisions/ADR-0127-graceful-degradation.md) - Error handling strategy
- [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md) - Cache requirements
