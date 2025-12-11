"""Exception hierarchy for autom8_asana SDK."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from httpx import Response

__all__ = [
    "AsanaError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "GoneError",
    "RateLimitError",
    "ServerError",
    "TimeoutError",
    "ConfigurationError",
    "SyncInAsyncContextError",
    "CircuitBreakerOpenError",
]


class AsanaError(Exception):
    """Base exception for all Asana API errors.

    Attributes:
        message: Human-readable error description
        status_code: HTTP status code (if from API response)
        response: Raw httpx Response object (if available)
        errors: List of error details from Asana API
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response: Response | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.errors = errors or []

    @classmethod
    def from_response(cls, response: Response) -> AsanaError:
        """Create appropriate exception from httpx Response.

        Parses the response body and returns the most specific
        exception subclass based on status code. Includes debugging
        context: HTTP status, request ID, and body snippet.
        """
        status = response.status_code
        errors: list[dict[str, Any]] = []
        request_id = response.headers.get("X-Request-Id")

        # Build context prefix for error message
        context_parts = [f"HTTP {status}"]
        if request_id:
            context_parts.append(f"request_id={request_id}")
        context = ", ".join(context_parts)

        # Default message with context
        message = f"Asana API error ({context})"

        try:
            body = response.json()
            if "errors" in body and isinstance(body["errors"], list):
                errors = body["errors"]
                messages = [e.get("message", "Unknown error") for e in errors]
                error_detail = "; ".join(messages)
                message = f"{error_detail} ({context})"
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            # Include body snippet for debugging when JSON parsing fails
            # UnicodeDecodeError can occur with invalid UTF-8 in response body
            try:
                body_text = response.text
            except UnicodeDecodeError:
                # Fallback: decode with replacement characters for truly invalid data
                body_text = response.content.decode("utf-8", errors="replace")
            if body_text:
                body_snippet = body_text[:200]
                if len(body_text) > 200:
                    body_snippet += "..."
                message = f"Asana API error ({context}): {body_snippet}"

        # Map to specific exception types
        exception_class = _STATUS_CODE_MAP.get(status, AsanaError)
        return exception_class(
            message,
            status_code=status,
            response=response,
            errors=errors,
        )


class AuthenticationError(AsanaError):
    """Authentication failed (401)."""
    pass


class ForbiddenError(AsanaError):
    """Access denied (403)."""
    pass


class NotFoundError(AsanaError):
    """Resource not found (404)."""
    pass


class GoneError(AsanaError):
    """Resource permanently deleted (410)."""
    pass


class RateLimitError(AsanaError):
    """Rate limit exceeded (429).

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header)
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

    @classmethod
    def from_response(cls, response: Response) -> RateLimitError:
        """Create RateLimitError with retry_after from headers."""
        base = AsanaError.from_response(response)
        retry_after = None
        if "retry-after" in response.headers:
            try:
                retry_after = int(response.headers["retry-after"])
            except ValueError:
                pass
        return cls(
            base.message,
            status_code=base.status_code,
            response=base.response,
            errors=base.errors,
            retry_after=retry_after,
        )


class ServerError(AsanaError):
    """Server-side error (5xx)."""
    pass


class TimeoutError(AsanaError):
    """Request timed out."""
    pass


class ConfigurationError(AsanaError):
    """SDK configuration error (not an API error)."""
    pass


class SyncInAsyncContextError(RuntimeError):
    """Raised when sync wrapper is called from async context.

    Per ADR-0002, sync wrappers fail fast in async contexts
    to prevent deadlocks.
    """

    def __init__(self, method_name: str, async_method_name: str) -> None:
        super().__init__(
            f"Cannot call sync method '{method_name}' from async context. "
            f"Use 'await {async_method_name}(...)' instead."
        )


class CircuitBreakerOpenError(AsanaError):
    """Raised when circuit breaker is open.

    Per ADR-0048: Fast-fail when service appears degraded.

    Attributes:
        time_until_recovery: Seconds until circuit breaker enters half-open state
    """

    def __init__(self, time_until_recovery: float) -> None:
        self.time_until_recovery = time_until_recovery
        super().__init__(
            f"Circuit breaker open. Service appears degraded. "
            f"Retry in {time_until_recovery:.1f}s. "
            f"Check Asana status: https://status.asana.com/"
        )


# Status code to exception class mapping
_STATUS_CODE_MAP: dict[int, type[AsanaError]] = {
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    410: GoneError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}
