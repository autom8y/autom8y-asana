"""Unit tests for metrics CLI entry point."""

from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from autom8_asana.metrics.__main__ import (
    _CLI_REQUIRED,
    _FORCE_WARM_REQUIRED_ENV,
    _SLA_PROFILE_THRESHOLDS,
    main,
)
from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.freshness import FreshnessReport
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    MetricRegistry.reset()
    yield  # type: ignore[misc]
    MetricRegistry.reset()


def _make_fresh_report(prefix: str = "dataframes/test/sections/") -> FreshnessReport:
    """Construct a minimal fresh FreshnessReport for tests that don't care about S3."""
    return FreshnessReport(
        oldest_mtime=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
        newest_mtime=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
        max_age_seconds=1000,
        threshold_seconds=21600,
        parquet_count=10,
        bucket="autom8-s3",
        prefix=prefix,
    )


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
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=_make_fresh_report(),
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
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=_make_fresh_report(),
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
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=_make_fresh_report("dataframes/000/sections/"),
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
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=_make_fresh_report("dataframes/000/sections/"),
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


# ---------------------------------------------------------------------------
# Batch-A — Work-Items 1, 2, 8
# Tests for --force-warm, --sla-profile, MINOR-OBS-2 botocore handler
# Per HANDOFF-thermia-to-10x-dev-2026-04-27.md §1 + §4 acceptance criteria.
# ---------------------------------------------------------------------------


class TestSlaProfileThresholds:
    """Work-Item 2 — per-class threshold mapping per P3 §2.2 / LD-P2-1."""

    def test_active_class_maps_to_6h(self) -> None:
        assert _SLA_PROFILE_THRESHOLDS["active"] == 21600

    def test_warm_class_maps_to_12h(self) -> None:
        assert _SLA_PROFILE_THRESHOLDS["warm"] == 43200

    def test_cold_class_maps_to_24h(self) -> None:
        assert _SLA_PROFILE_THRESHOLDS["cold"] == 86400

    def test_near_empty_class_maps_to_7d(self) -> None:
        assert _SLA_PROFILE_THRESHOLDS["near-empty"] == 604800

    def test_taxonomy_is_complete_4_class(self) -> None:
        """FLAG-2 canonical taxonomy: exactly 4 classes per P3 §2.2."""
        assert set(_SLA_PROFILE_THRESHOLDS.keys()) == {
            "active",
            "warm",
            "cold",
            "near-empty",
        }


