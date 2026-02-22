# TDD: SectionTimeline Primitive

```yaml
id: TDD-SECTION-TIMELINE-001
status: DRAFT
date: 2026-02-19
author: architect
prd: PRD-SECTION-TIMELINE-001
impact: high
impact_categories: [api_contract, data_model, service_layer]
```

---

## 1. System Context

### 1.1 Purpose

This design specifies the SectionTimeline primitive: domain models, service layer, HTTP endpoint, and pre-warm infrastructure. The primitive reconstructs a chronological timeline of which Asana section each offer occupied and when, then computes calendar-day counts (`active_section_days`, `billable_section_days`) independent of ad spend data.

### 1.2 Scope Boundary

This TDD covers ONLY the primitive itself. Integration with reconcile-spend, Rules 6 & 7, or ThreeWayComparison is explicitly out of scope per the PRD.

### 1.3 Design Constraints

- **Additive only**: No modifications to existing files except `api/routes/__init__.py`, `api/main.py`, and `api/lifespan.py`.
- **Existing patterns**: Uses `SuccessResponse[T]`, `raise_api_error()`, `RequestId`, `AsanaClientDualMode` DI.
- **Existing infrastructure**: Story cache via `StoriesClient.list_for_task_cached()`, classification via `OFFER_CLASSIFIER.classify()`.

---

## 2. Tradeoff Analysis

### 2.1 Day Counting: set[date] vs. Interval Arithmetic

| Approach | Complexity | Correctness | Perf |
|----------|-----------|-------------|------|
| `set[date]` dedup | Simple | Correct for overlapping intervals | O(days * intervals) |
| Interval tree / arithmetic | Complex | Correct but hard to verify | O(intervals * log(intervals)) |

**Decision**: `set[date]` dedup. The maximum period is bounded (realistic queries are 30-90 days), and we have at most a few dozen intervals per offer. The O(days * intervals) cost is negligible (< 1ms per offer for a 365-day period with 50 intervals). The simplicity makes the implementation trivially verifiable against the PRD edge cases.

### 2.2 Service vs. Class Methods for Day Counting

| Approach | Testability | Cohesion |
|----------|------------|----------|
| Methods on `SectionTimeline` | Unit-testable without service | Timeline owns its own computation |
| Free functions in service | Requires timeline + period args | Service orchestrates everything |

**Decision**: Methods on `SectionTimeline`. The day counting is intrinsic to the timeline data -- it operates on `self.intervals` and a query period. Placing it on the model enables pure unit tests with no service dependencies.

### 2.3 Frozen Dataclass vs. Pydantic for Domain Models

| Approach | Mutability | Serialization | Perf |
|----------|-----------|---------------|------|
| `@dataclass(frozen=True)` | Immutable | Manual | Fast construction |
| Pydantic `BaseModel` | Mutable by default | Built-in | Slower construction |

**Decision**: Frozen dataclasses for `SectionInterval` and `SectionTimeline` (domain layer, not serialized to HTTP). Pydantic for `OfferTimelineEntry` (API response model, needs JSON serialization). This matches the existing codebase pattern where `AccountActivity` is a plain enum and `SectionClassifier` is a frozen dataclass.

### 2.4 Pre-Warm: Blocking Startup vs. Background Task

| Approach | Startup Latency | Availability |
|----------|----------------|--------------|
| Blocking startup | High (minutes) | 100% once started |
| Background task + 503 gate | Zero | Gradual (503 -> 200) |

**Decision**: Background `asyncio.Task` launched after entity discovery, matching the existing `cache_warming` pattern in `lifespan.py`. The 503 gate (50% threshold) provides a readiness signal without blocking the ECS health check.

---

## 3. Data Model

### 3.1 File: `src/autom8_asana/models/business/section_timeline.py`

```python
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
        intervals: Chronologically ordered tuple of SectionInterval values.
        task_created_at: Task creation timestamp (used for imputation).
        story_count: Number of section_changed stories after filtering.
    """

    offer_gid: str
    office_phone: str | None
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
            # AC-4.5: Open intervals extend to period_end
            if interval.exited_at is None:
                interval_end = end
            else:
                interval_end = interval.exited_at.date()

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
        active_section_days: Calendar days in ACTIVE sections during period.
        billable_section_days: Calendar days in ACTIVE or ACTIVATING
            sections during period.
    """

    offer_gid: str = Field(..., description="Asana task GID")
    office_phone: str | None = Field(
        default=None, description="Office phone custom field"
    )
    active_section_days: int = Field(
        ..., ge=0, description="Days in ACTIVE sections"
    )
    billable_section_days: int = Field(
        ..., ge=0, description="Days in ACTIVE or ACTIVATING sections"
    )

    model_config = {"extra": "forbid"}
```

### 3.2 Design Rationale

- **`intervals: tuple[...]`** -- Tuple (not list) because the timeline is frozen/immutable once constructed. Consistent with the `frozen=True` contract.
- **`_count_days_for_classifications`** -- Private shared method avoids duplicating the date iteration logic between `active_days_in_period` and `billable_days_in_period`.
- **Lazy import of `AccountActivity`** -- The `from __future__ import annotations` makes all type hints strings, and the runtime imports in methods avoid circular import issues (same pattern used by `Offer.account_activity`).
- **`story_count`** -- Retained for observability/debugging. Allows callers to distinguish "zero days because never moved and currently inactive" from "zero days because no section_changed stories found."

---

## 4. Service Layer

### 4.1 File: `src/autom8_asana/services/section_timeline_service.py`

