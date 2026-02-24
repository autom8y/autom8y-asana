"""Auto-cascade field seeding with zero-config matching.

Per TDD-lifecycle-engine-hardening Section 2.4:
- Fields with matching names on both source and target cascade automatically
- YAML config only needed for exclusions and computed fields
- Reuses FieldSeeder infrastructure for enum resolution and API write

FR Coverage: FR-SEED-001, FR-SEED-002, FR-SEED-003

Design:
  1. Fetch target task's custom field definitions (names + types)
  2. Build target field name set (lowered for case-insensitive matching)
  3. For each cascade layer (Business -> Unit -> Process -> Computed):
     a. Inspect entity's custom fields
     b. For each field name that exists on BOTH source and target:
        - If not in exclude_fields: cascade the value
     c. Later layers override earlier (dict.update semantics)
  4. Write all matched fields via FieldSeeder (enum resolution + single API call)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.field_utils import get_field_attr, normalize_custom_fields

if TYPE_CHECKING:
    from autom8_asana.automation.seeding import FieldSeeder
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.process import Process
    from autom8_asana.models.business.unit import Unit

logger = get_logger(__name__)


@dataclass
class SeedingResult:
    """Result of auto-cascade field seeding.

    Attributes:
        fields_seeded: Names of fields that were successfully cascaded.
        fields_skipped: Names of fields not found on target or excluded.
        warnings: Non-fatal issues encountered during seeding.
    """

    fields_seeded: list[str] = field(default_factory=list)
    fields_skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AutoCascadeSeeder:
    """Auto-cascade field seeding with zero-config matching.

    Replaces FieldSeeder's static field lists with runtime field-name
    matching. Fields with the same name on source entities and the target
    task cascade automatically. YAML config is only needed for exclusions
    and computed fields.

    Cascade precedence (later overrides earlier):
      1. Business custom fields -> target
      2. Unit custom fields -> target
      3. Source Process custom fields -> target
      4. Computed fields (e.g., Launch Date = today)

    Uses FieldSeeder infrastructure for enum resolution and API write.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def seed_async(
        self,
        target_task_gid: str,
        business: Business | None,
        unit: Unit | None,
        source_process: Process,
        exclude_fields: list[str] | None = None,
        computed_fields: dict[str, str] | None = None,
        target_task: Any | None = None,
    ) -> SeedingResult:
        """Seed fields from hierarchy to target using auto-cascade.

        Args:
            target_task_gid: GID of the newly created task.
            business: Business entity (layer 1).
            unit: Unit entity (layer 2).
            source_process: Source process (layer 3).
            exclude_fields: Field names to skip (from YAML SeedingConfig).
            computed_fields: Computed values (layer 4, highest priority).
            target_task: Pre-fetched task with custom_fields. When provided,
                skips the task fetch and reuses for write_fields_async
                (saves 2 API calls total). Must include custom_fields with
                name, resource_subtype, and enum_options.

        Returns:
            SeedingResult with lists of seeded and skipped fields.
        """
        result = SeedingResult()
        excludes = {f.lower() for f in (exclude_fields or [])}

        # Fetch target custom field definitions (skip if pre-fetched)
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

        target_fields = normalize_custom_fields(target_task.custom_fields)
        target_field_names: dict[str, dict[str, Any]] = {
            get_field_attr(f, "name", "").lower(): f
            for f in target_fields
            if get_field_attr(f, "name", "")
        }

        if not target_field_names:
            logger.info(
                "auto_cascade_no_target_fields",
                task_gid=target_task_gid,
            )
            return result

        # Build cascaded values from each layer
        seeded: dict[str, Any] = {}

        # Layer 1: Business cascade
        if business is not None:
            business_values = self._extract_matching_fields(
                business,
                target_field_names,
                excludes,
            )
            seeded.update(business_values)

        # Layer 2: Unit cascade (overrides Business)
        if unit is not None:
            unit_values = self._extract_matching_fields(
                unit,
                target_field_names,
                excludes,
            )
            seeded.update(unit_values)

        # Layer 3: Source process carry-through (overrides Unit)
        process_values = self._extract_matching_fields(
            source_process,
            target_field_names,
            excludes,
        )
        seeded.update(process_values)

        # Layer 4: Computed fields (overrides everything)
        for field_name, computation in (computed_fields or {}).items():
            if field_name.lower() in excludes:
                continue
            value = self._compute_field(computation)
            if value is not None:
                seeded[field_name] = value

        if not seeded:
            logger.info(
                "auto_cascade_no_matching_fields",
                task_gid=target_task_gid,
            )
            return result

        logger.info(
            "auto_cascade_fields_matched",
            task_gid=target_task_gid,
            field_count=len(seeded),
            fields=list(seeded.keys()),
        )

        # Write using FieldSeeder infrastructure (enum resolution + API call)
        # Pass target_task to avoid re-fetching (IMP-02: eliminates double-fetch)
        from autom8_asana.automation.seeding import FieldSeeder

        field_seeder = FieldSeeder(self._client)
        write_result = await field_seeder.write_fields_async(
            target_task_gid,
            seeded,
            target_task=target_task,
        )

        result.fields_seeded = write_result.fields_written
        result.fields_skipped = write_result.fields_skipped
        if write_result.error:
            result.warnings.append(f"Field write error: {write_result.error}")

        return result

    def _extract_matching_fields(
        self,
        entity: Any,
        target_field_names: dict[str, dict[str, Any]],
        excludes: set[str],
    ) -> dict[str, Any]:
        """Extract field values from entity that match target fields.

        Matching is case-insensitive on custom field name.
        """
        matched: dict[str, Any] = {}

        # Get entity's custom fields
        entity_cfs = getattr(entity, "custom_fields", None) or []
        entity_fields = normalize_custom_fields(entity_cfs)

        for field_dict in entity_fields:
            field_name = get_field_attr(field_dict, "name", "")
            if not field_name:
                continue

            field_name_lower = field_name.lower()

            # Check exclusion
            if field_name_lower in excludes:
                continue

            # Check if field exists on target
            if field_name_lower not in target_field_names:
                continue

            # Extract value based on field type
            value = self._extract_field_value(field_dict)
            if value is not None:
                matched[field_name] = value

        return matched

    @staticmethod
    def _extract_field_value(field_dict: dict[str, Any]) -> Any:
        """Extract the display value from a custom field dict.

        Returns string names for enums (resolved to target GIDs at write time),
        ISO date strings for dates, and raw values for text/number fields.
        """
        subtype = get_field_attr(field_dict, "resource_subtype", "")

        if subtype == "enum":
            enum_value = get_field_attr(field_dict, "enum_value", None)
            if enum_value:
                return get_field_attr(enum_value, "name", None)
            return None

        if subtype == "multi_enum":
            multi_values = get_field_attr(
                field_dict,
                "multi_enum_values",
                [],
            )
            if multi_values:
                return [
                    get_field_attr(v, "name", "")
                    for v in multi_values
                    if get_field_attr(v, "name", "")
                ]
            return None

        if subtype == "people":
            people = get_field_attr(field_dict, "people_value", [])
            if people:
                return [
                    {"gid": get_field_attr(p, "gid", "")}
                    for p in people
                    if get_field_attr(p, "gid", "")
                ]
            return None

        if subtype == "date":
            date_val = get_field_attr(field_dict, "date_value", None)
            if date_val:
                return get_field_attr(date_val, "date", None)
            return None

        if subtype == "text":
            return get_field_attr(field_dict, "text_value", None)

        if subtype == "number":
            return get_field_attr(field_dict, "number_value", None)

        # Fallback: display_value
        return get_field_attr(field_dict, "display_value", None)

    @staticmethod
    def _compute_field(computation: str) -> Any:
        """Resolve a computed field specification to a value.

        Supported computations:
          - "today": Current date in ISO format (YYYY-MM-DD)
          - Any other string: Returned as-is (literal value)
        """
        if computation == "today":
            return date.today().isoformat()
        # Extensible: treat as literal value
        return computation
