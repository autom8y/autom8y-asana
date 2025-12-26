# ADR-0124: Client Cache Integration Pattern

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-22
- **Deciders**: SDK Team
- **Related**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md), [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md), ADR-0123, ADR-0021

## Context

The `TasksClient.get_async()` method currently always makes an HTTP request to the Asana API:

```python
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    validate_gid(task_gid, "task_gid")
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/tasks/{task_gid}", params=params)  # Always HTTP
    if raw:
        return data
    task = Task.model_validate(data)
    task._client = self._client
    return task
```

With cache infrastructure now being activated (ADR-0123), we need to integrate cache checking into this method. The pattern must:
- Check cache before making HTTP requests
- Store responses in cache on miss
- Handle both `raw=True` (dict) and `raw=False` (Task model) returns
- Support entity-type-specific TTLs
- Degrade gracefully on cache errors (per NFR-DEGRADE-*)

**The key question**: What pattern should we use to integrate cache logic into client methods?

Forces at play:
- Caching logic should be reusable across multiple client methods (get_async, future subtasks_async, etc.)
- Cache errors must not propagate to callers
- Performance overhead must be minimal (<10ms per call)
- Code readability should not suffer
- Type hints and IDE support must be preserved
- Pattern should be consistent with existing SDK patterns

## Decision

We will use **inline check with helper methods in BaseClient**:

```python
class BaseClient:
    """Base class with reusable cache helper methods."""

    def _cache_get(self, key: str, entry_type: EntryType) -> CacheEntry | None:
        """Check cache with graceful degradation."""
        if self._cache is None:
            return None
        try:
            entry = self._cache.get_versioned(key, entry_type)
            if entry and not entry.is_expired():
                return entry
            return None
        except Exception as exc:
            logger.warning("Cache get failed: %s", exc)
            return None

    def _cache_set(self, key: str, data: dict, entry_type: EntryType, ttl: int | None = None) -> None:
        """Store in cache with graceful degradation."""
        if self._cache is None:
            return
        try:
            entry = CacheEntry(key=key, data=data, entry_type=entry_type, ...)
            self._cache.set_versioned(key, entry)
        except Exception as exc:
            logger.warning("Cache set failed: %s", exc)

    def _cache_invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        """Invalidate cache with graceful degradation."""
        ...
```

Integration in `TasksClient.get_async()`:

```python
class TasksClient(BaseClient):
    async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
        validate_gid(task_gid, "task_gid")

        # Check cache first
        cached_entry = self._cache_get(task_gid, EntryType.TASK)
        if cached_entry is not None:
            data = cached_entry.data
            if raw:
                return data
            task = Task.model_validate(data)
            task._client = self._client
            return task

        # Cache miss: fetch from API
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/tasks/{task_gid}", params=params)

        # Store in cache
        ttl = self._resolve_entity_ttl(data)
        self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)

        if raw:
            return data
        task = Task.model_validate(data)
        task._client = self._client
        return task
```

## Rationale

### Why Inline Check Over Alternatives?

| Criterion | Decorator | Middleware | **Inline + Helpers** |
|-----------|-----------|------------|----------------------|
| Readability | Medium | Low | **High** |
| Reusability | High | High | **High** |
| Type preservation | Poor | Medium | **Good** |
| Debug clarity | Poor | Poor | **Good** |
| Performance | Medium | Medium | **Best** |
| Flexibility | Low | Low | **High** |

### Why Helper Methods in BaseClient?

1. **Reusability**: `_cache_get`, `_cache_set`, `_cache_invalidate` can be used by any client (Tasks, Projects, Sections, etc.)

2. **Encapsulated error handling**: Graceful degradation logic is written once, not repeated in every method.

3. **Consistent interface**: All clients use the same pattern, making the codebase predictable.

4. **Testability**: Helpers can be mocked independently for unit testing.

### Why Not Abstract Away the Cache Check Entirely?

We considered hiding cache logic completely:

```python
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    data = await self._get_with_cache(f"/tasks/{task_gid}", task_gid, EntryType.TASK)
    # ... process data
```

We rejected this because:
- Different methods need different cache key strategies (GID vs parent+GID for subtasks)
- TTL resolution varies by entity type
- Some methods may not be cacheable (list_async with pagination)
- Explicit cache check makes caching behavior visible in code review

### Why Explicit TTL Resolution?

The `_resolve_entity_ttl(data)` method allows entity-type-specific TTLs:

```python
def _resolve_entity_ttl(self, data: dict[str, Any]) -> int:
    entity_type = self._detect_entity_type(data)
    if entity_type == "business":
        return 3600  # 1 hour
    elif entity_type == "process":
        return 60    # 1 minute
    # ... etc
    return 300  # default
```

