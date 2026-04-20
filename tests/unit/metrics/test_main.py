"""Unit tests for metrics CLI entry point."""

from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tomllib
from unittest.mock import patch

import polars as pl
import pytest

from autom8_asana.metrics.__main__ import _CLI_REQUIRED, main
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

    @pytest.fixture(autouse=True)
    def _set_cli_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Satisfy the CFG-006 preflight for the duration of each test.

        TestCliCompute exercises CLI composition (arg parsing, metric lookup,
        result formatting) — not the preflight gate itself. The preflight
        contract (CFG-006) is correct; these tests need env isolation so they
        pass regardless of the invoking shell's state (CI, fresh clone, etc.).
        """
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv("ASANA_CACHE_S3_REGION", "us-east-1")

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


# ---------------------------------------------------------------------------
# RES-001: Parity guard — _CLI_REQUIRED tuple vs secretspec.toml [profiles.cli]
# Sprint-B advisory #3 (AUDIT-env-secrets-sprint-B.md §8 item 3)
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SECRETSPEC_TOML = _REPO_ROOT / "secretspec.toml"


class TestPreflightParity:
    """Parity guard: _CLI_REQUIRED must equal the required=true vars in [profiles.cli].

    Primary test (TOML parse) catches drift whenever secretspec.toml is edited.
    Skip-gated test catches semantic divergence between the binary and the inline
    fallback when the secretspec binary is present in the environment.

    See src/autom8_asana/metrics/__main__.py::_CLI_REQUIRED and
    src/autom8_asana/metrics/__main__.py::_preflight_inline_fallback.
    """

    def test_inline_and_secretspec_enforce_same_required_vars(self) -> None:
        """_CLI_REQUIRED must equal the set of required=true vars in [profiles.cli].

        Parses secretspec.toml via tomllib (stdlib, Py 3.11+) and extracts every
        var under [profiles.cli] whose 'required' attribute is True. Compares that
        set against _CLI_REQUIRED. A mismatch means the inline fallback will silently
        skip enforcement of any var added to the profile contract.
        """
        with _SECRETSPEC_TOML.open("rb") as f:
            data = tomllib.load(f)

        cli_profile = data.get("profiles", {}).get("cli", {})
        required_from_toml = {
            key for key, attrs in cli_profile.items() if attrs.get("required") is True
        }
        required_from_tuple = set(_CLI_REQUIRED)

        assert required_from_toml == required_from_tuple, (
            f"[profiles.cli] required=true vars in secretspec.toml: {sorted(required_from_toml)}\n"
            f"_CLI_REQUIRED tuple: {sorted(required_from_tuple)}\n"
            "Update _CLI_REQUIRED in src/autom8_asana/metrics/__main__.py to match."
        )

    @pytest.mark.skipif(
        shutil.which("secretspec") is None,
        reason="secretspec binary absent — inline-fallback path is only runtime check",
    )
    def test_secretspec_binary_parity_when_available(self) -> None:
        """When secretspec is present, binary and inline fallback enforce the same vars.

        Part A: secretspec check --profile cli with both required vars UNSET must
        exit non-zero and name each _CLI_REQUIRED var in stderr.

        Part B: _preflight_inline_fallback() with both vars UNSET must raise
        SystemExit(2) and name the same vars in stderr.
        """
        import os

        from autom8_asana.metrics.__main__ import _preflight_inline_fallback

        # Part A — binary
        clean_env = {k: v for k, v in os.environ.items() if k not in _CLI_REQUIRED}
        result = subprocess.run(
            [
                "secretspec",
                "check",
                "--config",
                str(_SECRETSPEC_TOML),
                "--provider",
                "env",
                "--profile",
                "cli",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=clean_env,
            timeout=10,
        )
        assert result.returncode != 0, (
            "secretspec check --profile cli should exit non-zero when required vars are absent"
        )
        for var in _CLI_REQUIRED:
            assert var in result.stderr, (
                f"Expected secretspec stderr to mention '{var}'; got: {result.stderr!r}"
            )

        # Part B — inline fallback
        # Temporarily unset the required vars for the duration of the assertion.
        original = {v: os.environ.pop(v, None) for v in _CLI_REQUIRED}
        try:
            captured_stderr = io.StringIO()
            with pytest.raises(SystemExit) as exc_info:
                with patch("sys.stderr", captured_stderr):
                    _preflight_inline_fallback()
            assert exc_info.value.code == 2, (
                f"_preflight_inline_fallback should sys.exit(2), got {exc_info.value.code}"
            )
            stderr_text = captured_stderr.getvalue()
            for var in _CLI_REQUIRED:
                assert var in stderr_text, (
                    f"Expected inline fallback stderr to mention '{var}'; got: {stderr_text!r}"
                )
        finally:
            for var, val in original.items():
                if val is not None:
                    os.environ[var] = val
