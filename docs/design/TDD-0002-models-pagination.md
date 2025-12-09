# TDD: Core Models and Pagination Infrastructure

## Metadata
- **TDD ID**: TDD-0002
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-SDK-035, FR-SDK-036, FR-SDK-037, FR-SDK-038, FR-SDK-039, FR-SDK-040)
- **Related TDDs**: [TDD-0001](TDD-0001-sdk-architecture.md) (overall SDK architecture)
- **Related ADRs**:
  - [ADR-0004](../decisions/ADR-0004-item-class-boundary.md) - Minimal AsanaResource in SDK
  - [ADR-0005](../decisions/ADR-0005-pydantic-model-config.md) - Pydantic v2 with extra="ignore"
  - ADR-0006 (proposed) - NameGid as standalone model

## Overview

This TDD defines the design for the core models layer (NameGid, Item loader protocol) and pagination infrastructure (PageIterator) for the autom8_asana SDK. The design extends the existing `AsanaResource` base class and `Task` model with lightweight reference models, pagination support for list operations, and lazy loading hooks per ADR-0004.

## Requirements Summary

From PRD-0001:
- **FR-SDK-035**: Automatic pagination for list operations (iterator interface for results)
- **FR-SDK-036**: NameGid model for resource references (lightweight with name and gid)
- **FR-SDK-037**: Base model class for all Asana resources (already implemented as `AsanaResource`)
- **FR-SDK-038**: Core Item class with lazy loading hooks (no business logic)
- **FR-SDK-039**: Pydantic v2 for all models (already in place)
- **FR-SDK-040**: Model serialization to/from Asana API format

## System Context

```
                                   autom8_asana SDK
+--------------------------------------------------------------------------------+
|                                                                                |
|  +------------------+     +-----------------------+     +-------------------+  |
|  | models/          |     | clients/              |     | transport/        |  |
|  |                  |     |                       |     |                   |  |
|  | - base.py        |<----| - tasks.py            |<----| - http.py         |  |
|  | - common.py (NEW)|     | - projects.py         |     | - rate_limiter.py |  |
|  | - task.py        |     | - ...                 |     | - retry.py        |  |
|  | - ...            |     |                       |     |                   |  |
|  +------------------+     +-----------------------+     +-------------------+  |
|          ^                          |                                          |
|          |                          |                                          |
|  +------------------+     +-----------------------+                             |
|  | protocols/       |     | AsyncIterator         |                             |
|  |                  |     | (PageIterator)        |                             |
|  | - item_loader.py |     +-----------------------+                             |
|  |   (NEW)          |                                                          |
|  +------------------+                                                          |
|                                                                                |
+--------------------------------------------------------------------------------+
          ^
          |
          | autom8 injects ItemLoader implementation
          |
+--------------------------------------------------------------------------------+
|                               autom8 Monolith                                   |
|                                                                                |
|  +------------------+                                                          |
|  | Item class       | -- extends AsanaResource                                  |
|  | (business logic) | -- implements lazy loading via ItemLoader                 |
|  +------------------+                                                          |
|                                                                                |
+--------------------------------------------------------------------------------+
```

## Design

### Component Architecture

| Component | Responsibility | File Location |
|-----------|---------------|---------------|
| `NameGid` | Lightweight resource reference (gid + name + optional resource_type) | `models/common.py` |
| `PageIterator[T]` | Async iterator for paginated API responses | `models/common.py` |
| `ItemLoader` | Protocol for lazy loading resource data | `protocols/item_loader.py` |
| `AsanaResource` | Base model class (existing) | `models/base.py` |
| `Task` (updated) | Task model using NameGid for nested refs | `models/task.py` |

### Data Model

#### NameGid Model

A lightweight model for Asana resource references. Used throughout the SDK where the API returns compact resource objects (assignee, projects, workspace, parent, etc.).

