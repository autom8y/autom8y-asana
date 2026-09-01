"""GET /v1/forwarding-stage/census — the tripwire's second operand, at the wire.

The service-level teeth live in ``tests/unit/services/test_forwarding_stage_census.py``
(total-vs-refuse, the absent-fuel invariant, the two-sided tripwire arms). This
module locks the properties that only exist AT THE ROUTE:

  * every service refusal becomes a typed HTTP error, never a 200 with a
    degraded count — the consumer must not be able to mistake an outage for
    "no clinic is Verified";
  * the route is READ-ONLY and carries no write class, so SEC-001's
    deny-by-default write-class authorization does not apply to it;
  * it presents the EXISTING shared S2S identity and mints no new principal.

The last one is not incidental. U-4's finding is that a caller presenting a
DIFFERENT principal becomes structurally invisible to the OBSERVE-mode allowlist
harvest — authentication precedes authorization, so a caller that cannot
authenticate never reaches the gate that emits the harvest receipt. Creating a
second instance of that class here, while closing the first, would be a
self-inflicted repeat.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.config import get_settings
from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.forwarding_stage_census import ASANA_MAX_PAGE_SIZE
from autom8_asana.services.resolver import EntityProjectRegistry

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}
CENSUS_PATH = "/v1/forwarding-stage/census"

FIELD_GID = "1216419441591239"
VERIFIED_OPTION_GID = "opt-verified"
OPTION_GIDS_JSON = (
    '{"Sent":"opt-sent","Approved":"opt-approved","Verified":"opt-verified",'
    '"Stalled":"opt-stalled","Flowing":"opt-flowing","Live":"opt-live",'
    '"Inactive":"opt-inactive"}'
)

_ROUTE_SRC = (
    Path(__file__).resolve().parents[4] / "src/autom8_asana/api/routes/forwarding_stage_census.py"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _task(option_gid: str | None) -> dict[str, Any]:
    enum_value = {"gid": option_gid} if option_gid else None
    return {"gid": "t", "custom_fields": [{"gid": FIELD_GID, "enum_value": enum_value}]}


def _mock_jwt_validation(service_name: str = "email_booking_intake") -> AsyncMock:
    """The SAME claims shape /v1/receipts is tested with — one identity, two routes."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _mock_client(rows: list[dict[str, Any]], *, raises: Exception | None = None) -> MagicMock:
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    async def _get_paginated(path: str, *, params: dict[str, Any] | None = None):
        if raises is not None:
            raise raises
        start = int((params or {}).get("offset") or 0)
        page = rows[start : start + ASANA_MAX_PAGE_SIZE]
        nxt = start + ASANA_MAX_PAGE_SIZE
        return page, (str(nxt) if nxt < len(rows) else None)

    client._http = MagicMock()
    client._http.get_paginated = AsyncMock(side_effect=_get_paginated)
    return client


def _patches(client: MagicMock):
    return (
        patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ),
        patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            _mock_jwt_validation(),
        ),
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
        patch("autom8_asana.api.dependencies.get_bot_pat", return_value="test_bot_pat"),
        patch(
            "autom8_asana.api.routes.forwarding_stage_census.AsanaClient",
            return_value=client,
        ),
    )


@pytest.fixture(autouse=True)
def _reset_singletons(monkeypatch):
    monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_FIELD_GID", FIELD_GID)
    monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_OPTION_GIDS", OPTION_GIDS_JSON)
    get_settings.cache_clear()
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    get_settings.cache_clear()
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects", new_callable=AsyncMock
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            app.state.entity_project_registry = EntityProjectRegistry.get_instance()

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as tc:
        yield tc


def _get(client: TestClient, mock_client: MagicMock):
    p = _patches(mock_client)
    with p[0], p[1], p[2], p[3], p[4]:
        return client.get(CENSUS_PATH, headers=AUTH_HEADER)


# ===========================================================================
# R-1 — the happy path returns a TOTAL with its audit trail.
# ===========================================================================


