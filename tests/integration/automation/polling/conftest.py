"""Test fixtures for polling automation integration tests.

Provides real AsanaClient and test resource fixtures for integration testing.
All fixtures skip gracefully when required environment variables are not set.

Environment Variables:
    ASANA_ACCESS_TOKEN or ASANA_PAT: Asana API token (required)
    ASANA_TEST_PROJECT_GID: Test project GID (required for project tests)
    ASANA_TEST_TAG_GID: Test tag GID (required for tag tests)
    ASANA_TEST_SECTION_GID: Test section GID (required for section tests)
    ASANA_WORKSPACE_GID: Workspace GID (optional, auto-detected if single)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, AsyncGenerator

import pytest

if TYPE_CHECKING:
    from autom8_asana import AsanaClient
    from autom8_asana.models import Task


def _get_asana_token() -> str | None:
    """Get Asana token from environment.

    Checks ASANA_ACCESS_TOKEN first, then falls back to ASANA_PAT.

    Returns:
        Token string if found, None otherwise.
    """
    return os.environ.get("ASANA_ACCESS_TOKEN") or os.environ.get("ASANA_PAT")


# ============================================================================
# Client Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def asana_client() -> "AsanaClient":
    """Real Asana client from environment.

    This fixture creates a real AsanaClient using the ASANA_ACCESS_TOKEN
    or ASANA_PAT environment variable. Tests requiring this fixture will
    be skipped if no token is available.

    Scope: module (shared across tests in the same module for efficiency)
    """
    from autom8_asana import AsanaClient

    token = _get_asana_token()
    if not token:
        pytest.skip("ASANA_ACCESS_TOKEN or ASANA_PAT not set")

    return AsanaClient(token=token)


@pytest.fixture(scope="module")
def workspace_gid(asana_client: "AsanaClient") -> str:
    """Get workspace GID from client or environment.

    Uses the client's auto-detected workspace, or ASANA_WORKSPACE_GID env var.
    """
    if asana_client.default_workspace_gid:
        return asana_client.default_workspace_gid

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
    if not workspace_gid:
        pytest.skip("No workspace GID available (auto-detect failed, no ASANA_WORKSPACE_GID)")

    return workspace_gid


# ============================================================================
# Test Resource GID Fixtures
# ============================================================================


@pytest.fixture
def test_project_gid() -> str:
    """GID of a test project for integration tests.

    Tests requiring a project will be skipped if ASANA_TEST_PROJECT_GID is not set.
    """
    gid = os.environ.get("ASANA_TEST_PROJECT_GID")
    if not gid:
        pytest.skip("ASANA_TEST_PROJECT_GID not set")
    return gid


@pytest.fixture
def test_tag_gid() -> str:
    """GID of a test tag for integration tests.

    Tests requiring a tag will be skipped if ASANA_TEST_TAG_GID is not set.
    """
    gid = os.environ.get("ASANA_TEST_TAG_GID")
    if not gid:
        pytest.skip("ASANA_TEST_TAG_GID not set")
    return gid


@pytest.fixture
def test_section_gid() -> str:
    """GID of a test section for integration tests.

    Tests requiring a section will be skipped if ASANA_TEST_SECTION_GID is not set.
    """
    gid = os.environ.get("ASANA_TEST_SECTION_GID")
    if not gid:
        pytest.skip("ASANA_TEST_SECTION_GID not set")
    return gid


# ============================================================================
# Task Fixtures (create and cleanup)
# ============================================================================


@pytest.fixture
async def test_task(
    asana_client: "AsanaClient",
    test_project_gid: str,
) -> AsyncGenerator["Task", None]:
    """Create a temporary task for testing, cleanup after.

    Creates a new task in the test project with a unique name.
    The task is automatically deleted after the test completes.

    Yields:
        Task object with gid, name, and other fields.
    """
    # Generate unique task name with timestamp and UUID
    unique_id = str(uuid.uuid4())[:8]
    task_name = f"[Integration Test] {datetime.now(timezone.utc).isoformat()} - {unique_id}"

    # Create the task
    task = await asana_client.tasks.create_async(
        name=task_name,
        projects=[test_project_gid],
        notes="This task was created for integration testing. If it persists, it can be safely deleted.",
    )

    yield task

    # Cleanup: delete the task
    try:
        await asana_client.tasks.delete_async(task.gid)
    except Exception:
        # Task may already be deleted or inaccessible - that's fine
        pass


@pytest.fixture
async def stale_task(
    asana_client: "AsanaClient",
    test_project_gid: str,
) -> AsyncGenerator["Task", None]:
    """Create a task that appears stale for trigger testing.

    Note: We cannot actually make a task stale without waiting days.
    This fixture creates a task and relies on the TriggerEvaluator
    being tested with a mocked 'now' time or with appropriately
    configured stale thresholds.

    For true staleness testing, consider:
    - Using mock tasks in unit tests
    - Setting very short stale thresholds (1 day) and waiting
    - Testing with existing stale tasks in your workspace

    Yields:
        Task object that can be used for trigger testing.
    """
    unique_id = str(uuid.uuid4())[:8]
    task_name = f"[Stale Test Task] {datetime.now(timezone.utc).isoformat()} - {unique_id}"

    task = await asana_client.tasks.create_async(
        name=task_name,
        projects=[test_project_gid],
        notes="Created for stale trigger integration testing.",
    )

    yield task

    try:
        await asana_client.tasks.delete_async(task.gid)
    except Exception:
        pass


@pytest.fixture
async def task_with_due_date(
    asana_client: "AsanaClient",
    test_project_gid: str,
) -> AsyncGenerator["Task", None]:
    """Create a task with a due date in the near future.

    Creates a task due in 3 days, useful for deadline trigger testing.

    Yields:
        Task object with due_on set to 3 days from now.
    """
    unique_id = str(uuid.uuid4())[:8]
    task_name = f"[Due Date Test Task] {unique_id}"
    due_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")

    task = await asana_client.tasks.create_async(
        name=task_name,
        projects=[test_project_gid],
        due_on=due_date,
        notes="Created for deadline trigger integration testing.",
    )

    yield task

    try:
        await asana_client.tasks.delete_async(task.gid)
    except Exception:
        pass


# ============================================================================
# Mock Task Fixtures for TriggerEvaluator Tests
# ============================================================================

from tests._shared.mocks import MockTask


@pytest.fixture
def now() -> datetime:
    """Current UTC datetime for consistent testing."""
    return datetime.now(timezone.utc)


@pytest.fixture
def mock_stale_task(now: datetime) -> MockTask:
    """Mock task that is stale (modified 5 days ago)."""
    return MockTask(
        gid="mock-stale-1",
        name="Mock Stale Task",
        modified_at=(now - timedelta(days=5)).isoformat(),
        created_at=(now - timedelta(days=10)).isoformat(),
    )


@pytest.fixture
def mock_fresh_task(now: datetime) -> MockTask:
    """Mock task that is fresh (modified today)."""
    return MockTask(
        gid="mock-fresh-1",
        name="Mock Fresh Task",
        modified_at=now.isoformat(),
        created_at=(now - timedelta(days=2)).isoformat(),
    )


@pytest.fixture
def mock_due_soon_task(now: datetime) -> MockTask:
    """Mock task due in 3 days."""
    return MockTask(
        gid="mock-due-soon-1",
        name="Mock Due Soon Task",
        modified_at=now.isoformat(),
        created_at=(now - timedelta(days=5)).isoformat(),
        due_on=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
    )


@pytest.fixture
def mock_old_open_task(now: datetime) -> MockTask:
    """Mock task created 100 days ago, still open."""
    return MockTask(
        gid="mock-old-1",
        name="Mock Old Open Task",
        modified_at=(now - timedelta(days=50)).isoformat(),
        created_at=(now - timedelta(days=100)).isoformat(),
        completed=False,
    )


@pytest.fixture
def mock_old_completed_task(now: datetime) -> MockTask:
    """Mock task created 100 days ago, completed."""
    return MockTask(
        gid="mock-old-completed-1",
        name="Mock Old Completed Task",
        modified_at=(now - timedelta(days=10)).isoformat(),
        created_at=(now - timedelta(days=100)).isoformat(),
        completed=True,
    )
