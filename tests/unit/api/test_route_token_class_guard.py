"""Route-walking guard: which token classes each mounted route admits.

This module walks every route mounted on the production FastAPI app built by
``create_app()`` and pins, in ONE reviewed table (``ROUTE_TOKEN_TABLE``), the
token classes each route admits. It fails when:

* a mounted route is missing from the table, or a table entry has no route;
* a route's auth mechanism (derived from the JWT middleware exclude list plus
  the route's dependency chain) differs from the mechanism the table names;
* a real request carrying a token class the table does not name reaches the
  route handler, or a named class is refused.

Token classes
-------------
``ANONYMOUS``          no credential.
``SERVICE_JWT``        service-to-service JWT.
``ASANA_PAT``          Asana personal access token, PAT pass-through.
``WEBHOOK_URL_TOKEN``  the inbound webhook ``?token=`` URL token, no bearer.
``USER_JWT``           interactive user JWT (``token_type="user_access"``).
``OPERATOR_JWT``       machine-operator JWT (``token_type="operator_access"``).
``AGENT_JWT``          delegated-agent JWT (``token_type="agent_access"``).

Policy
------
* User and operator tokens are refused on every authenticated route.
* Agent tokens are refused on every authenticated route except
  ``AGENT_ADMIT_ROUTES``. The route dependency is the refusing layer, which is
  why no route may rely on the JWT middleware alone.
* An agent token never reaches a handler outside ``AGENT_ADMIT_ROUTES``, and
  never produces a server error on any route.
* Public routes ignore any presented credential.
* Agent expectations are strict xfails until SDK agent support lands; the
  admission expectations are strict xfails until agent admission lands.

How requests are measured
-------------------------
The behavioral tests send real requests through the real middleware stack and
the real auth dependency subtrees (``get_auth_context``,
``require_service_claims``, ``verify_webhook_token`` and anything that depends
on them, such as the write-authorization gate). Only the handler body and the
route's non-auth parameters are replaced, by a sentinel that records that it
ran. So "admitted" means the sentinel ran and "refused" means it did not. No
handler body runs, so no request reaches Asana or a database. Tokens are
signed with a test RSA key; the JWKS lookup is patched to serve it.
"""

from __future__ import annotations

import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

# The app factory needs an idempotency backend before it can build its
# middleware stack (same hygiene as test_tags_auth_exclusion.py).
os.environ.setdefault("IDEMPOTENCY_STORE_BACKEND", "noop")

import autom8y_auth.claims as sdk_claims
from autom8y_auth import AuthSettings
from autom8y_auth.middleware import _matches_path
from autom8y_auth.testing import RSAKeyPairFixture, create_jwks_document, create_test_token
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, get_request_handler, request_response
from fastapi.testclient import TestClient
from starlette.routing import Match, Route

from autom8_asana.api.dependencies import get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.api.rate_limit import limiter
from autom8_asana.api.routes import webhooks as webhooks_module
from autom8_asana.api.routes.internal import require_service_claims
from autom8_asana.api.routes.webhooks import verify_webhook_token
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi import FastAPI, Request


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


class TokenClass(StrEnum):
    ANONYMOUS = "anonymous"
    SERVICE_JWT = "service_jwt"
    ASANA_PAT = "asana_pat"
    WEBHOOK_URL_TOKEN = "webhook_url_token"
    USER_JWT = "user_jwt"
    OPERATOR_JWT = "operator_jwt"
    AGENT_JWT = "agent_jwt"


class Mechanism(StrEnum):
    """How a route authenticates, derived from middleware + dependency chain."""

    # JWT middleware excluded, no auth dependency: any credential is ignored.
    PUBLIC = "public"
    # JWT middleware enforced AND require_service_claims in the chain.
    SERVICE_JWT = "service_jwt"
    # JWT middleware excluded, require_service_claims in the chain. The
    # dependency alone authenticates this route.
    SERVICE_JWT_DEPENDENCY_ONLY = "service_jwt_dependency_only"
    # JWT middleware excluded, get_auth_context only: PAT pass-through or JWT.
    DUAL_MODE_PAT_TREE = "dual_mode_pat_tree"
    # JWT middleware enforced, get_auth_context only. The dependency would
    # accept a PAT, but the middleware refuses it first, so only JWTs arrive.
    DUAL_MODE_BEHIND_JWT_MIDDLEWARE = "dual_mode_behind_jwt_middleware"
    # JWT middleware excluded, verify_webhook_token in the chain.
    WEBHOOK_URL_TOKEN = "webhook_url_token"
    # JWT middleware enforced and NO auth dependency. Not allowed in the table:
    # the route dependency is the layer that refuses agent tokens, so a route
    # without one has nothing that refuses them.
    MIDDLEWARE_ONLY = "middleware_only"


