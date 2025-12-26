# ADR-0024: Thread-Safety Guarantees

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md), [ADR-0017](ADR-0017-redis-backend-architecture.md)

## Context

The autom8_asana SDK is used in concurrent environments:
- Multi-threaded web servers (FastAPI, Django)
- Async event loops with concurrent tasks
- Background workers processing multiple items
- ECS tasks with multiple threads

Concurrent access to cache creates race conditions:

**Race condition example**:
```
Thread A                    Thread B                    Redis
    |                           |                         |
    | GET task:123              |                         |
    |-------------------------------------------------->  |
    |                           | GET task:123            |
    |                           |------------------------>|
    | <-- {version: 1}          |                         |
    |                           | <-- {version: 1}        |
    | Update task               |                         |
    | SET task:123 {v:2}        | Update task             |
    |-------------------------------------------------->  |
    |                           | SET task:123 {v:2}      |
    |                           |------------------------>|
    |                           |                         |
    | OK                        | OK                      |
    |                           |                         |
    # Both threads think they updated successfully
    # But one update was lost!
```

**Requirements**:
- FR-CACHE-014: Use WATCH/MULTI for atomic read-modify-write
- FR-CACHE-040: Thread-safe lock for in-memory batch check cache
- NFR-REL-005: Zero race conditions

## Decision

**Use Redis WATCH/MULTI for atomic cache updates and per-operation connections from a pool for thread safety. Use threading.Lock for in-memory caches.**

### Redis WATCH/MULTI Pattern

```python
import redis


class RedisCacheProvider:
    """Thread-safe Redis cache provider using connection pooling."""

    def __init__(self, config: RedisConfig) -> None:
        self._pool = redis.ConnectionPool(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
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
        """Atomically update a cache entry using optimistic locking.

        Uses Redis WATCH/MULTI to detect concurrent modifications.
        Retries on conflict up to max_retries times.
        """
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

    async def set_versioned(
        self,
        key: str,
        entry: CacheEntry,
    ) -> None:
        """Set cache entry atomically.

        For simple writes (not read-modify-write), WATCH is not needed.
        Each operation uses its own connection from the pool.
        """
        redis_key = self._make_key(key, entry.entry_type)
        conn = self._get_connection()
        try:
            pipe = conn.pipeline()
            pipe.hset(redis_key, mapping=self._serialize(entry))
            if entry.ttl:
                pipe.expire(redis_key, entry.ttl)
            pipe.execute()
        finally:
            conn.close()
```

### Connection Pool Configuration

```python
@dataclass
class RedisConfig:
    """Redis connection configuration."""
    max_connections: int = 10  # Pool size

    # Each operation gets its own connection from the pool.
    # Pool handles connection reuse and cleanup.
    # max_connections should >= expected concurrent operations.
```

### In-Memory Cache Thread Safety

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

    def _record_check(self, gid: str, is_fresh: bool) -> None:
        """Thread-safe record of check result."""
        with self._lock:
            self._check_cache[gid] = (datetime.utcnow(), is_fresh)


