# Cache Provider Protocol Reference

## Overview

The `CacheProvider` protocol defines the interface contract for cache implementations in the autom8_asana SDK. This abstraction allows swapping cache backends (Redis, S3, in-memory) without changing client code.

**Purpose**: Standardize cache integration across all resource clients (tasks, projects, etc.).

**Key Principle**: Protocol defines behavior contract, implementations provide specific backend logic.

## Protocol Definition

### Core Interface

```python
from typing import Protocol, Optional, TypeVar, Dict, List
from datetime import datetime

T = TypeVar('T')


class CacheProvider(Protocol):
    """Protocol for cache provider implementations.

    Implementations must provide:
    - get/set operations for single entries
    - get_multi/set_multi for batch operations
    - delete/clear for cache invalidation
    - exists for cache presence checks
    """

    async def get(
        self,
        key: str,
        default: Optional[T] = None
    ) -> Optional[T]:
        """Get cached value by key.

        Args:
            key: Cache key (e.g., "task:1234567890123456")
            default: Value to return if key not found

        Returns:
            Cached value if exists and not expired, else default
        """
        ...

    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None
    ) -> None:
        """Set cached value with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (must be serializable)
            ttl: Time-to-live in seconds (None = use default)
        """
        ...

    async def delete(self, key: str) -> None:
        """Delete cached value by key.

        Args:
            key: Cache key to delete
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists (even if expired), False otherwise
        """
        ...

    async def get_multi(
        self,
        keys: List[str]
    ) -> Dict[str, T]:
        """Batch get operation for multiple keys.

        Args:
            keys: List of cache keys to retrieve

        Returns:
            Dict mapping key → value for keys that exist
            Missing or expired keys are excluded from result
        """
        ...

    async def set_multi(
        self,
        items: Dict[str, T],
        ttl: Optional[int] = None
    ) -> None:
        """Batch set operation for multiple key-value pairs.

        Args:
            items: Dict mapping cache key → value
            ttl: Time-to-live in seconds for all items
        """
        ...

    async def clear(self) -> None:
        """Clear all cached entries.

        Warning: Use with caution. Clears entire cache.
        """
        ...
```

### Extension Methods (Optional)

Implementations may provide additional methods for advanced functionality:

```python
class ExtendedCacheProvider(CacheProvider):
    """Extended cache provider with additional capabilities."""

    async def get_with_metadata(
        self,
        key: str
    ) -> Optional[tuple[T, dict]]:
        """Get value with metadata (created_at, ttl, etc.).

        Returns:
            Tuple of (value, metadata) if exists, else None
        """
        ...

    async def set_if_not_exists(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value only if key doesn't exist (atomic).

        Returns:
            True if value was set, False if key already existed
        """
        ...

    async def increment(
        self,
        key: str,
        delta: int = 1
    ) -> int:
        """Atomically increment numeric value.

        Args:
            key: Cache key
            delta: Amount to increment (default 1)

        Returns:
            New value after increment
        """
        ...

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key.

        Returns:
            Remaining seconds until expiration, or None if no TTL
        """
        ...

    async def update_ttl(
        self,
        key: str,
        ttl: int
    ) -> None:
        """Update TTL without changing value.

        Args:
            key: Cache key
            ttl: New TTL in seconds
        """
        ...
```

## Integration Patterns

### Client Cache Pattern

**Pattern** (from ADR-0124): Integrate `CacheProvider` into resource clients.

```python
class TaskClient:
    """Task resource client with caching."""

    def __init__(
        self,
        api_client: AsanaClient,
        cache_provider: Optional[CacheProvider] = None,
    ):
        self.api = api_client
        self.cache = cache_provider

    async def get_task(
        self,
        gid: str,
        freshness: Freshness = Freshness.EVENTUAL,
    ) -> Task:
        """Get task with cache support.

        Args:
            gid: Task GID
            freshness: EVENTUAL (trust cache) or STRICT (validate)

        Returns:
            Task object
        """
        # Construct cache key
        cache_key = f"task:{gid}"

        # Check cache if provider available
        if self.cache:
            cached = await self.cache.get(cache_key)

            if cached:
                # Cache hit
                if freshness == Freshness.EVENTUAL:
                    return Task.from_dict(cached)

                # STRICT mode: validate freshness
                if await self._is_fresh(cached, gid):
                    return Task.from_dict(cached)

        # Cache miss or stale: fetch from API
        task_data = await self.api.tasks.get_task(gid)
        task = Task.from_dict(task_data)

        # Populate cache
        if self.cache:
            await self.cache.set(
                cache_key,
                task_data,
                ttl=3600  # 1 hour for tasks
            )

        return task

    async def _is_fresh(self, cached_data: dict, gid: str) -> bool:
        """Check if cached data is fresh."""
        # Lightweight staleness check
        current_modified_at = await self.api.tasks.get_task(
            gid,
            opt_fields=["modified_at"]
        )

        return cached_data["modified_at"] == current_modified_at["modified_at"]
```

