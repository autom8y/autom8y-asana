"""Unified retry orchestrator for autom8_asana infrastructure.

Provides coordinated retry logic across Redis, S3, and HTTP subsystems
with shared budgets and per-backend circuit breakers to prevent cascade
amplification during partial infrastructure failures.

Components:
- RetryPolicy: Protocol + DefaultRetryPolicy for retry decision-making
- RetryBudget: Sliding-window token-bucket preventing cascade amplification
- CircuitBreaker: Per-backend 3-state machine (closed/open/half-open)
- RetryOrchestrator: Facade combining policy, budget, and circuit breaker

Module: src/autom8_asana/core/retry.py

Design reference: docs/design/TDD-unified-retry-orchestrator.md
"""

from __future__ import annotations

import asyncio
import enum
import random
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import (
    Protocol,
    TypeVar,
    runtime_checkable,
)

from autom8y_log import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BackoffType(enum.Enum):
    """Retry backoff strategy types."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    IMMEDIATE = "immediate"
    NONE = "none"  # No retry (passthrough)


class Subsystem(enum.Enum):
    """Subsystem identifiers for retry budget allocation."""

    REDIS = "redis"
    S3 = "s3"
    HTTP = "http"


class CBState(enum.Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryPolicyConfig:
    """Configuration for the default retry policy.

    Attributes:
        backoff_type: Strategy for calculating delays.
        max_attempts: Maximum attempts including initial (1 = no retry).
        base_delay: Base delay in seconds for backoff calculation.
        max_delay: Maximum delay cap in seconds.
        jitter: Whether to add random jitter to delays (prevents thundering herd).
    """

    backoff_type: BackoffType = BackoffType.EXPONENTIAL
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    jitter: bool = True


@dataclass(frozen=True)
class BudgetConfig:
    """Configuration for retry budget.

    Attributes:
        per_subsystem_max: Maximum retry tokens per subsystem per window.
        global_max: Maximum retry tokens across all subsystems per window.
        window_seconds: Sliding window duration for token replenishment.
        min_tokens_for_probe: Minimum tokens reserved for circuit breaker probes.
    """

    per_subsystem_max: int = 20
    global_max: int = 50
    window_seconds: float = 60.0
    min_tokens_for_probe: int = 2


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration.

    Attributes:
        failure_threshold: Consecutive failures to trigger OPEN.
        recovery_timeout: Seconds before OPEN -> HALF_OPEN transition.
        half_open_max_probes: Successful probes needed to close circuit.
        name: Identifier for logging (e.g., "redis", "s3").
    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_probes: int = 2
    name: str = "unknown"


# ---------------------------------------------------------------------------
# RetryPolicy protocol + default implementation
# ---------------------------------------------------------------------------


@runtime_checkable
class RetryPolicy(Protocol):
    """Protocol for retry decision-making.

    Implementations determine whether a failed operation should be retried
    and how long to wait before the next attempt.
    """

    @property
    def max_attempts(self) -> int:
        """Maximum number of attempts (including the initial attempt)."""
        ...

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if the operation should be retried.

        Args:
            error: The exception that caused the failure.
            attempt: The current attempt number (1-indexed).

        Returns:
            True if retry should be attempted.
        """
        ...

    def delay_for(self, attempt: int) -> float:
        """Calculate delay in seconds before the next retry attempt.

        Args:
            attempt: The current attempt number (1-indexed).

        Returns:
            Delay in seconds. 0.0 for immediate retry.
        """
        ...


