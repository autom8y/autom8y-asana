"""Rate-limit buckets are keyed on VERIFIED identity, through the real app.

These tests drive the app built by ``create_app()`` with its real middleware
stack (JWTAuthMiddleware, SlowAPIMiddleware and the rest), with auth dev mode
OFF. JWTs are really signed and really verified: the only test seam is the
JWKS HTTP fetch, which serves the public half of a test keypair. Buckets are
observed in the real SlowAPI limiter's in-memory storage.

Policy under test (``api/rate_limit.py``):

- A token that is not verified never selects the resolver SA bucket or any
  identity bucket.
- A verified resolver SA token keeps its isolated ``sa:asana-dataframe-resolver``
  bucket (Surface E).
- Distinct verified services get distinct buckets.
- Unverifiable tokens cannot consume a verified caller's bucket.
- PATs are keyed by a keyed hash of the whole token, so PATs sharing a prefix
  get distinct buckets.
- Unauthenticated requests are keyed by client IP.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import httpx
import pytest
from autom8y_auth.testing import (
    RSAKeyPairFixture,
    create_jwks_document,
    create_service_claims,
    create_test_token,
    mock_jwks_transport,
)
from fastapi.testclient import TestClient

os.environ.setdefault("IDEMPOTENCY_STORE_BACKEND", "noop")

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.api.rate_limit import SA_RATE_LIMIT_NAMESPACE, limiter
from autom8_asana.api.routes.internal import require_service_claims
from autom8_asana.auth.dual_mode import AuthMode
from autom8_asana.auth.jwt_validator import reset_auth_client

if TYPE_CHECKING:
    from collections.abc import Iterator

_ISSUER = "test.auth.autom8y.io"
_KID = "rate-limit-test-kid"
# JWT-protected S2S route with no rate-limit decorator, so the app-wide
# SlowAPIMiddleware applies the default limit to it.
_PROTECTED_PATH = "/v1/resolve/unit"
# JWT-excluded route: the JWT middleware verifies a token if one is present
# but lets unverifiable requests through, so they reach the limiter.
_EXCLUDED_PATH = "/health"
_CLIENT_IP = "testclient"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def signing_key() -> RSAKeyPairFixture:
    return RSAKeyPairFixture()


@pytest.fixture
def client(signing_key: RSAKeyPairFixture, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The real app, with real JWT verification against a test JWKS."""
    monkeypatch.delenv("AUTH__DEV_MODE", raising=False)
    monkeypatch.setenv("AUTH__ISSUER", _ISSUER)
    reset_auth_client()

    jwks = create_jwks_document(signing_key.public_key, _KID)

    async def _jwks_http_client(_self: object) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=mock_jwks_transport(jwks))

    with patch("autom8y_auth._jwks.JWKSClient._get_http_client", _jwks_http_client):
        app = create_app()

        # Route-level auth dependencies are stubbed so the protected route
        # stays local. The middleware stack (where the limiter and JWT
        # verification run) is untouched.
        async def _auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="stub",
                caller_service="stub",
                claims=SimpleNamespace(sub="stub", client_id=None),
            )

        async def _service_claims() -> SimpleNamespace:
            return SimpleNamespace(sub="stub", service_name="stub", client_id=None)

        app.dependency_overrides[get_auth_context] = _auth_context
        app.dependency_overrides[require_service_claims] = _service_claims

        limiter.reset()
        # No context manager: the lifespan (startup discovery) is not needed.
        yield TestClient(app, raise_server_exceptions=False)
        limiter.reset()

    reset_auth_client()


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _signed_token(key: RSAKeyPairFixture, **claims: Any) -> str:
    claims.setdefault("sub", str(uuid.uuid4()))
    claims.setdefault("bypass_scope_enforcement", True)
    return create_test_token(
        key.private_key_pem, _KID, create_service_claims(issuer=_ISSUER, **claims)
    )


def _resolver_claims() -> dict[str, Any]:
    return {
        "service_account_id": "asana-dataframe-resolver",
        "client_id": "asana-dataframe-resolver-client",
    }


