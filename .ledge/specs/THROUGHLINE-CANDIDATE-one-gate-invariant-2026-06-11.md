---
type: spec
status: draft
name: one-gate-invariant
throughline_status: CANDIDATE
origin: "2026-06-05→06-11 cure-recovery saga (autom8y-asana #127→#128): 3 defect rounds converged onto ONE gated write primitive (write_final_artifacts_async honoring WriteDecision + backstop-REFUSE at section_persistence.py:905) and ONE gated serve accessor (_memory_get_serviceable, sole memory_tier.get at dataframe_cache.py:391). Game-day proved PRESERVE correctly computed AND logged while NOT enforced at the operative write site — the cure was topological convergence, not another patch."
custodian_of_record: "eunomia governance rite (autom8y-asana residency at mint); registered at station E3, procession 'Pre-Clear External Corroboration & Governance Custody'"
custodian_primary: [eunomia]
custodian_meta: Pythia
evidence_grade: "[MODERATE, self-ref-capped]"
evidence_annotation: "N_applied=1 (one incident arc: #127→#128 convergence, autom8y-asana). E1's 2 mutation-REDs (write-side + serve-side, EUNOMIA-INTERIM-CORROBORATION-keystone-day1-2026-06-11.md Item 2) are rite-disjoint corroborating receipts WITHIN the same incident — they harden the N=1 anchor, they do NOT increment N. ALL evidence is same-satellite; per the O-2 custodian precedent on integration-boundary-fidelity ('Gate requires a SECOND satellite repo / DISTINCT satellite'), same-satellite evidence is NON-promoting."
n_applied: "1 (single incident; E1 mutation-RED corroboration rite-disjoint but same-incident, non-incrementing)"
n_prevented_incidents: 0
siblings: [integration-boundary-fidelity, premise-integrity, structural-verification-receipt]
user-invocable: false
---

# Throughline (candidate): one-gate-invariant

> Registered 2026-06-11 by eunomia entropy-assessor (E3) per the
> @throughlines:index Extension Protocol shape mirrored from
> `THROUGHLINE-integration-boundary-fidelity-2026-06-10.md`. CANDIDATE at N=1;
> does NOT add an INDEX row (gate quoted in §4).

## §1 Statement

**A contract face is honest iff every path of its class passes through a single
enforced primitive, proven by a content-RED at each altitude.**

Corollary: a decision that is computed and logged but not enforced at the
operative site is not a gate — it is narration. Honesty is established only
when removing the primitive turns a content assertion RED at every altitude
that serves or persists the contract face (write altitude AND serve altitude,
independently).

## §2 Custodian ruling: NEW candidate, not a §-deepening of integration-boundary-fidelity

Ruled narrow at E3 (2026-06-11):

- **integration-boundary-fidelity (ibf)** governs TEST fidelity: "Tests guarding
  a production integration boundary MUST stub ONLY the lowest client boundary
  (raw transport), use REAL object shapes at REAL keys..." (ibf §1). Its
  falsifier is stub-theater — a green test guarding an inert integration.
- **one-gate-invariant** governs PRODUCTION enforcement topology: how many
  physical sites a contract-face path class flows through, and whether the gate
  is enforced at the operative site. Its falsifier is the game-day class:
  decision computed + logged, write degraded anyway (#128 receipt:
  `fail_closed_write_preserve_prior_good` FIRED while the write clobbered).
- They are family: **ibf observes the failure mode; one-gate names the
  structural cure.** Distinct altitude, distinct obligation, distinct
  falsifier ⇒ distinct custody entry. Sibling linkage recorded here (one-way;
  ibf back-link deferred to its next custodian edit — no duplicate custody
  created).

## §3 N-Applied Evidence (N=1, same-satellite)

- **Mint arc**: #127 builder-path fail-closed → game-day exposed Writer-B gap →
  #128 converged Writer A+B onto `write_final_artifacts_async` + backstop-REFUSE
  (`section_persistence.py:905` @ 49099b12) and serve fan-in onto
  `_memory_get_serviceable` (`dataframe_cache.py:391`, sole `memory_tier.get`
  in src/ — E1 re-grep, Item 1, CORROBORATED).
- **Content-RED at each altitude (E1 Item 2, rite-disjoint)**: write-side
  mutation (PRESERVE early-return → `if False:`) → 2 RED by frame content
  ("persisted 0/3 — degraded frame OVERWROTE prior-good"); serve-side mutation
  (degrade-detector blinded) → 2 RED on BOTH normal-serve and circuit-LKG
  paths. 22 GREEN restored after each revert.
- **Honest counter**: one incident, one satellite. The two mutation-REDs prove
  the mint instance is real; they are not a second application.

## §4 Promotion Gate (criteria quoted verbatim from the ibf precedent)

- N>=2 requires what ibf §7 requires: "a SECOND satellite repo applies the
  ... discipline ... The second anchor MUST be a DISTINCT incident at a
  DISTINCT satellite". For one-gate: a second satellite converging a multi-path
  contract face onto a single enforced primitive with content-RED proof at each
  altitude.
- INDEX row per index.md:62 as quoted by ibf: "N_applied >= 3 across at least
  two distinct incidents".
- STRONG mirrors ibf §7: "at least one anchor must be rite-disjoint AND must
  demonstrate the forcing function ... *preventing* a stub-green cure from
  deploying inert — not merely detecting it post-hoc."
- Per the O-2 precedent (ibf §5, 2026-06-11): "Gate requires 'a SECOND
  satellite repo' / 'DISTINCT satellite'" — same-satellite corroboration is
  recorded but NON-promoting. That precedent binds this candidate identically.

## §5 Siblings

- **integration-boundary-fidelity** — the family bond ruled in §2.
- **structural-verification-receipt** — the content-RED obligation is the
  enforcement-topology analogue of claim-truth-at-assertion-time.

*Authored 2026-06-11, eunomia entropy-assessor (E3). No INDEX row. N=1,
[MODERATE, self-ref-capped]. Pythia ruling deferred.*
