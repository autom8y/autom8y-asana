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
from unittest.mock import patch

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
    }
    with patch.dict(os.environ, env_overrides):
        from autom8_asana.api.main import create_app

        return create_app()


app = _create_fuzz_app()

schema = from_asgi("/openapi.json", app=app)


@schema.parametrize()
def test_api(case):
    """Validate each endpoint against its OpenAPI schema."""
    case.call_and_validate()
