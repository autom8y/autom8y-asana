"""ECS fair-share self-cap tests -- the in-path 1390/60s cap on the FAIR_SHARE GET lane.

Mirror of ``test_budget_allocator_warmer_floor.py`` (the 110/60s warmer reservation) and
``test_canary_f1a_budget_allocator.py`` (the 2-sided discriminating canary), applied to
the ECS fair-share cap this build WIRES in-path. Before this build the 1390 cap was a
config constant + advisory-only overage telemetry with NO in-path ``gate.admit`` on the
ECS/fair-share GET path (``_floor_paced`` returns the fetch UNCHANGED off the warmer
lane). This suite proves the cap now BITES on the fair-share lane while staying
byte-identical-inert when the operator knob is off.

All transport is SIMULATED with an in-silico clock -- ZERO live Asana calls, ZERO real
sleeps (F-b: no live probes). Two-sided per the discriminating-canary doctrine: a
deliberately-OVER-1390 burst is CORRECTLY CAPPED/shed (the over-budget demand is a
broken INPUT the live cap refuses -- NOT a defect injected into a working surface,
G-THEATER forbidden) AND a real <=1390 demand passes GREEN.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autom8_asana.config import AsanaConfig, BudgetAllocatorConfig
from autom8_asana.transport.asana_http import AsanaHttpClient
from autom8_asana.transport.budget_allocator import (
    BudgetAllocator,
    PublishedFloor,
    WarmerFloorGate,
    set_budget_allocator,
)

# capacity-specification.md §6.1 / pythia PC-4: 1390 = 1500 ceiling - 110 warmer floor.
_FAIR_SHARE_CAP = 1390
_WINDOW_SECONDS = 60.0
# The two cache-warmer Lambdas carry this token; ECS/near-zero Lambdas do not.
_WARMER_FUNCTION_NAME = "autom8-asana-cache-warmer"


class _FakeClock:
    """Deterministic in-silico clock; ``sleep`` advances it (no real time)."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        assert seconds >= 0.0
        self.t += seconds


def _http_client() -> AsanaHttpClient:
    """A minimal AsanaHttpClient -- enough to exercise the fair-share seam methods."""
    return AsanaHttpClient(config=AsanaConfig(), auth_provider=MagicMock())


async def _admitted_in_window(
    *, cap: int, demand: int, window: float = _WINDOW_SECONDS
) -> tuple[int, float]:
    """Admit up to ``demand`` calls, STOPPING once simulated wall-clock reaches ``window``.

    Models a burst of ``demand`` GETs arriving inside one ``window``-second budget window
    under a ``cap``/60s gate. Returns ``(admitted_count, simulated_elapsed_seconds)``.
    """
    clock = _FakeClock()
    gate = WarmerFloorGate(
        PublishedFloor(max_requests=cap, window_seconds=60),
        clock=clock,
        sleep=clock.sleep,
    )
    admitted = 0
    for _ in range(demand):
        if clock.t >= window:
            break
        await gate.admit()
        admitted += 1
    return admitted, clock.t


# --------------------------------------------------------------------------
# Floor value + process-singleton memoization (the correctness substrate)
# --------------------------------------------------------------------------


def test_fair_share_floor_is_the_config_cap_over_the_window() -> None:
    """The fair-share floor is the config's 1390 cap over the 60s window (PC-2 pure read)."""
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=_FAIR_SHARE_CAP)
    )
    floor = alloc.fair_share_floor()
    assert floor.max_requests == _FAIR_SHARE_CAP
    assert floor.window_seconds == 60
    assert floor.rate_per_second == pytest.approx(_FAIR_SHARE_CAP / 60)


def test_fair_share_gate_is_process_singleton_memoized() -> None:
    """The fair-share gate is ONE shared instance per process (PC-1 unification).

    Load-bearing: a fresh gate per GET would reset the token bucket every call and never
    cap a CONCURRENT burst -- the cap would be a no-op. Memoization is what makes 1390/60s
    a process-wide budget rather than a per-call reset.
    """
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=_FAIR_SHARE_CAP)
    )
    first = alloc.fair_share_gate()
    second = alloc.fair_share_gate()
    assert first is second  # the SAME object, not a fresh per-call gate
    assert isinstance(first, WarmerFloorGate)


# --------------------------------------------------------------------------
# TWO-SIDED discriminating cap: over-1390 is shed, real <=1390 passes GREEN
# --------------------------------------------------------------------------


async def test_over_budget_burst_is_capped_and_real_demand_passes() -> None:
    """TWO-SIDED (discriminating-canary): the cap SHEDS an over-1390 burst AND passes a
    real <=1390 demand.

    * BROKEN INPUT (deliberately over budget): a 1400-GET burst inside one 60s window is
      CORRECTLY CAPPED to ~1390 admissions -- the ~10 excess GETs are shed past the
      window, so the ECS service stops starving the fleet's shared 1500/60s budget. The
      over-budget demand is a deliberately-broken INPUT the live cap refuses; NO defect
      is injected into a working surface (G-THEATER forbidden).
    * REAL INPUT (within budget): a 1000-GET demand passes GREEN in full -- legitimate
      under-budget traffic is never throttled.
    """
    capped, _ = await _admitted_in_window(cap=_FAIR_SHARE_CAP, demand=_FAIR_SHARE_CAP + 10)
    assert capped < _FAIR_SHARE_CAP + 10, "over-budget burst must be SHED, not fully admitted"
    assert capped == pytest.approx(_FAIR_SHARE_CAP, abs=2), "the cap holds at ~1390/60s"

    passed, elapsed = await _admitted_in_window(cap=_FAIR_SHARE_CAP, demand=1000)
    assert passed == 1000, "a real <=1390 demand must pass GREEN in full"
    assert elapsed < _WINDOW_SECONDS, "under-budget demand fits comfortably inside the window"


