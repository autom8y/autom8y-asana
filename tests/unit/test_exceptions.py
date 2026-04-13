"""Tests for exception hierarchy and from_response factory."""

from unittest.mock import MagicMock

from autom8_asana.errors import (
    AsanaError,
    AuthenticationError,
    ForbiddenError,
    GoneError,
    InsightsError,
    InsightsNotFoundError,
    InsightsServiceError,
    InsightsValidationError,
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
        mock_response.json.return_value = {"errors": [{"message": "Invalid token"}]}

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, AuthenticationError)
        assert error.status_code == 401
        assert "Invalid token" in error.message

    def test_from_response_403(self) -> None:
        """Test 403 returns ForbiddenError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"errors": [{"message": "Access denied"}]}

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, ForbiddenError)
        assert error.status_code == 403

    def test_from_response_404(self) -> None:
        """Test 404 returns NotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"errors": [{"message": "Task not found"}]}

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, NotFoundError)
        assert error.status_code == 404

    def test_from_response_410(self) -> None:
        """Test 410 returns GoneError."""
        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_response.json.return_value = {"errors": [{"message": "Resource deleted"}]}

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, GoneError)
        assert error.status_code == 410

    def test_from_response_429(self) -> None:
        """Test 429 returns RateLimitError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"errors": [{"message": "Rate limit exceeded"}]}

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, RateLimitError)
        assert error.status_code == 429

    def test_from_response_500(self) -> None:
        """Test 500 returns ServerError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errors": [{"message": "Internal server error"}]}

        error = AsanaError.from_response(mock_response)

        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_from_response_unknown_status(self) -> None:
        """Test unknown status returns base AsanaError."""
        mock_response = MagicMock()
        mock_response.status_code = 418  # I'm a teapot
        mock_response.json.return_value = {"errors": [{"message": "I'm a teapot"}]}

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
        mock_response.json.return_value = {"errors": [{"message": "Server error"}]}

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
        mock_response.json.return_value = {"errors": [{"message": "Rate limit exceeded"}]}

        error = RateLimitError.from_response(mock_response)

        assert error.retry_after == 30

    def test_retry_after_missing(self) -> None:
        """Test when Retry-After header is not present."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_response.json.return_value = {"errors": [{"message": "Rate limit exceeded"}]}

        error = RateLimitError.from_response(mock_response)

        assert error.retry_after is None

    def test_retry_after_invalid(self) -> None:
        """Test handling of non-integer Retry-After header."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "not-a-number"}
        mock_response.json.return_value = {"errors": [{"message": "Rate limit exceeded"}]}

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


# --- Insights API Exception Tests (FR-008) ---


class TestInsightsError:
    """Tests for InsightsError base class."""

    def test_basic_creation(self) -> None:
        """Test basic InsightsError creation."""
        error = InsightsError("Insights operation failed")

        assert str(error) == "Insights operation failed"
        assert error.message == "Insights operation failed"
        assert error.request_id is None

    def test_creation_with_request_id(self) -> None:
        """Test InsightsError with request_id attribute."""
        error = InsightsError(
            "Insights operation failed",
            request_id="req-12345-abcde",
        )

        assert error.message == "Insights operation failed"
        assert error.request_id == "req-12345-abcde"

    def test_inherits_from_asana_error(self) -> None:
        """Test InsightsError inherits from AsanaError."""
        error = InsightsError("Test error")

        assert isinstance(error, AsanaError)
        assert isinstance(error, Exception)

    def test_with_status_code(self) -> None:
        """Test InsightsError with status_code from parent."""
        error = InsightsError(
            "Insights error",
            request_id="req-123",
            status_code=500,
        )

        assert error.status_code == 500
        assert error.request_id == "req-123"


class TestInsightsValidationError:
    """Tests for InsightsValidationError (400-level)."""

    def test_basic_creation(self) -> None:
        """Test basic InsightsValidationError creation."""
        error = InsightsValidationError("Invalid factory name")

        assert str(error) == "Invalid factory name"
        assert error.field is None
        assert error.request_id is None

    def test_creation_with_field(self) -> None:
        """Test InsightsValidationError with field attribute."""
        error = InsightsValidationError(
            "Invalid E.164 format",
            field="office_phone",
        )

        assert error.message == "Invalid E.164 format"
        assert error.field == "office_phone"

    def test_creation_with_all_attributes(self) -> None:
        """Test InsightsValidationError with all attributes."""
        error = InsightsValidationError(
            "Invalid period format",
            field="period",
            request_id="req-validation-001",
        )

        assert error.message == "Invalid period format"
        assert error.field == "period"
        assert error.request_id == "req-validation-001"

    def test_inherits_from_insights_error(self) -> None:
        """Test InsightsValidationError inherits from InsightsError."""
        error = InsightsValidationError("Test validation error")

        assert isinstance(error, InsightsError)
        assert isinstance(error, AsanaError)


class TestInsightsNotFoundError:
    """Tests for InsightsNotFoundError (404-level)."""

    def test_basic_creation(self) -> None:
        """Test basic InsightsNotFoundError creation."""
        error = InsightsNotFoundError("No data for this business")

        assert str(error) == "No data for this business"
        assert error.request_id is None

    def test_creation_with_request_id(self) -> None:
        """Test InsightsNotFoundError with request_id."""
        error = InsightsNotFoundError(
            "No insights data found for +17705753103",
            request_id="req-404-notfound",
        )

        assert error.message == "No insights data found for +17705753103"
        assert error.request_id == "req-404-notfound"

    def test_inherits_from_insights_error(self) -> None:
        """Test InsightsNotFoundError inherits from InsightsError."""
        error = InsightsNotFoundError("Test not found")

        assert isinstance(error, InsightsError)
        assert isinstance(error, AsanaError)


class TestInsightsServiceError:
    """Tests for InsightsServiceError (500-level)."""

    def test_basic_creation(self) -> None:
        """Test basic InsightsServiceError creation."""
        error = InsightsServiceError("autom8_data is unavailable")

        assert str(error) == "autom8_data is unavailable"
        assert error.reason is None
        assert error.request_id is None

    def test_creation_with_reason(self) -> None:
        """Test InsightsServiceError with reason attribute."""
        error = InsightsServiceError(
            "Request timed out",
            reason="timeout",
        )

        assert error.message == "Request timed out"
        assert error.reason == "timeout"

    def test_creation_with_status_code(self) -> None:
        """Test InsightsServiceError with status_code attribute."""
        error = InsightsServiceError(
            "Internal server error",
            status_code=500,
        )

        assert error.message == "Internal server error"
        assert error.status_code == 500

    def test_creation_with_all_attributes(self) -> None:
        """Test InsightsServiceError with all attributes."""
        error = InsightsServiceError(
            "Service unavailable",
            reason="circuit_breaker",
            status_code=503,
            request_id="req-service-001",
        )

        assert error.message == "Service unavailable"
        assert error.reason == "circuit_breaker"
        assert error.status_code == 503
        assert error.request_id == "req-service-001"

    def test_inherits_from_insights_error(self) -> None:
        """Test InsightsServiceError inherits from InsightsError."""
        error = InsightsServiceError("Test service error")

        assert isinstance(error, InsightsError)
        assert isinstance(error, AsanaError)

    def test_reason_values(self) -> None:
        """Test common reason values for InsightsServiceError."""
        # Test various reason values that would be used in practice
        reasons = ["timeout", "circuit_breaker", "http_error", "feature_disabled"]

        for reason in reasons:
            error = InsightsServiceError(f"Error with reason: {reason}", reason=reason)
            assert error.reason == reason
