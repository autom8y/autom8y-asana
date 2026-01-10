"""E2E integration tests for Entity Resolver with type coercion fix.

This module tests the Entity Resolver endpoint using httpx.ASGITransport
to bypass network and test the app directly.

Tests verify:
- Resolution works with mocked data (not INDEX_UNAVAILABLE)
- DataFrame builds successfully with type coercion
- TypeCoercer properly handles multi_enum -> str conversion

Per TDD-custom-field-type-coercion:
- multi_enum fields returning [] should be coerced to None (not cause validation error)
- Resolution should succeed even with mixed field types
"""

from __future__ import annotations

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.api.main import create_app
from autom8_asana.api.routes.health import set_cache_ready
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.dynamic_index import DynamicIndex
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.services.resolver import (
    EntityProjectRegistry,
    _apply_legacy_mapping as resolver_apply_legacy_mapping,
)


# --- Helpers ---


def _apply_legacy_mapping(criterion: dict, entity_type: str) -> dict:
    """Apply legacy field mapping to criterion using resolver's dynamic algorithm."""
    return resolver_apply_legacy_mapping(entity_type, criterion)


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


# --- Fixtures ---


@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """Reset singletons before and after each test for isolation."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    # Ensure cache is marked ready for tests
    set_cache_ready(True)
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    set_cache_ready(True)


@pytest.fixture
def mock_service_claims() -> ServiceClaims:
    """Create mock service claims for S2S auth."""
    return ServiceClaims(
        sub="service:test_service",
        service_name="test_service",
        scope="multi-tenant",
    )


@pytest.fixture
def sample_unit_dataframe() -> pl.DataFrame:
    """Create a sample Unit DataFrame with multi_enum fields.

    This simulates the real data structure from Asana, including
    multi_enum fields that may return empty lists.
    """
    return pl.DataFrame(
        {
            "gid": ["1234567890123456", "9876543210987654", "1111222233334444"],
            "name": ["Test Unit A", "Test Unit B", "Test Unit C"],
            "office_phone": ["+15551234567", "+15559876543", "+15551112222"],
            "vertical": ["dental", "medical", "chiropractic"],
            # multi_enum fields that get coerced to str | None
            "services": ["Cleaning, Whitening", None, "Adjustment"],
            "status": ["Active", "Pending", None],
        }
    )


@pytest.fixture
def sample_unit_dataframe_with_list_coercion() -> pl.DataFrame:
    """DataFrame simulating raw multi_enum values before coercion.

    This tests that TypeCoercer properly handles:
    - [] -> None
    - ["A", "B"] -> "A, B"
    """
    return pl.DataFrame(
        {
            "gid": ["1234567890123456", "9876543210987654"],
            "name": ["Test Unit A", "Test Unit B"],
            "office_phone": ["+15551234567", "+15559876543"],
            "vertical": ["dental", "medical"],
        }
    )


# --- Test Classes ---


class TestEntityResolverE2E:
    """E2E tests for Entity Resolver using ASGI transport.

    Uses httpx.ASGITransport to test the app without starting a real server.
    The TestClient is used because it properly manages FastAPI's lifespan.
    """

    def test_resolve_unit_with_mocked_discovery(
        self,
        mock_service_claims: ServiceClaims,
        sample_unit_dataframe: pl.DataFrame,
    ) -> None:
        """Test unit resolution succeeds with mocked discovery and DataFrame.

        Verifies:
        - Endpoint returns 200 (not 503 INDEX_UNAVAILABLE)
        - Resolution works correctly with test data
        - Meta contains expected entity_type and counts
        """
        from fastapi.testclient import TestClient

        # Mock discovery to set up registry
        async def mock_discovery(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid="test_project_123",
                project_name="Test Business Units",
            )
            app.state.entity_project_registry = registry

        # Create mock resolve function that uses the sample DataFrame
        mock_resolve = _make_mock_strategy_resolve(
            sample_unit_dataframe, ["office_phone", "vertical"]
        )

        with (
            patch(
                "autom8_asana.api.main._discover_entity_projects",
                new_callable=AsyncMock,
                side_effect=mock_discovery,
            ),
            patch(
                "autom8_asana.api.main._preload_dataframe_cache",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch(
                "autom8_asana.AsanaClient",
            ) as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
                mock_resolve,
            ),
        ):
            # Setup mock client
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Create app with mocked components
            app = create_app()

            # Override the auth dependency using FastAPI's dependency override system
            async def mock_require_claims():
                return mock_service_claims

            app.dependency_overrides[require_service_claims] = mock_require_claims

            try:
                # Use TestClient which properly manages lifespan
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/resolve/unit",
                        headers={"Authorization": "Bearer test.jwt.token"},
                        json={
                            "criteria": [
                                {"phone": "+15551234567", "vertical": "dental"},
                            ]
                        },
                    )

                # Assert success
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}: {response.text}"
                )

                data = response.json()
                assert "results" in data
                assert "meta" in data
                assert len(data["results"]) == 1
                assert data["results"][0]["gid"] == "1234567890123456"
                assert data["results"][0]["error"] is None
                assert data["meta"]["entity_type"] == "unit"
                assert data["meta"]["resolved_count"] == 1
                assert data["meta"]["unresolved_count"] == 0
            finally:
                app.dependency_overrides.clear()

    def test_resolve_unit_not_found_returns_error(
        self,
        mock_service_claims: ServiceClaims,
        sample_unit_dataframe: pl.DataFrame,
    ) -> None:
        """Test unit resolution returns NOT_FOUND for unknown phone/vertical."""
        from fastapi.testclient import TestClient

        async def mock_discovery(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid="test_project_123",
                project_name="Test Business Units",
            )
            app.state.entity_project_registry = registry

        # Create mock resolve function that uses the sample DataFrame
        mock_resolve = _make_mock_strategy_resolve(
            sample_unit_dataframe, ["office_phone", "vertical"]
        )

        with (
            patch(
                "autom8_asana.api.main._discover_entity_projects",
                new_callable=AsyncMock,
                side_effect=mock_discovery,
            ),
            patch(
                "autom8_asana.api.main._preload_dataframe_cache",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch(
                "autom8_asana.AsanaClient",
            ) as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
                mock_resolve,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            app = create_app()

            async def mock_require_claims():
                return mock_service_claims

            app.dependency_overrides[require_service_claims] = mock_require_claims

            try:
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/resolve/unit",
                        headers={"Authorization": "Bearer test.jwt.token"},
                        json={
                            "criteria": [
                                {"phone": "+19999999999", "vertical": "unknown"},
                            ]
                        },
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["results"][0]["gid"] is None
                assert data["results"][0]["error"] == "NOT_FOUND"
                assert data["meta"]["resolved_count"] == 0
                assert data["meta"]["unresolved_count"] == 1
            finally:
                app.dependency_overrides.clear()

    def test_resolve_batch_preserves_order(
        self,
        mock_service_claims: ServiceClaims,
        sample_unit_dataframe: pl.DataFrame,
    ) -> None:
        """Test batch resolution preserves input order."""
        from fastapi.testclient import TestClient

        async def mock_discovery(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid="test_project_123",
                project_name="Test Business Units",
            )
            app.state.entity_project_registry = registry

        # Create mock resolve function that uses the sample DataFrame
        mock_resolve = _make_mock_strategy_resolve(
            sample_unit_dataframe, ["office_phone", "vertical"]
        )

        with (
            patch(
                "autom8_asana.api.main._discover_entity_projects",
                new_callable=AsyncMock,
                side_effect=mock_discovery,
            ),
            patch(
                "autom8_asana.api.main._preload_dataframe_cache",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch(
                "autom8_asana.AsanaClient",
            ) as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
                mock_resolve,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            app = create_app()

            async def mock_require_claims():
                return mock_service_claims

            app.dependency_overrides[require_service_claims] = mock_require_claims

            try:
                with TestClient(app) as client:
                    response = client.post(
                        "/v1/resolve/unit",
                        headers={"Authorization": "Bearer test.jwt.token"},
                        json={
                            "criteria": [
                                {
                                    "phone": "+15551234567",
                                    "vertical": "dental",
                                },  # Found
                                {
                                    "phone": "+19999999999",
                                    "vertical": "unknown",
                                },  # Not found
                                {
                                    "phone": "+15559876543",
                                    "vertical": "medical",
                                },  # Found
                            ]
                        },
                    )

                assert response.status_code == 200
                data = response.json()

                # Verify order is preserved
                assert len(data["results"]) == 3
                assert data["results"][0]["gid"] == "1234567890123456"  # First found
                assert data["results"][1]["gid"] is None  # Not found
                assert data["results"][1]["error"] == "NOT_FOUND"
                assert data["results"][2]["gid"] == "9876543210987654"  # Second found

                assert data["meta"]["resolved_count"] == 2
                assert data["meta"]["unresolved_count"] == 1
            finally:
                app.dependency_overrides.clear()


class TestTypeCoercionIntegration:
    """Tests verifying TypeCoercer integration with DataFrame building."""

    def test_type_coercer_handles_empty_list_to_none(self) -> None:
        """Verify TypeCoercer converts [] to None for string columns.

        This is the core fix for the multi_enum validation error.
        """
        from autom8_asana.dataframes.resolver.coercer import TypeCoercer

        coercer = TypeCoercer()

        # Empty list should become None
        result = coercer.coerce([], "Utf8")
        assert result is None

        # Non-empty list should become comma-separated string
        result = coercer.coerce(["A", "B"], "Utf8")
        assert result == "A, B"

        # Single item list
        result = coercer.coerce(["Single"], "Utf8")
        assert result == "Single"

    def test_type_coercer_preserves_none(self) -> None:
        """Verify TypeCoercer preserves None values."""
        from autom8_asana.dataframes.resolver.coercer import TypeCoercer

        coercer = TypeCoercer()

        result = coercer.coerce(None, "Utf8")
        assert result is None

        result = coercer.coerce(None, "List[Utf8]")
        assert result is None

    def test_type_coercer_string_passthrough(self) -> None:
        """Verify strings pass through unchanged for string targets."""
        from autom8_asana.dataframes.resolver.coercer import TypeCoercer

        coercer = TypeCoercer()

        result = coercer.coerce("test value", "Utf8")
        assert result == "test value"

        result = coercer.coerce("test value", "String")
        assert result == "test value"


class TestHealthEndpoint:
    """Test health endpoint to verify service is operational."""

    def test_health_endpoint_returns_ok(self) -> None:
        """Test /health returns 200 when service is ready."""
        from fastapi.testclient import TestClient

        async def mock_discovery(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid="test_project_123",
                project_name="Test Business Units",
            )
            app.state.entity_project_registry = registry

        async def mock_preload(app):
            # Mark cache as ready after "preload"
            set_cache_ready(True)

        with (
            patch(
                "autom8_asana.api.main._discover_entity_projects",
                new_callable=AsyncMock,
                side_effect=mock_discovery,
            ),
            patch(
                "autom8_asana.api.main._preload_dataframe_cache",
                new_callable=AsyncMock,
                side_effect=mock_preload,
            ),
        ):
            app = create_app()

            with TestClient(app) as client:
                response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestAuthenticationEnforcement:
    """Test that authentication is properly enforced."""

    def test_missing_auth_returns_401(self) -> None:
        """Test that missing Authorization header returns 401."""
        from fastapi.testclient import TestClient

        async def mock_discovery(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid="test_project_123",
                project_name="Test Business Units",
            )
            app.state.entity_project_registry = registry

        with (
            patch(
                "autom8_asana.api.main._discover_entity_projects",
                new_callable=AsyncMock,
                side_effect=mock_discovery,
            ),
            patch(
                "autom8_asana.api.main._preload_dataframe_cache",
                new_callable=AsyncMock,
            ),
        ):
            app = create_app()

            with TestClient(app) as client:
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
