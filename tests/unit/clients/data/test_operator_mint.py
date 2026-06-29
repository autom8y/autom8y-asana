"""Tests for the machine-operator SigV4 mint client (GAP-1 PR-A).

Exercises the REAL botocore SigV4 signing path and the auth ``/operator/token``
request contract (AT-MINT-1..4), the INERT/refusal graceful path (AT-INERT-1), and
the mint-once + reuse + re-mint token provider (§5.4).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.credentials import Credentials

from autom8_asana.clients.data._operator_mint import (
    GET_CALLER_IDENTITY_BODY,
    STS_HOST,
    OperatorMintClient,
    OperatorTokenProvider,
    sign_get_caller_identity,
)
from autom8_asana.errors import OperatorMintRefusedError

_TOKEN_URL = "https://auth.test.local/operator/token"


def _fake_credentials() -> Any:
    """Fake-but-valid-shaped session credentials for real SigV4 signing."""
    return Credentials(
        access_key="AKIATESTTESTTESTTEST",
        secret_key="secretkeysecretkeysecretkeysecretkey1234",
        token="FwoGZXIvYXdzEXAMPLEsessiontoken",
    ).get_frozen_credentials()


def _make_response(status_code: int, json_body: dict[str, Any] | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_body or {})
    return resp


def _token_success_body(access_token: str = "operator.jwt.token", expires_in: int = 300) -> dict:
    # The auth /operator/token returns a SuccessResponse envelope: {"data": {...}}.
    return {
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        },
        "meta": {"request_id": "req_test"},
    }


# --- sign_get_caller_identity (AT-MINT-1 / AT-MINT-2) ---


class TestSignGetCallerIdentity:
    """Real SigV4 signing of sts:GetCallerIdentity."""

    def test_signed_headers_carry_authorization_and_date(self) -> None:
        headers = sign_get_caller_identity(_fake_credentials())
        # Case-insensitive lookup
        lower = {k.lower(): v for k, v in headers.items()}
        assert lower["authorization"].startswith("AWS4-HMAC-SHA256 ")
        assert "x-amz-date" in lower
        # Session credentials -> the security token rides along.
        assert "x-amz-security-token" in lower

    def test_signed_host_is_pinned_sts(self) -> None:
        """AT-MINT-2: the signed Host targets the pinned STS host (testable pin)."""
        headers = sign_get_caller_identity(_fake_credentials())
        lower = {k.lower(): v for k, v in headers.items()}
        assert lower["host"] == STS_HOST == "sts.amazonaws.com"
        # host is part of SignedHeaders (so STS validates against it on replay).
        assert "host" in lower["authorization"].split("SignedHeaders=")[1]

    def test_regional_host_changes_the_signature(self) -> None:
        """AT-MINT-2 (two-sided): signing for a regional host yields a different sig."""
        global_headers = sign_get_caller_identity(_fake_credentials())
        regional_headers = sign_get_caller_identity(
            _fake_credentials(),
            sts_endpoint="https://sts.us-west-2.amazonaws.com/",
            sts_host="sts.us-west-2.amazonaws.com",
        )
        g = {k.lower(): v for k, v in global_headers.items()}
        r = {k.lower(): v for k, v in regional_headers.items()}
        assert r["host"] == "sts.us-west-2.amazonaws.com"
        # A request signed for the regional host would be rejected by the auth
        # host-pin; the signature itself differs from the pinned-host signature.
        assert g["authorization"] != r["authorization"]

    def test_get_caller_identity_body_constant_matches_auth(self) -> None:
        """AT-MINT-1: the only replayable STS action body (byte-exact)."""
        assert GET_CALLER_IDENTITY_BODY == "Action=GetCallerIdentity&Version=2011-06-15"


# --- OperatorMintClient.mint ---


class TestOperatorMintClientMint:
    async def test_mint_posts_signed_components_and_parses_token(self) -> None:
        """The mint forwards the signed GetCallerIdentity components and parses the token."""
        captured: dict[str, Any] = {}

        async def fake_post(url: str, *, json: dict[str, Any], **kwargs: Any) -> MagicMock:
            captured["url"] = url
            captured["json"] = json
            return _make_response(200, _token_success_body("tok123", 300))

        http = MagicMock()
        http.post = AsyncMock(side_effect=fake_post)

        client = OperatorMintClient(
            token_url=_TOKEN_URL,
            http_client=http,
            credentials_provider=_fake_credentials,
        )
        access_token, expires_in = await client.mint()

        assert access_token == "tok123"
        assert expires_in == 300
        assert captured["url"] == _TOKEN_URL
        body = captured["json"]
        # AT-MINT-1: exactly the GetCallerIdentity action.
        assert body["iam_request_body"] == GET_CALLER_IDENTITY_BODY
        assert body["iam_request_method"] == "POST"
        # The signed headers ride verbatim; a single-use nonce is included.
        assert "Authorization" in {
            k.title(): v for k, v in body["iam_request_headers"].items()
        } or any(k.lower() == "authorization" for k in body["iam_request_headers"])
        assert body["nonce"]

    async def test_mint_403_raises_refused(self) -> None:
        """AT-INERT-1: a 403 (the empty-allowlist INERT gate) -> typed refusal."""
        http = MagicMock()
        http.post = AsyncMock(return_value=_make_response(403, {"error": "refused"}))
        client = OperatorMintClient(
            token_url=_TOKEN_URL, http_client=http, credentials_provider=_fake_credentials
        )
        with pytest.raises(OperatorMintRefusedError) as exc:
            await client.mint()
        assert exc.value.reason == "mint_refused_403"
        assert exc.value.status_code == 403

    async def test_mint_429_raises_refused(self) -> None:
        http = MagicMock()
        http.post = AsyncMock(return_value=_make_response(429))
        client = OperatorMintClient(
            token_url=_TOKEN_URL, http_client=http, credentials_provider=_fake_credentials
        )
        with pytest.raises(OperatorMintRefusedError) as exc:
            await client.mint()
        assert exc.value.reason == "mint_rate_limited_429"

    async def test_mint_no_token_url_raises(self) -> None:
        http = MagicMock()
        http.post = AsyncMock()
        client = OperatorMintClient(
            token_url=None, http_client=http, credentials_provider=_fake_credentials
        )
        with pytest.raises(OperatorMintRefusedError) as exc:
            await client.mint()
        assert exc.value.reason == "no_token_url"
        http.post.assert_not_called()

    async def test_mint_no_credentials_raises(self) -> None:
        http = MagicMock()
        http.post = AsyncMock()
        client = OperatorMintClient(
            token_url=_TOKEN_URL, http_client=http, credentials_provider=lambda: None
        )
        with pytest.raises(OperatorMintRefusedError) as exc:
            await client.mint()
        assert exc.value.reason == "no_credentials"
        http.post.assert_not_called()

    async def test_mint_malformed_response_raises(self) -> None:
        http = MagicMock()
        http.post = AsyncMock(return_value=_make_response(200, {"data": {"token_type": "bearer"}}))
        client = OperatorMintClient(
            token_url=_TOKEN_URL, http_client=http, credentials_provider=_fake_credentials
        )
        with pytest.raises(OperatorMintRefusedError) as exc:
            await client.mint()
        assert exc.value.reason == "mint_malformed_response"

    async def test_no_secret_at_rest_in_module_source(self) -> None:
        """AT-MINT-4: the mint module persists no token to disk / Secrets Manager."""
        source = Path("src/autom8_asana/clients/data/_operator_mint.py").read_text(encoding="utf-8")
        # No filesystem writes, no Secrets Manager client, no token logging by value.
        assert "open(" not in source
        assert ".write_text(" not in source
        assert "secretsmanager" not in source.lower()
        assert "put_secret" not in source.lower()


# --- OperatorTokenProvider (§5.4 mint-once + reuse + re-mint) ---


class TestOperatorTokenProvider:
    async def test_mints_once_and_reuses(self) -> None:
        mint = MagicMock()
        mint.mint = AsyncMock(return_value=("tok-a", 300))
        provider = OperatorTokenProvider(mint)

        first = await provider.get_token()
        second = await provider.get_token()

        assert first == second == "tok-a"
        mint.mint.assert_awaited_once()

    async def test_force_refresh_remints(self) -> None:
        mint = MagicMock()
        mint.mint = AsyncMock(side_effect=[("tok-a", 300), ("tok-b", 300)])
        provider = OperatorTokenProvider(mint)

        first = await provider.get_token()
        second = await provider.get_token(force_refresh=True)

        assert first == "tok-a"
        assert second == "tok-b"
        assert mint.mint.await_count == 2

    async def test_remints_when_near_expiry(self) -> None:
        mint = MagicMock()
        mint.mint = AsyncMock(side_effect=[("tok-a", 300), ("tok-b", 300)])
        # Safety margin larger than TTL -> the cached token is always "near expiry".
        provider = OperatorTokenProvider(mint, expiry_safety_seconds=10_000)

        await provider.get_token()
        await provider.get_token()

        assert mint.mint.await_count == 2

    async def test_refusal_propagates(self) -> None:
        mint = MagicMock()
        mint.mint = AsyncMock(
            side_effect=OperatorMintRefusedError("refused", reason="mint_refused_403")
        )
        provider = OperatorTokenProvider(mint)
        with pytest.raises(OperatorMintRefusedError):
            await provider.get_token()

    async def test_reuse_within_ttl_no_remint(self) -> None:
        """A second call well within TTL reuses (no second mint)."""
        mint = MagicMock()
        mint.mint = AsyncMock(return_value=("tok-a", 300))
        provider = OperatorTokenProvider(mint, expiry_safety_seconds=1)

        await provider.get_token()
        # Simulate a tiny delay well within the 300s TTL.
        before = time.monotonic()
        await provider.get_token()
        assert time.monotonic() - before < 1.0
        mint.mint.assert_awaited_once()
