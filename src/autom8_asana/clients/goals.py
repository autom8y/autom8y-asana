"""Goals client - returns typed Goal models by default.

Per TDD-0004: GoalsClient provides goal CRUD, subgoals, and supporting work for Tier 2.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.goal import Goal
from autom8_asana.transport.sync import sync_wrapper


class GoalsClient(BaseClient):
    """Client for Asana Goal operations.

    Goals support hierarchical organization (subgoals).
    Returns typed Goal models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    @overload
    async def get_async(
        self,
        goal_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Goal:
        """Overload: get, returning Goal model."""
        ...

    @overload
    async def get_async(
        self,
        goal_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    async def get_async(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Goal | dict[str, Any]:
        """Get a goal by GID.

        Args:
            goal_gid: Goal GID
            raw: If True, return raw dict instead of Goal model
            opt_fields: Optional fields to include

        Returns:
            Goal model by default, or dict if raw=True
        """
        self._log_operation("get_async", goal_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/goals/{goal_gid}", params=params)
        if raw:
            return data
        return Goal.model_validate(data)

    @overload
    def get(
        self,
        goal_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Goal:
        """Overload: get (sync), returning Goal model."""
        ...

    @overload
    def get(
        self,
        goal_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Goal | dict[str, Any]:
        """Get a goal by GID (sync).

        Args:
            goal_gid: Goal GID
            raw: If True, return raw dict instead of Goal model
            opt_fields: Optional fields to include

        Returns:
            Goal model by default, or dict if raw=True
        """
        return self._get_sync(goal_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Goal | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(goal_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(goal_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[False] = ...,
        due_on: str | None = ...,
        start_on: str | None = ...,
        owner: str | None = ...,
        team: str | None = ...,
        time_period: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> Goal:
        """Overload: create, returning Goal model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[True],
        due_on: str | None = ...,
        start_on: str | None = ...,
        owner: str | None = ...,
        team: str | None = ...,
        time_period: str | None = ...,
        notes: str | None = ...,
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
        due_on: str | None = None,
        start_on: str | None = None,
        owner: str | None = None,
        team: str | None = None,
        time_period: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Create a goal.

        Args:
            workspace: Workspace GID
            name: Goal name
            raw: If True, return raw dict
            due_on: Due date (YYYY-MM-DD)
            start_on: Start date (YYYY-MM-DD)
            owner: Owner user GID
            team: Team GID (for team goals)
            time_period: Time period GID
            notes: Goal description
            **kwargs: Additional goal fields

        Returns:
            Goal model by default, or dict if raw=True
        """
        self._log_operation("create_async")

        data: dict[str, Any] = {"workspace": workspace, "name": name}

        if due_on is not None:
            data["due_on"] = due_on
        if start_on is not None:
            data["start_on"] = start_on
        if owner is not None:
            data["owner"] = owner
        if team is not None:
            data["team"] = team
        if time_period is not None:
            data["time_period"] = time_period
        if notes is not None:
            data["notes"] = notes

        data.update(kwargs)

        result = await self._http.post("/goals", json={"data": data})
        if raw:
            return result
        return Goal.model_validate(result)

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[False] = ...,
        due_on: str | None = ...,
        start_on: str | None = ...,
        owner: str | None = ...,
        team: str | None = ...,
        time_period: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> Goal:
        """Overload: create (sync), returning Goal model."""
        ...

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        raw: Literal[True],
        due_on: str | None = ...,
        start_on: str | None = ...,
        owner: str | None = ...,
        team: str | None = ...,
        time_period: str | None = ...,
        notes: str | None = ...,
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
        due_on: str | None = None,
        start_on: str | None = None,
        owner: str | None = None,
        team: str | None = None,
        time_period: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Create a goal (sync).

        Args:
            workspace: Workspace GID
            name: Goal name
            raw: If True, return raw dict
            due_on: Due date (YYYY-MM-DD)
            start_on: Start date (YYYY-MM-DD)
            owner: Owner user GID
            team: Team GID (for team goals)
            time_period: Time period GID
            notes: Goal description
            **kwargs: Additional goal fields

        Returns:
            Goal model by default, or dict if raw=True
        """
        return self._create_sync(
            workspace=workspace,
            name=name,
            raw=raw,
            due_on=due_on,
            start_on=start_on,
            owner=owner,
            team=team,
            time_period=time_period,
            notes=notes,
            **kwargs,
        )

    @sync_wrapper("create_async")
    async def _create_sync(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        due_on: str | None = None,
        start_on: str | None = None,
        owner: str | None = None,
        team: str | None = None,
        time_period: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_async(
                workspace=workspace,
                name=name,
                raw=True,
                due_on=due_on,
                start_on=start_on,
                owner=owner,
                team=team,
                time_period=time_period,
                notes=notes,
                **kwargs,
            )
        return await self.create_async(
            workspace=workspace,
            name=name,
            raw=False,
            due_on=due_on,
            start_on=start_on,
            owner=owner,
            team=team,
            time_period=time_period,
            notes=notes,
            **kwargs,
        )

    @overload
    async def update_async(
        self,
        goal_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Goal:
        """Overload: update, returning Goal model."""
        ...

    @overload
    async def update_async(
        self,
        goal_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

    async def update_async(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Update a goal.

        Args:
            goal_gid: Goal GID
            raw: If True, return raw dict instead of Goal model
            **kwargs: Fields to update

        Returns:
            Goal model by default, or dict if raw=True
        """
        self._log_operation("update_async", goal_gid)
        result = await self._http.put(f"/goals/{goal_gid}", json={"data": kwargs})
        if raw:
            return result
        return Goal.model_validate(result)

    @overload
    def update(
        self,
        goal_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Goal:
        """Overload: update (sync), returning Goal model."""
        ...

    @overload
    def update(
        self,
        goal_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    def update(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Update a goal (sync).

        Args:
            goal_gid: Goal GID
            raw: If True, return raw dict instead of Goal model
            **kwargs: Fields to update

        Returns:
            Goal model by default, or dict if raw=True
        """
        return self._update_sync(goal_gid, raw=raw, **kwargs)

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_async(goal_gid, raw=True, **kwargs)
        return await self.update_async(goal_gid, raw=False, **kwargs)

    async def delete_async(self, goal_gid: str) -> None:
        """Delete a goal.

        Args:
            goal_gid: Goal GID
        """
        self._log_operation("delete_async", goal_gid)
        await self._http.delete(f"/goals/{goal_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, goal_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(goal_gid)

    def delete(self, goal_gid: str) -> None:
        """Delete a goal (sync).

        Args:
            goal_gid: Goal GID
        """
        self._delete_sync(goal_gid)

    # --- List Operations ---

    def list_async(
        self,
        *,
        workspace: str | None = None,
        team: str | None = None,
        portfolio: str | None = None,
        project: str | None = None,
        is_workspace_level: bool | None = None,
        time_periods: list[str] | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Goal]:
        """List goals.

        At least one of workspace, team, portfolio, or project is required.

        Args:
            workspace: Filter by workspace
            team: Filter by team
            portfolio: Filter by portfolio
            project: Filter by supporting project
            is_workspace_level: Filter workspace-level goals
            time_periods: Filter by time period GIDs
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Goal]
        """
        self._log_operation("list_async")

        async def fetch_page(offset: str | None) -> tuple[list[Goal], str | None]:
            """Fetch a single page of Goal objects."""
            params = self._build_opt_fields(opt_fields)
            if workspace:
                params["workspace"] = workspace
            if team:
                params["team"] = team
            if portfolio:
                params["portfolio"] = portfolio
            if project:
                params["project"] = project
            if is_workspace_level is not None:
                params["is_workspace_level"] = is_workspace_level
            if time_periods:
                params["time_periods"] = ",".join(time_periods)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated("/goals", params=params)
            goals = [Goal.model_validate(g) for g in data]
            return goals, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Subgoals ---

    def list_subgoals_async(
        self,
        goal_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Goal]:
        """List subgoals of a goal.

        Args:
            goal_gid: Parent goal GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Goal]
        """
        self._log_operation("list_subgoals_async", goal_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Goal], str | None]:
            """Fetch a single page of Goal objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/goals/{goal_gid}/subgoals", params=params
            )
            goals = [Goal.model_validate(g) for g in data]
            return goals, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    @overload
    async def add_subgoal_async(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        raw: Literal[False] = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> Goal:
        """Overload: add subgoal, returning Goal model."""
        ...

    @overload
    async def add_subgoal_async(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        raw: Literal[True],
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: add subgoal, returning raw dict."""
        ...

    async def add_subgoal_async(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        raw: bool = False,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Goal | dict[str, Any]:
        """Add a subgoal to a goal.

        Args:
            goal_gid: Parent goal GID
            subgoal: Subgoal GID to add
            raw: If True, return raw dict
            insert_before: Subgoal GID to insert before
            insert_after: Subgoal GID to insert after

        Returns:
            Updated parent goal
        """
        self._log_operation("add_subgoal_async", goal_gid)

        data: dict[str, Any] = {"subgoal": subgoal}
        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        result = await self._http.post(
            f"/goals/{goal_gid}/addSubgoal", json={"data": data}
        )
        if raw:
            return result
        return Goal.model_validate(result)

    @overload
    def add_subgoal(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        raw: Literal[False] = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> Goal:
        """Overload: add subgoal (sync), returning Goal model."""
        ...

    @overload
    def add_subgoal(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        raw: Literal[True],
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: add subgoal (sync), returning raw dict."""
        ...

    def add_subgoal(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        raw: bool = False,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Goal | dict[str, Any]:
        """Add a subgoal (sync).

        Args:
            goal_gid: Parent goal GID
            subgoal: Subgoal GID to add
            raw: If True, return raw dict
            insert_before: Subgoal GID to insert before
            insert_after: Subgoal GID to insert after

        Returns:
            Updated parent goal
        """
        return self._add_subgoal_sync(
            goal_gid,
            subgoal=subgoal,
            raw=raw,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    @sync_wrapper("add_subgoal_async")
    async def _add_subgoal_sync(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        raw: bool = False,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Goal | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.add_subgoal_async(
                goal_gid,
                subgoal=subgoal,
                raw=True,
                insert_before=insert_before,
                insert_after=insert_after,
            )
        return await self.add_subgoal_async(
            goal_gid,
            subgoal=subgoal,
            raw=False,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    async def remove_subgoal_async(
        self,
        goal_gid: str,
        *,
        subgoal: str,
    ) -> None:
        """Remove a subgoal from a goal.

        Args:
            goal_gid: Parent goal GID
            subgoal: Subgoal GID to remove
        """
        self._log_operation("remove_subgoal_async", goal_gid)
        await self._http.post(
            f"/goals/{goal_gid}/removeSubgoal",
            json={"data": {"subgoal": subgoal}},
        )

    @sync_wrapper("remove_subgoal_async")
    async def _remove_subgoal_sync(
        self,
        goal_gid: str,
        *,
        subgoal: str,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.remove_subgoal_async(goal_gid, subgoal=subgoal)

    def remove_subgoal(
        self,
        goal_gid: str,
        *,
        subgoal: str,
    ) -> None:
        """Remove a subgoal (sync).

        Args:
            goal_gid: Parent goal GID
            subgoal: Subgoal GID to remove
        """
        self._remove_subgoal_sync(goal_gid, subgoal=subgoal)

    # --- Supporting Resources ---

    @overload
    async def add_supporting_work_async(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        raw: Literal[False] = ...,
        contribution_weight: float | None = ...,
    ) -> Goal:
        """Overload: add supporting work, returning Goal model."""
        ...

    @overload
    async def add_supporting_work_async(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        raw: Literal[True],
        contribution_weight: float | None = ...,
    ) -> dict[str, Any]:
        """Overload: add supporting work, returning raw dict."""
        ...

    async def add_supporting_work_async(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        raw: bool = False,
        contribution_weight: float | None = None,
    ) -> Goal | dict[str, Any]:
        """Add supporting work (project/portfolio) to a goal.

        Args:
            goal_gid: Goal GID
            supporting_resource: Project or portfolio GID
            raw: If True, return raw dict
            contribution_weight: Optional weight (0.0 to 1.0)

        Returns:
            Updated goal
        """
        self._log_operation("add_supporting_work_async", goal_gid)

        data: dict[str, Any] = {"supporting_resource": supporting_resource}
        if contribution_weight is not None:
            data["contribution_weight"] = contribution_weight

        result = await self._http.post(
            f"/goals/{goal_gid}/addSupportingRelationship", json={"data": data}
        )
        if raw:
            return result
        return Goal.model_validate(result)

    @overload
    def add_supporting_work(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        raw: Literal[False] = ...,
        contribution_weight: float | None = ...,
    ) -> Goal:
        """Overload: add supporting work (sync), returning Goal model."""
        ...

    @overload
    def add_supporting_work(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        raw: Literal[True],
        contribution_weight: float | None = ...,
    ) -> dict[str, Any]:
        """Overload: add supporting work (sync), returning raw dict."""
        ...

    def add_supporting_work(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        raw: bool = False,
        contribution_weight: float | None = None,
    ) -> Goal | dict[str, Any]:
        """Add supporting work (sync).

        Args:
            goal_gid: Goal GID
            supporting_resource: Project or portfolio GID
            raw: If True, return raw dict
            contribution_weight: Optional weight (0.0 to 1.0)

        Returns:
            Updated goal
        """
        return self._add_supporting_work_sync(
            goal_gid,
            supporting_resource=supporting_resource,
            raw=raw,
            contribution_weight=contribution_weight,
        )

    @sync_wrapper("add_supporting_work_async")
    async def _add_supporting_work_sync(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        raw: bool = False,
        contribution_weight: float | None = None,
    ) -> Goal | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.add_supporting_work_async(
                goal_gid,
                supporting_resource=supporting_resource,
                raw=True,
                contribution_weight=contribution_weight,
            )
        return await self.add_supporting_work_async(
            goal_gid,
            supporting_resource=supporting_resource,
            raw=False,
            contribution_weight=contribution_weight,
        )

    async def remove_supporting_work_async(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
    ) -> None:
        """Remove supporting work from a goal.

        Args:
            goal_gid: Goal GID
            supporting_resource: Project or portfolio GID to remove
        """
        self._log_operation("remove_supporting_work_async", goal_gid)
        await self._http.post(
            f"/goals/{goal_gid}/removeSupportingRelationship",
            json={"data": {"supporting_resource": supporting_resource}},
        )

    @sync_wrapper("remove_supporting_work_async")
    async def _remove_supporting_work_sync(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.remove_supporting_work_async(
            goal_gid, supporting_resource=supporting_resource
        )

    def remove_supporting_work(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
    ) -> None:
        """Remove supporting work (sync).

        Args:
            goal_gid: Goal GID
            supporting_resource: Project or portfolio GID to remove
        """
        self._remove_supporting_work_sync(goal_gid, supporting_resource=supporting_resource)

    # --- Followers ---

    @overload
    async def add_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[False] = ...,
    ) -> Goal:
        """Overload: add followers, returning Goal model."""
        ...

    @overload
    async def add_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add followers, returning raw dict."""
        ...

    async def add_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: bool = False,
    ) -> Goal | dict[str, Any]:
        """Add followers to a goal.

        Args:
            goal_gid: Goal GID
            followers: List of user GIDs

        Returns:
            Updated goal
        """
        self._log_operation("add_followers_async", goal_gid)
        result = await self._http.post(
            f"/goals/{goal_gid}/addFollowers",
            json={"data": {"followers": ",".join(followers)}},
        )
        if raw:
            return result
        return Goal.model_validate(result)

    @overload
    def add_followers(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[False] = ...,
    ) -> Goal:
        """Overload: add followers (sync), returning Goal model."""
        ...

    @overload
    def add_followers(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add followers (sync), returning raw dict."""
        ...

    def add_followers(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: bool = False,
    ) -> Goal | dict[str, Any]:
        """Add followers (sync).

        Args:
            goal_gid: Goal GID
            followers: List of user GIDs

        Returns:
            Updated goal
        """
        return self._add_followers_sync(goal_gid, followers=followers, raw=raw)

    @sync_wrapper("add_followers_async")
    async def _add_followers_sync(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: bool = False,
    ) -> Goal | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.add_followers_async(goal_gid, followers=followers, raw=True)
        return await self.add_followers_async(goal_gid, followers=followers, raw=False)

    @overload
    async def remove_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[False] = ...,
    ) -> Goal:
        """Overload: remove followers, returning Goal model."""
        ...

    @overload
    async def remove_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: remove followers, returning raw dict."""
        ...

    async def remove_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: bool = False,
    ) -> Goal | dict[str, Any]:
        """Remove followers from a goal.

        Args:
            goal_gid: Goal GID
            followers: List of user GIDs

        Returns:
            Updated goal
        """
        self._log_operation("remove_followers_async", goal_gid)
        result = await self._http.post(
            f"/goals/{goal_gid}/removeFollowers",
            json={"data": {"followers": ",".join(followers)}},
        )
        if raw:
            return result
        return Goal.model_validate(result)

    @overload
    def remove_followers(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[False] = ...,
    ) -> Goal:
        """Overload: remove followers (sync), returning Goal model."""
        ...

    @overload
    def remove_followers(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: remove followers (sync), returning raw dict."""
        ...

    def remove_followers(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: bool = False,
    ) -> Goal | dict[str, Any]:
        """Remove followers (sync).

        Args:
            goal_gid: Goal GID
            followers: List of user GIDs

        Returns:
            Updated goal
        """
        return self._remove_followers_sync(goal_gid, followers=followers, raw=raw)

    @sync_wrapper("remove_followers_async")
    async def _remove_followers_sync(
        self,
        goal_gid: str,
        *,
        followers: list[str],
        raw: bool = False,
    ) -> Goal | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.remove_followers_async(
                goal_gid, followers=followers, raw=True
            )
        return await self.remove_followers_async(
            goal_gid, followers=followers, raw=False
        )
