"""Process task extractor with base + 3 Process-specific fields.

Follows the OfferExtractor pattern: extends BaseExtractor with
Process-specific custom field extraction and row model construction.

Per ADR-pipeline-stage-aggregation: pipeline_type is NOT extracted
here -- it is a derived column set by the Phase 2 aggregator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import ProcessRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class ProcessExtractor(BaseExtractor):
    """Extractor for Process task type.

    Cascade fields (2):
        office_phone, vertical

    Derived fields (1):
        pipeline_type (set by aggregator, not by extractor)
    """

    def _create_row(self, data: dict[str, Any]) -> ProcessRow:
        """Create ProcessRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            ProcessRow instance
        """
        data["type"] = "Process"
        return ProcessRow.model_validate(data)

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'Process'.

        Args:
            task: Task to extract from

        Returns:
            'Process' (always)
        """
        return "Process"
