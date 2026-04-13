"""Tests for the FleetQuery -> EntityQueryService adapter (S3 D4).

Test surface (per S3 TDD section 7.4.3):

1. Pure adapter translation:
   - entity_type required and validated
   - select optional and type-checked
   - residual filter keys forwarded to ``where`` verbatim
   - limit/offset propagate cleanly

2. Pagination round-trip (section 7.3 invariant):
   - FleetQuery(limit=L, offset=O) + total_count -> PaginationMeta with
     matching limit, offset-derived next_offset, accurate has_more
   - last-page handling clears next_offset

3. Route integration (dual-namespace per section 7.4.3):
   - POST /v1/query/entities accepts FleetQuery body and returns
     SuccessResponse[FleetQueryEnvelope]
   - POST /api/v1/query/entities is reachable with the SAME handler
   - Both routes round-trip PaginationMeta

4. Backward-compat invariants:
   - The legacy POST /v1/query/{entity_type} surface is untouched
     (verified by importing the existing query module and asserting
     its router still exposes the legacy endpoints)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from autom8y_api_schemas import FleetQuery, PaginationMeta

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

from autom8_asana.api.fleet_query_adapter import (
    AdapterValidationError,
    FleetQueryDispatchKwargs,
    build_pagination_meta,
    fleet_query_to_dispatch_kwargs,
    pagination_meta_from_query_result,
)
from autom8_asana.services.query_service import QueryResult

# ---------------------------------------------------------------------------
# Pure adapter translation
# ---------------------------------------------------------------------------


class TestFleetQueryToDispatchKwargs:
    """Translation from FleetQuery -> EntityQueryService.query kwargs."""

    def test_minimal_valid_query(self) -> None:
        query = FleetQuery(filters={"entity_type": "offer"})
        dispatch = fleet_query_to_dispatch_kwargs(query)
        assert isinstance(dispatch, FleetQueryDispatchKwargs)
        assert dispatch.entity_type == "offer"
        assert dispatch.where == {}
        assert dispatch.select is None
        assert dispatch.limit == 50
        assert dispatch.offset == 0

    def test_residual_keys_become_where_predicates(self) -> None:
        query = FleetQuery(
            limit=10,
            offset=20,
            filters={
                "entity_type": "offer",
                "vertical": "chiro",
                "section": "ACTIVE",
            },
        )
        dispatch = fleet_query_to_dispatch_kwargs(query)
        assert dispatch.entity_type == "offer"
        assert dispatch.where == {"vertical": "chiro", "section": "ACTIVE"}
        assert dispatch.limit == 10
        assert dispatch.offset == 20

    def test_select_extracted_from_filters(self) -> None:
        query = FleetQuery(
            filters={
                "entity_type": "offer",
                "select": ["gid", "name", "section"],
                "vertical": "dental",
            },
        )
        dispatch = fleet_query_to_dispatch_kwargs(query)
        assert dispatch.select == ["gid", "name", "section"]
        # select MUST NOT leak into the where dict.
        assert "select" not in dispatch.where
        assert dispatch.where == {"vertical": "dental"}

    def test_missing_entity_type_raises_validation_error(self) -> None:
        query = FleetQuery(filters={"vertical": "chiro"})
        with pytest.raises(AdapterValidationError) as exc_info:
            fleet_query_to_dispatch_kwargs(query)
        assert "entity_type" in str(exc_info.value)

    @pytest.mark.parametrize("bad_value", ["", "   ", 0, None, []])
    def test_invalid_entity_type_raises_validation_error(self, bad_value: Any) -> None:
        query = FleetQuery(filters={"entity_type": bad_value})
        with pytest.raises(AdapterValidationError):
            fleet_query_to_dispatch_kwargs(query)

    @pytest.mark.parametrize("bad_select", ["gid,name", {"a": 1}, [1, 2, 3]])
    def test_invalid_select_raises_validation_error(self, bad_select: Any) -> None:
        query = FleetQuery(filters={"entity_type": "offer", "select": bad_select})
        with pytest.raises(AdapterValidationError) as exc_info:
            fleet_query_to_dispatch_kwargs(query)
        assert "select" in str(exc_info.value)

    def test_nested_filter_values_pass_through_to_where(self) -> None:
        query = FleetQuery(
            filters={
                "entity_type": "offer",
                "tags": ["a", "b"],
                "metadata": {"key": "value"},
            }
        )
        dispatch = fleet_query_to_dispatch_kwargs(query)
        assert dispatch.where["tags"] == ["a", "b"]
        assert dispatch.where["metadata"] == {"key": "value"}


# ---------------------------------------------------------------------------
# Pagination round-trip (section 7.3 invariant)
# ---------------------------------------------------------------------------


class TestBuildPaginationMeta:
    """Section 7.3 round-trip invariant: FleetQuery -> PaginationMeta."""

    def test_first_page_with_more_pages(self) -> None:
        query = FleetQuery(limit=10, offset=0)
        meta = build_pagination_meta(query, total_count=100)
        assert isinstance(meta, PaginationMeta)
        assert meta.limit == 10
        assert meta.has_more is True
        assert meta.next_offset == "offset:10"
        assert meta.total_count == 100

    def test_middle_page(self) -> None:
        query = FleetQuery(limit=10, offset=20)
        meta = build_pagination_meta(query, total_count=100)
        assert meta.next_offset == "offset:30"
        assert meta.has_more is True

    def test_last_page_clears_next_offset(self) -> None:
        query = FleetQuery(limit=10, offset=90)
        meta = build_pagination_meta(query, total_count=100)
        assert meta.has_more is False
        assert meta.next_offset is None

    def test_overshoot_offset_clears_cursor(self) -> None:
        # offset > total_count: callers paginated past the end. has_more
        # must be False.
        query = FleetQuery(limit=10, offset=200)
        meta = build_pagination_meta(query, total_count=50)
        assert meta.has_more is False
        assert meta.next_offset is None

    def test_round_trip_from_query_result_helper(self) -> None:
        # The convenience helper accepts a QueryResult and pulls
        # total_count off of it directly.
        query = FleetQuery(limit=10, offset=20)
        result = QueryResult(
            data=[{"gid": "1"}, {"gid": "2"}],
            total_count=100,
            project_gid="proj-123",
        )
        meta = pagination_meta_from_query_result(query, result)
        assert meta.limit == 10
        assert meta.next_offset == "offset:30"
        assert meta.total_count == 100
        assert meta.has_more is True


# ---------------------------------------------------------------------------
# Route integration (dual-namespace at /v1 and /api/v1)
# ---------------------------------------------------------------------------


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    """Helper: validate_service_token mock returning valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _create_mock_offer_dataframe() -> pl.DataFrame:
    """Minimal offer DataFrame fixture used by the route tests."""
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


