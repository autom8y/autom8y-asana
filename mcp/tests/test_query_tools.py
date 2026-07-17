"""Rich native tier (C1): query_rows + query_aggregate, with honesty passthrough.

The honesty attestations (stale_served / honest_empty / contract_complete, SVR-5)
MUST be surfaced UNWRAPPED-and-VISIBLE at the TOP LEVEL of the tool result — this
is what sprint-4 contract-tests; sprint-2 makes it true.
"""

from __future__ import annotations

from asana_mcp.schemas import AggregateArgs, RowsArgs
from asana_mcp.tools.query import query_aggregate_handler, query_rows_handler


async def test_query_rows_unwraps_and_surfaces_honesty_top_level(fake_ctx):
    result = await query_rows_handler(fake_ctx, "offer", RowsArgs(select=["office_phone", "vertical"]))
    assert result["entity_type"] == "offer"
    assert result["rows"] == [{"office_phone": "+15551234567", "vertical": "dental"}]
    assert result["rows_count"] == 1
    # honesty fields lifted to TOP LEVEL (unwrapped + visible):
    assert result["stale_served"] is False
    assert result["honest_empty"] is False
    assert result["contract_complete"] is True
    # inner meta still present for completeness
    assert result["meta"]["total_count"] == 1
    assert result["meta"]["project_gid"] == "1200653012566782"


async def test_query_aggregate_surfaces_only_emitted_honesty(fake_ctx):
    args = AggregateArgs(group_by=["vertical"], aggregations=[{"column": "office_phone", "agg": "count"}])
    result = await query_aggregate_handler(fake_ctx, "offer", args)
    assert result["groups"] == [{"vertical": "dental", "count_office_phone": 5}]
    assert result["stale_served"] is True  # top-level, unwrapped
    # AggregateMeta does NOT emit honest_empty / contract_complete -> NOT fabricated:
    assert "honest_empty" not in result
    assert "contract_complete" not in result


async def test_query_rows_predicate_where_is_forwarded(fake_ctx):
    # flat-array predicate sugar is accepted by the hand-authored schema
    args = RowsArgs(where=[{"field": "vertical", "op": "eq", "value": "dental"}], limit=10)
    result = await query_rows_handler(fake_ctx, "offer", args)
    assert result["rows_count"] == 1
