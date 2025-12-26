# ADR-0129: Stories Client Cache Wiring Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: SDK Team
- **Related**: [PRD-CACHE-PERF-STORIES](../requirements/PRD-CACHE-PERF-STORIES.md), [TDD-CACHE-PERF-STORIES](../design/TDD-CACHE-PERF-STORIES.md), [ADR-0020-incremental-story-loading](ADR-0020-incremental-story-loading.md), [ADR-0127-graceful-degradation](ADR-0127-graceful-degradation.md)

## Context

The `StoriesClient` provides story/comment operations for tasks. The current `list_for_task_async()` method fetches stories directly from the Asana API without cache integration, returning a `PageIterator[Story]` for lazy pagination.

Meanwhile, `cache/stories.py` contains a fully implemented `load_stories_incremental()` function (per ADR-0020) that:
- Checks cache for existing stories
- Uses Asana's `since` parameter for incremental fetching
- Merges new stories with cached stories (deduplication by GID)
- Updates cache with merged result

This incremental loader is currently unused. We need to wire `StoriesClient` to leverage this infrastructure.

**Forces at play:**
- Existing `list_for_task_async()` returns `PageIterator[Story]` (lazy evaluation)
- `load_stories_incremental()` requires eager evaluation (full fetch then cache)
- Existing consumers expect `PageIterator` semantics
- Cache integration requires different return type (`list[Story]`)
- Backward compatibility is critical (NFR-COMPAT-001)
- Performance benefits require incremental caching (NFR-PERF-002)

**The key question**: How should we wire `StoriesClient` to use the incremental cache loader?

## Decision

We will add a **new method** `list_for_task_cached_async()` that uses `load_stories_incremental()`, while leaving the existing `list_for_task_async()` unchanged.

```python
class StoriesClient(BaseClient):
    # EXISTING - unchanged
    def list_for_task_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Story]:
        """Returns PageIterator for lazy pagination."""
        ...

    # NEW - cache-aware
    async def list_for_task_cached_async(
        self,
        task_gid: str,
        *,
        task_modified_at: str | None = None,
        opt_fields: list[str] | None = None,
    ) -> list[Story]:
        """Returns list[Story] with incremental caching."""
        ...

    # NEW - sync wrapper
    def list_for_task_cached(
        self,
        task_gid: str,
        *,
        task_modified_at: str | None = None,
        opt_fields: list[str] | None = None,
    ) -> list[Story]:
        """Sync wrapper for cached method."""
        ...
```

**Key implementation details:**

1. **Fetcher adapter**: Create `_make_stories_fetcher()` that returns a closure matching `load_stories_incremental()`'s expected signature:
   ```python
   Callable[[str, str | None], Awaitable[list[dict[str, Any]]]]
   ```

2. **Cache integration**: Call `load_stories_incremental()` from the new method, passing the fetcher and cache provider.

3. **Model conversion**: Convert returned `list[dict]` to `list[Story]` after cache operations.

4. **Graceful degradation**: Fall back to full fetch when cache unavailable (per ADR-0127).

## Rationale

### Why a New Method?

| Concern | New Method Approach |
|---------|---------------------|
| Backward compatibility | 100% - existing method unchanged |
| Return type clarity | `list[Story]` clearly signals eager evaluation |
| Semantic distinction | "cached" in name signals caching behavior |
| API discoverability | Both methods visible, user chooses |
| Testing | Existing tests unaffected |

The alternative approaches (modify existing, add parameter) both have significant drawbacks detailed below.

### Why Not Modify Existing `list_for_task_async()`?

The existing method returns `PageIterator[Story]`, which provides:
- Lazy evaluation (pages fetched on demand)
- Memory efficiency for large result sets
- Ability to stop iteration early

Changing to `list[Story]` would:
- Break type contracts for existing consumers
- Force eager evaluation even when not needed
- Require migration effort for all callers

### Why Not Add `use_cache: bool` Parameter?

Adding a parameter like:
```python
async def list_for_task_async(
    self,
    task_gid: str,
    *,
    use_cache: bool = False,  # NEW
    ...
) -> PageIterator[Story] | list[Story]:
```

Problems:
- **Return type ambiguity**: Union return type complicates type checking
- **Conditional semantics**: Same method behaves differently based on flag
- **API confusion**: Users must remember flag to get caching
- **PageIterator incompatibility**: Cannot cache and return PageIterator

### Why Closure-Based Fetcher Factory?

