"""FastAPI application factory with lifespan management.

This module provides the main FastAPI application factory with:
- Lifespan context manager for startup/shutdown
- CORS middleware (configurable)
- Rate limiting middleware (SlowAPI)
- Request ID middleware for correlation
- Request logging middleware
- Route registration
- Exception handler registration
- Entity resolver startup discovery

Per TDD-ASANA-SATELLITE:
- FR-SVC-001: FastAPI application factory with lifespan
- FR-SVC-002: Request ID middleware
- FR-SVC-003: Request logging middleware
- FR-SVC-004: CORS middleware with configurable origins
- FR-SVC-005: Service-level rate limiting via SlowAPI

Per TDD-entity-resolver:
- Entity resolver discovers project GIDs at startup
- Fail-fast if discovery fails
- Store EntityProjectRegistry in app.state

Per ADR-ASANA-007:
- SDK client lifecycle is per-request (via dependencies)
- No persistent client state in app.state

Design Principles:
- Thin API layer that delegates to SDK
- Request tracing via X-Request-ID header
- Centralized error handling
- Structured JSON logging
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
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
from .middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    configure_structlog,
)
from .rate_limit import limiter
from .routes import (
    admin_router,
    dataframes_router,
    health_router,
    internal_router,
    projects_router,
    query_router,
    query_v2_router,
    resolver_router,
    sections_router,
    tasks_router,
    users_router,
    workspaces_router,
)


# Re-exports from startup.py for backward compatibility (removed in C4)
from .startup import (  # noqa: F401
    _discover_entity_projects,
    _initialize_dataframe_cache,
    _initialize_mutation_invalidator,
    _register_schema_providers,
)


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle.

    Per FR-SVC-001: Application factory with lifespan context manager.

    Startup:
    - Configure structured logging
    - Log startup event
    - Entity resolver discovery (FR-004, FR-005 per TDD-entity-resolver)
    - DataFrame cache preload from S3 (FR-003 per sprint-materialization-002)

    Shutdown:
    - Log shutdown event
    - Clean up resources (if any)

    Per ADR-ASANA-007: SDK client lifecycle is per-request,
    so no persistent client initialization needed here.

    Per ADR-0060: Entity resolver discovers project GIDs at startup.

    Per sprint-materialization-002 FR-003, FR-004:
    - Pre-warm DataFrame cache before accepting traffic
    - Health check returns 503 until cache is ready

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

    # Entity resolver startup discovery (FR-004, FR-005)
    try:
        await _discover_entity_projects(app)
    except Exception as e:
        logger.error(
            "entity_resolver_discovery_failed",
            extra={
                "error": str(e),
                "remediation": (
                    "Ensure workspace contains projects with names: "
                    "Business Units. Check ASANA_BOT_PAT is configured."
                ),
            },
        )
        # Per ADR-0060: Fail-fast on discovery failure
        raise RuntimeError(f"Entity resolver discovery failed: {e}") from e

    # Initialize DataFrameCache for Offer/Contact resolution strategies
    # Per TDD-DATAFRAME-CACHE-001: Provides tiered caching (Memory + S3)
    _initialize_dataframe_cache()

    # Register schema providers with SDK for cache compatibility checks
    # Per SDK Phase 1: Bridges satellite SchemaRegistry to SDK registry
    _register_schema_providers()

    # Initialize MutationInvalidator for REST cache invalidation
    # Per TDD-CACHE-INVALIDATION-001: Wire cache invalidation into REST routes
    _initialize_mutation_invalidator(app)

    # DataFrame cache preload (FR-003 per sprint-materialization-002)
    # Runs after entity discovery so we know which projects exist
    # Per progressive cache warming architecture: use progressive preload with
    # parallel project processing, resume capability, and heartbeat monitoring
    #
    # IMPORTANT: Run cache warming as background task to not block startup.
    # This allows /health to return 200 immediately while cache warms.
    # The /health/ready endpoint returns 503 until cache is warm.
    # Per ECS health check fix: blocking startup causes health check failures
    # when rate limiting or other errors slow down cache warming.
    background_task = asyncio.create_task(
        _preload_dataframe_cache_progressive(app),
        name="cache_warming",
    )

    # Store task reference to cancel on shutdown
    app.state.cache_warming_task = background_task

    logger.info(
        "cache_warming_started_background",
        extra={"task_name": "cache_warming"},
    )

    yield

    # Cancel background cache warming if still running
    if hasattr(app.state, "cache_warming_task"):
        task = app.state.cache_warming_task
        if not task.done():
            logger.info("cache_warming_cancelling")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("cache_warming_cancelled")
            except Exception as e:
                logger.warning(
                    "cache_warming_cancel_error",
                    extra={"error": str(e)},
                )

    # Close connection managers (ordered shutdown per TDD-CONNECTION-LIFECYCLE-001)
    if hasattr(app.state, "connection_registry"):
        try:
            await app.state.connection_registry.close_all_async()
            logger.info("connection_registry_shutdown_complete")
        except Exception as e:
            logger.warning(
                "connection_registry_shutdown_error",
                extra={"error": str(e)},
            )

    # Shutdown
    logger.info(
        "api_stopping",
        extra={"service": "autom8_asana"},
    )



# Re-exports from preload/ subpackage for backward compatibility (removed in C4)
from .preload.legacy import (  # noqa: F401
    _do_full_rebuild,
    _do_incremental_catchup,
    _preload_dataframe_cache,
)
from .preload.progressive import (  # noqa: F401
    _invoke_cache_warmer_lambda_from_preload,
    _preload_dataframe_cache_progressive,
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
            InstrumentationConfig(service_name="asana"),
        )
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
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