class TestSlaProfileFlagParsing:
    """Work-Item 2 — argparse integration for --sla-profile."""

    @pytest.fixture(autouse=True)
    def _set_cli_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv("ASANA_CACHE_S3_REGION", "us-east-1")

    def test_invalid_sla_profile_value_rejected(self, capsys: pytest.CaptureFixture[str]) -> None:
        """argparse choices reject unknown profile names."""
        with patch("sys.argv", ["metrics", "active_mrr", "--sla-profile=bogus"]):
            with pytest.raises(SystemExit):
                main()
        captured = capsys.readouterr()
        # argparse emits the choice-violation error on stderr
        assert "invalid choice" in captured.err.lower() or "bogus" in captured.err

    def test_warm_profile_threshold_passed_to_freshness_report(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--sla-profile=warm yields 43200s threshold inside FreshnessReport."""
        mock_df = pl.DataFrame(
            {
                "name": ["A"],
                "section": ["ACTIVE"],
                "office_phone": ["555-1"],
                "vertical": ["dental"],
                "mrr": ["1000"],
                "weekly_ad_spend": ["100"],
            }
        )

        # Capture the threshold_seconds passed into from_s3_listing
        captured_kwargs: dict[str, object] = {}

        def _fake_from_s3_listing(
            *, bucket: str, prefix: str, threshold_seconds: int
        ) -> FreshnessReport:
            captured_kwargs["threshold_seconds"] = threshold_seconds
            captured_kwargs["bucket"] = bucket
            return FreshnessReport(
                oldest_mtime=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
                newest_mtime=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
                max_age_seconds=1000,
                threshold_seconds=threshold_seconds,
                parquet_count=10,
                bucket=bucket,
                prefix=prefix,
            )

        with (
            patch("sys.argv", ["metrics", "active_mrr", "--sla-profile=warm"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                side_effect=_fake_from_s3_listing,
            ),
        ):
            main()

        assert captured_kwargs["threshold_seconds"] == 43200, (
            "Expected --sla-profile=warm to map to 43200s (12h) per P3 §2.2"
        )

    def test_explicit_staleness_threshold_overrides_sla_profile(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-2: --staleness-threshold (numeric) takes precedence over --sla-profile."""
        mock_df = pl.DataFrame(
            {
                "name": ["A"],
                "section": ["ACTIVE"],
                "office_phone": ["555-1"],
                "vertical": ["dental"],
                "mrr": ["1000"],
                "weekly_ad_spend": ["100"],
            }
        )

        captured_kwargs: dict[str, object] = {}

        def _fake(*, bucket: str, prefix: str, threshold_seconds: int) -> FreshnessReport:
            captured_kwargs["threshold_seconds"] = threshold_seconds
            return FreshnessReport(
                oldest_mtime=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
                newest_mtime=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
                max_age_seconds=1000,
                threshold_seconds=threshold_seconds,
                parquet_count=10,
                bucket=bucket,
                prefix=prefix,
            )

        with (
            patch(
                "sys.argv",
                [
                    "metrics",
                    "active_mrr",
                    "--sla-profile=cold",  # would be 86400
                    "--staleness-threshold",
                    "1h",  # explicit -> 3600 wins
                ],
            ),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                side_effect=_fake,
            ),
        ):
            main()

        assert captured_kwargs["threshold_seconds"] == 3600

    def test_default_threshold_is_active_class_6h(self, capsys: pytest.CaptureFixture[str]) -> None:
        """PRD C-2: when no --sla-profile and no --staleness-threshold, default is 6h."""
        mock_df = pl.DataFrame(
            {
                "name": ["A"],
                "section": ["ACTIVE"],
                "office_phone": ["555-1"],
                "vertical": ["dental"],
                "mrr": ["1000"],
                "weekly_ad_spend": ["100"],
            }
        )

        captured_kwargs: dict[str, object] = {}

        def _fake(*, bucket: str, prefix: str, threshold_seconds: int) -> FreshnessReport:
            captured_kwargs["threshold_seconds"] = threshold_seconds
            return FreshnessReport(
                oldest_mtime=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
                newest_mtime=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
                max_age_seconds=1000,
                threshold_seconds=threshold_seconds,
                parquet_count=10,
                bucket=bucket,
                prefix=prefix,
            )

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                side_effect=_fake,
            ),
        ):
            main()

        assert captured_kwargs["threshold_seconds"] == 21600


