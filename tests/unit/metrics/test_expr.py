"""Unit tests for MetricExpr."""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.metrics.expr import SUPPORTED_AGGS, MetricExpr


class TestMetricExprCreation:
    """Test MetricExpr construction and validation."""

    def test_basic_creation(self) -> None:
        expr = MetricExpr(name="sum_mrr", column="mrr", agg="sum")
        assert expr.name == "sum_mrr"
        assert expr.column == "mrr"
        assert expr.agg == "sum"
        assert expr.cast_dtype is None
        assert expr.filter_expr is None

    def test_creation_with_all_fields(self) -> None:
        filter_expr = pl.col("mrr").is_not_null()
        expr = MetricExpr(
            name="sum_mrr",
            column="mrr",
            cast_dtype=pl.Float64,
            agg="sum",
            filter_expr=filter_expr,
        )
        assert expr.cast_dtype == pl.Float64
        assert expr.filter_expr is not None

    def test_invalid_agg_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported aggregation 'median'"):
            MetricExpr(name="bad", column="col", agg="median")

    def test_frozen_cannot_mutate(self) -> None:
        expr = MetricExpr(name="sum_mrr", column="mrr", agg="sum")
        with pytest.raises(AttributeError):
            expr.name = "changed"  # type: ignore[misc]

    def test_all_supported_aggs_accepted(self) -> None:
        for agg in SUPPORTED_AGGS:
            expr = MetricExpr(name=f"test_{agg}", column="col", agg=agg)
            assert expr.agg == agg


class TestMetricExprToPolars:
    """Test to_polars_expr() output."""

    def test_sum_without_cast(self) -> None:
        expr = MetricExpr(name="sum_val", column="val", agg="sum")
        df = pl.DataFrame({"val": [1, 2, 3]})
        result = df.select(expr.to_polars_expr())
        assert result["sum_val"][0] == 6

    def test_sum_with_cast(self) -> None:
        expr = MetricExpr(
            name="sum_mrr", column="mrr", cast_dtype=pl.Float64, agg="sum"
        )
        df = pl.DataFrame({"mrr": ["100", "200", "300"]})
        result = df.select(expr.to_polars_expr())
        assert result["sum_mrr"][0] == 600.0

    def test_count(self) -> None:
        expr = MetricExpr(name="cnt", column="val", agg="count")
        df = pl.DataFrame({"val": [1, 2, None]})
        result = df.select(expr.to_polars_expr())
        # Polars count() excludes nulls
        assert result["cnt"][0] == 2

    def test_mean(self) -> None:
        expr = MetricExpr(name="avg", column="val", agg="mean")
        df = pl.DataFrame({"val": [10.0, 20.0, 30.0]})
        result = df.select(expr.to_polars_expr())
        assert result["avg"][0] == pytest.approx(20.0)

    def test_min_max(self) -> None:
        expr_min = MetricExpr(name="lo", column="val", agg="min")
        expr_max = MetricExpr(name="hi", column="val", agg="max")
        df = pl.DataFrame({"val": [5, 1, 9]})
        assert df.select(expr_min.to_polars_expr())["lo"][0] == 1
        assert df.select(expr_max.to_polars_expr())["hi"][0] == 9

    def test_cast_strict_false_handles_non_numeric(self) -> None:
        """Non-numeric strings become null with strict=False."""
        expr = MetricExpr(
            name="sum_mrr", column="mrr", cast_dtype=pl.Float64, agg="sum"
        )
        df = pl.DataFrame({"mrr": ["100", "not_a_number", "200"]})
        result = df.select(expr.to_polars_expr())
        assert result["sum_mrr"][0] == 300.0

    def test_alias_is_name(self) -> None:
        expr = MetricExpr(name="my_alias", column="val", agg="sum")
        df = pl.DataFrame({"val": [1]})
        result = df.select(expr.to_polars_expr())
        assert "my_alias" in result.columns
