"""DataFrame build coordination with coalescing and staleness awareness.

Per TDD-BUILD-COALESCING-001: Single entry point for all DataFrame build
requests. Deduplicates using asyncio.Future (ADR-BC-001), integrates with
MutationInvalidator staleness signals (ADR-BC-003), and enforces global
concurrency limits (ADR-BC-004).

Wraps the existing DataFrameCacheCoalescer (ADR-BC-002) rather than
replacing it, allowing incremental migration across phases.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import polars as pl

logger = get_logger(__name__)


class BuildOutcome(str, Enum):
    """Outcome of a build request.

    Each outcome maps to a distinct code path in build_or_wait_async:
    - BUILT: This caller performed the build (first arrival for key).
    - COALESCED: This caller waited on an existing in-flight build.
    - TIMED_OUT: Wait exceeded timeout; caller receives no data.
    - FAILED: Build raised an exception; error propagated to all waiters.
    - STALE_REJECTED: In-flight build was invalidated; new build started.
    """

    BUILT = "built"
    COALESCED = "coalesced"
    TIMED_OUT = "timed_out"
    FAILED = "failed"
    STALE_REJECTED = "stale_rejected"


CoalescingKey = tuple[str, str]  # (project_gid, entity_type)


def make_coalescing_key(project_gid: str, entity_type: str) -> CoalescingKey:
    """Create a coalescing key for build coordination.

    Args:
        project_gid: Asana project GID (e.g., "1234567890").
        entity_type: Entity type string (e.g., "unit", "offer", "business").

    Returns:
        Tuple suitable as dict key.
    """
    return (project_gid, entity_type)


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Result of a coordinated build.

    Immutable value object shared across all coalesced waiters via
    asyncio.Future. The frozen constraint ensures result integrity
    when multiple coroutines read it concurrently.

    Attributes:
        outcome: How this caller's request was resolved.
        dataframe: The built DataFrame, or None on timeout/failure.
        watermark: Data freshness watermark, or None on timeout/failure.
        build_duration_ms: Wall-clock build time in milliseconds.
        waiter_count: Number of callers that coalesced on this build.
        error: Exception from build_fn, set only when outcome is FAILED.
    """

    outcome: BuildOutcome
    dataframe: pl.DataFrame | None = None
    watermark: datetime | None = None
    build_duration_ms: float = 0.0
    waiter_count: int = 0
    error: Exception | None = None


@dataclass
class _InFlightBuild:
    """Internal state for a build in progress.

    Not exported; used only by BuildCoordinator to track active builds.

    Attributes:
        future: Shared future that all coalesced waiters await.
        started_at: When the build was initiated (for duration tracking).
        waiter_count: Number of additional callers waiting on this build.
        invalidated: Set True by mark_invalidated(); causes new arrivals
            to start fresh builds instead of coalescing.
    """

    future: asyncio.Future[BuildResult]
    started_at: datetime
    waiter_count: int = 0
    invalidated: bool = False


