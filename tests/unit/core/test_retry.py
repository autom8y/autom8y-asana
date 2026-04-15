"""Tests for the unified retry orchestrator.

Verifies RetryPolicy, RetryBudget, CircuitBreaker, and RetryOrchestrator
components defined in core/retry.py.

Design reference: docs/design/TDD-unified-retry-orchestrator.md
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from botocore.exceptions import ClientError

from autom8_asana.core.errors import (
    CacheError,
    RedisTransportError,
    S3TransportError,
    TransportError,
)
from autom8_asana.core.retry import (
    BackoffType,
    BudgetConfig,
    CBState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    DefaultRetryPolicy,
    RetryBudget,
    RetryMetrics,
    RetryOrchestrator,
    RetryPolicyConfig,
    Subsystem,
)

# ---------------------------------------------------------------------------
# DefaultRetryPolicy tests
# ---------------------------------------------------------------------------


class TestDefaultRetryPolicy:
    """Test the default retry policy with C1 exception integration."""

    def test_max_attempts_default(self) -> None:
        policy = DefaultRetryPolicy()
        assert policy.max_attempts == 3

    def test_max_attempts_custom(self) -> None:
        config = RetryPolicyConfig(max_attempts=5)
        policy = DefaultRetryPolicy(config)
        assert policy.max_attempts == 5

    # --- Transient classification ---

    def test_transient_autom8_error_retried(self) -> None:
        """Transient Autom8Error subclasses should be retried."""
        policy = DefaultRetryPolicy()
        err = RedisTransportError("timeout", operation="get")
        assert policy.should_retry(err, attempt=1) is True

    def test_transient_s3_error_retried(self) -> None:
        err = S3TransportError("throttle", error_code="SlowDown")
        policy = DefaultRetryPolicy()
        assert policy.should_retry(err, attempt=1) is True

    def test_permanent_autom8_error_not_retried(self) -> None:
        """Permanent Autom8Error subclasses should not be retried."""
        policy = DefaultRetryPolicy()
        err = CacheError("bad json")
        assert policy.should_retry(err, attempt=1) is False

    def test_permanent_s3_nosuchkey_not_retried(self) -> None:
        err = S3TransportError("not found", error_code="NoSuchKey")
        policy = DefaultRetryPolicy()
        assert policy.should_retry(err, attempt=1) is False

    def test_permanent_s3_access_denied_not_retried(self) -> None:
        err = S3TransportError("denied", error_code="AccessDenied")
        policy = DefaultRetryPolicy()
        assert policy.should_retry(err, attempt=1) is False

    def test_unknown_exception_not_retried(self) -> None:
        """Non-domain exceptions default to not retried."""
        policy = DefaultRetryPolicy()
        err = ValueError("bad input")
        assert policy.should_retry(err, attempt=1) is False

    def test_connection_error_retried_via_tuple(self) -> None:
        """ConnectionError is in CACHE_TRANSIENT_ERRORS tuple."""
        policy = DefaultRetryPolicy()
        err = ConnectionError("refused")
        assert policy.should_retry(err, attempt=1) is True

    def test_timeout_error_retried_via_tuple(self) -> None:
        """TimeoutError is in CACHE_TRANSIENT_ERRORS tuple."""
        policy = DefaultRetryPolicy()
        err = TimeoutError("timed out")
        assert policy.should_retry(err, attempt=1) is True

    def test_max_attempts_honored(self) -> None:
        """Should not retry when attempt >= max_attempts."""
        policy = DefaultRetryPolicy(RetryPolicyConfig(max_attempts=3))
        err = TransportError("fail")
        assert policy.should_retry(err, attempt=3) is False
        assert policy.should_retry(err, attempt=4) is False

    def test_backoff_none_never_retries(self) -> None:
        config = RetryPolicyConfig(backoff_type=BackoffType.NONE, max_attempts=5)
        policy = DefaultRetryPolicy(config)
        err = TransportError("fail")
        assert policy.should_retry(err, attempt=1) is False

    # --- Delay calculation ---

    def test_exponential_backoff_delay(self) -> None:
        config = RetryPolicyConfig(
            backoff_type=BackoffType.EXPONENTIAL,
            base_delay=0.5,
            jitter=False,
        )
        policy = DefaultRetryPolicy(config)
        assert policy.delay_for(1) == pytest.approx(0.5)  # 0.5 * 2^0
        assert policy.delay_for(2) == pytest.approx(1.0)  # 0.5 * 2^1
        assert policy.delay_for(3) == pytest.approx(2.0)  # 0.5 * 2^2

    def test_linear_backoff_delay(self) -> None:
        config = RetryPolicyConfig(
            backoff_type=BackoffType.LINEAR,
            base_delay=1.0,
            jitter=False,
        )
        policy = DefaultRetryPolicy(config)
        assert policy.delay_for(1) == pytest.approx(1.0)
        assert policy.delay_for(2) == pytest.approx(2.0)
        assert policy.delay_for(3) == pytest.approx(3.0)

    def test_immediate_backoff_delay_zero(self) -> None:
        config = RetryPolicyConfig(backoff_type=BackoffType.IMMEDIATE)
        policy = DefaultRetryPolicy(config)
        assert policy.delay_for(1) == 0.0
        assert policy.delay_for(5) == 0.0

    def test_none_backoff_delay_zero(self) -> None:
        config = RetryPolicyConfig(backoff_type=BackoffType.NONE)
        policy = DefaultRetryPolicy(config)
        assert policy.delay_for(1) == 0.0

    def test_max_delay_cap(self) -> None:
        config = RetryPolicyConfig(
            backoff_type=BackoffType.EXPONENTIAL,
            base_delay=10.0,
            max_delay=5.0,
            jitter=False,
        )
        policy = DefaultRetryPolicy(config)
        # 10.0 * 2^0 = 10.0, capped at 5.0
        assert policy.delay_for(1) == pytest.approx(5.0)

    def test_jitter_within_bounds(self) -> None:
        """Jitter should produce delay in [0.5*base, 1.5*base] range."""
        config = RetryPolicyConfig(
            backoff_type=BackoffType.EXPONENTIAL,
            base_delay=1.0,
            max_delay=100.0,
            jitter=True,
        )
        policy = DefaultRetryPolicy(config)
        delays = [policy.delay_for(1) for _ in range(100)]
        # attempt=1: base * 2^0 = 1.0, with jitter: [0.5, 1.5]
        assert all(0.5 <= d <= 1.5 for d in delays), f"Out of bounds: {min(delays)}-{max(delays)}"
        # Should have some variance (not all identical)
        assert len(set(round(d, 6) for d in delays)) > 1


# ---------------------------------------------------------------------------
# RetryBudget tests
# ---------------------------------------------------------------------------


class TestRetryBudget:
    """Test the sliding-window token-bucket retry budget."""

    def test_acquire_within_limit(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=5, global_max=10))
        for _ in range(5):
            assert budget.try_acquire(Subsystem.S3) is True

    def test_acquire_denied_at_subsystem_limit(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=3, global_max=100))
        for _ in range(3):
            assert budget.try_acquire(Subsystem.REDIS) is True
        assert budget.try_acquire(Subsystem.REDIS) is False

    def test_acquire_denied_at_global_limit(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=5))
        for _ in range(3):
            assert budget.try_acquire(Subsystem.S3) is True
        for _ in range(2):
            assert budget.try_acquire(Subsystem.REDIS) is True
        # Global limit reached (5)
        assert budget.try_acquire(Subsystem.HTTP) is False

    def test_per_subsystem_isolation(self) -> None:
        """Each subsystem has its own independent budget."""
        budget = RetryBudget(BudgetConfig(per_subsystem_max=2, global_max=100))
        assert budget.try_acquire(Subsystem.S3) is True
        assert budget.try_acquire(Subsystem.S3) is True
        assert budget.try_acquire(Subsystem.S3) is False
        # Redis should still have budget
        assert budget.try_acquire(Subsystem.REDIS) is True

    def test_window_expiration_replenishes(self) -> None:
        """Tokens older than window_seconds are evicted."""
        budget = RetryBudget(
            BudgetConfig(
                per_subsystem_max=2,
                global_max=10,
                window_seconds=0.1,  # 100ms window for testing
            )
        )
        assert budget.try_acquire(Subsystem.S3) is True
        assert budget.try_acquire(Subsystem.S3) is True
        assert budget.try_acquire(Subsystem.S3) is False

        # Wait for window to expire
        time.sleep(0.15)
        assert budget.try_acquire(Subsystem.S3) is True

    def test_utilization_calculation(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=10, global_max=100))
        assert budget.utilization(Subsystem.S3) == pytest.approx(0.0)
        for _ in range(5):
            budget.try_acquire(Subsystem.S3)
        assert budget.utilization(Subsystem.S3) == pytest.approx(0.5)

    def test_global_utilization(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=10))
        for _ in range(3):
            budget.try_acquire(Subsystem.S3)
        for _ in range(2):
            budget.try_acquire(Subsystem.REDIS)
        assert budget.global_utilization() == pytest.approx(0.5)

    def test_is_exhausted_subsystem(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=2, global_max=100))
        assert budget.is_exhausted(Subsystem.S3) is False
        budget.try_acquire(Subsystem.S3)
        budget.try_acquire(Subsystem.S3)
        assert budget.is_exhausted(Subsystem.S3) is True
        assert budget.is_exhausted(Subsystem.REDIS) is False

    def test_is_exhausted_global(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=3))
        for _ in range(3):
            budget.try_acquire(Subsystem.S3)
        assert budget.is_exhausted() is True

    def test_release_frees_token(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=2, global_max=10))
        budget.try_acquire(Subsystem.S3)
        budget.try_acquire(Subsystem.S3)
        assert budget.try_acquire(Subsystem.S3) is False
        budget.release(Subsystem.S3)
        assert budget.try_acquire(Subsystem.S3) is True

    def test_reset_clears_all(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=2, global_max=10))
        budget.try_acquire(Subsystem.S3)
        budget.try_acquire(Subsystem.S3)
        budget.reset()
        assert budget.utilization(Subsystem.S3) == pytest.approx(0.0)
        assert budget.try_acquire(Subsystem.S3) is True

    def test_denial_count_tracked(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=1, global_max=10))
        budget.try_acquire(Subsystem.S3)
        budget.try_acquire(Subsystem.S3)  # denied
        budget.try_acquire(Subsystem.S3)  # denied
        assert budget.denial_count == 2

    def test_thread_safety(self) -> None:
        """Concurrent access should not corrupt budget state."""
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=200))
        results: list[bool] = []
        barrier = threading.Barrier(10)

        def acquire_many() -> None:
            barrier.wait()
            for _ in range(20):
                results.append(budget.try_acquire(Subsystem.S3))

        threads = [threading.Thread(target=acquire_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 10 threads * 20 acquires = 200 attempts, subsystem limit 100
        acquired = sum(1 for r in results if r)
        assert acquired == 100
        # All 200 should have returned a boolean
        assert len(results) == 200


# ---------------------------------------------------------------------------
# CircuitBreaker tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Test the 3-state circuit breaker."""

    def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == CBState.CLOSED

    def test_allow_request_when_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.allow_request() is True

    def test_closed_to_open_after_threshold(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=3, name="test")
        cb = CircuitBreaker(config=config)
        err = TransportError("fail")

        cb.record_failure(err)
        assert cb.state == CBState.CLOSED
        cb.record_failure(err)
        assert cb.state == CBState.CLOSED
        cb.record_failure(err)
        assert cb.state == CBState.OPEN

    def test_open_rejects_requests(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=999.0, name="test")
        cb = CircuitBreaker(config=config)
        cb.record_failure(TransportError("fail"))
        assert cb.state == CBState.OPEN
        assert cb.allow_request() is False

    def test_open_to_half_open_after_timeout(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, name="test")
        cb = CircuitBreaker(config=config)
        cb.record_failure(TransportError("fail"))
        assert cb.state == CBState.OPEN

        time.sleep(0.15)
        assert cb.state == CBState.HALF_OPEN
        assert cb.allow_request() is True

    def test_half_open_to_closed_after_probes(self) -> None:
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_max_probes=2,
            name="test",
        )
        cb = CircuitBreaker(config=config)
        cb.record_failure(TransportError("fail"))
        time.sleep(0.1)
        assert cb.state == CBState.HALF_OPEN

        cb.record_success()
        assert cb.state == CBState.HALF_OPEN  # 1 probe, need 2
        cb.record_success()
        assert cb.state == CBState.CLOSED

    def test_half_open_to_open_on_probe_failure(self) -> None:
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_max_probes=3,
            name="test",
        )
        cb = CircuitBreaker(config=config)
        cb.record_failure(TransportError("fail"))
        time.sleep(0.1)
        assert cb.state == CBState.HALF_OPEN

        cb.record_failure(TransportError("probe failed"))
        assert cb.state == CBState.OPEN

    def test_success_resets_failure_count(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=3, name="test")
        cb = CircuitBreaker(config=config)
        err = TransportError("fail")

        cb.record_failure(err)
        cb.record_failure(err)
        # 2 failures, not at threshold yet
        cb.record_success()
        # Reset failure count to 0

        cb.record_failure(err)
        cb.record_failure(err)
        # Only 2 consecutive failures, still closed
        assert cb.state == CBState.CLOSED

    def test_force_open(self) -> None:
        cb = CircuitBreaker(config=CircuitBreakerConfig(name="test"))
        cb.force_open("budget exhausted")
        assert cb.state == CBState.OPEN
        assert cb.allow_request() is False

    def test_reset(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, name="test")
        cb = CircuitBreaker(config=config)
        cb.record_failure(TransportError("fail"))
        assert cb.state == CBState.OPEN
        cb.reset()
        assert cb.state == CBState.CLOSED
        assert cb.allow_request() is True

    def test_thread_safety(self) -> None:
        """Concurrent record_failure should not corrupt state."""
        config = CircuitBreakerConfig(failure_threshold=50, name="test")
        cb = CircuitBreaker(config=config)
        barrier = threading.Barrier(10)

        def record_failures() -> None:
            barrier.wait()
            for _ in range(10):
                cb.record_failure(TransportError("fail"))

        threads = [threading.Thread(target=record_failures) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 10 threads * 10 failures = 100, threshold is 50
        assert cb.state == CBState.OPEN


# ---------------------------------------------------------------------------
# CircuitBreakerOpenError tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerOpenError:
    """Test CircuitBreakerOpenError attributes."""

    def test_attributes(self) -> None:
        err = CircuitBreakerOpenError("circuit open", backend="s3", operation="get_object")
        assert str(err) == "circuit open"
        assert err.backend == "s3"
        assert err.operation == "get_object"

    def test_default_attributes(self) -> None:
        err = CircuitBreakerOpenError("open")
        assert err.backend == "unknown"
        assert err.operation == "unknown"

    def test_is_exception(self) -> None:
        assert issubclass(CircuitBreakerOpenError, Exception)


# ---------------------------------------------------------------------------
# RetryOrchestrator sync tests
# ---------------------------------------------------------------------------


class TestRetryOrchestratorSync:
    """Test synchronous execute_with_retry."""

    def _make_orchestrator(
        self,
        *,
        max_attempts: int = 3,
        backoff_type: BackoffType = BackoffType.IMMEDIATE,
        budget_config: BudgetConfig | None = None,
        cb_config: CircuitBreakerConfig | None = None,
        subsystem: Subsystem = Subsystem.S3,
    ) -> RetryOrchestrator:
        policy = DefaultRetryPolicy(
            RetryPolicyConfig(
                backoff_type=backoff_type,
                max_attempts=max_attempts,
                jitter=False,
            )
        )
        budget = RetryBudget(budget_config or BudgetConfig())
        cb = CircuitBreaker(config=cb_config or CircuitBreakerConfig(name="test"))
        return RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=cb,
            subsystem=subsystem,
        )

    def test_happy_path_no_retry(self) -> None:
        orch = self._make_orchestrator()
        result = orch.execute_with_retry(lambda: 42, operation_name="test")
        assert result == 42

    def test_retry_on_transient_error(self) -> None:
        orch = self._make_orchestrator()
        call_count = 0

        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransportError("timeout")
            return "success"

        result = orch.execute_with_retry(flaky, operation_name="flaky_op")
        assert result == "success"
        assert call_count == 3

    def test_permanent_error_no_retry(self) -> None:
        orch = self._make_orchestrator()
        call_count = 0

        def permanent_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise CacheError("bad json")

        with pytest.raises(CacheError):
            orch.execute_with_retry(permanent_fail, operation_name="perm")

        assert call_count == 1  # No retry attempted

    def test_all_retries_exhausted(self) -> None:
        orch = self._make_orchestrator(max_attempts=3)
        call_count = 0

        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise TransportError("always fails")

        with pytest.raises(TransportError, match="always fails"):
            orch.execute_with_retry(always_fail, operation_name="fail")

        assert call_count == 3

    def test_budget_denial_stops_retry(self) -> None:
        budget_config = BudgetConfig(per_subsystem_max=0, global_max=0)
        orch = self._make_orchestrator(budget_config=budget_config)
        call_count = 0

        def fail_once() -> str:
            nonlocal call_count
            call_count += 1
            raise TransportError("timeout")

        with pytest.raises(TransportError):
            orch.execute_with_retry(fail_once, operation_name="budget_test")

        assert call_count == 1  # No retry because budget denied

    def test_circuit_breaker_open_raises(self) -> None:
        cb_config = CircuitBreakerConfig(failure_threshold=1, name="test")
        orch = self._make_orchestrator(cb_config=cb_config)

        # Trip the circuit breaker
        orch.circuit_breaker.force_open("test")

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            orch.execute_with_retry(lambda: 42, operation_name="blocked")

        assert exc_info.value.backend == "s3"
        assert exc_info.value.operation == "blocked"

    def test_properties(self) -> None:
        orch = self._make_orchestrator(subsystem=Subsystem.REDIS)
        assert orch.subsystem == Subsystem.REDIS
        assert isinstance(orch.policy, DefaultRetryPolicy)
        assert isinstance(orch.budget, RetryBudget)
        assert isinstance(orch.circuit_breaker, CircuitBreaker)


