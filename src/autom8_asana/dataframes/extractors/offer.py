"""Offer task extractor with base + 11 Offer-specific fields.

Follows the ContactExtractor pattern: extends BaseExtractor with
Offer-specific custom field extraction and row model construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import OfferRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class OfferExtractor(BaseExtractor):
    """Extractor for Offer task type.

    Cascade fields (5):
        office, office_phone, vertical, mrr, weekly_ad_spend

    Custom fields (5):
        specialty, offer_id, platforms, language, cost

    Derived fields (1):
        vertical_id (stub -- pending Vertical model lookup)
    """

    def _create_row(self, data: dict[str, Any]) -> OfferRow:
        """Create OfferRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            OfferRow instance
        """
        data["type"] = "Offer"
        return OfferRow.model_validate(data)

    def _extract_vertical_id(self, task: Task) -> str | None:
        """Extract vertical identifier (derived field stub).

        Args:
            task: Task to extract from

        Returns:
            None (stub implementation pending Vertical model lookup)
        """
        return None

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'Offer'.

        Args:
            task: Task to extract from

        Returns:
            'Offer' (always)
        """
        return "Offer"
