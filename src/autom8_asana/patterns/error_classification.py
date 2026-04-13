"""Error classification mixin for retryable error handling.

Per Initiative DESIGN-PATTERNS-B: Eliminates duplicated is_retryable,
recovery_hint, and retry_after_seconds logic from SaveError and ActionResult.

Per ADR-0079: Classification based on HTTP status code semantics.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class HasError(Protocol):
    """Protocol for types that may contain an error.

    Classes implementing this protocol can use RetryableErrorMixin
    to gain error classification capabilities.

    The _get_error() method should return:
    - The error exception if one is present
    - None if no error (e.g., successful operation)
    """

    @abstractmethod
    def _get_error(self) -> Exception | None:
        """Return the error if present, None otherwise."""
        ...


class RetryableErrorMixin:
    """Mixin providing error classification and recovery hints.

    Classes using this mixin must implement _get_error() to return
    the error to be classified, or None for successful operations.

    Provides:
    - is_retryable: Whether the error can be retried
    - recovery_hint: Human-readable recovery guidance
    - retry_after_seconds: Delay before retry (for rate limits)

    Per ADR-0079: Classification based on HTTP status code semantics.
    Per FR-FH-002: 429 errors classified as retryable.
    Per FR-FH-003: 5xx errors classified as retryable.
    Per FR-FH-004: 4xx errors (except 429) not retryable.
    """

    @abstractmethod
    def _get_error(self) -> Exception | None:
        """Return the error if present, None otherwise.

        Subclasses must implement this to provide the error to classify.
        Return None for successful operations (is_retryable will be False).
        """
        ...

    @property
    def is_retryable(self) -> bool:
        """Determine if this error is potentially retryable.

        Per ADR-0079: Classification based on HTTP status code semantics.

        Classification:
        - Network errors (TimeoutError, ConnectionError, OSError): Retryable
        - 429 Rate Limit: Retryable
        - 5xx Server Errors: Retryable
        - 4xx Client Errors: Not retryable
        - Unknown errors (no status code): Not retryable

        Returns:
            True if error type suggests retry may succeed.
            Always False for successful operations (no error).
        """
        error = self._get_error()
        if error is None:
            return False

        # Network errors are retryable (transient failures)
        if isinstance(error, (TimeoutError, ConnectionError, OSError)):
            return True

        status_code = self._extract_status_code(error)
        if status_code is None:
            return False  # Unknown errors are not retryable

        # Rate limit is retryable
        if status_code == 429:
            return True

        # Server errors are retryable; client errors are not
        return 500 <= status_code < 600

    @property
    def recovery_hint(self) -> str:
        """Provide guidance for recovering from this error.

        Returns actionable advice based on the error type and status code.

        Returns:
            Human-readable recovery guidance string.
            Empty string for successful operations (no error).
        """
        error = self._get_error()
        if error is None:
            return ""

        # Network error hints
        if isinstance(error, TimeoutError):
            return "Request timed out. Retry with exponential backoff."
        if isinstance(error, ConnectionError):
            return "Connection failed. Check network connectivity and retry."
        if isinstance(error, OSError):
            return "Network error. Check connectivity and retry."

        status_code = self._extract_status_code(error)
        if status_code is None:
            return "Unknown error. Inspect the error attribute for details."

        # Status code specific hints
        hints: dict[int, str] = {
            400: "Bad request. Check payload format and required fields.",
            401: "Authentication failed. Verify API credentials.",
            403: "Permission denied. Check workspace/project access permissions.",
            404: "Resource not found. Verify the GID exists.",
            409: "Conflict detected. Resource may have been modified. Refresh and retry.",
            429: "Rate limit exceeded. Wait for retry_after_seconds and retry.",
            500: "Server error. Retry with exponential backoff.",
            502: "Bad gateway. Retry with exponential backoff.",
            503: "Service unavailable. Retry with exponential backoff.",
            504: "Gateway timeout. Retry with exponential backoff.",
        }

        if status_code in hints:
            return hints[status_code]

        if 400 <= status_code < 500:
            return f"Client error ({status_code}). Check request parameters."
        if 500 <= status_code < 600:
            return f"Server error ({status_code}). Retry with exponential backoff."

        return f"HTTP {status_code}. Inspect the error attribute for details."

    @property
    def retry_after_seconds(self) -> int | None:
        """Get recommended wait time before retry (for rate limits).

        Per ADR-0079: Extracts retry_after from RateLimitError when available.

        Returns:
            Seconds to wait before retrying, or None if not applicable.
        """
        error = self._get_error()
        if error is None:
            return None
        return getattr(error, "retry_after", None)

    @staticmethod
    def _extract_status_code(error: Exception) -> int | None:
        """Extract HTTP status code from error.

        Handles AsanaError and generic exceptions with status_code attribute.

        Args:
            error: The exception to extract status code from.

        Returns:
            HTTP status code or None if not available.
        """
        # Lazy import to avoid circular dependency
        from autom8_asana.errors import AsanaError

        if isinstance(error, AsanaError):
            return error.status_code

        # Check for status_code attribute on generic exceptions
        if hasattr(error, "status_code"):
            status = error.status_code
            if isinstance(status, int):
                return status

        return None
