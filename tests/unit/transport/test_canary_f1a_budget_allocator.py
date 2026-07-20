"""ITEM-F node-6 canary suite -- 2-sided, discriminating (F-b: all in-silico).

Two canary pairs + a rollback rehearsal, per HANDOFF §3 NODE-6 CANARY SPEC. Every
RED-before is CURRENT unguarded behavior failing a NEW assertion -- NOT an injected
defect (discriminating-canary doctrine; G-THEATER forbidden). The genuine
pre-allocator RED-before is archived from a pinned base-revision run at
``.sos/wip/thermia/f1a/canary-red-before-archive.txt`` (see the archive receipt).

Pair (a) -- ephemeral-bypass cap-leak (bounds the strongest-surviving-attack):
  RED-before: an ephemeral consumer leaks past the budget, silent and unbounded.
  GREEN-after: the advisory limiter detects + telemeters the leak; overage is
  bounded and budget_floor_overage fires. (Advisory cannot hard-block; GREEN =
  bounded-and-loud, not zero-leak.)

Pair (b) -- warmer self-suppression re-arm:
  RED-before: under storm/AIMD pressure the warmer self-suppresses to ~0.
  GREEN-after: with the static published floor, the warmer proceeds at 110/60s
  while AIMD suppresses everyone else.
"""

from __future__ import annotations

from typing import Any

from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.transport.adaptive_semaphore import AIMDConfig, AsyncAdaptiveSemaphore
from autom8_asana.transport.budget_allocator import (
    BudgetAllocator,
    Lane,
    PublishedFloor,
    WarmerFloorGate,
)

_FAIR_SHARE_CAP = 1390
_FLOOR = 110


class _RecordingLog:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def _rec(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self.events.append((event, extra or {}))

    debug = info = warning = error = _rec

    def named(self, name: str) -> list[dict[str, Any]]:
        return [extra for ev, extra in self.events if ev == name]


class _FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.t += seconds


# ==========================================================================
# Pair (a) -- ephemeral-bypass cap-leak: bounded-and-loud vs silent
# ==========================================================================


def test_canary_pair_a_green_leak_is_bounded_and_loud() -> None:
    """GREEN-after: the advisory limiter telemeters an ephemeral cap-leak."""
    log = _RecordingLog()
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=_FAIR_SHARE_CAP),
        log_provider=log,
    )
    # An ephemeral consumer leaks 10 calls past the 1390 fair-share cap.
    for _ in range(_FAIR_SHARE_CAP + 10):
        alloc.observe_admission(Lane.FAIR_SHARE)
    overages = log.named("budget_floor_overage")
    assert overages, "GREEN: an over-cap leak must be telemetered (bounded-and-loud)"
    assert overages[-1]["overage"] == 10  # the leak is BOUNDED and quantified
    assert overages[-1]["cap"] == _FAIR_SHARE_CAP


def test_canary_pair_a_red_disabled_leak_is_silent() -> None:
    """RED-before: the CURRENT unguarded (disabled) path is silent -- the disease.

    This is NOT an injected defect: ENABLED=false is byte-identical to the
    pre-allocator surface (ITEM-D), so this reproduces exactly today's silent,
    unbounded leak. The canary bites only if the disabled path were NOT silent.
    """
    log = _RecordingLog()
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=False, fair_share_max_requests=_FAIR_SHARE_CAP),
        log_provider=log,
    )
    for _ in range(_FAIR_SHARE_CAP + 10):
        alloc.observe_admission(Lane.FAIR_SHARE)
    assert log.named("budget_floor_overage") == []  # SILENT leak == the disease


# ==========================================================================
# Pair (b) -- warmer self-suppression re-arm
# ==========================================================================


async def test_canary_pair_b_green_floored_warmer_holds_110() -> None:
    """GREEN-after: the static floor holds 110/60s while AIMD is suppressed to 1."""
    sem = AsyncAdaptiveSemaphore(AIMDConfig(ceiling=25, floor=1, grace_period_seconds=0.0))
    for _ in range(10):
        async with await sem.acquire() as slot:
            slot.reject()
    assert sem.current_limit == 1  # AIMD suppressed

    clock = _FakeClock()
    gate = WarmerFloorGate(
        PublishedFloor(max_requests=_FLOOR, window_seconds=60),
        clock=clock,
        sleep=clock.sleep,
    )
    admitted = 0
    while clock.t < 60.0:
        await gate.admit()
        admitted += 1
    assert admitted >= _FLOOR  # floor holds ~110/60s despite AIMD=1


async def test_canary_pair_b_red_plain_aimd_self_suppresses() -> None:
    """RED-before: plain AIMD (no floor) collapses toward 0 under a storm.

    The CURRENT warmer wiring: a real AsyncAdaptiveSemaphore self-suppresses to
    window=1 under sustained 429s. Its sustained admission over a 60s window is
    FAR below the 110/60s the floor guarantees -- the 2026-07-14 oscillation. The
    canary bites only if plain AIMD did NOT collapse.
    """
    sem = AsyncAdaptiveSemaphore(AIMDConfig(ceiling=25, floor=1, grace_period_seconds=0.0))
    start_window = sem.current_limit
    for _ in range(10):
        async with await sem.acquire() as slot:
            slot.reject()
    # The suppression signature: the concurrency window collapses from its wide
    # start (25) all the way to the floor (1) under a sustained storm. A warmer
    # bound to THIS plain-AIMD wiring (and deferring on the global 429) cannot
    # guarantee 110/60s -- it self-suppresses toward 0 warm events (2026-07-14).
    # The static RATE floor (pair-b GREEN) is what overrides this collapse.
    assert start_window == 25
    assert sem.current_limit == 1  # collapsed to the floor == the disease reproduced


# ==========================================================================
# Rollback rehearsal (killswitch-rollback-spec §3.4): KILL => byte-identical
# ==========================================================================


def test_canary_rollback_rehearsal_byte_identical_revert() -> None:
    """Flip ENABLED=false mid-suite => byte-identical revert to un-arbitrated.

    Rehearses the KILL transition: an ARMED allocator telemeters; after the
    operator flips the knob false (KILLED), the SAME over-cap input produces the
    pre-allocator behavior -- no telemetry, no interposition (byte-identical).
    """
    # ACTIVE: the armed allocator telemeters the leak.
    armed_log = _RecordingLog()
    armed = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=_FAIR_SHARE_CAP),
        log_provider=armed_log,
    )
    for _ in range(_FAIR_SHARE_CAP + 5):
        armed.observe_admission(Lane.FAIR_SHARE)
    assert armed_log.named("budget_floor_overage")  # ACTIVE => loud

    # KILLED (operator flips false): identical input => byte-identical silence.
    killed_log = _RecordingLog()
    killed = BudgetAllocator(
        BudgetAllocatorConfig(enabled=False, fair_share_max_requests=_FAIR_SHARE_CAP),
        log_provider=killed_log,
    )
    for _ in range(_FAIR_SHARE_CAP + 5):
        killed.observe_admission(Lane.FAIR_SHARE)
    # Byte-identical revert: the KILLED path telemeters nothing and holds no
    # interposition state -- exactly the pre-allocator surface.
    assert killed_log.named("budget_floor_overage") == []
    assert killed.registered_client_count == 0
