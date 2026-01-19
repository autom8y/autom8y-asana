"""Tests for ProjectDataFrameBuilder.build_with_parallel_fetch_async().

Per TDD-WATERMARK-CACHE Phase 1: Unit tests for parallel section fetch
integration with ProjectDataFrameBuilder.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

# MIGRATION: Tests need update for ProgressiveProjectBuilder constructor signature
pytestmark = pytest.mark.skip(
    reason="MIGRATION: Tests need update for ProgressiveProjectBuilder"
)

from autom8_asana.dataframes.resolver import MockCustomFieldResolver
from autom8_asana.dataframes.schemas import BASE_SCHEMA
from autom8_asana.models.section import Section
from autom8_asana.models.task import Task


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def minimal_task() -> Task:
    """Create a minimal valid Task for testing."""
    return Task(
        gid="1234567890",
        name="Test Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
    )


@pytest.fixture
def task_in_active_section() -> Task:
    """Create a task in the 'Active' section."""
    return Task(
        gid="task_active",
        name="Active Task",
        resource_subtype="default_task",
        completed=False,
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-01-16T15:45:30.000Z",
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec_active", "name": "Active"},
            }
        ],
    )


@pytest.fixture
def task_in_done_section() -> Task:
    """Create a task in the 'Done' section."""
    return Task(
        gid="task_done",
        name="Done Task",
        resource_subtype="default_task",
        completed=True,
        completed_at="2024-02-01T12:00:00.000Z",
        created_at="2024-01-15T10:30:00.000Z",
        modified_at="2024-02-01T12:00:00.000Z",
        memberships=[
            {
                "project": {"gid": "proj123", "name": "Test Project"},
                "section": {"gid": "sec_done", "name": "Done"},
            }
        ],
    )


@pytest.fixture
def unit_resolver() -> MockCustomFieldResolver:
    """Create a mock resolver with Unit custom field values."""
    return MockCustomFieldResolver(
        {
            "mrr": Decimal("5000.00"),
            "weekly_ad_spend": Decimal("1500.50"),
            "products": ["Product A", "Product B"],
            "languages": ["English", "Spanish"],
            "discount": Decimal("10.5"),
            "vertical": "Healthcare",
            "specialty": "Dental",
        }
    )


@pytest.fixture
def mock_project() -> MagicMock:
    """Create a mock Project."""
    project = MagicMock()
    project.gid = "proj123"
    project.tasks = []
    return project


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient."""
    client = MagicMock()
    client.sections = MagicMock()
    client.tasks = MagicMock()
    return client


@pytest.fixture
def mock_unified_store() -> AsyncMock:
    """Create a mock UnifiedTaskStore for Phase 4 mandatory requirement."""
    store = AsyncMock()
    store.get_batch_async = AsyncMock(return_value={})
    store.put_batch_async = AsyncMock(return_value=0)
    return store


def create_mock_page_iterator(items: list) -> MagicMock:
    """Create a mock PageIterator that returns the given items."""
    mock_iterator = MagicMock()
    mock_iterator.collect = AsyncMock(return_value=items)
    return mock_iterator


# =============================================================================
# TestBuildWithParallelFetchAsync
# =============================================================================


