"""Tests for the bounded-concurrency gather utility.

Verifies gather_with_semaphore from core/concurrency.py — ordering
guarantees, concurrency bounds, error handling, and structured logging.
"""

from __future__ import annotations

import asyncio

import pytest
import structlog.testing

from autom8_asana.core.concurrency import gather_with_semaphore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _succeed(value: object) -> object:
    """Coroutine that returns its argument after yielding control."""
    await asyncio.sleep(0)
    return value


async def _fail(msg: str) -> None:
    """Coroutine that raises ValueError."""
    await asyncio.sleep(0)
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Basic behavior
# ---------------------------------------------------------------------------


class TestGatherWithSemaphore:
    """Core behavior tests for gather_with_semaphore."""

    @pytest.mark.asyncio
    async def test_empty_returns_empty(self) -> None:
        """Passing an empty iterable returns an empty list."""
        result = await gather_with_semaphore([])
        assert result == []

    @pytest.mark.asyncio
    async def test_all_exceptions(self) -> None:
        """All coros raise; returns list of exceptions with return_exceptions=True."""
        coros = [_fail(f"err-{i}") for i in range(5)]
        results = await gather_with_semaphore(coros, return_exceptions=True)

        assert len(results) == 5
        for i, r in enumerate(results):
            assert isinstance(r, ValueError)
            assert str(r) == f"err-{i}"

    @pytest.mark.asyncio
    async def test_mixed_success_failure(self) -> None:
        """Mix of succeeding and failing coros preserves order."""
        coros = [
            _succeed(0),
            _fail("oops"),
            _succeed(2),
            _fail("boom"),
            _succeed(4),
        ]
        results = await gather_with_semaphore(coros, return_exceptions=True)

        assert len(results) == 5
        assert results[0] == 0
        assert isinstance(results[1], ValueError) and str(results[1]) == "oops"
        assert results[2] == 2
        assert isinstance(results[3], ValueError) and str(results[3]) == "boom"
        assert results[4] == 4

    @pytest.mark.asyncio
    async def test_generator_input(self) -> None:
        """Generator expression (not a list) is eagerly consumed and executed."""
        gen = (_succeed(i) for i in range(5))
        results = await gather_with_semaphore(gen)

        assert results == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_large_input(self) -> None:
        """100+ coros all complete without deadlock."""
        count = 150
        coros = [_succeed(i) for i in range(count)]
        results = await gather_with_semaphore(coros, concurrency=10)

        assert len(results) == count
        assert results == list(range(count))

    @pytest.mark.asyncio
    async def test_preserves_order(self) -> None:
        """Results match input order regardless of completion timing."""

        async def _delayed(value: int, delay: float) -> int:
            await asyncio.sleep(delay)
            return value

        # Coros with varying delays — later indices finish first
        coros = [
            _delayed(0, 0.05),
            _delayed(1, 0.01),
            _delayed(2, 0.03),
            _delayed(3, 0.0),
            _delayed(4, 0.02),
        ]
        results = await gather_with_semaphore(coros, concurrency=5)

        assert results == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Tests for return_exceptions=False behavior."""

    @pytest.mark.asyncio
    async def test_return_exceptions_false(self) -> None:
        """With return_exceptions=False, first exception propagates."""
        coros = [
            _succeed(0),
            _fail("propagated"),
            _succeed(2),
        ]
        with pytest.raises(ValueError, match="propagated"):
            await gather_with_semaphore(
                coros,
                return_exceptions=False,
            )


# ---------------------------------------------------------------------------
# Concurrency bound
# ---------------------------------------------------------------------------


class TestConcurrencyBound:
    """Tests that the semaphore actually limits concurrency."""

    @pytest.mark.asyncio
    async def test_concurrency_bound(self) -> None:
        """With concurrency=2 and 10 coros, at most 2 run simultaneously."""
        max_concurrent = 0
        current = 0
        lock = asyncio.Lock()

        async def _tracked() -> None:
            nonlocal max_concurrent, current
            async with lock:
                current += 1
                if current > max_concurrent:
                    max_concurrent = current
            # Hold the slot briefly to let others try to enter
            await asyncio.sleep(0.01)
            async with lock:
                current -= 1

        coros = [_tracked() for _ in range(10)]
        await gather_with_semaphore(coros, concurrency=2)

        assert max_concurrent <= 2, (
            f"Expected at most 2 concurrent, observed {max_concurrent}"
        )
        assert max_concurrent == 2, (
            f"Expected exactly 2 concurrent (sanity check), observed {max_concurrent}"
        )


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------


class TestStructuredLogging:
    """Tests for structured log output."""

    @pytest.mark.asyncio
    async def test_label_in_log(self) -> None:
        """Label appears in structured log output.

        When autom8y_log configures structlog with cache_logger_on_first_use=True,
        the module-level logger in concurrency.py caches its bound logger on first
        use. If earlier tests trigger that caching, structlog.testing.capture_logs()
        cannot intercept subsequent calls because the cached logger bypasses the
        reconfigured processor chain. Clearing the instance-level ``bind`` attribute
        forces the proxy to re-resolve from current config on next access.
        """
        from autom8_asana.core import concurrency as _conc_mod

        # Clear structlog BoundLoggerLazyProxy cache so capture_logs() works
        # even when earlier tests triggered cache_logger_on_first_use binding.
        proxy = _conc_mod.logger
        if "bind" in getattr(proxy, "__dict__", {}):
            del proxy.__dict__["bind"]

        with structlog.testing.capture_logs() as captured:
            await gather_with_semaphore(
                [_succeed(1), _succeed(2)],
                label="my_operation",
            )

        assert len(captured) >= 1
        log_entry = captured[-1]
        assert log_entry["event"] == "my_operation_completed"
        assert log_entry["succeeded"] == 2
        assert log_entry["failed"] == 0
        assert log_entry["total"] == 2
        assert "elapsed_ms" in log_entry
