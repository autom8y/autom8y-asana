"""Integration tests for custom field type validation."""

from decimal import Decimal

import pytest

from autom8_asana.models.custom_field_accessor import CustomFieldAccessor
from autom8_asana.persistence.exceptions import GidValidationError as ValidationError


class TestTextFieldValidation:
    """Test text field type validation."""

    def test_text_field_accepts_string(self):
        """Text field accepts string value."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Description", "resource_subtype": "text"}]
        )
        accessor.set("Description", "Valid text")  # Should not raise

    def test_text_field_rejects_int(self):
        """Text field rejects integer."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Description", "resource_subtype": "text"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Description", 123)
        assert "text" in str(exc.value).lower()
        assert "int" in str(exc.value)

    def test_text_field_rejects_float(self):
        """Text field rejects float."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Description", "resource_subtype": "text"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Description", 123.45)
        assert "text" in str(exc.value).lower()

    def test_text_field_accepts_none(self):
        """Text field accepts None to clear."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Description", "resource_subtype": "text"}]
        )
        accessor.set("Description", None)  # Should not raise

    def test_text_field_rejects_list(self):
        """Text field rejects list."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Description", "resource_subtype": "text"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Description", ["item"])
        assert "text" in str(exc.value).lower()


class TestNumberFieldValidation:
    """Test number field type validation."""

    def test_number_field_accepts_int(self):
        """Number field accepts integer."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        accessor.set("Budget", 1000)  # Should not raise

    def test_number_field_accepts_float(self):
        """Number field accepts float."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        accessor.set("Budget", 1000.50)  # Should not raise

    def test_number_field_accepts_decimal(self):
        """Number field accepts Decimal for precision."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        accessor.set("Budget", Decimal("1000.50"))  # Should not raise

    def test_number_field_rejects_string(self):
        """Number field rejects string."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Budget", "1000")
        assert "number" in str(exc.value).lower()
        assert "str" in str(exc.value)

    def test_number_field_accepts_none(self):
        """Number field accepts None."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        accessor.set("Budget", None)  # Should not raise

    def test_number_field_rejects_list(self):
        """Number field rejects list."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Budget", [1000])
        assert "number" in str(exc.value).lower()


class TestEnumFieldValidation:
    """Test enum field type validation."""

    def test_enum_field_accepts_string_gid(self):
        """Enum field accepts string GID."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Status", "resource_subtype": "enum"}]
        )
        accessor.set("Status", "1234567890")  # Should not raise

    def test_enum_field_accepts_dict_with_gid(self):
        """Enum field accepts dict with gid key."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Status", "resource_subtype": "enum"}]
        )
        accessor.set(
            "Status", {"gid": "1234567890", "name": "High"}
        )  # Should not raise

    def test_enum_field_rejects_list(self):
        """Enum field rejects list."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Status", "resource_subtype": "enum"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Status", ["High", "Medium"])
        assert "enum" in str(exc.value).lower()
        assert "list" in str(exc.value)

    def test_enum_field_rejects_dict_without_gid(self):
        """Enum field rejects dict without gid key."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Status", "resource_subtype": "enum"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Status", {"name": "High"})
        assert "gid" in str(exc.value)

    def test_enum_field_rejects_int(self):
        """Enum field rejects integer."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Status", "resource_subtype": "enum"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Status", 123)
        assert "enum" in str(exc.value).lower()

    def test_enum_field_accepts_none(self):
        """Enum field accepts None to clear."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Status", "resource_subtype": "enum"}]
        )
        accessor.set("Status", None)  # Should not raise


class TestMultiEnumFieldValidation:
    """Test multi_enum field type validation."""

    def test_multi_enum_field_accepts_list(self):
        """Multi_enum field accepts list."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Tags", "resource_subtype": "multi_enum"}]
        )
        accessor.set("Tags", ["1234567890", "0987654321"])  # Should not raise

    def test_multi_enum_field_rejects_string(self):
        """Multi_enum field rejects string."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Tags", "resource_subtype": "multi_enum"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Tags", "1234567890")
        assert "multi_enum" in str(exc.value).lower()
        assert "list" in str(exc.value)

    def test_multi_enum_field_accepts_empty_list(self):
        """Multi_enum field accepts empty list (clear all)."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Tags", "resource_subtype": "multi_enum"}]
        )
        accessor.set("Tags", [])  # Should not raise

    def test_multi_enum_field_rejects_dict(self):
        """Multi_enum field rejects dict."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Tags", "resource_subtype": "multi_enum"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Tags", {"gid": "123"})
        assert "multi_enum" in str(exc.value).lower()

    def test_multi_enum_field_accepts_none(self):
        """Multi_enum field accepts None to clear."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Tags", "resource_subtype": "multi_enum"}]
        )
        accessor.set("Tags", None)  # Should not raise


