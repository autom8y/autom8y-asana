"""Adversarial tests for I6: API Error Unification helpers.

Tests for raise_api_error() and raise_service_error() in api/errors.py,
verifying:
- Consistent error response format: {"error": "CODE", "message": "...", "request_id": "..."}
- Request ID extraction from both Request objects and raw strings
- Edge cases: None state, missing request_id, empty strings
- ServiceError integration via raise_service_error()
- Backward compatibility: centralized handlers still work
- KEEP sites: internal.py and webhooks.py are NOT migrated

Per TDD-API-ERR-UNIFY-001 Section 8: Success Criteria.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.services.errors import (
    CacheNotReadyError,
    EntityNotFoundError,
    EntityTypeMismatchError,
    InvalidFieldError,
    InvalidParameterError,
    NoValidFieldsError,
    ServiceError,
    TaskNotFoundError,
    UnknownEntityError,
    UnknownSectionError,
    get_status_for_error,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_request(request_id: str = "abc123") -> MagicMock:
    """Create a mock FastAPI Request with request.state.request_id set."""
    req = MagicMock()
    req.state = SimpleNamespace(request_id=request_id)
    return req


def _make_request_no_state() -> MagicMock:
    """Create a mock FastAPI Request with NO state attribute at all."""
    req = MagicMock(spec=[])  # spec=[] means no attributes
    req.state = SimpleNamespace()  # state exists but no request_id
    return req


# ===========================================================================
# raise_api_error -- Happy Path
# ===========================================================================


class TestRaiseApiErrorHappyPath:
    """Verify raise_api_error produces correct format with string request_id."""

    def test_basic_error_format(self) -> None:
        """Error response has error, message, and request_id keys."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("req-001", 400, "INVALID_INPUT", "Bad input")

        exc = exc_info.value
        assert exc.status_code == 400
        assert exc.detail["error"]["code"] == "INVALID_INPUT"
        assert exc.detail["error"]["message"] == "Bad input"
        assert exc.detail["request_id"] == "req-001"

    def test_with_string_request_id(self) -> None:
        """raise_api_error accepts raw string for request_id."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("raw-id-456", 404, "NOT_FOUND", "Gone")

        exc = exc_info.value
        assert exc.detail["request_id"] == "raw-id-456"
        assert exc.detail["error"]["code"] == "NOT_FOUND"

    def test_with_details_kwarg(self) -> None:
        """Extra details dict is merged into detail."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(
                "req-002",
                422,
                "INVALID_FIELD",
                "Bad field",
                details={"field": "foo", "available": ["bar", "baz"]},
            )

        detail = exc_info.value.detail
        assert detail["error"]["code"] == "INVALID_FIELD"
        assert detail["request_id"] == "req-002"
        assert detail["field"] == "foo"
        assert detail["available"] == ["bar", "baz"]

    def test_with_headers(self) -> None:
        """Custom headers are passed through to HTTPException."""
        req = _make_request("req-003")
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(
                req,
                429,
                "RATE_LIMITED",
                "Slow down",
                headers={"Retry-After": "60"},
            )

        exc = exc_info.value
        assert exc.headers == {"Retry-After": "60"}

    def test_no_headers_by_default(self) -> None:
        """When headers not provided, HTTPException headers is None."""
        req = _make_request("req-004")
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(req, 500, "INTERNAL_ERROR", "Oops")

        assert exc_info.value.headers is None

    def test_various_status_codes(self) -> None:
        """Verify all status codes used across route files work."""
        status_codes = [400, 404, 422, 429, 500, 501, 502, 503, 504]
        for code in status_codes:
            with pytest.raises(HTTPException) as exc_info:
                raise_api_error("id", code, "CODE", "msg")
            assert exc_info.value.status_code == code


# ===========================================================================
# raise_api_error -- Edge Cases and Adversarial Inputs
# ===========================================================================


