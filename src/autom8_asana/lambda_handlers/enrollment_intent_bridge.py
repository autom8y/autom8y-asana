"""Lambda handler: WS-A enrollment intent -> scheduling gate bridge (DEFAULT-DARK).

GRANDEUR ANCHOR (the throughline this bridge serves):
    "ONE intent surface reaching the gate through ONE governed, role-guarded,
    receipted write path; intent default-open, EXECUTION fail-closed; no silent
    enrollment states -- a bridge that cannot prove its frame is real REFUSES
    loudly and writes NOTHING."

Design of record: ``.ledge/specs/TDD-ws-a-intent-gate-bridge-2026-08-05.md``
(autom8y repo) §3. Companion ADR: ``ADR-ws-a-bridge-placement-2026-08-05.md``
(FORK-1 -> Option B: the bridge lives in autom8y-asana, natively co-located with
the frames it reads).

The PURE half -- the three-frame projection, the R1 coercion, and all four
refusal predicates -- lives in
:mod:`autom8_asana.enrollment.intent_projection` (WS-A PR-2). This module is the
I/O half: the DARK gate, the S3 reads, the governed HTTP client, the two-pass
delta loop, and the metric/receipt surface.

------------------------------------------------------------------------------
★ THE REFUSAL PREDICATE -- THE STRUCTURAL CURE, NOT AN OPTIONAL HARDENING
------------------------------------------------------------------------------
``derive_enrolled(None) -> True`` is ratified POLICY (charter R1), so a fossil,
collapsed, or schema-lagged intent frame projects null intent for every reachable
office, coerces each to Enabled *correctly per policy*, and writes it through the
governed path *correctly per R4*. The result is MASS SILENT ENROLLMENT executed
flawlessly by a system with no defect in it -- and every PT-03 leg passes under it,
because PT-03 certifies the DOOR, not the intent that walks through it.

``EDGE-bridge-arm-after-PT02`` governs the SEQUENCE (the bridge must not arm until
PT-02 has PASSED). This module makes the same failure UNREPRESENTABLE regardless
of sequencing. Four guards, each refusing the WHOLE cycle and writing NOTHING:

  1. SCHEMA-LAG   required columns absent on any frame     -> FrameSchemaLagError
  2. FRESHNESS    any of the THREE frames stale/absent/    -> EnrollmentRefusedError
                  unprovable age (source_complete = False)
  3. UNIVERSE     in-scope phones below the baseline-      -> EnrollmentRefusedError
     FLOOR        relative floor
  4. DELTA        computed flip-delta above the ceiling    -> EnrollmentRefusedError
     CEILING

Ship both the constraint and the predicate: a predicate can be misconfigured, a
constraint can be skipped. Neither alone is sufficient.

★ Plus a fifth, from R-1 (silent no-op): a cycle that resolves ZERO offices while
the in-scope universe is non-empty is a REFUSE, not a success. A phone-format
divergence between the frame and ``business_offers`` would otherwise make the
bridge look perfectly healthy while doing nothing at all.

------------------------------------------------------------------------------
★ REFUSE-ON-ABSENT-FUEL -- the floor and the ceiling have NO DEFAULTS
------------------------------------------------------------------------------
:data:`MIN_INSCOPE_PHONES_ENV_VAR` and :data:`MAX_DELTA_PER_CYCLE_ENV_VAR` are
deliberately un-defaulted. A guessed floor is no floor: the producer's
``MIN_POSTURE_SIGNAL_ROWS = 1`` would pass the observed 932 -> 1-44 collapse
untouched (CARD WS-B/4), and the DIAG's ~921-guid / 475-guard anchor is the
GUID-side number over a different filter -- transposing it into a PHONE-keyed
floor would be a fabricated threshold. Both are set at deploy time from the live
recovered universe (TDD §6 build-entry measurement E-2). Unset => REFUSE.

------------------------------------------------------------------------------
TWO PASSES, BECAUSE "REFUSE WHOLE" REQUIRES KNOWING THE DELTA FIRST
------------------------------------------------------------------------------
  PASS 1 (READ)  GET /config for every in-scope office -> current gate state.
                 Offices that 404 / fail to read are classified and DROP OUT of
                 the delta: an office whose current state is UNKNOWN is never
                 written (a write from an unknown baseline is the blind
                 mass-change this design refuses).
  GATE           assert_delta_within_ceiling(len(delta)). A breach refuses the
                 WHOLE cycle -- nothing has been written yet, by construction.
  PASS 2 (WRITE) PATCH only the delta, sequentially.

Consequence: re-running is safe, steady-state writes are ZERO, and every
``scheduling_config_updated`` receipt corresponds to a REAL state change. That is
what makes the PT-03 receipt leg meaningful -- there is no receipt theatre.

------------------------------------------------------------------------------
READ-ONLY SUBSTRATE ACCESS -- NO ``Business()``, NO ASANA_PAT, NO DB
------------------------------------------------------------------------------
The frames are read as raw ``boto3.get_object`` + ``pl.read_parquet`` passes
(mirroring the WS-E tripwire). ``Business()`` is NEVER instantiated -- it WRITES to
Asana on init (probe scar). The ONLY write this Lambda can perform, anywhere, is
the governed ``PATCH`` through ``autom8y-scheduling``.

------------------------------------------------------------------------------
DISJOINTNESS FROM WS-E (named in both modules so a future reader cannot merge them)
------------------------------------------------------------------------------
``traffic_offer_divergence_tripwire`` surfaces offices TRADING WITHOUT A ROSTER
ROW and deliberately excludes ``scheduling_gate_rejected``. THIS bridge closes the
complementary R1 class: ROSTER-ENABLED BUT GATE-DECLINED. WS-E is the instrument
that points here; this is the instrument that acts.

Environment Variables:
    ENROLLMENT_INTENT_BRIDGE_ENABLED: DEFAULT-OFF activation gate. UNSET => DARK.
    ENROLLMENT_INTENT_BRIDGE_DRY_RUN: project + compute the delta, write NOTHING.
    ENROLLMENT_INTENT_BRIDGE_MIN_INSCOPE_PHONES: universe floor. NO DEFAULT.
    ENROLLMENT_INTENT_BRIDGE_MAX_DELTA_PER_CYCLE: mass-change brake. NO DEFAULT.
    ENROLLMENT_INTENT_BRIDGE_FRAME_STALENESS_SECONDS: refuse ceiling on frame age
        (default 43200 = 12h = 2x the 6h warm cadence; matches WS-E).
    ENROLLMENT_INTENT_BRIDGE_SCHEDULING_URL: governed write path base URL.
    ENROLLMENT_INTENT_BRIDGE_HTTP_TIMEOUT_SECONDS: per-request timeout (default 10).
    ASANA_CACHE_S3_BUCKET: frame bucket (house canonical, ADR-0002).
    SERVICE_CLIENT_ID / SERVICE_CLIENT_SECRET: the asana-enrollment-bridge SA.
"""

