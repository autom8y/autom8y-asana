# TDD-CACHE-PERF-STORIES: Stories Client Incremental Cache Integration

## Metadata
- **TDD ID**: TDD-CACHE-PERF-STORIES
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: [PRD-CACHE-PERF-STORIES](../requirements/PRD-CACHE-PERF-STORIES.md)
- **Related TDDs**: [TDD-CACHE-INTEGRATION](TDD-CACHE-INTEGRATION.md)
- **Related ADRs**: [ADR-0020-incremental-story-loading](../decisions/ADR-0020-incremental-story-loading.md), [ADR-0127-graceful-degradation](../decisions/ADR-0127-graceful-degradation.md), [ADR-0129-stories-client-cache-wiring](../decisions/ADR-0129-stories-client-cache-wiring.md)

---

## 1. Overview

This TDD specifies the technical design for wiring `StoriesClient` to the existing `load_stories_incremental()` infrastructure. The incremental loader is fully implemented in `cache/stories.py` (per ADR-0020) but is not yet wired to any client method. This design introduces a new `list_for_task_cached_async()` method that leverages the incremental cache loader, enabling story caching with Asana's `since` parameter for efficient repeat fetches.

**Key Design Principle**: Add new capability via a dedicated method. The existing `list_for_task_async()` remains unchanged, preserving backward compatibility and PageIterator semantics.

---

## 2. Requirements Summary

Per PRD-CACHE-PERF-STORIES, this design addresses:

| Category | Count | Summary |
|----------|-------|---------|
| FR-CLIENT-* | 5 | New cached method and sync wrapper |
| FR-FETCH-* | 6 | Loader-compatible fetcher adapter |
| FR-CACHE-* | 5 | Integration with `load_stories_incremental()` |
| FR-MERGE-* | 3 | Story merging (satisfied by existing loader) |
| FR-DEGRADE-* | 3 | Graceful degradation without cache |
| NFR-PERF-* | 5 | <100ms incremental fetch latency |
| NFR-COMPAT-* | 4 | No breaking changes |
| NFR-OBS-* | 3 | Structured logging |

---

## 3. System Context

```
+-------------------------------------------------------------------------+
|                           StoriesClient                                   |
|  +-------------------------------------------------------------------+  |
|  |                  list_for_task_cached_async()                     |  |
|  |                                                                   |  |
|  |  1. Check if cache provider available                             |  |
|  |  2. Create fetcher adapter (_make_stories_fetcher)                |  |
|  |  3. Call load_stories_incremental()                               |  |
|  |  4. Convert raw dicts to Story models                             |  |
|  |  5. Return list[Story]                                            |  |
|  +-------------------------------------------------------------------+  |
|                             |                                           |
|                             v                                           |
|  +-------------------------------------------------------------------+  |
|  |  _make_stories_fetcher() -> Callable                              |  |
|  |  - Closure over task_gid, opt_fields                              |  |
|  |  - Accepts (task_gid, since) -> list[dict]                        |  |
|  |  - Uses self._http.get_paginated() with since param               |  |
|  |  - Collects all pages eagerly                                     |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------------+
|                    cache/stories.py                                       |
|  +-------------------------------------------------------------------+  |
|  |  load_stories_incremental()                                       |  |
|  |  - Manages cache entry lifecycle                                  |  |
|  |  - Calls fetcher with since parameter                             |  |
|  |  - Merges cached + new stories                                    |  |
|  |  - Returns (stories, entry, was_incremental)                      |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------------+
|                    CacheProvider                                          |
|  - get_versioned(task_gid, EntryType.STORIES)                           |
|  - set_versioned(task_gid, CacheEntry)                                  |
+-------------------------------------------------------------------------+
```

---

## 4. Component Architecture

### 4.1 StoriesClient.list_for_task_cached_async() (NEW)

**Location**: `src/autom8_asana/clients/stories.py`

**Purpose**: Provide cache-aware story fetching using the incremental loader.

```python
async def list_for_task_cached_async(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    """List stories for a task with incremental caching.

    Uses the existing load_stories_incremental() infrastructure to:
    - Check cache for existing stories
    - Fetch only new stories via Asana's 'since' parameter
    - Merge and deduplicate by story GID
    - Update cache with merged result

    Per ADR-0129: New method pattern chosen over modifying existing
    list_for_task_async() to preserve PageIterator semantics.

    Args:
        task_gid: Task GID.
        task_modified_at: Optional task modified_at timestamp for cache
            versioning. If provided, used as cache entry version.
        opt_fields: Fields to include in API response.

    Returns:
        list[Story] - All stories for the task, sorted by created_at.

    Example:
        >>> stories = await client.stories.list_for_task_cached_async("123")
        >>> # Second call uses incremental fetch (only new stories)
        >>> stories = await client.stories.list_for_task_cached_async("123")
    """
```