```python
# /src/autom8_asana/models/common.py

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NameGid(BaseModel):
    """Lightweight model for Asana resource references.

    Asana API frequently returns resource references as compact objects
    containing only gid, name, and resource_type. This model provides
    type-safe access to these references.

    Example API response:
        {
            "assignee": {
                "gid": "12345",
                "name": "Alice Smith",
                "resource_type": "user"
            }
        }

    Usage:
        >>> ref = NameGid(gid="12345", name="Alice")
        >>> ref.gid
        '12345'

    Note: Unlike AsanaResource, NameGid does NOT inherit from it because:
    1. NameGid is a reference, not a full resource
    2. gid is required on NameGid, but name is optional
    3. Keeps NameGid minimal for memory efficiency in large lists
    """

    model_config = ConfigDict(
        extra="ignore",  # Forward compatibility per ADR-0005
        populate_by_name=True,
        str_strip_whitespace=True,
        frozen=True,  # References are immutable
    )

    gid: str
    name: str | None = None
    resource_type: str | None = None

    def __hash__(self) -> int:
        """Enable use in sets and as dict keys."""
        return hash(self.gid)

    def __eq__(self, other: object) -> bool:
        """Equality based on gid only."""
        if isinstance(other, NameGid):
            return self.gid == other.gid
        return NotImplemented
```

**Design Decisions for NameGid:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Standalone vs inherits from AsanaResource | Standalone | NameGid is a reference, not a resource; different semantics (name optional vs required on some resources) |
| Frozen (immutable) | Yes | References shouldn't change; enables hashing for sets/dict keys |
| name field | Optional | API sometimes returns only gid in compact responses |
| resource_type field | Optional | Useful for type discrimination but not always present |
| Equality semantics | Based on gid | Two refs to same resource are equal regardless of name |

#### PageIterator

Generic async iterator for automatic pagination of Asana list operations.

```python
# /src/autom8_asana/models/common.py (continued)

from typing import TypeVar, Generic, AsyncIterator, Callable, Awaitable, Any

T = TypeVar("T")


class PageIterator(Generic[T]):
    """Async iterator for paginated Asana API responses.

    Automatically handles pagination tokens (offset-based pagination used by
    Asana API). Fetches pages lazily as iteration progresses.

    Usage (async for):
        async for task in client.tasks.list(project="123"):
            print(task.name)

    Usage (collect all):
        tasks = [t async for t in client.tasks.list(project="123")]

    Usage (first N items):
        async for i, task in enumerate(client.tasks.list(project="123")):
            if i >= 10:
                break
            print(task.name)

    Memory efficiency:
        - Only one page is buffered at a time
        - Items are yielded immediately as available
        - Safe for iterating very large result sets

    Asana pagination:
        Asana uses offset-based pagination with `next_page.offset` in responses.
        The iterator handles this automatically, passing offset to subsequent
        requests until no more pages exist.
    """

    def __init__(
        self,
        fetch_page: Callable[[str | None], Awaitable[tuple[list[T], str | None]]],
        page_size: int = 100,
    ) -> None:
        """Initialize PageIterator.

        Args:
            fetch_page: Async function that fetches a page of results.
                Takes an optional offset string, returns (items, next_offset).
                next_offset is None when no more pages exist.
            page_size: Number of items per page (for documentation; actual
                page size is controlled by fetch_page implementation).
        """
        self._fetch_page = fetch_page
        self._page_size = page_size
        self._buffer: list[T] = []
        self._next_offset: str | None = None
        self._exhausted = False
        self._started = False

    def __aiter__(self) -> "PageIterator[T]":
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> T:
        """Get next item, fetching new page if needed."""
        # Refill buffer if empty and more pages available
        if not self._buffer and not self._exhausted:
            await self._fetch_next_page()

        # Return next item or stop iteration
        if self._buffer:
            return self._buffer.pop(0)
        raise StopAsyncIteration

    async def _fetch_next_page(self) -> None:
        """Fetch the next page of results."""
        if self._exhausted:
            return

        # Fetch page with current offset (None for first page)
        offset = self._next_offset if self._started else None
        items, next_offset = await self._fetch_page(offset)

        self._started = True
        self._buffer.extend(items)
        self._next_offset = next_offset

        # Mark exhausted if no more pages
        if next_offset is None:
            self._exhausted = True

    async def collect(self) -> list[T]:
        """Collect all items into a list.

        Convenience method for when you need all results.
        For large result sets, prefer iterating directly.

        Returns:
            List of all items across all pages.
        """
        return [item async for item in self]

    async def first(self) -> T | None:
        """Get the first item, or None if empty.

        Returns:
            First item or None.
        """
        try:
            return await self.__anext__()
        except StopAsyncIteration:
            return None

    async def take(self, n: int) -> list[T]:
        """Take up to n items.

        Args:
            n: Maximum number of items to take.

        Returns:
            List of up to n items.
        """
        result: list[T] = []
        count = 0
        async for item in self:
            if count >= n:
                break
            result.append(item)
            count += 1
        return result
```

