"""Integration test for Unit cascade field resolution.

This test validates the complete cascade resolution flow WITHOUT mocking
the cascade field values. It uses actual parent hierarchy traversal.

Per PRD FR-004: "Create test that validates end-to-end cascade field resolution."
Per TDD-unit-cascade-resolution-fix: Validates Fix 1 and Fix 2 correctness.
"""

from __future__ import annotations

import pytest

from autom8_asana._defaults.cache import InMemoryCacheProvider
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.cache.providers.unified import UnifiedTaskStore
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
from tests._shared.mocks import MockTask

# Test data: Simulated Business -> Unit hierarchy
BUSINESS_TASK = {
    "gid": "business-001",
    "name": "Test Business",
    "parent": None,  # Business is root
    "modified_at": "2026-01-06T12:00:00Z",
    "custom_fields": [
        {
            "gid": "cf-phone",
            "name": "Office Phone",
            "resource_subtype": "text",
            "text_value": "+15551234567",
            "display_value": "+15551234567",
        },
        {
            "gid": "cf-vertical",
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_value": {"gid": "ev-chiro", "name": "Chiropractic"},
            "display_value": "Chiropractic",
        },
    ],
}

UNIT_TASKS = [
    {
        "gid": "unit-001",
        "name": "Unit Task 1",
        "parent": {"gid": "business-001"},
        "modified_at": "2026-01-06T12:00:00Z",
        "custom_fields": [],  # No local cascade fields - must resolve from parent
    },
    {
        "gid": "unit-002",
        "name": "Unit Task 2",
        "parent": {"gid": "business-001"},
        "modified_at": "2026-01-06T12:00:00Z",
        "custom_fields": [],
    },
]


class MockTasksClient:
    """Mock TasksClient that returns Business task when requested."""

    def __init__(self) -> None:
        self.call_count = 0
        self.fetched_gids: list[str] = []

    async def get_async(
        self, gid: str, opt_fields: list[str] | None = None, raw: bool = False
    ) -> MockTask | None:
        self.call_count += 1
        self.fetched_gids.append(gid)
        if gid == "business-001":
            return MockTask(_data=BUSINESS_TASK)
        return None


class TestHierarchyContainsVsCache:
    """Test that hierarchy registration doesn't imply data is cached."""

    def test_unit_registered_but_parent_not_cached(self) -> None:
        """Verify parent task data is not cached when only child is registered.

        Per TDD-unit-cascade-resolution-fix: When a Unit is registered,
        the hierarchy knows about the parent relationship (via get_parent_gid),
        but the parent's TASK DATA is not cached. This is the core issue that
        causes cascade resolution to fail.
        """
        # Setup: Create store with in-memory cache
        cache = InMemoryCacheProvider()
        store = UnifiedTaskStore(cache=cache)

        # Register a Unit - we know about the parent relationship
        unit = {
            "gid": "unit-1",
            "parent": {"gid": "business-1"},
            "modified_at": "2026-01-06T12:00:00Z",
        }
        store._hierarchy.register(unit)

        # The hierarchy knows the parent relationship
        assert store._hierarchy.get_parent_gid("unit-1") == "business-1"

        # But business-1 is NOT cached (no task data fetched)
        cached = store.cache.get_versioned("business-1", EntryType.TASK)
        assert cached is None, "Business task should not be cached - only relationship is known"

        # The ancestor chain returns the parent GID (we know the relationship)
        chain = store._hierarchy.get_ancestor_chain("unit-1")
        assert chain == ["business-1"], "Hierarchy knows the parent GID"


class TestImmediateParentFetch:
    """Test that put_batch_async fetches uncached parents."""

    async def test_put_batch_fetches_uncached_parents(self) -> None:
        """put_batch_async should fetch parents not in cache.

        Per TDD-unit-cascade-resolution-fix Fix 1: The cache check (not
        hierarchy.contains()) should trigger parent fetch.
        """
        # Setup
        cache = InMemoryCacheProvider()
        store = UnifiedTaskStore(cache=cache)
        mock_client = MockTasksClient()

        # Act: Store Unit tasks with hierarchy warming
        await store.put_batch_async(
            UNIT_TASKS,
            tasks_client=mock_client,
            warm_hierarchy=True,
        )

        # Verify: Business was fetched
        assert mock_client.call_count >= 1, "Business should have been fetched"
        assert "business-001" in mock_client.fetched_gids

        # Verify: Business is now cached
        cached = store.cache.get_versioned("business-001", EntryType.TASK)
        assert cached is not None, "Business should be cached after warming"
        assert cached.data["custom_fields"][0]["text_value"] == "+15551234567"


