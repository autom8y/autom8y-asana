"""GID Lookup contract tests for POST /v1/resolve/{entity_type}.

Per TDD-B01: These tests validate that autom8_asana's resolve endpoint
behaves according to the integration contract expected by autom8_data's
RealGidLookupClient. No server-side code changes are needed -- the
existing endpoint is fully compatible. These tests prove that compatibility.

Contract invariants enforced:
  1. Results array is positionally correlated with criteria array
  2. Every result has gid, match_count, error, gids, data fields
  3. Every meta has resolved_count, unresolved_count, entity_type,
     project_gid, available_fields, criteria_schema
  4. meta.resolved_count + meta.unresolved_count == len(criteria)
  5. Auth requires S2S JWT (PAT rejected, missing auth rejected)
  6. E.164 phone validation, batch size limits, entity type routing

Test IDs: CT-001 through CT-016 (per TDD-B01 Section 6).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.dynamic_index import DynamicIndex
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.services.resolver import EntityProjectRegistry
from autom8_asana.services.resolver import (
    _apply_legacy_mapping as resolver_apply_legacy_mapping,
)

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

UNIT_PROJECT_GID = "1201081073731555"

MOCK_UNIT_DF = pl.DataFrame(
    {
        "gid": [
            "1111111111111111",
            "2222222222222222",
            "3333333333333333",
        ],
        "office_phone": ["+11111111111", "+12222222222", "+13333333333"],
        "vertical": ["alpha", "bravo", "charlie"],
        "name": ["Unit Alpha", "Unit Bravo", "Unit Charlie"],
    }
)


# ---------------------------------------------------------------------------
# Helpers (reuse patterns from tests/api/test_routes_resolver.py)
# ---------------------------------------------------------------------------


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    """Create a mock JWT validation returning valid ServiceClaims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _apply_legacy_mapping(criterion: dict, entity_type: str) -> dict:
    """Apply legacy field mapping using resolver's dynamic algorithm."""
    return resolver_apply_legacy_mapping(entity_type, criterion)


