"""Tests for custom field descriptors.

Per TDD-PATTERNS-A: Tests for CustomFieldDescriptor[T] and all field type implementations.
Per ADR-0081: Custom field descriptor pattern.
Per ADR-0082: Fields class auto-generation strategy.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import arrow
import pytest

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    CustomFieldDescriptor,
    DateField,
    EnumField,
    IntField,
    MultiEnumField,
    NumberField,
    PeopleField,
    TextField,
)

# =============================================================================
# Test Fixtures: Mock CustomFieldAccessor
# =============================================================================


class MockCustomFieldAccessor:
    """Mock accessor for testing descriptors."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data or {}
        self._modifications: dict[str, Any] = {}

    def get(self, field_name: str | None, default: Any = None) -> Any:
        """Get field value."""
        if field_name is None:
            return default
        if field_name in self._modifications:
            return self._modifications[field_name]
        return self._data.get(field_name, default)

    def set(self, field_name: str | None, value: Any) -> None:
        """Set field value (tracks as modification)."""
        if field_name is not None:
            self._modifications[field_name] = value


class StubEntityWithDescriptors(BusinessEntity):
    """Stub entity with custom field descriptors for testing.

    Note: Descriptors declared WITHOUT type annotations per ADR-0077.
    """

    # Text fields
    company_id = TextField()
    facebook_page_id = TextField(field_name="Facebook Page ID")

    # Enum fields
    vertical = EnumField()
    status = EnumField(field_name="Status")

    # Multi-enum fields
    ad_types = MultiEnumField()

    # Number fields
    mrr = NumberField(field_name="MRR")
    budget = NumberField()

    # Int fields
    num_ai_copies = IntField()
    count = IntField(field_name="Count")

    # Cascading field
    office_phone = TextField(cascading=True)

    # People fields
    rep = PeopleField()
    team_members = PeopleField(field_name="Team Members")

    # Date fields
    due_date = DateField()
    started_at = DateField(field_name="Started At")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._mock_accessor: MockCustomFieldAccessor | None = None

    def custom_fields_editor(self) -> MockCustomFieldAccessor:
        """Return mock accessor."""
        if self._mock_accessor is None:
            self._mock_accessor = MockCustomFieldAccessor()
        return self._mock_accessor

    def set_mock_data(self, data: dict[str, Any]) -> None:
        """Set mock data for testing."""
        self._mock_accessor = MockCustomFieldAccessor(data)


# =============================================================================
# Field Name Derivation Tests (ADR-0082)
# =============================================================================


class TestFieldNameDerivation:
    """Tests for field name derivation from property names."""

    @pytest.mark.parametrize(
        "descriptor_cls,attr_name,expected",
        [
            pytest.param(TextField, "company_name", "Company Name", id="simple-name"),
            pytest.param(TextField, "status", "Status", id="single-word"),
            pytest.param(TextField, "company_id", "Company ID", id="abbrev-id"),
            pytest.param(NumberField, "mrr", "MRR", id="abbrev-mrr"),
            pytest.param(IntField, "total_ai_count", "Total AI Count", id="abbrev-ai"),
            pytest.param(TextField, "website_url", "Website URL", id="abbrev-url"),
            pytest.param(EnumField, "vca_status", "VCA Status", id="abbrev-vca"),
            pytest.param(TextField, "sms_number", "SMS Number", id="abbrev-sms"),
            pytest.param(TextField, "google_cal_id", "Google CAL ID", id="abbrev-cal"),
            pytest.param(MultiEnumField, "ad_types", "AD Types", id="abbrev-ad"),
            pytest.param(TextField, "ai_ad_url_id", "AI AD URL ID", id="multiple-abbreviations"),
        ],
    )
    def test_field_name_derivation(
        self, descriptor_cls: type, attr_name: str, expected: str
    ) -> None:
        """Verify snake_case property name derives correct Title Case field name."""
        descriptor = descriptor_cls()
        descriptor.__set_name__(StubEntityWithDescriptors, attr_name)
        assert descriptor.field_name == expected

    def test_explicit_override(self) -> None:
        """Explicit field_name overrides derivation."""
        descriptor = TextField(field_name="Custom Name Here")
        descriptor.__set_name__(StubEntityWithDescriptors, "some_property")
        assert descriptor.field_name == "Custom Name Here"

    def test_constant_name_generation(self) -> None:
        """Constant name is SCREAMING_SNAKE version."""
        descriptor = TextField()
        descriptor.__set_name__(StubEntityWithDescriptors, "company_id")
        assert descriptor._constant_name == "COMPANY_ID"

    def test_public_name_stored(self) -> None:
        """Public name is stored."""
        descriptor = TextField()
        descriptor.__set_name__(StubEntityWithDescriptors, "company_id")
        assert descriptor.public_name == "company_id"


