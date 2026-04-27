"""Freshness signal module for the metrics CLI.

Implements per ADR-001 (Metrics CLI declares data-source freshness alongside
scalar value) and TDD freshness-module.tdd.md §1.

Public surface:
    - FreshnessReport (frozen dataclass + classmethod factory)
    - FreshnessError (exception class with `kind` attribute)
    - parse_duration_spec(s: str) -> int
    - format_duration(seconds: int) -> str
    - format_human_lines(report) -> list[str]
    - format_json_envelope(report, value, ...) -> dict
    - format_warning(report) -> str

S3 access uses list_objects_v2 paginator (NOT head_object) per TDD §2.1.
All datetimes are timezone-aware UTC.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Exception class
# ---------------------------------------------------------------------------


class FreshnessError(Exception):
    """Raised by from_s3_listing on S3 access failures.

    The `kind` attribute is one of: 'auth', 'not-found', 'network', 'unknown'.
    The integration layer maps `kind` to the AC-4.1/4.2/4.3 stderr lines.
    """

    KIND_AUTH = "auth"
    KIND_NOT_FOUND = "not-found"
    KIND_NETWORK = "network"
    KIND_UNKNOWN = "unknown"

    def __init__(
        self,
        kind: str,
        bucket: str,
        prefix: str,
        underlying: BaseException,
    ) -> None:
        self.kind = kind
        self.bucket = bucket
        self.prefix = prefix
        self.underlying = underlying
        super().__init__(f"freshness read failed ({kind}): s3://{bucket}/{prefix} — {underlying!r}")


# ---------------------------------------------------------------------------
# FreshnessReport dataclass
# ---------------------------------------------------------------------------


# Sentinel for "no parquets found" — epoch UTC. Numerically extreme staleness
# allows the CLI integration layer to detect zero-parquet conditions per
# TDD §1.2 / §3.4.
_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class FreshnessReport:
    """Immutable freshness signal derived from S3 parquet listing.

    All datetimes are timezone-aware UTC. `stale` is a derived predicate
    (max_age_seconds > threshold_seconds), exposed as an attribute so consumers
    do not re-derive the comparison.

    When `parquet_count == 0`, oldest_mtime and newest_mtime are sentinel epoch
    values (1970-01-01T00:00Z); CLI integration layer detects this case and
    emits an empty-prefix error per TDD §3.4.
    """

    oldest_mtime: datetime
    newest_mtime: datetime
    max_age_seconds: int
    threshold_seconds: int
    parquet_count: int
    bucket: str
    prefix: str

    @property
    def stale(self) -> bool:
        """True iff max_age_seconds strictly exceeds threshold_seconds.

        Exclusive comparison — equality is fresh, not stale.
        """
        return self.max_age_seconds > self.threshold_seconds

    @classmethod
    def from_s3_listing(
        cls,
        bucket: str,
        prefix: str,
        threshold_seconds: int,
        *,
        s3_client: Any | None = None,
        now: datetime | None = None,
    ) -> FreshnessReport:
        """Build a FreshnessReport by listing s3://{bucket}/{prefix}.

        Args:
            bucket: S3 bucket name.
            prefix: Key prefix (typically ends with '/').
            threshold_seconds: Carried into the report and used to derive `stale`.
            s3_client: boto3 S3 client; if None, constructed via boto3.client("s3", region_name=...)
                with the same region resolution as dataframes/offline.py.
            now: Override for datetime.now(tz=UTC); injectable for deterministic
                tests.

        Returns:
            FreshnessReport instance. Returns sentinel report with parquet_count=0
            when no .parquet keys are found under prefix.

        Raises:
            FreshnessError: wraps boto3 NoCredentialsError, ClientError, and
                network failures into a single exception class with a `kind`
                attribute.
        """
        # Lazy boto3 import to keep the freshness module importable in
        # environments where boto3 may not be available at import time.
        import boto3
        import botocore.exceptions

        if s3_client is None:
            region = os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
            s3_client = boto3.client("s3", region_name=region)

        if now is None:
            now = datetime.now(tz=UTC)

        try:
            paginator = s3_client.get_paginator("list_objects_v2")
            min_mtime: datetime | None = None
            max_mtime: datetime | None = None
            count = 0
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not key.endswith(".parquet"):
                        continue
                    mtime = obj.get("LastModified")
                    if mtime is None:
                        continue
                    count += 1
                    if min_mtime is None or mtime < min_mtime:
                        min_mtime = mtime
                    if max_mtime is None or mtime > max_mtime:
                        max_mtime = mtime
        except botocore.exceptions.NoCredentialsError as e:
            raise FreshnessError(FreshnessError.KIND_AUTH, bucket, prefix, e) from e
        except botocore.exceptions.ClientError as e:
            code = (e.response or {}).get("Error", {}).get("Code", "")
            if code in {
                "AccessDenied",
                "403",
                "InvalidAccessKeyId",
                "SignatureDoesNotMatch",
            }:
                kind = FreshnessError.KIND_AUTH
            elif code in {"NoSuchBucket", "NoSuchKey", "404"}:
                kind = FreshnessError.KIND_NOT_FOUND
            else:
                kind = FreshnessError.KIND_UNKNOWN
            raise FreshnessError(kind, bucket, prefix, e) from e
        except (
            botocore.exceptions.EndpointConnectionError,
            botocore.exceptions.ReadTimeoutError,
            botocore.exceptions.ConnectTimeoutError,
        ) as e:
            raise FreshnessError(FreshnessError.KIND_NETWORK, bucket, prefix, e) from e
        except Exception as e:
            # Catch-all for unexpected boto3/network errors; mark as unknown.
            raise FreshnessError(FreshnessError.KIND_UNKNOWN, bucket, prefix, e) from e

        if count == 0:
            # Sentinel report per TDD §1.2: epoch mtimes, parquet_count=0.
            # CLI integration layer (§3.4) detects parquet_count==0 and emits
            # the empty-prefix error.
            sentinel_age = int((now - _EPOCH_UTC).total_seconds())
            return cls(
                oldest_mtime=_EPOCH_UTC,
                newest_mtime=_EPOCH_UTC,
                max_age_seconds=sentinel_age,
                threshold_seconds=threshold_seconds,
                parquet_count=0,
                bucket=bucket,
                prefix=prefix,
            )

        # Type narrowing: count > 0 guarantees min/max are set.
        assert min_mtime is not None
        assert max_mtime is not None
        max_age = int((now - min_mtime).total_seconds())
        # Clamp negative values to 0 (clock skew protection).
        if max_age < 0:
            max_age = 0
        return cls(
            oldest_mtime=min_mtime,
            newest_mtime=max_mtime,
            max_age_seconds=max_age,
            threshold_seconds=threshold_seconds,
            parquet_count=count,
            bucket=bucket,
            prefix=prefix,
        )


# ---------------------------------------------------------------------------
# Duration spec parser
# ---------------------------------------------------------------------------


_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$")
_UNIT_MULTIPLIERS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration_spec(s: str) -> int:
    """Parse a duration spec string and return total seconds.

    Accepts: Ns, Nm, Nh, Nd where N is a positive integer.
    Examples: "90s" -> 90, "30m" -> 1800, "6h" -> 21600, "1d" -> 86400.

    Whitespace tolerance: leading/trailing whitespace stripped; whitespace
    between digits and unit tolerated ("6 h" -> 21600). No support for
    composite forms ("1h30m"). Case-sensitive: uppercase "6H" rejected.

    Args:
        s: Duration spec string.

    Returns:
        Total seconds as an int.

    Raises:
        ValueError: with actionable message on any parse failure (empty,
            missing unit, non-integer N, unknown unit, N == 0, mixed forms).
    """
    if not isinstance(s, str):
        raise ValueError(_invalid_duration_msg(s))
    match = _DURATION_RE.match(s)
    if match is None:
        raise ValueError(_invalid_duration_msg(s))
    n_str, unit = match.group(1), match.group(2)
    n = int(n_str)
    if n == 0:
        raise ValueError(_invalid_duration_msg(s))
    return n * _UNIT_MULTIPLIERS[unit]


def _invalid_duration_msg(s: object) -> str:
    return (
        f"invalid duration spec '{s}': "
        "expected formats Ns/Nm/Nh/Nd (e.g., '6h', '30m', '1d', '90s')"
    )


# ---------------------------------------------------------------------------
# Duration formatter
# ---------------------------------------------------------------------------


def format_duration(seconds: int) -> str:
    """Format seconds as a human-readable Nd Nh Nm string.

    Rules:
        - Seconds < 60: "Ns" (e.g., "45s", "0s").
        - 60 <= seconds < 3600: "Nm" (e.g., "1m", "59m").
        - 3600 <= seconds < 86400: "Nh Nm" (e.g., "1h 0m", "23h 59m").
        - seconds >= 86400: "Nd Nh Nm" (e.g., "1d 0h 0m", "32d 10h 56m").

    Examples:
        format_duration(45)       -> "45s"
        format_duration(90)       -> "1m"
        format_duration(3600)     -> "1h 0m"
        format_duration(2802960)  -> "32d 10h 56m"
    """
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    if seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    days = seconds // 86400
    rem = seconds % 86400
    hours = rem // 3600
    minutes = (rem % 3600) // 60
    return f"{days}d {hours}h {minutes}m"


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _fmt_dt_human(dt: datetime) -> str:
    """Format a datetime as 'YYYY-MM-DD HH:MM UTC' (minute granularity)."""
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _fmt_dt_iso(dt: datetime) -> str:
    """Format a datetime as ISO-8601 'YYYY-MM-DDTHH:MM:SSZ' (Z suffix, second granularity)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_human_lines(report: FreshnessReport) -> list[str]:
    """Returns the additive stdout lines per PRD AC-1.2.

    Format:
        ["parquet mtime: oldest=YYYY-MM-DD HH:MM UTC, newest=YYYY-MM-DD HH:MM UTC, max_age=Nh Nm"]

    All datetimes formatted at minute granularity.
    """
    return [
        (
            f"parquet mtime: "
            f"oldest={_fmt_dt_human(report.oldest_mtime)}, "
            f"newest={_fmt_dt_human(report.newest_mtime)}, "
            f"max_age={format_duration(report.max_age_seconds)}"
        )
    ]


