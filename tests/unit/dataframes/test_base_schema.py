"""Tests for BASE_SCHEMA definition.

Verifies the base schema has exactly 13 columns with correct
names, types, and nullability.
"""

from __future__ import annotations

import polars as pl
import pytest

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
        parts = BASE_SCHEMA.version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_column_count_is_13(self) -> None:
        """Verify BASE_SCHEMA has exactly 13 columns."""
        assert len(BASE_SCHEMA) == 13
        assert len(BASE_COLUMNS) == 13


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
            "parent_gid",
        ]
        assert BASE_SCHEMA.column_names() == expected_names

    @pytest.mark.parametrize(
        "column_name,expected_dtype,expected_nullable,expected_source",
        [
            pytest.param("gid", "Utf8", False, "gid", id="gid"),
            pytest.param("name", "Utf8", False, "name", id="name"),
            pytest.param("type", "Utf8", False, None, id="type"),
            pytest.param("date", "Date", True, None, id="date"),
            pytest.param("created", "Datetime", False, "created_at", id="created"),
            pytest.param("due_on", "Date", True, "due_on", id="due_on"),
            pytest.param("is_completed", "Boolean", False, "completed", id="is_completed"),
            pytest.param("completed_at", "Datetime", True, "completed_at", id="completed_at"),
            pytest.param("url", "Utf8", False, None, id="url"),
            pytest.param("last_modified", "Datetime", False, "modified_at", id="last_modified"),
            pytest.param("section", "Utf8", True, None, id="section"),
            pytest.param("tags", "List[Utf8]", False, "tags", id="tags"),
            pytest.param("parent_gid", "Utf8", True, None, id="parent_gid"),
        ],
    )
    def test_column_definition(
        self,
        column_name: str,
        expected_dtype: str,
        expected_nullable: bool,
        expected_source: str | None,
    ) -> None:
        """Verify column exists with correct dtype, nullability, and source."""
        col = BASE_SCHEMA.get_column(column_name)
        assert col is not None
        assert col.dtype == expected_dtype
        assert col.nullable is expected_nullable
        assert col.source == expected_source


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
        assert polars_schema["parent_gid"] == pl.Utf8

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
        assert result["version"] == BASE_SCHEMA.version
        assert len(result["columns"]) == 13

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
            "parent_gid": None,
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
