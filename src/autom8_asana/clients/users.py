"""Users client - returns typed User models by default.

Per TDD-0003: UsersClient provides get, me, and list_for_workspace operations.
Per TDD-DESIGN-PATTERNS-D: Uses @async_method for async/sync method generation.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.user import User
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method
from autom8_asana.settings import get_settings

# Cache TTL for user metadata (1 hour)
# User profiles change infrequently (name, email rarely modified)
# Configurable via ASANA_CACHE_TTL_USER environment variable
USER_CACHE_TTL = get_settings().cache.ttl_user


class UsersClient(BaseClient):
    """Client for Asana User operations.

    Returns typed User models by default. Use raw=True for dict returns.
    """

    @overload  # type: ignore[no-overload-impl]
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

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def get(
        self,
        user_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Get a user by GID with cache support.

        Per TDD-CACHE-UTILIZATION: Checks cache before HTTP request.
        Per ADR-0119: 6-step client cache integration pattern.

        Args:
            user_gid: User GID
            raw: If True, return raw dict instead of User model
            opt_fields: Optional fields to include

        Returns:
            User model by default, or dict if raw=True

        Raises:
            GidValidationError: If user_gid is invalid.
        """
        from autom8_asana.cache.models.entry import EntryType
        from autom8_asana.persistence.validation import validate_gid

        # Step 1: Validate GID
        validate_gid(user_gid, "user_gid")

        # Step 2: Check cache first
        cached_entry = self._cache_get(user_gid, EntryType.USER)
        if cached_entry is not None:
            # Step 3: Cache hit - return cached data
            data = cached_entry.data
            if raw:
                return data
            return User.model_validate(data)

        # Step 4: Cache miss - fetch from API
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/users/{user_gid}", params=params)

        # Step 5: Store in cache
        self._cache_set(user_gid, data, EntryType.USER, ttl=USER_CACHE_TTL)

        # Step 6: Return model or raw dict
        if raw:
            return data
        return User.model_validate(data)

    @overload  # type: ignore[no-overload-impl]
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

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def me(
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