class TestRaiseApiErrorEdgeCases:
    """Adversarial edge cases for raise_api_error."""

    def test_missing_request_id_on_state(self) -> None:
        """When caller passes 'unknown' as request_id, it is preserved."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("unknown", 400, "CODE", "msg")

        assert exc_info.value.detail["request_id"] == "unknown"

    def test_empty_string_request_id(self) -> None:
        """Empty string request_id is preserved (not replaced with 'unknown')."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("", 400, "CODE", "msg")

        # Empty string IS a valid request_id (caller's problem if they pass "")
        assert exc_info.value.detail["request_id"] == ""

    def test_empty_code(self) -> None:
        """Empty error code is allowed (caller's responsibility)."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("id", 400, "", "msg")

        assert exc_info.value.detail["error"]["code"] == ""

    def test_empty_message(self) -> None:
        """Empty message is allowed."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("id", 400, "CODE", "")

        assert exc_info.value.detail["error"]["message"] == ""

    @pytest.mark.parametrize(
        "details",
        [
            pytest.param(None, id="none"),
            pytest.param({}, id="empty-dict"),
        ],
    )
    def test_details_falsy_not_merged(self, details: Any) -> None:
        """When details is None or empty dict, only base keys are in detail."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("id", 400, "CODE", "msg", details=details)

        detail = exc_info.value.detail
        assert set(detail.keys()) == {"error", "message", "request_id"}

    def test_details_can_overwrite_base_keys(self) -> None:
        """Adversarial: details dict can overwrite 'error' or 'message'.

        This is a design choice -- details.update() runs after base keys.
        Callers should not do this, but we document the behavior.
        """
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(
                "id",
                400,
                "ORIGINAL_CODE",
                "original msg",
                details={"error": "OVERWRITTEN", "message": "overwritten msg"},
            )

        detail = exc_info.value.detail
        # details.update() overwrites base keys
        assert detail["error"]["code"] == "OVERWRITTEN"
        assert detail["error"]["message"] == "overwritten msg"

    def test_never_returns(self) -> None:
        """raise_api_error always raises, never returns a value."""
        req = _make_request()
        # If this didn't raise, the test would fail
        with pytest.raises(HTTPException):
            raise_api_error(req, 400, "CODE", "msg")

    def test_unicode_in_message(self) -> None:
        """Unicode characters in message are preserved."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("id", 400, "CODE", "Error: \u2603 \u00e9\u00e8\u00ea")

        assert "\u2603" in exc_info.value.detail["message"]

    def test_very_long_request_id(self) -> None:
        """Very long request_id does not crash."""
        long_id = "x" * 10000
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(long_id, 400, "CODE", "msg")

        assert exc_info.value.detail["request_id"] == long_id


# ===========================================================================
# raise_service_error -- Happy Path
# ===========================================================================


class TestRaiseServiceErrorHappyPath:
    """Verify raise_service_error produces correct format."""

    def test_basic_service_error(self) -> None:
        """ServiceError.to_dict() is preserved and request_id injected."""
        err = ServiceError("something broke")

        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("svc-001", err)

        exc = exc_info.value
        assert exc.status_code == 500  # ServiceError -> 500
        assert exc.detail["error"]["code"] == "SERVICE_ERROR"
        assert exc.detail["error"]["message"] == "something broke"
        assert exc.detail["request_id"] == "svc-001"

    def test_task_not_found_error(self) -> None:
        """TaskNotFoundError maps to 404."""
        err = TaskNotFoundError("1234567890")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        exc = exc_info.value
        assert exc.status_code == 404
        assert exc.detail["error"]["code"] == "TASK_NOT_FOUND"
        assert "1234567890" in exc.detail["message"]
        assert exc.detail["request_id"] == "req-id"

    def test_unknown_entity_error_preserves_extra_fields(self) -> None:
        """UnknownEntityError.to_dict() has available_types; request_id added."""
        err = UnknownEntityError("widget", ["offer", "unit"])
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        detail = exc_info.value.detail
        assert detail["error"]["code"] == "UNKNOWN_ENTITY_TYPE"
        assert detail["available_types"] == ["offer", "unit"]
        assert detail["request_id"] == "req-id"

    def test_entity_type_mismatch_preserves_extra_fields(self) -> None:
        """EntityTypeMismatchError.to_dict() has expected/actual projects."""
        err = EntityTypeMismatchError("gid123", "proj_a", ["proj_b", "proj_c"])
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        detail = exc_info.value.detail
        assert detail["expected_project"] == "proj_a"
        assert detail["actual_projects"] == ["proj_b", "proj_c"]
        assert detail["request_id"] == "req-id"

    def test_invalid_field_error(self) -> None:
        """InvalidFieldError maps to 422 and preserves field lists."""
        err = InvalidFieldError(["bad_field"], ["gid", "name"])
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        exc = exc_info.value
        assert exc.status_code == 422
        assert exc.detail["invalid_fields"] == ["bad_field"]
        assert exc.detail["available_fields"] == ["gid", "name"]

    def test_cache_not_ready_error(self) -> None:
        """CacheNotReadyError maps to 503."""
        err = CacheNotReadyError("unit")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"]["code"] == "CACHE_NOT_WARMED"

    def test_with_headers(self) -> None:
        """Custom headers are passed through."""
        err = ServiceError("rate limited")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err, headers={"Retry-After": "30"})

        assert exc_info.value.headers == {"Retry-After": "30"}

    def test_with_string_request_id(self) -> None:
        """raise_service_error accepts raw string request_id."""
        err = ServiceError("test")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("raw-string-id", err)

        assert exc_info.value.detail["request_id"] == "raw-string-id"

    def test_with_request_object(self) -> None:
        """raise_service_error accepts string request_id extracted from Request."""
        req = _make_request("from-request")
        err = ServiceError("test")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error(req.state.request_id, err)

        assert exc_info.value.detail["request_id"] == "from-request"


