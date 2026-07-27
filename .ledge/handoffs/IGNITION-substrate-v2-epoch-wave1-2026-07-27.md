---
type: handoff
artifact_type: IGNITION
initiative_slug: substrate-v2-epoch
authored_on: 2026-07-27
status: accepted
from: framing-session (charter → frame → shape → telos RATIFIED)
to: fresh corridor session (active-rite 10x-dev, wave-1 = S1)
---

# IGNITION — substrate-v2-epoch · Wave-1 (S1 whole-design)

Operator ignition kit. Part 1 is run in the terminal BEFORE opening the fresh
session; Part 2 is pasted verbatim as the fresh session's first message.

Founding artifacts (all inscribed 2026-07-27): charter (accepted, 12 rulings) ·
frame + shape (local, `.sos/wip/frames/` — gitignored by platform design, same-
machine only) · telos **RATIFIED** (Gate A CLOSED, deadline 2026-09-30
checkpoint, attester eunomia). PR #276 (P6 v1-honesty floor) MERGED `bdbf86cb`.

## Part 1 — operator terminal (Phase 0, batched seeding, ONE restart)

Meta-optimization over shape §4 (surfaced, not silent): the shape staggers
co-seats (arch at Phase 0; thermia/security at Phase 2), each transition
carrying the UV-P-5 restart question. Batching ALL THREE invokes before the
single restart collapses UV-P-5 and removes every mid-corridor restart — S1
flows into the 5-wide dark-build fan-out with zero further operator CLI.
`ari sync --rite` is a SINGULAR full switch; `ari rite invoke` is additive
co-seat (both CONFIRMED live, shape §11).

```bash
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana

ari sync --rite=10x-dev          # SINGULAR full switch: eunomia -> corridor
ari rite invoke arch agents      # co-seat: arch-adversary (S1 design critic) + structure-evaluator (S9 proxy)
ari rite invoke thermia agents   # co-seat: rate-safety/capacity (S4/S6; P10 teeth)
ari rite invoke security agents  # co-seat: security-reviewer/threat-modeler (S5 auth, S8 gate critic)

# -> RESTART Claude Code (once). Do NOT co-seat eunomia: T2 corridor purity —
#    the attester rite must never be the executing rite (telos :81-85).
```

## Part 2 — paste into the fresh session (verbatim)

