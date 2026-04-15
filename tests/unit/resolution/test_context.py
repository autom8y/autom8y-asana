"""Tests for ResolutionContext."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from autom8_asana.models.business.business import Business
from autom8_asana.resolution.context import ResolutionContext, ResolutionError
from autom8_asana.resolution.result import ResolutionStatus
from tests.unit.resolution.conftest import make_business_entity

if TYPE_CHECKING:
    from autom8_asana.models.business.contact import ContactHolder


class TestResolutionContext:
    """Tests for ResolutionContext."""

    async def test_context_manager(self, mock_client: MagicMock) -> None:
        """Test async context manager clears cache."""
        async with ResolutionContext(mock_client) as ctx:
            entity = make_business_entity("test-123", "Test")
            ctx.cache_entity(entity)
            assert len(ctx._session_cache) == 1

        # Cache should be cleared after exit
        # (we can't check it directly since context is closed)

    def test_cache_entity(self, mock_client: MagicMock) -> None:
        """Test caching entity."""
        ctx = ResolutionContext(mock_client)
        entity = make_business_entity("test-123", "Test")
        ctx.cache_entity(entity)

        assert ctx._session_cache["test-123"] == entity

    def test_get_cached(self, mock_client: MagicMock, mock_business: Business) -> None:
        """Test retrieving cached entity by type."""
        ctx = ResolutionContext(mock_client)
        ctx.cache_entity(mock_business)

        result = ctx.get_cached(Business)
        assert result == mock_business

    def test_get_cached_returns_none_when_not_found(self, mock_client: MagicMock) -> None:
        """Test get_cached returns None when type not found."""
        ctx = ResolutionContext(mock_client)
        result = ctx.get_cached(Business)
        assert result is None

    def test_get_cached_business(self, mock_client: MagicMock, mock_business: Business) -> None:
        """Test convenience method for cached business."""
        ctx = ResolutionContext(mock_client)
        ctx.cache_entity(mock_business)

        result = ctx.get_cached_business()
        assert result == mock_business

    async def test_resolve_entity_async_no_source(self, mock_client: MagicMock) -> None:
        """Test resolve_entity_async fails with no source entity."""
        ctx = ResolutionContext(mock_client)  # No trigger_entity

        result = await ctx.resolve_entity_async(Business)

        assert result.status == ResolutionStatus.FAILED
        assert "No source entity" in result.diagnostics[0]

    async def test_resolve_entity_async_uses_trigger_entity(self, mock_client: MagicMock) -> None:
        """Test resolve_entity_async uses trigger_entity as default source."""
        trigger = make_business_entity("trigger-123", "Trigger")
        ctx = ResolutionContext(mock_client, trigger_entity=trigger)

        # Set up mock to return a task with no parent so traversal terminates
        # cleanly without producing unawaited coroutine warnings.
        terminal_task = MagicMock()
        terminal_task.parent = None
        terminal_task.gid = "trigger-123"
        mock_client.tasks.get_async.return_value = terminal_task

        # No dependencies to traverse
        async def empty_collect() -> list:
            return []

        dep_iter = MagicMock()
        dep_iter.collect = empty_collect
        mock_client.tasks.dependencies_async.return_value = dep_iter

        result = await ctx.resolve_entity_async(Business)

        # Should have tried strategies and all failed
        assert len(result.diagnostics) > 0

    async def test_business_async_with_gid(
        self,
        mock_client: MagicMock,
        mock_business: Business,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test business_async fast path with direct GID."""

        # Mock Business.from_gid_async (monkeypatch ensures cleanup)
        async def mock_from_gid(client, gid, hydrate=True):
            return mock_business

        monkeypatch.setattr(Business, "from_gid_async", mock_from_gid)

        ctx = ResolutionContext(mock_client, business_gid="biz-123")
        result = await ctx.business_async()

        assert result == mock_business

    async def test_business_async_raises_on_failure(self, mock_client: MagicMock) -> None:
        """Test business_async raises ResolutionError on failure."""
        ctx = ResolutionContext(mock_client)  # No trigger_entity

        with pytest.raises(ResolutionError) as exc_info:
            await ctx.business_async()

        assert "Cannot resolve Business" in str(exc_info.value)

    async def test_contact_async_raises_on_failure(self, mock_client: MagicMock) -> None:
        """Test contact_async raises ResolutionError on failure."""
        ctx = ResolutionContext(mock_client)

        with pytest.raises(ResolutionError) as exc_info:
            await ctx.contact_async()

        assert "Cannot resolve Contact" in str(exc_info.value)

    async def test_hydrate_branch_async(
        self, mock_client: MagicMock, mock_business: Business
    ) -> None:
        """Test branch hydration."""

        # Mock subtasks fetch
        async def mock_collect():
            return []

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter

        # Mock _populate_holders
        mock_business._populate_holders = MagicMock()

        ctx = ResolutionContext(mock_client)
        await ctx.hydrate_branch_async(mock_business, "contact_holder")

        # Should have fetched holders
        mock_client.tasks.subtasks_async.assert_called_once()
        assert ctx._holders_fetched is True

    async def test_hydrate_branch_async_cached(
        self, mock_client: MagicMock, mock_business: Business
    ) -> None:
        """Test branch hydration uses cached holders."""

        async def mock_collect():
            return []

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter
        mock_business._populate_holders = MagicMock()

        ctx = ResolutionContext(mock_client)
        ctx._holders_fetched = True  # Mark as already fetched

        await ctx.hydrate_branch_async(mock_business, "contact_holder")

        # Should NOT fetch holders again
        mock_client.tasks.subtasks_async.assert_not_called()


