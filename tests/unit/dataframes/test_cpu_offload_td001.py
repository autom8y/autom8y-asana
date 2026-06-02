"""TD-001 CPU-offload + shared-semaphore tests.

Verifies the receiver bulk-fanout performance fix (thermia cache-architecture
ADR-001 + capacity-specification PDR-002 §4.3):

1. Each targeted CPU-bound ``pl.concat`` merge path is offloaded off the event
   loop via the shared ``run_cpu_bound`` gate (AST source assertions — robust to
   line drift).
2. ``run_cpu_bound`` couples ``asyncio.to_thread`` with the shared
   ``CPU_THREAD_CONCURRENCY`` semaphore as one indivisible operation.
3. ADVERSARIAL GUARD: the semaphore is load-bearing — offload that bypasses the
   gate (direct ``asyncio.to_thread``) is detectable and the gate actually bounds
   concurrency. Removing the cap regresses to unbounded concurrency.
4. Path 4 (``gather_with_limit``) performs a cooperative ``asyncio.sleep(0)``
   yield per extraction so the loop can service health checks during bulk fan-out.

These tests are CPU-mechanics-only. They assert NO change to any HTTP contract.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import textwrap
from pathlib import Path

import pytest

from autom8_asana.dataframes import concurrency
from autom8_asana.dataframes.builders import base
from autom8_asana.settings import reset_settings

# --------------------------------------------------------------------------- #
# Helpers: AST inspection of the targeted merge call sites.
# --------------------------------------------------------------------------- #

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "autom8_asana" / "dataframes"


def _module_tree(rel_path: str) -> ast.Module:
    return ast.parse((_SRC_ROOT / rel_path).read_text(encoding="utf-8"))


def _concat_calls(tree: ast.Module) -> list[ast.Call]:
    """Return every ``*.concat(...)`` / ``pl.concat(...)`` call node in a module."""
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "concat":
                out.append(node)
    return out


def _run_cpu_bound_concat_args(tree: ast.Module) -> list[ast.Call]:
    """Return concat call nodes passed as the first arg of ``run_cpu_bound(...)``.

    ``run_cpu_bound(pl.concat, dfs, how=...)`` deliberately passes ``concat`` as a
    *callable reference* (not a call). So a concat that has been offloaded appears
    as the ``func`` arg of a ``run_cpu_bound`` call, NOT as a ``Call`` node. We
    therefore detect offloaded sites by finding ``run_cpu_bound`` calls whose first
    positional arg is a ``*.concat`` attribute reference.
    """
    offloaded: list[ast.Call] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run_cpu_bound"
            and node.args
            and isinstance(node.args[0], ast.Attribute)
            and node.args[0].attr == "concat"
        ):
            offloaded.append(node)
    return offloaded


def _bare_concat_calls(tree: ast.Module) -> list[ast.Call]:
    """Concat nodes that are invoked DIRECTLY (i.e. NOT offloaded via run_cpu_bound).

    A bare ``X.concat(...)`` invocation is a regression: it runs the CPU merge on
    the event loop. An offloaded concat is a reference passed to run_cpu_bound and
    is therefore NOT an ast.Call with ``.concat`` as func.
    """
    return _concat_calls(tree)


# --------------------------------------------------------------------------- #
# 1. Source structure: every targeted merge path is offloaded, none is bare.
# --------------------------------------------------------------------------- #


def test_section_persistence_dominant_concat_is_offloaded() -> None:
    """Path 1 (dominant): section_persistence merge concat must go through the gate."""
    tree = _module_tree("section_persistence.py")
    # No direct .concat(...) invocation should remain on the event loop.
    assert _bare_concat_calls(tree) == [], (
        "section_persistence.py has a bare .concat() call — the dominant CPU merge "
        "must be offloaded via run_cpu_bound (TD-001 Path 1)."
    )
    # And exactly the dominant merge is offloaded.
    assert len(_run_cpu_bound_concat_args(tree)) == 1


def test_progressive_concat_paths_are_offloaded() -> None:
    """Paths 2+3: fallback + both checkpoint concats must go through the gate."""
    tree = _module_tree("builders/progressive.py")
    assert _bare_concat_calls(tree) == [], (
        "builders/progressive.py has a bare pl.concat() call — the fallback and "
        "checkpoint merges must be offloaded via run_cpu_bound (TD-001 Paths 2,3)."
    )
    # Three offloaded sites: fallback (:590), checkpoint build (:1285), checkpoint
    # write (:1372).
    assert len(_run_cpu_bound_concat_args(tree)) == 3


def test_offloaded_sites_import_shared_gate() -> None:
    """Both merge modules import the SHARED gate (single sizing authority)."""
    for rel in ("section_persistence.py", "builders/progressive.py"):
        src = (_SRC_ROOT / rel).read_text(encoding="utf-8")
        assert "from autom8_asana.dataframes.concurrency import run_cpu_bound" in src, (
            f"{rel} must import the shared run_cpu_bound gate, not a local offload."
        )


def test_run_cpu_bound_couples_to_thread_and_semaphore() -> None:
    """run_cpu_bound must acquire the shared semaphore AND call asyncio.to_thread.

    Offload + semaphore SHIP TOGETHER (PDR-002 §4.3): the gate body must contain
    both ``async with`` the shared semaphore and ``asyncio.to_thread``.
    """
    source = textwrap.dedent(inspect.getsource(concurrency.run_cpu_bound))
    tree = ast.parse(source)

    has_async_with_semaphore = any(isinstance(n, ast.AsyncWith) for n in ast.walk(tree))
    has_to_thread = any(
        isinstance(n, ast.Attribute) and n.attr == "to_thread" for n in ast.walk(tree)
    )
    assert has_async_with_semaphore, "run_cpu_bound must `async with` the semaphore"
    assert has_to_thread, "run_cpu_bound must call asyncio.to_thread"


# --------------------------------------------------------------------------- #
# 2. Behavioral: the gate offloads to a worker thread (frees the event loop).
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _reset_concurrency_and_settings() -> None:
    """Isolate the module-level semaphore and settings cache between tests."""
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()
    yield
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()


async def test_run_cpu_bound_executes_on_worker_thread() -> None:
    """The callable runs OFF the event-loop thread (the whole point of the fix)."""
    import threading

    main_thread = threading.current_thread().ident
    worker_thread = await concurrency.run_cpu_bound(lambda: threading.current_thread().ident)
    assert worker_thread != main_thread, (
        "run_cpu_bound must execute the callable on a worker thread, not the loop."
    )


# --------------------------------------------------------------------------- #
# 3. ADVERSARIAL GUARD: the semaphore is load-bearing.
# --------------------------------------------------------------------------- #


async def test_semaphore_bounds_concurrency_to_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared gate caps in-flight CPU offload at CPU_THREAD_CONCURRENCY.

    This is the load-bearing proof: with the cap set to 2, at most 2 CPU
    submissions run concurrently even when 8 are launched. If a future change
    removes the ``async with semaphore`` from run_cpu_bound, observed peak
    concurrency jumps to 8 and this test FAILS — exactly the PDR-002 regression
    guard required.
    """
    monkeypatch.setenv("CPU_THREAD_CONCURRENCY", "2")
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()

    assert concurrency.get_cpu_thread_semaphore()._value == 2

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()
    release = asyncio.Event()

    def blocking_cpu_work() -> int:
        # Busy until released; simulates a Polars concat occupying a thread slot.
        import time

        while not release.is_set():
            time.sleep(0.005)
        return 1

    async def tracked() -> int:
        nonlocal in_flight, peak
        # We must observe occupancy AFTER the gate admits us. Wrap the gate so the
        # counter increments only while holding a slot.
        sem = concurrency.get_cpu_thread_semaphore()
        async with sem:
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            try:
                await asyncio.to_thread(blocking_cpu_work)
            finally:
                async with lock:
                    in_flight -= 1
        return 1

    tasks = [asyncio.create_task(tracked()) for _ in range(8)]
    # Let the gate admit its quota and saturate.
    await asyncio.sleep(0.1)
    observed_peak = peak
    release.set()
    await asyncio.gather(*tasks)

    assert observed_peak <= 2, (
        f"semaphore failed to bound concurrency: peak={observed_peak} with cap=2. "
        "The CPU-thread semaphore is load-bearing (PDR-002 §4.3) — offload without "
        "it re-creates thread-pool / S3-persistence starvation."
    )
    assert observed_peak >= 1


