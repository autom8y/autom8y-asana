"""Unit tests for compute_metric."""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.metrics.compute import compute_metric
from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope


@pytest.fixture
def sample_offer_df() -> pl.DataFrame:
    """Synthetic ACTIVE section DataFrame matching parquet schema."""
    return pl.DataFrame(
        {
            "name": ["Offer A", "Offer B", "Offer C", "Offer D"],
            "office_phone": ["555-0001", "555-0001", "555-0002", "555-0003"],
            "vertical": ["dental", "dental", "dental", "med_spa"],
            "mrr": ["1000", "2000", "1500", None],
            "weekly_ad_spend": ["500", "600", None, "200"],
        }
    )


def _make_metric(
    column: str,
    *,
    cast_dtype: pl.DataType | None = None,
    filter_expr: pl.Expr | None = None,
    dedup_keys: list[str] | None = None,
    pre_filters: list[pl.Expr] | None = None,
) -> Metric:
    """Helper to create a Metric with minimal boilerplate."""
    return Metric(
        name=f"test_{column}",
        description=f"Test metric for {column}",
        expr=MetricExpr(
            name=f"sum_{column}",
            column=column,
            cast_dtype=cast_dtype,
            agg="sum",
            filter_expr=filter_expr,
        ),
        scope=Scope(
            entity_type="test",
            section="123",
            dedup_keys=dedup_keys,
            pre_filters=pre_filters,
        ),
    )


class TestComputeBasic:
    """Test basic compute_metric functionality."""

    def test_basic_sum_no_filter_no_dedup(self) -> None:
        df = pl.DataFrame({"name": ["a", "b"], "val": [10, 20]})
        metric = _make_metric("val")
        result = compute_metric(metric, df)
        assert result["val"].sum() == 30

    def test_with_cast_from_string(self, sample_offer_df: pl.DataFrame) -> None:
        metric = _make_metric("mrr", cast_dtype=pl.Float64)
        result = compute_metric(metric, sample_offer_df)
        # All 4 rows included (no filter), null MRR cast becomes null
        # sum of 1000 + 2000 + 1500 + null = 4500
        assert result["mrr"].sum() == 4500.0

    def test_with_filter(self, sample_offer_df: pl.DataFrame) -> None:
        metric = _make_metric(
            "mrr",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
        )
        result = compute_metric(metric, sample_offer_df)
        # Offer D has null MRR, filtered out: 3 rows remain
        assert len(result) == 3
        assert result["mrr"].sum() == 4500.0

    def test_with_dedup(self, sample_offer_df: pl.DataFrame) -> None:
        metric = _make_metric(
            "mrr",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
            dedup_keys=["office_phone", "vertical"],
        )
        result = compute_metric(metric, sample_offer_df)
        # Offer A and B share (555-0001, dental) -> keep first (Offer A, mrr=1000)
        # Offer C is unique (555-0002, dental) -> keep (mrr=1500)
        # Offer D is filtered out (null mrr)
        assert len(result) == 2
        assert result["mrr"].sum() == 2500.0

    def test_with_pre_filters(self, sample_offer_df: pl.DataFrame) -> None:
        metric = _make_metric(
            "mrr",
            cast_dtype=pl.Float64,
            dedup_keys=["office_phone", "vertical"],
            pre_filters=[pl.col("vertical") == "dental"],
        )
        result = compute_metric(metric, sample_offer_df)
        # Only dental rows kept by pre_filter: Offer A, B, C
        # Then dedup (555-0001, dental) -> keeps Offer A; (555-0002, dental) -> Offer C
        # No cast filter so null mrr becomes null, still kept
        assert len(result) == 2

    def test_deterministic_sort(self) -> None:
        df = pl.DataFrame(
            {
                "name": ["Z", "A", "M"],
                "key": ["c", "a", "b"],
                "val": [1, 2, 3],
            }
        )
        metric = _make_metric("val", dedup_keys=["key"])
        result = compute_metric(metric, df)
        assert result["key"].to_list() == ["a", "b", "c"]

    def test_empty_dataframe(self) -> None:
        df = pl.DataFrame({"name": [], "val": []}).cast({"val": pl.Int64})
        metric = _make_metric("val")
        result = compute_metric(metric, df)
        assert len(result) == 0

    def test_null_handling_in_metric_column(self) -> None:
        df = pl.DataFrame(
            {
                "name": ["a", "b", "c"],
                "val": [10.0, None, 30.0],
            }
        )
        metric = _make_metric("val")
        result = compute_metric(metric, df)
        # sum ignores nulls: 10 + 30 = 40
        assert result["val"].sum() == 40.0


class TestComputeVerbose:
    """Test verbose output."""

    def test_verbose_prints_table(self, capsys: pytest.CaptureFixture[str]) -> None:
        df = pl.DataFrame({"name": ["a"], "val": [42]})
        metric = _make_metric("val")
        compute_metric(metric, df, verbose=True)
        captured = capsys.readouterr()
        assert "42" in captured.out


