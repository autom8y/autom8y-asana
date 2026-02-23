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


# ---------------------------------------------------------------------------
# Merged from test_reorder_adversarial.py [RF-009]
# ---------------------------------------------------------------------------

import random
from itertools import permutations


class TestLISAdversarial:
    """Adversarial inputs targeting the _compute_lis_indices function."""

    def test_two_elements_ascending(self) -> None:
        """Two elements already sorted: LIS should be 2."""
        result = _compute_lis_indices([0, 1])
        assert len(result) == 2

    def test_two_elements_descending(self) -> None:
        """Two elements reversed: LIS should be 1."""
        result = _compute_lis_indices([1, 0])
        assert len(result) == 1

    def test_alternating_high_low(self) -> None:
        """Alternating pattern: [1, 0, 3, 2, 5, 4]."""
        result = _compute_lis_indices([1, 0, 3, 2, 5, 4])
        # LIS is [0, 2, 4] or [1, 3, 5] etc. -> length 3
        assert len(result) == 3

    def test_adjacent_pairs_swapped(self) -> None:
        """[0, 2, 1, 4, 3, 6, 5] - adjacent pairs swapped."""
        result = _compute_lis_indices([0, 2, 1, 4, 3, 6, 5])
        # LIS: [0, 1, 3, 5] or [0, 2, 4, 6] -> length 4
        assert len(result) == 4

    def test_large_sorted_100(self) -> None:
        """100 elements already sorted: LIS should be 100."""
        result = _compute_lis_indices(list(range(100)))
        assert len(result) == 100

    def test_large_reversed_100(self) -> None:
        """100 elements fully reversed: LIS should be 1."""
        result = _compute_lis_indices(list(range(99, -1, -1)))
        assert len(result) == 1

    def test_sawtooth_pattern(self) -> None:
        """Sawtooth: [2, 0, 1, 5, 3, 4, 8, 6, 7]."""
        seq = [2, 0, 1, 5, 3, 4, 8, 6, 7]
        result = _compute_lis_indices(seq)
        # LIS could be [0, 1, 3, 4, 6, 7] -> length 6
        assert len(result) == 6

    def test_single_displacement_at_start(self) -> None:
        """Last element placed at start: [6, 0, 1, 2, 3, 4, 5]."""
        result = _compute_lis_indices([6, 0, 1, 2, 3, 4, 5])
        # LIS: [0, 1, 2, 3, 4, 5] -> length 6
        assert len(result) == 6

    def test_single_displacement_at_end(self) -> None:
        """First element placed at end: [1, 2, 3, 4, 5, 6, 0]."""
        result = _compute_lis_indices([1, 2, 3, 4, 5, 6, 0])
        # LIS: [1, 2, 3, 4, 5, 6] -> length 6
        assert len(result) == 6

    def test_lis_indices_form_increasing_subsequence(self) -> None:
        """Verify returned indices actually form an increasing subsequence."""
        seq = [5, 3, 4, 0, 2, 1, 6]
        indices = _compute_lis_indices(seq)
        sorted_indices = sorted(indices)
        values = [seq[i] for i in sorted_indices]
        # Values must be strictly increasing
        for i in range(1, len(values)):
            assert values[i] > values[i - 1], (
                f"LIS values not increasing at position {i}: "
                f"{values[i - 1]} >= {values[i]}"
            )


