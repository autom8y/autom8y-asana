"""Goal followers management.

Per ADR-0059: Extracted from GoalsClient to follow SRP.
Manages adding and removing followers from goals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload

from autom8_asana.models.goal import Goal
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from autom8_asana.clients.goals import GoalsClient


class GoalFollowers:
    """Manages goal follower relationships.

    This class handles:
    - Adding followers to goals
    - Removing followers from goals

    Usage:
        # Via GoalsClient
        client.goals.followers.add_followers_async("goal123", followers=["user1", "user2"])
        client.goals.followers.remove_followers_async("goal123", followers=["user1"])
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

    # --- Add Followers ---

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
        result: dict[str, Any] = await self._http.post(
            f"/goals/{goal_gid}/addFollowers",
            json={"data": {"followers": ",".join(followers)}},
        )
        if raw:
            return result
        goal: Goal = Goal.model_validate(result)
        return goal

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
            return await self.add_followers_async(
                goal_gid, followers=followers, raw=True
            )
        return await self.add_followers_async(goal_gid, followers=followers, raw=False)

    # --- Remove Followers ---

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
        result: dict[str, Any] = await self._http.post(
            f"/goals/{goal_gid}/removeFollowers",
            json={"data": {"followers": ",".join(followers)}},
        )
        if raw:
            return result
        goal: Goal = Goal.model_validate(result)
        return goal

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
