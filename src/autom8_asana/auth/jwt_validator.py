"""JWT validation using autom8y-auth SDK.

This module wraps the autom8y-auth SDK to provide JWT validation
for service-to-service (S2S) requests. It handles:
- Lazy initialization of the AuthClient
- JWKS caching (managed by SDK, 5-minute TTL + stale cache fallback)
- Thread-safe singleton pattern

Per TDD-auth-v1-migration Section 4.1:
- Uses AuthSettings() for configuration (v1.0 API)
- Validates service tokens specifically
- Logs validation events (not token values)

Per ADR-S2S-001: No custom JWT validation logic - delegate entirely to SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8y_auth import AuthClient, ServiceClaims

logger = get_logger("autom8_asana.auth")

# Module-level client (lazy initialized, thread-safe)
_auth_client: AuthClient | None = None


def _get_auth_client() -> AuthClient:
    """Get or create the auth client using environment config.

    Thread-safe lazy initialization. Client is reused across requests.
    JWKS caching is handled by the SDK (5-minute TTL by default,
    configurable via AUTH__CACHE__TTL_SECONDS).

    Returns:
        AuthClient instance configured from environment.

    Raises:
        ImportError: If autom8y-auth SDK is not installed.
    """
    global _auth_client
    if _auth_client is None:
        from autom8y_auth import AuthClient, AuthSettings

        settings = AuthSettings()
        _auth_client = AuthClient(settings)
        logger.debug(
            "auth_client_initialized",
            extra={
                "issuer": settings.issuer,
                "jwks_url": settings.jwks_url,
                "dev_mode": settings.dev_mode,
            },
        )
    return _auth_client


async def validate_service_token(token: str) -> ServiceClaims:
    """Validate JWT and return service claims.

    Args:
        token: JWT token string (without Bearer prefix)

    Returns:
        ServiceClaims with sub, scope, service_name, etc.

    Raises:
        autom8y_auth.AuthError: Base class for all validation errors
            - InvalidSignatureError: Signature verification failed
            - TokenExpiredError: Token has expired
            - InvalidIssuerError: Issuer mismatch
            - UnknownKeyIDError: Key ID not in JWKS
            - InvalidTokenTypeError: Not a service token
            - JWKSFetchError: Cannot reach JWKS endpoint
    """
    client = _get_auth_client()

    # Validate and ensure it's a service token
    claims = await client.validate_service_token(token)

    # Log success without sensitive data
    logger.debug(
        "s2s_jwt_validated",
        extra={
            "caller_service": claims.service_name,
            "scope": claims.scope,
        },
    )

    return claims


def reset_auth_client() -> None:
    """Reset the auth client singleton.

    For testing only. Allows tests to reinitialize the client
    with different configuration.
    """
    global _auth_client
    if _auth_client is not None:
        # Note: We don't await close() here because this is a sync function.
        # In production, the client lives for the process lifetime.
        # In tests, the client is lightweight and GC handles cleanup.
        pass
    _auth_client = None


__all__ = [
    "validate_service_token",
    "reset_auth_client",
]
