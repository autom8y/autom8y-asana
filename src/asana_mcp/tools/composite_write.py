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

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime FastMCP dependency
    from collections.abc import Awaitable, Callable


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
    if not await _run_step(
        ctx, steps[2], "PUT", f"/api/v1/tasks/{task_gid}", {"completed": True}
    ):
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
# MOUNT-SEAM entrypoint (frozen signature) — register(mcp, ctx)
# --------------------------------------------------------------------------- #
TOOL_NAME = "asana_complete_tagged_task"
TOOL_DESCRIPTION = (
    "Composite workflow (all-or-nothing, server-sequenced): add a tag to an Asana task, "
    "save the task state (PUT), then mark it complete. Idempotent end-to-end and safe to "
    "re-run; a partial failure converges on re-run. On any step failure the tool refuses "
    "loudly and reports exactly what committed vs not — it never claims atomicity (the "
    "backing API has no transaction)."
)


def register(mcp: Any, ctx: SidecarContext) -> None:
    """Attach the composite write tool to `mcp` (seam item 2). EXPOSURE-GATED.

    Attaches NOTHING unless the write surface is enabled (default OFF). `mcp` is
    duck-typed (real FastMCP in sprint-6 assembly; FakeMCP in tests) so this throwaway
    needs no FastMCP dependency and stays import-safe.
    """
    if not write_surface_enabled(ctx):
        return  # exposure gated OFF: the throwaway cannot leak as a ratified surface

    async def asana_complete_tagged_task(
        task_gid: str,
        tag_gid: str,
        name: str | None = None,
        notes: str | None = None,
        due_on: str | None = None,
    ) -> dict[str, Any]:
        save_fields = {
            k: v
            for k, v in (("name", name), ("notes", notes), ("due_on", due_on))
            if v is not None
        }
        result = await execute_composite_write(
            ctx, task_gid=task_gid, tag_gid=tag_gid, save_fields=save_fields
        )
        return result.as_dict()

    _bind_tool(mcp, asana_complete_tagged_task, name=TOOL_NAME, description=TOOL_DESCRIPTION)


def _bind_tool(mcp: Any, fn: Callable[..., Awaitable[Any]], *, name: str, description: str) -> None:
    """Bind `fn` as an MCP tool via FastMCP's `.tool(...)` decorator (duck-typed).

    SEAM ASSUMPTION (verify at sprint-6 assembly): FastMCP exposes `.tool(name=...,
    description=...)` returning a decorator. If the real FastMCP API differs, this is the
    single line to adapt; the tool logic above is transport-agnostic.
    """
    mcp.tool(name=name, description=description)(fn)
