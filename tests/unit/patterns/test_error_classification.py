"""Unit tests for RetryableErrorMixin and HasError protocol.

Per Initiative DESIGN-PATTERNS-B: Tests for the error classification mixin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from autom8_asana.patterns import HasError, RetryableErrorMixin


# ---------------------------------------------------------------------------
# Test fixtures: Classes using the mixin
# ---------------------------------------------------------------------------


@dataclass
class ErrorContainer(RetryableErrorMixin):
    """Simple test class with an error field."""

    error: Exception | None

    def _get_error(self) -> Exception | None:
        return self.error


@dataclass
class ConditionalErrorContainer(RetryableErrorMixin):
    """Test class that conditionally exposes error based on success flag."""

    success: bool
    error: Exception | None = None

    def _get_error(self) -> Exception | None:
        if self.success:
            return None
        return self.error


class MockErrorWithStatusCode(Exception):
    """Mock exception with status_code attribute."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# HasError Protocol Tests
# ---------------------------------------------------------------------------


class TestHasErrorProtocol:
    """Tests for HasError protocol type checking."""

    def test_error_container_implements_has_error(self) -> None:
        """ErrorContainer satisfies HasError protocol."""
        container = ErrorContainer(error=ValueError("test"))
        assert isinstance(container, HasError)

    def test_conditional_container_implements_has_error(self) -> None:
        """ConditionalErrorContainer satisfies HasError protocol."""
        container = ConditionalErrorContainer(success=True)
        assert isinstance(container, HasError)

    def test_plain_object_does_not_implement_has_error(self) -> None:
        """Objects without _get_error do not satisfy HasError."""

        class PlainClass:
            pass

        obj = PlainClass()
        assert not isinstance(obj, HasError)

    def test_object_with_wrong_signature_does_not_implement(self) -> None:
        """Objects with wrong _get_error signature do not satisfy HasError."""

        class WrongSignature:
            def _get_error(self, arg: str) -> Exception | None:
                return None

        # Note: runtime_checkable only checks method existence, not signature
        # This test documents that limitation
        obj = WrongSignature()
        # Protocol only checks method exists, not signature at runtime
        assert isinstance(obj, HasError)  # This is a known limitation


# ---------------------------------------------------------------------------
# RetryableErrorMixin.is_retryable Tests
# ---------------------------------------------------------------------------


class TestIsRetryable:
    """Tests for RetryableErrorMixin.is_retryable property."""

    def test_no_error_returns_false(self) -> None:
        """is_retryable is False when no error present."""
        container = ErrorContainer(error=None)
        assert container.is_retryable is False

    def test_success_flag_prevents_retryable(self) -> None:
        """is_retryable is False for successful operations."""
        error = RateLimitError("Rate limited", status_code=429)
        container = ConditionalErrorContainer(success=True, error=error)
        assert container.is_retryable is False

    # --- Network Errors ---

    def test_timeout_error_is_retryable(self) -> None:
        """TimeoutError is classified as retryable."""
        container = ErrorContainer(error=TimeoutError("timed out"))
        assert container.is_retryable is True

    def test_connection_error_is_retryable(self) -> None:
        """ConnectionError is classified as retryable."""
        container = ErrorContainer(error=ConnectionError("refused"))
        assert container.is_retryable is True

    def test_os_error_is_retryable(self) -> None:
        """OSError is classified as retryable."""
        container = ErrorContainer(error=OSError("network unreachable"))
        assert container.is_retryable is True

    # --- HTTP Status Codes: Retryable ---

    def test_429_rate_limit_is_retryable(self) -> None:
        """429 status code is retryable."""
        error = RateLimitError("Rate limited", status_code=429)
        container = ErrorContainer(error=error)
        assert container.is_retryable is True

    def test_500_server_error_is_retryable(self) -> None:
        """500 status code is retryable."""
        error = ServerError("Internal Server Error", status_code=500)
        container = ErrorContainer(error=error)
        assert container.is_retryable is True

    def test_502_bad_gateway_is_retryable(self) -> None:
        """502 status code is retryable."""
        error = ServerError("Bad Gateway", status_code=502)
        container = ErrorContainer(error=error)
        assert container.is_retryable is True

    def test_503_service_unavailable_is_retryable(self) -> None:
        """503 status code is retryable."""
        error = ServerError("Service Unavailable", status_code=503)
        container = ErrorContainer(error=error)
        assert container.is_retryable is True

    def test_504_gateway_timeout_is_retryable(self) -> None:
        """504 status code is retryable."""
        error = ServerError("Gateway Timeout", status_code=504)
        container = ErrorContainer(error=error)
        assert container.is_retryable is True

    # --- HTTP Status Codes: Not Retryable ---

    def test_400_bad_request_not_retryable(self) -> None:
        """400 status code is not retryable."""
        error = AsanaError("Bad Request", status_code=400)
        container = ErrorContainer(error=error)
        assert container.is_retryable is False

    def test_401_unauthorized_not_retryable(self) -> None:
        """401 status code is not retryable."""
        error = AuthenticationError("Unauthorized", status_code=401)
        container = ErrorContainer(error=error)
        assert container.is_retryable is False

    def test_403_forbidden_not_retryable(self) -> None:
        """403 status code is not retryable."""
        error = ForbiddenError("Forbidden", status_code=403)
        container = ErrorContainer(error=error)
        assert container.is_retryable is False

    def test_404_not_found_not_retryable(self) -> None:
        """404 status code is not retryable."""
        error = NotFoundError("Not Found", status_code=404)
        container = ErrorContainer(error=error)
        assert container.is_retryable is False

    def test_409_conflict_not_retryable(self) -> None:
        """409 status code is not retryable."""
        error = AsanaError("Conflict", status_code=409)
        container = ErrorContainer(error=error)
        assert container.is_retryable is False

    # --- Edge Cases ---

    def test_unknown_error_not_retryable(self) -> None:
        """Errors without status code are not retryable."""
        error = ValueError("Something went wrong")
        container = ErrorContainer(error=error)
        assert container.is_retryable is False

    def test_generic_exception_with_status_code_attribute(self) -> None:
        """Generic exceptions with status_code attribute are handled."""
        error = MockErrorWithStatusCode("Rate limited", status_code=429)
        container = ErrorContainer(error=error)
        assert container.is_retryable is True


