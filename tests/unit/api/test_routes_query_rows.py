"""Integration tests for POST /v1/query/{entity_type}/rows endpoint.

Per TDD Section 11.5 (TC-I001 through TC-I020):
- TC-I001: Basic /rows query with eq predicate
- TC-I002: /rows with section parameter
- TC-I003: /rows with nested AND/OR predicate
- TC-I004: /rows with unknown field in predicate
- TC-I005: /rows with invalid operator for dtype
- TC-I006: /rows with coercion failure
- TC-I007: /rows with unknown section
- TC-I008: /rows with depth > 5
- TC-I009: /rows with no predicate (all rows)
- TC-I010: /rows with empty array predicate
- TC-I011: /rows pagination (limit + offset)
- TC-I012: /rows select fields with gid always included
- TC-I013: /rows cache not warm
- TC-I014: /rows missing auth
- TC-I015: /rows PAT token rejected
- TC-I016: /rows response meta includes query_ms
- TC-I017: Existing /query/{et} still works
- TC-I018: Existing /query/{et} has deprecation headers
- TC-I019: /rows with flat array sugar predicate
- TC-I020: /rows with in operator
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _create_mock_dataframe() -> pl.DataFrame:
    """Create a mock DataFrame for testing with offer-like columns."""
    return pl.DataFrame(
        {
            "gid": [
                "1234567890123456",
                "1234567890123457",
                "1234567890123458",
                "1234567890123459",
            ],
            "name": [
                "Acme Dental - Facebook",
                "Beta Medical - Google",
                "Gamma Dental - Google",
                "Delta Medical - Facebook",
            ],
            "section": ["ACTIVE", "ACTIVE", "PAUSED", "ACTIVE"],
            "vertical": ["dental", "medical", "dental", "medical"],
            "office_phone": [
                "+15551234567",
                "+15559876543",
                "+15551111111",
                "+15552222222",
            ],
            "offer_id": ["offer-001", "offer-002", "offer-003", "offer-004"],
        }
    )


JWT_TOKEN = "header.payload.signature"


class TestRowsEndpointBasic:
    """Basic /rows endpoint tests."""

    def test_tc_i001_basic_eq_predicate(self, client: TestClient) -> None:
        """TC-I001: Basic /rows query with eq predicate returns filtered results."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "where": {"field": "vertical", "op": "eq", "value": "dental"},
                    "select": ["gid", "name", "vertical"],
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "data" in data
        assert "meta" in data
        assert data["meta"]["total_count"] == 2
        for record in data["data"]:
            assert record["vertical"] == "dental"

    def test_tc_i002_section_parameter(self, client: TestClient) -> None:
        """TC-I002: /rows with section parameter filters by section."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
            # Mock section resolution to succeed
            patch(
                "autom8_asana.services.query_service.resolve_section",
                new_callable=AsyncMock,
                return_value="ACTIVE",
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "section": "ACTIVE",
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["meta"]["total_count"] == 3
        for record in data["data"]:
            assert record["section"] == "ACTIVE"

    def test_tc_i003_nested_and_or_predicate(self, client: TestClient) -> None:
        """TC-I003: /rows with nested AND/OR predicate."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "where": {
                        "and": [
                            {
                                "or": [
                                    {
                                        "field": "vertical",
                                        "op": "eq",
                                        "value": "dental",
                                    },
                                    {
                                        "field": "vertical",
                                        "op": "eq",
                                        "value": "medical",
                                    },
                                ]
                            },
                            {"field": "section", "op": "eq", "value": "ACTIVE"},
                        ]
                    },
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["meta"]["total_count"] == 3

    def test_tc_i009_no_predicate_all_rows(self, client: TestClient) -> None:
        """TC-I009: /rows with no predicate returns all rows."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["meta"]["total_count"] == 4

    def test_tc_i010_empty_array_predicate(self, client: TestClient) -> None:
        """TC-I010: /rows with empty array predicate returns all rows."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"where": []},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["meta"]["total_count"] == 4

    def test_tc_i019_flat_array_sugar(self, client: TestClient) -> None:
        """TC-I019: /rows with flat array sugar predicate treated as AND."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "where": [
                        {"field": "section", "op": "eq", "value": "ACTIVE"},
                        {"field": "vertical", "op": "eq", "value": "dental"},
                    ],
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["meta"]["total_count"] == 1

    def test_tc_i020_in_operator(self, client: TestClient) -> None:
        """TC-I020: /rows with in operator for set membership filtering."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "where": {
                        "field": "vertical",
                        "op": "in",
                        "value": ["dental", "medical"],
                    },
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["meta"]["total_count"] == 4


class TestRowsPagination:
    """Test pagination for /rows endpoint."""

    def test_tc_i011_pagination(self, client: TestClient) -> None:
        """TC-I011: /rows pagination (limit + offset)."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"limit": 2, "offset": 1},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 2
        assert data["meta"]["total_count"] == 4
        assert data["meta"]["limit"] == 2
        assert data["meta"]["offset"] == 1

    def test_tc_i012_select_fields_gid_always_included(
        self, client: TestClient
    ) -> None:
        """TC-I012: /rows select fields with gid always included."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"select": ["name", "vertical"]},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        for record in data["data"]:
            assert "gid" in record  # Always included
            assert "name" in record
            assert "vertical" in record


