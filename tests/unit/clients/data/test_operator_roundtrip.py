"""GAP-1 PR-A round-trip proof (the G-THEATER bar, not a green CI).

This is the best achievable real round-trip in an off-real-STS environment: a
DEFINITIVE integration test that exercises the REAL mint client (real botocore
SigV4 signing of sts:GetCallerIdentity) -> the real ``/operator/token`` request
contract -> the real ``execute_operator_batch`` consumer path -> the OQ-2 adapter,
against a FAITHFUL data-plane + auth double that mirrors the auth verification
(body / host-pin / X-Amz-Date freshness / ARN allowlist) and the data operator
route (C-1 insight allowlist INCL the +2 names, owned-set all-or-nothing, bare
404-as-oracle).

Proof level achieved: DEFINITIVE integration with a faithful double (real SigV4
signing leg + real request contracts). The ONE leg this cannot exercise off-prod
is the actual STS signature validation against the live AWS STS endpoint (no real
credentials / no network); that leg is carried as a FLIP-time UV-P. Stated plainly.

The faithful auth double mirrors (auth origin/main 3df3298a):
  - services/operator_identity.py _GET_CALLER_IDENTITY_BODY (body check)
  - services/operator_identity.py _assert_host_pin (host pin)
  - services/operator_identity.py _enforce_freshness (X-Amz-Date skew window)
  - services/operator_identity.py resolve_operator_sub (ARN allowlist)
The faithful data double mirrors (data origin/main 3169fa96):
  - analytics/routes/operator_insights.py _OPERATOR_INSIGHT_ALLOWLIST (+2 names)
  - analytics/routes/operator_insights.py owned-set all-or-nothing + 404-as-oracle

Two-sided canaries: RT-1 (stale X-Amz-Date rejected), RT-2 (non-allowlisted name ->
bare 404), RT-3 (non-owned office -> bare 404).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import respx
from botocore.credentials import Credentials

from autom8_asana.clients.data import _operator_mint as _mint_mod
from autom8_asana.clients.data._endpoints.operator import OPERATOR_BATCH_PATH
from autom8_asana.clients.data._operator_mint import OperatorMintClient, OperatorTokenProvider
from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.errors import OperatorAccessDeniedError, OperatorMintRefusedError

pytestmark = pytest.mark.usefixtures("enable_insights_feature")

_AUTH_ORIGIN = "https://auth.test.local"
_TOKEN_URL = f"{_AUTH_ORIGIN}/operator/token"
_DATA_BASE = "http://data.test.local"
_HARNESS_TOKEN = "operator.roundtrip.token"

# The data-plane C-1 allowlist WITH PR-D1's +2 names (the round-trip exercises a NEW
# name, offer_level_stats / question_level_stats, that origin/main does not yet carry).
_ALLOWLIST_WITH_PLUS_2 = frozenset(
    {
        "business_summary",
        "account_level_stats",
        "asset_level_stats",
        "offer_level_stats",
        "question_level_stats",
    }
)
_ORACLE_404_DETAIL = "No business record matches the requesting tenant"
_STS_MAX_SKEW_SECONDS = 60


def _fake_credentials() -> Any:
    return Credentials(
        access_key="AKIATESTTESTTESTTEST",
        secret_key="secretkeysecretkeysecretkeysecretkey1234",
        token="FwoGZXIvYXdzEXAMPLEsessiontoken",
    ).get_frozen_credentials()


class FaithfulStack:
    """A faithful auth+data double mirroring the verification contracts."""

    def __init__(
        self,
        *,
        allowlist: frozenset[str] = _ALLOWLIST_WITH_PLUS_2,
        owned: frozenset[str] = frozenset({"+17705753103", "+14155550100"}),
        arn_allowlisted: bool = True,
    ) -> None:
        self.allowlist = allowlist
        self.owned = owned
        self.arn_allowlisted = arn_allowlisted
        self.minted_tokens: list[str] = []

    # --- auth /operator/token (mirrors operator_identity verification) ---
    def auth_handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        headers = {k.lower(): v for k, v in body.get("iam_request_headers", {}).items()}

        # 1. body must be exactly GetCallerIdentity (auth _GET_CALLER_IDENTITY_BODY).
        if body.get("iam_request_body") != _mint_mod.GET_CALLER_IDENTITY_BODY:
            return self._refused()
        # 2. host pin (auth _assert_host_pin).
        if headers.get("host") != _mint_mod.STS_HOST:
            return self._refused()
        # 3. X-Amz-Date freshness (auth _enforce_freshness).
        amz_date = headers.get("x-amz-date")
        if not amz_date or not self._fresh(amz_date):
            return self._refused()
        # 4. The signature would attest a caller ARN; off-STS we simulate that the
        #    valid signed request proves the harness's synthetic ARN, and check the
        #    ARN allowlist (auth resolve_operator_sub).
        if not self.arn_allowlisted:
            return self._refused()
        # 5. The Authorization header must be a real SigV4 signature (sanity).
        if not headers.get("authorization", "").startswith("AWS4-HMAC-SHA256 "):
            return self._refused()

        self.minted_tokens.append(_HARNESS_TOKEN)
        return httpx.Response(
            200,
            json={
                "data": {
                    "access_token": _HARNESS_TOKEN,
                    "token_type": "bearer",
                    "expires_in": 300,
                },
                "meta": {"request_id": "req_auth"},
            },
        )

    @staticmethod
    def _refused() -> httpx.Response:
        # auth maps every front-end failure to a uniform 403 (reason hidden).
        return httpx.Response(403, json={"error": {"code": "FORBIDDEN", "message": "refused"}})

    @staticmethod
    def _fresh(amz_date: str) -> bool:
        try:
            signed_at = datetime.strptime(amz_date, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            return False
        return abs((datetime.now(UTC) - signed_at).total_seconds()) <= _STS_MAX_SKEW_SECONDS

    # --- data /insights/operator/execute-batch (mirrors operator_insights) ---
    def data_handler(self, request: httpx.Request) -> httpx.Response:
        # REC-3: an operator Bearer must be present (else 401-class).
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return httpx.Response(401, json={"error": {"code": "TOKEN_MISSING"}})

        payload = json.loads(request.content)
        insight = payload.get("insight_name")
        phones = payload.get("phones") or []

        # C-1 default-deny insight allowlist -> bare 404-as-oracle before resolution.
        if insight not in self.allowlist:
            return self._oracle_404()
        # owned-set all-or-nothing: ANY non-owned office -> bare 404-as-oracle.
        if any(p not in self.owned for p in phones):
            return self._oracle_404()

        results = [
            {
                "phone": p,
                "status": "success",
                "data": {
                    "result_type": "result",
                    "data": [{"office_phone": p, "insight": insight, "spend": 100, "leads": 5}],
                    "meta": {},
                },
                "error": None,
                "cache_hit": False,
                "duration_ms": 1.0,
            }
            for p in phones
        ]
        return httpx.Response(
            200,
            json={
                "data": {
                    "insight": insight,
                    "total_phones": len(phones),
                    "successful": len(phones),
                    "failed": 0,
                    "results": results,
                    "pair_results": None,
                    "duration_ms": 3.0,
                },
                "meta": {"request_id": "req_data"},
            },
        )

    @staticmethod
    def _oracle_404() -> httpx.Response:
        return httpx.Response(
            404, json={"error": {"code": "DATA-AUTHZ-AGG-404", "message": _ORACLE_404_DETAIL}}
        )

    def register(self) -> None:
        respx.post(_TOKEN_URL).mock(side_effect=self.auth_handler)
        respx.post(OPERATOR_BATCH_PATH).mock(side_effect=self.data_handler)


def _build_client(stack: FaithfulStack) -> DataServiceClient:
    """A real DataServiceClient with a real mint client (real SigV4, fake creds)."""
    config = DataServiceConfig(base_url=_DATA_BASE, operator_token_url=_TOKEN_URL)
    # The mint client posts to the auth origin via a real Autom8yHttpClient (respx
    # intercepts), signing with real botocore SigV4 over the fake-but-valid creds.
    from autom8y_http import Autom8yHttpClient, HttpClientConfig

    mint_http = Autom8yHttpClient(config=HttpClientConfig(base_url=_AUTH_ORIGIN))
    mint_client = OperatorMintClient(
        token_url=_TOKEN_URL,
        http_client=mint_http,
        credentials_provider=_fake_credentials,
    )
    provider = OperatorTokenProvider(mint_client)
    return DataServiceClient(config=config, operator_token_provider=provider)


# --- The round-trip (H-A level: real SigV4 -> real contracts -> faithful double) ---


class TestOperatorRoundTrip:
    async def test_full_chain_serves_a_new_name(self) -> None:
        """Real mint -> token -> operator route for a NEW name (offer_level_stats)."""
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "offer_level_stats",  # a PR-D1 +2 name
                    phones=["+17705753103", "+14155550100"],
                    period="t30",
                )
        # Real BatchInsightResponse parsed + OQ-2 distributed per-office.
        assert set(out) == {"+17705753103", "+14155550100"}
        assert out["+17705753103"][0]["insight"] == "offer_level_stats"
        # A real token was actually minted via the SigV4 round-trip.
        assert stack.minted_tokens == [_HARNESS_TOKEN]

    async def test_question_level_stats_new_name_also_serves(self) -> None:
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "question_level_stats", phones=["+17705753103"], period="lifetime"
                )
        assert out["+17705753103"][0]["insight"] == "question_level_stats"

    # --- RT-1: freshness (two-sided) ---

    async def test_rt1_fresh_mints_green(self) -> None:
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=["+17705753103"]
                )
        assert out["+17705753103"]  # GREEN: fresh signature accepted

    async def test_rt1_stale_x_amz_date_rejected_red(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RT-1 RED: a stale X-Amz-Date (>60s) is rejected at the mint -> refusal."""
        real_sign = _mint_mod.sign_get_caller_identity

        def stale_sign(*args: Any, **kwargs: Any) -> dict[str, str]:
            headers = real_sign(*args, **kwargs)
            stale = (datetime.now(UTC) - timedelta(seconds=120)).strftime("%Y%m%dT%H%M%SZ")
            # Overwrite the freshly-signed date with a stale one (case-insensitive).
            for k in list(headers):
                if k.lower() == "x-amz-date":
                    headers[k] = stale
            return headers

        monkeypatch.setattr(_mint_mod, "sign_get_caller_identity", stale_sign)
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            with pytest.raises(OperatorMintRefusedError):
                async with client:
                    await client.get_operator_insights_batch_async(
                        "account_level_stats", phones=["+17705753103"]
                    )
        assert stack.minted_tokens == []  # no token issued for a stale request

    # --- RT-2: insight allowlist (two-sided, exercises the +2 names AND C-1) ---

    async def test_rt2_allowlisted_new_name_green(self) -> None:
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "offer_level_stats", phones=["+17705753103"]
                )
        assert out["+17705753103"]  # GREEN: +2 name admitted

    async def test_rt2_non_allowlisted_name_bare_404_red(self) -> None:
        """RT-2 RED: reconciliation (excluded) -> bare 404-as-oracle."""
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            with pytest.raises(OperatorAccessDeniedError) as exc:
                async with client:
                    await client.get_operator_insights_batch_async(
                        "reconciliation", phones=["+17705753103"]
                    )
        assert exc.value.reason == "route_denied_404"

    # --- RT-3: ownership (two-sided) ---

    async def test_rt3_owned_office_green(self) -> None:
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            async with client:
                out = await client.get_operator_insights_batch_async(
                    "account_level_stats", phones=["+17705753103"]
                )
        assert out["+17705753103"]  # GREEN: owned office served

    async def test_rt3_non_owned_office_bare_404_red(self) -> None:
        """RT-3 RED: a non-owned office -> bare 404-as-oracle (single office, no sweep)."""
        stack = FaithfulStack()
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            with pytest.raises(OperatorAccessDeniedError) as exc:
                async with client:
                    await client.get_operator_insights_batch_async(
                        "account_level_stats", phones=["+19999999999"]
                    )
        assert exc.value.reason == "route_denied_404"

    # --- INERT: an empty ARN allowlist 403s the mint (the deploy-INERT gate) ---

    async def test_inert_empty_arn_allowlist_refuses_mint(self) -> None:
        stack = FaithfulStack(arn_allowlisted=False)
        client = _build_client(stack)
        with respx.mock:
            stack.register()
            with pytest.raises(OperatorMintRefusedError):
                async with client:
                    await client.get_operator_insights_batch_async(
                        "account_level_stats", phones=["+17705753103"]
                    )
        assert stack.minted_tokens == []
