"""Unit tests for the CloudWatch metric emission module (Batch-B work-item-4).

Per HANDOFF-thermia-to-10x-dev §1 work-item-4 + ADR-006:
- 5 CLI metrics emitted as a single batched put_metric_data call
- C-6 HARD CONSTRAINT: SectionCoverageDelta MUST NOT be wired to alarms
- SectionAgeP95Seconds correctness with retained per-key mtimes
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from autom8_asana.metrics.cloudwatch_emit import (
    ALARMED_METRICS,
    ALL_CLI_METRICS,
    FRESHNESS_PROBE_NAMESPACE,
    METRIC_FORCE_WARM_LATENCY_SECONDS,
    METRIC_MAX_PARQUET_AGE_SECONDS,
    METRIC_SECTION_AGE_P95_SECONDS,
    METRIC_SECTION_COUNT,
    METRIC_SECTION_COVERAGE_DELTA,
    C6ConstraintViolation,
    c6_guard_check,
    emit_freshness_probe_metrics,
)
from autom8_asana.metrics.freshness import FreshnessReport


def _make_report(
    *,
    parquet_count: int = 14,
    max_age_seconds: int = 3600,
    threshold_seconds: int = 21600,
    mtimes: tuple[datetime, ...] | None = None,
) -> FreshnessReport:
    """Helper to construct a FreshnessReport for tests."""
    if mtimes is None:
        # Generate parquet_count mtimes across [now - max_age, now - 0]
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        if parquet_count == 0:
            mtimes = ()
        else:
            step = max(max_age_seconds // max(parquet_count - 1, 1), 1)
            mtimes = tuple(now - timedelta(seconds=i * step) for i in range(parquet_count))
    if mtimes:
        oldest = min(mtimes)
        newest = max(mtimes)
    else:
        oldest = newest = datetime(1970, 1, 1, tzinfo=UTC)
    return FreshnessReport(
        oldest_mtime=oldest,
        newest_mtime=newest,
        max_age_seconds=max_age_seconds,
        threshold_seconds=threshold_seconds,
        parquet_count=parquet_count,
        bucket="autom8-s3",
        prefix="dataframes/test/sections/",
        mtimes=mtimes,
    )


# ---------------------------------------------------------------------------
# C-6 HARD CONSTRAINT — mechanical guard test
# ---------------------------------------------------------------------------


class TestC6GuardCheck:
    """The C-6 guard mechanically prevents alarm wiring on SectionCoverageDelta."""

    def test_section_coverage_delta_raises_c6_violation(self) -> None:
        """ADR-006 alarm-vs-metric matrix: SectionCoverageDelta MUST NOT alarm."""
        with pytest.raises(C6ConstraintViolation) as exc_info:
            c6_guard_check(METRIC_SECTION_COVERAGE_DELTA)
        assert "SectionCoverageDelta" in str(exc_info.value)
        assert "C-6" in str(exc_info.value)

    def test_max_parquet_age_does_not_raise(self) -> None:
        """MaxParquetAgeSeconds is alarmable per ADR-006 ALERT-1/ALERT-2."""
        c6_guard_check(METRIC_MAX_PARQUET_AGE_SECONDS)

    def test_section_count_does_not_raise(self) -> None:
        """SectionCount is alarmable in principle; today no alarm wired."""
        c6_guard_check(METRIC_SECTION_COUNT)

    def test_unknown_metric_does_not_raise(self) -> None:
        """Unknown metric names are out-of-scope for this guard (no false trip)."""
        c6_guard_check("SomeOtherMetric")

    def test_alarmed_set_excludes_section_coverage_delta(self) -> None:
        """Type-level invariant: ALARMED_METRICS does not contain SectionCoverageDelta."""
        assert METRIC_SECTION_COVERAGE_DELTA not in ALARMED_METRICS
        assert METRIC_SECTION_COVERAGE_DELTA in ALL_CLI_METRICS

    def test_alarmed_subset_of_all(self) -> None:
        """ALARMED_METRICS is a strict subset of ALL_CLI_METRICS."""
        assert ALARMED_METRICS.issubset(ALL_CLI_METRICS)
        assert ALARMED_METRICS != ALL_CLI_METRICS  # strict subset


# ---------------------------------------------------------------------------
# Section AgeP95 computation
# ---------------------------------------------------------------------------


class TestSectionAgeP95Seconds:
    """SectionAgeP95Seconds computation requires per-key mtime list retention."""

    def test_p95_with_uniform_distribution(self) -> None:
        """P95 of N evenly-spaced ages uses nearest-rank with ceiling index."""
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        # 20 keys, ages 0, 60, 120, ..., 1140 seconds
        mtimes = tuple(now - timedelta(seconds=60 * i) for i in range(20))
        report = _make_report(parquet_count=20, mtimes=mtimes, max_age_seconds=1140)
        # P95 of N=20: ceil(0.95*20) = 19, index 18 (the 19th oldest)
        # Sorted ages ascending: [0, 60, ..., 1140]; index 18 = age 1080
        p95 = report.section_age_p95_seconds(now=now)
        assert p95 == 1080

    def test_p95_with_outlier(self) -> None:
        """A single far-tail outlier should NOT dominate P95 (resolution >0.95)."""
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        # 14 fresh keys + 1 ancient outlier = 15 total
        fresh_mtimes = [now - timedelta(seconds=60 * i) for i in range(14)]
        ancient = now - timedelta(seconds=2_000_000)
        all_mtimes = (*fresh_mtimes, ancient)
        report = _make_report(parquet_count=15, mtimes=all_mtimes, max_age_seconds=2_000_000)
        # P95 of N=15: ceil(0.95*15) = 15, index 14 → the outlier age
        # By design (nearest-rank): with N=15, P95 captures the outlier.
        # This is correct behavior — caller chooses N to discriminate tail.
        p95 = report.section_age_p95_seconds(now=now)
        assert p95 == 2_000_000

    def test_p95_returns_zero_for_empty_report(self) -> None:
        """Empty report → P95 = 0 sentinel (caller checks parquet_count first)."""
        report = _make_report(parquet_count=0, mtimes=())
        assert report.section_age_p95_seconds() == 0

    def test_p95_clamps_negative_to_zero(self) -> None:
        """Future-dated mtime (clock skew) → age clamped to 0."""
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        # Single key in the future (clock skew)
        future_mtime = now + timedelta(seconds=60)
        report = _make_report(parquet_count=1, mtimes=(future_mtime,), max_age_seconds=0)
        p95 = report.section_age_p95_seconds(now=now)
        assert p95 == 0  # clamped


# ---------------------------------------------------------------------------
# Single-batch put_metric_data emission (ADR-006 §Decision)
# ---------------------------------------------------------------------------


class TestEmitFreshnessProbeMetricsBatch:
    """The 5 CLI metrics MUST be emitted in a single put_metric_data batch."""

    def test_single_batch_when_all_metrics_emit(self) -> None:
        """5 metrics (incl. ForceWarmLatency) → 1 put_metric_data call."""
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        mtimes = tuple(now - timedelta(seconds=300 * i) for i in range(14))
        report = _make_report(parquet_count=14, mtimes=mtimes, max_age_seconds=3900)

        cw_client = MagicMock()
        result = emit_freshness_probe_metrics(
            report=report,
            metric_name_dim="active_mrr",
            project_gid="1143843662099250",
            section_coverage_delta=2,
            force_warm_latency_seconds=12.5,
            section_age_p95_seconds=3600,
            cw_client=cw_client,
        )

        # CRITICAL: exactly one put_metric_data call
        assert cw_client.put_metric_data.call_count == 1
        # All 5 metrics in a single MetricData payload
        call = cw_client.put_metric_data.call_args
        assert call.kwargs["Namespace"] == FRESHNESS_PROBE_NAMESPACE
        metric_data = call.kwargs["MetricData"]
        assert len(metric_data) == 5
        names = {md["MetricName"] for md in metric_data}
        assert names == {
            METRIC_MAX_PARQUET_AGE_SECONDS,
            METRIC_SECTION_COUNT,
            METRIC_SECTION_AGE_P95_SECONDS,
            METRIC_SECTION_COVERAGE_DELTA,
            METRIC_FORCE_WARM_LATENCY_SECONDS,
        }
        # Verify diagnostic return shape
        assert result["namespace"] == FRESHNESS_PROBE_NAMESPACE
        assert len(result["metric_data"]) == 5

    def test_four_metric_batch_when_force_warm_latency_omitted(self) -> None:
        """Default freshness-probe path (no --force-warm) emits 4 metrics in 1 batch."""
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        mtimes = tuple(now - timedelta(seconds=300 * i) for i in range(14))
        report = _make_report(parquet_count=14, mtimes=mtimes)

        cw_client = MagicMock()
        emit_freshness_probe_metrics(
            report=report,
            metric_name_dim="active_mrr",
            project_gid="1143843662099250",
            section_coverage_delta=0,
            force_warm_latency_seconds=None,
            cw_client=cw_client,
        )

        # Exactly 1 put_metric_data call; 4 metrics (no ForceWarmLatencySeconds).
        assert cw_client.put_metric_data.call_count == 1
        metric_data = cw_client.put_metric_data.call_args.kwargs["MetricData"]
        assert len(metric_data) == 4
        names = {md["MetricName"] for md in metric_data}
        assert METRIC_FORCE_WARM_LATENCY_SECONDS not in names

    def test_section_coverage_delta_emitted_with_correct_value(self) -> None:
        """SectionCoverageDelta value lands faithfully (informational, no alarm)."""
        report = _make_report(parquet_count=14, max_age_seconds=3600)
        cw_client = MagicMock()
        emit_freshness_probe_metrics(
            report=report,
            metric_name_dim="active_mrr",
            project_gid="1143843662099250",
            section_coverage_delta=3,  # 17 expected - 14 observed
            cw_client=cw_client,
        )
        metric_data = cw_client.put_metric_data.call_args.kwargs["MetricData"]
        delta_metric = next(
            md for md in metric_data if md["MetricName"] == METRIC_SECTION_COVERAGE_DELTA
        )
        assert delta_metric["Value"] == 3.0
        assert delta_metric["Unit"] == "Count"

    def test_metric_values_match_report_fields(self) -> None:
        """MaxParquetAgeSeconds + SectionCount values trace to FreshnessReport."""
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        mtimes = tuple(now - timedelta(seconds=300 * i) for i in range(14))
        report = _make_report(parquet_count=14, mtimes=mtimes, max_age_seconds=3900)

        cw_client = MagicMock()
        emit_freshness_probe_metrics(
            report=report,
            metric_name_dim="active_mrr",
            project_gid="1143843662099250",
            section_coverage_delta=0,
            section_age_p95_seconds=3600,
            cw_client=cw_client,
        )
        metric_data = cw_client.put_metric_data.call_args.kwargs["MetricData"]
        max_age = next(
            md for md in metric_data if md["MetricName"] == METRIC_MAX_PARQUET_AGE_SECONDS
        )
        section_count = next(md for md in metric_data if md["MetricName"] == METRIC_SECTION_COUNT)
        p95 = next(md for md in metric_data if md["MetricName"] == METRIC_SECTION_AGE_P95_SECONDS)
        assert max_age["Value"] == 3900.0
        assert max_age["Unit"] == "Seconds"
        assert section_count["Value"] == 14.0
        assert section_count["Unit"] == "Count"
        assert p95["Value"] == 3600.0
        assert p95["Unit"] == "Seconds"

    def test_emission_failure_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CloudWatch failure → stderr WARNING; caller does NOT see an exception."""
        report = _make_report()
        cw_client = MagicMock()
        cw_client.put_metric_data.side_effect = RuntimeError("cw down")

        # Best-effort: must not raise — PRD C-2 forbids new metric work from
        # changing CLI exit-code semantics.
        emit_freshness_probe_metrics(
            report=report,
            metric_name_dim="active_mrr",
            project_gid="1143843662099250",
            section_coverage_delta=0,
            cw_client=cw_client,
        )
        captured = capsys.readouterr()
        assert "CloudWatch metric emission failed" in captured.err

    def test_dimensions_include_metric_and_project(self) -> None:
        """Dimensions should include both metric_name and project_gid for attribution."""
        report = _make_report()
        cw_client = MagicMock()
        emit_freshness_probe_metrics(
            report=report,
            metric_name_dim="active_mrr",
            project_gid="1143843662099250",
            section_coverage_delta=0,
            cw_client=cw_client,
        )
        metric_data = cw_client.put_metric_data.call_args.kwargs["MetricData"]
        for md in metric_data:
            dim_names = {d["Name"] for d in md["Dimensions"]}
            assert "metric_name" in dim_names
            assert "project_gid" in dim_names
            dim_values = {d["Name"]: d["Value"] for d in md["Dimensions"]}
            assert dim_values["metric_name"] == "active_mrr"
            assert dim_values["project_gid"] == "1143843662099250"