**Design Decisions for PageIterator:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Generic `T` vs resource-specific | Generic | Reusable for all resource types (Task, Project, User, etc.) |
| Buffer strategy | Single page | Memory efficient; yields immediately without loading all |
| Callback signature | `(offset) -> (items, next_offset)` | Clean separation; clients build their own fetch logic |
| Helper methods | `collect()`, `first()`, `take()` | Common patterns; saves boilerplate for consumers |
| Offset type | `str | None` | Asana uses string offsets; None signals end/start |

#### ItemLoader Protocol

Protocol for lazy loading per ADR-0004. The SDK provides only the protocol; autom8 implements it.

```python
# /src/autom8_asana/protocols/item_loader.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class ItemLoader(Protocol):
    """Protocol for lazy loading additional resource data.

    The SDK provides this protocol as a hook for consumers who want
    lazy loading behavior. The SDK does NOT provide an implementation.

    Per ADR-0004:
    - SDK provides minimal AsanaResource base class
    - autom8 monolith implements lazy loading via this protocol
    - New microservices can implement their own or skip lazy loading

    Example implementation (in autom8, NOT in SDK):
        class Autom8ItemLoader:
            def __init__(self, cache: TaskCache, client: AsanaClient):
                self._cache = cache
                self._client = client

            async def load_async(
                self,
                resource: AsanaResource,
                fields: list[str] | None = None,
            ) -> dict[str, Any]:
                # Check cache first
                cached = self._cache.get(resource.gid)
                if cached:
                    return cached

                # Fetch from API
                data = await self._client.tasks.get_async(
                    resource.gid,
                    opt_fields=fields,
                    raw=True,
                )
                self._cache.set(resource.gid, data)
                return data

    Usage in autom8's Item class:
        class Item(AsanaResource):
            _loader: ItemLoader | None = None

            def __getattr__(self, name: str) -> Any:
                if self._loader and name in self._lazy_fields:
                    data = asyncio.run(self._loader.load_async(self, [name]))
                    return data.get(name)
                raise AttributeError(name)
    """

    async def load_async(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Load additional data for a resource.

        Args:
            resource: The resource to load data for (has gid, resource_type)
            fields: Optional list of specific fields to load. If None,
                load all available fields.

        Returns:
            Dict containing the loaded field values.

        Raises:
            NotFoundError: If resource doesn't exist
            AsanaError: On API/cache errors
        """
        ...

    def load(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sync version of load_async.

        Args:
            resource: The resource to load data for
            fields: Optional list of specific fields to load

        Returns:
            Dict containing the loaded field values.
        """
        ...
```

**Design Decisions for ItemLoader:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Protocol vs ABC | Protocol | Structural typing; no inheritance required |
| SDK provides implementation | No | Per ADR-0004; lazy loading is application-specific |
| Async + sync methods | Both | Matches SDK async-first with sync wrapper pattern |
| Returns dict | Yes | Flexible; consumer decides how to merge into resource |
| Optional fields parameter | Yes | Efficiency; load only what's needed |

