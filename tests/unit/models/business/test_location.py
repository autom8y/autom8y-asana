"""Tests for Location and LocationHolder models.

Per TDD-BIZMODEL Phase 3: Tests for Location entity with address fields.
Per PRD-0024: Updated field schema to match Asana reality.
"""

from __future__ import annotations

from autom8_asana.models.business.hours import Hours
from autom8_asana.models.business.location import Location, LocationHolder
from autom8_asana.models.task import Task


class TestLocation:
    """Tests for Location model."""

    def test_location_inherits_from_task(self) -> None:
        """Location inherits from Task and can be constructed."""
        location = Location(gid="123", name="Main Office")
        assert location.gid == "123"
        assert location.name == "Main Office"


class TestLocationNewFields:
    """Tests for new Location fields per PRD-0024."""

    def test_street_number_property(self) -> None:
        """street_number returns int value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Street #", "number_value": 123}],
        )
        assert location.street_number == 123

    def test_street_number_setter(self) -> None:
        """street_number setter updates value."""
        location = Location(gid="123", custom_fields=[])
        location.street_number = 456
        assert location.custom_fields_editor().get("Street #") == 456

    def test_street_name_property(self) -> None:
        """street_name returns text value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Street Name", "text_value": "Main St"}],
        )
        assert location.street_name == "Main St"

    def test_street_name_setter(self) -> None:
        """street_name setter updates value."""
        location = Location(gid="123", custom_fields=[])
        location.street_name = "Oak Ave"
        assert location.custom_fields_editor().get("Street Name") == "Oak Ave"

    def test_city_property(self) -> None:
        """city getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "City", "text_value": "Springfield"}],
        )
        assert location.city == "Springfield"

    def test_state_property(self) -> None:
        """state getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "State", "text_value": "IL"}],
        )
        assert location.state == "IL"

    def test_zip_code_property(self) -> None:
        """zip_code getter returns value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Zip Code", "text_value": "62701"}],
        )
        assert location.zip_code == "62701"

    def test_country_property_enum(self) -> None:
        """country getter extracts name from enum dict per PRD-0024."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Country", "enum_value": {"name": "US"}}],
        )
        assert location.country == "US"

    def test_time_zone_property(self) -> None:
        """time_zone getter extracts name from enum dict."""
        location = Location(gid="123", custom_fields=[])
        location.custom_fields_editor().set("Time Zone", {"name": "America/New_York"})
        assert location.time_zone == "America/New_York"

    def test_suite_property(self) -> None:
        """suite getter returns text value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Suite", "text_value": "Suite 100"}],
        )
        assert location.suite == "Suite 100"

    def test_neighborhood_property(self) -> None:
        """neighborhood getter returns text value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Neighborhood", "text_value": "Downtown"}],
        )
        assert location.neighborhood == "Downtown"

    def test_office_location_property(self) -> None:
        """office_location getter returns text value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Office Location", "text_value": "2nd Floor"}],
        )
        assert location.office_location == "2nd Floor"

    def test_min_radius_property(self) -> None:
        """min_radius getter returns int value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Min Radius", "number_value": 5}],
        )
        assert location.min_radius == 5

    def test_max_radius_property(self) -> None:
        """max_radius getter returns int value."""
        location = Location(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Max Radius", "number_value": 50}],
        )
        assert location.max_radius == 50


class TestLocationFullAddress:
    """Tests for Location.full_address computed property."""

    def test_full_address_complete(self) -> None:
        """full_address combines all address fields per TDD."""
        location = Location(gid="123", custom_fields=[])
        location.custom_fields_editor().set("Street #", 123)
        location.custom_fields_editor().set("Street Name", "Main St")
        location.custom_fields_editor().set("Suite", "Suite 100")
        location.custom_fields_editor().set("City", "Springfield")
        location.custom_fields_editor().set("State", "IL")
        location.custom_fields_editor().set("Zip Code", "62701")
        location.custom_fields_editor().set("Country", {"name": "US"})

        expected = "123 Main St, Suite 100, Springfield, IL 62701, US"
        assert location.full_address == expected

    def test_full_address_no_suite(self) -> None:
        """full_address works without suite."""
        location = Location(gid="123", custom_fields=[])
        location.custom_fields_editor().set("Street #", 123)
        location.custom_fields_editor().set("Street Name", "Main St")
        location.custom_fields_editor().set("City", "Springfield")
        location.custom_fields_editor().set("State", "IL")

        expected = "123 Main St, Springfield, IL"
        assert location.full_address == expected

    def test_full_address_partial(self) -> None:
        """full_address handles missing fields."""
        location = Location(gid="123", custom_fields=[])
        location.custom_fields_editor().set("City", "Springfield")

        assert location.full_address == "Springfield"

    def test_full_address_empty(self) -> None:
        """full_address returns empty string when no fields set."""
        location = Location(gid="123", custom_fields=[])
        assert location.full_address == ""


class TestLocationFieldsClass:
    """Tests for Location.Fields class constants per PRD-0024."""

    def test_field_names_match_asana(self) -> None:
        """Fields class has correct names per PRD-0024."""
        assert Location.Fields.STREET_NUMBER == "Street #"
        assert Location.Fields.STREET_NAME == "Street Name"
        assert Location.Fields.CITY == "City"
        assert Location.Fields.STATE == "State"
        assert Location.Fields.ZIP_CODE == "Zip Code"
        assert Location.Fields.COUNTRY == "Country"

    def test_new_fields_present(self) -> None:
        """New fields are present per PRD-0024."""
        assert Location.Fields.TIME_ZONE == "Time Zone"
        assert Location.Fields.SUITE == "Suite"
        assert Location.Fields.NEIGHBORHOOD == "Neighborhood"
        assert Location.Fields.OFFICE_LOCATION == "Office Location"
        assert Location.Fields.MIN_RADIUS == "Min Radius"
        assert Location.Fields.MAX_RADIUS == "Max Radius"

    def test_stale_fields_removed(self) -> None:
        """Stale fields are removed per PRD-0024."""
        assert not hasattr(Location.Fields, "STREET")
        assert not hasattr(Location.Fields, "PHONE")
        assert not hasattr(Location.Fields, "LATITUDE")
        assert not hasattr(Location.Fields, "LONGITUDE")


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
