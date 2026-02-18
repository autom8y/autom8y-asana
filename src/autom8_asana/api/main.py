"""FastAPI application factory.

Per TDD-I5: This module is the thin app factory shell after decomposition.
Startup/shutdown logic lives in lifespan.py, initialization in startup.py,
and preload subsystem in preload/.

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

from autom8y_log import get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# CRITICAL: Import from models.business at module level to ensure bootstrap runs
# on every app startup BEFORE any detection can occur. The bootstrap in
# models/business/__init__.py populates ProjectTypeRegistry for Tier 1 detection.
import autom8_asana.models.business  # noqa: F401 - side effect import for bootstrap

from .config import get_settings
from .errors import register_exception_handlers
from .lifespan import lifespan  # noqa: F401
from .middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
)
from .rate_limit import limiter
from .routes import (
    admin_router,
    dataframes_router,
    entity_write_router,
    health_router,
    internal_router,
    projects_router,
    query_router,
    query_v2_router,
    resolver_router,
    sections_router,
    tasks_router,
    users_router,
    webhooks_router,
    workspaces_router,
)

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application with:
        - Lifespan context manager
        - CORS middleware (if configured)
        - Rate limiting middleware
        - Request ID middleware
        - Request logging middleware
        - Platform observability (metrics, tracing, log correlation)
        - Health route
        - Exception handlers

    Per TDD-ASANA-SATELLITE:
    - Middleware stack order matters for proper execution
    - Exception handlers map SDK errors to HTTP responses

    Per PRD-PLATFORM-OBSERVABILITY-STD M3.3:
    - instrument_app() provides platform-standard baseline metrics
    - Graceful degradation if autom8y-telemetry is not installed
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

    # --- Platform Observability ---
    # Per PRD-PLATFORM-OBSERVABILITY-STD M3.3: Adopt instrument_app() for
    # platform-standard metrics (request duration, count, in-flight),
    # /metrics endpoint, tracing, and log correlation.
    # Must be added BEFORE other middleware so MetricsMiddleware wraps them.
    try:
        from autom8y_telemetry import InstrumentationConfig, instrument_app

        instrument_app(
            app,
            InstrumentationConfig(
                service_name="asana",
                enable_tracing=True,
                enable_log_correlation=True,
            ),
        )
        # Register domain-specific Prometheus metrics on the default registry.
        # Per TDD-SDK-ALIGNMENT Path 3: metrics are served alongside SDK metrics
        # via the /metrics endpoint that instrument_app() creates.
        import autom8_asana.api.metrics  # noqa: F401 - register domain metrics

        logger.info(
            "platform_observability_enabled",
            extra={"service_name": "asana"},
        )
    except ImportError:
        logger.warning(
            "platform_observability_unavailable",
            extra={
                "reason": "autom8y-telemetry not installed",
                "impact": "No platform metrics, /metrics endpoint, or tracing",
                "remediation": "Install autom8y-telemetry[fastapi]>=0.2.0",
            },
        )

    # --- Middleware Stack ---
    # Starlette executes middleware in reverse order of addition.
    # Outer to inner execution order:
    # 1. CORSMiddleware - handle preflight (outermost)
    # 2. SlowAPIMiddleware - rate limiting
    # 3. RequestLoggingMiddleware - log all requests
    # 4. RequestIDMiddleware - set request_id (innermost)
    # Note: MetricsMiddleware from instrument_app() is added above and
    # wraps the entire stack for accurate request duration measurement.

    # CORS (if configured) - MUST be outermost to handle preflight OPTIONS
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
        logger.info(
            "cors_enabled",
            extra={"allowed_origins": settings.cors_origins_list},
        )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
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
    app.include_router(resolver_router)
    app.include_router(query_router)
    app.include_router(query_v2_router)
    app.include_router(admin_router)
    app.include_router(webhooks_router)
    app.include_router(entity_write_router)

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
