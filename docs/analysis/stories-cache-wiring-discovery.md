# Stories Cache Wiring Discovery

> Session 1 Discovery Document for PROMPT-0-CACHE-PERF-STORIES

## Executive Summary

The `StoriesClient` currently fetches stories via `list_for_task_async()` returning a `PageIterator[Story]`, with no cache integration. The `cache/stories.py` module has a fully-implemented `load_stories_incremental()` function that supports Asana's `since` parameter for incremental fetching, story merging, and cache population. **Wiring requires adding a new method** (`list_for_task_cached_async()`) to preserve backward compatibility while enabling cache-aware incremental fetching. The integration is straightforward but requires a fetcher adapter to bridge PageIterator's lazy pagination with the loader's eager list requirement.

---

## Current State Analysis

### StoriesClient Implementation

| Attribute | Value |
|-----------|-------|
| Location | `/src/autom8_asana/clients/stories.py` |
| Key Method | `list_for_task_async(task_gid, opt_fields, limit)` |
| Return Type | `PageIterator[Story]` (lazy pagination) |
| Cache Usage | **None** - fetches directly via HTTP |
| Base Class | `BaseClient` with `self._cache` available |

**Current Flow (Lines 288-322):**
```python
def list_for_task_async(self, task_gid: str, ...) -> PageIterator[Story]:
    async def fetch_page(offset: str | None) -> tuple[list[Story], str | None]:
        params = self._build_opt_fields(opt_fields)
        params["limit"] = min(limit, 100)
        if offset:
            params["offset"] = offset
        data, next_offset = await self._http.get_paginated(
            f"/tasks/{task_gid}/stories", params=params
        )
        stories = [Story.model_validate(s) for s in data]
        return stories, next_offset
    return PageIterator(fetch_page, page_size=min(limit, 100))
```

**Key Observations:**
1. Returns `PageIterator[Story]` - lazy evaluation, one page at a time
2. No `since` parameter support - always fetches all stories
3. Converts to `Story` models immediately (loader expects `dict`)
4. `self._cache` is available via `BaseClient` but unused

### Incremental Loader Infrastructure

| Attribute | Value |
|-----------|-------|
| Location | `/src/autom8_asana/cache/stories.py` |
| Key Function | `load_stories_incremental()` |
| Entry Type | `EntryType.STORIES` (already defined) |
| Status | **Fully implemented and tested** |

**Signature:**
```python
async def load_stories_incremental(
    task_gid: str,
    cache: CacheProvider,
    fetcher: Callable[[str, str | None], Awaitable[list[dict[str, Any]]]],
    current_modified_at: str | None = None,
) -> tuple[list[dict[str, Any]], CacheEntry | None, bool]:
```

**Key Features Already Implemented:**
- `EntryType.STORIES` in cache entry types
- Incremental fetch using Asana `since` parameter
- Story merging with deduplication by GID (`_merge_stories()`)
- Cache entry with `last_fetched` metadata
- `filter_relevant_stories()` for struc-relevant story types
- `get_latest_story_timestamp()` for tracking
- 17 comprehensive unit tests in `test_stories.py`

### Helper Functions Available

| Function | Purpose |
|----------|---------|
| `_create_stories_entry()` | Creates CacheEntry with `last_fetched` metadata |
| `_extract_stories_list()` | Extracts stories from cache entry data wrapper |
| `_merge_stories()` | Merges existing + new, dedupes by GID, sorts by `created_at` |
| `filter_relevant_stories()` | Filters to struc-relevant `resource_subtypes` |
| `get_latest_story_timestamp()` | Gets latest `created_at` for next `since` value |

---

## Integration Analysis

### Q1: Integration Point Design

**Problem:**
- Current `list_for_task_async()` returns `PageIterator[Story]` (lazy evaluation)
- `load_stories_incremental()` expects fetcher returning `list[dict]` (eager, all at once)
- These are fundamentally different execution models

**Options Evaluated:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Modify `list_for_task_async()` | Single method | Breaks PageIterator consumers, changes return type |
| B | New method `list_for_task_cached_async()` | Preserves compatibility | Two methods for similar purpose |
| C | Add `use_cache=True` parameter | Single method | Complex overloading, confusing API |

**Recommendation: Option B - New Method**

Create `list_for_task_cached_async()` that:
- Calls `load_stories_incremental()` internally
- Returns `list[Story]` (not PageIterator)
- Accepts optional `task_modified_at` for versioning
- Preserves `list_for_task_async()` for PageIterator consumers

**Rationale:**
1. No breaking changes to existing consumers
2. Clear semantic distinction (cached vs. non-cached)
3. Matches established pattern (clients have multiple list methods)
4. Cache-aware method returns eager list (natural for cached data)

---

