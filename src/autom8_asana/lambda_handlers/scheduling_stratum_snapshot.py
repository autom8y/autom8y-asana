"""Lambda handler: scheduling-stratum WHOLE-SNAPSHOT push (I2, DEFAULT-DARK).

The FORK-2 (c2) periodic full-snapshot trigger for the scheduling-posture substrate.
It re-pushes the FULL active-office set so the data side's whole-source DELETE
continually reconciles the projection against Asana (the surviving source-reconcile
that lets the 019 reconcile module dissolve). Mirrors the established
scheduled-entrypoint pattern (``cache_warmer`` client/cache setup +
``onboarding_walkthrough`` DARK-gate short-circuit), driving the pure
``resolve_and_push_snapshot`` pipeline.

FRAME-FIRST (FORK-1 A∘D, warm-projection). The active-office posture is projected in
ONE pure Polars pass over the ALREADY-WARMED offer frame (:func:`project_offer_frame`
via the pure ``map_frame_row_to_inputs``): sub-second, ZERO per-office Asana reads
(the measured 900s-Lambda-ceiling blocker is dissolved -- TDD-DELTA 2026-07-02). The
posture columns are projected upstream at bulk frame-warm time (offer schema 1.6.0 --
cascade:UnitHolder for the enrollment status + eight providers; see OFFER_SCHEMA).

EXPLICIT COMPLETENESS CONTRACT (the load-bearing safety):

    UNIVERSE (LOCKED): the posture universe is the set of DISTINCT NON-NULL
    ``company_id`` guids in the warmed offer frame. guid-less offers DROP and fail
    SAFE to GHL by absence (the honest posture). Multi-offer-per-guid collapses to ONE
    deterministic representative (max ``last_modified``) supplying enrollment status
    AND destination JOINTLY; a per-guid ``custom_cal_status`` disagreement is metered
    as drift.

    This entry point projects the FULL offer frame, NEVER a completed-entities
    partial. A partial batch fed to the data side's whole-source DELETE
    (``snapshot_replace``) would mass-wipe live enrolled offices -- strictly worse
    than a stale snapshot. :func:`assert_complete_office_set` REFUSES the push when
    the office set cannot be proven complete (an unreadable/absent offer frame, or an
    empty deduped guid set): it returns a ``refused`` outcome and pushes NOTHING.

    SCHEMA-LAG: the SWR cache serves stale-while-revalidate, so the first post-deploy
    read may serve a PRE-1.6.0 frame LACKING the projected posture columns. This is
    detected (:func:`missing_frame_columns`) and REFUSED honestly -- never fabricated
    or default-filled. The refusal's triggered refresh converges the frame; a
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

#: The offer entity type whose warmed DataFrame is the full active-office source.
SNAPSHOT_OFFER_ENTITY_TYPE = "offer"

#: Intended LOW-frequency cadence (hours) for the releaser-seam EventBridge rule.
#: NOT enforced by the handler (EventBridge owns scheduling); surfaced here so the
#: infra wiring has a single documented default.
DEFAULT_SNAPSHOT_CADENCE_HOURS = 6

#: Env override for the documented cadence (consumed by the releaser-seam infra).
SNAPSHOT_CADENCE_HOURS_ENV_VAR = "SCHEDULING_STRATUM_SNAPSHOT_CADENCE_HOURS"

#: VALUE-FLOOR guard threshold (the degenerate-source completeness teeth). A healthy
#: whole-source snapshot MUST carry a scheduling-posture SIGNAL on at least this many
#: offices in the universe. The 1.5.0 defect (cascade/cf sources at the WRONG level or
#: WRONG name) resolved EVERY posture column null, so 0/545 pushed offices carried any
#: signal -- yet company_id resolved fine, so the completeness gate passed and a
#: degenerate whole-source push overwrote live posture with empties. A legitimate
#: fleet -- even an all-GHL one that leaves the eight alt-providers null -- still
#: carries a non-null custom_cal_status (the office-global binary enrollment enum) on
#: every enrolled office, so a real universe never floors to zero.
MIN_POSTURE_SIGNAL_ROWS = 1

#: The posture-signal columns the value floor inspects: custom_cal_status + the eight
#: CASCADE_PRIORITY providers (i.e. every REQUIRED_FRAME_COLUMN except the identity
#: guid). Derived from REQUIRED_FRAME_COLUMNS so it stays in lockstep with the schema.
_POSTURE_SIGNAL_COLUMNS: tuple[str, ...] = tuple(
    c for c in REQUIRED_FRAME_COLUMNS if c != GUID_FIELD
)


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
    """
    if not gate():
        logger.info("scheduling_stratum_snapshot_skipped", extra={"reason": "gate_off"})
        emit_metric("SchedulingStratumSnapshotSkipped", 1, dimensions={"reason": "gate_off"})
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
        emit_metric(
            "SchedulingStratumSnapshotRefused",
            1,
            dimensions={"reason": "incomplete_office_set"},
        )
        return SnapshotRunResult(status="refused", reason=str(exc), entry_count=0)

    result = await push(extracted)
    entry_count = result.entry_count if result is not None else 0
    pushed = bool(result is not None and result.pushed)
    logger.info(
        "scheduling_stratum_snapshot_complete",
        extra={"office_count": len(extracted), "entry_count": entry_count, "pushed": pushed},
    )
    emit_metric(
        "SchedulingStratumSnapshotPushed" if pushed else "SchedulingStratumSnapshotDryRun",
        1,
        dimensions={"office_count": str(len(extracted))},
    )
    return SnapshotRunResult(
        status="pushed" if pushed else "dry_run",
        reason=None,
        entry_count=entry_count,
    )


