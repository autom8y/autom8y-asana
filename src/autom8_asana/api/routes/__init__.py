"""API route aggregation.

This module aggregates all API routers for inclusion in the FastAPI app.

Per TDD-ASANA-SATELLITE:
- Routes organized by resource type
- Health check at /health (no prefix, unauthenticated)
- Resource routes at /api/v1/{resource} (authenticated)

Current routes:
- Health router (/health, /ready, /health/deps) - unauthenticated
- Users router (/api/v1/users) - authenticated
- Workspaces router (/api/v1/workspaces) - authenticated
- DataFrames router (/api/v1/dataframes) - authenticated
- Tasks router (/api/v1/tasks) - authenticated
- Projects router (/api/v1/projects) - authenticated
- Sections router (/api/v1/sections) - authenticated
- Internal router (/api/v1/internal) - S2S only (service token required)
- Resolver router (/v1/resolve) - S2S only (entity resolution)
- Query router (/v1/query) - S2S only (entity query)
- Entity write router (/api/v1/entity) - S2S only (entity write)
- Intake resolve router (/v1/resolve/business, /v1/resolve/contact) - S2S only (intake resolution)
- Intake custom fields router (/v1/tasks/{gid}/custom-fields) - S2S only (custom field writes)
- Intake create router (/v1/intake/business, /v1/intake/route) - S2S only (business creation + routing)
- Matching router (/v1/matching/query) - S2S only (business matching, hidden from schema)
"""

from .admin import router as admin_router
from .dataframes import router as dataframes_router
from .entity_write import router as entity_write_router
from .fleet_query import (
    fleet_query_router_api_v1,
    fleet_query_router_v1,
)
from .health import router as health_router
from .intake_create import router as intake_create_router
from .intake_custom_fields import router as intake_custom_fields_router
from .intake_resolve import router as intake_resolve_router
from .internal import router as internal_router
from .matching import router as matching_router
from .projects import router as projects_router
from .query import query_introspection_router
from .query import router as query_router
from .resolver import router as resolver_router
from .section_timelines import router as section_timelines_router
from .sections import router as sections_router
from .tasks import router as tasks_router
from .users import router as users_router
from .webhooks import router as webhooks_router
from .workflows import router as workflows_router
from .workspaces import router as workspaces_router

__all__ = [
    "admin_router",
    "dataframes_router",
    "entity_write_router",
    "fleet_query_router_api_v1",
    "fleet_query_router_v1",
    "health_router",
    "intake_create_router",
    "intake_custom_fields_router",
    "intake_resolve_router",
    "matching_router",
    "internal_router",
    "projects_router",
    "query_introspection_router",
    "query_router",
    "resolver_router",
    "section_timelines_router",
    "sections_router",
    "tasks_router",
    "users_router",
    "webhooks_router",
    "workflows_router",
    "workspaces_router",
]
