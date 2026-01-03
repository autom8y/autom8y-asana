"""Standalone test for TokenBucketRateLimiter POC.

This test imports only the rate_limiter module directly,
avoiding dependency on OpenTelemetry for basic validation.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add prototype directory to path for direct module import
prototype_dir = Path(__file__).parent / "autom8y_telemetry"
sys.path.insert(0, str(prototype_dir))

# Import modules directly (no package-level imports)
import rate_limiter
import protocols


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic token acquisition and refill."""
    # Create limiter: 10 tokens, 1 second refill
    limiter = rate_limiter.TokenBucketRateLimiter(max_tokens=10, refill_period=1.0)

    # Should start with full bucket
    assert limiter.available_tokens == 10.0

    # Acquire 5 tokens
    await limiter.acquire(5)
    assert abs(limiter.available_tokens - 5.0) < 0.1  # Allow for time drift

    # Acquire remaining 5 tokens
    await limiter.acquire(5)
    assert abs(limiter.available_tokens - 0.0) < 0.1  # Allow for time drift

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
    limiter = rate_limiter.TokenBucketRateLimiter(max_tokens=5, refill_period=1.0)

    # Should be instance of protocol
    assert isinstance(limiter, protocols.RateLimiterProtocol)

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
        rate_limiter.TokenBucketRateLimiter(max_tokens=0, refill_period=1.0)

    with pytest.raises(RuntimeError, match="refill_period must be positive"):
        rate_limiter.TokenBucketRateLimiter(max_tokens=10, refill_period=0.0)


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_access():
    """Test that rate limiter handles concurrent acquisitions correctly."""
    limiter = rate_limiter.TokenBucketRateLimiter(max_tokens=5, refill_period=1.0)

    # Launch 3 concurrent acquisitions (2 tokens each = 6 total)
    # Should process first 2, then wait for refill for 3rd
    async def acquire_tokens():
        await limiter.acquire(2)
        return True

    # Run 3 concurrent tasks
    results = await asyncio.gather(
        acquire_tokens(),
        acquire_tokens(),
        acquire_tokens(),
    )

    # All should succeed (with waiting)
    assert all(results)

    # Should have used all tokens and refilled some
    available = limiter.available_tokens
    assert available >= 0.0
