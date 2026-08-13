"""Temporal filtering for SectionTimeline queries.

Provides TemporalFilter for matching SectionTimeline intervals based on
section transitions (moved_to, moved_from) and date ranges (since, until).

Also includes parse_date_or_relative() for CLI-friendly date input that
accepts both ISO dates (2025-01-01) and relative durations (30d, 4w).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.business.section_timeline import (
        SectionInterval,
        SectionTimeline,
    )


@dataclass(frozen=True)
class TemporalFilter:
    """Filter for SectionTimeline queries.

    Matches timelines that have at least one interval satisfying all
    specified criteria:

    - moved_to: The interval enters this section name or classification.
    - moved_from: The previous interval was in this section or classification.
    - since: The transition (entered_at) happened on or after this date.
    - until: The transition (entered_at) happened on or before this date.

    An empty filter (all None) matches every timeline.
    """

    moved_to: str | None = None
    moved_from: str | None = None
    since: date | None = None
    until: date | None = None

    def _has_any_criterion(self) -> bool:
        """True if at least one transition criterion is specified.

        An empty filter (all None) is a "match every timeline" request and is
        NOT a transition query, so the imputed-interval guard below does not
        apply to it.
        """
        return any(
            criterion is not None
            for criterion in (self.moved_to, self.moved_from, self.since, self.until)
        )

    def matches(self, timeline: SectionTimeline) -> bool:
        """Check if any interval in the timeline matches all filter criteria."""
        return any(self._interval_matches(interval, timeline) for interval in timeline.intervals)

    def _interval_matches(self, interval: SectionInterval, timeline: SectionTimeline) -> bool:
        """Check if a single interval satisfies all filter criteria."""
        # Imputed-interval guard (DEFECT-temporal-filter-imputed-false-move-2026-08-12).
        # A timeline with story_count == 0 has no observed stories: its single
        # interval is SYNTHESISED from the offer's creation timestamp and current
        # classification (see section_timeline_service._build_imputed_interval).
        # That interval records "no move was observed", not "a move occurred".
        # Every criterion below is transition-semantics (moved_to = entered,
        # since/until = the transition's entered_at, moved_from = predecessor),
        # so any NON-EMPTY filter must reject an imputed interval — matching it
        # reports a never-moved offer as having moved. An empty filter still
        # matches (it is not a transition query); see _has_any_criterion.
        #
        # This is the correct fix, NOT the moved_from workaround: moved_from
        # engages the idx == 0 guard, which drops every offer's GENUINE first
        # move (there is no synthesised pre-first interval for story-derived
        # timelines). story_count discriminates imputed (0) from observed (>0),
        # so genuine first moves are preserved.
        if timeline.story_count == 0 and self._has_any_criterion():
            return False

        # Check moved_to (entered this section or classification)
        if self.moved_to is not None:
            section_match = interval.section_name.lower() == self.moved_to.lower()
            classification_match = (
                interval.classification is not None
                and interval.classification.value.lower() == self.moved_to.lower()
            )
            if not (section_match or classification_match):
                return False

        # Check since/until against entered_at
        if self.since is not None and interval.entered_at.date() < self.since:
            return False
        if self.until is not None and interval.entered_at.date() > self.until:
            return False

        # Check moved_from (previous interval's section or classification)
        if self.moved_from is not None:
            idx = timeline.intervals.index(interval)
            if idx == 0:
                return False  # No previous interval
            prev = timeline.intervals[idx - 1]
            prev_section_match = prev.section_name.lower() == self.moved_from.lower()
            prev_class_match = (
                prev.classification is not None
                and prev.classification.value.lower() == self.moved_from.lower()
            )
            if not (prev_section_match or prev_class_match):
                return False

        return True


def parse_date_or_relative(value: str) -> date:
    """Parse an absolute ISO date or relative duration string.

    Accepts:
        - ISO date: '2025-01-01'
        - Relative days: '30d' (30 days before today)
        - Relative weeks: '4w' (28 days before today)

    Args:
        value: Date string to parse.

    Returns:
        Resolved date.

    Raises:
        ValueError: If the value cannot be parsed as a date or relative duration.
    """
    stripped = value.strip()

    # Try relative patterns first
    relative_match = re.match(r"^(\d+)(d|w)$", stripped)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        if unit == "w":
            amount *= 7
        return date.today() - timedelta(days=amount)

    # Try ISO date
    try:
        return date.fromisoformat(stripped)
    except ValueError:
        raise ValueError(
            f"Cannot parse date: {value!r}. "
            "Expected ISO date (2025-01-01) or relative duration (30d, 4w)"
        ) from None
