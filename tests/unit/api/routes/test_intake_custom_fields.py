"""Tests for intake custom field write endpoint.

POST /v1/tasks/{task_gid}/custom-fields

Validates field resolution, partial failure handling, and auth requirements.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.errors import NotFoundError, RateLimitError
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

TASK_GID = "9999999999999999"

MOCK_CUSTOM_FIELDS = [
    {
        "gid": "cf_company_id",
        "name": "company_id",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_utm_source",
        "name": "UTM Source",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_utm_medium",
        "name": "UTM Medium",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_status",
        "name": "Status",
        "resource_subtype": "enum",
        "text_value": None,
        "enum_value": None,
        "enum_options": [
            {"gid": "opt_active", "name": "Active", "enabled": True},
            {"gid": "opt_paused", "name": "Paused", "enabled": True},
        ],
    },
    {
        "gid": "cf_ad_spend",
        "name": "Weekly Ad Spend",
        "resource_subtype": "number",
        "number_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_facebook",
        "name": "Facebook URL",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
]

MOCK_TASK_DATA = {
    "gid": TASK_GID,
    "custom_fields": MOCK_CUSTOM_FIELDS,
    "memberships": [{"project": {"gid": "proj_123"}}],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    """Create a mock JWT validation returning valid ServiceClaims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _make_mock_asana_client(
    *,
    task_data: dict | None = None,
    raise_on_get: Exception | None = None,
    raise_on_update: Exception | None = None,
) -> MagicMock:
    """Create mock AsanaClient for custom field tests."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    if raise_on_get:
        mock_client.tasks.get_async = AsyncMock(side_effect=raise_on_get)
    else:
        mock_client.tasks.get_async = AsyncMock(
            return_value=task_data or MOCK_TASK_DATA
        )

    if raise_on_update:
        mock_client.tasks.update_async = AsyncMock(side_effect=raise_on_update)
    else:
        mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

    return mock_client


def _custom_field_patches(mock_client: MagicMock | None = None):
    """Create context manager patches for JWT, bot PAT, and AsanaClient."""
    jwt_patch = patch(
        "autom8_asana.api.routes.internal.validate_service_token",
        _mock_jwt_validation(),
    )
    jwt_patch_canonical = patch(
        "autom8_asana.auth.jwt_validator.validate_service_token",
        _mock_jwt_validation(),
    )
    pat_patch = patch(
        "autom8_asana.auth.bot_pat.get_bot_pat",
        return_value="test_bot_pat",
    )
    pat_patch_deps = patch(
        "autom8_asana.api.dependencies.get_bot_pat",
        return_value="test_bot_pat",
    )

    mock_client_instance = mock_client or _make_mock_asana_client()

    client_patch = patch(
        "autom8_asana.api.routes.intake_custom_fields.AsanaClient",
        return_value=mock_client_instance,
    )

    # Patch SchemaRegistry to avoid startup dependency
    schema_patch = patch(
        "autom8_asana.services.intake_custom_field_service.IntakeCustomFieldService._enrich_from_schema_registry",
    )

    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        schema_patch,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before and after each test."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    """Create a test application with mocked lifespan."""
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
                entity_type="business",
                project_gid="1234567890123456",
                project_name="Business",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    """Synchronous test client with lifespan events."""
    with TestClient(app) as tc:
        yield tc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWriteCustomFieldsEndpoint:
    """POST /v1/tasks/{task_gid}/custom-fields"""

    def test_write_single_field(self, client: TestClient) -> None:
        """Single field written successfully."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"company_id": "guid-456"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_gid"] == TASK_GID
        assert data["fields_written"] == 1
        assert data["errors"] == []

    def test_write_multiple_fields(self, client: TestClient) -> None:
        """Multiple fields written in one call."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={
                    "fields": {
                        "company_id": "guid-789",
                        "UTM Source": "google",
                        "UTM Medium": "cpc",
                    }
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 3
        assert data["errors"] == []

    def test_company_id_writeback(self, client: TestClient) -> None:
        """company_id field write (primary use case)."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"company_id": "company-guid-abc"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_gid"] == TASK_GID
        assert data["fields_written"] == 1

        # Verify the Asana update was called with the right field GID
        mock_asana.tasks.update_async.assert_called_once()
        call_data = mock_asana.tasks.update_async.call_args
        custom_fields = call_data.kwargs["data"]["custom_fields"]
        assert "cf_company_id" in custom_fields
        assert custom_fields["cf_company_id"] == "company-guid-abc"

    def test_partial_failure(self, client: TestClient) -> None:
        """Some fields succeed, some fail (unresolvable). Returns errors list."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={
                    "fields": {
                        "company_id": "guid-000",
                        "nonexistent_field": "value",
                    }
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1
        assert "nonexistent_field" in data["errors"]

    def test_task_not_found_404(self, client: TestClient) -> None:
        """Invalid task_gid returns 404 TASK_NOT_FOUND."""
        mock_asana = _make_mock_asana_client(raise_on_get=NotFoundError("Not found"))
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/tasks/0000000000000000/custom-fields",
                json={"fields": {"company_id": "test"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "TASK_NOT_FOUND"

    def test_empty_fields_422(self, client: TestClient) -> None:
        """Empty fields dict returns 422 EMPTY_FIELDS."""
        patches = _custom_field_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "EMPTY_FIELDS"

    def test_requires_s2s_jwt(self, client: TestClient) -> None:
        """Missing auth header returns 401."""
        resp = client.post(
            f"/v1/tasks/{TASK_GID}/custom-fields",
            json={"fields": {"company_id": "test"}},
        )
        assert resp.status_code == 401

    def test_null_value_clears_field(self, client: TestClient) -> None:
        """None value clears the custom field."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"company_id": None}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1

        # Verify null was passed through to Asana
        mock_asana.tasks.update_async.assert_called_once()
        call_data = mock_asana.tasks.update_async.call_args
        custom_fields = call_data.kwargs["data"]["custom_fields"]
        assert custom_fields["cf_company_id"] is None

    def test_social_profile_field_write(self, client: TestClient) -> None:
        """Social profile URL written as custom field."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"Facebook URL": "https://facebook.com/testbiz"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1
        assert data["errors"] == []

    def test_all_fields_unresolvable(self, client: TestClient) -> None:
        """All fields fail resolution. Returns 200 with fields_written=0."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={
                    "fields": {
                        "nonexistent_a": "val1",
                        "nonexistent_b": "val2",
                    }
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 0
        assert len(data["errors"]) == 2
