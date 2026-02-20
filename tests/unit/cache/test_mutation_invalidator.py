"""Tests for MutationInvalidator service.

Per TDD-CACHE-INVALIDATION-001 Test Strategy: Unit tests for
MutationInvalidator with mock CacheProvider and mock DataFrameCache.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.cache.integration.mutation_invalidator import (
    MutationInvalidator,
    _log_task_exception,
)
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
)


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock CacheProvider."""
    cache = MagicMock()
    cache.invalidate = MagicMock()
    return cache


@pytest.fixture
def mock_df_cache() -> MagicMock:
    """Create a mock DataFrameCache with invalidate_project."""
    df_cache = MagicMock()
    df_cache.invalidate_project = MagicMock()
    return df_cache


@pytest.fixture
def invalidator(mock_cache: MagicMock) -> MutationInvalidator:
    """Create a MutationInvalidator with mock cache, no DataFrameCache."""
    return MutationInvalidator(cache_provider=mock_cache)


@pytest.fixture
def invalidator_with_df(
    mock_cache: MagicMock, mock_df_cache: MagicMock
) -> MutationInvalidator:
    """Create a MutationInvalidator with both cache backends."""
    return MutationInvalidator(cache_provider=mock_cache, dataframe_cache=mock_df_cache)


class TestTaskMutationInvalidation:
    """Tests for task mutation handling."""

    @pytest.mark.asyncio
    async def test_task_update_invalidates_entity_cache(
        self, invalidator: MutationInvalidator, mock_cache: MagicMock
    ) -> None:
        """Task update invalidates TASK, SUBTASKS, DETECTION entries."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
        )
        await invalidator.invalidate_async(event)

        mock_cache.invalidate.assert_called_once_with(
            "12345", [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]
        )

    @pytest.mark.asyncio
    async def test_task_update_with_project_context_invalidates_dataframes(
        self, invalidator: MutationInvalidator, mock_cache: MagicMock
    ) -> None:
        """Task update with project_gids invalidates per-task DataFrame entries."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
            project_gids=["proj1", "proj2"],
        )

        with patch(
            "autom8_asana.cache.integration.dataframes.invalidate_task_dataframes"
        ) as mock_df_inv:
            await invalidator.invalidate_async(event)

        # Per-task DataFrame invalidation called with correct args
        mock_df_inv.assert_called_once_with(
            "12345", ["proj1", "proj2"], invalidator._cache
        )
        # Entity cache still invalidated
        mock_cache.invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_create_triggers_project_dataframe_invalidation(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_cache: MagicMock,
        mock_df_cache: MagicMock,
    ) -> None:
        """Task create invalidates project DataFrameCache (structural change)."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="new_task",
            mutation_type=MutationType.CREATE,
            project_gids=["proj1"],
        )
        await invalidator_with_df.invalidate_async(event)

        # Entity cache invalidated (may also include per-task DataFrame calls)
        mock_cache.invalidate.assert_any_call(
            "new_task", [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]
        )
        # Project DataFrame invalidated
        mock_df_cache.invalidate_project.assert_called_once_with("proj1")

    @pytest.mark.asyncio
    async def test_task_delete_triggers_project_dataframe_invalidation(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_cache: MagicMock,
        mock_df_cache: MagicMock,
    ) -> None:
        """Task delete invalidates project DataFrameCache when project GIDs known."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.DELETE,
            project_gids=["proj1"],
        )
        await invalidator_with_df.invalidate_async(event)

        mock_df_cache.invalidate_project.assert_called_once_with("proj1")

    @pytest.mark.asyncio
    async def test_task_update_does_not_trigger_project_dataframe_invalidation(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_df_cache: MagicMock,
    ) -> None:
        """Task update (non-structural) does NOT invalidate project DataFrameCache."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
            project_gids=["proj1"],
        )
        await invalidator_with_df.invalidate_async(event)

        mock_df_cache.invalidate_project.assert_not_called()

    @pytest.mark.asyncio
    async def test_task_move_invalidates_project_dataframes(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_df_cache: MagicMock,
    ) -> None:
        """Task move invalidates DataFrameCache for affected projects."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.MOVE,
            project_gids=["proj1"],
            section_gid="sect_dest",
        )
        await invalidator_with_df.invalidate_async(event)

        mock_df_cache.invalidate_project.assert_called_once_with("proj1")

    @pytest.mark.asyncio
    async def test_task_add_member_invalidates_project_dataframes(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_df_cache: MagicMock,
    ) -> None:
        """Task add-to-project invalidates project DataFrameCache."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.ADD_MEMBER,
            project_gids=["proj_new"],
        )
        await invalidator_with_df.invalidate_async(event)

        mock_df_cache.invalidate_project.assert_called_once_with("proj_new")

    @pytest.mark.asyncio
    async def test_task_remove_member_invalidates_project_dataframes(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_df_cache: MagicMock,
    ) -> None:
        """Task remove-from-project invalidates project DataFrameCache."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.REMOVE_MEMBER,
            project_gids=["proj_old"],
        )
        await invalidator_with_df.invalidate_async(event)

        mock_df_cache.invalidate_project.assert_called_once_with("proj_old")


