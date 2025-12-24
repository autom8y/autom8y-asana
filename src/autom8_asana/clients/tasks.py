"""Tasks client - returns typed Task models by default.

Phase 3.2: Updated to return Pydantic Task models.
Use raw=True for backward-compatible dict returns.
Per TDD-0002: list_async() returns PageIterator[Task] for automatic pagination.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, overload

from autom8_asana.clients.base import BaseClient

logger = logging.getLogger(__name__)
from autom8_asana.models import PageIterator, Task
from autom8_asana.models.business.fields import STANDARD_TASK_OPT_FIELDS
from autom8_asana.observability import error_handler
from autom8_asana.persistence.session import SaveSession
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient


class TasksClient(BaseClient):
    """Client for Asana Task operations.

    Returns typed Task models by default. Use raw=True for dict returns.

    P1 Direct Methods (P1):
        - add_tag_async() / add_tag()
        - remove_tag_async() / remove_tag()
        - move_to_section_async() / move_to_section()
        - set_assignee_async() / set_assignee()
        - add_to_project_async() / add_to_project()
        - remove_from_project_async() / remove_from_project()
    """

    def __init__(
        self,
        http: Any,
        config: Any,
        auth_provider: Any,
        cache_provider: Any | None = None,
        log_provider: Any | None = None,
        client: AsanaClient | None = None,
    ) -> None:
        """Initialize TasksClient.

        Args:
            http: HTTP client
            config: SDK configuration
            auth_provider: Authentication provider
            cache_provider: Optional cache provider
            log_provider: Optional log provider
            client: Full AsanaClient instance (for SaveSession support)
        """
        super().__init__(
            http=http,
            config=config,
            auth_provider=auth_provider,
            cache_provider=cache_provider,
            log_provider=log_provider,
        )
        self._client = client

    @overload
    async def get_async(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Task:
        """Get a task by GID, returning a Task model."""
        ...

    @overload
    async def get_async(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Get a task by GID, returning a raw dict."""
        ...

    @error_handler
    async def get_async(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Task | dict[str, Any]:
        """Get a task by GID with cache support.

        Per FR-CLIENT-001: Checks cache before HTTP request.
        Per FR-CLIENT-002: Uses task GID as cache key with EntryType.TASK.
        Per FR-CLIENT-004: Respects TTL expiration.
        Per FR-CLIENT-007: raw=True returns cached dict directly.

        Args:
            task_gid: Task GID
            raw: If True, return raw dict instead of Task model
            opt_fields: Optional fields to include

        Returns:
            Task model by default, or dict if raw=True

        Raises:
            ValidationError: If task_gid is invalid.
        """
        from autom8_asana.cache.entry import EntryType
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")

        # FR-CLIENT-001: Check cache first
        cached_entry = self._cache_get(task_gid, EntryType.TASK)
        if cached_entry is not None:
            # Per NFR-OBS-001: Log cache hit at DEBUG level
            logger.debug(
                "Cache hit for task",
                extra={"task_gid": task_gid},
            )
            data = cached_entry.data
            if raw:
                return data
            task = Task.model_validate(data)
            task._client = self._client
            return task

        # Per NFR-OBS-001: Log cache miss at DEBUG level
        opt_fields_count = len(opt_fields) if opt_fields else 0
        logger.debug(
            "Cache miss for task",
            extra={"task_gid": task_gid, "opt_fields_count": opt_fields_count},
        )

        # Cache miss: fetch from API
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/tasks/{task_gid}", params=params)

        # Store in cache with entity-type TTL
        ttl = self._resolve_entity_ttl(data)
        self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)

        if raw:
            return data
        task = Task.model_validate(data)
        task._client = self._client  # Store client reference for save/refresh
        return task

    def _resolve_entity_ttl(self, data: dict[str, Any]) -> int:
        """Resolve TTL based on entity type detection.

        Per FR-TTL-001 through FR-TTL-007: Different TTLs for
        Business (3600s), Contact/Unit (900s), Offer (180s),
        Process (60s), and generic tasks (300s).

        Priority:
        1. CacheConfig.get_entity_ttl() if CacheConfig is available
        2. Detection-based defaults (hardcoded fallback)
        3. 300s default for unknown entity types

        Args:
            data: Task data dict from API.

        Returns:
            TTL in seconds.
        """
        # Try to detect entity type from data
        entity_type = self._detect_entity_type(data)

        # Priority 1: Use CacheConfig.get_entity_ttl() if available (FR-TTL-006)
        if hasattr(self._config, "cache") and self._config.cache is not None:
            cache_config = self._config.cache
            if hasattr(cache_config, "get_entity_ttl"):
                if entity_type:
                    return cache_config.get_entity_ttl(entity_type)
                # No entity type detected - use default TTL
                if hasattr(cache_config, "ttl") and cache_config._ttl is not None:
                    return cache_config.ttl.default_ttl
                return 300

        # Priority 2: Fallback to hardcoded defaults (when CacheConfig unavailable)
        entity_ttls = {
            "business": 3600,
            "contact": 900,
            "unit": 900,
            "offer": 180,
            "process": 60,
            "address": 3600,
            "hours": 3600,
        }

        if entity_type and entity_type.lower() in entity_ttls:
            return entity_ttls[entity_type.lower()]

        # FR-TTL-005: Default TTL for generic tasks
        return 300

    def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
        """Detect entity type from task data.

        Uses existing detection infrastructure if available.

        Args:
            data: Task data dict.

        Returns:
            Entity type name or None if not detectable.
        """
        try:
            from autom8_asana.models.business.detection import detect_entity_type
            from autom8_asana.models import Task as TaskModel

            # Create a temporary Task model to use detection
            temp_task = TaskModel.model_validate(data)
            result = detect_entity_type(temp_task)
            if result and result.entity_type:
                return result.entity_type.value
            return None
        except ImportError:
            # Detection module not available
            return None
        except Exception:
            # Detection failed, use default
            return None

    @overload
    def get(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Task:
        """Get a task by GID (sync), returning a Task model."""
        ...

    @overload
    def get(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Get a task by GID (sync), returning a raw dict."""
        ...

    def get(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Task | dict[str, Any]:
        """Get a task by GID (sync).

        Args:
            task_gid: Task GID
            raw: If True, return raw dict instead of Task model
            opt_fields: Optional fields to include

        Returns:
            Task model by default, or dict if raw=True
        """
        return self._get_sync(task_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Task | dict[str, Any]:
        """Internal sync wrapper implementation."""
        # Use conditionals to satisfy mypy's overload requirements
        if raw:
            return await self.get_async(task_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(task_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def create_async(
        self,
        *,
        name: str,
        raw: Literal[False] = ...,
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> Task:
        """Create a new task, returning a Task model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        name: str,
        raw: Literal[True],
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a new task, returning a raw dict."""
        ...

    @error_handler
    async def create_async(
        self,
        *,
        name: str,
        raw: bool = False,
        workspace: str | None = None,
        projects: list[str] | None = None,
        parent: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Create a new task.

        Args:
            name: Task name (required)
            raw: If True, return raw dict instead of Task model
            workspace: Workspace GID (required if no projects/parent)
            projects: List of project GIDs to add task to
            parent: Parent task GID (for subtasks)
            notes: Task description
            **kwargs: Additional task fields

        Returns:
            Task model by default, or dict if raw=True
        """

        data: dict[str, Any] = {"name": name}

        if workspace:
            data["workspace"] = workspace
        if projects:
            data["projects"] = projects
        if parent:
            data["parent"] = parent
        if notes:
            data["notes"] = notes

        data.update(kwargs)

        result = await self._http.post("/tasks", json={"data": data})
        if raw:
            return result
        task = Task.model_validate(result)
        task._client = self._client  # Store client reference for save/refresh
        return task

    @overload
    def create(
        self,
        *,
        name: str,
        raw: Literal[False] = ...,
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> Task:
        """Create a new task (sync), returning a Task model."""
        ...

    @overload
    def create(
        self,
        *,
        name: str,
        raw: Literal[True],
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a new task (sync), returning a raw dict."""
        ...

    def create(
        self,
        *,
        name: str,
        raw: bool = False,
        workspace: str | None = None,
        projects: list[str] | None = None,
        parent: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Create a new task (sync).

        Args:
            name: Task name (required)
            raw: If True, return raw dict instead of Task model
            workspace: Workspace GID (required if no projects/parent)
            projects: List of project GIDs to add task to
            parent: Parent task GID (for subtasks)
            notes: Task description
            **kwargs: Additional task fields

        Returns:
            Task model by default, or dict if raw=True
        """
        return self._create_sync(
            name=name,
            raw=raw,
            workspace=workspace,
            projects=projects,
            parent=parent,
            notes=notes,
            **kwargs,
        )

    @sync_wrapper("create_async")
    async def _create_sync(
        self,
        *,
        name: str,
        raw: bool = False,
        workspace: str | None = None,
        projects: list[str] | None = None,
        parent: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Internal sync wrapper implementation."""
        # Use conditionals to satisfy mypy's overload requirements
        if raw:
            return await self.create_async(
                name=name,
                raw=True,
                workspace=workspace,
                projects=projects,
                parent=parent,
                notes=notes,
                **kwargs,
            )
        return await self.create_async(
            name=name,
            raw=False,
            workspace=workspace,
            projects=projects,
            parent=parent,
            notes=notes,
            **kwargs,
        )

    @overload
    async def update_async(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Task:
        """Update a task, returning a Task model."""
        ...

    @overload
    async def update_async(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a task, returning a raw dict."""
        ...

    @error_handler
    async def update_async(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Update a task.

        Args:
            task_gid: Task GID
            raw: If True, return raw dict instead of Task model
            **kwargs: Fields to update

        Returns:
            Task model by default, or dict if raw=True
        """
        result = await self._http.put(f"/tasks/{task_gid}", json={"data": kwargs})
        if raw:
            return result
        task = Task.model_validate(result)
        task._client = self._client  # Store client reference for save/refresh
        return task

    @overload
    def update(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Task:
        """Update a task (sync), returning a Task model."""
        ...

    @overload
    def update(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a task (sync), returning a raw dict."""
        ...

    def update(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Update a task (sync).

        Args:
            task_gid: Task GID
            raw: If True, return raw dict instead of Task model
            **kwargs: Fields to update

        Returns:
            Task model by default, or dict if raw=True
        """
        return self._update_sync(task_gid, raw=raw, **kwargs)

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Internal sync wrapper implementation."""
        # Use conditionals to satisfy mypy's overload requirements
        if raw:
            return await self.update_async(task_gid, raw=True, **kwargs)
        return await self.update_async(task_gid, raw=False, **kwargs)

    @error_handler
    async def delete_async(self, task_gid: str) -> None:
        """Delete a task.

        Args:
            task_gid: Task GID
        """
        await self._http.delete(f"/tasks/{task_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, task_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(task_gid)

    def delete(self, task_gid: str) -> None:
        """Delete a task (sync).

        Args:
            task_gid: Task GID
        """
        self._delete_sync(task_gid)

    def list_async(
        self,
        *,
        project: str | None = None,
        section: str | None = None,
        assignee: str | None = None,
        workspace: str | None = None,
        completed_since: str | None = None,
        modified_since: str | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Task]:
        """List tasks with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            project: Filter by project GID
            section: Filter by section GID
            assignee: Filter by assignee GID (use "me" for current user)
            workspace: Filter by workspace GID (required if no project/section)
            completed_since: ISO 8601 datetime; include completed tasks modified since
            modified_since: ISO 8601 datetime; only tasks modified since
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Task] - async iterator over Task objects

        Example:
            # Iterate all tasks
            async for task in client.tasks.list_async(project="123"):
                print(task.name)

            # Get first 10
            tasks = await client.tasks.list_async(project="123").take(10)

            # Collect all
            all_tasks = await client.tasks.list_async(project="123").collect()
        """
        self._log_operation("list_async")

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            """Fetch a single page of tasks."""
            params = self._build_opt_fields(opt_fields)
            if project:
                params["project"] = project
            if section:
                params["section"] = section
            if assignee:
                params["assignee"] = assignee
            if workspace:
                params["workspace"] = workspace
            if completed_since:
                params["completed_since"] = completed_since
            if modified_since:
                params["modified_since"] = modified_since
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated("/tasks", params=params)
            tasks = [Task.model_validate(t) for t in data]
            return tasks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # Default fields needed for entity type detection and field cascading
    # Per PRD-CACHE-PERF-HYDRATION FR-CACHE-001, FR-CACHE-002:
    # Use STANDARD_TASK_OPT_FIELDS to ensure parent.gid and people_value are present.
    # This enables upward traversal and Owner cascading from cached tasks.
    # Per ADR-0101: Include project.name for ProcessType detection via project name matching.
    # Per TDD-HYDRATION: Include custom_fields for field cascading (Vertical, Products, etc.)
    _DETECTION_FIELDS: list[str] = list(STANDARD_TASK_OPT_FIELDS)

    def subtasks_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        include_detection_fields: bool = False,
        limit: int = 100,
    ) -> PageIterator[Task]:
        """List subtasks of a task with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Per ADR-0057: Provides async iteration over subtasks of a parent task.

        Args:
            task_gid: GID of the parent task
            opt_fields: Fields to include in response
            include_detection_fields: If True, automatically include fields needed
                for entity type detection and field cascading:
                - Detection: memberships.project.gid, memberships.project.name, name
                - Custom fields: custom_fields with all subfields for cascading
                This is useful when hydrating holders to enable detection-based
                identification, ProcessType detection via project name matching,
                and access to cascading fields (Vertical, Products, etc.).
                Default is False to maintain backward compatibility.
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Task] - async iterator over Task objects

        Example:
            # Iterate all subtasks
            async for subtask in client.tasks.subtasks_async("parent_gid"):
                print(subtask.name)

            # Collect all subtasks
            all_subtasks = await client.tasks.subtasks_async("parent_gid").collect()

            # With detection fields for holder identification
            subtasks = await client.tasks.subtasks_async(
                "parent_gid", include_detection_fields=True
            ).collect()
        """
        self._log_operation("subtasks_async")

        # Merge detection fields if requested
        effective_opt_fields = opt_fields
        if include_detection_fields:
            detection_fields = set(self._DETECTION_FIELDS)
            if opt_fields:
                # Merge, avoiding duplicates
                effective_opt_fields = list(set(opt_fields) | detection_fields)
            else:
                effective_opt_fields = list(detection_fields)

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            """Fetch a single page of subtasks."""
            params = self._build_opt_fields(effective_opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/subtasks",
                params=params,
            )
            tasks = [Task.model_validate(t) for t in data]
            return tasks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    def dependents_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Task]:
        """List dependent tasks (tasks that depend on this task) with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Per FR-PREREQ-003: Follows subtasks_async() pattern for fetching dependents.

        A dependent task is one that depends on this task to be completed first
        (i.e., this task is a blocker/dependency of the returned tasks).
        Note: Asana limits combined dependents+dependencies to 30 per task.

        Args:
            task_gid: GID of the task to get dependents for.
            opt_fields: Fields to include in response.
            limit: Number of items per page (default 100, max 100).

        Returns:
            PageIterator[Task] - async iterator over Task objects.

        Example:
            # Iterate all dependents
            async for dependent in client.tasks.dependents_async("task_gid"):
                print(f"Task {dependent.name} depends on this task")

            # Collect all dependents
            all_dependents = await client.tasks.dependents_async("task_gid").collect()
        """
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        self._log_operation("dependents_async")

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            """Fetch a single page of dependents."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/dependents",
                params=params,
            )
            tasks = [Task.model_validate(t) for t in data]
            return tasks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- P1 Direct Methods: Convenience Wrappers ---
    # Per TDD-SDKUX §2C: Direct methods that wrap SaveSession internally
    # and return updated Task objects without requiring explicit session management.

    @error_handler
    async def add_tag_async(
        self, task_gid: str, tag_gid: str, *, refresh: bool = False
    ) -> Task:
        """Add tag to task without explicit SaveSession.

        Args:
            task_gid: Target task GID
            tag_gid: Tag GID to add
            refresh: If True, fetch fresh task state after commit. If False (default),
                     return the task fetched before commit. Note: the returned task
                     may not reflect the newly added tag relationship until refreshed.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or tag not found
            SaveSessionError: If the action operation fails
            ValidationError: If task_gid or tag_gid is invalid.

        Example:
            >>> # Default: single GET (faster, but task.tags may be stale)
            >>> task = await client.tasks.add_tag_async(task_gid, tag_gid)
            >>>
            >>> # With refresh: two GETs (slower, but task.tags is current)
            >>> task = await client.tasks.add_tag_async(task_gid, tag_gid, refresh=True)
        """
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(tag_gid, "tag_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self.get_async(task_gid)
            session.add_tag(task, tag_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        # Per TDD-TRIAGE-FIXES: Only refresh if explicitly requested
        if refresh:
            return await self.get_async(task_gid)
        return task

    def add_tag(self, task_gid: str, tag_gid: str, *, refresh: bool = False) -> Task:
        """Add tag to task without explicit SaveSession (sync).

        Args:
            task_gid: Target task GID
            tag_gid: Tag GID to add
            refresh: If True, fetch fresh task state after commit. Default False.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or tag not found
            SaveSessionError: If the action operation fails
        """
        return self._add_tag_sync(task_gid, tag_gid, refresh=refresh)

    @sync_wrapper("add_tag_async")
    async def _add_tag_sync(
        self, task_gid: str, tag_gid: str, *, refresh: bool = False
    ) -> Task:
        """Internal sync wrapper for add_tag_async."""
        return await self.add_tag_async(task_gid, tag_gid, refresh=refresh)

    @error_handler
    async def remove_tag_async(
        self, task_gid: str, tag_gid: str, *, refresh: bool = False
    ) -> Task:
        """Remove tag from task without explicit SaveSession.

        Args:
            task_gid: Target task GID
            tag_gid: Tag GID to remove
            refresh: If True, fetch fresh task state after commit. If False (default),
                     return the task fetched before commit.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or tag not found
            SaveSessionError: If the action operation fails
            ValidationError: If task_gid or tag_gid is invalid.

        Example:
            >>> task = await client.tasks.remove_tag_async(task_gid, tag_gid)
        """
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(tag_gid, "tag_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self.get_async(task_gid)
            session.remove_tag(task, tag_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self.get_async(task_gid)
        return task

    def remove_tag(self, task_gid: str, tag_gid: str, *, refresh: bool = False) -> Task:
        """Remove tag from task without explicit SaveSession (sync).

        Args:
            task_gid: Target task GID
            tag_gid: Tag GID to remove
            refresh: If True, fetch fresh task state after commit. Default False.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or tag not found
            SaveSessionError: If the action operation fails
        """
        return self._remove_tag_sync(task_gid, tag_gid, refresh=refresh)

    @sync_wrapper("remove_tag_async")
    async def _remove_tag_sync(
        self, task_gid: str, tag_gid: str, *, refresh: bool = False
    ) -> Task:
        """Internal sync wrapper for remove_tag_async."""
        return await self.remove_tag_async(task_gid, tag_gid, refresh=refresh)

    @error_handler
    async def move_to_section_async(
        self,
        task_gid: str,
        section_gid: str,
        project_gid: str,
        *,
        refresh: bool = False,
    ) -> Task:
        """Move task to section within project without explicit SaveSession.

        Args:
            task_gid: Target task GID
            section_gid: Section GID to move task to
            project_gid: Project GID (for validation/context)
            refresh: If True, fetch fresh task state after commit. If False (default),
                     return the task fetched before commit.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task, section, or project not found
            SaveSessionError: If the action operation fails
            ValidationError: If task_gid, section_gid, or project_gid is invalid.

        Example:
            >>> task = await client.tasks.move_to_section_async(
            ...     task_gid, section_gid, project_gid
            ... )
        """
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(section_gid, "section_gid")
        validate_gid(project_gid, "project_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self.get_async(task_gid)
            session.move_to_section(task, section_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self.get_async(task_gid)
        return task

    def move_to_section(
        self,
        task_gid: str,
        section_gid: str,
        project_gid: str,
        *,
        refresh: bool = False,
    ) -> Task:
        """Move task to section within project without explicit SaveSession (sync).

        Args:
            task_gid: Target task GID
            section_gid: Section GID to move task to
            project_gid: Project GID (for validation/context)
            refresh: If True, fetch fresh task state after commit. Default False.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task, section, or project not found
            SaveSessionError: If the action operation fails
        """
        return self._move_to_section_sync(
            task_gid, section_gid, project_gid, refresh=refresh
        )

    @sync_wrapper("move_to_section_async")
    async def _move_to_section_sync(
        self,
        task_gid: str,
        section_gid: str,
        project_gid: str,
        *,
        refresh: bool = False,
    ) -> Task:
        """Internal sync wrapper for move_to_section_async."""
        return await self.move_to_section_async(
            task_gid, section_gid, project_gid, refresh=refresh
        )

    @error_handler
    async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task:
        """Set task assignee without explicit SaveSession.

        Args:
            task_gid: Target task GID
            assignee_gid: Assignee user GID

        Returns:
            Updated Task from API

        Raises:
            APIError: If task or assignee not found
            ValidationError: If task_gid or assignee_gid is invalid.

        Example:
            >>> task = await client.tasks.set_assignee_async(task_gid, assignee_gid)
        """
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(assignee_gid, "assignee_gid")

        # Assignee is updated via the update endpoint, not SaveSession
        result = await self._http.put(
            f"/tasks/{task_gid}",
            json={"data": {"assignee": assignee_gid}},
        )
        task = Task.model_validate(result)
        return task

    def set_assignee(self, task_gid: str, assignee_gid: str) -> Task:
        """Set task assignee without explicit SaveSession (sync).

        Args:
            task_gid: Target task GID
            assignee_gid: Assignee user GID

        Returns:
            Updated Task from API

        Raises:
            APIError: If task or assignee not found
        """
        return self._set_assignee_sync(task_gid, assignee_gid)

    @sync_wrapper("set_assignee_async")
    async def _set_assignee_sync(self, task_gid: str, assignee_gid: str) -> Task:
        """Internal sync wrapper for set_assignee_async."""
        return await self.set_assignee_async(task_gid, assignee_gid)

    @error_handler
    async def add_to_project_async(
        self,
        task_gid: str,
        project_gid: str,
        section_gid: str | None = None,
        *,
        refresh: bool = False,
    ) -> Task:
        """Add task to project without explicit SaveSession.

        Args:
            task_gid: Target task GID
            project_gid: Project GID to add task to
            section_gid: Optional section GID within project
            refresh: If True, fetch fresh task state after commit. If False (default),
                     return the task fetched before commit.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or project not found
            SaveSessionError: If the action operation fails
            ValidationError: If task_gid or project_gid is invalid.

        Example:
            >>> task = await client.tasks.add_to_project_async(task_gid, project_gid)
            >>> # With section
            >>> task = await client.tasks.add_to_project_async(
            ...     task_gid, project_gid, section_gid=section_gid
            ... )
        """
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(project_gid, "project_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self.get_async(task_gid)
            session.add_to_project(task, project_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self.get_async(task_gid)
        return task

    def add_to_project(
        self,
        task_gid: str,
        project_gid: str,
        section_gid: str | None = None,
        *,
        refresh: bool = False,
    ) -> Task:
        """Add task to project without explicit SaveSession (sync).

        Args:
            task_gid: Target task GID
            project_gid: Project GID to add task to
            section_gid: Optional section GID within project
            refresh: If True, fetch fresh task state after commit. Default False.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or project not found
            SaveSessionError: If the action operation fails
        """
        return self._add_to_project_sync(
            task_gid, project_gid, section_gid, refresh=refresh
        )

    @sync_wrapper("add_to_project_async")
    async def _add_to_project_sync(
        self,
        task_gid: str,
        project_gid: str,
        section_gid: str | None = None,
        *,
        refresh: bool = False,
    ) -> Task:
        """Internal sync wrapper for add_to_project_async."""
        return await self.add_to_project_async(
            task_gid, project_gid, section_gid, refresh=refresh
        )

    @error_handler
    async def remove_from_project_async(
        self, task_gid: str, project_gid: str, *, refresh: bool = False
    ) -> Task:
        """Remove task from project without explicit SaveSession.

        Args:
            task_gid: Target task GID
            project_gid: Project GID to remove task from
            refresh: If True, fetch fresh task state after commit. If False (default),
                     return the task fetched before commit.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or project not found
            SaveSessionError: If the action operation fails
            ValidationError: If task_gid or project_gid is invalid.

        Example:
            >>> task = await client.tasks.remove_from_project_async(task_gid, project_gid)
        """
        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(project_gid, "project_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self.get_async(task_gid)
            session.remove_from_project(task, project_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self.get_async(task_gid)
        return task

    def remove_from_project(
        self, task_gid: str, project_gid: str, *, refresh: bool = False
    ) -> Task:
        """Remove task from project without explicit SaveSession (sync).

        Args:
            task_gid: Target task GID
            project_gid: Project GID to remove task from
            refresh: If True, fetch fresh task state after commit. Default False.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)

        Raises:
            APIError: If task or project not found
            SaveSessionError: If the action operation fails
        """
        return self._remove_from_project_sync(task_gid, project_gid, refresh=refresh)

    @sync_wrapper("remove_from_project_async")
    async def _remove_from_project_sync(
        self, task_gid: str, project_gid: str, *, refresh: bool = False
    ) -> Task:
        """Internal sync wrapper for remove_from_project_async."""
        return await self.remove_from_project_async(
            task_gid, project_gid, refresh=refresh
        )

    # --- Task Duplication ---
    # Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT: Wraps Asana's duplicate endpoint

    @overload
    async def duplicate_async(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[False] = ...,
    ) -> Task:
        """Duplicate a task, returning a Task model."""
        ...

    @overload
    async def duplicate_async(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Duplicate a task, returning a raw dict."""
        ...

    @error_handler
    async def duplicate_async(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = None,
        raw: bool = False,
    ) -> Task | dict[str, Any]:
        """Duplicate a task with optional attribute copying.

        Per FR-DUP-001: Wraps Asana's POST /tasks/{task_gid}/duplicate.

        Args:
            task_gid: GID of the task to duplicate.
            name: Name for the new task (required by Asana API).
            include: List of attributes to copy. Valid values:
                - "subtasks": Copy all subtasks
                - "notes": Copy task description
                - "assignee": Copy assignee
                - "attachments": Copy attachments
                - "dates": Copy due dates
                - "dependencies": Copy dependencies
                - "collaborators": Copy followers
                - "tags": Copy tags
            raw: If True, return raw dict instead of Task model.

        Returns:
            Task model (or dict if raw=True) representing the new task.
            The new_task.gid is immediately available.
            Note: Subtasks are created asynchronously by Asana.

        Raises:
            ValidationError: If task_gid is invalid.
            NotFoundError: If source task doesn't exist.
        """
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")

        # Build request payload
        data: dict[str, Any] = {"name": name}
        if include:
            data["include"] = include

        # Call Asana duplicate endpoint
        result = await self._http.post(
            f"/tasks/{task_gid}/duplicate",
            json={"data": data},
        )

        # Asana returns a job object with new_task embedded
        # Extract the new_task from the job response
        new_task_data: dict[str, Any] = result.get("new_task", result)

        if raw:
            return new_task_data
        task = Task.model_validate(new_task_data)
        task._client = self._client
        return task

    @overload
    def duplicate(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[False] = ...,
    ) -> Task:
        """Duplicate a task (sync), returning a Task model."""
        ...

    @overload
    def duplicate(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Duplicate a task (sync), returning a raw dict."""
        ...

    def duplicate(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = None,
        raw: bool = False,
    ) -> Task | dict[str, Any]:
        """Duplicate a task (sync).

        Per FR-DUP-001: Wraps Asana's POST /tasks/{task_gid}/duplicate.

        Args:
            task_gid: GID of the task to duplicate.
            name: Name for the new task (required by Asana API).
            include: List of attributes to copy. Valid values:
                - "subtasks": Copy all subtasks
                - "notes": Copy task description
                - "assignee": Copy assignee
                - "attachments": Copy attachments
                - "dates": Copy due dates
                - "dependencies": Copy dependencies
                - "collaborators": Copy followers
                - "tags": Copy tags
            raw: If True, return raw dict instead of Task model.

        Returns:
            Task model (or dict if raw=True) representing the new task.
        """
        return self._duplicate_sync(task_gid, name=name, include=include, raw=raw)

    @sync_wrapper("duplicate_async")
    async def _duplicate_sync(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = None,
        raw: bool = False,
    ) -> Task | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.duplicate_async(
                task_gid, name=name, include=include, raw=True
            )
        return await self.duplicate_async(
            task_gid, name=name, include=include, raw=False
        )
