"""Tests for ColumnDef and DataFrameSchema models.

Verifies column definition creation, immutability, dtype conversion,
and schema export capabilities.
"""

from __future__ import annotations

from typing import Any

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema


class TestColumnDef:
    """Tests for ColumnDef dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic column definition creation."""
        col = ColumnDef("gid", "Utf8")
        assert col.name == "gid"
        assert col.dtype == "Utf8"
        assert col.nullable is True  # Default
        assert col.source is None
        assert col.extractor is None
        assert col.description is None

    def test_creation_with_all_fields(self) -> None:
        """Test column definition with all fields."""
        extractor = lambda x: x.get("gid")  # noqa: E731
        col = ColumnDef(
            name="task_gid",
            dtype="Utf8",
            nullable=False,
            source="gid",
            extractor=extractor,
            description="Task identifier",
        )
        assert col.name == "task_gid"
        assert col.dtype == "Utf8"
        assert col.nullable is False
        assert col.source == "gid"
        assert col.extractor is extractor
        assert col.description == "Task identifier"

    def test_immutability(self) -> None:
        """Test that ColumnDef is frozen (immutable)."""
        col = ColumnDef("name", "Utf8")
        with pytest.raises(AttributeError):
            col.name = "different"  # type: ignore[misc]

    def test_hashable(self) -> None:
        """Test that ColumnDef is hashable (for use in sets/dicts)."""
        col1 = ColumnDef("gid", "Utf8")
        col2 = ColumnDef("gid", "Utf8")
        col3 = ColumnDef("name", "Utf8")

        # Can be added to set
        col_set = {col1, col2, col3}
        assert len(col_set) == 2  # col1 and col2 are equal

    def test_equality(self) -> None:
        """Test ColumnDef equality (extractor excluded from comparison)."""
        extractor1 = lambda x: x  # noqa: E731
        extractor2 = lambda x: x.get("gid")  # noqa: E731

        col1 = ColumnDef("gid", "Utf8", extractor=extractor1)
        col2 = ColumnDef("gid", "Utf8", extractor=extractor2)

        # Extractors are excluded from comparison
        assert col1 == col2


class TestColumnDefPolarsTypes:
    """Tests for ColumnDef.get_polars_dtype()."""

    @pytest.mark.parametrize(
        "dtype_str,expected_type",
        [
            ("Utf8", pl.Utf8),
            ("String", pl.Utf8),  # Alias
            ("Int64", pl.Int64),
            ("Int32", pl.Int32),
            ("Float64", pl.Float64),
            ("Boolean", pl.Boolean),
            ("Date", pl.Date),
        ],
    )
    def test_basic_dtypes(self, dtype_str: str, expected_type: pl.DataType) -> None:
        """Test basic dtype string to Polars type conversion."""
        col = ColumnDef("test", dtype_str)
        result = col.get_polars_dtype()
        assert result == expected_type

    def test_datetime_type(self) -> None:
        """Test Datetime type includes time unit and timezone."""
        col = ColumnDef("created", "Datetime")
        result = col.get_polars_dtype()
        assert isinstance(result, pl.Datetime)
        assert result.time_unit == "us"
        assert result.time_zone == "UTC"

    def test_list_utf8_type(self) -> None:
        """Test List[Utf8] type."""
        col = ColumnDef("tags", "List[Utf8]")
        result = col.get_polars_dtype()
        assert isinstance(result, pl.List)
        assert result.inner == pl.Utf8

    def test_list_string_alias(self) -> None:
        """Test List[String] alias for List[Utf8]."""
        col = ColumnDef("products", "List[String]")
        result = col.get_polars_dtype()
        assert isinstance(result, pl.List)
        assert result.inner == pl.Utf8

    def test_decimal_type(self) -> None:
        """Test Decimal type maps to Float64 for monetary values.

        Note: Polars Decimal requires precision/scale, so we use Float64
        which handles most use cases well.
        """
        col = ColumnDef("mrr", "Decimal")
        result = col.get_polars_dtype()
        assert result == pl.Float64

    def test_unknown_dtype_raises_error(self) -> None:
        """Test that unknown dtype raises ValueError."""
        col = ColumnDef("unknown", "UnknownType")
        with pytest.raises(ValueError, match="Unknown Polars dtype"):
            col.get_polars_dtype()


class TestDataFrameSchema:
    """Tests for DataFrameSchema dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic schema creation."""
        columns = [
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8"),
        ]
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=columns,
        )
        assert schema.name == "test"
        assert schema.task_type == "*"
        assert len(schema.columns) == 2
        assert schema.version == "1.0.0"  # Default

    def test_custom_version(self) -> None:
        """Test schema with custom version."""
        schema = DataFrameSchema(
            name="test",
            task_type="Unit",
            columns=[ColumnDef("gid", "Utf8")],
            version="2.1.0",
        )
        assert schema.version == "2.1.0"

    def test_len(self) -> None:
        """Test __len__ returns column count."""
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef("a", "Utf8"),
                ColumnDef("b", "Utf8"),
                ColumnDef("c", "Int64"),
            ],
        )
        assert len(schema) == 3


