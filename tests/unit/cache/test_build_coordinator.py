"""Tests for BuildCoordinator.

Per TDD-BUILD-COALESCING-001: Validates coalescing, staleness rejection,
concurrency limiting, timeout, cancellation isolation, error propagation,
and metrics accuracy.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime

import polars as pl
import pytest

from autom8_asana.cache.dataframe.build_coordinator import (
    BuildCoordinator,
    BuildOutcome,
    CoalescingKey,
    make_coalescing_key,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_df(rows: int = 5) -> pl.DataFrame:
    """Create a small test DataFrame."""
    return pl.DataFrame({"gid": [str(i) for i in range(rows)]})


def _make_key(project: str = "proj-1", entity: str = "unit") -> CoalescingKey:
    """Create a test coalescing key."""
    return make_coalescing_key(project, entity)


async def _slow_build(
    delay: float = 0.1, rows: int = 5
) -> tuple[pl.DataFrame, datetime]:
    """Simulate a build that takes time."""
    await asyncio.sleep(delay)
    return _make_df(rows), datetime.now(UTC)


async def _instant_build(rows: int = 5) -> tuple[pl.DataFrame, datetime]:
    """Simulate an instant build."""
    return _make_df(rows), datetime.now(UTC)


async def _failing_build() -> tuple[pl.DataFrame, datetime]:
    """Build function that always raises."""
    raise ConnectionError("Build exploded")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def coordinator() -> BuildCoordinator:
    """Create a BuildCoordinator with sensible test defaults."""
    return BuildCoordinator(
        default_timeout_seconds=5.0,
        max_concurrent_builds=4,
    )


# ---------------------------------------------------------------------------
# Unit Tests: Basic Operations
# ---------------------------------------------------------------------------


class TestBuildCoordinatorBasic:
    """Basic functionality tests."""

    @pytest.mark.asyncio
    async def test_single_build_no_coalescing(
        self, coordinator: BuildCoordinator
    ) -> None:
        """One caller, no contention: outcome is BUILT."""
        key = _make_key()
        result = await coordinator.build_or_wait_async(key, _instant_build)

        assert result.outcome == BuildOutcome.BUILT
        assert result.dataframe is not None
        assert result.dataframe.shape[0] == 5
        assert result.watermark is not None
        assert result.waiter_count == 0
        assert result.error is None
        assert result.build_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_two_callers_coalesced(self, coordinator: BuildCoordinator) -> None:
        """Two concurrent callers for same key: one BUILT, one COALESCED."""
        key = _make_key()

        async def slow_build() -> tuple[pl.DataFrame, datetime]:
            return await _slow_build(delay=0.2)

        results = await asyncio.gather(
            coordinator.build_or_wait_async(key, slow_build, caller="first"),
            coordinator.build_or_wait_async(key, slow_build, caller="second"),
        )

        outcomes = {r.outcome for r in results}
        assert BuildOutcome.BUILT in outcomes
        assert BuildOutcome.COALESCED in outcomes

        # Both should receive a DataFrame
        for r in results:
            assert r.dataframe is not None
            assert r.dataframe.shape[0] == 5

    @pytest.mark.asyncio
    async def test_different_keys_independent(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Two callers with different keys: both BUILT independently."""
        key1 = _make_key("proj-1", "unit")
        key2 = _make_key("proj-2", "offer")

        build_count = 0

        async def counting_build() -> tuple[pl.DataFrame, datetime]:
            nonlocal build_count
            build_count += 1
            return await _slow_build(delay=0.1)

        results = await asyncio.gather(
            coordinator.build_or_wait_async(key1, counting_build),
            coordinator.build_or_wait_async(key2, counting_build),
        )

        assert results[0].outcome == BuildOutcome.BUILT
        assert results[1].outcome == BuildOutcome.BUILT
        assert build_count == 2

    @pytest.mark.asyncio
    async def test_is_building_during_build(
        self, coordinator: BuildCoordinator
    ) -> None:
        """is_building returns True during build, False after."""
        key = _make_key()
        build_started = asyncio.Event()
        proceed = asyncio.Event()

        async def gated_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await proceed.wait()
            return _make_df(), datetime.now(UTC)

        task = asyncio.create_task(coordinator.build_or_wait_async(key, gated_build))

        await build_started.wait()
        assert coordinator.is_building(key) is True

        proceed.set()
        await task

        assert coordinator.is_building(key) is False

    @pytest.mark.asyncio
    async def test_cleanup_after_completion(
        self, coordinator: BuildCoordinator
    ) -> None:
        """After build completes, key is removed from _in_flight."""
        key = _make_key()
        await coordinator.build_or_wait_async(key, _instant_build)

        assert key not in coordinator._in_flight

    @pytest.mark.asyncio
    async def test_make_coalescing_key(self) -> None:
        """make_coalescing_key returns correct tuple."""
        key = make_coalescing_key("1234", "unit")
        assert key == ("1234", "unit")
        assert key[0] == "1234"
        assert key[1] == "unit"


