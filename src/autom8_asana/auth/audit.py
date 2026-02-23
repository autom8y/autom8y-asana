"""S2S audit logging for autom8_asana.

This module provides structured audit logging for service-to-service
requests, ensuring all S2S operations are tracked without exposing
sensitive credentials.

Per ADR-S2S-005:
- Structured JSON format for CloudWatch Logs Insights
- request_id for cross-service correlation
- No credential material (tokens, PATs) in logs
- INFO level for successful operations

Per FR-AUDIT-001, FR-AUDIT-002:
- Log caller_service, auth_mode, endpoint, status_code, duration_ms
- Never log token values or authorization headers
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.api.dependencies import (
        AuthContext,
    )  # nosemgrep: autom8y.no-lower-imports-api

logger = get_logger("autom8_asana.audit")


@dataclass(frozen=True, slots=True)
class S2SAuditEntry:
    """Immutable audit log entry for S2S requests.

    All fields are safe to log (no credentials).

    Attributes:
        event: Event type identifier
        timestamp: ISO 8601 timestamp in UTC
        request_id: Request correlation ID
        auth_mode: Authentication mode (jwt or pat)
        caller_service: Service name from JWT claims (None for PAT)
        endpoint: API endpoint path
        method: HTTP method
        response_status: HTTP response status code
        duration_ms: Request duration in milliseconds
    """

    event: str
    timestamp: str
    request_id: str
    auth_mode: str
    caller_service: str | None
    endpoint: str
    method: str
    response_status: int
    duration_ms: float

    def to_dict(self, *, include_event: bool = True) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Args:
            include_event: Whether to include the event field. Set to False
                when unpacking as **kwargs to a logger method that takes
                event as a positional argument.

        Returns:
            Dictionary with all non-None fields.
        """
        result: dict[str, Any] = {
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "auth_mode": self.auth_mode,
            "endpoint": self.endpoint,
            "method": self.method,
            "response_status": self.response_status,
            "duration_ms": round(self.duration_ms, 2),
        }
        if include_event:
            result["event"] = self.event
        if self.caller_service is not None:
            result["caller_service"] = self.caller_service
        return result

    def to_json(self) -> str:
        """Serialize to JSON string for CloudWatch.

        Returns:
            Compact JSON string.
        """
        return json.dumps(self.to_dict(), separators=(",", ":"))


class S2SAuditLogger:
    """Audit logger for S2S requests.

    Thread-safe logger that produces structured JSON audit entries
    for all S2S operations.

    Example:
        audit = S2SAuditLogger()
        start = audit.start_timer()

        # ... process request ...

        audit.log_request(
            request_id="abc123",
            auth_context=auth_context,
            endpoint="/api/v1/dataframes/project/123",
            method="GET",
            status=200,
            start_time=start,
        )
    """

    # Event type for S2S request logging
    EVENT_S2S_REQUEST = "s2s_request"

    def __init__(self) -> None:
        """Initialize the audit logger."""
        self._logger = logger

    @staticmethod
    def start_timer() -> float:
        """Start a timer for measuring request duration.

        Returns:
            Start time in seconds (monotonic clock).
        """
        return time.perf_counter()

    @staticmethod
    def _calculate_duration_ms(start_time: float) -> float:
        """Calculate duration in milliseconds from start time.

        Args:
            start_time: Start time from start_timer()

        Returns:
            Duration in milliseconds.
        """
        return (time.perf_counter() - start_time) * 1000

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO 8601 format.

        Returns:
            ISO 8601 timestamp with UTC timezone (Z suffix).
        """
        return (
            datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )

    def log_request(
        self,
        request_id: str,
        auth_context: AuthContext,
        endpoint: str,
        method: str,
        status: int,
        start_time: float,
    ) -> S2SAuditEntry:
        """Log an S2S request.

        Creates a structured audit log entry and emits it to the
        configured logger. Only logs S2S (JWT) requests by default.

        Per ADR-S2S-005:
        - Uses INFO level for successful operations
        - Uses WARNING level for failures (4xx/5xx)
        - Never includes credential material

        Args:
            request_id: Request correlation ID
            auth_context: Authentication context with mode and claims
            endpoint: API endpoint path (may include path parameters)
            method: HTTP method (GET, POST, etc.)
            status: HTTP response status code
            start_time: Timer start from start_timer()

        Returns:
            The created audit entry (for testing).
        """
        duration_ms = self._calculate_duration_ms(start_time)

        entry = S2SAuditEntry(
            event=self.EVENT_S2S_REQUEST,
            timestamp=self._get_timestamp(),
            request_id=request_id,
            auth_mode=auth_context.mode.value,
            caller_service=auth_context.caller_service,
            endpoint=endpoint,
            method=method,
            response_status=status,
            duration_ms=duration_ms,
        )

        # Emit structured log using appropriate level
        # Use include_event=False since event is passed as positional arg
        if status >= 400:
            self._logger.warning("s2s_request", **entry.to_dict(include_event=False))
        else:
            self._logger.info("s2s_request", **entry.to_dict(include_event=False))

        return entry

    def log_jwt_only(
        self,
        request_id: str,
        auth_context: AuthContext,
        endpoint: str,
        method: str,
        status: int,
        start_time: float,
    ) -> S2SAuditEntry | None:
        """Log only S2S (JWT) requests, skip PAT requests.

        This is the preferred method for route handlers that want
        to log S2S calls but not clutter logs with user PAT calls.

        Args:
            request_id: Request correlation ID
            auth_context: Authentication context with mode and claims
            endpoint: API endpoint path
            method: HTTP method
            status: HTTP response status code
            start_time: Timer start from start_timer()

        Returns:
            The created audit entry for JWT requests, None for PAT.
        """
        from autom8_asana.auth.dual_mode import AuthMode

        if auth_context.mode != AuthMode.JWT:
            return None

        return self.log_request(
            request_id=request_id,
            auth_context=auth_context,
            endpoint=endpoint,
            method=method,
            status=status,
            start_time=start_time,
        )


# Module-level singleton for convenience
_audit_logger: S2SAuditLogger | None = None


def get_audit_logger() -> S2SAuditLogger:
    """Get the S2S audit logger singleton.

    Returns:
        S2SAuditLogger instance.
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = S2SAuditLogger()
    return _audit_logger


def reset_audit_logger() -> None:
    """Reset the audit logger singleton (for testing)."""
    global _audit_logger
    _audit_logger = None


__all__ = [
    "S2SAuditEntry",
    "S2SAuditLogger",
    "get_audit_logger",
    "reset_audit_logger",
]
