"""Monolith evidence source: the DIP port + its CloudWatch Insights impl.

The ``evidence -> stage`` derivation is pure domain; this module is the
infrastructure boundary that GATHERS the evidence. The port
:class:`MonolithEvidenceSource` is what the orchestrator depends on, so the
whole backfill is testable against a FAKE source with no AWS (the two-sided
teeth in ``test_backfill.py``). The concrete
:class:`CloudWatchInsightsEvidenceSource` runs ``aws logs start-query`` via the
boto3 ``logs`` client.

Two loud failure modes live here (both are teeth targets):

- :class:`DenominatorCapError` -- a query returned exactly ``query_row_cap``
  rows, so the true clinic denominator is unknown; the run ABORTS rather than
  emitting a partial PLAN that looks complete (DD-2 / G-DENOM / T-B5).
- :class:`MalformedLogRecordError` -- a log record's ``@message`` did not yield
  an inbox capture (garbage/truncated); it is rejected LOUDLY per-record and
  counted, never producing a phantom clinic (T-B2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from autom8y_log import get_logger

from autom8_asana.automation.forwarding_stage_backfill.config import (
    BackfillConfig,
    UncalibratedBackfillConfig,
)
from autom8_asana.domain.forwarding_stage_backfill import BookingSignal, ConfirmationSignal

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)


class DenominatorCapError(RuntimeError):
    """A CloudWatch Insights query returned exactly ``query_row_cap`` rows.

    A capped result means the true denominator is unknown; a PLAN built on it
    would silently under-count the book (a lying PLAN). The run ABORTS LOUD
    (DD-2 / G-DENOM / T-B5).
    """

    def __init__(self, *, query_kind: str, row_count: int, cap: int) -> None:
        self.query_kind = query_kind
        self.row_count = row_count
        self.cap = cap
        super().__init__(
            f"{query_kind} query returned {row_count} rows == the row cap {cap}; "
            f"the true denominator is unknown. ABORTING rather than emitting a "
            f"partial PLAN. Raise the cap and re-run, or narrow the window."
        )


class MalformedLogRecordError(ValueError):
    """A log record's ``@message`` did not yield a valid inbox capture.

    Raised per-record (garbage/truncated JSON, missing inbox). The gather loop
    catches it, counts it in ``malformed_records``, and continues WITHOUT
    producing a phantom clinic (T-B2). Never crashes the whole run.
    """

    def __init__(self, raw_message: str) -> None:
        self.raw_message = raw_message
        # Truncate the raw form in the message so a huge garbage record does not
        # flood the log line.
        preview = raw_message[:80] + ("..." if len(raw_message) > 80 else "")
        super().__init__(f"log record has no parseable inbox capture: {preview!r}")


@dataclass(frozen=True)
class BookingGatherResult:
    """Per-clinic booking-mail counts + the denominator-guard metadata.

    ``signals`` maps inbox_uuid -> :class:`BookingSignal`. ``cap_hit`` is True
    when the query returned exactly the row cap (denominator unknown ->
    orchestrator aborts). ``malformed_records`` counts records rejected by the
    per-record parser (T-B2). ``row_count`` is the raw row count for the PLAN
    denominator header.
    """

    signals: dict[str, BookingSignal]
    row_count: int
    cap_hit: bool
    malformed_records: int = 0
    booking_mail_total: int = 0


@dataclass(frozen=True)
class ConfirmationGatherResult:
    """Per-clinic forwarding-confirmation timestamps + guard metadata."""

    signals: dict[str, ConfirmationSignal]
    row_count: int
    cap_hit: bool
    malformed_records: int = 0


@runtime_checkable
class MonolithEvidenceSource(Protocol):
    """The DIP port the orchestrator depends on.

    Concrete implementations gather per-clinic evidence over a lookback window.
    A FAKE implementation (no AWS) satisfies this protocol in the unit tests; the
    :class:`CloudWatchInsightsEvidenceSource` satisfies it in production.
    """

    def booking_mail_counts(self, window_days: int) -> BookingGatherResult:
        """Per-clinic booking-mail counts over the last ``window_days``."""
        ...

    def forwarding_confirmations(self, window_days: int) -> ConfirmationGatherResult:
        """Per-clinic forwarding-confirmation timestamps over ``window_days``."""
        ...


def _window_bounds(window_days: int, *, now: datetime | None = None) -> tuple[int, int]:
    """Return ``(start_epoch, end_epoch)`` for the lookback window (UTC)."""
    end = now or datetime.now(UTC)
    start = end - timedelta(days=window_days)
    return int(start.timestamp()), int(end.timestamp())


class CloudWatchInsightsEvidenceSource:
    """Gather clinic evidence from ``/ecs/monolith-prod`` via CloudWatch Insights.

    Uses the boto3 ``logs`` client (``start_query`` + poll ``get_query_results``).
    The query strings + regexes come from :class:`BackfillConfig` (never
    hardcoded). ``filter-log-events`` times out on this group -> Insights only.

    The boto3 client is injected (defaults to a lazily-created one) so the class
    is exercisable with a stub client in a light integration test without hitting
    AWS; the two-sided PARSING teeth live in ``test_backfill.py`` against the
    FAKE source, and the row-cap/malformed guards are the shared helpers below.
    """

    def __init__(
        self,
        config: BackfillConfig,
        *,
        logs_client: Any | None = None,
        poll_interval_s: float = 1.0,
        poll_timeout_s: float = 120.0,
    ) -> None:
        if not config.is_calibrated:
            raise UncalibratedBackfillConfig(
                "BackfillConfig still bears '<...>' grammar placeholders; the "
                "build station must pin the live query predicates/regexes before "
                "a real gather (fail-closed calibration guard)."
            )
        self._config = config
        self._logs_client = logs_client
        self._poll_interval_s = poll_interval_s
        self._poll_timeout_s = poll_timeout_s

    @property
    def _client(self) -> Any:
        if self._logs_client is None:
            import boto3  # local import: the port is testable without boto3

            self._logs_client = boto3.client("logs", region_name=self._config.aws_region)
        return self._logs_client

    # -- gather legs -------------------------------------------------------

    def booking_mail_counts(self, window_days: int) -> BookingGatherResult:
        rows = self._run_query(self._config.booking_mail_query(), window_days)
        cap_hit = len(rows) >= self._config.query_row_cap
        signals: dict[str, BookingSignal] = {}
        malformed = 0
        total = 0
        for row in rows:
            fields = _row_fields(row)
            inbox = fields.get("inbox")
            if not inbox:
                malformed += 1
                logger.warning("backfill_booking_row_no_inbox", extra={"row": fields})
                continue
            count = int(fields.get("booking_count", 0) or 0)
            last_seen = _parse_ts(fields.get("last_seen"))
            signals[inbox] = BookingSignal(count=count, last_seen=last_seen)
            total += count
        return BookingGatherResult(
            signals=signals,
            row_count=len(rows),
            cap_hit=cap_hit,
            malformed_records=malformed,
            booking_mail_total=total,
        )

    def forwarding_confirmations(self, window_days: int) -> ConfirmationGatherResult:
        rows = self._run_query(self._config.forwarding_confirmation_query(), window_days)
        cap_hit = len(rows) >= self._config.query_row_cap
        signals: dict[str, ConfirmationSignal] = {}
        malformed = 0
        for row in rows:
            fields = _row_fields(row)
            inbox = fields.get("inbox")
            if not inbox:
                malformed += 1
                logger.warning("backfill_confirmation_row_no_inbox", extra={"row": fields})
                continue
            confirmed_at = _parse_ts(fields.get("confirmed_at"))
            signals[inbox] = ConfirmationSignal(confirmed_at=confirmed_at)
        return ConfirmationGatherResult(
            signals=signals,
            row_count=len(rows),
            cap_hit=cap_hit,
            malformed_records=malformed,
        )

    # -- CloudWatch plumbing ----------------------------------------------

    def _run_query(self, query_string: str, window_days: int) -> list[list[dict[str, str]]]:
        """Issue ``start_query`` and poll ``get_query_results`` until Complete."""
        import time

        start_epoch, end_epoch = _window_bounds(window_days)
        started = self._client.start_query(
            logGroupName=self._config.log_group,
            startTime=start_epoch,
            endTime=end_epoch,
            queryString=query_string,
        )
        query_id = started["queryId"]
        deadline = time.monotonic() + self._poll_timeout_s
        while True:
            result = self._client.get_query_results(queryId=query_id)
            status = result.get("status")
            if status == "Complete":
                rows: list[list[dict[str, str]]] = result.get("results", [])
                return rows
            if status in ("Failed", "Cancelled", "Timeout"):
                raise RuntimeError(
                    f"CloudWatch Insights query {query_id} ended with status={status}"
                )
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"CloudWatch Insights query {query_id} did not complete within "
                    f"{self._poll_timeout_s}s (last status={status})"
                )
            time.sleep(self._poll_interval_s)


def _row_fields(row: list[dict[str, str]]) -> dict[str, str]:
    """Flatten a CloudWatch Insights result row (``[{field, value}, ...]``)."""
    return {cell.get("field", ""): cell.get("value", "") for cell in row}


def _parse_ts(raw: str | None) -> datetime:
    """Parse a CloudWatch ``latest(@timestamp)`` value into an aware datetime.

    Insights returns ``@timestamp`` as ``YYYY-MM-DD HH:MM:SS.mmm`` (UTC). Falls
    back to epoch-millis if the value is numeric.
    """
    if not raw:
        return datetime.now(UTC)
    raw = raw.strip()
    if raw.isdigit():
        return datetime.fromtimestamp(int(raw) / 1000.0, tz=UTC)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return datetime.now(UTC)


def assert_not_capped(result: BookingGatherResult | ConfirmationGatherResult, *, kind: str) -> None:
    """Raise :class:`DenominatorCapError` if a gather result hit the row cap.

    The orchestrator calls this on BOTH gather legs before deriving anything, so
    a capped result never yields a partial PLAN (DD-2 / G-DENOM / T-B5).
    """
    if result.cap_hit:
        raise DenominatorCapError(
            query_kind=kind,
            row_count=result.row_count,
            cap=result.row_count,  # by construction row_count == cap when cap_hit
        )


def parse_inbox_or_raise(fields: Mapping[str, str]) -> str:
    """Return the inbox capture or raise :class:`MalformedLogRecordError`.

    The strict-form gate mirroring the satellite: a record whose ``@message`` did
    not yield an ``inbox`` capture is rejected LOUDLY and counted, never
    producing a phantom clinic (T-B2).
    """
    inbox = fields.get("inbox")
    if not inbox:
        raise MalformedLogRecordError(fields.get("@message", str(dict(fields))))
    return inbox


__all__ = [
    "BookingGatherResult",
    "CloudWatchInsightsEvidenceSource",
    "ConfirmationGatherResult",
    "DenominatorCapError",
    "MalformedLogRecordError",
    "MonolithEvidenceSource",
    "assert_not_capped",
    "parse_inbox_or_raise",
]
