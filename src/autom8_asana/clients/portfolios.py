"""Portfolios client - returns typed Portfolio models by default.

Per TDD-0004: PortfoliosClient provides portfolio CRUD, project management for Tier 2.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.portfolio import Portfolio
from autom8_asana.models.project import Project
from autom8_asana.transport.sync import sync_wrapper


class PortfoliosClient(BaseClient):
    """Client for Asana Portfolio operations.

    Portfolios contain projects for high-level tracking.
    Returns typed Portfolio models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    @overload
    async def get_async(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Portfolio:
        """Overload: get, returning Portfolio model."""
        ...

    @overload
    async def get_async(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    async def get_async(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Portfolio | dict[str, Any]:
        """Get a portfolio by GID.

        Args:
            portfolio_gid: Portfolio GID
            raw: If True, return raw dict instead of Portfolio model
            opt_fields: Optional fields to include

        Returns:
            Portfolio model by default, or dict if raw=True
        """
        self._log_operation("get_async", portfolio_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/portfolios/{portfolio_gid}", params=params)
        if raw:
            return data
        return Portfolio.model_validate(data)

    @overload
    def get(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Portfolio:
        """Overload: get (sync), returning Portfolio model."""
        ...

    @overload
    def get(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Portfolio | dict[str, Any]:
        """Get a portfolio by GID (sync).

        Args:
            portfolio_gid: Portfolio GID
            raw: If True, return raw dict instead of Portfolio model
            opt_fields: Optional fields to include

        Returns:
            Portfolio model by default, or dict if raw=True
        """
        return self._get_sync(portfolio_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Portfolio | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(portfolio_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(portfolio_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[False] = ...,
        color: str | None = ...,
        public: bool | None = ...,
        **kwargs: Any,
    ) -> Portfolio:
        """Overload: create, returning Portfolio model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[True],
        color: str | None = ...,
        public: bool | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: create, returning raw dict."""
        ...

    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        color: str | None = None,
        public: bool | None = None,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Create a portfolio.

        Args:
            workspace: Workspace GID
            name: Portfolio name
            raw: If True, return raw dict
            color: Optional color
            public: Whether portfolio is public
            **kwargs: Additional portfolio fields

        Returns:
            Portfolio model by default, or dict if raw=True
        """
        self._log_operation("create_async")

        data: dict[str, Any] = {"workspace": workspace, "name": name}

        if color is not None:
            data["color"] = color
        if public is not None:
            data["public"] = public

        data.update(kwargs)

        result = await self._http.post("/portfolios", json={"data": data})
        if raw:
            return result
        return Portfolio.model_validate(result)

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[False] = ...,
        color: str | None = ...,
        public: bool | None = ...,
        **kwargs: Any,
    ) -> Portfolio:
        """Overload: create (sync), returning Portfolio model."""
        ...

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[True],
        color: str | None = ...,
        public: bool | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: create (sync), returning raw dict."""
        ...

    def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        color: str | None = None,
        public: bool | None = None,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Create a portfolio (sync).

        Args:
            workspace: Workspace GID
            name: Portfolio name
            raw: If True, return raw dict
            color: Optional color
            public: Whether portfolio is public
            **kwargs: Additional portfolio fields

        Returns:
            Portfolio model by default, or dict if raw=True
        """
        return self._create_sync(
            workspace=workspace,
            name=name,
            raw=raw,
            color=color,
            public=public,
            **kwargs,
        )

    @sync_wrapper("create_async")
    async def _create_sync(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        color: str | None = None,
        public: bool | None = None,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_async(
                workspace=workspace,
                name=name,
                raw=True,
                color=color,
                public=public,
                **kwargs,
            )
        return await self.create_async(
            workspace=workspace,
            name=name,
            raw=False,
            color=color,
            public=public,
            **kwargs,
        )

    @overload
    async def update_async(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Portfolio:
        """Overload: update, returning Portfolio model."""
        ...

    @overload
    async def update_async(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

    async def update_async(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Update a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            raw: If True, return raw dict instead of Portfolio model
            **kwargs: Fields to update

        Returns:
            Portfolio model by default, or dict if raw=True
        """
        self._log_operation("update_async", portfolio_gid)
        result = await self._http.put(
            f"/portfolios/{portfolio_gid}", json={"data": kwargs}
        )
        if raw:
            return result
        return Portfolio.model_validate(result)

    @overload
    def update(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Portfolio:
        """Overload: update (sync), returning Portfolio model."""
        ...

    @overload
    def update(
        self,
        portfolio_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    def update(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Update a portfolio (sync).

        Args:
            portfolio_gid: Portfolio GID
            raw: If True, return raw dict instead of Portfolio model
            **kwargs: Fields to update

        Returns:
            Portfolio model by default, or dict if raw=True
        """
        return self._update_sync(portfolio_gid, raw=raw, **kwargs)

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_async(portfolio_gid, raw=True, **kwargs)
        return await self.update_async(portfolio_gid, raw=False, **kwargs)

    async def delete_async(self, portfolio_gid: str) -> None:
        """Delete a portfolio.

        Args:
            portfolio_gid: Portfolio GID
        """
        self._log_operation("delete_async", portfolio_gid)
        await self._http.delete(f"/portfolios/{portfolio_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, portfolio_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(portfolio_gid)

    def delete(self, portfolio_gid: str) -> None:
        """Delete a portfolio (sync).

        Args:
            portfolio_gid: Portfolio GID
        """
        self._delete_sync(portfolio_gid)

    # --- List Operations ---

    def list_async(
        self,
        *,
        workspace: str,
        owner: str,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Portfolio]:
        """List portfolios.

        Args:
            workspace: Workspace GID
            owner: Owner user GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Portfolio]
        """
        self._log_operation("list_async")

        async def fetch_page(offset: str | None) -> tuple[list[Portfolio], str | None]:
            """Fetch a single page of Portfolio objects."""
            params = self._build_opt_fields(opt_fields)
            params["workspace"] = workspace
            params["owner"] = owner
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                "/portfolios", params=params
            )
            portfolios = [Portfolio.model_validate(p) for p in data]
            return portfolios, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Project Management ---

    def list_items_async(
        self,
        portfolio_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Project]:
        """List projects in a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Project]
        """
        self._log_operation("list_items_async", portfolio_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Project], str | None]:
            """Fetch a single page of Project objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/portfolios/{portfolio_gid}/items", params=params
            )
            projects = [Project.model_validate(p) for p in data]
            return projects, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    async def add_item_async(
        self,
        portfolio_gid: str,
        *,
        item: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a project to a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            item: Project GID to add
            insert_before: Project GID to insert before
            insert_after: Project GID to insert after
        """
        self._log_operation("add_item_async", portfolio_gid)

        data: dict[str, Any] = {"item": item}
        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        await self._http.post(
            f"/portfolios/{portfolio_gid}/addItem", json={"data": data}
        )

    @sync_wrapper("add_item_async")
    async def _add_item_sync(
        self,
        portfolio_gid: str,
        *,
        item: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.add_item_async(
            portfolio_gid,
            item=item,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    def add_item(
        self,
        portfolio_gid: str,
        *,
        item: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a project to a portfolio (sync).

        Args:
            portfolio_gid: Portfolio GID
            item: Project GID to add
            insert_before: Project GID to insert before
            insert_after: Project GID to insert after
        """
        self._add_item_sync(
            portfolio_gid,
            item=item,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    async def remove_item_async(
        self,
        portfolio_gid: str,
        *,
        item: str,
    ) -> None:
        """Remove a project from a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            item: Project GID to remove
        """
        self._log_operation("remove_item_async", portfolio_gid)
        await self._http.post(
            f"/portfolios/{portfolio_gid}/removeItem",
            json={"data": {"item": item}},
        )

    @sync_wrapper("remove_item_async")
    async def _remove_item_sync(
        self,
        portfolio_gid: str,
        *,
        item: str,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.remove_item_async(portfolio_gid, item=item)

    def remove_item(
        self,
        portfolio_gid: str,
        *,
        item: str,
    ) -> None:
        """Remove a project from a portfolio (sync).

        Args:
            portfolio_gid: Portfolio GID
            item: Project GID to remove
        """
        self._remove_item_sync(portfolio_gid, item=item)

    # --- Members ---

    @overload
    async def add_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Portfolio:
        """Overload: add members, returning Portfolio model."""
        ...

    @overload
    async def add_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add members, returning raw dict."""
        ...

    async def add_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Portfolio | dict[str, Any]:
        """Add members to a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            members: List of user GIDs
            raw: If True, return raw dict

        Returns:
            Updated portfolio
        """
        self._log_operation("add_members_async", portfolio_gid)
        result = await self._http.post(
            f"/portfolios/{portfolio_gid}/addMembers",
            json={"data": {"members": ",".join(members)}},
        )
        if raw:
            return result
        return Portfolio.model_validate(result)

    @overload
    def add_members(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Portfolio:
        """Overload: add members (sync), returning Portfolio model."""
        ...

    @overload
    def add_members(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add members (sync), returning raw dict."""
        ...

    def add_members(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Portfolio | dict[str, Any]:
        """Add members (sync).

        Args:
            portfolio_gid: Portfolio GID
            members: List of user GIDs
            raw: If True, return raw dict

        Returns:
            Updated portfolio
        """
        return self._add_members_sync(portfolio_gid, members=members, raw=raw)

    @sync_wrapper("add_members_async")
    async def _add_members_sync(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Portfolio | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.add_members_async(
                portfolio_gid, members=members, raw=True
            )
        return await self.add_members_async(portfolio_gid, members=members, raw=False)

    @overload
    async def remove_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Portfolio:
        """Overload: remove members, returning Portfolio model."""
        ...

    @overload
    async def remove_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: remove members, returning raw dict."""
        ...

    async def remove_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Portfolio | dict[str, Any]:
        """Remove members from a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            members: List of user GIDs
            raw: If True, return raw dict

        Returns:
            Updated portfolio
        """
        self._log_operation("remove_members_async", portfolio_gid)
        result = await self._http.post(
            f"/portfolios/{portfolio_gid}/removeMembers",
            json={"data": {"members": ",".join(members)}},
        )
        if raw:
            return result
        return Portfolio.model_validate(result)

    @overload
    def remove_members(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Portfolio:
        """Overload: remove members (sync), returning Portfolio model."""
        ...

    @overload
    def remove_members(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: remove members (sync), returning raw dict."""
        ...

    def remove_members(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Portfolio | dict[str, Any]:
        """Remove members (sync).

        Args:
            portfolio_gid: Portfolio GID
            members: List of user GIDs
            raw: If True, return raw dict

        Returns:
            Updated portfolio
        """
        return self._remove_members_sync(portfolio_gid, members=members, raw=raw)

    @sync_wrapper("remove_members_async")
    async def _remove_members_sync(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Portfolio | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.remove_members_async(
                portfolio_gid, members=members, raw=True
            )
        return await self.remove_members_async(
            portfolio_gid, members=members, raw=False
        )

    # --- Custom Fields ---

    async def add_custom_field_setting_async(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
        is_important: bool | None = None,
    ) -> None:
        """Add a custom field to a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            custom_field: Custom field GID
            is_important: Whether the field is marked important
        """
        self._log_operation("add_custom_field_setting_async", portfolio_gid)

        data: dict[str, Any] = {"custom_field": custom_field}
        if is_important is not None:
            data["is_important"] = is_important

        await self._http.post(
            f"/portfolios/{portfolio_gid}/addCustomFieldSetting",
            json={"data": data},
        )

    @sync_wrapper("add_custom_field_setting_async")
    async def _add_custom_field_setting_sync(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
        is_important: bool | None = None,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.add_custom_field_setting_async(
            portfolio_gid, custom_field=custom_field, is_important=is_important
        )

    def add_custom_field_setting(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
        is_important: bool | None = None,
    ) -> None:
        """Add a custom field (sync).

        Args:
            portfolio_gid: Portfolio GID
            custom_field: Custom field GID
            is_important: Whether the field is marked important
        """
        self._add_custom_field_setting_sync(
            portfolio_gid, custom_field=custom_field, is_important=is_important
        )

    async def remove_custom_field_setting_async(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Remove a custom field from a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            custom_field: Custom field GID
        """
        self._log_operation("remove_custom_field_setting_async", portfolio_gid)
        await self._http.post(
            f"/portfolios/{portfolio_gid}/removeCustomFieldSetting",
            json={"data": {"custom_field": custom_field}},
        )

    @sync_wrapper("remove_custom_field_setting_async")
    async def _remove_custom_field_setting_sync(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.remove_custom_field_setting_async(
            portfolio_gid, custom_field=custom_field
        )

    def remove_custom_field_setting(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Remove a custom field (sync).

        Args:
            portfolio_gid: Portfolio GID
            custom_field: Custom field GID
        """
        self._remove_custom_field_setting_sync(portfolio_gid, custom_field=custom_field)
