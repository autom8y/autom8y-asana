"""Route handler tests for section timeline endpoint.

Per TDD-SECTION-TIMELINE-REMEDIATION: Tests for the remediated
GET /api/v1/offers/section-timelines endpoint.

- 200 success (mock get_or_compute_timelines)
- 422 validation (period_start > period_end)
- 502 upstream error (task enumeration failure)
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.routes.section_timelines import router
from autom8_asana.client import AsanaClient
from autom8_asana.models.business.section_timeline import OfferTimelineEntry

# ---------------------------------------------------------------------------
# App fixture with DI overrides
# ---------------------------------------------------------------------------


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with DI overrides for testing."""
    app = FastAPI()

    # Override DI dependencies to avoid auth/client setup
    mock_client = MagicMock(spec=AsanaClient)

    async def override_client() -> AsanaClient:
        return mock_client

    async def override_request_id() -> str:
        return "test-request-id"

    app.dependency_overrides[AsanaClientDualMode.__metadata__[0].dependency] = override_client  # type: ignore[index]
    app.dependency_overrides[RequestId.__metadata__[0].dependency] = override_request_id  # type: ignore[index]

    app.include_router(router)
    return app


@pytest.fixture
def app() -> FastAPI:
    return _create_test_app()


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 200 Success
# ---------------------------------------------------------------------------


class TestSuccessResponse:
    def test_200_returns_timelines(self, test_client: TestClient) -> None:
        """GET with valid params returns 200 with timeline data."""
        mock_entries = [
            OfferTimelineEntry(
                offer_gid="offer1",
                office_phone="555-0100",
                active_section_days=15,
                billable_section_days=20,
            )
        ]

        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=mock_entries,
        ):
            response = test_client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        body = response.json()
        # SuccessResponse envelope: {"data": {...}, "meta": {...}}
        timelines = body["data"]["timelines"]
        assert len(timelines) == 1
        assert timelines[0]["offer_gid"] == "offer1"
        assert timelines[0]["active_section_days"] == 15
        assert timelines[0]["billable_section_days"] == 20
        # Meta should include request_id
        assert "meta" in body
        assert body["meta"]["request_id"] == "test-request-id"

    def test_200_empty_timelines(self, test_client: TestClient) -> None:
        """EC-2: Both caches cold returns 200 with empty timelines list."""
        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = test_client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["timelines"] == []


# ---------------------------------------------------------------------------
# 422 Validation
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_422_period_start_after_end(self, test_client: TestClient) -> None:
        """period_start > period_end returns 422 VALIDATION_ERROR."""
        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
        ):
            response = test_client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-02-01",
                    "period_end": "2025-01-01",
                },
            )

        assert response.status_code == 422
        body = response.json()
        assert body["detail"]["error"]["code"] == "VALIDATION_ERROR"

    def test_422_missing_period_start(self, test_client: TestClient) -> None:
        """Missing period_start returns 422."""
        response = test_client.get(
            "/api/v1/offers/section-timelines",
            params={"period_end": "2025-01-31"},
        )
        assert response.status_code == 422

    def test_422_missing_period_end(self, test_client: TestClient) -> None:
        """Missing period_end returns 422."""
        response = test_client.get(
            "/api/v1/offers/section-timelines",
            params={"period_start": "2025-01-01"},
        )
        assert response.status_code == 422

    def test_422_invalid_date_format(self, test_client: TestClient) -> None:
        """Invalid date format returns 422."""
        response = test_client.get(
            "/api/v1/offers/section-timelines",
            params={
                "period_start": "not-a-date",
                "period_end": "2025-01-31",
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 502 Upstream Error
# ---------------------------------------------------------------------------


class TestUpstreamErrors:
    def test_502_on_computation_failure(self, test_client: TestClient) -> None:
        """Asana API failure during computation returns 502."""
        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Asana API connection failed"),
        ):
            response = test_client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 502
        body = response.json()
        assert body["detail"]["error"]["code"] == "UPSTREAM_ERROR"
