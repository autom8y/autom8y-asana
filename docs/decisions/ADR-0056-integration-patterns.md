# ADR-0056: Integration Patterns for Cross-Layer Orchestration

## Metadata
- **Status**: Accepted
- **Consolidated From**: ADR-0119 (Client Cache Integration), ADR-0124 (Client Cache Pattern), ADR-0116 (Batch Cache Population), ADR-0134 (Staleness Check Integration), ADR-0050 (Holder Lazy Loading), ADR-0087 (Minimal Stub Model)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Related**: [reference/PATTERNS.md](reference/PATTERNS.md), ADR-SUMMARY-CACHE, ADR-0052 (Protocol Extensibility)

---

## Context

Caching, staleness checking, and client operations require coordination across SDK layers:

1. **Client Cache Integration**: StandardizedTasks, Projects, Sections, Users, CustomFields clients all need caching
2. **Batch Cache Population**: Large projects (3,500+ tasks) require efficient bulk operations
3. **Staleness Check Integration**: Lightweight `modified_at` checks extend expired cache entries
4. **Holder Lazy Loading**: Business holders (contacts, units) contain subtasks that shouldn't be fetched eagerly
5. **Minimal Stub Models**: Type-safe iteration over stub holders without known custom fields

**Forces at play**:
- Different entity types have different versioning capabilities (`modified_at` varies)
- TTL requirements differ by entity volatility
- Code duplication risk if pattern not well-defined
- Graceful degradation must never propagate exceptions
- Performance requirements (batch operations, minimal API calls)

---

## Decision

Use **standardized integration patterns** with graceful degradation and batch optimization.

### 1. Client Cache Integration Pattern

**6-step standardized pattern** for all SDK clients:

```python
@error_handler
async def get_async(
    self,
    {entity}_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Model | dict[str, Any]:
    """Get {entity} by GID with cache support.

    Per ADR-0056: Follows 6-step client cache integration pattern.
    """
    from autom8_asana.cache.entry import EntryType
    from autom8_asana.persistence.validation import validate_gid

    # 1. Validate GID
    validate_gid({entity}_gid, "{entity}_gid")

    # 2. Check cache first
    cached_entry = self._cache_get({entity}_gid, EntryType.{ENTRY_TYPE})
    if cached_entry is not None:
        data = cached_entry.data
        if raw:
            return data
        return Model.model_validate(data)

    # 3. Fetch from API on miss
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/{entities}/{{{entity}_gid}}", params=params)

    # 4. Store in cache
    self._cache_set({entity}_gid, data, EntryType.{ENTRY_TYPE}, ttl={TTL})

    # 5. Return response
    if raw:
        return data
    return Model.model_validate(data)
```

**TTL Configuration** (fixed per entity type):

| EntryType | TTL (seconds) | Rationale |
|-----------|---------------|-----------|
| TASK | Entity-type detected | Business/Contact/etc. have different TTLs |
| PROJECT | 900 (15 min) | Has `modified_at`; metadata changes infrequently |
| SECTION | 1800 (30 min) | No `modified_at`; sections rarely change |
| USER | 3600 (1 hour) | No timestamps; profiles extremely stable |
| CUSTOM_FIELD | 1800 (30 min) | Schema changes require admin action |

**Versioning Strategy**:
- **Entities with `modified_at`** (Task, Project): Extract from API response
- **Entities without `modified_at`** (Section, User, CustomField): Use `datetime.now()`

This is handled automatically by `BaseClient._cache_set()`:

```python
def _cache_set(
    self,
    key: str,
    data: dict[str, Any],
    entry_type: EntryType,
    ttl: int | None = None
) -> None:
    """Store entry in cache with versioning (graceful degradation).

    Per ADR-0127: Cache failures log warnings without raising.
    """
    if self._cache is None:
        return

    try:
        # Extract modified_at if available
        modified_at = data.get("modified_at")
        if modified_at:
            version = self._parse_modified_at(modified_at)
        else:
            version = datetime.now(timezone.utc)

        entry = CacheEntry(
            data=data,
            entry_type=entry_type,
            version=version,
            ttl=ttl or DEFAULT_TTL
        )

        self._cache.set_versioned(key, entry)

        logger.debug(
            "cache_set",
            extra={
                "entry_type": entry_type.value,
                "key": key,
                "ttl": ttl,
                "has_modified_at": modified_at is not None
            }
        )

    except Exception as exc:
        logger.warning(
            "cache_set_failed",
            extra={
                "entry_type": entry_type.value,
                "key": key,
                "error": str(exc)
            }
        )
        # Never propagate cache errors
```

**Rationale**:
- **Consistency**: All clients behave identically
- **Maintainability**: Single pattern to understand and test
- **Reliability**: Leverages proven BaseClient helpers
- **Graceful degradation**: Cache errors never propagate