```text
ultracode

@potnia — orchestrate substrate-v2-epoch WAVE-1 under max rigor / max vigor.
@pythia — standing adjudicator at every genuine fork (option-enumeration-discipline: enumerate before recommending; never absorb a conflict — surface it).

PREFLIGHT (verify by direct inspection; REFUSE-LOUD on any miss; label drift UV-P — never assume):
1. `ari rite current` == 10x-dev (corridor open; T2 satisfied).
2. Roster present in .claude/agents/: potnia + pythia + native 10x-dev {architect, requirements-analyst, principal-engineer, qa-adversary} + co-seated arch {arch-adversary, structure-evaluator, dependency-analyst, remediation-planner, topology-cartographer}, thermia {capacity-engineer, heat-mapper, systems-thermodynamicist, thermal-monitor}, security {security-reviewer, threat-modeler, penetration-tester, compliance-architect}.
3. Founding artifacts readable (paths below); telos status == RATIFIED.
4. `/sos start --initiative=substrate-v2-epoch` (or `/go`) — tracked session on.

BINDING LAW (read before any dispatch; on conflict the CHARTER wins and the conflict is SURFACED, not absorbed):
@.ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md          — P1–P12 · RC-A..F acceptance invariants · one-way-door register
@.sos/wip/frames/substrate-v2-epoch.md                          — mission · §3 SVR ledger (L1–L9) + UV-P-1/2/3
@.sos/wip/frames/substrate-v2-epoch.shape.md                    — 12-sprint DAG · §2 sprint specs · §3 checkpoints+doors · §4 sequence · §8 tension rulings (T1–T5) · §9 risk map · §10 UV-P routing/defer registry
@.know/telos/substrate-v2-epoch.md                              — RATIFIED telos; Gate B/C posture
Evidence pull on demand (do not preload — D14): @.ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md · @.ledge/decisions/ADR-seam1-entity-identity-key.md · @.ledge/decisions/ADR-006-freshness-equals-verification-recency.md · @.know/scar-tissue.md

MISSION (operator's words — carry verbatim into every dispatch):
every business number the asana dataframe substrate serves is provably current or loudly refused — delivered by a substrate-v2 designed whole and small enough that its correctness is legible, with v1 deleted and the doctrine packaged so any autom8y-* repo can reconstruct the same guarantees as a template application, not a research project.

REALIZATION PREDICATE (verbatim — every sprint exit anchors to it; NOT "PRs merged"):
"Verified-realized" = P5 cutover-gate receipts clean (adversarial fixture replay + bounded live-parity window, every divergence explained) AND a rite-disjoint attester re-derives active_mrr by their own hands matching live Asana within freshness-SLA across ≥2 warm cycles AND v1 planes/bridges/flags enumerate to zero AND doctrine landed at fleet-constitution level.

WAVE-1 MANDATE — S1 ONLY (shape §2:S1, internals non-prescriptive):
Dispatch /architect ultracode: design substrate-v2 WHOLE from RC-A..F as CONSTRUCTIVE invariants (violations unconstructable or fail-loud — P3); resolve forks F1–F6 under option-enumeration-discipline with arch-adversary as RITE-DISJOINT critic challenging every option slate (critic-substitution-rule; self-assessment caps MODERATE); freeze the inter-module seams (freshness / storage+keys / rebuild / serving / observability) so wave-2 fans out 5-wide; requirements-analyst renders RC-A..F as testable acceptance predicates; principal-engineer holds feasibility + frozen-seam interfaces. Exit = ratified TDD (.ledge/specs/TDD-substrate-v2.md + ADR set), green CI + adversarial review (P7 — do NOT gold-plate), PT-01 HARD-passed.
S1 preload slice ONLY (D14): charter + shape §2:S1 + DEFECT (full) + ADR-seam1:120-162,458-491 + ADR-006:462 + skills {option-enumeration-discipline, doc-artifact-schemas, structural-verification-receipt, premise-validation-discipline}. prod_touch: none.

DOORS AT S1 — NOTHING CROSSES ON AUTO-RATIFY (P8):
DP-2 (door #2, F3 key/schema) + DP-3 (door #3, F5 consumer contracts) → author compact OPERATOR DECISION-PACKETS to .ledge/decisions/DP-{2,3}-*.md with the adversary's dissent attached, then HALT those threads for operator ratification. All other F-fork decisions auto-ratify after adversarial challenge.

WAVE-2 STAGING (prepare, do NOT fire): on PT-01 pass, stage dispatch specs for the 5-wide fan-out {S2 freshness, S3 storage/keys, S6 observability, S7 gate-harness, S9 doctrine-author} per shape §4 phase-2 (worktree-per-sprint via workflow:sprint-parallel-worktrees; one atomic PR per sprint; S4/S5 gated on S2+S3). Build sprints ignite only after DP-2/DP-3 ratification where their seams depend on those doors — pythia adjudicates which are door-independent and may flow immediately.

AUTONOMY + ACCESS (P9, operator-granted): full-auto below one-way doors — design, build, merge-on-green, staged/reversible writes, prod READS. Standing read/author access across the WHOLE tree: /Users/tomtenuta/Code/a8/** (this repo, parent monorepos, sibling autom8y-*, .a8/knossos constitution layer — above, below, or across). RESERVED to operator regardless of access: destructive data ops, cross-repo terraform APPLIES, one-way-door ADR ratification (packets instead). Access ≠ authority to cross a door.

PROD-TOUCH LAW (P10 — the 429 scar is on record): every prod touch routes through paced primitives (AIMD/429-banking, bounded concurrency), respects a per-day budget, prefers off-peak, leaves a receipt. Ad-hoc unpaced pulls are BANNED — agents included. Wave-1 S1 requires NO prod touch.

DISCIPLINE PACK (load on demand, not upfront): prompting · context-engineering · anti-theater-checks · dispatch-retry · orchestrator-antipatterns · telos-integrity-ref · cross-rite-handoff. Main thread is the SOLE dispatcher (agents cannot spawn agents). Report emergent findings as findings — never silently widen scope (charter non-goals + shape §10 defer registry govern).

CLOSE SEAM (meta-optimal tribute to the next operator): wave-1 closes (or parks under context pressure) by authoring .ledge/handoffs/HANDOFF-s1-substrate-v2-design-<date>.md per cross-rite-handoff schema — carrying the telos, the predicate verbatim, PT-01 verdict, both decision-packets' status, staged wave-2 specs, fresh SVR/UV-P deltas — plus telos ledger writeback (Gate B anchors for anything landed) and /sos wrap. The next session must be able to ignite wave-2 from the handoff alone.
```

## Wave-1 exit → operator levers

PT-01 verdict + DP-2/DP-3 packets arrive for ratification; wave-2 fires on
your word. Later phase transitions (shape §4): Phase-7 attestation is
`ari sync --rite=eunomia` + one restart — far downstream, not now.
