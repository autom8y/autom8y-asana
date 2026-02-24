"""Tests for GET /v1/query/{entity_type}/sections endpoint.

Per AUTOM8_QUERY WS-C deliverable C-2 (AC-9.4):
- Returns section names and classifications for entity types with classifiers
- Returns 404 for entity types without section classifiers
- Requires service token authentication
- Shares logic with CLI 'sections' subcommand via introspection module
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


JWT_TOKEN = "header.payload.signature"


class TestSectionsEndpoint:
    """Test GET /v1/query/{entity_type}/sections endpoint."""

    def test_offer_sections(self, client: TestClient) -> None:
        """Offer entity returns sections with classifications."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/query/offer/sections",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "entity_type" in body
        assert body["entity_type"] == "offer"
        data = body["data"]
        assert isinstance(data, list)
        assert len(data) > 0

        # All entries have required keys
        for entry in data:
            assert "section_name" in entry
            assert "classification" in entry

        # Check known sections exist
        section_names = {e["section_name"] for e in data}
        assert "active" in section_names

        # Check classifications are valid values
        valid_classifications = {"active", "activating", "inactive", "ignored"}
        for entry in data:
            assert entry["classification"] in valid_classifications

    def test_unit_sections(self, client: TestClient) -> None:
        """Unit entity returns unit-specific sections."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/query/unit/sections",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        section_names = {e["section_name"] for e in data}
        # Unit-specific sections should exist
        assert "active" in section_names or "onboarding" in section_names

    def test_entity_without_classifier_returns_404(self, client: TestClient) -> None:
        """Entity type without SectionClassifier returns 404."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/query/business/sections",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

        assert response.status_code == 404
        body = response.json()
        # FastAPI wraps HTTPException detail in a "detail" key
        detail = body["detail"]
        assert detail["error"] == "NO_SECTION_CLASSIFIER"
        assert "No section classifier" in detail["message"]

    def test_missing_auth_returns_401(self, client: TestClient) -> None:
        """Request without Authorization header returns 401."""
        response = client.get("/v1/query/offer/sections")
        assert response.status_code == 401

    def test_response_includes_entity_type(self, client: TestClient) -> None:
        """Response body includes entity_type field for context."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/query/offer/sections",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

        body = response.json()
        assert body["entity_type"] == "offer"