class DefaultRetryPolicy:
    """Default retry policy with configurable backoff.

    Integrates with C1 exception hierarchy:
    - Autom8Error subclasses: consults ``transient`` property
    - botocore/redis errors: classified via CACHE_TRANSIENT_ERRORS tuple
    - Unknown exceptions: not retried (fail-fast)
    """

    # Permanent AWS error codes that should NEVER be retried.
    # These indicate deterministic conditions (not-found, access denied, etc.)
    # rather than transient backend failures.
    # Mirrors S3TransportError.transient (exceptions.py:119-127) plus additional
    # deterministic codes (InvalidObjectState, NoSuchUpload, MethodNotAllowed).
    _PERMANENT_S3_ERROR_CODES: frozenset[str] = frozenset(
        {
            "NoSuchKey",
            "NoSuchBucket",
            "AccessDenied",
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
            "AllAccessDisabled",
            "InvalidBucketName",
            "InvalidObjectState",
            "NoSuchUpload",
            "MethodNotAllowed",
        }
    )

    def __init__(self, config: RetryPolicyConfig | None = None) -> None:
        self._config = config or RetryPolicyConfig()

    @property
    def max_attempts(self) -> int:
        return self._config.max_attempts

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check whether the error is transient and attempts remain."""
        if attempt >= self._config.max_attempts:
            return False
        if self._config.backoff_type == BackoffType.NONE:
            return False
        return self._is_transient(error)

    def delay_for(self, attempt: int) -> float:
        """Calculate delay using the configured backoff strategy."""
        if self._config.backoff_type == BackoffType.IMMEDIATE:
            return 0.0
        if self._config.backoff_type == BackoffType.NONE:
            return 0.0
        if self._config.backoff_type == BackoffType.LINEAR:
            delay = self._config.base_delay * attempt
        else:  # EXPONENTIAL
            delay = self._config.base_delay * (2 ** (attempt - 1))

        delay = min(delay, self._config.max_delay)

        if self._config.jitter:
            delay *= random.uniform(0.5, 1.5)

        return delay

    @staticmethod
    def _is_transient(error: Exception) -> bool:
        """Classify error transience using C1 hierarchy.

        Priority:
        1. Autom8Error.transient property (authoritative)
        2. ClientError code inspection for known-permanent AWS error codes
        3. Known transient error tuples (migration compatibility)
        4. Default: not transient (fail-fast)
        """
        from autom8_asana.core.exceptions import Autom8Error

        if isinstance(error, Autom8Error):
            return error.transient

        # Inspect ClientError error codes BEFORE the tuple-based check.
        # ClientError encompasses both transient (Throttling, InternalError)
        # and permanent (NoSuchKey, AccessDenied) errors. The isinstance
        # check below would classify ALL ClientError as transient.
        if hasattr(error, "response"):
            error_code = error.response.get("Error", {}).get("Code", "")
            if error_code in DefaultRetryPolicy._PERMANENT_S3_ERROR_CODES:
                return False

        # Migration compatibility: check error tuple membership
        from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

        if isinstance(error, CACHE_TRANSIENT_ERRORS):
            return True

        return False


# ---------------------------------------------------------------------------
# RetryBudget
# ---------------------------------------------------------------------------


class RetryBudget:
    """Shared retry budget preventing cascade amplification.

    Uses a sliding window counter (deque of timestamps) for each subsystem
    and a global counter. When either budget is exhausted, further retries
    are denied, forcing fail-fast behavior.

    Thread-safe via threading.Lock.
    """

    def __init__(self, config: BudgetConfig | None = None) -> None:
        self._config = config or BudgetConfig()
        self._lock = threading.Lock()
        # Per-subsystem deques of timestamps
        self._subsystem_tokens: dict[Subsystem, deque[float]] = {
            sub: deque() for sub in Subsystem
        }
        # Global deque of timestamps
        self._global_tokens: deque[float] = deque()
        # Track budget denials for metrics
        self._denial_count: int = 0

    def try_acquire(self, subsystem: Subsystem) -> bool:
        """Attempt to acquire a retry token.

        Returns False if subsystem budget or global budget is exhausted.
        Thread-safe.
        """
        now = time.monotonic()
        with self._lock:
            self._evict_expired(now)

            sub_count = len(self._subsystem_tokens[subsystem])
            global_count = len(self._global_tokens)

            if sub_count >= self._config.per_subsystem_max:
                self._denial_count += 1
                return False
            if global_count >= self._config.global_max:
                self._denial_count += 1
                return False

            self._subsystem_tokens[subsystem].append(now)
            self._global_tokens.append(now)
            return True

    def release(self, subsystem: Subsystem) -> None:
        """Release a retry token (on success after retry).

        Removes the most recent token for the subsystem to give the
        budget some breathing room after a successful retry.
        """
        with self._lock:
            sub_tokens = self._subsystem_tokens[subsystem]
            if sub_tokens:
                sub_tokens.pop()
            if self._global_tokens:
                self._global_tokens.pop()

    def utilization(self, subsystem: Subsystem) -> float:
        """Current utilization ratio for a subsystem (0.0 to 1.0)."""
        now = time.monotonic()
        with self._lock:
            self._evict_expired(now)
            count = len(self._subsystem_tokens[subsystem])
            max_val = self._config.per_subsystem_max
            return count / max_val if max_val > 0 else 0.0

    def global_utilization(self) -> float:
        """Current global utilization ratio (0.0 to 1.0)."""
        now = time.monotonic()
        with self._lock:
            self._evict_expired(now)
            count = len(self._global_tokens)
            max_val = self._config.global_max
            return count / max_val if max_val > 0 else 0.0

    def is_exhausted(self, subsystem: Subsystem | None = None) -> bool:
        """Check if budget is exhausted.

        Args:
            subsystem: Check specific subsystem. None checks global only.
        """
        now = time.monotonic()
        with self._lock:
            self._evict_expired(now)
            if subsystem is not None:
                sub_count = len(self._subsystem_tokens[subsystem])
                if sub_count >= self._config.per_subsystem_max:
                    return True
            global_count = len(self._global_tokens)
            return global_count >= self._config.global_max

    def reset(self) -> None:
        """Reset all budgets. For testing only."""
        with self._lock:
            for sub in Subsystem:
                self._subsystem_tokens[sub].clear()
            self._global_tokens.clear()
            self._denial_count = 0

    @property
    def denial_count(self) -> int:
        """Total number of budget denials since creation or last reset."""
        return self._denial_count

    def _evict_expired(self, now: float) -> None:
        """Remove tokens older than the sliding window. Must hold lock."""
        cutoff = now - self._config.window_seconds
        for sub in Subsystem:
            tokens = self._subsystem_tokens[sub]
            while tokens and tokens[0] < cutoff:
                tokens.popleft()
        while self._global_tokens and self._global_tokens[0] < cutoff:
            self._global_tokens.popleft()


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is rejected because the circuit breaker is open.

    Attributes:
        backend: The backend subsystem name.
        operation: The operation that was rejected.
    """

    def __init__(
        self,
        message: str,
        *,
        backend: str = "unknown",
        operation: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.backend = backend
        self.operation = operation


class CircuitBreaker:
    """Per-backend circuit breaker with budget coordination.

    Implements a 3-state machine (closed/open/half-open) that:
    - Counts consecutive failures
    - Has an explicit half-open probe state
    - Coordinates with RetryBudget for system-wide degradation
    - Emits state transition events for observability

    Thread-safe via threading.Lock.
    """

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        budget: RetryBudget | None = None,
    ) -> None:
        self._config = config or CircuitBreakerConfig()
        self._budget = budget
        self._lock = threading.Lock()
        self._state = CBState.CLOSED
        self._failure_count: int = 0
        self._success_probe_count: int = 0
        self._last_failure_time: float = 0.0
        self._opened_at: float = 0.0

    @property
    def state(self) -> CBState:
        """Current circuit breaker state, with automatic OPEN->HALF_OPEN transition."""
        with self._lock:
            return self._get_effective_state()

    def _get_effective_state(self) -> CBState:
        """Compute effective state. Must hold lock."""
        if self._state == CBState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._config.recovery_timeout:
                self._transition_to(
                    CBState.HALF_OPEN, reason="recovery_timeout_elapsed"
                )
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns True if circuit is CLOSED or HALF_OPEN (probe).
        Returns False if circuit is OPEN and recovery timeout not elapsed.
        """
        with self._lock:
            effective = self._get_effective_state()
            if effective == CBState.CLOSED:
                return True
            if effective == CBState.HALF_OPEN:
                return True
            # OPEN
            return False

    def record_success(self) -> None:
        """Record a successful operation.

        In HALF_OPEN: increments probe success counter; if enough
        probes succeed, transitions to CLOSED.
        In CLOSED: resets consecutive failure counter.
        """
        with self._lock:
            effective = self._get_effective_state()
            if effective == CBState.HALF_OPEN:
                self._success_probe_count += 1
                logger.info(
                    "circuit_breaker_probe",
                    name=self._config.name,
                    probe_number=self._success_probe_count,
                    max_probes=self._config.half_open_max_probes,
                )
                if self._success_probe_count >= self._config.half_open_max_probes:
                    self._transition_to(
                        CBState.CLOSED, reason="half_open_probes_succeeded"
                    )
            elif effective == CBState.CLOSED:
                self._failure_count = 0

    def record_failure(self, error: Exception) -> None:
        """Record a failed operation.

        In CLOSED: increments failure counter; if threshold reached,
        transitions to OPEN.
        In HALF_OPEN: transitions immediately to OPEN.
        """
        with self._lock:
            effective = self._get_effective_state()
            self._last_failure_time = time.monotonic()

            if effective == CBState.HALF_OPEN:
                self._transition_to(
                    CBState.OPEN,
                    reason=f"half_open_probe_failed: {type(error).__name__}",
                )
            elif effective == CBState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self._config.failure_threshold:
                    self._transition_to(
                        CBState.OPEN,
                        reason=f"failure_threshold_reached ({self._failure_count})",
                    )

    def force_open(self, reason: str) -> None:
        """Force circuit to OPEN state (e.g., budget exhaustion).

        Args:
            reason: Why the circuit was forced open (for logging).
        """
        with self._lock:
            self._transition_to(CBState.OPEN, reason=f"forced: {reason}")

    def reset(self) -> None:
        """Reset to initial closed state. For testing only."""
        with self._lock:
            self._state = CBState.CLOSED
            self._failure_count = 0
            self._success_probe_count = 0
            self._last_failure_time = 0.0
            self._opened_at = 0.0

    def _transition_to(self, new_state: CBState, *, reason: str) -> None:
        """Perform a state transition with logging. Must hold lock."""
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state

        logger.warning(
            "circuit_breaker_state_change",
            name=self._config.name,
            from_state=old_state.value,
            to_state=new_state.value,
            reason=reason,
            failure_count=self._failure_count,
        )

        if new_state == CBState.OPEN:
            self._opened_at = time.monotonic()
            self._success_probe_count = 0
        elif new_state == CBState.CLOSED:
            self._failure_count = 0
            self._success_probe_count = 0
        elif new_state == CBState.HALF_OPEN:
            self._success_probe_count = 0


# ---------------------------------------------------------------------------
# RetryMetrics
# ---------------------------------------------------------------------------


@dataclass
class RetryMetrics:
    """Snapshot of retry orchestrator state for health/diagnostics."""

    budget_utilization: dict[str, float] = field(default_factory=dict)
    global_budget_utilization: float = 0.0
    circuit_breaker_states: dict[str, str] = field(default_factory=dict)
    total_budget_denials: int = 0


# ---------------------------------------------------------------------------
# RetryOrchestrator
# ---------------------------------------------------------------------------


class RetryOrchestrator:
    """Facade combining retry policy, budget, and circuit breaker.

    Provides ``execute_with_retry()`` (sync) and
    ``execute_with_retry_async()`` (async) methods that:
    1. Check circuit breaker state
    2. Execute the operation
    3. On failure: check policy, check budget, wait, retry
    4. On success: record success with circuit breaker
    5. On exhaustion: record failure, potentially open circuit

    Supports both sync and async callables.
    """

    def __init__(
        self,
        policy: RetryPolicy,
        budget: RetryBudget,
        circuit_breaker: CircuitBreaker,
        subsystem: Subsystem,
    ) -> None:
        self._policy = policy
        self._budget = budget
        self._circuit_breaker = circuit_breaker
        self._subsystem = subsystem

    @property
    def policy(self) -> RetryPolicy:
        """The retry policy used by this orchestrator."""
        return self._policy

    @property
    def budget(self) -> RetryBudget:
        """The shared retry budget."""
        return self._budget

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """The circuit breaker for this subsystem."""
        return self._circuit_breaker

    @property
    def subsystem(self) -> Subsystem:
        """The subsystem this orchestrator manages."""
        return self._subsystem

    def get_metrics(self) -> RetryMetrics:
        """Snapshot of current retry state for health endpoints."""
        return RetryMetrics(
            budget_utilization={
                sub.value: self._budget.utilization(sub) for sub in Subsystem
            },
            global_budget_utilization=self._budget.global_utilization(),
            circuit_breaker_states={
                self._circuit_breaker._config.name: self._circuit_breaker.state.value,
            },
            total_budget_denials=self._budget.denial_count,
        )

    def execute_with_retry(
        self,
        operation: Callable[[], T],
        *,
        operation_name: str = "unknown",
    ) -> T:
        """Execute a synchronous operation with retry orchestration.

        Args:
            operation: Callable to execute.
            operation_name: For logging/observability.

        Returns:
            Result of the operation.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open.
            Exception: Original exception after all retries exhausted.
        """
        start_time = time.monotonic()

        for attempt in range(1, self._policy.max_attempts + 1):
            # 1. Check circuit breaker
            if not self._circuit_breaker.allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open for {self._subsystem.value}",
                    backend=self._subsystem.value,
                    operation=operation_name,
                )

            try:
                # 2. Execute operation
                result = operation()

                # 3. Record success
                self._circuit_breaker.record_success()
                if attempt > 1:
                    self._budget.release(self._subsystem)
                    duration_ms = (time.monotonic() - start_time) * 1000
                    logger.info(
                        "retry_succeeded",
                        subsystem=self._subsystem.value,
                        operation=operation_name,
                        total_attempts=attempt,
                        total_duration_ms=round(duration_ms, 2),
                    )
                return result

            except Exception as exc:  # BROAD-CATCH: enrichment -- retry loop catches any error to decide retry vs re-raise
                # 4. Check if retryable via policy (BEFORE recording CB failure)
                is_retryable = self._policy.should_retry(exc, attempt)

                # 5. Record failure with circuit breaker ONLY for transient errors.
                # Non-transient errors (NoSuchKey, AccessDenied) are application-level
                # conditions, not backend failures. They should not count toward
                # the CB failure threshold.
                if is_retryable or self._policy._is_transient(exc):
                    self._circuit_breaker.record_failure(exc)

                if not is_retryable:
                    duration_ms = (time.monotonic() - start_time) * 1000
                    logger.error(
                        "retry_exhausted",
                        subsystem=self._subsystem.value,
                        operation=operation_name,
                        total_attempts=attempt,
                        total_duration_ms=round(duration_ms, 2),
                        final_error=str(exc),
                        error_type=type(exc).__name__,
                    )
                    raise

                # 6. Check budget
                if not self._budget.try_acquire(self._subsystem):
                    logger.warning(
                        "retry_budget_exhausted",
                        subsystem=self._subsystem.value,
                        operation=operation_name,
                        utilization=self._budget.utilization(self._subsystem),
                        global_utilization=self._budget.global_utilization(),
                    )
                    raise

                # 7. Calculate delay and wait
                delay = self._policy.delay_for(attempt)
                logger.warning(
                    "retry_attempt",
                    subsystem=self._subsystem.value,
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=self._policy.max_attempts,
                    delay_seconds=round(delay, 3),
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                time.sleep(delay)

        # Defensive: should not reach here
        raise RuntimeError("Retry loop exited without result or exception")

    async def execute_with_retry_async(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        operation_name: str = "unknown",
    ) -> T:
        """Execute an async operation with retry orchestration.

        Same semantics as execute_with_retry but uses asyncio.sleep
        for delays.

        Args:
            operation: Async callable to execute.
            operation_name: For logging/observability.

        Returns:
            Result of the operation.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open.
            Exception: Original exception after all retries exhausted.
        """
        start_time = time.monotonic()

        for attempt in range(1, self._policy.max_attempts + 1):
            # 1. Check circuit breaker
            if not self._circuit_breaker.allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open for {self._subsystem.value}",
                    backend=self._subsystem.value,
                    operation=operation_name,
                )

            try:
                # 2. Execute operation
                result = await operation()

                # 3. Record success
                self._circuit_breaker.record_success()
                if attempt > 1:
                    self._budget.release(self._subsystem)
                    duration_ms = (time.monotonic() - start_time) * 1000
                    logger.info(
                        "retry_succeeded",
                        subsystem=self._subsystem.value,
                        operation=operation_name,
                        total_attempts=attempt,
                        total_duration_ms=round(duration_ms, 2),
                    )
                return result

            except Exception as exc:  # BROAD-CATCH: enrichment -- async retry loop catches any error to decide retry vs re-raise
                # 4. Check if retryable via policy (BEFORE recording CB failure)
                is_retryable = self._policy.should_retry(exc, attempt)

                # 5. Record failure with circuit breaker ONLY for transient errors.
                # Non-transient errors (NoSuchKey, AccessDenied) are application-level
                # conditions, not backend failures. They should not count toward
                # the CB failure threshold.
                if is_retryable or self._policy._is_transient(exc):
                    self._circuit_breaker.record_failure(exc)

                if not is_retryable:
                    duration_ms = (time.monotonic() - start_time) * 1000
                    logger.error(
                        "retry_exhausted",
                        subsystem=self._subsystem.value,
                        operation=operation_name,
                        total_attempts=attempt,
                        total_duration_ms=round(duration_ms, 2),
                        final_error=str(exc),
                        error_type=type(exc).__name__,
                    )
                    raise

                # 6. Check budget
                if not self._budget.try_acquire(self._subsystem):
                    logger.warning(
                        "retry_budget_exhausted",
                        subsystem=self._subsystem.value,
                        operation=operation_name,
                        utilization=self._budget.utilization(self._subsystem),
                        global_utilization=self._budget.global_utilization(),
                    )
                    raise

                # 7. Calculate delay and wait
                delay = self._policy.delay_for(attempt)
                logger.warning(
                    "retry_attempt",
                    subsystem=self._subsystem.value,
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=self._policy.max_attempts,
                    delay_seconds=round(delay, 3),
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                await asyncio.sleep(delay)

        # Defensive: should not reach here
        raise RuntimeError("Retry loop exited without result or exception")
