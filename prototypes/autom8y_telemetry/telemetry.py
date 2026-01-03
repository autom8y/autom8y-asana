"""OpenTelemetry initialization and context management.

This is prototype code - demonstrates OTel integration pattern.
Production version would live in autom8y_telemetry package.

SHORTCUTS TAKEN (see README.md):
- Console exporter only (no OTLP)
- Hardcoded configuration (no env vars)
- Minimal error handling
- No resource attributes beyond service.name
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# Global tracer instance
_tracer: trace.Tracer | None = None


def init_telemetry(service_name: str = "autom8y-telemetry-poc") -> trace.Tracer:
    """Initialize OpenTelemetry tracing with console exporter.

    One-line setup for basic distributed tracing.

    Args:
        service_name: Service name for trace identification

    Returns:
        Configured tracer instance

    Example:
        >>> from autom8y_telemetry import init_telemetry
        >>> tracer = init_telemetry("my-service")
        >>> with tracer.start_as_current_span("operation"):
        ...     # Work happens here
        ...     pass
    """
    global _tracer

    # Create resource with service name
    resource = Resource(attributes={
        "service.name": service_name,
    })

    # Create tracer provider with resource
    provider = TracerProvider(resource=resource)

    # Add console exporter for POC (production would use OTLP)
    console_exporter = ConsoleSpanExporter()
    span_processor = BatchSpanProcessor(console_exporter)
    provider.add_span_processor(span_processor)

    # Set as global provider
    trace.set_tracer_provider(provider)

    # Create and cache tracer
    _tracer = trace.get_tracer(__name__)

    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance.

    Returns:
        Configured tracer

    Raises:
        RuntimeError: If init_telemetry() hasn't been called yet
    """
    if _tracer is None:
        raise RuntimeError("Telemetry not initialized. Call init_telemetry() first.")
    return _tracer


@contextmanager
def start_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Iterator[trace.Span]:
    """Start a new span in the current trace context.

    Convenience wrapper around tracer.start_as_current_span.

    Args:
        name: Span name (operation being traced)
        attributes: Optional attributes to attach to span

    Yields:
        Active span

    Example:
        >>> with start_span("database_query", {"query": "SELECT ..."}) as span:
        ...     result = execute_query()
        ...     span.set_attribute("rows_returned", len(result))
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def get_current_trace_id() -> str | None:
    """Get the trace ID from current span context.

    Returns:
        Trace ID as hex string, or None if no active span

    Example:
        >>> with start_span("operation"):
        ...     trace_id = get_current_trace_id()
        ...     print(f"Trace ID: {trace_id}")
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """Get the span ID from current span context.

    Returns:
        Span ID as hex string, or None if no active span

    Example:
        >>> with start_span("operation"):
        ...     span_id = get_current_span_id()
        ...     print(f"Span ID: {span_id}")
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return None
