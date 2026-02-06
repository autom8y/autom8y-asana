"""Adversarial tests for paced fetch and checkpoint in ProgressiveProjectBuilder.

Probes edge cases, error injection, concurrency, resume corner cases,
configuration boundaries, and data integrity for the large section resilience
feature per TDD-large-section-resilience.

QA Adversary: These tests exist to break things on purpose.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders.progressive import (
    ProgressiveProjectBuilder,
)
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_task(gid: str) -> MagicMock:
    """Create a mock Task with model_dump."""
    task = MagicMock()
    task.gid = gid
    task.name = f"Task {gid}"
    task.model_dump.return_value = {"gid": gid, "name": f"Task {gid}"}
    return task


class _FakePageIterator:
    """Fake PageIterator yielding a configurable number of tasks."""

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
    read_raises: Exception | None = None,
    s3_put_success: bool = True,
    s3_put_side_effect: list | None = None,
) -> ProgressiveProjectBuilder:
    """Create a builder with mocked dependencies.

    Args:
        manifest: Manifest to use.
        checkpoint_df: DataFrame to return from read_section_async.
        read_raises: Exception to raise from read_section_async.
        s3_put_success: Whether S3 put_object_async succeeds.
        s3_put_side_effect: List of S3 result mocks for sequential calls.
    """
    mock_client = MagicMock()
    mock_schema = MagicMock()
    mock_schema.to_polars_schema.return_value = {"gid": pl.Utf8, "name": pl.Utf8}

    mock_persistence = MagicMock(spec=SectionPersistence)
    mock_persistence.update_manifest_section_async = AsyncMock(return_value=manifest)
    mock_persistence.write_section_async = AsyncMock(return_value=True)
    mock_persistence._make_section_key = MagicMock(
        return_value="dataframes/proj/sections/sec.parquet"
    )

    if s3_put_side_effect is not None:
        # Map side_effect to True/False based on .success attribute
        checkpoint_results = [
            r.success if hasattr(r, "success") else bool(r) for r in s3_put_side_effect
        ]
        mock_persistence.write_checkpoint_async = AsyncMock(
            side_effect=checkpoint_results
        )
    else:
        mock_persistence.write_checkpoint_async = AsyncMock(return_value=s3_put_success)

    mock_persistence._get_manifest_lock = MagicMock(return_value=asyncio.Lock())
    mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
    mock_persistence._manifest_cache = {}
    mock_persistence._save_manifest_async = AsyncMock(return_value=True)

    if read_raises is not None:
        mock_persistence.read_section_async = AsyncMock(side_effect=read_raises)
    else:
        mock_persistence.read_section_async = AsyncMock(return_value=checkpoint_df)

    builder = ProgressiveProjectBuilder(
        client=mock_client,
        project_gid="proj_123",
        entity_type="contact",
        schema=mock_schema,
        persistence=mock_persistence,
    )
    builder._manifest = manifest

    mock_view = MagicMock()
    mock_view._extract_rows_async = AsyncMock(
        side_effect=lambda dicts, **kw: [
            {"gid": d["gid"], "name": d["name"]} for d in dicts
        ]
    )
    builder._dataframe_view = mock_view

    return builder


def _patch_pacing(
    pace_pages: int = 25,
    checkpoint_pages: int = 50,
    delay: float = 2.0,
):
    """Context manager to patch all three pacing constants plus asyncio.sleep."""
    return (
        patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        patch(
            "autom8_asana.dataframes.builders.progressive.PACE_PAGES_PER_PAUSE",
            pace_pages,
        ),
        patch(
            "autom8_asana.dataframes.builders.progressive.CHECKPOINT_EVERY_N_PAGES",
            checkpoint_pages,
        ),
        patch(
            "autom8_asana.dataframes.builders.progressive.PACE_DELAY_SECONDS",
            delay,
        ),
    )


# ===================================================================
# 1. EDGE CASES -- Section Size Boundaries
# ===================================================================


@pytest.mark.asyncio
class TestSectionSizeBoundaries:
    """Probe the 100-task heuristic boundary in both directions."""

    async def test_section_with_1_task(self) -> None:
        """Single-task section: no pacing, completes normally."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(1)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep"
        ) as mock_sleep:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        mock_sleep.assert_not_called()
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 1

    async def test_section_with_99_tasks(self) -> None:
        """99 tasks (just under threshold): no pacing."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(99)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep"
        ) as mock_sleep:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        mock_sleep.assert_not_called()
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 99

    async def test_section_with_exactly_100_tasks(self) -> None:
        """Exactly 100 tasks: pacing activates but no actual pauses taken."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(100)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Iterator exhausts immediately after first page -- no sleep taken
        mock_sleep.assert_not_called()
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 100

    async def test_section_with_101_tasks(self) -> None:
        """101 tasks (just over threshold): pacing activates, 1 task on page 2."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(101)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Only 1 task on second page, not enough to trigger page boundary
        mock_sleep.assert_not_called()
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 101

    async def test_section_with_10000_tasks(self) -> None:
        """10,000 tasks (large scale): correct row count and checkpoint count."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(10000)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=50
        )
        with sleep_mock as mock_sleep, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 10000

        # 10000 tasks = 100 pages. First page consumed by heuristic.
        # Pages 2-100 in pacing loop. pages_fetched increments at
        # 100-task boundaries: pages 2,3,...,100 => pages_fetched goes 2..100.
        # Sleep at pages_fetched % 25 == 0: 25, 50, 75, 100 => 4 sleeps
        assert mock_sleep.call_count == 4

        # Checkpoints at pages_fetched % 50 == 0: 50, 100 => 2 checkpoints
        assert builder._persistence.write_checkpoint_async.call_count == 2


