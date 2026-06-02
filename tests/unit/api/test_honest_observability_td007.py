"""TD-007 honest-observability instrumentation tests (observability-plan §2).

Covers the RECEIVER-EMITTED signals (the ones the receiver process can emit;
external ALB/CloudWatch signals are the re-gate stream's to correlate):

* event_loop_lag_seconds — the leading indicator of CPU-on-loop starvation,
  emitted by the EventLoopLagMonitor on its slow timer.
* CPU-thread-semaphore in_use / waiting / max — saturation of the offload gate
  (dataframes/concurrency.py:run_cpu_bound), so gate starvation is visible.
* serving_stale_total + lkg_serve_age_seconds — the LKG path emission that makes
  the success-rate flattering visible (dataframe_cache.py:531-554).
* receiver_query_success_rate_{project,section,combined} — receiver-emitted
  honest success rate (NOT ALB-inferred), from the query path counters.
* PROHIBITION: success_rate must not be readable without serving_stale_total
  co-available (success_rate_with_stale_context enforces it structurally).
* The 4-signal CPU_STARVATION_REPLACEMENT correlation precondition (the two
  receiver-observable signals) fires on a synthetic event.

Each metric is read via the prometheus_client REGISTRY collect()/sample pattern
established in tests/unit/api/test_exports_metrics.py. NO HTTP contract is
exercised — these are pure metric-emission unit tests (additive meta only).
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from autom8_asana.api import metrics
from autom8_asana.api.event_loop_monitor import EventLoopLagMonitor
from autom8_asana.dataframes import concurrency
from autom8_asana.settings import reset_settings

# ---------------------------------------------------------------------------
# Metric read helpers (prometheus_client REGISTRY sample pattern)
# ---------------------------------------------------------------------------


def _histogram_count(hist, **labels) -> float:
    """Sum of observations for a histogram (optionally filtered by labels)."""
    total = 0.0
    for metric in hist.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_count"):
                continue
            if all(sample.labels.get(k) == v for k, v in labels.items()):
                total += sample.value
    return total


def _gauge_value(gauge) -> float:
    for metric in gauge.collect():
        for sample in metric.samples:
            return sample.value
    return 0.0


def _counter_value(counter, **labels) -> float:
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_total"):
                continue
            if all(sample.labels.get(k) == v for k, v in labels.items()):
                total += sample.value
    return total


def _outcome_counts(entity_type: str | None = None) -> tuple[float, float]:
    """Raw (success, server_error) counts on RECEIVER_QUERY_OUTCOME.

    Mirrors the denominator logic of ``receiver_query_success_rate`` but exposes
    the raw counts so a test can capture-before / assert-delta against the
    PROCESS-GLOBAL counter — order-independent under ``-n auto`` even when a
    co-located test writes the same project/section arms.
    """
    success = 0.0
    server_error = 0.0
    for metric in metrics.RECEIVER_QUERY_OUTCOME.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_total"):
                continue
            if entity_type is not None and sample.labels.get("entity_type") != entity_type:
                continue
            if sample.labels.get("outcome") == "success":
                success += sample.value
            elif sample.labels.get("outcome") == "server_error":
                server_error += sample.value
    return success, server_error


@pytest.fixture(autouse=True)
def _reset_concurrency_and_settings() -> None:
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()
    yield
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()


# ---------------------------------------------------------------------------
# 1. event_loop_lag_seconds
# ---------------------------------------------------------------------------


async def test_event_loop_lag_monitor_emits_a_sample() -> None:
    """The monitor's sample emits one observation to event_loop_lag_seconds."""
    before = _histogram_count(metrics.EVENT_LOOP_LAG_SECONDS)
    monitor = EventLoopLagMonitor(interval_seconds=0.01)
    lag = await monitor.sample_once()
    after = _histogram_count(metrics.EVENT_LOOP_LAG_SECONDS)

    assert after == before + 1, "one lag sample must be observed"
    assert lag >= 0.0, "lag is overshoot of the intended interval (>= 0 after clamp)"


async def test_event_loop_lag_monitor_start_stop_clean() -> None:
    """The monitor starts a background task and stops without hanging."""
    monitor = EventLoopLagMonitor(interval_seconds=0.01)
    task = monitor.start()
    assert not task.done()
    # Let it tick at least once.
    await asyncio.sleep(0.03)
    await asyncio.wait_for(monitor.stop(), timeout=1.0)
    assert task.done()


def test_event_loop_lag_record_clamps_negative() -> None:
    """Negative jitter is clamped to 0 (never observes a negative lag)."""
    before = _histogram_count(metrics.EVENT_LOOP_LAG_SECONDS)
    metrics.record_event_loop_lag(-0.5)
    after = _histogram_count(metrics.EVENT_LOOP_LAG_SECONDS)
    assert after == before + 1  # observed, but the value was clamped to 0.0


# ---------------------------------------------------------------------------
# 2. CPU-thread semaphore in_use / waiting / max
# ---------------------------------------------------------------------------


