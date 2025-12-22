"""Part 2: Dependency Ordering Validation Tests.

Tests DependencyGraph correctness using Kahn's algorithm for topological sort.

Test Coverage:
- FR-DEPEND-001: Detect parent-child relationships from parent field
- FR-DEPEND-002: Use Kahn's algorithm with O(V+E) complexity
- FR-DEPEND-003: Raise CyclicDependencyError if cycle detected
- FR-DEPEND-007: Group independent entities for parallel batching
- FR-DEPEND-008: Support explicit dependency declaration
- ADR-0037: Kahn's algorithm for dependency ordering
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.exceptions import CyclicDependencyError
from autom8_asana.persistence.graph import DependencyGraph


# ---------------------------------------------------------------------------
# Parent-Child Ordering Tests
# ---------------------------------------------------------------------------


class TestParentChildOrdering:
    """Test parent saves before child (FR-DEPEND-001)."""

    def test_parent_before_child_in_levels(self) -> None:
        """Parent task at level 0, child at level 1."""
        parent = Task(gid="parent_1", name="Parent")
        child = Task(gid="child_1", name="Child", parent=NameGid(gid="parent_1"))

        graph = DependencyGraph()
        graph.build([parent, child])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert parent in levels[0]
        assert child in levels[1]

    def test_three_level_hierarchy(self) -> None:
        """Grandparent -> Parent -> Child ordering."""
        grandparent = Task(gid="gp", name="Grandparent")
        parent = Task(gid="p", name="Parent", parent=NameGid(gid="gp"))
        child = Task(gid="c", name="Child", parent=NameGid(gid="p"))

        graph = DependencyGraph()
        graph.build([grandparent, parent, child])
        levels = graph.get_levels()

        assert len(levels) == 3
        assert grandparent in levels[0]
        assert parent in levels[1]
        assert child in levels[2]

    def test_multiple_children_same_level(self) -> None:
        """Multiple children of same parent at same level."""
        parent = Task(gid="parent", name="Parent")
        child1 = Task(gid="c1", name="Child 1", parent=NameGid(gid="parent"))
        child2 = Task(gid="c2", name="Child 2", parent=NameGid(gid="parent"))
        child3 = Task(gid="c3", name="Child 3", parent=NameGid(gid="parent"))

        graph = DependencyGraph()
        graph.build([parent, child1, child2, child3])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert parent in levels[0]
        assert all(c in levels[1] for c in [child1, child2, child3])

    def test_four_level_deep_chain(self) -> None:
        """Four level deep chain maintains correct order."""
        l0 = Task(gid="l0", name="Level 0")
        l1 = Task(gid="l1", name="Level 1", parent=NameGid(gid="l0"))
        l2 = Task(gid="l2", name="Level 2", parent=NameGid(gid="l1"))
        l3 = Task(gid="l3", name="Level 3", parent=NameGid(gid="l2"))

        graph = DependencyGraph()
        graph.build([l3, l2, l1, l0])  # Intentionally reversed
        levels = graph.get_levels()

        assert len(levels) == 4
        assert levels[0] == [l0]
        assert levels[1] == [l1]
        assert levels[2] == [l2]
        assert levels[3] == [l3]

    def test_parent_with_mixed_depth_children(self) -> None:
        """Parent with both direct children and grandchildren."""
        root = Task(gid="root", name="Root")
        child_a = Task(gid="child_a", name="Child A", parent=NameGid(gid="root"))
        child_b = Task(gid="child_b", name="Child B", parent=NameGid(gid="root"))
        grandchild = Task(gid="gc", name="Grandchild", parent=NameGid(gid="child_a"))

        graph = DependencyGraph()
        graph.build([grandchild, root, child_b, child_a])
        levels = graph.get_levels()

        assert len(levels) == 3
        assert root in levels[0]
        assert child_a in levels[1]
        assert child_b in levels[1]
        assert grandchild in levels[2]


# ---------------------------------------------------------------------------
# Cycle Detection Tests
# ---------------------------------------------------------------------------


class TestCycleDetection:
    """Test cycle detection raises CyclicDependencyError (FR-DEPEND-003)."""

    def test_direct_cycle_raises(self) -> None:
        """A depends on B, B depends on A."""
        task_a = Task(gid="a", name="A", parent=NameGid(gid="b"))
        task_b = Task(gid="b", name="B", parent=NameGid(gid="a"))

        graph = DependencyGraph()
        graph.build([task_a, task_b])

        with pytest.raises(CyclicDependencyError) as exc_info:
            graph.get_levels()

        # Cycle should include both entities
        assert len(exc_info.value.cycle) >= 2

    def test_indirect_cycle_raises(self) -> None:
        """A -> B -> C -> A cycle."""
        task_a = Task(gid="a", name="A", parent=NameGid(gid="c"))
        task_b = Task(gid="b", name="B", parent=NameGid(gid="a"))
        task_c = Task(gid="c", name="C", parent=NameGid(gid="b"))

        graph = DependencyGraph()
        graph.build([task_a, task_b, task_c])

        with pytest.raises(CyclicDependencyError):
            graph.get_levels()

    def test_self_reference_raises(self) -> None:
        """Entity referencing itself raises cycle error."""
        task = Task(gid="self", name="Self", parent=NameGid(gid="self"))

        graph = DependencyGraph()
        graph.build([task])

        with pytest.raises(CyclicDependencyError):
            graph.get_levels()

    def test_long_cycle_detected(self) -> None:
        """Long cycle (5 entities) is detected."""
        tasks = []
        for i in range(5):
            next_idx = (i + 1) % 5  # Creates cycle: 0->1->2->3->4->0
            tasks.append(
                Task(
                    gid=f"task_{i}",
                    name=f"Task {i}",
                    parent=NameGid(gid=f"task_{next_idx}"),
                )
            )

        graph = DependencyGraph()
        graph.build(tasks)

        with pytest.raises(CyclicDependencyError):
            graph.get_levels()

    def test_cycle_in_subgraph(self) -> None:
        """Cycle in one part of graph is detected even with valid parts."""
        # Valid independent task
        independent = Task(gid="ind", name="Independent")

        # Cycle: A <-> B
        task_a = Task(gid="a", name="A", parent=NameGid(gid="b"))
        task_b = Task(gid="b", name="B", parent=NameGid(gid="a"))

        graph = DependencyGraph()
        graph.build([independent, task_a, task_b])

        with pytest.raises(CyclicDependencyError):
            graph.get_levels()

    def test_topological_sort_also_raises_on_cycle(self) -> None:
        """topological_sort() raises CyclicDependencyError too."""
        task_a = Task(gid="a", parent=NameGid(gid="b"))
        task_b = Task(gid="b", parent=NameGid(gid="a"))

        graph = DependencyGraph()
        graph.build([task_a, task_b])

        with pytest.raises(CyclicDependencyError):
            graph.topological_sort()


# ---------------------------------------------------------------------------
# Complex Graphs Tests
# ---------------------------------------------------------------------------


class TestComplexGraphs:
    """Test complex dependency structures."""

    def test_ten_entity_mixed_hierarchy(self) -> None:
        """10 entities with various dependencies."""
        root = Task(gid="root", name="Root")

        # Create tree structure
        entities = [root]
        for i in range(1, 4):
            parent_entity = Task(
                gid=f"l1_{i}",
                name=f"Level 1 #{i}",
                parent=NameGid(gid="root"),
            )
            entities.append(parent_entity)

            for j in range(1, 3):
                child = Task(
                    gid=f"l2_{i}_{j}",
                    name=f"Level 2 #{i}.{j}",
                    parent=NameGid(gid=f"l1_{i}"),
                )
                entities.append(child)

        graph = DependencyGraph()
        graph.build(entities)
        levels = graph.get_levels()

        assert len(levels) == 3
        assert root in levels[0]
        assert len(levels[1]) == 3  # 3 level-1 nodes
        assert len(levels[2]) == 6  # 6 level-2 nodes

    def test_diamond_dependency(self) -> None:
        """A depends on B and C, both depend on D."""
        #     D
        #    / \
        #   B   C
        #    \ /
        #     A (via explicit dep or parent to B)
        d = Task(gid="d", name="D")
        b = Task(gid="b", name="B", parent=NameGid(gid="d"))
        c = Task(gid="c", name="C", parent=NameGid(gid="d"))
        a = Task(gid="a", name="A", parent=NameGid(gid="b"))

        graph = DependencyGraph()
        graph.build([a, b, c, d])
        levels = graph.get_levels()

        # D first, then B and C, then A
        assert d in levels[0]
        assert b in levels[1]
        assert c in levels[1]
        assert a in levels[2]

    def test_independent_entities_same_level(self) -> None:
        """Unrelated entities all at level 0."""
        tasks = [Task(gid=f"task_{i}", name=f"Task {i}") for i in range(5)]

        graph = DependencyGraph()
        graph.build(tasks)
        levels = graph.get_levels()

        assert len(levels) == 1
        assert len(levels[0]) == 5
        for task in tasks:
            assert task in levels[0]

    def test_two_independent_chains(self) -> None:
        """Two independent chains are processed correctly."""
        # Chain 1: a1 -> b1 -> c1
        a1 = Task(gid="a1", name="A1")
        b1 = Task(gid="b1", name="B1", parent=NameGid(gid="a1"))
        c1 = Task(gid="c1", name="C1", parent=NameGid(gid="b1"))

        # Chain 2: a2 -> b2
        a2 = Task(gid="a2", name="A2")
        b2 = Task(gid="b2", name="B2", parent=NameGid(gid="a2"))

        graph = DependencyGraph()
        graph.build([c1, a1, b2, a2, b1])  # Shuffled
        levels = graph.get_levels()

        # Roots at level 0
        assert a1 in levels[0]
        assert a2 in levels[0]

        # First children at level 1
        assert b1 in levels[1]
        assert b2 in levels[1]

        # Only chain 1 has level 2
        assert c1 in levels[2]

    def test_wide_tree_structure(self) -> None:
        """Root with 10 children at same level."""
        root = Task(gid="root", name="Root")
        children = [
            Task(gid=f"child_{i}", name=f"Child {i}", parent=NameGid(gid="root"))
            for i in range(10)
        ]

        graph = DependencyGraph()
        graph.build([root] + children)
        levels = graph.get_levels()

        assert len(levels) == 2
        assert levels[0] == [root]
        assert len(levels[1]) == 10

    def test_unbalanced_tree(self) -> None:
        """Unbalanced tree with different depths."""
        #        root
        #       / | \
        #      a  b  c
        #      |     |
        #      d     e
        #      |
        #      f
        root = Task(gid="root", name="Root")
        a = Task(gid="a", name="A", parent=NameGid(gid="root"))
        b = Task(gid="b", name="B", parent=NameGid(gid="root"))
        c = Task(gid="c", name="C", parent=NameGid(gid="root"))
        d = Task(gid="d", name="D", parent=NameGid(gid="a"))
        e = Task(gid="e", name="E", parent=NameGid(gid="c"))
        f = Task(gid="f", name="F", parent=NameGid(gid="d"))

        graph = DependencyGraph()
        graph.build([f, e, d, c, b, a, root])
        levels = graph.get_levels()

        assert len(levels) == 4
        assert root in levels[0]
        assert a in levels[1] and b in levels[1] and c in levels[1]
        assert d in levels[2] and e in levels[2]
        assert f in levels[3]


# ---------------------------------------------------------------------------
# External Parent Reference Tests
# ---------------------------------------------------------------------------


class TestExternalParentReference:
    """Test handling of parent references not in the entity list."""

    def test_external_parent_ignored(self) -> None:
        """Parent GID not in entity list is ignored."""
        child = Task(
            gid="child",
            name="Orphan Child",
            parent=NameGid(gid="external_parent"),
        )

        graph = DependencyGraph()
        graph.build([child])
        result = graph.topological_sort()

        # Should still work - external dep is ignored
        assert result == [child]

    def test_mixed_internal_external_parents(self) -> None:
        """Mix of internal and external parent references."""
        internal_parent = Task(gid="internal", name="Internal")
        child_of_internal = Task(
            gid="child_internal",
            name="Child of Internal",
            parent=NameGid(gid="internal"),
        )
        child_of_external = Task(
            gid="child_external",
            name="Child of External",
            parent=NameGid(gid="external"),
        )

        graph = DependencyGraph()
        graph.build([internal_parent, child_of_internal, child_of_external])
        levels = graph.get_levels()

        # Internal parent at level 0, external child also at level 0 (no dep)
        assert internal_parent in levels[0]
        assert child_of_external in levels[0]
        assert child_of_internal in levels[1]


# ---------------------------------------------------------------------------
# Explicit Dependency Tests
# ---------------------------------------------------------------------------


class TestExplicitDependency:
    """Test explicit dependency declaration (FR-DEPEND-008)."""

    def test_add_explicit_dependency(self) -> None:
        """add_explicit_dependency() creates edge between entities."""
        task_a = Task(gid="a", name="A")
        task_b = Task(gid="b", name="B")

        graph = DependencyGraph()
        graph.build([task_a, task_b])

        # Initially both at level 0
        levels_before = graph.get_levels()
        assert len(levels_before) == 1

        # Add dependency: B depends on A
        graph.add_explicit_dependency(dependent=task_b, dependency=task_a)

        levels_after = graph.get_levels()
        assert len(levels_after) == 2
        assert task_a in levels_after[0]
        assert task_b in levels_after[1]

    def test_explicit_dependency_combines_with_parent(self) -> None:
        """Explicit dependency works with parent relationships."""
        parent = Task(gid="parent", name="Parent")
        child = Task(gid="child", name="Child", parent=NameGid(gid="parent"))
        unrelated = Task(gid="unrelated", name="Unrelated")

        graph = DependencyGraph()
        graph.build([parent, child, unrelated])

        # Make child also depend on unrelated
        graph.add_explicit_dependency(dependent=child, dependency=unrelated)

        levels = graph.get_levels()

        # Both parent and unrelated must come before child
        child_level = None
        for idx, level in enumerate(levels):
            if child in level:
                child_level = idx
                break

        assert child_level is not None
        assert child_level > 0

        # Parent and unrelated should be in earlier levels
        for idx, level in enumerate(levels):
            if parent in level or unrelated in level:
                assert idx < child_level

    def test_explicit_dependency_unknown_entity_ignored(self) -> None:
        """Explicit dependency with unknown entity is no-op."""
        task_a = Task(gid="a", name="A")
        task_b = Task(gid="b", name="B")
        external = Task(gid="external", name="Not in graph")

        graph = DependencyGraph()
        graph.build([task_a, task_b])

        # Try to add dependency involving entity not in graph
        graph.add_explicit_dependency(dependent=task_a, dependency=external)

        # Should not affect the graph
        levels = graph.get_levels()
        assert len(levels) == 1


# ---------------------------------------------------------------------------
# Topological Sort Tests
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    """Test topological sort ordering correctness."""

    def test_topological_sort_maintains_dependency_order(self) -> None:
        """Topological sort produces valid dependency order."""
        # Chain: A -> B -> C -> D
        a = Task(gid="a", name="A")
        b = Task(gid="b", name="B", parent=NameGid(gid="a"))
        c = Task(gid="c", name="C", parent=NameGid(gid="b"))
        d = Task(gid="d", name="D", parent=NameGid(gid="c"))

        graph = DependencyGraph()
        graph.build([d, c, b, a])  # Reversed order input
        result = graph.topological_sort()

        # Verify order: A before B before C before D
        assert result.index(a) < result.index(b)
        assert result.index(b) < result.index(c)
        assert result.index(c) < result.index(d)

    def test_topological_sort_handles_empty_graph(self) -> None:
        """Empty graph produces empty sort result."""
        graph = DependencyGraph()
        graph.build([])

        result = graph.topological_sort()
        assert result == []

    def test_topological_sort_single_entity(self) -> None:
        """Single entity returns list with that entity."""
        task = Task(gid="single", name="Single")

        graph = DependencyGraph()
        graph.build([task])

        result = graph.topological_sort()
        assert result == [task]

    def test_topological_sort_preserves_all_entities(self) -> None:
        """All entities appear in sort result."""
        tasks = [Task(gid=f"t_{i}", name=f"Task {i}") for i in range(10)]

        graph = DependencyGraph()
        graph.build(tasks)

        result = graph.topological_sort()
        assert len(result) == 10
        for task in tasks:
            assert task in result


# ---------------------------------------------------------------------------
# New Entity (Temp GID) Tests
# ---------------------------------------------------------------------------


class TestNewEntityDependencies:
    """Test dependency handling for new entities with temp GIDs."""

    def test_temp_gid_parent_resolved(self) -> None:
        """Parent with temp GID is correctly resolved."""
        parent = Task(gid="temp_parent", name="New Parent")
        # Child references parent by its temp GID
        child = Task(gid="temp_child", name="New Child")
        # Set parent as the actual entity (simulating user code)
        child.parent = parent  # type: ignore[assignment]

        graph = DependencyGraph()
        graph.build([parent, child])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert parent in levels[0]
        assert child in levels[1]

    def test_mixed_real_and_temp_gids(self) -> None:
        """Mix of real and temp GIDs works correctly."""
        real_parent = Task(gid="real_123", name="Real Parent")
        temp_child = Task(
            gid="temp_child",
            name="Temp Child",
            parent=NameGid(gid="real_123"),
        )

        graph = DependencyGraph()
        graph.build([real_parent, temp_child])
        levels = graph.get_levels()

        assert len(levels) == 2
        assert real_parent in levels[0]
        assert temp_child in levels[1]


# ---------------------------------------------------------------------------
# Graph Rebuild Tests
# ---------------------------------------------------------------------------


class TestGraphRebuild:
    """Test rebuilding graph state."""

    def test_build_clears_previous_state(self) -> None:
        """build() clears previous graph state."""
        graph = DependencyGraph()

        # First build
        old_task = Task(gid="old", name="Old")
        graph.build([old_task])

        # Second build replaces state
        new_task = Task(gid="new", name="New")
        graph.build([new_task])

        result = graph.topological_sort()
        assert old_task not in result
        assert result == [new_task]

    def test_multiple_builds_work_correctly(self) -> None:
        """Multiple sequential builds work correctly."""
        graph = DependencyGraph()

        for i in range(5):
            tasks = [Task(gid=f"gen{i}_t{j}") for j in range(3)]
            graph.build(tasks)
            result = graph.topological_sort()
            assert len(result) == 3
