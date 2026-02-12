"""Name resolution for resources (tags, sections, projects, users).

Per ADR-0060: Per-SaveSession caching for performance (5-10x API reduction).
Per TDD-DESIGN-PATTERNS-D: Uses @async_method for async/sync method generation.
Provides polymorphic name/GID resolution with per-session caching.
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import TYPE_CHECKING, Any, cast

from autom8_asana.exceptions import NameNotFoundError
from autom8_asana.patterns import async_method

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient


class NameResolver:
    """Resolve resource names to GIDs with per-session caching.

    Supports polymorphic input (name_or_gid: str):
    - If input looks like GID (20+ alphanumeric chars): return as-is
    - Otherwise: Fetch resources, find matching name, cache GID, return it

    Cache Structure:
    - Key: f"{resource_type}:{scope}:{name.lower()}"
    - Value: GID
    - Lifetime: Duration of SaveSession (cleared on context exit)
    """

    def __init__(
        self,
        client: AsanaClient,
        session_cache: dict[str, str] | None = None,
    ) -> None:
        """Initialize resolver.

        Args:
            client: AsanaClient instance
            session_cache: Per-SaveSession cache dict (None = new empty dict)
        """
        self._client = client
        self._cache: dict[str, str] = session_cache or {}

    @async_method
    async def resolve_tag(
        self,
        name_or_gid: str,
        project_gid: str | None = None,
    ) -> str:
        """Resolve tag name to GID (workspace-scoped).

        Args:
            name_or_gid: Tag name or GID (e.g., "Urgent" or "1234567890abcdef")
            project_gid: Unused (tags are workspace-scoped, not project-scoped)

        Returns:
            Tag GID

        Raises:
            NameNotFoundError: If name not found (with suggestions)

        Example:
            >>> gid = await resolver.resolve_tag_async("Urgent")
            >>> # Or passthrough if already GID:
            >>> gid = await resolver.resolve_tag_async("1234567890abcdef1234")
        """
        # Passthrough if looks like GID
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        # Get workspace GID from client
        workspace_gid = cast(Any, self._client).default_workspace_gid

        # Check cache
        cache_key = f"tag:{workspace_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all tags in workspace
        all_tags = []
        async for tag in self._client.tags.list_for_workspace_async(workspace_gid):
            all_tags.append(tag)

        # Find exact match (case-insensitive, whitespace-tolerant)
        for tag in all_tags:
            if tag.name and tag.name.lower().strip() == name_or_gid.lower().strip():
                self._cache[cache_key] = tag.gid
                return tag.gid

        # Not found - suggest alternatives
        available_names = [tag.name for tag in all_tags]
        suggestions = get_close_matches(
            name_or_gid,
            [n for n in available_names if n],
            n=3,
            cutoff=0.6,
        )

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="tag",
            scope=workspace_gid,
            suggestions=suggestions,
            available_names=[n for n in available_names if n],
        )

    @async_method
    async def resolve_section(
        self,
        name_or_gid: str,
        project_gid: str,
    ) -> str:
        """Resolve section name to GID (project-scoped).

        Args:
            name_or_gid: Section name or GID
            project_gid: Project context (sections scoped to projects)

        Returns:
            Section GID

        Raises:
            NameNotFoundError: If name not found
        """
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        cache_key = f"section:{project_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all sections in project
        all_sections = []
        async for section in self._client.sections.list_for_project_async(project_gid):
            all_sections.append(section)

        # Find exact match
        for section in all_sections:
            if (
                section.name
                and section.name.lower().strip() == name_or_gid.lower().strip()
            ):
                self._cache[cache_key] = section.gid
                return section.gid

        # Not found
        available_names = [s.name for s in all_sections if s.name]
        suggestions = get_close_matches(
            name_or_gid,
            available_names,
            n=3,
            cutoff=0.6,
        )

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="section",
            scope=project_gid,
            suggestions=suggestions,
            available_names=available_names,
        )

    @async_method
    async def resolve_project(
        self,
        name_or_gid: str,
        workspace_gid: str,
    ) -> str:
        """Resolve project name to GID (workspace-scoped).

        Args:
            name_or_gid: Project name or GID
            workspace_gid: Workspace context

        Returns:
            Project GID

        Raises:
            NameNotFoundError: If name not found
        """
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        cache_key = f"project:{workspace_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all projects in workspace
        all_projects = []
        async for project in self._client.projects.list_async(workspace=workspace_gid):
            all_projects.append(project)

        # Find exact match
        for project in all_projects:
            if (
                project.name
                and project.name.lower().strip() == name_or_gid.lower().strip()
            ):
                self._cache[cache_key] = project.gid
                return project.gid

        # Not found
        available_names = [p.name for p in all_projects if p.name]
        suggestions = get_close_matches(
            name_or_gid,
            available_names,
            n=3,
            cutoff=0.6,
        )

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="project",
            scope=workspace_gid,
            suggestions=suggestions,
            available_names=available_names,
        )

    @async_method
    async def resolve_assignee(
        self,
        name_or_gid: str,
        workspace_gid: str,
    ) -> str:
        """Resolve user name or email to GID (workspace-scoped).

        Args:
            name_or_gid: User name, email, or GID
            workspace_gid: Workspace context

        Returns:
            User GID

        Raises:
            NameNotFoundError: If name/email not found
        """
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        cache_key = f"user:{workspace_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all users in workspace
        all_users = []
        async for user in self._client.users.list_for_workspace_async(workspace_gid):
            all_users.append(user)

        # Find match by name or email (case-insensitive)
        for user in all_users:
            user_email = user.email.lower().strip() if user.email else ""
            if (
                user.name and user.name.lower().strip() == name_or_gid.lower().strip()
            ) or user_email == name_or_gid.lower().strip():
                self._cache[cache_key] = user.gid
                return user.gid

        # Not found
        available = [
            f"{u.name} ({u.email})" if u.email else u.name for u in all_users if u.name
        ]
        suggestions = get_close_matches(
            name_or_gid,
            available,
            n=3,
            cutoff=0.6,
        )

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="user",
            scope=workspace_gid,
            suggestions=suggestions,
            available_names=available,
        )

    @staticmethod
    def _looks_like_gid(value: str) -> bool:
        """Check if value looks like an Asana GID.

        GIDs are 20+ character alphanumeric strings (may contain underscores).

        Args:
            value: String to test

        Returns:
            True if value looks like a GID
        """
        if len(value) < 20:
            return False
        # Remove underscores and check if remaining is alphanumeric
        return value.replace("_", "").isalnum()
