"""Regression: fleet /v1/query/entities mount-order invariant (TENSION-009).

POST /v1/query/entities MUST be registered before the legacy
POST /v1/query/{entity_type} wildcard, or FastAPI routes it to the legacy
handler (entity_type="entities") and the fleet body fails QueryRequest
validation (422). The runtime guard ``_assert_fleet_query_mount_order`` (called
in ``create_app``) locks this; a regression makes app startup raise, which any
test that builds the app will surface.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI

from autom8_asana.api.main import _assert_fleet_query_mount_order


def _add(app: FastAPI, path: str) -> None:
    app.add_api_route(path, lambda: {"ok": True}, methods=["POST"])


def test_guard_raises_when_wildcard_precedes_fleet() -> None:
    """Wildcard-first registration (the regression) must raise."""
    app = FastAPI()
    _add(app, "/v1/query/{entity_type}")
    _add(app, "/v1/query/entities")
    with pytest.raises(RuntimeError, match="mount-order regression"):
        _assert_fleet_query_mount_order(app)


def test_guard_passes_when_fleet_precedes_wildcard() -> None:
    """Correct order (fleet before wildcard) must not raise."""
    app = FastAPI()
    _add(app, "/v1/query/entities")
    _add(app, "/v1/query/{entity_type}")
    _assert_fleet_query_mount_order(app)


def test_guard_noop_when_either_route_absent() -> None:
    """Defensive: absence of either route must not break startup."""
    app = FastAPI()
    _add(app, "/v1/healthz")
    _assert_fleet_query_mount_order(app)
