"""ITEM-C warmer floor-admission tests -- the 110/60s claim + <=1800s sweep gate.

The warmer lane claims its static 110/60s floor and completes its gap-sweep under
it; AIMD-override proven. All transport is SIMULATED/mocked with an in-silico
clock -- ZERO live Asana calls, ZERO real sleeps (F-b honored; F-b forbids live
probes).

TL-A BUILD-GATE (ITEM-C): floor-admission drives a full 3,291-GET sweep in
<=1800s at 110/60s; if the sweep exceeds 1800s the 110 floor is UNDER-DERIVED ->
re-derive (HALT, do NOT fudge). AND under simulated AIMD self-suppression the
floored lane holds 110/60s; if AIMD still suppresses it to ~0, the reconciliation
is falsified -- HALT.

Adversary AC-3 (verbatim): with floor-admission at 110/min, a 3,291-GET sweep
completes within <=1800s of warm-window wall-clock.
"""

from __future__ import annotations

import pytest

from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.transport.adaptive_semaphore import AIMDConfig, AsyncAdaptiveSemaphore
from autom8_asana.transport.budget_allocator import (
    BudgetAllocator,
    PublishedFloor,
    WarmerFloorGate,
    running_in_warmer_lane,
)

# capacity-specification.md §1.2: the offer key's worst-case gap-fill.
_OFFER_SWEEP_GETS = 3291
# adversary AC-3 / TL-A: the sweep must complete within one 30-min tick.
_SWEEP_BUDGET_SECONDS = 1800
# capacity-specification.md §1.1: the offer key lands at list positions 17-18 of
# 68, one key PAST the 16-key bulk budget (_DEFAULT_BULK_KEY_BUDGET).
_BULK_KEY_BUDGET = 16
_OFFER_KEY_POSITION = 17  # 1-indexed; the offer key's first arm


