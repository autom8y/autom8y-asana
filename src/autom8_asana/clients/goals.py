"""Goals client - returns typed Goal models by default.

Per TDD-0004: GoalsClient provides goal CRUD, subgoals, and supporting work for Tier 2.
Per TDD-DESIGN-PATTERNS-D: Uses @async_method for async/sync method generation.
Per ADR-0059: Subgoal, supporting work, and follower operations delegated to extracted classes.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.goal import Goal
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method

if TYPE_CHECKING:
    from autom8_asana.clients.goal_followers import GoalFollowers
    from autom8_asana.clients.goal_relationships import GoalRelationships


class GoalsClient(BaseClient):
    """Client for Asana Goal operations.

    Goals support hierarchical organization (subgoals).
    Returns typed Goal models by default. Use raw=True for dict returns.

    Per ADR-0059: Relationship and follower operations are delegated to
    extracted classes accessible via the `relationships` and `followers`
    properties. Backward-compatible delegation methods are provided.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize GoalsClient with lazy-loaded sub-clients."""
        super().__init__(*args, **kwargs)
        self._relationships: GoalRelationships | None = None
        self._followers: GoalFollowers | None = None

    # --- Sub-client Properties (Lazy Initialization) ---

    @property
    def relationships(self) -> GoalRelationships:
        """Access goal relationships operations (subgoals, supporting work).

        Returns:
            GoalRelationships instance for managing goal hierarchies.
        """
        if self._relationships is None:
            from autom8_asana.clients.goal_relationships import GoalRelationships

            self._relationships = GoalRelationships(self)
        return self._relationships

    @property
    def followers(self) -> GoalFollowers:
        """Access goal followers operations.

        Returns:
            GoalFollowers instance for managing goal followers.
        """
        if self._followers is None:
            from autom8_asana.clients.goal_followers import GoalFollowers

            self._followers = GoalFollowers(self)
        return self._followers

    # --- Core CRUD Operations ---

    @overload  # type: ignore[no-overload-impl]
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

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def get(
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

    @overload  # type: ignore[no-overload-impl]
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

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def create(
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

    @overload  # type: ignore[no-overload-impl]
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

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def update(
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

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def delete(self, goal_gid: str) -> None:
        """Delete a goal.

        Args:
            goal_gid: Goal GID
        """
        self._log_operation("delete_async", goal_gid)
        await self._http.delete(f"/goals/{goal_gid}")

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

    # --- Delegation Methods (Backward Compatibility) ---
    # Note: For type-safe overloaded versions, use .relationships and .followers properties

    def list_subgoals_async(self, goal_gid: str, **kwargs: Any) -> PageIterator[Goal]:
        """List subgoals. Delegates to relationships."""
        return self.relationships.list_subgoals_async(goal_gid, **kwargs)

    async def add_subgoal_async(
        self, goal_gid: str, **kwargs: Any
    ) -> Goal | dict[str, Any]:
        """Add a subgoal. Delegates to relationships."""
        result: Goal | dict[str, Any] = await self.relationships.add_subgoal_async(
            goal_gid, **kwargs
        )
        return result

    def add_subgoal(self, goal_gid: str, **kwargs: Any) -> Goal | dict[str, Any]:
        """Add a subgoal (sync). Delegates to relationships."""
        result: Goal | dict[str, Any] = self.relationships.add_subgoal(
            goal_gid, **kwargs
        )
        return result

    async def remove_subgoal_async(self, goal_gid: str, *, subgoal: str) -> None:
        """Remove a subgoal. Delegates to relationships."""
        await self.relationships.remove_subgoal_async(goal_gid, subgoal=subgoal)  # type: ignore[attr-defined]

    def remove_subgoal(self, goal_gid: str, *, subgoal: str) -> None:
        """Remove a subgoal (sync). Delegates to relationships."""
        self.relationships.remove_subgoal(goal_gid, subgoal=subgoal)

    async def add_supporting_work_async(
        self, goal_gid: str, **kwargs: Any
    ) -> Goal | dict[str, Any]:
        """Add supporting work. Delegates to relationships."""
        result: (
            Goal | dict[str, Any]
        ) = await self.relationships.add_supporting_work_async(goal_gid, **kwargs)
        return result

    def add_supporting_work(
        self, goal_gid: str, **kwargs: Any
    ) -> Goal | dict[str, Any]:
        """Add supporting work (sync). Delegates to relationships."""
        result: Goal | dict[str, Any] = self.relationships.add_supporting_work(
            goal_gid, **kwargs
        )
        return result

    async def remove_supporting_work_async(
        self, goal_gid: str, *, supporting_resource: str
    ) -> None:
        """Remove supporting work. Delegates to relationships."""
        await self.relationships.remove_supporting_work_async(  # type: ignore[attr-defined]
            goal_gid, supporting_resource=supporting_resource
        )

    def remove_supporting_work(
        self, goal_gid: str, *, supporting_resource: str
    ) -> None:
        """Remove supporting work (sync). Delegates to relationships."""
        self.relationships.remove_supporting_work(
            goal_gid, supporting_resource=supporting_resource
        )

    async def add_followers_async(
        self, goal_gid: str, **kwargs: Any
    ) -> Goal | dict[str, Any]:
        """Add followers. Delegates to followers."""
        result: Goal | dict[str, Any] = await self.followers.add_followers_async(
            goal_gid, **kwargs
        )
        return result

    def add_followers(self, goal_gid: str, **kwargs: Any) -> Goal | dict[str, Any]:
        """Add followers (sync). Delegates to followers."""
        result: Goal | dict[str, Any] = self.followers.add_followers(goal_gid, **kwargs)
        return result

    async def remove_followers_async(
        self, goal_gid: str, **kwargs: Any
    ) -> Goal | dict[str, Any]:
        """Remove followers. Delegates to followers."""
        result: Goal | dict[str, Any] = await self.followers.remove_followers_async(
            goal_gid, **kwargs
        )
        return result

    def remove_followers(self, goal_gid: str, **kwargs: Any) -> Goal | dict[str, Any]:
        """Remove followers (sync). Delegates to followers."""
        result: Goal | dict[str, Any] = self.followers.remove_followers(
            goal_gid, **kwargs
        )
        return result
