"""Tests for Domain III: API-layer typed exceptions and handlers.

Verifies that the new typed exception classes (ApiAuthError,
ApiServiceUnavailableError, ApiDataFrameBuildError) produce canonical
ErrorResponse envelopes when caught by their registered handlers.

Per Domain III (Absolute Enforcement Mandate): All bare HTTPException
sites have been converted to typed exceptions.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from autom8_asana.api.exception_types import (
    ApiAuthError,
    ApiDataFrameBuildError,
    ApiError,
    ApiServiceUnavailableError,
)

# ---------------------------------------------------------------------------
# ApiError base class
# ---------------------------------------------------------------------------


class TestApiError:
    """Tests for the ApiError base exception."""

    def test_basic_construction(self) -> None:
        """ApiError stores code, message, status_code, details, headers."""
        exc = ApiError("CODE", "msg", status_code=418, details={"k": "v"})
        assert exc.code == "CODE"
        assert exc.message == "msg"
        assert exc.status_code == 418
        assert exc.details == {"k": "v"}
        assert exc.headers is None
        assert str(exc) == "msg"

    def test_default_status_code(self) -> None:
        """Default status_code is 500."""
        exc = ApiError("CODE", "msg")
        assert exc.status_code == 500

    def test_with_headers(self) -> None:
        """Headers are stored when provided."""
        headers = {"X-Custom": "value"}
        exc = ApiError("CODE", "msg", headers=headers)
        assert exc.headers == headers


# ---------------------------------------------------------------------------
# ApiAuthError
# ---------------------------------------------------------------------------


class TestApiAuthError:
    """Tests for ApiAuthError (401)."""

    def test_default_www_authenticate_header(self) -> None:
        """ApiAuthError includes WWW-Authenticate: Bearer by default."""
        exc = ApiAuthError("MISSING_AUTH", "Authorization header required")
        assert exc.status_code == 401
        assert exc.headers == {"WWW-Authenticate": "Bearer"}

    def test_custom_headers_override_default(self) -> None:
        """Custom headers replace the default WWW-Authenticate."""
        exc = ApiAuthError(
            "CUSTOM",
            "custom",
            headers={"WWW-Authenticate": "Basic"},
        )
        assert exc.headers == {"WWW-Authenticate": "Basic"}

    def test_is_exception(self) -> None:
        """ApiAuthError can be raised and caught."""
        with pytest.raises(ApiAuthError) as exc_info:
            raise ApiAuthError("MISSING_AUTH", "Authorization header required")
        assert exc_info.value.code == "MISSING_AUTH"

    def test_is_api_error_subclass(self) -> None:
        """ApiAuthError is a subclass of ApiError."""
        exc = ApiAuthError("CODE", "msg")
        assert isinstance(exc, ApiError)

    @pytest.mark.parametrize(
        "code,message",
        [
            ("MISSING_AUTH", "Authorization header required"),
            ("INVALID_SCHEME", "Bearer scheme required"),
            ("MISSING_TOKEN", "Token is required"),
            ("INVALID_TOKEN", "Invalid token format"),
            ("SERVICE_TOKEN_REQUIRED", "PAT tokens are not supported"),
        ],
    )
    def test_all_auth_error_codes(self, code: str, message: str) -> None:
        """All auth error codes from the codebase can be represented."""
        exc = ApiAuthError(code, message)
        assert exc.code == code
        assert exc.message == message
        assert exc.status_code == 401


# ---------------------------------------------------------------------------
# ApiServiceUnavailableError
# ---------------------------------------------------------------------------


class TestApiServiceUnavailableError:
    """Tests for ApiServiceUnavailableError (503)."""

    def test_default_status_code(self) -> None:
        """Status code is always 503."""
        exc = ApiServiceUnavailableError("S2S_NOT_CONFIGURED", "Not available")
        assert exc.status_code == 503

    def test_with_details(self) -> None:
        """Details are stored when provided."""
        exc = ApiServiceUnavailableError(
            "S2S_NOT_CONFIGURED",
            "Not available",
            details={"retry": True},
        )
        assert exc.details == {"retry": True}

    def test_no_headers(self) -> None:
        """503 errors do not include WWW-Authenticate header."""
        exc = ApiServiceUnavailableError("CODE", "msg")
        assert exc.headers is None

    def test_is_api_error_subclass(self) -> None:
        """ApiServiceUnavailableError is a subclass of ApiError."""
        exc = ApiServiceUnavailableError("CODE", "msg")
        assert isinstance(exc, ApiError)


# ---------------------------------------------------------------------------
# ApiDataFrameBuildError
# ---------------------------------------------------------------------------


class TestApiDataFrameBuildError:
    """Tests for ApiDataFrameBuildError (503)."""

    def test_default_status_code(self) -> None:
        """Status code is always 503."""
        exc = ApiDataFrameBuildError("BUILD_FAILED", "Build failed")
        assert exc.status_code == 503

    def test_retry_after_in_details(self) -> None:
        """retry_after_seconds is stored in details dict."""
        exc = ApiDataFrameBuildError(
            "BUILD_FAILED",
            "Build failed",
            retry_after_seconds=30,
        )
        assert exc.details == {"retry_after_seconds": 30}

    def test_no_retry_after(self) -> None:
        """Without retry_after_seconds, details is None."""
        exc = ApiDataFrameBuildError("BUILD_UNAVAILABLE", "No method")
        assert exc.details is None

    def test_is_api_error_subclass(self) -> None:
        """ApiDataFrameBuildError is a subclass of ApiError."""
        exc = ApiDataFrameBuildError("CODE", "msg")
        assert isinstance(exc, ApiError)

    @pytest.mark.parametrize(
        "code,message,retry",
        [
            ("CACHE_BUILD_IN_PROGRESS", "Build in progress, retry shortly", 5),
            ("DATAFRAME_BUILD_UNAVAILABLE", "No build method configured", None),
            ("DATAFRAME_BUILD_FAILED", "Failed to build DataFrame", 30),
            ("DATAFRAME_BUILD_ERROR", "Build failed: ValueError", 30),
        ],
    )
    def test_all_dataframe_error_codes(
        self, code: str, message: str, retry: int | None
    ) -> None:
        """All dataframe error codes from the codebase can be represented."""
        exc = ApiDataFrameBuildError(code, message, retry_after_seconds=retry)
        assert exc.code == code
        assert exc.message == message


# ---------------------------------------------------------------------------
# Handler integration tests
# ---------------------------------------------------------------------------


def _make_request(request_id: str = "test-req-id") -> MagicMock:
    """Create a mock FastAPI Request with request.state.request_id."""
    req = MagicMock()
    req.state = SimpleNamespace(request_id=request_id)
    return req


class TestApiAuthErrorHandler:
    """Tests for api_auth_error_handler producing canonical ErrorResponse."""

    @pytest.mark.asyncio
    async def test_produces_canonical_envelope(self) -> None:
        """Handler produces canonical ErrorResponse format."""
        from autom8_asana.api.errors import api_auth_error_handler

        request = _make_request("auth-req-001")
        exc = ApiAuthError("MISSING_AUTH", "Authorization header required")

        response = await api_auth_error_handler(request, exc)

        assert response.status_code == 401
        content = response.body.decode()
        import json

        body = json.loads(content)
        assert body["error"]["code"] == "MISSING_AUTH"
        assert body["error"]["message"] == "Authorization header required"
        assert body["meta"]["request_id"] == "auth-req-001"

    @pytest.mark.asyncio
    async def test_includes_www_authenticate_header(self) -> None:
        """Handler includes WWW-Authenticate header from exception."""
        from autom8_asana.api.errors import api_auth_error_handler

        request = _make_request()
        exc = ApiAuthError("INVALID_SCHEME", "Bearer scheme required")

        response = await api_auth_error_handler(request, exc)

        assert response.headers.get("www-authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_missing_request_id_uses_unknown(self) -> None:
        """Handler uses 'unknown' when request.state has no request_id."""
        from autom8_asana.api.errors import api_auth_error_handler

        request = MagicMock()
        request.state = SimpleNamespace()  # No request_id
        exc = ApiAuthError("CODE", "msg")

        response = await api_auth_error_handler(request, exc)

        import json

        body = json.loads(response.body.decode())
        assert body["meta"]["request_id"] == "unknown"


class TestApiServiceUnavailableHandler:
    """Tests for api_service_unavailable_handler."""

    @pytest.mark.asyncio
    async def test_produces_503_canonical_envelope(self) -> None:
        """Handler produces 503 with canonical ErrorResponse."""
        from autom8_asana.api.errors import api_service_unavailable_handler

        request = _make_request("svc-req-001")
        exc = ApiServiceUnavailableError(
            "S2S_NOT_CONFIGURED",
            "Service-to-service authentication is not available",
        )

        response = await api_service_unavailable_handler(request, exc)

        assert response.status_code == 503
        import json

        body = json.loads(response.body.decode())
        assert body["error"]["code"] == "S2S_NOT_CONFIGURED"
        assert body["meta"]["request_id"] == "svc-req-001"


class TestApiDataFrameBuildErrorHandler:
    """Tests for api_dataframe_build_error_handler."""

    @pytest.mark.asyncio
    async def test_produces_503_with_retry_details(self) -> None:
        """Handler produces 503 with retry_after_seconds in details."""
        from autom8_asana.api.errors import api_dataframe_build_error_handler

        request = _make_request("df-req-001")
        exc = ApiDataFrameBuildError(
            "CACHE_BUILD_IN_PROGRESS",
            "DataFrame build in progress, retry shortly",
            retry_after_seconds=5,
        )

        response = await api_dataframe_build_error_handler(request, exc)

        assert response.status_code == 503
        import json

        body = json.loads(response.body.decode())
        assert body["error"]["code"] == "CACHE_BUILD_IN_PROGRESS"
        assert body["error"]["details"]["retry_after_seconds"] == 5
        assert body["meta"]["request_id"] == "df-req-001"

    @pytest.mark.asyncio
    async def test_produces_503_without_retry(self) -> None:
        """Handler produces 503 without retry details when not provided."""
        from autom8_asana.api.errors import api_dataframe_build_error_handler

        request = _make_request("df-req-002")
        exc = ApiDataFrameBuildError(
            "DATAFRAME_BUILD_UNAVAILABLE",
            "No build method configured",
        )

        response = await api_dataframe_build_error_handler(request, exc)

        assert response.status_code == 503
        import json

        body = json.loads(response.body.decode())
        assert body["error"]["code"] == "DATAFRAME_BUILD_UNAVAILABLE"
        # details should be None/absent
        assert body["error"]["details"] is None


class TestApiErrorHandler:
    """Tests for the generic api_error_handler (catch-all for ApiError)."""

    @pytest.mark.asyncio
    async def test_catches_base_api_error(self) -> None:
        """Generic handler catches ApiError instances."""
        from autom8_asana.api.errors import api_error_handler

        request = _make_request("generic-req")
        exc = ApiError("CUSTOM_CODE", "Custom message", status_code=418)

        response = await api_error_handler(request, exc)

        assert response.status_code == 418
        import json

        body = json.loads(response.body.decode())
        assert body["error"]["code"] == "CUSTOM_CODE"
        assert body["error"]["message"] == "Custom message"


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    """Verify API-layer handlers are registered in the app."""

    def test_api_layer_handlers_in_all(self) -> None:
        """All API-layer handler functions are in __all__."""
        from autom8_asana.api import errors

        api_handlers = [
            "api_auth_error_handler",
            "api_service_unavailable_handler",
            "api_dataframe_build_error_handler",
            "api_error_handler",
        ]
        for name in api_handlers:
            assert name in errors.__all__, f"Missing from __all__: {name}"
            assert callable(getattr(errors, name))

    def test_register_includes_api_layer_handlers(self) -> None:
        """register_exception_handlers registers API-layer handlers."""
        import inspect

        from autom8_asana.api.errors import register_exception_handlers

        source = inspect.getsource(register_exception_handlers)
        assert "ApiAuthError" in source
        assert "ApiServiceUnavailableError" in source
        assert "ApiDataFrameBuildError" in source
        assert "ApiError" in source


# ---------------------------------------------------------------------------
# Zero bare HTTPException verification
# ---------------------------------------------------------------------------


class TestZeroBareHttpException:
    """Verify no bare HTTPException remains in the migrated modules."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "autom8_asana.api.dependencies",
            "autom8_asana.api.routes.internal",
            "autom8_asana.auth.dual_mode",
            "autom8_asana.cache.dataframe.decorator",
        ],
    )
    def test_no_raise_http_exception(self, module_path: str) -> None:
        """Domain III modules have zero 'raise HTTPException(' sites."""
        import importlib
        import inspect

        mod = importlib.import_module(module_path)
        source = inspect.getsource(mod)
        assert "raise HTTPException(" not in source, (
            f"{module_path} still has 'raise HTTPException(' -- Domain III incomplete"
        )
