"""Shared custom field value extraction utilities.

Per IMP-18: DRY extraction of Asana custom field values from dict data.
Used by both DataFrameViewPlugin and CascadeViewPlugin to avoid
duplicated extraction logic.

Per TDD-WS3: DRY extraction of shared traversal helpers used by both
CascadingFieldResolver (System B) and CascadeViewPlugin (System C).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.models.business.fields import CascadingFieldDef

from autom8_asana.models.business.detection import EntityType


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
        name = opt.get("name") if isinstance(opt, dict) else getattr(opt, "name", None)
        if name:
            result.append(name)
    return result if result else None


def _extract_date(date_value: Any) -> str | None:
    """Extract date string from date value."""
    if isinstance(date_value, dict):
        return date_value.get("date")
    return str(date_value) if date_value is not None else None


def _extract_people(people_value: Any) -> list[str] | None:
    """Extract GIDs from people value (list of dicts or objects)."""
    items = people_value or []
    gids: list[str] = []
    for p in items:
        gid = p.get("gid") if isinstance(p, dict) else getattr(p, "gid", None)
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


# ── DRY traversal helpers (TDD-WS3) ──────────────────────────────


def class_to_entity_type(cls: type) -> EntityType:
    """Map business model class to EntityType enum.

    Per TDD-WS3 Section 2.2: Extracted from identical 12-entry maps
    in CascadingFieldResolver and CascadeViewPlugin.

    Args:
        cls: Business model class (e.g., Business, Unit).

    Returns:
        Corresponding EntityType enum value, or EntityType.UNKNOWN
        if the class name is not recognized.
    """
    class_name_map: dict[str, EntityType] = {
        "Business": EntityType.BUSINESS,
        "Unit": EntityType.UNIT,
        "Contact": EntityType.CONTACT,
        "ContactHolder": EntityType.CONTACT_HOLDER,
        "UnitHolder": EntityType.UNIT_HOLDER,
        "LocationHolder": EntityType.LOCATION_HOLDER,
        "OfferHolder": EntityType.OFFER_HOLDER,
        "ProcessHolder": EntityType.PROCESS_HOLDER,
        "Offer": EntityType.OFFER,
        "Process": EntityType.PROCESS,
        "Location": EntityType.LOCATION,
        "Hours": EntityType.HOURS,
    }
    return class_name_map.get(cls.__name__, EntityType.UNKNOWN)


def get_custom_field_value(task_or_dict: Any, field_name: str) -> Any:
    """Extract custom field value from a Task object or task dict by name.

    Per TDD-WS3 Section 2.2: Unified replacement for both
    ``_get_custom_field_value`` (Task variant) and
    ``_get_custom_field_value_from_dict`` (dict variant) that existed
    in CascadingFieldResolver and CascadeViewPlugin.

    Uses ``isinstance(task_or_dict, dict)`` to dispatch between dict-based
    cache data and Task objects with attribute access.

    Args:
        task_or_dict: Either a Task object or a task dict (from cache).
        field_name: Custom field name to look up (case-insensitive).

    Returns:
        Field value if found, None otherwise.
    """
    if isinstance(task_or_dict, dict):
        custom_fields = task_or_dict.get("custom_fields")
    else:
        custom_fields = getattr(task_or_dict, "custom_fields", None)

    if not custom_fields:
        return None

    normalized_name = field_name.lower().strip()

    for cf in custom_fields:
        cf_name = cf.get("name") if isinstance(cf, dict) else getattr(cf, "name", None)
        if cf_name and cf_name.lower().strip() == normalized_name:
            return extract_cf_value(cf)

    return None


def get_field_value(task_or_dict: Any, field_def: CascadingFieldDef) -> Any:
    """Extract field value using CascadingFieldDef, checking source_field first.

    Per TDD-WS3 Section 2.2: Key new abstraction that wires the existing
    ``CascadingFieldDef.source_field`` attribute into DataFrame-layer
    resolvers. When ``source_field`` is set (e.g., ``"name"`` for
    BUSINESS_NAME), reads from that attribute/key directly instead of
    searching custom_fields.

    When ``source_field`` is None (the common case), falls through to
    ``get_custom_field_value`` -- no behavior change for existing fields.

    Args:
        task_or_dict: Either a Task object or a task dict (from cache).
        field_def: CascadingFieldDef with field configuration.

    Returns:
        Field value if found, None otherwise.
    """
    if field_def.source_field:
        if isinstance(task_or_dict, dict):
            return task_or_dict.get(field_def.source_field)
        return getattr(task_or_dict, field_def.source_field, None)
    return get_custom_field_value(task_or_dict, field_def.name)
