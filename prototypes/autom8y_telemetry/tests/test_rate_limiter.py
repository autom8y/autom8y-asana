"""Basic test for TokenBucketRateLimiter POC.

This is prototype code - minimal test coverage only.
Production version would have comprehensive test suite.
"""

import asyncio

import pytest

# Add parent directory to path for prototype import
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rate_limiter import TokenBucketRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic token acquisition and refill."""
    # Create limiter: 10 tokens, 1 second refill
    limiter = TokenBucketRateLimiter(max_tokens=10, refill_period=1.0)

    # Should start with full bucket
    assert limiter.available_tokens == 10.0

    # Acquire 5 tokens
    await limiter.acquire(5)
    assert limiter.available_tokens == 5.0

    # Acquire remaining 5 tokens
    await limiter.acquire(5)
    assert limiter.available_tokens == 0.0

    # Wait for partial refill
    await asyncio.sleep(0.5)
    assert limiter.available_tokens >= 4.5  # ~5 tokens refilled

    # Stats should work
    stats = limiter.get_stats()
    assert stats["max_tokens"] == 10
    assert stats["refill_rate"] == 10.0  # 10 tokens per second
    assert 0.0 <= stats["utilization"] <= 1.0


@pytest.mark.asyncio
async def test_rate_limiter_protocol_compliance():
    """Test that TokenBucketRateLimiter implements RateLimiterProtocol."""
    from protocols import RateLimiterProtocol

    limiter = TokenBucketRateLimiter(max_tokens=5, refill_period=1.0)

    # Should be instance of protocol
    assert isinstance(limiter, RateLimiterProtocol)

    # Protocol methods should work
    await limiter.acquire(1)
    tokens = limiter.available_tokens
    assert isinstance(tokens, float)

    stats = limiter.get_stats()
    assert isinstance(stats, dict)


@pytest.mark.asyncio
async def test_rate_limiter_invalid_config():
    """Test that invalid configuration raises errors."""
    with pytest.raises(RuntimeError, match="max_tokens must be positive"):
        TokenBucketRateLimiter(max_tokens=0, refill_period=1.0)

    with pytest.raises(RuntimeError, match="refill_period must be positive"):
        TokenBucketRateLimiter(max_tokens=10, refill_period=0.0)