class TestCensusHappyPath:
    def test_r1a_green_returns_the_total_across_pages(self, client: TestClient) -> None:
        """GREEN: 5 Verified across 2 pages -> verified_count 5, pages_drained 2."""
        rows = [_task(VERIFIED_OPTION_GID) for _ in range(3)]
        rows += [_task("opt-live") for _ in range(97)]
        rows += [_task(VERIFIED_OPTION_GID) for _ in range(2)]
        rows += [_task(None) for _ in range(20)]

        response = _get(client, _mock_client(rows))

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["verified_count"] == 5
        assert data["tasks_scanned"] == 122
        assert data["pages_drained"] == 2
        # CENSUS-F-2: the trust condition is on the wire, and discriminates.
        assert data["terminal_page_full"] is False

    def test_r1b_response_carries_the_partition_so_the_operand_is_auditable(
        self, client: TestClient
    ) -> None:
        """stage_counts sums to field_present_count ON THE WIRE.

        The consumer alarms on verified_count. Shipping it without the means to
        check that no clinic was lost or double-counted would make it an
        unaccountable scalar the tripwire must simply believe.
        """
        rows = [_task(VERIFIED_OPTION_GID) for _ in range(4)]
        rows += [_task("opt-live") for _ in range(6)]
        rows += [_task(None) for _ in range(5)]

        data = _get(client, _mock_client(rows)).json()["data"]

        assert sum(data["stage_counts"].values()) == data["field_present_count"] == 15
        assert data["stage_counts"]["Verified"] == 4


# ===========================================================================
# R-2 — every refusal is a typed error, never a 200 with a degraded count.
# ===========================================================================


class TestCensusRefusals:
    def test_r2a_page_ceiling_truncation_is_502(self, client: TestClient, monkeypatch) -> None:
        """RED: the REACHABLE truncation guard -> 502 STAGE_CENSUS_TRUNCATED.

        ★ RE-AUTHORED FOR CENSUS-F-2. This case previously asserted that a
        lying continuation signal produced a 502. It does not, and cannot: the
        old detection ran a confirmation read at a SYNTHESIZED offset, and
        Asana offsets are opaque tokens that must round-trip. That branch was
        unreachable in production, so asserting it here certified a behaviour
        the live API could never exhibit.

        What IS reachable is the page ceiling, which this now exercises: a
        corpus deeper than `max_pages` refuses rather than returning a prefix.
        """
        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_CENSUS_MAX_PAGES", "1")
        get_settings.cache_clear()
        rows = [_task(VERIFIED_OPTION_GID) for _ in range(3)]
        rows += [_task("opt-live") for _ in range(97)]
        rows += [_task(VERIFIED_OPTION_GID) for _ in range(50)]

        response = _get(client, _mock_client(rows))

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "STAGE_CENSUS_TRUNCATED"

    def test_r2a2_a_lying_server_returns_the_flag_not_a_false_refusal(
        self, client: TestClient
    ) -> None:
        """HONEST NEGATIVE at the route: an undetectable lie is REPORTED.

        A server that truncates and claims completeness is not detectable with
        the fuel Asana provides. The route therefore returns 200 with the short
        count AND `terminal_page_full=True` -- the operator's hook. Asserting
        this keeps the limitation visible on the wire contract rather than
        letting a future reader assume the route catches it.
        """
        rows = [_task(VERIFIED_OPTION_GID) for _ in range(3)]
        rows += [_task("opt-live") for _ in range(97)]
        rows += [_task(VERIFIED_OPTION_GID) for _ in range(50)]
        mock = _mock_client(rows)

        async def _lying(path: str, *, params: dict[str, Any] | None = None):
            return rows[:ASANA_MAX_PAGE_SIZE], None

        mock._http.get_paginated = AsyncMock(side_effect=_lying)
        response = _get(client, mock)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["verified_count"] == 3, "true count is 53; the lie is undetected"
        assert data["terminal_page_full"] is True, "but the condition IS reported"

    def test_r2b_red_empty_corpus_is_502_not_a_zero(self, client: TestClient) -> None:
        """RED: zero tasks -> 502, never 200 with verified_count 0.

        A wrong project gid and an empty project are one shape from here, and a
        200/0 would read to the tripwire as a confident healthy zero.
        """
        response = _get(client, _mock_client([]))

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "STAGE_CENSUS_EMPTY_CORPUS"

    def test_r2c_red_field_absent_is_502_not_a_zero(self, client: TestClient) -> None:
        """RED: tasks present, field on none -> 502 STAGE_CENSUS_FIELD_ABSENT."""
        rows = [{"gid": "t", "custom_fields": []} for _ in range(5)]

        response = _get(client, _mock_client(rows))

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "STAGE_CENSUS_FIELD_ABSENT"

    def test_r2f_red_gid_drift_is_502_not_a_confident_zero(
        self, client: TestClient, monkeypatch
    ) -> None:
        """RED (CENSUS-F-1): a stale Verified gid -> 502, never 200 with 0.

        Broken INPUT: the configured option map carries a Verified gid the
        workspace no longer issues, so every Verified task lands in UNKNOWN.
        A 200/0 here is the most dangerous output this route can produce -- the
        tripwire would read it as a maximal keyspace_overcount against a
        perfectly healthy keyspace.
        """
        monkeypatch.setenv(
            "ASANA_API_FORWARDING_STAGE_OPTION_GIDS",
            OPTION_GIDS_JSON.replace('"Verified":"opt-verified"', '"Verified":"opt-STALE"'),
        )
        get_settings.cache_clear()
        rows = [_task(VERIFIED_OPTION_GID) for _ in range(7)]

        response = _get(client, _mock_client(rows))

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "STAGE_CENSUS_GID_DRIFT"

    def test_r2d_red_unconfigured_is_503(self, client: TestClient, monkeypatch) -> None:
        """RED: the pre-flip dark posture -> 503 STAGE_CENSUS_UNCONFIGURED.

        Distinguished from the 502s deliberately: an unconfigured census is an
        operator/config state (retryable after a config change), not a contract
        violation by the upstream.
        """
        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_FIELD_GID", "")
        get_settings.cache_clear()

        response = _get(client, _mock_client([_task(VERIFIED_OPTION_GID)]))

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "STAGE_CENSUS_UNCONFIGURED"

    def test_r2e_red_transport_failure_is_503_never_an_empty_census(
        self, client: TestClient
    ) -> None:
        """RED: a timeout -> 503, never 200/0.

        S-3 critic F-6 verbatim: a leaked error "could plausibly be caught
        somewhere as 'no contacts', which is the very ambiguity this surface
        exists to make impossible."
        """
        response = _get(client, _mock_client([], raises=TimeoutError("asana timeout")))

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "ASANA_UNAVAILABLE"

    def test_r2f_no_refusal_path_can_return_200(self, client: TestClient) -> None:
        """Aggregate guard: NONE of the degraded inputs yields a 2xx.

        A per-case assertion could drift one case at a time; this states the
        property the consumer actually depends on — there is no input for which
        this route reports a count it cannot vouch for.
        """
        degraded = [
            _mock_client([]),
            _mock_client([{"gid": "t", "custom_fields": []}]),
            _mock_client([], raises=TimeoutError("boom")),
            _mock_client([], raises=RuntimeError("unexpected")),
        ]

        for mock in degraded:
            assert _get(client, mock).status_code >= 400


