"""Factory for DataFrameCache singleton initialization.

Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
Provides singleton access to the DataFrameCache instance with proper
configuration from settings.

Uses ProgressiveTier to read/write DataFrames from the same location
as SectionPersistence (ProgressiveProjectBuilder), eliminating the
dual-location bug where S3Tier and SectionPersistence used different paths.

Usage:
    >>> from autom8_asana.cache.dataframe.factory import (
    ...     initialize_dataframe_cache,
    ...     get_dataframe_cache,
    ... )
    >>>
    >>> # Initialize during app startup
    >>> initialize_dataframe_cache()
    >>>
    >>> # Get cache instance (returns None if not initialized)
    >>> cache = get_dataframe_cache()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache

logger = get_logger(__name__)


async def _swr_build_callback(
    cache: DataFrameCache,
    project_gid: str,
    entity_type: str,
) -> None:
    """SWR background rebuild callback.

    Extracted from initialize_dataframe_cache closure for testability.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
    from autom8_asana.dataframes.models.registry import get_schema
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import create_section_persistence
    from autom8_asana.services.resolver import to_pascal_case

    try:
        bot_pat = get_bot_pat()
    except BotPATError:
        logger.warning("swr_build_no_bot_pat", extra={"project_gid": project_gid})
        return

    from autom8_asana.config import get_workspace_gid

    workspace_gid = get_workspace_gid()
    if not workspace_gid:
        logger.warning("swr_build_no_workspace", extra={"project_gid": project_gid})
        return

    async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
        task_type = to_pascal_case(entity_type)
        schema = get_schema(task_type)
        resolver = DefaultCustomFieldResolver()
        section_persistence = create_section_persistence()

        async with section_persistence:
            builder = ProgressiveProjectBuilder(
                client=client,
                project_gid=project_gid,
                entity_type=entity_type,
                schema=schema,
                persistence=section_persistence,
                resolver=resolver,
                store=client.unified_store,
            )
            result = await builder.build_progressive_async(resume=True)

        if result.total_rows > 0 and result.dataframe is not None:
            await cache.put_async(
                project_gid,
                entity_type,
                result.dataframe,
                result.watermark,
            )


def initialize_dataframe_cache() -> DataFrameCache | None:
    """Initialize the singleton DataFrameCache with settings from environment.

    Creates a DataFrameCache instance configured with:
    - MemoryTier: 30% heap limit, 100 max entries
    - ProgressiveTier: Uses SectionPersistence storage location
    - DataFrameCacheCoalescer: For thundering herd prevention
    - CircuitBreaker: Per-project failure isolation

    Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
    - Memory tier is hot cache with LRU eviction
    - Progressive tier reads/writes to SectionPersistence location
    - Entity-aware TTLs with SWR

    Returns:
        Initialized DataFrameCache instance, or None if S3 not configured.

    Example:
        >>> # In api/main.py lifespan
        >>> await initialize_dataframe_cache()
        >>>
        >>> # Later in resolution strategies
        >>> cache = get_dataframe_cache()
    """
    from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
    from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
    from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
    from autom8_asana.cache.integration.dataframe_cache import (
        DataFrameCache,
        set_dataframe_cache,
    )
    from autom8_asana.cache.integration.dataframe_cache import (
        get_dataframe_cache as _get_cache,
    )
    from autom8_asana.dataframes.section_persistence import create_section_persistence
    from autom8_asana.settings import get_settings

    # Check if already initialized
    existing = _get_cache()
    if existing is not None:
        logger.debug("dataframe_cache_already_initialized")
        return existing

    settings = get_settings()

    # Check if S3 is configured
    if not settings.s3.bucket:
        logger.warning(
            "dataframe_cache_s3_not_configured",
            extra={
                "detail": (
                    "ASANA_CACHE_S3_BUCKET not set. "
                    "DataFrameCache will not be available. "
                    "Resolution strategies will build DataFrames on every request."
                ),
            },
        )
        return None

    # Create tiers
    memory_tier = MemoryTier(
        max_heap_percent=settings.cache.dataframe_heap_percent,
        max_entries=settings.cache.dataframe_max_entries,
    )

    # Create SectionPersistence for ProgressiveTier
    # Uses the standard "dataframes/" prefix to match ProgressiveProjectBuilder
    persistence = create_section_persistence()

    progressive_tier = ProgressiveTier(
        persistence=persistence,
    )

    # Create coalescer and circuit breaker
    coalescer = DataFrameCacheCoalescer(
        max_wait_seconds=60.0,
    )

    circuit_breaker = CircuitBreaker(
        failure_threshold=3,
        reset_timeout_seconds=60,
        success_threshold=1,
    )

    # Create cache instance
    # Note: schema_version is no longer passed here - each entity type uses
    # its schema version from SchemaRegistry. The default "1.0.0" in the
    # DataFrameCache dataclass is only used as a fallback if registry
    # lookup fails during put_async().
    cache = DataFrameCache(
        memory_tier=memory_tier,
        progressive_tier=progressive_tier,
        coalescer=coalescer,
        circuit_breaker=circuit_breaker,
    )

    from functools import partial

    cache.set_build_callback(partial(_swr_build_callback, cache))

    # Set as singleton
    set_dataframe_cache(cache)

    logger.info(
        "dataframe_cache_initialized",
        extra={
            "tier_type": "progressive",
            "s3_bucket": settings.s3.bucket,
            "memory_max_entries": settings.cache.dataframe_max_entries,
            "memory_heap_percent": settings.cache.dataframe_heap_percent,
        },
    )

    return cache


def get_dataframe_cache_provider() -> DataFrameCache | None:
    """Get the DataFrameCache singleton for use with @dataframe_cache decorator.

    This function is designed to be passed to the @dataframe_cache decorator's
    cache_provider parameter. It returns the singleton instance or None if
    not initialized.

    Returns:
        DataFrameCache instance or None.

    Example:
        >>> @dataframe_cache(
        ...     cache_provider=get_dataframe_cache_provider,
        ...     entity_type="offer",
        ... )
        ... class OfferResolutionStrategy:
        ...     ...
    """
    from autom8_asana.cache.integration.dataframe_cache import (
        get_dataframe_cache as _get_cache,
    )

    return _get_cache()


# Re-export for convenience
def get_dataframe_cache() -> DataFrameCache | None:
    """Get the singleton DataFrameCache instance.

    Returns:
        DataFrameCache if initialized, None otherwise.
    """
    from autom8_asana.cache.integration.dataframe_cache import (
        get_dataframe_cache as _get_cache,
    )

    return _get_cache()


def reset_dataframe_cache() -> None:
    """Reset the singleton DataFrameCache (for testing).

    Clears the singleton instance so next initialization creates fresh cache.
    """
    from autom8_asana.cache.integration.dataframe_cache import (
        reset_dataframe_cache as _reset,
    )

    _reset()
    logger.debug("dataframe_cache_reset")
