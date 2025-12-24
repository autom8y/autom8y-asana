"""Request coalescer for batching staleness checks.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Batches staleness check requests
within a time window for efficient batch API usage.

Per ADR-0132: 50ms default window, 100 max batch, immediate flush at max.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.cache.entry import CacheEntry
    from autom8_asana.cache.lightweight_checker import LightweightChecker

logger = logging.getLogger(__name__)


@dataclass
class RequestCoalescer:
    """Batches staleness check requests within a time window.

    Per ADR-0132: Implements 50ms coalescing with immediate flush at max batch.

    Algorithm:
    1. First request starts timer (window_ms)
    2. Subsequent requests join pending batch
    3. Batch flushes when:
       a. Timer expires (window_ms)
       b. Max batch size reached (max_batch)
    4. Results distributed to all waiting callers
    5. Same GID requested multiple times = single API call, shared result

    Attributes:
        checker: LightweightChecker for executing batch checks.
        window_ms: Coalescing window in milliseconds (default 50).
        max_batch: Maximum batch size before immediate flush (default 100).

    Example:
        >>> coalescer = RequestCoalescer(
        ...     checker=lightweight_checker,
        ...     window_ms=50,
        ...     max_batch=100,
        ... )
        >>> # Multiple concurrent callers get batched together
        >>> results = await asyncio.gather(
        ...     coalescer.request_check_async(entry1),
        ...     coalescer.request_check_async(entry2),
        ...     coalescer.request_check_async(entry3),
        ... )
    """

    checker: "LightweightChecker" = field(repr=False)
    window_ms: int = 50
    max_batch: int = 100

    # Internal state
    _pending: dict[str, tuple["CacheEntry", "asyncio.Future[str | None]"]] = field(
        default_factory=dict, init=False, repr=False
    )
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _timer_task: asyncio.Task[None] | None = field(
        default=None, init=False, repr=False
    )
    _batch_start_time: float | None = field(default=None, init=False, repr=False)

    # Statistics
    _total_requests: int = field(default=0, init=False, repr=False)
    _total_batches: int = field(default=0, init=False, repr=False)
    _total_deduped: int = field(default=0, init=False, repr=False)

    async def request_check_async(self, entry: "CacheEntry") -> str | None:
        """Queue entry for batch staleness check.

        Per FR-BATCH-001 through FR-BATCH-006:
        - Collects entries within window_ms window
        - Deduplicates by GID (FR-BATCH-006)
        - Flushes immediately at max_batch (FR-BATCH-005)
        - Returns modified_at or None on error/deleted

        Args:
            entry: Cache entry to check (entry.key = GID).

        Returns:
            modified_at string if successfully checked, None on error/deleted.
        """
        gid = entry.key
        self._total_requests += 1

        async with self._lock:
            # FR-BATCH-006: Deduplication - if GID already pending, reuse its future
            if gid in self._pending:
                _, existing_future = self._pending[gid]
                self._total_deduped += 1
                logger.debug(
                    "coalescer_dedup",
                    extra={
                        "cache_operation": "staleness_check",
                        "gid": gid,
                        "pending_count": len(self._pending),
                    },
                )
                # Release lock before awaiting
                future_to_await = existing_future
            else:
                # Create new future for this request
                loop = asyncio.get_running_loop()
                future: asyncio.Future[str | None] = loop.create_future()
                self._pending[gid] = (entry, future)

                # Start timer on first request in batch
                if self._timer_task is None or self._timer_task.done():
                    self._batch_start_time = time.monotonic()
                    self._timer_task = asyncio.create_task(self._timer_flush())

                # FR-BATCH-005: Immediate flush if max batch reached
                if len(self._pending) >= self.max_batch:
                    logger.debug(
                        "coalescer_max_batch_flush",
                        extra={
                            "cache_operation": "staleness_check",
                            "batch_size": len(self._pending),
                            "trigger": "max_batch",
                        },
                    )
                    # Cancel timer and flush immediately
                    if self._timer_task and not self._timer_task.done():
                        self._timer_task.cancel()
                        try:
                            await self._timer_task
                        except asyncio.CancelledError:
                            pass
                    await self._flush_batch()

                future_to_await = future

        # Await outside lock to allow other requests to queue
        return await future_to_await

    async def _timer_flush(self) -> None:
        """Wait for window, then flush."""
        try:
            await asyncio.sleep(self.window_ms / 1000.0)
            async with self._lock:
                if self._pending:
                    logger.debug(
                        "coalescer_timer_flush",
                        extra={
                            "cache_operation": "staleness_check",
                            "batch_size": len(self._pending),
                            "trigger": "timer",
                            "window_ms": self.window_ms,
                        },
                    )
                    await self._flush_batch()
        except asyncio.CancelledError:
            # Timer was cancelled (max batch flush took over)
            pass

    async def _flush_batch(self) -> None:
        """Execute batch check and distribute results.

        Must be called with _lock held.
        """
        if not self._pending:
            return

        # Capture pending entries and clear for next batch
        batch = dict(self._pending)
        self._pending.clear()
        self._timer_task = None

        # Calculate actual window utilization
        window_utilization_ms = 0.0
        if self._batch_start_time is not None:
            window_utilization_ms = (
                time.monotonic() - self._batch_start_time
            ) * 1000.0
        self._batch_start_time = None

        # Extract entries for checker
        entries = [entry for entry, _ in batch.values()]
        unique_gids = len(batch)
        self._total_batches += 1

        logger.debug(
            "coalesce_batch_flush",
            extra={
                "cache_operation": "staleness_check",
                "batch_size": len(entries),
                "unique_gids": unique_gids,
                "coalesce_window_ms": self.window_ms,
                "entries_coalesced": len(entries),
                "chunk_count": (len(entries) + 9) // 10,
                "window_utilization_ms": round(window_utilization_ms, 2),
            },
        )

        try:
            # Execute batch check (outside lock would be ideal, but we need
            # to distribute results atomically)
            results = await self.checker.check_batch_async(entries)

            # Distribute results to waiting futures
            self._distribute_results(batch, results)
        except Exception as e:
            # Batch failed - set all futures to None
            logger.warning(
                "coalescer_batch_failure",
                extra={
                    "cache_operation": "staleness_check",
                    "batch_size": len(entries),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            for gid, (_, future) in batch.items():
                if not future.done():
                    future.set_result(None)

    def _distribute_results(
        self,
        batch: dict[str, tuple["CacheEntry", "asyncio.Future[str | None]"]],
        results: dict[str, str | None],
    ) -> None:
        """Set results on waiting futures.

        Args:
            batch: Dict of GID -> (entry, future).
            results: Dict of GID -> modified_at or None.
        """
        for gid, (_, future) in batch.items():
            if not future.done():
                modified_at = results.get(gid)
                future.set_result(modified_at)

    def get_stats(self) -> dict[str, int]:
        """Get coalescer statistics.

        Returns:
            Dict with total_requests, total_batches, total_deduped.
        """
        return {
            "total_requests": self._total_requests,
            "total_batches": self._total_batches,
            "total_deduped": self._total_deduped,
        }

    async def flush_pending(self) -> None:
        """Force flush any pending requests.

        Useful for cleanup or testing.
        """
        async with self._lock:
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
                try:
                    await self._timer_task
                except asyncio.CancelledError:
                    pass
            if self._pending:
                await self._flush_batch()
