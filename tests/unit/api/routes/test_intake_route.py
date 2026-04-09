"""Tests for intake process routing endpoint.

POST /v1/intake/route - Route a unit to a process type

Per IMPL spec section 4:
- Idempotent: existing open process returns is_new=False (200, not 409)
- Completed processes ignored (new one created)
- Assignee resolution via fuzzy match (logs warning if not found, does not fail)
- due_at set on the process task
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

BUSINESS_PROJECT_GID = "1234567890123456"
UNIT_GID = "unit_001"
PROCESS_GID = "process_new_001"
EXISTING_PROCESS_GID = "process_existing_001"

ROUTE_BODY = {
    "unit_gid": UNIT_GID,
    "process_type": "sales",
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


def _make_collect_mock(return_value):
    """Create a mock object whose .collect() returns an AsyncMock with given value.

    Matches the PageIterator pattern: service calls method(...).collect().
    """
    collector = MagicMock()
    collector.collect = AsyncMock(return_value=return_value)
    return collector


def _make_mock_asana_client(
    *,
    existing_processes: list[dict] | None = None,
    raise_on_get: Exception | None = None,
    raise_on_create: Exception | None = None,
    users: list[dict] | None = None,
) -> MagicMock:
    """Create mock AsanaClient for route tests.

    Args:
        existing_processes: List of existing process subtasks under unit.
        raise_on_get: Exception to raise on tasks.get_async.
        raise_on_create: Exception to raise on tasks.create_async.
        users: Mock workspace users for assignee resolution.
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # tasks.get_async -- validate unit exists
    if raise_on_get:
        mock_client.tasks.get_async = AsyncMock(side_effect=raise_on_get)
    else:
        mock_client.tasks.get_async = AsyncMock(
            return_value={"gid": UNIT_GID, "name": "Unit Task"},
        )

    # tasks.subtasks_async -- returns PageIterator-like with .collect()
    mock_client.tasks.subtasks_async = MagicMock(
        return_value=_make_collect_mock(existing_processes or []),
    )

    # tasks.create_async -- create new process (subtask with parent= kwarg)
    if raise_on_create:
        mock_client.tasks.create_async = AsyncMock(
            side_effect=raise_on_create,
        )
    else:
        mock_client.tasks.create_async = AsyncMock(
            return_value={"gid": PROCESS_GID},
        )

    # tasks.update_async -- set fields
    mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

    # users.list_for_workspace_async -- returns PageIterator-like with .collect()
    default_users = users or [
        {"gid": "user_alice", "name": "Alice Johnson"},
        {"gid": "user_bob", "name": "Bob Williams"},
    ]
    mock_client.users.list_for_workspace_async = MagicMock(
        return_value=_make_collect_mock(default_users),
    )

    return mock_client


