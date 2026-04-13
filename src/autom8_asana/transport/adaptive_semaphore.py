"""AIMD adaptive concurrency semaphore for Asana API rate limiting.

Per TDD-GAP-04/ADR-GAP04-001: Local AIMD implementation replacing fixed
asyncio.Semaphore instances in AsanaHttpClient. Uses Additive Increase /
Multiplicative Decrease (TCP congestion control) to dynamically adjust
concurrency in response to 429 rate limit signals.

Two-layer design:
  - TokenBucketRateLimiter controls request RATE (tokens/second)
  - AsyncAdaptiveSemaphore controls CONCURRENCY (in-flight count)

These are complementary, not competing.

Architecture:
  - AIMDConfig: Immutable configuration dataclass with validation
  - Slot: Context manager yielded by acquire(), carries epoch for feedback
  - NoOpSlot: No-op slot for FixedSemaphoreAdapter (AIMD disabled)
  - FixedSemaphoreAdapter: Wraps asyncio.Semaphore with acquire()->Slot interface
  - AsyncAdaptiveSemaphore: Core AIMD primitive with epoch coalescing
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from autom8_asana.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8y_log import LoggerProtocol

__all__ = [
    "AIMDConfig",
    "AsyncAdaptiveSemaphore",
    "FixedSemaphoreAdapter",
    "NoOpSlot",
    "Slot",
]


@dataclass(frozen=True)
class AIMDConfig:
    """Configuration for AIMD adaptive concurrency control.

    All parameters have sensible defaults derived from TCP congestion
    control principles and Asana API behavior observations.

    Attributes:
        ceiling: Maximum concurrency (from ConcurrencyConfig.read_limit or write_limit).
        floor: Minimum concurrency. Must be >= 1 to prevent deadlock.
        multiplicative_decrease: Factor to multiply window by on 429 (e.g., 0.5 = halve).
        additive_increase: Amount to add to window on success (e.g., 1.0).
        grace_period_seconds: Suppress increases after a decrease for this duration.
        increase_interval_seconds: Minimum time between successive increases (FR-007).
        cooldown_trigger: Consecutive 429s before cooldown warning (FR-008 stub).
        cooldown_duration_seconds: Cooldown duration placeholder (unused in v1).
    """

    ceiling: int
    floor: int = 1
    multiplicative_decrease: float = 0.5
    additive_increase: float = 1.0
    grace_period_seconds: float = 5.0
    increase_interval_seconds: float = 2.0
    cooldown_trigger: int = 5
    cooldown_duration_seconds: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.floor < 1:
            raise ConfigurationError("floor must be >= 1 to prevent deadlock")
        if self.ceiling < self.floor:
            raise ConfigurationError("ceiling must be >= floor")
        if not 0.0 < self.multiplicative_decrease < 1.0:
            raise ConfigurationError("multiplicative_decrease must be in (0, 1)")
        if self.additive_increase <= 0:
            raise ConfigurationError("additive_increase must be positive")
        if self.grace_period_seconds < 0:
            raise ConfigurationError("grace_period_seconds must be non-negative")
        if self.increase_interval_seconds < 0:
            raise ConfigurationError("increase_interval_seconds must be non-negative")


class Slot:
    """Concurrency slot yielded by AsyncAdaptiveSemaphore.acquire().

    Carries the epoch at acquire time for AIMD feedback coalescing.
    The caller signals request outcome via reject() or succeed().
    The slot releases on context exit regardless of feedback status.

    Lifecycle:
        acquire() -> Slot(status="pending")
          slot.reject()   -> status="rejected",  triggers multiplicative decrease
          slot.succeed()  -> status="succeeded", triggers additive increase
        __aexit__()       -> releases slot (decrements in_flight, notifies waiters)

    If neither reject() nor succeed() is called, the slot releases silently
    without AIMD feedback. This is safe -- no window adjustment occurs.
    """

    __slots__ = ("_semaphore", "_epoch", "_status")

    def __init__(
        self,
        semaphore: AsyncAdaptiveSemaphore,
        epoch: int,
    ) -> None:
        self._semaphore = semaphore
        self._epoch = epoch
        self._status: Literal["pending", "rejected", "succeeded", "released"] = "pending"

    async def __aenter__(self) -> Slot:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self._status = "released"
        await self._semaphore._release()

    def reject(self) -> None:
        """Signal 429 received. Triggers multiplicative decrease if epoch is current.

        Synchronous -- state mutation is safe without await in single-threaded
        asyncio because no await points exist in _handle_reject. The _release()
        in __aexit__ handles all Condition notifications.
        """
        if self._status != "pending":
            return  # Idempotent
        self._status = "rejected"
        self._semaphore._handle_reject(self._epoch)

    def succeed(self) -> None:
        """Signal success. Triggers additive increase if epoch is current.

        Synchronous -- same rationale as reject().
        """
        if self._status != "pending":
            return  # Idempotent
        self._status = "succeeded"
        self._semaphore._handle_success(self._epoch)


class NoOpSlot:
    """No-op slot for FixedSemaphoreAdapter when AIMD is disabled.

    reject() and succeed() are no-ops. Release delegates to the
    underlying asyncio.Semaphore.
    """

    __slots__ = ("_semaphore",)

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        self._semaphore = semaphore

    async def __aenter__(self) -> NoOpSlot:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self._semaphore.release()

    def reject(self) -> None:
        """No-op: AIMD is disabled."""

    def succeed(self) -> None:
        """No-op: AIMD is disabled."""


class FixedSemaphoreAdapter:
    """Adapts asyncio.Semaphore to the AsyncAdaptiveSemaphore interface.

    Used when aimd_enabled=False. Provides the same acquire()->Slot pattern
    so AsanaHttpClient._request() does not need conditional code paths.
    """

    def __init__(self, limit: int) -> None:
        self._semaphore = asyncio.Semaphore(limit)
        self._limit = limit

    async def acquire(self) -> NoOpSlot:
        """Acquire semaphore and return a NoOpSlot."""
        await self._semaphore.acquire()
        return NoOpSlot(self._semaphore)

    @property
    def ceiling(self) -> int:
        """Maximum concurrency (fixed)."""
        return self._limit

    @property
    def current_limit(self) -> int:
        """Current effective concurrency limit (fixed, same as ceiling)."""
        return self._limit

    @property
    def in_flight(self) -> int:
        """Approximate number of in-flight requests."""
        # asyncio.Semaphore._value tracks available permits
        return self._limit - self._semaphore._value

    def get_stats(self) -> dict[str, Any]:
        """Return stats matching AsyncAdaptiveSemaphore interface."""
        return {
            "name": "fixed",
            "current_limit": self._limit,
            "ceiling": self._limit,
            "floor": self._limit,
            "in_flight": self.in_flight,
            "epoch": 0,
            "decrease_count": 0,
            "increase_count": 0,
            "consecutive_rejects": 0,
            "grace_period_active": False,
            "window_raw": float(self._limit),
        }


class AsyncAdaptiveSemaphore:
    """AIMD adaptive concurrency semaphore.

    Replaces asyncio.Semaphore with a dynamically-sized concurrency controller.
    On 429 (reject), halves the concurrency window. On success, increments by 1.
    Epoch coalescing prevents N simultaneous 429s from causing N halvings.

    Internal state is protected by asyncio.Condition for coroutine-level mutual
    exclusion. All operations are O(1).

    Args:
        config: AIMD configuration parameters.
        name: Identifier for log disambiguation ("read" or "write").
        logger: Optional structured logger.
        clock: Injectable monotonic clock (default: time.monotonic).
    """

    def __init__(
        self,
        config: AIMDConfig,
        *,
        name: str = "",
        logger: LoggerProtocol | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._config = config
        self._name = name
        self._logger = logger
        self._clock = clock or time.monotonic

        # AIMD state
        self._window: float = float(config.ceiling)
        self._in_flight: int = 0
        self._epoch: int = 0

        # Timing state
        self._last_decrease_time: float = 0.0
        self._last_increase_time: float = 0.0

        # Counters
        self._decrease_count: int = 0
        self._increase_count: int = 0
        self._consecutive_rejects: int = 0

        # Async primitive
        self._condition = asyncio.Condition()

    async def acquire(self) -> Slot:
        """Acquire a concurrency slot, blocking if at the AIMD limit.

        Returns a Slot context manager. The caller MUST use it as:
            async with await semaphore.acquire() as slot:
                response = await make_request()
                if response.status_code == 429:
                    slot.reject()
                else:
                    slot.succeed()

        If neither reject() nor succeed() is called before exit,
        the slot releases without AIMD feedback (silent release).
        """
        async with self._condition:
            while self._in_flight >= int(self._window):
                await self._condition.wait()
            self._in_flight += 1
            return Slot(semaphore=self, epoch=self._epoch)

    async def _release(self) -> None:
        """Release a slot (called by Slot.__aexit__).

        Decrements in_flight and notifies ONE waiter to prevent thundering herd.
        """
        async with self._condition:
            self._in_flight -= 1
            self._condition.notify(1)

    def _handle_reject(self, slot_epoch: int) -> None:
        """Handle 429 rejection signal. Synchronous -- no await points.

        Performs multiplicative decrease if the slot's epoch is current.
        Stale epochs (from before the most recent decrease) are ignored,
        ensuring exactly one halving per burst of 429s.

        Args:
            slot_epoch: The epoch at which the slot was acquired.
        """
        if slot_epoch < self._epoch:
            return  # Stale epoch -- already handled

        old_window = self._window
        self._window = max(
            self._window * self._config.multiplicative_decrease,
            float(self._config.floor),
        )
        self._epoch += 1
        self._last_decrease_time = self._clock()
        self._decrease_count += 1
        self._consecutive_rejects += 1

        # Cooldown stub check (FR-008)
        if self._consecutive_rejects >= self._config.cooldown_trigger and self._logger:
            self._logger.warning(
                "aimd_cooldown_threshold_reached",
                extra={
                    "name": self._name,
                    "consecutive_rejects": self._consecutive_rejects,
                    "cooldown_trigger": self._config.cooldown_trigger,
                    "note": "cooldown_not_active_in_v1",
                },
            )

        if self._logger:
            at_floor = self._window <= float(self._config.floor)
            log_fn = self._logger.warning if at_floor else self._logger.info
            log_fn(
                "aimd_decrease",
                extra={
                    "name": self._name,
                    "before": old_window,
                    "after": self._window,
                    "epoch": self._epoch,
                    "trigger": "429",
                },
            )
            if at_floor:
                self._logger.warning(
                    "aimd_at_minimum",
                    extra={
                        "name": self._name,
                        "floor": self._config.floor,
                    },
                )

    def _handle_success(self, slot_epoch: int) -> None:
        """Handle success signal. Synchronous -- no await points.

        Performs additive increase if the slot's epoch is current,
        the grace period has expired, and the increase interval has elapsed.

        Args:
            slot_epoch: The epoch at which the slot was acquired.
        """
        if slot_epoch < self._epoch:
            return  # Stale epoch

        # Reset consecutive rejects on success
        self._consecutive_rejects = 0

        now = self._clock()

        # Grace period check (FR-002)
        if now - self._last_decrease_time < self._config.grace_period_seconds:
            if self._logger:
                remaining = self._config.grace_period_seconds - (now - self._last_decrease_time)
                self._logger.debug(
                    "aimd_grace_period_suppressed",
                    extra={
                        "name": self._name,
                        "remaining_seconds": remaining,
                    },
                )
            return

        # Increase throttle check (FR-007)
        if now - self._last_increase_time < self._config.increase_interval_seconds:
            return

        # Already at ceiling
        if self._window >= float(self._config.ceiling):
            return

        old_window = self._window
        self._window = min(
            self._window + self._config.additive_increase,
            float(self._config.ceiling),
        )
        self._last_increase_time = now
        self._increase_count += 1

        if self._logger:
            self._logger.debug(
                "aimd_increase",
                extra={
                    "name": self._name,
                    "before": old_window,
                    "after": self._window,
                    "epoch": self._epoch,
                },
            )

    @property
    def current_limit(self) -> int:
        """Current effective concurrency limit (integer floor of window)."""
        return int(self._window)

    @property
    def ceiling(self) -> int:
        """Maximum concurrency (from config)."""
        return self._config.ceiling

    @property
    def in_flight(self) -> int:
        """Number of currently-held slots."""
        return self._in_flight

    def get_stats(self) -> dict[str, Any]:
        """Return current AIMD state for programmatic access.

        Does NOT acquire the lock -- provides an approximate snapshot.
        This matches TokenBucketRateLimiter.available_tokens which is also unlocked.
        """
        now = self._clock()
        grace_active = (
            now - self._last_decrease_time < self._config.grace_period_seconds
            if self._last_decrease_time > 0
            else False
        )
        return {
            "name": self._name,
            "current_limit": int(self._window),
            "ceiling": self._config.ceiling,
            "floor": self._config.floor,
            "in_flight": self._in_flight,
            "epoch": self._epoch,
            "decrease_count": self._decrease_count,
            "increase_count": self._increase_count,
            "consecutive_rejects": self._consecutive_rejects,
            "grace_period_active": grace_active,
            "window_raw": self._window,
        }
