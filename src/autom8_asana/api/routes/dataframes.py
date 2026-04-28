"""DataFrames REST endpoints.

This module provides REST endpoints for Asana DataFrame operations,
returning task data as structured DataFrames in JSON or Polars format.

Endpoints:
- GET /api/v1/dataframes/schemas - List all dataframe schemas
- GET /api/v1/dataframes/schemas/{name} - Get single schema details
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

from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Annotated, Any, Literal

from autom8y_log import get_logger
from fastapi import Header, Query
from fastapi.responses import JSONResponse, Response

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    AsanaClientDualMode,
    AuthContextDep,
    DataFrameServiceDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.api.models import (
    GidStr,
    PaginationMeta,
    ResponseMeta,
    build_success_response,
)
from autom8_asana.api.routes._security import pat_router
from autom8_asana.services.dataframe_service import InvalidSchemaError
from autom8_asana.services.errors import EntityNotFoundError

if TYPE_CHECKING:
    import polars as pl

router = pat_router(prefix="/api/v1/dataframes", tags=["dataframes"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100

# Schema name to module constant mapping for introspection endpoints
_SCHEMA_NAMES = (
    "base",
    "unit",
    "contact",
    "business",
    "offer",
    "asset_edit",
    "asset_edit_holder",
    "process",
)

DataFrameSchemaLiteral = Literal[
    "base",
    "unit",
    "contact",
    "business",
    "offer",
    "asset_edit",
    "asset_edit_holder",
    "process",
]

# MIME types for content negotiation
MIME_JSON = "application/json"
MIME_POLARS = "application/x-polars-json"
# Sprint 3 additive (per TDD §7 + PRD §8.4): /exports format negotiation MIMEs.
MIME_CSV = "text/csv"
MIME_PARQUET = "application/vnd.apache.parquet"

# Sprint 3 ESC-3 (TDD §15.3): observability logger for export size measurement.
_export_format_logger = get_logger(f"{__name__}.exports.format")


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
    *,
    format: Literal["json", "csv", "parquet"] | None = None,
) -> Response:
    """Format DataFrame as HTTP response with content negotiation.

    Args:
        df: Polars DataFrame to serialize.
        request_id: Request ID for response metadata.
        limit: Page size for pagination metadata.
        has_more: Whether more pages are available.
        next_offset: Pagination cursor for next page.
        accept: Accept header value for format selection.
        format: Sprint 3 additive (TDD §7) — explicit format selector for the
            new ``/exports`` route. When set to ``"csv"`` or ``"parquet"``, the
            corresponding non-JSON branch fires. ``"json"`` and ``None`` preserve
            the existing JSON / Polars-binary content-negotiation behavior so
            existing dataframes/section/project route callers are unaffected
            (TDD-AC-4).

    Returns:
        Response in the requested format with the appropriate MIME type.
    """
    pagination = PaginationMeta(
        limit=limit,
        has_more=has_more,
        next_offset=next_offset,
    )

    # Sprint 3 (TDD §7.2): explicit format selector branches FIRST so the
    # /exports route can request CSV/Parquet without disturbing existing
    # content-negotiation paths used by the dataframes/project + dataframes/section
    # route handlers (TDD-AC-4 — additive extension).
    if format == "csv":
        return _format_csv_response(df, request_id)
    if format == "parquet":
        return _format_parquet_response(df, request_id)

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


def _format_csv_response(df: pl.DataFrame, request_id: str) -> Response:
    """Serialize an eager DataFrame as a ``text/csv`` HTTP body.

    Per TDD §7.3: reuses ``pl.DataFrame.write_csv()`` directly (the existing
    ``CsvFormatter`` at ``query/formatters.py:122`` targets ``RowsResponse``
    shapes, not raw DataFrames). The ``identity_complete`` column (when present
    per ``api/routes/_exports_helpers.attach_identity_complete``) appears as a
    header and a per-row boolean column.

    ESC-3 (TDD §15.3): emits an observability log record with row count and
    serialized byte count per format so Sprint 3 can confirm Phase 1 fixtures
    fit the in-memory body decision (TDD §7.5 disposition).
    """
    body = df.write_csv()
    body_bytes = body.encode("utf-8")
    _emit_export_size_metric(
        request_id=request_id,
        format_label="csv",
        df=df,
        serialized_size=len(body_bytes),
    )
    return Response(
        content=body_bytes,
        media_type=MIME_CSV,
        headers={"X-Request-ID": request_id},
    )


def _format_parquet_response(df: pl.DataFrame, request_id: str) -> Response:
    """Serialize an eager DataFrame as an ``application/vnd.apache.parquet`` HTTP body.

    Per TDD §7.3: writes ``pl.DataFrame.write_parquet()`` to a ``BytesIO``
    buffer (the existing ``builders/base.py:751 to_parquet`` writes to a
    ``Path``; here we need a Response payload). Polars is already a runtime
    requirement; no new dependency added.

    ESC-3 (TDD §15.3): emits the same observability metric as CSV.
    """
    buf = BytesIO()
    df.write_parquet(buf)
    body_bytes = buf.getvalue()
    _emit_export_size_metric(
        request_id=request_id,
        format_label="parquet",
        df=df,
        serialized_size=len(body_bytes),
    )
    return Response(
        content=body_bytes,
        media_type=MIME_PARQUET,
        headers={"X-Request-ID": request_id},
    )


def _emit_export_size_metric(
    *,
    request_id: str,
    format_label: str,
    df: pl.DataFrame,
    serialized_size: int,
) -> None:
    """Log row count + serialized byte count for an export response.

    ESC-3 measurement surface (TDD §15.3 + DEFER-WATCH-7). Sprint 3 inspects
    these log records against Reactivation+Outreach fixtures to decide whether
    Phase 1 in-memory body limits hold or whether a Phase 1.5 streaming ADR
    is required.
    """
    _export_format_logger.info(
        "export_format_serialized",
        extra={
            "request_id": request_id,
            "format": format_label,
            "row_count": df.height,
            "column_count": df.width,
            "serialized_bytes": serialized_size,
        },
    )


def _load_all_schemas() -> dict[str, Any]:
    """Load all registered DataFrameSchema objects by name.

    Returns:
        Dict mapping schema name to DataFrameSchema instance.
    """
    from autom8_asana.dataframes.schemas import (
        ASSET_EDIT_HOLDER_SCHEMA,
        ASSET_EDIT_SCHEMA,
        BASE_SCHEMA,
        BUSINESS_SCHEMA,
        CONTACT_SCHEMA,
        OFFER_SCHEMA,
        PROCESS_SCHEMA,
        UNIT_SCHEMA,
    )

    return {
        "base": BASE_SCHEMA,
        "unit": UNIT_SCHEMA,
        "contact": CONTACT_SCHEMA,
        "business": BUSINESS_SCHEMA,
        "offer": OFFER_SCHEMA,
        "process": PROCESS_SCHEMA,
        "asset_edit": ASSET_EDIT_SCHEMA,
        "asset_edit_holder": ASSET_EDIT_HOLDER_SCHEMA,
    }


def _schema_to_dict(
    name: str,
    schema: Any,
    *,
    include_semantic: bool = False,
    semantic_type: str | None = None,
    include_enums: bool = False,
) -> dict[str, Any]:
    """Convert a DataFrameSchema to an API-friendly dict.

    Per ADR-omniscience-semantic-introspection (D3): When
    ``include_semantic=True``, enriches descriptions with YAML annotations.
    When ``semantic_type`` is set, filters columns to those matching the
    specified data_type_semantic value.

    Per SI-11: When ``include_enums=True`` and ``include_semantic=True``,
    enum-typed columns include their valid_values in the column dict.

    Args:
        name: Schema name key.
        schema: DataFrameSchema instance.
        include_semantic: Include YAML annotation in descriptions.
        semantic_type: Filter columns by semantic type.
        include_enums: Include valid_values for enum fields.

    Returns:
        Dict with schema metadata and column definitions.
    """
    from autom8_asana.dataframes.annotations import (
        enrich_schema,
        get_semantic_type,
        parse_semantic_metadata,
    )

    working_schema = enrich_schema(schema, include_semantic=include_semantic)

    columns = []
    for col in working_schema.columns:
        col_type: str | None = None
        if include_semantic:
            col_type = get_semantic_type(col.description)
        if semantic_type is not None and include_semantic and col_type != semantic_type:
            continue

        col_dict: dict[str, Any] = {
            "name": col.name,
            "dtype": col.dtype,
            "nullable": col.nullable,
            "description": col.description,
        }

        # SI-11: Include enum values when requested
        if include_enums and include_semantic and col_type in {"enum", "multi_enum"}:
            metadata = parse_semantic_metadata(col.description)
            if metadata is not None:
                valid_values = metadata.get("valid_values")
                if isinstance(valid_values, list):
                    col_dict["enum_values"] = valid_values

        columns.append(col_dict)

    return {
        "name": name,
        "version": working_schema.version,
        "task_type": working_schema.task_type,
        "column_count": len(columns),
        "columns": columns,
    }


# ---------------------------------------------------------------------------
# Schema introspection endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/schemas",
    summary="List all dataframe schemas",
    description=(
        "Returns all available dataframe schemas with their column definitions. "
        "Each schema maps Asana custom fields to typed DataFrame columns. "
        "Use this to discover which schema to pass to the project or section "
        "dataframe endpoints (GET /api/v1/dataframes/project/{gid}?schema=...). "
        "When include_semantic=true, descriptions include structured YAML "
        "metadata with business meaning, data type semantics, and more."
    ),
)
async def list_dataframes(
    request_id: RequestId,
    auth: AuthContextDep,
    include_semantic: Annotated[
        bool,
        Query(
            description=(
                "When true, descriptions include the full YAML semantic "
                "annotation block after a --- delimiter."
            ),
        ),
    ] = False,
    semantic_type: Annotated[
        str | None,
        Query(
            description=(
                "Filter columns to those matching a data_type_semantic value "
                "(e.g., 'enum', 'currency'). Requires include_semantic=true."
            ),
        ),
    ] = None,
    include_enums: Annotated[
        bool,
        Query(
            description=(
                "When true, enum-typed columns include their valid_values "
                "list. Requires include_semantic=true."
            ),
        ),
    ] = False,
) -> Any:
    """List available dataframe schemas with their columns."""
    all_schemas = _load_all_schemas()
    result = [
        _schema_to_dict(
            name,
            schema,
            include_semantic=include_semantic,
            semantic_type=semantic_type,
            include_enums=include_enums,
        )
        for name, schema in all_schemas.items()
    ]
    return build_success_response(data=result, request_id=request_id)


@router.get(
    "/schemas/{name}",
    summary="Get a single dataframe schema",
    description=(
        "Returns detailed column definitions for a specific dataframe schema. "
        "Each column includes name, dtype (Polars type), nullable flag, and "
        "description. Use this to understand the exact columns returned when "
        "requesting data with this schema. When include_semantic=true, "
        "descriptions include structured YAML metadata."
    ),
)
async def get_dataframe_schema(
    name: DataFrameSchemaLiteral,
    request_id: RequestId,
    auth: AuthContextDep,
    include_semantic: Annotated[
        bool,
        Query(
            description=(
                "When true, descriptions include the full YAML semantic "
                "annotation block after a --- delimiter."
            ),
        ),
    ] = False,
    semantic_type: Annotated[
        str | None,
        Query(
            description=(
                "Filter columns to those matching a data_type_semantic value "
                "(e.g., 'enum', 'currency'). Requires include_semantic=true."
            ),
        ),
    ] = None,
    include_enums: Annotated[
        bool,
        Query(
            description=(
                "When true, enum-typed columns include their valid_values "
                "list. Requires include_semantic=true."
            ),
        ),
    ] = False,
) -> Any:
    """Get detailed column definitions for a specific schema."""
    all_schemas = _load_all_schemas()
    schema = all_schemas.get(name)
    if schema is None:
        raise_api_error(
            request_id,
            404,
            "SCHEMA_NOT_FOUND",
            f"Unknown schema: '{name}'. Available schemas: {', '.join(sorted(all_schemas.keys()))}",
            details={"available_schemas": sorted(all_schemas.keys())},
        )
    return build_success_response(
        data=_schema_to_dict(
            name,
            schema,
            include_semantic=include_semantic,
            semantic_type=semantic_type,
            include_enums=include_enums,
        ),
        request_id=request_id,
    )


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------


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
async def list_project_dataframe(
    gid: GidStr,
    client: AsanaClientDualMode,
    auth: AuthContextDep,
    request_id: RequestId,
    dataframe_service: DataFrameServiceDep,
    schema: Annotated[
        DataFrameSchemaLiteral,
        Query(
            description=(
                "Schema to use for extraction. Valid values: base, unit, "
                "contact, business, offer, asset_edit, asset_edit_holder, "
                "process"
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
    - ``unit`` / ``contact`` / ``business`` / ``offer`` / ``process`` —
      domain-specific custom fields (office_phone, weekly_ad_spend, email, etc.)
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
async def list_section_dataframe(
    gid: GidStr,
    client: AsanaClientDualMode,
    auth: AuthContextDep,
    request_id: RequestId,
    dataframe_service: DataFrameServiceDep,
    schema: Annotated[
        DataFrameSchemaLiteral,
        Query(
            description=(
                "Schema to use for extraction. Valid values: base, unit, "
                "contact, business, offer, asset_edit, asset_edit_holder, "
                "process"
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
    - ``unit`` / ``contact`` / ``business`` / ``offer`` / ``process`` —
      domain-specific custom fields
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
