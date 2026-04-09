"""Tests for SectionService -- section CRUD with mock dependencies.

Verifies:
- All CRUD operations call correct SDK methods
- MutationEvent construction for each operation type
- fire_and_forget called with correct event parameters
- InvalidParameterError for reorder validation failures
- No HTTP fixtures needed (pure unit tests with mocks)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationType,
)
from autom8_asana.services.errors import InvalidParameterError
from autom8_asana.services.section_service import SectionService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_invalidator() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client.sections = AsyncMock()
    return client


@pytest.fixture()
def service(mock_invalidator: MagicMock) -> SectionService:
    return SectionService(invalidator=mock_invalidator)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _last_event(mock_invalidator: MagicMock):
    """Get the last MutationEvent passed to fire_and_forget."""
    mock_invalidator.fire_and_forget.assert_called()
    return mock_invalidator.fire_and_forget.call_args[0][0]


# ---------------------------------------------------------------------------
# Tests: get_section  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestGetSection:
    @pytest.mark.asyncio()
    async def test_get_section(
        self, service: SectionService, mock_client: AsyncMock
    ) -> None:
        mock_client.sections.get_async.return_value = {
            "gid": "sec-1",
            "name": "To Do",
        }

        result = await service.get_section(mock_client, "sec-1")

        assert result["gid"] == "sec-1"
        mock_client.sections.get_async.assert_called_once_with("sec-1", raw=True)


# ---------------------------------------------------------------------------
# Tests: create_section (S1)  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestCreateSection:
    @pytest.mark.asyncio()
    async def test_create_fires_invalidation(
        self,
        service: SectionService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.sections.create_async.return_value = {
            "gid": "sec-new",
            "name": "New Section",
        }

        result = await service.create_section(
            mock_client, name="New Section", project="proj-1"
        )

        assert result["gid"] == "sec-new"
        event = _last_event(mock_invalidator)
        assert event.entity_kind == EntityKind.SECTION
        assert event.entity_gid == "sec-new"
        assert event.mutation_type == MutationType.CREATE
        assert event.project_gids == ["proj-1"]

    @pytest.mark.asyncio()
    async def test_create_passes_params(
        self,
        service: SectionService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.sections.create_async.return_value = {"gid": "x"}

        await service.create_section(mock_client, name="Test", project="proj-2")

        mock_client.sections.create_async.assert_called_once_with(
            name="Test", project="proj-2", raw=True
        )


# ---------------------------------------------------------------------------
# Tests: update_section (S2)  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestUpdateSection:
    @pytest.mark.asyncio()
    async def test_update_fires_invalidation(
        self,
        service: SectionService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        mock_client.sections.update_async.return_value = {
            "gid": "sec-1",
            "name": "Renamed",
            "project": {"gid": "proj-1"},
        }

        result = await service.update_section(mock_client, "sec-1", name="Renamed")

        assert result["name"] == "Renamed"
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.UPDATE
        assert event.entity_gid == "sec-1"
        assert event.project_gids == ["proj-1"]

    @pytest.mark.asyncio()
    async def test_update_no_project_in_response(
        self,
        service: SectionService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        """When response has no project, project_gids should be empty."""
        mock_client.sections.update_async.return_value = {
            "gid": "sec-1",
            "name": "Renamed",
        }

        await service.update_section(mock_client, "sec-1", name="Renamed")

        event = _last_event(mock_invalidator)
        assert event.project_gids == []


# ---------------------------------------------------------------------------
# Tests: delete_section (S3)  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestDeleteSection:
    @pytest.mark.asyncio()
    async def test_delete_fires_invalidation(
        self,
        service: SectionService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        await service.delete_section(mock_client, "sec-1")

        mock_client.sections.delete_async.assert_called_once_with("sec-1")
        event = _last_event(mock_invalidator)
        assert event.mutation_type == MutationType.DELETE
        assert event.entity_gid == "sec-1"
        assert event.project_gids == []


# ---------------------------------------------------------------------------
# Tests: add_task (S4)  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestAddTask:
    @pytest.mark.asyncio()
    async def test_add_task_fires_invalidation(
        self,
        service: SectionService,
        mock_client: AsyncMock,
        mock_invalidator: MagicMock,
    ) -> None:
        await service.add_task(mock_client, "sec-1", "task-1")

        mock_client.sections.add_task_async.assert_called_once_with(
            "sec-1", task="task-1"
        )
        event = _last_event(mock_invalidator)
        assert event.entity_kind == EntityKind.SECTION
        assert event.entity_gid == "sec-1"
        assert event.mutation_type == MutationType.ADD_MEMBER
        assert event.section_gid == "task-1"  # task_gid carried in section_gid


# ---------------------------------------------------------------------------
# Tests: reorder  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestReorder:
    @pytest.mark.asyncio()
    async def test_reorder_before(
        self, service: SectionService, mock_client: AsyncMock
    ) -> None:
        await service.reorder(mock_client, "sec-1", "proj-1", before_section="sec-2")

        mock_client.sections.insert_section_async.assert_called_once_with(
            "proj-1",
            section="sec-1",
            before_section="sec-2",
            after_section=None,
        )

    @pytest.mark.asyncio()
    async def test_reorder_after(
        self, service: SectionService, mock_client: AsyncMock
    ) -> None:
        await service.reorder(mock_client, "sec-1", "proj-1", after_section="sec-0")

        mock_client.sections.insert_section_async.assert_called_once_with(
            "proj-1",
            section="sec-1",
            before_section=None,
            after_section="sec-0",
        )

    @pytest.mark.asyncio()
    async def test_reorder_neither_raises(
        self, service: SectionService, mock_client: AsyncMock
    ) -> None:
        with pytest.raises(
            InvalidParameterError, match="before_section.*after_section"
        ):
            await service.reorder(mock_client, "sec-1", "proj-1")

    @pytest.mark.asyncio()
    async def test_reorder_both_raises(
        self, service: SectionService, mock_client: AsyncMock
    ) -> None:
        with pytest.raises(InvalidParameterError, match="Only one"):
            await service.reorder(
                mock_client,
                "sec-1",
                "proj-1",
                before_section="a",
                after_section="b",
            )


# ---------------------------------------------------------------------------
# Tests: extract_section_project_gids  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestExtractProjectGids:
    def test_with_project_dict(self) -> None:
        result = SectionService._extract_section_project_gids(
            {"project": {"gid": "proj-1"}}
        )
        assert result == ["proj-1"]

    def test_without_project(self) -> None:
        result = SectionService._extract_section_project_gids({"name": "Test"})
        assert result == []

    def test_non_dict_input(self) -> None:
        result = SectionService._extract_section_project_gids("not a dict")
        assert result == []

    def test_project_without_gid(self) -> None:
        result = SectionService._extract_section_project_gids(
            {"project": {"name": "Test"}}
        )
        assert result == []


# ---------------------------------------------------------------------------
# Tests: No HTTP coupling
# ---------------------------------------------------------------------------


class TestNoHTTPCoupling:
    def test_no_http_exception_in_module(self) -> None:
        import autom8_asana.services.section_service as mod

        source = mod.__file__
        assert source is not None
        with open(source) as f:
            content = f.read()
        assert "HTTPException" not in content