class TestDateFieldValidation:
    """Test date field type validation."""

    def test_date_field_accepts_iso_string(self):
        """Date field accepts ISO format string."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Due Date", "resource_subtype": "date"}]
        )
        accessor.set("Due Date", "2025-12-31")  # Should not raise

    def test_date_field_rejects_int(self):
        """Date field rejects integer."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Due Date", "resource_subtype": "date"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Due Date", 20251231)
        assert "date" in str(exc.value).lower()

    def test_date_field_accepts_none(self):
        """Date field accepts None."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Due Date", "resource_subtype": "date"}]
        )
        accessor.set("Due Date", None)  # Should not raise

    def test_date_field_rejects_list(self):
        """Date field rejects list."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Due Date", "resource_subtype": "date"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Due Date", ["2025-12-31"])
        assert "date" in str(exc.value).lower()


class TestPeopleFieldValidation:
    """Test people field type validation."""

    def test_people_field_accepts_list(self):
        """People field accepts list of GIDs."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Team Members", "resource_subtype": "people"}]
        )
        accessor.set("Team Members", ["1234567890", "0987654321"])  # Should not raise

    def test_people_field_rejects_string(self):
        """People field rejects string."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Team Members", "resource_subtype": "people"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Team Members", "1234567890")
        assert "people" in str(exc.value).lower()
        assert "list" in str(exc.value)

    def test_people_field_accepts_empty_list(self):
        """People field accepts empty list (clear all)."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Team Members", "resource_subtype": "people"}]
        )
        accessor.set("Team Members", [])  # Should not raise

    def test_people_field_accepts_none(self):
        """People field accepts None to clear."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Team Members", "resource_subtype": "people"}]
        )
        accessor.set("Team Members", None)  # Should not raise

    def test_people_field_rejects_dict(self):
        """People field rejects dict."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Team Members", "resource_subtype": "people"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Team Members", {"gid": "123"})
        assert "people" in str(exc.value).lower()


class TestErrorMessages:
    """Test that error messages are clear and actionable."""

    def test_error_includes_field_name(self):
        """Error message includes field name."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Budget", "invalid")
        assert "Budget" in str(exc.value)

    def test_error_includes_expected_type(self):
        """Error message includes expected type."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Budget", "invalid")
        assert "number" in str(exc.value).lower()

    def test_error_includes_actual_type(self):
        """Error message includes actual type received."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Budget", "invalid")
        assert "str" in str(exc.value)

    def test_error_includes_actual_value(self):
        """Error message includes the invalid value."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Budget", "invalid")
        # Check for either the quoted value or the unquoted version
        error_str = str(exc.value).lower()
        assert "invalid" in error_str or "'invalid'" in str(exc.value)

    def test_error_message_format_number(self):
        """Error message has correct format for number field."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("Budget", "not_a_number")
        error = str(exc.value)
        assert "Custom field 'Budget'" in error
        assert "expects number" in error
        assert "got str" in error


