"""Integration tests for error response edge cases.

Tests edge cases in error response handling that weren't covered by unit tests,
including malformed responses, unusual encodings, and connection errors.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from autom8_asana.config import AsanaConfig, RetryConfig
from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)
from autom8_asana.transport.http import AsyncHTTPClient


class MockAuthProvider:
    """Mock auth provider for integration testing."""

    def get_secret(self, key: str) -> str:
        return "test-token-for-error-response-tests"


class MockLogger:
    """Mock logger that records calls."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("debug", msg))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("info", msg))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("warning", msg))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("error", msg))

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages.append(("exception", msg))


@pytest.fixture
def config() -> AsanaConfig:
    """Test configuration with no retries for predictable behavior."""
    return AsanaConfig(
        base_url="https://app.asana.com/api/1.0",
        retry=RetryConfig(
            max_retries=0,  # No retries for error response tests
            jitter=False,
        ),
    )


@pytest.fixture
def auth_provider() -> MockAuthProvider:
    """Mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def logger() -> MockLogger:
    """Mock logger."""
    return MockLogger()


class TestEmptyResponseBody:
    """Test handling of error responses with empty bodies."""

    @respx.mock
    async def test_error_with_empty_body_400(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """400 error with completely empty body is handled gracefully."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                content=b"",
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        assert "HTTP 400" in error.message
        await client.close()

    @respx.mock
    async def test_error_with_empty_body_500(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """500 error with empty body raises ServerError with context."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                content=b"",
                headers={"X-Request-Id": "empty-body-500"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 500
        assert "HTTP 500" in error.message
        assert "request_id=empty-body-500" in error.message
        await client.close()

    @respx.mock
    async def test_error_with_whitespace_only_body(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Error with whitespace-only body is handled gracefully."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                404,
                content=b"   \n\t  ",
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(NotFoundError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 404
        await client.close()


class TestInvalidJSONBody:
    """Test handling of error responses with malformed JSON."""

    @respx.mock
    async def test_truncated_json_body(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Truncated JSON body (incomplete) is handled gracefully."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                content=b'{"errors": [{"message": "Incomplete',
                headers={"Content-Type": "application/json"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        # Body snippet should be in error message
        assert "Incomplete" in error.message
        await client.close()

    @respx.mock
    async def test_json_with_trailing_garbage(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """JSON with trailing garbage characters is handled."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                content=b'{"errors": []}garbage after json',
                headers={"Content-Type": "application/json"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 500
        await client.close()

    @respx.mock
    async def test_json_array_instead_of_object(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """JSON array instead of expected object is handled."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                json=["error1", "error2"],  # Array instead of object
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        # Should not crash, should produce sensible error
        assert "HTTP 400" in error.message
        await client.close()

    @respx.mock
    async def test_json_primitive_instead_of_object(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """JSON primitive (string) instead of expected object is handled."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                content=b'"just a string"',
                headers={"Content-Type": "application/json"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        await client.close()


class TestMissingErrorsKey:
    """Test handling of valid JSON without expected 'errors' array."""

    @respx.mock
    async def test_json_without_errors_key(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Valid JSON without 'errors' key uses default message."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                json={"status": "error", "code": "INVALID"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        assert "HTTP 400" in error.message
        # Should not contain error details since no 'errors' key
        await client.close()

    @respx.mock
    async def test_errors_key_not_an_array(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """'errors' key that is not an array is handled."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                json={"errors": "This is not an array"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        # Should fallback to default message, not crash
        await client.close()

    @respx.mock
    async def test_errors_array_with_missing_message(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """'errors' array with items missing 'message' key handled."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                json={"errors": [{"code": "INVALID", "help": "See docs"}]},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        # Should use fallback "Unknown error" for missing message
        assert "Unknown error" in error.message
        await client.close()

    @respx.mock
    async def test_empty_errors_array(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Empty 'errors' array is handled gracefully."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                json={"errors": []},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        await client.close()


class TestHTTPStatusWithoutErrorBody:
    """Test various HTTP error codes with non-JSON or empty bodies."""

    @respx.mock
    async def test_401_with_plain_text_body(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """401 with plain text body raises AuthenticationError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                401,
                content=b"Unauthorized access",
                headers={"Content-Type": "text/plain"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AuthenticationError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 401
        # Plain text body should be included in message
        assert "Unauthorized access" in error.message
        await client.close()

    @respx.mock
    async def test_429_with_empty_body(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """429 with empty body still raises RateLimitError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                429,
                content=b"",
                headers={"Retry-After": "60"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(RateLimitError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 429
        await client.close()

    @respx.mock
    async def test_502_with_no_content_type(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """502 with no content type header is handled."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                502,
                content=b"Bad Gateway",
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 502
        assert "Bad Gateway" in error.message
        await client.close()


class TestHTMLErrorPageHandling:
    """Test handling of HTML error pages from proxies/CDNs."""

    @respx.mock
    async def test_html_error_page_502(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """HTML error page from proxy is handled gracefully."""
        html_error = b"""<!DOCTYPE html>
<html>
<head><title>502 Bad Gateway</title></head>
<body>
<h1>502 Bad Gateway</h1>
<p>The server is temporarily unable to service your request.</p>
</body>
</html>"""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                502,
                content=html_error,
                headers={"Content-Type": "text/html"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 502
        # Should include HTML snippet in message for debugging
        assert "502" in error.message or "Bad Gateway" in error.message
        await client.close()

    @respx.mock
    async def test_cloudflare_style_error_page(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Cloudflare-style HTML error page is handled."""
        cloudflare_html = b"""<!DOCTYPE html>
<html>
<head>
<title>Error 503</title>
<meta name="robots" content="noindex, nofollow">
</head>
<body>
<div class="cf-error-title"><h1>Service Temporarily Unavailable</h1></div>
<div class="cf-wrapper"><p>Please try again in a few minutes.</p></div>
</body>
</html>"""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                503,
                content=cloudflare_html,
                headers={"Content-Type": "text/html; charset=UTF-8"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 503
        await client.close()

    @respx.mock
    async def test_nginx_default_error_page(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """nginx default error page is handled."""
        nginx_html = b"""<html>
<head><title>504 Gateway Time-out</title></head>
<body bgcolor="white">
<center><h1>504 Gateway Time-out</h1></center>
<hr><center>nginx/1.18.0</center>
</body>
</html>"""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                504,
                content=nginx_html,
                headers={"Content-Type": "text/html"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 504
        await client.close()


class TestTruncatedResponseHandling:
    """Test handling of very long error messages."""

    @respx.mock
    async def test_very_long_error_message(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Very long error message is truncated without crashing."""
        long_message = "A" * 10000  # 10KB error message
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                json={"errors": [{"message": long_message}]},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        # Error should contain part of the message
        assert "AAA" in error.message
        await client.close()

    @respx.mock
    async def test_very_long_non_json_body(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Very long non-JSON body is truncated in error message."""
        long_body = b"X" * 10000  # 10KB body
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                content=long_body,
                headers={"X-Request-Id": "long-body-test"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 500
        # Message should be truncated (per from_response logic: first 200 chars + ...)
        assert len(error.message) < 10000
        assert "..." in error.message
        await client.close()

    @respx.mock
    async def test_many_errors_in_array(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Many errors in array are joined without crashing."""
        many_errors = [{"message": f"Error {i}"} for i in range(100)]
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                json={"errors": many_errors},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        # Should contain some errors joined together
        assert "Error 0" in error.message
        assert error.errors == many_errors
        await client.close()


class TestNonUTF8ResponseHandling:
    """Test handling of responses with invalid/non-UTF8 encoding."""

    @respx.mock
    async def test_latin1_encoded_response(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Latin-1 encoded text in response is handled."""
        # Latin-1 character that's invalid in UTF-8 interpretation
        latin1_text = "Error: caf\xe9".encode("latin-1")
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                content=latin1_text,
                headers={"Content-Type": "text/plain; charset=latin-1"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 500
        await client.close()

    @respx.mock
    async def test_binary_content_in_error_response(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Binary content in error response is handled without crashing."""
        # Random binary data that's definitely not valid text
        binary_content = bytes(range(256))
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                content=binary_content,
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 500
        await client.close()

    @respx.mock
    async def test_null_bytes_in_response(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Null bytes in response body are handled."""
        content_with_nulls = b'{"error": "test\x00null\x00bytes"}'
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                400,
                content=content_with_nulls,
                headers={"Content-Type": "application/json"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 400
        await client.close()


class TestConnectionErrorsVsHTTPErrors:
    """Test that connection failures are distinguished from HTTP errors."""

    @respx.mock
    async def test_connection_refused(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Connection refused raises AsanaError with useful context."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        # Should not have status_code since it's a connection error
        assert error.status_code is None
        assert "HTTP error" in str(error) or "Connection" in str(error)
        await client.close()

    @respx.mock
    async def test_dns_resolution_failure(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """DNS resolution failure raises AsanaError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            side_effect=httpx.ConnectError("Name resolution failed")
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code is None
        await client.close()

    @respx.mock
    async def test_ssl_error(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """SSL/TLS error raises AsanaError with context."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            side_effect=httpx.ConnectError("SSL certificate verify failed")
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code is None
        await client.close()

    @respx.mock
    async def test_connection_timeout_vs_read_timeout(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Connection timeout raises TimeoutError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            side_effect=httpx.ConnectTimeout("Connection timed out")
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(TimeoutError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert "timed out" in str(error).lower()
        await client.close()

    @respx.mock
    async def test_read_timeout(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Read timeout after connection raises TimeoutError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(TimeoutError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert "timed out" in str(error).lower()
        await client.close()

    @respx.mock
    async def test_network_error_generic(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Generic network error raises AsanaError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            side_effect=httpx.NetworkError("Network unreachable")
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code is None
        await client.close()


class TestEdgeCaseHTTPStatus:
    """Test edge case HTTP status codes."""

    @respx.mock
    async def test_uncommon_4xx_status(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Uncommon 4xx status (418 I'm a teapot) raises base AsanaError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                418,
                json={"errors": [{"message": "I'm a teapot"}]},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 418
        assert type(error) is AsanaError  # Not a subclass
        await client.close()

    @respx.mock
    async def test_uncommon_5xx_status(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Uncommon 5xx status (507 Insufficient Storage) raises ServerError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                507,
                json={"errors": [{"message": "Insufficient storage"}]},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 507
        # 507 is not in _STATUS_CODE_MAP, so base AsanaError
        assert type(error) is AsanaError
        await client.close()

    @respx.mock
    async def test_422_unprocessable_entity(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """422 Unprocessable Entity raises base AsanaError."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                422,
                json={"errors": [{"message": "Validation failed"}]},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(AsanaError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 422
        assert "Validation failed" in error.message
        await client.close()


class TestErrorResponseWithSpecialHeaders:
    """Test error handling with special response headers."""

    @respx.mock
    async def test_error_with_request_id_header(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """X-Request-Id header is included in error message."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                500,
                json={"errors": [{"message": "Internal error"}]},
                headers={"X-Request-Id": "req-12345-abcde"},
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(ServerError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert "req-12345-abcde" in error.message
        await client.close()

    @respx.mock
    async def test_rate_limit_with_multiple_headers(
        self, config: AsanaConfig, auth_provider: MockAuthProvider
    ) -> None:
        """Rate limit error preserves Retry-After from headers."""
        respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
            return_value=httpx.Response(
                429,
                json={"errors": [{"message": "Rate limited"}]},
                headers={
                    "Retry-After": "120",
                    "X-RateLimit-Limit": "1500",
                    "X-RateLimit-Remaining": "0",
                    "X-Request-Id": "rate-limit-req",
                },
            )
        )
        client = AsyncHTTPClient(config, auth_provider)

        with pytest.raises(RateLimitError) as exc_info:
            await client.get("/tasks/123")

        error = exc_info.value
        assert error.status_code == 429
        assert "rate-limit-req" in error.message
        await client.close()