class TestComputeClassification:
    """Test classification filtering in compute_metric."""

    @staticmethod
    def _make_classified_metric(
        column: str,
        *,
        entity_type: str = "offer",
        classification: str = "active",
        cast_dtype: pl.DataType | None = None,
        filter_expr: pl.Expr | None = None,
        dedup_keys: list[str] | None = None,
    ) -> Metric:
        return Metric(
            name=f"test_{column}",
            description=f"Test metric for {column}",
            expr=MetricExpr(
                name=f"sum_{column}",
                column=column,
                cast_dtype=cast_dtype,
                agg="sum",
                filter_expr=filter_expr,
            ),
            scope=Scope(
                entity_type=entity_type,
                classification=classification,
                dedup_keys=dedup_keys,
            ),
        )

    def test_classification_filters_to_matching_sections(self) -> None:
        """Active classification keeps ACTIVE/STAGING, drops INACTIVE."""
        df = pl.DataFrame(
            {
                "name": ["A", "B", "C"],
                "section": ["ACTIVE", "INACTIVE", "STAGING"],
                "office_phone": ["555-1", "555-2", "555-3"],
                "vertical": ["dental", "dental", "dental"],
                "mrr": [100.0, 200.0, 300.0],
            }
        )
        metric = self._make_classified_metric("mrr")
        result = compute_metric(metric, df)
        # ACTIVE and STAGING are both in the "active" classification
        assert len(result) == 2
        assert result["mrr"].sum() == 400.0

    def test_classification_case_insensitive(self) -> None:
        """Section matching is case-insensitive (classifier stores lowercase)."""
        df = pl.DataFrame(
            {
                "name": ["A", "B"],
                "section": ["Active", "Inactive"],
                "mrr": [100.0, 200.0],
            }
        )
        metric = self._make_classified_metric("mrr")
        result = compute_metric(metric, df)
        assert len(result) == 1
        assert result["mrr"].sum() == 100.0

    def test_classification_none_is_noop(self) -> None:
        """classification=None does not filter any rows (backward compat)."""
        df = pl.DataFrame(
            {
                "name": ["A", "B"],
                "section": ["ACTIVE", "INACTIVE"],
                "mrr": [100.0, 200.0],
            }
        )
        metric = _make_metric("mrr")  # no classification
        result = compute_metric(metric, df)
        assert len(result) == 2

    def test_classification_unknown_entity_type_raises(self) -> None:
        """Unknown entity type raises ValueError."""
        df = pl.DataFrame({"section": ["X"], "mrr": [1.0]})
        metric = self._make_classified_metric(
            "mrr", entity_type="nonexistent", classification="active"
        )
        with pytest.raises(ValueError, match="No classifier"):
            compute_metric(metric, df)

    def test_classification_missing_section_column_raises(self) -> None:
        """DataFrame without 'section' column raises ValueError."""
        df = pl.DataFrame({"name": ["A"], "mrr": [1.0]})
        metric = self._make_classified_metric("mrr")
        with pytest.raises(ValueError, match="section"):
            compute_metric(metric, df)

    def test_classification_with_dedup(self) -> None:
        """Classification + dedup work together correctly."""
        df = pl.DataFrame(
            {
                "name": ["A", "B", "C", "D"],
                "section": ["ACTIVE", "ACTIVE", "INACTIVE", "STAGING"],
                "office_phone": ["555-1", "555-1", "555-2", "555-3"],
                "vertical": ["dental", "dental", "dental", "dental"],
                "mrr": ["100", "200", "300", "400"],
            }
        )
        metric = self._make_classified_metric(
            "mrr",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
            dedup_keys=["office_phone", "vertical"],
        )
        result = compute_metric(metric, df)
        # ACTIVE: A(555-1,dental,100), B(555-1,dental,200) -> dedup keeps A(100)
        # INACTIVE: C filtered out by classification
        # STAGING: D(555-3,dental,400) -> kept
        assert len(result) == 2
        assert result["mrr"].sum() == 500.0


class TestComputeParity:
    """Parity tests: new metrics layer produces same totals as old scripts."""

    def test_mrr_parity(self, sample_offer_df: pl.DataFrame) -> None:
        """active_mrr metric matches the dedup logic used by `python -m autom8_asana.metrics active_mrr`."""
        metric = _make_metric(
            "mrr",
            cast_dtype=pl.Float64,
            filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
            dedup_keys=["office_phone", "vertical"],
        )
        result = compute_metric(metric, sample_offer_df)

        # Reproduce old script logic
        old_result = (
            sample_offer_df.select("name", "office_phone", "vertical", "mrr")
            .with_columns(pl.col("mrr").cast(pl.Float64, strict=False).alias("mrr"))
            .filter(pl.col("mrr").is_not_null() & (pl.col("mrr") > 0))
            .unique(subset=["office_phone", "vertical"], keep="first")
        )

        assert result["mrr"].sum() == old_result["mrr"].sum()
        assert len(result) == len(old_result)

    def test_ad_spend_parity(self, sample_offer_df: pl.DataFrame) -> None:
        """active_ad_spend metric matches calc_ad_spend logic on same data."""
        metric = _make_metric(
            "weekly_ad_spend",
            cast_dtype=pl.Float64,
            filter_expr=(pl.col("weekly_ad_spend").is_not_null() & (pl.col("weekly_ad_spend") > 0)),
            dedup_keys=["office_phone", "vertical"],
        )
        result = compute_metric(metric, sample_offer_df)

        # Reproduce old script logic
        old_result = (
            sample_offer_df.select("name", "office_phone", "vertical", "weekly_ad_spend")
            .with_columns(
                pl.col("weekly_ad_spend").cast(pl.Float64, strict=False).alias("weekly_ad_spend")
            )
            .filter(pl.col("weekly_ad_spend").is_not_null() & (pl.col("weekly_ad_spend") > 0))
            .unique(subset=["office_phone", "vertical"], keep="first")
        )

        assert result["weekly_ad_spend"].sum() == old_result["weekly_ad_spend"].sum()
        assert len(result) == len(old_result)
