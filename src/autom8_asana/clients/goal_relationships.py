"""Goal relationships management - subgoals and supporting work.

Per ADR-0059: Extracted from GoalsClient to follow SRP.
Manages goal hierarchies (subgoals) and supporting work relationships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload

from autom8_asana.models import PageIterator
from autom8_asana.models.goal import Goal
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from autom8_asana.clients.goals import GoalsClient


class GoalRelationships:
    """Manages goal hierarchy and supporting work relationships.

    This class handles:
    - Subgoal management (list, add, remove)
    - Supporting work relationships (projects/portfolios linked to goals)

    Usage:
        # Via GoalsClient
        client.goals.relationships.list_subgoals_async("goal123")
        client.goals.relationships.add_supporting_work_async("goal123", supporting_resource="proj456")
    """

    def __init__(self, parent: GoalsClient) -> None:
        """Initialize with parent GoalsClient.

        Args:
            parent: The parent GoalsClient instance for HTTP and logging access.
        """
        self._parent = parent

    @property
    def _http(self) -> Any:
        """Access parent's HTTP client."""
        return self._parent._http

    def _log_operation(self, operation: str, resource_gid: str | None = None) -> None:
        """Log operation via parent client."""
        self._parent._log_operation(operation, resource_gid)

    def _build_opt_fields(self, opt_fields: list[str] | None) -> dict[str, Any]:
        """Build opt_fields via parent client."""
        return self._parent._build_opt_fields(opt_fields)

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

    # --- Supporting Work ---

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
        self._remove_supporting_work_sync(
            goal_gid, supporting_resource=supporting_resource
        )