def format_json_envelope(
    report: FreshnessReport,
    value: float | None,
    metric_name: str,
    currency: str,
    env: str,
    bucket_evidence: str,
) -> dict:
    """Build the AC-3.1 JSON envelope dict (TDD §4 schema v1).

    The dict is JSON-serializable as-is (no datetime objects). Calling
    json.dumps(envelope, sort_keys=True) produces a deterministic byte-for-byte
    serialization for a given S3 state.

    Args:
        report: FreshnessReport.
        value: Computed metric value, or None for null-value emission.
        metric_name: e.g., "active_mrr".
        currency: e.g., "USD".
        env: e.g., "production".
        bucket_evidence: Citation token for the bucket->env mapping per PRD G5.

    Returns:
        JSON-serializable dict matching the schema in TDD §4.2.
    """
    return {
        "schema_version": 1,
        "metric": metric_name,
        "value": value,
        "currency": currency,
        "freshness": {
            "oldest_mtime": _fmt_dt_iso(report.oldest_mtime),
            "newest_mtime": _fmt_dt_iso(report.newest_mtime),
            "max_age_seconds": report.max_age_seconds,
            "threshold_seconds": report.threshold_seconds,
            "stale": report.stale,
            "parquet_count": report.parquet_count,
        },
        "provenance": {
            "bucket": report.bucket,
            "prefix": report.prefix,
            "env": env,
            "evidence": bucket_evidence,
        },
    }


def format_warning(report: FreshnessReport) -> str:
    """Returns the AC-2.1 stderr WARNING line.

    Format:
        "WARNING: data older than {threshold_human} (max_age={observed_human})"
    """
    threshold_human = format_duration(report.threshold_seconds)
    observed_human = format_duration(report.max_age_seconds)
    return f"WARNING: data older than {threshold_human} (max_age={observed_human})"
