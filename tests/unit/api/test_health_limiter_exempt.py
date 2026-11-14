"""The liveness and readiness probes are exempt from the rate limiter (D-AF3 part 1).

Policy under test:

- ``/health`` (container liveness) and ``/ready`` (the ALB target-group probe)
  are never answered 429 by the limiter, however many requests one client
  sends.
- ``/health/deps`` is NOT exempt. It stays under the default limit, as does
  every other route. The teeth twins below send the same volume to limited
  routes and must see 429.

SlowAPI records an exemption by the handler's ``"{module}.{function name}"``
string, so a rename or a move silently restores the limit. The pinned names
below fail loudly in that case. Update them in the same change as any rename.

These tests drive the app built by ``create_app()`` with its real middleware
stack and the real module-level limiter. Only two things are stubbed: the
default limit is lowered so the volume stays small, and the probes' outbound
JWKS client is replaced so no request leaves the process.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from slowapi.middleware import _get_route_name

from autom8_asana.api import rate_limit
from autom8_asana.api.main import create_app
from autom8_asana.api.rate_limit import limiter
from autom8_asana.api.routes import health

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from fastapi import FastAPI

# Path -> the exact handler name SlowAPI matches against its exempt set.
PINNED_EXEMPT_PROBES: dict[str, str] = {
    "/health": "autom8_asana.api.routes.health.health_check",
    "/ready": "autom8_asana.api.routes.health.readiness_check",
}

# The one non-probe exemption: the D6 Asana webhook target, so a valid delivery is never
# answered 429 (TDD-asana-bench-D6-shadow-receiver section 4, TM-4; RL-1 and RL-2 live in
# tests/unit/api/routes/test_asana_hook_route.py).
PINNED_EXEMPT_HOOK: dict[str, str] = {
    "/api/v1/webhooks/asana/{handle}": "autom8_asana.api.routes.asana_hook.receive_asana_hook",
}

# Limited on purpose: the dependency probe keeps the default limit.
DEPS_PROBE_PATH = "/health/deps"
DEPS_PROBE_NAME = "autom8_asana.api.routes.health.deps_check"

# A JWT-excluded route with no route-level limit, so the global default applies.
LIMITED_PATH = "/docs"

TINY_LIMIT = 3
VOLUME = TINY_LIMIT * 5


class _OfflineHttpClient:
    """Stand-in for the probes' JWKS client that never opens a connection."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> _OfflineHttpClient:
        raise RuntimeError("outbound HTTP is disabled in this test")

    async def __aexit__(self, *exc: object) -> None:
        return None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The real app with a tiny default limit and no outbound HTTP."""
    monkeypatch.delenv("AUTH__DEV_MODE", raising=False)
    # _get_rate_limit_string reads get_settings() on every request.
    monkeypatch.setattr(
        rate_limit, "get_settings", lambda: SimpleNamespace(rate_limit_rpm=TINY_LIMIT)
    )
    monkeypatch.setattr(health, "Autom8yHttpClient", _OfflineHttpClient)

    app = create_app()
    limiter.reset()
    # No context manager: the lifespan (startup discovery) is not needed.
    yield TestClient(app, raise_server_exceptions=False)
    limiter.reset()


def _bucket_hits() -> dict[str, int]:
    """Hits per rate-limit key, read from the real limiter's storage."""
    hits: dict[str, int] = {}
    for storage_key, count in limiter._storage.storage.items():
        parts = storage_key.split("/")
        if parts[0] == "LIMITER" and len(parts) > 1:
            hits[parts[1]] = hits.get(parts[1], 0) + int(count)
    return hits


def _flood(client: TestClient, path: str) -> list[int]:
    return [client.get(path).status_code for _ in range(VOLUME)]


def _endpoints(app: FastAPI, path: str) -> list[Callable[..., Any]]:
    return [
        route.endpoint
        for route in app.routes
        if getattr(route, "path", None) == path and hasattr(route, "endpoint")
    ]


# ---------------------------------------------------------------------------
# (a) Name pinning
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("path", "name"), sorted(PINNED_EXEMPT_PROBES.items()))
def test_probe_handler_name_is_in_exempt_set(path: str, name: str) -> None:
    assert name in limiter._exempt_routes, (path, sorted(limiter._exempt_routes))


@pytest.mark.parametrize(("path", "name"), sorted(PINNED_EXEMPT_PROBES.items()))
def test_built_app_serves_probe_with_pinned_handler(path: str, name: str) -> None:
    """The endpoint the middleware resolves for each probe has the pinned name."""
    endpoints = _endpoints(create_app(), path)

    assert len(endpoints) == 1, (path, endpoints)
    assert _get_route_name(endpoints[0]) == name


def test_only_the_pinned_probes_are_exempt() -> None:
    """No other route of the built app is exempt, /health/deps included.

    The pinned set is the two probes plus the D6 webhook target, and nothing else.
    """
    app = create_app()
    exempt_served = {
        _get_route_name(endpoint)
        for route in app.routes
        if hasattr(route, "endpoint")
        for endpoint in [route.endpoint]
        if _get_route_name(endpoint) in limiter._exempt_routes
    }

    assert exempt_served == set(PINNED_EXEMPT_PROBES.values()) | set(PINNED_EXEMPT_HOOK.values())


def test_deps_probe_is_not_exempt() -> None:
    endpoints = _endpoints(create_app(), DEPS_PROBE_PATH)

    assert len(endpoints) == 1, endpoints
    assert _get_route_name(endpoints[0]) == DEPS_PROBE_NAME
    assert DEPS_PROBE_NAME not in limiter._exempt_routes


def test_docs_route_exists_so_the_teeth_twin_is_not_vacuous() -> None:
    """If docs were turned off, the /docs twin would 404 rather than test the limit."""
    endpoints = _endpoints(create_app(), LIMITED_PATH)

    assert len(endpoints) == 1, endpoints
    assert _get_route_name(endpoints[0]) not in limiter._exempt_routes


# ---------------------------------------------------------------------------
# (b) Two-sided behavior
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(PINNED_EXEMPT_PROBES))
def test_probe_flood_from_one_client_is_never_answered_429(client: TestClient, path: str) -> None:
    statuses = _flood(client, path)

    assert 429 not in statuses, statuses
    # Exempt requests never reach the key function or the storage.
    assert _bucket_hits() == {}


@pytest.mark.parametrize("path", [LIMITED_PATH, DEPS_PROBE_PATH])
def test_same_flood_to_a_limited_route_is_answered_429(client: TestClient, path: str) -> None:
    """Teeth twins: the identical volume to a limited route trips the limit."""
    statuses = _flood(client, path)

    assert 429 not in statuses[:TINY_LIMIT], statuses
    assert statuses[TINY_LIMIT:] == [429] * (VOLUME - TINY_LIMIT), statuses
