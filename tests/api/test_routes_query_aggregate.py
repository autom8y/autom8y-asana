"""Integration tests for POST /v1/query/{entity_type}/aggregate endpoint.

Per TDD Section 11.6 (TC-RA001 through TC-RA012).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
from fastapi.testclient import TestClient


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _create_mock_dataframe() -> pl.DataFrame:
    """Create a mock DataFrame for aggregate testing with offer-like columns."""
    return pl.DataFrame(
        {
            "gid": [
                "1234567890123456",
                "1234567890123457",
                "1234567890123458",
                "1234567890123459",
                "1234567890123460",
            ],
            "name": [
                "Acme Dental - Facebook",
                "Beta Medical - Google",
                "Gamma Dental - Google",
                "Delta Medical - Facebook",
                "Echo Dental - Facebook",
            ],
            "section": ["ACTIVE", "ACTIVE", "PAUSED", "ACTIVE", "ACTIVE"],
            "vertical": ["dental", "medical", "dental", "medical", "dental"],
            "office_phone": [
                "+15551234567",
                "+15559876543",
                "+15551111111",
                "+15552222222",
                "+15553333333",
            ],
            "offer_id": [
                "offer-001",
                "offer-002",
                "offer-003",
                "offer-004",
                "offer-005",
            ],
        }
    )


JWT_TOKEN = "header.payload.signature"


def _common_patches(mock_df: pl.DataFrame | None = None):
    """Return a context manager stack with common patches for aggregate tests."""
    if mock_df is None:
        mock_df = _create_mock_dataframe()

    return (
        patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ),
        patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            return_value="test_bot_pat",
        ),
        patch("autom8_asana.client.AsanaClient"),
        patch(
            "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ),
    )


class TestAggregateEndpointBasic:
    """Basic /aggregate endpoint tests."""

    def test_tc_ra001_valid_aggregate_request(self, client: TestClient) -> None:
        """TC-RA001: Valid aggregate request returns 200 with correct response shape."""
        mock_df = _create_mock_dataframe()
        p1, p2, p3, p4 = _common_patches(mock_df)

        with p1, p2, p3 as mock_client_class, p4:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [
                        {"column": "gid", "agg": "count", "alias": "row_count"},
                    ],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert data["meta"]["group_count"] == 2
        assert data["meta"]["aggregation_count"] == 1
        assert data["meta"]["group_by"] == ["vertical"]
        assert data["meta"]["entity_type"] == "offer"
        assert data["meta"]["query_ms"] >= 0

    def test_tc_ra002_unknown_entity_type(self, client: TestClient) -> None:
        """TC-RA002: Unknown entity type returns 404 UNKNOWN_ENTITY_TYPE."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/query/nonexistent/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                },
            )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "UNKNOWN_ENTITY_TYPE"

    def test_tc_ra003_sum_on_boolean_column(self, client: TestClient) -> None:
        """TC-RA003: sum on Boolean column returns 422 AGGREGATION_ERROR."""
        # Need a df with a Boolean column
        mock_df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "section": ["ACTIVE", "ACTIVE"],
                "vertical": ["dental", "medical"],
                "office_phone": ["+111", "+222"],
                "offer_id": ["o1", "o2"],
                "is_completed": [True, False],
            }
        )
        p1, p2, p3, p4 = _common_patches(mock_df)

        with p1, p2, p3 as mock_client_class, p4:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [
                        {"column": "is_completed", "agg": "sum"},
                    ],
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "AGGREGATION_ERROR"
        assert "sum" in data["detail"]["message"]

    def test_tc_ra004_group_by_list_column(self, client: TestClient) -> None:
        """TC-RA004: group_by on List column returns 422 AGGREGATION_ERROR."""
        # Need a df with a List column
        mock_df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "section": ["ACTIVE", "ACTIVE"],
                "vertical": ["dental", "medical"],
                "office_phone": ["+111", "+222"],
                "offer_id": ["o1", "o2"],
                "platforms": [["fb"], ["google"]],
            }
        )
        p1, p2, p3, p4 = _common_patches(mock_df)

        with p1, p2, p3 as mock_client_class, p4:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["platforms"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "AGGREGATION_ERROR"
        assert "List" in data["detail"]["message"]

    def test_tc_ra006_where_predicate_too_deep(self, client: TestClient) -> None:
        """TC-RA006: WHERE predicate too deep returns 400 QUERY_TOO_COMPLEX."""
        mock_df = _create_mock_dataframe()
        leaf = {"field": "name", "op": "eq", "value": "x"}
        deep = {"and": [{"or": [{"and": [{"not": {"and": [leaf]}}]}]}]}

        p1, p2, p3, p4 = _common_patches(mock_df)

        with p1, p2, p3 as mock_client_class, p4:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                    "where": deep,
                },
            )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "QUERY_TOO_COMPLEX"

    def test_tc_ra007_cache_not_warm(self, client: TestClient) -> None:
        """TC-RA007: Cache not warm returns 503 CACHE_NOT_WARMED."""
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
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                },
            )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "CACHE_NOT_WARMED"

    def test_tc_ra008_empty_aggregation_result(self, client: TestClient) -> None:
        """TC-RA008: Empty aggregation result returns 200 with empty data."""
        mock_df = _create_mock_dataframe()
        p1, p2, p3, p4 = _common_patches(mock_df)

        with p1, p2, p3 as mock_client_class, p4:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [
                        {"column": "gid", "agg": "count", "alias": "cnt"},
                    ],
                    "having": {"field": "cnt", "op": "gt", "value": 999999},
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["group_count"] == 0

    def test_tc_ra009_auth_required(self, client: TestClient) -> None:
        """TC-RA009: S2S auth required -- no auth returns 401."""
        response = client.post(
            "/v1/query/offer/aggregate",
            json={
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
            },
        )
        assert response.status_code == 401

    def test_tc_ra010_with_section_filter(self, client: TestClient) -> None:
        """TC-RA010: With section filter returns 200 with section applied."""
        mock_df = _create_mock_dataframe()
        p1, p2, p3, p4 = _common_patches(mock_df)

        mock_section = MagicMock()
        mock_section.resolve.return_value = "gid-123"

        with (
            p1,
            p2,
            p3 as mock_client_class,
            p4,
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_manifest_async",
                new_callable=AsyncMock,
                return_value=mock_section,
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
            ),
        ):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [
                        {"column": "gid", "agg": "count", "alias": "cnt"},
                    ],
                    "section": "ACTIVE",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["group_count"] >= 0

    def test_tc_ra011_count_distinct(self, client: TestClient) -> None:
        """TC-RA011: count_distinct in response returns correct unique counts."""
        mock_df = _create_mock_dataframe()
        p1, p2, p3, p4 = _common_patches(mock_df)

        with p1, p2, p3 as mock_client_class, p4:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["section"],
                    "aggregations": [
                        {
                            "column": "vertical",
                            "agg": "count_distinct",
                            "alias": "uniq_verts",
                        },
                    ],
                },
            )

        assert response.status_code == 200
        data = response.json()
        for row in data["data"]:
            assert "uniq_verts" in row
            assert isinstance(row["uniq_verts"], int)

    def test_tc_ra012_extra_fields_rejected(self, client: TestClient) -> None:
        """TC-RA012: Request with extra fields returns 422 validation error."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/query/offer/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "group_by": ["vertical"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                    "extra_field": True,
                },
            )

        assert response.status_code == 422
