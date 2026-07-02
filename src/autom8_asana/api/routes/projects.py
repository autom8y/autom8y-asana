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

from typing import Annotated, Any, cast

from fastapi import Depends, Query, Request, status

from autom8_asana import AsanaClient
from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.error_responses import (
    authenticated_responses,
    entity_responses,
    mutation_responses,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.exception_types import ApiServiceUnavailableError
from autom8_asana.api.models import (
    AsanaResource,
    CreateProjectRequest,
    GidStr,
    MembersRequest,
    PaginationMeta,
    SuccessResponse,
    UpdateProjectRequest,
    build_success_response,
)
from autom8_asana.api.routes._security import pat_router
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
from autom8_asana.core.project_registry import UNIT_PROJECT

router = pat_router(prefix="/api/v1/projects", tags=["projects"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


# ---------------------------------------------------------------------------
# Scoped, token-safe section-read capability (FORK-R REUSE branch, TDD §3.1)
# ---------------------------------------------------------------------------
# H2 (BOLA/IDOR): the section-list capability is pinned to a single-project
# allowlist. Only these project GIDs may have their sections listed through
# this route; every other ``{gid}`` fails closed (404). This removes the
# "any project" reach that made the route a wider BOLA/IDOR surface than the
# one cutover project the read-capability exists to serve.
SECTION_LIST_PROJECT_ALLOWLIST: frozenset[str] = frozenset({UNIT_PROJECT})


async def get_s2s_section_client(
    request: Request,
    _claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> AsanaClient:
    """Resolve a JWT-only (S2S) ``AsanaClient`` for the scoped section read.

    Structurally excludes the FORBIDDEN plaintext-PAT mode (the
    ``get_auth_context`` PAT branch at ``dependencies.py:139-148``):

    - ``require_service_claims`` rejects PAT tokens (401 SERVICE_TOKEN_REQUIRED)
      and requires a valid, short-lived S2S JWT (H1, H6).
    - The Asana credential is the *brokered bot PAT* resolved server-side via
      ``get_bot_pat()`` (``ASANA_PAT_ARN``). The caller's bearer token is never
      used as an Asana credential and the caller never materializes the
      plaintext PAT (H4, H5).

    Mirrors the JWT-only guard used by ``intake_create.py`` so this capability
    cannot fall back to caller-plaintext auth by construction.
    """
    # H5: fail closed if the brokered bot PAT cannot be resolved. Never leak an
    # unhandled BotPATError (500) and never silently degrade to plaintext.
    try:
        bot_pat = get_bot_pat()
    except BotPATError as exc:
        raise ApiServiceUnavailableError(
            "S2S_NOT_CONFIGURED",
            "Service-to-service authentication is not available",
        ) from exc
    pool = getattr(request.app.state, "client_pool", None)
    if pool is not None:
        return cast("AsanaClient", await pool.get_or_create(bot_pat, is_s2s=True))
    # Fallback: no pool (e.g. testing without lifespan).
    return AsanaClient(token=bot_pat)


# --- Core CRUD Endpoints ---


@router.get(
    "",
    summary="List projects in a workspace",
    response_description="Paginated list of projects",
    response_model=SuccessResponse[list[AsanaResource]],
    responses=authenticated_responses(),
)
async def list_projects(
    client: AsanaClientDualMode,
    request_id: RequestId,
    workspace: Annotated[
        GidStr,
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
    """List all projects in a workspace with cursor-based pagination.

    The ``workspace`` query parameter is required. Use ``offset`` from the
    previous response's ``meta.pagination.next_offset`` to page through
    large result sets.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        workspace: Workspace GID to list projects from (required).
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        Paginated list of project resources.
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
        data=data,  # type: ignore[arg-type]
        request_id=request_id,
        pagination=pagination,
    )


@router.get(
    "/{gid}",
    summary="Get a project by GID",
    response_description="Project details",
    response_model=SuccessResponse[AsanaResource],
    responses=entity_responses(),
)
async def get_project(
    gid: GidStr,
    client: AsanaClientDualMode,
    request_id: RequestId,
    opt_fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of fields to include",
            examples=["name,notes,owner,team"],
        ),
    ] = None,
) -> SuccessResponse[AsanaResource]:
    """Get a single project by its Asana GID.

    Use ``opt_fields`` to limit the response to specific fields
    (e.g. ``"name,notes,owner,team"``). When omitted, Asana returns its
    default field set.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Asana project GID.
        opt_fields: Comma-separated Asana field names to include.

    Returns:
        Project resource with the requested fields populated.

    Raises:
        404: Project not found or not accessible.
    """
    fields_list: list[str] | None = None
    if opt_fields:
        fields_list = [f.strip() for f in opt_fields.split(",")]

    project = await client.projects.get_async(gid, opt_fields=fields_list, raw=True)
    return build_success_response(data=project, request_id=request_id)  # type: ignore[arg-type]


@router.post(
    "",
    summary="Create a project",
    response_description="Created project details",
    response_model=SuccessResponse[AsanaResource],
    status_code=status.HTTP_201_CREATED,
    responses=mutation_responses(),
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "project"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def create_project(
    body: CreateProjectRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Create a new project in a workspace.

    Both ``name`` and ``workspace`` are required. Supply ``team`` to create
    the project under a specific Asana team within the workspace.

    Requires Bearer token authentication (JWT or PAT).

    No duplicate checking is performed. Calling this endpoint multiple
    times with the same parameters creates multiple distinct projects, each
    with a unique GID.

    Args:
        body: Project creation parameters (``name``, ``workspace``, ``team``).

    Returns:
        The newly created project resource (HTTP 201).
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
    return build_success_response(data=project, request_id=request_id)  # type: ignore[arg-type]


@router.put(
    "/{gid}",
    summary="Update a project",
    response_description="Updated project details",
    response_model=SuccessResponse[AsanaResource],
    responses={**entity_responses(), **mutation_responses()},
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "project"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def update_project(
    gid: GidStr,
    body: UpdateProjectRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Update fields on an existing project.

    This is a partial update: only fields included in the request body are
    modified. Omitted fields retain their current values. At least one of
    ``name``, ``notes``, or ``archived`` must be provided.

    Requires Bearer token authentication (JWT or PAT).

    Setting archived=true hides the project from Asana UI but preserves all
    data. Tasks, sections, and memberships remain accessible via API.
    Archiving is reversible (set archived=false).

    Args:
        gid: Asana project GID.
        body: Fields to update (``name``, ``notes``, ``archived``).

    Returns:
        The updated project resource.

    Raises:
        400: No fields provided in the request body.
        404: Project not found or not accessible.
    """
    kwargs: dict[str, Any] = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.notes is not None:
        kwargs["notes"] = body.notes
    if body.archived is not None:
        kwargs["archived"] = body.archived

    if not kwargs:
        raise_api_error(
            request_id,
            status.HTTP_400_BAD_REQUEST,
            "INVALID_PARAMETER",
            "At least one field must be provided for update",
        )

    project = await client.projects.update_async(gid, raw=True, **kwargs)
    return build_success_response(data=project, request_id=request_id)  # type: ignore[arg-type]


@router.delete(
    "/{gid}",
    summary="Delete a project",
    response_description="No content",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=entity_responses(),
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "project"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def delete_project(
    gid: GidStr,
    client: AsanaClientDualMode,
) -> None:
    """Permanently delete a project from Asana.

    This action is irreversible. All tasks, sections, and memberships
    within the project are removed. Consider archiving (``PUT /projects/{gid}``
    with ``archived: true``) if you want to preserve the data.

    Requires Bearer token authentication (JWT or PAT).

    **IRREVERSIBLE**: Permanently deletes this project, all sections, and
    removes all task memberships. Tasks are NOT deleted but lose their
    project association. Consider archiving (PUT with archived=true) instead.

    Args:
        gid: Asana project GID.

    Returns:
        204 No Content on success.

    Raises:
        404: Project not found or not accessible.
    """
    await client.projects.delete_async(gid)  # type: ignore[attr-defined]


# --- Section-related Operations ---


@router.get(
    "/{gid}/sections",
    summary="List sections in the pinned cutover project (S2S, scoped)",
    response_description="Paginated list of sections",
    response_model=SuccessResponse[list[AsanaResource]],
    responses=entity_responses(),
)
async def list_sections(
    gid: GidStr,
    client: Annotated[AsanaClient, Depends(get_s2s_section_client)],
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
    """List sections within the pinned cutover project (token-safe scoped read).

    This is the token-safe section-read capability (FORK-R REUSE branch). It is
    hardened against the credential-topology risks gating SCAR-REG-001:

    - **H1 auth**: requires a valid, short-lived S2S JWT via
      ``get_s2s_section_client`` → ``require_service_claims``. Unauthenticated
      requests and PAT tokens fail closed (401); the forbidden plaintext-PAT
      mode is impossible by construction.
    - **H2 BOLA/IDOR**: ``{gid}`` must be in ``SECTION_LIST_PROJECT_ALLOWLIST``
      (integer-validated by ``GidStr`` in production); any other project fails
      closed (404).
    - **H3 path/verb**: GET-only; the outbound Asana URL is built server-side
      from the allowlisted ``{gid}`` (no caller-supplied URL; method-override
      headers are not honored).
    - **H4 log hygiene**: the bot PAT is brokered server-side and never logged.

    Args:
        gid: Project GID (must be allowlisted).
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.

    Returns:
        Paginated list of section resources in display order.

    Raises:
        404: Project GID is not in the scoped allowlist (or not found).
    """
    # H2: BOLA/IDOR guard — fail closed for any non-allowlisted project GID.
    # 404 (not 403) avoids confirming the existence of other projects.
    if gid not in SECTION_LIST_PROJECT_ALLOWLIST:
        raise_api_error(
            request_id=request_id,
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Sections are not available for the requested project.",
        )

    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if offset:
        params["offset"] = offset

    # H3: outbound URL constructed server-side from the allowlisted gid.
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
        data=data,  # type: ignore[arg-type]
        request_id=request_id,
        pagination=pagination,
    )


# --- Membership Operations ---


@router.post(
    "/{gid}/members",
    summary="Add members to a project",
    response_description="Updated project with new members",
    response_model=SuccessResponse[AsanaResource],
    responses={**entity_responses(), **mutation_responses()},
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "project"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def add_members(
    gid: GidStr,
    body: MembersRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Add one or more users as members of a project.

    Provide a list of user GIDs in ``members``. Users already on the project
    are not duplicated. Members gain visibility and task assignment access
    within the project.

    Requires Bearer token authentication (JWT or PAT).

    **IDEMPOTENT**: Adding a user who is already a project member is a
    no-op. Added members gain immediate visibility and task assignment
    access.

    Args:
        gid: Project GID.
        body: ``members`` — list of user GIDs to add.

    Returns:
        The updated project resource with the new member list.

    Raises:
        404: Project or one or more users not found or not accessible.
    """
    project = await client.projects.add_members_async(gid, members=body.members, raw=True)
    return build_success_response(data=project, request_id=request_id)  # type: ignore[arg-type]


@router.delete(
    "/{gid}/members",
    summary="Remove members from a project",
    response_description="Updated project with members removed",
    response_model=SuccessResponse[AsanaResource],
    responses={**entity_responses(), **mutation_responses()},
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "project"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def remove_members(
    gid: GidStr,
    body: MembersRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
) -> SuccessResponse[AsanaResource]:
    """Remove one or more members from a project.

    Removing a user who is not a member is a no-op. The removed users
    lose access to the project but their tasks within it are not deleted.

    Requires Bearer token authentication (JWT or PAT).

    **IDEMPOTENT**: Removing a user who is not a project member is a no-op.
    Removed users lose project access but their assigned tasks within the
    project are preserved.

    Args:
        gid: Project GID.
        body: ``members`` — list of user GIDs to remove.

    Returns:
        The updated project resource with the members removed.

    Raises:
        404: Project not found or not accessible.
    """
    project = await client.projects.remove_members_async(gid, members=body.members, raw=True)
    return build_success_response(data=project, request_id=request_id)  # type: ignore[arg-type]


__all__ = ["router"]
