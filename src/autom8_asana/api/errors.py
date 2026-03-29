"""Exception handlers for API error responses.

This module centralizes exception handling for the API layer, mapping
SDK exceptions to HTTP responses with appropriate status codes.

Per ADR-ASANA-004: Error Handling and HTTP Mapping
| SDK Exception        | HTTP Status | Error Code          |
|---------------------|-------------|---------------------|
| NotFoundError       | 404         | RESOURCE_NOT_FOUND  |
| AuthenticationError | 401         | INVALID_CREDENTIALS |
| ForbiddenError      | 403         | FORBIDDEN           |
| RateLimitError      | 429         | RATE_LIMITED        |
| GidValidationError  | 400         | VALIDATION_ERROR    |
| ServerError         | 502         | UPSTREAM_ERROR      |
| TimeoutError        | 504         | UPSTREAM_TIMEOUT    |
| Exception (catch-all)| 500        | INTERNAL_ERROR      |

Per PRD-ASANA-SATELLITE (FR-ERR-008):
- All error responses include request_id for correlation

Per PRD-ASANA-SATELLITE (FR-ERR-009):
- Generic 500 responses hide implementation details

Per ADR-I6-001: API Error Response Convention
- raise_api_error() for route-level validation/precondition errors
- raise_service_error() for ServiceError conversion with request_id
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Never

from autom8y_http import RequestError
from autom8y_log import get_logger
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)
from autom8_asana.persistence.exceptions import GidValidationError

from .exceptions import (
    ApiAuthError,
    ApiDataFrameBuildError,
    ApiError,
    ApiServiceUnavailableError,
)
from .models import ErrorDetail, ErrorResponse, ResponseMeta

if TYPE_CHECKING:
    from autom8_asana.services.errors import ServiceError

logger = get_logger(__name__)


def _build_error_response(
    request: Request,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build error response dict from components.

    Args:
        request: FastAPI request (for request_id).
        code: Machine-readable error code.
        message: Human-readable error message.
        details: Additional error context.

    Returns:
        Dict suitable for JSONResponse content.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    return ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
        ),
        meta=ResponseMeta(request_id=request_id),
    ).model_dump(mode="json")


def raise_api_error(
    request_id: str,
    status_code: int,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Never:
    """Raise HTTPException with consistent error format.

    Ensures all route-level error responses include:
    - Machine-readable error code
    - Human-readable message
    - request_id for correlation (per FR-ERR-008)

    Per ADR-I6-001: Used for Tier 2 (ServiceError conversion) and
    Tier 3 (route-specific validation/precondition checks).

    Args:
        request_id: Request ID string (from RequestId dependency).
        status_code: HTTP status code.
        code: Machine-readable error code (e.g., "INVALID_ENTITY_TYPE").
        message: Human-readable error description.
        details: Additional structured context (optional). Merged into detail dict.
        headers: Additional HTTP headers (e.g., Retry-After).

    Raises:
        HTTPException: Always raised, never returns.
    """
    detail: dict[str, Any] = {
        "error": code,
        "message": message,
        "request_id": request_id,
    }
    if details:
        detail.update(details)
    raise HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers,
    )


def raise_service_error(
    request_id: str,
    error: ServiceError,
    *,
    headers: dict[str, str] | None = None,
) -> Never:
    """Raise HTTPException from a ServiceError with consistent format.

    Convenience wrapper for the common pattern of catching ServiceError
    and converting to HTTPException. Preserves all fields from
    error.to_dict() and injects request_id.

    Per ADR-I6-001 Tier 2: Preferred for routes that delegate to a
    service layer raising domain exceptions.

    Args:
        request_id: Request ID string (from RequestId dependency).
        error: ServiceError instance with error_code, message, and to_dict().
        headers: Additional HTTP headers.

    Raises:
        HTTPException: Always raised.
    """
    from autom8_asana.services.errors import get_status_for_error

    detail = error.to_dict()
    detail["request_id"] = request_id
    raise HTTPException(
        status_code=get_status_for_error(error),
        detail=detail,
        headers=headers,
    )


async def not_found_handler(
    request: Request,
    exc: NotFoundError,
) -> JSONResponse:
    """Handle NotFoundError -> 404 RESOURCE_NOT_FOUND.

    Args:
        request: FastAPI request object.
        exc: NotFoundError from SDK.

    Returns:
        404 JSONResponse with structured error.
    """
    return JSONResponse(
        status_code=404,
        content=_build_error_response(
            request,
            code="RESOURCE_NOT_FOUND",
            message=str(exc),
        ),
    )


async def authentication_error_handler(
    request: Request,
    exc: AuthenticationError,
) -> JSONResponse:
    """Handle AuthenticationError -> 401 INVALID_CREDENTIALS.

    Per RFC 7235: Include WWW-Authenticate header.

    Args:
        request: FastAPI request object.
        exc: AuthenticationError from SDK (invalid/expired PAT).

    Returns:
        401 JSONResponse with WWW-Authenticate header.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "authentication_failed",
        extra={
            "request_id": request_id,
            "error_code": "INVALID_CREDENTIALS",
        },
    )
    return JSONResponse(
        status_code=401,
        content=_build_error_response(
            request,
            code="INVALID_CREDENTIALS",
            message="Invalid or expired Asana credentials",
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )


async def forbidden_error_handler(
    request: Request,
    exc: ForbiddenError,
) -> JSONResponse:
    """Handle ForbiddenError -> 403 FORBIDDEN.

    Args:
        request: FastAPI request object.
        exc: ForbiddenError from SDK (valid PAT but insufficient permissions).

    Returns:
        403 JSONResponse with structured error.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "authorization_failed",
        extra={
            "request_id": request_id,
            "error_code": "FORBIDDEN",
        },
    )
    return JSONResponse(
        status_code=403,
        content=_build_error_response(
            request,
            code="FORBIDDEN",
            message=str(exc),
        ),
    )


async def rate_limit_error_handler(
    request: Request,
    exc: RateLimitError,
) -> JSONResponse:
    """Handle RateLimitError -> 429 RATE_LIMITED.

    Per PRD-ASANA-SATELLITE (FR-ERR-004): Include Retry-After header.

    Args:
        request: FastAPI request object.
        exc: RateLimitError from SDK (Asana rate limit hit).

    Returns:
        429 JSONResponse with Retry-After header.
    """
    retry_after = getattr(exc, "retry_after", None) or 60
    return JSONResponse(
        status_code=429,
        content=_build_error_response(
            request,
            code="RATE_LIMITED",
            message="Rate limit exceeded. Please retry later.",
            details={"retry_after": retry_after},
        ),
        headers={"Retry-After": str(retry_after)},
    )


async def validation_error_handler(
    request: Request,
    exc: GidValidationError,
) -> JSONResponse:
    """Handle GidValidationError -> 400 VALIDATION_ERROR.

    Args:
        request: FastAPI request object.
        exc: GidValidationError from SDK (invalid GID format).

    Returns:
        400 JSONResponse with structured error.
    """
    return JSONResponse(
        status_code=400,
        content=_build_error_response(
            request,
            code="VALIDATION_ERROR",
            message=str(exc),
        ),
    )


async def server_error_handler(
    request: Request,
    exc: ServerError,
) -> JSONResponse:
    """Handle ServerError -> 502 UPSTREAM_ERROR.

    Args:
        request: FastAPI request object.
        exc: ServerError from SDK (Asana returned 5xx).

    Returns:
        502 JSONResponse with structured error.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "upstream_error",
        extra={
            "request_id": request_id,
            "error_code": "UPSTREAM_ERROR",
            "upstream_status": getattr(exc, "status_code", None),
        },
    )
    return JSONResponse(
        status_code=502,
        content=_build_error_response(
            request,
            code="UPSTREAM_ERROR",
            message="Asana API is currently unavailable",
        ),
    )