### Updated Task Model

Update the Task model to use NameGid for nested references instead of `dict[str, Any]`:

```python
# /src/autom8_asana/models/task.py (updated)

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Task(AsanaResource):
    """Asana Task resource model.

    Uses NameGid for typed resource references (assignee, projects, etc.).
    Custom fields and complex nested structures remain as dicts.

    Example:
        >>> task = Task.model_validate(api_response)
        >>> if task.assignee:
        ...     print(f"Assigned to {task.assignee.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="task")

    # Basic task fields
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status fields
    completed: bool | None = None
    completed_at: str | None = None
    completed_by: NameGid | None = None  # Changed from dict

    # Due dates
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    due_at: str | None = Field(default=None, description="Due datetime (ISO 8601)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    start_at: str | None = Field(default=None, description="Start datetime (ISO 8601)")

    # Relationships - typed with NameGid
    assignee: NameGid | None = None  # Changed from dict
    assignee_section: NameGid | None = None  # Changed from dict
    assignee_status: str | None = Field(
        default=None,
        description="Scheduling status (inbox, today, upcoming, later)",
    )
    projects: list[NameGid] | None = None  # Changed from list[dict]
    parent: NameGid | None = None  # Changed from dict
    workspace: NameGid | None = None  # Changed from dict
    memberships: list[dict[str, Any]] | None = None  # Keep as dict (complex structure)
    followers: list[NameGid] | None = None  # Changed from list[dict]
    tags: list[NameGid] | None = None  # Changed from list[dict]

    # Hierarchy and dependencies
    num_subtasks: int | None = None
    num_hearts: int | None = Field(default=None, description="Deprecated: use num_likes")
    num_likes: int | None = None
    is_rendered_as_separator: bool | None = None

    # Custom fields - remain as dict (complex structure)
    custom_fields: list[dict[str, Any]] | None = None

    # Metadata
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
    modified_at: str | None = Field(default=None, description="Modified datetime (ISO 8601)")
    created_by: NameGid | None = None  # Changed from dict

    # Approval fields
    approval_status: str | None = Field(
        default=None,
        description="Approval status (pending, approved, rejected, changes_requested)",
    )

    # External data - remains as dict (arbitrary structure)
    external: dict[str, Any] | None = Field(
        default=None,
        description="External data (id and data fields for integrations)",
    )

    # Visibility and access
    resource_subtype: str | None = Field(
        default=None,
        description="Subtype (default_task, milestone, section, approval)",
    )

    # Permalink
    permalink_url: str | None = None

    # Liked status
    liked: bool | None = None
    hearted: bool | None = Field(default=None, description="Deprecated: use liked")
    hearts: list[dict[str, Any]] | None = Field(
        default=None,
        description="Deprecated: use likes",
    )
    likes: list[dict[str, Any]] | None = None  # Keep as dict (user refs with extra data)

    # Actual time tracking
    actual_time_minutes: float | None = None
```

**Migration Strategy for Task Model:**

The change from `dict[str, Any]` to `NameGid` is backward compatible:

1. **Pydantic handles coercion**: `NameGid.model_validate({"gid": "123", "name": "Test"})` works
2. **Extra fields ignored**: Per ADR-0005, unknown fields in API response are ignored
3. **Gradual adoption**: Existing code accessing `.assignee["gid"]` needs update to `.assignee.gid`
4. **Test coverage**: All existing tests updated to verify new behavior

**Fields staying as dict:**
| Field | Reason |
|-------|--------|
| `memberships` | Complex nested structure (project + section refs) |
| `custom_fields` | Arbitrary structure (enum, number, text, multi-enum values) |
| `external` | Arbitrary user-defined structure |
| `hearts`, `likes` | User refs with additional metadata |

### API Contracts

#### Updated TasksClient.list Method

