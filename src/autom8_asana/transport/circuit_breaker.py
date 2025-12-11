"""Circuit breaker for cascading failure prevention.

Per ADR-0048: Composition pattern wrapping request execution.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.config import CircuitBreakerConfig
    from autom8_asana.protocols.log import LogProvider

from autom8_asana.exceptions import CircuitBreakerOpenError


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Fast-fail mode
    HALF_OPEN = "half_open"  # Probe mode


class CircuitBreaker:
    """Circuit breaker state machine.

    State transitions:
        CLOSED -> (failure_threshold reached) -> OPEN
        OPEN -> (recovery_timeout elapsed) -> HALF_OPEN
        HALF_OPEN -> (probe succeeds) -> CLOSED
        HALF_OPEN -> (probe fails) -> OPEN
    """

    def __init__(
        self,
        config: CircuitBreakerConfig,
        log: LogProvider | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration.
            log: Optional logger for state transitions.
        """
        self._config = config
        self._log = log
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

        # Event hooks (local callbacks)
        self._on_state_change_hooks: list[
            Callable[[CircuitState, CircuitState], Any]
        ] = []
        self._on_failure_hooks: list[Callable[[Exception], Any]] = []
        self._on_success_hooks: list[Callable[[], Any]] = []

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def enabled(self) -> bool:
        """Whether circuit breaker is active."""
        return self._config.enabled

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        return self._failure_count

    # Hook registration methods

    def on_state_change(
        self, callback: Callable[[CircuitState, CircuitState], Any]
    ) -> None:
        """Register callback for state transitions.

        Args:
            callback: Function receiving (old_state, new_state).
        """
        self._on_state_change_hooks.append(callback)

    def on_failure(self, callback: Callable[[Exception], Any]) -> None:
        """Register callback for recorded failures.

        Args:
            callback: Function receiving the exception.
        """
        self._on_failure_hooks.append(callback)

    def on_success(self, callback: Callable[[], Any]) -> None:
        """Register callback for recorded successes.

        Args:
            callback: Function called on success (no arguments).
        """
        self._on_success_hooks.append(callback)

    async def check(self) -> None:
        """Pre-request guard.

        Raises:
            CircuitBreakerOpenError: If circuit is open and not ready for recovery.
        """
        if not self._config.enabled:
            return

        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    time_remaining = self._time_until_recovery()
                    raise CircuitBreakerOpenError(time_remaining)

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._config.half_open_max_calls:
                    raise CircuitBreakerOpenError(0.0)
                self._half_open_calls += 1

    async def record_success(self) -> None:
        """Record successful request."""
        if not self._config.enabled:
            return

        async with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.CLOSED)
            self._fire_success_hooks()

    async def record_failure(self, error: Exception) -> None:
        """Record failed request.

        Args:
            error: The exception that caused the failure.
        """
        if not self._config.enabled:
            return

        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            self._fire_failure_hooks(error)

            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._failure_count >= self._config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _should_attempt_recovery(self) -> bool:
        """Check if recovery timeout has elapsed."""
        if self._last_failure_time is None:
            return True
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed >= self._config.recovery_timeout

    def _time_until_recovery(self) -> float:
        """Calculate time remaining until recovery attempt."""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        remaining = self._config.recovery_timeout - elapsed
        return max(0.0, remaining)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state with logging and hooks.

        Args:
            new_state: The state to transition to.
        """
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0

        if self._log:
            self._log.info(
                "circuit_breaker_state_change",
                old_state=old_state.value,
                new_state=new_state.value,
            )

        for hook in self._on_state_change_hooks:
            try:
                hook(old_state, new_state)
            except Exception:
                pass  # Don't let hook errors affect circuit breaker

    def _fire_success_hooks(self) -> None:
        """Fire success hooks."""
        for hook in self._on_success_hooks:
            try:
                hook()
            except Exception:
                pass  # Don't let hook errors affect circuit breaker

    def _fire_failure_hooks(self, error: Exception) -> None:
        """Fire failure hooks.

        Args:
            error: The exception to pass to hooks.
        """
        for hook in self._on_failure_hooks:
            try:
                hook(error)
            except Exception:
                pass  # Don't let hook errors affect circuit breaker
