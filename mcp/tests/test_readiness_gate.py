"""Readiness callable gates tool availability on the satellite /ready (mount-seam).

A not-ready satellite yields a retryable cache-warming refusal (kind='warming')
BEFORE the tool endpoint is touched — classified as warming, never auth.
"""

from __future__ import annotations

import pytest

from asana_mcp.errors import McpToolError
from asana_mcp.schemas import RowsArgs
from asana_mcp.tools.discovery import list_entity_types_handler
from asana_mcp.tools.query import query_rows_handler


async def test_readiness_gate_blocks_discovery(cold_ctx):
    with pytest.raises(McpToolError) as ei:
        await list_entity_types_handler(cold_ctx)
    assert ei.value.kind == "warming"
    assert ei.value.code == "READINESS_NOT_READY"
    assert ei.value.retryable is True


async def test_readiness_gate_blocks_query(cold_ctx):
    with pytest.raises(McpToolError) as ei:
        await query_rows_handler(cold_ctx, "offer", RowsArgs())
    assert ei.value.kind == "warming"
    assert ei.value.kind != "auth"
