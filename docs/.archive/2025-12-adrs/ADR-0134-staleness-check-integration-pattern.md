# ADR-0134: Staleness Check Integration Pattern

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-24
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-CACHE-LIGHTWEIGHT-STALENESS, TDD-CACHE-LIGHTWEIGHT-STALENESS, ADR-0132 (Batch Request Coalescing), ADR-0133 (Progressive TTL Extension), ADR-0127 (Graceful Degradation Pattern)

## Context

The lightweight staleness check system must integrate into the existing SDK architecture without breaking changes. The integration point determines:

1. **Where** staleness checks are triggered
2. **How** the coordinator is accessed
3. **What** code paths are affected
4. **Whether** existing behavior is preserved

### Problem Statement

The SDK has a layered architecture:

```
Consumer Code
      |
      v
TasksClient.get_async()
      |
      v
BaseClient._cache_get()
      |
      v
CacheProvider.get_versioned()
```

Staleness checks must be inserted into this flow without:
- Breaking existing public APIs
- Changing method signatures
- Affecting tests that don't use staleness checking
- Adding mandatory dependencies

### Forces at Play

| Force | Description |
|-------|-------------|
| **Backward Compatibility** | Existing code must work unchanged |
| **Testability** | Components must be mockable/replaceable |
| **Gradual Rollout** | Feature must be opt-in or disable-able |
| **Separation of Concerns** | Staleness logic shouldn't pollute client code |
| **Performance** | Integration overhead must be minimal |
| **Observability** | Clear logging of which path was taken |

### Key Questions

1. **Where** in the call hierarchy should the coordinator sit?
2. **How** should components access the coordinator?
3. **What** happens when coordinator is unavailable?
4. **How** to preserve existing behavior for non-staleness-aware code?

## Decision

**Implement coordinator pattern with constructor injection at BaseClient level, with transparent integration via enhanced cache helper method.**

### Specific Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Coordinator Location | `StalenessCheckCoordinator` as separate component | Separation of concerns |
| Injection Method | Constructor parameter on `BaseClient` | Explicit dependency, testable |
| Integration Point | New `_cache_get_with_staleness_async()` method | Preserves existing `_cache_get()` |
| Default Behavior | Disabled (coordinator=None) | Backward compatible |
| Entity Type Filter | Only TASK and PROJECT | Only types with `modified_at` |
| Error Handling | Graceful degradation per ADR-0127 | Never propagate staleness exceptions |

### Integration Architecture

```
+-----------------------------------------------------------------------------+
|                          AsanaClient                                         |
|  +-----------------------------------------------------------------------+  |
|  |  Constructor                                                           |  |
|  |  + Creates StalenessCheckCoordinator if cache enabled                 |  |
|  |  + Passes coordinator to TasksClient, ProjectsClient                  |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|                          TasksClient                                         |
|  +-----------------------------------------------------------------------+  |
|  |  Constructor (inherited from BaseClient)                               |  |
|  |  + staleness_coordinator: StalenessCheckCoordinator | None            |  |
|  +-----------------------------------------------------------------------+  |
|  |  get_async(gid, ...)                                                   |  |
|  |  + Uses _cache_get_with_staleness_async() if coordinator available    |  |
|  |  + Falls back to _cache_get() otherwise                               |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|                           BaseClient                                         |
|  +-----------------------------------------------------------------------+  |
|  |  _cache_get(key, entry_type) -> CacheEntry | None                     |  |
|  |  [EXISTING - unchanged]                                               |  |
|  |  + Check cache                                                         |  |
|  |  + Return entry if not expired                                        |  |
|  |  + Return None if expired or missing                                  |  |
|  +-----------------------------------------------------------------------+  |
|  |  _cache_get_with_staleness_async(key, entry_type) -> CacheEntry | None|  |
|  |  [NEW - enhanced flow]                                                |  |
|  |  + Check cache                                                         |  |
|  |  + Return entry if not expired                                        |  |
|  |  + If expired: queue staleness check                                  |  |
|  |  + Return extended entry if unchanged, None if changed                |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|                    StalenessCheckCoordinator                                 |
|  + check_and_get_async(entry) -> CacheEntry | None                          |
|  + Orchestrates coalescer and checker                                       |
|  + Handles TTL extension                                                    |
+-----------------------------------------------------------------------------+
```

