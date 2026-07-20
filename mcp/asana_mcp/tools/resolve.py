"""resolve_entity — identifier (phone/vertical, offer_id, ...) -> Asana task GID.

Hand-authored from the native ResolutionRequest model. resolve's response has no
honesty attestations (they are rows-specific), so none are fabricated — the
result surfaces the native ResolutionMeta as-is.
"""

from __future__ import annotations

from typing import Any

from asana_mcp.context import SidecarContext
from asana_mcp.envelopes import unwrap_outer
from asana_mcp.schemas import ResolveArgs
from asana_mcp.tools._common import ensure_ready, post_json


async def resolve_entity_handler(
    ctx: SidecarContext, entity_type: str, args: ResolveArgs
) -> dict[str, Any]:
    """POST /v1/resolve/{entity_type} — batch identifier resolution."""
    await ensure_ready(ctx)
    body = args.model_dump(exclude_none=True)
    raw = await post_json(ctx, f"/v1/resolve/{entity_type}", body)
    inner = unwrap_outer(raw)  # {"results": [...], "meta": {...}}
    results = inner.get("results", []) if isinstance(inner, dict) else []
    meta = inner.get("meta", {}) if isinstance(inner, dict) else {}
    return {
        "entity_type": entity_type,
        "results": results,  # [{gid, gids?, match_count, error?, ...}]
        "result_count": len(results) if isinstance(results, list) else None,
        "meta": meta,  # {resolved_count, unresolved_count, ...}
    }


def register(mcp: Any, ctx: SidecarContext) -> None:
    """Mount-seam item 2: register(mcp, ctx)."""

    @mcp.tool(
        name="resolve_entity",
        description=(
            "Resolve business identifiers (phone/vertical, offer_id, contact_email, "
            "...) to Asana task GIDs, in batch. Use GET /v1/resolve/{entity_type}/"
            "schema (via describe flows) to discover valid criterion fields per type."
        ),
    )
    async def resolve_entity(entity_type: str, args: ResolveArgs) -> dict[str, Any]:
        return await resolve_entity_handler(ctx, entity_type, args)
