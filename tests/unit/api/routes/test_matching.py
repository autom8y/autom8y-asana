"""Tests for matching query endpoint.

POST /v1/matching/query - Query for matching business candidates.

Tests validate:
- S2S JWT auth enforcement
- Request validation (at least one identity field required)
- Response shape and projection (no internals leaked)
- Cache unavailability handling
- Service error handling
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.dual_mode import AuthMode
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}
BUSINESS_PROJECT_GID = "1234567890123456"

MINIMAL_QUERY_BODY = {
    "name": "Acme Corp",
}

FULL_QUERY_BODY = {
    "name": "Acme Corporation",
    "phone": "+15551234567",
    "email": "info@acme.com",
    "domain": "acme.com",
    "limit": 5,
    "threshold": 0.9,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    """Create a mock JWT validation returning valid ServiceClaims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


@dataclass
class _FakeEntry:
    """Minimal stand-in for DataFrameCacheEntry."""

    dataframe: object


def _make_fake_dataframe():
    """Create a minimal polars DataFrame for testing."""
    import polars as pl

    return pl.DataFrame(
        {
            "gid": ["biz_001", "biz_002", "biz_003"],
            "name": ["Acme Corp", "Acme Inc", "Beta LLC"],
            "office_phone": ["+15551234567", "+15551234000", "+15559999999"],
            "email": ["info@acme.com", "hello@acme.com", "info@beta.com"],
            "domain": ["acme.com", "acme.com", "beta.com"],
            "company_id": ["C001", "C002", "C003"],
        }
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app(monkeypatch_module):
    """Create test app with auth middleware in dev-mode bypass.

    Sets AUTOM8Y_ENV=LOCAL + AUTH__DEV_MODE=true so the JWTAuthMiddleware
    returns bypass claims instead of validating tokens. Also overrides the
    get_auth_context dependency for consistent auth context in route logic.

    TestMatchingAuth uses a separate unauthenticated fixture (raw_client)
    with a non-LOCAL env to test auth rejection behavior.
    """
    monkeypatch_module.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch_module.setenv("AUTH__DEV_MODE", "true")

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="business",
                project_gid=BUSINESS_PROJECT_GID,
                project_name="Business",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        test_app = create_app()

        async def _mock_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service="autom8_data",
            )

        test_app.dependency_overrides[get_auth_context] = _mock_get_auth_context
        yield test_app


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest's monkeypatch is function-scoped)."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def raw_app():
    """Create test app WITHOUT auth bypass — for auth rejection tests."""
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="business",
                project_gid=BUSINESS_PROJECT_GID,
                project_name="Business",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture(scope="module")
def _module_client(app):
    """Module-scoped TestClient with auth bypass."""
    with TestClient(app) as tc:
        yield tc


