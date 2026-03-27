"""Schema discovery endpoint for entity resolution.

Per TDD-I10: Extracted from resolver.py to separate the schema discovery
endpoint from the main resolution logic. This module provides the
GET /v1/resolve/{entity_type}/schema endpoint.

Per ADR-omniscience-semantic-introspection (D3): Extended with
``include_semantic`` and ``semantic_type`` query parameters for
structured metadata discovery. When ``include_semantic=true``,
descriptions include the full YAML annotation block.

Routes:
    GET /{entity_type}/schema - Discover queryable fields for an entity type

Models:
    SchemaFieldInfo: Metadata about a single queryable field
    EntitySchemaResponse: Full schema discovery response
"""

from __future__ import annotations

from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.api.dependencies import (
    RequestId,  # noqa: TC001 — FastAPI resolves these at runtime
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)

__all__ = [
    "schema_router",
    "SchemaFieldInfo",
    "EntitySchemaResponse",
]

logger = get_logger(__name__)

schema_router = APIRouter()


class SchemaFieldInfo(BaseModel):
    """Information about a queryable schema field.

    Per SPIKE-dynamic-api-criteria: Enables API consumers to discover
    valid criterion fields dynamically.

    Per ADR-omniscience-semantic-introspection (D3): Extended with
    semantic_type and cascade_source for structured metadata.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Column name used in query predicates and select clauses."
    )
    type: str = Field(
        description="Data type of the column (e.g., 'Utf8', 'Float64', 'Boolean')."
    )
    description: str | None = Field(
        default=None,
        description="Human-readable explanation of the field's domain meaning.",
    )
    semantic_type: str | None = Field(
        default=None,
        description=(
            "Semantic type classification (e.g., 'phone', 'enum', 'currency'). "
            "Populated when include_semantic=true and field has an annotation."
        ),
    )
    cascade_source: str | None = Field(
        default=None,
        description=(
            "Source entity for cascade fields (e.g., 'Business', 'Unit'). "
            "Populated when field has cascade_behavior annotation."
        ),
    )


class EntitySchemaResponse(BaseModel):
    """Response for schema discovery endpoint.

    Returns metadata about queryable fields for an entity type.
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(
        description="Entity type this schema describes (e.g., 'unit', 'business')."
    )
    version: str = Field(description="Schema version string for the entity type.")
    queryable_fields: list[SchemaFieldInfo] = Field(
        description="Fields available for querying and resolution criteria."
    )


@schema_router.get(
    "/{entity_type}/schema",
    response_model=EntitySchemaResponse,
    summary="Get queryable fields for entity type",
    description=(
        "Returns schema information including all fields that can be used "
        "in resolution criteria. When include_semantic=true, descriptions "
        "include structured YAML metadata with business meaning, data type "
        "semantics, cascade behavior, and resolution impact."
    ),
)
async def get_entity_schema(
    entity_type: str,
    request_id: RequestId,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    include_semantic: Annotated[
        bool,
        Query(
            description=(
                "When true, descriptions include the full YAML semantic "
                "annotation block after a --- delimiter. When false (default), "
                "descriptions are the human-readable prefix only."
            ),
        ),
    ] = False,
    semantic_type: Annotated[
        str | None,
        Query(
            description=(
                "Filter columns to those matching a data_type_semantic value "
                "(e.g., 'enum', 'currency', 'phone'). Requires "
                "include_semantic=true."
            ),
        ),
    ] = None,
) -> EntitySchemaResponse:
    """Return queryable fields for entity type.

    Per SPIKE-dynamic-api-criteria: Enables API consumers to discover
    valid criterion fields dynamically instead of relying on hardcoded
    field lists.

    Per ADR-omniscience-semantic-introspection (D3): When
    ``include_semantic=true``, enriches descriptions with YAML metadata
    and populates ``semantic_type`` / ``cascade_source`` on each field.

    Args:
        entity_type: Entity type (unit, business, offer, contact)
        claims: Validated service claims from JWT
        include_semantic: Include YAML annotation in descriptions
        semantic_type: Filter by data_type_semantic value

    Returns:
        Schema information including queryable fields.

    Raises:
        HTTPException: 404 if entity type unknown.
    """
    # Lazy import to avoid circular dependency (resolver_schema -> resolver)
    from autom8_asana.api.routes.resolver import get_supported_entity_types
    from autom8_asana.dataframes.annotations import (
        enrich_schema,
        get_semantic_type,
        parse_semantic_metadata,
    )
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    # Validate entity type
    supported_types = get_supported_entity_types()
    if entity_type not in supported_types:
        raise_api_error(
            request_id,
            404,
            "UNKNOWN_ENTITY_TYPE",
            f"Unknown entity type: {entity_type}",
            details={"available_types": sorted(supported_types)},
        )

    # Get schema from registry
    registry = SchemaRegistry.get_instance()
    schema = registry.get_schema(entity_type.capitalize())

    if schema is None:
        raise_api_error(
            request_id,
            404,
            "SCHEMA_NOT_FOUND",
            f"No schema registered for entity type: {entity_type}",
        )

    # Apply semantic enrichment if requested
    working_schema = enrich_schema(schema, include_semantic=include_semantic)

    # Build queryable fields list
    # Include fields that have a source (can be populated) or are core fields
    queryable_fields: list[SchemaFieldInfo] = []
    for col in working_schema.columns:
        if col.source is None and col.name not in {"gid", "name", "parent_gid"}:
            continue

        # Extract semantic metadata for the enriched fields
        col_semantic_type: str | None = None
        col_cascade_source: str | None = None

        if include_semantic:
            col_semantic_type = get_semantic_type(col.description)
            metadata = parse_semantic_metadata(col.description)
            if metadata is not None:
                cascade = metadata.get("cascade_behavior")
                if isinstance(cascade, dict):
                    col_cascade_source = cascade.get("source_entity")

        # Apply semantic_type filter if specified
        if (
            semantic_type is not None
            and include_semantic
            and col_semantic_type != semantic_type
        ):
            continue

        queryable_fields.append(
            SchemaFieldInfo(
                name=col.name,
                type=str(col.dtype),
                description=col.description,
                semantic_type=col_semantic_type,
                cascade_source=col_cascade_source,
            ),
        )

    logger.info(
        "schema_discovery_request",
        extra={
            "entity_type": entity_type,
            "version": schema.version,
            "field_count": len(queryable_fields),
            "caller_service": claims.service_name,
            "include_semantic": include_semantic,
            "semantic_type_filter": semantic_type,
        },
    )

    return EntitySchemaResponse(
        entity_type=entity_type,
        version=schema.version,
        queryable_fields=queryable_fields,
    )
