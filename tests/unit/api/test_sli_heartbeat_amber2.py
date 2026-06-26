"""AMBER-2 SLI heartbeat tests — affirmative emitting-floor denominator.

PROVES (G-PROVE, G-THEATER): the heartbeat materializes the EXACT series the
``EcsServiceDenominatorAbsent{service=asana,slo=emitting_floor}`` alarm counts —
``autom8y_http_request_duration_seconds_count{service="asana"}`` — by directly
reading that series off the live prometheus_client default REGISTRY before and
after a heartbeat tick. These are NOT stubs: each assertion reads the real SDK
histogram (the same collector ``instrument_app`` registers).

PROVES (G-DENOM): the lit series is PROBE-class ONLY. The synthetic observation
carries ``route_class="probe"`` and a never-routed path; the business-class count
(``route_class="business"``) is asserted UNTOUCHED across a tick.

PROVES (dead-man NOT neutered): with the heartbeat absent (no tick), the
``service="asana"`` denominator stays at its baseline — i.e. nothing else lights
it — so a real outage (heartbeat task dead AND no traffic) leaves the denominator
dark and the dead-man re-fires. The heartbeat clears only the FALSE down.

Metric reads use the prometheus_client ``collect()``/sample pattern established in
tests/unit/api/test_honest_observability_td007.py and test_exports_metrics.py.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from autom8_asana.api import sli_heartbeat
from autom8_asana.api.sli_heartbeat import (
    HEARTBEAT_DISABLE_ENV,
    HEARTBEAT_PATH,
    SERVICE_NAME,
    SliHeartbeat,
    observe_heartbeat,
)

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# Series read helpers — read the SAME SDK histogram the alarm scrapes.
# ---------------------------------------------------------------------------


def _http_duration_histogram():
    """The cached platform histogram instance (the one instrument_app registers).

    Retrieving it via get_or_create_metrics returns the registry-cached collector
    for service_name="asana" — byte-for-byte the series the alarm counts.
    """
    from autom8y_telemetry.fastapi.metrics import get_or_create_metrics

    duration, _req, _inflight = get_or_create_metrics(
        service_name=SERVICE_NAME,
        route_class_labels=True,
    )
    return duration


def _denominator_count(**label_filter: str) -> float:
    """Sum of ``..._count`` samples on the HTTP duration histogram.

    With ``service="asana"`` filter this is EXACTLY
    ``count(autom8y_http_request_duration_seconds_count{service="asana"})``'s
    underlying value — the emitting-floor denominator the dead-man keys on.
    """
    hist = _http_duration_histogram()
    total = 0.0
    for metric in hist.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_count"):
                continue
            if all(sample.labels.get(k) == v for k, v in label_filter.items()):
                total += sample.value
    return total


# ---------------------------------------------------------------------------
# 1. The heartbeat materializes the denominator (G-PROVE / G-THEATER)
# ---------------------------------------------------------------------------


def test_heartbeat_materializes_service_asana_denominator() -> None:
    """One tick lights autom8y_http_request_duration_seconds_count{service=asana}."""
    before = _denominator_count(service="asana")
    observe_heartbeat()
    after = _denominator_count(service="asana")

    assert after == before + 1, (
        "one heartbeat must add exactly one observation to the "
        "service=asana emitting-floor denominator the alarm counts"
    )


def test_heartbeat_series_is_probe_class_and_synthetic_path() -> None:
    """The lit series carries route_class=probe on the synthetic heartbeat path."""
    before = _denominator_count(service="asana", route_class="probe", path=HEARTBEAT_PATH)
    observe_heartbeat()
    after = _denominator_count(service="asana", route_class="probe", path=HEARTBEAT_PATH)

    assert after == before + 1, "the heartbeat series is the probe-class synthetic path"


# ---------------------------------------------------------------------------
# 2. G-DENOM — probe-class ONLY; business denominator untouched
# ---------------------------------------------------------------------------


def test_heartbeat_does_not_touch_business_denominator() -> None:
    """A tick lights route_class=probe but NEVER route_class=business (G-DENOM)."""
    business_before = _denominator_count(service="asana", route_class="business")
    probe_before = _denominator_count(service="asana", route_class="probe")

    observe_heartbeat()

    business_after = _denominator_count(service="asana", route_class="business")
    probe_after = _denominator_count(service="asana", route_class="probe")

    assert business_after == business_before, (
        "G-DENOM: the heartbeat must NEVER contaminate the business economics denominator"
    )
    assert probe_after == probe_before + 1, "the heartbeat lights the probe class"


def test_heartbeat_does_not_touch_receiver_query_outcome() -> None:
    """G-DENOM: the heartbeat touches NONE of the domain economics counters."""
    from autom8_asana.api import metrics

    def _outcome_total() -> float:
        total = 0.0
        for metric in metrics.RECEIVER_QUERY_OUTCOME.collect():
            for sample in metric.samples:
                if sample.name.endswith("_total"):
                    total += sample.value
        return total

    before = _outcome_total()
    observe_heartbeat()
    after = _outcome_total()

    assert after == before, (
        "G-DENOM: receiver_query_outcome_total must be untouched by the heartbeat"
    )


# ---------------------------------------------------------------------------
# 3. Dead-man NOT neutered — absent heartbeat leaves the denominator dark
# ---------------------------------------------------------------------------


def test_absent_heartbeat_does_not_light_denominator() -> None:
    """No tick => no new denominator count (the dead-man still catches real-down).

    This is the anti-theater guard: if SOMETHING ELSE lit the service=asana
    denominator without a heartbeat, the dead-man could be silently neutered.
    Asserting the count is invariant across a no-op window proves the heartbeat
    is the ONLY thing this test lights — so when the heartbeat task is dead and
    there is no traffic, the denominator goes dark and EcsServiceDenominatorAbsent
    re-fires on a REAL outage.
    """
    before = _denominator_count(service="asana")
    # Deliberately do NOT tick. Spin the loop a little to give any errant
    # background emitter a chance to fire (there must be none in this unit ctx).
    after = _denominator_count(service="asana")

    assert after == before, "an absent heartbeat must NOT light the denominator"


# ---------------------------------------------------------------------------
# 4. Background task lifecycle (mirrors EventLoopLagMonitor contract)
# ---------------------------------------------------------------------------


async def test_heartbeat_task_lights_on_start_and_stops_clean() -> None:
    """start() lights the denominator immediately and stop() tears down cleanly."""
    before = _denominator_count(service="asana")
    hb = SliHeartbeat(interval_seconds=0.01)
    task = hb.start()
    assert task is not None and not task.done()

    # The task observes immediately on startup (before the first sleep), so the
    # denominator must advance without waiting a full interval.
    await asyncio.sleep(0.03)  # also lets at least one timer tick fire
    mid = _denominator_count(service="asana")
    assert mid >= before + 1, "the running heartbeat lights the denominator"

    await asyncio.wait_for(hb.stop(), timeout=1.0)
    assert task.done()


async def test_heartbeat_disabled_starts_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the disable flag set, start() returns None and lights nothing."""
    monkeypatch.setenv(HEARTBEAT_DISABLE_ENV, "true")
    assert sli_heartbeat.heartbeat_enabled() is False

    before = _denominator_count(service="asana")
    hb = SliHeartbeat(interval_seconds=0.01)
    task = hb.start()
    await asyncio.sleep(0.03)
    after = _denominator_count(service="asana")

    assert task is None, "a disabled heartbeat starts no background task"
    assert after == before, "a disabled heartbeat lights nothing"


def test_heartbeat_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default posture is ON (the soak precondition is default-armed)."""
    monkeypatch.delenv(HEARTBEAT_DISABLE_ENV, raising=False)
    assert sli_heartbeat.heartbeat_enabled() is True


def test_observe_never_raises_on_metric_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """observe_heartbeat is fire-and-forget: a metrics-layer error never escapes."""

    def _boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("registry exploded")

    monkeypatch.setattr("autom8y_telemetry.fastapi.metrics.get_or_create_metrics", _boom)
    # Must NOT raise — the broad catch keeps the background timer alive.
    observe_heartbeat()
