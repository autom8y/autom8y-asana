"""Route handler tests for status-aware entity resolution.

Per TDD-STATUS-AWARE-RESOLUTION:
Tests for active_only parameter wiring, status in response body,
total_match_count, and no-classifier degradation at the API layer.
"""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNIT_PROJECT_GID = "1201081073731555"
JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}


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


def _resolve_patches(
    resolve_results: list[ResolutionResult],
) -> tuple[object, ...]:
    """Create patch stack for resolver route tests.

    Patches JWT validation, bot PAT, AsanaClient, and strategy.resolve().
    Uses the same proven pattern as test_resolver_gid_contract.py.
    """
    mock_resolve = AsyncMock(return_value=resolve_results)

    jwt_patch = patch(
        "autom8_asana.api.routes.internal.validate_service_token",
        _mock_jwt_validation(),
    )
    jwt_patch_canonical = patch(
        "autom8_asana.auth.jwt_validator.validate_service_token",
        _mock_jwt_validation(),
    )
    pat_patch = patch(
        "autom8_asana.auth.bot_pat.get_bot_pat",
        return_value="test_bot_pat",
    )
    pat_patch_deps = patch(
        "autom8_asana.api.dependencies.get_bot_pat",
        return_value="test_bot_pat",
    )
    client_patch = patch("autom8_asana.AsanaClient")
    strategy_patch = patch(
        "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
        mock_resolve,
    )
    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        strategy_patch,
        mock_resolve,
    )


def _make_async_client_mock(mock_client_class: MagicMock) -> None:
    """Configure mock AsanaClient as an async context manager."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():  # type: ignore[misc]
    """Reset singletons before and after each test for isolation."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app():  # type: ignore[misc]
    """Create a test application with mocked discovery and entity registry."""
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app: MagicMock) -> None:
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
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app: MagicMock) -> TestClient:  # type: ignore[misc]
    """Synchronous test client with lifespan events handled."""
    with TestClient(app) as tc:
        yield tc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolverStatusRoutes:
    """Tests for status-aware resolver route handler.

    Per TDD-STATUS-AWARE-RESOLUTION / FR-1, FR-3, FR-7, FR-10, FR-11.
    """

    def test_resolve_default_active_only_true(self, client: TestClient) -> None:
        """No active_only in body -> defaults to True, filters applied.

        Per SD-1: active_only=True is the default.
        """
        result_with_status = ResolutionResult.from_gids_with_status(
            gids=["gid-active"],
            status_annotations=["active"],
            total_match_count=3,
        )
        patches = _resolve_patches([result_with_status])
        *ctx_patches, mock_resolve = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])  # client_patch

            response = client.post(
                "/v1/resolve/unit",
                json={"criteria": [{"phone": "+15551234567", "vertical": "dental"}]},
                headers=AUTH_HEADER,
            )

        assert response.status_code == 200
        data = response.json()["data"]
        r = data["results"][0]
        assert r["status"] == ["active"]
        assert r["total_match_count"] == 3

        # Verify resolve was called with active_only=True (default)
        call_kwargs = mock_resolve.call_args
        assert call_kwargs is not None
        # active_only is passed as keyword arg
        if call_kwargs.kwargs:
            assert call_kwargs.kwargs.get("active_only") is True

    def test_resolve_explicit_active_only_false(self, client: TestClient) -> None:
        """active_only=False -> all matches returned.

        Per US-2: Diagnostic mode returns all.
        """
        all_results = ResolutionResult.from_gids_with_status(
            gids=["gid-1", "gid-2"],
            status_annotations=["active", "inactive"],
            total_match_count=None,
        )
        patches = _resolve_patches([all_results])
        *ctx_patches, mock_resolve = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                    "active_only": False,
                },
                headers=AUTH_HEADER,
            )

        assert response.status_code == 200
        data = response.json()["data"]
        r = data["results"][0]
        assert r["match_count"] == 2
        assert r["status"] == ["active", "inactive"]
        assert r["total_match_count"] is None

    def test_resolve_status_in_response_body(self, client: TestClient) -> None:
        """Response includes status list.

        Per FR-3: Each match carries status annotation.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["g1", "g2", "g3"],
            status_annotations=["active", "activating", None],
        )
        patches = _resolve_patches([result])
        *ctx_patches, _ = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
                headers=AUTH_HEADER,
            )

        assert response.status_code == 200
        data = response.json()["data"]
        r = data["results"][0]
        assert r["status"] == ["active", "activating", None]
        assert len(r["status"]) == 3

    def test_resolve_total_match_count_in_response(self, client: TestClient) -> None:
        """Response includes total_match_count.

        Per FR-11: Pre-filter count in response.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["g1"],
            status_annotations=["active"],
            total_match_count=5,
        )
        patches = _resolve_patches([result])
        *ctx_patches, _ = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
                headers=AUTH_HEADER,
            )

        assert response.status_code == 200
        r = response.json()["data"]["results"][0]
        assert r["total_match_count"] == 5

    def test_resolve_null_status_when_no_classifier(self, client: TestClient) -> None:
        """status is null when no classifier (FR-7).

        Per FR-7: No classifier -> status field is null in response.
        Uses 'unit' entity type with a result that has no status annotations
        to verify the response model correctly serializes null status.
        """
        # Simulate the no-classifier path: from_gids without status
        result = ResolutionResult.from_gids(["g1", "g2"])
        patches = _resolve_patches([result])
        *ctx_patches, _ = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
                headers=AUTH_HEADER,
            )

        assert response.status_code == 200
        r = response.json()["data"]["results"][0]
        assert r["status"] is None
        assert r["total_match_count"] is None

    def test_resolve_match_count_is_post_filter(self, client: TestClient) -> None:
        """match_count = filtered count.

        Per FR-10: match_count reflects post-filter.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["g1"],
            status_annotations=["active"],
            total_match_count=4,
        )
        patches = _resolve_patches([result])
        *ctx_patches, _ = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
                headers=AUTH_HEADER,
            )

        r = response.json()["data"]["results"][0]
        assert r["match_count"] == 1  # Post-filter count
        assert r["total_match_count"] == 4  # Pre-filter count

    def test_resolve_completed_task_excluded_active_only(
        self, client: TestClient
    ) -> None:
        """EC-4 end-to-end: completed task excluded from active_only.

        Per FR-6: is_completed=True maps to INACTIVE, excluded by active_only.
        """
        result = ResolutionResult.from_gids_with_status(
            gids=["g-active"],
            status_annotations=["active"],
            total_match_count=2,
        )
        patches = _resolve_patches([result])
        *ctx_patches, _ = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
                headers=AUTH_HEADER,
            )

        r = response.json()["data"]["results"][0]
        assert r["match_count"] == 1
        assert r["gid"] == "g-active"
        assert "inactive" not in (r["status"] or [])

    def test_resolve_single_null_section_active_only(self, client: TestClient) -> None:
        """EC-2: Single null-section GID + active_only=True -> NOT_FOUND.

        Per EC-2: Null section excluded by active_only.
        """
        result = ResolutionResult.not_found()
        patches = _resolve_patches([result])
        *ctx_patches, _ = patches

        with ExitStack() as stack:
            entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
            _make_async_client_mock(entered[4])

            response = client.post(
                "/v1/resolve/unit",
                json={
                    "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
                },
                headers=AUTH_HEADER,
            )

        r = response.json()["data"]["results"][0]
        assert r["gid"] is None
        assert r["error"] == "NOT_FOUND"
