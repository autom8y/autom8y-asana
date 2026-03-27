"""AssetEditHolder task extractor with base + 1 holder-specific field.

Follows the ContactExtractor pattern: extends BaseExtractor with
AssetEditHolder-specific extraction and row model construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import AssetEditHolderRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class AssetEditHolderExtractor(BaseExtractor):
    """Extractor for AssetEditHolder task type.

    Cascade fields (1):
        office_phone (cascades from Business)

    This is a simple holder extractor with minimal fields.
    """

    def _create_row(self, data: dict[str, Any]) -> AssetEditHolderRow:
        """Create AssetEditHolderRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            AssetEditHolderRow instance
        """
        data["type"] = "AssetEditHolder"
        return AssetEditHolderRow.model_validate(data)

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'AssetEditHolder'.

        Args:
            task: Task to extract from

        Returns:
            'AssetEditHolder' (always)
        """
        return "AssetEditHolder"
