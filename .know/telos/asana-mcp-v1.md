---
type: telos
initiative: asana-mcp-v1
status: RATIFIED
created: 2026-07-17
author: myron (dispatched /frame; autonomy grant charter §5.2)
session_repo: /Users/tomtenuta/Code/a8/a8/repos
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
ratification: >
  RATIFIED 2026-07-17 by operator (Tom Tenuta) — explicit instruction ("mark it
  ratified on my behalf") recorded by session a8-mcp-substrate on the operator's
  behalf. Amendable values NOT amended: verification_deadline 2026-08-14 and the
  eunomia rite-disjoint attester stand as authored. Scope: this telos declaration
  only — GATE-BW (B1-B5 + W-5 rulings), GATE-FELT, and GATE-PROBE remain open and
  reserved per charter §5.
upstream_mandate: "autom8y-asana/.sos/wip/SPIKE-asana-mcp-exposure.md:216-217 + .ledge/decisions/DECISION-fleet-mcp-program-alignment-2026-07-17.md:87-89"
---

# Telos — asana-mcp-v1 (RATIFIED)

Authored PROPOSED under the charter §5.2 autonomy grant ("author the MCP v1 frame and
telos declaration as PROPOSED artifacts", DECISION-fleet-mcp-program-alignment-2026-07-17.md:87-89)
discharging the upstream-spike mandate ("`/frame` a build initiative **with a telos
declaration**", SPIKE-asana-mcp-exposure.md:216-217). **RATIFIED 2026-07-17 by explicit
operator instruction**, recorded on the operator's behalf (see frontmatter `ratification`);
the amendable values (deadline, attester) were offered and not amended — they now stand.

## Declaration (telos-integrity-ref §2)

```yaml
telos:
  initiative_slug: asana-mcp-v1
  inception_anchor:
    framed_at: "2026-07-17"
    frame_artifact: "autom8y-asana/.sos/wip/frames/asana-mcp-v1.md:1"
    why_this_initiative_exists: >
      Internal a8 agents ground on and act in asana business context through a
      fleet-conformant MCP surface — reads broad, writes narrow. Origin chain, all
      live-resolved at frame time: upstream GO spike
      (autom8y-asana/.sos/wip/SPIKE-asana-mcp-exposure.md:173-174) -> adjudicated
      substrate slate (.ledge/spikes/SPIKE-mcp-substrate-concepts-2026-07-17.md) ->
      operator-ratified charter (.ledge/decisions/DECISION-fleet-mcp-program-alignment-2026-07-17.md).
  shipped_definition:
    code_or_artifact_landed:
      # Landed rows flipped from "(planned)" 2026-07-20 (WS-D s5 single writer) —
      # every anchor re-verified by direct read at origin/main 793e670b.
      - "FastMCP sidecar read tools 1-5 + match_business stub: mcp/asana_mcp/server.py:33 (create_server) + mcp/asana_mcp/tools/ (#239 squash 23440991); MCP-1 error passthrough mcp/asana_mcp/errors.py:110"
      - "The single W-2 composite write tool, exposure-gated OFF: src/asana_mcp/tools/composite_write.py:277 (register self-gates; flag const :82) (#238 squash a0b7142d)"
      - "Observability + guardrails floor: src/asana_mcp/observability.py:726 (instrument) + :259 (validate_partition fail-loud invariants) (#240 squash edaa9ddd); CI floor suite tests/asana_mcp/ (9 files)"
      - "Rulings dossier B1-B5 + W-5 (RATIFIED at GATE-BW 2026-07-17): .ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md:749-766 (ratification block) (#241 squash 793e670b)"
      - "Granted hygiene motions: D1-D11 ledger .ledge/decisions/DECISION-mcp-doctrine-debt-ledger-D1-D11-2026-07-17.md:1 + governed x-fleet query markers src/autom8_asana/api/main.py:757-766 (#237 squash 75b3b3ed)"
      - "Write-path groundwork: fail-loud idempotency contract spec .ledge/specs/SPEC-fail-loud-idempotency-contract-b5.md:1; OpenFGA amendment stays DRAFT at autom8y#1074 (OPEN, landing operator-reserved by design)"
      - "SAT-1 cure (post-n=0 HYBRID, operator-authorized): registry-driven vocabulary src/autom8_asana/services/resolver.py:290 + parity contract test tests/unit/services/test_entity_vocabulary_parity.py:73,113 (#245 squash 2eb830ca)"
    user_visible_surface: >
      An MCP endpoint internal a8 agents connect to over S2S JWT exposing six read
      tools (list_entity_types, describe_entity, query_rows, query_aggregate,
      resolve_entity, match_business) plus one ratified composite write tool
      (add_tag -> push -> mark_complete), with honesty attestations
      (stale_served / honest_empty / contract_complete) visible in tool output.
      The operator sees an agent answer real business questions and act on a real
      task inside the operator's own workflow.
  verified_realized_definition:
    user_visible_evidence:
      # Charter §3 ratified felt-gate predicate — carried VERBATIM. NOT "PRs merged".
      - >
        an agent, unassisted from schemas alone, (a) answers a real business
        question via list→describe→rows→aggregate AND (b) executes the composite
        chain add_tag → push(PUT-save) → mark_complete correctly against a real
        task, witnessed by the operator in their own workflow — NOT "PRs merged"
      - >
        technical floor (necessary but NOT sufficient, charter §3:69-70): spike POC
        criteria (a)-(d) (SPIKE-asana-mcp-exposure.md:210-215) + slate additions —
        traceparent visible across the sidecar->REST hop, budget-partition env vars
        honored, import-safety test green
  verification_method: in-anger-dogfood
  verification_deadline: "2026-08-14"   # PROPOSED — operator may amend at ratification; drives Naxos TELOS_OVERDUE. The felt verdict also starts the §4 probe clock (charter :71).
  rite_disjoint_attester: >
      eunomia verification-auditor (rite-disjoint ADVISORY over receipts, R1
      binding). The felt VERDICT itself is reserved to the operator as sole closer
      (charter §3:63-65) — no session, agent, or attester may speak it; eunomia
      attests receipt integrity, never the felt outcome.
  attestation_status:
    inception: INSCRIBED
    shipped: LANDED   # 2026-07-20 — per-item {path}:{line} anchors above, re-verified at 793e670b
    verified_realized: >
      REALIZED — GATE-FELT CLOSED by the operator 2026-07-20. The felt verdict
      (the operator's words, verbatim, A2 dictation scribed at the operator's
      direction) lives at .sos/wip/asana-mcp-v1.felt-gate-envelope.md:503-526
      (§5.2) and is CITED here, not restated. Effect (mechanical, per envelope
      §5.2): v1 SHIPPED 2026-07-20; the §4 probe clock started (probe entry
      repos/.ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md,
      probe_due 2026-08-03, ruling operator-only). Witness receipts: limb (a)
      n=1 clean run (digest §7, envelope §1.4); limb (b) real-task composite +
      refusal + re-run (envelope §2.3); C2 no-re-fire (envelope §3.3).
      Eunomia receipt-integrity ADVISORY: PENDING (PT-09 of the post-felt
      wave) — eunomia attests receipts only, never the felt outcome.
    last_eunomia_advisory: null   # PT-09 pending; will carry the VERDICT path when issued
  receipt_grammar:
    per_item_file_line_anchors:
      - ".ledge/decisions/DECISION-fleet-mcp-program-alignment-2026-07-17.md:65-71 (felt-gate predicate source)"
      - "autom8y-asana/.sos/wip/SPIKE-asana-mcp-exposure.md:107-121 (tools 1-6 table)"
      - "autom8y-asana/.sos/wip/frames/asana-mcp-v1.md §7 (SVR ledger carrying all live-code receipts)"
      - ".sos/wip/asana-mcp-v1.felt-gate-envelope.md:503-526 (§5.2 closure record — the verified_realized pointer)"
      - ".ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md ADDENDUM-1 (C1 fork-(a) receipt filed 2026-07-20)"
    cross_stream_concurrence: false   # honest: eunomia PT-09 attestation pending; single-writer self-record caps MODERATE
    code_verbatim_match: true   # landed-row anchors re-verified by direct read at 793e670b this pass
```

## Gate Posture

- **Gate A (inception)**: every required field above is non-stub — INSCRIBED. The
  deadline and attester, PROPOSED at authoring, stand unamended as of the
  2026-07-17 operator ratification (frontmatter `ratification`).
- **Gate A.1 (provenance-root)**: all three cited origin artifacts resolved by live
  read at frame time (2026-07-17; sizes 7.5k / 27k / 15k). Resolution receipt:
  frame §7 SVR-9.
- **Gate B (close)**: SATISFIED 2026-07-20 — every "(planned)" row replaced with a
  real `{path}:{line}` anchor (re-verified by direct read at origin/main
  `793e670b`); no wave-level CLOSED token used (F-HYG-CF-A honored). Single
  writer: WS-D s5 (docs/tech-writer, asana-mcp-postfelt-hardening); self-record
  caps MODERATE per self-ref-evidence-grade-rule — the rite-disjoint eunomia
  receipt-integrity ADVISORY (PT-09) is the pending external leg.
- **Gate C (handoff)**: any cross-rite HANDOFF for this initiative carries this
  telos; unconsumed UV-P labels (frame §7) ride the DEFER-tag escape valve with a
  defer-watch-manifest entry.

## Closure Record (2026-07-20 — pointers only; the verdict is the operator's)

- GATE-BW: PASS 2026-07-17 (dossier `:749-766` ratification block).
- GATE-FELT: **CLOSED 2026-07-20 by the operator** — verdict verbatim at
  `.sos/wip/asana-mcp-v1.felt-gate-envelope.md:503-526` (§5.2). v1 SHIPPED.
- GATE-PROBE: SCHEDULED — entry
  `repos/.ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md`, probe_due
  **2026-08-03**, ruling (COMMIT / PARK / KILL) operator-only.
- Open governance residue (routed, not lost): the `tasks.py:254` idempotency
  annotation reconciliation ruling is STAGED for the operator at dossier
  ADDENDUM-1 §A1.4 — predicate limb (c) of the successor initiative
  `asana-mcp-postfelt-hardening` (`.know/telos/asana-mcp-postfelt-hardening.md`).
