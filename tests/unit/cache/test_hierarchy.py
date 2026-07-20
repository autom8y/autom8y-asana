"""Tests for HierarchyIndex.

Per TDD-UNIFIED-CACHE-001: Validates parent-child tracking,
ancestor chain resolution, and cascade invalidation support.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from autom8_asana.cache.policies.hierarchy import HierarchyIndex


class TestHierarchyIndexBasics:
    """Basic HierarchyIndex functionality tests."""

    def test_register_task_without_parent(self) -> None:
        """Test registering a root task (no parent)."""
        index = HierarchyIndex()
        task = {"gid": "root-1", "name": "Root Task"}

        index.register(task)

        assert index.contains("root-1")
        assert index.get_parent_gid("root-1") is None

    def test_register_task_with_parent(self) -> None:
        """Test registering a task with parent."""
        index = HierarchyIndex()
        parent = {"gid": "parent-1", "name": "Parent"}
        child = {"gid": "child-1", "name": "Child", "parent": {"gid": "parent-1"}}

        index.register(parent)
        index.register(child)

        assert index.get_parent_gid("child-1") == "parent-1"
        assert "child-1" in index.get_children_gids("parent-1")

    def test_register_with_entity_type(self) -> None:
        """Test registering task with entity type."""
        index = HierarchyIndex()
        task = {"gid": "task-1"}

        index.register(task, entity_type="Business")

        assert index.get_entity_type("task-1") == "Business"

    def test_register_missing_gid_raises(self) -> None:
        """Test that registering task without gid raises."""
        index = HierarchyIndex()

        with pytest.raises(ValueError, match="must have 'gid' field"):
            index.register({"name": "No GID"})

    def test_register_empty_task_raises(self) -> None:
        """Test that registering empty task raises."""
        index = HierarchyIndex()

        with pytest.raises(ValueError, match="must have 'gid' field"):
            index.register({})


class TestHierarchyIndexParentChild:
    """Tests for parent-child relationship tracking."""

    def test_get_parent_gid_not_registered(self) -> None:
        """Test get_parent_gid for unregistered task."""
        index = HierarchyIndex()

        assert index.get_parent_gid("not-exists") is None

    def test_get_children_gids_empty(self) -> None:
        """Test get_children_gids for task with no children."""
        index = HierarchyIndex()
        index.register({"gid": "task-1"})

        children = index.get_children_gids("task-1")
        assert children == set()

    def test_get_children_gids_multiple(self) -> None:
        """Test get_children_gids with multiple children."""
        index = HierarchyIndex()
        index.register({"gid": "parent"})
        index.register({"gid": "child-1", "parent": {"gid": "parent"}})
        index.register({"gid": "child-2", "parent": {"gid": "parent"}})
        index.register({"gid": "child-3", "parent": {"gid": "parent"}})

        children = index.get_children_gids("parent")
        assert children == {"child-1", "child-2", "child-3"}

    def test_parent_change_updates_relationships(self) -> None:
        """Test that changing parent updates both old and new parent's children."""
        index = HierarchyIndex()
        index.register({"gid": "parent-a"})
        index.register({"gid": "parent-b"})
        index.register({"gid": "child", "parent": {"gid": "parent-a"}})

        # Verify initial state
        assert index.get_parent_gid("child") == "parent-a"
        assert "child" in index.get_children_gids("parent-a")

        # Change parent
        index.register({"gid": "child", "parent": {"gid": "parent-b"}})

        # Verify updated state
        assert index.get_parent_gid("child") == "parent-b"
        assert "child" not in index.get_children_gids("parent-a")
        assert "child" in index.get_children_gids("parent-b")

    def test_children_gids_returns_copy(self) -> None:
        """Test that get_children_gids returns a copy."""
        index = HierarchyIndex()
        index.register({"gid": "parent"})
        index.register({"gid": "child", "parent": {"gid": "parent"}})

        children = index.get_children_gids("parent")
        children.add("external-modification")

        # Original should be unchanged
        assert "external-modification" not in index.get_children_gids("parent")


