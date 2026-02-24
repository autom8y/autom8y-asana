"""Shared fixtures for persistence validation tests.

Provides mock clients, result builders, and test utilities
for comprehensive validation of the Save Orchestration Layer.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid

# ---------------------------------------------------------------------------
# Mock Client Fixtures
# ---------------------------------------------------------------------------


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient with mock batch client.

    Returns:
        MagicMock configured as AsanaClient with batch property.
    """
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None
    return mock_client


@pytest.fixture
def mock_client() -> MagicMock:
    """Fixture providing a mock AsanaClient."""
    return create_mock_client()


@pytest.fixture
def mock_client_with_success(mock_client: MagicMock) -> MagicMock:
    """Fixture providing mock client configured for single success response."""
    mock_client.batch.execute_async = AsyncMock(
        return_value=[create_success_result(gid="new_gid_123")]
    )
    return mock_client


@pytest.fixture
def mock_client_with_failure(mock_client: MagicMock) -> MagicMock:
    """Fixture providing mock client configured for single failure response."""
    mock_client.batch.execute_async = AsyncMock(
        return_value=[create_failure_result(message="API Error", status_code=400)]
    )
    return mock_client


# ---------------------------------------------------------------------------
# BatchResult Builders
# ---------------------------------------------------------------------------


def create_success_result(
    gid: str = "123",
    name: str = "Test",
    request_index: int = 0,
    extra_data: dict[str, Any] | None = None,
) -> BatchResult:
    """Create a successful BatchResult.

    Args:
        gid: GID to return in response data.
        name: Name to return in response data.
        request_index: Index for request correlation.
        extra_data: Additional fields to include in response data.

    Returns:
        BatchResult with 200 status and data.
    """
    data = {"gid": gid, "name": name}
    if extra_data:
        data.update(extra_data)

    return BatchResult(
        status_code=200,
        body={"data": data},
        request_index=request_index,
    )


def create_failure_result(
    message: str = "Error",
    status_code: int = 400,
    request_index: int = 0,
) -> BatchResult:
    """Create a failed BatchResult.

    Args:
        message: Error message.
        status_code: HTTP status code (4xx or 5xx).
        request_index: Index for request correlation.

    Returns:
        BatchResult with error status and message.
    """
    return BatchResult(
        status_code=status_code,
        body={"errors": [{"message": message}]},
        request_index=request_index,
    )


# ---------------------------------------------------------------------------
# Test Entity Builders
# ---------------------------------------------------------------------------


def create_task(
    gid: str | None = None,
    name: str = "Test Task",
    parent_gid: str | None = None,
) -> Task:
    """Create a Task for testing.

    Args:
        gid: Task GID (None for new entity, "temp_*" for tracked new entity).
        name: Task name.
        parent_gid: Parent task GID (creates NameGid reference).

    Returns:
        Task instance configured for testing.
    """
    parent = NameGid(gid=parent_gid) if parent_gid else None
    return Task(gid=gid, name=name, parent=parent)


