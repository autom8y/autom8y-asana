"""Application lifespan context manager.

Extracted from api/main.py per TDD-I5 (API Main Decomposition).
Manages startup initialization and shutdown cleanup for the FastAPI app.

Note: bare-except sites are preserved as-is from main.py.
They are tagged for narrowing in I6 (Exception Narrowing).
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from autom8y_log import get_logger
from autom8y_log.processors import add_otel_trace_ids
from fastapi import FastAPI

from autom8_asana.client import AsanaClient
from autom8_asana.core.logging import configure as configure_logging

from .client_pool import ClientPool
from .config import get_settings
from .middleware import _filter_sensitive_data
from .preload import _preload_dataframe_cache_progressive
from .startup import (
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
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        format="console" if settings.debug else "auto",
        additional_processors=[add_otel_trace_ids, _filter_sensitive_data],
    )

    # Activate global httpx auto-instrumentation so ALL httpx.AsyncClient
    # instances (including DataServiceClient's direct clients) propagate
    # W3C traceparent headers automatically. This complements the transport-
    # level instrumentation in autom8y-http's InstrumentedTransport.
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("httpx_otel_instrumentation_enabled")
    except ImportError:
        logger.warning(
            "httpx_otel_instrumentation_unavailable",
            extra={
                "impact": "Direct httpx clients will not propagate W3C traceparent",
                "remediation": "Install opentelemetry-instrumentation-httpx>=0.42b0",
            },
        )

    logger.info(
        "api_starting",
        extra={
            "service": "autom8_asana",
            "log_level": settings.log_level,
            "debug": settings.debug,
            "rate_limit_rpm": settings.rate_limit_rpm,
        },
    )

    # Initialize token-keyed client pool for S2S resilience (IMP-19)
    # Allows rate limiters, circuit breakers, and AIMD semaphores to
    # accumulate state across requests sharing the same token.
    app.state.client_pool = ClientPool()
    logger.info("client_pool_initialized")

    # Entity resolver startup discovery (FR-004, FR-005)
    try:
        await _discover_entity_projects(app)
    except Exception as e:  # BROAD-CATCH: startup
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

    # Cross-registry consistency validation (QW-4)
    # Per ARCH-REVIEW-1: Prevent silent divergence between EntityRegistry
    # and EntityProjectRegistry (just populated by discovery above).
    # ProjectTypeRegistry is validated separately in Lambda bootstrap.
    # GID mismatches are logged as errors but do not block startup, since
    # EntityProjectRegistry is populated from live workspace discovery and
    # may legitimately diverge from static EntityDescriptor GIDs.
    from autom8_asana.core.registry_validation import (
        validate_cross_registry_consistency,
    )

    validation = validate_cross_registry_consistency(
        check_project_type_registry=False,
        check_entity_project_registry=True,
    )
    if not validation.ok:
        logger.error(
            "cross_registry_validation_failed",
            extra={"errors": validation.errors},
        )

    # Initialize DataFrameCache for Offer/Contact resolution strategies
    # Per TDD-DATAFRAME-CACHE-001: Provides tiered caching (Memory + S3)
    # Stores instance on app.state.dataframe_cache per ADR-0067.
    _initialize_dataframe_cache(app)

    # Register schema providers with SDK for cache compatibility checks
    # Per SDK Phase 1: Bridges satellite SchemaRegistry to SDK registry
    _register_schema_providers()

    # Initialize MutationInvalidator for REST cache invalidation
    # Per TDD-CACHE-INVALIDATION-001: Wire cache invalidation into REST routes
    _initialize_mutation_invalidator(app)

    # Initialize EntityWriteRegistry for entity write endpoint
    # Per TDD-ENTITY-WRITE-API Section 8.1: Built once at startup, stored on app.state.
    # Must be after entity discovery so EntityRegistry has project GIDs.
    try:
        from autom8_asana.core.entity_registry import get_registry
        from autom8_asana.resolution.write_registry import EntityWriteRegistry

        entity_registry = get_registry()
        write_registry = EntityWriteRegistry(entity_registry)
        app.state.entity_write_registry = write_registry
        logger.info(
            "entity_write_registry_ready",
            extra={"writable_types": write_registry.writable_types()},
        )
    except Exception as e:  # BROAD-CATCH: degrade
        logger.warning(
            "entity_write_registry_init_failed",
            extra={
                "error": str(e),
                "impact": "Entity write endpoint will return 503",
            },
        )

    # Register workflow configs for API invocation
    # Per TDD-ENTITY-SCOPE-001 Section 2.7.4: Reuse WorkflowHandlerConfig
    # from Lambda handlers for the API invoke endpoint.
    try:
        from autom8_asana.api.routes.workflows import register_workflow_config
        from autom8_asana.lambda_handlers.conversation_audit import (
            _config as audit_config,
        )
        from autom8_asana.lambda_handlers.insights_export import (
            _config as insights_config,
        )

        register_workflow_config(insights_config)
        register_workflow_config(audit_config)
        logger.info(
            "workflow_configs_registered",
            extra={"workflow_ids": ["insights-export", "conversation-audit"]},
        )
    except Exception as e:  # BROAD-CATCH: degrade
        logger.warning(
            "workflow_configs_registration_failed",
            extra={
                "error": str(e),
                "impact": "Workflow invoke endpoint will return 404 for all workflows",
            },
        )

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

    # --- Section Timeline Story Cache Pre-Warm (FR-7) ---
    # Per TDD-SECTION-TIMELINE-001: Background story cache warming
    # for section timeline endpoint readiness gating.
    #
    # IMPORTANT: The timeline warm must start AFTER cache_warming completes
    # to avoid Asana API rate limit saturation. Both tasks use bounded
    # concurrency (Semaphore(20)) independently; running them concurrently
    # yields ~40 parallel API slots, triggering 429s that cause the timeline
    # warm to timeout at 600s. Sequential staggering ensures only one warm
    # task makes API calls at a time.

    # Initialize progress counters and failure flag on app.state
    app.state.timeline_warm_count = 0
    app.state.timeline_total = 0
    app.state.timeline_warm_failed = False  # Set True on timeout or exception

    async def _warm_section_timeline_stories() -> None:
        """Background task: warm story caches for section timelines.

        Per SPIKE-SECTION-TIMELINE-CACHE: warm_story_caches() uses bounded-parallel
        concurrency (Semaphore(20)) so S3 promotion is fast (~5s for 500 offers).

        Per interview 2026-02-19: If warm-up exceeds _WARM_TIMEOUT_SECONDS or
        fails catastrophically, set app.state.timeline_warm_failed = True so
        the endpoint returns TIMELINE_WARM_FAILED (permanent 503) instead of
        TIMELINE_NOT_READY (retry-able 503). This distinguishes 'still starting'
        from 'broken and needs operator attention'.

        Waits for cache_warming_task to complete before starting story warm
        to avoid concurrent Asana API rate limit contention.
        """
        # Stagger: wait for DataFrame cache warming to finish first.
        # This prevents concurrent API call storms that saturate Asana's
        # rate limit (observed: 659 rate_limit_429_received events).
        try:
            await background_task  # cache_warming_task
            logger.info("timeline_warm_cache_warming_complete_proceeding")
        except asyncio.CancelledError:
            logger.info("timeline_warm_cache_warming_cancelled_proceeding")
            # Cache warming was cancelled (shutdown) -- don't proceed
            raise
        except Exception:
            # Cache warming failed, but timeline warm can still attempt
            # since it uses a separate Asana client and different API calls.
            logger.warning(
                "timeline_warm_cache_warming_failed_proceeding",
                extra={
                    "impact": "Timeline warm will proceed despite cache warming failure"
                },
            )

        from autom8_asana.services.section_timeline_service import (
            _WARM_TIMEOUT_SECONDS,
            warm_story_caches,
        )

        try:
            from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

            try:
                bot_pat = get_bot_pat()
            except BotPATError:
                logger.warning(
                    "timeline_warm_skipped_no_bot_pat",
                    extra={"reason": "ASANA_PAT not configured"},
                )
                # No bot PAT -> treat as permanent failure (operator must configure)
                app.state.timeline_warm_failed = True
                return

            warm_client = AsanaClient(token=bot_pat)

            def on_progress(warmed: int, total: int) -> None:
                app.state.timeline_warm_count = warmed
                app.state.timeline_total = total

            # Wrap with timeout. asyncio.wait_for raises TimeoutError on expiry.
            warmed, total = await asyncio.wait_for(
                warm_story_caches(client=warm_client, on_progress=on_progress),
                timeout=_WARM_TIMEOUT_SECONDS,
            )
            logger.info(
                "timeline_story_warm_complete",
                extra={"warmed": warmed, "total": total},
            )
        except TimeoutError:
            logger.error(
                "timeline_story_warm_timed_out",
                extra={"timeout_seconds": _WARM_TIMEOUT_SECONDS},
            )
            app.state.timeline_warm_failed = True
        except asyncio.CancelledError:
            logger.info("timeline_story_warm_cancelled")
            raise
        except Exception:
            logger.exception("timeline_story_warm_exception")
            app.state.timeline_warm_failed = True

    timeline_warm_task = asyncio.create_task(
        _warm_section_timeline_stories(),
        name="timeline_story_warm",
    )
    app.state.timeline_warm_task = timeline_warm_task

    logger.info(
        "timeline_story_warm_started_background",
        extra={"task_name": "timeline_story_warm"},
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
            except Exception as e:  # BROAD-CATCH: degrade
                logger.warning(
                    "cache_warming_cancel_error",
                    extra={"error": str(e)},
                )

    # Cancel timeline story warm task if still running
    if hasattr(app.state, "timeline_warm_task"):
        task = app.state.timeline_warm_task
        if not task.done():
            logger.info("timeline_story_warm_cancelling")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("timeline_story_warm_cancelled")
            except Exception as e:
                logger.warning(
                    "timeline_story_warm_cancel_error",
                    extra={"error": str(e)},
                )

    # Close client pool (IMP-19)
    if hasattr(app.state, "client_pool"):
        try:
            await app.state.client_pool.close_all()
            logger.info("client_pool_shutdown_complete")
        except Exception as e:  # BROAD-CATCH: degrade
            logger.warning(
                "client_pool_shutdown_error",
                extra={"error": str(e)},
            )

    # Close connection managers (ordered shutdown per TDD-CONNECTION-LIFECYCLE-001)
    if hasattr(app.state, "connection_registry"):
        try:
            await app.state.connection_registry.close_all_async()
            logger.info("connection_registry_shutdown_complete")
        except Exception as e:  # BROAD-CATCH: degrade
            logger.warning(
                "connection_registry_shutdown_error",
                extra={"error": str(e)},
            )

    # Shutdown
    logger.info(
        "api_stopping",
        extra={"service": "autom8_asana"},
    )
