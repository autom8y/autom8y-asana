"""Tests for BASE_SCHEMA definition.

Verifies the base schema has exactly 12 columns with correct
names, types, and nullability.
"""

from __future__ import annotations

import polars as pl

from autom8_asana.dataframes.schemas.base import BASE_COLUMNS, BASE_SCHEMA


class TestBaseSchemaStructure:
    """Tests for BASE_SCHEMA structure."""

    def test_schema_name(self) -> None:
        """Verify schema name is 'base'."""
        assert BASE_SCHEMA.name == "base"

    def test_task_type_is_wildcard(self) -> None:
        """Verify task_type is '*' (applies to all)."""
        assert BASE_SCHEMA.task_type == "*"

    def test_version_is_semver(self) -> None:
        """Verify version follows semver format."""
        assert BASE_SCHEMA.version == "1.0.0"

    def test_column_count_is_12(self) -> None:
        """Verify BASE_SCHEMA has exactly 12 columns."""
        assert len(BASE_SCHEMA) == 12
        assert len(BASE_COLUMNS) == 12


class TestBaseSchemaColumns:
    """Tests for BASE_SCHEMA column definitions."""

    def test_column_names(self) -> None:
        """Verify all expected column names are present."""
        expected_names = [
            "gid",
            "name",
            "type",
            "date",
            "created",
            "due_on",
            "is_completed",
            "completed_at",
            "url",
            "last_modified",
            "section",
            "tags",
        ]
        assert BASE_SCHEMA.column_names() == expected_names

    def test_gid_column(self) -> None:
        """Verify gid column definition."""
        col = BASE_SCHEMA.get_column("gid")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is False
        assert col.source == "gid"

    def test_name_column(self) -> None:
        """Verify name column definition."""
        col = BASE_SCHEMA.get_column("name")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is False
        assert col.source == "name"

    def test_type_column(self) -> None:
        """Verify type column definition."""
        col = BASE_SCHEMA.get_column("type")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is False
        assert col.source is None  # Derived via _extract_type() with fallback logic

    def test_date_column(self) -> None:
        """Verify date column definition."""
        col = BASE_SCHEMA.get_column("date")
        assert col is not None
        assert col.dtype == "Date"
        assert col.nullable is True
        assert col.source is None  # Custom extraction

    def test_created_column(self) -> None:
        """Verify created column definition."""
        col = BASE_SCHEMA.get_column("created")
        assert col is not None
        assert col.dtype == "Datetime"
        assert col.nullable is False
        assert col.source == "created_at"

    def test_due_on_column(self) -> None:
        """Verify due_on column definition."""
        col = BASE_SCHEMA.get_column("due_on")
        assert col is not None
        assert col.dtype == "Date"
        assert col.nullable is True
        assert col.source == "due_on"

    def test_is_completed_column(self) -> None:
        """Verify is_completed column definition."""
        col = BASE_SCHEMA.get_column("is_completed")
        assert col is not None
        assert col.dtype == "Boolean"
        assert col.nullable is False
        assert col.source == "completed"

    def test_completed_at_column(self) -> None:
        """Verify completed_at column definition."""
        col = BASE_SCHEMA.get_column("completed_at")
        assert col is not None
        assert col.dtype == "Datetime"
        assert col.nullable is True
        assert col.source == "completed_at"

    def test_url_column(self) -> None:
        """Verify url column definition."""
        col = BASE_SCHEMA.get_column("url")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is False
        assert col.source is None  # Constructed from GID

    def test_last_modified_column(self) -> None:
        """Verify last_modified column definition."""
        col = BASE_SCHEMA.get_column("last_modified")
        assert col is not None
        assert col.dtype == "Datetime"
        assert col.nullable is False
        assert col.source == "modified_at"

    def test_section_column(self) -> None:
        """Verify section column definition."""
        col = BASE_SCHEMA.get_column("section")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True
        assert col.source is None  # Extracted from memberships

    def test_tags_column(self) -> None:
        """Verify tags column definition."""
        col = BASE_SCHEMA.get_column("tags")
        assert col is not None
        assert col.dtype == "List[Utf8]"
        assert col.nullable is False
        assert col.source == "tags"


class TestBaseSchemaPolarsConversion:
    """Tests for BASE_SCHEMA Polars schema conversion."""

    def test_to_polars_schema(self) -> None:
        """Verify to_polars_schema produces valid Polars types."""
        polars_schema = BASE_SCHEMA.to_polars_schema()

        assert polars_schema["gid"] == pl.Utf8
        assert polars_schema["name"] == pl.Utf8
        assert polars_schema["type"] == pl.Utf8
        assert polars_schema["date"] == pl.Date
        assert isinstance(polars_schema["created"], pl.Datetime)
        assert polars_schema["due_on"] == pl.Date
        assert polars_schema["is_completed"] == pl.Boolean
        assert isinstance(polars_schema["completed_at"], pl.Datetime)
        assert polars_schema["url"] == pl.Utf8
        assert isinstance(polars_schema["last_modified"], pl.Datetime)
        assert polars_schema["section"] == pl.Utf8
        assert isinstance(polars_schema["tags"], pl.List)

    def test_datetime_columns_have_utc_timezone(self) -> None:
        """Verify datetime columns use UTC timezone."""
        polars_schema = BASE_SCHEMA.to_polars_schema()

        for col_name in ["created", "completed_at", "last_modified"]:
            dtype = polars_schema[col_name]
            if isinstance(dtype, pl.Datetime):
                assert dtype.time_zone == "UTC"


class TestBaseSchemaToDict:
    """Tests for BASE_SCHEMA to_dict() serialization."""

    def test_to_dict_structure(self) -> None:
        """Verify to_dict produces expected structure."""
        result = BASE_SCHEMA.to_dict()

        assert result["name"] == "base"
        assert result["task_type"] == "*"
        assert result["version"] == "1.0.0"
        assert len(result["columns"]) == 12

    def test_to_dict_column_includes_description(self) -> None:
        """Verify column descriptions are included."""
        result = BASE_SCHEMA.to_dict()

        gid_col = result["columns"][0]
        assert gid_col["name"] == "gid"
        assert gid_col["description"] is not None
        assert "identifier" in gid_col["description"].lower()


class TestBaseSchemaValidation:
    """Tests for BASE_SCHEMA row validation."""

    def test_validate_valid_row(self) -> None:
        """Verify valid row passes validation."""
        row = {
            "gid": "123",
            "name": "Test",
            "type": "task",
            "date": None,
            "created": "2024-01-01T00:00:00Z",
            "due_on": None,
            "is_completed": False,
            "completed_at": None,
            "url": "https://app.asana.com/0/0/123",
            "last_modified": "2024-01-01T00:00:00Z",
            "section": None,
            "tags": [],
        }
        errors = BASE_SCHEMA.validate_row(row)
        assert errors == []

    def test_validate_row_missing_required(self) -> None:
        """Verify validation catches missing required fields."""
        row = {
            "gid": None,  # Required but null
            "name": "Test",
            "type": "task",
        }
        errors = BASE_SCHEMA.validate_row(row)
        assert len(errors) >= 1
        assert any("gid" in e for e in errors)
