"""Tasks REST endpoints with cache invalidation.

This module provides REST endpoints for Asana Task operations,
wrapping the SDK TasksClient with thin API handlers.

Per TDD-CACHE-INVALIDATION-001: All 10 mutation endpoints (T1-T10)
fire MutationInvalidator.fire_and_forget() after successful Asana API calls.

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
    MutationInvalidatorDep,
    RequestId,
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
from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
    extract_project_gids,
)

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

    Returns a paginated list of tasks from the specified project or section.
    Either project or section must be provided (not both).

    Args:
        project: Project GID to list tasks from (FR-API-TASK-006).
        section: Section GID to list tasks from (FR-API-TASK-007).
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response (FR-API-TASK-008).

    Returns:
        List of tasks with pagination metadata.

    Raises:
        400: Neither project nor section provided, or both provided.
    """
    if project is None and section is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'project' or 'section' query parameter is required",
        )

    if project is not None and section is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of 'project' or 'section' may be specified",
        )

    # Build params for SDK call
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if offset:
        params["offset"] = offset

    # Use the HTTP client directly for paginated requests
    if project:
        endpoint = f"/projects/{project}/tasks"
    else:
        endpoint = f"/sections/{section}/tasks"

    data, next_offset = await client._http.get_paginated(endpoint, params=params)

    pagination = PaginationMeta(
        limit=limit,
        has_more=next_offset is not None,
        next_offset=next_offset,
    )

    return build_success_response(
        data=data,
        request_id=request_id,
        pagination=pagination,
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
    opt_fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of fields to include",
            example="name,notes,due_on,assignee",
        ),
    ] = None,
) -> SuccessResponse[dict[str, Any]]:
    """Get a task by its GID.

    Per FR-API-TASK-001: Get task by GID.
    Per FR-API-TASK-002: Support opt_fields for field selection.

    Args:
        gid: Asana task GID.
        opt_fields: Comma-separated list of fields to include in response.

    Returns:
        Task data with requested fields.
    """
    # Parse opt_fields if provided
    fields_list: list[str] | None = None
    if opt_fields:
        fields_list = [f.strip() for f in opt_fields.split(",")]

    task = await client.tasks.get_async(gid, opt_fields=fields_list, raw=True)
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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Create a new task.

    Per FR-API-TASK-003: Create task with name, notes, assignee, projects, due_on.

    Args:
        body: Task creation parameters.

    Returns:
        Created task data.

    Raises:
        400: Neither projects nor workspace provided.
    """
    if body.projects is None and body.workspace is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'projects' or 'workspace' must be provided",
        )

    # Build kwargs for SDK
    kwargs: dict[str, Any] = {}
    if body.notes:
        kwargs["notes"] = body.notes
    if body.assignee:
        kwargs["assignee"] = body.assignee
    if body.due_on:
        kwargs["due_on"] = body.due_on

    task = await client.tasks.create_async(
        name=body.name,
        projects=body.projects,
        workspace=body.workspace,
        raw=True,
        **kwargs,
    )

    # Fire-and-forget: invalidate cache without blocking response
    # Project GIDs from request body (task response may also include them)
    project_gids = extract_project_gids(task) or (body.projects or [])
    task_gid = task.get("gid", "") if isinstance(task, dict) else ""
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=task_gid,
        mutation_type=MutationType.CREATE,
        project_gids=list(project_gids),
    ))

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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Update an existing task.

    Per FR-API-TASK-004: Update task fields.

    Only provided fields are updated; omitted fields retain their values.

    Args:
        gid: Asana task GID.
        body: Fields to update.

    Returns:
        Updated task data.
    """
    # Build kwargs from non-None fields
    kwargs: dict[str, Any] = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.notes is not None:
        kwargs["notes"] = body.notes
    if body.completed is not None:
        kwargs["completed"] = body.completed
    if body.due_on is not None:
        kwargs["due_on"] = body.due_on

    if not kwargs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )

    task = await client.tasks.update_async(gid, raw=True, **kwargs)

    # Fire-and-forget: invalidate cache without blocking response
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.UPDATE,
        project_gids=extract_project_gids(task),
    ))

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
    invalidator: MutationInvalidatorDep,
) -> None:
    """Delete a task.

    Per FR-API-TASK-005: Delete task by GID.
    Per ADR-002: DELETE returns 204 with no body, so no project_gids available.
    Entity cache is still invalidated; DataFrame invalidation skipped.

    Args:
        gid: Asana task GID.

    Returns:
        No content on success.
    """
    await client.tasks.delete_async(gid)

    # Fire-and-forget: entity cache invalidated, DataFrame skipped (no project context)
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.DELETE,
        project_gids=[],  # 204 No Content - no project GIDs available
    ))


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

    Per FR-API-TASK-009: List subtasks of a task.

    Args:
        gid: Parent task GID.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of subtasks with pagination metadata.
    """
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if offset:
        params["offset"] = offset

    data, next_offset = await client._http.get_paginated(
        f"/tasks/{gid}/subtasks",
        params=params,
    )

    pagination = PaginationMeta(
        limit=limit,
        has_more=next_offset is not None,
        next_offset=next_offset,
    )

    return build_success_response(
        data=data,
        request_id=request_id,
        pagination=pagination,
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

    Per FR-API-TASK-010: List dependent tasks.

    A dependent task is one that depends on this task to be completed first.

    Args:
        gid: Task GID to get dependents for.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of dependent tasks with pagination metadata.
    """
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if offset:
        params["offset"] = offset

    data, next_offset = await client._http.get_paginated(
        f"/tasks/{gid}/dependents",
        params=params,
    )

    pagination = PaginationMeta(
        limit=limit,
        has_more=next_offset is not None,
        next_offset=next_offset,
    )

    return build_success_response(
        data=data,
        request_id=request_id,
        pagination=pagination,
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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Duplicate a task.

    Per FR-API-TASK-011: Duplicate task with a new name.

    Creates a copy of the task with the specified name.

    Args:
        gid: GID of task to duplicate.
        body: Name for the duplicated task.

    Returns:
        New duplicated task data.
    """
    task = await client.tasks.duplicate_async(gid, name=body.name, raw=True)

    # Fire-and-forget: new task created via duplication
    task_gid = task.get("gid", "") if isinstance(task, dict) else ""
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=task_gid,
        mutation_type=MutationType.CREATE,
        project_gids=extract_project_gids(task),
    ))

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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Add a tag to a task.

    Per FR-API-TASK-012: Add tag to task.

    Args:
        gid: Task GID.
        body: Tag GID to add.

    Returns:
        Updated task data.
    """
    task = await client.tasks.add_tag_async(gid, body.tag_gid)
    task_data = task.model_dump()

    # Fire-and-forget: tag change affects entity cache
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.UPDATE,
        project_gids=extract_project_gids(task_data),
    ))

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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Remove a tag from a task.

    Per FR-API-TASK-013: Remove tag from task.

    Args:
        gid: Task GID.
        tag_gid: Tag GID to remove.

    Returns:
        Updated task data.
    """
    task = await client.tasks.remove_tag_async(gid, tag_gid)
    task_data = task.model_dump()

    # Fire-and-forget: tag change affects entity cache
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.UPDATE,
        project_gids=extract_project_gids(task_data),
    ))

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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Move a task to a section within a project.

    Per FR-API-TASK-014: Move task to section.

    Args:
        gid: Task GID.
        body: Target section and project GIDs.

    Returns:
        Updated task data.
    """
    task = await client.tasks.move_to_section_async(
        gid, body.section_gid, body.project_gid
    )
    task_data = task.model_dump()

    # Fire-and-forget: section move is a structural change
    # project_gid from request body covers both source and destination
    # (within the same project). Cross-project moves would need both GIDs.
    project_gids = extract_project_gids(task_data) or [body.project_gid]
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.MOVE,
        project_gids=project_gids,
        section_gid=body.section_gid,
    ))

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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Set or clear the task assignee.

    Per FR-API-TASK-015: Set task assignee.

    Args:
        gid: Task GID.
        body: Assignee user GID (null to unassign).

    Returns:
        Updated task data.
    """
    if body.assignee_gid is None:
        # Use update to clear assignee
        task = await client.tasks.update_async(gid, raw=True, assignee=None)
    else:
        task_obj = await client.tasks.set_assignee_async(gid, body.assignee_gid)
        task = task_obj.model_dump()

    # Fire-and-forget: assignee change affects entity cache
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.UPDATE,
        project_gids=extract_project_gids(task),
    ))

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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Add a task to a project.

    Per FR-API-TASK-016: Add task to project.

    Args:
        gid: Task GID.
        body: Project GID to add task to.

    Returns:
        Updated task data.
    """
    task = await client.tasks.add_to_project_async(gid, body.project_gid)
    task_data = task.model_dump()

    # Fire-and-forget: membership change is structural
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.ADD_MEMBER,
        project_gids=[body.project_gid],
    ))

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
    invalidator: MutationInvalidatorDep,
) -> SuccessResponse[dict[str, Any]]:
    """Remove a task from a project.

    Per FR-API-TASK-017: Remove task from project.

    Args:
        gid: Task GID.
        project_gid: Project GID to remove task from.

    Returns:
        Updated task data.
    """
    task = await client.tasks.remove_from_project_async(gid, project_gid)
    task_data = task.model_dump()

    # Fire-and-forget: membership removal is structural
    invalidator.fire_and_forget(MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid=gid,
        mutation_type=MutationType.REMOVE_MEMBER,
        project_gids=[project_gid],
    ))

    return build_success_response(data=task_data, request_id=request_id)


__all__ = ["router"]
