"""Shared error classification and degraded mode handling for cache backends.

Extracted from cache backends to eliminate duplicated degraded-mode
state machines and error classification logic.
"""

from __future__ import annotations

import time

from autom8y_log import get_logger

logger = get_logger(__name__)


# Base error types that trigger degraded mode across all backends
CONNECTION_ERROR_TYPES: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def is_connection_error(
    error: Exception,
    *,
    extra_types: tuple[type[Exception], ...] = (),
) -> bool:
    """Check if error is a connection/timeout error.

    Args:
        error: Exception to classify.
        extra_types: Additional backend-specific error types.

    Returns:
        True if error indicates a connection or timeout failure.
    """
    return isinstance(error, CONNECTION_ERROR_TYPES + extra_types)


def is_s3_not_found_error(error: Exception) -> bool:
    """Check if error indicates S3 object not found (404/NoSuchKey).

    Handles both botocore ClientError and string-pattern matching
    for compatibility with both sync and async S3 clients.

    Args:
        error: Exception to check.

    Returns:
        True if error indicates object not found.
    """
    # Check botocore ClientError response
    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code in ("NoSuchKey", "404", "NotFound"):
            return True

    # Check exception class name
    if type(error).__name__ in ("NoSuchKey", "NotFound"):
        return True

    # Check string patterns for S3 not-found errors
    error_str = str(error).lower()
    return "nosuchkey" in error_str or "not found" in error_str or "404" in error_str


def is_s3_retryable_error(error: Exception) -> bool:
    """Check if S3 error is transient and should be retried.

    Args:
        error: Exception to check.

    Returns:
        True if error is transient (throttling, 5xx, timeout).
    """
    import asyncio

    # Specific exception types
    if isinstance(
        error, (ConnectionError, TimeoutError, asyncio.TimeoutError, OSError)
    ):
        return True

    # Check botocore error codes
    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code in (
            "SlowDown",
            "ServiceUnavailable",
            "InternalError",
            "RequestTimeout",
        ):
            return True

    # String pattern matching for broader compatibility
    error_str = str(error).lower()
    retryable_patterns = [
        "timeout",
        "connection",
        "throttl",
        "slowdown",
        "503",
        "500",
        "serviceunav",
    ]
    return any(pattern in error_str for pattern in retryable_patterns)


class DegradedModeMixin:
    """Mixin providing degraded mode state machine for cache backends.

    Manages the _degraded flag, reconnect timing, and mode transitions.
    Backends using this mixin must initialize `_degraded`, `_last_reconnect_attempt`,
    and `_reconnect_interval` attributes.

    Usage:
        class MyBackend(DegradedModeMixin):
            def __init__(self):
                self._degraded = False
                self._last_reconnect_attempt = 0.0
                self._reconnect_interval = 30.0
    """

    _degraded: bool
    _last_reconnect_attempt: float
    _reconnect_interval: float

    def enter_degraded_mode(self, reason: str) -> None:
        """Enter degraded mode with logging.

        Only logs on first entry (not if already degraded).

        Args:
            reason: Human-readable reason for entering degraded mode.
        """
        if not self._degraded:
            logger.warning(
                "backend_entering_degraded_mode",
                extra={
                    "backend": type(self).__name__,
                    "reason": reason,
                },
            )
            self._degraded = True

    def should_attempt_reconnect(self) -> bool:
        """Check if enough time has passed to attempt reconnection.

        Returns:
            True if reconnect should be attempted.
        """
        if not self._degraded:
            return False
        return time.time() - self._last_reconnect_attempt >= self._reconnect_interval

    def record_reconnect_attempt(self) -> None:
        """Record that a reconnect attempt is being made."""
        self._last_reconnect_attempt = time.time()

    def exit_degraded_mode(self) -> None:
        """Exit degraded mode (connection restored)."""
        self._degraded = False
