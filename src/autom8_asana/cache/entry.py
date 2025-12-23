"""Cache entry dataclass and entry type enum."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EntryType(str, Enum):
    """Types of cache entries with distinct versioning strategies.

    Each entry type corresponds to a different Asana resource relationship
    and may have different caching behaviors (TTL, overflow thresholds).
    """

    TASK = "task"
    SUBTASKS = "subtasks"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"
    DATAFRAME = "dataframe"

    # Per TDD-CACHE-UTILIZATION: New entry types for client caching
    PROJECT = "project"  # TTL: 900s (15 min), has modified_at
    SECTION = "section"  # TTL: 1800s (30 min), no modified_at
    USER = "user"  # TTL: 3600s (1 hour), no modified_at
    CUSTOM_FIELD = "custom_field"  # TTL: 1800s (30 min), no modified_at


@dataclass(frozen=True)
class CacheEntry:
    """Immutable cache entry with versioning metadata.

    Represents a cached Asana resource with version tracking for
    staleness detection. The `version` field typically contains the
    resource's `modified_at` timestamp.

    Attributes:
        key: The cache key (typically task GID).
        data: The cached payload (task dict, list of subtasks, etc.).
        entry_type: Type of entry for versioning strategy selection.
        version: The modified_at timestamp for staleness comparison.
        cached_at: When this entry was written to cache.
        ttl: Time-to-live in seconds, None for no expiration.
        project_gid: Project context for dataframe entries (varies by project).
        metadata: Additional entry-type-specific metadata.

    Example:
        >>> entry = CacheEntry(
        ...     key="1234567890",
        ...     data={"gid": "1234567890", "name": "Task"},
        ...     entry_type=EntryType.TASK,
        ...     version=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     cached_at=datetime.now(timezone.utc),
        ...     ttl=300,
        ... )
        >>> entry.is_expired()
        False
    """

    key: str
    data: dict[str, Any]
    entry_type: EntryType
    version: datetime
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int | None = 300
    project_gid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if entry has exceeded its TTL.

        Args:
            now: Current time for comparison. Defaults to UTC now.

        Returns:
            True if entry has expired, False if still valid or no TTL set.
        """
        if self.ttl is None:
            return False
        now = now or datetime.now(timezone.utc)
        # Ensure both datetimes are timezone-aware for comparison
        cached_at = self.cached_at
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        elapsed = (now - cached_at).total_seconds()
        return elapsed > self.ttl

    def is_current(self, current_version: datetime | str) -> bool:
        """Check if cached version matches or is newer than current.

        Used for staleness detection. A cache entry is considered
        current if its version is >= the source's modified_at.

        Args:
            current_version: The current modified_at from the source.
                Can be datetime or ISO format string.

        Returns:
            True if cache is current (not stale), False if stale.
        """
        if isinstance(current_version, str):
            current_version = _parse_datetime(current_version)

        cached_version = self.version
        if isinstance(cached_version, str):
            cached_version = _parse_datetime(cached_version)

        # Normalize to UTC for comparison
        if cached_version.tzinfo is None:
            cached_version = cached_version.replace(tzinfo=timezone.utc)
        if current_version.tzinfo is None:
            current_version = current_version.replace(tzinfo=timezone.utc)

        return cached_version >= current_version

    def is_stale(self, current_version: datetime | str) -> bool:
        """Check if entry is stale compared to current version.

        Inverse of is_current for semantic clarity.

        Args:
            current_version: The current modified_at from the source.

        Returns:
            True if cache is stale, False if current.
        """
        return not self.is_current(current_version)


def _parse_datetime(value: str) -> datetime:
    """Parse ISO format datetime string.

    Handles common ISO formats including those with and without
    timezone information.

    Args:
        value: ISO format datetime string.

    Returns:
        Parsed datetime, with UTC timezone if none specified.
    """
    # Handle various ISO formats
    # Try with timezone first
    try:
        # Python 3.11+ fromisoformat handles Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # Fallback for edge cases
        from datetime import datetime as dt_module

        # Try strptime with common formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]:
            try:
                parsed = dt_module.strptime(value, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                continue
        raise ValueError(f"Unable to parse datetime: {value}")
