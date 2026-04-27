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
    """Work-Item 1 — argparse integration for --force-warm + --wait."""

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
        """LD-P2-2: missing CACHE_WARMER_LAMBDA_FUNCTION_NAME → friendly stderr, exit 1."""
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

    def test_force_warm_async_invokes_through_coalescer(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LD-P3-2: --force-warm (async) routes through DataFrameCacheCoalescer.

        Verifies:
          1. coalescer.try_acquire_async is awaited BEFORE boto3.invoke
          2. boto3.client('lambda').invoke is called with InvocationType=Event
          3. Exit code 0 on Lambda accept (StatusCode=202)
        """
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        # Track call order to verify coalescer-first discipline
        call_order: list[str] = []

        # Use a real coalescer; the in-process try_acquire returns True on first call
        # so the boto3 invoke runs.
        original_try_acquire = None

        async def _tracking_try_acquire(self_: object, key: str) -> bool:
            call_order.append(f"coalescer.try_acquire_async({key})")
            assert original_try_acquire is not None
            return await original_try_acquire(self_, key)

        async def _tracking_release(self_: object, key: str, success: bool) -> None:
            call_order.append(f"coalescer.release_async({key}, success={success})")

        mock_lambda_client = MagicMock()

        def _mock_invoke(**kwargs: object) -> dict[str, object]:
            call_order.append(f"lambda.invoke({kwargs.get('InvocationType')})")
            return {"StatusCode": 202}

        mock_lambda_client.invoke = _mock_invoke

        from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer

        original_try_acquire = DataFrameCacheCoalescer.try_acquire_async

        with (
            patch("sys.argv", ["metrics", "--force-warm", "--project-gid", "12345"]),
            patch(
                "autom8_asana.cache.dataframe.coalescer.DataFrameCacheCoalescer.try_acquire_async",
                _tracking_try_acquire,
            ),
            patch(
                "autom8_asana.cache.dataframe.coalescer.DataFrameCacheCoalescer.release_async",
                _tracking_release,
            ),
            patch("boto3.client", return_value=mock_lambda_client),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        # CRITICAL: coalescer.try_acquire_async MUST appear before lambda.invoke
        # to satisfy LD-P3-2 (coalescer-routed, NOT direct invoke).
        coalescer_acquire_idx = next(
            (i for i, c in enumerate(call_order) if "try_acquire_async" in c), -1
        )
        invoke_idx = next((i for i, c in enumerate(call_order) if "lambda.invoke" in c), -1)
        assert coalescer_acquire_idx >= 0, (
            f"coalescer.try_acquire_async never called; call_order={call_order}"
        )
        assert invoke_idx >= 0, f"lambda.invoke never called; call_order={call_order}"
        assert coalescer_acquire_idx < invoke_idx, (
            f"LD-P3-2 violation: lambda.invoke called BEFORE coalescer acquire; "
            f"call_order={call_order}"
        )

        # Verify async InvocationType
        assert any("Event" in c for c in call_order), (
            f"Expected InvocationType=Event for default async path; call_order={call_order}"
        )

        captured = capsys.readouterr()
        assert "force-warm invoked" in captured.err.lower()

    def test_force_warm_wait_uses_request_response(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force-warm --wait uses InvocationType=RequestResponse per P2 §4."""
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        captured_invocation_type: dict[str, object] = {}

        mock_lambda_client = MagicMock()

        def _mock_invoke(**kwargs: object) -> dict[str, object]:
            captured_invocation_type["type"] = kwargs.get("InvocationType")
            # Sync success: payload is JSON body, no FunctionError
            payload_mock = MagicMock()
            payload_mock.read.return_value = b'{"success": true}'
            return {"StatusCode": 200, "Payload": payload_mock}

        mock_lambda_client.invoke = _mock_invoke

        with (
            patch(
                "sys.argv",
                ["metrics", "--force-warm", "--wait", "--project-gid", "12345"],
            ),
            patch("boto3.client", return_value=mock_lambda_client),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

        assert captured_invocation_type["type"] == "RequestResponse", (
            f"Expected --wait to use InvocationType=RequestResponse; "
            f"got {captured_invocation_type['type']}"
        )

        captured = capsys.readouterr()
        assert "sync" in captured.err.lower() or "L1 invalidated" in captured.err

    def test_force_warm_lambda_function_error_exits_1(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force-warm --wait exits 1 when Lambda reports FunctionError."""
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "autom8-s3")
        monkeypatch.setenv(_FORCE_WARM_REQUIRED_ENV, "test-warmer-fn")

        mock_lambda_client = MagicMock()

        def _mock_invoke(**kwargs: object) -> dict[str, object]:
            payload_mock = MagicMock()
            payload_mock.read.return_value = b'{"errorMessage": "boom"}'
            return {
                "StatusCode": 200,
                "FunctionError": "Unhandled",
                "Payload": payload_mock,
            }

        mock_lambda_client.invoke = _mock_invoke

        with (
            patch(
                "sys.argv",
                ["metrics", "--force-warm", "--wait", "--project-gid", "12345"],
            ),
            patch("boto3.client", return_value=mock_lambda_client),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "FunctionError" in captured.err

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
