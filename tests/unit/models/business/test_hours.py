"""Tests for Hours model.

Per TDD-BIZMODEL Phase 3: Tests for Hours entity with operating hours.
Per PRD-0024: Field names are "Monday", etc. (not "Monday Hours").
Per PRD-0024: Fields are multi_enum returning list[str].
Per ADR-0114: Deprecated aliases emit DeprecationWarning.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.hours import Hours
from autom8_asana.models.business.location import LocationHolder


class TestHours:
    """Tests for Hours model."""

    def test_hours_inherits_from_task(self) -> None:
        """Hours inherits from Task and can be constructed."""
        hours = Hours(gid="123", name="Hours")
        assert hours.gid == "123"
        assert hours.name == "Hours"


class TestHoursNewProperties:
    """Tests for Hours new property names per PRD-0024."""

    def test_monday_getter(self) -> None:
        """monday getter returns list from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Monday",
            [
                {"gid": "t1", "name": "08:00:00"},
                {"gid": "t2", "name": "17:00:00"},
            ],
        )
        assert hours.monday == ["08:00:00", "17:00:00"]

    def test_monday_empty(self) -> None:
        """monday returns empty list when not set."""
        hours = Hours(gid="123", custom_fields=[])
        assert hours.monday == []

    def test_monday_setter(self) -> None:
        """monday setter updates value."""
        hours = Hours(gid="123", custom_fields=[])
        hours.monday = ["09:00:00", "18:00:00"]
        assert hours.custom_fields_editor().get("Monday") == ["09:00:00", "18:00:00"]
        assert hours.custom_fields_editor().has_changes()

    def test_tuesday_getter(self) -> None:
        """tuesday getter returns list from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Tuesday",
            [
                {"gid": "t1", "name": "09:00:00"},
            ],
        )
        assert hours.tuesday == ["09:00:00"]

    def test_wednesday_getter(self) -> None:
        """wednesday getter returns list from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Wednesday",
            [
                {"gid": "t1", "name": "10:00:00"},
            ],
        )
        assert hours.wednesday == ["10:00:00"]

    def test_thursday_getter(self) -> None:
        """thursday getter returns list from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Thursday",
            [
                {"gid": "t1", "name": "08:30:00"},
            ],
        )
        assert hours.thursday == ["08:30:00"]

    def test_friday_getter(self) -> None:
        """friday getter returns list from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Friday",
            [
                {"gid": "t1", "name": "08:00:00"},
                {"gid": "t2", "name": "16:00:00"},
            ],
        )
        assert hours.friday == ["08:00:00", "16:00:00"]

    def test_saturday_getter(self) -> None:
        """saturday getter returns list from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Saturday",
            [
                {"gid": "t1", "name": "10:00:00"},
                {"gid": "t2", "name": "14:00:00"},
            ],
        )
        assert hours.saturday == ["10:00:00", "14:00:00"]


class TestHoursHelperProperties:
    """Tests for Hours helper properties per TDD."""

    def test_monday_open(self) -> None:
        """monday_open returns first value from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Monday",
            [
                {"gid": "t1", "name": "08:00:00"},
                {"gid": "t2", "name": "17:00:00"},
            ],
        )
        assert hours.monday_open == "08:00:00"

    def test_monday_open_empty(self) -> None:
        """monday_open returns None when not set."""
        hours = Hours(gid="123", custom_fields=[])
        assert hours.monday_open is None

    def test_monday_close(self) -> None:
        """monday_close returns last value from multi-enum."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Monday",
            [
                {"gid": "t1", "name": "08:00:00"},
                {"gid": "t2", "name": "17:00:00"},
            ],
        )
        assert hours.monday_close == "17:00:00"

    def test_monday_close_single_value(self) -> None:
        """monday_close returns None when only one value."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Monday",
            [
                {"gid": "t1", "name": "08:00:00"},
            ],
        )
        assert hours.monday_close is None


