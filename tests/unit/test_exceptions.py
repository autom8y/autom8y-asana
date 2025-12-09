"""Tests for exception hierarchy and from_response factory."""

from unittest.mock import MagicMock

import pytest

from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    ForbiddenError,
    GoneError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SyncInAsyncContextError,
)


class TestAsanaError:
    """Tests for base AsanaError."""

    def test_basic_creation(self) -> None:
        """Test basic exception creation."""
        error = AsanaError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.status_code is None
        assert error.response is None
        assert error.errors == []

    def test_creation_with_all_fields(self) -> None:
        """Test exception creation with all fields populated."""
        mock_response = MagicMock()
        error = AsanaError(
            "API error",
            status_code=400,
            response=mock_response,
            errors=[{"message": "Invalid field"}],
        )
        assert error.message == "API error"
        assert error.status_code == 400
        assert error.response is mock_response
        assert error.errors == [{"message": "Invalid field"}]


class TestFromResponse:
    """Tests for AsanaError.from_response factory method."""

    def test_from_response_401(self) -> None:
        """Test 401 returns AuthenticationError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "errors": [{"message": "Invalid token"}]
        }

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, AuthenticationError)
        assert error.status_code == 401
        assert "Invalid token" in error.message

    def test_from_response_403(self) -> None:
        """Test 403 returns ForbiddenError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "errors": [{"message": "Access denied"}]
        }

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, ForbiddenError)
        assert error.status_code == 403

    def test_from_response_404(self) -> None:
        """Test 404 returns NotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "errors": [{"message": "Task not found"}]
        }

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, NotFoundError)
        assert error.status_code == 404

    def test_from_response_410(self) -> None:
        """Test 410 returns GoneError."""
        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_response.json.return_value = {
            "errors": [{"message": "Resource deleted"}]
        }

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, GoneError)
        assert error.status_code == 410

    def test_from_response_429(self) -> None:
        """Test 429 returns RateLimitError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "errors": [{"message": "Rate limit exceeded"}]
        }

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, RateLimitError)
        assert error.status_code == 429

    def test_from_response_500(self) -> None:
        """Test 500 returns ServerError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "errors": [{"message": "Internal server error"}]
        }

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_from_response_unknown_status(self) -> None:
        """Test unknown status returns base AsanaError."""
        mock_response = MagicMock()
        mock_response.status_code = 418  # I'm a teapot
        mock_response.json.return_value = {
            "errors": [{"message": "I'm a teapot"}]
        }

        error = AsanaError.from_response(mock_response)

        assert type(error) is AsanaError  # Not a subclass
        assert error.status_code == 418

    def test_from_response_json_decode_error(self) -> None:
        """Test handling of non-JSON response body includes context."""
        import json

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = "Internal Server Error"
        mock_response.headers = {"X-Request-Id": "req-12345"}

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, ServerError)
        # Error message should include status code, request ID, and body text
        assert "HTTP 500" in error.message
        assert "request_id=req-12345" in error.message
        assert "Internal Server Error" in error.message

    def test_from_response_multiple_errors(self) -> None:
        """Test joining multiple error messages with context."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"X-Request-Id": "req-multi"}
        mock_response.json.return_value = {
            "errors": [
                {"message": "First error"},
                {"message": "Second error"},
            ]
        }

        error = AsanaError.from_response(mock_response)

        assert "First error" in error.message
        assert "Second error" in error.message
        assert "HTTP 400" in error.message
        assert "request_id=req-multi" in error.message

    def test_from_response_no_request_id(self) -> None:
        """Test error message when X-Request-Id header is absent."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}  # No X-Request-Id
        mock_response.json.return_value = {
            "errors": [{"message": "Server error"}]
        }

        error = AsanaError.from_response(mock_response)

        assert "HTTP 500" in error.message
        assert "request_id" not in error.message  # Should not include request_id context
        assert "Server error" in error.message


class TestRateLimitError:
    """Tests for RateLimitError specific functionality."""

    def test_retry_after_from_response(self) -> None:
        """Test parsing Retry-After header."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "30"}
        mock_response.json.return_value = {
            "errors": [{"message": "Rate limit exceeded"}]
        }

        error = RateLimitError.from_response(mock_response)

        assert error.retry_after == 30

    def test_retry_after_missing(self) -> None:
        """Test when Retry-After header is not present."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_response.json.return_value = {
            "errors": [{"message": "Rate limit exceeded"}]
        }

        error = RateLimitError.from_response(mock_response)

        assert error.retry_after is None

    def test_retry_after_invalid(self) -> None:
        """Test handling of non-integer Retry-After header."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "not-a-number"}
        mock_response.json.return_value = {
            "errors": [{"message": "Rate limit exceeded"}]
        }

        error = RateLimitError.from_response(mock_response)

        assert error.retry_after is None


class TestSyncInAsyncContextError:
    """Tests for SyncInAsyncContextError."""

    def test_error_message(self) -> None:
        """Test error message formatting."""
        error = SyncInAsyncContextError("get", "get_async")

        assert "get" in str(error)
        assert "get_async" in str(error)
        assert "async context" in str(error)

    def test_is_runtime_error(self) -> None:
        """Test that it's a RuntimeError (not AsanaError)."""
        error = SyncInAsyncContextError("get", "get_async")

        assert isinstance(error, RuntimeError)
        assert not isinstance(error, AsanaError)
