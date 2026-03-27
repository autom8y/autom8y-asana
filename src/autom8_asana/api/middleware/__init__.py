"""API middleware package.

Re-exports from core module for backward compatibility with existing
imports (e.g., ``from autom8_asana.api.middleware import RequestIDMiddleware``).

Submodules:
    core        -- RequestIDMiddleware, RequestLoggingMiddleware
    idempotency -- IdempotencyMiddleware (RFC 8791)
"""

from .core import (
    SENSITIVE_FIELDS,
    SLOW_REQUEST_THRESHOLD_MS,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    _filter_sensitive_data,
)
from .idempotency import IdempotencyMiddleware

__all__ = [
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "IdempotencyMiddleware",
    "SLOW_REQUEST_THRESHOLD_MS",
    "_filter_sensitive_data",
    "SENSITIVE_FIELDS",
]
