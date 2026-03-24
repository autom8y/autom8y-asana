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
    AsanaResource,
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
    summary="List accessible workspaces",
    response_description="Paginated list of workspaces",
    response_model=SuccessResponse[list[AsanaResource]],
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
) -> SuccessResponse[list[AsanaResource]]:
    """List all Asana workspaces accessible to the authenticated user.

    Returns workspaces the token owner can access. In most configurations
    this is a single organization workspace. Use the returned GIDs with
    ``GET /api/v1/projects``, ``GET /api/v1/users``, and task creation.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        Paginated list of workspace resources with ``gid``, ``name``,
        ``is_organization``, and ``email_domains``.
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
    summary="Get a workspace by GID",
    response_description="Workspace details",
    response_model=SuccessResponse[AsanaResource],
)
async def get_workspace(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Get a single workspace by its Asana GID.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Asana workspace GID.

    Returns:
        Workspace resource with ``gid``, ``name``, ``is_organization``,
        and ``email_domains``.

    Raises:
        404: Workspace not found or not accessible with the provided token.
    """
    workspace = await client.workspaces.get_async(gid, raw=True)
    return build_success_response(data=workspace, request_id=request_id)


__all__ = ["router"]