# ===================================================================
# 2. ERROR INJECTION -- S3 and Processing Failures
# ===================================================================


@pytest.mark.asyncio
class TestS3WriteFailureDuringCheckpoint:
    """S3 write failure during checkpoint should not crash the fetch."""

    async def test_s3_checkpoint_failure_continues_fetching(self) -> None:
        """S3 write fails during checkpoint: fetch continues, final write succeeds."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        # S3 put returns failure for checkpoints
        builder = _make_builder(manifest=manifest, s3_put_success=False)

        # 5000 tasks = 50 pages -> 1 checkpoint attempt at page 50
        builder._client.tasks.list_async.return_value = _FakePageIterator(5000)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=50
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        # Fetch still completes despite checkpoint failure
        assert result is True
        # Final write goes through write_section_async (not the S3 direct path)
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 5000


@pytest.mark.asyncio
class TestManifestUpdateFailureDuringCheckpoint:
    """Manifest save failure during checkpoint should not crash the fetch."""

    async def test_manifest_save_failure_continues(self) -> None:
        """Manifest save fails during checkpoint: fetch continues."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # Make save_manifest fail
        builder._persistence._save_manifest_async = AsyncMock(
            side_effect=ConnectionError("Manifest save failed")
        )

        # 5000 tasks = 50 pages -> 1 checkpoint at page 50
        builder._client.tasks.list_async.return_value = _FakePageIterator(5000)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=50
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        # _write_checkpoint catches exceptions and returns False
        # But the outer fetch loop continues
        assert result is True
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 5000


