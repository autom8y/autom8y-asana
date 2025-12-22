"""autom8_asana API layer - FastAPI service exposing SDK via REST.

This module provides a FastAPI application factory for the autom8_asana
satellite service. The API layer wraps the SDK without modifying it,
exposing core operations via REST endpoints.

Example:
    from autom8_asana.api import create_app

    app = create_app()

Per TDD-ASANA-SATELLITE:
- SDK remains installable without [api] extra (backward compatibility)
- API is purely additive, wrapping SDK functionality

Per ADR-ASANA-002:
- PAT pass-through authentication
- Per-request SDK client instantiation
"""

from autom8_asana.api.main import create_app
from autom8_asana.api.models import (
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    ResponseMeta,
    SuccessResponse,
)

__version__ = "0.1.0"

__all__ = [
    # App factory
    "create_app",
    # Response models
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "ResponseMeta",
    "SuccessResponse",
    # Version
    "__version__",
]
