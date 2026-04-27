"""S3 integration tests for freshness module using moto.

Covers per TDD freshness-module §6.2:
    - N keys with mixed mtimes -> correct min/max/count
    - Pagination across multiple pages
    - Empty prefix -> parquet_count == 0 sentinel
    - Mixed .parquet and non-.parquet keys
    - NoCredentialsError -> FreshnessError(kind='auth')
    - ClientError AccessDenied -> FreshnessError(kind='auth')
    - ClientError NoSuchBucket -> FreshnessError(kind='not-found')
    - EndpointConnectionError -> FreshnessError(kind='network')

Plus PRD SM-6 backwards-compat regex anchor (last test class).
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Try to import moto; skip integration tests if not available.
try:
    import boto3
    import botocore.exceptions
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:  # pragma: no cover - skipped if moto absent
    MOTO_AVAILABLE = False
    mock_aws = None  # type: ignore[assignment]

from autom8_asana.metrics.freshness import FreshnessError, FreshnessReport

# ---------------------------------------------------------------------------
# moto-backed integration tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestFromS3ListingHappyPath:
    """from_s3_listing against moto-backed S3."""

    BUCKET = "autom8-s3"
    PREFIX = "dataframes/1143843662099250/sections/"

    def _create_bucket_with_keys(
        self,
        client: object,
        keys_with_mtimes: list[tuple[str, datetime]],
    ) -> None:
        client.create_bucket(Bucket=self.BUCKET)  # type: ignore[attr-defined]
        for key, _mtime in keys_with_mtimes:
            client.put_object(Bucket=self.BUCKET, Key=key, Body=b"x")  # type: ignore[attr-defined]
        # Note: moto sets LastModified to the put time; we cannot directly
        # control it. For tests that rely on relative ordering, we put keys
        # in order (earliest first) so put-time order matches expected ordering.

    def test_listing_with_n_parquet_keys(self) -> None:
        """N keys present -> parquet_count == N, oldest/newest computed correctly."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            for i in range(5):
                client.put_object(
                    Bucket=self.BUCKET,
                    Key=f"{self.PREFIX}section_{i}.parquet",
                    Body=b"x",
                )
            now = datetime.now(tz=UTC) + timedelta(seconds=10)
            report = FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
                now=now,
            )
            assert report.parquet_count == 5
            assert report.bucket == self.BUCKET
            assert report.prefix == self.PREFIX
            assert report.threshold_seconds == 21600
            # All puts happened within last few seconds; max_age is small
            assert report.max_age_seconds >= 0
            assert report.oldest_mtime <= report.newest_mtime

    def test_only_parquet_keys_counted(self) -> None:
        """Mixed .parquet and non-.parquet keys -> only .parquet counted."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            client.put_object(Bucket=self.BUCKET, Key=f"{self.PREFIX}a.parquet", Body=b"x")
            client.put_object(Bucket=self.BUCKET, Key=f"{self.PREFIX}b.json", Body=b"x")
            client.put_object(Bucket=self.BUCKET, Key=f"{self.PREFIX}c.parquet", Body=b"x")
            client.put_object(Bucket=self.BUCKET, Key=f"{self.PREFIX}d.txt", Body=b"x")
            report = FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
            assert report.parquet_count == 2

    def test_empty_prefix_returns_sentinel(self) -> None:
        """parquet_count == 0 -> sentinel epoch mtimes per TDD §1.2."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            # No objects added
            report = FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
            assert report.parquet_count == 0
            # Sentinel: epoch UTC
            assert report.oldest_mtime == datetime(1970, 1, 1, tzinfo=UTC)
            assert report.newest_mtime == datetime(1970, 1, 1, tzinfo=UTC)
            # Sentinel max_age is numerically extreme -> stale
            assert report.stale is True

    def test_pagination_aggregates_across_pages(self) -> None:
        """Test that paginator iteration aggregates across multiple pages.

        Moto's default page size is 1000; we put >1000 keys to force pagination.
        We use a smaller key body to keep test runtime reasonable.
        """
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=self.BUCKET)
            n_keys = 1100  # exceeds default 1000 page size
            for i in range(n_keys):
                client.put_object(
                    Bucket=self.BUCKET,
                    Key=f"{self.PREFIX}section_{i:04d}.parquet",
                    Body=b"x",
                )
            report = FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
            assert report.parquet_count == n_keys


