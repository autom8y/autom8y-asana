"""Health contract models for the Asana satellite service.

Fleet-standard health models imported from autom8y-api-schemas.
This module re-exports all types at their original import path for
backward compatibility. New code should import from
autom8y_api_schemas directly.

Migration: Lexicon Ascension Sprint-4 (ASANA-QW-05)
"""

from autom8y_api_schemas import (
    CheckResult,
    HealthResponse,
    HealthStatus,
    deps_response,
    liveness_response,
    readiness_response,
)

__all__ = [
    "CheckResult",
    "HealthResponse",
    "HealthStatus",
    "deps_response",
    "liveness_response",
    "readiness_response",
]