# ---------------------------------------------------------------------------
# RetryOrchestrator async tests
# ---------------------------------------------------------------------------


class TestRetryOrchestratorAsync:
    """Test async execute_with_retry_async."""

    def _make_orchestrator(
        self,
        *,
        max_attempts: int = 3,
        backoff_type: BackoffType = BackoffType.IMMEDIATE,
        budget_config: BudgetConfig | None = None,
        cb_config: CircuitBreakerConfig | None = None,
    ) -> RetryOrchestrator:
        policy = DefaultRetryPolicy(
            RetryPolicyConfig(
                backoff_type=backoff_type,
                max_attempts=max_attempts,
                jitter=False,
            )
        )
        budget = RetryBudget(budget_config or BudgetConfig())
        cb = CircuitBreaker(config=cb_config or CircuitBreakerConfig(name="test"))
        return RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=cb,
            subsystem=Subsystem.S3,
        )

    async def test_happy_path_async(self) -> None:
        orch = self._make_orchestrator()

        async def op() -> int:
            return 42

        result = await orch.execute_with_retry_async(op, operation_name="test")
        assert result == 42

    async def test_retry_on_transient_error_async(self) -> None:
        orch = self._make_orchestrator()
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise S3TransportError("throttle", error_code="SlowDown")
            return "success"

        result = await orch.execute_with_retry_async(flaky, operation_name="flaky")
        assert result == "success"
        assert call_count == 3

    async def test_permanent_error_no_retry_async(self) -> None:
        orch = self._make_orchestrator()
        call_count = 0

        async def perm_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise CacheError("quota")

        with pytest.raises(CacheError):
            await orch.execute_with_retry_async(perm_fail, operation_name="perm")

        assert call_count == 1

    async def test_all_retries_exhausted_async(self) -> None:
        orch = self._make_orchestrator(max_attempts=2)
        call_count = 0

        async def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise RedisTransportError("down")

        with pytest.raises(RedisTransportError):
            await orch.execute_with_retry_async(always_fail, operation_name="fail")

        assert call_count == 2

    async def test_budget_denial_async(self) -> None:
        budget_config = BudgetConfig(per_subsystem_max=0, global_max=0)
        orch = self._make_orchestrator(budget_config=budget_config)
        call_count = 0

        async def fail() -> str:
            nonlocal call_count
            call_count += 1
            raise TransportError("timeout")

        with pytest.raises(TransportError):
            await orch.execute_with_retry_async(fail, operation_name="budget")

        assert call_count == 1

    async def test_circuit_breaker_open_async(self) -> None:
        orch = self._make_orchestrator()
        orch.circuit_breaker.force_open("test")

        async def op() -> int:
            return 42

        with pytest.raises(CircuitBreakerOpenError):
            await orch.execute_with_retry_async(op, operation_name="blocked")


