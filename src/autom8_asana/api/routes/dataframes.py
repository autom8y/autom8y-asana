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
"""

from io import StringIO
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from autom8_asana._defaults.cache import InMemoryCacheProvider
from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.models import (
    PaginationMeta,
    ResponseMeta,
    build_success_response,
)
from autom8_asana.cache.unified import UnifiedTaskStore
from autom8_asana.dataframes import (
    DefaultCustomFieldResolver,
    SectionDataFrameBuilder,
)
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.dataframes.models.schema import DataFrameSchema
from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin
from autom8_asana.models.task import Task

router = APIRouter(prefix="/api/v1/dataframes", tags=["dataframes"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100

# MIME types for content negotiation
MIME_JSON = "application/json"
MIME_POLARS = "application/x-polars-json"

# Module-level cached mapping (built on first access)
# Per TDD-dynamic-schema-api: Lazy initialization with thread-safe registry
_schema_mapping: dict[str, str] | None = None
_valid_schemas: list[str] | None = None


def _get_schema_mapping() -> tuple[dict[str, str], list[str]]:
    """Get cached schema mapping, building it if necessary.

    Returns:
        Tuple of (name_to_task_type mapping, sorted valid schema names).

    Note:
        Thread-safe: SchemaRegistry._ensure_initialized() uses locking.
        The global assignment is atomic in CPython.
    """
    global _schema_mapping, _valid_schemas

    if _schema_mapping is None:
        registry = SchemaRegistry.get_instance()

        # Build mapping: schema.name -> task_type
        # Special case: base schema uses "*" wildcard
        mapping = {"base": "*"}
        for task_type in registry.list_task_types():
            schema = registry.get_schema(task_type)
            mapping[schema.name] = task_type

        _schema_mapping = mapping
        _valid_schemas = sorted(mapping.keys())

    return _schema_mapping, _valid_schemas


def _get_schema(schema_name: str) -> DataFrameSchema:
    """Get DataFrameSchema for the given schema name.

    Per TDD-dynamic-schema-api: Dynamic validation against SchemaRegistry.

    Args:
        schema_name: Schema name from API request (case-insensitive).

    Returns:
        DataFrameSchema from registry.

    Raises:
        HTTPException: 400 if schema name is invalid.
    """
    mapping, valid_schemas = _get_schema_mapping()

    # Handle empty/whitespace input (FastAPI defaults handle missing)
    if not schema_name or not schema_name.strip():
        # Use base schema as fallback
        return SchemaRegistry.get_instance().get_schema("*")

    # Normalize: lowercase and strip whitespace
    normalized = schema_name.lower().strip()

    # Block wildcard as direct input (it's exposed as "base")
    if normalized == "*":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_SCHEMA",
                "message": (
                    "Unknown schema '*'. Use 'base' for the base schema. "
                    f"Valid schemas: {', '.join(valid_schemas)}"
                ),
                "valid_schemas": valid_schemas,
            },
        )

    task_type = mapping.get(normalized)

    if task_type is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_SCHEMA",
                "message": (
                    f"Unknown schema '{schema_name}'. "
                    f"Valid schemas: {', '.join(valid_schemas)}"
                ),
                "valid_schemas": valid_schemas,
            },
        )

    return SchemaRegistry.get_instance().get_schema(task_type)


def _should_use_polars_format(accept: str | None) -> bool:
    """Check if client requested Polars format.

    Per ADR-ASANA-005: Content negotiation based on Accept header.
    Default to JSON if no Accept header or unknown format.
    """
    if accept is None:
        return False
    # Check for explicit Polars MIME type
    return MIME_POLARS in accept


@router.get(
    "/project/{gid}",
    summary="Get project tasks as dataframe",
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
    """Get project tasks as a DataFrame.

    Per FR-API-DF-001, FR-API-DF-002, TDD-dynamic-schema-api:
    - Fetches tasks from the specified project
    - Returns DataFrame in JSON or Polars format based on Accept header
    - Supports all registered schemas via dynamic validation

    Args:
        gid: Asana project GID.
        schema: Schema for extraction (base, unit, contact, business,
            offer, asset_edit, asset_edit_holder). Case-insensitive.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.
        accept: Accept header for content negotiation.

    Returns:
        DataFrame data in requested format with pagination metadata.

    Raises:
        HTTPException: 400 if schema is invalid (includes valid_schemas list).
    """
    # Build opt_fields for custom field data needed by extractors
    opt_fields = [
        "gid",
        "name",
        "resource_type",
        "completed",
        "completed_at",
        "created_at",
        "modified_at",
        "notes",
        "assignee",
        "assignee.name",
        "due_on",
        "due_at",
        "start_on",
        "memberships.section.name",
        "memberships.project.gid",
        "custom_fields",
        "custom_fields.gid",
        "custom_fields.name",
        "custom_fields.resource_subtype",
        "custom_fields.display_value",
        "custom_fields.enum_value",
        "custom_fields.enum_value.name",
        "custom_fields.multi_enum_values",
        "custom_fields.multi_enum_values.name",
        "custom_fields.number_value",
        "custom_fields.text_value",
    ]

    # Build params for SDK call
    params: dict[str, Any] = {
        "project": gid,
        "limit": min(limit, MAX_LIMIT),
        "opt_fields": ",".join(opt_fields),
    }
    if offset:
        params["offset"] = offset

    # Fetch tasks using HTTP client
    data, next_offset = await client._http.get_paginated("/tasks", params=params)

    # Get schema and build DataFrame
    df_schema = _get_schema(schema)

    # Create resolver for custom field mapping
    resolver = DefaultCustomFieldResolver()

    # Build DataFrame using DataFrameViewPlugin
    # Per TDD-UNIFIED-CACHE-001 Phase 4: unified_store is mandatory.
    # Create a lightweight in-memory store for the API route since we already
    # have the tasks fetched - no caching needed for this synchronous path.
    unified_store = UnifiedTaskStore(cache=InMemoryCacheProvider())

    # Create DataFrameViewPlugin for extraction
    view_plugin = DataFrameViewPlugin(
        schema=df_schema,
        store=unified_store,
        resolver=resolver,
    )

    # Extract rows from tasks using the view plugin (async endpoint)
    import polars as pl

    rows = await view_plugin._extract_rows_async(data, project_gid=gid)
    if rows:
        df = pl.DataFrame(rows, schema=df_schema.to_polars_schema())
    else:
        df = pl.DataFrame(schema=df_schema.to_polars_schema())

    # Create pagination metadata
    pagination = PaginationMeta(
        limit=limit,
        has_more=next_offset is not None,
        next_offset=next_offset,
    )

    # Return appropriate format based on Accept header
    if _should_use_polars_format(accept):
        # Polars JSON format - write to string buffer
        buffer = StringIO()
        df.write_json(buffer)
        polars_json = buffer.getvalue()

        # Wrap in response envelope
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
        # JSON records format - convert DataFrame to list of dicts
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
    "/section/{gid}",
    summary="Get section tasks as dataframe",
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
    """Get section tasks as a DataFrame.

    Per FR-API-DF-003, FR-API-DF-004, TDD-dynamic-schema-api:
    - Fetches tasks from the specified section
    - Returns DataFrame in JSON or Polars format based on Accept header
    - Supports all registered schemas via dynamic validation

    Args:
        gid: Asana section GID.
        schema: Schema for extraction (base, unit, contact, business,
            offer, asset_edit, asset_edit_holder). Case-insensitive.
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.
        accept: Accept header for content negotiation.

    Returns:
        DataFrame data in requested format with pagination metadata.

    Raises:
        HTTPException: 400 if schema is invalid (includes valid_schemas list).
        HTTPException: 404 if section not found or has no parent project.
    """
    # First, get the section to find its parent project
    section_data = await client._http.get(
        f"/sections/{gid}",
        params={"opt_fields": "project.gid"},
    )
    project_gid = section_data.get("project", {}).get("gid")

    if not project_gid:
        raise HTTPException(
            status_code=404,
            detail="Section not found or has no parent project",
        )

    # Build opt_fields for custom field data needed by extractors
    opt_fields = [
        "gid",
        "name",
        "resource_type",
        "completed",
        "completed_at",
        "created_at",
        "modified_at",
        "notes",
        "assignee",
        "assignee.name",
        "due_on",
        "due_at",
        "start_on",
        "memberships.section.name",
        "memberships.project.gid",
        "custom_fields",
        "custom_fields.gid",
        "custom_fields.name",
        "custom_fields.resource_subtype",
        "custom_fields.display_value",
        "custom_fields.enum_value",
        "custom_fields.enum_value.name",
        "custom_fields.multi_enum_values",
        "custom_fields.multi_enum_values.name",
        "custom_fields.number_value",
        "custom_fields.text_value",
    ]

    # Build params for SDK call
    params: dict[str, Any] = {
        "section": gid,
        "limit": min(limit, MAX_LIMIT),
        "opt_fields": ",".join(opt_fields),
    }
    if offset:
        params["offset"] = offset

    # Fetch tasks using HTTP client
    data, next_offset = await client._http.get_paginated("/tasks", params=params)

    # Convert to Task models for builder
    tasks = [Task.model_validate(t) for t in data]

    # Get schema and build DataFrame
    df_schema = _get_schema(schema)

    # Create resolver for custom field mapping
    resolver = DefaultCustomFieldResolver()

    # Create a mock section object with the project reference for the builder
    class SectionProxy:
        def __init__(self, gid: str, project_gid: str, tasks: list[Task]):
            self.gid = gid
            self.project = {"gid": project_gid}
            self.tasks = tasks

    section_proxy = SectionProxy(gid, project_gid, tasks)

    # Build DataFrame
    builder = SectionDataFrameBuilder(
        section=section_proxy,
        task_type="*",  # Extract all task types
        schema=df_schema,
        resolver=resolver,
    )
    df = builder.build(tasks=tasks)

    # Create pagination metadata
    pagination = PaginationMeta(
        limit=limit,
        has_more=next_offset is not None,
        next_offset=next_offset,
    )

    # Return appropriate format based on Accept header
    if _should_use_polars_format(accept):
        # Polars JSON format - write to string buffer
        buffer = StringIO()
        df.write_json(buffer)
        polars_json = buffer.getvalue()

        # Wrap in response envelope
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
        # JSON records format - convert DataFrame to list of dicts
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


__all__ = ["router"]
