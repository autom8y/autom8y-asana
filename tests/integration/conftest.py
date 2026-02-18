"""Shared fixtures for integration tests.

Provides mock client and task fixtures for testing GID validation.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def client_fixture(mock_http, auth_provider, logger):
    """Create a mock AsanaClient for testing."""
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.tasks import TasksClient
    from autom8_asana.config import AsanaConfig

    config = AsanaConfig()

    # Create mock client
    client = MagicMock(spec=AsanaClient)
    client._http = mock_http
    client._auth_provider = auth_provider
    client._log = logger
    client.config = config

    # Create TasksClient with mock HTTP
    tasks_client = TasksClient(
        http=mock_http,
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
        client=client,
    )

    client.tasks = tasks_client

    return client


@pytest.fixture
def task_fixture():
    """Create a mock Task for testing."""
    from autom8_asana.models.task import Task

    return Task(gid="1234567890", name="Test Task")
