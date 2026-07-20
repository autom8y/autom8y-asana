"""Rich, native-shaped EXECUTION tier (C1): query_rows + query_aggregate.

Hand-authored from the native RowsRequest / AggregateRequest models (C2 / R6 —
spec-driven generation is impossible because the execution router is hidden,
SVR-2). The honesty attestations (stale_served / honest_empty / contract_complete)
are surfaced UNWRAPPED-and-VISIBLE at the top level of the tool result (C6 /
SVR-5); sprint-4 contract-tests their presence.
"""

from __future__ import annotations

from typing import Any

from asana_mcp.context import SidecarContext
from asana_mcp.schemas import AggregateArgs, RowsArgs
from asana_mcp.tools._common import ensure_ready, post_json, shape_execution_result


async def query_rows_handler(
    ctx: SidecarContext, entity_type: str, args: RowsArgs
) -> dict[str, Any]:
    """POST /v1/query/{entity_type}/rows — the workhorse row query."""
    await ensure_ready(ctx)
    body = args.model_dump(exclude_none=True)
    raw = await post_json(ctx, f"/v1/query/{entity_type}/rows", body)
    return shape_execution_result(raw, entity_type=entity_type, data_label="rows")


async def query_aggregate_handler(
    ctx: SidecarContext, entity_type: str, args: AggregateArgs
) -> dict[str, Any]:
    """POST /v1/query/{entity_type}/aggregate — counts / sums / group-bys."""
    await ensure_ready(ctx)
    body = args.model_dump(exclude_none=True)
    raw = await post_json(ctx, f"/v1/query/{entity_type}/aggregate", body)
    return shape_execution_result(raw, entity_type=entity_type, data_label="groups")


def register(mcp: Any, ctx: SidecarContext) -> None:
    """Mount-seam item 2: register(mcp, ctx)."""

    @mcp.tool(
        name="query_rows",
        description=(
            "The workhorse: return filtered rows of a business entity (business, "
            "contact, offer, unit, process). Supports composable where-predicates, "
            "select, order, and pagination. The result surfaces honesty flags "
            "(stale_served, honest_empty, contract_complete) so you know if the data "
            "was served stale or an empty result is genuine."
        ),
    )
    async def query_rows(entity_type: str, args: RowsArgs) -> dict[str, Any]:
        return await query_rows_handler(ctx, entity_type, args)

    @mcp.tool(
        name="query_aggregate",
        description=(
            "Compute counts / sums / group-bys over a business entity (pipeline "
            "metrics). Group by 1-5 columns and apply 1-10 aggregations, with "
            "optional pre-filter (where) and post-filter (having). The result "
            "surfaces the stale_served honesty flag."
        ),
    )
    async def query_aggregate(entity_type: str, args: AggregateArgs) -> dict[str, Any]:
        return await query_aggregate_handler(ctx, entity_type, args)
