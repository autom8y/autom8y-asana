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

router = s2s_router(prefix="/api/v1/internal", tags=["internal"], include_in_schema=False)


# --- Service Claims Model ---


class ServiceClaims(BaseModel):
    """Claims extracted from a validated service token.

    RE-2 / DEV-1 (design §5.1 L1-1, "un-loss the claims model"): this is a
    LOCAL narrowing of ``autom8y_auth.claims.ServiceClaims``, not the SDK model.
    Before DEV-1 it copied only ``sub``/``service_name``/``scope``/
    ``permissions`` and dropped everything else — including ``client_id``, the
    issuer-asserted key the fleet authorizes on
    (``SCHEDULING_ENROLLMENT_WRITER_CLIENT_IDS``,
    ``services/auth/service-accounts.yaml:680-683``). That lossiness was
    load-bearing: the authorization key was discarded before any route could
    see it, so no route *could* have made an authorization decision on it.

    ``client_id`` is carried so that write-class authorization
    (``api/write_authz.py``) has a signature-covered principal to key on.

    Note on ``service_account_id``: the canonical ``sa.yaml_id`` is emitted by
    the auth service but is NOT a field on the SDK's ``ServiceClaims``, which
    declares ``extra="ignore"`` and therefore drops it during validation. It
    survives only on ``request.state.claims_dict`` (populated by
    ``JWTAuthMiddleware``), which is where ``resolve_principal`` reads it —
    the same precedence already proven at ``idempotency.py:508-530`` and
    documented at ``rate_limit.py:25-46``. It is deliberately NOT mirrored onto
    this model, because doing so would fabricate a field the SDK never
    populates and invite a silent ``None`` to be read as an identity.

    Attributes:
        sub: Subject (service identifier — the SA UUID).
        service_name: Name of the calling service. On the SDK model this is a
            ``@property`` returning ``sub`` (``claims.py:183-185``); it is NOT
            an independently issuer-asserted claim. See ``rate_limit.py:42-46``
            for the prior in-repo defect caused by treating it as one.
        scope: RFC 6749 scope claim. Carried for LOGGING ONLY. It must never be
            used for an authorization decision — ``scope == "*"`` is a legacy
            wildcard sentinel that makes ``has_scope`` fail open
            (``claims.py:220-222``); see the axis ruling in
            ``api/write_authz.py``.
        permissions: Service permissions populated from ServiceAccount scopes.
            Used for fine-grained authorization on privileged routes
            (e.g., super-admin gating on /v1/admin/cache/refresh per
            Bedrock W4C-P3 / SEC-DT-10), and the layer-2 axis for write-class
            authorization (plain membership, no wildcard).
        client_id: ServiceAccount ``client_id``, present on ServiceAccount
            tokens. Issuer-asserted and signature-covered. Tier-2 principal for
            write-class authorization.
    """

    sub: str
    service_name: str
    scope: str | None = None
    permissions: list[str] = []
    client_id: str | None = None


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
    except Exception as e:  # BROAD-CATCH: boundary  # noqa: BLE001
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

    # RE-2 / DEV-1: carry `client_id` across the narrowing.
    #
    # The isinstance() narrowing is load-bearing, not defensive clutter. An
    # authorization key must be a genuine string or absent — never a duck-typed
    # object. Without it, any object exposing a `client_id` attribute (a stub, a
    # proxy, a partially-populated model) would be admitted here and later
    # compared against the writer allowlist, where `__eq__` is the object's to
    # define. Anything that is not a `str` degrades to None, which
    # `resolve_principal` reads as "tier absent" and falls through to `sub`. It
    # never yields a spurious identity.
    raw_client_id = getattr(claims, "client_id", None)
    return ServiceClaims(
        sub=claims.sub,
        service_name=claims.service_name,
        scope=claims.scope,
        permissions=list(claims.permissions),
        client_id=raw_client_id if isinstance(raw_client_id, str) else None,
    )


__all__ = [
    # Router
    "router",
    # Models
    "ServiceClaims",
    # Dependencies
    "require_service_claims",
]
