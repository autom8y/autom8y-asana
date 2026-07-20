"""resolve_entity: identifier -> GID, native ResolutionResponse passthrough."""

from __future__ import annotations

from asana_mcp.schemas import ResolveArgs
from asana_mcp.tools.resolve import resolve_entity_handler


async def test_resolve_entity_returns_results_and_meta(fake_ctx):
    args = ResolveArgs(criteria=[{"phone": "+15551234567", "vertical": "dental"}])
    result = await resolve_entity_handler(fake_ctx, "unit", args)
    assert result["entity_type"] == "unit"
    assert result["result_count"] == 2
    assert result["results"][0]["gid"] == "1234567890123456"
    assert result["results"][1]["error"] == "NOT_FOUND"
    assert result["meta"]["resolved_count"] == 1
    # resolve has NO honesty attestations -> none fabricated
    assert "stale_served" not in result
