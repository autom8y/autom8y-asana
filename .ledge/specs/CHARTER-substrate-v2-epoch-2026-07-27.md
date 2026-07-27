---
type: spec
artifact_type: CHARTER
initiative_slug: substrate-v2-epoch
authored_on: 2026-07-27
authored_by: operator-interview (3-phase, 12 rulings)
status: accepted
ratification: operator-interview-2026-07-27 (12 explicit rulings via AskUserQuestion)
consumes: .ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md
seeds: /frame → /architect → /build → /qa ultracode workflows
---

# CHARTER — Substrate-v2 Epoch (dataframe substrate coherence)

Vision-altitude charter from the 2026-07-27 operator interview. This document is
deliberately NON-PRESCRIPTIVE below the principle line: the /architect, /build,
/qa ultracode workflows own the design space, bounded only by what is ratified
here. Do not narrow it further without a new operator ruling.

## The wound (why this epoch exists)

`active_mrr` served **$79,585 — 14 days stale — under a false-fresh "verified
1m ago" signal**; the true value was **$84,385**. The operator's gut caught what
the system's green signals did not. Root-cause analysis found not N bugs but
**six broken invariants** with N symptoms (full evidence: the DEFECT report):

| RC | Broken invariant |
|----|-----------------|
| RC-A | No single source of truth per (project, entity) — 4 row-copies, 3 writers, 2+ readers, nothing asserts agreement (the "double-write cache location") |
| RC-B | Freshness is write-time metadata (stamps, mtimes), not content-derived truth |
| RC-C | Plane-correctness is per-call-site manual discipline; the enumerated guard drifted and missed a whole layer |
| RC-D | Migrations defer with no forcing function; "temporary" bridges are immortal (dual-plane since 2026-06-09) |
| RC-E | No atomic, side-effect-explicit, rate-safe rebuild primitive (building mutates prod; partial = corrupt; rebuilds 429-storm) |
| RC-F | Observability can read green while broken (query-gated alarms, dead-man on a dead metric) |

These six become **substrate-v2's acceptance invariants**: v2 is not done until
each is impossible-by-construction or fail-loud, and v1's copies of them are
deleted.

## North star

One small, obviously-correct substrate: a number served is a number the system
can prove; a number it cannot prove is refused loudly; and the system is small
enough that the proof is legible. Asana is the proving ground; the doctrine and
its reusable forms are the deliverable that unblocks the same reconstruction
across the fleet.

## Ratified principles (P1–P12)

**P1 — Sequencing.** Asana-first at max rigor, explicitly AS the unblock for the
fleet-wide program. Stream 2 (fleet sweep) starts from extracted doctrine, not
from scratch. Doctrine extraction is load-bearing, not optional.

**P2 — Truth posture: refuse > wrong.** The substrate never serves an
unprovable number. Fail-loud refusal is a feature, not an outage. Alarm
philosophy follows: alarms assert provability, not liveness.

**P3 — Subtraction posture: subtract > guard.** Prefer deleting surfaces,
paths, planes, and flags over guarding them. This applies to v1's remains AND
to guard machinery itself: prevention **by construction** (e.g. keys that
cannot be built plane-blind) beats proliferating guard suites. Make it small
enough to be obviously correct, then harden what remains.

