"""Cache configuration settings."""

from __future__ import annotations

from dataclasses import dataclass, field

from autom8_asana.cache.models.entry import EntryType


@dataclass
class OverflowSettings:
    """Per-relationship overflow thresholds.

    When a relationship count exceeds the threshold, the data is
    not cached to prevent unbounded cache growth. These thresholds
    are based on typical Asana usage patterns.

    Attributes:
        subtasks: Maximum subtasks before skipping cache (default 40).
        dependencies: Maximum dependencies before skipping cache.
        dependents: Maximum dependents before skipping cache.
        stories: Maximum stories before skipping cache (default 100).
        attachments: Maximum attachments before skipping cache.
    """

    subtasks: int = 40
    dependencies: int = 40
    dependents: int = 40
    stories: int = 100
    attachments: int = 40

    def get_threshold(self, entry_type: EntryType) -> int | None:
        """Get overflow threshold for an entry type.

        Args:
            entry_type: The entry type to get threshold for.

        Returns:
            Threshold count, or None if no overflow limit applies.
        """
        thresholds = {
            EntryType.SUBTASKS: self.subtasks,
            EntryType.DEPENDENCIES: self.dependencies,
            EntryType.DEPENDENTS: self.dependents,
            EntryType.STORIES: self.stories,
            EntryType.ATTACHMENTS: self.attachments,
        }
        return thresholds.get(entry_type)

    def should_cache(self, entry_type: EntryType, count: int) -> bool:
        """Check if count is within threshold for caching.

        Args:
            entry_type: The entry type being cached.
            count: Number of items in the relationship.

        Returns:
            True if should cache (within threshold), False if overflow.
        """
        threshold = self.get_threshold(entry_type)
        if threshold is None:
            return True  # No threshold for this type
        return count <= threshold


@dataclass
class TTLSettings:
    """TTL configuration with per-project and per-entry-type overrides.

    TTL resolution priority (first match wins):
    1. Project-specific TTL if project_gid provided and configured
    2. Entry-type-specific TTL if entry_type provided and configured
    3. Default TTL

    Attributes:
        default_ttl: Default TTL in seconds (default 300 = 5 minutes).
        project_ttls: Per-project TTL overrides keyed by project GID.
        entry_type_ttls: Per-entry-type TTL overrides.

    Example:
        >>> ttl = TTLSettings(
        ...     default_ttl=300,
        ...     project_ttls={"123456": 600},  # 10 min for project 123456
        ...     entry_type_ttls={"stories": 60},  # 1 min for stories
        ... )
        >>> ttl.get_ttl(project_gid="123456")
        600
        >>> ttl.get_ttl(entry_type="stories")
        60
        >>> ttl.get_ttl()
        300
    """

    default_ttl: int = 300
    project_ttls: dict[str, int] = field(default_factory=dict)
    entry_type_ttls: dict[str, int] = field(default_factory=dict)

    def get_ttl(
        self,
        project_gid: str | None = None,
        entry_type: str | EntryType | None = None,
    ) -> int:
        """Resolve TTL with priority: project > entry_type > default.

        Args:
            project_gid: Optional project GID for project-specific TTL.
            entry_type: Optional entry type for type-specific TTL.

        Returns:
            Resolved TTL in seconds.
        """
        if project_gid and project_gid in self.project_ttls:
            return self.project_ttls[project_gid]

        if entry_type:
            type_key = (
                entry_type.value if isinstance(entry_type, EntryType) else entry_type
            )
            if type_key in self.entry_type_ttls:
                return self.entry_type_ttls[type_key]

        return self.default_ttl


@dataclass
class CacheSettings:
    """Complete cache configuration.

    Central configuration for all cache behavior including TTL,
    overflow thresholds, and operational parameters.

    Attributes:
        enabled: Whether caching is enabled (default True).
        ttl: TTL configuration settings.
        overflow: Overflow threshold settings.
        batch_check_ttl: Seconds for in-memory batch check cache (default 25).
        reconnect_interval: Seconds between Redis reconnect attempts (default 30).
        max_batch_size: Maximum GIDs per batch modification check (default 100).

    Example:
        >>> settings = CacheSettings(
        ...     enabled=True,
        ...     ttl=TTLSettings(default_ttl=600),
        ...     overflow=OverflowSettings(stories=50),
        ... )
    """

    enabled: bool = True
    ttl: TTLSettings = field(default_factory=TTLSettings)
    overflow: OverflowSettings = field(default_factory=OverflowSettings)
    # TTL for in-memory batch modification check cache (25 seconds)
    # Balances freshness vs. API pressure for bulk staleness checks
    batch_check_ttl: int = 25
    # Interval between Redis reconnection attempts (30 seconds)
    # Prevents connection storm after transient Redis unavailability
    reconnect_interval: int = 30
    max_batch_size: int = 100

    def get_ttl(
        self,
        project_gid: str | None = None,
        entry_type: str | EntryType | None = None,
    ) -> int:
        """Convenience method to get TTL from settings.

        Args:
            project_gid: Optional project GID for project-specific TTL.
            entry_type: Optional entry type for type-specific TTL.

        Returns:
            Resolved TTL in seconds.
        """
        return self.ttl.get_ttl(project_gid, entry_type)

    def should_cache(self, entry_type: EntryType, count: int) -> bool:
        """Check if count is within threshold for caching.

        Args:
            entry_type: The entry type being cached.
            count: Number of items in the relationship.

        Returns:
            True if should cache (within threshold), False if overflow.
        """
        return self.overflow.should_cache(entry_type, count)
