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
from datetime import (
    date,  # noqa: TC003 — FastAPI needs this at runtime for query param validation
)
from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    AsanaClientDualMode,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.models.business.activity import AccountActivity
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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "timelines": [
                        {
                            "offer_gid": "1234567890123456",
                            "office_phone": "+15551234567",
                            "offer_id": "OFF-0042",
                            "active_section_days": 18,
                            "billable_section_days": 22,
                            "current_section": "ACTIVE",
                            "current_classification": "active",
                        }
                    ]
                }
            ]
        },
    )


@router.get(
    "/section-timelines",
    summary="Get section timelines for all offers",
    response_description="Section timeline entries for all offers in the period",
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
    classification: Annotated[
        str | None,
        Query(
            description=(
                "Filter by current classification "
                "(active, activating, inactive, ignored)"
            )
        ),
    ] = None,
) -> SuccessResponse[SectionTimelinesResponse]:
    """Get section timelines for all offers in the Business Offers project.

    Computes ``active_section_days`` and ``billable_section_days`` for
    each offer by replaying its Asana section history within the specified
    date range. Each entry also reports the offer's ``current_section`` and
    ``current_classification``.

    **Performance**: Results are cached after the first computation.

    - Warm path (cache hit): < 2 seconds.
    - Cold path (cache miss): < 5 seconds. The endpoint computes on demand
      from cached task stories, then stores the result for reuse.

    **Classification filter**: When provided, only entries whose current
    section matches the requested classification are returned. Valid values:
    ``active``, ``activating``, ``inactive``, ``ignored``.

    Requires Bearer token authentication (JWT or PAT).

    Args:
        period_start: Start date for day counting (inclusive, YYYY-MM-DD).
        period_end: End date for day counting (inclusive, YYYY-MM-DD).
        classification: Optional classification filter.

    Returns:
        List of ``OfferTimelineEntry`` records for the period.

    Raises:
        422: ``period_start`` is after ``period_end``.
        422: ``classification`` is not a valid ``AccountActivity`` value.
        502: Asana API failed during on-demand task enumeration.
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

    # Normalize to lowercase for case-insensitive matching
    if classification is not None:
        classification = classification.lower()
    _VALID_CLASSIFICATIONS = {e.value for e in AccountActivity}
    if classification is not None and classification not in _VALID_CLASSIFICATIONS:
        raise_api_error(
            request_id,
            422,
            "VALIDATION_ERROR",
            f"Invalid classification '{classification}'. "
            f"Valid values: {', '.join(sorted(_VALID_CLASSIFICATIONS))}",
        )

    try:
        entries = await get_or_compute_timelines(
            client=client,
            project_gid=BUSINESS_OFFERS_PROJECT_GID,
            classifier_name="offer",
            period_start=period_start,
            period_end=period_end,
            classification_filter=classification,
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
            "classification": classification,
            "duration_ms": round(duration_ms, 1),
        },
    )

    response_data = SectionTimelinesResponse(timelines=entries)
    return build_success_response(data=response_data, request_id=request_id)


__all__ = ["router"]