# =============================================================================
# TextField Tests
# =============================================================================


class TestTextField:
    """Tests for TextField descriptor."""

    def test_get_string_value(self) -> None:
        """Returns string value directly."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Company ID": "ACME-001"})

        result = entity.company_id
        assert result == "ACME-001"

    def test_get_none_value(self) -> None:
        """Returns None when field not set."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        result = entity.company_id
        assert result is None

    def test_get_coerces_non_string(self) -> None:
        """Coerces non-string values to string."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Company ID": 12345})

        result = entity.company_id
        assert result == "12345"

    def test_set_value(self) -> None:
        """Sets value via accessor."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.company_id = "NEW-001"

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Company ID") == "NEW-001"

    def test_set_none(self) -> None:
        """Sets None to clear field."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Company ID": "OLD-001"})

        entity.company_id = None

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Company ID") is None

    def test_explicit_field_name(self) -> None:
        """Uses explicit field name when provided."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Facebook Page ID": "fb-12345"})

        result = entity.facebook_page_id
        assert result == "fb-12345"

    def test_class_access_returns_descriptor(self) -> None:
        """Accessing on class returns descriptor itself."""
        descriptor = StubEntityWithDescriptors.company_id
        assert isinstance(descriptor, TextField)


# =============================================================================
# EnumField Tests
# =============================================================================


class TestEnumField:
    """Tests for EnumField descriptor."""

    def test_get_extracts_name_from_dict(self) -> None:
        """Extracts name from enum dict."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Vertical": {"gid": "123", "name": "Healthcare"}})

        result = entity.vertical
        assert result == "Healthcare"

    def test_get_none_value(self) -> None:
        """Returns None when field not set."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        result = entity.vertical
        assert result is None

    def test_get_string_passthrough(self) -> None:
        """Passes through string values."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Vertical": "Healthcare"})

        result = entity.vertical
        assert result == "Healthcare"

    def test_get_dict_with_none_name(self) -> None:
        """Returns None when dict has no name."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Vertical": {"gid": "123"}})

        result = entity.vertical
        assert result is None

    def test_get_coerces_other_types(self) -> None:
        """Coerces other types to string."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Vertical": 123})

        result = entity.vertical
        assert result == "123"

    def test_set_value(self) -> None:
        """Sets value via accessor."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.vertical = "Healthcare"

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Vertical") == "Healthcare"


# =============================================================================
# MultiEnumField Tests
# =============================================================================


class TestMultiEnumField:
    """Tests for MultiEnumField descriptor."""

    def test_get_extracts_names_from_list_of_dicts(self) -> None:
        """Extracts names from list of enum dicts."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data(
            {
                "AD Types": [
                    {"gid": "1", "name": "Image"},
                    {"gid": "2", "name": "Video"},
                ]
            }
        )

        result = entity.ad_types
        assert result == ["Image", "Video"]

    def test_get_returns_empty_list_for_none(self) -> None:
        """Returns empty list when field is None."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        result = entity.ad_types
        assert result == []

    def test_get_returns_empty_list_for_non_list(self) -> None:
        """Returns empty list when value is not a list."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"AD Types": "not a list"})

        result = entity.ad_types
        assert result == []

    def test_get_handles_string_items(self) -> None:
        """Handles list of strings (already extracted)."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"AD Types": ["Image", "Video"]})

        result = entity.ad_types
        assert result == ["Image", "Video"]

    def test_get_skips_none_items(self) -> None:
        """Skips None items in list."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data(
            {
                "AD Types": [
                    {"gid": "1", "name": "Image"},
                    None,
                    {"gid": "2", "name": "Video"},
                ]
            }
        )

        result = entity.ad_types
        assert result == ["Image", "Video"]

    def test_get_skips_dict_without_name(self) -> None:
        """Skips dict items without name."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data(
            {
                "AD Types": [
                    {"gid": "1", "name": "Image"},
                    {"gid": "2"},  # No name
                ]
            }
        )

        result = entity.ad_types
        assert result == ["Image"]

    def test_set_value(self) -> None:
        """Sets value via accessor."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.ad_types = ["Image", "Video"]

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("AD Types") == ["Image", "Video"]

    def test_set_none(self) -> None:
        """Sets None to clear field."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.ad_types = None

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("AD Types") is None


