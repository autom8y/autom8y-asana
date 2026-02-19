"""Route handler tests for section timeline endpoint.

Per TDD-SECTION-TIMELINE-001 Section 13.3: Tests for the
GET /api/v1/offers/section-timelines endpoint using FastAPI TestClient.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.routes.section_timelines import router
from autom8_asana.exceptions import AsanaError
from autom8_asana.models.business.section_timeline import OfferTimelineEntry


# ---------------------------------------------------------------------------
# Test Application Factory
# ---------------------------------------------------------------------------


def _create_test_app(
    *,
    timeline_warm_count: int = 100,
    timeline_total: int = 100,
    timeline_warm_failed: bool = False,
) -> FastAPI:
    """Create a minimal FastAPI app with the section_timelines router.

    Configures app.state for readiness gate testing and provides
    dependency overrides for AsanaClientDualMode and RequestId.
    """
    from autom8_asana.api.dependencies import (
        get_asana_client_from_context,
        get_request_id,
    )

    app = FastAPI()
    app.include_router(router)

    # Set readiness state
    app.state.timeline_warm_count = timeline_warm_count
    app.state.timeline_total = timeline_total
    app.state.timeline_warm_failed = timeline_warm_failed

    # Override request_id dependency
    async def _mock_request_id() -> str:
        return "test-request-id-123"

    app.dependency_overrides[get_request_id] = _mock_request_id

    return app


def _override_client(app: FastAPI, mock_client: MagicMock) -> None:
    """Override the AsanaClientDualMode dependency with a mock."""
    from autom8_asana.api.dependencies import get_asana_client_from_context

    async def _mock_get_client():
        yield mock_client

    app.dependency_overrides[get_asana_client_from_context] = _mock_get_client


# ---------------------------------------------------------------------------
# 200 Success
# ---------------------------------------------------------------------------


class TestSuccessResponse:
    def test_200_success_response(self) -> None:
        """FR-6, SC-4: Valid request returns SuccessResponse."""
        app = _create_test_app()
        mock_client = MagicMock()
        _override_client(app, mock_client)

        entries = [
            OfferTimelineEntry(
                offer_gid="offer1",
                office_phone="555-0100",
                active_section_days=7,
                billable_section_days=10,
            ),
        ]

        with patch(
            "autom8_asana.api.routes.section_timelines.get_section_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
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
        timelines = body["data"]["timelines"]
        assert len(timelines) == 1
        assert timelines[0]["offer_gid"] == "offer1"
        assert timelines[0]["active_section_days"] == 7
        assert timelines[0]["billable_section_days"] == 10

    def test_response_includes_null_phone(self) -> None:
        """EC-5, AC-5.4: office_phone: null in response."""
        app = _create_test_app()
        mock_client = MagicMock()
        _override_client(app, mock_client)

        entries = [
            OfferTimelineEntry(
                offer_gid="offer1",
                office_phone=None,
                active_section_days=0,
                billable_section_days=0,
            ),
        ]

        with patch(
            "autom8_asana.api.routes.section_timelines.get_section_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/offers/section-timelines",
                    params={
                        "period_start": "2025-01-01",
                        "period_end": "2025-01-31",
                    },
                )

        assert response.status_code == 200
        timelines = response.json()["data"]["timelines"]
        assert timelines[0]["office_phone"] is None


# ---------------------------------------------------------------------------
# 422 Validation Errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_200_period_start_equals_end(self) -> None:
        """D-002: period_start == period_end is valid (strict > check, not >=)."""
        app = _create_test_app()
        mock_client = MagicMock()
        _override_client(app, mock_client)

        with patch(
            "autom8_asana.api.routes.section_timelines.get_section_timelines",
            new_callable=AsyncMock,
            return_value=[],
        ):
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
        mock_client = MagicMock()
        _override_client(app, mock_client)

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
        mock_client = MagicMock()
        _override_client(app, mock_client)

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
        mock_client = MagicMock()
        _override_client(app, mock_client)

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
        mock_client = MagicMock()
        _override_client(app, mock_client)

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
        app = _create_test_app(
            timeline_warm_failed=True,
        )
        mock_client = MagicMock()
        _override_client(app, mock_client)

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
        mock_client = MagicMock()
        _override_client(app, mock_client)

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
        app = _create_test_app(
            timeline_warm_count=50,
            timeline_total=100,
        )
        mock_client = MagicMock()
        _override_client(app, mock_client)

        entries = [
            OfferTimelineEntry(
                offer_gid="offer1",
                office_phone=None,
                active_section_days=5,
                billable_section_days=5,
            ),
        ]

        with patch(
            "autom8_asana.api.routes.section_timelines.get_section_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
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
        mock_client = MagicMock()
        _override_client(app, mock_client)

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
        # Even though warm_count/total >= 50%, warm_failed should win
        app = _create_test_app(
            timeline_warm_count=100,
            timeline_total=100,
            timeline_warm_failed=True,
        )
        mock_client = MagicMock()
        _override_client(app, mock_client)

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


# ---------------------------------------------------------------------------
# 502 Upstream Error
# ---------------------------------------------------------------------------


class TestUpstreamError:
    def test_502_asana_error(self) -> None:
        """AC-6.6: AsanaError mapped to UPSTREAM_ERROR."""
        app = _create_test_app()
        mock_client = MagicMock()
        _override_client(app, mock_client)

        with patch(
            "autom8_asana.api.routes.section_timelines.get_section_timelines",
            new_callable=AsyncMock,
            side_effect=AsanaError("API down"),
        ):
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/offers/section-timelines",
                    params={
                        "period_start": "2025-01-01",
                        "period_end": "2025-01-31",
                    },
                )

        assert response.status_code == 502
        detail = response.json()["detail"]
        assert detail["error"] == "UPSTREAM_ERROR"
