"""Tests for TokenBucketRateLimiter."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from autom8_asana.transport.rate_limiter import TokenBucketRateLimiter


class MockLogger:
    """Mock logger that records calls for testing."""

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


class TestTokenBucketRateLimiter:
    """Tests for token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_initial_tokens(self) -> None:
        """Test that bucket starts full."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

        # Should have all tokens available
        assert limiter.available_tokens == pytest.approx(100, rel=0.01)

    @pytest.mark.asyncio
    async def test_acquire_single_token(self) -> None:
        """Test acquiring a single token."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

        await limiter.acquire(1)

        # Should have 99 tokens remaining
        assert limiter.available_tokens == pytest.approx(99, rel=0.1)

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self) -> None:
        """Test acquiring multiple tokens at once."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

        await limiter.acquire(10)

        # Should have approximately 90 tokens remaining
        assert limiter.available_tokens == pytest.approx(90, rel=0.1)

    @pytest.mark.asyncio
    async def test_acquire_depletes_bucket(self) -> None:
        """Test that acquiring depletes the bucket."""
        limiter = TokenBucketRateLimiter(max_tokens=10, refill_period=60.0)

        # Acquire all tokens
        for _ in range(10):
            await limiter.acquire(1)

        # Bucket should be nearly empty
        assert limiter.available_tokens < 1

    @pytest.mark.asyncio
    async def test_refill_over_time(self) -> None:
        """Test that tokens refill over time."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=1.0)

        # Deplete some tokens
        await limiter.acquire(50)

        # Wait for half the refill period
        await asyncio.sleep(0.5)

        # Should have refilled approximately 50 tokens
        available = limiter.available_tokens
        assert available > 50  # At least some refill
        assert available <= 100  # But not over max

    @pytest.mark.asyncio
    async def test_bucket_caps_at_max(self) -> None:
        """Test that bucket doesn't exceed max tokens."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=0.1)

        # Wait long enough for "overfill"
        await asyncio.sleep(0.2)

        # Should still be capped at max
        assert limiter.available_tokens <= 100

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self) -> None:
        """Test that concurrent acquires are thread-safe."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

        # Spawn multiple concurrent acquires
        async def acquire_one() -> None:
            await limiter.acquire(1)

        await asyncio.gather(*[acquire_one() for _ in range(50)])

        # Should have approximately 50 tokens remaining
        assert limiter.available_tokens == pytest.approx(50, rel=0.1)

    @pytest.mark.asyncio
    async def test_blocks_when_empty(self) -> None:
        """Test that acquire blocks when bucket is empty."""
        # Fast refill for test
        limiter = TokenBucketRateLimiter(max_tokens=5, refill_period=0.5)

        # Deplete bucket
        for _ in range(5):
            await limiter.acquire(1)

        # Time the next acquire - should block
        start = time.monotonic()
        await limiter.acquire(1)
        elapsed = time.monotonic() - start

        # Should have waited at least some time for refill
        assert elapsed > 0.05  # At least 50ms

    @pytest.mark.asyncio
    async def test_default_parameters(self) -> None:
        """Test default rate limit values (Asana's 1500/60s)."""
        limiter = TokenBucketRateLimiter()

        assert limiter._max_tokens == 1500
        assert limiter._refill_rate == pytest.approx(25.0, rel=0.01)  # 1500/60

    @pytest.mark.asyncio
    async def test_refill_rate_calculation(self) -> None:
        """Test that refill rate is correctly calculated."""
        limiter = TokenBucketRateLimiter(max_tokens=120, refill_period=60.0)

        # Should refill 2 tokens per second
        assert limiter._refill_rate == pytest.approx(2.0, rel=0.01)