```python
"""Section timeline service for reconstructing offer section histories.

Per TDD-SECTION-TIMELINE-001: Orchestrates story fetching, filtering,
timeline construction, and day counting for all offers in the Business
Offers project.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime

# Bounded concurrency for S3-backed warm-up (per SPIKE-SECTION-TIMELINE-CACHE).
# Avoids overwhelming Redis/S3 while parallelizing promotion from cold tier.
# Sequential fetching is only necessary for Asana API calls; S3 reads are safe
# to parallelize. Semaphore(20) balances speed vs. resource pressure.
_WARM_CONCURRENCY = 20

# Wall-clock timeout for the pre-warm task. If warming takes longer than this,
# assume Asana API is unavailable or partially degraded and surface a distinct
# TIMELINE_WARM_FAILED error (per interview decision 2026-02-19).
_WARM_TIMEOUT_SECONDS = 600  # 10 minutes

from autom8y_log import get_logger

from autom8_asana.client import AsanaClient
from autom8_asana.exceptions import AsanaError
from autom8_asana.models.business.activity import (
    OFFER_CLASSIFIER,
    AccountActivity,
    extract_section_name,
)
from autom8_asana.models.business.section_timeline import (
    OfferTimelineEntry,
    SectionInterval,
    SectionTimeline,
)
from autom8_asana.models.story import Story

logger = get_logger(__name__)

# Business Offers project GID (matches Offer.PRIMARY_PROJECT_GID)
BUSINESS_OFFERS_PROJECT_GID = "1143843662099250"

# Story opt_fields for section_changed extraction
_STORY_OPT_FIELDS: list[str] = [
    "gid",
    "resource_subtype",
    "created_at",
    "new_section.name",
    "old_section.name",
]

# Task opt_fields for offer enumeration
_TASK_OPT_FIELDS: list[str] = [
    "gid",
    "created_at",
    "memberships.section.name",
    "memberships.project.gid",
    "custom_fields.name",
    "custom_fields.text_value",
]


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string to datetime.

    Handles Asana's format: "2024-01-15T10:30:00.000Z"

    Args:
        value: ISO 8601 datetime string or None.

    Returns:
        Parsed datetime or None.
    """
    if value is None:
        return None
    # Strip trailing 'Z' and parse
    clean = value.replace("Z", "+00:00")
    return datetime.fromisoformat(clean)


def _is_cross_project_noise(story: Story) -> bool:
    """Check if a section_changed story is cross-project noise.

    Per AC-1.3: If BOTH old_section and new_section classify as None,
    this story is from a non-Business-Offers project and should be
    skipped.

    Per AC-1.4: If only one side is None, the story is retained.

    Args:
        story: Story with resource_subtype == "section_changed".

    Returns:
        True if the story should be filtered out (both sides unknown).
    """
    new_name = story.new_section.name if story.new_section else None
    old_name = story.old_section.name if story.old_section else None

    new_cls = OFFER_CLASSIFIER.classify(new_name) if new_name else None
    old_cls = OFFER_CLASSIFIER.classify(old_name) if old_name else None

    return new_cls is None and old_cls is None


def _extract_office_phone(task_data: dict) -> str | None:
    """Extract office_phone custom field from raw task data.

    Walks custom_fields array looking for the "Office Phone" field.

    Args:
        task_data: Raw task dict from Asana API.

    Returns:
        Office phone string or None.
    """
    custom_fields = task_data.get("custom_fields") or []
    for cf in custom_fields:
        if isinstance(cf, dict) and cf.get("name") == "Office Phone":
            return cf.get("text_value")
    return None


def _build_intervals_from_stories(
    stories: list[Story],
) -> tuple[list[SectionInterval], int]:
    """Walk filtered stories chronologically to produce SectionInterval list.

    Per AC-2.5: Each story closes the previous interval and opens a new one.
    Per AC-2.6: The final interval has exited_at=None.
    Per AC-2.3: Unknown sections get classification=None + WARNING log.

    Args:
        stories: Section-changed stories, already filtered, sorted by
            created_at ascending.

    Returns:
        Tuple of (intervals list, story count used).
    """
    if not stories:
        return [], 0

    intervals: list[SectionInterval] = []
    story_count = len(stories)

    for i, story in enumerate(stories):
        section_name = story.new_section.name if story.new_section else "UNKNOWN"
        classification = OFFER_CLASSIFIER.classify(section_name)

        if classification is None:
            logger.warning(
                "unknown_section_in_timeline",
                extra={
                    "section_name": section_name,
                    "story_gid": story.gid,
                },
            )

        entered_at = _parse_datetime(story.created_at)
        if entered_at is None:
            continue

        # Close previous interval
        if intervals:
            prev = intervals[-1]
            intervals[-1] = SectionInterval(
                section_name=prev.section_name,
                classification=prev.classification,
                entered_at=prev.entered_at,
                exited_at=entered_at,
            )

        # Open new interval (AC-2.6: last one stays open)
        intervals.append(
            SectionInterval(
                section_name=section_name,
                classification=classification,
                entered_at=entered_at,
                exited_at=None,
            )
        )

    return intervals, story_count


def _build_imputed_interval(
    task_created_at: datetime | None,
    account_activity: AccountActivity | None,
    section_name: str,
) -> list[SectionInterval]:
    """Build a single imputed interval for a never-moved task.

    Per AC-3.1: If zero stories remain, impute [task.created_at, None].
    Per AC-3.2: Use the offer's current account_activity for classification.

    Args:
        task_created_at: Task creation timestamp.
        account_activity: Current section classification.
        section_name: Current section name.

    Returns:
        List containing one SectionInterval, or empty if no created_at.
    """
    if task_created_at is None:
        return []

    return [
        SectionInterval(
            section_name=section_name,
            classification=account_activity,
            entered_at=task_created_at,
            exited_at=None,
        )
    ]


async def build_timeline_for_offer(
    client: AsanaClient,
    offer_gid: str,
    office_phone: str | None,
    task_created_at: datetime | None,
    current_section_name: str | None,
    current_account_activity: AccountActivity | None,
) -> SectionTimeline:
    """Build a SectionTimeline for a single offer.

    Per FR-1: Fetch and filter stories.
    Per FR-2: Walk chronologically to produce intervals.
    Per FR-3: Handle never-moved tasks via imputation.

    Args:
        client: AsanaClient for story fetching.
        offer_gid: Offer task GID.
        office_phone: Office phone custom field value.
        task_created_at: Task creation timestamp.
        current_section_name: Current section name (for imputation).
        current_account_activity: Current classification (for imputation).

    Returns:
        SectionTimeline for this offer.
    """
    # FR-1: Fetch stories via cached client
    stories = await client.stories.list_for_task_cached_async(
        offer_gid,
        opt_fields=_STORY_OPT_FIELDS,
    )

    # AC-1.2: Filter to section_changed only
    section_stories = [
        s for s in stories if s.resource_subtype == "section_changed"
    ]

    # AC-1.3, AC-1.4: Filter cross-project noise
    filtered_stories = [
        s for s in section_stories if not _is_cross_project_noise(s)
    ]

    # Sort by created_at ascending (AC-2.5)
    filtered_stories.sort(key=lambda s: s.created_at or "")

    # FR-2: Build intervals from filtered stories
    intervals, story_count = _build_intervals_from_stories(filtered_stories)

    # FR-3: Handle never-moved task
    if not intervals:
        intervals = _build_imputed_interval(
            task_created_at,
            current_account_activity,
            current_section_name or "UNKNOWN",
        )
        story_count = 0

    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        intervals=tuple(intervals),
        task_created_at=task_created_at,
        story_count=story_count,
    )


async def get_section_timelines(
    client: AsanaClient,
    period_start: date,
    period_end: date,
) -> list[OfferTimelineEntry]:
    """Compute section timelines for all offers in the Business Offers project.

    Per FR-5: Enumerates ALL tasks in project GID 1143843662099250.
    Per FR-4: Computes active_section_days and billable_section_days.

    Args:
        client: AsanaClient for Asana API calls.
        period_start: Query period start (inclusive).
        period_end: Query period end (inclusive).

    Returns:
        List of OfferTimelineEntry for all offers.
    """
    # FR-5/AC-5.1: Enumerate all tasks in Business Offers project
    tasks = await client.tasks.list_async(
        project=BUSINESS_OFFERS_PROJECT_GID,
        opt_fields=_TASK_OPT_FIELDS,
    ).collect()

    logger.info(
        "section_timeline_enumeration_complete",
        extra={
            "offer_count": len(tasks),
            "period_start": str(period_start),
            "period_end": str(period_end),
        },
    )

    entries: list[OfferTimelineEntry] = []

    for task in tasks:
        try:
            # Extract fields from task
            task_created_at = _parse_datetime(task.created_at)
            section_name = extract_section_name(
                task, project_gid=BUSINESS_OFFERS_PROJECT_GID
            )
            account_activity = (
                OFFER_CLASSIFIER.classify(section_name) if section_name else None
            )

            # Extract office_phone from custom_fields
            # Task model custom_fields are list[dict] when using opt_fields
            office_phone = _extract_office_phone(task.model_dump())

            timeline = await build_timeline_for_offer(
                client=client,
                offer_gid=task.gid,
                office_phone=office_phone,
                task_created_at=task_created_at,
                current_section_name=section_name,
                current_account_activity=account_activity,
            )

            active_days = timeline.active_days_in_period(period_start, period_end)
            billable_days = timeline.billable_days_in_period(period_start, period_end)

            entries.append(
                OfferTimelineEntry(
                    offer_gid=task.gid,
                    office_phone=office_phone,
                    active_section_days=active_days,
                    billable_section_days=billable_days,
                )
            )
        except Exception:
            logger.warning(
                "section_timeline_offer_failed",
                extra={"offer_gid": task.gid},
                exc_info=True,
            )
            continue

    logger.info(
        "section_timeline_computation_complete",
        extra={
            "total_offers": len(tasks),
            "successful_entries": len(entries),
            "period_start": str(period_start),
            "period_end": str(period_end),
        },
    )

    return entries


async def warm_story_caches(
    client: AsanaClient,
    on_progress: callable | None = None,
) -> tuple[int, int]:
    """Pre-warm story caches for all offers in the Business Offers project.

    Per FR-7/AC-7.2: Iterates over all offers and calls
    list_for_task_cached() to populate the incremental story cache.

    Per AC-7.6: Individual failures are logged at WARNING and do not
    abort the overall warm-up.

    Per SPIKE-SECTION-TIMELINE-CACHE: Uses bounded-parallel concurrency
    (_WARM_CONCURRENCY) instead of sequential iteration. S3 → Redis promotion
    is I/O-safe to parallelize; only Asana API fetches need rate-limit care,
    and list_for_task_cached() handles that internally (writes to S3 are
    sequential within each offer's cache path).

    Args:
        client: AsanaClient for Asana API calls.
        on_progress: Optional callback(warmed: int, total: int) for
            progress tracking.

    Returns:
        Tuple of (warmed_count, total_count).
    """
    # Enumerate all offers
    tasks = await client.tasks.list_async(
        project=BUSINESS_OFFERS_PROJECT_GID,
        opt_fields=["gid"],
    ).collect()

    total = len(tasks)
    warmed = 0
    sem = asyncio.Semaphore(_WARM_CONCURRENCY)

    logger.info(
        "story_cache_warm_started",
        extra={"total_offers": total, "concurrency": _WARM_CONCURRENCY},
    )

    async def _warm_one(gid: str) -> bool:
        """Warm a single offer's story cache. Returns True on success."""
        async with sem:
            try:
                await client.stories.list_for_task_cached_async(
                    gid,
                    opt_fields=_STORY_OPT_FIELDS,
                )
                return True
            except Exception:
                logger.warning(
                    "story_cache_warm_offer_failed",
                    extra={"offer_gid": gid},
                    exc_info=True,
                )
                return False

    # Run bounded-parallel warm; gather results to track progress.
    # Return_exceptions=True ensures one failure doesn't cancel others.
    results = await asyncio.gather(
        *[_warm_one(task.gid) for task in tasks],
        return_exceptions=True,
    )

    warmed = sum(1 for r in results if r is True)

    if on_progress is not None:
        on_progress(warmed, total)

    logger.info(
        "story_cache_warm_complete",
        extra={"warmed": warmed, "total": total},
    )

    return warmed, total
```