**Traceability**: FR-CLIENT-001, FR-CLIENT-003, FR-CLIENT-004, FR-CACHE-005

---

### 4.2 StoriesClient.list_for_task_cached() (NEW)

**Location**: `src/autom8_asana/clients/stories.py`

**Purpose**: Sync wrapper for cached story fetching.

```python
def list_for_task_cached(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    """List stories for a task with incremental caching (sync).

    Synchronous wrapper for list_for_task_cached_async().
    Per ADR-0002: Uses sync_wrapper pattern.

    Args:
        task_gid: Task GID.
        task_modified_at: Optional task modified_at for cache versioning.
        opt_fields: Fields to include in API response.

    Returns:
        list[Story] - All stories for the task, sorted by created_at.
    """
    return self._list_for_task_cached_sync(
        task_gid,
        task_modified_at=task_modified_at,
        opt_fields=opt_fields,
    )

@sync_wrapper("list_for_task_cached_async")
async def _list_for_task_cached_sync(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    """Internal sync wrapper implementation."""
    return await self.list_for_task_cached_async(
        task_gid,
        task_modified_at=task_modified_at,
        opt_fields=opt_fields,
    )
```

**Traceability**: FR-CLIENT-002

---

### 4.3 StoriesClient._make_stories_fetcher() (NEW)

**Location**: `src/autom8_asana/clients/stories.py`

**Purpose**: Create a fetcher function compatible with `load_stories_incremental()` signature.

```python
def _make_stories_fetcher(
    self,
    opt_fields: list[str] | None,
) -> Callable[[str, str | None], Awaitable[list[dict[str, Any]]]]:
    """Create a fetcher function for load_stories_incremental().

    The returned fetcher:
    - Accepts (task_gid, since) arguments
    - Returns list[dict] (raw API response, not Story models)
    - Eagerly collects all pages before returning
    - Passes 'since' to Asana API when provided

    Per FR-FETCH-001: Matches loader's expected signature.
    Per FR-FETCH-003: Eager pagination (all pages collected).
    Per FR-FETCH-004: Returns raw dicts, not models.

    Args:
        opt_fields: Fields to include in API response.

    Returns:
        Async callable matching load_stories_incremental() fetcher signature.
    """
    async def fetcher(task_gid: str, since: str | None) -> list[dict[str, Any]]:
        """Fetch all stories for a task, optionally since a timestamp."""
        params = self._build_opt_fields(opt_fields)
        params["limit"] = 100

        # FR-FETCH-002, FR-FETCH-005: Only include 'since' when provided
        if since is not None:
            params["since"] = since

        # FR-FETCH-003: Eagerly collect all pages
        all_stories: list[dict[str, Any]] = []
        offset: str | None = None

        while True:
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/stories",
                params=params,
            )
            all_stories.extend(data)

            if not next_offset:
                break
            offset = next_offset

        return all_stories

    return fetcher
```

**Traceability**: FR-FETCH-001, FR-FETCH-002, FR-FETCH-003, FR-FETCH-004, FR-FETCH-005, FR-FETCH-006

---

### 4.4 Integration with load_stories_incremental()

**Location**: Within `list_for_task_cached_async()`

**Purpose**: Wire the fetcher to the existing incremental loader.

