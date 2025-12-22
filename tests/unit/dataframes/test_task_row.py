"""Tests for TaskRow, UnitRow, and ContactRow Pydantic models.

Verifies model construction, immutability, validation, to_dict()
conversion, and Decimal handling for Polars compatibility.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from autom8_asana.dataframes.models.task_row import ContactRow, TaskRow, UnitRow


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_task_data() -> dict[str, Any]:
    """Minimal valid TaskRow data."""
    return {
        "gid": "1234567890",
        "name": "Test Task",
        "type": "default_task",
        "created": datetime(2024, 12, 1, 10, 0, 0, tzinfo=timezone.utc),
        "is_completed": False,
        "url": "https://app.asana.com/0/0/1234567890",
        "last_modified": datetime(2024, 12, 8, 15, 30, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def unit_task_data(base_task_data: dict[str, Any]) -> dict[str, Any]:
    """Valid UnitRow data."""
    return {
        **base_task_data,
        "type": "Unit",
        "mrr": Decimal("1234.56"),
        "weekly_ad_spend": Decimal("500.00"),
        "products": ["ProductA", "ProductB"],
        "languages": ["English", "Spanish"],
        "discount": Decimal("10.5"),
        "office": "New York",
        "office_phone": "+1-555-0123",
        "vertical": "Healthcare",
        "vertical_id": "v123",
        "specialty": "Dental",
        "max_pipeline_stage": "Closed Won",
    }


@pytest.fixture
def contact_task_data(base_task_data: dict[str, Any]) -> dict[str, Any]:
    """Valid ContactRow data."""
    return {
        **base_task_data,
        "type": "Contact",
        "full_name": "John Doe",
        "nickname": "JD",
        "contact_phone": "+1-555-0100",
        "contact_email": "john.doe@example.com",
        "position": "CEO",
        "employee_id": "EMP001",
        "contact_url": "https://linkedin.com/in/johndoe",
        "time_zone": "America/New_York",
        "city": "New York",
    }


# ---------------------------------------------------------------------------
# TaskRow Base Tests
# ---------------------------------------------------------------------------


class TestTaskRowCreation:
    """Tests for TaskRow construction."""

    def test_minimal_creation(self, base_task_data: dict[str, Any]) -> None:
        """Test TaskRow creation with minimal required fields."""
        row = TaskRow(**base_task_data)

        assert row.gid == "1234567890"
        assert row.name == "Test Task"
        assert row.type == "default_task"
        assert row.is_completed is False
        assert row.url == "https://app.asana.com/0/0/1234567890"

    def test_all_optional_fields(self, base_task_data: dict[str, Any]) -> None:
        """Test TaskRow with all optional fields."""
        data = {
            **base_task_data,
            "date": date(2024, 12, 15),
            "due_on": date(2024, 12, 31),
            "completed_at": datetime(2024, 12, 10, 12, 0, 0, tzinfo=timezone.utc),
            "section": "In Progress",
            "tags": ["urgent", "backend"],
        }
        row = TaskRow(**data)

        assert row.date == date(2024, 12, 15)
        assert row.due_on == date(2024, 12, 31)
        assert row.completed_at is not None
        assert row.section == "In Progress"
        assert row.tags == ["urgent", "backend"]

    def test_default_tags_is_empty_list(self, base_task_data: dict[str, Any]) -> None:
        """Test that tags defaults to empty list."""
        row = TaskRow(**base_task_data)
        assert row.tags == []

    def test_field_count(self) -> None:
        """Verify TaskRow has exactly 12 base fields."""
        # Get fields from model_fields (Pydantic v2)
        fields = TaskRow.model_fields
        assert len(fields) == 12


class TestTaskRowImmutability:
    """Tests for TaskRow immutability (frozen=True)."""

    def test_cannot_modify_field(self, base_task_data: dict[str, Any]) -> None:
        """Test that fields cannot be modified after creation."""
        row = TaskRow(**base_task_data)
        with pytest.raises(ValidationError):
            row.name = "Modified Name"  # type: ignore[misc]

    def test_cannot_modify_list_field(self, base_task_data: dict[str, Any]) -> None:
        """Test that list fields are also immutable."""
        data = {**base_task_data, "tags": ["original"]}
        row = TaskRow(**data)

        # Cannot reassign the list
        with pytest.raises(ValidationError):
            row.tags = ["modified"]  # type: ignore[misc]


class TestTaskRowValidation:
    """Tests for TaskRow validation rules."""

    def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TaskRow(
                gid="123",
                name="Test",
                type="task",
                # Missing: created, is_completed, url, last_modified
            )
        errors = exc_info.value.errors()
        assert len(errors) >= 4

    def test_gid_must_be_string(self, base_task_data: dict[str, Any]) -> None:
        """Test that gid must be string type."""
        data = {**base_task_data, "gid": 123}  # int instead of str
        with pytest.raises(ValidationError) as exc_info:
            TaskRow(**data)
        assert any(e["loc"] == ("gid",) for e in exc_info.value.errors())

    def test_extra_forbid_rejects_unknown_fields(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test that extra='forbid' rejects unknown fields."""
        data = {**base_task_data, "unknown_field": "value"}
        with pytest.raises(ValidationError) as exc_info:
            TaskRow(**data)
        assert "extra_forbidden" in str(exc_info.value)

    def test_strict_prevents_type_coercion(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test that strict=True prevents silent type coercion."""
        data = {**base_task_data, "is_completed": "true"}  # str instead of bool
        with pytest.raises(ValidationError):
            TaskRow(**data)


class TestTaskRowToDict:
    """Tests for TaskRow.to_dict() method."""

    def test_to_dict_returns_dict(self, base_task_data: dict[str, Any]) -> None:
        """Test that to_dict returns a dict."""
        row = TaskRow(**base_task_data)
        result = row.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_all_fields(self, base_task_data: dict[str, Any]) -> None:
        """Test that to_dict includes all fields."""
        row = TaskRow(**base_task_data)
        result = row.to_dict()

        assert "gid" in result
        assert "name" in result
        assert "type" in result
        assert "created" in result
        assert "is_completed" in result
        assert "url" in result
        assert "last_modified" in result
        assert "tags" in result

    def test_to_dict_preserves_values(self, base_task_data: dict[str, Any]) -> None:
        """Test that to_dict preserves field values."""
        row = TaskRow(**base_task_data)
        result = row.to_dict()

        assert result["gid"] == "1234567890"
        assert result["name"] == "Test Task"
        assert result["is_completed"] is False


# ---------------------------------------------------------------------------
# UnitRow Tests
# ---------------------------------------------------------------------------


class TestUnitRowCreation:
    """Tests for UnitRow construction."""

    def test_creation_with_all_fields(self, unit_task_data: dict[str, Any]) -> None:
        """Test UnitRow creation with all fields."""
        row = UnitRow(**unit_task_data)

        assert row.mrr == Decimal("1234.56")
        assert row.weekly_ad_spend == Decimal("500.00")
        assert row.products == ["ProductA", "ProductB"]
        assert row.languages == ["English", "Spanish"]
        assert row.discount == Decimal("10.5")
        assert row.office == "New York"
        assert row.office_phone == "+1-555-0123"
        assert row.vertical == "Healthcare"
        assert row.vertical_id == "v123"
        assert row.specialty == "Dental"
        assert row.max_pipeline_stage == "Closed Won"

    def test_default_type_is_unit(self, base_task_data: dict[str, Any]) -> None:
        """Test that UnitRow has default type='Unit'."""
        data = {k: v for k, v in base_task_data.items() if k != "type"}
        row = UnitRow(**data)
        assert row.type == "Unit"

    def test_optional_unit_fields_default_to_none_or_empty(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test UnitRow optional fields default values."""
        data = {k: v for k, v in base_task_data.items() if k != "type"}
        row = UnitRow(**data)

        assert row.mrr is None
        assert row.weekly_ad_spend is None
        assert row.products == []
        assert row.languages == []
        assert row.discount is None
        assert row.office is None

    def test_field_count(self) -> None:
        """Verify UnitRow has 23 fields (12 base + 11 Unit)."""
        fields = UnitRow.model_fields
        assert len(fields) == 23

    def test_inherits_from_task_row(self) -> None:
        """Test that UnitRow inherits from TaskRow."""
        assert issubclass(UnitRow, TaskRow)


class TestUnitRowDecimalHandling:
    """Tests for UnitRow Decimal field handling."""

    def test_decimal_fields_accept_decimal(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test Decimal fields accept Decimal values."""
        data = {
            **base_task_data,
            "type": "Unit",
            "mrr": Decimal("9999.99"),
        }
        row = UnitRow(**data)
        assert row.mrr == Decimal("9999.99")
        assert isinstance(row.mrr, Decimal)

    def test_to_dict_converts_decimal_to_float(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test to_dict converts Decimal values to float for Polars."""
        data = {
            **base_task_data,
            "type": "Unit",
            "mrr": Decimal("1234.56"),
            "weekly_ad_spend": Decimal("500.00"),
        }
        row = UnitRow(**data)
        result = row.to_dict()

        assert isinstance(result["mrr"], float)
        assert result["mrr"] == 1234.56
        assert isinstance(result["weekly_ad_spend"], float)
        assert result["weekly_ad_spend"] == 500.00

    def test_to_dict_handles_none_decimal(self, base_task_data: dict[str, Any]) -> None:
        """Test to_dict handles None Decimal fields."""
        data = {k: v for k, v in base_task_data.items() if k != "type"}
        row = UnitRow(**data)
        result = row.to_dict()

        assert result["mrr"] is None
        assert result["weekly_ad_spend"] is None


# ---------------------------------------------------------------------------
# ContactRow Tests
# ---------------------------------------------------------------------------


class TestContactRowCreation:
    """Tests for ContactRow construction."""

    def test_creation_with_all_fields(self, contact_task_data: dict[str, Any]) -> None:
        """Test ContactRow creation with all fields."""
        row = ContactRow(**contact_task_data)

        assert row.full_name == "John Doe"
        assert row.nickname == "JD"
        assert row.contact_phone == "+1-555-0100"
        assert row.contact_email == "john.doe@example.com"
        assert row.position == "CEO"
        assert row.employee_id == "EMP001"
        assert row.contact_url == "https://linkedin.com/in/johndoe"
        assert row.time_zone == "America/New_York"
        assert row.city == "New York"

    def test_default_type_is_contact(self, base_task_data: dict[str, Any]) -> None:
        """Test that ContactRow has default type='Contact'."""
        data = {k: v for k, v in base_task_data.items() if k != "type"}
        row = ContactRow(**data)
        assert row.type == "Contact"

    def test_optional_contact_fields_default_to_none(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test ContactRow optional fields default to None."""
        data = {k: v for k, v in base_task_data.items() if k != "type"}
        row = ContactRow(**data)

        assert row.full_name is None
        assert row.nickname is None
        assert row.contact_phone is None
        assert row.contact_email is None
        assert row.position is None

    def test_field_count(self) -> None:
        """Verify ContactRow has 21 fields (12 base + 9 Contact)."""
        fields = ContactRow.model_fields
        assert len(fields) == 21

    def test_inherits_from_task_row(self) -> None:
        """Test that ContactRow inherits from TaskRow."""
        assert issubclass(ContactRow, TaskRow)


# ---------------------------------------------------------------------------
# Edge Cases and Special Values
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and special values."""

    def test_empty_string_name(self, base_task_data: dict[str, Any]) -> None:
        """Test empty string name is valid."""
        data = {**base_task_data, "name": ""}
        row = TaskRow(**data)
        assert row.name == ""

    def test_empty_tags_list(self, base_task_data: dict[str, Any]) -> None:
        """Test empty tags list is valid."""
        data = {**base_task_data, "tags": []}
        row = TaskRow(**data)
        assert row.tags == []

    def test_large_gid(self, base_task_data: dict[str, Any]) -> None:
        """Test large GID strings are handled."""
        large_gid = "1234567890123456789"
        data = {**base_task_data, "gid": large_gid}
        row = TaskRow(**data)
        assert row.gid == large_gid

    def test_unicode_in_strings(self, base_task_data: dict[str, Any]) -> None:
        """Test Unicode characters are preserved."""
        data = {
            **base_task_data,
            "name": "Task with unicode: cafe",
            "section": "Section",
        }
        row = TaskRow(**data)
        assert "cafe" in row.name
        assert "" in (row.section or "")

    def test_very_long_url(self, base_task_data: dict[str, Any]) -> None:
        """Test very long URL is handled."""
        long_url = "https://app.asana.com/0/" + "0" * 1000 + "/123"
        data = {**base_task_data, "url": long_url}
        row = TaskRow(**data)
        assert row.url == long_url


class TestDateTimeHandling:
    """Tests for datetime field handling."""

    def test_datetime_with_timezone(self, base_task_data: dict[str, Any]) -> None:
        """Test datetime fields with timezone."""
        dt = datetime(2024, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
        data = {**base_task_data, "created": dt}
        row = TaskRow(**data)
        assert row.created == dt

    def test_date_field_accepts_date(self, base_task_data: dict[str, Any]) -> None:
        """Test date fields accept date objects."""
        d = date(2024, 12, 15)
        data = {**base_task_data, "date": d, "due_on": d}
        row = TaskRow(**data)
        assert row.date == d
        assert row.due_on == d

    def test_completed_at_can_be_none(self, base_task_data: dict[str, Any]) -> None:
        """Test completed_at can be None."""
        row = TaskRow(**base_task_data)
        assert row.completed_at is None


class TestModelDumpCompatibility:
    """Tests for Pydantic model_dump compatibility."""

    def test_model_dump_equals_to_dict_for_base_row(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test model_dump and to_dict produce equivalent results for base row."""
        row = TaskRow(**base_task_data)
        dump = row.model_dump()
        to_dict = row.to_dict()

        # All keys should match
        assert set(dump.keys()) == set(to_dict.keys())

    def test_to_dict_handles_nested_decimal_in_subclass(
        self, base_task_data: dict[str, Any]
    ) -> None:
        """Test to_dict converts nested Decimal values."""
        data = {
            **base_task_data,
            "type": "Unit",
            "mrr": Decimal("100.50"),
            "discount": Decimal("5.25"),
        }
        row = UnitRow(**data)
        result = row.to_dict()

        # Both Decimal fields should be converted
        assert isinstance(result["mrr"], float)
        assert isinstance(result["discount"], float)