```python
# In /src/autom8_asana/clients/tasks.py

def list(
    self,
    *,
    project: str | None = None,
    section: str | None = None,
    assignee: str | None = None,
    workspace: str | None = None,
    completed_since: str | None = None,
    modified_since: str | None = None,
    opt_fields: list[str] | None = None,
) -> PageIterator[Task]:
    """List tasks with automatic pagination.

    Returns a PageIterator that lazily fetches pages as you iterate.

    Args:
        project: Filter by project GID
        section: Filter by section GID
        assignee: Filter by assignee GID (use "me" for current user)
        workspace: Filter by workspace GID (required if no project/section)
        completed_since: ISO 8601 datetime; include completed tasks modified since
        modified_since: ISO 8601 datetime; only tasks modified since
        opt_fields: Fields to include in response

    Returns:
        PageIterator[Task] - async iterator over Task objects

    Example:
        # Iterate all tasks
        async for task in client.tasks.list(project="123"):
            print(task.name)

        # Get first 10
        tasks = await client.tasks.list(project="123").take(10)

        # Collect all
        all_tasks = await client.tasks.list(project="123").collect()
    """
    async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
        params = self._build_opt_fields(opt_fields)
        if project:
            params["project"] = project
        if section:
            params["section"] = section
        if assignee:
            params["assignee"] = assignee
        if workspace:
            params["workspace"] = workspace
        if completed_since:
            params["completed_since"] = completed_since
        if modified_since:
            params["modified_since"] = modified_since
        params["limit"] = 100
        if offset:
            params["offset"] = offset

        # This would need modification to return next_page info
        # For now, showing the expected interface
        result = await self._http.get("/tasks", params=params)
        # Asana returns: {"data": [...], "next_page": {"offset": "xyz"}}
        # HTTP client currently unwraps data, need to preserve pagination info

        tasks = [Task.model_validate(t) for t in result]
        next_offset = None  # Would extract from response
        return tasks, next_offset

    return PageIterator(fetch_page)
```

**Note**: HTTP client modification needed to support pagination info. See Implementation Plan.

### Data Flow

#### Pagination Flow

