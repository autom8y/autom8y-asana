"""Users client - returns typed User models by default.

Per TDD-0003: UsersClient provides get, me, and list_for_workspace operations.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.user import User
from autom8_asana.transport.sync import sync_wrapper


class UsersClient(BaseClient):
    """Client for Asana User operations.

    Returns typed User models by default. Use raw=True for dict returns.
    """

    @overload
    async def get_async(
        self,
        user_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> User:
        """Overload: get, returning User model."""
        ...

    @overload
    async def get_async(
        self,
        user_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    async def get_async(
        self,
        user_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Get a user by GID.

        Args:
            user_gid: User GID
            raw: If True, return raw dict instead of User model
            opt_fields: Optional fields to include

        Returns:
            User model by default, or dict if raw=True
        """
        self._log_operation("get_async", user_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/users/{user_gid}", params=params)
        if raw:
            return data
        return User.model_validate(data)

    @overload
    def get(
        self,
        user_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> User:
        """Overload: get (sync), returning User model."""
        ...

    @overload
    def get(
        self,
        user_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        user_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Get a user by GID (sync).

        Args:
            user_gid: User GID
            raw: If True, return raw dict instead of User model
            opt_fields: Optional fields to include

        Returns:
            User model by default, or dict if raw=True
        """
        return self._get_sync(user_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        user_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(user_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(user_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def me_async(
        self,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> User:
        """Overload: me, returning User model."""
        ...

    @overload
    async def me_async(
        self,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: me, returning raw dict."""
        ...

    async def me_async(
        self,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Get the current authenticated user.

        This is a convenience method that calls GET /users/me.

        Args:
            raw: If True, return raw dict instead of User model
            opt_fields: Optional fields to include

        Returns:
            User model by default, or dict if raw=True
        """
        self._log_operation("me_async")
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get("/users/me", params=params)
        if raw:
            return data
        return User.model_validate(data)

    @overload
    def me(
        self,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> User:
        """Overload: me (sync), returning User model."""
        ...

    @overload
    def me(
        self,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: me (sync), returning raw dict."""
        ...

    def me(
        self,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Get the current authenticated user (sync).

        Args:
            raw: If True, return raw dict instead of User model
            opt_fields: Optional fields to include

        Returns:
            User model by default, or dict if raw=True
        """
        return self._me_sync(raw=raw, opt_fields=opt_fields)

    @sync_wrapper("me_async")
    async def _me_sync(
        self,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.me_async(raw=True, opt_fields=opt_fields)
        return await self.me_async(raw=False, opt_fields=opt_fields)

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[User]:
        """List users in a workspace with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            workspace_gid: Workspace GID to list users from
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[User] - async iterator over User objects

        Example:
            async for user in client.users.list_for_workspace_async("123"):
                print(f"{user.name}: {user.email}")
        """
        self._log_operation("list_for_workspace_async", workspace_gid)

        async def fetch_page(offset: str | None) -> tuple[list[User], str | None]:
            """Fetch a single page of User objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/workspaces/{workspace_gid}/users", params=params
            )
            users = [User.model_validate(u) for u in data]
            return users, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))