class TestForceWarmFlagParsing:
    """Work-Item 1 — argparse integration for --force-warm + --wait.

    PT-2 Option B refactor (2026-04-27): mocks relocated from
    boto3.client("lambda").invoke to force_warm() patches at the import
    site (autom8_asana.metrics.__main__.force_warm). LD-P3-2 call-order
    semantics preserved at force_warm() interaction altitude — a Lambda
    invoke without first delegating to force_warm() is now structurally
    impossible (the CLI no longer constructs its own boto3 client).
    """

    @staticmethod
    def _make_async_force_warm_result(
        *, deduped: bool = False, invoked: bool = True, wait: bool = False
    ) -> object:
        """Build a ForceWarmResult fixture for use as force_warm() return.

        Encapsulates the canonical surface's return shape so individual tests
        only need to flip the booleans they care about.
        """
        from autom8_asana.cache.integration.force_warm import ForceWarmResult

        invocation_type = "RequestResponse" if wait else "Event"
        return ForceWarmResult(
            invoked=invoked,
            invocation_type=invocation_type,
            deduped=deduped,
            latency_seconds=0.001,
            function_arn="test-warmer-fn",
            project_gid="12345",
            entity_types=(),
            coalescer_key="forcewarm:12345:*",
            lambda_status_code=202 if not wait else 200,
            lambda_response_payload={"success": True} if wait else None,
            l1_invalidated=wait and not deduped and invoked,
        )

    def test_force_warm_missing_bucket_exits_1_friendly(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1: ASANA_CACHE_S3_BUCKET unset → friendly stderr, exit 1, no Lambda invoke."""
        monkeypatch.delenv("ASANA_CACHE_S3_BUCKET", raising=False)
        monkeypatch.setenv("ASANA_CACHE_S3_REGION", "us-east-1")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "fn-name")

        with patch("sys.argv", ["metrics", "--force-warm"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "ASANA_CACHE_S3_BUCKET" in captured.err
        # Must not be a raw traceback
        assert "Traceback" not in captured.err

    def test_force_warm_missing_function_name_env_exits_1(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing CACHE_WARMER_LAMBDA_ARN → friendly stderr, exit 1.

        PT-2 Option B refactor unified the force-warm env var to the fleet
        convention (CACHE_WARMER_LAMBDA_ARN, see admin.py:211 +
        progressive.py:548). _FORCE_WARM_REQUIRED_ENV is now bound to
        force_warm.LAMBDA_ARN_ENV_VAR.
        """
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv("ASANA_CACHE_S3_REGION", "us-east-1")
        monkeypatch.delenv(_FORCE_WARM_REQUIRED_ENV, raising=False)

        with patch("sys.argv", ["metrics", "--force-warm", "--project-gid", "12345"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert _FORCE_WARM_REQUIRED_ENV in captured.err
        assert "Traceback" not in captured.err

    def test_force_warm_env_var_is_fleet_convention(self) -> None:
        """PT-2 Option B refactor: env var unified to fleet convention.

        Asserts the CLI's force-warm env var matches the canonical
        force_warm() module's LAMBDA_ARN_ENV_VAR, which in turn matches
        the fleet convention used at api/routes/admin.py:211 and
        api/preload/progressive.py:548.
        """
        from autom8_asana.cache.integration.force_warm import LAMBDA_ARN_ENV_VAR

        assert _FORCE_WARM_REQUIRED_ENV == "CACHE_WARMER_LAMBDA_ARN"
        assert _FORCE_WARM_REQUIRED_ENV == LAMBDA_ARN_ENV_VAR

    def test_force_warm_async_delegates_to_canonical_force_warm(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LD-P3-2: --force-warm (async) delegates to canonical force_warm().

        Verifies (LD-P3-2 call-order semantics preserved at force_warm()
        interaction altitude):
          1. force_warm() is awaited (not boto3 directly — the CLI no longer
             constructs its own boto3 client; LD-P3-2 violation is now
             structurally impossible).
          2. force_warm() is called with wait=False, entity_types=(),
             project_gid='12345' for the async path.
          3. force_warm() is called with a non-None DataFrameCache instance
             (proving coalescer-routing at the canonical surface altitude;
             cache.coalescer is the unified instance per PT-2 Option B).
          4. Exit code 0 on successful Lambda accept.
        """
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        captured_calls: list[dict[str, object]] = []

        async def _mock_force_warm(**kwargs: object) -> object:
            captured_calls.append(kwargs)
            return self._make_async_force_warm_result(wait=False)

        # Stub out the factory to avoid touching real S3 / settings. The
        # CLI's _resolve_dataframe_cache_for_cli reads through these symbols.
        mock_cache = MagicMock(name="DataFrameCache")

        with (
            patch("sys.argv", ["metrics", "--force-warm", "--project-gid", "12345"]),
            patch(
                "autom8_asana.metrics.__main__.force_warm",
                _mock_force_warm,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        # Assert delegation occurred exactly once with the right shape.
        assert len(captured_calls) == 1, (
            f"Expected exactly one force_warm() call; got {len(captured_calls)}"
        )
        call = captured_calls[0]
        assert call["project_gid"] == "12345"
        assert call["wait"] is False
        assert call["entity_types"] == ()
        # Cache instance is passed through — coalescer-routing happens at
        # the canonical surface altitude (force_warm.py uses cache.coalescer).
        assert call["cache"] is mock_cache, (
            "force_warm() must receive the app-shared DataFrameCache instance "
            "(PT-2 Option B: NO fresh per-invocation coalescer)"
        )

        captured = capsys.readouterr()
        assert "force-warm invoked" in captured.err.lower()

    def test_force_warm_wait_delegates_with_wait_true(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force-warm --wait passes wait=True to canonical force_warm()."""
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        captured_calls: list[dict[str, object]] = []

        async def _mock_force_warm(**kwargs: object) -> object:
            captured_calls.append(kwargs)
            return self._make_async_force_warm_result(wait=True)

        mock_cache = MagicMock(name="DataFrameCache")

        with (
            patch(
                "sys.argv",
                ["metrics", "--force-warm", "--wait", "--project-gid", "12345"],
            ),
            patch(
                "autom8_asana.metrics.__main__.force_warm",
                _mock_force_warm,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        assert len(captured_calls) == 1
        assert captured_calls[0]["wait"] is True, (
            f"Expected wait=True; got {captured_calls[0]['wait']!r}"
        )

        captured = capsys.readouterr()
        assert "sync" in captured.err.lower() or "L1 invalidated" in captured.err

    def test_force_warm_lambda_function_error_exits_1(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force-warm --wait exits 1 when force_warm raises ForceWarmError(KIND_LAMBDA)."""
        from autom8_asana.cache.integration.force_warm import ForceWarmError

        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        async def _mock_force_warm(**kwargs: object) -> object:
            raise ForceWarmError(
                ForceWarmError.KIND_LAMBDA,
                "Lambda FunctionError=Unhandled; payload={'errorMessage': 'boom'}",
            )

        mock_cache = MagicMock(name="DataFrameCache")

        with (
            patch(
                "sys.argv",
                ["metrics", "--force-warm", "--wait", "--project-gid", "12345"],
            ),
            patch(
                "autom8_asana.metrics.__main__.force_warm",
                _mock_force_warm,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        # ForceWarmError stringification carries "[lambda] ..." prefix; CLI
        # surfaces "Lambda reported failure" or includes the error body.
        assert "lambda" in captured.err.lower()
        assert "Traceback" not in captured.err

    def test_force_warm_no_project_gid_or_metric_exits_1(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force-warm without --project-gid or metric exits 1 with friendly stderr."""
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        with patch("sys.argv", ["metrics", "--force-warm"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "project-gid" in captured.err.lower() or "classifier" in captured.err

    def test_two_cli_invocations_share_dedup_state(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PT-2 Option B: two CLI --force-warm invocations share dedup state.

        The structural fix for the parallel-batch interface drift defect:
        Batch-A previously constructed a fresh DataFrameCacheCoalescer per
        invocation, so two CLI calls in the same process did NOT coalesce
        (defeating LD-P3-2 thundering-herd intent). After the refactor, both
        invocations resolve through the app-shared DataFrameCache singleton
        (factory module-level _dataframe_cache), so they share the same
        coalescer instance and the same dedup state.

        This test mocks force_warm() and asserts that both CLI invocations
        receive the SAME cache instance — proof of singleton sharing. It then
        simulates the second invocation hitting the deduped path (force_warm
        returns ForceWarmResult(deduped=True, invoked=False)) and asserts
        the CLI surfaces "coalesced" and exits 0.
        """
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        captured_caches: list[object] = []
        invocation_counter = {"n": 0}

        async def _mock_force_warm(**kwargs: object) -> object:
            captured_caches.append(kwargs["cache"])
            invocation_counter["n"] += 1
            # First invocation: held the lock and invoked. Second invocation:
            # deduped onto the in-flight first call.
            if invocation_counter["n"] == 1:
                return self._make_async_force_warm_result(deduped=False, invoked=True, wait=False)
            return self._make_async_force_warm_result(deduped=True, invoked=False, wait=False)

        # A single shared mock cache stands in for the singleton.
        shared_mock_cache = MagicMock(name="SharedDataFrameCache")

        # First CLI invocation
        with (
            patch("sys.argv", ["metrics", "--force-warm", "--project-gid", "12345"]),
            patch(
                "autom8_asana.metrics.__main__.force_warm",
                _mock_force_warm,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=shared_mock_cache,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        # Second CLI invocation — should hit the deduped path
        with (
            patch("sys.argv", ["metrics", "--force-warm", "--project-gid", "12345"]),
            patch(
                "autom8_asana.metrics.__main__.force_warm",
                _mock_force_warm,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=shared_mock_cache,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        # CRITICAL: both invocations received the SAME cache instance.
        # This is the structural property that defeats interface drift —
        # the coalescer at cache.coalescer is unified across CLI calls.
        assert len(captured_caches) == 2, (
            f"Expected 2 force_warm() calls; got {len(captured_caches)}"
        )
        assert captured_caches[0] is captured_caches[1], (
            "PT-2 Option B violation: two CLI invocations received DIFFERENT "
            "cache instances. The app-shared singleton path is broken; "
            "force-warm dedup state is NOT unified — interface drift restored."
        )

        # Second invocation surfaced the coalesced path.
        captured = capsys.readouterr()
        assert "coalesced" in captured.err.lower(), (
            f"Expected 'coalesced' in stderr for the deduped second invocation; "
            f"got: {captured.err!r}"
        )

    def test_force_warm_coalescer_key_shape_matches_canonical(self) -> None:
        """PT-2 Option B: coalescer key shape matches Batch-C canonical.

        Asserts the key shape forcewarm:{project_gid}:{entity_types|*} that
        Batch-C's force_warm.build_coalescer_key produces. The CLI surface
        no longer constructs its own key; this test pins the canonical key
        shape so a divergence in Batch-C would surface here as a CLI test
        regression rather than only as a Batch-C test regression.
        """
        from autom8_asana.cache.integration.force_warm import (
            COALESCER_KEY_PREFIX,
            build_coalescer_key,
        )

        assert COALESCER_KEY_PREFIX == "forcewarm:"
        assert build_coalescer_key("12345", ()) == "forcewarm:12345:*"
        assert build_coalescer_key("12345", ("unit",)) == "forcewarm:12345:unit"
        assert build_coalescer_key("12345", ("offer", "unit")) == "forcewarm:12345:offer,unit"


class TestMinorObs2BotocoreFix:
    """Work-Item 8 — MINOR-OBS-2 botocore traceback fix.

    Verifies the exception handler at __main__.py post-load_project_dataframe
    catches botocore.exceptions.ClientError(NoSuchBucket) and emits an
    AC-4.2-shaped friendly stderr line WITHOUT a raw traceback.
    """

    @pytest.fixture(autouse=True)
    def _set_cli_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "nonexistent-bucket-xyz")
        monkeypatch.setenv("ASANA_CACHE_S3_REGION", "us-east-1")

    def test_no_such_bucket_clienterror_emits_friendly_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-8: ClientError(NoSuchBucket) → friendly stderr, no raw traceback."""
        from botocore.exceptions import ClientError

        no_such_bucket = ClientError(
            error_response={
                "Error": {
                    "Code": "NoSuchBucket",
                    "Message": "The specified bucket does not exist",
                }
            },
            operation_name="ListObjectsV2",
        )

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                side_effect=no_such_bucket,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        # AC-4.2 shape: "ERROR: bucket or prefix not found — s3://{bucket}/{prefix}"
        assert "bucket or prefix not found" in captured.err
        assert "nonexistent-bucket-xyz" in captured.err
        # CRITICAL: no raw traceback
        assert "Traceback" not in captured.err
        assert "botocore.exceptions" not in captured.err

    def test_access_denied_clienterror_emits_friendly_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """ClientError(AccessDenied) is also mapped to a friendly line."""
        from botocore.exceptions import ClientError

        access_denied = ClientError(
            error_response={
                "Error": {"Code": "AccessDenied", "Message": "denied"},
            },
            operation_name="ListObjectsV2",
        )

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                side_effect=access_denied,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "access denied" in captured.err.lower()
        assert "Traceback" not in captured.err

    def test_unknown_clienterror_code_emits_friendly_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Unknown ClientError code still produces a friendly stderr (no raw traceback)."""
        from botocore.exceptions import ClientError

        unknown = ClientError(
            error_response={"Error": {"Code": "SomeNewCode", "Message": "x"}},
            operation_name="ListObjectsV2",
        )

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                side_effect=unknown,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "SomeNewCode" in captured.err or "ClientError" in captured.err
        assert "Traceback" not in captured.err

    def test_no_credentials_error_emits_friendly_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """NoCredentialsError also handled; no raw traceback."""
        from botocore.exceptions import NoCredentialsError

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                side_effect=NoCredentialsError(),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "credentials unavailable" in captured.err.lower()
        assert "Traceback" not in captured.err


# ---------------------------------------------------------------------------
# BLOCK-1 remediation — wire emit_freshness_probe_metrics() into production
# CLI flow. PT-3 Pythia raised that the emit function existed with full unit-
# test coverage but was NEVER CALLED from __main__.py. The four tests below
# verify the production wiring per the PT-3 verdict + ADR-006 § Decision +
# P4 SLI definitions.
# ---------------------------------------------------------------------------


class TestForceWarmEmitsFreshnessMetrics:
    """BLOCK-1 remediation tests — production wiring of emit_freshness_probe_metrics().

    Verifies the four wiring properties:
      1. ``--force-warm --wait`` triggers emit with ForceWarmLatencySeconds populated.
      2. Default-mode CLI (no --force-warm) emits baseline metrics with
         ForceWarmLatencySeconds=None.
      3. CW emit failure does NOT crash the CLI (sys.exit semantics preserved;
         _safe_emit_freshness_probe_metrics absorbs the exception).
      4. FLAG-1 boundary: latency captured spans coalescer wait (the window
         starts at parser.parse_args() return, ends at post-warm S3 recheck).
    """

    @pytest.fixture(autouse=True)
    def _set_cli_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv("ASANA_CACHE_S3_REGION", "us-east-1")

    @staticmethod
    def _make_sync_force_warm_result() -> object:
        """Build a successful sync ForceWarmResult fixture (wait=True path)."""
        from autom8_asana.cache.integration.force_warm import ForceWarmResult

        return ForceWarmResult(
            invoked=True,
            invocation_type="RequestResponse",
            deduped=False,
            latency_seconds=0.001,
            function_arn="test-warmer-fn",
            project_gid="12345",
            entity_types=(),
            coalescer_key="forcewarm:12345:*",
            lambda_status_code=200,
            lambda_response_payload={"success": True},
            l1_invalidated=True,
        )

    def test_force_warm_wait_triggers_emit_with_latency(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1: --force-warm --wait calls emit_freshness_probe_metrics with non-None latency.

        Verifies the production wiring:
          - force_warm() returns success on the sync path.
          - _execute_force_warm re-runs FreshnessReport.from_s3_listing() to
            observe post-warm fresh state.
          - emit_freshness_probe_metrics is invoked with
            force_warm_latency_seconds populated (not None) per FLAG-1.
        """
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        async def _mock_force_warm(**kwargs: object) -> object:
            return self._make_sync_force_warm_result()

        captured_emit_kwargs: list[dict[str, object]] = []

        def _mock_emit(**kwargs: object) -> dict[str, object]:
            captured_emit_kwargs.append(kwargs)
            return {"namespace": "Autom8y/FreshnessProbe", "metric_data": []}

        recheck_report = _make_fresh_report(prefix="dataframes/12345/sections/")

        mock_cache = MagicMock(name="DataFrameCache")

        with (
            patch(
                "sys.argv",
                ["metrics", "--force-warm", "--wait", "--project-gid", "12345"],
            ),
            patch(
                "autom8_asana.metrics.__main__.force_warm",
                _mock_force_warm,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=recheck_report,
            ),
            patch(
                "autom8_asana.metrics.__main__.emit_freshness_probe_metrics",
                side_effect=_mock_emit,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        # Assert emit was invoked exactly once on the --force-warm --wait path.
        assert len(captured_emit_kwargs) == 1, (
            f"Expected exactly one emit_freshness_probe_metrics() call on "
            f"the sync force-warm success path; got {len(captured_emit_kwargs)}"
        )
        call = captured_emit_kwargs[0]
        # ForceWarmLatencySeconds MUST be populated (non-None) per FLAG-1.
        assert call["force_warm_latency_seconds"] is not None, (
            "BLOCK-1 production wiring: ForceWarmLatencySeconds must be "
            "populated on the sync force-warm success path; received None"
        )
        latency_val = call["force_warm_latency_seconds"]
        assert isinstance(latency_val, float)
        # Latency window includes argparse → coalescer wait → recheck;
        # expect a small but strictly-positive value in unit-test conditions.
        assert latency_val >= 0.0, f"FLAG-1 latency must be non-negative; got {latency_val!r}"
        assert call["report"] is recheck_report
        assert call["project_gid"] == "12345"

    def test_default_mode_emits_baseline_metrics_with_latency_none(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test 2: default-mode CLI (no --force-warm) emits baseline metrics; latency=None.

        ADR-006: per-CLI-invocation observability surface. Even when the
        operator runs the standard metric path (no force-warm), the four-
        metric baseline batch (MaxParquetAgeSeconds + SectionCount +
        SectionAgeP95Seconds + SectionCoverageDelta) is emitted.
        ForceWarmLatencySeconds is OMITTED (no force-warm window exists).
        """
        mock_df = pl.DataFrame(
            {
                "name": ["A", "B"],
                "section": ["ACTIVE", "ACTIVE"],
                "office_phone": ["555-1", "555-2"],
                "vertical": ["dental", "dental"],
                "mrr": ["1000", "2000"],
                "weekly_ad_spend": ["100", "200"],
            }
        )

        captured_emit_kwargs: list[dict[str, object]] = []

        def _mock_emit(**kwargs: object) -> dict[str, object]:
            captured_emit_kwargs.append(kwargs)
            return {"namespace": "Autom8y/FreshnessProbe", "metric_data": []}

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=_make_fresh_report(),
            ),
            patch(
                "autom8_asana.metrics.__main__.emit_freshness_probe_metrics",
                side_effect=_mock_emit,
            ),
        ):
            main()

        # Assert baseline emission occurred exactly once on the default path.
        assert len(captured_emit_kwargs) == 1, (
            f"Expected exactly one emit on default-mode CLI path; got {len(captured_emit_kwargs)}"
        )
        call = captured_emit_kwargs[0]
        # ForceWarmLatencySeconds MUST be None on the default (non-force-warm)
        # path per FLAG-1 contract — no window exists to measure.
        assert call["force_warm_latency_seconds"] is None, (
            "FLAG-1 contract: default-mode CLI must omit ForceWarmLatencySeconds "
            f"(force_warm_latency_seconds=None); received: "
            f"{call['force_warm_latency_seconds']!r}"
        )
        # Verify the baseline-metric inputs flow through.
        assert call["metric_name_dim"] == "active_mrr"
        # PRD C-2 backwards-compat: dollar-figure stdout preserved.
        captured = capsys.readouterr()
        assert "active_mrr:" in captured.out
        assert "$3,000.00" in captured.out

    def test_cw_emit_failure_does_not_crash_cli(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test 3: CW emission failure absorbed by safe-emit; CLI still exits normally.

        PRD C-2 backwards-compat: default-mode CLI MUST NOT change exit-code
        semantics from added observability emissions. The wrapper
        _safe_emit_freshness_probe_metrics catches any exception (boto3
        import failure, AWS_REGION resolution error, transport error) and
        emits a single stderr WARNING; the CLI's primary purpose (compute +
        print metric) succeeds.
        """
        mock_df = pl.DataFrame(
            {
                "name": ["A", "B"],
                "section": ["ACTIVE", "ACTIVE"],
                "office_phone": ["555-1", "555-2"],
                "vertical": ["dental", "dental"],
                "mrr": ["1000", "2000"],
                "weekly_ad_spend": ["100", "200"],
            }
        )

        def _exploding_emit(**kwargs: object) -> dict[str, object]:
            raise RuntimeError("CloudWatch transport unavailable")

        with (
            patch("sys.argv", ["metrics", "active_mrr"]),
            patch(
                "autom8_asana.dataframes.offline.load_project_dataframe",
                return_value=mock_df,
            ),
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=_make_fresh_report(),
            ),
            patch(
                "autom8_asana.metrics.__main__.emit_freshness_probe_metrics",
                side_effect=_exploding_emit,
            ),
        ):
            # main() must NOT raise; default-mode exit semantics unchanged.
            main()

        captured = capsys.readouterr()
        # Primary purpose: dollar figure was emitted to stdout (C-2 preserved).
        assert "active_mrr:" in captured.out
        assert "$3,000.00" in captured.out
        # Safe-emit surfaced a single stderr WARNING line.
        assert "WARNING" in captured.err
        assert "metric emission failed" in captured.err
        # No raw traceback leaked.
        assert "Traceback" not in captured.err

    def test_flag_1_boundary_latency_spans_coalescer_wait(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 4: FLAG-1 boundary — latency captured spans the coalescer wait window.

        The flag-parse-to-fresh-state window MUST include any coalescer wait
        time per FLAG-1 boundary (P4 SLI-2). This test introduces an
        artificial delay inside the mocked force_warm() coroutine and asserts
        that the captured ForceWarmLatencySeconds reflects it (window
        bounded below by the simulated coalescer wait duration).
        """
        import asyncio

        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        simulated_wait_seconds = 0.05  # 50ms simulated coalescer/Lambda window

        async def _mock_force_warm(**kwargs: object) -> object:
            await asyncio.sleep(simulated_wait_seconds)
            return self._make_sync_force_warm_result()

        captured_emit_kwargs: list[dict[str, object]] = []

        def _mock_emit(**kwargs: object) -> dict[str, object]:
            captured_emit_kwargs.append(kwargs)
            return {"namespace": "Autom8y/FreshnessProbe", "metric_data": []}

        recheck_report = _make_fresh_report(prefix="dataframes/12345/sections/")

        mock_cache = MagicMock(name="DataFrameCache")

        with (
            patch(
                "sys.argv",
                ["metrics", "--force-warm", "--wait", "--project-gid", "12345"],
            ),
            patch(
                "autom8_asana.metrics.__main__.force_warm",
                _mock_force_warm,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.metrics.freshness.FreshnessReport.from_s3_listing",
                return_value=recheck_report,
            ),
            patch(
                "autom8_asana.metrics.__main__.emit_freshness_probe_metrics",
                side_effect=_mock_emit,
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        assert len(captured_emit_kwargs) == 1
        latency = captured_emit_kwargs[0]["force_warm_latency_seconds"]
        assert latency is not None, (
            "FLAG-1 boundary: ForceWarmLatencySeconds must be populated "
            "when --force-warm --wait succeeds"
        )
        assert isinstance(latency, float)
        # The captured latency MUST be >= the simulated coalescer wait —
        # this is the structural property the FLAG-1 boundary requires.
        assert latency >= simulated_wait_seconds, (
            f"FLAG-1 boundary violation: captured latency ({latency:.4f}s) "
            f"is less than the simulated coalescer wait "
            f"({simulated_wait_seconds:.4f}s). The window is starting too "
            f"late or ending too early; re-inspect flag_parse_baseline "
            f"capture point + post-warm recheck end timestamp."
        )
