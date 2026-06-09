"""Affirmative SLI heartbeat — materializes the emitting-floor denominator.

THE PROBLEM (AMBER-2):
    ``EcsServiceDenominatorAbsent{service=asana,slo=emitting_floor}`` pages when
    the receiver is scraped + UP + instrumented but emits ZERO
    ``autom8y_http_request_duration_seconds_count{service="asana"}``. That happens
    whenever the receiver has had no NON-EXCLUDED requests: the warm-lane is
    paused, ECS/ALB health checks hit the ALWAYS-EXCLUDED ``/health``
    (autom8y_telemetry ``middleware.py`` ``_ALWAYS_EXCLUDED``), and — pre-cutover —
    there is no business traffic. The denominator stays dark, so the dead-man
    cannot tell "idle" from "down". A dark SLI cannot certify a soak.

THE FIX (affirmative liveness):
    A background asyncio task (mirroring ``EventLoopLagMonitor``) that, on a slow
    timer, directly observes the EXISTING platform HTTP duration histogram
    (``autom8y_http_request_duration_seconds``) under a clearly-SYNTHETIC,
    PROBE-class series. This materializes the denominator the alarm counts via the
    receiver's OWN liveness — it proves its serving path is alive even when idle —
    WITHOUT a network round-trip and WITHOUT the expensive ``/ready`` deep check
    (synchronous JWKS I/O, 503 when the warm-lane is paused).

G-DENOM (hard constraint — the synthetic series is PROBE-class ONLY):
    The observation carries ``route_class="probe"`` and a synthetic, never-routed
    path (:data:`HEARTBEAT_PATH`). It can NEVER contaminate the
    ``route_class="business"`` economics denominator, and it touches NONE of the
    domain counters (``receiver_query_outcome_total`` et al.). The dead-man keys on
    ``count(...{service="asana"}) >= 1`` (any route_class), so a probe-class
    observation is exactly sufficient to clear the FALSE down — while a real
    outage (heartbeat task dead AND no traffic) still leaves the denominator dark
    and re-fires the page. The dead-man is NOT neutered.

Design intent — CHEAP and ROBUST:
    - One background task; sleeps :data:`DEFAULT_INTERVAL_SECONDS` between ticks,
      so steady-state cost is ~one ``Histogram.observe`` per interval. NO
      per-request hot-path cost; negligible load on the single uvicorn worker.
    - The observed duration is a fixed, near-zero synthetic value — there is no
      real work to time. We are lighting the COUNT (denominator), not measuring
      latency; the probe-class latency distribution is not an SLI.
    - Retrieves the SAME cached histogram instance that ``instrument_app`` created
      (``get_or_create_metrics`` returns the registry-cached collector), so the
      series the heartbeat lights is byte-for-byte the one the alarm scrapes.
    - Feature-flag-guarded (default ON, disableable via
      :data:`HEARTBEAT_DISABLE_ENV`) so it can be turned off per-task without a
      code change if business traffic ever makes it redundant.
    - Started in the FastAPI lifespan and cancelled cleanly at shutdown.

The monitor is started in the FastAPI lifespan and cancelled at shutdown.
"""

from __future__ import annotations

import asyncio
import os

from autom8y_log import get_logger

logger = get_logger(__name__)

#: Default seconds between heartbeat ticks. 30s keeps the denominator lit well
#: inside any reasonable ``EcsServiceDenominatorAbsent`` evaluation window
#: (the alarm pages on absence over minutes) while costing ~one observe/30s.
DEFAULT_INTERVAL_SECONDS: float = 30.0

#: Service name — MUST match ``instrument_app(InstrumentationConfig(
#: service_name="asana"))`` at ``api/main.py`` so the lit series carries the
#: SAME ``service="asana"`` label the alarm selects on.
SERVICE_NAME: str = "asana"

#: Clearly-synthetic, never-routed path for the heartbeat series. It is NOT a
#: registered FastAPI route, so it can never collide with a business route
#: template; the double-underscore sentinel marks it as machine-emitted (mirrors
#: the SDK's ``/__unknown__`` sentinel convention).
HEARTBEAT_PATH: str = "/__sli_heartbeat__"

#: Synthetic HTTP method label. ``INTERNAL`` is deliberately not a real HTTP verb
#: so the series is unmistakably non-request traffic on inspection.
HEARTBEAT_METHOD: str = "INTERNAL"

#: Synthetic status — the heartbeat asserts the serving path is HEALTHY, so 200.
HEARTBEAT_STATUS: str = "200"

#: Route-class label. PROBE (never "business") is the G-DENOM invariant: the lit
#: series is denominator-affirmative for the emitting-floor alarm but is excluded
#: from any business-scoped SLI denominator by the ``route_class`` filter.
HEARTBEAT_ROUTE_CLASS: str = "probe"

