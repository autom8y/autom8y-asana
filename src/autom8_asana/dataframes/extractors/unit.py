"""Unit task extractor with 21 fields (12 base + 9 Unit-specific).

Per TDD-0009 Phase 3: UnitExtractor extends BaseExtractor with
Unit-specific custom field extraction.
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
    """Extractor for Unit task type with 21 fields.

    Per FR-SUBCLASS-001: Extracts 12 base fields plus 9 Unit-specific fields.

    Direct custom fields (6):
        mrr, weekly_ad_spend, products, languages, discount, office_phone
        These are extracted via CustomFieldResolver from cf: sources.

    Cascade/derived fields (3):
        office, vertical, specialty
        office resolves Business ancestor name via parent chain traversal.
        vertical and specialty are direct custom fields via cascade sources.

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
            UnitRow instance with all 21 fields
        """
        # Ensure type is set correctly
        data["type"] = "Unit"

        return UnitRow.model_validate(data)

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
