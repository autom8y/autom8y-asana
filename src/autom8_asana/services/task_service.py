"""Task CRUD operations with integrated cache invalidation.

Per TDD-SERVICE-LAYER-001 Phase 2: Encapsulates task business logic
extracted from api/routes/tasks.py. The service owns MutationEvent
construction and fire-and-forget invalidation, eliminating the
repeated pattern from each route handler.

Usage:
    service = TaskService(invalidator=mutation_invalidator)
    task = await service.create_task(client, params)
    task = await service.update_task(client, gid, params)
    await service.delete_task(client, gid)

Note: This service does NOT modify route handlers. Route wiring
is Phase 3/4 work per the migration plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
    extract_project_gids,
)
from autom8_asana.services.errors import InvalidParameterError

if TYPE_CHECKING:
    from autom8_asana import AsanaClient
    from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Service Data Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateTaskParams:
    """Parameters for creating a task.

    Mirrors CreateTaskRequest but is transport-agnostic.

    Attributes:
        name: Task name (required).
        projects: List of project GIDs (optional).
        workspace: Workspace GID (optional, required if no projects).
        notes: Task description (optional).
        assignee: Assignee user GID (optional).
        due_on: Due date YYYY-MM-DD (optional).
    """

    name: str
    projects: list[str] | None = None
    workspace: str | None = None
    notes: str | None = None
    assignee: str | None = None
    due_on: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateTaskParams:
    """Parameters for updating a task.

    All fields optional; only non-None fields are sent to Asana.

    Attributes:
        name: New task name.
        notes: New task description.
        completed: Completion status.
        due_on: Due date YYYY-MM-DD.
    """

    name: str | None = None
    notes: str | None = None
    completed: bool | None = None
    due_on: str | None = None


@dataclass(frozen=True, slots=True)
class ServiceListResult:
    """Paginated list result from service layer.

    Attributes:
        data: List of entity dicts.
        has_more: Whether more pages exist.
        next_offset: Opaque pagination cursor, or None.
    """

    data: list[dict[str, Any]]
    has_more: bool
    next_offset: str | None


# ---------------------------------------------------------------------------
# TaskService
# ---------------------------------------------------------------------------


class TaskService:
    """Task CRUD operations with integrated cache invalidation.

    Encapsulates:
    - Asana SDK task client calls
    - MutationEvent construction from response data
    - Fire-and-forget invalidation via MutationInvalidator

    Dependencies are received via constructor injection per ADR-SLE-002.
    The AsanaClient is passed per-method since it varies per request.
    """

    def __init__(self, invalidator: MutationInvalidator) -> None:
        """Initialize with invalidation dependency.

        Args:
            invalidator: MutationInvalidator for cache invalidation.
        """
        self._invalidator = invalidator

    # --- List Operations ---

    async def list_tasks(
        self,
        client: AsanaClient,
        *,
        project: str | None = None,
        section: str | None = None,
        limit: int = 100,
        offset: str | None = None,
    ) -> ServiceListResult:
        """List tasks by project or section with pagination.

        Args:
            client: Asana SDK client for API calls.
            project: Project GID (mutually exclusive with section).
            section: Section GID (mutually exclusive with project).
            limit: Maximum items per page (1-100).
            offset: Pagination cursor from previous response.

        Returns:
            ServiceListResult with task data and pagination info.

        Raises:
            InvalidParameterError: Neither or both of project/section provided.
        """
        if project is None and section is None:
            raise InvalidParameterError(
                "Either 'project' or 'section' query parameter is required"
            )
        if project is not None and section is not None:
            raise InvalidParameterError(
                "Only one of 'project' or 'section' may be specified"
            )

        params: dict[str, Any] = {"limit": min(limit, 100)}
        if offset:
            params["offset"] = offset

        if project:
            endpoint = f"/projects/{project}/tasks"
        else:
            endpoint = f"/sections/{section}/tasks"

        data, next_offset = await client._http.get_paginated(endpoint, params=params)

        return ServiceListResult(
            data=data,
            has_more=next_offset is not None,
            next_offset=next_offset,
        )

    # --- Get ---

    async def get_task(
        self,
        client: AsanaClient,
        gid: str,
        *,
        opt_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get task by GID.

        Args:
            client: Asana SDK client.
            gid: Asana task GID.
            opt_fields: Optional list of fields to include.

        Returns:
            Task data dict from Asana API.
        """
        return await client.tasks.get_async(gid, opt_fields=opt_fields, raw=True)

    # --- Create (T1) ---

    async def create_task(
        self,
        client: AsanaClient,
        params: CreateTaskParams,
    ) -> dict[str, Any]:
        """Create task and fire invalidation event.

        Args:
            client: Asana SDK client.
            params: Task creation parameters.

        Returns:
            Created task data dict.

        Raises:
            InvalidParameterError: Neither projects nor workspace provided.
        """
        if params.projects is None and params.workspace is None:
            raise InvalidParameterError(
                "Either 'projects' or 'workspace' must be provided"
            )

        kwargs: dict[str, Any] = {}
        if params.notes:
            kwargs["notes"] = params.notes
        if params.assignee:
            kwargs["assignee"] = params.assignee
        if params.due_on:
            kwargs["due_on"] = params.due_on

        task = await client.tasks.create_async(
            name=params.name,
            projects=params.projects,
            workspace=params.workspace,
            raw=True,
            **kwargs,
        )

        # Encapsulated invalidation
        project_gids = extract_project_gids(task) or (params.projects or [])
        task_gid = task.get("gid", "") if isinstance(task, dict) else ""
        self._fire_invalidation(
            entity_gid=task_gid,
            mutation_type=MutationType.CREATE,
            project_gids=list(project_gids),
        )

        return task

    # --- Update (T2) ---

    async def update_task(
        self,
        client: AsanaClient,
        gid: str,
        params: UpdateTaskParams,
    ) -> dict[str, Any]:
        """Update task and fire invalidation event.

        Args:
            client: Asana SDK client.
            gid: Asana task GID.
            params: Fields to update.

        Returns:
            Updated task data dict.

        Raises:
            InvalidParameterError: No fields provided for update.
        """
        kwargs: dict[str, Any] = {}
        if params.name is not None:
            kwargs["name"] = params.name
        if params.notes is not None:
            kwargs["notes"] = params.notes
        if params.completed is not None:
            kwargs["completed"] = params.completed
        if params.due_on is not None:
            kwargs["due_on"] = params.due_on

        if not kwargs:
            raise InvalidParameterError(
                "At least one field must be provided for update"
            )

        task = await client.tasks.update_async(gid, raw=True, **kwargs)

        self._fire_invalidation(
            entity_gid=gid,
            mutation_type=MutationType.UPDATE,
            project_gids=extract_project_gids(task),
        )

        return task

    # --- Delete (T3) ---

    async def delete_task(
        self,
        client: AsanaClient,
        gid: str,
    ) -> None:
        """Delete task and fire invalidation event.

        Args:
            client: Asana SDK client.
            gid: Asana task GID.
        """
        await client.tasks.delete_async(gid)  # type: ignore[attr-defined]

        # 204 No Content: no project GIDs available from response
        self._fire_invalidation(
            entity_gid=gid,
            mutation_type=MutationType.DELETE,
            project_gids=[],
        )

    # --- Subtasks / Dependents ---

    async def list_subtasks(
        self,
        client: AsanaClient,
        gid: str,
        *,
        limit: int = 100,
        offset: str | None = None,
    ) -> ServiceListResult:
        """List subtasks of a task with pagination.

        Args:
            client: Asana SDK client.
            gid: Parent task GID.
            limit: Maximum items per page.
            offset: Pagination cursor.

        Returns:
            ServiceListResult with subtask data.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if offset:
            params["offset"] = offset

        data, next_offset = await client._http.get_paginated(
            f"/tasks/{gid}/subtasks", params=params
        )

        return ServiceListResult(
            data=data,
            has_more=next_offset is not None,
            next_offset=next_offset,
        )

    async def list_dependents(
        self,
        client: AsanaClient,
        gid: str,
        *,
        limit: int = 100,
        offset: str | None = None,
    ) -> ServiceListResult:
        """List tasks that depend on this task.

        Args:
            client: Asana SDK client.
            gid: Task GID.
            limit: Maximum items per page.
            offset: Pagination cursor.

        Returns:
            ServiceListResult with dependent task data.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if offset:
            params["offset"] = offset

        data, next_offset = await client._http.get_paginated(
            f"/tasks/{gid}/dependents", params=params
        )

        return ServiceListResult(
            data=data,
            has_more=next_offset is not None,
            next_offset=next_offset,
        )

    # --- Duplicate (T4) ---

    async def duplicate_task(
        self,
        client: AsanaClient,
        gid: str,
        name: str,
    ) -> dict[str, Any]:
        """Duplicate a task and fire invalidation event.

        Args:
            client: Asana SDK client.
            gid: GID of task to duplicate.
            name: Name for the duplicated task.

        Returns:
            New task data dict.
        """
        task = await client.tasks.duplicate_async(gid, name=name, raw=True)

        task_gid = task.get("gid", "") if isinstance(task, dict) else ""
        self._fire_invalidation(
            entity_gid=task_gid,
            mutation_type=MutationType.CREATE,
            project_gids=extract_project_gids(task),
        )

        return task

    # --- Tags (T5, T6) ---

    async def add_tag(
        self,
        client: AsanaClient,
        gid: str,
        tag_gid: str,
    ) -> dict[str, Any]:
        """Add a tag to a task.

        Args:
            client: Asana SDK client.
            gid: Task GID.
            tag_gid: Tag GID to add.

        Returns:
            Updated task data dict.
        """
        task = await client.tasks.add_tag_async(gid, tag_gid)
        task_data = task.model_dump()

        self._fire_invalidation(
            entity_gid=gid,
            mutation_type=MutationType.UPDATE,
            project_gids=extract_project_gids(task_data),
        )

        return task_data

    async def remove_tag(
        self,
        client: AsanaClient,
        gid: str,
        tag_gid: str,
    ) -> dict[str, Any]:
        """Remove a tag from a task.

        Args:
            client: Asana SDK client.
            gid: Task GID.
            tag_gid: Tag GID to remove.

        Returns:
            Updated task data dict.
        """
        task = await client.tasks.remove_tag_async(gid, tag_gid)
        task_data = task.model_dump()

        self._fire_invalidation(
            entity_gid=gid,
            mutation_type=MutationType.UPDATE,
            project_gids=extract_project_gids(task_data),
        )

        return task_data

    # --- Membership (T7, T8, T9, T10) ---

    async def move_to_section(
        self,
        client: AsanaClient,
        gid: str,
        section_gid: str,
        project_gid: str,
    ) -> dict[str, Any]:
        """Move a task to a section within a project.

        Args:
            client: Asana SDK client.
            gid: Task GID.
            section_gid: Target section GID.
            project_gid: Project GID containing the section.

        Returns:
            Updated task data dict.
        """
        task = await client.tasks.move_to_section_async(gid, section_gid, project_gid)
        task_data = task.model_dump()

        project_gids = extract_project_gids(task_data) or [project_gid]
        self._invalidator.fire_and_forget(
            MutationEvent(
                entity_kind=EntityKind.TASK,
                entity_gid=gid,
                mutation_type=MutationType.MOVE,
                project_gids=project_gids,
                section_gid=section_gid,
            )
        )

        return task_data

    async def set_assignee(
        self,
        client: AsanaClient,
        gid: str,
        assignee_gid: str | None,
    ) -> dict[str, Any]:
        """Set or clear the task assignee.

        Args:
            client: Asana SDK client.
            gid: Task GID.
            assignee_gid: User GID, or None to unassign.

        Returns:
            Updated task data dict.
        """
        if assignee_gid is None:
            task = await client.tasks.update_async(gid, raw=True, assignee=None)
        else:
            task_obj = await client.tasks.set_assignee_async(gid, assignee_gid)
            task = task_obj.model_dump()

        self._fire_invalidation(
            entity_gid=gid,
            mutation_type=MutationType.UPDATE,
            project_gids=extract_project_gids(task),
        )

        return task

    async def add_to_project(
        self,
        client: AsanaClient,
        gid: str,
        project_gid: str,
    ) -> dict[str, Any]:
        """Add a task to a project.

        Args:
            client: Asana SDK client.
            gid: Task GID.
            project_gid: Project GID to add task to.

        Returns:
            Updated task data dict.
        """
        task = await client.tasks.add_to_project_async(gid, project_gid)
        task_data = task.model_dump()

        self._invalidator.fire_and_forget(
            MutationEvent(
                entity_kind=EntityKind.TASK,
                entity_gid=gid,
                mutation_type=MutationType.ADD_MEMBER,
                project_gids=[project_gid],
            )
        )

        return task_data

    async def remove_from_project(
        self,
        client: AsanaClient,
        gid: str,
        project_gid: str,
    ) -> dict[str, Any]:
        """Remove a task from a project.

        Args:
            client: Asana SDK client.
            gid: Task GID.
            project_gid: Project GID to remove task from.

        Returns:
            Updated task data dict.
        """
        task = await client.tasks.remove_from_project_async(gid, project_gid)
        task_data = task.model_dump()

        self._invalidator.fire_and_forget(
            MutationEvent(
                entity_kind=EntityKind.TASK,
                entity_gid=gid,
                mutation_type=MutationType.REMOVE_MEMBER,
                project_gids=[project_gid],
            )
        )

        return task_data

    # --- Private: Invalidation Helper ---

    def _fire_invalidation(
        self,
        *,
        entity_gid: str,
        mutation_type: MutationType,
        project_gids: list[str],
        section_gid: str | None = None,
    ) -> None:
        """Construct MutationEvent and fire invalidation.

        Centralizes the repeated MutationEvent construction pattern.

        Args:
            entity_gid: GID of the mutated task.
            mutation_type: What operation was performed.
            project_gids: Affected project GIDs.
            section_gid: Optional section context.
        """
        self._invalidator.fire_and_forget(
            MutationEvent(
                entity_kind=EntityKind.TASK,
                entity_gid=entity_gid,
                mutation_type=mutation_type,
                project_gids=project_gids,
                section_gid=section_gid,
            )
        )


__all__ = [
    "CreateTaskParams",
    "ServiceListResult",
    "TaskService",
    "UpdateTaskParams",
]
