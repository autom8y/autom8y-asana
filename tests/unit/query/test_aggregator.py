"""Tests for query/aggregator.py: AggregationCompiler, dtype validation, HAVING schema.

Covers TDD Section 11.3 (TC-AC001 through TC-AC013)
and Section 11.4 (TC-AH001 through TC-AH006).
"""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.aggregator import (
    AGG_COMPATIBILITY,
    AggregationCompiler,
    build_post_agg_schema,
    validate_alias_uniqueness,
)
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.errors import (
    AggregationError,
    InvalidOperatorError,
    UnknownFieldError,
)
from autom8_asana.query.models import AggFunction, AggSpec

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
