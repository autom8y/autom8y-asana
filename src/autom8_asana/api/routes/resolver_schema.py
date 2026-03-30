"""Schema discovery endpoint for entity resolution.

Per TDD-I10: Extracted from resolver.py to separate the schema discovery
endpoint from the main resolution logic. This module provides the
GET /v1/resolve/{entity_type}/schema endpoint.

Per ADR-omniscience-semantic-introspection (D3): Extended with
``include_semantic`` and ``semantic_type`` query parameters for
structured metadata discovery. When ``include_semantic=true``,
descriptions include the full YAML annotation block.

Per SI-11: ``include_enums`` query parameter for inline enum values.
Per SI-12: ``GET /{entity_type}/schema/enums/{field_name}`` detail route.

Routes:
    GET /{entity_type}/schema - Discover queryable fields for an entity type
    GET /{entity_type}/schema/enums/{field_name} - Get enum values for a field

Models:
    SchemaFieldInfo: Metadata about a single queryable field
    EntitySchemaResponse: Full schema discovery response
    EnumValueInfo: Information about a single enum value
    EnumDetailResponse: Response for enum detail endpoint
"""

from __future__ import annotations

from typing import Annotated

from autom8y_log import get_logger
from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.api.dependencies import (
    RequestId,  # noqa: TC001 — FastAPI resolves these at runtime
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)

__all__ = [
    "schema_router",
    "SchemaFieldInfo",
    "EntitySchemaResponse",
    "EnumValueInfo",
    "EnumDetailResponse",
]

logger = get_logger(__name__)

schema_router = s2s_router()


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
    enum_values: list[dict] | None = Field(
        default=None,
        description=(
            "Valid enum values with business meaning. Populated when "
            "include_enums=true and field is enum type."
        ),
    )


class EntitySchemaResponse(BaseModel):
    """Response for schema discovery endpoint.

    Returns metadata about queryable fields for an entity type.

    Per Sprint 4 TDD: Extended with category, holder_for, and
    parent_entity fields derived from EntityDescriptor.
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(
        description="Entity type this schema describes (e.g., 'unit', 'business')."
    )
    version: str = Field(description="Schema version string for the entity type.")
    category: str | None = Field(
        default=None,
        description=(
            "Entity category classification (e.g., 'root', 'composite', "
            "'leaf', 'holder'). Derived from EntityDescriptor."
        ),
    )
    holder_for: str | None = Field(
        default=None,
        description=(
            "For holder entities, the entity type this holds "
            "(e.g., 'asset_edit' for asset_edit_holder). None for non-holders."
        ),
    )
    parent_entity: str | None = Field(
        default=None,
        description=(
            "Parent entity type in the hierarchy (e.g., 'business'). "
            "None when no parent relationship exists."
        ),
    )
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
    include_enums: Annotated[
        bool,
        Query(
            description=(
                "When true, enum-typed fields include their valid_values "
                "list in the enum_values response field. Requires "
                "include_semantic=true."
            ),
        ),
    ] = False,
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
        include_enums: Include valid_values for enum fields

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
    from autom8_asana.core.string_utils import to_pascal_case

    schema = registry.get_schema(to_pascal_case(entity_type))

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
        col_enum_values: list[dict] | None = None

        if include_semantic:
            col_semantic_type = get_semantic_type(col.description)
            metadata = parse_semantic_metadata(col.description)
            if metadata is not None:
                cascade = metadata.get("cascade_behavior")
                if isinstance(cascade, dict):
                    col_cascade_source = cascade.get("source_entity")

                # SI-11: Extract enum values when requested
                if include_enums and col_semantic_type in {"enum", "multi_enum"}:
                    valid_values = metadata.get("valid_values")
                    if isinstance(valid_values, list):
                        col_enum_values = valid_values

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
                enum_values=col_enum_values,
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

    # Resolve category metadata from EntityRegistry descriptor
    category: str | None = None
    holder_for: str | None = None
    parent_entity: str | None = None
    try:
        from autom8_asana.core.entity_registry import (
            get_registry as get_entity_registry,
        )

        entity_desc = get_entity_registry().get(entity_type)
        if entity_desc is not None:
            category = getattr(entity_desc, "category", None)
            holder_for = getattr(entity_desc, "holder_for", None)
            parent_entity = getattr(entity_desc, "parent_entity", None)
    except Exception:
        logger.debug("entity_descriptor_lookup_failed", extra={"entity_type": entity_type})

    return EntitySchemaResponse(
        entity_type=entity_type,
        version=schema.version,
        category=category,
        holder_for=holder_for,
        parent_entity=parent_entity,
        queryable_fields=queryable_fields,
    )


# ---------------------------------------------------------------------------
# SI-12: Enum detail route
# ---------------------------------------------------------------------------


class EnumValueInfo(BaseModel):
    """Information about a single enum value."""

    model_config = ConfigDict(extra="forbid")

    value: str = Field(description="The enum value string.")
    meaning: str = Field(description="Business meaning of this value.")


class EnumDetailResponse(BaseModel):
    """Response for enum detail endpoint."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(
        description="Entity type this enum belongs to (e.g., 'unit', 'offer')."
    )
    field_name: str = Field(description="Column name of the enum field.")
    semantic_type: str = Field(
        description="Semantic type classification (e.g., 'enum', 'multi_enum')."
    )
    values_source: str | None = Field(
        default=None,
        description="Source of enum values (e.g., 'hardcoded', 'asana_configured').",
    )
    values: list[EnumValueInfo] = Field(
        description="List of valid enum values with business meanings."
    )


