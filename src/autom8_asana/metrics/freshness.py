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
class VerificationAge:
    """Per ADR-006 verification-recency signal scoped to active-classified sections.

    Distinct from the mutation-recency signal (``max_age_seconds`` /
    ``oldest_mtime`` on ``FreshnessReport``). Verification-recency tracks
    when the cached content was last confirmed against Asana (any probe
    verdict != PROBE_FAILED), independent of byte changes.

    Carries ``in_scope_count`` so the CLI can include the denominator in
    the human-readable line. ``oldest_verified_at`` is the floor used to
    derive ``max_age_seconds``; ``threshold_seconds`` is the cadence-tied
    SLA-class threshold. ``backfill_used`` is True iff any in-scope
    section had ``last_verified_at is None`` and the reader fell back to
    that section's ``written_at`` (legacy / never-probed; backfills on
    next probe per ADR-006 §Decision-6).

    Constructors:
      - ``from_manifest_join``: production path; joins active-section
        classifier names against ``SectionInfo.name``.
      - ``unavailable``: degraded sentinel when classifier-missing,
        manifest-missing, or join-empty (per QA-gate-2 condition 1's
        degrade rules).
    """

    oldest_verified_at: datetime | None
    max_age_seconds: int
    threshold_seconds: int
    in_scope_count: int
    backfill_used: bool
    available: bool

    @classmethod
    def unavailable(cls, threshold_seconds: int) -> VerificationAge:
        """Sentinel when verification_age cannot be computed."""
        return cls(
            oldest_verified_at=None,
            max_age_seconds=0,
            threshold_seconds=threshold_seconds,
            in_scope_count=0,
            backfill_used=False,
            available=False,
        )

    @property
    def stale(self) -> bool:
        """True iff verification_age exceeds the threshold AND signal is available."""
        return self.available and self.max_age_seconds > self.threshold_seconds


