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

★ CANARY-SENTINEL EXCLUSION (numerator integrity):
    The calendly-intake canary tenant is seeded with a synthetic business/unit/contact
    but NO offer row, so its reserved phone (``CANARY_SENTINEL_PHONE``) is absent from
    the active-offer roster BY CONSTRUCTION while every canary cycle logs traffic for
    it. BOTH traffic queries therefore carry an explicit exclusion clause -- otherwise
    a synthetic office scores DIVERGENT (``absent_from_frame``) forever, poisoning a
    business-of-record numerator with a row no operator can reconcile. Ruled in the
    ``autom8y`` repo at
    ``.ledge/decisions/ADR-resolve-cure-F1-canary-vertical-2026-08-08.md``
    (§ "Denominator-leak check", part (b)).

FRESHNESS-REFUSE (I-REFUSE-NEVER-FABRICATE, spec §2):
    The S3 offer-frame parquet etag drifts continuously (live re-warm -- observed
    245,844 B -> 245,779 B within one probe session, spec §5). On a stale /
    unreadable / schema-lagged / empty frame the evaluator emits
    ``EvaluationRefused=1`` and NO divergence verdict -- it NEVER fabricates a 0 or a
    divergence from a broken read. A fabricated 0 would read "all clear" while the
    instrument is blind; a fabricated divergence would false-page. Both are refused.

★ BOTH TRAFFIC LEGS ARE REQUIRED (no silent partial denominator):
    ``traffic(O, W)`` is a UNION over two sources. A leg that cannot be read does NOT
    degrade to the other leg -- it REFUSES the cycle (``EvaluationRefused=1``, no
    verdict) and stamps ``TrafficLegUnavailable`` with a bounded ``leg`` dimension so
    triage knows WHICH leg died. Rationale: a soft-degrading leg publishes a
    CONFIDENT-LOOKING count over HALF a denominator while ``EvaluationRefused=0``
    says all-clear -- the never-silent doctrine's exact inversion. This is the R-eps
    hazard: post-cutover, bookings migrate ONTO the scheduling plane, so a dropped
    scheduling leg degrades the instrument in DIRECT PROPORTION to the campaign
    succeeding. A silent partial denominator is now structurally impossible.

BASELINE-POISONING GUARD (spec §2 fast-burn):
    The committed hashed divergent phone-set (drives ``NewlyTradingWithoutActiveOffer
    Count``) is written ONLY on a NON-refused run. A refused run MUST NOT overwrite
    the baseline with an empty set -- else the next run reads every office as "newly
    divergent" and false-pages. This is a required unit tooth.

