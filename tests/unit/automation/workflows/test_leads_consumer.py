"""Unit tests for GrainBridgeLeadsConsumer.

Covers the reconciliation invariant (attempted == succeeded + Sum skips), the
per-class skip emission, the FATAL 401/403 carve-out (raise-and-halt, never N
masquerading resolution_miss skips), per-business token isolation (the leads
path never uses the fleet ServiceTokenAuthProvider), and the empty-active-set
edge case (EC-2).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.auth.business_token import (
    MintCredentialError,
    MintRateLimited,
    MintResolutionMiss,
    MintScopeError,
)
from autom8_asana.auth.per_business_provider import PerBusinessTokenProvider
from autom8_asana.automation.workflows.leads_consumer import (
    GrainBridgeLeadsConsumer,
    _ResolvedBusiness,
)
from autom8_asana.automation.workflows.leads_skip import SkipClass
from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsResponse,
)
from autom8_asana.core.scope import EntityScope


def _leads_response(
    rows: list[dict[str, Any]] | None = None, *, is_stale: bool = False
) -> InsightsResponse:
    data = rows if rows is not None else [{"lead_id": "L1", "name": "x"}]
    return InsightsResponse(
        data=data,
        metadata=InsightsMetadata(
            factory="leads",
            row_count=len(data),
            column_count=1,
            columns=[ColumnInfo(name="lead_id", dtype="str")],
            cache_hit=False,
            duration_ms=10.0,
            is_stale=is_stale,
        ),
        request_id="req-1",
    )


class _FakeLeadsClient:
    def __init__(
        self, response: InsightsResponse | None = None, exc: Exception | None = None
    ) -> None:
        self._response = response if response is not None else _leads_response()
        self._exc = exc
        self.get_leads_calls: list[str] = []
        self.closed = False

    async def get_leads_async(
        self, office_phone: str, *, days: int = 30, limit: int = 100
    ) -> InsightsResponse:
        self.get_leads_calls.append(office_phone)
        if self._exc is not None:
            raise self._exc
        return self._response

    async def close(self) -> None:
        self.closed = True


class _StubMinter:
    """Duck-typed minter: maps ebid -> token (str) OR an exception to raise."""

    def __init__(self, behavior: dict[str, Any]) -> None:
        self._behavior = behavior
        self.minted: list[str] = []

    async def mint(self, external_business_id: str) -> str:
        self.minted.append(external_business_id)
        outcome = self._behavior.get(external_business_id, "tok-default")
        if isinstance(outcome, Exception):
            raise outcome
        return str(outcome)

    async def close(self) -> None:
        return None


def _resolved(company_id: str | None, office_phone: str = "+17705551234") -> _ResolvedBusiness:
    return _ResolvedBusiness(
        gid="biz-" + (company_id or "none"),
        office_phone=office_phone,
        vertical="chiropractic",
        company_id=company_id,
        name="Acme",
    )


def _consumer(
    minter: Any,
    factory: Any,
    *,
    resolve_map: dict[str, _ResolvedBusiness | None],
    metrics_sink: list[tuple[str, float, dict[str, str]]] | None = None,
) -> GrainBridgeLeadsConsumer:
    def hook(name: str, value: float, labels: dict[str, str]) -> None:
        if metrics_sink is not None:
            metrics_sink.append((name, value, labels))

    consumer = GrainBridgeLeadsConsumer(
        MagicMock(),
        minter,
        factory,
        metrics_hook=hook,
    )

    async def fake_resolve(offer_gid: str) -> _ResolvedBusiness | None:
        return resolve_map.get(offer_gid)

    consumer._resolve = fake_resolve  # type: ignore[method-assign]
    return consumer


async def test_reconciliation_invariant_across_mixed_batch() -> None:
    # company_id maps: A valid+ok, B None, C 404, D 429, E empty-leads
    fake_client = _FakeLeadsClient()
    empty_client = _FakeLeadsClient(response=_leads_response(rows=[]))

    clients = {"company-A": fake_client, "company-E": empty_client}

    def factory(provider: Any) -> Any:
        # Token format is "tok-<ebid>"; map back via the minter behavior keys.
        return clients_for_token.get(provider.get_secret("k"), _FakeLeadsClient())

    # Build ebids -> resolve map and minter behavior keyed by ebid.
    from autom8_asana.automation.workflows.leads_ebid import compute_ebid

    ebid_a = compute_ebid("company-A")
    ebid_e = compute_ebid("company-E")
    minter = _StubMinter(
        {
            ebid_a: "tok-A",
            ebid_e: "tok-E",
            compute_ebid("company-C"): MintResolutionMiss("404"),
            compute_ebid("company-D"): MintRateLimited("429"),
        }
    )
    clients_for_token = {"tok-A": fake_client, "tok-E": empty_client}

    resolve_map: dict[str, _ResolvedBusiness | None] = {
        "A": _resolved("company-A"),
        "B": _resolved(None),
        "C": _resolved("company-C"),
        "D": _resolved("company-D"),
        "E": _resolved("company-E"),
    }
    consumer = _consumer(minter, factory, resolve_map=resolve_map)

    scope = EntityScope(entity_ids=("A", "B", "C", "D", "E"))
    result = await consumer.run(scope)

    assert result.attempted == 5
    assert result.succeeded == 1
    assert result.skipped_by_class[SkipClass.RESOLUTION_MISS] == 2  # B (absent) + C (404)
    assert result.skipped_by_class[SkipClass.MINT_UNAVAILABLE] == 1  # D
    assert result.skipped_by_class[SkipClass.INACTIVE_OR_EMPTY] == 1  # E
    # The run asserts the invariant internally; re-confirm here.
    assert result.attempted == result.succeeded + result.total_skipped


async def test_401_credential_error_halts_run() -> None:
    from autom8_asana.automation.workflows.leads_ebid import compute_ebid

    minter = _StubMinter({compute_ebid("company-A"): MintCredentialError("401")})
    consumer = _consumer(
        minter,
        lambda p: _FakeLeadsClient(),
        resolve_map={"A": _resolved("company-A")},
    )
    with pytest.raises(MintCredentialError):
        await consumer.run(EntityScope(entity_ids=("A",)))


async def test_403_scope_error_halts_run() -> None:
    from autom8_asana.automation.workflows.leads_ebid import compute_ebid

    minter = _StubMinter({compute_ebid("company-A"): MintScopeError("403")})
    consumer = _consumer(
        minter,
        lambda p: _FakeLeadsClient(),
        resolve_map={"A": _resolved("company-A")},
    )
    with pytest.raises(MintScopeError):
        await consumer.run(EntityScope(entity_ids=("A",)))


async def test_leads_path_uses_per_business_provider_never_fleet() -> None:
    captured: list[Any] = []

    def factory(provider: Any) -> Any:
        captured.append(provider)
        return _FakeLeadsClient()

    minter = _StubMinter({})  # default token
    consumer = _consumer(minter, factory, resolve_map={"A": _resolved("company-A")})
    await consumer.run(EntityScope(entity_ids=("A",)))
    assert len(captured) == 1
    # SC-BUILD: the leads path is fed a per-business provider, NEVER the fleet
    # ServiceTokenAuthProvider.
    assert isinstance(captured[0], PerBusinessTokenProvider)
    from autom8_asana.auth.service_token import ServiceTokenAuthProvider

    assert not isinstance(captured[0], ServiceTokenAuthProvider)


async def test_empty_active_set_no_mint_no_fallback() -> None:
    minter = _StubMinter({})
    factory_calls: list[Any] = []
    consumer = _consumer(
        minter,
        lambda p: factory_calls.append(p) or _FakeLeadsClient(),
        resolve_map={},
    )

    async def empty_enumerate(scope: Any) -> list[dict[str, Any]]:
        return []

    consumer._enumerate = empty_enumerate  # type: ignore[method-assign]

    result = await consumer.run(EntityScope(entity_ids=()))
    # EC-2: empty active set -> attempted=0, no mint, no client, no fallback.
    assert result.attempted == 0
    assert result.succeeded == 0
    assert minter.minted == []
    assert factory_calls == []


async def test_skip_before_mint_does_not_build_client() -> None:
    # company_id None -> resolution_miss(input_absent) BEFORE any mint.
    minter = _StubMinter({})
    factory_calls: list[Any] = []
    consumer = _consumer(
        minter,
        lambda p: factory_calls.append(p) or _FakeLeadsClient(),
        resolve_map={"A": _resolved(None)},
    )
    result = await consumer.run(EntityScope(entity_ids=("A",)))
    assert result.skipped_by_class[SkipClass.RESOLUTION_MISS] == 1
    assert minter.minted == []  # no mint attempted for an absent company_id
    assert factory_calls == []  # no per-business client built


async def test_no_office_phone_skips_inactive_without_mint() -> None:
    minter = _StubMinter({})
    factory_calls: list[Any] = []
    consumer = _consumer(
        minter,
        lambda p: factory_calls.append(p) or _FakeLeadsClient(),
        resolve_map={"A": _resolved("company-A", office_phone="")},
    )
    result = await consumer.run(EntityScope(entity_ids=("A",)))
    assert result.skipped_by_class[SkipClass.INACTIVE_OR_EMPTY] == 1
    assert minter.minted == []
    assert factory_calls == []


async def test_stale_cache_not_counted_as_success() -> None:
    from autom8_asana.automation.workflows.leads_ebid import compute_ebid

    stale_client = _FakeLeadsClient(response=_leads_response(is_stale=True))
    minter = _StubMinter({compute_ebid("company-A"): "tok-A"})
    consumer = _consumer(
        minter,
        lambda p: stale_client,
        resolve_map={"A": _resolved("company-A")},
    )
    result = await consumer.run(EntityScope(entity_ids=("A",)))
    assert result.succeeded == 0
    assert result.skipped_by_class[SkipClass.INACTIVE_OR_EMPTY] == 1


async def test_per_business_client_is_closed() -> None:
    from autom8_asana.automation.workflows.leads_ebid import compute_ebid

    fake_client = _FakeLeadsClient()
    minter = _StubMinter({compute_ebid("company-A"): "tok-A"})
    consumer = _consumer(minter, lambda p: fake_client, resolve_map={"A": _resolved("company-A")})
    await consumer.run(EntityScope(entity_ids=("A",)))
    assert fake_client.closed is True
