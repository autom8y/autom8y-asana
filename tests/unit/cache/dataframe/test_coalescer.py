"""Unit tests for DataFrameCacheCoalescer.

Per TDD-DATAFRAME-CACHE-001: Tests for request coalescing,
first-request-builds pattern, and waiter notification.
"""

import asyncio

import pytest

from autom8_asana.cache.dataframe.coalescer import (
    DataFrameCacheCoalescer,
)


class TestDataFrameCacheCoalescer:
    """Tests for DataFrameCacheCoalescer."""

    async def test_first_request_acquires(self) -> None:
        """First request acquires lock."""
        coalescer = DataFrameCacheCoalescer()

        acquired = await coalescer.try_acquire_async("key-1")

        assert acquired is True
        assert coalescer.is_building("key-1")

    async def test_second_request_does_not_acquire(self) -> None:
        """Second request does not acquire while first building."""
        coalescer = DataFrameCacheCoalescer()

        await coalescer.try_acquire_async("key-1")
        acquired = await coalescer.try_acquire_async("key-1")

        assert acquired is False

    async def test_different_keys_can_acquire(self) -> None:
        """Different keys can acquire independently."""
        coalescer = DataFrameCacheCoalescer()

        acquired1 = await coalescer.try_acquire_async("key-1")
        acquired2 = await coalescer.try_acquire_async("key-2")

        assert acquired1 is True
        assert acquired2 is True
        assert coalescer.is_building("key-1")
        assert coalescer.is_building("key-2")

    async def test_waiter_notified_on_success(self) -> None:
        """Waiters notified when build completes successfully."""
        coalescer = DataFrameCacheCoalescer()
        await coalescer.try_acquire_async("key-1")

        async def wait_and_check() -> bool:
            return await coalescer.wait_async("key-1", timeout_seconds=1.0)

        async def release() -> None:
            await asyncio.sleep(0.1)
            await coalescer.release_async("key-1", success=True)

        wait_task = asyncio.create_task(wait_and_check())
        release_task = asyncio.create_task(release())

        await release_task
        result = await wait_task

        assert result is True

    async def test_waiter_notified_on_failure(self) -> None:
        """Waiters notified when build fails."""
        coalescer = DataFrameCacheCoalescer()
        await coalescer.try_acquire_async("key-1")

        async def wait_and_check() -> bool:
            return await coalescer.wait_async("key-1", timeout_seconds=1.0)

        async def release() -> None:
            await asyncio.sleep(0.1)
            await coalescer.release_async("key-1", success=False)

        wait_task = asyncio.create_task(wait_and_check())
        release_task = asyncio.create_task(release())

        await release_task
        result = await wait_task

        assert result is False

    async def test_wait_timeout(self) -> None:
        """Wait times out if build takes too long."""
        coalescer = DataFrameCacheCoalescer()
        await coalescer.try_acquire_async("key-1")

        result = await coalescer.wait_async("key-1", timeout_seconds=0.1)

        assert result is False

        # Clean up
        await coalescer.release_async("key-1", success=False)

    async def test_wait_on_nonexistent_key(self) -> None:
        """Wait on nonexistent key returns False immediately."""
        coalescer = DataFrameCacheCoalescer()

        result = await coalescer.wait_async("nonexistent", timeout_seconds=1.0)

        assert result is False

    async def test_is_building_false_after_release(self) -> None:
        """is_building returns False after release (eventually)."""
        coalescer = DataFrameCacheCoalescer()

        await coalescer.try_acquire_async("key-1")
        assert coalescer.is_building("key-1")

        await coalescer.release_async("key-1", success=True)
        # Build status changes from BUILDING
        assert not coalescer.is_building("key-1")

    async def test_can_reacquire_after_cleanup(self) -> None:
        """Can acquire same key after cleanup."""
        coalescer = DataFrameCacheCoalescer()

        # First build
        await coalescer.try_acquire_async("key-1")
        await coalescer.release_async("key-1", success=True)

        # Force cleanup
        await coalescer.force_cleanup("key-1")

        # Should be able to acquire again
        acquired = await coalescer.try_acquire_async("key-1")
        assert acquired is True

    async def test_stats(self) -> None:
        """Stats track operations correctly."""
        coalescer = DataFrameCacheCoalescer()

        await coalescer.try_acquire_async("key-1")
        await coalescer.release_async("key-1", success=True)

        await coalescer.force_cleanup("key-1")

        await coalescer.try_acquire_async("key-2")
        await coalescer.release_async("key-2", success=False)

        stats = coalescer.get_stats()

        assert stats["acquires"] == 2
        assert stats["completions_success"] == 1
        assert stats["completions_failure"] == 1

    async def test_multiple_waiters(self) -> None:
        """Multiple waiters all get notified."""
        coalescer = DataFrameCacheCoalescer()
        await coalescer.try_acquire_async("key-1")

        results: list[bool] = []

        async def waiter(name: str) -> None:
            result = await coalescer.wait_async("key-1", timeout_seconds=1.0)
            results.append(result)

        # Start multiple waiters
        waiters = [asyncio.create_task(waiter(f"w-{i}")) for i in range(3)]

        # Give waiters time to register
        await asyncio.sleep(0.05)

        # Release
        await coalescer.release_async("key-1", success=True)

        # Wait for all
        await asyncio.gather(*waiters)

        assert len(results) == 3
        assert all(r is True for r in results)
