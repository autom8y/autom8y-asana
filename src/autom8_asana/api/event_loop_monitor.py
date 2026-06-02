"""Lightweight asyncio event-loop lag monitor (TD-007, observability-plan §1.2).

The CPU-on-event-loop starvation failure that TD-001 fixes shows up first as
event-loop lag: when a synchronous Polars merge runs on the loop thread, the loop
cannot service its own timers, so a ``sleep(interval)`` overshoots. This monitor
samples that overshoot on a slow background timer and feeds it to the
``event_loop_lag_seconds`` histogram (p50/p99 derivable).

Design intent — CHEAP:
- One background task; sleeps ``interval_seconds`` (default 5s) between samples,
  so the steady-state cost is ~one ``loop.time()`` read + one histogram observe
  per interval. It adds NO per-request hot-path cost.
- The probe itself uses ``loop.time()`` (monotonic) deltas; no wall-clock, no I/O.

The monitor is started in the FastAPI lifespan and cancelled at shutdown.
"""

from __future__ import annotations

import asyncio

from autom8y_log import get_logger

from .metrics import record_event_loop_lag

logger = get_logger(__name__)

_DEFAULT_INTERVAL_SECONDS = 5.0


class EventLoopLagMonitor:
    """Samples event-loop scheduling lag on a slow background timer.

    Each tick measures ``actual_elapsed - intended_interval`` for a known sleep.
    A loop that is being starved by CPU-on-thread work overshoots the intended
    sleep, producing a positive lag sample. Negative jitter is clamped to 0 by
    ``record_event_loop_lag``.
    """

    def __init__(self, interval_seconds: float = _DEFAULT_INTERVAL_SECONDS) -> None:
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                start = loop.time()
                await asyncio.sleep(self._interval)
                # Overshoot beyond the intended interval == loop scheduling lag.
                lag = (loop.time() - start) - self._interval
                record_event_loop_lag(lag)
        except asyncio.CancelledError:
            raise

    def start(self) -> asyncio.Task[None]:
        """Start the monitor as a background task; returns the task handle."""
        if self._task is not None and not self._task.done():
            return self._task
        self._task = asyncio.create_task(self._run(), name="event_loop_lag_monitor")
        logger.info("event_loop_lag_monitor_started", extra={"interval_seconds": self._interval})
        return self._task

    async def stop(self) -> None:
        """Cancel the monitor task and await its teardown."""
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("event_loop_lag_monitor_stopped")
        self._task = None

    async def sample_once(self) -> float:
        """Take a single lag sample and emit it (test seam / one-shot probe).

        Returns the measured lag in seconds (overshoot of ``interval``).
        """
        loop = asyncio.get_running_loop()
        start = loop.time()
        await asyncio.sleep(self._interval)
        lag = (loop.time() - start) - self._interval
        record_event_loop_lag(lag)
        return lag
