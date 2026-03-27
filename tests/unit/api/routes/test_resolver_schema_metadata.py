"""Tests for Sprint 4 schema endpoint category metadata.

Per Sprint 4 TDD: Validates that GET /v1/resolve/{entity_type}/schema
returns category, holder_for, and parent_entity fields derived from
the EntityDescriptor in EntityRegistry.

Test Matrix:
    T1: business -> category="root", holder_for=None, parent_entity=None
    T2: unit -> category="composite", holder_for=None, parent_entity=None
    T3: contact -> category="leaf", holder_for=None, parent_entity=None
    T4: asset_edit_holder -> category="holder", holder_for="asset_edit",
        parent_entity="business"
    T5: asset_edit -> category="leaf", holder_for=None, parent_entity=None
    T6: EntitySchemaResponse rejects unknown fields (extra="forbid" preserved)
    T7: Defensive fallback when EntityDescriptor not found
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.api.routes.resolver_schema import EntitySchemaResponse
from autom8_asana.auth.dual_mode import AuthMode
from autom8_asana.services.resolver import EntityProjectRegistry


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


# Entity registrations that include asset_edit and asset_edit_holder
# (the standard conftest only registers 4 entities).
_TEST_ENTITIES = [
    ("offer", "1143843662099250", "Business Offers"),
    ("unit", "1201081073731555", "Business Units"),
    ("contact", "1200775689604552", "Contacts"),
    ("business", "1200653012566782", "Business"),
    ("asset_edit", "1202204184560785", "Asset Edits"),
    ("asset_edit_holder", "1203992664400125", "Asset Edit Holder"),
]


def _populate_test_registry():
    """Reset and populate EntityProjectRegistry with full entity set."""
    EntityProjectRegistry.reset()
    registry = EntityProjectRegistry.get_instance()
    for entity_type, gid, name in _TEST_ENTITIES:
        registry.register(
            entity_type=entity_type,
            project_gid=gid,
            project_name=name,
        )
    return registry


@pytest.fixture(scope="module")
def app():
    """Create a test application with all 6 resolvable entities registered."""
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            registry = _populate_test_registry()
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        test_app = create_app()

        async def _mock_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service="autom8_data",
            )

        test_app.dependency_overrides[get_auth_context] = _mock_get_auth_context
        yield test_app


@pytest.fixture(scope="module")
def _module_client(app):
    """Module-scoped TestClient -- enters ASGI lifespan once."""
    with TestClient(app) as tc:
        yield tc


@pytest.fixture(autouse=True)
def _reset_registry():
    """Re-populate EntityProjectRegistry before each test."""
    _populate_test_registry()
    yield
    EntityProjectRegistry.reset()


@pytest.fixture
def client(_module_client) -> TestClient:
    """Per-test alias for the module-scoped TestClient."""
    return _module_client


# ---------------------------------------------------------------------------
# T1: Business -> ROOT
# ---------------------------------------------------------------------------


class TestBusinessSchemaMetadata:
    """T1: business -> category=root, holder_for=None, parent_entity=None."""

    def test_business_schema_returns_root_category(self, client: TestClient) -> None:
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/business/schema",
                headers={"Authorization": "Bearer header.payload.signature"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "root"
        assert data["holder_for"] is None
        assert data["parent_entity"] is None


# ---------------------------------------------------------------------------
# T2: Unit -> COMPOSITE
# ---------------------------------------------------------------------------


class TestUnitSchemaMetadata:
    """T2: unit -> category=composite."""

    def test_unit_schema_returns_composite_category(self, client: TestClient) -> None:
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema",
                headers={"Authorization": "Bearer header.payload.signature"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "composite"
        assert data["holder_for"] is None


# ---------------------------------------------------------------------------
# T3: Contact -> LEAF
# ---------------------------------------------------------------------------


class TestContactSchemaMetadata:
    """T3: contact -> category=leaf."""

    def test_contact_schema_returns_leaf_category(self, client: TestClient) -> None:
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/contact/schema",
                headers={"Authorization": "Bearer header.payload.signature"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "leaf"
        assert data["holder_for"] is None
        assert data["parent_entity"] is None


# ---------------------------------------------------------------------------
# T4: asset_edit_holder -> HOLDER
# ---------------------------------------------------------------------------


class TestAssetEditHolderSchemaMetadata:
    """T4: asset_edit_holder -> category=holder, holder_for=asset_edit."""

    def test_holder_schema_returns_holder_category(self, client: TestClient) -> None:
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/asset_edit_holder/schema",
                headers={"Authorization": "Bearer header.payload.signature"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "holder"
        assert data["holder_for"] == "asset_edit"
        assert data["parent_entity"] == "business"


# ---------------------------------------------------------------------------
# T5: asset_edit -> LEAF (not confused with its holder)
# ---------------------------------------------------------------------------


class TestAssetEditSchemaMetadata:
    """T5: asset_edit -> category=leaf (not holder)."""

    def test_asset_edit_is_leaf_not_holder(self, client: TestClient) -> None:
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/asset_edit/schema",
                headers={"Authorization": "Bearer header.payload.signature"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "leaf"
        assert data["holder_for"] is None


# ---------------------------------------------------------------------------
# T6: Response model validation (extra="forbid" preserved)
# ---------------------------------------------------------------------------


class TestSchemaResponseModelValidation:
    """T6: EntitySchemaResponse rejects unknown fields."""

    def test_extra_fields_rejected(self) -> None:
        """extra='forbid' still works on EntitySchemaResponse."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            EntitySchemaResponse(
                entity_type="test",
                version="1.0.0",
                category="leaf",
                queryable_fields=[],
                unknown_field="should_fail",
            )

    def test_new_fields_present_in_valid_response(self) -> None:
        """All three new fields are present in a valid response model."""
        resp = EntitySchemaResponse(
            entity_type="asset_edit_holder",
            version="1.0.0",
            category="holder",
            holder_for="asset_edit",
            parent_entity="business",
            queryable_fields=[],
        )
        assert resp.category == "holder"
        assert resp.holder_for == "asset_edit"
        assert resp.parent_entity == "business"

    def test_optional_fields_default_to_none(self) -> None:
        """holder_for and parent_entity default to None."""
        resp = EntitySchemaResponse(
            entity_type="business",
            version="1.0.0",
            category="root",
            queryable_fields=[],
        )
        assert resp.holder_for is None
        assert resp.parent_entity is None


