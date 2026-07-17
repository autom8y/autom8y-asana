"""SidecarContext — the FROZEN mount-seam substrate carried into every tool.

Mount-seam item 2 (verbatim): ``SidecarContext`` carries ``http`` (the
S2S-JWT-authed ``httpx.AsyncClient``), ``settings``, and ``readiness`` (a
callable proxying the satellite ``/ready``). No tool module creates its own
client/auth — every tool consumes ``ctx.http`` only.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from asana_mcp.bridge import build_http_client, make_readiness_probe
from asana_mcp.bridge import TokenProvider
from asana_mcp.settings import Settings


@dataclass
class SidecarContext:
    """The three FROZEN fields the seam carries into ``register(mcp, ctx)``."""

    http: httpx.AsyncClient
    settings: Settings
    readiness: Callable[[], Awaitable[bool]]


def build_context(
    settings: Settings,
    *,
    token_provider: TokenProvider | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SidecarContext:
    """Assemble the SidecarContext at CALL time (no import-time IO — C9a)."""
    http = build_http_client(settings, token_provider=token_provider, transport=transport)
    readiness = make_readiness_probe(http, settings)
    return SidecarContext(http=http, settings=settings, readiness=readiness)
