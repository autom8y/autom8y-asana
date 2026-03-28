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

from autom8y_http import (
    Autom8yHttpClient,
    HttpClientConfig,
    RequestError,
    TimeoutException,
)
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


# --- Workflow Config Readiness State (REMEDY-002) ---
# Module-level flag for workflow config registration outcome at ECS startup.
# Set by lifespan.py after the try/except import block.
# None = startup not yet complete, True = registered OK, False = degraded.
_workflow_configs_registered: bool | None = None


def set_workflow_configs_registered(registered: bool) -> None:
    """Record whether workflow configs were successfully registered at startup.

    Per REMEDY-002: The lifespan try/except silently swallows import failures.
    This flag surfaces the registration outcome in the readiness check so that
    monitoring can detect ECS startup degradation.

    Args:
        registered: True if all configs registered; False if import failed.
    """
    global _workflow_configs_registered
    _workflow_configs_registered = registered


def is_workflow_configs_registered() -> bool | None:
    """Return the workflow config registration outcome.

    Returns:
        True if registered OK, False if degraded, None if startup not complete.
    """
    return _workflow_configs_registered


@router.get(
    "/health",
    summary="Check application liveness",
    response_description="Application liveness status",
)
async def health_check() -> JSONResponse:
    """Liveness probe — pure liveness, no I/O, always 200.

    Returns 200 immediately if the application process is running and can
    accept connections. This endpoint never checks dependencies and never
    returns a non-200 status.

    Use this endpoint for ALB/ECS liveness checks. Use ``/ready`` to gate
    traffic on cache warmth and ``/health/deps`` to probe upstream services.

    Does NOT require authentication.

    Returns:
        - 200: ``{"status": "healthy", "version": "0.1.0"}``
    """
    from autom8_asana.api.health_models import liveness_response

    resp = liveness_response(SERVICE_NAME, API_VERSION)
    return JSONResponse(
        content=resp.model_dump(mode="json"),
        status_code=resp.http_status_code(),
    )


@router.get(
    "/ready",
    summary="Check service readiness",
    response_description="Service readiness status with cache state",
)
async def readiness_check() -> JSONResponse:
    """Readiness probe — returns 200 when cache is warm, 503 while loading.

    Use this endpoint to gate traffic: route requests here only after
    receiving 200. The ALB should use ``/health`` for liveness; this
    endpoint is for readiness-aware load balancers and deployment pipelines.

    Per sprint-materialization-002 FR-004:
    - Returns 503 (unavailable) during cache preload.
    - Returns 200 (ok) after cache is ready.

    Does NOT require authentication.

    Returns:
        - 200: Cache ready — service can handle all requests.
        - 503: Cache warming — service is starting up.
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

    # Per REMEDY-002: Surface workflow config registration outcome so that
    # ECS startup degradation (silent import failure) is observable.
    if _workflow_configs_registered is True:
        workflow_check = CheckResult(status=HealthStatus.OK)
    elif _workflow_configs_registered is False:
        workflow_check = CheckResult(
            status=HealthStatus.UNAVAILABLE,
            detail={"message": "Workflow config import failed at startup"},
        )
    else:
        # None = startup not yet complete (ECS is still initializing)
        workflow_check = CheckResult(
            status=HealthStatus.UNAVAILABLE,
            detail={"message": "Workflow config registration pending"},
        )

    resp = readiness_response(
        SERVICE_NAME,
        API_VERSION,
        checks={"cache": cache_check, "workflow_configs": workflow_check},
    )
    return JSONResponse(
        content=resp.model_dump(mode="json"),
        status_code=resp.http_status_code(),
    )


@router.get(
    "/health/deps",
    summary="Check dependency health",
    response_description="Dependency health status with per-check results",
)
async def deps_check() -> JSONResponse:
    """Dependency probe — checks JWKS reachability and bot PAT configuration.

    Runs two checks and reports each result independently:

    - ``jwks``: HTTP GET to the JWKS endpoint. Reports latency and whether
      the response contains a valid ``keys`` array.
    - ``bot_pat``: Presence check for the ``ASANA_PAT`` environment variable.
      Never logs or returns the token value.

    Per PRD-S2S-001 NFR-OPS-002:
    - Degraded checks reduce the aggregate status but do not block the response.
    - A single UNAVAILABLE check returns 503.

    Does NOT require authentication.

    Returns:
        - 200: All checks healthy or degraded (non-critical).
        - 503: At least one critical dependency unavailable.
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
    _jwks_config = HttpClientConfig(
        timeout=5.0, enable_retry=False, enable_circuit_breaker=False
    )
    try:
        async with Autom8yHttpClient(_jwks_config) as client:
            async with client.raw() as raw_client:
                response = await raw_client.get(jwks_url)
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
    except TimeoutException:
        latency = (time.monotonic() - t0) * 1000
        logger.warning("JWKS health check timed out", extra={"jwks_url": jwks_url})
        checks["jwks"] = CheckResult(
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 1),
            detail={"error": "timeout"},
        )
    except RequestError as e:
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
