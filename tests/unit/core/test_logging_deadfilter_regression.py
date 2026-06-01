"""Regression: custom log processors must survive premature SDK auto-config.

SEC dead-custom-processor defect (SRE 2026-06-02). A module-scope
``get_logger(__name__)`` evaluated during import triggers the autom8y_log SDK's
auto-config with the BARE default chain, setting the SDK-level ``_configured``
flag before the application's own ``core.logging.configure(...)`` runs (ECS
lifespan startup / Lambda cold-start). Without a re-activation guard, the
satellite ``configure_logging`` call no-ops and SILENTLY DISCARDS
``additional_processors`` — leaving the substring ``_filter_sensitive_data``
redaction dead on both surfaces (compound keys like ``asana_pat`` reach logs
unredacted; FR-AUTH-004).

These tests drive the defect through the LIVE configured chain (emit via
``get_logger`` after a premature ``get_logger`` + ``configure``), not by calling
the processor functions in isolation — the test-adequacy gap that hid the
original defect. The fix is ``reset_logging()`` before ``configure_logging`` in
``core.logging.configure``.
"""

from __future__ import annotations

import contextlib
import io

import pytest
from autom8y_log import get_logger, reset_logging
from autom8y_log.processors import add_otel_trace_ids

import autom8_asana.core.logging as core_logging
from autom8_asana.api.middleware.core import _filter_sensitive_data


@pytest.fixture
def _pristine_logging():
    """Reset both the satellite and SDK logging state around each test.

    The satellite ``_configured`` flag is module-global and may be set by app
    startup elsewhere in the session; reset it so ``configure`` actually runs.
    """
    reset_logging()
    original = core_logging._configured
    core_logging._configured = False
    try:
        yield
    finally:
        reset_logging()
        core_logging._configured = original


def _emit_capture(**fields: str) -> str:
    """Emit one structured log line through the live chain and capture stdout."""
    log = get_logger("deadfilter_regression_probe")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        log.info("probe", **fields)
    return buf.getvalue()


def test_custom_filter_survives_premature_get_logger(_pristine_logging: None) -> None:
    """A premature get_logger() must NOT defeat the custom sensitive-data filter.

    Reproduces the cold-start import ordering: a module-scope logger fires
    (SDK auto-config, bare chain) BEFORE configure() runs. Post-fix, configure()
    re-activates the full chain and the compound-key secret is redacted.
    """
    # Premature module-scope get_logger -> SDK auto-config with the bare chain.
    _premature = get_logger("premature_import_time_logger")
    _premature.info("import_time")  # force first-use chain binding on bare defaults

    # Application configure() (ECS lifespan / Lambda cold-start equivalent).
    core_logging.configure(
        level="INFO",
        format="json",
        additional_processors=[add_otel_trace_ids, _filter_sensitive_data],
    )

    # Compound-key secret (substring match: "asana_pat" contains "pat").
    out = _emit_capture(asana_pat="1/RAWSECRET", bot_token="xoxb-LEAK")

    assert "RAWSECRET" not in out, f"asana_pat leaked unredacted: {out}"
    assert "xoxb-LEAK" not in out, f"bot_token leaked unredacted: {out}"
    assert out.count("[REDACTED]") >= 2


def test_exact_and_compound_sensitive_keys_redacted(_pristine_logging: None) -> None:
    """Both exact (authorization) and compound (asana_pat) keys redact post-configure."""
    get_logger("premature").info("warm")  # premature auto-config

    core_logging.configure(
        level="INFO",
        format="json",
        additional_processors=[add_otel_trace_ids, _filter_sensitive_data],
    )

    out = _emit_capture(
        authorization="Bearer SECRET_AUTH",
        asana_pat="1/SECRET_PAT",
        client_secret="SECRET_CS",
    )

    for leaked in ("SECRET_AUTH", "SECRET_PAT", "SECRET_CS"):
        assert leaked not in out, f"{leaked} leaked: {out}"


def test_no_context_passthrough_still_clean(_pristine_logging: None) -> None:
    """Non-sensitive fields pass through unchanged after the re-activation fix."""
    core_logging.configure(
        level="INFO",
        format="json",
        additional_processors=[add_otel_trace_ids, _filter_sensitive_data],
    )

    out = _emit_capture(entity="project", count="42")

    assert "project" in out
    assert "42" in out
    assert "[REDACTED]" not in out
