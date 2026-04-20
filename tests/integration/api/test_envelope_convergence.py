"""Integration tests for WS-B1+B2 P1-D canonical error envelope + security headers.

Verifies that autom8y-asana, after the WS-B1+B2 Sprint-3 convergence
migration, exposes:

- Canonical fleet ``ErrorResponse`` envelope (``{error: {...}, meta: {...}}``)
  on every error path, namespaced to ``ASANA-*`` wire codes.
- ``ASANA-VAL-001`` on malformed validation requests (via
  ``register_validation_handler(app, service_code_prefix="ASANA")``).
- ``ASANA-AUTH-002`` on webhook signature-invalid requests.
- ``SecurityHeadersMiddleware`` shared with ads/scheduling — HSTS,
  X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and
  Cache-Control: no-store on non-docs paths.  Header set MUST be
  byte-identical to the ads and scheduling PT-03 captures.

Per ADR-canonical-error-vocabulary P1-D and the WS-B1 P1-A exit artifact,
these tests enforce PT-03 Phase-1 exit criteria at CI time.
"""

from __future__ import annotations

import pytest
from autom8y_api_schemas.errors import FleetError
from autom8y_api_schemas.middleware import SecurityHeadersMiddleware
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from autom8_asana.api.errors import fleet_error_handler

# ---------------------------------------------------------------------------
# Self-contained test app mirroring production wiring
#
# The production create_app() factory carries considerable weight
# (auth middleware, idempotency, lifespan, JWKS probes) that is
# out of scope for this test.  To verify envelope convergence and
# header byte-identity, we build a minimal app wired with the exact
# three WS-B1+B2 P1-D additions under test:
#   1. register_validation_handler(service_code_prefix="ASANA")
#   2. SecurityHeadersMiddleware (same class ads/scheduling install)
#   3. FleetError catch-all -> fleet_error_handler
# ---------------------------------------------------------------------------


class _PingRequest(BaseModel):
    """A trivial request model used to exercise the 422 validation path."""

    gid: str
    name: str


@pytest.fixture
def asana_test_app() -> FastAPI:
    """Minimal FastAPI app wired with the three WS-B1+B2 P1-D integration points."""
    from autom8y_api_schemas.validation import register_validation_handler

    app = FastAPI()

    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/api/v1/ping")
    def ping(body: _PingRequest) -> dict[str, str]:
        return {"gid": body.gid, "name": body.name}

    app.include_router(router)

    # WS-B1+B2 P1-D #1: canonical 422 handler with ASANA prefix.
    register_validation_handler(app, service_code_prefix="ASANA")

    # WS-B1+B2 P1-D #2: shared security headers middleware.
    app.add_middleware(SecurityHeadersMiddleware)

    # WS-B1+B2 P1-D #3: FleetError catch-all.
    app.exception_handler(FleetError)(fleet_error_handler)

    return app


@pytest.fixture
def client(asana_test_app: FastAPI) -> TestClient:
    return TestClient(asana_test_app)


# ---------------------------------------------------------------------------
# Deliverable 6: canonical envelope assertions
# ---------------------------------------------------------------------------


class TestCanonicalValidationEnvelope:
    """Malformed POST bodies yield canonical ``ASANA-VAL-001`` envelope."""

    def test_malformed_request_returns_canonical_envelope(self, client: TestClient) -> None:
        """POST with missing required fields returns fleet ErrorResponse envelope."""
        response = client.post(
            "/api/v1/ping",
            json={"garbage": "value"},  # missing gid + name, extra field
        )

        assert response.status_code == 422
        assert response.headers["content-type"].startswith("application/json")

        body = response.json()

        # WS-B1+B2 P1-D: canonical {"error": {...}, "meta": {...}} shape.
        assert set(body.keys()) == {"error", "meta"}

        # Error envelope: ASANA-VAL-001 (not FLEET-VAL-001, not default
        # FastAPI {"detail": [...]}).
        err = body["error"]
        assert err["code"] == "ASANA-VAL-001"
        assert err["retryable"] is False
        # Body-level retry guidance: must be explicit null (not missing).
        assert "retry_after_seconds" in err
        assert err["retry_after_seconds"] is None
        # Validation errors payload carried as a structured list.
        assert "details" in err
        validation_errors = err["details"]["validation_errors"]
        assert isinstance(validation_errors, list)
        assert len(validation_errors) >= 2
        fields_missing = {e["field"] for e in validation_errors if e["type"] == "missing"}
        assert "body.gid" in fields_missing
        assert "body.name" in fields_missing

        # Meta envelope: non-empty request_id and iso8601 timestamp.
        meta = body["meta"]
        assert isinstance(meta["request_id"], str)
        assert len(meta["request_id"]) > 0
        assert "timestamp" in meta

    def test_canonical_envelope_schema_matches_ads_and_scheduling(self, client: TestClient) -> None:
        """The envelope's top-level keys and error-object keys match the
        ads and scheduling PT-03 reference captures byte-for-byte (modulo
        the service-specific code and request_id/timestamp).
        """
        response = client.post(
            "/api/v1/ping",
            json={"garbage": "value"},
        )
        body = response.json()

        # Keys from ads-envelope.json canonical reference:
        # top-level keys are "error" + "meta"; error carries (code, details,
        # field, message, retry_after_seconds, retryable, suggestions); meta
        # carries (pagination, request_id, timestamp).
        assert set(body.keys()) == {"error", "meta"}
        assert set(body["error"].keys()) == {
            "code",
            "details",
            "field",
            "message",
            "retry_after_seconds",
            "retryable",
            "suggestions",
        }
        assert set(body["meta"].keys()) == {"pagination", "request_id", "timestamp"}