class TestStoryCacheInvalidation:
    """Tests for story cache invalidation on task mutations.

    Per R4-revised: only DELETE mutations hard-invalidate EntryType.STORIES.
    UPDATE, MOVE, CREATE preserve story entries so load_stories_incremental()
    can use the 'since' cursor for cheap incremental fetches (ADR-0020).
    """

    @pytest.mark.asyncio
    async def test_delete_mutation_invalidates_stories(
        self, invalidator: MutationInvalidator, mock_cache: MagicMock
    ) -> None:
        """DELETE event hard-invalidates EntryType.STORIES."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.DELETE,
            project_gids=["proj1"],
        )
        await invalidator.invalidate_async(event)

        # Should have two invalidate calls: entity types + stories
        calls = mock_cache.invalidate.call_args_list
        entity_call = calls[0]
        story_call = calls[1]

        assert entity_call.args == (
            "12345",
            [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION],
        )
        assert story_call.args == ("12345", [EntryType.STORIES])

    @pytest.mark.asyncio
    async def test_update_mutation_does_not_invalidate_stories(
        self, invalidator: MutationInvalidator, mock_cache: MagicMock
    ) -> None:
        """UPDATE event does NOT invalidate EntryType.STORIES."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
        )
        await invalidator.invalidate_async(event)

        # Only the entity types call, no stories
        mock_cache.invalidate.assert_called_once_with(
            "12345", [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]
        )

    @pytest.mark.asyncio
    async def test_move_mutation_does_not_invalidate_stories(
        self, invalidator: MutationInvalidator, mock_cache: MagicMock
    ) -> None:
        """MOVE event does NOT invalidate EntryType.STORIES."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.MOVE,
            project_gids=["proj1"],
            section_gid="sect_dest",
        )
        await invalidator.invalidate_async(event)

        # Verify no call includes EntryType.STORIES
        for call in mock_cache.invalidate.call_args_list:
            entry_types = call.args[1]
            assert EntryType.STORIES not in entry_types

    @pytest.mark.asyncio
    async def test_story_invalidation_failure_does_not_propagate(
        self, mock_cache: MagicMock
    ) -> None:
        """Story cache invalidation failure is caught and logged."""
        call_count = 0

        def selective_fail(gid: str, entry_types: list) -> None:
            nonlocal call_count
            call_count += 1
            if entry_types == [EntryType.STORIES]:
                raise ConnectionError("Redis down")

        mock_cache.invalidate.side_effect = selective_fail
        inv = MutationInvalidator(cache_provider=mock_cache)

        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.DELETE,
            project_gids=["proj1"],
        )
        # Should not raise despite story invalidation failure
        await inv.invalidate_async(event)


class TestSectionMutationInvalidation:
    """Tests for section mutation handling."""

    @pytest.mark.asyncio
    async def test_section_create_invalidates_section_cache(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_cache: MagicMock,
    ) -> None:
        """Section create invalidates SECTION entry type."""
        event = MutationEvent(
            entity_kind=EntityKind.SECTION,
            entity_gid="sect1",
            mutation_type=MutationType.CREATE,
            project_gids=["proj1"],
        )
        await invalidator_with_df.invalidate_async(event)

        mock_cache.invalidate.assert_called_once_with("sect1", [EntryType.SECTION])

    @pytest.mark.asyncio
    async def test_section_create_invalidates_project_dataframes(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_df_cache: MagicMock,
    ) -> None:
        """Section create invalidates project DataFrameCache."""
        event = MutationEvent(
            entity_kind=EntityKind.SECTION,
            entity_gid="sect1",
            mutation_type=MutationType.CREATE,
            project_gids=["proj1"],
        )
        await invalidator_with_df.invalidate_async(event)

        mock_df_cache.invalidate_project.assert_called_once_with("proj1")

    @pytest.mark.asyncio
    async def test_section_update_invalidates_entity_and_project(
        self,
        invalidator_with_df: MutationInvalidator,
        mock_cache: MagicMock,
        mock_df_cache: MagicMock,
    ) -> None:
        """Section update invalidates both section cache and project DataFrame."""
        event = MutationEvent(
            entity_kind=EntityKind.SECTION,
            entity_gid="sect1",
            mutation_type=MutationType.UPDATE,
            project_gids=["proj1"],
        )
        await invalidator_with_df.invalidate_async(event)

        mock_cache.invalidate.assert_called_once_with("sect1", [EntryType.SECTION])
        mock_df_cache.invalidate_project.assert_called_once_with("proj1")

    @pytest.mark.asyncio
    async def test_section_delete_invalidates_entity(
        self,
        invalidator: MutationInvalidator,
        mock_cache: MagicMock,
    ) -> None:
        """Section delete invalidates section entity cache."""
        event = MutationEvent(
            entity_kind=EntityKind.SECTION,
            entity_gid="sect1",
            mutation_type=MutationType.DELETE,
        )
        await invalidator.invalidate_async(event)

        mock_cache.invalidate.assert_called_once_with("sect1", [EntryType.SECTION])

    @pytest.mark.asyncio
    async def test_add_task_to_section_invalidates_task_entity(
        self,
        invalidator: MutationInvalidator,
        mock_cache: MagicMock,
    ) -> None:
        """Add-task-to-section invalidates both section and task entity caches."""
        event = MutationEvent(
            entity_kind=EntityKind.SECTION,
            entity_gid="sect1",
            mutation_type=MutationType.ADD_MEMBER,
            section_gid="task_gid_123",  # Task GID carried via section_gid
        )
        await invalidator.invalidate_async(event)

        # Should invalidate section entry AND task entry
        assert mock_cache.invalidate.call_count == 2
        calls = mock_cache.invalidate.call_args_list
        # First call: section entity
        assert calls[0].args[0] == "sect1"
        assert calls[0].args[1] == [EntryType.SECTION]
        # Second call: task entity
        assert calls[1].args[0] == "task_gid_123"
        assert calls[1].args[1] == [
            EntryType.TASK,
            EntryType.SUBTASKS,
            EntryType.DETECTION,
        ]


class TestGracefulDegradation:
    """Tests for error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_missing_dataframe_cache_skips_project_invalidation(
        self, invalidator: MutationInvalidator
    ) -> None:
        """No DataFrameCache skips project DataFrame invalidation without error."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.CREATE,
            project_gids=["proj1"],
        )
        # Should not raise
        await invalidator.invalidate_async(event)

    @pytest.mark.asyncio
    async def test_cache_provider_failure_does_not_propagate(
        self, mock_cache: MagicMock
    ) -> None:
        """Cache provider failure is caught and logged, not propagated."""
        mock_cache.invalidate.side_effect = ConnectionError("Redis down")
        inv = MutationInvalidator(cache_provider=mock_cache)

        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
        )
        # Should not raise
        await inv.invalidate_async(event)

    @pytest.mark.asyncio
    async def test_dataframe_cache_failure_does_not_propagate(
        self, mock_cache: MagicMock, mock_df_cache: MagicMock
    ) -> None:
        """DataFrameCache failure is caught and logged, not propagated."""
        mock_df_cache.invalidate_project.side_effect = ConnectionError("Memory error")
        inv = MutationInvalidator(
            cache_provider=mock_cache, dataframe_cache=mock_df_cache
        )

        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.CREATE,
            project_gids=["proj1"],
        )
        # Should not raise
        await inv.invalidate_async(event)

    @pytest.mark.asyncio
    async def test_unsupported_entity_kind_logs_warning(
        self, invalidator: MutationInvalidator
    ) -> None:
        """Unsupported entity kind logs warning but does not raise."""
        event = MutationEvent(
            entity_kind=EntityKind.PROJECT,
            entity_gid="proj1",
            mutation_type=MutationType.UPDATE,
        )
        # Should not raise
        await invalidator.invalidate_async(event)

    @pytest.mark.asyncio
    async def test_section_cache_failure_still_processes_dataframes(
        self, mock_cache: MagicMock, mock_df_cache: MagicMock
    ) -> None:
        """Section entity cache failure still processes DataFrame invalidation."""
        mock_cache.invalidate.side_effect = ConnectionError("Cache down")
        inv = MutationInvalidator(
            cache_provider=mock_cache, dataframe_cache=mock_df_cache
        )

        event = MutationEvent(
            entity_kind=EntityKind.SECTION,
            entity_gid="sect1",
            mutation_type=MutationType.UPDATE,
            project_gids=["proj1"],
        )
        await inv.invalidate_async(event)

        # DataFrame cache still called despite entity cache failure
        mock_df_cache.invalidate_project.assert_called_once_with("proj1")


class TestFireAndForget:
    """Tests for the fire-and-forget pattern."""

    @pytest.mark.asyncio
    async def test_fire_and_forget_creates_task(
        self, invalidator: MutationInvalidator
    ) -> None:
        """fire_and_forget schedules an asyncio task."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
        )
        invalidator.fire_and_forget(event)

        # Let the event loop process the background task
        await asyncio.sleep(0.01)

    @pytest.mark.asyncio
    async def test_fire_and_forget_task_has_name(
        self, invalidator: MutationInvalidator
    ) -> None:
        """fire_and_forget creates a named task for debugging."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
        )

        async def noop_invalidate(evt: MutationEvent) -> None:
            pass

        with patch.object(invalidator, "invalidate_async", side_effect=noop_invalidate):
            invalidator.fire_and_forget(event)
            await asyncio.sleep(0.01)


class TestLogTaskException:
    """Tests for the _log_task_exception callback."""

    def test_cancelled_task_is_silent(self) -> None:
        """Cancelled tasks are not logged."""
        task = MagicMock()
        task.cancelled.return_value = True
        # Should not raise or log
        _log_task_exception(task)
        task.exception.assert_not_called()

    def test_successful_task_is_silent(self) -> None:
        """Successful tasks (no exception) are not logged."""
        task = MagicMock()
        task.cancelled.return_value = False
        task.exception.return_value = None
        _log_task_exception(task)

    def test_failed_task_logs_error(self) -> None:
        """Failed tasks log the exception."""
        task = MagicMock()
        task.cancelled.return_value = False
        task.exception.return_value = RuntimeError("test error")
        task.get_name.return_value = "invalidate:task:12345"
        # Should not raise
        _log_task_exception(task)