@dataclass(frozen=True)
class FreshnessReport:
    """Immutable freshness signal derived from S3 parquet listing.

    All datetimes are timezone-aware UTC. `stale` is a derived predicate
    (max_age_seconds > threshold_seconds), exposed as an attribute so consumers
    do not re-derive the comparison.

    When `parquet_count == 0`, oldest_mtime and newest_mtime are sentinel epoch
    values (1970-01-01T00:00Z); CLI integration layer detects this case and
    emits an empty-prefix error per TDD §3.4.

    The `mtimes` tuple retains the per-key mtime list for distribution-aware
    statistics (e.g., SectionAgeP95Seconds). Empty tuple when parquet_count==0.
    Per HANDOFF §1 work-item-4 SectionAgeP95Seconds requirement (P4 §4 SLI-4).

    Per ADR-006, the historical ``max_age_seconds`` continues to encode
    **mutation-recency** (``now - min(parquet mtime)``); the alarmable
    **verification-recency** signal lives in the optional ``verification``
    attribute, populated by ``with_verification`` after a successful
    manifest read in the CLI. Pre-ADR-006 consumers see the v1 contract
    byte-for-byte.
    """

    oldest_mtime: datetime
    newest_mtime: datetime
    max_age_seconds: int
    threshold_seconds: int
    parquet_count: int
    bucket: str
    prefix: str
    mtimes: tuple[datetime, ...] = ()
    verification: VerificationAge | None = None

    def with_verification(self, verification: VerificationAge | None) -> FreshnessReport:
        """Return a new FreshnessReport with the supplied verification block.

        Immutable dataclass — instances are constructed once and never
        mutated; this helper produces a sibling carrying the
        post-manifest-read verification block (per ADR-006 §Decision-4 /
        TDD §2.3).
        """
        return FreshnessReport(
            oldest_mtime=self.oldest_mtime,
            newest_mtime=self.newest_mtime,
            max_age_seconds=self.max_age_seconds,
            threshold_seconds=self.threshold_seconds,
            parquet_count=self.parquet_count,
            bucket=self.bucket,
            prefix=self.prefix,
            mtimes=self.mtimes,
            verification=verification,
        )

    @property
    def stale(self) -> bool:
        """True iff max_age_seconds strictly exceeds threshold_seconds.

        Exclusive comparison — equality is fresh, not stale.
        """
        return self.max_age_seconds > self.threshold_seconds

    def section_age_p95_seconds(self, *, now: datetime | None = None) -> int:
        """Compute the P95 age across per-key mtimes.

        Returns the 95th percentile of `(now - mtime).total_seconds()` across
        the retained mtime list. Uses nearest-rank method (ceiling index) on
        the descending-by-age sorted list (oldest first).

        Returns 0 when `parquet_count == 0` (sentinel — caller checks this
        case before invoking).

        Args:
            now: Override for datetime.now(tz=UTC); injectable for deterministic
                tests. Must match the `now` used at FreshnessReport construction
                for self-consistency.

        Returns:
            P95 age in seconds (clamped to >= 0).
        """
        if self.parquet_count == 0 or not self.mtimes:
            return 0
        if now is None:
            now = datetime.now(tz=UTC)
        # Compute age per key; sort ascending (smallest age = freshest).
        ages = sorted(int((now - m).total_seconds()) for m in self.mtimes)
        # Nearest-rank P95: index = ceil(0.95 * N) - 1, clamped to [0, N-1].
        # For N=14: ceil(0.95 * 14) = ceil(13.3) = 14, index = 13 (the oldest).
        # For N=20: ceil(0.95 * 20) = 19, index = 18.
        n = len(ages)
        # Use math.ceil semantics inline to avoid an import for one call.
        idx = (95 * n + 99) // 100 - 1  # ceil(0.95*n) - 1
        if idx < 0:
            idx = 0
        if idx >= n:
            idx = n - 1
        age = ages[idx]
        return max(age, 0)

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
            # Accumulator for per-key mtimes — required for SectionAgeP95Seconds
            # per P4 §4 SLI-4 (HANDOFF §1 work-item-4). Retained as a list during
            # paginator iteration; frozen to a tuple for the immutable dataclass.
            mtimes_list: list[datetime] = []
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not key.endswith(".parquet"):
                        continue
                    mtime = obj.get("LastModified")
                    if mtime is None:
                        continue
                    count += 1
                    mtimes_list.append(mtime)
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
                mtimes=(),
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
            mtimes=tuple(mtimes_list),
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
) -> dict[str, Any]:
    """Build the JSON envelope dict (schema v2 per ADR-006 §Decision-4 / TDD §2.4).

    The dict is JSON-serializable as-is (no datetime objects). Calling
    json.dumps(envelope, sort_keys=True) produces a deterministic byte-for-byte
    serialization for a given S3 state.

    Schema v1 -> v2 (ADR-006 amend / ADR-001 §Consequences gated):
        - schema_version: 1 -> 2
        - additive: ``mutation_age`` (alias for the existing ``freshness``
          block; the original block name is RETAINED byte-for-byte so v1
          consumers keep working).
        - additive: ``verification_age`` block carrying the
          verification-recency signal. Always present; carries
          ``available: false`` when the manifest join did not resolve.

    Existing v1 fields are unchanged (additive only); regex- /
    path-anchored consumers of v1 fields keep working.

    Args:
        report: FreshnessReport (may carry verification block via
            ``with_verification``).
        value: Computed metric value, or None for null-value emission.
        metric_name: e.g., "active_mrr".
        currency: e.g., "USD".
        env: e.g., "production".
        bucket_evidence: Citation token for the bucket->env mapping per PRD G5.

    Returns:
        JSON-serializable dict matching the schema v2 shape.
    """
    # Existing v1 freshness block (mutation-axis). RETAINED verbatim.
    mutation_block = {
        "oldest_mtime": _fmt_dt_iso(report.oldest_mtime),
        "newest_mtime": _fmt_dt_iso(report.newest_mtime),
        "max_age_seconds": report.max_age_seconds,
        "threshold_seconds": report.threshold_seconds,
        "stale": report.stale,
        "parquet_count": report.parquet_count,
    }

    # v2: verification block (ADR-006 §Decision-4). Always present so
    # operators can detect the unavailable state explicitly rather than
    # via field absence.
    verification = report.verification
    if verification is not None and verification.available and verification.oldest_verified_at:
        verification_block: dict[str, Any] = {
            "available": True,
            "oldest_verified_at": _fmt_dt_iso(verification.oldest_verified_at),
            "max_age_seconds": verification.max_age_seconds,
            "threshold_seconds": verification.threshold_seconds,
            "stale": verification.stale,
            "in_scope_count": verification.in_scope_count,
            "backfill_used": verification.backfill_used,
        }
    else:
        verification_block = {
            "available": False,
            "oldest_verified_at": None,
            "max_age_seconds": 0,
            "threshold_seconds": (
                verification.threshold_seconds if verification is not None else 0
            ),
            "stale": False,
            "in_scope_count": 0,
            "backfill_used": False,
        }

    return {
        "schema_version": 2,
        "metric": metric_name,
        "value": value,
        "currency": currency,
        # v1 'freshness' block retained byte-for-byte for back-compat.
        "freshness": mutation_block,
        # v2 additive: explicit mutation_age + verification_age blocks.
        "mutation_age": mutation_block,
        "verification_age": verification_block,
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


# ---------------------------------------------------------------------------
# Verification-age sync bridge (ADR-006 §Decision-8 / TDD §2.3.1)
# ---------------------------------------------------------------------------


def read_manifest_sync(persistence: Any, project_gid: str) -> Any:
    """Synchronously read the section manifest for a project.

    Wraps the async ``persistence.get_manifest_async(project_gid)`` in
    ``asyncio.run``, guarded by a running-loop check so the caller fails
    LOUDLY rather than silently nesting (the ``RuntimeError`` the QA gate
    flagged at D2). The default metric-emission path at
    ``__main__.py::main()`` is synchronous (no running loop), so the
    ``asyncio.run`` branch is the production path; the explicit raise on
    the nested-loop branch is a safety net for any future caller that
    might invoke us from async context.

    Args:
        persistence: A ``SectionPersistence`` instance.
        project_gid: Asana project GID.

    Returns:
        The ``SectionManifest`` or ``None`` (forwarded from
        ``get_manifest_async``).

    Raises:
        RuntimeError: when invoked from within a running event loop --
            this is the loud-not-silent guard per QA-gate-2 condition 4.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop -- safe to drive our own.
        return asyncio.run(persistence.get_manifest_async(project_gid))
    # A loop IS running: asyncio.run would raise. Surface it rather than
    # nest. This path is not expected on the synchronous main() emission
    # path; if a future caller hits it they need to switch to an async
    # call site, not silently nest a second loop.
    raise RuntimeError(
        "read_manifest_sync called from within a running event loop; "
        "the metric emission path must remain synchronous (per ADR-006 "
        "§Decision-8 / TDD §2.3.1 nested-loop guard)"
    )


def compute_verification_age(
    *,
    manifest: Any,
    entity_type: str,
    threshold_seconds: int,
    now: datetime | None = None,
) -> VerificationAge:
    """Compute the verification-recency signal for ``entity_type`` against ``manifest``.

    Per ADR-006 §Decision-2/3/6 and TDD §2.3. Joins the classifier's
    active section *names* (lower-cased) against ``SectionInfo.name`` and
    computes ``now - min(last_verified_at)`` over the in-scope set.
    Sections with ``last_verified_at is None`` fall back to
    ``written_at`` (§Decision-6); the result still computes, and the
    next probe will backfill a real stamp.

    Returns ``VerificationAge.unavailable(...)`` when the join resolves
    empty (classifier-missing, manifest-missing, or no in-scope section
    has either ``last_verified_at`` or ``written_at``). The reader's
    caller degrades to the mutation-axis signal in that case.

    Args:
        manifest: ``SectionManifest`` (or ``None``).
        entity_type: Metric ``scope.entity_type`` (e.g. ``"offer"``,
            ``"unit"``).
        threshold_seconds: Cadence-tied threshold (the SLA-class active
            interval per ``sla_profile.py``).
        now: Override for ``datetime.now(tz=UTC)``; injectable for
            deterministic tests.

    Returns:
        A ``VerificationAge`` instance. ``available=False`` means
        ``verification_age`` could not be computed; the caller falls back
        to ``mutation_age``.
    """
    # Lazy import to keep the metrics.freshness module importable in
    # environments that do not load the dataframes substack at import
    # time.
    from autom8_asana.models.business.activity import CLASSIFIERS

    if now is None:
        now = datetime.now(tz=UTC)

    if manifest is None:
        return VerificationAge.unavailable(threshold_seconds)

    classifier = CLASSIFIERS.get(entity_type)
    if classifier is None:
        return VerificationAge.unavailable(threshold_seconds)

    active_names = classifier.active_sections()
    if not active_names:
        return VerificationAge.unavailable(threshold_seconds)

    # Build the in-scope set by joining classifier names (lower-case)
    # against manifest entries' SectionInfo.name (case-normalized).
    oldest: datetime | None = None
    in_scope = 0
    backfill_used = False
    for _gid, info in manifest.sections.items():
        # info.name may be None on pre-re-seed manifests. With ≥2 sections
        # this is also surfaced by the §2.6 contract violation in the
        # warm path; here we simply skip null-name entries (the join is
        # name-based; they cannot match).
        if not info.name:
            continue
        if info.name.lower() not in active_names:
            continue
        # In scope.
        candidate = info.last_verified_at
        if candidate is None:
            # §Decision-6 backfill: fall back to written_at; legacy /
            # never-probed sections produce a still-correct floor and
            # backfill to a real stamp on the next probe.
            candidate = info.written_at
            if candidate is not None:
                backfill_used = True
        if candidate is None:
            continue
        in_scope += 1
        if oldest is None or candidate < oldest:
            oldest = candidate

    if oldest is None or in_scope == 0:
        return VerificationAge.unavailable(threshold_seconds)

    age = int((now - oldest).total_seconds())
    if age < 0:
        age = 0  # clock skew protection (mirrors max_age clamp)
    return VerificationAge(
        oldest_verified_at=oldest,
        max_age_seconds=age,
        threshold_seconds=threshold_seconds,
        in_scope_count=in_scope,
        backfill_used=backfill_used,
        available=True,
    )


def format_verification_human_line(verification: VerificationAge) -> str | None:
    """Return the additive default-mode stdout line, or ``None`` when unavailable.

    Format (when available):
        ``"verification age: oldest=YYYY-MM-DD HH:MM UTC, max_age=Nh Nm (N in-scope sections[, backfill])"``

    Returns ``None`` when the verification signal is unavailable so the
    caller can choose to emit a degraded-state line, omit it, or pair it
    with the existing mutation_age line per ADR-006 §Decision-6
    degrade-to-mutation policy.
    """
    if not verification.available or verification.oldest_verified_at is None:
        return None
    parts = [
        f"verification age: oldest={_fmt_dt_human(verification.oldest_verified_at)}",
        f"max_age={format_duration(verification.max_age_seconds)}",
    ]
    suffix = f"({verification.in_scope_count} in-scope sections"
    if verification.backfill_used:
        suffix += ", backfill"
    suffix += ")"
    return ", ".join(parts) + " " + suffix
