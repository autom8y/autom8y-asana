# ADR-0063: Platform Extraction of Concurrency and Hierarchy Resolution Utilities

## Status

Proposed

## Context

### The Problem

The GID resolution service in autom8_asana times out when processing large entity hierarchies due to sequential processing patterns. When resolving parent references for tasks (e.g., project, section, assignee), each resolution triggers a synchronous API call, resulting in N+1 query patterns that compound with hierarchy depth.

Observed issues:
- Resolving 2600+ tasks with parent/section/project relationships takes 45-60s
- Sequential GID resolution creates cascading timeouts
- N+1 patterns exist across multiple entity relationship resolutions (tasks, sections, projects, custom fields)

### Existing Platform Infrastructure

Exploration of `autom8y/sdks/python/` revealed mature, production-ready infrastructure:

**autom8y-http** (already consumed by autom8_asana):
- `TokenBucketRateLimiter`: Async-safe token bucket with configurable refill rate
- `CircuitBreaker`: State machine (CLOSED/OPEN/HALF_OPEN) for cascading failure prevention
- `ExponentialBackoffRetry`: Jittered exponential backoff with configurable status codes
- `ResilientCoreClient`: Composition wrapper applying retry + circuit breaker policies

**autom8y-cache**:
- `HierarchyTracker`: Bidirectional parent-child relationship tracking with thread-safe operations
- `ModificationCheckCache`: TTL-based cache with staleness detection
- Tiered caching with memory/Redis/S3 backends

### The Gap

The platform has rate limiting and resilience patterns, but lacks:

1. **ConcurrencyController**: Coordinated concurrency limiting beyond rate limiting. The existing `TokenBucketRateLimiter` controls request rate, but doesn't coordinate concurrent in-flight request counts across operations that share resources.

2. **HierarchyAwareResolver protocol**: A protocol for batch resolution of hierarchical entities that respects parent-child ordering and leverages the existing `HierarchyTracker` for dependency-aware batching.

### Forces at Play

- N+1 patterns exist in multiple autom8_platform consumers (autom8_asana, future integrations)
- Building utilities locally creates duplication and inconsistent patterns
- Platform SDKs already have the foundational building blocks
- Extending existing SDKs is lower friction than creating new packages
- Platform repo is already a dependency for autom8_asana

## Decision

**Extend existing autom8y-http and autom8y-cache SDKs with new modules rather than building utilities locally in autom8_asana or creating a new SDK package.**

Specifically:

1. **Add `ConcurrencyController` to autom8y-http** (`src/autom8y_http/concurrency.py`):
   - Wraps `asyncio.Semaphore` with observability (waiters count, acquire latency)
   - Composes with existing `TokenBucketRateLimiter` (concurrency limits + rate limits)
   - Protocol-based for testability (`ConcurrencyControllerProtocol`)

2. **Add `HierarchyAwareResolver` protocol to autom8y-cache** (`src/autom8y_cache/resolver.py`):
   - Protocol defining batch resolution with hierarchy awareness
   - Default implementation using existing `HierarchyTracker` for dependency ordering
   - Configurable batch sizes and concurrency limits
   - Partial failure handling per ADR-0037 patterns

3. **autom8_asana consumes via existing dependency**:
   - No new dependencies; autom8_asana already depends on autom8y-http and autom8y-cache
   - `GidResolutionService` uses injected `ConcurrencyController` and implements `HierarchyAwareResolver`

### Module Locations

```
autom8y-http/
  src/autom8y_http/
    concurrency.py          # NEW: ConcurrencyController, ConcurrencyControllerProtocol
    protocols.py            # ADD: ConcurrencyControllerProtocol
    __init__.py             # EXPORT: ConcurrencyController, ConcurrencyControllerProtocol

autom8y-cache/
  src/autom8y_cache/
    resolver.py             # NEW: HierarchyAwareResolver protocol + default implementation
    protocols/__init__.py   # ADD: HierarchyAwareResolverProtocol
    __init__.py             # EXPORT: HierarchyAwareResolver, HierarchyAwareResolverProtocol
```

## Alternatives Considered

### Option A: Local Implementation in autom8_asana

