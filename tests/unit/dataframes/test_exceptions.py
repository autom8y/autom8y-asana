"""Tests for dataframe exception hierarchy.

Verifies exception inheritance, error message formatting,
context dict population, and value truncation for PII safety.
"""

from __future__ import annotations

import pytest

from autom8_asana.dataframes.exceptions import (
    DataFrameError,
    ExtractionError,
    SchemaNotFoundError,
    SchemaVersionError,
    TypeCoercionError,
)


class TestDataFrameError:
    """Tests for base DataFrameError."""

    def test_basic_creation(self) -> None:
        """Test basic exception creation."""
        error = DataFrameError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.context == {}

    def test_creation_with_context(self) -> None:
        """Test exception creation with context dict."""
        error = DataFrameError(
            "Operation failed",
            context={"task_gid": "123", "field": "name"},
        )
        assert error.message == "Operation failed"
        assert error.context == {"task_gid": "123", "field": "name"}

    def test_is_exception(self) -> None:
        """Verify DataFrameError inherits from Exception."""
        error = DataFrameError("test")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """Verify exception can be raised and caught."""
        with pytest.raises(DataFrameError) as exc_info:
            raise DataFrameError("test error")
        assert "test error" in str(exc_info.value)


class TestSchemaNotFoundError:
    """Tests for SchemaNotFoundError."""

    def test_creation(self) -> None:
        """Test exception creation with task type."""
        error = SchemaNotFoundError("CustomTask")
        assert error.task_type == "CustomTask"
        assert "CustomTask" in error.message
        assert "No schema registered" in error.message

    def test_inherits_from_dataframe_error(self) -> None:
        """Verify inheritance from DataFrameError."""
        error = SchemaNotFoundError("Unit")
        assert isinstance(error, DataFrameError)
        assert isinstance(error, Exception)

    def test_context_populated(self) -> None:
        """Verify context dict is populated."""
        error = SchemaNotFoundError("Contact")
        assert error.context == {"task_type": "Contact"}

    def test_message_formatting(self) -> None:
        """Test error message format."""
        error = SchemaNotFoundError("MyType")
        assert error.message == "No schema registered for task type: MyType"


class TestExtractionError:
    """Tests for ExtractionError."""

    def test_creation(self) -> None:
        """Test exception creation with all parameters."""
        original = ValueError("Invalid value")
        error = ExtractionError("task123", "mrr", original)

        assert error.task_gid == "task123"
        assert error.field_name == "mrr"
        assert error.original_error is original

    def test_message_includes_all_info(self) -> None:
        """Verify message includes task GID, field name, and original error."""
        original = TypeError("Expected int")
        error = ExtractionError("gid456", "weekly_ad_spend", original)

        assert "gid456" in error.message
        assert "weekly_ad_spend" in error.message
        assert "Expected int" in error.message

    def test_inherits_from_dataframe_error(self) -> None:
        """Verify inheritance from DataFrameError."""
        error = ExtractionError("gid", "field", ValueError())
        assert isinstance(error, DataFrameError)

    def test_context_populated(self) -> None:
        """Verify context dict is populated correctly."""
        original = KeyError("missing")
        error = ExtractionError("task999", "products", original)

        assert error.context["task_gid"] == "task999"
        assert error.context["field_name"] == "products"
        assert error.context["error_type"] == "KeyError"


class TestTypeCoercionError:
    """Tests for TypeCoercionError."""

    def test_creation(self) -> None:
        """Test exception creation with all parameters."""
        error = TypeCoercionError("mrr", "Decimal", "not_a_number")

        assert error.field_name == "mrr"
        assert error.expected_type == "Decimal"
        assert error.actual_value == "not_a_number"

    def test_message_formatting(self) -> None:
        """Verify message format includes expected and actual types."""
        error = TypeCoercionError("amount", "Float64", 123)

        assert "amount" in error.message
        assert "Float64" in error.message
        assert "int" in error.message  # actual type

    def test_inherits_from_dataframe_error(self) -> None:
        """Verify inheritance from DataFrameError."""
        error = TypeCoercionError("field", "type", "value")
        assert isinstance(error, DataFrameError)

    def test_context_populated(self) -> None:
        """Verify context dict is populated."""
        error = TypeCoercionError("count", "Int64", "abc")

        assert error.context["field_name"] == "count"
        assert error.context["expected_type"] == "Int64"
        assert error.context["actual_type"] == "str"

    def test_value_truncation_for_pii_safety(self) -> None:
        """Verify long values are truncated in message (PII safety)."""
        # Value longer than 50 chars should be truncated
        long_value = "A" * 100
        error = TypeCoercionError("email", "Utf8", long_value)

        # Original value is preserved in attribute
        assert error.actual_value == long_value
        # But message should not contain the full value
        assert long_value not in error.message

    def test_short_value_not_truncated(self) -> None:
        """Verify short values are not truncated."""
        short_value = "abc"
        error = TypeCoercionError("name", "Utf8", short_value)
        assert error.actual_value == short_value


class TestSchemaVersionError:
    """Tests for SchemaVersionError."""

    def test_creation(self) -> None:
        """Test exception creation with all parameters."""
        error = SchemaVersionError("unit", "1.0.0", "2.0.0")

        assert error.schema_name == "unit"
        assert error.expected_version == "1.0.0"
        assert error.actual_version == "2.0.0"

    def test_message_formatting(self) -> None:
        """Verify message includes schema name and both versions."""
        error = SchemaVersionError("contact", "1.0.0", "1.1.0")

        assert "contact" in error.message
        assert "1.0.0" in error.message
        assert "1.1.0" in error.message
        assert "mismatch" in error.message

    def test_inherits_from_dataframe_error(self) -> None:
        """Verify inheritance from DataFrameError."""
        error = SchemaVersionError("base", "1.0.0", "2.0.0")
        assert isinstance(error, DataFrameError)

    def test_context_populated(self) -> None:
        """Verify context dict is populated."""
        error = SchemaVersionError("unit", "1.0.0", "1.2.0")

        assert error.context["schema_name"] == "unit"
        assert error.context["expected_version"] == "1.0.0"
        assert error.context["actual_version"] == "1.2.0"


class TestExceptionHierarchy:
    """Tests for exception hierarchy structure."""

    def test_all_exceptions_inherit_from_dataframe_error(self) -> None:
        """All custom exceptions should inherit from DataFrameError."""
        assert issubclass(SchemaNotFoundError, DataFrameError)
        assert issubclass(ExtractionError, DataFrameError)
        assert issubclass(TypeCoercionError, DataFrameError)
        assert issubclass(SchemaVersionError, DataFrameError)

    def test_catch_all_with_base_class(self) -> None:
        """Can catch all dataframe exceptions with base class."""
        exceptions = [
            SchemaNotFoundError("Type"),
            ExtractionError("gid", "field", ValueError()),
            TypeCoercionError("field", "type", "value"),
            SchemaVersionError("schema", "1.0", "2.0"),
        ]

        for exc in exceptions:
            with pytest.raises(DataFrameError):
                raise exc

    def test_exceptions_can_be_caught_specifically(self) -> None:
        """Each exception can be caught by its specific type."""
        with pytest.raises(SchemaNotFoundError):
            raise SchemaNotFoundError("Type")

        with pytest.raises(ExtractionError):
            raise ExtractionError("gid", "field", ValueError())

        with pytest.raises(TypeCoercionError):
            raise TypeCoercionError("field", "type", "value")

        with pytest.raises(SchemaVersionError):
            raise SchemaVersionError("schema", "1.0", "2.0")
