"""Unit task extractor with 23 fields (12 base + 11 Unit-specific).

Per TDD-0009 Phase 3: UnitExtractor extends BaseExtractor with
Unit-specific custom field extraction and derived field stubs.
Per TDD-WS3: Office extraction eliminated; office column now resolves via
cascade:Business Name source in UNIT_SCHEMA (using CascadingFieldDef.source_field).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import UnitRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class UnitExtractor(BaseExtractor):
    """Extractor for Unit task type with 23 fields.

    Per FR-SUBCLASS-001: Extracts 12 base fields plus 11 Unit-specific fields.

    Direct custom fields (6):
        mrr, weekly_ad_spend, products, languages, discount, office_phone
        These are extracted via CustomFieldResolver from cf: sources.

    Derived fields (5):
        office, vertical_id, max_pipeline_stage
        office resolves Business ancestor name via parent chain traversal.
        vertical_id and max_pipeline_stage return None pending model lookups.
        Note: vertical and specialty are direct custom fields, not derived.

    Example:
        >>> from autom8_asana.dataframes.schemas import UNIT_SCHEMA
        >>> from autom8_asana.dataframes.resolver import MockCustomFieldResolver
        >>> from decimal import Decimal
        >>>
        >>> resolver = MockCustomFieldResolver({
        ...     "mrr": Decimal("5000"),
        ...     "products": ["Product A", "Product B"],
        ... })
        >>> extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        >>> row = extractor.extract(task)
        >>> row.type
        'Unit'
    """

    def _create_row(self, data: dict[str, Any]) -> UnitRow:
        """Create UnitRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            UnitRow instance with all 23 fields
        """
        # Ensure type is set correctly
        data["type"] = "Unit"

        return UnitRow.model_validate(data)

    # =========================================================================
    # Derived field extraction methods (stubs)
    # Per MVP Note: Return None with TODO comments pending business logic input
    # Per TDD-WS3: _extract_office and _extract_office_async removed.
    # Office now resolves via cascade:Business Name source in UNIT_SCHEMA.
    # =========================================================================

    def _extract_vertical_id(self, task: Task) -> str | None:
        """Extract vertical identifier (derived field stub).

        Per schema: Derived from Vertical model. The `vertical` column
        already captures the raw custom field value (e.g., "dental").
        This column is intended for the database-side vertical ID,
        which requires a Vertical model lookup (key -> ID).

        Not to be confused with `vertical` (the custom field key/name).

        Args:
            task: Task to extract from

        Returns:
            None (stub implementation)

        TODO:
            Implement vertical_id derivation from Vertical model.
            Requires a lookup from vertical key (e.g., "dental") to
            the Vertical model's database identifier.
        """
        # TODO: Implement vertical_id derivation from Vertical model
        # The `vertical` column captures the custom field key.
        # This column should hold the Vertical model's database ID.
        return None

    def _extract_max_pipeline_stage(self, task: Task) -> str | None:
        """Extract maximum pipeline stage reached (derived field stub).

        Per PRD-0003 Appendix A: Derived from UnitHolder model.
        Per MVP Note: Full implementation deferred pending autom8 team input.

        Args:
            task: Task to extract from

        Returns:
            None (stub implementation)

        TODO:
            Implement max_pipeline_stage derivation from UnitHolder.
            Requires access to UnitHolder model and pipeline stage tracking.
        """
        # TODO: Implement max_pipeline_stage derivation from UnitHolder
        # This requires:
        # 1. Access to the Unit's associated UnitHolder(s)
        # 2. Determination of maximum pipeline stage across holders
        # Deferred pending autom8 team input on UnitHolder model
        return None

    # =========================================================================
    # Type override
    # =========================================================================

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'Unit'.

        Args:
            task: Task to extract from

        Returns:
            'Unit' (always)
        """
        return "Unit"
