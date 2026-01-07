"""Tests for S2S audit logging.

Per TDD-S2S-001 Section 12.1:
- Audit log entry creation
- Log format validation
- No credential exposure

Per ADR-S2S-005:
- Structured JSON format
- request_id correlation
- No token/PAT values in logs
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from unittest.mock import patch

import pytest

from autom8_asana.auth.audit import (
    S2SAuditEntry,
    S2SAuditLogger,
    get_audit_logger,
    reset_audit_logger,
)
from autom8_asana.auth.dual_mode import AuthMode


class MockAuthContext:
    """Mock AuthContext for testing."""

    def __init__(
        self,
        mode: AuthMode = AuthMode.JWT,
        asana_pat: str = "test_pat",
        caller_service: str | None = "autom8_data",
    ) -> None:
        self.mode = mode
        self.asana_pat = asana_pat
        self.caller_service = caller_service


class TestS2SAuditEntry:
    """Tests for S2SAuditEntry dataclass."""

    def test_entry_creation(self) -> None:
        """Entry contains all expected fields."""
        # Arrange & Act
        entry = S2SAuditEntry(
            event="s2s_request",
            timestamp="2025-12-23T10:00:00.000Z",
            request_id="abc123",
            auth_mode="jwt",
            caller_service="autom8_data",
            endpoint="/api/v1/dataframes/project/123",
            method="GET",
            response_status=200,
            duration_ms=1234.56,
        )

        # Assert
        assert entry.event == "s2s_request"
        assert entry.timestamp == "2025-12-23T10:00:00.000Z"
        assert entry.request_id == "abc123"
        assert entry.auth_mode == "jwt"
        assert entry.caller_service == "autom8_data"
        assert entry.endpoint == "/api/v1/dataframes/project/123"
        assert entry.method == "GET"
        assert entry.response_status == 200
        assert entry.duration_ms == 1234.56

    def test_entry_to_dict(self) -> None:
        """to_dict() returns dictionary with all fields."""
        # Arrange
        entry = S2SAuditEntry(
            event="s2s_request",
            timestamp="2025-12-23T10:00:00.000Z",
            request_id="abc123",
            auth_mode="jwt",
            caller_service="autom8_data",
            endpoint="/api/v1/test",
            method="GET",
            response_status=200,
            duration_ms=100.5,
        )

        # Act
        result = entry.to_dict()

        # Assert
        assert result["event"] == "s2s_request"
        assert result["request_id"] == "abc123"
        assert result["auth_mode"] == "jwt"
        assert result["caller_service"] == "autom8_data"
        assert result["endpoint"] == "/api/v1/test"
        assert result["method"] == "GET"
        assert result["response_status"] == 200
        assert result["duration_ms"] == 100.5

    def test_entry_to_dict_excludes_none_caller(self) -> None:
        """to_dict() excludes caller_service when None (PAT mode)."""
        # Arrange
        entry = S2SAuditEntry(
            event="s2s_request",
            timestamp="2025-12-23T10:00:00.000Z",
            request_id="abc123",
            auth_mode="pat",
            caller_service=None,
            endpoint="/api/v1/test",
            method="GET",
            response_status=200,
            duration_ms=100.0,
        )

        # Act
        result = entry.to_dict()

        # Assert
        assert "caller_service" not in result
        assert result["auth_mode"] == "pat"

    def test_entry_to_json(self) -> None:
        """to_json() returns valid JSON string."""
        # Arrange
        entry = S2SAuditEntry(
            event="s2s_request",
            timestamp="2025-12-23T10:00:00.000Z",
            request_id="abc123",
            auth_mode="jwt",
            caller_service="autom8_data",
            endpoint="/api/v1/test",
            method="GET",
            response_status=200,
            duration_ms=100.0,
        )

        # Act
        json_str = entry.to_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["event"] == "s2s_request"
        assert parsed["caller_service"] == "autom8_data"

    def test_entry_duration_rounded(self) -> None:
        """Duration is rounded to 2 decimal places."""
        # Arrange
        entry = S2SAuditEntry(
            event="s2s_request",
            timestamp="2025-12-23T10:00:00.000Z",
            request_id="abc123",
            auth_mode="jwt",
            caller_service="autom8_data",
            endpoint="/api/v1/test",
            method="GET",
            response_status=200,
            duration_ms=123.456789,
        )

        # Act
        result = entry.to_dict()

        # Assert
        assert result["duration_ms"] == 123.46

    def test_entry_is_immutable(self) -> None:
        """Entry is frozen dataclass (immutable)."""
        # Arrange
        entry = S2SAuditEntry(
            event="s2s_request",
            timestamp="2025-12-23T10:00:00.000Z",
            request_id="abc123",
            auth_mode="jwt",
            caller_service="autom8_data",
            endpoint="/api/v1/test",
            method="GET",
            response_status=200,
            duration_ms=100.0,
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            entry.event = "modified"  # type: ignore


class TestS2SAuditLogger:
    """Tests for S2SAuditLogger class."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_audit_logger()

    def test_start_timer_returns_float(self) -> None:
        """start_timer() returns a float timestamp."""
        # Arrange
        logger = S2SAuditLogger()

        # Act
        result = logger.start_timer()

        # Assert
        assert isinstance(result, float)
        assert result > 0

    def test_log_request_creates_entry(self) -> None:
        """log_request() creates and returns an entry."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext(mode=AuthMode.JWT, caller_service="autom8_data")
        start_time = logger.start_timer()

        # Act
        entry = logger.log_request(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="GET",
            status=200,
            start_time=start_time,
        )

        # Assert
        assert entry.event == "s2s_request"
        assert entry.request_id == "test123"
        assert entry.auth_mode == "jwt"
        assert entry.caller_service == "autom8_data"
        assert entry.endpoint == "/api/v1/test"
        assert entry.method == "GET"
        assert entry.response_status == 200
        assert entry.duration_ms >= 0

    def test_log_request_uses_auth_mode_value(self) -> None:
        """log_request() uses the AuthMode value string."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext(mode=AuthMode.PAT, caller_service=None)
        start_time = logger.start_timer()

        # Act
        entry = logger.log_request(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="POST",
            status=201,
            start_time=start_time,
        )

        # Assert
        assert entry.auth_mode == "pat"
        assert entry.caller_service is None

    def test_log_request_timestamp_format(self) -> None:
        """log_request() uses ISO 8601 timestamp with Z suffix."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext()
        start_time = logger.start_timer()

        # Act
        entry = logger.log_request(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="GET",
            status=200,
            start_time=start_time,
        )

        # Assert
        # Should end with Z and be parseable
        assert entry.timestamp.endswith("Z")
        # Should be valid ISO format (will raise if invalid)
        datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))

    def test_log_jwt_only_logs_jwt_requests(self) -> None:
        """log_jwt_only() returns entry for JWT mode."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext(mode=AuthMode.JWT, caller_service="autom8_data")
        start_time = logger.start_timer()

        # Act
        entry = logger.log_jwt_only(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="GET",
            status=200,
            start_time=start_time,
        )

        # Assert
        assert entry is not None
        assert entry.auth_mode == "jwt"

    def test_log_jwt_only_skips_pat_requests(self) -> None:
        """log_jwt_only() returns None for PAT mode."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext(mode=AuthMode.PAT, caller_service=None)
        start_time = logger.start_timer()

        # Act
        entry = logger.log_jwt_only(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="GET",
            status=200,
            start_time=start_time,
        )

        # Assert
        assert entry is None


class TestNoCredentialExposure:
    """Tests verifying no credential exposure in logs.

    Per ADR-S2S-005: Never log token values, bot PAT, or any
    credential material.
    """

    def test_entry_does_not_contain_pat(self) -> None:
        """Audit entry never contains PAT values."""
        # Arrange
        sensitive_pat = "0/sensitive_pat_value_should_never_appear"
        auth_context = MockAuthContext(
            mode=AuthMode.JWT,
            asana_pat=sensitive_pat,
            caller_service="autom8_data",
        )
        logger = S2SAuditLogger()
        start_time = logger.start_timer()

        # Act
        entry = logger.log_request(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="GET",
            status=200,
            start_time=start_time,
        )

        # Assert
        json_output = entry.to_json()
        dict_output = entry.to_dict()

        # PAT value should not appear anywhere
        assert sensitive_pat not in json_output
        assert sensitive_pat not in str(dict_output)
        assert "asana_pat" not in json_output
        assert "pat" not in dict_output or dict_output.get("pat") is None

    def test_entry_does_not_expose_authorization_header(self) -> None:
        """Audit entry never contains authorization header values."""
        # Arrange
        auth_context = MockAuthContext(
            mode=AuthMode.JWT,
            asana_pat="secret_value",
            caller_service="autom8_data",
        )
        logger = S2SAuditLogger()
        start_time = logger.start_timer()

        # Act
        entry = logger.log_request(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="GET",
            status=200,
            start_time=start_time,
        )

        # Assert
        json_output = entry.to_json()
        assert "Bearer" not in json_output
        assert "Authorization" not in json_output
        assert "secret_value" not in json_output

    def test_logged_fields_are_safe(self) -> None:
        """Only safe fields are included in log output."""
        # Arrange
        auth_context = MockAuthContext(
            mode=AuthMode.JWT,
            asana_pat="should_not_appear",
            caller_service="autom8_data",
        )
        logger = S2SAuditLogger()
        start_time = logger.start_timer()

        # Act
        entry = logger.log_request(
            request_id="test123",
            auth_context=auth_context,  # type: ignore
            endpoint="/api/v1/test",
            method="GET",
            status=200,
            start_time=start_time,
        )
        dict_output = entry.to_dict()

        # Assert - only these keys should be present
        allowed_keys = {
            "event",
            "timestamp",
            "request_id",
            "auth_mode",
            "caller_service",
            "endpoint",
            "method",
            "response_status",
            "duration_ms",
        }
        assert set(dict_output.keys()).issubset(allowed_keys)


class TestGetAuditLogger:
    """Tests for singleton access."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_audit_logger()

    def test_get_audit_logger_returns_instance(self) -> None:
        """get_audit_logger() returns S2SAuditLogger instance."""
        # Act
        logger = get_audit_logger()

        # Assert
        assert isinstance(logger, S2SAuditLogger)

    def test_get_audit_logger_returns_same_instance(self) -> None:
        """get_audit_logger() returns singleton."""
        # Act
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        # Assert
        assert logger1 is logger2

    def test_reset_clears_singleton(self) -> None:
        """reset_audit_logger() clears the singleton."""
        # Arrange
        logger1 = get_audit_logger()

        # Act
        reset_audit_logger()
        logger2 = get_audit_logger()

        # Assert
        assert logger1 is not logger2


