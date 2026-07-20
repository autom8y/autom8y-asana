# C2 Sandbox Re-PUT Probe — OPERATOR-WITNESSED SANDBOX PROBE ONLY

> **BUILD-ONLY.** This harness was authored at sprint-6 assembly and **NOT RUN**.
> It runs **only** when the operator executes it by hand, against a **SANDBOX** Asana
> workspace, at felt-gate staging. It is fail-loud-gated so it cannot run in CI, under
> the write-exposure flag, or without explicit operator confirmation.

## Why this exists

The rulings dossier (`DECISION-asana-mcp-v1-rulings-B1-B5-W5.md`) leaves one behavior
**deliberately unprobed** under the zero-direct-calls fence:

> **UV-P #4 / B5 C2 caveat / §8 exposure-precondition (b):** does a RE-PUT of
> `completed=true` on an **already-complete** Asana task **RE-FIRE** Asana Rules
> automations (notifications, section moves, workflow transitions)?

W-3 rules the composite chain "safe to re-run" because **state converges** (the task
ends completed either way). But **state convergence ≠ side-effect silence** — whether
downstream Rules re-fire is **Asana-server-side** behavior, unprobeable from the repo
and fenced from live calls. §8 makes exposure precondition (b) require this be probed
**at felt-gate staging, operator-witnessed**. This harness is that probe.

It **decides nothing**. It gives the operator a structured, timestamped evidence bundle
to **witness** the answer. The felt verdict remains the operator's alone.

## Fences (held by construction)

| Fence | How it is held |
|-------|----------------|
| Zero direct Asana calls | Drives the autom8y-asana **satellite** REST surface (`PUT /api/v1/tasks/{gid}`); the satellite forwards to Asana under its own bot PAT. No `app.asana.com` call here. |
| MCP process uninvolved | Standalone script; does **not** import `asana_mcp`. The sidecar makes zero Asana calls regardless. |
| No baked secrets | Base URL, bearer, task GID read from env **at run time**; refuses if any is missing. |
| Not automatable | Requires `--i-am-the-operator-in-a-sandbox`; refuses under `CI` or when `ASANA_MCP_ENABLE_WRITE_SURFACE` is set. |
| Non-destructive | Only re-asserts `completed=true` on a task the operator already completed in a **sandbox**. Never deletes; never touches production. |

## Run contract (operator, felt-gate staging, sandbox only)

```bash
export ASANA_MCP_C2_SATELLITE_BASE_URL="https://asana.sandbox.<...>"   # sandbox satellite REST
export ASANA_MCP_C2_SATELLITE_TOKEN="<operator-minted sandbox S2S bearer>"
export ASANA_MCP_C2_SANDBOX_TASK_GID="<already-complete sandbox task gid>"
# optional automated correlation of inbound Rules webhooks (else observe the workspace):
export ASANA_MCP_C2_WEBHOOK_EVIDENCE_URL="https://.../sandbox/rule-webhook-log"

python mcp/probes/c2_sandbox_reput_probe.py --i-am-the-operator-in-a-sandbox
```

Requires `httpx` (imported lazily inside the run path; already a sidecar dependency).

## What it captures (the evidence bundle → stdout JSON)

1. `webhook_before` — optional pre-probe snapshot of the sandbox Rules-webhook log.
2. `snapshot_0` — task state before (completed / modified_at).
3. `reput_1` — first `PUT {completed: true}` (status, body, timing).
4. `snapshot_1` + `webhook_after_1` — state + webhook log after re-PUT #1.
5. `reput_2` — second `PUT {completed: true}` after `--interval-s` (default 5s).
6. `snapshot_2` + `webhook_after_2` — state + webhook log after re-PUT #2.
7. `modified_at_delta_on_reput_2` — convenience signal: did `modified_at` change on the
   second (already-complete → complete) re-PUT? A change **may** indicate a re-fire; the
   operator confirms actual Rules side-effects by observing the sandbox workspace.

## Where it fits

- Feeds the **operator-witnessed** felt-gate staging observation. The operator attaches
  the bundle to the felt-gate **witness envelope** (authored by tech-transfer at
  `.sos/wip/asana-mcp-v1.felt-gate-envelope.md` — **not** this artifact and **not** the
  prototype-engineer's to write).
- Discharges §8 exposure-precondition (b): the composite's `push` + `mark_complete` legs
  carry governed `idempotent:False` (tasks.py:254); exposure proceeds only with the
  operator seeing the true idempotency posture **and** this C2 Rules-re-fire probed.
- `"PRs merged"` is **not** the gate. GATE-BW ratification + this probe are inputs to the
  witness; the operator is the sole closer.