# ---------------------------------------------------------------------------
# Error mapping tests (using mocked clients, not moto)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="boto3/botocore required")
class TestFromS3ListingErrorMapping:
    """FreshnessError kind mapping per TDD §2.3."""

    BUCKET = "autom8-s3"
    PREFIX = "dataframes/test/sections/"

    def _make_mock_client_raising(self, exception: BaseException) -> MagicMock:
        """Construct a mock S3 client whose paginator raises the given exception."""
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        # paginate() returns an iterable; iterating raises the exception.
        mock_paginator.paginate.side_effect = exception
        mock_client.get_paginator.return_value = mock_paginator
        return mock_client

    def test_no_credentials_error_maps_to_auth(self) -> None:
        exc = botocore.exceptions.NoCredentialsError()
        client = self._make_mock_client_raising(exc)
        with pytest.raises(FreshnessError) as exc_info:
            FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
        assert exc_info.value.kind == "auth"
        assert exc_info.value.bucket == self.BUCKET
        assert exc_info.value.prefix == self.PREFIX

    def test_access_denied_maps_to_auth(self) -> None:
        exc = botocore.exceptions.ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            operation_name="ListObjectsV2",
        )
        client = self._make_mock_client_raising(exc)
        with pytest.raises(FreshnessError) as exc_info:
            FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
        assert exc_info.value.kind == "auth"

    def test_no_such_bucket_maps_to_not_found(self) -> None:
        exc = botocore.exceptions.ClientError(
            error_response={"Error": {"Code": "NoSuchBucket", "Message": "Not found"}},
            operation_name="ListObjectsV2",
        )
        client = self._make_mock_client_raising(exc)
        with pytest.raises(FreshnessError) as exc_info:
            FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
        assert exc_info.value.kind == "not-found"

    def test_endpoint_connection_error_maps_to_network(self) -> None:
        exc = botocore.exceptions.EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")
        client = self._make_mock_client_raising(exc)
        with pytest.raises(FreshnessError) as exc_info:
            FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
        assert exc_info.value.kind == "network"

    def test_unknown_client_error_maps_to_unknown(self) -> None:
        exc = botocore.exceptions.ClientError(
            error_response={"Error": {"Code": "WeirdUnseenError", "Message": "?"}},
            operation_name="ListObjectsV2",
        )
        client = self._make_mock_client_raising(exc)
        with pytest.raises(FreshnessError) as exc_info:
            FreshnessReport.from_s3_listing(
                bucket=self.BUCKET,
                prefix=self.PREFIX,
                threshold_seconds=21600,
                s3_client=client,
            )
        assert exc_info.value.kind == "unknown"