★ BASELINE 403-vs-404 (the other half of the same poisoning guard):
    An UNREADABLE baseline is only "first run" when S3 says the key is genuinely
    ABSENT (``NoSuchKey``/404). Any other failure -- above all ``AccessDenied``/403 --
    REFUSES. Without ``s3:ListBucket`` on the bucket S3 answers a MISSING key with 403,
    so absent-key and denied-read are wire-indistinguishable; reading 403 as "first
    run" makes the emitter re-seed from empty and publish
    ``newly ~= <whole standing divergent population>`` into the >=1 fast-burn alarm =
    a FALSE PAGE to a live SEV1 subscriber. The paired terraform grant makes the 404
    truthful; :data:`BASELINE_ABSENT_ERROR_CODES` makes the 403 loud.

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
        (default /aws/lambda/autom8-email-booking-intake -- verified live). REQUIRED:
        empty/unreadable REFUSES.
    TRAFFIC_OFFER_DIVERGENCE_SCHEDULING_LOG_GROUP: autom8y-scheduling SERVICE log group
        (default /ecs/autom8y-scheduling-service -- where ``booking_success`` is
        emitted). REQUIRED: empty/unreadable REFUSES.
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
    from collections.abc import Callable, Sequence

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
#: Diagnostic (no alarm of its own): =1 for the NAMED traffic leg that could not be
#: read this run. The REFUSE is what pages (via the armed ``EvaluationRefused`` alarm);
#: this metric only ATTRIBUTES which leg died, carrying a bounded ``leg`` dimension
#: (never a log-group ARN or any unbounded value).
METRIC_TRAFFIC_LEG_UNAVAILABLE = "TrafficLegUnavailable"

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
# Canary-sentinel exclusion (numerator integrity)
# ==============================================================================
#: The calendly-intake canary tenant's RESERVED synthetic office phone, in the E.164
#: form the seed writes and every canary cycle logs.
#:
#: ★ WHY BOTH TRAFFIC QUERIES MUST EXCLUDE IT. The canary seed creates a synthetic
#: business + unit + contact in the Businesses project but NO offer row, so the
#: sentinel is ABSENT from the active-offer roster BY CONSTRUCTION. Every canary cycle
#: logs it on the EBI resolve leg, so absent this exclusion the synthetic office lands
#: as DIVERGENT (class ``absent_from_frame``), adds +1 to ``TradingWithoutActiveOfferCount``
#: and burns a unit of the CARD-D ratchet-to-zero budget -- permanently poisoning a
#: business-of-record numerator with an "office" that is not a client and can never be
#: reconciled away. Ruled in the ``autom8y`` repo at
#: ``.ledge/decisions/ADR-resolve-cure-F1-canary-vertical-2026-08-08.md``
#: (§ "Denominator-leak check", part (b)).
#:
#: PRECEDENT for this explicit-exclusion-with-written-rationale pattern: the ``autom8y``
#: repo's ``terraform/services/auth/token_exchange_alarms.tf:172-183`` excludes the
#: ``calendly-intake-canary-seed`` service account from the token-exchange alarm roster
#: for the structurally identical reason -- a synthetic actor must never enter a
#: business-of-record instrument's population.
#:
#: EXACT-MATCH BY INTENT: the clause is ``!=`` on the full literal, never a prefix or
#: wildcard. A broadened match could silently swallow a REAL office; this is the one
#: reserved sentinel and nothing else.
CANARY_SENTINEL_PHONE = "+15550000000"

#: The Logs Insights filter clause carried by BOTH traffic queries. Built ONCE from
#: :data:`CANARY_SENTINEL_PHONE` so the two legs cannot drift apart -- traffic is a
#: UNION, so a single leg that lost the clause would re-open the whole leak.
CANARY_SENTINEL_EXCLUSION_CLAUSE = f'| filter office_phone != "{CANARY_SENTINEL_PHONE}"'

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
#: ★ The ``booking_success`` emitter is the MODERN autom8y-scheduling ECS service --
#: NOT the legacy monolith. Verified by file-read (no AWS needed):
#:   * emit site: autom8y-scheduling ``src/autom8_scheduling/scheduling/booking.py:221``
#:     -- ``logger.info("booking_success", extra={... "office_phone": office_phone ...})``
#:   * log group: autom8y ``terraform/modules/platform/primitives/ecs-fargate-service/
#:     main.tf:10`` name_prefix = ``autom8y-${service_name}-service`` (production) and
#:     ``:54`` ``name = "/ecs/${local.name_prefix}"``; autom8y
#:     ``terraform/services/scheduling/main.tf:42`` pins that prefix to
#:     ``autom8y-scheduling-service``. Sibling literals corroborate the convention
#:     (``/ecs/autom8y-{data,auth,asana}-service`` in terraform/shared/cloudwatch_queries.tf).
#: The PRIOR default ``/ecs/autom8-prod`` was a PHANTOM: ``autom8-prod`` is the legacy
#: ALB name, not a log group, and the group does not exist in the account -- every run
#: logged ``ResourceNotFoundException`` and the leg was silently dropped.
DEFAULT_SCHEDULING_LOG_GROUP = "/ecs/autom8y-scheduling-service"

#: ★ The phantom the scheduling leg used to default to. Named (not merely deleted) so a
#: unit tooth can prove the regression is caught rather than silently re-introduced.
PHANTOM_SCHEDULING_LOG_GROUP = "/ecs/autom8-prod"

