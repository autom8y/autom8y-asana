"""Token bucket rate limiter for Asana API."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from autom8_asana.exceptions import ConfigurationError

if TYPE_CHECKING:
    from autom8_asana.protocols.log import LogProvider


class TokenBucketRateLimiter:
    """Token bucket rate limiter.

    Allows burst traffic up to bucket capacity, then smoothly
    limits to the refill rate.

    Default: 1500 requests per 60 seconds (Asana's limit).

    Thread-safe via asyncio.Lock for async contexts.
    """

    def __init__(
        self,
        max_tokens: int = 1500,
        refill_period: float = 60.0,
        logger: LogProvider | None = None,
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_tokens: Maximum tokens (burst capacity), must be > 0
            refill_period: Seconds to fully refill bucket, must be > 0
            logger: Optional logger for rate limit warnings

        Raises:
            ConfigurationError: If max_tokens or refill_period are invalid
        """
        if max_tokens <= 0:
            raise ConfigurationError(f"max_tokens must be positive, got {max_tokens}")
        if refill_period <= 0:
            raise ConfigurationError(
                f"refill_period must be positive, got {refill_period}"
            )

        self._max_tokens = max_tokens
        self._refill_rate = max_tokens / refill_period  # tokens per second
        self._tokens = float(max_tokens)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._logger = logger

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)
        """
        async with self._lock:
            await self._refill()

            while self._tokens < tokens:
                # Calculate wait time for enough tokens
                needed = tokens - self._tokens
                wait_time = needed / self._refill_rate

                if self._logger:
                    # Use warning level for waits > 1s to help identify rate limiting issues
                    if wait_time > 1.0:
                        self._logger.warning(
                            f"Rate limit: waiting {wait_time:.2f}s for {needed:.1f} tokens"
                        )
                    else:
                        self._logger.info(
                            f"Rate limit: waiting {wait_time:.2f}s for {needed:.1f} tokens"
                        )

                await asyncio.sleep(wait_time)
                await self._refill()

            self._tokens -= tokens

    async def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    @property
    def available_tokens(self) -> float:
        """Current available tokens (approximate, not locked)."""
        elapsed = time.monotonic() - self._last_refill
        return min(self._max_tokens, self._tokens + elapsed * self._refill_rate)

    def get_stats(self) -> dict[str, Any]:
        """Return rate limiter statistics for monitoring.

        Returns:
            Dictionary containing:
                - available_tokens: Current available tokens (approximate)
                - max_tokens: Maximum bucket capacity
                - refill_rate: Tokens refilled per second
                - utilization: Fraction of capacity in use (0.0 = empty, 1.0 = full)
        """
        available = self.available_tokens
        return {
            "available_tokens": available,
            "max_tokens": self._max_tokens,
            "refill_rate": self._refill_rate,
            "utilization": 1.0 - (available / self._max_tokens),
        }
