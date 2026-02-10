"""Tests for LIS-based subtask reorder plan computation.

Per TDD-GAP-06 Section 10: Unit tests for compute_reorder_plan(),
_compute_lis_indices(), and SaveSession.reorder_subtasks() integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from autom8_asana.persistence.models import ActionType
from autom8_asana.persistence.reorder import (
    Move,
    ReorderPlan,
    _compute_lis_indices,
    compute_reorder_plan,
)
from autom8_asana.persistence.session import SaveSession

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeResource:
    """Minimal AsanaResource stand-in with gid attribute for testing."""

    gid: str
    name: str = ""
    resource_type: str | None = None


def make_resources(n: int) -> list[FakeResource]:
    """Create n FakeResource objects with gids "0" through "n-1"."""
    return [FakeResource(gid=str(i), name=f"item_{i}") for i in range(n)]


def apply_moves(
    current: list[FakeResource],
    moves: tuple[Move, ...],
) -> list[FakeResource]:
    """Simulate applying reorder moves to a list.

    Per TDD-GAP-06 Section 10: Test helper for SC-004 and property test.
    """
    result = list(current)
    for move in moves:
        # Remove item from current position
        result.remove(move.item)
        # Find reference position
        ref_idx = result.index(move.reference)
        # Insert relative to reference
        if move.direction == "insert_after":
            result.insert(ref_idx + 1, move.item)
        else:
            result.insert(ref_idx, move.item)
    return result


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient for SaveSession tests."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_client.batch = mock_batch
    mock_client._log = None
    mock_client._http = MagicMock()
    mock_client.automation = None
    return mock_client


# ---------------------------------------------------------------------------
# LIS Algorithm Tests
# ---------------------------------------------------------------------------


class TestComputeLisIndices:
    """Tests for the internal _compute_lis_indices function."""

    def test_empty_sequence(self) -> None:
        """Empty input returns empty set."""
        assert _compute_lis_indices([]) == set()

    def test_single_element(self) -> None:
        """Single element is always in the LIS."""
        assert _compute_lis_indices([0]) == {0}

    def test_already_sorted(self) -> None:
        """Sorted sequence: all elements are in the LIS."""
        result = _compute_lis_indices([0, 1, 2, 3, 4, 5, 6])
        assert len(result) == 7

    def test_fully_reversed(self) -> None:
        """Fully reversed: LIS length is 1."""
        result = _compute_lis_indices([6, 5, 4, 3, 2, 1, 0])
        assert len(result) == 1

    def test_partially_sorted(self) -> None:
        """Partially sorted: LIS captures the longest increasing run."""
        # Position sequence: [0, 1, 5, 3, 4, 2, 6]
        # LIS could be [0, 1, 3, 4, 6] (length 5)
        result = _compute_lis_indices([0, 1, 5, 3, 4, 2, 6])
        assert len(result) == 5


# ---------------------------------------------------------------------------
# compute_reorder_plan Tests
# ---------------------------------------------------------------------------


class TestComputeReorderPlan:
    """Tests for compute_reorder_plan() per TDD-GAP-06 Section 10."""

    def test_already_sorted_zero_moves(self) -> None:
        """SC-001: 7 items in order -> zero moves, lis_length == 7."""
        items = make_resources(7)
        plan = compute_reorder_plan(list(items), list(items))

        assert plan.moves == ()
        assert plan.lis_length == 7
        assert plan.total_children == 7
        assert plan.moves_required == 0

    def test_partially_sorted_minimum_moves(self) -> None:
        """SC-002: 7 items, 5 in order, 2 displaced -> 2 moves."""
        desired = make_resources(7)
        # Swap items at positions 2 and 5 to displace 2 elements
        # desired:  [0, 1, 2, 3, 4, 5, 6]
        # current:  [0, 1, 5, 3, 4, 2, 6]
        # Position seq: [0, 1, 5, 3, 4, 2, 6]
        # LIS = [0, 1, 3, 4, 6] -> length 5
        current = [
            desired[0],
            desired[1],
            desired[5],
            desired[3],
            desired[4],
            desired[2],
            desired[6],
        ]
        plan = compute_reorder_plan(current, list(desired))

        assert plan.lis_length == 5
        assert plan.moves_required == 2
        assert plan.total_children == 7

    def test_fully_reversed_n_minus_1_moves(self) -> None:
        """SC-003: 7 items fully reversed -> 6 moves, lis_length == 1."""
        desired = make_resources(7)
        current = list(reversed(desired))
        plan = compute_reorder_plan(current, list(desired))

        assert plan.lis_length == 1
        assert plan.moves_required == 6
        assert plan.total_children == 7

    def test_moves_produce_desired_order(self) -> None:
        """SC-004: Applying moves to current produces desired order."""
        desired = make_resources(7)
        # Scramble: [3, 6, 0, 5, 1, 4, 2]
        current = [
            desired[3],
            desired[6],
            desired[0],
            desired[5],
            desired[1],
            desired[4],
            desired[2],
        ]
        plan = compute_reorder_plan(current, list(desired))

        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_empty_input_zero_moves(self) -> None:
        """SC-005: Empty input -> zero moves."""
        plan = compute_reorder_plan([], [])

        assert plan == ReorderPlan(moves=(), lis_length=0, total_children=0)

    def test_single_element_zero_moves(self) -> None:
        """SC-005: Single element -> zero moves."""
        items = make_resources(1)
        plan = compute_reorder_plan(list(items), list(items))

        assert plan == ReorderPlan(moves=(), lis_length=1, total_children=1)

    def test_two_elements_swapped(self) -> None:
        """Two elements swapped -> 1 move."""
        desired = make_resources(2)
        current = [desired[1], desired[0]]
        plan = compute_reorder_plan(current, list(desired))

        assert plan.moves_required == 1
        assert plan.lis_length == 1

        # Verify the move produces correct order
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_mismatched_elements_raises(self) -> None:
        """Different gids in current and desired raises ValueError."""
        current = [FakeResource(gid="a"), FakeResource(gid="b")]
        desired = [FakeResource(gid="a"), FakeResource(gid="c")]

        with pytest.raises(ValueError, match="Mismatched elements"):
            compute_reorder_plan(current, desired)

    def test_duplicate_gids_in_current_raises(self) -> None:
        """Duplicate gids in current_order raises ValueError."""
        current = [FakeResource(gid="a"), FakeResource(gid="a")]
        desired = [FakeResource(gid="a"), FakeResource(gid="b")]

        with pytest.raises(ValueError, match="Duplicate gid in current_order"):
            compute_reorder_plan(current, desired)

    def test_duplicate_gids_in_desired_raises(self) -> None:
        """Duplicate gids in desired_order raises ValueError."""
        current = [FakeResource(gid="a"), FakeResource(gid="b")]
        desired = [FakeResource(gid="a"), FakeResource(gid="a")]

        with pytest.raises(ValueError, match="Duplicate gid in desired_order"):
            compute_reorder_plan(current, desired)

    def test_move_directions_are_valid(self) -> None:
        """All moves have valid direction values."""
        desired = make_resources(5)
        current = list(reversed(desired))
        plan = compute_reorder_plan(current, list(desired))

        for move in plan.moves:
            assert move.direction in ("insert_before", "insert_after")

    def test_move_references_are_stable(self) -> None:
        """Each move's reference was placed before the move executes."""
        desired = make_resources(7)
        current = list(reversed(desired))
        plan = compute_reorder_plan(current, list(desired))

        # LIS indices are the initially placed items
        lis_indices = _compute_lis_indices([desired.index(item) for item in current])
        placed_gids = {current[i].gid for i in lis_indices}

        for move in plan.moves:
            # Reference must be in placed set before this move
            assert move.reference.gid in placed_gids, (
                f"Move for {move.item.gid} references {move.reference.gid} "
                f"which is not yet placed"
            )
            placed_gids.add(move.item.gid)


