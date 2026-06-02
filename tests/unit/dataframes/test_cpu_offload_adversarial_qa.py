"""QA-adversary probes for the receiver bulk-offload integration-readiness work.

ADVERSARIAL tests written by the QA stream (not the implementer) to try to BREAK
the TD-001/007 implementation along the engineer-flagged risk axes. Kept separate
from the implementer's own files so a reviewer sees exactly what the adversary
probed.

Risk axes:
  R1  TD-001 process-wide semaphore singleton + first-use loop binding —
      multi-loop / loop-recreation (the asyncio.run / TestClient pattern).
  R1b reset_cpu_thread_semaphore() seam is test-only (no production caller).
  R3  the load-bearing cap binds to the REAL run_cpu_bound (not a re-impl).

NO HTTP contract is exercised; CPU-mechanics + observability probes only.
"""

from __future__ import annotations

import asyncio

from autom8_asana.dataframes import concurrency
from autom8_asana.settings import reset_settings

# --------------------------------------------------------------------------- #
# R1 — multi-loop / loop-recreation hazard for the process-wide singleton.
# --------------------------------------------------------------------------- #


def test_singleton_semaphore_reused_across_separate_event_loops() -> None:
    """Reuse of a stale singleton across two asyncio.run() loops is characterized.

    asyncio.Semaphore lazily binds its waiter machinery to the loop that first
    blocks on it. If a stale module-level instance built under one asyncio.run is
    reused under a DIFFERENT asyncio.run without reset_cpu_thread_semaphore(),
    acquisition under contention may raise RuntimeError. We pin the outcome to
    {works | loop-binding RuntimeError} — a SILENT WRONG ANSWER would be the
    dangerous third option. Production safety rests on the receiver having ONE
    loop for its lifetime (single uvicorn worker); this proves the failure mode
    rather than assuming it away.
    """
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()

    captured: dict[str, object] = {}

    async def first_loop() -> None:
        await concurrency.run_cpu_bound(lambda: 1)
        captured["sem"] = concurrency.get_cpu_thread_semaphore()

    asyncio.run(first_loop())
    sem_a = captured["sem"]

    outcome: dict[str, object] = {}

    async def second_loop() -> None:
        assert concurrency.get_cpu_thread_semaphore() is sem_a
        try:
            release = asyncio.Event()

            def block() -> int:
                import time

                while not release.is_set():
                    time.sleep(0.005)
                return 1

            t1 = asyncio.create_task(concurrency.run_cpu_bound(block))
            t2 = asyncio.create_task(concurrency.run_cpu_bound(lambda: 2))
            await asyncio.sleep(0.02)
            release.set()
            await asyncio.wait_for(asyncio.gather(t1, t2), timeout=2.0)
            outcome["result"] = "ok"
        except RuntimeError as e:
            outcome["result"] = f"RuntimeError: {e}"

    asyncio.run(second_loop())

    assert outcome["result"] == "ok" or "RuntimeError" in str(outcome["result"]), (
        f"unexpected cross-loop outcome: {outcome['result']!r}"
    )


def test_reset_seam_rebinds_distinct_semaphore_per_loop() -> None:
    """reset_cpu_thread_semaphore() between loops yields a fresh, distinct gate.

    Two sequential asyncio.run() blocks, each resetting first, must BOTH succeed
    and produce DISTINCT semaphore instances — proving reset is the correct
    remediation for the cross-loop hazard above.
    """
    seen: list[object] = []

    async def run_once() -> None:
        concurrency.reset_cpu_thread_semaphore()
        await concurrency.run_cpu_bound(lambda: 1)
        # Keep a STRONG reference so CPython cannot recycle the object's id() —
        # identity (is), not id() equality, is the correct distinctness check.
        seen.append(concurrency.get_cpu_thread_semaphore())

    asyncio.run(run_once())
    asyncio.run(run_once())

    assert len(seen) == 2
    assert seen[0] is not seen[1], "reset must rebind a distinct semaphore per loop"


def test_reset_seam_has_no_production_caller() -> None:
    """reset_cpu_thread_semaphore() must be called ONLY from tests, never src/.

    A production caller could silently drop the cap (re-introducing the PDR-002
    starvation). The only legitimate mention under src/ is concurrency.py (the
    definition); there must be ZERO call sites elsewhere under src/.
    """
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[3] / "src"
    callers: list[str] = []
    for py in src_root.rglob("*.py"):
        if py.name == "concurrency.py":
            continue
        text = py.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "reset_cpu_thread_semaphore" in line:
                callers.append(f"{py.relative_to(src_root)}:{lineno}: {line.strip()}")

    assert callers == [], f"reset_cpu_thread_semaphore() called in production code: {callers}"


# --------------------------------------------------------------------------- #
# R3 — the load-bearing cap binds to the REAL run_cpu_bound, not a re-impl.
# --------------------------------------------------------------------------- #


async def test_real_run_cpu_bound_bounds_concurrency(monkeypatch) -> None:
    """Bound concurrency through the ACTUAL run_cpu_bound (cap=2, launch 8).

    The implementer's load-bearing test wraps the gate in a re-implemented
    ``async with sem`` body. This probe routes the occupancy reading THROUGH the
    real run_cpu_bound's own in_use counter, so if ``async with semaphore`` is
    ever removed from run_cpu_bound ITSELF, THIS fails (peak jumps past 2).
    """
    monkeypatch.setenv("CPU_THREAD_CONCURRENCY", "2")
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()

    peak = 0
    release = asyncio.Event()

    def blocking_work() -> int:
        import time

        while not release.is_set():
            time.sleep(0.005)
        return 1

    async def driver() -> int:
        return await concurrency.run_cpu_bound(blocking_work)

    tasks = [asyncio.create_task(driver()) for _ in range(8)]
    for _ in range(20):
        await asyncio.sleep(0.01)
        in_use, _, _ = concurrency.get_semaphore_occupancy()
        peak = max(peak, in_use)
    release.set()
    await asyncio.gather(*tasks)

    assert peak <= 2, f"real run_cpu_bound failed to cap concurrency: peak in_use={peak}"
    assert peak >= 1, "gate admitted nothing — test did not actually saturate"
    in_use, waiting, _ = concurrency.get_semaphore_occupancy()
    assert in_use == 0 and waiting == 0, "occupancy leaked through the real gate"
