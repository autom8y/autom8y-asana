"""Tasks client - returns typed Task models by default.

Phase 3.2: Updated to return Pydantic Task models.
Use raw=True for backward-compatible dict returns.
Per TDD-0002: list_async() returns PageIterator[Task] for automatic pagination.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator, Task
from autom8_asana.observability import error_handler
from autom8_asana.transport.sync import sync_wrapper


class TasksClient(BaseClient):
    """Client for Asana Task operations.

    Returns typed Task models by default. Use raw=True for dict returns.
    """

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
        """Get a task by GID.

        Args:
            task_gid: Task GID
            raw: If True, return raw dict instead of Task model
            opt_fields: Optional fields to include

        Returns:
            Task model by default, or dict if raw=True
        """
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/tasks/{task_gid}", params=params)
        if raw:
            return data
        return Task.model_validate(data)

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
        return Task.model_validate(result)

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
        return Task.model_validate(result)

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
