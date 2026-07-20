"""Shared tool-layer helpers: readiness gate, HTTP execution, result shaping.

These are PURE functions over ``SidecarContext`` — independently unit-testable
against faked HTTP, with no fastmcp dependency. The ``register(mcp, ctx)``
adapters in each tool module are thin wrappers over these handlers.
"""

from __future__ import annotations

from typing import Any

import httpx

from asana_mcp.context import SidecarContext
from asana_mcp.envelopes import extract_honesty, unwrap_outer
from asana_mcp.errors import McpToolError, map_http_error


async def ensure_ready(ctx: SidecarContext) -> None:
    """Gate tool availability on the satellite ``/ready`` (seam readiness callable).

    Not-ready -> a retryable cache-warming refusal (C3), NEVER auth-shaped. This
    fires BEFORE the tool endpoint is called, so an agent gets an honest "warming,
    retry" signal rather than a confusing downstream failure.
    """
    if not await ctx.readiness():
        raise McpToolError(
            "The asana satellite is not ready (cache warming / startup discovery "
            "incomplete). Retry shortly — this is transient, NOT an auth failure.",
            kind="warming",
            retryable=True,
            status=503,
            retry_after=30.0,
            code="READINESS_NOT_READY",
        )


async def get_json(ctx: SidecarContext, path: str) -> Any:
    """GET ``path`` on the S2S surface; raise a classified error on non-200."""
    try:
        resp = await ctx.http.get(path)
    except httpx.HTTPError as exc:
        raise McpToolError(
            f"Transport error reaching the S2S surface: {exc}",
            kind="server",
            retryable=True,
        ) from exc
    if resp.status_code != 200:
        raise map_http_error(resp)
    return resp.json()


async def post_json(ctx: SidecarContext, path: str, body: dict[str, Any]) -> Any:
    """POST ``body`` to ``path`` on the S2S surface; raise on non-200."""
    try:
        resp = await ctx.http.post(path, json=body)
    except httpx.HTTPError as exc:
        raise McpToolError(
            f"Transport error reaching the S2S surface: {exc}",
            kind="server",
            retryable=True,
        ) from exc
    if resp.status_code != 200:
        raise map_http_error(resp)
    return resp.json()


def shape_execution_result(raw: Any, *, entity_type: str, data_label: str) -> dict[str, Any]:
    """Unwrap the double-envelope and surface honesty fields UNWRAPPED-and-VISIBLE.

    The honesty attestations (stale_served / honest_empty / contract_complete —
    C6 / SVR-5) are lifted to the TOP LEVEL of the returned dict so the LLM sees
    them plainly, never buried in nested meta. Only fields the endpoint actually
    emitted are surfaced (aggregate emits only stale_served). sprint-4
    contract-tests this presence.
    """
    inner = unwrap_outer(raw)
    if isinstance(inner, dict):
        data = inner.get("data", inner.get("results", []))
        meta = inner.get("meta", {})
    else:
        data, meta = inner, {}
    result: dict[str, Any] = {
        "entity_type": entity_type,
        data_label: data,
        f"{data_label}_count": len(data) if isinstance(data, list) else None,
        "meta": meta,
    }
    result.update(extract_honesty(meta))  # top-level honesty passthrough
    return result
