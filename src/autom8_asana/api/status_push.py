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
import uuid

from autom8y_log import get_logger

logger = get_logger(__name__)

#: Env var for the re-push cadence in seconds. Default 14400 (4 hours) -- the
#: RATIFIED cadence, which also makes the receiver docstring's "pushes
#: snapshots every 4 hours" true. A value <= 0 disables the periodic loop
#: (the preload-tail one-shot still fires).
STATUS_PUSH_INTERVAL_ENV_VAR = "STATUS_PUSH_INTERVAL_SECONDS"

#: Ratified 4-hour cadence (seconds).
DEFAULT_STATUS_PUSH_INTERVAL_SECONDS: float = 14400.0


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
    """Periodic account-status re-push on a slow background timer.

    Each cycle sleeps :data:`STATUS_PUSH_INTERVAL_ENV_VAR` seconds (default
    the ratified 4h) then fires :func:`push_account_status_snapshot` with
    ``trigger="interval"``. The FIRST cycle sleeps first -- the startup push
    is the preload tail's job, not the loop's. Mirrors ``SliHeartbeat``
    (api/sli_heartbeat.py) so the background timers share one lifecycle shape:
    started in the FastAPI lifespan, cancel-safe stop at shutdown.
    """

    def __init__(self, interval_seconds: float | None = None) -> None:
        self._interval = interval_seconds if interval_seconds is not None else _interval_from_env()
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval)
                await push_account_status_snapshot(trigger="interval")
        except asyncio.CancelledError:
            raise

    def start(self) -> asyncio.Task[None] | None:
        """Start the loop as a background task; returns the task handle.

        Returns ``None`` (and starts nothing) when the interval is <= 0
        (loop disabled). Idempotent: a second call while running returns the
        existing task.
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
        self._task = asyncio.create_task(self._run(), name="account_status_push_loop")
        logger.info(
            "status_push_loop_started",
            extra={"interval_seconds": self._interval},
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