#: Bounded ``leg`` dimension values for ``TrafficLegUnavailable`` + the refusal text.
TRAFFIC_LEG_EBI = "ebi"
TRAFFIC_LEG_SCHEDULING = "scheduling"

BASELINE_BUCKET_ENV_VAR = "TRAFFIC_OFFER_DIVERGENCE_BASELINE_BUCKET"
DEFAULT_BASELINE_BUCKET = "autom8-s3"
BASELINE_KEY = "soak-sentinel/r7-divergence-baseline.json"

#: S3/botocore error codes that mean the baseline object GENUINELY does not exist --
#: the ONLY codes that may be read as "first run, seed the baseline".
#:
#: ★ Every OTHER failure (notably ``AccessDenied`` / 403) REFUSES. Without
#: ``s3:ListBucket`` on the baseline bucket S3 answers a MISSING key with 403, not 404
#: -- so an auth failure and a first run are WIRE-INDISTINGUISHABLE. Treating 403 as
#: "first run" makes the emitter silently re-seed and publish ``newly ~= <the whole
#: standing divergent population>`` into the >=1 fast-burn alarm: a FALSE PAGE. The
#: paired terraform grant (``ListBucketForTruthful404OnBaselineKey``) is what makes the
#: 404 truthful; this constant is what makes the 403 loud.
BASELINE_ABSENT_ERROR_CODES: frozenset[str] = frozenset({"NoSuchKey", "404", "NotFound"})

OFFER_BUCKET_ENV_VAR = "ASANA_CACHE_S3_BUCKET"

#: Cap on per-office triage log lines per cycle. The divergent population is bounded by
#: the traffic denominator (~63-70 offices observed), so this is generous headroom; a
#: breach is LOUD (a distinct warning line), never a silent truncation.
PER_OFFICE_LOG_CAP = 250


class EvaluationRefusedError(Exception):
    """The run could not be proven complete -- REFUSE, emit no verdict.

    Raised by the frame freshness/readability gates, by an unreadable REQUIRED traffic
    leg, and by a non-absent baseline read failure. The handler converts it to an
    ``EvaluationRefused=1`` emission and returns WITHOUT a divergence verdict (the
    fail-safe: never fabricate a 0, a divergence, or a HALF-DENOMINATOR count from a
    broken read). The baseline is NOT committed on a refused run (poisoning guard).
    """


class TrafficLegUnavailableError(EvaluationRefusedError):
    """A REQUIRED traffic leg could not be read -- REFUSE, never a partial denominator.

    A subclass of :class:`EvaluationRefusedError` so it routes through the SAME armed
    ``EvaluationRefused`` alarm (no new alarm surface needed), while carrying ``leg``
    so the refusal can be ATTRIBUTED via the ``TrafficLegUnavailable`` diagnostic.
    """

    def __init__(self, leg: str, log_group: str, detail: str) -> None:
        self.leg = leg
        self.log_group = log_group
        super().__init__(
            f"REQUIRED traffic leg {leg!r} unreadable (log group {log_group!r}): {detail}. "
            "REFUSING the cycle: a partial traffic denominator would publish a "
            "confident-looking divergence count over HALF the input while "
            "EvaluationRefused=0 reads all-clear."
        )


class TrafficLeg(NamedTuple):
    """One REQUIRED traffic source: a named log group + the query that reads it.

    ``name`` is the bounded ``leg`` metric-dimension value (never the log-group ARN --
    unbounded dimensions are a CloudWatch cardinality trap).
    """

    name: str
    log_group: str
    query: str


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
# ★ Traffic union -- EVERY leg is REQUIRED (no silent partial denominator)
# ==============================================================================


