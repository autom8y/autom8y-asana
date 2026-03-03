"""Tests for UNIT_SCHEMA definition.

Verifies the Unit schema has exactly 24 columns (13 base + 11 Unit-specific)
with correct names, types, and nullability.
"""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.dataframes.schemas.base import BASE_COLUMNS
from autom8_asana.dataframes.schemas.unit import UNIT_COLUMNS, UNIT_SCHEMA


class TestUnitSchemaStructure:
    """Tests for UNIT_SCHEMA structure."""

    def test_schema_name(self) -> None:
        """Verify schema name is 'unit'."""
        assert UNIT_SCHEMA.name == "unit"

    def test_task_type_is_unit(self) -> None:
        """Verify task_type is 'Unit'."""
        assert UNIT_SCHEMA.task_type == "Unit"

    def test_version_is_semver(self) -> None:
        """Verify version follows semver format."""
        parts = UNIT_SCHEMA.version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_column_count_is_24(self) -> None:
        """Verify UNIT_SCHEMA has exactly 24 columns (13 base + 11 Unit)."""
        assert len(UNIT_SCHEMA) == 24
        assert len(BASE_COLUMNS) == 13
        assert len(UNIT_COLUMNS) == 11

    def test_includes_all_base_columns(self) -> None:
        """Verify all base columns are present at the start."""
        base_names = [col.name for col in BASE_COLUMNS]
        unit_names = UNIT_SCHEMA.column_names()[:13]
        assert unit_names == base_names


class TestUnitSchemaColumns:
    """Tests for UNIT_SCHEMA column definitions."""

    def test_unit_specific_column_names(self) -> None:
        """Verify all Unit-specific column names are present."""
        expected_unit_columns = [
            "mrr",
            "weekly_ad_spend",
            "products",
            "languages",
            "discount",
            "office",
            "office_phone",
            "vertical",
            "vertical_id",
            "specialty",
            "max_pipeline_stage",
        ]
        # Unit columns come after base columns
        unit_names = UNIT_SCHEMA.column_names()[13:]
        assert unit_names == expected_unit_columns

    @pytest.mark.parametrize(
        "column_name,expected_dtype",
        [
            pytest.param("mrr", "Decimal", id="mrr"),
            pytest.param("weekly_ad_spend", "Decimal", id="weekly_ad_spend"),
            pytest.param("products", "List[Utf8]", id="products"),
            pytest.param("languages", "List[Utf8]", id="languages"),
            pytest.param("discount", "Decimal", id="discount"),
            pytest.param("office", "Utf8", id="office"),
            pytest.param("office_phone", "Utf8", id="office_phone"),
            pytest.param("vertical", "Utf8", id="vertical"),
            pytest.param("vertical_id", "Utf8", id="vertical_id"),
            pytest.param("specialty", "Utf8", id="specialty"),
            pytest.param("max_pipeline_stage", "Utf8", id="max_pipeline_stage"),
        ],
    )
    def test_column_definition(self, column_name: str, expected_dtype: str) -> None:
        """Verify column exists with correct dtype and nullability."""
        col = UNIT_SCHEMA.get_column(column_name)
        assert col is not None
        assert col.dtype == expected_dtype
        assert col.nullable is True


class TestUnitSchemaPolarsConversion:
    """Tests for UNIT_SCHEMA Polars schema conversion."""

    def test_to_polars_schema(self) -> None:
        """Verify to_polars_schema produces valid Polars types."""
        polars_schema = UNIT_SCHEMA.to_polars_schema()

        # Check base columns (inherited)
        assert polars_schema["gid"] == pl.Utf8
        assert polars_schema["name"] == pl.Utf8

        # Check Unit-specific columns (Decimal maps to Float64)
        assert polars_schema["mrr"] == pl.Float64
        assert polars_schema["weekly_ad_spend"] == pl.Float64
        assert polars_schema["discount"] == pl.Float64
        assert isinstance(polars_schema["products"], pl.List)
        assert isinstance(polars_schema["languages"], pl.List)
        assert polars_schema["office"] == pl.Utf8
        assert polars_schema["vertical"] == pl.Utf8


class TestUnitSchemaColumnOrder:
    """Tests for UNIT_SCHEMA column ordering."""

    def test_column_order_base_then_unit(self) -> None:
        """Verify columns are ordered: base columns first, then Unit columns."""
        names = UNIT_SCHEMA.column_names()

        # First 13 should be base columns
        assert names[0] == "gid"
        assert names[11] == "tags"
        assert names[12] == "parent_gid"

        # 14th column (index 13) should be first Unit column
        assert names[13] == "mrr"

        # Last column should be max_pipeline_stage
        assert names[-1] == "max_pipeline_stage"


class TestUnitSchemaToDict:
    """Tests for UNIT_SCHEMA to_dict() serialization."""

    def test_to_dict_structure(self) -> None:
        """Verify to_dict produces expected structure."""
        result = UNIT_SCHEMA.to_dict()

        assert result["name"] == "unit"
        assert result["task_type"] == "Unit"
        assert result["version"] == UNIT_SCHEMA.version
        assert len(result["columns"]) == 24

    def test_to_dict_includes_unit_columns(self) -> None:
        """Verify Unit columns are included in to_dict output."""
        result = UNIT_SCHEMA.to_dict()
        column_names = [c["name"] for c in result["columns"]]

        assert "mrr" in column_names
        assert "weekly_ad_spend" in column_names
        assert "max_pipeline_stage" in column_names