### Code Changes

#### BaseClient Enhancement

```python
# src/autom8_asana/clients/base.py

class BaseClient:
    def __init__(
        self,
        http: AsyncHTTPClient,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
        staleness_coordinator: StalenessCheckCoordinator | None = None,  # NEW
    ) -> None:
        # ... existing init ...
        self._staleness_coordinator = staleness_coordinator  # NEW

    # EXISTING - unchanged
    def _cache_get(
        self,
        key: str,
        entry_type: EntryType,
    ) -> CacheEntry | None:
        """Check cache for an entry (graceful degradation).

        Per NFR-DEGRADE-001: Cache failures log warnings without raising.
        Per ADR-0127: Graceful degradation pattern.

        Args:
            key: Cache key (typically task GID).
            entry_type: Type of cache entry.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        # ... existing implementation unchanged ...

    # NEW - staleness-aware cache get
    async def _cache_get_with_staleness_async(
        self,
        key: str,
        entry_type: EntryType,
    ) -> CacheEntry | None:
        """Check cache with staleness checking for expired entries.

        Per ADR-0134: Enhanced cache lookup that performs lightweight
        staleness checks on expired entries before returning cache miss.

        Flow:
        1. Check cache for entry
        2. If not found -> return None (cache miss)
        3. If not expired -> return entry (cache hit)
        4. If expired AND staleness check supported:
           a. Queue for batch modified_at check
           b. If unchanged -> extend TTL, return entry
           c. If changed -> return None (caller fetches)
        5. If expired AND staleness check not supported -> return None

        Args:
            key: Cache key (typically task GID).
            entry_type: Type of cache entry.

        Returns:
            CacheEntry if hit or unchanged, None if miss or changed.
        """
        if self._cache is None:
            return None

        try:
            entry = self._cache.get_versioned(key, entry_type)

            if entry is None:
                logger.debug(
                    "cache_miss",
                    extra={"entry_type": entry_type.value, "key": key},
                )
                return None

            if not entry.is_expired():
                logger.debug(
                    "cache_hit",
                    extra={"entry_type": entry_type.value, "key": key},
                )
                return entry

            # Entry expired - attempt staleness check if available
            if self._staleness_coordinator is not None:
                # Only check types with modified_at
                if entry_type in (EntryType.TASK, EntryType.PROJECT):
                    try:
                        result = await self._staleness_coordinator.check_and_get_async(
                            entry
                        )
                        if result is not None:
                            logger.debug(
                                "staleness_check_unchanged",
                                extra={
                                    "entry_type": entry_type.value,
                                    "key": key,
                                    "new_ttl": result.ttl,
                                },
                            )
                            return result
                        logger.debug(
                            "staleness_check_changed",
                            extra={"entry_type": entry_type.value, "key": key},
                        )
                    except Exception as exc:
                        # Per ADR-0127: Graceful degradation
                        logger.warning(
                            "staleness_check_failed",
                            extra={
                                "entry_type": entry_type.value,
                                "key": key,
                                "error": str(exc),
                            },
                        )

            return None

        except Exception as exc:
            logger.warning(
                "cache_get_failed",
                extra={
                    "entry_type": entry_type.value,
                    "key": key,
                    "error": str(exc),
                },
            )
            return None
```

#### TasksClient Usage

```python
# src/autom8_asana/clients/tasks.py

class TasksClient(BaseClient):
    async def get_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single task by GID.

        Per ADR-0134: Uses staleness-aware cache lookup when available.
        """
        # Use staleness-aware cache if coordinator available
        if self._staleness_coordinator is not None:
            entry = await self._cache_get_with_staleness_async(
                task_gid, EntryType.TASK
            )
        else:
            entry = self._cache_get(task_gid, EntryType.TASK)

        if entry is not None:
            return entry.data

        # Cache miss or changed - fetch from API
        result = await self._http.request(
            "GET",
            f"/tasks/{task_gid}",
            params=self._build_opt_fields(opt_fields),
        )

        # Cache the fresh result
        self._cache_set(task_gid, result, EntryType.TASK)

        return result
```

#### AsanaClient Wiring

