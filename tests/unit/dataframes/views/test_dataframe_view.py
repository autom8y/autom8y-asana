"""Tests for DataFrameViewPlugin.

Per TDD-UNIFIED-CACHE-001 Phase 2: Unit tests for DataFrame view plugin
with mocked UnifiedTaskStore and schema.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock UnifiedTaskStore."""
    store = MagicMock()
    store.get_batch_async = AsyncMock(return_value={})
    store.get_parent_chain_async = AsyncMock(return_value=[])
    return store


@pytest.fixture
def simple_schema() -> DataFrameSchema:
    """Create a simple test schema."""
    return DataFrameSchema(
        name="test",
        task_type="Test",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False, source=None),
            ColumnDef("name", "Utf8", nullable=False, source=None),
            ColumnDef("type", "Utf8", nullable=False, source=None),
            ColumnDef("is_completed", "Boolean", nullable=False, source=None),
        ],
        version="1.0.0",
    )


@pytest.fixture
def full_schema() -> DataFrameSchema:
    """Create a full test schema with various field types."""
    return DataFrameSchema(
        name="full_test",
        task_type="Unit",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False, source=None),
            ColumnDef("name", "Utf8", nullable=False, source=None),
            ColumnDef("type", "Utf8", nullable=False, source=None),
            ColumnDef("created", "Datetime", nullable=True, source=None),
            ColumnDef("last_modified", "Datetime", nullable=True, source=None),
            ColumnDef("due_on", "Date", nullable=True, source=None),
            ColumnDef("is_completed", "Boolean", nullable=False, source=None),
            ColumnDef("section", "Utf8", nullable=True, source=None),
            ColumnDef("tags", "List[Utf8]", nullable=True, source=None),
            ColumnDef("url", "Utf8", nullable=True, source=None),
            ColumnDef("vertical", "Utf8", nullable=True, source="cf:Vertical"),
            ColumnDef("mrr", "Float64", nullable=True, source="cf:MRR"),
        ],
        version="1.0.0",
    )


@pytest.fixture
def cascade_schema() -> DataFrameSchema:
    """Create a schema with cascade fields."""
    return DataFrameSchema(
        name="cascade_test",
        task_type="Unit",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False, source=None),
            ColumnDef("name", "Utf8", nullable=False, source=None),
            ColumnDef("office_phone", "Utf8", nullable=True, source="cascade:Office Phone"),
        ],
        version="1.0.0",
    )


@pytest.fixture
def sample_task_data() -> dict[str, Any]:
    """Create sample task data dict."""
    return {
        "gid": "task-123",
        "name": "Test Task",
        "resource_subtype": "default_task",
        "completed": False,
        "completed_at": None,
        "created_at": "2025-01-01T10:00:00.000Z",
        "modified_at": "2025-01-02T15:30:00.000Z",
        "due_on": "2025-02-01",
        "parent": {"gid": "parent-456"},
        "memberships": [
            {
                "project": {"gid": "proj-1"},
                "section": {"gid": "sec-1", "name": "Active"},
            }
        ],
        "tags": [
            {"gid": "tag-1", "name": "Important"},
            {"gid": "tag-2", "name": "Review"},
        ],
        "custom_fields": [
            {
                "gid": "cf-1",
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_value": {"gid": "opt-1", "name": "Dental"},
            },
            {
                "gid": "cf-2",
                "name": "MRR",
                "resource_subtype": "number",
                "number_value": 1500.0,
            },
        ],
    }


@pytest.fixture
def dataframe_plugin(mock_store: MagicMock, simple_schema: DataFrameSchema) -> DataFrameViewPlugin:
    """Create a DataFrameViewPlugin with mock store and simple schema."""
    return DataFrameViewPlugin(store=mock_store, schema=simple_schema)


