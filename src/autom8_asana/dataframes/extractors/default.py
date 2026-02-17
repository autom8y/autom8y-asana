"""Default extractor for base/generic task types.

Per TDD-0009: DefaultExtractor provides extraction for the 12 base fields
without any type-specific custom field extraction. Used when task_type="*".
"""

from __future__ import annotations

from typing import Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import TaskRow


class DefaultExtractor(BaseExtractor):
    """Extractor for generic task types with 12 base fields.

    Used when task_type="*" (wildcard/base schema). Extracts only the
    12 base fields defined in BASE_SCHEMA without any type-specific
    custom field extraction.

    Example:
        >>> from autom8_asana.dataframes.schemas import BASE_SCHEMA
        >>> extractor = DefaultExtractor(BASE_SCHEMA)
        >>> row = extractor.extract(task)
        >>> row.gid
        '1234567890'
    """

    def _create_row(self, data: dict[str, Any]) -> TaskRow:
        """Create TaskRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            TaskRow instance with all 12 base fields
        """
        return TaskRow.model_validate(data)