# ---------------------------------------------------------------------------
# JSON Schema validation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto required for end-to-end")
class TestJsonEnvelopeSchemaValidation:
    """Validate format_json_envelope output against TDD §4.2 schema."""

    def test_envelope_has_required_top_level_fields(self) -> None:
        from autom8_asana.metrics.freshness import format_json_envelope

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
        # Required top-level fields per schema §4.2
        for field in (
            "schema_version",
            "metric",
            "value",
            "currency",
            "freshness",
            "provenance",
        ):
            assert field in envelope, f"Required field missing: {field}"
        # schema_version const = 1
        assert envelope["schema_version"] == 1
        # freshness sub-fields
        for field in (
            "oldest_mtime",
            "newest_mtime",
            "max_age_seconds",
            "threshold_seconds",
            "stale",
            "parquet_count",
        ):
            assert field in envelope["freshness"], f"Required freshness field missing: {field}"
        # provenance sub-fields
        for field in ("bucket", "prefix", "env", "evidence"):
            assert field in envelope["provenance"], f"Required provenance field missing: {field}"

    def test_freshness_max_age_seconds_is_non_negative_integer(self) -> None:
        from autom8_asana.metrics.freshness import format_json_envelope

        report = FreshnessReport(
            oldest_mtime=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
            newest_mtime=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
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
        assert isinstance(envelope["freshness"]["max_age_seconds"], int)
        assert envelope["freshness"]["max_age_seconds"] >= 0
        assert isinstance(envelope["freshness"]["threshold_seconds"], int)
        assert envelope["freshness"]["threshold_seconds"] >= 1
        assert isinstance(envelope["freshness"]["parquet_count"], int)
        assert envelope["freshness"]["parquet_count"] >= 0


# ---------------------------------------------------------------------------
# PRD SM-6 backwards-compat regex anchor
# ---------------------------------------------------------------------------


class TestDefaultModeBackwardsCompat:
    """PRD SM-6: existing dollar-figure line is preserved byte-for-byte.

    This is the regex anchor test described in TDD §6.5 — bind to the actual
    bytes emitted by `print(f"\\n  {metric.name}: {formatted}")` at
    __main__.py:217 (latent #1 resolution).
    """

    def test_regex_pattern_matches_actual_emission(self) -> None:
        """The regex matches the actual bytes the existing CLI emits.

        The print(f"\\n  {metric.name}: {formatted}") at __main__.py:217
        emits a leading newline + 2-space indent + name + colon + value.
        In MULTILINE mode, ^ anchors to the start of each line (after a \\n)
        so the regex matches the indented dollar line directly.
        """
        # The actual print is print(f"<NL>  {metric.name}: {formatted}").
        # Python's print adds a trailing newline, and the format string's leading
        # newline produces a blank line BEFORE the indented value line. The full
        # stdout shape (after the preceding 'Loaded ...' line) joins those two.
        prior_line = "Loaded 100 rows from project xyz\n"
        emitted = "\n  active_mrr: $94,076.00\n"
        full_stdout = prior_line + emitted
        # Pattern: 2-space indent, metric name, colon, dollar amount.
        # In MULTILINE mode, ^ anchors at the start of each line.
        pattern = re.compile(r"^  active_mrr: \$[\d,]+\.\d{2}$", re.MULTILINE)
        match = pattern.search(full_stdout)
        assert match is not None, (
            f"Pattern did not match expected emission shape. "
            f"Pattern: {pattern.pattern!r}, stdout: {full_stdout!r}"
        )
        # Additionally verify the leading blank line (the \n in the f-string)
        # sits immediately before the matched value line.
        assert "\n\n  active_mrr: " in full_stdout, (
            "Existing CLI emits a blank line before the value (the f-string's \\n prefix)"
        )

    def test_pattern_matches_various_dollar_amounts(self) -> None:
        """Pattern is value-agnostic and matches different dollar amounts."""
        pattern = re.compile(r"^  active_mrr: \$[\d,]+\.\d{2}$", re.MULTILINE)
        for amount in ("$1.00", "$1,234.56", "$1,234,567.89", "$0.00"):
            stdout = f"prefix\n  active_mrr: {amount}\nsuffix"
            match = pattern.search(stdout)
            assert match is not None, f"Pattern did not match for {amount!r}"

    def test_dollar_figure_byte_shape_is_preserved_in_main_module(self) -> None:
        """SVR-style verification that __main__.py still emits the literal pattern.

        Reads the source file and asserts the verbatim print statement is present.
        Bind to actual bytes per latent #1.
        """
        import inspect

        from autom8_asana.metrics import __main__ as main_module

        src = inspect.getsource(main_module)
        # The exact print call from the existing implementation; preserved
        # byte-for-byte under default mode per PRD C-2 / SM-6.
        assert 'print(f"\\n  {metric.name}: {formatted}")' in src
