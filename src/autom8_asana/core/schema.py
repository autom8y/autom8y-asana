"""Schema version lookup utilities.

Delegates to ``dataframes.models.registry.get_schema_version``. This module
exists for backward compatibility -- callers that already import from
``core.schema`` continue to work without changes.
"""

from __future__ import annotations


def get_schema_version(entity_type: str | None) -> str | None:
    """Look up schema version from SchemaRegistry for an entity type.

    Args:
        entity_type: Entity type in lowercase (e.g., "unit", "contact").
            Returns None if entity_type is None or empty.

    Returns:
        Schema version string if found, None if lookup fails.
    """
    from autom8_asana.dataframes.models.registry import (
        get_schema_version as _get_schema_version,
    )

    return _get_schema_version(entity_type)
