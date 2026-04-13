"""Tests for action ordering DAG module.

Per TDD-GAP-05 Section 13.1: Ordering constraint resolution tests.
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.action_ordering import (
    ORDERING_RULES,
    OrderingRule,
    _same_task_add_project_then_move_section,
    resolve_order,
)
from autom8_asana.persistence.models import ActionOperation, ActionType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_action(
    task_gid: str,
    action_type: ActionType,
    target_gid: str | None = None,
) -> ActionOperation:
    """Create an ActionOperation with minimal data for testing."""
    task = Task(gid=task_gid, name=f"Task {task_gid}")
    target = NameGid(gid=target_gid) if target_gid else None
    return ActionOperation(task=task, action=action_type, target=target)


# ---------------------------------------------------------------------------
# OrderingRule Tests
# ---------------------------------------------------------------------------


class TestOrderingRule:
    """Tests for the OrderingRule dataclass."""

    def test_ordering_rule_is_frozen(self) -> None:
        """OrderingRule is immutable."""
        rule = OrderingRule(
            predecessor=ActionType.ADD_TAG,
            successor=ActionType.REMOVE_TAG,
            match_fn=lambda p, s: True,
        )
        with pytest.raises(AttributeError):
            rule.predecessor = ActionType.REMOVE_TAG  # type: ignore[misc]

    def test_same_task_predicate_matches_same_task(self) -> None:
        """_same_task_add_project_then_move_section matches same task GID."""
        pred = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        succ = _make_action("task_1", ActionType.MOVE_TO_SECTION, "section_1")
        assert _same_task_add_project_then_move_section(pred, succ) is True

    def test_same_task_predicate_no_match_different_tasks(self) -> None:
        """_same_task_add_project_then_move_section rejects different tasks."""
        pred = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        succ = _make_action("task_2", ActionType.MOVE_TO_SECTION, "section_1")
        assert _same_task_add_project_then_move_section(pred, succ) is False


# ---------------------------------------------------------------------------
# resolve_order Tests
# ---------------------------------------------------------------------------


class TestResolveOrderEmpty:
    """Tests for empty and trivial inputs."""

    def test_resolve_order_empty(self) -> None:
        """Empty list returns empty list."""
        result = resolve_order([])
        assert result == []


class TestResolveOrderNoConstraints:
    """Tests when no ordering rules apply."""

    def test_no_constraints_single_tier(self) -> None:
        """5 independent tag actions -> single tier with all 5."""
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(5)]
        tiers = resolve_order(actions)

        assert len(tiers) == 1
        assert len(tiers[0]) == 5

    def test_no_constraints_preserves_order(self) -> None:
        """Actions in single tier maintain input list order."""
        actions = [_make_action(f"task_{i}", ActionType.REMOVE_TAG, f"tag_{i}") for i in range(10)]
        tiers = resolve_order(actions)

        assert len(tiers) == 1
        # Verify order preserved
        for i, action in enumerate(tiers[0]):
            assert action.task.gid == f"task_{i}"


class TestResolveOrderWithConstraints:
    """Tests with the default ADD_TO_PROJECT -> MOVE_TO_SECTION rule."""

    def test_add_project_before_move_section_same_task(self) -> None:
        """ADD_TO_PROJECT and MOVE_TO_SECTION for same task -> 2 tiers."""
        add_proj = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_1", ActionType.MOVE_TO_SECTION, "section_1")

        tiers = resolve_order([add_proj, move_sect])

        assert len(tiers) == 2
        assert tiers[0] == [add_proj]
        assert tiers[1] == [move_sect]

    def test_add_project_before_move_section_reversed_input(self) -> None:
        """Even if MOVE_TO_SECTION comes first in input, ordering is correct."""
        move_sect = _make_action("task_1", ActionType.MOVE_TO_SECTION, "section_1")
        add_proj = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")

        tiers = resolve_order([move_sect, add_proj])

        assert len(tiers) == 2
        assert tiers[0] == [add_proj]
        assert tiers[1] == [move_sect]

    def test_different_tasks_no_constraint(self) -> None:
        """ADD_TO_PROJECT for task A, MOVE_TO_SECTION for task B -> single tier."""
        add_proj = _make_action("task_A", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_B", ActionType.MOVE_TO_SECTION, "section_1")

        tiers = resolve_order([add_proj, move_sect])

        assert len(tiers) == 1
        assert len(tiers[0]) == 2


class TestResolveOrderMixed:
    """Tests with mixed independent and dependent actions."""

    def test_mixed_independent_and_dependent(self) -> None:
        """EC-008: 15 tags + ADD_TO_PROJECT in tier 0, MOVE_TO_SECTION in tier 1."""
        tag_actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(15)]
        add_proj = _make_action("task_x", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_x", ActionType.MOVE_TO_SECTION, "section_1")

        all_actions = tag_actions + [add_proj, move_sect]
        tiers = resolve_order(all_actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 16  # 15 tags + add_to_project
        assert len(tiers[1]) == 1  # move_to_section
        assert tiers[1][0] is move_sect

    def test_preserves_original_order_within_tier(self) -> None:
        """Actions in same tier maintain input list order (stable sort)."""
        actions = [
            _make_action("task_c", ActionType.ADD_TAG, "tag_1"),
            _make_action("task_a", ActionType.REMOVE_TAG, "tag_2"),
            _make_action("task_b", ActionType.ADD_TAG, "tag_3"),
        ]

        tiers = resolve_order(actions)

        assert len(tiers) == 1
        assert tiers[0][0].task.gid == "task_c"
        assert tiers[0][1].task.gid == "task_a"
        assert tiers[0][2].task.gid == "task_b"

    def test_multiple_dependencies(self) -> None:
        """3 ADD_TO_PROJECT + 3 MOVE_TO_SECTION (pairwise same task) -> 2 tiers."""
        actions = []
        for i in range(3):
            actions.append(_make_action(f"task_{i}", ActionType.ADD_TO_PROJECT, f"proj_{i}"))
        for i in range(3):
            actions.append(_make_action(f"task_{i}", ActionType.MOVE_TO_SECTION, f"section_{i}"))

        tiers = resolve_order(actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 3  # All ADD_TO_PROJECT
        assert len(tiers[1]) == 3  # All MOVE_TO_SECTION


class TestResolveOrderCustomRules:
    """Tests with custom rule sets."""

    def test_custom_rules_override_defaults(self) -> None:
        """Pass custom rules list; verify extensibility without modifying global."""
        # Custom rule: ADD_TAG must come before REMOVE_TAG for same task
        custom_rule = OrderingRule(
            predecessor=ActionType.ADD_TAG,
            successor=ActionType.REMOVE_TAG,
            match_fn=lambda p, s: p.task.gid == s.task.gid,
        )

        add_tag = _make_action("task_1", ActionType.ADD_TAG, "tag_1")
        remove_tag = _make_action("task_1", ActionType.REMOVE_TAG, "tag_2")

        # With default rules, no constraint (both in tier 0)
        tiers_default = resolve_order([add_tag, remove_tag], rules=ORDERING_RULES)
        assert len(tiers_default) == 1

        # With custom rule, constraint applies (2 tiers)
        tiers_custom = resolve_order([add_tag, remove_tag], rules=[custom_rule])
        assert len(tiers_custom) == 2
        assert tiers_custom[0] == [add_tag]
        assert tiers_custom[1] == [remove_tag]

    def test_empty_rules_no_constraints(self) -> None:
        """Passing empty rules list means no constraints."""
        add_proj = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_1", ActionType.MOVE_TO_SECTION, "section_1")

        tiers = resolve_order([add_proj, move_sect], rules=[])

        assert len(tiers) == 1
        assert len(tiers[0]) == 2


class TestResolveOrderCycleDetection:
    """Tests for cycle detection."""

    def test_cycle_detection_raises(self) -> None:
        """Artificial cycle via custom rules raises ValueError."""
        # Create a cycle: A -> B and B -> A
        rule_a_before_b = OrderingRule(
            predecessor=ActionType.ADD_TAG,
            successor=ActionType.REMOVE_TAG,
            match_fn=lambda p, s: True,
        )
        rule_b_before_a = OrderingRule(
            predecessor=ActionType.REMOVE_TAG,
            successor=ActionType.ADD_TAG,
            match_fn=lambda p, s: True,
        )

        action_a = _make_action("task_1", ActionType.ADD_TAG, "tag_1")
        action_b = _make_action("task_1", ActionType.REMOVE_TAG, "tag_2")

        with pytest.raises(ValueError, match="Cycle detected"):
            resolve_order(
                [action_a, action_b],
                rules=[rule_a_before_b, rule_b_before_a],
            )


class TestResolveOrderEdgeCases:
    """Additional edge cases for ordering."""

    def test_single_action(self) -> None:
        """Single action returns single tier with one action."""
        action = _make_action("task_1", ActionType.ADD_TAG, "tag_1")
        tiers = resolve_order([action])

        assert len(tiers) == 1
        assert tiers[0] == [action]

    def test_add_project_no_move_section(self) -> None:
        """ADD_TO_PROJECT alone -> tier 0, no ordering constraint."""
        action = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        tiers = resolve_order([action])

        assert len(tiers) == 1
        assert tiers[0] == [action]

    def test_move_section_without_add_project(self) -> None:
        """MOVE_TO_SECTION alone -> tier 0, no dependency."""
        action = _make_action("task_1", ActionType.MOVE_TO_SECTION, "section_1")
        tiers = resolve_order([action])

        assert len(tiers) == 1
        assert tiers[0] == [action]


# ---------------------------------------------------------------------------
# Merged from test_action_batch_adversarial.py [RF-009]
# ---------------------------------------------------------------------------


class TestResolveOrderMatchFnEdgeCases:
    """Actions that match rule's ActionType but not match_fn."""

    def test_multiple_add_project_one_move_section_only_constrains_matching(
        self,
    ) -> None:
        """ADD_TO_PROJECT for tasks A,B,C + MOVE_TO_SECTION for task B only.

        Only task B's pair should be constrained.
        """
        add_a = _make_action("task_A", ActionType.ADD_TO_PROJECT, "proj_1")
        add_b = _make_action("task_B", ActionType.ADD_TO_PROJECT, "proj_2")
        add_c = _make_action("task_C", ActionType.ADD_TO_PROJECT, "proj_3")
        move_b = _make_action("task_B", ActionType.MOVE_TO_SECTION, "sect_1")

        tiers = resolve_order([add_a, add_b, add_c, move_b])

        assert len(tiers) == 2
        # Tier 0: add_a, add_b, add_c (3 ADD_TO_PROJECT)
        assert len(tiers[0]) == 3
        # Tier 1: move_b (MOVE_TO_SECTION for task_B)
        assert len(tiers[1]) == 1
        assert tiers[1][0] is move_b


