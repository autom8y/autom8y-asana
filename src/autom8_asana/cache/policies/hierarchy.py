"""Hierarchy index for parent-child task relationships.

Per TDD-UNIFIED-CACHE-001: Maintains bidirectional parent-child mappings
for efficient traversal in both directions. Used for cascade invalidation
and parent chain resolution.

Migration Note (SDK-PRIMITIVES-001):
    This module now wraps autom8y_cache.HierarchyTracker with Asana-specific
    extractors for gid and parent.gid. The HierarchyIndex class provides
    backward compatibility while delegating to the SDK primitive.
"""

from __future__ import annotations

import threading
from typing import Any

from autom8y_cache import HierarchyTracker
from autom8y_log import get_logger

logger = get_logger(__name__)


def _asana_gid_extractor(entity: Any) -> str | None:
    """Extract GID from Asana task dict.

    Args:
        entity: Task dict with "gid" key.

    Returns:
        GID string or None if not present.
    """
    if isinstance(entity, dict):
        return entity.get("gid")
    return None


def _asana_parent_gid_extractor(entity: Any) -> str | None:
    """Extract parent GID from Asana task dict.

    Asana tasks have parent in nested structure: task.parent.gid

    Args:
        entity: Task dict with optional "parent" key containing nested "gid".

    Returns:
        Parent GID string or None if not present.
    """
    if isinstance(entity, dict):
        parent = entity.get("parent")
        if parent and isinstance(parent, dict):
            gid: str | None = parent.get("gid")
            return gid
    return None


class HierarchyIndex:
    """Index of task hierarchy relationships.

    Maintains bidirectional parent-child mappings for efficient
    traversal in both directions. Used for cascade invalidation
    and parent chain resolution.

    Thread Safety:
        All operations are protected by thread-safe primitives to ensure
        thread-safe concurrent access.

    Implementation Note:
        This class wraps autom8y_cache.HierarchyTracker with Asana-specific
        extractors for gid and parent.gid. Entity type tracking is maintained
        locally as it's Asana-specific metadata not in the SDK primitive.

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
        # Delegate to SDK HierarchyTracker with Asana-specific extractors
        self._tracker: HierarchyTracker[str] = HierarchyTracker(
            id_extractor=_asana_gid_extractor,
            parent_id_extractor=_asana_parent_gid_extractor,
        )
        # Map: gid -> entity_type (Asana-specific metadata not in SDK)
        self._entity_types: dict[str, str | None] = {}
        # Lock for entity_types (tracker has its own internal locking)
        self._entity_types_lock = threading.Lock()

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

        # Delegate hierarchy tracking to SDK
        self._tracker.register(task)

        # Store entity type locally (Asana-specific metadata)
        if entity_type is not None:
            with self._entity_types_lock:
                self._entity_types[gid] = entity_type

        # Extract parent_gid for logging
        parent_gid = _asana_parent_gid_extractor(task)

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
        return self._tracker.get_parent_id(gid)

    def get_children_gids(self, gid: str) -> set[str]:
        """Get immediate children GIDs.

        Args:
            gid: Task GID to look up.

        Returns:
            Set of child GIDs (may be empty).
        """
        return self._tracker.get_children_ids(gid)

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
        return self._tracker.get_ancestor_chain(gid, max_depth=max_depth)

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
        return self._tracker.get_descendant_ids(gid, max_depth=max_depth)

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
        return self._tracker.get_root_id(gid)

    def get_entity_type(self, gid: str) -> str | None:
        """Get stored entity type for a task.

        Args:
            gid: Task GID.

        Returns:
            Entity type if registered, None otherwise.
        """
        with self._entity_types_lock:
            return self._entity_types.get(gid)

    def contains(self, gid: str) -> bool:
        """Check if GID is registered in the index.

        Args:
            gid: Task GID to check.

        Returns:
            True if GID is registered, False otherwise.
        """
        return self._tracker.contains(gid)

    def remove(self, gid: str) -> None:
        """Remove task from index.

        Cleans up all relationships (parent/child mappings).

        Args:
            gid: Task GID to remove.
        """
        self._tracker.remove(gid)

        # Also remove entity type
        with self._entity_types_lock:
            self._entity_types.pop(gid, None)

    def clear(self) -> None:
        """Clear all entries from the index."""
        self._tracker.clear()
        with self._entity_types_lock:
            self._entity_types.clear()

    def __len__(self) -> int:
        """Return number of registered tasks."""
        return len(self._tracker)

    def get_stats(self) -> dict[str, int]:
        """Get index statistics.

        Returns:
            Dict with task_count, root_count, max_depth info.
        """
        stats = self._tracker.get_stats()
        # Map SDK stat names to our existing API
        return {
            "task_count": stats.get("entity_count", 0),
            "root_count": stats.get("root_count", 0),
            "children_map_size": stats.get("children_map_size", 0),
        }
