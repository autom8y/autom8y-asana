"""Structlog processor for OpenTelemetry trace ID injection.

This is prototype code - demonstrates log/trace correlation.
Production version would live in autom8y_telemetry package.

SHORTCUTS TAKEN (see README.md):
- Minimal error handling
- No configuration options
- Basic implementation only
"""

from __future__ import annotations

from typing import Any

from opentelemetry import trace


def add_otel_trace_ids(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor to inject OpenTelemetry trace/span IDs.

    Automatically adds trace_id and span_id to all log events
    when inside an active trace context.

    Args:
        logger: Structlog logger instance (unused)
        method_name: Log method name (unused)
        event_dict: Event dictionary to be logged

    Returns:
        Modified event_dict with trace_id and span_id added

    Example:
        >>> import structlog
        >>> from autom8y_telemetry import add_otel_trace_ids, init_telemetry
        >>>
        >>> # Configure structlog
        >>> structlog.configure(
        ...     processors=[
        ...         add_otel_trace_ids,
        ...         structlog.dev.ConsoleRenderer(),
        ...     ]
        ... )
        >>>
        >>> # Initialize telemetry
        >>> init_telemetry("my-service")
        >>>
        >>> # Logs will now include trace_id/span_id when in span context
        >>> log = structlog.get_logger()
        >>> with start_span("operation"):
        ...     log.info("processing_item", item_id=123)
        ...     # Output includes: trace_id=... span_id=... item_id=123
    """
    span = trace.get_current_span()

    if span and span.get_span_context().is_valid:
        span_context = span.get_span_context()

        # Format IDs as hex strings (standard format)
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")

    return event_dict
