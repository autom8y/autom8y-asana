"""Custom field accessor for fluent API.

Provides set/get/remove methods with automatic name->GID resolution.
"""

from __future__ import annotations

from typing import Any, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver


# Sentinel for missing values in __getitem__
_MISSING = object()


class CustomFieldAccessor:
    """Fluent API wrapper for custom fields with optional strict name resolution.

    Provides set/get methods with automatic name->GID resolution.
    Tracks modifications for change detection.

    Per TDD-TRIAGE-FIXES Issue #1: Fail-fast on unknown field names in strict mode.

    Example:
        task.custom_fields.set("Priority", "High")
        task.custom_fields.set("MRR", Decimal("1000.50"))
        value = task.custom_fields.get("Priority")

    The accessor wraps a list of custom field dicts from the API:
    [{"gid": "123", "name": "Priority", "text_value": "High"}, ...]

    Attributes:
        strict: If True (default), raise NameNotFoundError on unknown names.
                If False, return name as-is (legacy behavior).
    """

    def __init__(
        self,
        data: list[dict[str, Any]] | None = None,
        resolver: DefaultCustomFieldResolver | None = None,
        strict: bool = True,
    ) -> None:
        """Initialize accessor.

        Args:
            data: Raw custom field list from API response.
            resolver: Optional resolver for name->GID lookup.
            strict: If True (default), raise NameNotFoundError on unknown names.
                   If False, return name as-is (legacy, deprecated).
        """
        self._data: list[dict[str, Any]] = list(data) if data else []
        self._resolver = resolver
        self._strict = strict
        self._modifications: dict[str, Any] = {}  # gid -> new_value (or None for removal)
        self._name_to_gid: dict[str, str] = {}  # Cache name->gid from data
        self._build_index()

    def _build_index(self) -> None:
        """Build name->gid index from existing data."""
        for field in self._data:
            gid = field.get("gid")
            name = field.get("name")
            if gid and name:
                # Normalize name for case-insensitive lookup
                self._name_to_gid[name.lower().strip()] = gid

    def set(self, name_or_gid: str, value: Any) -> None:
        """Set custom field value by name or GID.

        Per TDD-TRIAGE-FIXES Issue #3: Type validation at set time.

        Args:
            name_or_gid: Field name or GID.
            value: Field value (type must match field's resource_subtype).

        Raises:
            GidValidationError: If value type doesn't match field type.
        """
        gid = self._resolve_gid(name_or_gid)

        # Validate type before storing
        self._validate_type(gid, value)

        self._modifications[gid] = value

    def get(self, name_or_gid: str, default: Any = None) -> Any:
        """Get custom field value by name or GID.

        Args:
            name_or_gid: Field name or GID.
            default: Value to return if field not found.

        Returns:
            Field value or default.
        """
        gid = self._resolve_gid(name_or_gid)

        # Check modifications first
        if gid in self._modifications:
            return self._modifications[gid]

        # Find in original data
        for field in self._data:
            if field.get("gid") == gid:
                return self._extract_value(field)

        return default

    def remove(self, name_or_gid: str) -> None:
        """Remove custom field (set to null).

        Args:
            name_or_gid: Field name or GID.
        """
        gid = self._resolve_gid(name_or_gid)
        self._modifications[gid] = None

    def __getitem__(self, key: str) -> Any:
        """Get custom field value using dictionary syntax.

        Args:
            key: Custom field name or GID.

        Returns:
            Field value.

        Raises:
            KeyError: If field doesn't exist (consistent with dict behavior).

        Example:
            >>> accessor["Priority"]
            "High"
        """
        result = self.get(key, default=_MISSING)
        if result is _MISSING:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, value: Any) -> None:
        """Set custom field value using dictionary syntax.

        Args:
            key: Custom field name or GID.
            value: New value (type depends on field type).

        Example:
            >>> accessor["Priority"] = "High"

        Side Effects:
            Marks CustomFieldAccessor as having changes (tracked by has_changes()).
        """
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        """Delete custom field value using dictionary syntax.

        Args:
            key: Custom field name or GID.

        Raises:
            KeyError: If field doesn't exist.

        Example:
            >>> del accessor["Priority"]

        Side Effects:
            Marks field for removal (set to None) and marks changes.
        """
        # Verify field exists before deleting
        _ = self[key]  # This will raise KeyError if field doesn't exist
        self.remove(key)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to API payload format.

        Returns list of custom field dicts with modifications applied.
        Format: [{"gid": "123", "value": ...}, ...]
        """
        result: list[dict[str, Any]] = []

        # Include original fields with modifications
        seen_gids: set[str] = set()
        for field in self._data:
            gid = field.get("gid")
            if not gid:
                continue
            seen_gids.add(gid)

            if gid in self._modifications:
                # Modified field
                result.append({"gid": gid, "value": self._modifications[gid]})
            else:
                # Unchanged - include original value
                result.append({"gid": gid, "value": self._extract_value(field)})

        # Add new fields (gids not in original data)
        for gid, value in self._modifications.items():
            if gid not in seen_gids:
                result.append({"gid": gid, "value": value})

        return result

    def to_api_dict(self) -> dict[str, Any]:
        """Convert modifications to Asana API payload format.

        Per ADR-0056: Asana's API expects custom_fields as a dictionary
        mapping field GID to value, not an array of objects.

        Returns:
            Dict mapping field GID to formatted value.
        """
        result: dict[str, Any] = {}
        for gid, value in self._modifications.items():
            result[gid] = self._format_value_for_api(value)
        return result

    def _format_value_for_api(self, value: Any) -> Any:
        """Format a value for the Asana API.

        Handles: text (string), number, enum (GID), multi-enum (list of GIDs),
        people (list of user GIDs), None (to clear).

        Per TDD-TRIAGE-FIXES Issue #3: Support Decimal for precision.
        """
        from decimal import Decimal

        if value is None:
            return None

        # Handle Decimal → float conversion for API
        if isinstance(value, Decimal):
            return float(value)

        # Multi-enum and People: list of GIDs
        if isinstance(value, list):
            formatted = []
            for item in value:
                if isinstance(item, dict) and "gid" in item:
                    formatted.append(item["gid"])
                elif isinstance(item, str):
                    formatted.append(item)
                elif hasattr(item, "gid"):
                    formatted.append(item.gid)
                else:
                    formatted.append(item)
            return formatted

        # Enum: extract GID if dict
        if isinstance(value, dict) and "gid" in value:
            return value["gid"]

        # Model objects with gid attribute
        if hasattr(value, "gid"):
            return value.gid

        # Text, Number, Date: return as-is
        return value

    def has_changes(self) -> bool:
        """Check if any modifications are pending."""
        return len(self._modifications) > 0

    def clear_changes(self) -> None:
        """Clear all pending modifications."""
        self._modifications.clear()

    def list_available_fields(self) -> list[str]:
        """List all available custom field names for this task.

        Returns:
            Sorted list of custom field names (from local data only, not resolver).

        Raises:
            None - always succeeds, returns empty list if no fields.

        Example:
            >>> accessor = task.custom_fields
            >>> available = accessor.list_available_fields()
            >>> print(available)
            ['Budget', 'Priority', 'Status', 'Team']
        """
        if not self._data:
            return []

        # Extract field names from data
        names = []
        for field in self._data:
            name = field.get("name")
            if name:  # Only include non-empty names
                names.append(name)

        # Remove duplicates and sort alphabetically
        return sorted(list(set(names)))

    def _resolve_gid(self, name_or_gid: str) -> str:
        """Resolve field name to GID with optional strict validation.

        Per TDD-TRIAGE-FIXES Issue #1: Fail-fast on unknown names in strict mode.

        Args:
            name_or_gid: Field name or GID (numeric string).

        Returns:
            GID (always a string).

        Raises:
            NameNotFoundError: If name not found and strict=True.
            (No error if strict=False - returns input as-is).
        """
        # Check if this looks like a GID (all digits or already known GID)
        # Numeric strings are GIDs (e.g., "1234567890")
        if name_or_gid.isdigit():
            return name_or_gid

        # Try local index first (case-insensitive lookup)
        normalized = name_or_gid.lower().strip()
        if normalized in self._name_to_gid:
            return self._name_to_gid[normalized]

        # Check if input matches a GID exactly (in case resolver stores GIDs with non-digit chars)
        for field in self._data:
            if field.get("gid") == name_or_gid:
                return name_or_gid

        # Try resolver if available
        if self._resolver:
            try:
                resolved = self._resolver.resolve(name_or_gid)
                if resolved:
                    return resolved
            except (KeyError, AttributeError, Exception):
                # Resolver failed, continue to strict mode check
                pass

        # Name not found anywhere - decide based on strict mode
        if self._strict:
            from difflib import get_close_matches

            from autom8_asana.exceptions import NameNotFoundError

            # Get available field names for suggestions
            available = self.list_available_fields()

            # Use difflib to find close matches (fuzzy)
            suggestions = get_close_matches(
                name_or_gid, available, n=3, cutoff=0.6
            )

            # Raise error with suggestions
            raise NameNotFoundError(
                resource_type="custom_field",
                name=name_or_gid,
                scope="task",
                suggestions=suggestions,
                available_names=available if len(available) <= 20 else None,
            )

        # Non-strict mode: return input as-is (legacy behavior)
        return name_or_gid

    def _extract_value(self, field: dict[str, Any]) -> Any:
        """Extract value from custom field dict based on type."""
        # Asana stores values in type-specific fields
        if "text_value" in field and field["text_value"] is not None:
            return field["text_value"]
        if "number_value" in field and field["number_value"] is not None:
            return field["number_value"]
        if "enum_value" in field and field["enum_value"] is not None:
            # enum_value is a dict with gid/name
            return field["enum_value"]
        if "multi_enum_values" in field and field["multi_enum_values"]:
            return field["multi_enum_values"]
        if "date_value" in field and field["date_value"] is not None:
            return field["date_value"]
        if "people_value" in field and field["people_value"]:
            return field["people_value"]
        # Fallback to display_value
        return field.get("display_value")

    def _validate_type(self, gid: str, value: Any) -> None:
        """Validate value type against field's resource_subtype.

        Per TDD-TRIAGE-FIXES Issue #3: Type validation at set() time.

        Args:
            gid: Field GID.
            value: Value to validate.

        Raises:
            GidValidationError: If value type doesn't match field type.
        """
        from autom8_asana.persistence.exceptions import GidValidationError
        from decimal import Decimal

        if value is None:
            return  # None is always valid (clears the field)

        # Find field by GID
        field = next((f for f in self._data if f.get("gid") == gid), None)
        if not field:
            return  # Field not found (will be caught by _resolve_gid())

        field_type = field.get("resource_subtype", "unknown")
        field_name = field.get("name", gid)

        # Validate based on field type
        if field_type == "text":
            if not isinstance(value, str):
                raise GidValidationError(
                    f"Custom field '{field_name}' expects text (str), got {type(value).__name__}. "
                    f"Field type: text. Provided value: {value!r}. "
                    f"Expected types: str or None."
                )

        elif field_type == "number":
            if not isinstance(value, (int, float, Decimal)):
                raise GidValidationError(
                    f"Custom field '{field_name}' expects number, got {type(value).__name__}. "
                    f"Field type: number. Provided value: {value!r}. "
                    f"Expected types: int, float, Decimal, or None."
                )

        elif field_type == "enum":
            if not isinstance(value, (str, dict)):
                raise GidValidationError(
                    f"Custom field '{field_name}' expects enum, got {type(value).__name__}. "
                    f"Field type: enum. Provided value: {value!r}. "
                    f"Expected types: str (enum name/GID) or dict with 'gid' key, or None."
                )
            if isinstance(value, dict) and "gid" not in value:
                raise GidValidationError(
                    f"Custom field '{field_name}' expects dict with 'gid' key. "
                    f"Field type: enum. Provided dict keys: {list(value.keys())}. "
                    f"Expected: dict with 'gid' key, or None."
                )

        elif field_type == "multi_enum":
            if not isinstance(value, list):
                raise GidValidationError(
                    f"Custom field '{field_name}' expects multi_enum (list), got {type(value).__name__}. "
                    f"Field type: multi_enum. Provided value: {value!r}. "
                    f"Expected types: list of enum GIDs, or None."
                )

        elif field_type == "date":
            if not isinstance(value, str):
                raise GidValidationError(
                    f"Custom field '{field_name}' expects date (ISO string), got {type(value).__name__}. "
                    f"Field type: date. Provided value: {value!r}. "
                    f"Expected types: str (ISO date like '2025-12-12'), or None."
                )

        elif field_type == "people":
            if not isinstance(value, list):
                raise GidValidationError(
                    f"Custom field '{field_name}' expects people (list), got {type(value).__name__}. "
                    f"Field type: people. Provided value: {value!r}. "
                    f"Expected types: list of user GIDs, or None."
                )

    def __len__(self) -> int:
        """Return number of custom fields."""
        return len(self._data)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over custom field dicts."""
        return iter(self._data)
