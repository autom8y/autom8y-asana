"""Teams client - returns typed Team models by default.

Per TDD-0004: TeamsClient provides team operations for Tier 2.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator, User
from autom8_asana.models.team import Team, TeamMembership
from autom8_asana.transport.sync import sync_wrapper


class TeamsClient(BaseClient):
    """Client for Asana Team operations.

    Teams exist only in organization workspaces.
    Returns typed Team models by default. Use raw=True for dict returns.
    """

    # --- Core Operations ---

    @overload
    async def get_async(
        self,
        team_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Team:
        """Overload: get, returning Team model."""
        ...

    @overload
    async def get_async(
        self,
        team_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    async def get_async(
        self,
        team_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Team | dict[str, Any]:
        """Get a team by GID.

        Args:
            team_gid: Team GID
            raw: If True, return raw dict instead of Team model
            opt_fields: Optional fields to include

        Returns:
            Team model by default, or dict if raw=True
        """
        self._log_operation("get_async", team_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/teams/{team_gid}", params=params)
        if raw:
            return data
        return Team.model_validate(data)

    @overload
    def get(
        self,
        team_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Team:
        """Overload: get (sync), returning Team model."""
        ...

    @overload
    def get(
        self,
        team_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        team_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Team | dict[str, Any]:
        """Get a team by GID (sync).

        Args:
            team_gid: Team GID
            raw: If True, return raw dict instead of Team model
            opt_fields: Optional fields to include

        Returns:
            Team model by default, or dict if raw=True
        """
        return self._get_sync(team_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        team_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Team | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(team_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(team_gid, raw=False, opt_fields=opt_fields)

    # --- List Operations ---

    def list_for_user_async(
        self,
        user_gid: str,
        *,
        organization: str | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Team]:
        """List teams for a user.

        Args:
            user_gid: User GID (or 'me' for current user)
            organization: Filter by organization workspace GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Team]
        """
        self._log_operation("list_for_user_async", user_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Team], str | None]:
            """Fetch a single page of Team objects."""
            params = self._build_opt_fields(opt_fields)
            if organization:
                params["organization"] = organization
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/users/{user_gid}/teams", params=params
            )
            teams = [Team.model_validate(t) for t in data]
            return teams, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Team]:
        """List teams in an organization workspace.

        Args:
            workspace_gid: Organization workspace GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Team]
        """
        self._log_operation("list_for_workspace_async", workspace_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Team], str | None]:
            """Fetch a single page of Team objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/workspaces/{workspace_gid}/teams", params=params
            )
            teams = [Team.model_validate(t) for t in data]
            return teams, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    def list_users_async(
        self,
        team_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[User]:
        """List users in a team.

        Args:
            team_gid: Team GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[User] - team members
        """
        self._log_operation("list_users_async", team_gid)

        async def fetch_page(offset: str | None) -> tuple[list[User], str | None]:
            """Fetch a single page of User objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/teams/{team_gid}/users", params=params
            )
            users = [User.model_validate(u) for u in data]
            return users, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Membership Operations ---

    @overload
    async def add_user_async(
        self,
        team_gid: str,
        *,
        user: str,
        raw: Literal[False] = ...,
    ) -> TeamMembership:
        """Overload: add user, returning TeamMembership model."""
        ...

    @overload
    async def add_user_async(
        self,
        team_gid: str,
        *,
        user: str,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add user, returning raw dict."""
        ...

    async def add_user_async(
        self,
        team_gid: str,
        *,
        user: str,
        raw: bool = False,
    ) -> TeamMembership | dict[str, Any]:
        """Add a user to a team.

        Args:
            team_gid: Team GID
            user: User GID to add
            raw: If True, return raw dict instead of TeamMembership model

        Returns:
            TeamMembership result
        """
        self._log_operation("add_user_async", team_gid)
        result = await self._http.post(
            f"/teams/{team_gid}/addUser",
            json={"data": {"user": user}},
        )
        if raw:
            return result
        return TeamMembership.model_validate(result)

    @overload
    def add_user(
        self,
        team_gid: str,
        *,
        user: str,
        raw: Literal[False] = ...,
    ) -> TeamMembership:
        """Overload: add user (sync), returning TeamMembership model."""
        ...

    @overload
    def add_user(
        self,
        team_gid: str,
        *,
        user: str,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add user (sync), returning raw dict."""
        ...

    def add_user(
        self,
        team_gid: str,
        *,
        user: str,
        raw: bool = False,
    ) -> TeamMembership | dict[str, Any]:
        """Add a user to a team (sync).

        Args:
            team_gid: Team GID
            user: User GID to add
            raw: If True, return raw dict instead of TeamMembership model

        Returns:
            TeamMembership result
        """
        return self._add_user_sync(team_gid, user=user, raw=raw)

    @sync_wrapper("add_user_async")
    async def _add_user_sync(
        self,
        team_gid: str,
        *,
        user: str,
        raw: bool = False,
    ) -> TeamMembership | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.add_user_async(team_gid, user=user, raw=True)
        return await self.add_user_async(team_gid, user=user, raw=False)

    async def remove_user_async(
        self,
        team_gid: str,
        *,
        user: str,
    ) -> None:
        """Remove a user from a team.

        Args:
            team_gid: Team GID
            user: User GID to remove
        """
        self._log_operation("remove_user_async", team_gid)
        await self._http.post(
            f"/teams/{team_gid}/removeUser",
            json={"data": {"user": user}},
        )

    @sync_wrapper("remove_user_async")
    async def _remove_user_sync(
        self,
        team_gid: str,
        *,
        user: str,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.remove_user_async(team_gid, user=user)

    def remove_user(
        self,
        team_gid: str,
        *,
        user: str,
    ) -> None:
        """Remove a user from a team (sync).

        Args:
            team_gid: Team GID
            user: User GID to remove
        """
        self._remove_user_sync(team_gid, user=user)
