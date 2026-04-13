"""Typed API-layer exceptions for canonical error responses.

These exceptions replace bare HTTPException raises across the API layer,
ensuring all error responses flow through registered exception handlers
and produce canonical ErrorResponse envelopes.

Per Domain III (Absolute Enforcement Mandate): Every error site must use
a typed exception caught by a registered handler in api/errors.py.

Hierarchy:
    ApiError (base)
    +-- ApiAuthError (401, WWW-Authenticate support)
    +-- ApiServiceUnavailableError (503, retry guidance)
    +-- ApiDataFrameBuildError (503, cache/build infrastructure)
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ApiError",
    "ApiAuthError",
    "ApiServiceUnavailableError",
    "ApiDataFrameBuildError",
]


class ApiError(Exception):
    """Base exception for API-layer errors.

    API-layer errors originate in dependencies, middleware, and
    infrastructure code (as opposed to SDK errors from upstream Asana
    or service-layer business logic errors).

    Attributes:
        code: Machine-readable error code (e.g., "MISSING_AUTH").
        message: Human-readable error description.
        status_code: HTTP status code for the response.
        details: Optional structured context merged into the error response.
        headers: Optional HTTP response headers (e.g., WWW-Authenticate).
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers


class ApiAuthError(ApiError):
    """Authentication or authorization failure (401).

    Raised by auth dependencies when credentials are missing, malformed,
    or invalid. Always includes WWW-Authenticate: Bearer header per RFC 7235.

    Error codes:
        MISSING_AUTH - No Authorization header
        INVALID_SCHEME - Not Bearer scheme
        MISSING_TOKEN - Empty token after Bearer prefix
        INVALID_TOKEN - Token fails format validation
        SERVICE_TOKEN_REQUIRED - PAT used on S2S-only endpoint
        S2S validation codes - From autom8y_auth (e.g., EXPIRED_TOKEN)
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        # Default to WWW-Authenticate: Bearer if no headers provided
        if headers is None:
            headers = {"WWW-Authenticate": "Bearer"}
        super().__init__(
            code,
            message,
            status_code=401,
            headers=headers,
        )


class ApiServiceUnavailableError(ApiError):
    """Service or infrastructure unavailability (503).

    Raised when a required service component is not configured,
    temporarily down, or otherwise unable to serve the request.

    Error codes:
        S2S_NOT_CONFIGURED - JWT auth infrastructure not available
        circuit breaker codes - From autom8y_auth CircuitOpenError
        transient auth codes - From autom8y_auth TransientAuthError
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code,
            message,
            status_code=503,
            details=details,
        )


class ApiDataFrameBuildError(ApiError):
    """DataFrame cache build infrastructure error (503).

    Raised by the dataframe_cache decorator when a cache build is
    in progress, fails, or has no build method configured.

    Error codes:
        CACHE_BUILD_IN_PROGRESS - Another request is building, retry shortly
        DATAFRAME_BUILD_UNAVAILABLE - No build method configured
        DATAFRAME_BUILD_FAILED - Build returned None
        DATAFRAME_BUILD_ERROR - Build raised an unexpected exception
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        details: dict[str, Any] | None = None
        if retry_after_seconds is not None:
            details = {"retry_after_seconds": retry_after_seconds}
        super().__init__(
            code,
            message,
            status_code=503,
            details=details,
        )