def _unsigned_token(**claims: Any) -> str:
    """A JWT-shaped token whose signature segment is not a signature."""

    def _b64(obj: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    payload = dict(create_service_claims(issuer=_ISSUER, **claims))
    payload.setdefault("sub", str(uuid.uuid4()))
    payload.setdefault("bypass_scope_enforcement", True)
    return f"{_b64({'alg': 'RS256', 'kid': _KID, 'typ': 'JWT'})}.{_b64(payload)}.bm90LWEtc2ln"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Limiter observation
# ---------------------------------------------------------------------------


def _bucket_hits() -> dict[str, int]:
    """Hits per rate-limit key, read from the real limiter's storage.

    Storage keys have the form ``LIMITER/{key}/{scope}/{amount}/{multiples}/{unit}``.
    """
    hits: dict[str, int] = {}
    for storage_key, count in limiter._storage.storage.items():
        parts = storage_key.split("/")
        if parts[0] == "LIMITER" and len(parts) > 1:
            hits[parts[1]] = hits.get(parts[1], 0) + int(count)
    return hits


# ---------------------------------------------------------------------------
# Middleware order
# ---------------------------------------------------------------------------


def test_built_app_runs_rate_limit_inside_jwt_auth() -> None:
    """In the built app, JWT verification runs before SlowAPI picks a bucket.

    ``user_middleware[0]`` is the outermost layer, so JWT must come first.
    """
    app = create_app()
    names = [mw.cls.__name__ for mw in app.user_middleware]

    assert names.index("JWTAuthMiddleware") < names.index("SlowAPIMiddleware"), names


def test_ensure_rate_limit_runs_after_auth_reorders_and_is_idempotent() -> None:
    """The ordering helper moves SlowAPI just inside JWT and is a no-op after."""
    from autom8y_auth import JWTAuthMiddleware
    from fastapi import FastAPI
    from slowapi.middleware import SlowAPIMiddleware
    from starlette.middleware.cors import CORSMiddleware

    from autom8_asana.api.rate_limit import ensure_rate_limit_runs_after_auth

    app = FastAPI()
    # Same registration order as create_fleet_app: CORS, JWT, then SlowAPI.
    app.add_middleware(CORSMiddleware, allow_origins=["*"])
    app.add_middleware(JWTAuthMiddleware, exclude_paths=["/health"])
    app.add_middleware(SlowAPIMiddleware)
    before = [mw.cls.__name__ for mw in app.user_middleware]
    assert before == ["SlowAPIMiddleware", "JWTAuthMiddleware", "CORSMiddleware"]

    ensure_rate_limit_runs_after_auth(app)
    after = [mw.cls.__name__ for mw in app.user_middleware]
    assert after == ["JWTAuthMiddleware", "SlowAPIMiddleware", "CORSMiddleware"]

    ensure_rate_limit_runs_after_auth(app)
    assert [mw.cls.__name__ for mw in app.user_middleware] == after


# ---------------------------------------------------------------------------
# Resolver SA bucket
# ---------------------------------------------------------------------------


def test_unsigned_token_claiming_resolver_identity_does_not_get_sa_bucket(
    client: TestClient,
) -> None:
    token = _unsigned_token(**_resolver_claims())

    protected = client.post(_PROTECTED_PATH, json={}, headers=_bearer(token))
    excluded = client.get(_EXCLUDED_PATH, headers=_bearer(token))

    assert protected.status_code == 401
    assert excluded.status_code == 200
    hits = _bucket_hits()
    assert SA_RATE_LIMIT_NAMESPACE not in hits
    assert not any(key.startswith("jwt:") for key in hits)
    # The unverifiable request that reached the limiter is keyed by IP.
    assert hits.get(f"ip:{_CLIENT_IP}") == 1


def test_token_signed_by_another_key_claiming_resolver_does_not_get_sa_bucket(
    client: TestClient,
) -> None:
    token = _signed_token(RSAKeyPairFixture(), **_resolver_claims())

    protected = client.post(_PROTECTED_PATH, json={}, headers=_bearer(token))
    excluded = client.get(_EXCLUDED_PATH, headers=_bearer(token))

    assert protected.status_code == 401
    assert excluded.status_code == 200
    hits = _bucket_hits()
    assert SA_RATE_LIMIT_NAMESPACE not in hits
    assert hits.get(f"ip:{_CLIENT_IP}") == 1


def test_genuinely_signed_resolver_token_gets_sa_bucket(
    client: TestClient, signing_key: RSAKeyPairFixture
) -> None:
    token = _signed_token(signing_key, **_resolver_claims())

    response = client.post(_PROTECTED_PATH, json={}, headers=_bearer(token))

    assert response.status_code not in (401, 429)
    assert _bucket_hits() == {SA_RATE_LIMIT_NAMESPACE: 1}


def test_business_scoped_resolver_token_gets_sa_bucket(
    client: TestClient, signing_key: RSAKeyPairFixture
) -> None:
    token = _signed_token(
        signing_key,
        bypass_scope_enforcement=False,
        business_id=str(uuid.uuid4()),
        **_resolver_claims(),
    )

    response = client.post(_PROTECTED_PATH, json={}, headers=_bearer(token))

    assert response.status_code not in (401, 429)
    assert _bucket_hits() == {SA_RATE_LIMIT_NAMESPACE: 1}


# ---------------------------------------------------------------------------
# Distinct verified callers
# ---------------------------------------------------------------------------


def test_two_verified_services_get_different_buckets(
    client: TestClient, signing_key: RSAKeyPairFixture
) -> None:
    token_a = _signed_token(signing_key, service_account_id="svc-alpha", client_id="alpha")
    token_b = _signed_token(signing_key, service_account_id="svc-bravo", client_id="bravo")

    client.post(_PROTECTED_PATH, json={}, headers=_bearer(token_a))
    client.post(_PROTECTED_PATH, json={}, headers=_bearer(token_b))
    client.post(_PROTECTED_PATH, json={}, headers=_bearer(token_b))

    assert _bucket_hits() == {"jwt:svc-alpha": 1, "jwt:svc-bravo": 2}


def test_business_id_separates_buckets_for_one_service(
    client: TestClient, signing_key: RSAKeyPairFixture
) -> None:
    biz_1, biz_2 = str(uuid.uuid4()), str(uuid.uuid4())
    token_1 = _signed_token(
        signing_key,
        service_account_id="svc-alpha",
        bypass_scope_enforcement=False,
        business_id=biz_1,
    )
    token_2 = _signed_token(
        signing_key,
        service_account_id="svc-alpha",
        bypass_scope_enforcement=False,
        business_id=biz_2,
    )

    client.post(_PROTECTED_PATH, json={}, headers=_bearer(token_1))
    client.post(_PROTECTED_PATH, json={}, headers=_bearer(token_2))

    assert _bucket_hits() == {f"jwt:svc-alpha:{biz_1}": 1, f"jwt:svc-alpha:{biz_2}": 1}


def test_junk_tokens_sharing_a_prefix_do_not_consume_verified_bucket(
    client: TestClient, signing_key: RSAKeyPairFixture
) -> None:
    """Unverifiable tokens with a verified token's prefix do not drain its bucket.

    Every junk token reuses the verified token's header segment, so all of
    them share its leading characters. The default limit is 100/minute; the
    junk volume exceeds it.
    """
    verified = _signed_token(signing_key, service_account_id="svc-alpha")
    header_segment = verified.split(".")[0]

    for i in range(101):
        junk = f"{header_segment}.e30.junk{i}"
        assert client.post(_PROTECTED_PATH, json={}, headers=_bearer(junk)).status_code != 200

    response = client.post(_PROTECTED_PATH, json={}, headers=_bearer(verified))

    assert response.status_code != 429
    assert _bucket_hits().get("jwt:svc-alpha") == 1


# ---------------------------------------------------------------------------
# PATs and unauthenticated callers
# ---------------------------------------------------------------------------


def test_pats_sharing_first_eight_chars_get_different_buckets(client: TestClient) -> None:
    pat_a = "1/1234567890:aaaaaaaaaaaaaaaa"
    pat_b = "1/1234567890:bbbbbbbbbbbbbbbb"
    assert pat_a[:8] == pat_b[:8]

    client.get(_EXCLUDED_PATH, headers=_bearer(pat_a))
    client.get(_EXCLUDED_PATH, headers=_bearer(pat_b))
    client.get(_EXCLUDED_PATH, headers=_bearer(pat_b))

    hits = _bucket_hits()
    pat_buckets = {key: count for key, count in hits.items() if key.startswith("pat:")}
    assert sorted(pat_buckets.values()) == [1, 2]
    # The bucket key never carries raw token characters.
    assert not any(pat_a[:8] in key or pat_a[-8:] in key for key in pat_buckets)


def test_unauthenticated_request_is_keyed_by_ip(client: TestClient) -> None:
    response = client.get(_EXCLUDED_PATH)

    assert response.status_code == 200
    assert _bucket_hits() == {f"ip:{_CLIENT_IP}": 1}
