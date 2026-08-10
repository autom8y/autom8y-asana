"""UnitHolder task extractor with base + 10 scheduling-posture fields.

Follows the AssetEditHolderExtractor pattern: extends BaseExtractor with
UnitHolder-specific row construction and type pinning.

WS-B (DIAG-ws-b-offer-frame-collapse-2026-08-05): every posture field is read
``cf:`` off the UnitHolder's OWN manifest, so extraction needs no ancestor
traversal and is immune to the depth-1 ancestor-walk defect (CARD WS-B/1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import UnitHolderRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class UnitHolderExtractor(BaseExtractor):
    """Extractor for UnitHolder task type.

    Custom-field (cf:) columns (10):
        custom_cal_status, reviewwave_id, acuity_cal_url, calendly_url,
        janeapp_url, ehr_cal_url, trackstat_id, sked_id, google_cal_id,
        custom_ghl_id

    Cascade columns: NONE. This entity is a cascade PROVIDER, not a consumer.
    """

    def _create_row(self, data: dict[str, Any]) -> UnitHolderRow:
        """Create UnitHolderRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            UnitHolderRow instance
        """
        data["type"] = "UnitHolder"
        return UnitHolderRow.model_validate(data)

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'UnitHolder'.

        Args:
            task: Task to extract from

        Returns:
            'UnitHolder' (always)
        """
        return "UnitHolder"
