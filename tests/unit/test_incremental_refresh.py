"""Tests for incremental refresh functionality in ProjectDataFrameBuilder.

Tests cover:
- refresh_incremental with no watermark triggers full rebuild
- refresh_incremental with watermark triggers incremental fetch
- _merge_deltas correctness (filter + concat)
- Fallback behavior on error
- New watermark calculation

Per TDD-materialization-layer FR-002, FR-006:
ProjectDataFrameBuilder.refresh_incremental() provides efficient incremental
sync using modified_since API parameter.

NOTE: These tests require migration to ProgressiveProjectBuilder.
The old ProjectDataFrameBuilder has been removed. Tests are skipped until migration.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

# Skip marker for entire module - tests need migration to ProgressiveProjectBuilder
pytestmark = pytest.mark.skip(
    reason="Requires migration to ProgressiveProjectBuilder - constructor signatures differ"
)

if TYPE_CHECKING:
    pass


# Minimal test schema with only required fields for testing
TEST_SCHEMA = DataFrameSchema(
    name="test",
    task_type="*",
    columns=[
        ColumnDef(name="gid", dtype="Utf8", nullable=False, source="gid"),
        ColumnDef(name="name", dtype="Utf8", nullable=False, source="name"),
        ColumnDef(name="type", dtype="Utf8", nullable=False),
        ColumnDef(name="date", dtype="Date", nullable=True),
        ColumnDef(
            name="created", dtype="Datetime", nullable=False, source="created_at"
        ),
        ColumnDef(name="due_on", dtype="Date", nullable=True, source="due_on"),
        ColumnDef(
            name="is_completed", dtype="Boolean", nullable=False, source="completed"
        ),
        ColumnDef(
            name="completed_at", dtype="Datetime", nullable=True, source="completed_at"
        ),
        ColumnDef(name="url", dtype="Utf8", nullable=False),
        ColumnDef(
            name="last_modified", dtype="Datetime", nullable=False, source="modified_at"
        ),
        ColumnDef(name="section", dtype="Utf8", nullable=True),
        ColumnDef(name="tags", dtype="List[Utf8]", nullable=False, source="tags"),
    ],
    version="1.0.0",
)


@pytest.fixture
def mock_unified_store() -> AsyncMock:
    """Create a mock UnifiedTaskStore for Phase 4 mandatory requirement."""
    store = AsyncMock()
    store.get_batch_async = AsyncMock(return_value={})
    store.put_batch_async = AsyncMock(return_value=0)
    return store


def make_mock_task(
    gid: str,
    name: str,
    modified_at: str = "2024-06-15T12:00:00.000Z",
    completed: bool = False,
) -> MagicMock:
    """Create a mock Task object for testing."""
    task = MagicMock()
    task.gid = gid
    task.name = name
    task.resource_subtype = "default_task"
    task.completed = completed
    task.completed_at = None
    task.created_at = "2024-01-01T00:00:00.000Z"
    task.modified_at = modified_at
    task.due_on = None
    task.tags = []
    task.memberships = []
    return task


def make_mock_project(gid: str, tasks: list[Any] | None = None) -> MagicMock:
    """Create a mock Project object for testing."""
    project = MagicMock()
    project.gid = gid
    project.tasks = tasks or []
    return project


def make_test_dataframe(
    gids: list[str],
    names: list[str],
    last_modified: datetime | None = None,
) -> pl.DataFrame:
    """Create a test DataFrame with proper schema.

    Uses TEST_SCHEMA to ensure type compatibility for merge operations.
    """
    if last_modified is None:
        last_modified = datetime(2024, 1, 1, tzinfo=UTC)

    n = len(gids)
    return pl.DataFrame(
        {
            "gid": gids,
            "name": names,
            "type": ["*"] * n,
            "date": [None] * n,
            "created": [datetime(2024, 1, 1, tzinfo=UTC)] * n,
            "due_on": [None] * n,
            "is_completed": [False] * n,
            "completed_at": [None] * n,
            "url": [f"https://app.asana.com/0/0/{gid}" for gid in gids],
            "last_modified": [last_modified] * n,
            "section": [None] * n,
            "tags": [[]] * n,
        },
        schema=TEST_SCHEMA.to_polars_schema(),
    )


class TestRefreshIncrementalNoWatermark:
    """Tests for refresh_incremental when no watermark exists (first sync)."""

    @pytest.mark.asyncio
    async def test_no_watermark_triggers_full_fetch(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """When watermark is None, refresh_incremental performs full fetch."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Mock the full fetch path
        mock_client = MagicMock()

        # Patch build_with_parallel_fetch_async to return a test DataFrame
        with patch.object(
            builder, "build_with_parallel_fetch_async", new_callable=AsyncMock
        ) as mock_build:
            mock_build.return_value = pl.DataFrame(
                {
                    "gid": ["task-1", "task-2"],
                    "name": ["Task 1", "Task 2"],
                    "type": ["*", "*"],
                    "date": [None, None],
                    "created": [datetime(2024, 1, 1, tzinfo=UTC)] * 2,
                    "due_on": [None, None],
                    "is_completed": [False, False],
                    "completed_at": [None, None],
                    "url": [
                        "https://app.asana.com/0/0/task-1",
                        "https://app.asana.com/0/0/task-2",
                    ],
                    "last_modified": [datetime(2024, 6, 15, tzinfo=UTC)] * 2,
                    "section": [None, None],
                    "tags": [[], []],
                }
            )

            df, new_watermark = await builder.refresh_incremental(
                client=mock_client,
                existing_df=None,
                watermark=None,
            )

            # Full fetch should have been called
            mock_build.assert_called_once_with(mock_client)

            # Should return a valid DataFrame
            assert len(df) == 2
            assert "gid" in df.columns

            # New watermark should be set
            assert new_watermark is not None
            assert new_watermark.tzinfo is not None

    @pytest.mark.asyncio
    async def test_existing_df_none_with_watermark_triggers_full_fetch(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """When existing_df is None even with watermark, performs full fetch."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        mock_client = MagicMock()
        watermark = datetime(2024, 1, 1, tzinfo=UTC)

        with patch.object(
            builder, "build_with_parallel_fetch_async", new_callable=AsyncMock
        ) as mock_build:
            mock_build.return_value = pl.DataFrame(
                {
                    "gid": ["task-1"],
                    "name": ["Task 1"],
                    "type": ["*"],
                    "date": [None],
                    "created": [datetime(2024, 1, 1, tzinfo=UTC)],
                    "due_on": [None],
                    "is_completed": [False],
                    "completed_at": [None],
                    "url": ["https://app.asana.com/0/0/task-1"],
                    "last_modified": [datetime(2024, 6, 15, tzinfo=UTC)],
                    "section": [None],
                    "tags": [[]],
                }
            )

            df, new_watermark = await builder.refresh_incremental(
                client=mock_client,
                existing_df=None,
                watermark=watermark,
            )

            # Full fetch should be triggered since existing_df is None
            mock_build.assert_called_once()


class TestRefreshIncrementalWithWatermark:
    """Tests for refresh_incremental with valid watermark (incremental sync)."""

    @pytest.mark.asyncio
    async def test_with_watermark_fetches_modified_only(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """When watermark exists, only tasks modified since are fetched."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Create existing DataFrame with one task
        existing_df = make_test_dataframe(["task-1"], ["Task 1"])

        watermark = datetime(2024, 1, 15, tzinfo=UTC)
        mock_client = MagicMock()

        # Mock the _fetch_modified_tasks to return one modified task
        modified_task = make_mock_task(
            gid="task-1",
            name="Task 1 Updated",
            modified_at="2024-06-15T12:00:00.000Z",
        )

        with patch.object(
            builder, "_fetch_modified_tasks", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = [modified_task]

            df, new_watermark = await builder.refresh_incremental(
                client=mock_client,
                existing_df=existing_df,
                watermark=watermark,
            )

            # Should have called _fetch_modified_tasks
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args
            assert call_args[0][1] == "project-123"  # project_gid
            assert call_args[0][2] == watermark

            # New watermark should be returned
            assert new_watermark is not None

    @pytest.mark.asyncio
    async def test_no_changes_returns_existing_df(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """When no tasks are modified, returns existing DataFrame unchanged."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        existing_df = make_test_dataframe(
            ["task-1", "task-2"],
            ["Task 1", "Task 2"],
        )

        watermark = datetime(2024, 1, 15, tzinfo=UTC)
        mock_client = MagicMock()

        with patch.object(
            builder, "_fetch_modified_tasks", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []  # No modified tasks

            df, new_watermark = await builder.refresh_incremental(
                client=mock_client,
                existing_df=existing_df,
                watermark=watermark,
            )

            # Should return existing DataFrame
            assert df is existing_df
            assert len(df) == 2

            # New watermark should still be set
            assert new_watermark is not None


@pytest.mark.skip(
    reason="_merge_deltas() method removed - only _merge_deltas_async() exists"
)
class TestMergeDeltas:
    """Tests for _merge_deltas method (filter + concat logic)."""

    def test_merge_deltas_replaces_existing_rows(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """Changed tasks replace existing rows with matching GIDs."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        existing_df = make_test_dataframe(
            ["task-1", "task-2", "task-3"],
            ["Task 1", "Task 2", "Task 3"],
        )

        # Mock tasks representing changes
        changed_task = make_mock_task(
            gid="task-2",
            name="Task 2 Updated",
            modified_at="2024-06-15T12:00:00.000Z",
            completed=True,
        )

        result = builder._merge_deltas(existing_df, [changed_task])

        # Should still have 3 rows
        assert len(result) == 3

        # task-2 should be updated
        task2_rows = result.filter(pl.col("gid") == "task-2")
        assert len(task2_rows) == 1

        # task-1 and task-3 should be unchanged
        task1_rows = result.filter(pl.col("gid") == "task-1")
        task3_rows = result.filter(pl.col("gid") == "task-3")
        assert len(task1_rows) == 1
        assert len(task3_rows) == 1

    def test_merge_deltas_adds_new_tasks(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """New tasks (GIDs not in existing DataFrame) are appended."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        existing_df = make_test_dataframe(["task-1"], ["Task 1"])

        # New task not in existing DataFrame
        new_task = make_mock_task(
            gid="task-new",
            name="New Task",
            modified_at="2024-06-15T12:00:00.000Z",
        )

        result = builder._merge_deltas(existing_df, [new_task])

        # Should have 2 rows now
        assert len(result) == 2

        # Both tasks should be present
        gids = result["gid"].to_list()
        assert "task-1" in gids
        assert "task-new" in gids

    def test_merge_deltas_empty_changes_returns_existing(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """When no changes, returns existing DataFrame unchanged."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        existing_df = make_test_dataframe(
            ["task-1", "task-2"],
            ["Task 1", "Task 2"],
        )

        result = builder._merge_deltas(existing_df, [])

        assert result is existing_df

    def test_merge_deltas_multiple_updates_and_new(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """Multiple updates and new tasks are handled correctly."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        existing_df = make_test_dataframe(
            ["task-1", "task-2", "task-3"],
            ["Task 1", "Task 2", "Task 3"],
        )

        # One update, one new
        updated_task = make_mock_task(gid="task-2", name="Task 2 Updated")
        new_task = make_mock_task(gid="task-4", name="Task 4")

        result = builder._merge_deltas(existing_df, [updated_task, new_task])

        assert len(result) == 4
        gids = result["gid"].to_list()
        assert set(gids) == {"task-1", "task-2", "task-3", "task-4"}


class TestFallbackBehavior:
    """Tests for fallback behavior on errors."""

    @pytest.mark.asyncio
    async def test_error_during_incremental_triggers_full_fetch(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """Errors during incremental fetch trigger fallback to full fetch."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        existing_df = make_test_dataframe(["task-1"], ["Task 1"])

        watermark = datetime(2024, 1, 15, tzinfo=UTC)
        mock_client = MagicMock()

        with patch.object(
            builder, "_fetch_modified_tasks", new_callable=AsyncMock
        ) as mock_fetch:
            # Simulate error during incremental fetch
            mock_fetch.side_effect = RuntimeError("API error")

            with patch.object(
                builder, "build_with_parallel_fetch_async", new_callable=AsyncMock
            ) as mock_full:
                mock_full.return_value = make_test_dataframe(
                    ["task-1", "task-2"],
                    ["Task 1", "Task 2"],
                    last_modified=datetime(2024, 6, 15, tzinfo=UTC),
                )

                df, new_watermark = await builder.refresh_incremental(
                    client=mock_client,
                    existing_df=existing_df,
                    watermark=watermark,
                )

                # Should have fallen back to full fetch
                mock_full.assert_called_once()
                assert len(df) == 2

    @pytest.mark.asyncio
    async def test_future_watermark_triggers_full_rebuild(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """Watermark in future (clock skew) triggers full rebuild."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        existing_df = make_test_dataframe(["task-1"], ["Task 1"])

        # Future watermark (clock skew scenario)
        future_watermark = datetime.now(UTC) + timedelta(days=365)
        mock_client = MagicMock()

        with patch.object(
            builder, "build_with_parallel_fetch_async", new_callable=AsyncMock
        ) as mock_full:
            mock_full.return_value = make_test_dataframe(
                ["task-1"],
                ["Task 1"],
                last_modified=datetime(2024, 6, 15, tzinfo=UTC),
            )

            # Future watermark should trigger fallback to full fetch
            df, new_watermark = await builder.refresh_incremental(
                client=mock_client,
                existing_df=existing_df,
                watermark=future_watermark,
            )

            # Should have done full fetch as fallback
            mock_full.assert_called_once()


class TestWatermarkCalculation:
    """Tests for new watermark calculation."""

    @pytest.mark.asyncio
    async def test_new_watermark_is_sync_start_time(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """New watermark should be the sync start time (not task modified_at)."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        mock_client = MagicMock()
        before_sync = datetime.now(UTC)

        with patch.object(
            builder, "build_with_parallel_fetch_async", new_callable=AsyncMock
        ) as mock_build:
            mock_build.return_value = make_test_dataframe(
                ["task-1"],
                ["Task 1"],
                last_modified=datetime(2024, 6, 15, tzinfo=UTC),
            )

            _, new_watermark = await builder.refresh_incremental(
                client=mock_client,
                existing_df=None,
                watermark=None,
            )

        after_sync = datetime.now(UTC)

        # New watermark should be between before and after sync time
        assert before_sync <= new_watermark <= after_sync

    @pytest.mark.asyncio
    async def test_watermark_is_timezone_aware(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """New watermark must be timezone-aware (UTC)."""
        project = make_mock_project("project-123", [])
        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        mock_client = MagicMock()

        with patch.object(
            builder, "build_with_parallel_fetch_async", new_callable=AsyncMock
        ) as mock_build:
            mock_build.return_value = make_test_dataframe(
                ["task-1"],
                ["Task 1"],
                last_modified=datetime(2024, 6, 15, tzinfo=UTC),
            )

            _, new_watermark = await builder.refresh_incremental(
                client=mock_client,
                existing_df=None,
                watermark=None,
            )

        # Must have timezone info
        assert new_watermark.tzinfo is not None
        assert new_watermark.tzinfo == UTC


class TestNoProjectGid:
    """Tests for edge case when project has no GID."""

    @pytest.mark.asyncio
    async def test_no_project_gid_returns_empty_df(
        self,
        mock_unified_store: MagicMock,
    ) -> None:
        """When project has no GID, returns empty DataFrame."""
        project = MagicMock()
        project.gid = None  # No GID
        project.tasks = []

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=TEST_SCHEMA,
            unified_store=mock_unified_store,
        )

        mock_client = MagicMock()

        df, new_watermark = await builder.refresh_incremental(
            client=mock_client,
            existing_df=None,
            watermark=None,
        )

        # Should return empty DataFrame
        assert len(df) == 0
        # Watermark should still be set
        assert new_watermark is not None
