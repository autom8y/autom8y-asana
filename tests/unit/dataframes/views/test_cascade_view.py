"""Tests for CascadeViewPlugin.

Per TDD-UNIFIED-CACHE-001 Phase 2: Unit tests for cascade view plugin
with mocked UnifiedTaskStore.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
from autom8_asana.models.business.detection import EntityType


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock UnifiedTaskStore.

    Per TDD-CACHE-COMPLETENESS-001 Phase 3: Mocks get_with_upgrade_async
    and get_hierarchy_index for completeness-aware parent chain traversal.
    """
    store = MagicMock()
    store.get_parent_chain_async = AsyncMock(return_value=[])
    # Mock for completeness-aware parent chain lookup
    store.get_with_upgrade_async = AsyncMock(return_value=None)
    # Mock hierarchy index
    mock_hierarchy = MagicMock()
    mock_hierarchy.get_ancestor_chain = MagicMock(return_value=[])
    store.get_hierarchy_index = MagicMock(return_value=mock_hierarchy)
    return store


@pytest.fixture
def cascade_plugin(mock_store: MagicMock) -> CascadeViewPlugin:
    """Create a CascadeViewPlugin with mock store."""
    return CascadeViewPlugin(store=mock_store)


@pytest.fixture
def mock_task() -> MagicMock:
    """Create a mock Task with custom fields."""
    task = MagicMock()
    task.gid = "task-123"
    task.name = "Test Unit"
    task.parent = MagicMock(gid="parent-456")
    task.custom_fields = [
        {
            "gid": "cf-1",
            "name": "Office Phone",
            "resource_subtype": "text",
            "text_value": "555-123-4567",
        },
        {
            "gid": "cf-2",
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_value": {"gid": "enum-1", "name": "Dental"},
        },
    ]
    return task


@pytest.fixture
def mock_task_no_custom_fields() -> MagicMock:
    """Create a mock Task without custom fields."""
    task = MagicMock()
    task.gid = "task-456"
    task.name = "Test Unit No Fields"
    task.parent = MagicMock(gid="parent-789")
    task.custom_fields = None
    return task


class TestCascadeViewPluginInit:
    """Tests for CascadeViewPlugin initialization."""

    def test_init_with_store(self, mock_store: MagicMock) -> None:
        """Test plugin initialization with store."""
        plugin = CascadeViewPlugin(store=mock_store)

        assert plugin.store is mock_store
        assert plugin.registry is not None
        assert isinstance(plugin.get_stats(), dict)

    def test_init_with_custom_registry(self, mock_store: MagicMock) -> None:
        """Test plugin initialization with custom registry."""
        custom_registry = {"test_field": (MagicMock, MagicMock())}
        plugin = CascadeViewPlugin(store=mock_store, registry=custom_registry)

        assert plugin.registry is custom_registry


