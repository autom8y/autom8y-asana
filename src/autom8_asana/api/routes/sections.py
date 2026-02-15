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

from fastapi import APIRouter, status

from autom8_asana.api.dependencies import (
    AsanaClientDualMode,
    RequestId,
    SectionServiceDep,
)
from autom8_asana.api.errors import raise_service_error
from autom8_asana.api.models import (
    AddTaskToSectionRequest,
    AsanaResource,
    CreateSectionRequest,
    ReorderSectionRequest,
    SuccessResponse,
    UpdateSectionRequest,
    build_success_response,
)
from autom8_asana.services.errors import ServiceError

router = APIRouter(prefix="/api/v1/sections", tags=["sections"])


# --- Core CRUD Endpoints ---


@router.get(
    "/{gid}",
    summary="Get section by GID",
    response_model=SuccessResponse[AsanaResource],
)
async def get_section(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Get a section by its GID.

    Args:
        gid: Asana section GID.

    Returns:
        Section data.
    """
    try:
        section = await section_service.get_section(client, gid)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=section, request_id=request_id)


# S1: POST /sections - Create section
@router.post(
    "",
    summary="Create a new section",
    response_model=SuccessResponse[AsanaResource],
    status_code=status.HTTP_201_CREATED,
)
async def create_section(
    body: CreateSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Create a new section in a project.

    Args:
        body: Section creation parameters.

    Returns:
        Created section data.
    """
    try:
        section = await section_service.create_section(
            client, name=body.name, project=body.project
        )
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=section, request_id=request_id)


# S2: PUT /sections/{gid} - Update section
@router.put(
    "/{gid}",
    summary="Update a section",
    response_model=SuccessResponse[AsanaResource],
)
async def update_section(
    gid: str,
    body: UpdateSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> SuccessResponse[AsanaResource]:
    """Update a section (rename).

    Args:
        gid: Asana section GID.
        body: Fields to update.

    Returns:
        Updated section data.
    """
    try:
        section = await section_service.update_section(client, gid, body.name)
    except ServiceError as e:
        raise_service_error(request_id, e)
    return build_success_response(data=section, request_id=request_id)


# S3: DELETE /sections/{gid} - Delete section
@router.delete(
    "/{gid}",
    summary="Delete a section",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_section(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> None:
    """Delete a section.

    Args:
        gid: Asana section GID.

    Returns:
        No content on success.
    """
    try:
        await section_service.delete_section(client, gid)
    except ServiceError as e:
        raise_service_error(request_id, e)


# --- Task Operations ---


# S4: POST /sections/{gid}/tasks - Add task to section
@router.post(
    "/{gid}/tasks",
    summary="Add task to section",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_task_to_section(
    gid: str,
    body: AddTaskToSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> None:
    """Add a task to a section.

    Args:
        gid: Section GID.
        body: Task GID to add.

    Returns:
        No content on success.
    """
    try:
        await section_service.add_task(client, gid, body.task_gid)
    except ServiceError as e:
        raise_service_error(request_id, e)


# --- Reorder Operations ---


@router.post(
    "/{gid}/reorder",
    summary="Reorder section within project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reorder_section(
    gid: str,
    body: ReorderSectionRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    section_service: SectionServiceDep,
) -> None:
    """Reorder a section within a project.

    Moves the section to a new position. Exactly one of before_section
    or after_section must be provided.

    Args:
        gid: Section GID to reorder.
        body: Reorder parameters including project and position.

    Returns:
        No content on success.

    Raises:
        400: Neither or both of before_section/after_section provided.
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
