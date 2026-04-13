"""SC-06 CI probe: verify ``/openapi.json`` is reachable and returns a valid schema.

Per TDD-fleet-api-sovereignty-s2 §4.2.4, every fleet satellite ships one
probe test at this path and test name so QA can grep across the fleet.

Scope (VERIFY-CI-ONLY): the endpoint is already exposed at the app-factory
level on all 5 satellites (S1 Phase 1 Thread G HIGH-confidence finding).
This test asserts the runtime accessibility contract in CI, so a
regression that accidentally breaks the spec-serving path is caught
before deploy.
"""

from __future__ import annotations

import os

# Environment setup required BEFORE importing the asana app factory.
# The JWTAuthMiddleware default ``AuthSettings`` refuses to build when the
# production JWKS URL is paired with ``AUTOM8Y_ENV != production`` (fleet
# production-URL guard).  The asana ``tests/conftest.py`` already sets
# ``AUTH__JWKS_URL`` to localhost and ``AUTOM8Y_ENV=test``, so we only need
# a non-conflicting idempotency backend here.  We deliberately do NOT set
# ``AUTH__DEV_MODE=true`` because that requires ``AUTOM8Y_ENV=LOCAL``,
# which would fight the conftest fixture.  Asana's production ``create_app``
# already declares ``/openapi.json`` in ``JWTAuthConfig.exclude_paths``, so
# the probe runs without authentication.
os.environ.setdefault("IDEMPOTENCY_STORE_BACKEND", "noop")

from fastapi.testclient import TestClient
from openapi_spec_validator import validate

from autom8_asana.api.main import create_app


def test_openapi_endpoint_returns_valid_schema() -> None:
    """``GET /openapi.json`` returns 200 and a structurally valid OpenAPI spec.

    Asana's ``JWTAuthConfig.exclude_paths`` already lists ``/openapi.json``,
    so this probe runs without authentication and asserts the spec is
    parseable by ``openapi-spec-validator``.
    """
    app = create_app()
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200, (
        f"/openapi.json returned {response.status_code}; expected 200. Body: {response.text[:200]}"
    )

    spec = response.json()
    assert isinstance(spec, dict)
    assert "openapi" in spec, "spec missing 'openapi' version field"
    assert "paths" in spec, "spec missing 'paths'"

    # openapi-spec-validator raises on structurally invalid specs.
    validate(spec)
