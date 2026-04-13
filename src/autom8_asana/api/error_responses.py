"""Centralized error response catalog for OpenAPI documentation.

This module declares the standard error responses that authenticated
endpoints can return, and provides composition helpers to wire them
into route decorators via the ``responses=`` kwarg.

The runtime error handling lives in ``errors.py`` -- this module
supplies only the *documentation layer* so that OpenAPI consumers see
the correct status codes in the generated spec.

Per TDD sprint4-error-catalog: STANDARD_ERROR_RESPONSES is the single
source of truth for error response metadata.

ADR-dual-error-envelope-resolution (S3 — DOCUMENT verdict):
401 and 403 use oneOf[ErrorResponse, AuthTebError] to document both
the application-layer envelope (ErrorResponse via route handlers) and
the middleware-layer envelope (AuthTebError via JWTAuthMiddleware AUTH-TEB-NNN).
This makes the dual shape visible in the spec and enables schemathesis to
validate AUTH-TEB responses without custom hooks.
"""

from __future__ import annotations

from typing import Any

from autom8y_api_schemas import AuthTebError

from autom8_asana.api.models import ErrorResponse

# Union type for auth-protected route responses: documents both the
# application-layer ErrorResponse and the middleware-layer AuthTebError.
_AuthEnvelope = ErrorResponse | AuthTebError

STANDARD_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "model": _AuthEnvelope,
        "description": ("Unauthorized -- AUTH-TEB (JWTAuthMiddleware) or application-layer error"),
    },
    403: {
        "model": _AuthEnvelope,
        "description": ("Forbidden -- AUTH-TEB-004 (JWTAuthMiddleware) or application-layer error"),
    },
    404: {
        "model": ErrorResponse,
        "description": ("Resource not found or not accessible with the provided token"),
    },
    422: {
        "description": "Validation error -- invalid request parameters",
    },
    429: {
        "model": ErrorResponse,
        "description": ("Rate limited -- retry after the duration in the Retry-After header"),
    },
    500: {
        "model": ErrorResponse,
        "description": "Internal server error",
    },
}


def authenticated_responses() -> dict[int | str, dict[str, Any]]:
    """Error responses for any authenticated endpoint.

    Returns 401 and 403 entries. Use for list/aggregate endpoints
    that do not take a ``{gid}`` path parameter.
    """
    return {k: STANDARD_ERROR_RESPONSES[k] for k in (401, 403)}


def entity_responses() -> dict[int | str, dict[str, Any]]:
    """Error responses for endpoints that resolve a single entity by GID.

    Returns 401, 403, and 404 entries. Use for any endpoint with a
    ``{gid}`` path parameter.
    """
    return {k: STANDARD_ERROR_RESPONSES[k] for k in (401, 403, 404)}


def mutation_responses() -> dict[int | str, dict[str, Any]]:
    """Error responses for POST/PUT endpoints with a request body.

    Returns 401, 403, and 422 entries. The 422 entry uses
    ``description`` only (no ``model``) to avoid conflicting with
    FastAPI's auto-generated ``HTTPValidationError``.
    """
    return {k: STANDARD_ERROR_RESPONSES[k] for k in (401, 403, 422)}


def rate_limited_responses() -> dict[int | str, dict[str, Any]]:
    """Error responses for endpoints with known rate-limit exposure.

    Returns 401, 403, and 429 entries. Use for endpoints that proxy
    to the Asana API with rate-limit exposure.
    """
    return {k: STANDARD_ERROR_RESPONSES[k] for k in (401, 403, 429)}


__all__ = [
    "STANDARD_ERROR_RESPONSES",
    "authenticated_responses",
    "entity_responses",
    "mutation_responses",
    "rate_limited_responses",
]