# ---------------------------------------------------------------------------
# Unit Tests: Timeout Behavior
# ---------------------------------------------------------------------------


class TestBuildCoordinatorTimeout:
    """Timeout behavior tests."""

    @pytest.mark.asyncio
    async def test_timeout_returns_timed_out(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Waiter that exceeds timeout gets TIMED_OUT outcome."""
        key = _make_key()
        build_started = asyncio.Event()
        proceed = asyncio.Event()

        async def slow_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await proceed.wait()
            return _make_df(), datetime.now(UTC)

        # Start first build (will hold)
        builder_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, slow_build, caller="builder")
        )
        await build_started.wait()

        # Second caller with short timeout
        waiter_result = await coordinator.build_or_wait_async(
            key, slow_build, timeout_seconds=0.1, caller="waiter"
        )

        assert waiter_result.outcome == BuildOutcome.TIMED_OUT
        assert waiter_result.dataframe is None
        assert waiter_result.watermark is None

        # Let builder finish
        proceed.set()
        builder_result = await builder_task
        assert builder_result.outcome == BuildOutcome.BUILT

    @pytest.mark.asyncio
    async def test_timeout_does_not_cancel_build(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Timed-out waiter does not cancel the in-flight build."""
        key = _make_key()
        build_completed = asyncio.Event()
        build_started = asyncio.Event()

        async def tracked_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await asyncio.sleep(0.5)
            build_completed.set()
            return _make_df(), datetime.now(UTC)

        builder_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, tracked_build, caller="builder")
        )
        await build_started.wait()

        # Waiter times out
        await coordinator.build_or_wait_async(
            key, tracked_build, timeout_seconds=0.05, caller="waiter"
        )

        # Build should still complete
        await builder_task
        assert build_completed.is_set()

    @pytest.mark.asyncio
    async def test_timeout_under_slow_build(self) -> None:
        """build_fn sleeps 2s, waiter timeout 0.2s: waiter gets TIMED_OUT, builder completes."""
        coordinator = BuildCoordinator(
            default_timeout_seconds=5.0, max_concurrent_builds=4
        )
        key = _make_key()
        build_started = asyncio.Event()

        async def very_slow_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await asyncio.sleep(2.0)
            return _make_df(), datetime.now(UTC)

        builder_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, very_slow_build, caller="builder")
        )
        await build_started.wait()

        waiter_result = await coordinator.build_or_wait_async(
            key, very_slow_build, timeout_seconds=0.2, caller="waiter"
        )
        assert waiter_result.outcome == BuildOutcome.TIMED_OUT

        builder_result = await builder_task
        assert builder_result.outcome == BuildOutcome.BUILT


# ---------------------------------------------------------------------------
# Unit Tests: Error Propagation
# ---------------------------------------------------------------------------


