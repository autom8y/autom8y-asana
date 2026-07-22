"""Composite write tool (asana-mcp-v1, sprint-3): add_tag -> push(PUT-save) -> mark_complete.

THROWAWAY / REFERENCE-POSTURE PROTOTYPE. NOT production code. Do not promote before
the charter §4 probe rules COMMIT (constraint 8). At tech-transfer this is a REFERENCE
IMPLEMENTATION ONLY — reimplement against production contracts; do not patch these
shortcuts into production.

Charter rulings realized (DECISION-fleet-mcp-program-alignment-2026-07-17.md):
  - W-2  the ratified chain ships as ONE workflow-shaped tool, sequenced server-side,
         all-or-nothing (see the "all-or-nothing, honestly" note below for the exact,
         non-ACID meaning). Agents never sequence raw mutations.
  - W-3  idempotent end-to-end: the whole chain is safely re-runnable; a partial
         failure CONVERGES on safe re-run. Defanged by verb SELECTION, not by fixing
         the idempotency store (SCAR-IDEM-001 / SVR-6 left untouched by design).
  - W-4  "push" IS the save mechanism: PUT the task state back (idempotent by REST
         full-state PUT semantics).

Backing REST verbs (live at HEAD f3d8eec1, re-verified this sprint; SVR-7):
  - add_tag        POST /api/v1/tasks/{gid}/tags   body {tag_gid}            (tasks.py:524-570;
                   openapi_extra x-fleet-idempotency idempotent:True; docstring "no-op")
  - push(PUT-save) PUT  /api/v1/tasks/{gid}         body {name?,notes?,due_on?}(tasks.py:246-301)
  - mark_complete  PUT  /api/v1/tasks/{gid}         body {completed:true}     (tasks.py:246-301;
                   `completed` field :294)

  NUANCE surfaced honestly (not silently smoothed): the PUT /tasks/{gid} route stamps
  `x-fleet-idempotency {idempotent: False}` (tasks.py:254) because a *partial* update is
  not idempotent in general. W-4 rules the composite's push/mark_complete as idempotent
  under full-state / completed=true PUT semantics. This tool relies on the W-4 ruling,
  NOT on the route's generic x-fleet stamp. If a future push carried an *append*-shaped
  field the W-3 property would break — that is exactly what the B5 fail-loud contract
  guards (.ledge/specs/SPEC-fail-loud-idempotency-contract-b5.md).

Standing fences honored:
  - NEVER imports the autom8_asana domain SDK; makes ZERO direct Asana calls. Consumes
    ctx.http (the S2S-JWT-authed client injected per the frozen MOUNT-SEAM) to reach the
    autom8y-asana REST surface only (constraint 5).
  - EXPOSURE-GATED: register() attaches the tool ONLY when the write surface is enabled
    (ASANA_MCP_ENABLE_WRITE_SURFACE, default OFF). Build != expose; exposure-as-ratified
    is reserved behind W-5 (GATE-BW).
  - No httpx import here (repo TID251 ban); ctx.http is duck-typed (typed `Any`).

all-or-nothing, honestly (the backing API has NO multi-op transaction):
  The tool runs the three steps in order, server-side. On the FIRST failing step it
  STOPS, leaves already-committed steps committed (no rollback is possible), and returns
  a REFUSED-INCOMPLETE report naming exactly what committed vs not. It NEVER claims
  atomicity the backing API cannot give. Because every verb is idempotent, a safe re-run
  of the whole chain converges to the fully-applied state — that convergence IS the W-3
  property. "All-or-nothing" therefore means: the tool either completes the chain, or it
  refuses loudly with an honest partial-state receipt whose safe re-run converges.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from asana_mcp.errors import McpToolError
from asana_mcp.tools.confirm_gate import (
    REDEEM_OK,
    ConfirmationGate,
    build_confirmation_envelope,
    intent_fingerprint,
)
from asana_mcp.tools.tag_resolve import (
    TagNameCache,
    read_back_tag_state,
    resolve_tag_name,
    validate_tag_selector,
)

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime FastMCP dependency
    from collections.abc import Awaitable, Callable

    from asana_mcp.tools.tag_resolve import TagResolution


# --------------------------------------------------------------------------- #
# Seam contract (structural view; sprint-2 owns the CONCRETE classes)
# --------------------------------------------------------------------------- #
@runtime_checkable
class SidecarContext(Protocol):
    """Structural subset of the frozen MOUNT-SEAM SidecarContext consumed by THIS tool.

    sprint-2 owns the concrete class (carrying http/settings/readiness). This Protocol
    exists only so the module is independently testable and import-safe. `http` is typed
    Any to avoid importing httpx (repo TID251 ban); at runtime it is the S2S-JWT-authed
    httpx.AsyncClient the seam injects.
    """

    http: Any
    settings: Any


# --------------------------------------------------------------------------- #
# Exposure gate (default OFF) — build != expose (Potnia risk #2; W-5 / GATE-BW)
# --------------------------------------------------------------------------- #
WRITE_SURFACE_ENV = "ASANA_MCP_ENABLE_WRITE_SURFACE"
_TRUTHY = {"1", "true", "yes", "on"}


def write_surface_enabled(ctx: SidecarContext | None = None) -> bool:
    """Return True only if the write surface is explicitly enabled. Default: False.

    Precedence: an explicit boolean on ctx.settings.enable_write_surface (sprint-2 may
    add it) wins; otherwise the ASANA_MCP_ENABLE_WRITE_SURFACE env var. Absent/unset =>
    OFF, so the throwaway cannot leak as a ratified surface.
    """
    settings = getattr(ctx, "settings", None) if ctx is not None else None
    flag = getattr(settings, "enable_write_surface", None)
    if isinstance(flag, bool):
        return flag
    return os.environ.get(WRITE_SURFACE_ENV, "").strip().lower() in _TRUTHY


# --------------------------------------------------------------------------- #
# Result model — an honest, structured receipt (never claims atomicity)
# --------------------------------------------------------------------------- #
ATOMICITY_DISCLAIMER = (
    "NON-ATOMIC forward-apply. The backing Asana REST surface has no multi-op "
    "transaction, so steps that committed are NOT rolled back on a later failure. "
    "This tool reports exactly what committed; it never claims atomicity. Every verb "
    "is idempotent, so a safe re-run of the whole chain converges (W-3)."
)
RERUN_GUIDANCE = (
    "Safe to re-run this same tool call unchanged. add_tag no-ops if already applied, "
    "push(PUT-save) is a deterministic full-state save, mark_complete is true->true. "
    "The chain converges to the fully-applied state; no step double-applies."
)

_STATUS_COMPLETED = "completed"
_STATUS_REFUSED = "refused_incomplete"

_STEP_COMMITTED = "committed"
_STEP_FAILED = "failed"
_STEP_NOT_ATTEMPTED = "not_attempted"


@dataclass
class StepOutcome:
    name: str
    status: str = _STEP_NOT_ATTEMPTED
    http_status: int | None = None
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "http_status": self.http_status,
            "detail": self.detail,
        }


@dataclass
class CompositeWriteResult:
    status: str
    steps: list[StepOutcome]
    atomicity: str = ATOMICITY_DISCLAIMER
    rerun_guidance: str | None = None

    @property
    def committed(self) -> list[str]:
        return [s.name for s in self.steps if s.status == _STEP_COMMITTED]

    @property
    def not_committed(self) -> list[str]:
        return [s.name for s in self.steps if s.status != _STEP_COMMITTED]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "committed": self.committed,
            "not_committed": self.not_committed,
            "steps": [s.as_dict() for s in self.steps],
            "atomicity": self.atomicity,
            "rerun_guidance": self.rerun_guidance,
        }


# --------------------------------------------------------------------------- #
# Executor — the server-side, all-or-nothing (honest) sequencer
# --------------------------------------------------------------------------- #
async def execute_composite_write(
    ctx: SidecarContext,
    *,
    task_gid: str,
    tag_gid: str,
    save_fields: dict[str, Any] | None = None,
) -> CompositeWriteResult:
    """Run add_tag -> push(PUT-save) -> mark_complete against the REST surface via ctx.http.

    Returns a CompositeWriteResult. status == "completed" iff all three steps committed;
    otherwise "refused_incomplete" with a per-step receipt and re-run guidance.
    """
    steps = [
        StepOutcome("add_tag"),
        StepOutcome("push"),
        StepOutcome("mark_complete"),
    ]

    # Pre-flight input refusal (broken INPUT is refused before any backend call).
    invalid = _validate_inputs(task_gid, tag_gid)
    if invalid is not None:
        steps[0].detail = f"refused pre-flight: {invalid}"
        return _refuse(steps)

    # Step 1 — add_tag: POST /api/v1/tasks/{gid}/tags
    if not await _run_step(
        ctx, steps[0], "POST", f"/api/v1/tasks/{task_gid}/tags", {"tag_gid": tag_gid}
    ):
        return _refuse(steps)

    # Step 2 — push (PUT-save): PUT /api/v1/tasks/{gid}
    if not await _run_step(
        ctx, steps[1], "PUT", f"/api/v1/tasks/{task_gid}", dict(save_fields or {})
    ):
        return _refuse(steps)

    # Step 3 — mark_complete: PUT /api/v1/tasks/{gid} {completed: true}
    if not await _run_step(ctx, steps[2], "PUT", f"/api/v1/tasks/{task_gid}", {"completed": True}):
        return _refuse(steps)

    return CompositeWriteResult(status=_STATUS_COMPLETED, steps=steps)


def _validate_inputs(task_gid: str, tag_gid: str) -> str | None:
    if not task_gid or not str(task_gid).strip():
        return "task_gid is required and must be non-empty"
    if not tag_gid or not str(tag_gid).strip():
        return "tag_gid is required and must be non-empty"
    return None


async def _run_step(
    ctx: SidecarContext,
    step: StepOutcome,
    method: str,
    path: str,
    body: dict[str, Any],
) -> bool:
    """Execute one backing call; mutate `step`; return True iff committed (2xx)."""
    try:
        resp = await ctx.http.request(method, path, json=body)
    except McpToolError as err:
        # Already honestly classified (e.g. the bridge's S2S mint-failure
        # mapping: credential-invalid 401 vs auth-infra 503). Carry the shape
        # through the step receipt — NEVER relabel it a transport error (the
        # 401-fail-clean fix; the failure families never cross-dress).
        step.status = _STEP_FAILED
        step.http_status = err.status
        step.detail = f"{err.kind}: {err.message}"
        return False
    except Exception as exc:  # noqa: BLE001 - transport failure is a legitimate refusal
        step.status = _STEP_FAILED
        step.detail = f"transport error: {type(exc).__name__}: {exc}"
        return False

    step.http_status = getattr(resp, "status_code", None)
    if isinstance(step.http_status, int) and 200 <= step.http_status < 300:
        step.status = _STEP_COMMITTED
        step.detail = "ok"
        return True

    step.status = _STEP_FAILED
    step.detail = _error_detail(resp)
    return False


def _error_detail(resp: Any) -> str:
    code = getattr(resp, "status_code", "?")
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001 - non-JSON error bodies are tolerated
        return f"HTTP {code}"
    if isinstance(body, dict):
        return f"HTTP {code}: {body.get('error') or body.get('detail') or body}"
    return f"HTTP {code}"


def _refuse(steps: list[StepOutcome]) -> CompositeWriteResult:
    return CompositeWriteResult(
        status=_STATUS_REFUSED,
        steps=steps,
        rerun_guidance=RERUN_GUIDANCE,
    )


# --------------------------------------------------------------------------- #
# Dual-key orchestrator (WS-B2) — tag_gid | tag_name -> resolved add_tag
# --------------------------------------------------------------------------- #
# This layer wraps the UNCHANGED execute_composite_write: it (1) enforces the
# exactly-one dual-key contract, (2) resolves tag_name -> tag_gid read-only via the
# satellite #246 route (no new write verb — the HARD FENCE), (3) runs the existing
# add_tag->push->mark_complete chain against the resolved GID, and (4) reads the task
# back to confirm the tag applied (PLAY-3). execute_composite_write keeps its exact
# 3-step, gid-only behavior so its two-sided suite is untouched.


def _resolution_refusal(resolution_receipt: dict[str, Any]) -> dict[str, Any]:
    """Assemble a pre-write refusal (dual-key invalid, or name unresolved/error).

    No backend WRITE was attempted, so the write leg is null and nothing committed.
    """
    return {
        "status": _STATUS_REFUSED,
        "resolution": resolution_receipt,
        "write": None,
        "confirmation": None,
    }


def _resolution_receipt_from(resolution: TagResolution, tag_name: str) -> dict[str, Any]:
    receipt = {
        "selector": "tag_name",
        "requested": tag_name,
        "outcome": resolution.status,
        "tag_gid": resolution.tag_gid,
        "cache": resolution.cache,
        "scan_page_cap": resolution.scan_page_cap,
        "detail": resolution.detail,
    }
    if resolution.candidates:
        receipt["candidates"] = resolution.candidates
    return receipt


async def execute_tagged_write(
    ctx: SidecarContext,
    *,
    task_gid: str,
    tag_gid: str | None = None,
    tag_name: str | None = None,
    save_fields: dict[str, Any] | None = None,
    cache: TagNameCache | None = None,
) -> dict[str, Any]:
    """Dual-key composite write: resolve the tag selector, run the chain, confirm.

    Returns an assembled dict: ``resolution`` (always), ``write`` (the composite
    CompositeWriteResult dict, or None if refused pre-write), ``confirmation`` (the
    PLAY-3 read-back, or None), and an overall ``status``.
    """
    # 1 — dual-key contract: EXACTLY ONE of tag_gid | tag_name.
    selector_error = validate_tag_selector(tag_gid, tag_name)
    if selector_error is not None:
        return _resolution_refusal(
            {
                "selector": "invalid",
                "requested": {"tag_gid": tag_gid, "tag_name": tag_name},
                "outcome": "invalid_selector",
                "tag_gid": None,
                "cache": "n/a",
                "detail": selector_error,
            }
        )

    # 2 — resolve tag_name -> tag_gid (read-only), or take the provided tag_gid as-is.
    if tag_name is not None and str(tag_name).strip():
        try:
            resolution = await resolve_tag_name(ctx, tag_name, cache=cache)
        except McpToolError as err:
            receipt = {
                "selector": "tag_name",
                "requested": tag_name,
                "outcome": "resolution_error",
                "tag_gid": None,
                "cache": "n/a",
                "detail": err.message,
                "error": err.to_tool_payload(),
            }
            return _resolution_refusal(receipt)
        if not resolution.resolved:
            return _resolution_refusal(_resolution_receipt_from(resolution, tag_name))
        resolved_gid = resolution.tag_gid
        resolution_receipt = _resolution_receipt_from(resolution, tag_name)
    else:
        resolved_gid = str(tag_gid)
        resolution_receipt = {
            "selector": "tag_gid",
            "requested": tag_gid,
            "outcome": "provided",
            "tag_gid": resolved_gid,
            "cache": "n/a",
            "detail": "tag_gid supplied directly; no name resolution performed.",
        }

    # 3 — the UNCHANGED write chain against the resolved GID.
    result = await execute_composite_write(
        ctx, task_gid=task_gid, tag_gid=resolved_gid, save_fields=save_fields
    )

    # 4 — PLAY-3 read-back confirmation, once add_tag has actually committed.
    confirmation: dict[str, Any] | None = None
    if "add_tag" in result.committed and resolved_gid is not None:
        confirmation = await read_back_tag_state(ctx, task_gid, resolved_gid)

    return {
        "status": result.status,
        "resolution": resolution_receipt,
        "write": result.as_dict(),
        "confirmation": confirmation,
    }


# --------------------------------------------------------------------------- #
# MOUNT-SEAM entrypoint (frozen signature) — register(mcp, ctx)
# --------------------------------------------------------------------------- #
TOOL_NAME = "asana_complete_tagged_task"
TOOL_DESCRIPTION = (
    "Composite workflow (all-or-nothing, server-sequenced): add a tag to an Asana task, "
    "save the task state (PUT), then mark it complete. Idempotent end-to-end and safe to "
    "re-run; a partial failure converges on re-run. On any step failure the tool refuses "
    "loudly and reports exactly what committed vs not — it never claims atomicity (the "
    "backing API has no transaction).\n"
    "\n"
    "TAG SELECTOR (dual-key): supply EXACTLY ONE of tag_gid or tag_name (both or neither "
    "is a validation error). tag_name is resolved to a GID read-only via the satellite tag "
    "name-resolution route; the only write is still the single add_tag. Name matching is "
    "EXACT and case-sensitive (byte-for-byte). Asana tag names are NOT unique, so a name "
    "may be AMBIGUOUS (multiple matches) — the tool refuses and lists candidate GIDs; pass "
    "the intended tag_gid to disambiguate. A name MISS is bounded: the satellite scan caps "
    "at 100 pages (~10,000 tags) and does not report truncation on name queries, so 'not "
    "found' means 'not found within the bounded scan', NOT proven absent — if you expect "
    "the tag to exist, pass tag_gid directly. Name->GID resolutions are cached in-process "
    "(TTL-bounded); a tag RENAMED at the source may resolve to its OLD GID until the cache "
    "entry expires.\n"
    "\n"
    "CONSUMED-TRIGGER HAZARD (play/automation tags): a play/automation tag can be a "
    "CONSUMED trigger — the automation STRIPS the tag when it fires. Re-applying the tag "
    "RE-FIRES the automation. If a call LOOKS failed, do NOT blindly re-run against a real "
    "play tag: a re-apply can DOUBLE-TRIGGER a live business workflow. Check the read-back "
    "confirmation first.\n"
    "\n"
    "CONFIRMATION: after the write the tool reads the task back (explicit opt_fields) and "
    "reports the observed tag state, so you get a mechanism receipt that the tag actually "
    "applied. A tag absent-after-apply is a hint that a consumed-trigger automation fired.\n"
    "\n"
    "CONFIRM-BEFORE-FIRING GATE (R5 / RB-1 — REQUIRED): applying a tag can fire live "
    "business automations, so this tool is two-phase. Phase 1: call WITHOUT "
    "confirmation_token — NOTHING is written; you receive a confirmation_required "
    "envelope with a single-use, expiring confirmation_token bound to exactly these "
    "arguments. You MUST present the pending write to the HUMAN operator and wait for "
    "their explicit yes. Phase 2: only after the human approves, call again with the "
    "SAME arguments plus confirmation_token — the chain then executes. A token that is "
    "reused, expired, or presented with ANY changed argument is refused (zero writes) "
    "and a fresh confirmation is required. v1 posture: ALL tags are treated "
    "trigger-capable; do not assume any tag is exempt."
)


def register(mcp: Any, ctx: SidecarContext) -> None:
    """Attach the composite write tool to `mcp` (seam item 2). EXPOSURE-GATED.

    Attaches NOTHING unless the write surface is enabled (default OFF). `mcp` is
    duck-typed (real FastMCP in sprint-6 assembly; FakeMCP in tests) so this throwaway
    needs no FastMCP dependency and stays import-safe.
    """
    if not write_surface_enabled(ctx):
        return  # exposure gated OFF: the throwaway cannot leak as a ratified surface

    # One process-lifetime name->GID cache shared across tool invocations (TTL-bounded).
    tag_cache = TagNameCache()
    # RB-1 (R5): one process-lifetime confirm-before-firing gate. The EXPOSED
    # surface pauses for a human yes; the pure executors below it are unchanged
    # (the WS-B2 layering precedent), so their two-sided suites stay untouched.
    confirmation_gate = ConfirmationGate()

    async def asana_complete_tagged_task(
        task_gid: str,
        tag_gid: str | None = None,
        tag_name: str | None = None,
        name: str | None = None,
        notes: str | None = None,
        due_on: str | None = None,
        confirmation_token: str | None = None,
    ) -> dict[str, Any]:
        save_fields = {
            k: v for k, v in (("name", name), ("notes", notes), ("due_on", due_on)) if v is not None
        }

        # --- RB-1 confirm-before-firing gate (R5): fires BEFORE any backend call.
        fingerprint = intent_fingerprint(
            task_gid=task_gid, tag_gid=tag_gid, tag_name=tag_name, save_fields=save_fields
        )
        if confirmation_token is None:
            reason = "confirmation_required"
        else:
            outcome = confirmation_gate.redeem(confirmation_token, fingerprint)
            reason = None if outcome == REDEEM_OK else outcome
        if reason is not None:
            return build_confirmation_envelope(
                reason=reason,
                token=confirmation_gate.issue(fingerprint),
                ttl_s=confirmation_gate.ttl_s,
                task_gid=task_gid,
                tag_gid=tag_gid,
                tag_name=tag_name,
                save_fields=save_fields,
            )

        return await execute_tagged_write(
            ctx,
            task_gid=task_gid,
            tag_gid=tag_gid,
            tag_name=tag_name,
            save_fields=save_fields,
            cache=tag_cache,
        )

    _bind_tool(mcp, asana_complete_tagged_task, name=TOOL_NAME, description=TOOL_DESCRIPTION)


def _bind_tool(mcp: Any, fn: Callable[..., Awaitable[Any]], *, name: str, description: str) -> None:
    """Bind `fn` as an MCP tool via FastMCP's `.tool(...)` decorator (duck-typed).

    SEAM ASSUMPTION (verify at sprint-6 assembly): FastMCP exposes `.tool(name=...,
    description=...)` returning a decorator. If the real FastMCP API differs, this is the
    single line to adapt; the tool logic above is transport-agnostic.
    """
    mcp.tool(name=name, description=description)(fn)
