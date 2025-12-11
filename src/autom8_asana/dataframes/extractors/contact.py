"""Contact task extractor with 21 fields (12 base + 9 Contact-specific).

Per TDD-0009 Phase 3: ContactExtractor extends BaseExtractor with
Contact-specific custom field extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import ContactRow

if TYPE_CHECKING:
    from autom8_asana.models.task import Task


class ContactExtractor(BaseExtractor):
    """Extractor for Contact task type with 21 fields.

    Per FR-SUBCLASS-002: Extracts 12 base fields plus 9 Contact-specific fields.

    Contact fields (9):
        full_name, nickname, contact_phone, contact_email, position,
        employee_id, contact_url, time_zone, city

    All Contact-specific fields are extracted via CustomFieldResolver
    from cf: sources. No derived fields are required for Contact.

    Example:
        >>> from autom8_asana.dataframes.schemas import CONTACT_SCHEMA
        >>> from autom8_asana.dataframes.resolver import MockCustomFieldResolver
        >>>
        >>> resolver = MockCustomFieldResolver({
        ...     "full_name": "John Doe",
        ...     "contact_email": "john.doe@example.com",
        ... })
        >>> extractor = ContactExtractor(CONTACT_SCHEMA, resolver)
        >>> row = extractor.extract(task)
        >>> row.type
        'Contact'
    """

    def _create_row(self, data: dict[str, Any]) -> ContactRow:
        """Create ContactRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            ContactRow instance with all 21 fields
        """
        # Ensure type is set correctly
        data["type"] = "Contact"

        # Convert None lists to empty lists for list fields
        if data.get("tags") is None:
            data["tags"] = []

        return ContactRow.model_validate(data)

    # =========================================================================
    # Type override
    # =========================================================================

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'Contact'.

        Args:
            task: Task to extract from

        Returns:
            'Contact' (always)
        """
        return "Contact"
