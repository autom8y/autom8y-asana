"""Factory for DataFrameCache singleton initialization.

Per TDD-DATAFRAME-CACHE-001: Provides singleton access to the DataFrameCache
instance with proper configuration from settings.

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
    from autom8_asana.cache.dataframe_cache import DataFrameCache

logger = get_logger(__name__)


def initialize_dataframe_cache() -> "DataFrameCache | None":
    """Initialize the singleton DataFrameCache with settings from environment.

    Creates a DataFrameCache instance configured with:
    - MemoryTier: 30% heap limit, 100 max entries
    - S3Tier: From ASANA_CACHE_S3_BUCKET and ASANA_CACHE_S3_PREFIX settings
    - DataFrameCacheCoalescer: For thundering herd prevention
    - CircuitBreaker: Per-project failure isolation

    Per TDD-DATAFRAME-CACHE-001:
    - Memory tier is hot cache with LRU eviction
    - S3 tier is cold storage (source of truth)
    - 12-hour default TTL

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
    from autom8_asana.cache.dataframe.tiers.s3 import S3Tier
    from autom8_asana.cache.dataframe_cache import (
        DataFrameCache,
        get_dataframe_cache as _get_cache,
        set_dataframe_cache,
    )
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
        max_heap_percent=0.3,
        max_entries=100,
    )

    # Build S3 prefix for DataFrame cache (separate from general cache)
    s3_prefix = f"{settings.s3.prefix}/dataframes/"

    s3_tier = S3Tier(
        bucket=settings.s3.bucket,
        prefix=s3_prefix,
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
        s3_tier=s3_tier,
        coalescer=coalescer,
        circuit_breaker=circuit_breaker,
        ttl_hours=12,
    )

    # Set as singleton
    set_dataframe_cache(cache)

    logger.info(
        "dataframe_cache_initialized",
        extra={
            "s3_bucket": settings.s3.bucket,
            "s3_prefix": s3_prefix,
            "ttl_hours": 12,
            "memory_max_entries": 100,
            "memory_heap_percent": 0.3,
        },
    )

    return cache


def get_dataframe_cache_provider() -> "DataFrameCache | None":
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
    from autom8_asana.cache.dataframe_cache import (
        get_dataframe_cache as _get_cache,
    )

    return _get_cache()


# Re-export for convenience
def get_dataframe_cache() -> "DataFrameCache | None":
    """Get the singleton DataFrameCache instance.

    Returns:
        DataFrameCache if initialized, None otherwise.
    """
    from autom8_asana.cache.dataframe_cache import (
        get_dataframe_cache as _get_cache,
    )

    return _get_cache()


def reset_dataframe_cache() -> None:
    """Reset the singleton DataFrameCache (for testing).

    Clears the singleton instance so next initialization creates fresh cache.
    """
    from autom8_asana.cache.dataframe_cache import (
        reset_dataframe_cache as _reset,
    )

    _reset()
    logger.debug("dataframe_cache_reset")