_AUTH_DEPENDENCY_KINDS: dict[Any, str] = {
    get_auth_context: "dual_mode",
    require_service_claims: "service_only",
    verify_webhook_token: "webhook",
}

# Token classes each mechanism admits on the CURRENT code. The agent class is
# never derived: no production dependency names the agent claims type yet.
_MECHANISM_ADMITS: dict[Mechanism, frozenset[TokenClass]] = {
    Mechanism.PUBLIC: frozenset(TokenClass),
    Mechanism.SERVICE_JWT: frozenset({TokenClass.SERVICE_JWT}),
    Mechanism.SERVICE_JWT_DEPENDENCY_ONLY: frozenset({TokenClass.SERVICE_JWT}),
    Mechanism.DUAL_MODE_PAT_TREE: frozenset({TokenClass.SERVICE_JWT, TokenClass.ASANA_PAT}),
    Mechanism.DUAL_MODE_BEHIND_JWT_MIDDLEWARE: frozenset({TokenClass.SERVICE_JWT}),
    Mechanism.WEBHOOK_URL_TOKEN: frozenset({TokenClass.WEBHOOK_URL_TOKEN}),
}

_S = frozenset({TokenClass.SERVICE_JWT})
_S_PAT = frozenset({TokenClass.SERVICE_JWT, TokenClass.ASANA_PAT})
_S_AGENT = frozenset({TokenClass.SERVICE_JWT, TokenClass.AGENT_JWT})
_WEBHOOK = frozenset({TokenClass.WEBHOOK_URL_TOKEN})
_ANY = frozenset(TokenClass)


# ---------------------------------------------------------------------------
# THE TABLE -- the one place a reviewer reads.
#
# Key: "METHOD /path/template". Value: (mechanism, token classes admitted).
# Adding a route to the app without adding it here fails the guard. Adding a
# token class here that the route's wiring does not admit fails the guard.
# AGENT_JWT appears only on AGENT_ADMIT_ROUTES (the admission target).
# ---------------------------------------------------------------------------

