"""Common models for Asana API resources.

Per TDD-0002 and ADR-0006: NameGid as standalone frozen model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


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


T = TypeVar("T")


class PageIterator(Generic[T]):
    """Async iterator for paginated Asana API responses.

    Automatically handles pagination tokens (offset-based pagination used by
    Asana API). Fetches pages lazily as iteration progresses.

    Usage (async for):
        async for task in client.tasks.list_async(project="123"):
            print(task.name)

    Usage (collect all):
        tasks = [t async for t in client.tasks.list_async(project="123")]

    Usage (first N items):
        async for i, task in enumerate(client.tasks.list_async(project="123")):
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

    def __aiter__(self) -> PageIterator[T]:
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
            List of up to n items. Empty list if n <= 0.
        """
        if n <= 0:
            return []
        result: list[T] = []
        async for item in self:
            result.append(item)
            if len(result) >= n:
                break
        return result
