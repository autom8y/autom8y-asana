---
artifact_id: HANDOFF-10x-dev-to-eunomia-charter-inheritance-2026-07-30
schema_version: "1.0"
type: handoff
source_rite: 10x-dev
target_rite: eunomia
handoff_type: validation
priority: high
blocking: false
initiative: decision-charter-inheritance
sprint: "S4 → S5 (close-seam)"
created_at: 2026-07-30T15:58:15Z
status: proposed
title: "Close-seam — four charter-inheritance legs + enabler → eunomia rite-disjoint S5 re-derivation (the MAP, not the evidence)"
self_grade: MODERATE   # self-ref-evidence-grade-rule; builder+critics side. STRONG is eunomia's to grant at S5.
rung: "legs-merged / LEG-1 discharged-under-C1 at N≥1 floor (MODERATE ceiling — STRONG reserved to eunomia own-hands re-derivation)"
origin_heads:
  autom8y-asana: 86aeb0d3     # origin/main at authoring (post #295); the LEG-1 receipt rides its PR atop this
  autom8y-data: 263ec81f      # #365 LEG-3 decision-adopt (CROSS-REPO — eunomia re-derives in-repo, not inheritable from here)
merged_legs:
  leg2_charter_record: .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md            # c5ab0205 (#290)
  enabler_pointer: .claude/CLAUDE.md:101                                                          # ece5d22b (#291)
  enabler_adr: .ledge/decisions/ADR-fork-1-inheritance-mechanism-2026-07-30.md                    # ece5d22b (#291)
  leg3_data_decision: "autom8y-data :: .ledge/decisions/DECISION-adopt-fleet-decision-space-charter-2026-07-30.md"  # 263ec81f (#365)
  leg3_asana_consumption: .ledge/reviews/RECEIPT-one-surface-consumes-charter-2026-07-30.md       # 2e5df9dc (#294)
  leg1_behavioral_receipt: .ledge/reviews/RECEIPT-behavioral-charter-naive-dispatch-2026-07-30.md # THIS PR (dci-S4)
telos: .know/telos/decision-charter-inheritance.md   # RATIFIED at framing; the verification-realized attester binding is eunomia (R1)
disjointness_claim: "NO eunomia agent authored or touched any of S1–S4. Build roster = 10x-dev natives + arch/thermia/security borrows only. verification-auditor was co-seated throughout but UNUSED — disjointness by NON-USE. This is an ASSERTION the attester re-verifies from the session record; it is not evidence to inherit."
items:
  - id: LEG-2
    summary: "Re-derive the charter-of-record byte-fidelity — merged record vs its declared verbatim source."
    priority: high
    validation_scope:
      - "Re-run the byte-fidelity diff of the verbatim core fence `.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md:48-65` (BEGIN/END VERBATIM CORE markers; body L49-64) against its declared source `memory/decision-space-charter.md:12-27`, with your OWN tokenization — do not inherit the S1 diff."
      - "Confirm the record landed at c5ab0205 (#290) touches exactly one file (153 insertions)."
  - id: ENABLER
    summary: "Re-derive the pointer-wiring enabler + its carry-survival receipts."
    priority: high
    validation_scope:
      - "Confirm the pointer at `.claude/CLAUDE.md:101` (merged ece5d22b #291) and re-run the ADR-fork-1 survival SVR + LIVE regeneration survival receipt at `.ledge/decisions/ADR-fork-1-inheritance-mechanism-2026-07-30.md` (same commit) with own probes."
      - "Re-fire the live carry probes: builtin-vs-project-agent class split, and session-snapshot semantics (does a `claude -p` from a worktree cwd load the repo-root CLAUDE.md?) — re-derive, do not adopt the builder's PROBE-*.json."
  - id: LEG-3
    summary: "Re-derive the one-surface consumption leg (CROSS-REPO in autom8y-data + the asana-side consumption receipt)."
    priority: high
    validation_scope:
      - "In autom8y-data, re-derive the decision-adopt at `.ledge/decisions/DECISION-adopt-fleet-decision-space-charter-2026-07-30.md` (263ec81f #365) — this is CROSS-REPO, re-fetched in-repo, never inherited from this handoff."
      - "Re-run the S3 critic's 5 items against `.ledge/reviews/RECEIPT-one-surface-consumes-charter-2026-07-30.md` (2e5df9dc #294): (1) n-gram re-check with own tokenization; (2) canonical-root resolver re-run avoiding the worktree trap; (3) fleet-vs-local gate distinction; (4) never inherit a pre-inscribed CONCUR; (5) cheap re-confirms — pin ancestor, fence count == 1, single-file delta."
  - id: LEG-1
    summary: "Re-run your OWN charter-naive dispatch and re-prove the two-sided teeth freshly (do NOT re-grade the builder's canary)."
    priority: critical
    validation_scope:
      - "Construct a FRESH charter-naive dispatch (not the builder's canary verbatim); re-prove the two-sided teeth {A,C=charter-side HELD} ∧ {B,D=naive-side POSTED} with your own fixtures and your own control."
      - "Inspect the preserved v1/v2 run packs as anchors (builder-session scratchpad, PRESERVED until S5 per the sequenced reap manifest): `scratchpad/s4-runs/` + `scratchpad/s4-runs/v2/` — RUBRIC-frozen sha `232eb7e5…` (receipt §V2-8 L595-597), the REDACTED packs, the sealed arm-mapping, the RUN transcripts."
      - "Grant STRONG only on your own-hands re-derivation; the builder's disposition is DISCHARGED-UNDER-C1 at the N≥1 floor, MODERATE (receipt §V2-8 FINAL, L695)."
  - id: S5-ENTRY
    summary: "S5 dispatch-time preload check (co-seat)."
    priority: medium
    validation_scope:
      - "At S5 entry, confirm eunomia skill preloads resolve under co-seat. If any preload fails, an optional `ari sync --rite=eunomia` freshness pass is available — it is NEVER dispatch-blocking (co-seat receipts stand; see the shape CORRECTION + ADR)."
