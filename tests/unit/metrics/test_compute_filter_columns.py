"""Regression tests: filters may reference columns outside the projection.

SCAR-METRICS-SELECT-FILTER-001: compute_metric projected to
(name, dedup keys, metric column) before applying filter_expr, so any
filter referencing another column raised ColumnNotFoundError.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from autom8_asana.metrics.compute import compute_metric
from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry


def _metric(
    *,
    filter_expr: pl.Expr | None = None,
    pre_filters: list[pl.Expr] | None = None,
    dedup_keys: list[str] | None = None,
) -> Metric:
    return Metric(
        name="test_filter_cols",
        description="filter on unselected column",
        expr=MetricExpr(name="sum_val", column="val", agg="sum", filter_expr=filter_expr),
        scope=Scope(entity_type="test", dedup_keys=dedup_keys, pre_filters=pre_filters),
    )


class TestFilterOnUnselectedColumn:
    def test_filter_expr_references_unselected_column(self) -> None:
        df = pl.DataFrame(
            {
                "name": ["a", "b", "c"],
                "val": [10, 20, 30],
                "status": ["keep", "drop", "keep"],
            }
        )
        result = compute_metric(_metric(filter_expr=pl.col("status") == "keep"), df)
        assert result["val"].sum() == 40
        assert result.height == 2

    def test_pre_filter_references_unselected_column(self) -> None:
        df = pl.DataFrame({"name": ["a", "b"], "val": [10, 20], "flag": [True, False]})
        result = compute_metric(_metric(pre_filters=[pl.col("flag")]), df)
        assert result["val"].to_list() == [10]

    def test_filter_on_unselected_column_with_dedup(self) -> None:
        df = pl.DataFrame(
            {
                "name": ["a", "b", "c"],
                "key": ["k1", "k1", "k2"],
                "val": [1, 2, 3],
                "status": ["drop", "keep", "keep"],
            }
        )
        result = compute_metric(
            _metric(filter_expr=pl.col("status") == "keep", dedup_keys=["key"]), df
        )
        assert result["key"].to_list() == ["k1", "k2"]
        assert result["val"].to_list() == [2, 3]

    def test_output_columns_unchanged(self) -> None:
        df = pl.DataFrame({"name": ["a"], "val": [1], "status": ["keep"]})
        result = compute_metric(_metric(filter_expr=pl.col("status") == "keep"), df)
        assert result.columns == ["name", "val"]


def _frame_for_all_metrics() -> pl.DataFrame:
    """Minimal frame containing every column any registered metric needs."""
    now = datetime.now(UTC)
    old = now - timedelta(days=90)
    return pl.DataFrame(
        {
            "name": ["r1", "r2"],
            "section": ["active", "active"],
            "office_phone": ["p1", "p2"],
            "vertical": ["v1", "v2"],
            "mrr": ["100", "200"],
            "weekly_ad_spend": ["10", "20"],
            "entity_gid": ["g1", "g2"],
            "from_stage": ["outreach", "sales"],
            "to_stage": ["sales", "onboarding"],
            "transition_type": ["converted", "converted"],
            "duration_days": [1.0, 2.0],
            "entered_at": [old, old],
            "exited_at": [None, now],
        },
        schema_overrides={"exited_at": pl.Datetime(time_zone="UTC")},
    )


_ALL_METRICS = MetricRegistry().list_metrics()


def test_registry_is_populated() -> None:
    assert len(_ALL_METRICS) >= 9


@pytest.mark.parametrize("metric_name", _ALL_METRICS)
def test_every_registered_metric_computes(metric_name: str) -> None:
    metric = MetricRegistry().get_metric(metric_name)
    result = compute_metric(metric, _frame_for_all_metrics())
    assert isinstance(result, pl.DataFrame)
    assert metric.expr.column in result.columns
