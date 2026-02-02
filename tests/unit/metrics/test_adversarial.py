"""Adversarial tests for the metrics layer.

QA Adversary validation: edge cases, error paths, boundary conditions,
and integration points for MetricExpr, Scope, Metric, MetricRegistry,
and compute_metric.
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

import pytest
import polars as pl

from autom8_asana.metrics.compute import compute_metric
from autom8_asana.metrics.expr import SUPPORTED_AGGS, MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metric(
    column: str = "val",
    *,
    name: str | None = None,
    cast_dtype: pl.DataType | None = None,
    agg: str = "sum",
    filter_expr: pl.Expr | None = None,
    dedup_keys: list[str] | None = None,
    pre_filters: list[pl.Expr] | None = None,
) -> Metric:
    mname = name or f"test_{column}"
    return Metric(
        name=mname,
        description=f"Test metric {mname}",
        expr=MetricExpr(
            name=f"{agg}_{column}",
            column=column,
            cast_dtype=cast_dtype,
            agg=agg,
            filter_expr=filter_expr,
        ),
        scope=Scope(
            entity_type="test",
            section="999",
            dedup_keys=dedup_keys,
            pre_filters=pre_filters,
        ),
    )


# ===========================================================================
# 1. MetricExpr Adversarial Tests
# ===========================================================================

class TestMetricExprAdversarial:
    """Adversarial tests for MetricExpr edge cases."""

    def test_empty_string_agg_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unsupported aggregation"):
            MetricExpr(name="x", column="c", agg="")

    def test_whitespace_agg_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unsupported aggregation"):
            MetricExpr(name="x", column="c", agg=" sum ")

    def test_case_sensitive_agg(self) -> None:
        """Agg names must be exact lowercase."""
        with pytest.raises(ValueError):
            MetricExpr(name="x", column="c", agg="SUM")
        with pytest.raises(ValueError):
            MetricExpr(name="x", column="c", agg="Sum")

    def test_sql_injection_agg(self) -> None:
        """Attempting SQL injection via agg field is rejected."""
        with pytest.raises(ValueError, match="Unsupported aggregation"):
            MetricExpr(name="x", column="c", agg="sum; DROP TABLE")

    def test_getattr_attack_agg(self) -> None:
        """Agg field uses getattr on Polars expr -- ensure only safe names pass."""
        # __class__ exists as an attribute on pl.Expr but is not in SUPPORTED_AGGS
        with pytest.raises(ValueError, match="Unsupported aggregation"):
            MetricExpr(name="x", column="c", agg="__class__")

    def test_to_polars_expr_all_nulls(self) -> None:
        """Sum of an all-null column should return null, not error."""
        expr = MetricExpr(name="s", column="val", cast_dtype=pl.Float64, agg="sum")
        df = pl.DataFrame({"val": [None, None, None]})
        result = df.select(expr.to_polars_expr())
        assert result["s"][0] is None or result["s"][0] == 0.0

    def test_to_polars_expr_empty_df(self) -> None:
        """Aggregation on empty DataFrame should not raise."""
        expr = MetricExpr(name="s", column="val", agg="sum")
        df = pl.DataFrame({"val": pl.Series([], dtype=pl.Int64)})
        result = df.select(expr.to_polars_expr())
        assert result["s"][0] == 0 or result["s"][0] is None

    def test_cast_from_mixed_types(self) -> None:
        """Cast handles string column with mixed numeric/non-numeric gracefully."""
        expr = MetricExpr(name="s", column="val", cast_dtype=pl.Float64, agg="sum")
        df = pl.DataFrame({"val": ["100", "abc", "200", "", None]})
        result = df.select(expr.to_polars_expr())
        # "abc" and "" become null; sum of 100 + 200 = 300
        assert result["s"][0] == 300.0

    def test_very_large_values(self) -> None:
        """Large financial values do not overflow Float64."""
        expr = MetricExpr(name="s", column="val", cast_dtype=pl.Float64, agg="sum")
        df = pl.DataFrame({"val": [1e15, 2e15, 3e15]})
        result = df.select(expr.to_polars_expr())
        assert result["s"][0] == pytest.approx(6e15)

    def test_negative_values(self) -> None:
        """Negative numbers handled correctly in sum."""
        expr = MetricExpr(name="s", column="val", agg="sum")
        df = pl.DataFrame({"val": [-10, 20, -5]})
        result = df.select(expr.to_polars_expr())
        assert result["s"][0] == 5


# ===========================================================================
# 2. compute_metric Adversarial Tests
# ===========================================================================

class TestComputeAdversarial:
    """Adversarial tests for compute_metric edge cases."""

    def test_empty_df_after_filter(self) -> None:
        """Filter removes ALL rows -> empty result, no crash."""
        df = pl.DataFrame({
            "name": ["a", "b"],
            "val": [0, 0],
        })
        m = _metric("val", filter_expr=pl.col("val") > 100)
        result = compute_metric(m, df)
        assert len(result) == 0
        assert result["val"].sum() == 0

    def test_all_null_column(self) -> None:
        """Column exists but all values are None."""
        df = pl.DataFrame({
            "name": ["a", "b", "c"],
            "val": [None, None, None],
        }).cast({"val": pl.Float64})
        m = _metric("val")
        result = compute_metric(m, df)
        assert len(result) == 3
        # sum of all nulls
        total = result["val"].sum()
        assert total == 0.0 or total is None

    def test_all_null_column_with_filter_gt_zero(self) -> None:
        """All-null column with > 0 filter -> empty result."""
        df = pl.DataFrame({
            "name": ["a", "b"],
            "val": [None, None],
        }).cast({"val": pl.Float64})
        m = _metric(
            "val",
            filter_expr=pl.col("val").is_not_null() & (pl.col("val") > 0),
        )
        result = compute_metric(m, df)
        assert len(result) == 0

    def test_missing_metric_column_raises(self) -> None:
        """DataFrame lacks the metric column entirely."""
        df = pl.DataFrame({"name": ["a"], "other": [1]})
        m = _metric("nonexistent")
        with pytest.raises(Exception):  # ColumnNotFoundError or SchemaError
            compute_metric(m, df)

    def test_missing_dedup_key_column_raises(self) -> None:
        """DataFrame lacks a dedup_key column."""
        df = pl.DataFrame({"name": ["a"], "val": [1]})
        m = _metric("val", dedup_keys=["missing_key"])
        with pytest.raises(Exception):
            compute_metric(m, df)

    def test_dedup_with_nulls_in_dedup_keys(self) -> None:
        """Null values in dedup keys should still work (each null is unique or grouped)."""
        df = pl.DataFrame({
            "name": ["a", "b", "c"],
            "key": [None, None, "x"],
            "val": [10, 20, 30],
        })
        m = _metric("val", dedup_keys=["key"])
        result = compute_metric(m, df)
        # Polars unique with null: nulls may be grouped as one
        assert len(result) <= 3
        assert len(result) >= 2  # at least "x" and one null group

    def test_single_row_df(self) -> None:
        """Single-row DataFrame."""
        df = pl.DataFrame({"name": ["a"], "val": [42]})
        m = _metric("val")
        result = compute_metric(m, df)
        assert len(result) == 1
        assert result["val"][0] == 42

    def test_duplicate_column_in_dedup_keys_and_metric(self) -> None:
        """Metric column also appears in dedup_keys -> no duplicate column error."""
        df = pl.DataFrame({
            "name": ["a", "b"],
            "val": [10, 20],
        })
        m = _metric("val", dedup_keys=["val"])
        result = compute_metric(m, df)
        # Both are unique by val
        assert len(result) == 2

    def test_name_column_absent(self) -> None:
        """If 'name' column is absent, compute_metric should still work."""
        df = pl.DataFrame({"val": [10, 20, 30]})
        m = _metric("val")
        result = compute_metric(m, df)
        assert result["val"].sum() == 60
        assert "name" not in result.columns

    def test_very_wide_dataframe(self) -> None:
        """DataFrame with many extra columns -- compute_metric selects only needed ones."""
        data = {f"col_{i}": [i] for i in range(100)}
        data["name"] = ["a"]
        data["val"] = [42]
        df = pl.DataFrame(data)
        m = _metric("val")
        result = compute_metric(m, df)
        # Should only have name + val
        assert set(result.columns) == {"name", "val"}
        assert result["val"][0] == 42

    def test_cast_then_filter_order(self) -> None:
        """Cast happens before filter -- filter on cast-result should work."""
        df = pl.DataFrame({
            "name": ["a", "b", "c"],
            "val": ["100", "not_num", "200"],
        })
        m = _metric(
            "val",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("val").is_not_null() & (pl.col("val") > 0),
        )
        result = compute_metric(m, df)
        # "not_num" cast to null -> filtered out
        assert len(result) == 2
        assert result["val"].sum() == 300.0

    def test_pre_filters_and_expr_filter_combined(self) -> None:
        """Both filter_expr and pre_filters apply.

        Note: pre_filters can only reference columns that compute_metric selects
        (name, dedup_keys, metric column). Use dedup_keys to include extra columns.
        """
        df = pl.DataFrame({
            "name": ["a", "b", "c", "d"],
            "cat": ["x", "x", "y", "y"],
            "val": [10.0, 20.0, 30.0, 40.0],
        })
        m = _metric(
            "val",
            filter_expr=pl.col("val") > 15,
            pre_filters=[pl.col("cat") == "x"],
            dedup_keys=["cat"],  # include "cat" in selected columns
        )
        result = compute_metric(m, df)
        # cat == "x": a(10), b(20). Then val > 15: only b(20)
        # But dedup on "cat" keeps only one "x" row, so result is 1 row
        assert len(result) == 1
        assert result["val"][0] == 20.0

    def test_verbose_does_not_affect_result(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """verbose=True prints but returns same data as verbose=False."""
        df = pl.DataFrame({"name": ["a", "b"], "val": [10, 20]})
        m = _metric("val")
        r1 = compute_metric(m, df, verbose=False)
        r2 = compute_metric(m, df, verbose=True)
        captured = capsys.readouterr()
        assert len(captured.out) > 0  # something was printed
        assert r1["val"].to_list() == r2["val"].to_list()


# ===========================================================================
# 3. Registry Adversarial Tests
# ===========================================================================

class TestRegistryAdversarial:
    """Adversarial tests for MetricRegistry."""

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        MetricRegistry.reset()
        yield  # type: ignore[misc]
        MetricRegistry.reset()

    def test_register_empty_name(self) -> None:
        """Metric with empty string name -- helper uses fallback name.

        Empty string is falsy so the helper defaults to 'test_val'.
        This tests that arbitrary names register correctly.
        """
        registry = MetricRegistry()
        registry._initialized = True
        m = Metric(
            name="",
            description="empty name test",
            expr=MetricExpr(name="sum_val", column="val", agg="sum"),
            scope=Scope(entity_type="test"),
        )
        registry.register(m)
        assert registry.get_metric("") is m

    def test_register_special_chars_name(self) -> None:
        """Names with special characters."""
        registry = MetricRegistry()
        registry._initialized = True
        m = _metric("val", name="metric-with-dashes.and.dots!")
        registry.register(m)
        assert registry.get_metric("metric-with-dashes.and.dots!") is m

    def test_get_metric_none_arg(self) -> None:
        """Passing None as metric name -- should raise KeyError, not crash."""
        registry = MetricRegistry()
        registry._initialized = True
        with pytest.raises(KeyError):
            registry.get_metric(None)  # type: ignore[arg-type]

    def test_list_empty_registry(self) -> None:
        """Empty registry returns empty list."""
        registry = MetricRegistry()
        registry._initialized = True
        assert registry.list_metrics() == []

    def test_reset_clears_registered_metrics(self) -> None:
        """After reset, previously registered metrics are gone."""
        registry = MetricRegistry()
        registry._initialized = True
        registry.register(_metric("val", name="ephemeral"))
        MetricRegistry.reset()
        new_registry = MetricRegistry()
        new_registry._initialized = True
        with pytest.raises(KeyError, match="ephemeral"):
            new_registry.get_metric("ephemeral")

    def test_concurrent_reset_and_access(self) -> None:
        """Sequential reset -> access cycle (simulates concurrent pattern)."""
        for _ in range(10):
            MetricRegistry.reset()
            registry = MetricRegistry()
            names = registry.list_metrics()
            assert isinstance(names, list)
            assert "active_mrr" in names

    def test_double_lazy_init(self) -> None:
        """Calling get_metric twice does not double-register."""
        registry = MetricRegistry()
        m1 = registry.get_metric("active_mrr")
        m2 = registry.get_metric("active_mrr")
        assert m1 is m2

    def test_extensibility_new_metric(self) -> None:
        """Register a new metric dynamically and verify discoverability."""
        registry = MetricRegistry()
        # Trigger lazy init first
        _ = registry.list_metrics()
        custom = _metric("custom_col", name="custom_metric_qa")
        registry.register(custom)
        assert "custom_metric_qa" in registry.list_metrics()
        assert registry.get_metric("custom_metric_qa") is custom


# ===========================================================================
# 4. CLI Adversarial Tests
# ===========================================================================

class TestCLIAdversarial:
    """Adversarial tests for scripts/calc_metric.py CLI."""

    def test_cli_no_args(self) -> None:
        """No arguments -> error exit."""
        result = subprocess.run(
            [sys.executable, "scripts/calc_metric.py"],
            capture_output=True, text=True, timeout=30,
            cwd="/Users/tomtenuta/Code/autom8_asana",
        )
        assert result.returncode != 0

    def test_cli_list(self) -> None:
        """--list shows available metrics."""
        result = subprocess.run(
            [sys.executable, "scripts/calc_metric.py", "--list"],
            capture_output=True, text=True, timeout=30,
            cwd="/Users/tomtenuta/Code/autom8_asana",
        )
        assert result.returncode == 0
        assert "active_mrr" in result.stdout
        assert "active_ad_spend" in result.stdout
        assert "Available metrics:" in result.stdout

    def test_cli_unknown_metric(self) -> None:
        """Unknown metric name -> error exit with message."""
        result = subprocess.run(
            [sys.executable, "scripts/calc_metric.py", "nonexistent_metric"],
            capture_output=True, text=True, timeout=30,
            cwd="/Users/tomtenuta/Code/autom8_asana",
            env={**__import__("os").environ, "ASANA_CACHE_S3_BUCKET": "fake-bucket"},
        )
        assert result.returncode != 0
        assert "Unknown metric" in result.stderr or "ERROR" in result.stderr

    def test_cli_no_bucket_env(self) -> None:
        """Missing ASANA_CACHE_S3_BUCKET -> error."""
        import os
        env = {k: v for k, v in os.environ.items() if k != "ASANA_CACHE_S3_BUCKET"}
        result = subprocess.run(
            [sys.executable, "scripts/calc_metric.py", "active_mrr"],
            capture_output=True, text=True, timeout=30,
            cwd="/Users/tomtenuta/Code/autom8_asana",
            env=env,
        )
        assert result.returncode != 0
        assert "ASANA_CACHE_S3_BUCKET" in result.stderr

    def test_cli_help(self) -> None:
        """--help works and documents flags."""
        result = subprocess.run(
            [sys.executable, "scripts/calc_metric.py", "--help"],
            capture_output=True, text=True, timeout=30,
            cwd="/Users/tomtenuta/Code/autom8_asana",
        )
        assert result.returncode == 0
        assert "--verbose" in result.stdout
        assert "--list" in result.stdout
        assert "metric" in result.stdout.lower()

    def test_cli_list_and_metric_name(self) -> None:
        """--list with a metric name should still just list."""
        result = subprocess.run(
            [sys.executable, "scripts/calc_metric.py", "--list", "active_mrr"],
            capture_output=True, text=True, timeout=30,
            cwd="/Users/tomtenuta/Code/autom8_asana",
        )
        # --list should take precedence, or both should work without crash
        assert result.returncode == 0
        assert "active_mrr" in result.stdout


# ===========================================================================
# 5. Import and Module-Level Tests
# ===========================================================================

class TestImportSafety:
    """Verify no import errors or side effects."""

    def test_import_metrics_package(self) -> None:
        """Top-level package import works."""
        from autom8_asana.metrics import (
            MetricExpr,
            Metric,
            Scope,
            MetricRegistry,
            compute_metric,
        )
        assert MetricExpr is not None
        assert Metric is not None
        assert Scope is not None
        assert MetricRegistry is not None
        assert compute_metric is not None

    def test_import_definitions_offer(self) -> None:
        """Importing offer definitions does not crash."""
        from autom8_asana.metrics.definitions import offer
        assert hasattr(offer, "ACTIVE_MRR")
        assert hasattr(offer, "ACTIVE_AD_SPEND")

    def test_offer_section_enum_used_correctly(self) -> None:
        """OfferSection.ACTIVE matches the section GID in metric definitions."""
        from autom8_asana.models.business.sections import OfferSection
        MetricRegistry.reset()
        registry = MetricRegistry()
        mrr = registry.get_metric("active_mrr")
        assert mrr.scope.section == OfferSection.ACTIVE.value
        MetricRegistry.reset()

    def test_supported_aggs_is_frozen(self) -> None:
        """SUPPORTED_AGGS cannot be mutated."""
        assert isinstance(SUPPORTED_AGGS, frozenset)
        with pytest.raises(AttributeError):
            SUPPORTED_AGGS.add("median")  # type: ignore[attr-defined]


# ===========================================================================
# 6. Backward Compatibility Deep Tests
# ===========================================================================

class TestBackwardCompatibilityDeep:
    """Deep parity tests comparing new metrics layer to old script logic."""

    @pytest.fixture
    def realistic_offer_df(self) -> pl.DataFrame:
        """Larger, more realistic test DataFrame."""
        return pl.DataFrame({
            "name": [
                "Offer A", "Offer B", "Offer C", "Offer D", "Offer E",
                "Offer F", "Offer G", "Offer H", "Offer I", "Offer J",
            ],
            "office_phone": [
                "555-0001", "555-0001", "555-0002", "555-0003", "555-0003",
                "555-0004", "555-0005", "555-0005", "555-0006", "555-0006",
            ],
            "vertical": [
                "dental", "dental", "dental", "med_spa", "med_spa",
                "chiro", "dental", "plumbing", "dental", "dental",
            ],
            "mrr": [
                "1000", "2000", "1500", None, "500",
                "0", "300", "400", "-50", "abc",
            ],
            "weekly_ad_spend": [
                "500", "600", None, "200", "0",
                "150", "abc", "300", "100", "250",
            ],
        })

    def test_mrr_parity_realistic(self, realistic_offer_df: pl.DataFrame) -> None:
        """MRR totals match between old and new logic on realistic data."""
        # Old script logic (from calc_mrr.py)
        old = (
            realistic_offer_df
            .select("name", "office_phone", "vertical", "mrr")
            .with_columns(pl.col("mrr").cast(pl.Float64, strict=False).alias("mrr"))
            .filter(pl.col("mrr").is_not_null() & (pl.col("mrr") > 0))
            .unique(subset=["office_phone", "vertical"], keep="first")
        )
        old_total = old["mrr"].sum()
        old_count = len(old)

        # New metrics layer
        m = _metric(
            "mrr",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
            dedup_keys=["office_phone", "vertical"],
        )
        new = compute_metric(m, realistic_offer_df)
        new_total = new["mrr"].sum()
        new_count = len(new)

        assert new_total == old_total, f"MRR mismatch: new={new_total} vs old={old_total}"
        assert new_count == old_count, f"Row count mismatch: new={new_count} vs old={old_count}"

    def test_ad_spend_parity_realistic(self, realistic_offer_df: pl.DataFrame) -> None:
        """Ad spend totals match between old and new logic on realistic data."""
        # Old script logic (from calc_ad_spend.py)
        old = (
            realistic_offer_df
            .select("name", "office_phone", "vertical", "weekly_ad_spend")
            .with_columns(
                pl.col("weekly_ad_spend").cast(pl.Float64, strict=False).alias("weekly_ad_spend")
            )
            .filter(
                pl.col("weekly_ad_spend").is_not_null()
                & (pl.col("weekly_ad_spend") > 0)
            )
            .unique(subset=["office_phone", "vertical"], keep="first")
        )
        old_total = old["weekly_ad_spend"].sum()
        old_count = len(old)

        # New metrics layer
        m = _metric(
            "weekly_ad_spend",
            cast_dtype=pl.Float64,
            filter_expr=(
                pl.col("weekly_ad_spend").is_not_null()
                & (pl.col("weekly_ad_spend") > 0)
            ),
            dedup_keys=["office_phone", "vertical"],
        )
        new = compute_metric(m, realistic_offer_df)
        new_total = new["weekly_ad_spend"].sum()
        new_count = len(new)

        assert new_total == old_total, f"Ad spend mismatch: new={new_total} vs old={old_total}"
        assert new_count == old_count, f"Row count mismatch: new={new_count} vs old={old_count}"

    def test_zero_values_filtered_by_gt_zero(self) -> None:
        """Zero values are correctly excluded by > 0 filter (matching old scripts)."""
        df = pl.DataFrame({
            "name": ["a", "b", "c"],
            "office_phone": ["p1", "p2", "p3"],
            "vertical": ["v1", "v2", "v3"],
            "mrr": ["0", "100", "0.0"],
        })
        m = _metric(
            "mrr",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
            dedup_keys=["office_phone", "vertical"],
        )
        result = compute_metric(m, df)
        assert len(result) == 1
        assert result["mrr"][0] == 100.0

    def test_negative_values_filtered_by_gt_zero(self) -> None:
        """Negative values are excluded by > 0 filter."""
        df = pl.DataFrame({
            "name": ["a", "b"],
            "office_phone": ["p1", "p2"],
            "vertical": ["v1", "v2"],
            "mrr": ["-50", "100"],
        })
        m = _metric(
            "mrr",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
            dedup_keys=["office_phone", "vertical"],
        )
        result = compute_metric(m, df)
        assert len(result) == 1
        assert result["mrr"][0] == 100.0

    def test_dedup_keeps_first_encounter(self) -> None:
        """Dedup keeps first row per key combo, matching Polars unique(keep='first')."""
        df = pl.DataFrame({
            "name": ["first", "second", "third"],
            "key": ["a", "a", "b"],
            "val": [10, 20, 30],
        })
        m = _metric("val", dedup_keys=["key"])
        result = compute_metric(m, df)
        # key "a" should keep "first" with val=10
        a_row = result.filter(pl.col("key") == "a")
        assert a_row["val"][0] == 10
        assert a_row["name"][0] == "first"
