"""Derived cache entry operations for computed timeline data.

Per TDD-SECTION-TIMELINE-REMEDIATION: Provides read/write operations
for DerivedTimelineCacheEntry, which stores pre-computed SectionTimeline
data keyed by (project_gid, classifier_name).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.models.entry import (
    DerivedTimelineCacheEntry,
    EntryType,
)
from autom8_asana.models.business.section_timeline import (
    SectionInterval,
    SectionTimeline,
)

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)


# Default TTL for derived timeline entries: 5 minutes.
# Balances freshness (stories may update) vs. computation cost (~2-4s for 3,800 entities).
_DERIVED_TIMELINE_TTL = 300


def make_derived_timeline_key(project_gid: str, classifier_name: str) -> str:
    """Build the cache key for a derived timeline entry.

    Args:
        project_gid: Asana project GID.
        classifier_name: Classifier name ("offer", "unit").

    Returns:
        Composite cache key string.
    """
    return f"timeline:{project_gid}:{classifier_name}"


def get_cached_timelines(
    project_gid: str,
    classifier_name: str,
    cache: CacheProvider,
) -> DerivedTimelineCacheEntry | None:
    """Read a derived timeline entry from cache.

    Args:
        project_gid: Asana project GID.
        classifier_name: Classifier name.
        cache: Cache provider.

    Returns:
        DerivedTimelineCacheEntry if found and not expired, None otherwise.
    """
    key = make_derived_timeline_key(project_gid, classifier_name)
    entry = cache.get_versioned(key, EntryType.DERIVED_TIMELINE)
    if entry is None:
        return None
    # Ensure we return the typed subclass
    if isinstance(entry, DerivedTimelineCacheEntry):
        return entry
    # Fallback: base CacheEntry returned (deserialization did not produce typed subclass).
    # This indicates a registry miss or forward-compatibility edge case. Log for observability.
    logger.warning(
        "derived_timeline_cache_type_mismatch",
        extra={
            "key": key,
            "entry_type": type(entry).__name__,
            "expected": "DerivedTimelineCacheEntry",
        },
    )
    return None


def store_derived_timelines(
    project_gid: str,
    classifier_name: str,
    timeline_data: list[dict[str, Any]],
    cache: CacheProvider,
    *,
    entity_count: int = 0,
    cache_hits: int = 0,
    cache_misses: int = 0,
    computation_duration_ms: float = 0.0,
) -> None:
    """Store a derived timeline computation in the cache.

    Args:
        project_gid: Asana project GID.
        classifier_name: Classifier name.
        timeline_data: JSON-serializable list of timeline dicts.
        cache: Cache provider.
        entity_count: Total entities processed.
        cache_hits: Entities with cached stories.
        cache_misses: Entities without cached stories.
        computation_duration_ms: Computation time for observability.
    """
    key = make_derived_timeline_key(project_gid, classifier_name)
    now = datetime.now(UTC)

    entry = DerivedTimelineCacheEntry(
        key=key,
        data={"timelines": timeline_data},
        entry_type=EntryType.DERIVED_TIMELINE,
        version=now,
        cached_at=now,
        ttl=_DERIVED_TIMELINE_TTL,
        project_gid=project_gid,
        metadata={"computed_at": now.isoformat()},
        classifier_name=classifier_name,
        source_entity_count=entity_count,
        source_cache_hits=cache_hits,
        source_cache_misses=cache_misses,
        computation_duration_ms=computation_duration_ms,
    )
    cache.set_versioned(key, entry)


def serialize_timeline(timeline: SectionTimeline) -> dict[str, Any]:
    """Serialize a SectionTimeline to a JSON-compatible dict.

    Per TDD-SECTION-TIMELINE-REMEDIATION AMB-6: JSON dict serialization
    consistent with all other cache entries in the system.

    Args:
        timeline: SectionTimeline domain object.

    Returns:
        JSON-serializable dict.
    """
    return {
        "offer_gid": timeline.offer_gid,
        "office_phone": timeline.office_phone,
        "offer_id": timeline.offer_id,
        "intervals": [
            {
                "section_name": iv.section_name,
                "classification": iv.classification.value
                if iv.classification
                else None,
                "entered_at": iv.entered_at.isoformat(),
                "exited_at": iv.exited_at.isoformat() if iv.exited_at else None,
            }
            for iv in timeline.intervals
        ],
        "task_created_at": (
            timeline.task_created_at.isoformat() if timeline.task_created_at else None
        ),
        "story_count": timeline.story_count,
    }


def deserialize_timeline(data: dict[str, Any]) -> SectionTimeline:
    """Deserialize a SectionTimeline from a JSON dict.

    Per TDD-SECTION-TIMELINE-REMEDIATION AMB-6: Inverse of serialize_timeline.

    Args:
        data: JSON dict previously produced by serialize_timeline.

    Returns:
        SectionTimeline domain object.
    """
    from autom8_asana.models.business.activity import AccountActivity

    intervals: list[SectionInterval] = []
    for iv_data in data.get("intervals", []):
        cls_value = iv_data.get("classification")
        classification = AccountActivity(cls_value) if cls_value else None
        intervals.append(
            SectionInterval(
                section_name=iv_data["section_name"],
                classification=classification,
                entered_at=datetime.fromisoformat(iv_data["entered_at"]),
                exited_at=(
                    datetime.fromisoformat(iv_data["exited_at"])
                    if iv_data.get("exited_at")
                    else None
                ),
            )
        )

    task_created_at = data.get("task_created_at")
    return SectionTimeline(
        offer_gid=data["offer_gid"],
        office_phone=data.get("office_phone"),
        offer_id=data.get("offer_id"),
        intervals=tuple(intervals),
        task_created_at=(
            datetime.fromisoformat(task_created_at) if task_created_at else None
        ),
        story_count=data.get("story_count", 0),
    )
