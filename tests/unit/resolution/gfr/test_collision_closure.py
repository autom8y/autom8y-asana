"""The §12.2 ANTI-VACUITY collision-closure gate — the telos-bearing test.

This is the heart of the realization predicate (TDD §12.2, §12.4(b)): it proves
the v2 gid-exact identity path DEFEATS a cross-tenant phone collision that would
silently select the WRONG tenant under the v1 office_phone join.

The non-vacuity hinge (residual_blocking #2): a gid-exact path passes step 3
(`result == G_A`) TRIVIALLY even if the collision protection were absent, because
it structurally never consults the phone join. So the proof requires a companion
broken-path fixture that:

  1. re-introduces the v1 trap by routing company_id through the REAL frozen
     ``execute_join`` (``query/join.py:157`` — ``unique(keep='first')`` then
     ``how='left'``) keyed on the shared ``office_phone``; AND
  2. is ORDERED so B's row precedes A's row for the shared phone key, making B the
     ``keep='first'`` dedup-WINNER for A's gid. (If A were the survivor the broken
     path would coincidentally return G_A and prove nothing.)

The test INSPECTS the constructed dedup ordering (not just the assertion text):
it asserts, against the real ``execute_join`` output, that the broken path
returns G_B (RED) while the v2 gid-exact path returns G_A (GREEN). The DELTA
between the two is the proof the gid-exact identity path actually defeats the
collision. A suite that shipped step 3 without this verified-ordering step 4
would be coverage theater and is REJECTED by design.

NOTE: this exercises ``query/join.py`` as a CLIENT (read-only import + call) to
prove the broken path is genuinely wrong. It does NOT edit the frozen file.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import polars as pl
import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.query.join import execute_join  # frozen — consumed as a client
from autom8_asana.query.models import Comparison, Op, RowsRequest
from autom8_asana.resolution.gfr.engine import resolve_async
from tests.unit.resolution.gfr.conftest import (
    make_hydration_result,
    make_rows_response,
)

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]

_HYDRATE = "autom8_asana.resolution.gfr.entry.hydrate_from_gid_async"

# Two real-shaped tenants sharing an office_phone. A is the tenant we resolve;
# B is the deliberately-constructed dedup-WINNER for the shared phone.
SHARED_PHONE = "+15551234567"
GID_A = "A_business_gid"
GID_B = "B_business_gid"
GUID_A = "11111111-1111-4111-8111-111111111111"  # G_A — A's correct company_id
GUID_B = "22222222-2222-4222-8222-222222222222"  # G_B — B's company_id (the wrong tenant)
OFFER_A = "A_offer_gid"


def _collision_business_frame() -> pl.DataFrame:
    """The multi-tenant Business frame with B ORDERED BEFORE A for the phone.

    Row order is load-bearing: ``unique(subset=['office_phone'], keep='first')``
    keeps the FIRST occurrence, so placing B's row first makes B the dedup
    survivor for the shared phone key. This is the §12.2-step-4 positive
    construction that makes the broken path non-vacuous.
    """
    return pl.DataFrame(
        [
            {"gid": GID_B, "office_phone": SHARED_PHONE, "company_id": GUID_B},  # FIRST
            {"gid": GID_A, "office_phone": SHARED_PHONE, "company_id": GUID_A},  # second
        ]
    )


def _offer_a_primary_frame() -> pl.DataFrame:
    """A's offer row carrying the shared phone — the broken-path join primary."""
    return pl.DataFrame([{"gid": OFFER_A, "office_phone": SHARED_PHONE}])


class TestDedupOrderingInspection:
    """Step 4 inspection: prove B is positively the keep='first' winner for A."""

    def test_b_row_precedes_a_row_for_shared_phone(self) -> None:
        frame = _collision_business_frame()
        phone_rows = frame.filter(pl.col("office_phone") == SHARED_PHONE)
        # Both tenants share the phone (the collision).
        assert phone_rows.height == 2
        # B is ordered FIRST — the keep='first' survivor.
        first_gid = phone_rows.row(0, named=True)["gid"]
        assert first_gid == GID_B, "B must precede A so B wins keep='first' dedup"

    def test_real_dedup_makes_b_the_survivor(self) -> None:
        # Exercise the SAME dedup the frozen execute_join uses (join.py:157).
        frame = _collision_business_frame()
        deduped = frame.unique(subset=["office_phone"], keep="first")
        survivor = deduped.filter(pl.col("office_phone") == SHARED_PHONE).row(0, named=True)
        assert survivor["gid"] == GID_B
        assert survivor["company_id"] == GUID_B  # the WRONG tenant survives