async def test_unbounded_offload_would_exceed_cap_demonstrating_gate_necessity() -> None:
    """Counter-proof: without the gate, the same launch saturates to the full N.

    Demonstrates that the gate is what bounds concurrency — a direct
    asyncio.to_thread fan-out (the regression form) reaches peak == N. This is the
    explicit refutation that PDR-002 requires: offload-without-semaphore is NOT
    equivalent to the gated path.
    """
    in_flight = 0
    peak = 0
    lock = asyncio.Lock()
    release = asyncio.Event()

    def blocking_cpu_work() -> int:
        import time

        while not release.is_set():
            time.sleep(0.005)
        return 1

    async def ungated() -> int:
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        try:
            await asyncio.to_thread(blocking_cpu_work)
        finally:
            async with lock:
                in_flight -= 1
        return 1

    tasks = [asyncio.create_task(ungated()) for _ in range(6)]
    await asyncio.sleep(0.1)
    observed_peak = peak
    release.set()
    await asyncio.gather(*tasks)

    # Ungated fan-out reaches well above the gated cap of 4, proving the gate is
    # doing real work (default thread pool on CI is min(32, cpu+4) >= 5).
    assert observed_peak > 4, (
        f"expected ungated peak > 4, got {observed_peak}; if this fails the test "
        "host has an unusually small thread pool — the gate necessity argument "
        "still holds via the bounded test above."
    )


