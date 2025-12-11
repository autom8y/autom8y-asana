"""Tests for CONTACT_SCHEMA definition.

Verifies the Contact schema has exactly 21 columns (12 base + 9 Contact-specific)
with correct names, types, and nullability.
"""

from __future__ import annotations

import polars as pl

from autom8_asana.dataframes.schemas.base import BASE_COLUMNS
from autom8_asana.dataframes.schemas.contact import CONTACT_COLUMNS, CONTACT_SCHEMA


class TestContactSchemaStructure:
    """Tests for CONTACT_SCHEMA structure."""

    def test_schema_name(self) -> None:
        """Verify schema name is 'contact'."""
        assert CONTACT_SCHEMA.name == "contact"

    def test_task_type_is_contact(self) -> None:
        """Verify task_type is 'Contact'."""
        assert CONTACT_SCHEMA.task_type == "Contact"

    def test_version_is_semver(self) -> None:
        """Verify version follows semver format."""
        assert CONTACT_SCHEMA.version == "1.0.0"

    def test_column_count_is_21(self) -> None:
        """Verify CONTACT_SCHEMA has exactly 21 columns (12 base + 9 Contact)."""
        assert len(CONTACT_SCHEMA) == 21
        assert len(BASE_COLUMNS) == 12
        assert len(CONTACT_COLUMNS) == 9

    def test_includes_all_base_columns(self) -> None:
        """Verify all base columns are present at the start."""
        base_names = [col.name for col in BASE_COLUMNS]
        contact_names = CONTACT_SCHEMA.column_names()[:12]
        assert contact_names == base_names


class TestContactSchemaColumns:
    """Tests for CONTACT_SCHEMA column definitions."""

    def test_contact_specific_column_names(self) -> None:
        """Verify all Contact-specific column names are present."""
        expected_contact_columns = [
            "full_name",
            "nickname",
            "contact_phone",
            "contact_email",
            "position",
            "employee_id",
            "contact_url",
            "time_zone",
            "city",
        ]
        # Contact columns come after base columns
        contact_names = CONTACT_SCHEMA.column_names()[12:]
        assert contact_names == expected_contact_columns

    def test_full_name_column(self) -> None:
        """Verify full_name column definition."""
        col = CONTACT_SCHEMA.get_column("full_name")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_nickname_column(self) -> None:
        """Verify nickname column definition."""
        col = CONTACT_SCHEMA.get_column("nickname")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_contact_phone_column(self) -> None:
        """Verify contact_phone column definition."""
        col = CONTACT_SCHEMA.get_column("contact_phone")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_contact_email_column(self) -> None:
        """Verify contact_email column definition."""
        col = CONTACT_SCHEMA.get_column("contact_email")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_position_column(self) -> None:
        """Verify position column definition."""
        col = CONTACT_SCHEMA.get_column("position")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_employee_id_column(self) -> None:
        """Verify employee_id column definition."""
        col = CONTACT_SCHEMA.get_column("employee_id")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_contact_url_column(self) -> None:
        """Verify contact_url column definition."""
        col = CONTACT_SCHEMA.get_column("contact_url")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_time_zone_column(self) -> None:
        """Verify time_zone column definition."""
        col = CONTACT_SCHEMA.get_column("time_zone")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_city_column(self) -> None:
        """Verify city column definition."""
        col = CONTACT_SCHEMA.get_column("city")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True


class TestContactSchemaPolarsConversion:
    """Tests for CONTACT_SCHEMA Polars schema conversion."""

    def test_to_polars_schema(self) -> None:
        """Verify to_polars_schema produces valid Polars types."""
        polars_schema = CONTACT_SCHEMA.to_polars_schema()

        # Check base columns (inherited)
        assert polars_schema["gid"] == pl.Utf8
        assert polars_schema["name"] == pl.Utf8

        # Check Contact-specific columns
        assert polars_schema["full_name"] == pl.Utf8
        assert polars_schema["nickname"] == pl.Utf8
        assert polars_schema["contact_phone"] == pl.Utf8
        assert polars_schema["contact_email"] == pl.Utf8
        assert polars_schema["position"] == pl.Utf8
        assert polars_schema["employee_id"] == pl.Utf8
        assert polars_schema["contact_url"] == pl.Utf8
        assert polars_schema["time_zone"] == pl.Utf8
        assert polars_schema["city"] == pl.Utf8


class TestContactSchemaColumnOrder:
    """Tests for CONTACT_SCHEMA column ordering."""

    def test_column_order_base_then_contact(self) -> None:
        """Verify columns are ordered: base columns first, then Contact columns."""
        names = CONTACT_SCHEMA.column_names()

        # First 12 should be base columns
        assert names[0] == "gid"
        assert names[11] == "tags"

        # 13th column (index 12) should be first Contact column
        assert names[12] == "full_name"

        # Last column should be city
        assert names[-1] == "city"


class TestContactSchemaToDict:
    """Tests for CONTACT_SCHEMA to_dict() serialization."""

    def test_to_dict_structure(self) -> None:
        """Verify to_dict produces expected structure."""
        result = CONTACT_SCHEMA.to_dict()

        assert result["name"] == "contact"
        assert result["task_type"] == "Contact"
        assert result["version"] == "1.0.0"
        assert len(result["columns"]) == 21

    def test_to_dict_includes_contact_columns(self) -> None:
        """Verify Contact columns are included in to_dict output."""
        result = CONTACT_SCHEMA.to_dict()
        column_names = [c["name"] for c in result["columns"]]

        assert "full_name" in column_names
        assert "contact_email" in column_names
        assert "city" in column_names


class TestContactSchemaAllColumnsNullable:
    """Tests that Contact-specific columns are all nullable."""

    def test_all_contact_columns_are_nullable(self) -> None:
        """Verify all Contact-specific columns are nullable."""
        for col in CONTACT_COLUMNS:
            assert col.nullable is True, f"Column {col.name} should be nullable"
