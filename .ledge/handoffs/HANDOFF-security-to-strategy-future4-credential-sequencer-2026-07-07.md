---
type: handoff
status: proposed
handoff_type: strategic_evaluation
source_rite: security
target_rite: strategy
initiative: asana-realization-tail-convergence
workstream: C — Credential-Topology Closure
sprint: C1
authored_at: 2026-07-07
authored_by: security rite (C1 credential-topology closure)
self_assessment_cap: MODERATE
---

# HANDOFF — security → strategy: Fleet Credential-Retirement Sequencer (named owner needed)

## The ask (leadership decision, NOT a build)

Stand up a **fleet credential-retirement SEQUENCER** — a single-owner ordering primitive
(SSOT) that gates credential migrations/retirements: *which key retires when, after which
consumers have cut over, with a rollback path*. Name its owner.

## Trigger — FIRED (verified 2026-07-07)

The fleet retires/migrates credentials per-leg with **no coordination authority**. Evidence:
bypass-holders grew **15 → 16** (migration-033's dedicated-exempt SA + uncoordinated
fossil-key retirements). The gap is structural, cross-service, and **monotonically worsening**.

## Why it matters (dual-mode risk)

- **Lockout / DoS**: retiring a key still depended-on by a live consumer breaks that consumer
  fleet-wide, with no rollback sequencer to recover cleanly.
- **Bypass-sprawl / EoP**: to avoid lockout, teams grant bypass-holder status instead of clean
  rotation → long-lived standing bypass credentials accumulate, each an EoP/Spoofing surface
  that outlives its justification.

## The concrete instance this blocks

**R-C1-T21** — the leaked ASANA_PAT (Track C, this session) "stays live until E" *precisely
because* no coordinated retirement path exists. Any obtained fossil/bypass credential inherits
an extended useful life from the fleet's structural reluctance to kill it. The sequencer is the
class-fix; the PAT rotation is the instance-fix.

## Evaluation criteria (for strategy)

1. Who owns the sequencer (a rite? a role? a service)?
2. What is the retirement ordering primitive (cutover-gated? dependency-graph-driven)?
3. How is the current bypass-holder set (16) audited-down to justified-only?
4. Interaction with the `single-writer-credential-lifecycle` throughline discipline.

Receipts + full threat context: `.ledge/reviews/RECEIPT-credential-topology-closure-c1-2026-07-07.md`.
