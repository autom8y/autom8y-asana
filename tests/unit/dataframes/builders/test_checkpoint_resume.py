"""Unit tests for checkpoint resume in ProgressiveProjectBuilder.

Tests resume from checkpoint, missing checkpoint fallback, corrupt checkpoint
fallback, and no resume for PENDING sections per TDD-large-section-resilience
section 9.2.
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


def _make_mock_task(gid: str) -> MagicMock:
    """Create a mock Task with model_dump."""
    task = MagicMock()
    task.gid = gid
    task.name = f"Task {gid}"
    task.model_dump.return_value = {"gid": gid, "name": f"Task {gid}"}
    return task


class _FakePageIterator:
    """Fake PageIterator that yields a configurable number of tasks."""

    def __init__(self, total_tasks: int, start_gid: int = 0) -> None:
        self._tasks = [_make_mock_task(str(i)) for i in range(start_gid, start_gid + total_tasks)]
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
    manifest: SectionManifest,
    checkpoint_df: pl.DataFrame | None = None,
    read_raises: Exception | None = None,
) -> ProgressiveProjectBuilder:
    """Create a builder with mocked dependencies for resume testing."""
    mock_client = MagicMock()
    mock_schema = MagicMock()
    mock_schema.to_polars_schema.return_value = {"gid": pl.Utf8, "name": pl.Utf8}

    mock_persistence = MagicMock(spec=SectionPersistence)
    mock_persistence.update_manifest_section_async = AsyncMock(return_value=manifest)
    mock_persistence.write_section_async = AsyncMock(return_value=True)
    mock_persistence._make_section_key = MagicMock(
        return_value="dataframes/proj/sections/sec.parquet"
    )
    mock_persistence._s3_client = MagicMock()
    mock_s3_result = MagicMock()
    mock_s3_result.success = True
    mock_s3_result.error = None
    mock_persistence._s3_client.put_object_async = AsyncMock(return_value=mock_s3_result)
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
        side_effect=lambda dicts, **kw: [{"gid": d["gid"], "name": d["name"]} for d in dicts]
    )
    builder._dataframe_view = mock_view

    return builder


class TestResumeFromCheckpoint:
    """Resume detection when IN_PROGRESS + rows_fetched > 0 + parquet exists."""

    async def test_resume_from_checkpoint(self) -> None:
        """Builder reads checkpoint and skips already-fetched pages."""
        checkpoint_df = pl.DataFrame(
            {
                "gid": [str(i) for i in range(500)],
                "name": [f"Task {i}" for i in range(500)],
            }
        )
        section_info = SectionInfo(
            status=SectionStatus.IN_PROGRESS,
            rows_fetched=500,
            last_fetched_offset=5,  # 5 pages fetched
            chunks_checkpointed=1,
        )
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": section_info},
        )
        builder = _make_builder(manifest=manifest, checkpoint_df=checkpoint_df)

        # Total 1000 tasks: pages 1-5 (500 tasks) already checkpointed,
        # pages 6-10 (500 tasks) need fetching.
        # The builder will create a fresh iterator with all 1000 tasks,
        # skip the first 5 pages (500 tasks), then fetch the remaining 500.
        builder._client.tasks.list_async.return_value = _FakePageIterator(1000)

        with patch(
            "autom8_asana.dataframes.builders.progressive.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # read_section_async should have been called to read the checkpoint
        builder._persistence.read_section_async.assert_called_once_with("proj_123", "sec_1")


class TestResumeMissingCheckpoint:
    """Missing parquet on resume falls back to full refetch."""

    async def test_resume_missing_checkpoint(self) -> None:
        """Manifest has rows_fetched but parquet missing: full refetch."""
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
        # checkpoint_df=None simulates missing parquet
        builder = _make_builder(manifest=manifest, checkpoint_df=None)

        # Small section to keep test fast
        builder._client.tasks.list_async.return_value = _FakePageIterator(50)

        result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # No pages should be skipped since checkpoint was None
        # Final write should happen normally with 50 tasks
        call_args = builder._persistence.write_section_async.call_args
        written_df = call_args[0][2]
        assert len(written_df) == 50


class TestResumeCorruptCheckpoint:
    """Corrupt parquet on resume falls back to full refetch."""

    async def test_resume_corrupt_checkpoint(self) -> None:
        """Corrupt parquet triggers warning and full refetch."""
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
        builder = _make_builder(
            manifest=manifest,
            read_raises=Exception("Corrupt parquet file"),
        )

        builder._client.tasks.list_async.return_value = _FakePageIterator(50)

        result = await builder._fetch_and_persist_section("sec_1", None, 0, 1)

        assert result is True
        # Falls back to full refetch
        call_args = builder._persistence.write_section_async.call_args
        written_df = call_args[0][2]
        assert len(written_df) == 50


class TestNoResumeForPendingSection:
    """PENDING status should not trigger resume."""

    async def test_no_resume_for_pending_section(self) -> None:
        """Section with PENDING status: no resume attempt."""
        section_info = SectionInfo(status=SectionStatus.PENDING)
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
        # read_section_async should NOT be called for PENDING sections
        builder._persistence.read_section_async.assert_not_called()
