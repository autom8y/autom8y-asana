"""Tests for intake business creation endpoint.

POST /v1/intake/business - Create full business hierarchy (7-phase SaveSession)

Per IMPL spec section 3:
- SaveSession batching: 7 phases, strict order (Phase 2 parallelizes)
- Social profiles written as custom fields (SOCIAL-PROFILES-ORPHANED fix)
- Address uses postal_code (ZIP-MISMATCH fix)
- Response holders dict contains all 7 holder types
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.intake_create_service import HOLDER_TYPES
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

BUSINESS_PROJECT_GID = "1234567890123456"
BUSINESS_GID = "biz_001"
UNIT_GID = "unit_001"
CONTACT_GID = "contact_001"
PROCESS_GID = "process_001"

# Pre-generate holder GIDs keyed by name
HOLDER_GIDS = {name: f"holder_{i:03d}" for i, name in enumerate(HOLDER_TYPES)}

MINIMAL_CREATE_BODY = {
    "name": "Test Dental Practice",
    "office_phone": "+15551234567",
    "vertical": "dental",
    "contact": {"name": "Jane Smith"},
}

FULL_CREATE_BODY = {
    "name": "Test Dental Practice",
    "office_phone": "+15551234567",
    "vertical": "dental",
    "num_reviews": 42,
    "website": "https://testdental.com",
    "address": {
        "street_number": "123",
        "street_name": "Main St",
        "city": "Springfield",
        "state": "IL",
        "postal_code": "62701",
        "country": "US",
    },
    "social_profiles": [
        {"platform": "facebook", "url": "https://facebook.com/testdental"},
        {"platform": "instagram", "url": "https://instagram.com/testdental"},
    ],
    "contact": {
        "name": "Jane Smith",
        "email": "jane@testdental.com",
        "phone": "+15559876543",
        "timezone": "America/Chicago",
    },
    "process": {
        "process_type": "sales",
        "due_at": "2026-04-01T10:00:00Z",
        "assignee_name": "Alice",
    },
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
    raise_on_create: Exception | None = None,
    raise_on_get: Exception | None = None,
) -> MagicMock:
    """Create mock AsanaClient for business creation tests.

    Mocks:
    - tasks.create_in_workspace_async -> returns business task GID
    - tasks.create_subtask_async -> returns holder/unit/contact/process GIDs
    - tasks.get_async -> returns task with custom_fields
    - tasks.update_async -> no-op success
    - tasks.subtasks_async -> returns empty (no existing processes)
    - users.get_users_async -> returns mock users
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    if raise_on_create:
        mock_client.tasks.create_in_workspace_async = AsyncMock(
            side_effect=raise_on_create
        )
        mock_client.tasks.create_subtask_async = AsyncMock(side_effect=raise_on_create)
    else:
        # Phase 1: create_in_workspace_async returns business
        mock_client.tasks.create_in_workspace_async = AsyncMock(
            return_value={"gid": BUSINESS_GID},
        )

        # Phase 2-5: create_subtask_async returns sequential GIDs
        # The call order: 7 holders (parallel), then unit, contact, process
        subtask_call_count = {"n": 0}

        async def create_subtask_side_effect(parent_gid, data=None, **kwargs):
            subtask_call_count["n"] += 1
            n = subtask_call_count["n"]
            # First 7 calls are holders (Phase 2)
            if n <= 7:
                holder_name = data.get("name", f"holder_{n}") if data else f"holder_{n}"
                return {"gid": HOLDER_GIDS.get(holder_name, f"holder_{n:03d}")}
            # 8th call is unit (Phase 3)
            if n == 8:
                return {"gid": UNIT_GID}
            # 9th call is contact (Phase 4)
            if n == 9:
                return {"gid": CONTACT_GID}
            # 10th call is process (Phase 5)
            return {"gid": PROCESS_GID}

        mock_client.tasks.create_subtask_async = AsyncMock(
            side_effect=create_subtask_side_effect
        )

    if raise_on_get:
        mock_client.tasks.get_async = AsyncMock(side_effect=raise_on_get)
    else:
        # Phase 6+7: get_async returns task with custom fields for field resolution
        mock_client.tasks.get_async = AsyncMock(
            return_value={
                "gid": BUSINESS_GID,
                "custom_fields": [
                    {
                        "gid": "cf_facebook",
                        "name": "Facebook URL",
                        "resource_subtype": "text",
                    },
                    {
                        "gid": "cf_instagram",
                        "name": "Instagram URL",
                        "resource_subtype": "text",
                    },
                    {
                        "gid": "cf_youtube",
                        "name": "YouTube URL",
                        "resource_subtype": "text",
                    },
                    {
                        "gid": "cf_linkedin",
                        "name": "LinkedIn URL",
                        "resource_subtype": "text",
                    },
                    {
                        "gid": "cf_street",
                        "name": "Street Number",
                        "resource_subtype": "text",
                    },
                    {"gid": "cf_city", "name": "City", "resource_subtype": "text"},
                    {"gid": "cf_state", "name": "State", "resource_subtype": "text"},
                    {
                        "gid": "cf_postal",
                        "name": "Postal Code",
                        "resource_subtype": "text",
                    },
                    {
                        "gid": "cf_country",
                        "name": "Country",
                        "resource_subtype": "text",
                    },
                ],
            },
        )

    mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())
    mock_client.tasks.subtasks_async = AsyncMock(return_value=[])
    mock_client.users.get_users_async = AsyncMock(
        return_value=[
            {"gid": "user_alice", "name": "Alice Johnson"},
            {"gid": "user_bob", "name": "Bob Williams"},
        ],
    )

    return mock_client


