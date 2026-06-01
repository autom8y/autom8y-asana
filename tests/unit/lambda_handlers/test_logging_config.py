"""Correlation tests for Lambda cold-start logging config (TDD-LOG-TRACE-LAMBDA).

These tests verify the three load-bearing properties of
``lambda_handlers.logging_config``:

1. **Trace-id-in-log non-vacuity** — inside an active OpenTelemetry span, the
   wired ``add_otel_trace_ids`` processor injects a 32-hex ``trace_id`` and a
   16-hex ``span_id`` into the event dict, so Lambda log lines correlate with
   the spans opened by ``@instrument_lambda``.
2. **No-context passthrough** — outside any span, no ``trace_id``/``span_id``
   keys are added (the processor must not fabricate correlation ids).
3. **Sensitive-data filter (substring semantics)** — the locally-defined
   redaction processor redacts compound keys (``asana_pat``, ``bot_token``,
   ``client_secret``) that the SDK's exact-match default filter would leak,
   preserving the satellite ``api.middleware.core._filter_sensitive_data``
   semantics without importing the FastAPI app.

The logging configuration is process-global state. The ``xdist_group`` marker
co-locates this module on a single worker under ``--dist=loadgroup`` so the
cold-start guard and any global configure() interaction stay deterministic and
do not race other process-global logging tests across workers.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from autom8y_log.processors import add_otel_trace_ids
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from autom8_asana.lambda_handlers.logging_config import (
    _filter_sensitive_data_substring,
    configure_lambda_logging,
)

# Process-global logging state: keep this module on one xdist worker.
pytestmark = [pytest.mark.xdist_group("lambda_logging_config")]


@pytest.fixture(scope="module")
def _tracer() -> trace.Tracer:
    """Provide a real (SDK) tracer so spans produce valid span contexts.

    Uses the process tracer provider if one is already a real
    ``TracerProvider``; otherwise installs one. A valid span context is
    required for ``add_otel_trace_ids`` to inject ids (it checks
    ``span_context.is_valid``).
    """
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        trace.set_tracer_provider(TracerProvider())
    return trace.get_tracer("test.lambda_logging_config")


# --- 1. Trace-id-in-log non-vacuity ---


def test_trace_ids_injected_inside_active_span(_tracer: trace.Tracer) -> None:
    """Inside an active span, trace_id (32 hex) and span_id (16 hex) appear."""
    with _tracer.start_as_current_span("lambda-handler-span"):
        event_dict: dict[str, Any] = {"event": "handler_invoked"}
        result = add_otel_trace_ids(None, "info", event_dict)

    assert "trace_id" in result, "add_otel_trace_ids must inject trace_id in span context"
    assert "span_id" in result, "add_otel_trace_ids must inject span_id in span context"
    # Non-vacuity: ids are correctly-sized lowercase hex, not empty/placeholder.
    assert len(result["trace_id"]) == 32
    assert len(result["span_id"]) == 16
    int(result["trace_id"], 16)  # parses as hex
    int(result["span_id"], 16)
    assert result["trace_id"] != "0" * 32, "trace_id must not be the all-zero (invalid) id"


def test_trace_ids_match_active_span_context(_tracer: trace.Tracer) -> None:
    """The injected ids equal the active span's own context (true correlation)."""
    with _tracer.start_as_current_span("lambda-handler-span") as span:
        ctx = span.get_span_context()
        result = add_otel_trace_ids(None, "info", {"event": "handler_invoked"})

    assert result["trace_id"] == format(ctx.trace_id, "032x")
    assert result["span_id"] == format(ctx.span_id, "016x")


# --- 2. No-context passthrough ---


def test_no_trace_ids_outside_span_context() -> None:
    """Outside any active span, the processor adds no correlation ids."""
    event_dict: dict[str, Any] = {"event": "module_import"}
    result = add_otel_trace_ids(None, "info", event_dict)

    assert "trace_id" not in result, "no trace_id may be fabricated outside a span"
    assert "span_id" not in result, "no span_id may be fabricated outside a span"
    assert result["event"] == "module_import", "non-trace fields pass through unchanged"


# --- 3. Sensitive-data filter (substring semantics) ---


