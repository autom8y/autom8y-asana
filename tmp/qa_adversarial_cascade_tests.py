#!/usr/bin/env python3
"""QA Adversarial Tests for Unit Cascade Resolution Fix.

Per PRD-unit-cascade-resolution-fix Success Criteria validation.
Tests edge cases that could cause cascade field resolution to fail.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock


# =============================================================================
# Test 1: Orphan Task (no parent) - should return None gracefully
# =============================================================================


async def test_orphan_task_cascade_returns_none():
    """Orphan task with no parent should return None for cascade fields.

    Edge case: Task exists at top level with no parent reference.
    Expected: cascade:field should return None, not error.
    """
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.cache.entry import CacheEntry, EntryType
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin
    from autom8_asana.dataframes.models.schema import DataFrameSchema, ColumnDef
    from autom8_asana.cache.completeness import CompletenessLevel
    from datetime import datetime, timezone

    # Create orphan task with no parent
    orphan_task = {
        "gid": "orphan_123",
        "name": "Orphan Task",
        "parent": None,  # No parent
        "custom_fields": [],
        "modified_at": "2024-01-01T00:00:00Z",
    }

    # Create mock cache with completeness metadata
    mock_cache = MagicMock()
    mock_entry = CacheEntry(
        key="orphan_123",
        data=orphan_task,
        entry_type=EntryType.TASK,
        version=datetime.now(timezone.utc),
        cached_at=datetime.now(timezone.utc),
        metadata={"completeness_level": CompletenessLevel.STANDARD.value},
    )
    mock_cache.get_versioned.return_value = mock_entry
    mock_cache.get_batch.return_value = {"orphan_123": mock_entry}

    # Create store with empty hierarchy (no parent registered)
    store = UnifiedTaskStore(cache=mock_cache)

    # Create schema with cascade field
    schema = DataFrameSchema(
        name="test",
        task_type="*",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", nullable=False),
            ColumnDef(
                name="office_phone",
                dtype="Utf8",
                nullable=True,
                source="cascade:Office Phone",
            ),
        ],
        version="1.0.0",
    )

    plugin = DataFrameViewPlugin(store=store, schema=schema)

    # Materialize should return None for cascade field (no parent to cascade from)
    from autom8_asana.cache.freshness_coordinator import FreshnessMode

    df = await plugin.materialize_async(
        task_gids=["orphan_123"], freshness=FreshnessMode.IMMEDIATE
    )

    assert len(df) == 1
    assert df["gid"][0] == "orphan_123"
    assert df["office_phone"][0] is None  # Should be None, not error

    print("[PASS] test_orphan_task_cascade_returns_none")


# =============================================================================
# Test 2: Parent exists but missing custom_fields - should handle gracefully
# =============================================================================


async def test_parent_missing_custom_fields():
    """Parent task exists but has no custom_fields array.

    Edge case: Parent was fetched with minimal opt_fields that didn't include
    custom_fields data.
    Expected: cascade should return None gracefully.
    """
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.cache.entry import CacheEntry, EntryType
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin
    from autom8_asana.dataframes.models.schema import DataFrameSchema, ColumnDef
    from autom8_asana.cache.completeness import CompletenessLevel
    from autom8_asana.cache.freshness_coordinator import FreshnessMode
    from datetime import datetime, timezone

    # Child task with parent reference
    child_task = {
        "gid": "child_123",
        "name": "Child Task",
        "parent": {"gid": "parent_456"},
        "custom_fields": [],
        "modified_at": "2024-01-01T00:00:00Z",
    }

    # Parent task WITHOUT custom_fields key
    parent_task = {
        "gid": "parent_456",
        "name": "Parent Task",
        # "custom_fields" key is MISSING entirely
        "parent": None,
        "modified_at": "2024-01-01T00:00:00Z",
    }

    # Create mock cache with completeness metadata
    mock_cache = MagicMock()
    child_entry = CacheEntry(
        key="child_123",
        data=child_task,
        entry_type=EntryType.TASK,
        version=datetime.now(timezone.utc),
        cached_at=datetime.now(timezone.utc),
        metadata={"completeness_level": CompletenessLevel.STANDARD.value},
    )
    parent_entry = CacheEntry(
        key="parent_456",
        data=parent_task,
        entry_type=EntryType.TASK,
        version=datetime.now(timezone.utc),
        cached_at=datetime.now(timezone.utc),
        metadata={"completeness_level": CompletenessLevel.STANDARD.value},
    )

    mock_cache.get_versioned.side_effect = lambda gid, _: {
        "child_123": child_entry,
        "parent_456": parent_entry,
    }.get(gid)
    mock_cache.get_batch.return_value = {
        "child_123": child_entry,
        "parent_456": parent_entry,
    }

    store = UnifiedTaskStore(cache=mock_cache)
    # Register parent-child relationship
    store.get_hierarchy_index().register(child_task)
    store.get_hierarchy_index().register(parent_task)

    schema = DataFrameSchema(
        name="test",
        task_type="*",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", nullable=False),
            ColumnDef(
                name="office_phone",
                dtype="Utf8",
                nullable=True,
                source="cascade:Office Phone",
            ),
        ],
        version="1.0.0",
    )

    plugin = DataFrameViewPlugin(store=store, schema=schema)

    # Should not error, just return None for cascade field
    df = await plugin.materialize_async(
        task_gids=["child_123"], freshness=FreshnessMode.IMMEDIATE
    )

    assert len(df) == 1
    assert df["gid"][0] == "child_123"
    assert df["office_phone"][0] is None  # Gracefully returns None

    print("[PASS] test_parent_missing_custom_fields")


# =============================================================================
# Test 3: Parent has custom_fields but field not present - should return None
# =============================================================================


async def test_parent_field_not_present():
    """Parent has custom_fields but not the specific field we're looking for.

    Edge case: Parent has some custom fields but not "Office Phone".
    Expected: cascade should return None (field not found in chain).
    """
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.cache.entry import CacheEntry, EntryType
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin
    from autom8_asana.dataframes.models.schema import DataFrameSchema, ColumnDef
    from autom8_asana.cache.completeness import CompletenessLevel
    from autom8_asana.cache.freshness_coordinator import FreshnessMode
    from datetime import datetime, timezone

    child_task = {
        "gid": "child_123",
        "name": "Child Task",
        "parent": {"gid": "parent_456"},
        "custom_fields": [],
        "modified_at": "2024-01-01T00:00:00Z",
    }

    parent_task = {
        "gid": "parent_456",
        "name": "Parent Task",
        "custom_fields": [
            # Has custom fields, but NOT "Office Phone"
            {
                "gid": "cf_1",
                "name": "Company ID",
                "resource_subtype": "text",
                "text_value": "ACME001",
            },
            {
                "gid": "cf_2",
                "name": "Industry",
                "resource_subtype": "enum",
                "enum_value": {"name": "Healthcare"},
            },
        ],
        "parent": None,
        "modified_at": "2024-01-01T00:00:00Z",
    }

    mock_cache = MagicMock()
    child_entry = CacheEntry(
        key="child_123",
        data=child_task,
        entry_type=EntryType.TASK,
        version=datetime.now(timezone.utc),
        cached_at=datetime.now(timezone.utc),
        metadata={"completeness_level": CompletenessLevel.STANDARD.value},
    )
    parent_entry = CacheEntry(
        key="parent_456",
        data=parent_task,
        entry_type=EntryType.TASK,
        version=datetime.now(timezone.utc),
        cached_at=datetime.now(timezone.utc),
        metadata={"completeness_level": CompletenessLevel.STANDARD.value},
    )

    mock_cache.get_versioned.side_effect = lambda gid, _: {
        "child_123": child_entry,
        "parent_456": parent_entry,
    }.get(gid)
    mock_cache.get_batch.return_value = {
        "child_123": child_entry,
        "parent_456": parent_entry,
    }

    store = UnifiedTaskStore(cache=mock_cache)
    store.get_hierarchy_index().register(child_task)
    store.get_hierarchy_index().register(parent_task)

    schema = DataFrameSchema(
        name="test",
        task_type="*",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", nullable=False),
            ColumnDef(
                name="office_phone",
                dtype="Utf8",
                nullable=True,
                source="cascade:Office Phone",
            ),
        ],
        version="1.0.0",
    )

    plugin = DataFrameViewPlugin(store=store, schema=schema)
    df = await plugin.materialize_async(
        task_gids=["child_123"], freshness=FreshnessMode.IMMEDIATE
    )

    assert len(df) == 1
    assert df["office_phone"][0] is None  # Field not found in parent chain

    print("[PASS] test_parent_field_not_present")


# =============================================================================
# Test 4: max_depth limit - should stop traversal at depth limit
# =============================================================================


async def test_max_depth_limit():
    """Test that hierarchy traversal respects max_depth setting.

    Edge case: Very deep hierarchy that could cause performance issues.
    Expected: Traversal should stop at max_depth (default 5).
    """
    from autom8_asana.cache.hierarchy import HierarchyIndex

    # Create a 10-level deep hierarchy
    hierarchy = HierarchyIndex()

    # Level 0 is root, levels 1-9 are children
    tasks = []
    for i in range(10):
        task = {
            "gid": f"task_{i}",
            "name": f"Task Level {i}",
            "parent": {"gid": f"task_{i - 1}"} if i > 0 else None,
        }
        tasks.append(task)
        hierarchy.register(task)

    # Get ancestor chain from deepest task (task_9)
    # With max_depth=5, should only get 5 ancestors
    ancestors = hierarchy.get_ancestor_chain("task_9", max_depth=5)

    assert len(ancestors) == 5, f"Expected 5 ancestors, got {len(ancestors)}"

    # Should be task_8, task_7, task_6, task_5, task_4 (5 ancestors)
    expected = ["task_8", "task_7", "task_6", "task_5", "task_4"]
    assert ancestors == expected, f"Expected {expected}, got {ancestors}"

    # Without limit, should get all 9 ancestors
    all_ancestors = hierarchy.get_ancestor_chain("task_9", max_depth=100)
    assert len(all_ancestors) == 9

    print("[PASS] test_max_depth_limit")


# =============================================================================
# Test 5: Circular parent reference - should not infinite loop
# =============================================================================


async def test_circular_reference_protection():
    """Test protection against circular parent references.

    Edge case: Corrupt data where task A -> B -> A (circular).
    Expected: Should detect cycle and stop, not infinite loop.
    """
    from autom8_asana.cache.hierarchy import HierarchyIndex

    hierarchy = HierarchyIndex()

    # Create circular reference: A -> B -> C -> A
    task_a = {"gid": "task_a", "name": "Task A", "parent": {"gid": "task_c"}}
    task_b = {"gid": "task_b", "name": "Task B", "parent": {"gid": "task_a"}}
    task_c = {"gid": "task_c", "name": "Task C", "parent": {"gid": "task_b"}}

    hierarchy.register(task_a)
    hierarchy.register(task_b)
    hierarchy.register(task_c)

    # Should not hang or infinite loop - max_depth protects us
    import asyncio

    async def test_with_timeout():
        # This should complete quickly even with circular ref due to max_depth
        ancestors = hierarchy.get_ancestor_chain("task_a", max_depth=5)
        return ancestors

    try:
        ancestors = await asyncio.wait_for(test_with_timeout(), timeout=2.0)
        # Should have stopped at max_depth
        assert len(ancestors) <= 5, (
            f"Got more ancestors than max_depth: {len(ancestors)}"
        )
        print("[PASS] test_circular_reference_protection - stopped at max_depth")
    except asyncio.TimeoutError:
        print("[FAIL] test_circular_reference_protection - infinite loop detected!")
        raise AssertionError("Infinite loop detected in circular reference handling")


# =============================================================================
# Test 6: Enum field cascade - should extract enum name correctly
# =============================================================================


async def test_enum_field_cascade():
    """Test cascade resolution for enum custom fields (like Vertical).

    Edge case: Vertical is an enum field, not text, and needs special extraction.
    Expected: Should extract enum_value.name properly.
    """
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.cache.entry import CacheEntry, EntryType
    from datetime import datetime, timezone

    # Business task with Vertical enum field
    business_task = {
        "gid": "business_123",
        "name": "Healthcare Business",
        "parent": None,
        "custom_fields": [
            {
                "gid": "cf_vertical",
                "name": "Vertical",
                "resource_subtype": "enum",
                "enum_value": {"gid": "enum_chiro", "name": "Chiropractic"},
            },
        ],
        "modified_at": "2024-01-01T00:00:00Z",
    }

    mock_cache = MagicMock()
    business_entry = CacheEntry(
        key="business_123",
        data=business_task,
        entry_type=EntryType.TASK,
        version=datetime.now(timezone.utc),
        cached_at=datetime.now(timezone.utc),
    )
    mock_cache.get_versioned.return_value = business_entry
    mock_cache.get_batch.return_value = {"business_123": business_entry}

    store = UnifiedTaskStore(cache=mock_cache)
    store.get_hierarchy_index().register(business_task)

    cascade_plugin = CascadeViewPlugin(store=store)

    # Extract enum value from dict
    value = cascade_plugin._get_custom_field_value_from_dict(business_task, "Vertical")

    assert value == "Chiropractic", f"Expected 'Chiropractic', got '{value}'"

    print("[PASS] test_enum_field_cascade")


# =============================================================================
# Test 7: Case-insensitive field name matching
# =============================================================================


async def test_case_insensitive_field_matching():
    """Test that field name matching is case-insensitive.

    Edge case: Field in schema is "office_phone" but API returns "Office Phone".
    Expected: Should match regardless of case.
    """
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
    from autom8_asana.cache.unified import UnifiedTaskStore

    # Task with mixed case field name
    task = {
        "gid": "task_123",
        "name": "Test Task",
        "custom_fields": [
            {
                "gid": "cf_phone",
                "name": "OFFICE PHONE",  # UPPERCASE
                "resource_subtype": "text",
                "text_value": "+15551234567",
            },
        ],
    }

    mock_cache = MagicMock()
    store = UnifiedTaskStore(cache=mock_cache)
    cascade_plugin = CascadeViewPlugin(store=store)

    # Try to find with different cases
    value1 = cascade_plugin._get_custom_field_value_from_dict(
        task, "office phone"
    )  # lowercase
    value2 = cascade_plugin._get_custom_field_value_from_dict(
        task, "Office Phone"
    )  # title case
    value3 = cascade_plugin._get_custom_field_value_from_dict(
        task, "OFFICE PHONE"
    )  # uppercase

    assert value1 == "+15551234567", f"Lowercase lookup failed: {value1}"
    assert value2 == "+15551234567", f"Title case lookup failed: {value2}"
    assert value3 == "+15551234567", f"Uppercase lookup failed: {value3}"

    print("[PASS] test_case_insensitive_field_matching")


# =============================================================================
# Test 8: Empty custom_fields array - should return None gracefully
# =============================================================================


async def test_empty_custom_fields_array():
    """Test handling of empty custom_fields array.

    Edge case: Parent task exists with custom_fields: [] (empty array).
    Expected: Should return None gracefully.
    """
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
    from autom8_asana.cache.unified import UnifiedTaskStore

    task = {
        "gid": "task_123",
        "name": "Test Task",
        "custom_fields": [],  # Empty array
    }

    mock_cache = MagicMock()
    store = UnifiedTaskStore(cache=mock_cache)
    cascade_plugin = CascadeViewPlugin(store=store)

    value = cascade_plugin._get_custom_field_value_from_dict(task, "Office Phone")

    assert value is None, f"Expected None for empty custom_fields, got {value}"

    print("[PASS] test_empty_custom_fields_array")


# =============================================================================
# Run all tests
# =============================================================================


async def run_all_tests():
    """Run all adversarial tests."""
    print("=" * 60)
    print("QA ADVERSARIAL TESTS - Unit Cascade Resolution Fix")
    print("=" * 60)
    print()

    tests = [
        ("1. Orphan Task (no parent)", test_orphan_task_cascade_returns_none),
        ("2. Parent missing custom_fields", test_parent_missing_custom_fields),
        ("3. Parent field not present", test_parent_field_not_present),
        ("4. max_depth limit", test_max_depth_limit),
        ("5. Circular reference protection", test_circular_reference_protection),
        ("6. Enum field cascade", test_enum_field_cascade),
        ("7. Case-insensitive matching", test_case_insensitive_field_matching),
        ("8. Empty custom_fields array", test_empty_custom_fields_array),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nRunning: {name}")
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
