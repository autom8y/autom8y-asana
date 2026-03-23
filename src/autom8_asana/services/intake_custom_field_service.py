"""Service for intake custom field write operations.

Resolves field descriptor names to Asana custom field GIDs via SchemaRegistry,
then writes all resolved fields in a single Asana API update call.

Simpler than the full FieldWriteService -- does not require entity_type upfront.
Detects entity type from the task's project membership.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.api.routes.intake_custom_fields_models import CustomFieldWriteResponse

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)


class IntakeCustomFieldService:
    """Write custom fields by descriptor name, resolving to Asana field GIDs.

    Detects entity type from task project membership and uses SchemaRegistry
    to resolve field names to Asana custom field GIDs.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def write_fields(
        self,
        task_gid: str,
        fields: dict[str, str | int | float | bool | None],
    ) -> CustomFieldWriteResponse:
        """Write custom field values to an Asana task.

        Args:
            task_gid: Asana task GID.
            fields: Dict of field_name -> value.

        Returns:
            CustomFieldWriteResponse with write count and errors.

        Raises:
            LookupError: If task_gid is not found in Asana.
        """
        # Fetch task to get project context and current custom fields
        task_data = await self._client.tasks.get_async(
            task_gid,
            opt_fields=["memberships", "custom_fields"],
        )

        # Extract current custom fields for name -> GID mapping
        current_custom_fields = (
            task_data.get("custom_fields", [])
            if isinstance(task_data, dict)
            else getattr(task_data, "custom_fields", []) or []
        )

        # Build name -> GID mapping from current task's custom fields
        field_name_to_gid: dict[str, str] = {}
        field_gid_to_meta: dict[str, dict[str, Any]] = {}
        for cf in current_custom_fields:
            cf_name = cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            cf_gid = cf.get("gid", "") if isinstance(cf, dict) else getattr(cf, "gid", "")
            cf_subtype = cf.get("resource_subtype", "") if isinstance(cf, dict) else getattr(cf, "resource_subtype", "")
            if cf_name and cf_gid:
                # Map both the raw name and a normalized version
                field_name_to_gid[cf_name.lower()] = cf_gid
                # Also map snake_case descriptor name
                descriptor = cf_name.lower().replace(" ", "_")
                field_name_to_gid[descriptor] = cf_gid
                field_gid_to_meta[cf_gid] = {
                    "name": cf_name,
                    "resource_subtype": cf_subtype,
                    "enum_options": cf.get("enum_options", []) if isinstance(cf, dict) else getattr(cf, "enum_options", []) or [],
                }

        # Also try SchemaRegistry for more comprehensive field resolution
        self._enrich_from_schema_registry(field_name_to_gid, field_gid_to_meta, task_data)

        # Resolve fields and build Asana custom_fields dict
        custom_fields_payload: dict[str, Any] = {}
        errors: list[str] = []

        for field_name, value in fields.items():
            gid = field_name_to_gid.get(field_name.lower())
            if gid is None:
                # Try snake_case normalized version
                normalized = field_name.lower().replace(" ", "_")
                gid = field_name_to_gid.get(normalized)

            if gid is None:
                errors.append(field_name)
                logger.warning(
                    "custom_field_not_resolved",
                    extra={"task_gid": task_gid, "field_name": field_name},
                )
                continue

            # Format value for Asana API
            formatted_value = self._format_value_for_asana(
                value, gid, field_gid_to_meta.get(gid, {})
            )
            custom_fields_payload[gid] = formatted_value

        # Write resolved fields in a single Asana API call
        fields_written = 0
        if custom_fields_payload:
            try:
                await self._client.tasks.update_async(
                    task_gid,
                    data={"custom_fields": custom_fields_payload},
                )
                fields_written = len(custom_fields_payload)
            except Exception as exc:
                logger.error(
                    "custom_field_write_failed",
                    extra={
                        "task_gid": task_gid,
                        "field_count": len(custom_fields_payload),
                        "error": str(exc),
                    },
                )
                raise

        return CustomFieldWriteResponse(
            task_gid=task_gid,
            fields_written=fields_written,
            errors=errors,
        )

    def _enrich_from_schema_registry(
        self,
        field_name_to_gid: dict[str, str],
        field_gid_to_meta: dict[str, dict[str, Any]],
        task_data: Any,
    ) -> None:
        """Try to enrich field mapping from SchemaRegistry.

        This provides more comprehensive mapping including fields
        that may not be on the current task (e.g., unset fields).
        """
        try:
            from autom8_asana.dataframes.models.registry import SchemaRegistry

            registry = SchemaRegistry.get_instance()
            # Try each registered schema looking for matching columns
            for entity_type in ("Business", "Unit", "Contact", "Offer"):
                try:
                    schema = registry.get_schema(entity_type)
                    if schema is None:
                        continue
                    for col in schema.columns:
                        if col.source and col.name:
                            field_name_to_gid[col.name.lower()] = col.source
                            descriptor = col.name.lower().replace(" ", "_")
                            field_name_to_gid[descriptor] = col.source
                except Exception:
                    continue
        except Exception:
            # SchemaRegistry not available -- rely on task's custom fields
            pass

    def _format_value_for_asana(
        self,
        value: str | int | float | bool | None,
        field_gid: str,
        field_meta: dict[str, Any],
    ) -> Any:
        """Format a value for the Asana API.

        Handles enum resolution (value name -> GID) and type coercion.
        """
        if value is None:
            return None

        resource_subtype = field_meta.get("resource_subtype", "")

        # Enum fields: resolve value name to option GID
        if resource_subtype == "enum" and isinstance(value, str):
            enum_options = field_meta.get("enum_options", [])
            for opt in enum_options:
                opt_name = opt.get("name", "") if isinstance(opt, dict) else getattr(opt, "name", "")
                if opt_name.lower() == value.lower():
                    return opt.get("gid") if isinstance(opt, dict) else getattr(opt, "gid", value)
            # No matching enum option -- return raw value (Asana may reject)
            return value

        # Number fields: ensure numeric type
        if resource_subtype == "number":
            if isinstance(value, (int, float)):
                return value
            try:
                return float(value) if "." in str(value) else int(value)
            except (ValueError, TypeError):
                return value

        # Text fields and others: return as-is
        return str(value) if not isinstance(value, (int, float, bool)) else value


__all__ = [
    "IntakeCustomFieldService",
]
