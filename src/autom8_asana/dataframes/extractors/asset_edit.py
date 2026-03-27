"""AssetEdit task extractor with base + 21 AssetEdit-specific fields.

Follows the ContactExtractor pattern: extends BaseExtractor with
AssetEdit-specific custom field extraction and row model construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import AssetEditRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class AssetEditExtractor(BaseExtractor):
    """Extractor for AssetEdit task type.

    Process fields (10):
        started_at, process_completed_at, process_notes, status,
        priority, process_due_date, assigned_to, vertical,
        office_phone, specialty

    AssetEdit-specific fields (11):
        asset_approval, asset_id, editor, reviewer, offer_id,
        raw_assets, review_all_ads, score, asset_edit_specialty,
        template_id, videos_paid

    Cascade fields (vertical, office_phone) require async extraction.
    """

    def _create_row(self, data: dict[str, Any]) -> AssetEditRow:
        """Create AssetEditRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            AssetEditRow instance
        """
        data["type"] = "AssetEdit"
        return AssetEditRow.model_validate(data)

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'AssetEdit'.

        Args:
            task: Task to extract from

        Returns:
            'AssetEdit' (always)
        """
        return "AssetEdit"
