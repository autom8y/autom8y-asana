"""S2S-JWT bridge for the asana_mcp sidecar (constraint 5 / SVR-8 / A1).

The sidecar speaks HTTP ONLY to the autom8y-asana REST S2S surface. It NEVER
imports the autom8_asana domain SDK and makes ZERO direct Asana API calls. Auth
JOINS the existing fleet bridge — ``autom8y_core.TokenManager`` (SVR-8) — with
zero new auth-minting code.

The live ``autom8y_core`` import is LAZY (inside the default provider) so that the
pure tool logic + envelope/error/schema layers import WITHOUT pulling
autom8y_core, and so ``import asana_mcp`` performs no IO at import time (C9a).
The ``token_provider`` / ``transport`` seams let tests inject a fake token and a
fake transport, so unit tests never touch live TokenManager and never hit Asana.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx

from asana_mcp.settings import Settings

TokenProvider = Callable[[], Awaitable[str]]


def _default_token_provider() -> TokenProvider:
    """Live provider: mint/refresh the S2S JWT via ``autom8y_core.TokenManager``.

    This lazy import is the ONLY sanctioned autom8y_core touch-point (SVR-8). It
    never imports autom8_asana.
    """
    from autom8y_core import TokenManager  # sanctioned fleet bridge (SVR-8)

    token_manager = TokenManager.from_env()

    async def _provide() -> str:
        return await token_manager.get_token_async()

    return _provide


def build_http_client(
    settings: Settings,
    *,
    token_provider: TokenProvider | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """Build the S2S-JWT-authed ``httpx.AsyncClient`` the seam's SidecarContext carries.

    An async request event-hook attaches ``Authorization: Bearer <jwt>`` per
    request, so token refresh is transparent. ``base_url`` is the satellite REST
    surface — NEVER Asana's API (constraint 5).
    """
    provider = token_provider or _default_token_provider()

    async def _attach_bearer(request: httpx.Request) -> None:
        token = await provider()
        request.headers["Authorization"] = f"Bearer {token}"

    timeout = httpx.Timeout(settings.request_timeout_s, connect=settings.connect_timeout_s)
    return httpx.AsyncClient(
        base_url=settings.base_url,
        timeout=timeout,
        transport=transport,
        event_hooks={"request": [_attach_bearer]},
        headers={"user-agent": "asana-mcp-sidecar/0.1 (reference-poc)"},
    )


def make_readiness_probe(
    http: httpx.AsyncClient, settings: Settings
) -> Callable[[], Awaitable[bool]]:
    """Readiness callable proxying the satellite ``/ready`` (mount-seam item 2).

    ``200`` -> ready; anything else (``503`` warming) -> not ready. On a transport
    error, honor the configured posture (default fail-CLOSED -> not ready).
    sprint-4 finalizes the C9 posture declaration.
    """

    async def _ready() -> bool:
        try:
            resp = await http.get(settings.ready_path)
        except httpx.HTTPError:
            return settings.readiness_fail_open
        return resp.status_code == 200

    return _ready
