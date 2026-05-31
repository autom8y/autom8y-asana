"""Factory for DataFrameCache singleton initialization.

Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
Provides singleton access to the DataFrameCache instance with proper
configuration from settings.

Uses ProgressiveTier to read/write DataFrames from the same location
as SectionPersistence (ProgressiveProjectBuilder), eliminating the
dual-location bug where S3Tier and SectionPersistence used different paths.

Per receiver-bulk-fanout-reliability Stage-1 (Surface A, ADR-ARCH-001):
Also provides accessors for the BuildCoordinator singleton — same module-
level accessor pattern as ``get_dataframe_cache_provider()``. The
``BuildCoordinator``'s ``asyncio.Semaphore`` requires a running event loop,
so instantiation MUST happen inside FastAPI's lifespan (after the event
loop is up), not at module-import time.

Usage:
    >>> from autom8_asana.cache.dataframe.factory import (
    ...     initialize_dataframe_cache,
    ...     get_dataframe_cache,
    ...     initialize_build_coordinator,
    ...     get_build_coordinator,
    ... )
    >>>
    >>> # Initialize during app startup (inside FastAPI lifespan)
    >>> initialize_dataframe_cache()
    >>> initialize_build_coordinator()
    >>>
    >>> # Get instances (return None if not initialized)
    >>> cache = get_dataframe_cache()
    >>> coordinator = get_build_coordinator()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe.build_coordinator import BuildCoordinator
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache

logger = get_logger(__name__)

# Module-level singleton for Lambda and non-FastAPI contexts.
# FastAPI routes use app.state.dataframe_cache via get_dataframe_cache() dependency.
_dataframe_cache: DataFrameCache | None = None

# Module-level BuildCoordinator singleton (Surface A).
# MUST be initialized inside an event-loop context (FastAPI lifespan) because
# ``BuildCoordinator.__post_init__`` creates an ``asyncio.Semaphore`` that
# requires a running loop. Tests inject directly via ``set_build_coordinator``.
_build_coordinator: BuildCoordinator | None = None


async def _swr_build_callback(
    cache: DataFrameCache,
    project_gid: str,
    entity_type: str,
) -> None:
    """SWR background rebuild callback.

    Extracted from initialize_dataframe_cache closure for testability.
    """
    import time

    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.core.string_utils import to_pascal_case
    from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
    from autom8_asana.dataframes.models.registry import get_schema
    from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    from autom8_asana.dataframes.section_persistence import create_section_persistence

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

    logger.info(
        "swr_build_started",
        extra={"project_gid": project_gid, "entity_type": entity_type},
    )
    build_start = time.monotonic()

    try:
        async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
            task_type = to_pascal_case(entity_type)
            schema = get_schema(task_type)
            resolver = DefaultCustomFieldResolver()
            section_persistence = create_section_persistence()

            async with section_persistence:
                from autom8_asana.services.gid_lookup import build_gid_index_data

                builder = ProgressiveProjectBuilder(
                    client=client,
                    project_gid=project_gid,
                    entity_type=entity_type,
                    schema=schema,
                    persistence=section_persistence,
                    resolver=resolver,
                    store=client.unified_store,
                    index_builder=build_gid_index_data,
                )
                result = await builder.build_progressive_async(resume=True)

            if result.total_rows > 0 and result.dataframe is not None:
                await cache.put_async(
                    project_gid,
                    entity_type,
                    result.dataframe,
                    result.watermark,
                )

        duration_ms = (time.monotonic() - build_start) * 1000
        logger.info(
            "swr_build_complete",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "total_rows": result.total_rows,
                "duration_ms": round(duration_ms, 1),
            },
        )
    except Exception:
        duration_ms = (time.monotonic() - build_start) * 1000
        logger.exception(
            "swr_build_failed",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "duration_ms": round(duration_ms, 1),
            },
        )
        raise


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
    global _dataframe_cache

    from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
    from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
    from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
    from autom8_asana.dataframes.section_persistence import create_section_persistence
    from autom8_asana.settings import get_settings

    # Check if already initialized
    if _dataframe_cache is not None:
        logger.debug("dataframe_cache_already_initialized")
        return _dataframe_cache

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

    # Store in module-level singleton (Lambda and non-FastAPI contexts)
    _dataframe_cache = cache

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
    return _dataframe_cache


def get_dataframe_cache() -> DataFrameCache | None:
    """Get the singleton DataFrameCache instance.

    Used by Lambda handlers and non-FastAPI contexts. FastAPI routes should
    use the get_dataframe_cache() dependency from api.dependencies instead.

    Returns:
        DataFrameCache if initialized, None otherwise.
    """
    return _dataframe_cache


def set_dataframe_cache(cache: DataFrameCache) -> None:
    """Set the singleton DataFrameCache instance.

    Intended for testing and Lambda warm-up scenarios where the cache
    must be injected without calling initialize_dataframe_cache().

    Args:
        cache: DataFrameCache instance to store as singleton.
    """
    global _dataframe_cache
    _dataframe_cache = cache


def reset_dataframe_cache() -> None:
    """Reset the singleton DataFrameCache (for testing).

    Clears the singleton instance so next initialization creates fresh cache.
    """
    global _dataframe_cache
    _dataframe_cache = None
    logger.debug("dataframe_cache_reset")


# ---------------------------------------------------------------------------
# BuildCoordinator singleton accessors (Surface A — Stage-1)
# ---------------------------------------------------------------------------
#
# Per receiver-bulk-fanout-reliability ADR-ARCH-001: the coordinator MUST be
# instantiated inside an event-loop context (FastAPI lifespan). Mirrors the
# established ``initialize_dataframe_cache`` / ``get_dataframe_cache_provider``
# pattern above so universal_strategy._build_on_miss can access the singleton
# via a module-level call WITHOUT DI threading through resolution strategies.


def initialize_build_coordinator(
    max_concurrent_builds: int | None = None,
    default_timeout_seconds: float | None = None,
) -> BuildCoordinator:
    """Initialize the BuildCoordinator singleton.

    Called once from FastAPI lifespan AFTER the event loop is running.
    Idempotent: subsequent calls return the existing instance without
    re-instantiation (the semaphore would otherwise be replaced mid-flight,
    losing in-flight build state).

    Per Phase-3 Knob 1 + Knob 2 derivations:
    - ``max_concurrent_builds = 4`` (retained default — safe for single
      uvicorn worker with conservative container memory).
    - ``default_timeout_seconds = 55.0`` (must fit < ALB idle_timeout default
      of 60s with 5s connection-teardown margin; UV-P-1 will refine).

    Args:
        max_concurrent_builds: Cross-key concurrency cap. Default 4 from
            ``BuildCoordinator``'s own default.
        default_timeout_seconds: Per-call wait timeout. Default 55.0s
            (capacity-spec Phase-3 Knob 2).

    Returns:
        The BuildCoordinator singleton (newly-created or pre-existing).
    """
    global _build_coordinator

    if _build_coordinator is not None:
        logger.debug("build_coordinator_already_initialized")
        return _build_coordinator

    from autom8_asana.cache.dataframe.build_coordinator import BuildCoordinator

    # Use provided overrides or fall back to BuildCoordinator defaults.
    # Per Phase-3 Knob 2: 55s is the deploy-time conservative default that
    # fits under the AWS ALB idle_timeout default of 60s (UV-P-1).
    coordinator_kwargs: dict[str, float | int] = {}
    if max_concurrent_builds is not None:
        coordinator_kwargs["max_concurrent_builds"] = max_concurrent_builds
    coordinator_kwargs["default_timeout_seconds"] = (
        default_timeout_seconds if default_timeout_seconds is not None else 55.0
    )

    coordinator = BuildCoordinator(**coordinator_kwargs)  # type: ignore[arg-type]
    _build_coordinator = coordinator

    logger.info(
        "build_coordinator_initialized",
        extra={
            "max_concurrent_builds": coordinator.max_concurrent_builds,
            "default_timeout_seconds": coordinator.default_timeout_seconds,
        },
    )

    return coordinator


def get_build_coordinator() -> BuildCoordinator | None:
    """Get the BuildCoordinator singleton for build-on-miss coordination.

    Returns:
        BuildCoordinator instance if initialized, else None. Callers that
        find None MUST fall through to a safe path (e.g., the legacy
        per-key dedup set) rather than raising — the coordinator is an
        optimization, not a hard dependency.
    """
    return _build_coordinator


def set_build_coordinator(coordinator: BuildCoordinator | None) -> None:
    """Set or clear the BuildCoordinator singleton (for testing).

    Tests inject a BuildCoordinator with controlled semaphore size + timeout
    via this setter, mirroring ``set_dataframe_cache``.

    Args:
        coordinator: BuildCoordinator to install, or None to clear.
    """
    global _build_coordinator
    _build_coordinator = coordinator


def reset_build_coordinator() -> None:
    """Reset the BuildCoordinator singleton (for testing)."""
    global _build_coordinator
    _build_coordinator = None
    logger.debug("build_coordinator_reset")


# Self-register for SystemContext.reset_all()
from autom8_asana.core.system_context import register_reset  # noqa: E402

register_reset(reset_dataframe_cache)
register_reset(reset_build_coordinator)
