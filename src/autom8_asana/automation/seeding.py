"""Field seeding for pipeline conversion.

Per FR-005: Field seeding from Business/Unit cascade and Process carry-through.
Per ADR-0105: Field Seeding Architecture.
Per FR-SEED-001: Persist seeded values to API.
Per ADR-0112: Custom Field GID Resolution via CustomFieldAccessor.

Field seeding computes initial field values for newly created processes by:
1. Cascading fields from Business (configured per-pipeline, empty by default)
2. Cascading fields from Unit (e.g., Vertical)
3. Carrying through fields from the source process (e.g., Contact Phone, Priority)
4. Computing dynamic fields (e.g., Launch Date = today)

After computation, write_fields_async() persists these values to the API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business import Business, Process, Unit

logger = get_logger(__name__)

# Re-exported from core.field_utils for backward compatibility.
# These were extracted to break the lifecycle -> automation package cycle.
from autom8_asana.core.field_utils import (  # noqa: E402
    get_field_attr,
    normalize_custom_fields,
)


@dataclass
class WriteResult:
    """Result of a field write operation.

    Per FR-SEED-001: Track success status and details of field persistence.

    Attributes:
        success: Whether the write operation completed successfully.
        fields_written: List of field names that were successfully written.
        fields_skipped: List of field names not found on target (skipped with warning).
        error: Error message if the operation failed, None otherwise.
    """

    success: bool
    fields_written: list[str] = field(default_factory=list)
    fields_skipped: list[str] = field(default_factory=list)
    error: str | None = None

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        status = "success" if self.success else f"failed: {self.error}"
        return (
            f"WriteResult({status}, written={len(self.fields_written)}, "
            f"skipped={len(self.fields_skipped)})"
        )


class FieldSeeder:
    """Computes field values from hierarchy and carry-through.

    Per FR-005: Provides field seeding for pipeline conversion.

    Field precedence (later overrides earlier):
    1. Business cascade fields
    2. Unit cascade fields
    3. Process carry-through fields
    4. Computed fields (e.g., Launch Date)

    Field lists can be configured at construction time or via PipelineStage.
    When None is passed for a field list, defaults are used.

    Example:
        seeder = FieldSeeder(client)

        # Seed fields for new onboarding process
        fields = await seeder.seed_fields_async(
            business=business,
            unit=unit,
            source_process=sales_process,
        )
        # fields contains combined cascade + carry-through + computed values

        # With custom field lists (from PipelineStage)
        seeder = FieldSeeder(
            client,
            business_cascade_fields=["Company Name", "Phone"],
            unit_cascade_fields=["Location", "Type"],
        )
    """

    # Default fields that cascade from Business
    # Note: Empty by default - common Business fields like Office Phone, Company ID
    # don't exist on all target projects. Configure per-pipeline via constructor.
    DEFAULT_BUSINESS_CASCADE_FIELDS: list[str] = []

    # Default fields that cascade from Unit
    # Note: Only Vertical exists on common target projects (e.g., Onboarding).
    # Platforms and Booking Type don't exist on Onboarding project.
    DEFAULT_UNIT_CASCADE_FIELDS: list[str] = [
        "Vertical",
    ]

    # Default fields carried through from source Process
    DEFAULT_PROCESS_CARRY_THROUGH_FIELDS: list[str] = [
        "Contact Phone",
        "Priority",
    ]

    def __init__(
        self,
        client: AsanaClient,
        business_cascade_fields: list[str] | None = None,
        unit_cascade_fields: list[str] | None = None,
        process_carry_through_fields: list[str] | None = None,
    ) -> None:
        """Initialize FieldSeeder.

        Args:
            client: AsanaClient for API operations.
            business_cascade_fields: Fields to cascade from Business.
                When None, uses DEFAULT_BUSINESS_CASCADE_FIELDS.
            unit_cascade_fields: Fields to cascade from Unit.
                When None, uses DEFAULT_UNIT_CASCADE_FIELDS.
            process_carry_through_fields: Fields to carry through from Process.
                When None, uses DEFAULT_PROCESS_CARRY_THROUGH_FIELDS.
        """
        self._client = client
        self._business_cascade_fields = (
            business_cascade_fields
            if business_cascade_fields is not None
            else self.DEFAULT_BUSINESS_CASCADE_FIELDS
        )
        self._unit_cascade_fields = (
            unit_cascade_fields
            if unit_cascade_fields is not None
            else self.DEFAULT_UNIT_CASCADE_FIELDS
        )
        self._process_carry_through_fields = (
            process_carry_through_fields
            if process_carry_through_fields is not None
            else self.DEFAULT_PROCESS_CARRY_THROUGH_FIELDS
        )

    async def cascade_from_hierarchy_async(
        self, business: Business | None, unit: Unit | None
    ) -> dict[str, Any]:
        """Collect cascading field values from Business and Unit.

        Per FR-005: Cascades fields from parent entities.

        Fields are collected from Business first, then Unit. If a field
        exists in both, Unit's value takes precedence.

        Args:
            business: Business entity (may be None).
            unit: Unit entity (may be None).

        Returns:
            Dict of field name to value for cascade fields.

        Example:
            fields = await seeder.cascade_from_hierarchy_async(business, unit)
            # fields = {"Office Phone": "555-1234", "Vertical": "Dental", ...}
        """
        fields: dict[str, Any] = {}

        # Cascade from Business
        if business is not None:
            for field_name in self._business_cascade_fields:
                value = self._get_field_value(business, field_name)
                if value is not None:
                    fields[field_name] = value

        # Cascade from Unit (overrides Business values)
        if unit is not None:
            for field_name in self._unit_cascade_fields:
                value = self._get_field_value(unit, field_name)
                if value is not None:
                    fields[field_name] = value

        return fields

    async def carry_through_from_process_async(
        self, source_process: Process
    ) -> dict[str, Any]:
        """Collect carry-through field values from source Process.

        Per FR-005: Carries through fields from the source process.

        These are fields that should be copied from the source process
        (e.g., Sales) to the target process (e.g., Onboarding).

        Args:
            source_process: Source Process entity to copy fields from.

        Returns:
            Dict of field name to value for carry-through fields.

        Example:
            fields = await seeder.carry_through_from_process_async(sales_process)
            # fields = {"Contact Phone": "555-5678", "Priority": "High", ...}
        """
        fields: dict[str, Any] = {}

        for field_name in self._process_carry_through_fields:
            value = self._get_field_value(source_process, field_name)
            if value is not None:
                fields[field_name] = value

        return fields

    async def compute_fields_async(self, source_process: Process) -> dict[str, Any]:
        """Compute dynamic field values.

        Per FR-005: Computes fields like Launch Date = today.

        Args:
            source_process: Source Process (for context, not currently used).

        Returns:
            Dict of computed field name to value.

        Example:
            fields = await seeder.compute_fields_async(sales_process)
            # fields = {"Launch Date": "2024-01-15"}
        """
        today = date.today().isoformat()

        return {
            "Launch Date": today,
        }

    async def seed_fields_async(
        self,
        business: Business | None,
        unit: Unit | None,
        source_process: Process,
    ) -> dict[str, Any]:
        """Combine cascade + carry-through + computed fields.

        Per FR-005: Main seeding method combining all field sources.

        Field precedence (later overrides earlier):
        1. Business cascade fields
        2. Unit cascade fields
        3. Process carry-through fields
        4. Computed fields

        Args:
            business: Business entity (may be None).
            unit: Unit entity (may be None).
            source_process: Source Process entity.

        Returns:
            Combined dict of all seeded field values.

        Example:
            fields = await seeder.seed_fields_async(business, unit, sales_process)
            # Apply to new task via custom_fields update
        """
        logger.info(
            "seeding_fields_async",
            business=getattr(business, "name", None) if business else None,
            unit=getattr(unit, "name", None) if unit else None,
            process=getattr(source_process, "name", None) if source_process else None,
        )

        fields: dict[str, Any] = {}

        # Layer 1 & 2: Cascade from hierarchy
        cascade_fields = await self.cascade_from_hierarchy_async(business, unit)
        logger.info("seeding_cascade_fields_collected", fields=cascade_fields)
        fields.update(cascade_fields)

        # Layer 3: Carry-through from source process
        carry_through_fields = await self.carry_through_from_process_async(
            source_process
        )
        logger.info("seeding_carry_through_collected", fields=carry_through_fields)
        fields.update(carry_through_fields)

        # Layer 4: Computed fields (highest precedence)
        computed_fields = await self.compute_fields_async(source_process)
        logger.info("seeding_computed_fields", fields=computed_fields)
        fields.update(computed_fields)

        logger.info("seeding_final_fields", fields=fields)
        return fields

    async def write_fields_async(
        self,
        target_task_gid: str,
        fields: dict[str, Any],
        field_name_mapping: dict[str, str] | None = None,
        target_task: Any | None = None,
    ) -> WriteResult:
        """Write seeded field values to target task.

        Per FR-SEED-001: Persists computed field values to API.
        Per FR-SEED-002: Uses single update_async() call (batch all fields).
        Per FR-SEED-005: Skip missing fields with warning log.
        Per ADR-0112: Uses CustomFieldAccessor for GID resolution.

        Args:
            target_task_gid: GID of the task to update.
            fields: Dict of field name to value (from seed_fields_async).
            field_name_mapping: Optional mapping from source field names to target
                field names. Use when source and target projects have different
                custom field names. Example: {"Office Phone": "Business Phone"}.
            target_task: Pre-fetched task with custom_fields. When provided,
                skips the task fetch (saves 1 API call). Must include
                custom_fields with name, resource_subtype, and enum_options.

        Returns:
            WriteResult with success status and details.

        Side Effects:
            - Logs warning for fields not found on target (FR-SEED-005)
            - Single API call to update_async() (FR-SEED-002)

        Example:
            seeder = FieldSeeder(client)
            fields = await seeder.seed_fields_async(business, unit, source_process)
            result = await seeder.write_fields_async(new_task.gid, fields)
            if result.success:
                print(f"Wrote {len(result.fields_written)} fields")
        """
        from autom8_asana.models.custom_field_accessor import CustomFieldAccessor

        logger.info(
            "seeding_write_fields_async",
            task_gid=target_task_gid,
            fields=fields,
        )

        if not fields:
            logger.info("seeding_no_fields_to_write")
            return WriteResult(
                success=True,
                fields_written=[],
                fields_skipped=[],
            )

        try:
            # Step 1: Fetch target task with custom field definitions
            # (skip if pre-fetched task provided)
            if target_task is None:
                target_task = await self._client.tasks.get_async(
                    target_task_gid,
                    opt_fields=[
                        "custom_fields",
                        "custom_fields.name",
                        "custom_fields.resource_subtype",
                        "custom_fields.enum_options",
                    ],
                )

            # Normalize custom fields to dicts (may be objects from API)
            # This ensures CustomFieldAccessor receives the expected dict format
            custom_fields_list = normalize_custom_fields(target_task.custom_fields)

            # Step 2: Build accessor from target's field definitions
            # Use strict=False to not fail on unknown fields
            accessor = CustomFieldAccessor(
                data=custom_fields_list,
                strict=False,
            )

            # Step 3: Filter and resolve fields
            fields_to_write: list[str] = []
            fields_skipped: list[str] = []
            logger.info(
                "seeding_target_custom_fields",
                field_names=[get_field_attr(f, "name") for f in custom_fields_list],
            )

            # Apply field name mapping (source name -> target name)
            mapping = field_name_mapping or {}
            mapped_fields: dict[str, Any] = {}
            for source_name, value in fields.items():
                target_name = mapping.get(source_name, source_name)
                mapped_fields[target_name] = value

            logger.info("seeding_mapped_fields", mapped_fields=mapped_fields)

            # Build resource_subtype lookup for post-resolution checks
            # (e.g., skipping empty people fields)
            _subtype_by_name: dict[str, str] = {}
            for cf in custom_fields_list:
                cf_name = cf.get("name", "")
                if cf_name:
                    _subtype_by_name[cf_name.lower().strip()] = cf.get(
                        "resource_subtype", ""
                    )

            # Resolve fields via shared FieldResolver (ADR-EW-003)
            from autom8_asana.resolution.field_resolver import FieldResolver

            resolver = FieldResolver(
                custom_fields_data=custom_fields_list,
                descriptor_index={},  # FieldSeeder uses display names only
                core_fields=frozenset(),  # FieldSeeder never writes core fields
            )
            resolved = resolver.resolve_fields(mapped_fields)

            for rf in resolved:
                if rf.status == "resolved" and rf.gid:
                    # Skip empty/falsy values for people fields (they expect lists)
                    field_subtype = _subtype_by_name.get(
                        (rf.matched_name or "").lower().strip(), ""
                    )
                    if field_subtype == "people" and not rf.value:
                        logger.debug(
                            "seeding_skipping_empty_people_field",
                            field_name=rf.input_name,
                        )
                        fields_skipped.append(rf.input_name)
                        continue

                    assert (
                        rf.matched_name is not None
                    )  # guaranteed when status == "resolved"
                    accessor.set(rf.matched_name, rf.value)
                    fields_to_write.append(rf.matched_name)
                else:
                    if rf.status == "skipped":
                        logger.warning(
                            "seeding_field_not_found",
                            field_name=rf.input_name,
                            task_gid=target_task_gid,
                        )
                    fields_skipped.append(rf.input_name)

            # Step 4: Single API call with all fields (FR-SEED-002)
            if accessor.has_changes():
                logger.info("seeding_api_update", api_dict=accessor.to_api_dict())
                await self._client.tasks.update_async(
                    target_task_gid,
                    custom_fields=accessor.to_api_dict(),
                )
            else:
                logger.info("seeding_no_changes_skipping_api")

            logger.info(
                "seeding_write_result",
                fields_written=fields_to_write,
                fields_skipped=fields_skipped,
            )
            return WriteResult(
                success=True,
                fields_written=fields_to_write,
                fields_skipped=fields_skipped,
            )

        except Exception as e:  # BROAD-CATCH: boundary -- wraps API+accessor+resolution pipeline, must return WriteResult
            logger.error(
                "seeding_write_failed",
                task_gid=target_task_gid,
                error=str(e),
            )
            return WriteResult(
                success=False,
                fields_written=[],
                fields_skipped=list(fields.keys()),
                error=str(e),
            )

    def _get_field_value(self, entity: Any, field_name: str) -> Any:
        """Get field value from entity, handling enums and various sources.

        Tries multiple sources in order:
        1. Descriptor-based field access (snake_case attribute)
        2. Direct attribute access (original name)
        3. CustomFieldAccessor.get() for raw custom field access
        4. Special case handling (Business Name from task name)

        Args:
            entity: Entity to get field from.
            field_name: Field name (display name, e.g., "Office Phone").

        Returns:
            Field value, or None if not found.
        """
        entity_type = type(entity).__name__

        # Convert display name to attribute name (snake_case)
        attr_name = self._to_attr_name(field_name)
        logger.debug(
            "seeding_get_field_value",
            entity_type=entity_type,
            field_name=field_name,
            attr_name=attr_name,
        )

        # Try descriptor-based access first (for business entity models)
        if hasattr(entity, attr_name):
            try:
                value = getattr(entity, attr_name)
                normalized = self._normalize_value(value)
                logger.debug(
                    "seeding_descriptor_access",
                    entity_type=entity_type,
                    attr_name=attr_name,
                    raw_value=repr(value),
                    normalized=repr(normalized),
                )
                # Only return if we got a meaningful value
                # Empty lists from MultiEnumField mean "no value" - check raw field
                if normalized is not None and normalized != []:
                    return normalized
                # Fall through to try raw custom field access
                logger.debug("seeding_descriptor_empty_trying_raw")
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                logger.debug("seeding_descriptor_access_failed", error=str(e))

        # Try raw CustomFieldAccessor access (bypasses descriptors)
        # This handles cases where descriptor returns [] but raw field has data
        if hasattr(entity, "custom_fields_editor"):
            try:
                accessor = entity.custom_fields_editor()
                raw_value = accessor.get(field_name)
                if raw_value is not None:
                    normalized = self._normalize_value(raw_value)
                    logger.debug(
                        "seeding_custom_fields_editor_get",
                        field_name=field_name,
                        raw_value=repr(raw_value),
                        normalized=repr(normalized),
                    )
                    return normalized
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                logger.debug("seeding_custom_fields_editor_failed", error=str(e))

        # Try direct attribute access (for non-descriptor fields)
        if hasattr(entity, field_name):
            try:
                value = getattr(entity, field_name)
                normalized = self._normalize_value(value)
                logger.debug(
                    "seeding_direct_attr_access",
                    entity_type=entity_type,
                    field_name=field_name,
                    raw_value=repr(value),
                    normalized=repr(normalized),
                )
                if normalized is not None:
                    return normalized
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                logger.debug("seeding_direct_attr_failed", error=str(e))

        # Special case: Business Name comes from task name
        if field_name == "Business Name" and hasattr(entity, "name"):
            logger.debug("seeding_using_entity_name", name=entity.name)
            return entity.name

        logger.debug(
            "seeding_no_value_found",
            entity_type=entity_type,
            field_name=field_name,
        )
        return None

    def _to_attr_name(self, field_name: str) -> str:
        """Convert display field name to snake_case attribute name.

        Args:
            field_name: Display name (e.g., "Office Phone").

        Returns:
            Snake case attribute name (e.g., "office_phone").
        """
        return field_name.lower().replace(" ", "_")

    def _normalize_value(self, value: Any) -> Any:
        """Normalize value for storage, handling enums, multi-enums, and people.

        Handles various value formats from Asana custom fields:
        - enum_value: dict with gid/name -> extract name string
        - multi_enum_values: list of dicts -> extract list of name strings
        - people_value: list of dicts -> extract list of name strings
        - text_value: string -> return as-is
        - number_value: number -> return as-is
        - Python enum: object with .value -> extract value

        Args:
            value: Raw value from custom field or descriptor.

        Returns:
            Normalized value suitable for seeding:
            - Single enum: string name
            - Multi-enum: list of string names
            - People: list of string names
            - Other: value as-is
        """
        if value is None:
            return None

        # Handle Python enum objects (have .value attribute)
        if hasattr(value, "value") and not isinstance(value, (dict, list)):
            return value.value

        # Handle single enum dict: {"gid": "123", "name": "Value"} -> "Value"
        if isinstance(value, dict):
            if "name" in value:
                return value["name"]
            if "gid" in value:
                # If only GID, return as-is (will be resolved later)
                return value.get("gid")
            return value

        # Handle list values (multi-enum, people, etc.)
        if isinstance(value, list):
            if not value:
                return []

            # Check first item to determine list type
            first = value[0]

            # Multi-enum or people: list of dicts with name/gid
            if isinstance(first, dict):
                # Extract names if available, else GIDs
                result = []
                for item in value:
                    if isinstance(item, dict):
                        if "name" in item:
                            result.append(item["name"])
                        elif "gid" in item:
                            result.append(item["gid"])
                    elif isinstance(item, str):
                        result.append(item)
                return result if result else []

            # List of strings (already normalized) - return as-is
            return value

        return value

    @staticmethod
    def _build_enum_lookup(enum_options: list[Any]) -> dict[str, str]:
        """Build case-insensitive name-to-GID lookup from enum options.

        Maps both lowered option names and raw GID strings to the option GID,
        enabling both name-based and GID passthrough resolution.

        Args:
            enum_options: List of enum option dicts/objects with 'name' and 'gid'.

        Returns:
            Dict mapping lowered names and GID strings to GID values.
        """
        name_to_gid: dict[str, str] = {}
        for option in enum_options:
            opt_name = get_field_attr(option, "name", "")
            opt_gid = get_field_attr(option, "gid", "")
            if opt_name and opt_gid:
                name_to_gid[opt_name.lower()] = opt_gid
                # Also map GID to itself for passthrough
                name_to_gid[opt_gid] = opt_gid
        return name_to_gid

    @staticmethod
    def _resolve_single_option(
        value: Any,
        name_to_gid: dict[str, str],
        enum_options: list[Any],
        field_name: str,
        task_gid: str,
        *,
        multi: bool = False,
    ) -> str | None:
        """Resolve a single string value to a GID using the lookup dict.

        Handles GID passthrough (numeric strings validated against known GIDs)
        and case-insensitive name matching. Logs warnings when values cannot
        be resolved, including available options.

        Args:
            value: String value to resolve (name or GID).
            name_to_gid: Lookup dict from _build_enum_lookup.
            enum_options: Original enum options list (for available-options warning).
            field_name: Field name for logging.
            task_gid: Task GID for logging.
            multi: If True, use multi-enum log event names.

        Returns:
            Resolved GID string, or None if resolution fails.
        """
        value_str = str(value).lower().strip()

        # Check if it's already a GID (numeric string)
        if value_str.isdigit():
            if value_str in name_to_gid:
                return value_str
            gid_event = (
                "seeding_multi_enum_gid_not_found"
                if multi
                else "seeding_enum_gid_not_found"
            )
            logger.warning(
                gid_event,
                gid=value,
                field_name=field_name,
                **({"task_gid": task_gid} if not multi else {}),
            )
            return None

        # Name-based lookup (case-insensitive)
        if value_str in name_to_gid:
            resolved_gid = name_to_gid[value_str]
            if not multi:
                logger.debug(
                    "seeding_enum_resolved",
                    value=value,
                    resolved_gid=resolved_gid,
                    field_name=field_name,
                )
            return resolved_gid

        # No match found - log warning with available options
        available_options = [
            get_field_attr(opt, "name", "")
            for opt in enum_options
            if get_field_attr(opt, "enabled", True)
        ]
        not_found_event = (
            "seeding_multi_enum_value_not_found"
            if multi
            else "seeding_enum_value_not_found"
        )
        logger.warning(
            not_found_event,
            value=value,
            field_name=field_name,
            task_gid=task_gid,
            available_options=available_options,
        )
        return None

    def _resolve_enum_value(
        self,
        field_def: Any,
        value: Any,
        field_name: str,
        task_gid: str,
    ) -> Any:
        """Resolve enum and multi-enum string values to GIDs.

        Per G2 Fix: Enum fields require GIDs, not string names.
        Asana silently ignores invalid enum values, so resolution is critical.

        Handles:
        - Single enum: string name -> GID
        - Multi-enum: list of string names -> list of GIDs

        Args:
            field_def: Custom field definition from API (dict or object with enum_options).
            value: The value to potentially resolve (string or list of strings).
            field_name: Field name for logging.
            task_gid: Task GID for logging.

        Returns:
            Resolved value (GID for enums, list of GIDs for multi-enums).
            Returns None if resolution fails (value not found in options).
        """
        if value is None:
            return None

        field_type = get_field_attr(field_def, "resource_subtype", "")

        # Handle multi_enum fields (list of values)
        if field_type == "multi_enum":
            if not isinstance(value, list):
                value = [value]

            enum_options = get_field_attr(field_def, "enum_options", [])
            if not enum_options:
                logger.warning(
                    "seeding_multi_enum_no_options",
                    field_name=field_name,
                    task_gid=task_gid,
                )
                return None

            name_to_gid = self._build_enum_lookup(enum_options)

            resolved_gids: list[str] = []
            for item in value:
                if item is None:
                    continue
                resolved = self._resolve_single_option(
                    item,
                    name_to_gid,
                    enum_options,
                    field_name,
                    task_gid,
                    multi=True,
                )
                if resolved is not None:
                    resolved_gids.append(resolved)

            return resolved_gids if resolved_gids else None

        # Handle single enum fields
        if field_type == "enum":
            enum_options = get_field_attr(field_def, "enum_options", [])
            if not enum_options:
                logger.warning(
                    "seeding_enum_no_options",
                    field_name=field_name,
                    task_gid=task_gid,
                )
                return None

            name_to_gid = self._build_enum_lookup(enum_options)
            return self._resolve_single_option(
                value,
                name_to_gid,
                enum_options,
                field_name,
                task_gid,
                multi=False,
            )

        # Not an enum field - return value unchanged
        return value