# ---------------------------------------------------------------------------
# Integration / end-to-end tests
# ---------------------------------------------------------------------------


class TestRetryOrchestratorIntegration:
    """End-to-end tests combining policy, budget, and circuit breaker."""

    def test_budget_exhaustion_during_retry_sequence(self) -> None:
        """Budget runs out mid-retry-sequence."""
        budget = RetryBudget(BudgetConfig(per_subsystem_max=1, global_max=10))
        policy = DefaultRetryPolicy(
            RetryPolicyConfig(
                backoff_type=BackoffType.IMMEDIATE,
                max_attempts=5,
                jitter=False,
            )
        )
        cb = CircuitBreaker(config=CircuitBreakerConfig(name="test"))
        orch = RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=cb,
            subsystem=Subsystem.S3,
        )

        call_count = 0

        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise TransportError("fail")

        with pytest.raises(TransportError):
            orch.execute_with_retry(always_fail, operation_name="limited")

        # First call fails, budget allows 1 retry, second call fails,
        # budget denies third retry. Total calls = 2.
        assert call_count == 2

    def test_circuit_breaker_opens_during_retries(self) -> None:
        """Circuit breaker trips mid-retry due to accumulated failures."""
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=100))
        policy = DefaultRetryPolicy(
            RetryPolicyConfig(
                backoff_type=BackoffType.IMMEDIATE,
                max_attempts=10,
                jitter=False,
            )
        )
        cb = CircuitBreaker(
            config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=999.0,
                name="test",
            )
        )
        orch = RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=cb,
            subsystem=Subsystem.S3,
        )

        call_count = 0

        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise TransportError("fail")

        # After 3 failures, CB opens. On attempt 4, allow_request() returns False.
        with pytest.raises(CircuitBreakerOpenError):
            orch.execute_with_retry(always_fail, operation_name="cb_trip")

        assert call_count == 3

    def test_shared_budget_across_subsystems(self) -> None:
        """Two orchestrators share a budget; one exhausts the global cap."""
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=2))
        policy = DefaultRetryPolicy(
            RetryPolicyConfig(
                backoff_type=BackoffType.IMMEDIATE,
                max_attempts=10,
                jitter=False,
            )
        )

        s3_orch = RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=CircuitBreaker(config=CircuitBreakerConfig(name="s3")),
            subsystem=Subsystem.S3,
        )

        redis_orch = RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=CircuitBreaker(config=CircuitBreakerConfig(name="redis")),
            subsystem=Subsystem.REDIS,
        )

        # S3 orchestrator consumes 2 tokens from global budget
        with pytest.raises(TransportError):
            s3_orch.execute_with_retry(
                lambda: (_ for _ in ()).throw(TransportError("s3 fail")),
                operation_name="s3_op",
            )

        # Redis orchestrator should be denied by global budget
        redis_call_count = 0

        def redis_fail() -> str:
            nonlocal redis_call_count
            redis_call_count += 1
            raise TransportError("redis fail")

        with pytest.raises(TransportError):
            redis_orch.execute_with_retry(redis_fail, operation_name="redis_op")

        # Redis gets 1 call (initial), then budget denied on retry
        assert redis_call_count == 1

    async def test_concurrent_async_retries(self) -> None:
        """Multiple concurrent async operations share budget correctly."""
        budget = RetryBudget(BudgetConfig(per_subsystem_max=5, global_max=5))
        policy = DefaultRetryPolicy(
            RetryPolicyConfig(
                backoff_type=BackoffType.IMMEDIATE,
                max_attempts=10,
                jitter=False,
            )
        )

        orchestrators = [
            RetryOrchestrator(
                policy=policy,
                budget=budget,
                circuit_breaker=CircuitBreaker(config=CircuitBreakerConfig(name=f"s3_{i}")),
                subsystem=Subsystem.S3,
            )
            for i in range(5)
        ]

        call_counts = [0] * 5

        async def make_failing_op(idx: int):
            async def op() -> str:
                call_counts[idx] += 1
                raise TransportError("fail")

            return op

        async def run_one(idx: int) -> None:
            op = await make_failing_op(idx)
            with pytest.raises((TransportError, CircuitBreakerOpenError)):
                await orchestrators[idx].execute_with_retry_async(op, operation_name=f"op_{idx}")

        await asyncio.gather(*[run_one(i) for i in range(5)])

        # Total calls across all orchestrators should be bounded:
        # 5 initial calls + at most 5 retries (global budget)
        total_calls = sum(call_counts)
        assert total_calls <= 10


