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

from typing import Annotated

from fastapi import Query, status

from autom8_asana.api.dependencies import (
    AsanaClientDualMode,
    RequestId,
    TaskServiceDep,
)
from autom8_asana.api.error_responses import (
    authenticated_responses,
    entity_responses,
    mutation_responses,
)
from autom8_asana.api.errors import raise_service_error
from autom8_asana.api.models import (
    AddTagRequest,
    AddToProjectRequest,
    AsanaResource,
    CreateTaskRequest,
    DuplicateTaskRequest,
    GidStr,
    ListTasksParams,
    MoveSectionRequest,
    PaginationMeta,
    SetAssigneeRequest,
    SuccessResponse,
    UpdateTaskRequest,
    build_success_response,
)
from autom8_asana.api.routes._security import pat_router
from autom8_asana.services.errors import ServiceError
from autom8_asana.services.task_service import CreateTaskParams, UpdateTaskParams

router = pat_router(prefix="/api/v1/tasks", tags=["tasks"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


# --- Core CRUD Endpoints ---


@router.get(
    "",
    summary="List tasks in a project or section",
    response_description="Paginated list of tasks",
    response_model=SuccessResponse[list[AsanaResource]],
    responses=authenticated_responses(),
)
async def list_tasks(
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
    params: Annotated[ListTasksParams, Query()],
) -> SuccessResponse[list[AsanaResource]]:
    """List tasks from a project or section with cursor-based pagination.

    Exactly one of ``project`` or ``section`` must be provided. Supplying
    both or neither returns ``422 Unprocessable Entity`` (via Pydantic).

    Use ``offset`` from the previous response's ``meta.pagination.next_offset``
    to retrieve the next page. When ``has_more`` is false, you have reached
    the last page.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        params: Query parameters (project/section, limit, offset).

    Returns:
        Paginated list of tasks with ``gid``, ``name``, and task fields.

    Raises:
        400: Business logic error from service layer.
        422: Validation error if project/section rules are violated.
    """
    try:
        result = await task_service.list_tasks(
            client,
            project=params.project,
            section=params.section,
            limit=params.limit,
            offset=params.offset,
        )
    except ServiceError as e:
        raise_service_error(request_id, e)

    pagination = PaginationMeta(
        limit=params.limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
    )

    return build_success_response(
        data=result.data,  # type: ignore[arg-type]
        request_id=request_id,
        pagination=pagination,
    )


@router.get(
    "/{gid}",
    summary="Get a task by GID",
    response_description="Task details",
    response_model=SuccessResponse[AsanaResource],
    responses=entity_responses(),
)
async def get_task(
    gid: GidStr,
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
) -> SuccessResponse[AsanaResource]:
    """Get a single task by its Asana GID.

    Use ``opt_fields`` to limit the response to specific fields and reduce
    payload size. When omitted, Asana returns its default field set.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Asana task GID (numeric string, e.g. ``"1234567890123456"``).
        opt_fields: Comma-separated Asana field names
            (e.g. ``"name,notes,due_on,assignee"``).

    Returns:
        Task resource with the requested fields populated.

    Raises:
        404: Task not found or not accessible with the provided token.
    """
    fields_list: list[str] | None = None
    if opt_fields:
        fields_list = [f.strip() for f in opt_fields.split(",")]

    try:
        task = await task_service.get_task(client, gid, opt_fields=fields_list)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task, request_id=request_id)  # type: ignore[arg-type]


# T1: POST /tasks - Create task
@router.post(
    "",
    summary="Create a task",
    response_description="Created task details",
    response_model=SuccessResponse[AsanaResource],
    status_code=status.HTTP_201_CREATED,
    responses=mutation_responses(),
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "task"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def create_task(
    body: CreateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Create a new task in Asana.

    At least one of ``projects`` or ``workspace`` must be provided. When
    ``projects`` is supplied, the task is added to each listed project.
    When only ``workspace`` is supplied, the task is created in that
    workspace without a project assignment.

    Requires Bearer token authentication (JWT or PAT).

    No duplicate checking is performed. Calling this endpoint multiple
    times with the same parameters creates multiple distinct tasks, each
    with a unique GID.

    Args:
        body: Task creation parameters (name, projects, workspace, etc.).

    Returns:
        The newly created task resource (HTTP 201).

    Raises:
        400: Neither ``projects`` nor ``workspace`` was provided.
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
        raise_service_error(request_id, e)

    return build_success_response(data=task, request_id=request_id)  # type: ignore[arg-type]


# T2: PUT /tasks/{gid} - Update task
@router.put(
    "/{gid}",
    summary="Update a task",
    response_description="Updated task details",
    response_model=SuccessResponse[AsanaResource],
    responses={**entity_responses(), **mutation_responses()},
)
async def update_task(
    gid: GidStr,
    body: UpdateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Update fields on an existing task.

    This is a partial update: only fields included in the request body
    are modified. Omitted fields retain their current values in Asana.

    Requires Bearer token authentication (JWT or PAT).

    **CAUTION**: Setting completed=true may trigger Asana Rules automations
    (notifications, section moves, workflow transitions). This is a partial
    update -- only fields included in the request body are modified; omitted
    fields are unchanged.

    Args:
        gid: Asana task GID.
        body: Fields to update (``name``, ``notes``, ``completed``, ``due_on``).

    Returns:
        The updated task resource.

    Raises:
        404: Task not found or not accessible with the provided token.
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
        raise_service_error(request_id, e)

    return build_success_response(data=task, request_id=request_id)  # type: ignore[arg-type]


# T3: DELETE /tasks/{gid} - Delete task
@router.delete(
    "/{gid}",
    summary="Delete a task",
    response_description="No content",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=entity_responses(),
)
async def delete_task(
    gid: GidStr,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> None:
    """Permanently delete a task from Asana.

    This action is irreversible. The task and all its subtasks are removed
    from Asana. Consider completing or archiving instead.

    Requires Bearer token authentication (JWT or PAT).

    **IRREVERSIBLE**: Permanently deletes this task and ALL subtasks.
    Dependents are orphaned. No backup is created. Consider completing the
    task (PUT with completed=true) instead of deleting.

    Args:
        gid: Asana task GID.

    Returns:
        204 No Content on success.

    Raises:
        404: Task not found or not accessible with the provided token.
    """
    try:
        await task_service.delete_task(client, gid)
    except ServiceError as e:
        raise_service_error(request_id, e)


# --- Related Operations ---


@router.get(
    "/{gid}/subtasks",
    summary="List subtasks of a task",
    response_description="Paginated list of subtasks",
    response_model=SuccessResponse[list[AsanaResource]],
    responses=entity_responses(),
)
async def list_subtasks(
    gid: GidStr,
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
) -> SuccessResponse[list[AsanaResource]]:
    """List direct subtasks of a task with cursor-based pagination.

    Returns the immediate child tasks of the specified parent. Only
    direct children are included; grandchildren require separate calls.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Parent task GID.
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        Paginated list of subtask resources.

    Raises:
        404: Parent task not found or not accessible.
    """
    try:
        result = await task_service.list_subtasks(
            client, gid, limit=limit, offset=offset
        )
    except ServiceError as e:
        raise_service_error(request_id, e)

    pagination = PaginationMeta(
        limit=limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
    )

    return build_success_response(
        data=result.data,  # type: ignore[arg-type]
        request_id=request_id,
        pagination=pagination,
    )


@router.get(
    "/{gid}/dependents",
    summary="List tasks that depend on a task",
    response_description="Paginated list of dependent tasks",
    response_model=SuccessResponse[list[AsanaResource]],
    responses=entity_responses(),
)
async def list_dependents(
    gid: GidStr,
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
) -> SuccessResponse[list[AsanaResource]]:
    """List tasks that depend on (are blocked by) this task.

    Returns tasks that have marked this task as a prerequisite. These are
    the tasks that cannot start until this one is completed.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Task GID to get dependents for.
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        Paginated list of dependent task resources.

    Raises:
        404: Task not found or not accessible.
    """
    try:
        result = await task_service.list_dependents(
            client, gid, limit=limit, offset=offset
        )
    except ServiceError as e:
        raise_service_error(request_id, e)

    pagination = PaginationMeta(
        limit=limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
    )

    return build_success_response(
        data=result.data,  # type: ignore[arg-type]
        request_id=request_id,
        pagination=pagination,
    )


# T4: POST /tasks/{gid}/duplicate - Duplicate task
@router.post(
    "/{gid}/duplicate",
    summary="Duplicate a task",
    response_description="Newly duplicated task details",
    response_model=SuccessResponse[AsanaResource],
    status_code=status.HTTP_201_CREATED,
    responses={**entity_responses(), **mutation_responses()},
)
async def duplicate_task(
    gid: GidStr,
    body: DuplicateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Duplicate a task with a new name.

    Creates a copy of the task in the same project and section. The
    duplicate inherits the source task's description, assignee, and due
    date but gets the name provided in the request body.

    Requires Bearer token authentication (JWT or PAT).

    Creates a new task with a new GID in the same project and section.
    Inherits description, assignee, and due date. Does NOT duplicate
    subtasks, tags, or custom field values.

    Args:
        gid: GID of the source task to duplicate.
        body: ``name`` for the new duplicate task.

    Returns:
        The newly created duplicate task resource (HTTP 201).

    Raises:
        404: Source task not found or not accessible.
    """
    try:
        task = await task_service.duplicate_task(client, gid, body.name)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task, request_id=request_id)  # type: ignore[arg-type]


# --- Tags ---


# T5: POST /tasks/{gid}/tags - Add tag
@router.post(
    "/{gid}/tags",
    summary="Add a tag to a task",
    response_description="Updated task with new tag",
    response_model=SuccessResponse[AsanaResource],
    responses={**entity_responses(), **mutation_responses()},
)
async def add_tag(
    gid: GidStr,
    body: AddTagRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Add an existing Asana tag to a task.

    The tag must already exist in Asana. To create a tag, use the Asana
    API directly. Adding a tag that is already on the task is a no-op.

    Requires Bearer token authentication (JWT or PAT).

    **IDEMPOTENT**: Adding a tag that is already on the task is a no-op
    returning 200. The tag must already exist in Asana -- this endpoint
    does not create tags.

    Args:
        gid: Task GID.
        body: ``tag_gid`` — GID of the tag to apply.

    Returns:
        The updated task resource with the tag applied.

    Raises:
        404: Task or tag not found, or not accessible.
    """
    try:
        task_data = await task_service.add_tag(client, gid, body.tag_gid)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task_data, request_id=request_id)  # type: ignore[arg-type]


# T6: DELETE /tasks/{gid}/tags/{tag_gid} - Remove tag
@router.delete(
    "/{gid}/tags/{tag_gid}",
    summary="Remove a tag from a task",
    response_description="Updated task with tag removed",
    response_model=SuccessResponse[AsanaResource],
)
async def remove_tag(
    gid: GidStr,
    tag_gid: GidStr,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Remove a tag from a task.

    Removing a tag that is not on the task is a no-op. The tag itself is
    not deleted from Asana — only the association with this task is removed.

    Requires Bearer token authentication (JWT or PAT).

    **IDEMPOTENT**: Removing a tag that is not on the task is a no-op
    returning 200. The tag itself is not deleted from Asana -- only the
    association with this task is removed.

    Args:
        gid: Task GID.
        tag_gid: GID of the tag to remove.

    Returns:
        The updated task resource with the tag removed.

    Raises:
        404: Task not found or not accessible.
    """
    try:
        task_data = await task_service.remove_tag(client, gid, tag_gid)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task_data, request_id=request_id)  # type: ignore[arg-type]


# --- Membership ---


# T7: POST /tasks/{gid}/section - Move to section
@router.post(
    "/{gid}/section",
    summary="Move a task to a section",
    response_description="Updated task with new section",
    response_model=SuccessResponse[AsanaResource],
)
async def move_to_section(
    gid: GidStr,
    body: MoveSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Move a task to a different section within a project.

    The task must already be a member of the specified project. Both
    ``section_gid`` and ``project_gid`` are required to unambiguously
    identify the destination (a task can belong to multiple projects).

    Requires Bearer token authentication (JWT or PAT).

    **CAUTION**: Moving a task to a different section may trigger lifecycle
    automations including workflow transitions and status changes. Requires
    both section_gid and project_gid. The task must already be a member of
    the specified project.

    Args:
        gid: Task GID.
        body: ``section_gid`` and ``project_gid`` for the destination.

    Returns:
        The updated task resource with the new section membership.

    Raises:
        404: Task, section, or project not found or not accessible.
    """
    try:
        task_data = await task_service.move_to_section(
            client, gid, body.section_gid, body.project_gid
        )
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task_data, request_id=request_id)  # type: ignore[arg-type]


# T8: PUT /tasks/{gid}/assignee - Set assignee
@router.put(
    "/{gid}/assignee",
    summary="Set or clear a task assignee",
    response_description="Updated task with new assignee",
    response_model=SuccessResponse[AsanaResource],
)
async def set_assignee(
    gid: GidStr,
    body: SetAssigneeRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Set or clear the assignee of a task.

    Pass a valid user GID in ``assignee_gid`` to assign the task. Pass
    ``null`` to remove the current assignee and leave the task unassigned.

    Requires Bearer token authentication (JWT or PAT).

    Assignee change triggers Asana notifications to the new assignee.
    Pass null to unassign the task.

    Args:
        gid: Task GID.
        body: ``assignee_gid`` — user GID to assign, or ``null`` to unassign.

    Returns:
        The updated task resource with the new assignee.

    Raises:
        404: Task or user not found, or not accessible.
    """
    try:
        task = await task_service.set_assignee(client, gid, body.assignee_gid)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task, request_id=request_id)  # type: ignore[arg-type]


# T9: POST /tasks/{gid}/projects - Add to project
@router.post(
    "/{gid}/projects",
    summary="Add a task to a project",
    response_description="Updated task with new project membership",
    response_model=SuccessResponse[AsanaResource],
)
async def add_to_project(
    gid: GidStr,
    body: AddToProjectRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Add a task to an additional project.

    A task can belong to multiple projects. This endpoint adds the task to
    the specified project without removing it from existing projects.

    Requires Bearer token authentication (JWT or PAT).

    **IDEMPOTENT**: Adding a task to a project it already belongs to is a
    no-op. A task can belong to multiple projects simultaneously. This does
    not change the task's section within the project.

    Args:
        gid: Task GID.
        body: ``project_gid`` — project to add the task to.

    Returns:
        The updated task resource with the new project membership.

    Raises:
        404: Task or project not found, or not accessible.
    """
    try:
        task_data = await task_service.add_to_project(client, gid, body.project_gid)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task_data, request_id=request_id)  # type: ignore[arg-type]


# T10: DELETE /tasks/{gid}/projects/{project_gid} - Remove from project
@router.delete(
    "/{gid}/projects/{project_gid}",
    summary="Remove a task from a project",
    response_description="Updated task with project membership removed",
    response_model=SuccessResponse[AsanaResource],
)
async def remove_from_project(
    gid: GidStr,
    project_gid: GidStr,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Remove a task from a project without deleting the task.

    If the task belongs to multiple projects, it is removed only from the
    specified project. The task itself is not deleted and remains accessible
    from other projects it belongs to.

    Requires Bearer token authentication (JWT or PAT).

    Removes the task from the specified project without deleting the task.
    If this is the task's last project, it becomes uncategorized but remains
    accessible in the workspace.

    Args:
        gid: Task GID.
        project_gid: GID of the project to remove the task from.

    Returns:
        The updated task resource with the project membership removed.

    Raises:
        404: Task or project not found, or not accessible.
    """
    try:
        task_data = await task_service.remove_from_project(client, gid, project_gid)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=task_data, request_id=request_id)  # type: ignore[arg-type]


__all__ = ["router"]