# ---------------------------------------------------------------------------
# Deliverable 6: security header byte-identity
# ---------------------------------------------------------------------------


# Shared fleet header values — byte-for-byte identical to
# ads-headers.txt and scheduling-headers.txt captures.
_EXPECTED_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


class TestSecurityHeadersByteIdentity:
    """Security headers present on every non-docs path match the fleet reference."""

    def test_health_returns_all_five_fleet_security_headers(self, client: TestClient) -> None:
        """GET /health yields the 5-header fleet set (HSTS / XFO / XCTO /
        Referrer-Policy / Cache-Control) at the exact values installed by
        ads and scheduling.
        """
        response = client.get("/health")

        assert response.status_code == 200
        for name, expected_value in _EXPECTED_SECURITY_HEADERS.items():
            actual = response.headers.get(name)
            assert actual == expected_value, (
                f"Security header {name} drifted from fleet reference: "
                f"expected {expected_value!r}, got {actual!r}"
            )

    def test_error_response_also_carries_security_headers(self, client: TestClient) -> None:
        """422 validation error path also carries the fleet security headers —
        SecurityHeadersMiddleware must enrich error responses, not just 200s.
        """
        response = client.post(
            "/api/v1/ping",
            json={"garbage": "value"},
        )
        assert response.status_code == 422
        for name, expected_value in _EXPECTED_SECURITY_HEADERS.items():
            actual = response.headers.get(name)
            assert actual == expected_value

    def test_header_set_matches_fleet_reference_captures(self, client: TestClient) -> None:
        """Security-headers response subset for /health is byte-identical
        with the ads and scheduling PT-03 captures.  This is the cross-
        service drift gate enforced in Sprint-5.
        """
        response = client.get("/health")

        # Build the header-only reference line set (what curl -I emits,
        # minus HTTP/1.1 status line and connection headers the ASGI
        # stack doesn't surface consistently).  Starlette TestClient
        # lower-cases response header names; normalize by canonical-case
        # lookup to align with the curl -I capture format.
        actual_header_lines = sorted(
            f"{name}: {response.headers[name]}"
            for name in _EXPECTED_SECURITY_HEADERS
            if name in response.headers
        )
        expected_header_lines = sorted(
            f"{name}: {value}" for name, value in _EXPECTED_SECURITY_HEADERS.items()
        )
        assert actual_header_lines == expected_header_lines


# ---------------------------------------------------------------------------
# Deliverable 6 bonus: cross-capture byte-identity assertion
#
# Directly compares this test's generated header set to the on-disk
# ads and scheduling reference captures.  Sprint-5 will ship the
# cross-service ``diff`` gate; this test prefigures it inside the asana
# suite so drift is caught at PR time.
# ---------------------------------------------------------------------------


class TestHeaderByteIdentityVsFleetCaptures:
    """Diff this suite's header output against the ads + scheduling captures."""

    _SHARED_HEADER_NAMES = (
        "Strict-Transport-Security",
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Referrer-Policy",
        "Cache-Control",
    )

    @staticmethod
    def _parse_header_capture(path: str) -> dict[str, str]:
        """Parse a curl-style header capture into a dict (excluding the
        HTTP status line).
        """
        from pathlib import Path

        text = Path(path).read_text(encoding="utf-8")
        out: dict[str, str] = {}
        for line in text.splitlines():
            if ":" not in line or line.startswith("HTTP/"):
                continue
            name, value = line.split(":", 1)
            out[name.strip()] = value.strip()
        return out

    @pytest.mark.parametrize(
        "fleet_reference_path",
        [
            "/Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/ads-headers.txt",
            "/Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/scheduling-headers.txt",
        ],
        ids=["ads", "scheduling"],
    )
    def test_shared_headers_match_fleet_capture(
        self, client: TestClient, fleet_reference_path: str
    ) -> None:
        """Asana's security header emissions for the 5 shared fleet headers
        are byte-identical to both ads and scheduling references.  Sprint-5
        enforces ``diff ads-headers.txt asana-headers.txt`` exit 0.
        """
        from pathlib import Path

        if not Path(fleet_reference_path).exists():
            pytest.skip(f"Fleet reference capture missing: {fleet_reference_path}")

        reference = self._parse_header_capture(fleet_reference_path)
        response = client.get("/health")

        for name in self._SHARED_HEADER_NAMES:
            expected = reference.get(name)
            actual = response.headers.get(name)
            assert expected is not None, f"Fleet reference missing {name}"
            assert actual == expected, (
                f"Drift vs {fleet_reference_path}: {name} expected {expected!r}, got {actual!r}"
            )