class CacheMetrics:
    """Thread-safe metrics aggregator."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def record_hit(self) -> None:
        with self._lock:
            self._hits += 1

    def hit_rate(self) -> float:
        with self._lock:
            total = self._hits + self._misses
            return (self._hits / total * 100) if total > 0 else 0.0
```

### Async Context Safety

```python
import asyncio


class AsyncRedisCacheProvider:
    """Async-safe Redis cache provider."""

    def __init__(self, config: RedisConfig) -> None:
        # Use aioredis or redis.asyncio for async operations
        self._pool: redis.asyncio.ConnectionPool | None = None

    async def _get_pool(self) -> redis.asyncio.ConnectionPool:
        """Lazy initialization of async connection pool."""
        if self._pool is None:
            self._pool = redis.asyncio.ConnectionPool(
                host=self._config.host,
                port=self._config.port,
                max_connections=self._config.max_connections,
            )
        return self._pool

    async def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness = Freshness.EVENTUAL,
    ) -> CacheEntry | None:
        """Async-safe cache read."""
        pool = await self._get_pool()
        async with redis.asyncio.Redis(connection_pool=pool) as conn:
            data = await conn.hgetall(self._make_key(key, entry_type))
            return self._deserialize(data) if data else None
```

## Rationale

**Why WATCH/MULTI over client-side locking?**

Client-side locks (`threading.Lock`) only work within a single process:
```
# Doesn't work across processes/machines!
Process A (ECS Task 1)      Process B (ECS Task 2)
    |                           |
    | lock.acquire()            |
    | read from Redis           | lock.acquire() # Different lock!
    | ...                       | read from Redis
    | write to Redis            | write to Redis
    | lock.release()            | lock.release()
    |                           |
    # Race condition still possible!
```

Redis WATCH/MULTI provides optimistic locking across all clients:
```
Process A                   Process B                   Redis
    |                           |                         |
    | WATCH task:123            |                         |
    |                           | WATCH task:123          |
    | GET task:123              |                         |
    |                           | GET task:123            |
    | MULTI                     |                         |
    | SET task:123 ...          |                         |
    | EXEC                      |                         |
    | <-- OK                    |                         |
    |                           | MULTI                   |
    |                           | SET task:123 ...        |
    |                           | EXEC                    |
    |                           | <-- WatchError!         |
    |                           | (key changed since WATCH)|
    |                           | Retry...                |
```

**Why connection pooling?**

Creating new connections per operation is expensive:
- TCP handshake overhead
- TLS negotiation (if enabled)
- Redis AUTH command

Connection pooling:
- Reuses established connections
- Bounds maximum connections
- Handles connection lifecycle

**Why per-operation connections from pool?**

Each operation gets its own connection to prevent:
- WATCH state bleeding between operations
- Transaction state confusion
- Pipeline interference

```python
# Safe: each operation has isolated connection
async def operation_a():
    conn = pool.get_connection()
    conn.watch(key_a)
    # ...

async def operation_b():
    conn = pool.get_connection()  # Different connection!
    conn.watch(key_b)
    # ...
```

**Why threading.Lock for in-memory caches?**

In-memory caches (batch check, metrics) are process-local:
- Don't need distributed locking
- `threading.Lock` is sufficient
- Lower overhead than Redis operations
- Works in both sync and async (with care)

## Alternatives Considered

### Alternative 1: Client-Side Distributed Locking (Redlock)

- **Description**: Use Redlock algorithm for distributed mutex.
- **Pros**:
  - Familiar mutex pattern
  - Works across processes
  - Explicit lock/unlock
- **Cons**:
  - Complex implementation (Redlock correctness is debated)
  - Lock contention blocks all waiters
  - Dead locks possible if process crashes holding lock
  - Higher latency (acquire, hold, release)
- **Why not chosen**: WATCH/MULTI is simpler and sufficient for our use case. Optimistic locking (retry on conflict) is better than pessimistic locking (wait for lock) for cache operations.

### Alternative 2: No Locking (Accept Races)

- **Description**: Accept that race conditions may occur, rely on idempotent operations.
- **Pros**:
  - Simplest implementation
  - Maximum throughput
  - No lock overhead
- **Cons**:
  - Data corruption possible
  - Version tracking unreliable
  - Violates NFR-REL-005 (zero race conditions)
- **Why not chosen**: Cache consistency is a requirement. Stale data or lost updates are unacceptable.

### Alternative 3: Single-Threaded Event Loop

- **Description**: Process all cache operations on single thread.
- **Pros**:
  - No concurrency issues
  - Simple reasoning
  - Works for async (one event loop)
- **Cons**:
  - Doesn't help with multi-process deployments
  - Bottleneck for throughput
  - Doesn't match async SDK design
- **Why not chosen**: SDK is designed for concurrent use. Single-threading defeats purpose.

### Alternative 4: Lua Scripts for Atomicity

- **Description**: Use Redis Lua scripts for atomic operations.
- **Pros**:
  - True atomicity (script runs without interruption)
  - Single round trip
  - Complex logic in script
- **Cons**:
  - Lua complexity
  - Script management overhead
  - Debugging difficulty
  - Overkill for simple get/set operations
- **Why not chosen**: WATCH/MULTI is sufficient for our patterns. Lua scripts reserved for more complex atomic operations if needed later.

### Alternative 5: asyncio.Lock for In-Memory

- **Description**: Use asyncio.Lock instead of threading.Lock for in-memory caches.
- **Pros**:
  - Native async support
  - No blocking
  - Consistent with async codebase
- **Cons**:
  - Only works within one event loop
  - threading.Lock works in both sync and async contexts
  - CacheMetrics used from sync code too
- **Why not chosen**: threading.Lock is more universal. Works in sync wrappers and async contexts.

## Consequences

### Positive

- **Race-free updates**: WATCH/MULTI prevents lost updates
- **Cross-process safety**: Works across ECS tasks, Lambda invocations
- **Efficient pooling**: Connection reuse reduces overhead
- **Simple in-memory locking**: threading.Lock for local caches
- **Retry on conflict**: Optimistic locking recovers from contention

### Negative

- **Retry overhead**: Conflicts require retry (rare in practice)
- **Pool sizing**: Must tune max_connections for workload
- **Connection per operation**: Slightly higher connection churn
- **Lock contention**: In-memory locks can block threads

### Neutral

- **max_retries configurable**: Default 3 retries for WATCH conflicts
- **Pool managed by redis-py**: Standard library handles lifecycle
- **Error on max retries**: Raises ConcurrentModificationError

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - Read-modify-write operations use WATCH/MULTI
   - Simple writes use pipelined HSET + EXPIRE
   - In-memory caches use threading.Lock
   - Connections obtained from pool, not created directly

2. **Testing requirements**:
   - Concurrent access tests with multiple threads
   - WATCH conflict simulation and retry verification
   - Pool exhaustion handling

3. **Configuration guidelines**:
   - `max_connections` >= expected concurrent operations
   - `max_retries` tuned for contention level
   - Monitor pool usage metrics

4. **Error handling**:
   - ConcurrentModificationError for exhausted retries
   - Log warnings on retries
   - Track retry rates in metrics
