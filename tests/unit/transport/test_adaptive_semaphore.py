"""Unit tests for AsyncAdaptiveSemaphore AIMD primitive.

Per TDD-GAP-04/Section 8.1: Tests for the adaptive concurrency semaphore
including epoch coalescing, grace period, increase throttle, cooldown stub,
stats API, and structured logging.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from autom8_asana.errors import ConfigurationError
from autom8_asana.transport.adaptive_semaphore import (
    AIMDConfig,
    AsyncAdaptiveSemaphore,
    FixedSemaphoreAdapter,
    NoOpSlot,
    Slot,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class FakeClock:
    """Controllable clock for deterministic testing of time-dependent behavior."""

    def __init__(self, start: float = 0.0) -> None:
        self._time = start

    def __call__(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


def _make_semaphore(
    ceiling: int = 50,
    floor: int = 1,
    multiplicative_decrease: float = 0.5,
    additive_increase: float = 1.0,
    grace_period_seconds: float = 5.0,
    increase_interval_seconds: float = 2.0,
    cooldown_trigger: int = 5,
    clock: FakeClock | None = None,
    logger: MagicMock | None = None,
    name: str = "test",
) -> tuple[AsyncAdaptiveSemaphore, FakeClock]:
    """Factory for creating test semaphores with sensible defaults."""
    if clock is None:
        clock = FakeClock(start=100.0)  # Start at 100 so grace period checks work
    config = AIMDConfig(
        ceiling=ceiling,
        floor=floor,
        multiplicative_decrease=multiplicative_decrease,
        additive_increase=additive_increase,
        grace_period_seconds=grace_period_seconds,
        increase_interval_seconds=increase_interval_seconds,
        cooldown_trigger=cooldown_trigger,
    )
    sem = AsyncAdaptiveSemaphore(config=config, name=name, logger=logger, clock=clock)
    return sem, clock


# ---------------------------------------------------------------------------
# SC-001: Acquire and reject behavior
# ---------------------------------------------------------------------------


class TestAcquireAndReject:
    """Tests for acquire, release, and reject (multiplicative decrease)."""

    @pytest.mark.asyncio
    async def test_acquire_below_limit_does_not_block(self):
        """Acquire when in_flight < window returns immediately."""
        sem, _ = _make_semaphore(ceiling=10)
        slot = await sem.acquire()
        assert isinstance(slot, Slot)
        assert sem.in_flight == 1
        await slot.__aexit__(None, None, None)
        assert sem.in_flight == 0

    @pytest.mark.asyncio
    async def test_acquire_at_limit_blocks(self):
        """Acquire when in_flight == window blocks until release."""
        sem, _ = _make_semaphore(ceiling=2)
        slot1 = await sem.acquire()
        slot2 = await sem.acquire()
        assert sem.in_flight == 2

        # Third acquire should block
        acquired = asyncio.Event()

        async def acquire_third():
            slot3 = await sem.acquire()
            acquired.set()
            return slot3

        task = asyncio.create_task(acquire_third())
        # Give the event loop a chance to schedule the task
        await asyncio.sleep(0.01)
        assert not acquired.is_set()

        # Release one slot -- should unblock
        await slot1.__aexit__(None, None, None)
        await asyncio.sleep(0.01)
        assert acquired.is_set()

        # Cleanup
        slot3 = task.result()
        await slot2.__aexit__(None, None, None)
        await slot3.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_reject_halves_window(self):
        """After reject(), window = old * 0.5."""
        sem, _ = _make_semaphore(ceiling=50)
        assert sem.current_limit == 50

        async with await sem.acquire() as slot:
            slot.reject()

        assert sem.current_limit == 25

    @pytest.mark.asyncio
    async def test_reject_at_floor_stays_at_floor(self):
        """Window never drops below floor (SC-004)."""
        sem, _ = _make_semaphore(ceiling=4, floor=2)

        # First reject: 4 * 0.5 = 2 (at floor)
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 2

        # Second reject: should stay at floor
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 2

    @pytest.mark.asyncio
    async def test_reject_at_floor_logs_warning(self):
        """aimd_at_minimum event emitted when window hits floor (SC-005)."""
        mock_logger = MagicMock()
        sem, _ = _make_semaphore(ceiling=2, floor=1, logger=mock_logger)

        async with await sem.acquire() as slot:
            slot.reject()

        # Should have called warning for aimd_at_minimum
        warning_calls = [
            c for c in mock_logger.warning.call_args_list if c[0][0] == "aimd_at_minimum"
        ]
        assert len(warning_calls) == 1
        assert warning_calls[0].kwargs["extra"]["floor"] == 1

    @pytest.mark.asyncio
    async def test_epoch_coalescing_single_halving(self):
        """N simultaneous rejects cause exactly 1 halving (SC-001)."""
        sem, _ = _make_semaphore(ceiling=50)

        # Acquire multiple slots (all get epoch=0)
        slots = []
        for _ in range(5):
            slots.append(await sem.acquire())

        # All reject -- only the first should trigger halving
        for s in slots:
            s.reject()

        # Window should be 25 (one halving), not 50 * 0.5^5
        assert sem.current_limit == 25
        assert sem._epoch == 1

        # Cleanup
        for s in slots:
            await s.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_stale_epoch_success_ignored(self):
        """Success from pre-decrease epoch does not increase window (SC-001)."""
        sem, clock = _make_semaphore(ceiling=50, grace_period_seconds=0.0)
        clock.advance(10.0)  # Past any default grace period

        # Acquire slot at epoch=0
        slot_old = await sem.acquire()
        slot_trigger = await sem.acquire()

        # Trigger decrease with one slot
        slot_trigger.reject()
        assert sem.current_limit == 25
        assert sem._epoch == 1

        # Old slot succeeds -- should be ignored (stale epoch)
        slot_old.succeed()
        assert sem.current_limit == 25  # Unchanged

        await slot_old.__aexit__(None, None, None)
        await slot_trigger.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# SC-002: Success and recovery behavior
# ---------------------------------------------------------------------------


class TestSuccessAndRecovery:
    """Tests for succeed (additive increase) and full recovery."""

    @pytest.mark.asyncio
    async def test_succeed_increases_window(self):
        """After succeed(), window = old + 1.0 (SC-002)."""
        sem, clock = _make_semaphore(
            ceiling=50, grace_period_seconds=0.0, increase_interval_seconds=0.0
        )
        clock.advance(10.0)

        # Decrease first so there is room to increase
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 25

        clock.advance(1.0)

        # Now succeed
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 26

    @pytest.mark.asyncio
    async def test_succeed_at_ceiling_stays_at_ceiling(self):
        """Window never exceeds ceiling (SC-002)."""
        sem, clock = _make_semaphore(
            ceiling=50, grace_period_seconds=0.0, increase_interval_seconds=0.0
        )
        clock.advance(10.0)
        assert sem.current_limit == 50

        # Succeed should not push above ceiling
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 50

    @pytest.mark.asyncio
    async def test_grace_period_suppresses_increase(self):
        """Success during grace period does not increase window (SC-002)."""
        sem, clock = _make_semaphore(
            ceiling=50, grace_period_seconds=5.0, increase_interval_seconds=0.0
        )
        clock.advance(10.0)

        # Decrease
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 25

        # Advance only 2 seconds (within 5s grace period)
        clock.advance(2.0)

        # Succeed -- should be suppressed
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 25  # Unchanged

    @pytest.mark.asyncio
    async def test_grace_period_expires_allows_increase(self):
        """Success after grace period increases window (SC-002)."""
        sem, clock = _make_semaphore(
            ceiling=50, grace_period_seconds=5.0, increase_interval_seconds=0.0
        )
        clock.advance(10.0)

        # Decrease
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 25

        # Advance past grace period
        clock.advance(6.0)

        # Succeed -- should increase
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 26

    @pytest.mark.asyncio
    async def test_increase_throttle_respected(self):
        """Successive successes within interval only increase once (SC-002, FR-007)."""
        sem, clock = _make_semaphore(
            ceiling=50,
            grace_period_seconds=0.0,
            increase_interval_seconds=2.0,
        )
        clock.advance(10.0)

        # Decrease to create room
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 25

        clock.advance(1.0)

        # First success -- should increase
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 26

        # Immediately another success (0 seconds later) -- throttled
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 26  # No change

        # Advance past interval
        clock.advance(3.0)

        # Now should increase
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 27

    @pytest.mark.asyncio
    async def test_full_recovery_to_ceiling(self):
        """After decrease, N successes bring window back to ceiling (SC-002)."""
        sem, clock = _make_semaphore(
            ceiling=10,
            grace_period_seconds=0.0,
            increase_interval_seconds=0.0,
        )
        clock.advance(10.0)

        # Decrease: 10 -> 5
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 5

        clock.advance(1.0)

        # 5 successes should bring back to 10
        for i in range(5):
            clock.advance(0.1)
            async with await sem.acquire() as slot:
                slot.succeed()

        assert sem.current_limit == 10

        # Extra succeed should not exceed ceiling
        clock.advance(0.1)
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 10


# ---------------------------------------------------------------------------
# NFR-002, NFR-003: Safety tests
# ---------------------------------------------------------------------------


class TestSafety:
    """Tests for exception safety and concurrent correctness."""

    @pytest.mark.asyncio
    async def test_concurrent_acquire_correctness(self):
        """Multiple concurrent coroutines maintain consistent state (NFR-003)."""
        sem, clock = _make_semaphore(
            ceiling=5, grace_period_seconds=0.0, increase_interval_seconds=0.0
        )
        clock.advance(10.0)
        results = []

        async def worker(worker_id: int):
            async with await sem.acquire() as slot:
                results.append(worker_id)
                await asyncio.sleep(0.01)
                slot.succeed()

        # Launch 10 workers with ceiling=5
        tasks = [asyncio.create_task(worker(i)) for i in range(10)]
        await asyncio.gather(*tasks)

        # All 10 should complete
        assert len(results) == 10
        # in_flight should be 0
        assert sem.in_flight == 0

    @pytest.mark.asyncio
    async def test_slot_releases_on_exception(self):
        """Slot releases even when request raises exception (NFR-002)."""
        sem, _ = _make_semaphore(ceiling=5)

        with pytest.raises(RuntimeError):
            async with await sem.acquire() as slot:
                raise RuntimeError("simulated request failure")

        # Slot should have been released
        assert sem.in_flight == 0


# ---------------------------------------------------------------------------
# Slot idempotency and silent release
# ---------------------------------------------------------------------------


class TestSlotBehavior:
    """Tests for Slot edge cases."""

    @pytest.mark.asyncio
    async def test_slot_reject_idempotent(self):
        """Calling reject() twice is safe."""
        sem, _ = _make_semaphore(ceiling=50)

        async with await sem.acquire() as slot:
            slot.reject()
            slot.reject()  # Second call should be no-op

        # Only one halving
        assert sem.current_limit == 25

    @pytest.mark.asyncio
    async def test_slot_succeed_idempotent(self):
        """Calling succeed() twice is safe."""
        sem, clock = _make_semaphore(
            ceiling=50, grace_period_seconds=0.0, increase_interval_seconds=0.0
        )
        clock.advance(10.0)

        # Decrease first
        async with await sem.acquire() as slot:
            slot.reject()

        clock.advance(1.0)

        async with await sem.acquire() as slot:
            slot.succeed()
            slot.succeed()  # Second call should be no-op

        # Only one increase
        assert sem.current_limit == 26

    @pytest.mark.asyncio
    async def test_slot_silent_release(self):
        """Not calling reject/succeed releases without feedback."""
        sem, _ = _make_semaphore(ceiling=50)

        async with await sem.acquire() as slot:
            pass  # No feedback

        # Window unchanged
        assert sem.current_limit == 50
        assert sem.in_flight == 0


# ---------------------------------------------------------------------------
# FR-006: Stats API
# ---------------------------------------------------------------------------


class TestStatsAPI:
    """Tests for the get_stats() introspection API."""

    @pytest.mark.asyncio
    async def test_stats_api(self):
        """get_stats() returns all documented fields (FR-006)."""
        sem, clock = _make_semaphore(ceiling=50, name="read")
        clock.advance(10.0)

        stats = sem.get_stats()
        assert stats["name"] == "read"
        assert stats["current_limit"] == 50
        assert stats["ceiling"] == 50
        assert stats["floor"] == 1
        assert stats["in_flight"] == 0
        assert stats["epoch"] == 0
        assert stats["decrease_count"] == 0
        assert stats["increase_count"] == 0
        assert stats["consecutive_rejects"] == 0
        assert stats["grace_period_active"] is False
        assert stats["window_raw"] == 50.0

        # After a decrease
        async with await sem.acquire() as slot:
            slot.reject()

        stats = sem.get_stats()
        assert stats["current_limit"] == 25
        assert stats["epoch"] == 1
        assert stats["decrease_count"] == 1
        assert stats["grace_period_active"] is True


# ---------------------------------------------------------------------------
# FR-008: Cooldown stub
# ---------------------------------------------------------------------------


class TestCooldownStub:
    """Tests for the cooldown counter and threshold warning."""

    @pytest.mark.asyncio
    async def test_cooldown_counter_increments(self):
        """Consecutive rejects increment counter (FR-008)."""
        sem, _ = _make_semaphore(ceiling=50, cooldown_trigger=10)

        # 3 consecutive rejects (each triggers new epoch)
        for _ in range(3):
            async with await sem.acquire() as slot:
                slot.reject()

        assert sem._consecutive_rejects == 3

    @pytest.mark.asyncio
    async def test_cooldown_counter_resets_on_success(self):
        """Success resets consecutive reject counter (FR-008)."""
        sem, clock = _make_semaphore(
            ceiling=50,
            grace_period_seconds=0.0,
            increase_interval_seconds=0.0,
            cooldown_trigger=10,
        )
        clock.advance(10.0)

        # Two rejects
        async with await sem.acquire() as slot:
            slot.reject()
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem._consecutive_rejects == 2

        clock.advance(1.0)

        # One success resets the counter
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem._consecutive_rejects == 0

    @pytest.mark.asyncio
    async def test_cooldown_threshold_logs_warning(self):
        """Warning emitted at threshold (FR-008)."""
        mock_logger = MagicMock()
        sem, _ = _make_semaphore(ceiling=1000, cooldown_trigger=3, logger=mock_logger)

        # 3 consecutive rejects should trigger cooldown warning
        for _ in range(3):
            async with await sem.acquire() as slot:
                slot.reject()

        cooldown_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "aimd_cooldown_threshold_reached"
        ]
        assert len(cooldown_calls) >= 1
        assert cooldown_calls[0].kwargs["extra"]["consecutive_rejects"] == 3


# ---------------------------------------------------------------------------
# SC-005: Structured logging
# ---------------------------------------------------------------------------


class TestStructuredLogging:
    """Tests for structured log events."""

    @pytest.mark.asyncio
    async def test_structured_log_decrease(self):
        """aimd_decrease event has correct fields (SC-005)."""
        mock_logger = MagicMock()
        sem, _ = _make_semaphore(ceiling=50, logger=mock_logger)

        async with await sem.acquire() as slot:
            slot.reject()

        # Find the aimd_decrease call
        decrease_calls = [c for c in mock_logger.info.call_args_list if c[0][0] == "aimd_decrease"]
        assert len(decrease_calls) == 1
        extra = decrease_calls[0].kwargs["extra"]
        assert extra["name"] == "test"
        assert extra["before"] == 50.0
        assert extra["after"] == 25.0
        assert extra["epoch"] == 1
        assert extra["trigger"] == "429"

    @pytest.mark.asyncio
    async def test_structured_log_increase(self):
        """aimd_increase event at DEBUG level (SC-005)."""
        mock_logger = MagicMock()
        sem, clock = _make_semaphore(
            ceiling=50,
            grace_period_seconds=0.0,
            increase_interval_seconds=0.0,
            logger=mock_logger,
        )
        clock.advance(10.0)

        # Decrease first
        async with await sem.acquire() as slot:
            slot.reject()

        clock.advance(1.0)

        # Succeed
        async with await sem.acquire() as slot:
            slot.succeed()

        increase_calls = [c for c in mock_logger.debug.call_args_list if c[0][0] == "aimd_increase"]
        assert len(increase_calls) == 1
        extra = increase_calls[0].kwargs["extra"]
        assert extra["name"] == "test"
        assert extra["before"] == 25.0
        assert extra["after"] == 26.0
        assert extra["epoch"] == 1


# ---------------------------------------------------------------------------
# NFR-005: Injectable clock
# ---------------------------------------------------------------------------


class TestInjectableClock:
    """Tests for injectable clock (NFR-005)."""

    @pytest.mark.asyncio
    async def test_injectable_clock(self):
        """Grace period and throttle use injected clock (NFR-005)."""
        clock = FakeClock(start=100.0)
        sem, _ = _make_semaphore(
            ceiling=50,
            grace_period_seconds=5.0,
            increase_interval_seconds=2.0,
            clock=clock,
        )

        # Decrease at t=100
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 25

        # At t=102 (within grace period), succeed should be suppressed
        clock.advance(2.0)
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 25

        # At t=106 (past grace period), succeed should work
        clock.advance(4.0)
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 26

        # At t=106.5 (within increase interval), succeed should be throttled
        clock.advance(0.5)
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 26

        # At t=109 (past increase interval), succeed should work
        clock.advance(2.5)
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 27


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


class TestConfigValidation:
    """Tests for AIMDConfig validation."""

    def test_config_validation_floor_zero(self):
        """floor < 1 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="floor must be >= 1"):
            AIMDConfig(ceiling=50, floor=0)

    def test_config_validation_ceiling_below_floor(self):
        """ceiling < floor raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="ceiling must be >= floor"):
            AIMDConfig(ceiling=1, floor=5)

    def test_config_validation_decrease_out_of_range(self):
        """multiplicative_decrease outside (0, 1) raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="multiplicative_decrease must be in"):
            AIMDConfig(ceiling=50, multiplicative_decrease=1.5)
        with pytest.raises(ConfigurationError, match="multiplicative_decrease must be in"):
            AIMDConfig(ceiling=50, multiplicative_decrease=0.0)

    def test_config_validation_increase_non_positive(self):
        """additive_increase <= 0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="additive_increase must be"):
            AIMDConfig(ceiling=50, additive_increase=0.0)

    def test_config_validation_grace_negative(self):
        """grace_period_seconds < 0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="grace_period_seconds"):
            AIMDConfig(ceiling=50, grace_period_seconds=-1.0)

    def test_config_validation_interval_negative(self):
        """increase_interval_seconds < 0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="increase_interval_seconds"):
            AIMDConfig(ceiling=50, increase_interval_seconds=-1.0)


# ---------------------------------------------------------------------------
# No-logger safety
# ---------------------------------------------------------------------------


class TestNoLogger:
    """Tests that all paths work without a logger."""

    @pytest.mark.asyncio
    async def test_no_logger_does_not_raise(self):
        """All paths work without a logger."""
        sem, clock = _make_semaphore(
            ceiling=50,
            grace_period_seconds=0.0,
            increase_interval_seconds=0.0,
            logger=None,
            cooldown_trigger=1,
        )
        clock.advance(10.0)

        # Reject (triggers decrease + cooldown warning path)
        async with await sem.acquire() as slot:
            slot.reject()
        assert sem.current_limit == 25

        clock.advance(1.0)

        # Succeed (triggers increase path)
        async with await sem.acquire() as slot:
            slot.succeed()
        assert sem.current_limit == 26

        # Silent release
        async with await sem.acquire() as slot:
            pass

        assert sem.in_flight == 0


# ---------------------------------------------------------------------------
# FixedSemaphoreAdapter tests
# ---------------------------------------------------------------------------


class TestFixedSemaphoreAdapter:
    """Tests for the AIMD-disabled adapter."""

    @pytest.mark.asyncio
    async def test_adapter_acquire_and_release(self):
        """Adapter provides acquire()->NoOpSlot pattern."""
        adapter = FixedSemaphoreAdapter(limit=5)
        assert adapter.ceiling == 5
        assert adapter.current_limit == 5

        async with await adapter.acquire() as slot:
            assert isinstance(slot, NoOpSlot)
            slot.reject()  # No-op
            slot.succeed()  # No-op

        # Stats API
        stats = adapter.get_stats()
        assert stats["ceiling"] == 5
        assert stats["current_limit"] == 5
        assert stats["decrease_count"] == 0

    @pytest.mark.asyncio
    async def test_adapter_concurrent_limit(self):
        """Adapter respects concurrency limit."""
        adapter = FixedSemaphoreAdapter(limit=2)

        slot1 = await adapter.acquire()
        await slot1.__aenter__()
        slot2 = await adapter.acquire()
        await slot2.__aenter__()

        # Third acquire should block
        acquired = asyncio.Event()

        async def acquire_third():
            s = await adapter.acquire()
            acquired.set()
            return s

        task = asyncio.create_task(acquire_third())
        await asyncio.sleep(0.01)
        assert not acquired.is_set()

        # Release one
        await slot1.__aexit__(None, None, None)
        await asyncio.sleep(0.01)
        assert acquired.is_set()

        # Cleanup
        slot3 = task.result()
        await slot2.__aexit__(None, None, None)
        await slot3.__aexit__(None, None, None)