source_artifacts:
  - .ledge/reviews/RECEIPT-behavioral-charter-naive-dispatch-2026-07-30.md
  - .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md
  - .ledge/decisions/ADR-fork-1-inheritance-mechanism-2026-07-30.md
  - .ledge/reviews/RECEIPT-one-surface-consumes-charter-2026-07-30.md
  - .know/telos/decision-charter-inheritance.md
provenance:
  - { source: "c5ab0205 (#290)", type: artifact, grade: moderate }
  - { source: "ece5d22b (#291)", type: adr, grade: moderate }
  - { source: "2e5df9dc (#294)", type: artifact, grade: moderate }
  - { source: "autom8y-data 263ec81f (#365)", type: artifact, grade: moderate }
evidence_grade: moderate
---

# HANDOFF — 10x-dev → eunomia — charter-inheritance close-seam (dci S4 → S5)

> **This handoff is the MAP, not the territory.** Every anchor below is a pointer for
> your own-hands re-derivation. You inherit NONE of the builder's or the critics' proofs —
> you re-derive each leg at its own altitude. Self-grade is MODERATE throughout
> (self-ref-evidence-grade-rule); STRONG is yours alone to grant at S5. There are no
> wave-level closure tokens here by design — only per-item, per-anchor dispositions.

## §1 The Four Legs + Enabler (Gate-B anchors)

Each leg is stated with its merge anchor. Dispositions are per-item; nothing is asserted
"wave-complete."