### 2. Batch Cache Population Pattern

**Check-Fetch-Populate pattern** for bulk operations:

```python
async def populate_cache_for_project_async(
    self,
    project_gid: str,
    expected_gids: list[str]
) -> None:
    """Populate cache for all tasks in project with minimal API calls.

    Per ADR-0056: Batch cache population pattern.

    Args:
        project_gid: Project GID.
        expected_gids: List of task GIDs to populate.

    Example:
        # Cache 3,500 tasks efficiently
        await client.tasks.populate_cache_for_project_async(
            "123456",
            expected_gids=all_task_gids
        )
    """
    if self._cache is None:
        return

    # 1. Generate cache keys
    cache_keys = [
        self._make_cache_key(gid, project_gid)
        for gid in expected_gids
    ]

    # 2. Check cache (batch operation)
    cached_entries = self._cache.get_batch(cache_keys, EntryType.TASK)

    # 3. Partition hits/misses
    cache_hits = {
        k: v for k, v in cached_entries.items()
        if v and not v.is_stale()
    }
    cache_misses = {
        k for k in cache_keys
        if k not in cache_hits
    }

    logger.info(
        "batch_cache_check",
        extra={
            "total": len(cache_keys),
            "hits": len(cache_hits),
            "misses": len(cache_misses)
        }
    )

    # 4. Fetch only misses (parallel)
    if cache_misses:
        missing_gids = [
            self._extract_gid_from_cache_key(k)
            for k in cache_misses
        ]

        fetched = await self._parallel_fetch(missing_gids)

        # 5. Populate cache (batch operation)
        entries_to_cache = {
            self._make_cache_key(task.gid, project_gid): CacheEntry(
                data=task.model_dump(),
                entry_type=EntryType.TASK,
                version=task.modified_at or datetime.now(timezone.utc),
                ttl=300
            )
            for task in fetched
        }

        self._cache.set_batch(entries_to_cache)

        logger.info(
            "batch_cache_populated",
            extra={"count": len(entries_to_cache)}
        )
```

**Batch API**:

```python
# CacheProvider protocol methods
def get_batch(
    self,
    keys: list[str],
    entry_type: EntryType,
) -> dict[str, CacheEntry | None]:
    """Get multiple entries in single operation.

    Args:
        keys: List of cache keys.
        entry_type: Type of entries.

    Returns:
        Dict mapping keys to entries (None for missing).
    """
    ...

def set_batch(self, entries: dict[str, CacheEntry]) -> None:
    """Set multiple entries in single operation.

    Args:
        entries: Dict mapping keys to cache entries.
    """
    ...
```

**Impact**:
- **Before**: 3,500 individual cache `get()` calls = O(n) latency
- **After**: 1 batch `get_batch()` call + partial fetch = O(1) + O(misses)

**Rationale**:
- **Minimize API calls**: Only fetch missing/stale entries
- **Batch operations**: Single round-trip for cache check
- **Partial cache**: Leverage existing valid entries

### 3. Staleness Check Integration Pattern

**Enhanced cache lookup** with coordinator pattern:

```python
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
            logger.debug("cache_miss", extra={"entry_type": entry_type.value, "key": key})
            return None

        if not entry.is_expired():
            logger.debug("cache_hit", extra={"entry_type": entry_type.value, "key": key})
            return entry

        # Entry expired - attempt staleness check if available
        if self._staleness_coordinator is not None:
            # Only check types with modified_at
            if entry_type in (EntryType.TASK, EntryType.PROJECT):
                try:
                    result = await self._staleness_coordinator.check_and_get_async(entry)
                    if result is not None:
                        logger.debug(
                            "staleness_check_unchanged",
                            extra={
                                "entry_type": entry_type.value,
                                "key": key,
                                "new_ttl": result.ttl
                            }
                        )
                        return result
                    logger.debug(
                        "staleness_check_changed",
                        extra={"entry_type": entry_type.value, "key": key}
                    )
                except Exception as exc:
                    # Per ADR-0127: Graceful degradation
                    logger.warning(
                        "staleness_check_failed",
                        extra={
                            "entry_type": entry_type.value,
                            "key": key,
                            "error": str(exc)
                        }
                    )

        return None  # Expired, no coordinator, or changed

    except Exception as exc:
        logger.warning(
            "cache_get_failed",
            extra={
                "entry_type": entry_type.value,
                "key": key,
                "error": str(exc)
            }
        )
        return None
```

**Constructor Injection**:

```python
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
        # ...
        self._staleness_coordinator = staleness_coordinator
```

**Client Usage**:

```python
class TasksClient(BaseClient):
    async def get_async(self, task_gid: str, **kwargs) -> dict[str, Any]:
        # Use staleness-aware cache if coordinator available
        if self._staleness_coordinator is not None:
            entry = await self._cache_get_with_staleness_async(task_gid, EntryType.TASK)
        else:
            entry = self._cache_get(task_gid, EntryType.TASK)

        if entry is not None:
            return entry.data

        # Cache miss or changed - fetch from API
        # ...
```

**Rationale**:
- **Opt-in**: Disabled by default (coordinator=None)
- **Entity type filter**: Only TASK/PROJECT (have `modified_at`)
- **Graceful degradation**: Staleness check errors fall back to full fetch
- **Constructor injection**: Explicit dependency, testable

### 4. Holder Lazy Loading Pattern

**Deferred fetching triggered on SaveSession.track():**

```python
async def prefetch_holders(self) -> None:
    """Prefetch holder subtasks for all tracked business entities.

    Per ADR-0050: Holders fetched when entity tracked, not on property access.

    Example:
        async with client.save_session() as session:
            session.track(business)
            await session.prefetch_holders()  # Explicit prefetch
            # business.contact_holder now populated
    """
    for entity in self._tracked_entities:
        if hasattr(entity, "_holder_gid"):
            holder_gid = entity._holder_gid
            if holder_gid:
                # Fetch holder task with subtasks
                holder_task = await self._client.tasks.get_async(
                    holder_gid,
                    opt_fields=["subtasks"]
                )
                # Populate entity._holder attribute
                entity._populate_holder(holder_task)
```

**Rationale**:
- **Why not property access**: Async properties break Python conventions
- **Why not __init__**: Task construction should be cheap, no network calls
- **Batch-friendly**: Multiple businesses can be prefetched in parallel

### 5. Minimal Stub Model Pattern

**Type-safe stubs for holders without known custom fields:**

```python
class DNA(BusinessEntity):
    """Minimal typed model for DNA holder subtasks.

    Per ADR-0087: Minimal stub model for type safety without
    known custom fields.

    Contents:
    - Bidirectional navigation only (holder → entity, entity → root)

    Exclusions:
    - No custom field accessors (domain unknown)
    """

    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    # Navigation descriptors
    dna_holder: DNAHolder | None = HolderRef[DNAHolder]()
    business: Business | None = ParentRef[Business](holder_attr="_dna_holder")
```

**Usage**:

```python
# Type-safe iteration
for dna in business.dna_holder.children:  # list[DNA], not list[Task]
    print(dna.business.name)  # Navigate to root
    # dna.some_custom_field  # NOT available (domain unknown)
```

**Rationale**:
- **Purpose**: Type safety for stub holders without known custom fields
- **Contents**: Bidirectional navigation only
- **Exclusions**: No custom field descriptors (domain unknown)

---

## Rationale

### Why Standardized Pattern Over Custom Logic?

Each client could implement custom caching, but this leads to:
- Inconsistent behavior across clients
- Harder testing (each client needs unique coverage)
- Bug risk from subtle differences

Standardized pattern ensures:
- Predictable behavior for SDK users
- Single test template for all clients
- Easier code review (deviation is red flag)

### Why Fixed TTL vs. Configurable?

**Fixed TTL per entity type** rather than user-configurable:
- **Simplicity**: No new configuration surface
- **Consistency**: All SDK users get same behavior
- **Appropriate defaults**: TTLs based on entity volatility analysis

Users needing different TTLs can:
1. Implement custom CacheProvider
2. Use cache invalidation APIs
3. Request configuration in future release

### Why Batch Operations?

**Large project performance**:
- 3,500 tasks × individual cache.get() = 3,500 round-trips
- 1 × cache.get_batch() = 1 round-trip

**Redis native support**:
- `MGET` for batch get
- `MSET` for batch set
- Atomic operations

### Why Constructor Injection for Coordinator?

| Approach | Pros | Cons |
|----------|------|------|
| **Constructor Injection** | **Explicit, testable, replaceable** | Requires param threading |
| Global singleton | Simple access | Hidden dependency, test isolation |
| Thread-local | Per-thread isolation | Complex lifecycle |
| Method parameter | Per-call control | Pollutes signatures |

Constructor injection:
- Makes dependencies explicit
- Enables easy mocking in tests
- Follows existing patterns (cache_provider, auth_provider)
- Allows different coordinators per client

### Why Lazy Loading for Holders?

**Problem**: Eager loading subtasks bloats response size, slows initialization.

**Alternatives**:

| When | Pros | Cons |
|------|------|------|
| Property access | Transparent | Async properties break conventions |
| **SaveSession.track()** | **Explicit, batch-friendly** | Requires awareness |
| __init__ | Immediate | Expensive, not lazy |

Lazy loading on track() balances explicitness with performance.

---

## Alternatives Considered

