"""Tests for query/temporal.py: TemporalFilter matching and date parsing."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.business.section_timeline import (
    SectionInterval,
    SectionTimeline,
)
from autom8_asana.query.temporal import TemporalFilter, parse_date_or_relative

# ---------------------------------------------------------------------------
# Test fixtures (pure data, no mocks)
# ---------------------------------------------------------------------------


def _make_timeline(
    offer_gid: str = "100",
    intervals: tuple[SectionInterval, ...] = (),
) -> SectionTimeline:
    """Build a SectionTimeline with sensible defaults."""
    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone="+15551234567",
        offer_id="OFR-001",
        intervals=intervals,
        task_created_at=datetime(2024, 6, 1, tzinfo=UTC),
        story_count=len(intervals),
    )


def _make_interval(
    section_name: str,
    classification: AccountActivity | None,
    entered_at: datetime,
    exited_at: datetime | None = None,
) -> SectionInterval:
    """Build a SectionInterval."""
    return SectionInterval(
        section_name=section_name,
        classification=classification,
        entered_at=entered_at,
        exited_at=exited_at,
    )


# Reusable timeline: Sales Process -> ACTIVATING -> ACTIVE (open)
SAMPLE_TIMELINE = _make_timeline(
    offer_gid="200",
    intervals=(
        _make_interval(
            "Sales Process",
            AccountActivity.IGNORED,
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 2, 1, tzinfo=UTC),
        ),
        _make_interval(
            "ACTIVATING",
            AccountActivity.ACTIVATING,
            datetime(2025, 2, 1, tzinfo=UTC),
            datetime(2025, 3, 1, tzinfo=UTC),
        ),
        _make_interval(
            "ACTIVE",
            AccountActivity.ACTIVE,
            datetime(2025, 3, 1, tzinfo=UTC),
            None,  # open interval
        ),
    ),
)


# ---------------------------------------------------------------------------
# TemporalFilter.matches() tests
# ---------------------------------------------------------------------------


class TestFilterMovedToSection:
    """Test moved_to matching against section name."""

    def test_matches_exact_section(self) -> None:
        f = TemporalFilter(moved_to="ACTIVE")
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_case_insensitive(self) -> None:
        f = TemporalFilter(moved_to="active")
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_no_match(self) -> None:
        f = TemporalFilter(moved_to="NONEXISTENT")
        assert f.matches(SAMPLE_TIMELINE) is False


class TestFilterMovedToClassification:
    """Test moved_to matching against classification value."""

    def test_matches_classification_value(self) -> None:
        f = TemporalFilter(moved_to="activating")
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_matches_ignored_classification(self) -> None:
        f = TemporalFilter(moved_to="ignored")
        assert f.matches(SAMPLE_TIMELINE) is True


class TestFilterSince:
    """Test since date filtering on entered_at."""

    def test_includes_on_date(self) -> None:
        f = TemporalFilter(since=date(2025, 3, 1))
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_includes_after_date(self) -> None:
        f = TemporalFilter(since=date(2025, 2, 15))
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_excludes_all_before(self) -> None:
        """Since after all entered_at dates excludes the timeline."""
        f = TemporalFilter(since=date(2025, 4, 1))
        assert f.matches(SAMPLE_TIMELINE) is False


class TestFilterUntil:
    """Test until date filtering on entered_at."""

    def test_includes_on_date(self) -> None:
        f = TemporalFilter(until=date(2025, 1, 1))
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_excludes_all_after(self) -> None:
        """Until before all entered_at dates excludes the timeline."""
        f = TemporalFilter(until=date(2024, 12, 31))
        assert f.matches(SAMPLE_TIMELINE) is False


class TestFilterMovedFrom:
    """Test moved_from matching against the previous interval."""

    def test_matches_previous_section(self) -> None:
        """ACTIVATING follows Sales Process -> moved_from 'Sales Process' matches."""
        f = TemporalFilter(moved_to="ACTIVATING", moved_from="Sales Process")
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_matches_previous_classification(self) -> None:
        """ACTIVE follows ACTIVATING -> moved_from 'activating' (classification) matches."""
        f = TemporalFilter(moved_to="ACTIVE", moved_from="activating")
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_no_previous_for_first_interval(self) -> None:
        """First interval has no predecessor -> moved_from never matches."""
        f = TemporalFilter(moved_to="Sales Process", moved_from="ANYTHING")
        assert f.matches(SAMPLE_TIMELINE) is False

    def test_wrong_previous(self) -> None:
        """moved_from does not match the actual predecessor."""
        f = TemporalFilter(moved_to="ACTIVE", moved_from="Sales Process")
        # ACTIVE's predecessor is ACTIVATING, not Sales Process
        assert f.matches(SAMPLE_TIMELINE) is False


class TestFilterCombined:
    """Test combining multiple filter criteria."""

    def test_moved_from_moved_to_since(self) -> None:
        f = TemporalFilter(
            moved_from="ACTIVATING",
            moved_to="ACTIVE",
            since=date(2025, 3, 1),
        )
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_combined_no_match(self) -> None:
        """All criteria must match the same interval."""
        f = TemporalFilter(
            moved_to="ACTIVE",
            since=date(2025, 3, 1),
            until=date(2025, 2, 28),  # contradicts since
        )
        assert f.matches(SAMPLE_TIMELINE) is False

    def test_combined_moved_from_wrong_predecessor(self) -> None:
        f = TemporalFilter(
            moved_from="Sales Process",
            moved_to="ACTIVE",
            since=date(2025, 1, 1),
        )
        # ACTIVE predecessor is ACTIVATING, not Sales Process
        assert f.matches(SAMPLE_TIMELINE) is False


class TestFilterEmpty:
    """Test that an empty filter matches everything."""

    def test_matches_any_timeline(self) -> None:
        f = TemporalFilter()
        assert f.matches(SAMPLE_TIMELINE) is True

    def test_matches_single_interval(self) -> None:
        tl = _make_timeline(
            intervals=(
                _make_interval(
                    "STAGING",
                    None,
                    datetime(2025, 6, 1, tzinfo=UTC),
                ),
            ),
        )
        f = TemporalFilter()
        assert f.matches(tl) is True

    def test_no_match_empty_timeline(self) -> None:
        """Empty timeline has no intervals to match."""
        tl = _make_timeline(intervals=())
        f = TemporalFilter()
        assert f.matches(tl) is False


# ---------------------------------------------------------------------------
# Limb (ii): imputed intervals must never satisfy a transition query.
#
# DEFECT-temporal-filter-imputed-false-move-2026-08-12: an offer with zero
# observed stories is given ONE synthesised ("imputed") interval whose
# entered_at is the offer's *creation* timestamp and whose classification is
# the offer's *current* one (story_count == 0). Every TemporalFilter criterion
# is transition-semantics (moved_to = entered, since/until = the transition
# timestamp, moved_from = predecessor), so a non-empty filter that matches the
# imputed interval reports a NEVER-MOVED offer as HAVING MOVED.
#
# Two-sided teeth (discriminating-canary doctrine §2.3): the imputed and the
# genuine timelines below are byte-identical in interval shape — a single
# ACTIVE interval entered on the weekend. ONLY story_count differs (0 vs 1).
# The filter result must flip on that discriminator alone: imputed → rejected,
# genuine → matched. A fixture matching on shape rather than substance cannot
# do that.
# ---------------------------------------------------------------------------


# Saturday of a weekend window. The natural query is "what moved into ACTIVE
# between Saturday and Sunday" — moved_to + since/until, moved_from OMITTED.
_WEEKEND_SATURDAY = datetime(2025, 6, 7, tzinfo=UTC)
_WEEKEND_SINCE = date(2025, 6, 7)
_WEEKEND_UNTIL = date(2025, 6, 8)


def _single_active_interval() -> tuple[SectionInterval, ...]:
    """One open ACTIVE interval entered on the weekend Saturday."""
    return (
        _make_interval("ACTIVE", AccountActivity.ACTIVE, _WEEKEND_SATURDAY, None),
    )


def _imputed_timeline() -> SectionTimeline:
    """A never-moved offer: zero observed stories, one imputed interval.

    entered_at == task_created_at (the weekend Saturday), classification ==
    the offer's current one, story_count == 0. This is exactly what
    ``_build_imputed_interval`` produces for an offer with no cached stories.
    """
    return SectionTimeline(
        offer_gid="imputed-1",
        office_phone="+15550000001",
        offer_id="OFR-IMP",
        intervals=_single_active_interval(),
        task_created_at=_WEEKEND_SATURDAY,
        story_count=0,  # <-- the imputation discriminator
    )


def _genuine_first_move_timeline() -> SectionTimeline:
    """A genuinely-observed first move into ACTIVE on the weekend Saturday.

    Byte-identical interval shape to ``_imputed_timeline`` — the ONLY
    difference is story_count > 0 (a real section_changed story was observed).
    intervals[0] is therefore a *genuine first move*.
    """
    return SectionTimeline(
        offer_gid="genuine-1",
        office_phone="+15550000002",
        offer_id="OFR-GEN",
        intervals=_single_active_interval(),
        task_created_at=_WEEKEND_SATURDAY,
        story_count=1,  # <-- one observed story: a real move
    )


class TestImputedIntervalNotAMove:
    """Limb (ii) two-sided teeth: the imputation discriminator flips the match."""

    def test_imputed_interval_rejected_by_weekend_move_query(self) -> None:
        """NEGATIVE CONTROL (RED-before): a never-moved offer must NOT match.

        The natural weekend shape: moved_to + since/until, moved_from OMITTED.
        Pre-fix this returns True (the false positive the DEFECT describes);
        post-fix it must return False.
        """
        f = TemporalFilter(
            moved_to="ACTIVE",
            since=_WEEKEND_SINCE,
            until=_WEEKEND_UNTIL,
            # moved_from intentionally OMITTED — the natural query shape.
        )
        assert f.matches(_imputed_timeline()) is False

    def test_genuine_move_still_matches_same_query(self) -> None:
        """POSITIVE CONTROL: a genuine move under the SAME filter must match.

        Same interval shape as the imputed case; only story_count differs.
        The fix must bite ONLY on imputation, never on genuine moves.
        """
        f = TemporalFilter(
            moved_to="ACTIVE",
            since=_WEEKEND_SINCE,
            until=_WEEKEND_UNTIL,
        )
        assert f.matches(_genuine_first_move_timeline()) is True

    def test_imputed_interval_still_matches_empty_filter(self) -> None:
        """An EMPTY filter matches every timeline, imputed included (unchanged)."""
        assert TemporalFilter().matches(_imputed_timeline()) is True

    def test_imputed_rejected_by_moved_to_only(self) -> None:
        """moved_to alone is transition-semantics — imputed must not match."""
        assert TemporalFilter(moved_to="ACTIVE").matches(_imputed_timeline()) is False

    def test_imputed_rejected_by_since_only(self) -> None:
        """since alone consults entered_at (a transition) — imputed must not match."""
        assert TemporalFilter(since=_WEEKEND_SINCE).matches(_imputed_timeline()) is False

    def test_imputed_rejected_by_until_only(self) -> None:
        """until alone consults entered_at (a transition) — imputed must not match."""
        assert TemporalFilter(until=_WEEKEND_UNTIL).matches(_imputed_timeline()) is False

    def test_genuine_move_matches_since_only(self) -> None:
        """POSITIVE CONTROL for since-only: genuine move in window still matches."""
        assert TemporalFilter(since=_WEEKEND_SINCE).matches(
            _genuine_first_move_timeline()
        ) is True

    def test_moved_from_workaround_drops_genuine_first_move(self) -> None:
        """Exit criterion 2: prove the moved_from workaround is sign-inverted.

        The workaround engages the ``idx == 0`` guard, which drops EVERY
        offer's genuine first move (``_build_intervals_from_stories`` synthesises
        no pre-first interval). The correct fix (this sprint) keeps the genuine
        first move while rejecting the imputed one — the workaround does the
        opposite of both.
        """
        genuine = _genuine_first_move_timeline()

        # The correct fix: genuine first move MATCHES without needing moved_from.
        assert TemporalFilter(
            moved_to="ACTIVE",
            since=_WEEKEND_SINCE,
            until=_WEEKEND_UNTIL,
        ).matches(genuine) is True

        # The rejected workaround: adding moved_from drops the genuine first
        # move (idx == 0 -> no predecessor -> False). This is the sign
        # inversion the sprint must NOT ship.
        assert TemporalFilter(
            moved_to="ACTIVE",
            moved_from="STAGING",
            since=_WEEKEND_SINCE,
            until=_WEEKEND_UNTIL,
        ).matches(genuine) is False


# ---------------------------------------------------------------------------
# parse_date_or_relative() tests
# ---------------------------------------------------------------------------


class TestParseDateIso:
    """Test ISO date parsing."""

    def test_standard_iso(self) -> None:
        assert parse_date_or_relative("2025-01-01") == date(2025, 1, 1)

    def test_with_whitespace(self) -> None:
        assert parse_date_or_relative("  2025-06-15  ") == date(2025, 6, 15)


class TestParseDateRelativeDays:
    """Test relative day parsing."""

    def test_30_days(self) -> None:
        result = parse_date_or_relative("30d")
        expected = date.today() - timedelta(days=30)
        assert result == expected

    def test_1_day(self) -> None:
        result = parse_date_or_relative("1d")
        expected = date.today() - timedelta(days=1)
        assert result == expected


class TestParseDateRelativeWeeks:
    """Test relative week parsing."""

    def test_4_weeks(self) -> None:
        result = parse_date_or_relative("4w")
        expected = date.today() - timedelta(days=28)
        assert result == expected

    def test_1_week(self) -> None:
        result = parse_date_or_relative("1w")
        expected = date.today() - timedelta(days=7)
        assert result == expected


class TestParseDateInvalid:
    """Test error handling for invalid date strings."""

    def test_garbage_string(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_date_or_relative("not-a-date")

    def test_partial_iso(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_date_or_relative("2025-13")

    def test_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_date_or_relative("")

    def test_relative_missing_unit(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_date_or_relative("30")