# ===========================================================================
# R-3 — READ-ONLY, and no new principal. The two scope constraints.
# ===========================================================================


class TestCensusIsReadOnlyAndMintsNothing:
    def test_r3a_route_declares_no_write_class(self) -> None:
        """The route imports NO write-authz symbol and declares no write class.

        SEC-001's gate is per-route opt-in via the decorator's ``dependencies=``
        (see write_authz.py's own usage docstring), and GUARD-1's
        ``test_red_guard_does_not_trip_on_reads`` confirms reads are outside its
        scope. Asserted structurally so a later edit that adds a write here
        cannot pass silently as "still a read route".

        Checked over the AST's IMPORT nodes, not over the raw text. A substring
        scan would trip on this module's own docstring, which NAMES
        ``require_write_authz`` in order to explain its absence — the repo's own
        ``test_docstring_exemption_is_not_a_bypass`` guards the inverse of the
        same confusion. Prose about a symbol is not use of it.
        """
        import ast

        tree = ast.parse(_ROUTE_SRC.read_text())
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "write_authz" in node.module:
                    imported.add(node.module)
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)

        assert not any("write_authz" in name for name in imported)
        assert "WriteClass" not in imported
        assert "require_write_authz" not in imported
        assert "x-fleet-read-only" in _ROUTE_SRC.read_text()

    def test_r3b_route_issues_no_asana_mutation(self) -> None:
        """No write verb appears on this route's path.

        The Asana client surface for mutation is create/update/delete/post/put.
        A read route that grew one would still parse, deploy, and pass its
        happy-path test — this is the guard that would not.
        """
        source = _ROUTE_SRC.read_text()
        body = source.split("async def get_forwarding_stage_census", 1)[1]

        for verb in ("create_", "update_", "delete_", ".post(", ".put(", ".patch("):
            assert verb not in body, f"mutation verb {verb!r} on a read route"

    def test_r3c_green_serves_under_the_existing_s2s_identity(self, client: TestClient) -> None:
        """The SAME require_service_claims dependency /v1/receipts uses.

        Identity receipt: this test authenticates with the identical claims
        shape the receipts route is tested with (``service_name=
        email_booking_intake``), so the census presents no new principal and
        requires no new credential. See
        FINDING-u4-nudge-lambda-client-id-2026-09-01.md for why a distinct
        principal here would be a self-inflicted repeat of U-4.
        """
        source = _ROUTE_SRC.read_text()
        assert "require_service_claims" in source

        response = _get(client, _mock_client([_task(VERIFIED_OPTION_GID)]))

        assert response.status_code == 200

    def test_r3d_red_an_unauthenticated_request_is_refused(self, client: TestClient) -> None:
        """RED pair for 3c: no Authorization header -> 401, never an open read.

        Without this, 3c would also pass against a route that required no auth
        at all — which would be a genuinely worse outcome than a new principal.
        """
        p = _patches(_mock_client([_task(VERIFIED_OPTION_GID)]))
        with p[0], p[1], p[2], p[3], p[4]:
            response = client.get(CENSUS_PATH)

        assert response.status_code == 401

    def test_r3e_the_route_is_registered_and_reachable(self, app) -> None:
        """The route is mounted. An unregistered route is a 404 nobody notices.

        The EBI consumer's failure mode for a missing second source is
        STAGE_OF_RECORD_UNAVAILABLE — indistinguishable from this route simply
        never having been mounted, which is exactly the silence class this whole
        arc closes.
        """
        paths = {route.path for route in app.routes if hasattr(route, "path")}

        assert CENSUS_PATH in paths


