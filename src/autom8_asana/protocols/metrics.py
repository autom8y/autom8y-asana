"""Metrics emitter protocol for cache observability.

Decouples the cache layer (DataFrameCache) from the API layer (api/metrics.py).
DataFrameCache accepts any MetricsEmitter instead of importing Prometheus
helpers directly, eliminating Cycle 5 (cache -> api).
"""

from __future__ import annotations

from typing import Protocol


class MetricsEmitter(Protocol):
    """Protocol for emitting cache operation metrics.

    Any object that implements these three methods satisfies the protocol
    via structural typing. PrometheusMetricsEmitter (in api/metrics.py)
    is the primary implementation.

    Example:
        cache = DataFrameCache(
            ...,
            metrics_emitter=PrometheusMetricsEmitter(),
        )
    """

    def record_cache_op(self, entity_type: str, tier: str, result: str) -> None:
        """Record a cache operation (hit/miss/error).

        Args:
            entity_type: Entity type (e.g., "unit", "offer").
            tier: Cache tier ("memory" or "s3").
            result: Operation result ("hit", "miss", or "error").
        """
        ...

    def record_rows_cached(self, entity_type: str, row_count: int) -> None:
        """Update the rows-cached gauge for an entity type.

        Args:
            entity_type: Entity type (e.g., "unit", "offer").
            row_count: Number of rows in the cached DataFrame.
        """
        ...

    def record_swr_refresh(self, entity_type: str, result: str) -> None:
        """Record an SWR refresh attempt.

        Args:
            entity_type: Entity type (e.g., "unit", "offer").
            result: Refresh result ("success" or "failure").
        """
        ...
