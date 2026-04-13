"""Sections client - returns typed Section models by default.

Per TDD-0003: SectionsClient provides CRUD and task movement operations.
Per TDD-DESIGN-PATTERNS-D: Uses @async_method for async/sync method generation.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any, Literal, overload

from autom8y_log import get_logger

from autom8_asana.clients.base import BaseClient
from autom8_asana.core.errors import CacheError
from autom8_asana.models import PageIterator
from autom8_asana.models.section import Section
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method
from autom8_asana.settings import get_settings

logger = get_logger(__name__)


class SectionsClient(BaseClient):
    """Client for Asana Section operations.

    Returns typed Section models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    # Type overloads for get (required for IDE/mypy support with raw parameter)
    # Note: @async_method provides the implementation; mypy errors are expected
    # because mypy cannot see runtime-generated implementations.
    @overload  # type: ignore[no-overload-impl]
    async def get_async(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Section:
        """Get a section by GID, returning a Section model."""
        ...

    @overload
    async def get_async(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Get a section by GID, returning a raw dict."""
        ...

    @overload
    def get(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Section:
        """Get a section by GID (sync), returning a Section model."""
        ...

    @overload
    def get(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Get a section by GID (sync), returning a raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def get(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Section | dict[str, Any]:
        """Get a section by GID with cache support.

        Per TDD-CACHE-UTILIZATION: Checks cache before HTTP request.
        Per ADR-0119: 6-step client cache integration pattern.

        Args:
            section_gid: Section GID
            raw: If True, return raw dict instead of Section model
            opt_fields: Optional fields to include

        Returns:
            Section model by default, or dict if raw=True

        Raises:
            GidValidationError: If section_gid is invalid.
        """
        from autom8_asana.cache.models.entry import EntryType
        from autom8_asana.persistence.validation import validate_gid

        # Step 1: Validate GID
        validate_gid(section_gid, "section_gid")

        # Step 2: Check cache first
        cached_entry = self._cache_get(section_gid, EntryType.SECTION)
        if cached_entry is not None:
            # Step 3: Cache hit - return cached data
            data = cached_entry.data
            if raw:
                return data
            return Section.model_validate(data)

        # Step 4: Cache miss - fetch from API
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/sections/{section_gid}", params=params)

        # Step 5: Store in cache (30 min TTL, no modified_at available)
        cache_ttl = get_settings().cache.ttl_section
        self._cache_set(section_gid, data, EntryType.SECTION, ttl=cache_ttl)

        # Step 6: Return model or raw dict
        if raw:
            return data
        return Section.model_validate(data)

    # Type overloads for create
    @overload  # type: ignore[no-overload-impl]
    async def create_async(
        self,
        *,
        name: str,
        project: str,
        raw: Literal[False] = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> Section:
        """Create a new section, returning a Section model."""
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
        """Create a new section, returning a raw dict."""
        ...

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
        """Create a new section (sync), returning a Section model."""
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
        """Create a new section (sync), returning a raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
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
    @overload  # type: ignore[no-overload-impl]
    async def update_async(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Section:
        """Update a section, returning a Section model."""
        ...

    @overload
    async def update_async(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a section, returning a raw dict."""
        ...

    @overload
    def update(
        self,
        section_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Section:
        """Update a section (sync), returning a Section model."""
        ...

    @overload
    def update(
        self,
        section_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a section (sync), returning a raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
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

    @async_method  # type: ignore[arg-type]
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
        """List sections in a project with automatic pagination and cache population.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Per TDD-CACHE-UTILIZATION and ADR-0120: Populates cache entries for each
        section during pagination using set_batch() for opportunistic warming.

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
        from datetime import datetime

        from autom8_asana.cache.models.entry import CacheEntry, EntryType

        self._log_operation("list_for_project_async", project_gid)

        # Capture cache reference for closure
        cache = self._cache

        async def fetch_page(offset: str | None) -> tuple[list[Section], str | None]:
            """Fetch a single page of Section objects with cache population."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/projects/{project_gid}/sections", params=params
            )

            # Per ADR-0120: Batch populate cache during pagination
            if cache is not None and data:
                try:
                    entries: dict[str, CacheEntry] = {}
                    now = datetime.now(UTC)
                    cache_ttl = get_settings().cache.ttl_section
                    for section_data in data:
                        gid = section_data.get("gid")
                        if gid:
                            entry = CacheEntry(
                                key=gid,
                                data=section_data,
                                entry_type=EntryType.SECTION,
                                version=now,  # No modified_at for sections
                                ttl=cache_ttl,
                            )
                            entries[gid] = entry
                    if entries:
                        cache.set_batch(entries)
                except (
                    ConnectionError,
                    TimeoutError,
                    OSError,
                    ValueError,
                    TypeError,
                    CacheError,
                ):
                    # Per ADR-0127: Graceful degradation - log and continue
                    logger.warning("Section cache degradation", exc_info=True)

            sections = [Section.model_validate(s) for s in data]
            return sections, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Task Movement Operations ---

    @async_method  # type: ignore[arg-type]
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

    @async_method  # type: ignore[arg-type]
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
