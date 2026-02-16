"""Shared custom field value extraction utilities.

Per IMP-18: DRY extraction of Asana custom field values from dict data.
Used by both DataFrameViewPlugin and CascadeViewPlugin to avoid
duplicated extraction logic.
"""

from __future__ import annotations

from typing import Any


def extract_cf_value(cf_data: dict[str, Any]) -> Any:
    """Extract typed value from an Asana custom field dict.

    Dispatches on ``resource_subtype`` when present, falling back to a
    priority-ordered probe of typed value keys.

    Priority order (fallback path): number_value > text_value >
    enum_value.name > multi_enum_values > display_value.

    Args:
        cf_data: A single custom field dict from the Asana API or cache.

    Returns:
        The extracted value, or ``None`` if no value could be resolved.

    Note:
        Nested values (enum_value, multi_enum_values entries, people_value
        entries) may be dicts **or** model objects with attribute access.
        Both are handled transparently.
    """
    if not isinstance(cf_data, dict):
        return None

    resource_subtype = cf_data.get("resource_subtype")

    match resource_subtype:
        case "text":
            return cf_data.get("text_value")
        case "number":
            return cf_data.get("number_value")
        case "enum":
            return _extract_enum(cf_data.get("enum_value"))
        case "multi_enum":
            return _extract_multi_enum(cf_data.get("multi_enum_values"))
        case "date":
            return _extract_date(cf_data.get("date_value"))
        case "people":
            return _extract_people(cf_data.get("people_value"))
        case _:
            return _extract_fallback(cf_data)


# ── internal helpers ────────────────────────────────────────────────


def _extract_enum(enum_value: Any) -> str | None:
    """Extract name from enum value (dict or object)."""
    if enum_value is None:
        return None
    if isinstance(enum_value, dict):
        return enum_value.get("name")
    return getattr(enum_value, "name", None)


def _extract_multi_enum(multi_values: Any) -> list[str] | None:
    """Extract names from multi-enum values (list of dicts or objects)."""
    items = multi_values or []
    result: list[str] = []
    for opt in items:
        if isinstance(opt, dict):
            name = opt.get("name")
        else:
            name = getattr(opt, "name", None)
        if name:
            result.append(name)
    return result if result else None


def _extract_date(date_value: Any) -> str | None:
    """Extract date string from date value."""
    if isinstance(date_value, dict):
        return date_value.get("date")
    return date_value


def _extract_people(people_value: Any) -> list[str] | None:
    """Extract GIDs from people value (list of dicts or objects)."""
    items = people_value or []
    gids: list[str] = []
    for p in items:
        if isinstance(p, dict):
            gid = p.get("gid")
        else:
            gid = getattr(p, "gid", None)
        if gid:
            gids.append(gid)
    return gids if gids else None


def _extract_fallback(cf_data: dict[str, Any]) -> Any:
    """Fallback extraction when resource_subtype is missing or unknown.

    Probes typed value fields in priority order before falling back
    to display_value.
    """
    if cf_data.get("number_value") is not None:
        return cf_data.get("number_value")
    if cf_data.get("text_value") is not None:
        return cf_data.get("text_value")
    enum_value = cf_data.get("enum_value")
    if enum_value is not None and isinstance(enum_value, dict):
        return enum_value.get("name")
    return cf_data.get("display_value")