### Client Cache Alternatives

#### Alternative 1: Client-Specific Caching Logic

- **Description**: Each client implements own strategy
- **Pros**: Maximum flexibility per entity type
- **Cons**: Code duplication, inconsistent behavior, higher test burden
- **Why not chosen**: Pattern consistency outweighs flexibility

#### Alternative 2: Generic Caching Decorator

- **Description**: `@cached(entry_type=...)` decorator
- **Pros**: Zero duplication, single implementation
- **Cons**: Decorator complexity with async, hard to handle `raw` parameter, obscures logic
- **Why not chosen**: Explicit pattern clearer

#### Alternative 3: Always Use Current Timestamp

- **Description**: Don't use `modified_at` even when available
- **Pros**: Simpler, uniform versioning
- **Cons**: Loses staleness detection, cache may return stale data
- **Why not chosen**: `modified_at` provides better freshness

### Staleness Check Alternatives

#### Alternative 1: CacheProvider Protocol Extension

- **Description**: Add staleness to CacheProvider protocol
- **Pros**: All cache access automatically staleness-aware
- **Cons**: Protocol change affects all implementations, mixes concerns, cache shouldn't know about API
- **Why not chosen**: Staleness needs API access; cache should be storage-focused

#### Alternative 2: TasksClient-Level Only

- **Description**: Implement only in TasksClient
- **Pros**: Limited scope, clear ownership
- **Cons**: Cannot reuse for ProjectsClient, duplicates logic
- **Why not chosen**: BaseClient-level enables reuse

---

## Consequences

### Positive

1. **Client Cache Integration**:
   - Consistency across all clients
   - Maintainability (single pattern)
   - Reliability (proven BaseClient helpers)
   - Simplicity (no new abstractions)

2. **Batch Cache Population**:
   - Minimize API calls for large projects
   - Leverage cache efficiently
   - O(1) latency vs O(n)

3. **Staleness Check Integration**:
   - Backward compatible (opt-in)
   - Testable (coordinator mockable)
   - Gradual rollout via configuration
   - Clear boundaries (coordinator encapsulates logic)
   - Observable (distinct log events)

4. **Holder Lazy Loading**:
   - Performance (no eager fetching)
   - Explicit control (prefetch_holders())
   - Batch-friendly (parallel fetches)

5. **Minimal Stub Model**:
   - Type safety for iteration
   - Navigation works correctly
   - No false custom field promises

### Negative

1. **Client Cache Integration**:
   - Fixed TTLs (users cannot customize)
   - No skip-cache option (must call API directly)
   - Code similarity (pattern repetition)

2. **Batch Cache Population**:
   - Complexity (partition logic)
   - Requires batch-capable cache backend

3. **Staleness Check Integration**:
   - Two code paths (_cache_get vs _cache_get_with_staleness_async)
   - Constructor threading (coordinator passed through layers)
   - Async requirement (staleness needs async context)
   - Additional complexity

4. **Holder Lazy Loading**:
   - Requires awareness (must call prefetch_holders())
   - Not transparent (explicit step)

5. **Minimal Stub Model**:
   - Additional model classes
   - Limited functionality (navigation only)

### Neutral

1. **Test coverage**: Each client needs tests, but template exists
2. **Documentation**: Patterns must be documented
3. **Configuration**: Features can be enabled/disabled
4. **Logging**: Additional debug/warning logs

---

## Compliance

### How This Decision Will Be Enforced

1. **Code review checklist**:
   - [ ] Cache integration follows 6-step pattern
   - [ ] Graceful degradation implemented
   - [ ] TTL documented in docstring
   - [ ] EntryType enum value added for new cacheable entities

2. **Pattern template** for new clients:
```python
async def get_async(self, {entity}_gid: str, *, raw: bool = False, ...) -> Model | dict:
    validate_gid({entity}_gid, "{entity}_gid")
    cached_entry = self._cache_get({entity}_gid, EntryType.{ENTRY_TYPE})
    if cached_entry is not None:
        return cached_entry.data if raw else Model.model_validate(cached_entry.data)
    data = await self._http.get(f"/{entities}/{{{entity}_gid}}", ...)
    self._cache_set({entity}_gid, data, EntryType.{ENTRY_TYPE}, ttl={TTL})
    return data if raw else Model.model_validate(data)
```

3. **Tests**:
   - Cache hit path
   - Cache miss path
   - TTL verification
   - Graceful degradation

---

**Related**: ADR-SUMMARY-CACHE (versioning, TTL), ADR-0052 (CacheProvider protocol), ADR-0127 (Graceful Degradation), reference/PATTERNS.md (full catalog)

**Supersedes**: Individual ADRs ADR-0119, ADR-0124, ADR-0116, ADR-0134, ADR-0050, ADR-0087