class TestCascadeViewPluginResolve:
    """Tests for CascadeViewPlugin.resolve_async()."""

    async def test_resolve_unregistered_field_returns_none(
        self, cascade_plugin: CascadeViewPlugin, mock_task: MagicMock
    ) -> None:
        """Test that unregistered field returns None."""
        result = await cascade_plugin.resolve_async(mock_task, "Unknown Field")

        assert result is None
        assert cascade_plugin.get_stats()["field_not_found"] == 1

    async def test_resolve_local_override_when_allowed(self, mock_store: MagicMock) -> None:
        """Test local value is returned when allow_override=True."""
        from autom8_asana.models.business.fields import CascadingFieldDef

        # Create real field def that allows override
        field_def = CascadingFieldDef(
            name="Test Field",
            target_types=None,
            allow_override=True,
        )

        # Create mock owner class
        class MockBusiness:
            pass

        mock_registry = {"test field": (MockBusiness, field_def)}

        plugin = CascadeViewPlugin(store=mock_store, registry=mock_registry)

        # Create task with local value
        task = MagicMock()
        task.gid = "task-1"
        task.custom_fields = [
            {
                "gid": "cf-1",
                "name": "Test Field",
                "resource_subtype": "text",
                "text_value": "local-value",
            }
        ]

        result = await plugin.resolve_async(task, "Test Field")

        assert result == "local-value"
        assert plugin.get_stats()["field_found"] == 1

    async def test_resolve_traverses_parent_chain(
        self, mock_store: MagicMock, mock_task: MagicMock
    ) -> None:
        """Test that resolution traverses parent chain.

        Per TDD-CACHE-COMPLETENESS-001 Phase 3: Uses get_with_upgrade_async
        for completeness-aware parent chain traversal.
        """
        # Set up parent chain with field value
        parent_data = {
            "gid": "parent-456",
            "name": "Business Task",
            "parent": None,  # Root
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "(614) 636-2433",
                }
            ],
        }
        # Mock hierarchy index to return parent GID
        mock_hierarchy = MagicMock()
        mock_hierarchy.get_ancestor_chain = MagicMock(return_value=["parent-456"])
        mock_store.get_hierarchy_index = MagicMock(return_value=mock_hierarchy)
        # Mock get_with_upgrade_async to return parent data
        mock_store.get_with_upgrade_async = AsyncMock(return_value=parent_data)

        plugin = CascadeViewPlugin(store=mock_store)

        # Remove local value from task
        mock_task.custom_fields = []

        result = await plugin.resolve_async(mock_task, "Office Phone")

        # Should find value in parent, normalized to E.164 by GAP-B cascade guard
        assert result == "+16146362433"
        mock_store.get_with_upgrade_async.assert_called_once()

    async def test_resolve_returns_none_when_chain_empty(
        self, cascade_plugin: CascadeViewPlugin, mock_task: MagicMock
    ) -> None:
        """Test None returned when parent chain is empty and field not local."""
        # Remove local value
        mock_task.custom_fields = []

        result = await cascade_plugin.resolve_async(mock_task, "Office Phone")

        assert result is None

    async def test_resolve_respects_max_depth(
        self, mock_store: MagicMock, mock_task: MagicMock
    ) -> None:
        """Test max_depth parameter is passed to hierarchy lookup.

        Per TDD-CACHE-COMPLETENESS-001 Phase 3: max_depth is passed to
        the hierarchy index's get_ancestor_chain method.
        """
        # Set up hierarchy mock to track max_depth
        mock_hierarchy = MagicMock()
        mock_hierarchy.get_ancestor_chain = MagicMock(return_value=[])
        mock_store.get_hierarchy_index = MagicMock(return_value=mock_hierarchy)

        plugin = CascadeViewPlugin(store=mock_store)
        mock_task.custom_fields = []

        await plugin.resolve_async(mock_task, "Office Phone", max_depth=3)

        # Verify max_depth was passed to hierarchy index
        mock_hierarchy.get_ancestor_chain.assert_called_with(mock_task.gid, max_depth=3)