Build `ConcurrencyController` and hierarchy resolution directly in autom8_asana.

**Pros**:
- No cross-repository coordination required
- Faster initial implementation
- autom8_asana controls its own destiny

**Cons**:
- N+1 patterns exist in other platform consumers (future integrations)
- Duplicates patterns that should be platform-level utilities
- Inconsistent resilience patterns across satellites
- autom8_asana becomes the wrong layer for reusable infrastructure

**Why not chosen**: These are cross-cutting concerns applicable to multiple platform consumers. Local implementation creates duplication and inconsistency.

### Option B: New SDK Package (autom8y-concurrency)

Create a new SDK package dedicated to concurrency control.

**Pros**:
- Clean separation of concerns
- Independent versioning
- Clear package boundary

**Cons**:
- Too fine-grained; concurrency control is a feature, not a product
- Increases dependency graph complexity
- More packages to maintain and version
- ConcurrencyController naturally composes with rate limiter (same package)

**Why not chosen**: Over-segmentation. Concurrency control is closely related to HTTP client behavior (autom8y-http) and batch resolution is closely related to caching (autom8y-cache). These are features, not standalone products.

### Option C: Extend Existing SDKs (Selected)

Add new modules to autom8y-http and autom8y-cache.

**Pros**:
- Natural fit with existing patterns (composition, protocols, async-first)
- Leverages existing primitives (rate limiter, hierarchy tracker)
- No new dependencies for consumers
- Follows established package conventions

**Cons**:
- Requires coordinated release across platform SDKs
- Platform repo becomes a dependency for more features
- Changes to platform require cross-team coordination

**Why chosen**: Best tradeoff between reusability and complexity. The new modules compose naturally with existing primitives and follow established patterns.

## Rationale

### Why Extend autom8y-http with ConcurrencyController?

The `ConcurrencyController` is an HTTP client concern because:

1. **Composes with existing primitives**: Works alongside `TokenBucketRateLimiter` - rate limiting controls how fast you can make requests, concurrency limiting controls how many are in-flight simultaneously.

2. **Applied at request layer**: The concurrency limit applies when making HTTP requests, not when processing results. This is the same layer as rate limiting and circuit breaking.

3. **Follows SDK patterns**: Protocol-based, async-first, injectable - matches `TokenBucketRateLimiter` and `CircuitBreaker` patterns.

### Why Extend autom8y-cache with HierarchyAwareResolver?

The `HierarchyAwareResolver` belongs in autom8y-cache because:

1. **Uses existing HierarchyTracker**: The resolver leverages `HierarchyTracker` to understand parent-child ordering for batch resolution.

2. **Caching concern**: Resolution results are cached; the resolver protocol integrates with cache warming and invalidation patterns.

3. **Batch operations pattern**: Follows `ModificationCheckCache` patterns for bulk operations.

### Composition Example

```python
from autom8y_http import TokenBucketRateLimiter, ConcurrencyController
from autom8y_cache import HierarchyAwareResolver

# Compose rate limiting + concurrency limiting
rate_limiter = TokenBucketRateLimiter(max_tokens=1500, refill_period=60)
concurrency = ConcurrencyController(max_concurrent=50)

async def fetch_with_limits(url: str) -> Response:
    async with concurrency.acquire():  # Limit concurrent requests
        await rate_limiter.acquire()    # Limit request rate
        return await http_client.get(url)

# Resolver uses both when batch-resolving hierarchy
resolver = HierarchyAwareResolver(
    hierarchy_tracker=tracker,
    fetch_fn=fetch_with_limits,
    batch_size=100,
)
```

## Consequences

### Positive

1. **Reusable across integrations**: Future platform integrations (autom8_jira, autom8_monday, etc.) benefit from the same concurrency and resolution patterns.

2. **Consistent resilience behavior**: All platform consumers use the same battle-tested primitives for rate limiting, concurrency control, and batch resolution.

3. **Leverages existing infrastructure**: No reinvention - the new modules compose with existing `TokenBucketRateLimiter`, `HierarchyTracker`, and resilience patterns.