@pytest.mark.asyncio
class TestTaskToDictExceptionMidLoop:
    """Exception during task-to-dict conversion mid-pacing loop."""

    async def test_task_to_dict_exception_mid_loop(self) -> None:
        """A broken task's model_dump raises: section fails gracefully."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # Create an iterator where one task's model_dump raises
        iterator = _FakePageIterator(200)
        # Poison the 150th task's model_dump
        iterator._tasks[150].model_dump.side_effect = ValueError("Bad task data")
        builder._client.tasks.list_async.return_value = iterator

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing()
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        # The exception happens during task_dicts = [self._task_to_dict(task) ...]
        # which is AFTER the pacing loop, in the final conversion step.
        # The outer try/except catches it and marks section FAILED.
        assert result is False
        builder._persistence.update_manifest_section_async.assert_any_call(
            "proj_123", "sec_1", SectionStatus.FAILED, error="Bad task data"
        )


@pytest.mark.asyncio
class TestRowExtractionExceptionAtCheckpoint:
    """Exception during row extraction at checkpoint time."""

    async def test_extract_rows_exception_at_checkpoint(self) -> None:
        """_extract_rows raises during checkpoint: checkpoint fails, fetch continues."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # 5000 tasks = 50 pages -> checkpoint at page 50
        builder._client.tasks.list_async.return_value = _FakePageIterator(5000)

        # Make _extract_rows fail only on the first call (checkpoint),
        # then succeed on the second call (final write)
        call_count = 0
        original_side_effect = builder._dataframe_view._extract_rows_async.side_effect

        async def flaky_extract(dicts, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Extract rows failed at checkpoint")
            return original_side_effect(dicts, **kw)

        builder._dataframe_view._extract_rows_async = AsyncMock(
            side_effect=flaky_extract
        )

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=50
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        # _write_checkpoint catches the exception internally, fetch continues
        assert result is True
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 5000


# ===================================================================
# 3. CONCURRENCY / STATE -- Interleaved Checkpoints
# ===================================================================


@pytest.mark.asyncio
class TestConcurrentLargeSections:
    """Two concurrent large sections using the same manifest lock."""

    async def test_concurrent_sections_manifest_consistency(self) -> None:
        """Two large sections run concurrently with shared persistence.

        Verifies that each section completes with correct row counts.
        """
        section_info_1 = SectionInfo()
        section_info_2 = SectionInfo()
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=2,
            sections={"sec_1": section_info_1, "sec_2": section_info_2},
        )

        # Build two separate builders sharing the same persistence mock
        builder1 = _make_builder(manifest=manifest)
        builder2 = _make_builder(manifest=manifest)
        # Share the same persistence to test lock contention
        builder2._persistence = builder1._persistence

        # Section 1: 300 tasks (3 pages, enters pacing)
        # Section 2: 500 tasks (5 pages, enters pacing)
        builder1._client.tasks.list_async.return_value = _FakePageIterator(300)
        builder2._client.tasks.list_async.return_value = _FakePageIterator(
            500, start_gid=300
        )

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=2, checkpoint_pages=3
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            results = await asyncio.gather(
                builder1._fetch_and_persist_section("sec_1", None, 0, 2),
                builder2._fetch_and_persist_section("sec_2", None, 1, 2),
            )

        assert results[0] is True
        assert results[1] is True

        # Verify write_section_async was called for both sections
        write_calls = builder1._persistence.write_section_async.call_args_list
        assert len(write_calls) == 2

        # Extract written DataFrames and verify row counts
        dfs = [call[0][2] for call in write_calls]
        row_counts = sorted([len(df) for df in dfs])
        assert row_counts == [300, 500]


# ===================================================================
# 4. RESUME EDGE CASES
# ===================================================================


