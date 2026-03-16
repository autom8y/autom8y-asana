"""Execution context for Automation Layer.

Per TDD-AUTOMATION-LAYER: AutomationContext provides execution context and loop prevention.
Per FR-011: Max cascade depth configuration prevents circular trigger chains.
Per FR-012: Visited set tracking prevents same entity triggering same rule twice in chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.automation.config import AutomationConfig
    from autom8_asana.client import AsanaClient
    from autom8_asana.persistence.models import SaveResult


@dataclass
class AutomationContext:
    """Execution context for automation rules.

    Provides access to SDK client, configuration, and cascade tracking.

    Per FR-011: Tracks depth for max cascade depth enforcement.
    Per FR-012: Tracks visited (entity_gid, rule_id) pairs for loop prevention.

    Attributes:
        client: AsanaClient for API operations.
        config: AutomationConfig with settings.
        depth: Current cascade depth (for loop prevention).
        visited: Set of (entity_gid, rule_id) already processed.
        save_result: Original SaveResult that triggered automation.

    Example:
        context = AutomationContext(
            client=client,
            config=config,
            depth=0,
            visited=set(),
            save_result=result,
        )

        # Check if can continue without loop
        if context.can_continue(entity.gid, rule.id):
            context.mark_visited(entity.gid, rule.id)
            # Execute rule...

        # Create child context for nested automation
        child_context = context.child_context()
    """

    client: AsanaClient
    config: AutomationConfig
    depth: int = 0
    visited: set[tuple[str, str]] = field(default_factory=set)
    save_result: SaveResult | None = None

    def can_continue(self, entity_gid: str, rule_id: str) -> bool:
        """Check if automation can continue without loop.

        Per FR-011/FR-012: Depth and visited set tracking.

        Two-layer protection:
        1. Depth prevents unbounded recursion (max_cascade_depth).
        2. Visited set prevents same (entity, rule) pair executing twice.

        Args:
            entity_gid: GID of entity being processed.
            rule_id: ID of rule to execute.

        Returns:
            True if safe to continue, False if would loop.
        """
        # Check depth limit
        if self.depth >= self.config.max_cascade_depth:
            return False

        # Check visited set
        key = (entity_gid, rule_id)
        return key not in self.visited

    def mark_visited(self, entity_gid: str, rule_id: str) -> None:
        """Mark entity/rule pair as visited.

        Args:
            entity_gid: GID of entity being processed.
            rule_id: ID of rule executed.
        """
        self.visited.add((entity_gid, rule_id))

    def child_context(self) -> AutomationContext:
        """Create child context with incremented depth.

        Used when automation triggers nested automation (e.g., creating
        an entity that itself triggers another rule).

        The visited set is shared by reference, so loop detection
        works across the entire automation chain.

        Returns:
            New AutomationContext with depth + 1, shared visited set.
        """
        return AutomationContext(
            client=self.client,
            config=self.config,
            depth=self.depth + 1,
            visited=self.visited,  # Shared reference
            save_result=self.save_result,
        )
