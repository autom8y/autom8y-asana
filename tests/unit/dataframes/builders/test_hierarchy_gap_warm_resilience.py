"""Gap-warm 429 resilience for HierarchyWarmer.warm_hierarchy_gaps_async.

Regression suite for the ASR offer-frame starvation
(ATTRIBUTION-RECEIPT-asana-429-storm-2026-07-13): the fleet shares one Asana
1500/60s budget, and under contention a single surfaced RateLimitError used to
propagate out of the un-chunked gather, hit the outer BROAD-CATCH, and discard
EVERY successfully-fetched parent — ``gaps_warmed=0`` on every SWR cycle, so
the hierarchy never converged (``hierarchy_gap_warming_failed`` with
``parent_gids_count=3291`` in the live logs).

The cure this suite pins:
- a per-fetch RateLimitError tolerates (transport retries are already
  exhausted by the time it surfaces) instead of nuking the batch;
- fetches run in bounded chunks with a saturation abort that BANKS partial
  progress and yields the saturated budget;
- a 429 surfacing from the recursive chain warm (put_batch_async) does not
  discard the banked store;
- the healthy path is byte-for-byte behavior-identical (all fetched, one
  store, complete telemetry).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl

from autom8_asana.dataframes.builders import hierarchy_warmer as hw_module
from autom8_asana.dataframes.builders.hierarchy_warmer import HierarchyWarmer
from autom8_asana.errors import RateLimitError


def _make_warmer(
    get_async_side_effect: Any,
    cached_gids: set[str] | None = None,
) -> tuple[HierarchyWarmer, MagicMock, AsyncMock]:
    """Build a HierarchyWarmer with mocked store/client.

    Returns (warmer, store_mock, tasks_get_async_mock).
    """
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
        max_concurrent=4,
        task_to_dict=lambda task: dict(task),
    )
    return warmer, store, client.tasks.get_async


def _df(parent_gids: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"parent_gid": parent_gids})


def _task(gid: str) -> dict[str, Any]:
    return {"gid": gid, "name": f"parent {gid}"}


async def test_single_429_banks_partial_progress() -> None:
    """One rate-limited fetch among many must not discard the successes.

    Pre-cure behavior: the RateLimitError propagated out of the gather into
    the BROAD-CATCH -> return 0, nothing stored (the live gaps_warmed=0).
    """
    gids = [str(1000 + i) for i in range(10)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == "1003":
            raise RateLimitError("too many requests", retry_after=30)
        return _task(gid)

    warmer, store, get_async = _make_warmer(side_effect)

    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 9
    store.put_batch_async.assert_awaited_once()
    stored = store.put_batch_async.await_args.args[0]
    assert len(stored) == 9
    assert all(t["gid"] != "1003" for t in stored)
    assert get_async.await_count == 10


async def test_saturation_abort_banks_and_stops() -> None:
    """A saturated chunk aborts the remaining chunks but banks its successes."""
    gids = [str(2000 + i) for i in range(12)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        # First chunk (4 gids at patched chunk size): 2 ok, 2 rate-limited
        # -> 2 >= ceil(4 * 0.5) triggers the saturation abort.
        if gid in {"2002", "2003"}:
            raise RateLimitError("too many requests", retry_after=60)
        return _task(gid)

    warmer, store, get_async = _make_warmer(side_effect)

    with patch.object(hw_module, "_GAP_WARM_CHUNK_SIZE", 4):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 2
    # Only the first chunk was attempted: the remaining 8 gids were NOT fetched
    # this cycle (they stay uncached and resume next cycle).
    assert get_async.await_count == 4
    store.put_batch_async.assert_awaited_once()
    assert len(store.put_batch_async.await_args.args[0]) == 2


async def test_healthy_path_unchanged() -> None:
    """No contention: all parents fetched, one store, complete telemetry."""
    gids = [str(3000 + i) for i in range(6)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        return _task(gid)

    warmer, store, get_async = _make_warmer(side_effect)

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 6
    assert get_async.await_count == 6
    store.put_batch_async.assert_awaited_once()
    events_info = [c.args[0] for c in mock_logger.info.call_args_list]
    events_warn = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_warming_complete" in events_info
    assert "hierarchy_gap_warming_partial" not in events_warn
    assert "hierarchy_gap_warming_failed" not in events_warn


async def test_partial_telemetry_on_rate_limit() -> None:
    """Any rate-limited fetch downgrades the summary to the partial event."""
    gids = [str(4000 + i) for i in range(5)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == "4000":
            raise RateLimitError("too many requests", retry_after=15)
        return _task(gid)

    warmer, _store, _get_async = _make_warmer(side_effect)

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 4
    events_warn = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_warming_partial" in events_warn
    partial_call = next(
        c
        for c in mock_logger.warning.call_args_list
        if c.args[0] == "hierarchy_gap_warming_partial"
    )
    extra = partial_call.kwargs["extra"]
    assert extra["attempted"] == 5
    assert extra["fetched"] == 4
    assert extra["rate_limited"] == 1


async def test_chain_warm_429_keeps_banked_store() -> None:
    """A 429 from the recursive chain warm must not forfeit the stored batch.

    put_batch_async stores BEFORE it warms (unified store ordering), so the
    fetched parents are cached even when the deeper chain warm rate-limits;
    the return value reports the banked count instead of 0.
    """
    gids = [str(5000 + i) for i in range(3)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        return _task(gid)

    warmer, store, _get_async = _make_warmer(side_effect)
    store.put_batch_async.side_effect = RateLimitError("too many requests", retry_after=45)

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 3
    events_warn = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_chain_warm_rate_limited" in events_warn
    assert "hierarchy_gap_warming_partial" in events_warn
    assert "hierarchy_gap_warming_failed" not in events_warn


async def test_second_cycle_resumes_from_shrunken_uncached() -> None:
    """Convergence across cycles: banked parents are skipped next cycle."""
    gids = [str(6000 + i) for i in range(8)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        return _task(gid)

    # Cycle 2 premise: the first 5 were banked by cycle 1 (now cached).
    warmer, store, get_async = _make_warmer(
        side_effect, cached_gids={str(6000 + i) for i in range(5)}
    )

    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 3
    assert get_async.await_count == 3
    fetched_gids = {t["gid"] for t in store.put_batch_async.await_args.args[0]}
    assert fetched_gids == {"6005", "6006", "6007"}


async def test_unexpected_error_still_fails_closed() -> None:
    """Non-rate-limit unexpected errors keep the pre-existing fail-closed path."""
    gids = [str(7000 + i) for i in range(3)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        raise ValueError("unexpected corruption")

    warmer, store, _get_async = _make_warmer(side_effect)

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 0
    store.put_batch_async.assert_not_awaited()
    events_warn = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_warming_failed" in events_warn
