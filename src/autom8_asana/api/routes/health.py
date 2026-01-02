"""Health check endpoints.

This module provides health check endpoints for container orchestration
and deployment monitoring.

Per TDD-ASANA-SATELLITE (FR-API-HEALTH-001, FR-API-HEALTH-002):
- GET /health returns service status
- Health check does NOT require authentication

Per PRD-ASANA-SATELLITE:
- Returns {"status": "healthy", "version": "0.1.0"}
- Used for ALB health checks and ECS task health

Per PRD-S2S-001 (NFR-OPS-002):
- GET /health/s2s returns S2S connectivity status
- Checks JWKS endpoint reachability for JWT validation

Per sprint-materialization-002 FR-004:
- Returns 503 "warming" status during cache preload
- Returns 200 "healthy" status after cache is ready
"""

from __future__ import annotations

import logging
import os
from typing import TypedDict

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import version directly to avoid circular import
# (api/__init__.py imports from main.py which imports routes)
API_VERSION = "0.1.0"

logger = logging.getLogger("autom8_asana.health")

router = APIRouter(tags=["health"])

# --- Cache Readiness State (FR-004) ---
# Module-level flag for cache warm-up state
# Set to True by startup preload after cache is populated
_cache_ready: bool = False


def set_cache_ready(ready: bool) -> None:
    """Set cache readiness state.

    Per FR-004: Called by startup preload to signal cache is ready.
    Health check returns 503 "warming" until this is set to True.

    Args:
        ready: True when cache preload is complete.
    """
    global _cache_ready
    _cache_ready = ready
    logger.info(
        "cache_ready_state_changed",
        extra={"ready": ready},
    )


def is_cache_ready() -> bool:
    """Check if cache is ready.

    Returns:
        True if cache preload is complete.
    """
    return _cache_ready


class HealthResponse(TypedDict):
    """Health check response structure."""

    status: str
    version: str


class S2SHealthResponse(TypedDict, total=False):
    """S2S health check response structure."""

    status: str
    version: str
    s2s_connectivity: bool
    jwks_reachable: bool
    bot_pat_configured: bool
    details: dict[str, str]


@router.get("/health")
async def health_check() -> JSONResponse:
    """Liveness probe - returns healthy if the application is running and warm.

    Per FR-API-HEALTH-001:
    - Returns 200 with {"status": "healthy", "version": "0.1.0"}

    Per FR-API-HEALTH-002:
    - This endpoint does NOT require authentication
    - No Authorization header needed

    Per sprint-materialization-002 FR-004:
    - Returns 503 with {"status": "warming"} during cache preload
    - Returns 200 with {"status": "healthy"} after cache is ready

    This endpoint checks cache readiness state. During startup preload,
    it returns 503 to prevent traffic until caches are populated.

    Returns:
        JSON response with status and current version.
        - 200: Cache is ready, service is healthy
        - 503: Cache is warming, service is not ready for traffic
    """
    if not _cache_ready:
        logger.debug(
            "health_check_warming",
            extra={"cache_ready": False},
        )
        return JSONResponse(
            content={
                "status": "warming",
                "version": API_VERSION,
                "message": "Cache preload in progress",
            },
            status_code=503,
        )

    return JSONResponse(
        content={"status": "healthy", "version": API_VERSION},
        status_code=200,
    )


@router.get("/health/s2s")
async def s2s_health_check() -> JSONResponse:
    """S2S readiness probe - checks JWT/S2S authentication dependencies.

    Per PRD-S2S-001 NFR-OPS-002:
    - Returns S2S connectivity status
    - Checks JWKS endpoint reachability
    - Checks bot PAT configuration

    This endpoint verifies that the service can accept S2S (JWT) requests:
    1. JWKS endpoint is reachable for signature validation
    2. Bot PAT is configured for Asana API calls

    Does NOT require authentication.

    Returns:
        JSON response with S2S connectivity details.
        - 200: All dependencies healthy
        - 503: One or more dependencies unavailable
    """
    details: dict[str, str] = {}
    jwks_reachable = False
    bot_pat_configured = False

    # Check JWKS endpoint reachability
    jwks_url = os.environ.get(
        "AUTH_JWKS_URL",
        "https://auth.api.autom8y.io/.well-known/jwks.json",
    )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(jwks_url)
            if response.status_code == 200:
                # Verify it looks like a JWKS response
                data = response.json()
                if "keys" in data and isinstance(data["keys"], list):
                    jwks_reachable = True
                    details["jwks_status"] = "reachable"
                else:
                    details["jwks_status"] = "invalid_response"
            else:
                details["jwks_status"] = f"http_{response.status_code}"
    except httpx.TimeoutException:
        details["jwks_status"] = "timeout"
        logger.warning("JWKS health check timed out", extra={"jwks_url": jwks_url})
    except httpx.RequestError as e:
        details["jwks_status"] = "connection_error"
        logger.warning(
            "JWKS health check failed",
            extra={"jwks_url": jwks_url, "error": str(e)},
        )
    except Exception as e:
        details["jwks_status"] = "error"
        logger.exception("JWKS health check unexpected error")

    # Check bot PAT configuration (presence only, never log value)
    bot_pat = os.environ.get("ASANA_PAT", "")
    if bot_pat and len(bot_pat) >= 10:
        bot_pat_configured = True
        details["bot_pat_status"] = "configured"
    else:
        details["bot_pat_status"] = "not_configured"

    # Overall S2S connectivity
    s2s_connectivity = jwks_reachable and bot_pat_configured

    # Determine overall status
    if s2s_connectivity:
        status = "healthy"
        http_status = 200
    else:
        status = "degraded"
        http_status = 503

    response_content: S2SHealthResponse = {
        "status": status,
        "version": API_VERSION,
        "s2s_connectivity": s2s_connectivity,
        "jwks_reachable": jwks_reachable,
        "bot_pat_configured": bot_pat_configured,
        "details": details,
    }

    return JSONResponse(content=response_content, status_code=http_status)


__all__ = ["router", "set_cache_ready", "is_cache_ready"]