@pytest.fixture(scope="module")
def raw_client(raw_app):
    """Module-scoped TestClient WITHOUT auth bypass — for auth tests."""
    with TestClient(raw_app) as tc:
        yield tc


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons for test isolation."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    registry = EntityProjectRegistry.get_instance()
    registry.register(
        entity_type="business",
        project_gid=BUSINESS_PROJECT_GID,
        project_name="Business",
    )
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture
def client(_module_client) -> TestClient:
    """Per-test TestClient alias."""
    return _module_client


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestMatchingAuth:
    """Authentication tests for POST /v1/matching/query.

    Uses raw_client (no auth override) so the real auth middleware fires.
    """

    def test_missing_auth_returns_401(self, raw_client: TestClient) -> None:
        """Request without Authorization header returns 401."""
        resp = raw_client.post("/v1/matching/query", json=MINIMAL_QUERY_BODY)
        assert resp.status_code == 401

    def test_pat_token_rejected(self, raw_client: TestClient) -> None:
        """Non-JWT tokens are rejected by auth middleware before route-level check."""
        resp = raw_client.post(
            "/v1/matching/query",
            json=MINIMAL_QUERY_BODY,
            headers={"Authorization": "Bearer pat_token_1234567890"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH-INVALID-TOKEN"


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestMatchingValidation:
    """Input validation for POST /v1/matching/query."""

    def test_empty_identity_returns_400(self, client: TestClient) -> None:
        """Request with no identity fields returns 400 INVALID_QUERY."""
        with (
            patch("autom8_asana.api.routes.internal.detect_token_type") as mock_detect,
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
            ) as mock_validate,
        ):
            from autom8_asana.auth.dual_mode import AuthMode

            mock_detect.return_value = AuthMode.JWT
            mock_validate.return_value = _mock_jwt_validation().return_value

            resp = client.post(
                "/v1/matching/query",
                json={},
                headers=AUTH_HEADER,
            )
            assert resp.status_code == 400
            assert resp.json()["error"]["code"] == "INVALID_QUERY"

    def test_only_limit_and_threshold_returns_400(self, client: TestClient) -> None:
        """Request with only limit/threshold (no identity fields) returns 400."""
        with (
            patch("autom8_asana.api.routes.internal.detect_token_type") as mock_detect,
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
            ) as mock_validate,
        ):
            from autom8_asana.auth.dual_mode import AuthMode

            mock_detect.return_value = AuthMode.JWT
            mock_validate.return_value = _mock_jwt_validation().return_value

            resp = client.post(
                "/v1/matching/query",
                json={"limit": 5, "threshold": 0.8},
                headers=AUTH_HEADER,
            )
            assert resp.status_code == 400

    def test_limit_validation(self, client: TestClient) -> None:
        """Limit must be between 1 and 100."""
        with (
            patch("autom8_asana.api.routes.internal.detect_token_type") as mock_detect,
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
            ) as mock_validate,
        ):
            from autom8_asana.auth.dual_mode import AuthMode

            mock_detect.return_value = AuthMode.JWT
            mock_validate.return_value = _mock_jwt_validation().return_value

            resp = client.post(
                "/v1/matching/query",
                json={"name": "Test", "limit": 0},
                headers=AUTH_HEADER,
            )
            assert resp.status_code == 422  # Pydantic validation

    def test_threshold_validation(self, client: TestClient) -> None:
        """Threshold must be between 0.0 and 1.0."""
        with (
            patch("autom8_asana.api.routes.internal.detect_token_type") as mock_detect,
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
            ) as mock_validate,
        ):
            from autom8_asana.auth.dual_mode import AuthMode

            mock_detect.return_value = AuthMode.JWT
            mock_validate.return_value = _mock_jwt_validation().return_value

            resp = client.post(
                "/v1/matching/query",
                json={"name": "Test", "threshold": 1.5},
                headers=AUTH_HEADER,
            )
            assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Success path tests
# ---------------------------------------------------------------------------