### Q2: Fetcher Adapter Design

**Requirement:** Create a fetcher compatible with `load_stories_incremental()`:
```python
Callable[[str, str | None], Awaitable[list[dict[str, Any]]]]
# Takes: (task_gid, since_timestamp)
# Returns: list of story dicts
```

**Proposed Design:**

```python
async def _create_stories_fetcher(
    self,
    task_gid: str,
    opt_fields: list[str] | None = None,
) -> Callable[[str, str | None], Awaitable[list[dict[str, Any]]]]:
    """Create a fetcher function for load_stories_incremental.

    The fetcher:
    1. Accepts (task_gid, since) where since is ISO timestamp or None
    2. Fetches ALL pages (eager, not lazy)
    3. Returns list[dict] (raw API response, not Story models)
    4. Passes `since` to Asana API when provided
    """
    async def fetcher(gid: str, since: str | None) -> list[dict[str, Any]]:
        params = self._build_opt_fields(opt_fields)
        params["limit"] = 100
        if since:
            params["since"] = since  # Asana's incremental parameter

        all_stories: list[dict[str, Any]] = []
        offset: str | None = None

        while True:
            if offset:
                params["offset"] = offset
            data, next_offset = await self._http.get_paginated(
                f"/tasks/{gid}/stories", params=params
            )
            all_stories.extend(data)  # Raw dicts, not Story models
            if next_offset is None:
                break
            offset = next_offset

        return all_stories

    return fetcher
```

**Key Design Decisions:**
1. **Eager fetching:** Collects all pages before returning (required by loader)
2. **Raw dicts:** Returns `dict`, not `Story` models (loader expects dicts)
3. **since parameter:** Passes to Asana API when provided
4. **Pagination handled:** Loops through all pages internally

---

### Q3: current_modified_at Source

**Context:** `load_stories_incremental()` accepts `current_modified_at` for cache versioning:
```python
current_modified_at: str | None = None  # Task's modified_at for versioning
```

**Options Evaluated:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Accept as parameter | Caller provides, no extra API call | Caller must know task.modified_at |
| B | Fetch task separately | Always accurate | Extra API call, defeats caching purpose |
| C | Use `last_fetched` only | Simpler, no extra data needed | Less precise cache invalidation |
| D | Make optional | Flexibility | May be confusing |

**Recommendation: Option A - Accept as Optional Parameter**

```python
async def list_for_task_cached_async(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,  # Caller provides if available
    opt_fields: list[str] | None = None,
) -> list[Story]:
```

**Rationale:**
1. Caller often has task already (e.g., in struc computation pipeline)
2. No extra API call when caller has the data
3. Falls back gracefully when not provided (uses current time)
4. Matches loader's existing optional parameter design

---

### Q4: Return Type Design

**Context:** `load_stories_incremental()` returns:
```python
tuple[list[dict[str, Any]], CacheEntry | None, bool]
# (merged_stories, cache_entry, was_incremental_fetch)
```

**Options Evaluated:**

| Option | Return Type | Pros | Cons |
|--------|-------------|------|------|
| A | `list[Story]` | Simple, matches other clients | Loses cache metadata |
| B | `StoriesCacheResult` dataclass | Rich metadata | New type, more complex |
| C | `list[Story]` + optional out-param | Simple default, optional metadata | Unusual pattern |

**Recommendation: Option A (Simple) with Option B available later**

**Phase 1:** Return `list[Story]` for simplicity
```python
async def list_for_task_cached_async(...) -> list[Story]:
    stories, _, _ = await load_stories_incremental(...)
    return [Story.model_validate(s) for s in stories]
```

**Phase 2 (if needed):** Add metrics/observability via logging
- Log `was_incremental_fetch` for observability
- Track cache hit/miss in metrics

**Rationale:**
1. Simple API matches other client methods
2. Cache metadata is internal implementation detail
3. Observability via logging, not return type
4. Can add richer return type later if proven need exists

---

### Q5: Story Consumer Compatibility

**Story Consumers Identified:**

| Consumer | Usage | Impact |
|----------|-------|--------|
| `automation/pipeline.py` | `create_comment_async()` only | **None** - write operation |
| Tests | `list_for_task_async()` for PageIterator | **None** - unchanged |
| Struc computation | (Not currently using stories) | **Potential future consumer** |

**Analysis:**

1. **No current consumers of `list_for_task_async()` for reading**
   - Only `create_comment_async()` is used in production code
   - Story listing is available but not actively consumed

2. **Struc computation pipeline could benefit**
   - `filter_relevant_stories()` exists for struc-relevant story types
   - `DEFAULT_STORY_TYPES` defines relevant `resource_subtypes`
   - Integration point exists but is not yet connected

