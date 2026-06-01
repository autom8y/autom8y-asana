"""Cold-start logging configuration for Lambda handlers.

Per TDD-LOG-TRACE-LAMBDA: AWS Lambda handlers must emit structured logs that
carry the active OpenTelemetry ``trace_id``/``span_id`` so log lines correlate
with the spans opened by ``@instrument_lambda`` (autom8y_telemetry). They must
also redact substring-matched sensitive fields (``asana_pat``, ``bot_token``,
``client_secret``) that the SDK's default exact-match field filter would leak.

Why this module exists
----------------------
The FastAPI/ECS path wires these processors in ``api.lifespan`` at startup
(``api/lifespan.py``: ``additional_processors=[add_otel_trace_ids,
_filter_sensitive_data]``). The Lambda handlers had no equivalent wiring: the
first ``get_logger`` call auto-configures ``autom8y_log`` with bare
``LogConfig()`` defaults (no trace-id processor, exact-match-only redaction),
so Lambda logs carried neither trace correlation nor substring redaction.

Design constraints (all load-bearing)
-------------------------------------
1. **Import-safety**: ``lambda_handlers/__init__.py`` must remain free of
   top-level side effects that construct application settings. This module
   reads logging configuration purely from ``LOG_*`` environment variables via
   ``LogConfig`` (autom8y_log) and ``core.logging.configure``; it never calls
   ``api.config.get_settings()``.

2. **PROCESS-GLOBAL / cold-start-once**: configuration is applied once at
   module-import (cold-start) time, NOT per-invocation. Reconfiguring the
   global structlog chain on every Lambda invocation is forbidden. Idempotence
   is guaranteed three ways: this module's own ``_configured`` flag, the
   ``core.logging`` wrapper's ``_configured`` guard, and ``autom8y_log``'s
   process-global guard in ``configure_logging``.

3. **No FastAPI coupling**: the satellite ``_filter_sensitive_data`` lives in
   ``api/middleware/core.py``; importing it transitively loads the entire
   FastAPI application surface (~138 modules, including the frozen
   ``api.lifespan``), which would inflate Lambda cold-start and couple the
   Lambda image to the web app. Instead, the substring-redaction *semantics*
   are preserved here by an independent processor that uses the identical
   sensitive-field set and substring-match rule. The behavior is preserved;
   the FastAPI import graph is not dragged into the Lambda.

4. **Trace-id processor is shared with the SDK**: ``add_otel_trace_ids`` is
   imported from ``autom8y_log.processors`` (the same function the ECS path
   uses). Importing it adds zero incremental modules at cold-start because
   every handler already imports ``autom8y_log`` for ``get_logger``.
"""

from __future__ import annotations

import os
from typing import Any

from autom8y_log.processors import add_otel_trace_ids

from autom8_asana.core.logging import configure as configure_logging

__all__ = ["configure_lambda_logging"]

# Sensitive-field set mirrors the satellite filter in api/middleware/core.py
# (SENSITIVE_FIELDS). Substring matching — NOT exact matching — is the
# load-bearing property: it redacts compound keys such as ``asana_pat``,
# ``bot_token`` and ``client_secret`` that the autom8y_log default
# exact-match filter (DEFAULT_SENSITIVE_FIELDS) would let through. Keep this
# set in sync with api/middleware/core.py SENSITIVE_FIELDS.
_SENSITIVE_FIELDS = frozenset({"authorization", "token", "pat", "password", "secret"})

_REDACTED = "[REDACTED]"

# Module-level cold-start guard. Defensive: core.logging.configure and
# autom8y_log.configure_logging each hold their own process-global guard, so
# this flag is a third layer that also makes the function cheap to call again
# (e.g. if both __init__ and a direct caller invoke it) without re-entering
# the configure delegation.
_configured = False


def _filter_sensitive_data_substring(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor: redact substring-matched sensitive fields.

    Semantics intentionally identical to ``api.middleware.core``'s
    ``_filter_sensitive_data``: any event-dict key whose lowercased form
    contains one of ``_SENSITIVE_FIELDS`` as a substring has its value
    replaced with ``"[REDACTED]"``. This catches ``asana_pat``,
    ``bot_token``, ``client_secret`` etc. that an exact-match filter misses.

    Args:
        _logger: Logger instance (unused; structlog processor protocol).
        _method_name: Log method name (unused; structlog processor protocol).
        event_dict: Log event dictionary to filter in place.

    Returns:
        The event dictionary with sensitive values redacted.
    """
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(field in key_lower for field in _SENSITIVE_FIELDS):
            event_dict[key] = _REDACTED
    return event_dict


def configure_lambda_logging() -> None:
    """Configure structured logging for Lambda handlers once at cold-start.

    Idempotent. Reads ``LOG_*`` from the environment (via ``LogConfig`` inside
    ``core.logging.configure``) — never ``get_settings()`` — so calling this at
    module-import time preserves the import-safety property of
    ``lambda_handlers/__init__.py``.

    Wires two additional structlog processors into the autom8y_log chain:

    - ``add_otel_trace_ids``: injects ``trace_id``/``span_id`` from the active
      OpenTelemetry span (opened by ``@instrument_lambda``) so Lambda log lines
      correlate with their spans. No-ops outside a span context.
    - ``_filter_sensitive_data_substring``: substring redaction preserving the
      satellite filter's semantics without importing the FastAPI app.

    The log level is taken from ``LOG_LEVEL`` (default ``INFO``) and the format
    from ``LOG_FORMAT`` (default ``auto`` → JSON in Lambda's non-TTY runtime).
    """
    global _configured
    if _configured:
        return

    # Read level/format from LOG_* env only. LogConfig() inside core.logging
    # also reads LOG_*, but core.logging.configure takes explicit level/format
    # kwargs, so resolve them from env here to keep the call self-describing
    # and free of any settings construction.
    level = os.environ.get("LOG_LEVEL", "INFO")
    fmt = os.environ.get("LOG_FORMAT", "auto")

    configure_logging(
        level=level,
        format=fmt,
        additional_processors=[add_otel_trace_ids, _filter_sensitive_data_substring],
    )
    _configured = True