class TestDataFrameSchemaColumnAccess:
    """Tests for DataFrameSchema column access methods."""

    @pytest.fixture
    def sample_schema(self) -> DataFrameSchema:
        """Create sample schema for testing."""
        return DataFrameSchema(
            name="sample",
            task_type="*",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False, source="gid"),
                ColumnDef("name", "Utf8", source="name"),
                ColumnDef("count", "Int64", source="num_items"),
            ],
        )

    def test_get_column_found(self, sample_schema: DataFrameSchema) -> None:
        """Test get_column returns column when found."""
        col = sample_schema.get_column("gid")
        assert col is not None
        assert col.name == "gid"
        assert col.dtype == "Utf8"

    def test_get_column_not_found(self, sample_schema: DataFrameSchema) -> None:
        """Test get_column returns None when not found."""
        col = sample_schema.get_column("nonexistent")
        assert col is None

    def test_column_names(self, sample_schema: DataFrameSchema) -> None:
        """Test column_names returns ordered list."""
        names = sample_schema.column_names()
        assert names == ["gid", "name", "count"]

    def test_column_names_preserves_order(self) -> None:
        """Test column_names preserves insertion order."""
        schema = DataFrameSchema(
            name="ordered",
            task_type="*",
            columns=[
                ColumnDef("z", "Utf8"),
                ColumnDef("a", "Utf8"),
                ColumnDef("m", "Utf8"),
            ],
        )
        assert schema.column_names() == ["z", "a", "m"]


class TestDataFrameSchemaPolarsConversion:
    """Tests for DataFrameSchema.to_polars_schema()."""

    def test_to_polars_schema(self) -> None:
        """Test conversion to Polars schema dict."""
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef("gid", "Utf8"),
                ColumnDef("count", "Int64"),
                ColumnDef("active", "Boolean"),
            ],
        )
        polars_schema = schema.to_polars_schema()

        assert isinstance(polars_schema, dict)
        assert polars_schema["gid"] == pl.Utf8
        assert polars_schema["count"] == pl.Int64
        assert polars_schema["active"] == pl.Boolean

    def test_to_polars_schema_with_complex_types(self) -> None:
        """Test conversion with complex types (Datetime, List)."""
        schema = DataFrameSchema(
            name="complex",
            task_type="*",
            columns=[
                ColumnDef("created", "Datetime"),
                ColumnDef("tags", "List[Utf8]"),
            ],
        )
        polars_schema = schema.to_polars_schema()

        assert isinstance(polars_schema["created"], pl.Datetime)
        assert isinstance(polars_schema["tags"], pl.List)


class TestDataFrameSchemaToDict:
    """Tests for DataFrameSchema.to_dict() serialization."""

    def test_to_dict_basic(self) -> None:
        """Test basic to_dict output."""
        schema = DataFrameSchema(
            name="base",
            task_type="*",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False, source="gid"),
            ],
            version="1.0.0",
        )
        result = schema.to_dict()

        assert result["name"] == "base"
        assert result["task_type"] == "*"
        assert result["version"] == "1.0.0"
        assert len(result["columns"]) == 1

    def test_to_dict_column_structure(self) -> None:
        """Test column structure in to_dict output."""
        schema = DataFrameSchema(
            name="test",
            task_type="Unit",
            columns=[
                ColumnDef(
                    "mrr",
                    "Decimal",
                    nullable=True,
                    source="cf_12345",
                    description="Monthly revenue",
                ),
            ],
        )
        result = schema.to_dict()
        col = result["columns"][0]

        assert col["name"] == "mrr"
        assert col["dtype"] == "Decimal"
        assert col["nullable"] is True
        assert col["source"] == "cf_12345"
        assert col["description"] == "Monthly revenue"

    def test_to_dict_excludes_extractor(self) -> None:
        """Test that extractor function is not serialized."""
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef(
                    "gid",
                    "Utf8",
                    extractor=lambda x: x.get("gid"),
                ),
            ],
        )
        result = schema.to_dict()

        # extractor should not be in output
        assert "extractor" not in result["columns"][0]

    def test_to_dict_is_json_serializable(self) -> None:
        """Test that to_dict output is JSON serializable."""
        import json

        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("date", "Date", nullable=True),
            ],
        )
        result = schema.to_dict()

        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Roundtrip should work
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"


class TestDataFrameSchemaValidation:
    """Tests for DataFrameSchema.validate_row()."""

    @pytest.fixture
    def validation_schema(self) -> DataFrameSchema:
        """Create schema for validation testing."""
        return DataFrameSchema(
            name="validation_test",
            task_type="*",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=False),
                ColumnDef("description", "Utf8", nullable=True),
            ],
        )

    def test_validate_row_valid(self, validation_schema: DataFrameSchema) -> None:
        """Test validation with valid row."""
        row: dict[str, Any] = {
            "gid": "123",
            "name": "Test",
            "description": "A test task",
        }
        errors = validation_schema.validate_row(row)
        assert errors == []

    def test_validate_row_valid_with_none_nullable(
        self, validation_schema: DataFrameSchema
    ) -> None:
        """Test validation with None for nullable field."""
        row: dict[str, Any] = {
            "gid": "123",
            "name": "Test",
            "description": None,  # nullable=True
        }
        errors = validation_schema.validate_row(row)
        assert errors == []

    def test_validate_row_missing_required(
        self, validation_schema: DataFrameSchema
    ) -> None:
        """Test validation with missing required field."""
        row: dict[str, Any] = {
            "gid": "123",
            "description": "A test",
            # name is missing
        }
        errors = validation_schema.validate_row(row)
        assert len(errors) == 1
        assert "name" in errors[0]
        assert "null" in errors[0]

    def test_validate_row_null_required(
        self, validation_schema: DataFrameSchema
    ) -> None:
        """Test validation with None for required field."""
        row: dict[str, Any] = {
            "gid": None,  # nullable=False
            "name": "Test",
        }
        errors = validation_schema.validate_row(row)
        assert len(errors) == 1
        assert "gid" in errors[0]

    def test_validate_row_multiple_errors(
        self, validation_schema: DataFrameSchema
    ) -> None:
        """Test validation with multiple errors."""
        row: dict[str, Any] = {
            "gid": None,  # required but null
            "name": None,  # required but null
        }
        errors = validation_schema.validate_row(row)
        assert len(errors) == 2
