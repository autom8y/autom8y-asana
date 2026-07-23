"""WS-5b (L1): list_report_workflows — disclosure of the REGISTERED report-workflow
surface (GET /api/v1/workflows), honestly labeled.

Two-sided by design: the positive side proves the surface is disclosed with the
oracle metadata + honesty vocabulary; the negative sides prove (a) the write-verb
is NEVER disclosed (R7 / §5 boundary), (b) a genuinely empty registry surfaces
honest_empty rather than a masked error, and (c) the readiness gate fires BEFORE
the oracle is touched (warming, never auth).
"""

from __future__ import annotations

import httpx
import pytest
from asana_mcp.errors import McpToolError
from asana_mcp.tools.workflows import list_report_workflows_handler


async def test_discloses_registered_report_workflows(fake_ctx):
    """Positive: the two registered report workflows are disclosed with oracle metadata."""
    result = await list_report_workflows_handler(fake_ctx)

    assert result["report_workflows_count"] == 2
    ids = {w["workflow_id"] for w in result["report_workflows"]}
    assert ids == {"insights-export", "conversation-audit"}

    # oracle metadata is passed through verbatim (workflow_id, log_prefix,
    # requires_data_client, response_metadata_keys)
    insights = next(w for w in result["report_workflows"] if w["workflow_id"] == "insights-export")
    assert insights["log_prefix"] == "lambda_insights_export"
    assert insights["requires_data_client"] is True
    assert set(insights["response_metadata_keys"]) == {
        "total_tables_succeeded",
        "total_tables_failed",
    }

    # honesty-attestation vocabulary surfaced UNWRAPPED-and-VISIBLE at the top level
    assert result["honest_empty"] is False
    assert result["contract_complete"] is True


async def test_write_verb_is_never_disclosed(fake_ctx):
    """Negative (boundary): a PURE READ discloses the surface but NEVER the invoke write-verb."""
    result = await list_report_workflows_handler(fake_ctx)

    # the invoke verb is not offered — no callable, no truthy invocation flag
    assert result["invocation_disclosed"] is False

    # the boundary is stated honestly: the note NAMES the write-verb without exposing it
    note = result["invocation_note"]
    assert "POST /api/v1/workflows/{workflow_id}/invoke" in note
    assert "write-verb" in note
    assert "NOT exposed" in note

    # consumption predicate is carried verbatim-in-intent: CAPABILITY-NOW / bot PAT
    posture = result["consumption_posture"]
    assert "CAPABILITY-NOW / consumption-post-KEYSTONE" in posture
    assert "bot PAT" in posture
    assert "audit-names-the-human" in posture  # named as NOT-yet, never claimed


async def test_honest_empty_when_registry_empty(ctx_factory):
    """Negative (empty side): a genuinely empty registry -> honest_empty, not a masked error."""

    def _empty_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ready":
            return httpx.Response(200, json={"status": "ready"})
        if request.method == "GET" and request.url.path == "/api/v1/workflows/":
            return httpx.Response(200, json={"data": [], "meta": {"request_id": "req-empty"}})
        return httpx.Response(404, json={"error": {"code": "UNMAPPED_ROUTE"}})

    ctx = ctx_factory(_empty_handler)
    result = await list_report_workflows_handler(ctx)

    assert result["report_workflows_count"] == 0
    assert result["report_workflows"] == []
    assert result["honest_empty"] is True
    assert result["contract_complete"] is True
    assert result["invocation_disclosed"] is False


async def test_readiness_gate_fires_before_disclosure(cold_ctx):
    """Negative (readiness): a cold satellite -> retryable warming refusal, NOT auth."""
    with pytest.raises(McpToolError) as ei:
        await list_report_workflows_handler(cold_ctx)
    assert ei.value.kind == "warming"
    assert ei.value.kind != "auth"
    assert ei.value.code == "READINESS_NOT_READY"
    assert ei.value.retryable is True