class TestLargeNAndPathological:
    """Test with larger inputs and pathological permutations."""

    def test_100_elements_random_permutation(self) -> None:
        """100 elements in random order: moves + LIS == N."""
        rng = random.Random(42)  # Fixed seed for reproducibility
        desired = make_resources(100)
        current = list(desired)
        rng.shuffle(current)

        plan = compute_reorder_plan(current, list(desired))

        assert plan.moves_required + plan.lis_length == 100
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_100_elements_nearly_sorted(self) -> None:
        """100 elements with only 3 displaced: should require exactly 3 moves."""
        desired = make_resources(100)
        current = list(desired)
        # Displace elements at positions 10, 50, 90 by moving them to front
        displaced = [current.pop(90), current.pop(49), current.pop(9)]
        current = displaced + current  # Put them at the front

        plan = compute_reorder_plan(current, list(desired))

        # LIS should be 97 (all undisplaced elements), moves should be 3
        assert plan.lis_length == 97
        assert plan.moves_required == 3
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_50_elements_reversed(self) -> None:
        """50 elements reversed: 49 moves, LIS 1."""
        desired = make_resources(50)
        current = list(reversed(desired))

        plan = compute_reorder_plan(current, list(desired))

        assert plan.lis_length == 1
        assert plan.moves_required == 49
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_even_indices_swapped(self) -> None:
        """Swap every pair of even/odd indices: [1,0,3,2,5,4,7,6,9,8]."""
        desired = make_resources(10)
        current = []
        for i in range(0, 10, 2):
            if i + 1 < 10:
                current.append(desired[i + 1])
                current.append(desired[i])
            else:
                current.append(desired[i])

        plan = compute_reorder_plan(current, list(desired))

        # LIS picks one from each pair -> length 5
        assert plan.lis_length == 5
        assert plan.moves_required == 5
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_rotate_right_by_one(self) -> None:
        """Rotate right by 1: [9, 0, 1, 2, 3, 4, 5, 6, 7, 8]."""
        desired = make_resources(10)
        current = [desired[-1]] + list(desired[:-1])

        plan = compute_reorder_plan(current, list(desired))

        # LIS = [0, 1, 2, 3, 4, 5, 6, 7, 8] -> length 9, 1 move
        assert plan.lis_length == 9
        assert plan.moves_required == 1
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_rotate_left_by_one(self) -> None:
        """Rotate left by 1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]."""
        desired = make_resources(10)
        current = list(desired[1:]) + [desired[0]]

        plan = compute_reorder_plan(current, list(desired))

        # LIS = [1, 2, 3, 4, 5, 6, 7, 8, 9] -> length 9, 1 move
        assert plan.lis_length == 9
        assert plan.moves_required == 1
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_interleaved_halves(self) -> None:
        """First half interleaved with second: [0,5,1,6,2,7,3,8,4,9]."""
        desired = make_resources(10)
        current = []
        for i in range(5):
            current.append(desired[i])
            current.append(desired[i + 5])

        plan = compute_reorder_plan(current, list(desired))

        # LIS should be [0, 1, 2, 3, 4] or [0, 5, 6, 7, 8, 9] -> length 5 or 6
        assert plan.lis_length >= 5
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_two_sorted_blocks_reversed(self) -> None:
        """Two sorted blocks in wrong order: [5,6,7,8,9, 0,1,2,3,4]."""
        desired = make_resources(10)
        current = list(desired[5:]) + list(desired[:5])

        plan = compute_reorder_plan(current, list(desired))

        # LIS = [5,6,7,8,9] or [0,1,2,3,4] -> length 5
        assert plan.lis_length == 5
        assert plan.moves_required == 5
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]


class TestExhaustiveSmallN:
    """Exhaustive verification for all permutations of small N."""

    @pytest.mark.parametrize("n", [2, 3, 4])
    def test_all_permutations_produce_desired_order(self, n: int) -> None:
        """For all permutations of n elements, moves produce desired order."""
        desired = make_resources(n)
        for perm in permutations(range(n)):
            current = [desired[i] for i in perm]
            plan = compute_reorder_plan(current, list(desired))

            assert plan.moves_required == plan.total_children - plan.lis_length, (
                f"Invariant violated for perm {perm}"
            )

            if plan.moves_required > 0:
                result = apply_moves(current, plan.moves)
                assert [r.gid for r in result] == [r.gid for r in desired], (
                    f"Wrong result for perm {perm}"
                )
            else:
                assert [r.gid for r in current] == [r.gid for r in desired]

    @pytest.mark.parametrize("n", [2, 3, 4])
    def test_all_permutations_moves_are_minimal(self, n: int) -> None:
        """For all permutations, moves == N - LIS_length (provably minimal)."""
        desired = make_resources(n)
        for perm in permutations(range(n)):
            current = [desired[i] for i in perm]
            plan = compute_reorder_plan(current, list(desired))

            # The number of moves should equal N - LIS_length
            # This is the mathematical minimum for this problem
            lis_indices = _compute_lis_indices(
                [list(desired).index(item) for item in current]
            )
            expected_moves = n - len(lis_indices)
            assert plan.moves_required == expected_moves, (
                f"Non-minimal moves for perm {perm}: "
                f"got {plan.moves_required}, expected {expected_moves}"
            )