class TestMatchingQuerySuccess:
    """Successful matching query tests."""

    def _patch_auth_and_cache(self):
        """Context manager patches for auth and cache."""
        from autom8_asana.auth.dual_mode import AuthMode

        mock_detect = patch(
            "autom8_asana.api.routes.internal.detect_token_type",
            return_value=AuthMode.JWT,
        )
        mock_validate = patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            new_callable=AsyncMock,
            return_value=_mock_jwt_validation().return_value,
        )

        fake_df = _make_fake_dataframe()
        fake_entry = _FakeEntry(dataframe=fake_df)
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=fake_entry)

        mock_cache_factory = patch(
            "autom8_asana.api.routes.matching.get_dataframe_cache_provider",
            return_value=mock_cache,
        )

        return mock_detect, mock_validate, mock_cache_factory

    def test_minimal_query_returns_200(self, client: TestClient) -> None:
        """Minimal query with just name returns 200 with candidates."""
        p_detect, p_validate, p_cache = self._patch_auth_and_cache()

        with p_detect, p_validate, p_cache:
            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        outer = resp.json()
        assert "data" in outer
        assert "meta" in outer
        body = outer["data"]
        assert "candidates" in body
        assert "total_candidates_evaluated" in body
        assert "query_threshold" in body
        assert isinstance(body["candidates"], list)

    def test_full_query_returns_200(self, client: TestClient) -> None:
        """Full query with all identity fields returns 200."""
        p_detect, p_validate, p_cache = self._patch_auth_and_cache()

        with p_detect, p_validate, p_cache:
            resp = client.post(
                "/v1/matching/query",
                json=FULL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert len(body["candidates"]) <= FULL_QUERY_BODY["limit"]

    def test_response_does_not_leak_internals(self, client: TestClient) -> None:
        """Response must not contain raw_score, left_value, right_value, weight_applied."""
        p_detect, p_validate, p_cache = self._patch_auth_and_cache()

        with p_detect, p_validate, p_cache:
            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        body = resp.json()["data"]

        # Check response data
        resp_str = str(body)
        assert "raw_score" not in resp_str
        assert "left_value" not in resp_str
        assert "right_value" not in resp_str
        assert "weight_applied" not in resp_str

    def test_candidate_shape(self, client: TestClient) -> None:
        """Each candidate has required fields."""
        p_detect, p_validate, p_cache = self._patch_auth_and_cache()

        with p_detect, p_validate, p_cache:
            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        body = resp.json()["data"]
        for candidate in body["candidates"]:
            assert "candidate_gid" in candidate
            assert "score" in candidate
            assert "is_match" in candidate
            assert "field_comparisons" in candidate
            assert isinstance(candidate["field_comparisons"], list)

            for fc in candidate["field_comparisons"]:
                assert "field_name" in fc
                assert "contributed" in fc
                # similarity can be null for exact-match fields with missing data
                assert "similarity" in fc

    def test_candidates_sorted_by_score_desc(self, client: TestClient) -> None:
        """Candidates are returned sorted by score descending."""
        p_detect, p_validate, p_cache = self._patch_auth_and_cache()

        with p_detect, p_validate, p_cache:
            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        body = resp.json()["data"]
        scores = [c["score"] for c in body["candidates"]]
        assert scores == sorted(scores, reverse=True)

    def test_query_with_email_only(self, client: TestClient) -> None:
        """Query with only email is valid."""
        p_detect, p_validate, p_cache = self._patch_auth_and_cache()

        with p_detect, p_validate, p_cache:
            resp = client.post(
                "/v1/matching/query",
                json={"email": "info@acme.com"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestMatchingQueryErrors:
    """Error handling for matching query."""

    def test_cache_unavailable_returns_503(self, client: TestClient) -> None:
        """When cache provider is None, returns 503."""
        from autom8_asana.auth.dual_mode import AuthMode

        with (
            patch(
                "autom8_asana.api.routes.internal.detect_token_type",
                return_value=AuthMode.JWT,
            ),
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
                return_value=_mock_jwt_validation().return_value,
            ),
            patch(
                "autom8_asana.api.routes.matching.get_dataframe_cache_provider",
                return_value=None,
            ),
        ):
            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "CACHE_UNAVAILABLE"

    def test_cache_miss_returns_503(self, client: TestClient) -> None:
        """When cache entry is None (miss), returns 503."""
        from autom8_asana.auth.dual_mode import AuthMode

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        with (
            patch(
                "autom8_asana.api.routes.internal.detect_token_type",
                return_value=AuthMode.JWT,
            ),
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
                return_value=_mock_jwt_validation().return_value,
            ),
            patch(
                "autom8_asana.api.routes.matching.get_dataframe_cache_provider",
                return_value=mock_cache,
            ),
        ):
            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "CACHE_UNAVAILABLE"

    def test_cache_fetch_error_returns_503(self, client: TestClient) -> None:
        """When cache.get_async raises, returns 503."""
        from autom8_asana.auth.dual_mode import AuthMode

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(side_effect=RuntimeError("S3 timeout"))

        with (
            patch(
                "autom8_asana.api.routes.internal.detect_token_type",
                return_value=AuthMode.JWT,
            ),
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
                return_value=_mock_jwt_validation().return_value,
            ),
            patch(
                "autom8_asana.api.routes.matching.get_dataframe_cache_provider",
                return_value=mock_cache,
            ),
        ):
            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 503

    def test_matching_engine_error_returns_500(self, client: TestClient) -> None:
        """When matching service raises, returns 500."""
        from autom8_asana.auth.dual_mode import AuthMode

        fake_df = _make_fake_dataframe()
        fake_entry = _FakeEntry(dataframe=fake_df)
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=fake_entry)

        with (
            patch(
                "autom8_asana.api.routes.internal.detect_token_type",
                return_value=AuthMode.JWT,
            ),
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                new_callable=AsyncMock,
                return_value=_mock_jwt_validation().return_value,
            ),
            patch(
                "autom8_asana.api.routes.matching.get_dataframe_cache_provider",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.api.routes.matching.MatchingService",
            ) as mock_svc_cls,
        ):
            mock_svc_cls.return_value.query.side_effect = RuntimeError("engine failure")

            resp = client.post(
                "/v1/matching/query",
                json=MINIMAL_QUERY_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 500
        assert resp.json()["error"]["code"] == "MATCHING_ERROR"


# ---------------------------------------------------------------------------
# Router configuration tests
# ---------------------------------------------------------------------------


class TestMatchingRouterConfig:
    """Router configuration and registration tests."""

    def test_router_hidden_from_schema(self) -> None:
        """Matching router has include_in_schema=False."""
        from autom8_asana.api.routes.matching import router

        assert router.include_in_schema is False

    def test_router_prefix(self) -> None:
        """Matching router has /v1/matching prefix."""
        from autom8_asana.api.routes.matching import router

        assert router.prefix == "/v1/matching"

    def test_router_tags(self) -> None:
        """Matching router has matching tag."""
        from autom8_asana.api.routes.matching import router

        assert "matching" in router.tags

    def test_matching_router_registered_in_app(self, app) -> None:
        """Matching router is registered in the app."""
        route_paths = [route.path for route in app.routes]
        assert "/v1/matching/query" in route_paths
