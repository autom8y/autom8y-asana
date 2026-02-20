"""Section timeline domain models for offer activity tracking.

Per TDD-SECTION-TIMELINE-001: Frozen dataclasses for domain logic,
Pydantic model for API response serialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from autom8_asana.models.business.activity import AccountActivity


@dataclass(frozen=True)
class SectionInterval:
    """A time interval where an offer occupied a specific Asana section.

    Per AC-2.1: Each interval has a start, optional end, section name,
    and classification.

    Attributes:
        section_name: Asana section name (e.g., "ACTIVE", "STAGING").
        classification: AccountActivity category, or None if the section
            is unregistered in OFFER_CLASSIFIER.
        entered_at: UTC datetime when the offer entered this section.
        exited_at: UTC datetime when the offer left this section,
            or None if this is the current (open) interval.
    """

    section_name: str
    classification: AccountActivity | None
    entered_at: datetime
    exited_at: datetime | None


@dataclass(frozen=True)
class SectionTimeline:
    """Complete section history for a single offer.

    Per PRD Section 6: Aggregates intervals and computes day counts.

    Attributes:
        offer_gid: Asana task GID of the offer.
        office_phone: Office phone custom field value (may be None).
        offer_id: Internal business offer ID (Offer ID custom field), or None.
        intervals: Chronologically ordered tuple of SectionInterval values.
        task_created_at: Task creation timestamp (used for imputation).
        story_count: Number of section_changed stories after filtering.
    """

    offer_gid: str
    office_phone: str | None
    offer_id: str | None
    intervals: tuple[SectionInterval, ...]
    task_created_at: datetime | None
    story_count: int

    def active_days_in_period(self, start: date, end: date) -> int:
        """Count unique calendar dates with ACTIVE classification overlap.

        Per AC-4.1: Counts days where ANY interval with
        classification == ACTIVE overlaps [start, end] inclusive.
        Per AC-4.4: Uses set[date] for deduplication.
        Per AC-4.5: Open intervals extend to period_end.

        Args:
            start: Period start date (inclusive).
            end: Period end date (inclusive).

        Returns:
            Number of unique active days in period.
        """
        from autom8_asana.models.business.activity import AccountActivity

        return self._count_days_for_classifications(
            start, end, frozenset({AccountActivity.ACTIVE})
        )

    def billable_days_in_period(self, start: date, end: date) -> int:
        """Count unique calendar dates with ACTIVE or ACTIVATING overlap.

        Per AC-4.2: Counts days where ANY interval with
        classification in {ACTIVE, ACTIVATING} overlaps [start, end].
        Per AC-4.4: Uses set[date] for deduplication.
        Per AC-4.5: Open intervals extend to period_end.

        Args:
            start: Period start date (inclusive).
            end: Period end date (inclusive).

        Returns:
            Number of unique billable days in period.
        """
        from autom8_asana.models.business.activity import AccountActivity

        return self._count_days_for_classifications(
            start, end, frozenset({AccountActivity.ACTIVE, AccountActivity.ACTIVATING})
        )

    def _count_days_for_classifications(
        self,
        start: date,
        end: date,
        classifications: frozenset[AccountActivity],
    ) -> int:
        """Shared implementation for day counting with set[date] dedup.

        Per AC-2.4: Intervals with classification=None are excluded.
        Per AC-4.4: set[date] handles multi-interval same-day overlaps.
        Per AC-4.5: Open intervals (exited_at=None) extend to period_end.

        Args:
            start: Period start date (inclusive).
            end: Period end date (inclusive).
            classifications: Set of AccountActivity values that qualify.

        Returns:
            Count of unique calendar dates in [start, end] with qualifying overlap.
        """
        days: set[date] = set()

        for interval in self.intervals:
            # AC-2.4: Skip intervals with unknown classification
            if interval.classification is None:
                continue
            if interval.classification not in classifications:
                continue

            # Determine interval date range
            interval_start = interval.entered_at.date()
            # AC-4.5: Open intervals extend to period_end.
            # Closed intervals: the transition day (exited_at.date()) belongs to
            # the section being entered, not the section being exited. Subtract 1
            # day so the last counted date is the day before the transition.
            # (Stakeholder decision 2026-02-19: transition day → new section.)
            if interval.exited_at is None:
                interval_end = end
            else:
                interval_end = interval.exited_at.date() - timedelta(days=1)

            # Clamp to query period
            clamped_start = max(interval_start, start)
            clamped_end = min(interval_end, end)

            # Collect qualifying dates
            current = clamped_start
            while current <= clamped_end:
                days.add(current)
                current += timedelta(days=1)

        return len(days)


class OfferTimelineEntry(BaseModel):
    """API response model for a single offer's timeline summary.

    Per AC-5.2: Contains offer_gid, office_phone, and both day counts.

    Attributes:
        offer_gid: Asana task GID of the offer.
        office_phone: Office phone custom field value (null if not set).
        offer_id: Internal business offer ID (null if not set).
        active_section_days: Calendar days in ACTIVE sections during period.
        billable_section_days: Calendar days in ACTIVE or ACTIVATING
            sections during period.
    """

    offer_gid: str = Field(..., description="Asana task GID")
    office_phone: str | None = Field(
        default=None, description="Office phone custom field"
    )
    offer_id: str | None = Field(
        default=None,
        description="Internal business offer ID (Offer ID custom field)",
    )
    active_section_days: int = Field(..., ge=0, description="Days in ACTIVE sections")
    billable_section_days: int = Field(
        ..., ge=0, description="Days in ACTIVE or ACTIVATING sections"
    )
    current_section: str | None = Field(
        default=None,
        description="Current Asana section name (from last interval)",
    )
    current_classification: str | None = Field(
        default=None,
        description="Classification of current section (e.g., active, activating)",
    )

    model_config = {"extra": "forbid"}