@dataclass
class BuildCoordinator:
    """Coordinates DataFrame builds to prevent duplicate concurrent work.

    Single entry point for all build requests. Uses asyncio.Future
    (not Event) for result sharing: the builder sets the Future result,
    and all waiters receive the same BuildResult object (ADR-BC-001).

    Deadlock prevention (see TDD Section 10):
    - _lock and _build_semaphore are never held simultaneously.
    - _lock is never held during build_fn execution or future awaits.
    - mark_invalidated uses no locks (boolean flag set only).

    Attributes:
        default_timeout_seconds: Default maximum wait for coalesced builds.
        max_concurrent_builds: Maximum simultaneous builds across all keys.
    """

    default_timeout_seconds: float = 60.0
    max_concurrent_builds: int = 4

    # Internal state -- not exposed via init
    _in_flight: dict[CoalescingKey, _InFlightBuild] = field(
        default_factory=dict, init=False
    )
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _build_semaphore: asyncio.Semaphore | None = field(default=None, init=False)
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize semaphore and statistics counters."""
        self._build_semaphore = asyncio.Semaphore(self.max_concurrent_builds)
        self._stats = {
            "builds_started": 0,
            "builds_coalesced": 0,
            "builds_succeeded": 0,
            "builds_failed": 0,
            "builds_timed_out": 0,
            "builds_stale_rejected": 0,
        }

    async def build_or_wait_async(
        self,
        key: CoalescingKey,
        build_fn: Callable[[], Awaitable[tuple[Any, datetime]]],
        *,
        timeout_seconds: float | None = None,
        caller: str = "unknown",
    ) -> BuildResult:
        """Request a build, coalescing with any in-flight build for the same key.

        If no build is in-flight for this key, starts one using build_fn.
        If a build is already in-flight AND not staleness-rejected, waits
        for it to complete and returns the same result.

        Lock ordering (deadlock prevention):
        1. Acquire _lock for dict check/mutation.
        2. Release _lock.
        3. Either await future (wait path) or acquire _build_semaphore (build path).
        4. _lock is never held during build_fn or future await.

        Args:
            key: (project_gid, entity_type) tuple.
            build_fn: Async callable that performs the build.
                Must return (DataFrame, watermark) tuple.
            timeout_seconds: Maximum wait time. None uses default_timeout_seconds.
            caller: Identifier for logging (e.g., "decorator", "warmer").

        Returns:
            BuildResult with outcome, DataFrame, and metadata.
        """
        timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self.default_timeout_seconds
        )
        future: asyncio.Future[BuildResult] | None = None

        async with self._lock:
            if key in self._in_flight:
                existing = self._in_flight[key]
                if not existing.invalidated:
                    # Coalesce: wait on existing build
                    existing.waiter_count += 1
                    self._stats["builds_coalesced"] += 1
                    future = existing.future

                    logger.debug(
                        "build_coordinator_coalesced",
                        extra={
                            "project_gid": key[0],
                            "entity_type": key[1],
                            "caller": caller,
                            "waiter_count": existing.waiter_count,
                        },
                    )
                else:
                    # Existing build is stale -- start a new build instead.
                    self._stats["builds_stale_rejected"] += 1
                    logger.info(
                        "build_coordinator_stale_rejected",
                        extra={
                            "project_gid": key[0],
                            "entity_type": key[1],
                            "caller": caller,
                        },
                    )

            if future is None:
                # Start new build: create future and register in-flight
                loop = asyncio.get_running_loop()
                new_future = loop.create_future()
                self._in_flight[key] = _InFlightBuild(
                    future=new_future,
                    started_at=datetime.now(UTC),
                )
                self._stats["builds_started"] += 1

                logger.info(
                    "build_coordinator_started",
                    extra={
                        "project_gid": key[0],
                        "entity_type": key[1],
                        "caller": caller,
                    },
                )

        # --- _lock is released here ---

        if future is not None:
            return await self._wait_for_build(key, future, timeout, caller)

        return await self._execute_build(key, build_fn, caller)

    async def _wait_for_build(
        self,
        key: CoalescingKey,
        future: asyncio.Future[BuildResult],
        timeout: float,
        caller: str,
    ) -> BuildResult:
        """Wait path: await an existing in-flight build's future.

        Uses asyncio.shield to prevent cancellation of the shared future
        if this waiter times out or is cancelled.

        Args:
            key: Coalescing key for stats/logging.
            future: Shared future from the in-flight build.
            timeout: Maximum seconds to wait.
            caller: Caller identifier for logging.

        Returns:
            BuildResult with COALESCED or TIMED_OUT outcome.
        """
        try:
            result = await asyncio.wait_for(
                asyncio.shield(future),
                timeout=timeout,
            )

            # Return a COALESCED copy of the result so callers can
            # distinguish whether they performed the build or waited.
            if result.outcome == BuildOutcome.FAILED:
                # Propagate failure to all waiters
                return result

            return BuildResult(
                outcome=BuildOutcome.COALESCED,
                dataframe=result.dataframe,
                watermark=result.watermark,
                build_duration_ms=result.build_duration_ms,
                waiter_count=result.waiter_count,
            )

        except TimeoutError:
            self._stats["builds_timed_out"] += 1
            async with self._lock:
                if key in self._in_flight:
                    self._in_flight[key].waiter_count -= 1

            logger.warning(
                "build_coordinator_timeout",
                extra={
                    "project_gid": key[0],
                    "entity_type": key[1],
                    "caller": caller,
                    "timeout_seconds": timeout,
                },
            )

            return BuildResult(outcome=BuildOutcome.TIMED_OUT)

    async def _execute_build(
        self,
        key: CoalescingKey,
        build_fn: Callable[[], Awaitable[tuple[Any, datetime]]],
        caller: str,
    ) -> BuildResult:
        """Build path: execute build_fn and resolve the shared future.

        Acquires _build_semaphore for global concurrency control.
        On completion (success or failure), sets the future result so
        all coalesced waiters receive the outcome.

        Args:
            key: Coalescing key.
            build_fn: Async callable returning (DataFrame, watermark).
            caller: Caller identifier for logging.

        Returns:
            BuildResult with BUILT or FAILED outcome.
        """
        assert self._build_semaphore is not None  # Set in __post_init__
        start = time.perf_counter()

        try:
            async with self._build_semaphore:
                df, watermark = await build_fn()

            duration_ms = (time.perf_counter() - start) * 1000

            async with self._lock:
                result = self._resolve_success(key, df, watermark, duration_ms)

            self._stats["builds_succeeded"] += 1

            logger.info(
                "build_coordinator_completed",
                extra={
                    "project_gid": key[0],
                    "entity_type": key[1],
                    "outcome": result.outcome.value,
                    "build_duration_ms": round(result.build_duration_ms, 1),
                    "waiter_count": result.waiter_count,
                    "caller": caller,
                },
            )

            return result

        except CACHE_TRANSIENT_ERRORS as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            result = BuildResult(
                outcome=BuildOutcome.FAILED,
                build_duration_ms=duration_ms,
                error=exc,
            )

            async with self._lock:
                if key in self._in_flight:
                    in_flight = self._in_flight[key]
                    if not in_flight.future.done():
                        in_flight.future.set_result(result)
                    del self._in_flight[key]

            self._stats["builds_failed"] += 1

            logger.error(
                "build_coordinator_failed",
                extra={
                    "project_gid": key[0],
                    "entity_type": key[1],
                    "build_duration_ms": round(duration_ms, 1),
                    "caller": caller,
                    "error": str(exc),
                },
            )

            return result

    def _resolve_success(
        self,
        key: CoalescingKey,
        df: Any,
        watermark: datetime,
        duration_ms: float,
    ) -> BuildResult:
        """Resolve a successful build under _lock.

        Sets the future result and removes the in-flight entry.
        Must be called while holding _lock.

        Args:
            key: Coalescing key.
            df: Built DataFrame.
            watermark: Build watermark.
            duration_ms: Build duration in milliseconds.

        Returns:
            BuildResult with BUILT outcome.
        """
        waiter_count = 0

        if key in self._in_flight:
            in_flight = self._in_flight[key]
            waiter_count = in_flight.waiter_count

            result = BuildResult(
                outcome=BuildOutcome.BUILT,
                dataframe=df,
                watermark=watermark,
                build_duration_ms=duration_ms,
                waiter_count=waiter_count,
            )

            if not in_flight.future.done():
                in_flight.future.set_result(result)
            del self._in_flight[key]
        else:
            result = BuildResult(
                outcome=BuildOutcome.BUILT,
                dataframe=df,
                watermark=watermark,
                build_duration_ms=duration_ms,
                waiter_count=waiter_count,
            )

        return result

    def mark_invalidated(
        self,
        project_gid: str,
        entity_type: str | None = None,
    ) -> int:
        """Mark in-flight builds as invalidated due to mutation.

        Called by MutationInvalidator when a mutation affects a project.
        Does NOT cancel the build -- it continues to completion so existing
        waiters are not orphaned. New arrivals for the same key will start
        a fresh build instead of coalescing (ADR-BC-003).

        No async lock needed -- _in_flight reads are safe under GIL for
        the boolean flag set. The _lock is only needed for structural
        mutations (add/remove keys).

        Args:
            project_gid: Project GID that was mutated.
            entity_type: Optional specific entity type. If None, marks
                all entity types for the project.

        Returns:
            Number of in-flight builds marked invalidated.
        """
        count = 0
        for key, build in self._in_flight.items():
            if key[0] == project_gid:
                if entity_type is None or key[1] == entity_type:
                    build.invalidated = True
                    count += 1

        if count > 0:
            logger.info(
                "in_flight_builds_invalidated",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "count": count,
                },
            )

        return count

    def is_building(self, key: CoalescingKey) -> bool:
        """Check if a build is in-flight for this key.

        Args:
            key: (project_gid, entity_type) tuple.

        Returns:
            True if a build is currently in progress for this key.
        """
        return key in self._in_flight

    def get_stats(self) -> dict[str, int]:
        """Get coordinator statistics.

        Returns:
            Copy of statistics dictionary with all counters.
        """
        return dict(self._stats)

    async def force_cleanup(self, key: CoalescingKey) -> None:
        """Force cleanup of in-flight state for a key.

        Intended for operational recovery when a build hangs forever.
        Cancels the future (existing waiters get CancelledError) and
        removes the in-flight entry.

        Args:
            key: Coalescing key to clean up.
        """
        async with self._lock:
            if key in self._in_flight:
                in_flight = self._in_flight[key]
                if not in_flight.future.done():
                    in_flight.future.cancel()
                del self._in_flight[key]

                logger.warning(
                    "build_coordinator_force_cleanup",
                    extra={
                        "project_gid": key[0],
                        "entity_type": key[1],
                        "waiter_count": in_flight.waiter_count,
                    },
                )
