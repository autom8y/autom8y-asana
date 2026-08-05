"""Lambda handler: R7 standing traffic-vs-offer divergence tripwire (DEFAULT-DARK).

GRANDEUR ANCHOR (the throughline this instrument serves):
    "Every active client's booked appointments route automatically into their
    integrated calendar plane -- one intent surface, one receipted write path, no
    silent enrollment states." An office that is TRADING (taking booking traffic)
    while it has NO active/activating offer on the Asana roster is, today, a SILENT
    state. This tripwire makes that state LOUD and two-sided. It SURFACES divergence;
    it NEVER edits Asana data (reconciliation is CARD-D, operator-team). Read-only.

Design of record: ``.ledge/specs/SPEC-ws-e-divergence-tripwire-2026-08-03.md`` (§1
predicate, §2 metrics/thresholds, §3 atomic split). This module is HALF-1 (the
emitter); HALF-2 is the CloudWatch alarm terraform in the ``autom8y`` repo.

------------------------------------------------------------------------------
★ CROSS-REPO EMIT->ALARM CONTRACT (byte-exact; the ONLY thing binding the pair)
------------------------------------------------------------------------------
The alarm half (``autom8y`` repo,
``terraform/services/asana/traffic_offer_divergence_alarm.tf``) watches the EXACT
namespace + metric names + ``environment`` dimension this module emits via
``put_metric_data``. A rename/typo on EITHER side yields a silently
INSUFFICIENT_DATA alarm watching a metric nobody emits -- green on both halves,
DEAD as a pair. The namespace + metric-name constants below ARE that contract; the
terraform test ``test_traffic_offer_divergence_alarm_terraform.py`` and this module's
``__all__`` pin them so a rename trips CI, not production. The chaos-engineer's
teeth leg proves the spanning emit->breach end-to-end against the DEPLOYED pair.

JOIN KEY = ``office_phone`` (NOT the guid).
    Live probe (spec §0/§5, frozen 2026-08-03): ``company_id`` (guid) is populated
    on 0 of the 117 active/activating offer rows -- the guid side of the offer
    frame's join authority is DARK on the active roster. ``office_phone`` is
    populated on the active roster (102 distinct phones) and on BOTH traffic
    sources, so it is the operative join key. The guid is a SECONDARY diagnostic
    only (absent-from-frame attribution), never the primary join.

THE R7 PREDICATE (spec §1):
    traffic(O, W)   := EBI guid_resolved events for O.office_phone in window W
                       UNION scheduling booking_success events for O.office_phone  >= 1
    active_offer(O) := EXISTS offer-frame row R : R.office_phone == O.office_phone
                       AND classify(R.section) in {active, activating}  (OFFER_CLASSIFIER)
                       AND R.is_completed == False                       (terminal override)
    DIVERGENT(O)    := traffic(O, W) AND NOT active_offer(O)

    Sub-classes (bounded, non-PII -- safe as a ``class`` metric dimension):
      * ``inframe_inactive``   -- O.office_phone is in the frame but only on
        inactive / sales-process / complete rows (roster-void; dominant class).
      * ``absent_from_frame``  -- O.office_phone is on NO offer-frame row (deeper
        onboarding / identity gap).

★ THE R1 DISCRIMINATING BOUNDARY (spec §1) -- the sharpest tooth:
    An office that is GATE-DECLINED (``scheduling_gate_rejected``,
    reason=``business_disabled``) WHILE it has an active offer is the R1
    intent-vs-gate class -- a DIFFERENT instrument. R7 keys ONLY on roster
    membership, NEVER on gate outcome: such an office has ``active_offer(O)=True``,
    so it is NOT divergent here. The traffic gather deliberately selects
    ``booking_success`` (a committed write) and NEVER ``scheduling_gate_rejected``.
    ``SCHEDULING_R1_GATE_EVENT_EXCLUDED`` names the excluded event so the unit teeth
    can prove R7 does not conflate with R1.

FRESHNESS-REFUSE (I-REFUSE-NEVER-FABRICATE, spec §2):
    The S3 offer-frame parquet etag drifts continuously (live re-warm -- observed
    245,844 B -> 245,779 B within one probe session, spec §5). On a stale /
    unreadable / schema-lagged / empty frame the evaluator emits
    ``EvaluationRefused=1`` and NO divergence verdict -- it NEVER fabricates a 0 or a
    divergence from a broken read. A fabricated 0 would read "all clear" while the
    instrument is blind; a fabricated divergence would false-page. Both are refused.

BASELINE-POISONING GUARD (spec §2 fast-burn):
    The committed hashed divergent phone-set (drives ``NewlyTradingWithoutActiveOffer
    Count``) is written ONLY on a NON-refused run. A refused run MUST NOT overwrite
    the baseline with an empty set -- else the next run reads every office as "newly
    divergent" and false-pages. This is a required unit tooth.

READ-ONLY / NO ``Business()`` (WRITE trap):
    The evaluator reads the warmed offer frame as a pure Polars pass over raw S3
    (``boto3.get_object`` + ``pl.read_parquet``) -- it NEVER instantiates
    ``Business()`` (which WRITES to Asana on init; probe scar). IAM is read-only:
    ``s3:GetObject`` (offer frame) + ``s3:GetObject``/``PutObject`` (baseline object
    only) + ``logs:StartQuery``/``GetQueryResults`` (two log groups) +
    ``cloudwatch:PutMetricData``. NO Asana write scope. NO DB write.

DEFAULT-DARK (mirrors ``scheduling_stratum_snapshot``):
    Inert until the operator flips ``TRAFFIC_OFFER_DIVERGENCE_ENABLED`` (DEFAULT-OFF).
    With the gate off the handler short-circuits to ``skipped`` BEFORE any S3 read or
    Logs query -- but STILL emits ``LastRunEpoch`` so the dead-man tracks invocation
    (an honest "alive but intentionally dark" heartbeat; the verdict metrics only
    flow once armed). The EventBridge rule + per-function Lambda CMD live in EXTERNAL
    deploy infra (releaser-seam), not authored in this repo.

Environment Variables:
    TRAFFIC_OFFER_DIVERGENCE_ENABLED: DEFAULT-OFF activation gate. UNSET => DARK.
    TRAFFIC_OFFER_DIVERGENCE_WINDOW_DAYS: trailing traffic window (default 7).
    TRAFFIC_OFFER_DIVERGENCE_FRAME_STALENESS_SECONDS: refuse ceiling on frame age
        (default 43200 = 12h = 2x the 6h warm cadence).
    TRAFFIC_OFFER_DIVERGENCE_EBI_LOG_GROUP: EBI intake log group
        (default /aws/lambda/autom8-email-booking-intake -- verified live).
    TRAFFIC_OFFER_DIVERGENCE_SCHEDULING_LOG_GROUP: scheduling monolith log group
        (releaser-seam override; the monolith is a separate service).
    TRAFFIC_OFFER_DIVERGENCE_BASELINE_BUCKET: baseline JSON bucket (default autom8-s3).
    ASANA_CACHE_S3_BUCKET: offer-frame bucket (house canonical, ADR-0002).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
from typing import TYPE_CHECKING, Any, NamedTuple

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric
from autom8_asana.models.business.activity import OFFER_CLASSIFIER
from autom8_asana.storage_namespace import DATAFRAMES_V2

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

logger = get_logger(__name__)

# ==============================================================================
# ★ CROSS-REPO EMIT->ALARM CONTRACT (byte-exact match with the terraform half)
# ==============================================================================
# COUNTERPART: autom8y repo,
#   terraform/services/asana/traffic_offer_divergence_alarm.tf
# A rename here WITHOUT the matching rename there = a green-on-both-halves,
# dead-as-a-pair INSUFFICIENT_DATA alarm. These constants are the seam.
METRIC_NAMESPACE = "Autom8y/AsanaOfferDivergence"

#: Primary slow-burn alarm target: count of DIVERGENT offices this run.
METRIC_TRADING_COUNT = "TradingWithoutActiveOfferCount"
#: Fast-burn alarm target: divergent offices NOT in the prior committed baseline.
METRIC_NEWLY_TRADING = "NewlyTradingWithoutActiveOfferCount"
#: Floor alarm target: active-offer roster denominator (guards mass-divergence).
METRIC_ROSTER_SIZE = "ActiveOfferRosterSize"
#: Refuse alarm target: =1 when the frame cannot be proven fresh/complete.
METRIC_EVALUATION_REFUSED = "EvaluationRefused"
#: Dead-man alarm target: emitted EVERY invocation (incl. DARK/refused).
METRIC_LAST_RUN_EPOCH = "LastRunEpoch"
#: Dashboard (no alarm): trailing-window bookings of divergent offices (blast radius).
METRIC_TRADING_BOOKINGS = "TradingWithoutActiveOfferBookings"
#: Dashboard (no alarm): divergent-office count split by the ``class`` dimension.
METRIC_TRADING_BY_CLASS = "TradingWithoutActiveOfferByClass"
#: Dashboard (no alarm): traffic denominator (distinct offices that took traffic).
METRIC_TRAFFIC_OFFICES = "TrafficOfficesEvaluated"

# The five alarm-bound metric names, pinned as a set so the terraform test / a
# rename cross-check can assert the emit<->alarm contract mechanically.
ALARM_BOUND_METRICS: frozenset[str] = frozenset(
    {
        METRIC_TRADING_COUNT,
        METRIC_NEWLY_TRADING,
        METRIC_ROSTER_SIZE,
        METRIC_EVALUATION_REFUSED,
        METRIC_LAST_RUN_EPOCH,
    }
)

# ==============================================================================
# Offer frame + join semantics
# ==============================================================================
#: The Offer project gid (OFFER_CLASSIFIER.project_gid); its warmed merged frame is
#: the active-office roster source.
OFFER_PROJECT_GID = "1143843662099250"
#: S3 key of the warmed merged offer frame under the DATAFRAMES_V2 plane prefix
#: (storage.py entity-segmented layout: {prefix}{gid}/{entity}/dataframe.parquet). The
#: prefix is DERIVED from the storage_namespace registry (DATAFRAMES_V2.prefix), never
#: hand-pinned, so the t3 namespace-contract holds; the resolved key is byte-identical.
OFFER_FRAME_KEY = f"{DATAFRAMES_V2.prefix}{OFFER_PROJECT_GID}/offer/dataframe.parquet"

#: The columns a VALID offer frame MUST carry for the R7 predicate. Their absence is
#: SCHEMA-LAG (a stale-while-revalidate cache served a pre-projection frame) -> REFUSE
#: honestly, never fabricate a roster from a frame that cannot carry it.
REQUIRED_OFFER_COLUMNS: tuple[str, ...] = ("office_phone", "section", "is_completed")

#: Bounded, non-PII divergence sub-classes (safe as a ``class`` metric dimension).
CLASS_INFRAME_INACTIVE = "inframe_inactive"
CLASS_ABSENT_FROM_FRAME = "absent_from_frame"

# ==============================================================================
# Traffic gather -- event vocabulary (load-bearing; anti-blind-instrument)
# ==============================================================================
# EBI resolve events (verified live against
# autom8y@84222e67:services/email-booking-intake/src/email_booking_intake/pipeline/
# stages/resolve_office.py:202 (guid_resolved_via_data_service) + :210
# (guid_resolved_via_override) -- BOTH log a top-level ``office_phone``).
EBI_RESOLVE_EVENTS: tuple[str, ...] = (
    "guid_resolved_via_data_service",
    "guid_resolved_via_override",
)
# Scheduling committed-booking event (monolith; a separate service). Logs
# ``extra.office_phone``. Grounded live by spec §5 QID
# e200aeee-5b3a-4775-8ebe-7f6af769e268 (30d census: booking_success=444).
SCHEDULING_BOOKING_EVENT = "booking_success"

# ★ R1 BOUNDARY: the gate-declined event R7 must NEVER select on. Naming it here
# (rather than merely omitting it) lets the unit teeth prove R7 does not conflate
# with the R1 intent-vs-gate instrument. Grounded live by spec §5 census
# (scheduling_gate_rejected=679/30d, reason=business_disabled).
SCHEDULING_R1_GATE_EVENT_EXCLUDED = "scheduling_gate_rejected"

# ==============================================================================
# Config knobs (env-overridable; releaser-seam sets these at deploy time)
# ==============================================================================
DIVERGENCE_ENABLED_ENV_VAR = "TRAFFIC_OFFER_DIVERGENCE_ENABLED"

DEFAULT_TRAFFIC_WINDOW_DAYS = 7
TRAFFIC_WINDOW_DAYS_ENV_VAR = "TRAFFIC_OFFER_DIVERGENCE_WINDOW_DAYS"

#: Refuse a frame older than this many seconds (2x the 6h warm cadence). A stale
#: frame means the warmer died -- serving it would emit a stale verdict.
DEFAULT_FRAME_STALENESS_CEILING_SECONDS = 43200
FRAME_STALENESS_CEILING_ENV_VAR = "TRAFFIC_OFFER_DIVERGENCE_FRAME_STALENESS_SECONDS"

EBI_LOG_GROUP_ENV_VAR = "TRAFFIC_OFFER_DIVERGENCE_EBI_LOG_GROUP"
DEFAULT_EBI_LOG_GROUP = "/aws/lambda/autom8-email-booking-intake"
SCHEDULING_LOG_GROUP_ENV_VAR = "TRAFFIC_OFFER_DIVERGENCE_SCHEDULING_LOG_GROUP"
#: Documented default; the monolith is a separate service so the exact group is a
#: releaser-seam override. Absent an override the scheduling leg is skipped (EBI-only
#: traffic), never fabricated.
DEFAULT_SCHEDULING_LOG_GROUP = "/ecs/autom8-prod"

BASELINE_BUCKET_ENV_VAR = "TRAFFIC_OFFER_DIVERGENCE_BASELINE_BUCKET"
DEFAULT_BASELINE_BUCKET = "autom8-s3"
BASELINE_KEY = "soak-sentinel/r7-divergence-baseline.json"

OFFER_BUCKET_ENV_VAR = "ASANA_CACHE_S3_BUCKET"


class EvaluationRefusedError(Exception):
    """The offer frame could not be proven fresh/complete -- REFUSE, emit no verdict.

    Raised by the freshness / readability gates. The handler converts it to an
    ``EvaluationRefused=1`` emission and returns WITHOUT a divergence verdict (the
    fail-safe: never fabricate a 0 or a divergence from a broken read). The baseline
    is NOT committed on a refused run (poisoning guard).
    """


class TrafficTally(NamedTuple):
    """The union of traffic across EBI + scheduling for window W, join-keyed by phone.

    ``phones`` is the distinct set of offices that took traffic; ``bookings_by_phone``
    carries per-office event counts so blast-radius (``TradingWithoutActiveOffer
    Bookings``) can be summed over the divergent subset.
    """

    phones: frozenset[str]
    bookings_by_phone: dict[str, int]


class DivergenceVerdict(NamedTuple):
    """Outcome of the R7 predicate over one (frame, traffic) pair."""

    divergent_phones: frozenset[str]
    classes: dict[str, str]  # phone -> CLASS_*
    class_counts: dict[str, int]  # CLASS_* -> count (both classes always present)
    divergent_bookings: int
    roster_size: int  # distinct active/activating office_phone (floor denominator)
    traffic_offices: int  # distinct traffic phones (traffic denominator)
    matched_offices: int  # traffic phones WITH an active offer (the healthy state)


class RunResult(NamedTuple):
    """What the orchestrator returns (handler + tests read this)."""

    status: str  # skipped | refused | evaluated | error
    reason: str | None
    divergent_count: int
    newly_count: int
    roster_size: int


# ==============================================================================
# PURE predicate core (no I/O -- the two-sided unit-teeth surface)
# ==============================================================================


def _norm_phone(value: Any) -> str:
    """Normalize a phone to its comparison form (strip outer whitespace only).

    Deliberately conservative: both traffic sources and the offer frame derive
    ``office_phone`` from the SAME ``Business.office_phone`` cascade, so they are
    byte-identical modulo whitespace. Over-normalizing (stripping punctuation) risks
    false joins across distinct offices.
    """
    return str(value).strip() if value is not None else ""


def _distinct_phones(df: pl.DataFrame, *, predicate: pl.Expr | None = None) -> frozenset[str]:
    """Distinct non-blank normalized ``office_phone`` values, optionally filtered."""
    import polars as pl

    frame = df.filter(predicate) if predicate is not None else df
    if "office_phone" not in frame.columns:
        return frozenset()
    values = (
        frame.select(pl.col("office_phone").cast(pl.Utf8).str.strip_chars().alias("_p"))
        .filter(pl.col("_p").is_not_null() & (pl.col("_p") != ""))
        .get_column("_p")
        .to_list()
    )
    return frozenset(values)


def _active_offer_predicate() -> pl.Expr:
    """Polars predicate: a row is an ACTIVE offer (roster member).

    ``classify(section) in {active, activating}`` (OFFER_CLASSIFIER.billable_sections,
    case-insensitive) AND ``is_completed`` is not True (SD-6 terminal override; a null
    ``is_completed`` is treated as NOT completed, i.e. eligible).
    """
    import polars as pl

    billable = list(OFFER_CLASSIFIER.billable_sections())  # lowercase section names
    return (
        pl.col("section").is_not_null()
        & pl.col("section").cast(pl.Utf8).str.to_lowercase().str.strip_chars().is_in(billable)
        & (~pl.col("is_completed").cast(pl.Boolean).fill_null(False))
    )


def active_roster_phones(offer_df: pl.DataFrame) -> frozenset[str]:
    """Distinct ``office_phone`` on active/activating, non-completed offer rows."""
    return _distinct_phones(offer_df, predicate=_active_offer_predicate())


def inframe_phones(offer_df: pl.DataFrame) -> frozenset[str]:
    """Distinct ``office_phone`` present on ANY offer-frame row (for class attribution)."""
    return _distinct_phones(offer_df)


def classify_divergent(phone: str, present_in_frame: frozenset[str]) -> str:
    """Attribute a divergent office to its bounded sub-class (non-PII)."""
    return CLASS_INFRAME_INACTIVE if phone in present_in_frame else CLASS_ABSENT_FROM_FRAME


def assert_frame_readable(offer_df: pl.DataFrame) -> None:
    """READABILITY gate: REFUSE a frame missing required columns or carrying 0 rows.

    A missing required column is SCHEMA-LAG (pre-projection frame). Zero rows is
    indistinguishable from a broken read (a genuinely-empty offer board is a fleet
    catastrophe, not a steady state) -- REFUSED fail-safe rather than yielding a
    fabricated all-clear 0. A small-but-nonzero roster is NOT refused here: it emits
    ``ActiveOfferRosterSize`` and the FLOOR alarm independently guards a collapse.
    """
    missing = [c for c in REQUIRED_OFFER_COLUMNS if c not in offer_df.columns]
    if missing:
        raise EvaluationRefusedError(
            f"offer frame lacks required columns {missing} (schema-lag / pre-projection "
            "frame); refusing to fabricate a roster from a frame that cannot carry it"
        )
    if offer_df.height == 0:
        raise EvaluationRefusedError(
            "offer frame is empty (0 rows) -- indistinguishable from a broken read; "
            "refusing to fabricate an all-clear verdict"
        )


def assert_frame_fresh(
    frame_last_modified_epoch: float | None,
    *,
    now_epoch: float,
    ceiling_seconds: float,
) -> None:
    """FRESHNESS gate: REFUSE a frame whose S3 age exceeds the ceiling (warmer died).

    ``None`` (no LastModified resolvable) is REFUSED -- an unprovable freshness is not
    a fresh frame. A future-dated frame (clock skew) is admitted (age clamped >= 0).
    """
    if frame_last_modified_epoch is None:
        raise EvaluationRefusedError("offer frame freshness is unprovable (no LastModified)")
    age = max(0.0, now_epoch - frame_last_modified_epoch)
    if age > ceiling_seconds:
        raise EvaluationRefusedError(
            f"offer frame is stale: age {age:.0f}s > ceiling {ceiling_seconds:.0f}s "
            "(the warmer likely died); refusing to emit a stale verdict"
        )


def resolve_divergence(offer_df: pl.DataFrame, traffic: TrafficTally) -> DivergenceVerdict:
    """PURE R7 predicate: DIVERGENT(O) := traffic(O) AND NOT active_offer(O).

    Assumes a VALID frame (call :func:`assert_frame_readable` first). Returns the
    divergent set with per-office class attribution + the denominators. R1
    (gate-declined WITH an active offer) is silent by construction: such an office has
    ``active_offer(O)=True`` so it never enters ``divergent``, regardless of gate
    outcome -- and the traffic tally never carries ``scheduling_gate_rejected`` events.
    """
    roster = active_roster_phones(offer_df)
    present = inframe_phones(offer_df)
    traffic_phones = frozenset(_norm_phone(p) for p in traffic.phones if _norm_phone(p))

    divergent = frozenset(p for p in traffic_phones if p not in roster)
    matched = traffic_phones & roster

    classes: dict[str, str] = {p: classify_divergent(p, present) for p in divergent}
    class_counts = {
        CLASS_INFRAME_INACTIVE: sum(1 for c in classes.values() if c == CLASS_INFRAME_INACTIVE),
        CLASS_ABSENT_FROM_FRAME: sum(1 for c in classes.values() if c == CLASS_ABSENT_FROM_FRAME),
    }
    divergent_bookings = sum(int(traffic.bookings_by_phone.get(p, 0)) for p in divergent)

    return DivergenceVerdict(
        divergent_phones=divergent,
        classes=classes,
        class_counts=class_counts,
        divergent_bookings=divergent_bookings,
        roster_size=len(roster),
        traffic_offices=len(traffic_phones),
        matched_offices=len(matched),
    )


# ==============================================================================
# Baseline (fast-burn delta) -- hashed phone-set, poisoning-guarded
# ==============================================================================


def phone_hash(phone: str) -> str:
    """SHA-256 hex of a normalized phone (the baseline stores hashes, never plaintext)."""
    return hashlib.sha256(_norm_phone(phone).encode("utf-8")).hexdigest()


def compute_newly_divergent(
    divergent_phones: frozenset[str], prior_hashes: set[str]
) -> tuple[int, set[str]]:
    """Return ``(newly_count, new_baseline_hashes)`` for the fast-burn delta.

    ``newly_count`` = divergent offices whose hash is NOT in the prior committed
    baseline (a previously-matched office that just went divergent -- the sharpest
    "silent enrollment state just happened" transition). ``new_baseline_hashes`` is
    the CURRENT divergent set hashed, to be committed ONLY on a non-refused run.
    """
    current_hashes = {phone_hash(p) for p in divergent_phones}
    newly = current_hashes - set(prior_hashes)
    return len(newly), current_hashes


# ==============================================================================
# Metric emission
# ==============================================================================


def _emit(metric: str, value: float, *, dimensions: dict[str, str] | None = None) -> None:
    """Emit into the R7 namespace (overrides the house default namespace)."""
    emit_metric(metric, value, dimensions=dimensions, namespace=METRIC_NAMESPACE)


def emit_heartbeat(now_epoch: float) -> None:
    """Dead-man heartbeat: emitted on EVERY invocation (skipped / refused / evaluated).

    The evaluator's own absence must be detectable on a metric that EXISTS every run
    (contrast an orphaned dead-man watching a namespace nobody emits into).
    """
    _emit(METRIC_LAST_RUN_EPOCH, now_epoch)


def emit_refused(reason: str) -> None:
    """Refuse emission: EvaluationRefused=1 and NO verdict metrics (never a fabricated 0)."""
    logger.warning("traffic_offer_divergence_refused", extra={"reason": reason})
    _emit(METRIC_EVALUATION_REFUSED, 1)


def emit_evaluated(verdict: DivergenceVerdict, newly_count: int) -> None:
    """Verdict emission: the full R7 metric set for a non-refused run.

    ``EvaluationRefused=0`` publishes a real 0 so the refuse alarm sits in OK (not
    INSUFFICIENT_DATA). The per-office triage lives in a structured LOG line (queried
    via Logs Insights), NEVER a CloudWatch dimension (I-NO-PII-METRIC: never a phone
    or guid as a dimension).
    """
    _emit(METRIC_EVALUATION_REFUSED, 0)
    _emit(METRIC_TRADING_COUNT, len(verdict.divergent_phones))
    _emit(METRIC_NEWLY_TRADING, newly_count)
    _emit(METRIC_ROSTER_SIZE, verdict.roster_size)
    _emit(METRIC_TRAFFIC_OFFICES, verdict.traffic_offices)
    _emit(METRIC_TRADING_BOOKINGS, verdict.divergent_bookings)
    for klass, count in verdict.class_counts.items():
        _emit(METRIC_TRADING_BY_CLASS, count, dimensions={"class": klass})
    # Structured per-run triage line (bounded counts + class split; NO phone/guid).
    logger.info(
        "traffic_offer_divergence_evaluated",
        extra={
            "divergent_count": len(verdict.divergent_phones),
            "newly_count": newly_count,
            "roster_size": verdict.roster_size,
            "traffic_offices": verdict.traffic_offices,
            "matched_offices": verdict.matched_offices,
            "divergent_bookings": verdict.divergent_bookings,
            "class_inframe_inactive": verdict.class_counts[CLASS_INFRAME_INACTIVE],
            "class_absent_from_frame": verdict.class_counts[CLASS_ABSENT_FROM_FRAME],
        },
    )


# ==============================================================================
# Orchestrator (injectable I/O -- integration-testable without live AWS)
# ==============================================================================


def run_divergence_evaluation(
    *,
    gate: Callable[[], bool],
    load_frame: Callable[[], tuple[pl.DataFrame, float | None]],
    gather_traffic: Callable[[], TrafficTally],
    read_baseline: Callable[[], set[str]],
    commit_baseline: Callable[[set[str]], None],
    now_epoch: float | None = None,
    ceiling_seconds: float,
) -> RunResult:
    """One evaluation run under the DARK gate + freshness-refuse + poisoning guard.

    I/O is injected so the gate / refuse / baseline decisions are unit-testable with
    ZERO live AWS. ``load_frame`` returns ``(offer_df, frame_last_modified_epoch)``;
    it (or the freshness/readability gates) may raise :class:`EvaluationRefusedError`.
    On refuse: emit ``EvaluationRefused=1``, NO verdict, and DO NOT commit the baseline
    (poisoning guard). ``LastRunEpoch`` is emitted on every path (incl. skipped).
    """
    now = time.time() if now_epoch is None else now_epoch
    emit_heartbeat(now)

    if not gate():
        logger.info("traffic_offer_divergence_skipped", extra={"reason": "gate_off"})
        return RunResult(
            status="skipped", reason="gate_off", divergent_count=0, newly_count=0, roster_size=0
        )

    try:
        offer_df, frame_mtime = load_frame()
        assert_frame_fresh(frame_mtime, now_epoch=now, ceiling_seconds=ceiling_seconds)
        assert_frame_readable(offer_df)
        traffic = gather_traffic()
        verdict = resolve_divergence(offer_df, traffic)
        newly_count, new_hashes = compute_newly_divergent(verdict.divergent_phones, read_baseline())
    except EvaluationRefusedError as exc:
        emit_refused(str(exc))
        # POISONING GUARD: baseline NOT committed on a refused run.
        return RunResult(
            status="refused", reason=str(exc), divergent_count=0, newly_count=0, roster_size=0
        )

    emit_evaluated(verdict, newly_count)
    # Commit the fresh baseline ONLY now (non-refused run) so the next run's delta is honest.
    commit_baseline(new_hashes)
    return RunResult(
        status="evaluated",
        reason=None,
        divergent_count=len(verdict.divergent_phones),
        newly_count=newly_count,
        roster_size=verdict.roster_size,
    )


# ==============================================================================
# Live wiring (env config + raw S3 + Logs Insights; NO Business())
# ==============================================================================


def _is_enabled() -> bool:
    """DEFAULT-OFF activation gate (UNSET => DARK)."""
    return os.environ.get(DIVERGENCE_ENABLED_ENV_VAR, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _int_env(var: str, default: int) -> int:
    raw = os.environ.get(var)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _load_offer_frame() -> tuple[pl.DataFrame, float | None]:
    """Raw pure-Polars read of the warmed merged offer frame from S3 (NO Business()).

    Returns ``(offer_df, last_modified_epoch)``. A missing object / unreadable body is
    surfaced as :class:`EvaluationRefusedError` (freshness unprovable) rather than a
    crash -- an absent frame is a refuse, not a 500.
    """
    import boto3
    import polars as pl

    bucket = os.environ.get(OFFER_BUCKET_ENV_VAR)
    if not bucket:
        raise EvaluationRefusedError(f"offer-frame bucket unset ({OFFER_BUCKET_ENV_VAR})")
    client = boto3.client("s3")
    try:
        resp = client.get_object(Bucket=bucket, Key=OFFER_FRAME_KEY)
        body = resp["Body"].read()
        last_modified = resp.get("LastModified")
    except Exception as exc:
        raise EvaluationRefusedError(
            f"offer frame unreadable at s3://{bucket}/{OFFER_FRAME_KEY}: {exc}"
        ) from exc
    last_modified_epoch = last_modified.timestamp() if last_modified is not None else None
    return pl.read_parquet(io.BytesIO(body)), last_modified_epoch


def build_ebi_query(window_days: int) -> str:
    """Logs Insights query: distinct EBI-resolved offices + per-office booking counts.

    Selects ONLY the EBI resolve events (top-level ``office_phone``). NEVER selects
    ``scheduling_gate_rejected`` (that is R1, not R7)."""
    events = " or ".join(f'event = "{e}"' for e in EBI_RESOLVE_EVENTS)
    return (
        "fields office_phone\n"
        f"| filter {events}\n"
        "| filter ispresent(office_phone)\n"
        "| stats count() as bookings by office_phone"
    )


def build_scheduling_query(window_days: int) -> str:
    """Logs Insights query: distinct scheduling-committed offices + booking counts.

    Selects ONLY ``booking_success`` (a committed write on ``extra.office_phone``).
    NEVER selects ``scheduling_gate_rejected`` -- keying on a gate outcome would
    conflate R7 with the R1 intent-vs-gate instrument (the sharpest tooth, spec §1)."""
    return (
        "fields extra.office_phone as office_phone\n"
        f'| filter event = "{SCHEDULING_BOOKING_EVENT}"\n'
        "| filter ispresent(office_phone)\n"
        "| stats count() as bookings by office_phone"
    )


def _run_logs_insights(
    client: Any, log_group: str, query: str, *, start: int, end: int
) -> dict[str, int]:
    """Run one Logs Insights query, return ``{office_phone: bookings}``.

    A query failure (missing log group / throttle) raises so the caller can decide
    refuse-vs-partial; the caller treats a missing scheduling group as EBI-only, not
    fabricated traffic."""
    started = client.start_query(
        logGroupName=log_group, startTime=start, endTime=end, queryString=query
    )
    query_id = started["queryId"]
    while True:
        res = client.get_query_results(queryId=query_id)
        status = res.get("status")
        if status in {"Complete", "Failed", "Cancelled", "Timeout"}:
            break
        time.sleep(1)
    if status != "Complete":
        raise RuntimeError(f"Logs Insights query {status} on {log_group}")
    tally: dict[str, int] = {}
    for row in res.get("results", []):
        fields = {f["field"]: f["value"] for f in row}
        phone = _norm_phone(fields.get("office_phone"))
        if not phone:
            continue
        try:
            tally[phone] = tally.get(phone, 0) + int(fields.get("bookings", "0"))
        except (TypeError, ValueError):
            tally[phone] = tally.get(phone, 0)
    return tally


def _gather_traffic(window_days: int) -> TrafficTally:
    """Union EBI + scheduling traffic over window W (join-keyed by office_phone).

    The scheduling leg is best-effort: if its log group is unset/unreachable the union
    degrades to EBI-only (still a real traffic read), NEVER fabricated. A failure of
    the EBI leg propagates (EBI is the primary traffic source)."""
    import boto3

    client = boto3.client("logs")
    end = int(time.time())
    start = end - window_days * 86400

    ebi_group = os.environ.get(EBI_LOG_GROUP_ENV_VAR, DEFAULT_EBI_LOG_GROUP)
    tally = _run_logs_insights(
        client, ebi_group, build_ebi_query(window_days), start=start, end=end
    )

    sched_group = os.environ.get(SCHEDULING_LOG_GROUP_ENV_VAR, DEFAULT_SCHEDULING_LOG_GROUP)
    if sched_group:
        try:
            sched = _run_logs_insights(
                client, sched_group, build_scheduling_query(window_days), start=start, end=end
            )
            for phone, count in sched.items():
                tally[phone] = tally.get(phone, 0) + count
        except Exception as exc:  # noqa: BLE001 -- scheduling leg is best-effort; EBI-only degrade
            logger.warning(
                "traffic_offer_divergence_scheduling_leg_failed",
                extra={"error": str(exc), "log_group": sched_group},
            )
    return TrafficTally(phones=frozenset(tally.keys()), bookings_by_phone=tally)


def _read_baseline() -> set[str]:
    """Read the prior committed hashed divergent phone-set from S3 (empty on miss)."""
    import boto3

    bucket = os.environ.get(BASELINE_BUCKET_ENV_VAR, DEFAULT_BASELINE_BUCKET)
    client = boto3.client("s3")
    try:
        resp = client.get_object(Bucket=bucket, Key=BASELINE_KEY)
        data = json.loads(resp["Body"].read())
    except Exception as exc:  # noqa: BLE001 -- first run / missing baseline => empty prior
        logger.info("traffic_offer_divergence_baseline_absent", extra={"error": str(exc)})
        return set()
    hashes = data.get("divergent_hashes", []) if isinstance(data, dict) else []
    return {str(h) for h in hashes}


def _commit_baseline(new_hashes: set[str]) -> None:
    """Persist the current hashed divergent set (called ONLY on a non-refused run)."""
    import boto3

    bucket = os.environ.get(BASELINE_BUCKET_ENV_VAR, DEFAULT_BASELINE_BUCKET)
    client = boto3.client("s3")
    payload = json.dumps(
        {"divergent_hashes": sorted(new_hashes), "committed_epoch": int(time.time())}
    ).encode("utf-8")
    try:
        client.put_object(Bucket=bucket, Key=BASELINE_KEY, Body=payload)
    except Exception as exc:  # noqa: BLE001 -- a baseline write failure must not fail the run
        logger.warning("traffic_offer_divergence_baseline_write_failed", extra={"error": str(exc)})


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for the R7 traffic-vs-offer divergence tripwire.

    DEFAULT-DARK: ``skipped`` (200) unless ``TRAFFIC_OFFER_DIVERGENCE_ENABLED`` is
    truthy. ``refused`` (the freshness/readability gate firing) is a deliberate SAFE
    outcome -> 200; only a genuine substrate/config error is 500. ``LastRunEpoch`` is
    emitted on every invocation so the dead-man tracks liveness."""
    logger.info("traffic_offer_divergence_invoked", extra={"has_context": context is not None})
    window_days = _int_env(TRAFFIC_WINDOW_DAYS_ENV_VAR, DEFAULT_TRAFFIC_WINDOW_DAYS)
    ceiling = _int_env(FRAME_STALENESS_CEILING_ENV_VAR, DEFAULT_FRAME_STALENESS_CEILING_SECONDS)
    try:
        result = run_divergence_evaluation(
            gate=_is_enabled,
            load_frame=_load_offer_frame,
            gather_traffic=lambda: _gather_traffic(window_days),
            read_baseline=_read_baseline,
            commit_baseline=_commit_baseline,
            ceiling_seconds=ceiling,
        )
    except Exception as exc:  # noqa: BLE001 -- lambda boundary: honest 500 (NOT a fabricated verdict)
        logger.error(
            "traffic_offer_divergence_error",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )
        _emit("TrafficOfferDivergenceError", 1)
        return {
            "statusCode": 500,
            "body": {"status": "error", "error": str(exc), "error_type": type(exc).__name__},
        }

    return {
        "statusCode": 500 if result.status == "error" else 200,
        "body": {
            "status": result.status,
            "reason": result.reason,
            "divergent_count": result.divergent_count,
            "newly_count": result.newly_count,
            "roster_size": result.roster_size,
        },
    }


__all__ = [
    "ALARM_BOUND_METRICS",
    "CLASS_ABSENT_FROM_FRAME",
    "CLASS_INFRAME_INACTIVE",
    "DivergenceVerdict",
    "EBI_RESOLVE_EVENTS",
    "EvaluationRefusedError",
    "METRIC_EVALUATION_REFUSED",
    "METRIC_LAST_RUN_EPOCH",
    "METRIC_NAMESPACE",
    "METRIC_NEWLY_TRADING",
    "METRIC_ROSTER_SIZE",
    "METRIC_TRADING_BY_CLASS",
    "METRIC_TRADING_COUNT",
    "RunResult",
    "SCHEDULING_BOOKING_EVENT",
    "SCHEDULING_R1_GATE_EVENT_EXCLUDED",
    "TrafficTally",
    "active_roster_phones",
    "assert_frame_fresh",
    "assert_frame_readable",
    "build_ebi_query",
    "build_scheduling_query",
    "classify_divergent",
    "compute_newly_divergent",
    "emit_evaluated",
    "emit_heartbeat",
    "emit_refused",
    "handler",
    "inframe_phones",
    "phone_hash",
    "resolve_divergence",
    "run_divergence_evaluation",
]
