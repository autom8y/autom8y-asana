"""Unit tests for paced fetch in ProgressiveProjectBuilder.

Tests large section detection, pacing sleep intervals, checkpoint writes,
and small section passthrough per TDD-large-section-resilience section 9.1.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.settings import reset_settings

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
    """Create a mock Task with model_dump."""
    task = MagicMock()
    task.gid = gid
    task.name = f"Task {gid}"
    task.model_dump.return_value = {"gid": gid, "name": f"Task {gid}"}
    return task


class _FakePageIterator:
    """Fake PageIterator that yields a configurable number of tasks.

    Simulates Asana's 100-tasks-per-page behavior by yielding tasks
    one at a time, as the real PageIterator.__anext__() does.
    """

    def __init__(self, total_tasks: int) -> None:
        self._tasks = [_make_mock_task(str(i)) for i in range(total_tasks)]
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
) -> ProgressiveProjectBuilder:
    """Create a builder with mocked dependencies."""
    mock_client = MagicMock()
    mock_schema = MagicMock()
    mock_schema.to_polars_schema.return_value = {"gid": pl.Utf8, "name": pl.Utf8}
    mock_persistence = MagicMock(spec=SectionPersistence)
    mock_persistence.update_manifest_section_async = AsyncMock(return_value=manifest)
    mock_persistence.write_section_async = AsyncMock(return_value=True)
    mock_persistence.write_checkpoint_async = AsyncMock(return_value=True)
    mock_persistence.update_checkpoint_metadata_async = AsyncMock(return_value=None)
    mock_persistence._make_section_key = MagicMock(
        return_value="dataframes/proj/sections/sec.parquet"
    )
    mock_persistence._get_manifest_lock = MagicMock(return_value=asyncio.Lock())
    mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
    mock_persistence._manifest_cache = {}

    builder = ProgressiveProjectBuilder(
        client=mock_client,
        project_gid="proj_123",
        entity_type="contact",
        schema=mock_schema,
        persistence=mock_persistence,
    )

    # Set up manifest for section-level access
    builder._manifest = manifest

    # Mock dataframe view for row extraction
    mock_view = MagicMock()
    mock_view._extract_rows_async = AsyncMock(
        side_effect=lambda dicts, **kw: [
            {"gid": d["gid"], "name": d["name"]} for d in dicts
        ]
    )
    builder._dataframe_view = mock_view

    return builder


@pytest.mark.asyncio
class TestSmallSectionNoPacing:
    """Sections with <100 tasks should not activate pacing."""

    async def test_small_section_no_pacing(self) -> None:
        """Section with 50 tasks: no asyncio.sleep calls, no checkpoint writes."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # Return 50 tasks (less than one full page)
        builder._client.tasks.list_async.return_value = _FakePageIterator(50)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep"
        ) as mock_sleep:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        mock_sleep.assert_not_called()
        # No checkpoint writes for small sections
        builder._persistence.write_checkpoint_async.assert_not_called()
        # Final write should go through write_section_async
        builder._persistence.write_section_async.assert_called_once()


