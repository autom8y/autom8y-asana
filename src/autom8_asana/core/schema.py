"""Schema version lookup utilities."""

from __future__ import annotations

from autom8y_log import get_logger

logger = get_logger(__name__)


def get_schema_version(entity_type: str | None) -> str | None:
    """Look up schema version from SchemaRegistry for an entity type.

    Performs lazy imports to avoid circular dependencies.

    Args:
        entity_type: Entity type in lowercase (e.g., "unit", "contact").
            Returns None if entity_type is None or empty.

    Returns:
        Schema version string if found, None if lookup fails.
    """
    if not entity_type:
        return None
    try:
        from autom8_asana.dataframes.models.registry import SchemaRegistry
        from autom8_asana.services.resolver import to_pascal_case

        registry = SchemaRegistry.get_instance()
        registry_key = to_pascal_case(entity_type)
        schema = registry.get_schema(registry_key)
        return schema.version if schema else None
    except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as e:
        logger.warning(
            "schema_version_lookup_failed",
            extra={"entity_type": entity_type, "error": str(e)},
        )
        return None
