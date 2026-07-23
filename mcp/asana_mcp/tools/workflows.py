"""Read/disclosure tier (WS-5b / L1): ``list_report_workflows``.

Progressive MCP disclosure of the REGISTERED report-workflow SURFACE. This tool
reads the LIVE oracle — ``GET /api/v1/workflows`` (``api/routes/workflows.py``
``list_workflows``, backed by the ``_WORKFLOW_CONFIGS`` registry populated at
startup by ``api/lifespan.py``) — and returns the registered workflows with the
honesty-attestation vocabulary (``honest_empty`` / ``contract_complete``) lifted
UNWRAPPED-and-VISIBLE to the top level (C6 / SVR-5), exactly as the query tools do.

BOUNDARY — this is a PURE READ; it NEVER invokes a workflow (R7 / §5 HALT):
  * Invocation is exposed ONLY via ``POST /api/v1/workflows/{workflow_id}/invoke``
    — a DECLARED write-verb (``x-fleet-side-effects: asana_api/task``). Every
    currently-registered report workflow (insights-export, conversation-audit)
    UPLOADS a report file to Asana tasks and DELETES prior attachments on invoke
    (``automation/workflows/insights/workflow.py`` §"upload/delete",
    ``automation/workflows/conversation_audit/workflow.py:491-501``). That verb is
    deliberately NOT disclosed here. RB-1 confirm-gate posture is preserved: a pure
    read is a no-op for the gate, and disclosing the surface never arms the write.
  * Re-invoking a report workflow can RE-FIRE a consuming Asana listener — "re-run
    = re-trigger BY DESIGN" (scar SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER). Disclosure
    that only READS the registry cannot re-trigger anything; invocation would.

CONSUMPTION PREDICATE — CAPABILITY-NOW / consumption-post-KEYSTONE: the disclosed
verbs still run on the SHARED BOT PAT (S2S-JWT → bot PAT, resolved by
``api/dependencies.get_auth_context``) until the identity keystone (acting_agent +
delegating_user) lands in a cross-repo Phase-2. This ships SURFACE, NOT
audit-names-the-human. Built-unconsumed is named here, never reported as mission.

REFERENCE / THROWAWAY POSTURE (charter §5.3, MCP-REFERENCE-POSTURE-001): this
sidecar is a REFERENCE IMPLEMENTATION — reimplement against production contracts
at tech-transfer.
"""

from __future__ import annotations

from typing import Any

from asana_mcp.context import SidecarContext
from asana_mcp.envelopes import unwrap_outer
from asana_mcp.tools._common import ensure_ready, get_json

# The live disclosure oracle (READ-ONLY): GET /api/v1/workflows -> list_workflows.
# Trailing slash is load-bearing: the route is prefix="/api/v1/workflows" + "/", and
# the sidecar http client does NOT follow redirects — a 307 to the canonical slash
# would drop the Authorization header on the hop.
_WORKFLOWS_ORACLE_PATH = "/api/v1/workflows/"

# Non-drifting statement of the invoke boundary. True for ANY registered workflow,
# because the INVOKE ENDPOINT itself is the declared write-verb — independent of
# which workflows happen to be registered.
_INVOCATION_NOTE = (
    "Invocation runs ONLY via POST /api/v1/workflows/{workflow_id}/invoke — a "
    "declared write-verb (x-fleet-side-effects: asana_api/task; registered report "
    "workflows upload a report file to Asana tasks and delete prior attachments on "
    "invoke). It is intentionally NOT exposed by this read/disclosure surface "
    "(R7 / §5 write-verb boundary)."
)

_CONSUMPTION_POSTURE = (
    "CAPABILITY-NOW / consumption-post-KEYSTONE: disclosed verbs still run on the "
    "shared bot PAT (S2S-JWT -> bot PAT) until the identity keystone (acting_agent "
    "+ delegating_user) lands in a cross-repo Phase-2. This is SURFACE disclosure, "
    "NOT audit-names-the-human."
)


async def list_report_workflows_handler(ctx: SidecarContext) -> dict[str, Any]:
    """GET /api/v1/workflows -> disclose the REGISTERED report-workflow surface.

    Pure read of the live oracle; never invokes. The honesty attestations
    (``honest_empty`` / ``contract_complete``) are tool-computed over the live
    registry and surfaced at the TOP level so the LLM sees them plainly.
    """
    await ensure_ready(ctx)
    entries = unwrap_outer(await get_json(ctx, _WORKFLOWS_ORACLE_PATH))
    workflows = entries if isinstance(entries, list) else []
    count = len(workflows)
    return {
        # Oracle entries verbatim: {workflow_id, log_prefix, requires_data_client,
        # response_metadata_keys}. The oracle carries NO side-effect field, so the
        # write posture is stated once, honestly, below — never fabricated per-entry.
        "report_workflows": workflows,
        "report_workflows_count": count,
        # Honesty-attestation vocabulary (C6 / SVR-5), tool-computed over the oracle:
        "honest_empty": count == 0,  # a genuinely empty registry, not hidden/masked data
        "contract_complete": True,  # the COMPLETE registered set is disclosed (no filter/truncation)
        # Boundary + consumption posture, honestly labeled:
        "invocation_disclosed": False,
        "invocation_note": _INVOCATION_NOTE,
        "consumption_posture": _CONSUMPTION_POSTURE,
        "hint": (
            "These are the report workflows registered for API invocation. This tool "
            "DISCLOSES the surface only — it does not run anything. Invocation is a "
            "separate write-verb (writes Asana attachments) and is not exposed here. "
            "An empty list means no workflows are registered right now (e.g. startup "
            "registration did not complete) — an honest empty, not an error."
        ),
    }


def register(mcp: Any, ctx: SidecarContext) -> None:
    """Mount-seam item 2: register(mcp, ctx). Thin adapter over the pure handler."""

    @mcp.tool(
        name="list_report_workflows",
        description=(
            "Disclose the report workflows registered on the asana satellite "
            "(insights-export, conversation-audit, ...): each entry's workflow_id, "
            "log_prefix, requires_data_client, and response_metadata_keys. This is a "
            "READ/disclosure surface — it lists what exists and surfaces honesty flags "
            "(honest_empty, contract_complete). It does NOT invoke: invocation is a "
            "separate write-verb that writes Asana attachments and is not exposed here. "
            "Disclosed verbs run on the shared bot PAT until the identity keystone "
            "lands (CAPABILITY-NOW / consumption-post-KEYSTONE)."
        ),
    )
    async def list_report_workflows() -> dict[str, Any]:
        return await list_report_workflows_handler(ctx)