async def timeout_error_handler(
    request: Request,
    exc: TimeoutError,
) -> JSONResponse:
    """Handle TimeoutError -> 504 UPSTREAM_TIMEOUT.

    Args:
        request: FastAPI request object.
        exc: TimeoutError from SDK (request timed out).

    Returns:
        504 JSONResponse with structured error.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "upstream_timeout",
        extra={
            "request_id": request_id,
            "error_code": "UPSTREAM_TIMEOUT",
        },
    )
    return JSONResponse(
        status_code=504,
        content=_build_error_response(
            request,
            code="UPSTREAM_TIMEOUT",
            message="Request to Asana API timed out",
        ),
    )


async def request_error_handler(
    request: Request,
    exc: RequestError,
) -> JSONResponse:
    """Handle httpx RequestError -> 502 UPSTREAM_ERROR.

    Args:
        request: FastAPI request object.
        exc: RequestError from httpx (network/connection failure).

    Returns:
        502 JSONResponse with structured error.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "network_error",
        extra={
            "request_id": request_id,
            "error_code": "UPSTREAM_ERROR",
            "error_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=502,
        content=_build_error_response(
            request,
            code="UPSTREAM_ERROR",
            message="Failed to connect to Asana API",
        ),
    )


async def asana_error_handler(
    request: Request,
    exc: AsanaError,
) -> JSONResponse:
    """Handle generic AsanaError -> 500 INTERNAL_ERROR.

    Catches any AsanaError subclass not handled by specific handlers.

    Args:
        request: FastAPI request object.
        exc: AsanaError from SDK.

    Returns:
        500 JSONResponse with structured error.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "unhandled_asana_error",
        extra={
            "request_id": request_id,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        },
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            request,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ),
    )


async def generic_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all handler for unexpected exceptions.

    Per PRD-ASANA-SATELLITE (FR-ERR-009):
    - Returns 500 without exposing stack trace
    - Logs full exception for debugging

    Args:
        request: FastAPI request object.
        exc: Any unhandled exception.

    Returns:
        500 JSONResponse with generic error message.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            request,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ),
    )


# ---------------------------------------------------------------------------
# API-layer exception handlers (Domain III: Absolute Enforcement Mandate)
# ---------------------------------------------------------------------------


async def api_auth_error_handler(
    request: Request,
    exc: ApiAuthError,
) -> JSONResponse:
    """Handle ApiAuthError -> 401 with WWW-Authenticate header.

    Replaces bare HTTPException(401) sites in auth dependencies.
    Produces canonical ErrorResponse with request_id correlation.

    Args:
        request: FastAPI request object.
        exc: ApiAuthError from auth dependency.

    Returns:
        401 JSONResponse with canonical error envelope and
        WWW-Authenticate header (per RFC 7235).
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "api_auth_error",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
        headers=exc.headers,
    )


