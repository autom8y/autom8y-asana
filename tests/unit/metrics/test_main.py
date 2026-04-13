"""Unit tests for metrics CLI entry point."""

from __future__ import annotations

from unittest.mock import patch

import polars as pl
import pytest

from autom8_asana.metrics.__main__ import main
from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    MetricRegistry.reset()
    yield  # type: ignore[misc]
    MetricRegistry.reset()


class TestCliList:
    """Test --list functionality."""

    def test_list_outputs_metric_names(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("sys.argv", ["metrics", "--list"]):
            main()
        captured = capsys.readouterr()
        assert "active_mrr" in captured.out
        assert "active_ad_spend" in captured.out
        assert "Available metrics:" in captured.out


class TestCliErrors:
    """Test error handling."""

    def test_no_args_exits(self) -> None:
        with patch("sys.argv", ["metrics"]):
            with pytest.raises(SystemExit):
                main()

    def test_unknown_metric_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("sys.argv", ["metrics", "nonexistent_metric"]):
            with pytest.raises(SystemExit):
                main()
        captured = capsys.readouterr()
        assert "Unknown metric" in captured.err


class TestCliCompute:
    """Test metric computation via CLI."""

    def test_compute_with_mocked_loader(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI computes metric when loader returns valid DataFrame."""
        mock_df = pl.DataFrame(
            {
                "name": ["A", "B", "C"],
                "section": ["ACTIVE", "STAGING", "INACTIVE"],
                "office_phone": ["555-1", "555-2", "555-3"],
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["1000", "2000", "500"],
                "weekly_ad_spend": ["100", "200", "50"],
            }
        )

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
        ):
            main()

        captured = capsys.readouterr()
        assert "active_mrr:" in captured.out
        # ACTIVE + STAGING are "active" classification; INACTIVE is not
        # A: mrr=1000, B: mrr=2000 -> after dedup both unique -> sum=3000
        assert "$3,000.00" in captured.out

    def test_compute_ad_spend(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI computes ad spend metric."""
        mock_df = pl.DataFrame(
            {
                "name": ["A", "B"],
                "section": ["ACTIVE", "ACTIVE"],
                "office_phone": ["555-1", "555-2"],
                "vertical": ["dental", "med_spa"],
                "mrr": ["1000", "2000"],
                "weekly_ad_spend": ["150", "250"],
            }
        )

        with (
            patch("sys.argv", ["metrics", "active_ad_spend"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
        ):
            main()

        captured = capsys.readouterr()
        assert "active_ad_spend:" in captured.out
        assert "$400.00" in captured.out

    def test_loader_error_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI exits gracefully when loader fails."""
        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                side_effect=ValueError("No S3 bucket configured"),
            ),
        ):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "No S3 bucket configured" in captured.err

    def test_count_metric_formats_as_integer(self, capsys: pytest.CaptureFixture[str]) -> None:
        """count aggregation formats as plain integer, not dollar amount (LS-DEEP-001)."""
        registry = MetricRegistry()
        registry._initialized = True
        count_metric = Metric(
            name="test_count",
            description="Test count metric",
            expr=MetricExpr(name="count_name", column="name", agg="count"),
            scope=Scope(entity_type="test", section="999"),
        )
        registry.register(count_metric)

        mock_df = pl.DataFrame(
            {
                "name": ["A", "B", "C"],
                "section": ["ACTIVE", "ACTIVE", "ACTIVE"],
                "office_phone": ["555-1", "555-2", "555-3"],
                "vertical": ["dental", "dental", "dental"],
                "mrr": ["1000", "2000", "500"],
                "weekly_ad_spend": ["100", "200", "50"],
            }
        )

        with (
            patch("sys.argv", ["metrics", "test_count"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
            patch(
                "autom8_asana.models.business.activity.CLASSIFIERS",
                {"test": type("C", (), {"project_gid": "000"})()},
            ),
        ):
            main()

        captured = capsys.readouterr()
        assert "test_count:" in captured.out
        # count of 3 rows should display as "3", never as "$3.00"
        assert "3" in captured.out
        assert "$3" not in captured.out
        assert "$3.00" not in captured.out

    def test_mean_metric_empty_dataframe_shows_no_data(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """mean on empty DataFrame returns None; CLI displays 'N/A (no data)' (LS-DEEP-002)."""
        registry = MetricRegistry()
        registry._initialized = True
        mean_metric = Metric(
            name="test_mean",
            description="Test mean metric",
            expr=MetricExpr(
                name="mean_mrr",
                column="mrr",
                cast_dtype=pl.Float64,
                agg="mean",
            ),
            scope=Scope(entity_type="test", section="999"),
        )
        registry.register(mean_metric)

        # Empty DataFrame — mean() returns None, must not raise TypeError
        mock_df = pl.DataFrame(
            {
                "name": pl.Series([], dtype=pl.Utf8),
                "mrr": pl.Series([], dtype=pl.Utf8),
            }
        )

        with (
            patch("sys.argv", ["metrics", "test_mean"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
            patch(
                "autom8_asana.models.business.activity.CLASSIFIERS",
                {"test": type("C", (), {"project_gid": "000"})()},
            ),
        ):
            main()  # must NOT raise TypeError

        captured = capsys.readouterr()
        assert "test_mean:" in captured.out
        assert "N/A (no data)" in captured.out