The `_make_stories_fetcher()` method returns a closure that captures `opt_fields`:

```python
def _make_stories_fetcher(
    self,
    opt_fields: list[str] | None,
) -> Callable[[str, str | None], Awaitable[list[dict[str, Any]]]]:
    async def fetcher(task_gid: str, since: str | None) -> list[dict[str, Any]]:
        # Uses self._http and captured opt_fields
        ...
    return fetcher
```

Benefits:
- **Clean encapsulation**: Fetcher has exactly the signature the loader expects
- **Flexible configuration**: opt_fields captured at creation time
- **Testable**: Factory method can be unit tested independently
- **Matches loader contract**: No adapter layer needed

Alternative (partial application) was considered but closures are more idiomatic Python for this use case.

## Alternatives Considered

### Alternative 1: Modify Existing Method

- **Description**: Change `list_for_task_async()` to use caching and return `list[Story]`
- **Pros**:
  - Simpler API (one method)
  - Automatic caching for all callers
- **Cons**:
  - Breaking change (return type)
  - Loses PageIterator benefits
  - Forces eager evaluation
  - Migration required for all consumers
- **Why not chosen**: NFR-COMPAT-001 requires no breaking changes. PageIterator semantics are valuable.

### Alternative 2: Add `use_cache` Parameter

- **Description**: Add optional parameter to toggle caching behavior
- **Pros**:
  - Single method surface
  - Opt-in caching
- **Cons**:
  - Union return type (`PageIterator | list`)
  - Type checker cannot narrow return type
  - Confusing API (same method, different behavior)
  - Conditional logic complexity
- **Why not chosen**: Return type ambiguity makes type checking unreliable. Clear semantic distinction is better.

### Alternative 3: Decorator/Wrapper Approach

- **Description**: Create a caching wrapper that takes the existing method
- **Pros**:
  - Separation of concerns
  - Reusable pattern
- **Cons**:
  - Cannot intercept PageIterator iteration
  - Would require consuming all pages (defeating lazy evaluation)
  - Complex implementation for unclear benefit
- **Why not chosen**: PageIterator abstraction is incompatible with caching semantics.

### Alternative 4: Override with Optional Caching

- **Description**: Keep signature but cache internally, still return PageIterator
- **Pros**:
  - No API change
  - Transparent caching
- **Cons**:
  - PageIterator cannot be cached (it's a generator-like object)
  - Would cache per-page, not full story set
  - Cannot use incremental loader (expects full list)
- **Why not chosen**: Fundamentally incompatible with existing incremental loader design.

## Consequences

### Positive

- **Zero breaking changes**: Existing `list_for_task_async()` unchanged
- **Clear semantics**: `list_for_task_cached_async()` name signals behavior
- **Type safety**: Return type is unambiguous `list[Story]`
- **Performance option**: Users can choose cached path when appropriate
- **Incremental benefits**: Subsequent calls fetch only new stories

### Negative

- **API surface increase**: Two methods instead of one
- **User decision required**: Must choose between cached and non-cached
- **Documentation burden**: Need to explain when to use which method

### Neutral

- **Consistent with SDK patterns**: Other clients may follow same pattern
- **Fetcher factory is internal**: Implementation detail, not public API

## Compliance

How do we ensure this decision is followed?

1. **Code review**: New story-related methods should consider whether caching applies
2. **Documentation**: Clearly document when to use each method in docstrings
3. **Examples**: Provide usage examples showing both patterns
4. **Testing**: Verify both methods work correctly and independently

## Implementation Notes

### Method Placement

Add to `StoriesClient` after existing list methods:

```python
class StoriesClient(BaseClient):
    # ... existing methods ...

    # --- Cached Operations ---

    async def list_for_task_cached_async(self, ...) -> list[Story]:
        ...

    def list_for_task_cached(self, ...) -> list[Story]:
        ...

    def _make_stories_fetcher(self, ...) -> Callable[...]:
        ...

    async def _fetch_all_stories_uncached(self, ...) -> list[Story]:
        ...
```

### Imports Required

```python
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from autom8_asana.cache.stories import load_stories_incremental
from autom8_asana.models.story import Story
```

### Logging

Per NFR-OBS-001/002/003, log cache behavior:

```python
logger.debug(
    "Stories loaded for task %s: %d stories, incremental=%s",
    task_gid,
    len(stories),
    was_incremental,
    extra={"task_gid": task_gid, "was_incremental": was_incremental},
)
```
