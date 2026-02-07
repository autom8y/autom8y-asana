"""Unit and integration tests for webhook inbound event handler.

Per TDD-GAP-02, Section 10: Tests cover token verification, cache
invalidation, endpoint integration, dispatch protocol, and dispatch
management.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.routes.webhooks import (
    _TASK_ENTRY_TYPES,
    NoOpDispatcher,
    get_dispatcher,
    invalidate_stale_task_cache,
    set_dispatcher,
    verify_webhook_token,
)
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.models.task import Task
from autom8_asana.settings import reset_settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_TOKEN = "test-secret-token-xyz"


@pytest.fixture
def webhook_token():
    """Set WEBHOOK_INBOUND_TOKEN env var for testing."""
    with patch.dict(os.environ, {"WEBHOOK_INBOUND_TOKEN": _TEST_TOKEN}):
        reset_settings()
        yield _TEST_TOKEN
        reset_settings()


@pytest.fixture
def unconfigured_token():
    """Ensure WEBHOOK_INBOUND_TOKEN is not set."""
    env_copy = os.environ.copy()
    env_copy.pop("WEBHOOK_INBOUND_TOKEN", None)
    with patch.dict(os.environ, env_copy, clear=True):
        reset_settings()
        yield
        reset_settings()


@pytest.fixture
def sample_task_payload():
    """Full Asana task JSON equivalent to GET /tasks/{gid}."""
    return {
        "gid": "1234567890",
        "resource_type": "task",
        "name": "Test Task",
        "modified_at": "2026-02-07T15:30:00.000Z",
        "assignee": {"gid": "111", "name": "User"},
        "projects": [{"gid": "222", "name": "Project"}],
        "custom_fields": [],
    }


@pytest.fixture
def mock_cache_provider():
    """Mock CacheProvider for cache invalidation tests."""
    provider = MagicMock()
    provider.get_versioned.return_value = None
    return provider


@pytest.fixture
def test_client(webhook_token):
    """FastAPI TestClient with webhook token configured."""
    from fastapi import FastAPI

    from autom8_asana.api.routes.webhooks import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def test_client_unconfigured(unconfigured_token):
    """FastAPI TestClient without webhook token configured."""
    from fastapi import FastAPI

    from autom8_asana.api.routes.webhooks import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_dispatcher():
    """Reset the module-level dispatcher to NoOpDispatcher after each test."""
    yield
    set_dispatcher(NoOpDispatcher())


# ---------------------------------------------------------------------------
# Token Verification Tests
# ---------------------------------------------------------------------------


class TestVerifyWebhookToken:
    """Tests for the verify_webhook_token dependency function."""

    def test_valid_token_returns_token(self, webhook_token):
        """Valid token should be returned unchanged."""
        result = verify_webhook_token(token=_TEST_TOKEN)
        assert result == _TEST_TOKEN

    def test_missing_token_raises_401(self, webhook_token):
        """Missing token (None) should raise 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(token=None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "MISSING_TOKEN"

    def test_empty_token_raises_401(self, webhook_token):
        """Empty string token should raise 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(token="")
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "MISSING_TOKEN"

    def test_wrong_token_raises_401(self, webhook_token):
        """Incorrect token should raise 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(token="wrong-token")
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "INVALID_TOKEN"

    def test_unconfigured_token_raises_503(self, unconfigured_token):
        """When WEBHOOK_INBOUND_TOKEN is not set, should raise 503."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(token="any-token")
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "WEBHOOK_NOT_CONFIGURED"

    def test_timing_safe_comparison_used(self, webhook_token):
        """Verify hmac.compare_digest is used for comparison."""
        with patch("autom8_asana.api.routes.webhooks.hmac.compare_digest") as mock_cmp:
            mock_cmp.return_value = True
            verify_webhook_token(token=_TEST_TOKEN)
            mock_cmp.assert_called_once_with(_TEST_TOKEN, _TEST_TOKEN)


# ---------------------------------------------------------------------------
# Cache Invalidation Tests
# ---------------------------------------------------------------------------


class TestInvalidateStaleCacheTask:
    """Tests for the invalidate_stale_task_cache function."""

    def test_invalidates_when_inbound_newer(self, mock_cache_provider):
        """Should invalidate when inbound modified_at is newer than cached."""
        cached_entry = CacheEntry(
            key="12345",
            data={"gid": "12345"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 2, 7, 10, 0, 0, tzinfo=UTC),
        )
        mock_cache_provider.get_versioned.return_value = cached_entry

        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=mock_cache_provider,
        )

        assert result is True
        mock_cache_provider.invalidate.assert_called_once_with(
            "12345", _TASK_ENTRY_TYPES
        )

    def test_skips_when_inbound_older(self, mock_cache_provider):
        """Should skip when inbound modified_at is older than cached."""
        cached_entry = CacheEntry(
            key="12345",
            data={"gid": "12345"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 2, 7, 20, 0, 0, tzinfo=UTC),
        )
        mock_cache_provider.get_versioned.return_value = cached_entry

        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=mock_cache_provider,
        )

        assert result is False
        mock_cache_provider.invalidate.assert_not_called()

    def test_skips_when_inbound_equal(self, mock_cache_provider):
        """Should skip when inbound modified_at equals cached version."""
        cached_entry = CacheEntry(
            key="12345",
            data={"gid": "12345"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 2, 7, 15, 30, 0, tzinfo=UTC),
        )
        mock_cache_provider.get_versioned.return_value = cached_entry

        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=mock_cache_provider,
        )

        assert result is False
        mock_cache_provider.invalidate.assert_not_called()

    def test_skips_when_no_cached_entry(self, mock_cache_provider):
        """Should skip when no cached entry exists."""
        mock_cache_provider.get_versioned.return_value = None

        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=mock_cache_provider,
        )

        assert result is False
        mock_cache_provider.invalidate.assert_not_called()

    def test_skips_when_modified_at_none(self, mock_cache_provider):
        """Should skip when inbound modified_at is None."""
        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at=None,
            cache_provider=mock_cache_provider,
        )

        assert result is False
        mock_cache_provider.get_versioned.assert_not_called()

    def test_skips_when_cache_provider_none(self):
        """Should skip when cache_provider is None."""
        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=None,
        )

        assert result is False

    def test_invalidates_correct_entry_types(self, mock_cache_provider):
        """Should invalidate TASK, SUBTASKS, and DETECTION entry types."""
        cached_entry = CacheEntry(
            key="12345",
            data={"gid": "12345"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 2, 7, 10, 0, 0, tzinfo=UTC),
        )
        mock_cache_provider.get_versioned.return_value = cached_entry

        invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=mock_cache_provider,
        )

        call_args = mock_cache_provider.invalidate.call_args
        entry_types = call_args[0][1]
        assert EntryType.TASK in entry_types
        assert EntryType.SUBTASKS in entry_types
        assert EntryType.DETECTION in entry_types
        assert len(entry_types) == 3

    def test_cache_error_does_not_propagate(self, mock_cache_provider):
        """Cache errors should be caught and logged, not propagated."""
        mock_cache_provider.get_versioned.side_effect = ConnectionError("Redis down")

        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=mock_cache_provider,
        )

        assert result is False


# ---------------------------------------------------------------------------
# Endpoint Integration Tests
# ---------------------------------------------------------------------------


class TestReceiveInboundWebhook:
    """Integration tests for the POST /api/v1/webhooks/inbound endpoint."""

    def test_happy_path_returns_200(self, test_client, sample_task_payload):
        """Valid request should return 200 with accepted status."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=sample_task_payload,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_missing_token_returns_401(self, test_client, sample_task_payload):
        """Request without token should return 401."""
        response = test_client.post(
            "/api/v1/webhooks/inbound",
            json=sample_task_payload,
        )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "MISSING_TOKEN"

    def test_wrong_token_returns_401(self, test_client, sample_task_payload):
        """Request with wrong token should return 401."""
        response = test_client.post(
            "/api/v1/webhooks/inbound?token=wrong-token",
            json=sample_task_payload,
        )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "INVALID_TOKEN"

    def test_unconfigured_token_returns_503(
        self, test_client_unconfigured, sample_task_payload
    ):
        """When token is not configured, should return 503."""
        response = test_client_unconfigured.post(
            "/api/v1/webhooks/inbound?token=any-token",
            json=sample_task_payload,
        )

        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "WEBHOOK_NOT_CONFIGURED"

    def test_non_json_body_returns_400(self, test_client):
        """Non-JSON body should return 400."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            content=b"not json",
            headers={"content-type": "text/plain"},
        )

        assert response.status_code == 400
        assert response.json()["error"] == "INVALID_JSON"

    def test_empty_body_returns_200_with_warning(self, test_client):
        """Empty JSON body should return 200 with detail about empty payload."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json={},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        assert "empty" in response.json()["detail"]

    def test_missing_gid_returns_400(self, test_client):
        """JSON without gid field should return 400."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json={"name": "No GID Task"},
        )

        assert response.status_code == 400
        assert response.json()["error"] == "MISSING_GID"

    def test_task_validation_error_returns_400(self, test_client):
        """JSON that fails Task model validation should return 400."""
        # gid is required to be a string. Pydantic v2 with str_strip_whitespace
        # will coerce int->str, so we need a truly invalid scenario.
        # AsanaResource requires gid: str, but pydantic coerces most types.
        # Use a mock to force validation failure.
        with patch(
            "autom8_asana.api.routes.webhooks.Task.model_validate",
            side_effect=ValueError("Validation failed"),
        ):
            response = test_client.post(
                f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
                json={"gid": "12345"},
            )

        assert response.status_code == 400
        assert response.json()["error"] == "INVALID_TASK"

    def test_background_task_enqueued(self, test_client, sample_task_payload):
        """Background task should be added via BackgroundTasks."""
        with patch(
            "autom8_asana.api.routes.webhooks._process_inbound_task"
        ) as mock_process:
            response = test_client.post(
                f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
                json=sample_task_payload,
            )

            assert response.status_code == 200
            # FastAPI TestClient executes background tasks synchronously
            mock_process.assert_called_once()
            call_args = mock_process.call_args
            task_arg = call_args[0][0]
            assert task_arg.gid == "1234567890"

    def test_structured_log_emitted_on_accept(self, test_client, sample_task_payload):
        """webhook_task_received log should be emitted on successful accept."""
        with patch("autom8_asana.api.routes.webhooks.logger") as mock_logger:
            response = test_client.post(
                f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
                json=sample_task_payload,
            )

            assert response.status_code == 200
            # Find the webhook_task_received call
            info_calls = [
                c
                for c in mock_logger.info.call_args_list
                if c[0][0] == "webhook_task_received"
            ]
            assert len(info_calls) == 1
            extra = info_calls[0][1]["extra"]
            assert extra["task_gid"] == "1234567890"
            assert extra["resource_type"] == "task"

    def test_unknown_fields_ignored(self, test_client):
        """Unknown fields in payload should be silently ignored."""
        payload = {
            "gid": "1234567890",
            "resource_type": "task",
            "unknown_field_1": "should be ignored",
            "another_unknown": 42,
        }

        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"


# ---------------------------------------------------------------------------
# Dispatch Protocol Tests
# ---------------------------------------------------------------------------


class TestNoOpDispatcher:
    """Tests for the NoOpDispatcher default implementation."""

    @pytest.mark.asyncio
    async def test_dispatch_logs_task_gid(self):
        """NoOpDispatcher should log the task GID."""
        dispatcher = NoOpDispatcher()
        task = Task.model_validate(
            {"gid": "9876543210", "resource_type": "task", "modified_at": None}
        )

        with patch("autom8_asana.api.routes.webhooks.logger") as mock_logger:
            await dispatcher.dispatch(task)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "webhook_task_dispatched_noop"
            assert call_args[1]["extra"]["task_gid"] == "9876543210"

    @pytest.mark.asyncio
    async def test_dispatch_does_not_raise(self):
        """NoOpDispatcher.dispatch should complete without raising."""
        dispatcher = NoOpDispatcher()
        task = Task.model_validate({"gid": "12345", "resource_type": "task"})

        # Should not raise
        await dispatcher.dispatch(task)


# ---------------------------------------------------------------------------
# Dispatch Management Tests
# ---------------------------------------------------------------------------


class TestSetDispatcher:
    """Tests for set_dispatcher and get_dispatcher module functions."""

    def test_replaces_global_dispatcher(self):
        """set_dispatcher should replace the global dispatcher."""
        custom_dispatcher = MagicMock()
        custom_dispatcher.dispatch = AsyncMock()

        set_dispatcher(custom_dispatcher)

        assert get_dispatcher() is custom_dispatcher

    def test_get_dispatcher_returns_current(self):
        """get_dispatcher should return the current dispatcher."""
        # Default should be NoOpDispatcher
        dispatcher = get_dispatcher()
        assert isinstance(dispatcher, NoOpDispatcher)

    def test_get_dispatcher_after_set_returns_new(self):
        """After set_dispatcher, get_dispatcher returns the new one."""
        original = get_dispatcher()
        new_dispatcher = MagicMock()
        new_dispatcher.dispatch = AsyncMock()

        set_dispatcher(new_dispatcher)

        assert get_dispatcher() is new_dispatcher
        assert get_dispatcher() is not original


# ---------------------------------------------------------------------------
# Background Task Integration Tests
# ---------------------------------------------------------------------------


class TestProcessInboundTask:
    """Tests for the _process_inbound_task background function."""

    @pytest.mark.asyncio
    async def test_calls_cache_invalidation(self, mock_cache_provider):
        """Background task should call invalidate_stale_task_cache."""
        from autom8_asana.api.routes.webhooks import _process_inbound_task

        task = Task.model_validate(
            {
                "gid": "12345",
                "resource_type": "task",
                "modified_at": "2026-02-07T15:30:00.000Z",
            }
        )

        with patch(
            "autom8_asana.api.routes.webhooks.invalidate_stale_task_cache"
        ) as mock_invalidate:
            await _process_inbound_task(task, mock_cache_provider)

            mock_invalidate.assert_called_once_with(
                task_gid="12345",
                inbound_modified_at="2026-02-07T15:30:00.000Z",
                cache_provider=mock_cache_provider,
            )

    @pytest.mark.asyncio
    async def test_calls_dispatcher(self):
        """Background task should call the dispatcher."""
        from autom8_asana.api.routes.webhooks import _process_inbound_task

        task = Task.model_validate({"gid": "12345", "resource_type": "task"})
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch = AsyncMock()
        set_dispatcher(mock_dispatcher)

        await _process_inbound_task(task, None)

        mock_dispatcher.dispatch.assert_awaited_once_with(task)

    @pytest.mark.asyncio
    async def test_dispatch_error_does_not_propagate(self):
        """Dispatch errors should be caught and logged, not raised."""
        from autom8_asana.api.routes.webhooks import _process_inbound_task

        task = Task.model_validate({"gid": "12345", "resource_type": "task"})
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch = AsyncMock(
            side_effect=RuntimeError("Dispatch failed")
        )
        set_dispatcher(mock_dispatcher)

        # Should not raise
        await _process_inbound_task(task, None)
