"""Route integration tests for PATCH /api/v1/entity/{entity_type}/{gid}.

Per TDD-ENTITY-WRITE-API Section 16.4:
    Validates the full HTTP layer including auth, entity type validation,
    error mapping, and response structure using FastAPI TestClient.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.resolution.write_registry import (
    CORE_FIELD_NAMES,
    WritableEntityInfo,
)
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

PROJECT_GID = "1143843662099250"
JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

MOCK_CUSTOM_FIELDS = [
    {
        "gid": "cf_111",
        "name": "Weekly Ad Spend",
        "resource_subtype": "number",
        "text_value": None,
        "number_value": 100,
        "enum_value": None,
        "multi_enum_values": [],
        "enum_options": [],
    },
    {
        "gid": "cf_222",
        "name": "Status",
        "resource_subtype": "enum",
        "text_value": None,
        "number_value": None,
        "enum_value": {"gid": "opt_active", "name": "Active"},
        "multi_enum_values": [],
        "enum_options": [
            {"gid": "opt_active", "name": "Active", "enabled": True},
            {"gid": "opt_paused", "name": "Paused", "enabled": True},
        ],
    },
    {
        "gid": "cf_333",
        "name": "Asset ID",
        "resource_subtype": "text",
        "text_value": "asset-100",
        "number_value": None,
        "enum_value": None,
        "multi_enum_values": [],
        "enum_options": [],
    },
]

MOCK_TASK_DATA: dict = {
    "gid": "9999999999",
    "name": "Test Offer",
    "assignee": None,
    "due_on": None,
    "completed": False,
    "notes": "",
    "custom_fields": MOCK_CUSTOM_FIELDS,
    "memberships": [
        {"project": {"gid": PROJECT_GID}},
    ],
}

DESCRIPTOR_INDEX = {
    "weekly_ad_spend": "Weekly Ad Spend",
    "status": "Status",
    "asset_id": "Asset ID",
}

WRITE_INFO = WritableEntityInfo(
    entity_type="offer",
    model_class=type("FakeOffer", (), {}),
    project_gid=PROJECT_GID,
    descriptor_index=DESCRIPTOR_INDEX,
    core_fields=CORE_FIELD_NAMES,
)


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


def _make_mock_write_registry() -> MagicMock:
    """Create a mock EntityWriteRegistry."""
    registry = MagicMock()
    registry.get.return_value = WRITE_INFO
    registry.is_writable.side_effect = lambda t: t == "offer"
    registry.writable_types.return_value = ["offer"]
    return registry


def _make_async_client_mock(mock_client_class: MagicMock) -> MagicMock:
    """Configure mock AsanaClient as an async context manager."""
    mock_client = MagicMock()
    mock_tasks = MagicMock()
    mock_tasks.get_async = AsyncMock(return_value=MOCK_TASK_DATA)
    mock_tasks.update_async = AsyncMock(return_value=MOCK_TASK_DATA)
    mock_client.tasks = mock_tasks
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client
    return mock_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before and after each test for isolation."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def mock_write_registry():
    return _make_mock_write_registry()


@pytest.fixture()
def app(mock_write_registry):
    """Create a test application with mocked discovery and write registry."""
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="offer",
                project_gid=PROJECT_GID,
                project_name="Business Offers",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry

        # Patch EntityWriteRegistry at its source module so the lazy import
        # in lifespan picks up the mock.
        with (
            patch(
                "autom8_asana.resolution.write_registry.EntityWriteRegistry",
                return_value=mock_write_registry,
            ),
            patch(
                "autom8_asana.core.entity_registry.get_registry",
                return_value=MagicMock(),
            ),
        ):
            yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    """Synchronous test client with lifespan events handled."""
    with TestClient(app) as tc:
        yield tc


def _patches(
    task_data: dict | None = None,
    get_side_effect: Exception | None = None,
    update_side_effect: Exception | None = None,
):
    """Stack of patches for auth, bot PAT, and AsanaClient."""
    # Patch JWT validation in both internal.py (for require_service_claims)
    # and jwt_validator module (for AuthContextDep's lazy import in get_auth_context).
    jwt_patch = patch(
        "autom8_asana.api.routes.internal.validate_service_token",
        _mock_jwt_validation(),
    )
    jwt_patch_dep = patch(
        "autom8_asana.auth.jwt_validator.validate_service_token",
        _mock_jwt_validation(),
    )
    # Patch get_bot_pat at the dependencies module level (where get_auth_context uses it).
    pat_patch = patch(
        "autom8_asana.api.dependencies.get_bot_pat",
        return_value="test_bot_pat",
    )
    client_patch = patch("autom8_asana.AsanaClient")
    return (
        jwt_patch,
        jwt_patch_dep,
        pat_patch,
        client_patch,
        task_data,
        get_side_effect,
        update_side_effect,
    )


def _apply_patches(
    jwt_p,
    jwt_dep_p,
    pat_p,
    client_p,
    task_data=None,
    get_side_effect=None,
    update_side_effect=None,
):
    """Enter patches and configure the mock client."""
    jwt_p.start()
    jwt_dep_p.start()
    pat_p.start()
    mock_client_class = client_p.start()

    mock_client = MagicMock()
    mock_tasks = MagicMock()

    if get_side_effect is not None:
        mock_tasks.get_async = AsyncMock(side_effect=get_side_effect)
    else:
        mock_tasks.get_async = AsyncMock(return_value=task_data or MOCK_TASK_DATA)

    if update_side_effect is not None:
        mock_tasks.update_async = AsyncMock(side_effect=update_side_effect)
    else:
        mock_tasks.update_async = AsyncMock(return_value=task_data or MOCK_TASK_DATA)

    mock_client.tasks = mock_tasks
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client

    return mock_client


def _stop_patches(jwt_p, jwt_dep_p, pat_p, client_p, *_):
    """Stop all patches."""
    jwt_p.stop()
    jwt_dep_p.stop()
    pat_p.stop()
    client_p.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEntityWriteRoute:
    """Per TDD-ENTITY-WRITE-API Section 16.4."""

    def test_patch_success_200(self, client: TestClient) -> None:
        """Full happy path: PATCH -> 200 with field_results."""
        patches = _patches()
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={"fields": {"name": "Updated Name"}},
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 200
        data = resp.json()
        assert data["gid"] == "9999999999"
        assert data["entity_type"] == "offer"
        assert data["fields_written"] == 1
        assert data["fields_skipped"] == 0
        assert len(data["field_results"]) == 1
        assert data["field_results"][0]["name"] == "name"
        assert data["field_results"][0]["status"] == "written"

    def test_missing_auth_401(self, client: TestClient) -> None:
        """No Authorization header -> 401."""
        resp = client.patch(
            "/api/v1/entity/offer/9999999999",
            json={"fields": {"name": "Updated"}},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "MISSING_AUTH"

    def test_pat_token_rejected_401(self, client: TestClient) -> None:
        """PAT token -> 401 SERVICE_TOKEN_REQUIRED."""
        # A PAT token looks like a long numeric string (not a JWT)
        pat_header = {"Authorization": "Bearer 1/1234567890123456789"}

        with patch(
            "autom8_asana.api.routes.internal.detect_token_type",
        ) as mock_detect:
            from autom8_asana.auth.dual_mode import AuthMode

            mock_detect.return_value = AuthMode.PAT

            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={"fields": {"name": "Updated"}},
                headers=pat_header,
            )

        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "SERVICE_TOKEN_REQUIRED"

    def test_unknown_entity_type_404(self, client: TestClient) -> None:
        """Unknown type -> 404 with available types."""
        patches = _patches()
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/nonexistent/9999999999",
                json={"fields": {"name": "Updated"}},
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 404
        data = resp.json()["detail"]
        assert data["error"] == "UNKNOWN_ENTITY_TYPE"
        assert "available_types" in data
        assert "offer" in data["available_types"]

    def test_task_not_found_404(self, client: TestClient) -> None:
        """Invalid GID -> 404 TASK_NOT_FOUND."""
        from autom8_asana.exceptions import NotFoundError

        patches = _patches(get_side_effect=NotFoundError("Not found", status_code=404))
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/0000000000",
                json={"fields": {"name": "Test"}},
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "TASK_NOT_FOUND"

    def test_entity_type_mismatch_404(self, client: TestClient) -> None:
        """Wrong project -> 404 ENTITY_TYPE_MISMATCH."""
        wrong_data = {
            **MOCK_TASK_DATA,
            "memberships": [
                {"project": {"gid": "WRONG_PROJECT_GID"}},
            ],
        }
        patches = _patches(task_data=wrong_data)
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={"fields": {"name": "Test"}},
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "ENTITY_TYPE_MISMATCH"

    def test_empty_fields_422(self, client: TestClient) -> None:
        """Empty fields -> 422."""
        patches = _patches()
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={"fields": {}},
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 422

    def test_no_valid_fields_422(self, client: TestClient) -> None:
        """All fields invalid -> 422 NO_VALID_FIELDS."""
        patches = _patches()
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={"fields": {"bogus_1": "x", "bogus_2": "y"}},
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "NO_VALID_FIELDS"

    def test_partial_success_200(self, client: TestClient) -> None:
        """Mix of valid/invalid -> 200 with skipped results."""
        patches = _patches()
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={
                    "fields": {
                        "name": "Updated Name",
                        "nonexistent_field": "value",
                    }
                },
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1
        assert data["fields_skipped"] == 1

        results_by_name = {r["name"]: r for r in data["field_results"]}
        assert results_by_name["name"]["status"] == "written"
        assert results_by_name["nonexistent_field"]["status"] == "skipped"

    def test_list_mode_append(self, client: TestClient) -> None:
        """list_mode='append' -> append behavior for text fields."""
        patches = _patches()
        mock_client = _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={
                    "fields": {"asset_id": "asset-200"},
                    "list_mode": "append",
                },
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1

        # Verify the update call included the appended text value
        call_kwargs = mock_client.tasks.update_async.call_args.kwargs
        custom_fields = call_kwargs.get("custom_fields", {})
        # The value should be "asset-100,asset-200" (appended to existing)
        assert custom_fields.get("cf_333") == "asset-100,asset-200"

    def test_unknown_fields_422(self, client: TestClient) -> None:
        """Unknown top-level fields (e.g. list_remove) -> 422."""
        patches = _patches()
        _apply_patches(*patches)

        try:
            resp = client.patch(
                "/api/v1/entity/offer/9999999999",
                json={
                    "fields": {"name": "Test"},
                    "list_remove": ["Q2"],
                },
                headers=AUTH_HEADER,
            )
        finally:
            _stop_patches(*patches)

        assert resp.status_code == 422
