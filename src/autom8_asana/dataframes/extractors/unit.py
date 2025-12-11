"""Unit task extractor with 23 fields (12 base + 11 Unit-specific).

Per TDD-0009 Phase 3: UnitExtractor extends BaseExtractor with
Unit-specific custom field extraction and derived field stubs.
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

    Direct custom fields (5):
        mrr, weekly_ad_spend, products, languages, discount
        These are extracted via CustomFieldResolver from cf: sources.

    Derived fields (6):
        office, office_phone, vertical_id, max_pipeline_stage
        These return None with TODO comments pending autom8 team input.
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

        # Convert None lists to empty lists for list fields
        if data.get("tags") is None:
            data["tags"] = []
        if data.get("products") is None:
            data["products"] = []
        if data.get("languages") is None:
            data["languages"] = []

        return UnitRow.model_validate(data)

    # =========================================================================
    # Derived field extraction methods (stubs)
    # Per MVP Note: Return None with TODO comments pending business logic input
    # =========================================================================

    def _extract_office(self, task: Task) -> str | None:
        """Extract office location (derived field stub).

        Per PRD-0003 Appendix A: Derived from business.office_phone lookup.
        Per MVP Note: Full implementation deferred pending autom8 team input.

        Args:
            task: Task to extract from

        Returns:
            None (stub implementation)

        TODO:
            Implement office derivation from business.office_phone lookup.
            Requires access to business model and office mapping logic.
        """
        # TODO: Implement office derivation from business.office_phone lookup
        # This requires:
        # 1. Access to the Unit's associated business
        # 2. Lookup of office_phone to office mapping
        # Deferred pending autom8 team input on business logic
        return None

    def _extract_office_phone(self, task: Task) -> str | None:
        """Extract office phone number (derived field stub).

        Per PRD-0003 Appendix A: Derived from business model.
        Per MVP Note: Full implementation deferred pending autom8 team input.

        Args:
            task: Task to extract from

        Returns:
            None (stub implementation)

        TODO:
            Implement office_phone derivation from business model.
            Requires access to business model relationships.
        """
        # TODO: Implement office_phone derivation from business model
        # This requires:
        # 1. Access to the Unit's associated business
        # 2. Extraction of office_phone from business
        # Deferred pending autom8 team input on business logic
        return None

    def _extract_vertical_id(self, task: Task) -> str | None:
        """Extract vertical identifier (derived field stub).

        Per PRD-0003 Appendix A: Derived from Vertical model.
        Per MVP Note: Full implementation deferred pending autom8 team input.

        Args:
            task: Task to extract from

        Returns:
            None (stub implementation)

        TODO:
            Implement vertical_id derivation from Vertical model.
            Requires mapping from vertical name to vertical ID.
        """
        # TODO: Implement vertical_id derivation from Vertical model
        # This requires:
        # 1. Access to the vertical custom field value
        # 2. Lookup of vertical name to Vertical model ID
        # Deferred pending autom8 team input on Vertical model mapping
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