# ---------------------------------------------------------------------------
# Deliverable 6: webhook signature-invalid canonical envelope
# ---------------------------------------------------------------------------


class TestWebhookSignatureInvalidCanonicalEnvelope:
    """Webhook handler invalid-signature path emits canonical envelope.

    Specifically asserts that the webhook endpoint uses the canonical
    ``ASANA-AUTH-002`` wire code (``asana.webhook.signature_invalid``)
    rather than a bare ``401`` or plain ``HTTPException``.  This is the
    consumer-facing contract for Asana's Rules-action retry harness.
    """

    @pytest.fixture
    def webhook_app(self) -> FastAPI:
        """FastAPI app wired exactly as production wires the webhook
        subsystem (router + fleet exception handler + security headers).
        """
        import os
        from unittest.mock import patch

        from autom8y_api_schemas.middleware import SecurityHeadersMiddleware
        from autom8y_api_schemas.validation import register_validation_handler

        from autom8_asana.api.routes.webhooks import router
        from autom8_asana.settings import reset_settings

        with patch.dict(os.environ, {"WEBHOOK_INBOUND_TOKEN": "expected-test-token"}):
            reset_settings()

            app = FastAPI()
            app.include_router(router)
            register_validation_handler(app, service_code_prefix="ASANA")
            app.add_middleware(SecurityHeadersMiddleware)
            app.exception_handler(FleetError)(fleet_error_handler)
            yield app
            reset_settings()

    def test_invalid_signature_returns_canonical_asana_auth_002(self, webhook_app: FastAPI) -> None:
        """POST to webhook inbound with wrong ?token= returns canonical
        envelope with ``ASANA-AUTH-002`` wire code.
        """
        client = TestClient(webhook_app)
        response = client.post(
            "/api/v1/webhooks/inbound?token=wrong-token",
            json={"gid": "12345"},
        )

        assert response.status_code == 401
        body = response.json()
        assert body["error"]["code"] == "ASANA-AUTH-002"
        assert body["error"]["retryable"] is False
        assert body["meta"]["request_id"]

        # Security headers must be present on the auth-failure response too.
        assert response.headers.get("Strict-Transport-Security") == (
            "max-age=31536000; includeSubDomains"
        )
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_missing_signature_returns_canonical_asana_auth_002(self, webhook_app: FastAPI) -> None:
        """POST without ?token= also returns ``ASANA-AUTH-002``.  Missing
        and wrong are collapsed to the same code by design (see class
        docstring in webhooks.py).
        """
        client = TestClient(webhook_app)
        response = client.post(
            "/api/v1/webhooks/inbound",
            json={"gid": "12345"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "ASANA-AUTH-002"

    def test_not_a_generic_http_401_envelope(self, webhook_app: FastAPI) -> None:
        """Regression guard: the response MUST NOT be FastAPI's default
        ``{"detail": "Not authenticated"}`` or ``{"detail": {...}}`` — it
        must be the canonical ``{"error": {...}, "meta": {...}}`` envelope.
        """
        client = TestClient(webhook_app)
        response = client.post(
            "/api/v1/webhooks/inbound?token=wrong",
            json={"gid": "12345"},
        )

        body = response.json()
        # The canonical envelope does NOT carry a top-level "detail" key.
        assert "detail" not in body
        assert "error" in body
        assert "meta" in body
        # Error code is the canonical wire code, not a legacy string.
        assert body["error"]["code"] == "ASANA-AUTH-002"
        # The message is stable and not "Not authenticated".
        assert body["error"]["message"] != "Not authenticated"


# ---------------------------------------------------------------------------
# Smoke assertion: the fleet FleetError catch-all is wired
# ---------------------------------------------------------------------------


class TestFleetErrorCatchAll:
    """Any FleetError subclass raised from a route surfaces as canonical
    envelope via ``fleet_error_handler``.
    """

    def test_arbitrary_asana_error_surfaces_canonical_envelope(
        self, asana_test_app: FastAPI
    ) -> None:
        """A route that raises ``AsanaNotFoundError`` directly routes through
        ``fleet_error_handler`` and emits ``ASANA-NF-001`` in the canonical
        envelope.
        """
        from autom8y_api_schemas.errors import AsanaNotFoundError

        @asana_test_app.get("/_raise_not_found")
        def _raise() -> None:
            raise AsanaNotFoundError(message="Task not found")

        client = TestClient(asana_test_app)
        response = client.get("/_raise_not_found")

        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "ASANA-NF-001"
        assert body["error"]["message"] == "Task not found"
        assert body["error"]["retryable"] is False
        assert body["meta"]["request_id"]
