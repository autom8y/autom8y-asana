"""Lambda handler: scheduling-stratum WHOLE-SNAPSHOT push (I2, DEFAULT-DARK).

The FORK-2 (c2) periodic full-snapshot trigger for the scheduling-posture substrate.
It re-pushes the FULL active-office set so the data side's whole-source DELETE
continually reconciles the projection against Asana (the surviving source-reconcile
that lets the 019 reconcile module dissolve). Mirrors the established
scheduled-entrypoint pattern (``cache_warmer`` client/cache setup +
``onboarding_walkthrough`` DARK-gate short-circuit), driving the pure
``resolve_and_push_snapshot`` pipeline.

FRAME-FIRST (FORK-1 A∘D, warm-projection). The office posture is projected in ONE
pure Polars pass over ALREADY-WARMED frames (:func:`project_office_frame` via the
pure ``map_frame_row_to_inputs``): sub-second, ZERO per-office Asana reads (the
measured 900s-Lambda-ceiling blocker is dissolved -- TDD-DELTA 2026-07-02).

OFFICE SPINE (WS-B re-source, DIAG-ws-b-offer-frame-collapse-2026-08-05). The source
is the ``unit_holder x business`` join, NOT the offer frame. The offer frame sources
both the office guid and the nine posture columns ``cascade:`` through a FRAME-LESS
OfferHolder tier, and the ancestor-hydration walk that must deliver them terminates
at depth 1 (``warm_ancestors_completed {total_warmed: 0, final_depth: 1}``) -- so
hops 3 (UnitHolder) and 4 (Business) are never visited and those columns are
STRUCTURALLY unreachable there (measured: company_id 2/4191, the eight provider
columns 0/4191). ``office_phone`` survived only because it is locally stamped on the
Offer task itself. The producer therefore reads the two frames that NATIVELY own the
data -- UnitHolder (posture, cf: on its own manifest) and Business (the guid) --
joined on ``unit_holder.parent_gid -> business.gid``, measured 2082/2082 = 100.0%.
Zero ancestor traversal, zero new Asana reads.

EXPLICIT COMPLETENESS CONTRACT (the load-bearing safety):

    UNIVERSE (LOCKED): the posture universe is the set of DISTINCT NON-NULL
    ``company_id`` guids in the joined office spine (~921 today, vs a ``prior_count``
    of 949 -- shrink ratio 0.030, inside the data side's 0.500 guard). guid-less rows
    DROP and fail SAFE to GHL by absence (the honest posture). Multi-unit_holder-
    per-guid collapses to ONE deterministic representative (max ``last_modified``)
    supplying enrollment status AND destination JOINTLY; a per-guid
    ``custom_cal_status`` disagreement is metered as drift. Note the universe is the
    OFFICE SPINE (all offices, including de-enrolled ones, which is what preserves
    the wire-v2 ``enrolled=false stays present`` invariant) -- NOT an active-offer
    scoping, which would be 57 guids and correctly refused by the shrink guard.

    This entry point projects the FULL spine, NEVER a completed-entities partial. A
    partial batch fed to the data side's whole-source DELETE (``snapshot_replace``)
    would mass-wipe live enrolled offices -- strictly worse than a stale snapshot.
    :func:`assert_complete_office_set` REFUSES the push when the office set cannot be
    proven complete (EITHER spine frame unreadable/absent, or an empty deduped guid
    set): it returns a ``refused`` outcome and pushes NOTHING.

    SCHEMA-LAG: the SWR cache serves stale-while-revalidate, so a read may serve a
    unit_holder frame predating UNIT_HOLDER_SCHEMA (base columns only). This is
    detected (:func:`join_office_spine`) and REFUSED honestly -- never fabricated or
    default-filled. It is also the PR-1-before-PR-2 safety: shipping this re-source
    against a base-columns-only unit_holder frame yields honest refusals, not a
    degenerate push. The refusal's triggered refresh converges the frame; a
    subsequent run succeeds.

    VALUE-FLOOR: the columns may be PRESENT (schema-lag passes) yet their CONTENT
    degenerate -- every posture column resolved null (the 1.5.0 wrong-level / wrong-name
    cascade defect: 0/545 offices carried any signal, but company_id resolved so the SET
    gate passed). :func:`assert_posture_signal_floor` REFUSES a universe that carries a
    posture signal on FEWER than :data:`MIN_POSTURE_SIGNAL_ROWS` offices, so an all-empty
    projection never whole-source-overwrites live posture with empties.

    Contrast ``push_orchestrator._push_*_for_completed_entities``, which operate over
    ``completed_entities`` (a PARTIAL set) -- that shape MUST NOT be used here.

DEFAULT-DARK. The whole mechanism is inert until the operator flips
``SCHEDULING_STRATUM_PUSH_ENABLED`` (DEFAULT-OFF): with the gate off the handler
short-circuits to ``skipped`` BEFORE any substrate construction or Asana read (the
gate governs BOTH this handler's execution AND, downstream, the live POST in
``push_stratum_snapshot``).

Cadence: LOW-frequency by design (hours -- NOT the paused 429-wounded <=10-min
section lane, ``config.py`` SECTION recalibration). :data:`DEFAULT_SNAPSHOT_CADENCE_HOURS`
is the intended cadence; the actual EventBridge schedule + per-function Lambda CMD
override live in EXTERNAL deploy infra (this repo carries no IaC for it) -- a
RELEASER-SEAM item, not authored here.

Environment Variables:
    SCHEDULING_STRATUM_PUSH_ENABLED: DEFAULT-OFF activation gate (this handler +
        the live POST). UNSET => DARK no-op.
    ASANA_PAT / ASANA_WORKSPACE_GID: Asana credentials (bot PAT path).
    AUTOM8Y_DATA_URL: data-service base URL for the sync POST.
    SERVICE_CLIENT_ID / SERVICE_CLIENT_SECRET: the current-generation S2S
        client-credentials pair. On the LIVE push path the handler exchanges them
        for a genuine service JWT (:class:`ServiceTokenAuthProvider`, mirroring
        ``workflow_handler``) and injects it as the push ``auth_token`` -- NOT the
        legacy ``AUTOM8Y_DATA_API_KEY`` fossil (an 11-char single-segment stub the
        data side rejects with 401 AUTH-TEB-003 "Token is malformed").
    SCHEDULING_STRATUM_SNAPSHOT_CADENCE_HOURS: intended cadence (releaser-seam doc).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, NamedTuple

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric
from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    REQUIRED_FRAME_COLUMNS,
    FrameSchemaLagError,
    map_frame_row_to_inputs,
    missing_frame_columns,
)
from autom8_asana.services.scheduling_stratum_push import (
    _is_stratum_push_enabled,
    resolve_and_push_snapshot,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import polars as pl

    from autom8_asana.normalizer.scheduling_extractor import ExtractedScheduling
    from autom8_asana.services.scheduling_stratum_push import StratumPushResult

logger = get_logger(__name__)

#: The OFFICE SPINE (WS-B): the two warmed frames whose join is the full office
#: source. ``unit_holder`` natively holds the nine scheduling-posture fields
#: (schema 1.0.0, cf: off its own manifest); ``business`` natively holds the office
#: guid (``company_id``, cf:Company ID). They join on
#: ``unit_holder.parent_gid -> business.gid`` -- measured 2082/2082 = 100.0%
#: complete on today's frames.
#:
#: This REPLACES the offer frame as the producer's source. The offer frame sources
#: BOTH the guid and the posture ``cascade:`` through a frame-less OfferHolder tier,
#: and the ancestor walk that must deliver them terminates at depth 1, so those
#: columns are structurally unreachable there (company_id 2/4191, the eight provider
#: columns 0/4191). See DIAG-ws-b-offer-frame-collapse-2026-08-05.
SNAPSHOT_UNIT_HOLDER_ENTITY_TYPE = "unit_holder"
SNAPSHOT_BUSINESS_ENTITY_TYPE = "business"

#: The join key on the unit_holder side (rides BASE_COLUMNS); joins to business.gid.
OFFICE_SPINE_JOIN_KEY = "parent_gid"

#: Intended cadence (hours) for the releaser-seam EventBridge rule.
#: NOT enforced by the handler (EventBridge owns scheduling); surfaced here so the
#: infra wiring has a single documented default.
#:
#: C2 CADENCE/TTL MARGIN (2026-08-06). Was 6. The data side serves a posture only
#: while ``synced_at`` is inside the 8h TTL (autom8y-data scheduling_posture.py
#: ``_DEFAULT_TTL_SECONDS = 8 * 3600``; the deployed ECS taskdef carries no
#: ``SCHEDULING_STRATUM_TTL_SECONDS`` override). At a 6h cadence a push at T expires
#: at T+8h and the NEXT tick is T+6h -- so a SINGLE missed tick puts the following
#: attempt at T+12h, four hours PAST the cliff, flipping all ~921 offices to
#: ``fallback_ghl`` simultaneously. Missed-tick margin at 6h is ZERO.
#:
#: At 2h the ticks inside one TTL window are T+2 / T+4 / T+6: TWO consecutive ticks
#: may fail before the substrate can go fossil. The cost is paid on the cheap axis --
#: the producer is FRAME-FIRST (it reads already-warmed frames from the dataframe
#: cache and issues ZERO per-office Asana reads), so raising the cadence adds NO
#: Asana REST load; it adds two extra whole-source replaces per day on a 921-row
#: table. Widening the TTL instead was REJECTED: the TTL is the serve-side staleness
#: FUSE, and buying schedule margin by letting the substrate serve staler posture
#: pays for producer unreliability with client-facing correctness.
DEFAULT_SNAPSHOT_CADENCE_HOURS = 2

#: Env override for the documented cadence (consumed by the releaser-seam infra).
SNAPSHOT_CADENCE_HOURS_ENV_VAR = "SCHEDULING_STRATUM_SNAPSHOT_CADENCE_HOURS"

#: Env override for the VALUE-FLOOR threshold (operator ratchet -- no deploy needed).
#: Mirrors the data side's ``SCHEDULING_STRATUM_MAX_SHRINK_RATIO`` idiom.
MIN_POSTURE_SIGNAL_ROWS_ENV_VAR = "SCHEDULING_STRATUM_MIN_POSTURE_SIGNAL_ROWS"

#: Stage-1 DERIVED default for the value floor (C5). See :data:`MIN_POSTURE_SIGNAL_ROWS`.
_DEFAULT_MIN_POSTURE_SIGNAL_ROWS = 100


def _resolve_min_posture_signal_rows() -> int:
    """Resolve the value-floor threshold (env-overridable; fail-safe to the default).

    Read ONCE at import (Lambda env is fixed for a container's life). A malformed or
    negative override degrades to the derived default rather than silently disabling
    the floor -- an override of 0 would restore exactly the blindness C5 exists to cure.
    """
    raw = os.environ.get(MIN_POSTURE_SIGNAL_ROWS_ENV_VAR)
    if raw is None:
        return _DEFAULT_MIN_POSTURE_SIGNAL_ROWS
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_MIN_POSTURE_SIGNAL_ROWS
    return parsed if parsed >= 1 else _DEFAULT_MIN_POSTURE_SIGNAL_ROWS


#: VALUE-FLOOR guard threshold (the degenerate-source completeness teeth). A healthy
#: whole-source snapshot MUST carry a scheduling-posture SIGNAL on at least this many
#: offices in the universe. The 1.5.0 defect (cascade/cf sources at the WRONG level or
#: WRONG name) resolved EVERY posture column null, so 0/545 pushed offices carried any
#: signal -- yet company_id resolved fine, so the completeness gate passed and a
#: degenerate whole-source push overwrote live posture with empties. A legitimate
#: fleet -- even an all-GHL one that leaves the eight alt-providers null -- still
#: carries a non-null custom_cal_status (the office-global binary enrollment enum) on
#: every enrolled office, so a real universe never floors to zero.
#:
#: C5 RAISED 1 -> 100 (2026-08-06). A floor of 1 was minted when the universe was
#: tens of offices; it is now evaluated over a 921-office population (own-hands:
#: three consecutive ticks 2026-08-05T18:00Z / 08-06T00:00Z / 06:00Z each logged
#: ``distinct_guids: 921``), i.e. a floor of 1/921 -- 920 offices could resolve to
#: an all-null posture and the guard would still admit the whole-source overwrite.
#: The DIAG's own Leg-A recommendation ("assert a floor materially above 1, e.g.
#: >= 100") was never implemented; 100 IMPLEMENTS IT VERBATIM.
#:
#: Why 100 is the STAGE-1 value and not a tighter one: nothing in the fleet has ever
#: MEASURED the live signal-bearing row count -- the guard only ever answered the
#: boolean ">= 1", so the honest ceiling on a same-deploy derivation is what the
#: instrument can prove. This change ships that instrument
#: (:data:`METRIC_POSTURE_SIGNAL_ROWS`) alongside the floor. 100 is safe by
#: construction against every observation in hand: it is 100x the prior floor, >2x
#: the ENTIRE pre-WS-B era's maximum universe (max ``office_count`` 44 across the
#: 18 ``pushed=false`` ticks of 2026-07-22..08-05), and carries ~5x downside headroom
#: against the ~540 signal-bearing representatives the WS-B DIAG observed.
#:
#: STAGE-2 RATCHET (operator, no deploy): after >= 2 live ticks of
#: ``SchedulingStratumPostureSignalRows``, set
#: ``SCHEDULING_STRATUM_MIN_POSTURE_SIGNAL_ROWS`` to ~0.5x the observed value.
MIN_POSTURE_SIGNAL_ROWS = _resolve_min_posture_signal_rows()

#: The posture-signal columns the value floor inspects: custom_cal_status + the eight
#: CASCADE_PRIORITY providers (i.e. every REQUIRED_FRAME_COLUMN except the identity
#: guid). Derived from REQUIRED_FRAME_COLUMNS so it stays in lockstep with the schema.
_POSTURE_SIGNAL_COLUMNS: tuple[str, ...] = tuple(
    c for c in REQUIRED_FRAME_COLUMNS if c != GUID_FIELD
)

# ==============================================================================
# ★ CROSS-REPO EMIT->ALARM CONTRACT (byte-exact; the ONLY thing binding the pair)
# ==============================================================================
# COUNTERPART ALARMS (autom8y repo):
#   terraform/services/asana/scheduling_stratum_producer_alarms.tf
# The two halves live in DIFFERENT repos; the ONLY thing binding them is a
# byte-exact match on {namespace + metric name + dimension}. A rename/typo on
# EITHER side yields an alarm watching a metric nobody emits -- GREEN on both
# halves, DEAD as a pair. autom8y's tests/test_scheduling_stratum_producer_alarms_
# terraform.py pins these literals against the terraform, so a rename trips CI,
# not production. (Same discipline as the R7 divergence tripwire pair.)
#
# ★ NAMESPACE: these ride the house default ``autom8/lambda`` (ASANA_CW_NAMESPACE).
# ★ DIMENSION: emit_metric() stamps ``environment=<ASANA_CW_ENVIRONMENT>`` on EVERY
#   metric. Until 2026-08-06 the production Lambda carried NO ASANA_CW_ENVIRONMENT,
#   so it stamped the ObservabilitySettings default "staging" -- a PRODUCTION
#   producer publishing into a staging dimension. The paired terraform change sets
#   ASANA_CW_ENVIRONMENT = var.environment on the function; without it every alarm
#   below binds a dimension-series nobody emits into.
#
# ★ NO HIGH-CARDINALITY DIMENSIONS. The pre-existing
#   ``SchedulingStratumSnapshotPushed`` / ``...DryRun`` emissions stamp
#   ``office_count=<N>`` as a DIMENSION, so every tick lands on a DIFFERENT metric
#   series (live `cloudwatch list-metrics` on 2026-08-06 shows 12 distinct
#   ...DryRun series, one per office_count value). Such a series is STRUCTURALLY
#   unalarmable: an alarm must pin the dimension, and the pinned value goes
#   INSUFFICIENT_DATA the moment the count moves by one. That is why the outage
#   below was invisible AT THE METRIC LAYER even though the signal existed in the
#   log. Every metric in this contract is emitted with NO dimensions beyond the
#   environment stamp, and carries its payload in the VALUE.
#
# ★ EVERY TERMINAL PATH PUBLISHES (D-1, 2026-08-06). A chaos experiment proved the
#   push-failure metric covers only the REACHED-PUSH arm: over the real darkness
#   window 2026-07-06..2026-08-01 there were 94 ``..._refused`` ticks (verbatim
#   unvarying reason "empty active-office set (refusing an empty whole-source
#   push)") against 8 ``..._complete`` ticks with pushed=false -- and the refusal arm
#   RETURNS upstream of that metric. With the alarm on treat_missing_data=
#   notBreaching, absence read as OK through 92% of the outage it was named for.
#   The cure is structural, not a widened threshold: the refusal and skip emissions
#   lost their ``reason`` DIMENSION (dimension matching is EXACT -- a
#   ``{environment, reason}`` series is unreadable by an ``{environment}`` alarm,
#   the same trap ``office_count`` sprang), and ``...Refused`` / ``...SchemaLag``
#   joined ALARM_BOUND_METRICS. The reason string still rides the log line, which is
#   where a high-cardinality value belongs.
#
# ★ DELIBERATE ACTIONS ARE NOT FAULTS (D-2, 2026-08-06). A forced dry-run
#   (``event["dry_run"]``, an explicitly supported operation) used to publish
#   ``PushFailed=1`` -- byte-identical at the metric layer to a real outage, and two
#   inside consecutive 2h windows would page SEV-1 to a live SMS subscriber for a
#   non-incident. Shadow runs now publish ``...ShadowRun`` and NOTHING on the failure
#   series. Their substrate-staleness cost is deliberately UNCHANGED: they do not
#   deliver, so ``...PushEpoch`` stays absent and the freshness dead-man keeps
#   counting toward the 8h TTL cliff.
# ==============================================================================

#: Heartbeat emitted on EVERY invocation (skipped / refused / dry-run / pushed /
#: error) as the current epoch. LIVENESS deadman input: a PRESENT datapoint is
#: never < 1, so a value-comparison never trips and ONLY MISSING data breaches.
METRIC_RUN_EPOCH = "SchedulingStratumSnapshotRunEpoch"

#: Heartbeat emitted ONLY when the data-service POST returned OK (``pushed=true``),
#: as the current epoch. SUBSTRATE-FRESHNESS deadman input: a successful push is
#: what re-stamps ``synced_at`` on all ~921 rows, so ABSENCE of this datapoint for
#: longer than the data side's TTL is exactly "the substrate is about to go fossil
#: and every office will flip to fallback_ghl". This is the metric whose absence
#: would have been RED for the whole 2026-07-22..08-05 darkness.
METRIC_PUSH_EPOCH = "SchedulingStratumSnapshotPushEpoch"

#: 1 when a run REACHED THE PUSH and genuinely failed to deliver, 0 when it
#: delivered. THE SILENT-CLEAN FAILURE: the producer logs {"pushed": false} and
#: exits 0, so AWS/Lambda Errors stays 0 and the DLQ stays empty.
#:
#: ★ SCOPE (D-1, corrected 2026-08-06). This metric is emitted ONLY on the
#: reached-push arm. The ``refused`` and ``skipped`` arms ``return`` upstream of it,
#: so it is BLIND to them BY CONSTRUCTION -- and its alarm is
#: treat_missing_data=notBreaching, so that blindness reads as OK. Measured over the
#: real darkness window 2026-07-06..2026-08-01: 94 refusals vs 8 reached-push
#: non-deliveries, i.e. this metric covers 8% of the outage it is named for. The
#: refusal arm is covered by :data:`METRIC_REFUSED` (and its sub-class markers);
#: total absence is the two dead-men's remit. Do NOT widen this metric to cover the
#: refusal arm -- an alarm whose scope drifts from its name is how the blindness was
#: minted. Keep each terminal path on its own honest series.
#:
#: ★ NOT emitted on a deliberate shadow run (D-2). See :data:`METRIC_SHADOW_RUN`.
METRIC_PUSH_FAILED = "SchedulingStratumSnapshotPushFailed"

#: 1 on EVERY refusal terminal path -- the union of every reason
#: :class:`SnapshotRefusedError` can carry (empty/incomplete office set, schema lag,
#: degenerate source, and any refusal class added later).
#:
#: ★ D-1 THE 92% PATH. Emitted with NO DIMENSIONS. It previously carried
#: ``dimensions={"reason": ...}``, and CloudWatch dimension matching is EXACT: an
#: alarm pinning ``{environment}`` alone can never read a ``{environment, reason}``
#: series, so the signal existed and was STRUCTURALLY unalarmable -- the same trap
#: ``office_count`` sprang on ...Pushed/...DryRun. The reason still rides the
#: ``scheduling_stratum_snapshot_refused`` log line verbatim, which is where a
#: high-cardinality string belongs.
#:
#: This is the UNION leg deliberately: :data:`METRIC_SCHEMA_LAG` and
#: ``SchedulingStratumSnapshotDegenerateSource`` are SUB-CLASS discriminators that
#: tell an operator WHICH refusal without a log dive, but a future refusal class
#: would be silent if only the sub-classes were bound. The union closes the class.
METRIC_REFUSED = "SchedulingStratumSnapshotRefused"

#: 1 when the DARK gate short-circuited the run. Emitted with NO DIMENSIONS for the
#: same structural reason as :data:`METRIC_REFUSED` (it previously carried
#: ``reason=gate_off``), so it is BINDABLE -- but NO alarm binds it, deliberately:
#: a dark gate is an operator STATE, not a fault, and paging for it is exactly the
#: deliberate-action-looks-like-a-failure conflation D-2 cures. A gate left off by
#: accident is caught by the substrate-freshness dead-man within ~7h.
METRIC_SKIPPED = "SchedulingStratumSnapshotSkipped"

#: 1 when a refusal was caused by SCHEMA LAG (the warmed frame predates the posture
#: schema). Already dimension-free; it simply had no alarm bound to it -- an
#: instrument that exists and watches nothing. Bound as of D-1.
METRIC_SCHEMA_LAG = "SchedulingStratumSnapshotSchemaLag"

#: 1 when the run was a DELIBERATE operator shadow run (``event["dry_run"]`` forced).
#:
#: ★ D-2. Observed live 2026-08-06T09:05:15Z (RequestId
#: 8fde3ea0-0436-4492-b2cc-031368bf904e): a forced dry-run published
#: ``PushFailed=1`` and suppressed ``PushEpoch`` -- byte-identical at the metric
#: layer to a real delivery failure. Once actions are armed, two shadow runs inside
#: consecutive 2h windows would page SEV-1 (live SMS subscriber) for a non-incident.
#: A shadow run now publishes THIS marker and NOTHING on the failure series.
#:
#: ★ DELIBERATELY UNBOUND, and the substrate-staleness axis is deliberately
#: UNCHANGED: a shadow run does not deliver, so it ages the substrate toward the 8h
#: TTL cliff exactly like any other non-delivery and ``PushEpoch`` stays absent.
#: Curing D-2 by fabricating a heartbeat would trade a false page for a fossil
#: substrate served silently -- a strictly worse bargain.
METRIC_SHADOW_RUN = "SchedulingStratumSnapshotShadowRun"

#: Count of universe rows carrying ANY scheduling-posture signal -- the VALUE-FLOOR's
#: own numerator, made observable. The floor has only ever answered the boolean
#: ">= MIN_POSTURE_SIGNAL_ROWS"; nothing ever published the number it compared.
METRIC_POSTURE_SIGNAL_ROWS = "SchedulingStratumPostureSignalRows"

#: The universe height the floor divides into -- the denominator half of the pair.
METRIC_POSTURE_UNIVERSE_ROWS = "SchedulingStratumPostureUniverseRows"

#: Metrics an autom8y CloudWatch alarm is BOUND to. Renaming any of these without
#: the matching terraform edit silently decouples the pair. The autom8y-side test
#: asserts this frozenset equals the set of metric_names in the alarm file.
#: ``SchedulingStratumUniverseCensus`` and ``SchedulingStratumSnapshotDegenerateSource``
#: are PRE-EXISTING emissions (unchanged here) that the alarm half binds.
#:
#: ★ :data:`METRIC_SHADOW_RUN` and :data:`METRIC_SKIPPED` are intentionally ABSENT:
#: both mark deliberate operator states, and an alarm on a deliberate state is the
#: false-page shape. They are dimension-free so they remain bindable if that
#: judgement ever changes.
ALARM_BOUND_METRICS: frozenset[str] = frozenset(
    {
        METRIC_RUN_EPOCH,
        METRIC_PUSH_EPOCH,
        METRIC_PUSH_FAILED,
        METRIC_REFUSED,
        METRIC_SCHEMA_LAG,
        "SchedulingStratumUniverseCensus",
        "SchedulingStratumSnapshotDegenerateSource",
    }
)

#: ★ L2 — THE SOURCE-HEALTH COMPANION SET. The three FIRE-ONLY series.
#:
#: These three publish 1 on their fault path and, before this change, published
#: NOTHING otherwise. Their alarms are ``GreaterThanThreshold(0)`` with
#: ``treat_missing_data=notBreaching``, so on every healthy tick the alarm saw NO
#: DATA and sat in OK *by the missing-data rule* -- not because anything measured
#: health. That OK is BLIND: it is indistinguishable from an OK produced by a dead
#: emitter, a renamed metric, a wrong-dimension emission, or a lost IAM permission.
#: Live on 2026-08-10 none of the three had EVER published a datapoint on the
#: ``{environment=production}`` series its alarm binds.
#:
#: ★ THE TEMPLATE IS :data:`METRIC_PUSH_FAILED`, which has always published a real
#: ``0`` on every delivering tick (``0 if pushed else 1``, ONE call site, ONE
#: emission per tick). That is exactly why its OK is VALUE-DRIVEN: the alarm is
#: reading a measured "no failure", not an absence. Live receipt: 13 consecutive
#: real-0 datapoints at the 2h cadence over 2026-08-09T21:56Z..2026-08-10T21:56Z.
#: These three now do the same thing on the same dimension set.
#:
#: ★ MUTUAL EXCLUSION IS STRUCTURAL, not a convention. Every 1-emission for these
#: three sits on a path that RAISES :class:`SnapshotRefusedError`; the companion 0
#: is published in :func:`execute_snapshot_push` only on the path where that raise
#: did NOT happen -- the two live on opposite sides of one try/except boundary in
#: one function. A tick can therefore never publish both a 0 and a 1 on the same
#: series, and the 0 can never mask a firing.
#:
#: ★ SPELLING. Names are the alarm seam (CloudWatch matching is EXACT), so every
#: member is asserted to be in :data:`ALARM_BOUND_METRICS` at import time below.
SOURCE_HEALTH_COMPANION_METRICS: tuple[str, ...] = (
    "SchedulingStratumSnapshotDegenerateSource",
    METRIC_REFUSED,
    METRIC_SCHEMA_LAG,
)

# Import-time seam guard: a companion published on a name no alarm binds is a
# metric nobody reads, and a companion MISSING from the alarm set means an alarm
# was retired without retiring its companion. Either way the pair has decoupled.
assert set(SOURCE_HEALTH_COMPANION_METRICS) <= ALARM_BOUND_METRICS, (
    "SOURCE_HEALTH_COMPANION_METRICS carries a name no alarm binds: "
    f"{sorted(set(SOURCE_HEALTH_COMPANION_METRICS) - ALARM_BOUND_METRICS)}"
)


def _emit_source_health_companions() -> None:
    """Publish a REAL 0 on each fire-only source-health series (L2).

    Called from ONE place: :func:`execute_snapshot_push`, on the path where the
    source guards RAN and did NOT refuse. The claim each 0 makes is therefore
    exactly true and narrowly scoped: *this tick evaluated the source and found no
    refusal, no schema lag, and no degenerate posture*.

    ★ DIMENSION-FREE (D-1). ``emit_metric`` stamps ``environment=<ASANA_CW_ENVIRONMENT>``
    and nothing else, which is the EXACT single-dimension set every alarm binds
    (``dimensions = {environment = var.environment}`` in
    terraform/services/asana/scheduling_stratum_producer_alarms.tf). Passing a
    ``dimensions=`` kwarg here would fork these onto a ``{environment, reason}``-shaped
    series no alarm can match -- the ORIGINAL scar this whole package cures. Do not
    add one.

    ★ WHAT THIS DOES NOT DO. A 0 makes the OK VALUE-DRIVEN; it does not prove the
    alarm can go RED. The RED legs are owed to the operator-attended injection
    experiment (CARD-RUL19-INJECTION), because driving any of these to ALARM pages
    a live SEV-1 SMS subscriber.
    """
    for metric_name in SOURCE_HEALTH_COMPANION_METRICS:
        emit_metric(metric_name, 0)


def _now_epoch() -> int:
    """Current UTC epoch seconds (the deadman heartbeat payload)."""
    from datetime import UTC, datetime

    return int(datetime.now(UTC).timestamp())


class SnapshotRefusedError(Exception):
    """The office set could not be proven complete -- refuse to push a partial.

    Raised by :func:`assert_complete_office_set`. The caller converts it to a
    ``refused`` outcome and pushes NOTHING (the completeness-contract safety).
    """


class SnapshotRunResult(NamedTuple):
    """Outcome of a snapshot-push run (handler + tests read this)."""

    status: str  # skipped | refused | dry_run | pushed | error
    reason: str | None
    entry_count: int


def assert_complete_office_set(
    office_gids: list[str] | None,
    *,
    source_complete: bool,
) -> list[str]:
    """COMPLETENESS-CONTRACT gate: return the FULL active-office gid set or REFUSE.

    The whole-snapshot push feeds the data side's whole-source DELETE, so the batch
    MUST be the complete active-office set. This gate REFUSES (raises
    :class:`SnapshotRefusedError`) when completeness cannot be proven:

      * ``source_complete is False`` -- the office source could not be read as a full
        snapshot (absent/unreadable offer frame, unresolved project). Pushing what we
        have would be a PARTIAL -> mass-wipe.
      * empty ``office_gids`` -- an empty batch fed to the whole-source DELETE wipes
        every live office. A genuinely-empty fleet is indistinguishable from a broken
        read here, so it is REFUSED (fail-safe) rather than pushed.

    Returns the gid set (duplicates removed, order preserved) on success.
    """
    if not source_complete:
        raise SnapshotRefusedError("office source could not be read as a complete snapshot")
    if not office_gids:
        raise SnapshotRefusedError("empty active-office set (refusing an empty whole-source push)")
    # De-dup preserving first-seen order (defensive: the whole-source push must not
    # carry duplicate office gids into the entry_count integrity witness).
    seen: set[str] = set()
    unique: list[str] = []
    for gid in office_gids:
        if gid and gid not in seen:
            seen.add(gid)
            unique.append(gid)
    if not unique:
        raise SnapshotRefusedError("active-office set contained no usable gids")
    return unique


async def execute_snapshot_push(
    *,
    gate: Callable[[], bool],
    enumerate_offices: Callable[[], Awaitable[tuple[list[ExtractedScheduling], bool]]],
    push: Callable[[list[ExtractedScheduling]], Awaitable[StratumPushResult | None]],
    shadow_run: bool = False,
) -> SnapshotRunResult:
    """Orchestrate one whole-snapshot push under the DARK gate + completeness contract.

    Injectable core (no live substrate) so the gate / completeness / push decisions
    are unit-testable. When ``gate()`` is falsy the enumeration is NEVER invoked -- no
    substrate construction, no Asana read (the DEFAULT-DARK guarantee).

    ``enumerate_offices`` returns the frame-projected offices (one per distinct guid)
    plus ``source_complete``. It may raise :class:`SnapshotRefusedError` directly on
    SCHEMA-LAG (a pre-1.5.0 frame). :func:`assert_complete_office_set` gates the guid
    set (REFUSE on incomplete source OR empty). Both refusal paths converge on the
    ``refused`` outcome (byte-compatible with the gid-based predecessor).

    ★ EVERY TERMINAL PATH PUBLISHES (D-1). ``skipped`` / ``refused`` / ``shadow`` /
    non-delivery / delivery each emit a dimension-free marker, so the ABSENCE of a
    signal never has to be interpreted as health. The refusal and skip arms ``return``
    upstream of the push emissions, which is exactly why the push-failure metric alone
    covered only 8% of the historical outage.

    ★ EVERY NON-REFUSING TICK ALSO PUBLISHES A REAL 0 (L2) on each of the three
    fire-only source-health series via :func:`_emit_source_health_companions`, so
    their alarms' OK becomes VALUE-DRIVEN instead of OK-by-missing-data. The
    ``skipped`` arm is deliberately EXCLUDED: a dark gate never enumerates, so it
    never evaluated the source, and a 0 there would assert a verdict nobody reached
    -- the same over-claim D-2 refused when it declined to publish ``PushFailed=0``
    on a shadow run.

    Args:
        shadow_run: True when the OPERATOR deliberately forced a dry run via
            ``event["dry_run"]`` (D-2). A shadow run is not a delivery failure: it
            publishes :data:`METRIC_SHADOW_RUN` and NOTHING on
            :data:`METRIC_PUSH_FAILED`. It still delivers nothing, so
            :data:`METRIC_PUSH_EPOCH` stays absent and the substrate-freshness
            dead-man keeps counting -- deliberately.
    """
    if not gate():
        logger.info("scheduling_stratum_snapshot_skipped", extra={"reason": "gate_off"})
        # D-1: dimension-free. The reason rides the log line above; a `reason`
        # DIMENSION puts the datapoint on a series no {environment}-pinned alarm can
        # match, which is how a present signal becomes an unalarmable one.
        emit_metric(METRIC_SKIPPED, 1)
        return SnapshotRunResult(status="skipped", reason="gate_off", entry_count=0)

    try:
        extracted, source_complete = await enumerate_offices()
        # The completeness gate operates on the guid set (LOCKED semantics: REFUSE on
        # !source_complete OR empty deduped guid set). The offices are already
        # guid-deduped by the frame projection; assert_complete_office_set is the
        # unchanged safety teeth (it never weakens -- only refuses).
        assert_complete_office_set([o.guid for o in extracted], source_complete=source_complete)
    except SnapshotRefusedError as exc:
        logger.warning("scheduling_stratum_snapshot_refused", extra={"reason": str(exc)})
        # ★ D-1 THE 92% PATH, made alarmable. 94 of the 102 terminal ticks over
        # 2026-07-06..2026-08-01 landed HERE, every one of them logging the verbatim
        # reason "empty active-office set (refusing an empty whole-source push)" --
        # and returning before the push-failure emission below. The metric was emitted
        # with dimensions={"reason": "incomplete_office_set"}, which forks it onto a
        # series no alarm binding {environment} can read. Dimension-free now, and
        # BOUND on the autom8y side (asana-stratum-push-refused).
        emit_metric(METRIC_REFUSED, 1)
        return SnapshotRunResult(status="refused", reason=str(exc), entry_count=0)

    # ★ L2 THE COMPANION 0s. Reached ONLY when the enumeration and the completeness
    # gate both ran to completion without raising -- i.e. no refusal of ANY class
    # occurred on this tick. Every 1-emission for these three series is upstream of
    # (or inside) the try above and raises, so the `except` arm returns before this
    # line: a 0 and a 1 on the same series in the same tick is structurally
    # impossible, and a firing can never be masked.
    #
    # Placed BEFORE the push deliberately. These three measure SOURCE health, not
    # DELIVERY health -- the source was evaluated and found sound whether or not the
    # subsequent POST succeeds. Publishing after the push would suppress the 0 on a
    # tick whose push raised, re-introducing missing-data blindness on exactly the
    # ticks an operator most needs the source verdict for. Delivery has its own
    # honest series (PushFailed / PushEpoch) and they are untouched here.
    _emit_source_health_companions()

    result = await push(extracted)
    entry_count = result.entry_count if result is not None else 0
    pushed = bool(result is not None and result.pushed)
    logger.info(
        "scheduling_stratum_snapshot_complete",
        extra={
            "office_count": len(extracted),
            "entry_count": entry_count,
            "pushed": pushed,
            "shadow_run": shadow_run,
        },
    )
    emit_metric(
        "SchedulingStratumSnapshotPushed" if pushed else "SchedulingStratumSnapshotDryRun",
        1,
        dimensions={"office_count": str(len(extracted))},
    )
    # C1(b) THE SILENT-CLEAN FAILURE, made alarmable. The line above is RETAINED
    # (dashboards/queries depend on it) but is unalarmable by construction: its
    # office_count DIMENSION forks a new metric series on every tick. These carry the
    # same fact with NO high-cardinality dimension, so an alarm can actually bind
    # them. PushFailed publishes a real 0 on delivery, so the alarm distinguishes
    # "delivered" from "ran and delivered nothing"; PushEpoch is emitted ONLY on
    # delivery, so its ABSENCE is the substrate-freshness signal.
    #
    # ★ D-2. A DELIBERATE shadow run reaches here with pushed=False and is NOT a
    # failure. It publishes the shadow marker and NOTHING on the failure series --
    # not even a 0, which would assert a delivery that did not happen. Observed live
    # 2026-08-06T09:05:15Z: a forced dry-run emitted PushFailed=1, byte-identical to a
    # real outage; two of those inside consecutive 2h windows page SEV-1 to a live SMS
    # subscriber for a non-incident.
    if shadow_run:
        emit_metric(METRIC_SHADOW_RUN, 1)
    else:
        emit_metric(METRIC_PUSH_FAILED, 0 if pushed else 1)
    # Unconditional on delivery (never inside the shadow branch): the freshness
    # heartbeat tracks what was actually DELIVERED, and a shadow run delivers
    # nothing, so it correctly ages the substrate toward the 8h TTL cliff.
    if pushed:
        emit_metric(METRIC_PUSH_EPOCH, _now_epoch())
    return SnapshotRunResult(
        status="pushed" if pushed else "dry_run",
        reason=None,
        entry_count=entry_count,
    )


def project_posture_rows(df: pl.DataFrame) -> tuple[list[ExtractedScheduling], list[str]]:
    """PURE frame projection: dedup rows by office guid + project posture.

    ENTITY-AGNOSTIC (WS-B). This is the unchanged universe / representative / drift
    core, formerly ``project_offer_frame``. It consumes ANY frame carrying
    :data:`REQUIRED_FRAME_COLUMNS` plus ``gid`` / ``last_modified``; WS-B re-sourced
    the producer to feed it the ``unit_holder x business`` join
    (:func:`project_office_frame`) instead of the offer frame, which is a SOURCE
    change, not a contract change. The rules below are byte-identical to the
    offer-frame era -- they are the reason 949 live office postures were never
    overwritten with empties, and they are deliberately untouched.

    UNIVERSE (LOCKED): the posture universe is the set of DISTINCT NON-NULL
    ``company_id`` guids in the frame. guid-less (null/blank) rows DROP -- they
    fail SAFE to GHL by absence (the honest posture; no fabricated identity). A
    guid with multiple rows collapses to ONE deterministic representative
    (max ``last_modified``, tie-broken by ``gid``) supplying BOTH the enrollment status
    AND the destination cascade JOINTLY -- a coherent single-row posture, never
    status from one row mixed with a destination from another. A per-guid
    disagreement on ``custom_cal_status`` across a guid's rows is surfaced as a drift
    signal (returned for the caller to meter) but does NOT block the snapshot.

    Args:
        df: A warmed DataFrame carrying the projected posture columns.

    Returns:
        ``(extracted, drift_guids)`` -- the projected offices (one per distinct guid)
        and the guids whose rows disagreed on ``custom_cal_status``.

    Raises:
        FrameSchemaLagError: if the frame lacks the posture-projection columns.
    """
    import polars as pl

    missing = missing_frame_columns(df.columns)
    if missing:
        raise FrameSchemaLagError(
            f"frame lacks projected posture columns: {missing} "
            "(the read triggers a refresh; a subsequent run converges)"
        )

    # Universe: distinct non-null / non-blank company_id guids. guid-less offers DROP.
    universe = df.filter(
        pl.col(GUID_FIELD).is_not_null()
        & (pl.col(GUID_FIELD).cast(pl.Utf8).str.strip_chars() != "")
    )
    if universe.height == 0:
        return [], []

    # Drift: guids whose offers carry >= 2 distinct NON-NULL custom_cal_status values.
    drift_guids = (
        universe.filter(pl.col(CUSTOM_CAL_STATUS_FIELD).is_not_null())
        .group_by(GUID_FIELD)
        .agg(pl.col(CUSTOM_CAL_STATUS_FIELD).n_unique().alias("_n_status"))
        .filter(pl.col("_n_status") > 1)
        .get_column(GUID_FIELD)
        .to_list()
    )

    # Deterministic representative per guid: max last_modified, tie-broken by gid.
    # Sort so the winner is FIRST within each guid, then keep the first per guid.
    representatives = universe.sort(
        ["last_modified", "gid"], descending=[True, True], nulls_last=True
    ).unique(subset=[GUID_FIELD], keep="first", maintain_order=True)

    extracted: list[ExtractedScheduling] = []
    for row in representatives.iter_rows(named=True):
        try:
            extracted.append(map_frame_row_to_inputs(row))
        except (FrameSchemaLagError, ValueError) as exc:
            # Per-office isolation: a representative that cannot project is skipped,
            # never aborting the whole snapshot (guid-null is already excluded above).
            logger.warning(
                "scheduling_stratum_frame_project_skip",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
    return extracted, drift_guids


def join_office_spine(unit_holder_df: pl.DataFrame, business_df: pl.DataFrame) -> pl.DataFrame:
    """Join the office spine: ``unit_holder.parent_gid -> business.gid`` (PURE).

    Produces the frame the unchanged projection core consumes: the nine posture
    columns from ``unit_holder`` (its own cf: manifest) plus ``company_id`` from the
    ``business`` ancestor that owns it. Measured 2082/2082 = 100.0% linkage.

    A LEFT join is deliberate: a unit_holder whose business carries no
    ``Company ID`` yields a NULL guid and is DROPPED by the universe rule -- it fails
    SAFE to GHL by absence rather than being fabricated an identity. (DIAG CARD
    WS-B/3: 9 of 71 active offices are in this state today.)

    Only ``gid`` + ``company_id`` are taken from the business side so its ``name`` /
    ``last_modified`` / ``section`` cannot collide with the unit_holder columns the
    representative rule sorts on.

    Raises:
        FrameSchemaLagError: if either side lacks its required columns. This is the
            PR-1-not-yet-deployed detector -- a unit_holder frame carrying only BASE
            columns trips it and the run REFUSES honestly rather than pushing a
            fabricated all-null posture over 949 live offices.
    """
    import polars as pl

    # unit_holder side: the nine posture columns + the join key.
    missing_posture = [c for c in _POSTURE_SIGNAL_COLUMNS if c not in unit_holder_df.columns]
    if missing_posture:
        raise FrameSchemaLagError(
            f"unit_holder frame lacks the scheduling-posture columns {missing_posture} "
            "(UNIT_HOLDER_SCHEMA not deployed, or the warmer has not completed a cycle "
            "since it was). Refusing rather than pushing an all-null posture."
        )
    if OFFICE_SPINE_JOIN_KEY not in unit_holder_df.columns:
        raise FrameSchemaLagError(
            f"unit_holder frame lacks the office-spine join key {OFFICE_SPINE_JOIN_KEY!r}"
        )

    # D-6(a) SUFFIX-COLLISION GUARD: the join CONTRIBUTES company_id from the
    # business side. If the unit_holder frame ever carried its own company_id
    # column, polars would keep both as company_id / company_id_right and the
    # projection would silently read the WRONG one (UnitHolder's is always null --
    # R-7 -- so every office would drop). Refuse rather than resolve ambiguously.
    if GUID_FIELD in unit_holder_df.columns:
        raise FrameSchemaLagError(
            f"unit_holder frame unexpectedly carries {GUID_FIELD!r}; the office guid is "
            "owned by the BUSINESS ancestor and is contributed by this join. Joining "
            "would produce a suffixed duplicate column and read the wrong one."
        )

    # business side: the office guid + its own gid (the join target).
    missing_business = [c for c in ("gid", GUID_FIELD) if c not in business_df.columns]
    if missing_business:
        raise FrameSchemaLagError(
            f"business frame lacks the office-identity columns {missing_business}"
        )

    # D-6(b) DETERMINISTIC business-side dedup. business.gid is a task PK and is
    # unique in practice (live: 2572/2572), so this normally selects nothing --
    # but `keep="first"` on raw frame order would make a duplicate resolve
    # ARBITRARILY, and a leading row with a null guid would silently DROP an office
    # that has a perfectly good identity on its sibling row.
    #
    # Ordering mirrors the unit_holder representative rule (max last_modified,
    # tie-broken by gid) with ONE additional leading key: a non-null company_id
    # always wins. That extra key is the difference between keeping and losing an
    # office when a stale partial row sorts first.
    identity_sort_keys = ["_has_guid"]
    identity_descending = [True]
    if "last_modified" in business_df.columns:
        identity_sort_keys.append("last_modified")
        identity_descending.append(True)
    identity_sort_keys.append("gid")
    identity_descending.append(True)

    business_identity = (
        business_df.with_columns(
            (
                pl.col(GUID_FIELD).is_not_null()
                & (pl.col(GUID_FIELD).cast(pl.Utf8).str.strip_chars() != "")
            ).alias("_has_guid")
        )
        .sort(identity_sort_keys, descending=identity_descending, nulls_last=True)
        .unique(subset=["gid"], keep="first", maintain_order=True)
        .select(
            pl.col("gid").alias(OFFICE_SPINE_JOIN_KEY),
            pl.col(GUID_FIELD),
        )
    )

    return unit_holder_df.join(business_identity, on=OFFICE_SPINE_JOIN_KEY, how="left")


def office_spine_census(
    unit_holder_df: pl.DataFrame, business_df: pl.DataFrame, joined: pl.DataFrame
) -> dict[str, int]:
    """PURE per-tick census of the office spine (D-1 observability).

    The join DROPS a materially large share of unit_holder rows -- measured 52.4%
    on today's frames (3 null parent_gid + 1089 businesses carrying no
    ``Company ID``). Those rows fail SAFE to GHL by absence, which is the designed
    posture, but until now they vanished with ZERO signal.

    That silence matters because the two guards leave a detection BAND: with
    ``MIN_POSTURE_SIGNAL_ROWS = 1`` and a shrink-guard ceiling of 0.500, a universe
    could collapse from ~921 all the way to ~475 and still be accepted by both. This
    census makes the denominator observable every tick so a partial collapse is
    visible in the log/metric surface long before it reaches the guards.

    Pure and cheap (a few Polars aggregates); the caller emits.

    Returns:
        Counts keyed ``unit_holder_rows``, ``null_parent``, ``dangling_parent``,
        ``business_no_guid``, ``distinct_guids``.
    """
    import polars as pl

    def _non_blank(col: str) -> pl.Expr:
        return pl.col(col).is_not_null() & (pl.col(col).cast(pl.Utf8).str.strip_chars() != "")

    unit_holder_rows = unit_holder_df.height
    null_parent = unit_holder_df.filter(~_non_blank(OFFICE_SPINE_JOIN_KEY)).height

    business_gids = set(business_df.filter(_non_blank("gid")).get_column("gid").to_list())
    linked = unit_holder_df.filter(_non_blank(OFFICE_SPINE_JOIN_KEY))
    dangling_parent = linked.filter(
        ~pl.col(OFFICE_SPINE_JOIN_KEY).is_in(list(business_gids))
    ).height

    business_no_guid = business_df.filter(~_non_blank(GUID_FIELD)).height

    distinct_guids = (
        joined.filter(_non_blank(GUID_FIELD)).get_column(GUID_FIELD).n_unique()
        if GUID_FIELD in joined.columns
        else 0
    )

    return {
        "unit_holder_rows": unit_holder_rows,
        "null_parent": null_parent,
        "dangling_parent": dangling_parent,
        "business_no_guid": business_no_guid,
        "distinct_guids": distinct_guids,
    }


def project_office_frame(
    unit_holder_df: pl.DataFrame, business_df: pl.DataFrame
) -> tuple[list[ExtractedScheduling], list[str]]:
    """PURE office-spine projection (WS-B): join the spine, then project posture.

    The producer's source of record. Replaces the offer-frame projection, whose
    ``company_id`` and posture columns are structurally unreachable (the ancestor
    walk terminates at depth 1). Universe arithmetic on today's frames: the office
    spine yields ~921 distinct guids against a ``prior_count`` of 949 -- a shrink
    ratio of 0.030, comfortably inside the data side's 0.500 guard. An
    Offer-ACTIVE-scoped universe would be 57 guids (ratio 0.940) and would be
    correctly REFUSED on arrival; the universe must be the office spine.

    Delegates to the UNCHANGED :func:`project_posture_rows` core, so the universe
    rule, the deterministic per-guid representative rule, and the drift metering are
    identical to the offer-frame era.

    Returns:
        ``(extracted, drift_guids)`` -- one office per distinct guid, and the guids
        whose unit_holders disagreed on ``custom_cal_status``.

    Raises:
        FrameSchemaLagError: if either frame lacks its required columns.
    """
    return project_posture_rows(join_office_spine(unit_holder_df, business_df))


def posture_signal_row_count(df: pl.DataFrame) -> int:
    """Count universe offices carrying ANY scheduling-posture signal (VALUE-FLOOR input).

    The universe is the push universe (distinct-agnostic here: every non-null / non-blank
    ``company_id`` row -- dedup happens later in :func:`project_posture_rows`). An office
    carries a posture signal when its ``custom_cal_status`` OR any of the eight
    CASCADE_PRIORITY provider columns is non-null. A frame missing the posture columns
    entirely (pre-1.6.0 schema-lag) returns 0 here, but that case is caught earlier by
    the schema-lag guard -- this counter is only consulted once the columns are present.
    """
    import polars as pl

    signal_cols = [c for c in _POSTURE_SIGNAL_COLUMNS if c in df.columns]
    if GUID_FIELD not in df.columns or not signal_cols:
        return 0
    universe = df.filter(
        pl.col(GUID_FIELD).is_not_null()
        & (pl.col(GUID_FIELD).cast(pl.Utf8).str.strip_chars() != "")
    )
    if universe.height == 0:
        return 0
    return universe.filter(pl.any_horizontal([pl.col(c).is_not_null() for c in signal_cols])).height


def _posture_universe_height(df: pl.DataFrame) -> int:
    """The DENOMINATOR the value floor divides into: universe rows (C5 instrument).

    NEW and additive -- it duplicates the universe predicate
    :func:`assert_posture_signal_floor` already applies internally so the caller can
    PUBLISH the denominator without reaching into (or altering) the certified guard
    body. Same predicate as :func:`posture_signal_row_count`: rows whose
    ``company_id`` is non-null and non-blank.
    """
    import polars as pl

    if GUID_FIELD not in df.columns:
        return 0
    return df.filter(
        pl.col(GUID_FIELD).is_not_null()
        & (pl.col(GUID_FIELD).cast(pl.Utf8).str.strip_chars() != "")
    ).height


def assert_posture_signal_floor(df: pl.DataFrame) -> None:
    """VALUE-FLOOR guard: REFUSE a whole-source push whose projected posture is degenerate.

    The completeness contract already refuses an incomplete / empty office SET
    (:func:`assert_complete_office_set`), but a source that resolves every posture
    column to null -- a wrong-level or mis-named cascade source, the 1.5.0 defect --
    produces a FULL, non-empty office set whose CONTENT is empty (all enrolled=true /
    stratum='inactive' / destination null). company_id still resolves, so the SET gate
    passes; only a VALUE floor catches it.

    Raises :class:`SnapshotRefusedError` when a NON-EMPTY universe carries a posture
    signal on FEWER than :data:`MIN_POSTURE_SIGNAL_ROWS` offices. An empty universe is
    NOT floored here (it is the ``assert_complete_office_set`` empty-set refusal's
    remit); a legitimate fleet always clears the floor via ``custom_cal_status``.
    """
    import polars as pl

    signal_cols = [c for c in _POSTURE_SIGNAL_COLUMNS if c in df.columns]
    if GUID_FIELD not in df.columns or not signal_cols:
        # Missing columns => schema-lag territory (handled upstream); nothing to floor.
        return
    universe_height = df.filter(
        pl.col(GUID_FIELD).is_not_null()
        & (pl.col(GUID_FIELD).cast(pl.Utf8).str.strip_chars() != "")
    ).height
    if universe_height == 0:
        return  # empty universe => assert_complete_office_set refuses; not a value-floor case
    signal_rows = posture_signal_row_count(df)
    if signal_rows < MIN_POSTURE_SIGNAL_ROWS:
        raise SnapshotRefusedError(
            f"degenerate posture source (value floor): {signal_rows}/{universe_height} "
            "universe offices carry ANY scheduling-posture signal (null custom_cal_status "
            "AND all-null provider cascade across the WHOLE universe). The projection "
            "source is degenerate -- almost certainly a wrong-level or mis-named cascade "
            "source (cf. the 1.5.0 cf:Offer defect) rather than a genuinely all-unenrolled "
            "fleet. Refusing to push a whole-source snapshot that would overwrite live "
            "posture with empties."
        )


async def _enumerate_offices_from_frame(
    cache: Any, unit_holder_project_gid: str, business_project_gid: str
) -> tuple[list[ExtractedScheduling], bool]:
    """Return ``(extracted_offices, source_complete)`` by projecting the OFFICE SPINE.

    Both frames are FULL-project snapshots (warmed as wholes), so joining them yields
    the complete office posture set with ZERO Asana reads. Returns
    ``source_complete=False`` when EITHER frame is absent / unreadable -- a
    half-readable spine is a PARTIAL, and the completeness gate must REFUSE rather
    than let it reach the data side's whole-source DELETE. Raises
    :class:`SnapshotRefusedError` on SCHEMA-LAG so the refusal carries the honest
    reason.
    """
    unit_holder_entry = await cache.get_async(
        unit_holder_project_gid, SNAPSHOT_UNIT_HOLDER_ENTITY_TYPE
    )
    if unit_holder_entry is None or getattr(unit_holder_entry, "dataframe", None) is None:
        logger.warning(
            "scheduling_stratum_snapshot_no_unit_holder_frame",
            extra={"project_gid": unit_holder_project_gid},
        )
        return [], False

    business_entry = await cache.get_async(business_project_gid, SNAPSHOT_BUSINESS_ENTITY_TYPE)
    if business_entry is None or getattr(business_entry, "dataframe", None) is None:
        logger.warning(
            "scheduling_stratum_snapshot_no_business_frame",
            extra={"project_gid": business_project_gid},
        )
        return [], False

    unit_holder_df = unit_holder_entry.dataframe
    business_df = business_entry.dataframe
    if "gid" not in unit_holder_df.columns:
        logger.warning("scheduling_stratum_snapshot_unit_holder_frame_no_gid_column")
        return [], False

    try:
        joined = join_office_spine(unit_holder_df, business_df)
        # D-1: emit the per-tick spine census BEFORE the guards run, so a partial
        # collapse is observable even on ticks that end in a refusal (the refusing
        # ticks are exactly the ones an operator most needs the denominator for).
        census = office_spine_census(unit_holder_df, business_df, joined)
        logger.info("office_spine_universe_census", extra=census)
        emit_metric("SchedulingStratumUniverseCensus", census["distinct_guids"])
        emit_metric(
            "SchedulingStratumUniverseDropped",
            census["unit_holder_rows"] - census["distinct_guids"],
        )
        extracted, drift_guids = project_posture_rows(joined)
    except FrameSchemaLagError as exc:
        # SCHEMA-LAG: the unit_holder frame predates UNIT_HOLDER_SCHEMA (or the warmer
        # has not completed a cycle since it deployed), or the business frame lacks the
        # identity columns. REFUSE honestly -- never fabricate posture from a frame that
        # cannot carry it. This is the PR-1-before-PR-2 safety and it MUST fire.
        logger.warning("scheduling_stratum_snapshot_frame_schema_lag", extra={"reason": str(exc)})
        # D-1: promoted to a named constant and BOUND on the autom8y side
        # (asana-stratum-schema-lag). It was already dimension-free -- it simply had
        # no alarm watching it. The refusal it raises also lands on METRIC_REFUSED,
        # so this is the sub-class discriminator, not the coverage leg.
        emit_metric(METRIC_SCHEMA_LAG, 1)
        raise SnapshotRefusedError(str(exc)) from exc

    # VALUE-FLOOR: the columns are PRESENT (schema-lag passed) but their CONTENT may be
    # degenerate (all-null posture -- a wrong-level/wrong-name source, or a spine whose
    # posture never populated). company_id resolves fine, so the office SET is complete
    # and the SET gate would pass; only this value floor catches an all-empty projection
    # before it whole-source overwrites live posture. Evaluated on the JOINED frame --
    # the same rows the projection consumes. Raises SnapshotRefusedError.
    #
    # C5 DENOMINATOR INSTRUMENT. Publish the numbers the floor COMPARES, before it
    # decides. The floor has only ever answered a boolean (">= MIN_POSTURE_SIGNAL_ROWS"),
    # so no observation of the live signal-bearing count exists anywhere -- which is
    # precisely why the floor could not be responsibly ratcheted past 1. Emitted
    # BEFORE the guard so a REFUSING tick still publishes its measurement (the
    # refusing ticks are exactly the ones an operator most needs the numbers for),
    # and computed from the SAME helpers the guard uses so the two can never drift.
    # assert_posture_signal_floor / posture_signal_row_count bodies are UNTOUCHED.
    _signal_rows = posture_signal_row_count(joined)
    _universe_rows = _posture_universe_height(joined)
    logger.info(
        "scheduling_stratum_posture_signal_census",
        extra={
            "signal_rows": _signal_rows,
            "universe_rows": _universe_rows,
            "floor": MIN_POSTURE_SIGNAL_ROWS,
        },
    )
    emit_metric(METRIC_POSTURE_SIGNAL_ROWS, _signal_rows)
    emit_metric(METRIC_POSTURE_UNIVERSE_ROWS, _universe_rows)

    try:
        assert_posture_signal_floor(joined)
    except SnapshotRefusedError:
        emit_metric("SchedulingStratumSnapshotDegenerateSource", 1)
        raise

    if drift_guids:
        logger.warning(
            "scheduling_stratum_snapshot_status_drift",
            extra={"drift_guid_count": len(drift_guids)},
        )
        emit_metric("SchedulingStratumStatusDrift", len(drift_guids))
    return extracted, True


def _mint_stratum_push_token() -> str | None:
    """Mint the current-generation S2S JWT for the live stratum push, or None.

    Exchanges ``SERVICE_CLIENT_ID`` + ``SERVICE_CLIENT_SECRET`` for a genuine
    service JWT via :class:`~autom8_asana.auth.service_token.ServiceTokenAuthProvider`
    (the same client-credentials path ``workflow_handler`` uses). Returns the bearer
    string on success, or ``None`` on ANY failure -- missing/unresolvable creds,
    auth-service error, or an empty token.

    ``None`` is the honest-skip signal: the caller takes the no-push path rather than
    fall back to ``gid_push._get_auth_token()``'s legacy ``AUTOM8Y_DATA_API_KEY``
    fossil, whose live value is an 11-char single-segment stub the data side rejects
    (401 AUTH-TEB-003 "Token is malformed: Not enough segments"). DELIBERATELY
    broad-catch + degrade-to-skip -- UNLIKE ``workflow_handler`` (which raise-and-500s
    a mint failure) -- because this whole-snapshot push is non-blocking by contract
    (``services/scheduling_stratum_push``): a mint failure must be a skip, never a
    500 and never an unauthenticated POST.
    """
    from autom8_asana.auth.service_token import ServiceTokenAuthProvider

    try:
        provider = ServiceTokenAuthProvider()
        try:
            token = provider.get_secret("scheduling-stratum-push")
        finally:
            provider.close()
    except Exception as exc:  # noqa: BLE001 -- mint failure => honest skip, never the fossil
        logger.warning(
            "scheduling_stratum_snapshot_token_mint_failed",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )
        return None
    return token or None


async def _resolve_and_push_snapshot_authed(
    extracted_offices: list[ExtractedScheduling],
    *,
    dry_run: bool | None,
) -> StratumPushResult | None:
    """Push the projected snapshot with a freshly-minted S2S JWT (retire the fossil seam).

    The effective-dry-run decision is mirrored EXACTLY from
    :func:`~autom8_asana.services.scheduling_stratum_push.push_stratum_snapshot`, so
    the mint fires on precisely the runs that will POST:

      * DRY-RUN (no live POST) -- pass straight through with NO mint attempted; a
        dry-run must never fail on a mint issue (it does not authenticate).
      * LIVE POST -- mint via :func:`_mint_stratum_push_token` and inject it as
        ``auth_token``. On ANY mint failure take the honest skip: surface
        ``scheduling_stratum_push_skipped`` with a mint-failure reason and return
        ``None`` (``pushed=False``) -- NEVER push with a garbage/fossil token, NEVER
        crash the handler.

    This is only reached when the DARK gate is ON (``execute_snapshot_push``
    short-circuits to ``skipped`` before ``push`` when the gate is off), so the gate
    is not re-litigated here -- only the live-vs-dry-run split governs the mint.
    """
    enabled = _is_stratum_push_enabled()
    effective_dry_run = (not enabled) if dry_run is None else dry_run
    if effective_dry_run:
        return await resolve_and_push_snapshot(extracted_offices, dry_run=dry_run)

    token = _mint_stratum_push_token()
    if token is None:
        logger.warning(
            "scheduling_stratum_push_skipped",
            extra={
                "reason": "service_token_mint_failed",
                "entry_count": len(extracted_offices),
            },
        )
        return None
    return await resolve_and_push_snapshot(extracted_offices, dry_run=dry_run, auth_token=token)


async def run_snapshot_push_async(
    context: Any = None, *, dry_run: bool | None = None
) -> SnapshotRunResult:
    """Live wiring for the whole-snapshot push (DARK short-circuit + real substrate).

    The substrate (cache / registry / client / query-engine) is constructed lazily
    INSIDE the enumerate/push closures so that a DARK gate returns ``skipped`` with
    ZERO substrate construction and ZERO Asana reads.
    """

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        # Deferred imports (cold-start): only reached when the gate is ON.
        from autom8_asana.cache.dataframe.factory import (
            get_dataframe_cache,
            initialize_dataframe_cache,
        )
        from autom8_asana.models.business._bootstrap import bootstrap
        from autom8_asana.services.resolver import EntityProjectRegistry

        bootstrap()
        cache = get_dataframe_cache() or initialize_dataframe_cache()
        if cache is None:
            logger.error("scheduling_stratum_snapshot_cache_init_failed")
            return [], False

        registry = EntityProjectRegistry.get_instance()
        if not registry.is_ready():
            try:
                from autom8_asana.services.discovery import discover_entity_projects_async

                await discover_entity_projects_async()
            except Exception as exc:  # noqa: BLE001 -- discovery failure => incomplete source
                logger.warning(
                    "scheduling_stratum_snapshot_discovery_failed", extra={"error": str(exc)}
                )
                return [], False

        unit_holder_gid = registry.get_project_gid(SNAPSHOT_UNIT_HOLDER_ENTITY_TYPE)
        business_gid = registry.get_project_gid(SNAPSHOT_BUSINESS_ENTITY_TYPE)
        if not unit_holder_gid or not business_gid:
            # An unresolved spine project is an INCOMPLETE source, never a partial push.
            logger.error(
                "scheduling_stratum_snapshot_spine_project_unresolved",
                extra={
                    "unit_holder_resolved": bool(unit_holder_gid),
                    "business_resolved": bool(business_gid),
                },
            )
            return [], False
        return await _enumerate_offices_from_frame(cache, unit_holder_gid, business_gid)

    async def _push(extracted_offices: list[ExtractedScheduling]) -> StratumPushResult | None:
        # FRAME-FIRST: the offices are already projected from the warmed frame -- the
        # push path issues ZERO Asana reads (no AsanaClient / QueryEngine).
        # AUTH: route through _resolve_and_push_snapshot_authed so the LIVE POST
        # carries a freshly-minted S2S JWT (ServiceTokenAuthProvider), NOT the legacy
        # AUTOM8Y_DATA_API_KEY fossil (the 11-char single-segment stub the data side
        # rejects with 401 AUTH-TEB-003). Only reached when the gate is ON
        # (execute_snapshot_push short-circuits to skipped when it is off); a dry-run
        # passes straight through without a mint, and a mint failure is an honest skip
        # (pushed=False, no POST) -- never an unauthenticated POST, never a crash.
        return await _resolve_and_push_snapshot_authed(extracted_offices, dry_run=dry_run)

    return await execute_snapshot_push(
        gate=_is_stratum_push_enabled,
        enumerate_offices=_enumerate,
        push=_push,
        # ★ D-2. A SHADOW RUN is one the operator forced via the event. Truthiness
        # mirrors _resolve_and_push_snapshot_authed's own effective-dry-run rule
        # EXACTLY: reaching the push means the gate is ON, so there
        # `effective_dry_run = (not enabled) if dry_run is None else dry_run`
        # collapses to `bool(dry_run)`. A run that is dry because the GATE is off is
        # not a shadow run -- it never reaches the push at all (it returns `skipped`).
        shadow_run=bool(dry_run),
    )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for the scheduling-stratum whole-snapshot push.

    DEFAULT-DARK: returns ``skipped`` unless ``SCHEDULING_STRATUM_PUSH_ENABLED`` is
    truthy. ``refused`` (the completeness contract firing) and ``skipped`` are
    deliberate SAFE outcomes -> HTTP 200; only a substrate/config error is 500.
    """
    import asyncio

    logger.info("scheduling_stratum_snapshot_invoked", extra={"has_context": context is not None})
    # C1(a) LIVENESS deadman heartbeat -- emitted FIRST, on EVERY invocation
    # (skipped / refused / dry-run / pushed / error), before anything that can
    # raise. This is the "the producer's own absence must be detectable on a metric
    # that EXISTS every run" discipline: an alarm watching a metric only emitted on
    # the happy path cannot tell a dead producer from a busy one.
    emit_metric(METRIC_RUN_EPOCH, _now_epoch())
    # ``dry_run`` may be forced via the event for a shadow run even once the gate is on.
    dry_run = event.get("dry_run") if isinstance(event, dict) else None
    try:
        result = asyncio.run(run_snapshot_push_async(context, dry_run=dry_run))
    except Exception as exc:  # noqa: BLE001 -- lambda boundary: return an honest 500
        logger.error(
            "scheduling_stratum_snapshot_error",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )
        emit_metric("SchedulingStratumSnapshotError", 1)
        return {
            "statusCode": 500,
            "body": {"status": "error", "error": str(exc), "error_type": type(exc).__name__},
        }

    status_code = 500 if result.status == "error" else 200
    return {
        "statusCode": status_code,
        "body": {
            "status": result.status,
            "reason": result.reason,
            "entry_count": result.entry_count,
        },
    }