class TestReferenceStabilityAdversarial:
    """Larger-scale reference stability verification."""

    def test_reference_stability_reversed_10(self) -> None:
        """Reversed 10 elements: all references must be stable."""
        desired = make_resources(10)
        current = list(reversed(desired))
        plan = compute_reorder_plan(current, list(desired))

        lis_indices = _compute_lis_indices([desired.index(item) for item in current])
        placed_gids = {current[i].gid for i in lis_indices}

        for move in plan.moves:
            assert move.reference.gid in placed_gids, (
                f"Unstable reference: {move.item.gid} references "
                f"{move.reference.gid} not in {placed_gids}"
            )
            placed_gids.add(move.item.gid)

    def test_reference_stability_random_100(self) -> None:
        """Random 100-element permutation: all references stable."""
        rng = random.Random(12345)
        desired = make_resources(100)
        current = list(desired)
        rng.shuffle(current)
        plan = compute_reorder_plan(current, list(desired))

        desired_position = {item.gid: idx for idx, item in enumerate(desired)}
        position_seq = [desired_position[item.gid] for item in current]
        lis_indices = _compute_lis_indices(position_seq)
        placed_gids = {current[i].gid for i in lis_indices}

        for move in plan.moves:
            assert move.reference.gid in placed_gids, (
                f"Unstable reference: {move.item.gid} references "
                f"{move.reference.gid} not in {placed_gids}"
            )
            placed_gids.add(move.item.gid)

    def test_reference_stability_scattered(self) -> None:
        """Scattered permutation: [4, 0, 8, 2, 6, 1, 9, 3, 7, 5]."""
        desired = make_resources(10)
        perm = [4, 0, 8, 2, 6, 1, 9, 3, 7, 5]
        current = [desired[i] for i in perm]
        plan = compute_reorder_plan(current, list(desired))

        desired_position = {item.gid: idx for idx, item in enumerate(desired)}
        position_seq = [desired_position[item.gid] for item in current]
        lis_indices = _compute_lis_indices(position_seq)
        placed_gids = {current[i].gid for i in lis_indices}

        for move in plan.moves:
            assert move.reference.gid in placed_gids
            placed_gids.add(move.item.gid)


class TestInsertBeforePath:
    """Test the insert_before code path where no placed element is to the left."""

    def test_first_element_displaced(self) -> None:
        """Element that belongs at position 0 is currently last.
        This triggers the insert_before path."""
        desired = make_resources(5)
        # Element 0 at the end: [1, 2, 3, 4, 0]
        current = [desired[1], desired[2], desired[3], desired[4], desired[0]]

        plan = compute_reorder_plan(current, list(desired))

        # LIS = [1, 2, 3, 4] -> length 4, 1 move for element 0
        assert plan.lis_length == 4
        assert plan.moves_required == 1

        # The move for element "0" should be insert_before element "1"
        move = plan.moves[0]
        assert move.item.gid == "0"
        assert move.direction == "insert_before"
        assert move.reference.gid == "1"

        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_multiple_elements_need_insert_before(self) -> None:
        """First 3 elements displaced to end: [3, 4, 5, 6, 0, 1, 2]."""
        desired = make_resources(7)
        current = [
            desired[3],
            desired[4],
            desired[5],
            desired[6],
            desired[0],
            desired[1],
            desired[2],
        ]

        plan = compute_reorder_plan(current, list(desired))

        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]

    def test_all_displaced_first_needs_insert_before(self) -> None:
        """Reversed 3 elements: [2, 1, 0]. Element 0 needs insert_before."""
        desired = make_resources(3)
        current = [desired[2], desired[1], desired[0]]

        plan = compute_reorder_plan(current, list(desired))

        assert plan.moves_required == 2
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]


