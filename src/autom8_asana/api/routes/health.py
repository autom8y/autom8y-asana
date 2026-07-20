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

import enum
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

# --- Cache Readiness State (FR-004; WS-A Finding-1 fail-closed) ---
# Three-way preload outcome model. Prior to fail-closed hardening this was a
# single bool that the preload set True unconditionally in a `finally` block, so
# a FAILED or ABORTED preload reported the pod ready and shifted production
# traffic onto a silently-cold task (the liveness-masquerade). The state machine
# below distinguishes the three honest outcomes so /ready can gate the ALB
# target group truthfully:
#
#   WARMING  -> preload in progress             -> /ready 503 (CACHE_BUILD_IN_PROGRESS)
#   READY    -> preload completed                -> /ready 200
#   DEGRADED -> deliberate degrade, serviceable  -> /ready 200 + degraded signal
#   FAILED   -> preload raised / aborted         -> /ready 503 (PRELOAD_FAILED)
#
# /health (liveness) is intentionally untouched: a FAILED preload keeps the pod
# alive so the previous task keeps serving under the TG gate and operators see
# the true state.


class PreloadState(enum.StrEnum):
    """Outcome of the startup cache preload.

    Serviceable states (READY, DEGRADED) gate /ready to 200; non-serviceable
    states (WARMING, FAILED) gate /ready to 503.
    """

    WARMING = "warming"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"


_SERVICEABLE_STATES = frozenset({PreloadState.READY, PreloadState.DEGRADED})

_preload_state: PreloadState = PreloadState.WARMING
_preload_detail: str | None = None


def _set_preload_state(state: PreloadState, detail: str | None = None) -> None:
    """Record the preload outcome and log the transition."""
    global _preload_state, _preload_detail
    _preload_state = state
    _preload_detail = detail
    logger.info(
        "cache_ready_state_changed",
        extra={
            "state": state.value,
            "ready": state in _SERVICEABLE_STATES,
            "detail": detail,
        },
    )


def set_cache_ready(ready: bool) -> None:
    """Set cache readiness state (backward-compatible bool API).

    Per FR-004: called by startup preload to signal cache is ready. ``True`` maps
    to the READY state; ``False`` resets to WARMING. Use ``set_cache_degraded`` /
    ``set_cache_failed`` to record the richer three-way outcome.

    Args:
        ready: True when cache preload is complete; False to reset to warming.
    """
    _set_preload_state(PreloadState.READY if ready else PreloadState.WARMING)


def set_cache_degraded(reason: str) -> None:
    """Mark the cache serviceable-but-degraded (deliberate partial degrade).

    The pod serves traffic (/ready 200) but the readiness payload surfaces a
    degraded signal with the reason, so operators see the true state.

    Args:
        reason: Short machine-readable cause (e.g. ``"bot_pat_unavailable"``).
    """
    _set_preload_state(PreloadState.DEGRADED, reason)


def set_cache_failed(reason: str) -> None:
    """Mark the cache preload FAILED — /ready fails closed (503).

    Per WS-A Finding-1: a failed or aborted preload must NOT report ready. The
    pod stays alive (/health untouched) so the previous task keeps serving under
    the target-group gate.

    Args:
        reason: Short machine-readable cause (e.g. ``"preload_exception_ValueError"``).
    """
    _set_preload_state(PreloadState.FAILED, reason)


def is_cache_ready() -> bool:
    """Check if the cache is serviceable (READY or DEGRADED).

    Returns:
        True if the preload completed or is in a deliberate serviceable-degraded
        state; False while warming or after a failure/abort.
    """
    return _preload_state in _SERVICEABLE_STATES


def get_preload_state() -> PreloadState:
    """Return the current three-way preload state."""
    return _preload_state


