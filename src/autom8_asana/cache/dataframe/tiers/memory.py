"""Memory tier for DataFrame hot cache.

Per TDD-DATAFRAME-CACHE-001: Dynamic heap-based limits with LRU/staleness eviction.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import CacheEntry

logger = get_logger(__name__)


def _get_container_memory_bytes() -> int:
    """Detect actual container memory limit via cgroup, env var, or fallback.

    Priority:
    1. CONTAINER_MEMORY_MB env var (explicit override)
    2. cgroup v2: /sys/fs/cgroup/memory.max
    3. cgroup v1: /sys/fs/cgroup/memory/memory.limit_in_bytes
    4. Fallback: 1GB (conservative default for unknown environments)
    """
    import os

    # 1. Explicit env var override
    env_mb = os.environ.get("CONTAINER_MEMORY_MB")
    if env_mb:
        try:
            return int(env_mb) * 1024 * 1024
        except ValueError:
            pass

    # 2. cgroup v2
    # 3. cgroup v1
    for path in [
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",
    ]:
        try:
            with open(path) as f:
                val = f.read().strip()
                if val not in ("max", "-1"):
                    return int(val)
        except (FileNotFoundError, ValueError, PermissionError):
            continue

    # 4. Fallback: 1GB
    return 1024 * 1024 * 1024


@dataclass
class MemoryTier:
    """Memory tier with LRU eviction and heap-based limits.

    Per TDD-DATAFRAME-CACHE-001:
    - Dynamic memory limit based on heap percentage
    - LRU + staleness-based eviction via evict_stale()
    - Thread-safe access via RLock

    The memory tier uses an OrderedDict to maintain LRU ordering.
    When entries are accessed (get), they move to the end (most recently used).
    When eviction is needed, entries are removed from the front (least recently used).

    Attributes:
        max_heap_percent: Maximum heap percentage to use (0.0-1.0).
        max_entries: Maximum number of entries (backup limit).

    Example:
        >>> tier = MemoryTier(max_heap_percent=0.3, max_entries=100)
        >>> tier.put("key", entry)
        >>> entry = tier.get("key")  # Moves to front of LRU
    """

    max_heap_percent: float = 0.3
    max_entries: int = 100

    # Internal state
    _cache: OrderedDict[str, CacheEntry] = field(
        default_factory=OrderedDict, init=False
    )
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)
    _current_bytes: int = field(default=0, init=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize statistics."""
        self._stats = {
            "gets": 0,
            "puts": 0,
            "evictions_lru": 0,
            "evictions_staleness": 0,
            "evictions_memory": 0,
        }

    def get(self, key: str) -> CacheEntry | None:
        """Get entry and move to front of LRU.

        Args:
            key: Cache key (entity_type:project_gid).

        Returns:
            CacheEntry if found, None otherwise.
        """
        with self._lock:
            self._stats["gets"] += 1

            if key not in self._cache:
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key: str, entry: CacheEntry) -> None:
        """Store entry with LRU tracking.

        Args:
            key: Cache key (entity_type:project_gid).
            entry: CacheEntry to store.
        """
        with self._lock:
            self._stats["puts"] += 1

            # Remove existing if present
            if key in self._cache:
                old_entry = self._cache.pop(key)
                self._current_bytes -= self._estimate_size(old_entry)

            # Check memory limit before adding
            entry_size = self._estimate_size(entry)
            while self._should_evict(entry_size):
                self._evict_one()

            # Check entry limit
            while len(self._cache) >= self.max_entries:
                self._evict_one()

            # Add new entry
            self._cache[key] = entry
            self._current_bytes += entry_size

    def remove(self, key: str) -> bool:
        """Remove entry by key.

        Args:
            key: Cache key.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_bytes -= self._estimate_size(entry)
                return True
            return False

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()
            self._current_bytes = 0

    def evict_stale(self, max_age_seconds: int) -> int:
        """Evict entries older than max_age_seconds.

        Per TDD: LRU/staleness-based eviction.

        Args:
            max_age_seconds: Maximum age in seconds.

        Returns:
            Number of entries evicted.
        """
        with self._lock:
            now = datetime.now(UTC)
            cutoff = now.timestamp() - max_age_seconds

            stale_keys = [
                key
                for key, entry in self._cache.items()
                if entry.created_at.timestamp() < cutoff
            ]

            for key in stale_keys:
                entry = self._cache.pop(key)
                self._current_bytes -= self._estimate_size(entry)
                self._stats["evictions_staleness"] += 1

            return len(stale_keys)

    def get_stats(self) -> dict[str, int]:
        """Get tier statistics."""
        with self._lock:
            return {
                **self._stats,
                "entry_count": len(self._cache),
                "current_bytes": self._current_bytes,
                "max_bytes": self._get_max_bytes(),
            }

    def __len__(self) -> int:
        """Return number of entries in cache."""
        with self._lock:
            return len(self._cache)

    def _should_evict(self, new_entry_size: int) -> bool:
        """Check if eviction needed for new entry."""
        if len(self._cache) == 0:
            return False

        max_bytes = self._get_max_bytes()
        return (self._current_bytes + new_entry_size) > max_bytes

    def _evict_one(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Pop from front (least recently used)
        key, entry = self._cache.popitem(last=False)
        self._current_bytes -= self._estimate_size(entry)
        self._stats["evictions_lru"] += 1

        logger.debug(
            "memory_tier_evict_lru",
            extra={"key": key, "row_count": entry.row_count},
        )

    def _get_max_bytes(self) -> int:
        """Calculate maximum bytes based on heap percentage of container memory."""
        total_memory = _get_container_memory_bytes()
        max_bytes = int(total_memory * self.max_heap_percent)

        logger.debug(
            "memory_tier_max_bytes",
            extra={
                "total_memory_mb": total_memory // (1024 * 1024),
                "heap_percent": self.max_heap_percent,
                "max_bytes_mb": max_bytes // (1024 * 1024),
            },
        )

        return max_bytes

    def _estimate_size(self, entry: CacheEntry) -> int:
        """Estimate entry size in bytes.

        Uses Polars' estimated_size() for DataFrame memory usage.

        Args:
            entry: CacheEntry to estimate.

        Returns:
            Estimated size in bytes.
        """
        return int(entry.dataframe.estimated_size())