class TestCascadeResolution:
    """Test cascade field resolution through parent hierarchy."""

    async def test_cascade_resolution_populates_fields(self) -> None:
        """Test that cascade fields are populated from Business parent.

        This test validates:
        1. Unit tasks are stored with warm_hierarchy=True
        2. Business parent is fetched and cached
        3. Cascade resolution extracts office_phone from Business
        4. Cascade resolution extracts vertical from Business

        Per SC-002: "Unit DataFrame contains populated office_phone column"
        Per SC-003: "Unit DataFrame contains populated vertical column"
        """
        # Setup: Create store with in-memory cache
        cache = InMemoryCacheProvider()
        store = UnifiedTaskStore(cache=cache)
        mock_client = MockTasksClient()

        # Act: Store Unit tasks with hierarchy warming
        await store.put_batch_async(
            UNIT_TASKS,
            tasks_client=mock_client,
            warm_hierarchy=True,
        )

        # Verify: Business was fetched and cached
        hierarchy = store.get_hierarchy_index()
        assert hierarchy.contains("business-001"), "Business should be in hierarchy"

        # Verify: Parent chain works
        chain = await store.get_parent_chain_async("unit-001")
        assert len(chain) == 1, f"Expected 1 parent, got {len(chain)}"
        assert chain[0]["gid"] == "business-001"

        # Verify: Business has cascade fields
        assert chain[0]["custom_fields"][0]["name"] == "Office Phone"
        assert chain[0]["custom_fields"][0]["text_value"] == "+15551234567"
        assert chain[0]["custom_fields"][1]["name"] == "Vertical"
        assert chain[0]["custom_fields"][1]["enum_value"]["name"] == "Chiropractic"

    async def test_dataframe_cascade_fields_populated(self) -> None:
        """Test that DataFrame extraction populates cascade columns.

        This validates the full extraction path:
        1. DataFrameViewPlugin._resolve_cascade_from_dict() is called
        2. It retrieves parent chain from store
        3. It extracts Office Phone and Vertical from Business parent
        4. DataFrame has non-null values in cascade columns

        Per SC-004: "Integration test validates cascade resolution with real hierarchy"
        """
        from autom8_asana.cache.models.completeness import STANDARD_FIELDS
        from autom8_asana.cache.models.freshness_unified import FreshnessIntent
        from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin

        # Setup
        cache = InMemoryCacheProvider()
        store = UnifiedTaskStore(cache=cache)
        mock_client = MockTasksClient()

        # Store Units with hierarchy warming (this stores with HIERARCHY_OPT_FIELDS)
        await store.put_batch_async(
            UNIT_TASKS,
            tasks_client=mock_client,
            warm_hierarchy=True,
        )

        # Store Units again with STANDARD fields so they pass completeness check
        standard_fields = list(STANDARD_FIELDS)
        for unit in UNIT_TASKS:
            await store.put_async(unit, opt_fields=standard_fields)

        # Create view plugin
        view = DataFrameViewPlugin(store=store, schema=UNIT_SCHEMA)

        # Materialize DataFrame with IMMEDIATE freshness (skip freshness validation
        # since we don't have a batch_client configured for this test)
        df = await view.materialize_async(
            task_gids=["unit-001", "unit-002"],
            project_gid="test-project",
            freshness=FreshnessIntent.IMMEDIATE,
        )

        # Verify we got rows
        assert len(df) == 2, f"Expected 2 rows, got {len(df)}"

        # Verify cascade fields populated
        # Note: office_phone uses cascade: source, vertical uses cf: source (not cascade)
        assert "office_phone" in df.columns, "office_phone column missing"
        assert "vertical" in df.columns, "vertical column missing"

        # Check office_phone is NOT null (it cascades from parent)
        office_phone_nulls = df["office_phone"].null_count()
        total_rows = len(df)

        assert office_phone_nulls == 0, f"office_phone has {office_phone_nulls}/{total_rows} nulls"
        # vertical is now a direct custom field (cf:Vertical), not cascade
        # Since UNIT_TASKS have empty custom_fields, vertical will be null
        # This is expected behavior per schema change

        # Verify actual office_phone value
        assert df["office_phone"][0] == "+15551234567"


class TestWarmAncestorsAsync:
    """Test warm_ancestors_async with cache-based fetching."""

    async def test_warm_ancestors_fetches_uncached_parents(self) -> None:
        """warm_ancestors_async should fetch parents not in cache.

        Per TDD-unit-cascade-resolution-fix Fix 2: The cache check should
        trigger parent fetch when parent data is not cached.
        """
        from autom8_asana.cache.integration.hierarchy_warmer import warm_ancestors_async

        # Setup
        cache = InMemoryCacheProvider()
        store = UnifiedTaskStore(cache=cache)
        mock_client = MockTasksClient()

        # First, register and cache Units
        for unit in UNIT_TASKS:
            store._hierarchy.register(unit)
            await store.put_async(unit)

        # Verify: Hierarchy knows about parent relationship
        assert store._hierarchy.get_parent_gid("unit-001") == "business-001"

        # Verify: But business is NOT in cache
        cached_before = store.cache.get_versioned("business-001", EntryType.TASK)
        assert cached_before is None, "Business should not be cached before warming"

        # Act: Warm ancestors
        warmed = await warm_ancestors_async(
            gids=["unit-001", "unit-002"],
            hierarchy_index=store._hierarchy,
            tasks_client=mock_client,
            unified_store=store,
        )

        # Verify: Business was fetched
        assert "business-001" in mock_client.fetched_gids, "Business should have been fetched"
        assert warmed >= 1, "At least one ancestor should have been warmed"

        # Verify: Business is now cached
        cached_after = store.cache.get_versioned("business-001", EntryType.TASK)
        assert cached_after is not None, "Business should be cached after warming"


class TestNoDuplicateFetches:
    """Test that parents are not fetched multiple times."""

    async def test_single_parent_fetched_once(self) -> None:
        """Multiple Units with same parent should only trigger one fetch.

        Per TDD: Performance consideration - parent tasks are cached after
        first fetch, so subsequent requests should hit cache.
        """
        # Setup
        cache = InMemoryCacheProvider()
        store = UnifiedTaskStore(cache=cache)
        mock_client = MockTasksClient()

        # Act: Store Unit tasks with hierarchy warming
        await store.put_batch_async(
            UNIT_TASKS,
            tasks_client=mock_client,
            warm_hierarchy=True,
        )

        # Count how many times business-001 was fetched
        business_fetch_count = mock_client.fetched_gids.count("business-001")

        # Should only be fetched once despite two Units referencing it
        assert business_fetch_count == 1, (
            f"Business should be fetched exactly once, but was fetched {business_fetch_count} times"
        )
