---
type: decision
decision_subtype: doctrine-debt-ledger
slug: mcp-doctrine-debt-ledger-D1-D11
status: proposed
date: 2026-07-17
rite: rnd
initiative: asana-mcp-v1
charter: .ledge/decisions/DECISION-fleet-mcp-program-alignment-2026-07-17.md
upstream:
  - .ledge/spikes/SPIKE-mcp-substrate-concepts-2026-07-17.md   # §D D1-D11, §E kills
  - autom8y-asana/.sos/wip/frames/asana-mcp-v1.shape.md         # §10 defer_registry
evidence: MODERATE (inherited from the slate ceiling; session-internal critics only)
---

# DECISION: MCP doctrine-debt-ledger — D1-D11 (reference-posture; probe-COMMIT-gated)

Mechanical capture of the fleet-MCP second-evidence-leg debt so nothing is lost
between MCP #1 (asana) and the deferred MCP #2 (autom8y-data). **These are LEDGER
ENTRIES ONLY.** Filing this document does NOT authorize building, extracting, or
promoting any D-item. It records what MUST be evaluated *if and only if* the
second leg is committed.

## Sole trigger (binding)

> **The charter §4 second-leg probe ruling COMMIT is the SOLE trigger** that
> converts any D-item below from *ledgered* to *mandatory-to-evaluate*
> (charter §4:73-78; shape §10:587). The probe entry is created at v1 ship time
> and stands +2 weeks after the operator closes the v1 felt-gate. On the probe's
> **PARK** or **KILL** ruling, every D-item **stays ledgered** — untouched.

**Promotion bar (why these wait):** per the reference-then-promote pipeline
(executed twice from asana — `envelopes.py`, `health.py`, each *after* a real
second consumer) and the R11 bar (twice-proven OR rite-disjoint critic-STRONG).
The slate is self-graded MODERATE (session-internal critics only), so nothing
clears R11 yet (slate :259-262). Reference-posture is fenced across every v1
sprint (charter V-1 :21-24; constraint 8 no-promotion-before-probe-COMMIT).

## D-items (slate §D:257-294 — verbatim-faithful; each names the §4 probe COMMIT)

Every entry's conversion trigger is identical: **charter §4 probe COMMIT** (stated
once above; re-tagged per entry per the sprint-1 exit criterion).

- **D1 — FastMCP-over-fleet-REST sidecar scaffold/template** (the "satellite MCP
  template"). _Trigger: §4 probe COMMIT._
- **D2 — Tool-authoring convention claims**: ~8-15 workflow-shaped tool grain,
  sidecar-over-REST, hand-author-from-Pydantic — all N=1 pattern claims until #2
  fires. _Trigger: §4 probe COMMIT._
- **D3 — Typed-client extension** (AsanaQueryClient → aggregate/resolve/match) and
  `require_caller_subject` allowlist promotion into autom8y-auth — one consumer
  each today. _Trigger: §4 probe COMMIT._
- **D4 — `contracts.mcp` manifest slot** — deferred at N=0; **evaluate against the
  doctrine critic's cheaper alternative first**: carry the tool surface as governed
  `x-fleet-*` OpenAPI annotations (zero a8 schema change, visible to existing
  GOV-009 tooling). _Trigger: §4 probe COMMIT._
- **D5 — Satellite-dispatch YAML extraction into one reusable workflow** — already
  N=5 hand-copied; a 6th copy for the MCP is the strongest duplication signal yet.
  Freebie debt-paydown the MCP work can trigger. _Trigger: §4 probe COMMIT._
- **D6 — Shared honesty/freshness mixin in `autom8y_api_schemas.meta`** — only
  after autom8y-data's genuinely divergent shape (DataQuality / degraded_paths /
  WindowAlignmentVerdict / RefusedResult) exists to reconcile against (see E1).
  _Trigger: §4 probe COMMIT._
- **D7 — Cross-MCP tool namespacing convention** — **must land before two servers
  are reachable from one client**: asana-mcp and data-mcp would both author
  `query_rows`/`query_aggregate`; nothing in `.know` addresses per-server tool-name
  collision (the OperationRegistry governs operationId uniqueness within one merged
  spec, not client-facing tool names). _Trigger: §4 probe COMMIT._
- **D8 — Client-side fleet-MCP discovery/config distribution** — no
  `.mcp.json`/mcpServers distribution mechanism exists anywhere; without it every
  new fleet MCP is hand-edited client config, the exact per-satellite toil this
  program exists to prevent. Candidate owner: the api-gateway fleet tool catalog.
  _Trigger: §4 probe COMMIT._
- **D9 — Repeatable runtime tool-ergonomics eval harness** — semantic-score is
  static-only; the spike's POC criterion ("tool-selection quality in Claude Code vs
  CLI baseline") is one-shot. A per-MCP tool-USE eval becomes the gate that stops
  tool-count/ambiguity bloat at #2 (`eval-harness-shape` skill exists as a starting
  shape). Per shape §10: the felt-gate uses ONE-SHOT POC evidence; the harness
  stays **LEDGERED, NOT built**. _Trigger: §4 probe COMMIT._
- **D10 — Sidecar↔service behavioral contract test across independent deploys** —
  A5 guards schema byte-identity only; nothing gates envelope/503/honesty *response
  semantics* when the parent satellite rolls out independently. Needed under either
  B1 placement. _Trigger: §4 probe COMMIT._
- **D11 — Readiness-proxy helper extraction** — only if #2 exhibits the same shape
  (C3). _Trigger: §4 probe COMMIT._

## Charter non-goals (shape §10:588-593 — do not drift)

- No fleet MCP roadmap beyond the probe.
- No parallel data-MCP (#2) work before the probe COMMIT.
- No external-exposure work beyond not-foreclosing (V-2); the OAuth front door is
  deferred to a future product decision.
- No composite-tool → workflow-registry generalization unless a 2nd ratified chain
  demands it.
- No re-litigating slate kills E1-E5 without new evidence.

## Slate kills E1-E5 (slate §E:296-321; shape §10:606-611 — do NOT re-litigate without new evidence)

- **E1** pre-emptive shared honesty mixin (killed 3/4 critics) — resequenced to D6.
- **E2** fleet budget-arbitration ADR/service (descoped) — survives only as B4's
  taxonomy checklist.
- **E3** fleet MCP gateway as #1 default (hard-rejected B1a) — honest costing at #2
  scoping, not silence.
- **E4** agent-delegation path (deferred immature) — migration target only after
  wiring + tests; B3's trigger governs.
- **E5** "ADR-125 mandates new MCP abstractions land in a8" (corrected) — ADR-125
  is host-substrate hygiene, not feature placement.

## Cross-references

- Charter: `.ledge/decisions/DECISION-fleet-mcp-program-alignment-2026-07-17.md`
  (§4 probe :73-78; §6 slate-effect table :100-108; §7 non-goals :110-115).
- Slate: `.ledge/spikes/SPIKE-mcp-substrate-concepts-2026-07-17.md`
  (§D ledger :257-294; §E kills :296-321).
- Shape defer_registry:
  `autom8y-asana/.sos/wip/frames/asana-mcp-v1.shape.md` §10:583-612.
