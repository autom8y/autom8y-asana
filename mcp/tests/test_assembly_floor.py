"""FLOOR ATTESTATION — seam-contract §5 items 1-4 against the ASSEMBLED sidecar.

sprint-6 assembly leg. Exercises the frozen mount-seam order (create_server-style
register of the READ tools -> exposure-gated write tool OFF -> instrument()) against
the REAL fastmcp 3.4.4 registry (mcp._local_provider._components) with an injected
MockTransport ctx (the transport/token seam s2 built into build_context).

Discriminating-canary doctrine (§2.1/§2.2): every RED is a deliberately-broken INPUT
the LIVE assembled surface CORRECTLY REJECTS, paired with the real input passing GREEN.
NO defect is injected into the assembled package to manufacture a RED (that would be
G-THEATER). The production diff of this file is test-only.

Floor items (contract §5, PT-01 Q3 = items 1-4):
  1. Traceparent visible across the hop (two-sided: instrumented vs bare client).
  2. Partition honored (invariant fail-loud on broken env; burst+1 -> one refusal).
  3. Import-safety green for the unified package INCLUDING asana_mcp.assembly.
  4. Honesty propagated (4 native fields surfaced + span attrs; hiding tool rejected).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from asana_mcp.context import build_context
from asana_mcp.observability import (
    ATTR_HONESTY_PREFIX,
    ATTR_REFUSAL_CAUSE,
    BudgetPartitionError,
    HonestySuppressionError,
    ObservabilitySettings,
    RateCap,
    instrument,
    instrument_tool,
)
from asana_mcp.settings import Settings
from asana_mcp.tools import composite_write, discovery, query, resolve
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# --- one global recording provider for the whole module (no telemetry plugin here) --
_EXPORTER = InMemorySpanExporter()
_PROVIDER = TracerProvider()
_PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))
trace.set_tracer_provider(_PROVIDER)

# --- canned native envelope shapes (rows carries all four honesty fields) -----------
_ENTITIES = [
    {"entity_type": "offer", "display_name": "Offer", "project_gid": "1", "category": "business"}
]
_ROWS_ENVELOPE = {
    "data": {
        "data": [{"office_phone": "+15551234567", "vertical": "dental"}],
        "meta": {
            "total_count": 1,
            "returned_count": 1,
            "entity_type": "offer",
            "stale_served": False,
            "honest_contract_complete": True,
            "honest_empty": False,
            "contract_complete": True,
        },
    },
    "meta": {"request_id": "req-1"},
}


async def _fake_token() -> str:
    return "fake.s2s.jwt"


def _handler(record: list[dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        record.append({"path": request.url.path, "traceparent": request.headers.get("traceparent")})
        p = request.url.path
        if p == "/ready":
            return httpx.Response(200, json={"status": "ready"})
        if p == "/v1/query/entities":
            return httpx.Response(200, json={"data": _ENTITIES})
        if p.endswith("/rows"):
            return httpx.Response(200, json=_ROWS_ENVELOPE)
        return httpx.Response(404, json={"error": {"code": "UNMAPPED"}})

    return handler


def _assemble(record: list[dict], *, instrument_on: bool = True):
    """Assemble per the frozen mount-seam order with an injected MockTransport ctx."""
    from fastmcp import FastMCP

    ctx = build_context(
        Settings(base_url="http://sat.local", ready_path="/ready"),
        token_provider=_fake_token,
        transport=httpx.MockTransport(_handler(record)),
    )
    mcp = FastMCP(name="asana-mcp")
    discovery.register(mcp, ctx)  # READ tools 1-2
    query.register(mcp, ctx)  # READ tools 3-4
    resolve.register(mcp, ctx)  # READ tool 5
    mcp.sidecar_context = ctx
    composite_write.register(mcp, ctx)  # EXPOSURE-GATED, default OFF -> attaches nothing
    if instrument_on:
        instrument(mcp, None)  # obs from_env; wires HTTPXClientInstrumentor onto ctx.http
    return mcp, ctx


@pytest.fixture(autouse=True)
def _clear_spans():
    _EXPORTER.clear()
    yield


# ---------------------------------------------------------------------------
# FLOOR ITEM 1 — traceparent visible across the hop (two-sided)
# ---------------------------------------------------------------------------
def test_floor1_traceparent_across_the_hop() -> None:
    record: list[dict] = []
    mcp, ctx = _assemble(record, instrument_on=True)
    asyncio.run(mcp.call_tool("list_entity_types", {}))
    asyncio.run(ctx.http.aclose())

    spans = [
        s for s in _EXPORTER.get_finished_spans() if s.name == "execute_tool list_entity_types"
    ]
    assert len(spans) == 1, "assembled server did not open exactly one execute_tool span"
    tid = format(spans[0].get_span_context().trace_id, "032x")
    tps = [r["traceparent"] for r in record if r["traceparent"]]
    assert tps, "no outbound request carried a W3C traceparent"
    # every outbound hop rides the SAME trace as the sidecar tool span
    assert all(tp.split("-")[1] == tid for tp in tps), (
        "outbound traceparent trace_id != sidecar span trace_id"
    )


def test_floor1_negative_control_bare_client_no_traceparent() -> None:
    """Discriminating control: an UN-instrumented assembled surface injects NO traceparent."""
    record: list[dict] = []
    mcp, ctx = _assemble(record, instrument_on=False)
    asyncio.run(mcp.call_tool("list_entity_types", {}))
    asyncio.run(ctx.http.aclose())
    assert record, "the bare tool still hit the transport"
    assert all(r["traceparent"] is None for r in record), (
        "bare client leaked a traceparent (assertion is vacuous)"
    )


# ---------------------------------------------------------------------------
# FLOOR ITEM 2 — partition honored (invariant fail-loud + burst+1 refusal)
# ---------------------------------------------------------------------------
def test_floor2_partition_invariant_fail_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    """Broken INPUT: an oversubscribed share partition is REFUSED at instrument() time."""
    monkeypatch.setenv("ASANA_MCP_PAT_SHARE_MCP", "0.50")  # 0.60+0.32+0.50 = 1.42 > 1.0
    record: list[dict] = []
    with pytest.raises(BudgetPartitionError):
        _assemble(record, instrument_on=True)


def test_floor2_burst_plus_one_yields_exactly_one_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    """burst executions -> zero refusals (GREEN); burst+1 -> exactly one typed refusal (RED)."""
    monkeypatch.setenv("ASANA_MCP_RATE_BURST", "1")  # burst = 1
    monkeypatch.setenv("ASANA_MCP_RATE_RPS", "0.001")  # negligible refill; 0.001*60 <= 0.08*1500 OK
    record: list[dict] = []
    mcp, ctx = _assemble(record, instrument_on=True)

    asyncio.run(mcp.call_tool("list_entity_types", {}))  # call 1: within burst -> allowed
    refusals_after_burst = [
        s
        for s in _EXPORTER.get_finished_spans()
        if s.attributes.get(ATTR_REFUSAL_CAUSE) == "rate_budget"
    ]
    assert refusals_after_burst == [], "a within-burst call was refused (partition too tight)"

    # call 2: burst+1 -> refused. fastmcp does NOT swallow it — the typed refusal
    # propagates out of call_tool (fail-closed, never queued past MAX_WAIT).
    with pytest.raises(Exception) as ei:  # noqa: B017 - fastmcp may wrap the typed error
        asyncio.run(mcp.call_tool("list_entity_types", {}))
    asyncio.run(ctx.http.aclose())
    assert "MCP_RATE_BUDGET_EXHAUSTED" in str(ei.value), (
        "refusal was not the typed rate-budget code"
    )
    refusals = [
        s
        for s in _EXPORTER.get_finished_spans()
        if s.attributes.get(ATTR_REFUSAL_CAUSE) == "rate_budget"
    ]
    assert len(refusals) == 1, (
        f"burst+1 must yield exactly one rate_budget refusal, got {len(refusals)}"
    )


# ---------------------------------------------------------------------------
# FLOOR ITEM 3 — import-safety green for the unified package incl. assembly.py
# ---------------------------------------------------------------------------
_IMPORT_SCRIPT = r"""
import sys, json, socket, tempfile, os
net = []
_WATCH = ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system", "urllib.Request")
sys.addaudithook(lambda e, a: net.append(e) if e in _WATCH else None)

