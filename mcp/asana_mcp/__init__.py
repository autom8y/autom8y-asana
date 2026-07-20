"""asana_mcp — FastMCP sidecar over the autom8y-asana REST S2S surface.

REFERENCE / THROWAWAY POC (asana-mcp-v1 sprint-2). Enables felt-gate limb (a):
an agent, from schemas alone, answers a real business question via
list -> describe -> rows -> aggregate.

CONSTRAINT 5 (load-bearing): this package NEVER imports the ``autom8_asana``
domain SDK and makes ZERO direct Asana calls. It speaks HTTP only to the REST
S2S surface; auth joins the ``autom8y_core.TokenManager`` bridge (SVR-8).

``create_server`` is exposed via a lazy ``__getattr__`` so that ``import
asana_mcp`` (and the pure handler / envelope / error / schema layers) does NOT
require ``fastmcp`` and performs no import-time IO (C9a import-safety).
"""

from __future__ import annotations

from asana_mcp.context import SidecarContext, build_context
from asana_mcp.settings import Settings

__all__ = ["Settings", "SidecarContext", "build_context", "create_server"]


def __getattr__(name: str):  # PEP 562 lazy attribute
    if name == "create_server":
        from asana_mcp.server import create_server

        return create_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