class TestBuildCoordinatorErrors:
    """Error propagation tests."""

    @pytest.mark.asyncio
    async def test_build_failure_propagates_to_builder(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Build that raises returns FAILED outcome to the builder."""
        key = _make_key()
        result = await coordinator.build_or_wait_async(key, _failing_build)

        assert result.outcome == BuildOutcome.FAILED
        assert result.error is not None
        assert isinstance(result.error, ConnectionError)
        assert "Build exploded" in str(result.error)
        assert result.dataframe is None

    @pytest.mark.asyncio
    async def test_build_failure_propagates_to_waiters(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Build failure propagates FAILED result to all coalesced waiters."""
        key = _make_key()
        build_started = asyncio.Event()

        async def delayed_failure() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await asyncio.sleep(0.2)
            raise ConnectionError("Delayed explosion")

        builder_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, delayed_failure, caller="builder")
        )
        await build_started.wait()

        # Let the second caller join before failure
        await asyncio.sleep(0.05)
        waiter_result = await coordinator.build_or_wait_async(
            key, delayed_failure, caller="waiter"
        )

        builder_result = await builder_task

        # Both should see FAILED
        assert builder_result.outcome == BuildOutcome.FAILED
        assert waiter_result.outcome == BuildOutcome.FAILED
        assert waiter_result.error is not None

    @pytest.mark.asyncio
    async def test_failure_cleans_up_in_flight(
        self, coordinator: BuildCoordinator
    ) -> None:
        """After build failure, key is removed from _in_flight."""
        key = _make_key()
        await coordinator.build_or_wait_async(key, _failing_build)

        assert key not in coordinator._in_flight

    @pytest.mark.asyncio
    async def test_new_build_after_failure(self, coordinator: BuildCoordinator) -> None:
        """A new build can start after a previous failure for the same key."""
        key = _make_key()

        # First build fails
        result1 = await coordinator.build_or_wait_async(key, _failing_build)
        assert result1.outcome == BuildOutcome.FAILED

        # Second build succeeds
        result2 = await coordinator.build_or_wait_async(key, _instant_build)
        assert result2.outcome == BuildOutcome.BUILT
        assert result2.dataframe is not None


# ---------------------------------------------------------------------------
# Unit Tests: Staleness Gate
# ---------------------------------------------------------------------------


