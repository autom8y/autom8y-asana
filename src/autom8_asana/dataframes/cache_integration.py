"""Cache integration for dataframe builders.

Per TDD-0008 Session 4 Phase 4: Provides cache integration layer for
structured dataframe extraction with async operations and schema versioning.

This module provides:
- CachedRow: Immutable dataclass representing a cached dataframe row
- DataFrameCacheIntegration: Class managing cache operations for dataframe entries

Design decisions per user requirements:
- Primary API is async (matches existing load_dataframe_cached)
- Sync wrappers use asyncio.run() for backward compatibility
- Schema version stored in CacheEntry.metadata["schema_version"]
- Staleness check: invalidate if schema version mismatch OR modified_at is newer
- Default freshness: EVENTUAL (no API validation)
- Error handling: try/except with logging, never propagate (FR-CACHE-008)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.integration.dataframes import make_dataframe_key
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.models.versioning import parse_version
from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider


# Module-level logger for cache events
_logger = get_logger(__name__)


@dataclass(frozen=True)
class CachedRow:
    """Immutable representation of a cached dataframe row.

    Per TDD-0008 Session 4 Phase 4: Represents the result of extracting
    a task into a dataframe row, with cache metadata for staleness detection.

    Attributes:
        task_gid: The GID of the task this row represents.
        project_gid: The project context for this row.
        data: The extracted row data (column name -> value mapping).
        schema_version: Version of schema used for extraction.
        cached_at: When this row was cached.
        version: The task's modified_at timestamp when cached.

    Example:
        >>> row = CachedRow(
        ...     task_gid="12345",
        ...     project_gid="proj1",
        ...     data={"gid": "12345", "name": "Task"},
        ...     schema_version="1.0.0",
        ...     cached_at=datetime.now(timezone.utc),
        ...     version=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ... )
        >>> row.cache_key
        '12345:proj1'
    """

    task_gid: str
    project_gid: str
    data: dict[str, Any]
    schema_version: str
    cached_at: datetime
    version: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cache_key(self) -> str:
        """Get the cache key for this row."""
        return make_dataframe_key(self.task_gid, self.project_gid)

    def is_schema_current(self, current_schema_version: str) -> bool:
        """Check if row was cached with current schema version.

        Args:
            current_schema_version: The current schema version to compare.

        Returns:
            True if schema versions match, False otherwise.
        """
        return self.schema_version == current_schema_version

    def is_version_current(self, current_modified_at: datetime | str) -> bool:
        """Check if row was cached with current task version.

        Args:
            current_modified_at: The task's current modified_at.

        Returns:
            True if cached version >= current, False if stale.
        """
        current = (
            parse_version(current_modified_at)
            if isinstance(current_modified_at, str)
            else current_modified_at
        )

        # Normalize timezones
        cached_version = self.version
        if cached_version.tzinfo is None:
            cached_version = cached_version.replace(tzinfo=UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)

        return cached_version >= current


class DataFrameCacheIntegration:
    """Cache integration for dataframe operations.

    Per TDD-0008 Session 4 Phase 4: Manages cache operations for dataframe entries
    with schema version tracking and staleness detection.

    This class coordinates between the dataframe builders and the cache layer,
    handling:
    - Reading cached dataframe rows with schema version validation
    - Writing extracted rows to cache with version metadata
    - Batch operations for efficient DataFrame construction
    - Warming cache for anticipated access patterns
    - Invalidation on schema or data version changes

    Attributes:
        cache: The cache provider for storage.
        logger: Optional log provider for cache events.
        default_ttl: Default TTL for cached entries.

    Example:
        >>> integration = DataFrameCacheIntegration(cache_provider)
        >>> row = await integration.get_cached_row_async(
        ...     task_gid="12345",
        ...     project_gid="proj1",
        ...     schema_version="1.0.0",
        ... )
        >>> if row is not None:
        ...     print("Cache hit!")
    """

    def __init__(
        self,
        cache: CacheProvider,
        logger: LogProvider | None = None,
        default_ttl: int = 300,
    ) -> None:
        """Initialize cache integration.

        Args:
            cache: Cache provider for storage operations.
            logger: Optional log provider for cache event logging.
            default_ttl: Default TTL in seconds for cached entries.
        """
        self._cache = cache
        self._logger = logger
        self._default_ttl = default_ttl

    @property
    def cache(self) -> CacheProvider:
        """Get the underlying cache provider."""
        return self._cache

    # =========================================================================
    # Async Methods (Primary API)
    # =========================================================================

    async def get_cached_row_async(
        self,
        task_gid: str,
        project_gid: str,
        schema_version: str,
        current_modified_at: datetime | str | None = None,
        freshness: FreshnessIntent = FreshnessIntent.EVENTUAL,
    ) -> CachedRow | None:
        """Retrieve a cached dataframe row if valid.

        Per FR-CACHE-001: Retrieves cached dataframe with schema version validation.
        Returns None if:
        - Entry not in cache
        - Schema version mismatch (invalidates and returns None)
        - Data version stale (if current_modified_at provided)
        - Cache operation fails (graceful degradation)

        Args:
            task_gid: The task GID.
            project_gid: The project context GID.
            schema_version: Current schema version for validation.
            current_modified_at: Optional task modified_at for staleness check.
            freshness: Cache freshness mode (default EVENTUAL).

        Returns:
            CachedRow if found and valid, None otherwise.
        """
        key = make_dataframe_key(task_gid, project_gid)

        try:
            entry = self._cache.get_versioned(key, EntryType.DATAFRAME, freshness)

            if entry is None:
                self._log_cache_event("miss", key, entry_type="dataframe")
                return None

            # Check schema version - invalidate on mismatch
            cached_schema = entry.metadata.get("schema_version")
            if cached_schema != schema_version:
                self._log_cache_event(
                    "evict",
                    key,
                    entry_type="dataframe",
                    metadata={
                        "reason": "schema_mismatch",
                        "cached": cached_schema,
                        "current": schema_version,
                    },
                )
                await self.invalidate_async(task_gid, project_gid)
                return None

            # Check data staleness if modified_at provided
            if current_modified_at is not None and not self._check_staleness(
                entry.version, current_modified_at
            ):
                self._log_cache_event(
                    "evict",
                    key,
                    entry_type="dataframe",
                    metadata={"reason": "data_stale"},
                )
                await self.invalidate_async(task_gid, project_gid)
                return None

            # Valid cache hit
            self._log_cache_event("hit", key, entry_type="dataframe")
            return CachedRow(
                task_gid=task_gid,
                project_gid=project_gid,
                data=entry.data,
                schema_version=cached_schema,
                cached_at=entry.cached_at,
                version=entry.version,
                metadata=entry.metadata,
            )

        except CACHE_TRANSIENT_ERRORS as exc:
            # FR-CACHE-008: Graceful degradation on cache errors
            self._log_cache_event(
                "error",
                key,
                entry_type="dataframe",
                metadata={"error": str(exc)},
            )
            return None

    async def get_cached_batch_async(
        self,
        task_project_pairs: list[tuple[str, str]],
        schema_version: str,
        modifications: dict[str, datetime | str] | None = None,
        freshness: FreshnessIntent = FreshnessIntent.EVENTUAL,
    ) -> dict[str, CachedRow | None]:
        """Retrieve multiple cached dataframe rows.

        Per FR-CACHE-021: Batch retrieval for efficiency.

        Args:
            task_project_pairs: List of (task_gid, project_gid) tuples.
            schema_version: Current schema version for validation.
            modifications: Optional dict of task_gid -> modified_at for staleness.
            freshness: Cache freshness mode.

        Returns:
            Dict mapping cache keys to CachedRow or None.
        """
        modifications = modifications or {}
        results: dict[str, CachedRow | None] = {}

        for task_gid, project_gid in task_project_pairs:
            key = make_dataframe_key(task_gid, project_gid)
            current_modified_at = modifications.get(task_gid)
            results[key] = await self.get_cached_row_async(
                task_gid=task_gid,
                project_gid=project_gid,
                schema_version=schema_version,
                current_modified_at=current_modified_at,
                freshness=freshness,
            )

        return results

    async def cache_row_async(
        self,
        task_gid: str,
        project_gid: str,
        data: dict[str, Any],
        schema_version: str,
        version: datetime | str,
        ttl: int | None = None,
    ) -> bool:
        """Cache a dataframe row.

        Per FR-CACHE-002: Writes dataframe to cache with version metadata.

        Args:
            task_gid: The task GID.
            project_gid: The project context GID.
            data: The extracted row data.
            schema_version: Schema version used for extraction.
            version: The task's modified_at timestamp.
            ttl: Optional TTL override (uses default if None).

        Returns:
            True if cached successfully, False on error.
        """
        key = make_dataframe_key(task_gid, project_gid)
        effective_ttl = ttl if ttl is not None else self._default_ttl

        # Normalize version to datetime
        version_dt = parse_version(version) if isinstance(version, str) else version
        if version_dt.tzinfo is None:
            version_dt = version_dt.replace(tzinfo=UTC)

        try:
            entry = CacheEntry(
                key=key,
                data=data,
                entry_type=EntryType.DATAFRAME,
                version=version_dt,
                cached_at=datetime.now(UTC),
                ttl=effective_ttl,
                project_gid=project_gid,
                metadata={"schema_version": schema_version},
            )

            self._cache.set_versioned(key, entry)
            self._log_cache_event("write", key, entry_type="dataframe")
            return True

        except CACHE_TRANSIENT_ERRORS as exc:
            # FR-CACHE-008: Graceful degradation
            self._log_cache_event(
                "error",
                key,
                entry_type="dataframe",
                metadata={"error": str(exc), "operation": "write"},
            )
            return False

    async def cache_batch_async(
        self,
        rows: list[tuple[str, str, dict[str, Any], datetime | str]],
        schema_version: str,
        ttl: int | None = None,
    ) -> int:
        """Cache multiple dataframe rows.

        Per FR-CACHE-022: Batch write for efficiency.

        Args:
            rows: List of (task_gid, project_gid, data, version) tuples.
            schema_version: Schema version used for extraction.
            ttl: Optional TTL override.

        Returns:
            Count of successfully cached rows.
        """
        successful = 0
        entries: dict[str, CacheEntry] = {}
        effective_ttl = ttl if ttl is not None else self._default_ttl

        try:
            for task_gid, project_gid, data, version in rows:
                key = make_dataframe_key(task_gid, project_gid)

                # Normalize version
                version_dt = (
                    parse_version(version) if isinstance(version, str) else version
                )
                if version_dt.tzinfo is None:
                    version_dt = version_dt.replace(tzinfo=UTC)

                entry = CacheEntry(
                    key=key,
                    data=data,
                    entry_type=EntryType.DATAFRAME,
                    version=version_dt,
                    cached_at=datetime.now(UTC),
                    ttl=effective_ttl,
                    project_gid=project_gid,
                    metadata={"schema_version": schema_version},
                )
                entries[key] = entry

            # Batch write
            self._cache.set_batch(entries)
            successful = len(entries)

            for key in entries:
                self._log_cache_event("write", key, entry_type="dataframe")

        except CACHE_TRANSIENT_ERRORS as exc:
            # FR-CACHE-008: Graceful degradation
            self._log_cache_event(
                "error",
                "batch",
                entry_type="dataframe",
                metadata={"error": str(exc), "operation": "batch_write"},
            )

        return successful

    async def warm_dataframe_async(
        self,
        task_project_pairs: list[tuple[str, str]],
    ) -> int:
        """Warm cache for specified task+project combinations.

        Per FR-CACHE-005: Pre-populate cache for anticipated access.
        Note: This only marks entries for warming; actual data loading
        must be done by the caller.

        Args:
            task_project_pairs: List of (task_gid, project_gid) tuples.

        Returns:
            Count of entries to warm (for tracking).
        """
        # This method prepares the warm operation; actual data loading
        # is handled by the caller who has access to task data
        try:
            gids = [make_dataframe_key(t, p) for t, p in task_project_pairs]
            result = self._cache.warm(gids, [EntryType.DATAFRAME])
            return result.warmed + result.skipped
        except CACHE_TRANSIENT_ERRORS as exc:
            self._log_cache_event(
                "error",
                "warm",
                entry_type="dataframe",
                metadata={"error": str(exc)},
            )
            return 0

    async def invalidate_async(
        self,
        task_gid: str,
        project_gid: str,
    ) -> bool:
        """Invalidate cached dataframe for task+project.

        Per FR-CACHE-006: Explicit cache invalidation.

        Args:
            task_gid: The task GID.
            project_gid: The project context GID.

        Returns:
            True if invalidated successfully, False on error.
        """
        key = make_dataframe_key(task_gid, project_gid)

        try:
            self._cache.invalidate(key, [EntryType.DATAFRAME])
            self._log_cache_event("evict", key, entry_type="dataframe")
            return True
        except CACHE_TRANSIENT_ERRORS as exc:
            self._log_cache_event(
                "error",
                key,
                entry_type="dataframe",
                metadata={"error": str(exc), "operation": "invalidate"},
            )
            return False

    # =========================================================================
    # Sync Wrappers (Backward Compatibility)
    # =========================================================================

    def get_cached_row(
        self,
        task_gid: str,
        project_gid: str,
        schema_version: str,
        current_modified_at: datetime | str | None = None,
        freshness: FreshnessIntent = FreshnessIntent.EVENTUAL,
    ) -> CachedRow | None:
        """Sync wrapper for get_cached_row_async.

        See get_cached_row_async for full documentation.
        """
        return asyncio.run(
            self.get_cached_row_async(
                task_gid=task_gid,
                project_gid=project_gid,
                schema_version=schema_version,
                current_modified_at=current_modified_at,
                freshness=freshness,
            )
        )

    def get_cached_batch(
        self,
        task_project_pairs: list[tuple[str, str]],
        schema_version: str,
        modifications: dict[str, datetime | str] | None = None,
        freshness: FreshnessIntent = FreshnessIntent.EVENTUAL,
    ) -> dict[str, CachedRow | None]:
        """Sync wrapper for get_cached_batch_async.

        See get_cached_batch_async for full documentation.
        """
        return asyncio.run(
            self.get_cached_batch_async(
                task_project_pairs=task_project_pairs,
                schema_version=schema_version,
                modifications=modifications,
                freshness=freshness,
            )
        )

    def cache_row(
        self,
        task_gid: str,
        project_gid: str,
        data: dict[str, Any],
        schema_version: str,
        version: datetime | str,
        ttl: int | None = None,
    ) -> bool:
        """Sync wrapper for cache_row_async.

        See cache_row_async for full documentation.
        """
        return asyncio.run(
            self.cache_row_async(
                task_gid=task_gid,
                project_gid=project_gid,
                data=data,
                schema_version=schema_version,
                version=version,
                ttl=ttl,
            )
        )

    def cache_batch(
        self,
        rows: list[tuple[str, str, dict[str, Any], datetime | str]],
        schema_version: str,
        ttl: int | None = None,
    ) -> int:
        """Sync wrapper for cache_batch_async.

        See cache_batch_async for full documentation.
        """
        return asyncio.run(
            self.cache_batch_async(rows=rows, schema_version=schema_version, ttl=ttl)
        )

    def invalidate(
        self,
        task_gid: str,
        project_gid: str,
    ) -> bool:
        """Sync wrapper for invalidate_async.

        See invalidate_async for full documentation.
        """
        return asyncio.run(self.invalidate_async(task_gid, project_gid))

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _check_staleness(
        self,
        cached_version: datetime,
        current_version: datetime | str,
    ) -> bool:
        """Check if cached version is still current.

        Per ADR-0019: Staleness detection algorithm.

        Args:
            cached_version: Version stored in cache.
            current_version: Current version from source.

        Returns:
            True if cache is current (not stale), False if stale.
        """
        current = (
            parse_version(current_version)
            if isinstance(current_version, str)
            else current_version
        )

        # Normalize timezones
        if cached_version.tzinfo is None:
            cached_version = cached_version.replace(tzinfo=UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)

        return cached_version >= current

    def _log_cache_event(
        self,
        event_type: str,
        key: str,
        entry_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a cache event.

        Per ADR-0023: Cache observability strategy.

        Args:
            event_type: Type of event (hit, miss, write, evict, error).
            key: Cache key involved.
            entry_type: Entry type if applicable.
            metadata: Additional event metadata.
        """
        # Try to use LogProvider.log_cache_event if available
        if self._logger is not None:
            if hasattr(self._logger, "log_cache_event"):
                self._logger.log_cache_event(
                    event_type=event_type,
                    key=key,
                    entry_type=entry_type,
                    metadata=metadata,
                )
                return

            # Fall back to standard logging
            log_msg = f"cache_{event_type}: key={key}"
            if entry_type:
                log_msg += f" type={entry_type}"
            if metadata:
                log_msg += f" {metadata}"

            if event_type == "error":
                self._logger.error(log_msg)
            else:
                self._logger.debug(log_msg)
        else:
            # Use module logger
            log_msg = f"cache_{event_type}: key={key}"
            if entry_type:
                log_msg += f" type={entry_type}"
            if metadata:
                log_msg += f" {metadata}"

            if event_type == "error":
                _logger.error(log_msg)
            else:
                _logger.debug(log_msg)
