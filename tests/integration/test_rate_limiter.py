"""Integration tests for rate limiter under realistic conditions."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import respx

from autom8_asana.config import (
    AsanaConfig,
    ConcurrencyConfig,
    RateLimitConfig,
    RetryConfig,
)
from autom8_asana.transport.http import AsyncHTTPClient
from autom8_asana.transport.rate_limiter import TokenBucketRateLimiter


class MockAuthProvider:
    """Mock auth provider for integration testing."""

    def get_secret(self, key: str) -> str:
        return "integration-test-token"


class MockLogger:
    """Mock logger that records calls."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("debug", msg))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("info", msg))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("warning", msg))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("error", msg))

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("exception", msg))


class TestConcurrentRequestsRespectRateLimit:
    """Test that concurrent requests are properly rate-limited."""

    async def test_100_concurrent_requests_respect_rate_limit(self) -> None:
        """Launch 100 concurrent requests and verify they're properly rate-limited without errors.

        Uses a small token bucket (10 tokens, 1 second refill) to make test fast.
        All 100 requests should complete successfully, rate-limited by token bucket.
        """
        max_tokens = 10
        refill_period = 1.0  # 1 second to refill completely

        limiter = TokenBucketRateLimiter(
            max_tokens=max_tokens,
            refill_period=refill_period,
        )

        completed = 0
        errors: list[Exception] = []

        async def make_request(request_id: int) -> int:
            nonlocal completed
            try:
                await limiter.acquire()
                completed += 1
                return request_id
            except Exception as e:
                errors.append(e)
                raise

        start_time = time.monotonic()

        # Launch 100 concurrent requests
        tasks = [make_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        elapsed = time.monotonic() - start_time

        # All requests should complete successfully
        assert len(results) == 100
        assert completed == 100
        assert len(errors) == 0

        # With 10 tokens and 100 requests, we need at least 9 refills
        # (10 burst + 90 more requiring ~9 seconds at 10 tokens/second)
        # Allow some tolerance for timing variations
        expected_min_time = (100 - max_tokens) / (max_tokens / refill_period)
        assert elapsed >= expected_min_time * 0.8, (
            f"Expected at least {expected_min_time * 0.8:.2f}s, got {elapsed:.2f}s"
        )


class TestRateLimiterAndSemaphoreInteraction:
    """Test that rate limiter and concurrency semaphores work together."""

    @respx.mock
    async def test_rate_limit_and_semaphore_no_deadlock(self) -> None:
        """Test that rate limiter and concurrency semaphores work together without deadlocks.

        Uses constrained configuration:
        - Small token bucket (5 tokens)
        - Low concurrency limits (2 read, 1 write)
        - 20 concurrent requests

        All requests should complete without deadlock.
        """
        config = AsanaConfig(
            base_url="https://app.asana.com/api/1.0",
            rate_limit=RateLimitConfig(
                max_requests=5,
                window_seconds=1,
            ),
            concurrency=ConcurrencyConfig(
                read_limit=2,
                write_limit=1,
            ),
            retry=RetryConfig(
                max_retries=0,  # No retries for this test
                jitter=False,
            ),
        )
        auth_provider = MockAuthProvider()
        logger = MockLogger()

        http_client = AsyncHTTPClient(config, auth_provider, logger)

        # Mock 20 different endpoints
        for i in range(20):
            respx.get(f"https://app.asana.com/api/1.0/tasks/task{i}").mock(
                return_value=httpx.Response(
                    200,
                    json={"data": {"gid": f"task{i}", "name": f"Task {i}"}},
                )
            )

        try:
            # Launch 20 concurrent GET requests
            tasks = [http_client.get(f"/tasks/task{i}") for i in range(20)]

            # Use timeout to detect deadlock
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=30.0,  # 30 second timeout - should be plenty
            )

            assert len(results) == 20
            for i, result in enumerate(results):
                assert result["gid"] == f"task{i}"

        finally:
            await http_client.close()


