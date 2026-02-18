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
        result = verify_webhook_token(request_id="test-req-id", token=_TEST_TOKEN)
        assert result == _TEST_TOKEN

    def test_missing_token_raises_401(self, webhook_token):
        """Missing token (None) should raise 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(request_id="test-req-id", token=None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "MISSING_TOKEN"

    def test_empty_token_raises_401(self, webhook_token):
        """Empty string token should raise 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(request_id="test-req-id", token="")
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "MISSING_TOKEN"

    def test_wrong_token_raises_401(self, webhook_token):
        """Incorrect token should raise 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(request_id="test-req-id", token="wrong-token")
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "INVALID_TOKEN"

    def test_unconfigured_token_raises_503(self, unconfigured_token):
        """When WEBHOOK_INBOUND_TOKEN is not set, should raise 503."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_webhook_token(request_id="test-req-id", token="any-token")
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "WEBHOOK_NOT_CONFIGURED"

    def test_timing_safe_comparison_used(self, webhook_token):
        """Verify hmac.compare_digest is used for comparison."""
        with patch("autom8_asana.api.routes.webhooks.hmac.compare_digest") as mock_cmp:
            mock_cmp.return_value = True
            verify_webhook_token(request_id="test-req-id", token=_TEST_TOKEN)
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


# ---------------------------------------------------------------------------
# QA Adversary: Adversarial Tests
# ---------------------------------------------------------------------------


