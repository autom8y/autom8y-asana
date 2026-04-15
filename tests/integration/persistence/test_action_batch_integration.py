"""Integration tests for action batching via SaveSession.

Per TDD-GAP-05 Section 13.2: Full SaveSession flow with batched actions.
These tests use mock clients to verify the integration between SaveSession,
ActionExecutor, and BatchClient without hitting the real Asana API.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client() -> MagicMock:
    """Create a mock AsanaClient with batch and _http attributes."""
    client = MagicMock()

    # Mock HTTP client
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_http._log = None
    client._http = mock_http

    # Mock batch client
    mock_batch = AsyncMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    # Provide _http and _log for BaseClient compatibility
    mock_batch._http = mock_http
    mock_batch._log = None
    client.batch = mock_batch

    # No automation, no cache provider
    client.automation = None
    client._cache_provider = None
    client._log = None
    client._config = MagicMock()
    client._config.automation = None

    return client


def _make_batch_result(success: bool = True, gid: str = "111111") -> BatchResult:
    """Create a BatchResult for testing."""
    if success:
        return BatchResult(status_code=200, body={"data": {"gid": gid}})
    else:
        return BatchResult(
            status_code=500,
            body={"errors": [{"message": "Server error"}]},
        )


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestSaveSessionCommitBatchesActions:
    """Test full SaveSession commit with batched actions."""

    async def test_save_session_commit_batches_actions(self) -> None:
        """Full SaveSession flow: track entity, add 5 tags, commit -> batch used."""
        from autom8_asana.persistence.session import SaveSession

        mock_client = _make_mock_client()

        # Configure batch client to return 5 successful results
        mock_client.batch.execute_async.return_value = [
            _make_batch_result(True, f"{900000 + i}") for i in range(5)
        ]

        async with SaveSession(mock_client) as session:
            task = Task(gid="123456", name="Existing Task")
            # Don't track the task (we only want action operations, not CRUD)

            # Add 5 tags using numeric GIDs
            for i in range(5):
                session.add_tag(task, str(800000 + i))

            result = await session.commit_async()

        # Verify action results
        assert len(result.action_results) == 5
        assert all(r.success for r in result.action_results)

        # Verify batch client was used (not individual HTTP calls for actions)
        mock_client.batch.execute_async.assert_called_once()

    async def test_save_session_commit_mixed_crud_and_batched_actions(self) -> None:
        """CRUD entities + batched actions in single commit -> both execute."""
        from autom8_asana.persistence.session import SaveSession

        mock_client = _make_mock_client()

        # CRUD batch response for update
        crud_batch_result = BatchResult(
            status_code=200,
            body={"data": {"gid": "123456", "name": "Updated Task"}},
        )
        # Action batch response for tags
        tag_batch_results = [_make_batch_result(True, f"{900000 + i}") for i in range(3)]

        # Configure CRUD batch executor (used by SavePipeline)
        # The SavePipeline uses BatchExecutor which calls batch.execute_async
        mock_client.batch.execute_async.side_effect = [
            [crud_batch_result],  # CRUD phase
            tag_batch_results,  # Actions phase
        ]

        async with SaveSession(mock_client) as session:
            task = Task(gid="123456", name="Original Task")
            session.track(task)
            task.name = "Updated Task"

            # Also add some tags using numeric GIDs
            for i in range(3):
                session.add_tag(task, str(800000 + i))

            result = await session.commit_async()

        # CRUD should have processed (1 update)
        assert len(result.succeeded) == 1

        # Actions should have processed (3 tags via batch)
        assert len(result.action_results) == 3
        assert all(r.success for r in result.action_results)

        # batch.execute_async called at least once for CRUD and once for actions
        assert mock_client.batch.execute_async.call_count >= 2

    async def test_save_session_action_fallback_to_sequential(self) -> None:
        """When batch fails for actions, falls back to sequential HTTP calls."""
        from autom8_asana.persistence.session import SaveSession

        mock_client = _make_mock_client()

        # Make batch raise on action execution
        mock_client.batch.execute_async.side_effect = ConnectionError("Network error")

        async with SaveSession(mock_client) as session:
            task = Task(gid="123456", name="Test Task")

            # Add 3 tags (will try batch, then fall back)
            for i in range(3):
                session.add_tag(task, str(800000 + i))

            result = await session.commit_async()

        # Actions should still succeed via sequential fallback
        assert len(result.action_results) == 3
        assert all(r.success for r in result.action_results)

        # HTTP request should have been called for sequential fallback
        assert mock_client._http.request.call_count == 3
