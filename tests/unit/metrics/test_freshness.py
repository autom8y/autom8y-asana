"""Unit tests for src/autom8_asana/metrics/freshness.py.

Covers per TDD freshness-module §6.1:
    - parse_duration_spec (valid + invalid)
    - format_duration boundary
    - format_human_lines
    - format_json_envelope
    - format_warning
    - FreshnessReport.stale property
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from autom8_asana.metrics.freshness import (
    FreshnessReport,
    format_duration,
    format_human_lines,
    format_json_envelope,
    format_warning,
    parse_duration_spec,
)

# ---------------------------------------------------------------------------
# parse_duration_spec
# ---------------------------------------------------------------------------


class TestParseDurationSpec:
    """parse_duration_spec — valid and invalid inputs per TDD §1.3."""

    @pytest.mark.parametrize(
        "spec,expected",
        [
            ("90s", 90),
            ("1s", 1),
            ("30m", 1800),
            ("1m", 60),
            ("6h", 21600),
            ("1h", 3600),
            ("23h", 82800),
            ("1d", 86400),
            ("32d", 2764800),
            # Whitespace tolerance per §1.3
            (" 6h ", 21600),
            ("6 h", 21600),
            ("\t1d\n", 86400),
        ],
    )
    def test_valid_specs(self, spec: str, expected: int) -> None:
        assert parse_duration_spec(spec) == expected

    @pytest.mark.parametrize(
        "spec",
        [
            "",
            "1h30m",  # composite forms not supported
            "6 hours",
            "-6h",
            "6",  # no unit
            "h",  # no number
            "6x",  # unknown unit
            "0s",  # zero rejected
            "0h",
            "0d",
            "6H",  # case-sensitive: uppercase rejected
            "6D",
            "abc",
            "h6",
            "6.5h",  # non-integer
        ],
    )
    def test_invalid_specs(self, spec: str) -> None:
        with pytest.raises(ValueError) as exc_info:
            parse_duration_spec(spec)
        # Error message must mention the input + the expected formats list
        msg = str(exc_info.value)
        assert "invalid duration spec" in msg
        assert "Ns/Nm/Nh/Nd" in msg

    def test_error_message_is_deterministic(self) -> None:
        """PRD AC-2.4: same input -> same byte output."""
        with pytest.raises(ValueError) as exc1:
            parse_duration_spec("bogus")
        with pytest.raises(ValueError) as exc2:
            parse_duration_spec("bogus")
        assert str(exc1.value) == str(exc2.value)


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------


class TestFormatDuration:
    """format_duration — boundary cases per TDD §6.1."""

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "0s"),
            (1, "1s"),
            (45, "45s"),
            (59, "59s"),
            (60, "1m"),
            (90, "1m"),  # truncates to whole minute
            (3599, "59m"),
            (3600, "1h 0m"),
            (3660, "1h 1m"),
            (86399, "23h 59m"),
            (86400, "1d 0h 0m"),
            (86460, "1d 0h 1m"),
            (2802960, "32d 10h 36m"),  # PRD AC-1.2 example: 32d 10h 36m
        ],
    )
    def test_format(self, seconds: int, expected: str) -> None:
        assert format_duration(seconds) == expected


# ---------------------------------------------------------------------------
# FreshnessReport.stale property
# ---------------------------------------------------------------------------


def _make_report(max_age: int, threshold: int) -> FreshnessReport:
    """Construct a FreshnessReport with controlled max_age/threshold values."""
    return FreshnessReport(
        oldest_mtime=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
        newest_mtime=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
        max_age_seconds=max_age,
        threshold_seconds=threshold,
        parquet_count=10,
        bucket="autom8-s3",
        prefix="dataframes/1143843662099250/sections/",
    )


class TestFreshnessReportStaleProperty:
    """FreshnessReport.stale — boundary semantics per TDD §1.1."""

    def test_below_threshold_fresh(self) -> None:
        report = _make_report(max_age=1000, threshold=21600)
        assert report.stale is False

    def test_at_threshold_fresh(self) -> None:
        """Equality is fresh, not stale (deterministic boundary per AC-2.4)."""
        report = _make_report(max_age=21600, threshold=21600)
        assert report.stale is False

    def test_above_threshold_stale(self) -> None:
        report = _make_report(max_age=21601, threshold=21600)
        assert report.stale is True

    def test_far_above_threshold_stale(self) -> None:
        report = _make_report(max_age=2802960, threshold=21600)
        assert report.stale is True


# ---------------------------------------------------------------------------
# format_human_lines
# ---------------------------------------------------------------------------


class TestFormatHumanLines:
    """format_human_lines — PRD AC-1.2 stdout shape."""

    def test_returns_list_of_one_line(self) -> None:
        report = FreshnessReport(
            oldest_mtime=datetime(2026, 3, 26, 4, 17, tzinfo=UTC),
            newest_mtime=datetime(2026, 4, 27, 14, 1, tzinfo=UTC),
            max_age_seconds=2802960,
            threshold_seconds=21600,
            parquet_count=71,
            bucket="autom8-s3",
            prefix="dataframes/1143843662099250/sections/",
        )
        lines = format_human_lines(report)
        assert len(lines) == 1
        assert lines[0] == (
            "parquet mtime: oldest=2026-03-26 04:17 UTC, "
            "newest=2026-04-27 14:01 UTC, max_age=32d 10h 36m"
        )


# ---------------------------------------------------------------------------
# format_warning
# ---------------------------------------------------------------------------


class TestFormatWarning:
    """format_warning — PRD AC-2.1 stderr shape."""

    def test_warning_format(self) -> None:
        report = _make_report(max_age=2802960, threshold=21600)
        warning = format_warning(report)
        assert warning == "WARNING: data older than 6h 0m (max_age=32d 10h 36m)"


# ---------------------------------------------------------------------------
# format_json_envelope
# ---------------------------------------------------------------------------


class TestFormatJsonEnvelope:
    """format_json_envelope — PRD AC-3.1 envelope schema."""

    def test_envelope_shape(self) -> None:
        report = FreshnessReport(
            oldest_mtime=datetime(2026, 3, 26, 4, 17, 0, tzinfo=UTC),
            newest_mtime=datetime(2026, 4, 27, 14, 1, 0, tzinfo=UTC),
            max_age_seconds=2802960,
            threshold_seconds=21600,
            parquet_count=71,
            bucket="autom8-s3",
            prefix="dataframes/1143843662099250/sections/",
        )
        envelope = format_json_envelope(
            report=report,
            value=94076.00,
            metric_name="active_mrr",
            currency="USD",
            env="production",
            bucket_evidence="stakeholder-affirmation-2026-04-27",
        )
        assert envelope == {
            "schema_version": 1,
            "metric": "active_mrr",
            "value": 94076.00,
            "currency": "USD",
            "freshness": {
                "oldest_mtime": "2026-03-26T04:17:00Z",
                "newest_mtime": "2026-04-27T14:01:00Z",
                "max_age_seconds": 2802960,
                "threshold_seconds": 21600,
                "stale": True,
                "parquet_count": 71,
            },
            "provenance": {
                "bucket": "autom8-s3",
                "prefix": "dataframes/1143843662099250/sections/",
                "env": "production",
                "evidence": "stakeholder-affirmation-2026-04-27",
            },
        }

    def test_envelope_round_trip_through_json(self) -> None:
        """Determinism: json.dumps(sort_keys=True) is reproducible."""
        report = _make_report(max_age=1000, threshold=21600)
        envelope = format_json_envelope(
            report=report,
            value=42.0,
            metric_name="test_metric",
            currency="USD",
            env="production",
            bucket_evidence="test-evidence",
        )
        serialized = json.dumps(envelope, sort_keys=True, indent=2)
        round_tripped = json.loads(serialized)
        assert round_tripped == envelope

    def test_envelope_with_null_value(self) -> None:
        """value can be None (per JSON schema spec; AC-5.3 alternative form)."""
        report = _make_report(max_age=1000, threshold=21600)
        envelope = format_json_envelope(
            report=report,
            value=None,
            metric_name="active_mrr",
            currency="USD",
            env="production",
            bucket_evidence="test-evidence",
        )
        assert envelope["value"] is None
        # JSON serialization should represent None as null
        assert '"value": null' in json.dumps(envelope, indent=2)

    def test_envelope_stale_field_reflects_threshold(self) -> None:
        """freshness.stale derives from max_age vs threshold per AC-3.3."""
        report_fresh = _make_report(max_age=1000, threshold=21600)
        report_stale = _make_report(max_age=86400, threshold=21600)

        env_fresh = format_json_envelope(
            report=report_fresh,
            value=1.0,
            metric_name="m",
            currency="USD",
            env="production",
            bucket_evidence="e",
        )
        env_stale = format_json_envelope(
            report=report_stale,
            value=1.0,
            metric_name="m",
            currency="USD",
            env="production",
            bucket_evidence="e",
        )
        assert env_fresh["freshness"]["stale"] is False
        assert env_stale["freshness"]["stale"] is True

    def test_iso_format_uses_z_suffix(self) -> None:
        """Determinism: ISO-8601 with Z suffix, not +00:00, per TDD §5.2."""
        report = FreshnessReport(
            oldest_mtime=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            newest_mtime=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            max_age_seconds=0,
            threshold_seconds=21600,
            parquet_count=1,
            bucket="b",
            prefix="p",
        )
        envelope = format_json_envelope(
            report=report,
            value=1.0,
            metric_name="m",
            currency="USD",
            env="production",
            bucket_evidence="e",
        )
        assert envelope["freshness"]["oldest_mtime"].endswith("Z")
        assert "+00:00" not in envelope["freshness"]["oldest_mtime"]
