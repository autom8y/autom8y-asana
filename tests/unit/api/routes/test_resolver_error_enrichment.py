"""Tests for Sprint 3 error enrichment changes in resolver routes.

Per ADR-error-taxonomy-resolution:
- FIND-001: to_pascal_case replaces .capitalize() for multi-word entity types
- FIND-004: Three-clause except chain at the resolver boundary

Test IDs:
- EE-001: Schema lookup succeeds for multi-word entity types (asset_edit)
- EE-002: Schema lookup succeeds for asset_edit_holder
- EE-003: ServiceError returns structured error via raise_service_error
- EE-004: AsanaError propagates to FastAPI global handlers
- EE-005: Unexpected Exception returns RESOLUTION_ERROR / 500
"""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.errors import RateLimitError
from autom8_asana.services.errors import CacheNotReadyError, ServiceError
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNIT_PROJECT_GID = "1201081073731555"
ASSET_EDIT_PROJECT_GID = "9900000000000001"
ASSET_EDIT_HOLDER_PROJECT_GID = "9900000000000002"
JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}


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


def _build_patches(
    resolve_side_effect: object = None,
    resolve_return: list[ResolutionResult] | None = None,
) -> tuple[object, ...]:
    """Build standard patch stack for resolver route tests.

    Args:
        resolve_side_effect: If set, strategy.resolve raises this.
        resolve_return: If set, strategy.resolve returns this list.

    Returns:
        Tuple of patch context managers.
    """
    mock_resolve = AsyncMock()
    if resolve_side_effect is not None:
        mock_resolve.side_effect = resolve_side_effect
    elif resolve_return is not None:
        mock_resolve.return_value = resolve_return
    else:
        mock_resolve.return_value = [ResolutionResult.from_gids(["gid-1"])]

    # Build a mock strategy that will be returned by get_strategy()
    mock_strategy = MagicMock()
    mock_strategy.resolve = mock_resolve
    mock_strategy.validate_criterion.return_value = []  # no validation errors

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
    client_patch = patch("autom8_asana.AsanaClient")
    # Patch get_strategy at the resolver module level (where it's imported)
    # to return our mock strategy for any entity type.
    strategy_patch = patch(
        "autom8_asana.api.routes.resolver.get_strategy",
        return_value=mock_strategy,
    )
    # Patch get_supported_entity_types to include all test entity types
    # (holder types like asset_edit_holder are not in the fallback set)
    supported_patch = patch(
        "autom8_asana.api.routes.resolver.get_supported_entity_types",
        return_value={
            "unit",
            "business",
            "offer",
            "contact",
            "asset_edit",
            "asset_edit_holder",
        },
    )
    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        strategy_patch,
        supported_patch,
    )


def _make_async_client_mock(mock_client_class: MagicMock) -> None:
    """Configure mock AsanaClient as an async context manager."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():  # type: ignore[misc]
    """Reset singletons before and after each test for isolation."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):  # type: ignore[misc]
    """Create a test application with mocked discovery and entity registry.

    Registers unit, asset_edit, and asset_edit_holder entity types.
    """
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app: MagicMock) -> None:
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid=UNIT_PROJECT_GID,
                project_name="Business Units",
            )
            registry.register(
                entity_type="asset_edit",
                project_gid=ASSET_EDIT_PROJECT_GID,
                project_name="Asset Edits",
            )
            registry.register(
                entity_type="asset_edit_holder",
                project_gid=ASSET_EDIT_HOLDER_PROJECT_GID,
                project_name="Asset Edit Holders",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app: MagicMock) -> TestClient:  # type: ignore[misc]
    """Synchronous test client with lifespan events handled."""
    with TestClient(app) as tc:
        yield tc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FIND-001: to_pascal_case schema lookup
# ---------------------------------------------------------------------------


