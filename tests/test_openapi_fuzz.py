"""Property-based API fuzz testing via Schemathesis.

Generates requests from the OpenAPI spec and validates responses
against the documented schema. Uses schemathesis.from_asgi() with
the asana service's create_app() factory for in-process testing.

FR-2: Schemathesis expansion to satellite services.
FR-3: Auth bypass via environment configuration.
FR-10: Hypothesis max_examples capped for CI performance.

Note: The asana service uses dual-mode auth (PAT + JWT). For fuzz
testing, JWT middleware is configured with a permissive exclude list,
and PAT routes will return auth errors (expected -- they require a
real Asana PAT). The fuzz test validates schema conformance, not
authorization behavior.
"""

from __future__ import annotations

import os
import re
from unittest.mock import patch

import httpx
import respx
from hypothesis import settings as hypothesis_settings
from schemathesis.openapi import from_asgi

_MAX_EXAMPLES = int(os.environ.get("SCHEMATHESIS_MAX_EXAMPLES", "50"))

hypothesis_settings.register_profile(
    "ci",
    max_examples=_MAX_EXAMPLES,
    deadline=None,
)
hypothesis_settings.load_profile(
    os.environ.get("HYPOTHESIS_PROFILE", "ci"),
)


def _create_fuzz_app():
    """Create asana app with mocked dependencies for fuzz testing.

    Sets environment to local with noop idempotency store.
    Auth middleware remains active but health/docs paths are excluded.
    PAT-authenticated routes will return 401/403 as expected.
    """
    env_overrides = {
        "AUTOM8Y_ENV": "local",
        "IDEMPOTENCY_STORE_BACKEND": "noop",
        "ASANA_BOT_PAT": "fuzz_test_pat",
        "ASANA_WEBHOOK_INBOUND_TOKEN": "fuzz_test_token",
        "ASANA_CACHE_S3_BUCKET": "fuzz-test-bucket",
        "AUTH_JWKS_URL": "http://localhost:9999/jwks.json",
        "STATUS_PUSH_ENABLED": "false",
    }
    with patch.dict(os.environ, env_overrides):
        # Mandate 2: Mock pool statistics to return static values
        # (prevent coroutine serialization errors in health endpoints)
        with patch(
            "autom8y_http.Autom8yHttpClient.get_pool_stats",
            return_value={"size": 10, "used": 0},
            create=True,
        ):
            from autom8_asana.api.main import create_app

            return create_app()


app = _create_fuzz_app()

schema = from_asgi("/openapi.json", app=app)


@schema.parametrize()
def test_api(case):
    """Validate each endpoint against its OpenAPI schema."""
    # Inject valid-looking PAT to test logic beyond auth middleware
    case.headers["Authorization"] = "Bearer fuzz_test_pat"

    # Use context manager to ensure fresh mock state for every hypothesis example
    # (Fixes FailedHealthCheck for function-scoped fixtures)
    with respx.mock(assert_all_called=False) as respx_mock:
        # Absolute catch-all for ALL outbound calls (Asana, Auth, Telemetry, etc.)
        # Returns schema-compliant data to satisfy ResponseValidationError.
        def asana_side_effect(request):
            path = request.url.path
            segments = [s for s in path.split("/") if s]

            # Generic resource data satisfying AsanaResource and User requirements
            resource_data = {
                "gid": "1234567890123456",
                "name": "Mock Resource",
                "resource_type": "task",
                "email": "fuzz@autom8y.io",
                "workspaces": [
                    {"gid": "1111111111111111", "resource_type": "workspace"}
                ],
            }

            # Heuristic for list vs single resource
            # If path ends in a numeric GID or is /me, it's a single resource.
            # Otherwise, plural paths like /users, /tasks are usually lists.
            is_single = (segments and segments[-1].isdigit()) or path.endswith("/me")

            # Special case: some POST actions return single resources even if path is plural
            if request.method == "POST":
                is_single = True

            data = resource_data if is_single else [resource_data]

            return httpx.Response(
                201 if request.method == "POST" else 200,
                json={
                    "data": data,
                    "meta": {
                        "request_id": "fuzz-mock-id",
                        "timestamp": "2026-04-09T12:00:00Z",
                    },
                },
            )

        respx_mock.route().mock(side_effect=asana_side_effect)

        case.call_and_validate()