```python
# src/autom8_asana/client.py

class AsanaClient:
    def __init__(
        self,
        config: AsanaConfig | None = None,
        auth_provider: AuthProvider | None = None,
        cache_provider: CacheProvider | None = None,
        # ... other params ...
    ) -> None:
        # ... existing setup ...

        # Create staleness coordinator if cache enabled
        staleness_coordinator: StalenessCheckCoordinator | None = None
        if cache_provider is not None and config.cache.enabled:
            staleness_settings = config.cache.staleness_check_settings
            if staleness_settings.enabled:
                staleness_coordinator = StalenessCheckCoordinator(
                    cache_provider=cache_provider,
                    batch_client=self._batch,
                    settings=staleness_settings,
                )

        # Pass coordinator to clients
        self._tasks = TasksClient(
            http=self._http,
            config=config,
            auth_provider=auth_provider,
            cache_provider=cache_provider,
            staleness_coordinator=staleness_coordinator,  # NEW
        )
```

## Rationale

### Why Constructor Injection?

| Approach | Pros | Cons |
|----------|------|------|
| **Constructor Injection** | **Explicit, testable, replaceable** | **Requires param threading** |
| Global singleton | Simple access | Hidden dependency, test isolation issues |
| Thread-local | Per-thread isolation | Complex lifecycle, Python GIL nuances |
| Method parameter | Per-call control | Pollutes all method signatures |

Constructor injection:
- Makes dependencies explicit
- Enables easy mocking in tests
- Follows existing patterns (cache_provider, auth_provider)
- Allows different coordinators per client instance

### Why New Method vs. Enhancing Existing?

| Approach | Pros | Cons |
|----------|------|------|
| Enhance `_cache_get()` | Single code path | Breaks sync/async contract |
| **New `_cache_get_with_staleness_async()`** | **Clear async boundary** | **Two code paths** |
| Decorator pattern | Non-invasive | Magic behavior, hard to debug |

The existing `_cache_get()` is synchronous. Staleness checking requires async I/O. Rather than breaking the sync method or adding complexity, a new async method provides clear semantics.

### Why Entity Type Filter?

Only TASK and PROJECT have reliable `modified_at` fields:

| Entry Type | Has modified_at | Staleness Check Support |
|------------|-----------------|------------------------|
| TASK | Yes | Yes |
| PROJECT | Yes | Yes |
| SECTION | No | No |
| USER | No | No |
| CUSTOM_FIELD | No | No |
| SUBTASKS | Derived | Future (via parent) |
| DEPENDENCIES | Derived | Future (via parent) |

Filtering to supported types prevents API errors and provides clear documentation of capability.

### Why Graceful Degradation?

Per ADR-0127, cache-related errors should never propagate to consumers:

```python
try:
    result = await self._staleness_coordinator.check_and_get_async(entry)
    # ...
except Exception as exc:
    # Log and continue - fall back to full fetch
    logger.warning("staleness_check_failed", extra={"error": str(exc)})
```

This ensures:
- Application continues working if staleness checks fail
- Errors are logged for debugging
- Consumer receives valid data (either cached or fresh)

## Alternatives Considered

### Alternative 1: Middleware/Decorator Pattern

**Description**: Wrap cache operations with staleness-checking decorator.

```python
@staleness_check
def _cache_get(self, key, entry_type):
    # ...
```

**Pros**:
- Non-invasive to existing methods
- Separates cross-cutting concern
- Potentially reusable

**Cons**:
- "Magic" behavior hard to debug
- Breaks explicit is better than implicit
- Decorator must handle sync/async boundary
- Hidden control flow

**Why not chosen**: Explicit method call is clearer and easier to reason about.

### Alternative 2: CacheProvider Protocol Extension

**Description**: Add staleness checking to CacheProvider protocol itself.

```python
class CacheProvider(Protocol):
    def get_versioned_with_staleness(
        self,
        key: str,
        entry_type: EntryType,
        staleness_checker: Callable,
    ) -> CacheEntry | None:
        # ...
```

**Pros**:
- All cache access automatically staleness-aware
- Single integration point
- Encapsulated within cache layer

**Cons**:
- Protocol change affects all implementations
- Mixes caching and staleness concerns
- Staleness checking needs BatchClient (API layer)
- Cache shouldn't know about API calls

**Why not chosen**: Staleness checking requires API access; cache layer should remain storage-focused.