# ---------------------------------------------------------------------------
# Hypothesis Property-Based Test (skipped if hypothesis not installed)
# ---------------------------------------------------------------------------

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st

    _HAS_HYPOTHESIS = True
except ImportError:
    _HAS_HYPOTHESIS = False


@pytest.mark.skipif(not _HAS_HYPOTHESIS, reason="hypothesis not installed")
def test_property_moves_produce_desired_order() -> None:
    """For any permutation, applying generated moves produces the sorted output."""
    if not _HAS_HYPOTHESIS:
        return

    @given(
        st.lists(
            st.integers(min_value=0, max_value=99),
            min_size=0,
            max_size=20,
            unique=True,
        ).flatmap(
            lambda items: st.tuples(
                st.just(items),
                st.permutations(items),
            )
        )
    )
    @settings(max_examples=200)
    def _inner(items_and_perm: tuple) -> None:
        sorted_items, perm = items_and_perm

        desired = [FakeResource(gid=str(v), name=f"item_{v}") for v in sorted_items]
        current = [FakeResource(gid=str(v), name=f"item_{v}") for v in perm]

        plan = compute_reorder_plan(current, desired)

        assert plan.moves_required == plan.total_children - plan.lis_length

        if plan.moves_required > 0:
            result = apply_moves(current, plan.moves)
            assert [r.gid for r in result] == [r.gid for r in desired]
        else:
            assert [r.gid for r in current] == [r.gid for r in desired]

    _inner()


