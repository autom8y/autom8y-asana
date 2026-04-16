"""Unit tests for admin cache refresh endpoint.

Per TDD-cache-freshness-remediation Fix 4: Tests for POST /v1/admin/cache/refresh.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.routes.admin import (
    SUPER_ADMIN_PERMISSION,
    VALID_ENTITY_TYPES,
    CacheRefreshRequest,
    CacheRefreshResponse,
    refresh_cache,
    router,
)
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.auth.dual_mode import AuthMode


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with admin router."""
    from autom8_asana.api.errors import register_exception_handlers

    test_app = FastAPI()
    test_app.include_router(router)

    @test_app.middleware("http")
    async def add_request_id(request, call_next):
        request.state.request_id = "test-request-id"
        return await call_next(request)

    register_exception_handlers(test_app)
    return test_app


@pytest.fixture
def mock_service_claims() -> ServiceClaims:
    """Create mock service claims for S2S auth (super-admin SA).

    Carries the canonical ``admin:access`` permission so the W4C-P3
    super-admin gate on /v1/admin/cache/refresh permits the call. Tests
    that need a non-super-admin caller use ``mock_non_super_admin_claims``.
    """
    return ServiceClaims(
        sub="service-123",
        service_name="test-service",
        scope="multi-tenant",
        permissions=[SUPER_ADMIN_PERMISSION],
    )


@pytest.fixture
def mock_non_super_admin_claims() -> ServiceClaims:
    """Create mock service claims WITHOUT the super-admin permission."""
    return ServiceClaims(
        sub="service-456",
        service_name="non-admin-service",
        scope="multi-tenant",
        permissions=["data:read", "tasks:write"],
    )


@pytest.fixture
def authed_app(app: FastAPI, mock_service_claims: ServiceClaims) -> FastAPI:
    """Create app with mocked S2S authentication."""

    async def override_require_service_claims() -> ServiceClaims:
        return mock_service_claims

    async def override_get_auth_context() -> AuthContext:
        return AuthContext(
            mode=AuthMode.JWT,
            asana_pat="test_bot_pat",
            caller_service="test-service",
        )

    app.dependency_overrides[require_service_claims] = override_require_service_claims
    app.dependency_overrides[get_auth_context] = override_get_auth_context
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
        assert body["error"]["code"] == "INVALID_ENTITY_TYPE"

    @pytest.mark.slow
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
                f"Expected 202 for entity_type={entity_type}, got {response.status_code}"
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

    @pytest.mark.slow
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
        assert body["error"]["code"] == "CACHE_NOT_INITIALIZED"

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
        assert body["error"]["code"] == "REGISTRY_NOT_READY"


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


class TestAdminRefreshSuperAdminGate:
    """Bedrock W4C-P3 / SEC-DT-10 / D-017.

    The fleet-wide cache-purge endpoint must be reachable only by
    ServiceAccounts provisioned with the canonical ``admin:access``
    permission. Any other authenticated S2S caller must be rejected
    with 403 INSUFFICIENT_PRIVILEGE.

    These tests prove BOTH paths so the regression cannot recur:
      1. super-admin SA -> 202 (proceeds normally)
      2. non-super-admin SA -> 403 (rejected before any side effects)
    """

    def test_admin_cache_refresh_super_admin_proceeds(
        self,
        app: FastAPI,
        mock_service_claims: ServiceClaims,
    ) -> None:
        """Super-admin SA (carrying ``admin:access``) is allowed through."""

        async def override_require_service_claims() -> ServiceClaims:
            return mock_service_claims

        async def override_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service=mock_service_claims.service_name,
            )

        app.dependency_overrides[require_service_claims] = override_require_service_claims
        app.dependency_overrides[get_auth_context] = override_get_auth_context

        # Sanity-check the fixture actually carries the gating permission
        assert SUPER_ADMIN_PERMISSION in mock_service_claims.permissions

        client = TestClient(app)
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

        assert response.status_code == 202, response.text
        body = response.json()
        assert body["status"] == "accepted"
        assert body["entity_types"] == ["offer"]

    def test_admin_cache_refresh_non_super_admin_rejected(
        self,
        app: FastAPI,
        mock_non_super_admin_claims: ServiceClaims,
    ) -> None:
        """Non-super-admin SA is rejected with 403 INSUFFICIENT_PRIVILEGE.

        Crucially, the rejection must happen before any cache or
        registry side effects — we patch them to raise so any leakage
        through the gate would also surface as a test failure.
        """

        async def override_require_service_claims() -> ServiceClaims:
            return mock_non_super_admin_claims

        async def override_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service=mock_non_super_admin_claims.service_name,
            )

        app.dependency_overrides[require_service_claims] = override_require_service_claims
        app.dependency_overrides[get_auth_context] = override_get_auth_context

        # Sanity-check the fixture lacks the gating permission
        assert SUPER_ADMIN_PERMISSION not in mock_non_super_admin_claims.permissions

        client = TestClient(app)
        # Patch the side-effect collaborators to raise — if the gate
        # leaks the call would attempt these and surface a different
        # error than the expected 403 INSUFFICIENT_PRIVILEGE.
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                side_effect=AssertionError(
                    "cache lookup must not run for non-super-admin caller",
                ),
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                side_effect=AssertionError(
                    "registry lookup must not run for non-super-admin caller",
                ),
            ),
        ):
            response = client.post(
                "/v1/admin/cache/refresh",
                json={"entity_type": "offer"},
            )

        assert response.status_code == 403, response.text
        body = response.json()
        assert body["error"]["code"] == "INSUFFICIENT_PRIVILEGE"
        assert SUPER_ADMIN_PERMISSION in body["error"]["message"]

    def test_admin_cache_refresh_empty_permissions_rejected(
        self,
        app: FastAPI,
    ) -> None:
        """ServiceJWT with NO permissions list is rejected (defense in depth)."""
        empty_claims = ServiceClaims(
            sub="service-empty",
            service_name="empty-perms-service",
            scope=None,
            permissions=[],
        )

        async def override_require_service_claims() -> ServiceClaims:
            return empty_claims

        async def override_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service=empty_claims.service_name,
            )

        app.dependency_overrides[require_service_claims] = override_require_service_claims
        app.dependency_overrides[get_auth_context] = override_get_auth_context

        client = TestClient(app)
        response = client.post(
            "/v1/admin/cache/refresh",
            json={},
        )

        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "INSUFFICIENT_PRIVILEGE"


class TestAdminRefreshSuperAdminGuard:
    """Static guard ensuring the super-admin gate is wired into the route.

    A regression that drops the permission check would still pass the
    behavioural tests above only if the dependency overrides hide the
    bug — this guard inspects the source of the route handler and the
    module-level constant so any silent removal trips the test suite.
    """

    def test_super_admin_permission_constant_is_canonical(self) -> None:
        """Permission string must match the autom8y-auth canonical convention."""
        assert SUPER_ADMIN_PERMISSION == "admin:access"

    def test_route_handler_references_super_admin_permission(self) -> None:
        """The route handler source must reference the gating constant."""
        import inspect

        source = inspect.getsource(refresh_cache)
        assert "SUPER_ADMIN_PERMISSION" in source, (
            "refresh_cache must enforce SUPER_ADMIN_PERMISSION; "
            "regression of Bedrock W4C-P3 / SEC-DT-10."
        )
        assert "INSUFFICIENT_PRIVILEGE" in source, (
            "refresh_cache must surface INSUFFICIENT_PRIVILEGE on non-super-admin callers."
        )