def union_traffic_legs(
    legs: Sequence[TrafficLeg],
    *,
    run_leg: Callable[[TrafficLeg], dict[str, int]],
) -> TrafficTally:
    """Union EVERY configured traffic leg. A leg that cannot be read REFUSES the cycle.

    ``run_leg`` is injected so the leg-failure semantics are unit-testable with ZERO
    live AWS.

    ★ THE STRUCTURAL GUARD. The predecessor of this function swallowed a scheduling-leg
    exception and degraded to EBI-only, publishing ``TradingWithoutActiveOfferCount``
    (and ``EvaluationRefused=0``) over HALF the traffic denominator. That is
    fail-SOFT: the instrument reports a confident number while half-blind. Here a leg
    that is unset/blank or that raises REFUSES -- routed through the armed
    ``EvaluationRefused`` alarm and ATTRIBUTED by ``TrafficLegUnavailable{leg}``.

    An EMPTY result from a leg is NOT a failure (a genuinely quiet window is a real
    read); only an unreadable leg refuses.
    """
    if not legs:
        raise EvaluationRefusedError(
            "no traffic legs configured; refusing to evaluate divergence against an "
            "empty traffic denominator"
        )

    tally: dict[str, int] = {}
    for leg in legs:
        if not leg.log_group.strip():
            raise TrafficLegUnavailableError(leg.name, leg.log_group, "log group is unset/blank")
        try:
            leg_tally = run_leg(leg)
        except TrafficLegUnavailableError:
            raise
        except Exception as exc:  # ANY leg failure is a REFUSAL (re-raised), never a degrade
            raise TrafficLegUnavailableError(
                leg.name, leg.log_group, f"{type(exc).__name__}: {exc}"
            ) from exc
        for phone, count in leg_tally.items():
            key = _norm_phone(phone)
            if not key:
                continue
            tally[key] = tally.get(key, 0) + int(count)

    return TrafficTally(phones=frozenset(tally), bookings_by_phone=tally)


# ==============================================================================
# Baseline (fast-burn delta) -- hashed phone-set, poisoning-guarded
# ==============================================================================


def baseline_error_code(exc: BaseException) -> str:
    """Best-effort botocore error code for an S3 read failure (``""`` when unknown).

    Reads ``ClientError.response["Error"]["Code"]`` (and the HTTP status as a fallback)
    WITHOUT importing botocore -- the classifier stays unit-testable against a plain
    stub and the module keeps its zero-heavy-import posture.
    """
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return ""
    code = str((response.get("Error") or {}).get("Code", "")).strip()
    if code:
        return code
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return str(status).strip() if status is not None else ""


def classify_baseline_read_failure(exc: BaseException) -> bool:
    """``True`` iff the failure means the baseline key is GENUINELY ABSENT (seed once).

    ★ Every other failure -- above all ``AccessDenied``/403 -- returns ``False`` and the
    caller REFUSES. Absent ``s3:ListBucket`` S3 answers a MISSING key with 403, so
    "denied" and "absent" are wire-indistinguishable; reading 403 as first-run re-seeds
    the baseline from empty and publishes ``newly ~= <whole standing population>`` into
    the >=1 fast-burn alarm -- a FALSE PAGE. Correct-by-luck once is not a guard.
    """
    return baseline_error_code(exc) in BASELINE_ABSENT_ERROR_CODES


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


def emit_traffic_leg_unavailable(leg: str) -> None:
    """Attribute a refusal to the NAMED traffic leg that could not be read.

    Diagnostic only -- the REFUSE is what pages (the armed ``EvaluationRefused`` alarm).
    ``leg`` is a bounded vocabulary value (:data:`TRAFFIC_LEG_EBI` /
    :data:`TRAFFIC_LEG_SCHEDULING`), never a log-group ARN.
    """
    _emit(METRIC_TRAFFIC_LEG_UNAVAILABLE, 1, dimensions={"leg": leg})


def emit_refused(reason: str, *, leg: str | None = None) -> None:
    """Refuse emission: EvaluationRefused=1 and NO verdict metrics (never a fabricated 0).

    When the refusal came from an unreadable REQUIRED traffic leg, ``leg`` names it and
    ``TrafficLegUnavailable`` is stamped so triage does not have to grep the reason text.
    """
    logger.warning("traffic_offer_divergence_refused", extra={"reason": reason, "leg": leg})
    _emit(METRIC_EVALUATION_REFUSED, 1)
    if leg is not None:
        emit_traffic_leg_unavailable(leg)


