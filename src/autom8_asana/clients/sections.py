"""Sections client - returns typed Section models by default.

Per TDD-0003: SectionsClient provides CRUD and task movement operations.
Per TDD-DESIGN-PATTERNS-D: Uses @async_method for async/sync method generation.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.section import Section
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method


class SectionsClient(BaseClient):
    """Client for Asana Section operations.

    Returns typed Section models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    # Type overloads for get (required for IDE/mypy support with raw parameter)
    # Note: @async_method provides the implementation; mypy errors are expected
    # because mypy cannot see runtime-generated implementations.
    @overload
    async def get_async(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Section: ...

    @overload
    async def get_async(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]: ...

    @overload
    def get(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Section: ...

    @overload
    def get(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]: ...

    @async_method
    @error_handler
    async def get(
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

    # Type overloads for create
    @overload
    async def create_async(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[False] = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> Section: ...

    @overload
    async def create_async(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[True],
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]: ...

    @overload
    def create(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[False] = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> Section: ...

    @overload
    def create(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[True],
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]: ...

    @async_method
    @error_handler
    async def create(
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

    # Type overloads for update
    @overload
    async def update_async(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Section: ...

    @overload
    async def update_async(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    @overload
    def update(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Section: ...

    @overload
    def update(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    @async_method
    @error_handler
    async def update(
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

    @async_method
    @error_handler
    async def delete(self, section_gid: str) -> None:
        """Delete a section.

        Args:
            section_gid: Section GID
        """
        await self._http.delete(f"/sections/{section_gid}")

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

    @async_method
    @error_handler
    async def add_task(
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

    @async_method
    @error_handler
    async def insert_section(
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
