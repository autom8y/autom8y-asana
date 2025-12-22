"""Stories client - returns typed Story models by default.

Per TDD-0004: StoriesClient provides story/comment operations for Tier 2.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.story import Story
from autom8_asana.transport.sync import sync_wrapper


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
