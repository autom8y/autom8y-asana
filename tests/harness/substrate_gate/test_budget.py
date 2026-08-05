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
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.errors import RateLimitError
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.rebuild import FetchedSections, PacedAsanaFetcher
from tests.harness.substrate_gate.budget import (
    PINNED_LEDGER_PATH,
    BudgetedPacedFetcher,
    BudgetLedgerCorrupt,
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


# ------------------------------------------- WU-2 close 3: multi-unit overshoot ---
def test_multi_unit_charge_never_overshoots_the_cap(tmp_path) -> None:
    """``consume(units)`` refuses BEFORE charging when ``current + units > cap``.

    The pre-fix check (``current >= cap``) let ``units>1`` overshoot by up to units-1;
    the fix pre-charges against the whole ``units`` and refuses with NO partial charge.
    """
    path = tmp_path / "b.json"
    ledger = PerDayBudgetLedger(path=path, cap=5, clock=_fixed_clock())
    assert ledger.consume(3) == 3  # 0 + 3 <= cap -> allowed

    with pytest.raises(ParityBudgetExhausted):
        ledger.consume(4)  # 3 + 4 = 7 > cap -> refuse (would overshoot by 2)
    assert ledger.count_today() == 3  # ledger UNCHANGED — not clamped to cap, no partial


def test_multi_unit_exact_fill_passes_then_next_refuses(tmp_path) -> None:
    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=5, clock=_fixed_clock())
    assert ledger.consume(5) == 5  # 0 + 5 == cap -> fills exactly, allowed
    with pytest.raises(ParityBudgetExhausted):
        ledger.consume(1)  # 5 + 1 > cap -> refuse
    assert ledger.count_today() == 5


def test_single_unit_boundary_unchanged_by_overshoot_fix(tmp_path) -> None:
    """Regression guard: ``current + 1 > cap`` is exactly the old ``current >= cap``."""
    ledger = PerDayBudgetLedger(path=tmp_path / "b.json", cap=1, clock=_fixed_clock())
    assert ledger.consume() == 1  # 0 + 1 == cap -> allowed
    with pytest.raises(ParityBudgetExhausted):
        ledger.consume()  # 1 + 1 > cap -> fires (== old current >= cap)


# ------------------------------------------ WU-2 close 1: corrupt-ledger refusal ---
def test_corrupt_json_refuses_loudly_not_silent_reset(tmp_path) -> None:
    """A tampered/corrupt ledger must REFUSE loudly, never fail-open to a 0 count."""
    path = tmp_path / "b.json"
    path.write_text("{ this is not valid json ]", encoding="utf-8")
    ledger = PerDayBudgetLedger(path=path, cap=5, clock=_fixed_clock())

    with pytest.raises(BudgetLedgerCorrupt):
        ledger.count_today()  # the read path refuses (no silent reset-to-zero)
    with pytest.raises(BudgetLedgerCorrupt):
        ledger.consume()  # and the charge path refuses too


def test_valid_json_but_non_dict_refuses_loudly(tmp_path) -> None:
    path = tmp_path / "b.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")  # valid JSON, wrong shape
    ledger = PerDayBudgetLedger(path=path, cap=5, clock=_fixed_clock())
    with pytest.raises(BudgetLedgerCorrupt):
        ledger.count_today()


def test_non_integer_day_count_refuses_loudly(tmp_path) -> None:
    path = tmp_path / "b.json"
    path.write_text('{"2026-07-30": "banana"}', encoding="utf-8")  # dict, non-int value
    ledger = PerDayBudgetLedger(path=path, cap=5, clock=_fixed_clock())
    with pytest.raises(BudgetLedgerCorrupt):
        ledger.count_today()


def test_missing_file_is_a_legitimate_empty_ledger(tmp_path) -> None:
    """A MISSING file is first-run, not corrupt: count 0, charging proceeds."""
    ledger = PerDayBudgetLedger(path=tmp_path / "nope.json", cap=5, clock=_fixed_clock())
    assert ledger.count_today() == 0
    assert ledger.consume() == 1


