"""Tests for resolver routes (/v1/resolve/*).

Per TDD-entity-resolver Phase 1:
- POST /v1/resolve/unit requires service token (S2S)
- Batch size validation (max 1000)
- E.164 phone format validation
- Input order preserved in response
- Returns GID or error for each criterion

Test Matrix (per TDD Appendix B):
- TC-001: Valid phone/vertical returns GID
- TC-002: Unknown phone/vertical returns null with NOT_FOUND
- TC-003: Invalid E.164 returns 422
- TC-004: Missing vertical returns 422
- TC-005: Batch 1000 completes <1000ms
- TC-012: PAT token returns 401 SERVICE_TOKEN_REQUIRED
- TC-013: Empty criteria returns 200 with empty results
- TC-014: Invalid entity_type returns 404 UNKNOWN_ENTITY_TYPE
"""

from __future__ import annotations

import time
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.resolver import EntityProjectRegistry


@pytest.fixture
def app():
    """Create a test application instance with mocked discovery."""
    # Mock the discovery to avoid actual Asana API calls
    with patch(
        "autom8_asana.api.main._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:
        # Configure mock discovery to set up EntityProjectRegistry
        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid="1201081073731555",
                project_name="units",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create a synchronous test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """Reset singletons before and after each test."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


class TestResolveUnitEndpoint:
    """Test POST /v1/resolve/unit."""

    def test_valid_phone_vertical_returns_gid(self, client: TestClient) -> None:
        """TC-001: Valid phone/vertical returns GID."""
        import polars as pl

        jwt_token = "header.payload.signature"

        # Create mock DataFrame with matching data
        mock_df = pl.DataFrame({
            "gid": ["1234567890123456", "9876543210987654"],
            "office_phone": ["+15551234567", "+15559876543"],
            "vertical": ["dental", "medical"],
            "name": ["Unit A", "Unit B"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.UnitResolutionStrategy._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            # Setup mock client
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "meta" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["gid"] == "1234567890123456"
        assert data["results"][0]["error"] is None
        assert data["meta"]["entity_type"] == "unit"
        assert data["meta"]["resolved_count"] == 1
        assert data["meta"]["unresolved_count"] == 0

    def test_unknown_phone_vertical_returns_not_found(self, client: TestClient) -> None:
        """TC-002: Unknown phone/vertical returns null with NOT_FOUND."""
        import polars as pl

        jwt_token = "header.payload.signature"

        # Create mock DataFrame without matching data
        mock_df = pl.DataFrame({
            "gid": ["1111111111111111"],
            "office_phone": ["+11111111111"],
            "vertical": ["other"],
            "name": ["Other Unit"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.UnitResolutionStrategy._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15559999999", "vertical": "unknown"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["gid"] is None
        assert data["results"][0]["error"] == "NOT_FOUND"
        assert data["meta"]["resolved_count"] == 0
        assert data["meta"]["unresolved_count"] == 1

    def test_invalid_e164_returns_422(self, client: TestClient) -> None:
        """TC-003: Invalid E.164 returns 422."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "5551234567", "vertical": "dental"},  # Missing +
                    ]
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_missing_vertical_returns_422(self, client: TestClient) -> None:
        """TC-004: Missing vertical returns 422."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567"},  # Missing vertical
                    ]
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "MISSING_REQUIRED_FIELD"

    def test_empty_criteria_returns_empty_results(self, client: TestClient) -> None:
        """TC-013: Empty criteria returns 200 with empty results."""
        jwt_token = "header.payload.signature"

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"criteria": []},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["meta"]["resolved_count"] == 0
        assert data["meta"]["unresolved_count"] == 0


class TestResolveValidation:
    """Test input validation for resolve endpoint."""

    def test_batch_over_1000_returns_422(self, client: TestClient) -> None:
        """Batch size > 1000 returns 422 validation error."""
        jwt_token = "header.payload.signature"

        # Create 1001 criteria
        criteria = [
            {"phone": f"+1555{i:07d}", "vertical": "dental"}
            for i in range(1001)
        ]

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"criteria": criteria},
            )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        error_msg = str(data["detail"]).lower()
        assert "batch" in error_msg or "1000" in error_msg

    def test_batch_exactly_1000_succeeds(self, client: TestClient) -> None:
        """TC-005: Batch 1000 completes successfully."""
        import polars as pl

        jwt_token = "header.payload.signature"

        # Create mock DataFrame
        mock_df = pl.DataFrame({
            "gid": ["1111111111111111"],
            "office_phone": ["+11111111111"],
            "vertical": ["dental"],
            "name": ["Unit A"],
        })

        criteria = [
            {"phone": f"+1555{i:07d}", "vertical": "dental"}
            for i in range(1000)
        ]

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.UnitResolutionStrategy._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            start_time = time.monotonic()
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"criteria": criteria},
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1000
        # TC-005: Batch 1000 completes <1000ms (with mock, should be much faster)
        assert elapsed_ms < 1000, f"Batch 1000 took {elapsed_ms}ms, expected <1000ms"

    def test_extra_fields_rejected(self, client: TestClient) -> None:
        """Extra fields in request body are rejected."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ],
                    "extra_field": "should_be_rejected",
                },
            )

        assert response.status_code == 422