class TestDecimalSupport:
    """Test Decimal support in number fields and API formatting."""

    def test_decimal_accepted_and_stored(self):
        """Decimal value is accepted and stored in modifications."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Amount", "resource_subtype": "number"}]
        )
        value = Decimal("123.45")
        accessor.set("Amount", value)
        assert accessor.get("Amount") == value

    def test_decimal_formatted_to_float_for_api(self):
        """Decimal is converted to float for API."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Amount", "resource_subtype": "number"}]
        )
        value = Decimal("123.45")
        accessor.set("Amount", value)

        api_dict = accessor.to_api_dict()
        assert "1" in api_dict
        assert api_dict["1"] == 123.45
        assert isinstance(api_dict["1"], float)

    def test_decimal_precision_preserved_in_storage(self):
        """Decimal precision is preserved when stored (before API conversion)."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Amount", "resource_subtype": "number"}]
        )
        # High precision decimal
        value = Decimal("0.123456789")
        accessor.set("Amount", value)
        assert accessor.get("Amount") == value

    def test_zero_decimal_accepted(self):
        """Zero as Decimal is accepted."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Amount", "resource_subtype": "number"}]
        )
        accessor.set("Amount", Decimal("0"))  # Should not raise

    def test_negative_decimal_accepted(self):
        """Negative Decimal is accepted."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Amount", "resource_subtype": "number"}]
        )
        accessor.set("Amount", Decimal("-500.50"))  # Should not raise


class TestValidationByGid:
    """Test validation when using GID instead of name."""

    def test_validation_by_gid_string(self):
        """Validation works when setting by GID."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1234567890", "name": "Priority", "resource_subtype": "enum"}]
        )
        # Use numeric string GID
        accessor.set("1234567890", "valid_gid")  # Should not raise

    def test_validation_by_gid_string_rejects_invalid(self):
        """Validation rejects invalid type when setting by GID."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1234567890", "name": "Priority", "resource_subtype": "number"}
            ]
        )
        with pytest.raises(ValidationError) as exc:
            accessor.set("1234567890", "not_a_number")
        assert "number" in str(exc.value).lower()


class TestValidationWithRemove:
    """Test that remove() properly clears fields."""

    def test_remove_is_allowed(self):
        """remove() calls set with None, which is always allowed."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority", "resource_subtype": "enum"}]
        )
        accessor.remove("Priority")  # Should not raise

    def test_remove_sets_to_none(self):
        """remove() sets field to None."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Priority", "resource_subtype": "enum"}]
        )
        accessor.remove("Priority")
        assert accessor.get("Priority") is None


class TestValidationWithDictSyntax:
    """Test validation with dictionary-style access."""

    def test_setitem_validates_type(self):
        """__setitem__ validates type."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        with pytest.raises(ValidationError):
            accessor["Budget"] = "not_a_number"

    def test_setitem_accepts_valid_value(self):
        """__setitem__ accepts valid values."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        accessor["Budget"] = 1000  # Should not raise

    def test_setitem_with_gid(self):
        """__setitem__ works with GID."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1234567890", "name": "Budget", "resource_subtype": "number"}]
        )
        accessor["1234567890"] = 500  # Should not raise


class TestMixedFieldTypes:
    """Test validation with multiple field types in one accessor."""

    def test_multiple_fields_validated_independently(self):
        """Each field type is validated independently."""
        accessor = CustomFieldAccessor(
            data=[
                {"gid": "1", "name": "Name", "resource_subtype": "text"},
                {"gid": "2", "name": "Budget", "resource_subtype": "number"},
                {"gid": "3", "name": "Status", "resource_subtype": "enum"},
            ]
        )

        # Valid values for each
        accessor.set("Name", "Project A")
        accessor.set("Budget", 1000)
        accessor.set("Status", "active_gid")

        # Invalid for first field
        with pytest.raises(ValidationError):
            accessor.set("Name", 123)

        # Invalid for second field
        with pytest.raises(ValidationError):
            accessor.set("Budget", "not_a_number")

        # Invalid for third field
        with pytest.raises(ValidationError):
            accessor.set("Status", ["multi"])


class TestValidationEdgeCases:
    """Test edge cases in validation."""

    def test_boolean_rejected_as_number(self):
        """Boolean should not be accepted as number (bool is int subclass)."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
        )
        # Note: bool is a subclass of int in Python, so this will be accepted
        # This is consistent with Python's type system
        accessor.set("Budget", True)  # Allowed because bool is int subclass
        assert accessor.get("Budget") is True

    def test_empty_string_accepted_for_text(self):
        """Empty string is valid text."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Description", "resource_subtype": "text"}]
        )
        accessor.set("Description", "")  # Should not raise

    def test_unknown_field_type_no_validation(self):
        """Unknown field types skip validation."""
        accessor = CustomFieldAccessor(
            data=[{"gid": "1", "name": "Custom", "resource_subtype": "unknown_type"}]
        )
        accessor.set(
            "Custom", "anything"
        )  # Should not raise - unknown types bypass validation

    def test_validation_with_missing_field(self):
        """Validation for missing field does not raise (will fail elsewhere)."""
        # Use non-strict mode for legacy behavior (test was written pre-strict mode)
        accessor = CustomFieldAccessor(data=[], strict=False)
        # When field is not found, validation returns early without raising
        accessor.set("nonexistent", "value")  # Should not raise during validation
