"""Default implementation of CustomFieldResolver.

Per TDD-0009.1: Builds a name->gid index from the first task's custom_fields,
then uses that index for all subsequent lookups.

Thread-safe for concurrent extraction using RLock.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.dataframes.resolver.normalizer import NameNormalizer

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import ColumnDef
    from autom8_asana.models.custom_field import CustomField
    from autom8_asana.models.task import Task


logger = get_logger(__name__)


class DefaultCustomFieldResolver:
    """Default implementation of CustomFieldResolver.

    Builds a name->gid index from the first task's custom_fields,
    then uses that index for all subsequent lookups.

    Thread-safe for concurrent extraction.

    Example:
        >>> resolver = DefaultCustomFieldResolver()
        >>> resolver.build_index(task.custom_fields)
        >>> gid = resolver.resolve("cf:MRR")
        >>> value = resolver.get_value(task, "cf:MRR")

    Attributes:
        strict: If True, raise KeyError on missing fields. Default False.
    """

    def __init__(self, strict: bool = False) -> None:
        """Initialize resolver.

        Args:
            strict: If True, raise KeyError on missing fields.
                    If False (default), return None for missing fields.
        """
        self._strict = strict
        self._index: dict[str, str] = {}  # normalized_name -> gid
        self._gid_to_info: dict[str, dict[str, Any]] = {}  # gid -> field info
        self._built = False
        self._lock = threading.RLock()
        self._unresolved: set[str] = set()

    def build_index(self, custom_fields: list[CustomField]) -> None:
        """Build name->gid index from custom fields.

        Only builds once; subsequent calls are no-ops (idempotent).
        Thread-safe with double-checked locking.

        Args:
            custom_fields: List of CustomField objects from task
        """
        if self._built:
            return

        with self._lock:
            if self._built:
                return

            duplicates: dict[str, list[str]] = {}

            for cf in custom_fields:
                if not cf.gid or not cf.name:
                    continue

                normalized = NameNormalizer.normalize(cf.name)

                # Track duplicates for warning
                if normalized in self._index:
                    existing_gid = self._index[normalized]
                    if normalized not in duplicates:
                        duplicates[normalized] = [existing_gid]
                    duplicates[normalized].append(cf.gid)
                    # First match wins - don't overwrite
                    continue

                self._index[normalized] = cf.gid
                self._gid_to_info[cf.gid] = {
                    "name": cf.name,
                    "type": cf.resource_subtype,
                    "normalized": normalized,
                }

            # Log warnings for duplicates
            for normalized, gids in duplicates.items():
                logger.warning(
                    "Duplicate custom field name after normalization",
                    extra={
                        "normalized_name": normalized,
                        "gids": gids,
                        "using_gid": self._index[normalized],
                    },
                )

            self._built = True
            logger.debug(
                "Custom field index built",
                extra={"indexed_fields": len(self._index)},
            )

    def resolve(self, field_name: str) -> str | None:
        """Resolve field name to GID.

        Handles prefixes:
            - "gid:123" -> return "123" directly
            - "cf:Name" -> resolve "Name" by normalized lookup
            - "name" -> resolve "name" by normalized lookup

        Args:
            field_name: Field name with optional prefix

        Returns:
            GID if resolvable, None otherwise
        """
        # Handle gid: prefix (explicit GID - bypass resolution)
        if field_name.startswith("gid:"):
            return field_name[4:]

        # Handle cf: prefix (explicit custom field name)
        lookup_name = field_name[3:] if field_name.startswith("cf:") else field_name

        normalized = NameNormalizer.normalize(lookup_name)
        gid = self._index.get(normalized)

        if gid is None:
            self._unresolved.add(field_name)

        return gid

    def get_value(
        self,
        task: Task,
        field_name: str,
        *,
        column_def: ColumnDef | None = None,
    ) -> Any:
        """Extract custom field value from task.

        Args:
            task: Task to extract from
            field_name: Schema field name (with optional prefix)
            column_def: Optional column definition for schema-aware coercion

        Returns:
            Extracted value (coerced if column_def provided), or None

        Note:
            When column_def is provided, its dtype is used for coercion.

        Raises:
            KeyError: If strict mode and field not found
        """
        gid = self.resolve(field_name)

        if gid is None:
            if self._strict:
                raise KeyError(f"Cannot resolve custom field: {field_name}")
            return None

        # Find custom field in task by GID
        # Note: task.custom_fields is list[dict[str, Any]] in the model
        for cf_data in task.custom_fields or []:
            cf_gid = (
                cf_data.get("gid") if isinstance(cf_data, dict) else getattr(cf_data, "gid", None)
            )
            if cf_gid == gid:
                raw_value = self._extract_raw_value(cf_data)

                # Schema-aware coercion
                if column_def is not None:
                    return self._coerce_with_schema(raw_value, column_def, cf_data)

                return raw_value

        return None

    def _coerce_with_schema(
        self,
        value: Any,
        column_def: ColumnDef,
        cf_data: dict[str, Any] | Any,
    ) -> Any:
        """Coerce value using schema dtype.

        Args:
            value: Raw value from Asana API
            column_def: Column definition with target dtype
            cf_data: Custom field data for source type info

        Returns:
            Coerced value
        """
        from autom8_asana.dataframes.resolver.coercer import coerce_value

        # Get source type from custom field data
        source_type = (
            cf_data.get("resource_subtype")
            if isinstance(cf_data, dict)
            else getattr(cf_data, "resource_subtype", None)
        )

        return coerce_value(
            value,
            column_def.dtype,
            source_type=source_type,
        )

    def has_field(self, field_name: str) -> bool:
        """Check if field is resolvable.

        Args:
            field_name: Schema field name (with optional prefix)

        Returns:
            True if field can be resolved to a GID
        """
        return self.resolve(field_name) is not None

    def _extract_raw_value(self, cf_data: dict[str, Any] | Any) -> Any:
        """Extract raw value based on custom field type.

        Args:
            cf_data: Custom field data (dict or CustomField-like object)

        Returns:
            Raw value extracted based on resource_subtype
        """

        def get_attr(key: str, default: Any = None) -> Any:
            """Get attribute from dict or object."""
            if isinstance(cf_data, dict):
                return cf_data.get(key, default)
            return getattr(cf_data, key, default)

        resource_subtype = get_attr("resource_subtype")

        match resource_subtype:
            case "text":
                return get_attr("text_value")
            case "number":
                return get_attr("number_value")
            case "enum":
                enum_value = get_attr("enum_value")
                if enum_value is None:
                    return None
                if isinstance(enum_value, dict):
                    return enum_value.get("name")
                return getattr(enum_value, "name", None)
            case "multi_enum":
                multi_values = get_attr("multi_enum_values") or []
                result: list[str] = []
                for opt in multi_values:
                    name = opt.get("name") if isinstance(opt, dict) else getattr(opt, "name", None)
                    if name:
                        result.append(name)
                return result
            case "date":
                date_value = get_attr("date_value")
                if isinstance(date_value, dict):
                    return date_value.get("date")
                return date_value
            case "people":
                people = get_attr("people_value") or []
                gid_result: list[str] = []
                for p in people:
                    gid = p.get("gid") if isinstance(p, dict) else getattr(p, "gid", None)
                    if gid:
                        gid_result.append(gid)
                return gid_result
            case _:
                # Fallback to display_value
                return get_attr("display_value")

    def get_resolution_stats(self) -> dict[str, Any]:
        """Get statistics about resolved fields (for debugging).

        Returns:
            Dict with index statistics
        """
        return {
            "indexed_fields": len(self._index),
            "field_names": list(self._gid_to_info.values()),
            "unresolved_lookups": list(self._unresolved),
            "cache_info": NameNormalizer.cache_info(),
        }

    def get_unresolved_fields(self) -> list[str]:
        """Get list of field names that failed resolution.

        Per FR-MISSING-004: Track which fields failed resolution.

        Returns:
            List of field names that could not be resolved
        """
        return list(self._unresolved)

    def clear_cache(self) -> None:
        """Clear the resolution index and allow rebuilding.

        Per FR-CACHE-004: Provide cache invalidation method.
        """
        with self._lock:
            self._index.clear()
            self._gid_to_info.clear()
            self._unresolved.clear()
            self._built = False
            logger.debug("Resolution cache cleared")