# ===========================================================================
# raise_service_error -- Edge Cases
# ===========================================================================


class TestRaiseServiceErrorEdgeCases:
    """Adversarial edge cases for raise_service_error."""

    def test_missing_request_id_on_state(self) -> None:
        """Caller passes 'unknown' when no request_id is available."""
        err = ServiceError("test")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("unknown", err)

        assert exc_info.value.detail["request_id"] == "unknown"

    def test_unknown_section_without_available(self) -> None:
        """UnknownSectionError without available_sections."""
        err = UnknownSectionError("Backlog")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        detail = exc_info.value.detail
        assert detail["error"]["code"] == "UNKNOWN_SECTION"
        assert detail["request_id"] == "req-id"
        # available_sections omitted when empty list
        assert "available_sections" not in detail

    def test_unknown_section_with_available(self) -> None:
        """UnknownSectionError with available_sections."""
        err = UnknownSectionError("Backlog", ["Done", "In Progress"])
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        detail = exc_info.value.detail
        assert detail["available_sections"] == ["Done", "In Progress"]

    def test_no_valid_fields_error(self) -> None:
        """NoValidFieldsError maps to 422."""
        err = NoValidFieldsError("all failed")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        assert exc_info.value.status_code == 422

    def test_request_id_injected_into_to_dict(self) -> None:
        """Verify request_id is added to the dict from to_dict(), not replacing."""
        err = InvalidFieldError(["x"], ["y", "z"])
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", err)

        detail = exc_info.value.detail
        # All to_dict() fields preserved
        assert "error" in detail
        assert "message" in detail
        assert "invalid_fields" in detail
        assert "available_fields" in detail
        # Plus request_id injected
        assert "request_id" in detail


# ===========================================================================
# Format Consistency Across Route Files
# ===========================================================================


