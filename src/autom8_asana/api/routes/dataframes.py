"""DataFrames REST endpoints.

This module provides REST endpoints for Asana DataFrame operations,
returning task data as structured DataFrames in JSON or Polars format.

Endpoints:
- GET /api/v1/dataframes/project/{gid} - Project tasks as dataframe
- GET /api/v1/dataframes/section/{gid} - Section tasks as dataframe

Per TDD-ASANA-SATELLITE (FR-API-DF-001 through FR-API-DF-005):
- All endpoints require Bearer token authentication
- Content negotiation via Accept header (ADR-ASANA-005):
  - application/json (default): JSON records array
  - application/x-polars-json: Polars-serialized format
- Schema selector via query parameter (dynamic from SchemaRegistry)

Per ADR-ASANA-005:
- Accept header determines response format
- Default to JSON records for broad compatibility
- Polars format for clients that can deserialize directly

Per TDD-dynamic-schema-api:
- Schema validation is dynamic, sourced from SchemaRegistry
- All registered schemas are accessible (base, unit, contact, business,
  offer, asset_edit, asset_edit_holder)
- Invalid schema returns HTTP 400 with list of valid schemas

Per TDD-SERVICE-LAYER-001 v2.0 Phase 4:
- Business logic delegated to DataFrameService
- Route handles only HTTP concerns (content negotiation, response formatting)
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse, Response

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    AsanaClientDualMode,
    DataFrameServiceDep,
    RequestId,
)
from autom8_asana.api.errors import raise_service_error
from autom8_asana.api.models import (
    PaginationMeta,
    ResponseMeta,
    build_success_response,
)
from autom8_asana.services.dataframe_service import InvalidSchemaError
from autom8_asana.services.errors import EntityNotFoundError

if TYPE_CHECKING:
    import polars as pl

router = APIRouter(prefix="/api/v1/dataframes", tags=["dataframes"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100

# MIME types for content negotiation
MIME_JSON = "application/json"
MIME_POLARS = "application/x-polars-json"


def _should_use_polars_format(accept: str | None) -> bool:
    """Check if client requested Polars format.

    Per ADR-ASANA-005: Content negotiation based on Accept header.
    Default to JSON if no Accept header or unknown format.
    """
    if accept is None:
        return False
    # Check for explicit Polars MIME type
    return MIME_POLARS in accept


def _format_dataframe_response(
    df: pl.DataFrame,
    request_id: str,
    limit: int,
    has_more: bool,
    next_offset: str | None,
    accept: str | None,
) -> Response:
    """Format DataFrame as HTTP response with content negotiation.

    Args:
        df: Polars DataFrame to serialize.
        request_id: Request ID for response metadata.
        limit: Page size for pagination metadata.
        has_more: Whether more pages are available.
        next_offset: Pagination cursor for next page.
        accept: Accept header value for format selection.

    Returns:
        JSONResponse in requested format.
    """
    pagination = PaginationMeta(
        limit=limit,
        has_more=has_more,
        next_offset=next_offset,
    )

    if _should_use_polars_format(accept):
        buffer = StringIO()
        df.write_json(buffer)
        polars_json = buffer.getvalue()

        response_data = {
            "data": polars_json,
            "meta": ResponseMeta(
                request_id=request_id,
                pagination=pagination,
            ).model_dump(mode="json"),
        }
        return JSONResponse(
            content=response_data,
            media_type=MIME_POLARS,
        )
    else:
        records = df.to_dicts()
        response = build_success_response(
            data=records,
            request_id=request_id,
            pagination=pagination,
        )
        return JSONResponse(
            content=response.model_dump(mode="json"),
            media_type=MIME_JSON,
        )


@router.get(
    "/project/{gid}",
    summary="Get project tasks as a DataFrame",
    response_description="DataFrame of project tasks in requested format",
    responses={
        200: {
            "description": "DataFrame data in requested format",
            "content": {
                MIME_JSON: {
                    "example": {
                        "data": [
                            {"gid": "123", "name": "Task 1", "type": "Unit"},
                            {"gid": "456", "name": "Task 2", "type": "Contact"},
                        ],
                        "meta": {
                            "request_id": "abc123",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "pagination": {
                                "limit": 100,
                                "has_more": False,
                                "next_offset": None,
                            },
                        },
                    }
                },
                MIME_POLARS: {
                    "description": "Polars-serialized JSON format",
                },
            },
        },
    },
)
async def get_project_dataframe(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    dataframe_service: DataFrameServiceDep,
    schema: Annotated[
        str,
        Query(
            description=(
                "Schema to use for extraction. Valid values: base, unit, "
                "contact, business, offer, asset_edit, asset_edit_holder"
            ),
        ),
    ] = "base",
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
    accept: Annotated[
        str | None,
        Header(alias="Accept", description="Response format preference"),
    ] = MIME_JSON,
) -> Response:
    """Fetch all tasks in a project as a structured DataFrame.

    Extracts task fields according to the selected ``schema``, then returns
    the result as either JSON records or Polars-serialized JSON depending
    on the ``Accept`` header.

    **Schemas** control which custom fields are extracted:

    - ``base`` — GID, name, completed, created_at (default)
    - ``unit`` / ``contact`` / ``business`` / ``offer`` — domain-specific
      custom fields (office_phone, weekly_ad_spend, email, etc.)
    - ``asset_edit`` / ``asset_edit_holder`` — asset editing metadata

    **Response formats** (via ``Accept`` header):

    - ``application/json`` (default) — JSON records array
    - ``application/x-polars-json`` — Polars-serialized format for direct
      DataFrame deserialization

    Supports cursor-based pagination via ``offset`` and ``limit``.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Asana project GID.
        schema: Field extraction schema (default ``base``).
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.
        accept: Response format preference (``Accept`` header).

    Returns:
        DataFrame of project tasks in the requested format and schema.

    Raises:
        400: Invalid ``schema`` value. Response includes list of valid schemas.
        404: Project not found or not accessible.
    """
    try:
        df_schema = dataframe_service.get_schema(schema)
    except InvalidSchemaError as e:
        raise_service_error(request_id, e)

    result = await dataframe_service.build_project_dataframe(
        client=client,
        project_gid=gid,
        schema=df_schema,
        limit=min(limit, MAX_LIMIT),
        offset=offset,
    )

    return _format_dataframe_response(
        df=result.dataframe,
        request_id=request_id,
        limit=limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
        accept=accept,
    )


@router.get(
    "/section/{gid}",
    summary="Get section tasks as a DataFrame",
    response_description="DataFrame of section tasks in requested format",
    responses={
        200: {
            "description": "DataFrame data in requested format",
            "content": {
                MIME_JSON: {
                    "example": {
                        "data": [
                            {"gid": "123", "name": "Task 1", "type": "Unit"},
                        ],
                        "meta": {
                            "request_id": "abc123",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "pagination": {
                                "limit": 100,
                                "has_more": False,
                                "next_offset": None,
                            },
                        },
                    }
                },
                MIME_POLARS: {
                    "description": "Polars-serialized JSON format",
                },
            },
        },
    },
)
async def get_section_dataframe(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    dataframe_service: DataFrameServiceDep,
    schema: Annotated[
        str,
        Query(
            description=(
                "Schema to use for extraction. Valid values: base, unit, "
                "contact, business, offer, asset_edit, asset_edit_holder"
            ),
        ),
    ] = "base",
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
    accept: Annotated[
        str | None,
        Header(alias="Accept", description="Response format preference"),
    ] = MIME_JSON,
) -> Response:
    """Fetch all tasks in a section as a structured DataFrame.

    Identical to ``GET /api/v1/dataframes/project/{gid}`` but scoped to
    a single section. Useful when you need task data from one lane of a
    board without fetching the entire project.

    **Schemas** control which custom fields are extracted:

    - ``base`` — GID, name, completed, created_at (default)
    - ``unit`` / ``contact`` / ``business`` / ``offer`` — domain-specific
      custom fields
    - ``asset_edit`` / ``asset_edit_holder`` — asset editing metadata

    **Response formats** (via ``Accept`` header):

    - ``application/json`` (default) — JSON records array
    - ``application/x-polars-json`` — Polars-serialized format

    Requires Bearer token authentication (JWT or PAT).

    Args:
        gid: Asana section GID.
        schema: Field extraction schema (default ``base``).
        limit: Items per page (1–100, default 100).
        offset: Pagination cursor from previous response.
        accept: Response format preference (``Accept`` header).

    Returns:
        DataFrame of section tasks in the requested format and schema.

    Raises:
        400: Invalid ``schema`` value. Response includes list of valid schemas.
        404: Section not found or not accessible.
    """
    try:
        df_schema = dataframe_service.get_schema(schema)
    except InvalidSchemaError as e:
        raise_service_error(request_id, e)

    try:
        result, _project_gid = await dataframe_service.build_section_dataframe(
            client=client,
            section_gid=gid,
            schema=df_schema,
            limit=min(limit, MAX_LIMIT),
            offset=offset,
        )
    except EntityNotFoundError as e:
        raise_service_error(request_id, e)

    return _format_dataframe_response(
        df=result.dataframe,
        request_id=request_id,
        limit=limit,
        has_more=result.has_more,
        next_offset=result.next_offset,
        accept=accept,
    )


__all__ = ["router"]
