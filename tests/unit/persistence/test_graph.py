"""Tests for DependencyGraph.

Per TDD-0010: Verify Kahn's algorithm for dependency ordering per ADR-0037.
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.errors import CyclicDependencyError
from autom8_asana.persistence.graph import DependencyGraph

# ---------------------------------------------------------------------------
# Graph Building Tests
# ---------------------------------------------------------------------------


class TestGraphBuilding:
    """Tests for graph construction."""

    def test_build_empty_graph(self) -> None:
        """Building with empty entity list produces empty graph."""
        graph = DependencyGraph()
        graph.build([])

        result = graph.topological_sort()
        assert result == []

    def test_build_single_entity(self) -> None:
        """Building with single entity works."""
        graph = DependencyGraph()
        task = Task(gid="123", name="Single Task")

        graph.build([task])
        result = graph.topological_sort()

        assert result == [task]

    def test_build_detects_parent_child(self) -> None:
        """build() detects parent-child relationships from parent field."""
        graph = DependencyGraph()

        parent = Task(gid="parent", name="Parent Task")
        child = Task(gid="child", name="Child Task", parent=NameGid(gid="parent"))

        graph.build([parent, child])
        result = graph.topological_sort()

        # Parent must come before child
        assert result.index(parent) < result.index(child)

    def test_build_with_namegid_parent(self) -> None:
        """build() handles NameGid parent references."""
        graph = DependencyGraph()

        parent = Task(gid="111", name="Parent")
        child = Task(
            gid="222",
            name="Child",
            parent=NameGid(gid="111", name="Parent"),
        )

        graph.build([parent, child])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert parent in levels[0]
        assert child in levels[1]

    def test_build_with_string_parent(self) -> None:
        """build() handles string GID parent references."""
        graph = DependencyGraph()

        # Create a task with parent as NameGid (simulating API response)
        parent = Task(gid="parent_gid", name="Parent")
        child = Task(gid="child_gid", name="Child", parent=NameGid(gid="parent_gid"))

        graph.build([parent, child])
        result = graph.topological_sort()

        assert result.index(parent) < result.index(child)

    def test_build_with_direct_string_parent(self) -> None:
        """build() handles direct string parent references."""
        graph = DependencyGraph()

        # Simulate a case where parent is a raw string GID
        parent = Task(gid="parent_str", name="Parent")
        child = Task(gid="child_str", name="Child")
        # Set parent as raw string (unusual but possible)
        child.parent = "parent_str"  # type: ignore[assignment]

        graph.build([parent, child])
        result = graph.topological_sort()

        assert result.index(parent) < result.index(child)

    def test_build_ignores_external_parent(self) -> None:
        """build() ignores parent GIDs not in entity list."""
        graph = DependencyGraph()

        # Child references a parent not in the entity list
        child = Task(
            gid="child",
            name="Orphan Child",
            parent=NameGid(gid="external_parent"),
        )

        graph.build([child])
        result = graph.topological_sort()

        # Should still work - external dep is ignored
        assert result == [child]


# ---------------------------------------------------------------------------
# Topological Sort Tests
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    """Tests for topological sorting."""

    def test_topological_sort_correct_order(self) -> None:
        """topological_sort() returns correct dependency order."""
        graph = DependencyGraph()

        # Build a chain: A -> B -> C
        task_a = Task(gid="A", name="Task A")
        task_b = Task(gid="B", name="Task B", parent=NameGid(gid="A"))
        task_c = Task(gid="C", name="Task C", parent=NameGid(gid="B"))

        graph.build([task_c, task_a, task_b])  # Intentionally unordered
        result = graph.topological_sort()

        assert result.index(task_a) < result.index(task_b)
        assert result.index(task_b) < result.index(task_c)

    def test_topological_sort_raises_on_cycle(self) -> None:
        """topological_sort() raises CyclicDependencyError on cycle."""
        graph = DependencyGraph()

        # Create a cycle using AsanaResource entities directly
        # Note: We'll use NameGid since Task.parent expects that
        task_a = Task(gid="A", name="Task A", parent=NameGid(gid="B"))
        task_b = Task(gid="B", name="Task B", parent=NameGid(gid="A"))

        graph.build([task_a, task_b])

        with pytest.raises(CyclicDependencyError) as exc_info:
            graph.topological_sort()

        assert len(exc_info.value.cycle) > 0
        assert "Cyclic dependency detected" in str(exc_info.value)

    def test_topological_sort_independent_entities(self) -> None:
        """Independent entities can appear in any order."""
        graph = DependencyGraph()

        task_a = Task(gid="A", name="Task A")
        task_b = Task(gid="B", name="Task B")
        task_c = Task(gid="C", name="Task C")

        graph.build([task_a, task_b, task_c])
        result = graph.topological_sort()

        # All should be present (using list comparison since Task is unhashable)
        assert len(result) == 3
        assert task_a in result
        assert task_b in result
        assert task_c in result


# ---------------------------------------------------------------------------
# Level Grouping Tests
# ---------------------------------------------------------------------------


class TestGetLevels:
    """Tests for level-based grouping."""

    def test_get_levels_groups_independent(self) -> None:
        """get_levels() groups independent entities at same level."""
        graph = DependencyGraph()

        # Three independent tasks
        task_a = Task(gid="A", name="Task A")
        task_b = Task(gid="B", name="Task B")
        task_c = Task(gid="C", name="Task C")

        graph.build([task_a, task_b, task_c])
        levels = graph.get_levels()

        # All should be at level 0
        assert len(levels) == 1
        assert len(levels[0]) == 3
        assert task_a in levels[0]
        assert task_b in levels[0]
        assert task_c in levels[0]

    def test_get_levels_parents_before_children(self) -> None:
        """get_levels() puts parents in earlier levels than children."""
        graph = DependencyGraph()

        parent = Task(gid="parent", name="Parent")
        child1 = Task(gid="child1", name="Child 1", parent=NameGid(gid="parent"))
        child2 = Task(gid="child2", name="Child 2", parent=NameGid(gid="parent"))

        graph.build([child1, parent, child2])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert levels[0] == [parent]
        assert len(levels[1]) == 2
        assert child1 in levels[1]
        assert child2 in levels[1]

    def test_get_levels_deep_hierarchy(self) -> None:
        """get_levels() handles deep hierarchy correctly."""
        graph = DependencyGraph()

        # Create 4-level deep hierarchy
        level0 = Task(gid="L0", name="Level 0")
        level1 = Task(gid="L1", name="Level 1", parent=NameGid(gid="L0"))
        level2 = Task(gid="L2", name="Level 2", parent=NameGid(gid="L1"))
        level3 = Task(gid="L3", name="Level 3", parent=NameGid(gid="L2"))

        graph.build([level3, level1, level0, level2])  # Shuffled
        levels = graph.get_levels()

        assert len(levels) == 4
        assert levels[0] == [level0]
        assert levels[1] == [level1]
        assert levels[2] == [level2]
        assert levels[3] == [level3]

    def test_get_levels_multiple_independent_chains(self) -> None:
        """get_levels() handles multiple independent chains."""
        graph = DependencyGraph()

        # Chain 1: A -> B
        chain1_root = Task(gid="A", name="A")
        chain1_child = Task(gid="B", name="B", parent=NameGid(gid="A"))

        # Chain 2: X -> Y -> Z
        chain2_root = Task(gid="X", name="X")
        chain2_mid = Task(gid="Y", name="Y", parent=NameGid(gid="X"))
        chain2_leaf = Task(gid="Z", name="Z", parent=NameGid(gid="Y"))

        graph.build(
            [
                chain1_child,
                chain2_leaf,
                chain1_root,
                chain2_mid,
                chain2_root,
            ]
        )
        levels = graph.get_levels()

        # Level 0: both roots
        assert len(levels[0]) == 2
        assert chain1_root in levels[0]
        assert chain2_root in levels[0]

        # Level 1: first children
        assert len(levels[1]) == 2
        assert chain1_child in levels[1]
        assert chain2_mid in levels[1]

        # Level 2: only chain2 leaf
        assert levels[2] == [chain2_leaf]

    def test_get_levels_raises_on_cycle(self) -> None:
        """get_levels() raises CyclicDependencyError on cycle."""
        graph = DependencyGraph()

        task_a = Task(gid="A", parent=NameGid(gid="B"))
        task_b = Task(gid="B", parent=NameGid(gid="C"))
        task_c = Task(gid="C", parent=NameGid(gid="A"))

        graph.build([task_a, task_b, task_c])

        with pytest.raises(CyclicDependencyError):
            graph.get_levels()

    def test_get_levels_empty_graph(self) -> None:
        """get_levels() returns empty list for empty graph."""
        graph = DependencyGraph()
        graph.build([])

        levels = graph.get_levels()
        assert levels == []


# ---------------------------------------------------------------------------
# Explicit Dependency Tests
# ---------------------------------------------------------------------------


class TestExplicitDependency:
    """Tests for explicit dependency declaration."""

    def test_add_explicit_dependency(self) -> None:
        """add_explicit_dependency() creates edge between entities."""
        graph = DependencyGraph()

        # Two independent tasks
        task_a = Task(gid="A", name="Task A")
        task_b = Task(gid="B", name="Task B")

        graph.build([task_a, task_b])

        # Add explicit dependency: B depends on A
        graph.add_explicit_dependency(dependent=task_b, dependency=task_a)

        levels = graph.get_levels()

        assert len(levels) == 2
        assert task_a in levels[0]
        assert task_b in levels[1]

    def test_add_explicit_dependency_with_existing(self) -> None:
        """add_explicit_dependency() works with existing parent deps."""
        graph = DependencyGraph()

        # A -> B (parent relationship)
        task_a = Task(gid="A", name="A")
        task_b = Task(gid="B", name="B", parent=NameGid(gid="A"))
        task_c = Task(gid="C", name="C")

        graph.build([task_a, task_b, task_c])

        # Add: C depends on B
        graph.add_explicit_dependency(dependent=task_c, dependency=task_b)

        levels = graph.get_levels()

        assert len(levels) == 3
        assert task_a in levels[0]
        assert task_b in levels[1]
        assert task_c in levels[2]

    def test_add_explicit_dependency_ignores_unknown_entities(self) -> None:
        """add_explicit_dependency() is no-op for unknown entities."""
        graph = DependencyGraph()

        task_a = Task(gid="A")
        task_b = Task(gid="B")
        external = Task(gid="external")

        graph.build([task_a, task_b])

        # Try to add dependency with entity not in graph
        graph.add_explicit_dependency(dependent=task_a, dependency=external)

        # Should not affect the graph
        levels = graph.get_levels()
        assert len(levels) == 1
        assert len(levels[0]) == 2
        assert task_a in levels[0]
        assert task_b in levels[0]


# ---------------------------------------------------------------------------
# Handles No Dependencies Tests
# ---------------------------------------------------------------------------


class TestNoDependencies:
    """Tests for graphs with no dependencies."""

    def test_handles_no_dependencies(self) -> None:
        """Graph with no dependencies processes correctly."""
        graph = DependencyGraph()

        tasks = [Task(gid=str(i), name=f"Task {i}") for i in range(5)]

        graph.build(tasks)
        result = graph.topological_sort()

        assert len(result) == 5
        for task in tasks:
            assert task in result

    def test_levels_with_no_dependencies(self) -> None:
        """All entities at level 0 when no dependencies."""
        graph = DependencyGraph()

        tasks = [Task(gid=str(i)) for i in range(3)]

        graph.build(tasks)
        levels = graph.get_levels()

        assert len(levels) == 1
        assert len(levels[0]) == 3
        for task in tasks:
            assert task in levels[0]


# ---------------------------------------------------------------------------
# New Entity (Temp GID) Tests
# ---------------------------------------------------------------------------


class TestNewEntities:
    """Tests for new entities with temp GIDs.

    Note: In real usage, temp GIDs are generated using temp_{id(entity)}.
    These tests use real GIDs to verify dependency detection.
    """

    def test_new_entity_dependency(self) -> None:
        """New entities with dependencies are handled correctly."""
        graph = DependencyGraph()

        # Use real GIDs - temp GID behavior tested separately
        parent = Task(gid="parent_gid", name="New Parent")
        child = Task(gid="child_gid", name="New Child")

        # Child's parent reference points to the parent's GID
        child.parent = NameGid(gid="parent_gid")

        graph.build([parent, child])
        result = graph.topological_sort()

        assert result.index(parent) < result.index(child)

    def test_entity_reference_as_parent(self) -> None:
        """Entity object reference as parent is resolved."""
        graph = DependencyGraph()

        # Use real GIDs for predictable behavior
        parent = Task(gid="real_parent", name="Parent")
        child = Task(gid="real_child", name="Child", parent=NameGid(gid="real_parent"))

        graph.build([parent, child])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert parent in levels[0]
        assert child in levels[1]

    def test_temp_gid_generation(self) -> None:
        """Entities with temp_* GIDs get regenerated temp GIDs."""
        graph = DependencyGraph()

        # Entity with a temp_* GID will get regenerated
        task_with_temp = Task(gid="temp_user_provided", name="Task")

        graph.build([task_with_temp])
        result = graph.topological_sort()

        # Should still work - one entity
        assert len(result) == 1
        assert result[0] is task_with_temp

    def test_entity_as_direct_parent_reference(self) -> None:
        """Entity object used directly as parent is resolved."""
        graph = DependencyGraph()

        # Parent entity with temp GID
        parent = Task(gid="temp_parent", name="Parent")
        # Child with parent set as the actual entity object (not NameGid)
        # This tests the entity identity resolution path
        child = Task(gid="child_gid", name="Child")
        # Set parent to the actual parent entity (simulating user code)
        child.parent = parent  # type: ignore[assignment]

        graph.build([parent, child])
        levels = graph.get_levels()

        # Parent should still be resolved via identity
        assert len(levels) == 2
        assert parent in levels[0]
        assert child in levels[1]


# ---------------------------------------------------------------------------
# Graph Rebuild Tests
# ---------------------------------------------------------------------------


class TestGraphRebuild:
    """Tests for rebuilding the graph."""

    def test_build_clears_previous_state(self) -> None:
        """build() clears previous graph state."""
        graph = DependencyGraph()

        # First build
        task_old = Task(gid="old")
        graph.build([task_old])

        # Second build with different entities
        task_new = Task(gid="new")
        graph.build([task_new])

        result = graph.topological_sort()

        assert task_old not in result
        assert result == [task_new]

    def test_rebuild_with_different_dependencies(self) -> None:
        """Rebuilding changes dependency structure."""
        graph = DependencyGraph()

        task_a = Task(gid="A")
        task_b = Task(gid="B", parent=NameGid(gid="A"))

        # Build with dependency
        graph.build([task_a, task_b])
        levels1 = graph.get_levels()
        assert len(levels1) == 2

        # Rebuild with same entities but no dependency
        task_b_no_parent = Task(gid="B")
        graph.build([task_a, task_b_no_parent])
        levels2 = graph.get_levels()

        # Now both at level 0
        assert len(levels2) == 1


# ---------------------------------------------------------------------------
# Complex Hierarchy Tests
# ---------------------------------------------------------------------------


class TestComplexHierarchy:
    """Tests for complex dependency hierarchies."""

    def test_diamond_dependency(self) -> None:
        """Diamond dependency pattern is handled correctly."""
        graph = DependencyGraph()

        #     A
        #    / \
        #   B   C
        #    \ /
        #     D

        task_a = Task(gid="A", name="A")
        task_b = Task(gid="B", name="B", parent=NameGid(gid="A"))
        task_c = Task(gid="C", name="C", parent=NameGid(gid="A"))
        task_d = Task(gid="D", name="D", parent=NameGid(gid="B"))

        graph.build([task_d, task_b, task_c, task_a])

        # Add explicit dep: D also depends on C
        graph.add_explicit_dependency(dependent=task_d, dependency=task_c)

        result = graph.topological_sort()

        # A must come first, then B and C (in any order), then D
        assert result.index(task_a) < result.index(task_b)
        assert result.index(task_a) < result.index(task_c)
        assert result.index(task_b) < result.index(task_d)
        assert result.index(task_c) < result.index(task_d)

    def test_wide_and_deep_hierarchy(self) -> None:
        """Wide and deep hierarchy is processed efficiently."""
        graph = DependencyGraph()

        # Root with 5 children, each with 2 grandchildren
        root = Task(gid="root", name="Root")
        children = [
            Task(gid=f"child_{i}", name=f"Child {i}", parent=NameGid(gid="root")) for i in range(5)
        ]
        grandchildren = [
            Task(
                gid=f"gc_{c}_{g}",
                name=f"GC {c}_{g}",
                parent=NameGid(gid=f"child_{c}"),
            )
            for c in range(5)
            for g in range(2)
        ]

        all_tasks = [root] + children + grandchildren
        graph.build(all_tasks)

        result = graph.topological_sort()

        assert len(result) == 16  # 1 + 5 + 10

        # Root first, then children, then grandchildren
        root_idx = result.index(root)
        for child in children:
            assert result.index(child) > root_idx
            for gc in grandchildren:
                if gc.parent and gc.parent.gid == child.gid:
                    assert result.index(gc) > result.index(child)

    def test_self_referential_raises_cycle(self) -> None:
        """Self-referential entity raises CyclicDependencyError."""
        graph = DependencyGraph()

        # Task that references itself as parent
        task = Task(gid="self_ref", name="Self", parent=NameGid(gid="self_ref"))

        graph.build([task])

        with pytest.raises(CyclicDependencyError):
            graph.topological_sort()
