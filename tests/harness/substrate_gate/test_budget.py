"""Per-day P10 budget + process-singleton fetcher tests (S8-0 · REQUIREMENTS 2 & 3).

Covers: the cap boundary (cap-1 passes, cap fires), cross-invocation durability (a
fresh ledger over the same path continues the day's count), attempts-count-on-429
(the charge lands BEFORE the outbound, so a 429'd attempt still spent its unit), the
``PacedAsanaFetcher`` Protocol conformance of the budget wrapper, the at-cap
short-circuit (inner never runs), the process-singleton fetcher (idempotent), and the
real wiring of the budget through the parity source's fetch path.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import polars as pl
import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.errors import RateLimitError
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.rebuild import FetchedSections, PacedAsanaFetcher
from tests.harness.substrate_gate.budget import (
    BudgetedPacedFetcher,
    ParityBudgetExhausted,
    PerDayBudgetLedger,
)
from tests.harness.substrate_gate.parity import (
    PacedLiveParitySource,
    ParityObservation,
    get_process_fetcher,
    reset_process_fetcher,
)

_DAY = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def _fixed_clock(moment: datetime = _DAY):
    return lambda: moment


def _aid() -> ArtifactId:
    return ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)


def _empty_sections() -> FetchedSections:
    return FetchedSections(
        frame=pl.DataFrame(), section_instants={}, requested_sections=frozenset()
    )


# --------------------------------------------------------------- ledger core ---
def test_cap_boundary_cap_minus_one_passes_cap_fires(tmp_path) -> None:
    ledger = PerDayBudgetLedger(path=tmp_path / "budget.json", cap=2, clock=_fixed_clock())

    assert ledger.consume() == 1  # current 0 (< cap) -> 1
    assert ledger.consume() == 2  # current 1 (== cap-1) -> 2  ("cap-1 passes")
    with pytest.raises(ParityBudgetExhausted):
        ledger.consume()  # current 2 (== cap) -> fires  ("cap fires")
    assert ledger.count_today() == 2  # the refused charge did not proceed


def test_cross_invocation_durability(tmp_path) -> None:
    path = tmp_path / "budget.json"
    first = PerDayBudgetLedger(path=path, cap=5, clock=_fixed_clock())
    first.consume()
    first.consume()

    # A FRESH instance over the SAME path continues the same day's count.
    second = PerDayBudgetLedger(path=path, cap=5, clock=_fixed_clock())
    assert second.count_today() == 2
    assert second.consume() == 3

    # And it is genuinely persisted, keyed by the UTC day.
    on_disk = json.loads(path.read_text())
    assert on_disk == {"2026-07-30": 3}


def test_next_day_resets_the_count(tmp_path) -> None:
    path = tmp_path / "budget.json"
    day_one = PerDayBudgetLedger(path=path, cap=2, clock=_fixed_clock(_DAY))
    day_one.consume()
    day_one.consume()
    with pytest.raises(ParityBudgetExhausted):
        day_one.consume()

    tomorrow = _DAY.replace(day=31)
    day_two = PerDayBudgetLedger(path=path, cap=2, clock=_fixed_clock(tomorrow))
    assert day_two.count_today() == 0  # new day, fresh budget
    assert day_two.consume() == 1


# ------------------------------------------------------ budgeted paced fetcher ---
class _OkInner:
    """A minimal ``PacedAsanaFetcher`` that records its calls and returns empty sections."""

    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        self.calls += 1
        return _empty_sections()


class _RateLimitedInner:
    """A ``PacedAsanaFetcher`` whose every attempt 429s AFTER being invoked."""

    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, aid: ArtifactId) -> FetchedSections:
        self.calls += 1
        raise RateLimitError("inner fetch 429", retry_after=1)


def _requires_paced_asana_fetcher(fetcher: PacedAsanaFetcher) -> PacedAsanaFetcher:
    """Static conformance gate: only a ``PacedAsanaFetcher`` type-checks as an argument."""
    return fetcher


def test_budgeted_fetcher_satisfies_paced_asana_fetcher_protocol(tmp_path) -> None:
    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=3, clock=_fixed_clock())
    wrapper = BudgetedPacedFetcher(_OkInner(), ledger)
    # Structural + static conformance to the FROZEN Seam-3 Protocol.
    assert _requires_paced_asana_fetcher(wrapper) is wrapper
    assert hasattr(wrapper, "fetch")


def test_budgeted_fetch_consumes_then_delegates(tmp_path) -> None:
    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=3, clock=_fixed_clock())
    inner = _OkInner()
    wrapper = BudgetedPacedFetcher(inner, ledger)

    result = asyncio.run(wrapper.fetch(_aid()))

    assert isinstance(result, FetchedSections)
    assert inner.calls == 1
    assert ledger.count_today() == 1  # the attempt was charged


def test_attempt_counts_even_when_inner_429s(tmp_path) -> None:
    """attempts-count-on-429: the charge lands BEFORE the outbound, so a 429 still spent it."""
    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=3, clock=_fixed_clock())
    inner = _RateLimitedInner()
    wrapper = BudgetedPacedFetcher(inner, ledger)

    with pytest.raises(RateLimitError):
        asyncio.run(wrapper.fetch(_aid()))

    assert inner.calls == 1
    assert ledger.count_today() == 1  # charged despite the 429


def test_at_cap_raises_before_inner_runs(tmp_path) -> None:
    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=1, clock=_fixed_clock())
    ledger.consume()  # exhaust the day
    inner = _OkInner()
    wrapper = BudgetedPacedFetcher(inner, ledger)

    with pytest.raises(ParityBudgetExhausted):
        asyncio.run(wrapper.fetch(_aid()))
    assert inner.calls == 0  # the outbound never ran — halted loudly at the gate


# ----------------------------------------------------- process-singleton fetcher ---
def test_get_process_fetcher_is_idempotent() -> None:
    reset_process_fetcher()
    try:
        first = get_process_fetcher()
        second = get_process_fetcher()
        assert first is second  # ONE shared K>1 in-flight ceiling guard per process
        assert first.armed is False  # constructed DARK
    finally:
        reset_process_fetcher()


# ---------------------------------------------------- budget wired into parity ---
class _FastClock:
    def __init__(self) -> None:
        self._t = 0.0

    def __call__(self) -> float:
        self._t += 100.0
        return self._t


async def _no_sleep(_seconds: float) -> None:
    return None


def _armed_source(outbound, ledger: PerDayBudgetLedger) -> PacedLiveParitySource:
    return PacedLiveParitySource(
        armed=True,
        outbound=outbound,
        gate_clock=_FastClock(),
        gate_sleep=_no_sleep,
        budget=ledger,
    )


def test_parity_source_routes_each_attempt_through_the_budget(tmp_path) -> None:
    from tests.harness.substrate_gate.exemplars import exemplar_one_observation

    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=5, clock=_fixed_clock())

    async def _ok(_aid_: ArtifactId) -> ParityObservation:
        return exemplar_one_observation()

    source = _armed_source(_ok, ledger)
    asyncio.run(source.fetch_all_paced([_aid()]))
    assert ledger.count_today() == 1  # the single attempt charged the day


def test_parity_source_halts_loudly_at_cap(tmp_path) -> None:
    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=1, clock=_fixed_clock())
    ledger.consume()  # exhaust the day before the run

    ran: list[str] = []

    async def _ok(aid: ArtifactId) -> ParityObservation:
        ran.append(aid.project_gid)
        from tests.harness.substrate_gate.exemplars import exemplar_one_observation

        return exemplar_one_observation()

    source = _armed_source(_ok, ledger)
    with pytest.raises(ParityBudgetExhausted):
        asyncio.run(source.fetch_all_paced([_aid()]))
    assert ran == []  # the outbound never ran — budget halted the parity fan-out
