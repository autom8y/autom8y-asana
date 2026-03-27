"""Business task extractor with base + 5 Business-specific fields.

Follows the ContactExtractor pattern: extends BaseExtractor with
Business-specific custom field extraction and row model construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import BusinessRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class BusinessExtractor(BaseExtractor):
    """Extractor for Business task type.

    Business fields (5):
        company_id, office_phone, stripe_id, booking_type, facebook_page_id

    All Business-specific fields are extracted via CustomFieldResolver
    from cf: sources. No derived fields are required for Business.
    """

    def _create_row(self, data: dict[str, Any]) -> BusinessRow:
        """Create BusinessRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            BusinessRow instance
        """
        data["type"] = "Business"
        return BusinessRow.model_validate(data)

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'Business'.

        Args:
            task: Task to extract from

        Returns:
            'Business' (always)
        """
        return "Business"
