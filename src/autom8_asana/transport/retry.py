"""Retry handler with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.config import RetryConfig
    from autom8_asana.protocols.log import LogProvider


class RetryHandler:
    """Handles retry logic with exponential backoff and jitter.

    Implements the retry behavior specified in TDD:
    - Exponential backoff: delay = base_delay * (exponential_base ** attempt)
    - Optional jitter: adds random factor to prevent thundering herd
    - Respects Retry-After header for 429 responses
    """

    def __init__(
        self,
        config: RetryConfig,
        logger: LogProvider | None = None,
    ) -> None:
        """Initialize retry handler.

        Args:
            config: Retry configuration
            logger: Optional logger
        """
        self._config = config
        self._logger = logger

    def should_retry(self, status_code: int, attempt: int) -> bool:
        """Determine if request should be retried.

        Args:
            status_code: HTTP status code
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self._config.max_retries:
            return False
        return status_code in self._config.retryable_status_codes

    def get_delay(self, attempt: int, retry_after: int | None = None) -> float:
        """Calculate delay before next retry.

        Args:
            attempt: Current attempt number (0-indexed)
            retry_after: Retry-After header value (takes precedence)

        Returns:
            Delay in seconds
        """
        if retry_after is not None:
            # Respect server's Retry-After, but cap at max_delay
            return min(float(retry_after), self._config.max_delay)

        # Exponential backoff
        delay = self._config.base_delay * (self._config.exponential_base**attempt)

        # Add jitter if enabled (0.5x to 1.5x)
        if self._config.jitter:
            delay *= 0.5 + random.random()

        # Cap at max delay
        return min(delay, self._config.max_delay)

    async def wait(self, attempt: int, retry_after: int | None = None) -> None:
        """Wait before retry.

        Args:
            attempt: Current attempt number
            retry_after: Optional Retry-After header value
        """
        delay = self.get_delay(attempt, retry_after)

        if self._logger:
            self._logger.warning(
                f"Retry attempt {attempt + 1}/{self._config.max_retries}: "
                f"waiting {delay:.2f}s"
            )

        await asyncio.sleep(delay)
