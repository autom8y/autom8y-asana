"""Tests for UNIT_SCHEMA definition.

Verifies the Unit schema has exactly 23 columns (12 base + 11 Unit-specific)
with correct names, types, and nullability.
"""

from __future__ import annotations

import polars as pl

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
        assert UNIT_SCHEMA.version == "1.0.0"

    def test_column_count_is_23(self) -> None:
        """Verify UNIT_SCHEMA has exactly 23 columns (12 base + 11 Unit)."""
        assert len(UNIT_SCHEMA) == 23
        assert len(BASE_COLUMNS) == 12
        assert len(UNIT_COLUMNS) == 11

    def test_includes_all_base_columns(self) -> None:
        """Verify all base columns are present at the start."""
        base_names = [col.name for col in BASE_COLUMNS]
        unit_names = UNIT_SCHEMA.column_names()[:12]
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
        unit_names = UNIT_SCHEMA.column_names()[12:]
        assert unit_names == expected_unit_columns

    def test_mrr_column(self) -> None:
        """Verify mrr column definition."""
        col = UNIT_SCHEMA.get_column("mrr")
        assert col is not None
        assert col.dtype == "Decimal"
        assert col.nullable is True

    def test_weekly_ad_spend_column(self) -> None:
        """Verify weekly_ad_spend column definition."""
        col = UNIT_SCHEMA.get_column("weekly_ad_spend")
        assert col is not None
        assert col.dtype == "Decimal"
        assert col.nullable is True

    def test_products_column(self) -> None:
        """Verify products column definition."""
        col = UNIT_SCHEMA.get_column("products")
        assert col is not None
        assert col.dtype == "List[Utf8]"
        assert col.nullable is True

    def test_languages_column(self) -> None:
        """Verify languages column definition."""
        col = UNIT_SCHEMA.get_column("languages")
        assert col is not None
        assert col.dtype == "List[Utf8]"
        assert col.nullable is True

    def test_discount_column(self) -> None:
        """Verify discount column definition."""
        col = UNIT_SCHEMA.get_column("discount")
        assert col is not None
        assert col.dtype == "Decimal"
        assert col.nullable is True

    def test_office_column(self) -> None:
        """Verify office column definition."""
        col = UNIT_SCHEMA.get_column("office")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_office_phone_column(self) -> None:
        """Verify office_phone column definition."""
        col = UNIT_SCHEMA.get_column("office_phone")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_vertical_column(self) -> None:
        """Verify vertical column definition."""
        col = UNIT_SCHEMA.get_column("vertical")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_vertical_id_column(self) -> None:
        """Verify vertical_id column definition."""
        col = UNIT_SCHEMA.get_column("vertical_id")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_specialty_column(self) -> None:
        """Verify specialty column definition."""
        col = UNIT_SCHEMA.get_column("specialty")
        assert col is not None
        assert col.dtype == "Utf8"
        assert col.nullable is True

    def test_max_pipeline_stage_column(self) -> None:
        """Verify max_pipeline_stage column definition."""
        col = UNIT_SCHEMA.get_column("max_pipeline_stage")
        assert col is not None
        assert col.dtype == "Utf8"
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

        # First 12 should be base columns
        assert names[0] == "gid"
        assert names[11] == "tags"

        # 13th column (index 12) should be first Unit column
        assert names[12] == "mrr"

        # Last column should be max_pipeline_stage
        assert names[-1] == "max_pipeline_stage"


class TestUnitSchemaToDict:
    """Tests for UNIT_SCHEMA to_dict() serialization."""

    def test_to_dict_structure(self) -> None:
        """Verify to_dict produces expected structure."""
        result = UNIT_SCHEMA.to_dict()

        assert result["name"] == "unit"
        assert result["task_type"] == "Unit"
        assert result["version"] == "1.0.0"
        assert len(result["columns"]) == 23

    def test_to_dict_includes_unit_columns(self) -> None:
        """Verify Unit columns are included in to_dict output."""
        result = UNIT_SCHEMA.to_dict()
        column_names = [c["name"] for c in result["columns"]]

        assert "mrr" in column_names
        assert "weekly_ad_spend" in column_names
        assert "max_pipeline_stage" in column_names
