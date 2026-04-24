"""Tests for query/aggregator.py: AggregationCompiler, dtype validation, HAVING schema.

Covers TDD Section 11.3 (TC-AC001 through TC-AC013)
and Section 11.4 (TC-AH001 through TC-AH006).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import polars as pl
import pytest
from pydantic import ValidationError

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.aggregator import (
    AGG_COMPATIBILITY,
    AggregationCompiler,
    build_post_agg_schema,
    validate_alias_uniqueness,
)
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
    AggregationError,
    InvalidOperatorError,
    QueryTooComplexError,
    UnknownFieldError,
)
from autom8_asana.query.guards import QueryLimits
from autom8_asana.query.models import AggFunction, AggregateRequest, AggSpec
from autom8_asana.services.query_service import EntityQueryService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def offer_schema() -> DataFrameSchema:
    """Minimal schema for aggregator tests (Offer-like with Utf8 mrr/cost)."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("vertical", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
            ColumnDef("cost", "Utf8", nullable=True),
            ColumnDef("platforms", "List[Utf8]", nullable=True),
        ],
    )


@pytest.fixture
def numeric_schema() -> DataFrameSchema:
    """Schema with numeric columns for aggregation tests."""
    return DataFrameSchema(
        name="test_entity",
        task_type="TestEntity",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("vertical", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("amount", "Float64", nullable=True),
            ColumnDef("quantity", "Int64", nullable=True),
            ColumnDef("created_date", "Date", nullable=True),
            ColumnDef("is_active", "Boolean", nullable=True),
        ],
    )


# ---------------------------------------------------------------------------
# TestAggregationCompiler (TC-AC001 through TC-AC013)
# ---------------------------------------------------------------------------


