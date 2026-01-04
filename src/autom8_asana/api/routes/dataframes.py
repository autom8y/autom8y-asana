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
- Schema selector via query parameter (base, unit, contact)

Per ADR-ASANA-005:
- Accept header determines response format
- Default to JSON records for broad compatibility
- Polars format for clients that can deserialize directly
"""

from enum import Enum
from io import StringIO
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.models import (
    PaginationMeta,
    ResponseMeta,
    build_success_response,
)
from autom8_asana.cache.unified import UnifiedTaskStore
from autom8_asana.dataframes import (
    BASE_SCHEMA,
    CONTACT_SCHEMA,
    UNIT_SCHEMA,
    DefaultCustomFieldResolver,
    ProjectDataFrameBuilder,
    SectionDataFrameBuilder,
)
from autom8_asana._defaults.cache import InMemoryCacheProvider
from autom8_asana.models.task import Task

router = APIRouter(prefix="/api/v1/dataframes", tags=["dataframes"])

# Default pagination limit
DEFAULT_LIMIT = 100
MAX_LIMIT = 100

# MIME types for content negotiation
MIME_JSON = "application/json"
MIME_POLARS = "application/x-polars-json"


class SchemaType(str, Enum):
    """Schema type selector for DataFrame extraction."""

    base = "base"
    unit = "unit"
    contact = "contact"


def _get_schema(schema_type: SchemaType):
    """Get DataFrameSchema for the given schema type."""
    match schema_type:
        case SchemaType.unit:
            return UNIT_SCHEMA
        case SchemaType.contact:
            return CONTACT_SCHEMA
        case SchemaType.base:
            return BASE_SCHEMA


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
        SchemaType,
        Query(description="Schema to use for extraction (base, unit, contact)"),
    ] = SchemaType.base,
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

    Per FR-API-DF-001, FR-API-DF-002:
    - Fetches tasks from the specified project
    - Returns DataFrame in JSON or Polars format based on Accept header
    - Supports schema selection for type-specific extraction

    Args:
        gid: Asana project GID.
        schema: Schema for extraction (base, unit, contact).
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.
        accept: Accept header for content negotiation.

    Returns:
        DataFrame data in requested format with pagination metadata.
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

    # Convert to Task models for builder
    tasks = [Task.model_validate(t) for t in data]

    # Get schema and build DataFrame
    df_schema = _get_schema(schema)

    # Create resolver for custom field mapping
    resolver = DefaultCustomFieldResolver()

    # Create a mock project object with the gid for the builder
    class ProjectProxy:
        def __init__(self, gid: str, tasks: list[Task]):
            self.gid = gid
            self.tasks = tasks

    project_proxy = ProjectProxy(gid, tasks)

    # Build DataFrame
    # Per TDD-UNIFIED-CACHE-001 Phase 4: unified_store is mandatory.
    # Create a lightweight in-memory store for the API route since we already
    # have the tasks fetched - no caching needed for this synchronous path.
    unified_store = UnifiedTaskStore(cache=InMemoryCacheProvider())
    builder = ProjectDataFrameBuilder(
        project=project_proxy,
        task_type="*",  # Extract all task types
        schema=df_schema,
        resolver=resolver,
        unified_store=unified_store,
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
        SchemaType,
        Query(description="Schema to use for extraction (base, unit, contact)"),
    ] = SchemaType.base,
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

    Per FR-API-DF-003, FR-API-DF-004:
    - Fetches tasks from the specified section
    - Returns DataFrame in JSON or Polars format based on Accept header
    - Supports schema selection for type-specific extraction

    Args:
        gid: Asana section GID.
        schema: Schema for extraction (base, unit, contact).
        limit: Number of items per page (1-100, default 100).
        offset: Pagination cursor from previous response.
        accept: Accept header for content negotiation.

    Returns:
        DataFrame data in requested format with pagination metadata.
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
