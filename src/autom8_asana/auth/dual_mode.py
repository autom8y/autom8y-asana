"""Dual-mode authentication: JWT detection and routing.

This module provides token type detection for dual-mode authentication,
enabling autom8_asana to accept both:
- JWT tokens from internal services (S2S mode)
- PAT tokens from external users (pass-through mode)

Per ADR-S2S-001: Token detection uses dot counting (JWT has exactly 2 dots,
Asana PAT has 0 dots). This is O(n), simple, and reliable.

Per TDD-S2S-001 Section 5.1:
- AuthMode enum distinguishes JWT from PAT
- detect_token_type() uses dot counting
- get_auth_mode() extracts and validates from header
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from fastapi import Header, HTTPException


class AuthMode(str, Enum):
    """Authentication mode for the current request.

    Attributes:
        JWT: Service token from auth service (S2S)
        PAT: Personal access token from Asana (user pass-through)
    """

    JWT = "jwt"
    PAT = "pat"


def detect_token_type(token: str) -> AuthMode:
    """Detect token type by counting dots.

    JWT tokens have exactly 2 dots (header.payload.signature).
    Asana PATs have 0 dots (format: 0/xxxxxxxx or 1/xxxxxxxx).

    Args:
        token: Bearer token string (without "Bearer " prefix)

    Returns:
        AuthMode.JWT or AuthMode.PAT

    Rationale:
        See ADR-S2S-001 for alternatives considered (header-based,
        regex, decode-and-inspect, prefix convention).
    """
    dot_count = token.count(".")
    if dot_count == 2:
        return AuthMode.JWT
    return AuthMode.PAT


async def get_auth_mode(
    authorization: Annotated[str | None, Header()] = None,
) -> tuple[AuthMode, str]:
    """Extract auth mode and token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Tuple of (AuthMode, token_string)

    Raises:
        HTTPException: 401 if header is missing or invalid
    """
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_AUTH",
                "message": "Authorization header required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_SCHEME", "message": "Bearer scheme required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    if len(token) < 10:
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_TOKEN", "message": "Token too short"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_mode = detect_token_type(token)
    return auth_mode, token


__all__ = [
    "AuthMode",
    "detect_token_type",
    "get_auth_mode",
]
