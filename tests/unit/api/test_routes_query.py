"""Tests for query routes (/v1/query/*).

Per TDD-entity-query-endpoint:
- POST /v1/query/{entity_type} requires service token (S2S)
- Uses UniversalResolutionStrategy._get_dataframe() for cache lifecycle
- Supports where clause filtering (AND semantics, equality only)
- Supports field selection via select parameter
- Supports pagination via limit/offset
- Returns 503 when cache not warmed

Test Matrix (per TDD):
- TC-001: Valid query with where clause returns matching records
- TC-002: Empty where returns all records (paginated)
- TC-003: Field selection (select parameter)
- TC-004: Pagination (limit/offset)
- TC-005: Invalid entity type returns 404
- TC-006: Invalid field in where clause returns 422
- TC-007: Invalid field in select returns 422
- TC-008: Missing authentication returns 401
- TC-009: PAT token returns 401 SERVICE_TOKEN_REQUIRED
- TC-010: Cache miss returns 503 CACHE_NOT_WARMED
- TC-011: Multiple where fields (AND semantics)
- TC-012: Limit clamped to 1000
- TC-013: Negative offset returns 422
- TC-014: Offset beyond total_count returns empty data with correct total
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.services.query_service import CacheNotWarmError
from autom8_asana.services.resolver import EntityProjectRegistry


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _create_mock_dataframe(entity_type: str = "offer") -> pl.DataFrame:
    """Create a mock DataFrame for testing."""
    if entity_type == "offer":
        return pl.DataFrame(
            {
                "gid": [
                    "1234567890123456",
                    "1234567890123457",
                    "1234567890123458",
                    "1234567890123459",
                ],
                "name": [
                    "Acme Dental - Facebook",
                    "Beta Medical - Google",
                    "Gamma Dental - Google",
                    "Delta Medical - Facebook",
                ],
                "section": ["ACTIVE", "ACTIVE", "PAUSED", "ACTIVE"],
                "vertical": ["dental", "medical", "dental", "medical"],
                "office_phone": [
                    "+15551234567",
                    "+15559876543",
                    "+15551111111",
                    "+15552222222",
                ],
                "offer_id": ["offer-001", "offer-002", "offer-003", "offer-004"],
            }
        )
    elif entity_type == "unit":
        return pl.DataFrame(
            {
                "gid": ["unit-001", "unit-002"],
                "name": ["Unit A", "Unit B"],
                "section": ["ACTIVE", "ACTIVE"],
                "vertical": ["dental", "medical"],
                "office_phone": ["+15551234567", "+15559876543"],
            }
        )
    return pl.DataFrame(
        {
            "gid": ["generic-001"],
            "name": ["Generic"],
            "section": ["ACTIVE"],
        }
    )


class TestQueryEndpoint:
    """Test POST /v1/query/{entity_type}."""

    def test_valid_query_with_where_clause(self, client: TestClient) -> None:
        """TC-001: Valid query with where clause returns matching records."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "where": {"section": "ACTIVE"},
                    "select": ["gid", "name", "section"],
                    "limit": 100,
                    "offset": 0,
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "data" in data
        assert "meta" in data
        assert len(data["data"]) == 3  # 3 ACTIVE offers
        assert data["meta"]["total_count"] == 3
        assert data["meta"]["entity_type"] == "offer"
        assert data["meta"]["project_gid"] == "1143843662099250"
        # Verify all returned records have section=ACTIVE
        for record in data["data"]:
            assert record["section"] == "ACTIVE"

    def test_empty_where_returns_all_records(self, client: TestClient) -> None:
        """TC-002: Empty where clause returns all records (paginated)."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 100},  # Empty where
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 4  # All 4 records
        assert data["meta"]["total_count"] == 4

    def test_field_selection(self, client: TestClient) -> None:
        """TC-003: Select parameter limits returned fields."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "select": ["gid", "name", "vertical"],
                    "limit": 100,
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) > 0
        # gid is always included
        assert "gid" in data["data"][0]
        assert "name" in data["data"][0]
        assert "vertical" in data["data"][0]
        # section should NOT be present (not in select)
        assert (
            "section" not in data["data"][0] or data["data"][0].get("section") is None
        )

    def test_pagination_limit(self, client: TestClient) -> None:
        """TC-004a: Limit parameter controls result count."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 2},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 2
        assert data["meta"]["total_count"] == 4  # Total is still 4
        assert data["meta"]["limit"] == 2

    def test_pagination_offset(self, client: TestClient) -> None:
        """TC-004b: Offset parameter skips records."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 2, "offset": 2},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 2
        assert data["meta"]["total_count"] == 4
        assert data["meta"]["offset"] == 2

    def test_invalid_entity_type_returns_404(self, client: TestClient) -> None:
        """TC-005: Invalid entity type returns 404 UNKNOWN_ENTITY_TYPE."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/query/invalid_type",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 100},
            )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "UNKNOWN_ENTITY_TYPE"
        assert "invalid_type" in data["detail"]["message"]
        assert "available_types" in data["detail"]

    def test_invalid_field_in_where_returns_422(self, client: TestClient) -> None:
        """TC-006: Invalid field in where clause returns 422 INVALID_FIELD."""
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
        ):
            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "where": {"nonexistent_field": "value"},
                    "limit": 100,
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "INVALID_FIELD"
        assert "nonexistent_field" in data["detail"]["message"]
        assert "available_fields" in data["detail"]

    def test_invalid_field_in_select_returns_422(self, client: TestClient) -> None:
        """TC-007: Invalid field in select returns 422 INVALID_FIELD."""
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
        ):
            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "select": ["gid", "nonexistent_field"],
                    "limit": 100,
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "INVALID_FIELD"

    def test_multiple_where_fields_and_semantics(self, client: TestClient) -> None:
        """TC-011: Multiple where fields use AND semantics."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "where": {"section": "ACTIVE", "vertical": "dental"},
                    "limit": 100,
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        # Should only return "Acme Dental - Facebook" (ACTIVE + dental)
        assert data["meta"]["total_count"] == 1
        assert len(data["data"]) == 1

    def test_limit_clamped_to_1000(self, client: TestClient) -> None:
        """TC-012: Limit over 1000 is clamped to 1000."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 5000},  # Over 1000
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["meta"]["limit"] == 1000  # Clamped

    def test_negative_offset_returns_422(self, client: TestClient) -> None:
        """TC-013: Negative offset returns 422 validation error."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"offset": -1},
            )

        assert response.status_code == 422

    def test_offset_beyond_total_returns_empty(self, client: TestClient) -> None:
        """TC-014: Offset beyond total_count returns empty data with correct total."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"offset": 1000},  # Beyond 4 records
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 0
        assert data["meta"]["total_count"] == 4  # Total still accurate


class TestQueryAuthentication:
    """Test authentication requirements for query endpoint."""

    def test_missing_auth_header_returns_401(self, client: TestClient) -> None:
        """TC-008: Missing Authorization header returns 401."""
        response = client.post(
            "/v1/query/offer",
            json={"limit": 100},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTH-MISSING-TOKEN"

    def test_pat_token_returns_401(self, client: TestClient) -> None:
        """TC-009: PAT token returns 401 with SERVICE_TOKEN_REQUIRED."""
        pat_token = "0/1234567890abcdef1234567890"

        response = client.post(
            "/v1/query/offer",
            headers={"Authorization": f"Bearer {pat_token}"},
            json={"limit": 100},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "SERVICE_TOKEN_REQUIRED"
        assert "service-to-service" in data["error"]["message"].lower()

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
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 100},
            )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "TOKEN_EXPIRED"


class TestQueryCacheNotWarm:
    """Test behavior when cache is not warmed."""

    def test_cache_not_warm_returns_503(self, client: TestClient) -> None:
        """TC-010: Cache miss returns 503 CACHE_NOT_WARMED."""
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
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=None,  # Cache miss
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 100},
            )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "CACHE_NOT_WARMED"
        assert "retry_after_seconds" in data["detail"]


class TestQueryProjectNotConfigured:
    """Test behavior when project is not configured."""

    def test_empty_registry_returns_error(self) -> None:
        """Returns error when entity registry has no entities registered.

        When EntityProjectRegistry is empty and bot PAT is not configured,
        the auth dependency fails before entity validation, returning 503.
        """
        EntityProjectRegistry.reset()

        with patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
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
                        "/v1/query/offer",
                        headers={"Authorization": f"Bearer {jwt_token}"},
                        json={"limit": 100},
                    )

                # Bot PAT not configured -> 503, or entity not found -> 404
                assert response.status_code in {404, 503}
                data = response.json()
                assert "error" in data or "detail" in data

    def test_registry_none_returns_503(self) -> None:
        """Returns 503 when project not configured for entity type.

        After I2-S2 wiring, EntityService handles entity validation
        via validate_entity_type() which raises ServiceNotConfiguredError
        when the project GID is None.
        """
        from autom8_asana.api.dependencies import get_entity_service
        from autom8_asana.services.entity_service import EntityService
        from autom8_asana.services.errors import ServiceNotConfiguredError

        EntityProjectRegistry.reset()

        with patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ) as mock_discover:

            async def partial_registry_setup(app):
                EntityProjectRegistry.reset()
                registry = EntityProjectRegistry.get_instance()
                app.state.entity_project_registry = registry

            mock_discover.side_effect = partial_registry_setup
            test_app = create_app()

            jwt_token = "header.payload.signature"

            # Mock EntityService to raise ServiceNotConfiguredError
            mock_entity_svc = MagicMock(spec=EntityService)
            mock_entity_svc.validate_entity_type.side_effect = (
                ServiceNotConfiguredError(
                    "No project configured for entity type: offer"
                )
            )

            # Use FastAPI's dependency override for the EntityService
            test_app.dependency_overrides[get_entity_service] = lambda: mock_entity_svc

            try:
                with TestClient(test_app) as test_client:
                    with patch(
                        "autom8_asana.api.routes.internal.validate_service_token",
                        _mock_jwt_validation(),
                    ):
                        response = test_client.post(
                            "/v1/query/offer",
                            headers={"Authorization": f"Bearer {jwt_token}"},
                            json={"limit": 100},
                        )

                    # ServiceNotConfiguredError -> 503
                    assert response.status_code == 503
                    data = response.json()
                    assert data["detail"]["error"] == "SERVICE_NOT_CONFIGURED"
            finally:
                test_app.dependency_overrides.clear()


class TestQueryRequestValidation:
    """Test request body validation."""

    def test_limit_less_than_1_returns_422(self, client: TestClient) -> None:
        """Limit < 1 returns 422 validation error."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 0},
            )

        assert response.status_code == 422

    def test_extra_fields_rejected(self, client: TestClient) -> None:
        """Extra fields in request body are rejected."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "limit": 100,
                    "extra_field": "should_be_rejected",
                },
            )

        assert response.status_code == 422


class TestQueryResponseStructure:
    """Test response structure matches TDD specification."""

    def test_response_has_required_fields(self, client: TestClient) -> None:
        """Response includes all required fields per TDD."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 100},
            )

        assert response.status_code == 200
        outer = response.json()
        assert "data" in outer
        assert "meta" in outer
        data = outer["data"]

        # Domain response structure
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)

        # Meta structure
        meta = data["meta"]
        assert "total_count" in meta
        assert "limit" in meta
        assert "offset" in meta
        assert "entity_type" in meta
        assert "project_gid" in meta

        # Verify types
        assert isinstance(meta["total_count"], int)
        assert isinstance(meta["limit"], int)
        assert isinstance(meta["offset"], int)
        assert isinstance(meta["entity_type"], str)
        assert isinstance(meta["project_gid"], str)

    def test_gid_always_included_in_results(self, client: TestClient) -> None:
        """gid is always included in results regardless of select."""
        jwt_token = "header.payload.signature"
        mock_df = _create_mock_dataframe("offer")

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "select": ["name"],  # No gid in select
                    "limit": 100,
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        # gid should still be present
        for record in data["data"]:
            assert "gid" in record