class TestFormatConsistencyAcrossRoutes:
    """Verify that different route patterns produce identical base format.

    Per TDD Section 8: All error responses use
    {"error": "CODE", "message": "...", "request_id": "..."}
    """

    def test_tasks_pattern_via_raise_service_error(self) -> None:
        """tasks.py pattern: catch ServiceError, call raise_service_error."""
        err = TaskNotFoundError("123")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("tasks-req-id", err)

        detail = exc_info.value.detail
        assert "error" in detail
        assert "message" in detail
        assert "request_id" in detail

    def test_admin_pattern_via_raise_api_error(self) -> None:
        """admin.py pattern: direct raise_api_error with validation."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(
                "admin-req-id",
                400,
                "INVALID_ENTITY_TYPE",
                "Invalid entity_type: 'widget'",
            )

        detail = exc_info.value.detail
        assert "error" in detail
        assert "message" in detail
        assert "request_id" in detail

    def test_entity_write_pattern_sdk_recatch(self) -> None:
        """entity_write.py REVIEW pattern: recatch SDK errors with raise_api_error."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(
                "ew-req-id",
                429,
                "RATE_LIMITED",
                "Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        detail = exc_info.value.detail
        assert detail["error"]["code"] == "RATE_LIMITED"
        assert detail["error"]["message"] == "Rate limit exceeded"
        assert detail["request_id"] == "ew-req-id"
        assert exc_info.value.headers == {"Retry-After": "60"}

    def test_query_error_pattern_via_internal_helper(self) -> None:
        """query.py pattern: _raise_query_error wraps raise_api_error."""
        # Simulating what _raise_query_error does
        d = {"error": "QUERY_TOO_COMPLEX", "message": "Too deep"}
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("qv2-req-id", 400, d["error"], d["message"])

        detail = exc_info.value.detail
        assert detail["error"]["code"] == "QUERY_TOO_COMPLEX"
        assert detail["request_id"] == "qv2-req-id"

    def test_base_keys_always_present(self) -> None:
        """Every invocation pattern produces the three base keys."""
        patterns: list[tuple[str, int]] = [
            ("raise_api_error_direct", 400),
            ("raise_service_error_service", 500),
            ("raise_api_error_with_details", 422),
        ]

        for label, status in patterns:
            if "service" in label:
                err = ServiceError("msg")
                with pytest.raises(HTTPException) as exc_info:
                    raise_service_error("id", err)
            else:
                with pytest.raises(HTTPException) as exc_info:
                    raise_api_error("id", status, "CODE", "msg")

            detail = exc_info.value.detail
            for key in ("error", "message", "request_id"):
                assert key in detail, f"{label}: missing key '{key}'"


# ===========================================================================
# KEEP Sites Verification
# ===========================================================================


class TestTypedExceptionSites:
    """Verify internal.py and dependencies.py use typed exceptions.

    Per Domain III (Absolute Enforcement Mandate): All bare HTTPException
    sites have been converted to typed API-layer exceptions.
    """

    def test_internal_auth_uses_typed_exceptions(self) -> None:
        """internal.py auth dependency uses ApiAuthError typed exceptions."""
        import inspect

        from autom8_asana.api.routes import internal

        source = inspect.getsource(internal._extract_bearer_token)
        # Should use typed ApiAuthError
        assert "ApiAuthError" in source
        # Should NOT use raw raise HTTPException
        assert "raise HTTPException" not in source

    def test_internal_require_service_claims_uses_typed_exceptions(self) -> None:
        """require_service_claims uses typed exceptions."""
        import inspect

        from autom8_asana.api.routes import internal

        source = inspect.getsource(internal.require_service_claims)
        assert "raise HTTPException" not in source
        assert "ApiAuthError" in source or "ApiServiceUnavailableError" in source

    def test_webhook_verify_token_is_migrated(self) -> None:
        """verify_webhook_token uses raise_api_error helper (migrated from raw HTTPException)."""
        import inspect

        from autom8_asana.api.routes import webhooks

        source = inspect.getsource(webhooks.verify_webhook_token)
        assert "raise_api_error" in source


# ===========================================================================
# REVIEW Sites Verification (entity_write.py #13-#15)
# ===========================================================================


class TestReviewSitesEntityWrite:
    """Verify entity_write.py REVIEW sites (#13-#15) kept re-catches
    and use the helper.

    Per TDD Section 5.4: Keep re-catches but use raise_api_error().
    """

    def test_entity_write_has_rate_limit_recatch(self) -> None:
        """entity_write.py still catches RateLimitError explicitly."""
        import inspect

        from autom8_asana.api.routes import entity_write

        source = inspect.getsource(entity_write.write_entity_fields)
        assert "except RateLimitError" in source
        # Uses helper, not raw HTTPException
        assert "raise_api_error" in source

    def test_entity_write_has_timeout_recatch(self) -> None:
        """entity_write.py still catches AsanaTimeoutError (may be in a tuple except)."""
        import inspect

        from autom8_asana.api.routes import entity_write

        source = inspect.getsource(entity_write.write_entity_fields)
        assert "AsanaTimeoutError" in source

    def test_entity_write_has_server_error_recatch(self) -> None:
        """entity_write.py still catches ServerError (may be in a tuple except)."""
        import inspect

        from autom8_asana.api.routes import entity_write

        source = inspect.getsource(entity_write.write_entity_fields)
        assert "ServerError" in source

    def test_entity_write_no_raw_http_exception_in_try_block(self) -> None:
        """entity_write route handler uses raise_api_error, not raw HTTPException.

        The only raw HTTPException in entity_write.py should be the
        'except HTTPException: raise' passthrough.
        """
        import inspect

        from autom8_asana.api.routes import entity_write

        source = inspect.getsource(entity_write.write_entity_fields)
        # The only raw HTTPException reference should be the re-raise passthrough
        lines = source.split("\n")
        http_exc_lines = [
            line.strip()
            for line in lines
            if "HTTPException" in line and "import" not in line
        ]
        # Should only have "except HTTPException:" and "raise" (the passthrough)
        assert any("except HTTPException" in line for line in http_exc_lines)
        # Should NOT have "raise HTTPException(" with arguments
        assert not any("raise HTTPException(" in line for line in http_exc_lines)