class TestDataFrameViewPluginInit:
    """Tests for DataFrameViewPlugin initialization."""

    def test_init_with_store_and_schema(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test plugin initialization with store and schema."""
        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        assert plugin.store is mock_store
        assert plugin.schema is simple_schema
        assert plugin.resolver is None
        assert plugin.cascade_plugin is not None

    def test_init_with_resolver(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test plugin initialization with resolver."""
        mock_resolver = MagicMock()
        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema, resolver=mock_resolver)

        assert plugin.resolver is mock_resolver

    def test_init_creates_cascade_plugin(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test that cascade plugin is created on init."""
        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        assert plugin.cascade_plugin.store is mock_store


class TestDataFrameViewPluginMaterialize:
    """Tests for DataFrameViewPlugin.materialize_async()."""

    async def test_materialize_empty_gids(self, dataframe_plugin: DataFrameViewPlugin) -> None:
        """Test materialize with empty GID list."""
        result = await dataframe_plugin.materialize_async([])

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 0

    async def test_materialize_no_tasks_found(
        self, dataframe_plugin: DataFrameViewPlugin, mock_store: MagicMock
    ) -> None:
        """Test materialize when no tasks found in cache."""
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": None})

        result = await dataframe_plugin.materialize_async(["task-1"])

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 0

    async def test_materialize_single_task(
        self,
        mock_store: MagicMock,
        simple_schema: DataFrameSchema,
        sample_task_data: dict[str, Any],
    ) -> None:
        """Test materialize with single task."""
        mock_store.get_batch_async = AsyncMock(return_value={"task-123": sample_task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        result = await plugin.materialize_async(["task-123"])

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 1
        assert result["gid"][0] == "task-123"
        assert result["name"][0] == "Test Task"
        assert result["type"][0] == "default_task"
        assert result["is_completed"][0] is False

    async def test_materialize_multiple_tasks(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test materialize with multiple tasks."""
        tasks = {
            "task-1": {
                "gid": "task-1",
                "name": "Task One",
                "resource_subtype": "default_task",
                "completed": False,
            },
            "task-2": {
                "gid": "task-2",
                "name": "Task Two",
                "resource_subtype": "milestone",
                "completed": True,
            },
        }
        mock_store.get_batch_async = AsyncMock(return_value=tasks)
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        result = await plugin.materialize_async(["task-1", "task-2"])

        assert len(result) == 2
        assert "task-1" in result["gid"].to_list()
        assert "task-2" in result["gid"].to_list()

    async def test_materialize_respects_freshness_mode(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test that freshness mode is passed to store."""
        mock_store.get_batch_async = AsyncMock(return_value={})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        await plugin.materialize_async(["task-1"], freshness=FreshnessIntent.STRICT)

        mock_store.get_batch_async.assert_called_with(["task-1"], freshness=FreshnessIntent.STRICT)

    async def test_materialize_with_project_gid(
        self,
        mock_store: MagicMock,
        simple_schema: DataFrameSchema,
        sample_task_data: dict[str, Any],
    ) -> None:
        """Test materialize with project_gid context."""
        mock_store.get_batch_async = AsyncMock(return_value={"task-123": sample_task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        # Should complete without error
        result = await plugin.materialize_async(["task-123"], project_gid="proj-1")

        assert len(result) == 1


class TestDataFrameViewPluginExtraction:
    """Tests for field extraction methods."""

    async def test_extract_datetime_fields(
        self, mock_store: MagicMock, full_schema: DataFrameSchema
    ) -> None:
        """Test datetime field extraction."""
        task_data = {
            "gid": "task-1",
            "name": "Test",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T10:00:00.000Z",
            "modified_at": "2025-01-02T15:30:00.000Z",
            "due_on": "2025-02-01",
            "memberships": [],
            "tags": [],
            "custom_fields": [],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=full_schema)

        result = await plugin.materialize_async(["task-1"])

        assert result["created"][0] is not None
        assert result["last_modified"][0] is not None
        # Due_on should be a date
        assert result["due_on"][0] is not None

    async def test_extract_tags(self, mock_store: MagicMock, full_schema: DataFrameSchema) -> None:
        """Test tags extraction."""
        task_data = {
            "gid": "task-1",
            "name": "Test",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T00:00:00Z",
            "modified_at": "2025-01-01T00:00:00Z",
            "memberships": [],
            "tags": [
                {"gid": "tag-1", "name": "Important"},
                {"gid": "tag-2", "name": "Review"},
            ],
            "custom_fields": [],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=full_schema)

        result = await plugin.materialize_async(["task-1"])

        tags = result["tags"][0]
        assert "Important" in tags
        assert "Review" in tags

    async def test_extract_section(
        self, mock_store: MagicMock, full_schema: DataFrameSchema
    ) -> None:
        """Test section extraction."""
        task_data = {
            "gid": "task-1",
            "name": "Test",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T00:00:00Z",
            "modified_at": "2025-01-01T00:00:00Z",
            "memberships": [
                {
                    "project": {"gid": "proj-1"},
                    "section": {"gid": "sec-1", "name": "Active"},
                }
            ],
            "tags": [],
            "custom_fields": [],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=full_schema)

        result = await plugin.materialize_async(["task-1"], project_gid="proj-1")

        assert result["section"][0] == "Active"

    async def test_extract_custom_field_enum(
        self, mock_store: MagicMock, full_schema: DataFrameSchema
    ) -> None:
        """Test custom field enum extraction."""
        task_data = {
            "gid": "task-1",
            "name": "Test",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T00:00:00Z",
            "modified_at": "2025-01-01T00:00:00Z",
            "memberships": [],
            "tags": [],
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Vertical",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": "opt-1", "name": "Dental"},
                }
            ],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=full_schema)

        result = await plugin.materialize_async(["task-1"])

        assert result["vertical"][0] == "Dental"

    async def test_extract_custom_field_number(
        self, mock_store: MagicMock, full_schema: DataFrameSchema
    ) -> None:
        """Test custom field number extraction."""
        task_data = {
            "gid": "task-1",
            "name": "Test",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T00:00:00Z",
            "modified_at": "2025-01-01T00:00:00Z",
            "memberships": [],
            "tags": [],
            "custom_fields": [
                {
                    "gid": "cf-2",
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 1500.0,
                }
            ],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=full_schema)

        result = await plugin.materialize_async(["task-1"])

        assert result["mrr"][0] == 1500.0


class TestDataFrameViewPluginCascadeFields:
    """Tests for cascade field resolution."""

    async def test_cascade_field_local_value(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Test cascade field extraction with local value."""
        task_data = {
            "gid": "task-1",
            "name": "Test Unit",
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "555-LOCAL",
                }
            ],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        result = await plugin.materialize_async(["task-1"])

        assert result["office_phone"][0] == "555-LOCAL"

    async def test_cascade_field_from_parent(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Test cascade field extraction from parent chain."""
        task_data = {
            "gid": "task-1",
            "name": "Test Unit",
            "parent": {"gid": "parent-1"},
            "custom_fields": [],  # No local value
        }
        parent_data = {
            "gid": "parent-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "555-PARENT",
                }
            ],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[parent_data])

        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        result = await plugin.materialize_async(["task-1"])

        assert result["office_phone"][0] == "555-PARENT"


class TestDataFrameViewPluginCascadeFallback:
    """Tests for cascade field resolution fallback.

    Per TDD-unit-cascade-resolution-fix Fix 3: When parent_chain is empty
    but task has parent.gid, try direct fetch from cache.
    """

    async def test_cascade_fallback_when_parent_chain_empty(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Test fallback to direct parent fetch when parent_chain is empty.

        Per TDD-unit-cascade-resolution-fix: When get_parent_chain_async
        returns empty but task has parent.gid, the fallback should try
        get_with_upgrade_async to fetch the parent directly.
        """
        task_data = {
            "gid": "unit-1",
            "name": "Test Unit",
            "parent": {"gid": "business-1"},  # Has parent reference
            "custom_fields": [],  # No local value
        }
        parent_data = {
            "gid": "business-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "555-FALLBACK",
                }
            ],
        }

        # Parent chain returns empty (the bug scenario)
        mock_store.get_batch_async = AsyncMock(return_value={"unit-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        # But get_with_upgrade_async can fetch the parent
        mock_store.get_with_upgrade_async = AsyncMock(return_value=parent_data)

        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        result = await plugin.materialize_async(["unit-1"])

        # Should have used the fallback to get the parent
        assert mock_store.get_with_upgrade_async.called
        assert result["office_phone"][0] == "555-FALLBACK"

    async def test_cascade_fallback_not_triggered_when_chain_populated(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Test fallback is NOT triggered when parent chain is populated."""
        task_data = {
            "gid": "unit-1",
            "name": "Test Unit",
            "parent": {"gid": "business-1"},
            "custom_fields": [],
        }
        parent_data = {
            "gid": "business-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "555-FROM-CHAIN",
                }
            ],
        }

        mock_store.get_batch_async = AsyncMock(return_value={"unit-1": task_data})
        # Parent chain returns the parent normally
        mock_store.get_parent_chain_async = AsyncMock(return_value=[parent_data])
        mock_store.get_with_upgrade_async = AsyncMock(return_value=None)

        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        result = await plugin.materialize_async(["unit-1"])

        # Should NOT have triggered the fallback
        assert not mock_store.get_with_upgrade_async.called
        assert result["office_phone"][0] == "555-FROM-CHAIN"

    async def test_cascade_fallback_returns_none_when_no_parent(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Test cascade returns None when task has no parent and chain is empty."""
        task_data = {
            "gid": "root-1",
            "name": "Root Task",
            "parent": None,  # No parent
            "custom_fields": [],
        }

        mock_store.get_batch_async = AsyncMock(return_value={"root-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])
        mock_store.get_with_upgrade_async = AsyncMock(return_value=None)

        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        result = await plugin.materialize_async(["root-1"])

        # Should NOT trigger fallback when no parent.gid
        assert not mock_store.get_with_upgrade_async.called
        assert result["office_phone"][0] is None

    async def test_resolve_cascade_from_populated_chain(
        self, mock_store: MagicMock, cascade_schema: DataFrameSchema
    ) -> None:
        """Verify cascade field extracted from parent in chain.

        Per TDD-unit-cascade-resolution-fix Test 2: When parent chain is
        populated, the cascade field should be extracted from the parent.
        """
        task_data = {
            "gid": "unit-1",
            "name": "Test Unit",
            "parent": {"gid": "business-1"},
            "custom_fields": [],
        }
        business_data = {
            "gid": "business-1",
            "parent": None,
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "+15551234567",
                }
            ],
        }

        mock_store.get_batch_async = AsyncMock(return_value={"unit-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[business_data])

        plugin = DataFrameViewPlugin(store=mock_store, schema=cascade_schema)

        result = await plugin.materialize_async(["unit-1"])

        assert result["office_phone"][0] == "+15551234567"


class TestDataFrameViewPluginIncremental:
    """Tests for incremental materialization."""

    async def test_incremental_with_existing_df(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test incremental materialization with existing DataFrame."""
        existing_df = pl.DataFrame(
            {
                "gid": ["task-1"],
                "name": ["Old Name"],
                "type": ["default_task"],
                "is_completed": [False],
            }
        )

        # Updated task data
        task_data = {
            "gid": "task-1",
            "name": "Updated Name",
            "resource_subtype": "default_task",
            "completed": True,
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        watermark = datetime(2025, 1, 1, tzinfo=UTC)
        result_df, new_watermark = await plugin.materialize_incremental_async(
            existing_df, watermark, "proj-1"
        )

        assert len(result_df) == 1
        assert result_df["name"][0] == "Updated Name"
        assert new_watermark > watermark


class TestDataFrameViewPluginStats:
    """Tests for statistics tracking."""

    async def test_stats_tracking(
        self,
        mock_store: MagicMock,
        simple_schema: DataFrameSchema,
        sample_task_data: dict[str, Any],
    ) -> None:
        """Test that statistics are tracked correctly."""
        mock_store.get_batch_async = AsyncMock(return_value={"task-123": sample_task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        # Initial stats
        stats = plugin.get_stats()
        assert stats["materialize_calls"] == 0

        # Make a materialize call
        await plugin.materialize_async(["task-123"])

        # Stats should be updated
        stats = plugin.get_stats()
        assert stats["materialize_calls"] == 1
        assert stats["tasks_fetched"] == 1
        assert stats["rows_extracted"] == 1

    def test_reset_stats(self, dataframe_plugin: DataFrameViewPlugin) -> None:
        """Test that stats can be reset."""
        # Manually set stats
        dataframe_plugin._stats["materialize_calls"] = 10

        dataframe_plugin.reset_stats()

        stats = dataframe_plugin.get_stats()
        assert stats["materialize_calls"] == 0


class TestDataFrameViewPluginEdgeCases:
    """Tests for edge cases."""

    async def test_task_with_missing_fields(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test task with missing optional fields."""
        task_data = {
            "gid": "task-1",
            # Missing name and other fields
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        result = await plugin.materialize_async(["task-1"])

        # Should handle missing fields gracefully
        assert len(result) == 1
        assert result["gid"][0] == "task-1"
        assert result["name"][0] == ""  # Default empty string

    async def test_task_with_null_custom_fields(
        self, mock_store: MagicMock, full_schema: DataFrameSchema
    ) -> None:
        """Test task with null custom_fields list."""
        task_data = {
            "gid": "task-1",
            "name": "Test",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T00:00:00Z",
            "modified_at": "2025-01-01T00:00:00Z",
            "memberships": [],
            "tags": [],
            "custom_fields": None,  # Null
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-1": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=full_schema)

        result = await plugin.materialize_async(["task-1"])

        # Should handle null custom_fields
        assert len(result) == 1
        assert result["vertical"][0] is None

    async def test_url_generation(
        self, mock_store: MagicMock, full_schema: DataFrameSchema
    ) -> None:
        """Test URL field generation."""
        task_data = {
            "gid": "12345678901234567",
            "name": "Test",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T00:00:00Z",
            "modified_at": "2025-01-01T00:00:00Z",
            "memberships": [],
            "tags": [],
            "custom_fields": [],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"12345678901234567": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=full_schema)

        result = await plugin.materialize_async(["12345678901234567"])

        expected_url = "https://app.asana.com/0/0/12345678901234567"
        assert result["url"][0] == expected_url


class TestDataFrameViewPluginMixedTypes:
    """Tests for handling mixed type fields (e.g., percentage fields).

    Per progressive builder fix: Fields with missing resource_subtype
    should prefer typed values (number_value) over display_value to
    avoid Polars schema inference errors like "0%" vs 0.0.
    """

    @pytest.fixture
    def percentage_schema(self) -> DataFrameSchema:
        """Schema with percentage/decimal fields."""
        return DataFrameSchema(
            name="percentage_test",
            task_type="Unit",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False, source=None),
                ColumnDef("name", "Utf8", nullable=False, source=None),
                ColumnDef("discount", "Float64", nullable=True, source="cf:Discount"),
                ColumnDef("commission", "Float64", nullable=True, source="cf:Commission"),
            ],
            version="1.0.0",
        )

    async def test_extract_cf_value_prefers_number_over_display(
        self, mock_store: MagicMock, percentage_schema: DataFrameSchema
    ) -> None:
        """Test that number_value is preferred over display_value.

        This is the exact scenario that caused the progressive builder error:
        display_value="0%" but number_value=0.0.
        """
        task_data = {
            "gid": "task-123",
            "name": "Test Unit",
            "resource_subtype": "default_task",
            "completed": False,
            "created_at": "2025-01-01T00:00:00Z",
            "modified_at": "2025-01-01T00:00:00Z",
            "memberships": [],
            "tags": [],
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Discount",
                    "resource_subtype": None,  # Missing type info
                    "number_value": 0.0,
                    "display_value": "0%",
                },
                {
                    "gid": "cf-2",
                    "name": "Commission",
                    "resource_subtype": "number",  # Correct type
                    "number_value": 0.15,
                    "display_value": "15%",
                },
            ],
        }
        mock_store.get_batch_async = AsyncMock(return_value={"task-123": task_data})
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=percentage_schema)

        result = await plugin.materialize_async(["task-123"])

        # Both should be numeric, not strings like "0%" or "15%"
        assert result["discount"][0] == 0.0
        assert result["commission"][0] == 0.15
        assert not isinstance(result["discount"][0], str)
        assert not isinstance(result["commission"][0], str)

    def test_extract_cf_value_fallback_priority(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test fallback priority: number > text > enum > display."""
        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        # Test 1: number_value present - should return number
        cf_number = {
            "resource_subtype": None,
            "number_value": 42.5,
            "text_value": "forty-two",
            "display_value": "42.5 (formatted)",
        }
        assert plugin._extract_cf_value(cf_number) == 42.5

        # Test 2: number_value None, text_value present - should return text
        cf_text = {
            "resource_subtype": None,
            "number_value": None,
            "text_value": "hello world",
            "display_value": "Hello, World!",
        }
        assert plugin._extract_cf_value(cf_text) == "hello world"

        # Test 3: number and text None, enum present - should return enum name
        cf_enum = {
            "resource_subtype": None,
            "number_value": None,
            "text_value": None,
            "enum_value": {"gid": "e1", "name": "Active"},
            "display_value": "Active status",
        }
        assert plugin._extract_cf_value(cf_enum) == "Active"

        # Test 4: only display_value - should return display
        cf_display_only = {
            "resource_subtype": "formula",
            "display_value": "Computed: 123",
        }
        assert plugin._extract_cf_value(cf_display_only) == "Computed: 123"

    def test_extract_custom_field_value_from_dict_priority(
        self, mock_store: MagicMock, simple_schema: DataFrameSchema
    ) -> None:
        """Test _extract_custom_field_value_from_dict fallback priority.

        This method is used as fallback when cascade_plugin is not available.
        """
        plugin = DataFrameViewPlugin(store=mock_store, schema=simple_schema)

        # Task with percentage-like field
        task_data = {
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Commission",
                    "resource_subtype": None,  # Missing
                    "number_value": 0.0,
                    "display_value": "0%",
                },
            ]
        }

        result = plugin._extract_custom_field_value_from_dict(task_data, "Commission")

        # Should return 0.0, not "0%"
        assert result == 0.0
        assert not isinstance(result, str)

    async def test_polars_dataframe_creation_with_percentage(
        self, mock_store: MagicMock, percentage_schema: DataFrameSchema
    ) -> None:
        """Test that DataFrame creation succeeds with percentage fields.

        This verifies the fix prevents the ComputeError that occurred when
        Polars tried to append "0%" string to a Float64 column.
        """
        # Multiple tasks with varying percentage values
        tasks = {
            "task-1": {
                "gid": "task-1",
                "name": "Task 1",
                "resource_subtype": "default_task",
                "completed": False,
                "created_at": "2025-01-01T00:00:00Z",
                "modified_at": "2025-01-01T00:00:00Z",
                "memberships": [],
                "tags": [],
                "custom_fields": [
                    {
                        "gid": "cf-1",
                        "name": "Discount",
                        "resource_subtype": None,  # Edge case: missing type
                        "number_value": 0.0,
                        "display_value": "0%",
                    },
                ],
            },
            "task-2": {
                "gid": "task-2",
                "name": "Task 2",
                "resource_subtype": "default_task",
                "completed": False,
                "created_at": "2025-01-01T00:00:00Z",
                "modified_at": "2025-01-01T00:00:00Z",
                "memberships": [],
                "tags": [],
                "custom_fields": [
                    {
                        "gid": "cf-1",
                        "name": "Discount",
                        "resource_subtype": "number",  # Normal case
                        "number_value": 0.25,
                        "display_value": "25%",
                    },
                ],
            },
        }
        mock_store.get_batch_async = AsyncMock(return_value=tasks)
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=percentage_schema)

        # This should NOT raise ComputeError
        result = await plugin.materialize_async(["task-1", "task-2"])

        # Verify DataFrame was created successfully
        assert len(result) == 2
        assert result.schema["discount"] == pl.Float64

        # Verify all values are numeric
        discounts = result["discount"].to_list()
        assert 0.0 in discounts
        assert 0.25 in discounts
        assert all(isinstance(d, (int, float)) or d is None for d in discounts)


class TestDataFrameViewPluginMultiEnumCoercion:
    """Tests for multi_enum custom field type coercion.

    Per TDD-custom-field-type-coercion: multi_enum fields return list[str]
    from the Asana API but must be coerced to match the schema's target dtype.
    Without coercion, Polars throws ComputeError when list values conflict
    with inferred Utf8 type from earlier None values.
    """

    @pytest.fixture
    def multi_enum_list_schema(self) -> DataFrameSchema:
        """Schema with a List[Utf8] column from multi_enum source."""
        return DataFrameSchema(
            name="multi_enum_test",
            task_type="Offer",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False, source=None),
                ColumnDef("name", "Utf8", nullable=False, source=None),
                ColumnDef("platforms", "List[Utf8]", nullable=True, source="cf:Platforms"),
            ],
            version="1.0.0",
        )

    @pytest.fixture
    def multi_enum_string_schema(self) -> DataFrameSchema:
        """Schema with a Utf8 column from multi_enum source."""
        return DataFrameSchema(
            name="multi_enum_string_test",
            task_type="Offer",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False, source=None),
                ColumnDef("name", "Utf8", nullable=False, source=None),
                ColumnDef("platforms", "Utf8", nullable=True, source="cf:Platforms"),
            ],
            version="1.0.0",
        )

    async def test_multi_enum_list_dtype_preserves_list(
        self, mock_store: MagicMock, multi_enum_list_schema: DataFrameSchema
    ) -> None:
        """Test multi_enum value preserved as list when target is List[Utf8]."""
        tasks = {
            "task-1": {
                "gid": "task-1",
                "name": "Task with platforms",
                "resource_subtype": "default_task",
                "completed": False,
                "custom_fields": [
                    {
                        "gid": "cf-plat",
                        "name": "Platforms",
                        "resource_subtype": "multi_enum",
                        "multi_enum_values": [
                            {"gid": "e1", "name": "Corrective Care"},
                            {"gid": "e2", "name": "Preventive Care"},
                        ],
                    }
                ],
            },
        }
        mock_store.get_batch_async = AsyncMock(return_value=tasks)
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=multi_enum_list_schema)
        result = await plugin.materialize_async(["task-1"])

        assert len(result) == 1
        platforms = result["platforms"][0].to_list()
        assert "Corrective Care" in platforms
        assert "Preventive Care" in platforms

    async def test_multi_enum_string_dtype_coerces_to_csv(
        self, mock_store: MagicMock, multi_enum_string_schema: DataFrameSchema
    ) -> None:
        """Test multi_enum list coerced to comma-separated string when target is Utf8."""
        tasks = {
            "task-1": {
                "gid": "task-1",
                "name": "Task with platforms",
                "resource_subtype": "default_task",
                "completed": False,
                "custom_fields": [
                    {
                        "gid": "cf-plat",
                        "name": "Platforms",
                        "resource_subtype": "multi_enum",
                        "multi_enum_values": [
                            {"gid": "e1", "name": "Corrective Care"},
                            {"gid": "e2", "name": "Preventive Care"},
                        ],
                    }
                ],
            },
        }
        mock_store.get_batch_async = AsyncMock(return_value=tasks)
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=multi_enum_string_schema)
        result = await plugin.materialize_async(["task-1"])

        assert len(result) == 1
        platforms = result["platforms"][0]
        assert isinstance(platforms, str)
        assert "Corrective Care" in platforms
        assert "Preventive Care" in platforms

    async def test_multi_enum_mixed_none_and_values_no_crash(
        self, mock_store: MagicMock, multi_enum_list_schema: DataFrameSchema
    ) -> None:
        """Test that None followed by list values doesn't crash Polars.

        This is the exact production scenario: first task has None for the
        multi_enum field, Polars infers Utf8, then a later task has
        ["Corrective Care"] which conflicts.
        """
        tasks = {
            "task-1": {
                "gid": "task-1",
                "name": "Task without platforms",
                "resource_subtype": "default_task",
                "completed": False,
                "custom_fields": [
                    {
                        "gid": "cf-plat",
                        "name": "Platforms",
                        "resource_subtype": "multi_enum",
                        "multi_enum_values": [],  # Empty - returns None
                    }
                ],
            },
            "task-2": {
                "gid": "task-2",
                "name": "Task with platforms",
                "resource_subtype": "default_task",
                "completed": False,
                "custom_fields": [
                    {
                        "gid": "cf-plat",
                        "name": "Platforms",
                        "resource_subtype": "multi_enum",
                        "multi_enum_values": [
                            {"gid": "e1", "name": "Corrective Care"},
                        ],
                    }
                ],
            },
        }
        mock_store.get_batch_async = AsyncMock(return_value=tasks)
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])

        plugin = DataFrameViewPlugin(store=mock_store, schema=multi_enum_list_schema)

        # This should NOT raise polars.exceptions.ComputeError
        result = await plugin.materialize_async(["task-1", "task-2"])

        assert len(result) == 2
