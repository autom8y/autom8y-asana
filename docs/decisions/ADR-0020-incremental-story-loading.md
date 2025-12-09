# ADR-0020: Incremental Story Loading

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0002](../requirements/PRD-0002-intelligent-caching.md), [TDD-0008](../design/TDD-0008-intelligent-caching.md)

## Context

Asana tasks accumulate stories (comments, activity logs) over time. A heavily-commented task may have hundreds of stories. Each story fetch via API returns paginated results, potentially requiring multiple requests.

**Problem**:
- Full story reload for a task with 200 stories: ~3 API calls (100 per page)
- If only 2 new comments were added since last fetch, 198 stories are re-transferred
- This wastes API quota and increases latency

**Asana API capability**:
- Stories endpoint supports `since` parameter
- `GET /tasks/{gid}/stories?since={ISO_timestamp}` returns only stories created after timestamp
- Stories are immutable (no updates, only additions)

**Requirements**:
- FR-CACHE-025: Cache STORIES with incremental support
- FR-CACHE-041: Support `since` parameter for story loading
- FR-CACHE-042: Merge new stories with cached stories
- FR-CACHE-043: Atomic cache update after story merge

## Decision

**Use Asana API `since` parameter to fetch only new stories, merge with cached stories, and update cache atomically.**

### Implementation

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StoryCache:
    """Cached stories with metadata for incremental loading."""
    stories: list[dict]
    last_story_at: datetime  # Timestamp of newest story
    count: int


class StoriesClient:
    """Client for Asana Stories with incremental caching."""

    async def get_stories(
        self,
        task_gid: str,
        use_cache: bool = True,
    ) -> list[Story]:
        """Get all stories for a task with incremental loading.

        If cache exists:
        1. Fetch stories since last_story_at
        2. Merge new stories with cached
        3. Update cache atomically
        4. Return combined list

        If no cache:
        1. Fetch all stories
        2. Cache result
        3. Return list
        """
        if not use_cache:
            return await self._fetch_all_stories(task_gid)

        # Try to get cached stories
        cached = await self._cache.get_versioned(
            task_gid,
            EntryType.STORIES,
        )

        if cached is None:
            # No cache, full fetch
            stories = await self._fetch_all_stories(task_gid)
            await self._cache_stories(task_gid, stories)
            return stories

        # Incremental fetch
        last_story_at = cached.metadata.get("last_story_at")
        new_stories = await self._fetch_stories_since(task_gid, last_story_at)

        if not new_stories:
            # No new stories, return cached
            return [Story.model_validate(s) for s in cached.data["stories"]]

        # Merge: cached + new (new are appended, already in order)
        all_stories = cached.data["stories"] + [s.model_dump() for s in new_stories]

        # Update cache atomically
        await self._cache_stories(task_gid, all_stories)

        return [Story.model_validate(s) for s in all_stories]

    async def _fetch_stories_since(
        self,
        task_gid: str,
        since: datetime,
    ) -> list[Story]:
        """Fetch stories created after given timestamp."""
        stories = []
        params = {
            "since": since.isoformat(),
            "opt_fields": "created_at,created_by,text,type,resource_subtype",
        }

        async for page in self._http.paginate(f"/tasks/{task_gid}/stories", params):
            for story_data in page:
                stories.append(Story.model_validate(story_data))

        return stories

    async def _cache_stories(
        self,
        task_gid: str,
        stories: list[dict] | list[Story],
    ) -> None:
        """Cache stories with metadata."""
        if not stories:
            return

        # Determine last_story_at from newest story
        story_dicts = [
            s.model_dump() if isinstance(s, Story) else s
            for s in stories
        ]

        last_story_at = max(
            arrow.get(s["created_at"])
            for s in story_dicts
        ).datetime

        entry = CacheEntry(
            data={"stories": story_dicts},
            entry_type=EntryType.STORIES,
            version=last_story_at,
            cached_at=datetime.utcnow(),
            ttl=self._settings.ttl.get_ttl(entry_type="stories"),
            metadata={"last_story_at": last_story_at},
        )

        await self._cache.set_versioned(task_gid, entry)
```

### Cache Structure

```
asana:tasks:{gid}:stories
    data: {
        "stories": [
            {"gid": "s1", "created_at": "...", "text": "..."},
            {"gid": "s2", "created_at": "...", "text": "..."},
            ...
        ]
    }
    version: <last_story_at>
    cached_at: <cache write timestamp>
    metadata: {
        "last_story_at": "2025-12-09T10:30:00Z"
    }
```

### Merge Algorithm

```
Cached Stories:  [S1, S2, S3, S4, S5]  (last_story_at = S5.created_at)
                       |
                       v
API Call: GET /tasks/{gid}/stories?since=S5.created_at
                       |
                       v