```python
async def list_for_task_cached_async(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    """Implementation body."""
    self._log_operation("list_for_task_cached_async", task_gid)

    # FR-DEGRADE-001: Fallback without cache
    if self._cache is None:
        logger.debug(
            "No cache provider, performing full fetch for task %s",
            task_gid,
            extra={"task_gid": task_gid, "cache_available": False},
        )
        return await self._fetch_all_stories_uncached(task_gid, opt_fields)

    try:
        from autom8_asana.cache.stories import load_stories_incremental

        # FR-FETCH-001: Create loader-compatible fetcher
        fetcher = self._make_stories_fetcher(opt_fields)

        # FR-CACHE-001: Use incremental loader
        stories_dicts, cache_entry, was_incremental = await load_stories_incremental(
            task_gid=task_gid,
            cache=self._cache,
            fetcher=fetcher,
            current_modified_at=task_modified_at,  # FR-CACHE-005
        )

        # NFR-OBS-001, NFR-OBS-002: Log fetch type and result
        logger.debug(
            "Stories loaded for task %s: %d stories, incremental=%s",
            task_gid,
            len(stories_dicts),
            was_incremental,
            extra={
                "task_gid": task_gid,
                "story_count": len(stories_dicts),
                "was_incremental": was_incremental,
                "cache_hit": was_incremental,
            },
        )

        # Convert dicts to Story models
        return [Story.model_validate(s) for s in stories_dicts]

    except Exception as exc:
        # FR-DEGRADE-002, FR-DEGRADE-003: Log and fallback
        logger.warning(
            "Cache operation failed for stories (task=%s): %s, falling back to full fetch",
            task_gid,
            exc,
            extra={"task_gid": task_gid, "error": str(exc)},
        )
        return await self._fetch_all_stories_uncached(task_gid, opt_fields)
```

**Traceability**: FR-CACHE-001, FR-CACHE-002, FR-CACHE-003, FR-CACHE-004, FR-CACHE-005, FR-DEGRADE-001, FR-DEGRADE-002, FR-DEGRADE-003

---

### 4.5 StoriesClient._fetch_all_stories_uncached() (NEW)

**Location**: `src/autom8_asana/clients/stories.py`

**Purpose**: Fallback method for fetching all stories without cache.

```python
async def _fetch_all_stories_uncached(
    self,
    task_gid: str,
    opt_fields: list[str] | None,
) -> list[Story]:
    """Fetch all stories without caching (fallback path).

    Used when:
    - Cache provider is None (FR-DEGRADE-001)
    - Cache operation fails (FR-DEGRADE-003)

    Args:
        task_gid: Task GID.
        opt_fields: Fields to include.

    Returns:
        list[Story] - All stories, eagerly collected.
    """
    params = self._build_opt_fields(opt_fields)
    params["limit"] = 100

    all_stories: list[Story] = []
    offset: str | None = None

    while True:
        if offset:
            params["offset"] = offset

        data, next_offset = await self._http.get_paginated(
            f"/tasks/{task_gid}/stories",
            params=params,
        )
        all_stories.extend([Story.model_validate(s) for s in data])

        if not next_offset:
            break
        offset = next_offset

    return all_stories
```

**Traceability**: FR-DEGRADE-001, FR-DEGRADE-003

---

## 5. Sequence Diagrams

### 5.1 Cache Miss Flow (First Fetch)

```
+-------+      +---------------+      +-------------------+      +---------------+      +------+
| User  |      | StoriesClient |      | load_stories_inc. |      | CacheProvider |      | HTTP |
+---+---+      +-------+-------+      +---------+---------+      +-------+-------+      +--+---+
    |                  |                        |                        |                 |
    | list_for_task_cached_async("123")         |                        |                 |
    |----------------->|                        |                        |                 |
    |                  |                        |                        |                 |
    |                  | _make_stories_fetcher()|                        |                 |
    |                  |----------------------->|                        |                 |
    |                  |                        |                        |                 |
    |                  | load_stories_incremental(task_gid, cache, fetcher)               |
    |                  |----------------------->|                        |                 |
    |                  |                        |                        |                 |
    |                  |                        | get_versioned("123", STORIES)           |
    |                  |                        |----------------------->|                 |
    |                  |                        |                        |                 |
    |                  |                        |         None           |                 |
    |                  |                        |<-----------------------|                 |
    |                  |                        |                        |                 |
    |                  |                        | fetcher("123", None)   |                 |
    |                  |                        |-------------------------------------------->|
    |                  |                        |                        |                 |
    |                  |                        |              [story_dicts]               |
    |                  |                        |<--------------------------------------------|
    |                  |                        |                        |                 |
    |                  |                        | set_versioned("123", entry)             |
    |                  |                        |----------------------->|                 |
    |                  |                        |                        |                 |
    |                  |   (stories, entry, False)                       |                 |
    |                  |<-----------------------|                        |                 |
    |                  |                        |                        |                 |
    |                  | [Story.model_validate()]                        |                 |
    |                  |                        |                        |                 |
    |   list[Story]    |                        |                        |                 |
    |<-----------------|                        |                        |                 |
```

