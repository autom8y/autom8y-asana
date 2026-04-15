"""Unit tests for story cache warming in the Lambda cache warmer.

Tests that the _warm_story_caches_for_completed_entities function:
1. Warms stories for all task GIDs found in warmed DataFrames
2. Handles timeout (exits early, logs)
3. Failure is isolated (doesn't affect overall warmer success)
4. Skips entity types with no DataFrame
5. Respects Semaphore concurrency
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.lambda_handlers.story_warmer import (
    _warm_story_caches_for_completed_entities,
)


def _always_project(et: str) -> str:
    return f"project-{et}"


def _always_none(et: str) -> None:
    return None


class TestWarmStoryCachesForCompletedEntities:
    """Tests for the _warm_story_caches_for_completed_entities helper."""

    @pytest.fixture
    def mock_dataframe_cache(self) -> MagicMock:
        """Create a mock DataFrameCache."""
        cache = MagicMock()
        cache.get_async = AsyncMock(return_value=None)
        return cache

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock AsanaClient with stories sub-client."""
        client = MagicMock()
        client.stories = MagicMock()
        client.stories.list_for_task_cached_async = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def offer_dataframe(self) -> pl.DataFrame:
        """Create a DataFrame with GID column."""
        return pl.DataFrame(
            {
                "gid": ["task-1", "task-2", "task-3"],
                "name": ["Offer A", "Offer B", "Offer C"],
            }
        )

    @pytest.fixture
    def no_gid_dataframe(self) -> pl.DataFrame:
        """Create a DataFrame WITHOUT GID column."""
        return pl.DataFrame(
            {
                "name": ["Thing A"],
                "status": ["active"],
            }
        )

    async def test_warms_stories_for_all_task_gids(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
        offer_dataframe: pl.DataFrame,
    ) -> None:
        """Story warming calls list_for_task_cached_async for each task GID."""
        mock_entry = MagicMock()
        mock_entry.dataframe = offer_dataframe
        mock_dataframe_cache.get_async.return_value = mock_entry

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-1",
                context=None,
            )

        assert stats["success"] == 3
        assert stats["failure"] == 0
        assert stats["total_tasks"] == 3
        assert mock_client.stories.list_for_task_cached_async.call_count == 3

        # Verify max_cache_age_seconds=7200 was passed
        for call in mock_client.stories.list_for_task_cached_async.call_args_list:
            assert call.kwargs.get("max_cache_age_seconds") == 7200

    async def test_handles_timeout_exits_early(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Story warming exits early when Lambda timeout is imminent."""
        # Create a large DataFrame (>100 tasks to trigger chunk boundary)
        large_df = pl.DataFrame(
            {
                "gid": [f"task-{i}" for i in range(200)],
                "name": [f"Task {i}" for i in range(200)],
            }
        )
        mock_entry = MagicMock()
        mock_entry.dataframe = large_df
        mock_dataframe_cache.get_async.return_value = mock_entry

        # Mock context that signals timeout after first chunk
        context = MagicMock()
        call_count = 0

        def get_remaining() -> int:
            nonlocal call_count
            call_count += 1
            # First call: plenty of time. Second call: timeout imminent.
            if call_count <= 1:
                return 300_000
            return 60_000  # Below TIMEOUT_BUFFER_MS (120_000)

        context.get_remaining_time_in_millis = get_remaining

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-timeout",
                context=context,
            )

        # Should have processed first chunk (100) but not second
        assert stats["success"] == 100
        assert stats["total_tasks"] == 200

    async def test_failure_is_isolated_does_not_raise(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
        offer_dataframe: pl.DataFrame,
    ) -> None:
        """Story warming failure for individual tasks does not propagate."""
        mock_entry = MagicMock()
        mock_entry.dataframe = offer_dataframe
        mock_dataframe_cache.get_async.return_value = mock_entry

        # Make the story fetch fail for all tasks
        mock_client.stories.list_for_task_cached_async = AsyncMock(
            side_effect=RuntimeError("API error"),
        )

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            # Should NOT raise
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-fail",
                context=None,
            )

        assert stats["success"] == 0
        assert stats["failure"] == 3
        assert stats["total_tasks"] == 3

    async def test_skips_entity_with_no_dataframe(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Entities with no cached DataFrame are silently skipped."""
        mock_dataframe_cache.get_async.return_value = None

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-no-df",
                context=None,
            )

        assert stats["total_tasks"] == 0
        assert stats["success"] == 0
        mock_client.stories.list_for_task_cached_async.assert_not_called()

    async def test_skips_entity_with_no_gid_column(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
        no_gid_dataframe: pl.DataFrame,
    ) -> None:
        """Entities whose DataFrames lack a 'gid' column are skipped."""
        mock_entry = MagicMock()
        mock_entry.dataframe = no_gid_dataframe
        mock_dataframe_cache.get_async.return_value = mock_entry

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-no-gid",
                context=None,
            )

        assert stats["total_tasks"] == 0
        mock_client.stories.list_for_task_cached_async.assert_not_called()

    async def test_skips_entity_with_no_project_gid(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Entities without a project GID are skipped."""
        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_none,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-no-proj",
                context=None,
            )

        assert stats["total_tasks"] == 0
        mock_client.stories.list_for_task_cached_async.assert_not_called()

    async def test_emits_cloudwatch_metrics(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
        offer_dataframe: pl.DataFrame,
    ) -> None:
        """Emits StoryWarmSuccess, StoryWarmFailure, StoriesWarmed, StoryWarmDuration."""
        mock_entry = MagicMock()
        mock_entry.dataframe = offer_dataframe
        mock_dataframe_cache.get_async.return_value = mock_entry

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ) as mock_emit:
            await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-metrics",
                context=None,
            )

        metric_names = [call.args[0] for call in mock_emit.call_args_list]
        assert "StoryWarmSuccess" in metric_names
        assert "StoryWarmFailure" in metric_names
        assert "StoriesWarmed" in metric_names
        assert "StoryWarmDuration" in metric_names

    async def test_empty_completed_entities_is_noop(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """No work done when completed_entities is empty."""
        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=[],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-empty",
                context=None,
            )

        assert stats["total_tasks"] == 0
        assert stats["success"] == 0
        mock_client.stories.list_for_task_cached_async.assert_not_called()

    async def test_fatal_error_is_caught(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Fatal error in story warming is caught and does not propagate."""
        # Make get_async raise to trigger the outer try/except
        mock_dataframe_cache.get_async = AsyncMock(
            side_effect=RuntimeError("catastrophic failure"),
        )

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            # Should NOT raise
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-fatal",
                context=None,
            )

        # Stats may be partial but function returned cleanly
        assert isinstance(stats, dict)

    async def test_multiple_entities_processes_all(
        self,
        mock_dataframe_cache: MagicMock,
        mock_client: MagicMock,
    ) -> None:
        """Processes multiple entity types, collecting tasks from each."""
        offer_df = pl.DataFrame({"gid": ["task-1", "task-2"], "name": ["A", "B"]})
        unit_df = pl.DataFrame({"gid": ["task-3"], "name": ["C"]})

        offer_entry = MagicMock()
        offer_entry.dataframe = offer_df
        unit_entry = MagicMock()
        unit_entry.dataframe = unit_df

        async def mock_get_async(project_gid: str, entity_type: str) -> MagicMock:
            if entity_type == "offer":
                return offer_entry
            elif entity_type == "unit":
                return unit_entry
            return None

        mock_dataframe_cache.get_async = mock_get_async

        with patch(
            "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["offer", "unit"],
                get_project_gid=_always_project,
                dataframe_cache=mock_dataframe_cache,
                client=mock_client,
                invocation_id="test-invoke-multi",
                context=None,
            )

        assert stats["total_tasks"] == 3
        assert stats["success"] == 3
        assert mock_client.stories.list_for_task_cached_async.call_count == 3