from __future__ import annotations

import io
import os
import time
import uuid
from typing import TYPE_CHECKING, Any, NamedTuple

from autom8y_log import get_logger

from autom8_asana.enrollment.intent_projection import (
    BUSINESS_FRAME_KEY,
    OFFER_FRAME_KEY,
    UNIT_HOLDER_FRAME_KEY,
    EnrollmentRefusedError,
    FrameSchemaLagError,
    assert_delta_within_ceiling,
    assert_frames_fresh,
    assert_universe_floor,
    project_enrollment_intent,
)
from autom8_asana.enrollment.scheduling_client import (
    DEFAULT_SCHEDULING_BASE_URL,
    NON_ERROR_OUTCOMES,
    Outcome,
    SchedulingConfigClient,
)
from autom8_asana.lambda_handlers.cloudwatch import emit_metric

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from autom8_asana.enrollment.intent_projection import (
        EnrollmentIntent,
        EnrollmentProjection,
    )

logger = get_logger(__name__)

# ==============================================================================
# ★ CROSS-REPO EMIT->ALARM CONTRACT (byte-exact match with the terraform half)
# ==============================================================================
# COUNTERPART: autom8y repo, terraform/services/asana/enrollment_intent_bridge_*.tf
# A rename here WITHOUT the matching rename there yields a green-on-both-halves,
# dead-as-a-pair INSUFFICIENT_DATA alarm. These constants ARE the seam, and they
# are pinned in __all__ + the terraform test so a rename trips CI, not production.
METRIC_NAMESPACE = "Autom8y/AsanaEnrollmentBridge"

