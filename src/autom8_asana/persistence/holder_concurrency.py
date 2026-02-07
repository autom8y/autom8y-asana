"""Concurrency manager for holder auto-creation.

Per TDD-GAP-01 Section 3.5: asyncio.Lock manager keyed by (parent_gid, holder_type).
Per PRD-GAP-01 FR-005: Prevent duplicate holder creation under in-process concurrency.

Locks are created lazily on first acquisition and held for the duration of the
detect-or-create critical section. The lock key is (parent_gid, holder_type) so
that two different parents can safely create their holders concurrently.

Lifecycle:
- Created: SaveSession.__init__
- Used: During ENSURE_HOLDERS phase of each commit
- Destroyed: When SaveSession is garbage collected (or context exited)

Thread safety: asyncio.Lock is coroutine-safe but not thread-safe.
This matches the SaveSession concurrency model (asyncio coroutines).
"""

from __future__ import annotations

import asyncio


class HolderConcurrencyManager:
    """Per-session asyncio.Lock manager keyed by (parent_gid, holder_type).

    Created by SaveSession.__init__ and passed to HolderEnsurer.
    Locks are created lazily on first acquisition and held for the
    duration of the detect-or-create critical section.

    Example:
        manager = HolderConcurrencyManager()
        lock = manager.get_lock("parent_gid_123", "contact_holder")
        async with lock:
            # detect-or-create critical section
            ...
    """

    def __init__(self) -> None:
        """Initialize with empty lock registry."""
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    def get_lock(self, parent_gid: str, holder_type: str) -> asyncio.Lock:
        """Get or create a lock for (parent_gid, holder_type).

        Args:
            parent_gid: GID of the parent entity (Business or Unit).
            holder_type: Holder key name (e.g., "contact_holder").

        Returns:
            asyncio.Lock for the given (parent_gid, holder_type) pair.
        """
        key = (parent_gid, holder_type)
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
