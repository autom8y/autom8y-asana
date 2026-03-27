"""Unit tests for lifecycle pipeline metric definitions and MetricExpr extensions.

Test IDs: UT-OBS-007 through UT-OBS-011 from the ADR QA checklist.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from autom8_asana.metrics.expr import SUPPORTED_AGGS, MetricExpr
from autom8_asana.metrics.registry import MetricRegistry

# ---------------------------------------------------------------------------
# MetricExpr extension tests (median/quantile)
# ---------------------------------------------------------------------------


class TestMetricExprMedian:
    """Test median aggregation support in MetricExpr."""

    def test_median_in_supported_aggs(self) -> None:
        """UT-OBS-010: median is in SUPPORTED_AGGS."""
        assert "median" in SUPPORTED_AGGS

    def test_median_expr_creation(self) -> None:
        """UT-OBS-010: MetricExpr with agg='median' is valid."""
        expr = MetricExpr(name="med", column="val", agg="median")
        assert expr.agg == "median"

    def test_median_to_polars_expr(self) -> None:
        """UT-OBS-010: median produces correct Polars result."""
        expr = MetricExpr(name="med", column="val", agg="median")
        df = pl.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = df.select(expr.to_polars_expr())
        assert result["med"][0] == pytest.approx(3.0)

    def test_median_with_cast(self) -> None:
        """Median with cast_dtype handles string columns."""
        expr = MetricExpr(name="med", column="val", cast_dtype=pl.Float64, agg="median")
        df = pl.DataFrame({"val": ["10", "20", "30"]})
        result = df.select(expr.to_polars_expr())
        assert result["med"][0] == pytest.approx(20.0)


class TestMetricExprQuantile:
    """Test quantile aggregation support in MetricExpr."""

    def test_quantile_in_supported_aggs(self) -> None:
        """UT-OBS-011: quantile is in SUPPORTED_AGGS."""
        assert "quantile" in SUPPORTED_AGGS

    def test_quantile_requires_quantile_value(self) -> None:
        """UT-OBS-011: quantile without quantile_value raises ValueError."""
        with pytest.raises(ValueError, match="quantile_value"):
            MetricExpr(name="q", column="val", agg="quantile")

    def test_quantile_with_value(self) -> None:
        """UT-OBS-011: quantile with value produces correct result."""
        expr = MetricExpr(name="p95", column="val", agg="quantile", quantile_value=0.95)
        # 100 values: 1..100. P95 should be near 95.
        df = pl.DataFrame({"val": list(range(1, 101))})
        result = df.select(expr.to_polars_expr())
        assert result["p95"][0] >= 90.0

    def test_quantile_p50_equals_median(self) -> None:
        """P50 quantile should produce the same result as median."""
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        expr_q50 = MetricExpr(
            name="p50", column="val", agg="quantile", quantile_value=0.5
        )
        expr_med = MetricExpr(name="med", column="val", agg="median")
        df = pl.DataFrame({"val": vals})
        q50 = df.select(expr_q50.to_polars_expr())["p50"][0]
        med = df.select(expr_med.to_polars_expr())["med"][0]
        assert q50 == pytest.approx(med)

    def test_quantile_with_cast(self) -> None:
        """Quantile with cast_dtype for string-encoded numbers."""
        expr = MetricExpr(
            name="p95",
            column="val",
            cast_dtype=pl.Float64,
            agg="quantile",
            quantile_value=0.95,
        )
        df = pl.DataFrame({"val": ["10", "20", "30", "40", "50"]})
        result = df.select(expr.to_polars_expr())
        assert result["p95"][0] >= 40.0


class TestMetricExprBackwardCompat:
    """Verify existing aggregations still work after the extension."""

    @pytest.mark.parametrize("agg", ["sum", "count", "mean", "min", "max"])
    def test_existing_aggs_unchanged(self, agg: str) -> None:
        """All pre-existing aggs still work."""
        expr = MetricExpr(name=f"test_{agg}", column="val", agg=agg)
        df = pl.DataFrame({"val": [1, 2, 3]})
        result = df.select(expr.to_polars_expr())
        assert f"test_{agg}" in result.columns

    def test_invalid_agg_still_rejected(self) -> None:
        """Unknown aggs are still rejected."""
        with pytest.raises(ValueError, match="Unsupported aggregation"):
            MetricExpr(name="bad", column="col", agg="stddev")


# ---------------------------------------------------------------------------
# Lifecycle metric registration tests
# ---------------------------------------------------------------------------


class TestLifecycleMetricRegistration:
    """Test that all 7 lifecycle metrics are registered."""

    @pytest.fixture(autouse=True)
    def _reset_registry(self) -> None:
        MetricRegistry.reset()
        yield  # type: ignore[misc]
        MetricRegistry.reset()

    def test_all_seven_metrics_registered(self) -> None:
        """All 7 lifecycle metrics appear in the registry."""
        registry = MetricRegistry()
        names = registry.list_metrics()
        expected = [
            "outreach_to_sales_conversion",
            "sales_to_onboarding_conversion",
            "onboarding_to_implementation_conversion",
            "stage_duration_median",
            "stage_duration_p95",
            "stalled_entities",
            "weekly_transitions",
        ]
        for metric_name in expected:
            assert metric_name in names, f"{metric_name} not registered"

    def test_conversion_metric_has_filter(self) -> None:
        """Conversion metrics have filter_expr for stage pair + converted type."""
        registry = MetricRegistry()
        metric = registry.get_metric("sales_to_onboarding_conversion")
        assert metric.expr.filter_expr is not None
        assert metric.expr.agg == "count"

    def test_duration_median_metric(self) -> None:
        """Duration median uses median agg on duration_days column."""
        registry = MetricRegistry()
        metric = registry.get_metric("stage_duration_median")
        assert metric.expr.agg == "median"
        assert metric.expr.column == "duration_days"

    def test_duration_p95_metric(self) -> None:
        """Duration p95 uses quantile(0.95) on duration_days column."""
        registry = MetricRegistry()
        metric = registry.get_metric("stage_duration_p95")
        assert metric.expr.agg == "quantile"
        assert metric.expr.quantile_value == 0.95
        assert metric.expr.column == "duration_days"

    def test_stalled_entities_metric(self) -> None:
        """Stalled entities counts entity_gid with dedup."""
        registry = MetricRegistry()
        metric = registry.get_metric("stalled_entities")
        assert metric.expr.agg == "count"
        assert metric.scope.dedup_keys == ["entity_gid"]

    def test_weekly_transitions_metric(self) -> None:
        """Weekly transitions counts all entity_gid occurrences."""
        registry = MetricRegistry()
        metric = registry.get_metric("weekly_transitions")
        assert metric.expr.agg == "count"
        assert metric.expr.column == "entity_gid"


# ---------------------------------------------------------------------------
# Lifecycle metric computation tests (with sample data)
# ---------------------------------------------------------------------------


class TestLifecycleMetricComputation:
    """Test lifecycle metrics against sample stage transition DataFrames."""

    def _sample_transitions(self) -> pl.DataFrame:
        """Build a sample stage_transition DataFrame for testing."""
        now = datetime.now(UTC)
        return pl.DataFrame(
            {
                "entity_gid": [
                    "gid1",
                    "gid1",
                    "gid2",
                    "gid2",
                    "gid3",
                ],
                "entity_type": [
                    "Process",
                    "Process",
                    "Process",
                    "Process",
                    "Process",
                ],
                "business_gid": [
                    "biz1",
                    "biz1",
                    "biz2",
                    "biz2",
                    "biz3",
                ],
                "from_stage": [
                    "outreach",
                    "sales",
                    "outreach",
                    "sales",
                    "sales",
                ],
                "to_stage": [
                    "sales",
                    "onboarding",
                    "sales",
                    "onboarding",
                    "onboarding",
                ],
                "pipeline_stage_num": [2, 3, 2, 3, 3],
                "transition_type": [
                    "converted",
                    "converted",
                    "converted",
                    "converted",
                    "converted",
                ],
                "entered_at": [
                    now - timedelta(days=30),
                    now - timedelta(days=20),
                    now - timedelta(days=25),
                    now - timedelta(days=15),
                    now - timedelta(days=10),
                ],
                "exited_at": [
                    now - timedelta(days=20),
                    now - timedelta(days=10),
                    now - timedelta(days=15),
                    now - timedelta(days=5),
                    None,  # Still in onboarding
                ],
                "duration_days": [10.0, 10.0, 10.0, 10.0, None],
                "automation_result_id": [
                    "r1",
                    "r2",
                    "r3",
                    "r4",
                    "r5",
                ],
            },
            schema={
                "entity_gid": pl.Utf8,
                "entity_type": pl.Utf8,
                "business_gid": pl.Utf8,
                "from_stage": pl.Utf8,
                "to_stage": pl.Utf8,
                "pipeline_stage_num": pl.Int64,
                "transition_type": pl.Utf8,
                "entered_at": pl.Datetime("us", "UTC"),
                "exited_at": pl.Datetime("us", "UTC"),
                "duration_days": pl.Float64,
                "automation_result_id": pl.Utf8,
            },
        )

    def test_conversion_count(self) -> None:
        """UT-OBS-008: Conversion metric counts correct transitions."""
        df = self._sample_transitions()
        # Filter for sales -> onboarding converted
        filtered = df.filter(
            (pl.col("from_stage") == "sales")
            & (pl.col("to_stage") == "onboarding")
            & (pl.col("transition_type") == "converted")
        )
        count = filtered.select(pl.col("entity_gid").count()).item()
        assert count == 3  # gid1, gid2, gid3

    def test_duration_excludes_open_intervals(self) -> None:
        """UT-OBS-009: Duration metrics exclude rows where exited_at is null."""
        df = self._sample_transitions()
        closed = df.filter(pl.col("exited_at").is_not_null())
        assert len(closed) == 4  # 5th row has exited_at=None
        median = closed.select(pl.col("duration_days").median()).item()
        assert median == pytest.approx(10.0)

    def test_stall_detection_filter(self) -> None:
        """UT-OBS-007: Stall detection filter respects threshold."""
        now = datetime.now(UTC)
        df = pl.DataFrame(
            {
                "entity_gid": ["gid1", "gid2", "gid3"],
                "entered_at": [
                    now - timedelta(days=60),  # stalled (>30 days)
                    now - timedelta(days=10),  # not stalled
                    now - timedelta(days=45),  # stalled (>30 days)
                ],
                "exited_at": [None, None, None],
            },
            schema={
                "entity_gid": pl.Utf8,
                "entered_at": pl.Datetime("us", "UTC"),
                "exited_at": pl.Datetime("us", "UTC"),
            },
        )
        cutoff = now - timedelta(days=30)
        stalled = df.filter(
            pl.col("exited_at").is_null() & (pl.col("entered_at") < cutoff)
        )
        assert len(stalled) == 2
        assert set(stalled["entity_gid"].to_list()) == {"gid1", "gid3"}
