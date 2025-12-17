"""Tests for Hours model.

Per TDD-BIZMODEL Phase 3: Tests for Hours entity with operating hours.
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


class TestHoursDayProperties:
    """Tests for Hours day-specific properties."""

    def test_monday_hours_getter(self) -> None:
        """monday_hours getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Monday Hours", "text_value": "9:00 AM - 5:00 PM"}
            ],
        )
        assert hours.monday_hours == "9:00 AM - 5:00 PM"

    def test_monday_hours_setter(self) -> None:
        """monday_hours setter updates value."""
        hours = Hours(gid="123", custom_fields=[])
        hours.monday_hours = "8:00 AM - 6:00 PM"
        assert hours.get_custom_fields().get("Monday Hours") == "8:00 AM - 6:00 PM"
        assert hours.get_custom_fields().has_changes()

    def test_tuesday_hours_getter(self) -> None:
        """tuesday_hours getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Tuesday Hours", "text_value": "9:00 AM - 5:00 PM"}
            ],
        )
        assert hours.tuesday_hours == "9:00 AM - 5:00 PM"

    def test_wednesday_hours_getter(self) -> None:
        """wednesday_hours getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Wednesday Hours", "text_value": "9:00 AM - 5:00 PM"}
            ],
        )
        assert hours.wednesday_hours == "9:00 AM - 5:00 PM"

    def test_thursday_hours_getter(self) -> None:
        """thursday_hours getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Thursday Hours", "text_value": "9:00 AM - 5:00 PM"}
            ],
        )
        assert hours.thursday_hours == "9:00 AM - 5:00 PM"

    def test_friday_hours_getter(self) -> None:
        """friday_hours getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Friday Hours", "text_value": "9:00 AM - 5:00 PM"}
            ],
        )
        assert hours.friday_hours == "9:00 AM - 5:00 PM"

    def test_saturday_hours_getter(self) -> None:
        """saturday_hours getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Saturday Hours", "text_value": "10:00 AM - 2:00 PM"}
            ],
        )
        assert hours.saturday_hours == "10:00 AM - 2:00 PM"

    def test_sunday_hours_getter(self) -> None:
        """sunday_hours getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Sunday Hours", "text_value": "Closed"}
            ],
        )
        assert hours.sunday_hours == "Closed"


class TestHoursAdditionalFields:
    """Tests for Hours additional fields."""

    def test_timezone_getter(self) -> None:
        """timezone getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Timezone", "text_value": "America/New_York"}
            ],
        )
        assert hours.timezone == "America/New_York"

    def test_hours_notes_getter(self) -> None:
        """hours_notes getter returns value."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Hours Notes", "text_value": "Closed on holidays"}
            ],
        )
        assert hours.hours_notes == "Closed on holidays"


class TestHoursComputedProperties:
    """Tests for Hours computed properties."""

    def test_weekday_hours(self) -> None:
        """weekday_hours returns Monday-Friday hours."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Monday Hours", "text_value": "9-5"},
                {"gid": "2", "name": "Tuesday Hours", "text_value": "9-5"},
                {"gid": "3", "name": "Wednesday Hours", "text_value": "9-5"},
                {"gid": "4", "name": "Thursday Hours", "text_value": "9-5"},
                {"gid": "5", "name": "Friday Hours", "text_value": "9-5"},
            ],
        )
        weekday = hours.weekday_hours
        assert weekday["monday"] == "9-5"
        assert weekday["tuesday"] == "9-5"
        assert weekday["wednesday"] == "9-5"
        assert weekday["thursday"] == "9-5"
        assert weekday["friday"] == "9-5"

    def test_weekend_hours(self) -> None:
        """weekend_hours returns Saturday-Sunday hours."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Saturday Hours", "text_value": "10-2"},
                {"gid": "2", "name": "Sunday Hours", "text_value": "Closed"},
            ],
        )
        weekend = hours.weekend_hours
        assert weekend["saturday"] == "10-2"
        assert weekend["sunday"] == "Closed"

    def test_all_hours(self) -> None:
        """all_hours returns all days."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Monday Hours", "text_value": "9-5"},
                {"gid": "2", "name": "Sunday Hours", "text_value": "Closed"},
            ],
        )
        all_hrs = hours.all_hours
        assert "monday" in all_hrs
        assert "sunday" in all_hrs
        assert len(all_hrs) == 7


class TestHoursIsOpenOn:
    """Tests for Hours.is_open_on method."""

    def test_is_open_on_returns_true_when_hours_set(self) -> None:
        """is_open_on returns True when hours are set."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Monday Hours", "text_value": "9:00 AM - 5:00 PM"}
            ],
        )
        assert hours.is_open_on("monday") is True

    def test_is_open_on_returns_false_when_closed(self) -> None:
        """is_open_on returns False when hours are 'Closed'."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Sunday Hours", "text_value": "Closed"}
            ],
        )
        assert hours.is_open_on("sunday") is False

    def test_is_open_on_returns_false_when_not_set(self) -> None:
        """is_open_on returns False when hours not set."""
        hours = Hours(gid="123", custom_fields=[])
        assert hours.is_open_on("monday") is False

    def test_is_open_on_case_insensitive(self) -> None:
        """is_open_on is case-insensitive for day names."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Monday Hours", "text_value": "9-5"}
            ],
        )
        assert hours.is_open_on("MONDAY") is True
        assert hours.is_open_on("Monday") is True

    @pytest.mark.parametrize("closed_value", ["Closed", "closed", "N/A", "none", ""])
    def test_is_open_on_recognizes_closed_indicators(self, closed_value: str) -> None:
        """is_open_on recognizes various closed indicators."""
        hours = Hours(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Monday Hours", "text_value": closed_value}
            ],
        )
        assert hours.is_open_on("monday") is False


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