# ===========================================================================
# R-4 — the request shape (the under-reporting filter must never appear).
# ===========================================================================


def test_r4_route_never_sends_completed_since(client: TestClient) -> None:
    """``completed_since`` must not reach the wire.

    Asana reads it as "incomplete OR completed since T", so the intuitive
    ``completed_since=now`` would EXCLUDE every completed task and silently
    under-report by exactly the population that finished onboarding — the named
    trap wearing a filter. Asserted at the route so a future "let's only count
    active clinics" edit trips a test rather than the tripwire.
    """
    mock = _mock_client([_task(VERIFIED_OPTION_GID) for _ in range(3)])

    _get(client, mock)

    assert mock._http.get_paginated.await_count >= 1
    for call in mock._http.get_paginated.await_args_list:
        assert "completed_since" not in call.kwargs["params"]


def test_r5_openapi_advertises_the_read_only_marker(app) -> None:
    """The read-only declaration is machine-readable, not just prose.

    Fleet tooling reads ``x-fleet-*`` extensions; a human-only claim that this
    route is read-only would be invisible to every automated audit that matters.
    """
    schema = app.openapi()
    operation = schema["paths"][CENSUS_PATH]["get"]

    assert operation.get("x-fleet-read-only") is True
    assert "x-fleet-side-effects" not in operation

    # And the response model is the census shape, not a bare integer.
    assert re.search(r"ForwardingStageCensusResponse", str(operation))


def test_r6_openapi_publishes_the_refusal_taxonomy(app) -> None:
    """502 and 503 are ADVERTISED, not merely documented in the docstring.

    For this route the refusals ARE the contract. A generated client that saw
    only 200/4xx would treat a 502 as an unexpected error — and the natural
    handling of an unexpected error in a counting client is a fallback default,
    which would reintroduce the ambiguous zero on the CLIENT side after the
    server deliberately refused to produce it. Publishing them makes
    "never interpret as zero" a machine-visible instruction.
    """
    operation = app.openapi()["paths"][CENSUS_PATH]["get"]

    assert "502" in operation["responses"]
    assert "503" in operation["responses"]
    for code in ("502", "503"):
        assert "NEVER interpret as zero" in operation["responses"][code]["description"]
