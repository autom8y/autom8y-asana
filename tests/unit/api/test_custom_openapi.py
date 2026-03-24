"""Tests for custom_openapi() spec enrichment (Sprint 1).

Validates that the custom OpenAPI post-processor correctly:
- Injects BearerAuth and ServiceJWT security schemes
- Annotates per-operation security based on tag classification
- Strips leaked authorization header parameters
- Seeds tag descriptions for visible routers
- Caches the generated spec
- Produces a valid OpenAPI 3.1 document
- Does not break Swagger UI rendering (debug mode)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.auth.dual_mode import AuthMode


@pytest.fixture(scope="module")
def debug_app():
    """Create a test app with debug=True for /docs access.

    Module-scoped to avoid per-test ASGI lifespan overhead.
    """
    with (
        patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ) as mock_discover,
        patch(
            "autom8_asana.api.main.get_settings",
        ) as mock_settings,
    ):
        settings = mock_settings.return_value
        settings.debug = True
        settings.cors_origins_list = []
        settings.rate_limit_rpm = 100
        settings.log_level = "INFO"

        async def setup_registry(app):
            from autom8_asana.services.resolver import (
                EntityProjectRegistry,
            )

            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="offer",
                project_gid="1143843662099250",
                project_name="Business Offers",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        test_app = create_app()

        async def _mock_auth() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service="autom8_data",
            )

        test_app.dependency_overrides[get_auth_context] = _mock_auth
        yield test_app


@pytest.fixture(scope="module")
def spec(debug_app):
    """Return the enriched OpenAPI spec dict."""
    return debug_app.openapi()


@pytest.fixture(scope="module")
def debug_client(debug_app):
    """Module-scoped TestClient with ASGI lifespan entered."""
    with TestClient(debug_app) as tc:
        yield tc


# --- Test 1: Security schemes present ---


def test_security_schemes_present(spec):
    """BearerAuth and ServiceJWT exist with correct structure."""
    schemes = spec["components"]["securitySchemes"]

    assert "BearerAuth" in schemes
    bearer = schemes["BearerAuth"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"
    assert "description" in bearer

    assert "ServiceJWT" in schemes
    jwt = schemes["ServiceJWT"]
    assert jwt["type"] == "http"
    assert jwt["scheme"] == "bearer"
    assert jwt["bearerFormat"] == "JWT"
    assert "description" in jwt


# --- Test 2: Health endpoints have no security ---


def test_health_endpoints_no_security(spec):
    """Health operations have security: [] (explicitly unauthenticated)."""
    health_paths = ["/health", "/ready", "/health/deps"]
    for path in health_paths:
        path_item = spec["paths"].get(path)
        assert path_item is not None, f"Missing path: {path}"
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "patch", "delete"):
                assert operation.get("security") == [], (
                    f"{method.upper()} {path} should have security: []"
                )


# --- Test 3: PAT endpoints have BearerAuth ---


def test_pat_endpoints_bearer_auth(spec):
    """Operations tagged with PAT tags have BearerAuth security."""
    pat_prefixes = ("/api/v1/tasks", "/api/v1/projects")
    found_any = False
    for path, path_item in spec["paths"].items():
        if any(path.startswith(pfx) for pfx in pat_prefixes):
            for method in (
                "get",
                "post",
                "put",
                "patch",
                "delete",
            ):
                operation = path_item.get(method)
                if operation is None:
                    continue
                found_any = True
                assert operation.get("security") == [{"BearerAuth": []}], (
                    f"{method.upper()} {path} should have BearerAuth security"
                )
    assert found_any, "No PAT-tagged operations found in spec"


# --- Test 4: Authorization param stripped ---


def test_authorization_param_stripped(spec):
    """No operation has an authorization header parameter."""
    for path, path_item in spec["paths"].items():
        for method in (
            "get",
            "post",
            "put",
            "patch",
            "delete",
        ):
            operation = path_item.get(method)
            if operation is None:
                continue
            for param in operation.get("parameters", []):
                assert not (
                    param.get("name") == "authorization" and param.get("in") == "header"
                ), f"{method.upper()} {path} still has authorization header parameter"


# --- Test 5: Tag descriptions present ---


def test_tag_descriptions_present(spec):
    """spec['tags'] contains entries for all visible router tags."""
    expected_tags = {
        "health",
        "tasks",
        "projects",
        "sections",
        "users",
        "workspaces",
        "dataframes",
        "webhooks",
        "offers",
        "workflows",
    }
    tag_entries = {t["name"]: t for t in spec["tags"]}
    for tag_name in expected_tags:
        assert tag_name in tag_entries, f"Missing tag description for '{tag_name}'"
        assert "description" in tag_entries[tag_name]
        assert len(tag_entries[tag_name]["description"]) > 0


# --- Test 6: Schema cached ---


def test_openapi_schema_cached(debug_app):
    """Calling app.openapi() twice returns the same object (identity)."""
    first = debug_app.openapi()
    second = debug_app.openapi()
    assert first is second


# --- Test 7: OpenAPI version 3.1 ---


def test_openapi_version_3_1(spec):
    """spec['openapi'] starts with '3.1'."""
    assert spec["openapi"].startswith("3.1"), (
        f"Expected OpenAPI 3.1.x, got {spec['openapi']}"
    )


# --- Test 8: /docs endpoint returns 200 ---


def test_docs_endpoint_returns_200(debug_client):
    """GET /docs returns 200 in debug mode (Swagger UI renders)."""
    response = debug_client.get("/docs")
    assert response.status_code == 200
