"""Tests for derived cache entry operations.

Per TDD-SECTION-TIMELINE-REMEDIATION: Tests for Gap 3 primitives:
- make_derived_timeline_key() format
- _serialize_timeline() / _deserialize_timeline() round-trip
- get_cached_timelines() hit/miss paths
- store_derived_timelines() creates correct entry
- DerivedTimelineCacheEntry to_dict() / from_dict() round-trip
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

from autom8_asana.cache.integration.derived import (
    _DERIVED_TIMELINE_TTL,
    _deserialize_timeline,
    _serialize_timeline,
    get_cached_timelines,
    make_derived_timeline_key,
    store_derived_timelines,
)
from autom8_asana.cache.models.entry import (
    CacheEntry,
    DerivedTimelineCacheEntry,
    EntryType,
)
from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.business.section_timeline import (
    SectionInterval,
    SectionTimeline,
)

# ---------------------------------------------------------------------------
# Mock Cache Provider with EntryType composite keys
# ---------------------------------------------------------------------------


class MockCacheProvider(_SDKMockCacheProvider):
    """Mock cache provider for derived cache tests.

    Uses composite keys (entry_type.value:key) matching the pattern
    established in test_stories.py.
    """

    @property
    def _cache(self) -> dict[str, CacheEntry]:
        return self._versioned_store  # type: ignore[return-value]

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: object = None,
    ) -> CacheEntry | None:
        self.calls.append(
            (
                "get_versioned",
                {"key": key, "entry_type": entry_type, "freshness": freshness},
            )
        )
        cache_key = f"{entry_type.value}:{key}"
        return self._versioned_store.get(cache_key)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        self.calls.append(("set_versioned", {"key": key, "entry": entry}))
        cache_key = f"{entry.entry_type.value}:{key}"
        self._versioned_store[cache_key] = entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _make_timeline(
    offer_gid: str = "offer1",
    office_phone: str | None = "555-0100",
    offer_id: str | None = None,
    intervals: tuple[SectionInterval, ...] | None = None,
    task_created_at: datetime | None = None,
    story_count: int = 2,
) -> SectionTimeline:
    if intervals is None:
        intervals = (
            SectionInterval(
                section_name="ACTIVATING",
                classification=AccountActivity.ACTIVATING,
                entered_at=_utc(2025, 1, 1),
                exited_at=_utc(2025, 1, 5),
            ),
            SectionInterval(
                section_name="ACTIVE",
                classification=AccountActivity.ACTIVE,
                entered_at=_utc(2025, 1, 5),
                exited_at=None,
            ),
        )
    if task_created_at is None:
        task_created_at = _utc(2024, 12, 1)
    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        offer_id=offer_id,
        intervals=intervals,
        task_created_at=task_created_at,
        story_count=story_count,
    )


# ---------------------------------------------------------------------------
# make_derived_timeline_key
# ---------------------------------------------------------------------------


class TestMakeDerivedTimelineKey:
    def test_format_offer(self) -> None:
        """Key format is timeline:{project_gid}:{classifier_name}."""
        key = make_derived_timeline_key("1143843662099250", "offer")
        assert key == "timeline:1143843662099250:offer"

    def test_format_unit(self) -> None:
        key = make_derived_timeline_key("1234567890000000", "unit")
        assert key == "timeline:1234567890000000:unit"

    def test_different_inputs_produce_different_keys(self) -> None:
        k1 = make_derived_timeline_key("proj1", "offer")
        k2 = make_derived_timeline_key("proj1", "unit")
        k3 = make_derived_timeline_key("proj2", "offer")
        assert len({k1, k2, k3}) == 3


# ---------------------------------------------------------------------------
# _serialize_timeline / _deserialize_timeline round-trip
# ---------------------------------------------------------------------------


class TestSerializationRoundTrip:
    def test_full_round_trip(self) -> None:
        """Serialize then deserialize preserves all fields."""
        original = _make_timeline()
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)

        assert restored.offer_gid == original.offer_gid
        assert restored.office_phone == original.office_phone
        assert restored.story_count == original.story_count
        assert restored.task_created_at == original.task_created_at
        assert len(restored.intervals) == len(original.intervals)

    def test_interval_fields_preserved(self) -> None:
        """Interval section_name, classification, entered_at, exited_at preserved."""
        original = _make_timeline()
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)

        for orig_iv, rest_iv in zip(original.intervals, restored.intervals):
            assert rest_iv.section_name == orig_iv.section_name
            assert rest_iv.classification == orig_iv.classification
            assert rest_iv.entered_at == orig_iv.entered_at
            assert rest_iv.exited_at == orig_iv.exited_at

    def test_none_office_phone(self) -> None:
        """office_phone=None round-trips correctly."""
        original = _make_timeline(office_phone=None)
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.office_phone is None

    def test_none_task_created_at(self) -> None:
        """task_created_at=None round-trips correctly."""
        original = SectionTimeline(
            offer_gid="offer1",
            office_phone=None,
            offer_id=None,
            intervals=(),
            task_created_at=None,
            story_count=0,
        )
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.task_created_at is None

    def test_none_classification(self) -> None:
        """Interval with classification=None round-trips correctly."""
        interval = SectionInterval(
            section_name="UNKNOWN_SECTION",
            classification=None,
            entered_at=_utc(2025, 1, 1),
            exited_at=None,
        )
        original = _make_timeline(intervals=(interval,), story_count=1)
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.intervals[0].classification is None

    def test_none_exited_at(self) -> None:
        """Open interval (exited_at=None) round-trips correctly."""
        original = _make_timeline()
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.intervals[-1].exited_at is None

    def test_empty_intervals(self) -> None:
        """Timeline with no intervals round-trips correctly."""
        original = SectionTimeline(
            offer_gid="offer1",
            office_phone=None,
            offer_id=None,
            intervals=(),
            task_created_at=_utc(2025, 1, 1),
            story_count=0,
        )
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.intervals == ()

    def test_zero_story_count(self) -> None:
        """story_count=0 round-trips correctly (imputed timelines)."""
        original = _make_timeline(story_count=0)
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.story_count == 0

    def test_offer_id_round_trip(self) -> None:
        """SC-8, SC-10: offer_id survives serialize-then-deserialize."""
        original = _make_timeline(offer_id="OFR-1234")
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.offer_id == "OFR-1234"

    def test_offer_id_none_round_trip(self) -> None:
        """SC-8, SC-10: offer_id=None survives serialize-then-deserialize."""
        original = _make_timeline(offer_id=None)
        serialized = _serialize_timeline(original)
        restored = _deserialize_timeline(serialized)
        assert restored.offer_id is None

    def test_backward_compat_missing_offer_id(self) -> None:
        """SC-9: Deserialize dict without offer_id key, expect offer_id=None."""
        data = {
            "offer_gid": "offer1",
            "office_phone": "555-0100",
            "intervals": [],
            "task_created_at": "2025-01-01T00:00:00+00:00",
            "story_count": 0,
        }
        # Note: no "offer_id" key in data
        restored = _deserialize_timeline(data)
        assert restored.offer_id is None

    def test_serialized_includes_offer_id_key(self) -> None:
        """SC-8: Serialized dict always contains offer_id key, even when None."""
        original = _make_timeline(offer_id=None)
        serialized = _serialize_timeline(original)
        assert "offer_id" in serialized
        assert serialized["offer_id"] is None

    def test_serialized_format_is_json_compatible(self) -> None:
        """Serialized dict contains only JSON-safe types."""
        import json

        original = _make_timeline()
        serialized = _serialize_timeline(original)
        # Should not raise
        json_str = json.dumps(serialized)
        assert isinstance(json_str, str)


# ---------------------------------------------------------------------------
# get_cached_timelines
# ---------------------------------------------------------------------------


class TestGetCachedTimelines:
    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        return MockCacheProvider()

    def test_cache_miss_returns_none(self, cache: MockCacheProvider) -> None:
        """Empty cache returns None."""
        result = get_cached_timelines("proj1", "offer", cache)
        assert result is None

    def test_cache_hit_returns_entry(self, cache: MockCacheProvider) -> None:
        """Pre-populated cache returns DerivedTimelineCacheEntry."""
        key = make_derived_timeline_key("proj1", "offer")
        now = datetime.now(UTC)
        entry = DerivedTimelineCacheEntry(
            key=key,
            data={"timelines": []},
            entry_type=EntryType.DERIVED_TIMELINE,
            version=now,
            cached_at=now,
            ttl=_DERIVED_TIMELINE_TTL,
            project_gid="proj1",
            metadata={},
            classifier_name="offer",
        )
        cache._cache[f"{EntryType.DERIVED_TIMELINE.value}:{key}"] = entry

        result = get_cached_timelines("proj1", "offer", cache)
        assert result is not None
        assert isinstance(result, DerivedTimelineCacheEntry)
        assert result.classifier_name == "offer"

    def test_base_entry_returns_none(self, cache: MockCacheProvider) -> None:
        """If get_versioned returns base CacheEntry (not subclass), returns None."""
        key = make_derived_timeline_key("proj1", "offer")
        now = datetime.now(UTC)
        # Store a base CacheEntry instead of DerivedTimelineCacheEntry
        base_entry = CacheEntry(
            key=key,
            data={"timelines": []},
            entry_type=EntryType.DERIVED_TIMELINE,
            version=now,
            cached_at=now,
            ttl=300,
        )
        cache._cache[f"{EntryType.DERIVED_TIMELINE.value}:{key}"] = base_entry

        result = get_cached_timelines("proj1", "offer", cache)
        assert result is None


# ---------------------------------------------------------------------------
# store_derived_timelines
# ---------------------------------------------------------------------------


class TestStoreDerivedTimelines:
    @pytest.fixture
    def cache(self) -> MockCacheProvider:
        return MockCacheProvider()

    def test_stores_entry_in_cache(self, cache: MockCacheProvider) -> None:
        """store_derived_timelines writes a DerivedTimelineCacheEntry."""
        timeline_data = [_serialize_timeline(_make_timeline())]
        store_derived_timelines(
            project_gid="proj1",
            classifier_name="offer",
            timeline_data=timeline_data,
            cache=cache,
            entity_count=100,
            cache_hits=90,
            cache_misses=10,
            computation_duration_ms=1234.5,
        )

        key = make_derived_timeline_key("proj1", "offer")
        stored = cache._cache.get(f"{EntryType.DERIVED_TIMELINE.value}:{key}")
        assert stored is not None
        assert isinstance(stored, DerivedTimelineCacheEntry)
        assert stored.classifier_name == "offer"
        assert stored.source_entity_count == 100
        assert stored.source_cache_hits == 90
        assert stored.source_cache_misses == 10
        assert stored.computation_duration_ms == 1234.5
        assert stored.ttl == _DERIVED_TIMELINE_TTL
        assert stored.project_gid == "proj1"

    def test_stores_timeline_data_in_data_dict(self, cache: MockCacheProvider) -> None:
        """Data field wraps timelines under 'timelines' key."""
        timeline_data = [{"offer_gid": "o1"}]
        store_derived_timelines(
            project_gid="proj1",
            classifier_name="offer",
            timeline_data=timeline_data,
            cache=cache,
        )

        key = make_derived_timeline_key("proj1", "offer")
        stored = cache._cache[f"{EntryType.DERIVED_TIMELINE.value}:{key}"]
        assert stored.data == {"timelines": [{"offer_gid": "o1"}]}

    def test_metadata_has_computed_at(self, cache: MockCacheProvider) -> None:
        """Metadata includes computed_at ISO timestamp."""
        store_derived_timelines(
            project_gid="proj1",
            classifier_name="offer",
            timeline_data=[],
            cache=cache,
        )

        key = make_derived_timeline_key("proj1", "offer")
        stored = cache._cache[f"{EntryType.DERIVED_TIMELINE.value}:{key}"]
        assert "computed_at" in stored.metadata
        # Should be parseable as ISO datetime
        datetime.fromisoformat(stored.metadata["computed_at"])


# ---------------------------------------------------------------------------
# DerivedTimelineCacheEntry to_dict / from_dict round-trip
# ---------------------------------------------------------------------------


class TestDerivedTimelineCacheEntryRoundTrip:
    def test_to_dict_includes_subclass_fields(self) -> None:
        now = datetime.now(UTC)
        entry = DerivedTimelineCacheEntry(
            key="timeline:proj1:offer",
            data={"timelines": []},
            entry_type=EntryType.DERIVED_TIMELINE,
            version=now,
            cached_at=now,
            ttl=300,
            project_gid="proj1",
            metadata={},
            classifier_name="offer",
            source_entity_count=100,
            source_cache_hits=90,
            source_cache_misses=10,
            computation_duration_ms=500.0,
        )

        d = entry.to_dict()
        assert d["_type"] == "derived_timeline"
        assert d["_class"] == "DerivedTimelineCacheEntry"
        assert d["classifier_name"] == "offer"
        assert d["source_entity_count"] == 100
        assert d["source_cache_hits"] == 90
        assert d["source_cache_misses"] == 10
        assert d["computation_duration_ms"] == 500.0

    def test_from_dict_dispatches_to_subclass(self) -> None:
        now = datetime.now(UTC)
        d = {
            "_type": "derived_timeline",
            "key": "timeline:proj1:offer",
            "data": {"timelines": []},
            "entry_type": "derived_timeline",
            "version": now.isoformat(),
            "cached_at": now.isoformat(),
            "ttl": 300,
            "project_gid": "proj1",
            "metadata": {},
            "classifier_name": "offer",
            "source_entity_count": 50,
            "source_cache_hits": 45,
            "source_cache_misses": 5,
            "computation_duration_ms": 250.0,
        }

        entry = CacheEntry.from_dict(d)
        assert type(entry) is DerivedTimelineCacheEntry
        assert entry.classifier_name == "offer"
        assert entry.source_entity_count == 50

    def test_full_round_trip(self) -> None:
        now = datetime.now(UTC)
        original = DerivedTimelineCacheEntry(
            key="timeline:proj1:unit",
            data={"timelines": [{"offer_gid": "o1"}]},
            entry_type=EntryType.DERIVED_TIMELINE,
            version=now,
            cached_at=now,
            ttl=300,
            project_gid="proj1",
            metadata={"computed_at": now.isoformat()},
            classifier_name="unit",
            source_entity_count=200,
            source_cache_hits=180,
            source_cache_misses=20,
            computation_duration_ms=1000.0,
        )

        d = original.to_dict()
        restored = CacheEntry.from_dict(d)

        assert type(restored) is DerivedTimelineCacheEntry
        assert restored.key == original.key
        assert restored.entry_type == original.entry_type
        assert restored.classifier_name == original.classifier_name
        assert restored.source_entity_count == original.source_entity_count
        assert restored.source_cache_hits == original.source_cache_hits
        assert restored.source_cache_misses == original.source_cache_misses
        assert restored.computation_duration_ms == original.computation_duration_ms
        assert restored.data == original.data
        assert restored.project_gid == original.project_gid


# ---------------------------------------------------------------------------
# __init_subclass__ Registration
# ---------------------------------------------------------------------------


class TestDerivedTimelineRegistration:
    def test_registered_in_type_registry(self) -> None:
        """DERIVED_TIMELINE is registered via __init_subclass__."""
        assert (
            CacheEntry._type_registry[EntryType.DERIVED_TIMELINE.value]
            is DerivedTimelineCacheEntry
        )
