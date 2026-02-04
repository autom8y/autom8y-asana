"""Tasks REST endpoints delegating to TaskService.

This module provides REST endpoints for Asana Task operations,
delegating business logic to TaskService per TDD-I2-SERVICE-WIRING-001.

Endpoints:
- GET /api/v1/tasks?project={gid} - List tasks by project (paginated)
- GET /api/v1/tasks?section={gid} - List tasks by section (paginated)
- GET /api/v1/tasks/{gid} - Get task by GID
- GET /api/v1/tasks/{gid}?opt_fields=... - Get task with specific fields
- POST /api/v1/tasks - Create task
- PUT /api/v1/tasks/{gid} - Update task
- DELETE /api/v1/tasks/{gid} - Delete task
- GET /api/v1/tasks/{gid}/subtasks - List subtasks (paginated)
- GET /api/v1/tasks/{gid}/dependents - List dependents (paginated)
- POST /api/v1/tasks/{gid}/duplicate - Duplicate task
- POST /api/v1/tasks/{gid}/tags - Add tag to task
- DELETE /api/v1/tasks/{gid}/tags/{tag_gid} - Remove tag from task
- POST /api/v1/tasks/{gid}/section - Move task to section
- PUT /api/v1/tasks/{gid}/assignee - Set task assignee
- POST /api/v1/tasks/{gid}/projects - Add task to project
- DELETE /api/v1/tasks/{gid}/projects/{project_gid} - Remove task from project

Per TDD-ASANA-SATELLITE:
- All endpoints require Bearer token authentication
- Responses use standard envelope: {"data": ..., "meta": {...}}
- List endpoints support cursor-based pagination
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

from autom8_asana.api.dependencies import (
    AsanaClientDualMode,
    RequestId,
    TaskServiceDep,
)
from autom8_asana.api.models import (
    AddTagRequest,
    AddToProjectRequest,
    CreateTaskRequest,
    DuplicateTaskRequest,
    MoveSectionRequest,
    PaginationMeta,
    SetAssigneeRequest,
    SuccessResponse,
    UpdateTaskRequest,
    build_success_response,
)
from autom8_asana.services.errors import ServiceError, get_status_for_error
from autom8_asana.services.task_service import CreateTaskParams, UpdateTaskParams

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


# --- Core CRUD Endpoints ---


@router.get(
    "",
    summary="List tasks by project or section",
    response_model=SuccessResponse[list[dict[str, Any]]],
)
async def list_tasks(
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
    project: Annotated[
        str | None,
        Query(description="Project GID to list tasks from"),
    ] = None,
    section: Annotated[
        str | None,
        Query(description="Section GID to list tasks from"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
) -> SuccessResponse[list[dict[str, Any]]]:
    """List tasks by project or section with pagination.

    Args:
        project: Project GID to list tasks from.
        section: Section GID to list tasks from.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of tasks with pagination metadata.

    Raises:
        400: Neither project nor section provided, or both provided.
    """
    try:
        result = await task_service.list_tasks(
            client, project=project, section=section, limit=limit, offset=offset
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=get_status_for_error(e), detail=e.message
        )

    pagination = PaginationMeta(
        limit=limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
    )

    return build_success_response(
        data=result.data, request_id=request_id, pagination=pagination
    )


@router.get(
    "/{gid}",
    summary="Get task by GID",
    response_model=SuccessResponse[dict[str, Any]],
)
async def get_task(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
    opt_fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of fields to include",
            examples=["name,notes,due_on,assignee"],
        ),
    ] = None,
) -> SuccessResponse[dict[str, Any]]:
    """Get a task by its GID.

    Args:
        gid: Asana task GID.
        opt_fields: Comma-separated list of fields to include in response.

    Returns:
        Task data with requested fields.
    """
    fields_list: list[str] | None = None
    if opt_fields:
        fields_list = [f.strip() for f in opt_fields.split(",")]

    task = await task_service.get_task(client, gid, opt_fields=fields_list)
    return build_success_response(data=task, request_id=request_id)


# T1: POST /tasks - Create task
@router.post(
    "",
    summary="Create a new task",
    response_model=SuccessResponse[dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    body: CreateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Create a new task.

    Args:
        body: Task creation parameters.

    Returns:
        Created task data.

    Raises:
        400: Neither projects nor workspace provided.
    """
    try:
        task = await task_service.create_task(
            client,
            CreateTaskParams(
                name=body.name,
                projects=body.projects,
                workspace=body.workspace,
                notes=body.notes,
                assignee=body.assignee,
                due_on=body.due_on,
            ),
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=get_status_for_error(e), detail=e.message
        )

    return build_success_response(data=task, request_id=request_id)


