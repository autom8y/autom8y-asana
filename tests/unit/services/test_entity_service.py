"""Tests for EntityService -- entity resolution and validation.

Verifies:
- EntityContext creation with valid entity types
- UnknownEntityError for unknown types
- ServiceNotConfiguredError for missing project or bot PAT
- get_queryable_entities() delegates correctly
- No HTTP fixtures needed (pure unit tests)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.core.entity_registry import EntityDescriptor, EntityRegistry
from autom8_asana.services.entity_context import EntityContext
from autom8_asana.services.entity_service import EntityService
from autom8_asana.services.errors import (
    ServiceNotConfiguredError,
    UnknownEntityError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_descriptor(name: str, project_gid: str | None = "proj-1") -> EntityDescriptor:
    """Create a minimal EntityDescriptor for testing."""
    return EntityDescriptor(
        name=name,
        pascal_name=name.capitalize(),
        display_name=name.capitalize(),
        primary_project_gid=project_gid,
        warmable=project_gid is not None,
    )


def _make_registry(*names: str) -> EntityRegistry:
    """Create an EntityRegistry with the given entity names."""
    descriptors = tuple(_make_descriptor(n, f"proj-{n}") for n in names)
    return EntityRegistry(descriptors)


def _make_project_registry(mappings: dict[str, str]) -> MagicMock:
    """Create a mock EntityProjectRegistry with given mappings."""
    mock = MagicMock()
    mock.get_project_gid.side_effect = lambda et: mappings.get(et)
    mock.is_ready.return_value = True
    mock.get_all_entity_types.return_value = list(mappings.keys())
    return mock


@pytest.fixture()
def entity_registry() -> EntityRegistry:
    return _make_registry("unit", "offer", "business")


@pytest.fixture()
def project_registry() -> MagicMock:
    return _make_project_registry(
        {
            "unit": "proj-unit",
            "offer": "proj-offer",
            "business": "proj-business",
        }
    )


@pytest.fixture()
def service(
    entity_registry: EntityRegistry, project_registry: MagicMock
) -> EntityService:
    return EntityService(
        entity_registry=entity_registry,
        project_registry=project_registry,
    )


# ---------------------------------------------------------------------------
# Tests: validate_entity_type
# ---------------------------------------------------------------------------


class TestValidateEntityType:
    """Tests for EntityService.validate_entity_type()."""

    @patch("autom8_asana.services.entity_service.EntityService.get_queryable_entities")
    @patch("autom8_asana.services.entity_service.EntityService._acquire_bot_pat")
    def test_valid_entity_returns_context(
        self,
        mock_bot_pat: MagicMock,
        mock_queryable: MagicMock,
        service: EntityService,
    ) -> None:
        mock_queryable.return_value = {"unit", "offer", "business"}
        mock_bot_pat.return_value = "bot-pat-123"

        ctx = service.validate_entity_type("unit")

        assert isinstance(ctx, EntityContext)
        assert ctx.entity_type == "unit"
        assert ctx.project_gid == "proj-unit"
        assert ctx.bot_pat == "bot-pat-123"
        assert ctx.descriptor.name == "unit"

    @patch("autom8_asana.services.entity_service.EntityService.get_queryable_entities")
    def test_unknown_entity_raises(
        self,
        mock_queryable: MagicMock,
        service: EntityService,
    ) -> None:
        mock_queryable.return_value = {"unit", "offer"}

        with pytest.raises(UnknownEntityError) as exc_info:
            service.validate_entity_type("widget")

        assert exc_info.value.entity_type == "widget"
        assert "offer" in exc_info.value.available
        assert "unit" in exc_info.value.available

    @patch("autom8_asana.services.entity_service.EntityService.get_queryable_entities")
    @patch("autom8_asana.services.entity_service.EntityService._acquire_bot_pat")
    def test_missing_project_gid_raises(
        self,
        mock_bot_pat: MagicMock,
        mock_queryable: MagicMock,
        entity_registry: EntityRegistry,
    ) -> None:
        """When project registry returns None, ServiceNotConfiguredError."""
        project_registry = _make_project_registry({"unit": None})  # type: ignore[dict-item]
        svc = EntityService(
            entity_registry=entity_registry,
            project_registry=project_registry,
        )
        mock_queryable.return_value = {"unit"}

        with pytest.raises(ServiceNotConfiguredError) as exc_info:
            svc.validate_entity_type("unit")

        assert "No project configured" in str(exc_info.value)

    @patch("autom8_asana.services.entity_service.EntityService.get_queryable_entities")
    def test_missing_bot_pat_raises(
        self,
        mock_queryable: MagicMock,
        service: EntityService,
    ) -> None:
        mock_queryable.return_value = {"unit"}

        with patch(
            "autom8_asana.services.entity_service.EntityService._acquire_bot_pat",
            side_effect=ServiceNotConfiguredError("Bot PAT not configured: missing"),
        ):
            with pytest.raises(ServiceNotConfiguredError) as exc_info:
                service.validate_entity_type("unit")

        assert "Bot PAT" in str(exc_info.value)

    @patch("autom8_asana.services.entity_service.EntityService.get_queryable_entities")
    @patch("autom8_asana.services.entity_service.EntityService._acquire_bot_pat")
    def test_context_is_frozen(
        self,
        mock_bot_pat: MagicMock,
        mock_queryable: MagicMock,
        service: EntityService,
    ) -> None:
        mock_queryable.return_value = {"unit"}
        mock_bot_pat.return_value = "pat"

        ctx = service.validate_entity_type("unit")

        with pytest.raises(AttributeError):
            ctx.entity_type = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: EntityContext
# ---------------------------------------------------------------------------


class TestEntityContext:
    """Tests for EntityContext dataclass."""

    def test_frozen(self) -> None:
        desc = _make_descriptor("unit")
        ctx = EntityContext(
            entity_type="unit",
            project_gid="proj-1",
            descriptor=desc,
            bot_pat="pat",
        )
        with pytest.raises(AttributeError):
            ctx.entity_type = "other"  # type: ignore[misc]

    def test_slots(self) -> None:
        desc = _make_descriptor("unit")
        ctx = EntityContext(
            entity_type="unit",
            project_gid="proj-1",
            descriptor=desc,
            bot_pat="pat",
        )
        assert not hasattr(ctx, "__dict__")

    def test_all_fields_accessible(self) -> None:
        desc = _make_descriptor("unit")
        ctx = EntityContext(
            entity_type="unit",
            project_gid="proj-1",
            descriptor=desc,
            bot_pat="secret",
        )
        assert ctx.entity_type == "unit"
        assert ctx.project_gid == "proj-1"
        assert ctx.descriptor is desc
        assert ctx.bot_pat == "secret"


# ---------------------------------------------------------------------------
# Tests: Service does not use HTTPException
# ---------------------------------------------------------------------------


class TestNoHTTPDependency:
    """Ensure service layer has no HTTP framework coupling."""

    def test_entity_service_no_http_exception(self) -> None:
        import autom8_asana.services.entity_service as mod

        source = mod.__file__
        assert source is not None
        with open(source) as f:
            content = f.read()
        assert "HTTPException" not in content

    def test_entity_context_no_http_exception(self) -> None:
        import autom8_asana.services.entity_context as mod

        source = mod.__file__
        assert source is not None
        with open(source) as f:
            content = f.read()
        assert "HTTPException" not in content