def _patch_query_path() -> Any:
    """Compose the patch stack used by the fleet route integration tests.

    Mocks the same surfaces the legacy route tests mock so the fleet
    handler exercises the real adapter and EntityQueryService while the
    cache + AsanaClient are stubbed.
    """
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
            return_value=_create_mock_offer_dataframe(),
        ),
    )


@pytest.mark.parametrize(
    "route_path",
    ["/v1/query/entities", "/api/v1/query/entities"],
    ids=["legacy_v1_namespace", "fleet_api_v1_namespace"],
)
class TestFleetQueryRoutesDualNamespace:
    """Both /v1/query/entities and /api/v1/query/entities accept FleetQuery."""

    def test_post_returns_success_envelope(self, client: TestClient, route_path: str) -> None:
        jwt_token = "header.payload.signature"
        patches = _patch_query_path()

        with patches[0], patches[1], patches[2] as mock_client_cls, patches[3]:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            response = client.post(
                route_path,
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "limit": 10,
                    "offset": 0,
                    "filters": {
                        "entity_type": "offer",
                        "select": ["gid", "name", "section"],
                        "section": "ACTIVE",
                    },
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert "data" in body
        assert "meta" in body

        # Payload (FleetQueryEnvelope) shape
        data = body["data"]
        assert data["entity_type"] == "offer"
        assert data["project_gid"] == "1143843662099250"
        assert isinstance(data["rows"], list)
        # 3 ACTIVE offers in the fixture.
        assert len(data["rows"]) == 3
        for row in data["rows"]:
            assert row["section"] == "ACTIVE"

    def test_pagination_meta_round_trips(self, client: TestClient, route_path: str) -> None:
        # Section 7.3 invariant: FleetQuery(limit=L, offset=O) round-trips
        # into the response envelope's PaginationMeta.
        jwt_token = "header.payload.signature"
        patches = _patch_query_path()

        with patches[0], patches[1], patches[2] as mock_client_cls, patches[3]:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            response = client.post(
                route_path,
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "limit": 2,
                    "offset": 1,
                    "filters": {
                        "entity_type": "offer",
                        "section": "ACTIVE",
                    },
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        meta = body["meta"]
        assert "pagination" in meta
        pagination = meta["pagination"]
        # limit MUST mirror the request.
        assert pagination["limit"] == 2
        # total_count MUST reflect the cache row count BEFORE pagination
        # (3 ACTIVE offers in the fixture).
        assert pagination["total_count"] == 3
        # offset=1 + limit=2 = 3 == total_count, so no more pages.
        assert pagination["has_more"] is False
        assert pagination["next_offset"] is None

    def test_missing_entity_type_returns_400(self, client: TestClient, route_path: str) -> None:
        jwt_token = "header.payload.signature"
        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
        ):
            response = client.post(
                route_path,
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"limit": 10, "offset": 0, "filters": {"vertical": "chiro"}},
            )
        # AdapterValidationError -> 400 via raise_api_error
        assert response.status_code == 400
        body = response.json()
        # Error envelope shape from raise_api_error
        assert body["error"]["code"] == "FLEET_QUERY_VALIDATION"
        assert "entity_type" in body["error"]["message"]