### 5.2 Cache Hit Flow (Incremental Fetch)

```
+-------+      +---------------+      +-------------------+      +---------------+      +------+
| User  |      | StoriesClient |      | load_stories_inc. |      | CacheProvider |      | HTTP |
+---+---+      +-------+-------+      +---------+---------+      +-------+-------+      +--+---+
    |                  |                        |                        |                 |
    | list_for_task_cached_async("123")         |                        |                 |
    |----------------->|                        |                        |                 |
    |                  |                        |                        |                 |
    |                  | load_stories_incremental(...)                   |                 |
    |                  |----------------------->|                        |                 |
    |                  |                        |                        |                 |
    |                  |                        | get_versioned("123", STORIES)           |
    |                  |                        |----------------------->|                 |
    |                  |                        |                        |                 |
    |                  |                        | CacheEntry(metadata={last_fetched: T1}) |
    |                  |                        |<-----------------------|                 |
    |                  |                        |                        |                 |
    |                  |                        | fetcher("123", T1)     |                 |
    |                  |                        |------------------------|---------------->|
    |                  |                        |                        |                 |
    |                  |                        |      [2 new stories]   |                 |
    |                  |                        |<-----------------------|-----------------|
    |                  |                        |                        |                 |
    |                  |                        | _merge_stories(50 cached, 2 new)        |
    |                  |                        |                        |                 |
    |                  |                        | set_versioned("123", merged_entry)      |
    |                  |                        |----------------------->|                 |
    |                  |                        |                        |                 |
    |                  |  (52 stories, entry, True)                      |                 |
    |                  |<-----------------------|                        |                 |
    |                  |                        |                        |                 |
    |   list[Story]    |                        |                        |                 |
    |<-----------------|                        |                        |                 |
```

### 5.3 Graceful Degradation Flow

```
+-------+      +---------------+      +-------------------+      +---------------+      +------+
| User  |      | StoriesClient |      | load_stories_inc. |      | CacheProvider |      | HTTP |
+---+---+      +-------+-------+      +---------+---------+      +-------+-------+      +--+---+
    |                  |                        |                        |                 |
    | list_for_task_cached_async("123")         |                        |                 |
    |----------------->|                        |                        |                 |
    |                  |                        |                        |                 |
    |                  | load_stories_incremental(...)                   |                 |
    |                  |----------------------->|                        |                 |
    |                  |                        |                        |                 |
    |                  |                        | get_versioned("123", STORIES)           |
    |                  |                        |----------------------->|                 |
    |                  |                        |                        |                 |
    |                  |                        |   ConnectionError!     |                 |
    |                  |                        |<-----------------------|                 |
    |                  |                        |                        |                 |
    |                  |   Exception raised     |                        |                 |
    |                  |<-----------------------|                        |                 |
    |                  |                        |                        |                 |
    |                  | [Log WARNING]          |                        |                 |
    |                  |                        |                        |                 |
    |                  | _fetch_all_stories_uncached()                   |                 |
    |                  |---------------------------------------------------->|
    |                  |                        |                        |                 |
    |                  |                      [story_dicts]              |                 |
    |                  |<----------------------------------------------------|
    |                  |                        |                        |                 |
    |   list[Story]    |                        |                        |                 |
    |<-----------------|                        |                        |                 |
```

---

## 6. Interface Definitions

### 6.1 New Public Methods

```python
# StoriesClient.list_for_task_cached_async
async def list_for_task_cached_async(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    ...

# StoriesClient.list_for_task_cached
def list_for_task_cached(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    ...
```

### 6.2 Internal Methods

```python
# Fetcher factory
def _make_stories_fetcher(
    self,
    opt_fields: list[str] | None,
) -> Callable[[str, str | None], Awaitable[list[dict[str, Any]]]]:
    ...

# Uncached fallback
async def _fetch_all_stories_uncached(
    self,
    task_gid: str,
    opt_fields: list[str] | None,
) -> list[Story]:
    ...

# Sync wrapper implementation
@sync_wrapper("list_for_task_cached_async")
async def _list_for_task_cached_sync(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    ...
```

### 6.3 Existing Interfaces Used (No Modification)

