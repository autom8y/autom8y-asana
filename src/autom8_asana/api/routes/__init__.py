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
"""

from .dataframes import router as dataframes_router
from .health import router as health_router
from .projects import router as projects_router
from .sections import router as sections_router
from .tasks import router as tasks_router
from .users import router as users_router
from .workspaces import router as workspaces_router

__all__ = [
    "dataframes_router",
    "health_router",
    "projects_router",
    "sections_router",
    "tasks_router",
    "users_router",
    "workspaces_router",
]
