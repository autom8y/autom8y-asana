"""Circuit breaker for per-project failure isolation.

Per TDD-DATAFRAME-CACHE-001: Circuit breaker with per-project granularity.

States:
- CLOSED: Normal operation, requests allowed
- OPEN: Failing, requests rejected until reset timeout
- HALF_OPEN: Testing if recovered, allows one request through
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict

from autom8y_log import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class ProjectCircuit:
    """Circuit state for a single project."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure: datetime | None = None
    last_success: datetime | None = None


@dataclass
class CircuitBreaker:
    """Circuit breaker with per-project granularity.

    Per TDD-DATAFRAME-CACHE-001:
    - Per-project circuit state (isolated failures)
    - Opens after threshold consecutive failures
    - Half-open after reset timeout to test recovery
    - Closes on successful operation

    State Transitions:
    - CLOSED -> OPEN: After failure_threshold failures
    - OPEN -> HALF_OPEN: After reset_timeout_seconds
    - HALF_OPEN -> CLOSED: On success
    - HALF_OPEN -> OPEN: On failure

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        reset_timeout_seconds: Time before trying half-open state.
        success_threshold: Successes needed in half-open to close.

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=3)
        >>>
        >>> # Record failures
        >>> breaker.record_failure("project-123")  # count=1
        >>> breaker.record_failure("project-123")  # count=2
        >>> breaker.record_failure("project-123")  # count=3, opens
        >>>
        >>> # Check state
        >>> breaker.is_open("project-123")  # True
        >>>
        >>> # After reset timeout, transitions to half-open
        >>> breaker.is_open("project-123")  # False (half-open allows)
        >>>
        >>> # On success, closes
        >>> breaker.close("project-123")
    """

    failure_threshold: int = 3
    reset_timeout_seconds: int = 60
    success_threshold: int = 1

    # Internal state
    _circuits: Dict[str, ProjectCircuit] = field(default_factory=dict, init=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize statistics."""
        self._stats = {
            "failures_recorded": 0,
            "successes_recorded": 0,
            "circuits_opened": 0,
            "circuits_closed": 0,
            "requests_rejected": 0,
        }

    def is_open(self, project_gid: str) -> bool:
        """Check if circuit is open (rejecting requests).

        Also handles state transitions:
        - OPEN -> HALF_OPEN after reset timeout

        Args:
            project_gid: Project to check.

        Returns:
            True if requests should be rejected.
        """
        circuit = self._circuits.get(project_gid)

        if circuit is None:
            return False

        if circuit.state == CircuitState.CLOSED:
            return False

        if circuit.state == CircuitState.HALF_OPEN:
            return False  # Allow test request

        # OPEN state - check if reset timeout elapsed
        if circuit.last_failure is not None:
            elapsed = datetime.now(timezone.utc) - circuit.last_failure
            if elapsed.total_seconds() >= self.reset_timeout_seconds:
                # Transition to half-open
                circuit.state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    extra={"project_gid": project_gid},
                )
                return False

        # Still open
        self._stats["requests_rejected"] += 1
        return True

    def record_failure(self, project_gid: str) -> None:
        """Record a failure for project.

        Increments failure count and opens circuit if threshold reached.

        Args:
            project_gid: Project that failed.
        """
        self._stats["failures_recorded"] += 1

        if project_gid not in self._circuits:
            self._circuits[project_gid] = ProjectCircuit()

        circuit = self._circuits[project_gid]
        circuit.failure_count += 1
        circuit.last_failure = datetime.now(timezone.utc)

        # Check if should open circuit
        if (
            circuit.state != CircuitState.OPEN
            and circuit.failure_count >= self.failure_threshold
        ):
            circuit.state = CircuitState.OPEN
            self._stats["circuits_opened"] += 1
            logger.warning(
                "circuit_breaker_opened",
                extra={
                    "project_gid": project_gid,
                    "failure_count": circuit.failure_count,
                },
            )

        # In half-open, a failure reopens
        elif circuit.state == CircuitState.HALF_OPEN:
            circuit.state = CircuitState.OPEN
            logger.info(
                "circuit_breaker_reopened",
                extra={"project_gid": project_gid},
            )

    def close(self, project_gid: str) -> None:
        """Close circuit (record success).

        Resets failure count and closes circuit if in half-open state.

        Args:
            project_gid: Project that succeeded.
        """
        self._stats["successes_recorded"] += 1

        if project_gid not in self._circuits:
            return

        circuit = self._circuits[project_gid]
        circuit.last_success = datetime.now(timezone.utc)

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.state = CircuitState.CLOSED
            circuit.failure_count = 0
            self._stats["circuits_closed"] += 1
            logger.info(
                "circuit_breaker_closed",
                extra={"project_gid": project_gid},
            )

        elif circuit.state == CircuitState.CLOSED:
            circuit.failure_count = 0

    def get_state(self, project_gid: str) -> CircuitState:
        """Get current circuit state for project.

        Args:
            project_gid: Project to check.

        Returns:
            CircuitState for the project (CLOSED if no circuit exists).
        """
        circuit = self._circuits.get(project_gid)
        return circuit.state if circuit else CircuitState.CLOSED

    def reset(self, project_gid: str) -> None:
        """Reset circuit to closed state.

        Removes all state for the project.

        Args:
            project_gid: Project to reset.
        """
        if project_gid in self._circuits:
            del self._circuits[project_gid]

    def reset_all(self) -> None:
        """Reset all circuits to closed state."""
        self._circuits.clear()

    def get_stats(self) -> dict[str, int]:
        """Get breaker statistics."""
        return {
            **self._stats,
            "open_circuits": sum(
                1 for c in self._circuits.values() if c.state == CircuitState.OPEN
            ),
            "half_open_circuits": sum(
                1
                for c in self._circuits.values()
                if c.state == CircuitState.HALF_OPEN
            ),
        }

    def get_open_circuits(self) -> list[str]:
        """Get list of project GIDs with open circuits.

        Returns:
            List of project GIDs in OPEN state.
        """
        return [
            gid
            for gid, circuit in self._circuits.items()
            if circuit.state == CircuitState.OPEN
        ]