def _route_patches(mock_client: MagicMock | None = None):
    """Create context manager patches for JWT, bot PAT, and AsanaClient."""
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

    mock_client_instance = mock_client or _make_mock_asana_client()

    client_patch = patch(
        "autom8_asana.api.routes.intake_create.AsanaClient",
        return_value=mock_client_instance,
    )

    # Mock the project GID resolver (not used by route, but required for service import)
    project_patch = patch(
        "autom8_asana.services.intake_create_service.resolve_business_project_gid",
        return_value=BUSINESS_PROJECT_GID,
    )

    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        project_patch,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before and after each test."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    """Create a test application with mocked lifespan."""
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")

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


@pytest.fixture()
def client(app) -> TestClient:
    """Synchronous test client with lifespan events."""
    with TestClient(app) as tc:
        yield tc


# ---------------------------------------------------------------------------
# POST /v1/intake/route
# ---------------------------------------------------------------------------


class TestRouteIntakeProcessEndpoint:
    """POST /v1/intake/route"""

    def test_new_process_created(self, client: TestClient) -> None:
        """New process created when none exists. Returns is_new=True."""
        mock_asana = _make_mock_asana_client(existing_processes=[])
        patches = _route_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=ROUTE_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        data = body["data"]
        assert data["process_gid"] == PROCESS_GID
        assert data["process_type"] == "sales"
        assert data["is_new"] is True

    def test_existing_open_process_reused(self, client: TestClient) -> None:
        """Existing open process returned with is_new=False (idempotent)."""
        mock_asana = _make_mock_asana_client(
            existing_processes=[
                {
                    "gid": EXISTING_PROCESS_GID,
                    "name": "Sales Process",
                    "completed": False,
                },
            ],
        )
        patches = _route_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=ROUTE_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["process_gid"] == EXISTING_PROCESS_GID
        assert data["is_new"] is False

        # Verify no new task was created (create_async not called with parent=)
        mock_asana.tasks.create_async.assert_not_called()

    def test_completed_process_not_reused(self, client: TestClient) -> None:
        """Completed process is ignored; new one created."""
        mock_asana = _make_mock_asana_client(
            existing_processes=[
                {
                    "gid": EXISTING_PROCESS_GID,
                    "name": "Sales Process",
                    "completed": True,  # Completed -- should be ignored
                },
            ],
        )
        patches = _route_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=ROUTE_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["process_gid"] == PROCESS_GID  # New one
        assert data["is_new"] is True

        # Verify a new task WAS created via create_async
        mock_asana.tasks.create_async.assert_called_once()

    def test_with_assignee_fuzzy_match(self, client: TestClient) -> None:
        """Assignee resolved by fuzzy name match."""
        mock_asana = _make_mock_asana_client()
        patches = _route_patches(mock_asana)

        body = {**ROUTE_BODY, "assignee_name": "Alice"}

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_new"] is True
        # Assignee should be resolved to Alice's name
        assert data["assignee_name"] is not None

        # Verify update was called to set assignee
        mock_asana.tasks.update_async.assert_called()

    def test_assignee_not_found_still_succeeds(self, client: TestClient) -> None:
        """Missing assignee logs warning but does not fail."""
        mock_asana = _make_mock_asana_client(users=[])  # No users found
        patches = _route_patches(mock_asana)

        body = {**ROUTE_BODY, "assignee_name": "Nonexistent Person"}

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_new"] is True
        assert data["process_gid"] == PROCESS_GID
        # Assignee name echoed back even though resolution failed
        assert data["assignee_name"] == "Nonexistent Person"

    def test_with_due_at(self, client: TestClient) -> None:
        """due_at set on the process task."""
        mock_asana = _make_mock_asana_client()
        patches = _route_patches(mock_asana)

        body = {**ROUTE_BODY, "due_at": "2026-04-01T10:00:00Z"}

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200

        # Verify due_at was included in the create_async call
        create_call = mock_asana.tasks.create_async.call_args
        assert create_call.kwargs.get("due_at") == "2026-04-01T10:00:00Z"

    def test_unit_not_found_404(self, client: TestClient) -> None:
        """Invalid unit_gid returns 404 UNIT_NOT_FOUND."""
        mock_asana = _make_mock_asana_client(
            raise_on_get=Exception("Not Found"),
        )
        patches = _route_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=ROUTE_BODY,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "UNIT_NOT_FOUND"

    def test_unknown_process_type_422(self, client: TestClient) -> None:
        """Unknown process_type returns 422 UNKNOWN_PROCESS_TYPE."""
        patches = _route_patches()

        body = {"unit_gid": UNIT_GID, "process_type": "nonexistent"}

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/intake/route",
                json=body,
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "UNKNOWN_PROCESS_TYPE"

    def test_requires_s2s_jwt(self, client: TestClient) -> None:
        """Missing auth header returns 401."""
        resp = client.post(
            "/v1/intake/route",
            json=ROUTE_BODY,
        )
        assert resp.status_code == 401