### 4.2 Key Design Decisions

1. **Free functions, not a class**: The service is stateless. Functions take `AsanaClient` as an argument, matching the codebase pattern where services that need a client receive it via DI at the route level. No `__init__` state means no lifecycle management.

2. **`_STORY_OPT_FIELDS` constant**: Centralizes the opt_fields list so both `warm_story_caches()` and `build_timeline_for_offer()` use identical field sets, ensuring cache compatibility.

3. **`_extract_office_phone` from raw dict**: The Task model uses `custom_fields` as a raw list when fetched with opt_fields. We extract via dict walking rather than descriptor resolution (the `Offer.office_phone` descriptor requires a fully hydrated Offer, which we do not have in this read path).

4. **Sequential story fetching per offer**: Stories for each offer are fetched sequentially (not concurrently) to avoid rate limit saturation. The caching layer (`list_for_task_cached`) ensures most calls hit cache after warm-up.

5. **`on_progress` callback**: The warm function accepts a progress callback instead of writing to `app.state` directly. This keeps the service layer decoupled from FastAPI. The lifespan code provides the callback that writes to `app.state`.

---

## 5. HTTP Endpoint

### 5.1 File: `src/autom8_asana/api/routes/section_timelines.py`

```python
"""Section timeline endpoint for offer activity tracking.

Per TDD-SECTION-TIMELINE-001 / FR-6: Exposes timeline data for all
offers in the Business Offers project.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.exceptions import AsanaError
from autom8_asana.models.business.section_timeline import OfferTimelineEntry
from autom8_asana.services.section_timeline_service import get_section_timelines

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/offers", tags=["offers"])

# Readiness gate threshold (AC-7.4)
_READINESS_THRESHOLD = 0.50

# Retry-After seconds for 503 responses (AC-6.7)
_RETRY_AFTER_SECONDS = 30


class SectionTimelinesResponse(BaseModel):
    """Response wrapper for section timeline data.

    Attributes:
        timelines: List of timeline entries for all offers.
    """

    timelines: list[OfferTimelineEntry] = Field(
        ..., description="Timeline entries for all offers"
    )

    model_config = {"extra": "forbid"}


class _ReadinessState(str):
    """Possible readiness outcomes for the section timeline endpoint."""
    READY = "ready"
    NOT_READY = "not_ready"       # Still warming
    WARM_FAILED = "warm_failed"   # Timeout or catastrophic failure


def _check_readiness(request: Request) -> str:
    """Check if story caches are sufficiently warmed.

    Per AC-7.4: Returns READY if >= 50% of offers have cached stories.
    Per interview 2026-02-19: Distinguishes still-warming (NOT_READY)
    from failed warm-up (WARM_FAILED) so callers can distinguish transient
    from permanent error conditions.

    Args:
        request: FastAPI request (for app.state access).

    Returns:
        _ReadinessState string: READY, NOT_READY, or WARM_FAILED.
    """
    if getattr(request.app.state, "timeline_warm_failed", False):
        return _ReadinessState.WARM_FAILED

    warm_count = getattr(request.app.state, "timeline_warm_count", 0)
    total_count = getattr(request.app.state, "timeline_total", 0)

    if total_count == 0:
        return _ReadinessState.NOT_READY

    if (warm_count / total_count) >= _READINESS_THRESHOLD:
        return _ReadinessState.READY

    return _ReadinessState.NOT_READY


@router.get(
    "/section-timelines",
    summary="Get section timelines for all offers",
    response_model=SuccessResponse[SectionTimelinesResponse],
)
async def get_offer_section_timelines(
    request: Request,
    client: AsanaClientDualMode,
    request_id: RequestId,
    period_start: Annotated[
        date,
        Query(description="Period start date (YYYY-MM-DD, inclusive)"),
    ],
    period_end: Annotated[
        date,
        Query(description="Period end date (YYYY-MM-DD, inclusive)"),
    ],
) -> SuccessResponse[SectionTimelinesResponse]:
    """Get section timelines for all offers in the Business Offers project.

    Computes active_section_days and billable_section_days for each offer
    based on their Asana section history within the specified date range.

    Args:
        request: FastAPI request.
        client: Asana API client (from DI).
        request_id: Request correlation ID.
        period_start: Start date for day counting (inclusive).
        period_end: End date for day counting (inclusive).

    Returns:
        SuccessResponse containing list of OfferTimelineEntry.

    Raises:
        HTTPException: 422 if period_start > period_end.
        HTTPException: 502 if Asana API fails.
        HTTPException: 503 if story caches are not warmed.
    """
    start_time = time.perf_counter()

    # AC-6.5: Validate period_start <= period_end
    if period_start > period_end:
        raise_api_error(
            request_id,
            422,
            "VALIDATION_ERROR",
            "period_start must be <= period_end",
        )

    # AC-6.7, AC-7.4: Check readiness gate (distinguishes warming vs. failed)
    readiness = _check_readiness(request)
    if readiness == _ReadinessState.WARM_FAILED:
        raise_api_error(
            request_id,
            503,
            "TIMELINE_WARM_FAILED",
            "Section timeline story cache warm-up failed — operator intervention required",
        )
    elif readiness == _ReadinessState.NOT_READY:
        raise_api_error(
            request_id,
            503,
            "TIMELINE_NOT_READY",
            "Section timeline story caches are still warming up",
            details={"retry_after_seconds": _RETRY_AFTER_SECONDS},
            headers={"Retry-After": str(_RETRY_AFTER_SECONDS)},
        )

    # FR-4, FR-5: Compute timelines
    try:
        entries = await get_section_timelines(
            client=client,
            period_start=period_start,
            period_end=period_end,
        )
    except AsanaError:
        # AC-6.6: Asana API failure -> 502
        raise_api_error(
            request_id,
            502,
            "UPSTREAM_ERROR",
            "Asana API is currently unavailable",
        )

    duration_ms = (time.perf_counter() - start_time) * 1000

    # NFR-2: Structured logging for endpoint completion
    logger.info(
        "section_timelines_served",
        extra={
            "request_id": request_id,
            "offer_count": len(entries),
            "period_start": str(period_start),
            "period_end": str(period_end),
            "duration_ms": round(duration_ms, 1),
        },
    )

    response_data = SectionTimelinesResponse(timelines=entries)
    return build_success_response(data=response_data, request_id=request_id)


__all__ = ["router"]
```

