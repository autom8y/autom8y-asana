---
type: telos
initiative: asana-mcp-postfelt-hardening
status: PROPOSED
created: 2026-07-19
author: myron (dispatched /frame 2026-07-19; the operator dispatch supplies the mission + verified-realized predicate verbatim — this file transcribes, it does not invent)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
parent_telos: .know/telos/asana-mcp-v1.md   # RATIFIED 2026-07-17; this initiative hardens its realized surface
activation_gate: >
  NAMED-ONLY until the operator closes the asana-mcp-v1 felt gate (limb (b) + felt
  verdict PENDING, operator-only per charter §3:63-71). Nothing in this telos
  authorizes pre-verdict execution.
  GATE FIRED 2026-07-20: the operator closed GATE-FELT (envelope §5.2,
  .sos/wip/asana-mcp-v1.felt-gate-envelope.md:503-526) and executed/delegated the
  ACT-2 merges (#239 23440991 / #240 edaa9ddd / #238 a0b7142d / #241 793e670b) —
  the wave is ACTIVE under the PT-01 standing grant. Telos ratification (A3)
  remains a pending operator act; status stays PROPOSED until then.
amendable: >
  verification_deadline (PROPOSED 2026-08-14 — carried from the parent telos's
  ratified-unamended value) and rite_disjoint_attester (carried from the parent's
  ratified-unamended eunomia binding). Operator may amend either at ratification;
  the mission + predicate are the operator's own words and are NOT amendable here.
---

# Telos — asana-mcp-postfelt-hardening (PROPOSED)

Authored under the /frame dispatch of 2026-07-19 per the predecessor pattern
(.know/telos/asana-mcp-v1.md:6 — myron-authored PROPOSED, operator-ratified). The
mission and the three-limb verified-realized predicate below are the OPERATOR'S OWN
declarations, carried verbatim from the dispatch.

## Declaration (telos-integrity-ref §2)

```yaml
telos:
  initiative_slug: asana-mcp-postfelt-hardening
  inception_anchor:
    framed_at: "2026-07-19"
    frame_artifact: ".sos/wip/frames/asana-mcp-postfelt-hardening.md:1"
    why_this_initiative_exists: >
      An agent or teammate reaching the asana MCP surface finds it reliably
      available THROUGH deploys and addressable in human terms — no cold-window
      lockouts, tags by name — with the v1 witness's receipts consolidated into
      the repo's knowledge and governance planes. Origin chain, all internal and
      live-read at frame time: limb-(a) witness evidence digest §9 ALB-1 +
      §10 TAG-1/TAG-2 (.sos/wip/asana-mcp-v1.limb-a-witness-evidence-digest.md),
      adversary DELTA (.ledge/reviews/ADVERSARY-REPORT-asana-mcp-cure-wave-DELTA-2026-07-19.md),
      mint-halt incident (.ledge/reviews/INCIDENT-asana-mcp-witness-mint-halt-2026-07-18.md),
      felt-gate envelope §3.3, and the REBASE horizon ledger
      (.sos/wip/REBASE-asana-mcp-lane-2026-07-18.md §d POST-FELT).
  shipped_definition:
    code_or_artifact_landed:
      # PLANNED at inception — replace with real {path}:{line} anchors as items
      # land. Gate B refuses wave-level tokens without them (F-HYG-CF-A).
      # Row states updated 2026-07-20 by the WS-D s5 single writer; only WS-D
      # flips — its anchors ride the same WS-D PR as this file and are true at
      # its merge. All other rows remain honestly un-landed.
      - "(planned) WS-A fleet IaC: TG health-check -> /ready + ECS grace sized >= measured full-preload duration (autom8y repo terraform; cross-repo — receipts will live in the autom8y repo; no s2 PR observed at 2026-07-20 authoring)"
      - "(planned) WS-B satellite GET /tags surface + sidecar tag-by-NAME addressing (shape a/b/c per digest §10)"
      - "(planned) WS-C: #242 rebased onto the operator-merged stack + format pass + un-draft (#242 still OPEN draft at 2026-07-20 authoring; s1 owns)"
      - "WS-D LANDED (via the WS-D PR, branch docs/asana-mcp-postfelt-wsd): .know refresh — .know/architecture.md:165 (§MCP Sidecar Surfaces), .know/scar-tissue.md:342,399,438 (SCAR-VOCAB-PARITY-001 / SCAR-AUTHSIG-001 / SCAR-TG-LIVENESS-001 + two N=1 candidates), .know/design-constraints.md:226-245 (MCP-BUDGET-PARTITION/WRITE-FLAG/B1O1-COUPLING/REFERENCE-POSTURE-001), .know/test-coverage.md:397 (§MCP Island Test Topology); fork-(a) receipt FILED on the dossier record .ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md:856 (ADDENDUM-1; C1 ruling STAGED operator-only at :915 §A1.4 — limb (c) completes at the operator's mark); TAG-2 + PLAY-3 defer-watch REGISTERED .know/defer-watch.yaml:469,:521"
      - "(planned) WS-E: sandbox/tag/helper/worktree lane residues cleared by 2026-07-24"
    user_visible_surface: >
      Deploys become client-invisible: a mid-deploy client session sees zero
      warming errors instead of a cold-window lockout. The composite write is
      addressable by tag NAME, not gid. The repo's .know/ and governance planes
      carry the witness arc's scars, receipts, and the reconciled C1 annotation.
  verified_realized_definition:
    user_visible_evidence:
      # Operator's predicate, carried VERBATIM from the 2026-07-19 dispatch — NOT "PRs merged".
      - >
        (a) a deploy completes while a client session queries continuously and
        observes ZERO warming errors (TG health-check receipt on /ready + one
        mid-deploy green session)
      - >
        (b) one composite invocation addressed by tag NAME succeeds e2e
      - >
        (c) C1 annotation reconciliation + fork-(a) receipt filed on the dossier
        record — NOT "PRs merged"
    verification_method: in-anger-dogfood
    verification_deadline: "2026-08-14"   # PROPOSED — matches the parent telos's ratified deadline; operator may amend; drives Naxos TELOS_OVERDUE
    rite_disjoint_attester: >
      eunomia verification-auditor (rite-disjoint ADVISORY over receipts, R1
      binding) — carried from the parent telos's ratified-unamended binding.
      Felt/witness observations inside the predicate remain the operator's own;
      eunomia attests receipt integrity, never a felt outcome.
  attestation_status:
    inception: INSCRIBED
    shipped: UNATTESTED   # PARTIAL 2026-07-20 — the WS-D row carries real anchors (rides the WS-D PR); WS-A/B/C/E rows remain (planned). Full LANDED requires all rows real; no wave-level token (F-HYG-CF-A).
    verified_realized: UNATTESTED   # predicate limbs (a)/(b) not yet receipted; limb (c) receipt FILED, operator ruling STAGED (dossier ADDENDUM-1 §A1.4)
    last_eunomia_advisory: null   # eunomia attests at PT-09, receipts only
  receipt_grammar:
    per_item_file_line_anchors:
      - ".sos/wip/asana-mcp-v1.limb-a-witness-evidence-digest.md:200-211 (ALB-1 root cause + disposition — WS-A source)"
      - ".sos/wip/asana-mcp-v1.limb-a-witness-evidence-digest.md:219-234 (TAG-1/TAG-2 — WS-B source + TAG-2 exclusion)"
      - ".sos/wip/asana-mcp-v1.felt-gate-envelope.md:352-380 (§3.3 C2 no-re-fire record; fork-(a) receipt exists — WS-D C1 source)"
      - ".sos/wip/REBASE-asana-mcp-lane-2026-07-18.md:373-411 (POST-FELT horizon ledger this initiative discharges)"
      - ".sos/wip/frames/asana-mcp-postfelt-hardening.md §3 (SVR ledger: live TG probe / #242 state / tasks.py:254 — all resolved 2026-07-19, zero drift)"
    cross_stream_concurrence: false
    code_verbatim_match: false
```

## Gate Posture

- **Gate A (inception)**: every required field above is non-stub — INSCRIBED. The
  deadline and attester are PROPOSED carries of the parent's ratified values;
  operator may amend at ratification.
- **Gate A.1 (provenance-root)**: all cited origin artifacts are internal and were
  live-read in full or targeted-section during the 2026-07-19 frame dispatch;
  resolution receipts ride the frame's §3 SVR ledger. No external origin-signal is
  asserted; nothing requires a UV-P origin label.
- **Gate B (close)**: fires when `code_or_artifact_landed` carries real
  `{path}:{line}` anchors; "(planned)" rows are inception placeholders that MUST be
  replaced as items land — wave-level CLOSED tokens refused per F-HYG-CF-A.
  Row-flip discipline in effect 2026-07-20: WS-D flipped with per-item anchors
  (single writer: WS-D s5 docs/tech-writer — the wave's SOLE telos writer);
  WS-A/WS-B/WS-C/WS-E remain (planned) until their own receipts exist. Self-record
  caps MODERATE (self-ref-evidence-grade-rule); eunomia PT-09 is the external leg.
- **Gate C (handoff)**: any cross-rite HANDOFF for this initiative carries this
  telos; unconsumed UV-P labels ride the DEFER-tag escape valve with a
  defer-watch-manifest entry.
