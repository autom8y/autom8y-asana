"""Span attribute tests for cascade audit instrumentation (Sprint 5, G-06).

Verifies that ``audit_cascade_key_nulls()`` writes the correct attributes onto
the ambient ``computation.progressive.build`` span when cascade key columns have
non-zero null rates.

Test coverage:
- T-G06 (warning threshold): attributes written when null_rate > 5%
- T-G06 (error threshold): columns_at_error attribute set when null_rate > 20%
- T-G06 (ok / empty guard): no cascade_audit.* attributes when early-return fires
"""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from autom8_asana.dataframes.builders.cascade_validator import (
    CASCADE_NULL_ERROR_THRESHOLD,
    CASCADE_NULL_WARN_THRESHOLD,
    audit_cascade_key_nulls,
)

# ---------------------------------------------------------------------------
# OTel fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def otel_provider():
    """Fresh TracerProvider per test for span isolation."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield provider, exporter

    exporter.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schema_with_cascade(col_name: str, field_name: str) -> MagicMock:
    """Return a mock DataFrameSchema with one cascade column."""
    schema = MagicMock()
    schema.get_cascade_columns.return_value = [(col_name, field_name)]
    return schema


def _make_df_with_null_rate(
    col_name: str, null_rate: float, total_rows: int = 100
) -> pl.DataFrame:
    """Build a DataFrame where ``col_name`` has the given null rate.

    Produces ``total_rows`` rows: ``null_count`` nulls followed by non-null values.
    """
    null_count = int(null_rate * total_rows)
    values: list[str | None] = [None] * null_count + ["value"] * (
        total_rows - null_count
    )
    return pl.DataFrame({"gid": [str(i) for i in range(total_rows)], col_name: values})


# ---------------------------------------------------------------------------
# T-G06: cascade audit attributes on ambient span
# ---------------------------------------------------------------------------


class TestCascadeAuditSpanAttributes:
    """T-G06: audit_cascade_key_nulls writes attributes onto the ambient span."""

    def test_warning_threshold_sets_attributes(self, otel_provider):
        """Null rate > 5% sets cascade_audit.* attributes including columns_at_warning."""
        _, exporter = otel_provider

        # null_rate = 10% -- exceeds WARNING (5%) but not ERROR (20%)
        null_rate = CASCADE_NULL_WARN_THRESHOLD + 0.05
        df = _make_df_with_null_rate("office_phone", null_rate, total_rows=100)
        schema = _make_schema_with_cascade("office_phone", "Office Phone")

        test_tracer = trace.get_tracer("test.cascade")
        with test_tracer.start_as_current_span("computation.progressive.build") as span:
            audit_cascade_key_nulls(
                df,
                entity_type="unit",
                project_gid="proj-123",
                schema=schema,
                key_columns=("office_phone",),
            )
            span_ref = span

        spans = exporter.get_finished_spans()
        progressive_spans = [
            s for s in spans if s.name == "computation.progressive.build"
        ]
        assert len(progressive_spans) == 1

        attrs = dict(progressive_spans[0].attributes)

        assert attrs["computation.cascade_audit.entity_type"] == "unit"
        assert attrs["computation.cascade_audit.max_severity"] == "warning"
        assert attrs["computation.cascade_audit.total_rows"] == 100
        assert attrs["computation.cascade_audit.null_column_count"] == 1

        # columns_at_warning should be set
        assert "computation.cascade_audit.columns_at_warning" in attrs
        assert "office_phone" in attrs["computation.cascade_audit.columns_at_warning"]

        # columns_at_error should NOT be set (null_rate < 20%)
        assert "computation.cascade_audit.columns_at_error" not in attrs

    def test_error_threshold_sets_columns_at_error(self, otel_provider):
        """Null rate > 20% sets columns_at_error in addition to columns_at_warning."""
        _, exporter = otel_provider

        # null_rate = 30% -- exceeds ERROR threshold (20%)
        null_rate = CASCADE_NULL_ERROR_THRESHOLD + 0.10
        df = _make_df_with_null_rate("office_phone", null_rate, total_rows=100)
        schema = _make_schema_with_cascade("office_phone", "Office Phone")

        test_tracer = trace.get_tracer("test.cascade")
        with test_tracer.start_as_current_span("computation.progressive.build"):
            audit_cascade_key_nulls(
                df,
                entity_type="unit",
                project_gid="proj-456",
                schema=schema,
                key_columns=("office_phone",),
            )

        spans = exporter.get_finished_spans()
        progressive_spans = [
            s for s in spans if s.name == "computation.progressive.build"
        ]
        assert len(progressive_spans) == 1

        attrs = dict(progressive_spans[0].attributes)

        assert attrs["computation.cascade_audit.max_severity"] == "error"
        assert "computation.cascade_audit.columns_at_error" in attrs
        assert "office_phone" in attrs["computation.cascade_audit.columns_at_error"]

    def test_no_matching_key_columns_no_cascade_audit_attributes(self, otel_provider):
        """When no cascade column is a key column, cascade_key_nulls is empty -> early return.

        The early-return guard fires when cascade_key_nulls is empty, which happens
        when the cascade column is NOT in the key_columns tuple.  No attributes are
        written to the span in this case.
        """
        _, exporter = otel_provider

        df = _make_df_with_null_rate("office_phone", 0.10, total_rows=100)
        schema = _make_schema_with_cascade("office_phone", "Office Phone")

        test_tracer = trace.get_tracer("test.cascade")
        with test_tracer.start_as_current_span("computation.progressive.build"):
            # Pass an empty key_columns tuple -- office_phone is NOT a key column,
            # so it is skipped and cascade_key_nulls stays empty -> early return.
            audit_cascade_key_nulls(
                df,
                entity_type="unit",
                project_gid="proj-ok",
                schema=schema,
                key_columns=(),
            )

        spans = exporter.get_finished_spans()
        progressive_spans = [
            s for s in spans if s.name == "computation.progressive.build"
        ]
        assert len(progressive_spans) == 1

        attrs = dict(progressive_spans[0].attributes)

        # No cascade_audit.* attributes should be present (early return path)
        cascade_attrs = [k for k in attrs if k.startswith("computation.cascade_audit.")]
        assert len(cascade_attrs) == 0, (
            f"Expected no cascade_audit.* attrs when key_columns is empty, got {cascade_attrs}"
        )

    def test_no_active_span_is_safe_noop(self):
        """With no active span, audit_cascade_key_nulls is a safe no-op (no exception)."""
        # Ensure there is no active span by using a fresh NoOpTracerProvider
        from opentelemetry.trace import NonRecordingSpan

        # null_rate = 10% to ensure we reach attribute-writing code
        null_rate = CASCADE_NULL_WARN_THRESHOLD + 0.05
        df = _make_df_with_null_rate("office_phone", null_rate, total_rows=50)
        schema = _make_schema_with_cascade("office_phone", "Office Phone")

        # Call without any active span context -- should not raise
        audit_cascade_key_nulls(
            df,
            entity_type="unit",
            project_gid="proj-noop",
            schema=schema,
            key_columns=("office_phone",),
        )
        # If we reach here, the no-op path is safe
