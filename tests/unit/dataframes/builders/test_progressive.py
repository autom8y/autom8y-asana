"""Unit tests for ProgressiveProjectBuilder delta checkpoint extraction.

Tests IMP-22 (delta checkpoint extraction) and IMP-15 (double task-to-dict
elimination). Validates that the delta approach produces identical DataFrames
to full extraction, per R5 comparison requirement.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from autom8_asana.dataframes.builders.progressive import (
    ProgressiveProjectBuilder,
)
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)


def _make_mock_task(gid: str) -> MagicMock:
    """Create a mock Task with model_dump and gid attribute."""
    task = MagicMock()
    task.gid = gid
    task.name = f"Task {gid}"
    task.model_dump.return_value = {
        "gid": gid,
        "name": f"Task {gid}",
        "custom_fields": [],
    }
    return task


class _FakePageIterator:
    """Fake PageIterator that yields a configurable number of tasks."""

    def __init__(self, total_tasks: int, start_gid: int = 0) -> None:
        self._tasks = [
            _make_mock_task(str(i)) for i in range(start_gid, start_gid + total_tasks)
        ]
        self._index = 0

    def __aiter__(self) -> _FakePageIterator:
        return self

    async def __anext__(self) -> MagicMock:
        if self._index >= len(self._tasks):
            raise StopAsyncIteration
        task = self._tasks[self._index]
        self._index += 1
        return task


def _make_builder(
    *,
    manifest: SectionManifest | None = None,
    checkpoint_df: pl.DataFrame | None = None,
) -> ProgressiveProjectBuilder:
    """Create a builder with mocked dependencies for delta checkpoint testing."""
    mock_client = MagicMock()
    mock_schema = MagicMock()
    mock_schema.version = "1.0.0"
    mock_schema.to_polars_schema.return_value = {"gid": pl.Utf8, "name": pl.Utf8}

    mock_persistence = MagicMock(spec=SectionPersistence)
    mock_persistence.update_manifest_section_async = AsyncMock(
        return_value=manifest or _make_manifest()
    )
    mock_persistence.write_section_async = AsyncMock(return_value=True)
    mock_persistence.write_checkpoint_async = AsyncMock(return_value=True)
    mock_persistence.read_section_async = AsyncMock(return_value=checkpoint_df)
    mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)

    if manifest is None:
        manifest = _make_manifest()

    builder = ProgressiveProjectBuilder(
        client=mock_client,
        project_gid="proj_123",
        entity_type="contact",
        schema=mock_schema,
        persistence=mock_persistence,
    )

    builder._manifest = manifest

    # Mock DataFrameView to return rows based on task dicts
    mock_view = MagicMock()
    mock_view._extract_rows_async = AsyncMock(
        side_effect=lambda dicts, **kw: [
            {"gid": d["gid"], "name": d["name"]} for d in dicts
        ]
    )
    builder._dataframe_view = mock_view

    return builder


def _make_manifest(
    sections: dict[str, SectionInfo] | None = None,
) -> SectionManifest:
    """Create a manifest for testing."""
    return SectionManifest(
        project_gid="proj_123",
        entity_type="contact",
        total_sections=1,
        sections=sections or {"sec_1": SectionInfo(status=SectionStatus.PENDING)},
    )


@pytest.mark.asyncio
class TestDeltaCheckpointProducesIdenticalDataframe:
    """R5 comparison test: delta extraction must equal full extraction."""

    async def test_delta_checkpoint_produces_identical_dataframe(self) -> None:
        """Verify delta checkpoint + final build equals full extraction.

        Creates 300 tasks (3 pages of 100). Sets CHECKPOINT_EVERY_N_PAGES=2
        so a checkpoint fires after page 2 (200 tasks). Then the final build
        handles the remaining 100 tasks via branch (a).

        Compares the delta result against a full extraction of all 300 tasks.
        """
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(300)]

        # Run 1: Full extraction (branch c -- no checkpoint state)
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        full_df, full_hash, _ = await builder._build_section_dataframe(tasks)

        # Run 2: Simulate delta extraction path
        # First, write a checkpoint at task 200 (as _write_checkpoint would)
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        await builder._write_checkpoint("sec_1", tasks[:200], pages_fetched=2)

        # Now build the final DataFrame with all 300 tasks
        # _build_section_dataframe should take branch (a): delta + concat
        delta_df, delta_hash, _ = await builder._build_section_dataframe(tasks)

        # Assert: identical DataFrames
        assert_frame_equal(full_df, delta_df)
        assert full_hash == delta_hash
        assert len(delta_df) == 300

    async def test_delta_with_multiple_checkpoints(self) -> None:
        """Multiple checkpoints accumulate correctly.

        500 tasks, checkpoints at 200 and 400, final build handles remaining 100.
        """
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(500)]

        # Full extraction for comparison
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        full_df, _, _ = await builder._build_section_dataframe(tasks)

        # Delta path: two checkpoints then final build
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        await builder._write_checkpoint("sec_1", tasks[:200], pages_fetched=2)
        assert builder._checkpoint_task_count == 200
        assert builder._checkpoint_df is not None
        assert len(builder._checkpoint_df) == 200

        await builder._write_checkpoint("sec_1", tasks[:400], pages_fetched=4)
        assert builder._checkpoint_task_count == 400
        assert len(builder._checkpoint_df) == 400

        delta_df, _, _ = await builder._build_section_dataframe(tasks)

        assert_frame_equal(full_df, delta_df)
        assert len(delta_df) == 500

    async def test_delta_no_tasks_after_checkpoint(self) -> None:
        """All tasks already checkpointed -- branch (b).

        200 tasks, checkpoint at 200, no remaining tasks.
        """
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(200)]

        # Full extraction for comparison
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        full_df, _, _ = await builder._build_section_dataframe(tasks)

        # Delta path: checkpoint covers all tasks
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        await builder._write_checkpoint("sec_1", tasks, pages_fetched=2)
        assert builder._checkpoint_task_count == 200

        # Final build should take branch (b)
        delta_df, _, _ = await builder._build_section_dataframe(tasks)

        assert_frame_equal(full_df, delta_df)
        assert len(delta_df) == 200


@pytest.mark.asyncio
class TestDeltaCheckpointState:
    """Tests for delta checkpoint state management."""

    async def test_checkpoint_state_initialized_to_empty(self) -> None:
        """Builder starts with no checkpoint state."""
        builder = _make_builder()
        assert builder._checkpoint_df is None
        assert builder._checkpoint_task_count == 0

    async def test_checkpoint_state_reset_per_section(self) -> None:
        """Delta state resets at the start of each section fetch (R5)."""
        builder = _make_builder()

        # Simulate leftover state from a previous section
        builder._checkpoint_df = pl.DataFrame({"gid": ["old"], "name": ["Old Task"]})
        builder._checkpoint_task_count = 999

        # Set up a small section fetch
        builder._client.tasks.list_async.return_value = _FakePageIterator(50)

        await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        # After section fetch, the delta state should have been reset
        # (it was reset at the start, before any processing)
        # The section_dfs should have the new section's data
        assert "sec_1" in builder._section_dfs
        assert len(builder._section_dfs["sec_1"]) == 50

    async def test_write_checkpoint_updates_delta_state(self) -> None:
        """_write_checkpoint updates _checkpoint_df and _checkpoint_task_count."""
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(200)]

        assert builder._checkpoint_df is None
        assert builder._checkpoint_task_count == 0

        await builder._write_checkpoint("sec_1", tasks, pages_fetched=2)

        assert builder._checkpoint_df is not None
        assert len(builder._checkpoint_df) == 200
        assert builder._checkpoint_task_count == 200

    async def test_write_checkpoint_extracts_only_delta(self) -> None:
        """Second checkpoint only extracts new tasks, not all tasks."""
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(400)]

        # First checkpoint: 200 tasks
        await builder._write_checkpoint("sec_1", tasks[:200], pages_fetched=2)

        # Spy on _extract_rows to verify only delta tasks are extracted
        extract_calls = []
        original_extract = builder._dataframe_view._extract_rows_async.side_effect

        async def capturing_extract(dicts, **kw):
            extract_calls.append(len(dicts))
            return original_extract(dicts, **kw)

        builder._dataframe_view._extract_rows_async.side_effect = capturing_extract

        # Second checkpoint: 400 tasks total, should only extract 200 new ones
        await builder._write_checkpoint("sec_1", tasks, pages_fetched=4)

        assert extract_calls == [200]
        assert len(builder._checkpoint_df) == 400
        assert builder._checkpoint_task_count == 400


@pytest.mark.asyncio
class TestDeltaBuildSectionDataframe:
    """Tests for _build_section_dataframe delta branches."""

    async def test_branch_a_checkpoint_with_remaining_tasks(self) -> None:
        """Branch (a): checkpoint exists and more tasks remain."""
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(300)]

        # Set up checkpoint state (as if 200 tasks were already checkpointed)
        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        await builder._write_checkpoint("sec_1", tasks[:200], pages_fetched=2)

        df, _, _ = await builder._build_section_dataframe(tasks)
        assert len(df) == 300

    async def test_branch_b_checkpoint_covers_all_tasks(self) -> None:
        """Branch (b): checkpoint exists and no new tasks."""
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(200)]

        builder._checkpoint_df = None
        builder._checkpoint_task_count = 0
        await builder._write_checkpoint("sec_1", tasks, pages_fetched=2)

        # Spy on _extract_rows -- should NOT be called for branch (b)
        extract_calls = []
        original_extract = builder._dataframe_view._extract_rows_async.side_effect

        async def capturing_extract(dicts, **kw):
            extract_calls.append(len(dicts))
            return original_extract(dicts, **kw)

        builder._dataframe_view._extract_rows_async.side_effect = capturing_extract

        df, _, _ = await builder._build_section_dataframe(tasks)
        assert len(df) == 200
        # No extraction should have occurred -- reuses checkpoint directly
        assert extract_calls == []

    async def test_branch_c_no_checkpoint(self) -> None:
        """Branch (c): no checkpoint, full extraction."""
        builder = _make_builder()
        tasks = [_make_mock_task(str(i)) for i in range(150)]

        # No checkpoint state
        assert builder._checkpoint_df is None
        assert builder._checkpoint_task_count == 0

        df, _, _ = await builder._build_section_dataframe(tasks)
        assert len(df) == 150


@pytest.mark.asyncio
class TestDeltaCheckpointEndToEnd:
    """End-to-end tests through _fetch_and_persist_section with checkpoints."""

    async def test_large_section_with_checkpoint(self) -> None:
        """Large section triggers checkpoint, final build uses delta.

        300 tasks (3 pages), checkpoint every 2 pages.
        """
        builder = _make_builder()
        builder._client.tasks.list_async.return_value = _FakePageIterator(300)

        with (
            patch(
                "autom8_asana.dataframes.builders.progressive.CHECKPOINT_EVERY_N_PAGES",
                2,
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Checkpoint should have been written
        builder._persistence.write_checkpoint_async.assert_called_once()
        # Final section should have been written with all 300 rows
        call_args = builder._persistence.write_section_async.call_args
        written_df = call_args[0][2]
        assert len(written_df) == 300

    async def test_small_section_no_checkpoint(self) -> None:
        """Small section (< 100 tasks) takes the fast path with no checkpoint."""
        builder = _make_builder()
        builder._client.tasks.list_async.return_value = _FakePageIterator(50)

        result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # No checkpoint for small sections
        builder._persistence.write_checkpoint_async.assert_not_called()
        # Delta state should still be clean (reset at top, no checkpoints)
        # Final section should have 50 rows
        call_args = builder._persistence.write_section_async.call_args
        written_df = call_args[0][2]
        assert len(written_df) == 50


@pytest.mark.asyncio
class TestPopulateStoreDoesNotUseCheckpointState:
    """Verify _populate_store_with_tasks is independent of delta state."""

    async def test_populate_store_calls_task_to_dict_independently(self) -> None:
        """_populate_store_with_tasks calls _task_to_dict on its own,
        separate from the DataFrame extraction pipeline."""
        builder = _make_builder()
        mock_store = MagicMock()
        mock_store.put_batch_async = AsyncMock()
        builder._store = mock_store

        tasks = [_make_mock_task(str(i)) for i in range(5)]

        # Set up checkpoint state as if we already processed some tasks
        builder._checkpoint_task_count = 3
        builder._checkpoint_df = pl.DataFrame(
            {"gid": ["0", "1", "2"], "name": ["Task 0", "Task 1", "Task 2"]}
        )

        # _populate_store_with_tasks should process ALL tasks regardless
        await builder._populate_store_with_tasks(tasks)

        # Verify put_batch_async was called with all 5 tasks
        mock_store.put_batch_async.assert_called_once()
        task_dicts = mock_store.put_batch_async.call_args[0][0]
        assert len(task_dicts) == 5
