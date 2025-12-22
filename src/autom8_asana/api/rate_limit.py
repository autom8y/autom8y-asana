"""Rate limiting for API endpoints.

This module provides service-level rate limiting using SlowAPI.

Per TDD-ASANA-SATELLITE (FR-SVC-005):
- Service-level rate limiting via SlowAPI
- Default 100 requests per minute per client
- Returns 429 with Retry-After header when exceeded

Per ADR-ASANA-003: Layered Rate Limiting
- Service layer (this module): Protects our infrastructure
- SDK layer: Respects Asana's rate limits (1500 req/60s)
- Different concerns, defense in depth
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import get_settings


def _get_rate_limit_key(request: Request) -> str:
    """Generate rate limit key from request.

    Key is based on:
    1. First 8 chars of PAT (if Bearer auth present) - user isolation
    2. Remote IP address (fallback for unauthenticated requests)

    Per ADR-ASANA-002: Different PATs should have independent rate limits
    since they represent different Asana users.

    Args:
        request: FastAPI request object.

    Returns:
        Rate limit key string.
    """
    # Try to extract PAT prefix for user isolation
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer ") and len(auth_header) > 15:
        # Use first 8 chars of token as identifier (safe to log)
        token_prefix = auth_header[7:15]
        return f"pat:{token_prefix}"

    # Fallback to IP for unauthenticated requests (e.g., /health)
    ip = get_remote_address(request)
    return f"ip:{ip}"


def _get_rate_limit_string() -> str:
    """Get rate limit string from settings.

    Returns:
        Rate limit string (e.g., "100/minute").
    """
    settings = get_settings()
    return f"{settings.rate_limit_rpm}/minute"


# Create limiter instance
# Uses in-memory storage by default (suitable for single-instance v1)
# For multi-instance, configure Redis: Limiter(storage_uri="redis://...")
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[_get_rate_limit_string()],
    enabled=True,
)


def get_limiter() -> Limiter:
    """Get the configured rate limiter instance.

    Returns:
        Configured SlowAPI Limiter.
    """
    return limiter


__all__ = [
    "get_limiter",
    "limiter",
]