class TestCascadeViewPluginPrefetch:
    """Tests for CascadeViewPlugin.prefetch_parents_async()."""

    async def test_prefetch_empty_list(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test prefetch with empty task list."""
        await cascade_plugin.prefetch_parents_async([])

        assert cascade_plugin.get_stats()["prefetch_calls"] == 1

    async def test_prefetch_triggers_cache_lookup(self, mock_store: MagicMock) -> None:
        """Test prefetch triggers parent chain lookups."""
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])
        plugin = CascadeViewPlugin(store=mock_store)

        # Create tasks with parents
        task1 = MagicMock()
        task1.gid = "task-1"
        task1.parent = MagicMock(gid="parent-1")

        task2 = MagicMock()
        task2.gid = "task-2"
        task2.parent = MagicMock(gid="parent-2")

        await plugin.prefetch_parents_async([task1, task2])

        # Should have called get_parent_chain_async for each task with parent
        assert mock_store.get_parent_chain_async.call_count == 2

    async def test_prefetch_skips_orphan_tasks(self, mock_store: MagicMock) -> None:
        """Test prefetch skips tasks without parents."""
        mock_store.get_parent_chain_async = AsyncMock(return_value=[])
        plugin = CascadeViewPlugin(store=mock_store)

        # Task without parent
        orphan = MagicMock()
        orphan.gid = "orphan-1"
        orphan.parent = None

        await plugin.prefetch_parents_async([orphan])

        # Should not have called get_parent_chain_async
        mock_store.get_parent_chain_async.assert_not_called()


class TestCascadeViewPluginFieldExtraction:
    """Tests for field value extraction methods."""

    def test_extract_text_field(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test text field extraction."""
        cf_data = {
            "gid": "cf-1",
            "name": "Notes",
            "resource_subtype": "text",
            "text_value": "Hello World",
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == "Hello World"

    def test_extract_number_field(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test number field extraction."""
        cf_data = {
            "gid": "cf-2",
            "name": "MRR",
            "resource_subtype": "number",
            "number_value": 1234.56,
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == 1234.56

    def test_extract_enum_field(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test enum field extraction."""
        cf_data = {
            "gid": "cf-3",
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_value": {"gid": "enum-1", "name": "Dental"},
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == "Dental"

    def test_extract_enum_field_none_value(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test enum field with None value."""
        cf_data = {
            "gid": "cf-3",
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_value": None,
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result is None

    def test_extract_multi_enum_field(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test multi_enum field extraction."""
        cf_data = {
            "gid": "cf-4",
            "name": "Platforms",
            "resource_subtype": "multi_enum",
            "multi_enum_values": [
                {"gid": "opt-1", "name": "GBP"},
                {"gid": "opt-2", "name": "LSA"},
            ],
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == ["GBP", "LSA"]

    def test_extract_date_field(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test date field extraction."""
        cf_data = {
            "gid": "cf-5",
            "name": "Start Date",
            "resource_subtype": "date",
            "date_value": {"date": "2025-01-15"},
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == "2025-01-15"

    def test_extract_people_field(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test people field extraction."""
        cf_data = {
            "gid": "cf-6",
            "name": "Owners",
            "resource_subtype": "people",
            "people_value": [
                {"gid": "user-1"},
                {"gid": "user-2"},
            ],
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == ["user-1", "user-2"]

    def test_extract_unknown_type_uses_display_value(
        self, cascade_plugin: CascadeViewPlugin
    ) -> None:
        """Test unknown field type falls back to display_value."""
        cf_data = {
            "gid": "cf-7",
            "name": "Custom",
            "resource_subtype": "formula",  # Unknown type
            "display_value": "Computed: 42",
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == "Computed: 42"


class TestCascadeViewPluginClassMapping:
    """Tests for entity type mapping."""

    def test_class_to_entity_type_business(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test Business class maps correctly."""

        class Business:
            pass

        result = cascade_plugin._class_to_entity_type(Business)

        assert result == EntityType.BUSINESS

    def test_class_to_entity_type_unit(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test Unit class maps correctly."""

        class Unit:
            pass

        result = cascade_plugin._class_to_entity_type(Unit)

        assert result == EntityType.UNIT

    def test_class_to_entity_type_unknown(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test unknown class maps to UNKNOWN."""

        class SomeOtherClass:
            pass

        result = cascade_plugin._class_to_entity_type(SomeOtherClass)

        assert result == EntityType.UNKNOWN


class TestCascadeViewPluginStats:
    """Tests for statistics tracking."""

    async def test_stats_tracking(
        self, cascade_plugin: CascadeViewPlugin, mock_task: MagicMock
    ) -> None:
        """Test that statistics are tracked correctly."""
        # Initial stats should be zero
        stats = cascade_plugin.get_stats()
        assert stats["resolve_calls"] == 0

        # Make a resolve call
        await cascade_plugin.resolve_async(mock_task, "Office Phone")

        # Stats should be updated
        stats = cascade_plugin.get_stats()
        assert stats["resolve_calls"] == 1

    def test_reset_stats(self, cascade_plugin: CascadeViewPlugin) -> None:
        """Test that stats can be reset."""
        # Manually set a stat
        cascade_plugin._stats["resolve_calls"] = 10

        cascade_plugin.reset_stats()

        stats = cascade_plugin.get_stats()
        assert stats["resolve_calls"] == 0


class TestCascadeViewPluginEdgeCases:
    """Tests for edge cases."""

    async def test_task_with_none_custom_fields(
        self, cascade_plugin: CascadeViewPlugin, mock_task_no_custom_fields: MagicMock
    ) -> None:
        """Test task with None custom_fields."""
        result = await cascade_plugin.resolve_async(mock_task_no_custom_fields, "Office Phone")

        # Should handle gracefully
        assert result is None

    async def test_resolve_with_case_insensitive_field_name(self, mock_store: MagicMock) -> None:
        """Test field name lookup is case insensitive.

        Per TDD-CACHE-COMPLETENESS-001 Phase 3: Uses get_with_upgrade_async
        for completeness-aware parent chain traversal.
        """
        from autom8_asana.models.business.fields import CascadingFieldDef

        # Set up parent with field (root task - no parent)
        parent_data = {
            "gid": "parent-1",
            "parent": None,  # Root task = Business
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",  # Mixed case
                    "resource_subtype": "text",
                    "text_value": "(614) 636-2433",
                }
            ],
        }
        # Mock hierarchy index to return parent GID
        mock_hierarchy = MagicMock()
        mock_hierarchy.get_ancestor_chain = MagicMock(return_value=["parent-1"])
        mock_store.get_hierarchy_index = MagicMock(return_value=mock_hierarchy)
        # Mock get_with_upgrade_async to return parent data
        mock_store.get_with_upgrade_async = AsyncMock(return_value=parent_data)

        # Create field def for testing
        field_def = CascadingFieldDef(name="Office Phone", target_types=None)

        # IMPORTANT: Class must be named "Business" exactly for type mapping
        class Business:
            pass

        mock_registry = {"office phone": (Business, field_def)}

        plugin = CascadeViewPlugin(store=mock_store, registry=mock_registry)

        task = MagicMock()
        task.gid = "task-1"
        task.name = "Test Unit"  # Must be a string for detection
        task.custom_fields = []
        task.memberships = None  # Required for detection

        # Search with different case (registry key should be normalized)
        result = await plugin.resolve_async(task, "office phone")

        # Per GAP-B: Office Phone values are normalized to E.164 on cascade read
        assert result == "+16146362433"

    async def test_resolve_from_root_fallback(self, mock_store: MagicMock) -> None:
        """Test Business field found at root task (fallback behavior).

        Per TDD-CACHE-COMPLETENESS-001 Phase 3: Uses get_with_upgrade_async
        for completeness-aware parent chain traversal.
        """
        from autom8_asana.models.business.fields import CascadingFieldDef

        # Parent chain ends at root with field value
        parent_data = {
            "gid": "root-1",
            "parent": None,  # This is root = Business
            "custom_fields": [
                {
                    "gid": "cf-1",
                    "name": "Office Phone",
                    "resource_subtype": "text",
                    "text_value": "(614) 636-2433",
                }
            ],
        }
        # Mock hierarchy index to return parent GID
        mock_hierarchy = MagicMock()
        mock_hierarchy.get_ancestor_chain = MagicMock(return_value=["root-1"])
        mock_store.get_hierarchy_index = MagicMock(return_value=mock_hierarchy)
        # Mock get_with_upgrade_async to return parent data
        mock_store.get_with_upgrade_async = AsyncMock(return_value=parent_data)

        # Create field def for testing
        field_def = CascadingFieldDef(name="Office Phone", target_types=None)

        # IMPORTANT: Class must be named "Business" exactly for type mapping
        class Business:
            pass

        mock_registry = {"office phone": (Business, field_def)}

        plugin = CascadeViewPlugin(store=mock_store, registry=mock_registry)

        task = MagicMock()
        task.gid = "task-1"
        task.name = "Test Unit"  # Must be a string for detection
        task.custom_fields = []
        task.memberships = None  # Required for detection

        result = await plugin.resolve_async(task, "Office Phone")

        # Should find at root, normalized to E.164 by GAP-B cascade guard
        assert result == "+16146362433"


class TestCascadeViewPluginMixedTypes:
    """Tests for handling mixed type fields (e.g., percentage fields).

    Per progressive builder fix: Fields with missing resource_subtype
    should prefer typed values (number_value) over display_value to
    avoid schema inference errors like "0%" vs 0.0.
    """

    def test_extract_unknown_type_prefers_number_value(
        self, cascade_plugin: CascadeViewPlugin
    ) -> None:
        """Test that number_value is preferred over display_value for unknown types.

        This handles percentage fields where display_value is "0%" but
        number_value is 0.0, which was causing Polars schema errors.
        """
        cf_data = {
            "gid": "cf-percent",
            "name": "Commission",
            "resource_subtype": None,  # Unknown/missing type
            "number_value": 0.0,
            "display_value": "0%",
        }

        result = cascade_plugin._extract_field_value(cf_data)

        # Should return number_value (0.0) not display_value ("0%")
        assert result == 0.0
        assert not isinstance(result, str)

    def test_extract_unknown_type_prefers_text_over_display(
        self, cascade_plugin: CascadeViewPlugin
    ) -> None:
        """Test that text_value is preferred over display_value when number is None."""
        cf_data = {
            "gid": "cf-text",
            "name": "Notes",
            "resource_subtype": None,
            "text_value": "Some notes",
            "display_value": "Display: Some notes",
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == "Some notes"

    def test_extract_unknown_type_prefers_enum_over_display(
        self, cascade_plugin: CascadeViewPlugin
    ) -> None:
        """Test enum_value is preferred over display_value when text/number are None."""
        cf_data = {
            "gid": "cf-enum",
            "name": "Status",
            "resource_subtype": None,  # Missing
            "enum_value": {"gid": "e1", "name": "Active"},
            "display_value": "Active (custom)",
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == "Active"

    def test_extract_unknown_type_falls_back_to_display(
        self, cascade_plugin: CascadeViewPlugin
    ) -> None:
        """Test display_value is used when no typed values exist."""
        cf_data = {
            "gid": "cf-formula",
            "name": "Computed",
            "resource_subtype": "formula",  # Unrecognized type
            "display_value": "Computed: 42",
            # No typed values
        }

        result = cascade_plugin._extract_field_value(cf_data)

        assert result == "Computed: 42"

    def test_extract_percentage_field_returns_numeric(
        self, cascade_plugin: CascadeViewPlugin
    ) -> None:
        """Test realistic percentage field scenario.

        This is the exact scenario that caused the progressive builder error:
        - resource_subtype may be "number" or missing
        - display_value contains formatted percentage string
        - number_value contains actual numeric value
        """
        # Scenario 1: resource_subtype is "number" (should work via match case)
        cf_with_type = {
            "gid": "cf-discount",
            "name": "Discount",
            "resource_subtype": "number",
            "number_value": 0.15,
            "display_value": "15%",
        }
        result = cascade_plugin._extract_field_value(cf_with_type)
        assert result == 0.15

        # Scenario 2: resource_subtype is missing (fallback case)
        cf_without_type = {
            "gid": "cf-discount",
            "name": "Discount",
            "resource_subtype": None,
            "number_value": 0.15,
            "display_value": "15%",
        }
        result = cascade_plugin._extract_field_value(cf_without_type)
        assert result == 0.15

        # Scenario 3: resource_subtype is unknown
        cf_unknown_type = {
            "gid": "cf-discount",
            "name": "Discount",
            "resource_subtype": "percentage",  # Not a standard Asana type
            "number_value": 0.15,
            "display_value": "15%",
        }
        result = cascade_plugin._extract_field_value(cf_unknown_type)
        assert result == 0.15
