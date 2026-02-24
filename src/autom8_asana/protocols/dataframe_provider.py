"""DataFrameProvider protocol for query engine decoupling.

Abstracts DataFrame retrieval from the services layer, allowing the
query engine to operate against any provider implementation without
importing services.query_service or services.resolver.

Per R-010 (WS-QUERY): Inverts the dependency direction so the query
engine (computational) does not depend on the services layer (orchestration).

Reference pattern: EndpointPolicy in clients/data/_policy.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo
    from autom8_asana.client import AsanaClient


@runtime_checkable
class DataFrameProvider(Protocol):
    """Protocol for providing DataFrames to the query engine.

    Implementations must supply:
    - get_dataframe(): Async retrieval with full cache lifecycle
    - last_freshness_info: Side-channel freshness metadata from last call

    The canonical implementation is EntityQueryService, which delegates
    to UniversalResolutionStrategy for layered cache access + self-refresh.
    """

    @property
    def last_freshness_info(self) -> FreshnessInfo | None:
        """Freshness metadata from the most recent get_dataframe() call.

        Returns None if no call has been made yet or freshness info
        was not available.
        """
        ...

    async def get_dataframe(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
    ) -> pl.DataFrame:
        """Retrieve a DataFrame for the given entity type.

        Implementations should provide full cache lifecycle semantics:
        - Cache hit: Return immediately from memory/S3
        - Cache miss: Trigger build/refresh
        - Concurrent misses: Coalesce requests

        Args:
            entity_type: Entity type to query (e.g., "offer").
            project_gid: Project GID for cache key.
            client: AsanaClient for build operations if cache miss.

        Returns:
            Polars DataFrame with entity data.

        Raises:
            CacheNotWarmError: DataFrame unavailable after refresh attempt.
        """
        ...