def emit_per_office_triage(
    verdict: DivergenceVerdict,
    prior_hashes: set[str],
    bookings_by_phone: dict[str, int] | None = None,
) -> int:
    """Emit ONE bounded, non-PII structured line per divergent office. Returns the count.

    ★ This is the surface the alarm runbooks point triage at. Before this existed the
    runbooks named ``event=traffic_offer_divergence_evaluated`` for "the per-office
    structured log" -- but that event is AGGREGATE-ONLY, so the documented triage path
    did not exist.

    NON-PII by construction: the office is identified by the SAME SHA-256 phone hash the
    baseline commits (:func:`phone_hash`), never a plaintext phone or a guid. An operator
    resolves a hash by hashing their candidate phones -- the identical join the baseline
    already implies.

    LOUD truncation: past :data:`PER_OFFICE_LOG_CAP` lines the remainder is dropped and a
    distinct warning names how many were withheld (never a silent truncation).
    """
    bookings = bookings_by_phone or {}
    divergent = sorted(verdict.divergent_phones)
    emitted = 0
    for phone in divergent[:PER_OFFICE_LOG_CAP]:
        digest = phone_hash(phone)
        logger.info(
            "traffic_offer_divergence_office",
            extra={
                "phone_hash": digest,
                "class": verdict.classes[phone],
                "bookings": int(bookings.get(phone, 0)),
                "newly": digest not in prior_hashes,
            },
        )
        emitted += 1
    withheld = len(divergent) - emitted
    if withheld > 0:
        logger.warning(
            "traffic_offer_divergence_office_log_truncated",
            extra={"emitted": emitted, "withheld": withheld, "cap": PER_OFFICE_LOG_CAP},
        )
    return emitted


def emit_evaluated(
    verdict: DivergenceVerdict,
    newly_count: int,
    *,
    prior_hashes: set[str] | None = None,
    bookings_by_phone: dict[str, int] | None = None,
) -> None:
    """Verdict emission: the full R7 metric set for a non-refused run.

    ``EvaluationRefused=0`` publishes a real 0 so the refuse alarm sits in OK (not
    INSUFFICIENT_DATA). The per-office triage lives in structured LOG lines (queried
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
    # Structured per-RUN aggregate line (bounded counts + class split; NO phone/guid).
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
    # Structured per-OFFICE triage lines (the surface the alarm runbooks name).
    emit_per_office_triage(verdict, prior_hashes or set(), bookings_by_phone)


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

    ★ ``gather_traffic`` and ``read_baseline`` may ALSO refuse -- an unreadable REQUIRED
    traffic leg (:class:`TrafficLegUnavailableError`) and a non-absent baseline read
    failure (403) both land here. Both formerly degraded SILENTLY.
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
        prior_hashes = read_baseline()
        newly_count, new_hashes = compute_newly_divergent(verdict.divergent_phones, prior_hashes)
    except EvaluationRefusedError as exc:
        emit_refused(str(exc), leg=getattr(exc, "leg", None))
        # POISONING GUARD: baseline NOT committed on a refused run.
        return RunResult(
            status="refused", reason=str(exc), divergent_count=0, newly_count=0, roster_size=0
        )

    emit_evaluated(
        verdict,
        newly_count,
        prior_hashes=set(prior_hashes),
        bookings_by_phone=dict(traffic.bookings_by_phone),
    )
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
    ``scheduling_gate_rejected`` (that is R1, not R7). EXCLUDES the canary sentinel
    so the synthetic tenant cannot enter the divergence numerator."""
    events = " or ".join(f'event = "{e}"' for e in EBI_RESOLVE_EVENTS)
    # ★ CANARY-SENTINEL EXCLUSION (this is the leg the canary actually logs on).
    #   * sentinel      -- CANARY_SENTINEL_PHONE ("+15550000000"), the calendly-intake
    #     canary tenant's synthetic office phone: logged by every canary cycle, and
    #     seeded with NO offer row, so unexcluded it scores DIVERGENT/absent_from_frame.
    #   * ruling        -- autom8y repo,
    #     `.ledge/decisions/ADR-resolve-cure-F1-canary-vertical-2026-08-08.md`
    #     § "Denominator-leak check" (b).
    #   * precedent     -- autom8y repo,
    #     `terraform/services/auth/token_exchange_alarms.tf:172-183` (same synthetic
    #     actor excluded from the SA alarm roster, with the same written why).
    # It is a FILTER stage in the chain (before `| stats`), NOT a comment -- Logs
    # Insights `#` comments do not filter anything. The unit teeth pin both facts.
    return (
        "fields office_phone\n"
        f"| filter {events}\n"
        "| filter ispresent(office_phone)\n"
        f"{CANARY_SENTINEL_EXCLUSION_CLAUSE}\n"
        "| stats count() as bookings by office_phone"
    )


