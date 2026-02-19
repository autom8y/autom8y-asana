"""Section timeline endpoint for offer activity tracking.

Per TDD-SECTION-TIMELINE-001 / FR-6: Exposes timeline data for all
offers in the Business Offers project.

Architecture (DEF-006 fix): The endpoint reads pre-computed SectionTimeline
objects from app.state.offer_timelines (populated at warm-up time by
build_all_timelines). Request handling is pure CPU day-counting — no I/O.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from autom8_asana.api.dependencies import RequestId
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.models.business.section_timeline import (
    OfferTimelineEntry,
    SectionTimeline,
)
from autom8_asana.services.section_timeline_service import compute_timeline_entries

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


# Readiness state constants
_READY = "ready"
_NOT_READY = "not_ready"
_WARM_FAILED = "warm_failed"


def _check_readiness(request: Request) -> str:
    """Check if story caches are sufficiently warmed.

    Per AC-7.4: Returns READY if >= 50% of offers have cached stories.
    Per interview 2026-02-19: Distinguishes still-warming (NOT_READY)
    from failed warm-up (WARM_FAILED) so callers can distinguish transient
    from permanent error conditions.

    Args:
        request: FastAPI request (for app.state access).

    Returns:
        Readiness state string: _READY, _NOT_READY, or _WARM_FAILED.
    """
    if getattr(request.app.state, "timeline_warm_failed", False):
        return _WARM_FAILED

    warm_count = getattr(request.app.state, "timeline_warm_count", 0)
    total_count = getattr(request.app.state, "timeline_total", 0)

    if total_count == 0:
        return _NOT_READY

    if (warm_count / total_count) >= _READINESS_THRESHOLD:
        return _READY

    return _NOT_READY


@router.get(
    "/section-timelines",
    summary="Get section timelines for all offers",
    response_model=SuccessResponse[SectionTimelinesResponse],
)
async def get_offer_section_timelines(
    request: Request,
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

    Per DEF-006 fix: Reads pre-computed SectionTimeline objects from
    app.state.offer_timelines (built at warm-up). No I/O at request time.

    Args:
        request: FastAPI request.
        request_id: Request correlation ID.
        period_start: Start date for day counting (inclusive).
        period_end: End date for day counting (inclusive).

    Returns:
        SuccessResponse containing list of OfferTimelineEntry.

    Raises:
        HTTPException: 422 if period_start > period_end.
        HTTPException: 503 if timelines are not built yet.
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
    if readiness == _WARM_FAILED:
        raise_api_error(
            request_id,
            503,
            "TIMELINE_WARM_FAILED",
            "Section timeline story cache warm-up failed — operator intervention required",
        )
    elif readiness == _NOT_READY:
        raise_api_error(
            request_id,
            503,
            "TIMELINE_NOT_READY",
            "Section timeline story caches are still warming up",
            details={"retry_after_seconds": _RETRY_AFTER_SECONDS},
            headers={"Retry-After": str(_RETRY_AFTER_SECONDS)},
        )

    # DEF-006 fix: Read pre-computed timelines from app.state (no I/O).
    # build_all_timelines() populates this during warm-up.
    offer_timelines: list[tuple[str, str | None, SectionTimeline]] = getattr(
        request.app.state, "offer_timelines", []
    )

    # FR-4: Pure-CPU day counting against pre-computed timeline data.
    entries = compute_timeline_entries(offer_timelines, period_start, period_end)

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
