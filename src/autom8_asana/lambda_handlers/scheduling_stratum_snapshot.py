"""Lambda handler: scheduling-stratum WHOLE-SNAPSHOT push (I2, DEFAULT-DARK).

The FORK-2 (c2) periodic full-snapshot trigger for the scheduling-posture substrate.
It re-pushes the FULL active-office set so the data side's whole-source DELETE
continually reconciles the projection against Asana (the surviving source-reconcile
that lets the 019 reconcile module dissolve). Mirrors the established
scheduled-entrypoint pattern (``cache_warmer`` client/cache setup +
``onboarding_walkthrough`` DARK-gate short-circuit), driving the pure
``resolve_and_push_snapshot`` pipeline.

EXPLICIT COMPLETENESS CONTRACT (the load-bearing safety):

    This entry point iterates the FULL active-office set, NEVER a completed-entities
    partial. A partial batch fed to the data side's whole-source DELETE
    (``snapshot_replace``) would mass-wipe live enrolled offices -- strictly worse
    than a stale snapshot. :func:`assert_complete_office_set` REFUSES the push when
    the office set cannot be proven complete (an unreadable/absent offer frame, or an
    empty batch): it returns a ``refused`` outcome and pushes NOTHING.

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
    AUTOM8Y_DATA_URL (+ S2S auth env): data-service base URL / creds for the sync.
    SCHEDULING_STRATUM_SNAPSHOT_CADENCE_HOURS: intended cadence (releaser-seam doc).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, NamedTuple

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric
from autom8_asana.services.scheduling_stratum_push import (
    _is_stratum_push_enabled,
    resolve_and_push_snapshot,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

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
    enumerate_office_gids: Callable[[], Awaitable[tuple[list[str], bool]]],
    push: Callable[[list[str]], Awaitable[StratumPushResult | None]],
) -> SnapshotRunResult:
    """Orchestrate one whole-snapshot push under the DARK gate + completeness contract.

    Injectable core (no live substrate) so the gate / completeness / push decisions
    are unit-testable. When ``gate()`` is falsy the enumeration is NEVER invoked -- no
    substrate construction, no Asana read (the DEFAULT-DARK guarantee).
    """
    if not gate():
        logger.info("scheduling_stratum_snapshot_skipped", extra={"reason": "gate_off"})
        emit_metric("SchedulingStratumSnapshotSkipped", 1, dimensions={"reason": "gate_off"})
        return SnapshotRunResult(status="skipped", reason="gate_off", entry_count=0)

    office_gids, source_complete = await enumerate_office_gids()
    try:
        complete_set = assert_complete_office_set(office_gids, source_complete=source_complete)
    except SnapshotRefusedError as exc:
        logger.warning("scheduling_stratum_snapshot_refused", extra={"reason": str(exc)})
        emit_metric(
            "SchedulingStratumSnapshotRefused",
            1,
            dimensions={"reason": "incomplete_office_set"},
        )
        return SnapshotRunResult(status="refused", reason=str(exc), entry_count=0)

    result = await push(complete_set)
    entry_count = result.entry_count if result is not None else 0
    pushed = bool(result is not None and result.pushed)
    logger.info(
        "scheduling_stratum_snapshot_complete",
        extra={"office_count": len(complete_set), "entry_count": entry_count, "pushed": pushed},
    )
    emit_metric(
        "SchedulingStratumSnapshotPushed" if pushed else "SchedulingStratumSnapshotDryRun",
        1,
        dimensions={"office_count": str(len(complete_set))},
    )
    return SnapshotRunResult(
        status="pushed" if pushed else "dry_run",
        reason=None,
        entry_count=entry_count,
    )


async def _enumerate_active_office_gids(cache: Any, project_gid: str) -> tuple[list[str], bool]:
    """Return ``(office_gids, source_complete)`` from the warmed offer DataFrame.

    The offer frame is a FULL-project snapshot (warmed as a whole), so its ``gid``
    column IS the complete active-office set. Returns ``source_complete=False`` when
    the frame is absent / unreadable -- the completeness gate then REFUSES the push.
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
    gids = [str(g) for g in df["gid"].to_list() if g]
    return gids, True


async def run_snapshot_push_async(
    context: Any = None, *, dry_run: bool | None = None
) -> SnapshotRunResult:
    """Live wiring for the whole-snapshot push (DARK short-circuit + real substrate).

    The substrate (cache / registry / client / query-engine) is constructed lazily
    INSIDE the enumerate/push closures so that a DARK gate returns ``skipped`` with
    ZERO substrate construction and ZERO Asana reads.
    """

    async def _enumerate() -> tuple[list[str], bool]:
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
        return await _enumerate_active_office_gids(cache, project_gid)

    async def _push(office_gids: list[str]) -> StratumPushResult | None:
        from autom8y_config.lambda_extension import resolve_secret_from_env

        from autom8_asana import AsanaClient
        from autom8_asana.auth.bot_pat import get_bot_pat
        from autom8_asana.auth.service_token import ServiceTokenAuthProvider
        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.services.query_service import EntityQueryService

        bot_pat = get_bot_pat()
        workspace_gid = resolve_secret_from_env("ASANA_WORKSPACE_GID")
        auth_provider = ServiceTokenAuthProvider()
        async with (
            AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client,
            DataServiceClient(auth_provider=auth_provider) as data_client,
        ):
            query_engine = QueryEngine(provider=EntityQueryService(), data_client=data_client)
            return await resolve_and_push_snapshot(
                office_gids,
                client=client,
                query_engine=query_engine,
                dry_run=dry_run,
            )

    return await execute_snapshot_push(
        gate=_is_stratum_push_enabled,
        enumerate_office_gids=_enumerate,
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
    "SNAPSHOT_CADENCE_HOURS_ENV_VAR",
    "SNAPSHOT_OFFER_ENTITY_TYPE",
    "SnapshotRefusedError",
    "SnapshotRunResult",
    "assert_complete_office_set",
    "execute_snapshot_push",
    "handler",
    "run_snapshot_push_async",
]
