"""Span + structured-log tests for the ``exports.request`` request span.

OBS-EXPORTS-001 (SRE OB2 sprint). Verifies that ``export_handler`` opens ONE
``exports.request`` span wrapping the pipeline body, sets the six contracted
attributes, and emits the three contracted structured logs on their trigger
conditions. Both delegating routes (``post_export_v1`` / ``post_export_api_v1``)
inherit the SAME span via the shared callable.

Signal contract (.know/obs.md OBS-EXPORTS-001):
- Span attributes: entity_type, row_count_pre_dedup, row_count_post_dedup,
  date_filter_applied, section_default_applied, identity_suppressed_count.
- Structured logs: exports_section_default_injected,
  exports_identity_rows_suppressed, exports_date_filter_applied.

The OTel fixture mirrors tests/unit/api/routes/test_resolver_spans.py
(InMemorySpanExporter bound to the module-level ``exports._tracer``). The
handler-driving fixtures mirror tests/unit/api/test_exports_handler.py
(mock strategy / entity service / patched PredicateCompiler.compile).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from autom8_asana.api.routes.exports import ExportRequest, export_handler
from autom8_asana.query.compiler import PredicateCompiler

SPAN_NAME = "exports.request"

# Sections that the ACTIVE-default predicate injects (mirrors the helper's
# ACTIVE_SECTIONS membership; the patched compiler resolves them to a no-op
# passthrough so we exercise the section-default path, not the engine).
_ACTIVE_SECTIONS = ["ACTIVE", "BUILDING", "EXECUTING", "PROCESSING", "OPPORTUNITY", "CONTACTED"]


# ---------------------------------------------------------------------------
# OTel fixture: patches the module-level _tracer in exports.py
# ---------------------------------------------------------------------------


@pytest.fixture()
def otel_provider():
    """Fresh TracerProvider per test, bound to ``exports._tracer``.

    Mirrors test_resolver_spans.py: rebinds the module-level singleton so the
    span emitted by export_handler lands in this test's in-memory exporter.
    """
    import autom8_asana.api.routes.exports as _exports_module

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Do NOT call trace.set_tracer_provider(provider) here: OTel's API
    # documents this as a once-only operation ("This can only be done once, a
    # warning will be logged if any further attempt is made"). Multiple test
    # fixtures calling it race-fail silently, leaving later tests bound to the
    # first fixture's provider and producing empty exporters. Patching the
    # module-local _tracer below is sufficient: spans emitted via that tracer
    # are processed by THIS provider's SpanProcessor (the local exporter).

    fresh_tracer = provider.get_tracer("autom8_asana.api.routes.exports")
    original_tracer = _exports_module._tracer
    _exports_module._tracer = fresh_tracer

    yield provider, exporter

    _exports_module._tracer = original_tracer
    exporter.clear()


# ---------------------------------------------------------------------------
# Handler-driving helpers (mirror test_exports_handler.py)
# ---------------------------------------------------------------------------


def _make_mock_entity_service(entity_type: str = "process") -> MagicMock:
    svc = MagicMock()
    ctx = MagicMock()
    ctx.entity_type = entity_type
    ctx.project_gid = "1201265144487549"
    svc.validate_entity_type.return_value = ctx
    return svc


def _passthrough_compile(self: Any, node: Any, schema: Any) -> pl.Expr:
    """Patched PredicateCompiler.compile → a section IN filter (no engine call).

    Bypasses schema validation in this unit context (same approach as the
    existing test_exports_handler pipeline test).
    """
    return pl.col("section").is_in(_ACTIVE_SECTIONS)


async def _run_handler(req: ExportRequest, fake_df: pl.DataFrame) -> Any:
    """Drive export_handler against a mocked strategy + patched compiler."""
    mock_strategy = MagicMock()
    mock_strategy._get_dataframe = AsyncMock(return_value=fake_df)
    svc = _make_mock_entity_service(req.entity_type)

    with (
        patch(
            "autom8_asana.services.universal_strategy.get_universal_strategy",
            return_value=mock_strategy,
        ),
        patch.object(PredicateCompiler, "compile", _passthrough_compile),
    ):
        return await export_handler(
            request_body=req,
            request_id="abcdef0123456789",
            auth=object(),
            entity_service=svc,
            client=object(),
        )


async def _run_handler_capturing_logs(req: ExportRequest, fake_df: pl.DataFrame) -> list[str]:
    """Drive export_handler and return the list of ``logger.info`` event names.

    ``autom8y_log`` writes structured records straight to stdout (bypassing the
    stdlib propagation ``caplog`` hooks), so we patch the module logger and read
    the emitted event names directly — mirroring test_exports_handler.py's
    ``patch("autom8_asana.api.routes.exports.logger")`` approach.
    """
    mock_strategy = MagicMock()
    mock_strategy._get_dataframe = AsyncMock(return_value=fake_df)
    svc = _make_mock_entity_service(req.entity_type)

    with (
        patch(
            "autom8_asana.services.universal_strategy.get_universal_strategy",
            return_value=mock_strategy,
        ),
        patch.object(PredicateCompiler, "compile", _passthrough_compile),
        patch("autom8_asana.api.routes.exports.logger") as mock_logger,
    ):
        await export_handler(
            request_body=req,
            request_id="abcdef0123456789",
            auth=object(),
            entity_service=svc,
            client=object(),
        )
    return [c.args[0] for c in mock_logger.info.call_args_list if c.args]


def _date_df() -> pl.DataFrame:
    """Base fixture with a real ``due_on`` date column (date filter needs a
    temporal column — string comparison raises in polars)."""
    return _base_df().with_columns(
        due_on=pl.Series(["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"]).str.to_date()
    )


def _base_df() -> pl.DataFrame:
    """4-row fixture: one null-key row (g3) + one duplicate dedupe key (g4≡g1)."""
    return pl.DataFrame(
        {
            "gid": ["g1", "g2", "g3", "g4"],
            "name": ["acct1", "acct2", "acct3", "acct4"],
            "section": ["ACTIVE", "EXECUTING", "ACTIVE", "ACTIVE"],
            "office_phone": ["555-1", "555-2", None, "555-1"],
            "vertical": ["saas", "retail", "ent", "saas"],
            "pipeline_type": ["reactivation", "outreach", "outreach", "reactivation"],
            "modified_at": ["2026-04-01", "2026-04-15", "2026-04-20", "2026-04-10"],
        }
    )


def _only_finished_export_spans(exporter: InMemorySpanExporter) -> list[Any]:
    return [s for s in exporter.get_finished_spans() if s.name == SPAN_NAME]


# ---------------------------------------------------------------------------
# T1: ONE span, all six attributes, shared-callable inheritance
# ---------------------------------------------------------------------------


class TestExportsRequestSpanAttributes:
    """The shared handler opens exactly ONE exports.request span with 6 attrs."""

    @pytest.mark.asyncio
    async def test_single_span_with_all_six_attributes(self, otel_provider) -> None:
        _, exporter = otel_provider
        # Caller omits section → ACTIVE-default fires; include=False + null-key
        # row → identity suppression fires; g4 dedupes into g1 → post < pre.
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            format="json",
            options={"include_incomplete_identity": False},  # type: ignore[arg-type]
        )
        await _run_handler(req, _base_df())

        spans = _only_finished_export_spans(exporter)
        assert len(spans) == 1, (
            f"Expected exactly 1 '{SPAN_NAME}' span, got "
            f"{[s.name for s in exporter.get_finished_spans()]}"
        )
        attrs = dict(spans[0].attributes)

        # All six contracted attributes present.
        for key in (
            "entity_type",
            "row_count_pre_dedup",
            "row_count_post_dedup",
            "date_filter_applied",
            "section_default_applied",
            "identity_suppressed_count",
        ):
            assert key in attrs, f"missing span attribute {key!r}: {sorted(attrs)}"

        assert attrs["entity_type"] == "process"
        assert attrs["section_default_applied"] is True
        assert attrs["date_filter_applied"] is False
        # g3 (null office_phone) suppressed under include=False.
        assert attrs["identity_suppressed_count"] == 1
        # After suppression 3 rows enter dedupe; g4≡g1 → 2 rows post-dedup.
        assert attrs["row_count_pre_dedup"] == 3
        assert attrs["row_count_post_dedup"] == 2

    @pytest.mark.asyncio
    async def test_no_suppression_and_no_default_when_section_supplied(self, otel_provider) -> None:
        _, exporter = otel_provider
        # Caller supplies a section predicate → default NOT applied; include
        # defaults True → no identity suppression.
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            predicate={  # type: ignore[arg-type]
                "field": "section",
                "op": "in",
                "value": ["ACTIVE"],
            },
        )
        await _run_handler(req, _base_df())

        attrs = dict(_only_finished_export_spans(exporter)[0].attributes)
        assert attrs["section_default_applied"] is False
        assert attrs["identity_suppressed_count"] == 0
        assert attrs["date_filter_applied"] is False


# ---------------------------------------------------------------------------
# T2: date_filter_applied attribute true-path
# ---------------------------------------------------------------------------


class TestExportsDateFilterAttribute:
    @pytest.mark.asyncio
    async def test_date_filter_applied_true(self, otel_provider) -> None:
        _, exporter = otel_provider
        # A DATE_GTE predicate on due_on (real date column) → date_filter_expr.
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            predicate={  # type: ignore[arg-type]
                "field": "due_on",
                "op": "date_gte",
                "value": "2026-01-01",
            },
        )
        await _run_handler(req, _date_df())

        attrs = dict(_only_finished_export_spans(exporter)[0].attributes)
        assert attrs["date_filter_applied"] is True


# ---------------------------------------------------------------------------
# T3: structured logs fire on their trigger conditions
# ---------------------------------------------------------------------------


class TestExportsStructuredLogs:
    @pytest.mark.asyncio
    async def test_section_default_injected_log_fires(self, otel_provider) -> None:
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
        )
        events = await _run_handler_capturing_logs(req, _base_df())
        assert "exports_section_default_injected" in events

    @pytest.mark.asyncio
    async def test_section_default_log_absent_when_section_supplied(self, otel_provider) -> None:
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            predicate={  # type: ignore[arg-type]
                "field": "section",
                "op": "in",
                "value": ["ACTIVE"],
            },
        )
        events = await _run_handler_capturing_logs(req, _base_df())
        assert "exports_section_default_injected" not in events

    @pytest.mark.asyncio
    async def test_identity_rows_suppressed_log_fires(self, otel_provider) -> None:
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            options={"include_incomplete_identity": False},  # type: ignore[arg-type]
        )
        events = await _run_handler_capturing_logs(req, _base_df())
        assert "exports_identity_rows_suppressed" in events

    @pytest.mark.asyncio
    async def test_identity_rows_suppressed_log_absent_when_include_true(
        self, otel_provider
    ) -> None:
        # Default include=True → no suppression → no log even with null-key row.
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
        )
        events = await _run_handler_capturing_logs(req, _base_df())
        assert "exports_identity_rows_suppressed" not in events

    @pytest.mark.asyncio
    async def test_date_filter_applied_log_fires(self, otel_provider) -> None:
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            predicate={  # type: ignore[arg-type]
                "field": "due_on",
                "op": "date_gte",
                "value": "2026-01-01",
            },
        )
        events = await _run_handler_capturing_logs(req, _date_df())
        assert "exports_date_filter_applied" in events

    @pytest.mark.asyncio
    async def test_date_filter_applied_log_absent_without_date_op(self, otel_provider) -> None:
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
        )
        events = await _run_handler_capturing_logs(req, _base_df())
        assert "exports_date_filter_applied" not in events
