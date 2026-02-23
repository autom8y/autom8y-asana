"""Ordering constraint resolution for action batching.

Per TDD-GAP-05/ADR-GAP-05-002: DAG-based ordering with extensible rule registry.

Actions within a single commit may have ordering dependencies. For example,
ADD_TO_PROJECT must precede MOVE_TO_SECTION when both target the same task.
This module resolves those constraints into execution tiers via topological sort.

New constraints are added by appending to ORDERING_RULES (data-only change).
No graph logic changes are required.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8_asana.persistence.models import ActionOperation, ActionType

if TYPE_CHECKING:
    from collections.abc import Callable

    pass


@dataclass(frozen=True)
class OrderingRule:
    """A single ordering constraint between action types.

    Attributes:
        predecessor: ActionType that must execute first.
        successor: ActionType that must execute after.
        match_fn: Predicate that determines if two specific actions
                  are related by this rule. Receives (predecessor_action,
                  successor_action) and returns True if ordering applies.
    """

    predecessor: ActionType
    successor: ActionType
    match_fn: Callable[[ActionOperation, ActionOperation], bool]


# --- Rule Predicates ---


def _same_task_add_project_then_move_section(
    pred: ActionOperation,
    succ: ActionOperation,
) -> bool:
    """ADD_TO_PROJECT must precede MOVE_TO_SECTION for the same task.

    Since we cannot verify project membership at planning time without
    an API call, we conservatively assume the constraint applies when
    both actions target the same task. This is safe: it may over-order
    (place MOVE_TO_SECTION in a later tier than strictly necessary) but
    never under-order.
    """
    return pred.task.gid == succ.task.gid


# --- Rule Registry (extend here) ---

ORDERING_RULES: list[OrderingRule] = [
    OrderingRule(
        predecessor=ActionType.ADD_TO_PROJECT,
        successor=ActionType.MOVE_TO_SECTION,
        match_fn=_same_task_add_project_then_move_section,
    ),
    # Add new rules below. No graph logic changes needed.
]


# --- Public API ---


def resolve_order(
    actions: list[ActionOperation],
    rules: list[OrderingRule] | None = None,
) -> list[list[ActionOperation]]:
    """Resolve ordering constraints into tiers via topological sort.

    Uses Kahn's algorithm to partition actions into execution tiers.
    Actions within a tier have no mutual dependencies and can be freely
    grouped into batch chunks.

    Args:
        actions: All actions in a single commit.
        rules: Override rule set (defaults to ORDERING_RULES). Useful for testing.

    Returns:
        List of tiers (each tier is a list of ActionOperation).
        Tier 0 has no predecessors. Tier N depends only on tiers < N.
        Actions within a tier are in their original list order (stable).

    Raises:
        ValueError: If a cycle is detected in the dependency graph.
    """
    if not actions:
        return []

    if rules is None:
        rules = ORDERING_RULES

    # Index actions by type for efficient rule matching
    by_type: dict[ActionType, list[ActionOperation]] = defaultdict(list)
    for action in actions:
        by_type[action.action].append(action)

    # Build adjacency list and in-degree map
    # Key: id(action), Value: list of successor action ids
    adj: dict[int, list[int]] = defaultdict(list)
    in_degree: dict[int, int] = {id(a): 0 for a in actions}
    action_map: dict[int, ActionOperation] = {id(a): a for a in actions}

    for rule in rules:
        predecessors = by_type.get(rule.predecessor, [])
        successors = by_type.get(rule.successor, [])

        for pred in predecessors:
            for succ in successors:
                if rule.match_fn(pred, succ):
                    adj[id(pred)].append(id(succ))
                    in_degree[id(succ)] += 1

    # Preserve original list order for stable sorting within tiers
    original_order: dict[int, int] = {id(a): i for i, a in enumerate(actions)}

    # Kahn's algorithm with tier tracking
    tiers: list[list[ActionOperation]] = []
    # Start with all actions that have no predecessors
    current_tier_ids = deque(aid for aid, deg in in_degree.items() if deg == 0)

    placed = 0

    while current_tier_ids:
        tier: list[ActionOperation] = []
        next_tier_ids: deque[int] = deque()

        while current_tier_ids:
            aid = current_tier_ids.popleft()
            tier.append(action_map[aid])
            placed += 1

            for succ_id in adj[aid]:
                in_degree[succ_id] -= 1
                if in_degree[succ_id] == 0:
                    next_tier_ids.append(succ_id)

        # Stable sort: preserve original list order within tier
        tier.sort(key=lambda a: original_order[id(a)])

        tiers.append(tier)
        current_tier_ids = next_tier_ids

    if placed != len(actions):
        raise ValueError(
            f"Cycle detected in action ordering: placed {placed}/{len(actions)} actions"
        )

    return tiers
