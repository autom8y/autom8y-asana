"""``asana_mcp.assembly`` — the sprint-6 mount-seam assembly entrypoint.

Realizes FROZEN mount-seam v1 item 4 assembly order (autom8y-asana/.sos/wip/
asana-mcp-v1.mount-seam.md:26):

    create_server()  ->  register(...) per tool  ->  instrument(...)

``create_server`` (s2) already registers the READ tools (discovery / query / resolve)
and exposes the concrete ``SidecarContext`` at ``mcp.sidecar_context``. This module
adds the EXPOSURE-GATED composite write tool (s3) then applies the observability +
guardrails wrap (s4). ``instrument()`` is idempotent (mount-seam item 3).

STANDING FENCES (held):
  * The composite write tool is registered ONLY when its exposure flag
    ``ASANA_MCP_ENABLE_WRITE_SURFACE`` is truthy — DEFAULT OFF (build != expose;
    W-5 / GATE-BW). ``composite_write.register`` SELF-GATES, so calling it here
    attaches NOTHING while the flag is off. This assembly never flips the flag.
  * This package NEVER imports the ``autom8_asana`` domain SDK and makes ZERO direct
    Asana calls (constraint 5). fastmcp is imported at CALL time only (C9a import-safety):
    importing ``asana_mcp.assembly`` pulls no fastmcp and does no IO.

REFERENCE / THROWAWAY POSTURE (charter §5.3): NOT production code. At tech-transfer
this is a REFERENCE IMPLEMENTATION ONLY — reimplement against production contracts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from asana_mcp.server import create_server
from asana_mcp.settings import Settings

if TYPE_CHECKING:  # annotation only — no runtime fastmcp import (C9a)
    from fastmcp import FastMCP


def build_instrumented_server(settings: Settings | None = None) -> FastMCP:
    """Assemble the fully-wired sidecar per the frozen mount-seam order.

    1. ``create_server()`` — s2 skeleton + READ tools; all config resolved at call time.
    2. ``register(...)``    — s3 composite write, EXPOSURE-GATED (default OFF).
    3. ``instrument(...)``  — s4 observability + guardrails wrap (idempotent); also
       wires per-client httpx traceparent onto ``ctx.http`` (FORK-D Pythia D3).

    Returns the instrumented FastMCP. With the write flag OFF (default) the exposed
    surface is exactly the five READ tools; the composite write tool is absent.
    """
    from asana_mcp.observability import instrument
    from asana_mcp.tools import composite_write

    mcp = create_server(settings)

    # EXPOSURE-GATED (W-5 / GATE-BW): register() self-gates on
    # ASANA_MCP_ENABLE_WRITE_SURFACE (default OFF) — attaches nothing while off.
    ctx = getattr(mcp, "sidecar_context", None)
    composite_write.register(mcp, ctx)

    # obs settings resolve at call time inside instrument() (from_env when None).
    instrument(mcp, settings)
    return mcp