class TestResolveHolderAsync:
    """Tests for resolve_holder_async."""

    @staticmethod
    def _make_subtask_mock(
        gid: str,
        name: str,
        project_gids: list[str] | None = None,
    ) -> MagicMock:
        """Create a mock subtask with projects list."""
        subtask = MagicMock()
        subtask.gid = gid
        subtask.name = name
        subtask.resource_type = "task"
        if project_gids:
            projects = []
            for pgid in project_gids:
                p = MagicMock()
                p.gid = pgid
                projects.append(p)
            subtask.projects = projects
        else:
            subtask.projects = []
        subtask.model_dump.return_value = {
            "gid": gid,
            "name": name,
            "resource_type": "task",
        }
        return subtask

    async def test_returns_cached_holder(
        self, mock_client: MagicMock, mock_contact_holder: ContactHolder
    ) -> None:
        """Test returns holder from session cache without API call."""
        from autom8_asana.models.business.contact import ContactHolder

        ctx = ResolutionContext(mock_client, business_gid="biz-123")
        ctx.cache_entity(mock_contact_holder)

        result = await ctx.resolve_holder_async(ContactHolder)

        assert result == mock_contact_holder
        # No API call should have been made
        mock_client.tasks.subtasks_async.assert_not_called()

    async def test_returns_none_when_no_parent_gid(self, mock_client: MagicMock) -> None:
        """Test returns None when no parent GID is available."""
        from autom8_asana.models.business.contact import ContactHolder

        ctx = ResolutionContext(mock_client)  # No business_gid, no trigger

        result = await ctx.resolve_holder_async(ContactHolder)

        assert result is None
        mock_client.tasks.subtasks_async.assert_not_called()

    async def test_finds_holder_by_project_gid(self, mock_client: MagicMock) -> None:
        """Test finds holder among subtasks by matching PRIMARY_PROJECT_GID."""
        from autom8_asana.models.business.contact import ContactHolder

        # ContactHolder.PRIMARY_PROJECT_GID = "1201500116978260"  # noqa: ERA001
        contact_holder_gid = ContactHolder.PRIMARY_PROJECT_GID
        matching_subtask = self._make_subtask_mock(
            "holder-001",
            "Contacts",
            project_gids=[contact_holder_gid],
        )
        other_subtask = self._make_subtask_mock(
            "other-002",
            "Units",
            project_gids=["9999999999"],
        )

        async def mock_collect() -> list:
            return [other_subtask, matching_subtask]

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter

        ctx = ResolutionContext(mock_client, business_gid="biz-123")
        result = await ctx.resolve_holder_async(ContactHolder)

        assert result is not None
        assert result.gid == "holder-001"
        assert result.name == "Contacts"
        # Verify it was cached
        assert ctx.get_cached(ContactHolder) is not None
        # Verify API was called with the right parent
        mock_client.tasks.subtasks_async.assert_called_once_with(
            "biz-123", include_detection_fields=True
        )

    async def test_returns_none_when_no_matching_subtask(self, mock_client: MagicMock) -> None:
        """Test returns None when no subtask matches the holder type."""
        from autom8_asana.models.business.contact import ContactHolder

        unrelated_subtask = self._make_subtask_mock(
            "other-001",
            "Units",
            project_gids=["9999999999"],
        )

        async def mock_collect() -> list:
            return [unrelated_subtask]

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter

        ctx = ResolutionContext(mock_client, business_gid="biz-123")
        result = await ctx.resolve_holder_async(ContactHolder)

        assert result is None

    async def test_returns_none_when_no_subtasks(self, mock_client: MagicMock) -> None:
        """Test returns None when parent has no subtasks."""
        from autom8_asana.models.business.contact import ContactHolder

        async def mock_collect() -> list:
            return []

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter

        ctx = ResolutionContext(mock_client, business_gid="biz-123")
        result = await ctx.resolve_holder_async(ContactHolder)

        assert result is None

    async def test_uses_explicit_parent_gid(self, mock_client: MagicMock) -> None:
        """Test uses explicit parent_gid parameter over business_gid."""
        from autom8_asana.models.business.contact import ContactHolder

        async def mock_collect() -> list:
            return []

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter

        ctx = ResolutionContext(mock_client, business_gid="biz-default")
        await ctx.resolve_holder_async(ContactHolder, parent_gid="biz-override")

        # Should use the explicit parent_gid, not the context business_gid
        mock_client.tasks.subtasks_async.assert_called_once_with(
            "biz-override", include_detection_fields=True
        )

    async def test_returns_none_when_no_primary_project_gid(self, mock_client: MagicMock) -> None:
        """Test returns None when holder_type has no PRIMARY_PROJECT_GID."""
        from autom8_asana.models.business.base import BusinessEntity

        # BusinessEntity.PRIMARY_PROJECT_GID is None
        ctx = ResolutionContext(mock_client, business_gid="biz-123")
        result = await ctx.resolve_holder_async(BusinessEntity)

        assert result is None
        mock_client.tasks.subtasks_async.assert_not_called()

    async def test_uses_trigger_entity_parent_as_fallback(self, mock_client: MagicMock) -> None:
        """Test falls back to trigger_entity.parent.gid when no explicit parent."""
        from autom8_asana.models.business.contact import ContactHolder
        from autom8_asana.models.common import NameGid

        trigger = make_business_entity("trigger-123", "Trigger")
        # Set parent reference on trigger entity
        object.__setattr__(trigger, "parent", NameGid(gid="parent-from-trigger"))

        async def mock_collect() -> list:
            return []

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter

        ctx = ResolutionContext(mock_client, trigger_entity=trigger)
        await ctx.resolve_holder_async(ContactHolder)

        mock_client.tasks.subtasks_async.assert_called_once_with(
            "parent-from-trigger", include_detection_fields=True
        )

    async def test_handles_subtask_with_no_projects(self, mock_client: MagicMock) -> None:
        """Test gracefully handles subtasks that have no projects list."""
        from autom8_asana.models.business.contact import ContactHolder

        # Subtask with projects=None
        subtask_no_projects = MagicMock()
        subtask_no_projects.gid = "orphan-001"
        subtask_no_projects.name = "Orphan"
        subtask_no_projects.projects = None
        subtask_no_projects.resource_type = "task"

        async def mock_collect() -> list:
            return [subtask_no_projects]

        mock_iter = MagicMock()
        mock_iter.collect = mock_collect
        mock_client.tasks.subtasks_async.return_value = mock_iter

        ctx = ResolutionContext(mock_client, business_gid="biz-123")
        result = await ctx.resolve_holder_async(ContactHolder)

        assert result is None


class TestResolutionError:
    """Tests for ResolutionError."""

    def test_exception_message(self) -> None:
        """Test ResolutionError message."""
        err = ResolutionError("Test error message")
        assert str(err) == "Test error message"