### Post-Commit Hook Pattern

**Pattern**: Invalidate cache after write operations.

```python
class TaskClient:
    async def update_task(
        self,
        gid: str,
        data: dict
    ) -> Task:
        """Update task and invalidate cache.

        Args:
            gid: Task GID
            data: Update payload

        Returns:
            Updated task
        """
        # Update via API
        updated_task_data = await self.api.tasks.update_task(gid, data)

        # Invalidate cache (post-commit hook)
        if self.cache:
            cache_key = f"task:{gid}"
            await self.cache.delete(cache_key)

            # Optionally: repopulate with fresh data
            await self.cache.set(
                cache_key,
                updated_task_data,
                ttl=3600
            )

        return Task.from_dict(updated_task_data)
```

### Batch Population Pattern

**Pattern**: Efficiently populate cache for multiple entities.

```python
class TaskClient:
    async def get_tasks_for_project(
        self,
        project_gid: str,
    ) -> List[Task]:
        """Get all tasks in project with batch caching.

        Args:
            project_gid: Project GID

        Returns:
            List of tasks
        """
        # Fetch from API
        task_data_list = await self.api.tasks.get_tasks(
            project=project_gid
        )

        # Batch populate cache
        if self.cache:
            cache_items = {
                f"task:{task['gid']}": task
                for task in task_data_list
            }

            await self.cache.set_multi(
                cache_items,
                ttl=3600
            )

        return [Task.from_dict(data) for data in task_data_list]
```

### Graceful Degradation Pattern

**Pattern** (from ADR-0127): Handle cache failures gracefully.

```python
class TaskClient:
    async def get_task(self, gid: str) -> Task:
        """Get task with graceful cache degradation."""
        cache_key = f"task:{gid}"

        # Try cache first
        if self.cache:
            try:
                cached = await self.cache.get(cache_key)
                if cached:
                    return Task.from_dict(cached)
            except Exception as e:
                # Cache error: log and continue
                logger.warning(
                    f"Cache read failed for {gid}: {e}. "
                    "Falling back to API."
                )
                # Continue to API fetch

        # Fetch from API (cache miss or error)
        task_data = await self.api.tasks.get_task(gid)
        task = Task.from_dict(task_data)

        # Try to populate cache (best effort)
        if self.cache:
            try:
                await self.cache.set(cache_key, task_data, ttl=3600)
            except Exception as e:
                # Cache write failed: log but don't fail request
                logger.warning(f"Cache write failed for {gid}: {e}")

        return task
```

## Implementation Examples

### Minimal CacheProvider (In-Memory)

```python
class InMemoryCacheProvider:
    """Simple in-memory cache implementation."""

    def __init__(self):
        self._store: Dict[str, tuple[Any, datetime, int]] = {}

    async def get(self, key: str, default=None):
        entry = self._store.get(key)
        if not entry:
            return default

        value, created_at, ttl = entry

        # Check expiration
        if ttl and (datetime.now() - created_at).total_seconds() > ttl:
            del self._store[key]
            return default

        return value

    async def set(self, key: str, value, ttl=None):
        self._store[key] = (value, datetime.now(), ttl)

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_multi(self, items: Dict[str, Any], ttl=None):
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def clear(self):
        self._store.clear()
```

### Redis CacheProvider

```python
import redis.asyncio as aioredis
import json


class RedisCacheProvider:
    """Redis-backed cache implementation."""

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)

    async def get(self, key: str, default=None):
        value = await self.redis.get(key)
        if value is None:
            return default
        return json.loads(value)

    async def set(self, key: str, value, ttl=None):
        serialized = json.dumps(value)
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0

    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        if not keys:
            return {}

        values = await self.redis.mget(keys)
        result = {}

        for key, value in zip(keys, values):
            if value is not None:
                result[key] = json.loads(value)

        return result

    async def set_multi(self, items: Dict[str, Any], ttl=None):
        pipe = self.redis.pipeline()

        for key, value in items.items():
            serialized = json.dumps(value)
            if ttl:
                pipe.setex(key, ttl, serialized)
            else:
                pipe.set(key, serialized)

        await pipe.execute()

    async def clear(self):
        await self.redis.flushdb()
```

### With Staleness Detection

```python
class StalenessAwareCacheProvider:
    """Cache provider with built-in staleness detection."""

    def __init__(
        self,
        base_provider: CacheProvider,
        api_client: AsanaClient,
    ):
        self.cache = base_provider
        self.api = api_client

    async def get(
        self,
        key: str,
        freshness: Freshness = Freshness.EVENTUAL,
        default=None,
    ):
        # Get from cache
        entry = await self.cache.get(key)
        if not entry:
            return default

        # EVENTUAL mode: trust cache
        if freshness == Freshness.EVENTUAL:
            return entry["data"]

        # STRICT mode: validate staleness
        entity_type, gid = key.split(":")
        current_modified_at = await self._fetch_modified_at(entity_type, gid)

        if current_modified_at is None:
            # Entity deleted
            await self.cache.delete(key)
            return default

        cached_modified_at = entry.get("modified_at")
        if current_modified_at > cached_modified_at:
            # Stale: invalidate
            await self.cache.delete(key)
            return default

        # Fresh: return cached data
        return entry["data"]

    async def _fetch_modified_at(
        self,
        entity_type: str,
        gid: str,
    ) -> Optional[datetime]:
        """Fetch current modified_at from API."""
        if entity_type == "task":
            task = await self.api.tasks.get_task(
                gid,
                opt_fields=["modified_at"]
            )
            return task.get("modified_at")

        # Add other entity types as needed
        return None
```