**P4 — Shape: epoch re-architecture, dark launch, hard cutover.** Substrate-v2
is designed WHOLE (not incrementally negotiated with v1's shape), built dark
alongside v1, and lands in one cutover event. No strangler half-states — the
transitional-state pattern is the disease (RC-D).

**P5 — The cutover gate carries the live leg.** The single validation event =
full adversarial fixture replay **PLUS a time-boxed live-parity window (days,
not weeks)**: v2 computes the real numbers beside v1 against live prod, and
**every divergence is explained before the flip**. Rollback = restore v1.
V1 deletion follows cutover only after the gate's receipts are clean.

**P6 — V1 meanwhile: honest, frozen, zero new investment.** The landed guards
(PR #276: entity-aware prober, plane-divergence refusal, verification-axis
warnings) keep v1 honest. No further v1 hardening; a v1 refusal is answered by
an operator re-baseline, never by new v1 code. The epoch's enemy is v1 quietly
re-absorbing investment.

**P7 — Working proof bar: green CI + adversarial review.** Per unit of work,
the bar is discriminating tests + adversarial review — economical by design.
Rigor concentrates at exactly two places: the cutover gate (P5) and one-way
doors (P8). Do not gold-plate the corridor; do not thin the doors.

**P8 — Decision rights: adversarial delegation.** /architect enumerates options
exhaustively (option-enumeration-discipline); an adversary challenges before
ratification; decisions auto-ratify — EXCEPT one-way doors, which go to the
operator as compact decision packets **with the adversary's dissent attached**.
The operator governs the doors, not the corridor.

**P9 — Autonomy: full-auto below one-way doors.** Design, build, merge-on-green,
deploy-dispatch, prod reads, staged/reversible prod writes: autonomous.
Operator-reserved: destructive data operations (v1 plane deletion), cross-repo
terraform applies, ratification of one-way-door ADRs. Extends the fleet
constitution's full-auto-below-identity posture.

**P10 — Prod-touch policy: paced + budgeted.** All prod touches route through
paced primitives (AIMD / 429-banking, bounded concurrency), respect a per-day
API budget, prefer off-peak for heavy pulls, and leave a receipt. **Ad-hoc
unpaced pulls are banned for everyone, agents included** (the 2026-07-27
429-storm during ad-hoc validation is the counterexample on record).

**P11 — Doctrine home: constitution + memory; enforcement by construction.**
Ratified invariants land at the fleet-constitution level (.a8/knossos) so every
autom8y-* repo inherits them as standing law, and are recorded in scar-tissue /
ADR memory. The operator deliberately did NOT select blanket repo-level guard
suites as the doctrine home — consistent with P3, enforcement is primarily by
v2's construction (violations unconstructable), with CI teeth used sparingly
where construction cannot reach (e.g. bridge-sunset expiry). *Interpretation
note: this reading of the non-selection follows the P3 posture; if wrong,
amend here.*

**P12 — Epoch exit = v1 deleted + doctrine shipped.** The epoch ends when: v2
serves all consumers; v1's planes, bridges, and flags are DELETED (not
disabled); each RC-invariant is impossible-by-construction or fail-loud in v2;
and the doctrine + reusable forms are packaged so the fleet wave can /frame
directly from them. "Unblocked" means: the next repo's reconstruction is a
template application, not a research project.

## Non-goals

- Hardening or extending v1 (P6).
- Incremental/strangler migration shapes (P4 supersedes).
- Serving stale numbers with confidence labels (P2 rejects).
- New guard layers where subtraction can remove the hazard class (P3).

## Open questions — expressly delegated to /architect (do not pre-answer)

Canonical artifact shape (consolidated vs per-section vs other) · freshness
model (content-derived; hash vs watermark vs hybrid) · storage layout & key
schema · atomic rebuild mechanism (stage-validate-swap or better) · consumer
contracts (CLI, service, MCP/delegated-fleet) · observability design that
cannot lie (RC-F). Each requires exhaustive option enumeration + adversarial
challenge per P8; each one-way door among them returns as a decision packet.

## One-way door register (initial)

1. V1 data deletion (legacy + v1 planes) — operator.
2. V2 key/schema shape commitment (post-cutover it is load-bearing) — operator packet.
3. Cross-service consumer contract changes — operator packet.
4. Cross-repo terraform applies (warmer topology, alarms) — operator.

## Immediate next moves

1. `/frame substrate-v2-epoch` consuming this charter → workstream decomposition.
2. Dispatch /architect ultracode: substrate-v2 TDD from the six RC-invariants + P-set.
3. PR #276 (v1 honesty guards) — lands on green via armed auto-merge; it is the
   P6 floor, not the start of v1 investment.
