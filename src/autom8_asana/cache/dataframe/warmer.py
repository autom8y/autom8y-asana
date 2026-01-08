"""Cache warmer for Lambda pre-deployment warming.

Per TDD-DATAFRAME-CACHE-001 Section 5.7:
- Priority order: configurable, default ["offer", "unit", "business", "contact"]
- No limit on warm budget
- Partial warm not acceptable in strict mode (all must succeed)
- Lambda-only (not local CLI)

This module provides:
- WarmResult: Enum for warm operation outcomes
- WarmStatus: Dataclass for per-entity-type warming status
- CacheWarmer: Main warmer class for priority-based pre-warming
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import DataFrameCache
    from autom8_asana.client import AsanaClient

logger = get_logger(__name__)


class WarmResult(Enum):
    """Result of a warm operation.

    Attributes:
        SUCCESS: Entity type warmed successfully.
        FAILURE: Warming failed with an error.
        SKIPPED: Warming skipped (e.g., no project configured).
    """

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class WarmStatus:
    """Status of entity type warming.

    Per TDD-DATAFRAME-CACHE-001: Captures result of warming a single
    entity type including timing and error information.

    Attributes:
        entity_type: Entity type that was warmed (e.g., "unit", "offer").
        result: WarmResult indicating success, failure, or skip.
        project_gid: Project GID that was warmed (None if skipped).
        row_count: Number of rows in the warmed DataFrame.
        duration_ms: Time taken to warm in milliseconds.
        error: Error message if warming failed.

    Example:
        >>> status = WarmStatus(
        ...     entity_type="unit",
        ...     result=WarmResult.SUCCESS,
        ...     project_gid="1234567890",
        ...     row_count=5000,
        ...     duration_ms=2500.0,
        ... )
    """

    entity_type: str
    result: WarmResult
    project_gid: str | None = None
    row_count: int = 0
    duration_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all fields suitable for JSON.
        """
        return {
            "entity_type": self.entity_type,
            "result": self.result.value,
            "project_gid": self.project_gid,
            "row_count": self.row_count,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class CacheWarmer:
    """Pre-deployment cache warmer for Lambda.

    Per TDD-DATAFRAME-CACHE-001 Section 5.7:
    - Priority: Configurable order (default: offer, unit, business, contact)
    - All entity types must warm successfully in strict mode (no partial)
    - Lambda invocation only (not local CLI)

    The warmer builds DataFrames for each entity type and stores them
    in the cache via put_async(). It uses the resolution strategies'
    _build_dataframe methods to construct DataFrames.

    Attributes:
        cache: DataFrameCache to warm.
        priority: Entity type warm order (processed sequentially).
        strict: If True, fail on any warm failure (default True).

    Example:
        >>> from autom8_asana.cache.dataframe.factory import get_dataframe_cache
        >>> from autom8_asana.cache.dataframe.warmer import CacheWarmer
        >>>
        >>> warmer = CacheWarmer(cache=get_dataframe_cache())
        >>>
        >>> # Warm all entity types in priority order
        >>> results = await warmer.warm_all_async(
        ...     client=client,
        ...     project_gid_provider=lambda et: registry.get_project_gid(et),
        ... )
        >>>
        >>> if all(r.result == WarmResult.SUCCESS for r in results):
        ...     print("Cache warm complete")
    """

    cache: "DataFrameCache"
    priority: list[str] = field(
        default_factory=lambda: ["offer", "unit", "business", "contact"]
    )
    strict: bool = True

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize warmer statistics."""
        self._stats = {
            "warm_attempts": 0,
            "warm_successes": 0,
            "warm_failures": 0,
            "warm_skipped": 0,
            "total_rows_warmed": 0,
        }

    async def warm_all_async(
        self,
        client: "AsanaClient",
        project_gid_provider: Callable[[str], str | None],
    ) -> list[WarmStatus]:
        """Warm all entity types in priority order.

        Iterates through entity types in priority order, building and
        caching DataFrames for each. Uses the resolution strategies'
        _build_dataframe methods for construction.

        Args:
            client: AsanaClient for building DataFrames.
            project_gid_provider: Function to get project GID for entity type.
                Takes entity_type string, returns project_gid or None.

        Returns:
            List of WarmStatus for each entity type in priority order.

        Raises:
            RuntimeError: If strict mode and any warm fails.

        Example:
            >>> async def get_project_gid(entity_type: str) -> str | None:
            ...     return registry.get_project_gid(entity_type)
            >>>
            >>> results = await warmer.warm_all_async(client, get_project_gid)
            >>> for result in results:
            ...     print(f"{result.entity_type}: {result.result.value}")
        """
        results: list[WarmStatus] = []
        total_start = time.monotonic()

        logger.info(
            "cache_warm_starting",
            extra={
                "priority": self.priority,
                "strict": self.strict,
            },
        )

        for entity_type in self.priority:
            self._stats["warm_attempts"] += 1
            start = time.monotonic()

            project_gid = project_gid_provider(entity_type)

            if project_gid is None:
                status = WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.SKIPPED,
                    error="No project GID configured",
                )
                results.append(status)
                self._stats["warm_skipped"] += 1

                logger.warning(
                    "cache_warm_skipped",
                    extra={
                        "entity_type": entity_type,
                        "reason": "no_project_gid",
                    },
                )
                continue

            try:
                status = await self._warm_entity_type_async(
                    entity_type=entity_type,
                    project_gid=project_gid,
                    client=client,
                )

                elapsed_ms = (time.monotonic() - start) * 1000
                status.duration_ms = elapsed_ms

                results.append(status)

                if status.result == WarmResult.SUCCESS:
                    self._stats["warm_successes"] += 1
                    self._stats["total_rows_warmed"] += status.row_count
                else:
                    self._stats["warm_failures"] += 1

                    if self.strict:
                        raise RuntimeError(
                            f"Cache warm failed for {entity_type}: {status.error}"
                        )

            except RuntimeError:
                # Re-raise RuntimeError from strict mode
                raise

            except Exception as e:
                self._stats["warm_failures"] += 1
                elapsed_ms = (time.monotonic() - start) * 1000

                status = WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.FAILURE,
                    project_gid=project_gid,
                    duration_ms=elapsed_ms,
                    error=str(e),
                )
                results.append(status)

                logger.error(
                    "cache_warm_error",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                if self.strict:
                    raise RuntimeError(
                        f"Cache warm failed for {entity_type}: {e}"
                    ) from e

        # Log summary
        total_elapsed = (time.monotonic() - total_start) * 1000
        success_count = sum(1 for r in results if r.result == WarmResult.SUCCESS)
        failure_count = sum(1 for r in results if r.result == WarmResult.FAILURE)
        skipped_count = sum(1 for r in results if r.result == WarmResult.SKIPPED)

        logger.info(
            "cache_warm_complete",
            extra={
                "total": len(results),
                "success": success_count,
                "failure": failure_count,
                "skipped": skipped_count,
                "total_rows": self._stats["total_rows_warmed"],
                "total_duration_ms": total_elapsed,
            },
        )

        return results

    async def _warm_entity_type_async(
        self,
        entity_type: str,
        project_gid: str,
        client: "AsanaClient",
    ) -> WarmStatus:
        """Warm a single entity type.

        Builds the DataFrame using the appropriate resolution strategy's
        build method and stores it in the cache.

        Args:
            entity_type: Entity type to warm (e.g., "unit", "offer").
            project_gid: Project GID for entity type.
            client: AsanaClient for building.

        Returns:
            WarmStatus indicating result.
        """
        logger.info(
            "cache_warm_start",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )

        try:
            # Get the resolution strategy for this entity type
            strategy = self._get_strategy_instance(entity_type)

            if strategy is None:
                return WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.FAILURE,
                    project_gid=project_gid,
                    error=f"No resolution strategy registered for {entity_type}",
                )

            # Get the build method from the strategy
            build_method = getattr(strategy, "_build_dataframe", None)

            if build_method is None:
                return WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.FAILURE,
                    project_gid=project_gid,
                    error=f"Strategy for {entity_type} has no _build_dataframe method",
                )

            # Build DataFrame
            df, watermark = await build_method(project_gid, client)

            if df is None:
                return WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.FAILURE,
                    project_gid=project_gid,
                    error="DataFrame build returned None",
                )

            # Store in cache
            await self.cache.put_async(
                project_gid=project_gid,
                entity_type=entity_type,
                dataframe=df,
                watermark=watermark,
            )

            row_count = len(df)

            logger.info(
                "cache_warm_success",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                    "row_count": row_count,
                    "watermark": watermark.isoformat(),
                },
            )

            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SUCCESS,
                project_gid=project_gid,
                row_count=row_count,
            )

        except Exception as e:
            logger.error(
                "cache_warm_entity_failed",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.FAILURE,
                project_gid=project_gid,
                error=str(e),
            )

    def _get_strategy_instance(self, entity_type: str) -> Any:
        """Get resolution strategy instance for entity type.

        Creates a UniversalResolutionStrategy for the given entity type.

        Args:
            entity_type: Entity type (e.g., "unit", "offer", "contact").

        Returns:
            Strategy instance or None if not found.
        """
        # Import here to avoid circular imports
        from autom8_asana.services.resolver import get_strategy

        return get_strategy(entity_type)

    async def warm_entity_async(
        self,
        entity_type: str,
        client: "AsanaClient",
        project_gid_provider: Callable[[str], str | None],
    ) -> WarmStatus:
        """Warm a single entity type.

        Convenience method for warming a single entity type without
        going through the full priority list.

        Args:
            entity_type: Entity type to warm.
            client: AsanaClient for building.
            project_gid_provider: Function to get project GID.

        Returns:
            WarmStatus for the entity type.

        Example:
            >>> status = await warmer.warm_entity_async(
            ...     "unit",
            ...     client,
            ...     lambda et: registry.get_project_gid(et),
            ... )
        """
        start = time.monotonic()
        self._stats["warm_attempts"] += 1

        project_gid = project_gid_provider(entity_type)

        if project_gid is None:
            self._stats["warm_skipped"] += 1
            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SKIPPED,
                error="No project GID configured",
            )

        try:
            status = await self._warm_entity_type_async(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
            )

            elapsed_ms = (time.monotonic() - start) * 1000
            status.duration_ms = elapsed_ms

            if status.result == WarmResult.SUCCESS:
                self._stats["warm_successes"] += 1
                self._stats["total_rows_warmed"] += status.row_count
            else:
                self._stats["warm_failures"] += 1

            return status

        except Exception as e:
            self._stats["warm_failures"] += 1
            elapsed_ms = (time.monotonic() - start) * 1000

            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.FAILURE,
                project_gid=project_gid,
                duration_ms=elapsed_ms,
                error=str(e),
            )

    def get_stats(self) -> dict[str, int]:
        """Get warmer statistics.

        Returns:
            Dictionary with warming statistics.
        """
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        for key in self._stats:
            self._stats[key] = 0