# =============================================================================
# NumberField Tests
# =============================================================================


class TestNumberField:
    """Tests for NumberField descriptor."""

    def test_get_converts_to_decimal(self) -> None:
        """Converts number to Decimal."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"MRR": 1234.56})

        result = entity.mrr
        assert result == Decimal("1234.56")
        assert isinstance(result, Decimal)

    def test_get_none_value(self) -> None:
        """Returns None when field not set."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        result = entity.mrr
        assert result is None

    def test_get_zero_value(self) -> None:
        """Handles zero values."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"MRR": 0})

        result = entity.mrr
        assert result == Decimal("0")

    def test_get_integer_value(self) -> None:
        """Converts integer to Decimal."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"MRR": 1000})

        result = entity.mrr
        assert result == Decimal("1000")

    def test_get_string_number_value(self) -> None:
        """Converts string number to Decimal."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"MRR": "1234.56"})

        result = entity.mrr
        assert result == Decimal("1234.56")

    def test_set_decimal_converts_to_float(self) -> None:
        """Converts Decimal to float for API."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.mrr = Decimal("5000.00")

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("MRR") == 5000.0
        assert isinstance(accessor._modifications.get("MRR"), float)

    def test_set_none(self) -> None:
        """Sets None to clear field."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.mrr = None

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("MRR") is None

    def test_explicit_field_name(self) -> None:
        """Uses explicit field name (MRR not derived as M R R)."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"MRR": 1000})

        result = entity.mrr
        assert result == Decimal("1000")


# =============================================================================
# IntField Tests
# =============================================================================


class TestIntField:
    """Tests for IntField descriptor."""

    def test_get_returns_integer(self) -> None:
        """Returns integer value."""
        entity = StubEntityWithDescriptors(gid="test-1")
        # Note: "num_ai_copies" derives to "NUM AI Copies" (both are abbreviations)
        entity.set_mock_data({"NUM AI Copies": 5})

        result = entity.num_ai_copies
        assert result == 5
        assert isinstance(result, int)

    def test_get_none_value(self) -> None:
        """Returns None when field not set."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        result = entity.num_ai_copies
        assert result is None

    def test_get_zero_value(self) -> None:
        """Handles zero values."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"NUM AI Copies": 0})

        result = entity.num_ai_copies
        assert result == 0

    def test_get_truncates_float(self) -> None:
        """Truncates float to integer."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"NUM AI Copies": 5.7})

        result = entity.num_ai_copies
        assert result == 5

    def test_get_converts_string_number(self) -> None:
        """Converts string number to integer."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"NUM AI Copies": "10"})

        result = entity.num_ai_copies
        assert result == 10

    def test_set_value(self) -> None:
        """Sets integer value via accessor."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.num_ai_copies = 3

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("NUM AI Copies") == 3

    def test_set_none(self) -> None:
        """Sets None to clear field."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.num_ai_copies = None

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("NUM AI Copies") is None


# =============================================================================
# PeopleField Tests
# =============================================================================


