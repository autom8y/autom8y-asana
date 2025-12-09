"""Observability module for autom8_asana SDK.

Provides correlation ID generation, error handling decorator,
and contextual logging for request tracing.

Per TDD-0007 and ADR-0013.
"""

from autom8_asana.observability.correlation import (
    CorrelationContext,
    generate_correlation_id,
)
from autom8_asana.observability.decorators import error_handler

__all__ = [
    "CorrelationContext",
    "error_handler",
    "generate_correlation_id",
]
