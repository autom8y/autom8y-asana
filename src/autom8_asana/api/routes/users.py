"""Users REST endpoints.

This module provides REST endpoints for Asana User operations,
wrapping the SDK UsersClient with thin API handlers.

Endpoints:
- GET /api/v1/users/me - Current authenticated user
- GET /api/v1/users/{gid} - Get user by GID
- GET /api/v1/users?workspace={gid} - List users in workspace (paginated)

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

router = APIRouter(prefix="/api/v1/users", tags=["users"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


@router.get(
    "/me",
    summary="Get current authenticated user",
    response_model=SuccessResponse[dict[str, Any]],
)
async def get_current_user(
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[dict[str, Any]]:
    """Get the current authenticated user.

    Returns the user associated with the provided PAT token.

    Returns:
        User data with gid, name, email, and workspaces.
    """
    user = await client.users.me_async(raw=True)
    return build_success_response(data=user, request_id=request_id)


@router.get(
    "/{gid}",
    summary="Get user by GID",
    response_model=SuccessResponse[dict[str, Any]],
)
async def get_user(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[dict[str, Any]]:
    """Get a user by their GID.

    Args:
        gid: Asana user GID.

    Returns:
        User data with gid, name, email, and workspaces.
    """
    user = await client.users.get_async(gid, raw=True)
    return build_success_response(data=user, request_id=request_id)


@router.get(
    "",
    summary="List users in workspace",
    response_model=SuccessResponse[list[dict[str, Any]]],
)
async def list_users(
    client: AsanaClientDualMode,
    request_id: RequestId,
    workspace: Annotated[
        str,
        Query(description="Workspace GID to list users from"),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
) -> SuccessResponse[list[dict[str, Any]]]:
    """List users in a workspace with pagination.

    Returns a paginated list of users in the specified workspace.

    Args:
        workspace: Workspace GID (required).
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        List of users with pagination metadata.
    """
    # Build params for SDK call
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if offset:
        params["offset"] = offset

    # Use the HTTP client directly for paginated requests
    # to get the next_offset from response
    data, next_offset = await client._http.get_paginated(
        f"/workspaces/{workspace}/users",
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


__all__ = ["router"]
