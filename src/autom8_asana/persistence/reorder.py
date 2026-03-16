"""LIS-based subtask reorder plan computation.

Per TDD-GAP-06: Computes the minimum number of SET_PARENT actions needed
to reorder subtasks from a current order to a desired order using the
Longest Increasing Subsequence (LIS) algorithm.

Elements in the LIS are already in correct relative order and do not move.
Only the remaining N - LIS_length elements require SET_PARENT actions.

This module is a pure function library with no I/O or session dependency.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Move:
    """A single reorder instruction.

    Attributes:
        item: The AsanaResource to move.
        reference: The AsanaResource to position relative to (stable -- in the LIS
                   or already placed).
        direction: "insert_before" or "insert_after".
    """

    item: AsanaResource
    reference: AsanaResource
    direction: Literal["insert_before", "insert_after"]


@dataclass(frozen=True, slots=True)
class ReorderPlan:
    """Result of compute_reorder_plan().

    Attributes:
        moves: Ordered tuple of Move instructions. Executing them sequentially on
               the input produces the desired order.
        lis_length: Length of the longest increasing subsequence (elements that
                    stay in place).
        total_children: Total number of children in the input.
    """

    moves: tuple[Move, ...]
    lis_length: int
    total_children: int

    @property
    def moves_required(self) -> int:
        """Number of SET_PARENT actions needed."""
        return len(self.moves)


def _compute_lis_indices(position_sequence: list[int]) -> set[int]:
    """Compute indices of elements forming the Longest Increasing Subsequence.

    Uses O(N log N) patience sorting with bisect_left for index recovery.

    Args:
        position_sequence: For each element at index i in the current order,
            the value is its position in the desired order. E.g., if current[2]
            should be at desired position 5, then position_sequence[2] == 5.

    Returns:
        Set of indices into position_sequence that form the LIS.
        These elements are already in correct relative order and do not need to move.
    """
    n = len(position_sequence)
    if n == 0:
        return set()

    tails: list[int] = []  # tails[i] = smallest ending value of IS of length i+1
    tail_indices: list[
        int
    ] = []  # tail_indices[i] = index in position_sequence of tails[i]
    predecessors: list[int] = [
        -1
    ] * n  # predecessors[i] = index of element before i in the LIS

    for i, val in enumerate(position_sequence):
        pos = bisect_left(tails, val)
        if pos == len(tails):
            tails.append(val)
            tail_indices.append(i)
        else:
            tails[pos] = val
            tail_indices[pos] = i
        predecessors[i] = tail_indices[pos - 1] if pos > 0 else -1

    # Backtrack from tail_indices[-1] through predecessors to recover full LIS
    lis_indices: set[int] = set()
    idx = tail_indices[-1]
    while idx != -1:
        lis_indices.add(idx)
        idx = predecessors[idx]

    return lis_indices


def compute_reorder_plan(
    current_order: list[AsanaResource],
    desired_order: list[AsanaResource],
) -> ReorderPlan:
    """Compute the minimum moves to transform current_order into desired_order.

    Pure function. No I/O. No session dependency. This IS the dry-run.

    Both lists must contain the same elements (by gid). Order differs.

    Args:
        current_order: Elements in their current sequence.
        desired_order: Elements in the target sequence.

    Returns:
        ReorderPlan with Move instructions.

    Raises:
        ValueError: If the two lists contain different elements (by gid) or
            contain duplicate gids.
    """
    n = len(current_order)

    # Degenerate cases
    if n <= 1 and len(desired_order) == n:
        # Validate gids match for single-element case
        if n == 1 and current_order[0].gid != desired_order[0].gid:
            raise ValueError(
                f"Mismatched elements: current has {{{current_order[0].gid}}}, "
                f"desired has {{{desired_order[0].gid}}}"
            )
        return ReorderPlan(moves=(), lis_length=n, total_children=n)

    # Build desired_position: gid -> index in desired_order
    desired_position: dict[str, int] = {}
    for idx, item in enumerate(desired_order):
        if item.gid in desired_position:
            raise ValueError(f"Duplicate gid in desired_order: {item.gid}")
        desired_position[item.gid] = idx

    # Validate: same gids in both lists, no duplicates in current_order
    current_gids: set[str] = set()
    for item in current_order:
        if item.gid in current_gids:
            raise ValueError(f"Duplicate gid in current_order: {item.gid}")
        current_gids.add(item.gid)

    desired_gids = set(desired_position.keys())
    if current_gids != desired_gids:
        only_current = current_gids - desired_gids
        only_desired = desired_gids - current_gids
        parts: list[str] = []
        if only_current:
            parts.append(f"only in current: {only_current}")
        if only_desired:
            parts.append(f"only in desired: {only_desired}")
        raise ValueError(f"Mismatched elements: {', '.join(parts)}")

    # Build position_sequence
    position_sequence = [desired_position[item.gid] for item in current_order]

    # Compute LIS
    lis_indices = _compute_lis_indices(position_sequence)

    # Generate moves for non-LIS elements
    # Build a set of gids that are "placed" (LIS members initially)
    placed_gids: set[str] = {current_order[i].gid for i in lis_indices}

    # Map gid -> AsanaResource from desired_order for lookup
    gid_to_resource: dict[str, AsanaResource] = {
        item.gid: item for item in desired_order
    }

    # Process non-LIS elements in desired order (ascending by desired position)
    non_lis_in_desired_order: list[AsanaResource] = [
        item for item in desired_order if item.gid not in placed_gids
    ]

    moves: list[Move] = []
    for item in non_lis_in_desired_order:
        desired_pos = desired_position[item.gid]

        # Look left for nearest placed element
        reference = None
        direction: Literal["insert_before", "insert_after"] = "insert_after"

        for left_pos in range(desired_pos - 1, -1, -1):
            left_gid = desired_order[left_pos].gid
            if left_gid in placed_gids:
                reference = gid_to_resource[left_gid]
                direction = "insert_after"
                break

        if reference is None:
            # No placed element to the left; look right for insert_before
            for right_pos in range(desired_pos + 1, len(desired_order)):
                right_gid = desired_order[right_pos].gid
                if right_gid in placed_gids:
                    reference = gid_to_resource[right_gid]
                    direction = "insert_before"
                    break

        # reference must exist: at least the LIS members are placed
        # (LIS is non-empty for n >= 2, and we handled n <= 1 above)
        moves.append(Move(item=item, reference=reference, direction=direction))  # type: ignore[arg-type]
        placed_gids.add(item.gid)

    return ReorderPlan(
        moves=tuple(moves),
        lis_length=len(lis_indices),
        total_children=n,
    )
