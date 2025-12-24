"""Stories client - returns typed Story models by default.

Per TDD-0004: StoriesClient provides story/comment operations for Tier 2.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.story import Story
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class StoriesClient(BaseClient):
    """Client for Asana Story operations.

    Stories include comments and system-generated activity.
    Returns typed Story models by default. Use raw=True for dict returns.
    """

    # --- Core Operations ---

    @overload
    async def get_async(
        self,
        story_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Story:
        """Overload: get, returning Story model."""
        ...

    @overload
    async def get_async(
        self,
        story_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    async def get_async(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Story | dict[str, Any]:
        """Get a story by GID.

        Args:
            story_gid: Story GID
            raw: If True, return raw dict instead of Story model
            opt_fields: Optional fields to include

        Returns:
            Story model by default, or dict if raw=True
        """
        self._log_operation("get_async", story_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/stories/{story_gid}", params=params)
        if raw:
            return data
        return Story.model_validate(data)

    @overload
    def get(
        self,
        story_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Story:
        """Overload: get (sync), returning Story model."""
        ...

    @overload
    def get(
        self,
        story_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Story | dict[str, Any]:
        """Get a story by GID (sync).

        Args:
            story_gid: Story GID
            raw: If True, return raw dict instead of Story model
            opt_fields: Optional fields to include

        Returns:
            Story model by default, or dict if raw=True
        """
        return self._get_sync(story_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Story | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(story_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(story_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def update_async(
        self,
        story_gid: str,
        *,
        raw: Literal[False] = ...,
        text: str | None = ...,
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> Story:
        """Overload: update, returning Story model."""
        ...

    @overload
    async def update_async(
        self,
        story_gid: str,
        *,
        raw: Literal[True],
        text: str | None = ...,
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

    async def update_async(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        text: str | None = None,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Update a story (comment only).

        Only comments (resource_subtype=comment_added) can be updated.

        Args:
            story_gid: Story GID
            raw: If True, return raw dict
            text: New text content
            html_text: New HTML content
            is_pinned: Whether to pin the comment

        Returns:
            Story model by default, or dict if raw=True
        """
        self._log_operation("update_async", story_gid)

        data: dict[str, Any] = {}
        if text is not None:
            data["text"] = text
        if html_text is not None:
            data["html_text"] = html_text
        if is_pinned is not None:
            data["is_pinned"] = is_pinned

        result = await self._http.put(f"/stories/{story_gid}", json={"data": data})
        if raw:
            return result
        return Story.model_validate(result)

    @overload
    def update(
        self,
        story_gid: str,
        *,
        raw: Literal[False] = ...,
        text: str | None = ...,
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> Story:
        """Overload: update (sync), returning Story model."""
        ...

    @overload
    def update(
        self,
        story_gid: str,
        *,
        raw: Literal[True],
        text: str | None = ...,
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    def update(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        text: str | None = None,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Update a story (sync).

        Args:
            story_gid: Story GID
            raw: If True, return raw dict
            text: New text content
            html_text: New HTML content
            is_pinned: Whether to pin the comment

        Returns:
            Story model by default, or dict if raw=True
        """
        return self._update_sync(
            story_gid, raw=raw, text=text, html_text=html_text, is_pinned=is_pinned
        )

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        text: str | None = None,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_async(
                story_gid, raw=True, text=text, html_text=html_text, is_pinned=is_pinned
            )
        return await self.update_async(
            story_gid, raw=False, text=text, html_text=html_text, is_pinned=is_pinned
        )

    async def delete_async(self, story_gid: str) -> None:
        """Delete a story (comment only).

        Only comments can be deleted. System stories cannot be deleted.

        Args:
            story_gid: Story GID
        """
        self._log_operation("delete_async", story_gid)
        await self._http.delete(f"/stories/{story_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, story_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(story_gid)

    def delete(self, story_gid: str) -> None:
        """Delete a story (sync).

        Only comments can be deleted. System stories cannot be deleted.

        Args:
            story_gid: Story GID
        """
        self._delete_sync(story_gid)

    # --- List Operations ---

    def list_for_task_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Story]:
        """List stories on a task.

        Returns both comments and system activity.

        Args:
            task_gid: Task GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Story]
        """
        self._log_operation("list_for_task_async", task_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Story], str | None]:
            """Fetch a single page of Story objects."""
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

    # --- Comment Creation ---

    @overload
    async def create_comment_async(
        self,
        *,
        task: str,
        text: str,
        raw: Literal[False] = ...,
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> Story:
        """Overload: create comment, returning Story model."""
        ...

    @overload
    async def create_comment_async(
        self,
        *,
        task: str,
        text: str,
        raw: Literal[True],
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> dict[str, Any]:
        """Overload: create comment, returning raw dict."""
        ...

    async def create_comment_async(
        self,
        *,
        task: str,
        text: str,
        raw: bool = False,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Create a comment on a task.

        Args:
            task: Task GID
            text: Comment text
            raw: If True, return raw dict
            html_text: Optional HTML formatted text
            is_pinned: Whether to pin the comment

        Returns:
            Story model by default, or dict if raw=True

        Example:
            >>> comment = await client.stories.create_comment_async(
            ...     task="123",
            ...     text="Great progress on this task!",
            ... )
        """
        self._log_operation("create_comment_async", task)

        data: dict[str, Any] = {"text": text}
        if html_text is not None:
            data["html_text"] = html_text
        if is_pinned is not None:
            data["is_pinned"] = is_pinned

        result = await self._http.post(f"/tasks/{task}/stories", json={"data": data})
        if raw:
            return result
        return Story.model_validate(result)

    @overload
    def create_comment(
        self,
        *,
        task: str,
        text: str,
        raw: Literal[False] = ...,
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> Story:
        """Overload: create comment (sync), returning Story model."""
        ...

    @overload
    def create_comment(
        self,
        *,
        task: str,
        text: str,
        raw: Literal[True],
        html_text: str | None = ...,
        is_pinned: bool | None = ...,
    ) -> dict[str, Any]:
        """Overload: create comment (sync), returning raw dict."""
        ...

    def create_comment(
        self,
        *,
        task: str,
        text: str,
        raw: bool = False,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Create a comment on a task (sync).

        Args:
            task: Task GID
            text: Comment text
            raw: If True, return raw dict
            html_text: Optional HTML formatted text
            is_pinned: Whether to pin the comment

        Returns:
            Story model by default, or dict if raw=True
        """
        return self._create_comment_sync(
            task=task, text=text, raw=raw, html_text=html_text, is_pinned=is_pinned
        )

    @sync_wrapper("create_comment_async")
    async def _create_comment_sync(
        self,
        *,
        task: str,
        text: str,
        raw: bool = False,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_comment_async(
                task=task, text=text, raw=True, html_text=html_text, is_pinned=is_pinned
            )
        return await self.create_comment_async(
            task=task, text=text, raw=False, html_text=html_text, is_pinned=is_pinned
        )

    # --- Cached List Operations (per TDD-CACHE-PERF-STORIES) ---

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
        self._log_operation("list_for_task_cached_async", task_gid)
        start_time = time.perf_counter()

        # NFR-OBS-002: Log fetch attempt entry point
        logger.debug(
            "Starting stories fetch for task %s",
            task_gid,
            extra={
                "task_gid": task_gid,
                "cache_available": self._cache is not None,
            },
        )

        # FR-DEGRADE-001: Fallback without cache
        if self._cache is None:
            stories = await self._fetch_all_stories_uncached(task_gid, opt_fields)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                "Stories fetch completed (no cache) for task %s: %d stories in %.2fms",
                task_gid,
                len(stories),
                duration_ms,
                extra={
                    "task_gid": task_gid,
                    "story_count": len(stories),
                    "duration_ms": duration_ms,
                    "cache_available": False,
                    "was_incremental": False,
                },
            )
            return stories

        try:
            from autom8_asana.cache.stories import load_stories_incremental

            # FR-FETCH-001: Create loader-compatible fetcher
            fetcher = self._make_stories_fetcher(opt_fields)

            # FR-CACHE-001: Use incremental loader
            (
                stories_dicts,
                cache_entry,
                was_incremental,
            ) = await load_stories_incremental(
                task_gid=task_gid,
                cache=self._cache,
                fetcher=fetcher,
                current_modified_at=task_modified_at,  # FR-CACHE-005
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            # NFR-OBS-001, NFR-OBS-002: Record metrics for fetch type
            self._record_stories_fetch_metrics(
                task_gid=task_gid,
                was_incremental=was_incremental,
                story_count=len(stories_dicts),
                duration_ms=duration_ms,
            )

            # NFR-OBS-001, NFR-OBS-002, NFR-OBS-003: Enhanced structured logging
            logger.debug(
                "Stories loaded for task %s: %d stories, incremental=%s in %.2fms",
                task_gid,
                len(stories_dicts),
                was_incremental,
                duration_ms,
                extra={
                    "task_gid": task_gid,
                    "story_count": len(stories_dicts),
                    "was_incremental": was_incremental,
                    "cache_hit": was_incremental,
                    "duration_ms": duration_ms,
                },
            )

            # Convert dicts to Story models
            return [Story.model_validate(s) for s in stories_dicts]

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            # FR-DEGRADE-002, FR-DEGRADE-003: Enhanced fallback logging
            logger.warning(
                "Cache operation failed for stories (task=%s): %s, "
                "falling back to full fetch after %.2fms",
                task_gid,
                exc,
                duration_ms,
                extra={
                    "task_gid": task_gid,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "duration_ms": duration_ms,
                },
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            return await self._fetch_all_stories_uncached(task_gid, opt_fields)

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

    def _record_stories_fetch_metrics(
        self,
        task_gid: str,
        was_incremental: bool,
        story_count: int,
        duration_ms: float,
    ) -> None:
        """Record metrics for stories fetch operation.

        Per NFR-OBS-001, NFR-OBS-002: Track incremental vs full fetch operations
        using the CacheMetrics infrastructure.

        Args:
            task_gid: Task GID for correlation.
            was_incremental: True if fetch used incremental cache path.
            story_count: Total number of stories after fetch/merge.
            duration_ms: Operation duration in milliseconds.
        """
        if self._cache is None:
            return

        try:
            metrics = self._cache.get_metrics()
            if was_incremental:
                metrics.record_incremental_fetch(
                    latency_ms=duration_ms,
                    key=task_gid,
                    entry_type="stories",
                    item_count=story_count,
                )
            else:
                metrics.record_full_fetch(
                    latency_ms=duration_ms,
                    key=task_gid,
                    entry_type="stories",
                    item_count=story_count,
                )
        except Exception as exc:
            # Metrics recording should never fail the operation
            logger.debug(
                "Failed to record stories cache metrics: %s",
                exc,
                extra={"task_gid": task_gid, "error": str(exc)},
            )
