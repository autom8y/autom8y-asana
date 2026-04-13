"""Completeness upgrader implementation for Asana tasks.

Per TDD-CACHE-SDK-PRIMITIVES-001: Implements the autom8y_cache.CompletenessUpgrader
protocol for transparent fetch-on-miss upgrades of Asana task cache entries.

This module provides the AsanaTaskUpgrader class that can be wired into cache
operations to automatically fetch missing fields when a cached entry has
insufficient completeness for the requested operation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_cache import CacheEntry
from autom8y_log import get_logger

from autom8_asana.cache.models.completeness import (
    FULL_FIELDS,
    MINIMAL_FIELDS,
    STANDARD_FIELDS,
    CompletenessLevel,
    create_completeness_metadata,
)
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.core.errors import CACHE_TRANSIENT_ERRORS

if TYPE_CHECKING:
    from autom8_asana.clients.tasks import TasksClient

logger = get_logger(__name__)

# Map completeness levels to their field sets
LEVEL_FIELDS: dict[CompletenessLevel, frozenset[str]] = {
    CompletenessLevel.MINIMAL: MINIMAL_FIELDS,
    CompletenessLevel.STANDARD: STANDARD_FIELDS,
    CompletenessLevel.FULL: FULL_FIELDS,
}


class AsanaTaskUpgrader:
    """Completeness upgrader for Asana tasks.

    Implements autom8y_cache.CompletenessUpgrader protocol to provide
    domain-specific fetch logic for upgrading cache entries when the
    cached entry exists but has insufficient completeness.

    Per TDD-CACHE-SDK-PRIMITIVES-001 and TDD-CACHE-COMPLETENESS-001:
    When a cached entry is found but doesn't have enough fields for
    the requested operation, this upgrader fetches the task with
    expanded opt_fields.

    Attributes:
        tasks_client: TasksClient for fetching task data from Asana API.

    Example:
        >>> upgrader = AsanaTaskUpgrader(tasks_client)
        >>> # Upgrade a cache entry to STANDARD completeness
        >>> entry = await upgrader.upgrade_async(
        ...     "task-gid",
        ...     CompletenessLevel.STANDARD
        ... )
        >>> # Get fields for a specific level
        >>> fields = upgrader.get_fields_for_level(CompletenessLevel.FULL)
    """

    def __init__(self, tasks_client: TasksClient) -> None:
        """Initialize upgrader with tasks client.

        Args:
            tasks_client: Asana TasksClient for API calls.
        """
        self._tasks_client = tasks_client

        # Statistics
        self._stats: dict[str, int] = {
            "upgrade_calls": 0,
            "upgrade_success": 0,
            "upgrade_failure": 0,
        }

    async def upgrade_async(
        self,
        key: str,
        target_level: CompletenessLevel,
    ) -> CacheEntry | None:
        """Fetch task data at target completeness level.

        Fetches the task from Asana API with opt_fields corresponding
        to the target completeness level, then returns a CacheEntry
        suitable for storing in the cache.

        Args:
            key: Task GID to fetch.
            target_level: Desired completeness level.

        Returns:
            CacheEntry if fetch succeeds, None otherwise.
            The returned entry will be at or above target_level.
        """
        self._stats["upgrade_calls"] += 1

        opt_fields = list(self.get_fields_for_level(target_level))

        try:
            task = await self._tasks_client.get_async(key, opt_fields=opt_fields, raw=True)

            if task is None:
                logger.debug(
                    "upgrade_task_not_found",
                    extra={"gid": key, "target_level": target_level.name},
                )
                self._stats["upgrade_failure"] += 1
                return None

            # Build cache entry
            modified_at = task.get("modified_at")
            version = self._parse_version(modified_at)

            # Create completeness metadata
            completeness_metadata = create_completeness_metadata(
                opt_fields, explicit_level=target_level
            )

            entry = CacheEntry(
                key=key,
                data=task,
                entry_type=EntryType.TASK.value,
                version=version,
                cached_at=datetime.now(UTC),
                metadata=completeness_metadata,
            )

            self._stats["upgrade_success"] += 1
            logger.info(
                "cache_entry_upgraded",
                extra={"gid": key, "target_level": target_level.name},
            )

            return entry

        except CACHE_TRANSIENT_ERRORS as e:
            logger.warning(
                "cache_upgrade_failed",
                extra={
                    "gid": key,
                    "target_level": target_level.name,
                    "error": str(e),
                },
            )
            self._stats["upgrade_failure"] += 1
            return None

    def get_fields_for_level(
        self,
        level: CompletenessLevel,
    ) -> frozenset[str]:
        """Get field set for a completeness level.

        Returns the Asana opt_fields to request when fetching
        at a specific completeness level.

        Args:
            level: Completeness level to get fields for.

        Returns:
            Frozenset of field names to request from Asana API.
        """
        return LEVEL_FIELDS.get(level, MINIMAL_FIELDS)

    def get_stats(self) -> dict[str, int]:
        """Get upgrader statistics.

        Returns:
            Dict with upgrade_calls, upgrade_success, upgrade_failure counts.
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics to zero."""
        for key in self._stats:
            self._stats[key] = 0

    def _parse_version(self, modified_at: str | None) -> datetime:
        """Parse modified_at to datetime for version tracking.

        Args:
            modified_at: ISO format timestamp or None.

        Returns:
            Parsed datetime, or current time if None.
        """
        if not modified_at:
            return datetime.now(UTC)

        # Handle Z suffix
        if modified_at.endswith("Z"):
            modified_at = modified_at[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(modified_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            logger.warning(
                "version_parse_failed",
                extra={"modified_at": modified_at},
            )
            return datetime.now(UTC)
