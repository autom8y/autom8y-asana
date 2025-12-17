"""Tests for TasksClient.dependents_async().

Per FR-PREREQ-003: Tests for the dependents_async() method following subtasks_async() pattern.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from autom8_asana.clients.tasks import TasksClient
from autom8_asana.config import AsanaConfig
from autom8_asana.models import PageIterator, Task


class MockHTTPClient:
    """Mock HTTP client for testing TasksClient."""

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


@pytest.fixture
def mock_http() -> MockHTTPClient:
    """Create mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def config() -> AsanaConfig:
    """Default test configuration."""
    return AsanaConfig()


@pytest.fixture
def auth_provider() -> MockAuthProvider:
    """Mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def tasks_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
) -> TasksClient:
    """Create TasksClient with mocked dependencies."""
    return TasksClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        client=None,
    )


class TestDependentsAsync:
    """Tests for TasksClient.dependents_async()."""

    async def test_dependents_async_returns_page_iterator(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async returns PageIterator[Task]."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "dep1", "name": "Dependent 1"},
                {"gid": "dep2", "name": "Dependent 2"},
            ],
            None,
        )

        result = tasks_client.dependents_async("5123")

        assert isinstance(result, PageIterator)

        # Collect results
        items = await result.collect()
        assert len(items) == 2
        assert all(isinstance(t, Task) for t in items)
        assert items[0].gid == "dep1"
        assert items[0].name == "Dependent 1"
        assert items[1].gid == "dep2"
        assert items[1].name == "Dependent 2"

    async def test_dependents_async_empty_result(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async handles empty result (task has no dependents)."""
        mock_http.get_paginated.return_value = ([], None)

        result = tasks_client.dependents_async("1234567890")

        items = await result.collect()
        assert items == []

    async def test_dependents_async_with_opt_fields(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async passes opt_fields parameter correctly."""
        mock_http.get_paginated.return_value = (
            [{"gid": "dep1", "name": "Dependent 1", "notes": "Some notes"}],
            None,
        )

        result = tasks_client.dependents_async("5123", opt_fields=["name", "notes"])

        items = await result.collect()
        assert len(items) == 1
        assert items[0].notes == "Some notes"

        # Verify opt_fields was passed in params
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["opt_fields"] == "name,notes"

    async def test_dependents_async_with_limit(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async respects limit parameter."""
        mock_http.get_paginated.return_value = (
            [{"gid": "dep1", "name": "Dependent 1"}],
            None,
        )

        result = tasks_client.dependents_async("5123", limit=50)

        await result.collect()

        # Verify limit was passed in params
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["limit"] == 50

    async def test_dependents_async_limit_capped_at_100(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async caps limit at 100 (Asana API max)."""
        mock_http.get_paginated.return_value = (
            [{"gid": "dep1", "name": "Dependent 1"}],
            None,
        )

        result = tasks_client.dependents_async("5123", limit=200)

        await result.collect()

        # Verify limit is capped at 100
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[1]["params"]["limit"] == 100

    async def test_dependents_async_pagination(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async handles multiple pages correctly."""
        # First call returns page 1 with offset for next page
        # Second call returns page 2 with no more pages
        mock_http.get_paginated.side_effect = [
            ([{"gid": "dep1", "name": "Dependent 1"}], "offset_token"),
            ([{"gid": "dep2", "name": "Dependent 2"}], None),
        ]

        result = tasks_client.dependents_async("5123")

        items = await result.collect()

        assert len(items) == 2
        assert items[0].gid == "dep1"
        assert items[1].gid == "dep2"

        # Verify both pages were fetched
        assert mock_http.get_paginated.call_count == 2

        # First call should not have offset
        first_call = mock_http.get_paginated.call_args_list[0]
        assert "offset" not in first_call[1]["params"]

        # Second call should have offset from first response
        second_call = mock_http.get_paginated.call_args_list[1]
        assert second_call[1]["params"]["offset"] == "offset_token"

    async def test_dependents_async_endpoint_verification(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async calls correct endpoint /tasks/{task_gid}/dependents."""
        mock_http.get_paginated.return_value = (
            [{"gid": "dep1", "name": "Dependent 1"}],
            None,
        )

        result = tasks_client.dependents_async("5123")

        await result.collect()

        # Verify the correct endpoint was called
        mock_http.get_paginated.assert_called_once()
        call_args = mock_http.get_paginated.call_args
        assert call_args[0][0] == "/tasks/5123/dependents"

    async def test_dependents_async_with_special_characters_in_gid(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async works with numeric GIDs (typical Asana format)."""
        mock_http.get_paginated.return_value = (
            [{"gid": "dep1", "name": "Dependent 1"}],
            None,
        )

        result = tasks_client.dependents_async("1234567890123456")

        await result.collect()

        call_args = mock_http.get_paginated.call_args
        assert call_args[0][0] == "/tasks/1234567890123456/dependents"

    async def test_dependents_async_validates_task_gid(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """dependents_async validates task_gid is not empty."""
        from autom8_asana.persistence.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            tasks_client.dependents_async("")

        assert "task_gid" in str(exc_info.value).lower()

    async def test_dependents_async_first_method(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """PageIterator.first() works correctly with dependents."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "dep1", "name": "First Dependent"},
                {"gid": "dep2", "name": "Second Dependent"},
            ],
            None,
        )

        result = tasks_client.dependents_async("5123")
        first = await result.first()

        assert first is not None
        assert first.gid == "dep1"
        assert first.name == "First Dependent"

    async def test_dependents_async_take_method(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """PageIterator.take(n) works correctly with dependents."""
        mock_http.get_paginated.return_value = (
            [
                {"gid": "dep1", "name": "Dependent 1"},
                {"gid": "dep2", "name": "Dependent 2"},
                {"gid": "dep3", "name": "Dependent 3"},
            ],
            None,
        )

        result = tasks_client.dependents_async("5123")
        taken = await result.take(2)

        assert len(taken) == 2
        assert taken[0].gid == "dep1"
        assert taken[1].gid == "dep2"