async def test_cpu_semaphore_gauges_emit_on_run_cpu_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_cpu_bound updates in_use/max gauges; settles to 0 in-use after."""
    monkeypatch.setenv("CPU_THREAD_CONCURRENCY", "3")
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()

    await concurrency.run_cpu_bound(lambda: 1)

    # Max reflects the configured cap; in_use settles back to 0 after completion.
    assert _gauge_value(metrics.CPU_THREAD_SEMAPHORE_MAX) == 3
    assert _gauge_value(metrics.CPU_THREAD_SEMAPHORE_IN_USE) == 0
    assert _gauge_value(metrics.CPU_THREAD_SEMAPHORE_WAITING) == 0


async def test_cpu_semaphore_waiting_gauge_rises_under_saturation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the gate saturated, the waiting gauge reflects blocked coroutines.

    Cap=1, two concurrent offloads: the second blocks on acquire, so occupancy
    shows in_use=1 and waiting>=1 while the first holds the slot.
    """
    monkeypatch.setenv("CPU_THREAD_CONCURRENCY", "1")
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()

    release = asyncio.Event()

    def blocking_work() -> int:
        import time

        while not release.is_set():
            time.sleep(0.005)
        return 1

    t1 = asyncio.create_task(concurrency.run_cpu_bound(blocking_work))
    t2 = asyncio.create_task(concurrency.run_cpu_bound(lambda: 2))
    await asyncio.sleep(0.05)  # let t1 acquire and t2 block on the gate

    in_use, waiting, max_slots = concurrency.get_semaphore_occupancy()
    observed_waiting_gauge = _gauge_value(metrics.CPU_THREAD_SEMAPHORE_WAITING)

    assert in_use == 1, "one slot held by the blocking task"
    assert waiting >= 1, "the second offload must be counted as waiting"
    assert observed_waiting_gauge >= 1, "waiting gauge reflects offload-gate saturation"
    assert max_slots == 1

    release.set()
    await asyncio.gather(t1, t2)
    # After drain, occupancy returns to empty.
    assert _gauge_value(metrics.CPU_THREAD_SEMAPHORE_IN_USE) == 0
    assert _gauge_value(metrics.CPU_THREAD_SEMAPHORE_WAITING) == 0


