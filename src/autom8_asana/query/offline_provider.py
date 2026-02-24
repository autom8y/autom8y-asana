"""Offline DataFrameProvider backed by S3 parquet files.

Bridges the sync load_project_dataframe() to the async DataFrameProvider
protocol. Caches loaded DataFrames in-process to avoid re-reading S3 for
join targets.

Per ADR-AQ-001: Direct async wrapper (no asyncio.to_thread) is acceptable
because the CLI is single-threaded via asyncio.run().

Per ADR-AQ-002: NullClient sentinel raises on any access, catching
accidental live API calls in offline mode.

Per ADR-AQ-003: OfflineProjectRegistry wraps EntityRegistry for offline
join resolution without the running service stack.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo
    from autom8_asana.client import AsanaClient


class NullClient:
    """Sentinel AsanaClient for offline mode.

    Raises RuntimeError on any method call, catching accidental
    live API access in offline paths. Cleaner than passing None
    with type: ignore scattered through call sites.
    """

    def __getattr__(self, name: str) -> NoReturn:
        raise RuntimeError(
            f"NullClient: attempted to call '{name}' in offline mode. "
            "Offline queries use S3 parquets and should never invoke the Asana API."
        )


class OfflineProjectRegistry:
    """Adapter providing get_project_gid() for offline join resolution.

    Wraps EntityRegistry, which carries primary_project_gid on each
    EntityDescriptor. This is the same data used at runtime by
    EntityProjectRegistry (services/resolver.py), but without requiring
    the running service stack or workspace discovery.

    Duck-types to the same interface expected by QueryEngine.execute_rows()
    entity_project_registry parameter.
    """

    def get_project_gid(self, entity_type: str) -> str | None:
        """Resolve entity type to primary project GID via EntityRegistry."""
        from autom8_asana.core.entity_registry import get_registry

        desc = get_registry().get(entity_type)
        return desc.primary_project_gid if desc else None


class OfflineDataFrameProvider:
    """DataFrameProvider backed by S3 parquet files.

    Bridges the sync load_project_dataframe() to the async
    DataFrameProvider protocol. Caches loaded DataFrames in-process
    to avoid re-reading S3 for join targets.

    Thread Safety:
        Single-threaded CLI context only. No lock needed.
    """

    def __init__(self, *, bucket: str | None = None, region: str = "us-east-1") -> None:
        self._bucket = bucket or os.environ.get("ASANA_CACHE_S3_BUCKET")
        self._region = region
        self._cache: dict[str, pl.DataFrame] = {}
        self._last_freshness: FreshnessInfo | None = None

    @property
    def last_freshness_info(self) -> FreshnessInfo | None:
        """Freshness metadata from the most recent get_dataframe() call.

        Returns None if no call has been made yet.
        """
        return self._last_freshness

    async def get_dataframe(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
    ) -> pl.DataFrame:
        """Load DataFrame from S3 parquets, with in-process caching.

        The client parameter is ignored (offline mode).

        Args:
            entity_type: Entity type to query.
            project_gid: Project GID for S3 key lookup.
            client: Ignored in offline mode (accepts NullClient).

        Returns:
            Polars DataFrame loaded from S3 parquets.

        Raises:
            ValueError: If no S3 bucket is configured.
            FileNotFoundError: If no parquets exist for the project.
        """
        if project_gid in self._cache:
            return self._cache[project_gid]

        from autom8_asana.dataframes.offline import load_project_dataframe_with_meta

        # Sync call in async wrapper -- acceptable for single-threaded CLI
        start = time.monotonic()
        df, last_modified = load_project_dataframe_with_meta(
            project_gid,
            bucket=self._bucket,
            region=self._region,
        )
        elapsed = time.monotonic() - start

        self._cache[project_gid] = df
        self._last_freshness = _build_offline_freshness(elapsed, last_modified)
        return df


def _build_offline_freshness(
    load_seconds: float,
    last_modified: datetime | None = None,
) -> FreshnessInfo:
    """Build FreshnessInfo for offline S3 data.

    When S3 LastModified metadata is available, computes real data age
    as the delta between now and the most recent object modification.
    Otherwise falls back to load duration as a proxy.
    """
    from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo

    if last_modified is not None:
        age = (datetime.now(UTC) - last_modified).total_seconds()
        return FreshnessInfo(
            freshness="s3_offline",
            data_age_seconds=age,
            staleness_ratio=0.0,
        )

    return FreshnessInfo(
        freshness="s3_offline",
        data_age_seconds=load_seconds,
        staleness_ratio=0.0,  # Not applicable for offline
    )