### 5.2 Endpoint Contract

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/api/v1/offers/section-timelines` |
| Auth | Dual-mode (JWT S2S or PAT) via `AsanaClientDualMode` |
| Query: `period_start` | `date` (required, YYYY-MM-DD) |
| Query: `period_end` | `date` (required, YYYY-MM-DD) |
| 200 Response | `SuccessResponse[SectionTimelinesResponse]` |
| 422 | `VALIDATION_ERROR` -- `period_start > period_end` or bad date format |
| 502 | `UPSTREAM_ERROR` -- Asana API failure |
| 503 | `TIMELINE_NOT_READY` + `Retry-After: 30` header |

### 5.3 Response Shape (200 OK)

```json
{
  "data": {
    "timelines": [
      {
        "offer_gid": "1205925604226368",
        "office_phone": "555-0100",
        "active_section_days": 7,
        "billable_section_days": 7
      },
      {
        "offer_gid": "1234567890123456",
        "office_phone": null,
        "active_section_days": 0,
        "billable_section_days": 3
      }
    ]
  },
  "meta": {
    "request_id": "a1b2c3d4e5f6g7h8",
    "timestamp": "2026-02-19T12:00:00Z",
    "pagination": null
  }
}
```

### 5.4 Error Response Shape (503)

```json
{
  "error": "TIMELINE_NOT_READY",
  "message": "Section timeline story caches are still warming up",
  "request_id": "a1b2c3d4e5f6g7h8",
  "retry_after_seconds": 30
}
```

Response includes HTTP header `Retry-After: 30`.

---

## 6. Pre-Warm Extension

### 6.1 Modifications to `src/autom8_asana/api/lifespan.py`

Insert AFTER the existing `cache_warming_task` launch (line ~198) and BEFORE the `yield`:

```python
# --- Section Timeline Story Cache Pre-Warm (FR-7) ---
# Per TDD-SECTION-TIMELINE-001: Background story cache warming
# for section timeline endpoint readiness gating.