```
User Code                TasksClient             PageIterator            AsyncHTTPClient
    |                         |                       |                        |
    | tasks.list(project=X)   |                       |                        |
    |------------------------>|                       |                        |
    |                         |                       |                        |
    |                         | return PageIterator   |                        |
    |                         |<----------------------|                        |
    |                         |                       |                        |
    | async for task in ...:  |                       |                        |
    |------------------------>|                       |                        |
    |                         | __anext__()           |                        |
    |                         |---------------------->|                        |
    |                         |                       |                        |
    |                         |                       | (buffer empty)         |
    |                         |                       | _fetch_next_page()     |
    |                         |                       |                        |
    |                         |                       | fetch_page(None)       |
    |                         |<----------------------|                        |
    |                         |                       |                        |
    |                         | GET /tasks?project=X&limit=100                 |
    |                         |----------------------------------------------->|
    |                         |                       |                        |
    |                         | {"data": [...], "next_page": {"offset": "Y"}}  |
    |                         |<-----------------------------------------------|
    |                         |                       |                        |
    |                         | (tasks, "Y")          |                        |
    |                         |---------------------->|                        |
    |                         |                       |                        |
    |                         |                       | buffer.extend(tasks)   |
    |                         |                       | next_offset = "Y"      |
    |                         |                       |                        |
    |                         |                       | buffer.pop(0)          |
    |                         |                       |----------------------->|
    |                         |                       |                        |
    | Task                    |                       |                        |
    |<------------------------|                       |                        |
    |                         |                       |                        |
    | (iteration continues...) |                      |                        |
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| NameGid standalone vs inherit | Standalone | Different semantics; lighter weight; enables frozen/hashable | ADR-0006 (proposed) |
| PageIterator generic | Yes | Reusable for all resource types | N/A (standard pattern) |
| ItemLoader in SDK | Protocol only | Per ADR-0004; lazy loading is app-specific | ADR-0004 |
| Task fields to NameGid | Gradual | Start with simple refs; complex structures stay dict | N/A |
| PageIterator helper methods | Yes | Convenience; common patterns | N/A |

## Complexity Assessment

**Level**: MODULE

**Justification**:
- Clear API surface (NameGid, PageIterator, ItemLoader protocol)
- Minimal internal structure (no layers within these components)
- Extends existing foundation (AsanaResource, Task)
- No new configuration or operational concerns
- Pure data structures and iterators

This is lower complexity than the overall SDK (SERVICE level) because these components are self-contained utilities without external dependencies or operational concerns.

## Implementation Plan

### Phase 1: NameGid Model (1 hour)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Create `models/common.py` with NameGid | None | 30min |
| Unit tests for NameGid | NameGid | 30min |

**Exit Criteria**: NameGid validates, serializes, and is hashable.

### Phase 2: PageIterator (2 hours)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| PageIterator class | None | 1h |
| Unit tests (mocked fetch) | PageIterator | 30min |
| Helper methods (collect, first, take) | PageIterator | 30min |

**Exit Criteria**: PageIterator passes all unit tests with mocked fetcher.

### Phase 3: HTTP Client Pagination Support (1 hour)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Add `request_with_pagination` method | AsyncHTTPClient | 30min |
| Update tests | Method | 30min |

**Exit Criteria**: HTTP client can return raw response with `next_page` info.

### Phase 4: Update Task Model (1 hour)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Update Task to use NameGid | NameGid | 30min |
| Update all Task tests | Task changes | 30min |

**Exit Criteria**: All 278 existing tests pass; Task uses NameGid.

### Phase 5: TasksClient.list with PageIterator (1 hour)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `TasksClient.list` | PageIterator, HTTP pagination | 30min |
| Integration tests | Full stack | 30min |

**Exit Criteria**: `client.tasks.list()` returns PageIterator; iteration works.

### Phase 6: ItemLoader Protocol (30 min)
| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Create `protocols/item_loader.py` | None | 15min |
| Documentation | Protocol | 15min |

**Exit Criteria**: Protocol defined; example in docstring.

**Total Estimate**: 6.5 hours

### Migration Notes

**For autom8 monolith migration:**

1. **Task field access changes**:
   ```python
   # Before
   task.assignee["gid"]
   task.assignee["name"]

   # After
   task.assignee.gid
   task.assignee.name
   ```

2. **Null checks unchanged**: `if task.assignee:` still works

3. **Serialization**:
   ```python
   # Before
   task.model_dump()["assignee"]  # dict

   # After
   task.model_dump()["assignee"]  # dict (Pydantic serializes NameGid to dict)
   ```

4. **Type hints**: Update type annotations from `dict[str, Any] | None` to `NameGid | None`

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking change for dict access | Medium | Medium | Phase migration; both patterns work during transition |
| PageIterator memory for huge results | Low | Low | Single-page buffer; can add limit parameter |
| HTTP client changes break existing | Medium | Low | Add new method; don't change existing |
| NameGid missing fields from API | Low | Medium | extra="ignore" handles gracefully |

## Observability

### Logging
- **DEBUG**: PageIterator page fetches, buffer refills
- **INFO**: Total items iterated (on iterator exhaustion)
- **WARNING**: Empty page from API (unexpected)

### Metrics (future)
- `asana_pagination_pages_fetched` (counter)
- `asana_pagination_items_total` (counter)
- `asana_pagination_buffer_size` (gauge)

## Testing Strategy

### Unit Testing
- **NameGid**: validation, serialization, hashing, equality
- **PageIterator**: empty results, single page, multi-page, helpers
- **Task with NameGid**: field access, serialization roundtrip

### Integration Testing
- **TasksClient.list**: real pagination with mock server
- **Large result sets**: memory efficiency

### Contract Testing
- **API response fixtures**: verify NameGid parses real Asana responses

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All design questions resolved |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Architect | Initial design |