class TestHoursComputedProperties:
    """Tests for Hours computed properties."""

    def test_weekday_hours(self) -> None:
        """weekday_hours returns Monday-Friday hours."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set("Monday", [{"gid": "1", "name": "9-5"}])
        hours.custom_fields_editor().set("Tuesday", [{"gid": "2", "name": "9-5"}])
        hours.custom_fields_editor().set("Wednesday", [{"gid": "3", "name": "9-5"}])
        hours.custom_fields_editor().set("Thursday", [{"gid": "4", "name": "9-5"}])
        hours.custom_fields_editor().set("Friday", [{"gid": "5", "name": "9-5"}])

        weekday = hours.weekday_hours
        assert weekday["monday"] == ["9-5"]
        assert weekday["tuesday"] == ["9-5"]
        assert weekday["wednesday"] == ["9-5"]
        assert weekday["thursday"] == ["9-5"]
        assert weekday["friday"] == ["9-5"]

    def test_all_hours_excludes_sunday(self) -> None:
        """all_hours includes 6 days (no Sunday per PRD-0024)."""
        hours = Hours(gid="123", custom_fields=[])
        all_hrs = hours.all_hours
        assert "monday" in all_hrs
        assert "saturday" in all_hrs
        assert "sunday" not in all_hrs  # Removed per PRD-0024
        assert len(all_hrs) == 6


class TestHoursIsOpenOn:
    """Tests for Hours.is_open_on method."""

    def test_is_open_on_returns_true_when_hours_set(self) -> None:
        """is_open_on returns True when hours are set (non-empty list)."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Monday",
            [
                {"gid": "t1", "name": "08:00:00"},
            ],
        )
        assert hours.is_open_on("monday") is True

    def test_is_open_on_returns_false_when_empty(self) -> None:
        """is_open_on returns False when hours are empty list."""
        hours = Hours(gid="123", custom_fields=[])
        assert hours.is_open_on("monday") is False

    def test_is_open_on_case_insensitive(self) -> None:
        """is_open_on is case-insensitive for day names."""
        hours = Hours(gid="123", custom_fields=[])
        hours.custom_fields_editor().set(
            "Monday",
            [
                {"gid": "t1", "name": "08:00:00"},
            ],
        )
        assert hours.is_open_on("MONDAY") is True
        assert hours.is_open_on("Monday") is True

    def test_is_open_on_unknown_day(self) -> None:
        """is_open_on returns False for unknown day."""
        hours = Hours(gid="123", custom_fields=[])
        assert hours.is_open_on("sunday") is False  # Sunday not in Asana


class TestHoursNavigation:
    """Tests for Hours navigation properties."""

    def test_location_holder_property(self) -> None:
        """location_holder returns cached reference."""
        hours = Hours(gid="123")
        holder = LocationHolder(gid="456")
        hours._location_holder = holder
        assert hours.location_holder is holder

    def test_invalidate_refs(self) -> None:
        """_invalidate_refs clears cached references."""
        hours = Hours(gid="123")
        holder = LocationHolder(gid="456")
        hours._location_holder = holder
        hours._invalidate_refs()
        assert hours._location_holder is None
        assert hours._business is None


class TestHoursFieldsClass:
    """Tests for Hours.Fields class constants per PRD-0024."""

    def test_field_names_match_asana(self) -> None:
        """Fields class has correct names per PRD-0024."""
        assert Hours.Fields.MONDAY == "Monday"
        assert Hours.Fields.TUESDAY == "Tuesday"
        assert Hours.Fields.WEDNESDAY == "Wednesday"
        assert Hours.Fields.THURSDAY == "Thursday"
        assert Hours.Fields.FRIDAY == "Friday"
        assert Hours.Fields.SATURDAY == "Saturday"

    def test_stale_fields_removed(self) -> None:
        """Stale fields are removed per PRD-0024."""
        assert not hasattr(Hours.Fields, "SUNDAY_HOURS")
        assert not hasattr(Hours.Fields, "TIMEZONE")
        assert not hasattr(Hours.Fields, "NOTES")