def _documented_cadence_hours() -> int:
    """The intended cadence (releaser-seam doc surface); default LOW-frequency hours."""
    raw = os.environ.get(SNAPSHOT_CADENCE_HOURS_ENV_VAR)
    if raw is None:
        return DEFAULT_SNAPSHOT_CADENCE_HOURS
    try:
        return int(raw)
    except (TypeError, ValueError):
        return DEFAULT_SNAPSHOT_CADENCE_HOURS


__all__ = [
    "ALARM_BOUND_METRICS",
    "DEFAULT_SNAPSHOT_CADENCE_HOURS",
    "METRIC_POSTURE_SIGNAL_ROWS",
    "METRIC_POSTURE_UNIVERSE_ROWS",
    "METRIC_PUSH_EPOCH",
    "METRIC_PUSH_FAILED",
    "METRIC_REFUSED",
    "METRIC_RUN_EPOCH",
    "METRIC_SCHEMA_LAG",
    "METRIC_SHADOW_RUN",
    "METRIC_SKIPPED",
    "MIN_POSTURE_SIGNAL_ROWS",
    "MIN_POSTURE_SIGNAL_ROWS_ENV_VAR",
    "OFFICE_SPINE_JOIN_KEY",
    "SNAPSHOT_BUSINESS_ENTITY_TYPE",
    "SNAPSHOT_CADENCE_HOURS_ENV_VAR",
    "SNAPSHOT_UNIT_HOLDER_ENTITY_TYPE",
    "SOURCE_HEALTH_COMPANION_METRICS",
    "SnapshotRefusedError",
    "SnapshotRunResult",
    "assert_complete_office_set",
    "assert_posture_signal_floor",
    "execute_snapshot_push",
    "handler",
    "join_office_spine",
    "office_spine_census",
    "posture_signal_row_count",
    "project_office_frame",
    "project_posture_rows",
    "run_snapshot_push_async",
]