#: Dead-man: emitted EVERY invocation (incl. DARK / refused).
METRIC_LAST_RUN_EPOCH = "LastRunEpoch"
#: =1 when the cycle REFUSED (frames unprovable, universe collapsed, delta ceiling).
METRIC_EVALUATION_REFUSED = "EvaluationRefused"
#: =1 specifically when the delta ceiling tripped (a distinct operator signal).
METRIC_DELTA_CEILING_TRIPPED = "DeltaCeilingTripped"
#: The universe denominator -- the floor alarm's target.
METRIC_IN_SCOPE_OFFICES = "InScopeOffices"
#: Offices whose Asana intent differs from live gate state this cycle.
METRIC_INTENT_DELTA = "IntentDeltaCount"
#: Gate writes that actually landed. Steady state == 0 (NFR-3).
METRIC_WRITES_APPLIED = "ConfigWritesApplied"
#: Offices already in the intended state (no call made).
METRIC_NOOP_OFFICES = "NoopOffices"
#: Phone present + in scope, but no Business row (R-1 silent-no-op canary).
METRIC_UNRESOLVED_OFFICES = "UnresolvedOfficeCount"
#: In scope with a Business row but no business offer -- setup work.
METRIC_NOT_CONFIGURED_OFFICES = "NotConfiguredOfficeCount"
#: Enable refused for unmet prerequisites. LOUD + queued; NOT an error.
METRIC_PREREQ_REFUSED = "EnrollmentPrereqRefusedCount"
#: The guard bit us (401/403) -- the observable side of "the guard BITES".
METRIC_WRITE_DENIED = "WriteDeniedCount"
#: Phone rejected by the gate's E.164 validation. Counted, never canonicalized.
METRIC_INVALID_PHONE = "InvalidPhoneFormatCount"
#: Genuine faults (transport / unexpected status).
METRIC_ERRORS = "BridgeErrorCount"
#: R-12 dashboard: in-scope offices the guid-keyed producer cannot see.
METRIC_GUID_NULL_IN_SCOPE = "GuidNullInScopeCount"
#: R-11 dashboard: active-roster phones with no office-spine row (silently excluded).
METRIC_ROSTER_ONLY_PHONES = "RosterOnlyPhoneCount"
#: Per-phone custom_cal_status disagreement (drift signal; does not block).
METRIC_STATUS_DRIFT = "StatusDriftPhoneCount"

#: The alarm-bound metric names, pinned as a set so the terraform test can assert
#: the emit<->alarm contract mechanically.
ALARM_BOUND_METRICS: frozenset[str] = frozenset(
    {
        METRIC_LAST_RUN_EPOCH,
        METRIC_EVALUATION_REFUSED,
        METRIC_DELTA_CEILING_TRIPPED,
        METRIC_IN_SCOPE_OFFICES,
        METRIC_WRITES_APPLIED,
        METRIC_UNRESOLVED_OFFICES,
        METRIC_WRITE_DENIED,
        METRIC_ERRORS,
    }
)

# ==============================================================================
# Config knobs
# ==============================================================================
ENABLED_ENV_VAR = "ENROLLMENT_INTENT_BRIDGE_ENABLED"
DRY_RUN_ENV_VAR = "ENROLLMENT_INTENT_BRIDGE_DRY_RUN"

#: ★ NO DEFAULT (refuse-on-absent-fuel -- see the module docstring).
MIN_INSCOPE_PHONES_ENV_VAR = "ENROLLMENT_INTENT_BRIDGE_MIN_INSCOPE_PHONES"
#: ★ NO DEFAULT (refuse-on-absent-fuel).
MAX_DELTA_PER_CYCLE_ENV_VAR = "ENROLLMENT_INTENT_BRIDGE_MAX_DELTA_PER_CYCLE"

FRAME_STALENESS_CEILING_ENV_VAR = "ENROLLMENT_INTENT_BRIDGE_FRAME_STALENESS_SECONDS"
#: 2x the 6h warm cadence -- identical to the WS-E tripwire so the two instruments
#: agree about what "stale" means.
DEFAULT_FRAME_STALENESS_CEILING_SECONDS = 43200

SCHEDULING_URL_ENV_VAR = "ENROLLMENT_INTENT_BRIDGE_SCHEDULING_URL"
HTTP_TIMEOUT_ENV_VAR = "ENROLLMENT_INTENT_BRIDGE_HTTP_TIMEOUT_SECONDS"
DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0

FRAME_BUCKET_ENV_VAR = "ASANA_CACHE_S3_BUCKET"

