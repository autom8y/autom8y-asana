"""FastAPI application factory with lifespan management.

This module provides the main FastAPI application factory with:
- Lifespan context manager for startup/shutdown
- CORS middleware (configurable)
- Rate limiting middleware (SlowAPI)
- Request ID middleware for correlation
- Request logging middleware
- Route registration
- Exception handler registration

Per TDD-ASANA-SATELLITE:
- FR-SVC-001: FastAPI application factory with lifespan
- FR-SVC-002: Request ID middleware
- FR-SVC-003: Request logging middleware
- FR-SVC-004: CORS middleware with configurable origins
- FR-SVC-005: Service-level rate limiting via SlowAPI

Per ADR-ASANA-007:
- SDK client lifecycle is per-request (via dependencies)
- No persistent client state in app.state

Design Principles:
- Thin API layer that delegates to SDK
- Request tracing via X-Request-ID header
- Centralized error handling
- Structured JSON logging
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import get_settings
from .errors import register_exception_handlers
from .middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    configure_structlog,
)
from .rate_limit import limiter
from .routes import (
    dataframes_router,
    health_router,
    internal_router,
    projects_router,
    sections_router,
    tasks_router,
    users_router,
    workspaces_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle.

    Per FR-SVC-001: Application factory with lifespan context manager.

    Startup:
    - Configure structured logging
    - Log startup event

    Shutdown:
    - Log shutdown event
    - Clean up resources (if any)

    Per ADR-ASANA-007: SDK client lifecycle is per-request,
    so no persistent client initialization needed here.

    Args:
        app: FastAPI application instance.

    Yields:
        None (no persistent state stored on app.state for SDK).
    """
    # Startup
    configure_structlog()
    settings = get_settings()

    logger.info(
        "api_starting",
        extra={
            "service": "autom8_asana",
            "log_level": settings.log_level,
            "debug": settings.debug,
            "rate_limit_rpm": settings.rate_limit_rpm,
        },
    )

    yield

    # Shutdown
    logger.info(
        "api_stopping",
        extra={"service": "autom8_asana"},
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application with:
        - Lifespan context manager
        - CORS middleware (if configured)
        - Rate limiting middleware
        - Request ID middleware
        - Request logging middleware
        - Health route
        - Exception handlers

    Per TDD-ASANA-SATELLITE:
    - Middleware stack order matters for proper execution
    - Exception handlers map SDK errors to HTTP responses
    """
    settings = get_settings()

    app = FastAPI(
        title="autom8_asana API",
        description="REST API for Asana integration via autom8_asana SDK",
        version="0.1.0",
        lifespan=lifespan,
        # Disable automatic docs in production
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # --- Middleware Stack ---
    # Starlette executes middleware in reverse order of addition.
    # Outer to inner execution order:
    # 1. CORSMiddleware - handle preflight (outermost)
    # 2. SlowAPIMiddleware - rate limiting
    # 3. RequestLoggingMiddleware - log all requests
    # 4. RequestIDMiddleware - set request_id (innermost)

    # CORS (if configured) - MUST be outermost to handle preflight OPTIONS
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
        logger.info(
            "cors_enabled",
            extra={"allowed_origins": settings.cors_origins_list},
        )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Request logging (before RequestID so it has access to request_id)
    app.add_middleware(RequestLoggingMiddleware)

    # Request ID (innermost - runs first, sets request_id for others)
    app.add_middleware(RequestIDMiddleware)

    # --- Routes ---
    app.include_router(health_router)
    app.include_router(users_router)
    app.include_router(workspaces_router)
    app.include_router(dataframes_router)
    app.include_router(tasks_router)
    app.include_router(projects_router)
    app.include_router(sections_router)
    app.include_router(internal_router)

    # --- Exception Handlers ---
    register_exception_handlers(app)

    return app


# Allow running directly with uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "autom8_asana.api.main:create_app",
        host="0.0.0.0",
        port=8000,
        factory=True,
        reload=True,
    )
