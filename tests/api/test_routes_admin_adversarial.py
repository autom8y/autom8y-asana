"""Adversarial edge case tests for admin cache refresh endpoint.

Per QA Adversary validation of TDD-cache-freshness-remediation Fix 4:
Tests boundary conditions, malicious inputs, and error paths that
the implementation tests may have missed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.routes.admin import (
    VALID_ENTITY_TYPES,
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
    return ServiceClaims(
        sub="service-123",
        service_name="test-service",
        scope="multi-tenant",
    )


@pytest.fixture
def authed_app(app: FastAPI, mock_service_claims: ServiceClaims) -> FastAPI:
    async def override_require_service_claims() -> ServiceClaims:
        return mock_service_claims

    app.dependency_overrides[require_service_claims] = override_require_service_claims
    return app


@pytest.fixture
def client(authed_app: FastAPI) -> TestClient:
    return TestClient(authed_app)


class TestAdminRefreshAdversarialInputs:
    """Adversarial input tests for admin cache refresh endpoint."""

    def test_empty_string_entity_type_rejected(self, client: TestClient) -> None:
        """Empty string entity_type should be rejected as invalid."""
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
                json={"entity_type": ""},
            )

        assert response.status_code == 400
        body = response.json()
        assert body["detail"]["error"] == "INVALID_ENTITY_TYPE"

    def test_sql_injection_entity_type_rejected(self, client: TestClient) -> None:
        """SQL injection in entity_type should be rejected."""
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
                json={"entity_type": "' OR '1'='1"},
            )

        assert response.status_code == 400

    def test_path_traversal_entity_type_rejected(self, client: TestClient) -> None:
        """Path traversal in entity_type should be rejected."""
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
                json={"entity_type": "../../../etc/passwd"},
            )

        assert response.status_code == 400

    def test_extremely_long_entity_type_rejected(self, client: TestClient) -> None:
        """Extremely long entity_type should be rejected (not in valid set)."""
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
                json={"entity_type": "a" * 10000},
            )

        assert response.status_code == 400

    def test_null_byte_entity_type_rejected(self, client: TestClient) -> None:
        """Null byte in entity_type should be rejected."""
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
                json={"entity_type": "offer\x00malicious"},
            )

        assert response.status_code == 400

    def test_extra_unknown_fields_ignored(self, client: TestClient) -> None:
        """Extra fields in request body should be ignored (Pydantic default)."""
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
                    "evil_field": "malicious_payload",
                    "__proto__": {"polluted": True},
                },
            )

        # Should succeed (extra fields ignored by Pydantic)
        assert response.status_code == 202

    def test_invalid_json_body_returns_422(self, client: TestClient) -> None:
        """Non-JSON body should return 422 Unprocessable Entity."""
        response = client.post(
            "/v1/admin/cache/refresh",
            content="not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @pytest.mark.slow
    def test_force_full_rebuild_non_boolean_coerced(self, client: TestClient) -> None:
        """Non-boolean force_full_rebuild should be coerced by Pydantic."""
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

            # Pydantic coerces "true" string to True for bool fields
            response = client.post(
                "/v1/admin/cache/refresh",
                json={"entity_type": "offer", "force_full_rebuild": 1},
            )

        # Pydantic coerces 1 to True
        assert response.status_code == 202
        body = response.json()
        assert body["force_full_rebuild"] is True


class TestAdminRefreshConcurrency:
    """Test concurrent and repeated refresh requests."""

    @pytest.mark.slow
    def test_multiple_rapid_requests_all_accepted(self, client: TestClient) -> None:
        """Multiple rapid requests should all return 202 (each gets unique refresh_id)."""
        refresh_ids = set()

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

            for _ in range(5):
                response = client.post(
                    "/v1/admin/cache/refresh",
                    json={"entity_type": "offer"},
                )
                assert response.status_code == 202
                refresh_ids.add(response.json()["refresh_id"])

        # All refresh IDs should be unique
        assert len(refresh_ids) == 5


class TestAdminRefreshValidEntityTypes:
    """Verify VALID_ENTITY_TYPES matches expected set."""

    def test_valid_entity_types_set(self) -> None:
        """VALID_ENTITY_TYPES should contain the expected entity types."""
        expected = {"unit", "business", "offer", "contact", "asset_edit"}
        assert VALID_ENTITY_TYPES == expected

    def test_asset_edit_holder_not_in_valid_types(self) -> None:
        """asset_edit_holder is NOT in VALID_ENTITY_TYPES (not directly refreshable)."""
        assert "asset_edit_holder" not in VALID_ENTITY_TYPES

    def test_unit_holder_not_in_valid_types(self) -> None:
        """unit_holder is NOT in VALID_ENTITY_TYPES."""
        assert "unit_holder" not in VALID_ENTITY_TYPES
