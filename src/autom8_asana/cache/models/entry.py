"""Cache entry dataclass, entry type enum, and typed subclass hierarchy.

Per TDD-unified-cacheentry-hierarchy: Provides a polymorphic CacheEntry
hierarchy with __init_subclass__ auto-registration for deserialization
dispatch. Base CacheEntry remains directly constructible for backward
compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from autom8_asana.cache.models.freshness_stamp import FreshnessStamp


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
    # Note: TTLs are NOT enforced here - they are resolved at cache time
    # via CacheConfig.get_entity_ttl() or DEFAULT_ENTITY_TTLS in config.py.
    PROJECT = "project"  # has modified_at
    SECTION = "section"  # no modified_at
    USER = "user"  # no modified_at
    CUSTOM_FIELD = "custom_field"  # no modified_at

    # Per PRD-CACHE-PERF-DETECTION: Detection result caching
    DETECTION = "detection"  # uses task.modified_at

    # Per PRD-CACHE-OPT-P3 / ADR-0131: GID enumeration caching
    PROJECT_SECTIONS = "project_sections"  # TTL: 1800s (30 min)
    GID_ENUMERATION = "gid_enumeration"  # TTL: 300s (5 min)

    # Per ADR-INS-004: autom8_data insights caching
    INSIGHTS = "insights"  # TTL: 300s (default, configurable via AUTOM8_DATA_CACHE_TTL)


@dataclass(frozen=True)
class CacheEntry:
    """Immutable cache entry with versioning metadata.

    Represents a cached Asana resource with version tracking for
    staleness detection. The ``version`` field typically contains the
    resource's ``modified_at`` timestamp.

    This base class remains directly constructible for backward
    compatibility. New code should prefer typed subclasses
    (EntityCacheEntry, RelationshipCacheEntry, etc.) where the
    EntryType is known at construction time.

    Subclass Registration:
        Subclasses declare ``entry_types=(EntryType.TASK,)`` in the
        class statement to auto-register for deserialization dispatch
        via ``CacheEntry.from_dict()``.

    Attributes:
        key: The cache key (typically task GID).
        data: The cached payload (task dict, list of subtasks, etc.).
        entry_type: Type of entry for versioning strategy selection.
        version: The modified_at timestamp for staleness comparison.
        cached_at: When this entry was written to cache.
        ttl: Time-to-live in seconds, None for no expiration.
        project_gid: Project context for dataframe entries (varies by project).
        metadata: Additional entry-type-specific metadata.
        freshness_stamp: Optional freshness provenance metadata.

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
    cached_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl: int | None = 300
    project_gid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    freshness_stamp: FreshnessStamp | None = None

    # Registry of EntryType.value -> subclass for deserialization dispatch.
    # Populated automatically by __init_subclass__ on subclass definition.
    _type_registry: ClassVar[dict[str, type[CacheEntry]]] = {}

    def __init_subclass__(
        cls,
        entry_types: tuple[EntryType, ...] = (),
        **kwargs: Any,
    ) -> None:
        """Register subclass for deserialization dispatch.

        Args:
            entry_types: Tuple of EntryType members this subclass handles.
                Each value is registered in _type_registry for from_dict()
                dispatch.
        """
        super().__init_subclass__(**kwargs)
        for et in entry_types:
            CacheEntry._type_registry[et.value] = cls

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if entry has exceeded its TTL.

        Args:
            now: Current time for comparison. Defaults to UTC now.

        Returns:
            True if entry has expired, False if still valid or no TTL set.
        """
        if self.ttl is None:
            return False
        now = now or datetime.now(UTC)
        # Ensure both datetimes are timezone-aware for comparison
        cached_at = self.cached_at
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
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
            cached_version = cached_version.replace(tzinfo=UTC)
        if current_version.tzinfo is None:
            current_version = current_version.replace(tzinfo=UTC)

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict with _type discriminator for polymorphic deserialization.

        The ``_type`` field carries the ``EntryType.value`` string so that
        ``CacheEntry.from_dict()`` can dispatch to the correct subclass.
        The ``_class`` field is informational (human-readable subclass name).

        Returns:
            Dict representation suitable for JSON serialization.
        """
        result: dict[str, Any] = {
            "_type": self.entry_type.value,
            "_class": type(self).__name__,
            "key": self.key,
            "data": self.data,
            "entry_type": self.entry_type.value,
            "version": self.version.isoformat(),
            "cached_at": self.cached_at.isoformat(),
            "ttl": self.ttl,
            "project_gid": self.project_gid,
            "metadata": self.metadata,
        }
        if self.freshness_stamp is not None:
            result["freshness_stamp"] = {
                "last_verified_at": self.freshness_stamp.last_verified_at.isoformat(),
                "source": self.freshness_stamp.source.value,
                "staleness_hint": self.freshness_stamp.staleness_hint,
            }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Deserialize from dict, dispatching to the correct subclass.

        If ``_type`` is present and a subclass is registered for that
        entry type value, delegates to the subclass's ``_from_dict_impl``.
        Otherwise constructs a base CacheEntry (backward compatibility
        for legacy serialized data without ``_type``).

        Args:
            data: Dict representation (e.g., from JSON deserialization).

        Returns:
            CacheEntry or appropriate subclass instance.
        """
        entry_type_str = data.get("_type") or data.get("entry_type")
        target_cls = (
            cls._type_registry.get(entry_type_str, cls) if entry_type_str else cls
        )
        # Delegate to subclass from_dict_impl if registered
        if target_cls is not cls and hasattr(target_cls, "_from_dict_impl"):
            result: CacheEntry = target_cls._from_dict_impl(data)
            return result
        # Base CacheEntry construction (legacy path)
        return _deserialize_base(data)


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
            dt = dt.replace(tzinfo=UTC)
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
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed
            except ValueError:
                continue
        raise ValueError(f"Unable to parse datetime: {value}")


def _deserialize_base(data: dict[str, Any]) -> CacheEntry:
    """Deserialize a dict into a base CacheEntry instance.

    Used for legacy data without ``_type`` or when no subclass is
    registered for the given entry type. Unknown fields are ignored
    for forward compatibility.

    Args:
        data: Dict representation of a CacheEntry.

    Returns:
        Base CacheEntry instance.
    """
    from autom8_asana.cache.models.freshness_stamp import (
        FreshnessStamp,
        VerificationSource,
    )

    entry_type_str = data.get("_type") or data.get("entry_type", "task")
    entry_type = EntryType(entry_type_str)

    version_raw = data.get("version")
    version: datetime = (
        _parse_datetime(version_raw)
        if isinstance(version_raw, str)
        else (version_raw if isinstance(version_raw, datetime) else datetime.now(UTC))
    )

    cached_at_raw = data.get("cached_at")
    cached_at = (
        _parse_datetime(cached_at_raw)
        if isinstance(cached_at_raw, str)
        else (cached_at_raw or datetime.now(UTC))
    )

    # Reconstruct FreshnessStamp if present
    stamp_data = data.get("freshness_stamp")
    freshness_stamp = None
    if isinstance(stamp_data, dict):
        freshness_stamp = FreshnessStamp(
            last_verified_at=_parse_datetime(stamp_data["last_verified_at"]),
            source=VerificationSource(stamp_data.get("source", "unknown")),
            staleness_hint=stamp_data.get("staleness_hint"),
        )

    return CacheEntry(
        key=data.get("key", ""),
        data=data.get("data", {}),
        entry_type=entry_type,
        version=version,
        cached_at=cached_at,
        ttl=data.get("ttl", 300),
        project_gid=data.get("project_gid"),
        metadata=data.get("metadata", {}),
        freshness_stamp=freshness_stamp,
    )


# ---------------------------------------------------------------------------
# Typed Subclasses
# ---------------------------------------------------------------------------
# Per TDD-unified-cacheentry-hierarchy: Each subclass declares the
# EntryType members it handles via entry_types=(...). The __init_subclass__
# hook auto-registers them in CacheEntry._type_registry for from_dict()
# polymorphic dispatch.


@dataclass(frozen=True)
class EntityCacheEntry(
    CacheEntry,
    entry_types=(
        EntryType.TASK,
        EntryType.PROJECT,
        EntryType.SECTION,
        EntryType.USER,
        EntryType.CUSTOM_FIELD,
    ),
):
    """Cache entry for single Asana entity lookups.

    Provides semantic alias for the entity GID and supports
    completeness tracking via typed fields rather than metadata dict.

    Attributes:
        completeness_level: Level of field completeness ("minimal",
            "standard", "full"). Replaces metadata["completeness_level"].
        opt_fields: Tuple of opt_field names included in this entry.
            Replaces metadata["opt_fields_used"].
    """

    completeness_level: str | None = None
    opt_fields: tuple[str, ...] | None = None

    @property
    def entity_gid(self) -> str:
        """Semantic alias for key (the Asana entity GID)."""
        return self.key

    @property
    def has_modified_at(self) -> bool:
        """Whether this entity type carries modified_at for version comparison."""
        return self.entry_type in (EntryType.TASK, EntryType.PROJECT)

    def to_dict(self) -> dict[str, Any]:
        """Serialize with subclass-specific fields."""
        result = super().to_dict()
        result["completeness_level"] = self.completeness_level
        result["opt_fields"] = list(self.opt_fields) if self.opt_fields else None
        return result

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> EntityCacheEntry:
        """Construct EntityCacheEntry from dict."""
        base = _deserialize_base(data)
        opt_fields_raw = data.get("opt_fields")
        opt_fields = tuple(opt_fields_raw) if opt_fields_raw else None
        return cls(
            key=base.key,
            data=base.data,
            entry_type=base.entry_type,
            version=base.version,
            cached_at=base.cached_at,
            ttl=base.ttl,
            project_gid=base.project_gid,
            metadata=base.metadata,
            freshness_stamp=base.freshness_stamp,
            completeness_level=data.get("completeness_level"),
            opt_fields=opt_fields,
        )


@dataclass(frozen=True)
class RelationshipCacheEntry(
    CacheEntry,
    entry_types=(
        EntryType.SUBTASKS,
        EntryType.DEPENDENCIES,
        EntryType.DEPENDENTS,
        EntryType.STORIES,
        EntryType.ATTACHMENTS,
    ),
):
    """Cache entry for relationship lists (subtasks, dependencies, etc.).

    Carries the parent entity GID and the relationship count for
    overflow threshold checks via OverflowSettings.

    Attributes:
        parent_gid: The entity these relationships belong to.
            Defaults to key if not explicitly set.
        relationship_count: Number of items in the relationship list.
            Auto-computed from data if not provided.
    """

    parent_gid: str | None = None
    relationship_count: int = 0

    def __post_init__(self) -> None:
        """Compute relationship_count from data if not provided."""
        if self.relationship_count == 0 and isinstance(self.data, dict):
            items = self.data.get("data", self.data)
            if isinstance(items, list):
                object.__setattr__(self, "relationship_count", len(items))

    @property
    def effective_parent_gid(self) -> str:
        """Parent GID (falls back to key if parent_gid is None)."""
        return self.parent_gid or self.key

    def to_dict(self) -> dict[str, Any]:
        """Serialize with subclass-specific fields."""
        result = super().to_dict()
        result["parent_gid"] = self.parent_gid
        result["relationship_count"] = self.relationship_count
        return result

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> RelationshipCacheEntry:
        """Construct RelationshipCacheEntry from dict."""
        base = _deserialize_base(data)
        return cls(
            key=base.key,
            data=base.data,
            entry_type=base.entry_type,
            version=base.version,
            cached_at=base.cached_at,
            ttl=base.ttl,
            project_gid=base.project_gid,
            metadata=base.metadata,
            freshness_stamp=base.freshness_stamp,
            parent_gid=data.get("parent_gid"),
            relationship_count=data.get("relationship_count", 0),
        )


@dataclass(frozen=True)
class DataFrameMetaCacheEntry(
    CacheEntry,
    entry_types=(
        EntryType.DATAFRAME,
        EntryType.PROJECT_SECTIONS,
        EntryType.GID_ENUMERATION,
    ),
):
    """Cache entry for DataFrame-related metadata lookups.

    ``project_gid`` is required (not Optional) since all DataFrame
    operations are scoped to a project.

    Note: This is NOT the DataFrame cache entry (which holds a
    ``pl.DataFrame``). This caches metadata about DataFrames in the
    versioned Redis/S3 tier.

    Attributes:
        schema_version: Schema version string for invalidation on bumps.
    """

    schema_version: str | None = None

    def __post_init__(self) -> None:
        """Validate project_gid is set for DataFrame entries."""
        if self.project_gid is None:
            raise ValueError(
                f"project_gid is required for {self.entry_type.value} entries"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize with subclass-specific fields."""
        result = super().to_dict()
        result["schema_version"] = self.schema_version
        return result

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> DataFrameMetaCacheEntry:
        """Construct DataFrameMetaCacheEntry from dict."""
        base = _deserialize_base(data)
        return cls(
            key=base.key,
            data=base.data,
            entry_type=base.entry_type,
            version=base.version,
            cached_at=base.cached_at,
            ttl=base.ttl,
            project_gid=base.project_gid,
            metadata=base.metadata,
            freshness_stamp=base.freshness_stamp,
            schema_version=data.get("schema_version"),
        )


@dataclass(frozen=True)
class DetectionCacheEntry(
    CacheEntry,
    entry_types=(EntryType.DETECTION,),
):
    """Cache entry for business detection results.

    Scoped to a task and a detection type (unit, offer, etc.).

    Attributes:
        detection_type: Kind of detection ("unit", "offer", etc.).
    """

    detection_type: str | None = None

    @property
    def task_gid(self) -> str:
        """Semantic alias for key (the task this detection is for)."""
        return self.key

    def to_dict(self) -> dict[str, Any]:
        """Serialize with subclass-specific fields."""
        result = super().to_dict()
        result["detection_type"] = self.detection_type
        return result

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> DetectionCacheEntry:
        """Construct DetectionCacheEntry from dict."""
        base = _deserialize_base(data)
        return cls(
            key=base.key,
            data=base.data,
            entry_type=base.entry_type,
            version=base.version,
            cached_at=base.cached_at,
            ttl=base.ttl,
            project_gid=base.project_gid,
            metadata=base.metadata,
            freshness_stamp=base.freshness_stamp,
            detection_type=data.get("detection_type"),
        )
