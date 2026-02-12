"""Base class for cache backends with shared scaffolding.

Per refactoring plan RF-008: Extracts the common resilience scaffolding
(degraded mode check, timing, metrics recording, transport error handling)
from S3CacheProvider and RedisCacheProvider into a template method base class.

Resolves SM-002 (boundary violation), SM-007 (freshness stamp duplication),
and SM-008 (init boilerplate duplication).
"""

from __future__ import annotations

import abc
import time
from datetime import datetime
from typing import Any

from autom8y_log import get_logger

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.errors import DegradedModeMixin
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.models.metrics import CacheMetrics
from autom8_asana.cache.models.settings import CacheSettings
from autom8_asana.cache.models.versioning import format_version, parse_version
from autom8_asana.protocols.cache import WarmResult

logger = get_logger(__name__)


class CacheBackendBase(DegradedModeMixin, abc.ABC):
    """Base class for cache backends providing shared resilience scaffolding.

    Template method pattern: The simple protocol operations (get, set, delete,
    get_versioned, set_versioned) are implemented here with shared scaffolding
    (timing, degraded check, metrics, error handling) that delegates to abstract
    ``_do_*`` methods for the backend-specific work.

    Complex protocol operations (get_batch, set_batch, warm, check_freshness,
    invalidate, is_healthy, clear_all_tasks) are left as abstract methods for
    backends to implement directly, since their scaffolding patterns diverge
    between S3 and Redis.

    Subclasses must:
    - Set ``_transport_errors`` class attribute to the backend's transport error tuple
    - Implement all ``_do_*`` abstract methods (for template methods)
    - Implement all remaining abstract protocol methods
    - Implement ``_handle_transport_error`` for backend-specific error handling
    - Call ``super().__init__(settings=settings)`` after backend-specific init

    Thread Safety:
        Shared attributes (_degraded, _metrics, _settings) are safe for concurrent
        reads. Writes to _degraded are idempotent. Subclasses manage their own
        connection/client thread safety.
    """

    # Subclasses MUST set this to the appropriate error tuple
    # e.g., S3_TRANSPORT_ERRORS or REDIS_TRANSPORT_ERRORS
    _transport_errors: tuple[type[Exception], ...] = ()

    def __init__(
        self,
        settings: CacheSettings | None = None,
    ) -> None:
        """Initialize shared backend state.

        Args:
            settings: Cache settings for TTL and overflow thresholds.
        """
        self._settings = settings or CacheSettings()
        self._metrics = CacheMetrics()
        self._degraded = False
        self._last_reconnect_attempt = 0.0
        self._reconnect_interval = float(self._settings.reconnect_interval)

    # --- Freshness Stamp Serialization (SM-007 fix) ---

    @staticmethod
    def _serialize_freshness_stamp(
        stamp: Any,
    ) -> dict[str, Any] | None:
        """Serialize a FreshnessStamp to a dict for storage.

        Shared between S3 and Redis backends. The dict format is identical;
        only the storage mechanism differs (S3 object metadata vs Redis hash).

        Args:
            stamp: FreshnessStamp instance, or None.

        Returns:
            Dict with last_verified_at, source, staleness_hint; or None.
        """
        if stamp is None:
            return None
        return {
            "last_verified_at": format_version(stamp.last_verified_at),
            "source": stamp.source.value,
            "staleness_hint": stamp.staleness_hint,
        }

    @staticmethod
    def _deserialize_freshness_stamp(raw: dict[str, Any] | None) -> Any:
        """Deserialize a freshness stamp dict back to FreshnessStamp.

        Args:
            raw: Dict from storage, or None.

        Returns:
            FreshnessStamp instance, or None.
        """
        if not raw:
            return None
        from autom8_asana.cache.models.freshness_stamp import (
            FreshnessStamp,
            VerificationSource,
        )

        return FreshnessStamp(
            last_verified_at=parse_version(raw["last_verified_at"]),
            source=VerificationSource(raw.get("source", "unknown")),
            staleness_hint=raw.get("staleness_hint"),
        )

    # --- Template Methods: Simple Protocol Operations ---
    # These have identical scaffolding in both S3 and Redis backends.

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve value from cache (simple key-value).

        Args:
            key: Cache key.

        Returns:
            Cached dict if found, None if miss.
        """
        start = time.perf_counter()
        try:
            if self._degraded:
                self._metrics.record_miss(0.0, key=key)
                return None

            result = self._do_get(key)
            latency = (time.perf_counter() - start) * 1000

            if result is None:
                self._metrics.record_miss(latency, key=key)
            else:
                self._metrics.record_hit(latency, key=key)
            return result

        except self._transport_errors as e:
            latency = (time.perf_counter() - start) * 1000
            if self._is_not_found_error(e):
                self._metrics.record_miss(latency, key=key)
                return None
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_transport_error(e, operation="get", key=key)
            return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in cache (simple key-value).

        Args:
            key: Cache key.
            value: Dict to cache.
            ttl: Time-to-live in seconds.
        """
        start = time.perf_counter()
        try:
            if self._degraded:
                return

            self._do_set(key, value, ttl)
            latency = (time.perf_counter() - start) * 1000
            self._metrics.record_write(latency, key=key)

        except self._transport_errors as e:
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_transport_error(e, operation="set", key=key)

    def delete(self, key: str) -> None:
        """Remove value from cache.

        Args:
            key: Cache key to delete.
        """
        try:
            if self._degraded:
                return

            self._do_delete(key)
            self._metrics.record_eviction(key=key)

        except self._transport_errors as e:
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_transport_error(e, operation="delete", key=key)

    def set_versioned(
        self,
        key: str,
        entry: CacheEntry,
    ) -> None:
        """Store versioned cache entry.

        Args:
            key: Cache key.
            entry: CacheEntry with data and metadata.
        """
        start = time.perf_counter()
        entry_type_str = entry.entry_type.value

        try:
            if self._degraded:
                return

            self._do_set_versioned(key, entry)
            latency = (time.perf_counter() - start) * 1000
            self._metrics.record_write(latency, key=key, entry_type=entry_type_str)

        except self._transport_errors as e:
            self._metrics.record_error(
                key=key, entry_type=entry_type_str, error_message=str(e)
            )
            self._handle_transport_error(e, operation="set_versioned", key=key)

    # --- Shared Utility Methods ---

    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics aggregator.

        Returns:
            CacheMetrics instance with hit/miss statistics.
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset cache metrics to zero."""
        self._metrics.reset()

    def _is_not_found_error(self, error: Exception) -> bool:
        """Check if error indicates a cache miss (not found).

        Override in backends that have distinct not-found errors (e.g., S3).
        Default returns False (treat all errors as real errors).

        Args:
            error: The exception to classify.

        Returns:
            True if error means the entry was not found.
        """
        return False

    # --- Abstract Methods: Template Method Hooks ---

    @abc.abstractmethod
    def _do_get(self, key: str) -> dict[str, Any] | None:
        """Backend-specific get operation (simple key-value).

        Returns:
            Cached dict if found, None if miss.
        """

    @abc.abstractmethod
    def _do_set(self, key: str, value: dict[str, Any], ttl: int | None) -> None:
        """Backend-specific set operation (simple key-value)."""

    @abc.abstractmethod
    def _do_delete(self, key: str) -> None:
        """Backend-specific delete operation."""

    @abc.abstractmethod
    def _do_set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Backend-specific versioned set operation."""

    @abc.abstractmethod
    def _handle_transport_error(
        self, error: Exception, *, operation: str = "unknown", key: str | None = None
    ) -> None:
        """Handle a transport error with backend-specific logic.

        Should wrap vendor exceptions into domain errors, classify connection
        errors, and call enter_degraded_mode() as appropriate.

        Args:
            error: The transport exception.
            operation: Name of the operation that failed.
            key: The cache key involved, if applicable.
        """

    # --- Abstract Methods: Complex Protocol Operations ---
    # These have divergent scaffolding patterns between backends
    # and are implemented directly by subclasses.

    @abc.abstractmethod
    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness | None = None,
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry with freshness control.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry for version resolution.
            freshness: STRICT validates version, EVENTUAL returns without check.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """

    @abc.abstractmethod
    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries in single operation.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries to retrieve.

        Returns:
            Dict mapping keys to CacheEntry or None if not found.
        """

    @abc.abstractmethod
    def set_batch(
        self,
        entries: dict[str, CacheEntry],
    ) -> None:
        """Store multiple entries in single operation.

        Args:
            entries: Dict mapping keys to CacheEntry objects.
        """

    @abc.abstractmethod
    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Pre-populate cache for specified GIDs and entry types.

        Args:
            gids: List of task GIDs to warm.
            entry_types: Entry types to fetch and cache.

        Returns:
            WarmResult with success/failure counts.
        """

    @abc.abstractmethod
    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if cached version matches current version.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            current_version: Known current modified_at timestamp.

        Returns:
            True if cache is fresh, False if stale or missing.
        """

    @abc.abstractmethod
    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries for a key.

        Args:
            key: Cache key (task GID).
            entry_types: Specific types to invalidate. If None, all types.
        """

    @abc.abstractmethod
    def is_healthy(self) -> bool:
        """Check if cache backend is operational.

        Returns:
            True if backend is healthy and responding.
        """

    @abc.abstractmethod
    def clear_all_tasks(self) -> int:
        """Clear all task entries from cache.

        Returns:
            Number of entries deleted.
        """
