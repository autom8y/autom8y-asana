"""Unit tests for ProgressiveProjectBuilder.

Tests progressive project building with section-level S3 persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders.progressive import (
    ProgressiveBuildResult,
    ProgressiveProjectBuilder,
    build_project_progressive_async,
)
from autom8_asana.dataframes.section_persistence import (
    SectionManifest,
    SectionInfo,
    SectionPersistence,
    SectionStatus,
)


class TestProgressiveBuildResult:
    """Tests for ProgressiveBuildResult dataclass."""

    def test_create_result(self) -> None:
        """Result contains all expected fields."""
        df = pl.DataFrame({"gid": ["1", "2"]})
        watermark = datetime.now(timezone.utc)

        result = ProgressiveBuildResult(
            df=df,
            watermark=watermark,
            total_rows=100,
            sections_fetched=5,
            sections_resumed=3,
            fetch_time_ms=500.0,
            total_time_ms=1000.0,
        )

        assert len(result.df) == 2
        assert result.total_rows == 100
        assert result.sections_fetched == 5
        assert result.sections_resumed == 3
        assert result.fetch_time_ms == 500.0
        assert result.total_time_ms == 1000.0


class TestProgressiveProjectBuilderInit:
    """Tests for ProgressiveProjectBuilder initialization."""

    def test_init(self) -> None:
        """Builder initializes with required parameters."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock()

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        assert builder._project_gid == "proj_123"
        assert builder._entity_type == "offer"
        assert builder._max_concurrent == 8  # default

    def test_init_custom_concurrency(self) -> None:
        """Builder accepts custom concurrency limit."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock()

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
            max_concurrent_sections=16,
        )

        assert builder._max_concurrent == 16


class TestTaskToDict:
    """Tests for task dict conversion."""

    def test_task_with_model_dump(self) -> None:
        """Tasks with model_dump use it."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock()

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"gid": "task_1", "name": "Test Task"}

        result = builder._task_to_dict(mock_task)

        assert result == {"gid": "task_1", "name": "Test Task"}
        mock_task.model_dump.assert_called_once()

    def test_task_without_model_dump(self) -> None:
        """Tasks without model_dump use attribute access."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock()

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        # Task without model_dump
        mock_task = MagicMock(spec=["gid", "name"])
        mock_task.gid = "task_1"
        mock_task.name = "Test Task"

        result = builder._task_to_dict(mock_task)

        assert result["gid"] == "task_1"
        assert result["name"] == "Test Task"


class TestBuildIndexData:
    """Tests for GidLookupIndex building."""

    def test_build_index_success(self) -> None:
        """Index builds successfully from DataFrame."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock()

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        # DataFrame with required columns for index
        df = pl.DataFrame({
            "gid": ["1", "2"],
            "office_phone": ["555-1234", "555-5678"],
            "vertical": ["sales", "marketing"],
        })

        with patch(
            "autom8_asana.services.gid_lookup.GidLookupIndex"
        ) as mock_index_class:
            mock_index = MagicMock()
            mock_index.serialize.return_value = {"entries": {}}
            mock_index_class.from_dataframe.return_value = mock_index

            result = builder._build_index_data(df)

            assert result == {"entries": {}}
            mock_index_class.from_dataframe.assert_called_once_with(df)

    def test_build_index_failure(self) -> None:
        """Index build failure returns None."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock()

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        df = pl.DataFrame({"gid": ["1", "2"]})

        with patch(
            "autom8_asana.services.gid_lookup.GidLookupIndex"
        ) as mock_index_class:
            mock_index_class.from_dataframe.side_effect = KeyError("missing column")

            result = builder._build_index_data(df)

            assert result is None


@pytest.mark.asyncio
class TestProgressiveBuild:
    """Tests for progressive build process."""

    async def test_build_no_sections(self) -> None:
        """Build with no sections returns empty result."""
        mock_client = MagicMock()
        mock_client.sections.list_for_project_async.return_value.collect = AsyncMock(
            return_value=[]
        )
        mock_schema = MagicMock()
        mock_persistence = MagicMock(spec=SectionPersistence)

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        # Mock _ensure_dataframe_view
        builder._ensure_dataframe_view = AsyncMock()

        result = await builder.build_progressive_async()

        assert len(result.df) == 0
        assert result.total_rows == 0
        assert result.sections_fetched == 0
        assert result.sections_resumed == 0

    async def test_build_with_resume(self) -> None:
        """Build resumes from existing manifest."""
        mock_client = MagicMock()

        # Mock sections
        mock_section = MagicMock()
        mock_section.gid = "sec_1"
        mock_client.sections.list_for_project_async.return_value.collect = AsyncMock(
            return_value=[mock_section]
        )

        mock_schema = MagicMock()
        mock_schema.version = "1.0.0"  # Set schema version for compatibility check

        # Mock persistence with completed manifest
        mock_persistence = MagicMock(spec=SectionPersistence)
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=1,
            completed_sections=1,
            schema_version="1.0.0",  # Must match mock_schema.version for resume
            sections={
                "sec_1": SectionInfo(status=SectionStatus.COMPLETE, rows=100),
            },
        )
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        # Mock dataframe view
        builder._ensure_dataframe_view = AsyncMock()
        builder._build_index_data = MagicMock(return_value=None)

        result = await builder.build_progressive_async(resume=True)

        # Should resume, not fetch
        assert result.sections_resumed == 1
        assert result.sections_fetched == 0

    async def test_build_fresh_start(self) -> None:
        """Build starts fresh when no manifest exists."""
        mock_client = MagicMock()

        # Mock sections
        mock_section = MagicMock()
        mock_section.gid = "sec_1"
        mock_client.sections.list_for_project_async.return_value.collect = AsyncMock(
            return_value=[mock_section]
        )

        # Mock task fetch
        mock_task = MagicMock()
        mock_task.gid = "task_1"
        mock_task.name = "Test Task"
        mock_task.model_dump = MagicMock(return_value={"gid": "task_1", "name": "Test Task"})
        mock_client.tasks.list_async.return_value.collect = AsyncMock(
            return_value=[mock_task]
        )

        mock_schema = MagicMock()

        # Mock persistence with no existing manifest
        mock_persistence = MagicMock(spec=SectionPersistence)
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)

        new_manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        mock_persistence.create_manifest_async = AsyncMock(return_value=new_manifest)
        mock_persistence.update_manifest_section_async = AsyncMock(return_value=new_manifest)
        mock_persistence.write_section_async = AsyncMock(return_value=True)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["task_1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="offer",
            schema=mock_schema,
            persistence=mock_persistence,
        )

        # Mock dataframe view
        mock_view = MagicMock()
        mock_view._extract_rows_async = AsyncMock(
            return_value=[{"gid": "task_1", "name": "Test Task"}]
        )
        builder._dataframe_view = mock_view
        builder._ensure_dataframe_view = AsyncMock()
        builder._build_index_data = MagicMock(return_value=None)

        result = await builder.build_progressive_async(resume=True)

        # Should create manifest and fetch section
        mock_persistence.create_manifest_async.assert_called_once()
        assert result.sections_resumed == 0


@pytest.mark.asyncio
class TestConvenienceFunction:
    """Tests for build_project_progressive_async convenience function."""

    async def test_convenience_function(self) -> None:
        """Convenience function creates builder and runs build."""
        mock_client = MagicMock()
        mock_client.sections.list_for_project_async.return_value.collect = AsyncMock(
            return_value=[]
        )
        mock_schema = MagicMock()
        mock_persistence = MagicMock(spec=SectionPersistence)

        with patch(
            "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder"
        ) as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build_progressive_async = AsyncMock(
                return_value=ProgressiveBuildResult(
                    df=pl.DataFrame(),
                    watermark=datetime.now(timezone.utc),
                    total_rows=0,
                    sections_fetched=0,
                    sections_resumed=0,
                    fetch_time_ms=0,
                    total_time_ms=0,
                )
            )
            mock_builder_class.return_value = mock_builder

            result = await build_project_progressive_async(
                client=mock_client,
                project_gid="proj_123",
                entity_type="offer",
                schema=mock_schema,
                persistence=mock_persistence,
                resume=True,
            )

            mock_builder_class.assert_called_once()
            mock_builder.build_progressive_async.assert_called_once_with(resume=True)
            assert result.total_rows == 0


@pytest.mark.asyncio
class TestPopulateStoreWithTasks:
    """Tests for _populate_store_with_tasks cascade warming."""

    async def test_populate_store_uses_batch_with_warming(self) -> None:
        """Progressive builder should use put_batch_async with warm_hierarchy=True.

        Per ADR-cascade-field-resolution: Hierarchy warming ensures parent tasks
        (Business, UnitHolder) are fetched and cached so cascade fields like
        office_phone and vertical resolve correctly.
        """
        mock_client = MagicMock()
        mock_client.tasks = MagicMock()  # tasks_client for hierarchy warming
        mock_schema = MagicMock()
        mock_persistence = MagicMock(spec=SectionPersistence)
        mock_store = AsyncMock()
        mock_store.put_batch_async = AsyncMock(return_value=5)

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="unit",
            schema=mock_schema,
            persistence=mock_persistence,
            store=mock_store,
        )

        # Create mock tasks
        mock_task = MagicMock()
        mock_task.gid = "task_1"
        mock_task.model_dump.return_value = {
            "gid": "task_1",
            "name": "Test Unit",
            "parent": {"gid": "parent_1"},
            "custom_fields": [],
        }

        await builder._populate_store_with_tasks([mock_task])

        # Verify put_batch_async was called with warm_hierarchy=True
        mock_store.put_batch_async.assert_called_once()
        call_kwargs = mock_store.put_batch_async.call_args.kwargs
        assert call_kwargs.get("warm_hierarchy") is True
        assert call_kwargs.get("tasks_client") is mock_client.tasks

    async def test_populate_store_empty_list(self) -> None:
        """Empty task list skips store population."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock(spec=SectionPersistence)
        mock_store = AsyncMock()

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="unit",
            schema=mock_schema,
            persistence=mock_persistence,
            store=mock_store,
        )

        await builder._populate_store_with_tasks([])

        # Should not call put_batch_async for empty list
        mock_store.put_batch_async.assert_not_called()

    async def test_populate_store_no_store(self) -> None:
        """No store skips population gracefully."""
        mock_client = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock(spec=SectionPersistence)

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="unit",
            schema=mock_schema,
            persistence=mock_persistence,
            store=None,  # No store
        )

        mock_task = MagicMock()
        mock_task.gid = "task_1"

        # Should not raise, just return
        await builder._populate_store_with_tasks([mock_task])

    async def test_populate_store_handles_exception(self) -> None:
        """Store population failure doesn't crash build."""
        mock_client = MagicMock()
        mock_client.tasks = MagicMock()
        mock_schema = MagicMock()
        mock_persistence = MagicMock(spec=SectionPersistence)
        mock_store = AsyncMock()
        mock_store.put_batch_async = AsyncMock(side_effect=Exception("S3 error"))

        builder = ProgressiveProjectBuilder(
            client=mock_client,
            project_gid="proj_123",
            entity_type="unit",
            schema=mock_schema,
            persistence=mock_persistence,
            store=mock_store,
        )

        mock_task = MagicMock()
        mock_task.gid = "task_1"
        mock_task.model_dump.return_value = {"gid": "task_1", "name": "Test"}

        # Should not raise, just log warning
        await builder._populate_store_with_tasks([mock_task])
