"""Application startup initialization helpers.

Extracted from api/main.py per TDD-I5 (API Main Decomposition).
These functions are called during the lifespan startup phase.
"""

from autom8y_log import get_logger
from fastapi import FastAPI

logger = get_logger(__name__)


def _initialize_dataframe_cache(app: FastAPI) -> None:
    """Initialize the DataFrameCache and store on app.state.

    Per TDD-DATAFRAME-CACHE-001 Phase 2:
    - Initializes DataFrameCache with Memory + S3 tiering
    - Stores instance on app.state.dataframe_cache for FastAPI DI
    - Used by @dataframe_cache decorator on Offer/Contact strategies
    - Graceful degradation if S3 not configured (logs warning, cache disabled)

    Per ADR-0067: Aligns DataFrameCache lifecycle with CacheProvider pattern,
    storing on app.state rather than using a module-level singleton.

    Args:
        app: FastAPI application instance.

    This is called during application startup, after entity project discovery.
    """
    from autom8_asana.cache.dataframe.factory import initialize_dataframe_cache

    cache = initialize_dataframe_cache()
    app.state.dataframe_cache = cache

    if cache is not None:
        from autom8_asana.api.metrics import PrometheusMetricsEmitter

        cache.metrics_emitter = PrometheusMetricsEmitter()

        logger.info(
            "dataframe_cache_ready",
            extra={
                "status": "initialized",
                "entity_types": ["unit", "offer", "contact"],
            },
        )
    else:
        logger.warning(
            "dataframe_cache_disabled",
            extra={
                "reason": "S3 not configured",
                "impact": "Unit/Offer/Contact resolution will build DataFrames on every request",
            },
        )


def _register_schema_providers() -> None:
    """Register Asana schema providers with SDK registry.

    Per SDK Phase 1 schema versioning:
    - Bridges satellite SchemaRegistry to SDK SchemaVersionProvider
    - Enables cache compatibility checks based on schema versions
    - Required for schema mismatch detection (SC-004)

    This is called during application startup, after entity project discovery.
    """
    from autom8_asana.cache.integration.schema_providers import register_asana_schemas

    register_asana_schemas()


def _initialize_mutation_invalidator(app: FastAPI) -> None:
    """Initialize the MutationInvalidator for REST cache invalidation.

    Per TDD-CACHE-INVALIDATION-001: Creates a MutationInvalidator with
    the app's cache provider and DataFrameCache, and stores it on app.state
    for injection via get_mutation_invalidator() dependency.

    Graceful degradation: If cache is not configured, creates a no-op
    invalidator that logs warnings but does not fail.

    Args:
        app: FastAPI application instance.
    """
    from autom8_asana.cache.integration.factory import CacheProviderFactory
    from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator
    from autom8_asana.config import CacheConfig

    try:
        # Get or create a cache provider for invalidation
        cache_provider = CacheProviderFactory.create(config=CacheConfig(enabled=True))
        # Read DataFrameCache from app.state (populated by _initialize_dataframe_cache)
        dataframe_cache = getattr(app.state, "dataframe_cache", None)

        app.state.mutation_invalidator = MutationInvalidator(
            cache_provider=cache_provider,
            dataframe_cache=dataframe_cache,
        )

        logger.info(
            "mutation_invalidator_ready",
            extra={
                "has_dataframe_cache": dataframe_cache is not None,
            },
        )
    except Exception as exc:  # BROAD-CATCH: startup  # noqa: BLE001
        # Graceful degradation: invalidation disabled but app still works
        logger.warning(
            "mutation_invalidator_init_failed",
            extra={
                "error": str(exc),
                "impact": "REST mutations will not invalidate cache",
            },
        )


async def _discover_entity_projects(app: FastAPI) -> None:
    """Discover and register entity type project mappings.

    Delegates to the extracted ``discover_entity_projects_async`` service
    and stores the resulting registry on ``app.state``.

    Args:
        app: FastAPI application instance

    Raises:
        RuntimeError: If collision detected (fail-fast per user decision)
        Exception: If discovery fails (fail-fast per ADR-0060)
    """
    from autom8_asana.services.discovery import discover_entity_projects_async

    entity_registry = await discover_entity_projects_async()
    app.state.entity_project_registry = entity_registry
