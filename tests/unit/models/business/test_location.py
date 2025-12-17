"""Tests for Location and LocationHolder models.

Per TDD-BIZMODEL Phase 3: Tests for Location entity with address fields.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.location import Location, LocationHolder
from autom8_asana.models.business.hours import Hours
from autom8_asana.models.task import Task


class TestLocation:
    """Tests for Location model."""

    def test_location_inherits_from_task(self) -> None:
        """Location inherits from Task and can be constructed."""
        location = Location(gid="123", name="Main Office")
        assert location.gid == "123"
        assert location.name == "Main Office"

    def test_street_property(self) -> None:
        """street getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Street", "text_value": "123 Main St"}
            ],
        )
        assert location.street == "123 Main St"

    def test_street_setter(self) -> None:
        """street setter updates value."""
        location = Location(gid="123", custom_fields=[])
        location.street = "456 Oak Ave"
        assert location.get_custom_fields().get("Street") == "456 Oak Ave"
        assert location.get_custom_fields().has_changes()

    def test_city_property(self) -> None:
        """city getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "City", "text_value": "Springfield"}
            ],
        )
        assert location.city == "Springfield"

    def test_state_property(self) -> None:
        """state getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "State", "text_value": "IL"}
            ],
        )
        assert location.state == "IL"

    def test_zip_code_property(self) -> None:
        """zip_code getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Zip Code", "text_value": "62701"}
            ],
        )
        assert location.zip_code == "62701"

    def test_country_property(self) -> None:
        """country getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Country", "text_value": "USA"}
            ],
        )
        assert location.country == "USA"

    def test_phone_property(self) -> None:
        """phone getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Phone", "text_value": "555-1234"}
            ],
        )
        assert location.phone == "555-1234"

    def test_latitude_property(self) -> None:
        """latitude getter returns float value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Latitude", "number_value": 39.7817}
            ],
        )
        assert location.latitude == 39.7817

    def test_longitude_property(self) -> None:
        """longitude getter returns float value."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Longitude", "number_value": -89.6501}
            ],
        )
        assert location.longitude == -89.6501


class TestLocationFullAddress:
    """Tests for Location.full_address computed property."""

    def test_full_address_complete(self) -> None:
        """full_address combines all address fields."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Street", "text_value": "123 Main St"},
                {"gid": "2", "name": "City", "text_value": "Springfield"},
                {"gid": "3", "name": "State", "text_value": "IL"},
                {"gid": "4", "name": "Zip Code", "text_value": "62701"},
                {"gid": "5", "name": "Country", "text_value": "USA"},
            ],
        )
        assert location.full_address == "123 Main St, Springfield, IL, 62701, USA"

    def test_full_address_partial(self) -> None:
        """full_address handles missing fields."""
        location = Location(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Street", "text_value": "123 Main St"},
                {"gid": "2", "name": "City", "text_value": "Springfield"},
            ],
        )
        assert location.full_address == "123 Main St, Springfield"

    def test_full_address_empty(self) -> None:
        """full_address returns empty string when no fields set."""
        location = Location(gid="123", custom_fields=[])
        assert location.full_address == ""


class TestLocationNavigation:
    """Tests for Location navigation properties."""

    def test_location_holder_property(self) -> None:
        """location_holder returns cached reference."""
        location = Location(gid="123")
        holder = LocationHolder(gid="456")
        location._location_holder = holder
        assert location.location_holder is holder

    def test_invalidate_refs(self) -> None:
        """_invalidate_refs clears cached references."""
        location = Location(gid="123")
        holder = LocationHolder(gid="456")
        location._location_holder = holder
        location._invalidate_refs()
        assert location._location_holder is None
        assert location._business is None


class TestLocationHolder:
    """Tests for LocationHolder model."""

    def test_locations_property_empty(self) -> None:
        """locations returns empty list by default."""
        holder = LocationHolder(gid="123")
        assert holder.locations == []

    def test_locations_property_populated(self) -> None:
        """locations returns populated list."""
        holder = LocationHolder(gid="123")
        holder._locations = [
            Location(gid="l1", name="Main Office"),
            Location(gid="l2", name="Branch Office"),
        ]
        assert len(holder.locations) == 2
        assert holder.locations[0].name == "Main Office"

    def test_primary_location_returns_first(self) -> None:
        """primary_location returns first location."""
        holder = LocationHolder(gid="123")
        holder._locations = [
            Location(gid="l1", name="Main Office"),
            Location(gid="l2", name="Branch Office"),
        ]
        assert holder.primary_location is not None
        assert holder.primary_location.name == "Main Office"

    def test_primary_location_none_when_empty(self) -> None:
        """primary_location returns None when no locations."""
        holder = LocationHolder(gid="123")
        assert holder.primary_location is None

    def test_hours_property(self) -> None:
        """hours returns cached Hours reference."""
        holder = LocationHolder(gid="123")
        hours = Hours(gid="456", name="Hours")
        holder._hours = hours
        assert holder.hours is hours

    def test_populate_children_separates_hours(self) -> None:
        """_populate_children separates Hours from Locations."""
        holder = LocationHolder(gid="123")
        subtasks = [
            Task(gid="l1", name="Main Office", created_at="2024-01-01T00:00:00Z"),
            Task(gid="h1", name="Hours", created_at="2024-01-02T00:00:00Z"),
            Task(gid="l2", name="Branch Office", created_at="2024-01-03T00:00:00Z"),
        ]
        holder._populate_children(subtasks)

        # Should have 2 locations
        assert len(holder.locations) == 2
        assert all(isinstance(loc, Location) for loc in holder.locations)
        assert holder.locations[0].name == "Main Office"
        assert holder.locations[1].name == "Branch Office"

        # Should have hours
        assert holder.hours is not None
        assert isinstance(holder.hours, Hours)
        assert holder.hours.name == "Hours"

    def test_populate_children_sets_back_references(self) -> None:
        """_populate_children sets back references on locations."""
        holder = LocationHolder(gid="123")
        holder._business = None

        subtasks = [Task(gid="l1", name="Main Office")]
        holder._populate_children(subtasks)

        assert holder.locations[0]._location_holder is holder

    def test_invalidate_cache(self) -> None:
        """invalidate_cache clears locations and hours."""
        holder = LocationHolder(gid="123")
        holder._locations = [Location(gid="l1")]
        holder._hours = Hours(gid="h1")
        holder.invalidate_cache()
        assert holder._locations == []
        assert holder._hours is None
