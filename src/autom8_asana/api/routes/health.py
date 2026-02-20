"""Health check endpoints.

Health endpoints follow the platform three-tier contract: /health (liveness),
/ready (readiness), /health/deps (dependency probe).

Tiers:
    GET /health      - Pure liveness probe. No I/O, always 200.
    GET /ready       - Readiness probe. Checks cache warmth, returns 200 or 503.
    GET /health/deps - Dependency probe. Checks JWKS reachability and PAT config.

Per PRD-ASANA-SATELLITE:
- Health endpoints do NOT require authentication.
- Used for ALB health checks and ECS task health.

Per sprint-materialization-002 FR-004:
- Returns 503 during cache preload (via /ready).
- Returns 200 after cache is ready (via /ready).

Per PRD-S2S-001 (NFR-OPS-002):
- Dependency probe checks JWKS endpoint reachability for JWT validation.
"""

from __future__ import annotations

import os
import time

import httpx
from autom8y_log import get_logger
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import version directly to avoid circular import
# (api/__init__.py imports from main.py which imports routes)
API_VERSION = "0.1.0"
SERVICE_NAME = "asana"

logger = get_logger("autom8_asana.health")

router = APIRouter(tags=["health"])

# --- Cache Readiness State (FR-004) ---
# Module-level flag for cache warm-up state
# Set to True by startup preload after cache is populated
_cache_ready: bool = False


def set_cache_ready(ready: bool) -> None:
    """Set cache readiness state.

    Per FR-004: Called by startup preload to signal cache is ready.
    Readiness check returns 503 until this is set to True.

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


@router.get("/health")
async def health_check() -> JSONResponse:
    """Liveness probe -- pure liveness, no I/O, always 200.

    This endpoint is used by ALB/ECS health checks to determine if the
    application process is running and can accept connections. It never
    performs dependency checks and always returns 200.

    Returns:
        JSON response with standard health contract envelope.
        - 200: Application is running (always)
    """
    from autom8_asana.api.health_models import liveness_response

    resp = liveness_response(SERVICE_NAME, API_VERSION)
    return JSONResponse(
        content=resp.model_dump(mode="json"),
        status_code=resp.http_status_code(),
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness probe -- checks cache warmth.

    Per sprint-materialization-002 FR-004:
    - Returns 503 (unavailable) during cache preload.
    - Returns 200 (ok) after cache is ready.

    Use this endpoint for traffic gating decisions that require warm cache.
    The ALB should use /health for liveness, not this endpoint.

    Returns:
        JSON response with standard health contract envelope.
        - 200: Cache is ready, service can handle traffic optimally.
        - 503: Cache is warming, service cannot serve traffic reliably.
    """
    from autom8_asana.api.health_models import (
        CheckResult,
        HealthStatus,
        readiness_response,
    )

    if _cache_ready:
        cache_check = CheckResult(status=HealthStatus.OK)
    else:
        logger.debug(
            "readiness_check_warming",
            extra={"cache_ready": False},
        )
        cache_check = CheckResult(
            status=HealthStatus.UNAVAILABLE,
            detail={"message": "Cache preload in progress"},
        )

    resp = readiness_response(
        SERVICE_NAME,
        API_VERSION,
        checks={"cache": cache_check},
    )
    return JSONResponse(
        content=resp.model_dump(mode="json"),
        status_code=resp.http_status_code(),
    )


@router.get("/health/deps")
async def deps_check() -> JSONResponse:
    """Dependency probe -- checks JWKS and PAT configuration.

    Per PRD-S2S-001 NFR-OPS-002:
    - Returns S2S connectivity status.
    - Checks JWKS endpoint reachability.
    - Checks bot PAT configuration.

    Does NOT require authentication.

    Returns:
        JSON response with standard health contract envelope.
        - 200: All dependencies healthy (or degraded but non-critical).
        - 503: Critical dependency unavailable.
    """
    from autom8_asana.api.health_models import (
        CheckResult,
        HealthStatus,
        deps_response,
    )

    checks: dict[str, CheckResult] = {}

    # --- JWKS reachability ---
    jwks_url = os.environ.get(
        "AUTH_JWKS_URL",
        "https://auth.api.autom8y.io/.well-known/jwks.json",
    )

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(jwks_url)
            latency = (time.monotonic() - t0) * 1000
            if response.status_code == 200:
                data = response.json()
                if "keys" in data and isinstance(data["keys"], list):
                    checks["jwks"] = CheckResult(
                        status=HealthStatus.OK,
                        latency_ms=round(latency, 1),
                    )
                else:
                    checks["jwks"] = CheckResult(
                        status=HealthStatus.DEGRADED,
                        latency_ms=round(latency, 1),
                        detail={"error": "invalid_response"},
                    )
            else:
                checks["jwks"] = CheckResult(
                    status=HealthStatus.DEGRADED,
                    latency_ms=round(latency, 1),
                    detail={"error": f"http_{response.status_code}"},
                )
    except httpx.TimeoutException:
        latency = (time.monotonic() - t0) * 1000
        logger.warning("JWKS health check timed out", extra={"jwks_url": jwks_url})
        checks["jwks"] = CheckResult(
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1),
            detail={"error": "timeout"},
        )
    except httpx.RequestError as e:
        latency = (time.monotonic() - t0) * 1000
        logger.warning(
            "JWKS health check failed",
            extra={"jwks_url": jwks_url, "error": str(e)},
        )
        checks["jwks"] = CheckResult(
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1),
            detail={"error": "connection_error"},
        )
    except Exception:  # BROAD-CATCH: degrade
        latency = (time.monotonic() - t0) * 1000
        logger.exception("JWKS health check unexpected error")
        checks["jwks"] = CheckResult(
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1),
            detail={"error": "unexpected"},
        )

    # --- Bot PAT configuration (presence only, never log value) ---
    bot_pat = os.environ.get("ASANA_PAT", "")
    if bot_pat and len(bot_pat) >= 10:
        checks["bot_pat"] = CheckResult(
            status=HealthStatus.OK,
            detail={"configured": True},
        )
    else:
        checks["bot_pat"] = CheckResult(
            status=HealthStatus.DEGRADED,
            detail={"configured": False},
        )

    resp = deps_response(SERVICE_NAME, API_VERSION, checks=checks)
    return JSONResponse(
        content=resp.model_dump(mode="json"),
        status_code=resp.http_status_code(),
    )


__all__ = ["router", "set_cache_ready", "is_cache_ready"]