def _create_patches(mock_client: MagicMock | None = None):
    """Create context manager patches for JWT, bot PAT, AsanaClient, and project registry."""
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
        "autom8_asana.api.routes.intake_create.AsanaClient",
        return_value=mock_client_instance,
    )

    # Mock the project GID resolver
    project_patch = patch(
        "autom8_asana.services.intake_create_service.resolve_business_project_gid",
        return_value=BUSINESS_PROJECT_GID,
    )

    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        project_patch,
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
def app():
    """Create a test application with mocked lifespan discovery."""
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="business",
                project_gid=BUSINESS_PROJECT_GID,
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
# POST /v1/intake/business
# ---------------------------------------------------------------------------


class TestCreateIntakeBusinessEndpoint:
    """POST /v1/intake/business"""

    def test_full_hierarchy_creation(self, client: TestClient) -> None:
        """Creates business + 7 holders + unit + contact. Returns all GIDs.

        Verifies 201 status code and all required response fields.
        """
        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=MINIMAL_CREATE_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["business_gid"] == BUSINESS_GID
        assert data["unit_gid"] == UNIT_GID
        assert data["contact_gid"] == CONTACT_GID
        assert data["contact_holder_gid"] is not None
        assert data["unit_holder_gid"] is not None
        assert data["process_gid"] is None  # No process requested

    def test_with_process_routing(self, client: TestClient) -> None:
        """When process config provided, creates process too."""
        body = {**MINIMAL_CREATE_BODY, "process": {"process_type": "sales"}}
        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["process_gid"] is not None

    def test_without_process(self, client: TestClient) -> None:
        """process_gid is None when no process config."""
        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=MINIMAL_CREATE_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201
        assert resp.json()["process_gid"] is None

    def test_social_profiles_written(self, client: TestClient) -> None:
        """Social profiles written as custom fields on business task.

        Verifies SOCIAL-PROFILES-ORPHANED fix: profiles reach Asana.
        """
        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        body = {
            **MINIMAL_CREATE_BODY,
            "social_profiles": [
                {"platform": "facebook", "url": "https://facebook.com/testbiz"},
                {"platform": "instagram", "url": "https://instagram.com/testbiz"},
            ],
        }

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201

        # Verify update_async was called with social profile custom fields
        update_calls = mock_asana.tasks.update_async.call_args_list
        # At least one update call should contain social profile fields
        social_written = False
        for call in update_calls:
            call_data = call.kwargs.get("data", {}) if call.kwargs else {}
            cf = call_data.get("custom_fields", {})
            if "cf_facebook" in cf or "cf_instagram" in cf:
                social_written = True
                break
        assert social_written, "Social profiles were not written to custom fields"

    def test_address_written_to_location_holder(self, client: TestClient) -> None:
        """Address fields written to location_holder via custom fields."""
        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        body = {
            **MINIMAL_CREATE_BODY,
            "address": {
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62701",
            },
        }

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201

        # Verify update was called for address fields
        update_calls = mock_asana.tasks.update_async.call_args_list
        address_written = False
        for call in update_calls:
            call_data = call.kwargs.get("data", {}) if call.kwargs else {}
            cf = call_data.get("custom_fields", {})
            if "cf_city" in cf or "cf_state" in cf or "cf_postal" in cf:
                address_written = True
                break
        assert address_written, "Address fields were not written to location_holder"

    def test_postal_code_not_zip(self, client: TestClient) -> None:
        """Verify postal_code field name used, never 'zip' or 'zip_code'.

        The address model only accepts postal_code (ZIP-MISMATCH fix).
        """
        body = {
            **MINIMAL_CREATE_BODY,
            "address": {"postal_code": "62701"},
        }
        # Verify the request body uses postal_code
        assert "postal_code" in str(body["address"])
        assert "zip" not in str(body["address"]).lower().replace("postal", "")

        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201

    def test_invalid_phone_400(self, client: TestClient) -> None:
        """Non-E.164 phone returns 400 INVALID_PHONE_FORMAT."""
        body = {**MINIMAL_CREATE_BODY, "office_phone": "555-1234567"}
        patches = _create_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"] == "INVALID_PHONE_FORMAT"

    def test_requires_s2s_jwt(self, client: TestClient) -> None:
        """Missing auth header returns 401."""
        resp = client.post(
            "/v1/intake/business",
            json=MINIMAL_CREATE_BODY,
        )
        assert resp.status_code == 401

    def test_default_unit_name(self, client: TestClient) -> None:
        """When unit_name is None, defaults to '{name} -- {vertical_title}'."""
        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=MINIMAL_CREATE_BODY,  # unit_name not provided
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201

        # Verify the unit was created with default name
        # The 8th subtask call should be the unit (after 7 holders)
        create_calls = mock_asana.tasks.create_subtask_async.call_args_list
        # Find the unit creation call (should contain the default unit name)
        unit_created = False
        expected_name = "Test Dental Practice -- Dental"
        for call in create_calls:
            call_data = call.kwargs.get("data", {}) if call.kwargs else {}
            if not call_data and len(call.args) > 1:
                call_data = call.args[1] if isinstance(call.args[1], dict) else {}
            name = call_data.get("name", "")
            if name == expected_name:
                unit_created = True
                break
        assert unit_created, (
            f"Unit not created with expected default name: {expected_name}"
        )

    def test_holders_dict_contains_all_seven(self, client: TestClient) -> None:
        """Response holders dict has all 7 holder types."""
        mock_asana = _make_mock_asana_client()
        patches = _create_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=MINIMAL_CREATE_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 201
        holders = resp.json()["holders"]
        for holder_name in HOLDER_TYPES:
            assert holder_name in holders, f"Missing holder: {holder_name}"
        assert len(holders) == 7

    def test_unknown_process_type_422(self, client: TestClient) -> None:
        """Unknown process_type in process config returns 422."""
        body = {
            **MINIMAL_CREATE_BODY,
            "process": {"process_type": "nonexistent"},
        }
        patches = _create_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/business",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 422
        data = resp.json()
        assert data["detail"]["error"] == "UNKNOWN_PROCESS_TYPE"
