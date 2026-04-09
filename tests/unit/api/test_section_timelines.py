"""Tests for section timelines endpoint.

Tests for S-3 (current_section/current_classification in response) and
S-1 (classification query parameter validation and filtering).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

from autom8_asana.models.business.section_timeline import OfferTimelineEntry

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _mock_entries() -> list[OfferTimelineEntry]:
    """Build a representative set of OfferTimelineEntry for testing."""
    return [
        OfferTimelineEntry(
            offer_gid="active_1",
            office_phone="555-0100",
            offer_id="OFR-001",
            active_section_days=10,
            billable_section_days=10,
            current_section="ACTIVE",
            current_classification="active",
        ),
        OfferTimelineEntry(
            offer_gid="activating_1",
            office_phone=None,
            offer_id=None,
            active_section_days=0,
            billable_section_days=5,
            current_section="ACTIVATING",
            current_classification="activating",
        ),
        OfferTimelineEntry(
            offer_gid="inactive_1",
            office_phone="555-0200",
            offer_id=None,
            active_section_days=0,
            billable_section_days=0,
            current_section="INACTIVE",
            current_classification="inactive",
        ),
    ]


class TestSectionTimelinesClassificationParam:
    """S-1: classification query parameter validation at route level."""

    def test_invalid_classification_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Invalid classification value returns 422 VALIDATION_ERROR."""
        client, _ = authed_client

        response = client.get(
            "/api/v1/offers/section-timelines",
            params={
                "period_start": "2025-01-01",
                "period_end": "2025-01-31",
                "classification": "bogus",
            },
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["error"]["code"] == "VALIDATION_ERROR"
        assert "bogus" in detail["error"]["message"]

    def test_valid_classification_accepted(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Valid classification value is accepted and passed to service."""
        client, _ = authed_client
        entries = [
            OfferTimelineEntry(
                offer_gid="active_1",
                office_phone=None,
                active_section_days=5,
                billable_section_days=5,
                current_section="ACTIVE",
                current_classification="active",
            ),
        ]

        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ) as mock_compute:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                    "classification": "active",
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["timelines"]) == 1
        # Verify classification_filter was passed through
        mock_compute.assert_called_once()
        call_kwargs = mock_compute.call_args.kwargs
        assert call_kwargs["classification_filter"] == "active"

    def test_no_classification_passes_none(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """No classification param passes None to service (backward compat)."""
        client, _ = authed_client
        entries = _mock_entries()

        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ) as mock_compute:
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["timelines"]) == 3  # all entries returned
        call_kwargs = mock_compute.call_args.kwargs
        assert call_kwargs["classification_filter"] is None


class TestSectionTimelinesResponseFields:
    """S-3: current_section and current_classification appear in response."""

    def test_current_fields_in_response(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Response includes current_section and current_classification fields."""
        client, _ = authed_client
        entries = _mock_entries()

        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        timelines = response.json()["data"]["timelines"]

        active_entry = next(t for t in timelines if t["offer_gid"] == "active_1")
        assert active_entry["current_section"] == "ACTIVE"
        assert active_entry["current_classification"] == "active"

        activating_entry = next(
            t for t in timelines if t["offer_gid"] == "activating_1"
        )
        assert activating_entry["current_section"] == "ACTIVATING"
        assert activating_entry["current_classification"] == "activating"

    def test_null_current_fields_in_response(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Entries without current_section have null in response."""
        client, _ = authed_client
        entries = [
            OfferTimelineEntry(
                offer_gid="unknown_1",
                office_phone=None,
                active_section_days=0,
                billable_section_days=0,
                current_section=None,
                current_classification=None,
            ),
        ]

        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        entry = response.json()["data"]["timelines"][0]
        assert entry["current_section"] is None
        assert entry["current_classification"] is None


class TestSectionTimelinesOfferIdField:
    """SC-6: offer_id appears in API response."""

    def test_offer_id_in_response(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """offer_id appears in response JSON for each timeline entry."""
        client, _ = authed_client
        entries = _mock_entries()

        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        timelines = response.json()["data"]["timelines"]

        active_entry = next(t for t in timelines if t["offer_gid"] == "active_1")
        assert active_entry["offer_id"] == "OFR-001"

    def test_offer_id_null_in_response(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """offer_id: null for entries without offer_id."""
        client, _ = authed_client
        entries = _mock_entries()

        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
            response = client.get(
                "/api/v1/offers/section-timelines",
                params={
                    "period_start": "2025-01-01",
                    "period_end": "2025-01-31",
                },
            )

        assert response.status_code == 200
        timelines = response.json()["data"]["timelines"]

        activating_entry = next(
            t for t in timelines if t["offer_gid"] == "activating_1"
        )
        assert activating_entry["offer_id"] is None
