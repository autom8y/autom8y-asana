"""Unit tests for section timeline domain models.

Per TDD-SECTION-TIMELINE-001 Section 13.1: Tests for SectionInterval,
SectionTimeline, and OfferTimelineEntry. Pure value-object tests with
no mocking required.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timezone

import pytest

from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.business.section_timeline import (
    OfferTimelineEntry,
    SectionInterval,
    SectionTimeline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    """Create a UTC datetime for test data."""
    return datetime(year, month, day, hour, tzinfo=UTC)


def _timeline(
    intervals: tuple[SectionInterval, ...],
    offer_gid: str = "1234",
    office_phone: str | None = None,
    offer_id: str | None = None,
    task_created_at: datetime | None = None,
    story_count: int = 0,
) -> SectionTimeline:
    """Build a SectionTimeline with sensible defaults."""
    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        offer_id=offer_id,
        intervals=intervals,
        task_created_at=task_created_at,
        story_count=story_count,
    )


# ---------------------------------------------------------------------------
# Frozen dataclass immutability
# ---------------------------------------------------------------------------


class TestSectionIntervalFrozen:
    def test_section_interval_frozen(self) -> None:
        """Verify SectionInterval is immutable."""
        interval = SectionInterval(
            section_name="ACTIVE",
            classification=AccountActivity.ACTIVE,
            entered_at=_utc(2025, 1, 1),
            exited_at=None,
        )
        with pytest.raises(FrozenInstanceError):
            interval.section_name = "OTHER"  # type: ignore[misc]


class TestSectionTimelineFrozen:
    def test_section_timeline_frozen(self) -> None:
        """Verify SectionTimeline is immutable."""
        tl = _timeline(intervals=())
        with pytest.raises(FrozenInstanceError):
            tl.offer_gid = "9999"  # type: ignore[misc]

    def test_offer_id_accessible(self) -> None:
        """SC-4: offer_id field is accessible on SectionTimeline."""
        tl = _timeline(intervals=(), offer_id="OFR-1234")
        assert tl.offer_id == "OFR-1234"

    def test_offer_id_none(self) -> None:
        """SC-4: offer_id=None is valid."""
        tl = _timeline(intervals=(), offer_id=None)
        assert tl.offer_id is None

    def test_offer_id_frozen(self) -> None:
        """SC-4: offer_id is immutable (frozen dataclass)."""
        tl = _timeline(intervals=(), offer_id="OFR-1234")
        with pytest.raises(FrozenInstanceError):
            tl.offer_id = "OFR-9999"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# active_days_in_period
# ---------------------------------------------------------------------------


class TestActiveDaysInPeriod:
    def test_single_active_interval(self) -> None:
        """FR-4, AC-4.1: Single ACTIVE interval spanning full period."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=_utc(2025, 1, 11),
                ),
            ),
        )
        # Period 2025-01-01 through 2025-01-10 (10 days)
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 10

    def test_excludes_activating(self) -> None:
        """AC-4.1: ACTIVATING interval not counted in active_days."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVATING",
                    classification=AccountActivity.ACTIVATING,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 0


# ---------------------------------------------------------------------------
# billable_days_in_period
# ---------------------------------------------------------------------------


class TestBillableDaysInPeriod:
    def test_includes_active_and_activating(self) -> None:
        """AC-4.2: Both ACTIVE and ACTIVATING counted."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVATING",
                    classification=AccountActivity.ACTIVATING,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=_utc(2025, 1, 6),
                ),
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 6),
                    exited_at=_utc(2025, 1, 11),
                ),
            ),
        )
        # Jan 1-5 ACTIVATING (5 days) + Jan 6-10 ACTIVE (5 days) = 10 days
        assert tl.billable_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 10

    def test_excludes_inactive(self) -> None:
        """AC-4.2: INACTIVE interval not counted."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="INACTIVE",
                    classification=AccountActivity.INACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        assert tl.billable_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestDayCountingEdgeCases:
    def test_none_classification_excluded(self) -> None:
        """AC-2.4: Intervals with classification=None excluded."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="UNKNOWN_SECTION",
                    classification=None,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 0
        assert tl.billable_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 0

    def test_open_interval_extends_to_period_end(self) -> None:
        """AC-4.5: exited_at=None treated as period_end."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 5),
                    exited_at=None,
                ),
            ),
        )
        # Open interval from Jan 5. Period is Jan 1-10.
        # Should count Jan 5-10 = 6 days (clamped start to entered_at).
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 6

    def test_single_day_period(self) -> None:
        """EC-7: period_start == period_end returns 0 or 1."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 5),
                    exited_at=None,
                ),
            ),
        )
        # Active on Jan 5 -> 1 day
        assert tl.active_days_in_period(date(2025, 1, 5), date(2025, 1, 5)) == 1
        # Not active on Jan 4 -> 0 days
        assert tl.active_days_in_period(date(2025, 1, 4), date(2025, 1, 4)) == 0

    def test_multi_interval_same_day_dedup(self) -> None:
        """AC-4.4: ACTIVE->ACTIVATING on same day counts once for billable."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 5, 8),
                    exited_at=_utc(2025, 1, 5, 16),
                ),
                SectionInterval(
                    section_name="ACTIVATING",
                    classification=AccountActivity.ACTIVATING,
                    entered_at=_utc(2025, 1, 5, 16),
                    exited_at=None,
                ),
            ),
        )
        # Both intervals touch Jan 5. Billable should be 1, not 2.
        assert tl.billable_days_in_period(date(2025, 1, 5), date(2025, 1, 5)) == 1

    def test_future_period_with_open_interval(self) -> None:
        """EC-9: Future dates counted for open intervals."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=None,
                ),
            ),
        )
        # Future period: Feb 1-Feb 10 (10 days)
        assert tl.active_days_in_period(date(2025, 2, 1), date(2025, 2, 10)) == 10

    def test_inclusive_boundaries(self) -> None:
        """EC-10: Period start/end dates are inclusive.

        Interval exits on Jan 4 (transition day belongs to the new section),
        so the last ACTIVE day is Jan 3. Period Jan 1-3 should return 3 days,
        confirming period_end is inclusive.
        """
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=_utc(2025, 1, 4),  # transitions out Jan 4 → Jan 3 is last ACTIVE
                ),
            ),
        )
        # Interval covers Jan 1-3 (exited_at date Jan 4 excluded).
        # Period Jan 1-3: all 3 days are ACTIVE.
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 3)) == 3

    def test_offer_goes_inactive_mid_period(self) -> None:
        """EC-6: Transition day belongs to the new (entering) section.

        Per stakeholder decision 2026-02-19: the day of the section transition
        belongs exclusively to the section being entered. An offer that was
        ACTIVE from Jan 1 and transitioned to INACTIVE at Jan 6 00:00 has
        Jan 6 as an INACTIVE day. Active days = Jan 1-5 = 5.
        """
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2025, 1, 1),
                    exited_at=_utc(2025, 1, 6),
                ),
                SectionInterval(
                    section_name="INACTIVE",
                    classification=AccountActivity.INACTIVE,
                    entered_at=_utc(2025, 1, 6),
                    exited_at=None,
                ),
            ),
        )
        # exited_at Jan 6 → interval_end = Jan 5. ACTIVE days Jan 1-5 = 5.
        # Period Jan 1-10. Active days = 5.
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 5