def project_offer_frame(df: pl.DataFrame) -> tuple[list[ExtractedScheduling], list[str]]:
    """PURE frame projection: dedup offers by office guid + project posture (frame-first).

    UNIVERSE (LOCKED): the posture universe is the set of DISTINCT NON-NULL
    ``company_id`` guids in the offer frame. guid-less (null/blank) offers DROP -- they
    fail SAFE to GHL by absence (the honest posture; no fabricated identity). A
    guid with multiple active offers collapses to ONE deterministic representative
    (max ``last_modified``, tie-broken by ``gid``) supplying BOTH the enrollment status
    AND the destination cascade JOINTLY -- a coherent single-offer posture, never
    status from one offer mixed with a destination from another. A per-guid
    disagreement on ``custom_cal_status`` across a guid's offers is surfaced as a drift
    signal (returned for the caller to meter) but does NOT block the snapshot.

    Args:
        df: The warmed offer DataFrame (must carry the 1.5.0 posture columns).

    Returns:
        ``(extracted, drift_guids)`` -- the projected offices (one per distinct guid)
        and the guids whose offers disagreed on ``custom_cal_status``.

    Raises:
        FrameSchemaLagError: if the frame lacks the 1.5.0 posture-projection columns.
    """
    import polars as pl

    missing = missing_frame_columns(df.columns)
    if missing:
        raise FrameSchemaLagError(
            f"offer frame lacks projected posture columns (frame schema pre-1.5.0): {missing} "
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


def posture_signal_row_count(df: pl.DataFrame) -> int:
    """Count universe offices carrying ANY scheduling-posture signal (VALUE-FLOOR input).

    The universe is the push universe (distinct-agnostic here: every non-null / non-blank
    ``company_id`` row -- dedup happens later in :func:`project_offer_frame`). An office
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
    cache: Any, project_gid: str
) -> tuple[list[ExtractedScheduling], bool]:
    """Return ``(extracted_offices, source_complete)`` by PROJECTING the warmed offer frame.

    The offer frame is a FULL-project snapshot (warmed as a whole), so projecting its
    posture columns yields the complete active-office posture set with ZERO Asana
    reads. Returns ``source_complete=False`` when the frame is absent / unreadable --
    the completeness gate then REFUSES. Raises :class:`SnapshotRefusedError` on
    SCHEMA-LAG (a pre-1.5.0 frame) so the refusal carries the honest reason.
    """
    entry = await cache.get_async(project_gid, SNAPSHOT_OFFER_ENTITY_TYPE)
    if entry is None or getattr(entry, "dataframe", None) is None:
        logger.warning(
            "scheduling_stratum_snapshot_no_offer_frame", extra={"project_gid": project_gid}
        )
        return [], False
    df = entry.dataframe
    if "gid" not in df.columns:
        logger.warning("scheduling_stratum_snapshot_offer_frame_no_gid_column")
        return [], False

    try:
        extracted, drift_guids = project_offer_frame(df)
    except FrameSchemaLagError as exc:
        # SCHEMA-LAG: a stale-while-revalidate cache served a PRE-1.6.0 frame. REFUSE
        # honestly (never fabricate posture from a frame that cannot carry it).
        logger.warning("scheduling_stratum_snapshot_frame_schema_lag", extra={"reason": str(exc)})
        emit_metric("SchedulingStratumSnapshotSchemaLag", 1)
        raise SnapshotRefusedError(str(exc)) from exc

    # VALUE-FLOOR: the columns are PRESENT (schema-lag passed) but their CONTENT may be
    # degenerate (all-null posture -- the 1.5.0 wrong-level/wrong-name cascade defect).
    # company_id resolves fine, so the office SET is complete and the SET gate would
    # pass; only this value floor catches an all-empty projection before it whole-source
    # overwrites live posture. Raises SnapshotRefusedError (caught by execute_snapshot_push).
    try:
        assert_posture_signal_floor(df)
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

        project_gid = registry.get_project_gid(SNAPSHOT_OFFER_ENTITY_TYPE)
        if not project_gid:
            logger.error("scheduling_stratum_snapshot_offer_project_unresolved")
            return [], False
        return await _enumerate_offices_from_frame(cache, project_gid)

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
    )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for the scheduling-stratum whole-snapshot push.

    DEFAULT-DARK: returns ``skipped`` unless ``SCHEDULING_STRATUM_PUSH_ENABLED`` is
    truthy. ``refused`` (the completeness contract firing) and ``skipped`` are
    deliberate SAFE outcomes -> HTTP 200; only a substrate/config error is 500.
    """
    import asyncio

    logger.info("scheduling_stratum_snapshot_invoked", extra={"has_context": context is not None})
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
    "DEFAULT_SNAPSHOT_CADENCE_HOURS",
    "MIN_POSTURE_SIGNAL_ROWS",
    "SNAPSHOT_CADENCE_HOURS_ENV_VAR",
    "SNAPSHOT_OFFER_ENTITY_TYPE",
    "SnapshotRefusedError",
    "SnapshotRunResult",
    "assert_complete_office_set",
    "assert_posture_signal_floor",
    "execute_snapshot_push",
    "handler",
    "posture_signal_row_count",
    "project_offer_frame",
    "run_snapshot_push_async",
]
