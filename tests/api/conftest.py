"""Fixtures for API route tests.

This module provides pytest fixtures for testing the FastAPI routes:
- Test client with app factory
- Mock SDK client for isolated testing
- Mock HTTP client for paginated responses
- Request ID injection
"""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create a synchronous test client for the FastAPI application.

    This uses FastAPI's TestClient which is synchronous but can test
    async routes. It handles lifespan events automatically.

    Yields:
        TestClient instance for making HTTP requests.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client for paginated responses.

    Returns:
        MagicMock with get_paginated method configured.
    """
    http_mock = MagicMock()
    http_mock.get_paginated = AsyncMock(return_value=([], None))
    return http_mock


@pytest.fixture
def mock_users_client() -> MagicMock:
    """Create a mock UsersClient.

    Returns:
        MagicMock with common users methods configured.
    """
    users_mock = MagicMock()
    users_mock.me_async = AsyncMock(
        return_value={
            "gid": "1234567890",
            "name": "Test User",
            "email": "test@example.com",
        }
    )
    users_mock.get_async = AsyncMock(
        return_value={
            "gid": "9876543210",
            "name": "Other User",
            "email": "other@example.com",
        }
    )
    return users_mock


@pytest.fixture
def mock_workspaces_client() -> MagicMock:
    """Create a mock WorkspacesClient.

    Returns:
        MagicMock with common workspaces methods configured.
    """
    workspaces_mock = MagicMock()
    workspaces_mock.get_async = AsyncMock(
        return_value={
            "gid": "1111111111",
            "name": "Test Workspace",
            "is_organization": True,
        }
    )
    return workspaces_mock


@pytest.fixture
def mock_tasks_client() -> MagicMock:
    """Create a mock TasksClient.

    Returns:
        MagicMock with common tasks methods configured.
    """
    tasks_mock = MagicMock()

    # Default return values
    default_task = {
        "gid": "2222222222",
        "name": "Test Task",
        "notes": "Task notes",
        "completed": False,
    }

    # Configure async methods
    tasks_mock.get_async = AsyncMock(return_value=default_task)
    tasks_mock.create_async = AsyncMock(return_value=default_task)
    tasks_mock.update_async = AsyncMock(return_value=default_task)
    tasks_mock.delete_async = AsyncMock(return_value=None)

    # Methods that return model objects (need model_dump)
    task_model = MagicMock()
    task_model.model_dump.return_value = default_task

    tasks_mock.add_tag_async = AsyncMock(return_value=task_model)
    tasks_mock.remove_tag_async = AsyncMock(return_value=task_model)
    tasks_mock.move_to_section_async = AsyncMock(return_value=task_model)
    tasks_mock.set_assignee_async = AsyncMock(return_value=task_model)
    tasks_mock.add_to_project_async = AsyncMock(return_value=task_model)
    tasks_mock.remove_from_project_async = AsyncMock(return_value=task_model)
    tasks_mock.duplicate_async = AsyncMock(return_value=default_task)

    return tasks_mock


@pytest.fixture
def mock_asana_client(
    mock_http_client: MagicMock,
    mock_users_client: MagicMock,
    mock_workspaces_client: MagicMock,
    mock_tasks_client: MagicMock,
) -> MagicMock:
    """Create a fully mocked AsanaClient.

    Combines all sub-client mocks into a single mock client.

    Returns:
        MagicMock configured as an AsanaClient.
    """
    client_mock = MagicMock()
    client_mock._http = mock_http_client
    client_mock.users = mock_users_client
    client_mock.workspaces = mock_workspaces_client
    client_mock.tasks = mock_tasks_client

    # Support async context manager (if used)
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=None)

    return client_mock


@pytest.fixture
def auth_header() -> dict[str, str]:
    """Generate a valid Authorization header for tests.

    Returns:
        Dictionary with Authorization header containing a test token.
    """
    return {"Authorization": "Bearer test_pat_token_12345"}


@pytest.fixture
def authed_client(
    app, mock_asana_client: MagicMock, auth_header: dict[str, str]
) -> Generator[tuple[TestClient, MagicMock], None, None]:
    """Create a test client with mocked AsanaClient dependency.

    This uses FastAPI's dependency_overrides to inject the mock client,
    allowing tests to verify SDK interactions without live API calls.

    Yields:
        Tuple of (TestClient, mock_asana_client) for assertions.
    """
    from autom8_asana.api.dependencies import get_asana_client

    async def mock_get_asana_client() -> AsyncGenerator[MagicMock, None]:
        yield mock_asana_client

    # Use FastAPI's dependency override mechanism
    app.dependency_overrides[get_asana_client] = mock_get_asana_client

    try:
        with TestClient(app) as test_client:
            yield test_client, mock_asana_client
    finally:
        # Clean up override
        app.dependency_overrides.clear()


# Constants for test data
TEST_USER_GID = "1234567890"
TEST_WORKSPACE_GID = "1111111111"
TEST_PROJECT_GID = "3333333333"
TEST_SECTION_GID = "4444444444"
TEST_TASK_GID = "2222222222"
TEST_TAG_GID = "5555555555"