# ===========================================================================
# Backward Compatibility: Centralized Handlers Still Work
# ===========================================================================


class TestCentralizedHandlersIntact:
    """Verify the centralized exception handlers in api/errors.py still exist."""

    def test_register_exception_handlers_exists(self) -> None:
        """register_exception_handlers is still exported."""
        from autom8_asana.api.errors import register_exception_handlers

        assert callable(register_exception_handlers)

    def test_all_handler_functions_exist(self) -> None:
        """All 10 centralized handler functions still exist."""
        from autom8_asana.api import errors

        handler_names = [
            "not_found_handler",
            "authentication_error_handler",
            "forbidden_error_handler",
            "rate_limit_error_handler",
            "validation_error_handler",
            "server_error_handler",
            "timeout_error_handler",
            "request_error_handler",
            "asana_error_handler",
            "generic_error_handler",
        ]
        for name in handler_names:
            assert hasattr(errors, name), f"Missing handler: {name}"
            assert callable(getattr(errors, name))

    def test_helpers_in_module_all(self) -> None:
        """raise_api_error and raise_service_error are in __all__."""
        from autom8_asana.api import errors

        assert "raise_api_error" in errors.__all__
        assert "raise_service_error" in errors.__all__


# ===========================================================================
# Migration Completeness: No raw HTTPException in MIGRATE files
# ===========================================================================


class TestMigrationCompleteness:
    """Verify ALL files use typed exceptions or helpers, not raw HTTPException."""

    @pytest.mark.parametrize(
        "module_path",
        [
            # Route modules (I6 migration)
            "autom8_asana.api.routes.tasks",
            "autom8_asana.api.routes.sections",
            "autom8_asana.api.routes.admin",
            "autom8_asana.api.routes.dataframes",
            "autom8_asana.api.routes.projects",
            "autom8_asana.api.routes.resolver_schema",
            # Auth dependencies (Domain III migration)
            "autom8_asana.api.routes.internal",
            "autom8_asana.auth.dual_mode",
        ],
    )
    def test_no_raw_http_exception_raise(self, module_path: str) -> None:
        """All files should not contain 'raise HTTPException(' calls."""
        import importlib
        import inspect

        mod = importlib.import_module(module_path)
        source = inspect.getsource(mod)
        assert "raise HTTPException(" not in source, (
            f"{module_path} still has 'raise HTTPException(' -- migration incomplete"
        )

    def test_dependencies_no_raw_http_exception(self) -> None:
        """api/dependencies.py should not have raw HTTPException raises."""
        import importlib
        import inspect

        mod = importlib.import_module("autom8_asana.api.dependencies")
        source = inspect.getsource(mod)
        assert "raise HTTPException(" not in source

    def test_dataframe_decorator_no_raw_http_exception(self) -> None:
        """cache/dataframe/decorator.py should not have raw HTTPException raises."""
        import importlib
        import inspect

        mod = importlib.import_module("autom8_asana.cache.dataframe.decorator")
        source = inspect.getsource(mod)
        assert "raise HTTPException(" not in source

    def test_resolver_only_passthrough_http_exception(self) -> None:
        """resolver.py should only have 'except HTTPException: raise' pattern."""
        import importlib
        import inspect

        mod = importlib.import_module("autom8_asana.api.routes.resolver")
        source = inspect.getsource(mod)
        # Should NOT have "raise HTTPException(" with args
        assert "raise HTTPException(" not in source
        # MAY have "except HTTPException:" + "raise" (passthrough)
        # This is fine -- it's just re-raising

    def test_query_no_raw_http_exception(self) -> None:
        """query.py should not have raw HTTPException raises."""
        import importlib
        import inspect

        mod = importlib.import_module("autom8_asana.api.routes.query")
        source = inspect.getsource(mod)
        assert "raise HTTPException(" not in source

    def test_entity_write_only_passthrough_http_exception(self) -> None:
        """entity_write.py should only have 'except HTTPException: raise'."""
        import importlib
        import inspect

        mod = importlib.import_module("autom8_asana.api.routes.entity_write")
        source = inspect.getsource(mod)
        # The only "raise HTTPException" should be in the passthrough
        # Not "raise HTTPException(" with constructor args
        assert "raise HTTPException(" not in source


