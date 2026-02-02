"""Unit tests for admin cache refresh endpoint.

Per TDD-cache-freshness-remediation Fix 4: Tests for POST /v1/admin/cache/refresh.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.routes.admin import (
    VALID_ENTITY_TYPES,
    CacheRefreshRequest,
    CacheRefreshResponse,
    router,
)
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with admin router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def mock_service_claims() -> ServiceClaims:
    """Create mock service claims for S2S auth."""
    return ServiceClaims(
        sub="service-123",
        service_name="test-service",
        scope="multi-tenant",
    )


@pytest.fixture
def authed_app(app: FastAPI, mock_service_claims: ServiceClaims) -> FastAPI:
    """Create app with mocked S2S authentication."""

    async def override_require_service_claims() -> ServiceClaims:
        return mock_service_claims

    app.dependency_overrides[require_service_claims] = (
        override_require_service_claims
    )
    return app


@pytest.fixture
def client(authed_app: FastAPI) -> TestClient:
    """Create test client with authed app."""
    return TestClient(authed_app)


@pytest.fixture
def unauthed_client(app: FastAPI) -> TestClient:
    """Create test client without auth override."""
    return TestClient(app)


class TestAdminRefreshRequiresServiceToken:
    """Test that admin endpoint requires S2S JWT authentication."""

    def test_admin_refresh_rejects_missing_auth(
        self,
        unauthed_client: TestClient,
    ) -> None:
        """Returns 401 when no Authorization header present."""
        response = unauthed_client.post(
            "/v1/admin/cache/refresh",
            json={},
        )

        assert response.status_code == 401

    def test_admin_refresh_rejects_pat_token(
        self,
        unauthed_client: TestClient,
    ) -> None:
        """Returns 401 for PAT tokens (non-JWT)."""
        response = unauthed_client.post(
            "/v1/admin/cache/refresh",
            json={},
            headers={"Authorization": "Bearer 0/1234567890abcdef"},
        )

        assert response.status_code == 401


class TestAdminRefreshValidatesEntityType:
    """Test entity type validation."""

    def test_admin_refresh_rejects_invalid_entity_type(
        self,
        client: TestClient,
    ) -> None:
        """Returns 400 for invalid entity type."""
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            ) as mock_registry_cls,
        ):
            mock_registry = MagicMock()
            mock_registry.is_ready.return_value = True
            mock_registry_cls.return_value = mock_registry

            response = client.post(
                "/v1/admin/cache/refresh",
                json={"entity_type": "invalid_type"},
            )

        assert response.status_code == 400
        body = response.json()
        assert body["detail"]["error"] == "INVALID_ENTITY_TYPE"

    def test_admin_refresh_accepts_all_valid_entity_types(
        self,
        client: TestClient,
    ) -> None:
        """All valid entity types are accepted."""
        for entity_type in VALID_ENTITY_TYPES:
            with (
                patch(
                    "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                    return_value=MagicMock(),
                ),
                patch(
                    "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                ) as mock_registry_cls,
            ):
                mock_registry = MagicMock()
                mock_registry.is_ready.return_value = True
                mock_registry_cls.return_value = mock_registry

                response = client.post(
                    "/v1/admin/cache/refresh",
                    json={"entity_type": entity_type},
                )

            assert response.status_code == 202, (
                f"Expected 202 for entity_type={entity_type}, "
                f"got {response.status_code}"
            )


class TestAdminRefreshAcceptsValidRequest:
    """Test valid request handling."""

    def test_admin_refresh_returns_202_with_single_entity(
        self,
        client: TestClient,
    ) -> None:
        """Valid request returns 202 Accepted with correct body."""
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            ) as mock_registry_cls,
        ):
            mock_registry = MagicMock()
            mock_registry.is_ready.return_value = True
            mock_registry_cls.return_value = mock_registry

            response = client.post(
                "/v1/admin/cache/refresh",
                json={"entity_type": "offer"},
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["entity_types"] == ["offer"]
        assert body["force_full_rebuild"] is False
        assert "refresh_id" in body
        assert "offer" in body["message"]

    def test_admin_refresh_with_force_full_rebuild(
        self,
        client: TestClient,
    ) -> None:
        """Force full rebuild flag is passed through."""
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            ) as mock_registry_cls,
        ):
            mock_registry = MagicMock()
            mock_registry.is_ready.return_value = True
            mock_registry_cls.return_value = mock_registry

            response = client.post(
                "/v1/admin/cache/refresh",
                json={
                    "entity_type": "offer",
                    "force_full_rebuild": True,
                },
            )

        assert response.status_code == 202
        body = response.json()
        assert body["force_full_rebuild"] is True
        assert "force full rebuild" in body["message"]


class TestAdminRefreshAllTypes:
    """Test null entity_type triggers all types."""

    def test_admin_refresh_all_types(
        self,
        client: TestClient,
    ) -> None:
        """Null entity_type triggers refresh for all valid types."""
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            ) as mock_registry_cls,
        ):
            mock_registry = MagicMock()
            mock_registry.is_ready.return_value = True
            mock_registry_cls.return_value = mock_registry

            response = client.post(
                "/v1/admin/cache/refresh",
                json={},
            )

        assert response.status_code == 202
        body = response.json()
        assert set(body["entity_types"]) == VALID_ENTITY_TYPES


class TestAdminRefreshServiceAvailability:
    """Test service availability checks."""

    def test_admin_refresh_503_when_cache_not_initialized(
        self,
        client: TestClient,
    ) -> None:
        """Returns 503 when DataFrameCache is not initialized."""
        with patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=None,
        ):
            response = client.post(
                "/v1/admin/cache/refresh",
                json={"entity_type": "offer"},
            )

        assert response.status_code == 503
        body = response.json()
        assert body["detail"]["error"] == "CACHE_NOT_INITIALIZED"

    def test_admin_refresh_503_when_registry_not_ready(
        self,
        client: TestClient,
    ) -> None:
        """Returns 503 when EntityProjectRegistry is not ready."""
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            ) as mock_registry_cls,
        ):
            mock_registry = MagicMock()
            mock_registry.is_ready.return_value = False
            mock_registry_cls.return_value = mock_registry

            response = client.post(
                "/v1/admin/cache/refresh",
                json={"entity_type": "offer"},
            )

        assert response.status_code == 503
        body = response.json()
        assert body["detail"]["error"] == "REGISTRY_NOT_READY"


class TestCacheRefreshModels:
    """Test Pydantic models."""

    def test_request_defaults(self) -> None:
        """Request model has correct defaults."""
        req = CacheRefreshRequest()
        assert req.entity_type is None
        assert req.force_full_rebuild is False

    def test_request_with_values(self) -> None:
        """Request model accepts values."""
        req = CacheRefreshRequest(entity_type="offer", force_full_rebuild=True)
        assert req.entity_type == "offer"
        assert req.force_full_rebuild is True

    def test_response_model(self) -> None:
        """Response model serializes correctly."""
        resp = CacheRefreshResponse(
            status="accepted",
            message="Cache refresh initiated",
            entity_types=["offer"],
            refresh_id="test-uuid",
            force_full_rebuild=False,
        )
        assert resp.status == "accepted"
        assert resp.entity_types == ["offer"]
        assert resp.refresh_id == "test-uuid"
