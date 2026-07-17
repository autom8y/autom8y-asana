"""Contract §3 gen_ai.* span + traceparent — two-sided; checklist items 1 & 12.

Real SDK tracer supplied by monkeypatching ``opentelemetry.trace.get_tracer`` (the
autom8y-telemetry pytest plugin resets the global provider per-test). InMemory
exporter is the fake collector. Asserts the contract's exact gen_ai.* +
com.autom8y.mcp.* attributes AND traceparent continuity across the ctx.http hop;
content attrs absent unless capture_content=True.
"""

from __future__ import annotations

import asyncio

import opentelemetry.trace as _otel_trace
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from asana_mcp.observability import (
    ATTR_BUDGET_CLASS,
    ATTR_SATELLITE,
    ATTR_TOOL_NAME,
    GEN_AI_OPERATION,
    GEN_AI_TOOL_ARGS,
    GEN_AI_TOOL_NAME,
    GEN_AI_TOOL_TYPE,
    ObservabilitySettings,
    instrument_tool,
    propagate_traceparent,
    tool_span,
)


@pytest.fixture
def collector(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("asana_mcp.observability")
    monkeypatch.setattr(_otel_trace, "get_tracer", lambda *a, **k: tracer)
    return exporter


class _FakeHttp:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}


class _FakeCtx:
    def __init__(self) -> None:
        self.http = _FakeHttp()


def test_span_carries_contract_attrs(collector: InMemorySpanExporter) -> None:
    with tool_span("query_rows", honesty={"stale_served": True}):
        pass
    spans = collector.get_finished_spans()
    assert len(spans) == 1
    a = spans[0].attributes
    assert a[GEN_AI_OPERATION] == "execute_tool"
    assert a[GEN_AI_TOOL_NAME] == "query_rows"
    assert a[GEN_AI_TOOL_TYPE] == "function"
    assert a[ATTR_SATELLITE] == "asana"  # com.autom8y.mcp.satellite
    assert a[ATTR_TOOL_NAME] == "query_rows"  # com.autom8y.mcp.tool.name
    assert a[ATTR_BUDGET_CLASS] == "mcp"  # com.autom8y.mcp.budget.class
    assert a["com.autom8y.mcp.honesty.stale_served"] is True
    assert spans[0].name == "execute_tool query_rows"


def test_content_attrs_absent_unless_capture_enabled(
    collector: InMemorySpanExporter,
) -> None:
    with tool_span("query_rows", capture_content=False, tool_args={"secret": 1}):
        pass
    a = collector.get_finished_spans()[0].attributes
    assert GEN_AI_TOOL_ARGS not in a  # PII posture: OFF by default (contract §3.2)


def test_content_attrs_present_when_capture_enabled(
    collector: InMemorySpanExporter,
) -> None:
    with tool_span("query_rows", capture_content=True, tool_args={"a": 1}):
        pass
    a = collector.get_finished_spans()[0].attributes
    assert GEN_AI_TOOL_ARGS in a


def test_traceparent_injected_carries_span_trace_id(
    collector: InMemorySpanExporter,
) -> None:
    carrier: dict[str, str] = {}
    with tool_span("query_rows") as span:
        propagate_traceparent(carrier)
        expected = format(span.get_span_context().trace_id, "032x")
    assert "traceparent" in carrier
    assert carrier["traceparent"].split("-")[1] == expected


def test_wrapper_propagates_traceparent_onto_ctx_http(
    collector: InMemorySpanExporter,
) -> None:
    obs = ObservabilitySettings.from_env()
    cap = obs.build_rate_cap()
    ctx = _FakeCtx()

    async def tool() -> dict[str, object]:
        return {"rows": []}

    wrapped = instrument_tool(
        tool, tool_name="query_rows", obs=obs, rate_cap=cap, get_ctx=lambda: ctx
    )
    asyncio.run(wrapped())
    spans = [s for s in collector.get_finished_spans() if s.name == "execute_tool query_rows"]
    assert len(spans) == 1
    tid = format(spans[0].get_span_context().trace_id, "032x")
    assert "traceparent" in ctx.http.headers  # continuous trace across the hop
    assert ctx.http.headers["traceparent"].split("-")[1] == tid


def test_refusal_span_carries_refusal_cause(collector: InMemorySpanExporter) -> None:
    """Checklist item 15: every refusal path sets com.autom8y.mcp.refusal.cause."""
    from asana_mcp.observability import (
        ATTR_REFUSAL_CAUSE,
        RateCap,
        RateCapExceeded,
    )

    obs = ObservabilitySettings.from_env()
    cap = RateCap(rate=1.0, window_s=1.0, burst=1.0)

    async def tool() -> dict[str, object]:
        return {"rows": []}

    wrapped = instrument_tool(tool, tool_name="query_rows", obs=obs, rate_cap=cap)
    asyncio.run(wrapped())  # consume the single token
    with pytest.raises(RateCapExceeded):
        asyncio.run(wrapped())  # refused -> refusal span
    causes = [s.attributes.get(ATTR_REFUSAL_CAUSE) for s in collector.get_finished_spans()]
    assert "rate_budget" in causes
