"""Projects client - returns typed Project models by default.

Per TDD-0003: ProjectsClient provides CRUD and membership operations.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.project import Project
from autom8_asana.models.section import Section
from autom8_asana.observability import error_handler
from autom8_asana.transport.sync import sync_wrapper


class ProjectsClient(BaseClient):
    """Client for Asana Project operations.

    Returns typed Project models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    @overload
    async def get_async(
        self,
        project_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Project:
        """Overload: get, returning Project model."""
        ...

    @overload
    async def get_async(
        self,
        project_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    @error_handler
    async def get_async(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Project | dict[str, Any]:
        """Get a project by GID with cache support.

        Per TDD-CACHE-UTILIZATION: Checks cache before HTTP request.
        Per ADR-0119: 6-step client cache integration pattern.

        Args:
            project_gid: Project GID
            raw: If True, return raw dict instead of Project model
            opt_fields: Optional fields to include

        Returns:
            Project model by default, or dict if raw=True

        Raises:
            GidValidationError: If project_gid is invalid.
        """
        from autom8_asana.cache.entry import EntryType
        from autom8_asana.persistence.validation import validate_gid

        # Step 1: Validate GID
        validate_gid(project_gid, "project_gid")

        # Step 2: Check cache first
        cached_entry = self._cache_get(project_gid, EntryType.PROJECT)
        if cached_entry is not None:
            # Step 3: Cache hit - return cached data
            data = cached_entry.data
            if raw:
                return data
            return Project.model_validate(data)

        # Step 4: Cache miss - fetch from API
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/projects/{project_gid}", params=params)

        # Step 5: Store in cache (15 min TTL)
        self._cache_set(project_gid, data, EntryType.PROJECT, ttl=900)

        # Step 6: Return model or raw dict
        if raw:
            return data
        return Project.model_validate(data)

    @overload
    def get(
        self,
        project_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Project:
        """Overload: get (sync), returning Project model."""
        ...

    @overload
    def get(
        self,
        project_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Project | dict[str, Any]:
        """Get a project by GID (sync).

        Args:
            project_gid: Project GID
            raw: If True, return raw dict instead of Project model
            opt_fields: Optional fields to include

        Returns:
            Project model by default, or dict if raw=True
        """
        return self._get_sync(project_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Project | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(project_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(project_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def create_async(
        self,
        *,
        name: str,
        workspace: str,
        raw: Literal[False] = ...,
        team: str | None = ...,
        public: bool | None = ...,
        color: str | None = ...,
        default_view: str | None = ...,
        **kwargs: Any,
    ) -> Project:
        """Overload: create, returning Project model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        name: str,
        workspace: str,
        raw: Literal[True],
        team: str | None = ...,
        public: bool | None = ...,
        color: str | None = ...,
        default_view: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: create, returning raw dict."""
        ...

    @error_handler
    async def create_async(
        self,
        *,
        name: str,
        workspace: str,
        raw: bool = False,
        team: str | None = None,
        public: bool | None = None,
        color: str | None = None,
        default_view: str | None = None,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Create a new project.

        Args:
            name: Project name (required)
            workspace: Workspace GID (required)
            raw: If True, return raw dict instead of Project model
            team: Team GID (for organization workspaces)
            public: Whether the project is public
            color: Project color
            default_view: Default view (list, board, calendar, timeline)
            **kwargs: Additional project fields

        Returns:
            Project model by default, or dict if raw=True
        """

        data: dict[str, Any] = {"name": name, "workspace": workspace}

        if team is not None:
            data["team"] = team
        if public is not None:
            data["public"] = public
        if color is not None:
            data["color"] = color
        if default_view is not None:
            data["default_view"] = default_view

        data.update(kwargs)

        result = await self._http.post("/projects", json={"data": data})
        if raw:
            return result
        return Project.model_validate(result)

    @overload
    def create(
        self,
        *,
        name: str,
        workspace: str,
        raw: Literal[False] = ...,
        team: str | None = ...,
        public: bool | None = ...,
        color: str | None = ...,
        default_view: str | None = ...,
        **kwargs: Any,
    ) -> Project:
        """Overload: create (sync), returning Project model."""
        ...

    @overload
    def create(
        self,
        *,
        name: str,
        workspace: str,
        raw: Literal[True],
        team: str | None = ...,
        public: bool | None = ...,
        color: str | None = ...,
        default_view: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: create (sync), returning raw dict."""
        ...

    def create(
        self,
        *,
        name: str,
        workspace: str,
        raw: bool = False,
        team: str | None = None,
        public: bool | None = None,
        color: str | None = None,
        default_view: str | None = None,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Create a new project (sync).

        Args:
            name: Project name (required)
            workspace: Workspace GID (required)
            raw: If True, return raw dict instead of Project model
            team: Team GID (for organization workspaces)
            public: Whether the project is public
            color: Project color
            default_view: Default view (list, board, calendar, timeline)
            **kwargs: Additional project fields

        Returns:
            Project model by default, or dict if raw=True
        """
        return self._create_sync(
            name=name,
            workspace=workspace,
            raw=raw,
            team=team,
            public=public,
            color=color,
            default_view=default_view,
            **kwargs,
        )

    @sync_wrapper("create_async")
    async def _create_sync(
        self,
        *,
        name: str,
        workspace: str,
        raw: bool = False,
        team: str | None = None,
        public: bool | None = None,
        color: str | None = None,
        default_view: str | None = None,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_async(
                name=name,
                workspace=workspace,
                raw=True,
                team=team,
                public=public,
                color=color,
                default_view=default_view,
                **kwargs,
            )
        return await self.create_async(
            name=name,
            workspace=workspace,
            raw=False,
            team=team,
            public=public,
            color=color,
            default_view=default_view,
            **kwargs,
        )

    @overload
    async def update_async(
        self,
        project_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Project:
        """Overload: update, returning Project model."""
        ...

    @overload
    async def update_async(
        self,
        project_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

    @error_handler
    async def update_async(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Update a project.

        Args:
            project_gid: Project GID
            raw: If True, return raw dict instead of Project model
            **kwargs: Fields to update

        Returns:
            Project model by default, or dict if raw=True
        """
        result = await self._http.put(f"/projects/{project_gid}", json={"data": kwargs})
        if raw:
            return result
        return Project.model_validate(result)

    @overload
    def update(
        self,
        project_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Project:
        """Overload: update (sync), returning Project model."""
        ...

    @overload
    def update(
        self,
        project_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    def update(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Update a project (sync).

        Args:
            project_gid: Project GID
            raw: If True, return raw dict instead of Project model
            **kwargs: Fields to update

        Returns:
            Project model by default, or dict if raw=True
        """
        return self._update_sync(project_gid, raw=raw, **kwargs)

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_async(project_gid, raw=True, **kwargs)
        return await self.update_async(project_gid, raw=False, **kwargs)

    @error_handler
    async def delete_async(self, project_gid: str) -> None:
        """Delete a project.

        Args:
            project_gid: Project GID
        """
        await self._http.delete(f"/projects/{project_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, project_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(project_gid)

    def delete(self, project_gid: str) -> None:
        """Delete a project (sync).

        Args:
            project_gid: Project GID
        """
        self._delete_sync(project_gid)

    def list_async(
        self,
        *,
        workspace: str | None = None,
        team: str | None = None,
        archived: bool | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Project]:
        """List projects with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            workspace: Filter by workspace GID
            team: Filter by team GID
            archived: Filter by archived status
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Project] - async iterator over Project objects

        Example:
            async for project in client.projects.list_async(workspace="123"):
                print(project.name)
        """
        self._log_operation("list_async")

        async def fetch_page(offset: str | None) -> tuple[list[Project], str | None]:
            """Fetch a single page of Project objects."""
            params = self._build_opt_fields(opt_fields)
            if workspace:
                params["workspace"] = workspace
            if team:
                params["team"] = team
            if archived is not None:
                params["archived"] = archived
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                "/projects", params=params
            )
            projects = [Project.model_validate(p) for p in data]
            return projects, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Membership Operations ---

    @overload
    async def add_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Project:
        """Overload: add members, returning Project model."""
        ...

    @overload
    async def add_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add members, returning raw dict."""
        ...

    @error_handler
    async def add_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Project | dict[str, Any]:
        """Add members to a project.

        Args:
            project_gid: Project GID
            members: List of user GIDs to add
            raw: If True, return raw dict instead of Project model

        Returns:
            Updated project
        """
        result = await self._http.post(
            f"/projects/{project_gid}/addMembers",
            json={"data": {"members": ",".join(members)}},
        )
        if raw:
            return result
        return Project.model_validate(result)

    @overload
    def add_members(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Project:
        """Overload: add members (sync), returning Project model."""
        ...

    @overload
    def add_members(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: add members (sync), returning raw dict."""
        ...

    def add_members(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Project | dict[str, Any]:
        """Add members to a project (sync).

        Args:
            project_gid: Project GID
            members: List of user GIDs to add
            raw: If True, return raw dict instead of Project model

        Returns:
            Updated project
        """
        return self._add_members_sync(project_gid, members=members, raw=raw)

    @sync_wrapper("add_members_async")
    async def _add_members_sync(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Project | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.add_members_async(project_gid, members=members, raw=True)
        return await self.add_members_async(project_gid, members=members, raw=False)

    @overload
    async def remove_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Project:
        """Overload: remove members, returning Project model."""
        ...

    @overload
    async def remove_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: remove members, returning raw dict."""
        ...

    @error_handler
    async def remove_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Project | dict[str, Any]:
        """Remove members from a project.

        Args:
            project_gid: Project GID
            members: List of user GIDs to remove
            raw: If True, return raw dict instead of Project model

        Returns:
            Updated project
        """
        result = await self._http.post(
            f"/projects/{project_gid}/removeMembers",
            json={"data": {"members": ",".join(members)}},
        )
        if raw:
            return result
        return Project.model_validate(result)

    @overload
    def remove_members(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[False] = ...,
    ) -> Project:
        """Overload: remove members (sync), returning Project model."""
        ...

    @overload
    def remove_members(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: remove members (sync), returning raw dict."""
        ...

    def remove_members(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Project | dict[str, Any]:
        """Remove members from a project (sync).

        Args:
            project_gid: Project GID
            members: List of user GIDs to remove
            raw: If True, return raw dict instead of Project model

        Returns:
            Updated project
        """
        return self._remove_members_sync(project_gid, members=members, raw=raw)

    @sync_wrapper("remove_members_async")
    async def _remove_members_sync(
        self,
        project_gid: str,
        *,
        members: list[str],
        raw: bool = False,
    ) -> Project | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.remove_members_async(
                project_gid, members=members, raw=True
            )
        return await self.remove_members_async(project_gid, members=members, raw=False)

    # --- Section-related convenience ---

    def get_sections_async(
        self,
        project_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Section]:
        """Get sections in a project (convenience method).

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            project_gid: Project GID
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Section] - async iterator over Section objects

        Example:
            async for section in client.projects.get_sections_async("123"):
                print(section.name)
        """
        self._log_operation("get_sections_async", project_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Section], str | None]:
            """Fetch a single page of Section objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/projects/{project_gid}/sections", params=params
            )
            sections = [Section.model_validate(s) for s in data]
            return sections, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))