def _make_mock_strategy_resolve(
    mock_df: pl.DataFrame,
    key_columns: list[str],
    entity_type: str = "unit",
):
    """Create a mock resolve function using the universal strategy pattern."""

    async def mock_resolve(self, criteria, project_gid, client, requested_fields=None):
        index = DynamicIndex.from_dataframe(mock_df, key_columns)
        results = []
        for criterion in criteria:
            mapped = _apply_legacy_mapping(criterion, entity_type)
            gids = index.lookup(mapped)
            if gids:
                results.append(ResolutionResult.from_gids(gids))
            else:
                results.append(ResolutionResult.not_found())
        return results

    return mock_resolve


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before and after each test for isolation."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app():
    """Create a test application with mocked discovery and entity registry."""
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid=UNIT_PROJECT_GID,
                project_name="Business Units",
            )
            registry.register(
                entity_type="business",
                project_gid="1234567890123456",
                project_name="Business",
            )
            registry.register(
                entity_type="offer",
                project_gid="1143843662099250",
                project_name="Business Offers",
            )
            registry.register(
                entity_type="contact",
                project_gid="1200775689604552",
                project_name="Contacts",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    """Synchronous test client with lifespan events handled."""
    with TestClient(app) as tc:
        yield tc


def _resolve_patches(mock_df: pl.DataFrame = MOCK_UNIT_DF):
    """Context-manager stack that patches JWT, bot PAT, AsanaClient, and strategy."""
    mock_resolve = _make_mock_strategy_resolve(mock_df, ["office_phone", "vertical"])
    jwt_patch = patch(
        "autom8_asana.api.routes.internal.validate_service_token",
        _mock_jwt_validation(),
    )
    pat_patch = patch(
        "autom8_asana.auth.bot_pat.get_bot_pat",
        return_value="test_bot_pat",
    )
    client_patch = patch("autom8_asana.AsanaClient")
    strategy_patch = patch(
        "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
        mock_resolve,
    )
    return jwt_patch, pat_patch, client_patch, strategy_patch


def _make_async_client_mock(mock_client_class: MagicMock) -> None:
    """Configure mock AsanaClient as an async context manager."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}


class TestGidLookupHappyPath:
    """CT-001 through CT-004: Core GID lookup scenarios."""

    def test_ct001_single_criterion_returns_gid(self, client: TestClient) -> None:
        """CT-001: Single phone/vertical criterion resolves to a GID."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "+11111111111", "vertical": "alpha"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1

        result = data["results"][0]
        assert isinstance(result["gid"], str)
        assert len(result["gid"]) > 0
        assert result["error"] is None
        assert result["match_count"] >= 1

    def test_ct002_batch_preserves_order(self, client: TestClient) -> None:
        """CT-002: Batch of 3 criteria returns 3 results preserving positional order."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "+11111111111", "vertical": "alpha"},  # found
                        {"phone": "+19999999999", "vertical": "missing"},  # not found
                        {"phone": "+13333333333", "vertical": "charlie"},  # found
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3

        assert data["results"][0]["gid"] is not None  # found
        assert data["results"][1]["gid"] is None  # not found
        assert data["results"][2]["gid"] is not None  # found

        # Verify specific GIDs match expected order
        assert data["results"][0]["gid"] == "1111111111111111"
        assert data["results"][2]["gid"] == "3333333333333333"

    def test_ct003_not_found_returns_null_gid_and_error(
        self, client: TestClient
    ) -> None:
        """CT-003: Criterion that matches nothing returns gid=null, error=NOT_FOUND."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "+19999999999", "vertical": "nonexistent"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        result = data["results"][0]

        assert result["gid"] is None
        assert result["error"] == "NOT_FOUND"
        assert result["match_count"] == 0

    def test_ct004_mixed_batch_meta_counts(self, client: TestClient) -> None:
        """CT-004: Batch with 2 found + 1 not-found has correct meta counts."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "+11111111111", "vertical": "alpha"},
                        {"phone": "+12222222222", "vertical": "bravo"},
                        {"phone": "+19999999999", "vertical": "missing"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["resolved_count"] == 2
        assert data["meta"]["unresolved_count"] == 1
        assert data["meta"]["entity_type"] == "unit"
        assert isinstance(data["meta"]["project_gid"], str)


class TestGidLookupResponseShape:
    """CT-005, CT-006: Validate response structure completeness."""

    def test_ct005_result_has_required_fields(self, client: TestClient) -> None:
        """CT-005: Each result has gid, match_count, error, gids, data fields."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "+11111111111", "vertical": "alpha"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        result = data["results"][0]

        # All fields specified in the contract must be present
        assert "gid" in result
        assert "match_count" in result
        assert "error" in result
        assert "gids" in result
        assert "data" in result

    def test_ct006_meta_has_required_fields(self, client: TestClient) -> None:
        """CT-006: Meta object has all required fields with correct types."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "+11111111111", "vertical": "alpha"},
                    ]
                },
            )

        assert response.status_code == 200
        meta = response.json()["meta"]

        assert "resolved_count" in meta
        assert "unresolved_count" in meta
        assert "entity_type" in meta
        assert "project_gid" in meta
        assert "available_fields" in meta
        assert "criteria_schema" in meta

        assert isinstance(meta["available_fields"], list)
        assert isinstance(meta["criteria_schema"], list)
        assert isinstance(meta["resolved_count"], int)
        assert isinstance(meta["unresolved_count"], int)
        assert isinstance(meta["entity_type"], str)
        assert isinstance(meta["project_gid"], str)


class TestGidLookupAuth:
    """CT-007, CT-008, CT-009: Authentication contract enforcement."""

    def test_ct007_missing_auth_returns_401(self, client: TestClient) -> None:
        """CT-007: Request without Authorization header returns 401 MISSING_AUTH."""
        response = client.post(
            "/v1/resolve/unit",
            json={
                "criteria": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["error"] == "MISSING_AUTH"

    def test_ct008_pat_token_returns_401(self, client: TestClient) -> None:
        """CT-008: PAT token (0/xxx format) returns 401 SERVICE_TOKEN_REQUIRED."""
        pat_token = "0/1234567890abcdef1234567890"

        response = client.post(
            "/v1/resolve/unit",
            headers={"Authorization": f"Bearer {pat_token}"},
            json={
                "criteria": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["error"] == "SERVICE_TOKEN_REQUIRED"

    def test_ct009_expired_jwt_returns_401(self, client: TestClient) -> None:
        """CT-009: Expired JWT returns 401 with TOKEN_EXPIRED error code."""
        mock_error = Exception("Token expired")
        mock_error.code = "TOKEN_EXPIRED"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            AsyncMock(side_effect=mock_error),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["error"] == "TOKEN_EXPIRED"


class TestGidLookupValidation:
    """CT-010, CT-011: Input validation contract."""

    def test_ct010_invalid_e164_returns_422(self, client: TestClient) -> None:
        """CT-010: Phone number without + prefix returns 422."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "5551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 422

    def test_ct011_batch_over_1000_returns_422(self, client: TestClient) -> None:
        """CT-011: 1001 criteria returns 422 with batch size error."""
        criteria = [
            {"phone": f"+1555{i:07d}", "vertical": "dental"} for i in range(1001)
        ]

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={"criteria": criteria},
            )

        assert response.status_code == 422