3. **filter_relevant_stories() usage**
   - Should be called by **caller**, not in client
   - Client returns all stories; caller filters as needed
   - Maintains separation of concerns

**Compatibility Conclusion:**
- No breaking changes needed
- New method is additive
- Existing PageIterator pattern preserved

---

## Proposed Integration Flow

### Current Flow (No Cache)

```
client.stories.list_for_task_async(task_gid)
    |
    v
PageIterator created (lazy)
    |
    v (on iteration)
GET /tasks/{gid}/stories (no since)
    |
    v
Returns ALL stories (could be hundreds)
    |
    v
Story.model_validate() per item
    |
    v
Yields Story objects one at a time
```

### Proposed Flow (With Cache)

```
client.stories.list_for_task_cached_async(task_gid, task_modified_at)
    |
    v
Check self._cache is available
    |
    +-- No cache --> Direct fetch (full), return list[Story]
    |
    v (cache available)
load_stories_incremental(task_gid, cache, fetcher, task_modified_at)
    |
    +-- Cache miss --> fetcher(task_gid, None) --> Full fetch
    |
    +-- Cache hit --> fetcher(task_gid, last_fetched) --> Incremental fetch
    |
    v
_merge_stories(cached, new) --> Dedupe by GID, sort by created_at
    |
    v
Cache updated with merged stories + new last_fetched
    |
    v
[Story.model_validate(s) for s in merged]
    |
    v
Returns list[Story] (eager, all at once)
```

### API Change Summary

```python
# EXISTING - Unchanged
def list_for_task_async(
    self,
    task_gid: str,
    *,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Story]:
    """List stories (lazy pagination, no cache)."""

# NEW - Added
async def list_for_task_cached_async(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
    """List stories with incremental caching.

    Uses Asana 'since' parameter for incremental fetching.
    Merges new stories with cached, dedupes by GID.

    Args:
        task_gid: Task GID
        task_modified_at: Task's modified_at for cache versioning
        opt_fields: Fields to include

    Returns:
        list[Story] - All stories (cached + new)
    """
```

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Eager fetch memory pressure** | High memory for tasks with many stories | Low | Most tasks have <100 stories; can add pagination limit |
| **Cache provider unavailable** | Method fails if cache required | Medium | Graceful degradation: fallback to full fetch when `self._cache` is None |
| **Merge correctness edge cases** | Data corruption, duplicate stories | Low | Existing tests cover merge; add integration tests |
| **Asana `since` parameter behavior** | May not work as expected | Low | Well-documented in Asana API; existing tests verify |
| **Performance regression on first fetch** | Slower than current | Very Low | First fetch is same as current (full fetch path) |
| **Story model validation failures** | Crash on unexpected data | Low | Story model uses `extra="ignore"` for forward compatibility |

---

## Open Questions for Architecture Phase

All critical questions have been resolved. The following are design clarifications for Architect:

1. **Sync wrapper:** Should `list_for_task_cached()` (sync) be added alongside async?
   - Recommendation: Yes, follow existing pattern with `@sync_wrapper`

2. **Metrics approach:** Structured logging vs. dedicated metrics?
   - Recommendation: Start with structured logging (`was_incremental_fetch`), add metrics in P2

3. **Cache TTL for stories:** Should stories have custom TTL?
   - Recommendation: Use default (300s) initially; stories don't change frequently

---

## Recommendation

**Proceed to Requirements Phase (Session 2)** with the following confirmed approach:

### Integration Strategy
1. **New method:** `list_for_task_cached_async()` returning `list[Story]`
2. **Preserve existing:** `list_for_task_async()` unchanged (PageIterator)
3. **Use existing loader:** `load_stories_incremental()` from `cache/stories.py`

### Implementation Components
1. **Fetcher adapter:** Create `_make_stories_fetcher()` internal method
2. **Cache integration:** Use `self._cache` from BaseClient
3. **Graceful degradation:** Fallback to full fetch when cache unavailable
4. **Model conversion:** Convert loader's `list[dict]` to `list[Story]`

### Success Criteria Validated
1. Infrastructure exists and is tested
2. Integration points are clear
3. No breaking changes required
4. Performance improvement achievable (incremental fetch)

---

## Appendix: File References

| File | Purpose |
|------|---------|
| `/src/autom8_asana/clients/stories.py` | StoriesClient - add new method here |
| `/src/autom8_asana/cache/stories.py` | Incremental loader - use as-is |
| `/src/autom8_asana/clients/base.py` | BaseClient with `self._cache` |
| `/src/autom8_asana/cache/entry.py` | `EntryType.STORIES` |
| `/tests/unit/cache/test_stories.py` | Existing loader tests |

---

*Discovery completed: 2025-12-23*
*Next: Session 2 - Requirements Definition (PRD-CACHE-PERF-STORIES)*
