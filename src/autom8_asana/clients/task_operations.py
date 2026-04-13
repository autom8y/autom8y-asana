"""P1 convenience methods for common task operations.

Per TDD-SDKUX Section 2C: Direct methods that wrap SaveSession internally
and return updated Task objects without requiring explicit session management.

Per ADR-0059: Extracted from tasks.py for SRP compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.models import Task
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.tasks import TasksClient

__all__ = ["TaskOperations"]


class TaskOperations:
    """P1 convenience methods for common task operations.

    Wraps SaveSession internally for single-action operations.
    Per TDD-SDKUX Section 2C.

    Thread Safety: Stateless - safe for concurrent use.
    """

    def __init__(self, tasks_client: TasksClient) -> None:
        """Initialize with parent TasksClient.

        Args:
            tasks_client: Parent client providing HTTP and client references.
        """
        self._client: AsanaClient | None = tasks_client._client
        self._tasks = tasks_client
        self._http = tasks_client._http

    # --- Tag Operations ---

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def add_tag(
        self,
        task_gid: str,
        tag_gid: str,
        *,
        refresh: bool = False,
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
        from autom8_asana.persistence.errors import SaveSessionError
        from autom8_asana.persistence.session import SaveSession
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(tag_gid, "tag_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self._tasks.get_async(task_gid)
            session.add_tag(task, tag_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        # Per TDD-TRIAGE-FIXES: Only refresh if explicitly requested
        if refresh:
            return await self._tasks.get_async(task_gid)
        return task

    # --- Remove Tag ---

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def remove_tag(
        self,
        task_gid: str,
        tag_gid: str,
        *,
        refresh: bool = False,
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
        from autom8_asana.persistence.errors import SaveSessionError
        from autom8_asana.persistence.session import SaveSession
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(tag_gid, "tag_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self._tasks.get_async(task_gid)
            session.remove_tag(task, tag_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self._tasks.get_async(task_gid)
        return task

    # --- Move to Section ---

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def move_to_section(
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
        from autom8_asana.persistence.errors import SaveSessionError
        from autom8_asana.persistence.session import SaveSession
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(section_gid, "section_gid")
        validate_gid(project_gid, "project_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self._tasks.get_async(task_gid)
            session.move_to_section(task, section_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self._tasks.get_async(task_gid)
        return task

    # --- Set Assignee ---

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def set_assignee(self, task_gid: str, assignee_gid: str) -> Task:
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

    # --- Add to Project ---

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def add_to_project(
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
        from autom8_asana.persistence.errors import SaveSessionError
        from autom8_asana.persistence.session import SaveSession
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(project_gid, "project_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self._tasks.get_async(task_gid)
            session.add_to_project(task, project_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self._tasks.get_async(task_gid)
        return task

    # --- Remove from Project ---

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def remove_from_project(
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
        from autom8_asana.persistence.errors import SaveSessionError
        from autom8_asana.persistence.session import SaveSession
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        validate_gid(project_gid, "project_gid")

        async with SaveSession(self._client) as session:  # type: ignore[arg-type]
            task = await self._tasks.get_async(task_gid)
            session.remove_from_project(task, project_gid)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

        if refresh:
            return await self._tasks.get_async(task_gid)
        return task