This addresses FR-TTL-001 through FR-TTL-007 requirements for entity-type-specific caching.

### Why Check `entry.is_expired()` in Helper?

Cache providers handle TTL internally, but the helper double-checks expiration for consistency:

```python
entry = self._cache.get_versioned(key, entry_type)
if entry and not entry.is_expired():
    return entry
```

This ensures expired entries are never returned, even if the provider has clock skew or delayed eviction.

## Alternatives Considered

### Alternative 1: Decorator Pattern

- **Description**: Create a `@cached` decorator that wraps methods:
  ```python
  @cached(entry_type=EntryType.TASK, key_arg="task_gid")
  async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
      # Original implementation without cache
  ```
- **Pros**:
  - Clean separation of concerns
  - Declarative caching configuration
  - No changes to method body
- **Cons**:
  - Decorators wrap functions, complicating stack traces
  - `raw=True` handling requires special logic in decorator
  - Type hints may be lost or require workarounds
  - Harder to customize TTL per response
  - Different cache key strategies hard to express
- **Why not chosen**: The `raw` parameter and entity-type TTL resolution require access to method internals that decorators can't cleanly provide.

### Alternative 2: Middleware/Interceptor

- **Description**: Add a caching middleware layer between client and HTTP:
  ```python
  class CachingMiddleware:
      async def intercept(self, request, next):
          cached = self._cache.get(request.url)
          if cached:
              return cached
          response = await next(request)
          self._cache.set(request.url, response)
          return response
  ```
- **Pros**:
  - Transparent to client code
  - Works for all HTTP calls automatically
  - Centralized cache logic
- **Cons**:
  - URL-based keys don't capture semantic meaning (GID vs URL)
  - All requests get same caching behavior
  - Cannot distinguish raw vs model returns
  - Harder to implement entity-type TTLs
  - Intercepts requests that shouldn't be cached (POST, PUT)
- **Why not chosen**: HTTP-level caching is too coarse-grained. We need task-level caching with GID keys and entity-type awareness.

### Alternative 3: Aspect-Oriented Programming (AOP)

- **Description**: Use an AOP library to inject caching logic:
  ```python
  @aspect
  class CacheAspect:
      @before("TasksClient.get_async")
      def check_cache(self, join_point):
          ...
      @after("TasksClient.get_async")
      def store_cache(self, join_point):
          ...
  ```
- **Pros**:
  - Complete separation of caching concern
  - No changes to existing methods
- **Cons**:
  - Adds external dependency
  - AOP is uncommon in Python ecosystem
  - Harder to debug and understand
  - Team unfamiliar with pattern
- **Why not chosen**: Over-engineering. The SDK doesn't use AOP elsewhere, and the pattern would be inconsistent.

### Alternative 4: Separate CachedTasksClient

- **Description**: Create a separate client class with caching:
  ```python
  class CachedTasksClient(TasksClient):
      async def get_async(self, task_gid: str, ...) -> Task:
          # Check cache, call super(), store cache
  ```
- **Pros**:
  - Original TasksClient unchanged
  - Clear separation of cached vs uncached
- **Cons**:
  - Doubles the number of client classes
  - User must choose between clients
  - Inheritance can become complex
  - Defeats purpose of "enabled by default"
- **Why not chosen**: Creates unnecessary complexity. Caching should be transparent to users.

## Consequences

### Positive

- **Clear code flow**: Cache check visible in method body, easy to follow
- **Reusable helpers**: BaseClient methods used by all clients
- **Type safety preserved**: No wrapper functions that lose type info
- **Flexible TTL**: Entity-type detection in method allows customization
- **Graceful degradation**: Error handling in helpers, not scattered
- **Testable**: Mock helpers or cache provider for unit tests

### Negative

- **Code duplication**: Cache check pattern repeated in each cached method
- **Manual integration**: Each new cacheable method must add cache logic
- **Helper coupling**: Clients depend on BaseClient cache helpers

### Neutral

- **Performance impact**: Adds ~1-5ms for cache operations (acceptable per NFR-PERF-002)
- **Code length**: ~10 extra lines per cached method

## Compliance

How do we ensure this decision is followed?

1. **Code review**: Cache logic must use BaseClient helpers
2. **Linting**: Consider custom lint rule for cache pattern consistency
3. **Testing**: Each cached method has cache hit/miss tests
4. **Documentation**: Pattern documented for future method authors

## Implementation Checklist

- [ ] Add `_cache_get`, `_cache_set`, `_cache_invalidate` to BaseClient
- [ ] Add `_parse_modified_at` utility to BaseClient
- [ ] Integrate cache check in TasksClient.get_async()
- [ ] Add `_resolve_entity_ttl` method to TasksClient
- [ ] Add unit tests for BaseClient helpers
- [ ] Add cache hit/miss tests for get_async()