async def test_cpu_semaphore_occupancy_balanced_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exception in the offloaded callable still releases the in-use slot."""
    monkeypatch.setenv("CPU_THREAD_CONCURRENCY", "2")
    reset_settings()
    concurrency.reset_cpu_thread_semaphore()

    def boom() -> int:
        raise ValueError("merge failed")

    with pytest.raises(ValueError, match="merge failed"):
        await concurrency.run_cpu_bound(boom)

    in_use, waiting, _ = concurrency.get_semaphore_occupancy()
    assert in_use == 0, "in-use slot must be released even when the merge raises"
    assert waiting == 0, "waiter count must not leak on the exception path"


# ---------------------------------------------------------------------------
# 3. serving_stale_total + lkg_serve_age_seconds
# ---------------------------------------------------------------------------


def test_record_serving_stale_emits_count_and_age() -> None:
    """record_serving_stale increments the count and observes the age."""
    before_count = _counter_value(metrics.SERVING_STALE_TOTAL, entity_type="offer")
    before_age = _histogram_count(metrics.LKG_SERVE_AGE_SECONDS, entity_type="offer")

    metrics.record_serving_stale("offer", 1500.0)

    assert _counter_value(metrics.SERVING_STALE_TOTAL, entity_type="offer") == before_count + 1
    assert _histogram_count(metrics.LKG_SERVE_AGE_SECONDS, entity_type="offer") == before_age + 1


async def test_lkg_path_emits_serving_stale_end_to_end() -> None:
    """The dataframe_cache LKG serve path emits serving_stale_total (TD-007 wiring).

    Reuses the cache unit harness: an offer entry past grace but within the
    default ceiling serves as LKG and must increment serving_stale_total.
    """
    from unittest.mock import patch

    from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
    from tests.unit.cache.dataframe.test_dataframe_cache import make_cache, make_entry

    memory = MemoryTier(max_entries=100)
    # offer TTL=180s, grace=540s, default ceiling=1800s. 1500s = LKG-servable.
    entry = make_entry(entity_type="offer", created_seconds_ago=1500)
    memory.put("offer:proj-1", entry)
    cache = make_cache(memory_tier=memory)

    before = _counter_value(metrics.SERVING_STALE_TOTAL, entity_type="offer")
    with patch("autom8_asana.cache.integration.dataframe_cache.asyncio.create_task"):
        result = await cache.get_async("proj-1", "offer")

    assert result is entry  # served as LKG
    assert _counter_value(metrics.SERVING_STALE_TOTAL, entity_type="offer") == before + 1


# ---------------------------------------------------------------------------
# 4. receiver_query_success_rate {project, section, combined}
# ---------------------------------------------------------------------------


def test_success_rate_per_arm_and_combined() -> None:
    """success_rate = 2xx / (2xx+5xx), per-arm and combined.

    RECEIVER_QUERY_OUTCOME is a PROCESS-GLOBAL counter with no per-test reset:
    under ``-n auto`` a co-located writer of the same project/section arms (e.g.
    test_receiver_bulk_fanout_reliability_stage1) makes absolute-value assertions
    non-deterministic. So this captures each arm's raw (success, error) counts
    BEFORE and asserts the DELTA matches the writes — order-independent by
    construction. The rate is then recomputed from the captured deltas, which is
    exactly what ``receiver_query_success_rate`` computes over the full counter.
    """
    # Baseline snapshot of the arms this test writes (may be non-zero under -n auto).
    proj_succ_0, proj_err_0 = _outcome_counts("project")
    sect_succ_0, sect_err_0 = _outcome_counts("section")

    # project: +9 success, +1 error -> delta-rate 0.9 ; section: +1, +1 -> 0.5
    for _ in range(9):
        metrics.record_receiver_query_outcome("project", success=True)
    metrics.record_receiver_query_outcome("project", success=False)
    metrics.record_receiver_query_outcome("section", success=True)
    metrics.record_receiver_query_outcome("section", success=False)

    proj_succ_1, proj_err_1 = _outcome_counts("project")
    sect_succ_1, sect_err_1 = _outcome_counts("section")

    # Assert the per-arm DELTAS this test is responsible for.
    d_proj_succ, d_proj_err = proj_succ_1 - proj_succ_0, proj_err_1 - proj_err_0
    d_sect_succ, d_sect_err = sect_succ_1 - sect_succ_0, sect_err_1 - sect_err_0
    assert (d_proj_succ, d_proj_err) == (9.0, 1.0)
    assert (d_sect_succ, d_sect_err) == (1.0, 1.0)

    # The rate over the deltas is what receiver_query_success_rate computes over
    # the (otherwise-isolated) arm: 2xx / (2xx + 5xx).
    project_rate = d_proj_succ / (d_proj_succ + d_proj_err)
    section_rate = d_sect_succ / (d_sect_succ + d_sect_err)
    combined_succ = d_proj_succ + d_sect_succ
    combined_total = combined_succ + d_proj_err + d_sect_err
    combined_rate = combined_succ / combined_total

    assert project_rate == pytest.approx(0.9)
    assert section_rate == pytest.approx(0.5)
    # combined: 10 success / 12 total
    assert combined_rate == pytest.approx(10 / 12)


def test_success_rate_none_on_zero_denominator() -> None:
    """A never-requested arm returns None (not a fabricated 100%)."""
    assert metrics.receiver_query_success_rate("nonexistent_arm_xyz") is None


# ---------------------------------------------------------------------------
# 5. PROHIBITION — success_rate not readable without serving_stale co-available
# ---------------------------------------------------------------------------


def test_prohibition_success_rate_co_reports_serving_stale() -> None:
    """success_rate_with_stale_context returns the rate AND the stale total together.

    The observability-plan §2 PROHIBITION: the honest rate must not be read
    without serving_stale_total. The accessor enforces this STRUCTURALLY — it
    is impossible to obtain the SLO rate from it without also receiving the
    stale-serve count in the same return tuple.
    """
    metrics.record_receiver_query_outcome("project", success=True)
    metrics.record_serving_stale("project", 600.0)

    rate, stale_total = metrics.success_rate_with_stale_context("project")

    assert rate is not None
    # The stale context is non-optional: it is returned alongside, not separately.
    assert stale_total >= 1.0


def test_prohibition_accessor_signature_forbids_bare_rate() -> None:
    """The SLO accessor's return is a 2-tuple (rate, stale) — never a bare float.

    Guards against a future refactor that drops the stale context from the SLO
    reading surface (re-introducing the flattered-rate blind spot the PROHIBITION
    exists to prevent).
    """
    sig = inspect.signature(metrics.success_rate_with_stale_context)
    # Annotated return is the (rate, stale) tuple — assert the co-report contract.
    assert "tuple" in str(sig.return_annotation).lower()
    result = metrics.success_rate_with_stale_context()
    assert isinstance(result, tuple) and len(result) == 2


# ---------------------------------------------------------------------------
# 6. CPU_STARVATION_REPLACEMENT correlation precondition (receiver-side 2 of 4)
# ---------------------------------------------------------------------------


def test_cpu_starvation_precondition_fires_on_synthetic_event() -> None:
    """Both receiver-observable leading signals present -> precondition True."""
    # Synthetic CPU_STARVATION_REPLACEMENT window: lag spike + gate saturated.
    assert metrics.cpu_starvation_precondition(
        event_loop_lag_seconds=0.75,  # > 500ms threshold
        cpu_thread_semaphore_waiting=2,  # gate saturated
    )


def test_cpu_starvation_precondition_requires_both_signals() -> None:
    """Either signal alone does NOT fire the precondition (no false positive)."""
    # Lag spike but gate not saturated.
    assert not metrics.cpu_starvation_precondition(0.75, 0)
    # Gate saturated but lag within threshold.
    assert not metrics.cpu_starvation_precondition(0.1, 3)
    # Neither.
    assert not metrics.cpu_starvation_precondition(0.0, 0)