class TestResolveOrderScale:
    """Scale tests for the DAG algorithm to confirm O(A*R) performance."""

    def test_1000_independent_actions(self) -> None:
        """1000 independent actions should resolve into 1 tier quickly."""
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(1000)]

        tiers = resolve_order(actions)

        assert len(tiers) == 1
        assert len(tiers[0]) == 1000

    def test_500_actions_with_ordering(self) -> None:
        """500 actions: 250 ADD_TO_PROJECT + 250 MOVE_TO_SECTION for same tasks."""
        actions = []
        for i in range(250):
            actions.append(_make_action(f"task_{i}", ActionType.ADD_TO_PROJECT, f"proj_{i}"))
        for i in range(250):
            actions.append(_make_action(f"task_{i}", ActionType.MOVE_TO_SECTION, f"sect_{i}"))

        tiers = resolve_order(actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 250
        assert len(tiers[1]) == 250

    def test_ordering_constraint_100_actions(self) -> None:
        """100 actions with ordering constraints should work correctly."""
        tag_actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(98)]
        add_proj = _make_action("task_x", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_x", ActionType.MOVE_TO_SECTION, "sect_1")

        actions = tag_actions + [add_proj, move_sect]
        tiers = resolve_order(actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 99  # 98 tags + add_project
        assert len(tiers[1]) == 1  # move_to_section


class TestMultipleDependenciesPerTask:
    """Multiple ADD_TO_PROJECT -> MOVE_TO_SECTION for same task."""

    def test_two_add_projects_two_move_sections_same_task(self) -> None:
        """2 ADD_TO_PROJECT + 2 MOVE_TO_SECTION for same task -> 2 tiers."""
        add_1 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        add_2 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_2")
        move_1 = _make_action("task_1", ActionType.MOVE_TO_SECTION, "sect_1")
        move_2 = _make_action("task_1", ActionType.MOVE_TO_SECTION, "sect_2")

        tiers = resolve_order([add_1, add_2, move_1, move_2])

        assert len(tiers) == 2
        # Tier 0: both ADD_TO_PROJECT
        assert len(tiers[0]) == 2
        assert all(a.action == ActionType.ADD_TO_PROJECT for a in tiers[0])
        # Tier 1: both MOVE_TO_SECTION
        assert len(tiers[1]) == 2
        assert all(a.action == ActionType.MOVE_TO_SECTION for a in tiers[1])

    def test_in_degree_accumulates_from_multiple_predecessors(self) -> None:
        """A MOVE_TO_SECTION with 3 ADD_TO_PROJECT predecessors has in_degree=3.

        Kahn's algorithm should place it in tier 1 because all predecessors
        are in tier 0. In_degree goes to 0 after processing tier 0.
        """
        add_1 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        add_2 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_2")
        add_3 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_3")
        move = _make_action("task_1", ActionType.MOVE_TO_SECTION, "sect_1")

        tiers = resolve_order([add_1, add_2, add_3, move])

        assert len(tiers) == 2
        assert len(tiers[0]) == 3
        assert len(tiers[1]) == 1
        assert tiers[1][0] is move