def get_preload_detail() -> str | None:
    """Return the machine-readable detail for the current preload state, if any."""
    return _preload_detail


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
    response_description="Service readiness status with dependency connectivity",
)
async def readiness_check() -> JSONResponse:
    """Readiness probe — deep connectivity checks for critical dependencies.

    Checks run concurrently with individual 2s timeouts to fit within
    the 5s ALB health check window.

    Checks:
    - ``cache``: DataFrame cache warm-up state (FR-004).
    - ``workflow_configs``: Workflow config registration (REMEDY-002).
    - ``jwks``: JWKS endpoint reachability for JWT validation (promoted
      from /health/deps per SP-L3-1 D4).
    - ``bot_pat``: Asana PAT configuration presence check (promoted
      from /health/deps per SP-L3-1 D4).

    Does NOT require authentication.

    Returns:
        - 200: All critical checks pass — service can handle requests.
        - 503: At least one critical dependency unavailable.
    """
    import asyncio

    from autom8_asana.api.health_models import (
        CheckResult,
        HealthStatus,
        readiness_response,
    )

    checks: dict[str, CheckResult] = {}

    # --- Cache warmth (FR-004; WS-A Finding-1 fail-closed) ---
    cache_state = _preload_state
    if cache_state is PreloadState.READY:
        checks["cache"] = CheckResult(status=HealthStatus.OK)
    elif cache_state is PreloadState.DEGRADED:
        # Deliberate degrade: serviceable, but surface the signal (200 + detail).
        checks["cache"] = CheckResult(
            status=HealthStatus.DEGRADED,
            detail={
                "message": "Cache serving in degraded mode",
                "cause": "PRELOAD_DEGRADED",
                "reason": _preload_detail,
            },
        )
    elif cache_state is PreloadState.FAILED:
        # Fail closed: preload raised or was aborted — NOT serviceable (503).
        # This is the liveness-masquerade fix: a failed preload no longer
        # masquerades as ready and shifts traffic onto a silently-cold task.
        logger.warning(
            "readiness_check_preload_failed",
            extra={"cause": "PRELOAD_FAILED", "reason": _preload_detail},
        )
        checks["cache"] = CheckResult(
            status=HealthStatus.UNAVAILABLE,
            detail={
                "message": "Cache preload failed",
                "cause": "PRELOAD_FAILED",
                "reason": _preload_detail,
            },
        )
    else:  # PreloadState.WARMING
        logger.debug(
            "readiness_check_warming",
            extra={"cache_ready": False},
        )
        checks["cache"] = CheckResult(
            status=HealthStatus.UNAVAILABLE,
            detail={
                "message": "Cache preload in progress",
                "cause": "CACHE_BUILD_IN_PROGRESS",
            },
        )

    # --- Workflow config registration (REMEDY-002) ---
    if _workflow_configs_registered is True:
        checks["workflow_configs"] = CheckResult(status=HealthStatus.OK)
    elif _workflow_configs_registered is False:
        checks["workflow_configs"] = CheckResult(
            status=HealthStatus.UNAVAILABLE,
            detail={"message": "Workflow config import failed at startup"},
        )
    else:
        checks["workflow_configs"] = CheckResult(
            status=HealthStatus.UNAVAILABLE,
            detail={"message": "Workflow config registration pending"},
        )

    # --- Deep connectivity checks (SP-L3-1 D4) ---
    # Run JWKS and PAT checks concurrently with individual 2s timeouts.
    async def _probe_jwks() -> CheckResult:
        """JWKS reachability probe (promoted from /health/deps)."""
        jwks_url = os.environ.get(
            "AUTH_JWKS_URL",
            "https://auth.api.autom8y.io/.well-known/jwks.json",
        )
        t0 = time.monotonic()
        _jwks_config = HttpClientConfig(
            timeout=2.0, enable_retry=False, enable_circuit_breaker=False
        )
        try:
            async with Autom8yHttpClient(_jwks_config) as client:
                async with client.raw() as raw_client:
                    response = await raw_client.get(jwks_url)
                latency = (time.monotonic() - t0) * 1000
                if response.status_code == 200:
                    data = response.json()
                    if "keys" in data and isinstance(data["keys"], list):
                        return CheckResult(
                            status=HealthStatus.OK,
                            latency_ms=round(latency, 1),
                        )
                    return CheckResult(
                        status=HealthStatus.DEGRADED,
                        latency_ms=round(latency, 1),
                        detail={"error": "invalid_response"},
                    )
                return CheckResult(
                    status=HealthStatus.DEGRADED,
                    latency_ms=round(latency, 1),
                    detail={"error": f"http_{response.status_code}"},
                )
        except TimeoutException:
            latency = (time.monotonic() - t0) * 1000
            return CheckResult(
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 1),
                detail={"error": "timeout"},
            )
        except RequestError:
            latency = (time.monotonic() - t0) * 1000
            return CheckResult(
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 1),
                detail={"error": "connection_error"},
            )
        except Exception:  # noqa: BLE001
            latency = (time.monotonic() - t0) * 1000
            return CheckResult(
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 1),
                detail={"error": "unexpected"},
            )

    async def _probe_bot_pat() -> CheckResult:
        """Bot PAT configuration presence check (promoted from /health/deps)."""
        bot_pat = os.environ.get("ASANA_PAT", "")
        if bot_pat and len(bot_pat) >= 10:
            return CheckResult(
                status=HealthStatus.OK,
                detail={"configured": True},
            )
        return CheckResult(
            status=HealthStatus.DEGRADED,
            detail={"configured": False},
        )

    # Run deep probes concurrently with 2s individual timeouts
    async def _run_with_timeout(coro: object, timeout: float = 2.0) -> CheckResult:
        try:
            return await asyncio.wait_for(coro, timeout=timeout)  # type: ignore[arg-type]
        except TimeoutError:
            return CheckResult(
                status=HealthStatus.DEGRADED,
                detail={"error": "timeout"},
            )

    jwks_result, pat_result = await asyncio.gather(
        _run_with_timeout(_probe_jwks()),
        _run_with_timeout(_probe_bot_pat()),
    )
    checks["jwks"] = jwks_result
    checks["bot_pat"] = pat_result

    resp = readiness_response(
        SERVICE_NAME,
        API_VERSION,
        checks=checks,
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
    _jwks_config = HttpClientConfig(timeout=5.0, enable_retry=False, enable_circuit_breaker=False)
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


__all__ = [
    "PreloadState",
    "get_preload_detail",
    "get_preload_state",
    "is_cache_ready",
    "router",
    "set_cache_degraded",
    "set_cache_failed",
    "set_cache_ready",
]
