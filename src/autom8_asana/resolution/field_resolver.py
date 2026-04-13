"""Field resolver for entity write operations.

Extracted from FieldSeeder (automation/seeding.py) per ADR-EW-003.

Stateless utility that resolves business-domain field names to Asana API
payloads. Handles field name matching (core, descriptor, display name),
enum resolution, multi-enum resolution, type validation, text list append,
and date wrapping.

Constructed per-request with the target task's custom field definitions.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ResolvedField:
    """Result of resolving a single field.

    Attributes:
        input_name: The field name as provided by the caller.
        matched_name: The actual Asana field name (or core field key).
        gid: Custom field GID (None for core fields).
        value: The resolved value ready for the Asana API.
        is_core: True if this is a core Asana field (name, assignee, etc.).
        status: "resolved", "skipped", "error".
        error: Error message if status != "resolved".
        suggestions: Fuzzy-match suggestions if field not found.
    """

    input_name: str
    matched_name: str | None = None
    gid: str | None = None
    value: Any = None
    is_core: bool = False
    status: str = "resolved"
    error: str | None = None
    suggestions: list[str] | None = None


def _build_enum_lookup(enum_options: list[dict[str, Any]]) -> dict[str, str]:
    """Build case-insensitive name-to-GID lookup from enum options.

    Maps both lowered option names and raw GID strings to the option GID,
    enabling both name-based and GID passthrough resolution.

    Args:
        enum_options: List of enum option dicts with 'name' and 'gid'.

    Returns:
        Dict mapping lowered names and GID strings to GID values.
    """
    name_to_gid: dict[str, str] = {}
    for option in enum_options:
        opt_name = option.get("name", "")
        opt_gid = option.get("gid", "")
        if opt_name and opt_gid:
            name_to_gid[opt_name.lower().strip()] = opt_gid
            # Also map GID to itself for passthrough
            name_to_gid[opt_gid] = opt_gid
    return name_to_gid


def _resolve_single_option(
    value: Any,
    name_to_gid: dict[str, str],
    enum_options: list[dict[str, Any]],
) -> str | None:
    """Resolve a single string value to an enum option GID.

    Handles GID passthrough (numeric strings validated against known GIDs)
    and case-insensitive name matching.

    Args:
        value: String value to resolve (name or GID).
        name_to_gid: Lookup dict from _build_enum_lookup.
        enum_options: Original enum options list (for logging).

    Returns:
        Resolved GID string, or None if resolution fails.
    """
    value_str = str(value).lower().strip()

    # Check if it's already a GID (numeric string with Asana GID length >= 13 digits).
    # Short numeric strings like "1", "2" are treated as option names, not GIDs.
    # (Fixes D-EW-002: numeric enum option names treated as GID passthroughs)
    if value_str.isdigit() and len(value_str) >= 13:
        if value_str in name_to_gid:
            return value_str
        logger.debug(
            "field_resolver_enum_gid_not_found",
            gid=value,
        )
        return None

    # Name-based lookup (case-insensitive) -- handles both text names and short numeric names
    if value_str in name_to_gid:
        resolved_gid = name_to_gid[value_str]
        logger.debug(
            "field_resolver_enum_resolved",
            value=value,
            resolved_gid=resolved_gid,
        )
        return resolved_gid

    # No match found
    logger.debug(
        "field_resolver_enum_value_not_found",
        value=value,
        available=[opt.get("name", "") for opt in enum_options if opt.get("enabled", True)],
    )
    return None


def _fuzzy_match(name: str, available: list[str], n: int = 3) -> list[str]:
    """Find close matches for a field name using difflib.

    Args:
        name: The unrecognized field name.
        available: List of available field names.
        n: Maximum number of suggestions.

    Returns:
        List of close-match strings.
    """
    return difflib.get_close_matches(name, available, n=n, cutoff=0.6)


def _available_enum_options(field_def: dict[str, Any]) -> list[str]:
    """Extract enabled enum option names from a field definition.

    Args:
        field_def: Custom field dict with enum_options.

    Returns:
        List of enabled option name strings.
    """
    options = field_def.get("enum_options", [])
    return [opt.get("name", "") for opt in options if opt.get("name") and opt.get("enabled", True)]


class FieldResolver:
    """Resolves business-domain field names to Asana API payloads.

    Stateless. Constructed per-request with the target task's
    custom field definitions.

    Args:
        custom_fields_data: List of custom field dicts from the Asana
            task response (with name, gid, resource_subtype, enum_options).
        descriptor_index: Maps snake_case descriptor name -> display name.
            From EntityWriteRegistry.WritableEntityInfo.descriptor_index.
        core_fields: Set of core field keys. From CORE_FIELD_NAMES.
    """

    def __init__(
        self,
        custom_fields_data: list[dict[str, Any]],
        descriptor_index: dict[str, str],
        core_fields: frozenset[str],
    ) -> None:
        self._custom_fields = custom_fields_data
        self._descriptor_index = descriptor_index
        self._core_fields = core_fields

        # Build case-insensitive display name -> field def index
        self._display_index: dict[str, dict[str, Any]] = {}
        for cf in custom_fields_data:
            name = cf.get("name", "")
            if name:
                self._display_index[name.lower().strip()] = cf

    def resolve_fields(
        self,
        fields: dict[str, Any],
        list_mode: str = "replace",
    ) -> list[ResolvedField]:
        """Resolve all fields in a request.

        Resolution order per field:
        1. Check core fields (exact key match).
        2. Check descriptor index (O(1) dict lookup by snake_case).
        3. Fall through to display name scan (case-insensitive).
        4. If no match, produce a "skipped" result with fuzzy suggestions.

        Args:
            fields: Dict of field_name -> value from request body.
            list_mode: "replace" or "append" for list-type fields.

        Returns:
            List of ResolvedField results, one per input field.
        """
        results: list[ResolvedField] = []
        for name, value in fields.items():
            result = self._resolve_single(name, value, list_mode)
            results.append(result)
        return results

    def _resolve_single(self, name: str, value: Any, list_mode: str) -> ResolvedField:
        """Resolve one field name + value."""

        # Step 1: Core field check
        if name in self._core_fields:
            return ResolvedField(
                input_name=name,
                matched_name=name,
                value=value,
                is_core=True,
            )

        # Step 2: Descriptor index lookup
        display_name = self._descriptor_index.get(name)
        if display_name:
            return self._resolve_custom_field(name, display_name, value, list_mode)

        # Step 3: Display name scan (case-insensitive)
        normalized = name.lower().strip()
        field_def = self._display_index.get(normalized)
        if field_def:
            return self._resolve_custom_field(name, field_def["name"], value, list_mode)

        # Step 4: Not found -- fuzzy suggestions
        available = [f.get("name", "") for f in self._custom_fields if f.get("name")]
        suggestions = _fuzzy_match(name, available)
        return ResolvedField(
            input_name=name,
            status="skipped",
            error=f"Field '{name}' not found on entity",
            suggestions=suggestions,
        )

    def _resolve_custom_field(
        self,
        input_name: str,
        display_name: str,
        value: Any,
        list_mode: str,
    ) -> ResolvedField:
        """Resolve a custom field by its display name."""
        normalized = display_name.lower().strip()
        field_def = self._display_index.get(normalized)
        if not field_def:
            return ResolvedField(
                input_name=input_name,
                status="skipped",
                error=f"Field '{display_name}' exists in model but not on Asana task",
            )

        gid = field_def.get("gid")
        field_type = field_def.get("resource_subtype", "")

        # Null clears -- pass through None for any field type
        if value is None:
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value=None,
            )

        # Type validation
        type_error = self._validate_type(field_type, value, input_name)
        if type_error:
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                status="error",
                error=type_error,
            )

        # Enum resolution
        if field_type == "enum":
            resolved_value = self._resolve_enum(field_def, value)
            if resolved_value is None:
                options = _available_enum_options(field_def)
                return ResolvedField(
                    input_name=input_name,
                    matched_name=display_name,
                    gid=gid,
                    status="skipped",
                    error=f"Enum value '{value}' not found",
                    suggestions=options,
                )
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value=resolved_value,
            )

        if field_type == "multi_enum":
            multi_value, unresolved = self._resolve_multi_enum(field_def, value, list_mode)
            if not multi_value and unresolved:
                # All values failed resolution -- report as error with available options
                options = _available_enum_options(field_def)
                return ResolvedField(
                    input_name=input_name,
                    matched_name=display_name,
                    gid=gid,
                    status="skipped",
                    error=(
                        f"No multi-enum values resolved for '{input_name}'. "
                        f"Unresolved: {unresolved}"
                    ),
                    suggestions=options,
                )
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value=multi_value,
            )

        # TextListField append handling
        if field_type == "text" and list_mode == "append" and isinstance(value, (str, list)):
            resolved_value = self._resolve_text_append(field_def, value)
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value=resolved_value,
            )

        # Date wrapping
        if field_type == "date" and isinstance(value, str):
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value={"date": value},
            )

        # Pass-through for text, number, people, etc.
        return ResolvedField(
            input_name=input_name,
            matched_name=display_name,
            gid=gid,
            value=value,
        )

    # ------------------------------------------------------------------
    # Enum resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_enum(field_def: dict[str, Any], value: Any) -> str | None:
        """Resolve a single enum value to its option GID.

        Args:
            field_def: Custom field dict with enum_options.
            value: String name or numeric GID.

        Returns:
            Option GID string, or None if not found.
        """
        enum_options = field_def.get("enum_options", [])
        if not enum_options:
            return None
        lookup = _build_enum_lookup(enum_options)
        return _resolve_single_option(value, lookup, enum_options)

    @staticmethod
    def _resolve_multi_enum(
        field_def: dict[str, Any],
        value: Any,
        list_mode: str,
    ) -> tuple[list[str], list[str]]:
        """Resolve multi-enum values with optional append.

        Args:
            field_def: Custom field dict with enum_options and multi_enum_values.
            value: Single value or list of values.
            list_mode: "replace" or "append".

        Returns:
            Tuple of (resolved_gids, unresolved_items).
            resolved_gids: List of resolved option GIDs.
            unresolved_items: List of input values that could not be matched.
        """
        enum_options = field_def.get("enum_options", [])
        lookup = _build_enum_lookup(enum_options)

        if not isinstance(value, list):
            value = [value]

        resolved_gids: list[str] = []
        unresolved: list[str] = []
        for item in value:
            gid = _resolve_single_option(item, lookup, enum_options)
            if gid:
                resolved_gids.append(gid)
            else:
                unresolved.append(str(item))

        if unresolved:
            field_name = field_def.get("name", "unknown")
            available = [
                opt.get("name", "")
                for opt in enum_options
                if opt.get("name") and opt.get("enabled", True)
            ]
            logger.warning(
                "multi_enum_option_mismatch",
                extra={
                    "field_name": field_name,
                    "unresolved_values": unresolved,
                    "resolved_count": len(resolved_gids),
                    "total_count": len(value),
                    "available_options": available,
                },
            )

        if list_mode == "append":
            # Merge with existing selections
            existing = field_def.get("multi_enum_values") or []
            existing_gids = [
                opt["gid"] for opt in existing if isinstance(opt, dict) and "gid" in opt
            ]
            # Dedup: add only new GIDs
            combined = list(existing_gids)
            for gid in resolved_gids:
                if gid not in combined:
                    combined.append(gid)
            return combined, unresolved

        return resolved_gids, unresolved

    # ------------------------------------------------------------------
    # Text append
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_text_append(field_def: dict[str, Any], value: str | list[str]) -> str:
        """Server-side text list append with dedup.

        Reads current text_value from the field definition (already fetched
        with the task), splits on comma delimiter, appends new values,
        deduplicates (preserving order), and re-joins.

        Args:
            field_def: Custom field dict with text_value.
            value: New value(s) to append.

        Returns:
            Comma-delimited string with merged, deduped values.
        """
        current_text = field_def.get("text_value") or ""
        delimiter = ","
        existing = [s.strip() for s in current_text.split(delimiter) if s.strip()]
        new_items = [value] if isinstance(value, str) else value
        for item in new_items:
            item = item.strip()
            if item and item not in existing:
                existing.append(item)
        return delimiter.join(existing)

    # ------------------------------------------------------------------
    # Type validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_type(field_type: str, value: Any, input_name: str) -> str | None:
        """Validate value type against field resource_subtype.

        Args:
            field_type: The field's resource_subtype (text, number, enum, etc.).
            value: The value to validate.
            input_name: Field name for error messages.

        Returns:
            Error message string if validation fails, None if valid.
        """
        if field_type == "number" and not isinstance(value, (int, float)):
            return f"Field '{input_name}' expects a number, got {type(value).__name__}"

        # Allow list for text fields (append mode handles it)
        if field_type == "text" and not isinstance(value, str) and not isinstance(value, list):
            return f"Field '{input_name}' expects text (str), got {type(value).__name__}"

        if field_type == "enum" and not isinstance(value, str):
            return f"Field '{input_name}' expects an enum string, got {type(value).__name__}"

        if field_type == "multi_enum" and not isinstance(value, (list, str)):
            return f"Field '{input_name}' expects a list of enum values, got {type(value).__name__}"

        if field_type == "date" and not isinstance(value, str):
            return f"Field '{input_name}' expects a date string, got {type(value).__name__}"

        return None
