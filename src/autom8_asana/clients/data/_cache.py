"""Cache operations for DataServiceClient.

Private module extracted from client.py to separate cache concerns from
the main client class. Functions are module-level to enable independent
testing and reduce class surface area.

These functions are NOT part of the public API -- they are imported and
used by DataServiceClient internally.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8_asana.clients.data._pii import mask_pii_in_string as _mask_pii_in_string
from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsResponse,
)
from autom8_asana.core.exceptions import CacheError

if TYPE_CHECKING:
    from autom8_asana.models.contracts import PhoneVerticalPair
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider


def build_cache_key(factory: str, pvp: PhoneVerticalPair) -> str:
    """Build cache key for insights response.

    Cache key format is insights:{factory}:{canonical_key}.

    Args:
        factory: Normalized factory name (e.g., "account").
        pvp: PhoneVerticalPair with canonical_key property.

    Returns:
        Cache key string (e.g., "insights:account:pv1:+17705753103:chiropractic").
    """
    return f"insights:{factory}:{pvp.canonical_key}"


def cache_response(
    cache: CacheProvider | None,
    cache_key: str,
    response: InsightsResponse,
    ttl: int,
    log: LogProvider | Any | None,
) -> None:
    """Cache successful insights response.

    Stores response in cache with configured TTL.
    Cache failures are logged but don't break requests (graceful degradation).

    Args:
        cache: Cache provider instance (None = caching disabled).
        cache_key: Pre-built cache key.
        response: Successful InsightsResponse to cache.
        ttl: Cache TTL in seconds.
        log: Logger instance for structured logging.
    """
    if cache is None:
        return

    try:
        # Serialize response to dict for caching
        cached_data = {
            "data": response.data,
            "metadata": response.metadata.model_dump(mode="json"),
            "request_id": response.request_id,
            "warnings": response.warnings,
            "cached_at": datetime.now(UTC).isoformat(),
        }

        # Use simple set method for cache storage
        cache.set(cache_key, cached_data, ttl=ttl)

        if log:
            log.debug(
                f"DataServiceClient: Cached response for {_mask_pii_in_string(cache_key)}",
                extra={"cache_key": _mask_pii_in_string(cache_key), "ttl": ttl},
            )
    except (
        ConnectionError,
        TimeoutError,
        OSError,
        ValueError,
        TypeError,
        CacheError,
    ) as e:
        # Graceful degradation: cache failures don't break requests
        if log:
            log.warning(
                f"DataServiceClient: Failed to cache response: {e}",
                extra={"cache_key": _mask_pii_in_string(cache_key)},
            )


def get_stale_response(
    cache: CacheProvider | None,
    cache_key: str,
    request_id: str,
    log: LogProvider | Any | None,
) -> InsightsResponse | None:
    """Retrieve stale response from cache for fallback.

    On service failure, returns stale cache entry
    with is_stale=True and cached_at populated.

    Args:
        cache: Cache provider instance (None = caching disabled).
        cache_key: Pre-built cache key.
        request_id: Request ID for the response.
        log: Logger instance for structured logging.

    Returns:
        InsightsResponse with is_stale=True if found, None otherwise.
    """
    if cache is None:
        return None

    try:
        cached_data = cache.get(cache_key)
        if cached_data is None:
            return None

        # Reconstruct InsightsResponse from cached data
        metadata_dict = cached_data.get("metadata", {})

        # Parse cached_at timestamp
        cached_at_str = cached_data.get("cached_at")
        cached_at = None
        if cached_at_str:
            try:
                cached_at = datetime.fromisoformat(cached_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                cached_at = datetime.now(UTC)

        # Rebuild column info
        columns = [ColumnInfo(**col) for col in metadata_dict.get("columns", [])]

        # Create metadata with staleness indicators
        metadata = InsightsMetadata(
            factory=metadata_dict.get("factory", "unknown"),
            frame_type=metadata_dict.get("frame_type"),
            insights_period=metadata_dict.get("insights_period"),
            row_count=metadata_dict.get("row_count", 0),
            column_count=metadata_dict.get("column_count", 0),
            columns=columns,
            cache_hit=metadata_dict.get("cache_hit", False),
            duration_ms=metadata_dict.get("duration_ms", 0.0),
            sort_history=metadata_dict.get("sort_history"),
            is_stale=True,  # Mark as stale
            cached_at=cached_at,  # Populate cached_at
        )

        stale_response = InsightsResponse(
            data=cached_data.get("data", []),
            metadata=metadata,
            request_id=request_id,
            warnings=cached_data.get("warnings", [])
            + ["Response served from stale cache due to service unavailability"],
        )

        if log:
            log.info(
                f"DataServiceClient: Returning stale cache fallback for {_mask_pii_in_string(cache_key)}",
                extra={
                    "cache_key": _mask_pii_in_string(cache_key),
                    "cached_at": cached_at_str,
                    "row_count": metadata.row_count,
                },
            )

        return stale_response

    except (
        ConnectionError,
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        CacheError,
    ) as e:
        # Graceful degradation: cache read failures return None
        if log:
            log.warning(
                f"DataServiceClient: Failed to retrieve stale response: {e}",
                extra={"cache_key": _mask_pii_in_string(cache_key)},
            )
        return None
