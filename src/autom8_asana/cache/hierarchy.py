"""Hierarchy index for parent-child task relationships.

Per TDD-UNIFIED-CACHE-001: Maintains bidirectional parent-child mappings
for efficient traversal in both directions. Used for cascade invalidation
and parent chain resolution.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class HierarchyIndex:
    """Index of task hierarchy relationships.

    Maintains bidirectional parent-child mappings for efficient
    traversal in both directions. Used for cascade invalidation
    and parent chain resolution.

    Thread Safety:
        All operations are protected by a threading.Lock to ensure
        thread-safe concurrent access.

    Example:
        >>> index = HierarchyIndex()
        >>> index.register({"gid": "child-1", "parent": {"gid": "parent-1"}})
        >>> index.get_parent_gid("child-1")
        'parent-1'
        >>> index.get_children_gids("parent-1")
        {'child-1'}
        >>> index.get_ancestor_chain("child-1")
        ['parent-1']
    """

    def __init__(self) -> None:
        """Initialize empty hierarchy index."""
        # Map: gid -> parent_gid (or None for root tasks)
        self._parent_map: dict[str, str | None] = {}
        # Map: gid -> set of child gids
        self._children_map: dict[str, set[str]] = {}
        # Map: gid -> entity_type (optional metadata)
        self._entity_types: dict[str, str | None] = {}
        # Lock for thread safety
        self._lock = threading.Lock()

    def register(
        self,
        task: dict[str, Any],
        entity_type: str | None = None,
    ) -> None:
        """Register task and update relationships.

        Extracts parent_gid from task.parent["gid"] when present.
        Updates both parent and children mappings bidirectionally.

        Args:
            task: Task dict with at least "gid" key.
                Optional "parent" key with nested "gid".
            entity_type: Optional detected entity type (e.g., "Business", "Unit").

        Raises:
            ValueError: If task is missing required "gid" field.
        """
        gid = task.get("gid")
        if not gid:
            raise ValueError("Task must have 'gid' field")

        # Extract parent_gid from nested structure
        parent_gid: str | None = None
        parent_data = task.get("parent")
        if parent_data and isinstance(parent_data, dict):
            parent_gid = parent_data.get("gid")

        with self._lock:
            # Get existing parent to check if it changed
            old_parent_gid = self._parent_map.get(gid)

            # If parent changed, remove from old parent's children
            if old_parent_gid is not None and old_parent_gid != parent_gid:
                if old_parent_gid in self._children_map:
                    self._children_map[old_parent_gid].discard(gid)

            # Update parent mapping
            self._parent_map[gid] = parent_gid

            # Add to new parent's children
            if parent_gid is not None:
                if parent_gid not in self._children_map:
                    self._children_map[parent_gid] = set()
                self._children_map[parent_gid].add(gid)

            # Store entity type if provided
            if entity_type is not None:
                self._entity_types[gid] = entity_type

            logger.debug(
                "hierarchy_registered",
                extra={
                    "gid": gid,
                    "parent_gid": parent_gid,
                    "entity_type": entity_type,
                },
            )

    def get_parent_gid(self, gid: str) -> str | None:
        """Get immediate parent GID.

        Args:
            gid: Task GID to look up.

        Returns:
            Parent GID if exists and task has parent, None otherwise.
        """
        with self._lock:
            return self._parent_map.get(gid)

    def get_children_gids(self, gid: str) -> set[str]:
        """Get immediate children GIDs.

        Args:
            gid: Task GID to look up.

        Returns:
            Set of child GIDs (may be empty).
        """
        with self._lock:
            # Return a copy to prevent external modification
            children = self._children_map.get(gid)
            return set(children) if children else set()

    def get_ancestor_chain(
        self,
        gid: str,
        max_depth: int = 5,
    ) -> list[str]:
        """Get ancestor GIDs from immediate parent to root.

        Traverses parent links up to max_depth levels.

        Args:
            gid: Starting task GID.
            max_depth: Maximum chain depth (default 5).

        Returns:
            List of ancestor GIDs from immediate parent to root.
            Empty list if task has no parent or is not registered.

        Example:
            >>> # Given: child -> parent -> grandparent
            >>> index.get_ancestor_chain("child")
            ['parent', 'grandparent']
        """
        chain: list[str] = []
        current_gid = gid

        with self._lock:
            for _ in range(max_depth):
                parent_gid = self._parent_map.get(current_gid)
                if parent_gid is None:
                    break
                chain.append(parent_gid)
                current_gid = parent_gid

        return chain

    def get_descendant_gids(
        self,
        gid: str,
        max_depth: int | None = None,
    ) -> set[str]:
        """Get all descendant GIDs (for cascade invalidation).

        Performs breadth-first traversal of children.

        Args:
            gid: Starting task GID.
            max_depth: Maximum traversal depth. None for unlimited.

        Returns:
            Set of all descendant GIDs (not including the starting GID).
        """
        descendants: set[str] = set()

        with self._lock:
            # BFS traversal
            current_level = {gid}
            depth = 0

            while current_level:
                if max_depth is not None and depth >= max_depth:
                    break

                next_level: set[str] = set()
                for current_gid in current_level:
                    children = self._children_map.get(current_gid, set())
                    for child_gid in children:
                        if child_gid not in descendants:
                            descendants.add(child_gid)
                            next_level.add(child_gid)

                current_level = next_level
                depth += 1

        return descendants

    def get_root_gid(self, gid: str) -> str | None:
        """Get root GID for this task's hierarchy.

        Traverses parent links to find the ultimate ancestor
        (task with no parent). Returns the starting GID if it
        has no parent.

        Args:
            gid: Task GID to find root for.

        Returns:
            Root GID, or None if task not registered.
        """
        with self._lock:
            if gid not in self._parent_map:
                return None

            current_gid = gid
            # Safety limit to prevent infinite loops
            for _ in range(100):
                parent_gid = self._parent_map.get(current_gid)
                if parent_gid is None:
                    return current_gid
                current_gid = parent_gid

            # Shouldn't reach here unless there's a cycle
            logger.warning(
                "hierarchy_cycle_detected",
                extra={"gid": gid, "current_gid": current_gid},
            )
            return current_gid

    def get_entity_type(self, gid: str) -> str | None:
        """Get stored entity type for a task.

        Args:
            gid: Task GID.

        Returns:
            Entity type if registered, None otherwise.
        """
        with self._lock:
            return self._entity_types.get(gid)

    def contains(self, gid: str) -> bool:
        """Check if GID is registered in the index.

        Args:
            gid: Task GID to check.

        Returns:
            True if GID is registered, False otherwise.
        """
        with self._lock:
            return gid in self._parent_map

    def remove(self, gid: str) -> None:
        """Remove task from index.

        Cleans up all relationships (parent/child mappings).

        Args:
            gid: Task GID to remove.
        """
        with self._lock:
            # Get parent to update parent's children
            parent_gid = self._parent_map.get(gid)
            if parent_gid is not None and parent_gid in self._children_map:
                self._children_map[parent_gid].discard(gid)

            # Remove from parent map
            self._parent_map.pop(gid, None)

            # Remove children mapping (children become orphaned)
            # Note: We don't update children's parent references here
            # as they still point to this GID
            self._children_map.pop(gid, None)

            # Remove entity type
            self._entity_types.pop(gid, None)

    def clear(self) -> None:
        """Clear all entries from the index."""
        with self._lock:
            self._parent_map.clear()
            self._children_map.clear()
            self._entity_types.clear()

    def __len__(self) -> int:
        """Return number of registered tasks."""
        with self._lock:
            return len(self._parent_map)

    def get_stats(self) -> dict[str, int]:
        """Get index statistics.

        Returns:
            Dict with task_count, root_count, max_depth info.
        """
        with self._lock:
            task_count = len(self._parent_map)
            root_count = sum(
                1 for parent_gid in self._parent_map.values() if parent_gid is None
            )
            return {
                "task_count": task_count,
                "root_count": root_count,
                "children_map_size": len(self._children_map),
            }