# ---------------------------------------------------------------------------
# RetryableErrorMixin.recovery_hint Tests
# ---------------------------------------------------------------------------


class TestRecoveryHint:
    """Tests for RetryableErrorMixin.recovery_hint property."""

    def test_no_error_returns_empty_string(self) -> None:
        """recovery_hint is empty when no error present."""
        container = ErrorContainer(error=None)
        assert container.recovery_hint == ""

    def test_success_flag_returns_empty_string(self) -> None:
        """recovery_hint is empty for successful operations."""
        error = RateLimitError("Rate limited", status_code=429)
        container = ConditionalErrorContainer(success=True, error=error)
        assert container.recovery_hint == ""

    # --- Network Error Hints ---

    def test_timeout_error_hint(self) -> None:
        """TimeoutError provides appropriate hint."""
        container = ErrorContainer(error=TimeoutError("timed out"))
        assert "timed out" in container.recovery_hint.lower()
        assert "exponential backoff" in container.recovery_hint.lower()

    def test_connection_error_hint(self) -> None:
        """ConnectionError provides appropriate hint."""
        container = ErrorContainer(error=ConnectionError("refused"))
        assert "connection" in container.recovery_hint.lower()
        assert "connectivity" in container.recovery_hint.lower()

    def test_os_error_hint(self) -> None:
        """OSError provides appropriate hint."""
        container = ErrorContainer(error=OSError("network unreachable"))
        assert "network" in container.recovery_hint.lower()
        assert "connectivity" in container.recovery_hint.lower()

    # --- HTTP Status Code Hints ---

    def test_429_hint_mentions_rate_limit(self) -> None:
        """429 hint mentions rate limit and retry_after."""
        error = RateLimitError("Rate limited", status_code=429)
        container = ErrorContainer(error=error)
        assert "rate limit" in container.recovery_hint.lower()
        assert "retry_after" in container.recovery_hint.lower()

    def test_500_hint_suggests_retry(self) -> None:
        """500 hint suggests retry with backoff."""
        error = ServerError("Internal Server Error", status_code=500)
        container = ErrorContainer(error=error)
        assert "retry" in container.recovery_hint.lower()
        assert "exponential backoff" in container.recovery_hint.lower()

    def test_400_hint_mentions_payload(self) -> None:
        """400 hint mentions checking payload."""
        error = AsanaError("Bad Request", status_code=400)
        container = ErrorContainer(error=error)
        assert "payload" in container.recovery_hint.lower()

    def test_401_hint_mentions_credentials(self) -> None:
        """401 hint mentions credentials."""
        error = AuthenticationError("Unauthorized", status_code=401)
        container = ErrorContainer(error=error)
        assert "credential" in container.recovery_hint.lower()

    def test_403_hint_mentions_permissions(self) -> None:
        """403 hint mentions permissions."""
        error = ForbiddenError("Forbidden", status_code=403)
        container = ErrorContainer(error=error)
        assert "permission" in container.recovery_hint.lower()

    def test_404_hint_mentions_gid(self) -> None:
        """404 hint mentions verifying GID."""
        error = NotFoundError("Not Found", status_code=404)
        container = ErrorContainer(error=error)
        hint_lower = container.recovery_hint.lower()
        assert "not found" in hint_lower or "gid" in hint_lower

    def test_409_hint_mentions_conflict(self) -> None:
        """409 hint mentions conflict."""
        error = AsanaError("Conflict", status_code=409)
        container = ErrorContainer(error=error)
        assert "conflict" in container.recovery_hint.lower()

    # --- Fallback Hints ---

    def test_unknown_4xx_hint(self) -> None:
        """Unknown 4xx status codes get generic client error hint."""
        error = AsanaError("I'm a teapot", status_code=418)
        container = ErrorContainer(error=error)
        assert "client error" in container.recovery_hint.lower()
        assert "418" in container.recovery_hint

    def test_unknown_5xx_hint(self) -> None:
        """Unknown 5xx status codes get generic server error hint."""
        error = ServerError("Unknown Server Error", status_code=599)
        container = ErrorContainer(error=error)
        assert "server error" in container.recovery_hint.lower()
        assert "599" in container.recovery_hint

    def test_unknown_error_hint(self) -> None:
        """Errors without status code get generic hint."""
        error = ValueError("Something went wrong")
        container = ErrorContainer(error=error)
        assert "unknown" in container.recovery_hint.lower()
        assert "inspect" in container.recovery_hint.lower()