# Initialize progress counters and failure flag on app.state
app.state.timeline_warm_count = 0
app.state.timeline_total = 0
app.state.timeline_warm_failed = False  # Set True on timeout or exception

async def _warm_section_timeline_stories() -> None:
    """Background task: warm story caches for section timelines.

    Per SPIKE-SECTION-TIMELINE-CACHE: warm_story_caches() uses bounded-parallel
    concurrency (Semaphore(20)) so S3 promotion is fast (~5s for 500 offers).

    Per interview 2026-02-19: If warm-up exceeds _WARM_TIMEOUT_SECONDS or
    fails catastrophically, set app.state.timeline_warm_failed = True so
    the endpoint returns TIMELINE_WARM_FAILED (permanent 503) instead of
    TIMELINE_NOT_READY (retry-able 503). This distinguishes 'still starting'
    from 'broken and needs operator attention'.
    """
    from autom8_asana.services.section_timeline_service import (
        _WARM_TIMEOUT_SECONDS,
        warm_story_caches,
    )

    try:
        # Create a bot-PAT client for pre-warm (same as S2S auth)
        from autom8_asana.api.config import get_settings
        from autom8_asana.client import AsanaClient

        settings = get_settings()
        bot_pat = settings.asana_bot_pat
        if not bot_pat:
            logger.warning(
                "timeline_warm_skipped_no_bot_pat",
                extra={"reason": "ASANA_BOT_PAT not configured"},
            )
            # No bot PAT → treat as permanent failure (operator must configure)
            app.state.timeline_warm_failed = True
            return

        warm_client = AsanaClient(token=bot_pat)

        def on_progress(warmed: int, total: int) -> None:
            app.state.timeline_warm_count = warmed
            app.state.timeline_total = total

        # Wrap with timeout. asyncio.wait_for raises TimeoutError on expiry.
        warmed, total = await asyncio.wait_for(
            warm_story_caches(client=warm_client, on_progress=on_progress),
            timeout=_WARM_TIMEOUT_SECONDS,
        )
        logger.info(
            "timeline_story_warm_complete",
            extra={"warmed": warmed, "total": total},
        )
    except asyncio.TimeoutError:
        logger.error(
            "timeline_story_warm_timed_out",
            extra={"timeout_seconds": _WARM_TIMEOUT_SECONDS},
        )
        app.state.timeline_warm_failed = True
    except asyncio.CancelledError:
        logger.info("timeline_story_warm_cancelled")
        raise
    except Exception:
        logger.error(
            "timeline_story_warm_exception",
            exc_info=True,
        )
        app.state.timeline_warm_failed = True

timeline_warm_task = asyncio.create_task(
    _warm_section_timeline_stories(),
    name="timeline_story_warm",
)
app.state.timeline_warm_task = timeline_warm_task

logger.info(
    "timeline_story_warm_started_background",
    extra={"task_name": "timeline_story_warm"},
)
```

In the shutdown section (after the existing `cache_warming_task` cleanup), add:

```python
# Cancel timeline story warm task if still running
if hasattr(app.state, "timeline_warm_task"):
    task = app.state.timeline_warm_task
    if not task.done():
        logger.info("timeline_story_warm_cancelling")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("timeline_story_warm_cancelled")
        except Exception as e:
            logger.warning(
                "timeline_story_warm_cancel_error",
                extra={"error": str(e)},
            )
```

### 6.2 Readiness Gate Flow

```
                 Startup
                    |
          +---------v----------+
          | Entity Discovery   |
          +---------+----------+
                    |
     +--------------+---------------+
     |                              |
     v                              v
 cache_warming_task          timeline_warm_task
 (DataFrames)                (Story caches)
     |                              |
     |                   +----------v-----------+
     |                   | For each offer:      |
     |                   |   list_for_task_cached|
     |                   |   update app.state   |
     |                   |     .timeline_warm_  |
     |                   |      count / total   |
     |                   +----------+-----------+
     |                              |
     v                              v
 /health/ready               Endpoint checks:
 (dataframe)                 warm_count/total >= 0.50?
                                    |
                            +-------+--------+
                            |                |
                          < 50%            >= 50%
                            |                |
                         503 +             200 OK
                     Retry-After:30