```python
# From cache/stories.py - used as-is
async def load_stories_incremental(
    task_gid: str,
    cache: CacheProvider,
    fetcher: Callable[[str, str | None], Awaitable[list[dict[str, Any]]]],
    current_modified_at: str | None = None,
) -> tuple[list[dict[str, Any]], CacheEntry | None, bool]:
    ...

# From BaseClient - inherited
def _cache(self) -> CacheProvider | None: ...
def _build_opt_fields(self, opt_fields: list[str] | None) -> dict[str, Any]: ...
def _log_operation(self, operation: str, resource_gid: str | None = None) -> None: ...
```

---

## 7. Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| API extension strategy | New method | Preserves PageIterator for existing consumers | [ADR-0129](../decisions/ADR-0129-stories-client-cache-wiring.md) |
| Fetcher implementation | Closure factory | Clean encapsulation of opt_fields | ADR-0129 |
| Error handling | Try/except with fallback | Matches ADR-0127 graceful degradation | [ADR-0127](../decisions/ADR-0127-graceful-degradation.md) |
| Sync wrapper | @sync_wrapper decorator | Matches existing client patterns | [ADR-0002](../decisions/ADR-0002-sync-wrapper-strategy.md) |

---

## 8. Complexity Assessment

**Level**: Module

**Justification**:
- Single component (StoriesClient) with focused responsibility
- No new infrastructure components required
- Uses existing `load_stories_incremental()` without modification
- Clear API boundary (two new public methods)
- No cross-cutting concerns or distributed complexity

**What would force higher complexity**:
- If we needed to modify the incremental loader -> Service
- If we needed new cache entry types -> Module (but more work)
- If we coordinated with multiple clients -> Service

---

## 9. Implementation Plan

### Phase 1: Core Implementation (Single Session)

| Task | File | Estimated Lines |
|------|------|-----------------|
| Add `list_for_task_cached_async()` | `clients/stories.py` | ~50 |
| Add `_make_stories_fetcher()` | `clients/stories.py` | ~30 |
| Add `_fetch_all_stories_uncached()` | `clients/stories.py` | ~25 |
| Add sync wrapper | `clients/stories.py` | ~20 |
| Add imports | `clients/stories.py` | ~5 |

**Total**: ~130 lines

### Phase 2: Testing (Same Session)

| Task | File | Coverage |
|------|------|----------|
| Unit tests for cached method | `tests/unit/clients/test_stories_cache.py` | Cache hit/miss |
| Unit tests for fetcher | `tests/unit/clients/test_stories_cache.py` | Pagination, since param |
| Unit tests for degradation | `tests/unit/clients/test_stories_cache.py` | No cache, cache failure |
| Integration with loader tests | `tests/integration/test_stories_cache.py` | End-to-end flow |

**Exit Criteria**:
- [ ] `list_for_task_cached_async()` returns cached stories on second call
- [ ] Incremental fetch uses `since` parameter
- [ ] Fallback works when cache unavailable
- [ ] All existing `list_for_task_async()` tests pass unchanged

---

## 10. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Memory pressure with many stories | Medium | Low | Most tasks have <100 stories; loader already handles this |
| Cache provider unavailable | Medium | Medium | FR-DEGRADE-001: Graceful fallback to full fetch |
| Story model validation failures | Low | Low | Story model uses `extra="ignore"` per ADR-0005 |
| Merge correctness issues | Medium | Very Low | Existing `_merge_stories()` has test coverage |
| Performance regression on first fetch | Low | Very Low | First fetch identical to current behavior |

---

## 11. Observability Strategy

### 11.1 Logging

| Event | Level | Fields |
|-------|-------|--------|
| Incremental fetch complete | DEBUG | `task_gid`, `story_count`, `was_incremental` |
| Cache fallback (no provider) | DEBUG | `task_gid`, `cache_available=False` |
| Cache operation failed | WARNING | `task_gid`, `error` |

### 11.2 Structured Logging Format

```python
logger.debug(
    "Stories loaded for task %s",
    task_gid,
    extra={
        "task_gid": task_gid,
        "story_count": len(stories),
        "was_incremental": was_incremental,
        "cache_hit": was_incremental,
    },
)
```

**Traceability**: NFR-OBS-001, NFR-OBS-002, NFR-OBS-003

---

## 12. Testing Strategy

### 12.1 Unit Tests

