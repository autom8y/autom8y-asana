"""Tests for the GFR entry phase (TDD §4.1, §9.3 entry.py row).

The entry phase is the ONLY Asana-API origin (INVARIANT I1, I3). These tests
verify it does triple duty (hydrate + type-detect + parent-anchor), surfaces the
two identity-failure reasons explicitly, and that its API read budget is bounded
and counted SEPARATELY from frame reads (the PT-03 baseline is taken AFTER the
entry phase returns — QA new_hole 3).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.errors import HydrationError
from autom8_asana.resolution.gfr.entry import EntryAnchor, _fetch_and_anchor_async
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.guard import assert_rows_tenant_identity
from tests.unit.resolution.gfr.conftest import make_entry_task, make_hydration_result

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]

_HYDRATE = "autom8_asana.resolution.gfr.entry.hydrate_from_gid_async"


class TestTripleDuty:
    @pytest.mark.asyncio
    async def test_anchors_business_gid_for_offer(self, mock_client) -> None:
        result = make_hydration_result(
            business_gid="B_correct", entry_type=EntityType.OFFER, path_len=3
        )
        with patch(_HYDRATE, AsyncMock(return_value=result)) as hydrate:
            anchor = await _fetch_and_anchor_async("O_correct", mock_client)
        assert isinstance(anchor, EntryAnchor)
        assert anchor.gid == "O_correct"
        assert anchor.entity_type is EntityType.OFFER
        assert anchor.business_gid == "B_correct"
        # Offer chain depth = 3 (Offer->OfferHolder->Unit->UnitHolder->Business).
        assert anchor.path_len == 3
        # hydrate_full=False: locate the Business root only (the identity spine).
        _, kwargs = hydrate.call_args
        assert kwargs.get("hydrate_full") is False

    @pytest.mark.asyncio
    async def test_business_entry_has_zero_path(self, mock_client) -> None:
        result = make_hydration_result(
            business_gid="B_self", entry_type=EntityType.BUSINESS, path_len=0
        )
        with patch(_HYDRATE, AsyncMock(return_value=result)):
            anchor = await _fetch_and_anchor_async("B_self", mock_client)
        assert anchor.business_gid == "B_self"
        assert anchor.path_len == 0


class TestIdentityFailures:
    @pytest.mark.asyncio
    async def test_hydration_error_maps_to_no_identity_path(self, mock_client) -> None:
        err = HydrationError("no business", entity_gid="g", entity_type=None, phase="upward")
        with patch(_HYDRATE, AsyncMock(side_effect=err)):
            with pytest.raises(UnresolvedError) as exc:
                await _fetch_and_anchor_async("g", mock_client)
        assert exc.value.reason == "no-identity-path"
        assert exc.value.fields == ["g"]

    @pytest.mark.asyncio
    async def test_unknown_type_maps_to_entity_type_undetectable(self, mock_client) -> None:
        result = make_hydration_result(business_gid="B", entry_type=EntityType.UNKNOWN, path_len=0)
        with patch(_HYDRATE, AsyncMock(return_value=result)):
            with pytest.raises(UnresolvedError) as exc:
                await _fetch_and_anchor_async("g", mock_client)
        assert exc.value.reason == "entity-type-undetectable"

    @pytest.mark.asyncio
    async def test_none_type_maps_to_entity_type_undetectable(self, mock_client) -> None:
        result = make_hydration_result(business_gid="B", entry_type=EntityType.OFFER)
        result.entry_type = None  # simulate detection returning no type
        with patch(_HYDRATE, AsyncMock(return_value=result)):
            with pytest.raises(UnresolvedError) as exc:
                await _fetch_and_anchor_async("g", mock_client)
        assert exc.value.reason == "entity-type-undetectable"


class TestEntryBudgetIsolation:
    @pytest.mark.asyncio
    async def test_all_origin_reads_happen_inside_entry_phase(self, mock_client) -> None:
        """All GFR-originated Asana reads happen via the entry fetch (INVARIANT I3).

        The entry phase consumes hydrate_from_gid_async exactly once; the entry +
        chain reads are inside that single call. A caller that baselines the
        client call count AFTER this returns sees the bounded entry budget, not a
        cache-only violation.
        """
        result = make_hydration_result(business_gid="B", entry_type=EntityType.OFFER, path_len=3)
        hydrate_mock = AsyncMock(return_value=result)
        with patch(_HYDRATE, hydrate_mock):
            anchor = await _fetch_and_anchor_async("O", mock_client)
        # Exactly one entry-phase origin call; the chain reads are inside it.
        assert hydrate_mock.await_count == 1
        # Bounded budget: 1 entry hydrate + <=3 parent reads for an offer chain.
        assert anchor.path_len <= 3


class TestEntryTaskThreading:
    """GAP-2 — EntryAnchor additively threads the hydrated cf-carrying task.

    The entry phase already hydrates a task carrying every custom field with its
    typed values (HYP-1). Sprint-1 stops discarding it: ``entry_task`` exposes the
    cf-manifest carrier to the sprint-2 dynamic tail. The field is additive
    (optional, default ``None``), ``is_identity=False`` enrichment data, and
    invisible to the identity guard (TDD §2, §4.1).
    """

    @pytest.mark.asyncio
    async def test_entry_anchor_has_entry_task_field(self, mock_client) -> None:
        """The field exists with a ``None`` default (additive at the type level)."""
        # Constructible without entry_task (default None) — proves additivity.
        anchor = EntryAnchor(gid="g", entity_type=EntityType.OFFER, business_gid="B", path_len=0)
        assert anchor.entry_task is None

    @pytest.mark.asyncio
    async def test_offer_entry_threads_hydrated_task(self, mock_client) -> None:
        """Non-Business entry: ``entry_task`` is the hydrated ``entry_entity`` task."""
        entry_task = make_entry_task(gid="O_correct")
        result = make_hydration_result(
            business_gid="B_correct",
            entry_type=EntityType.OFFER,
            path_len=3,
            entry_entity=entry_task,
        )
        with patch(_HYDRATE, AsyncMock(return_value=result)):
            anchor = await _fetch_and_anchor_async("O_correct", mock_client)
        # The SAME object hydration produced — sprint-1 only stops discarding it.
        assert anchor.entry_task is entry_task

    @pytest.mark.asyncio
    async def test_business_entry_threads_business_as_task(self, mock_client) -> None:
        """Business entry (D-3): ``entry_entity is None`` => thread ``business``.

        ``hydration.py:319-322`` sets ``entry_entity=None`` when the entry gid IS a
        Business; the cf manifest then lives on ``result.business``. The threading
        must give the tail a uniform cf-carrier, so it threads ``business`` here.
        """
        result = make_hydration_result(
            business_gid="B_self",
            entry_type=EntityType.BUSINESS,
            path_len=0,
            entry_entity=None,  # the Business-entry topology
        )
        with patch(_HYDRATE, AsyncMock(return_value=result)):
            anchor = await _fetch_and_anchor_async("B_self", mock_client)
        # D-3: not None — the cf-carrying task in the Business topology is business.
        assert anchor.entry_task is result.business

    @pytest.mark.asyncio
    async def test_entry_task_carries_custom_fields(self, mock_client) -> None:
        """The threaded task exposes ``.custom_fields`` (the sprint-2 manifest)."""
        entry_task = make_entry_task(
            gid="O", custom_fields=[{"gid": "cf1", "name": "Asset ID", "text_value": "a, b"}]
        )
        result = make_hydration_result(
            business_gid="B", entry_type=EntityType.OFFER, path_len=3, entry_entity=entry_task
        )
        with patch(_HYDRATE, AsyncMock(return_value=result)):
            anchor = await _fetch_and_anchor_async("O", mock_client)
        assert anchor.entry_task is not None
        assert anchor.entry_task.custom_fields == [
            {"gid": "cf1", "name": "Asset ID", "text_value": "a, b"}
        ]

    @pytest.mark.asyncio
    async def test_existing_entry_anchor_fields_unchanged(self, mock_client) -> None:
        """Regression: the original 4 fields are unchanged for the Offer case."""
        entry_task = make_entry_task(gid="O_correct")
        result = make_hydration_result(
            business_gid="B_correct",
            entry_type=EntityType.OFFER,
            path_len=3,
            entry_entity=entry_task,
        )
        with patch(_HYDRATE, AsyncMock(return_value=result)):
            anchor = await _fetch_and_anchor_async("O_correct", mock_client)
        assert anchor.gid == "O_correct"
        assert anchor.entity_type is EntityType.OFFER
        assert anchor.business_gid == "B_correct"
        assert anchor.path_len == 3


class TestEntryTaskInvisibleToGuard:
    """GAP-2 §4.1 — the seam is structurally invisible to the identity guard."""

    def test_entry_task_invisible_to_identity_guard(self) -> None:
        """A populated ``entry_task`` cannot change ``assert_rows_tenant_identity``.

        The guard reads only ``row["gid"]`` from query-result rows; it never
        receives or inspects an ``EntryAnchor``. Constructing an anchor WITH a
        populated cf-carrying ``entry_task`` is inert to the guard: a matching-gid
        row still passes, a mismatched-gid row still raises — purely on the row gid.
        """
        # An anchor carrying a fat cf manifest — the guard must remain blind to it.
        anchor = EntryAnchor(
            gid="O",
            entity_type=EntityType.OFFER,
            business_gid="B_tenant",
            path_len=3,
            entry_task=make_entry_task(
                gid="O",
                custom_fields=[{"gid": "cf1", "name": "Asset ID", "text_value": "leak?"}],
            ),
        )
        # Guard passes purely on the row gid == anchored business_gid.
        assert_rows_tenant_identity([{"gid": anchor.business_gid}], anchor.business_gid)

        # And a cross-tenant row still raises — entry_task contributes nothing.
        from autom8_asana.resolution.gfr.guard import GuardViolationError

        with pytest.raises(GuardViolationError):
            assert_rows_tenant_identity([{"gid": "OTHER_TENANT"}], anchor.business_gid)