```

### 6.3 Bot PAT Access

The pre-warm task needs an `AsanaClient` but runs outside the request lifecycle (no auth header). It uses the bot PAT from settings, matching how the existing `cache_warming` task uses the environment for Asana access. The `get_settings().asana_bot_pat` reads `ASANA_BOT_PAT` from the environment.

---

## 7. Route Registration

### 7.1 Modification to `src/autom8_asana/api/routes/__init__.py`

Add to imports:

```python
from .section_timelines import router as section_timelines_router
```

Add to `__all__`:

```python
"section_timelines_router",
```

### 7.2 Modification to `src/autom8_asana/api/main.py`

Add import in the routes import block:

```python
from autom8_asana.api.routes import section_timelines_router
```

Add after the existing `entity_write_router` include:

```python
app.include_router(section_timelines_router)
```

---

## 8. Integration Points

### 8.1 `StoriesClient.list_for_task_cached_async()`

| Property | Value |
|----------|-------|
| **Called from** | `build_timeline_for_offer()`, `warm_story_caches()` |
| **Location** | `src/autom8_asana/clients/stories.py:342` |
| **Signature** | `async def list_for_task_cached_async(task_gid: str, *, task_modified_at: str | None = None, opt_fields: list[str] | None = None) -> list[Story]` |
| **Args passed** | `task_gid=offer_gid, opt_fields=["gid", "resource_subtype", "created_at", "new_section.name", "old_section.name"]` |
| **Returns** | `list[Story]` sorted by `created_at` |
| **Caching** | Uses incremental append-only cache infrastructure; second call fetches only new stories |
| **Modifications** | None |

### 8.2 `TasksClient.list_async()`

| Property | Value |
|----------|-------|
| **Called from** | `get_section_timelines()`, `warm_story_caches()` |
| **Location** | `src/autom8_asana/clients/tasks.py:459` |
| **Signature** | `def list_async(*, project: str | None = None, opt_fields: list[str] | None = None, ...) -> PageIterator[Task]` |
| **Args passed (enumeration)** | `project="1143843662099250", opt_fields=["gid", "created_at", "memberships.section.name", "memberships.project.gid", "custom_fields.name", "custom_fields.text_value"]` |
| **Args passed (warm)** | `project="1143843662099250", opt_fields=["gid"]` |
| **Returns** | `PageIterator[Task]`, collected via `.collect()` |
| **Modifications** | None |

### 8.3 `OFFER_CLASSIFIER.classify()`

| Property | Value |
|----------|-------|
| **Called from** | `_is_cross_project_noise()`, `_build_intervals_from_stories()`, `get_section_timelines()` |
| **Location** | `src/autom8_asana/models/business/activity.py:69` |
| **Signature** | `def classify(section_name: str) -> AccountActivity | None` |
| **Behavior** | O(1) case-insensitive dict lookup. Returns `AccountActivity` or `None` for unregistered sections. |
| **Modifications** | None |

### 8.4 `extract_section_name()`

| Property | Value |
|----------|-------|
| **Called from** | `get_section_timelines()` |
| **Location** | `src/autom8_asana/models/business/activity.py:138` |
| **Signature** | `def extract_section_name(task: Any, project_gid: str | None = None) -> str | None` |
| **Args passed** | `task=task, project_gid="1143843662099250"` |
| **Modifications** | None |

### 8.5 `raise_api_error()`

| Property | Value |
|----------|-------|
| **Called from** | `get_offer_section_timelines()` |
| **Location** | `src/autom8_asana/api/errors.py:85` |
| **Signature** | `def raise_api_error(request_id: str, status_code: int, code: str, message: str, *, details: dict | None = None, headers: dict | None = None) -> Never` |
| **Used for** | Validation error (422), upstream error (502), timeline not ready (503) |
| **Modifications** | None |

### 8.6 `build_success_response()`

| Property | Value |
|----------|-------|
| **Called from** | `get_offer_section_timelines()` |
| **Location** | `src/autom8_asana/api/models.py:150` |
| **Signature** | `def build_success_response(data: Any, request_id: str, pagination: PaginationMeta | None = None) -> SuccessResponse[Any]` |
| **Modifications** | None |

### 8.7 `AsanaClientDualMode` / `RequestId`

| Property | Value |
|----------|-------|
| **Location** | `src/autom8_asana/api/dependencies.py:404,409` |
| **Type** | `Annotated[AsanaClient, Depends(get_asana_client_from_context)]` / `Annotated[str, Depends(get_request_id)]` |
| **Usage** | FastAPI DI for route handler parameters |
| **Modifications** | None |

---

## 9. File Inventory

| File | New/Modified | Reason |
|------|-------------|--------|
| `src/autom8_asana/models/business/section_timeline.py` | **New** | Domain models: `SectionInterval`, `SectionTimeline`, `OfferTimelineEntry` |
| `src/autom8_asana/services/section_timeline_service.py` | **New** | Service functions: `build_timeline_for_offer()`, `get_section_timelines()`, `warm_story_caches()` |
| `src/autom8_asana/api/routes/section_timelines.py` | **New** | HTTP endpoint: `GET /api/v1/offers/section-timelines` |
| `src/autom8_asana/api/routes/__init__.py` | **Modified** | Add `section_timelines_router` import and `__all__` entry |
| `src/autom8_asana/api/main.py` | **Modified** | Add `app.include_router(section_timelines_router)` |
| `src/autom8_asana/api/lifespan.py` | **Modified** | Add background story cache warm-up task and shutdown cleanup |
| `tests/unit/models/test_section_timeline.py` | **New** | Unit tests for domain models and day counting |
| `tests/unit/services/test_section_timeline_service.py` | **New** | Unit tests for service functions |
| `tests/unit/api/test_routes_section_timelines.py` | **New** | Route handler tests |

---

## 10. Error Handling

| Error Condition | Source | HTTP Status | Error Code | Detail |
|----------------|--------|-------------|------------|--------|
| Invalid date format | FastAPI validation | 422 | `VALIDATION_ERROR` | Standard Pydantic validation error |
| `period_start > period_end` | Route handler | 422 | `VALIDATION_ERROR` | `"period_start must be <= period_end"` |
| Asana API failure | `AsanaError` catch | 502 | `UPSTREAM_ERROR` | `"Asana API is currently unavailable"` |
| Story caches not warmed | Readiness gate | 503 | `TIMELINE_NOT_READY` | `retry_after_seconds: 30` + `Retry-After: 30` header |
| Individual offer processing failure | Per-offer try/except | N/A (logged) | N/A | WARNING log, offer excluded from results |
| Individual warm failure | Per-offer try/except | N/A (logged) | N/A | WARNING log, offer counted as not-warmed |

---

## 11. Security Considerations

- **No PII exposure**: `office_phone` is already exposed via the existing `Offer` model custom field descriptor. The timeline endpoint does not introduce new PII surface.
- **Auth**: Uses existing `AsanaClientDualMode` DI, inheriting JWT S2S and PAT authentication.
- **Bot PAT**: Pre-warm uses `ASANA_BOT_PAT` from environment (existing secret management pattern).
- **No input injection**: All user inputs are `date` types parsed by FastAPI/Pydantic, and `request_id` from middleware.

---

## 12. Performance Considerations

- **NFR-1 (< 5s p95)**: With pre-warmed caches, story fetches are cache hits (incremental: only new stories fetched). Offer enumeration is a single paginated API call. Day counting is O(days * intervals) per offer, negligible at ~1ms per offer.
- **NFR-3 (Cache Efficiency)**: Story data is fetched once during pre-warm, then incrementally updated. No full re-fetch on every request.
- **Warm-up time**: Approximately 1-2 minutes for ~500 offers (sequential story fetching to avoid rate limits). The 50% readiness gate allows serving after ~30-60 seconds.
- **Memory**: Each `SectionTimeline` is short-lived (constructed per-request, GC'd after response). The persistent cost is in the story cache itself (existing infrastructure).

---

## 13. Test Coverage Plan

### 13.1 `tests/unit/models/test_section_timeline.py`

Unit tests for domain models (pure logic, no mocking needed).

| Test Function | Covers | Description |
|--------------|--------|-------------|
| `test_section_interval_frozen` | Data model | Verify `SectionInterval` is immutable |
| `test_section_timeline_frozen` | Data model | Verify `SectionTimeline` is immutable |
| `test_active_days_single_active_interval` | FR-4, AC-4.1 | Single ACTIVE interval spanning full period |
| `test_active_days_excludes_activating` | AC-4.1 | ACTIVATING interval not counted in active_days |
| `test_billable_days_includes_active_and_activating` | AC-4.2 | Both ACTIVE and ACTIVATING counted |
| `test_billable_days_excludes_inactive` | AC-4.2 | INACTIVE interval not counted |
| `test_days_with_none_classification_excluded` | AC-2.4 | Intervals with `classification=None` excluded |
| `test_open_interval_extends_to_period_end` | AC-4.5 | `exited_at=None` treated as period_end |
| `test_single_day_period` | EC-7 | `period_start == period_end` returns 0 or 1 |
| `test_multi_interval_same_day_dedup` | AC-4.4 | ACTIVE->ACTIVATING on same day counts once |
| `test_future_period_with_open_interval` | EC-9 | Future dates counted for open intervals |
| `test_inclusive_boundaries` | EC-10 | Period start/end dates are inclusive |
| `test_offer_goes_inactive_mid_period` | EC-6 | Only pre-transition days counted |
| `test_never_moved_active` | EC-1 | Imputed ACTIVE: full period length |
| `test_never_moved_inactive` | EC-2 | Imputed INACTIVE: 0 days |
| `test_never_moved_activating` | AC-3.5 | Imputed ACTIVATING: 0 active, full billable |
| `test_offer_timeline_entry_serialization` | API contract | Pydantic model serializes correctly |
| `test_offer_timeline_entry_null_phone` | EC-5 | `office_phone: null` in serialized output |

**Test data setup**: Direct construction of `SectionInterval` and `SectionTimeline` objects with `datetime` and `AccountActivity` values. No mocking needed -- these are pure value objects.

### 13.2 `tests/unit/services/test_section_timeline_service.py`

Unit tests for service functions (mocked `AsanaClient`).

| Test Function | Covers | Description |
|--------------|--------|-------------|
| `test_is_cross_project_noise_both_none` | AC-1.3, EC-3 | Both sections unknown -> filtered |
| `test_is_cross_project_noise_one_known` | AC-1.4, EC-4 | One section known -> retained |
| `test_build_intervals_chronological` | AC-2.5 | Stories sorted and intervals built correctly |
| `test_build_intervals_closes_previous` | AC-2.5 | Previous interval `exited_at` set to current `entered_at` |
| `test_build_intervals_last_open` | AC-2.6 | Final interval has `exited_at=None` |
| `test_build_intervals_unknown_section_warning` | AC-2.3 | WARNING logged for unknown sections |
| `test_build_imputed_interval_active` | AC-3.1, AC-3.4 | Imputed ACTIVE interval from task created_at |
| `test_build_imputed_interval_inactive` | AC-3.3 | Imputed INACTIVE interval contributes 0 days |
| `test_build_timeline_for_offer_with_stories` | FR-1, FR-2 | End-to-end single offer timeline |
| `test_build_timeline_for_offer_never_moved` | FR-3 | Imputation when no section_changed stories |
| `test_get_section_timelines_full` | FR-4, FR-5 | Full pipeline with mocked offers |
| `test_get_section_timelines_individual_failure` | AC-7.6 | Failed offer logged, others succeed |
| `test_warm_story_caches_progress` | FR-7 | Progress callback invoked once after gather completes |
| `test_warm_story_caches_individual_failure` | AC-7.6 | Failed warm logged, others succeed (return_exceptions=True) |
| `test_warm_story_caches_parallel_concurrency` | SPIKE | Semaphore(20) limits concurrency; all offers still warmed |
| `test_parse_datetime_iso_format` | Utility | Parses Asana ISO 8601 format |
| `test_parse_datetime_none` | Utility | Returns None for None input |

**Test data setup**: Mock `AsanaClient` with:
- `client.tasks.list_async().collect()` returning `[Task(...)]` with appropriate fields
- `client.stories.list_for_task_cached_async()` returning `[Story(...)]` with section_changed data

### 13.3 `tests/unit/api/test_routes_section_timelines.py`

Route handler tests (FastAPI `TestClient`).

| Test Function | Covers | Description |
|--------------|--------|-------------|
| `test_200_success_response` | FR-6, SC-4 | Valid request returns SuccessResponse |
| `test_422_period_start_after_end` | AC-6.5, EC-8 | Returns VALIDATION_ERROR |
| `test_422_invalid_date_format` | AC-6.4 | FastAPI auto-validates date format |
| `test_503_timeline_not_ready` | AC-6.7, SC-3 | Returns TIMELINE_NOT_READY + Retry-After header |
| `test_503_retry_after_header` | AC-6.7 | `Retry-After: 30` header present |
| `test_503_timeline_warm_failed` | Interview | `timeline_warm_failed=True` → TIMELINE_WARM_FAILED, no Retry-After |
| `test_502_asana_error` | AC-6.6 | AsanaError mapped to UPSTREAM_ERROR |
| `test_readiness_gate_below_threshold` | AC-7.4 | < 50% -> NOT_READY -> 503 |
| `test_readiness_gate_above_threshold` | AC-7.4 | >= 50% -> READY -> proceeds |
| `test_readiness_gate_zero_total` | Edge case | total=0 -> NOT_READY |
| `test_readiness_gate_failed_state` | Interview | `timeline_warm_failed` takes priority over threshold check |
| `test_response_includes_null_phone` | EC-5, AC-5.4 | `office_phone: null` in response |
| `test_auth_required` | AC-6.8 | Missing auth -> 401 |

**Test data setup**: Use `unittest.mock.patch` to mock:
- `get_section_timelines()` return value for 200 tests
- `app.state.timeline_warm_count` / `app.state.timeline_total` for readiness gate tests
- `AsanaError` raise for 502 tests

---

## 14. ADR: Section Timeline Day Counting Strategy

### Context

The SectionTimeline primitive needs to count calendar days where an offer occupied a specific category of Asana section. Intervals can overlap on boundary dates (an offer moves from ACTIVE to ACTIVATING at 3pm -- both intervals touch that date). The PRD specifies that such days count once in both `active_section_days` and `billable_section_days`.

### Decision

Use `set[date]` deduplication: iterate each qualifying interval, generate all dates in the overlap with the query period, and add them to a `set[date]`. The final count is `len(days)`.

### Rationale

1. **Correctness**: Set deduplication handles all edge cases (same-day transitions, overlapping intervals) with zero special-case code.
2. **Simplicity**: The implementation is 15 lines and directly maps to the PRD specification.
3. **Performance**: Maximum practical cost is ~365 date objects per offer per year. For 500 offers, that is 182,500 set insertions -- completed in < 50ms total.
4. **Testability**: Every edge case (EC-6 through EC-10) reduces to constructing intervals and asserting `len(days)`.

### Consequences

- Positive: Trivially verifiable, no off-by-one risk from interval arithmetic.
- Positive: Naturally handles the `exited_at=None` case (just clamp to `period_end`).
- Negative: O(days) memory per offer (bounded at ~365 date objects = ~10KB). Acceptable.

---

## 15. ADR: Pre-Warm Architecture for Story Caches

### Context

The section timeline endpoint requires story data for every offer in the Business Offers project. Without pre-warming, the first request would trigger ~500 Asana API calls (one per offer), taking 5-10 minutes. The existing codebase has a `cache_warming` background task pattern for DataFrames.

### Decision

Launch a separate `asyncio.Task` during lifespan startup (after entity discovery) that sequentially warms story caches. Track progress on `app.state.timeline_warm_count` / `app.state.timeline_total`. Gate endpoint at 50% threshold.

### Rationale

1. **Non-blocking startup**: ECS health checks pass immediately; the timeline endpoint returns 503 until ready.
2. **Sequential fetching**: Avoids rate limit saturation from concurrent story fetches. The incremental cache ensures subsequent requests are fast.
3. **50% threshold**: Balances "available quickly" with "meaningful data." At 50%, at least half the offers return accurate results; the rest use the cache as it continues warming.
4. **Separate task from DataFrames**: The story warm and DataFrame warm are independent. Combining them would couple their failure modes and complicate progress tracking.

### Consequences

- Positive: Follows established pattern (`cache_warming_task`), minimal new infrastructure.
- Positive: Story caches persist across requests via `StoriesClient` incremental cache.
- Negative: First deployment has ~1-2 minute warm-up before endpoint is ready.
- Negative: Sequential fetching is slower than concurrent; could be parallelized later if needed.

---

## 16. Handoff Checklist

- [x] TDD covers all PRD requirements (FR-1 through FR-7, all ACs)
- [x] Component boundaries and responsibilities are clear (model / service / route / lifespan)
- [x] Data model defined with exact types and method signatures
- [x] API contract specified (endpoint, params, responses, errors)
- [x] ADRs document significant decisions (day counting, pre-warm)
- [x] Risks identified: rate limiting during warm-up (mitigated by sequential fetching), bot PAT availability (mitigated by graceful skip)
- [x] Integration points reference actual existing code with file paths and signatures
- [x] File inventory lists every new and modified file
- [x] Test coverage plan maps to FRs and ECs
- [x] Principal Engineer can implement directly from this TDD without architectural questions

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD-SECTION-TIMELINE | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-SECTION-TIMELINE.md` | Yes (written) |
| PRD-SECTION-TIMELINE | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-SECTION-TIMELINE.md` | Yes (Read-verified) |