class TestHierarchyIndexAncestorChain:
    """Tests for ancestor chain traversal."""

    def test_ancestor_chain_root_task(self) -> None:
        """Test ancestor chain for root task (no ancestors)."""
        index = HierarchyIndex()
        index.register({"gid": "root"})

        chain = index.get_ancestor_chain("root")
        assert chain == []

    def test_ancestor_chain_single_parent(self) -> None:
        """Test ancestor chain with single parent."""
        index = HierarchyIndex()
        index.register({"gid": "parent"})
        index.register({"gid": "child", "parent": {"gid": "parent"}})

        chain = index.get_ancestor_chain("child")
        assert chain == ["parent"]

    def test_ancestor_chain_multi_level(self) -> None:
        """Test ancestor chain with multiple levels."""
        index = HierarchyIndex()
        index.register({"gid": "grandparent"})
        index.register({"gid": "parent", "parent": {"gid": "grandparent"}})
        index.register({"gid": "child", "parent": {"gid": "parent"}})

        chain = index.get_ancestor_chain("child")
        assert chain == ["parent", "grandparent"]

    def test_ancestor_chain_respects_max_depth(self) -> None:
        """Test that ancestor chain respects max_depth."""
        index = HierarchyIndex()

        # Create a 5-level hierarchy
        index.register({"gid": "level-0"})
        for i in range(1, 6):
            index.register({"gid": f"level-{i}", "parent": {"gid": f"level-{i - 1}"}})

        # Get chain with max_depth=2
        chain = index.get_ancestor_chain("level-5", max_depth=2)
        assert chain == ["level-4", "level-3"]

    def test_ancestor_chain_not_registered(self) -> None:
        """Test ancestor chain for unregistered task."""
        index = HierarchyIndex()

        chain = index.get_ancestor_chain("not-exists")
        assert chain == []


class TestHierarchyIndexDescendants:
    """Tests for descendant traversal."""

    def test_descendant_gids_leaf_task(self) -> None:
        """Test descendants for leaf task (no children)."""
        index = HierarchyIndex()
        index.register({"gid": "leaf"})

        descendants = index.get_descendant_gids("leaf")
        assert descendants == set()

    def test_descendant_gids_single_level(self) -> None:
        """Test descendants with single level of children."""
        index = HierarchyIndex()
        index.register({"gid": "parent"})
        index.register({"gid": "child-1", "parent": {"gid": "parent"}})
        index.register({"gid": "child-2", "parent": {"gid": "parent"}})

        descendants = index.get_descendant_gids("parent")
        assert descendants == {"child-1", "child-2"}

    def test_descendant_gids_multi_level(self) -> None:
        """Test descendants with multiple levels."""
        index = HierarchyIndex()
        index.register({"gid": "root"})
        index.register({"gid": "child-1", "parent": {"gid": "root"}})
        index.register({"gid": "child-2", "parent": {"gid": "root"}})
        index.register({"gid": "grandchild-1", "parent": {"gid": "child-1"}})
        index.register({"gid": "grandchild-2", "parent": {"gid": "child-1"}})

        descendants = index.get_descendant_gids("root")
        assert descendants == {"child-1", "child-2", "grandchild-1", "grandchild-2"}

    def test_descendant_gids_respects_max_depth(self) -> None:
        """Test that descendants respects max_depth."""
        index = HierarchyIndex()
        index.register({"gid": "root"})
        index.register({"gid": "child", "parent": {"gid": "root"}})
        index.register({"gid": "grandchild", "parent": {"gid": "child"}})
        index.register({"gid": "great-grandchild", "parent": {"gid": "grandchild"}})

        # Get only first level
        descendants = index.get_descendant_gids("root", max_depth=1)
        assert descendants == {"child"}

        # Get first two levels
        descendants = index.get_descendant_gids("root", max_depth=2)
        assert descendants == {"child", "grandchild"}


class TestHierarchyIndexRoot:
    """Tests for root GID resolution."""

    def test_get_root_gid_is_root(self) -> None:
        """Test get_root_gid for root task (returns self)."""
        index = HierarchyIndex()
        index.register({"gid": "root"})

        root = index.get_root_gid("root")
        assert root == "root"

    def test_get_root_gid_traverses_to_root(self) -> None:
        """Test get_root_gid traverses to ultimate ancestor."""
        index = HierarchyIndex()
        index.register({"gid": "grandparent"})
        index.register({"gid": "parent", "parent": {"gid": "grandparent"}})
        index.register({"gid": "child", "parent": {"gid": "parent"}})

        assert index.get_root_gid("child") == "grandparent"
        assert index.get_root_gid("parent") == "grandparent"
        assert index.get_root_gid("grandparent") == "grandparent"

    def test_get_root_gid_not_registered(self) -> None:
        """Test get_root_gid for unregistered task."""
        index = HierarchyIndex()

        root = index.get_root_gid("not-exists")
        assert root is None


class TestHierarchyIndexRemoval:
    """Tests for task removal."""

    def test_remove_task(self) -> None:
        """Test removing a task from index."""
        index = HierarchyIndex()
        index.register({"gid": "task"})

        assert index.contains("task")

        index.remove("task")

        assert not index.contains("task")

    def test_remove_updates_parent_children(self) -> None:
        """Test that remove updates parent's children set."""
        index = HierarchyIndex()
        index.register({"gid": "parent"})
        index.register({"gid": "child", "parent": {"gid": "parent"}})

        assert "child" in index.get_children_gids("parent")

        index.remove("child")

        assert "child" not in index.get_children_gids("parent")

    def test_remove_nonexistent_is_safe(self) -> None:
        """Test that removing nonexistent task is safe."""
        index = HierarchyIndex()

        # Should not raise
        index.remove("not-exists")


