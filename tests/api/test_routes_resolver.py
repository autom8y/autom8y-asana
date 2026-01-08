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

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.dynamic_index import DynamicIndex
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.services.resolver import EntityProjectRegistry, LEGACY_FIELD_MAPPING


def _make_mock_cache_provider(mock_df: pl.DataFrame):
    """Create a mock cache provider that returns the given DataFrame."""
    mock_cache = MagicMock()
    mock_entry = MagicMock()
    mock_entry.dataframe = mock_df
    mock_cache.get_async = AsyncMock(return_value=mock_entry)
    mock_cache.put_async = AsyncMock()
    mock_cache.acquire_build_lock_async = AsyncMock(return_value=True)
    mock_cache.release_build_lock_async = AsyncMock()
    return lambda: mock_cache


def _apply_legacy_mapping(criterion: dict, entity_type: str) -> dict:
    """Apply legacy field mapping to criterion (same as UniversalResolutionStrategy)."""
    mapped = dict(criterion)
    # Apply global mappings
    global_map = LEGACY_FIELD_MAPPING.get("_global", {})
    for old_key, new_key in global_map.items():
        if old_key in mapped:
            mapped[new_key] = mapped.pop(old_key)
    # Apply entity-specific mappings
    entity_map = LEGACY_FIELD_MAPPING.get(entity_type, {})
    for old_key, new_key in entity_map.items():
        if old_key in mapped:
            mapped[new_key] = mapped.pop(old_key)
    return mapped


def _make_mock_strategy_resolve(
    mock_df: pl.DataFrame, key_columns: list[str], entity_type: str = "unit"
):
    """Create a mock resolve function using the universal strategy pattern."""

    async def mock_resolve(self, criteria, project_gid, client):
        # Build index from mock DataFrame
        index = DynamicIndex.from_dataframe(mock_df, key_columns)
        results = []
        for criterion in criteria:
            # Apply legacy mapping like real strategy does
            mapped = _apply_legacy_mapping(criterion, entity_type)
            gids = index.lookup(mapped)
            if gids:
                results.append(ResolutionResult.from_gids(gids))
            else:
                results.append(ResolutionResult.not_found())
        return results

    return mock_resolve


@pytest.fixture
def app():
    """Create a test application instance with mocked discovery."""
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
        jwt_token = "header.payload.signature"

        # Create mock DataFrame with matching data
        mock_df = pl.DataFrame({
            "gid": ["1234567890123456", "9876543210987654"],
            "office_phone": ["+15551234567", "+15559876543"],
            "vertical": ["dental", "medical"],
            "name": ["Unit A", "Unit B"],
        })

        # Create mock strategy that uses DynamicIndex
        mock_resolve = _make_mock_strategy_resolve(mock_df, ["office_phone", "vertical"])

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
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
                mock_resolve,
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
        jwt_token = "header.payload.signature"

        # Create mock DataFrame without matching data
        mock_df = pl.DataFrame({
            "gid": ["1111111111111111"],
            "office_phone": ["+11111111111"],
            "vertical": ["other"],
            "name": ["Other Unit"],
        })

        mock_resolve = _make_mock_strategy_resolve(mock_df, ["office_phone", "vertical"])

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
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
                mock_resolve,
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


class TestResolveDiscoveryIncomplete:
    """Test behavior when discovery is incomplete."""

    def test_discovery_incomplete_returns_503(self) -> None:
        """Returns 503 when entity resolver discovery not complete."""
        EntityProjectRegistry.reset()

        with patch(
            "autom8_asana.api.main._discover_entity_projects",
            new_callable=AsyncMock,
        ) as mock_discover:
            async def no_setup(app):
                EntityProjectRegistry.reset()
                registry = EntityProjectRegistry.get_instance()
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
        jwt_token = "header.payload.signature"

        mock_df = pl.DataFrame({
            "gid": ["1111111111111111", "2222222222222222", "3333333333333333"],
            "office_phone": ["+11111111111", "+12222222222", "+13333333333"],
            "vertical": ["a", "b", "c"],
            "name": ["Unit A", "Unit B", "Unit C"],
        })

        mock_resolve = _make_mock_strategy_resolve(mock_df, ["office_phone", "vertical"])

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
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
                mock_resolve,
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

        assert len(data["results"]) == 4
        assert data["results"][0]["gid"] == "1111111111111111"
        assert data["results"][1]["gid"] == "2222222222222222"
        assert data["results"][2]["gid"] is None
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

    def test_phone_with_trailing_newline_stripped(self) -> None:
        """Phone with trailing newline is stripped and validated (DEF-002)."""
        from autom8_asana.api.routes.resolver import ResolutionCriterion

        criterion = ResolutionCriterion(phone="+15551234567\n", vertical="dental")
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


