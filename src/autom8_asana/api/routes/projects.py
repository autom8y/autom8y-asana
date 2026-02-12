"""Projects REST endpoints.

This module provides REST endpoints for Asana Project operations,
wrapping the SDK ProjectsClient with thin API handlers.

Endpoints:
- GET /api/v1/projects?workspace={gid} - List projects by workspace (paginated)
- GET /api/v1/projects/{gid} - Get project by GID
- POST /api/v1/projects - Create project
- PUT /api/v1/projects/{gid} - Update project
- DELETE /api/v1/projects/{gid} - Delete project
- GET /api/v1/projects/{gid}/sections - List sections in project (paginated)
- POST /api/v1/projects/{gid}/members - Add members to project
- DELETE /api/v1/projects/{gid}/members - Remove members from project

Per TDD-ASANA-SATELLITE:
- All endpoints require Bearer token authentication
- Responses use standard envelope: {"data": ..., "meta": {...}}
- List endpoints support cursor-based pagination
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.models import (
    AsanaResource,
    CreateProjectRequest,
    MembersRequest,
    PaginationMeta,
    SuccessResponse,
    UpdateProjectRequest,
    build_success_response,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


# --- Core CRUD Endpoints ---


@router.get(
    "",
    summary="List projects by workspace",
    response_model=SuccessResponse[list[AsanaResource]],
)
async def list_projects(
    client: AsanaClientDualMode,
    request_id: RequestId,
    workspace: Annotated[
        str,
        Query(description="Workspace GID to list projects from"),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
) -> SuccessResponse[list[AsanaResource]]:
    """List projects by workspace with pagination.

    Per FR-API-PROJ-005: List projects by workspace.

    Returns a paginated list of projects from the specified workspace.

    Args:
        workspace: Workspace GID to list projects from (required).
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of projects with pagination metadata.
    """
    params: dict[str, Any] = {
        "workspace": workspace,
        "limit": min(limit, MAX_LIMIT),
    }
    if offset:
        params["offset"] = offset

    data, next_offset = await client._http.get_paginated("/projects", params=params)

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
    summary="Get project by GID",
    response_model=SuccessResponse[AsanaResource],
)
async def get_project(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    opt_fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of fields to include",
            example="name,notes,owner,team",
        ),
    ] = None,
) -> SuccessResponse[AsanaResource]:
    """Get a project by its GID.

    Per FR-API-PROJ-001: Get project by GID.

    Args:
        gid: Asana project GID.
        opt_fields: Comma-separated list of fields to include in response.

    Returns:
        Project data with requested fields.
    """
    fields_list: list[str] | None = None
    if opt_fields:
        fields_list = [f.strip() for f in opt_fields.split(",")]

    project = await client.projects.get_async(gid, opt_fields=fields_list, raw=True)
    return build_success_response(data=project, request_id=request_id)


@router.post(
    "",
    summary="Create a new project",
    response_model=SuccessResponse[AsanaResource],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    body: CreateProjectRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Create a new project.

    Per FR-API-PROJ-002: Create project with name, workspace, and optional team.

    Args:
        body: Project creation parameters.

    Returns:
        Created project data.
    """
    kwargs: dict[str, Any] = {}
    if body.team:
        kwargs["team"] = body.team

    project = await client.projects.create_async(
        name=body.name,
        workspace=body.workspace,
        raw=True,
        **kwargs,
    )
    return build_success_response(data=project, request_id=request_id)


@router.put(
    "/{gid}",
    summary="Update a project",
    response_model=SuccessResponse[AsanaResource],
)
async def update_project(
    gid: str,
    body: UpdateProjectRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Update an existing project.

    Per FR-API-PROJ-003: Update project fields.

    Only provided fields are updated; omitted fields retain their values.

    Args:
        gid: Asana project GID.
        body: Fields to update.

    Returns:
        Updated project data.
    """
    kwargs: dict[str, Any] = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.notes is not None:
        kwargs["notes"] = body.notes
    if body.archived is not None:
        kwargs["archived"] = body.archived

    if not kwargs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_PARAMETER",
                "message": "At least one field must be provided for update",
            },
        )

    project = await client.projects.update_async(gid, raw=True, **kwargs)
    return build_success_response(data=project, request_id=request_id)


@router.delete(
    "/{gid}",
    summary="Delete a project",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    gid: str,
    client: AsanaClientDualMode,
) -> None:
    """Delete a project.

    Per FR-API-PROJ-004: Delete project by GID.

    Args:
        gid: Asana project GID.

    Returns:
        No content on success.
    """
    await client.projects.delete_async(gid)


# --- Section-related Operations ---


@router.get(
    "/{gid}/sections",
    summary="List sections in project",
    response_model=SuccessResponse[list[AsanaResource]],
)
async def list_sections(
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
) -> SuccessResponse[list[AsanaResource]]:
    """List sections in a project with pagination.

    Per FR-API-PROJ-006: List sections in project.

    Args:
        gid: Project GID.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of sections with pagination metadata.
    """
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if offset:
        params["offset"] = offset

    data, next_offset = await client._http.get_paginated(
        f"/projects/{gid}/sections",
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


# --- Membership Operations ---


@router.post(
    "/{gid}/members",
    summary="Add members to project",
    response_model=SuccessResponse[AsanaResource],
)
async def add_members(
    gid: str,
    body: MembersRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Add members to a project.

    Per FR-API-PROJ-007: Add members to project.

    Args:
        gid: Project GID.
        body: List of user GIDs to add.

    Returns:
        Updated project data.
    """
    project = await client.projects.add_members_async(
        gid, members=body.members, raw=True
    )
    return build_success_response(data=project, request_id=request_id)


@router.delete(
    "/{gid}/members",
    summary="Remove members from project",
    response_model=SuccessResponse[AsanaResource],
)
async def remove_members(
    gid: str,
    body: MembersRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Remove members from a project.

    Per FR-API-PROJ-008: Remove members from project.

    Args:
        gid: Project GID.
        body: List of user GIDs to remove.

    Returns:
        Updated project data.
    """
    project = await client.projects.remove_members_async(
        gid, members=body.members, raw=True
    )
    return build_success_response(data=project, request_id=request_id)


__all__ = ["router"]
