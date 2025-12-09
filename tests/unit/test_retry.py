"""Tests for RetryHandler."""

import pytest

from autom8_asana.config import RetryConfig
from autom8_asana.transport.retry import RetryHandler


class TestRetryHandler:
    """Tests for retry handler logic."""

    def test_should_retry_within_max_retries(self) -> None:
        """Test that retry is allowed within max_retries."""
        config = RetryConfig(max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(429, attempt=0) is True
        assert handler.should_retry(429, attempt=1) is True
        assert handler.should_retry(429, attempt=2) is True

    def test_should_not_retry_at_max_retries(self) -> None:
        """Test that retry is denied at max_retries."""
        config = RetryConfig(max_retries=3)
        handler = RetryHandler(config)

        # At attempt 3, we've already tried 3 times (0, 1, 2)
        assert handler.should_retry(429, attempt=3) is False

    def test_should_not_retry_non_retryable_status(self) -> None:
        """Test that non-retryable status codes are not retried."""
        config = RetryConfig(max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(400, attempt=0) is False
        assert handler.should_retry(401, attempt=0) is False
        assert handler.should_retry(404, attempt=0) is False

    def test_default_retryable_status_codes(self) -> None:
        """Test default retryable status codes (429, 503, 504)."""
        config = RetryConfig()
        handler = RetryHandler(config)

        assert handler.should_retry(429, attempt=0) is True  # Rate limit
        assert handler.should_retry(503, attempt=0) is True  # Service unavailable
        assert handler.should_retry(504, attempt=0) is True  # Gateway timeout

    def test_custom_retryable_status_codes(self) -> None:
        """Test custom retryable status codes."""
        config = RetryConfig(retryable_status_codes=frozenset({500, 502}))
        handler = RetryHandler(config)

        assert handler.should_retry(500, attempt=0) is True
        assert handler.should_retry(502, attempt=0) is True
        assert handler.should_retry(429, attempt=0) is False  # Not in custom set


class TestGetDelay:
    """Tests for delay calculation."""

    def test_exponential_backoff(self) -> None:
        """Test exponential backoff calculation."""
        config = RetryConfig(
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # delay = base_delay * (exponential_base ** attempt)
        assert handler.get_delay(0) == pytest.approx(0.1)  # 0.1 * 2^0 = 0.1
        assert handler.get_delay(1) == pytest.approx(0.2)  # 0.1 * 2^1 = 0.2
        assert handler.get_delay(2) == pytest.approx(0.4)  # 0.1 * 2^2 = 0.4
        assert handler.get_delay(3) == pytest.approx(0.8)  # 0.1 * 2^3 = 0.8

    def test_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # At attempt 10, raw delay would be 1.0 * 2^10 = 1024
        assert handler.get_delay(10) == 5.0  # Capped at max_delay

    def test_retry_after_takes_precedence(self) -> None:
        """Test that Retry-After header takes precedence."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # Retry-After should override exponential backoff
        assert handler.get_delay(0, retry_after=30) == 30.0

    def test_retry_after_capped_at_max_delay(self) -> None:
        """Test that Retry-After is capped at max_delay."""
        config = RetryConfig(max_delay=60.0)
        handler = RetryHandler(config)

        # Large Retry-After should be capped
        assert handler.get_delay(0, retry_after=300) == 60.0

    def test_jitter_adds_randomness(self) -> None:
        """Test that jitter adds randomness to delays."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True,
        )
        handler = RetryHandler(config)

        # Get multiple delays - with jitter they should vary
        delays = [handler.get_delay(0) for _ in range(10)]

        # All should be between 0.5 and 1.5 (1.0 * (0.5 to 1.5))
        for delay in delays:
            assert 0.5 <= delay <= 1.5

        # They shouldn't all be exactly the same (very unlikely)
        assert len(set(delays)) > 1

    def test_jitter_range(self) -> None:
        """Test that jitter is in expected range (0.5x to 1.5x)."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=1.0,  # No exponential growth
            jitter=True,
        )
        handler = RetryHandler(config)

        # Sample many delays
        delays = [handler.get_delay(0) for _ in range(100)]

        # Check bounds
        assert min(delays) >= 0.5
        assert max(delays) <= 1.5


class TestWait:
    """Tests for async wait method."""

    @pytest.mark.asyncio
    async def test_wait_respects_delay(self) -> None:
        """Test that wait actually waits."""
        import time

        config = RetryConfig(
            base_delay=0.1,
            jitter=False,
        )
        handler = RetryHandler(config)

        start = time.monotonic()
        await handler.wait(0)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_wait_with_retry_after(self) -> None:
        """Test wait with Retry-After header."""
        import time

        config = RetryConfig()
        handler = RetryHandler(config)

        start = time.monotonic()
        await handler.wait(0, retry_after=1)  # 1 second from Retry-After
        elapsed = time.monotonic() - start

        assert elapsed >= 0.9  # Allow some tolerance
