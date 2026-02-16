"""Unit tests for GID mapping push to autom8_data.

Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: Tests for the push function that
sends GID mappings to autom8_data after cache warmer rebuilds.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from autom8_asana.services.gid_lookup import GidLookupIndex
from autom8_asana.services.gid_push import (
    GID_PUSH_ENABLED_ENV_VAR,
    _is_push_enabled,
    extract_mappings_from_index,
    push_gid_mappings_to_data_service,
)

# ============================================================================
# Tests for extract_mappings_from_index
# ============================================================================


class TestExtractMappingsFromIndex:
    """Tests for canonical_key parsing and mapping extraction."""

    def test_extracts_valid_pv1_entries(self) -> None:
        """Standard pv1:phone:vertical entries are extracted."""
        index = GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv1:+15559876543:chiropractic": "2222222222222222",
            },
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert len(mappings) == 2
        assert {
            "phone": "+15551234567",
            "vertical": "dental",
            "task_gid": "1111111111111111",
        } in mappings
        assert {
            "phone": "+15559876543",
            "vertical": "chiropractic",
            "task_gid": "2222222222222222",
        } in mappings

    def test_skips_non_pv1_entries(self) -> None:
        """Entries not starting with 'pv1' are skipped."""
        index = GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv2:+15559876543:chiropractic": "2222222222222222",
                "other:format": "3333333333333333",
            },
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert len(mappings) == 1
        assert mappings[0]["phone"] == "+15551234567"

    def test_skips_entries_with_wrong_part_count(self) -> None:
        """Entries with != 3 colon-separated parts are skipped."""
        index = GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv1:+15559876543": "2222222222222222",  # Only 2 parts
                "pv1:a:b:c": "3333333333333333",  # 4 parts
            },
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert len(mappings) == 1
        assert mappings[0]["phone"] == "+15551234567"

    def test_empty_index_returns_empty_list(self) -> None:
        """Empty index produces no mappings."""
        index = GidLookupIndex(
            lookup_dict={},
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert mappings == []


# ============================================================================
# Tests for _is_push_enabled
# ============================================================================


class TestIsPushEnabled:
    """Tests for feature flag check."""

    def test_enabled_by_default(self) -> None:
        """Push is enabled when env var is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert _is_push_enabled() is True

    def test_enabled_when_set_to_true(self) -> None:
        """Push is enabled when env var is 'true'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "true"}):
            assert _is_push_enabled() is True

    def test_disabled_when_set_to_false(self) -> None:
        """Push is disabled when env var is 'false'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "false"}):
            assert _is_push_enabled() is False

    def test_disabled_when_set_to_zero(self) -> None:
        """Push is disabled when env var is '0'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "0"}):
            assert _is_push_enabled() is False

    def test_disabled_when_set_to_no(self) -> None:
        """Push is disabled when env var is 'no'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "no"}):
            assert _is_push_enabled() is False

    def test_enabled_when_set_to_arbitrary_string(self) -> None:
        """Push is enabled when env var is any non-falsy value."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "yes"}):
            assert _is_push_enabled() is True


# ============================================================================
# Tests for push_gid_mappings_to_data_service
# ============================================================================


class TestPushGidMappingsToDataService:
    """Tests for the async push function."""

    @pytest.fixture
    def sample_index(self) -> GidLookupIndex:
        """Create a sample GidLookupIndex with valid entries."""
        return GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv1:+15559876543:chiropractic": "2222222222222222",
            },
            created_at=datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC),
        )

    @pytest.fixture
    def empty_index(self) -> GidLookupIndex:
        """Create an empty GidLookupIndex."""
        return GidLookupIndex(
            lookup_dict={},
            created_at=datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_push_disabled_returns_false(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Returns False when push is disabled via feature flag."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "false"}):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_skips_when_no_data_service_url(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Returns False when AUTOM8_DATA_URL is not configured."""
        with patch.dict("os.environ", {}, clear=True):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_skips_when_no_auth_token(self, sample_index: GidLookupIndex) -> None:
        """Returns False when auth token is not available."""
        with patch.dict(
            "os.environ", {"AUTOM8_DATA_URL": "http://localhost:8000"}, clear=True
        ):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_index_returns_true(self, empty_index: GidLookupIndex) -> None:
        """Returns True (no-op success) when index has no mappings."""
        with patch.dict("os.environ", {"AUTOM8_DATA_URL": "http://localhost:8000"}):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=empty_index,
                auth_token="test-token",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_successful_push(self, sample_index: GidLookupIndex) -> None:
        """Returns True and sends correct payload on HTTP 200."""
        mock_response = httpx.Response(
            status_code=200,
            json={"accepted": 2, "replaced": 0, "meta": {"request_id": "abc"}},
        )

        with patch(
            "autom8_asana.services.gid_push.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is True

        # Verify the POST was called with correct URL and payload
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args.args[0] == "http://localhost:8000/api/v1/gid-mappings/sync"

        payload = call_args.kwargs["json"]
        assert payload["project_gid"] == "1201081073731555"
        assert payload["entry_count"] == 2
        assert payload["source_timestamp"] == "2026-02-16T12:00:00+00:00"
        assert len(payload["mappings"]) == 2

        # Verify auth header
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_payload_mapping_shape(self, sample_index: GidLookupIndex) -> None:
        """Each mapping in the payload has phone, vertical, task_gid keys."""
        mock_response = httpx.Response(
            status_code=200,
            json={"accepted": 2, "replaced": 0},
        )

        captured_payload: dict | None = None

        async def capture_post(
            url: str, *, json: dict, headers: dict
        ) -> httpx.Response:
            nonlocal captured_payload
            captured_payload = json
            return mock_response

        with patch(
            "autom8_asana.services.gid_push.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = capture_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert captured_payload is not None
        for mapping in captured_payload["mappings"]:
            assert "phone" in mapping
            assert "vertical" in mapping
            assert "task_gid" in mapping

    @pytest.mark.asyncio
    async def test_http_error_returns_false(self, sample_index: GidLookupIndex) -> None:
        """Returns False on HTTP 500 error (non-blocking)."""
        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
        )

        with patch(
            "autom8_asana.services.gid_push.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, sample_index: GidLookupIndex) -> None:
        """Returns False on HTTP timeout (non-blocking)."""
        with patch(
            "autom8_asana.services.gid_push.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ReadTimeout("timed out")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_false(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Returns False on unexpected exceptions (non-blocking)."""
        with patch(
            "autom8_asana.services.gid_push.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = RuntimeError("unexpected")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_url_override(self, sample_index: GidLookupIndex) -> None:
        """data_service_url parameter overrides environment variable."""
        mock_response = httpx.Response(status_code=200, json={"accepted": 2})

        with patch(
            "autom8_asana.services.gid_push.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="https://custom-url.example.com",
                auth_token="test-token",
            )

        call_args = mock_client.post.call_args
        assert "custom-url.example.com" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_trailing_slash_in_url_handled(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Trailing slash in base URL does not cause double-slash."""
        mock_response = httpx.Response(status_code=200, json={"accepted": 2})

        with patch(
            "autom8_asana.services.gid_push.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            await push_gid_mappings_to_data_service(
                project_gid="test-gid",
                index=sample_index,
                data_service_url="http://localhost:8000/",
                auth_token="test-token",
            )

        call_args = mock_client.post.call_args
        url = call_args.args[0]
        assert "//" not in url.replace("http://", "")