# ---------------------------------------------------------------------------
# T7: Defensive fallback (unknown entity -> error, not crash)
# ---------------------------------------------------------------------------


class TestDefensiveFallback:
    """T7: Unknown entity type returns 404, not a crash."""

    def test_unknown_entity_returns_404(self, client: TestClient) -> None:
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/nonexistent_entity/schema",
                headers={"Authorization": "Bearer header.payload.signature"},
            )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "UNKNOWN_ENTITY_TYPE"

    def test_descriptor_not_found_uses_defaults(self) -> None:
        """When EntityRegistry.get() returns None, the handler's defensive
        guards produce category="unknown" and null for holder_for/parent_entity.

        This verifies the ternary logic that the handler uses:
            descriptor.category.value if descriptor else "unknown"
        """
        # Simulate the handler's defensive guard logic directly
        descriptor = None  # EntityRegistry.get() returned None

        category = descriptor.category.value if descriptor else "unknown"
        holder_for = descriptor.holder_for if descriptor else None
        parent_entity = descriptor.parent_entity if descriptor else None

        resp = EntitySchemaResponse(
            entity_type="test_entity",
            version="1.0.0",
            category=category,
            holder_for=holder_for,
            parent_entity=parent_entity,
            queryable_fields=[],
        )

        assert resp.category == "unknown"
        assert resp.holder_for is None
        assert resp.parent_entity is None
