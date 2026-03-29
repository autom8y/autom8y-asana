"""Fleet-standard security primitives for asana API routers.

Provides pre-configured SecureRouter factories for the asana service's
dual-mode authentication:
- PAT (Personal Access Token) via BearerAuth for standard resource endpoints
- S2S (Service-to-service) via ServiceJWT for internal service endpoints

Health routers should continue using plain APIRouter.

The auto_error=False setting ensures SecureRouters only inject OpenAPI
metadata without performing runtime auth checks -- runtime auth is handled
by the existing auth dependencies (get_current_user, verify_service_jwt).
"""

from __future__ import annotations

from fastapi.security import HTTPBearer

from autom8y_api_schemas import SecureRouter

# PAT Bearer auth for standard resource endpoints (/api/v1/*)
PAT_BEARER_SCHEME = HTTPBearer(
    scheme_name="BearerAuth",
    description="Asana Personal Access Token (PAT)",
    auto_error=False,
)

# S2S JWT auth for internal service endpoints (/v1/*)
SERVICE_JWT_SCHEME = HTTPBearer(
    scheme_name="ServiceJWT",
    description="Service-to-service JWT issued by the autom8y auth service",
    auto_error=False,
)


def pat_router(**kwargs) -> SecureRouter:
    """Create a SecureRouter with PAT BearerAuth scheme.

    Use for standard resource endpoints (tasks, projects, sections, etc.).
    """
    return SecureRouter(security_scheme=PAT_BEARER_SCHEME, **kwargs)


def s2s_router(**kwargs) -> SecureRouter:
    """Create a SecureRouter with ServiceJWT scheme.

    Use for internal S2S endpoints (resolver, query, admin, intake, etc.).
    """
    return SecureRouter(security_scheme=SERVICE_JWT_SCHEME, **kwargs)