@pytest.mark.parametrize(
    "perm",
    [
        [4, 3, 2, 1, 0],
        [1, 0, 3, 2, 4],
        [0, 4, 1, 3, 2],
        [2, 0, 4, 1, 3],
        [3, 1, 4, 0, 2],
        [0, 1, 2, 3, 4],
    ],
    ids=[
        "reversed",
        "pairs-swapped",
        "one-shift",
        "scattered",
        "interleaved",
        "sorted",
    ],
)
def test_deterministic_permutations_produce_desired_order(perm: list[int]) -> None:
    """Deterministic permutation coverage when hypothesis is unavailable."""
    desired = [FakeResource(gid=str(i), name=f"item_{i}") for i in range(5)]
    current = [desired[i] for i in perm]
    plan = compute_reorder_plan(current, list(desired))

    assert plan.moves_required == plan.total_children - plan.lis_length

    if plan.moves_required > 0:
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]
    else:
        assert [r.gid for r in current] == [r.gid for r in desired]


# ---------------------------------------------------------------------------
# SaveSession Integration Test
# ---------------------------------------------------------------------------


class TestReorderSubtasks:
    """Tests for SaveSession.reorder_subtasks() method."""

    def test_reorder_subtasks_queues_set_parent_actions(self) -> None:
        """Queues correct number of SET_PARENT actions for each move."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        desired = make_resources(7)
        # Swap 2 elements: LIS = 5, moves = 2
        current = [
            desired[0],
            desired[1],
            desired[5],
            desired[3],
            desired[4],
            desired[2],
            desired[6],
        ]
        parent = FakeResource(gid="parent_001", name="Parent")

        plan = session.reorder_subtasks(parent, current, list(desired))

        assert plan.moves_required == 2
        actions = session.get_pending_actions()
        assert len(actions) == 2
        assert all(a.action == ActionType.SET_PARENT for a in actions)

    def test_reorder_subtasks_action_positioning(self) -> None:
        """Each action has correct insert_before or insert_after."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        desired = make_resources(3)
        current = [desired[2], desired[0], desired[1]]
        parent = FakeResource(gid="parent_001", name="Parent")

        plan = session.reorder_subtasks(parent, current, list(desired))

        actions = session.get_pending_actions()
        for action in actions:
            # Each action should have exactly one of insert_before or insert_after
            has_before = "insert_before" in action.extra_params
            has_after = "insert_after" in action.extra_params
            assert has_before or has_after, "Action must have positioning"

    def test_reorder_subtasks_returns_plan(self) -> None:
        """Returns the computed ReorderPlan for inspection."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        items = make_resources(3)
        parent = FakeResource(gid="parent_001")

        plan = session.reorder_subtasks(parent, list(items), list(items))

        assert isinstance(plan, ReorderPlan)
        assert plan.moves_required == 0
        assert plan.lis_length == 3

    def test_reorder_subtasks_with_string_parent(self) -> None:
        """Accepts string GID as parent."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        desired = make_resources(3)
        current = [desired[1], desired[0], desired[2]]

        plan = session.reorder_subtasks("parent_gid", current, list(desired))

        actions = session.get_pending_actions()
        assert all(a.extra_params["parent"] == "parent_gid" for a in actions)

    def test_reorder_subtasks_closed_session_raises(self) -> None:
        """Raises SessionClosedError when session is closed."""
        from autom8_asana.persistence.exceptions import SessionClosedError

        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            pass  # Session closed after exit

        items = make_resources(3)
        with pytest.raises(SessionClosedError):
            session.reorder_subtasks("parent", list(items), list(items))

    def test_reorder_subtasks_no_actions_for_sorted(self) -> None:
        """No actions queued when already sorted."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        items = make_resources(5)
        parent = FakeResource(gid="parent_001")

        session.reorder_subtasks(parent, list(items), list(items))

        actions = session.get_pending_actions()
        assert len(actions) == 0


# ---------------------------------------------------------------------------
# Data Model Tests
# ---------------------------------------------------------------------------


class TestDataModels:
    """Tests for Move and ReorderPlan data models."""

    def test_move_is_frozen(self) -> None:
        """Move is immutable."""
        a = FakeResource(gid="a")
        b = FakeResource(gid="b")
        move = Move(item=a, reference=b, direction="insert_after")
        with pytest.raises(AttributeError):
            move.direction = "insert_before"  # type: ignore[misc]

    def test_reorder_plan_is_frozen(self) -> None:
        """ReorderPlan is immutable."""
        plan = ReorderPlan(moves=(), lis_length=0, total_children=0)
        with pytest.raises(AttributeError):
            plan.lis_length = 5  # type: ignore[misc]

    def test_reorder_plan_moves_required(self) -> None:
        """moves_required property matches moves length."""
        a = FakeResource(gid="a")
        b = FakeResource(gid="b")
        move = Move(item=a, reference=b, direction="insert_after")
        plan = ReorderPlan(moves=(move,), lis_length=1, total_children=2)
        assert plan.moves_required == 1
