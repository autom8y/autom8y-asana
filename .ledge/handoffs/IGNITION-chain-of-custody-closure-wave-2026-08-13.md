---
type: handoff
status: accepted
artifact_id: IGNITION-chain-of-custody-closure-wave-2026-08-13
initiative: chain-of-custody-closure
date: 2026-08-13
purpose: >-
  The audited paste-block ignition kit for a fresh CC session to dispatch the
  chain-of-custody-closure wave: spine card, citation legend, seat roster,
  14 verbatim-binding fences, per-sprint charge template, first-move
  verification, and the downstream operator /handoff seam.
ratified_by: RULING-operator-coc-defaults-ratification-2026-08-13 ("defaults stand")
precedence: IGNITION-exec-insight-delivery-wave-2026-08-13 (rev 2)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
---

# IGNITION — chain-of-custody-closure wave

## §0 Spine card

**Mission**: the trust machine's own chain of custody holds under attack — its
swap-detector detects swaps, its write door checks permission not merely
identity, its warm path feeds what it claims to serve, and its secret-leak
class cannot recur.

**Realization predicate (operator's words, carried into every exit)**:
"verified-realized" = falsifiable receipts, NOT "PRs merged": **(i)** a
two-sided limb-(a) demonstration — a count-preserving payload swap classified
NOT-OBSERVABLE AND an honest delivery classified OBSERVABLE, with the join's
module contract matching its implementation (no over-claiming docstring
survives); **(ii)** an RE-2 receipt at whatever rung the evidence honestly
reaches (enforced deny-on-missing-grant in harness, OR a ratified design with
a named owner — rungs never conflated, ADR-007); **(iii)** a gate proven
BITING by canary, red-then-green (RUF100 precedence).

**State at ignition**: `origin/main` @ `d7560153` (#364). ECS
`autom8y-asana-service:770` PRIMARY (image `d756015`, rollout COMPLETED
2026-08-13T12:44:56Z). AL-5 quiet window opens **~2026-08-15T12:45Z**.
Q-register ratified "defaults stand"; **Q-3 and Q-4 are HALTS** (CC-5 shut;
nothing merges). Phase 1 is **FIVE-WIDE**: CC-1 ∥ CC-2 ∥ CC-3 ∥ CC-4 ∥ CC-6.

**The DAG** (full blocks in the shape — this is the map, not the spec):

| id | what | author (rite) | critic (rite-disjoint) | exit rung |
|---|---|---|---|---|
| CC-1 | WS-A swap-detector, all 3 limbs, ONE sprint | principal-engineer (10x-dev) | structure-evaluator (arch) | PR-UP-MERGE-HELD |
| CC-2 | RE-2 design, SEC-001 | security-reviewer (security) | dependency-analyst (arch) | rung-DESIGN, paper |
| CC-3 | RE-2 blast radius, SEC-002/003 | penetration-tester (security) | platform-engineer (sre) | UV-Ps dispositioned |
| CC-4 | RE-1 option slate (prices F-1) | platform-engineer (sre) | remediation-planner (arch) | priced slate, paper |
| CC-5 | RE-1 ruled repair | ⛔ SHUT at F-1 | per branch | — |
| CC-6 | WS-D recon: gitleaks locus + baseline | pipeline-cartographer (eunomia) | threat-modeler (security) | finding, paper |
| CC-7 | WS-D biting gate + canary | janitor (hygiene) | security-reviewer (security) | PR-UP-MERGE-HELD |
| CC-8 | ATTEST limbs (i)+(iii) at held rung | verification-auditor (eunomia) | compliance-architect (security) | rung-ATTESTED |

Hard edges ONLY: E1 CC-6→CC-7 · E2 CC-1→CC-8 · E3 CC-7→CC-8 · E4 F-1→CC-5
(operator) · E5 F-3→CC-2/CC-3 (SATISFIED by Q-2: in-session). Do not add
edges; over-sequencing kills the parallelism.

**Checkpoints, all HARD**: PT-01 potnia (Phase-0→1, wave width) · PT-02 pythia
(**F-1, HALTING**, fires on CC-4 exit) · PT-03 potnia (Phase-1 fan-in, NCSR
roll-call = primary output) · PT-04 pythia (F-7/F-8, fires on CC-6 exit) ·
PT-05 potnia (Phase-2→3) · PT-06 pythia (**F-4, HALTING, EVENT-DRIVEN** —
fires the FIRST time any artifact is ready to inscribe, not at a phase
boundary) · PT-07 potnia (wave exit, rung roll-call → the §6 handoff seam).

## §1 Citation legend — read in this order, cite `file:line`, never re-derive

1. `@.sos/wip/frames/chain-of-custody-closure.shape.md` — THE SPEC. 8 sprint
   blocks, edges, PT-01..07, §A NCSR (7 pre-registered negatives, 4 refuters
   each), §9 risk map, §B defer registry, §D SVR ledger.
2. `@.sos/wip/frames/chain-of-custody-closure.md` — the frame: mission, §2.2
   telos block (inscribe verbatim → `.know/telos/chain-of-custody-closure.md`,
   first paper act), §2.4 non-substitution fence, workstreams, F-1..F-7,
   UV-P-CoC-1..4.
3. `@.ledge/decisions/RULING-operator-coc-defaults-ratification-2026-08-13.md`
   — what "defaults stand" ratified per item; the Q-9 deploy-race receipt;
   what was NOT absorbed.
4. Grounding: `@.ledge/handoffs/HANDOFF-10x-dev-to-sre-ex6-receipt-limb-2026-08-13.md`
   (**§4a JOINT GATE**) · `@.ledge/handoffs/HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13.md`
   (RE-2, SEC-001..003, §4 fences) · `@.ledge/handoffs/NORTH-2026-08-13.md`
   (§7 addendum; its ":769 untraced" line is SUPERSEDED by the ruling's Q-9
   table) · `@.ledge/reviews/PROBE-story-cache-warmth-2026-08-13.md` (RE-1
   blast radius, measured) · `@.ledge/decisions/RULING-operator-morning-set-2026-08-13.md`
   + `@.ledge/decisions/RULING-operator-k0b-uvp2-2026-08-13.md` (riders).

**TREE-AUTHORITATIVE COPIES** (differ from origin/main BY DESIGN — read from
the session working tree, never from a worktree cut of origin/main):
`ADR-mission-a-source-of-record-2026-08-12.md` · `NORTH-2026-08-13.md` · the
sre handoff (§4a exists ONLY in the tree copy) · both files in §1 items 3
above and this kit. The frame + shape live in gitignored `.sos/wip/` — tree
only, by definition.

## §2 Seats — 16 confirmed; the displaced five are NOT dispatchable

Roster per §0 table plus checkpoints (potnia, pythia). Binding capability
facts: **potnia is `tools: Read` only** — every potnia checkpoint is
Read-and-report; the MAIN THREAD persists the receipt. **Agents cannot spawn
agents** — the main thread is the sole dispatcher. **Every clock stays on the
main thread** (subagent self-park is unreliable; never park a waiter in a
seat). **qa-adversary is never a critic** in a 10x-dev-authored wave.
**NOT dispatchable** (displaced/absent): audit-lead, architect-enforcer,
entropy-assessor, consolidation-planner, arch-adversary. Ratified
substitutions: structure-evaluator for entropy-assessor; security-reviewer at
write-path surfaces. **myron is excluded** (it framed this wave).
Self-attestation caps **MODERATE** everywhere; STRONG comes only from the
rite-disjoint critic's own-hands re-derivation.

## §3 The fourteen fences — VERBATIM-BINDING on every seat

1. **MERGE FENCE (Q-4 HALT)** — NOTHING merges to autom8y-asana until the
   operator lifts F-4 at PT-06. PRs go up **UN-ARMED**: in THIS repo
   `{strict:true, enforce_admins:true}` means an armed auto-merge WILL fire —
   never `gh pr merge --auto` this wave. PR-UP-MERGE-HELD is a NAMED rung,
   not a failure. Even docs merges move the AL-5 window (#364 proved it).
   **Rider (Q-9 receipt)**: serial merges do NOT guarantee serial deploys —
   after any future fence lift, verify the PRIMARY deployment's image tag
   equals the intended head before trusting post-merge state.
2. **CODE FROM origin/main ONLY** — the local checkout predates #361-363:
   `rung_receipts/`, `rail_delivery/`, `readout/` exist ONLY at origin/main.
   ALL build work happens in worktrees cut from `origin/main` under
   `.knossos/worktrees/`. GOVERNANCE reads come from the session working tree
   (§1 tree-authoritative list). Src citations: `git show origin/main:<path>`.
3. **THE JOINT GATE** — REC-001 + REC-003 exit as ONE gate (sre handoff §4a).
   CC-1 is one sprint BY DESIGN; no state may exist where one landed without
   the other. The join's docstring contract must match its implementation at
   exit — an over-claiming docstring is a FAIL, not a nit.
4. **HELD-RUNG ATTESTATION (Q-10)** — CC-8 attests limbs (i)+(iii) at
   PR-UP-MERGE-HELD. The parent limb-(a) Phase-4 attestation stays eunomia's
   and stays BLOCKED until WS-A's both halves LAND (frame §2.4
   non-substitution — this wave's attestation is never cited for Rung E).
5. **HALTED FORKS** — F-1 (CC-5 SHUT) and F-4 (merge posture): surface at
   PT-02/PT-06 with pricing attached; NEVER resolve. HOLD is first-class.
6. **CR-1** — all three Asana write classes (comments, tasks, custom fields)
   are OPERATOR-RESERVED. The S2S gap means this process fence is the ONLY
   control. Never exercise a write path — not even to reproduce WS-B's
   finding.
7. **CR-2** — `s3://autom8y-asr-verdicts` operator-reserved: not read, not
   listed.
8. **CR-5** — no agent mints, extracts, copies or logs credential material.
   On ENCOUNTERING it anywhere: stop reading, report path + fact only. Live
   hazard: a Critical unrotated `ASANA_PAT` is reachable in this repo's git
   history (commits `a578ca85`, `525431de`, `15cffee1`, path
   `.claude/settings.local.json`; `.know/defer-watch.yaml:382-403`;
   OPERATOR-PENDING-ROTATION). **WS-D rider**: the CC-7 canary plants a
   SYNTHETIC secret on a throwaway branch — never touches, cites, or scans-to
   -surface the real historical leak beyond path+fact. Rotation is
   operator-only (Q-5: DEFER).
9. **MONOREPO TRAP** — `/Users/tomtenuta/Code/a8/a8/repos/autom8y` is on a
   divergent branch with a sibling session actively committing: reads via
   `git show origin/main:<path>` ONLY. Converse: in autom8y-asana the working
   tree is authoritative for the §1 list and local `main` lags.
10. **SEATS** — §2 is binding: no displaced seat, no invented seat, potnia
    Read-only, main thread sole dispatcher, clocks on main thread.
11. **NEVER `ari sync --rite=`** (destructive in this estate). Shape-schema's
    own §4 template prescribing it is SUPERSEDED (shape DV-4). Zero sync is
    needed — all six rites are live co-seated (verified 16/16).
12. **NO INFRA MUTATION** — no `terraform apply` (bare or targeted), no
    `terraform init`, no mutating AWS call; whole-directory apply in
    `terraform/services/asana` binds 7 alarms; L4 keep-warm stays REFUSED.
    Read-only AWS is permitted where a sprint's receipts need it.
13. **NO CLIENT/EXTERNAL COMMUNICATION** — no live Slack posts this wave
    (REC-004 is out of scope, operator-gated); delivery to humans is
    operator-performed, always.
14. **METHOD** — ADR-007 axis discipline + the decision-space charter
    (`.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md`)
    inherit automatically. NCSR §A is BINDING: every sprint exit reports its
    pre-registered negatives with refuter returns (verdict grammar
    STANDS/FALLS/NARROWS, §A.3 reporting duty — a null return is evidence,
    reported, never dropped). One-quantity-two-questions vigilance on every
    number.

## §4 Per-sprint charge template (context-engineering)

Each dispatch preloads ONLY its station's needs: the sprint block from the
shape (verbatim), the fences (all 14, §3), the grounding files ITS block
cites, and its rite's native skills. Charge structure: (1) seat + sprint id +
mission line; (2) the sprint block verbatim; (3) fences; (4) SVR duty —
re-verify platform-behavior premises at execution time, label UV-P on drift;
(5) NCSR duty — run the block's pre-registered negatives, report refuter
returns; (6) exit contract — exit at the rung the receipts honestly reach,
return a raw report (artifact paths, receipts, negatives, UV-Ps) for the main
thread to persist. Critics get the author's output + the SAME fences + an
explicit adversarial charge: attack, do not confirm; hop one past where the
author stopped.

## §5 FIRST MOVE — verification, halt-by-design

Before ANY dispatch:
```
ari rite current            # expect: 10x-dev
ls .claude/agents/          # every §0/§2 seat must resolve here
```
HALT and surface to the operator if any named seat is missing. ZERO sync.
The ONLY permitted `ari` state commands this wave are read-forms. FORBIDDEN:
`ari sync --rite=<anything>`. Not needed and not fired: any `ari rite invoke`
(all six rites already co-seated; re-seating the displaced five is an
operator lever explicitly NOT fired by "defaults stand").

Then: inscribe the telos (frame §2.2 verbatim → `.know/telos/
chain-of-custody-closure.md`, in-tree, un-merged) — the first paper act — and
dispatch Phase 1 five-wide.

## §6 The downstream operator /handoff seam (PT-07 exit contract)

The wave closes at a handoff terminal, never a silent stop. PT-07 authors
`HANDOFF-coc-wave-close-<date>.md` (cross-rite-handoff schema) carrying: the
rung roll-call (every sprint's honest exit rung — PR-UP-MERGE-HELD entries
listed as HELD with their PR numbers, never as done); the two halted forks
with pricing (F-1 slate from CC-4; F-4 with the AL-5 window state at close);
the NCSR ledger (all negatives + verdicts); the defer registry delta; UV-P
dispositions; and the operator's next-word menu (lift F-4 → merge order;
rule F-1 → open CC-5; word to eunomia when both WS-A halves LAND). Nothing
the operator did not rule may be recorded as decided.

## §7 The operator grant (verbatim intent, with correctness fences intact)

The operator grants comprehensive user-grade permission to the pantheon and
borrowed components, with full READ access to all repos on the filesystem —
above, below, or across the tree — for everything short of strict
impossibilities. The grant does NOT dissolve correctness fences: monorepo
reads stay `git show origin/main:` (divergence, not permission); writes stay
scoped to this wave's artifacts + worktree branches; the 14 fences bind. Bias
toward clean, modern, robust integration and toward confidently landing these
hard-earned efforts — at the rung the receipts honestly reach.
