"""Health contract models for the Asana satellite service.

Implements the platform three-tier health contract with standard response
envelope. All satellites produce identical response shapes and status values.

Tiers:
    /health      -- Liveness. No I/O, always 200.
    /ready       -- Readiness. Checks critical preconditions (cache warmth).
    /health/deps -- Dependency probe. Detailed checks (JWKS, PAT).
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(enum.StrEnum):
    """Canonical health status values.

    ok: All checks pass. HTTP 200.
    degraded: Non-critical check failed, service can still serve traffic. HTTP 200.
    unavailable: Critical check failed, service cannot serve traffic. HTTP 503.
    """

    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class CheckResult(BaseModel):
    """Result of a single dependency check."""

    status: HealthStatus
    latency_ms: float | None = None
    detail: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Standard health response envelope.

    Used by all three tiers: /health, /ready, /health/deps.
    """

    status: HealthStatus
    service: str
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checks: dict[str, CheckResult] | None = None

    def http_status_code(self) -> int:
        """Map status to HTTP status code."""
        if self.status == HealthStatus.UNAVAILABLE:
            return 503
        return 200


# --- Endpoint factory patterns ---


def liveness_response(service: str, version: str) -> HealthResponse:
    """Create a liveness response. Always returns ok."""
    return HealthResponse(
        status=HealthStatus.OK,
        service=service,
        version=version,
    )


def readiness_response(
    service: str,
    version: str,
    checks: dict[str, CheckResult],
) -> HealthResponse:
    """Create a readiness response based on check results.

    Returns unavailable if any check is unavailable.
    Returns degraded if any check is degraded but none unavailable.
    Returns ok if all checks pass.
    """
    statuses = [c.status for c in checks.values()]
    if HealthStatus.UNAVAILABLE in statuses:
        overall = HealthStatus.UNAVAILABLE
    elif HealthStatus.DEGRADED in statuses:
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.OK

    return HealthResponse(
        status=overall,
        service=service,
        version=version,
        checks=checks,
    )


# /health/deps (dependency probe) -- same signature as readiness_response
# with more granular checks.
# Alias: deps_response is identical to readiness_response. Both endpoints
# share the same response factory. See api/routes/health.py for mount points.
deps_response = readiness_response