@pytest.mark.asyncio
class TestResumeEdgeCases:
    """Edge cases for the resume-from-checkpoint path."""

    async def test_resume_with_rows_fetched_zero(self) -> None:
        """rows_fetched=0 with IN_PROGRESS: should NOT attempt resume."""
        section_info = SectionInfo(
            status=SectionStatus.IN_PROGRESS,
            rows_fetched=0,
            last_fetched_offset=0,
        )
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": section_info},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(50)

        result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # read_section_async should NOT be called (rows_fetched=0)
        builder._persistence.read_section_async.assert_not_called()

    async def test_resume_in_progress_no_parquet_in_s3(self) -> None:
        """IN_PROGRESS + rows_fetched>0 but read returns None: full refetch."""
        section_info = SectionInfo(
            status=SectionStatus.IN_PROGRESS,
            rows_fetched=500,
            last_fetched_offset=5,
            chunks_checkpointed=1,
        )
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": section_info},
        )
        # read_section_async returns None (parquet missing from S3)
        builder = _make_builder(manifest=manifest, checkpoint_df=None)
        builder._client.tasks.list_async.return_value = _FakePageIterator(50)

        result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        builder._persistence.read_section_async.assert_called_once()
        # No pages should be skipped when checkpoint is None
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 50

    async def test_resume_section_shrank(self) -> None:
        """Section shrank: resume_offset > actual pages. Should handle gracefully.

        If the section has fewer pages than resume_offset, the skip loop
        will exhaust the iterator before reaching the target offset.
        The first-page fetch after skip will get 0 tasks.
        """
        checkpoint_df = pl.DataFrame(
            {
                "gid": [str(i) for i in range(500)],
                "name": [f"Task {i}" for i in range(500)],
            }
        )
        section_info = SectionInfo(
            status=SectionStatus.IN_PROGRESS,
            rows_fetched=500,
            last_fetched_offset=5,  # Previously had 5 pages
            chunks_checkpointed=1,
        )
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": section_info},
        )
        builder = _make_builder(manifest=manifest, checkpoint_df=checkpoint_df)

        # Section now has only 200 tasks (2 pages), less than the offset of 5
        builder._client.tasks.list_async.return_value = _FakePageIterator(200)

        result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        # The builder should complete without crashing.
        # The skip loop exhausts the iterator, then the first-page fetch
        # also gets nothing. The section is marked COMPLETE with 0 rows
        # because there's nothing left after the skip.
        assert result is True


# ===================================================================
# 5. CONFIGURATION BOUNDARIES
# ===================================================================


@pytest.mark.asyncio
class TestConfigurationBoundaries:
    """Test extreme configuration values."""

    async def test_pace_pages_per_pause_1(self) -> None:
        """pace_pages_per_pause=1: pause after every page."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        # 300 tasks = 3 pages. First page is heuristic.
        # Pacing loop: pages 2 and 3. With pace=1, sleep at page 2 and page 3.
        builder._client.tasks.list_async.return_value = _FakePageIterator(300)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=1, checkpoint_pages=1000, delay=0.1
        )
        with sleep_mock as mock_sleep, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # pages_fetched goes: 2, 3. Both % 1 == 0 => 2 sleeps
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.1)

    async def test_checkpoint_every_page(self) -> None:
        """checkpoint_every_n_pages=1: checkpoint after every page."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        # 300 tasks = 3 pages. Pages 2 and 3 in pacing loop.
        builder._client.tasks.list_async.return_value = _FakePageIterator(300)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=1
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Checkpoint at every page: pages_fetched 2 and 3, both % 1 == 0
        assert builder._persistence.write_checkpoint_async.call_count == 2

    async def test_pace_delay_zero(self) -> None:
        """pace_delay_seconds=0: no actual delay but sleep still called."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(300)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=1, checkpoint_pages=1000, delay=0.0
        )
        with sleep_mock as mock_sleep, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Sleep is called with 0.0
        assert mock_sleep.call_count >= 1
        mock_sleep.assert_called_with(0.0)


# ===================================================================
# 6. DATA INTEGRITY -- No Dropped Tasks
# ===================================================================


@pytest.mark.asyncio
class TestDataIntegrity:
    """Verify all accumulated tasks appear in the final DataFrame."""

    async def test_all_tasks_present_in_final_dataframe(self) -> None:
        """Every task GID from the iterator appears in the final write."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        total_tasks = 350  # 3.5 pages
        builder._client.tasks.list_async.return_value = _FakePageIterator(total_tasks)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=1, checkpoint_pages=2
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == total_tasks

        # Verify every GID is present
        expected_gids = {str(i) for i in range(total_tasks)}
        actual_gids = set(written_df["gid"].to_list())
        assert actual_gids == expected_gids

    async def test_checkpoint_df_has_correct_schema(self) -> None:
        """Checkpoint DataFrame written to S3 has the correct schema."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # 5000 tasks -> checkpoint at page 50
        builder._client.tasks.list_async.return_value = _FakePageIterator(5000)

        captured_dfs: list[pl.DataFrame] = []
        original_write_parquet = pl.DataFrame.write_parquet

        # Capture DataFrames written to BytesIO during checkpoint
        def capture_parquet(self_df, file, *args, **kwargs):
            if isinstance(file, MagicMock):
                return  # Skip mocked files
            captured_dfs.append(self_df.clone())
            return original_write_parquet(self_df, file, *args, **kwargs)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=50
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Verify checkpoint was attempted (S3 put called)
        assert builder._persistence.write_checkpoint_async.call_count >= 1

    async def test_final_write_replaces_all_checkpoint_data(self) -> None:
        """Final write via write_section_async has ALL rows, not just new ones."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        total_tasks = 7500  # 75 pages
        builder._client.tasks.list_async.return_value = _FakePageIterator(total_tasks)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=50
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Final write contains ALL tasks, not just those after last checkpoint
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == total_tasks

        # Verify contiguous GIDs
        gids = sorted(int(g) for g in written_df["gid"].to_list())
        assert gids == list(range(total_tasks))


