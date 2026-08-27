---
type: telos
initiative: decision-charter-inheritance
status: RATIFIED
created: 2026-07-30
ratified: 2026-07-30 — operator /sprint ignition charge, ruling OS-1; both amendable carries (verification_deadline 2026-08-27 + eunomia verification-auditor attester) ratified UNAMENDED
author: myron (dispatched /frame 2026-07-30; the operator dispatch supplies the mission + verified-realized predicate verbatim — this file transcribes, it does not invent; pattern per .know/telos/fleet-delegation-portfolio.md:14, operator-ratified 2026-07-22)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
charter_of_reference: /Users/tomtenuta/.claude/projects/-Users-tomtenuta-Code-a8-a8-repos-autom8y-asana/memory/decision-space-charter.md (operator-ratified 2026-07-29; NON-AMENDABLE in this initiative)
governing_rulings: R24-R34 (.ledge/decisions/RULINGS-operator-interview-fleet-constitution-2026-07-24.md, merged dfdb84a3 #270) + substrate-v2 P1-P12 (.ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md)
amendable: >
  verification_deadline (PROPOSED 2026-08-27 — a Naxos TELOS_OVERDUE review
  checkpoint, ~4 weeks per the fleet-delegation-portfolio precedent) and
  rite_disjoint_attester (carried from the predecessor telos's
  ratified-unamended eunomia binding, .know/telos/fleet-delegation-portfolio.md:86-92).
  Operator may amend either at ratification; the mission + predicate are the
  operator's own words and are NOT amendable here.
---

# Telos — decision-charter-inheritance (RATIFIED)

Authored under the /frame dispatch of 2026-07-30 per the predecessor pattern.
The mission and the verified-realized predicate below are the OPERATOR'S OWN
declarations, carried verbatim from the dispatch.

## Declaration (telos-integrity-ref §2)

```yaml
telos:
  initiative_slug: decision-charter-inheritance
  inception_anchor:
    framed_at: "2026-07-30"
    frame_artifact: ".sos/wip/frames/decision-charter-inheritance.md:1"
    why_this_initiative_exists: >
      MISSION (operator's words, verbatim): Every downstream workflow — future
      sessions, agent dispatches, and eventually fleet repos — automatically
      inherits the ratified decision-space charter as standing law, so
      autonomous work runs hands-off within its two gates without per-fork
      check-ins or re-litigation. Origin chain, all internal and live-read at
      frame time: the ratified charter itself (memory/decision-space-charter.md:10
      "Operator-ratified 2026-07-29 (explicit 'Ratified!' on a full read-back,
      incl. the two inferred points as stated)" + :22 RATIFIED INFERENCES +
      :29 lineage block declaring "NOT yet landed as a shared repo artifact —
      this is private session memory"), the fleet constitution R24-R34
      (RULINGS-operator-interview-fleet-constitution-2026-07-24.md:92 R26
      standing grant), the substrate epoch P8/P9
      (CHARTER-substrate-v2-epoch-2026-07-27.md:86-96), and the UV-P-4
      constitution-path resolution
      (HANDOFF-wave2-to-s8-cutover-gate-2026-07-29.md:168-170).
  shipped_definition:
    code_or_artifact_landed:
      # PLANNED at inception — the envelope defers per-workstream landed
      # anchors to Pythia's /shape + landings. Gate B refuses wave-level
      # tokens without real {path}:{line} anchors (F-HYG-CF-A).
      - "(planned) WS-A charter-of-record: ratified charter text landed verbatim at constitution level in autom8y-asana/.ledge/decisions/ on files DISJOINT from the S9 doctrine draft — anchor minted at landing"
      - "(planned) WS-B inheritance-wiring: the mechanism (fork: inscription vs memory vs dispatch-template — named, unresolved) by which sessions/dispatches auto-carry the charter — anchors minted at landing"
      - "(planned) WS-C fleet-propagation-seam: at-least-one surface beyond this repo consuming the record via the S10 kit seam — anchor minted at landing"
      - "(planned) WS-D behavioral-verification: the receipt machinery observing a real charter-naive dispatch honoring the gates — anchor minted at landing"
    user_visible_surface: >
      A fresh session or agent dispatch — with no charter text pasted into its
      prompt — runs hands-off under the charter's two gates, escalating only
      at (a) irreversibility and (b) the sensitive list; forks stop being
      re-litigated per-session; fleet repos eventually receive the same
      standing law through the kit seam.
  verified_realized_definition:
    user_visible_evidence:
      # Operator's predicate, carried VERBATIM from the 2026-07-30 dispatch —
      # a BEHAVIORAL receipt, never a file-exists check.
      - >
        A fresh session/dispatch containing NO charter text in its prompt
        demonstrably operates under the charter — honors the two gates,
        escalates per the sensitive list — because inheritance carried it (a
        BEHAVIORAL receipt, observed on a real dispatch, not a file-exists
        check); AND the charter-of-record is landed at constitution level;
        AND at least one surface beyond this repo consumes it. This is
        governance work, but the receipt's reality-check leg is the observed
        behavior of a real dispatch (charter §4 posture).
    verification_method: in-anger-dogfood
    verification_deadline: "2026-08-27"   # RATIFIED 2026-07-30 (OS-1) — a Naxos TELOS_OVERDUE review checkpoint
    rite_disjoint_attester: >
      eunomia verification-auditor (rite-disjoint ADVISORY over receipts, R1
      binding) — carried from the fleet-delegation-portfolio telos's
      ratified-unamended binding. Constraint for /shape: eunomia must not be
      the executing rite of the attested workstream. The behavioral
      observation rides a REAL dispatch; eunomia attests mechanism receipts,
      never a felt outcome.
  attestation_status:
    inception: INSCRIBED
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null
  receipt_grammar:
    per_item_file_line_anchors:
      - "memory/decision-space-charter.md:10 (operator ratification line — the provenance root) + :22 (RATIFIED INFERENCES) + :29 (lineage: private-memory-only + landing offer)"
      - ".ledge/decisions/RULINGS-operator-interview-fleet-constitution-2026-07-24.md:92-105 (R26 full-auto-below-identity) + :150-166 (R29 identity gate) + :168-178 (R30 tripwire); merged dfdb84a3 (#270)"
      - ".ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md:86-96 (P8/P9 — 'Extends the fleet constitution's full-auto-below-identity posture')"
      - ".ledge/handoffs/HANDOFF-wave2-to-s8-cutover-gate-2026-07-29.md:168-170 (UV-P-4 resolved-model: in-repo .ledge/decisions of record + S10 kit propagation)"
      - "gh pr view 279 → state OPEN, isDraft true, title 'docs(ledge): substrate constitution RC-A..F + memory/teeth plan [S9] — LANDING-HELD-TO-S8-GREEN' (probe 2026-07-30)"
    cross_stream_concurrence: false
    code_verbatim_match: false
```

## Gate Posture

- **Gate A (inception)**: every required field above is non-stub — INSCRIBED.
  Deadline + attester were PROPOSED carries; RATIFIED UNAMENDED 2026-07-30 by
  the operator's /sprint ignition charge (ruling OS-1).
- **Gate A.1 (provenance-root)**: the founding claim is the operator's
  in-channel ratification ("Ratified!", 2026-07-29, on a full read-back
  including two named inferences), resolved to the memory file's own text at
  decision-space-charter.md:10 + :22 — live-read during this frame dispatch.
  All origin artifacts are internal and were live-read; no external
  origin-signal is asserted; nothing requires a UV-P origin label.
- **Gate B (close)**: fires when `code_or_artifact_landed` carries real
  `{path}:{line}` anchors; "(planned)" rows MUST be replaced as items land —
  wave-level CLOSED tokens refused per F-HYG-CF-A.
- **Gate C (handoff)**: any cross-rite HANDOFF for this initiative carries
  this telos; unconsumed UV-P labels ride the DEFER-tag escape valve with a
  defer-watch-manifest entry.