class TestBuildCoordinatorStaleness:
    """Staleness-aware coalescing tests."""

    @pytest.mark.asyncio
    async def test_mark_invalidated_during_build(
        self, coordinator: BuildCoordinator
    ) -> None:
        """mark_invalidated causes new callers to start fresh builds."""
        key = _make_key("proj-1", "unit")
        build_started = asyncio.Event()
        proceed = asyncio.Event()

        build_call_count = 0

        async def tracked_build() -> tuple[pl.DataFrame, datetime]:
            nonlocal build_call_count
            build_call_count += 1
            if build_call_count == 1:
                build_started.set()
                await proceed.wait()
            return _make_df(), datetime.now(UTC)

        # Start first build
        builder_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, tracked_build, caller="first")
        )
        await build_started.wait()

        # Mark as invalidated
        marked = coordinator.mark_invalidated("proj-1", "unit")
        assert marked == 1

        # New caller should start a fresh build (not coalesce)
        second_result = await coordinator.build_or_wait_async(
            key, tracked_build, caller="second"
        )
        assert second_result.outcome == BuildOutcome.BUILT
        assert build_call_count == 2

        # Let first build finish
        proceed.set()
        first_result = await builder_task
        assert first_result.outcome == BuildOutcome.BUILT

    @pytest.mark.asyncio
    async def test_mark_invalidated_all_entity_types(
        self, coordinator: BuildCoordinator
    ) -> None:
        """mark_invalidated with entity_type=None marks all entity types."""
        build_events = {}
        proceeds = {}

        for et in ("unit", "offer"):
            build_events[et] = asyncio.Event()
            proceeds[et] = asyncio.Event()

        async def make_build(et: str) -> tuple[pl.DataFrame, datetime]:
            build_events[et].set()
            await proceeds[et].wait()
            return _make_df(), datetime.now(UTC)

        key_unit = _make_key("proj-1", "unit")
        key_offer = _make_key("proj-1", "offer")

        t1 = asyncio.create_task(
            coordinator.build_or_wait_async(
                key_unit, lambda: make_build("unit"), caller="unit-builder"
            )
        )
        t2 = asyncio.create_task(
            coordinator.build_or_wait_async(
                key_offer, lambda: make_build("offer"), caller="offer-builder"
            )
        )

        await build_events["unit"].wait()
        await build_events["offer"].wait()

        # Invalidate all entity types for proj-1
        marked = coordinator.mark_invalidated("proj-1")
        assert marked == 2

        # Let builds finish
        proceeds["unit"].set()
        proceeds["offer"].set()
        await t1
        await t2

    @pytest.mark.asyncio
    async def test_existing_waiters_still_receive_result(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Invalidation does not orphan existing waiters."""
        key = _make_key("proj-1", "unit")
        build_started = asyncio.Event()
        proceed = asyncio.Event()

        async def gated_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await proceed.wait()
            return _make_df(rows=10), datetime.now(UTC)

        # Start builder
        builder_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, gated_build, caller="builder")
        )
        await build_started.wait()

        # Add a waiter BEFORE invalidation
        waiter_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, gated_build, caller="waiter")
        )
        await asyncio.sleep(0.05)  # Let waiter register

        # Invalidate -- waiter should NOT be orphaned
        coordinator.mark_invalidated("proj-1", "unit")

        # Complete the build
        proceed.set()

        builder_result = await builder_task
        waiter_result = await waiter_task

        # Builder: BUILT, Waiter: COALESCED (joined before invalidation)
        assert builder_result.outcome == BuildOutcome.BUILT
        assert waiter_result.outcome == BuildOutcome.COALESCED
        assert waiter_result.dataframe is not None
        assert waiter_result.dataframe.shape[0] == 10

    @pytest.mark.asyncio
    async def test_mark_invalidated_no_match(
        self, coordinator: BuildCoordinator
    ) -> None:
        """mark_invalidated returns 0 when no in-flight builds match."""
        result = coordinator.mark_invalidated("nonexistent-project")
        assert result == 0

    @pytest.mark.asyncio
    async def test_concurrent_mark_invalidated(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Multiple concurrent mark_invalidated calls are safe."""
        key = _make_key("proj-1", "unit")
        build_started = asyncio.Event()
        proceed = asyncio.Event()

        async def gated_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await proceed.wait()
            return _make_df(), datetime.now(UTC)

        task = asyncio.create_task(coordinator.build_or_wait_async(key, gated_build))
        await build_started.wait()

        # Multiple invalidation calls -- should be idempotent
        results = [coordinator.mark_invalidated("proj-1", "unit") for _ in range(10)]
        # First call marks 1, subsequent calls also see the already-invalidated build
        assert all(r == 1 for r in results)

        proceed.set()
        await task

    @pytest.mark.asyncio
    async def test_stale_rejected_stats(self, coordinator: BuildCoordinator) -> None:
        """builds_stale_rejected stat increments on staleness rejection."""
        key = _make_key("proj-1", "unit")
        build_started = asyncio.Event()
        proceed = asyncio.Event()

        call_count = 0

        async def counted_build() -> tuple[pl.DataFrame, datetime]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                build_started.set()
                await proceed.wait()
            return _make_df(), datetime.now(UTC)

        task = asyncio.create_task(
            coordinator.build_or_wait_async(key, counted_build, caller="first")
        )
        await build_started.wait()

        coordinator.mark_invalidated("proj-1", "unit")

        # This triggers stale rejection
        await coordinator.build_or_wait_async(key, counted_build, caller="second")

        proceed.set()
        await task

        stats = coordinator.get_stats()
        assert stats["builds_stale_rejected"] == 1

    @pytest.mark.asyncio
    async def test_build_fn_raises_after_invalidation(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Build marked stale, then build_fn raises: new build can start cleanly."""
        key = _make_key("proj-1", "unit")
        build_started = asyncio.Event()

        async def failing_after_start() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await asyncio.sleep(0.1)
            raise ConnectionError("Failed after invalidation")

        task = asyncio.create_task(
            coordinator.build_or_wait_async(key, failing_after_start, caller="first")
        )
        await build_started.wait()

        coordinator.mark_invalidated("proj-1", "unit")

        result = await task
        assert result.outcome == BuildOutcome.FAILED

        # Should be able to start a fresh build
        result2 = await coordinator.build_or_wait_async(
            key, _instant_build, caller="second"
        )
        assert result2.outcome == BuildOutcome.BUILT
        assert result2.dataframe is not None


# ---------------------------------------------------------------------------
# Unit Tests: Concurrency Limiting
# ---------------------------------------------------------------------------


class TestBuildCoordinatorConcurrency:
    """Concurrency limit (semaphore) tests."""

    @pytest.mark.asyncio
    async def test_max_concurrent_builds_honored(self) -> None:
        """Semaphore limits concurrent builds to max_concurrent_builds."""
        max_builds = 2
        coordinator = BuildCoordinator(
            default_timeout_seconds=10.0,
            max_concurrent_builds=max_builds,
        )

        concurrent_count = 0
        max_observed = 0
        lock = asyncio.Lock()

        async def tracking_build() -> tuple[pl.DataFrame, datetime]:
            nonlocal concurrent_count, max_observed
            async with lock:
                concurrent_count += 1
                max_observed = max(max_observed, concurrent_count)
            await asyncio.sleep(0.2)
            async with lock:
                concurrent_count -= 1
            return _make_df(), datetime.now(UTC)

        # Start 6 builds with different keys
        keys = [_make_key(f"proj-{i}", "unit") for i in range(6)]
        results = await asyncio.gather(
            *[coordinator.build_or_wait_async(key, tracking_build) for key in keys]
        )

        assert all(r.outcome == BuildOutcome.BUILT for r in results)
        assert max_observed <= max_builds

    @pytest.mark.asyncio
    async def test_semaphore_does_not_block_coalesced_waiters(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Coalesced waiters do not consume semaphore slots."""
        key = _make_key()

        async def slow_build() -> tuple[pl.DataFrame, datetime]:
            await asyncio.sleep(0.2)
            return _make_df(), datetime.now(UTC)

        # Launch many requests for same key -- only one should acquire semaphore
        results = await asyncio.gather(
            *[coordinator.build_or_wait_async(key, slow_build) for _ in range(10)]
        )

        built_count = sum(1 for r in results if r.outcome == BuildOutcome.BUILT)
        coalesced_count = sum(1 for r in results if r.outcome == BuildOutcome.COALESCED)

        assert built_count == 1
        assert coalesced_count == 9


# ---------------------------------------------------------------------------
# Unit Tests: Cancellation Isolation
# ---------------------------------------------------------------------------


class TestBuildCoordinatorCancellation:
    """Cancellation isolation tests (asyncio.shield)."""

    @pytest.mark.asyncio
    async def test_shield_prevents_waiter_cancellation(
        self, coordinator: BuildCoordinator
    ) -> None:
        """Cancel one waiter; other waiters still receive the result."""
        key = _make_key()
        build_started = asyncio.Event()

        async def slow_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await asyncio.sleep(0.5)
            return _make_df(), datetime.now(UTC)

        # Start builder
        builder_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, slow_build, caller="builder")
        )
        await build_started.wait()

        # Start two waiters
        await asyncio.sleep(0.05)
        waiter1_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, slow_build, caller="waiter1")
        )
        waiter2_task = asyncio.create_task(
            coordinator.build_or_wait_async(key, slow_build, caller="waiter2")
        )
        await asyncio.sleep(0.05)

        # Cancel waiter1
        waiter1_task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await waiter1_task

        # waiter2 and builder should still succeed
        builder_result = await builder_task
        waiter2_result = await waiter2_task

        assert builder_result.outcome == BuildOutcome.BUILT
        assert waiter2_result.outcome == BuildOutcome.COALESCED
        assert waiter2_result.dataframe is not None


