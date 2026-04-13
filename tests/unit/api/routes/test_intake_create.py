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


def _make_collect_mock(return_value):
    """Create a mock object whose .collect() returns an AsyncMock with given value.

    Matches the PageIterator pattern: service calls method(...).collect().
    """
    collector = MagicMock()
    collector.collect = AsyncMock(return_value=return_value)
    return collector


def _make_mock_asana_client(
    *,
    raise_on_create: Exception | None = None,
    raise_on_get: Exception | None = None,
) -> MagicMock:
    """Create mock AsanaClient for business creation tests.

    Mocks:
    - tasks.create_async -> dispatches by kwarg: projects= (business), parent= (subtask)
    - tasks.get_async -> returns task with custom_fields
    - tasks.update_async -> no-op success
    - tasks.subtasks_async -> returns PageIterator-like with .collect() (empty)
    - users.list_for_workspace_async -> returns PageIterator-like with .collect()
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    if raise_on_create:
        mock_client.tasks.create_async = AsyncMock(side_effect=raise_on_create)
    else:
        # Unified create_async mock that distinguishes by keyword args:
        # - projects= kwarg -> Phase 1 business task creation
        # - parent= kwarg -> Phase 2-5 subtask creation (holders, unit, contact, process)
        subtask_call_count = {"n": 0}

        async def create_async_side_effect(*, name, **kwargs):
            if "projects" in kwargs and kwargs["projects"]:
                # Phase 1: Business task creation (has projects kwarg)
                return {"gid": BUSINESS_GID}
            elif "parent" in kwargs and kwargs["parent"]:
                # Phase 2-5: Subtask creation (has parent kwarg)
                subtask_call_count["n"] += 1
                n = subtask_call_count["n"]
                # First 7 calls are holders (Phase 2)
                if n <= 7:
                    return {"gid": HOLDER_GIDS.get(name, f"holder_{n:03d}")}
                # 8th call is unit (Phase 3)
                if n == 8:
                    return {"gid": UNIT_GID}
                # 9th call is contact (Phase 4)
                if n == 9:
                    return {"gid": CONTACT_GID}
                # 10th call is process (Phase 5)
                return {"gid": PROCESS_GID}
            # Fallback
            return {"gid": "unknown_gid"}

        mock_client.tasks.create_async = AsyncMock(side_effect=create_async_side_effect)

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

    # subtasks_async returns a PageIterator-like object with .collect() method
    mock_client.tasks.subtasks_async = MagicMock(
        return_value=_make_collect_mock([]),
    )

    # users.list_for_workspace_async returns a PageIterator-like with .collect()
    mock_client.users.list_for_workspace_async = MagicMock(
        return_value=_make_collect_mock(
            [
                {"gid": "user_alice", "name": "Alice Johnson"},
                {"gid": "user_bob", "name": "Bob Williams"},
            ]
        ),
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
def app(monkeypatch):
    """Create a test application with mocked lifespan discovery."""
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
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        data = body["data"]
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
        assert resp.json()["data"]["process_gid"] is not None

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
        assert resp.json()["data"]["process_gid"] is None

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
        assert "data" in resp.json()

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
        assert data["error"]["code"] == "INVALID_PHONE_FORMAT"

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

        # Verify the unit was created with default name via create_async
        create_calls = mock_asana.tasks.create_async.call_args_list
        # Find the unit creation call (should contain the default unit name)
        unit_created = False
        expected_name = "Test Dental Practice -- Dental"
        for call in create_calls:
            call_name = call.kwargs.get("name", "")
            if call_name == expected_name:
                unit_created = True
                break
        assert unit_created, f"Unit not created with expected default name: {expected_name}"

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
        holders = resp.json()["data"]["holders"]
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
        assert data["error"]["code"] == "UNKNOWN_PROCESS_TYPE"


# ---------------------------------------------------------------------------
# Unit-level tests for _write_vertical_custom_field (Phase 3)
# ---------------------------------------------------------------------------


class TestPhase3VerticalCustomField:
    """Tests for the Vertical enum custom field write in Phase 3."""

    @pytest.mark.asyncio()
    async def test_phase3_writes_vertical_custom_field(self) -> None:
        """Verifies update_async is called with correct custom_fields payload.

        When the Vertical enum custom field exists and the vertical parameter
        matches an enum option, the service writes the enum option GID.
        """
        mock_client = MagicMock()
        mock_client.tasks.create_async = AsyncMock(
            return_value={"gid": UNIT_GID},
        )
        # get_async returns task with Vertical enum custom field
        mock_client.tasks.get_async = AsyncMock(
            return_value={
                "gid": UNIT_GID,
                "custom_fields": [
                    {
                        "gid": "cf_vertical",
                        "name": "Vertical",
                        "enum_options": [
                            {"gid": "enum_dental", "name": "Dental"},
                            {"gid": "enum_medical", "name": "Medical"},
                            {"gid": "enum_legal", "name": "Legal"},
                        ],
                    },
                ],
            },
        )
        mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

        from autom8_asana.services.intake_create_service import IntakeCreateService

        service = IntakeCreateService(mock_client)
        result_gid = await service._phase3_create_unit(
            unit_holder_gid="holder_unit",
            unit_name="Test Practice -- Dental",
            vertical="dental",
        )

        assert result_gid == UNIT_GID

        # Verify get_async was called to fetch custom fields
        mock_client.tasks.get_async.assert_called_once_with(
            UNIT_GID,
            opt_fields=[
                "custom_fields.gid",
                "custom_fields.name",
                "custom_fields.enum_options.gid",
                "custom_fields.enum_options.name",
            ],
        )

        # Verify update_async was called with correct enum custom field payload
        mock_client.tasks.update_async.assert_called_once_with(
            UNIT_GID,
            data={"custom_fields": {"cf_vertical": {"gid": "enum_dental"}}},
        )

    @pytest.mark.asyncio()
    async def test_phase3_vertical_cf_not_found_no_raise(self) -> None:
        """Verifies graceful degradation when Vertical custom field is absent.

        The service logs a warning but does not raise. The unit task is still
        created and its GID returned.
        """
        mock_client = MagicMock()
        mock_client.tasks.create_async = AsyncMock(
            return_value={"gid": UNIT_GID},
        )
        # get_async returns task WITHOUT a Vertical custom field
        mock_client.tasks.get_async = AsyncMock(
            return_value={
                "gid": UNIT_GID,
                "custom_fields": [
                    {"gid": "cf_other", "name": "Some Other Field"},
                ],
            },
        )
        mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

        from autom8_asana.services.intake_create_service import IntakeCreateService

        service = IntakeCreateService(mock_client)
        result_gid = await service._phase3_create_unit(
            unit_holder_gid="holder_unit",
            unit_name="Test Practice -- Dental",
            vertical="dental",
        )

        # Unit is still created successfully
        assert result_gid == UNIT_GID

        # update_async should NOT have been called (no field to write)
        mock_client.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio()
    async def test_phase3_vertical_enum_option_not_found_no_raise(self) -> None:
        """Verifies graceful degradation when enum option does not match.

        The Vertical custom field exists but the vertical parameter does not
        match any of its enum options. The service logs a warning and returns
        without writing.
        """
        mock_client = MagicMock()
        mock_client.tasks.create_async = AsyncMock(
            return_value={"gid": UNIT_GID},
        )
        # get_async returns Vertical field but with no matching enum option
        mock_client.tasks.get_async = AsyncMock(
            return_value={
                "gid": UNIT_GID,
                "custom_fields": [
                    {
                        "gid": "cf_vertical",
                        "name": "Vertical",
                        "enum_options": [
                            {"gid": "enum_medical", "name": "Medical"},
                            {"gid": "enum_legal", "name": "Legal"},
                        ],
                    },
                ],
            },
        )
        mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

        from autom8_asana.services.intake_create_service import IntakeCreateService

        service = IntakeCreateService(mock_client)
        result_gid = await service._phase3_create_unit(
            unit_holder_gid="holder_unit",
            unit_name="Test Practice -- Dental",
            vertical="dental",  # Not in enum_options
        )

        # Unit is still created successfully
        assert result_gid == UNIT_GID

        # update_async should NOT have been called (no matching enum option)
        mock_client.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio()
    async def test_phase3_vertical_case_insensitive_match(self) -> None:
        """Verifies case-insensitive matching of vertical to enum option."""
        mock_client = MagicMock()
        mock_client.tasks.create_async = AsyncMock(
            return_value={"gid": UNIT_GID},
        )
        mock_client.tasks.get_async = AsyncMock(
            return_value={
                "gid": UNIT_GID,
                "custom_fields": [
                    {
                        "gid": "cf_vertical",
                        "name": "VERTICAL",  # uppercase field name
                        "enum_options": [
                            {"gid": "enum_dental", "name": "Dental"},  # title case
                        ],
                    },
                ],
            },
        )
        mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

        from autom8_asana.services.intake_create_service import IntakeCreateService

        service = IntakeCreateService(mock_client)
        result_gid = await service._phase3_create_unit(
            unit_holder_gid="holder_unit",
            unit_name="Test Practice -- Dental",
            vertical="dental",  # lowercase vs "Dental" enum option
        )

        assert result_gid == UNIT_GID
        mock_client.tasks.update_async.assert_called_once_with(
            UNIT_GID,
            data={"custom_fields": {"cf_vertical": {"gid": "enum_dental"}}},
        )


# ---------------------------------------------------------------------------
# Service-layer tests for create_business_hierarchy orchestration
# ---------------------------------------------------------------------------


class TestCreateBusinessHierarchyOrchestration:
    """Tests for the 7-phase SaveSession orchestration.

    Route-level tests exercise the endpoint. These tests exercise the
    IntakeCreateService.create_business_hierarchy method directly to verify
    phase ordering, Phase 2 parallel gather semantics, and partial-failure
    behavior — aspects invisible through the route layer.
    """

    @staticmethod
    def _make_request(
        *,
        with_process: bool = False,
        with_social: bool = False,
        with_address: bool = False,
    ):
        from autom8_asana.api.routes.intake_create_models import (
            IntakeAddress,
            IntakeBusinessCreateRequest,
            IntakeContact,
            IntakeProcessConfig,
            IntakeSocialProfile,
        )

        kwargs: dict = {
            "name": "Test Dental Practice",
            "office_phone": "+15551234567",
            "vertical": "dental",
            "contact": IntakeContact(name="Jane Smith"),
        }
        if with_process:
            kwargs["process"] = IntakeProcessConfig(process_type="sales")
        if with_social:
            kwargs["social_profiles"] = [
                IntakeSocialProfile(
                    platform="facebook",
                    url="https://facebook.com/testdental",
                )
            ]
        if with_address:
            kwargs["address"] = IntakeAddress(city="Springfield", postal_code="62701")
        return IntakeBusinessCreateRequest(**kwargs)

    @pytest.mark.asyncio()
    async def test_phases_execute_in_strict_dependency_order(self) -> None:
        """Phase 1 completes before Phase 2; Phase 2 before Phase 3.

        Verifies the orchestrator enforces dependency order: unit_gid
        (Phase 3) depends on unit_holder (Phase 2), which depends on
        business_gid (Phase 1).
        """
        from autom8_asana.services.intake_create_service import IntakeCreateService

        call_order: list[str] = []

        async def create_side_effect(**kwargs):
            if "projects" in kwargs:
                call_order.append("phase1_business")
                return {"gid": BUSINESS_GID}
            parent = kwargs.get("parent")
            name = kwargs.get("name", "")
            if parent == BUSINESS_GID:
                call_order.append(f"phase2_holder:{name}")
                return {"gid": HOLDER_GIDS[name]}
            if parent == HOLDER_GIDS["unit_holder"]:
                call_order.append("phase3_unit")
                return {"gid": UNIT_GID}
            if parent == HOLDER_GIDS["contact_holder"]:
                call_order.append("phase4_contact")
                return {"gid": CONTACT_GID}
            return {"gid": "unknown"}

        mock_client = MagicMock()
        mock_client.tasks.create_async = AsyncMock(side_effect=create_side_effect)
        mock_client.tasks.get_async = AsyncMock(return_value={"gid": UNIT_GID, "custom_fields": []})
        mock_client.tasks.update_async = AsyncMock()

        with patch(
            "autom8_asana.services.intake_create_service.resolve_business_project_gid",
            return_value=BUSINESS_PROJECT_GID,
        ):
            service = IntakeCreateService(mock_client)
            response = await service.create_business_hierarchy(self._make_request())

        # Phase 1 must come first
        assert call_order[0] == "phase1_business"
        # All 7 holders must complete before Phase 3 (unit) or Phase 4 (contact)
        phase2_calls = [c for c in call_order if c.startswith("phase2_holder:")]
        assert len(phase2_calls) == 7
        phase3_idx = call_order.index("phase3_unit")
        phase4_idx = call_order.index("phase4_contact")
        for phase2_call in phase2_calls:
            assert call_order.index(phase2_call) < phase3_idx
            assert call_order.index(phase2_call) < phase4_idx
        # Phase 3 (unit) must come before Phase 4 (contact) — sequential
        assert phase3_idx < phase4_idx

        assert response.business_gid == BUSINESS_GID
        assert response.unit_gid == UNIT_GID
        assert response.contact_gid == CONTACT_GID
        assert len(response.holders) == 7

    @pytest.mark.asyncio()
    async def test_phase2_holder_failure_propagates_and_aborts_hierarchy(
        self,
    ) -> None:
        """One failed holder in Phase 2 aborts create_business_hierarchy.

        Phase 2 uses asyncio.gather() without return_exceptions=True, so the
        first failing holder propagates, cancels siblings, and the hierarchy
        creation raises — preventing partial state commitment downstream.
        """
        from autom8_asana.services.intake_create_service import IntakeCreateService

        phase3_called = False

        async def create_side_effect(**kwargs):
            nonlocal phase3_called
            if "projects" in kwargs:
                return {"gid": BUSINESS_GID}
            parent = kwargs.get("parent")
            name = kwargs.get("name", "")
            if parent == BUSINESS_GID:
                if name == "dna_holder":
                    raise RuntimeError("Asana API 500 on dna_holder creation")
                return {"gid": HOLDER_GIDS.get(name, "unknown")}
            # Phase 3+ should never be reached if Phase 2 fails
            phase3_called = True
            return {"gid": "should_not_exist"}

        mock_client = MagicMock()
        mock_client.tasks.create_async = AsyncMock(side_effect=create_side_effect)

        with patch(
            "autom8_asana.services.intake_create_service.resolve_business_project_gid",
            return_value=BUSINESS_PROJECT_GID,
        ):
            service = IntakeCreateService(mock_client)
            with pytest.raises(RuntimeError, match="dna_holder"):
                await service.create_business_hierarchy(self._make_request())

        assert phase3_called is False, "Phase 3 must not execute when Phase 2 partially fails"

    @pytest.mark.asyncio()
    async def test_phase5_skipped_when_process_not_requested(self) -> None:
        """Phase 5 (process routing) is skipped when request.process is None."""
        from autom8_asana.services.intake_create_service import IntakeCreateService

        route_process_called = False

        async def create_side_effect(**kwargs):
            if "projects" in kwargs:
                return {"gid": BUSINESS_GID}
            parent = kwargs.get("parent")
            name = kwargs.get("name", "")
            if parent == BUSINESS_GID:
                return {"gid": HOLDER_GIDS[name]}
            if parent == HOLDER_GIDS["unit_holder"]:
                return {"gid": UNIT_GID}
            if parent == HOLDER_GIDS["contact_holder"]:
                return {"gid": CONTACT_GID}
            return {"gid": "unknown"}

        mock_client = MagicMock()
        mock_client.tasks.create_async = AsyncMock(side_effect=create_side_effect)
        mock_client.tasks.get_async = AsyncMock(return_value={"gid": UNIT_GID, "custom_fields": []})
        mock_client.tasks.update_async = AsyncMock()

        service = IntakeCreateService(mock_client)

        async def tracking_route_process(*args, **kwargs):
            nonlocal route_process_called
            route_process_called = True
            return MagicMock(process_gid=PROCESS_GID)

        service.route_process = tracking_route_process  # type: ignore[method-assign]

        with patch(
            "autom8_asana.services.intake_create_service.resolve_business_project_gid",
            return_value=BUSINESS_PROJECT_GID,
        ):
            response = await service.create_business_hierarchy(
                self._make_request(with_process=False)
            )

        assert route_process_called is False
        assert response.process_gid is None