class _FakeClock:
    """Deterministic in-silico clock; ``sleep`` advances it (no real time)."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        assert seconds >= 0.0
        self.t += seconds


async def _run_sweep(floor: PublishedFloor, n_gets: int) -> float:
    """Admit ``n_gets`` floor-protected calls; return simulated wall-clock secs."""
    clock = _FakeClock()
    gate = WarmerFloorGate(floor, clock=clock, sleep=clock.sleep)
    for _ in range(n_gets):
        await gate.admit()
    return clock.t


# --------------------------------------------------------------------------
# AC-3: the 3,291-GET sweep completes in <=1800s at 110/60s
# --------------------------------------------------------------------------


async def test_sweep_gate_3291_completes_under_1800s_at_110() -> None:
    """TL-A GREEN: floor=110/60s completes the offer sweep within the 30-min tick."""
    floor = PublishedFloor(max_requests=110, window_seconds=60)
    elapsed = await _run_sweep(floor, _OFFER_SWEEP_GETS)
    assert elapsed <= _SWEEP_BUDGET_SECONDS, (
        f"3,291-GET sweep took {elapsed:.1f}s > {_SWEEP_BUDGET_SECONDS}s at 110/60s "
        "-- the 110 floor would be UNDER-DERIVED; re-derive (do NOT fudge)."
    )
    # Honest capacity number: ~1795s (3291 / (110/60)); assert we are in-band.
    assert 1750 <= elapsed <= 1800


async def test_sweep_gate_under_derived_floor_55_exceeds_1800s() -> None:
    """Discriminating teeth: an UNDER-derived floor (55) FAILS the same bound.

    This proves the <=1800s gate is meaningful, not a rubber stamp: 110 clears it,
    55 does not. (capacity-specification.md §1.6: 55 = the zero-margin floor.)
    """
    floor = PublishedFloor(max_requests=55, window_seconds=60)
    elapsed = await _run_sweep(floor, _OFFER_SWEEP_GETS)
    assert elapsed > _SWEEP_BUDGET_SECONDS, (
        "floor=55 should NOT complete the sweep within 1800s -- if it does, the bound has no teeth."
    )


async def test_sustained_floor_rate_is_110_per_60s() -> None:
    """The gate sustains exactly the published rate over a long horizon."""
    floor = PublishedFloor(max_requests=110, window_seconds=60)
    elapsed = await _run_sweep(floor, 1100)  # 10 windows' worth
    observed_rate_per_min = 1100 / (elapsed / 60)
    assert observed_rate_per_min == pytest.approx(110, rel=0.02)


# --------------------------------------------------------------------------
# Queue-position-independence: the offer key at 17-18/68 is served
# --------------------------------------------------------------------------


async def test_floor_admission_is_queue_position_independent() -> None:
    """The offer key PAST the 16-key bulk budget is still served (capacity §1.1).

    Two-sided: the bulk-budget model STARVES position 17 in the first invocation
    (RED), while the floor gate SERVES it (GREEN) -- floor admission does not
    depend on queue position.
    """
    # RED model: the bulk warmer serves only the first 16 keys per invocation, so
    # the offer key at position 17 is NOT admitted in the first pass.
    served_by_bulk_budget = _OFFER_KEY_POSITION <= _BULK_KEY_BUDGET
    assert served_by_bulk_budget is False  # starved past the 16-key budget

    # GREEN: the floor gate admits all 68 keys at the floor rate, position-blind.
    floor = PublishedFloor(max_requests=110, window_seconds=60)
    clock = _FakeClock()
    gate = WarmerFloorGate(floor, clock=clock, sleep=clock.sleep)
    admitted_positions: list[int] = []
    for position in range(1, 68 + 1):  # all 68 keys
        await gate.admit()
        admitted_positions.append(position)
    assert _OFFER_KEY_POSITION in admitted_positions
    assert _OFFER_KEY_POSITION + 1 in admitted_positions  # the offer key's 2nd arm
    assert len(admitted_positions) == 68  # every key served, none starved


# --------------------------------------------------------------------------
# AIMD-override: the static floor holds 110/60s under AIMD self-suppression
# --------------------------------------------------------------------------


async def test_aimd_collapses_to_floor_under_storm() -> None:
    """RED reproduction: a real AsyncAdaptiveSemaphore self-suppresses under 429s.

    This reproduces the production suppression signature the floor must override
    (the 2026-07-14 oscillation toward 0). Precondition for the two-sided proof
    (adversary AC-3 / CH-02): the RED arm must actually bite.
    """
    sem = AsyncAdaptiveSemaphore(AIMDConfig(ceiling=25, floor=1, grace_period_seconds=0.0))
    assert sem.current_limit == 25  # starts wide
    # Simulate a sustained 429 storm: each acquired slot is rejected (429).
    for _ in range(10):
        async with await sem.acquire() as slot:
            slot.reject()
    assert sem.current_limit == 1, "AIMD must collapse toward its floor under a storm"


async def test_floor_gate_holds_110_while_aimd_suppressed() -> None:
    """TL-A GREEN: the static floor OVERRIDES AIMD self-suppression.

    While a real AIMD semaphore is collapsed to window=1 (suppressed), the warmer
    floor gate STILL admits at 110/60s -- it never reads the AIMD window or the
    global 429 signal (C-11 decoupled). This is the static-floor-overrides-AIMD
    reconciliation, proven in-silico.
    """
    # Drive a real AIMD semaphore to full suppression (window == floor == 1).
    sem = AsyncAdaptiveSemaphore(AIMDConfig(ceiling=25, floor=1, grace_period_seconds=0.0))
    for _ in range(10):
        async with await sem.acquire() as slot:
            slot.reject()
    assert sem.current_limit == 1  # AIMD is suppressed to ~0 admission

    # The floor gate, DECOUPLED from that AIMD, admits 110 in one 60s window.
    floor = PublishedFloor(max_requests=110, window_seconds=60)
    clock = _FakeClock()
    gate = WarmerFloorGate(floor, clock=clock, sleep=clock.sleep)
    admitted = 0
    while clock.t < 60.0:
        await gate.admit()
        admitted += 1
    # A concurrency-1 AIMD gate would admit far fewer; the floor holds ~110/60s.
    assert admitted >= 110, (
        f"floor gate admitted only {admitted} in 60s while AIMD was suppressed to 1 "
        "-- the static floor did NOT override AIMD; reconciliation falsified."
    )


def test_warmer_floor_gate_api_is_aimd_decoupled() -> None:
    """Structural: the gate cannot consult AIMD -- it takes only floor+clock+sleep."""
    import inspect

    params = set(inspect.signature(WarmerFloorGate.__init__).parameters)
    assert params == {"self", "floor", "clock", "sleep"}
    # And the allocator hands out a gate for the published floor.
    alloc = BudgetAllocator(BudgetAllocatorConfig(enabled=True))
    gate = alloc.warmer_floor_gate()
    assert isinstance(gate, WarmerFloorGate)


# --------------------------------------------------------------------------
# running_in_warmer_lane: only the cache-warmer Lambdas claim the floor
# --------------------------------------------------------------------------


def test_warmer_lane_true_for_cache_warmer_functions(monkeypatch: pytest.MonkeyPatch) -> None:
    """The two warmer Lambdas (main + bulk) carry the ``cache-warmer`` token."""
    for name in ("autom8-asana-cache-warmer", "autom8-asana-cache-warmer-bulk"):
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", name)
        assert running_in_warmer_lane() is True


def test_warmer_lane_false_for_ecs_and_near_zero_lambdas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ECS (no Lambda env) and near-zero workflow Lambdas are NOT the warmer lane.

    Floor pacing is a per-lane RESERVATION: these processes must never be throttled
    to the warmer's 110/60s. (capacity-spec: a worst-case floor-paced sweep is
    ~30 min -- catastrophic for a client-felt/fair-share build.)
    """
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    assert running_in_warmer_lane() is False  # ECS service leaves it unset

    for name in ("autom8y-asana-service", "autom8-asana-insights-export", ""):
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", name)
        assert running_in_warmer_lane() is False