class TestPeopleField:
    """Tests for PeopleField descriptor."""

    def test_get_returns_list_of_dicts(self) -> None:
        """Returns list of person dicts."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data(
            {
                "Rep": [
                    {"gid": "123", "name": "John Doe", "email": "john@example.com"},
                    {"gid": "456", "name": "Jane Smith", "email": "jane@example.com"},
                ]
            }
        )

        result = entity.rep
        assert len(result) == 2
        assert result[0]["name"] == "John Doe"
        assert result[1]["name"] == "Jane Smith"

    def test_get_returns_empty_list_for_none(self) -> None:
        """Returns empty list when field is None."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        result = entity.rep
        assert result == []
        assert isinstance(result, list)

    def test_get_returns_empty_list_for_non_list(self) -> None:
        """Returns empty list when value is not a list."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Rep": "not a list"})

        result = entity.rep
        assert result == []

    def test_get_returns_empty_list_for_empty_list(self) -> None:
        """Returns empty list when field is empty list."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Rep": []})

        result = entity.rep
        assert result == []

    def test_set_value(self) -> None:
        """Sets list of person dicts."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        people = [{"gid": "789", "name": "New Person"}]
        entity.rep = people

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Rep") == people

    def test_set_none(self) -> None:
        """Sets None to clear field."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.rep = None

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Rep") is None

    def test_explicit_field_name(self) -> None:
        """Uses explicit field name when provided."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Team Members": [{"gid": "111", "name": "Team Member 1"}]})

        result = entity.team_members
        assert len(result) == 1
        assert result[0]["name"] == "Team Member 1"

    def test_class_access_returns_descriptor(self) -> None:
        """Accessing on class returns descriptor itself."""
        descriptor = StubEntityWithDescriptors.rep
        assert isinstance(descriptor, PeopleField)


# =============================================================================
# DateField Tests (ADR-0083)
# =============================================================================


class TestDateField:
    """Tests for DateField descriptor with Arrow integration."""

    def test_get_parses_iso_date(self) -> None:
        """Parses ISO 8601 date string to Arrow."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Due Date": "2025-12-16"})

        result = entity.due_date
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 16

    def test_get_parses_iso_datetime(self) -> None:
        """Parses ISO 8601 datetime string to Arrow."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Due Date": "2025-12-16T10:30:00Z"})

        result = entity.due_date
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 16
        assert result.hour == 10
        assert result.minute == 30

    def test_get_none_value(self) -> None:
        """Returns None when field is not set."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        result = entity.due_date
        assert result is None

    def test_get_empty_string_returns_none(self) -> None:
        """Returns None for empty string."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Due Date": ""})

        result = entity.due_date
        assert result is None

    def test_get_invalid_string_returns_none(self) -> None:
        """Returns None for invalid date string with warning."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Due Date": "not-a-date"})

        result = entity.due_date
        assert result is None

    def test_get_returns_arrow_passthrough(self) -> None:
        """Returns Arrow object if already Arrow."""
        entity = StubEntityWithDescriptors(gid="test-1")
        arrow_date = arrow.get("2025-06-15")
        entity.set_mock_data({"Due Date": arrow_date})

        result = entity.due_date
        assert result is arrow_date

    def test_set_arrow_serializes_to_iso(self) -> None:
        """Serializes Arrow to ISO date string."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        arrow_date = arrow.get("2025-12-25")
        entity.due_date = arrow_date

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Due Date") == "2025-12-25"

    def test_set_none(self) -> None:
        """Sets None to clear field."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.due_date = None

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Due Date") is None

    def test_set_arrow_with_time_serializes_date_only(self) -> None:
        """Serializes only date portion when Arrow has time."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        arrow_datetime = arrow.get("2025-12-25T15:30:45Z")
        entity.due_date = arrow_datetime

        accessor = entity.custom_fields_editor()
        # Should only serialize date, not time
        assert accessor._modifications.get("Due Date") == "2025-12-25"

    def test_explicit_field_name(self) -> None:
        """Uses explicit field name when provided."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Started At": "2025-01-15"})

        result = entity.started_at
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_class_access_returns_descriptor(self) -> None:
        """Accessing on class returns descriptor itself."""
        descriptor = StubEntityWithDescriptors.due_date
        assert isinstance(descriptor, DateField)

    def test_arrow_humanize_works(self) -> None:
        """Arrow humanize() method works on returned values."""
        entity = StubEntityWithDescriptors(gid="test-1")
        # Use a future date for consistent humanize output
        future_date = arrow.now().shift(days=7).format("YYYY-MM-DD")
        entity.set_mock_data({"Due Date": future_date})

        result = entity.due_date
        assert result is not None
        # humanize() should return a string like "in 7 days"
        humanized = result.humanize()
        assert isinstance(humanized, str)
        assert len(humanized) > 0

    def test_arrow_format_works(self) -> None:
        """Arrow format() method works on returned values."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Due Date": "2025-12-16"})

        result = entity.due_date
        assert result is not None
        formatted = result.format("MMMM D, YYYY")
        assert formatted == "December 16, 2025"

    def test_arrow_shift_works(self) -> None:
        """Arrow shift() method works for date arithmetic."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Due Date": "2025-12-16"})

        result = entity.due_date
        assert result is not None
        shifted = result.shift(days=7)
        assert shifted.day == 23
        assert shifted.month == 12

    def test_timezone_preserved(self) -> None:
        """Timezone information is preserved from datetime strings."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Due Date": "2025-12-16T10:30:00+05:00"})

        result = entity.due_date
        assert result is not None
        # Arrow preserves timezone
        assert result.hour == 10


# =============================================================================
# Cascading Parameter Tests
# =============================================================================


class TestCascadingParameter:
    """Tests for cascading parameter (metadata only)."""

    def test_cascading_true_stored(self) -> None:
        """Cascading parameter is stored as metadata."""
        descriptor = StubEntityWithDescriptors.office_phone
        assert descriptor.cascading is True

    def test_cascading_false_default(self) -> None:
        """Cascading defaults to False."""
        descriptor = StubEntityWithDescriptors.company_id
        assert descriptor.cascading is False

    def test_cascading_does_not_affect_get(self) -> None:
        """Cascading does not change get behavior."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Office Phone": "555-1234"})

        result = entity.office_phone
        assert result == "555-1234"

    def test_cascading_does_not_affect_set(self) -> None:
        """Cascading does not change set behavior."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.office_phone = "555-5678"

        accessor = entity.custom_fields_editor()
        assert accessor._modifications.get("Office Phone") == "555-5678"


# =============================================================================
# Fields Class Auto-Generation Tests (ADR-0082)
# =============================================================================


class TestFieldsClassGeneration:
    """Tests for Fields class auto-generation."""

    def test_fields_class_exists(self) -> None:
        """Fields class is generated."""
        assert hasattr(StubEntityWithDescriptors, "Fields")

    @pytest.mark.parametrize(
        "constant_name,expected_value",
        [
            pytest.param("COMPANY_ID", "Company ID", id="text-field"),
            pytest.param("FACEBOOK_PAGE_ID", "Facebook Page ID", id="explicit-name"),
            pytest.param("VERTICAL", "Vertical", id="enum-field"),
            pytest.param("MRR", "MRR", id="number-field"),
            pytest.param("NUM_AI_COPIES", "NUM AI Copies", id="int-field"),
            pytest.param("AD_TYPES", "AD Types", id="multi-enum"),
            pytest.param("OFFICE_PHONE", "Office Phone", id="cascading"),
            pytest.param("REP", "Rep", id="people-field"),
            pytest.param("DUE_DATE", "Due Date", id="date-field"),
        ],
    )
    def test_fields_has_constant(self, constant_name: str, expected_value: str) -> None:
        """Verify Fields class has constant with correct value."""
        assert hasattr(StubEntityWithDescriptors.Fields, constant_name)
        assert getattr(StubEntityWithDescriptors.Fields, constant_name) == expected_value


class TestFieldsClassWithExistingFields:
    """Tests for Fields class generation with existing Fields class."""

    def test_preserves_existing_constants(self) -> None:
        """Existing Fields class constants are preserved."""

        class EntityWithExistingFields(BusinessEntity):
            """Entity with both existing Fields and descriptors."""

            class Fields:
                LEGACY_FIELD = "Legacy Field"

            new_field = TextField()

            def custom_fields_editor(self) -> MockCustomFieldAccessor:
                return MockCustomFieldAccessor()

        # Both should exist
        assert hasattr(EntityWithExistingFields.Fields, "LEGACY_FIELD")
        assert EntityWithExistingFields.Fields.LEGACY_FIELD == "Legacy Field"
        assert hasattr(EntityWithExistingFields.Fields, "NEW_FIELD")
        assert EntityWithExistingFields.Fields.NEW_FIELD == "New Field"


# =============================================================================
# Descriptor Protocol Tests
# =============================================================================


class TestDescriptorProtocol:
    """Tests for descriptor protocol implementation."""

    def test_get_on_class_returns_descriptor(self) -> None:
        """Accessing descriptor on class returns descriptor itself."""
        descriptor = StubEntityWithDescriptors.company_id
        assert isinstance(descriptor, TextField)

    def test_get_on_instance_returns_value(self) -> None:
        """Accessing descriptor on instance returns field value."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Company ID": "TEST-001"})

        result = entity.company_id
        assert result == "TEST-001"

    def test_set_on_instance_stores_value(self) -> None:
        """Setting descriptor on instance stores in accessor."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        entity.company_id = "NEW-001"

        accessor = entity.custom_fields_editor()
        assert "Company ID" in accessor._modifications

    def test_slots_defined(self) -> None:
        """Descriptors use __slots__ for memory efficiency."""
        descriptor = CustomFieldDescriptor()
        assert hasattr(descriptor, "__slots__")
        assert "field_name" in CustomFieldDescriptor.__slots__
        assert "cascading" in CustomFieldDescriptor.__slots__
        assert "public_name" in CustomFieldDescriptor.__slots__
        assert "_constant_name" in CustomFieldDescriptor.__slots__


# =============================================================================
# Base Class Tests
# =============================================================================


class TestCustomFieldDescriptorBase:
    """Tests for CustomFieldDescriptor base class."""

    def test_get_value_not_implemented(self) -> None:
        """Base _get_value raises NotImplementedError."""
        descriptor = CustomFieldDescriptor[str]()
        descriptor.field_name = "Test Field"

        mock_obj = MagicMock()
        with pytest.raises(NotImplementedError):
            descriptor._get_value(mock_obj)

    def test_set_value_default_implementation(self) -> None:
        """Base _set_value calls accessor.set()."""
        descriptor = CustomFieldDescriptor[str]()
        descriptor.field_name = "Test Field"

        mock_obj = MagicMock()
        mock_accessor = MagicMock()
        mock_obj.custom_fields_editor.return_value = mock_accessor

        descriptor._set_value(mock_obj, "test value")

        mock_accessor.set.assert_called_once_with("Test Field", "test value")

    def test_abbreviations_frozenset(self) -> None:
        """ABBREVIATIONS is a frozenset with expected values."""
        abbrevs = CustomFieldDescriptor.ABBREVIATIONS
        assert isinstance(abbrevs, frozenset)
        assert "mrr" in abbrevs
        assert "ai" in abbrevs
        assert "url" in abbrevs
        assert "id" in abbrevs
        assert "num" in abbrevs
        assert "cal" in abbrevs
        assert "vca" in abbrevs
        assert "sms" in abbrevs
        assert "ad" in abbrevs


# =============================================================================
# Pydantic Compatibility Tests (ADR-0077)
# =============================================================================


class TestPydanticCompatibility:
    """Tests for Pydantic compatibility."""

    def test_descriptors_not_in_model_fields(self) -> None:
        """Descriptors are not treated as Pydantic model fields."""
        # model_fields should not include descriptor names
        assert "company_id" not in StubEntityWithDescriptors.model_fields
        assert "vertical" not in StubEntityWithDescriptors.model_fields
        assert "mrr" not in StubEntityWithDescriptors.model_fields

    def test_model_construction_with_descriptors(self) -> None:
        """Model can be constructed with descriptors defined."""
        # Should not raise
        entity = StubEntityWithDescriptors(gid="test-1", name="Test Entity")
        assert entity.gid == "test-1"
        assert entity.name == "Test Entity"

    def test_descriptor_access_after_construction(self) -> None:
        """Descriptors accessible after Pydantic construction."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({"Company ID": "ACME"})

        # Should work, not raise
        assert entity.company_id == "ACME"

    def test_descriptor_set_after_construction(self) -> None:
        """Descriptors can be set after Pydantic construction."""
        entity = StubEntityWithDescriptors(gid="test-1")
        entity.set_mock_data({})

        # Should work, not raise
        entity.company_id = "NEW"
        assert entity.custom_fields_editor()._modifications.get("Company ID") == "NEW"
