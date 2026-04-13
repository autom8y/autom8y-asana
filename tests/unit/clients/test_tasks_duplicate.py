"""Tests for TasksClient.duplicate_async() and duplicate().

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT FR-DUP-*: Tests for task duplication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from autom8_asana.clients.tasks import TasksClient
from autom8_asana.models import Task

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig


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


def make_job_response(new_task_gid: str, new_task_name: str) -> dict[str, Any]:
    """Create a mock Asana duplicate job response."""
    return {
        "gid": "123456789012",
        "resource_type": "job",
        "resource_subtype": "duplicate_task",
        "status": "in_progress",
        "new_task": {
            "gid": new_task_gid,
            "resource_type": "task",
            "name": new_task_name,
        },
    }


# Valid GIDs for testing (Asana GIDs are numeric strings)
TEMPLATE_GID = "1234567890123"
NEW_TASK_GID = "9876543210987"
NEW_TASK_GID_2 = "1111111111111"


class TestDuplicateAsync:
    """Tests for TasksClient.duplicate_async()."""

    async def test_duplicate_async_returns_task_model(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async returns Task model by default."""
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "Duplicated Task")

        result = await tasks_client.duplicate_async(
            TEMPLATE_GID, name="Duplicated Task"
        )

        assert isinstance(result, Task)
        assert result.gid == NEW_TASK_GID
        assert result.name == "Duplicated Task"

    async def test_duplicate_async_returns_raw_dict_when_raw_true(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async returns raw dict when raw=True."""
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "Duplicated Task")

        result = await tasks_client.duplicate_async(
            TEMPLATE_GID, name="Duplicated Task", raw=True
        )

        assert isinstance(result, dict)
        assert result["gid"] == NEW_TASK_GID
        assert result["name"] == "Duplicated Task"

    async def test_duplicate_async_calls_correct_endpoint(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async calls POST /tasks/{gid}/duplicate."""
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "New Task")

        await tasks_client.duplicate_async(TEMPLATE_GID, name="New Task")

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == f"/tasks/{TEMPLATE_GID}/duplicate"
        assert call_args[1]["json"]["data"]["name"] == "New Task"

    async def test_duplicate_async_with_include_options(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async passes include options in request."""
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "New Task")

        await tasks_client.duplicate_async(
            TEMPLATE_GID,
            name="New Task",
            include=["subtasks", "notes", "assignee"],
        )

        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]["data"]
        assert payload["name"] == "New Task"
        assert payload["include"] == ["subtasks", "notes", "assignee"]

    async def test_duplicate_async_without_include_options(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async omits include when not provided."""
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "New Task")

        await tasks_client.duplicate_async(TEMPLATE_GID, name="New Task")

        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]["data"]
        assert payload["name"] == "New Task"
        assert "include" not in payload

    async def test_duplicate_async_validates_empty_gid(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async validates task_gid is not empty."""
        from autom8_asana.persistence.errors import GidValidationError

        with pytest.raises(GidValidationError) as exc_info:
            await tasks_client.duplicate_async("", name="New Task")

        assert "task_gid" in str(exc_info.value).lower()

    async def test_duplicate_async_extracts_new_task_from_job(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async extracts new_task from job response."""
        # Full job response structure
        job_response = {
            "gid": "789012345678",
            "resource_type": "job",
            "resource_subtype": "duplicate_task",
            "status": "succeeded",
            "new_task": {
                "gid": NEW_TASK_GID_2,
                "resource_type": "task",
                "name": "Extracted Task",
                "notes": "Some notes",
            },
        }
        mock_http.post.return_value = job_response

        result = await tasks_client.duplicate_async(TEMPLATE_GID, name="Extracted Task")

        assert result.gid == NEW_TASK_GID_2
        assert result.name == "Extracted Task"


class TestDuplicateSync:
    """Tests for TasksClient.duplicate() sync wrapper."""

    def test_duplicate_sync_returns_task_model(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate() returns Task model by default."""
        sync_task_gid = "5555555555555"
        mock_http.post.return_value = make_job_response(sync_task_gid, "Sync Task")

        result = tasks_client.duplicate(TEMPLATE_GID, name="Sync Task")

        assert isinstance(result, Task)
        assert result.gid == sync_task_gid
        assert result.name == "Sync Task"

    def test_duplicate_sync_returns_raw_dict_when_raw_true(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate() returns raw dict when raw=True."""
        sync_task_gid = "5555555555555"
        mock_http.post.return_value = make_job_response(sync_task_gid, "Sync Task")

        result = tasks_client.duplicate(TEMPLATE_GID, name="Sync Task", raw=True)

        assert isinstance(result, dict)
        assert result["gid"] == sync_task_gid

    def test_duplicate_sync_with_include_options(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate() passes include options correctly."""
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "New Task")

        tasks_client.duplicate(
            TEMPLATE_GID,
            name="New Task",
            include=["subtasks", "dates"],
        )

        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]["data"]
        assert payload["include"] == ["subtasks", "dates"]


class TestDuplicateIncludeOptions:
    """Tests for all valid include options per Asana API."""

    @pytest.mark.parametrize(
        "include_option",
        [
            "subtasks",
            "notes",
            "assignee",
            "attachments",
            "dates",
            "dependencies",
            "collaborators",
            "tags",
        ],
    )
    async def test_duplicate_async_accepts_valid_include_options(
        self,
        tasks_client: TasksClient,
        mock_http: MockHTTPClient,
        include_option: str,
    ) -> None:
        """duplicate_async accepts all valid include options."""
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "New Task")

        await tasks_client.duplicate_async(
            TEMPLATE_GID,
            name="New Task",
            include=[include_option],
        )

        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]["data"]
        assert include_option in payload["include"]

    async def test_duplicate_async_with_all_include_options(
        self, tasks_client: TasksClient, mock_http: MockHTTPClient
    ) -> None:
        """duplicate_async handles all include options together."""
        all_options = [
            "subtasks",
            "notes",
            "assignee",
            "attachments",
            "dates",
            "dependencies",
            "collaborators",
            "tags",
        ]
        mock_http.post.return_value = make_job_response(NEW_TASK_GID, "Full Copy")

        await tasks_client.duplicate_async(
            TEMPLATE_GID,
            name="Full Copy",
            include=all_options,
        )

        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]["data"]
        assert set(payload["include"]) == set(all_options)