| Scenario | Input | Expected Output |
|----------|-------|-----------------|
| First fetch (cache miss) | Empty cache | Full fetch, cache populated |
| Second fetch (incremental) | Cached stories exist | Fetch since last_fetched |
| No cache provider | `self._cache = None` | Full fetch, no exception |
| Cache read fails | Cache raises exception | Warning logged, full fetch |
| Cache write fails | Cache raises on set | Warning logged, stories returned |
| Empty task (no stories) | Task with 0 stories | Empty list, cache populated |
| Multiple pages | Task with 150+ stories | All pages collected |
| opt_fields propagation | Custom fields | Fields in API request |

### 12.2 Mock Strategy

```python
@pytest.fixture
def mock_cache():
    """Mock cache provider for testing."""
    cache = Mock(spec=CacheProvider)
    cache.get_versioned.return_value = None  # Default: cache miss
    return cache

@pytest.fixture
def mock_http():
    """Mock HTTP client with paginated response."""
    http = AsyncMock()
    http.get_paginated.return_value = ([{"gid": "s1", "text": "test"}], None)
    return http
```

### 12.3 Integration Tests

| Scenario | Setup | Assertion |
|----------|-------|-----------|
| End-to-end cache flow | InMemoryCacheProvider | Second call faster |
| Merge behavior | Cached + new stories | Correct deduplication |
| sync wrapper | Sync context | Returns same result |

---

## 13. Open Questions

None - all design decisions resolved via PRD and discovery.

---

## 14. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial TDD |

---

## 15. Quality Gate Checklist

- [x] Traces to approved PRD
- [x] All significant decisions have ADRs
- [x] Component responsibilities clear
- [x] Interfaces defined with type signatures
- [x] Complexity level justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan actionable

---

## Appendix A: Requirement Traceability

| Requirement | Component | Method/Field |
|-------------|-----------|--------------|
| FR-CLIENT-001 | StoriesClient | list_for_task_cached_async() |
| FR-CLIENT-002 | StoriesClient | list_for_task_cached() |
| FR-CLIENT-003 | StoriesClient | list_for_task_cached_async() opt_fields param |
| FR-CLIENT-004 | StoriesClient | self._cache (inherited from BaseClient) |
| FR-CLIENT-005 | StoriesClient | list_for_task_async() unchanged |
| FR-FETCH-001 | StoriesClient | _make_stories_fetcher() signature |
| FR-FETCH-002 | StoriesClient | _make_stories_fetcher() since param |
| FR-FETCH-003 | StoriesClient | _make_stories_fetcher() while loop |
| FR-FETCH-004 | StoriesClient | _make_stories_fetcher() returns dict |
| FR-FETCH-005 | StoriesClient | _make_stories_fetcher() since omission |
| FR-FETCH-006 | StoriesClient | _make_stories_fetcher() opt_fields closure |
| FR-CACHE-001 | StoriesClient | load_stories_incremental() call |
| FR-CACHE-002 | cache/stories.py | EntryType.STORIES (existing) |
| FR-CACHE-003 | cache/stories.py | last_fetched metadata (existing) |
| FR-CACHE-004 | cache/stories.py | task_gid as key (existing) |
| FR-CACHE-005 | StoriesClient | task_modified_at parameter |
| FR-MERGE-001 | cache/stories.py | _merge_stories() (existing) |
| FR-MERGE-002 | cache/stories.py | _merge_stories() (existing) |
| FR-MERGE-003 | cache/stories.py | _merge_stories() (existing) |
| FR-DEGRADE-001 | StoriesClient | if self._cache is None fallback |
| FR-DEGRADE-002 | StoriesClient | except block logging |
| FR-DEGRADE-003 | StoriesClient | _fetch_all_stories_uncached() fallback |
| NFR-PERF-001 | Implementation | First fetch unchanged |
| NFR-PERF-002 | load_stories_incremental | since param reduces payload |
| NFR-PERF-003 | cache/stories.py | _merge_stories() (existing) |
| NFR-PERF-004 | load_stories_incremental | Cache hit path |
| NFR-PERF-005 | StoriesClient | Story.model_validate() loop |
| NFR-COMPAT-001 | StoriesClient | list_for_task_async() unchanged |
| NFR-COMPAT-002 | StoriesClient | list_for_task_async() unchanged |
| NFR-COMPAT-003 | Implementation | Python 3.10+ syntax |
| NFR-COMPAT-004 | Implementation | Type hints throughout |
| NFR-OBS-001 | StoriesClient | was_incremental logging |
| NFR-OBS-002 | StoriesClient | cache_hit logging |
| NFR-OBS-003 | StoriesClient | extra={} structured format |