class TestHierarchyIndexMisc:
    """Miscellaneous HierarchyIndex tests."""

    def test_len(self) -> None:
        """Test __len__ returns task count."""
        index = HierarchyIndex()

        assert len(index) == 0

        index.register({"gid": "task-1"})
        assert len(index) == 1

        index.register({"gid": "task-2"})
        assert len(index) == 2

    def test_clear(self) -> None:
        """Test clearing the index."""
        index = HierarchyIndex()
        index.register({"gid": "task-1"})
        index.register({"gid": "task-2", "parent": {"gid": "task-1"}})

        assert len(index) == 2

        index.clear()

        assert len(index) == 0
        assert not index.contains("task-1")
        assert not index.contains("task-2")

    def test_get_stats(self) -> None:
        """Test get_stats returns correct counts."""
        index = HierarchyIndex()
        index.register({"gid": "root-1"})
        index.register({"gid": "root-2"})
        index.register({"gid": "child-1", "parent": {"gid": "root-1"}})

        stats = index.get_stats()

        assert stats["task_count"] == 3
        assert stats["root_count"] == 2  # root-1 and root-2
        assert stats["children_map_size"] == 1  # Only root-1 has children


class TestHierarchyIndexThreadSafety:
    """Thread safety tests for HierarchyIndex."""

    def test_concurrent_register(self) -> None:
        """Test concurrent registration is thread-safe."""
        index = HierarchyIndex()
        num_tasks = 1000

        def register_task(i: int) -> None:
            index.register({"gid": f"task-{i}"})

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(register_task, range(num_tasks)))

        assert len(index) == num_tasks

    def test_concurrent_read_write(self) -> None:
        """Test concurrent reads and writes are thread-safe."""
        index = HierarchyIndex()
        num_operations = 500
        errors: list[Exception] = []

        # Register initial tasks
        index.register({"gid": "parent"})
        for i in range(100):
            index.register({"gid": f"child-{i}", "parent": {"gid": "parent"}})

        def read_operation() -> None:
            try:
                for _ in range(num_operations):
                    index.get_children_gids("parent")
                    index.get_ancestor_chain("child-50")
                    index.get_root_gid("child-50")
            except Exception as e:
                errors.append(e)

        def write_operation() -> None:
            try:
                for i in range(num_operations):
                    index.register({"gid": f"new-{threading.current_thread().name}-{i}"})
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=read_operation))
            threads.append(threading.Thread(target=write_operation))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestHierarchyIndexEdgeCases:
    """Edge case tests for HierarchyIndex."""

    def test_register_with_none_parent_gid(self) -> None:
        """Test registering task where parent dict exists but gid is None."""
        index = HierarchyIndex()

        # Parent dict exists but gid is None
        task = {"gid": "task-1", "parent": {"gid": None}}
        index.register(task)

        assert index.get_parent_gid("task-1") is None

    def test_register_with_empty_parent_dict(self) -> None:
        """Test registering task with empty parent dict."""
        index = HierarchyIndex()

        task = {"gid": "task-1", "parent": {}}
        index.register(task)

        assert index.get_parent_gid("task-1") is None

    def test_register_with_non_dict_parent(self) -> None:
        """Test registering task where parent is not a dict."""
        index = HierarchyIndex()

        # Parent is a string (shouldn't happen but handle gracefully)
        task = {"gid": "task-1", "parent": "parent-gid-string"}
        index.register(task)

        # Should treat as no parent
        assert index.get_parent_gid("task-1") is None

    def test_deep_hierarchy(self) -> None:
        """Test with deep hierarchy (10+ levels)."""
        index = HierarchyIndex()
        depth = 15

        # Build deep chain
        index.register({"gid": "level-0"})
        for i in range(1, depth):
            index.register({"gid": f"level-{i}", "parent": {"gid": f"level-{i - 1}"}})

        # Test ancestor chain
        chain = index.get_ancestor_chain(f"level-{depth - 1}", max_depth=20)
        assert len(chain) == depth - 1
        assert chain[0] == f"level-{depth - 2}"
        assert chain[-1] == "level-0"

        # Test root
        assert index.get_root_gid(f"level-{depth - 1}") == "level-0"

        # Test descendants
        descendants = index.get_descendant_gids("level-0")
        assert len(descendants) == depth - 1