async def test_cap_value_has_teeth_loose_cap_admits_the_same_burst() -> None:
    """Teeth (mirror warmer 110-vs-55): a deliberately LOOSE cap (2000/60s) admits the
    SAME 1400-burst in FULL.

    This proves the shed in the test above is attributable to the 1390 VALUE, not to the
    window harness -- without it the cap assertion would be a rubber stamp. 1390 sheds the
    excess; 2000 does not.
    """
    admitted, _ = await _admitted_in_window(cap=2000, demand=_FAIR_SHARE_CAP + 10)
    assert admitted == _FAIR_SHARE_CAP + 10, (
        "a 2000/60s cap must admit the 1400-burst in full -- if it also sheds, the window "
        "harness has teeth of its own and the 1390 shed is not attributable to the cap"
    )


async def test_sustained_fair_share_rate_is_1390_per_60s() -> None:
    """The gate sustains exactly the published 1390/60s rate over multiple windows."""
    clock = _FakeClock()
    gate = WarmerFloorGate(
        PublishedFloor(max_requests=_FAIR_SHARE_CAP, window_seconds=60),
        clock=clock,
        sleep=clock.sleep,
    )
    n = _FAIR_SHARE_CAP * 3  # three windows' worth
    for _ in range(n):
        await gate.admit()
    observed_rate_per_min = n / (clock.t / 60)
    assert observed_rate_per_min == pytest.approx(_FAIR_SHARE_CAP, rel=0.01)


# --------------------------------------------------------------------------
# Transport seam lane-gating (mirror canary pair-c): two-sided byte-identical
# --------------------------------------------------------------------------


def test_seam_green_ecs_lane_armed_resolves_the_shared_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GREEN-after: ECS lane (non-warmer) + ARMED + GET => the shared 1390/60s gate resolves."""
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)  # ECS leaves it unset
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=_FAIR_SHARE_CAP)
    )
    set_budget_allocator(alloc)
    gate = _http_client()._resolve_fair_share_gate("GET")
    assert gate is not None  # production GET path now interposes the cap
    assert gate is alloc.fair_share_gate()  # the SAME process-singleton gate


def test_seam_red_disabled_is_byte_identical(monkeypatch: pytest.MonkeyPatch) -> None:
    """RED-before/disabled: byte-identical -- NO gate resolved (pre-allocator baseline).

    ENABLED=false is byte-identical to the pre-allocator surface (ITEM-D). The canary bites
    only if the disabled path had interposed the cap.
    """
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    set_budget_allocator(BudgetAllocator(BudgetAllocatorConfig(enabled=False)))
    assert _http_client()._resolve_fair_share_gate("GET") is None


def test_seam_red_warmer_lane_is_byte_identical(monkeypatch: pytest.MonkeyPatch) -> None:
    """RED/warmer-lane: the warmer self-paces its own 110/60s floor; no fair-share cap.

    Guards double-counting: a warmer-lane GET is already paced by _floor_paced's 110/60s
    reservation, so the fair-share cap must NOT also gate it (one request, one reservation).
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _WARMER_FUNCTION_NAME)
    set_budget_allocator(BudgetAllocator(BudgetAllocatorConfig(enabled=True)))
    assert _http_client()._resolve_fair_share_gate("GET") is None


def test_seam_red_write_method_is_byte_identical(monkeypatch: pytest.MonkeyPatch) -> None:
    """RED/write: POST/PUT/DELETE are out of scope -- write-side arbitration owed by clause (c)."""
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    set_budget_allocator(BudgetAllocator(BudgetAllocatorConfig(enabled=True)))
    client = _http_client()
    for method in ("POST", "PUT", "DELETE"):
        assert client._resolve_fair_share_gate(method) is None


async def test_seam_admit_advances_shared_gate_when_armed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GREEN end-to-end: _fair_share_admit drives the shared gate on the fair-share lane.

    With a fixture clock, admitting the full 1390-GET budget advances simulated wall-clock
    by one full window (1390 / (1390/60) == 60s) -- proving the ECS GET path is paced
    in-path, not merely observed. The DISABLED path leaves the clock untouched (byte-
    identical no-op).
    """
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    clock = _FakeClock()
    armed = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=_FAIR_SHARE_CAP),
        clock=clock,
        sleep=clock.sleep,
    )
    set_budget_allocator(armed)
    client = _http_client()
    for _ in range(_FAIR_SHARE_CAP):
        await client._fair_share_admit("GET")
    assert clock.t == pytest.approx(_WINDOW_SECONDS, abs=0.5)  # one full window of pacing

    # DISABLED: byte-identical -- the clock never advances (no interposition).
    idle = _FakeClock()
    set_budget_allocator(
        BudgetAllocator(BudgetAllocatorConfig(enabled=False), clock=idle, sleep=idle.sleep)
    )
    for _ in range(50):
        await _http_client()._fair_share_admit("GET")
    assert idle.t == 0.0  # no admission, no pacing


def test_seam_fail_open_on_gate_fault_returns_none_and_tripwires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail-OPEN (pythia PC-3 / C-4): a gate-resolution fault lets the GET PROCEED
    un-capped (returns None) and emits the budget_lane_failopen tripwire -- never
    fail-closed (a fail-closed cap would worsen the storm the node-4 gate defeated).
    """
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    broken = MagicMock()
    broken.enabled = True
    broken.fair_share_gate.side_effect = RuntimeError("boom")
    set_budget_allocator(broken)
    assert _http_client()._resolve_fair_share_gate("GET") is None  # fail-OPEN, not raised
    broken.note_lane_failopen.assert_called_once()  # tripwire emitted