# T2: PUT /tasks/{gid} - Update task
@router.put(
    "/{gid}",
    summary="Update a task",
    response_model=SuccessResponse[dict[str, Any]],
)
async def update_task(
    gid: str,
    body: UpdateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Update an existing task.

    Only provided fields are updated; omitted fields retain their values.

    Args:
        gid: Asana task GID.
        body: Fields to update.

    Returns:
        Updated task data.
    """
    try:
        task = await task_service.update_task(
            client,
            gid,
            UpdateTaskParams(
                name=body.name,
                notes=body.notes,
                completed=body.completed,
                due_on=body.due_on,
            ),
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=get_status_for_error(e), detail=e.message
        )

    return build_success_response(data=task, request_id=request_id)


# T3: DELETE /tasks/{gid} - Delete task
@router.delete(
    "/{gid}",
    summary="Delete a task",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    gid: str,
    client: AsanaClientDualMode,
    task_service: TaskServiceDep,
) -> None:
    """Delete a task.

    Args:
        gid: Asana task GID.

    Returns:
        No content on success.
    """
    await task_service.delete_task(client, gid)


# --- Related Operations ---


@router.get(
    "/{gid}/subtasks",
    summary="List subtasks of a task",
    response_model=SuccessResponse[list[dict[str, Any]]],
)
async def list_subtasks(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
) -> SuccessResponse[list[dict[str, Any]]]:
    """List subtasks of a task with pagination.

    Args:
        gid: Parent task GID.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of subtasks with pagination metadata.
    """
    result = await task_service.list_subtasks(
        client, gid, limit=limit, offset=offset
    )

    pagination = PaginationMeta(
        limit=limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
    )

    return build_success_response(
        data=result.data, request_id=request_id, pagination=pagination
    )


@router.get(
    "/{gid}/dependents",
    summary="List dependent tasks",
    response_model=SuccessResponse[list[dict[str, Any]]],
)
async def list_dependents(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
) -> SuccessResponse[list[dict[str, Any]]]:
    """List tasks that depend on this task with pagination.

    Args:
        gid: Task GID to get dependents for.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of dependent tasks with pagination metadata.
    """
    result = await task_service.list_dependents(
        client, gid, limit=limit, offset=offset
    )

    pagination = PaginationMeta(
        limit=limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
    )

    return build_success_response(
        data=result.data, request_id=request_id, pagination=pagination
    )


# T4: POST /tasks/{gid}/duplicate - Duplicate task
@router.post(
    "/{gid}/duplicate",
    summary="Duplicate a task",
    response_model=SuccessResponse[dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_task(
    gid: str,
    body: DuplicateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Duplicate a task.

    Args:
        gid: GID of task to duplicate.
        body: Name for the duplicated task.

    Returns:
        New duplicated task data.
    """
    task = await task_service.duplicate_task(client, gid, body.name)
    return build_success_response(data=task, request_id=request_id)


# --- Tags ---


# T5: POST /tasks/{gid}/tags - Add tag
@router.post(
    "/{gid}/tags",
    summary="Add tag to task",
    response_model=SuccessResponse[dict[str, Any]],
)
async def add_tag(
    gid: str,
    body: AddTagRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Add a tag to a task.

    Args:
        gid: Task GID.
        body: Tag GID to add.

    Returns:
        Updated task data.
    """
    task_data = await task_service.add_tag(client, gid, body.tag_gid)
    return build_success_response(data=task_data, request_id=request_id)


# T6: DELETE /tasks/{gid}/tags/{tag_gid} - Remove tag
@router.delete(
    "/{gid}/tags/{tag_gid}",
    summary="Remove tag from task",
    response_model=SuccessResponse[dict[str, Any]],
)
async def remove_tag(
    gid: str,
    tag_gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Remove a tag from a task.

    Args:
        gid: Task GID.
        tag_gid: Tag GID to remove.

    Returns:
        Updated task data.
    """
    task_data = await task_service.remove_tag(client, gid, tag_gid)
    return build_success_response(data=task_data, request_id=request_id)


# --- Membership ---


# T7: POST /tasks/{gid}/section - Move to section
@router.post(
    "/{gid}/section",
    summary="Move task to section",
    response_model=SuccessResponse[dict[str, Any]],
)
async def move_to_section(
    gid: str,
    body: MoveSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Move a task to a section within a project.

    Args:
        gid: Task GID.
        body: Target section and project GIDs.

    Returns:
        Updated task data.
    """
    task_data = await task_service.move_to_section(
        client, gid, body.section_gid, body.project_gid
    )
    return build_success_response(data=task_data, request_id=request_id)


# T8: PUT /tasks/{gid}/assignee - Set assignee
@router.put(
    "/{gid}/assignee",
    summary="Set task assignee",
    response_model=SuccessResponse[dict[str, Any]],
)
async def set_assignee(
    gid: str,
    body: SetAssigneeRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Set or clear the task assignee.

    Args:
        gid: Task GID.
        body: Assignee user GID (null to unassign).

    Returns:
        Updated task data.
    """
    task = await task_service.set_assignee(client, gid, body.assignee_gid)
    return build_success_response(data=task, request_id=request_id)


# T9: POST /tasks/{gid}/projects - Add to project
@router.post(
    "/{gid}/projects",
    summary="Add task to project",
    response_model=SuccessResponse[dict[str, Any]],
)
async def add_to_project(
    gid: str,
    body: AddToProjectRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Add a task to a project.

    Args:
        gid: Task GID.
        body: Project GID to add task to.

    Returns:
        Updated task data.
    """
    task_data = await task_service.add_to_project(client, gid, body.project_gid)
    return build_success_response(data=task_data, request_id=request_id)


# T10: DELETE /tasks/{gid}/projects/{project_gid} - Remove from project
@router.delete(
    "/{gid}/projects/{project_gid}",
    summary="Remove task from project",
    response_model=SuccessResponse[dict[str, Any]],
)
async def remove_from_project(
    gid: str,
    project_gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[dict[str, Any]]:
    """Remove a task from a project.

    Args:
        gid: Task GID.
        project_gid: Project GID to remove task from.

    Returns:
        Updated task data.
    """
    task_data = await task_service.remove_from_project(client, gid, project_gid)
    return build_success_response(data=task_data, request_id=request_id)


__all__ = ["router"]
