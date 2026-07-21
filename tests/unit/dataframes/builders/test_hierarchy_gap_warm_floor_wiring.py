"""F1a warmer floor WIRING + AC-4 per-chunk banking for warm_hierarchy_gaps_async.

Closes F-C3-01 (CUSTODY-f1a-flip-ac4-ac5-2026-07-21 §2): before this build the
flip was registration-only -- ``WarmerFloorGate.admit`` and ``observe_admission``
had ZERO production call sites, so flipping ``ASANA_BUDGET_ALLOCATOR_ENABLED``
changed only bookkeeping. This suite proves the production call path now exists:
in the warmer lane with the allocator ARMED, every gap-warm GET is admitted
through the floor gate (the pattern the QA live-leg harness drove by hand,
QA-live-leg-verdict.md), and durable progress is banked PER CHUNK (AC-4 option
(b'), §3.4) so the §3.3 inversion (floor-paced sweeps outrun the 900s Lambda wall)
loses at most one chunk instead of the whole sweep.

Two-sided throughout (discriminating-canary doctrine):
  * ARMED + warmer lane  -> paced GETs + per-chunk banking (the cure).
  * disabled OR not the warmer lane -> byte-identical baseline: NO admit
    interposition on the Asana path, single end-of-sweep banking. The disabled
    arm is the disease preserved, not an injected defect (ENABLED=false is
    byte-identical to the pre-allocator surface, ITEM-D).

The WarmerFloorGate.admit rate contract itself (110/60s, <=1800s sweep,
AIMD-decoupled) is proven in test_budget_allocator_warmer_floor.py; here we prove
the PRODUCTION path reaches it and that real pacing flows end-to-end.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.dataframes.builders import hierarchy_warmer as hw_module
from autom8_asana.dataframes.builders.hierarchy_warmer import HierarchyWarmer
from autom8_asana.transport.budget_allocator import (
    BudgetAllocator,
    Lane,
    set_budget_allocator,
)

_WARMER_FUNCTION_NAME = "autom8-asana-cache-warmer"
_ECS_FUNCTION_NAME = "autom8y-asana-service"  # not a Lambda name; no warmer token


# ---------------------------------------------------------------------------
# Spies + fakes
# ---------------------------------------------------------------------------


class _SpyGate:
    """Counts admissions. Proves the PRODUCTION path routes each gap GET through
    ``WarmerFloorGate.admit`` (F-C3-01); the gate's rate contract is proven
    separately in test_budget_allocator_warmer_floor.py."""

    def __init__(self) -> None:
        self.admits = 0

    async def admit(self) -> None:
        self.admits += 1


class _SpyAllocator:
    """Minimal allocator stand-in matching the surface _floor_paced consults."""

    def __init__(self, *, enabled: bool, raise_on_gate: bool = False) -> None:
        self._enabled = enabled
        self._raise_on_gate = raise_on_gate
        self.gate = _SpyGate()
        self.observed: list[Lane] = []
        self.failopens: list[Lane] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def warmer_floor_gate(self, **_: Any) -> _SpyGate:
        if self._raise_on_gate:
            raise RuntimeError("gate construction fault (fail-open probe)")
        return self.gate

    def observe_admission(self, lane: Lane, *, count: int = 1) -> None:
        self.observed.append(lane)

    def note_lane_failopen(self, lane: Lane, error: BaseException) -> None:
        self.failopens.append(lane)


class _FakeClock:
    """Deterministic in-silico clock; ``sleep`` advances it (no real time)."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        assert seconds >= 0.0
        self.t += seconds


def _make_warmer(
    get_async_side_effect: Any,
    *,
    max_concurrent: int = 4,
    cached_gids: set[str] | None = None,
) -> tuple[HierarchyWarmer, MagicMock, AsyncMock]:
    cached = cached_gids or set()
    store = MagicMock()
    store.cache.get_versioned.side_effect = lambda gid, entry_type: (
        {"gid": gid} if gid in cached else None
    )
    store.put_batch_async = AsyncMock(return_value=None)

    client = MagicMock()
    client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

    warmer = HierarchyWarmer(
        store=store,
        client=client,
        project_gid="1143843662099250",
        entity_type="project",
        max_concurrent=max_concurrent,
        task_to_dict=lambda task: dict(task),
    )
    return warmer, store, client.tasks.get_async


def _df(parent_gids: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"parent_gid": parent_gids})


def _task(gid: str) -> dict[str, Any]:
    return {"gid": gid, "name": f"parent {gid}"}