# ---------------------------------------------------------------------------
# Unit Tests: Statistics
# ---------------------------------------------------------------------------


class TestBuildCoordinatorStats:
    """Statistics tracking tests."""

    @pytest.mark.asyncio
    async def test_stats_accuracy(self, coordinator: BuildCoordinator) -> None:
        """Run mixed scenario, check all stat counters."""
        key1 = _make_key("proj-1", "unit")
        key2 = _make_key("proj-2", "offer")

        # Two concurrent builds on key1 (1 built, 1 coalesced)
        async def slow() -> tuple[pl.DataFrame, datetime]:
            await asyncio.sleep(0.1)
            return _make_df(), datetime.now(UTC)

        results = await asyncio.gather(
            coordinator.build_or_wait_async(key1, slow, caller="a"),
            coordinator.build_or_wait_async(key1, slow, caller="b"),
        )

        # One independent build on key2
        await coordinator.build_or_wait_async(key2, _instant_build, caller="c")

        # One failing build
        key3 = _make_key("proj-3", "unit")
        await coordinator.build_or_wait_async(key3, _failing_build, caller="d")

        stats = coordinator.get_stats()

        # 3 unique builds started (key1, key2, key3)
        assert stats["builds_started"] == 3
        assert stats["builds_coalesced"] == 1
        assert stats["builds_succeeded"] == 2
        assert stats["builds_failed"] == 1
        assert stats["builds_timed_out"] == 0
        assert stats["builds_stale_rejected"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_returns_copy(self, coordinator: BuildCoordinator) -> None:
        """get_stats returns a copy, not a reference to internal state."""
        stats1 = coordinator.get_stats()
        stats1["builds_started"] = 999

        stats2 = coordinator.get_stats()
        assert stats2["builds_started"] == 0


# ---------------------------------------------------------------------------
# Unit Tests: Force Cleanup
# ---------------------------------------------------------------------------


class TestBuildCoordinatorForceCleanup:
    """force_cleanup tests."""

    @pytest.mark.asyncio
    async def test_force_cleanup_removes_in_flight(
        self, coordinator: BuildCoordinator
    ) -> None:
        """force_cleanup removes key from _in_flight and cancels future."""
        key = _make_key()
        build_started = asyncio.Event()

        async def hanging_build() -> tuple[pl.DataFrame, datetime]:
            build_started.set()
            await asyncio.sleep(100)  # Effectively hangs forever
            return _make_df(), datetime.now(UTC)

        task = asyncio.create_task(coordinator.build_or_wait_async(key, hanging_build))
        await build_started.wait()

        assert coordinator.is_building(key)

        await coordinator.force_cleanup(key)

        assert not coordinator.is_building(key)
        assert key not in coordinator._in_flight

        # Cancel the hanging task to clean up
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task

    @pytest.mark.asyncio
    async def test_force_cleanup_nonexistent_key(
        self, coordinator: BuildCoordinator
    ) -> None:
        """force_cleanup on nonexistent key is a no-op."""
        key = _make_key("nonexistent")
        await coordinator.force_cleanup(key)
        # Should not raise


# ---------------------------------------------------------------------------
# Concurrent Stress Tests
# ---------------------------------------------------------------------------


class TestBuildCoordinatorStress:
    """Concurrent stress tests per TDD test strategy."""

    @pytest.mark.asyncio
    async def test_100_concurrent_same_key(self) -> None:
        """100 concurrent callers for same key: exactly 1 BUILT, 99 COALESCED."""
        coordinator = BuildCoordinator(
            default_timeout_seconds=30.0,
            max_concurrent_builds=4,
        )
        key = _make_key()

        async def build() -> tuple[pl.DataFrame, datetime]:
            await asyncio.sleep(0.2)
            return _make_df(rows=42), datetime.now(UTC)

        results = await asyncio.gather(
            *[
                coordinator.build_or_wait_async(key, build, caller=f"caller-{i}")
                for i in range(100)
            ]
        )

        built = [r for r in results if r.outcome == BuildOutcome.BUILT]
        coalesced = [r for r in results if r.outcome == BuildOutcome.COALESCED]

        assert len(built) == 1
        assert len(coalesced) == 99

        # All receive the same DataFrame shape
        for r in results:
            assert r.dataframe is not None
            assert r.dataframe.shape[0] == 42

        stats = coordinator.get_stats()
        assert stats["builds_started"] == 1
        assert stats["builds_coalesced"] == 99

    @pytest.mark.asyncio
    async def test_rapid_invalidation_cycles(self) -> None:
        """Build -> invalidate -> build -> invalidate, 5 cycles: no deadlock."""
        coordinator = BuildCoordinator(
            default_timeout_seconds=10.0,
            max_concurrent_builds=4,
        )
        key = _make_key()

        for cycle in range(5):
            build_started = asyncio.Event()
            proceed = asyncio.Event()

            call_count = 0

            async def cycle_build() -> tuple[pl.DataFrame, datetime]:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    build_started.set()
                    await proceed.wait()
                return _make_df(), datetime.now(UTC)

            # Start build
            task = asyncio.create_task(
                coordinator.build_or_wait_async(
                    key, cycle_build, caller=f"cycle-{cycle}"
                )
            )
            await build_started.wait()

            # Invalidate mid-build
            coordinator.mark_invalidated("proj-1", "unit")

            # New build replaces stale one
            fresh_result = await coordinator.build_or_wait_async(
                key, cycle_build, caller=f"fresh-{cycle}"
            )
            assert fresh_result.outcome == BuildOutcome.BUILT

            # Let old build finish
            proceed.set()
            old_result = await task
            assert old_result.outcome == BuildOutcome.BUILT

        # No orphaned futures
        assert len(coordinator._in_flight) == 0

    @pytest.mark.asyncio
    async def test_mixed_keys_under_contention(self) -> None:
        """50 callers across 5 different keys: proper coalescing per key."""
        coordinator = BuildCoordinator(
            default_timeout_seconds=30.0,
            max_concurrent_builds=5,
        )

        keys = [_make_key(f"proj-{i}", "unit") for i in range(5)]

        async def build() -> tuple[pl.DataFrame, datetime]:
            await asyncio.sleep(0.15)
            return _make_df(), datetime.now(UTC)

        # 10 callers per key
        tasks = []
        for key in keys:
            for j in range(10):
                tasks.append(
                    coordinator.build_or_wait_async(
                        key, build, caller=f"k{key[0]}-c{j}"
                    )
                )

        results = await asyncio.gather(*tasks)

        # Each key should have exactly 1 BUILT
        for i, key in enumerate(keys):
            key_results = results[i * 10 : (i + 1) * 10]
            built = sum(1 for r in key_results if r.outcome == BuildOutcome.BUILT)
            coalesced = sum(
                1 for r in key_results if r.outcome == BuildOutcome.COALESCED
            )
            assert built == 1, f"Key {key}: expected 1 BUILT, got {built}"
            assert coalesced == 9, f"Key {key}: expected 9 COALESCED, got {coalesced}"

        stats = coordinator.get_stats()
        assert stats["builds_started"] == 5
        assert stats["builds_coalesced"] == 45


# ---------------------------------------------------------------------------
# Unit Tests: Default Configuration
# ---------------------------------------------------------------------------


class TestBuildCoordinatorConfiguration:
    """Configuration tests."""

    def test_default_configuration(self) -> None:
        """Test default configuration values."""
        coordinator = BuildCoordinator()
        assert coordinator.default_timeout_seconds == 60.0
        assert coordinator.max_concurrent_builds == 4

    def test_custom_configuration(self) -> None:
        """Test custom configuration values."""
        coordinator = BuildCoordinator(
            default_timeout_seconds=30.0,
            max_concurrent_builds=8,
        )
        assert coordinator.default_timeout_seconds == 30.0
        assert coordinator.max_concurrent_builds == 8

    def test_initial_stats_zeroed(self) -> None:
        """All stats start at zero."""
        coordinator = BuildCoordinator()
        stats = coordinator.get_stats()
        assert all(v == 0 for v in stats.values())
        assert "builds_started" in stats
        assert "builds_coalesced" in stats
        assert "builds_succeeded" in stats
        assert "builds_failed" in stats
        assert "builds_timed_out" in stats
        assert "builds_stale_rejected" in stats
