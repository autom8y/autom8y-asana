"""SD-02 account-status push -- live execution home on the ECS runtime.

THE PROBLEM (SPIKE-sd02-empty-registry-diagnosis-2026-07-08, H1 SUPPORTED):
    The account-status snapshot push existed ONLY in the cache-warmer Lambda's
    entity-type warm flow (``cache_warmer._warm_cache_async`` ->
    ``push_orchestrator._push_account_status_for_completed_entities``), and that
    lane is schedule-paused (Trap-4, 2026-06-08). The lanes that actually warm
    prod frames (ECS progressive preload, SWR refresh, both prematerialize
    lanes) never called it -- so ``account_status`` has held 0 rows since the
    table was created.

THE FIX (sprint-C6 of north-star-per-offer-economics):
    Give the push TWO in-repo firing points on the ECS runtime:

    1. A one-shot at the tail of progressive preload
       (``api/preload/progressive.py`` -> ``push_account_status_snapshot``).
    2. A periodic re-push loop (:class:`AccountStatusPushLoop`) at the ratified
       4-hour cadence, so churned accounts do not stay marked ACTIVE until the
       next deploy (the ACTIVE-scoped coverage denominator C-2 depends on).

    The Lambda seam stays exactly as-is; both lanes share the identical
    extraction + snapshot-replace push code, so dual-run (if the Lambda lane is
    ever re-armed) is idempotent last-writer-wins. Lane partition lever:
    ``STATUS_PUSH_ENABLED=false`` on whichever runtime should stand down
    (read per-process in ``services/gid_push.py``). Lane visibility: the
    ``invocation_id`` prefixes ``ecs-preload-*`` / ``ecs-interval-*``
    distinguish this runtime from the Lambda's ``aws_request_id``.

Isolation contract: the push must NEVER kill the preload task or the loop --
the whole seam body is wrapped in a broad catch that degrades to
``status_push_fatal_error`` (mirrors the Lambda lane's fatal guard in
``cache_warmer.py``). Lifecycle shape mirrors ``SliHeartbeat`` /
``EventLoopLagMonitor``: started in the FastAPI lifespan, cancelled cleanly
at shutdown.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)

#: Env var for the re-push cadence in seconds. Default 14400 (4 hours) -- the
#: RATIFIED cadence, which also makes the receiver docstring's "pushes
#: snapshots every 4 hours" true. A value <= 0 disables the periodic loop
#: (the preload-tail one-shot still fires).
STATUS_PUSH_INTERVAL_ENV_VAR = "STATUS_PUSH_INTERVAL_SECONDS"

#: Ratified 4-hour cadence (seconds).
DEFAULT_STATUS_PUSH_INTERVAL_SECONDS: float = 14400.0

#: Fixed lead, in seconds, before each epoch-grid point at which the loop fires.
#:
#: THE BUG THIS CURES. The loop used to sleep the interval FIRST and only then
#: push, so its fire phase was anchored to process BOOT -- an arbitrary instant.
#: The downstream consumer (account-status-recon, autom8y
#: ``terraform/services/account-status-recon/main.tf`` ``cron(0 */4 * * ? *)``)
#: reads the offer frame on a FIXED wall-clock grid -- measured read instant
#: HH:00:46.1 UTC, band 45.4-49.5 s, n=35 -- and suppresses its verdict surface
#: when the frame's verification age exceeds 7200 s (it warns at 3600 s).
#: Because the two phases were unrelated, ~50 % of boots left this loop's stamp
#: outside the consumer's window and the verdict surface went dark until the
#: next restart re-rolled the phase. Anchoring the fire to the wall clock makes
#: the phase a constant of the deployment instead of a coin flip.
#:
#: WHY 1800 s. The two failure directions are priced in the same currency and
#: balance at L ~= 1790 s: the late-stamp margin ``L + 45.4 - delta_max`` against
#: the warn margin ``3600 - (46.1 + L - delta_min)``, where delta is the measured
#: push->stamp latency, in [25.2, 78.2] s (n=30, p50 34.3, p95 45.7). 1800 also
#: lands the fire on HH:30:00 UTC, clear of BOTH known readers of
#: ``POST /v1/query/offer/rows`` (the 4-hourly reader above and the weekday
#: 13:00:08Z reconcile-ads reader), so the anchored rebuild never collides with
#: another trigger's build and its stamp is never confusable with theirs.
_ANCHOR_LEAD_SECONDS: float = 1800.0

#: Smallest delay the loop will ever sleep, so one grid slot can never fire
#: twice: a cycle whose push returns inside its own slot skips to the NEXT
#: slot. Capped at half a period so short override/test intervals stay honest.
_MIN_FIRE_GAP_SECONDS: float = 1.0


def _interval_from_env() -> float:
    """Resolve the loop interval from :data:`STATUS_PUSH_INTERVAL_ENV_VAR`.

    Unset/blank/unparseable values fall back to the ratified default so a typo
    can never silently disable the loop.
    """
    raw = os.environ.get(STATUS_PUSH_INTERVAL_ENV_VAR, "").strip()
    if not raw:
        return DEFAULT_STATUS_PUSH_INTERVAL_SECONDS
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "status_push_loop_invalid_interval",
            extra={
                "interval_env": STATUS_PUSH_INTERVAL_ENV_VAR,
                "raw_value": raw,
                "fallback_seconds": DEFAULT_STATUS_PUSH_INTERVAL_SECONDS,
            },
        )
        return DEFAULT_STATUS_PUSH_INTERVAL_SECONDS


def seconds_until_next_fire(now_epoch: float, interval: float, lead: float) -> float:
    """Seconds from *now_epoch* to the next epoch-grid fire instant.

    PURE -- no I/O, no sleeping, no module state. That is the point: the fire
    instant is a function of the wall clock alone, so an arbitrary boot instant
    is a TEST INPUT rather than a race, and every cycle re-acquires the grid
    from the clock instead of accumulating from its own start.

    The grid is ``k * interval - lead`` on the UTC epoch basis, so every
    returned delay satisfies::

        (now_epoch + delay) % interval == (-lead) % interval

    At the ratified 14400 s cadence with ``lead=1800`` that places every fire on
    HH:30:00 UTC, i.e. 1800 s ahead of the consumer's 4-hourly read grid.

    Args:
        now_epoch: Wall-clock seconds since the UNIX epoch (UTC by definition).
        interval: Grid period in seconds; must be > 0 (``start()`` refuses <= 0).
        lead: Seconds before each grid point at which to fire.

    Returns:
        A strictly positive delay. It is never smaller than
        :data:`_MIN_FIRE_GAP_SECONDS` (or half a period, whichever is less), so
        a push that returns inside its own slot skips forward to the next slot
        rather than firing that slot twice.
    """
    phase = (-lead) % interval
    delay = (phase - now_epoch) % interval
    min_gap = min(_MIN_FIRE_GAP_SECONDS, interval / 2.0)
    return delay if delay > min_gap else delay + interval


def _iso_z(epoch_seconds: float) -> str:
    """Render an epoch instant as second-resolution ISO-8601 UTC (``...Z``)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch_seconds))