async def _ok(gid: str, opt_fields: Any = None) -> dict[str, Any]:
    return _task(gid)


# ===========================================================================
# F-C3-01: the production call path into WarmerFloorGate.admit now EXISTS
# ===========================================================================


async def test_armed_warmer_lane_routes_every_get_through_admit(monkeypatch: Any) -> None:
    """GREEN: in the warmer lane + ARMED, every gap GET is admitted through the gate.

    This is the direct F-C3-01 falsification receipt: a spy on the gate proves the
    warm loop's outbound GETs pass through admit() -- the call site the custody
    census found had ZERO production callers.
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _WARMER_FUNCTION_NAME)
    spy = _SpyAllocator(enabled=True)
    set_budget_allocator(spy)

    gids = [str(1000 + i) for i in range(10)]
    warmer, store, get_async = _make_warmer(_ok)
    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 10
    assert get_async.await_count == 10  # every gap parent fetched
    assert spy.gate.admits == 10  # ...and every one passed through admit() FIRST
    assert spy.observed == [Lane.WARMER] * 10  # observe_admission wired (AC-2 site)
    assert spy.failopens == []  # no fault -> no fail-open tripwire


async def test_armed_warmer_lane_paces_sweep_at_floor_rate_end_to_end(
    monkeypatch: Any,
) -> None:
    """GREEN: the REAL WarmerFloorGate paces the production sweep at 110/60s.

    Uses the real BudgetAllocator with an in-silico clock (F-b: zero real sleeps):
    110 floor-paced GETs consume ~one 60s window, proving the floor's rate contract
    flows through the production warm loop -- not merely a no-op admit.
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _WARMER_FUNCTION_NAME)
    clock = _FakeClock()
    set_budget_allocator(
        BudgetAllocator(BudgetAllocatorConfig(enabled=True), clock=clock, sleep=clock.sleep)
    )

    n = 110
    gids = [str(2000 + i) for i in range(n)]
    warmer, _store, get_async = _make_warmer(_ok, max_concurrent=1)
    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == n
    assert get_async.await_count == n
    # 110 tokens earned at 110/60s from an empty bucket == ~60s of simulated pacing.
    assert clock.t == pytest.approx(n * 60 / 110, rel=0.02)


# ===========================================================================
# AC-4 (b'): per-chunk banking (kills factor 1, defuses the §3.3 inversion)
# ===========================================================================