# ---------------------------------------------------------------------------
# RetryMetrics tests
# ---------------------------------------------------------------------------


class TestRetryMetrics:
    """Test metrics snapshot."""

    def test_get_metrics(self) -> None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=10, global_max=50))
        cb = CircuitBreaker(config=CircuitBreakerConfig(name="s3"))
        policy = DefaultRetryPolicy()
        orch = RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=cb,
            subsystem=Subsystem.S3,
        )

        budget.try_acquire(Subsystem.S3)
        metrics = orch.get_metrics()

        assert isinstance(metrics, RetryMetrics)
        assert metrics.circuit_breaker_states == {"s3": "closed"}
        assert metrics.budget_utilization["s3"] == pytest.approx(0.1)
        assert metrics.global_budget_utilization == pytest.approx(0.02)
        assert metrics.total_budget_denials == 0


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestRetryPolicyProtocol:
    """Verify DefaultRetryPolicy satisfies RetryPolicy protocol."""

    def test_isinstance_check(self) -> None:
        from autom8_asana.core.retry import RetryPolicy

        policy = DefaultRetryPolicy()
        assert isinstance(policy, RetryPolicy)

    def test_custom_policy_conformance(self) -> None:
        """A custom class satisfying the protocol is accepted."""
        from autom8_asana.core.retry import RetryPolicy

        class NeverRetry:
            @property
            def max_attempts(self) -> int:
                return 1

            def should_retry(self, error: Exception, attempt: int) -> bool:
                return False

            def delay_for(self, attempt: int) -> float:
                return 0.0

            @staticmethod
            def _is_transient(error: Exception) -> bool:
                return False

        assert isinstance(NeverRetry(), RetryPolicy)

    def test_custom_policy_in_orchestrator(self) -> None:
        """Custom policy works with RetryOrchestrator."""

        class AlwaysRetryPolicy:
            @property
            def max_attempts(self) -> int:
                return 3

            def should_retry(self, error: Exception, attempt: int) -> bool:
                return attempt < self.max_attempts

            def delay_for(self, attempt: int) -> float:
                return 0.0

            @staticmethod
            def _is_transient(error: Exception) -> bool:
                return True

        budget = RetryBudget()
        cb = CircuitBreaker(config=CircuitBreakerConfig(name="test"))
        orch = RetryOrchestrator(
            policy=AlwaysRetryPolicy(),
            budget=budget,
            circuit_breaker=cb,
            subsystem=Subsystem.HTTP,
        )

        call_count = 0

        def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("arbitrary error")
            return "ok"

        result = orch.execute_with_retry(fail_twice, operation_name="custom")
        assert result == "ok"
        assert call_count == 3


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Test enum values for serialization/logging."""

    def test_backoff_type_values(self) -> None:
        assert BackoffType.EXPONENTIAL.value == "exponential"
        assert BackoffType.LINEAR.value == "linear"
        assert BackoffType.IMMEDIATE.value == "immediate"
        assert BackoffType.NONE.value == "none"

    def test_subsystem_values(self) -> None:
        assert Subsystem.REDIS.value == "redis"
        assert Subsystem.S3.value == "s3"
        assert Subsystem.HTTP.value == "http"

    def test_cb_state_values(self) -> None:
        assert CBState.CLOSED.value == "closed"
        assert CBState.OPEN.value == "open"
        assert CBState.HALF_OPEN.value == "half_open"


# ---------------------------------------------------------------------------
# Layer 1 Tests: Error Classification Fix (B1+B2)
# ---------------------------------------------------------------------------


class TestIsTransientClientErrorCodes:
    """Test _is_transient() classification of raw ClientError by error code.

    Per TDD Section 4.2.1: ClientError instances with permanent error codes
    (NoSuchKey, AccessDenied, etc.) must be classified as non-transient, even
    though ClientError is in CACHE_TRANSIENT_ERRORS.
    """

    @staticmethod
    def _make_client_error(code: str) -> Exception:
        """Create a mock ClientError with the given AWS error code."""
        from botocore.exceptions import ClientError

        return ClientError(
            error_response={"Error": {"Code": code, "Message": "test"}},
            operation_name="TestOp",
        )

    def test_is_transient_nosuchkey_returns_false(self) -> None:
        """NoSuchKey is a permanent error -- file does not exist."""
        error = self._make_client_error("NoSuchKey")
        assert DefaultRetryPolicy._is_transient(error) is False

    def test_is_transient_access_denied_returns_false(self) -> None:
        """AccessDenied is a permanent error -- credentials/permissions."""
        error = self._make_client_error("AccessDenied")
        assert DefaultRetryPolicy._is_transient(error) is False

    def test_is_transient_nosuchbucket_returns_false(self) -> None:
        """NoSuchBucket is a permanent error -- bucket does not exist."""
        error = self._make_client_error("NoSuchBucket")
        assert DefaultRetryPolicy._is_transient(error) is False

    def test_is_transient_invalid_access_key_returns_false(self) -> None:
        """InvalidAccessKeyId is a permanent error -- bad credentials."""
        error = self._make_client_error("InvalidAccessKeyId")
        assert DefaultRetryPolicy._is_transient(error) is False

    def test_is_transient_signature_mismatch_returns_false(self) -> None:
        """SignatureDoesNotMatch is a permanent error."""
        error = self._make_client_error("SignatureDoesNotMatch")
        assert DefaultRetryPolicy._is_transient(error) is False

    def test_is_transient_method_not_allowed_returns_false(self) -> None:
        """MethodNotAllowed is a permanent error."""
        error = self._make_client_error("MethodNotAllowed")
        assert DefaultRetryPolicy._is_transient(error) is False

    def test_is_transient_throttling_returns_true(self) -> None:
        """Throttling is a transient error -- backend is rate-limiting."""
        error = self._make_client_error("Throttling")
        assert DefaultRetryPolicy._is_transient(error) is True

    def test_is_transient_internal_error_returns_true(self) -> None:
        """InternalError is a transient error -- backend hiccup."""
        error = self._make_client_error("InternalError")
        assert DefaultRetryPolicy._is_transient(error) is True

    def test_is_transient_slow_down_returns_true(self) -> None:
        """SlowDown is a transient error -- rate limiting."""
        error = self._make_client_error("SlowDown")
        assert DefaultRetryPolicy._is_transient(error) is True

    def test_is_transient_service_unavailable_returns_true(self) -> None:
        """ServiceUnavailable is a transient error."""
        error = self._make_client_error("ServiceUnavailable")
        assert DefaultRetryPolicy._is_transient(error) is True


class TestCBNotIncrementedForPermanentErrors:
    """Test that permanent errors do not feed the circuit breaker.

    Per TDD Section 4.2.2: record_failure() is called ONLY for transient
    errors. NoSuchKey, AccessDenied, etc. should not increment the CB
    failure counter.
    """

    @staticmethod
    def _make_client_error(code: str) -> Exception:
        from botocore.exceptions import ClientError

        return ClientError(
            error_response={"Error": {"Code": code, "Message": "test"}},
            operation_name="TestOp",
        )

    def _make_orchestrator(
        self,
        *,
        max_attempts: int = 3,
        failure_threshold: int = 5,
    ) -> RetryOrchestrator:
        policy = DefaultRetryPolicy(
            RetryPolicyConfig(
                backoff_type=BackoffType.IMMEDIATE,
                max_attempts=max_attempts,
                jitter=False,
            )
        )
        budget = RetryBudget(BudgetConfig())
        cb = CircuitBreaker(
            config=CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                name="test",
            )
        )
        return RetryOrchestrator(
            policy=policy,
            budget=budget,
            circuit_breaker=cb,
            subsystem=Subsystem.S3,
        )

    def test_cb_not_incremented_for_permanent_error(self) -> None:
        """NoSuchKey does not increment CB failure count."""
        orch = self._make_orchestrator(max_attempts=1)
        error = self._make_client_error("NoSuchKey")

        with pytest.raises(ClientError):
            orch.execute_with_retry(
                lambda: (_ for _ in ()).throw(error),
                operation_name="test",
            )

        assert orch.circuit_breaker._failure_count == 0
        assert orch.circuit_breaker.state == CBState.CLOSED

    def test_cb_incremented_for_transient_error(self) -> None:
        """Throttling increments CB failure count."""
        orch = self._make_orchestrator(max_attempts=1)
        error = self._make_client_error("Throttling")

        with pytest.raises(ClientError):
            orch.execute_with_retry(
                lambda: (_ for _ in ()).throw(error),
                operation_name="test",
            )

        assert orch.circuit_breaker._failure_count == 1

    def test_nosuchkey_raises_immediately_no_retry(self) -> None:
        """NoSuchKey raises immediately without retry (called exactly once)."""
        orch = self._make_orchestrator(max_attempts=3)
        call_count = 0

        def op() -> str:
            nonlocal call_count
            call_count += 1
            raise self._make_client_error("NoSuchKey")

        with pytest.raises(ClientError):
            orch.execute_with_retry(op, operation_name="test")

        assert call_count == 1  # No retry

    def test_throttling_retried_up_to_max(self) -> None:
        """Throttling is retried up to max_attempts."""
        orch = self._make_orchestrator(max_attempts=3)
        call_count = 0

        def op() -> str:
            nonlocal call_count
            call_count += 1
            raise self._make_client_error("Throttling")

        with pytest.raises(ClientError):
            orch.execute_with_retry(op, operation_name="test")

        assert call_count == 3  # Retried up to max

    def test_access_denied_does_not_open_cb(self) -> None:
        """10 AccessDenied errors should NOT open the CB (failure_threshold=5)."""
        orch = self._make_orchestrator(max_attempts=1, failure_threshold=5)

        for _ in range(10):
            with pytest.raises(ClientError):
                orch.execute_with_retry(
                    lambda: (_ for _ in ()).throw(self._make_client_error("AccessDenied")),
                    operation_name="test",
                )

        assert orch.circuit_breaker.state == CBState.CLOSED
        assert orch.circuit_breaker._failure_count == 0

    async def test_cb_not_incremented_for_permanent_error_async(self) -> None:
        """Async: NoSuchKey does not increment CB failure count."""
        orch = self._make_orchestrator(max_attempts=1)
        error = self._make_client_error("NoSuchKey")

        async def op() -> str:
            raise error

        with pytest.raises(ClientError):
            await orch.execute_with_retry_async(op, operation_name="test")

        assert orch.circuit_breaker._failure_count == 0
        assert orch.circuit_breaker.state == CBState.CLOSED

    async def test_cb_incremented_for_transient_error_async(self) -> None:
        """Async: Throttling increments CB failure count."""
        orch = self._make_orchestrator(max_attempts=1)
        error = self._make_client_error("Throttling")

        async def op() -> str:
            raise error

        with pytest.raises(ClientError):
            await orch.execute_with_retry_async(op, operation_name="test")

        assert orch.circuit_breaker._failure_count == 1
