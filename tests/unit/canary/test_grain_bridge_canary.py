"""WS-CANARY -- the two-sided discriminating canary for the leads consumer.

Mirrors the auth oracle-seal canary (``test_identity_resolver_and_ebid_seal.py``
:219-300 @ 1ad88e87) at consumer altitude. The SAME harness is used for every
arm; only the INPUT (owned vs cross-tenant company_id) and a single fixture
parameter (the seal's membership gate) differ. NO production code is altered to
manufacture the RED arm (G-THEATER forbidden).

- TC-GREEN: an owned company_id -> ebid in the authorized set -> 200 mint ->
  single-tenant token -> leads read succeeds.
- TC-RED (= DATA-VAL-003 non-regression): a cross-tenant company_id -> ebid
  out-of-set -> uniform 404 AUTH-TEB-005 -> the minter raises
  MintResolutionMiss, ``resolution_miss`` is EMITted, and
  ``get_leads_async`` is NEVER called (no per-business token minted, no leads
  read, no fleet fallback).
- TC-TEETH (non-vacuity): a fixture flag disables the seal's membership gate;
  the SAME cross-tenant input then flips 404 -> 200 (a mint occurs, leads read
  occurs). Restore is byte-identical (the gate is a toggled parameter, not an
  edited production file). Proves the canary bites ONLY on the gate.
- TC-SCOPE: NO arm ever sends read:pii.
"""

from __future__ import annotations

from typing import Any

import pytest

from autom8_asana.auth.business_token import BusinessTokenMinter, MintResolutionMiss
from autom8_asana.automation.workflows.leads_consumer import (
    GrainBridgeLeadsConsumer,
    _ResolvedBusiness,
)
from autom8_asana.automation.workflows.leads_ebid import compute_ebid
from autom8_asana.automation.workflows.leads_skip import SkipClass
from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsResponse,
)
from autom8_asana.core.scope import EntityScope

OWNED_COMPANY_ID = "1000"  # an authorized_organizations member (after normalize)
CROSS_TENANT_COMPANY_ID = "9999"  # an un-owned tenant (out-of-set)
OWNED_GID = "offer-owned"
CROSS_GID = "offer-cross"