class TestLISOffByOne:
    """Test cases specifically targeting off-by-one errors in predecessor backtracking."""

    def test_sequence_where_last_element_extends_lis(self) -> None:
        """Sequence where the last element is the largest."""
        seq = [1, 3, 0, 2, 4]
        result = _compute_lis_indices(seq)
        # LIS: [0, 2, 4] or [1, 3, 4] or [1, 2, 4] -> length 3
        assert len(result) == 3

    def test_sequence_where_first_element_is_in_lis(self) -> None:
        """First element should be in the LIS."""
        seq = [0, 5, 1, 6, 2, 7, 3]
        result = _compute_lis_indices(seq)
        # LIS: [0, 1, 2, 3] -> length 4, and index 0 should be in the set
        assert len(result) == 4
        assert 0 in result

    def test_long_lis_at_end(self) -> None:
        """LIS elements are all at the end of the sequence."""
        seq = [9, 8, 7, 0, 1, 2, 3, 4, 5, 6]
        result = _compute_lis_indices(seq)
        # LIS: [0, 1, 2, 3, 4, 5, 6] -> length 7
        assert len(result) == 7

    def test_lis_at_beginning(self) -> None:
        """LIS elements span beginning with late-arriving smaller values."""
        seq = [0, 1, 2, 7, 8, 9, 6, 3, 4, 5]
        result = _compute_lis_indices(seq)
        # LIS: [0, 1, 2, 7, 8, 9] or [0, 1, 2, 3, 4, 5] -> length 6
        assert len(result) == 6

    def test_predecessor_chain_integrity(self) -> None:
        """Verify the predecessor chain forms a valid increasing subsequence."""
        seq = [5, 1, 4, 2, 3, 0, 6]
        indices = _compute_lis_indices(seq)
        sorted_indices = sorted(indices)
        values = [seq[i] for i in sorted_indices]

        # Must be strictly increasing
        for i in range(1, len(values)):
            assert values[i] > values[i - 1]

        # Length should be LIS length (known: [1, 2, 3, 6] -> 4)
        assert len(indices) == 4


class TestErrorHandlingEdgeCases:
    """Validation edge cases not covered by basic error tests."""

    def test_single_element_mismatch_raises(self) -> None:
        """Single element where gids differ."""
        current = [FakeResource(gid="a")]
        desired = [FakeResource(gid="b")]

        with pytest.raises(ValueError, match="Mismatched elements"):
            compute_reorder_plan(current, desired)

    def test_empty_and_nonempty_raises(self) -> None:
        """Empty current with non-empty desired."""
        current: list[FakeResource] = []
        desired = [FakeResource(gid="a")]

        with pytest.raises(ValueError):
            compute_reorder_plan(current, desired)

    def test_nonempty_and_empty_raises(self) -> None:
        """Non-empty current with empty desired."""
        current = [FakeResource(gid="a")]
        desired: list[FakeResource] = []

        with pytest.raises(ValueError):
            compute_reorder_plan(current, desired)

    def test_three_elements_rotation(self) -> None:
        """[1, 2, 0] rotation: LIS should be 2, moves should be 1."""
        desired = make_resources(3)
        current = [desired[1], desired[2], desired[0]]
        plan = compute_reorder_plan(current, list(desired))

        assert plan.lis_length == 2
        assert plan.moves_required == 1
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]


