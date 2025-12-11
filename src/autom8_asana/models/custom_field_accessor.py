"""Custom field accessor for fluent API.

Provides set/get/remove methods with automatic name->GID resolution.
"""

from __future__ import annotations

from typing import Any, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver


class CustomFieldAccessor:
    """Fluent API wrapper for custom fields.

    Provides set/get methods with automatic name->GID resolution.
    Tracks modifications for change detection.

    Example:
        task.custom_fields.set("Priority", "High")
        task.custom_fields.set("MRR", Decimal("1000.50"))
        value = task.custom_fields.get("Priority")

    The accessor wraps a list of custom field dicts from the API:
    [{"gid": "123", "name": "Priority", "text_value": "High"}, ...]
    """

    def __init__(
        self,
        data: list[dict[str, Any]] | None = None,
        resolver: DefaultCustomFieldResolver | None = None,
    ) -> None:
        """Initialize accessor.

        Args:
            data: Raw custom field list from API response.
            resolver: Optional resolver for name->GID lookup.
        """
        self._data: list[dict[str, Any]] = list(data) if data else []
        self._resolver = resolver
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

        Args:
            name_or_gid: Field name or GID.
            value: New value (type depends on field type).
        """
        gid = self._resolve_gid(name_or_gid)
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

    def has_changes(self) -> bool:
        """Check if any modifications are pending."""
        return len(self._modifications) > 0

    def clear_changes(self) -> None:
        """Clear all pending modifications."""
        self._modifications.clear()

    def _resolve_gid(self, name_or_gid: str) -> str:
        """Resolve name to GID.

        Args:
            name_or_gid: Field name or GID.

        Returns:
            GID string.

        If input looks like a GID (numeric string), return as-is.
        Otherwise, try resolver, then local index.
        """
        # If it looks like a GID (numeric), return as-is
        if name_or_gid.isdigit():
            return name_or_gid

        # Try local index first (case-insensitive)
        normalized = name_or_gid.lower().strip()
        if normalized in self._name_to_gid:
            return self._name_to_gid[normalized]

        # Try resolver if available
        if self._resolver:
            try:
                resolved = self._resolver.resolve(name_or_gid)
                if resolved:
                    return resolved
            except (KeyError, AttributeError):
                pass

        # Return as-is (might be a GID we don't know about)
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

    def __len__(self) -> int:
        """Return number of custom fields."""
        return len(self._data)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over custom field dicts."""
        return iter(self._data)
