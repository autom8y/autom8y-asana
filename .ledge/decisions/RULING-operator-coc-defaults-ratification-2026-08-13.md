---
type: decision
status: accepted
artifact_id: RULING-operator-coc-defaults-ratification-2026-08-13
initiative: chain-of-custody-closure
date: 2026-08-13
ruled_by: 'OPERATOR (in-session, post-shape: "defaults stand!")'
ratifies: .sos/wip/frames/chain-of-custody-closure.shape.md §Q-register (10 items)
precedence: RULING-operator-exec-defaults-ratification-2026-08-13 (per-item application)
binding_note: >-
  "Defaults stand" ratifies the 8 defaulted items and ACKNOWLEDGES the two
  halts. It resolves neither halt. Nothing beyond the per-item applications
  below is decided here.
---

# OPERATOR RATIFICATION — chain-of-custody-closure Q-register defaults

The shape's Q-register was authored for one-move ratification (its own design,
per the exec-wave precedent). The operator's word: **"defaults stand!"**
Per-item application follows so no later seat misreads the scope.

## Ratified as defaulted

- **Q-1 (F-5) — RATIFIED.** The telos is inscribed verbatim from frame §2.2 to
  `.know/telos/chain-of-custody-closure.md` as the wave's first paper act —
  in-tree, un-merged (Q-4 governs the landing). `verification_deadline:
  2026-09-12` stands **PROPOSED** (UV-P-CoC-2 remains open; the deadline is
  derived, not ruled).
- **Q-2 (F-3) — RATIFIED: WS-B locus IN-SESSION.** This resolves fork F-3 and
  satisfies hard edge E5. **Phase 1 launches FIVE-WIDE** (CC-1 ∥ CC-2 ∥ CC-3 ∥
  CC-4 ∥ CC-6). The security handoff's §5 locus question
  (`HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13.md`) is answered by this
  ratification: in-session, co-seated borrow.
- **Q-5 (F-2) — RATIFIED: DEFER.** cred-t21 rotation stays disabled,
  operator-only, runbook ready. No agent touches rotation.
- **Q-6 (F-7) — RATIFIED-CONDITIONAL.** The baseline fork may dissolve on
  CC-6's answer; if it fires, the default is **enforce-with-baseline** (the
  historical leak is baselined, the gate bites on NEW instances). PT-04
  surfaces it either way.
- **Q-7 (F-6) — RATIFIED: NOT REACHED.** REC-002 monorepo wiring stays outside
  the wave; DF-2 stands (WS-A touches zero monorepo paths).
- **Q-8 (F-8) — RATIFIED.** WS-D prefers the in-repo locus; if CC-6 finds the
  gate can only bite cross-repo, that surfaces as an operator fork at PT-04 —
  never built unilaterally.
- **Q-9 — RATIFIED and DISCHARGED same session.** See §Q-9 below.
- **Q-10 — RATIFIED.** CC-8 attests limbs (i)+(iii) **at the held rung**
  (PR-UP-MERGE-HELD). The frame's §2.4 non-substitution fence is untouched:
  this attestation grades the instrument-wave only; the parent limb-(a)
  Phase-4 attestation remains eunomia's and remains BLOCKED until WS-A's both
  halves LAND (not merely build).

## The two halts — acknowledged, NOT resolved

- **Q-3 (F-1) — HALT STANDS.** RE-1 ownership + locus is operator-only and
  unresolved. **CC-5 stays SHUT.** WS-C exits at a priced option slate
  (CC-4) + PT-02 surfaces the fork with the pricing attached. Any seat
  treating the slate as a decision is over-reading.
- **Q-4 (F-4) — HALT STANDS.** **Nothing merges to this repo.** PRs go up
  UN-ARMED; PR-UP-MERGE-HELD is a NAMED rung this wave. PT-06 is event-driven
  and fires the first time any artifact is ready to inscribe. O-7a
  regime-boundary bookkeeping remains the priced alternative if the operator
  chooses paper over quiet.

## §Q-9 — DISCHARGED: the `:769` ECS registration is traced

Read-only `describe-task-definition` across `:767`–`:770` (us-east-1,
2026-08-13 evening):

| rev | registered (UTC) | image tag | = commit / PR |
|---|---|---|---|
| :767 | 10:19:18Z | `164382c` | `164382c0` #361 (EX-4) |
| :768 | 11:15:02Z | `7870e9f` | `7870e9fe` #363 (EX-6) |
| :769 | 11:35:03Z | `d45aa30` | `d45aa305` #362 (EX-5) |
| :770 | 12:28:18Z | `d756015` | `d7560153` #364 (docs corpus) — PRIMARY, rollout COMPLETED 12:44:56Z |

**Findings:**
1. **No external deployer exists.** All four deploys attribute to this repo's
   own merge pipelines. The AL-5 measurement regime's actor set is clean; the
   O-7a anchor on `:770` (window opens ~2026-08-15T12:45Z) stands.
2. **A CI pipeline race is receipted**: #362 merged before #363, but #362's
   deploy pipeline completed 20 minutes AFTER #363's — so `:769` deployed an
   OLDER image over a newer one. Between 11:35Z and ~12:45Z the service ran
   the #362 image, which lacks #363's `rail_delivery/` code. Transient,
   self-healed by `:770`. **Standing hazard, carried to the kit (fence 1
   rider) and to any future K-4 sequencing: serial squash-merges do NOT
   guarantee serial deploys.** Post-fence-lift discipline: verify the PRIMARY
   deployment's image tag equals the intended head before trusting any
   post-merge state or measurement.
3. **A consult claim is FALSIFIED**: the 2026-08-13 pythia consult (and
   NORTH §7.2, which carried it) stated `:769` "matches no commit in this
   repo." It matches `d45aa305`. The likely error source: comparison against
   a short recent-commit list or the lagging local checkout. Recorded per the
   method — a second reader going one hop past where the record stopped, this
   time against the oracle's own output. NORTH §7's "trigger untraced" is
   hereby superseded by this table.

## NOT absorbed by "defaults stand"

- **The 75k budget lever is NOT fired.** The displaced five (audit-lead,
  architect-enforcer, entropy-assessor, consolidation-planner, arch-adversary)
  stay un-seated; the ratified substitutions govern. Re-seating is a separate
  operator word.
- **The complaint** (`.sos/wip/complaints/COMPLAINT-20260813-204500-pythia.yaml`)
  routes to the framework, not this wave.
- **UV-P-2** — the pulse-check was SENT by the operator 2026-08-13; the answer
  is pending and remains OPEN. Nothing here touches GATE-FORK.
- Everything in shape §B (defer registry, 11 carried + 8 UV-Ps + 3 opened)
  stays exactly as recorded.
