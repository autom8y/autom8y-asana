"""Shared pytest fixtures for autom8_asana tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from typing import Any


class MockClientBuilder:
    """Builder pattern for mock AsanaClient.

    Provides consistent mock client construction with explicit
    opt-in for each capability (batch, http, cache, etc.).

    Example:
        >>> client = (MockClientBuilder()
        ...     .with_batch(results=[success_result])
        ...     .with_http()
        ...     .build())
    """

    def __init__(self) -> None:
        self._client = MagicMock()
        self._client._log = None

    def with_workspace_gid(self, gid: str = "workspace_123") -> MockClientBuilder:
        """Set default workspace GID."""
        self._client.default_workspace_gid = gid
        return self

    def with_batch(
        self,
        results: list[Any] | None = None,
    ) -> MockClientBuilder:
        """Add mock batch client with execute_async."""
        batch_mock = MagicMock()
        batch_mock.execute_async = AsyncMock(return_value=results or [])
        self._client.batch = batch_mock
        return self

    def with_http(
        self,
        response: dict[str, Any] | None = None,
    ) -> MockClientBuilder:
        """Add mock HTTP client."""
        http_mock = AsyncMock()
        http_mock.request = AsyncMock(return_value=response or {"data": {}})
        self._client._http = http_mock
        return self

    def with_cache(self, cache_provider: Any = None) -> MockClientBuilder:
        """Add cache provider to client."""
        self._client._cache = cache_provider
        return self

    def with_projects_list(
        self,
        projects: list[Any] | None = None,
    ) -> MockClientBuilder:
        """Add mock projects.list_async with collect() support."""
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=projects or [])
        self._client.projects = MagicMock()
        self._client.projects.list_async = MagicMock(return_value=mock_iterator)
        return self

    def with_tasks(self) -> MockClientBuilder:
        """Add mock tasks client."""
        self._client.tasks = MagicMock()
        self._client.tasks.update_async = AsyncMock(return_value=MagicMock())
        self._client.tasks.get_async = AsyncMock(return_value=MagicMock())
        return self

    def build(self) -> MagicMock:
        """Build and return the mock client."""
        return self._client


@pytest.fixture
def mock_client_builder() -> type[MockClientBuilder]:
    """Provide MockClientBuilder class for test customization."""
    return MockClientBuilder


@pytest.fixture(autouse=True)
def reset_settings_singleton():
    """Reset the settings singleton before and after each test.

    This ensures test isolation when tests modify environment variables
    that affect Pydantic Settings.
    """
    from autom8_asana.settings import reset_settings

    reset_settings()
    yield
    reset_settings()


@pytest.fixture(autouse=True)
def reset_registries():
    """Reset all registry singletons before and after each test.

    This ensures test isolation for:
    - ProjectTypeRegistry (entity type detection)
    - WorkspaceProjectRegistry (project discovery)
    """
    from autom8_asana.models.business.registry import (
        ProjectTypeRegistry,
        WorkspaceProjectRegistry,
    )

    # Reset before test - use classmethod to clear singletons
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()

    yield

    # Reset after test
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()
