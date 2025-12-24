"""Workspaces REST endpoints.

This module provides REST endpoints for Asana Workspace operations,
wrapping the SDK WorkspacesClient with thin API handlers.

Endpoints:
- GET /api/v1/workspaces - List all workspaces (paginated)
- GET /api/v1/workspaces/{gid} - Get workspace by GID

Per TDD-ASANA-SATELLITE:
- All endpoints require Bearer token authentication
- Responses use standard envelope: {"data": ..., "meta": {...}}
- List endpoints support cursor-based pagination
"""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.models import (
    PaginationMeta,
    SuccessResponse,
    build_success_response,
)

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


@router.get(
    "",
    summary="List all workspaces",
    response_model=SuccessResponse[list[dict[str, Any]]],
)
async def list_workspaces(
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
    """List all workspaces accessible to the authenticated user.

    Returns a paginated list of workspaces the user has access to.

    Args:
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of workspaces with pagination metadata.
    """
    # Build params for SDK call
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if offset:
        params["offset"] = offset

    # Use the HTTP client directly for paginated requests
    # to get the next_offset from response
    data, next_offset = await client._http.get_paginated(
        "/workspaces",
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
    "/{gid}",
    summary="Get workspace by GID",
    response_model=SuccessResponse[dict[str, Any]],
)
async def get_workspace(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[dict[str, Any]]:
    """Get a workspace by its GID.

    Args:
        gid: Asana workspace GID.

    Returns:
        Workspace data with gid, name, is_organization, and email_domains.
    """
    workspace = await client.workspaces.get_async(gid, raw=True)
    return build_success_response(data=workspace, request_id=request_id)


__all__ = ["router"]
