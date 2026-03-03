---
schema_version: "2.1"
session_id: session-20260303-134822-abd31a5b
status: PARKED
created_at: "2026-03-03T12:48:22Z"
initiative: 'N8N-CASCADE-FIX: Principled bottom-up bugfix for cascade resolution on S3 fast-path + EntityWriteRequest contract hardening'
complexity: MODULE
active_rite: 10x-dev
rite: 10x-dev
current_phase: design
parked_at: "2026-03-03T13:13:16Z"
parked_reason: auto-parked on Stop
---



# Session: N8N-CASCADE-FIX: Principled bottom-up bugfix for cascade resolution on S3 fast-path + EntityWriteRequest contract hardening

## Artifacts
- Spike: `docs/spikes/SPIKE-n8n-consumer-bugs.md` (root cause analysis, bug inventory, diagnostic steps)
- Frame: `.claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md` (5 workstreams, dependency graph, execution plan)
- Sprint: `.sos/sessions/session-20260303-134822-abd31a5b/SPRINT_CONTEXT.md`

## Scope

Two consumer-facing bugs from Damian's n8n integration:
- **B1 (P0):** S3 fast-path bypasses cascade validation → `office_phone` null → NOT_FOUND for 9/10 accounts on `POST /v1/resolve/unit`
- **B2 (P1):** `EntityWriteRequest` lacks `extra="forbid"` → unknown fields silently dropped

5 workstreams (WS-1 through WS-5) decomposed bottom-up. Phase A (WS-2 + WS-1) is P0 critical path.

## Blockers
None.

## Next Steps
1. Phase A: implement WS-2 (shared store population for Business fast-path) + WS-1 (cascade validation on S3 fast-path) — use `/build` with frame spec
2. Phase B: implement WS-3 (EntityWriteRequest extra=forbid) — quick standalone commit
3. Phases C + D: WS-4 + WS-5 hardening after P0/P1 shipped