class TestRowsResponseMeta:
    """Test response metadata for /rows endpoint."""

    def test_tc_i016_query_ms_in_meta(self, client: TestClient) -> None:
        """TC-I016: /rows response meta includes query_ms > 0."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "query_ms" in data["meta"]
        assert data["meta"]["query_ms"] >= 0
        assert data["meta"]["entity_type"] == "offer"
        assert data["meta"]["project_gid"] == "1143843662099250"
        assert data["meta"]["returned_count"] == 4


class TestRowsErrors:
    """Test error responses for /rows endpoint."""

    def test_tc_i004_unknown_field(self, client: TestClient) -> None:
        """TC-I004: /rows with unknown field in predicate -> 422 UNKNOWN_FIELD."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "where": {"field": "nonexistent", "op": "eq", "value": "x"},
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "UNKNOWN_FIELD"
        assert "nonexistent" in data["error"]["message"]

    def test_tc_i005_invalid_operator_for_dtype(self, client: TestClient) -> None:
        """TC-I005: /rows with invalid operator for dtype -> 422 INVALID_OPERATOR."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Use a field we know exists in the offer schema.
            # The offer schema extends base which has 'date' (Date dtype).
            # 'contains' is not valid for Date.
            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "where": {"field": "date", "op": "contains", "value": "2025"},
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "INVALID_OPERATOR"

    def test_tc_i006_coercion_failure(self, client: TestClient) -> None:
        """TC-I006: /rows with coercion failure -> 422 COERCION_FAILED."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # 'date' is Date dtype, "not-a-date" can't be coerced
            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "where": {"field": "date", "op": "eq", "value": "not-a-date"},
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "COERCION_FAILED"

    def test_tc_i007_unknown_section(self, client: TestClient) -> None:
        """TC-I007: /rows with unknown section -> 422 UNKNOWN_SECTION."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
            # Mock resolve_section to raise UnknownSectionError
            patch(
                "autom8_asana.services.query_service.resolve_section",
                new_callable=AsyncMock,
                side_effect=__import__(
                    "autom8_asana.services.errors", fromlist=["UnknownSectionError"]
                ).UnknownSectionError("Nonexistent"),
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"section": "Nonexistent"},
            )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "UNKNOWN_SECTION"

    def test_tc_i008_depth_exceeds_limit(self, client: TestClient) -> None:
        """TC-I008: /rows with depth > 5 -> 400 QUERY_TOO_COMPLEX."""
        mock_df = _create_mock_dataframe()
        leaf = {"field": "name", "op": "eq", "value": "x"}

        # Build depth 6: and -> or -> and -> not -> and -> leaf
        deep = {
            "and": [
                {
                    "or": [
                        {
                            "and": [
                                {
                                    "not": {
                                        "and": [leaf],
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"where": deep},
            )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "QUERY_TOO_COMPLEX"

    def test_tc_i013_cache_not_warm(self, client: TestClient) -> None:
        """TC-I013: /rows cache not warm -> 503 CACHE_NOT_WARMED."""
        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "CACHE_NOT_WARMED"


class TestRowsAuthentication:
    """Test authentication for /rows endpoint."""

    def test_tc_i014_missing_auth(self, client: TestClient) -> None:
        """TC-I014: /rows missing auth -> 401 MISSING_AUTH."""
        response = client.post(
            "/v1/query/offer/rows",
            json={},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTH-MISSING-TOKEN"

    def test_tc_i015_pat_token_rejected(self, client: TestClient) -> None:
        """TC-I015: /rows PAT token -> 401 SERVICE_TOKEN_REQUIRED."""
        pat_token = "0/1234567890abcdef1234567890"
        response = client.post(
            "/v1/query/offer/rows",
            headers={"Authorization": f"Bearer {pat_token}"},
            json={},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "SERVICE_TOKEN_REQUIRED"


class TestDeprecationHeaders:
    """Test deprecation headers on existing endpoint."""

    def test_tc_i017_existing_endpoint_still_works(self, client: TestClient) -> None:
        """TC-I017: Existing /query/{et} still works."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"where": {"section": "ACTIVE"}, "limit": 100},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 3

    def test_tc_i018_deprecation_headers_present(self, client: TestClient) -> None:
        """TC-I018: Existing /query/{et} has deprecation headers."""
        mock_df = _create_mock_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"limit": 100},
            )

        assert response.status_code == 200
        assert response.headers.get("Deprecation") == "true"
        assert response.headers.get("Sunset") == "2026-06-01"
        assert "rows" in response.headers.get("Link", "")


class TestRowsEntityType:
    """Test entity type validation for /rows."""

    def test_unknown_entity_type_returns_404(self, client: TestClient) -> None:
        """Unknown entity type returns 404."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/query/invalid_type/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "UNKNOWN_ENTITY_TYPE"
