"""Shared fixtures for integration tests.

Provides mock client and task fixtures for testing GID validation.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    WorkspaceProjectRegistry,
)


@pytest.fixture(autouse=True)
def reset_registries_after_test() -> Generator[None, None, None]:
    """Auto-reset registries after each integration test.

    Per ADR-0093/ADR-0108: Singleton registries must be reset between tests
    to ensure test isolation. This fixture runs automatically for all
    integration tests.
    """
    yield
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()


class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(self) -> None:
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()
        self.get_paginated = AsyncMock()


class MockAuthProvider:
    """Mock auth provider."""

    def get_secret(self, key: str) -> str:
        return "test-token"


class MockLogger:
    """Mock logger."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("debug", msg))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("info", msg))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("warning", msg))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("error", msg))


@pytest.fixture
def mock_http():
    """Create a mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def mock_auth():
    """Create a mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MockLogger()


@pytest.fixture
def client_fixture(mock_http, mock_auth, mock_logger):
    """Create a mock AsanaClient for testing."""
    from autom8_asana.config import AsanaConfig
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.tasks import TasksClient

    config = AsanaConfig()

    # Create mock client
    client = MagicMock(spec=AsanaClient)
    client._http = mock_http
    client._auth_provider = mock_auth
    client._log = mock_logger
    client.config = config

    # Create TasksClient with mock HTTP
    tasks_client = TasksClient(
        http=mock_http,
        config=config,
        auth_provider=mock_auth,
        log_provider=mock_logger,
        client=client,
    )

    client.tasks = tasks_client

    return client


@pytest.fixture
def task_fixture():
    """Create a mock Task for testing."""
    from autom8_asana.models.task import Task

    return Task(gid="1234567890", name="Test Task")
