"""Dependency graph with Kahn's algorithm for topological sort.

Per ADR-0037: Use Kahn's algorithm for O(V+E) dependency ordering.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any

from autom8_asana.persistence.errors import CyclicDependencyError

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class DependencyGraph:
    """Dependency graph with Kahn's algorithm for topological sort.

    Per ADR-0037: Use Kahn's algorithm for O(V+E) dependency ordering.

    Responsibilities:
    - Build graph from entity relationships (parent field)
    - Detect cycles before save
    - Produce topologically sorted levels for batch execution

    The graph is rebuilt each time build() is called, allowing
    reuse across multiple commits in a session.
    """

    def __init__(self) -> None:
        """Initialize empty graph state."""
        # gid -> entity
        self._entities: dict[str, AsanaResource] = {}
        # gid -> set of dependent gids (edges: dependency -> dependent)
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        # gid -> number of dependencies
        self._in_degree: dict[str, int] = defaultdict(int)

    def build(self, entities: list[AsanaResource]) -> None:
        """Build dependency graph from entities.

        Per FR-DEPEND-001: Detect parent-child relationships from parent field.

        Args:
            entities: List of entities to include in graph.
        """
        self._entities.clear()
        self._adjacency.clear()
        self._in_degree.clear()

        # Index entities by GID (including temp GIDs)
        for entity in entities:
            gid = self._get_gid(entity)
            self._entities[gid] = entity
            self._in_degree[gid] = 0

        # Build edges based on parent field
        for entity in entities:
            child_gid = self._get_gid(entity)

            # Check for parent dependency
            parent_ref = getattr(entity, "parent", None)
            if parent_ref is not None:
                parent_gid = self._resolve_parent_gid(parent_ref, entities)

                if parent_gid and parent_gid in self._entities:
                    # Edge: parent -> child (parent must be saved first)
                    self._adjacency[parent_gid].add(child_gid)
                    self._in_degree[child_gid] += 1

    def topological_sort(self) -> list[AsanaResource]:
        """Perform topological sort using Kahn's algorithm.

        Per FR-DEPEND-002: Use Kahn's algorithm with O(V+E) complexity.
        Per FR-DEPEND-003: Raise CyclicDependencyError if cycle detected.

        Returns:
            Entities in dependency order (dependencies first).

        Raises:
            CyclicDependencyError: If graph contains cycles.
        """
        # Copy in_degree for modification
        in_degree = dict(self._in_degree)

        # Start with nodes that have no dependencies
        queue: deque[str] = deque(gid for gid, degree in in_degree.items() if degree == 0)

        result: list[AsanaResource] = []

        while queue:
            gid = queue.popleft()
            result.append(self._entities[gid])

            # Reduce in-degree of dependents
            for dependent_gid in self._adjacency.get(gid, set()):
                in_degree[dependent_gid] -= 1
                if in_degree[dependent_gid] == 0:
                    queue.append(dependent_gid)

        # If not all nodes processed, there's a cycle
        if len(result) != len(self._entities):
            cycle = self._find_cycle(in_degree)
            raise CyclicDependencyError(cycle)

        return result

    def get_levels(self) -> list[list[AsanaResource]]:
        """Get entities grouped by dependency level.

        Per FR-DEPEND-007: Group independent entities for parallel batching.
        Per FR-BATCH-001: Group operations by dependency level.

        Level 0 contains entities with no dependencies.
        Level N contains entities that depend only on entities in levels < N.

        Returns:
            List of lists where index is dependency level.

        Raises:
            CyclicDependencyError: If graph contains cycles.
        """
        # Handle empty graph
        if not self._entities:
            return []

        # Copy in_degree for modification
        in_degree = dict(self._in_degree)

        levels: list[list[AsanaResource]] = []
        remaining = set(self._entities.keys())

        while remaining:
            # Find all nodes with in_degree 0 among remaining
            level_gids = [gid for gid in remaining if in_degree.get(gid, 0) == 0]

            if not level_gids:
                # Cycle detected
                cycle = self._find_cycle(in_degree)
                raise CyclicDependencyError(cycle)

            # Add level
            levels.append([self._entities[gid] for gid in level_gids])

            # Remove from remaining and update in_degrees
            for gid in level_gids:
                remaining.discard(gid)
                for dependent_gid in self._adjacency.get(gid, set()):
                    in_degree[dependent_gid] -= 1

        return levels

    def add_explicit_dependency(
        self,
        dependent: AsanaResource,
        dependency: AsanaResource,
    ) -> None:
        """Add explicit dependency between entities.

        Per FR-DEPEND-008: Support explicit dependency declaration.

        Args:
            dependent: Entity that depends on another.
            dependency: Entity that must be saved first.
        """
        dependent_gid = self._get_gid(dependent)
        dependency_gid = self._get_gid(dependency)

        if (
            dependent_gid in self._entities
            and dependency_gid in self._entities
            and dependent_gid not in self._adjacency.get(dependency_gid, set())
        ):
            self._adjacency[dependency_gid].add(dependent_gid)
            self._in_degree[dependent_gid] += 1

    def _get_gid(self, entity: AsanaResource) -> str:
        """Get or generate GID for entity.

        Args:
            entity: Entity to get GID for.

        Returns:
            Entity's GID or temp_{id(entity)} for new entities.
        """
        if entity.gid and not entity.gid.startswith("temp_"):
            return entity.gid
        # Generate temporary GID for new entities
        return f"temp_{id(entity)}"

    def _resolve_parent_gid(
        self,
        parent_ref: Any,
        entities: list[AsanaResource],
    ) -> str | None:
        """Resolve parent reference to GID.

        Parent can be:
        - String GID
        - NameGid object with .gid attribute (real or temp GID)
        - Another AsanaResource entity

        Per TDD-GAP-01 Section 4.4 (Option A): Temp GID strings in NameGid
        references are valid parent identifiers when the referenced entity
        is in the graph. This enables the ENSURE_HOLDERS phase to wire
        child.parent = NameGid(gid=holder_temp_gid) and have the graph
        produce correct dependency levels.

        Args:
            parent_ref: The parent reference from entity.
            entities: List of entities in the graph (for object lookup).

        Returns:
            The resolved GID or None if not resolvable.
        """
        if isinstance(parent_ref, str):
            return parent_ref

        if hasattr(parent_ref, "gid"):
            # Could be NameGid or AsanaResource
            gid: str | None = parent_ref.gid
            if gid and not gid.startswith("temp_"):
                return gid
            # Temp GID: check if it references an entity in the graph.
            # This supports NameGid(gid="temp_xxx") references created by
            # the ENSURE_HOLDERS phase (holder auto-creation).
            if gid and gid.startswith("temp_") and gid in self._entities:
                return gid
            # Fallback: check if parent_ref IS a tracked entity (identity check)
            for entity in entities:
                if entity is parent_ref:
                    return self._get_gid(entity)

        return None

    def _find_cycle(
        self,
        in_degree: dict[str, int],
    ) -> list[AsanaResource]:
        """Find entities involved in a cycle for error reporting.

        Args:
            in_degree: Current in_degree state after partial processing.

        Returns:
            List of entities that couldn't be sorted (cycle participants).
        """
        # Return entities that couldn't be sorted (have remaining in_degree > 0)
        cycle_gids = [gid for gid, deg in in_degree.items() if deg > 0]
        # Limit to first 5 for readable error message
        return [self._entities[gid] for gid in cycle_gids[:5]]