def test_substring_filter_redacts_compound_secret_keys() -> None:
    """Compound keys an exact-match filter would miss are redacted."""
    event_dict: dict[str, Any] = {
        "asana_pat": "1/123:abcdefSECRET",
        "bot_token": "xoxb-deadbeef",
        "client_secret": "cs_live_xyz",
        "authorization": "Bearer abc",
        "task_gid": "1234567890",  # safe
        "count": 42,  # safe
    }
    result = _filter_sensitive_data_substring(None, "info", event_dict)

    assert result["asana_pat"] == "[REDACTED]"
    assert result["bot_token"] == "[REDACTED]"
    assert result["client_secret"] == "[REDACTED]"
    assert result["authorization"] == "[REDACTED]"
    # Non-sensitive fields untouched.
    assert result["task_gid"] == "1234567890"
    assert result["count"] == 42


def test_substring_filter_matches_satellite_semantics() -> None:
    """The Lambda filter and the satellite filter redact the same key set.

    Guards against drift: the Lambda processor is an independent copy of the
    satellite ``_filter_sensitive_data`` (decoupled to avoid importing the
    FastAPI app), so behavior-equivalence is asserted explicitly.
    """
    from autom8_asana.api.middleware.core import (
        _filter_sensitive_data as satellite_filter,
    )

    payload: dict[str, Any] = {
        "asana_pat": "secret1",
        "bot_token": "secret2",
        "client_secret": "secret3",
        "password_hash": "secret4",
        "x_request_id": "req-1",
        "duration_ms": 12.5,
    }
    lambda_result = _filter_sensitive_data_substring(None, "info", dict(payload))
    satellite_result = satellite_filter(None, "info", dict(payload))

    assert lambda_result == satellite_result


# --- 4. Cold-start wiring / idempotence ---


def test_configure_is_idempotent() -> None:
    """Second call to configure_lambda_logging is a no-op (cold-start once).

    Verifies the PROCESS-GLOBAL constraint: configuration happens once, not
    per-invocation. With the module-level guard already set (the package import
    at collection time configured it), the underlying configure delegate must
    not be re-invoked.
    """
    import autom8_asana.lambda_handlers.logging_config as lc

    # Establish the configured state explicitly (order-independent): the
    # package import sets this at cold-start, but assert the guard's contract
    # directly rather than relying on suite ordering.
    lc._configured = True
    with patch.object(lc, "configure_logging", MagicMock()) as mock_configure:
        configure_lambda_logging()
        assert mock_configure.call_count == 0, (
            "configure_lambda_logging must not reconfigure when already configured "
            "(PROCESS-GLOBAL cold-start-once constraint)"
        )


def test_cold_start_wiring_configures_without_settings() -> None:
    """Cold-start wiring configures autom8y_log without get_settings().

    Regression for the import-safety property: ``configure_lambda_logging``
    reads only LOG_* env vars (via core.logging -> LogConfig), never
    ``api.config.get_settings()``. Asserted from a clean logging state so the
    test is order-independent under the suite's autouse singleton resets — the
    package is already in sys.modules, so a re-import is a no-op and cannot be
    relied on to re-run the cold-start; we drive the cold-start function
    directly after restoring a pristine state.
    """
    import autom8y_log.logger as sdk_logger

    import autom8_asana.core.logging as core_logging
    import autom8_asana.lambda_handlers.logging_config as lc

    # Pristine state mirroring a Lambda cold-start: clear all THREE
    # process-global guards so the configure delegation actually re-runs:
    #   - lc._configured            (this module's guard)
    #   - core_logging._configured  (the core.logging wrapper guard)
    #   - autom8y_log _configured   (the SDK global, via reset_logging)
    # The triple guard is the "double-safe" property the design relies on; a
    # true cold-start has none of them set.
    sdk_logger.reset_logging()
    original_module_guard = lc._configured
    original_core_guard = core_logging._configured
    lc._configured = False
    core_logging._configured = False
    try:
        with patch("autom8_asana.settings.get_settings", MagicMock()) as mock_get_settings:
            configure_lambda_logging()
            assert mock_get_settings.call_count == 0, (
                "cold-start logging wiring must not trigger get_settings()"
            )
        assert sdk_logger._configured is True, (
            "autom8y_log must be configured after cold-start wiring"
        )
        assert lc._configured is True, "module cold-start guard must be set"
    finally:
        # Restore the configured steady state so other tests/handlers see a
        # configured chain (post-cold-start steady state).
        lc._configured = True if sdk_logger._configured else original_module_guard
        core_logging._configured = True if sdk_logger._configured else original_core_guard
