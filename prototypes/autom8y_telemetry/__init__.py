"""autom8y-telemetry POC: Platform primitives for observability.

This is prototype code demonstrating feasibility of extracting
reusable observability patterns from autom8_asana.

Public API:
- init_telemetry(): One-line OpenTelemetry setup
- TelemetryHTTPClient: Auto-instrumented HTTP client
- TokenBucketRateLimiter: Rate limiting primitive
- add_otel_trace_ids: Structlog processor for trace correlation

See README.md for usage examples and documented shortcuts.
"""

from .http_client import TelemetryHTTPClient
from .protocols import (
    LogProviderProtocol,
    RateLimiterProtocol,
    TelemetryHookProtocol,
)
from .rate_limiter import TokenBucketRateLimiter
from .structlog_processor import add_otel_trace_ids
from .telemetry import (
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    init_telemetry,
    start_span,
)

__all__ = [
    # Telemetry initialization
    "init_telemetry",
    "get_tracer",
    "start_span",
    "get_current_trace_id",
    "get_current_span_id",
    # HTTP client
    "TelemetryHTTPClient",
    # Rate limiting
    "TokenBucketRateLimiter",
    # Structlog integration
    "add_otel_trace_ids",
    # Protocols
    "RateLimiterProtocol",
    "TelemetryHookProtocol",
    "LogProviderProtocol",
]
