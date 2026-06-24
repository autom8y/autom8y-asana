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
from tests.unit.resolution.gfr.conftest import make_hydration_result

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
