"""Workspaces client - returns typed Workspace models by default.

Per TDD-0003: WorkspacesClient provides get and list operations.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.workspace import Workspace
from autom8_asana.transport.sync import sync_wrapper


class WorkspacesClient(BaseClient):
    """Client for Asana Workspace operations.

    Returns typed Workspace models by default. Use raw=True for dict returns.
    """

    @overload
    async def get_async(
        self,
        workspace_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Workspace:
        """Overload: get, returning Workspace model."""
        ...

    @overload
    async def get_async(
        self,
        workspace_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    async def get_async(
        self,
        workspace_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Workspace | dict[str, Any]:
        """Get a workspace by GID.

        Args:
            workspace_gid: Workspace GID
            raw: If True, return raw dict instead of Workspace model
            opt_fields: Optional fields to include

        Returns:
            Workspace model by default, or dict if raw=True
        """
        self._log_operation("get_async", workspace_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/workspaces/{workspace_gid}", params=params)
        if raw:
            return data
        return Workspace.model_validate(data)

    @overload
    def get(
        self,
        workspace_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Workspace:
        """Overload: get (sync), returning Workspace model."""
        ...

    @overload
    def get(
        self,
        workspace_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        workspace_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Workspace | dict[str, Any]:
        """Get a workspace by GID (sync).

        Args:
            workspace_gid: Workspace GID
            raw: If True, return raw dict instead of Workspace model
            opt_fields: Optional fields to include

        Returns:
            Workspace model by default, or dict if raw=True
        """
        return self._get_sync(workspace_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        workspace_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Workspace | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(workspace_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(workspace_gid, raw=False, opt_fields=opt_fields)

    def list_async(
        self,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Workspace]:
        """List workspaces accessible to the authenticated user.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Workspace] - async iterator over Workspace objects

        Example:
            async for workspace in client.workspaces.list_async():
                print(workspace.name)
        """
        self._log_operation("list_async")

        async def fetch_page(offset: str | None) -> tuple[list[Workspace], str | None]:
            """Fetch a single page of Workspace objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                "/workspaces", params=params
            )
            workspaces = [Workspace.model_validate(w) for w in data]
            return workspaces, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))
