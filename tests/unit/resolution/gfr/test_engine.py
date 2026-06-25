"""Tests for the GFR orchestration spine (TDD §4, §9.3 engine.py row).

CRITICAL (I1/I2): resolve(Offer_gid, [company_id]) goes the identity path; the
issued RowsRequest has ``join is None`` (structurally cannot hit the keep='first'
dedup) and a gid-exact ``where`` predicate. Also covers row-set native results,
scalar cardinality (INVARIANT I5), tier-2 by-guid end-to-end (INVARIANT I7), and
the all-or-nothing failure surface (INVARIANT I4).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.query.models import Comparison, Op, RowsRequest
from autom8_asana.resolution.gfr import engine as engine_mod
from autom8_asana.resolution.gfr.engine import resolve_async
from autom8_asana.resolution.gfr.errors import (
    AmbiguousCardinalityError,
    GuardViolationError,
    UnresolvedError,
)
from autom8_asana.resolution.gfr.models import FieldStatus, TruthTier
from tests.unit.resolution.gfr.conftest import (
    FakeByGuidVerifier,
    make_hydration_result,
    make_record,
    make_rows_response,
)

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]

_HYDRATE = "autom8_asana.resolution.gfr.entry.hydrate_from_gid_async"


def _offer_anchor(business_gid: str = "B_correct"):
    return make_hydration_result(business_gid=business_gid, entry_type=EntityType.OFFER, path_len=3)


class TestIdentityPathStructure:
    """I1/I2: the identity read is gid-exact with NO join."""

    @pytest.mark.asyncio
    async def test_issued_request_has_join_none(self, mock_client) -> None:
        captured: dict[str, RowsRequest] = {}

        async def _capture(entity_type, project_gid, client, request):
            captured["request"] = request
            captured["entity_type"] = entity_type
            captured["project_gid"] = project_gid
            return make_rows_response(rows=[{"company_id": "G_A", "gid": "B_correct"}])

        query_engine = AsyncMock()
        query_engine.execute_rows = _capture

        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            await resolve_async(
                "O_correct",
                ["company_id"],
                client=mock_client,
                query_engine=query_engine,
            )

        request = captured["request"]
        # INVARIANT I2: no join field => structurally cannot reach the
        # execute_join keep='first' dedup (query/join.py:157).
        assert request.join is None
        # INVARIANT I1: the where predicate is GID-EXACT, not a phone match.
        assert isinstance(request.where, Comparison)
        assert request.where.field == "gid"
        assert request.where.op is Op.EQ
        assert request.where.value == "B_correct"
        # The identity read targets the Business entity / multi-tenant project.
        assert captured["entity_type"] == "business"
        assert captured["project_gid"] == "1200653012566782"

    @pytest.mark.asyncio
    async def test_offer_company_id_resolves_to_anchored_tenant(self, mock_client) -> None:
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B_correct"}])
        )
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            result = await resolve_async(
                "O_correct",
                ["company_id"],
                client=mock_client,
                query_engine=query_engine,
            )
        assert result.row_count == 1
        fwp = result.rows[0]["company_id"]
        assert fwp.value == "G_A"
        assert fwp.source is TruthTier.CACHE
        assert fwp.status is FieldStatus.FRESH


class TestEngineOwnedTenantGuard:
    """GAP-1 RED-on-bypass: the engine OWNS Vector-A tenant safety.

    The tenant filter is implicit in the FROZEN query substrate (the gid-exact
    ``where`` -> ``query/engine.py:169`` ``df.filter``). These tests prove the
    engine does NOT merely TRUST that filter: it re-asserts every returned row's
    gid == the anchored business_gid in its OWN code. A drifted/buggy
    query-engine or provider that returns an UNFILTERED multi-tenant frame would,
    WITHOUT the guard, make ``response.data[0]`` a DIFFERENT tenant's row and the
    engine would silently read the wrong company_id. WITH the guard it raises
    ``GuardViolationError`` — the RED-on-bypass proof.
    """

    @pytest.mark.asyncio
    async def test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id(
        self, mock_client
    ) -> None:
        # The anchor resolves the entry gid to tenant B_correct (the parent-chain
        # identity edge). A drifted provider returns an UNFILTERED frame: data[0]
        # is a DIFFERENT tenant's row (gid B_WRONG, company_id G_WRONG), with the
        # correct tenant's row present only LATER in the frame. WITHOUT the
        # engine-owned guard, the engine would read data[0].company_id == G_WRONG
        # (the silent Vector-A cross-tenant leak). WITH it, it raises.
        unfiltered_multitenant = [
            {"company_id": "G_WRONG", "gid": "B_WRONG"},  # a DIFFERENT tenant as data[0]
            {"company_id": "G_correct", "gid": "B_correct"},  # the anchored tenant, buried
        ]
        captured: dict[str, list] = {}

        async def _unfiltered_execute(entity_type, project_gid, client, request):
            # Model a substrate that did NOT apply the gid-exact df.filter: it
            # echoes the whole multi-tenant frame regardless of the where predicate.
            captured["returned"] = list(unfiltered_multitenant)
            return make_rows_response(rows=list(unfiltered_multitenant))

        query_engine = AsyncMock()
        query_engine.execute_rows = _unfiltered_execute

        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor("B_correct"))):
            with pytest.raises(GuardViolationError) as exc:
                await resolve_async(
                    "O_correct",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                )

        # Non-vacuity: the wrong-tenant row WAS actually present as data[0] in the
        # mock response — i.e. without the guard the engine would have read it.
        assert captured["returned"][0]["gid"] == "B_WRONG"
        assert captured["returned"][0]["company_id"] == "G_WRONG"
        assert captured["returned"][0]["gid"] != "B_correct"
        # The guard names the cross-tenant leak it refused, citing the offending gid.
        message = str(exc.value)
        assert "B_WRONG" in message
        assert "B_correct" in message

    @pytest.mark.asyncio
    async def test_single_wrong_tenant_row_fires_guard(self, mock_client) -> None:
        # Even a single-row frame from an unfiltered provider — the wrong tenant's
        # ONLY row — must fire: the engine never reads a company_id off a row whose
        # gid is not the anchored tenant's.
        async def _wrong_only(entity_type, project_gid, client, request):
            return make_rows_response(rows=[{"company_id": "G_WRONG", "gid": "B_WRONG"}])

        query_engine = AsyncMock()
        query_engine.execute_rows = _wrong_only
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor("B_correct"))):
            with pytest.raises(GuardViolationError):
                await resolve_async(
                    "O_correct",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                )

    @pytest.mark.asyncio
    async def test_row_missing_gid_fires_guard_fail_closed(self, mock_client) -> None:
        # Fail-closed: a row that omits the gid key cannot be PROVEN to belong to
        # the anchored tenant, so the guard treats it as a violation rather than
        # trusting it by omission.
        async def _no_gid(entity_type, project_gid, client, request):
            return make_rows_response(rows=[{"company_id": "G_A"}])

        query_engine = AsyncMock()
        query_engine.execute_rows = _no_gid
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor("B_correct"))):
            with pytest.raises(GuardViolationError):
                await resolve_async(
                    "O_correct",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                )


class TestCardinality:
    @pytest.mark.asyncio
    async def test_scalar_true_returns_single_row(self, mock_client) -> None:
        # Rows carry the anchored gid (B_correct) — the gid-exact frame the frozen
        # filter produces; the engine-owned tenant guard (GAP-1) passes.
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B_correct"}])
        )
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            result = await resolve_async(
                "O",
                ["company_id"],
                client=mock_client,
                query_engine=query_engine,
                scalar=True,
            )
        assert result.scalar()["company_id"].value == "G_A"

    @pytest.mark.asyncio
    async def test_scalar_true_raises_on_multiple_rows(self, mock_client) -> None:
        # gid-exact normally yields <=1 row; a multi-row frame (drift) must raise
        # rather than silently collapse (INVARIANT I5). Both rows carry the
        # anchored gid so the tenant guard (GAP-1) passes and the AMBIGUOUS
        # cardinality surface is the one exercised.
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(
                rows=[
                    {"company_id": "A", "gid": "B_correct"},
                    {"company_id": "B", "gid": "B_correct"},
                ]
            )
        )
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            with pytest.raises(AmbiguousCardinalityError):
                await resolve_async(
                    "O",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                    scalar=True,
                )

    @pytest.mark.asyncio
    async def test_row_set_native_default_no_collapse(self, mock_client) -> None:
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(
                rows=[
                    {"company_id": "A", "gid": "B_correct"},
                    {"company_id": "B", "gid": "B_correct"},
                ]
            )
        )
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            result = await resolve_async(
                "O",
                ["company_id"],
                client=mock_client,
                query_engine=query_engine,
            )
        assert result.row_count == 2  # not collapsed


class TestTierTwoEndToEnd:
    @pytest.mark.asyncio
    async def test_verified_tier_stamps_data_verified(self, mock_client) -> None:
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B_correct"}])
        )
        verifier = FakeByGuidVerifier({"G_A": make_record("G_A")})
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            result = await resolve_async(
                "O",
                ["company_id"],
                client=mock_client,
                query_engine=query_engine,
                truth_tier=TruthTier.VERIFIED,
                verifier=verifier,
            )
        assert result.rows[0]["company_id"].source is TruthTier.VERIFIED
        # By-guid was consulted (INVARIANT I7), never an office_phone join.
        assert verifier.calls == ["G_A"]

    @pytest.mark.asyncio
    async def test_verified_tier_without_verifier_is_unresolved(self, mock_client) -> None:
        # Tier-2 requested but no by-guid verifier supplied -> cannot verify ->
        # all-or-nothing unresolved (caller misuse caught explicitly).
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B_correct"}])
        )
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            with pytest.raises(UnresolvedError) as exc:
                await resolve_async(
                    "O",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                    truth_tier=TruthTier.VERIFIED,
                    verifier=None,
                )
        assert exc.value.reason == "business-row-not-found"

    @pytest.mark.asyncio
    async def test_verified_tier_non_string_company_id_unresolved(self, mock_client) -> None:
        # A row whose company_id is null/non-string cannot be by-guid verified.
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": None, "gid": "B_correct"}])
        )
        verifier = FakeByGuidVerifier({"G_A": make_record("G_A")})
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            with pytest.raises(UnresolvedError) as exc:
                await resolve_async(
                    "O",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                    truth_tier=TruthTier.VERIFIED,
                    verifier=verifier,
                )
        assert exc.value.reason == "business-row-not-found"
        # Verifier was never consulted for a non-string candidate.
        assert verifier.calls == []

    @pytest.mark.asyncio
    async def test_verified_tier_by_guid_mismatch_unresolved(self, mock_client) -> None:
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B_correct"}])
        )
        verifier = FakeByGuidVerifier({"G_A": make_record("G_OTHER")})
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            with pytest.raises(UnresolvedError) as exc:
                await resolve_async(
                    "O",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                    truth_tier=TruthTier.VERIFIED,
                    verifier=verifier,
                )
        assert exc.value.reason == "business-row-not-found"


class TestAllOrNothing:
    @pytest.mark.asyncio
    async def test_unknown_field_fails_whole_call(self, mock_client) -> None:
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock()
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            with pytest.raises(UnresolvedError) as exc:
                await resolve_async(
                    "O",
                    ["company_id", "bogus_field"],
                    client=mock_client,
                    query_engine=query_engine,
                )
        assert exc.value.reason == "unknown-field"
        # The frame read never fired — planner rejected before any read.
        query_engine.execute_rows.assert_not_called()

    @pytest.mark.asyncio
    async def test_business_row_not_found_on_empty_identity_frame(self, mock_client) -> None:
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(return_value=make_rows_response(rows=[]))
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            with pytest.raises(UnresolvedError) as exc:
                await resolve_async(
                    "O",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                )
        assert exc.value.reason == "business-row-not-found"

    @pytest.mark.asyncio
    async def test_no_identity_path_when_no_identity_field_requested(self, mock_client) -> None:
        # A non-identity-only field set is out of this rung's identity scope.
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock()
        with patch(_HYDRATE, AsyncMock(return_value=_offer_anchor())):
            with pytest.raises(UnresolvedError) as exc:
                await resolve_async(
                    "O",
                    ["office_phone"],  # offer-owned, non-identity
                    client=mock_client,
                    query_engine=query_engine,
                )
        assert exc.value.reason == "no-identity-path"
