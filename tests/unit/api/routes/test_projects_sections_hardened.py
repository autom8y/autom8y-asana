"""Hard-gate tests for the token-safe, scoped GET /sections capability.

These tests exercise the FORK-R REUSE-branch hardening applied to
``GET /api/v1/projects/{gid}/sections`` (``routes/projects.py``). Each test
maps to a hard-gate from the TDD §5 gate table
(``.ledge/specs/TDD-asana-pat-read-route-and-wreg.md``):

- **H1** (auth) — the route requires a valid S2S JWT via
  ``require_service_claims``; unauthenticated + PAT-token requests fail closed
  and the forbidden plaintext-PAT mode is impossible by construction.
- **H2** (BOLA/IDOR) — the route is pinned to ``SECTION_LIST_PROJECT_ALLOWLIST``;
  any non-allowlisted ``{gid}`` fails closed (404).
- **H3** (path/verb) — GET-only; ``X-HTTP-Method-Override`` is ignored; the
  outbound Asana URL is built server-side from the allowlisted ``{gid}``.
- **H4** (log hygiene) — neither the bearer token nor the brokered bot PAT
  appears in emitted logs.
- **H6** (identity TTL) — an expired/invalid short-lived JWT is rejected.

NOTE on status codes: authentication failures (H1/H6, PAT rejection) resolve to
**401** — the correct status for missing/invalid credentials — not 403. The
security property the gate demands (no anonymous access, no PAT oracle, fail
closed) holds regardless; 403 would incorrectly imply an authenticated caller.
The allowlist gate (H2) returns **404** to avoid confirming the existence of
non-allowlisted projects (enumeration defense).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.api.routes.projects import (
    SECTION_LIST_PROJECT_ALLOWLIST,
    get_s2s_section_client,
)
from autom8_asana.auth.bot_pat import BotPATError, clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.core.project_registry import UNIT_PROJECT
from autom8_asana.services.resolver import EntityProjectRegistry

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CUTOVER_GID = UNIT_PROJECT  # "1201081073731555" — the single allowlisted project
OTHER_GID = "1200653012566782"  # real-shaped BUT non-allowlisted project GID
NON_NUMERIC_GID = "not-a-gid"

JWT_TOKEN = "header.payload.signature"  # 2 dots -> detected as JWT
PAT_TOKEN = "0/1234567890abcdef1234567890abcdef"  # 0 dots -> detected as PAT

JWT_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}
PAT_HEADER = {"Authorization": f"Bearer {PAT_TOKEN}"}

SENTINEL_BOT_PAT = "0/SENTINEL_BOT_PAT_VALUE_neverlogged_1234567890"

SAMPLE_SECTION = {
    "gid": "9111111111111111",
    "name": "Active",
    "project": {"gid": CUTOVER_GID, "name": "Business Units"},
}


def _valid_claims_mock(service_name: str = "autom8_data") -> AsyncMock:
    """AsyncMock returning valid ServiceClaims-shaped object."""
    claims = MagicMock()
    claims.sub = f"service:{service_name}"
    claims.service_name = service_name
    claims.scope = "multi-tenant"
    claims.permissions = []
    return AsyncMock(return_value=claims)


# ---------------------------------------------------------------------------
# Fixtures (function-scoped, self-contained — shadow the conftest app/client)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset() -> Generator[None, None, None]:
    clear_bot_pat_cache()
    reset_auth_client()
    yield
    clear_bot_pat_cache()
    reset_auth_client()


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch):
    """Create a test app with lifespan discovery mocked."""
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid=CUTOVER_GID,
                project_name="Business Units",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as tc:
        yield tc


@pytest.fixture()
def section_client_mock() -> MagicMock:
    """A mock AsanaClient whose paginated section fetch returns one section."""
    mock = MagicMock()
    mock._http = MagicMock()
    mock._http.get_paginated = AsyncMock(return_value=([SAMPLE_SECTION], None))
    return mock


@pytest.fixture()
def scoped_client(app, client, section_client_mock):
    """TestClient with ``get_s2s_section_client`` overridden to a mock.

    Use for behavior tests (allowlist / URL / pagination) where auth is not the
    subject under test. Auth-gate tests use ``client`` directly so
    ``require_service_claims`` runs for real.
    """

    async def _override() -> MagicMock:
        return section_client_mock

    app.dependency_overrides[get_s2s_section_client] = _override
    try:
        yield client, section_client_mock
    finally:
        app.dependency_overrides.pop(get_s2s_section_client, None)


# ===========================================================================
# H1 — authentication required; plaintext-PAT mode impossible by construction
# ===========================================================================


class TestH1Auth:
    def test_unauthenticated_request_fails_closed(self, client: TestClient) -> None:
        """No Authorization header -> 401 (never an anonymous section oracle)."""
        resp = client.get(f"/api/v1/projects/{CUTOVER_GID}/sections")
        assert resp.status_code == 401
        assert "data" not in resp.json()  # no section payload leaked

    def test_pat_token_rejected(self, client: TestClient) -> None:
        """A PAT bearer token is rejected: the forbidden plaintext-PAT mode is
        impossible by construction on this route (require_service_claims)."""
        resp = client.get(
            f"/api/v1/projects/{CUTOVER_GID}/sections",
            headers=PAT_HEADER,
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "SERVICE_TOKEN_REQUIRED"

    def test_valid_jwt_passes_auth_then_brokers_server_side(self, client: TestClient) -> None:
        """A valid S2S JWT passes the auth gate and reaches the server-side
        broker; when the broker cannot resolve the bot PAT it fails closed
        (503) — it never degrades to a caller-plaintext read or an anonymous
        200. The broker is stubbed to be unavailable so the test is
        deterministic regardless of any ambient ASANA_PAT."""
        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _valid_claims_mock(),
            ),
            patch(
                "autom8_asana.api.routes.projects.get_bot_pat",
                side_effect=BotPATError("bot PAT unavailable in test"),
            ),
        ):
            resp = client.get(
                f"/api/v1/projects/{CUTOVER_GID}/sections",
                headers=JWT_HEADER,
            )
        # Past auth (not 401); broker unavailable -> fail closed 503, no 200.
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "S2S_NOT_CONFIGURED"

    def test_valid_jwt_happy_path_returns_sections(self, scoped_client) -> None:
        """Two-sided of H1: a properly authenticated read returns 200 + data."""
        test_client, mock_sdk = scoped_client
        resp = test_client.get(
            f"/api/v1/projects/{CUTOVER_GID}/sections",
            headers=JWT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["data"][0]["name"] == "Active"


# ===========================================================================
# H2 — BOLA/IDOR: route pinned to the project allowlist
# ===========================================================================


class TestH2Allowlist:
    def test_allowlist_contains_only_the_cutover_project(self) -> None:
        assert CUTOVER_GID in SECTION_LIST_PROJECT_ALLOWLIST
        assert len(SECTION_LIST_PROJECT_ALLOWLIST) == 1

    def test_allowlisted_gid_returns_sections(self, scoped_client) -> None:
        test_client, mock_sdk = scoped_client
        resp = test_client.get(
            f"/api/v1/projects/{CUTOVER_GID}/sections",
            headers=JWT_HEADER,
        )
        assert resp.status_code == 200
        mock_sdk._http.get_paginated.assert_called_once_with(
            f"/projects/{CUTOVER_GID}/sections",
            params={"limit": 100},
        )

    def test_non_allowlisted_gid_fails_closed(self, scoped_client) -> None:
        """A different, real-shaped project GID must NOT return its sections."""
        test_client, mock_sdk = scoped_client
        resp = test_client.get(
            f"/api/v1/projects/{OTHER_GID}/sections",
            headers=JWT_HEADER,
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
        # The outbound Asana fetch must never fire for a non-allowlisted gid.
        mock_sdk._http.get_paginated.assert_not_called()

    def test_non_numeric_gid_fails_closed(self, scoped_client) -> None:
        """A non-numeric gid never reaches Asana (404 via allowlist; 422 via
        GidStr in production)."""
        test_client, mock_sdk = scoped_client
        resp = test_client.get(
            f"/api/v1/projects/{NON_NUMERIC_GID}/sections",
            headers=JWT_HEADER,
        )
        assert resp.status_code in (404, 422)
        mock_sdk._http.get_paginated.assert_not_called()


# ===========================================================================
# H3 — path/verb: GET-only, method-override ignored, server-built URL
# ===========================================================================


class TestH3PathVerb:
    def test_method_override_header_not_honored(self, scoped_client) -> None:
        """POST + X-HTTP-Method-Override: GET must NOT be treated as a GET read."""
        test_client, mock_sdk = scoped_client
        resp = test_client.post(
            f"/api/v1/projects/{CUTOVER_GID}/sections",
            headers={**JWT_HEADER, "X-HTTP-Method-Override": "GET"},
            json={},
        )
        assert resp.status_code == 405  # method not allowed; override ignored
        mock_sdk._http.get_paginated.assert_not_called()

    def test_outbound_url_built_server_side_from_pinned_gid(self, scoped_client) -> None:
        """The outbound Asana path is server-constructed from the allowlisted
        gid — the caller supplies no URL."""
        test_client, mock_sdk = scoped_client
        test_client.get(
            f"/api/v1/projects/{CUTOVER_GID}/sections?offset=cursor_abc",
            headers=JWT_HEADER,
        )
        mock_sdk._http.get_paginated.assert_called_once_with(
            f"/projects/{CUTOVER_GID}/sections",
            params={"limit": 100, "offset": "cursor_abc"},
        )


# ===========================================================================
# H4 — log hygiene: neither bearer token nor bot PAT appears in logs
# ===========================================================================


class TestH4LogHygiene:
    def test_bearer_token_and_bot_pat_never_logged(
        self,
        client: TestClient,
        section_client_mock: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Full real chain (auth + broker) with mocked externals: assert neither
        the JWT bearer token nor the brokered bot PAT value is emitted to logs."""
        # Force the no-pool fallback so the (patched) AsanaClient is used.
        client.app.state.client_pool = None  # type: ignore[attr-defined]

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _valid_claims_mock(),
            ),
            patch(
                "autom8_asana.api.routes.projects.get_bot_pat",
                return_value=SENTINEL_BOT_PAT,
            ),
            patch(
                "autom8_asana.api.routes.projects.AsanaClient",
                return_value=section_client_mock,
            ),
            caplog.at_level("DEBUG"),
        ):
            resp = client.get(
                f"/api/v1/projects/{CUTOVER_GID}/sections",
                headers=JWT_HEADER,
            )

        assert resp.status_code == 200
        log_text = caplog.text
        assert SENTINEL_BOT_PAT not in log_text
        assert JWT_TOKEN not in log_text


# ===========================================================================
# H6 — identity TTL: an expired/invalid short-lived JWT is rejected
# ===========================================================================


class TestH6IdentityTtl:
    def test_expired_jwt_rejected(self, client: TestClient) -> None:
        """An expired/invalid short-lived JWT (validation raises) -> rejected."""

        async def _raise(_token: str):
            raise ValueError("token expired")

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _raise,
        ):
            resp = client.get(
                f"/api/v1/projects/{CUTOVER_GID}/sections",
                headers=JWT_HEADER,
            )
        assert resp.status_code == 401
        assert "data" not in resp.json()