class TestGetStats:
    """Tests for rate limiter get_stats() method."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_expected_keys(self) -> None:
        """get_stats() returns all expected keys."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

        stats = limiter.get_stats()

        assert "available_tokens" in stats
        assert "max_tokens" in stats
        assert "refill_rate" in stats
        assert "utilization" in stats

    @pytest.mark.asyncio
    async def test_get_stats_initial_values(self) -> None:
        """get_stats() returns correct initial values for full bucket."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

        stats = limiter.get_stats()

        assert stats["max_tokens"] == 100
        assert stats["refill_rate"] == pytest.approx(100 / 60.0, rel=0.01)
        assert stats["available_tokens"] == pytest.approx(100, rel=0.01)
        # Full bucket = 0% utilization
        assert stats["utilization"] == pytest.approx(0.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_get_stats_after_acquire(self) -> None:
        """get_stats() reflects token consumption."""
        limiter = TokenBucketRateLimiter(max_tokens=100, refill_period=60.0)

        # Consume 50 tokens
        await limiter.acquire(50)

        stats = limiter.get_stats()

        assert stats["available_tokens"] == pytest.approx(50, rel=0.1)
        # 50 tokens used out of 100 = 50% utilization
        assert stats["utilization"] == pytest.approx(0.5, rel=0.1)

    @pytest.mark.asyncio
    async def test_get_stats_utilization_range(self) -> None:
        """Utilization is between 0.0 and 1.0."""
        limiter = TokenBucketRateLimiter(max_tokens=10, refill_period=60.0)

        # Full bucket
        stats = limiter.get_stats()
        assert 0.0 <= stats["utilization"] <= 1.0

        # Partially depleted
        await limiter.acquire(5)
        stats = limiter.get_stats()
        assert 0.0 <= stats["utilization"] <= 1.0

        # Nearly empty
        await limiter.acquire(4)
        stats = limiter.get_stats()
        assert 0.0 <= stats["utilization"] <= 1.0


class TestRateLimitLogging:
    """Tests for rate limiter logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_info_for_short_wait(self) -> None:
        """Logs at INFO level for waits <= 1 second."""
        logger = MockLogger()
        # 10 tokens, 10 tokens/second refill rate = 0.1s wait for 1 token
        limiter = TokenBucketRateLimiter(
            max_tokens=10, refill_period=1.0, logger=logger
        )

        # Deplete all tokens
        await limiter.acquire(10)

        # Next acquire will wait ~0.1s for 1 token
        await limiter.acquire(1)

        # Should have logged at info level (not warning)
        info_logs = [msg for level, msg in logger.messages if level == "info"]
        warning_logs = [msg for level, msg in logger.messages if level == "warning"]

        assert len(info_logs) >= 1
        assert any("Rate limit" in msg for msg in info_logs)
        # No warnings for short waits
        rate_limit_warnings = [msg for msg in warning_logs if "Rate limit" in msg]
        assert len(rate_limit_warnings) == 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_logs_warning_for_long_wait(self) -> None:
        """Logs at WARNING level for waits > 1 second."""
        logger = MockLogger()
        # Configure: 1 token max, 0.5 tokens/second refill rate
        # When bucket is empty, waiting for 1 token takes 2 seconds
        limiter = TokenBucketRateLimiter(max_tokens=1, refill_period=2.0, logger=logger)

        # Deplete the single token
        await limiter.acquire(1)

        # Request another token - bucket is empty, need to wait ~2s
        # This should trigger a warning since wait_time > 1.0
        await limiter.acquire(1)

        # Should have logged at warning level
        warning_logs = [msg for level, msg in logger.messages if level == "warning"]

        # At least one warning about waiting
        rate_limit_warnings = [msg for msg in warning_logs if "Rate limit" in msg]
        assert len(rate_limit_warnings) >= 1

    @pytest.mark.asyncio
    async def test_no_logging_when_no_wait(self) -> None:
        """No rate limit logs when acquire doesn't wait."""
        logger = MockLogger()
        limiter = TokenBucketRateLimiter(
            max_tokens=100, refill_period=60.0, logger=logger
        )

        # Acquire a few tokens - should not need to wait
        await limiter.acquire(5)

        # No rate limit logs expected
        rate_limit_logs = [msg for level, msg in logger.messages if "Rate limit" in msg]
        assert len(rate_limit_logs) == 0
