"""Batch modification checking with TTL-based caching.

This module provides efficient batch modification checking to prevent
spamming the Asana API with repeated modification timestamp requests.

Per ADR-0018: Uses a 25-second in-memory TTL for modification checks,
with per-run isolation to prevent stale data across different processes.
"""

from __future__ import annotations

import functools
import os
import socket
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

# Default TTL for modification checks (per ADR-0018)
DEFAULT_MODIFICATION_CHECK_TTL = 25.0

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ModificationCheck:
    """Cached result of a modification check.

    Attributes:
        gid: Task GID.
        modified_at: The modified_at timestamp from Asana.
        checked_at: Monotonic time when this check was performed.
    """

    gid: str
    modified_at: str
    checked_at: float  # time.monotonic()


class ModificationCheckCache:
    """In-memory cache for modification checks with TTL.

    Per ADR-0018:
    - 25-second TTL (configurable)
    - Per-run isolation (different runs don't share cache)
    - Thread-safe via threading.Lock

    This cache prevents repeated API calls to check modification timestamps
    within a short time window. Each "run" (ECS task, container, or process)
    maintains its own cache to avoid stale cross-process data.

    Thread Safety:
        All operations are protected by a threading.Lock for safe
        concurrent access from multiple threads.

    Example:
        >>> cache = ModificationCheckCache(ttl=25.0)
        >>> cache.set("123", "2025-01-01T00:00:00Z")
        >>> check = cache.get("123")
        >>> check.modified_at if check else None
        '2025-01-01T00:00:00Z'
    """

    def __init__(
        self,
        ttl: float = DEFAULT_MODIFICATION_CHECK_TTL,
        run_id: str | None = None,
    ) -> None:
        """Initialize modification check cache.

        Args:
            ttl: Time-to-live in seconds for cached checks.
                Defaults to 25 seconds per ADR-0018.
            run_id: Unique identifier for this run/process.
                Auto-generated if not provided.
        """
        self._cache: dict[str, ModificationCheck] = {}
        self._ttl = ttl
        self._run_id = run_id or self._generate_run_id()
        self._lock = threading.Lock()

    @staticmethod
    def _generate_run_id() -> str:
        """Generate a unique run ID for cache isolation.

        Attempts to use ECS-specific identifiers first, then falls
        back to hostname + PID for local development.

        Returns:
            Unique string identifying this run/process.
        """
        # Try ECS task metadata URI (ECS Fargate/EC2)
        ecs_metadata_uri = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
        if ecs_metadata_uri:
            return ecs_metadata_uri

        # Try ECS task ID environment variable
        ecs_task_id = os.environ.get("ECS_TASK_ID")
        if ecs_task_id:
            return ecs_task_id

        # Fallback to hostname + PID (local development)
        return f"{socket.gethostname()}:{os.getpid()}"

    @property
    def run_id(self) -> str:
        """Get the run ID for this cache instance."""
        return self._run_id

    @property
    def ttl(self) -> float:
        """Get the TTL in seconds."""
        return self._ttl

    def get(self, gid: str) -> ModificationCheck | None:
        """Get cached modification check if still valid.

        Args:
            gid: Task GID to look up.

        Returns:
            ModificationCheck if found and not expired, None otherwise.
        """
        with self._lock:
            check = self._cache.get(gid)
            if check is None:
                return None

            # Check TTL using monotonic time (immune to wall clock changes)
            if time.monotonic() - check.checked_at > self._ttl:
                del self._cache[gid]
                return None

            return check

    def get_many(self, gids: list[str]) -> tuple[dict[str, str], list[str]]:
        """Get cached modifications for multiple GIDs.

        Efficiently retrieves cached checks for multiple GIDs in a
        single operation, separating found (cached) from unfound (uncached).

        Args:
            gids: List of task GIDs to look up.

        Returns:
            Tuple of (cached: dict[gid, modified_at], uncached: list[gid]).
            - cached: GIDs found in cache with their modified_at values
            - uncached: GIDs not in cache or expired
        """
        cached: dict[str, str] = {}
        uncached: list[str] = []

        for gid in gids:
            check = self.get(gid)
            if check:
                cached[gid] = check.modified_at
            else:
                uncached.append(gid)

        return cached, uncached

    def set(self, gid: str, modified_at: str) -> None:
        """Cache a modification check result.

        Args:
            gid: Task GID.
            modified_at: The modified_at timestamp from Asana.
        """
        with self._lock:
            self._cache[gid] = ModificationCheck(
                gid=gid,
                modified_at=modified_at,
                checked_at=time.monotonic(),
            )

    def set_many(self, modifications: dict[str, str]) -> None:
        """Cache multiple modification check results.

        Efficiently stores multiple results in a single operation,
        all with the same checked_at timestamp.

        Args:
            modifications: Dict mapping GID to modified_at timestamp.
        """
        now = time.monotonic()
        with self._lock:
            for gid, modified_at in modifications.items():
                self._cache[gid] = ModificationCheck(
                    gid=gid,
                    modified_at=modified_at,
                    checked_at=now,
                )

    def clear(self) -> None:
        """Clear all cached checks."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get number of cached checks.

        Returns:
            Count of entries (including potentially expired ones
            that haven't been cleaned up yet).
        """
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Useful for periodic cleanup to free memory.

        Returns:
            Number of entries removed.
        """
        now = time.monotonic()
        removed = 0
        with self._lock:
            expired_gids = [
                gid
                for gid, check in self._cache.items()
                if now - check.checked_at > self._ttl
            ]
            for gid in expired_gids:
                del self._cache[gid]
                removed += 1
        return removed


# Global modification check cache (per-process singleton)
_modification_cache: ModificationCheckCache | None = None
_modification_cache_lock = threading.Lock()


def get_modification_cache(
    ttl: float = DEFAULT_MODIFICATION_CHECK_TTL,
) -> ModificationCheckCache:
    """Get or create the global modification check cache.

    Returns a singleton cache instance for the current process.
    Thread-safe initialization.

    Args:
        ttl: TTL in seconds. Only used if creating a new cache.
            Ignored if cache already exists.

    Returns:
        The global ModificationCheckCache instance.
    """
    global _modification_cache
    with _modification_cache_lock:
        if _modification_cache is None:
            _modification_cache = ModificationCheckCache(ttl=ttl)
        return _modification_cache


def reset_modification_cache() -> None:
    """Reset the global modification check cache.

    Primarily for testing. Clears the singleton instance so a new
    one will be created on next access.
    """
    global _modification_cache
    with _modification_cache_lock:
        _modification_cache = None


async def fetch_task_modifications(
    gids: list[str],
    batch_api: Callable[[list[str]], Awaitable[dict[str, str]]],
    cache_ttl: float = DEFAULT_MODIFICATION_CHECK_TTL,
) -> dict[str, str]:
    """Fetch modified_at timestamps for tasks, using in-memory TTL cache.

    This function implements the TTL-cached modification checking
    per ADR-0018. It first checks the in-memory cache for recent
    results, then calls the batch API only for uncached GIDs.

    Args:
        gids: Task GIDs to check.
        batch_api: Async function to call Asana batch API for uncached GIDs.
            Should accept list of GIDs and return dict[gid, modified_at].
        cache_ttl: TTL for cached results. Defaults to 25s per ADR-0018.

    Returns:
        Dict mapping GID to modified_at timestamp.

    Example:
        >>> async def mock_batch_api(gids: list[str]) -> dict[str, str]:
        ...     return {gid: "2025-01-01T00:00:00Z" for gid in gids}
        >>> import asyncio
        >>> result = asyncio.run(fetch_task_modifications(
        ...     ["123", "456"],
        ...     mock_batch_api,
        ... ))
        >>> "123" in result
        True
    """
    if not gids:
        return {}

    cache = get_modification_cache(ttl=cache_ttl)

    # Get cached values
    cached, uncached = cache.get_many(gids)

    if not uncached:
        # All GIDs were cached - no API call needed
        return cached

    # Fetch uncached from API
    fetched = await batch_api(uncached)

    # Cache the results
    cache.set_many(fetched)

    # Merge cached and fetched
    return {**cached, **fetched}


def ttl_cached_modifications(
    ttl: float = DEFAULT_MODIFICATION_CHECK_TTL,
) -> Callable[
    [Callable[..., Awaitable[dict[str, str]]]],
    Callable[..., Awaitable[dict[str, str]]],
]:
    """Decorator that adds TTL caching to a modification fetcher function.

    Wraps an async function that fetches modification timestamps,
    adding transparent TTL-based caching. Only uncached GIDs are
    passed to the wrapped function.

    Args:
        ttl: TTL in seconds for cached results. Defaults to 25s per ADR-0018.

    Returns:
        Decorator function.

    Example:
        >>> @ttl_cached_modifications(ttl=25.0)
        ... async def fetch_modifications(gids: list[str]) -> dict[str, str]:
        ...     # This would call the actual Asana batch API
        ...     return {gid: "2025-01-01T00:00:00Z" for gid in gids}
        ...
        >>> import asyncio
        >>> # First call hits API
        >>> result1 = asyncio.run(fetch_modifications(["123"]))
        >>> # Second call within 25s uses cache
        >>> result2 = asyncio.run(fetch_modifications(["123"]))
    """

    def decorator(
        func: Callable[..., Awaitable[dict[str, str]]],
    ) -> Callable[..., Awaitable[dict[str, str]]]:
        @functools.wraps(func)
        async def wrapper(
            gids: list[str],
            *args: object,
            **kwargs: object,
        ) -> dict[str, str]:
            return await fetch_task_modifications(
                gids=gids,
                batch_api=lambda uncached: func(uncached, *args, **kwargs),
                cache_ttl=ttl,
            )

        return wrapper

    return decorator