# ---------------------------------------------------------------------------
# Imputed (never-moved) scenarios
# ---------------------------------------------------------------------------


class TestNeverMovedScenarios:
    def test_never_moved_active(self) -> None:
        """EC-1: Imputed ACTIVE -- full period length."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVE",
                    classification=AccountActivity.ACTIVE,
                    entered_at=_utc(2024, 6, 1),
                    exited_at=None,
                ),
            ),
            task_created_at=_utc(2024, 6, 1),
            story_count=0,
        )
        # Full period Jan 1-10 = 10 days (open interval extends to period_end)
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 10

    def test_never_moved_inactive(self) -> None:
        """EC-2: Imputed INACTIVE -- 0 days."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="INACTIVE",
                    classification=AccountActivity.INACTIVE,
                    entered_at=_utc(2024, 6, 1),
                    exited_at=None,
                ),
            ),
            task_created_at=_utc(2024, 6, 1),
            story_count=0,
        )
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 0
        assert tl.billable_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 0

    def test_never_moved_activating(self) -> None:
        """AC-3.5: Imputed ACTIVATING -- 0 active, full billable."""
        tl = _timeline(
            intervals=(
                SectionInterval(
                    section_name="ACTIVATING",
                    classification=AccountActivity.ACTIVATING,
                    entered_at=_utc(2024, 6, 1),
                    exited_at=None,
                ),
            ),
            task_created_at=_utc(2024, 6, 1),
            story_count=0,
        )
        assert tl.active_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 0
        assert tl.billable_days_in_period(date(2025, 1, 1), date(2025, 1, 10)) == 10