def build_scheduling_query(window_days: int) -> str:
    """Logs Insights query: distinct scheduling-committed offices + booking counts.

    Selects ONLY ``booking_success`` (a committed write on ``extra.office_phone``).
    NEVER selects ``scheduling_gate_rejected`` -- keying on a gate outcome would
    conflate R7 with the R1 intent-vs-gate instrument (the sharpest tooth, spec §1).
    EXCLUDES the canary sentinel so the synthetic tenant cannot enter the numerator."""
    # ★ CANARY-SENTINEL EXCLUSION -- carried on BOTH legs, not just the EBI one.
    #   traffic(O, W) is a UNION: an exclusion on one leg only would still let a
    #   canary-shaped booking on the other leg poison the numerator, so the clause is
    #   unconditional here even though today's canary cycle exercises the EBI leg.
    #   * sentinel  -- CANARY_SENTINEL_PHONE ("+15550000000"), the calendly-intake
    #     canary tenant's synthetic office phone; seeded with NO offer row.
    #   * ruling    -- autom8y repo,
    #     `.ledge/decisions/ADR-resolve-cure-F1-canary-vertical-2026-08-08.md`
    #     § "Denominator-leak check" (b).
    #   * precedent -- autom8y repo,
    #     `terraform/services/auth/token_exchange_alarms.tf:172-183`.
    # Applied AFTER the `extra.office_phone as office_phone` alias, so the clause
    # binds the aliased field. It is a FILTER stage, NOT a comment.
    return (
        "fields extra.office_phone as office_phone\n"
        f'| filter event = "{SCHEDULING_BOOKING_EVENT}"\n'
        "| filter ispresent(office_phone)\n"
        f"{CANARY_SENTINEL_EXCLUSION_CLAUSE}\n"
        "| stats count() as bookings by office_phone"
    )


def _run_logs_insights(
    client: Any, log_group: str, query: str, *, start: int, end: int
) -> dict[str, int]:
    """Run one Logs Insights query, return ``{office_phone: bookings}``.

    A query failure (missing log group / throttle / Failed status) RAISES.
    :func:`union_traffic_legs` converts that into a cycle REFUSAL -- there is no
    degrade-to-the-other-leg path (a partial denominator is structurally impossible)."""
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


def resolve_traffic_legs(window_days: int) -> list[TrafficLeg]:
    """Build the REQUIRED traffic legs from env config (both legs, always)."""
    return [
        TrafficLeg(
            name=TRAFFIC_LEG_EBI,
            log_group=os.environ.get(EBI_LOG_GROUP_ENV_VAR, DEFAULT_EBI_LOG_GROUP),
            query=build_ebi_query(window_days),
        ),
        TrafficLeg(
            name=TRAFFIC_LEG_SCHEDULING,
            log_group=os.environ.get(SCHEDULING_LOG_GROUP_ENV_VAR, DEFAULT_SCHEDULING_LOG_GROUP),
            query=build_scheduling_query(window_days),
        ),
    ]


