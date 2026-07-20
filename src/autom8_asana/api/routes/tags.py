"""Tags REST endpoints delegating to TagService.

This module provides the SATELLITE read surface over workspace tags, closing
the TAG-1 gap (asana-mcp-postfelt-hardening / WS-B1): the composite write path
requires a ``tag_gid``, but callers think in tag NAMES and the satellite had no
way to resolve a name to a GID.

Endpoints:
- GET /api/v1/tags - List workspace tags (paginated)
- GET /api/v1/tags?name={name} - Resolve an exact tag name to its GID(s)

Per TDD-ASANA-SATELLITE:
- All endpoints require Bearer token authentication (JWT or PAT)
- Responses use standard envelope: {"data": ..., "meta": {...}}
- List endpoints support cursor-based pagination

Read-only and idempotent: no Asana write is performed. The name filter is the
resolution primitive the downstream sidecar (WS-B2) consumes.
"""

from typing import Annotated

from fastapi import Query

from autom8_asana.api.dependencies import (
    AsanaClientDualMode,
    RequestId,
    TagServiceDep,
)
from autom8_asana.api.error_responses import authenticated_responses
from autom8_asana.api.errors import raise_service_error
from autom8_asana.api.models import (
    AsanaResource,
    PaginationMeta,
    SuccessResponse,
    build_success_response,
)
from autom8_asana.api.routes._security import pat_router
from autom8_asana.services.errors import ServiceError

router = pat_router(prefix="/api/v1/tags", tags=["tags"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100


@router.get(
    "",
    summary="List workspace tags or resolve a tag name to its GID",
    response_description="Paginated workspace tags, or exact name-filtered matches",
    response_model=SuccessResponse[list[AsanaResource]],
    responses=authenticated_responses(),
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def list_tags(
    client: AsanaClientDualMode,
    request_id: RequestId,
    tag_service: TagServiceDep,
    name: Annotated[
        str | None,
        Query(
            description=(
                "Exact tag name to resolve to its GID(s). Matching is "
                "case-sensitive and byte-for-byte. Returns every tag with "
                "that exact name (Asana tag names are not unique); an empty "
                "list means no tag by that name exists. When omitted, the "
                "full workspace tag list is returned (paginated)."
            ),
            examples=["play_custom_calendar_integration"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
) -> SuccessResponse[list[AsanaResource]]:
    """List workspace tags, or resolve an exact tag name to its GID(s).

    This is the read surface that makes Asana tags addressable by NAME. Supply
    ``name`` to resolve a human-readable tag name to the GID(s) the composite
    write tool requires. Without ``name``, the full workspace tag list is
    returned one page at a time.

    Name resolution is EXACT and case-sensitive. Because Asana tag names are
    not unique, a match may return more than one tag -- the caller decides how
    to disambiguate. A name with no match returns HTTP 200 with an empty
    ``data`` list (not 404): a filtered collection with zero results is an
    empty collection, not a missing resource. Case-folding or fuzzy matching,
    if desired, belongs in the caller/sidecar layer, not this primitive.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        name: Exact tag name to resolve. Omit for an unfiltered listing.
        limit: Items per page for the unfiltered listing (1-100, default 100).
        offset: Pagination cursor from a previous unfiltered response.

    Returns:
        Envelope with a list of tag resources (``gid``, ``name``, ``color``,
        ``permalink_url``). For a name query the list is the complete match
        set; for an unfiltered listing it is one page plus a pagination cursor.

    Raises:
        503: The Asana workspace GID is not configured on the service.
    """
    try:
        result = await tag_service.list_tags(
            client,
            name=name,
            limit=limit,
            offset=offset,
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


__all__ = ["router"]
