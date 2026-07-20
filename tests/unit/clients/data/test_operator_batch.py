"""Tests for the operator-plane batch consume path + OQ-2 adapter (GAP-1 PR-A).

Covers the consume method's contract (AT-CONSUME-1/2/3), the OQ-2 per-office
distribution adapter, the EC-4 all-or-nothing drift sweep (AT-EC4-1), the 401 retry,
and the G-NO-FALLBACK invariant (AT-INERT-3): the operator path NEVER degrades to the
SA fleet-read.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from autom8_asana.clients.data._endpoints.operator import (
    OPERATOR_BATCH_PATH,
    distribute_per_office,
)
from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.errors import OperatorAccessDeniedError, OperatorMintRefusedError

pytestmark = pytest.mark.usefixtures("enable_insights_feature")

_OPERATOR_TOKEN = "operator.bearer.token"


def _provider(token: str = _OPERATOR_TOKEN) -> MagicMock:
    prov = MagicMock()
    prov.get_token = AsyncMock(return_value=token)
    return prov


def _client(provider: MagicMock | None = None) -> DataServiceClient:
    return DataServiceClient(
        config=DataServiceConfig(base_url="http://data.test.local"),
        operator_token_provider=provider or _provider(),
    )


def _phone_result(phone: str, rows: list[dict[str, Any]], status: str = "success") -> dict:
    return {
        "phone": phone,
        "status": status,
        "data": (
            {"result_type": "result", "data": rows, "meta": {}} if status == "success" else None
        ),
        "error": None if status == "success" else "no data",
        "cache_hit": False,
        "duration_ms": 1.0,
    }


def _op_envelope(per_office: dict[str, list[dict]], insight: str = "account_level_stats") -> dict:
    """A SuccessResponse[BatchInsightResponse] envelope (phone-only mode)."""
    results = [_phone_result(p, rows) for p, rows in per_office.items()]
    return {
        "data": {
            "insight": insight,
            "total_phones": len(per_office),
            "successful": len(per_office),
            "failed": 0,
            "results": results,
            "pair_results": None,
            "duration_ms": 5.0,
        },
        "meta": {"request_id": "req_test"},
    }


# --- OQ-2 adapter ---


class TestDistributePerOffice:
    def test_phone_mode_maps_phone_to_rows(self) -> None:
        rows_a = [{"office": "A", "spend": 10}]
        rows_b = [{"office": "B", "spend": 20}]
        body = _op_envelope({"+1111": rows_a, "+2222": rows_b})
        out = distribute_per_office(body)
        assert out == {"+1111": rows_a, "+2222": rows_b}

    def test_error_result_yields_empty_list(self) -> None:
        body = {
            "data": {
                "insight": "account_level_stats",
                "results": [
                    _phone_result("+1111", [{"x": 1}]),
                    _phone_result("+2222", [], status="error"),
                ],
            }
        }
        out = distribute_per_office(body)
        assert out["+1111"] == [{"x": 1}]
        assert out["+2222"] == []  # no data loss -> empty deck, no dropped key

    def test_pair_mode_supported(self) -> None:
        body = {
            "data": {
                "insight": "account_level_stats",
                "pair_results": [
                    {
                        "phone": "+1111",
                        "vertical": "chiro",
                        "status": "success",
                        "data": {"result_type": "result", "data": [{"y": 2}], "meta": {}},
                    }
                ],
            }
        }
        out = distribute_per_office(body)
        assert out == {"+1111": [{"y": 2}]}

    def test_empty_body_yields_empty(self) -> None:
        assert distribute_per_office({}) == {}
        assert distribute_per_office({"data": {}}) == {}


# --- execute_operator_batch (consume contract) ---


class TestExecuteOperatorBatch:
    async def test_empty_phones_no_wire_call(self) -> None:
        client = _client()
        with respx.mock:
            route = respx.post(OPERATOR_BATCH_PATH)
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=[]
                )
        assert out == {}
        assert not route.called

    async def test_uses_operator_bearer_not_sa_token(self) -> None:
        """AT-CONSUME-1: the operator Bearer is sent; _get_auth_token is never called."""
        client = _client()
        # Make the SA-token getter explode if anyone touches it.
        client._get_auth_token = MagicMock(  # type: ignore[method-assign]
            side_effect=AssertionError("SA token path must not be used")
        )
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("Authorization")
            return httpx.Response(200, json=_op_envelope({"+1111": [{"x": 1}]}))

        with respx.mock:
            respx.post(OPERATOR_BATCH_PATH).mock(side_effect=handler)
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=["+1111"]
                )

        assert captured["auth"] == f"Bearer {_OPERATOR_TOKEN}"
        assert out == {"+1111": [{"x": 1}]}
        client._get_auth_token.assert_not_called()

    async def test_request_shape_insight_name_phones_period_normalized(self) -> None:
        """AT-CONSUME-2: body carries insight_name + phones + normalized period."""
        client = _client()
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_op_envelope({"+1111": [{"x": 1}]}))

        with respx.mock:
            respx.post(OPERATOR_BATCH_PATH).mock(side_effect=handler)
            async with client:
                await client.get_operator_insights_batch_async(
                    "offer_level_stats", phones=["+1111"], period="t30"
                )

        body = captured["body"]
        assert body["insight_name"] == "offer_level_stats"
        assert body["phones"] == ["+1111"]
        assert body["period"] == "T30"  # normalized to the data-plane preset

    async def test_404_single_office_raises_access_denied(self) -> None:
        client = _client()
        with respx.mock:
            respx.post(OPERATOR_BATCH_PATH).mock(return_value=httpx.Response(404))
            with pytest.raises(OperatorAccessDeniedError) as exc:
                async with client:
                    await client.get_operator_insights_batch_async(
                        "account_level_stats", phones=["+1111"]
                    )
        assert exc.value.reason == "route_denied_404"

    async def test_429_raises_access_denied_no_fallback(self) -> None:
        client = _client()
        with respx.mock:
            data_route = respx.post("/api/v1/data-service/insights")
            respx.post(OPERATOR_BATCH_PATH).mock(return_value=httpx.Response(429))
            with pytest.raises(OperatorAccessDeniedError):
                async with client:
                    await client.get_operator_insights_batch_async(
                        "account_level_stats", phones=["+1111"]
                    )
        # G-NO-FALLBACK: the SA fleet-read endpoint was never touched.
        assert not data_route.called

    async def test_401_retries_once_with_force_refresh(self) -> None:
        provider = _provider()
        provider.get_token = AsyncMock(side_effect=["stale.token", "fresh.token"])
        client = _client(provider)
        seen_auth: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_auth.append(request.headers.get("Authorization", ""))
            if len(seen_auth) == 1:
                return httpx.Response(401)
            return httpx.Response(200, json=_op_envelope({"+1111": [{"x": 1}]}))

        with respx.mock:
            respx.post(OPERATOR_BATCH_PATH).mock(side_effect=handler)
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=["+1111"]
                )

        assert out == {"+1111": [{"x": 1}]}
        assert seen_auth == ["Bearer stale.token", "Bearer fresh.token"]
        # The provider was forced to re-mint exactly once.
        assert provider.get_token.await_args_list[1].kwargs == {"force_refresh": True}

    async def test_ec4_drift_sweep_serves_owned_subset_no_sa_fallback(self) -> None:
        """AT-EC4-1: one non-owned office 404s the batch -> per-office sweep on the
        operator route serves the owned subset; the SA fleet-read is never called."""
        owned = {"+1111", "+3333"}
        client = _client()

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            phones = body["phones"]
            if len(phones) > 1:
                # All-or-nothing: the batch contains a drift office -> bare 404.
                return httpx.Response(404)
            phone = phones[0]
            if phone in owned:
                return httpx.Response(200, json=_op_envelope({phone: [{"office": phone}]}))
            return httpx.Response(404)  # the drift office (bare 404-as-oracle)

        with respx.mock:
            data_route = respx.post("/api/v1/data-service/insights")
            respx.post(OPERATOR_BATCH_PATH).mock(side_effect=handler)
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=["+1111", "+2222", "+3333"]
                )

        # Owned offices served; the drift office (+2222) simply absent (empty deck).
        assert set(out) == owned
        assert out["+1111"] == [{"office": "+1111"}]
        assert "+2222" not in out
        # G-NO-FALLBACK: the sweep stayed on the operator route, never the SA path.
        assert not data_route.called

    async def test_g_no_fallback_on_mint_refusal(self) -> None:
        """AT-INERT-3: a mint refusal raises and emits NO SA fleet-read request."""
        provider = _provider()
        provider.get_token = AsyncMock(
            side_effect=OperatorMintRefusedError("refused", reason="mint_refused_403")
        )
        client = _client(provider)
        with respx.mock:
            data_route = respx.post("/api/v1/data-service/insights")
            appts_route = respx.get(url__regex=r".*/appointments.*")
            with pytest.raises(OperatorMintRefusedError):
                async with client:
                    await client.get_operator_insights_batch_async(
                        "account_level_stats", phones=["+1111"]
                    )
        assert not data_route.called
        assert not appts_route.called
