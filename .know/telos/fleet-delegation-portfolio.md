---
type: telos
initiative: fleet-delegation-portfolio
status: RATIFIED
ratified: >
  2026-07-22 — operator's word ("ratified!"). The mission and CONSUMPTION predicate stand
  as declared (operator-verbatim, never amendable). verification_deadline 2026-08-19
  (TELOS_OVERDUE review checkpoint) and rite_disjoint_attester (eunomia) carried UNAMENDED —
  the operator did not amend at ratification. The R20 moment-two ceremony date remains
  operator-minted when the spine lands (undecided by design). Same word ratifies PT-00: the
  /shape scope-fork (Option-B phased-meta) + the 7-sprint Phase-1 DAG + attester-disjointness.
  Precedent: postfelt telos ratified at R8 (2026-07-20).
created: 2026-07-22
author: myron (dispatched /frame 2026-07-22; the operator dispatch supplies the mission + verified-realized predicate verbatim — this file transcribes, it does not invent; pattern per .know/telos/asana-mcp-postfelt-hardening.md:6, operator-ratified at R8)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
sibling_telos: .know/telos/asana-mcp-v1.md (RATIFIED; WS-2 context-DONE substrate) + .know/telos/asana-mcp-postfelt-hardening.md (RATIFIED at R8)
governing_rulings: R1-R12 (RULINGS-operator-interview-telos-ratification-2026-07-20) + R13-R23 (RULINGS-operator-interview-fleet-halt-2026-07-22), both confirmed at origin/main
amendable: >
  verification_deadline (PROPOSED 2026-08-19 — a Naxos TELOS_OVERDUE review
  checkpoint, NOT the R20 moment-two ceremony date, which the operator
  deliberately left undecided and mints when the spine lands) and
  rite_disjoint_attester (carried from the predecessor telos's ratified
  eunomia binding). Operator may amend either at ratification; the mission +
  predicate are the operator's own words and are NOT amendable here.
---

# Telos — fleet-delegation-portfolio (PROPOSED)

Authored under the /frame dispatch of 2026-07-22 per the predecessor pattern.
The mission and the verified-realized predicate below are the OPERATOR'S OWN
declarations, carried verbatim from the dispatch.

## Declaration (telos-integrity-ref §2)

