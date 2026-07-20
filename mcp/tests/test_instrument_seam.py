"""Frozen mount-seam v1 item 3: instrument() idempotency + core guarantees.

Signature (FROZEN): def instrument(mcp: FastMCP, settings: Settings) -> FastMCP
(idempotent, checklist item 13). Tested against a local duck-typed FastMCP harness.
Fail-loud config validation (timeout cascade + partition) runs before any wrapping.
"""

from __future__ import annotations

import asyncio

import pytest
from asana_mcp.observability import (
    _INSTRUMENTED_ATTR,
    _WRAPPED_ATTR,
    BudgetPartition,
    HonestySuppressionError,
    ObservabilitySettings,
    RateCap,
    RateCapExceeded,
    instrument,
    instrument_tool,
)
from asana_mcp.timeouts import ConfigurationError, TimeoutConfig


class _ToolHandle:
    def __init__(self, fn: object) -> None:
        self.fn = fn


class _FakeMcp:
    def __init__(self, tools: dict[str, object]) -> None:
        self._tools = {n: _ToolHandle(f) for n, f in tools.items()}


def _obs(tool_s: float = 50.0) -> ObservabilitySettings:
    return ObservabilitySettings(
        timeouts=TimeoutConfig(connect_s=5.0, http_s=45.0, tool_s=tool_s),
        partition=BudgetPartition(),
        capture_content=False,
    )


# --- seam: returns the mcp, marks it, wraps tools, and is IDEMPOTENT ---
def test_instrument_is_idempotent() -> None:
    async def t() -> dict[str, object]:
        return {}

    mcp = _FakeMcp({"query_rows": t})
    r1 = instrument(mcp, _obs())
    assert r1 is mcp
    assert getattr(mcp, _INSTRUMENTED_ATTR) is True
    wrapped_fn = mcp._tools["query_rows"].fn
    assert getattr(wrapped_fn, _WRAPPED_ATTR, False) is True

    instrument(mcp, _obs())  # second call: no-op
    assert mcp._tools["query_rows"].fn is wrapped_fn  # NOT re-wrapped


# --- fail-loud config: RC001 HTTP=90 refuses at instrument() time ---
def test_instrument_fails_loud_on_inverted_cascade() -> None:
    async def t() -> dict[str, object]:
        return {}

    mcp = _FakeMcp({"x": t})
    bad = ObservabilitySettings(
        timeouts=TimeoutConfig(connect_s=5.0, http_s=90.0, tool_s=50.0),  # RC001 scar
        partition=BudgetPartition(),
    )
    with pytest.raises(ConfigurationError):
        instrument(mcp, bad)


# --- core wrapper: the outermost timeout guard fires (typed, NOT auth) ---
def test_wrapper_timeout_guard_fires() -> None:
    obs = _obs(tool_s=0.05)  # unvalidated: instrument_tool does not validate
    cap = obs.build_rate_cap()

    async def slow() -> dict[str, object]:
        await asyncio.sleep(1.0)
        return {}

    wrapped = instrument_tool(slow, tool_name="slow", obs=obs, rate_cap=cap)
    with pytest.raises(TimeoutError) as ei:
        asyncio.run(wrapped())
    msg = str(ei.value)
    assert "MCP_UPSTREAM_TIMEOUT" in msg
    assert "auth" not in msg.lower()  # never auth-shaped (contract §4.3)


# --- core wrapper: the rate cap REFUSES with the typed code (never queues) ---
def test_wrapper_rate_cap_refuses() -> None:
    obs = _obs()
    cap = RateCap(rate=1.0, window_s=1.0, burst=1.0)

    async def t() -> dict[str, object]:
        return {}

    wrapped = instrument_tool(t, tool_name="t", obs=obs, rate_cap=cap)
    asyncio.run(wrapped())  # first: ok
    with pytest.raises(RateCapExceeded) as ei:
        asyncio.run(wrapped())  # second: refused
    assert ei.value.code == "MCP_RATE_BUDGET_EXHAUSTED" and ei.value.retry_after_s > 0


# --- core wrapper: a honesty hide/flip is caught in-band ---
def test_wrapper_honesty_hide_caught() -> None:
    obs = _obs()
    cap = RateCap(rate=100.0, window_s=1.0, burst=100.0)

    async def hiding() -> dict[str, object]:
        return {"meta": {"stale_served": False}, "_upstream_meta": {"stale_served": True}}

    wrapped = instrument_tool(hiding, tool_name="q", obs=obs, rate_cap=cap)
    with pytest.raises(HonestySuppressionError):
        asyncio.run(wrapped())


# --- core wrapper: faithful honesty passes through ---
def test_wrapper_honesty_faithful_passes() -> None:
    obs = _obs()
    cap = RateCap(rate=100.0, window_s=1.0, burst=100.0)

    async def faithful() -> dict[str, object]:
        return {"meta": {"stale_served": True}, "_upstream_meta": {"stale_served": True}}

    wrapped = instrument_tool(faithful, tool_name="q", obs=obs, rate_cap=cap)
    out = asyncio.run(wrapped())
    assert out["meta"]["stale_served"] is True
