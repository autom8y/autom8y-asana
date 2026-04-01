"""API middleware for request ID and structured logging.

This module provides middleware for:
- Request ID generation and header injection
- Structured logging of all HTTP requests with PAT filtering

Per TDD-ASANA-SATELLITE (FR-SVC-002, FR-SVC-003):
- Request ID middleware adds unique ID to each request
- Request logging middleware logs all requests

Per PRD-ASANA-SATELLITE (FR-AUTH-004):
- PAT is not logged or persisted
- Structlog filter on "authorization", "token", "pat" fields

Per NFR-OBS-001:
- X-Request-ID on 100% of responses
"""

import time
import uuid
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from autom8_asana.core.logging import get_logger

# Threshold for slow request warnings (milliseconds)
SLOW_REQUEST_THRESHOLD_MS = 1000

# Fields to filter from logs (security: never log PAT values)
SENSITIVE_FIELDS = frozenset({"authorization", "token", "pat", "password", "secret"})


def _filter_sensitive_data(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor to filter sensitive fields.

    Per PRD-ASANA-SATELLITE (FR-AUTH-004): PAT values must never appear in logs.

    Args:
        _logger: Logger instance (unused).
        _method_name: Logging method name (unused).
        event_dict: Log event dictionary to filter.

    Returns:
        Filtered event dictionary with sensitive values redacted.
    """
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(field in key_lower for field in SENSITIVE_FIELDS):
            event_dict[key] = "[REDACTED]"
    return event_dict


# Get logger via SDK
logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request_id to request.state and response headers.

    Per TDD-ASANA-SATELLITE (FR-SVC-002):
    - Generates a 16-character UUID hex for each request
    - Enables request tracing and correlation in logs

    Per NFR-OBS-001:
    - X-Request-ID header on 100% of responses

    Rationale for 16 chars (64 bits):
    - 8 chars (32 bits): 50% collision after ~65,000 requests
    - 16 chars (64 bits): 50% collision after ~4 billion requests
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request and add request_id.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response with X-Request-ID header.
        """
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured logging middleware for request/response tracking.

    Per TDD-ASANA-SATELLITE (FR-SVC-003):
    - Logs all requests with method, path, status, duration
    - Integrates with RequestIDMiddleware for correlation

    Log Levels:
        - INFO: Successful requests (2xx)
        - WARNING: Client errors (4xx) or slow requests (>1s)
        - ERROR: Server errors (5xx)

    Log Fields:
        - request_id: Correlation ID from RequestIDMiddleware
        - method: HTTP method (GET, POST, etc.)
        - path: Request URL path
        - status_code: HTTP response status code
        - duration_ms: Request processing time in milliseconds
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request and response with timing.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response from downstream handler with logging side effect.
        """
        start_time = time.perf_counter()

        # Get request_id from state (set by RequestIDMiddleware)
        request_id: str = getattr(request.state, "request_id", "unknown")

        # Process request through remaining middleware and handlers
        response = await call_next(request)

        # Calculate duration with precision
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build structured log context (no sensitive data)
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }

        # Determine log level based on status code and duration
        if response.status_code >= 500:
            logger.error(  # nosemgrep: autom8y.no-logger-positional-args
                "request_failed", **log_data
            )
        elif response.status_code >= 400:
            logger.warning(  # nosemgrep: autom8y.no-logger-positional-args
                "client_error", **log_data
            )
        elif duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(  # nosemgrep: autom8y.no-logger-positional-args
                "slow_request", **log_data
            )
        else:
            logger.info(  # nosemgrep: autom8y.no-logger-positional-args
                "request_completed", **log_data
            )

        return response


__all__ = [
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "SLOW_REQUEST_THRESHOLD_MS",
    "_filter_sensitive_data",
    "SENSITIVE_FIELDS",
]