class TestResolveAuthentication:
    """Test authentication requirements for resolve endpoint."""

    def test_missing_auth_header_returns_401(self, client: TestClient) -> None:
        """Missing Authorization header returns 401."""
        response = client.post(
            "/v1/resolve/unit",
            json={
                "criteria": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "MISSING_AUTH"

    def test_pat_token_returns_401(self, client: TestClient) -> None:
        """TC-012: PAT token returns 401 with SERVICE_TOKEN_REQUIRED."""
        # PAT tokens start with 0/ or 1/ (no dots)
        pat_token = "0/1234567890abcdef1234567890"

        response = client.post(
            "/v1/resolve/unit",
            headers={"Authorization": f"Bearer {pat_token}"},
            json={
                "criteria": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "SERVICE_TOKEN_REQUIRED"
        assert "service-to-service" in data["detail"]["message"].lower()

    def test_invalid_jwt_returns_401(self, client: TestClient) -> None:
        """Invalid JWT returns 401 with validation error."""
        jwt_token = "invalid.jwt.token"

        mock_error = Exception("Token expired")
        mock_error.code = "TOKEN_EXPIRED"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            AsyncMock(side_effect=mock_error),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "TOKEN_EXPIRED"

    def test_valid_jwt_allows_access(self, client: TestClient) -> None:
        """Valid JWT token allows access to endpoint."""
        import polars as pl

        jwt_token = "header.payload.signature"

        mock_df = pl.DataFrame({
            "gid": ["1234567890123456"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
            "name": ["Unit A"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(service_name="test_service"),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.UnitResolutionStrategy._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 200


class TestResolveEntityType:
    """Test entity_type path parameter validation."""

    def test_unknown_entity_type_returns_404(self, client: TestClient) -> None:
        """TC-014: Invalid entity_type returns 404 UNKNOWN_ENTITY_TYPE."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/invalid_type",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "UNKNOWN_ENTITY_TYPE"
        assert "invalid_type" in data["detail"]["message"]

    def test_business_entity_type_returns_503_when_not_configured(
        self, client: TestClient
    ) -> None:
        """Business returns 503 when project not registered in discovery."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/business",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        # Business entity type IS supported (Phase 2), but project not registered
        # The base app fixture only registers "unit" project
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "PROJECT_NOT_CONFIGURED"


class TestResolveDiscoveryIncomplete:
    """Test behavior when discovery is incomplete."""

    def test_discovery_incomplete_returns_503(self) -> None:
        """Returns 503 when entity resolver discovery not complete."""
        # Reset singleton to ensure clean state
        EntityProjectRegistry.reset()

        # Create app WITHOUT mocking discovery (so registry stays empty)
        with patch(
            "autom8_asana.api.main._discover_entity_projects",
            new_callable=AsyncMock,
        ) as mock_discover:
            # Don't set up registry, leave it empty (not ready)
            async def no_setup(app):
                EntityProjectRegistry.reset()
                registry = EntityProjectRegistry.get_instance()
                # Don't register anything - leave empty so is_ready() returns False
                app.state.entity_project_registry = registry

            mock_discover.side_effect = no_setup
            test_app = create_app()

            jwt_token = "header.payload.signature"

            with TestClient(test_app) as test_client:
                with patch(
                    "autom8_asana.api.routes.internal.validate_service_token",
                    _mock_jwt_validation(),
                ):
                    response = test_client.post(
                        "/v1/resolve/unit",
                        headers={"Authorization": f"Bearer {jwt_token}"},
                        json={
                            "criteria": [
                                {"phone": "+15551234567", "vertical": "dental"},
                            ]
                        },
                    )

                assert response.status_code == 503
                data = response.json()
                assert data["detail"]["error"] == "DISCOVERY_INCOMPLETE"


class TestResolveInputOrder:
    """Test that input order is preserved in response."""

    def test_preserves_input_order(self, client: TestClient) -> None:
        """Response results preserve input order."""
        import polars as pl

        jwt_token = "header.payload.signature"

        # Create mock DataFrame with multiple units
        mock_df = pl.DataFrame({
            "gid": ["1111111111111111", "2222222222222222", "3333333333333333"],
            "office_phone": ["+11111111111", "+12222222222", "+13333333333"],
            "vertical": ["a", "b", "c"],
            "name": ["Unit A", "Unit B", "Unit C"],
        })

        criteria = [
            {"phone": "+11111111111", "vertical": "a"},
            {"phone": "+12222222222", "vertical": "b"},
            {"phone": "+14444444444", "vertical": "d"},  # Not found
            {"phone": "+13333333333", "vertical": "c"},
        ]

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.UnitResolutionStrategy._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"criteria": criteria},
            )

        assert response.status_code == 200
        data = response.json()

        # Verify order matches input
        assert len(data["results"]) == 4
        assert data["results"][0]["gid"] == "1111111111111111"
        assert data["results"][1]["gid"] == "2222222222222222"
        assert data["results"][2]["gid"] is None  # Not found
        assert data["results"][2]["error"] == "NOT_FOUND"
        assert data["results"][3]["gid"] == "3333333333333333"


class TestResolutionCriterionModel:
    """Test ResolutionCriterion model validation."""

    def test_valid_phone_vertical(self) -> None:
        """ResolutionCriterion accepts valid phone/vertical."""
        from autom8_asana.api.routes.resolver import ResolutionCriterion

        criterion = ResolutionCriterion(phone="+15551234567", vertical="dental")
        assert criterion.phone == "+15551234567"
        assert criterion.vertical == "dental"

    def test_invalid_phone_format(self) -> None:
        """ResolutionCriterion rejects invalid phone format."""
        from autom8_asana.api.routes.resolver import ResolutionCriterion
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ResolutionCriterion(phone="5551234567", vertical="dental")

    def test_phone_starting_with_zero_rejected(self) -> None:
        """Phone starting with zero after + is rejected."""
        from autom8_asana.api.routes.resolver import ResolutionCriterion
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ResolutionCriterion(phone="+05551234567", vertical="dental")

    def test_phone_with_dashes_rejected(self) -> None:
        """Phone with dashes is rejected."""
        from autom8_asana.api.routes.resolver import ResolutionCriterion
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ResolutionCriterion(phone="+1-555-123-4567", vertical="dental")

    def test_phone_with_trailing_newline_stripped(self) -> None:
        """Phone with trailing newline is stripped and validated (DEF-002)."""
        from autom8_asana.api.routes.resolver import ResolutionCriterion

        # Trailing newline should be stripped, phone should be valid
        criterion = ResolutionCriterion(phone="+15551234567\n", vertical="dental")
        assert criterion.phone == "+15551234567"

    def test_phone_with_whitespace_stripped(self) -> None:
        """Phone with leading/trailing whitespace is stripped."""
        from autom8_asana.api.routes.resolver import ResolutionCriterion

        criterion = ResolutionCriterion(phone="  +15551234567  ", vertical="dental")
        assert criterion.phone == "+15551234567"


class TestEntityProjectRegistry:
    """Test EntityProjectRegistry singleton."""

    def test_singleton_instance(self) -> None:
        """get_instance returns singleton."""
        EntityProjectRegistry.reset()
        registry1 = EntityProjectRegistry.get_instance()
        registry2 = EntityProjectRegistry.get_instance()
        assert registry1 is registry2

    def test_register_and_get(self) -> None:
        """Can register and retrieve project GID."""
        EntityProjectRegistry.reset()
        registry = EntityProjectRegistry.get_instance()

        registry.register(
            entity_type="unit",
            project_gid="1234567890",
            project_name="Units",
        )

        assert registry.get_project_gid("unit") == "1234567890"
        assert registry.is_ready()

    def test_reset_clears_instance(self) -> None:
        """reset clears the singleton instance."""
        EntityProjectRegistry.reset()
        registry = EntityProjectRegistry.get_instance()
        registry.register("unit", "123", "Units")
        assert registry.is_ready()

        EntityProjectRegistry.reset()
        new_registry = EntityProjectRegistry.get_instance()
        assert not new_registry.is_ready()
        assert new_registry is not registry

    def test_get_all_entity_types(self) -> None:
        """get_all_entity_types returns registered types."""
        EntityProjectRegistry.reset()
        registry = EntityProjectRegistry.get_instance()

        registry.register("unit", "123", "Units")
        registry.register("business", "456", "Business")

        types = registry.get_all_entity_types()
        assert "unit" in types
        assert "business" in types


# =============================================================================
# Phase 2 Tests: Business, Offer, Contact Resolution
# =============================================================================


@pytest.fixture
def phase2_app():
    """Create a test application with all Phase 2 entity types registered."""
    with patch(
        "autom8_asana.api.main._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:
        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid="1201081073731555",
                project_name="units",
            )
            registry.register(
                entity_type="business",
                project_gid="1201081073731556",
                project_name="business",
            )
            registry.register(
                entity_type="offer",
                project_gid="1201081073731557",
                project_name="offers",
            )
            registry.register(
                entity_type="contact",
                project_gid="1201081073731558",
                project_name="contacts",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture
def phase2_client(phase2_app) -> Generator[TestClient, None, None]:
    """Create a test client with Phase 2 entity types."""
    with TestClient(phase2_app) as test_client:
        yield test_client


class TestBusinessResolution:
    """Test POST /v1/resolve/business."""

    def test_valid_phone_vertical_returns_business_gid(
        self, phase2_client: TestClient
    ) -> None:
        """TC-006: Valid phone/vertical returns parent (Business) GID."""
        import polars as pl

        jwt_token = "header.payload.signature"

        # Create mock Unit DataFrame
        mock_df = pl.DataFrame({
            "gid": ["unit_1234567890"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
            "name": ["Unit A"],
        })

        # Mock task with parent
        mock_task = MagicMock()
        mock_task.parent = MagicMock()
        mock_task.parent.gid = "business_9876543210"

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.UnitResolutionStrategy._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.tasks = MagicMock()
            mock_client.tasks.get_async = AsyncMock(return_value=mock_task)
            mock_client_class.return_value = mock_client

            response = phase2_client.post(
                "/v1/resolve/business",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["gid"] == "business_9876543210"
        assert data["results"][0]["error"] is None
        assert data["meta"]["entity_type"] == "business"
        assert data["meta"]["resolved_count"] == 1

    def test_unit_exists_no_parent_returns_error(
        self, phase2_client: TestClient
    ) -> None:
        """TC-007: Unit exists but no parent returns null with error."""
        import polars as pl

        jwt_token = "header.payload.signature"

        mock_df = pl.DataFrame({
            "gid": ["unit_1234567890"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
            "name": ["Unit A"],
        })

        # Mock task WITHOUT parent
        mock_task = MagicMock()
        mock_task.parent = None

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.UnitResolutionStrategy._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.tasks = MagicMock()
            mock_client.tasks.get_async = AsyncMock(return_value=mock_task)
            mock_client_class.return_value = mock_client

            response = phase2_client.post(
                "/v1/resolve/business",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["gid"] is None
        assert data["results"][0]["error"] == "NO_PARENT_BUSINESS"


class TestOfferResolution:
    """Test POST /v1/resolve/offer."""

    def test_valid_offer_id_returns_gid(self, phase2_client: TestClient) -> None:
        """TC-008: Valid offer_id returns GID."""
        import polars as pl

        jwt_token = "header.payload.signature"

        mock_df = pl.DataFrame({
            "gid": ["offer_1234567890"],
            "offer_id": ["OFFER-001"],
            "name": ["Summer Sale"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.OfferResolutionStrategy._build_offer_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = phase2_client.post(
                "/v1/resolve/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"offer_id": "OFFER-001"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["gid"] == "offer_1234567890"
        assert data["meta"]["entity_type"] == "offer"

    def test_phone_vertical_offer_name_returns_gid(
        self, phase2_client: TestClient
    ) -> None:
        """TC-009: phone/vertical + offer_name returns GID."""
        import polars as pl

        jwt_token = "header.payload.signature"

        mock_df = pl.DataFrame({
            "gid": ["offer_1234567890"],
            "offer_id": ["OFFER-001"],
            "name": ["Summer Sale"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.OfferResolutionStrategy._build_offer_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = phase2_client.post(
                "/v1/resolve/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {
                            "phone": "+15551234567",
                            "vertical": "dental",
                            "offer_name": "Summer Sale",
                        },
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["gid"] == "offer_1234567890"

    def test_offer_missing_required_fields_returns_422(
        self, phase2_client: TestClient
    ) -> None:
        """Offer with only phone (missing vertical and offer_name) returns 422."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = phase2_client.post(
                "/v1/resolve/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567"},  # Missing vertical and offer_name
                    ]
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "MISSING_REQUIRED_FIELD"


class TestContactResolution:
    """Test POST /v1/resolve/contact."""

    def test_valid_email_returns_gid(self, phase2_client: TestClient) -> None:
        """TC-010: Valid email returns GID."""
        import polars as pl

        jwt_token = "header.payload.signature"

        mock_df = pl.DataFrame({
            "gid": ["contact_1234567890"],
            "contact_email": ["john@example.com"],
            "contact_phone": ["+15551234567"],
            "full_name": ["John Doe"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.ContactResolutionStrategy._build_contact_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = phase2_client.post(
                "/v1/resolve/contact",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"contact_email": "john@example.com"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["gid"] == "contact_1234567890"
        assert data["results"][0]["multiple"] is None
        assert data["meta"]["entity_type"] == "contact"

    def test_multiple_matches_returns_multiple_flag(
        self, phase2_client: TestClient
    ) -> None:
        """TC-011: Multiple matches returns all with multiple=true."""
        import polars as pl

        jwt_token = "header.payload.signature"

        # DataFrame with multiple contacts having same email
        mock_df = pl.DataFrame({
            "gid": ["contact_111", "contact_222", "contact_333"],
            "contact_email": ["shared@example.com", "shared@example.com", "other@example.com"],
            "contact_phone": ["+15551111111", "+15552222222", "+15553333333"],
            "full_name": ["John Doe", "Jane Doe", "Bob Smith"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.ContactResolutionStrategy._build_contact_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = phase2_client.post(
                "/v1/resolve/contact",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"contact_email": "shared@example.com"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["gid"] == "contact_111"  # First match
        assert data["results"][0]["multiple"] is True  # Multiple flag set
        assert data["meta"]["resolved_count"] == 1

    def test_contact_phone_lookup(self, phase2_client: TestClient) -> None:
        """Contact phone lookup returns GID."""
        import polars as pl

        jwt_token = "header.payload.signature"

        mock_df = pl.DataFrame({
            "gid": ["contact_1234567890"],
            "contact_email": ["john@example.com"],
            "contact_phone": ["+15551234567"],
            "full_name": ["John Doe"],
        })

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.resolver.ContactResolutionStrategy._build_contact_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = phase2_client.post(
                "/v1/resolve/contact",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"contact_phone": "+15551234567"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["gid"] == "contact_1234567890"

    def test_contact_missing_email_and_phone_returns_422(
        self, phase2_client: TestClient
    ) -> None:
        """Contact with neither email nor phone returns 422."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = phase2_client.post(
                "/v1/resolve/contact",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {},  # Empty criterion - no email or phone
                    ]
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "MISSING_REQUIRED_FIELD"


class TestFieldFiltering:
    """Test field filtering with SchemaRegistry validation."""

    def test_invalid_field_returns_422(self, client: TestClient) -> None:
        """TC-015: Invalid field name in request returns 422."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ],
                    "fields": ["nonexistent_field"],
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "INVALID_FIELD"
        assert "Invalid fields" in data["detail"]["message"]
        assert "nonexistent_field" in data["detail"]["message"]

    def test_filter_result_fields_default_gid_only(self) -> None:
        """Default (no fields) returns gid only."""
        from autom8_asana.services.resolver import filter_result_fields

        result = {
            "gid": "1234567890",
            "name": "Test Task",
            "office_phone": "+15551234567",
            "vertical": "dental",
        }

        filtered = filter_result_fields(result, None, "unit")
        assert filtered == {"gid": "1234567890"}

    def test_filter_result_fields_requested_fields(self) -> None:
        """Requested fields are included with gid."""
        from autom8_asana.services.resolver import filter_result_fields

        result = {
            "gid": "1234567890",
            "name": "Test Task",
            "office_phone": "+15551234567",
            "vertical": "dental",
        }

        filtered = filter_result_fields(result, ["name", "vertical"], "unit")
        assert filtered == {
            "gid": "1234567890",
            "name": "Test Task",
            "vertical": "dental",
        }

    def test_filter_result_fields_invalid_field_raises(self) -> None:
        """Invalid field raises ValueError."""
        from autom8_asana.services.resolver import filter_result_fields

        result = {"gid": "1234567890", "name": "Test Task"}

        with pytest.raises(ValueError, match="Invalid fields"):
            filter_result_fields(result, ["nonexistent_field"], "unit")

    def test_filter_result_fields_gid_always_included(self) -> None:
        """gid is always included even if not in requested fields."""
        from autom8_asana.services.resolver import filter_result_fields

        result = {
            "gid": "1234567890",
            "name": "Test Task",
        }

        filtered = filter_result_fields(result, ["name"], "unit")
        assert "gid" in filtered


class TestStrategyRegistration:
    """Test that all Phase 2 strategies are registered."""

    def test_all_strategies_registered(self) -> None:
        """All four entity types have strategies registered."""
        from autom8_asana.services.resolver import RESOLUTION_STRATEGIES

        assert "unit" in RESOLUTION_STRATEGIES
        assert "business" in RESOLUTION_STRATEGIES
        assert "offer" in RESOLUTION_STRATEGIES
        assert "contact" in RESOLUTION_STRATEGIES

    def test_business_strategy_uses_unit_strategy(self) -> None:
        """BusinessResolutionStrategy delegates to UnitResolutionStrategy."""
        from autom8_asana.services.resolver import (
            RESOLUTION_STRATEGIES,
            BusinessResolutionStrategy,
            UnitResolutionStrategy,
        )

        business_strategy = RESOLUTION_STRATEGIES["business"]
        assert isinstance(business_strategy, BusinessResolutionStrategy)
        assert isinstance(business_strategy._unit_strategy, UnitResolutionStrategy)
