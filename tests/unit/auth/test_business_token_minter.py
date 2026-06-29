"""Unit tests for BusinessTokenMinter (exchange-business client).

Pins the status -> exception map (§4 taxonomy), the SC-BUILD-1 scope pin
(requested_scopes == ["data:read"] on EVERY mint, never read:pii), the Basic-auth
ingress shape, and the SC-BUILD-4 credential discipline (process-env only, no
client_secret in logs).
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from autom8_asana.auth.business_token import (
    BusinessTokenMinter,
    MintCollision,
    MintCredentialError,
    MintRateLimited,
    MintResolutionMiss,
    MintScopeError,
    MintUnavailable,
)


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def json(self) -> Any:
        if isinstance(self._body, ValueError):
            raise self._body
        return self._body


class _FakeHttpClient:
    """Captures the outbound request and returns a scripted response."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    async def post(
        self,
        url: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self._response

    async def close(self) -> None:
        self.closed = True


def _minter(response: _FakeResponse) -> tuple[BusinessTokenMinter, _FakeHttpClient]:
    fake = _FakeHttpClient(response)
    minter = BusinessTokenMinter(
        client_id="cid",
        client_secret="csecret",
        http_client=fake,  # type: ignore[arg-type]
    )
    return minter, fake


async def test_mint_200_returns_access_token() -> None:
    minter, fake = _minter(_FakeResponse(200, {"access_token": "jwt-abc"}))
    token = await minter.mint("ebid-1")
    assert token == "jwt-abc"
    assert fake.calls[0]["url"] == "/tokens/exchange-business"


async def test_mint_scope_pin_is_data_read_only() -> None:
    minter, fake = _minter(_FakeResponse(200, {"access_token": "jwt"}))
    await minter.mint("ebid-1")
    body = fake.calls[0]["json"]
    assert body["requested_scopes"] == ["data:read"]
    assert body["external_business_id"] == "ebid-1"
    # SC-BUILD-1: never read:pii on any mint.
    assert "read:pii" not in body["requested_scopes"]


async def test_mint_basic_auth_header_shape() -> None:
    minter, fake = _minter(_FakeResponse(200, {"access_token": "jwt"}))
    await minter.mint("ebid-1")
    auth = fake.calls[0]["headers"]["Authorization"]
    assert auth.startswith("Basic ")
    decoded = base64.b64decode(auth.removeprefix("Basic ")).decode()
    assert decoded == "cid:csecret"


async def test_mint_404_raises_resolution_miss() -> None:
    minter, _ = _minter(_FakeResponse(404, {"error": "AUTH-TEB-005"}))
    with pytest.raises(MintResolutionMiss):
        await minter.mint("ebid-unknown")


async def test_mint_429_raises_rate_limited_with_retry_after() -> None:
    minter, _ = _minter(_FakeResponse(429, {}, headers={"Retry-After": "12"}))
    with pytest.raises(MintRateLimited) as exc_info:
        await minter.mint("ebid-1")
    assert exc_info.value.retry_after == 12


async def test_mint_401_raises_credential_error() -> None:
    minter, _ = _minter(_FakeResponse(401, {"error": "AUTH-TEB-001"}))
    with pytest.raises(MintCredentialError):
        await minter.mint("ebid-1")


async def test_mint_403_raises_scope_error() -> None:
    minter, _ = _minter(_FakeResponse(403, {"error": "AUTH-TEB-003"}))
    with pytest.raises(MintScopeError):
        await minter.mint("ebid-1")


async def test_mint_409_raises_collision() -> None:
    minter, _ = _minter(_FakeResponse(409, {"error": "DATA-CONFLICT-002"}))
    with pytest.raises(MintCollision):
        await minter.mint("ebid-1")


@pytest.mark.parametrize("status", [500, 502, 503, 504])
async def test_mint_5xx_raises_unavailable(status: int) -> None:
    minter, _ = _minter(_FakeResponse(status, {}))
    with pytest.raises(MintUnavailable):
        await minter.mint("ebid-1")


async def test_mint_malformed_200_raises_unavailable() -> None:
    minter, _ = _minter(_FakeResponse(200, {"no_token_here": True}))
    with pytest.raises(MintUnavailable):
        await minter.mint("ebid-1")


async def test_mint_non_json_200_raises_unavailable() -> None:
    minter, _ = _minter(_FakeResponse(200, ValueError("not json")))
    with pytest.raises(MintUnavailable):
        await minter.mint("ebid-1")


async def test_mint_unexpected_4xx_fails_closed_unavailable() -> None:
    minter, _ = _minter(_FakeResponse(418, {}))
    with pytest.raises(MintUnavailable):
        await minter.mint("ebid-1")


def test_missing_credentials_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVICE_CLIENT_ID", raising=False)
    monkeypatch.delenv("SERVICE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SERVICE_CLIENT_SECRET_ARN", raising=False)
    with pytest.raises(ValueError, match="SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET"):
        BusinessTokenMinter(client_id="", client_secret="")


def test_client_secret_not_stored_plaintext() -> None:
    minter = BusinessTokenMinter(client_id="cid", client_secret="topsecret")
    # The secret lives only inside the encoded Basic-auth blob; no plaintext
    # attribute holds it.
    for value in vars(minter).values():
        assert value != "topsecret"


async def test_scope_constant_not_mutated_across_mints() -> None:
    minter, fake = _minter(_FakeResponse(200, {"access_token": "jwt"}))
    await minter.mint("ebid-1")
    # mutate the body the minter sent
    fake.calls[0]["json"]["requested_scopes"].append("read:pii")
    # the frozen class constant must be unaffected
    assert BusinessTokenMinter.SCOPE_DATA_READ == ["data:read"]