async def test_armed_banks_each_chunk_mid_sweep(monkeypatch: Any) -> None:
    """GREEN: with the cure active, progress is banked PER CHUNK, not end-of-sweep.

    10 gids at chunk size 4 -> 3 chunks -> 3 durable banks (one per chunk),
    each carrying only its own chunk. This is the AC-4 (b') cadence change: a
    truncation now loses at most one chunk.
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _WARMER_FUNCTION_NAME)
    set_budget_allocator(_SpyAllocator(enabled=True))

    gids = [str(3000 + i) for i in range(10)]
    warmer, store, _get_async = _make_warmer(_ok)
    with patch.object(hw_module, "_GAP_WARM_CHUNK_SIZE", 4):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 10
    assert store.put_batch_async.await_count == 3  # one bank PER CHUNK (4, 4, 2)
    banked_sizes = [len(c.args[0]) for c in store.put_batch_async.await_args_list]
    assert banked_sizes == [4, 4, 2]
    all_banked = {t["gid"] for c in store.put_batch_async.await_args_list for t in c.args[0]}
    assert all_banked == set(gids)  # every parent durably banked, none dropped


async def test_armed_truncation_preserves_already_banked_chunks(monkeypatch: Any) -> None:
    """GREEN: a mid-sweep crash on a late chunk keeps the earlier chunks durable.

    Simulates the 900s Lambda-wall truncation the §3.3 inversion warns of: an
    unexpected fault while fetching chunk 3 sends the sweep to the BROAD-CATCH
    (return 0), but chunks 1+2 were ALREADY banked per-chunk before chunk 3 ran.
    Under the old single end-of-sweep banking this would forfeit everything.
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _WARMER_FUNCTION_NAME)
    set_budget_allocator(_SpyAllocator(enabled=True))

    gids = [str(4000 + i) for i in range(12)]  # 3 chunks of 4

    async def crash_on_chunk3(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == "4008":  # first gid of chunk 3
            raise ValueError("simulated Lambda-wall truncation mid-sweep")
        return _task(gid)

    warmer, store, _get_async = _make_warmer(crash_on_chunk3)
    with patch.object(hw_module, "_GAP_WARM_CHUNK_SIZE", 4):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    # The sweep truncates (BROAD-CATCH -> 0), but chunks 1+2 are already durable.
    assert warmed == 0
    assert store.put_batch_async.await_count == 2  # chunks 1 and 2 banked pre-crash
    survived = {t["gid"] for c in store.put_batch_async.await_args_list for t in c.args[0]}
    assert survived == {str(4000 + i) for i in range(8)}  # first 8 GIDs durable


# ===========================================================================
# Byte-identical-OFF: disabled and non-warmer-lane are the baseline exactly
# ===========================================================================


async def test_disabled_is_byte_identical_no_pacing_single_bank(monkeypatch: Any) -> None:
    """RED/disabled: ENABLED=false is byte-identical -- no admit, single bank.

    The disabled path reproduces exactly today's surface (ITEM-D): the gate is
    never touched and banking stays single end-of-sweep. The canary bites only if
    the disabled path had leaked pacing or per-chunk banking.
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _WARMER_FUNCTION_NAME)
    spy = _SpyAllocator(enabled=False)
    set_budget_allocator(spy)

    gids = [str(5000 + i) for i in range(10)]
    warmer, store, get_async = _make_warmer(_ok)
    with patch.object(hw_module, "_GAP_WARM_CHUNK_SIZE", 4):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 10
    assert get_async.await_count == 10
    assert spy.gate.admits == 0  # NO floor interposition on the Asana path
    assert spy.observed == []  # observe_admission never reached
    store.put_batch_async.assert_awaited_once()  # SINGLE end-of-sweep bank (baseline)
    assert len(store.put_batch_async.await_args.args[0]) == 10


async def test_enabled_but_not_warmer_lane_is_byte_identical(monkeypatch: Any) -> None:
    """ECS/near-zero lanes are NOT floor-throttled even when the knob is ARMED.

    Guards the stage-2 hazard: enabling the allocator in the ECS service (or a
    near-zero workflow Lambda) must NOT route its client-felt/fair-share gap-warm
    through the 110/60s warmer reservation (a ~30-min throttle). Lane gate: only
    the cache-warmer Lambdas claim the floor.
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _ECS_FUNCTION_NAME)  # armed, wrong lane
    spy = _SpyAllocator(enabled=True)
    set_budget_allocator(spy)

    gids = [str(6000 + i) for i in range(10)]
    warmer, store, get_async = _make_warmer(_ok)
    with patch.object(hw_module, "_GAP_WARM_CHUNK_SIZE", 4):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 10
    assert get_async.await_count == 10
    assert spy.gate.admits == 0  # armed, but NOT the warmer lane -> no floor pacing
    store.put_batch_async.assert_awaited_once()  # single end-of-sweep bank (baseline)


async def test_no_lambda_env_at_all_is_byte_identical(monkeypatch: Any) -> None:
    """The ECS service leaves AWS_LAMBDA_FUNCTION_NAME unset -> never warmer lane."""
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    spy = _SpyAllocator(enabled=True)
    set_budget_allocator(spy)

    gids = [str(7000 + i) for i in range(6)]
    warmer, store, _get_async = _make_warmer(_ok)
    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 6
    assert spy.gate.admits == 0
    store.put_batch_async.assert_awaited_once()


# ===========================================================================
# Fail-OPEN (pythia PC-3 / C-4): the limiter never blocks a warm sweep
# ===========================================================================


async def test_gate_construction_fault_fails_open(monkeypatch: Any) -> None:
    """An allocator-internal fault proceeds UN-paced and emits the tripwire.

    Fail-open is the whole point (C-4): a fail-closed limiter would worsen the
    storm the node-4 gate defeated. The sweep completes byte-identically (single
    bank) and budget_lane_failopen fires on the warmer lane.
    """
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", _WARMER_FUNCTION_NAME)
    spy = _SpyAllocator(enabled=True, raise_on_gate=True)
    set_budget_allocator(spy)

    gids = [str(8000 + i) for i in range(6)]
    warmer, store, get_async = _make_warmer(_ok)
    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 6  # sweep completed un-paced (fail-OPEN, not fail-closed)
    assert get_async.await_count == 6
    assert spy.gate.admits == 0  # gate never used
    assert spy.failopens == [Lane.WARMER]  # tripwire emitted on the warmer lane
    store.put_batch_async.assert_awaited_once()  # inert cadence -> single bank