# ---------------------------------------------------------------------------
# Backward-compat invariants
# ---------------------------------------------------------------------------


class TestLegacyQuerySurfacePreserved:
    """The fleet route is purely additive — legacy /v1/query routes still mount."""

    def test_legacy_query_router_still_exposes_post_handler(self) -> None:
        from autom8_asana.api.routes.query import router as legacy_query_router

        # Collect the route paths the legacy query router defines.
        legacy_paths = {getattr(r, "path", None) for r in legacy_query_router.routes}
        # The deprecated POST /{entity_type} legacy endpoint MUST remain.
        assert any("/{entity_type}" in (p or "") for p in legacy_paths)
        # The /rows and /aggregate endpoints MUST also remain.
        assert any("/{entity_type}/rows" in (p or "") for p in legacy_paths)
        assert any("/{entity_type}/aggregate" in (p or "") for p in legacy_paths)

    def test_fleet_router_does_not_overlap_legacy_routes(self) -> None:
        from autom8_asana.api.routes.fleet_query import (
            fleet_query_router_api_v1,
            fleet_query_router_v1,
        )

        v1_paths = {getattr(r, "path", None) for r in fleet_query_router_v1.routes}
        api_v1_paths = {getattr(r, "path", None) for r in fleet_query_router_api_v1.routes}
        # The fleet router defines exactly /entities under its prefix.
        # SecureRouter prepends the prefix, so route.path is the full path.
        assert any("/entities" in (p or "") for p in v1_paths)
        assert any("/entities" in (p or "") for p in api_v1_paths)
        # No accidental wildcard collision with /{entity_type}.
        assert all("/{entity_type}" not in (p or "") for p in v1_paths)
        assert all("/{entity_type}" not in (p or "") for p in api_v1_paths)