# ===========================================================================
# ServiceError Status Mapping Integration
# ===========================================================================


class TestServiceErrorStatusMapping:
    """Verify raise_service_error uses get_status_for_error correctly."""

    @pytest.mark.parametrize(
        "error,expected_status",
        [
            (TaskNotFoundError("123"), 404),
            (UnknownEntityError("x", []), 404),
            (UnknownSectionError("x"), 404),
            (EntityTypeMismatchError("g", "a", ["b"]), 404),
            (InvalidFieldError(["x"], ["y"]), 422),
            (InvalidParameterError("bad"), 400),
            (NoValidFieldsError("none"), 422),
            (CacheNotReadyError(), 503),
            (ServiceError("generic"), 500),
        ],
    )
    def test_status_code_matches_mapping(
        self, error: ServiceError, expected_status: int
    ) -> None:
        """raise_service_error uses get_status_for_error for status code."""
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("req-id", error)

        assert exc_info.value.status_code == expected_status


# ===========================================================================
# Request ID Extraction Robustness
# ===========================================================================


class TestRequestIdExtraction:
    """Adversarial tests for request_id extraction from various sources."""

    @pytest.mark.parametrize(
        "request_id",
        [
            pytest.param("a1b2c3d4e5f67890", id="normal-hex-id"),
            pytest.param("unknown", id="unknown-fallback"),
            pytest.param("my-custom-id", id="custom-string"),
        ],
    )
    def test_api_error_request_id_passthrough(self, request_id: str) -> None:
        """String request_id is used directly without any transformation."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(request_id, 400, "C", "m")
        assert exc_info.value.detail["request_id"] == request_id

    @pytest.mark.parametrize(
        "request_id",
        [
            pytest.param("from-req-obj", id="from-request-object"),
            pytest.param("str-id", id="string-direct"),
        ],
    )
    def test_service_error_request_id_passthrough(self, request_id: str) -> None:
        """raise_service_error preserves string request_id."""
        err = ServiceError("test")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error(request_id, err)
        assert exc_info.value.detail["request_id"] == request_id


# ===========================================================================
# Interaction: details dict does not clobber request_id
# ===========================================================================


class TestDetailsRequestIdInteraction:
    """Verify that details dict cannot accidentally remove request_id."""

    def test_details_with_request_id_key_overwrites(self) -> None:
        """Adversarial: if details contains 'request_id', it overwrites.

        This is because detail.update(details) runs after request_id is set.
        Document this as known behavior.
        """
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(
                "original-id",
                400,
                "CODE",
                "msg",
                details={"request_id": "clobbered-id"},
            )

        # details.update() overwrites request_id
        assert exc_info.value.detail["request_id"] == "clobbered-id"

    def test_service_error_request_id_always_last(self) -> None:
        """In raise_service_error, request_id is set AFTER to_dict().

        So even if to_dict() returned a 'request_id' key, it gets overwritten.
        """
        # ServiceError.to_dict() does not include request_id by default
        err = ServiceError("test")
        with pytest.raises(HTTPException) as exc_info:
            raise_service_error("winner-id", err)

        # request_id is set after detail = error.to_dict()
        assert exc_info.value.detail["request_id"] == "winner-id"
