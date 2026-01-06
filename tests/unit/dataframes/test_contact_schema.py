"""Tests for CONTACT_SCHEMA definition.

Verifies the Contact schema has exactly 12 base columns.
Custom fields can be added when verified on the Contacts project.
"""

from __future__ import annotations

import polars as pl

from autom8_asana.dataframes.schemas.base import BASE_COLUMNS
from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA


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
        assert CONTACT_SCHEMA.version == "2.0.0"

    def test_column_count_is_12(self) -> None:
        """Verify CONTACT_SCHEMA has exactly 12 base columns."""
        assert len(CONTACT_SCHEMA) == 12
        assert len(BASE_COLUMNS) == 12

    def test_includes_all_base_columns(self) -> None:
        """Verify all base columns are present."""
        base_names = [col.name for col in BASE_COLUMNS]
        contact_names = CONTACT_SCHEMA.column_names()
        assert contact_names == base_names


class TestContactSchemaPolarsConversion:
    """Tests for CONTACT_SCHEMA Polars schema conversion."""

    def test_to_polars_schema(self) -> None:
        """Verify to_polars_schema produces valid Polars types."""
        polars_schema = CONTACT_SCHEMA.to_polars_schema()

        # Check base columns
        assert polars_schema["gid"] == pl.Utf8
        assert polars_schema["name"] == pl.Utf8
        assert polars_schema["type"] == pl.Utf8
        assert polars_schema["is_completed"] == pl.Boolean


class TestContactSchemaToDict:
    """Tests for CONTACT_SCHEMA to_dict() serialization."""

    def test_to_dict_structure(self) -> None:
        """Verify to_dict produces expected structure."""
        result = CONTACT_SCHEMA.to_dict()

        assert result["name"] == "contact"
        assert result["task_type"] == "Contact"
        assert result["version"] == "2.0.0"
        assert len(result["columns"]) == 12