#: The three frames, in read order: (label, S3 key).
FRAME_SPECS: tuple[tuple[str, str], ...] = (
    ("unit_holder", UNIT_HOLDER_FRAME_KEY),
    ("business", BUSINESS_FRAME_KEY),
    ("offer", OFFER_FRAME_KEY),
)


class LoadedFrames(NamedTuple):
    """The three warmed frames plus their S3 ``LastModified`` epochs."""

    unit_holder: pl.DataFrame
    business: pl.DataFrame
    offer: pl.DataFrame
    #: ``(label, last_modified_epoch_or_None)`` -- ``None`` is itself a refusal.
    ages: tuple[tuple[str, float | None], ...]


class CycleResult(NamedTuple):
    """What the orchestrator returns (handler + tests read this)."""

    status: str  # skipped | refused | evaluated | error
    reason: str | None
    cycle_id: str
    in_scope: int
    delta: int
    applied: int
    outcomes: dict[str, int]


# ==============================================================================
# Metric emission
# ==============================================================================


def _emit(metric: str, value: float, *, dimensions: dict[str, str] | None = None) -> None:
    """Emit into the bridge namespace (overrides the house default namespace)."""
    emit_metric(metric, value, dimensions=dimensions, namespace=METRIC_NAMESPACE)


def emit_heartbeat(now_epoch: float) -> None:
    """Dead-man heartbeat -- emitted on EVERY invocation (skipped/refused/evaluated).

    The bridge's own absence must be detectable on a metric that EXISTS every run;
    an orphaned dead-man watching a namespace nobody emits into is not a dead-man.
    """
    _emit(METRIC_LAST_RUN_EPOCH, now_epoch)


def emit_refused(reason: str, *, cycle_id: str, delta_ceiling_tripped: bool = False) -> None:
    """Refusal emission: ``EvaluationRefused=1`` and NO verdict metrics.

    ★ Never a fabricated 0. A fabricated ``InScopeOffices=0`` would read "nothing
    to do, all clear" while the instrument is blind; a fabricated delta would
    false-act. Both are refused. Nothing has been written when this fires.
    """
    logger.warning(
        "enrollment_bridge_refused",
        extra={"reason": reason, "cycle_id": cycle_id},
    )
    _emit(METRIC_EVALUATION_REFUSED, 1)
    if delta_ceiling_tripped:
        _emit(METRIC_DELTA_CEILING_TRIPPED, 1)


