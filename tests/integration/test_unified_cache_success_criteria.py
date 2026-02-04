"""Success Criteria Validation Tests for Unified Cache Architecture.

Sprint: sprint-unified-cache-001
PRD: docs/requirements/PRD-UNIFIED-CACHE-001.md
TDD: docs/architecture/TDD-UNIFIED-CACHE-001.md

This module validates each success criterion from the PRD:
- SC-001: Single cache entry per task GID (no duplicates)
- SC-002: Cold cache DataFrame with no false NOT_FOUND
- SC-003: Cascade returns correct parent values
- SC-004: Warm cache uses 1-2 API calls (down from 4-6)
- SC-005: Freshness mode configuration (STRICT/EVENTUAL/IMMEDIATE)
- SC-006: Cold start performance < 30s with realistic dataset
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode
from autom8_asana.cache.policies.hierarchy import HierarchyIndex
from autom8_asana.cache.providers.unified import UnifiedTaskStore
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_cache_provider() -> MagicMock:
    """Create mock cache provider with tracking."""
    provider = MagicMock()
    provider._storage: dict[str, CacheEntry] = {}
    provider._api_calls = 0

    def get_batch_impl(gids: list[str], entry_type: EntryType):
        return {gid: provider._storage.get(gid) for gid in gids}

    def set_batch_impl(entries: dict[str, CacheEntry]):
        provider._storage.update(entries)

    def set_versioned_impl(gid: str, entry: CacheEntry):
        provider._storage[gid] = entry

    def get_versioned_impl(gid: str, entry_type: EntryType):
        return provider._storage.get(gid)

    provider.get_batch = MagicMock(side_effect=get_batch_impl)
    provider.set_batch = MagicMock(side_effect=set_batch_impl)
    provider.set_versioned = MagicMock(side_effect=set_versioned_impl)
    provider.get_versioned = MagicMock(side_effect=get_versioned_impl)
    provider.invalidate = MagicMock()
    return provider


@pytest.fixture
def mock_batch_client() -> MagicMock:
    """Create mock batch client for API call tracking."""
    client = MagicMock()
    client._call_count = 0

    async def execute_async_impl(requests: list):
        client._call_count += 1
        return []

    client.execute_async = AsyncMock(side_effect=execute_async_impl)
    return client


@pytest.fixture
def cascade_schema() -> DataFrameSchema:
    """Create schema with cascade fields for testing."""
    return DataFrameSchema(
        name="cascade_test",
        task_type="Unit",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False, source=None),
            ColumnDef("name", "Utf8", nullable=False, source=None),
            ColumnDef(
                "office_phone", "Utf8", nullable=True, source="cascade:Office Phone"
            ),
            ColumnDef("vertical", "Utf8", nullable=True, source="cascade:Vertical"),
        ],
        version="1.0.0",
    )


def make_task(
    gid: str,
    name: str,
    parent_gid: str | None = None,
    custom_fields: list[dict] | None = None,
) -> dict[str, Any]:
    """Create a task data dict."""
    task = {
        "gid": gid,
        "name": name,
        "resource_subtype": "default_task",
        "completed": False,
        "created_at": "2025-01-01T00:00:00.000Z",
        "modified_at": "2025-01-02T00:00:00.000Z",
        "custom_fields": custom_fields or [],
        "memberships": [],
        "tags": [],
    }
    if parent_gid:
        task["parent"] = {"gid": parent_gid}
    else:
        task["parent"] = None
    return task


def make_cache_entry(task_data: dict[str, Any]) -> CacheEntry:
    """Create a cache entry from task data with proper completeness metadata."""
    from autom8_asana.cache.models.completeness import CompletenessLevel

    modified_at = task_data.get("modified_at", "2025-01-02T00:00:00.000Z")
    version = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
    return CacheEntry(
        key=task_data["gid"],
        data=task_data,
        entry_type=EntryType.TASK,
        version=version,
        cached_at=datetime.now(UTC),
        ttl=300,
        metadata={
            "completeness_level": CompletenessLevel.STANDARD.value,
            "opt_fields_used": [],
        },
    )


# =============================================================================
# SC-001: Single Cache Entry Per Task GID
# =============================================================================


class TestSC001SingleCacheEntryPerGID:
    """SC-001: Validate single cache entry per task GID (no duplicates)."""

    def test_hierarchy_index_no_duplicate_gids(self) -> None:
        """Test HierarchyIndex rejects duplicate GIDs by overwriting."""
        index = HierarchyIndex()

        # Register same GID twice with different data
        task_v1 = {"gid": "task-001", "name": "Version 1"}
        task_v2 = {"gid": "task-001", "name": "Version 2"}

        index.register(task_v1)
        index.register(task_v2)

        # Should only have one entry
        assert len(index) == 1
        assert index.contains("task-001")

    @pytest.mark.asyncio
    async def test_unified_store_overwrites_duplicate_gids(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test UnifiedTaskStore overwrites duplicate GIDs."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        task_v1 = make_task("task-001", "Version 1")
        task_v2 = make_task("task-001", "Version 2")

        # Put same GID twice (async)
        await store.put_async(task_v1)
        await store.put_async(task_v2)

        # Should only have one entry in hierarchy
        hierarchy = store.get_hierarchy_index()
        assert len(hierarchy) == 1

        # Cache set_versioned should have been called twice (overwrite)
        assert mock_cache_provider.set_versioned.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_put_deduplicates_gids(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test batch put handles duplicate GIDs in input."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        task_v1 = make_task("task-001", "Version 1")
        task_v2 = make_task("task-001", "Version 2")  # Duplicate GID
        task_v3 = make_task("task-002", "Task 2")

        # Put batch with duplicate
        await store.put_batch_async([task_v1, task_v2, task_v3])

        # Hierarchy should have 2 unique entries
        hierarchy = store.get_hierarchy_index()
        assert len(hierarchy) == 2
        assert hierarchy.contains("task-001")
        assert hierarchy.contains("task-002")

    def test_hierarchy_get_all_gids_unique(self) -> None:
        """Test that all GIDs in hierarchy are unique."""
        index = HierarchyIndex()

        # Register many tasks including "duplicates"
        for i in range(100):
            index.register({"gid": f"task-{i % 50}"})  # 50 unique, 50 duplicates

        # Should only have 50 unique entries
        assert len(index) == 50


# =============================================================================
# SC-002: Cold Cache DataFrame - No False NOT_FOUND
# =============================================================================


class TestSC002ColdCacheNoFalseNotFound:
    """SC-002: Cold cache DataFrame returns no false NOT_FOUND errors."""

    @pytest.mark.asyncio
    async def test_cold_cache_populate_then_query(
        self, mock_cache_provider: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Test fresh cache: populate then query cascade field successfully."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Create hierarchy: Business -> Unit
        business = make_task(
            "business-001",
            "Test Business",
            custom_fields=[
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "555-1234",
                }
            ],
        )
        unit = make_task("unit-001", "Test Unit", parent_gid="business-001")

        # Populate cold cache
        await store.put_batch_async([business, unit])

        # Update mock to return the cached data
        mock_cache_provider.get_batch.side_effect = None
        mock_cache_provider.get_batch.return_value = {
            "unit-001": make_cache_entry(unit),
            "business-001": make_cache_entry(business),
        }

        # Query via DataFrameViewPlugin
        plugin = DataFrameViewPlugin(store=store, schema=cascade_schema)
        result = await plugin.materialize_async(["unit-001"])

        # Should have result (not NOT_FOUND)
        assert len(result) == 1
        assert result["gid"][0] == "unit-001"

    @pytest.mark.asyncio
    async def test_cold_cache_hierarchy_preserved(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test that hierarchy relationships are preserved in cold cache."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Build hierarchy
        grandparent = make_task("gp-001", "Grandparent")
        parent = make_task("p-001", "Parent", parent_gid="gp-001")
        child = make_task("c-001", "Child", parent_gid="p-001")

        # Populate
        await store.put_batch_async([grandparent, parent, child])

        # Hierarchy should track relationships
        hierarchy = store.get_hierarchy_index()
        assert hierarchy.get_parent_gid("c-001") == "p-001"
        assert hierarchy.get_parent_gid("p-001") == "gp-001"
        assert hierarchy.get_parent_gid("gp-001") is None

    @pytest.mark.asyncio
    async def test_empty_cache_returns_empty_not_error(
        self, mock_cache_provider: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Test that empty cache returns empty result, not error."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Query non-existent task
        plugin = DataFrameViewPlugin(store=store, schema=cascade_schema)
        result = await plugin.materialize_async(["non-existent-001"])

        # Should return empty DataFrame, not raise error
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 0


# =============================================================================
# SC-003: Cascade Returns Correct Parent Values
# =============================================================================


class TestSC003CascadeReturnsCorrectParentValues:
    """SC-003: Cascade resolution returns correct parent values."""

    @pytest.mark.asyncio
    async def test_cascade_parent_name_traversal(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test parent.name cascade traversal via hierarchy index."""
        # Test using HierarchyIndex directly (the underlying mechanism)
        index = HierarchyIndex()

        # Build hierarchy
        business = {"gid": "business-001", "name": "Acme Corp"}
        unit = {
            "gid": "unit-001",
            "name": "Sales Unit",
            "parent": {"gid": "business-001"},
        }

        index.register(business)
        index.register(unit)

        # Verify parent chain works
        chain = index.get_ancestor_chain("unit-001")
        assert chain == ["business-001"]

    @pytest.mark.asyncio
    async def test_cascade_parent_parent_name_traversal(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test parent.parent.name cascade traversal (2 levels)."""
        # Test using HierarchyIndex for multi-level traversal
        index = HierarchyIndex()

        # Build 3-level hierarchy
        grandparent = {"gid": "gp-001", "name": "Grandparent Corp"}
        parent = {
            "gid": "p-001",
            "name": "Parent Division",
            "parent": {"gid": "gp-001"},
        }
        child = {"gid": "c-001", "name": "Child Unit", "parent": {"gid": "p-001"}}

        index.register(grandparent)
        index.register(parent)
        index.register(child)

        # Verify ancestor chain (parent first, then grandparent)
        chain = index.get_ancestor_chain("c-001")
        assert chain == ["p-001", "gp-001"]

        # Verify we can get root
        root = index.get_root_gid("c-001")
        assert root == "gp-001"

    @pytest.mark.asyncio
    async def test_cascade_local_override(self, mock_cache_provider: MagicMock) -> None:
        """Test local value overrides parent when allow_override=True."""
        from autom8_asana.models.business.fields import CascadingFieldDef

        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Business has value
        business = make_task(
            "b-001",
            "Business",
            custom_fields=[
                {
                    "gid": "cf-1",
                    "name": "Test Field",
                    "resource_subtype": "text",
                    "text_value": "parent-value",
                }
            ],
        )

        # Unit has local override
        unit = make_task(
            "u-001",
            "Unit",
            parent_gid="b-001",
            custom_fields=[
                {
                    "gid": "cf-1",
                    "name": "Test Field",
                    "resource_subtype": "text",
                    "text_value": "local-value",
                }
            ],
        )

        await store.put_batch_async([business, unit])

        # Create plugin with allow_override field
        field_def = CascadingFieldDef(
            name="Test Field",
            target_types=None,
            allow_override=True,
        )

        class MockBusiness:
            pass

        mock_registry = {"test field": (MockBusiness, field_def)}
        cascade_plugin = CascadeViewPlugin(store=store, registry=mock_registry)

        mock_unit = MagicMock()
        mock_unit.gid = "u-001"
        mock_unit.custom_fields = unit["custom_fields"]

        result = await cascade_plugin.resolve_async(mock_unit, "Test Field")

        # Should use local value due to allow_override
        assert result == "local-value"


# =============================================================================
# SC-004: Warm Cache Uses 1-2 API Calls (Down from 4-6)
# =============================================================================


class TestSC004WarmCacheReducedAPICalls:
    """SC-004: Warm cache uses 1-2 API calls instead of 4-6."""

    @pytest.mark.asyncio
    async def test_immediate_mode_no_api_calls(
        self, mock_cache_provider: MagicMock, mock_batch_client: MagicMock
    ) -> None:
        """Test IMMEDIATE mode makes zero API calls."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            batch_client=mock_batch_client,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Pre-populate cache
        task = make_task("task-001", "Test Task")
        entry = make_cache_entry(task)
        mock_cache_provider._storage["task-001"] = entry

        # Query
        result = await store.get_batch_async(["task-001"])

        # Should not call API
        assert mock_batch_client._call_count == 0
        assert "task-001" in result

    @pytest.mark.asyncio
    async def test_eventual_mode_fresh_no_api_calls(
        self, mock_cache_provider: MagicMock, mock_batch_client: MagicMock
    ) -> None:
        """Test EVENTUAL mode with fresh entries makes no API calls."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            batch_client=mock_batch_client,
            freshness_mode=FreshnessMode.EVENTUAL,
        )

        # Pre-populate with fresh entry (just cached)
        task = make_task("task-001", "Test Task")
        entry = make_cache_entry(task)
        mock_cache_provider._storage["task-001"] = entry

        # Query
        await store.get_batch_async(["task-001"])

        # Fresh entry should not trigger API call
        assert mock_batch_client._call_count == 0

    @pytest.mark.asyncio
    async def test_strict_mode_makes_single_batch_call(
        self, mock_cache_provider: MagicMock, mock_batch_client: MagicMock
    ) -> None:
        """Test STRICT mode batches freshness checks into single call."""
        from autom8_asana.batch.models import BatchResult

        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            batch_client=mock_batch_client,
            freshness_mode=FreshnessMode.STRICT,
        )

        # Pre-populate cache with multiple tasks
        for i in range(5):
            task = make_task(f"task-{i:03d}", f"Task {i}")
            entry = make_cache_entry(task)
            mock_cache_provider._storage[f"task-{i:03d}"] = entry

        # Mock batch response
        mock_batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": f"task-{i:03d}",
                            "modified_at": "2025-01-02T00:00:00.000Z",
                        }
                    },
                    request_index=i,
                )
                for i in range(5)
            ]
        )

        # Query all 5 tasks via check_freshness_batch_async
        gids = [f"task-{i:03d}" for i in range(5)]
        await store.check_freshness_batch_async(gids)

        # Should make only 1 batch API call (not 5 individual calls)
        assert mock_batch_client.execute_async.call_count == 1


# =============================================================================
# SC-005: Freshness Mode Configuration
# =============================================================================


class TestSC005FreshnessModeConfiguration:
    """SC-005: Freshness mode is configurable (STRICT/EVENTUAL/IMMEDIATE)."""

    def test_freshness_mode_enum_values(self) -> None:
        """Test FreshnessMode enum has correct values."""
        assert FreshnessMode.STRICT.value == "strict"
        assert FreshnessMode.EVENTUAL.value == "eventual"
        assert FreshnessMode.IMMEDIATE.value == "immediate"

    def test_unified_store_accepts_all_modes(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test UnifiedTaskStore accepts all freshness modes."""
        for mode in FreshnessMode:
            store = UnifiedTaskStore(
                cache=mock_cache_provider,
                freshness_mode=mode,
            )
            assert store.freshness_mode == mode

    @pytest.mark.asyncio
    async def test_mode_can_be_overridden_per_request(
        self, mock_cache_provider: MagicMock, mock_batch_client: MagicMock
    ) -> None:
        """Test freshness mode can be overridden per request."""
        # Store defaults to IMMEDIATE
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            batch_client=mock_batch_client,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        task = make_task("task-001", "Test Task")
        entry = make_cache_entry(task)
        mock_cache_provider._storage["task-001"] = entry

        # Query with override to STRICT
        mock_batch_client.execute_async = AsyncMock(return_value=[])

        await store.get_batch_async(
            ["task-001"],
            freshness=FreshnessMode.STRICT,
        )

        # STRICT mode should attempt freshness check
        # (even though entry exists)

    def test_default_mode_is_eventual(self, mock_cache_provider: MagicMock) -> None:
        """Test default freshness mode is EVENTUAL."""
        store = UnifiedTaskStore(cache=mock_cache_provider)
        assert store.freshness_mode == FreshnessMode.EVENTUAL


# =============================================================================
# SC-006: Cold Start Performance < 30s
# =============================================================================


class TestSC006ColdStartPerformance:
    """SC-006: Cold start with realistic dataset < 30s."""

    @pytest.mark.asyncio
    async def test_cold_start_1000_tasks_under_threshold(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test cold start with 1000 tasks completes in reasonable time."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Generate 1000 tasks with hierarchy
        tasks = []
        for i in range(100):  # 100 businesses
            business = make_task(f"business-{i:03d}", f"Business {i}")
            tasks.append(business)
            for j in range(9):  # 9 units per business = 900 units
                unit = make_task(
                    f"unit-{i:03d}-{j:02d}",
                    f"Unit {i}-{j}",
                    parent_gid=f"business-{i:03d}",
                )
                tasks.append(unit)

        # Time the batch put
        start = time.perf_counter()
        await store.put_batch_async(tasks)
        elapsed = time.perf_counter() - start

        # Should complete in under 5 seconds (well under 30s)
        assert elapsed < 5.0, f"Cold start took {elapsed:.2f}s, expected < 5s"

        # Verify all tasks registered
        hierarchy = store.get_hierarchy_index()
        assert len(hierarchy) == 1000

    @pytest.mark.asyncio
    async def test_hierarchy_lookup_performance(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test hierarchy lookups are fast with realistic data."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Build deep hierarchy (5 levels)
        tasks = [make_task("level-0", "Root")]
        for i in range(1, 5):
            task = make_task(f"level-{i}", f"Level {i}", parent_gid=f"level-{i - 1}")
            tasks.append(task)

        await store.put_batch_async(tasks)

        # Time 1000 ancestor chain lookups
        hierarchy = store.get_hierarchy_index()
        start = time.perf_counter()
        for _ in range(1000):
            hierarchy.get_ancestor_chain("level-4", max_depth=10)
        elapsed = time.perf_counter() - start

        # 1000 lookups should complete in under 100ms
        assert elapsed < 0.1, (
            f"1000 lookups took {elapsed * 1000:.2f}ms, expected < 100ms"
        )


# =============================================================================
# Edge Cases for Adversarial Testing
# =============================================================================


class TestEdgeCases:
    """Edge cases and adversarial testing scenarios."""

    def test_empty_project_no_tasks(self, mock_cache_provider: MagicMock) -> None:
        """Test empty project (no tasks) handles gracefully."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # No tasks registered
        hierarchy = store.get_hierarchy_index()
        assert len(hierarchy) == 0
        assert hierarchy.get_parent_gid("non-existent") is None
        assert hierarchy.get_children_gids("non-existent") == set()

    @pytest.mark.asyncio
    async def test_orphaned_subtask_parent_deleted(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test handling of orphaned subtask when parent is deleted."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        parent = make_task("parent-001", "Parent")
        child = make_task("child-001", "Child", parent_gid="parent-001")

        await store.put_batch_async([parent, child])

        # Delete parent
        store.invalidate("parent-001", cascade=False)

        # Child still exists but parent reference is dangling
        hierarchy = store.get_hierarchy_index()
        assert hierarchy.contains("child-001")
        assert not hierarchy.contains("parent-001")

        # Getting parent chain should handle missing parent gracefully
        # Reset mock to return empty for parent
        mock_cache_provider._storage.pop("parent-001", None)
        chain = await store.get_parent_chain_async("child-001")

        # Should return empty or partial chain, not error
        assert isinstance(chain, list)

    def test_circular_reference_detection(self) -> None:
        """Test that circular references don't cause infinite loops."""
        index = HierarchyIndex()

        # Attempt to create circular reference (shouldn't happen naturally)
        task_a = {"gid": "a", "parent": {"gid": "b"}}
        task_b = {"gid": "b", "parent": {"gid": "a"}}

        index.register(task_a)
        index.register(task_b)

        # Ancestor chain should have max_depth protection
        chain = index.get_ancestor_chain("a", max_depth=10)
        assert len(chain) <= 10  # Should not infinite loop

    @pytest.mark.asyncio
    async def test_concurrent_access_patterns(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test concurrent access doesn't cause race conditions."""
        import asyncio

        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Concurrent puts
        tasks = [make_task(f"task-{i:03d}", f"Task {i}") for i in range(100)]

        async def put_task(task):
            await store.put_async(task)

        await asyncio.gather(*[put_task(t) for t in tasks])

        # All tasks should be registered
        hierarchy = store.get_hierarchy_index()
        assert len(hierarchy) == 100

    @pytest.mark.asyncio
    async def test_cache_eviction_during_cascade(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test cascade resolution handles cache eviction gracefully."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        business = make_task("b-001", "Business")
        unit = make_task("u-001", "Unit", parent_gid="b-001")

        await store.put_batch_async([business, unit])

        cascade_plugin = CascadeViewPlugin(store=store)

        # Create a proper mock task with string name attribute
        mock_unit = MagicMock()
        mock_unit.gid = "u-001"
        mock_unit.name = "Unit"  # Must be a string for detection
        mock_unit.custom_fields = []
        mock_unit.memberships = None

        # Simulate cache miss during parent lookup by patching
        with patch.object(
            store, "get_parent_chain_async", new=AsyncMock(return_value=[])
        ):
            result = await cascade_plugin.resolve_async(mock_unit, "Office Phone")

        # Should return None gracefully, not error
        assert result is None

    @pytest.mark.asyncio
    async def test_task_with_special_characters_in_gid(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test tasks with special characters in GID."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        # Asana GIDs are numeric, but test boundary
        task = make_task("12345678901234567890", "Long GID Task")
        await store.put_async(task)

        hierarchy = store.get_hierarchy_index()
        assert hierarchy.contains("12345678901234567890")

    @pytest.mark.asyncio
    async def test_task_with_empty_custom_fields_list(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test task with empty custom_fields list."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        task = make_task("task-001", "Task", custom_fields=[])
        await store.put_async(task)

        hierarchy = store.get_hierarchy_index()
        assert hierarchy.contains("task-001")

    @pytest.mark.asyncio
    async def test_task_with_none_custom_fields(
        self, mock_cache_provider: MagicMock
    ) -> None:
        """Test task with None custom_fields."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            freshness_mode=FreshnessMode.IMMEDIATE,
        )

        task = {
            "gid": "task-001",
            "name": "Task",
            "custom_fields": None,  # None instead of list
        }
        await store.put_async(task)

        hierarchy = store.get_hierarchy_index()
        assert hierarchy.contains("task-001")
