"""Sections client - returns typed Section models by default.

Per TDD-0003: SectionsClient provides CRUD and task movement operations.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.section import Section
from autom8_asana.observability import error_handler
from autom8_asana.transport.sync import sync_wrapper


class SectionsClient(BaseClient):
    """Client for Asana Section operations.

    Returns typed Section models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    @overload
    async def get_async(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Section:
        """Overload: get, returning Section model."""
        ...

    @overload
    async def get_async(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    @error_handler
    async def get_async(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Section | dict[str, Any]:
        """Get a section by GID.

        Args:
            section_gid: Section GID
            raw: If True, return raw dict instead of Section model
            opt_fields: Optional fields to include

        Returns:
            Section model by default, or dict if raw=True
        """
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/sections/{section_gid}", params=params)
        if raw:
            return data
        return Section.model_validate(data)

    @overload
    def get(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Section:
        """Overload: get (sync), returning Section model."""
        ...

    @overload
    def get(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Section | dict[str, Any]:
        """Get a section by GID (sync).

        Args:
            section_gid: Section GID
            raw: If True, return raw dict instead of Section model
            opt_fields: Optional fields to include

        Returns:
            Section model by default, or dict if raw=True
        """
        return self._get_sync(section_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Section | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(section_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(section_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def create_async(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[False] = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> Section:
        """Overload: create, returning Section model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[True],
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: create, returning raw dict."""
        ...

    @error_handler
    async def create_async(
        self,
        *,
        name: str,
        project: str,
        raw: bool = False,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Section | dict[str, Any]:
        """Create a new section in a project.

        Args:
            name: Section name (required)
            project: Project GID to create section in (required)
            raw: If True, return raw dict instead of Section model
            insert_before: Section GID to insert before
            insert_after: Section GID to insert after

        Returns:
            Section model by default, or dict if raw=True
        """

        data: dict[str, Any] = {"name": name}

        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        result = await self._http.post(
            f"/projects/{project}/sections", json={"data": data}
        )
        if raw:
            return result
        return Section.model_validate(result)

    @overload
    def create(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[False] = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> Section:
        """Overload: create (sync), returning Section model."""
        ...

    @overload
    def create(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[True],
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: create (sync), returning raw dict."""
        ...

    def create(
        self,
        *,
        name: str,
        project: str,
        raw: bool = False,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Section | dict[str, Any]:
        """Create a new section in a project (sync).

        Args:
            name: Section name (required)
            project: Project GID to create section in (required)
            raw: If True, return raw dict instead of Section model
            insert_before: Section GID to insert before
            insert_after: Section GID to insert after

        Returns:
            Section model by default, or dict if raw=True
        """
        return self._create_sync(
            name=name,
            project=project,
            raw=raw,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    @sync_wrapper("create_async")
    async def _create_sync(
        self,
        *,
        name: str,
        project: str,
        raw: bool = False,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Section | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_async(
                name=name,
                project=project,
                raw=True,
                insert_before=insert_before,
                insert_after=insert_after,
            )
        return await self.create_async(
            name=name,
            project=project,
            raw=False,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    @overload
    async def update_async(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Section:
        """Overload: update, returning Section model."""
        ...

    @overload
    async def update_async(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

    @error_handler
    async def update_async(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Section | dict[str, Any]:
        """Update a section (rename).

        Args:
            section_gid: Section GID
            raw: If True, return raw dict instead of Section model
            **kwargs: Fields to update (typically just 'name')

        Returns:
            Section model by default, or dict if raw=True
        """
        result = await self._http.put(f"/sections/{section_gid}", json={"data": kwargs})
        if raw:
            return result
        return Section.model_validate(result)

    @overload
    def update(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Section:
        """Overload: update (sync), returning Section model."""
        ...

    @overload
    def update(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    def update(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Section | dict[str, Any]:
        """Update a section (sync).

        Args:
            section_gid: Section GID
            raw: If True, return raw dict instead of Section model
            **kwargs: Fields to update (typically just 'name')

        Returns:
            Section model by default, or dict if raw=True
        """
        return self._update_sync(section_gid, raw=raw, **kwargs)

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Section | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_async(section_gid, raw=True, **kwargs)
        return await self.update_async(section_gid, raw=False, **kwargs)

    @error_handler
    async def delete_async(self, section_gid: str) -> None:
        """Delete a section.

        Args:
            section_gid: Section GID
        """
        await self._http.delete(f"/sections/{section_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, section_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(section_gid)

    def delete(self, section_gid: str) -> None:
        """Delete a section (sync).

        Args:
            section_gid: Section GID
        """
        self._delete_sync(section_gid)

    def list_for_project_async(
        self,
        project_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Section]:
        """List sections in a project with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            project_gid: Project GID
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Section] - async iterator over Section objects

        Example:
            async for section in client.sections.list_for_project_async("123"):
                print(section.name)
        """
        self._log_operation("list_for_project_async", project_gid)

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

    # --- Task Movement Operations ---

    @error_handler
    async def add_task_async(
        self,
        section_gid: str,
        *,
        task: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a task to a section.

        Moves the task to the specified section. If the task is already
        in another section of the same project, it will be moved.

        Args:
            section_gid: Section GID to add task to
            task: Task GID to add
            insert_before: Task GID to insert before
            insert_after: Task GID to insert after
        """

        data: dict[str, Any] = {"task": task}
        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        await self._http.post(f"/sections/{section_gid}/addTask", json={"data": data})

    @sync_wrapper("add_task_async")
    async def _add_task_sync(
        self,
        section_gid: str,
        *,
        task: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.add_task_async(
            section_gid,
            task=task,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    def add_task(
        self,
        section_gid: str,
        *,
        task: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a task to a section (sync).

        Moves the task to the specified section. If the task is already
        in another section of the same project, it will be moved.

        Args:
            section_gid: Section GID to add task to
            task: Task GID to add
            insert_before: Task GID to insert before
            insert_after: Task GID to insert after
        """
        self._add_task_sync(
            section_gid,
            task=task,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    @error_handler
    async def insert_section_async(
        self,
        project_gid: str,
        *,
        section: str,
        before_section: str | None = None,
        after_section: str | None = None,
    ) -> None:
        """Reorder a section within a project.

        Args:
            project_gid: Project GID
            section: Section GID to move
            before_section: Section GID to insert before
            after_section: Section GID to insert after
        """

        data: dict[str, Any] = {"section": section}
        if before_section is not None:
            data["before_section"] = before_section
        if after_section is not None:
            data["after_section"] = after_section

        await self._http.post(
            f"/projects/{project_gid}/sections/insert", json={"data": data}
        )

    @sync_wrapper("insert_section_async")
    async def _insert_section_sync(
        self,
        project_gid: str,
        *,
        section: str,
        before_section: str | None = None,
        after_section: str | None = None,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.insert_section_async(
            project_gid,
            section=section,
            before_section=before_section,
            after_section=after_section,
        )

    def insert_section(
        self,
        project_gid: str,
        *,
        section: str,
        before_section: str | None = None,
        after_section: str | None = None,
    ) -> None:
        """Reorder a section within a project (sync).

        Args:
            project_gid: Project GID
            section: Section GID to move
            before_section: Section GID to insert before
            after_section: Section GID to insert after
        """
        self._insert_section_sync(
            project_gid,
            section=section,
            before_section=before_section,
            after_section=after_section,
        )