# import the whole assembled surface (incl. the sprint-6 assembly entrypoint)
import asana_mcp
import asana_mcp.assembly as a
import asana_mcp.observability as o
import asana_mcp.timeouts as t
import_net = list(net)

# no module-level settings instance in the assembly entrypoint
real_has_instance = any(isinstance(getattr(a, n, None), o.ObservabilitySettings) for n in dir(a))

# teeth: a broken fixture that builds Settings at IMPORT is caught by the same detector
d = tempfile.mkdtemp()
open(os.path.join(d, "_broken.py"), "w").write(
    "from asana_mcp.observability import ObservabilitySettings\nS = ObservabilitySettings.from_env()\n"
)
sys.path.insert(0, d)
import _broken as b
broken_has_instance = any(isinstance(getattr(b, n, None), o.ObservabilitySettings) for n in dir(b))

print(json.dumps({"import_net": import_net, "real_has_instance": real_has_instance,
                  "broken_has_instance": broken_has_instance}))
"""


def test_floor3_unified_package_import_safe() -> None:
    mcp_root = str(Path(__file__).resolve().parents[1])  # mcp/ (asana_mcp lives here)
    env = {k: v for k, v in os.environ.items() if not k.startswith("ASANA_MCP_")}
    env["PYTHONPATH"] = mcp_root + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT], capture_output=True, text=True, env=env, timeout=60
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}"
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data["import_net"] == []  # ZERO network at import (C9a)
    assert data["real_has_instance"] is False  # assembly.py builds no Settings at import
    assert data["broken_has_instance"] is True  # detector has teeth (catches import-time Settings)


# ---------------------------------------------------------------------------
# FLOOR ITEM 4 — honesty propagated (surfaced fields + span attrs; hiding rejected)
# ---------------------------------------------------------------------------
def test_floor4_honesty_surfaced_and_span_attributed() -> None:
    record: list[dict] = []
    mcp, ctx = _assemble(record, instrument_on=True)
    res = asyncio.run(
        mcp.call_tool("query_rows", {"entity_type": "offer", "args": {"select": ["office_phone"]}})
    )
    asyncio.run(ctx.http.aclose())

    payload = res.structured_content
    # all four native honesty fields surfaced in the LLM-visible result
    for field in ("stale_served", "honest_empty", "contract_complete", "honest_contract_complete"):
        assert field in payload, f"honesty field {field!r} not surfaced to the LLM"
    # ...and mirrored onto the execute_tool span as com.autom8y.mcp.honesty.*
    spans = [s for s in _EXPORTER.get_finished_spans() if s.name == "execute_tool query_rows"]
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert any(k.startswith(ATTR_HONESTY_PREFIX) for k in attrs), (
        "no com.autom8y.mcp.honesty.* span attrs"
    )


def test_floor4_hiding_unwrapper_rejected() -> None:
    """Discriminating RED: a tool that DROPS an upstream honesty field is REJECTED by the guard."""
    obs = ObservabilitySettings.from_env()

    async def hiding() -> dict:
        # upstream says stale_served=True; surfaced meta hides it -> suppression
        return {"meta": {"stale_served": False}, "_upstream_meta": {"stale_served": True}}

    wrapped = instrument_tool(
        hiding, tool_name="query_rows", obs=obs, rate_cap=RateCap(rate=100, burst=100)
    )
    with pytest.raises(HonestySuppressionError):
        asyncio.run(wrapped())