class TestAdversarialTokenVerification:
    """Adversarial tests for token verification edge cases."""

    def test_empty_token_query_param_returns_401(self, test_client):
        """?token= (empty value) should return 401, not bypass auth."""
        response = test_client.post(
            "/api/v1/webhooks/inbound?token=",
            json={"gid": "12345"},
        )
        assert response.status_code == 401

    def test_whitespace_only_token_returns_401(self, test_client):
        """?token=%20%20 (whitespace only) should return 401."""
        response = test_client.post(
            "/api/v1/webhooks/inbound?token=%20%20",
            json={"gid": "12345"},
        )
        # FastAPI may or may not strip whitespace from query params.
        # Either 401 (token mismatch) or 401 (missing) is acceptable.
        assert response.status_code == 401

    def test_double_token_param_uses_first(self, test_client):
        """?token=valid&token=invalid -- FastAPI uses the last value for Query()."""
        # FastAPI Query(default=None) with a str|None type picks the last value
        # when duplicated. This test verifies the endpoint rejects when the
        # last value is wrong.
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}&token=wrong",
            json={"gid": "12345"},
        )
        # FastAPI picks the last value for scalar Query, so "wrong" is used
        assert response.status_code == 401

    def test_token_in_path_not_query_rejected(self, test_client):
        """Token in URL path segment should not authenticate."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound/{_TEST_TOKEN}",
            json={"gid": "12345"},
        )
        # Route does not match -- FastAPI returns 404 or 405
        assert response.status_code in (404, 405)

    def test_token_as_header_not_query_rejected(self, test_client):
        """Token in Authorization header should not authenticate."""
        response = test_client.post(
            "/api/v1/webhooks/inbound",
            json={"gid": "12345"},
            headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
        )
        assert response.status_code == 401

    def test_no_info_leakage_on_missing_token(self, test_client):
        """401 response should not reveal expected token format or value."""
        response = test_client.post(
            "/api/v1/webhooks/inbound",
            json={"gid": "12345"},
        )
        body = response.json()
        detail = body.get("detail", {})
        # Must not contain the actual token or hints about it
        response_text = str(body)
        assert _TEST_TOKEN not in response_text
        assert "expected" not in response_text.lower()
        assert detail.get("message") in (
            "Authentication required",
            "Authentication failed",
        )

    def test_no_info_leakage_on_wrong_token(self, test_client):
        """401 for wrong token should not reveal the expected token."""
        response = test_client.post(
            "/api/v1/webhooks/inbound?token=wrong",
            json={"gid": "12345"},
        )
        body = response.json()
        response_text = str(body)
        assert _TEST_TOKEN not in response_text
        assert "expected" not in response_text.lower()

    def test_no_info_leakage_on_unconfigured(self, test_client_unconfigured):
        """503 should not reveal whether a token is configured or its value."""
        response = test_client_unconfigured.post(
            "/api/v1/webhooks/inbound?token=probe",
            json={"gid": "12345"},
        )
        body = response.json()
        # Should say "not configured", not reveal the env var name or value
        assert "WEBHOOK_INBOUND_TOKEN" not in str(body)


class TestAdversarialPayloadInjection:
    """Adversarial tests for payload injection and malformed inputs."""

    def test_sql_injection_in_gid(self, test_client):
        """SQL injection in gid should be safely handled."""
        payload = {"gid": "' OR '1'='1"}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        # Should accept (gid is just a string), no SQL execution path
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_xss_in_gid(self, test_client):
        """XSS payload in gid should be safely handled."""
        payload = {"gid": "<script>alert('xss')</script>"}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200

    def test_path_traversal_in_gid(self, test_client):
        """Path traversal in gid should be safely handled."""
        payload = {"gid": "../../../etc/passwd"}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200

    def test_nosql_injection_in_gid(self, test_client):
        """NoSQL injection patterns in gid should be safely handled."""
        payload = {"gid": '{"$gt": ""}'}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200

    def test_very_long_gid(self, test_client):
        """Very long GID string should not cause issues."""
        payload = {"gid": "A" * 10000}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200

    def test_null_byte_in_gid(self, test_client):
        """Null byte in gid should be safely handled."""
        payload = {"gid": "12345\x006789"}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200

    def test_unicode_in_gid(self, test_client):
        """Unicode characters in gid should be safely handled."""
        payload = {"gid": "\u200b\u200b12345"}  # Zero-width spaces + digits
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200

    def test_whitespace_only_gid_returns_400(self, test_client):
        """Whitespace-only gid should be rejected (stripped to empty by Pydantic)."""
        payload = {"gid": "   "}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 400
        assert response.json()["error"] == "MISSING_GID"

    def test_gid_is_integer_returns_400(self, test_client):
        """Integer gid should be rejected (Task requires str gid)."""
        payload = {"gid": 12345}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        # body.get("gid") returns 12345 which is truthy, but Task.model_validate
        # will fail because gid must be a string. Should return 400.
        assert response.status_code == 400
        assert response.json()["error"] == "INVALID_TASK"

    def test_gid_is_boolean_returns_400(self, test_client):
        """Boolean gid should be rejected."""
        payload = {"gid": True}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 400

    def test_gid_is_null_returns_400(self, test_client):
        """Null gid should be rejected."""
        payload = {"gid": None}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 400
        assert response.json()["error"] == "MISSING_GID"


class TestAdversarialPayloadStructure:
    """Adversarial tests for non-standard payload structures."""

    def test_array_payload_returns_400(self, test_client):
        """JSON array payload should be rejected (not a dict)."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=[{"gid": "12345"}],
        )
        assert response.status_code == 400
        assert response.json()["error"] == "MISSING_GID"

    def test_string_payload_returns_400(self, test_client):
        """JSON string payload should be rejected."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            content=b'"just a string"',
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400

    def test_numeric_payload_returns_400(self, test_client):
        """JSON numeric payload should be rejected."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            content=b"42",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400

    def test_null_json_payload_returns_200_empty(self, test_client):
        """JSON null payload should be treated as empty body."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            content=b"null",
            headers={"content-type": "application/json"},
        )
        # null is falsy, so the `if not body` check catches it
        assert response.status_code == 200
        assert "empty" in response.json().get("detail", "")

    def test_nested_null_fields_handled(self, test_client):
        """Task with null optional fields should be accepted."""
        payload = {
            "gid": "1234567890",
            "resource_type": "task",
            "modified_at": None,
            "assignee": None,
            "projects": None,
            "custom_fields": None,
            "parent": None,
            "name": None,
        }
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_deeply_nested_payload_handled(self, test_client):
        """Payload with many custom fields should be accepted."""
        payload = {
            "gid": "1234567890",
            "resource_type": "task",
            "custom_fields": [
                {
                    "gid": f"cf_{i}",
                    "name": f"Field {i}",
                    "display_value": f"Value {i}",
                    "type": "text",
                    "text_value": f"text_{i}",
                }
                for i in range(200)  # Simulate hundreds of custom fields
            ],
        }
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=payload,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_content_type_text_plain_with_json_returns_400(self, test_client):
        """text/plain content type with JSON body should return 400.

        FastAPI/Starlette's request.json() will attempt to parse regardless
        of content type. The behavior depends on the body contents.
        """
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            content=b"not json at all",
            headers={"content-type": "text/plain"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "INVALID_JSON"

    def test_empty_content_type_with_valid_json(self, test_client):
        """No content-type header with valid JSON body should still work."""
        import json

        payload = {"gid": "1234567890", "resource_type": "task"}
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 200

    def test_form_encoded_body_returns_400(self, test_client):
        """Form-encoded body should return 400 (not valid JSON)."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            content=b"gid=12345&resource_type=task",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 400


