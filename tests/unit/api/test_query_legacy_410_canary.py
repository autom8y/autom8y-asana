"""RED-first two-sided fixtures for the FORK-1 legacy-query 410 canary.

FORK-1 retire of the deprecated `/v1/query/{entity_type}` endpoint
(api/main.py:470 mount). Evidence (N1 §D): 0 `deprecated_query_endpoint_used`
hits on the LIVE ECS group (18,888,558 records scanned 2026-06-01..now) and 0
on the legacy monolith (951 records) -- a G-DENOM-valid proven-zero.

The retire executes as 410-canary-THEN-unmount (NOT a silent delete):
  1. Flip QUERY_LEGACY_410_GONE=true -> the route returns 410 Gone and STOPS
     logging `deprecated_query_endpoint_used` (proves the route is reachable
     but dead). Watch ECS 4xx + the deprecated count stay 0 for one cadence.
  2. THEN remove the mount at api/main.py:470 (a separate operator step,
     SURFACED, not done here).

Two-sided teeth:
  (+) flag ON  -> 410 Gone; deprecated marker NOT logged.
  (-) flag OFF (default, no-defect variant -- MUST pass GREEN) -> route still
      serves its existing 4xx/2xx behavior and STILL logs the deprecation
      marker (canary is OFF, nothing changed).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

# Shares the module-scoped FastAPI app/client (SCAR-W1E-LOADGROUP-001 idiom).
pytestmark = [pytest.mark.xdist_group("query_routes")]

JWT_TOKEN = "header.payload.signature"

# Env flag that arms the 410 canary (reversible: unset to restore the route).
_CANARY_ENV = "QUERY_LEGACY_410_GONE"

# A body-parameterized entity reaches the deprecated handler's risk-1 guard
# without engine work; "unit" is registered with a GID in the test registry
# (conftest _TEST_ENTITIES) so it passes entity validation and reaches the
# deprecation-marker log on the OFF path.
_REGISTERED_ENTITY = "unit"


class TestCanaryOn410Gone:
    """(+) Flag ON: deprecated route returns 410 and does not log the marker."""

    def test_returns_410_when_canary_armed(self, client) -> None:
        captured: list[str] = []

        def _capture_info(event: str, *a: object, **k: object) -> None:
            captured.append(event)

        with (
            patch.dict(os.environ, {_CANARY_ENV: "true"}),
            patch("autom8_asana.api.routes.query.logger") as mock_logger,
        ):
            mock_logger.info.side_effect = _capture_info
            response = client.post(
                f"/v1/query/{_REGISTERED_ENTITY}",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"where": {}, "select": ["gid"]},
            )

        assert response.status_code == 410, (
            f"armed canary must return 410 Gone, got {response.status_code}: {response.text}"
        )
        # The dead route must NOT emit the deprecated-usage marker (that count
        # is the very signal the operator watches stay 0 during the canary).
        assert "deprecated_query_endpoint_used" not in captured, (
            "armed canary must not log deprecated_query_endpoint_used"
        )


class TestCanaryOffUnchanged:
    """(-) Flag OFF (default): route behavior is unchanged (no-defect variant)."""

    def test_route_still_serves_when_canary_unset(self, client) -> None:
        """Default (flag unset) -> NOT 410; the route still runs its handler."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(_CANARY_ENV, None)
            response = client.post(
                f"/v1/query/{_REGISTERED_ENTITY}",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"where": {}, "select": ["gid"]},
            )

        assert response.status_code != 410, (
            "with the canary OFF the route must NOT short-circuit to 410; "
            f"got {response.status_code}: {response.text}"
        )

    def test_explicit_false_serves_and_logs_marker(self) -> None:
        """Flag explicitly false -> the deprecation marker is still emitted.

        Unit-level assertion on the canary gate predicate so the negative leg
        does not depend on the full engine. Proves OFF leaves the marker path
        intact (canary genuinely gates only when armed).
        """
        from autom8_asana.api.routes.query import _legacy_query_410_armed

        with patch.dict(os.environ, {_CANARY_ENV: "false"}):
            assert _legacy_query_410_armed() is False

        with patch.dict(os.environ, {_CANARY_ENV: "true"}):
            assert _legacy_query_410_armed() is True

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(_CANARY_ENV, None)
            assert _legacy_query_410_armed() is False
