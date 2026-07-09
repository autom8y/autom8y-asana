"""BackfillConfig: the monolith log grammar as DATA, never literal'd in code.

The ``evidence -> stage`` derivation is pure domain; the evidence GATHERING is
infrastructure. This config is the ONE place the monolith's live log grammar
enters (DD-6 / ADR-BF-006): the log group, the lookback window, the CloudWatch
Insights query templates, and the ``@message`` regexes are all injected. A
monolith log-format change is therefore a config edit, and the pure derivation
stays testable against a FAKE evidence source with no AWS.

The ``INBOX_CAPTURE_REGEX`` is the join's load-bearing precondition: it MUST
capture the mailbox local-part exactly as ``resolve_office`` does
(``to_address.split("@")[0]`` after a zero-width strip) so the derived key
equals the Company-ID custom-field value the CI-task resolution searches on --
otherwise every resolution 0-matches into UNRESOLVED (DEPENDENCY-MAP
UT-OI2-GUID; asserted by T-B6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Ruled defaults (the design station's rulings, overridable via CLI/env).
# ---------------------------------------------------------------------------

#: The placeholder-token shape: a bare ``<UPPER_SNAKE_CASE>`` grammar surface
#: the build station has not yet pinned (e.g. ``<INBOX_CAPTURE_REGEX>``).
#: Deliberately narrower than "contains '<'" so a VALID CloudWatch Insights
#: named-capture group (``(?<inbox>...)``, lowercase, embedded inside a larger
#: regex) is never false-positived as an unpinned placeholder.
_PLACEHOLDER_TOKEN_RE = re.compile(r"<[A-Z][A-Z0-9_]*>")

#: Lookback window (DD-2). 21d is the coverage/freshness knee: long enough to
#: capture biweekly/low-volume/monthly-ish clinics (7d misses them -> false
#: no_evidence), short enough that "booking mail observed" still means "flowing
#: NOW" (60d+ would stamp Flowing on 6-week-old stale evidence). CLI override:
#: --lookback-days.
DEFAULT_LOOKBACK_DAYS = 21

#: The nudge/stall threshold (hours). Mirrors the S1 nudge->Stalled semantics:
#: a verified-but-silent clinic crosses into Stalled once its forwarding
#: confirmation is older than this.
DEFAULT_NUDGE_THRESHOLD_HOURS = 48

#: The CloudWatch Insights ``stats ... by`` row cap (DD-2 denominator guard).
#: The 60-row triage result was a ``start-query`` result CAP, not the clinic
#: count. This cap is set far above the ~60-clinic reality with headroom; if a
#: query returns exactly this many rows, the true denominator is unknown and the
#: run ABORTS LOUD (``DenominatorCapError``) rather than emitting a partial PLAN
#: that looks complete.
DEFAULT_QUERY_ROW_CAP = 10000

#: The log group holding the legacy monolith's evidence trail (AWS acct
#: 696318035277). ``filter-log-events`` times out on this group -> Insights
#: (``start-query``) is the ONLY working method.
DEFAULT_LOG_GROUP = "/ecs/monolith-prod"

#: AWS region for the log group (operator/SRE-sourced).
DEFAULT_AWS_REGION = "us-east-1"


@dataclass(frozen=True)
class BackfillConfig:
    """Data-driven contract for the backfill's evidence gathering.

    Every field carries a ruled default; the query predicates/regexes are the
    calibration surface the build station tunes against a live ``start-query``
    sample and pins (documented with the sample ``@message`` they match). The
    write leg is NOT here -- it reuses the S1 ``api/config.py`` forwarding_stage_*
    settings verbatim (see the backfill orchestrator).
    """

    log_group: str = DEFAULT_LOG_GROUP
    aws_region: str = DEFAULT_AWS_REGION
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    nudge_threshold_hours: int = DEFAULT_NUDGE_THRESHOLD_HOURS
    query_row_cap: int = DEFAULT_QUERY_ROW_CAP

    #: The CloudWatch Insights query for per-clinic booking-mail counts (the
    #: Flowing denominator). ``{predicate}`` / ``{inbox_regex}`` / ``{row_cap}``
    #: are interpolated at gather time; ``booking_predicate`` and ``inbox_regex``
    #: are the calibrated live-grammar values.
    booking_mail_query_template: str = (
        "fields @timestamp, @message\n"
        "| filter {predicate}\n"
        "| parse @message /{inbox_regex}/\n"
        "| stats count() as booking_count, latest(@timestamp) as last_seen by inbox\n"
        "| sort booking_count desc\n"
        "| limit {row_cap}"
    )

    #: The CloudWatch Insights query for per-clinic forwarding-confirmation
    #: events (the Verified/Stalled discriminator).
    forwarding_confirmation_query_template: str = (
        "fields @timestamp, @message\n"
        "| filter {predicate}\n"
        "| parse @message /{inbox_regex}/\n"
        "| stats latest(@timestamp) as confirmed_at by inbox\n"
        "| limit {row_cap}"
    )

    #: The booking-mail predicate: a booking-pipeline-entered marker. Calibrated
    #: by the build station against a live sample (the placeholder is the ONE
    #: grammar surface; the reference triage counted 627 booking mails / 7d).
    booking_predicate: str = "<BOOKING_MAIL_PREDICATE>"

    #: The forwarding-confirmation predicate: the ``classify_forwarding_email``
    #: HIT marker. Calibrated by the build station (reference triage: 2 real
    #: clinic cards + 2 operator-test hits / 7d).
    forwarding_confirmation_predicate: str = "<FORWARDING_CONFIRMATION_PREDICATE>"

    #: The inbox capture regex. MUST capture the mailbox local-part == the
    #: chiropractor_guid == the Company-ID field value (T-B6 join precondition).
    #: Calibrated by the build station; the capture group is named ``inbox``.
    inbox_capture_regex: str = "<INBOX_CAPTURE_REGEX>"

    @property
    def is_calibrated(self) -> bool:
        """True iff every live-grammar surface has been pinned (no placeholders).

        A backfill run against an uncalibrated config would parse nothing and
        report ``no clinics`` -- a silent lie. The evidence source asserts this
        before issuing any query.

        Detects the ``<UPPER_SNAKE_CASE>`` placeholder-token SHAPE
        (:data:`_PLACEHOLDER_TOKEN_RE`), not a bare ``"<"`` substring check --
        a bare check would false-positive on a VALID CloudWatch Insights
        named-capture group such as ``(?<inbox>...)``, which is legitimate
        calibrated grammar, not an unpinned placeholder.
        """
        return not any(
            _PLACEHOLDER_TOKEN_RE.search(value)
            for value in (
                self.booking_predicate,
                self.forwarding_confirmation_predicate,
                self.inbox_capture_regex,
            )
        )

    def booking_mail_query(self) -> str:
        """Render the booking-mail Insights query with calibrated grammar."""
        return self.booking_mail_query_template.format(
            predicate=self.booking_predicate,
            inbox_regex=self.inbox_capture_regex,
            row_cap=self.query_row_cap,
        )

    def forwarding_confirmation_query(self) -> str:
        """Render the forwarding-confirmation Insights query."""
        return self.forwarding_confirmation_query_template.format(
            predicate=self.forwarding_confirmation_predicate,
            inbox_regex=self.inbox_capture_regex,
            row_cap=self.query_row_cap,
        )


class UncalibratedBackfillConfig(RuntimeError):
    """Raised when a backfill runs against a config still bearing ``<...>``
    grammar placeholders -- the build station has not pinned the live query
    predicates/regexes. Fail-closed: never build a PLAN on a placeholder query
    (it would parse nothing and report a false empty book)."""


__all__ = [
    "DEFAULT_AWS_REGION",
    "DEFAULT_LOG_GROUP",
    "DEFAULT_LOOKBACK_DAYS",
    "DEFAULT_NUDGE_THRESHOLD_HOURS",
    "DEFAULT_QUERY_ROW_CAP",
    "BackfillConfig",
    "UncalibratedBackfillConfig",
]