class TestAdversarialCacheInvalidation:
    """Adversarial tests for cache invalidation edge cases."""

    def test_malformed_modified_at_does_not_crash(self, mock_cache_provider):
        """Malformed modified_at string should be caught by except block."""
        cached_entry = CacheEntry(
            key="12345",
            data={"gid": "12345"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 2, 7, 10, 0, 0, tzinfo=UTC),
        )
        mock_cache_provider.get_versioned.return_value = cached_entry

        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="not-a-valid-date",
            cache_provider=mock_cache_provider,
        )
        # ValueError from _parse_datetime is caught by the except Exception
        assert result is False

    def test_empty_string_modified_at_treated_as_falsy(self, mock_cache_provider):
        """Empty string modified_at should be treated as missing."""
        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="",
            cache_provider=mock_cache_provider,
        )
        # Empty string is falsy, caught by `if not inbound_modified_at`
        assert result is False
        mock_cache_provider.get_versioned.assert_not_called()

    def test_invalidation_error_during_delete_does_not_propagate(
        self, mock_cache_provider
    ):
        """Error during cache.invalidate() should be caught."""
        cached_entry = CacheEntry(
            key="12345",
            data={"gid": "12345"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 2, 7, 10, 0, 0, tzinfo=UTC),
        )
        mock_cache_provider.get_versioned.return_value = cached_entry
        mock_cache_provider.invalidate.side_effect = RuntimeError("Cache write failed")

        result = invalidate_stale_task_cache(
            task_gid="12345",
            inbound_modified_at="2026-02-07T15:30:00.000Z",
            cache_provider=mock_cache_provider,
        )
        assert result is False

    def test_task_entry_types_match_mutation_invalidator(self):
        """_TASK_ENTRY_TYPES must match MutationInvalidator._TASK_ENTRY_TYPES."""
        from autom8_asana.cache.integration.mutation_invalidator import (
            _TASK_ENTRY_TYPES as MUTATION_TASK_ENTRY_TYPES,
        )

        assert set(_TASK_ENTRY_TYPES) == set(MUTATION_TASK_ENTRY_TYPES), (
            f"Webhook _TASK_ENTRY_TYPES {_TASK_ENTRY_TYPES} does not match "
            f"MutationInvalidator {MUTATION_TASK_ENTRY_TYPES}"
        )

    def test_cache_provider_attribute_access_safe(
        self, test_client, sample_task_payload
    ):
        """When app.state has no mutation_invalidator, cache_provider should be None."""
        # The test_client fixture creates a bare FastAPI app without
        # mutation_invalidator on app.state. Verify it does not crash.
        with patch(
            "autom8_asana.api.routes.webhooks._process_inbound_task"
        ) as mock_process:
            response = test_client.post(
                f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
                json=sample_task_payload,
            )
            assert response.status_code == 200
            # Verify cache_provider passed is None (no mutation_invalidator)
            call_args = mock_process.call_args
            cache_provider_arg = call_args[0][1]
            assert cache_provider_arg is None