async def push_account_status_snapshot(trigger: str) -> None:
    """Push ONE full account-status snapshot from the ECS in-process cache.

    Builds the entity set from the ``EntityProjectRegistry`` singleton and
    delegates to the EXISTING shared orchestrator
    (``_push_account_status_for_completed_entities``) -- the same code the
    Lambda lane runs, so snapshots are equivalent across lanes. Using the full
    registry set (not a "completed" list) is correct here: cache misses are
    already skipped per-entity by the orchestrator, and SWR-refreshed frames
    are picked up on later cycles.

    Pushes are always the FULL aggregated snapshot: the receiver is a
    transactional snapshot-replace, so a partial (per-frame) push would
    replace the whole registry with one project's rows.

    Never raises: any failure degrades to ``status_push_fatal_error``.

    Args:
        trigger: Firing point label ("preload" or "interval") -- carried into
            the invocation_id so the ECS lanes are distinguishable in logs.
    """
    try:
        from autom8_asana.cache.dataframe.factory import get_dataframe_cache
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )
        from autom8_asana.services.resolver import EntityProjectRegistry

        registry = EntityProjectRegistry.get_instance()
        cache = get_dataframe_cache()
        if cache is None or not registry.is_ready():
            logger.info(
                "status_push_skipped",
                extra={
                    "reason": "ecs_cache_or_registry_unready",
                    "trigger": trigger,
                },
            )
            return

        entity_types = registry.get_all_entity_types()

        def get_project_gid(entity_type: str) -> str | None:
            config = registry.get_config(entity_type)
            return config.project_gid if config else None

        await _push_account_status_for_completed_entities(
            completed_entities=entity_types,
            get_project_gid=get_project_gid,
            cache=cache,
            invocation_id=f"ecs-{trigger}-{uuid.uuid4()}",
        )
    except (
        Exception  # noqa: BLE001
    ) as e:  # BROAD-CATCH: isolation -- the push must never kill the preload task or the loop
        logger.error(
            "status_push_fatal_error",
            extra={
                "trigger": trigger,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


class AccountStatusPushLoop:
    """Periodic account-status re-push, anchored to the wall clock.

    Each cycle sleeps to the next epoch-grid slot -- ``k * interval - lead``,
    recomputed from the wall clock EVERY cycle by
    :func:`seconds_until_next_fire` -- then fires
    :func:`push_account_status_snapshot` with ``trigger="interval"``. The FIRST
    cycle still sleeps first (the startup push is the preload tail's job, not
    the loop's); the sleep is now a computed one instead of a whole period.
    Mirrors ``SliHeartbeat`` (api/sli_heartbeat.py) so the background timers
    share one lifecycle shape: started in the FastAPI lifespan, cancel-safe
    stop at shutdown.

    The period contract is unchanged for every interval: consecutive fires are
    exactly ``interval`` seconds apart, ``<= 0`` still disables the loop, and an
    unparseable env value still falls back to the ratified default. Only the
    PHASE changes -- from "wherever this process happened to boot" to a fixed
    point on the UTC grid. The safe-band guarantee that phase buys (see
    :data:`_ANCHOR_LEAD_SECONDS`) is DECLARED to hold only at the ratified
    cadence, because that is the consumer's read period; on any other interval
    the loop still anchors but says so once, loudly, at start
    (``status_push_loop_anchor_guarantee_void``).

    Recomputing every cycle (rather than aligning once at start) is what makes
    the phase self-correcting: a cycle delayed by a long push, an event-loop
    stall or a clock step re-acquires the grid at the very next iteration.
    Measured drift under the old accumulate-from-boot form was only ~0.4 s per
    cycle, so drift is NOT the motive -- self-correction and testability are.

    Args:
        interval_seconds: Grid period; defaults to the cadence resolved from
            :data:`STATUS_PUSH_INTERVAL_ENV_VAR`.
        lead_seconds: Seconds before each grid point to fire; defaults to
            :data:`_ANCHOR_LEAD_SECONDS`.
        clock: Wall-clock source returning epoch seconds. Injected in tests so
            an arbitrary boot instant is an input, never a real sleep.
        sleep: Awaitable delay function. Injected in tests for the same reason;
            production uses :func:`asyncio.sleep`.
    """

    def __init__(
        self,
        interval_seconds: float | None = None,
        *,
        lead_seconds: float | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._interval = interval_seconds if interval_seconds is not None else _interval_from_env()
        self._lead = lead_seconds if lead_seconds is not None else _ANCHOR_LEAD_SECONDS
        self._clock: Callable[[], float] = clock if clock is not None else time.time
        self._sleep: Callable[[float], Awaitable[None]] = (
            sleep if sleep is not None else asyncio.sleep
        )
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        # COUPLING, NAMED -- do not narrow this push or short-circuit it.
        # The push's per-entity ``cache.get_async``
        # (lambda_handlers/push_orchestrator.py, the extraction loop) is what
        # advances the offer frame's VERIFICATION axis: a cache entry older
        # than its TTL triggers an SWR rebuild
        # (cache/integration/dataframe_cache.py ``_trigger_swr_refresh``) whose
        # ``_probe_freshness`` pass writes ``last_verified_at``
        # (dataframes/builders/progressive.py). The stamp is therefore a SIDE
        # EFFECT of this loop, not of its declared account-status purpose -- and
        # it is the only traffic-independent advancer that exists today. Note
        # the ``STATUS_PUSH_ENABLED`` lever is checked DOWNSTREAM of those reads
        # (services/gid_push.py, in ``push_status_to_data_service``), so it
        # silences the push but NOT the stamp. Narrowing the sweep to "cheap"
        # entities, early-returning on the lever, or deleting the loop returns
        # the offers verification axis to the read-triggered case, where every
        # consumer read sees a ~one-period-old stamp and aborts. Guarded by
        # test_status_push_anchor.py::TestCouplingRegression.
        try:
            while True:
                await self._sleep(
                    seconds_until_next_fire(self._clock(), self._interval, self._lead)
                )
                await push_account_status_snapshot(trigger="interval")
        except asyncio.CancelledError:
            raise

    def start(self) -> asyncio.Task[None] | None:
        """Start the loop as a background task; returns the task handle.

        Returns ``None`` (and starts nothing) when the interval is <= 0
        (loop disabled). Idempotent: a second call while running returns the
        existing task.

        Logs the resolved anchor at boot (``lead_seconds`` + ``next_fire_at``)
        so the phase is attributable hours before the first fire, and logs
        ``status_push_loop_anchor_guarantee_void`` once when the interval is not
        the ratified cadence the safe band was computed against.
        """
        if self._interval <= 0:
            logger.info(
                "status_push_loop_disabled",
                extra={
                    "interval_env": STATUS_PUSH_INTERVAL_ENV_VAR,
                    "interval_seconds": self._interval,
                },
            )
            return None
        if self._task is not None and not self._task.done():
            return self._task
        if self._interval != DEFAULT_STATUS_PUSH_INTERVAL_SECONDS:
            # Silent degradation is the failure mode this whole cure exists to
            # punish: the period is still honoured exactly, but the safe band
            # was computed against the consumer's read period, so off-cadence
            # the anchor guarantees phase stability and nothing more.
            logger.warning(
                "status_push_loop_anchor_guarantee_void",
                extra={
                    "interval_seconds": self._interval,
                    "lead_seconds": self._lead,
                    "ratified_interval_seconds": DEFAULT_STATUS_PUSH_INTERVAL_SECONDS,
                    "effect": (
                        "period preserved and phase still anchored; the measured "
                        "safe band against the consumer's read grid does not apply"
                    ),
                },
            )
        now = self._clock()
        next_fire_epoch = now + seconds_until_next_fire(now, self._interval, self._lead)
        self._task = asyncio.create_task(self._run(), name="account_status_push_loop")
        logger.info(
            "status_push_loop_started",
            extra={
                "interval_seconds": self._interval,
                "lead_seconds": self._lead,
                "next_fire_at": _iso_z(next_fire_epoch),
            },
        )
        return self._task

    async def stop(self) -> None:
        """Cancel the loop task and await its teardown."""
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("status_push_loop_stopped")
        self._task = None
