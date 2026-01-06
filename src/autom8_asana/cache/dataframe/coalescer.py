"""Request coalescing for DataFrame build deduplication.

Per TDD-DATAFRAME-CACHE-001: First request builds, others wait.

This coalescer is specifically for DataFrame build operations (different
from the staleness check coalescer in cache/coalescer.py).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict

from autom8y_log import get_logger

logger = get_logger(__name__)


class BuildStatus(Enum):
    """Status of a DataFrame build operation."""

    BUILDING = "building"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class BuildState:
    """State for an in-progress DataFrame build."""

    status: BuildStatus
    started_at: datetime
    event: asyncio.Event
    waiter_count: int = 0


@dataclass
class DataFrameCacheCoalescer:
    """Coalesces concurrent build requests for the same cache key.

    Per TDD-DATAFRAME-CACHE-001:
    - First request acquires lock and builds
    - Subsequent requests wait for first to complete
    - All waiters get notified on completion

    This prevents the "thundering herd" problem where multiple concurrent
    requests for a cache miss would all attempt to build the same DataFrame.

    Algorithm:
    1. First request for a key calls try_acquire_async() -> True
    2. Subsequent requests call try_acquire_async() -> False
    3. Subsequent requests call wait_async() to wait for completion
    4. First request calls release_async(success=True/False)
    5. All waiters are notified and can check cache

    Attributes:
        max_wait_seconds: Maximum time waiters will wait (default 60s).

    Example:
        >>> coalescer = DataFrameCacheCoalescer()
        >>>
        >>> # First request acquires
        >>> acquired = await coalescer.try_acquire_async("key")  # True
        >>>
        >>> # Second request does not acquire
        >>> acquired = await coalescer.try_acquire_async("key")  # False
        >>>
        >>> # Second request waits
        >>> success = await coalescer.wait_async("key", timeout=30)
        >>>
        >>> # First request completes
        >>> await coalescer.release_async("key", success=True)
    """

    max_wait_seconds: float = 60.0

    # Internal state
    _builds: Dict[str, BuildState] = field(default_factory=dict, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize statistics."""
        self._stats = {
            "acquires": 0,
            "waits": 0,
            "wait_timeouts": 0,
            "completions_success": 0,
            "completions_failure": 0,
        }

    async def try_acquire_async(self, key: str) -> bool:
        """Attempt to acquire build lock.

        If no build is in progress for this key, acquires the lock and
        returns True. The caller should then perform the build and call
        release_async when done.

        If a build is already in progress, returns False. The caller
        should then call wait_async to wait for the build to complete.

        Args:
            key: Cache key to build (entity_type:project_gid).

        Returns:
            True if caller should build, False if build in progress.
        """
        async with self._lock:
            if key in self._builds:
                state = self._builds[key]
                if state.status == BuildStatus.BUILDING:
                    return False

            # Acquire lock
            self._builds[key] = BuildState(
                status=BuildStatus.BUILDING,
                started_at=datetime.now(timezone.utc),
                event=asyncio.Event(),
            )
            self._stats["acquires"] += 1

            logger.debug(
                "dataframe_coalescer_acquire",
                extra={"key": key},
            )

            return True

    async def wait_async(
        self,
        key: str,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Wait for in-progress build to complete.

        Blocks until the build completes (success or failure) or timeout.

        Args:
            key: Cache key being built.
            timeout_seconds: Maximum wait time (default: max_wait_seconds).

        Returns:
            True if build succeeded, False on timeout or failure.
        """
        timeout = timeout_seconds or self.max_wait_seconds

        async with self._lock:
            if key not in self._builds:
                return False

            state = self._builds[key]
            state.waiter_count += 1

        self._stats["waits"] += 1

        try:
            await asyncio.wait_for(
                state.event.wait(),
                timeout=timeout,
            )

            return state.status == BuildStatus.SUCCESS

        except asyncio.TimeoutError:
            self._stats["wait_timeouts"] += 1
            logger.warning(
                "dataframe_coalescer_wait_timeout",
                extra={"key": key, "timeout": timeout},
            )
            return False

        finally:
            async with self._lock:
                if key in self._builds:
                    self._builds[key].waiter_count -= 1

    async def release_async(self, key: str, success: bool) -> None:
        """Release build lock and notify waiters.

        Must be called by the request that acquired the lock (returned
        True from try_acquire_async).

        Args:
            key: Cache key that was built.
            success: Whether build succeeded.
        """
        async with self._lock:
            if key not in self._builds:
                return

            state = self._builds[key]
            state.status = BuildStatus.SUCCESS if success else BuildStatus.FAILURE
            state.event.set()

            if success:
                self._stats["completions_success"] += 1
            else:
                self._stats["completions_failure"] += 1

            logger.debug(
                "dataframe_coalescer_release",
                extra={
                    "key": key,
                    "success": success,
                    "waiter_count": state.waiter_count,
                },
            )

            # Schedule cleanup after a delay (let waiters read status)
            asyncio.create_task(self._cleanup_after_delay(key, delay=5.0))

    async def _cleanup_after_delay(self, key: str, delay: float) -> None:
        """Remove build state after delay.

        Gives waiters time to read the final status before cleanup.

        Args:
            key: Cache key to clean up.
            delay: Seconds to wait before cleanup.
        """
        await asyncio.sleep(delay)
        async with self._lock:
            if key in self._builds:
                state = self._builds[key]
                if state.waiter_count == 0:
                    del self._builds[key]

    def is_building(self, key: str) -> bool:
        """Check if build is in progress for key.

        Args:
            key: Cache key to check.

        Returns:
            True if build is currently in progress.
        """
        return key in self._builds and self._builds[key].status == BuildStatus.BUILDING

    def get_stats(self) -> dict[str, int]:
        """Get coalescer statistics."""
        return dict(self._stats)

    async def force_cleanup(self, key: str) -> None:
        """Force cleanup of build state (for testing).

        Args:
            key: Cache key to clean up.
        """
        async with self._lock:
            if key in self._builds:
                del self._builds[key]