# ---------------------------------------------------------------------------
# RetryableErrorMixin.retry_after_seconds Tests
# ---------------------------------------------------------------------------


class TestRetryAfterSeconds:
    """Tests for RetryableErrorMixin.retry_after_seconds property."""

    def test_no_error_returns_none(self) -> None:
        """retry_after_seconds is None when no error present."""
        container = ErrorContainer(error=None)
        assert container.retry_after_seconds is None

    def test_error_without_retry_after_returns_none(self) -> None:
        """retry_after_seconds is None for errors without retry_after."""
        error = ServerError("Internal Server Error", status_code=500)
        container = ErrorContainer(error=error)
        assert container.retry_after_seconds is None

    def test_rate_limit_error_with_retry_after(self) -> None:
        """retry_after_seconds extracts from RateLimitError."""
        error = RateLimitError("Rate limited", status_code=429, retry_after=60)
        container = ErrorContainer(error=error)
        assert container.retry_after_seconds == 60

    def test_generic_error_with_retry_after_attribute(self) -> None:
        """retry_after_seconds extracts from generic error with attribute."""

        class CustomError(Exception):
            def __init__(self) -> None:
                super().__init__("custom")
                self.retry_after = 30

        error = CustomError()
        container = ErrorContainer(error=error)
        assert container.retry_after_seconds == 30


# ---------------------------------------------------------------------------
# RetryableErrorMixin._extract_status_code Tests
# ---------------------------------------------------------------------------


class TestExtractStatusCode:
    """Tests for RetryableErrorMixin._extract_status_code static method."""

    def test_extracts_from_asana_error(self) -> None:
        """Extracts status code from AsanaError."""
        error = AsanaError("Error", status_code=400)
        status = RetryableErrorMixin._extract_status_code(error)
        assert status == 400

    def test_extracts_from_rate_limit_error(self) -> None:
        """Extracts status code from RateLimitError."""
        error = RateLimitError("Rate limited", status_code=429)
        status = RetryableErrorMixin._extract_status_code(error)
        assert status == 429

    def test_extracts_from_generic_error_with_attribute(self) -> None:
        """Extracts status code from generic error with attribute."""
        error = MockErrorWithStatusCode("Error", status_code=503)
        status = RetryableErrorMixin._extract_status_code(error)
        assert status == 503

    def test_returns_none_for_error_without_status_code(self) -> None:
        """Returns None for errors without status_code."""
        error = ValueError("Error")
        status = RetryableErrorMixin._extract_status_code(error)
        assert status is None

    def test_returns_none_for_non_int_status_code(self) -> None:
        """Returns None if status_code is not an int."""

        class BadError(Exception):
            status_code = "not_an_int"  # type: ignore

        error = BadError()
        status = RetryableErrorMixin._extract_status_code(error)
        assert status is None


# ---------------------------------------------------------------------------
# Integration: Mixin with dataclass inheritance
# ---------------------------------------------------------------------------


class TestMixinDataclassIntegration:
    """Tests for mixin integration with dataclasses."""

    def test_mixin_works_with_dataclass(self) -> None:
        """Mixin integrates correctly with dataclass."""
        container = ErrorContainer(error=RateLimitError("test", status_code=429))

        # Dataclass features work
        assert container.error is not None

        # Mixin features work
        assert container.is_retryable is True
        assert "rate limit" in container.recovery_hint.lower()

    def test_multiple_inheritance_order(self) -> None:
        """Mixin works regardless of inheritance order."""

        @dataclass
        class MixinFirst(RetryableErrorMixin):
            error: Exception | None

            def _get_error(self) -> Exception | None:
                return self.error

        container = MixinFirst(error=TimeoutError("timeout"))
        assert container.is_retryable is True

    def test_mixin_can_be_overridden(self) -> None:
        """Subclasses can override mixin methods."""

        @dataclass
        class CustomContainer(RetryableErrorMixin):
            error: Exception | None

            def _get_error(self) -> Exception | None:
                return self.error

            @property
            def is_retryable(self) -> bool:
                # Custom: always retryable
                return True

        container = CustomContainer(error=NotFoundError("Not found", status_code=404))
        # Default would be False for 404, but override makes it True
        assert container.is_retryable is True
