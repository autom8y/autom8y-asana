"""Unit tests for automation base types.

Per TDD-AUTOMATION-LAYER: Test TriggerCondition.matches() and Action dataclass.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import pytest

from autom8_asana.automation.base import Action, TriggerCondition
from autom8_asana.automation.events.types import EventType


class MockProcessType(Enum):
    """Mock enum for testing."""

    SALES = "sales"
    ONBOARDING = "onboarding"


class MockEntity:
    """Mock entity for testing TriggerCondition."""

    def __init__(
        self,
        entity_type: str = "Process",
        process_type: MockProcessType | str | None = None,
        status: str | None = None,
    ) -> None:
        self.gid = "123456"
        self._entity_type = entity_type
        self.process_type = process_type
        self.status = status

    @property
    def __class_name__(self) -> str:
        return self._entity_type


class Process(MockEntity):
    """Mock Process class to get correct __name__."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(entity_type="Process", **kwargs)


class Offer(MockEntity):
    """Mock Offer class to get correct __name__."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(entity_type="Offer", **kwargs)


class TestTriggerCondition:
    """Tests for TriggerCondition.matches()."""

    def test_matches_entity_type(self) -> None:
        """Test matching entity type."""
        condition = TriggerCondition(entity_type="Process", event=EventType.CREATED)
        entity = Process()

        result = condition.matches(entity, EventType.CREATED, {})

        assert result is True

    def test_no_match_wrong_entity_type(self) -> None:
        """Test no match when entity type is wrong."""
        condition = TriggerCondition(entity_type="Process", event=EventType.CREATED)
        entity = Offer()

        result = condition.matches(entity, EventType.CREATED, {})

        assert result is False

    def test_matches_event(self) -> None:
        """Test matching event type."""
        condition = TriggerCondition(entity_type="Process", event=EventType.UPDATED)
        entity = Process()

        result = condition.matches(entity, EventType.UPDATED, {})

        assert result is True

    def test_no_match_wrong_event(self) -> None:
        """Test no match when event is wrong."""
        condition = TriggerCondition(entity_type="Process", event=EventType.UPDATED)
        entity = Process()

        result = condition.matches(entity, EventType.CREATED, {})

        assert result is False

    def test_matches_filter_in_context(self) -> None:
        """Test matching filter from context dict."""
        condition = TriggerCondition(
            entity_type="Process",
            event=EventType.SECTION_CHANGED,
            filters={"section": "converted"},
        )
        entity = Process()
        context = {"section": "converted"}

        result = condition.matches(entity, EventType.SECTION_CHANGED, context)

        assert result is True

    def test_no_match_filter_wrong_value(self) -> None:
        """Test no match when filter value is wrong."""
        condition = TriggerCondition(
            entity_type="Process",
            event=EventType.SECTION_CHANGED,
            filters={"section": "converted"},
        )
        entity = Process()
        context = {"section": "pending"}

        result = condition.matches(entity, EventType.SECTION_CHANGED, context)

        assert result is False

    def test_matches_filter_from_entity_attribute(self) -> None:
        """Test matching filter from entity attribute."""
        condition = TriggerCondition(
            entity_type="Process",
            event=EventType.CREATED,
            filters={"status": "active"},
        )
        entity = Process(status="active")
        context: dict[str, Any] = {}

        result = condition.matches(entity, EventType.CREATED, context)

        assert result is True

    def test_matches_filter_enum_value(self) -> None:
        """Test matching filter with enum attribute."""
        condition = TriggerCondition(
            entity_type="Process",
            event=EventType.CREATED,
            filters={"process_type": "sales"},
        )
        entity = Process(process_type=MockProcessType.SALES)
        context: dict[str, Any] = {}

        result = condition.matches(entity, EventType.CREATED, context)

        assert result is True

    def test_no_match_filter_missing_attribute(self) -> None:
        """Test no match when filter attribute is missing."""
        condition = TriggerCondition(
            entity_type="Process",
            event=EventType.CREATED,
            filters={"nonexistent": "value"},
        )
        entity = Process()
        context: dict[str, Any] = {}

        result = condition.matches(entity, EventType.CREATED, context)

        assert result is False

    def test_matches_multiple_filters(self) -> None:
        """Test matching multiple filters."""
        condition = TriggerCondition(
            entity_type="Process",
            event=EventType.SECTION_CHANGED,
            filters={
                "section": "converted",
                "process_type": "sales",
            },
        )
        entity = Process(process_type=MockProcessType.SALES)
        context = {"section": "converted"}

        result = condition.matches(entity, EventType.SECTION_CHANGED, context)

        assert result is True

    def test_no_match_one_filter_fails(self) -> None:
        """Test no match when one of multiple filters fails."""
        condition = TriggerCondition(
            entity_type="Process",
            event=EventType.SECTION_CHANGED,
            filters={
                "section": "converted",
                "process_type": "onboarding",  # This will fail
            },
        )
        entity = Process(process_type=MockProcessType.SALES)
        context = {"section": "converted"}

        result = condition.matches(entity, EventType.SECTION_CHANGED, context)

        assert result is False

    def test_frozen_dataclass(self) -> None:
        """Test that TriggerCondition is frozen (immutable)."""
        condition = TriggerCondition(entity_type="Process", event=EventType.CREATED)

        with pytest.raises(AttributeError):
            condition.entity_type = "Task"  # type: ignore[misc]


class TestAction:
    """Tests for Action dataclass."""

    def test_default_values(self) -> None:
        """Test default values for Action."""
        action = Action(type="create_process")

        assert action.type == "create_process"
        assert action.params == {}

    def test_custom_params(self) -> None:
        """Test Action with custom params."""
        action = Action(
            type="add_to_project",
            params={"project_gid": "123456"},
        )

        assert action.type == "add_to_project"
        assert action.params == {"project_gid": "123456"}

    def test_params_mutable(self) -> None:
        """Test that Action params can be modified."""
        action = Action(type="set_field")
        action.params["field_name"] = "Status"
        action.params["value"] = "Active"

        assert action.params == {"field_name": "Status", "value": "Active"}