class TestAggregationCompiler:
    """Test AggregationCompiler expression compilation."""

    def test_tc_ac001_sum_float64(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC001: sum on Float64 column produces correct result."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total_amount")
        exprs = compiler.compile([spec], numeric_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "medical"],
                "amount": [100.0, 200.0, 300.0],
            }
        )
        result = df.group_by("vertical").agg(exprs).sort("vertical")
        assert result["total_amount"].to_list() == [300.0, 300.0]

    def test_tc_ac002_sum_on_utf8_casts_to_float64(self, offer_schema: DataFrameSchema) -> None:
        """TC-AC002: sum on Utf8 column casts to Float64 (ADR-AGG-005)."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr")
        exprs = compiler.compile([spec], offer_schema)

        # Verify the expression works with numeric strings
        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "medical"],
                "mrr": ["100", "200", "300"],
            }
        )
        result = df.group_by("vertical").agg(exprs).sort("vertical")
        assert result["total_mrr"].to_list() == [300.0, 300.0]

    def test_utf8_sum_non_numeric_strings_become_null(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 sum with non-numeric strings produces null (strict=False)."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "mrr": ["not_a_number", "also_not"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # Non-numeric strings cast to null, sum of nulls is 0 in Polars
        assert result["total_mrr"].to_list() == [0.0]

    def test_tc_ac003_count_utf8(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC003: count on Utf8 column counts non-null values."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="vertical", agg=AggFunction.COUNT, alias="vert_count")
        exprs = compiler.compile([spec], numeric_schema)

        df = pl.DataFrame(
            {
                "section": ["A", "A", "A"],
                "vertical": ["dental", None, "medical"],
            }
        )
        result = df.group_by("section").agg(exprs)
        # count excludes nulls
        assert result["vert_count"].to_list() == [2]

    def test_tc_ac004_count_distinct_utf8(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC004: count_distinct on Utf8 column counts unique values."""
        compiler = AggregationCompiler()
        spec = AggSpec(
            column="vertical",
            agg=AggFunction.COUNT_DISTINCT,
            alias="unique_verticals",
        )
        exprs = compiler.compile([spec], numeric_schema)

        df = pl.DataFrame(
            {
                "section": ["Active", "Active", "Active"],
                "vertical": ["dental", "dental", "medical"],
            }
        )
        result = df.group_by("section").agg(exprs)
        assert result["unique_verticals"].to_list() == [2]

    def test_tc_ac005_mean_float64(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC005: mean on Float64 column produces Float64 mean."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="amount", agg=AggFunction.MEAN, alias="avg_amount")
        exprs = compiler.compile([spec], numeric_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "amount": [100.0, 200.0],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["avg_amount"].to_list() == [150.0]

    def test_tc_ac006_mean_on_boolean_raises(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC006: mean on Boolean column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="is_active", agg=AggFunction.MEAN)

        with pytest.raises(AggregationError) as exc_info:
            compiler.compile([spec], numeric_schema)
        assert "mean" in str(exc_info.value.message)
        assert "Boolean" in str(exc_info.value.message)

    def test_tc_ac007_min_date(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC007: min on Date column produces minimum date."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="created_date", agg=AggFunction.MIN, alias="earliest")
        exprs = compiler.compile([spec], numeric_schema)

        from datetime import date

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "created_date": [date(2025, 1, 1), date(2025, 6, 15)],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["earliest"].to_list() == [date(2025, 1, 1)]

    def test_tc_ac008_max_int64(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC008: max on Int64 column produces maximum value."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="quantity", agg=AggFunction.MAX, alias="max_qty")
        exprs = compiler.compile([spec], numeric_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "quantity": [10, 50, 30],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["max_qty"].to_list() == [50]

    def test_tc_ac009_sum_on_list_raises(self, offer_schema: DataFrameSchema) -> None:
        """TC-AC009: sum on List[Utf8] column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="platforms", agg=AggFunction.SUM)

        with pytest.raises(AggregationError) as exc_info:
            compiler.compile([spec], offer_schema)
        assert "platforms" in str(exc_info.value.message)

    def test_tc_ac010_nonexistent_column_raises(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC010: Aggregation on non-existent column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="nonexistent", agg=AggFunction.SUM)

        with pytest.raises(AggregationError) as exc_info:
            compiler.compile([spec], numeric_schema)
        assert "nonexistent" in str(exc_info.value.message)
        assert "Available" in str(exc_info.value.message)

    def test_tc_ac011_alias_applied(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC011: Alias applied correctly to output column name."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="my_total")
        exprs = compiler.compile([spec], numeric_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental"],
                "amount": [100.0],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert "my_total" in result.columns

    def test_tc_ac012_default_alias(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC012: Default alias "{agg}_{column}" generated correctly."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="amount", agg=AggFunction.SUM)
        exprs = compiler.compile([spec], numeric_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental"],
                "amount": [100.0],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert "sum_amount" in result.columns

    def test_tc_ac014_min_max_utf8_casts(self, offer_schema: DataFrameSchema) -> None:
        """TC-AC014: min/max on Utf8 column casts to Float64 (ADR-AGG-005)."""
        compiler = AggregationCompiler()
        spec_min = AggSpec(column="mrr", agg=AggFunction.MIN, alias="min_mrr")
        spec_max = AggSpec(column="mrr", agg=AggFunction.MAX, alias="max_mrr")
        exprs = compiler.compile([spec_min, spec_max], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["100", "200", "300"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["min_mrr"].to_list() == [100.0]
        assert result["max_mrr"].to_list() == [300.0]

    def test_tc_ac015_mean_utf8_casts(self, offer_schema: DataFrameSchema) -> None:
        """TC-AC015: mean on Utf8 column casts to Float64 (ADR-AGG-005)."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.MEAN, alias="avg_mrr")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "mrr": ["100", "200"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["avg_mrr"].to_list() == [150.0]

    def test_tc_ac016_count_on_utf8_no_cast(self, offer_schema: DataFrameSchema) -> None:
        """TC-AC016: count/count_distinct on Utf8 do NOT cast (they count values, not numerics)."""
        compiler = AggregationCompiler()
        spec_count = AggSpec(column="mrr", agg=AggFunction.COUNT, alias="mrr_count")
        spec_uniq = AggSpec(column="mrr", agg=AggFunction.COUNT_DISTINCT, alias="mrr_uniq")
        exprs = compiler.compile([spec_count, spec_uniq], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["100", "100", "200"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["mrr_count"].to_list() == [3]
        assert result["mrr_uniq"].to_list() == [2]

    def test_tc_ac013_multiple_specs(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AC013: Multiple agg specs compiled together returns correct length."""
        compiler = AggregationCompiler()
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="amount", agg=AggFunction.MEAN, alias="avg"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="row_count"),
        ]
        exprs = compiler.compile(specs, numeric_schema)
        assert len(exprs) == 3

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "amount": [100.0, 200.0],
                "gid": ["1", "2"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert "total" in result.columns
        assert "avg" in result.columns
        assert "row_count" in result.columns


# ---------------------------------------------------------------------------
# TestBuildPostAggSchema (TC-AH006)  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestBuildPostAggSchema:
    """Test synthetic schema construction for HAVING validation."""

    def test_tc_ah006_count_output_dtype(self, numeric_schema: DataFrameSchema) -> None:
        """count produces Int64 output dtype in post-agg schema."""
        spec = AggSpec(column="gid", agg=AggFunction.COUNT, alias="row_count")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        col = schema.get_column("row_count")
        assert col is not None
        assert col.dtype == "Int64"

    def test_mean_output_dtype(self, numeric_schema: DataFrameSchema) -> None:
        """mean produces Float64 output dtype."""
        spec = AggSpec(column="amount", agg=AggFunction.MEAN, alias="avg_amount")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        col = schema.get_column("avg_amount")
        assert col is not None
        assert col.dtype == "Float64"

    def test_sum_output_dtype_same_as_input(self, numeric_schema: DataFrameSchema) -> None:
        """sum retains source dtype."""
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        col = schema.get_column("total")
        assert col is not None
        assert col.dtype == "Float64"

    def test_count_distinct_output_dtype(self, numeric_schema: DataFrameSchema) -> None:
        """count_distinct produces Int64 output dtype."""
        spec = AggSpec(column="vertical", agg=AggFunction.COUNT_DISTINCT, alias="uniq")
        schema = build_post_agg_schema(
            group_by_columns=["section"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        col = schema.get_column("uniq")
        assert col is not None
        assert col.dtype == "Int64"

    def test_group_by_columns_retain_source_dtype(
        self,
        numeric_schema: DataFrameSchema,
    ) -> None:
        """group_by columns retain their source dtype."""
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        col = schema.get_column("vertical")
        assert col is not None
        assert col.dtype == "Utf8"

    def test_tc_hs004_sum_utf8_output_dtype_float64(self, offer_schema: DataFrameSchema) -> None:
        """TC-HS004: sum on Utf8 (cast) produces Float64 output dtype."""
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("total_mrr")
        assert col is not None
        assert col.dtype == "Float64"

    def test_sum_int64_output_dtype_int64(self, numeric_schema: DataFrameSchema) -> None:
        """sum on Int64 produces Int64 output dtype (not Float64)."""
        spec = AggSpec(column="quantity", agg=AggFunction.SUM, alias="total_qty")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        col = schema.get_column("total_qty")
        assert col is not None
        assert col.dtype == "Int64"

    def test_min_utf8_output_dtype_float64(self, offer_schema: DataFrameSchema) -> None:
        """min/max on Utf8 (cast) produces Float64 output dtype."""
        spec = AggSpec(column="mrr", agg=AggFunction.MIN, alias="min_mrr")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("min_mrr")
        assert col is not None
        assert col.dtype == "Float64"

    def test_min_date_output_dtype_date(self, numeric_schema: DataFrameSchema) -> None:
        """min on Date column retains Date output dtype."""
        spec = AggSpec(column="created_date", agg=AggFunction.MIN, alias="min_date")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        col = schema.get_column("min_date")
        assert col is not None
        assert col.dtype == "Date"

    def test_multiple_agg_columns_present(self, numeric_schema: DataFrameSchema) -> None:
        """Multiple agg specs all present in post-agg schema."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="cnt"),
        ]
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=specs,
            source_schema=numeric_schema,
        )
        assert schema.get_column("total") is not None
        assert schema.get_column("cnt") is not None
        assert schema.get_column("vertical") is not None


# ---------------------------------------------------------------------------
# TestHavingWithPredicateCompiler (TC-AH001 through TC-AH005)
# ---------------------------------------------------------------------------


class TestHavingWithPredicateCompiler:
    """Test HAVING clause using PredicateCompiler on synthetic post-agg schema."""

    def test_tc_ah001_having_on_agg_alias_gt(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AH001: HAVING on aggregated alias column (gt) filters groups correctly."""
        # Build aggregated DataFrame
        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "medical", "medical", "medical"],
                "amount": [100.0, 200.0, 50.0, 50.0, 50.0],
            }
        )
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total_amount")
        agg_compiler = AggregationCompiler()
        exprs = agg_compiler.compile([spec], numeric_schema)
        agg_df = df.group_by("vertical").agg(exprs)

        # Build post-agg schema and compile HAVING
        post_schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        pred_compiler = PredicateCompiler()
        having_node = {"field": "total_amount", "op": "gt", "value": 200.0}

        from pydantic import TypeAdapter

        from autom8_asana.query.models import PredicateNode

        adapter = TypeAdapter(PredicateNode)
        parsed = adapter.validate_python(having_node)
        having_expr = pred_compiler.compile(parsed, post_schema)
        result = agg_df.filter(having_expr)

        assert len(result) == 1
        assert result["vertical"].to_list() == ["dental"]

    def test_tc_ah002_having_on_group_by_column(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AH002: HAVING on group_by column (eq) filters groups by group key."""
        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "medical"],
                "amount": [100.0, 200.0, 300.0],
            }
        )
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total")
        agg_compiler = AggregationCompiler()
        exprs = agg_compiler.compile([spec], numeric_schema)
        agg_df = df.group_by("vertical").agg(exprs)

        post_schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        pred_compiler = PredicateCompiler()

        from pydantic import TypeAdapter

        from autom8_asana.query.models import PredicateNode

        adapter = TypeAdapter(PredicateNode)
        parsed = adapter.validate_python({"field": "vertical", "op": "eq", "value": "dental"})
        having_expr = pred_compiler.compile(parsed, post_schema)
        result = agg_df.filter(having_expr)

        assert len(result) == 1
        assert result["vertical"].to_list() == ["dental"]

    def test_tc_ah003_having_nonexistent_column_raises(
        self, numeric_schema: DataFrameSchema
    ) -> None:
        """TC-AH003: HAVING referencing non-existent column raises UnknownFieldError."""
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total")
        post_schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        pred_compiler = PredicateCompiler()

        from pydantic import TypeAdapter

        from autom8_asana.query.models import PredicateNode

        adapter = TypeAdapter(PredicateNode)
        parsed = adapter.validate_python({"field": "nonexistent_col", "op": "gt", "value": 100})
        with pytest.raises(UnknownFieldError) as exc_info:
            pred_compiler.compile(parsed, post_schema)
        assert exc_info.value.field == "nonexistent_col"

    def test_tc_ah004_having_with_and_group(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AH004: HAVING with AND group applies both conditions."""
        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "medical", "medical"],
                "amount": [100.0, 200.0, 50.0, 50.0],
            }
        )
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total")
        agg_compiler = AggregationCompiler()
        exprs = agg_compiler.compile([spec], numeric_schema)
        agg_df = df.group_by("vertical").agg(exprs)

        post_schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        pred_compiler = PredicateCompiler()

        from pydantic import TypeAdapter

        from autom8_asana.query.models import PredicateNode

        adapter = TypeAdapter(PredicateNode)
        parsed = adapter.validate_python(
            {
                "and": [
                    {"field": "total", "op": "gte", "value": 100.0},
                    {"field": "vertical", "op": "eq", "value": "dental"},
                ]
            }
        )
        having_expr = pred_compiler.compile(parsed, post_schema)
        result = agg_df.filter(having_expr)

        assert len(result) == 1
        assert result["vertical"].to_list() == ["dental"]

    def test_tc_ah005_having_invalid_operator_raises(self, numeric_schema: DataFrameSchema) -> None:
        """TC-AH005: HAVING with invalid operator for output dtype raises InvalidOperatorError."""
        spec = AggSpec(column="amount", agg=AggFunction.COUNT, alias="row_count")
        post_schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=numeric_schema,
        )
        pred_compiler = PredicateCompiler()

        from pydantic import TypeAdapter

        from autom8_asana.query.models import PredicateNode

        adapter = TypeAdapter(PredicateNode)
        # 'contains' is not valid for Int64
        parsed = adapter.validate_python({"field": "row_count", "op": "contains", "value": "5"})
        with pytest.raises(InvalidOperatorError):
            pred_compiler.compile(parsed, post_schema)


# ---------------------------------------------------------------------------
# AGG_COMPATIBILITY matrix coverage
# ---------------------------------------------------------------------------


class TestAggCompatibility:
    """Test the AGG_COMPATIBILITY matrix is correctly defined."""

    def test_utf8_all_non_list(self) -> None:
        """Utf8 supports all non-list aggregation functions (ADR-AGG-005)."""
        allowed = AGG_COMPATIBILITY["Utf8"]
        for func in AggFunction:
            assert func in allowed

    def test_int64_all_aggs(self) -> None:
        """Int64 supports all aggregation functions."""
        allowed = AGG_COMPATIBILITY["Int64"]
        for func in AggFunction:
            assert func in allowed

    def test_boolean_only_universal(self) -> None:
        """Boolean supports only count and count_distinct."""
        allowed = AGG_COMPATIBILITY["Boolean"]
        assert AggFunction.COUNT in allowed
        assert AggFunction.COUNT_DISTINCT in allowed
        assert AggFunction.SUM not in allowed

    def test_date_orderable_and_universal(self) -> None:
        """Date supports min, max, count, count_distinct but not sum/mean."""
        allowed = AGG_COMPATIBILITY["Date"]
        assert AggFunction.MIN in allowed
        assert AggFunction.MAX in allowed
        assert AggFunction.COUNT in allowed
        assert AggFunction.SUM not in allowed
        assert AggFunction.MEAN not in allowed

    def test_list_utf8_no_aggs(self) -> None:
        """List[Utf8] supports no aggregation functions."""
        allowed = AGG_COMPATIBILITY["List[Utf8]"]
        assert len(allowed) == 0


# ---------------------------------------------------------------------------
# TestValidateAliasUniqueness
# ---------------------------------------------------------------------------


class TestValidateAliasUniqueness:
    """Test alias uniqueness validation."""

    def test_unique_aliases_pass(self) -> None:
        """Unique aliases do not raise."""
        specs = [
            AggSpec(column="a", agg=AggFunction.SUM, alias="total_a"),
            AggSpec(column="b", agg=AggFunction.COUNT, alias="cnt_b"),
        ]
        validate_alias_uniqueness(specs, ["vertical"])  # no exception

    def test_duplicate_aliases_raise(self) -> None:
        """Duplicate aliases raise AggregationError."""
        specs = [
            AggSpec(column="a", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="b", agg=AggFunction.SUM, alias="total"),
        ]
        with pytest.raises(AggregationError, match="Duplicate alias"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_alias_collides_with_group_by(self) -> None:
        """Alias colliding with group_by column raises AggregationError."""
        specs = [
            AggSpec(column="a", agg=AggFunction.SUM, alias="vertical"),
        ]
        with pytest.raises(AggregationError, match="collides with group_by"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_default_aliases_unique(self) -> None:
        """Default aliases for different columns are unique."""
        specs = [
            AggSpec(column="a", agg=AggFunction.SUM),
            AggSpec(column="b", agg=AggFunction.SUM),
        ]
        validate_alias_uniqueness(specs, ["vertical"])  # no exception


# --- Adversarial tests (merged from test_adversarial_aggregate.py; Sprint 15 S4) ---
# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def offer_schema() -> DataFrameSchema:
    """Offer-like schema with Utf8 financial columns and List column."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("vertical", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
            ColumnDef("cost", "Utf8", nullable=True),
            ColumnDef("amount", "Float64", nullable=True),
            ColumnDef("quantity", "Int64", nullable=True),
            ColumnDef("is_active", "Boolean", nullable=True),
            ColumnDef("created_date", "Date", nullable=True),
            ColumnDef("platforms", "List[Utf8]", nullable=True),
        ],
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


def _patch_schema(schema: DataFrameSchema):
    """Context manager to patch SchemaRegistry for tests."""
    return patch(
        "autom8_asana.query.engine.SchemaRegistry",
        **{
            "return_value.get_schema.return_value": schema,
            "get_instance.return_value.get_schema.return_value": schema,
        },
    )


def _make_engine(df: pl.DataFrame, **limits_kwargs) -> QueryEngine:
    """Build a QueryEngine with a mocked service returning the given DataFrame."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
    limits = QueryLimits(**limits_kwargs) if limits_kwargs else QueryLimits()
    return QueryEngine(provider=service, limits=limits)


# ===========================================================================
# 1. AggSpec Model Edge Cases
# ===========================================================================


class TestAggSpecModelEdgeCases:
    """Adversarial tests for AggSpec and AggregateRequest Pydantic models."""

    def test_aggspec_empty_string_column(self) -> None:
        """AggSpec with empty string column name is accepted by Pydantic
        but should fail at compilation time (column not in schema)."""
        spec = AggSpec(column="", agg=AggFunction.SUM, alias="total")
        assert spec.column == ""

    def test_aggspec_alias_collides_with_group_by(self) -> None:
        """AggSpec alias that matches a group_by column is caught by validate_alias_uniqueness."""
        specs = [AggSpec(column="amount", agg=AggFunction.SUM, alias="vertical")]
        with pytest.raises(AggregationError, match="collides with group_by"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_duplicate_aliases_in_aggregation_list(self) -> None:
        """Duplicate explicit aliases are rejected."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="cost", agg=AggFunction.SUM, alias="total"),
        ]
        with pytest.raises(AggregationError, match="Duplicate alias"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_duplicate_default_aliases_same_column_same_func(self) -> None:
        """Two AggSpecs on same column with same function produce colliding default aliases."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM),
            AggSpec(column="amount", agg=AggFunction.SUM),
        ]
        # Default alias for both: "sum_amount" -- should collide
        with pytest.raises(AggregationError, match="Duplicate alias"):
            validate_alias_uniqueness(specs, ["vertical"])

    def test_all_six_agg_functions_on_same_column(self, offer_schema: DataFrameSchema) -> None:
        """All 6 agg functions applied to a single Float64 column compiles successfully."""
        compiler = AggregationCompiler()
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="s"),
            AggSpec(column="amount", agg=AggFunction.COUNT, alias="c"),
            AggSpec(column="amount", agg=AggFunction.MEAN, alias="m"),
            AggSpec(column="amount", agg=AggFunction.MIN, alias="mn"),
            AggSpec(column="amount", agg=AggFunction.MAX, alias="mx"),
            AggSpec(column="amount", agg=AggFunction.COUNT_DISTINCT, alias="cd"),
        ]
        exprs = compiler.compile(specs, offer_schema)
        assert len(exprs) == 6

    def test_aggfunction_invalid_string_rejected(self) -> None:
        """AggFunction enum rejects invalid string values via Pydantic."""
        with pytest.raises(ValidationError):
            AggSpec.model_validate({"column": "amount", "agg": "median", "alias": "x"})

    def test_aggregate_request_empty_group_by_rejected(self) -> None:
        """AggregateRequest with empty group_by fails Pydantic min_length=1."""
        with pytest.raises(ValidationError, match="group_by"):
            AggregateRequest.model_validate(
                {
                    "group_by": [],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                }
            )

    def test_aggregate_request_six_group_by_rejected(self) -> None:
        """AggregateRequest with 6 group_by columns fails Pydantic max_length=5."""
        with pytest.raises(ValidationError, match="group_by"):
            AggregateRequest.model_validate(
                {
                    "group_by": ["a", "b", "c", "d", "e", "f"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                }
            )

    def test_aggregate_request_empty_aggregations_rejected(self) -> None:
        """AggregateRequest with empty aggregations fails Pydantic min_length=1."""
        with pytest.raises(ValidationError, match="aggregations"):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                    "aggregations": [],
                }
            )

    def test_aggregate_request_eleven_aggregations_rejected(self) -> None:
        """AggregateRequest with 11 aggregations fails Pydantic max_length=10."""
        aggs = [{"column": "gid", "agg": "count", "alias": f"a{i}"} for i in range(11)]
        with pytest.raises(ValidationError, match="aggregations"):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                    "aggregations": aggs,
                }
            )

    def test_aggregate_request_extra_field_rejected(self) -> None:
        """AggregateRequest with extra fields rejected by extra='forbid'."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                    "surprise": True,
                }
            )

    def test_aggspec_extra_field_rejected(self) -> None:
        """AggSpec with extra fields rejected by extra='forbid'."""
        with pytest.raises(ValidationError):
            AggSpec.model_validate(
                {
                    "column": "gid",
                    "agg": "count",
                    "alias": "x",
                    "extra_param": 42,
                }
            )


# ===========================================================================
# 2. GROUP BY Edge Cases
# ===========================================================================


class TestGroupByEdgeCases:
    """Adversarial tests for GROUP BY validation and execution."""

    def test_group_by_list_column_rejected(self, offer_schema: DataFrameSchema) -> None:
        """GROUP BY on a List[Utf8] column raises AggregationError."""
        limits = QueryLimits()
        with pytest.raises(AggregationError, match="List"):
            limits.check_group_by(["platforms"], offer_schema)

    def test_group_by_nonexistent_column_rejected(self, offer_schema: DataFrameSchema) -> None:
        """GROUP BY on column not in schema raises UnknownFieldError."""
        limits = QueryLimits()
        with pytest.raises(UnknownFieldError) as exc_info:
            limits.check_group_by(["does_not_exist"], offer_schema)
        assert exc_info.value.field == "does_not_exist"

    def test_group_by_exceeds_max_columns(self, offer_schema: DataFrameSchema) -> None:
        """GROUP BY with columns exceeding max_group_by_columns raises AggregationError."""
        limits = QueryLimits(max_group_by_columns=2)
        with pytest.raises(AggregationError, match="Too many group_by"):
            limits.check_group_by(["gid", "name", "vertical"], offer_schema)

    async def test_group_by_all_null_values_produces_single_null_group(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """GROUP BY on column where all values are null produces a single null group."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": [None, None, None],
                "vertical": [None, None, None],
                "section": ["A", "B", "C"],
                "mrr": ["100", "200", "300"],
                "cost": ["10", "20", "30"],
                "amount": [1.0, 2.0, 3.0],
                "quantity": [1, 2, 3],
                "is_active": [True, False, True],
                "created_date": [None, None, None],
                "platforms": [["fb"], ["g"], ["fb"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        # All nulls -> single group with null key
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] is None
        assert result.data[0]["cnt"] == 3

    async def test_group_by_single_unique_value_produces_single_group(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """GROUP BY on column with single unique value produces one group."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "vertical": ["dental", "dental", "dental"],
                "section": ["A", "B", "C"],
                "mrr": ["100", "200", "300"],
                "cost": ["10", "20", "30"],
                "amount": [1.0, 2.0, 3.0],
                "quantity": [1, 2, 3],
                "is_active": [True, False, True],
                "created_date": [None, None, None],
                "platforms": [["fb"], ["g"], ["fb"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"
        assert result.data[0]["cnt"] == 3

    async def test_group_by_exceeding_max_aggregate_groups_raises(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """GROUP BY producing groups > max_aggregate_groups triggers AggregateGroupLimitError."""
        # Each row has unique gid, so group_by gid produces N groups
        n = 15
        df = pl.DataFrame(
            {
                "gid": [str(i) for i in range(n)],
                "name": [f"n{i}" for i in range(n)],
                "vertical": [f"v{i}" for i in range(n)],
                "section": ["A"] * n,
                "mrr": ["100"] * n,
                "cost": ["10"] * n,
                "amount": [1.0] * n,
                "quantity": [1] * n,
                "is_active": [True] * n,
                "created_date": [None] * n,
                "platforms": [["fb"]] * n,
            }
        )
        engine = _make_engine(df, max_aggregate_groups=10)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_schema(offer_schema):
            with pytest.raises(AggregateGroupLimitError) as exc_info:
                await engine.execute_aggregate(
                    entity_type="offer",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.group_count == n
            assert exc_info.value.max_groups == 10


# ===========================================================================
# 3. HAVING Edge Cases
# ===========================================================================


class TestHavingEdgeCases:
    """Adversarial tests for HAVING clause."""

    async def test_having_nonexistent_alias_raises(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING referencing alias not in agg output raises UnknownFieldError."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "vertical": ["dental", "medical"],
                "section": ["A", "B"],
                "mrr": ["100", "200"],
                "cost": ["10", "20"],
                "amount": [1.0, 2.0],
                "quantity": [1, 2],
                "is_active": [True, False],
                "created_date": [None, None],
                "platforms": [["fb"], ["g"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": {"field": "nonexistent_alias", "op": "gt", "value": 0},
            }
        )
        with _patch_schema(offer_schema):
            with pytest.raises(UnknownFieldError) as exc_info:
                await engine.execute_aggregate(
                    entity_type="offer",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )
            assert exc_info.value.field == "nonexistent_alias"

    async def test_having_complex_nested_predicates(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING with AND/OR nested predicates works correctly."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4", "5", "6"],
                "name": ["A", "B", "C", "D", "E", "F"],
                "vertical": ["dental", "dental", "medical", "medical", "vet", "vet"],
                "section": ["A"] * 6,
                "mrr": ["100"] * 6,
                "cost": ["10"] * 6,
                "amount": [100.0, 200.0, 50.0, 60.0, 1000.0, 2000.0],
                "quantity": [1, 2, 3, 4, 5, 6],
                "is_active": [True] * 6,
                "created_date": [None] * 6,
                "platforms": [["fb"]] * 6,
            }
        )
        engine = _make_engine(df)

        # HAVING: (total > 200 AND cnt >= 2) OR vertical = "vet"
        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "gid", "agg": "count", "alias": "cnt"},
                ],
                "having": {
                    "or": [
                        {
                            "and": [
                                {"field": "total", "op": "gt", "value": 200.0},
                                {"field": "cnt", "op": "gte", "value": 2},
                            ]
                        },
                        {"field": "vertical", "op": "eq", "value": "vet"},
                    ]
                },
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        verts = {d["vertical"] for d in result.data}
        # dental: total=300, cnt=2 -> passes AND
        # medical: total=110, cnt=2 -> fails total > 200
        # vet: total=3000, cnt=2 -> passes both branches
        assert "dental" in verts
        assert "vet" in verts
        assert "medical" not in verts

    async def test_having_filters_all_groups_returns_empty(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING that filters out ALL groups returns empty data."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "vertical": ["dental", "medical"],
                "section": ["A", "B"],
                "mrr": ["100", "200"],
                "cost": ["10", "20"],
                "amount": [1.0, 2.0],
                "quantity": [1, 2],
                "is_active": [True, False],
                "created_date": [None, None],
                "platforms": [["fb"], ["g"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": {"field": "cnt", "op": "gt", "value": 999999},
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.data == []
        assert result.meta.group_count == 0

    async def test_having_on_group_by_column_works(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING on a group_by column (not an aggregation alias) works."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "vertical": ["dental", "dental", "medical"],
                "section": ["A", "B", "C"],
                "mrr": ["100", "200", "300"],
                "cost": ["10", "20", "30"],
                "amount": [1.0, 2.0, 3.0],
                "quantity": [1, 2, 3],
                "is_active": [True, False, True],
                "created_date": [None, None, None],
                "platforms": [["fb"], ["g"], ["fb"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": {"field": "vertical", "op": "eq", "value": "dental"},
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"
        assert result.data[0]["cnt"] == 2

    async def test_having_numeric_comparison_on_count(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING with numeric comparison on count result works."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4", "5"],
                "name": ["A", "B", "C", "D", "E"],
                "vertical": ["dental", "dental", "dental", "medical", "medical"],
                "section": ["A"] * 5,
                "mrr": ["100"] * 5,
                "cost": ["10"] * 5,
                "amount": [1.0] * 5,
                "quantity": [1] * 5,
                "is_active": [True] * 5,
                "created_date": [None] * 5,
                "platforms": [["fb"]] * 5,
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": {"field": "cnt", "op": "gte", "value": 3},
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        # dental=3, medical=2 -> only dental passes cnt >= 3
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"

    def test_having_flat_array_sugar_wraps_to_and(self) -> None:
        """HAVING provided as flat array is auto-wrapped to AND group."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": [
                    {"field": "cnt", "op": "gt", "value": 1},
                    {"field": "cnt", "op": "lt", "value": 100},
                ],
            }
        )
        # Should parse without error; having is an AndGroup
        assert req.having is not None

    def test_having_empty_array_becomes_none(self) -> None:
        """HAVING provided as empty array becomes None."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": [],
            }
        )
        assert req.having is None

    async def test_having_depth_guard(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """HAVING predicate exceeding max depth raises QueryTooComplexError."""
        df = pl.DataFrame(
            {
                "gid": ["1"],
                "name": ["A"],
                "vertical": ["dental"],
                "section": ["A"],
                "mrr": ["100"],
                "cost": ["10"],
                "amount": [1.0],
                "quantity": [1],
                "is_active": [True],
                "created_date": [None],
                "platforms": [["fb"]],
            }
        )
        engine = _make_engine(df)

        leaf = {"field": "cnt", "op": "gt", "value": 1}
        deep = {"and": [{"or": [{"and": [{"not": {"and": [leaf]}}]}]}]}  # depth=6

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": deep,
            }
        )
        with _patch_schema(offer_schema):
            with pytest.raises(QueryTooComplexError):
                await engine.execute_aggregate(
                    entity_type="offer",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )


# ===========================================================================
# 4. Aggregation Compilation Edge Cases
# ===========================================================================


class TestAggregationCompilationEdgeCases:
    """Adversarial tests for AggregationCompiler edge cases."""

    def test_sum_on_boolean_rejected(self, offer_schema: DataFrameSchema) -> None:
        """sum on Boolean column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="is_active", agg=AggFunction.SUM)
        with pytest.raises(AggregationError, match="Boolean"):
            compiler.compile([spec], offer_schema)

    def test_mean_on_boolean_rejected(self, offer_schema: DataFrameSchema) -> None:
        """mean on Boolean column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="is_active", agg=AggFunction.MEAN)
        with pytest.raises(AggregationError, match="Boolean"):
            compiler.compile([spec], offer_schema)

    def test_sum_on_date_rejected(self, offer_schema: DataFrameSchema) -> None:
        """sum on Date column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="created_date", agg=AggFunction.SUM)
        with pytest.raises(AggregationError, match="Date"):
            compiler.compile([spec], offer_schema)

    def test_mean_on_date_rejected(self, offer_schema: DataFrameSchema) -> None:
        """mean on Date column raises AggregationError."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="created_date", agg=AggFunction.MEAN)
        with pytest.raises(AggregationError, match="Date"):
            compiler.compile([spec], offer_schema)

    def test_any_agg_on_list_utf8_rejected(self, offer_schema: DataFrameSchema) -> None:
        """All aggregation functions on List[Utf8] column are rejected."""
        compiler = AggregationCompiler()
        for func in AggFunction:
            spec = AggSpec(column="platforms", agg=func, alias=f"test_{func.value}")
            with pytest.raises(AggregationError):
                compiler.compile([spec], offer_schema)

    def test_sum_utf8_all_nulls_returns_zero(self, offer_schema: DataFrameSchema) -> None:
        """sum on Utf8 column where all values are null returns 0.0."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "mrr": [None, None],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # Polars sum of nulls after cast = 0.0
        assert result["total_mrr"].to_list() == [0.0]

    def test_count_all_nulls_returns_zero(self, offer_schema: DataFrameSchema) -> None:
        """count on column with all null values returns 0."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT, alias="cnt")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "mrr": [None, None],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["cnt"].to_list() == [0]

    def test_count_distinct_with_nulls(self, offer_schema: DataFrameSchema) -> None:
        """count_distinct on column with nulls: Polars n_unique counts null as a distinct value."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT_DISTINCT, alias="uniq")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["100", "100", None],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # "100" and null = 2 distinct values
        assert result["uniq"].to_list() == [2]

    def test_mean_on_empty_df(self, offer_schema: DataFrameSchema) -> None:
        """mean on empty DataFrame produces empty result, not an error."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="amount", agg=AggFunction.MEAN, alias="avg")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": pl.Series([], dtype=pl.Utf8),
                "amount": pl.Series([], dtype=pl.Float64),
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert len(result) == 0

    def test_empty_string_column_not_in_schema(self, offer_schema: DataFrameSchema) -> None:
        """AggSpec with empty string column name fails at compile time."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="", agg=AggFunction.SUM, alias="total")
        with pytest.raises(AggregationError, match="Unknown column"):
            compiler.compile([spec], offer_schema)


# ===========================================================================
# 5. Engine Integration Adversarial
# ===========================================================================


class TestEngineIntegrationAdversarial:
    """Adversarial tests for QueryEngine.execute_aggregate()."""

    async def test_full_pipeline_where_section_having(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """Full pipeline: WHERE + section + GROUP BY + HAVING."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-123"})

        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3", "4", "5"],
                "name": ["A", "B", "C", "D", "E"],
                "vertical": ["dental", "dental", "medical", "medical", "dental"],
                "section": ["Active", "Active", "Active", "Won", "Active"],
                "mrr": ["100", "200", "300", "400", "500"],
                "cost": ["10", "20", "30", "40", "50"],
                "amount": [100.0, 200.0, 300.0, 400.0, 500.0],
                "quantity": [1, 2, 3, 4, 5],
                "is_active": [True, True, False, True, True],
                "created_date": [None] * 5,
                "platforms": [["fb"]] * 5,
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                ],
                "section": "Active",
                "where": {"field": "is_active", "op": "eq", "value": True},
                "having": {"field": "total", "op": "gte", "value": 500.0},
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
                section_index=section_index,
            )

        # Active section: gid 1,2,3,5
        # WHERE is_active=True: gid 1,2,5 (dental: 100+200+500=800)
        # medical gid 3 has is_active=False so excluded
        # HAVING total >= 500: dental=800 passes
        assert result.meta.group_count == 1
        assert result.data[0]["vertical"] == "dental"
        assert result.data[0]["total"] == 800.0

    async def test_where_depth_guard(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """WHERE predicate exceeding max depth raises QueryTooComplexError."""
        df = pl.DataFrame(
            {
                "gid": ["1"],
                "name": ["A"],
                "vertical": ["dental"],
                "section": ["A"],
                "mrr": ["100"],
                "cost": ["10"],
                "amount": [1.0],
                "quantity": [1],
                "is_active": [True],
                "created_date": [None],
                "platforms": [["fb"]],
            }
        )
        engine = _make_engine(df)

        leaf = {"field": "name", "op": "eq", "value": "x"}
        deep = {"and": [{"or": [{"and": [{"not": {"and": [leaf]}}]}]}]}  # depth=6

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "where": deep,
            }
        )
        with _patch_schema(offer_schema):
            with pytest.raises(QueryTooComplexError):
                await engine.execute_aggregate(
                    entity_type="offer",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )

    async def test_alias_collision_at_engine_level(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """Duplicate aliases detected at engine level before compilation."""
        df = pl.DataFrame(
            {
                "gid": ["1"],
                "name": ["A"],
                "vertical": ["dental"],
                "section": ["A"],
                "mrr": ["100"],
                "cost": ["10"],
                "amount": [1.0],
                "quantity": [1],
                "is_active": [True],
                "created_date": [None],
                "platforms": [["fb"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "quantity", "agg": "sum", "alias": "total"},
                ],
            }
        )
        with _patch_schema(offer_schema):
            with pytest.raises(AggregationError, match="Duplicate alias"):
                await engine.execute_aggregate(
                    entity_type="offer",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )

    async def test_alias_collides_with_group_by_column_at_engine(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """Alias colliding with group_by column detected at engine level."""
        df = pl.DataFrame(
            {
                "gid": ["1"],
                "name": ["A"],
                "vertical": ["dental"],
                "section": ["A"],
                "mrr": ["100"],
                "cost": ["10"],
                "amount": [1.0],
                "quantity": [1],
                "is_active": [True],
                "created_date": [None],
                "platforms": [["fb"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "vertical"},
                ],
            }
        )
        with _patch_schema(offer_schema):
            with pytest.raises(AggregationError, match="collides with group_by"):
                await engine.execute_aggregate(
                    entity_type="offer",
                    project_gid="proj-1",
                    client=mock_client,
                    request=request,
                )

    async def test_response_format_data_is_list_of_dicts(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """Response data is a list of dicts with correct keys."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "vertical": ["dental", "dental", "medical"],
                "section": ["A", "B", "C"],
                "mrr": ["100", "200", "300"],
                "cost": ["10", "20", "30"],
                "amount": [1.0, 2.0, 3.0],
                "quantity": [1, 2, 3],
                "is_active": [True, False, True],
                "created_date": [None, None, None],
                "platforms": [["fb"], ["g"], ["fb"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [
                    {"column": "amount", "agg": "sum", "alias": "total"},
                    {"column": "gid", "agg": "count", "alias": "cnt"},
                ],
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert isinstance(result.data, list)
        for row in result.data:
            assert isinstance(row, dict)
            assert "vertical" in row
            assert "total" in row
            assert "cnt" in row

        assert result.meta.group_count == len(result.data)
        assert result.meta.aggregation_count == 2

    async def test_meta_has_group_count(
        self,
        mock_client: AsyncMock,
        offer_schema: DataFrameSchema,
    ) -> None:
        """AggregateMeta includes group_count matching actual data length."""
        df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "vertical": ["dental", "medical"],
                "section": ["A", "B"],
                "mrr": ["100", "200"],
                "cost": ["10", "20"],
                "amount": [1.0, 2.0],
                "quantity": [1, 2],
                "is_active": [True, False],
                "created_date": [None, None],
                "platforms": [["fb"], ["g"]],
            }
        )
        engine = _make_engine(df)

        request = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
            }
        )
        with _patch_schema(offer_schema):
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid="proj-1",
                client=mock_client,
                request=request,
            )

        assert result.meta.group_count == 2
        assert result.meta.group_count == len(result.data)
        assert result.meta.query_ms >= 0
        assert result.meta.entity_type == "offer"
        assert result.meta.project_gid == "proj-1"


# ===========================================================================
# 6. API Endpoint Edge Cases (via model validation, no TestClient needed)
# ===========================================================================


class TestAPIEndpointEdgeCases:
    """Adversarial tests for the aggregate API request validation layer."""

    def test_empty_body_rejected(self) -> None:
        """POST /aggregate with empty body fails Pydantic validation (missing required fields)."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate({})

    def test_valid_entity_type_invalid_aggregations(self) -> None:
        """Valid entity_type but invalid agg function rejected."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                    "aggregations": [{"column": "gid", "agg": "INVALID_FUNC"}],
                }
            )

    def test_where_flat_array_sugar(self) -> None:
        """WHERE provided as flat array is auto-wrapped to AND group."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
                "where": [
                    {"field": "name", "op": "eq", "value": "test"},
                ],
            }
        )
        assert req.where is not None

    def test_where_empty_array_becomes_none(self) -> None:
        """WHERE provided as empty array becomes None."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
                "where": [],
            }
        )
        assert req.where is None

    def test_aggregate_request_missing_group_by(self) -> None:
        """Missing group_by field rejected."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "aggregations": [{"column": "gid", "agg": "count"}],
                }
            )

    def test_aggregate_request_missing_aggregations(self) -> None:
        """Missing aggregations field rejected."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                }
            )


# ===========================================================================
# 7. Numeric Casting Adversarial (ADR-AGG-005)
# ===========================================================================


class TestNumericCastingAdversarial:
    """Adversarial tests for Utf8 -> Float64 casting in aggregation."""

    def test_utf8_mix_numeric_and_nonnumeric(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 column with mix of numeric and non-numeric strings:
        non-numeric become null, sum ignores nulls."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["100.5", "not_a_number", "200.5"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # "not_a_number" -> null via strict=False, sum ignores null
        assert result["total"].to_list() == [pytest.approx(301.0)]

    def test_utf8_all_nonnumeric_strings(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 column with ALL non-numeric strings: sum produces 0.0."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "mrr": ["abc", "def"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # All cast to null, sum of nulls = 0.0
        assert result["total"].to_list() == [0.0]

    def test_utf8_empty_strings_become_null(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 column with empty strings: empty strings become null after cast."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["", "100", ""],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # "" -> null via Float64 cast, sum = 100.0
        assert result["total"].to_list() == [100.0]

    def test_utf8_mean_with_nonnumeric(self, offer_schema: DataFrameSchema) -> None:
        """mean on Utf8 column with non-numeric strings: nulls ignored in mean."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.MEAN, alias="avg")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["100", "bad", "200"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # mean of [100.0, null, 200.0] = 150.0 (null excluded)
        assert result["avg"].to_list() == [150.0]

    def test_utf8_min_max_with_nonnumeric(self, offer_schema: DataFrameSchema) -> None:
        """min/max on Utf8 column with non-numeric strings: nulls ignored."""
        compiler = AggregationCompiler()
        spec_min = AggSpec(column="mrr", agg=AggFunction.MIN, alias="min_mrr")
        spec_max = AggSpec(column="mrr", agg=AggFunction.MAX, alias="max_mrr")
        exprs = compiler.compile([spec_min, spec_max], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["100", "bad", "300"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        assert result["min_mrr"].to_list() == [100.0]
        assert result["max_mrr"].to_list() == [300.0]

    def test_utf8_count_does_not_cast(self, offer_schema: DataFrameSchema) -> None:
        """count on Utf8 column does NOT cast -- counts all non-null values including non-numeric."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT, alias="cnt")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["100", "bad", None],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # count counts non-null: "100" and "bad" are non-null, None is excluded
        assert result["cnt"].to_list() == [2]

    def test_utf8_count_distinct_does_not_cast(self, offer_schema: DataFrameSchema) -> None:
        """count_distinct on Utf8 column does NOT cast -- counts unique string values."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.COUNT_DISTINCT, alias="uniq")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental", "dental", "dental"],
                "mrr": ["100", "100", "bad", None],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # "100", "bad", null = 3 distinct
        assert result["uniq"].to_list() == [3]

    def test_utf8_sum_preserves_decimal_precision(self, offer_schema: DataFrameSchema) -> None:
        """Utf8 sum preserves decimal precision within Float64 limits."""
        compiler = AggregationCompiler()
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
        exprs = compiler.compile([spec], offer_schema)

        df = pl.DataFrame(
            {
                "vertical": ["dental", "dental"],
                "mrr": ["0.1", "0.2"],
            }
        )
        result = df.group_by("vertical").agg(exprs)
        # Float64 addition: 0.1 + 0.2 ~ 0.3 (within floating point tolerance)
        assert result["total"].to_list() == [pytest.approx(0.3)]


# ===========================================================================
# 8. Error Serialization
# ===========================================================================


class TestErrorSerialization:
    """Verify error classes serialize to expected JSON shapes."""

    def test_aggregation_error_to_dict(self) -> None:
        """AggregationError serializes with correct error code."""
        err = AggregationError(message="test error")
        d = err.to_dict()
        assert d["error"] == "AGGREGATION_ERROR"
        assert d["message"] == "test error"

    def test_aggregate_group_limit_error_to_dict(self) -> None:
        """AggregateGroupLimitError serializes with group_count and max_groups."""
        err = AggregateGroupLimitError(group_count=20000, max_groups=10000)
        d = err.to_dict()
        assert d["error"] == "TOO_MANY_GROUPS"
        assert d["group_count"] == 20000
        assert d["max_groups"] == 10000
        assert "20000" in d["message"]
        assert "10000" in d["message"]

    def test_aggregation_error_is_query_engine_error(self) -> None:
        """AggregationError is a subclass of QueryEngineError."""
        from autom8_asana.query.errors import QueryEngineError

        err = AggregationError(message="test")
        assert isinstance(err, QueryEngineError)

    def test_aggregate_group_limit_error_is_query_engine_error(self) -> None:
        """AggregateGroupLimitError is a subclass of QueryEngineError."""
        from autom8_asana.query.errors import QueryEngineError

        err = AggregateGroupLimitError(group_count=1, max_groups=1)
        assert isinstance(err, QueryEngineError)


# ===========================================================================
# 9. Post-Aggregation Schema Adversarial
# ===========================================================================


class TestPostAggSchemaAdversarial:
    """Adversarial tests for build_post_agg_schema edge cases."""

    def test_schema_includes_all_group_by_and_agg_columns(
        self,
        offer_schema: DataFrameSchema,
    ) -> None:
        """Post-agg schema includes both group_by columns and all agg aliases."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="cnt"),
            AggSpec(column="amount", agg=AggFunction.MEAN, alias="avg"),
        ]
        schema = build_post_agg_schema(
            group_by_columns=["vertical", "section"],
            agg_specs=specs,
            source_schema=offer_schema,
        )
        col_names = schema.column_names()
        assert "vertical" in col_names
        assert "section" in col_names
        assert "total" in col_names
        assert "cnt" in col_names
        assert "avg" in col_names

    def test_post_agg_schema_sum_int64_infers_int64(
        self,
        offer_schema: DataFrameSchema,
    ) -> None:
        """sum on Int64 column infers Int64 output (not Float64)."""
        spec = AggSpec(column="quantity", agg=AggFunction.SUM, alias="total_qty")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("total_qty")
        assert col is not None
        assert col.dtype == "Int64"

    def test_post_agg_schema_sum_utf8_infers_float64(
        self,
        offer_schema: DataFrameSchema,
    ) -> None:
        """sum on Utf8 column (financial) infers Float64 output."""
        spec = AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("total_mrr")
        assert col is not None
        assert col.dtype == "Float64"

    def test_post_agg_schema_min_date_retains_date(
        self,
        offer_schema: DataFrameSchema,
    ) -> None:
        """min on Date column retains Date output dtype."""
        spec = AggSpec(column="created_date", agg=AggFunction.MIN, alias="earliest")
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=[spec],
            source_schema=offer_schema,
        )
        col = schema.get_column("earliest")
        assert col is not None
        assert col.dtype == "Date"

    def test_post_agg_schema_all_agg_columns_are_nullable(
        self,
        offer_schema: DataFrameSchema,
    ) -> None:
        """All aggregation output columns in post-agg schema are nullable."""
        specs = [
            AggSpec(column="amount", agg=AggFunction.SUM, alias="total"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="cnt"),
        ]
        schema = build_post_agg_schema(
            group_by_columns=["vertical"],
            agg_specs=specs,
            source_schema=offer_schema,
        )
        for spec in specs:
            col = schema.get_column(spec.resolved_alias)
            assert col is not None
            assert col.nullable is True
