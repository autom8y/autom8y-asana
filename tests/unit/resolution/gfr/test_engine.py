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


class TestCardinality:
    @pytest.mark.asyncio
    async def test_scalar_true_returns_single_row(self, mock_client) -> None:
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": "G_A"}])
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
        # rather than silently collapse (INVARIANT I5).
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(
            return_value=make_rows_response(rows=[{"company_id": "A"}, {"company_id": "B"}])
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
            return_value=make_rows_response(rows=[{"company_id": "A"}, {"company_id": "B"}])
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
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B"}])
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
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B"}])
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
            return_value=make_rows_response(rows=[{"company_id": None, "gid": "B"}])
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
            return_value=make_rows_response(rows=[{"company_id": "G_A", "gid": "B"}])
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
