"""Fixtures for API route tests.

This module provides pytest fixtures for testing the FastAPI routes:
- Test client with app factory
- Mock SDK client for isolated testing
- Mock HTTP client for paginated responses
- Request ID injection
"""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.dual_mode import AuthMode
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.resolver import EntityProjectRegistry

# Standard test entity registrations shared by lifespan mock and per-test reset
_TEST_ENTITIES = [
    ("offer", "1143843662099250", "Business Offers"),
    ("unit", "1201081073731555", "Business Units"),
    ("contact", "1200775689604552", "Contacts"),
    ("business", "1234567890123456", "Business"),
]


def _populate_test_registry():
    """Reset and re-populate EntityProjectRegistry with test data.

    Called both during module-scoped lifespan and per-test reset so that
    routes using EntityProjectRegistry.get_instance() always see the
    standard test registrations.
    """
    EntityProjectRegistry.reset()
    registry = EntityProjectRegistry.get_instance()
    for entity_type, gid, name in _TEST_ENTITIES:
        registry.register(
            entity_type=entity_type,
            project_gid=gid,
            project_name=name,
        )
    return registry


@pytest.fixture(scope="module")
def app():
    """Create a test application instance once per module with mocked discovery.

    Module-scoped to avoid per-test ASGI lifespan overhead (~340ms/test).

    Provides a default get_auth_context override so that routes using
    AuthContextDep don't attempt real JWT validation or bot PAT lookup.
    Individual tests that need specific auth behaviour use their own
    patch() or override this override via app.dependency_overrides.
    """
    import os

    # Enable auth dev mode bypass so JWTAuthMiddleware returns bypass claims
    # instead of validating the fake JWT token. Must be set before create_app()
    # because the middleware reads env at construction time.
    _prev_dev_mode = os.environ.get("AUTH__DEV_MODE")
    _prev_env = os.environ.get("AUTOM8Y_ENV")
    os.environ["AUTH__DEV_MODE"] = "true"
    os.environ["AUTOM8Y_ENV"] = "LOCAL"

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            registry = _populate_test_registry()
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        test_app = create_app()

        # Default auth context: JWT mode with a stub bot PAT.
        # Tests that need PAT-rejection or missing-auth responses rely on
        # require_service_claims, which validates independently of this override.
        async def _mock_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service="autom8_data",
            )

        test_app.dependency_overrides[get_auth_context] = _mock_get_auth_context

        yield test_app

    # Restore env vars after the module-scoped fixture tears down
    if _prev_dev_mode is None:
        os.environ.pop("AUTH__DEV_MODE", None)
    else:
        os.environ["AUTH__DEV_MODE"] = _prev_dev_mode
    if _prev_env is None:
        os.environ.pop("AUTOM8Y_ENV", None)
    else:
        os.environ["AUTOM8Y_ENV"] = _prev_env


@pytest.fixture(scope="module")
def _module_client(app):
    """Module-scoped TestClient — enters ASGI lifespan once."""
    with TestClient(app) as tc:
        yield tc


@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """Reset singletons before and after each test for isolation.

    Re-populates EntityProjectRegistry so that routes using
    get_instance() see test data even with module-scoped TestClient.
    """
    clear_bot_pat_cache()
    reset_auth_client()
    _populate_test_registry()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture
def client(_module_client) -> TestClient:
    """Per-test alias for the module-scoped TestClient.

    Reuses the module-scoped TestClient to avoid per-test ASGI lifespan overhead.
    """
    return _module_client


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client for paginated responses.

    Returns:
        MagicMock with get_paginated and get methods configured.
    """
    http_mock = MagicMock()
    http_mock.get_paginated = AsyncMock(return_value=([], None))
    http_mock.get = AsyncMock(return_value={})
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
def mock_sections_client() -> MagicMock:
    """Create a mock SectionsClient.

    Returns:
        MagicMock with common sections methods configured.
    """
    sections_mock = MagicMock()

    # Default return values
    default_section = {
        "gid": "4444444444",
        "name": "Test Section",
        "project": {"gid": "3333333333", "name": "Test Project"},
    }

    # Configure async methods
    sections_mock.get_async = AsyncMock(return_value=default_section)
    sections_mock.create_async = AsyncMock(return_value=default_section)
    sections_mock.update_async = AsyncMock(return_value=default_section)
    sections_mock.delete_async = AsyncMock(return_value=None)
    sections_mock.add_task_async = AsyncMock(return_value=None)
    sections_mock.insert_section_async = AsyncMock(return_value=None)

    return sections_mock


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
def mock_projects_client() -> MagicMock:
    """Create a mock ProjectsClient.

    Returns:
        MagicMock with common projects methods configured.
    """
    projects_mock = MagicMock()

    # Default return values
    default_project = {
        "gid": TEST_PROJECT_GID,
        "name": "Test Project",
        "notes": "Project notes",
        "workspace": {"gid": TEST_WORKSPACE_GID, "name": "Test Workspace"},
        "archived": False,
        "owner": {"gid": TEST_USER_GID, "name": "Test User"},
    }

    # Configure async methods
    projects_mock.get_async = AsyncMock(return_value=default_project)
    projects_mock.create_async = AsyncMock(return_value=default_project)
    projects_mock.update_async = AsyncMock(return_value=default_project)
    projects_mock.delete_async = AsyncMock(return_value=None)
    projects_mock.add_members_async = AsyncMock(return_value=default_project)
    projects_mock.remove_members_async = AsyncMock(return_value=default_project)

    return projects_mock


@pytest.fixture
def mock_asana_client(
    mock_http_client: MagicMock,
    mock_users_client: MagicMock,
    mock_workspaces_client: MagicMock,
    mock_sections_client: MagicMock,
    mock_tasks_client: MagicMock,
    mock_projects_client: MagicMock,
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
    client_mock.sections = mock_sections_client
    client_mock.tasks = mock_tasks_client
    client_mock.projects = mock_projects_client

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
    app, _module_client, mock_asana_client: MagicMock, auth_header: dict[str, str]
) -> Generator[tuple[TestClient, MagicMock], None, None]:
    """Create an authenticated test client using dependency overrides.

    Reuses the module-scoped TestClient and app, setting per-test
    dependency overrides for auth isolation without ASGI lifespan overhead.

    Yields:
        Tuple of (TestClient, mock_asana_client) for assertions.
    """
    from autom8_asana.api.dependencies import get_asana_client_from_context

    async def mock_get_asana_client_from_context() -> AsyncGenerator[MagicMock, None]:
        yield mock_asana_client

    # Use FastAPI's dependency override mechanism
    app.dependency_overrides[get_asana_client_from_context] = (
        mock_get_asana_client_from_context
    )

    try:
        yield _module_client, mock_asana_client
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
TEST_TEAM_GID = "6666666666"