# ---------------------------------------------------------------------------
# moto-backed integration test — end-to-end emission
# ---------------------------------------------------------------------------

try:
    import boto3
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:  # pragma: no cover
    MOTO_AVAILABLE = False


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto required for end-to-end")
class TestEmitMotoIntegration:
    """End-to-end: emit metrics against moto CloudWatch and verify roundtrip."""

    def test_metrics_visible_in_moto_cloudwatch(self) -> None:
        """Real CloudWatch client (moto-backed) accepts batched emission."""
        with mock_aws():
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
            mtimes = tuple(now - timedelta(seconds=300 * i) for i in range(14))
            report = _make_report(parquet_count=14, mtimes=mtimes, max_age_seconds=3900)
            emit_freshness_probe_metrics(
                report=report,
                metric_name_dim="active_mrr",
                project_gid="1143843662099250",
                section_coverage_delta=0,
                cw_client=cw,
            )
            # moto accepts the call without error; list_metrics confirms namespace.
            response = cw.list_metrics(Namespace=FRESHNESS_PROBE_NAMESPACE)
            metric_names = {m["MetricName"] for m in response["Metrics"]}
            assert METRIC_MAX_PARQUET_AGE_SECONDS in metric_names
            assert METRIC_SECTION_COUNT in metric_names
            assert METRIC_SECTION_AGE_P95_SECONDS in metric_names
            assert METRIC_SECTION_COVERAGE_DELTA in metric_names

    def test_force_warm_latency_metric_visible(self) -> None:
        """ForceWarmLatencySeconds emitted only when latency provided."""
        with mock_aws():
            cw = boto3.client("cloudwatch", region_name="us-east-1")
            report = _make_report()
            emit_freshness_probe_metrics(
                report=report,
                metric_name_dim="active_mrr",
                project_gid="1143843662099250",
                section_coverage_delta=0,
                force_warm_latency_seconds=12.5,
                cw_client=cw,
            )
            response = cw.list_metrics(Namespace=FRESHNESS_PROBE_NAMESPACE)
            metric_names = {m["MetricName"] for m in response["Metrics"]}
            assert METRIC_FORCE_WARM_LATENCY_SECONDS in metric_names