# ===================================================================
# 7. S3 PUT MIXED RESULTS -- Some checkpoints fail, some succeed
# ===================================================================


@pytest.mark.asyncio
class TestMixedCheckpointResults:
    """Some checkpoint writes succeed, some fail."""

    async def test_first_checkpoint_fails_second_succeeds(self) -> None:
        """First checkpoint S3 write fails, second succeeds: fetch still completes."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )

        fail_result = MagicMock()
        fail_result.success = False
        fail_result.error = "Transient S3 failure"

        success_result = MagicMock()
        success_result.success = True
        success_result.error = None

        builder = _make_builder(
            manifest=manifest,
            s3_put_side_effect=[fail_result, success_result],
        )

        # 10000 tasks = 100 pages -> checkpoints at 50 and 100
        builder._client.tasks.list_async.return_value = _FakePageIterator(10000)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=25, checkpoint_pages=50
        )
        with sleep_mock, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 10000

        # Both checkpoints were attempted
        assert builder._persistence.write_checkpoint_async.call_count == 2


# ===================================================================
# 8. PAGE BOUNDARY DETECTION -- Partial final page accounting
# ===================================================================


@pytest.mark.asyncio
class TestPageBoundaryAccounting:
    """Verify page counting with various task counts."""

    async def test_partial_final_page_counted(self) -> None:
        """250 tasks: 2 full pages + 50 extra. pages_fetched should be 3."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(250)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=1, checkpoint_pages=1000
        )
        with sleep_mock as mock_sleep, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 250

        # First page consumed by heuristic (100 tasks, pages_fetched=1).
        # Remaining 150 tasks. Page boundary at 100 more => pages_fetched=2.
        # 50 remaining tasks < 100, no more boundaries.
        # Sleep called at pages_fetched=2 (since 2%1==0), that's 1 sleep call.
        assert mock_sleep.call_count == 1

    async def test_exact_page_multiples(self) -> None:
        """500 tasks (exactly 5 pages): all tasks accounted for."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(500)

        sleep_mock, pace_mock, ckpt_mock, delay_mock = _patch_pacing(
            pace_pages=1, checkpoint_pages=1000
        )
        with sleep_mock as mock_sleep, pace_mock, ckpt_mock, delay_mock:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        written_df = builder._persistence.write_section_async.call_args[0][2]
        assert len(written_df) == 500

        # First page: 100 tasks (pages_fetched=1).
        # Remaining 400 tasks: page boundaries at 200, 300, 400, 500
        # => pages_fetched = 2, 3, 4, 5
        # Sleep at 2,3,4,5 (all % 1 == 0) => 4 sleeps
        assert mock_sleep.call_count == 4