class TestGidLookupEdgeCases:
    """CT-012, CT-015: Edge cases and boundary conditions."""

    def test_ct012_empty_criteria_returns_200(self, client: TestClient) -> None:
        """CT-012: Empty criteria list returns 200 with empty results and zero counts."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={"criteria": []},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["meta"]["resolved_count"] == 0
        assert data["meta"]["unresolved_count"] == 0

    def test_ct015_batch_exactly_1000_succeeds(self, client: TestClient) -> None:
        """CT-015: Boundary test -- exactly 1000 criteria is accepted."""
        # Build a DataFrame with 1000 entries for the mock strategy
        gids = [f"{i:016d}" for i in range(1000)]
        phones = [f"+1555{i:07d}" for i in range(1000)]
        verticals = ["dental"] * 1000
        names = [f"Unit {i}" for i in range(1000)]

        big_df = pl.DataFrame(
            {
                "gid": gids,
                "office_phone": phones,
                "vertical": verticals,
                "name": names,
            }
        )

        jwt_p, pat_p, cli_p, strat_p = _resolve_patches(mock_df=big_df)

        criteria = [
            {"phone": f"+1555{i:07d}", "vertical": "dental"} for i in range(1000)
        ]

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={"criteria": criteria},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1000


class TestGidLookupRouting:
    """CT-013: Entity type routing."""

    def test_ct013_unknown_entity_type_returns_404(self, client: TestClient) -> None:
        """CT-013: POST /v1/resolve/nonexistent returns 404 UNKNOWN_ENTITY_TYPE."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/v1/resolve/nonexistent",
                headers=AUTH_HEADER,
                json={
                    "criteria": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error"] == "UNKNOWN_ENTITY_TYPE"
        assert "available_types" in detail
        assert isinstance(detail["available_types"], list)


class TestGidLookupAvailability:
    """CT-014: Server availability checks."""

    def test_ct014_discovery_incomplete_returns_503(self) -> None:
        """CT-014: When entity registry is not ready, returns 503 DISCOVERY_INCOMPLETE."""
        EntityProjectRegistry.reset()

        with patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ) as mock_discover:

            async def no_setup(app):
                EntityProjectRegistry.reset()
                registry = EntityProjectRegistry.get_instance()
                # Registry exists but is_ready() is False (no registrations)
                app.state.entity_project_registry = registry

            mock_discover.side_effect = no_setup
            test_app = create_app()

            with TestClient(test_app) as test_client:
                with patch(
                    "autom8_asana.api.routes.internal.validate_service_token",
                    _mock_jwt_validation(),
                ):
                    response = test_client.post(
                        "/v1/resolve/unit",
                        headers=AUTH_HEADER,
                        json={
                            "criteria": [
                                {"phone": "+15551234567", "vertical": "dental"},
                            ]
                        },
                    )

                assert response.status_code == 503
                detail = response.json()["detail"]
                assert detail["error"] == "DISCOVERY_INCOMPLETE"


class TestGidLookupInvariants:
    """CT-016: Cross-cutting invariants."""

    def test_ct016_meta_count_invariant(self, client: TestClient) -> None:
        """CT-016: resolved_count + unresolved_count == len(criteria) for any batch."""
        jwt_p, pat_p, cli_p, strat_p = _resolve_patches()

        criteria = [
            {"phone": "+11111111111", "vertical": "alpha"},  # found
            {"phone": "+12222222222", "vertical": "bravo"},  # found
            {"phone": "+19999999999", "vertical": "missing"},  # not found
            {"phone": "+18888888888", "vertical": "absent"},  # not found
            {"phone": "+13333333333", "vertical": "charlie"},  # found
        ]

        with jwt_p, pat_p, cli_p as mock_cli, strat_p:
            _make_async_client_mock(mock_cli)

            response = client.post(
                "/v1/resolve/unit",
                headers=AUTH_HEADER,
                json={"criteria": criteria},
            )

        assert response.status_code == 200
        data = response.json()
        meta = data["meta"]

        criteria_count = len(criteria)
        assert meta["resolved_count"] + meta["unresolved_count"] == criteria_count
        assert len(data["results"]) == criteria_count