class TestSaveSessionIntegrationAdversarial:
    """Adversarial tests for SaveSession.reorder_subtasks() integration."""

    def test_reorder_large_n_queues_correct_actions(self) -> None:
        """Large N: verify action count matches plan."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        desired = make_resources(20)
        current = list(reversed(desired))
        parent = FakeResource(gid="parent_001")

        plan = session.reorder_subtasks(parent, current, list(desired))

        actions = session.get_pending_actions()
        assert len(actions) == plan.moves_required

    def test_reorder_with_logging_enabled(self) -> None:
        """Test with logging enabled (self._log is set)."""
        from unittest.mock import MagicMock as MMock

        mock_client = create_mock_client()
        mock_log = MMock()
        mock_client._log = mock_log
        session = SaveSession(mock_client)

        desired = make_resources(5)
        current = list(reversed(desired))
        parent = FakeResource(gid="parent_001")

        session.reorder_subtasks(parent, current, list(desired))

        # Verify logging was called
        assert mock_log.info.called or mock_log.debug.called

    def test_reorder_twice_accumulates_actions(self) -> None:
        """Calling reorder_subtasks twice accumulates all actions."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        desired1 = make_resources(3)
        parent1 = FakeResource(gid="parent_001")
        current1 = list(reversed(desired1))

        desired2 = [FakeResource(gid="x"), FakeResource(gid="y"), FakeResource(gid="z")]
        parent2 = FakeResource(gid="parent_002")
        current2 = [desired2[2], desired2[0], desired2[1]]

        plan1 = session.reorder_subtasks(parent1, current1, list(desired1))
        plan2 = session.reorder_subtasks(parent2, current2, list(desired2))

        actions = session.get_pending_actions()
        assert len(actions) == plan1.moves_required + plan2.moves_required

    def test_reorder_then_manual_set_parent(self) -> None:
        """reorder_subtasks followed by manual set_parent: actions accumulate."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        desired = make_resources(3)
        current = list(reversed(desired))
        parent = FakeResource(gid="parent_001")

        plan = session.reorder_subtasks(parent, current, list(desired))

        # Add one more manual set_parent
        extra = FakeResource(gid="extra")
        session.set_parent(extra, parent, insert_after=desired[2])

        actions = session.get_pending_actions()
        assert len(actions) == plan.moves_required + 1

    def test_reorder_single_element(self) -> None:
        """Reorder single element: no actions queued."""
        mock_client = create_mock_client()
        session = SaveSession(mock_client)
        parent = FakeResource(gid="parent_001")
        item = FakeResource(gid="only_child")

        plan = session.reorder_subtasks(parent, [item], [item])

        assert plan.moves_required == 0
        assert len(session.get_pending_actions()) == 0

    def test_reorder_preserves_existing_reorder_subtask_singular(self) -> None:
        """Verify the singular reorder_subtask() method still exists and works."""
        from unittest.mock import MagicMock as MMock

        mock_client = create_mock_client()
        session = SaveSession(mock_client)

        task = MMock()
        task.gid = "task_001"
        task.parent = MMock()
        task.parent.gid = "parent_001"

        sibling = MMock()
        sibling.gid = "sibling_001"

        session.reorder_subtask(task, insert_after=sibling)

        actions = session.get_pending_actions()
        assert len(actions) == 1
        from autom8_asana.persistence.models import ActionType

        assert actions[0].action == ActionType.SET_PARENT


class TestMultipleRandomSeeds:
    """Run with multiple random seeds to find non-deterministic issues."""

    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    def test_random_permutation_seed(self, seed: int) -> None:
        """Random permutation with different seeds: moves produce desired."""
        rng = random.Random(seed)
        n = 15
        desired = make_resources(n)
        current = list(desired)
        rng.shuffle(current)

        plan = compute_reorder_plan(current, list(desired))

        assert plan.moves_required == n - plan.lis_length
        if plan.moves_required > 0:
            result = apply_moves(current, plan.moves)
            assert [r.gid for r in result] == [r.gid for r in desired]

    @pytest.mark.parametrize("seed", range(5))
    def test_large_random_permutation(self, seed: int) -> None:
        """Larger random permutation (50 elements)."""
        rng = random.Random(seed + 100)
        n = 50
        desired = make_resources(n)
        current = list(desired)
        rng.shuffle(current)

        plan = compute_reorder_plan(current, list(desired))

        assert plan.moves_required == n - plan.lis_length
        result = apply_moves(current, plan.moves)
        assert [r.gid for r in result] == [r.gid for r in desired]
