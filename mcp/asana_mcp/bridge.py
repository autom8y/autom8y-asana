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

from asana_mcp.errors import McpToolError
from asana_mcp.settings import Settings

TokenProvider = Callable[[], Awaitable[str]]


def _classify_mint_failure(exc: BaseException) -> McpToolError | None:
    """Map an S2S token-MINT failure to an honest, correctly-classified error.

    The 401-fail-clean fix (operator ruling R21, Lane 1): with the daily-tool
    credential rotatable, a revoked/invalid ``sa_*`` pair must present CLEANLY
    — auth-shaped, non-retryable, remediation named — instead of erupting as a
    raw SDK traceback or being mislabeled a transport error. The two failure
    families NEVER cross-dress (the C3 / s4-posture discipline, applied at the
    MINT seam): credential-invalid is 401-shaped and non-retryable; auth-INFRA
    trouble (exchange unreachable / retries exhausted) is 503-shaped and
    retryable, explicitly NOT a credential failure.

    Classification is by exception-class NAME across the MRO — deliberately no
    ``autom8y_core`` import (C9a import-safety: the SDK stays a lazy, run-time
    dependency; tests fake the taxonomy with same-named classes). Hierarchy at
    autom8y-core 4.9.0: ``InvalidServiceKeyError`` and ``RetryExhaustedError``
    both subclass ``TokenAcquisitionError``, so the invalid-key check runs
    FIRST. Anything unrecognized returns None and propagates untouched — this
    seam never over-claims.
    """
    mro_names = {c.__name__ for c in type(exc).__mro__}
    if "InvalidServiceKeyError" in mro_names:
        return McpToolError(
            "The MCP mount's service-account credentials were REJECTED at S2S "
            "token mint (the auth server reports them invalid or revoked). "
            "This is NOT cache warming and NOT a satellite failure — retrying "
            "cannot succeed. Likely cause: the credential was rotated or "
            "revoked. Remediation: update the CLIENT_ID / CLIENT_SECRET values "
            "in the mount's MCP env entry and restart the session.",
            kind="auth",
            retryable=False,
            status=401,
            code="S2S_MINT_CREDENTIALS_INVALID",
        )
    if "TokenAcquisitionError" in mro_names:
        return McpToolError(
            "S2S token mint failed against the auth service (exchange "
            "unreachable, transient error, or retries exhausted). This is an "
            "auth-INFRASTRUCTURE condition — retryable — and explicitly NOT a "
            "credential failure: do not rotate or change CLIENT_ID / "
            "CLIENT_SECRET on this signal.",
            kind="server",
            retryable=True,
            status=503,
            retry_after=30.0,
            code="S2S_MINT_UNAVAILABLE",
        )
    return None


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
        try:
            token = await provider()
        except McpToolError:
            raise  # already honestly classified (injected providers may pre-shape)
        except Exception as exc:
            mapped = _classify_mint_failure(exc)
            if mapped is not None:
                raise mapped from exc
            raise  # never over-claim: unknown failures propagate untouched
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