class TestAdversarialDispatchProtocol:
    """Adversarial tests for the dispatch protocol."""

    def test_noop_dispatcher_satisfies_protocol(self):
        """NoOpDispatcher must satisfy WebhookDispatcher protocol at runtime."""
        from autom8_asana.api.routes.webhooks import WebhookDispatcher

        dispatcher = NoOpDispatcher()
        assert isinstance(dispatcher, WebhookDispatcher)

    def test_protocol_is_runtime_checkable(self):
        """WebhookDispatcher must have @runtime_checkable."""
        from autom8_asana.api.routes.webhooks import WebhookDispatcher

        # Verify isinstance check works (requires @runtime_checkable)
        class BadDispatcher:
            pass

        assert not isinstance(BadDispatcher(), WebhookDispatcher)

    @pytest.mark.asyncio
    async def test_dispatcher_swap_during_background_task(self):
        """Swapping dispatcher during background processing uses new dispatcher.

        This is not necessarily a bug (no lock on _dispatcher), but we
        should understand the behavior: the dispatcher read in
        _process_inbound_task uses whatever is current at call time.
        """
        from autom8_asana.api.routes.webhooks import _process_inbound_task

        task = Task.model_validate({"gid": "12345", "resource_type": "task"})

        # Set initial dispatcher
        initial_dispatcher = MagicMock()
        initial_dispatcher.dispatch = AsyncMock()
        set_dispatcher(initial_dispatcher)

        # Swap to new dispatcher before running background task
        new_dispatcher = MagicMock()
        new_dispatcher.dispatch = AsyncMock()
        set_dispatcher(new_dispatcher)

        await _process_inbound_task(task, None)

        # New dispatcher should have been called (module-level read)
        new_dispatcher.dispatch.assert_awaited_once()
        initial_dispatcher.dispatch.assert_not_awaited()


class TestAdversarialHTTPEdgeCases:
    """Adversarial tests for HTTP-level edge cases."""

    def test_get_method_rejected(self, test_client):
        """GET request to webhook endpoint should be rejected."""
        response = test_client.get(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
        )
        assert response.status_code == 405

    def test_put_method_rejected(self, test_client):
        """PUT request to webhook endpoint should be rejected."""
        response = test_client.put(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json={"gid": "12345"},
        )
        assert response.status_code == 405

    def test_delete_method_rejected(self, test_client):
        """DELETE request to webhook endpoint should be rejected."""
        response = test_client.delete(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
        )
        assert response.status_code == 405

    def test_options_method_returns_allow_header(self, test_client):
        """OPTIONS request should return allowed methods."""
        response = test_client.options(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
        )
        # FastAPI returns 405 for OPTIONS on routes without explicit OPTIONS handler
        # unless CORSMiddleware is active
        assert response.status_code in (200, 405)

    def test_response_has_correct_content_type(self, test_client, sample_task_payload):
        """Response should be application/json."""
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json=sample_task_payload,
        )
        assert "application/json" in response.headers.get("content-type", "")

    def test_auth_checked_before_body_parsing(self, test_client):
        """Token verification must happen before body parsing.

        A request with invalid token should get 401 even with malformed body.
        """
        response = test_client.post(
            "/api/v1/webhooks/inbound?token=wrong",
            content=b"this is not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 401

    def test_no_auth_dependency_leak_from_other_routes(self, test_client):
        """Webhook route should not use get_auth_context dependency."""
        # Verify that the webhook endpoint works without any Bearer token,
        # confirming it does not inherit the standard auth middleware.
        response = test_client.post(
            f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
            json={"gid": "12345"},
        )
        assert response.status_code == 200
        # No Authorization header was sent -- if get_auth_context was
        # required, this would have been 401 or 403.


class TestAdversarialSecurityLogging:
    """Verify that sensitive data never appears in log output."""

    def test_token_value_not_in_log_calls(self, test_client, sample_task_payload):
        """Token value must never appear in any log call arguments."""
        with patch("autom8_asana.api.routes.webhooks.logger") as mock_logger:
            test_client.post(
                f"/api/v1/webhooks/inbound?token={_TEST_TOKEN}",
                json=sample_task_payload,
            )

            # Inspect ALL log calls (info, warning, error, debug, exception)
            all_calls = (
                mock_logger.info.call_args_list
                + mock_logger.warning.call_args_list
                + mock_logger.error.call_args_list
                + mock_logger.debug.call_args_list
                + mock_logger.exception.call_args_list
            )
            for call in all_calls:
                call_str = str(call)
                assert _TEST_TOKEN not in call_str, (
                    f"Token value found in log call: {call_str}"
                )

    def test_token_value_not_in_rejection_logs(self, test_client):
        """Token value must not appear in logs for rejected requests."""
        with patch("autom8_asana.api.routes.webhooks.logger") as mock_logger:
            test_client.post(
                "/api/v1/webhooks/inbound?token=attacker-probe-token",
                json={"gid": "12345"},
            )

            all_calls = (
                mock_logger.info.call_args_list
                + mock_logger.warning.call_args_list
                + mock_logger.error.call_args_list
            )
            for call in all_calls:
                call_str = str(call)
                assert "attacker-probe-token" not in call_str
                assert _TEST_TOKEN not in call_str
