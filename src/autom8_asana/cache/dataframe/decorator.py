"""Class decorator for DataFrame caching on resolution strategies.

Per TDD-DATAFRAME-CACHE-001: Decorator pattern for transparent caching
with cache miss -> 503 response behavior.
"""

from __future__ import annotations

import os
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from autom8y_log import get_logger
from fastapi import HTTPException

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import DataFrameCache

logger = get_logger(__name__)

T = TypeVar("T")


def dataframe_cache(
    cache_provider: Callable[[], "DataFrameCache | None"],
    entity_type: str,
    build_method: str = "_build_dataframe",
    bypass_env_var: str = "DATAFRAME_CACHE_BYPASS",
) -> Callable[[type[T]], type[T]]:
    """Class decorator adding DataFrame caching to resolution strategies.

    Wraps the strategy's resolve() method to:
    1. Check cache before building DataFrame
    2. Return 503 on cache miss with build in progress
    3. Trigger build and cache result on first request
    4. Inject _cached_dataframe into strategy instance

    Per TDD-DATAFRAME-CACHE-001 ADR-002:
    - Return 503 with retry guidance on cache miss
    - Trigger async build via coalescer
    - Clients implement exponential backoff

    Args:
        cache_provider: Callable returning DataFrameCache instance.
            May return None if cache is not configured.
        entity_type: Entity type for cache key (unit, offer, contact).
        build_method: Name of method that builds the DataFrame.
            Must return tuple of (DataFrame, watermark datetime).
        bypass_env_var: Environment variable to bypass caching (for tests).

    Returns:
        Decorated class with caching behavior.

    Example:
        >>> @dataframe_cache(
        ...     cache_provider=lambda: get_dataframe_cache(),
        ...     entity_type="offer",
        ... )
        ... class OfferResolutionStrategy:
        ...     async def resolve(self, criteria, project_gid, client):
        ...         # DataFrame access via self._cached_dataframe
        ...         ...
        ...
        ...     async def _build_dataframe(self, project_gid, client):
        ...         # Build and return (df, watermark)
        ...         ...
    """

    def decorator(cls: type[T]) -> type[T]:
        original_resolve = cls.resolve

        @wraps(original_resolve)
        async def cached_resolve(
            self: T,
            criteria: list[Any],
            project_gid: str,
            client: Any,
        ) -> list[Any]:
            # Check bypass for testing
            if os.environ.get(bypass_env_var, "").lower() in ("1", "true", "yes"):
                logger.debug(
                    "dataframe_cache_bypassed",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                    },
                )
                return await original_resolve(self, criteria, project_gid, client)

            cache = cache_provider()

            # If no cache configured, fall back to original behavior
            if cache is None:
                logger.debug(
                    "dataframe_cache_not_configured",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                    },
                )
                return await original_resolve(self, criteria, project_gid, client)

            # Try to get cached DataFrame
            entry = await cache.get_async(project_gid, entity_type)

            if entry is not None:
                # Cache hit - inject DataFrame and resolve
                self._cached_dataframe = entry.dataframe
                return await original_resolve(self, criteria, project_gid, client)

            # Cache miss - check if build is in progress
            acquired = await cache.acquire_build_lock_async(project_gid, entity_type)

            if not acquired:
                # Another request is building - wait for it
                entry = await cache.wait_for_build_async(
                    project_gid,
                    entity_type,
                    timeout_seconds=30.0,
                )

                if entry is not None:
                    self._cached_dataframe = entry.dataframe
                    return await original_resolve(self, criteria, project_gid, client)

                # Timeout or failure
                logger.warning(
                    "dataframe_cache_wait_timeout",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                    },
                )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "CACHE_BUILD_IN_PROGRESS",
                        "message": "DataFrame build in progress, retry shortly",
                        "retry_after_seconds": 5,
                    },
                )

            # This request should build
            try:
                # Call the build method
                build_func = getattr(self, build_method, None)
                if build_func is None:
                    # Try entity-specific build method
                    build_func = getattr(self, f"_build_{entity_type}_dataframe", None)

                if build_func is None:
                    logger.error(
                        "dataframe_cache_no_build_method",
                        extra={
                            "entity_type": entity_type,
                            "build_method": build_method,
                        },
                    )
                    await cache.release_build_lock_async(
                        project_gid, entity_type, success=False
                    )
                    raise HTTPException(
                        status_code=503,
                        detail={
                            "error": "DATAFRAME_BUILD_UNAVAILABLE",
                            "message": "No build method configured",
                        },
                    )

                # Build returns (dataframe, watermark)
                result = await build_func(project_gid, client)

                # Handle both tuple and single return value
                if isinstance(result, tuple) and len(result) == 2:
                    df, watermark = result
                else:
                    # Assume it's just the DataFrame, use current time as watermark
                    from datetime import datetime, timezone

                    df = result
                    watermark = datetime.now(timezone.utc)

                if df is None:
                    await cache.release_build_lock_async(
                        project_gid, entity_type, success=False
                    )
                    raise HTTPException(
                        status_code=503,
                        detail={
                            "error": "DATAFRAME_BUILD_FAILED",
                            "message": "Failed to build DataFrame",
                            "retry_after_seconds": 30,
                        },
                    )

                # Store in cache
                await cache.put_async(project_gid, entity_type, df, watermark)

                # Release lock with success
                await cache.release_build_lock_async(
                    project_gid, entity_type, success=True
                )

                # Resolve with fresh DataFrame
                self._cached_dataframe = df
                return await original_resolve(self, criteria, project_gid, client)

            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise

            except Exception as e:
                # Release lock with failure
                await cache.release_build_lock_async(
                    project_gid, entity_type, success=False
                )

                logger.error(
                    "dataframe_cache_build_failed",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "DATAFRAME_BUILD_ERROR",
                        "message": f"Build failed: {type(e).__name__}",
                        "retry_after_seconds": 30,
                    },
                )

        cls.resolve = cached_resolve
        return cls

    return decorator