class _FakeResponse:
    def __init__(self, status_code: int, body: Any, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def json(self) -> Any:
        return self._body


class _FakeSealExchange:
    """Membership-gated exchange-business mock (mirrors the auth oracle seal).

    gate_enabled=True: ebid in ``authorized`` -> 200 + token; else uniform 404.
    gate_enabled=False (TEETH): the membership check is bypassed -> always 200.
    """

    def __init__(self, authorized: set[str], *, gate_enabled: bool = True) -> None:
        self.authorized = authorized
        self.gate_enabled = gate_enabled
        self.requests: list[dict[str, Any]] = []

    async def post(
        self,
        url: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _FakeResponse:
        self.requests.append({"url": url, "json": json, "headers": headers})
        ebid = json["external_business_id"]
        if self.gate_enabled and ebid not in self.authorized:
            # Uniform 404: miss == out-of-set, echoes only the caller's input.
            return _FakeResponse(404, {"error": "AUTH-TEB-005"})
        return _FakeResponse(200, {"access_token": f"per-business-jwt:{ebid}"})

    async def close(self) -> None:
        return None


class _FakeLeadsClient:
    def __init__(self) -> None:
        self.get_leads_calls: list[str] = []
        self.tokens_seen: list[str] = []
        self.closed = False

    async def get_leads_async(
        self, office_phone: str, *, days: int = 30, limit: int = 100
    ) -> InsightsResponse:
        self.get_leads_calls.append(office_phone)
        return InsightsResponse(
            data=[{"lead_id": "L1"}],
            metadata=InsightsMetadata(
                factory="leads",
                row_count=1,
                column_count=1,
                columns=[ColumnInfo(name="lead_id", dtype="str")],
                cache_hit=False,
                duration_ms=5.0,
                is_stale=False,
            ),
            request_id="canary-req",
        )

    async def close(self) -> None:
        self.closed = True


def _build(seal: _FakeSealExchange) -> tuple[GrainBridgeLeadsConsumer, dict[str, Any]]:
    minter = BusinessTokenMinter(
        client_id="cid",
        client_secret="csecret",
        http_client=seal,  # type: ignore[arg-type]
    )
    leads_client = _FakeLeadsClient()
    factory_calls: list[Any] = []

    def factory(provider: Any) -> Any:
        factory_calls.append(provider)
        leads_client.tokens_seen.append(provider.get_secret("k"))
        return leads_client

    from unittest.mock import MagicMock

    consumer = GrainBridgeLeadsConsumer(MagicMock(), minter, factory)

    resolve_map = {
        OWNED_GID: _ResolvedBusiness(
            gid="biz-owned",
            office_phone="+17705550001",
            vertical="chiropractic",
            company_id=OWNED_COMPANY_ID,
            name="Owned",
        ),
        CROSS_GID: _ResolvedBusiness(
            gid="biz-cross",
            office_phone="+17705559999",
            vertical="chiropractic",
            company_id=CROSS_TENANT_COMPANY_ID,
            name="Cross",
        ),
    }

    async def fake_resolve(offer_gid: str) -> _ResolvedBusiness | None:
        return resolve_map.get(offer_gid)

    consumer._resolve = fake_resolve  # type: ignore[method-assign]
    return consumer, {"leads_client": leads_client, "factory_calls": factory_calls}


def _authorized_owned() -> set[str]:
    return {compute_ebid(OWNED_COMPANY_ID)}


async def test_tc_green_owned_resolves_and_reads() -> None:
    seal = _FakeSealExchange(_authorized_owned())
    consumer, ctx = _build(seal)

    result = await consumer.run(EntityScope(entity_ids=(OWNED_GID,)))

    assert result.succeeded == 1
    # GREEN: a single-tenant mint occurred with the data:read scope pin.
    assert len(seal.requests) == 1
    assert seal.requests[0]["json"]["requested_scopes"] == ["data:read"]
    # the leads read happened on the per-business token.
    leads_client = ctx["leads_client"]
    assert leads_client.get_leads_calls == ["+17705550001"]
    assert leads_client.tokens_seen == [f"per-business-jwt:{compute_ebid(OWNED_COMPANY_ID)}"]


async def test_tc_red_cross_tenant_refused_no_mint_no_read() -> None:
    seal = _FakeSealExchange(_authorized_owned())
    consumer, ctx = _build(seal)

    result = await consumer.run(EntityScope(entity_ids=(CROSS_GID,)))

    # RED = DATA-VAL-003 non-regression.
    assert result.succeeded == 0
    assert result.skipped_by_class[SkipClass.RESOLUTION_MISS] == 1
    # uniform 404 returned, no per-business token minted (no 200 in responses).
    assert len(seal.requests) == 1  # the exchange was attempted...
    # ...and refused: get_leads_async NEVER called, no client built, no fallback.
    assert ctx["leads_client"].get_leads_calls == []
    assert ctx["factory_calls"] == []


async def test_tc_red_minter_raises_resolution_miss_directly() -> None:
    # Direct minter-altitude proof the seal refuses an out-of-set ebid with 404.
    seal = _FakeSealExchange(_authorized_owned())
    minter = BusinessTokenMinter(
        client_id="cid",
        client_secret="csecret",
        http_client=seal,  # type: ignore[arg-type]
    )
    with pytest.raises(MintResolutionMiss):
        await minter.mint(compute_ebid(CROSS_TENANT_COMPANY_ID))


async def test_tc_teeth_gate_disabled_flips_red_to_mint_then_restores() -> None:
    seal = _FakeSealExchange(_authorized_owned(), gate_enabled=True)

    # BEFORE: gate ON -> cross-tenant is RED (refused, no read).
    consumer_before, ctx_before = _build(seal)
    red_before = await consumer_before.run(EntityScope(entity_ids=(CROSS_GID,)))
    assert red_before.succeeded == 0
    assert ctx_before["leads_client"].get_leads_calls == []

    # TEETH: disable the membership gate (a toggled fixture parameter -- NOT an
    # edited production file). The SAME cross-tenant input now flips 404 -> 200.
    seal.gate_enabled = False
    consumer_teeth, ctx_teeth = _build(seal)
    teeth = await consumer_teeth.run(EntityScope(entity_ids=(CROSS_GID,)))
    assert teeth.succeeded == 1  # canary bit: 404 -> 200, leads read occurred
    assert ctx_teeth["leads_client"].get_leads_calls == ["+17705559999"]

    # RESTORE byte-identical: re-enable the gate -> back to RED.
    seal.gate_enabled = True
    consumer_after, ctx_after = _build(seal)
    red_after = await consumer_after.run(EntityScope(entity_ids=(CROSS_GID,)))
    assert red_after.succeeded == 0
    assert ctx_after["leads_client"].get_leads_calls == []
    # The only change between RED-before and RED-after is the gate toggle; the
    # production code path (minter + consumer) is unaltered.


async def test_tc_scope_no_arm_ever_requests_read_pii() -> None:
    # GREEN arm
    seal_green = _FakeSealExchange(_authorized_owned())
    consumer_g, _ = _build(seal_green)
    await consumer_g.run(EntityScope(entity_ids=(OWNED_GID,)))

    # TEETH-mint arm
    seal_teeth = _FakeSealExchange(_authorized_owned(), gate_enabled=False)
    consumer_t, _ = _build(seal_teeth)
    await consumer_t.run(EntityScope(entity_ids=(CROSS_GID,)))

    for seal in (seal_green, seal_teeth):
        for req in seal.requests:
            scopes = req["json"]["requested_scopes"]
            assert scopes == ["data:read"]
            assert "read:pii" not in scopes