def emit_cycle(
    projection: EnrollmentProjection,
    *,
    cycle_id: str,
    delta: int,
    outcomes: dict[Outcome, int],
    prereq_reasons: dict[str, int],
    dry_run: bool,
) -> None:
    """Verdict emission for a non-refused cycle.

    ``EvaluationRefused=0`` publishes a real 0 so the refuse alarm sits in OK
    rather than INSUFFICIENT_DATA. Per-office triage lives in structured LOG lines,
    NEVER a CloudWatch dimension (I-NO-PII-METRIC: never a phone or a guid).
    """
    counts = projection.counts
    _emit(METRIC_EVALUATION_REFUSED, 0)
    _emit(METRIC_DELTA_CEILING_TRIPPED, 0)
    _emit(METRIC_IN_SCOPE_OFFICES, counts.in_scope_phones)
    _emit(METRIC_INTENT_DELTA, delta)
    _emit(METRIC_WRITES_APPLIED, outcomes.get(Outcome.APPLIED, 0))
    _emit(METRIC_NOOP_OFFICES, outcomes.get(Outcome.NOOP, 0))
    _emit(METRIC_UNRESOLVED_OFFICES, outcomes.get(Outcome.UNRESOLVED, 0))
    _emit(METRIC_NOT_CONFIGURED_OFFICES, outcomes.get(Outcome.NOT_CONFIGURED, 0))
    _emit(METRIC_PREREQ_REFUSED, outcomes.get(Outcome.PREREQ_REFUSED, 0))
    _emit(METRIC_WRITE_DENIED, outcomes.get(Outcome.WRITE_DENIED, 0))
    _emit(METRIC_INVALID_PHONE, outcomes.get(Outcome.INVALID_PHONE, 0))
    # ★ The error budget is derived from NON_ERROR_OUTCOMES rather than an
    # enumerated list, so a future outcome added to the vocabulary counts as a
    # fault by DEFAULT until it is explicitly declared benign. Fail-loud on the
    # unknown; an omitted enumeration entry would silence a new failure class.
    _emit(METRIC_ERRORS, sum(v for k, v in outcomes.items() if k not in NON_ERROR_OUTCOMES))
    _emit(METRIC_GUID_NULL_IN_SCOPE, counts.guid_null_in_scope)
    _emit(METRIC_ROSTER_ONLY_PHONES, counts.roster_only_phones)
    _emit(METRIC_STATUS_DRIFT, counts.status_drift_phones)
    # Prereq refusals dimensioned by REASON (a bounded, non-PII vocabulary the
    # service defines: timezone_not_configured / business_hours_not_configured /
    # appointment_duration_not_set).
    for reason, count in sorted(prereq_reasons.items()):
        _emit(METRIC_PREREQ_REFUSED, count, dimensions={"reason": reason})

    logger.info(
        "enrollment_bridge_cycle_summary",
        extra={
            "cycle_id": cycle_id,
            "dry_run": dry_run,
            "spine_rows": counts.spine_rows,
            "phoneless_dropped": counts.phoneless_dropped,
            "spine_phones": counts.spine_phones,
            "roster_phones": counts.roster_phones,
            "in_scope_phones": counts.in_scope_phones,
            "out_of_scope_phones": counts.out_of_scope_phones,
            "roster_only_phones": counts.roster_only_phones,
            "status_drift_phones": counts.status_drift_phones,
            "guid_null_in_scope": counts.guid_null_in_scope,
            "guid_ambiguous_phones": counts.guid_ambiguous_phones,
            "explicit_enabled": counts.explicit_enabled,
            "explicit_disabled": counts.explicit_disabled,
            "coerced_unset": counts.coerced_unset,
            "unknown_option_defaulted": counts.unknown_option_defaulted,
            "delta": delta,
            **{
                f"outcome_{k.value}": v
                for k, v in sorted(outcomes.items(), key=lambda p: p[0].value)
            },
        },
    )


def emit_office_line(
    intent: EnrollmentIntent,
    *,
    outcome: Outcome,
    cycle_id: str,
    current: bool | None,
    reasons: tuple[str, ...] = (),
    detail: str | None = None,
) -> None:
    """One structured per-office line -- THE QUEUE (no new datastore, no backlog).

    The queue is the emitted record, re-derived every cycle from live truth, so it
    cannot go stale. Refused / unresolved / not-configured offices appear here
    exactly once per cycle (NFR-5), and ``reasons[]`` on a prereq refusal is the
    setup-work signal the operator acts on.
    """
    logger.info(
        "enrollment_bridge_office",
        extra={
            "cycle_id": cycle_id,
            "office_phone": intent.office_phone,
            "outcome": outcome.value,
            "intent_enabled": intent.intent_enabled,
            "intent_source": intent.intent_source,
            "current_enabled": current,
            "business_gid": intent.business_gid,
            "company_id": intent.company_id,
            "reasons": list(reasons),
            "detail": detail,
        },
    )


# ==============================================================================
# Orchestrator (injectable I/O -- unit-testable with ZERO live AWS / HTTP)
# ==============================================================================