class TestLogLevelSelection:
    """Tests for log level based on response status."""

    def test_success_logs_at_info(self) -> None:
        """200-399 responses log at INFO level."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext()

        with patch.object(logger, "_logger") as mock_logger:
            # Act
            logger.log_request(
                request_id="test123",
                auth_context=auth_context,  # type: ignore
                endpoint="/api/v1/test",
                method="GET",
                status=200,
                start_time=logger.start_timer(),
            )

            # Assert
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.INFO

    def test_client_error_logs_at_warning(self) -> None:
        """4xx responses log at WARNING level."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext()

        with patch.object(logger, "_logger") as mock_logger:
            # Act
            logger.log_request(
                request_id="test123",
                auth_context=auth_context,  # type: ignore
                endpoint="/api/v1/test",
                method="GET",
                status=404,
                start_time=logger.start_timer(),
            )

            # Assert
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.WARNING

    def test_server_error_logs_at_warning(self) -> None:
        """5xx responses log at WARNING level."""
        # Arrange
        logger = S2SAuditLogger()
        auth_context = MockAuthContext()

        with patch.object(logger, "_logger") as mock_logger:
            # Act
            logger.log_request(
                request_id="test123",
                auth_context=auth_context,  # type: ignore
                endpoint="/api/v1/test",
                method="GET",
                status=500,
                start_time=logger.start_timer(),
            )

            # Assert
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.WARNING
