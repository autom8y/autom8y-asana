"""Section timeline endpoint for offer activity tracking.

Per TDD-SECTION-TIMELINE-001 / FR-6: Exposes timeline data for all
offers in the Business Offers project.

Per TDD-SECTION-TIMELINE-REMEDIATION: Migrated off app.state to
compute-on-read-then-cache architecture. No warm-up pipeline, no
readiness gates -- the endpoint computes on first request and serves
from derived cache on subsequent requests.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.models.business.section_timeline import OfferTimelineEntry
from autom8_asana.services.section_timeline_service import (
    BUSINESS_OFFERS_PROJECT_GID,
    get_or_compute_timelines,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/offers", tags=["offers"])


class SectionTimelinesResponse(BaseModel):
    """Response wrapper for section timeline data.

    Attributes:
        timelines: List of timeline entries for all offers.
    """

    timelines: list[OfferTimelineEntry] = Field(
        ..., description="Timeline entries for all offers"
    )

    model_config = {"extra": "forbid"}


@router.get(
    "/section-timelines",
    summary="Get section timelines for all offers",
    response_model=SuccessResponse[SectionTimelinesResponse],
)
async def get_offer_section_timelines(
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

    Per TDD-SECTION-TIMELINE-REMEDIATION: Reads from derived cache on
    warm path (<2s). On cold cache, computes on demand from cached stories
    (<5s) and stores result for subsequent requests.

    Args:
        client: AsanaClient for task enumeration on cache miss.
        request_id: Request correlation ID.
        period_start: Start date for day counting (inclusive).
        period_end: End date for day counting (inclusive).

    Returns:
        SuccessResponse containing list of OfferTimelineEntry.

    Raises:
        HTTPException: 422 if period_start > period_end.
        HTTPException: 502 if Asana API fails during task enumeration.
    """
    start_time = time.perf_counter()

    # Validate period_start <= period_end
    if period_start > period_end:
        raise_api_error(
            request_id,
            422,
            "VALIDATION_ERROR",
            "period_start must be <= period_end",
        )

    try:
        entries = await get_or_compute_timelines(
            client=client,
            project_gid=BUSINESS_OFFERS_PROJECT_GID,
            classifier_name="offer",
            period_start=period_start,
            period_end=period_end,
        )
    except Exception:
        logger.exception(
            "section_timelines_computation_failed",
            extra={
                "request_id": request_id,
                "project_gid": BUSINESS_OFFERS_PROJECT_GID,
            },
        )
        raise_api_error(
            request_id,
            502,
            "UPSTREAM_ERROR",
            "Failed to compute section timelines",
        )

    duration_ms = (time.perf_counter() - start_time) * 1000

    # Structured logging for endpoint completion
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