```yaml
telos:
  initiative_slug: fleet-delegation-portfolio
  inception_anchor:
    framed_at: "2026-07-22"
    frame_artifact: ".sos/wip/frames/fleet-delegation-portfolio.md:1"
    why_this_initiative_exists: >
      MISSION (operator's words, verbatim): every internal AI assistant our
      team invokes acts inside real business workflows carrying the invoking
      human's OWN delegated identity end-to-end — so a real person is provably
      accountable for every action a machine takes in the business, on
      infrastructure we own. Origin chain, all internal and live-read at frame
      time: the 17-glint value sweep
      (.sos/wip/glints/GLINT-asana-automation-value-expansion-2026-07-22.md),
      the transported-not-consumed research
      (.sos/wip/RESEARCH-identity-consumption-mapping-2026-07-22.md), the
      remote-access spike §11 verified delta
      (.sos/wip/SPIKE-asana-mcp-remote-access.md:228-294), the RB-1 design
      (.sos/wip/DESIGN-rb1-confirm-gate-2026-07-22.md), the operator's felt
      verdict (.sos/wip/asana-mcp-v1.felt-gate-envelope.md §5.2), and the two
      committed rulings records at origin/main (R1-R12 + R13-R23).
  shipped_definition:
    code_or_artifact_landed:
      # PLANNED at inception — the portfolio envelope defers per-stream landed
      # anchors to Pythia's /shape + sprint landings. Gate B refuses wave-level
      # tokens without real {path}:{line} anchors (F-HYG-CF-A).
      - "(context-DONE, pre-portfolio) WS-2 First Hand: asana-mcp-v1 SHIPPED 2026-07-20 — GATE-FELT closure record at .sos/wip/asana-mcp-v1.felt-gate-envelope.md §5.2"
      - "(planned) WS-3/WS-4 keystone: delegated-identity consumption through the MCP layer with audit naming the human — per-item anchors minted at sprint landings"
      - "(planned) remaining streams (WS-1 anchor, WS-5, WS-5b, WS-6 post-R22, WS-7 design): anchors minted at their landings per the /shape decomposition"
    user_visible_surface: >
      A rep invokes an assistant; the assistant acts on the Asana substrate
      (and successor integrations) through the MCP layer on the rep's OWN
      delegated authority; the audit line names the rep, not the service; the
      R5 confirm gate pauses automation-triggering writes for the rep's own
      yes; the whole registered-workflow surface is progressively disclosed
      behind that gate.
  verified_realized_definition:
    user_visible_evidence:
      # Operator's predicate, carried VERBATIM from the 2026-07-22 dispatch —
      # NOT "PRs merged", NOT "tools shipped".
      - >
        an agent bearing the operator's OWN delegated identity performs a real
        read AND a ratified write through the MCP layer, the satellite
        authorizes it on the human's authority with NO machine-credential
        bypass, AND the audit line names that human (not the service) —
        witnessed live, mechanism-attested rite-disjoint. This CONSUMPTION
        predicate (audit-names-the-human) is the realized bar per R13
        (identity ON the value bar) — transport is NOT enough.
    verification_method: in-anger-dogfood
    verification_deadline: "2026-08-19"   # PROPOSED — TELOS_OVERDUE review checkpoint only; per R20 the moment-two ceremony date is operator-minted when the spine lands ("the second one must actually happen or the asterisk becomes permanent"); this checkpoint fires if no ceremony date exists by then
    rite_disjoint_attester: >
      eunomia verification-auditor (rite-disjoint ADVISORY over receipts, R1
      binding) — carried from the predecessor telos's ratified-unamended
      binding. Constraint for /shape: eunomia must not be the executing rite
      of the attested stream. The live witness inside the predicate remains
      the operator's own; eunomia attests mechanism receipts, never a felt
      outcome.
  attestation_status:
    inception: INSCRIBED
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null
  receipt_grammar:
    per_item_file_line_anchors:
      - ".sos/wip/RESEARCH-identity-consumption-mapping-2026-07-22.md:16 (TL;DR — identity TRANSPORTED not CONSUMED; the gap the predicate closes)"
      - ".sos/wip/glints/GLINT-asana-automation-value-expansion-2026-07-22.md:46 (G-01 delegation keystone — exchange BUILT, one species gate from live)"
      - "src/autom8_asana/auth/jwt_validator.py:24 + :83 @origin/main 8e77c9a0 (the satellite species-gate seam; restriction resolves into shared autom8y_auth lib)"
      - ".sos/wip/asana-mcp-v1.felt-gate-envelope.md:503 (§5.2 GATE-FELT closure — WS-2 context-DONE receipt)"
      - "git show origin/main:.ledge/decisions/RULINGS-operator-interview-fleet-halt-2026-07-22.md (R13 identity-on-the-bar; R20 two-moment split; R22 transport hold; R23 external CLOSED)"
    cross_stream_concurrence: false
    code_verbatim_match: false
```

## Gate Posture

- **Gate A (inception)**: every required field above is non-stub — INSCRIBED.
  Deadline + attester are PROPOSED carries; operator may amend at ratification.
- **Gate A.1 (provenance-root)**: all cited origin artifacts are internal and
  were live-read (full or targeted-section) during the 2026-07-22 frame
  dispatch; resolution receipts ride the frame's §3 premise ledger. No external
  origin-signal is asserted; nothing requires a UV-P origin label. The one
  unresolvable internal label (the dispatch's "glint V-13") is UV-P-carried in
  the frame, not asserted.
- **Gate B (close)**: fires when `code_or_artifact_landed` carries real
  `{path}:{line}` anchors; "(planned)" rows MUST be replaced as items land —
  wave-level CLOSED tokens refused per F-HYG-CF-A.
- **Gate C (handoff)**: any cross-rite HANDOFF for this initiative carries this
  telos; unconsumed UV-P labels ride the DEFER-tag escape valve with a
  defer-watch-manifest entry.
