"""Unit tests for AsanaResponseHandler.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-004: Tests Asana-specific response
unwrapping and error parsing.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from autom8_asana.transport.response_handler import AsanaResponseHandler


def _make_mock_response(
    status_code: int,
    json_data: dict | None = None,
    text: str = "",
    headers: dict | None = None,
) -> MagicMock:
    """Create a mock httpx.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.text = text or (json.dumps(json_data) if json_data else "")

    if json_data is not None:
        response.json.return_value = json_data
    else:
        response.json.side_effect = json.JSONDecodeError("", "", 0)

    return response


class TestUnwrapResponse:
    """Test response unwrapping."""

    def test_unwraps_data_envelope(self):
        """Extracts data from {"data": ...} envelope."""
        response = _make_mock_response(
            200,
            json_data={"data": {"gid": "123", "name": "Test Task"}},
        )
        result = AsanaResponseHandler.unwrap_response(response)
        assert result == {"gid": "123", "name": "Test Task"}

    def test_returns_non_wrapped_response(self):
        """Returns response as-is if no data envelope."""
        response = _make_mock_response(
            200,
            json_data={"gid": "123", "name": "Test Task"},
        )
        result = AsanaResponseHandler.unwrap_response(response)
        assert result == {"gid": "123", "name": "Test Task"}

    def test_handles_list_data(self):
        """Handles list data in envelope."""
        response = _make_mock_response(
            200,
            json_data={"data": [{"gid": "1"}, {"gid": "2"}]},
        )
        result = AsanaResponseHandler.unwrap_response(response)
        assert result == [{"gid": "1"}, {"gid": "2"}]

    def test_raises_on_error_status(self):
        """Raises AsanaError on 4xx/5xx status codes."""
        response = _make_mock_response(
            404,
            json_data={"errors": [{"message": "Not Found"}]},
            headers={"X-Request-Id": "abc123"},
        )
        with pytest.raises(NotFoundError) as exc_info:
            AsanaResponseHandler.unwrap_response(response)
        assert "Not Found" in str(exc_info.value)

    def test_raises_on_json_decode_error(self):
        """Raises AsanaError on invalid JSON."""
        response = MagicMock()
        response.status_code = 200
        response.headers = {"X-Request-Id": "abc123"}
        response.text = "not valid json"
        response.json.side_effect = json.JSONDecodeError("", "", 0)

        with pytest.raises(AsanaError) as exc_info:
            AsanaResponseHandler.unwrap_response(response)
        assert "Invalid JSON response" in str(exc_info.value)
        assert "abc123" in str(exc_info.value)

    def test_includes_body_snippet_on_json_error(self):
        """Includes body snippet in JSON decode error."""
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.text = "<!DOCTYPE html><html>Error Page</html>"
        response.json.side_effect = json.JSONDecodeError("", "", 0)

        with pytest.raises(AsanaError) as exc_info:
            AsanaResponseHandler.unwrap_response(response)
        assert "<!DOCTYPE html>" in str(exc_info.value)


class TestUnwrapPaginatedResponse:
    """Test paginated response unwrapping."""

    def test_extracts_data_list(self):
        """Extracts data list from paginated response."""
        response = _make_mock_response(
            200,
            json_data={
                "data": [{"gid": "1"}, {"gid": "2"}],
                "next_page": None,
            },
        )
        data, next_offset = AsanaResponseHandler.unwrap_paginated_response(response)
        assert data == [{"gid": "1"}, {"gid": "2"}]
        assert next_offset is None

    def test_extracts_next_offset(self):
        """Extracts next_offset from next_page."""
        response = _make_mock_response(
            200,
            json_data={
                "data": [{"gid": "1"}],
                "next_page": {
                    "offset": "eyJvZmZzZXQiOjEwfQ==",
                    "path": "/tasks",
                    "uri": "https://api.asana.com/tasks?offset=xxx",
                },
            },
        )
        data, next_offset = AsanaResponseHandler.unwrap_paginated_response(response)
        assert data == [{"gid": "1"}]
        assert next_offset == "eyJvZmZzZXQiOjEwfQ=="

    def test_returns_empty_list_for_no_data(self):
        """Returns empty list when no data key."""
        response = _make_mock_response(200, json_data={})
        data, next_offset = AsanaResponseHandler.unwrap_paginated_response(response)
        assert data == []
        assert next_offset is None

    def test_raises_on_error_status(self):
        """Raises AsanaError on 4xx/5xx status codes."""
        response = _make_mock_response(
            500,
            json_data={"errors": [{"message": "Internal Server Error"}]},
        )
        with pytest.raises(ServerError):
            AsanaResponseHandler.unwrap_paginated_response(response)


class TestParseError:
    """Test error parsing."""

    def test_parses_rate_limit_error(self):
        """Parses 429 as RateLimitError."""
        response = _make_mock_response(
            429,
            json_data={"errors": [{"message": "Rate limit exceeded"}]},
            headers={"Retry-After": "30"},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert isinstance(error, RateLimitError)
        assert error.retry_after == 30

    def test_parses_rate_limit_without_retry_after(self):
        """Parses 429 without Retry-After header."""
        response = _make_mock_response(
            429,
            json_data={"errors": [{"message": "Rate limit exceeded"}]},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert isinstance(error, RateLimitError)
        assert error.retry_after is None

    def test_parses_server_error(self):
        """Parses 5xx as ServerError."""
        for status in [500, 502, 503, 504]:
            response = _make_mock_response(
                status,
                json_data={"errors": [{"message": "Server error"}]},
            )
            error = AsanaResponseHandler.parse_error(response)
            assert isinstance(error, ServerError), f"Failed for status {status}"

    def test_parses_authentication_error(self):
        """Parses 401 as AuthenticationError."""
        response = _make_mock_response(
            401,
            json_data={"errors": [{"message": "Not authorized"}]},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert isinstance(error, AuthenticationError)

    def test_parses_forbidden_error(self):
        """Parses 403 as ForbiddenError."""
        response = _make_mock_response(
            403,
            json_data={"errors": [{"message": "Forbidden"}]},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert isinstance(error, ForbiddenError)

    def test_parses_not_found_error(self):
        """Parses 404 as NotFoundError."""
        response = _make_mock_response(
            404,
            json_data={"errors": [{"message": "Not found"}]},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert isinstance(error, NotFoundError)

    def test_parses_generic_client_error(self):
        """Parses unknown 4xx as AsanaError."""
        response = _make_mock_response(
            418,  # I'm a teapot
            json_data={"errors": [{"message": "I'm a teapot"}]},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert isinstance(error, AsanaError)
        assert not isinstance(error, (RateLimitError, ServerError))

    def test_includes_request_id_in_rate_limit_message(self):
        """Includes X-Request-Id in rate limit error message."""
        response = _make_mock_response(
            429,
            json_data={"errors": [{"message": "Rate limited"}]},
            headers={"X-Request-Id": "req-abc123", "Retry-After": "60"},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert "req-abc123" in str(error)

    def test_handles_invalid_retry_after(self):
        """Handles non-numeric Retry-After header."""
        response = _make_mock_response(
            429,
            json_data={"errors": [{"message": "Rate limited"}]},
            headers={"Retry-After": "invalid"},
        )
        error = AsanaResponseHandler.parse_error(response)
        assert isinstance(error, RateLimitError)
        assert error.retry_after is None
