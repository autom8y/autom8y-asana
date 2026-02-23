"""Tests for section route handler cache invalidation wiring.

Per TDD-CACHE-INVALIDATION-001 Test Strategy: Verify that each wired
section endpoint calls fire_and_forget() with the correct MutationEvent
after successful mutation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator
from autom8_asana.cache.models.mutation_event import EntityKind, MutationType
from tests.unit.api.conftest import TEST_PROJECT_GID, TEST_SECTION_GID, TEST_TASK_GID

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

AUTH_HEADER = {"Authorization": "Bearer test_pat_token_12345"}


@pytest.fixture
def mock_invalidator() -> MagicMock:
    """Create a mock MutationInvalidator."""
    inv = MagicMock(spec=MutationInvalidator)
    inv.fire_and_forget = MagicMock()
    return inv


@pytest.fixture
def authed_client_with_invalidator(
    app, mock_asana_client: MagicMock, mock_invalidator: MagicMock
) -> Generator[tuple[TestClient, MagicMock, MagicMock], None, None]:
    """Test client with both AsanaClient and MutationInvalidator mocked."""
    from autom8_asana.api.dependencies import (
        get_asana_client_from_context,
        get_mutation_invalidator,
    )

    async def mock_get_client() -> AsyncGenerator[MagicMock, None]:
        yield mock_asana_client

    app.dependency_overrides[get_asana_client_from_context] = mock_get_client
    app.dependency_overrides[get_mutation_invalidator] = lambda: mock_invalidator

    try:
        with TestClient(app) as test_client:
            yield test_client, mock_asana_client, mock_invalidator
    finally:
        app.dependency_overrides.clear()


class TestCreateSectionInvalidation:
    """S1: POST /sections triggers CREATE invalidation."""

    def test_create_section_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Create section fires invalidation with project GID from request."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.sections.create_async.return_value = {
            "gid": "new_sect_1",
            "name": "New Section",
            "project": {"gid": TEST_PROJECT_GID, "name": "Project"},
        }

        response = client.post(
            "/api/v1/sections",
            json={"name": "New Section", "project": TEST_PROJECT_GID},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 201
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.SECTION
        assert event.entity_gid == "new_sect_1"
        assert event.mutation_type == MutationType.CREATE
        assert event.project_gids == [TEST_PROJECT_GID]


class TestUpdateSectionInvalidation:
    """S2: PUT /sections/{gid} triggers UPDATE invalidation."""

    def test_update_section_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Update section fires invalidation with project from response."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.sections.update_async.return_value = {
            "gid": TEST_SECTION_GID,
            "name": "Renamed Section",
            "project": {"gid": TEST_PROJECT_GID, "name": "Project"},
        }

        response = client.put(
            f"/api/v1/sections/{TEST_SECTION_GID}",
            json={"name": "Renamed Section"},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.SECTION
        assert event.entity_gid == TEST_SECTION_GID
        assert event.mutation_type == MutationType.UPDATE
        assert event.project_gids == [TEST_PROJECT_GID]

    def test_update_section_no_project_in_response(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Update section with no project in response sends empty project_gids."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.sections.update_async.return_value = {
            "gid": TEST_SECTION_GID,
            "name": "Renamed Section",
        }

        response = client.put(
            f"/api/v1/sections/{TEST_SECTION_GID}",
            json={"name": "Renamed Section"},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 200
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.project_gids == []


class TestDeleteSectionInvalidation:
    """S3: DELETE /sections/{gid} triggers DELETE invalidation."""

    def test_delete_section_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Delete section fires invalidation with no project GIDs (204)."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.sections.delete_async.return_value = None

        response = client.delete(
            f"/api/v1/sections/{TEST_SECTION_GID}",
            headers=AUTH_HEADER,
        )

        assert response.status_code == 204
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.SECTION
        assert event.entity_gid == TEST_SECTION_GID
        assert event.mutation_type == MutationType.DELETE
        assert event.project_gids == []


class TestAddTaskToSectionInvalidation:
    """S4: POST /sections/{gid}/tasks triggers ADD_MEMBER invalidation."""

    def test_add_task_to_section_fires_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Add task to section fires invalidation with task GID in section_gid."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.sections.add_task_async.return_value = None

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/tasks",
            json={"task_gid": TEST_TASK_GID},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 204
        mock_inv.fire_and_forget.assert_called_once()
        event = mock_inv.fire_and_forget.call_args[0][0]
        assert event.entity_kind == EntityKind.SECTION
        assert event.entity_gid == TEST_SECTION_GID
        assert event.mutation_type == MutationType.ADD_MEMBER
        assert event.section_gid == TEST_TASK_GID  # Task GID carried via section_gid


class TestReorderSectionNoInvalidation:
    """Reorder does not trigger invalidation (order not cached)."""

    def test_reorder_section_no_invalidation(
        self,
        authed_client_with_invalidator: tuple[TestClient, MagicMock, MagicMock],
    ) -> None:
        """Reorder section does not call fire_and_forget."""
        client, mock_sdk, mock_inv = authed_client_with_invalidator

        mock_sdk.sections.insert_section_async.return_value = None

        response = client.post(
            f"/api/v1/sections/{TEST_SECTION_GID}/reorder",
            json={
                "project_gid": TEST_PROJECT_GID,
                "after_section": "other_sect",
            },
            headers=AUTH_HEADER,
        )

        assert response.status_code == 204
        mock_inv.fire_and_forget.assert_not_called()
