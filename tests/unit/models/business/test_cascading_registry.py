"""Tests for CASCADING_FIELD_REGISTRY and helper functions.

Per TDD-CASCADING-FIELD-RESOLUTION-001 Task 1: Tests for static registry
that maps field names to their CascadingFieldDef instances.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.business import Business
from autom8_asana.models.business.fields import (
    CascadingFieldDef,
    CascadingFieldEntry,
    get_cascading_field,
    get_cascading_field_registry,
)
from autom8_asana.models.business.unit import Unit


class TestCascadingFieldRegistry:
    """Tests for the cascading field registry."""

    def test_registry_contains_business_fields(self) -> None:
        """Registry includes all Business.CascadingFields definitions."""
        registry = get_cascading_field_registry()

        # Business cascading fields
        expected_business_fields = [
            "office phone",
            "company id",
            "business name",
            "primary contact phone",
        ]

        for field_name in expected_business_fields:
            assert field_name in registry, f"Missing Business field: {field_name}"
            owner_class, field_def = registry[field_name]
            assert owner_class is Business
            assert isinstance(field_def, CascadingFieldDef)

    def test_registry_contains_unit_fields(self) -> None:
        """Registry includes all Unit.CascadingFields definitions."""
        registry = get_cascading_field_registry()

        # Unit cascading fields
        expected_unit_fields = [
            "platforms",
            "vertical",
            "booking type",
        ]

        for field_name in expected_unit_fields:
            assert field_name in registry, f"Missing Unit field: {field_name}"
            owner_class, field_def = registry[field_name]
            assert owner_class is Unit
            assert isinstance(field_def, CascadingFieldDef)

    def test_registry_field_count(self) -> None:
        """Registry contains expected total field count (4 Business + 3 Unit)."""
        registry = get_cascading_field_registry()
        assert len(registry) == 7

    def test_registry_is_cached(self) -> None:
        """Registry is built once and cached for subsequent calls."""
        registry1 = get_cascading_field_registry()
        registry2 = get_cascading_field_registry()
        # Should be the exact same object (not just equal)
        assert registry1 is registry2


class TestGetCascadingField:
    """Tests for get_cascading_field() helper function."""

    def test_returns_tuple_for_known_field(self) -> None:
        """Returns (owner_class, field_def) tuple for known fields."""
        result = get_cascading_field("Office Phone")

        assert result is not None
        owner_class, field_def = result
        assert owner_class is Business
        assert isinstance(field_def, CascadingFieldDef)
        assert field_def.name == "Office Phone"

    def test_returns_none_for_unknown_field(self) -> None:
        """Returns None for fields not in registry."""
        result = get_cascading_field("Unknown Custom Field")
        assert result is None

    def test_case_insensitive_lookup_lowercase(self) -> None:
        """Lookup works with lowercase field names."""
        result = get_cascading_field("office phone")

        assert result is not None
        _, field_def = result
        assert field_def.name == "Office Phone"

    def test_case_insensitive_lookup_uppercase(self) -> None:
        """Lookup works with uppercase field names."""
        result = get_cascading_field("OFFICE PHONE")

        assert result is not None
        _, field_def = result
        assert field_def.name == "Office Phone"

    def test_case_insensitive_lookup_mixed_case(self) -> None:
        """Lookup works with mixed case field names."""
        result = get_cascading_field("oFfIcE pHoNe")

        assert result is not None
        _, field_def = result
        assert field_def.name == "Office Phone"

    def test_whitespace_trimming(self) -> None:
        """Lookup trims leading/trailing whitespace."""
        result = get_cascading_field("  Office Phone  ")

        assert result is not None
        _, field_def = result
        assert field_def.name == "Office Phone"

    def test_business_office_phone_field_def_properties(self) -> None:
        """Verify Office Phone field has expected properties."""
        result = get_cascading_field("Office Phone")

        assert result is not None
        owner_class, field_def = result
        assert owner_class is Business
        assert field_def.name == "Office Phone"
        assert field_def.target_types == {"Unit", "Offer", "Process", "Contact"}
        assert field_def.allow_override is False

    def test_business_company_id_field_def_properties(self) -> None:
        """Verify Company ID field has expected properties."""
        result = get_cascading_field("Company ID")

        assert result is not None
        owner_class, field_def = result
        assert owner_class is Business
        assert field_def.name == "Company ID"
        assert field_def.target_types is None  # Cascades to all
        assert field_def.allow_override is False

    def test_business_business_name_field_def_properties(self) -> None:
        """Verify Business Name field has expected properties."""
        result = get_cascading_field("Business Name")

        assert result is not None
        owner_class, field_def = result
        assert owner_class is Business
        assert field_def.name == "Business Name"
        assert field_def.target_types == {"Unit", "Offer"}
        assert field_def.source_field == "name"

    def test_unit_platforms_field_def_properties(self) -> None:
        """Verify Platforms field has expected properties."""
        result = get_cascading_field("Platforms")

        assert result is not None
        owner_class, field_def = result
        assert owner_class is Unit
        assert field_def.name == "Platforms"
        assert field_def.target_types == {"Offer"}
        assert field_def.allow_override is True  # Offers can override

    def test_unit_vertical_field_def_properties(self) -> None:
        """Verify Vertical field has expected properties."""
        result = get_cascading_field("Vertical")

        assert result is not None
        owner_class, field_def = result
        assert owner_class is Unit
        assert field_def.name == "Vertical"
        assert field_def.target_types == {"Offer", "Process"}
        assert field_def.allow_override is False

    def test_unit_booking_type_field_def_properties(self) -> None:
        """Verify Booking Type field has expected properties."""
        result = get_cascading_field("Booking Type")

        assert result is not None
        owner_class, field_def = result
        assert owner_class is Unit
        assert field_def.name == "Booking Type"
        assert field_def.target_types == {"Offer"}
        assert field_def.allow_override is False


class TestCascadingFieldEntryType:
    """Tests for CascadingFieldEntry type alias usage."""

    def test_entry_type_unpacking(self) -> None:
        """Entry can be unpacked into owner_class and field_def."""
        result = get_cascading_field("Office Phone")
        assert result is not None

        # Type annotation should work
        entry: CascadingFieldEntry = result
        owner_class, field_def = entry

        assert owner_class is Business
        assert isinstance(field_def, CascadingFieldDef)

    def test_registry_values_are_entries(self) -> None:
        """All registry values are valid CascadingFieldEntry tuples."""
        registry = get_cascading_field_registry()

        for field_name, entry in registry.items():
            owner_class, field_def = entry
            assert isinstance(owner_class, type), f"Invalid owner for {field_name}"
            assert isinstance(
                field_def, CascadingFieldDef
            ), f"Invalid field_def for {field_name}"


class TestModuleExports:
    """Tests for module export availability."""

    def test_exports_from_fields_module(self) -> None:
        """Registry functions exported from fields module."""
        from autom8_asana.models.business import fields

        assert hasattr(fields, "get_cascading_field")
        assert hasattr(fields, "get_cascading_field_registry")
        assert hasattr(fields, "CascadingFieldEntry")

    def test_exports_from_business_package(self) -> None:
        """Registry functions exported from business package."""
        from autom8_asana.models import business

        assert hasattr(business, "get_cascading_field")
        assert hasattr(business, "get_cascading_field_registry")
        assert hasattr(business, "CascadingFieldEntry")

    def test_direct_import_from_package(self) -> None:
        """Functions can be imported directly from package."""
        from autom8_asana.models.business import (
            CascadingFieldEntry,
            get_cascading_field,
            get_cascading_field_registry,
        )

        # Verify they work
        registry = get_cascading_field_registry()
        assert len(registry) > 0

        result = get_cascading_field("Office Phone")
        assert result is not None