4. **Protocol-based testability**: Both new components are protocol-first, enabling easy mocking and testing without real HTTP calls.

5. **No new dependencies**: autom8_asana already depends on autom8y-http and autom8y-cache; no dependency graph changes.

### Negative

1. **Coordinated release required**: Changes to autom8y-http and autom8y-cache must be released before autom8_asana can consume them.

2. **Platform repo dependency deepens**: autom8_asana becomes more coupled to platform SDK evolution. Breaking changes in autom8y-http/cache affect autom8_asana.

3. **Cross-repository coordination**: Feature development spans multiple repositories (autom8y, autom8_asana), requiring more coordination.

4. **Version alignment**: autom8_asana must track platform SDK versions and update when new features are available.

**Mitigation**: Use semantic versioning with care. New modules are additive (minor version bump). Breaking changes to existing modules follow deprecation cycle.

### Neutral

1. **Platform SDKs grow**: autom8y-http and autom8y-cache gain new modules. This is the natural evolution of shared infrastructure.

2. **Documentation burden**: New modules require documentation in both platform repo (API docs) and autom8_asana (usage examples).

## Implementation Guidance

### Phase 1: Platform SDK Extensions

1. Add `ConcurrencyController` to autom8y-http:
   - Protocol in `protocols.py`
   - Implementation in `concurrency.py`
   - Export from `__init__.py`
   - Unit tests with mock semaphore

2. Add `HierarchyAwareResolver` to autom8y-cache:
   - Protocol in `protocols/resolver.py`
   - Default implementation in `resolver.py`
   - Integration tests with `HierarchyTracker`

3. Release autom8y-http and autom8y-cache (minor version bump)

### Phase 2: autom8_asana Integration

1. Update autom8y-http and autom8y-cache dependencies
2. Inject `ConcurrencyController` into `AsanaClient`
3. Implement `HierarchyAwareResolverProtocol` in `GidResolutionService`
4. Wire batch resolution into entity resolution paths

### ConcurrencyController API Sketch

```python
class ConcurrencyControllerProtocol(Protocol):
    """Protocol for concurrency limiting."""

    @property
    def max_concurrent(self) -> int:
        """Maximum concurrent operations allowed."""
        ...

    @property
    def current_count(self) -> int:
        """Current number of in-flight operations."""
        ...

    async def acquire(self) -> AsyncContextManager[None]:
        """Acquire concurrency slot (blocks if at limit)."""
        ...

    async def try_acquire(self) -> AsyncContextManager[bool]:
        """Try to acquire slot without blocking."""
        ...


class ConcurrencyController:
    """Async concurrency limiter with observability."""

    def __init__(
        self,
        max_concurrent: int = 50,
        logger: LoggerProtocol | None = None,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._current_count = 0
        self._logger = logger

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        await self._semaphore.acquire()
        self._current_count += 1
        try:
            yield
        finally:
            self._current_count -= 1
            self._semaphore.release()
```

### HierarchyAwareResolver API Sketch

```python
class HierarchyAwareResolverProtocol(Protocol[K, V]):
    """Protocol for hierarchy-aware batch resolution."""

    async def resolve_batch(
        self,
        ids: Sequence[K],
        *,
        include_ancestors: bool = False,
    ) -> dict[K, V | ResolveError]:
        """Resolve IDs in hierarchy-respecting order."""
        ...


class HierarchyAwareResolver(Generic[K, V]):
    """Default implementation using HierarchyTracker."""

    def __init__(
        self,
        hierarchy_tracker: HierarchyTracker[K],
        fetch_fn: Callable[[Sequence[K]], Awaitable[dict[K, V | None]]],
        batch_size: int = 100,
        concurrency: ConcurrencyControllerProtocol | None = None,
    ) -> None:
        ...
```

## Cross-References

- **ADR-0062**: Rate limiter coordination (client-scoped shared rate limiter)
- **ADR-0025**: Async-first concurrency pattern
- **ADR-0037**: Partial failure result patterns
- **PRD-GID-RESOLUTION-FIX**: Requirements for GID resolution timeout fix
- **TDD-TTL-DETECTION-EXTRACTION**: Technical design for TTL detection extraction
