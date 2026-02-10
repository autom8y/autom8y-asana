"""Tags client - returns typed Tag models by default.

Per TDD-0004: TagsClient provides tag CRUD and task tagging for Tier 2.
Per TDD-DESIGN-PATTERNS-D: Uses @async_method for async/sync method generation.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.tag import Tag
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method


class TagsClient(BaseClient):
    """Client for Asana Tag operations.

    Returns typed Tag models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    @overload  # type: ignore[no-overload-impl]
    async def get_async(
        self,
        tag_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Tag:
        """Overload: get, returning Tag model."""
        ...

    @overload
    async def get_async(
        self,
        tag_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    @overload
    def get(
        self,
        tag_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Tag:
        """Overload: get (sync), returning Tag model."""
        ...

    @overload
    def get(
        self,
        tag_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def get(
        self,
        tag_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Tag | dict[str, Any]:
        """Get a tag by GID.

        Args:
            tag_gid: Tag GID
            raw: If True, return raw dict instead of Tag model
            opt_fields: Optional fields to include

        Returns:
            Tag model by default, or dict if raw=True
        """
        self._log_operation("get_async", tag_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/tags/{tag_gid}", params=params)
        if raw:
            return data
        return Tag.model_validate(data)

    @overload  # type: ignore[no-overload-impl]
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[False] = ...,
        color: str | None = ...,
        notes: str | None = ...,
    ) -> Tag:
        """Overload: create, returning Tag model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[True],
        color: str | None = ...,
        notes: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: create, returning raw dict."""
        ...

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[False] = ...,
        color: str | None = ...,
        notes: str | None = ...,
    ) -> Tag:
        """Overload: create (sync), returning Tag model."""
        ...

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[True],
        color: str | None = ...,
        notes: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: create (sync), returning raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        color: str | None = None,
        notes: str | None = None,
    ) -> Tag | dict[str, Any]:
        """Create a tag.

        Args:
            workspace: Workspace GID
            name: Tag name
            raw: If True, return raw dict
            color: Optional tag color
            notes: Optional tag description

        Returns:
            Tag model by default, or dict if raw=True
        """
        self._log_operation("create_async")

        data: dict[str, Any] = {"workspace": workspace, "name": name}

        if color is not None:
            data["color"] = color
        if notes is not None:
            data["notes"] = notes

        result = await self._http.post("/tags", json={"data": data})
        if raw:
            return result
        return Tag.model_validate(result)

    @overload  # type: ignore[no-overload-impl]
    async def update_async(
        self,
        tag_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Tag:
        """Overload: update, returning Tag model."""
        ...

    @overload
    async def update_async(
        self,
        tag_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

    @overload
    def update(
        self,
        tag_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Tag:
        """Overload: update (sync), returning Tag model."""
        ...

    @overload
    def update(
        self,
        tag_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def update(
        self,
        tag_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Tag | dict[str, Any]:
        """Update a tag.

        Args:
            tag_gid: Tag GID
            raw: If True, return raw dict instead of Tag model
            **kwargs: Fields to update

        Returns:
            Tag model by default, or dict if raw=True
        """
        self._log_operation("update_async", tag_gid)
        result = await self._http.put(f"/tags/{tag_gid}", json={"data": kwargs})
        if raw:
            return result
        return Tag.model_validate(result)

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def delete(self, tag_gid: str) -> None:
        """Delete a tag.

        Args:
            tag_gid: Tag GID
        """
        self._log_operation("delete_async", tag_gid)
        await self._http.delete(f"/tags/{tag_gid}")

    # --- List Operations ---

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Tag]:
        """List tags in a workspace.

        Args:
            workspace_gid: Workspace GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Tag]
        """
        self._log_operation("list_for_workspace_async", workspace_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Tag], str | None]:
            """Fetch a single page of Tag objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/workspaces/{workspace_gid}/tags", params=params
            )
            tags = [Tag.model_validate(t) for t in data]
            return tags, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    def list_for_task_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Tag]:
        """List tags on a task.

        Args:
            task_gid: Task GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Tag]
        """
        self._log_operation("list_for_task_async", task_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Tag], str | None]:
            """Fetch a single page of Tag objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/tags", params=params
            )
            tags = [Tag.model_validate(t) for t in data]
            return tags, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Task Tagging Operations ---

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def add_to_task(
        self,
        task_gid: str,
        *,
        tag: str,
    ) -> None:
        """Add a tag to a task.

        Args:
            task_gid: Task GID
            tag: Tag GID to add
        """
        self._log_operation("add_to_task_async", task_gid)
        await self._http.post(
            f"/tasks/{task_gid}/addTag",
            json={"data": {"tag": tag}},
        )

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def remove_from_task(
        self,
        task_gid: str,
        *,
        tag: str,
    ) -> None:
        """Remove a tag from a task.

        Args:
            task_gid: Task GID
            tag: Tag GID to remove
        """
        self._log_operation("remove_from_task_async", task_gid)
        await self._http.post(
            f"/tasks/{task_gid}/removeTag",
            json={"data": {"tag": tag}},
        )
