"""Unit tests for CircuitBreaker.

Per TDD-DATAFRAME-CACHE-001: Tests for circuit states, failure threshold,
reset timeout, and per-project isolation.
"""

import time

from autom8_asana.cache.dataframe.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self) -> None:
        """Initial state for project is CLOSED."""
        breaker = CircuitBreaker()

        state = breaker.get_state("proj-1")

        assert state == CircuitState.CLOSED
        assert not breaker.is_open("proj-1")

    def test_failure_increments_count(self) -> None:
        """Recording failure increments failure count."""
        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        assert not breaker.is_open("proj-1")  # Still below threshold
        assert breaker.get_state("proj-1") == CircuitState.CLOSED

    def test_opens_at_threshold(self) -> None:
        """Circuit opens when failure threshold reached."""
        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        assert breaker.is_open("proj-1")
        assert breaker.get_state("proj-1") == CircuitState.OPEN

    def test_is_open_rejects_requests(self) -> None:
        """Open circuit rejects requests."""
        breaker = CircuitBreaker(failure_threshold=2)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        # Should be open and reject
        assert breaker.is_open("proj-1")

        # Stats should track rejection
        stats = breaker.get_stats()
        assert stats["circuits_opened"] == 1
        # First is_open already incremented requests_rejected
        assert stats["requests_rejected"] == 1

        # Second call should also increment
        assert breaker.is_open("proj-1")
        stats = breaker.get_stats()
        assert stats["requests_rejected"] == 2

    def test_half_open_after_timeout(self) -> None:
        """Circuit transitions to HALF_OPEN after reset timeout."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=1)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        assert breaker.is_open("proj-1")

        # Simulate time passing
        circuit = breaker._circuits["proj-1"]
        circuit.last_failure = time.monotonic() - 2

        # Should now be half-open
        assert not breaker.is_open("proj-1")
        assert breaker.get_state("proj-1") == CircuitState.HALF_OPEN

    def test_closes_on_success_from_half_open(self) -> None:
        """Circuit closes when success recorded in HALF_OPEN state."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=1)

        # Open the circuit
        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        # Move to half-open
        circuit = breaker._circuits["proj-1"]
        circuit.last_failure = time.monotonic() - 2
        breaker.is_open("proj-1")  # Triggers half-open transition

        # Record success
        breaker.close("proj-1")

        assert breaker.get_state("proj-1") == CircuitState.CLOSED
        assert not breaker.is_open("proj-1")

    def test_reopens_on_failure_from_half_open(self) -> None:
        """Circuit reopens when failure recorded in HALF_OPEN state."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=1)

        # Open the circuit
        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        # Move to half-open
        circuit = breaker._circuits["proj-1"]
        circuit.last_failure = time.monotonic() - 2
        breaker.is_open("proj-1")  # Triggers half-open transition

        # Record another failure
        breaker.record_failure("proj-1")

        assert breaker.get_state("proj-1") == CircuitState.OPEN

    def test_close_resets_failure_count(self) -> None:
        """Closing circuit resets failure count."""
        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        # Close before threshold
        breaker.close("proj-1")

        # Should need 3 more failures to open
        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        assert not breaker.is_open("proj-1")

        breaker.record_failure("proj-1")
        assert breaker.is_open("proj-1")

    def test_per_project_isolation(self) -> None:
        """Different projects have independent circuits."""
        breaker = CircuitBreaker(failure_threshold=2)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        breaker.record_failure("proj-2")

        assert breaker.is_open("proj-1")
        assert not breaker.is_open("proj-2")

    def test_reset_removes_state(self) -> None:
        """Reset removes all state for project."""
        breaker = CircuitBreaker(failure_threshold=2)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")

        breaker.reset("proj-1")

        assert breaker.get_state("proj-1") == CircuitState.CLOSED
        assert not breaker.is_open("proj-1")

    def test_reset_all(self) -> None:
        """Reset all removes all circuits."""
        breaker = CircuitBreaker(failure_threshold=2)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")
        breaker.record_failure("proj-2")
        breaker.record_failure("proj-2")

        breaker.reset_all()

        assert not breaker.is_open("proj-1")
        assert not breaker.is_open("proj-2")

    def test_get_open_circuits(self) -> None:
        """Get list of open circuits."""
        breaker = CircuitBreaker(failure_threshold=2)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")
        breaker.record_failure("proj-2")

        open_circuits = breaker.get_open_circuits()

        assert "proj-1" in open_circuits
        assert "proj-2" not in open_circuits

    def test_stats(self) -> None:
        """Stats track operations correctly."""
        breaker = CircuitBreaker(failure_threshold=2)

        breaker.record_failure("proj-1")
        breaker.record_failure("proj-1")  # Opens
        breaker.close("proj-1")  # Success recorded (but circuit stays open
        # since it wasn't half-open)

        stats = breaker.get_stats()

        assert stats["failures_recorded"] == 2
        assert stats["successes_recorded"] == 1
        assert stats["circuits_opened"] == 1