class Test429ResponseTriggersRetry:
    """Test that 429 response triggers correct retry behavior."""

    @respx.mock
    async def test_429_triggers_retry_with_backoff(self) -> None:
        """Mock a 429 response and verify the client retries with backoff.

        Note: The current implementation uses exponential backoff for all retries,
        including 429 responses. The Retry-After header is parsed in RateLimitError
        but not currently used by the HTTP client's retry logic (it falls back to
        exponential backoff when retry_after is None).
        """
        config = AsanaConfig(
            base_url="https://app.asana.com/api/1.0",
            rate_limit=RateLimitConfig(
                max_requests=100,  # High limit so rate limiter doesn't interfere
                window_seconds=60,
            ),
            retry=RetryConfig(
                max_retries=3,
                base_delay=0.05,  # 50ms base delay
                max_delay=1.0,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        auth_provider = MockAuthProvider()
        logger = MockLogger()

        http_client = AsyncHTTPClient(config, auth_provider, logger)

        # First request returns 429 with Retry-After, second succeeds
        route = respx.get("https://app.asana.com/api/1.0/tasks/rate-limited")
        route.side_effect = [
            httpx.Response(
                429,
                headers={"Retry-After": "1"},
                json={"errors": [{"message": "Rate limit exceeded"}]},
            ),
            httpx.Response(
                200,
                json={"data": {"gid": "rate-limited", "name": "Task"}},
            ),
        ]

        try:
            start_time = time.monotonic()
            result = await http_client.get("/tasks/rate-limited")
            elapsed = time.monotonic() - start_time

            assert result["gid"] == "rate-limited"
            assert route.call_count == 2

            # Should have waited at least base_delay (exponential backoff)
            expected_min_delay = 0.05 * 0.8  # 80% of base delay
            assert elapsed >= expected_min_delay, (
                f"Expected at least {expected_min_delay:.3f}s wait, got {elapsed:.3f}s"
            )

            # Check logger recorded retry
            retry_logs = [
                msg
                for level, msg in logger.messages
                if level == "warning" and "Retry" in msg
            ]
            assert len(retry_logs) >= 1

        finally:
            await http_client.close()

    @respx.mock
    async def test_429_without_retry_after_uses_exponential_backoff(self) -> None:
        """429 without Retry-After header should use exponential backoff."""
        config = AsanaConfig(
            base_url="https://app.asana.com/api/1.0",
            rate_limit=RateLimitConfig(
                max_requests=100,
                window_seconds=60,
            ),
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.05,  # 50ms base delay
                max_delay=1.0,
                exponential_base=2.0,
                jitter=False,
                retryable_status_codes=frozenset({429, 503, 504}),
            ),
        )
        auth_provider = MockAuthProvider()
        logger = MockLogger()

        http_client = AsyncHTTPClient(config, auth_provider, logger)

        # Fail twice with 429 (no Retry-After), then succeed
        route = respx.get("https://app.asana.com/api/1.0/tasks/backoff")
        route.side_effect = [
            httpx.Response(
                429,
                json={"errors": [{"message": "Rate limit exceeded"}]},
            ),
            httpx.Response(
                429,
                json={"errors": [{"message": "Rate limit exceeded"}]},
            ),
            httpx.Response(
                200,
                json={"data": {"gid": "backoff", "name": "Task"}},
            ),
        ]

        try:
            start_time = time.monotonic()
            result = await http_client.get("/tasks/backoff")
            elapsed = time.monotonic() - start_time

            assert result["gid"] == "backoff"
            assert route.call_count == 3

            # Expected delays: 0.05s (first retry) + 0.1s (second retry) = 0.15s
            expected_min_delay = 0.05 + 0.1  # base_delay * 2^0 + base_delay * 2^1
            assert elapsed >= expected_min_delay * 0.8, (
                f"Expected at least {expected_min_delay * 0.8:.3f}s, got {elapsed:.3f}s"
            )

        finally:
            await http_client.close()


class TestTokenRefillAccuracy:
    """Test that tokens refill at the expected rate over time."""

    async def test_token_refill_rate(self) -> None:
        """Test that tokens refill at the expected rate over time."""
        max_tokens = 10
        refill_period = 1.0  # 10 tokens per second

        limiter = TokenBucketRateLimiter(
            max_tokens=max_tokens,
            refill_period=refill_period,
        )

        # Consume all tokens
        for _ in range(max_tokens):
            await limiter.acquire()

        # Available tokens should be near 0
        assert limiter.available_tokens < 1.0

        # Wait for half the refill period
        await asyncio.sleep(refill_period / 2)

        # Should have approximately half the tokens back
        available = limiter.available_tokens
        expected = max_tokens / 2
        tolerance = max_tokens * 0.2  # 20% tolerance for timing

        assert abs(available - expected) < tolerance, (
            f"Expected ~{expected} tokens, got {available}"
        )

        # Wait for rest of refill period
        await asyncio.sleep(refill_period / 2)

        # Should be back to full capacity
        available = limiter.available_tokens
        assert abs(available - max_tokens) < tolerance, (
            f"Expected ~{max_tokens} tokens, got {available}"
        )

    async def test_token_refill_does_not_exceed_max(self) -> None:
        """Test that tokens never exceed max_tokens even after long wait."""
        max_tokens = 10
        refill_period = 0.1  # Fast refill

        limiter = TokenBucketRateLimiter(
            max_tokens=max_tokens,
            refill_period=refill_period,
        )

        # Wait longer than refill period
        await asyncio.sleep(refill_period * 2)

        # Tokens should not exceed max
        assert limiter.available_tokens <= max_tokens


class TestBurstThenSteadyState:
    """Test burst capacity followed by steady-state rate limiting."""

    async def test_burst_then_steady_state(self) -> None:
        """Test that burst capacity works then transitions to steady-state rate.

        With 10 max tokens and 1 second refill:
        - First 10 requests should complete instantly (burst)
        - Next requests should be rate-limited to 10/second
        """
        max_tokens = 10
        refill_period = 1.0

        limiter = TokenBucketRateLimiter(
            max_tokens=max_tokens,
            refill_period=refill_period,
        )

        # Phase 1: Burst - 10 requests should complete quickly
        burst_start = time.monotonic()
        for _ in range(max_tokens):
            await limiter.acquire()
        burst_elapsed = time.monotonic() - burst_start

        # Burst should be nearly instant (well under 100ms)
        assert burst_elapsed < 0.1, f"Burst took {burst_elapsed:.3f}s, expected < 0.1s"

        # Phase 2: Steady state - next 10 requests should take ~1 second
        steady_start = time.monotonic()
        for _ in range(max_tokens):
            await limiter.acquire()
        steady_elapsed = time.monotonic() - steady_start

        # Steady state should take approximately the refill period
        # (with tolerance for timing variations)
        assert steady_elapsed >= refill_period * 0.8, (
            f"Steady state took {steady_elapsed:.3f}s, expected >= {refill_period * 0.8:.3f}s"
        )

    async def test_partial_burst_recovery(self) -> None:
        """Test that partial token recovery allows partial burst."""
        max_tokens = 10
        refill_period = 1.0

        limiter = TokenBucketRateLimiter(
            max_tokens=max_tokens,
            refill_period=refill_period,
        )

        # Consume all tokens
        for _ in range(max_tokens):
            await limiter.acquire()

        # Wait for 50% recovery
        await asyncio.sleep(refill_period / 2)

        # Should be able to burst ~5 requests quickly
        burst_start = time.monotonic()
        burst_count = 5
        for _ in range(burst_count):
            await limiter.acquire()
        burst_elapsed = time.monotonic() - burst_start

        # These should complete relatively quickly since we had ~5 tokens
        assert burst_elapsed < 0.2, (
            f"Partial burst took {burst_elapsed:.3f}s, expected < 0.2s"
        )


class TestRateLimiterWithHTTPClient:
    """Test rate limiter behavior through the full HTTP client stack."""

    @respx.mock
    async def test_rate_limited_requests_complete_successfully(self) -> None:
        """Test that many requests through HTTP client complete with rate limiting."""
        config = AsanaConfig(
            base_url="https://app.asana.com/api/1.0",
            rate_limit=RateLimitConfig(
                max_requests=10,  # Small for fast test
                window_seconds=1,
            ),
            concurrency=ConcurrencyConfig(
                read_limit=50,  # High concurrency to stress rate limiter
                write_limit=15,
            ),
            retry=RetryConfig(
                max_retries=0,
                jitter=False,
            ),
        )
        auth_provider = MockAuthProvider()
        logger = MockLogger()

        http_client = AsyncHTTPClient(config, auth_provider, logger)

        # Mock 30 endpoints
        for i in range(30):
            respx.get(f"https://app.asana.com/api/1.0/tasks/task{i}").mock(
                return_value=httpx.Response(
                    200,
                    json={"data": {"gid": f"task{i}", "name": f"Task {i}"}},
                )
            )

        try:
            start_time = time.monotonic()

            # Launch 30 concurrent requests
            tasks = [http_client.get(f"/tasks/task{i}") for i in range(30)]
            results = await asyncio.gather(*tasks)

            elapsed = time.monotonic() - start_time

            # All should succeed
            assert len(results) == 30
            for i, result in enumerate(results):
                assert result["gid"] == f"task{i}"

            # Should have taken some time due to rate limiting
            # With 10 tokens and 30 requests, need at least 2 seconds
            # (10 burst + 10/second * 2 seconds = 30)
            expected_min_time = (30 - 10) / 10 * 0.8  # 80% of theoretical minimum
            assert elapsed >= expected_min_time, (
                f"Expected at least {expected_min_time:.2f}s, got {elapsed:.2f}s"
            )

        finally:
            await http_client.close()

    @respx.mock
    async def test_mixed_read_write_with_rate_limiting(self) -> None:
        """Test that mixed read/write operations are properly rate-limited."""
        config = AsanaConfig(
            base_url="https://app.asana.com/api/1.0",
            rate_limit=RateLimitConfig(
                max_requests=10,
                window_seconds=1,
            ),
            concurrency=ConcurrencyConfig(
                read_limit=5,
                write_limit=2,
            ),
            retry=RetryConfig(
                max_retries=0,
                jitter=False,
            ),
        )
        auth_provider = MockAuthProvider()
        logger = MockLogger()

        http_client = AsyncHTTPClient(config, auth_provider, logger)

        # Mock GET endpoints
        for i in range(10):
            respx.get(f"https://app.asana.com/api/1.0/tasks/task{i}").mock(
                return_value=httpx.Response(
                    200,
                    json={"data": {"gid": f"task{i}", "name": f"Task {i}"}},
                )
            )

        # Mock POST endpoint
        respx.post("https://app.asana.com/api/1.0/tasks").mock(
            return_value=httpx.Response(
                201,
                json={"data": {"gid": "new-task", "name": "New Task"}},
            )
        )

        try:
            # Mix of reads and writes
            read_tasks = [http_client.get(f"/tasks/task{i}") for i in range(10)]
            write_tasks = [
                http_client.post("/tasks", json={"data": {"name": f"Task {i}"}})
                for i in range(5)
            ]

            all_tasks = read_tasks + write_tasks
            results = await asyncio.gather(*all_tasks)

            assert len(results) == 15

        finally:
            await http_client.close()
