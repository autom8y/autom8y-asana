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
    mock_client.batch.execute_async = AsyncMock(return_value=[
        create_success_result(gid="new_gid_123")
    ])
    return mock_client


@pytest.fixture
def mock_client_with_failure(mock_client: MagicMock) -> MagicMock:
    """Fixture providing mock client configured for single failure response."""
    mock_client.batch.execute_async = AsyncMock(return_value=[
        create_failure_result(message="API Error", status_code=400)
    ])
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


def create_multi_result(
    count: int,
    failure_indices: set[int] | None = None,
) -> list[BatchResult]:
    """Create multiple BatchResults.

    Args:
        count: Number of results to create.
        failure_indices: Set of indices to make failures (default: all succeed).

    Returns:
        List of BatchResult in order.
    """
    failure_indices = failure_indices or set()
    results = []

    for i in range(count):
        if i in failure_indices:
            results.append(create_failure_result(
                message=f"Error at index {i}",
                status_code=400,
                request_index=i,
            ))
        else:
            results.append(create_success_result(
                gid=f"gid_{i}",
                name=f"Result {i}",
                request_index=i,
            ))

    return results


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


def create_task_hierarchy(
    depth: int = 3,
    width: int = 2,
) -> list[Task]:
    """Create a hierarchical tree of tasks for testing.

    Args:
        depth: Number of levels in the hierarchy.
        width: Number of children per parent at each level.

    Returns:
        Flat list of all tasks in the hierarchy.
    """
    tasks: list[Task] = []
    root = Task(gid="root", name="Root")
    tasks.append(root)

    current_level = [root]

    for level in range(1, depth):
        next_level: list[Task] = []
        for parent in current_level:
            for child_idx in range(width):
                child_gid = f"l{level}_p{parent.gid}_{child_idx}"
                child = Task(
                    gid=child_gid,
                    name=f"Level {level} Child {child_idx}",
                    parent=NameGid(gid=parent.gid or ""),
                )
                tasks.append(child)
                next_level.append(child)
        current_level = next_level

    return tasks


# ---------------------------------------------------------------------------
# Test Utilities
# ---------------------------------------------------------------------------


class CallTracker:
    """Utility for tracking function calls in tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(args)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def reset(self) -> None:
        self.calls.clear()


@pytest.fixture
def call_tracker() -> CallTracker:
    """Fixture providing a call tracker instance."""
    return CallTracker()
