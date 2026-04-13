"""Shared utilities for Asana custom field data handling.

Extracted from automation/seeding.py to break the lifecycle -> automation
package-level cycle. These are generic helpers for working with Asana custom
field data that may be dicts or objects depending on Pydantic deserialization.
"""

from __future__ import annotations

from typing import Any


def get_field_attr(field_obj: Any, attr: str, default: Any = None) -> Any:
    """Get attribute from a custom field item, handling both dict and object types.

    The Asana API returns custom field data that Pydantic may deserialize as either
    dicts or objects depending on context. This helper safely accesses attributes
    from either format.

    Args:
        field_obj: Custom field item (dict or object).
        attr: Attribute name to access (e.g., "name", "gid", "resource_subtype").
        default: Value to return if attribute is not found.

    Returns:
        The attribute value, or default if not found.
    """
    if field_obj is None:
        return default

    # Try dict access first (most common case)
    if isinstance(field_obj, dict):
        return field_obj.get(attr, default)

    # Try attribute access (for object types)
    return getattr(field_obj, attr, default)


def to_dict(field_obj: Any) -> dict[str, Any]:
    """Convert a custom field item to a dict, handling both dict and object types.

    This ensures consistent dict format for CustomFieldAccessor which expects dicts.

    Args:
        field_obj: Custom field item (dict or object).

    Returns:
        Dict representation of the field.
    """
    if field_obj is None:
        return {}

    if isinstance(field_obj, dict):
        return field_obj

    # Convert object to dict by extracting known attributes
    result: dict[str, Any] = {}

    # Core field attributes
    for attr in [
        "gid",
        "name",
        "resource_subtype",
        "text_value",
        "number_value",
        "enum_value",
        "multi_enum_values",
        "enum_options",
        "enabled",
        "display_value",
        "people_value",
        "date_value",
    ]:
        value = getattr(field_obj, attr, None)
        if value is not None:
            # Recursively convert nested objects (like enum_options)
            if isinstance(value, list):
                result[attr] = [
                    to_dict(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                    for v in value
                ]
            elif isinstance(value, dict):
                result[attr] = value
            elif not isinstance(value, (str, int, float, bool, type(None))):
                # Nested object like enum_value
                result[attr] = to_dict(value)
            else:
                result[attr] = value

    return result


def normalize_custom_fields(custom_fields: list[Any] | None) -> list[dict[str, Any]]:
    """Normalize a list of custom fields to dict format.

    Args:
        custom_fields: List of custom field items (dicts or objects).

    Returns:
        List of custom field dicts.
    """
    if not custom_fields:
        return []
    return [to_dict(f) for f in custom_fields]