async def api_service_unavailable_handler(
    request: Request,
    exc: ApiServiceUnavailableError,
) -> JSONResponse:
    """Handle ApiServiceUnavailableError -> 503.

    Replaces bare HTTPException(503) sites in auth and infrastructure code.

    Args:
        request: FastAPI request object.
        exc: ApiServiceUnavailableError from infrastructure layer.

    Returns:
        503 JSONResponse with canonical error envelope.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "api_service_unavailable",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def api_dataframe_build_error_handler(
    request: Request,
    exc: ApiDataFrameBuildError,
) -> JSONResponse:
    """Handle ApiDataFrameBuildError -> 503.

    Replaces bare HTTPException(503) sites in the dataframe_cache decorator.

    Args:
        request: FastAPI request object.
        exc: ApiDataFrameBuildError from cache infrastructure.

    Returns:
        503 JSONResponse with canonical error envelope and retry guidance.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "api_dataframe_build_error",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def api_error_handler(
    request: Request,
    exc: ApiError,
) -> JSONResponse:
    """Handle generic ApiError (catch-all for API-layer exceptions).

    Catches any ApiError subclass not handled by specific handlers above.

    Args:
        request: FastAPI request object.
        exc: ApiError from API layer.

    Returns:
        JSONResponse with appropriate status code and canonical error envelope.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "api_error",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
            "status_code": exc.status_code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.

    Order matters: more specific handlers are registered first,
    with the catch-all handler registered last.

    Args:
        app: FastAPI application instance.
    """
    # SDK-specific errors (most specific first)
    app.exception_handler(NotFoundError)(not_found_handler)
    app.exception_handler(AuthenticationError)(authentication_error_handler)
    app.exception_handler(ForbiddenError)(forbidden_error_handler)
    app.exception_handler(RateLimitError)(rate_limit_error_handler)
    app.exception_handler(GidValidationError)(validation_error_handler)
    app.exception_handler(ServerError)(server_error_handler)
    app.exception_handler(TimeoutError)(timeout_error_handler)

    # Network errors
    app.exception_handler(RequestError)(request_error_handler)

    # Generic AsanaError (catches unhandled SDK errors)
    app.exception_handler(AsanaError)(asana_error_handler)

    # API-layer errors (Domain III: typed exceptions replace bare HTTPException)
    app.exception_handler(ApiAuthError)(api_auth_error_handler)
    app.exception_handler(ApiServiceUnavailableError)(api_service_unavailable_handler)
    app.exception_handler(ApiDataFrameBuildError)(api_dataframe_build_error_handler)
    app.exception_handler(ApiError)(api_error_handler)

    # Catch-all must be last
    app.exception_handler(Exception)(generic_error_handler)


__all__ = [
    "raise_api_error",
    "raise_service_error",
    "register_exception_handlers",
    # Individual handlers (for testing)
    "asana_error_handler",
    "authentication_error_handler",
    "forbidden_error_handler",
    "generic_error_handler",
    "not_found_handler",
    "rate_limit_error_handler",
    "request_error_handler",
    "server_error_handler",
    "timeout_error_handler",
    "validation_error_handler",
    # API-layer handlers (Domain III)
    "api_auth_error_handler",
    "api_service_unavailable_handler",
    "api_dataframe_build_error_handler",
    "api_error_handler",
]
