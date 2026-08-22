"""The gap sweep must survive a deleted ANCESTOR, not just a deleted parent (DIC-S04c).

DIC-S04b cured the gap GET (contact -> holder) and added the cached-but-unlinked
re-bank, which it runs FIRST so an early abort still leaves those edges
registered. But that re-bank goes through ``_bank_gap_chunk`` ->
``put_batch_async(warm_hierarchy=True)``, which makes its OWN Asana GETs one
level up (holder -> business). Neither of those two ancestor fetch sites
tolerated a permanent per-GID fault, and ``_bank_gap_chunk`` tolerated only
``RateLimitError`` -- so a single deleted BUSINESS unwound the whole sweep to
``return 0`` **before the first gap GET was even issued**.

Net effect on the S04b image: the 404 moved one level up and the plateau held.

LIVE RECEIPT (cache-warmer, contact frame ``1200775689604552``, 2026-08-20,
image ``55e69d78``, reproduced on every warm cycle for 197 cycles)::

    16:12:19.732  hierarchy_gap_fetch_starting   total_parent_gids=2679
                                                 uncached_count=795
                                                 cached_unlinked_count=1882
    16:12:22.860  hierarchy_gap_warming_failed   parent_gids_count=795
                                                 error="task: Not a recognized
                                                        ID: 1215624688510678
                                                        (HTTP 404)"
                                                 error_type="NotFoundError"
    16:12:22.860  hierarchy_gaps_warmed          reconstructed=23484 gaps_warmed=0
    16:12:45.539  cascade_key_null_audit         office_phone null_rate=0.897547
                                                 severity=error

3.1s elapsed with NO ``hierarchy_gap_parent_unresolvable`` and NO
``hierarchy_gap_chunk_aborted`` in between: the S04b per-fetch tolerance and the
S04b per-chunk isolation were both bypassed, because the fault fired at ancestor
depth inside the FIRST ``_bank_gap_chunk``.

Why the S04b suite did not catch it: every test there mocks
``store.put_batch_async`` as an ``AsyncMock``, so the ancestor GET it performs
in production was never exercised. These tests drive a REAL ``UnifiedTaskStore``
so the second hop is under test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.providers.unified import UnifiedTaskStore
from autom8_asana.dataframes.builders import hierarchy_warmer as hw_module
from autom8_asana.dataframes.builders.hierarchy_warmer import HierarchyWarmer
from autom8_asana.errors import NotFoundError, RateLimitError

if TYPE_CHECKING:
    from autom8_asana.cache.models.entry import EntryType

# The live GID whose deletion zeroed the sweep on the S04b image.
_DELETED_BUSINESS_GID = "1215624688510678"


def _parent_response(gid: str, parent_gid: str | None = None) -> MagicMock:
    mock = MagicMock()
    data: dict[str, Any] = {"gid": gid, "name": f"Task {gid}", "custom_fields": []}
    if parent_gid:
        data["parent"] = {"gid": parent_gid}
    mock.model_dump.return_value = data
    return mock


@pytest.fixture
def cache_provider() -> MagicMock:
    provider = MagicMock()
    stored: dict[str, object] = {}

    def _get_versioned(gid: str, entry_type: EntryType) -> object | None:
        return stored.get(gid)

    provider.get_versioned = MagicMock(side_effect=_get_versioned)
    provider.set_versioned = MagicMock(
        side_effect=lambda gid, entry, **_k: stored.update({gid: entry})
    )
    provider.get_batch = MagicMock(return_value={})
    provider.set_batch = MagicMock(side_effect=lambda entries, **_k: stored.update(entries))
    provider.invalidate = MagicMock()
    provider._stored = stored  # noqa: SLF001 -- test introspection handle
    return provider


def _warmer(
    cache_provider: MagicMock,
    *,
    holder_to_business: dict[str, str],
    deleted: set[str],
) -> tuple[HierarchyWarmer, UnifiedTaskStore, AsyncMock]:
    """Wire a HierarchyWarmer onto a REAL UnifiedTaskStore.

    ``holder_to_business`` is the second hop the cascade needs; ``deleted`` are
    GIDs Asana 404s on, at either hop.
    """
    store = UnifiedTaskStore(
        cache=cache_provider,
        batch_client=MagicMock(),
        freshness_mode=FreshnessIntent.EVENTUAL,
    )

    async def _get_async(gid: str, **_kwargs: object) -> MagicMock:
        if gid in deleted:
            raise NotFoundError(f"task: Not a recognized ID: {gid} (HTTP 404)")
        return _parent_response(gid, holder_to_business.get(gid))

    client = MagicMock()
    client.tasks.get_async = AsyncMock(side_effect=_get_async)

    warmer = HierarchyWarmer(
        store=store,
        client=client,
        project_gid="1200775689604552",
        entity_type="contact",
        max_concurrent=4,
        task_to_dict=lambda task: dict(task.model_dump()),
    )
    return warmer, store, client.tasks.get_async


def _df(parent_gids: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"parent_gid": parent_gids})


# ---------------------------------------------------------------------------
# RED against 55e69d78
# ---------------------------------------------------------------------------


async def test_deleted_business_does_not_zero_the_gap_sweep(
    cache_provider: MagicMock,
) -> None:
    """One deleted Business must not discard the holders that warmed fine.

    Pre-cure: ``NotFoundError`` from the ancestor hop escaped
    ``put_batch_async`` -> ``_bank_gap_chunk`` -> the outer BROAD-CATCH, so the
    sweep returned 0 and ``hierarchy_gap_warming_failed`` fired -- the live
    ``gaps_warmed=0``, every cycle, permanently.
    """
    holders = [f"holder-{i}" for i in range(6)]
    mapping = {h: f"biz-{i}" for i, h in enumerate(holders)}
    mapping["holder-3"] = _DELETED_BUSINESS_GID

    warmer, store, _get_async = _warmer(
        cache_provider, holder_to_business=mapping, deleted={_DELETED_BUSINESS_GID}
    )

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df(holders))

    assert warmed == 6
    warn_events = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_warming_failed" not in warn_events

    # The point of the sweep: the holder -> Business edges the cascade needs.
    hierarchy = store.get_hierarchy_index()
    for i, h in enumerate(holders):
        if h == "holder-3":
            continue
        assert hierarchy.get_parent_gid(h) == f"biz-{i}"
    # And the deleted Business is NOT invented as a stub row.
    assert _DELETED_BUSINESS_GID not in cache_provider._stored  # noqa: SLF001


async def test_ancestor_fault_during_the_unlinked_rebank_still_banks_the_edges(
    cache_provider: MagicMock,
) -> None:
    """The S04b re-bank path is where the live fault fires: it must survive it.

    ``_bank_gap_chunk`` is called with the cached-but-unlinked parents BEFORE
    the chunk loop, so pre-cure the ancestor 404 killed the sweep before a
    single gap GET was issued -- exactly the 3.1s live window with no
    per-fetch and no per-chunk event in it.
    """
    unlinked = {
        "holder-a": {"gid": "holder-a", "name": "a", "parent": {"gid": "biz-a"}},
        "holder-b": {"gid": "holder-b", "name": "b", "parent": {"gid": _DELETED_BUSINESS_GID}},
    }
    for gid, data in unlinked.items():
        cache_provider._stored[gid] = MagicMock(data=data)  # noqa: SLF001

    warmer, store, get_async = _warmer(
        cache_provider,
        holder_to_business={"gap-1": "biz-gap"},
        deleted={_DELETED_BUSINESS_GID},
    )

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df([*unlinked, "gap-1"]))

    # 2 re-banked + 1 gap-fetched.
    assert warmed == 3
    warn_events = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_warming_failed" not in warn_events

    # The gap GET happened AT ALL -- pre-cure the sweep died before reaching it.
    assert "gap-1" in {call.args[0] for call in get_async.await_args_list}

    hierarchy = store.get_hierarchy_index()
    assert hierarchy.get_parent_gid("holder-a") == "biz-a"
    assert hierarchy.get_parent_gid("gap-1") == "biz-gap"


async def test_bank_gap_chunk_isolates_an_unmodeled_chain_warm_fault(
    cache_provider: MagicMock,
) -> None:
    """Structural backstop: NO fault class at ancestor depth may zero the sweep.

    Named faults are cured at their fetch sites; this pins the general shape so
    a future error class added upstream degrades to partial progress instead of
    reopening the total-loss wound.
    """
    warmer, store, _ = _warmer(cache_provider, holder_to_business={}, deleted=set())

    class _UnmodeledFault(Exception):
        pass

    with (
        patch.object(store, "put_batch_async", AsyncMock(side_effect=_UnmodeledFault("boom"))),
        patch.object(hw_module, "logger") as mock_logger,
    ):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(["holder-1", "holder-2"]))

    warn_events = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_chain_warm_failed" in warn_events
    assert "hierarchy_gap_warming_failed" not in warn_events
    # Progress is still reported for what was fetched; the sweep did not unwind.
    assert warmed == 2


# ---------------------------------------------------------------------------
# Negative controls -- MUST pass on BOTH sides of the cure
# ---------------------------------------------------------------------------


async def test_healthy_sweep_registers_the_full_contact_chain(
    cache_provider: MagicMock,
) -> None:
    """No-defect control: with no faults the sweep behaves exactly as before."""
    holders = [f"holder-{i}" for i in range(4)]
    mapping = {h: f"biz-{i}" for i, h in enumerate(holders)}

    warmer, store, _ = _warmer(cache_provider, holder_to_business=mapping, deleted=set())

    warmed = await warmer.warm_hierarchy_gaps_async(_df(holders))

    assert warmed == 4
    hierarchy = store.get_hierarchy_index()
    assert all(hierarchy.get_parent_gid(h) == mapping[h] for h in holders)


async def test_rate_limit_at_ancestor_depth_keeps_its_own_diagnosis(
    cache_provider: MagicMock,
) -> None:
    """A 429 from the chain warm must NOT be re-labelled by the new broad catch.

    Rate-limiting is recoverable and budget-shaped; a permanent fault is
    neither. Collapsing the two would point an operator at the wrong subsystem.
    """
    warmer, store, _ = _warmer(cache_provider, holder_to_business={}, deleted=set())

    with (
        patch.object(
            store, "put_batch_async", AsyncMock(side_effect=RateLimitError("429", retry_after=30))
        ),
        patch.object(hw_module, "logger") as mock_logger,
    ):
        await warmer.warm_hierarchy_gaps_async(_df(["holder-1"]))

    warn_events = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_chain_warm_rate_limited" in warn_events
    assert "hierarchy_gap_chain_warm_failed" not in warn_events


async def test_phoneless_business_is_not_given_an_invented_phone(
    cache_provider: MagicMock,
) -> None:
    """The cure completes the CHAIN; it must never manufacture the VALUE.

    A Business row with no Office Phone stays phoneless downstream -- the
    cascade reports absence rather than papering over it.
    """
    warmer, store, _ = _warmer(
        cache_provider, holder_to_business={"holder-1": "biz-phoneless"}, deleted=set()
    )

    await warmer.warm_hierarchy_gaps_async(_df(["holder-1"]))

    entry = cache_provider._stored.get("biz-phoneless")  # noqa: SLF001
    assert entry is not None
    assert entry.data.get("custom_fields") == []
    assert "office_phone" not in entry.data
