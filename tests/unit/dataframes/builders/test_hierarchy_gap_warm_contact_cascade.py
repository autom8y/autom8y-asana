"""Gap-warm resilience for PERMANENT parent faults + cached-but-unlinked parents.

Regression suite for the contact-cascade rot (DIC-S04b) that 503'd
``POST /v1/resolve/business-by-email``.

LIVE RECEIPT (cache-warmer, contact frame ``1200775689604552``, 2026-08-19)::

    hierarchy_gap_fetch_starting   total_parent_gids=2679  uncached_count=795
    hierarchy_gap_warming_failed   parent_gids_count=795
                                   error="task: Not a recognized ID:
                                          1214958033084487 (HTTP 404)"
                                   error_type="NotFoundError"
    hierarchy_gaps_warmed          reconstructed=23484  gaps_warmed=0
    cascade_validation_complete    rows_checked=45598   rows_corrected=0
    cascade_key_null_audit         office_phone null_rate=0.966914  severity=error

TWO defects, one function, one cure:

1. ``NotFoundError`` is NOT a member of ``S3_TRANSPORT_ERRORS`` (that tuple is
   boto/network only) and ``gather_with_limit`` runs a bare ``asyncio.gather``
   with no ``return_exceptions``. So ONE deleted ancestor propagated into the
   outer BROAD-CATCH -> ``return 0``, discarding every parent that fetched
   fine. This is the same wound the 429 arc cured
   (``test_hierarchy_gap_warm_resilience.py``) with one difference that made it
   far worse: a 404 is PERMANENT, so the sweep did not lose a cycle, it lost
   EVERY cycle.

2. The parent partition read "cached as a task" as "hierarchy complete". It is
   not: ``reconstruct_hierarchy_from_dataframe`` registers the CHILD's edge
   (contact -> holder) and leaves the holder's OWN parent edge unknown, so
   ``get_ancestor_chain()`` terminates at the holder and the cascade never
   reaches the Business that owns ``Office Phone``.

Both sides are pinned here: the cure must populate the cascade where a parent
Business genuinely carries a phone, and must NOT invent one where it does not.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl

from autom8_asana.dataframes.builders import hierarchy_warmer as hw_module
from autom8_asana.dataframes.builders.cascade_validator import (
    validate_cascade_fields_async,
)
from autom8_asana.dataframes.builders.hierarchy_warmer import HierarchyWarmer
from autom8_asana.errors import ForbiddenError, GoneError, NotFoundError, RateLimitError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The live GID whose deletion held 23,484 contact rows off their cascade.
_DELETED_PARENT_GID = "1214958033084487"


def _make_warmer(
    get_async_side_effect: Any,
    *,
    cached: dict[str, dict[str, Any]] | None = None,
    linked: set[str] | None = None,
) -> tuple[HierarchyWarmer, MagicMock, AsyncMock]:
    """Build a HierarchyWarmer with mocked store/client.

    Args:
        get_async_side_effect: Side effect for ``client.tasks.get_async``.
        cached: gid -> cached task dict (drives ``cache.get_versioned``).
        linked: gids whose OWN parent edge is already registered in the
            hierarchy index (drives ``hierarchy.get_parent_gid``).

    Returns:
        (warmer, store_mock, tasks_get_async_mock)
    """
    cached = cached or {}
    linked = linked or set()

    hierarchy = MagicMock()
    hierarchy.get_parent_gid.side_effect = lambda gid: f"anc-{gid}" if gid in linked else None

    store = MagicMock()
    store.get_hierarchy_index.return_value = hierarchy
    store.cache.get_versioned.side_effect = lambda gid, entry_type: (
        MagicMock(data=cached[gid]) if gid in cached else None
    )
    store.put_batch_async = AsyncMock(return_value=None)

    client = MagicMock()
    client.tasks.get_async = AsyncMock(side_effect=get_async_side_effect)

    warmer = HierarchyWarmer(
        store=store,
        client=client,
        project_gid="1200775689604552",
        entity_type="contact",
        max_concurrent=4,
        task_to_dict=lambda task: dict(task),
    )
    return warmer, store, client.tasks.get_async


def _df(parent_gids: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"parent_gid": parent_gids})


def _holder(gid: str, business_gid: str = "biz-1") -> dict[str, Any]:
    """A ContactHolder dict: cached, and carrying its Business parent edge."""
    return {"gid": gid, "name": f"contacts {gid}", "parent": {"gid": business_gid}}


def _banked_gids(store: MagicMock) -> set[str]:
    """Every gid handed to put_batch_async across all awaits."""
    return {task["gid"] for call in store.put_batch_async.await_args_list for task in call.args[0]}


# ---------------------------------------------------------------------------
# Defect 1 -- a PERMANENT per-GID fault must not zero the sweep
# ---------------------------------------------------------------------------


async def test_single_404_does_not_discard_the_sweep() -> None:
    """One deleted ancestor among many must not discard the successes.

    Pre-cure: NotFoundError escaped the gather -> outer BROAD-CATCH ->
    ``hierarchy_gap_warming_failed`` + ``return 0``, nothing banked. That is
    the live ``gaps_warmed=0``, and because a 404 never heals it recurred on
    EVERY warm cycle.
    """
    gids = [str(1000 + i) for i in range(10)] + [_DELETED_PARENT_GID]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == _DELETED_PARENT_GID:
            raise NotFoundError(f"task: Not a recognized ID: {gid} (HTTP 404)")
        return _holder(gid)

    warmer, store, get_async = _make_warmer(side_effect)

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 10
    assert get_async.await_count == 11
    store.put_batch_async.assert_awaited_once()
    banked = _banked_gids(store)
    assert len(banked) == 10
    # The deleted parent is NOT banked as a stub -- absence is reported, never
    # papered over with an invented row.
    assert _DELETED_PARENT_GID not in banked

    events_warn = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_warming_failed" not in events_warn
    assert "hierarchy_gap_parent_unresolvable" in events_warn


async def test_permanent_fault_does_not_trip_the_saturation_abort() -> None:
    """404s are not rate limiting: the sweep must walk EVERY chunk.

    The saturation abort exists to yield a saturated shared budget. Counting a
    permanent fault toward it would abandon the remaining chunks for a reason
    that has nothing to do with budget -- and, being permanent, would abandon
    them forever.
    """
    gids = [str(2000 + i) for i in range(8)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        # Whole first chunk (size 4) is deleted -- 4/4 permanent faults.
        if gid in {"2000", "2001", "2002", "2003"}:
            raise NotFoundError(f"task: Not a recognized ID: {gid} (HTTP 404)")
        return _holder(gid)

    warmer, store, get_async = _make_warmer(side_effect)

    with patch.object(hw_module, "_GAP_WARM_CHUNK_SIZE", 4):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    # Both chunks attempted; the second chunk's 4 healthy parents are banked.
    assert get_async.await_count == 8
    assert warmed == 4
    assert _banked_gids(store) == {"2004", "2005", "2006", "2007"}


async def test_410_and_403_are_tolerated_per_fetch() -> None:
    """Gone and Forbidden are the same class as 404: per-GID, permanent."""
    gids = ["3000", "3001", "3002", "3003"]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == "3001":
            raise GoneError("task permanently deleted (HTTP 410)")
        if gid == "3002":
            raise ForbiddenError("access denied (HTTP 403)")
        return _holder(gid)

    warmer, store, _get_async = _make_warmer(side_effect)

    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 2
    assert _banked_gids(store) == {"3000", "3003"}


async def test_rate_limit_semantics_are_unchanged_by_the_cure() -> None:
    """The 429 path keeps its distinct accounting (arc regression guard).

    A permanent fault must not be laundered into ``rate_limited``, and a 429
    must still be counted there -- the two feed different decisions.
    """
    gids = ["4000", "4001", "4002"]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == "4000":
            raise RateLimitError("too many requests", retry_after=15)
        if gid == "4001":
            raise NotFoundError("task: Not a recognized ID: 4001 (HTTP 404)")
        return _holder(gid)

    warmer, _store, _get_async = _make_warmer(side_effect)

    with patch.object(hw_module, "logger") as mock_logger:
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    assert warmed == 1
    partial = next(
        c
        for c in mock_logger.warning.call_args_list
        if c.args[0] == "hierarchy_gap_warming_partial"
    )
    # Exactly one 429; the 404 is NOT counted as rate-limited.
    assert partial.kwargs["extra"]["rate_limited"] == 1


async def test_unmodeled_exception_banks_progress_and_stops() -> None:
    """Structural backstop: no future error class can reopen the total-loss wound.

    An error class nobody modeled must cost the REMAINING chunks, never the
    already-fetched ones.
    """
    gids = [str(5000 + i) for i in range(8)]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == "5005":
            raise ZeroDivisionError("an error class nobody modeled")
        return _holder(gid)

    warmer, store, _get_async = _make_warmer(side_effect)

    with (
        patch.object(hw_module, "_GAP_WARM_CHUNK_SIZE", 4),
        patch.object(hw_module, "logger") as mock_logger,
    ):
        warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    # First chunk banked; second chunk aborted; nothing discarded.
    assert warmed == 4
    assert _banked_gids(store) == {"5000", "5001", "5002", "5003"}
    events_warn = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "hierarchy_gap_chunk_aborted" in events_warn
    assert "hierarchy_gap_warming_failed" not in events_warn


# ---------------------------------------------------------------------------
# Defect 2 -- cached is not the same fact as hierarchy-linked
# ---------------------------------------------------------------------------


async def test_cached_but_unlinked_parent_is_rebanked_without_an_api_call() -> None:
    """A cached holder with no registered edge must still get one.

    This is the dominant half of the live rot: 1,884 of 2,679 contact parents
    were cached (so skipped as "done") yet had no holder -> business edge, so
    ``get_ancestor_chain()`` stopped at the holder and the cascade found no
    Business. Re-banking costs no Asana call -- the cached dict already carries
    ``parent``.
    """
    warmer, store, get_async = _make_warmer(
        AsyncMock(side_effect=AssertionError("no gap GET expected")),
        cached={"holder-1": _holder("holder-1"), "holder-2": _holder("holder-2")},
        linked=set(),
    )

    warmed = await warmer.warm_hierarchy_gaps_async(_df(["holder-1", "holder-2"]))

    assert warmed == 2
    assert get_async.await_count == 0  # zero added Asana budget
    assert _banked_gids(store) == {"holder-1", "holder-2"}
    # warm_hierarchy=True is what makes put_batch_async discover the Business.
    assert store.put_batch_async.await_args.kwargs["warm_hierarchy"] is True


async def test_cached_and_linked_parent_is_skipped_entirely() -> None:
    """The negative side: a complete chain must cost nothing and change nothing.

    Without this, the cure would re-bank every parent every cycle -- churn that
    buys no edge.
    """
    warmer, store, get_async = _make_warmer(
        AsyncMock(side_effect=AssertionError("no gap GET expected")),
        cached={"holder-1": _holder("holder-1")},
        linked={"holder-1"},
    )

    warmed = await warmer.warm_hierarchy_gaps_async(_df(["holder-1"]))

    assert warmed == 0
    assert get_async.await_count == 0
    store.put_batch_async.assert_not_awaited()


async def test_cached_unlinked_without_parent_field_is_not_rebanked() -> None:
    """A dict that cannot contribute an edge is skipped, not banked forever.

    A parentless cached dict would re-enter the unlinked branch on every cycle
    and buy nothing; banking it would be pure churn.
    """
    warmer, store, _get_async = _make_warmer(
        AsyncMock(side_effect=AssertionError("no gap GET expected")),
        cached={"root-1": {"gid": "root-1", "name": "a root task"}},
        linked=set(),
    )

    warmed = await warmer.warm_hierarchy_gaps_async(_df(["root-1"]))

    assert warmed == 0
    store.put_batch_async.assert_not_awaited()


async def test_both_halves_compose_on_the_live_shape() -> None:
    """The live contact frame shape: some parents uncached, some cached-unlinked,
    one deleted. All recoverable edges land in ONE sweep.
    """
    gids = ["holder-cached", "holder-linked", "holder-missing", _DELETED_PARENT_GID]

    async def side_effect(gid: str, opt_fields: Any = None) -> dict[str, Any]:
        if gid == _DELETED_PARENT_GID:
            raise NotFoundError(f"task: Not a recognized ID: {gid} (HTTP 404)")
        return _holder(gid)

    warmer, store, get_async = _make_warmer(
        side_effect,
        cached={
            "holder-cached": _holder("holder-cached"),
            "holder-linked": _holder("holder-linked"),
        },
        linked={"holder-linked"},
    )

    warmed = await warmer.warm_hierarchy_gaps_async(_df(gids))

    # Only the two genuinely-uncached gids cost a GET.
    assert get_async.await_count == 2
    # holder-cached (re-banked, free) + holder-missing (fetched). The linked one
    # needs nothing; the deleted one cannot be had.
    assert _banked_gids(store) == {"holder-cached", "holder-missing"}
    assert warmed == 2


# ---------------------------------------------------------------------------
# The cascade contract this cure exists to restore -- BOTH sides
# ---------------------------------------------------------------------------


def _cascade_store(
    *,
    ancestor_chains: dict[str, list[str]],
    parent_chains: dict[str, list[dict[str, Any]]],
) -> MagicMock:
    hierarchy = MagicMock()
    hierarchy.get_ancestor_chain.side_effect = lambda gid, max_depth=5: ancestor_chains.get(gid, [])
    store = MagicMock()
    store.get_hierarchy_index.return_value = hierarchy
    store.get_parent_chain_async = AsyncMock(
        side_effect=lambda gid, **kw: parent_chains.get(gid, [])
    )
    return store


def _office_phone_schema() -> MagicMock:
    schema = MagicMock()
    schema.get_cascade_columns.return_value = [("office_phone", "Office Phone")]
    return schema


def _contact_frame(gid: str) -> pl.DataFrame:
    return pl.DataFrame(
        {"gid": [gid], "name": ["Synthetic Contact"], "office_phone": [None]},
        schema={"gid": pl.Utf8, "name": pl.Utf8, "office_phone": pl.Utf8},
    )


# Synthetic, non-routable: 555-01xx inside a real area code is the reserved
# fictional range. PII fence -- no real office phone appears in a fixture.
_SYNTHETIC_OFFICE_PHONE = "+12065550142"


async def test_contact_cascades_office_phone_once_the_chain_is_complete() -> None:
    """POSITIVE side: a two-level contact -> holder -> business chain resolves.

    This is the state the cured warm produces. The ContactHolder carries no
    phone -- only the Business does -- so the chain must be walked to depth 2.
    Before the cure the holder's own edge was never registered, the chain
    terminated at the holder, and this row stayed null.
    """
    store = _cascade_store(
        ancestor_chains={"contact-1": ["holder-1", "biz-1"]},
        parent_chains={
            "contact-1": [
                {"gid": "holder-1", "custom_fields": []},
                {
                    "gid": "biz-1",
                    "custom_fields": [
                        {"name": "Office Phone", "display_value": _SYNTHETIC_OFFICE_PHONE}
                    ],
                },
            ]
        },
    )

    corrected, result = await validate_cascade_fields_async(
        merged_df=_contact_frame("contact-1"),
        store=store,
        cascade_plugin=MagicMock(),
        project_gid="1200775689604552",
        entity_type="contact",
        schema=_office_phone_schema(),
    )

    assert corrected["office_phone"][0] == _SYNTHETIC_OFFICE_PHONE
    assert result.rows_corrected == 1


async def test_phoneless_business_leaves_the_contact_null() -> None:
    """NEGATIVE side: no value is ever invented.

    The chain is complete and walked all the way to the Business, but that
    Business genuinely carries no Office Phone. The row MUST stay null -- the
    endpoint then reports ``office_phone_absent`` rather than binding a booking
    to a guessed company.
    """
    store = _cascade_store(
        ancestor_chains={"contact-2": ["holder-2", "biz-2"]},
        parent_chains={
            "contact-2": [
                {"gid": "holder-2", "custom_fields": []},
                {"gid": "biz-2", "custom_fields": []},
            ]
        },
    )

    corrected, result = await validate_cascade_fields_async(
        merged_df=_contact_frame("contact-2"),
        store=store,
        cascade_plugin=MagicMock(),
        project_gid="1200775689604552",
        entity_type="contact",
        schema=_office_phone_schema(),
    )

    assert corrected["office_phone"][0] is None
    assert result.rows_stale == 0
    assert result.rows_corrected == 0


async def test_chain_that_stops_at_the_holder_stays_null() -> None:
    """The PRE-cure state, pinned as a fixture: a truncated chain resolves nothing.

    This is what the live frame looked like -- ``get_ancestor_chain()``
    terminated at the ContactHolder because the holder's own parent edge was
    never registered. The Business (and its phone) is unreachable, so the row
    is null. Pinning it proves the two tests above discriminate on CHAIN
    COMPLETENESS and not on some incidental fixture difference.
    """
    store = _cascade_store(
        ancestor_chains={"contact-3": ["holder-3"]},
        parent_chains={"contact-3": [{"gid": "holder-3", "custom_fields": []}]},
    )

    corrected, result = await validate_cascade_fields_async(
        merged_df=_contact_frame("contact-3"),
        store=store,
        cascade_plugin=MagicMock(),
        project_gid="1200775689604552",
        entity_type="contact",
        schema=_office_phone_schema(),
    )

    assert corrected["office_phone"][0] is None
    assert result.rows_corrected == 0