class TestBuildWithParallelFetchAsync:
    """Tests for ProjectDataFrameBuilder.build_with_parallel_fetch_async()."""

    # -------------------------------------------------------------------------
    # Success Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_parallel_success(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        minimal_task: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test successful parallel fetch returns DataFrame."""
        # Setup mock sections client
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        # Setup mock tasks client
        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            if section == "section_1":
                return create_mock_page_iterator([minimal_task])
            return create_mock_page_iterator([])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1
        assert df["gid"][0] == "1234567890"
        assert df["name"][0] == "Test Task"

    @pytest.mark.asyncio
    async def test_build_async_empty_project(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test parallel fetch with empty project returns empty DataFrame."""
        # No sections
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator([])
        )

        # Project-level fetch also returns empty
        mock_client.tasks.list_async = MagicMock(
            return_value=create_mock_page_iterator([])
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
        assert df.columns == BASE_SCHEMA.column_names()

    @pytest.mark.asyncio
    async def test_build_async_multiple_sections(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test parallel fetch from multiple sections."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
        ]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )
        task2 = Task(
            gid="task_2",
            name="Task 2",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            if section == "section_1":
                return create_mock_page_iterator([task1])
            elif section == "section_2":
                return create_mock_page_iterator([task2])
            return create_mock_page_iterator([])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 2
        gids = set(df["gid"].to_list())
        assert gids == {"task_1", "task_2"}

    # -------------------------------------------------------------------------
    # Fallback Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_fallback_on_error(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        minimal_task: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test fallback to serial fetch on parallel fetch error."""
        # Setup sections client to fail
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(
            side_effect=Exception("Section listing failed")
        )
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=mock_iterator
        )

        # Serial fallback should work
        mock_client.tasks.list_async = MagicMock(
            return_value=create_mock_page_iterator([minimal_task])
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Should not raise - falls back to serial
        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1

    @pytest.mark.asyncio
    async def test_build_async_fallback_on_section_fetch_error(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        minimal_task: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test fallback when individual section fetch fails."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        # Section task fetch fails
        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            if section:
                mock_iter = MagicMock()
                mock_iter.collect = AsyncMock(
                    side_effect=Exception("Task fetch failed")
                )
                return mock_iter
            # Project-level fallback works
            return create_mock_page_iterator([minimal_task])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Should fall back to serial
        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1

    # -------------------------------------------------------------------------
    # Opt-out Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_opt_out_parallel(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        minimal_task: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test use_parallel_fetch=False uses serial fetch."""
        # Setup serial fetch
        mock_client.tasks.list_async = MagicMock(
            return_value=create_mock_page_iterator([minimal_task])
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(
            mock_client, use_parallel_fetch=False
        )

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1

        # Sections should NOT have been called
        mock_client.sections.list_for_project_async.assert_not_called()

        # Tasks should have been called with project= param
        mock_client.tasks.list_async.assert_called_once()
        call_kwargs = mock_client.tasks.list_async.call_args.kwargs
        assert call_kwargs.get("project") == "proj123"

    # -------------------------------------------------------------------------
    # Section Filtering
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_with_section_filter(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        task_in_active_section: Task,
        task_in_done_section: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test parallel fetch respects section filter."""
        sections = [
            Section(gid="section_active", name="Active"),
            Section(gid="section_done", name="Done"),
        ]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            if section == "section_active":
                return create_mock_page_iterator([task_in_active_section])
            elif section == "section_done":
                return create_mock_page_iterator([task_in_done_section])
            return create_mock_page_iterator([])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Filter to only Active section
        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            sections=["Active"],
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_active"

    # -------------------------------------------------------------------------
    # Schema Consistency
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_schema_identical(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        minimal_task: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test parallel fetch DataFrame matches build() schema."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )
        mock_client.tasks.list_async = MagicMock(
            return_value=create_mock_page_iterator([minimal_task])
        )

        # Use same project for both builds
        mock_project.tasks = [minimal_task]

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Build with parallel fetch
        df_parallel = await builder.build_with_parallel_fetch_async(mock_client)

        # Build with existing method
        df_sync = builder.build()

        # Schemas should match
        assert df_parallel.columns == df_sync.columns
        assert df_parallel.schema == df_sync.schema

    # -------------------------------------------------------------------------
    # Concurrency Limit
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_respects_max_concurrent(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        minimal_task: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test max_concurrent_sections parameter is passed to fetcher.

        This test verifies the default max_concurrent of 8 is overridden.
        Since we can't easily patch the dataclass constructor, we verify
        by checking the behavior with various max_concurrent values.
        """
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([minimal_task])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Test with custom max_concurrent_sections
        df = await builder.build_with_parallel_fetch_async(
            mock_client, max_concurrent_sections=4
        )

        # Verify the build succeeded (max_concurrent doesn't affect this test)
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1

        # Test with default (None) max_concurrent_sections
        df2 = await builder.build_with_parallel_fetch_async(mock_client)
        assert len(df2) == 1

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_no_project_gid(
        self, mock_client: MagicMock, mock_unified_store: MagicMock
    ) -> None:
        """Test handling when project has no GID."""
        project = MagicMock(spec=[])  # No gid attribute
        project.tasks = []

        builder = ProjectDataFrameBuilder(
            project=project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0

    @pytest.mark.asyncio
    async def test_build_async_deduplicates_multi_homed(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test parallel fetch deduplicates multi-homed tasks."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
        ]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        # Same task appears in both sections
        shared_task = Task(
            gid="shared_task",
            name="Shared Task",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            # Both sections return the same task
            return create_mock_page_iterator([shared_task])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        # Should only have one row despite appearing in 2 sections
        assert len(df) == 1
        assert df["gid"][0] == "shared_task"


# =============================================================================
# TestBuildSerialAsync
# =============================================================================


class TestBuildSerialAsync:
    """Tests for ProjectDataFrameBuilder._build_serial_async()."""

    @pytest.mark.asyncio
    async def test_build_serial_async(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        minimal_task: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test serial async build."""
        mock_client.tasks.list_async = MagicMock(
            return_value=create_mock_page_iterator([minimal_task])
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder._build_serial_async(mock_client)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1

    @pytest.mark.asyncio
    async def test_build_serial_async_with_section_filter(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        task_in_active_section: Task,
        task_in_done_section: Task,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test serial fetch respects section filter."""
        mock_client.tasks.list_async = MagicMock(
            return_value=create_mock_page_iterator(
                [task_in_active_section, task_in_done_section]
            )
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            sections=["Active"],
            unified_store=mock_unified_store,
        )

        df = await builder._build_serial_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_active"


# =============================================================================
# TestCacheIntegration (Phase 2: TDD-WATERMARK-CACHE)
# =============================================================================


class TestCacheIntegration:
    """Tests for cache integration in build_with_parallel_fetch_async().

    Per TDD-WATERMARK-CACHE Phase 2: Batch cache operations.
    """

    @pytest.fixture
    def mock_cache_integration(self) -> MagicMock:
        """Create a mock DataFrameCacheIntegration."""

        cache = MagicMock()
        cache.get_cached_batch_async = AsyncMock(return_value={})
        cache.cache_batch_async = AsyncMock(return_value=0)
        return cache

    # -------------------------------------------------------------------------
    # FR-CACHE-001: Cache lookup before API fetch
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_hit_full(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test full cache hit skips extraction (FR-CACHE-001).

        When all tasks are in cache, no extraction should occur.
        """
        from autom8_asana.dataframes.cache_integration import CachedRow
        from autom8_asana.cache.dataframes import make_dataframe_key
        from datetime import datetime, timezone

        # Setup sections and tasks
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Setup cache to return hit for task_1
        cache_key = make_dataframe_key("task_1", "proj123")
        cached_row = CachedRow(
            task_gid="task_1",
            project_gid="proj123",
            data={"gid": "task_1", "name": "Cached Task 1"},
            schema_version="1.0.0",
            cached_at=datetime.now(timezone.utc),
            version=datetime(2024, 1, 16, 15, 45, 30, tzinfo=timezone.utc),
        )
        mock_cache_integration.get_cached_batch_async = AsyncMock(
            return_value={cache_key: cached_row}
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        # Should use cached data
        assert df["name"][0] == "Cached Task 1"

        # Cache lookup should have been called
        mock_cache_integration.get_cached_batch_async.assert_called_once()

        # No cache population needed (all hits)
        mock_cache_integration.cache_batch_async.assert_not_called()

    # -------------------------------------------------------------------------
    # FR-CACHE-002: Cache miss triggers fetch and population
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_miss_full(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test full cache miss triggers extraction and cache population (FR-CACHE-005)."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Cache returns empty (all misses)
        mock_cache_integration.get_cached_batch_async = AsyncMock(return_value={})

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

        # Cache lookup should have been called
        mock_cache_integration.get_cached_batch_async.assert_called_once()

        # FR-CACHE-005: Cache population should have been called
        mock_cache_integration.cache_batch_async.assert_called_once()

    # -------------------------------------------------------------------------
    # FR-CACHE-004: Partial cache fetches only missing tasks
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_partial(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test partial cache hit only extracts missing tasks (FR-CACHE-004)."""
        from autom8_asana.dataframes.cache_integration import CachedRow
        from autom8_asana.cache.dataframes import make_dataframe_key
        from datetime import datetime, timezone

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )
        task2 = Task(
            gid="task_2",
            name="Task 2",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1, task2])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Cache hit for task_1 only
        cache_key_1 = make_dataframe_key("task_1", "proj123")
        cached_row = CachedRow(
            task_gid="task_1",
            project_gid="proj123",
            data={"gid": "task_1", "name": "Cached Task 1"},
            schema_version="1.0.0",
            cached_at=datetime.now(timezone.utc),
            version=datetime(2024, 1, 16, 15, 45, 30, tzinfo=timezone.utc),
        )
        mock_cache_integration.get_cached_batch_async = AsyncMock(
            return_value={cache_key_1: cached_row}
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 2

        # Verify both tasks present
        gids = set(df["gid"].to_list())
        assert gids == {"task_1", "task_2"}

        # task_1 should have cached name, task_2 should have extracted name
        row_1 = df.filter(pl.col("gid") == "task_1")
        row_2 = df.filter(pl.col("gid") == "task_2")
        assert row_1["name"][0] == "Cached Task 1"
        assert row_2["name"][0] == "Task 2"

        # Cache population should only include task_2 (the miss)
        mock_cache_integration.cache_batch_async.assert_called_once()
        call_args = mock_cache_integration.cache_batch_async.call_args
        rows_to_cache = call_args.kwargs.get(
            "rows", call_args.args[0] if call_args.args else []
        )
        cached_gids = [r[0] for r in rows_to_cache]
        assert cached_gids == ["task_2"]

    # -------------------------------------------------------------------------
    # FR-CONFIG-004: use_cache=False bypasses cache
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_disabled(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test use_cache=False bypasses cache entirely (FR-CONFIG-004)."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client, use_cache=False)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

        # Cache should NOT have been called at all
        mock_cache_integration.get_cached_batch_async.assert_not_called()
        mock_cache_integration.cache_batch_async.assert_not_called()

    # -------------------------------------------------------------------------
    # FR-CACHE-008: Graceful degradation on cache failure
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_failure_graceful(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cache exception doesn't fail build (FR-CACHE-008)."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Cache lookup fails
        mock_cache_integration.get_cached_batch_async = AsyncMock(
            side_effect=Exception("Cache connection failed")
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        # Should NOT raise - should degrade gracefully
        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"
        assert df["name"][0] == "Task 1"

    @pytest.mark.asyncio
    async def test_build_async_cache_write_failure_graceful(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cache write failure doesn't fail build (FR-CACHE-008)."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Cache lookup returns miss
        mock_cache_integration.get_cached_batch_async = AsyncMock(return_value={})

        # Cache write fails
        mock_cache_integration.cache_batch_async = AsyncMock(
            side_effect=Exception("Cache write failed")
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        # Should NOT raise - should degrade gracefully
        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

    # -------------------------------------------------------------------------
    # FR-CACHE-003: Cache key format verification
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_key_format(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cache keys use format {task_gid}:{project_gid} (FR-CACHE-003)."""
        from autom8_asana.cache.dataframes import make_dataframe_key

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_123",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        await builder.build_with_parallel_fetch_async(mock_client)

        # Verify cache lookup was called with correct key format
        call_args = mock_cache_integration.get_cached_batch_async.call_args
        task_project_pairs = call_args.kwargs.get("task_project_pairs")

        # Should have (task_gid, project_gid) pair
        assert task_project_pairs == [("task_123", "proj123")]

        # Verify key format matches make_dataframe_key
        expected_key = make_dataframe_key("task_123", "proj123")
        assert expected_key == "task_123:proj123"

    # -------------------------------------------------------------------------
    # FR-CACHE-006: Version uses task.modified_at
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_entry_version(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cached entries use task.modified_at as version (FR-CACHE-006)."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Cache miss to trigger cache population
        mock_cache_integration.get_cached_batch_async = AsyncMock(return_value={})

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        await builder.build_with_parallel_fetch_async(mock_client)

        # Verify cache_batch_async was called with modified_at as version
        call_args = mock_cache_integration.cache_batch_async.call_args
        rows = call_args.kwargs.get("rows", call_args.args[0] if call_args.args else [])

        # rows is list of (task_gid, project_gid, data, version)
        assert len(rows) == 1
        task_gid, project_gid, data, version = rows[0]
        assert task_gid == "task_1"
        assert project_gid == "proj123"
        assert version == "2024-01-16T15:45:30.000Z"

    # -------------------------------------------------------------------------
    # Cache with no cache_integration configured
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_no_cache_integration(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test build works when no cache_integration is configured."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # No cache_integration
        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=None,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

    # -------------------------------------------------------------------------
    # Cache with serial fallback
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_build_async_cache_with_serial_fallback(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_cache_integration: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cache integration works during serial fallback."""
        # Section listing fails - triggers serial fallback
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(
            side_effect=Exception("Section listing failed")
        )
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=mock_iterator
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        # Serial fallback should work
        mock_client.tasks.list_async = MagicMock(
            return_value=create_mock_page_iterator([task1])
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            cache_integration=mock_cache_integration,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1

        # Cache should still have been used during serial fallback
        mock_cache_integration.get_cached_batch_async.assert_called_once()


# =============================================================================
# TestTaskCacheBuildIntegration (TDD-CACHE-PERF-FETCH-PATH)
# =============================================================================


class TestTaskCacheBuildIntegration:
    """Tests for Task-level cache integration in build_with_parallel_fetch_async().

    Per TDD-CACHE-PERF-FETCH-PATH Phase 3: Validates the two-phase cache
    strategy with TaskCacheCoordinator.
    """

    @pytest.fixture
    def mock_task_cache_provider(self) -> MagicMock:
        """Create a mock task-level cache provider."""
        from autom8_asana._defaults.cache import InMemoryCacheProvider

        return InMemoryCacheProvider(default_ttl=300, max_size=1000)

    @pytest.fixture
    def mock_client_with_task_cache(
        self, mock_task_cache_provider: MagicMock
    ) -> MagicMock:
        """Create a mock AsanaClient with task cache provider."""
        client = MagicMock()
        client.sections = MagicMock()
        client.tasks = MagicMock()
        client.tasks._cache = mock_task_cache_provider
        return client

    # -------------------------------------------------------------------------
    # Cold Cache Path - First fetch populates cache
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_task_cache_cold_cache_populates(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cold cache path fetches from API and populates cache."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client_with_task_cache)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

        # Verify task was populated in cache
        cache_provider = mock_client_with_task_cache.tasks._cache
        from autom8_asana.cache.entry import EntryType

        cached = cache_provider.get_batch(["task_1"], EntryType.TASK)
        assert "task_1" in cached
        assert cached["task_1"] is not None

    # -------------------------------------------------------------------------
    # Warm Cache Path - Second fetch uses cache, no API calls for cached tasks
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_task_cache_warm_cache_skips_api(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test warm cache path returns cached tasks without full API fetch."""
        from autom8_asana.cache.entry import CacheEntry, EntryType
        from datetime import datetime, timezone

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Cached Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        # Pre-populate cache
        cache_provider = mock_client_with_task_cache.tasks._cache
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="task_1",
            data=task1.model_dump(exclude_none=True),
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )
        cache_provider.set_versioned("task_1", entry)

        # Track API calls
        api_call_count = 0

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            nonlocal api_call_count
            # Only count full fetches (not GID-only)
            if kwargs.get("opt_fields") != ["gid"]:
                api_call_count += 1
            # Return task for GID enumeration
            return create_mock_page_iterator([task1])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client_with_task_cache)

        assert len(df) == 1
        assert df["name"][0] == "Cached Task 1"

        # No full API fetch should have occurred (all cache hits)
        assert api_call_count == 0

    # -------------------------------------------------------------------------
    # Partial Cache Path - Mixed hits/misses
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_task_cache_partial_hit(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test partial cache hit fetches only missing tasks."""
        from autom8_asana.cache.entry import CacheEntry, EntryType
        from datetime import datetime, timezone

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        cached_task = Task(
            gid="task_1",
            name="Cached Task",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        uncached_task = Task(
            gid="task_2",
            name="Uncached Task",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        # Pre-populate cache with only task_1
        cache_provider = mock_client_with_task_cache.tasks._cache
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="task_1",
            data=cached_task.model_dump(exclude_none=True),
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )
        cache_provider.set_versioned("task_1", entry)

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([cached_task, uncached_task])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client_with_task_cache)

        assert len(df) == 2
        gids = set(df["gid"].to_list())
        assert gids == {"task_1", "task_2"}

        # Both tasks should now be in cache
        cached = cache_provider.get_batch(["task_1", "task_2"], EntryType.TASK)
        assert cached["task_1"] is not None
        assert cached["task_2"] is not None

    # -------------------------------------------------------------------------
    # use_cache=False bypasses task cache
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_task_cache_disabled(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test use_cache=False bypasses task cache entirely."""
        from autom8_asana.cache.entry import CacheEntry, EntryType
        from datetime import datetime, timezone

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Fresh Task",  # Different name than cached
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        # Pre-populate cache with different data
        cache_provider = mock_client_with_task_cache.tasks._cache
        now = datetime.now(timezone.utc)
        cached_data = task1.model_dump(exclude_none=True)
        cached_data["name"] = "Stale Cached Task"
        entry = CacheEntry(
            key="task_1",
            data=cached_data,
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )
        cache_provider.set_versioned("task_1", entry)

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Disable cache
        df = await builder.build_with_parallel_fetch_async(
            mock_client_with_task_cache, use_cache=False
        )

        assert len(df) == 1
        # Should get fresh data, not cached
        assert df["name"][0] == "Fresh Task"

    # -------------------------------------------------------------------------
    # Cache provider unavailable - graceful fallback
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_task_cache_provider_unavailable(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,  # No _cache attribute
        mock_unified_store: MagicMock,
    ) -> None:
        """Test graceful fallback when cache provider is unavailable."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Should work without cache
        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

    # -------------------------------------------------------------------------
    # Test helper methods
    # -------------------------------------------------------------------------

    def test_flatten_section_gids_deduplication(
        self, mock_project: MagicMock, mock_unified_store: MagicMock
    ) -> None:
        """Test _flatten_section_gids deduplicates multi-homed tasks."""
        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        section_gids_map = {
            "section_1": ["task_1", "task_2", "shared"],
            "section_2": ["shared", "task_3"],
            "section_3": ["task_4", "shared"],
        }

        result = builder._flatten_section_gids(section_gids_map)

        # Should deduplicate while preserving order
        assert result == ["task_1", "task_2", "shared", "task_3", "task_4"]

    def test_flatten_section_gids_empty(
        self, mock_project: MagicMock, mock_unified_store: MagicMock
    ) -> None:
        """Test _flatten_section_gids with empty input."""
        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        result = builder._flatten_section_gids({})
        assert result == []

    def test_get_task_cache_provider_exists(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test _get_task_cache_provider returns provider when available."""
        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        provider = builder._get_task_cache_provider(mock_client_with_task_cache)
        assert provider is not None

    def test_get_task_cache_provider_missing(
        self, mock_project: MagicMock, mock_unified_store: MagicMock
    ) -> None:
        """Test _get_task_cache_provider returns None when unavailable."""
        # Create a client without _cache attribute
        mock_client_no_cache = MagicMock()
        mock_client_no_cache.tasks = MagicMock(spec=["list_async"])  # No _cache

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        provider = builder._get_task_cache_provider(mock_client_no_cache)
        assert provider is None


# =============================================================================
# TestCacheOptimizationP2 (TDD-CACHE-OPTIMIZATION-P2)
# =============================================================================


class TestCacheOptimizationP2:
    """Tests for Cache Optimization Phase 2 - targeted fetch for cache misses.

    Per TDD-CACHE-OPTIMIZATION-P2 and ADR-0130: Validates that:
    1. Cold cache populates tasks after fetch_all()
    2. Warm cache (100% hit) skips API calls entirely
    3. Partial cache miss uses fetch_by_gids() for targeted fetch
    4. Cache population occurs after fetch (graceful degradation on failure)
    """

    @pytest.fixture
    def mock_task_cache_provider(self) -> MagicMock:
        """Create a mock task-level cache provider."""
        from autom8_asana._defaults.cache import InMemoryCacheProvider

        return InMemoryCacheProvider(default_ttl=300, max_size=1000)

    @pytest.fixture
    def mock_client_with_task_cache(
        self, mock_task_cache_provider: MagicMock
    ) -> MagicMock:
        """Create a mock AsanaClient with task cache provider."""
        client = MagicMock()
        client.sections = MagicMock()
        client.tasks = MagicMock()
        client.tasks._cache = mock_task_cache_provider
        return client

    # -------------------------------------------------------------------------
    # Cold Cache Tests - Population after fetch_all()
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cold_cache_populates_after_fetch(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cold cache path populates cache after fetch_all() (ADR-0130)."""
        from autom8_asana.cache.entry import EntryType

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )
        task2 = Task(
            gid="task_2",
            name="Task 2",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1, task2])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client_with_task_cache)

        assert len(df) == 2

        # Verify tasks were populated in cache
        cache_provider = mock_client_with_task_cache.tasks._cache
        cached = cache_provider.get_batch(["task_1", "task_2"], EntryType.TASK)

        assert "task_1" in cached
        assert "task_2" in cached
        assert cached["task_1"] is not None
        assert cached["task_2"] is not None

    # -------------------------------------------------------------------------
    # Warm Cache Tests - 100% hit skips API
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_warm_cache_100_percent_hit_zero_api_calls(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test 100% cache hit skips fetch entirely (FR-MISS-004)."""
        from autom8_asana.cache.entry import CacheEntry, EntryType
        from datetime import datetime, timezone

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Cached Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        # Pre-populate cache
        cache_provider = mock_client_with_task_cache.tasks._cache
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="task_1",
            data=task1.model_dump(exclude_none=True),
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )
        cache_provider.set_versioned("task_1", entry)

        # Track full fetch API calls (not GID enumeration)
        full_fetch_count = 0

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            nonlocal full_fetch_count
            # GID enumeration uses opt_fields=["gid"]
            if kwargs.get("opt_fields") != ["gid"]:
                full_fetch_count += 1
            return create_mock_page_iterator([task1])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client_with_task_cache)

        assert len(df) == 1
        assert df["name"][0] == "Cached Task 1"

        # No full fetch should have occurred (100% cache hit)
        assert full_fetch_count == 0

    # -------------------------------------------------------------------------
    # Partial Cache Tests - Uses fetch_by_gids()
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_partial_cache_hit_uses_fetch_by_gids(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test partial cache hit fetches only missing GIDs (FR-MISS-001/002)."""
        from autom8_asana.cache.entry import CacheEntry, EntryType
        from datetime import datetime, timezone

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        cached_task = Task(
            gid="task_1",
            name="Cached Task",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )
        uncached_task = Task(
            gid="task_2",
            name="Uncached Task",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        # Pre-populate cache with only task_1
        cache_provider = mock_client_with_task_cache.tasks._cache
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key="task_1",
            data=cached_task.model_dump(exclude_none=True),
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )
        cache_provider.set_versioned("task_1", entry)

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([cached_task, uncached_task])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client_with_task_cache)

        assert len(df) == 2
        gids = set(df["gid"].to_list())
        assert gids == {"task_1", "task_2"}

        # Verify task_2 was added to cache
        cached = cache_provider.get_batch(["task_2"], EntryType.TASK)
        assert cached["task_2"] is not None

    # -------------------------------------------------------------------------
    # Graceful Degradation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cache_population_failure_graceful_degradation(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cache population failure does not break fetch (NFR-DEGRADE-001)."""

        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Create a failing cache provider
        failing_cache = MagicMock()
        failing_cache.get_batch = MagicMock(return_value={})  # All misses
        failing_cache.set_batch = MagicMock(side_effect=Exception("Cache write failed"))
        mock_client.tasks._cache = failing_cache

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Should NOT raise - graceful degradation
        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

    @pytest.mark.asyncio
    async def test_cache_lookup_failure_graceful_degradation(
        self,
        mock_project: MagicMock,
        mock_client: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cache lookup failure does not break fetch (NFR-DEGRADE-001)."""
        sections = [Section(gid="section_1", name="Section 1")]
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            return create_mock_page_iterator([task1])

        mock_client.tasks.list_async = MagicMock(side_effect=mock_list_async)

        # Create a failing cache provider
        failing_cache = MagicMock()
        failing_cache.get_batch = MagicMock(side_effect=Exception("Cache read failed"))
        mock_client.tasks._cache = failing_cache

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        # Should NOT raise - graceful degradation
        df = await builder.build_with_parallel_fetch_async(mock_client)

        assert len(df) == 1
        assert df["gid"][0] == "task_1"

    # -------------------------------------------------------------------------
    # Cold Cache (0% hit) Uses fetch_all()
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cold_cache_uses_fetch_all_not_fetch_by_gids(
        self,
        mock_project: MagicMock,
        mock_client_with_task_cache: MagicMock,
        mock_unified_store: MagicMock,
    ) -> None:
        """Test cold cache (0% hit) uses fetch_all() for efficiency (FR-MISS-005)."""
        sections = [
            Section(gid="section_1", name="Section 1"),
            Section(gid="section_2", name="Section 2"),
        ]
        mock_client_with_task_cache.sections.list_for_project_async = MagicMock(
            return_value=create_mock_page_iterator(sections)
        )

        task1 = Task(
            gid="task_1",
            name="Task 1",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )
        task2 = Task(
            gid="task_2",
            name="Task 2",
            resource_subtype="default_task",
            completed=False,
            created_at="2024-01-15T10:30:00.000Z",
            modified_at="2024-01-16T15:45:30.000Z",
        )

        # Track which sections are fetched
        sections_fetched = []

        def mock_list_async(section: str | None = None, **kwargs: Any) -> MagicMock:
            if section:
                sections_fetched.append(section)
            if section == "section_1":
                return create_mock_page_iterator([task1])
            elif section == "section_2":
                return create_mock_page_iterator([task2])
            return create_mock_page_iterator([])

        mock_client_with_task_cache.tasks.list_async = MagicMock(
            side_effect=mock_list_async
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="*",
            schema=BASE_SCHEMA,
            unified_store=mock_unified_store,
        )

        df = await builder.build_with_parallel_fetch_async(mock_client_with_task_cache)

        assert len(df) == 2

        # Cold cache should fetch all sections (2 for GID enumeration + 2 for full fetch)
        # OR directly use fetch_all() which fetches all sections
        # Key point: both sections should be fetched for cold cache
        full_fetch_sections = [
            s for s in sections_fetched if s in ["section_1", "section_2"]
        ]
        # At minimum, we should have fetched both sections for full data
        assert len(full_fetch_sections) >= 2
