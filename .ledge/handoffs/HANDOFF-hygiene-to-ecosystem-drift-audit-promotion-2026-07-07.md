---
type: handoff
status: proposed  # authored + ready to dispatch to ecosystem Potnia; not yet executed cross-repo
handoff_type: execution
source_rite: hygiene
target_rite: ecosystem
target_agent: potnia (ecosystem rite — the DEFER's named escalation_target)
initiative: asana-realization-tail-convergence
workstream: A — Ledger-Truth Convergence
sprint: A3-promote
authored_at: 2026-07-07
authored_by: main-thread (session-20260707-143336-92643bbd) at OPERATOR DIRECTION
discharges_defer: drift-audit-discipline-fleet-promotion  # FIRED 2026-05-29; deadline 2026-09-29; SCAR-P6-001 Pattern-6-Recurrence
self_assessment_cap: MODERATE  # this checkout authors the envelope; the cross-repo promotion + its attestation are ecosystem-Potnia's / eunomia's (PT-E)
routing: satellite-primitive-promotion (repo-local → knossos shared-mena)
---

# HANDOFF — hygiene → ecosystem: promote the register-drift discipline to knossos (fleet-wide)

## Why this handoff exists

The realization-tail-convergence crusade proved, on its own paperwork, that hand-maintained
knowledge registers silently drift — five registers asserted the opposite of the code (A1),
and the guard-building sprint itself reproduced the disease three times (A2). A1 reconciled
the drift; A2 built a **biting, two-sided register-drift guard** so the drift becomes a CI
failure in *this* repo. But the discipline is **fleet-generic** — every satellite carries the
same register-drift risk — and its promotion to knossos has a **FIRED, overdue** DEFER. This
handoff discharges that DEFER by routing the cross-repo promotion to its named owner.

This is a **frame-and-dispatch** leg: the envelope is authored in `autom8y-asana`; the
promotion is **executed cross-repo** (knossos) by ecosystem Potnia via
`satellite-primitive-promotion`. Nothing is built in this checkout.

## The FIRED DEFER being discharged (do not edit its entry — append-only)

`.know/defer-watch.yaml` → `drift-audit-discipline-fleet-promotion`
- `filed_at: 2026-04-29` · `filed_by: janitor` · `parent_initiative: actual-blockers-2026-04-29`
- `watch_trigger: 2026-05-29` — **FIRED** (39 days overdue at authoring) · `deadline: 2026-09-29`
- `escalation_target: ecosystem rite Potnia` (this handoff's target)
- `retry_action`: "invoke satellite-primitive-promotion to lift drift-audit-discipline skill
  from autom8y-asana repo-local to knossos canonical shared-mena altitude; verify no content
  divergence has accrued during promotion window"
- evidence anchors: `SCAR-P6-001` (Pattern-6-Recurrence, `.know/scar-tissue.md`);
  `VERDICT-eunomia-final-adjudication-2026-04-29.md §5`; `PLAN-actual-blockers-2026-04-29.md §3.3`

## Items (execution — each carries acceptance_criteria + Gate-C per-item receipts)

### Item 1 — Promote the `drift-audit-discipline` SKILL to knossos shared-mena
- **artifact (repo-local, verified present)**: `.claude/skills/drift-audit-discipline/SKILL.md` (6.9k)
- **target**: `knossos/rites/shared/mena/drift-audit-discipline/`
- **mechanism**: `satellite-primitive-promotion` (cross-repo; branch knossos, sync-order, regression-verify, cleanup per that skill)
- **acceptance_criteria**:
  1. Skill lands at knossos shared-mena altitude, fleet-resolvable.
  2. **Content-divergence check** (the DEFER's explicit ask): diff the promoted copy against
     `autom8y-asana` repo-local at promotion time; reconcile any drift accrued since 2026-04-29.
  3. Repo-local copy either retired-in-favor-of-shared or explicitly retained with a pointer (no silent fork).

### Item 2 — Promote the A2 register-drift-guard PATTERN (the concrete realization)
- **artifact (PR #206, tip `973c5427`, CI-green/CLEAN, awaiting operator merge)**:
  `tests/unit/knowledge/register_drift_checks.py` (detectors + declarative `INVARIANT_TABLE`),
  `tests/unit/knowledge/test_register_drift_guard.py` (`@pytest.mark.scar` two-sided keystone +
  `test_every_invariant_row_is_two_sided` meta-vacuity gate), `tests/unit/knowledge/fixtures/drift/`.
- **rationale**: the SKILL is the doctrine; this keystone is the *biting mechanism*. Promoting
  the pattern (parametrized INVARIANT_TABLE + two-sided fixture doctrine + meta-vacuity test)
  lets each satellite arm the same guard by appending register rows — the discipline becomes
  executable fleet-wide, not just documented.
- **acceptance_criteria**:
  1. The pattern is templated for satellite reuse (per-repo register paths + landing-SHA corroboration).
  2. Two-sided-teeth + non-vacuity requirements travel with it (a promoted vacuous guard is rejected).
- **dependency**: PT-A2 leg (b) discharges on PR #206 merge (operator lever); this item's
  promotion fires **after** #206 lands so the pattern promoted is the merged, CI-proven one.

## Carried conditions / discipline

- **Gate-C receipt-grammar** (telos-integrity §3): every "promoted / landed / materialized"
  claim in the execution report carries a per-item `{path}:{line}` anchor OR a knossos-side
  VERDICT citation OR an explicit `[UNATTESTED — DEFER]` tag. No wave-level tokens.
- **DEFER discharge is recorded, not deleted**: on completion, append a
  `discharged-via-handoff` note referencing this envelope; the FIRED entry stays (append-only).
- **UV-P**: `satellite-primitive-promotion` was not located under `~/Code/knossos` from this
  checkout at authoring (skill-registry resolvable, path unconfirmed) — ecosystem Potnia
  confirms the promotion mechanism live before execution.
- Self-assessment caps **MODERATE**; verified_realized for the crusade remains eunomia's at PT-E.

## Non-scope

NOT built in this checkout. NO knossos edits from here. NO modification of the FIRED DEFER
entry's content. The operator dispatches this to ecosystem Potnia (`ari sync --rite=ecosystem`
+ restart, then route `satellite-primitive-promotion`).
