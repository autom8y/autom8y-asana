"""API route aggregation.

This module aggregates all API routers for inclusion in the FastAPI app.

Per TDD-ASANA-SATELLITE:
- Routes organized by resource type
- Health check at /health (no version prefix, unauthenticated)
- Resource routes at /api/v1/{resource} (authenticated)

Current routes:
- Health router (/health) - unauthenticated
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
"""

from .admin import router as admin_router
from .entity_write import router as entity_write_router
from .dataframes import router as dataframes_router
from .health import router as health_router
from .internal import router as internal_router
from .projects import router as projects_router
from .query import router as query_router
from .query_v2 import router as query_v2_router
from .resolver import router as resolver_router
from .sections import router as sections_router
from .tasks import router as tasks_router
from .users import router as users_router
from .webhooks import router as webhooks_router
from .workspaces import router as workspaces_router

__all__ = [
    "admin_router",
    "dataframes_router",
    "entity_write_router",
    "health_router",
    "internal_router",
    "projects_router",
    "query_router",
    "query_v2_router",
    "resolver_router",
    "sections_router",
    "tasks_router",
    "users_router",
    "webhooks_router",
    "workspaces_router",
]