# ---------------------------------------------------------------------------
# OfferTimelineEntry (Pydantic response model)
# ---------------------------------------------------------------------------


class TestOfferTimelineEntry:
    def test_serialization(self) -> None:
        """API contract: Pydantic model serializes correctly."""
        entry = OfferTimelineEntry(
            offer_gid="1205925604226368",
            office_phone="+15550001000",
            active_section_days=7,
            billable_section_days=10,
        )
        data = entry.model_dump()
        assert data == {
            "offer_gid": "1205925604226368",
            "office_phone": "+15550001000",
            "offer_id": None,
            "active_section_days": 7,
            "billable_section_days": 10,
            "current_section": None,
            "current_classification": None,
        }

    def test_null_phone(self) -> None:
        """EC-5: office_phone: null in serialized output."""
        entry = OfferTimelineEntry(
            offer_gid="1234567890123456",
            office_phone=None,
            active_section_days=0,
            billable_section_days=3,
        )
        data = entry.model_dump()
        assert data["office_phone"] is None

    def test_current_section_fields_populated(self) -> None:
        """S-3: current_section and current_classification populate correctly."""
        entry = OfferTimelineEntry(
            offer_gid="1234567890123456",
            office_phone=None,
            active_section_days=5,
            billable_section_days=5,
            current_section="ACTIVE",
            current_classification="active",
        )
        data = entry.model_dump()
        assert data["current_section"] == "ACTIVE"
        assert data["current_classification"] == "active"

    def test_current_section_fields_default_none(self) -> None:
        """S-3: current_section and current_classification default to None."""
        entry = OfferTimelineEntry(
            offer_gid="1234567890123456",
            office_phone=None,
            active_section_days=0,
            billable_section_days=0,
        )
        assert entry.current_section is None
        assert entry.current_classification is None

    def test_current_classification_is_string_not_enum(self) -> None:
        """S-3: current_classification stores string value, not enum object."""
        entry = OfferTimelineEntry(
            offer_gid="1234567890123456",
            office_phone=None,
            active_section_days=5,
            billable_section_days=5,
            current_section="ACTIVATING",
            current_classification="activating",
        )
        assert isinstance(entry.current_classification, str)
        assert entry.current_classification == "activating"

    def test_offer_id_in_serialization(self) -> None:
        """SC-5: offer_id appears in model_dump() output."""
        entry = OfferTimelineEntry(
            offer_gid="1234567890123456",
            office_phone=None,
            offer_id="OFR-1234",
            active_section_days=5,
            billable_section_days=5,
        )
        data = entry.model_dump()
        assert data["offer_id"] == "OFR-1234"

    def test_offer_id_null_in_serialization(self) -> None:
        """SC-5: offer_id=None serializes as None."""
        entry = OfferTimelineEntry(
            offer_gid="1234567890123456",
            office_phone=None,
            active_section_days=0,
            billable_section_days=0,
        )
        data = entry.model_dump()
        assert data["offer_id"] is None

    def test_offer_id_default_none(self) -> None:
        """SC-5: offer_id defaults to None when not passed."""
        entry = OfferTimelineEntry(
            offer_gid="1234567890123456",
            office_phone=None,
            active_section_days=0,
            billable_section_days=0,
        )
        assert entry.offer_id is None

    def test_extra_fields_still_forbidden(self) -> None:
        """S-3: model_config extra=forbid still enforced with new fields."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            OfferTimelineEntry(
                offer_gid="1234567890123456",
                office_phone=None,
                active_section_days=0,
                billable_section_days=0,
                bogus_field="should fail",  # type: ignore[call-arg]
            )
