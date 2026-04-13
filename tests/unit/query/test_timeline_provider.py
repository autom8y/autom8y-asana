"""Tests for query/timeline_provider.py: TimelineStore parquet cache."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from autom8_asana.models.business.activity import AccountActivity

if TYPE_CHECKING:
    import pytest
from autom8_asana.models.business.section_timeline import (
    SectionInterval,
    SectionTimeline,
)
from autom8_asana.query.timeline_provider import TimelineStore

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_interval(
    section_name: str,
    classification: AccountActivity | None,
    entered_at: datetime,
    exited_at: datetime | None = None,
) -> SectionInterval:
    return SectionInterval(
        section_name=section_name,
        classification=classification,
        entered_at=entered_at,
        exited_at=exited_at,
    )


def _sample_timelines() -> list[SectionTimeline]:
    """Two timelines with distinct intervals for roundtrip testing."""
    return [
        SectionTimeline(
            offer_gid="100",
            office_phone="+15551234567",
            offer_id="OFR-001",
            intervals=(
                _make_interval(
                    "Sales Process",
                    AccountActivity.IGNORED,
                    datetime(2025, 1, 1, tzinfo=UTC),
                    datetime(2025, 2, 1, tzinfo=UTC),
                ),
                _make_interval(
                    "ACTIVE",
                    AccountActivity.ACTIVE,
                    datetime(2025, 2, 1, tzinfo=UTC),
                    None,
                ),
            ),
            task_created_at=datetime(2024, 12, 1, tzinfo=UTC),
            story_count=5,
        ),
        SectionTimeline(
            offer_gid="200",
            office_phone=None,
            offer_id=None,
            intervals=(
                _make_interval(
                    "ACTIVATING",
                    AccountActivity.ACTIVATING,
                    datetime(2025, 3, 15, tzinfo=UTC),
                    None,
                ),
            ),
            task_created_at=None,
            story_count=1,
        ),
    ]


# ---------------------------------------------------------------------------
# Roundtrip tests
# ---------------------------------------------------------------------------


class TestSaveAndLoadRoundtrip:
    """Verify save + load produces equivalent SectionTimeline objects."""

    def test_roundtrip_preserves_data(self, tmp_path: pytest.TempPathFactory) -> None:
        store = TimelineStore(cache_dir=tmp_path)
        originals = _sample_timelines()

        path = store.save("proj_123", originals)
        assert path.exists()
        assert path.suffix == ".parquet"

        loaded = store.load("proj_123")
        assert loaded is not None
        assert len(loaded) == len(originals)

        # Sort both by offer_gid for stable comparison
        originals_sorted = sorted(originals, key=lambda t: t.offer_gid)
        loaded_sorted = sorted(loaded, key=lambda t: t.offer_gid)

        for orig, reloaded in zip(originals_sorted, loaded_sorted):
            assert reloaded.offer_gid == orig.offer_gid
            assert reloaded.office_phone == orig.office_phone
            assert reloaded.offer_id == orig.offer_id
            assert reloaded.story_count == orig.story_count
            assert len(reloaded.intervals) == len(orig.intervals)

            for orig_iv, reloaded_iv in zip(orig.intervals, reloaded.intervals):
                assert reloaded_iv.section_name == orig_iv.section_name
                assert reloaded_iv.classification == orig_iv.classification
                assert reloaded_iv.exited_at == orig_iv.exited_at
                # entered_at comparison: allow microsecond truncation from parquet
                assert abs((reloaded_iv.entered_at - orig_iv.entered_at).total_seconds()) < 1.0

    def test_roundtrip_with_nullable_fields(self, tmp_path: pytest.TempPathFactory) -> None:
        """Verify None values survive the parquet roundtrip."""
        store = TimelineStore(cache_dir=tmp_path)
        timelines = [
            SectionTimeline(
                offer_gid="300",
                office_phone=None,
                offer_id=None,
                intervals=(
                    _make_interval(
                        "STAGING",
                        None,  # No classification
                        datetime(2025, 5, 1, tzinfo=UTC),
                        None,  # Open interval
                    ),
                ),
                task_created_at=None,
                story_count=0,
            ),
        ]

        store.save("proj_null", timelines)
        loaded = store.load("proj_null")
        assert loaded is not None
        assert len(loaded) == 1

        tl = loaded[0]
        assert tl.office_phone is None
        assert tl.offer_id is None
        assert tl.task_created_at is None
        assert tl.intervals[0].classification is None
        assert tl.intervals[0].exited_at is None

    def test_roundtrip_empty_list(self, tmp_path: pytest.TempPathFactory) -> None:
        """Empty timeline list saves and loads as empty."""
        store = TimelineStore(cache_dir=tmp_path)
        store.save("proj_empty", [])
        loaded = store.load("proj_empty")
        assert loaded is not None
        assert loaded == []


# ---------------------------------------------------------------------------
# Load missing
# ---------------------------------------------------------------------------


class TestLoadMissing:
    """Verify behavior when no cache exists."""

    def test_returns_none(self, tmp_path: pytest.TempPathFactory) -> None:
        store = TimelineStore(cache_dir=tmp_path)
        result = store.load("nonexistent_project")
        assert result is None


# ---------------------------------------------------------------------------
# Age
# ---------------------------------------------------------------------------


class TestAge:
    """Verify cache age reporting."""

    def test_returns_timedelta(self, tmp_path: pytest.TempPathFactory) -> None:
        store = TimelineStore(cache_dir=tmp_path)
        store.save("proj_age", _sample_timelines())

        age = store.age("proj_age")
        assert age is not None
        # File was just created, age should be very small
        assert age < timedelta(seconds=10)

    def test_returns_none_when_missing(self, tmp_path: pytest.TempPathFactory) -> None:
        store = TimelineStore(cache_dir=tmp_path)
        assert store.age("nonexistent") is None

    def test_age_increases_over_time(self, tmp_path: pytest.TempPathFactory) -> None:
        """Verify age reflects real elapsed time."""
        store = TimelineStore(cache_dir=tmp_path)
        store.save("proj_aging", _sample_timelines())

        age1 = store.age("proj_aging")
        assert age1 is not None
        # Sleep briefly to see age increase
        time.sleep(0.1)
        age2 = store.age("proj_aging")
        assert age2 is not None
        assert age2 >= age1


# ---------------------------------------------------------------------------
# Cache directory creation
# ---------------------------------------------------------------------------


class TestCacheDirectory:
    """Verify cache_dir is created on save."""

    def test_creates_nested_dirs(self, tmp_path: pytest.TempPathFactory) -> None:
        nested = tmp_path / "deep" / "nested" / "cache"
        store = TimelineStore(cache_dir=nested)
        store.save("proj_nested", _sample_timelines())
        assert nested.exists()
        assert (nested / "proj_nested.parquet").exists()
