"""Contract tests for adapter consumption of autom8_asana responses.

These tests verify that autom8_asana response envelopes and field shapes
match what the monolith adapter's ResponseNormalizer expects.

If these tests fail, the adapter normalization layer may break.

Per TDD-GAP-07 Section 7.1:
- TestTaskResponseContract: envelope, required fields, custom_fields, dates, assignee
- TestListResponseContract: pagination meta shape, data is array
- TestSectionResponseContract: gid and name
- TestUserResponseContract: gid, name, email
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_task_data(
    gid: str = "1234567890",
    name: str = "Contract Test Task",
    completed: bool = False,
    assignee: dict[str, Any] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
    due_on: str | None = "2026-03-15",
    due_at: str | None = None,
    created_at: str = "2026-02-07T12:00:00.000Z",
    modified_at: str = "2026-02-07T12:30:00.000Z",
) -> dict[str, Any]:
    """Build a realistic task dict matching what TaskService.get_task returns."""
    return {
        "gid": gid,
        "name": name,
        "resource_type": "task",
        "completed": completed,
        "notes": "Some notes",
        "assignee": assignee or {"gid": "user_111", "name": "Alice"},
        "custom_fields": custom_fields
        if custom_fields is not None
        else [
            {
                "gid": "cf_1",
                "name": "Priority",
                "type": "enum",
                "enum_value": {"name": "High"},
            },
            {"gid": "cf_2", "name": "Estimate", "type": "number", "number_value": 5},
        ],
        "due_on": due_on,
        "due_at": due_at,
        "start_on": None,
        "created_at": created_at,
        "modified_at": modified_at,
        "projects": [{"gid": "proj_123", "name": "Test Project"}],
        "tags": [{"gid": "tag_1", "name": "urgent"}],
    }


def _make_section_data(
    gid: str = "section_123",
    name: str = "Contract Test Section",
) -> dict[str, Any]:
    """Build a realistic section dict."""
    return {
        "gid": gid,
        "name": name,
        "resource_type": "section",
        "project": {"gid": "proj_123", "name": "Test Project"},
        "created_at": "2026-02-07T12:00:00.000Z",
    }


def _make_user_data(
    gid: str = "user_456",
    name: str = "Contract Test User",
    email: str = "contract@example.com",
) -> dict[str, Any]:
    """Build a realistic user dict."""
    return {
        "gid": gid,
        "name": name,
        "email": email,
        "resource_type": "user",
        "workspaces": [{"gid": "ws_1", "name": "Workspace"}],
    }


@pytest.fixture
def task_app() -> FastAPI:
    """FastAPI app with task router and mocked dependencies."""
    from autom8_asana.api.routes.tasks import router

    app = FastAPI()
    app.include_router(router)

    # Mock the auth dependency to return a fake client
    mock_client = MagicMock()
    mock_task_service = MagicMock()

    # get_task returns our contract test data
    mock_task_service.get_task = AsyncMock(return_value=_make_task_data())

    # list_tasks returns a paginated result
    list_result = MagicMock()
    list_result.data = [_make_task_data(gid="t1"), _make_task_data(gid="t2")]
    list_result.has_more = True
    list_result.next_offset = "cursor_abc"
    mock_task_service.list_tasks = AsyncMock(return_value=list_result)

    # Override dependencies
    from autom8_asana.api.dependencies import (
        get_asana_client_from_context,
        get_request_id,
        get_task_service,
    )

    async def _mock_client():
        yield mock_client

    app.dependency_overrides[get_asana_client_from_context] = _mock_client
    app.dependency_overrides[get_request_id] = lambda: "contract-test-req-id"
    app.dependency_overrides[get_task_service] = lambda: mock_task_service

    return app


@pytest.fixture
def task_client(task_app: FastAPI) -> TestClient:
    """TestClient for task contract tests."""
    return TestClient(task_app)


@pytest.fixture
def section_app() -> FastAPI:
    """FastAPI app with section router and mocked dependencies."""
    from autom8_asana.api.routes.sections import router

    app = FastAPI()
    app.include_router(router)

    mock_client = MagicMock()
    mock_section_service = MagicMock()
    mock_section_service.get_section = AsyncMock(return_value=_make_section_data())

    from autom8_asana.api.dependencies import (
        get_asana_client_from_context,
        get_request_id,
        get_section_service,
    )

    async def _mock_client():
        yield mock_client

    app.dependency_overrides[get_asana_client_from_context] = _mock_client
    app.dependency_overrides[get_request_id] = lambda: "contract-test-req-id"
    app.dependency_overrides[get_section_service] = lambda: mock_section_service

    return app


@pytest.fixture
def section_client(section_app: FastAPI) -> TestClient:
    """TestClient for section contract tests."""
    return TestClient(section_app)


@pytest.fixture
def user_app() -> FastAPI:
    """FastAPI app with user router and mocked dependencies."""
    from autom8_asana.api.routes.users import router

    app = FastAPI()
    app.include_router(router)

    mock_client = MagicMock()
    # Users route calls client.users.get_async directly (no service layer)
    mock_client.users = MagicMock()
    mock_client.users.get_async = AsyncMock(return_value=_make_user_data())

    from autom8_asana.api.dependencies import (
        get_asana_client_from_context,
        get_request_id,
    )

    async def _mock_client():
        yield mock_client

    app.dependency_overrides[get_asana_client_from_context] = _mock_client
    app.dependency_overrides[get_request_id] = lambda: "contract-test-req-id"

    return app


@pytest.fixture
def user_client(user_app: FastAPI) -> TestClient:
    """TestClient for user contract tests."""
    return TestClient(user_app)


# ---------------------------------------------------------------------------
# Task Response Contract Tests
# ---------------------------------------------------------------------------


class TestTaskResponseContract:
    """Verify task response shape matches adapter expectations.

    The monolith adapter expects:
    - Response wrapped in {"data": {...}, "meta": {...}} envelope
    - data contains: gid, name, completed, assignee, custom_fields, due_on
    - custom_fields is a list (adapter re-indexes to dict by name)
    - Date fields are strings (adapter converts to arrow.Arrow)
    - assignee is a dict with gid key (or null)
    """

    def test_get_task_returns_envelope_with_data(self, task_client: TestClient) -> None:
        """Response has {"data": {...}, "meta": {...}} structure."""
        response = task_client.get("/api/v1/tasks/1234567890")
        assert response.status_code == 200

        body = response.json()
        assert "data" in body, "Response must have 'data' key"
        assert "meta" in body, "Response must have 'meta' key"
        assert isinstance(body["data"], dict), "data must be a dict for single resource"
        assert isinstance(body["meta"], dict), "meta must be a dict"

    def test_task_data_contains_required_fields(self, task_client: TestClient) -> None:
        """data dict contains gid, name, completed, assignee, custom_fields, due_on."""
        response = task_client.get("/api/v1/tasks/1234567890")
        data = response.json()["data"]

        required_fields = {
            "gid",
            "name",
            "completed",
            "assignee",
            "custom_fields",
            "due_on",
        }
        missing = required_fields - set(data.keys())
        assert not missing, f"Task data missing required fields: {missing}"

    def test_custom_fields_is_list(self, task_client: TestClient) -> None:
        """custom_fields is a list of dicts, not a dict keyed by name.

        The adapter's normalize_task re-indexes this list into a dict.
        If this contract changes, the normalizer breaks.
        """
        response = task_client.get("/api/v1/tasks/1234567890")
        data = response.json()["data"]

        assert isinstance(data["custom_fields"], list), (
            "custom_fields must be a list (adapter re-indexes to dict)"
        )
        if data["custom_fields"]:
            assert isinstance(data["custom_fields"][0], dict), (
                "Each custom field must be a dict"
            )

    def test_dates_are_strings(self, task_client: TestClient) -> None:
        """due_on, created_at, modified_at are strings (not datetime objects).

        The adapter's normalizer converts these strings to arrow.Arrow.
        If the format changes from string to object, normalization breaks.
        """
        response = task_client.get("/api/v1/tasks/1234567890")
        data = response.json()["data"]

        # due_on should be a string or null
        if data.get("due_on") is not None:
            assert isinstance(data["due_on"], str), "due_on must be a string"

        # created_at and modified_at should be strings
        if data.get("created_at") is not None:
            assert isinstance(data["created_at"], str), "created_at must be a string"
        if data.get("modified_at") is not None:
            assert isinstance(data["modified_at"], str), "modified_at must be a string"

    def test_assignee_is_dict_with_gid(self, task_client: TestClient) -> None:
        """assignee is {"gid": ..., "name": ...} or null.

        The adapter's shadow comparison accesses assignee.gid for nested
        field comparison. If assignee shape changes, shadow breaks.
        """
        response = task_client.get("/api/v1/tasks/1234567890")
        data = response.json()["data"]

        assignee = data.get("assignee")
        if assignee is not None:
            assert isinstance(assignee, dict), "assignee must be a dict (or null)"
            assert "gid" in assignee, "assignee dict must have 'gid' key"

    def test_meta_contains_request_id(self, task_client: TestClient) -> None:
        """meta contains request_id for tracing."""
        response = task_client.get("/api/v1/tasks/1234567890")
        meta = response.json()["meta"]

        assert "request_id" in meta, "meta must contain request_id"
        assert isinstance(meta["request_id"], str), "request_id must be a string"

    def test_meta_contains_timestamp(self, task_client: TestClient) -> None:
        """meta contains timestamp as ISO string."""
        response = task_client.get("/api/v1/tasks/1234567890")
        meta = response.json()["meta"]

        assert "timestamp" in meta, "meta must contain timestamp"
        assert isinstance(meta["timestamp"], str), "timestamp must be a string"


# ---------------------------------------------------------------------------
# List Response Contract Tests
# ---------------------------------------------------------------------------


class TestListResponseContract:
    """Verify list response pagination shape.

    The monolith adapter's _collect_all_pages reads:
    - body["data"] as a list
    - body["meta"]["pagination"]["has_more"] as bool
    - body["meta"]["pagination"]["next_offset"] as string
    """

    def test_list_response_has_pagination_meta(self, task_client: TestClient) -> None:
        """meta.pagination contains has_more, next_offset, limit."""
        response = task_client.get("/api/v1/tasks?project=proj_123")
        assert response.status_code == 200

        body = response.json()
        meta = body["meta"]
        assert "pagination" in meta, "meta must contain pagination for list responses"

        pagination = meta["pagination"]
        assert "has_more" in pagination, "pagination must have has_more"
        assert "next_offset" in pagination, "pagination must have next_offset"
        assert "limit" in pagination, "pagination must have limit"
        assert isinstance(pagination["has_more"], bool), "has_more must be a bool"

    def test_list_data_is_array(self, task_client: TestClient) -> None:
        """data is a list of dicts for list endpoints."""
        response = task_client.get("/api/v1/tasks?project=proj_123")
        data = response.json()["data"]

        assert isinstance(data, list), "data must be a list for list endpoints"
        if data:
            assert isinstance(data[0], dict), "Each item in data must be a dict"


# ---------------------------------------------------------------------------
# Section Response Contract Tests
# ---------------------------------------------------------------------------


class TestSectionResponseContract:
    """Verify section response shape matches adapter expectations."""

    def test_section_data_has_gid_and_name(self, section_client: TestClient) -> None:
        """Section data contains gid and name."""
        response = section_client.get("/api/v1/sections/section_123")
        assert response.status_code == 200

        body = response.json()
        assert "data" in body, "Response must have 'data' key"
        assert "meta" in body, "Response must have 'meta' key"

        data = body["data"]
        assert "gid" in data, "Section data must have 'gid'"
        assert "name" in data, "Section data must have 'name'"
        assert isinstance(data["gid"], str), "gid must be a string"
        assert isinstance(data["name"], str), "name must be a string"


# ---------------------------------------------------------------------------
# User Response Contract Tests
# ---------------------------------------------------------------------------


class TestUserResponseContract:
    """Verify user response shape matches adapter expectations."""

    def test_user_data_has_gid_name_email(self, user_client: TestClient) -> None:
        """User data contains gid, name, email."""
        response = user_client.get("/api/v1/users/user_456")
        assert response.status_code == 200

        body = response.json()
        assert "data" in body, "Response must have 'data' key"
        assert "meta" in body, "Response must have 'meta' key"

        data = body["data"]
        assert "gid" in data, "User data must have 'gid'"
        assert "name" in data, "User data must have 'name'"
        assert "email" in data, "User data must have 'email'"
        assert isinstance(data["gid"], str), "gid must be a string"
        assert isinstance(data["name"], str), "name must be a string"
