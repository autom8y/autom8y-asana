---
type: handoff
artifact_type: IGNITION
initiative_slug: substrate-v2-epoch
authored_on: 2026-07-30
status: accepted
from: consult/meta seat (2026-07-30 three-lane rebase sweep)
to: fresh corridor session (active-rite 10x-dev; S8 = the P5 cutover gate)
consumes: .ledge/handoffs/HANDOFF-wave2-to-s8-cutover-gate-2026-07-29.md
---

# IGNITION — substrate-v2-epoch · S8 (P5 cutover gate) + cutover + PT-04

Operator ignition kit, wave-1-precedent shape. Part 1 = terminal preflight;
Part 2 = pasted verbatim as the fresh session's first message.

State at authoring (rebase-verified 2026-07-30): wave-2 dark build COMPLETE on
main @ `f6d578bf` (#277–#288); v2 fully dark (zero consumers wired); P6 freeze
COMPLIANT; PT-01 PASS; DP-2/DP-3/DP-1F RATIFIED; UV-P-1/2 discharged (prod
warmer = `2201db21`, v2 plane warm-fresh); S9 doctrine PR #279 DRAFT
LANDING-HELD-TO-S8-GREEN; wave-2 session ARCHIVED, no S8 session open.

## Part 1 — operator terminal (verification-first; the corridor is ALREADY seeded)

Wave-1's batched seeding persisted and was re-invoked 2026-07-30
(`inv-20260730-*`): 10x-dev native + arch + thermia + security + **eunomia**
co-seats, 24 agents projected. **Zero new seeding commands are needed.** Do
NOT run bare `ari sync` speculatively — whether it preserves co-seat invokes
is UNVERIFIED [UV-P]; the idempotent recovery is re-running the invokes.

```bash
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana

ari rite current   # EXPECT: Active Rite 10x-dev + borrowed arch/thermia/eunomia(/security)
                   # If (and only if) a set is missing, re-seat additively:
                   #   ari rite invoke arch agents
                   #   ari rite invoke thermia agents
                   #   ari rite invoke security agents
                   # then restart CC once. Note: eunomia co-seat presence is
                   # TOLERATED but bound DORMANT (Part 2) — do not remove, do not use.
```

## Part 2 — paste into the fresh session (verbatim)

```text
ultracode

@potnia — orchestrate substrate-v2-epoch S8 (the P5 cutover gate) under max rigor / max vigor. Rigor CONCENTRATES here by charter design (P7): this is the single event all the epoch's risk was deferred into.
@pythia — standing adjudicator at every genuine fork; at S8 specifically: parity-divergence classification {explained-benign | wound}, fixture-recapture scope, DELTA re-enter routing, cutover-timing. Enumerate before recommending; conflicts are SURFACED, never absorbed.

PREFLIGHT (verify by direct inspection; REFUSE-LOUD on any miss; label drift UV-P):
1. `ari rite current` == 10x-dev with arch + thermia + security (+ eunomia) co-seats; 24 agents in .claude/agents/.
2. `git fetch && git rev-parse origin/main` at/after f6d578bf; latest main Test workflow GREEN. (Nightly Live Smoke red on v1 live-S3 smoke is a KNOWN environmental signal, not a substrate regression — verify it stayed v1-scoped before dismissing.)
3. Founding + wave artifacts readable (paths below); telos status == RATIFIED; PR #279 still DRAFT-held.
4. `/sos start --initiative=substrate-v2-epoch` — tracked session on.

EUNOMIA DORMANCY LAW (binding; new this wave): eunomia agents are co-seated in the roster but are the epoch's S12 ATTESTER SURFACE. NO eunomia agent (verification-auditor, test-cartographer, entropy-assessor, consolidation-planner, rationalization-executor, pipeline-cartographer) may author, review, verify, or touch ANY attested-stream artifact before S12 — attester purity per three-evidence-leg + dispatcher-critic-degeneracy (telos :81-85 T2). Any use = a surfaced violation, not a convenience.

BINDING LAW (read before any dispatch; charter wins on conflict; conflicts SURFACED):
@.ledge/handoffs/HANDOFF-wave2-to-s8-cutover-gate-2026-07-29.md   — THE controlling doc: S8 entry state, hard preconditions (§4), ignite sequence (§5), C8/D6b obligations
@.ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md            — P1–P12 · RC-A..F · doors
@.sos/wip/frames/substrate-v2-epoch.shape.md                      — PT-03 spec (:485-494) · phase-3/4 sequence (§4) · risk map (§9) · defer registry (§10)
@.know/telos/substrate-v2-epoch.md                                — RATIFIED; Gate-B posture; T2 binding
@.ledge/specs/TDD-substrate-v2.md · @.ledge/specs/RC-acceptance-predicates-substrate-v2.md
Evidence on demand (D14 — do not preload): QA-s2..s7 + SEC-s5 + CAPACITY-s4 reviews (.ledge/reviews/) · @.ledge/decisions/DP-3-consumer-contracts.md (424 contract) · @.ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md · tests/harness/substrate_gate/ · src/autom8_asana/substrate/

MISSION (operator verbatim — carry into every dispatch):
every business number the asana dataframe substrate serves is provably current or loudly refused — delivered by a substrate-v2 designed whole and small enough that its correctness is legible, with v1 deleted and the doctrine packaged so any autom8y-* repo can reconstruct the same guarantees as a template application, not a research project.

REALIZATION PREDICATE (verbatim — every exit anchors to it; NOT "PRs merged"):
"Verified-realized" = P5 cutover-gate receipts clean (adversarial fixture replay + bounded live-parity window, every divergence explained) AND a rite-disjoint attester re-derives active_mrr by their own hands matching live Asana within freshness-SLA across ≥2 warm cycles AND v1 planes/bridges/flags enumerate to zero AND doctrine landed at fleet-constitution level.

PHASE S8-0 — PRE-GATE HARDENING (one atomic PR; green CI + qa-adversary; P7 economy):
1. Fix AIMD signal-blindness: tests/harness/substrate_gate/parity.py::PacedLiveParitySource must call slot.reject() on 429 (handoff §4a HARD precondition — the 429-scar class inside the gate itself). Two-sided test: a synthetic 429 MUST propagate to AIMD; a 200 MUST NOT.
2. Build the per-day P10 budget counter (handoff §4b: "none exists") — enforced, not advisory; parity halts loudly at budget exhaustion.
3. Process-singleton PacedAsanaFetcher before any K>1 rebuild (CAPACITY-s4 condition 2).
4. Fixture re-capture (dark-drift R2 mitigation, never executed): refresh the exemplar corpus baseline from CURRENT prod via P10-safe paced reads, receipted; keep the $84,385-vs-$79,585 historical exemplar as exemplar #1 (it is the wound's parity archetype), ADD current-state exemplars. Pythia rules the recapture scope.
5. Hygiene debts (small, in the same PR): mint UV-P-6 for the unregistered "real section counts" premise (handoff :101-102) with a discharge route; promote DEFER-1..4 to .sos/wip/defer-watch/ manifests per shape §6 Gate-C; fix the stale harness docstring ("v2's serve does not exist" — it does, PR #286).

OPERATOR LEVER AT S8-0 EXIT (surface, do NOT execute — P9 reserves applies):
Author DP-4a-READY packet: exact `terraform apply` for terraform/services/asana/substrate_v2_provability_alarms.tf (PROV-1..6) + the D6b FutureDatedProofCount binding — alarms should be LIVE during the parity window, so this packet HALTS for operator action before S8-2 arms. Also author the C8 SLA-governance packet (adversary carry, due no later than PT-03). Resolve in the packet the in-repo-vs-cross-repo tf framing ambiguity (rebase finding: the .tf landed in-repo; frame/shape said parent-repo — state which is of-record).

PHASE S8-1 — FIXTURE REPLAY: full S7 corpus (22/22 RC-predicates), two-sided teeth (silent-serve of broken input FAILS; over-refusal of good input FAILS), divergence ledger opened. Any RED → bounded DELTA back to the owning module (no gold-plating around it).

PHASE S8-2 — BOUNDED LIVE-PARITY WINDOW (arms ONLY after S8-0 merged + DP-4a applied): DAYS not weeks; rides the S4 rebuild primitive EXCLUSIVELY (the sole P10-safe prod channel); v2 computes beside v1 against live prod; EVERY divergence enters the ledger and is classified by pythia {explained-benign | wound}; wound → DELTA to build, window clock restarts per pythia ruling. Budget-enforced + receipted per touch. Multi-day discipline: this window OUTLIVES sessions — each park authors a dated HANDOFF-s8-parity-<date>.md carrying the ledger state + receipts; resume re-verifies preflight. Never fake-complete a window.

PT-03 (HARD — fresh-instance potnia, de novo, per-question receipts, PT-01 precedent):
Q1 every ledger divergence explained · Q2 teeth proven two-sided · Q3 rite-disjoint security critics (threat-modeler + penetration-tester) common-mode-fixture-blindness hunt rendered, floor-not-ceiling · Q4 capacity-engineer rate-safety sign-off (CAPACITY-s4 conditions closed) · Q5 P10 receipts complete + budget honored · Q6 C8 + D6b + ≥1 observed-fired alarm (adversary C10) discharged. FAIL → back to build, no cutover. PASS → proceed.

ON PT-03 PASS (in order): (a) arm + TEST rollback (= restore v1 read-path; prove the restore actually serves); (b) PT-CUTOVER — reversible flip v1→v2 per shape phase-4 (P9 autonomous BECAUSE reversible + rollback proven); (c) PT-04 — observe ≥2 warm cycles with v2 serving (this seeds LEG-2 but does NOT satisfy it — that is eunomia's own-hands S12 job; claim nothing above MODERATE); (d) un-hold S9: mark PR #279 ready per its own landing plan (checkpoint-gated on S8-green, not a door). S11 extinction is NOT in this mandate — DP-1 + DP-4b are operator doors for the next wave.

AUTONOMY + ACCESS (P9): full-auto below one-way doors — build, merge-on-green, staged/reversible writes, prod reads, the reversible cutover flip. Whole-tree read/author access /Users/tomtenuta/Code/a8/** (above, below, across). RESERVED regardless of access: terraform applies (DP-4a/DP-4b), destructive data ops (DP-1 v1 deletion), one-way-door ADR ratification. Access ≠ authority to cross a door.

PROD-TOUCH LAW (P10): paced primitives only (AIMD/429-banking, bounded concurrency), per-day budget (built in S8-0, enforced thereafter), off-peak preference, receipt per touch. Ad-hoc unpaced pulls BANNED — agents included.

DISCIPLINE PACK (load on demand): prompting · context-engineering · anti-theater-checks · dispatch-retry · critic-substitution-rule · structural-verification-receipt · telos-integrity-ref · cross-rite-handoff. Main thread is the SOLE dispatcher. Emergent findings are findings — scope changes go through pythia, never silent.

CLOSE SEAM (tribute to the next operator): the S8 arc closes (or parks) by authoring .ledge/handoffs/HANDOFF-s8-<state>-<date>.md per cross-rite-handoff schema — telos + predicate verbatim, PT-03 verdict with per-question receipts, parity ledger, cutover/rollback state, PT-04 observations, DP-4a/C8 packet status, fresh SVR/UV-P deltas, and the exact S11/S12 ignite sequence — plus telos Gate-B writeback (real path:line anchors for everything landed) and /sos wrap. The next session must be able to ignite S11+S12 from the handoff alone.
```

## What comes back to the operator from S8

DP-4a-READY (terraform apply command — your hands) + C8 SLA packet before the
parity window arms; then the PT-03 verdict + parity ledger; then cutover/PT-04
state. Next-wave doors (yours): DP-1 (v1 deletion), DP-4b (warmer-DMS
terraform). S12 attestation = `ari sync --rite=eunomia` + one restart — only
after S11.