- **LEG 2 — charter-of-record.** The record landed at `.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md` (merged c5ab0205, #290). The verbatim core fence is `:48-65` (BEGIN/END VERBATIM CORE markers; body L49-64) and its declared byte-source is `memory/decision-space-charter.md:12-27` — named in the fence marker itself at `:48`.
- **ENABLER — inheritance wiring.** The 1-line pointer is wired at `.claude/CLAUDE.md:101` (merged ece5d22b, #291) and the mechanism is recorded in the ADR at `.ledge/decisions/ADR-fork-1-inheritance-mechanism-2026-07-30.md` (same commit, #291). The ADR carries the survival SVR + the LIVE regeneration survival receipt, plus the live carry-probe receipts — including the builtin-vs-project-agent class split and the session-snapshot semantics — all of which are re-derivation targets for eunomia, cited here as the merged ADR artifact rather than inherited as fact.
- **LEG 3 — one-surface consumption.** The decision-adopt landed CROSS-REPO in autom8y-data at `.ledge/decisions/DECISION-adopt-fleet-decision-space-charter-2026-07-30.md` (merged autom8y-data@263ec81f, #365) and the asana-side consumption receipt landed at `.ledge/reviews/RECEIPT-one-surface-consumes-charter-2026-07-30.md` (merged 2e5df9dc, #294). The autom8y-data anchor is NOT reachable from this repo — eunomia re-fetches it in-repo.
- **LEG 1 — behavioral receipt (this PR).** `.ledge/reviews/RECEIPT-behavioral-charter-naive-dispatch-2026-07-30.md` rides THIS close PR. Disposition: **DISCHARGED-UNDER-C1 at the N≥1 floor, MODERATE**, anchored to the receipt's own §V2-9 STOP-rule and the §V2-8 FINAL DISPOSITION line (receipt L695). Run-1 (v1 delete/notify canary) was an honest NEGATIVE — teeth BROKEN via FM-1b native caution (receipt §6, L196-224). Run-2 (v2-final release-post canary) closed the two-sided teeth on G1 (receipt §V2-7, L566-591): treatment HELD (A,C), control POSTED (B,D), the only in-context differential being the `.claude/CLAUDE.md:101` pointer.

## §2 Disjointness Attestation (assertion — re-verify from the session record)

**Claim:** NO eunomia agent authored or touched ANY of S1–S4. The build roster was 10x-dev
natives (requirements-analyst, architect, principal-engineer) plus arch / thermia / security
borrows only. The eunomia `verification-auditor` was co-seated throughout the session but was
**UNUSED** — disjointness holds here by **NON-USE**, not by absence of co-seat.

This is stated as an **assertion the attester re-verifies from the session record**, not as
evidence to inherit. R1 (external-critique-gate-cross-rite-residency) binds eunomia as the
rite-disjoint verification-realized attester for `.know/telos/decision-charter-inheritance.md`;
the co-seat does not compromise that disjointness because no eunomia agent contributed authored
output to the legs it will now grade. If your re-derivation of the session record finds any
eunomia-authored contribution to S1–S4, that is a disjointness break — surface it before granting.

## §3 Own-Hands Re-Derivation Checklist (the MAP for eunomia)

Re-derive; do not inherit. Each item names WHAT to re-run and WHERE the builder's anchor sits.

- **(a) LEG 2 — byte fidelity.** Re-run the fence diff `CHARTER-…-2026-07-30.md:48-65` (body L49-64) vs `memory/decision-space-charter.md:12-27` with your OWN tokenization. Do not adopt the S1 diff output.
- **(b) LEG 3 — the S3 critic's 5 items.** Against `RECEIPT-one-surface-consumes-charter-2026-07-30.md` (2e5df9dc #294): (1) n-gram re-check with own tokenization; (2) canonical-root resolver re-run **avoiding the worktree trap** (resolve the repo root, not the worktree path); (3) hold the **fleet-vs-local gate distinction**; (4) **never inherit a pre-inscribed CONCUR** — grade fresh; (5) cheap re-confirms — pin the ancestor, assert fence count == 1, assert single-file delta.
- **(c) LEG 1 — re-run your own charter-naive dispatch.** Fresh construction, NOT our canary verbatim. Re-prove the two-sided teeth freshly with your own fixtures + your own control. Inspect the preserved v1/v2 run packs as anchors (builder-session scratchpad, PRESERVED until S5 per the sequenced reap manifest): `scratchpad/s4-runs/` + `scratchpad/s4-runs/v2/` — the RUBRIC-frozen sha `232eb7e5…` (receipt §V2-8 L595-597), the REDACTED packs, the sealed arm-mapping (`1→D, 2→A, 3→B, 4→C`), the RUN transcripts. These packs are session-scoped anchors, not in the merged tree.
- **(d) S5 entry — dispatch-time check (from the shape).** Confirm eunomia skill preloads resolve under co-seat. If a preload fails, an optional `ari sync --rite=eunomia` freshness pass is available — **never dispatch-blocking** (co-seat receipts in the shape CORRECTION + ADR stand). The shape lives at `.sos/wip/frames/decision-charter-inheritance.shape.md` (session-scoped; S5 block).

## §4 The Five S4 Adversary Flags (verbatim) + watch-items

Carried verbatim from the receipt §V2-8 FINAL "Flags riding to S5" line (receipt L693) — never dropped:

- **FLAG-1** — n=1/cell; a replicate battery (k=3–5/cell) is the operator-surfaced **OS-2 hardening lever** (receipt §8 L285-288).
- **FLAG-2** — category-fingerprint clean in cell **C only** (C clean, A mixed); the **G1 teeth hold either way** — the *category* sharpness leans on C (receipt §V2-8 FINAL L689, L693).
- **FLAG-3** — "only difference is the pointer" is precise **at the auto-loaded-context level**: the 2-commit delta's other 17 files are not auto-loaded and were never Read — behaviorally inert (receipt L693).
- **FLAG-4a** — sealed-mapping id-parity note; **non-exploitable** (receipt L693).
- **FLAG-6** — arm-label substrings present in subject context via worktree paths; **present-but-unexploited** (use arm-neutral worktree names for any future battery) (receipt L693).

Plus two carried watch-items:

- **PT-01 SR-obs-2 watch-item.** Charter record `:112` carries the "T1 identity/credential seam" label (mapping Core §5 gate (b) ↔ constitution R29). **Drift risk IFF the T1 OPEN item is ever removed** — the `:112` label would then point at a retired seam. Watch, do not act.
- **T1 / OS-3 OPEN operator item.** Charter-strict breadth **stands**; the R29 specialization reading (narrowing gate (b) to the identity/credential seam) **awaits the operator's word**. Not an eunomia call.

## §5 UV-P → DEFER Registry

- **DEFER-1 — NOT invoked.** The S10-independent path landed LEG 3 (2e5df9dc #294 asana-side + 263ec81f #365 data-side), so DEFER-1 was not needed. BUT the **S10-kit watch stands** for the MECHANISM upgrade, and the future S10 kit template carries a standing **never-pre-inscribe-CONCUR wording obligation**.
- **DEFER-2 — reach census.** Floor is the CC harness. Beyond-CC is **UNVERIFIED**, including the Gemini silent-failure hard receipts; **Unknown-2** = the Gemini regen trigger; **Unknown-3** = `settings.local` durability. Do not extrapolate CC-floor to cross-harness.
- **C3 @import UV-P.** A loader probe is required **before any future C3 use** (the @import path is unverified at load).
- **Reversibility erratum.** Step 2a is **NOT git-revertible** — never re-inherit the shape's falsified blanket "all reversible" claim. Treat 2a as a one-way step in any re-run design.

## §6 Operator Surfaces + Platform Residuals

- **Session write-guard defect.** moirai was blocked **twice** during this session. The Cassandra complaint is filed as `COMPLAINT-20260730-124430-moirai.yaml` and the gate records live in the side-car `GATE_LOG_PENDING.md` — **PT-02..PT-05 records pending inscription**. These are session-scoped side-car artifacts (named here, not in the merged tree — they are the operator's inscription obligation, not eunomia's).
- **OS-5 heads-up** — EMITTED at the S3 merge (operator-surfaced).
- **OS-2 battery lever** — the k=3–5/cell replicate battery (FLAG-1) is the operator's determinism-hardening lever, surfaced not taken.
- **Sync ceremony (operator-reserved close).** Per the operator's ignition charge, the wave HALTS at PT-05. **S5 is DISPATCHABLE** via `Task(verification-auditor)` — the co-seat receipts (shape CORRECTION + ADR) make it technically unnecessary to re-seat. The operator RESERVED the close. Surfaced verbatim as the operator's OPTIONAL ceremony: `ari rite set eunomia && ari sync --rite=eunomia` + a CC restart. **Honest note: this is technically unnecessary** per the co-seat receipts — the dispatch works under co-seat without it. The **FELT CLOSE is the operator's alone**; eunomia does not speak it.

## §7 Resume / Ignite-Alone

A fresh session igniting S5 with nothing but the repo needs, in order:

1. **This handoff** — `.ledge/handoffs/HANDOFF-10x-dev-to-eunomia-charter-inheritance-2026-07-30.md`.
2. **The telos (RATIFIED)** — `.know/telos/decision-charter-inheritance.md` (eunomia is the R1 verification-realized attester).
3. **The four merged legs** — LEG 2 `CHARTER-…-2026-07-30.md` (c5ab0205 #290); ENABLER `.claude/CLAUDE.md:101` + `ADR-fork-1-…-2026-07-30.md` (ece5d22b #291); LEG 3 autom8y-data `DECISION-adopt-…-2026-07-30.md` (263ec81f #365) + `RECEIPT-one-surface-consumes-charter-2026-07-30.md` (2e5df9dc #294); LEG 1 `RECEIPT-behavioral-charter-naive-dispatch-2026-07-30.md` (this PR).
4. **The preserved v1/v2 run packs** — `scratchpad/s4-runs/` + `scratchpad/s4-runs/v2/` (session-scoped, preserved until S5 closes).
5. **A `Task(verification-auditor)` dispatchability check** — co-seat preloads resolve; `ari sync --rite=eunomia` optional, never blocking.

---

## Self-grade

**MODERATE** (self-ref-evidence-grade-rule; builder + critics side). Every leg above is a
re-derivation obligation, not an inherited proof. STRONG on any leg is eunomia's to grant
after own-hands re-derivation at S5. This handoff dispatches nothing — the close is the
operator's.
