"""Part 6: Live API Integration Tests.

Tests SaveSession with real Asana API calls.

Requirements:
- ASANA_ACCESS_TOKEN: Valid Asana Personal Access Token
- ASANA_WORKSPACE_GID: Workspace GID for testing
- ASANA_PROJECT_GID: Project GID for creating test tasks

These tests are skipped if environment variables are not set.

Run with: pytest tests/integration/persistence/ -v -m integration

Note: These tests create real tasks in your Asana workspace.
They attempt to clean up after themselves, but manual cleanup
may be required if tests fail unexpectedly.
"""

from __future__ import annotations

import os

import pytest

# Skip all tests if no API token
pytestmark = [
    pytest.mark.skipif(
        not os.getenv("ASANA_ACCESS_TOKEN"), reason="ASANA_ACCESS_TOKEN not set"
    ),
    pytest.mark.integration,
]


# ---------------------------------------------------------------------------
# Test Stubs (Uncomment when client is available)
# ---------------------------------------------------------------------------

# Note: These tests require the AsanaClient to be implemented with
# a save_session() method that returns a SaveSession instance.
# Once implemented, uncomment and adapt as needed.

"""
from autom8_asana.client import AsanaClient
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence import SaveSession


@pytest.fixture
async def live_client():
    '''Create real AsanaClient.'''
    token = os.getenv("ASANA_ACCESS_TOKEN")
    client = AsanaClient(access_token=token)
    yield client


@pytest.fixture
def test_workspace():
    '''Get test workspace GID from env.'''
    return os.getenv("ASANA_WORKSPACE_GID")


@pytest.fixture
def test_project():
    '''Get test project GID from env.'''
    return os.getenv("ASANA_PROJECT_GID")


@pytest.fixture
async def cleanup_tasks(live_client):
    '''Track tasks created during tests for cleanup.'''
    created_gids = []
    yield created_gids

    # Cleanup after test
    for gid in created_gids:
        try:
            await live_client.tasks.delete_async(gid)
        except Exception:
            pass  # Ignore cleanup errors


class TestLiveAPICreate:
    '''Integration tests for task creation.'''

    async def test_create_single_task(self, live_client, test_project, cleanup_tasks):
        '''Create a real task via SaveSession.'''
        task = Task(
            name="[TEST] SaveSession Create Test",
            projects=[NameGid(gid=test_project)],
        )

        async with live_client.save_session() as session:
            session.track(task)
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 1

        # Track for cleanup
        created_task = result.succeeded[0]
        cleanup_tasks.append(created_task.gid)

        # Verify task has real GID
        assert created_task.gid and not created_task.gid.startswith("temp_")

    async def test_create_with_parent(self, live_client, test_project, cleanup_tasks):
        '''Create parent and child tasks in single commit.'''
        parent = Task(
            gid="temp_parent",
            name="[TEST] Parent Task",
            projects=[NameGid(gid=test_project)],
        )
        child = Task(
            gid="temp_child",
            name="[TEST] Child Task",
            parent=NameGid(gid="temp_parent"),
            projects=[NameGid(gid=test_project)],
        )

        async with live_client.save_session() as session:
            session.track(parent)
            session.track(child)
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 2

        # Track for cleanup
        for task in result.succeeded:
            cleanup_tasks.append(task.gid)

        # Verify child has parent relationship
        assert child.parent is not None


class TestLiveAPIUpdate:
    '''Integration tests for task updates.'''

    async def test_update_task_name(self, live_client, test_project, cleanup_tasks):
        '''Update a real task's name via SaveSession.'''
        # First create a task
        create_task = Task(
            name="[TEST] Update Test - Original",
            projects=[NameGid(gid=test_project)],
        )

        async with live_client.save_session() as session:
            session.track(create_task)
            result = await session.commit_async()

        assert result.success
        created_gid = result.succeeded[0].gid
        cleanup_tasks.append(created_gid)

        # Now update it
        update_task = Task(gid=created_gid, name="[TEST] Update Test - Modified")

        async with live_client.save_session() as session:
            session.track(update_task)
            result = await session.commit_async()

        assert result.success

    async def test_update_multiple_fields(self, live_client, test_project, cleanup_tasks):
        '''Update multiple fields in single commit.'''
        # Create task
        task = Task(
            name="[TEST] Multi-field Update Test",
            notes="Original notes",
            projects=[NameGid(gid=test_project)],
        )

        async with live_client.save_session() as session:
            session.track(task)
            result = await session.commit_async()

        assert result.success
        cleanup_tasks.append(result.succeeded[0].gid)

        # Update multiple fields
        task.name = "[TEST] Multi-field Update Test - Modified"
        task.notes = "Modified notes"

        async with live_client.save_session() as session:
            session.track(task)
            result = await session.commit_async()

        assert result.success


class TestLiveAPIBatch:
    '''Integration tests for batch operations.'''

    async def test_batch_create_3_tasks(self, live_client, test_project, cleanup_tasks):
        '''Create multiple tasks in one commit.'''
        tasks = [
            Task(
                name=f"[TEST] Batch Task {i}",
                projects=[NameGid(gid=test_project)],
            )
            for i in range(3)
        ]

        async with live_client.save_session() as session:
            for task in tasks:
                session.track(task)
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 3

        for task in result.succeeded:
            cleanup_tasks.append(task.gid)

    async def test_mixed_operations(self, live_client, test_project, cleanup_tasks):
        '''Create and update in single commit.'''
        # Create initial task
        existing = Task(
            name="[TEST] Mixed Op - Existing",
            projects=[NameGid(gid=test_project)],
        )

        async with live_client.save_session() as session:
            session.track(existing)
            result = await session.commit_async()

        assert result.success
        cleanup_tasks.append(result.succeeded[0].gid)

        # Now create new and update existing in same commit
        new_task = Task(
            name="[TEST] Mixed Op - New",
            projects=[NameGid(gid=test_project)],
        )
        existing.name = "[TEST] Mixed Op - Existing (Updated)"

        async with live_client.save_session() as session:
            session.track(new_task)
            session.track(existing)
            result = await session.commit_async()

        assert result.success
        assert len(result.succeeded) == 2

        # Track new task for cleanup
        for task in result.succeeded:
            if task.gid not in cleanup_tasks:
                cleanup_tasks.append(task.gid)


class TestLiveAPIDelete:
    '''Integration tests for task deletion.'''

    async def test_delete_task(self, live_client, test_project):
        '''Delete a real task via SaveSession.'''
        # Create task
        task = Task(
            name="[TEST] Delete Test",
            projects=[NameGid(gid=test_project)],
        )

        async with live_client.save_session() as session:
            session.track(task)
            result = await session.commit_async()

        assert result.success
        created_gid = result.succeeded[0].gid

        # Delete it
        delete_task = Task(gid=created_gid)

        async with live_client.save_session() as session:
            session.delete(delete_task)
            result = await session.commit_async()

        assert result.success


class TestLiveAPIErrors:
    '''Integration tests for error handling.'''

    async def test_invalid_gid_error(self, live_client):
        '''Updating non-existent task returns error.'''
        task = Task(gid="invalid_gid_12345", name="Won't work")

        async with live_client.save_session() as session:
            session.track(task)
            task.name = "Modified"
            result = await session.commit_async()

        assert not result.success
        assert len(result.failed) == 1

    async def test_missing_required_field_error(self, live_client, test_project):
        '''Creating task without workspace/project returns error.'''
        # Task without project (should fail)
        task = Task(name="[TEST] No Project Task")

        async with live_client.save_session() as session:
            session.track(task)
            result = await session.commit_async()

        # Asana requires a workspace or project
        assert not result.success
"""


# ---------------------------------------------------------------------------
# Placeholder Tests (Run to verify test infrastructure)
# ---------------------------------------------------------------------------


class TestIntegrationInfrastructure:
    """Tests to verify integration test infrastructure works."""

    def test_environment_variables_accessible(self) -> None:
        """Verify we can read environment variables."""
        token = os.getenv("ASANA_ACCESS_TOKEN")
        # This test only runs if token is set (due to pytestmark)
        assert token is not None

    def test_project_gid_set(self) -> None:
        """Verify project GID is set when token is set."""
        project = os.getenv("ASANA_PROJECT_GID")
        if not project:
            pytest.skip("ASANA_PROJECT_GID not set (optional)")

    def test_workspace_gid_set(self) -> None:
        """Verify workspace GID is set when token is set."""
        workspace = os.getenv("ASANA_WORKSPACE_GID")
        if not workspace:
            pytest.skip("ASANA_WORKSPACE_GID not set (optional)")
