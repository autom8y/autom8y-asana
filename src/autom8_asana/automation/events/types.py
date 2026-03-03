"""Event type vocabulary for automation events.

Per GAP-03 FR-001: Closed EventType enum replacing hardcoded strings.
Per ADR-GAP03-001: str inheritance for backward compatibility.
"""

from enum import StrEnum


class EventType(StrEnum):
    """Closed vocabulary of event types.

    Inherits from str for backward compatibility with existing
    string comparisons in TriggerCondition.matches() and rule filters.

    Per ADR-GAP03-001: Mechanical migration replaces all string literals.
    """

    CREATED = "created"
    UPDATED = "updated"
    SECTION_CHANGED = "section_changed"
    DELETED = "deleted"
