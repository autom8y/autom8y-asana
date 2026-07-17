"""Mount-seam conformance (FROZEN v1). Asserts the implemented signatures match
the seam verbatim. The create_server signature check runs WITHOUT fastmcp (the
fastmcp import is call-time only); the live build + tool enumeration is exercised
only when fastmcp is installed (asserted against the real FastMCP 3.4.4 API).
"""

from __future__ import annotations

import inspect

import httpx
import pytest

from asana_mcp.context import SidecarContext, build_context
from asana_mcp.settings import Settings
from asana_mcp.tools import discovery, query, resolve


def test_create_server_signature_frozen():
    from asana_mcp.server import create_server  # importable without fastmcp

    sig = inspect.signature(create_server)
    assert list(sig.parameters) == ["settings"]
    assert sig.parameters["settings"].default is None
    assert "FastMCP" in str(sig.return_annotation)


def test_register_signatures_frozen():
    for mod in (discovery, query, resolve):
        assert list(inspect.signature(mod.register).parameters) == ["mcp", "ctx"]


def test_sidecar_context_carries_exactly_the_three_seam_fields():
    assert set(SidecarContext.__dataclass_fields__) == {"http", "settings", "readiness"}


async def test_build_context_yields_the_seam_substrate():
    async def _tok() -> str:
        return "t"

    ctx = build_context(
        Settings(base_url="http://x"),
        token_provider=_tok,
        transport=httpx.MockTransport(lambda r: httpx.Response(200)),
    )
    try:
        assert isinstance(ctx, SidecarContext)
        assert isinstance(ctx.http, httpx.AsyncClient)
        assert ctx.settings.base_url == "http://x"
        assert callable(ctx.readiness)
    finally:
        await ctx.http.aclose()


def test_instrument_hook_point_left_for_sprint4():
    import asana_mcp.server as server

    # sprint-4 provides instrument(mcp, settings); sprint-2 must NOT define it.
    assert not hasattr(server, "instrument")


async def test_create_server_registers_exactly_the_five_read_tools(monkeypatch):
    pytest.importorskip("fastmcp")
    import asana_mcp.bridge as bridge

    async def _tok() -> str:
        return "t"

    # avoid the live TokenManager — inject a fake provider at the bridge seam
    monkeypatch.setattr(bridge, "_default_token_provider", lambda: _tok)
    from asana_mcp.server import create_server

    mcp = create_server(Settings(base_url="http://x"))
    assert getattr(mcp, "sidecar_context", None) is not None
    tools = await mcp.list_tools()  # FastMCP 3.4.4 API (probed live)
    names = {t.name for t in tools}
    assert names == {
        "list_entity_types",
        "describe_entity",
        "query_rows",
        "query_aggregate",
        "resolve_entity",
    }
    assert "match_business" not in names  # surface-not-POC (shape §0)