@schema_router.get(
    "/{entity_type}/schema/enums/{field_name}",
    response_model=EnumDetailResponse,
    summary="Get enum values for a field",
    description=(
        "Returns the full enum documentation for a specific field on an "
        "entity type, including all valid values and their business meanings."
    ),
)
async def get_enum_detail(
    entity_type: str,
    field_name: str,
    request_id: RequestId,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> EnumDetailResponse:
    """Return enum values for a specific field on an entity type.

    Per SI-12: Provides detailed enum documentation without requiring
    the full schema discovery payload.

    Args:
        entity_type: Entity type (unit, business, offer, contact)
        field_name: Column name to look up enum values for
        request_id: Request correlation ID
        claims: Validated service claims from JWT

    Returns:
        Enum detail response with all valid values.

    Raises:
        HTTPException: 404 if entity type unknown, field not found,
            or field is not an enum type.
    """
    # Lazy import to avoid circular dependency
    from autom8_asana.api.routes.resolver import get_supported_entity_types
    from autom8_asana.dataframes.annotations import SEMANTIC_ANNOTATIONS

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

    # Look up annotation for this entity_type.field_name
    annotation_key = f"{entity_type}.{field_name}"
    annotation = SEMANTIC_ANNOTATIONS.get(annotation_key)
    if annotation is None:
        raise_api_error(
            request_id,
            404,
            "FIELD_NOT_ANNOTATED",
            f"No semantic annotation found for field '{field_name}' "
            f"on entity type '{entity_type}'.",
        )

    # Verify it is an enum or multi_enum type
    semantic_type = annotation.get("data_type_semantic", "")
    if semantic_type not in {"enum", "multi_enum"}:
        raise_api_error(
            request_id,
            404,
            "FIELD_NOT_ENUM",
            f"Field '{field_name}' on entity type '{entity_type}' has "
            f"semantic type '{semantic_type}', not an enum type.",
        )

    # Extract valid_values
    valid_values = annotation.get("valid_values", [])
    enum_values = [
        EnumValueInfo(
            value=v.get("value", ""),
            meaning=v.get("meaning", ""),
        )
        for v in valid_values
        if isinstance(v, dict)
    ]

    logger.info(
        "enum_detail_request",
        extra={
            "entity_type": entity_type,
            "field_name": field_name,
            "value_count": len(enum_values),
            "caller_service": claims.service_name,
        },
    )

    return EnumDetailResponse(
        entity_type=entity_type,
        field_name=field_name,
        semantic_type=semantic_type,
        values_source=annotation.get("values_source"),
        values=enum_values,
    )
