"""Sections REST endpoints delegating to SectionService.

This module provides REST endpoints for Asana Section operations,
delegating business logic to SectionService per TDD-I2-SERVICE-WIRING-001.

Endpoints:
- GET /api/v1/sections/{gid} - Get section by GID
- POST /api/v1/sections - Create section in project
- PUT /api/v1/sections/{gid} - Update section (rename)
- DELETE /api/v1/sections/{gid} - Delete section
- POST /api/v1/sections/{gid}/tasks - Add task to section
- POST /api/v1/sections/{gid}/reorder - Reorder section within project

Per TDD-ASANA-SATELLITE:
- All endpoints require Bearer token authentication
- Responses use standard envelope: {"data": ..., "meta": {...}}
"""

from fastapi import status

from autom8_asana.api.dependencies import (
    AsanaClientDualMode,
    RequestId,
    SectionServiceDep,
)
from autom8_asana.api.error_responses import (
    entity_responses,
    mutation_responses,
)
from autom8_asana.api.errors import raise_service_error
from autom8_asana.api.models import (
    AddTaskToSectionRequest,
    AsanaResource,
    CreateSectionRequest,
    GidStr,
    ReorderSectionRequest,
    SuccessResponse,
    UpdateSectionRequest,
    build_success_response,
)
from autom8_asana.api.routes._security import pat_router
from autom8_asana.services.errors import ServiceError

router = pat_router(prefix="/api/v1/sections", tags=["sections"])


# --- Core CRUD Endpoints ---


@router.get(
    "/{gid}",
    summary="Get a section by GID",
    response_description="Section details",
    response_model=SuccessResponse[AsanaResource],
    responses=entity_responses(),
)
async def get_section(
    gid: GidStr,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Get a single section by its Asana GID.

    Returns the section name, GID, and the project it belongs to.
    To list all sections in a project, use
    ``GET /api/v1/projects/{gid}/sections``.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Asana section GID.

    Returns:
        Section resource with name and parent project reference.

    Raises:
        404: Section not found or not accessible.
    """
    try:
        section = await section_service.get_section(client, gid)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=section, request_id=request_id)  # type: ignore[arg-type]


# S1: POST /sections - Create section
@router.post(
    "",
    summary="Create a section in a project",
    response_description="Created section details",
    response_model=SuccessResponse[AsanaResource],
    status_code=status.HTTP_201_CREATED,
    responses=mutation_responses(),
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "section"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def create_section(
    body: CreateSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Create a new section within an existing project.

    Both ``name`` and ``project`` (project GID) are required. The section
    is appended at the end of the project's section list. To reorder it,
    call ``POST /api/v1/sections/{gid}/reorder`` after creation.

    Requires Bearer token authentication (JWT or PAT).

    New sections are appended at the end of the project. No duplicate name
    checking is performed. To position the section, call
    ``POST /api/v1/sections/{gid}/reorder`` after creation.

    Args:
        body: ``name`` and ``project`` GID for the new section.

    Returns:
        The newly created section resource (HTTP 201).

    Raises:
        404: Project not found or not accessible.
    """
    try:
        section = await section_service.create_section(
            client, name=body.name, project=body.project
        )
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=section, request_id=request_id)  # type: ignore[arg-type]


# S2: PUT /sections/{gid} - Update section
@router.put(
    "/{gid}",
    summary="Rename a section",
    response_description="Updated section details",
    response_model=SuccessResponse[AsanaResource],
    responses={**entity_responses(), **mutation_responses()},
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "section"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def update_section(
    gid: GidStr,
    body: UpdateSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Rename an existing section.

    Currently only ``name`` can be updated. The section's position within
    the project is unchanged. To reorder sections, use
    ``POST /api/v1/sections/{gid}/reorder``.

    Requires Bearer token authentication (JWT or PAT).

    Name-only update. Does not reorder the section within the project.
    Use ``POST /api/v1/sections/{gid}/reorder`` to change position.

    Args:
        gid: Asana section GID.
        body: ``name`` — new display name for the section.

    Returns:
        The updated section resource.

    Raises:
        404: Section not found or not accessible.
    """
    try:
        section = await section_service.update_section(client, gid, body.name)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=section, request_id=request_id)  # type: ignore[arg-type]


# S3: DELETE /sections/{gid} - Delete section
@router.delete(
    "/{gid}",
    summary="Delete a section",
    response_description="No content",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=entity_responses(),
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "section"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def delete_section(
    gid: GidStr,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> None:
    """Permanently delete a section from its project.

    Tasks within the section are not deleted — they become uncategorized
    within the project. This action is irreversible.

    Requires Bearer token authentication (JWT or PAT).

    **IRREVERSIBLE**: Permanently deletes this section. Tasks within the
    section are NOT deleted but become uncategorized within the project.
    The section GID becomes permanently invalid.

    Args:
        gid: Asana section GID.

    Returns:
        204 No Content on success.

    Raises:
        404: Section not found or not accessible.
    """
    try:
        await section_service.delete_section(client, gid)
    except ServiceError as e:
        raise_service_error(request_id, e)


# --- Task Operations ---


# S4: POST /sections/{gid}/tasks - Add task to section
@router.post(
    "/{gid}/tasks",
    summary="Add a task to a section",
    response_description="No content",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**entity_responses(), **mutation_responses()},
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "task"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def add_task_to_section(
    gid: GidStr,
    body: AddTaskToSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> None:
    """Add a task to a section, moving it within its project.

    The task must already be a member of the project that contains this
    section. To move a task across projects, use
    ``POST /api/v1/tasks/{gid}/projects`` first.

    Requires Bearer token authentication (JWT or PAT).

    The task must already be in the project that owns this section. To move
    a task across projects, add it to the target project first via
    ``POST /api/v1/tasks/{gid}/projects``.

    Args:
        gid: Section GID.
        body: ``task_gid`` — GID of the task to add.

    Returns:
        204 No Content on success.

    Raises:
        404: Section or task not found, or task not in the section's project.
    """
    try:
        await section_service.add_task(client, gid, body.task_gid)
    except ServiceError as e:
        raise_service_error(request_id, e)


# --- Reorder Operations ---


@router.post(
    "/{gid}/reorder",
    summary="Reorder a section within a project",
    response_description="No content",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**entity_responses(), **mutation_responses()},
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "section"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def reorder_section(
    gid: GidStr,
    body: ReorderSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> None:
    """Move a section to a new position within a project.

    Exactly one of ``before_section`` or ``after_section`` must be provided:

    - ``before_section``: places this section immediately before the
      specified section.
    - ``after_section``: places this section immediately after the
      specified section.

    Both the moving section and the reference section must belong to the
    same project (identified by ``project_gid``).

    Requires Bearer token authentication (JWT or PAT).

    Moves the section to a new position. Exactly one of before_section or
    after_section must be provided. Both sections must be in the same
    project.

    Args:
        gid: Section GID to reorder.
        body: ``project_gid`` plus exactly one of ``before_section`` or
            ``after_section``.

    Returns:
        204 No Content on success.

    Raises:
        400: Neither or both of before_section/after_section provided.
        404: Section or project not found or not accessible.
    """
    try:
        await section_service.reorder(
            client,
            gid,
            body.project_gid,
            before_section=body.before_section,
            after_section=body.after_section,
        )
    except ServiceError as e:
        raise_service_error(request_id, e)


__all__ = ["router"]