### Alternative 3: TasksClient-Level Integration Only

**Description**: Implement staleness checking only in TasksClient, not BaseClient.

```python
class TasksClient(BaseClient):
    def __init__(self, ..., staleness_coordinator=None):
        self._staleness_coordinator = staleness_coordinator

    async def get_async(self, task_gid, ...):
        # Staleness logic directly in TasksClient
```

**Pros**:
- Changes limited to one client
- Very surgical scope
- Clear ownership

**Cons**:
- Cannot reuse for ProjectsClient
- Duplicates logic if extended to other clients
- Staleness is a cache concern, not task concern

**Why not chosen**: BaseClient-level integration enables reuse across clients that support staleness checking.

### Alternative 4: Separate StalenessAwareClient Base Class

**Description**: Create new base class with staleness support.

```python
class StalenessAwareClient(BaseClient):
    def __init__(self, ..., staleness_coordinator=None):
        # ...

    async def _cache_get_with_staleness_async(self, ...):
        # ...

class TasksClient(StalenessAwareClient):
    # ...
```

**Pros**:
- Clean separation of capabilities
- Explicit inheritance hierarchy
- Non-staleness clients unaffected

**Cons**:
- Diamond inheritance risk
- More complex class hierarchy
- Over-engineering for single feature

**Why not chosen**: Optional parameter on existing BaseClient is simpler and achieves same goal.

## Consequences

### Positive

1. **Backward Compatible**: Existing code works unchanged
2. **Testable**: Coordinator can be mocked/replaced
3. **Gradual Rollout**: Opt-in via configuration
4. **Clear Boundaries**: Staleness logic encapsulated in coordinator
5. **Observable**: Distinct log events for each path
6. **Extensible**: Easy to add staleness support to other clients

### Negative

1. **Two Code Paths**: `_cache_get()` vs `_cache_get_with_staleness_async()`
2. **Constructor Threading**: Coordinator passed through multiple layers
3. **Async Requirement**: Staleness checking requires async context
4. **Complexity**: More code paths to test and maintain

### Neutral

1. **Configuration**: Feature can be enabled/disabled via settings
2. **Entity Type Filtering**: Only TASK and PROJECT initially supported
3. **Logging**: Additional debug/warning logs

## Compliance

### How This Decision Will Be Enforced

1. **Code Review**: Changes to integration pattern require ADR reference
2. **Unit Tests**: Test both staleness-enabled and disabled paths
3. **Integration Tests**: Validate full flow with coordinator
4. **Backward Compat Tests**: Verify existing tests pass unchanged

### Configuration

```python
@dataclass(frozen=True)
class StalenessCheckSettings:
    """Per ADR-0134: Settings for staleness checking."""
    enabled: bool = True  # Feature flag
    base_ttl: int = 300
    max_ttl: int = 86400
    coalesce_window_ms: int = 50
    max_batch_size: int = 100

@dataclass
class CacheConfig:
    # ... existing fields ...
    staleness_check_settings: StalenessCheckSettings = field(
        default_factory=StalenessCheckSettings
    )
```

### Code Location

```python
# Integration points:
# /src/autom8_asana/clients/base.py - BaseClient with staleness coordinator
# /src/autom8_asana/clients/tasks.py - TasksClient usage
# /src/autom8_asana/client.py - AsanaClient wiring
# /src/autom8_asana/cache/staleness_coordinator.py - Coordinator implementation
```

### Logging

```python
# Path selection logging
logger.debug(
    "cache_lookup_path",
    extra={
        "path": "staleness_aware" | "standard",
        "entry_type": entry_type.value,
        "coordinator_available": self._staleness_coordinator is not None,
    },
)

# Staleness check outcome
logger.debug(
    "staleness_check_outcome",
    extra={
        "outcome": "unchanged" | "changed" | "error",
        "entry_type": entry_type.value,
        "key": key,
    },
)
```

### Backward Compatibility Checklist

- [ ] `BaseClient` constructor accepts `staleness_coordinator` as optional parameter
- [ ] Default value `None` preserves existing behavior
- [ ] Existing `_cache_get()` method unchanged
- [ ] Existing tests pass without modification
- [ ] Clients without coordinator work exactly as before
- [ ] No changes to public method signatures
- [ ] No changes to return types
