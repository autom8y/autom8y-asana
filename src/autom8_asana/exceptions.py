"""Exception hierarchy for autom8_asana SDK."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

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
    "NameNotFoundError",
    "HydrationError",
    "ResolutionError",
    # Insights API Exceptions (FR-008)
    "InsightsError",
    "InsightsValidationError",
    "InsightsNotFoundError",
    "InsightsServiceError",
    # Export API Exceptions (TDD-CONV-AUDIT-001)
    "ExportError",
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
    """Raised when an operation is rejected because the circuit breaker is open.

    Per ADR-0048: Fast-fail when service appears degraded.

    Attributes:
        backend: The backend subsystem name.
        operation: The operation that was rejected.
    """

    def __init__(
        self,
        message: str,
        *,
        backend: str = "unknown",
        operation: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.backend = backend
        self.operation = operation


class NameNotFoundError(AsanaError):
    """Raised when a resource name cannot be resolved to a GID.

    Per ADR-0060: Name resolution with per-SaveSession caching.

    Attributes:
        resource_type: Type of resource (e.g., "tag", "project", "user")
        name: Name that failed to resolve
        scope: Scope of search (workspace_gid, project_gid, etc.)
        suggestions: List of close matches (fuzzy matching suggestions)
        available_names: List of all available names in scope (for debugging)
    """

    def __init__(
        self,
        name: str,
        resource_type: str,
        scope: str,
        suggestions: list[str] | None = None,
        available_names: list[str] | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.name = name
        self.scope = scope
        self.suggestions = suggestions or []
        self.available_names = available_names or []

        msg = f"{resource_type.capitalize()} '{name}' not found in {scope}"
        if self.suggestions:
            msg += f". Did you mean: {', '.join(self.suggestions[:3])}?"
        if self.available_names and len(self.available_names) <= 20:
            msg += f" Available: {', '.join(self.available_names)}"

        super().__init__(msg)


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


class HydrationError(AsanaError):
    """Hydration operation failed.

    Per ADR-0070: Raised when hierarchy hydration fails and partial_ok=False (default).

    This exception is thrown during downward hydration (from Business to children)
    or upward traversal (from leaf entity to Business) when an unrecoverable error
    occurs.

    Attributes:
        entity_gid: GID of the entity where hydration started or failed.
        entity_type: Detected type of the entity (if known).
        phase: "downward" or "upward" indicating where failure occurred.
        partial_result: The HydrationResult with what succeeded before failure.
            Allows advanced error handlers to salvage partial data.
        cause: The underlying exception that caused the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        entity_gid: str,
        entity_type: str | None = None,
        phase: Literal["downward", "upward"],
        partial_result: Any = None,  # HydrationResult, but avoiding circular import
        cause: Exception | None = None,
    ) -> None:
        """Initialize HydrationError.

        Args:
            message: Human-readable error description.
            entity_gid: GID of the entity where hydration started or failed.
            entity_type: Detected type of the entity (if known).
            phase: "downward" or "upward" indicating where failure occurred.
            partial_result: HydrationResult with what succeeded before failure.
            cause: The underlying exception that caused the failure.
        """
        super().__init__(message)
        self.entity_gid = entity_gid
        self.entity_type = entity_type
        self.phase = phase
        self.partial_result = partial_result
        self.__cause__ = cause


class ResolutionError(AsanaError):
    """Resolution operation failed.

    Per FR-AMBIG-003: Raised on unrecoverable resolution failures (not ambiguity).

    This exception is thrown when all resolution strategies fail with errors
    and no matches were attempted successfully. Ambiguous results (multiple matches)
    are NOT raised as exceptions - they are returned as ResolutionResult with
    ambiguous=True.

    Attributes:
        entity_gid: GID of the AssetEdit being resolved.
        strategies_tried: List of strategies that were attempted.
        cause: The underlying exception that caused the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        entity_gid: str,
        strategies_tried: list[str] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize ResolutionError.

        Args:
            message: Human-readable error description.
            entity_gid: GID of the entity being resolved.
            strategies_tried: List of strategy names attempted.
            cause: The underlying exception that caused the failure.
        """
        super().__init__(message)
        self.entity_gid = entity_gid
        self.strategies_tried = strategies_tried or []
        self.__cause__ = cause


# --- Insights API Exceptions (FR-008) ---


class InsightsError(AsanaError):
    """Base exception for insights API errors.

    Per FR-008.1: Base class for all insights-related exceptions.
    Inherits from AsanaError for consistency with SDK exception hierarchy.

    Attributes:
        request_id: Request correlation ID for tracing through autom8_data.
    """

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize InsightsError.

        Args:
            message: Human-readable error description.
            request_id: Request correlation ID for tracing.
            **kwargs: Additional arguments passed to AsanaError.
        """
        super().__init__(message, **kwargs)
        self.request_id = request_id


class InsightsValidationError(InsightsError):
    """Invalid input for insights request.

    Per FR-008.2: 400-level client errors for validation failures.
    Raised when request parameters fail validation (e.g., invalid factory,
    malformed phone number, invalid period format).

    Attributes:
        field: Name of the field that failed validation (if applicable).
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize InsightsValidationError.

        Args:
            message: Human-readable error description.
            field: Name of the field that failed validation.
            **kwargs: Additional arguments passed to InsightsError.
        """
        super().__init__(message, **kwargs)
        self.field = field


class InsightsNotFoundError(InsightsError):
    """No insights data found for the requested parameters.

    Per FR-008.3: 404-level not found errors.
    Raised when no data exists for the specified PhoneVerticalPair
    and factory combination.
    """

    pass


class InsightsServiceError(InsightsError):
    """Upstream service failure from autom8_data.

    Per FR-008.4: 500-level server errors and connection failures.
    Raised when autom8_data is unavailable, times out, or returns
    a server error.

    Attributes:
        reason: Failure reason (timeout, circuit_breaker, http_error, etc.)
        status_code: HTTP status code from upstream (if available).
    """

    def __init__(
        self,
        message: str,
        *,
        reason: str | None = None,
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize InsightsServiceError.

        Args:
            message: Human-readable error description.
            reason: Failure reason category.
            status_code: HTTP status code from upstream service.
            **kwargs: Additional arguments passed to InsightsError.
        """
        # Pass status_code to parent if not already in kwargs
        if status_code is not None and "status_code" not in kwargs:
            kwargs["status_code"] = status_code
        super().__init__(message, **kwargs)
        self.reason = reason


# --- Export API Exceptions (TDD-CONV-AUDIT-001) ---


class ExportError(AsanaError):
    """Error from the conversation export endpoint.

    Per TDD-CONV-AUDIT-001 Section 3.7: Raised by
    DataServiceClient.get_export_csv_async() on HTTP errors,
    circuit breaker open, or timeout.

    Attributes:
        office_phone: The phone number that was being exported.
        reason: Classification of the error.
    """

    def __init__(
        self,
        message: str,
        *,
        office_phone: str = "",
        reason: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.office_phone = office_phone
        self.reason = reason