#: Near-zero synthetic observation. We light the COUNT, not a latency measurement;
#: a tiny fixed value keeps the probe-class histogram's sum negligible.
_HEARTBEAT_OBSERVED_SECONDS: float = 0.0

#: Env var that DISABLES the heartbeat (default ON). Accepts the usual falsey
#: spellings. Read at start() time so a per-task flip needs no code change.
HEARTBEAT_DISABLE_ENV: str = "ASANA_SLI_HEARTBEAT_DISABLED"


def heartbeat_enabled() -> bool:
    """Return True unless the heartbeat is explicitly disabled (default ON).

    The disable flag is read at :meth:`SliHeartbeat.start` time (not import time)
    so it can be flipped per-task without a redeploy. Any of ``1/true/yes/on``
    (case-insensitive) in :data:`HEARTBEAT_DISABLE_ENV` turns the heartbeat OFF;
    an unset or any other value leaves it ON.
    """
    return os.environ.get(HEARTBEAT_DISABLE_ENV, "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }


def observe_heartbeat() -> None:
    """Observe ONE synthetic PROBE-class sample on the platform HTTP histogram.

    Retrieves the SAME ``autom8y_http_request_duration_seconds`` histogram that
    ``instrument_app`` registered (``get_or_create_metrics`` returns the
    registry-cached collector for ``service_name="asana"``), then records a single
    observation under the synthetic, never-routed, PROBE-class label set. This
    materializes ``autom8y_http_request_duration_seconds_count{service="asana"}``
    — the exact series ``EcsServiceDenominatorAbsent`` counts — proving the
    receiver's serving path is alive even with zero business traffic.

    Fire-and-forget: wrapped in a broad try/except so a metrics-layer error can
    never propagate out of the background timer and crash the heartbeat task.

    G-DENOM: ``route_class="probe"`` + synthetic path/method — the business
    denominator and the domain counters are never touched.
    """
    try:
        # Import lazily so this module stays import-safe even if the telemetry
        # SDK metric layer is not yet initialized at import time. The call is
        # cheap and idempotent: get_or_create_metrics returns the cached collector
        # after the first call (the same one instrument_app created).
        from autom8y_telemetry.fastapi.metrics import get_or_create_metrics

        duration_histogram, _requests_counter, _in_flight = get_or_create_metrics(
            service_name=SERVICE_NAME,
            route_class_labels=True,
        )
        duration_histogram.labels(
            service=SERVICE_NAME,
            method=HEARTBEAT_METHOD,
            path=HEARTBEAT_PATH,
            status=HEARTBEAT_STATUS,
            route_class=HEARTBEAT_ROUTE_CLASS,
        ).observe(_HEARTBEAT_OBSERVED_SECONDS)
    except Exception as e:  # BROAD-CATCH: fire-and-forget — never crash the timer  # noqa: BLE001
        logger.warning("sli_heartbeat_observe_error", extra={"error": str(e)})


class SliHeartbeat:
    """Lights the emitting-floor denominator on a slow background timer.

    Each tick calls :func:`observe_heartbeat`, which records one synthetic
    PROBE-class observation on the platform HTTP duration histogram. The task
    survives observe errors (fire-and-forget) and is cancellable cleanly at
    shutdown. Mirrors ``EventLoopLagMonitor`` (api/event_loop_monitor.py) so the
    two background timers share one lifecycle shape.
    """

    def __init__(self, interval_seconds: float = DEFAULT_INTERVAL_SECONDS) -> None:
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        # Light the denominator IMMEDIATELY on startup so the series exists before
        # the first interval elapses — otherwise a freshly-started task that is
        # scraped within the first ``interval`` window would still read dark.
        observe_heartbeat()
        try:
            while True:
                await asyncio.sleep(self._interval)
                observe_heartbeat()
        except asyncio.CancelledError:
            raise

    def start(self) -> asyncio.Task[None] | None:
        """Start the heartbeat as a background task; returns the task handle.

        Returns ``None`` (and starts nothing) when the heartbeat is disabled via
        :data:`HEARTBEAT_DISABLE_ENV`. Idempotent: a second call while running
        returns the existing task.
        """
        if not heartbeat_enabled():
            logger.info(
                "sli_heartbeat_disabled",
                extra={"disable_env": HEARTBEAT_DISABLE_ENV},
            )
            return None
        if self._task is not None and not self._task.done():
            return self._task
        self._task = asyncio.create_task(self._run(), name="sli_heartbeat")
        logger.info("sli_heartbeat_started", extra={"interval_seconds": self._interval})
        return self._task

    async def stop(self) -> None:
        """Cancel the heartbeat task and await its teardown."""
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("sli_heartbeat_stopped")
        self._task = None

    def tick_once(self) -> None:
        """Emit one heartbeat observation synchronously (test seam / one-shot).

        Lets a test exercise the EXACT series-materialization the timer performs
        without waiting for a sleep interval or spinning the event loop.
        """
        observe_heartbeat()