def run_enrollment_bridge(
    *,
    gate: Callable[[], bool],
    load_frames: Callable[[], LoadedFrames],
    client_factory: Callable[[], SchedulingConfigClient],
    min_inscope_phones: int,
    max_delta_per_cycle: int,
    staleness_ceiling_seconds: float,
    dry_run: bool = False,
    now_epoch: float | None = None,
    cycle_id: str | None = None,
) -> CycleResult:
    """One bridge cycle under the DARK gate + the five refusals + delta-only writes.

    I/O is injected so every refusal and every disposition is unit-testable with no
    live AWS and no live HTTP.

    Order is load-bearing: the DARK gate short-circuits BEFORE any S3 read AND
    before the client is constructed, and the delta ceiling is evaluated BEFORE any
    write -- so a refusal at any point means nothing was written, by construction
    rather than by cleanup.

    ★ ``client_factory`` is a FACTORY, not a client, precisely so a DARK deployment
    never constructs service credentials. Until the SA is provisioned and its
    secret written, building the client raises -- and a dark bridge that 500s every
    six hours on credentials it is not yet supposed to have would be a self-inflicted
    alarm. Dark means dark: no S3 read, no token exchange, no HTTP.
    """
    now = time.time() if now_epoch is None else now_epoch
    run_id = cycle_id or str(uuid.uuid4())
    emit_heartbeat(now)

    if not gate():
        logger.info("enrollment_bridge_skipped", extra={"reason": "gate_off", "cycle_id": run_id})
        return CycleResult("skipped", "gate_off", run_id, 0, 0, 0, {})

    client = client_factory()
    outcomes: dict[Outcome, int] = {}
    prereq_reasons: dict[str, int] = {}

    def _record(outcome: Outcome) -> None:
        outcomes[outcome] = outcomes.get(outcome, 0) + 1

    try:
        # --- REFUSAL 2: freshness of ALL THREE frames (source_complete) ---------
        frames = load_frames()
        assert_frames_fresh(frames.ages, now_epoch=now, ceiling_seconds=staleness_ceiling_seconds)
        # --- REFUSAL 1: schema-lag (inside the projection) ----------------------
        projection = project_enrollment_intent(frames.unit_holder, frames.business, frames.offer)
        # --- REFUSAL 3: the universe floor -------------------------------------
        assert_universe_floor(projection.counts.in_scope_phones, floor=min_inscope_phones)

        # --- PASS 1 (READ): establish current gate state; NOTHING is written ----
        pending: list[tuple[EnrollmentIntent, bool]] = []
        resolved = 0
        for intent in projection.intents:
            read = client.get_config(intent.office_phone)
            if read.outcome is not Outcome.READ_OK:
                # UNRESOLVED / NOT_CONFIGURED / INVALID_PHONE / denied / failed --
                # each is counted, emitted, and DROPS OUT of the delta. An office
                # whose current state is unknown is never written.
                _record(read.outcome)
                emit_office_line(
                    intent,
                    outcome=read.outcome,
                    cycle_id=run_id,
                    current=None,
                    detail=read.detail,
                )
                continue
            resolved += 1
            if read.scheduling_enabled == intent.intent_enabled:
                _record(Outcome.NOOP)
                continue
            pending.append((intent, bool(read.scheduling_enabled)))

        # --- REFUSAL 5 (R-1): the silent no-op canary ---------------------------
        # A phone-format divergence between the frame and business_offers would make
        # every office 404 while the bridge reported a clean run. Zero resolved
        # against a non-empty universe is a REFUSE, not a success.
        if projection.intents and resolved == 0:
            raise EnrollmentRefusedError(
                f"resolved 0 of {len(projection.intents)} in-scope offices -- the "
                "phone join is producing nothing. A silent no-op reads as a healthy "
                "cycle; refusing instead."
            )

        # --- REFUSAL 4: the delta ceiling, BEFORE any write ---------------------
        delta = len(pending)
        assert_delta_within_ceiling(delta, ceiling=max_delta_per_cycle)

    except (EnrollmentRefusedError, FrameSchemaLagError) as exc:
        emit_refused(
            str(exc),
            cycle_id=run_id,
            delta_ceiling_tripped="delta ceiling tripped" in str(exc),
        )
        return CycleResult("refused", str(exc), run_id, 0, 0, 0, {})

    # --- PASS 2 (WRITE): the delta only, sequentially ---------------------------
    # Sequential by choice: this is a WRITE path against a single service, the
    # per-cycle delta is small by construction (the ceiling bounds it), and NFR-1
    # (<120s at N<=150) is met comfortably. Concurrency here would buy nothing and
    # would complicate the "receipt exists iff state moved" story.
    applied = 0
    for intent, current in pending:
        if dry_run:
            # ★ DRY-RUN: the delta is computed and emitted, and NOTHING is written.
            # This is the pre-arm observation cycle (TDD §8.1) -- a dry run that
            # REFUSES is the correct outcome and blocks the arm. The outcome is
            # DRY_RUN_SUPPRESSED, never NOOP: these offices WOULD have moved, and a
            # dry run that reported them as no-ops would read as "already converged".
            _record(Outcome.DRY_RUN_SUPPRESSED)
            emit_office_line(
                intent,
                outcome=Outcome.DRY_RUN_SUPPRESSED,
                cycle_id=run_id,
                current=current,
                detail="dry_run: write suppressed",
            )
            continue
        write = client.set_scheduling_enabled(
            intent.office_phone,
            scheduling_enabled=intent.intent_enabled,
            intent_source=intent.intent_source,
        )
        _record(write.outcome)
        if write.outcome is Outcome.APPLIED:
            applied += 1
        if write.outcome is Outcome.PREREQ_REFUSED:
            # ★ LOUD + queued, NEVER force-flipped and NEVER retried as a flip.
            for reason in write.reasons or ("unspecified",):
                prereq_reasons[reason] = prereq_reasons.get(reason, 0) + 1
        emit_office_line(
            intent,
            outcome=write.outcome,
            cycle_id=run_id,
            current=current,
            reasons=write.reasons,
            detail=write.detail,
        )

    emit_cycle(
        projection,
        cycle_id=run_id,
        delta=delta,
        outcomes=outcomes,
        prereq_reasons=prereq_reasons,
        dry_run=dry_run,
    )
    return CycleResult(
        status="evaluated",
        reason=None,
        cycle_id=run_id,
        in_scope=projection.counts.in_scope_phones,
        delta=delta,
        applied=applied,
        outcomes={k.value: v for k, v in outcomes.items()},
    )


