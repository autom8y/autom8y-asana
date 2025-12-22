"""FastAPI dependency injection for the API layer.

This module provides dependency factories for:
- PAT extraction from Authorization header
- Per-request AsanaClient instantiation
- Request ID access

Per ADR-ASANA-002: PAT Pass-Through Authentication
- Extract PAT from Authorization: Bearer header
- Validate token format (non-empty, minimum length)
- Create per-request SDK client

Per ADR-ASANA-007: SDK Client Lifecycle
- Per-request instantiation for user isolation
- Clean error boundaries
- No connection pooling across requests
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from autom8_asana import AsanaClient


async def get_asana_pat(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate PAT from Authorization header.

    Per ADR-ASANA-002:
    - Requires Bearer scheme
    - Validates non-empty token
    - Token must be at least 10 characters

    Args:
        authorization: Authorization header value.

    Returns:
        Extracted PAT token.

    Raises:
        HTTPException: 401 if header missing, wrong scheme, or invalid format.
    """
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization scheme. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if len(token) < 10:
        raise HTTPException(
            status_code=401,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


async def get_asana_client(
    pat: Annotated[str, Depends(get_asana_pat)],
) -> AsyncGenerator[AsanaClient, None]:
    """Create per-request AsanaClient with provided PAT.

    Per ADR-ASANA-007:
    - Each request gets a fresh client instance
    - Complete user isolation (no shared state)
    - Clean error boundaries
    - Garbage collection handles cleanup

    Args:
        pat: Personal Access Token from Authorization header.

    Yields:
        AsanaClient instance configured with the provided PAT.
    """
    client = AsanaClient(token=pat)
    try:
        yield client
    finally:
        # Explicit cleanup if SDK supports async close
        if hasattr(client, "aclose"):
            await client.aclose()


def get_request_id(request: Request) -> str:
    """Get request ID from request state.

    The request_id is set by RequestIDMiddleware and is available
    on request.state for all downstream handlers.

    Args:
        request: FastAPI request object.

    Returns:
        16-character hex request ID, or "unknown" if not set.
    """
    return getattr(request.state, "request_id", "unknown")


# Type aliases for cleaner route signatures
AsanaPAT = Annotated[str, Depends(get_asana_pat)]
AsanaClientDep = Annotated[AsanaClient, Depends(get_asana_client)]
RequestId = Annotated[str, Depends(get_request_id)]


__all__ = [
    # Dependencies
    "get_asana_client",
    "get_asana_pat",
    "get_request_id",
    # Type aliases
    "AsanaClientDep",
    "AsanaPAT",
    "RequestId",
]
