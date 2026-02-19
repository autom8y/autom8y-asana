"""Route handler tests for section timeline endpoint.

Per TDD-SECTION-TIMELINE-001 Section 13.3: Tests for the
GET /api/v1/offers/section-timelines endpoint using FastAPI TestClient.

Architecture (DEF-006 fix): The endpoint reads pre-computed SectionTimeline
objects from app.state.offer_timelines. No mock client needed — tests set
app.state.offer_timelines with pre-built test data.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.routes.section_timelines import router
from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.business.section_timeline import (
    SectionInterval,
    SectionTimeline,
)

# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_timeline(
    offer_gid: str = "offer1",
    office_phone: str | None = "555-0100",
    section_name: str = "ACTIVE",
    classification: AccountActivity | None = AccountActivity.ACTIVE,
    entered_at: datetime | None = None,
    exited_at: datetime | None = None,
) -> tuple[str, str | None, SectionTimeline]:
    """Build a pre-computed (offer_gid, office_phone, SectionTimeline) tuple."""
    if entered_at is None:
        entered_at = datetime(2025, 1, 1, tzinfo=UTC)
    interval = SectionInterval(
        section_name=section_name,
        classification=classification,
        entered_at=entered_at,
        exited_at=exited_at,
    )
    timeline = SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        intervals=(interval,),
        task_created_at=entered_at,
        story_count=1,
    )
    return (offer_gid, office_phone, timeline)


def _create_test_app(
    *,
    timeline_warm_count: int = 100,
    timeline_total: int = 100,
    timeline_warm_failed: bool = False,
    offer_timelines: list[tuple[str, str | None, SectionTimeline]] | None = None,
) -> FastAPI:
    """Create a minimal FastAPI app with the section_timelines router.

    Configures app.state for readiness gate testing.
    """
    from autom8_asana.api.dependencies import get_request_id

    app = FastAPI()
    app.include_router(router)

    # Set readiness state
    app.state.timeline_warm_count = timeline_warm_count
    app.state.timeline_total = timeline_total
    app.state.timeline_warm_failed = timeline_warm_failed

    # Set pre-computed timelines (DEF-006 architecture)
    if offer_timelines is not None:
        app.state.offer_timelines = offer_timelines
    else:
        app.state.offer_timelines = []

    # Override request_id dependency
    async def _mock_request_id() -> str:
        return "test-request-id-123"

    app.dependency_overrides[get_request_id] = _mock_request_id

    return app


# ---------------------------------------------------------------------------
# 200 Success
# ---------------------------------------------------------------------------


class TestSuccessResponse:
    def test_200_success_response(self) -> None:
        """FR-6, SC-4: Valid request returns SuccessResponse."""
        timelines = [_make_timeline()]
        app = _create_test_app(offer_timelines=timelines)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        result = body["data"]["timelines"]
        assert len(result) == 1
        assert result[0]["offer_gid"] == "offer1"
        # Entire Jan 2025 in ACTIVE section -> 31 active days
        assert result[0]["active_section_days"] == 31
        assert result[0]["billable_section_days"] == 31

    def test_response_includes_null_phone(self) -> None:
        """EC-5, AC-5.4: office_phone: null in response."""
        timelines = [_make_timeline(office_phone=None)]
        app = _create_test_app(offer_timelines=timelines)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        result = response.json()["data"]["timelines"]
        assert result[0]["office_phone"] is None


# ---------------------------------------------------------------------------
# 422 Validation Errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_200_period_start_equals_end(self) -> None:
        """D-002: period_start == period_end is valid (strict > check, not >=)."""
        timelines = [_make_timeline()]
        app = _create_test_app(offer_timelines=timelines)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-05",
                    "period_end": "2025-01-05",
                },
            )

        assert response.status_code == 200

    def test_422_period_start_after_end(self) -> None:
        """AC-6.5, EC-8: Returns VALIDATION_ERROR."""
        app = _create_test_app()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-02-01",
                    "period_end": "2025-01-01",
                },
            )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["error"] == "VALIDATION_ERROR"
        assert "period_start" in detail["message"]

    def test_422_invalid_date_format(self) -> None:
        """AC-6.4: FastAPI auto-validates date format."""
        app = _create_test_app()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "not-a-date",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 503 Readiness Gate
# ---------------------------------------------------------------------------


class TestReadinessGate:
    def test_503_timeline_not_ready(self) -> None:
        """AC-6.7, SC-3: Returns TIMELINE_NOT_READY + Retry-After header."""
        app = _create_test_app(
            timeline_warm_count=10,
            timeline_total=100,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "TIMELINE_NOT_READY"

    def test_503_retry_after_header(self) -> None:
        """AC-6.7: Retry-After: 30 header present."""
        app = _create_test_app(
            timeline_warm_count=10,
            timeline_total=100,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 503
        assert response.headers.get("retry-after") == "30"

    def test_503_timeline_warm_failed(self) -> None:
        """Interview: timeline_warm_failed=True -> TIMELINE_WARM_FAILED, no Retry-After."""
        app = _create_test_app(timeline_warm_failed=True)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "TIMELINE_WARM_FAILED"
        # WARM_FAILED should NOT have Retry-After (permanent failure)
        assert "retry-after" not in response.headers

    def test_readiness_gate_below_threshold(self) -> None:
        """AC-7.4: < 50% -> NOT_READY -> 503."""
        app = _create_test_app(
            timeline_warm_count=49,
            timeline_total=100,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "TIMELINE_NOT_READY"

    def test_readiness_gate_above_threshold(self) -> None:
        """AC-7.4: >= 50% -> READY -> proceeds."""
        timelines = [_make_timeline()]
        app = _create_test_app(
            timeline_warm_count=50,
            timeline_total=100,
            offer_timelines=timelines,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200

    def test_readiness_gate_zero_total(self) -> None:
        """Edge case: total=0 -> NOT_READY."""
        app = _create_test_app(
            timeline_warm_count=0,
            timeline_total=0,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "TIMELINE_NOT_READY"

    def test_readiness_gate_failed_state_priority(self) -> None:
        """Interview: timeline_warm_failed takes priority over threshold check."""
        app = _create_test_app(
            timeline_warm_count=100,
            timeline_total=100,
            timeline_warm_failed=True,
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "TIMELINE_WARM_FAILED"
