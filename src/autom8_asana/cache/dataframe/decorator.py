"""Class decorator for DataFrame caching on resolution strategies.

Per TDD-DATAFRAME-CACHE-001: Decorator pattern for transparent caching
with cache miss -> 503 response behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache

logger = get_logger(__name__)

T = TypeVar("T")


def dataframe_cache(
    cache_provider: Callable[[], DataFrameCache | None],
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
        original_resolve = cls.resolve  # type: ignore[attr-defined]

        async def _check_bypass(
            self: T,
            criteria: list[Any],
            project_gid: str,
            client: Any,
        ) -> list[Any] | None:
            """Check if caching is bypassed via environment variable.

            Returns resolved result if bypassed, None otherwise.
            """
            from autom8_asana.settings import get_settings

            if get_settings().runtime.dataframe_cache_bypass:
                logger.debug(
                    "dataframe_cache_bypassed",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                    },
                )
                result: list[Any] = await original_resolve(
                    self, criteria, project_gid, client
                )
                return result
            return None

        async def _try_cache_hit(
            self: T,
            cache: DataFrameCache,
            criteria: list[Any],
            project_gid: str,
            client: Any,
        ) -> list[Any] | None:
            """Attempt to resolve from cached DataFrame.

            Returns resolved result on cache hit, None on miss.
            """
            entry = await cache.get_async(project_gid, entity_type)
            if entry is not None:
                self._cached_dataframe = entry.dataframe  # type: ignore[attr-defined]
                result: list[Any] = await original_resolve(
                    self, criteria, project_gid, client
                )
                return result
            return None

        async def _wait_for_build(
            self: T,
            cache: DataFrameCache,
            criteria: list[Any],
            project_gid: str,
            client: Any,
        ) -> list[Any]:
            """Wait for another request's in-progress build to complete.

            Returns resolved result if build succeeds within timeout.
            Raises ApiDataFrameBuildError(503) on timeout.
            """
            entry = await cache.wait_for_build_async(
                project_gid,
                entity_type,
                timeout_seconds=30.0,
            )

            if entry is not None:
                self._cached_dataframe = entry.dataframe  # type: ignore[attr-defined]
                result: list[Any] = await original_resolve(
                    self, criteria, project_gid, client
                )
                return result

            logger.warning(
                "dataframe_cache_wait_timeout",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                },
            )
            from autom8_asana.api.exception_types import (
                ApiDataFrameBuildError,  # noqa: E501 -- lazy import avoids circular dependency
            )

            raise ApiDataFrameBuildError(
                "CACHE_BUILD_IN_PROGRESS",
                "DataFrame build in progress, retry shortly",
                retry_after_seconds=5,
            )

        async def _execute_build_and_cache(
            self: T,
            cache: DataFrameCache,
            criteria: list[Any],
            project_gid: str,
            client: Any,
        ) -> list[Any]:
            """Build DataFrame, cache it, and resolve.

            Handles lock release on both success and failure paths.
            Raises ApiDataFrameBuildError(503) if build method is missing, returns None,
            or raises an unexpected error.
            """
            try:
                build_func = getattr(self, build_method, None)
                if build_func is None:
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
                    from autom8_asana.api.exception_types import (
                        ApiDataFrameBuildError,  # noqa: E501 -- lazy import avoids circular dependency
                    )

                    raise ApiDataFrameBuildError(
                        "DATAFRAME_BUILD_UNAVAILABLE",
                        "No build method configured",
                    )

                build_result = await build_func(project_gid, client)

                df: pl.DataFrame | None
                if isinstance(build_result, tuple) and len(build_result) == 2:
                    df, watermark = build_result
                else:
                    df = build_result
                    watermark = datetime.now(UTC)

                if df is None:
                    await cache.release_build_lock_async(
                        project_gid, entity_type, success=False
                    )
                    from autom8_asana.api.exception_types import (
                        ApiDataFrameBuildError,  # noqa: E501 -- lazy import avoids circular dependency
                    )

                    raise ApiDataFrameBuildError(
                        "DATAFRAME_BUILD_FAILED",
                        "Failed to build DataFrame",
                        retry_after_seconds=30,
                    )

                await cache.put_async(project_gid, entity_type, df, watermark)

                await cache.release_build_lock_async(
                    project_gid, entity_type, success=True
                )

                self._cached_dataframe = df  # type: ignore[attr-defined]
                result: list[Any] = await original_resolve(
                    self, criteria, project_gid, client
                )
                return result

            except Exception as e:  # BROAD-CATCH: boundary -- catch-all converts to typed exception at API boundary
                from autom8_asana.api.exception_types import (
                    ApiDataFrameBuildError,  # noqa: E501 -- lazy import avoids circular dependency
                )

                if isinstance(e, ApiDataFrameBuildError):
                    raise

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
                raise ApiDataFrameBuildError(
                    "DATAFRAME_BUILD_ERROR",
                    f"Build failed: {type(e).__name__}",
                    retry_after_seconds=30,
                )

        @wraps(original_resolve)
        async def cached_resolve(
            self: T,
            criteria: list[Any],
            project_gid: str,
            client: Any,
        ) -> list[Any]:
            # Check bypass for testing
            bypass_result = await _check_bypass(self, criteria, project_gid, client)
            if bypass_result is not None:
                return bypass_result

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
                result: list[Any] = await original_resolve(
                    self, criteria, project_gid, client
                )
                return result

            # Try cache hit
            hit_result = await _try_cache_hit(
                self, cache, criteria, project_gid, client
            )
            if hit_result is not None:
                return hit_result

            # Cache miss - check if build is in progress
            acquired = await cache.acquire_build_lock_async(project_gid, entity_type)

            if not acquired:
                return await _wait_for_build(self, cache, criteria, project_gid, client)

            # This request should build
            return await _execute_build_and_cache(
                self, cache, criteria, project_gid, client
            )

        cls.resolve = cached_resolve  # type: ignore[attr-defined]
        return cls

    return decorator
