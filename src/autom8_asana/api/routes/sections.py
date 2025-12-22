"""Sections REST endpoints.

This module provides REST endpoints for Asana Section operations,
wrapping the SDK SectionsClient with thin API handlers.

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

from typing import Any

from fastapi import APIRouter, HTTPException, status

from autom8_asana.api.dependencies import AsanaClientDep, RequestId
from autom8_asana.api.models import (
    AddTaskToSectionRequest,
    CreateSectionRequest,
    ReorderSectionRequest,
    SuccessResponse,
    UpdateSectionRequest,
    build_success_response,
)

router = APIRouter(prefix="/api/v1/sections", tags=["sections"])


# --- Core CRUD Endpoints ---


@router.get(
    "/{gid}",
    summary="Get section by GID",
    response_model=SuccessResponse[dict[str, Any]],
)
async def get_section(
    gid: str,
    client: AsanaClientDep,
    request_id: RequestId,
) -> SuccessResponse[dict[str, Any]]:
    """Get a section by its GID.

    Per FR-API-SECT-001: Get section by GID.

    Args:
        gid: Asana section GID.

    Returns:
        Section data.
    """
    section = await client.sections.get_async(gid, raw=True)
    return build_success_response(data=section, request_id=request_id)


@router.post(
    "",
    summary="Create a new section",
    response_model=SuccessResponse[dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
)
async def create_section(
    body: CreateSectionRequest,
    client: AsanaClientDep,
    request_id: RequestId,
) -> SuccessResponse[dict[str, Any]]:
    """Create a new section in a project.

    Per FR-API-SECT-002: Create section with name and project.

    Args:
        body: Section creation parameters.

    Returns:
        Created section data.
    """
    section = await client.sections.create_async(
        name=body.name,
        project=body.project,
        raw=True,
    )
    return build_success_response(data=section, request_id=request_id)


@router.put(
    "/{gid}",
    summary="Update a section",
    response_model=SuccessResponse[dict[str, Any]],
)
async def update_section(
    gid: str,
    body: UpdateSectionRequest,
    client: AsanaClientDep,
    request_id: RequestId,
) -> SuccessResponse[dict[str, Any]]:
    """Update a section (rename).

    Per FR-API-SECT-003: Update section name.

    Args:
        gid: Asana section GID.
        body: Fields to update.

    Returns:
        Updated section data.
    """
    section = await client.sections.update_async(gid, raw=True, name=body.name)
    return build_success_response(data=section, request_id=request_id)


@router.delete(
    "/{gid}",
    summary="Delete a section",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_section(
    gid: str,
    client: AsanaClientDep,
) -> None:
    """Delete a section.

    Per FR-API-SECT-004: Delete section by GID.

    Args:
        gid: Asana section GID.

    Returns:
        No content on success.
    """
    await client.sections.delete_async(gid)


# --- Task Operations ---


@router.post(
    "/{gid}/tasks",
    summary="Add task to section",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_task_to_section(
    gid: str,
    body: AddTaskToSectionRequest,
    client: AsanaClientDep,
) -> None:
    """Add a task to a section.

    Per FR-API-SECT-005: Add task to section.

    Moves the task to the specified section. If the task is already
    in another section of the same project, it will be moved.

    Args:
        gid: Section GID.
        body: Task GID to add.

    Returns:
        No content on success.
    """
    await client.sections.add_task_async(gid, task=body.task_gid)


# --- Reorder Operations ---


@router.post(
    "/{gid}/reorder",
    summary="Reorder section within project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reorder_section(
    gid: str,
    body: ReorderSectionRequest,
    client: AsanaClientDep,
) -> None:
    """Reorder a section within a project.

    Per FR-API-SECT-006: Reorder section within project.

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
    if body.before_section is None and body.after_section is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'before_section' or 'after_section' must be provided",
        )

    if body.before_section is not None and body.after_section is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of 'before_section' or 'after_section' may be specified",
        )

    await client.sections.insert_section_async(
        body.project_gid,
        section=gid,
        before_section=body.before_section,
        after_section=body.after_section,
    )


__all__ = ["router"]
