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
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from autom8_asana.auth.dual_mode import AuthMode, detect_token_type
from autom8_asana.auth.jwt_validator import validate_service_token

logger = get_logger("autom8_asana.api.internal")

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


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
        HTTPException: 401 if header missing or invalid.
    """
    auth_header = request.headers.get("Authorization")

    if auth_header is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "MISSING_AUTH", "message": "Authorization header required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_SCHEME", "message": "Bearer scheme required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # Remove "Bearer " prefix

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": "MISSING_TOKEN", "message": "Token is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

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
        HTTPException: 401 if token is missing, invalid, or not a JWT.
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
        raise HTTPException(
            status_code=401,
            detail={
                "error": "SERVICE_TOKEN_REQUIRED",
                "message": "This endpoint requires service-to-service authentication. "
                "PAT tokens are not supported.",
            },
            headers={"WWW-Authenticate": "Bearer"},
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
        raise HTTPException(
            status_code=503,
            detail={
                "error": "S2S_NOT_CONFIGURED",
                "message": "Service-to-service authentication is not available",
            },
        )
    except Exception as e:
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
        raise HTTPException(
            status_code=401,
            detail={
                "error": error_code,
                "message": "JWT validation failed",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

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