class TestPascalCaseSchemaLookup:
    """EE-001/002: Verify to_pascal_case replaces .capitalize() for multi-word types."""

    @pytest.mark.parametrize(
        "entity_type,expected_schema_key",
        [
            ("asset_edit", "AssetEdit"),
            ("asset_edit_holder", "AssetEditHolder"),
        ],
        ids=["EE-001-asset_edit", "EE-002-asset_edit_holder"],
    )
    def test_schema_lookup_uses_pascal_case(
        self,
        client: TestClient,
        entity_type: str,
        expected_schema_key: str,
    ) -> None:
        """Schema lookup for multi-word entity types uses to_pascal_case.

        Verifies that SchemaRegistry.get_schema is called with the correct
        PascalCase key (e.g. "AssetEdit", not "Asset_edit").
        """
        patches = _build_patches()

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])  # client_patch

            # Mock SchemaRegistry to capture the schema key.
            # SchemaRegistry is imported locally inside resolve_entities(),
            # so patch it at the canonical source module.
            mock_schema = MagicMock()
            mock_schema.columns = [
                MagicMock(name="gid", source=None, dtype="Utf8", description=None),
                MagicMock(name="name", source=None, dtype="Utf8", description=None),
            ]
            mock_schema.version = "1.0"

            with patch(
                "autom8_asana.dataframes.models.registry.SchemaRegistry"
            ) as mock_registry_cls:
                mock_registry = MagicMock()
                mock_registry.get_schema.return_value = mock_schema
                mock_registry_cls.get_instance.return_value = mock_registry

                response = client.post(
                    f"/v1/resolve/{entity_type}",
                    headers=AUTH_HEADER,
                    json={
                        "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                    },
                )

            assert response.status_code == 200
            # Verify the schema was looked up with PascalCase key
            mock_registry.get_schema.assert_called_with(expected_schema_key)

    @pytest.mark.parametrize(
        "entity_type,expected_schema_key",
        [
            ("asset_edit", "AssetEdit"),
            ("asset_edit_holder", "AssetEditHolder"),
        ],
        ids=[
            "EE-001-schema-endpoint-asset_edit",
            "EE-002-schema-endpoint-asset_edit_holder",
        ],
    )
    def test_schema_endpoint_uses_pascal_case(
        self,
        client: TestClient,
        entity_type: str,
        expected_schema_key: str,
    ) -> None:
        """GET /{entity_type}/schema uses to_pascal_case for schema lookup.

        Tests the resolver_schema.py code path separately.
        """
        mock_schema = MagicMock()
        mock_schema.columns = [
            MagicMock(name="gid", source=None, dtype="Utf8", description="Task GID"),
        ]
        mock_schema.version = "2.0"

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
        # Patch get_supported_entity_types at the resolver module (source of
        # the lazy import in resolver_schema.py)
        supported_patch = patch(
            "autom8_asana.api.routes.resolver.get_supported_entity_types",
            return_value={
                "unit",
                "business",
                "offer",
                "contact",
                "asset_edit",
                "asset_edit_holder",
            },
        )

        with (
            jwt_patch,
            jwt_patch_canonical,
            pat_patch,
            pat_patch_deps,
            supported_patch,
            patch(
                "autom8_asana.dataframes.models.registry.SchemaRegistry"
            ) as mock_registry_cls,
        ):
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = mock_schema
            mock_registry_cls.get_instance.return_value = mock_registry

            response = client.get(
                f"/v1/resolve/{entity_type}/schema",
                headers=AUTH_HEADER,
            )

        assert response.status_code == 200
        mock_registry.get_schema.assert_called_with(expected_schema_key)


# ---------------------------------------------------------------------------
# FIND-004: Three-clause except chain
# ---------------------------------------------------------------------------


class TestExceptChain:
    """EE-003/004/005: Three-clause exception handling at resolver boundary."""

    def test_ee003_service_error_returns_structured_response(
        self, client: TestClient
    ) -> None:
        """ServiceError -> raise_service_error preserving error_code and status_hint.

        Per ADR-error-taxonomy-resolution Tier 1.
        """
        error = CacheNotReadyError("unit")
        patches = _build_patches(resolve_side_effect=error)

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
            )

        # CacheNotReadyError has status_hint=503, error_code="CACHE_NOT_WARMED"
        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "CACHE_NOT_WARMED"
        assert "request_id" in body["meta"]

    def test_ee003_service_error_generic_500(self, client: TestClient) -> None:
        """Base ServiceError -> 500 with SERVICE_ERROR code.

        Validates fallback for unmapped ServiceError subclasses.
        """
        error = ServiceError("something unexpected in service")
        patches = _build_patches(resolve_side_effect=error)

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
            )

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "SERVICE_ERROR"

    def test_ee004_asana_error_propagates_to_global_handler(
        self, client: TestClient
    ) -> None:
        """AsanaError -> re-raised, handled by FastAPI's global exception handlers.

        Per ADR-error-taxonomy-resolution Tier 2.
        RateLimitError should produce 429 via the registered rate_limit_error_handler.
        """
        error = RateLimitError("Rate limit exceeded")
        error.retry_after = 30
        patches = _build_patches(resolve_side_effect=error)

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
            )

        # RateLimitError -> 429 via global handler
        assert response.status_code == 429

    def test_ee005_unexpected_exception_returns_resolution_error(
        self, client: TestClient
    ) -> None:
        """Unexpected Exception -> RESOLUTION_ERROR / 500.

        Per ADR-error-taxonomy-resolution Tier 3.
        Backward-compatible fallback for truly unexpected failures.
        """
        error = RuntimeError("something completely unexpected")
        patches = _build_patches(resolve_side_effect=error)

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
            )

        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "RESOLUTION_ERROR"
        assert (
            body["error"]["message"]
            == "An unexpected error occurred during resolution."
        )
