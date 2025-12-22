"""Health check endpoint.

This module provides the health check endpoint for container orchestration
and deployment monitoring.

Per TDD-ASANA-SATELLITE (FR-API-HEALTH-001, FR-API-HEALTH-002):
- GET /health returns service status
- Health check does NOT require authentication

Per PRD-ASANA-SATELLITE:
- Returns {"status": "healthy", "version": "0.1.0"}
- Used for ALB health checks and ECS task health
"""

from typing import TypedDict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import version directly to avoid circular import
# (api/__init__.py imports from main.py which imports routes)
API_VERSION = "0.1.0"

router = APIRouter(tags=["health"])


class HealthResponse(TypedDict):
    """Health check response structure."""

    status: str
    version: str


@router.get("/health")
async def health_check() -> JSONResponse:
    """Liveness probe - returns healthy if the application is running.

    Per FR-API-HEALTH-001:
    - Returns 200 with {"status": "healthy", "version": "0.1.0"}

    Per FR-API-HEALTH-002:
    - This endpoint does NOT require authentication
    - No Authorization header needed

    This endpoint should always return 200 as long as the application
    process is running. It does not check external dependencies.

    Returns:
        JSON response with status "healthy" and current version.
    """
    return JSONResponse(
        content={"status": "healthy", "version": API_VERSION},
        status_code=200,
    )


__all__ = ["router"]