ROUTE_TOKEN_TABLE: dict[str, tuple[Mechanism, frozenset[TokenClass]]] = {
    # --- public: credential ignored -----------------------------------------
    "GET /openapi.json": (Mechanism.PUBLIC, _ANY),
    "GET /docs": (Mechanism.PUBLIC, _ANY),
    "GET /docs/oauth2-redirect": (Mechanism.PUBLIC, _ANY),
    "GET /redoc": (Mechanism.PUBLIC, _ANY),
    "GET /health": (Mechanism.PUBLIC, _ANY),
    "GET /ready": (Mechanism.PUBLIC, _ANY),
    "GET /health/deps": (Mechanism.PUBLIC, _ANY),
    "GET /metrics": (Mechanism.PUBLIC, _ANY),
    # --- PAT route trees: PAT pass-through or service JWT --------------------
    "GET /api/v1/users/me": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/users/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/users": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/workspaces": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/workspaces/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/dataframes/schemas": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/dataframes/schemas/{name}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/dataframes/project/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/dataframes/section/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/tasks": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/tasks/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/tasks": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "PUT /api/v1/tasks/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "DELETE /api/v1/tasks/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/tasks/{gid}/subtasks": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/tasks/{gid}/dependents": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/tasks/{gid}/duplicate": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/tasks/{gid}/tags": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "DELETE /api/v1/tasks/{gid}/tags/{tag_gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/tasks/{gid}/section": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "PUT /api/v1/tasks/{gid}/assignee": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/tasks/{gid}/projects": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "DELETE /api/v1/tasks/{gid}/projects/{project_gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/tags": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/projects": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/projects/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/projects": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "PUT /api/v1/projects/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "DELETE /api/v1/projects/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/projects/{gid}/members": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "DELETE /api/v1/projects/{gid}/members": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/sections/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/sections": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "PUT /api/v1/sections/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "DELETE /api/v1/sections/{gid}": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/sections/{gid}/tasks": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "POST /api/v1/sections/{gid}/reorder": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/offers/section-timelines": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    # --- inside a PAT tree, but service-JWT only (dependency authenticates) --
    "GET /api/v1/projects/{gid}/sections": (Mechanism.SERVICE_JWT_DEPENDENCY_ONLY, _S),
    # --- dual-mode dependency behind the JWT middleware: JWT only -----------
    "POST /v1/exports": (Mechanism.DUAL_MODE_BEHIND_JWT_MIDDLEWARE, _S),
    "POST /api/v1/exports": (Mechanism.DUAL_MODE_PAT_TREE, _S_PAT),
    "GET /api/v1/workflows/": (Mechanism.DUAL_MODE_BEHIND_JWT_MIDDLEWARE, _S),
    "POST /api/v1/workflows/{workflow_id}/invoke": (
        Mechanism.DUAL_MODE_BEHIND_JWT_MIDDLEWARE,
        _S,
    ),
    # --- webhook URL token ---------------------------------------------------
    "POST /api/v1/webhooks/inbound": (Mechanism.WEBHOOK_URL_TOKEN, _WEBHOOK),
    # --- service JWT (middleware + require_service_claims) -------------------
    "POST /v1/resolve/business": (Mechanism.SERVICE_JWT, _S_AGENT),
    "POST /v1/resolve/contact": (Mechanism.SERVICE_JWT, _S_AGENT),
    "POST /v1/resolve/business-by-email": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/resolve/{entity_type}/schema": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/resolve/{entity_type}/schema/enums/{field_name}": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/resolve/{entity_type}": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/query/entities": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/query/data-sources": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/query/data-sources/{factory}/fields": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/query/{entity_type}/fields": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/query/{entity_type}/relations": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/query/{entity_type}/sections": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/query/entities": (Mechanism.SERVICE_JWT, _S),
    "POST /api/v1/query/entities": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/query/{entity_type}/rows": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/query/{entity_type}/aggregate": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/admin/cache/refresh": (Mechanism.SERVICE_JWT, _S),
    "PATCH /api/v1/entity/{entity_type}/{gid}": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/tasks/{task_gid}/custom-fields": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/intake/business": (Mechanism.SERVICE_JWT, _S_AGENT),
    "POST /v1/intake/route": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/receipts": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/forwarding-stage/census": (Mechanism.SERVICE_JWT, _S),
    "POST /v1/matching/query": (Mechanism.SERVICE_JWT, _S),
    "GET /v1/identity-supply/{offer_gid}": (Mechanism.SERVICE_JWT, _S),
}

# The agent admission target. Pinned separately so that widening agent
# admission requires editing two places on purpose, not one by accident.
AGENT_ADMIT_ROUTES: frozenset[str] = frozenset(
    {
        "POST /v1/intake/business",
        "POST /v1/resolve/business",
        "POST /v1/resolve/contact",
    }
)

_AGENT_ADMISSION_PENDING = "xfail until agent admission lands on this route"


# ---------------------------------------------------------------------------
# Route walking
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouteInfo:
    key: str
    method: str
    path: str
    route: Route
    mechanism: Mechanism | None
    auth_kinds: frozenset[str]


def _auth_kinds(dependant: Dependant) -> set[str]:
    kinds: set[str] = set()
    for sub in dependant.dependencies:
        kind = _AUTH_DEPENDENCY_KINDS.get(sub.call)
        if kind is not None:
            kinds.add(kind)
        kinds |= _auth_kinds(sub)
    return kinds


def _derive_mechanism(middleware_enforced: bool, kinds: set[str]) -> Mechanism | None:
    if "webhook" in kinds:
        return None if middleware_enforced or len(kinds) > 1 else Mechanism.WEBHOOK_URL_TOKEN
    if "service_only" in kinds:
        return (
            Mechanism.SERVICE_JWT if middleware_enforced else Mechanism.SERVICE_JWT_DEPENDENCY_ONLY
        )
    if "dual_mode" in kinds:
        return (
            Mechanism.DUAL_MODE_BEHIND_JWT_MIDDLEWARE
            if middleware_enforced
            else Mechanism.DUAL_MODE_PAT_TREE
        )
    return Mechanism.MIDDLEWARE_ONLY if middleware_enforced else Mechanism.PUBLIC


def _jwt_exclude_paths(app: FastAPI) -> list[str]:
    for mw in app.user_middleware:
        if mw.cls.__name__ == "JWTAuthMiddleware":
            return list(mw.kwargs.get("exclude_paths", []))
    raise AssertionError("JWTAuthMiddleware not found in app.user_middleware")


def _walk_routes(app: FastAPI) -> list[RouteInfo]:
    exclude = _jwt_exclude_paths(app)
    infos: list[RouteInfo] = []
    for route in app.routes:
        if not isinstance(route, Route):
            raise AssertionError(f"unexpected non-HTTP route mounted: {route!r}")
        enforced = not any(_matches_path(route.path, p) for p in exclude)
        kinds = _auth_kinds(route.dependant) if isinstance(route, APIRoute) else set()
        for method in sorted((route.methods or set()) - {"HEAD"}):
            infos.append(
                RouteInfo(
                    key=f"{method} {route.path}",
                    method=method,
                    path=route.path,
                    route=route,
                    mechanism=_derive_mechanism(enforced, kinds),
                    auth_kinds=frozenset(kinds),
                )
            )
    return infos


@pytest.fixture(scope="module")
def walked_app() -> FastAPI:
    """A production app instance, never served; used for the structural walk."""
    return create_app()


@pytest.fixture(scope="module")
def walked(walked_app: FastAPI) -> dict[str, RouteInfo]:
    infos = _walk_routes(walked_app)
    by_key: dict[str, RouteInfo] = {}
    for info in infos:
        assert info.key not in by_key, f"duplicate route key {info.key}"
        by_key[info.key] = info
    return by_key


# ---------------------------------------------------------------------------
# Structural guard
# ---------------------------------------------------------------------------


def test_every_mounted_route_is_in_the_table(walked: dict[str, RouteInfo]) -> None:
    missing = sorted(set(walked) - set(ROUTE_TOKEN_TABLE))
    assert not missing, (
        "Mounted routes missing from ROUTE_TOKEN_TABLE. Decide which token "
        f"classes each admits and add it: {missing}"
    )


def test_every_table_entry_has_a_mounted_route(walked: dict[str, RouteInfo]) -> None:
    stale = sorted(set(ROUTE_TOKEN_TABLE) - set(walked))
    assert not stale, f"ROUTE_TOKEN_TABLE entries with no mounted route: {stale}"


def test_route_mechanism_matches_the_table(walked: dict[str, RouteInfo]) -> None:
    mismatches = {
        key: {"table": ROUTE_TOKEN_TABLE[key][0], "derived": info.mechanism}
        for key, info in walked.items()
        if key in ROUTE_TOKEN_TABLE and ROUTE_TOKEN_TABLE[key][0] != info.mechanism
    }
    assert not mismatches, f"auth mechanism drifted from the table: {mismatches}"


def test_no_route_is_protected_by_the_middleware_alone(walked: dict[str, RouteInfo]) -> None:
    """Every authenticated route carries a route dependency that can refuse."""
    middleware_only = sorted(
        k for k, i in walked.items() if i.mechanism is Mechanism.MIDDLEWARE_ONLY
    )
    unclassified = sorted(k for k, i in walked.items() if i.mechanism is None)
    assert not middleware_only, f"routes guarded only by JWTAuthMiddleware: {middleware_only}"
    assert not unclassified, f"routes with an unclassifiable auth chain: {unclassified}"


def test_table_token_classes_match_the_mechanism() -> None:
    """Non-agent classes in the table are exactly what the mechanism admits."""
    mismatches = {}
    for key, (mechanism, allowed) in ROUTE_TOKEN_TABLE.items():
        if mechanism is Mechanism.PUBLIC:
            expected = _MECHANISM_ADMITS[mechanism]
        else:
            expected = _MECHANISM_ADMITS[mechanism] | (
                {TokenClass.AGENT_JWT} if key in AGENT_ADMIT_ROUTES else set()
            )
        if allowed != expected:
            mismatches[key] = {"table": sorted(allowed), "expected": sorted(expected)}
    assert not mismatches, f"table token classes disagree with the mechanism: {mismatches}"


def test_agent_is_admitted_on_exactly_three_authenticated_routes() -> None:
    authenticated_agent_routes = {
        key
        for key, (mechanism, allowed) in ROUTE_TOKEN_TABLE.items()
        if mechanism is not Mechanism.PUBLIC and TokenClass.AGENT_JWT in allowed
    }
    assert authenticated_agent_routes == AGENT_ADMIT_ROUTES
    assert len(AGENT_ADMIT_ROUTES) == 3
    for key in AGENT_ADMIT_ROUTES:
        assert ROUTE_TOKEN_TABLE[key][0] is Mechanism.SERVICE_JWT


# ---------------------------------------------------------------------------
# Request harness
# ---------------------------------------------------------------------------

_KID = "route-guard-test-kid"

SDK_HAS_AGENT_CLAIMS = hasattr(sdk_claims, "AgentClaims")
SDK_HAS_OPERATOR_CLAIMS = hasattr(sdk_claims, "OperatorClaims")
_PENDING_SDK_AGENT_SUPPORT = "xfail until SDK agent support lands"


@dataclass
class Credentials:
    service_jwt: str
    user_jwt: str
    operator_jwt: str
    agent_jwt_minted: str
    agent_jwt_alternate: str
    asana_pat: str
    webhook_url_token: str


class Reached(list[str]):
    """Route paths whose sentinel ran, plus the middleware claims type seen.

    ``claims_types[i]`` is the class name of ``request.state.claims`` (set by
    ``JWTAuthMiddleware``) when ``self[i]`` ran, or ``"NoneType"``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.claims_types: list[str] = []

    def clear(self) -> None:
        super().clear()
        self.claims_types.clear()


def _sentinel_for(key: str, reached: Reached) -> Any:
    # Accepts the resolved auth values (auth_context, claims, ...) the original
    # handler would have received, and ignores them.
    async def _sentinel(request: Request, **_resolved: Any) -> dict[str, str]:
        reached.append(key)
        reached.claims_types.append(type(getattr(request.state, "claims", None)).__name__)
        return {"reached": key}

    return _sentinel


def _keeps_auth(dep: Dependant) -> bool:
    return dep.call in _AUTH_DEPENDENCY_KINDS or any(_keeps_auth(d) for d in dep.dependencies)


def _install_sentinels(app: FastAPI, reached: Reached) -> None:
    """Replace each handler body with a sentinel, keeping the auth subtrees."""
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        dependant = Dependant(
            call=_sentinel_for(route.path, reached),
            dependencies=[d for d in route.dependant.dependencies if _keeps_auth(d)],
            request_param_name="request",
            path=route.path_format,
        )
        route.app = request_response(
            get_request_handler(dependant=dependant, dependency_overrides_provider=app)
        )


@pytest.fixture(scope="module")
def keypair() -> RSAKeyPairFixture:
    return RSAKeyPairFixture()


@pytest.fixture(scope="module")
def credentials(keypair: RSAKeyPairFixture) -> Credentials:
    settings = AuthSettings()
    now = int(time.time())
    base = {
        "iss": settings.issuer,
        "aud": "https://api.autom8y.io",
        "iat": now,
        "exp": now + 600,
    }
    business_id = str(uuid.uuid4())
    service_claims = {
        **base,
        "sub": "autom8_data",
        "business_id": business_id,
        "permissions": [],
    }
    user_claims = {
        **base,
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "business_id": business_id,
        "roles": ["admin"],
        "permissions": ["read:data", "write:data"],
        "token_type": "user_access",
    }
    operator_claims = {
        **base,
        "sub": f"operator:{uuid.uuid4()}",
        "permissions": ["analytics:aggregate"],
        "token_type": "operator_access",
    }
    # The two agent token forms differ only in how the delegated grants are
    # written: "minted" is the form the auth service issues today, "alternate"
    # is the other form the claims model accepts. Both must be treated alike.
    agent_minted: dict[str, Any] = {
        **base,
        "sub": str(uuid.uuid4()),
        "business_id": business_id,
        "email": "delegator@example.com",
        "token_type": "agent_access",
        "act": {"sub": f"agent:{uuid.uuid4()}", "agent_type": "assistant"},
        "delegation_session_id": str(uuid.uuid4()),
        "scope": ["intake:write"],
    }
    agent_alternate = {**agent_minted, "scope": "intake:write", "scopes": ["intake:write"]}
    pem = keypair.private_key_pem
    return Credentials(
        service_jwt=create_test_token(pem, _KID, service_claims),
        user_jwt=create_test_token(pem, _KID, user_claims),
        operator_jwt=create_test_token(pem, _KID, operator_claims),
        agent_jwt_minted=create_test_token(pem, _KID, agent_minted),
        agent_jwt_alternate=create_test_token(pem, _KID, agent_alternate),
        asana_pat="1/" + secrets.token_hex(12),
        webhook_url_token=secrets.token_urlsafe(24),
    )


@pytest.fixture(scope="module")
def _served_app(
    keypair: RSAKeyPairFixture,
    credentials: Credentials,
) -> Iterator[tuple[TestClient, Reached]]:
    """Real app + real middleware + real auth dependencies, sentinel handlers.

    Module-scoped: one app and one middleware stack serve every request in
    this module, so the run stays well under a few seconds.
    """
    jwk = create_jwks_document(keypair.public_key, _KID)["keys"][0]

    async def _get_key(self: Any, kid: str, retry_on_miss: bool = True) -> dict[str, Any]:
        from autom8y_auth.errors import UnknownKeyIDError

        if kid != _KID:
            raise UnknownKeyIDError(f"unknown kid {kid}")
        return jwk

    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("AUTH__DEV_MODE", raising=False)
        mp.setenv("ASANA_PAT", "bot-pat-" + secrets.token_hex(8))
        mp.setattr("autom8y_auth._jwks.JWKSClient.get_key", _get_key)
        mp.setattr(
            webhooks_module,
            "get_settings",
            lambda: SimpleNamespace(
                webhook=SimpleNamespace(inbound_token=credentials.webhook_url_token)
            ),
        )
        mp.setattr(limiter, "enabled", False)
        clear_bot_pat_cache()
        reset_auth_client()

        reached = Reached()
        app = create_app()
        _install_sentinels(app, reached)
        # Not used as a context manager: the lifespan (entity discovery, cache
        # warm-up) never runs, so nothing leaves the process.
        yield TestClient(app, raise_server_exceptions=False), reached
        clear_bot_pat_cache()
        reset_auth_client()


@pytest.fixture
def harness(_served_app: tuple[TestClient, Reached]) -> tuple[TestClient, Reached]:
    client, reached = _served_app
    reached.clear()
    return client, reached


def _concrete_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


def _bearer_for(token_class: TokenClass, creds: Credentials) -> str | None:
    return {
        TokenClass.SERVICE_JWT: creds.service_jwt,
        TokenClass.ASANA_PAT: creds.asana_pat,
        TokenClass.USER_JWT: creds.user_jwt,
        TokenClass.OPERATOR_JWT: creds.operator_jwt,
        TokenClass.AGENT_JWT: creds.agent_jwt_minted,
    }.get(token_class)


def _request(
    client: TestClient,
    method: str,
    path: str,
    token_class: TokenClass,
    creds: Credentials,
    *,
    agent_token: str | None = None,
) -> Any:
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    bearer = agent_token if token_class is TokenClass.AGENT_JWT and agent_token else None
    bearer = bearer or _bearer_for(token_class, creds)
    if bearer is not None:
        headers["Authorization"] = f"Bearer {bearer}"
    if token_class is TokenClass.WEBHOOK_URL_TOKEN:
        params["token"] = creds.webhook_url_token
    return client.request(method, _concrete_path(path), headers=headers, params=params)


_ALL_KEYS = sorted(ROUTE_TOKEN_TABLE)


def test_concrete_paths_route_to_their_own_route(walked_app: FastAPI) -> None:
    """Precondition: each probe path is matched first by the route it probes."""
    wrong = {}
    for key in _ALL_KEYS:
        method, path = key.split(" ", 1)
        scope = {"type": "http", "path": _concrete_path(path), "method": method}
        first = next(r for r in walked_app.routes if r.matches(scope)[0] is Match.FULL)
        if first.path != path:
            wrong[key] = first.path
    assert not wrong, f"probe paths shadowed by another route: {wrong}"


# ---------------------------------------------------------------------------
# Behavioral guard: non-agent token classes
#
# One test per token class walks every route and reports every disagreement at
# once, so a failure names all drifted routes rather than the first one.
# ---------------------------------------------------------------------------


def _outcome(response: Any, reached: Reached, path: str) -> str:
    if reached == [path]:
        return "admitted"
    if reached:
        return f"reached another handler {reached}"
    return f"refused {response.status_code}"


# A token without a business is refused by the app's business requirement
# before the route dependency runs; both answers are refusals at authentication.
_REFUSAL_STATUSES: dict[TokenClass, frozenset[int]] = {
    TokenClass.OPERATOR_JWT: frozenset({400, 401}),
}

_NON_AGENT_CLASS_PARAMS = [
    pytest.param(
        c,
        marks=pytest.mark.skipif(
            not SDK_HAS_OPERATOR_CLAIMS, reason="requires SDK operator support"
        ),
    )
    if c is TokenClass.OPERATOR_JWT
    else c
    for c in TokenClass
    if c is not TokenClass.AGENT_JWT
]


@pytest.mark.parametrize("token_class", _NON_AGENT_CLASS_PARAMS, ids=str)
def test_non_agent_token_class_admission_matches_table(
    token_class: TokenClass,
    harness: tuple[TestClient, Reached],
    credentials: Credentials,
) -> None:
    client, reached = harness
    refusal = _REFUSAL_STATUSES.get(token_class, frozenset({401}))
    disagreements: dict[str, str] = {}
    for key in _ALL_KEYS:
        method, path = key.split(" ", 1)
        mechanism, allowed = ROUTE_TOKEN_TABLE[key]
        reached.clear()
        response = _request(client, method, path, token_class, credentials)
        status = response.status_code
        if mechanism is Mechanism.PUBLIC:
            ok = status < 400
            want = "served (credential ignored)"
        elif token_class in allowed:
            ok = status == 200 and reached == [path]
            want = "admitted"
        else:
            ok = status in refusal and not reached
            want = f"refused {sorted(refusal)}"
        if not ok:
            disagreements[key] = f"want {want}, got {_outcome(response, reached, path)}"
    assert not disagreements, f"{token_class}: {disagreements}"


# ---------------------------------------------------------------------------
# Behavioral guard: agent tokens
# ---------------------------------------------------------------------------

_AGENT_SHAPES = ["minted", "alternate"]

_NON_ADMIT_KEYS = sorted(
    k
    for k, (m, _a) in ROUTE_TOKEN_TABLE.items()
    if m is not Mechanism.PUBLIC and k not in AGENT_ADMIT_ROUTES
)
_PUBLIC_KEYS = sorted(k for k, (m, _a) in ROUTE_TOKEN_TABLE.items() if m is Mechanism.PUBLIC)


def _agent_token(creds: Credentials, shape: str) -> str:
    return creds.agent_jwt_minted if shape == "minted" else creds.agent_jwt_alternate


def _agent_request(
    client: TestClient, key: str, creds: Credentials, shape: str, reached: Reached
) -> Any:
    method, path = key.split(" ", 1)
    reached.clear()
    return _request(
        client,
        method,
        path,
        TokenClass.AGENT_JWT,
        creds,
        agent_token=_agent_token(creds, shape),
    )


def _shapes(*hard: str) -> list[Any]:
    """Agent shapes. Shapes named in ``hard`` are hard checks everywhere; the
    rest are strict xfails until SDK agent support lands."""
    return [
        shape
        if shape in hard
        else pytest.param(
            shape,
            marks=pytest.mark.xfail(
                condition=not SDK_HAS_AGENT_CLAIMS,
                strict=True,
                reason=_PENDING_SDK_AGENT_SUPPORT,
            ),
        )
        for shape in _AGENT_SHAPES
    ]


@pytest.mark.parametrize("shape", _shapes("minted"))
def test_agent_token_never_reaches_a_non_admit_handler(
    shape: str,
    harness: tuple[TestClient, Reached],
    credentials: Credentials,
) -> None:
    client, reached = harness
    leaked = {}
    for key in _NON_ADMIT_KEYS:
        response = _agent_request(client, key, credentials, shape, reached)
        if reached:
            leaked[key] = _outcome(response, reached, key.split(" ", 1)[1])
    assert not leaked, f"agent ({shape}) reached handlers: {leaked}"


@pytest.mark.parametrize("shape", _shapes("minted"))
def test_agent_token_does_not_reach_admit_handlers_before_admission(
    shape: str,
    harness: tuple[TestClient, Reached],
    credentials: Credentials,
) -> None:
    """Pins today's state on the admit routes: no agent reaches their handlers.

    Remove this test in the same change that removes the admission xfail on
    ``test_agent_token_is_admitted_on_target_routes``.
    """
    client, reached = harness
    leaked = {}
    for key in sorted(AGENT_ADMIT_ROUTES):
        response = _agent_request(client, key, credentials, shape, reached)
        if reached:
            leaked[key] = _outcome(response, reached, key.split(" ", 1)[1])
    assert not leaked, f"agent ({shape}) reached admit handlers before admission: {leaked}"


@pytest.mark.parametrize("shape", _shapes())
def test_agent_token_is_refused_with_401_on_non_admit_routes(
    shape: str,
    harness: tuple[TestClient, Reached],
    credentials: Credentials,
) -> None:
    client, reached = harness
    wrong = {}
    for key in _NON_ADMIT_KEYS:
        response = _agent_request(client, key, credentials, shape, reached)
        if response.status_code != 401 or reached:
            wrong[key] = _outcome(response, reached, key.split(" ", 1)[1])
    assert not wrong, f"agent ({shape}) not refused with 401: {wrong}"


@pytest.mark.parametrize("shape", _shapes())
def test_agent_token_never_causes_a_server_error(
    shape: str,
    harness: tuple[TestClient, Reached],
    credentials: Credentials,
) -> None:
    """Every mounted route answers an agent token without a server error.

    Public routes answer exactly as they do for an anonymous request.
    Authenticated routes outside the admit set refuse with 401 or 403. The admit
    routes only need to avoid a server error here; their admission expectations live
    in their own tests.
    """
    client, reached = harness
    wrong = {}
    for key in _ALL_KEYS:
        method, path = key.split(" ", 1)
        response = _agent_request(client, key, credentials, shape, reached)
        status = response.status_code
        if key in _PUBLIC_KEYS:
            reached.clear()
            anonymous = _request(client, method, path, TokenClass.ANONYMOUS, credentials)
            if status != anonymous.status_code or status >= 400:
                wrong[key] = f"status {status}, anonymous {anonymous.status_code}"
        elif key in AGENT_ADMIT_ROUTES:
            if status >= 500:
                wrong[key] = f"status {status}"
        elif status not in (401, 403) or reached:
            wrong[key] = _outcome(response, reached, path)
    assert not wrong, f"agent ({shape}): {wrong}"


@pytest.mark.parametrize("shape", _AGENT_SHAPES)
@pytest.mark.parametrize(
    "key",
    [
        pytest.param(k, marks=pytest.mark.xfail(strict=True, reason=_AGENT_ADMISSION_PENDING))
        for k in sorted(AGENT_ADMIT_ROUTES)
    ],
)
def test_agent_token_is_admitted_on_target_routes(
    key: str,
    shape: str,
    harness: tuple[TestClient, Reached],
    credentials: Credentials,
) -> None:
    """Admitted means the handler ran and the request was seen as an agent."""
    client, reached = harness
    path = key.split(" ", 1)[1]
    response = _agent_request(client, key, credentials, shape, reached)
    assert response.status_code == 200 and reached == [path], (
        f"{key}: agent ({shape}) {_outcome(response, reached, path)} {response.text[:300]}"
    )
    assert reached.claims_types == ["AgentClaims"], (
        f"{key}: admitted with claims {reached.claims_types}, not as an agent"
    )
