"""Base client class for all resource clients.

Per TDD-CACHE-INTEGRATION Section 4.4: Includes cache helper methods.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

if TYPE_CHECKING:
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
                self._log.debug(
                    f"{self.__class__.__name__}.{operation}({resource_gid})"
                )
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

    def _cache_set(
        self,
        key: str,
        data: dict[str, Any],
        entry_type: EntryType,
        ttl: int | None = None,
    ) -> None:
        """Store data in cache (graceful degradation).

        Per NFR-DEGRADE-004: Operation succeeds even if caching fails.
        Per ADR-0127: Graceful degradation pattern.

        Args:
            key: Cache key (typically task GID).
            data: Data to cache (typically API response dict).
            entry_type: Type of cache entry.
            ttl: Time-to-live in seconds. If None, uses default from config.
        """
        if self._cache is None:
            return

        try:
            from autom8_asana.cache.models.entry import CacheEntry

            # Extract version from modified_at if present
            modified_at = data.get("modified_at")
            if modified_at:
                version = self._parse_modified_at(modified_at)
            else:
                version = datetime.now(UTC)

            # Resolve TTL from config if not provided
            if ttl is None:
                ttl = self._config.cache.ttl.default_ttl

            entry = CacheEntry(
                key=key,
                data=data,
                entry_type=entry_type,
                version=version,
                ttl=ttl,
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
