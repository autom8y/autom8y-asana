"""FastMCP server factory (mount-seam item 1).

``create_server(settings)`` resolves ALL config at CALL time (no import-time
settings/IO/network — C9a), builds the SidecarContext, creates the FastMCP
instance, and registers the sprint-2 READ tools (1-5) via each tool module's
``register(mcp, ctx)`` (seam item 2). It returns the FastMCP.

FROZEN signature honored verbatim: ``def create_server(settings: Settings | None
= None) -> FastMCP``. ``fastmcp`` is imported INSIDE the function (and under
TYPE_CHECKING for the annotation) so that ``import asana_mcp.server`` — and the
whole package — imports WITHOUT fastmcp and does no import-time IO.

Deferred to later sprints (hook points left, not called here):
* seam item 3 — sprint-4 provides ``instrument(mcp, settings) -> FastMCP`` (idempotent).
* seam item 4 — sprint-6 assembles: create_server() -> register(...) per tool -> instrument(...).
sprint-3's write tools register against the SAME SidecarContext, exposed as the
documented ``server.sidecar_context`` attribute (a throwaway-posture convenience;
production assembly would thread ctx through an explicit container). Downstream
may equivalently rebuild it via ``build_context(settings)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from asana_mcp.context import SidecarContext, build_context
from asana_mcp.settings import Settings

if TYPE_CHECKING:  # annotation only — no runtime fastmcp import (C9a)
    from fastmcp import FastMCP


def create_server(settings: Settings | None = None) -> FastMCP:
    """Build the read-surface FastMCP sidecar. Config resolved at call time."""
    from fastmcp import FastMCP  # call-time import — keeps the package import-safe

    resolved = settings if settings is not None else Settings.from_env()
    ctx: SidecarContext = build_context(resolved)

    mcp = FastMCP(name="asana-mcp")

    # Register the sprint-2 read tools (1-5) via the frozen register(mcp, ctx) seam.
    from asana_mcp.tools import discovery, query, resolve

    discovery.register(mcp, ctx)  # list_entity_types, describe_entity (thin tier)
    query.register(mcp, ctx)  # query_rows, query_aggregate (rich native tier)
    resolve.register(mcp, ctx)  # resolve_entity (native)
    # tool 6 match_business is surface-not-POC — deliberately NOT registered.

    # Expose ctx for downstream assembly (sprint-3 write tools, sprint-6 instrument).
    # Defensive: some server classes may forbid attribute assignment.
    try:
        mcp.sidecar_context = ctx  # type: ignore[attr-defined]
    except (AttributeError, TypeError):  # pragma: no cover - rebuild via build_context()
        pass

    return mcp