def test_loud_refusals_are_plain_runtime_errors_non_transient() -> None:
    """Both loud stops are plain RuntimeErrors so ``core.retry`` treats them non-transient."""
    assert issubclass(BudgetLedgerCorrupt, RuntimeError)
    assert issubclass(ParityBudgetExhausted, RuntimeError)


# ------------------------------------------ WU-2 close 2: cross-process lock race ---
# Loads budget.py STANDALONE by file path (its runtime imports are pure stdlib; the
# autom8_asana imports are TYPE_CHECKING-only) — so the child pays no package/harness
# import cost and needs no autom8_asana on the path.
_RACE_CHILD = """
import importlib.util, os, sys
from datetime import datetime, UTC
from pathlib import Path

spec = importlib.util.spec_from_file_location("_budget_under_race", os.environ["BUDGET_PY"])
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)

ledger = budget.PerDayBudgetLedger(
    path=Path(os.environ["LEDGER_PATH"]),
    cap=int(os.environ["LEDGER_CAP"]),
    clock=lambda: datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
)
charged = 0
for _ in range(int(os.environ["LEDGER_ATTEMPTS"])):
    try:
        ledger.consume()
        charged += 1
    except budget.ParityBudgetExhausted:
        break
sys.stdout.write(str(charged))
"""


def test_cross_process_contention_never_exceeds_cap(tmp_path) -> None:
    """N real processes racing consume() near the cap must never JOINTLY exceed it.

    Without the flock, two processes both read ``N < cap`` and both write ``N+1`` (lost
    update): more than ``cap`` consumes succeed while the file value (last-writer-wins)
    HIDES the overshoot. We therefore sum the per-process SUCCESS counts and assert the
    sum is exactly the cap — the file value alone could not catch the bug.
    """
    budget_py = Path(__file__).resolve().parent / "budget.py"
    ledger_path = tmp_path / "race.json"
    cap = 40
    n_procs = 6
    attempts = cap + 5  # each child alone could exhaust the whole budget, then stop

    child_env = {
        **os.environ,
        "BUDGET_PY": str(budget_py),
        "LEDGER_PATH": str(ledger_path),
        "LEDGER_CAP": str(cap),
        "LEDGER_ATTEMPTS": str(attempts),
    }

    procs = [
        subprocess.Popen(  # noqa: S603 — fixed argv (sys.executable + inline snippet), no shell
            [sys.executable, "-c", _RACE_CHILD],
            env=child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(n_procs)
    ]

    charged_counts: list[int] = []
    for proc in procs:
        out, err = proc.communicate(timeout=45)
        assert proc.returncode == 0, f"race child failed (rc={proc.returncode}): {err}"
        charged_counts.append(int(out.strip()))

    total_charged = sum(charged_counts)
    assert total_charged == cap, (
        f"cross-process overshoot: {n_procs} procs jointly charged {total_charged} "
        f"successful consumes against cap={cap} (per-proc {charged_counts})"
    )

    # The durable ledger agrees exactly — no torn/lost write left it above cap.
    parent = PerDayBudgetLedger(path=ledger_path, cap=cap, clock=_fixed_clock())
    assert parent.count_today() == cap


# ---------------------------------------------- WU-2 exit bar: pinned ledger path ---
def test_pinned_ledger_path_is_durable_repo_relative_and_year_templated() -> None:
    """The production pin is repo-relative, durable (not /tmp, not scratchpad), templated."""
    assert PINNED_LEDGER_PATH == ".sos/wip/parity/budget-ledger-{year}.json"
    assert not PINNED_LEDGER_PATH.startswith("/")  # repo-relative, not absolute
    assert "/tmp" not in PINNED_LEDGER_PATH  # survives reboot
    assert "scratchpad" not in PINNED_LEDGER_PATH  # survives park-per-day
    # WU-3 resolves the {year} template into a concrete path at arming time.
    resolved = PINNED_LEDGER_PATH.format(year=2026)
    assert resolved == ".sos/wip/parity/budget-ledger-2026.json"


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