class TestUniversalStrategyIntegration:
    """Test that universal strategy is properly integrated."""

    def test_get_strategy_returns_universal_strategy(self) -> None:
        """get_strategy returns UniversalResolutionStrategy."""
        from autom8_asana.services.resolver import get_strategy

        # Register entity to make it resolvable
        EntityProjectRegistry.reset()
        registry = EntityProjectRegistry.get_instance()
        registry.register("unit", "123", "Units")

        strategy = get_strategy("unit")

        from autom8_asana.services.universal_strategy import UniversalResolutionStrategy
        assert isinstance(strategy, UniversalResolutionStrategy)

    def test_get_strategy_returns_none_for_unknown(self) -> None:
        """get_strategy returns None for unknown entity type."""
        from autom8_asana.services.resolver import get_strategy

        EntityProjectRegistry.reset()

        strategy = get_strategy("unknown_entity")
        assert strategy is None


class TestSchemaDiscoveryEndpoint:
    """Test GET /v1/resolve/{entity_type}/schema endpoint.

    Per SPIKE-dynamic-api-criteria: Schema discovery enables API consumers
    to discover valid criterion fields dynamically.
    """

    def test_schema_endpoint_returns_queryable_fields(self, client: TestClient) -> None:
        """Schema endpoint returns field metadata for valid entity type."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema",
                headers={"Authorization": f"Bearer {jwt_token}"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["entity_type"] == "unit"
        assert "version" in data
        assert "queryable_fields" in data
        assert isinstance(data["queryable_fields"], list)

        # Verify expected fields present
        field_names = [f["name"] for f in data["queryable_fields"]]
        assert "gid" in field_names
        assert "name" in field_names

    def test_schema_endpoint_unknown_entity_returns_404(
        self, client: TestClient
    ) -> None:
        """Unknown entity type returns 404 with helpful error."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/invalid_type/schema",
                headers={"Authorization": f"Bearer {jwt_token}"},
            )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "UNKNOWN_ENTITY_TYPE"
        assert "available_types" in data["detail"]

    def test_schema_endpoint_requires_auth(self, client: TestClient) -> None:
        """Schema endpoint requires authentication."""
        response = client.get("/v1/resolve/unit/schema")
        assert response.status_code == 401

    def test_schema_endpoint_returns_field_types(self, client: TestClient) -> None:
        """Schema fields include type information."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema",
                headers={"Authorization": f"Bearer {jwt_token}"},
            )

        assert response.status_code == 200
        data = response.json()

        # Find gid field and verify it has type info
        gid_field = next(
            (f for f in data["queryable_fields"] if f["name"] == "gid"), None
        )
        assert gid_field is not None
        assert "type" in gid_field


class TestDynamicCriteriaFields:
    """Test that dynamic criterion fields are accepted.

    Per SPIKE-dynamic-api-criteria: ResolutionCriterion uses extra="allow"
    to accept arbitrary schema columns beyond the typed common fields.
    """

    def test_dynamic_criterion_field_not_rejected(self, client: TestClient) -> None:
        """Dynamic criterion fields (not in typed model) are not immediately rejected.

        The field validation happens at the backend strategy level, not the API model.
        """
        jwt_token = "header.payload.signature"

        # Create mock DataFrame with the dynamic field
        mock_df = pl.DataFrame(
            {
                "gid": ["1234567890123456"],
                "mrr": ["5000"],  # Dynamic field
                "vertical": ["dental"],
                "office_phone": ["+15551234567"],
            }
        )

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.api.routes.resolver.get_strategy",
            ) as mock_get_strategy,
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="mock-pat",
            ),
        ):
            # Create mock strategy
            mock_strategy = MagicMock()
            mock_strategy.entity_type = "unit"
            mock_strategy.validate_criterion.return_value = []  # No validation errors
            mock_strategy.resolve = AsyncMock(
                return_value=[ResolutionResult.from_gids(["1234567890123456"])]
            )
            mock_get_strategy.return_value = mock_strategy

            # Use a dynamic field (mrr) not in the typed model
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"mrr": "5000", "vertical": "dental"},  # mrr is dynamic
                    ]
                },
            )

        # Should not be rejected at API level (extra="allow")
        # Backend validation determines if field is valid
        assert response.status_code == 200

    def test_invalid_dynamic_field_rejected_by_backend(
        self, client: TestClient
    ) -> None:
        """Invalid dynamic fields are rejected by backend validation."""
        jwt_token = "header.payload.signature"

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.api.routes.resolver.get_strategy",
            ) as mock_get_strategy,
        ):
            # Create mock strategy that rejects the field
            mock_strategy = MagicMock()
            mock_strategy.entity_type = "unit"
            mock_strategy.validate_criterion.return_value = [
                "Unknown field 'invalid_field'. Valid: [gid, mrr, name, ...]"
            ]
            mock_get_strategy.return_value = mock_strategy

            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "criteria": [
                        {"invalid_field": "value"},  # Not in schema
                    ]
                },
            )

        # Backend validation rejects unknown field
        assert response.status_code == 422
        data = response.json()
        assert "MISSING_REQUIRED_FIELD" in data["detail"]["error"]