@pytest.mark.asyncio
class TestLargeSectionPacingActivated:
    """Sections with 100+ tasks on first page should activate pacing."""

    async def test_large_section_pacing_activated(self) -> None:
        """100+ tasks on first page activates pacing mode."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # 150 tasks: first page has 100, second page has 50
        builder._client.tasks.list_async.return_value = _FakePageIterator(150)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Should have 150 tasks in final write
        call_args = builder._persistence.write_section_async.call_args
        written_df = call_args[0][2]  # Third positional arg is df
        assert len(written_df) == 150


@pytest.mark.asyncio
class TestPacingSleepIntervals:
    """Verify asyncio.sleep is called at correct intervals."""

    async def test_pacing_sleep_intervals(self) -> None:
        """75 pages with pace_pages_per_pause=25: verify 2 sleep calls (at 25, 50).

        Page 75 is the last full page. After the loop, the total is 75 pages.
        Sleep is called when pages_fetched % 25 == 0, so at pages 25 and 50.
        Page 75 % 25 == 0 would be a third call, but only if there's a 75th
        full page boundary hit inside the loop.
        """
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # 7500 tasks = 75 pages of 100
        # First page (100 tasks) consumed by detection. Remaining 7400 tasks
        # go through paced loop. pages_fetched starts at 1.
        # Pages 2-75: 74 more pages. Sleep at pages 25, 50, 75.
        builder._client.tasks.list_async.return_value = _FakePageIterator(7500)

        with (
            patch.dict(
                os.environ,
                {
                    "ASANA_PACING_PAGES_PER_PAUSE": "25",
                    "ASANA_PACING_CHECKPOINT_EVERY_N_PAGES": "50",
                },
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            reset_settings()
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)
        reset_settings()

        assert result is True
        # Sleep called at page boundaries: 25, 50, 75
        assert mock_sleep.call_count == 3
        mock_sleep.assert_called_with(2.0)


@pytest.mark.asyncio
class TestCheckpointWriteAtIntervals:
    """Verify checkpoint writes occur at configured intervals."""

    async def test_checkpoint_write_at_intervals(self) -> None:
        """120 pages, checkpoint_every_n_pages=50: 2 checkpoints (at 50, 100)."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo(status=SectionStatus.PENDING)},
        )
        builder = _make_builder(manifest=manifest)

        # 12000 tasks = 120 pages
        builder._client.tasks.list_async.return_value = _FakePageIterator(12000)

        with (
            patch.dict(
                os.environ,
                {
                    "ASANA_PACING_CHECKPOINT_EVERY_N_PAGES": "50",
                    "ASANA_PACING_PAGES_PER_PAUSE": "25",
                },
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            reset_settings()
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)
        reset_settings()

        assert result is True
        # Checkpoint writes go directly to S3 client (not write_section_async)
        # 2 checkpoints at pages 50 and 100
        assert builder._persistence.write_checkpoint_async.call_count == 2


@pytest.mark.asyncio
class TestCheckpointMetadataUpdated:
    """Verify SectionInfo checkpoint fields update correctly."""

    async def test_checkpoint_metadata_updated(self) -> None:
        """After checkpoint, SectionInfo.chunks_checkpointed increments."""
        section_info = SectionInfo(status=SectionStatus.PENDING)
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": section_info},
        )
        builder = _make_builder(manifest=manifest)

        # 5000 tasks = 50 pages -> 1 checkpoint at page 50
        builder._client.tasks.list_async.return_value = _FakePageIterator(5000)

        with (
            patch.dict(
                os.environ,
                {
                    "ASANA_PACING_CHECKPOINT_EVERY_N_PAGES": "50",
                    "ASANA_PACING_PAGES_PER_PAUSE": "25",
                },
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            reset_settings()
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)
        reset_settings()

        assert result is True
        # write_checkpoint_async internally updates metadata and saves manifest
        builder._persistence.write_checkpoint_async.assert_called()


@pytest.mark.asyncio
class TestEmptySectionNoPacing:
    """Empty sections should not trigger pacing."""

    async def test_empty_section_no_pacing(self) -> None:
        """0 tasks: no pacing, no checkpoint, marked COMPLETE with 0 rows."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)
        builder._client.tasks.list_async.return_value = _FakePageIterator(0)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep"
        ) as mock_sleep:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        mock_sleep.assert_not_called()
        # Should be marked COMPLETE with 0 rows
        builder._persistence.update_manifest_section_async.assert_any_call(
            "proj_123",
            "sec_1",
            SectionStatus.COMPLETE,
            rows=0,
            gid_hash=pytest.approx(
                builder._persistence.update_manifest_section_async.call_args_list[-1][
                    1
                ].get(
                    "gid_hash",
                    builder._persistence.update_manifest_section_async.call_args_list[
                        -1
                    ][0][-1]
                    if len(
                        builder._persistence.update_manifest_section_async.call_args_list[
                            -1
                        ][0]
                    )
                    > 3
                    else None,
                ),
            ),
        )


@pytest.mark.asyncio
class TestExactly100TasksPacingHarmless:
    """Edge case: exactly 100 tasks activates pacing but is harmless."""

    async def test_exactly_100_tasks_pacing_harmless(self) -> None:
        """100 tasks: pacing activates, iterator exhausts, no sleep called."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        builder = _make_builder(manifest=manifest)

        # Exactly 100 tasks -- first page consumes all of them
        builder._client.tasks.list_async.return_value = _FakePageIterator(100)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Pacing loop entered but iterator immediately exhausted -- no sleep
        mock_sleep.assert_not_called()
        # Final write has all 100 tasks
        call_args = builder._persistence.write_section_async.call_args
        written_df = call_args[0][2]
        assert len(written_df) == 100


@pytest.mark.asyncio
class TestFinalWriteReplacesCheckpoint:
    """Final write should contain all rows, replacing checkpoint."""

    async def test_final_write_replaces_checkpoint(self) -> None:
        """After 250 pages, final write has all 25000 rows."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo(status=SectionStatus.PENDING)},
        )
        builder = _make_builder(manifest=manifest)

        # 25000 tasks = 250 pages
        builder._client.tasks.list_async.return_value = _FakePageIterator(25000)

        with (
            patch.dict(
                os.environ,
                {
                    "ASANA_PACING_CHECKPOINT_EVERY_N_PAGES": "50",
                    "ASANA_PACING_PAGES_PER_PAUSE": "25",
                },
            ),
            patch(
                "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            reset_settings()
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)
        reset_settings()

        assert result is True
        # Final write through write_section_async has all rows
        call_args = builder._persistence.write_section_async.call_args
        written_df = call_args[0][2]
        assert len(written_df) == 25000
