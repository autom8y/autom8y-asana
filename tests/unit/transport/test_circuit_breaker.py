"""Unit tests for circuit breaker.

Tests the circuit breaker state machine per ADR-0048.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.config import CircuitBreakerConfig
from autom8_asana.exceptions import CircuitBreakerOpenError
from autom8_asana.transport.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerInit:
    """Test circuit breaker initialization."""

    def test_default_state_is_closed(self) -> None:
        """New circuit breaker starts in CLOSED state."""
        config = CircuitBreakerConfig(enabled=True)
        cb = CircuitBreaker(config)

        assert cb.state == CircuitState.CLOSED

    def test_disabled_by_default(self) -> None:
        """Default config has enabled=False."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)

        assert cb.enabled is False

    def test_custom_config_applied(self) -> None:
        """Custom config values are respected."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=10,
            recovery_timeout=120.0,
            half_open_max_calls=3,
        )
        cb = CircuitBreaker(config)

        assert cb.enabled is True
        assert cb._config.failure_threshold == 10
        assert cb._config.recovery_timeout == 120.0
        assert cb._config.half_open_max_calls == 3


class TestCircuitBreakerDisabled:
    """Test behavior when circuit breaker is disabled."""

    @pytest.mark.asyncio
    async def test_check_does_nothing_when_disabled(self) -> None:
        """check() is a no-op when disabled."""
        config = CircuitBreakerConfig(enabled=False)
        cb = CircuitBreaker(config)

        # Should not raise even if we would normally be in OPEN state
        cb._state = CircuitState.OPEN
        await cb.check()  # No exception

    @pytest.mark.asyncio
    async def test_record_success_does_nothing_when_disabled(self) -> None:
        """record_success() is a no-op when disabled."""
        config = CircuitBreakerConfig(enabled=False)
        cb = CircuitBreaker(config)

        cb._failure_count = 5
        await cb.record_success()

        # Failure count should NOT be reset when disabled
        assert cb._failure_count == 5

    @pytest.mark.asyncio
    async def test_record_failure_does_nothing_when_disabled(self) -> None:
        """record_failure() is a no-op when disabled."""
        config = CircuitBreakerConfig(enabled=False)
        cb = CircuitBreaker(config)

        await cb.record_failure(Exception("test error"))

        # Failure count should NOT be incremented when disabled
        assert cb._failure_count == 0


class TestCircuitBreakerStateTransitions:
    """Test state machine transitions."""

    @pytest.mark.asyncio
    async def test_closed_to_open_on_threshold(self) -> None:
        """CLOSED -> OPEN when failure_threshold reached."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=3)
        cb = CircuitBreaker(config)

        # Record failures up to threshold
        for _ in range(3):
            await cb.record_failure(Exception("error"))

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self) -> None:
        """OPEN -> HALF_OPEN after recovery_timeout elapsed."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=1,
            recovery_timeout=10.0,
        )
        cb = CircuitBreaker(config)

        # Trigger OPEN state
        with patch("time.monotonic", return_value=1000.0):
            await cb.record_failure(Exception("error"))

        assert cb.state == CircuitState.OPEN

        # Time has passed beyond recovery timeout
        with patch("time.monotonic", return_value=1015.0):  # 15s later > 10s timeout
            await cb.check()

        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self) -> None:
        """HALF_OPEN -> CLOSED on successful probe."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=1)
        cb = CircuitBreaker(config)

        # Set up HALF_OPEN state directly
        cb._state = CircuitState.HALF_OPEN

        await cb.record_success()

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self) -> None:
        """HALF_OPEN -> OPEN on failed probe."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=3)
        cb = CircuitBreaker(config)

        # Set up HALF_OPEN state directly
        cb._state = CircuitState.HALF_OPEN

        await cb.record_failure(Exception("probe failed"))

        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerFailureThreshold:
    """Test failure counting and threshold behavior."""

    @pytest.mark.asyncio
    async def test_failure_count_increments(self) -> None:
        """Each failure increments count."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=10)
        cb = CircuitBreaker(config)

        await cb.record_failure(Exception("error 1"))
        assert cb.failure_count == 1

        await cb.record_failure(Exception("error 2"))
        assert cb.failure_count == 2

        await cb.record_failure(Exception("error 3"))
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        """Success resets failure count to 0."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=10)
        cb = CircuitBreaker(config)

        # Build up some failures
        await cb.record_failure(Exception("error 1"))
        await cb.record_failure(Exception("error 2"))
        assert cb.failure_count == 2

        # Success should reset
        await cb.record_success()
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_threshold_not_reached_stays_closed(self) -> None:
        """Circuit stays CLOSED if threshold not reached."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=5)
        cb = CircuitBreaker(config)

        # Record failures but stay below threshold
        for _ in range(4):
            await cb.record_failure(Exception("error"))

        assert cb.failure_count == 4
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerRecovery:
    """Test recovery timeout and half-open probing."""

    @pytest.mark.asyncio
    async def test_check_raises_when_open(self) -> None:
        """check() raises CircuitBreakerOpenError when OPEN."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=1,
            recovery_timeout=60.0,
        )
        cb = CircuitBreaker(config)

        # Trigger OPEN state
        with patch("time.monotonic", return_value=1000.0):
            await cb.record_failure(Exception("error"))

        assert cb.state == CircuitState.OPEN

        # check() before recovery timeout should raise
        with (
            patch("time.monotonic", return_value=1030.0),
            pytest.raises(CircuitBreakerOpenError),
        ):  # 30s later < 60s timeout
            await cb.check()

    @pytest.mark.asyncio
    async def test_time_until_recovery_in_error(self) -> None:
        """CircuitBreakerOpenError includes time until recovery."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=1,
            recovery_timeout=60.0,
        )
        cb = CircuitBreaker(config)

        # Trigger OPEN state
        with patch("time.monotonic", return_value=1000.0):
            await cb.record_failure(Exception("error"))

        # Check error contains time remaining (30s remaining)
        with patch("time.monotonic", return_value=1030.0):
            try:
                await cb.check()
                pytest.fail("Expected CircuitBreakerOpenError")
            except CircuitBreakerOpenError as e:
                assert e.time_until_recovery == pytest.approx(30.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_half_open_limits_calls(self) -> None:
        """HALF_OPEN limits concurrent probes to half_open_max_calls."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=1,
            recovery_timeout=10.0,
            half_open_max_calls=2,
        )
        cb = CircuitBreaker(config)

        # Trigger OPEN state
        with patch("time.monotonic", return_value=1000.0):
            await cb.record_failure(Exception("error"))

        # Transition to HALF_OPEN
        with patch("time.monotonic", return_value=1015.0):
            await cb.check()  # First call - transitions to HALF_OPEN

        assert cb.state == CircuitState.HALF_OPEN
        assert cb._half_open_calls == 1

        # Second call allowed
        with patch("time.monotonic", return_value=1015.0):
            await cb.check()

        assert cb._half_open_calls == 2

        # Third call should be rejected
        with (
            patch("time.monotonic", return_value=1015.0),
            pytest.raises(CircuitBreakerOpenError) as exc_info,
        ):
            await cb.check()

        # Time remaining should be 0 (we're in HALF_OPEN, just limiting calls)
        assert exc_info.value.time_until_recovery == 0.0


class TestCircuitBreakerEventHooks:
    """Test event hook callbacks."""

    @pytest.mark.asyncio
    async def test_on_state_change_called(self) -> None:
        """on_state_change hook is called on transitions."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=1)
        cb = CircuitBreaker(config)

        transitions: list[tuple[CircuitState, CircuitState]] = []

        def track_transition(old: CircuitState, new: CircuitState) -> None:
            transitions.append((old, new))

        cb.on_state_change(track_transition)

        # Trigger CLOSED -> OPEN
        await cb.record_failure(Exception("error"))

        assert len(transitions) == 1
        assert transitions[0] == (CircuitState.CLOSED, CircuitState.OPEN)

    @pytest.mark.asyncio
    async def test_on_failure_called(self) -> None:
        """on_failure hook is called when failure recorded."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=10)
        cb = CircuitBreaker(config)

        failures: list[Exception] = []

        def track_failure(error: Exception) -> None:
            failures.append(error)

        cb.on_failure(track_failure)

        test_error = ValueError("test error")
        await cb.record_failure(test_error)

        assert len(failures) == 1
        assert failures[0] is test_error

    @pytest.mark.asyncio
    async def test_on_success_called(self) -> None:
        """on_success hook is called when success recorded."""
        config = CircuitBreakerConfig(enabled=True)
        cb = CircuitBreaker(config)

        success_count = {"count": 0}

        def track_success() -> None:
            success_count["count"] += 1

        cb.on_success(track_success)

        await cb.record_success()

        assert success_count["count"] == 1

    @pytest.mark.asyncio
    async def test_hook_exception_does_not_break_circuit(self) -> None:
        """Hook exceptions are swallowed."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=1)
        cb = CircuitBreaker(config)

        def bad_hook(*args: Any) -> None:
            raise RuntimeError("Hook exploded!")

        cb.on_state_change(bad_hook)
        cb.on_failure(bad_hook)
        cb.on_success(bad_hook)

        # These should not raise despite bad hooks
        await cb.record_failure(
            Exception("error")
        )  # Triggers state change + failure hooks
        assert cb.state == CircuitState.OPEN

        # Set up for success test
        cb._state = CircuitState.HALF_OPEN
        await cb.record_success()  # Triggers state change + success hooks
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerConcurrency:
    """Test thread safety with asyncio.Lock."""

    @pytest.mark.asyncio
    async def test_concurrent_failures_handled(self) -> None:
        """Concurrent record_failure calls don't cause race conditions."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=100)
        cb = CircuitBreaker(config)

        async def record_one_failure() -> None:
            await cb.record_failure(Exception("concurrent error"))

        # Fire off many concurrent failures
        await asyncio.gather(*[record_one_failure() for _ in range(50)])

        # All 50 should have been counted
        assert cb.failure_count == 50

    @pytest.mark.asyncio
    async def test_concurrent_checks_handled(self) -> None:
        """Concurrent check() calls are serialized properly."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=1,
            recovery_timeout=10.0,
            half_open_max_calls=3,
        )
        cb = CircuitBreaker(config)

        # Trigger OPEN state
        with patch("time.monotonic", return_value=1000.0):
            await cb.record_failure(Exception("error"))

        # Simulate many concurrent checks after recovery timeout
        results: list[str] = []

        async def try_check() -> None:
            try:
                with patch("time.monotonic", return_value=1015.0):
                    await cb.check()
                results.append("allowed")
            except CircuitBreakerOpenError:
                results.append("rejected")

        # Fire off more checks than half_open_max_calls allows
        await asyncio.gather(*[try_check() for _ in range(10)])

        # Exactly half_open_max_calls (3) should be allowed
        allowed_count = results.count("allowed")
        rejected_count = results.count("rejected")

        assert allowed_count == 3
        assert rejected_count == 7


class TestCircuitBreakerEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_failure_count_reset_on_transition_to_closed(self) -> None:
        """Transitioning to CLOSED resets failure count."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=5)
        cb = CircuitBreaker(config)

        # Build up failures
        cb._failure_count = 3
        cb._state = CircuitState.HALF_OPEN

        # Transition to CLOSED via success
        await cb.record_success()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_calls_reset_on_transition(self) -> None:
        """Transitioning to HALF_OPEN resets the call counter."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=1,
            recovery_timeout=10.0,
        )
        cb = CircuitBreaker(config)

        # Trigger OPEN, then transition to HALF_OPEN multiple times
        with patch("time.monotonic", return_value=1000.0):
            await cb.record_failure(Exception("error"))

        # First transition to HALF_OPEN
        with patch("time.monotonic", return_value=1015.0):
            await cb.check()

        assert cb._half_open_calls == 1

        # Fail the probe - back to OPEN
        with patch("time.monotonic", return_value=1015.0):
            await cb.record_failure(Exception("probe failed"))

        assert cb.state == CircuitState.OPEN

        # Second transition to HALF_OPEN - counter should reset
        with patch("time.monotonic", return_value=1030.0):
            await cb.check()

        assert cb.state == CircuitState.HALF_OPEN
        assert cb._half_open_calls == 1  # Reset to 1, not carried over

    @pytest.mark.asyncio
    async def test_no_last_failure_time_allows_recovery(self) -> None:
        """If last_failure_time is None, recovery is allowed."""
        config = CircuitBreakerConfig(
            enabled=True,
            failure_threshold=1,
            recovery_timeout=60.0,
        )
        cb = CircuitBreaker(config)

        # Directly set OPEN state without recording failure time
        cb._state = CircuitState.OPEN
        cb._last_failure_time = None

        # Should transition to HALF_OPEN immediately
        await cb.check()

        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_time_until_recovery_zero_when_no_failure_time(self) -> None:
        """time_until_recovery returns 0 if no failure recorded."""
        config = CircuitBreakerConfig(enabled=True, recovery_timeout=60.0)
        cb = CircuitBreaker(config)

        # Internal method check
        assert cb._time_until_recovery() == 0.0

    @pytest.mark.asyncio
    async def test_multiple_hooks_all_called(self) -> None:
        """Multiple registered hooks are all invoked."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=1)
        cb = CircuitBreaker(config)

        call_order: list[str] = []

        cb.on_state_change(lambda old, new: call_order.append("hook1"))
        cb.on_state_change(lambda old, new: call_order.append("hook2"))
        cb.on_state_change(lambda old, new: call_order.append("hook3"))

        await cb.record_failure(Exception("error"))

        assert call_order == ["hook1", "hook2", "hook3"]

    @pytest.mark.asyncio
    async def test_logger_called_on_state_change(self) -> None:
        """Logger is called when state changes."""
        config = CircuitBreakerConfig(enabled=True, failure_threshold=1)
        mock_log = MagicMock()
        cb = CircuitBreaker(config, log=mock_log)

        await cb.record_failure(Exception("error"))

        mock_log.info.assert_called_once_with(
            "circuit_breaker_state_change",
            old_state="closed",
            new_state="open",
        )