# ==============================================================================
# Live wiring (env config + raw S3 + the governed HTTP client)
# ==============================================================================


def _is_enabled() -> bool:
    """DEFAULT-OFF activation gate (UNSET => DARK)."""
    return os.environ.get(ENABLED_ENV_VAR, "").strip().lower() in {"1", "true", "yes", "on"}


def _is_dry_run() -> bool:
    """DRY-RUN: project, read, compute the delta -- write NOTHING."""
    return os.environ.get(DRY_RUN_ENV_VAR, "").strip().lower() in {"1", "true", "yes", "on"}


def _int_env(var: str, default: int) -> int:
    raw = os.environ.get(var)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _required_int_env(var: str) -> int:
    """Read a threshold that MUST be supplied. Absent / unparseable => 0 => REFUSE.

    ★ Refuse-on-absent-fuel. Returning 0 routes into
    :func:`assert_universe_floor` / :func:`assert_delta_within_ceiling`, both of
    which treat a non-positive threshold as a refusal with an explicit reason.
    A silently-defaulted threshold is the failure this design is written against.
    """
    raw = os.environ.get(var)
    if raw is None or not raw.strip():
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _load_frames() -> LoadedFrames:
    """Raw pure-Polars read of the three warmed frames from S3 (NO ``Business()``).

    A missing object / unreadable body is surfaced as a REFUSAL rather than a crash
    -- an absent frame is a refuse, not a 500. Every frame must be readable
    (``source_complete``); a partial read can never yield a partial cycle.
    """
    import boto3
    import polars as pl

    bucket = os.environ.get(FRAME_BUCKET_ENV_VAR)
    if not bucket:
        raise EnrollmentRefusedError(f"frame bucket unset ({FRAME_BUCKET_ENV_VAR})")
    client = boto3.client("s3")

    loaded: dict[str, pl.DataFrame] = {}
    ages: list[tuple[str, float | None]] = []
    for label, key in FRAME_SPECS:
        try:
            resp = client.get_object(Bucket=bucket, Key=key)
            body = resp["Body"].read()
            last_modified = resp.get("LastModified")
        except Exception as exc:
            raise EnrollmentRefusedError(
                f"frame '{label}' unreadable at s3://{bucket}/{key}: {exc}"
            ) from exc
        loaded[label] = pl.read_parquet(io.BytesIO(body))
        ages.append((label, last_modified.timestamp() if last_modified is not None else None))

    return LoadedFrames(
        unit_holder=loaded["unit_holder"],
        business=loaded["business"],
        offer=loaded["offer"],
        ages=tuple(ages),
    )


