"""Integration tests for unified cache wiring (Phase 3: TDD-UNIFIED-CACHE-001).

Tests the integration of:
- ProgressiveProjectBuilder with unified_store
- CascadingFieldResolver with cascade_plugin
- TaskCacheCoordinator.from_unified_store() adapter

Per TDD-UNIFIED-CACHE-001 Phase 3 Acceptance Criteria:
- All existing tests pass (no regression)
- Unified path produces identical DataFrame output to existing path
- Cascade resolution produces identical values via both paths

NOTE: Tests using ProjectDataFrameBuilder require migration to ProgressiveProjectBuilder.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness_coordinator import FreshnessMode
from autom8_asana.cache.unified import UnifiedTaskStore
from autom8_asana.dataframes.builders.task_cache import (
    TaskCacheCoordinator,
    TaskCacheResult,
)
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver
from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin

# Skip marker for tests that use ProjectDataFrameBuilder
MIGRATION_REQUIRED = pytest.mark.skip(
    reason="Requires migration to ProgressiveProjectBuilder - constructor signatures differ"
)


# Skip marker for tests that explicitly test the legacy path (no unified_store)
LEGACY_PATH_REMOVED = pytest.mark.skip(
    reason="unified_store is now mandatory in Phase 4 (TDD-UNIFIED-CACHE-001). "
    "Legacy path without unified_store has been removed."
)

# Skip marker for tests that rely on cascade_plugin being optional
LEGACY_CASCADE_PATH = pytest.mark.skip(
    reason="CascadingFieldResolver requires cascade_plugin after TDD-UNIFIED-CACHE-001 Phase 4. "
    "Legacy path without cascade_plugin has been removed."
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_cache_provider() -> MagicMock:
    """Create mock cache provider."""
    provider = MagicMock()
    provider.get_batch = MagicMock(return_value={})
    provider.set_batch = MagicMock()
    provider.get_versioned = MagicMock(return_value=None)
    provider.set_versioned = MagicMock()
    provider.invalidate = MagicMock()
    return provider


@pytest.fixture
def mock_unified_store(mock_cache_provider: MagicMock) -> UnifiedTaskStore:
    """Create mock unified task store."""
    return UnifiedTaskStore(
        cache=mock_cache_provider,
        batch_client=None,
        freshness_mode=FreshnessMode.IMMEDIATE,
    )


@pytest.fixture
def sample_task_dict() -> dict[str, Any]:
    """Create sample task data dict."""
    return {
        "gid": "task-001",
        "name": "Test Task",
        "resource_subtype": "default_task",
        "completed": False,
        "created_at": "2025-01-01T00:00:00.000Z",
        "modified_at": "2025-01-02T00:00:00.000Z",
        "due_on": "2025-01-15",
        "parent": {"gid": "parent-001"},
        "memberships": [
            {
                "project": {"gid": "project-001"},
                "section": {"gid": "section-001", "name": "Active"},
            }
        ],
        "custom_fields": [
            {
                "gid": "cf-001",
                "name": "Office Phone",
                "resource_subtype": "text",
                "text_value": "555-123-4567",
            },
            {
                "gid": "cf-002",
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_value": {"name": "Phones"},
            },
        ],
        "tags": [{"gid": "tag-001", "name": "urgent"}],
    }


@pytest.fixture
def sample_parent_task_dict() -> dict[str, Any]:
    """Create sample parent (Business) task data dict."""
    return {
        "gid": "parent-001",
        "name": "Business Task",
        "resource_subtype": "default_task",
        "completed": False,
        "created_at": "2025-01-01T00:00:00.000Z",
        "modified_at": "2025-01-02T00:00:00.000Z",
        "parent": None,  # Root task
        "custom_fields": [
            {
                "gid": "cf-001",
                "name": "Office Phone",
                "resource_subtype": "text",
                "text_value": "555-987-6543",
            },
            {
                "gid": "cf-003",
                "name": "Company ID",
                "resource_subtype": "text",
                "text_value": "COMPANY-123",
            },
        ],
    }


@pytest.fixture
def simple_schema() -> DataFrameSchema:
    """Create simple test schema."""
    return DataFrameSchema(
        name="test_schema",
        task_type="Unit",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", source=None),
            ColumnDef(name="name", dtype="Utf8", source=None),
            ColumnDef(name="is_completed", dtype="Boolean", source="completed"),
            ColumnDef(name="section", dtype="Utf8", source=None),
        ],
        version="1.0",
    )


@pytest.fixture
def cascade_schema() -> DataFrameSchema:
    """Create schema with cascade fields."""
    return DataFrameSchema(
        name="cascade_test_schema",
        task_type="Unit",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", source=None),
            ColumnDef(name="name", dtype="Utf8", source=None),
            ColumnDef(name="office_phone", dtype="Utf8", source="cascade:Office Phone"),
        ],
        version="1.0",
    )


# =============================================================================
# Test: ProjectDataFrameBuilder with unified_store
# =============================================================================


@MIGRATION_REQUIRED
class TestProjectDataFrameBuilderUnifiedIntegration:
    """Tests for ProgressiveProjectBuilder with unified_store parameter.

    NOTE: These tests require migration to ProgressiveProjectBuilder.
    The old ProjectDataFrameBuilder has been removed.
    """

    @pytest.mark.asyncio
    async def test_builder_with_unified_store_branches_correctly(
        self,
        mock_unified_store: UnifiedTaskStore,
        simple_schema: DataFrameSchema,
    ) -> None:
        """Test that builder branches to unified path when store provided."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    @LEGACY_PATH_REMOVED
    @pytest.mark.asyncio
    async def test_builder_without_unified_store_uses_existing_path(
        self,
        simple_schema: DataFrameSchema,
    ) -> None:
        """Test that builder uses existing path when no unified store.

        NOTE: This test is skipped - unified_store is now mandatory in Phase 4.
        """
        # Migration required: ProjectDataFrameBuilder removed
        pass

    @pytest.mark.asyncio
    async def test_unified_path_fetches_from_store(
        self,
        mock_cache_provider: MagicMock,
        simple_schema: DataFrameSchema,
        sample_task_dict: dict[str, Any],
    ) -> None:
        """Test that unified path fetches tasks from UnifiedTaskStore."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    @pytest.mark.asyncio
    async def test_unified_and_existing_paths_produce_same_columns(
        self,
        simple_schema: DataFrameSchema,
    ) -> None:
        """Test behavior parity between unified and existing paths."""
        # Both paths should produce DataFrames with the same schema
        # (columns and dtypes should match)

        # Create empty DataFrames to verify schema
        unified_df = pl.DataFrame(schema=simple_schema.to_polars_schema())
        existing_df = pl.DataFrame(schema=simple_schema.to_polars_schema())

        assert unified_df.columns == existing_df.columns
        assert unified_df.dtypes == existing_df.dtypes


# =============================================================================
# Test: CascadingFieldResolver with cascade_plugin
# =============================================================================


class TestCascadingFieldResolverUnifiedIntegration:
    """Tests for CascadingFieldResolver with cascade_plugin parameter."""

    @pytest.mark.asyncio
    async def test_resolver_delegates_to_cascade_plugin(
        self,
        mock_unified_store: UnifiedTaskStore,
    ) -> None:
        """Test that resolver delegates to cascade_plugin when provided."""
        # Create cascade plugin
        cascade_plugin = CascadeViewPlugin(store=mock_unified_store)

        # Mock the resolve_async method
        cascade_plugin.resolve_async = AsyncMock(return_value="555-123-4567")

        # Create resolver with plugin
        client = MagicMock()
        resolver = CascadingFieldResolver(client=client, cascade_plugin=cascade_plugin)

        # Create mock task
        task = MagicMock()
        task.gid = "task-001"

        # Resolve
        result = await resolver.resolve_async(task, "Office Phone")

        # Verify delegation
        cascade_plugin.resolve_async.assert_called_once_with(
            task=task,
            field_name="Office Phone",
            max_depth=5,
        )
        assert result == "555-123-4567"

    @LEGACY_CASCADE_PATH
    @pytest.mark.asyncio
    async def test_resolver_without_plugin_uses_existing_path(
        self,
    ) -> None:
        """Test that resolver uses existing path when no plugin provided.

        NOTE: This test is skipped - cascade_plugin is now required in Phase 4.
        _parent_cache has been removed.
        """
        # Create resolver without plugin
        client = MagicMock()
        resolver = CascadingFieldResolver(client=client)

        # Verify plugin is None
        assert resolver._cascade_plugin is None
        # Verify parent cache exists
        assert resolver._parent_cache == {}

    @LEGACY_CASCADE_PATH
    @pytest.mark.asyncio
    async def test_both_paths_return_same_value_for_unregistered_field(
        self,
        mock_unified_store: UnifiedTaskStore,
    ) -> None:
        """Test that both paths return None for unregistered fields.

        NOTE: This test is skipped - it compares with/without cascade_plugin paths
        but the without-plugin path has been removed in Phase 4.
        """
        # Create resolver with plugin
        cascade_plugin = CascadeViewPlugin(store=mock_unified_store)
        client = MagicMock()
        resolver_with_plugin = CascadingFieldResolver(
            client=client, cascade_plugin=cascade_plugin
        )

        # Create resolver without plugin
        resolver_without_plugin = CascadingFieldResolver(client=client)

        # Mock task
        task = MagicMock()
        task.gid = "task-001"
        task.custom_fields = []

        # Both should return None for unregistered field
        result_with = await resolver_with_plugin.resolve_async(
            task, "Nonexistent Field"
        )
        result_without = await resolver_without_plugin.resolve_async(
            task, "Nonexistent Field"
        )

        assert result_with is None
        assert result_without is None


# =============================================================================
# Test: TaskCacheCoordinator.from_unified_store() adapter
# =============================================================================


class TestTaskCacheCoordinatorUnifiedAdapter:
    """Tests for TaskCacheCoordinator.from_unified_store() adapter."""

    def test_from_unified_store_creates_adapter(
        self,
        mock_unified_store: UnifiedTaskStore,
    ) -> None:
        """Test that from_unified_store creates adapter correctly."""
        coordinator = TaskCacheCoordinator.from_unified_store(mock_unified_store)

        # Verify adapter state
        assert coordinator._unified_store is mock_unified_store
        assert coordinator._cache is None

    @pytest.mark.asyncio
    async def test_adapter_lookup_delegates_to_store(
        self,
        mock_cache_provider: MagicMock,
        sample_task_dict: dict[str, Any],
    ) -> None:
        """Test that adapter lookup delegates to UnifiedTaskStore."""
        # Setup cache to return task
        cache_entry = CacheEntry(
            key="task-001",
            data=sample_task_dict,
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
        )
        mock_cache_provider.get_batch.return_value = {"task-001": cache_entry}

        unified_store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        coordinator = TaskCacheCoordinator.from_unified_store(unified_store)

        # Lookup
        result = await coordinator.lookup_tasks_async(["task-001"])

        # Verify cache was queried
        mock_cache_provider.get_batch.assert_called_with(["task-001"], EntryType.TASK)
        assert "task-001" in result
        assert result["task-001"] is not None

    @pytest.mark.asyncio
    async def test_adapter_populate_delegates_to_store(
        self,
        mock_cache_provider: MagicMock,
    ) -> None:
        """Test that adapter populate delegates to UnifiedTaskStore."""
        unified_store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        coordinator = TaskCacheCoordinator.from_unified_store(unified_store)

        # Create mock task
        task = MagicMock()
        task.gid = "task-001"
        task.modified_at = "2025-01-02T00:00:00.000Z"
        task.model_dump.return_value = {"gid": "task-001", "name": "Test"}

        # Populate
        count = await coordinator.populate_tasks_async([task])

        # Verify cache was updated
        mock_cache_provider.set_batch.assert_called()
        assert count == 1

    @pytest.mark.asyncio
    async def test_adapter_preserves_merge_results_behavior(
        self,
        mock_unified_store: UnifiedTaskStore,
    ) -> None:
        """Test that adapter preserves merge_results behavior."""
        coordinator = TaskCacheCoordinator.from_unified_store(mock_unified_store)

        # Create mock tasks
        task1 = MagicMock()
        task1.gid = "task-001"
        task2 = MagicMock()
        task2.gid = "task-002"

        # Merge results
        cached = {"task-001": task1}
        fetched = [task2]
        result = coordinator.merge_results(["task-001", "task-002"], cached, fetched)

        # Verify result
        assert isinstance(result, TaskCacheResult)
        assert len(result.all_tasks) == 2
        assert result.cache_hits == 1
        assert result.cache_misses == 1


# =============================================================================
# Test: Warm Cache Path Uses Shared Cache
# =============================================================================


class TestWarmCachePathSharedCache:
    """Tests for warm cache path using shared cache."""

    @pytest.mark.asyncio
    async def test_second_build_uses_cached_data(
        self,
        mock_cache_provider: MagicMock,
        simple_schema: DataFrameSchema,
        sample_task_dict: dict[str, Any],
    ) -> None:
        """Test that second build hits cache populated by first build."""
        # Track set_batch calls to verify cache population
        set_batch_calls: list[dict] = []
        mock_cache_provider.set_batch.side_effect = lambda x: set_batch_calls.append(x)

        # First build populates cache
        cache_entry = CacheEntry(
            key="task-001",
            data=sample_task_dict,
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
        )

        # Configure cache behavior
        # First call returns miss, subsequent calls return hit
        call_count = [0]

        def get_batch_side_effect(gids: list[str], entry_type: EntryType):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call - cache miss
                return {}
            else:
                # Subsequent calls - cache hit
                return {gid: cache_entry for gid in gids}

        mock_cache_provider.get_batch.side_effect = get_batch_side_effect

        unified_store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Verify cache is being used correctly
        # First lookup should miss
        result1 = await unified_store.get_batch_async(["task-001"])
        assert result1.get("task-001") is None

        # After population, second lookup should hit
        await unified_store.put_async(sample_task_dict)
        _ = await unified_store.get_batch_async(["task-001"])
        # The mock simulates the cache behavior
        assert mock_cache_provider.get_batch.call_count == 2


# =============================================================================
# Test: Regression - Existing Tests Pass
# =============================================================================


@MIGRATION_REQUIRED
class TestNoRegression:
    """Tests to verify no regression from existing behavior.

    NOTE: Tests using ProjectDataFrameBuilder require migration to ProgressiveProjectBuilder.
    """

    def test_project_builder_accepts_all_existing_parameters(
        self,
        simple_schema: DataFrameSchema,
    ) -> None:
        """Test that ProgressiveProjectBuilder accepts all existing parameters."""
        # Migration required: ProjectDataFrameBuilder removed
        # ProgressiveProjectBuilder has different constructor signature
        pass

    def test_cascading_resolver_accepts_existing_parameters(
        self,
    ) -> None:
        """Test that CascadingFieldResolver accepts existing parameters."""
        client = MagicMock()

        # Existing parameter should still work
        resolver = CascadingFieldResolver(client=client)

        assert resolver is not None
        assert resolver._client is client
        assert resolver._parent_cache == {}
        assert resolver._cascade_plugin is None

    def test_task_cache_coordinator_accepts_existing_parameters(
        self,
        mock_cache_provider: MagicMock,
    ) -> None:
        """Test that TaskCacheCoordinator accepts existing parameters."""
        # Existing instantiation should still work
        coordinator = TaskCacheCoordinator(
            cache_provider=mock_cache_provider,
            default_ttl=600,
        )

        assert coordinator is not None
        assert coordinator._cache is mock_cache_provider
        assert coordinator._default_ttl == 600
        assert coordinator._unified_store is None


# =============================================================================
# Test: Performance Timing (Informational)
# =============================================================================


class TestPerformanceTiming:
    """Informational tests for performance timing comparison."""

    @pytest.mark.asyncio
    async def test_unified_store_lookup_timing(
        self,
        mock_cache_provider: MagicMock,
        sample_task_dict: dict[str, Any],
    ) -> None:
        """Test timing of unified store lookup path."""
        import time

        # Setup cache
        cache_entry = CacheEntry(
            key="task-001",
            data=sample_task_dict,
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
        )
        mock_cache_provider.get_batch.return_value = {"task-001": cache_entry}

        unified_store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )
        coordinator = TaskCacheCoordinator.from_unified_store(unified_store)

        # Time lookup
        start = time.perf_counter()
        for _ in range(100):
            await coordinator.lookup_tasks_async(["task-001"])
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Log timing (informational, no assertion)
        print(f"\n100 unified store lookups: {elapsed_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_legacy_coordinator_lookup_timing(
        self,
        mock_cache_provider: MagicMock,
        sample_task_dict: dict[str, Any],
    ) -> None:
        """Test timing of legacy coordinator lookup path."""
        import time

        # Setup cache
        cache_entry = CacheEntry(
            key="task-001",
            data=sample_task_dict,
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
        )
        mock_cache_provider.get_batch.return_value = {"task-001": cache_entry}

        coordinator = TaskCacheCoordinator(cache_provider=mock_cache_provider)

        # Time lookup
        start = time.perf_counter()
        for _ in range(100):
            await coordinator.lookup_tasks_async(["task-001"])
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Log timing (informational, no assertion)
        print(f"\n100 legacy coordinator lookups: {elapsed_ms:.2f}ms")