def _gather_traffic(window_days: int) -> TrafficTally:
    """Union EBI + scheduling traffic over window W (join-keyed by office_phone).

    ★ BOTH legs are REQUIRED. See :func:`union_traffic_legs` -- an unreadable leg
    REFUSES the cycle rather than degrading to a half denominator."""
    import boto3

    client = boto3.client("logs")
    end = int(time.time())
    start = end - window_days * 86400

    def run_leg(leg: TrafficLeg) -> dict[str, int]:
        return _run_logs_insights(client, leg.log_group, leg.query, start=start, end=end)

    return union_traffic_legs(resolve_traffic_legs(window_days), run_leg=run_leg)


def _read_baseline() -> set[str]:
    """Read the prior committed hashed divergent phone-set from S3.

    ★ A GENUINELY-ABSENT key (``NoSuchKey``/404) is the first run -> empty prior, seed
    once. ANY other failure (notably ``AccessDenied``/403) REFUSES: absent
    ``s3:ListBucket`` a missing key answers 403, so treating 403 as first-run would
    silently re-seed and false-page the >=1 fast-burn alarm. The refusal NAMES the
    observed error code so it is actionable rather than a wedge."""
    import boto3

    bucket = os.environ.get(BASELINE_BUCKET_ENV_VAR, DEFAULT_BASELINE_BUCKET)
    client = boto3.client("s3")
    try:
        resp = client.get_object(Bucket=bucket, Key=BASELINE_KEY)
        data = json.loads(resp["Body"].read())
    except Exception as exc:  # classified below: proven-absent => seed once, else REFUSE
        code = baseline_error_code(exc) or type(exc).__name__
        if not classify_baseline_read_failure(exc):
            raise EvaluationRefusedError(
                f"baseline read at s3://{bucket}/{BASELINE_KEY} failed with {code!r} -- "
                "NOT a proven-absent key, so this run must not be treated as a first run. "
                "Re-seeding from an empty baseline would publish "
                "NewlyTradingWithoutActiveOfferCount ~= the whole standing divergent "
                "population into the >=1 fast-burn alarm (a false page). Grant "
                "s3:ListBucket on the baseline bucket (terraform "
                "traffic_offer_divergence_s3 / ListBucketForTruthful404OnBaselineKey) so "
                "a missing key answers 404, or fix the object's access."
            ) from exc
        logger.info(
            "traffic_offer_divergence_baseline_absent",
            extra={"error": str(exc), "error_code": code, "seeding": True},
        )
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
    "BASELINE_ABSENT_ERROR_CODES",
    "CANARY_SENTINEL_EXCLUSION_CLAUSE",
    "CANARY_SENTINEL_PHONE",
    "CLASS_ABSENT_FROM_FRAME",
    "CLASS_INFRAME_INACTIVE",
    "DEFAULT_EBI_LOG_GROUP",
    "DEFAULT_SCHEDULING_LOG_GROUP",
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
    "METRIC_TRAFFIC_LEG_UNAVAILABLE",
    "PER_OFFICE_LOG_CAP",
    "PHANTOM_SCHEDULING_LOG_GROUP",
    "RunResult",
    "SCHEDULING_BOOKING_EVENT",
    "SCHEDULING_R1_GATE_EVENT_EXCLUDED",
    "TRAFFIC_LEG_EBI",
    "TRAFFIC_LEG_SCHEDULING",
    "TrafficLeg",
    "TrafficLegUnavailableError",
    "TrafficTally",
    "active_roster_phones",
    "assert_frame_fresh",
    "assert_frame_readable",
    "baseline_error_code",
    "build_ebi_query",
    "build_scheduling_query",
    "classify_baseline_read_failure",
    "classify_divergent",
    "compute_newly_divergent",
    "emit_evaluated",
    "emit_heartbeat",
    "emit_per_office_triage",
    "emit_refused",
    "emit_traffic_leg_unavailable",
    "handler",
    "inframe_phones",
    "phone_hash",
    "resolve_divergence",
    "resolve_traffic_legs",
    "run_divergence_evaluation",
    "union_traffic_legs",
]