class TestBrokenPathFiresRed:
    """Step 4 RED: the v1 office_phone join returns G_B (the wrong tenant) for A."""

    def test_office_phone_join_yields_wrong_tenant_for_a(self) -> None:
        # Re-introduce the v1 trap via the REAL frozen execute_join: enrich A's
        # offer row with company_id keyed on the shared office_phone.
        primary = _offer_a_primary_frame()
        target = _collision_business_frame()
        result = execute_join(
            primary_df=primary,
            target_df=target,
            join_key="office_phone",
            select_columns=["company_id"],
            target_entity_type="business",
        )
        # The dedup keeps B's row, so A's offer is enriched with B's company_id.
        enriched = result.df.row(0, named=True)
        broken_company_id = enriched["business_company_id"]
        # RED: the broken phone-join path returns G_B — the WRONG tenant.
        assert broken_company_id == GUID_B
        assert broken_company_id != GUID_A


class TestV2PathFiresGreen:
    """Step 3 + the DELTA: v2 gid-exact resolves A to G_A, NEVER G_B."""

    @pytest.mark.asyncio
    async def test_v2_resolves_a_to_g_a_never_g_b(self, mock_client) -> None:
        captured: dict[str, RowsRequest] = {}

        async def _gid_exact_execute(entity_type, project_gid, client, request):
            captured["request"] = request
            # Simulate the gid-exact frame read: filter the multi-tenant frame by
            # the where predicate's gid value — exactly what execute_rows does.
            frame = _collision_business_frame()
            assert isinstance(request.where, Comparison)
            target_gid = request.where.value
            row = frame.filter(pl.col("gid") == target_gid)
            rows = row.to_dicts()
            return make_rows_response(rows=rows)

        query_engine = AsyncMock()
        query_engine.execute_rows = _gid_exact_execute

        # A's offer anchors to A's Business gid via the parent chain (collision-
        # free identity edge) — NOT to B.
        anchor = make_hydration_result(business_gid=GID_A, entry_type=EntityType.OFFER, path_len=3)
        with patch(_HYDRATE, AsyncMock(return_value=anchor)):
            result = await resolve_async(
                OFFER_A,
                ["company_id"],
                client=mock_client,
                query_engine=query_engine,
            )

        # GREEN: v2 resolves A to A's own company_id.
        resolved = result.rows[0]["company_id"].value
        assert resolved == GUID_A
        # NEVER the wrong tenant.
        assert resolved != GUID_B

        # Structural proof (I2): the issued request is gid-exact with NO join, so
        # it can NEVER reach the keep='first' dedup that selected B above.
        request = captured["request"]
        assert request.join is None
        assert request.where.field == "gid"
        assert request.where.op is Op.EQ
        assert request.where.value == GID_A  # anchored to A, not the phone winner

    @pytest.mark.asyncio
    async def test_delta_broken_returns_b_v2_returns_a(self, mock_client) -> None:
        """The DELTA is the proof: same fixture, broken=G_B vs v2=G_A.

        Co-locating both halves in one assertion makes the non-vacuity explicit:
        the broken phone-join path and the v2 gid-exact path run against the SAME
        collision frame and produce DIFFERENT tenants. If the collision
        protection were absent, both would return G_B; the delta proves the
        gid-exact path defeats the collision.
        """
        # Broken half (RED): phone join -> G_B.
        broken = execute_join(
            primary_df=_offer_a_primary_frame(),
            target_df=_collision_business_frame(),
            join_key="office_phone",
            select_columns=["company_id"],
            target_entity_type="business",
        )
        broken_result = broken.df.row(0, named=True)["business_company_id"]

        # v2 half (GREEN): gid-exact -> G_A.
        async def _gid_exact(entity_type, project_gid, client, request):
            frame = _collision_business_frame()
            rows = frame.filter(pl.col("gid") == request.where.value).to_dicts()
            return make_rows_response(rows=rows)

        query_engine = AsyncMock()
        query_engine.execute_rows = _gid_exact
        anchor = make_hydration_result(business_gid=GID_A, entry_type=EntityType.OFFER, path_len=3)
        with patch(_HYDRATE, AsyncMock(return_value=anchor)):
            v2 = await resolve_async(
                OFFER_A,
                ["company_id"],
                client=mock_client,
                query_engine=query_engine,
            )
        v2_result = v2.rows[0]["company_id"].value

        # The DELTA: broken selects the wrong tenant, v2 selects the right one.
        assert broken_result == GUID_B
        assert v2_result == GUID_A
        assert broken_result != v2_result
