"""Internal routes for S2S communication.

This module provides internal endpoints used by other autom8 services.
The Entity Resolver endpoint (/api/v1/resolver) has replaced the legacy
gid-lookup endpoint for GID resolution.

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported for internal routes
"""

from __future__ import annotations

from autom8y_log import get_logger
from fastapi import (
    Request,  # noqa: TC002 — FastAPI resolves Request annotation via get_type_hints() at route registration; moving behind TYPE_CHECKING would raise NameError
)
from pydantic import BaseModel

from autom8_asana.api.exception_types import ApiAuthError, ApiServiceUnavailableError
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.auth.dual_mode import AuthMode, detect_token_type
from autom8_asana.auth.jwt_validator import validate_service_token

logger = get_logger("autom8_asana.api.internal")

router = s2s_router(
    prefix="/api/v1/internal", tags=["internal"], include_in_schema=False
)


# --- Service Claims Model ---


class ServiceClaims(BaseModel):
    """Claims extracted from a validated service token.

    Attributes:
        sub: Subject (service identifier)
        service_name: Name of the calling service
        scope: Permission scope (e.g., multi-tenant)
    """

    sub: str
    service_name: str
    scope: str | None = None


# --- Authentication Dependencies ---


async def _extract_bearer_token(request: Request) -> str:
    """Extract Bearer token from Authorization header.

    Args:
        request: FastAPI request object.

    Returns:
        Token string (without Bearer prefix).

    Raises:
        ApiAuthError: 401 if header missing or invalid.
    """
    auth_header = request.headers.get("Authorization")

    if auth_header is None:
        raise ApiAuthError("MISSING_AUTH", "Authorization header required")

    if not auth_header.startswith("Bearer "):
        raise ApiAuthError("INVALID_SCHEME", "Bearer scheme required")

    token = auth_header[7:]  # Remove "Bearer " prefix

    if not token:
        raise ApiAuthError("MISSING_TOKEN", "Token is required")

    return token


async def require_service_claims(request: Request) -> ServiceClaims:
    """Require valid service token (S2S) and return claims.

    This dependency is for internal routes that should ONLY be called
    by other autom8 services, not by end users with PAT tokens.

    Args:
        request: FastAPI request object.

    Returns:
        ServiceClaims with validated service information.

    Raises:
        ApiAuthError: 401 if token is missing, invalid, or not a JWT.
        ApiServiceUnavailableError: 503 if S2S auth is not configured.
    """
    token = await _extract_bearer_token(request)
    request_id = getattr(request.state, "request_id", "unknown")

    # Check if this is a JWT (S2S) or PAT (user)
    auth_mode = detect_token_type(token)

    if auth_mode == AuthMode.PAT:
        # PAT tokens are not allowed for internal routes
        logger.warning(
            "internal_route_pat_rejected",
            extra={
                "request_id": request_id,
                "reason": "PAT tokens not allowed for internal routes",
            },
        )
        raise ApiAuthError(
            "SERVICE_TOKEN_REQUIRED",
            "This endpoint requires service-to-service authentication. "
            "PAT tokens are not supported.",
        )

    # Validate JWT and extract claims
    try:
        claims = await validate_service_token(token)
    except ImportError as e:
        logger.error(
            "autom8y_auth_not_installed",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise ApiServiceUnavailableError(
            "S2S_NOT_CONFIGURED",
            "Service-to-service authentication is not available",
        )
    except Exception as e:  # BROAD-CATCH: boundary
        # Try to get error code from autom8y_auth exceptions
        error_code = getattr(e, "code", "UNKNOWN_ERROR")
        logger.warning(
            "s2s_jwt_validation_failed",
            extra={
                "request_id": request_id,
                "error_code": error_code,
                "error_message": str(e),
            },
        )
        raise ApiAuthError(error_code, "JWT validation failed")

    logger.info(
        "internal_route_authenticated",
        extra={
            "request_id": request_id,
            "caller_service": claims.service_name,
            "scope": claims.scope,
        },
    )

    return ServiceClaims(
        sub=claims.sub,
        service_name=claims.service_name,
        scope=claims.scope,
    )


__all__ = [
    # Router
    "router",
    # Models
    "ServiceClaims",
    # Dependencies
    "require_service_claims",
]