New Stories:     [S6, S7]  (created after S5)
                       |
                       v
Merged Result:   [S1, S2, S3, S4, S5, S6, S7]
                       |
                       v
Cache Updated:   stories = merged, last_story_at = S7.created_at
```

## Rationale

**Why incremental over full reload?**

| Scenario | Full Reload | Incremental |
|----------|-------------|-------------|
| 200 stories, 2 new | 3 API calls | 1 API call |
| Payload transferred | 200 stories | 2 stories |
| Cache update | Full replace | Append + update |

For tasks with many stories, incremental is dramatically more efficient.

**Why use `created_at` as version?**

Stories are immutable:
- Once created, a story is never modified
- No updates, only additions
- `created_at` uniquely identifies story age

Using `created_at` of the newest story (`last_story_at`) as the version allows:
- Simple comparison for staleness
- Reliable `since` parameter for API

**Why atomic cache update?**

Race condition scenario without atomicity:
1. Process A reads cache, fetches new stories
2. Process B reads cache, fetches new stories
3. Process A writes merged result
4. Process B writes merged result (overwrites A's additions)

With Redis WATCH/MULTI:
1. WATCH the stories key
2. Read current value
3. Merge with new stories
4. MULTI: SET new value
5. EXEC (fails if key changed since WATCH)
6. On failure, retry from step 1

## Alternatives Considered

### Alternative 1: Always Full Reload

- **Description**: Fetch all stories on every request, no incremental logic.
- **Pros**:
  - Simple implementation
  - No merge complexity
  - Always consistent
- **Cons**:
  - Wasteful for large story collections
  - Unnecessary API calls
  - Higher latency for heavily-commented tasks
- **Why not chosen**: Inefficient for the common case of few new stories on subsequent reads.

### Alternative 2: Story-Level Caching

- **Description**: Cache each story individually by GID.
- **Pros**:
  - Fine-grained cache control
  - Individual story invalidation
  - Works with story updates (if they existed)
- **Cons**:
  - Many cache keys (one per story)
  - Complex to collect all stories for a task
  - No benefit since stories are immutable
  - Higher Redis memory overhead
- **Why not chosen**: Over-engineered for immutable resources. List caching is simpler and sufficient.

### Alternative 3: Event Sourcing Pattern

- **Description**: Store stories as append-only event log in cache.
- **Pros**:
  - Natural fit for immutable data
  - Clear append semantics
  - History preserved
- **Cons**:
  - Overkill for simple story caching
  - Complex event log management
  - Same result as simpler list append
- **Why not chosen**: Unnecessary complexity. Simple list append achieves same outcome.

### Alternative 4: Webhook-Triggered Story Updates

- **Description**: Use webhooks to push new stories to cache in real-time.
- **Pros**:
  - Real-time updates
  - No polling or `since` queries
  - Cache always current
- **Cons**:
  - Requires webhook infrastructure
  - Webhook delivery not guaranteed
  - SDK becomes dependent on consumer webhook setup
  - Complex webhook event processing
- **Why not chosen**: Webhooks are optional. SDK must work without them.

## Consequences

### Positive

- **Significant API reduction**: Few new stories = one API call instead of many
- **Lower latency**: Less data transferred for incremental updates
- **Efficient cache usage**: Only store/transfer what's needed
- **Consistent ordering**: Stories always in chronological order
- **Simple mental model**: Cache = all stories, fetch = what's new

### Negative

- **Story deletion not detected**: If a story is deleted in Asana, cache retains it
  - Mitigation: Full refresh on TTL expiration; rare in practice
- **Merge complexity**: Must handle concurrent updates atomically
- **Story count changes**: If API returns fewer stories than cached (deletion), triggers full refresh
- **`since` parameter precision**: Must use exactly `last_story_at` timestamp

### Neutral

- **Metadata field added**: `last_story_at` stored in cache entry metadata
- **Version field overloaded**: Uses `last_story_at` as version (appropriate for stories)
- **Full refresh available**: `refresh_stories()` method for explicit full reload

## Compliance

To ensure this decision is followed:

1. **Code review checklist**:
   - Story fetching uses incremental loading by default
   - Cache metadata includes `last_story_at`
   - Atomic updates use Redis WATCH/MULTI

2. **Testing requirements**:
   - Unit tests for merge algorithm
   - Unit tests for concurrent update handling
   - Integration tests with mock API returning `since` results

3. **Edge case handling**:
   - Empty story list (no stories)
   - First fetch (no cache)
   - Story deletion detection (full refresh trigger)
   - Pagination of incremental results

4. **Documentation**:
   - Explain incremental loading in API docs
   - Document `refresh_stories()` for forced full reload
   - Clarify story deletion handling behavior
