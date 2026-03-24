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
from autom8_asana.api.error_responses import (
    authenticated_responses,
    entity_responses,
)
from autom8_asana.api.models import (
    AsanaResource,
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
    summary="Get the current authenticated user",
    response_description="Current user profile",
    response_model=SuccessResponse[AsanaResource],
    responses=authenticated_responses(),
)
async def get_current_user(
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Get the user associated with the Bearer token in the request.

    Useful for resolving the token's owner GID before making workspace-
    or project-scoped calls. The returned GID can be passed to
    ``GET /api/v1/users/{gid}`` or used as an assignee value.

    Requires Bearer token authentication (JWT or PAT).

    Returns:
        Current user resource with ``gid``, ``name``, ``email``,
        and ``workspaces``.
    """
    user = await client.users.me_async(raw=True)
    return build_success_response(data=user, request_id=request_id)


@router.get(
    "/{gid}",
    summary="Get a user by GID",
    response_description="User profile",
    response_model=SuccessResponse[AsanaResource],
    responses=entity_responses(),
)
async def get_user(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Get a specific Asana user by their GID.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Asana user GID.

    Returns:
        User resource with ``gid``, ``name``, ``email``, and ``workspaces``.

    Raises:
        404: User not found or not accessible with the provided token.
    """
    user = await client.users.get_async(gid, raw=True)
    return build_success_response(data=user, request_id=request_id)


@router.get(
    "",
    summary="List users in a workspace",
    response_description="Paginated list of workspace users",
    response_model=SuccessResponse[list[AsanaResource]],
    responses=authenticated_responses(),
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
) -> SuccessResponse[list[AsanaResource]]:
    """List all users in a workspace with cursor-based pagination.

    The ``workspace`` query parameter is required. Returns all users
    with access to the specified workspace — useful for populating
    assignee pickers or resolving names to GIDs.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        workspace: Workspace GID (required).
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        Paginated list of user resources with ``gid``, ``name``, and
        ``email``.
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
