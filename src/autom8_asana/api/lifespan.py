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


async def _drain_background_builds(
    tasks: set[asyncio.Task[None]],
    drain_timeout: float,
) -> None:
    """Bounded-wait for in-flight background builds at SIGTERM shutdown (TD-004).

    Per thermia cache-architecture ADR-002: ECS task replacement sends SIGTERM,
    the lifespan context exits, and the fire-and-forget builds in
    ``universal_strategy._background_tasks`` would otherwise be orphaned mid-flight
    (RECV-BULK-002). This waits up to ``drain_timeout`` seconds for the *not-yet-done*
    tasks to finish/checkpoint. Tasks still pending after the window are left as-is
    (same orphaning as the pre-TD-004 behavior — never worse).

    SAFETY INVARIANT (ADR-002, Q5 RESOLVED): callers MUST ensure
    ``drain_timeout`` <= the ECS ``deregistration_delay`` (default 300s, >=30s). A
    drain LONGER than the deregistration delay would let ECS SIGKILL the task
    mid-drain — re-orphaning builds and defeating this drain. ``deregistration_delay``
    is an infra/TF config (autom8y repo), not enforced in code here.

    A ``drain_timeout`` of 0 (or no pending tasks) is a no-op: shutdown proceeds
    immediately.

    Args:
        tasks: The background-build task set (``_background_tasks``).
        drain_timeout: Max seconds to wait. Values <= 0 skip the drain.
    """
    if drain_timeout <= 0:
        return
    pending = {t for t in tasks if not t.done()}
    if not pending:
        return

    logger.info(
        "build_drain_starting",
        extra={"task_count": len(pending), "drain_timeout_seconds": drain_timeout},
    )
    done, still_pending = await asyncio.wait(pending, timeout=drain_timeout)
    if still_pending:
        logger.warning(
            "build_drain_incomplete",
            extra={
                "drained": len(done),
                "still_pending": len(still_pending),
                "drain_timeout_seconds": drain_timeout,
            },
        )
    else:
        logger.info("build_drain_complete", extra={"drained": len(done)})


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
        None (control returned to request handlers; startup state on app.state
        includes cache_provider, client_pool, entity_write_registry,
        cache_warming_task).
    """
    # Startup
    # Bootstrap business model registry before any detection calls
    from autom8_asana.models.business._bootstrap import bootstrap

    bootstrap()

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

    # DEF-005: Create a shared SDK CacheProvider once so warm-up tasks and
    # request-handler clients can share the same cache backend instance.
    # Without this, each AsanaClient auto-detects its own provider, which
    # creates isolated InMemoryCacheProvider instances in non-Redis
    # environments -- warm-up data becomes invisible to request handlers.
    from autom8_asana.cache.integration.factory import create_cache_provider
    from autom8_asana.config import AsanaConfig

    _sdk_config = AsanaConfig()
    app.state.cache_provider = create_cache_provider(_sdk_config.cache)
    logger.info(
        "shared_cache_provider_initialized",
        extra={"provider_type": type(app.state.cache_provider).__name__},
    )

    # Initialize token-keyed client pool for S2S resilience (IMP-19)
    # Allows rate limiters, circuit breakers, and AIMD semaphores to
    # accumulate state across requests sharing the same token.
    # DEF-005: pass shared cache_provider so pooled clients share the same
    # cache backend as the shared request-handler pool.
    app.state.client_pool = ClientPool(
        cache_provider=app.state.cache_provider,
    )
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

    # Initialize BuildCoordinator for cross-key concurrency control on the
    # request-time build-on-miss path (receiver-bulk-fanout-reliability
    # Stage-1 Surface A, ADR-ARCH-001).
    # MUST be inside lifespan: BuildCoordinator constructs an asyncio.Semaphore
    # in __post_init__, which requires a running event loop. Module-import-
    # time instantiation raises RuntimeError("no running event loop").
    # Defaults: max_concurrent_builds=4 (Phase-3 Knob 1, conservative for
    # single-worker uvicorn); default_timeout_seconds=55.0 (Phase-3 Knob 2,
    # fits under AWS ALB default idle_timeout of 60s with 5s teardown margin).
    from autom8_asana.cache.dataframe.factory import initialize_build_coordinator

    initialize_build_coordinator()

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
    except Exception as e:  # BROAD-CATCH: degrade  # noqa: BLE001
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
        app.state.workflow_configs_registered = True
        from autom8_asana.api.routes.health import set_workflow_configs_registered

        set_workflow_configs_registered(True)
        logger.info(
            "workflow_configs_registered",
            extra={"workflow_ids": ["insights-export", "conversation-audit"]},
        )
    except Exception as e:  # BROAD-CATCH: degrade  # noqa: BLE001
        app.state.workflow_configs_registered = False
        from autom8_asana.api.routes.health import set_workflow_configs_registered

        set_workflow_configs_registered(False)
        logger.warning(
            "workflow_configs_registration_failed",
            extra={
                "error": str(e),
                "impact": "Workflow invoke endpoint will return 404 for all workflows",
            },
        )

    # L1 (WS-4a): Validate cascade warm-up ordering before preload.
    # Catches misconfiguration early — warm_priority must respect cascade
    # dependency graph. Raises ValueError on conflict (fail-fast).
    from autom8_asana.dataframes.cascade_utils import validate_cascade_ordering

    try:
        validate_cascade_ordering()
        logger.info("cascade_ordering_validated")
    except ValueError as e:
        logger.error(
            "cascade_ordering_validation_failed",
            extra={"error": str(e)},
        )
        raise

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

    # Start the event-loop lag monitor (TD-007, observability-plan §1.2).
    # Cheap: one slow background timer feeding event_loop_lag_seconds — the
    # leading indicator of the CPU-on-loop starvation TD-001 fixes. No per-request
    # cost. Stored on app.state so it is cancelled cleanly at shutdown.
    from autom8_asana.api.event_loop_monitor import EventLoopLagMonitor

    event_loop_lag_monitor = EventLoopLagMonitor()
    event_loop_lag_monitor.start()
    app.state.event_loop_lag_monitor = event_loop_lag_monitor

    # Per TDD-SECTION-TIMELINE-REMEDIATION: Section timeline warm-up pipeline
    # REMOVED. Timeline data is now computed on first request and served from
    # derived cache on subsequent requests. No app.state keys for timeline
    # data, no startup-time story cache warming, no readiness gates.

    yield

    # SIGTERM graceful drain (TD-004, thermia cache-architecture ADR-002).
    # Drain in-flight fire-and-forget background builds BEFORE tearing down the
    # client pool below, so an in-flight build that needs an httpx client (via
    # app.state.client_pool) can still complete during the drain window. See
    # _drain_background_builds for the full ADR-002 safety invariant.
    #
    # NOTE: `settings` above is api/config.ApiSettings (ASANA_API_* surface) which
    # does NOT carry the drain knob. The drain timeout lives on the SDK
    # RuntimeSettings (autom8_asana.settings), so read it from there explicitly.
    from autom8_asana.services.universal_strategy import _background_tasks
    from autom8_asana.settings import get_settings as get_sdk_settings

    await _drain_background_builds(
        _background_tasks,
        get_sdk_settings().runtime.build_drain_timeout_seconds,
    )

    # Stop the event-loop lag monitor (TD-007).
    if hasattr(app.state, "event_loop_lag_monitor"):
        try:
            await app.state.event_loop_lag_monitor.stop()
        except Exception as e:  # BROAD-CATCH: degrade  # noqa: BLE001
            logger.warning("event_loop_lag_monitor_stop_error", extra={"error": str(e)})

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
            except Exception as e:  # BROAD-CATCH: degrade  # noqa: BLE001
                logger.warning(
                    "cache_warming_cancel_error",
                    extra={"error": str(e)},
                )

    # Close client pool (IMP-19)
    if hasattr(app.state, "client_pool"):
        try:
            await app.state.client_pool.close_all()
            logger.info("client_pool_shutdown_complete")
        except Exception as e:  # BROAD-CATCH: degrade  # noqa: BLE001
            logger.warning(
                "client_pool_shutdown_error",
                extra={"error": str(e)},
            )

    # Close connection managers (ordered shutdown per TDD-CONNECTION-LIFECYCLE-001)
    if hasattr(app.state, "connection_registry"):
        try:
            await app.state.connection_registry.close_all_async()
            logger.info("connection_registry_shutdown_complete")
        except Exception as e:  # BROAD-CATCH: degrade  # noqa: BLE001
            logger.warning(
                "connection_registry_shutdown_error",
                extra={"error": str(e)},
            )

    # Shutdown
    logger.info(
        "api_stopping",
        extra={"service": "autom8_asana"},
    )