class TestEntityQueryService:
    """Unit tests for EntityQueryService."""

    @pytest.mark.asyncio
    async def test_query_applies_filters_correctly(self) -> None:
        """EntityQueryService applies where filters correctly."""
        from autom8_asana.services.query_service import EntityQueryService

        mock_df = _create_mock_dataframe("offer")

        # Create mock strategy
        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=mock_df)

        service = EntityQueryService(strategy_factory=lambda _: mock_strategy)
        mock_client = MagicMock()

        result = await service.query(
            entity_type="offer",
            project_gid="123",
            client=mock_client,
            where={"section": "ACTIVE"},
            select=["gid", "name"],
            limit=100,
            offset=0,
        )

        assert result.total_count == 3  # 3 ACTIVE
        assert len(result.data) == 3

    @pytest.mark.asyncio
    async def test_query_raises_on_cache_miss(self) -> None:
        """EntityQueryService raises CacheNotWarmError on cache miss."""
        from autom8_asana.services.query_service import EntityQueryService

        # Create mock strategy that returns None (cache miss)
        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=None)

        service = EntityQueryService(strategy_factory=lambda _: mock_strategy)
        mock_client = MagicMock()

        with pytest.raises(CacheNotWarmError):
            await service.query(
                entity_type="offer",
                project_gid="123",
                client=mock_client,
                where={},
                select=None,
                limit=100,
                offset=0,
            )

    @pytest.mark.asyncio
    async def test_query_pagination(self) -> None:
        """EntityQueryService applies pagination correctly."""
        from autom8_asana.services.query_service import EntityQueryService

        mock_df = _create_mock_dataframe("offer")

        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=mock_df)

        service = EntityQueryService(strategy_factory=lambda _: mock_strategy)
        mock_client = MagicMock()

        result = await service.query(
            entity_type="offer",
            project_gid="123",
            client=mock_client,
            where={},
            select=["gid"],
            limit=2,
            offset=1,
        )

        # Total is 4, but we skip 1 and take 2
        assert result.total_count == 4
        assert len(result.data) == 2


class TestQueryModels:
    """Test Pydantic model validation."""

    def test_query_request_defaults(self) -> None:
        """QueryRequest has correct defaults."""
        from autom8_asana.api.routes.query import QueryRequest

        request = QueryRequest()
        assert request.where == {}
        assert request.select is None
        assert request.limit == 100
        assert request.offset == 0

    def test_query_request_limit_clamped(self) -> None:
        """QueryRequest clamps limit to 1000."""
        from autom8_asana.api.routes.query import QueryRequest

        request = QueryRequest(limit=5000)
        assert request.limit == 1000

    def test_query_request_negative_offset_rejected(self) -> None:
        """QueryRequest rejects negative offset."""
        import pydantic

        from autom8_asana.api.routes.query import QueryRequest

        with pytest.raises(pydantic.ValidationError):
            QueryRequest(offset=-1)

    def test_query_request_zero_limit_rejected(self) -> None:
        """QueryRequest rejects limit < 1."""
        import pydantic

        from autom8_asana.api.routes.query import QueryRequest

        with pytest.raises(pydantic.ValidationError):
            QueryRequest(limit=0)
