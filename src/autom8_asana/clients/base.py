"""Base client class for all resource clients.

Per TDD-CACHE-INTEGRATION Section 4.4: Includes cache helper methods.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.errors import CACHE_TRANSIENT_ERRORS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from autom8_asana.cache.models.entry import CacheEntry, EntryType
    from autom8_asana.config import AsanaConfig
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider
    from autom8_asana.transport.asana_http import AsanaHttpClient

logger = get_logger(__name__)


class BaseClient:
    """Base class for resource-specific clients.

    Provides common functionality:
    - Access to HTTP transport
    - Access to providers (auth, cache, log)
    - Request building helpers
    - Response parsing helpers
    - Cache helpers for check-before-HTTP, store-on-miss pattern
    """

    def __init__(
        self,
        http: AsanaHttpClient,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
    ) -> None:
        """Initialize base client.

        Args:
            http: HTTP client for making requests
            config: SDK configuration
            auth_provider: Authentication provider
            cache_provider: Optional cache provider
            log_provider: Optional log provider
        """
        self._http = http
        self._config = config
        self._auth = auth_provider
        self._cache = cache_provider
        self._log = log_provider

    def _build_opt_fields(self, opt_fields: list[str] | None) -> dict[str, Any]:
        """Build opt_fields query parameter.

        Args:
            opt_fields: List of field names to include

        Returns:
            Query params dict with opt_fields formatted for Asana API
        """
        if not opt_fields:
            return {}
        return {"opt_fields": ",".join(opt_fields)}

    def _log_operation(self, operation: str, resource_gid: str | None = None) -> None:
        """Log an operation if logger is available."""
        if self._log:
            if resource_gid:
                self._log.debug(f"{self.__class__.__name__}.{operation}({resource_gid})")
            else:
                self._log.debug(f"{self.__class__.__name__}.{operation}()")

    # --- Cache Helper Methods (per TDD-CACHE-INTEGRATION Section 4.4) ---

    def _cache_get(
        self,
        key: str,
        entry_type: EntryType,
    ) -> CacheEntry | None:
        """Check cache for an entry (graceful degradation).

        Per NFR-DEGRADE-001: Cache failures log warnings without raising.
        Per ADR-0127: Graceful degradation pattern.

        Args:
            key: Cache key (typically task GID).
            entry_type: Type of cache entry.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        if self._cache is None:
            return None

        try:
            entry = self._cache.get_versioned(key, entry_type)
            if entry is not None and not entry.is_expired():
                logger.debug(
                    "cache_hit",
                    entry_type=entry_type.value,
                    key=key,
                )
                return entry
            return None
        except CACHE_TRANSIENT_ERRORS as exc:
            # NFR-DEGRADE-001: Log and continue
            logger.warning(
                "cache_get_failed",
                entry_type=entry_type.value,
                key=key,
                error=str(exc),
            )
            return None

    def _cache_get_covering(
        self,
        key: str,
        entry_type: EntryType,
        requested_opt_fields: Sequence[str],
    ) -> tuple[CacheEntry | None, CacheEntry | None]:
        """Check cache for an entry COVERING the requested projection (PHE).

        Per ADR-taskcache-projection-coverage-2026-07-08: wraps ``_cache_get``
        and gates the hit on ``projection_covers``. When an entry exists but
        does NOT cover the requested projection, returns a miss (None) plus a
        structured ``cache_coverage_miss`` log, so callers' existing miss
        paths fire unchanged; the stale entry is exposed as the second tuple
        element so the caller's re-hydration union can include the stored
        projection (the anti-thrash term).

        An EMPTY requested projection declares no field demand and is served
        by any live entry (a KNOWN entry trivially covers the empty set; an
        UNKNOWN entry cannot starve a demand that was never declared -- gating
        it would degrade default-projection readers to permanent re-fetch).

        Args:
            key: Cache key (typically entity GID).
            entry_type: Type of cache entry.
            requested_opt_fields: The RESOLVED requested projection.

        Returns:
            Tuple of (covered_entry, existing_entry):
            - (entry, entry) on a covering hit,
            - (None, entry) on a coverage-miss (entry exists, not covering),
            - (None, None) when no live entry exists.
        """
        entry = self._cache_get(key, entry_type)
        if entry is None:
            return None, None
        if not requested_opt_fields:
            return entry, entry

        from autom8_asana.cache.models.coverage import projection_covers, stored_projection

        if projection_covers(entry, requested_opt_fields):
            return entry, entry

        stored = stored_projection(entry)
        # The amplification tripwire (TDD SS2.4): every coverage-miss is loud.
        logger.info(
            "cache_coverage_miss",
            gid=key,
            entry_type=entry_type.value,
            missing_fields=sorted(set(requested_opt_fields) - (stored or frozenset())),
            stored_count=len(stored) if stored is not None else 0,
        )
        return None, entry

    def _cache_set(
        self,
        key: str,
        data: dict[str, Any],
        entry_type: EntryType,
        ttl: int | None = None,
        opt_fields: Sequence[str] | None = None,
    ) -> None:
        """Store data in cache (graceful degradation).

        Per NFR-DEGRADE-004: Operation succeeds even if caching fails.
        Per ADR-0127: Graceful degradation pattern.

        Args:
            key: Cache key (typically task GID).
            data: Data to cache (typically API response dict).
            entry_type: Type of cache entry.
            ttl: Time-to-live in seconds. If None, uses default from config.
            opt_fields: The projection this data was hydrated at (PHE). When
                provided, stamps ``opt_fields_used`` + ``completeness_level``
                entry metadata (the ``create_completeness_metadata`` keys) so
                the coverage predicate can gate later hits. None = UNKNOWN
                (entry coverage-misses once and heals).
        """
        if self._cache is None:
            return

        try:
            from autom8_asana.cache.models.entry import CacheEntry

            # Extract version from modified_at if present
            modified_at = data.get("modified_at")
            version = self._parse_modified_at(modified_at) if modified_at else datetime.now(UTC)

            # Resolve TTL from config if not provided
            if ttl is None:
                ttl = self._config.cache.ttl.default_ttl

            # PHE: persist the hydration projection as entry metadata (the
            # authority slot -- survives _extend_ttl's metadata spread).
            metadata: dict[str, Any] = {}
            if opt_fields is not None:
                from autom8_asana.cache.models.completeness import (
                    create_completeness_metadata,
                )

                metadata = create_completeness_metadata(sorted(set(opt_fields)))

            entry = CacheEntry(
                key=key,
                data=data,
                entry_type=entry_type,
                version=version,
                ttl=ttl,
                metadata=metadata,
            )
            self._cache.set_versioned(key, entry)

            logger.debug(
                "cache_set",
                entry_type=entry_type.value,
                key=key,
                ttl=ttl,
            )
        except CACHE_TRANSIENT_ERRORS as exc:
            # NFR-DEGRADE-004: Log and continue
            logger.warning(
                "cache_set_failed",
                entry_type=entry_type.value,
                key=key,
                error=str(exc),
            )

    def _cache_invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries for a key (graceful degradation).

        Per ADR-0127: Graceful degradation pattern.

        Args:
            key: Cache key to invalidate (typically task GID).
            entry_types: Entry types to invalidate. None = all types.
        """
        if self._cache is None:
            return

        try:
            self._cache.invalidate(key, entry_types)
            logger.debug(
                "cache_invalidated",
                key=key,
                types=[t.value for t in entry_types] if entry_types else "all",
            )
        except CACHE_TRANSIENT_ERRORS as exc:
            logger.warning(
                "cache_invalidate_failed",
                key=key,
                error=str(exc),
            )

    @staticmethod
    def _parse_modified_at(value: str | datetime) -> datetime:
        """Parse modified_at to datetime.

        Args:
            value: ISO format string or datetime.

        Returns:
            Timezone-aware datetime (UTC).
        """
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value

        # Handle ISO format with Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