def _build_client() -> tuple[SchedulingConfigClient, Callable[[], None]]:
    """Build the governed-path client. Returns ``(client, close)``.

    ``autom8y_http.SyncHttpClient`` is the house HTTP primitive (raw ``httpx`` is
    banned). Retry and circuit-breaking are DISABLED on this client: it is a WRITE
    path whose caller already classifies every outcome, and an SDK-level retry on a
    PATCH would obscure the "a receipt exists iff state moved" contract.
    """
    from autom8y_http import HttpClientConfig, SyncHttpClient

    from autom8_asana.auth.service_token import ServiceTokenAuthProvider

    base_url = os.environ.get(SCHEDULING_URL_ENV_VAR, DEFAULT_SCHEDULING_BASE_URL)
    timeout = float(_int_env(HTTP_TIMEOUT_ENV_VAR, int(DEFAULT_HTTP_TIMEOUT_SECONDS)))
    http = SyncHttpClient(
        HttpClientConfig(
            base_url=base_url,
            timeout=timeout,
            enable_retry=False,
            enable_circuit_breaker=False,
        )
    )
    auth = ServiceTokenAuthProvider()

    def _close() -> None:
        http.close()
        auth.close()

    return SchedulingConfigClient(http, lambda: auth.get_secret("service_token")), _close


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for the WS-A enrollment intent -> gate bridge.

    DEFAULT-DARK: ``skipped`` (200) unless ``ENROLLMENT_INTENT_BRIDGE_ENABLED`` is
    truthy. ``refused`` is a deliberate SAFE outcome -> 200 (the guards working as
    designed is not an incident); only a genuine substrate/config fault is 500.
    ``LastRunEpoch`` is emitted on every invocation so the dead-man tracks liveness.

    ``event`` may carry ``{"dry_run": true}`` to force a write-suppressed cycle
    without changing the deployed environment -- the pre-arm observation path.
    """
    logger.info(
        "enrollment_bridge_invoked",
        extra={"has_context": context is not None},
    )
    dry_run = _is_dry_run() or bool((event or {}).get("dry_run"))
    # Closers are collected by the factory, so a DARK run (which never calls it)
    # constructs nothing and has nothing to close.
    closers: list[Callable[[], None]] = []

    def _factory() -> SchedulingConfigClient:
        client, close = _build_client()
        closers.append(close)
        return client

    try:
        result = run_enrollment_bridge(
            gate=_is_enabled,
            load_frames=_load_frames,
            client_factory=_factory,
            min_inscope_phones=_required_int_env(MIN_INSCOPE_PHONES_ENV_VAR),
            max_delta_per_cycle=_required_int_env(MAX_DELTA_PER_CYCLE_ENV_VAR),
            staleness_ceiling_seconds=_int_env(
                FRAME_STALENESS_CEILING_ENV_VAR, DEFAULT_FRAME_STALENESS_CEILING_SECONDS
            ),
            dry_run=dry_run,
        )
    except Exception as exc:  # noqa: BLE001 -- lambda boundary: honest 500, NOT a fabricated cycle
        logger.error(
            "enrollment_bridge_error",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )
        _emit(METRIC_ERRORS, 1)
        return {
            "statusCode": 500,
            "body": {"status": "error", "error": str(exc), "error_type": type(exc).__name__},
        }
    finally:
        for close in closers:
            close()

    return {
        "statusCode": 200,
        "body": {
            "status": result.status,
            "reason": result.reason,
            "cycle_id": result.cycle_id,
            "in_scope": result.in_scope,
            "delta": result.delta,
            "applied": result.applied,
            "outcomes": result.outcomes,
        },
    }


__all__ = [
    "ALARM_BOUND_METRICS",
    "DEFAULT_FRAME_STALENESS_CEILING_SECONDS",
    "ENABLED_ENV_VAR",
    "DRY_RUN_ENV_VAR",
    "FRAME_SPECS",
    "MAX_DELTA_PER_CYCLE_ENV_VAR",
    "METRIC_DELTA_CEILING_TRIPPED",
    "METRIC_ERRORS",
    "METRIC_EVALUATION_REFUSED",
    "METRIC_GUID_NULL_IN_SCOPE",
    "METRIC_INTENT_DELTA",
    "METRIC_INVALID_PHONE",
    "METRIC_IN_SCOPE_OFFICES",
    "METRIC_LAST_RUN_EPOCH",
    "METRIC_NAMESPACE",
    "METRIC_NOOP_OFFICES",
    "METRIC_NOT_CONFIGURED_OFFICES",
    "METRIC_PREREQ_REFUSED",
    "METRIC_ROSTER_ONLY_PHONES",
    "METRIC_STATUS_DRIFT",
    "METRIC_UNRESOLVED_OFFICES",
    "METRIC_WRITES_APPLIED",
    "METRIC_WRITE_DENIED",
    "MIN_INSCOPE_PHONES_ENV_VAR",
    "CycleResult",
    "LoadedFrames",
    "emit_cycle",
    "emit_heartbeat",
    "emit_office_line",
    "emit_refused",
    "handler",
    "run_enrollment_bridge",
]