## Cache Key Conventions

### Entity Keys

**Format**: `{entity_type}:{gid}`

**Examples**:
- `task:1234567890123456` - Task entity
- `project:9876543210987654` - Project entity
- `user:1111111111111111` - User entity

**Rationale**: Namespace by entity type to avoid key collisions.

### Collection Keys

**Format**: `{entity_type}:collection:{scope}:{scope_id}`

**Examples**:
- `task:collection:project:9876543210987654` - All tasks in project
- `subtask:collection:task:1234567890123456` - All subtasks of task
- `project:collection:workspace:5555555555555555` - All projects in workspace

**Rationale**: Distinguish collections from individual entities.

### Custom Keys

**Format**: Application-specific, but follow patterns:
- Use colons `:` as namespace separators
- Include entity type prefix for clarity
- Include scope identifiers for collections

**Examples**:
- `detection:result:1234567890123456` - Detection result for task
- `hierarchy:task:1234567890123456` - Full hierarchy for task
- `batch:tasks:request:abc123` - Batch request result

## Error Handling

### Graceful Degradation

**Principle** (from ADR-0127): Cache failures should not break application functionality.

**Implementation**:
1. Wrap all cache operations in try-except
2. Log cache errors but continue
3. Fall back to API on cache failure
4. Best-effort cache population (don't fail on write errors)

```python
async def get_with_fallback(
    cache: CacheProvider,
    key: str,
    fetch_fn: Callable[[], Awaitable[T]],
) -> T:
    """Get from cache with fallback to fetch function."""
    # Try cache
    try:
        cached = await cache.get(key)
        if cached:
            return cached
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")

    # Fetch from source
    value = await fetch_fn()

    # Try to populate cache (best effort)
    try:
        await cache.set(key, value)
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")

    return value
```

### Fallback Strategies

| Cache Error | Strategy | Rationale |
|-------------|----------|-----------|
| Redis connection failure | Bypass cache, use API | Maintain service availability |
| Serialization error | Skip cache, log error | Data structure may be incompatible |
| Cache unavailable | Operate without cache | Graceful degradation |
| Key not found | Fetch from API | Normal cache miss |
| TTL expired | Fetch from API | Normal expiration |

## Performance Considerations

### Serialization

**Challenge**: Python objects must be serialized to store in cache.

**Options**:

| Method | Pros | Cons | Use Case |
|--------|------|------|----------|
| JSON | Human-readable, universal | Slower, no datetime support | General purpose |
| Pickle | Native Python, fast | Not human-readable, security risk | Internal use only |
| MessagePack | Fast, compact | Binary format | High-throughput systems |
| Protocol Buffers | Strongly-typed, efficient | Requires schema | Cross-service caching |

**Recommendation**: Use JSON for simplicity and compatibility.

```python
import json


async def set(self, key: str, value, ttl=None):
    serialized = json.dumps(value, default=str)  # Handle datetime
    await self.redis.set(key, serialized)
```

### Batch Operations

**When to use `get_multi` vs. individual `get`**:

| Scenario | Use | Rationale |
|----------|-----|-----------|
| Fetching 1-2 keys | Individual `get` | Overhead of batch not worth it |
| Fetching 3-10 keys | `get_multi` | Reduces round trips |
| Fetching 10+ keys | `get_multi` with chunking | Batch operations more efficient |
| Keys needed sequentially | Individual `get` | Don't fetch unnecessary data |
| Keys needed in parallel | `get_multi` | Single network round trip |

**Batch size limits**: Redis has no hard limit, but keep batches < 1000 keys for manageable network payload.

## Related Documentation

- [ADR-0123: Cache Provider Selection](../decisions/ADR-0123-cache-provider-selection.md) - Why CacheProvider protocol chosen
- [ADR-0124: Client Cache Pattern](../decisions/ADR-0124-client-cache-pattern.md) - Integration pattern
- [ADR-0127: Graceful Degradation](../decisions/ADR-0127-graceful-degradation.md) - Error handling strategy
- [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md) - Staleness algorithms
- [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md) - TTL calculation
- [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md) - Cache requirements
- [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md) - Implementation details
- [RUNBOOK-cache-troubleshooting.md](../runbooks/RUNBOOK-cache-troubleshooting.md) - Operational troubleshooting