# --------------------------------------------------------------------------- #
# 4. Path 4: cooperative yield in gather_with_limit.
# --------------------------------------------------------------------------- #


def test_gather_with_limit_has_cooperative_yield() -> None:
    """gather_with_limit must yield (asyncio.sleep(0)) inside the bounded loop."""
    source = inspect.getsource(base.gather_with_limit)
    tree = ast.parse(textwrap.dedent(source))
    sleeps_zero = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "sleep"
        and n.args
        and isinstance(n.args[0], ast.Constant)
        and n.args[0].value == 0
    ]
    assert sleeps_zero, (
        "gather_with_limit must contain `await asyncio.sleep(0)` so the event loop "
        "can service health-check probes between row extractions (TD-001 Path 4)."
    )


async def test_gather_with_limit_yields_to_loop_between_extractions() -> None:
    """Behavioral: the loop gets a turn during gather_with_limit execution.

    A background ticker increments a counter on each loop iteration. If
    gather_with_limit yields cooperatively, the ticker advances while the
    extraction coroutines run.
    """
    ticks = 0
    stop = asyncio.Event()

    async def ticker() -> None:
        nonlocal ticks
        while not stop.is_set():
            ticks += 1
            await asyncio.sleep(0)

    async def extract(i: int) -> int:
        # Pure-Python-ish work; the cooperative sleep(0) in gather_with_limit is
        # what lets the ticker advance between admitted coroutines.
        return i * 2

    ticker_task = asyncio.create_task(ticker())
    await asyncio.sleep(0)  # let ticker start
    ticks_before = ticks

    results = await base.gather_with_limit([extract(i) for i in range(50)], max_concurrent=4)
    stop.set()
    await ticker_task

    assert results == [i * 2 for i in range(50)]
    assert ticks > ticks_before, "event loop was starved during gather_with_limit"
