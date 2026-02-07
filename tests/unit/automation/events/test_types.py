"""Tests for EventType enum.

Per GAP-03 SC-003: EventType enum replaces hardcoded strings.
Per ADR-GAP03-001: str inheritance maintains backward compatibility.
"""

import pytest

from autom8_asana.automation.events.types import EventType


class TestEventTypeEnum:
    """Test EventType enum members and values."""

    def test_members_exist(self) -> None:
        assert EventType.CREATED is not None
        assert EventType.UPDATED is not None
        assert EventType.SECTION_CHANGED is not None
        assert EventType.DELETED is not None

    def test_values(self) -> None:
        assert EventType.CREATED.value == "created"
        assert EventType.UPDATED.value == "updated"
        assert EventType.SECTION_CHANGED.value == "section_changed"
        assert EventType.DELETED.value == "deleted"

    def test_member_count(self) -> None:
        assert len(EventType) == 4


class TestEventTypeStrCompatibility:
    """Test str inheritance backward compatibility."""

    def test_str_equality(self) -> None:
        assert EventType.CREATED == "created"
        assert EventType.UPDATED == "updated"
        assert EventType.SECTION_CHANGED == "section_changed"
        assert EventType.DELETED == "deleted"

    def test_is_instance_of_str(self) -> None:
        assert isinstance(EventType.CREATED, str)

    def test_construct_from_string(self) -> None:
        assert EventType("created") is EventType.CREATED
        assert EventType("section_changed") is EventType.SECTION_CHANGED

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError):
            EventType("nonexistent")

    def test_in_string_comparison(self) -> None:
        events = ["created", "updated"]
        assert EventType.CREATED in events

    def test_dict_key_compatibility(self) -> None:
        d = {"created": True}
        assert d[EventType.CREATED] is True

    def test_json_serializable_via_value(self) -> None:
        import json

        data = {"event_type": EventType.SECTION_CHANGED.value}
        result = json.dumps(data)
        assert '"section_changed"' in result
