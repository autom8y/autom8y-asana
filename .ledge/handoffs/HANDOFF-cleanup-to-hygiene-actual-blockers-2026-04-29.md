---
artifact_id: HANDOFF-cleanup-to-hygiene-2026-04-29
schema_version: "1.0"
type: handoff
source_rite: cleanup
target_rite: hygiene
handoff_type: execution
priority: medium
blocking: false
initiative: "Principled Actual-Blocker Remediation"
created_at: "2026-04-29T12:30:00Z"
status: completed
authority: "User-granted: '/cross-rite-handoff --to=hygiene for /task to principly remediate actual blockers only' (2026-04-29)"
posture: "principled minimum — only items that demonstrably block something get scoped; everything else properly deferred elsewhere"
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
upstream_artifacts:
  - .ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md
  - .ledge/reviews/CASE-comprehensive-cleanliness-2026-04-29.md
items:
  - id: HYG-001
    summary: "Triage 3 stale CI gates failing on every green PR (alarm-fatigue blocker for all-green merge semantics)"
    priority: high
    acceptance_criteria:
      - "Per-gate diagnosis of root cause (file:line + workflow-run URL evidence)"
      - "Per-gate disposition: FIX-TO-GREEN | DELETE-AS-OBSOLETE | ACCEPT-WITH-EXPLICIT-FLAG (with ADR rationale)"
      - "If FIX-TO-GREEN: gate passes on a fresh PR after remediation"
      - "If DELETE: workflow file change merged; no functional regression"
      - "If ACCEPT-WITH-FLAG: ADR authored documenting why the gate is structurally non-fixable in current state; defer-watch entry filed for future fix"
      - "All 3 gates have a definite disposition (no 'TBD' at task close)"
    notes: |
      The 3 gates: Lint & Type Check, Semantic Score Gate, Spectral Fleet Validation.
      All 3 failed on PR #39 merge commit `45a9e875` AND PR #40 merge commit `848525b9` —
      pre-existing fleet debt. Semantic Score Gate fails on stale baseline (M-07 constraint
      coverage floor + M-05 type strictness regression of -0.0046, invariant under
      docs-only changes). Each gate fails on EVERY PR currently, eroding green-CI signal
      trust across the fleet. Blocker classification: alarm-fatigue / signal-erosion —
      the fleet has implicitly accepted red-on-green, but that's a debt position not a
      design choice.

      Actual-blocker bar met because: gate failures are the FIRST thing reviewers see
      on a PR, prompting "is this safe to merge?" cognitive overhead on every merge.
      Three weeks of accumulated alarm fatigue erode the team's ability to trust CI
      to surface real failures. Remediation restores signal/noise integrity.

      Hygiene rite should triage with code-smeller (diagnose root cause per gate) →
      architect-enforcer (per-gate disposition recommendation; option-enumeration
      across FIX/DELETE/ACCEPT) → janitor (execute) → audit-lead (sign-off).

      Estimated effort: 1-2 days if all 3 are FIX-TO-GREEN; <1 day if mostly DELETE/ACCEPT.

  - id: HYG-002
    summary: "Codify Pattern 6 synthesis-altitude clause in drift-audit-discipline skill (process-blocker for next plan-authoring)"
    priority: high
    acceptance_criteria:
      - "drift-audit-discipline skill (locate via grep; likely at $KNOSSOS_HOME/skills/ or .claude/skills/) updated with synthesis-altitude clause"
      - "Synthesis-altitude clause text: 're-run drift-audit at any altitude where mixed-resolution upstream substrates are being consolidated. Specifically: any plan-authoring step that consumes [UNATTESTED] inventory framing MUST verify ground truth against origin/main before propagating the framing forward.'"
      - "VERDICT §5 Pattern-6-Recurrence Meta-Finding cross-referenced as the originating evidence (file:line anchor)"
      - "CASE §8 Q-1 promoted from 'NOW URGENT' aspiration to actual codified clause"
      - "Cross-link from .know/scar-tissue.md SCAR-P6-001 to the skill update (so future grep finds the bidirectional reference)"
    notes: |
      Pattern 6 (audit-time stale-checkout artifacts) was originally codified at SCAN-altitude
      in CASE-comprehensive-cleanliness-2026-04-29.md. Eunomia VERDICT §5 surfaced that the
      pattern RECURS at PLAN-AUTHORING altitude (consolidation-planner produced inverted-drift
      claim about test_source_stub.py absent on autom8y origin/main when actually present
      at blob bf4f74180e15f07a698538afa14f6f82d47bf641 PR #174 commit f2dfc1c3).

      The mechanism: planner consumed earlier [UNATTESTED] inventory framing and propagated
      it forward without re-invoking drift-audit-discipline at synthesis altitude. SWEEP §6
      had subsequently RESOLVED the question with the correct ground truth, but planner
      didn't re-read SWEEP — only read the upstream INVENTORY's stale framing.

      Actual-blocker bar met because: until codified, the next plan-authoring step at any
      future eunomia/review engagement will repeat the same failure mode. The eunomia VERDICT
      flagged FLAG-CP02-DRIFT specifically because of this — the carry-forward CP-02
      execution requires a human to manually re-run drift-audit (unforced), or else commit
      lands on stale branch. Codification removes the manual-vigilance burden.

      Hygiene rite scope: this is a knossos-skill update, not a code change. /hygiene's
      authority covers documentation/discipline-codification work. If the drift-audit-discipline
      skill is at $KNOSSOS_HOME (outside this repo), this may need to escalate via
      satellite-primitive-promotion protocol — janitor should detect that and surface to
      hygiene-rite Potnia for routing.

      Estimated effort: <1 day if skill is repo-local; ~1 day if requires satellite-primitive-promotion.
---

# HANDOFF: cleanup → hygiene — Principled Actual-Blocker Remediation

## Why this handoff exists

User invocation: **"/cross-rite-handoff --to=hygiene for /task to principly remediate actual blockers only"** (2026-04-29).

The "actual blockers only" framing was applied as a sharp filter against the full carry-forward register from today's cascade. Of ~13 carry-forward items, only **2 meet the bar**:

1. **HYG-001** — 3 stale CI gates (alarm-fatigue blocker; fail on every PR; erode signal trust)
2. **HYG-002** — Pattern 6 codification at drift-audit-discipline skill (process blocker; uncodified mechanism will recur at next plan-authoring)

Everything else (DEFER-WATCH entries, CP-01/CP-02 test additions, M-16 Dockerfile enforcement, Pattern 2 tool READMEs, MockTask proliferation, M-08/M-09 status transitions) is properly deferred via defer-watch registry, routed to non-hygiene rites, or is shelf-tidying that doesn't block anything.

## Why these two specifically

### HYG-001 actual-blocker predicate

- **Failing on every PR**: PR #39 + PR #40 both merged with these 3 gates RED. Pattern is consistent across cascade.
- **Blocks all-green merge semantics**: every PR reviewer must override gate failures, eroding "is this safe?" cognitive integrity.
- **Invariant under docs-only changes**: gates fail even when no code changed (verified on PR #40 which was docs-heavy).
- **Fleet has implicitly accepted**: this is a debt position, not a design choice.
- **Remediation restores signal**: fixing/deleting/accepting-with-flag returns CI to actionable state.

### HYG-002 actual-blocker predicate

- **Recurrence-prevention**: Pattern 6 surfaced at SCAN altitude (CASE), then RECURRED at PLAN altitude (eunomia VERDICT §5). Without codification, will recur at next altitude.
- **Carries forward to CP-02 execution**: FLAG-CP02-DRIFT in VERDICT §6.2 explicitly requires manual drift-audit re-run because skill doesn't enforce it. Manual vigilance is fragile.
- **Process-blocker for next eunomia/review engagement**: any future plan-authoring step that consumes mixed-resolution upstream substrates will repeat the failure mode.

## Authority boundary

hygiene rite (potnia + code-smeller + architect-enforcer + janitor + audit-lead) MAY:
- Read source across autom8y/, autom8y-asana/, a8/, knossos/ skill directories.
- Modify CI workflow files (`.github/workflows/`) for HYG-001 disposition execution.
- Modify knossos skill files for HYG-002 codification.
- Author ADRs for any ACCEPT-WITH-EXPLICIT-FLAG dispositions.
- Open PRs for code/skill changes (separate PRs per HYG-NNN preferred for atomic revertability).
- File defer-watch entries if remediation requires multi-stage work.

hygiene rite MAY NOT:
- Touch other rites' canonical artifacts (.know/ updates outside scope; theoros owns those).
- Modify the eunomia VERDICT or CASE file (they're status:accepted; cite-only).
- Author cross-rite handoffs (recommendation-only; surface back to user).

## Disciplines to apply

- `option-enumeration-discipline` — for HYG-001 per-gate disposition (FIX/DELETE/ACCEPT must be enumerated, not just chosen)
- `structural-verification-receipt` — every disposition cites file:line + workflow-run URL evidence
- `authoritative-source-integrity` — every codification cites prior authority (VERDICT, CASE, originating issue)
- `defer-watch-manifest` — if any item gets ACCEPT-WITH-FLAG, file proper defer-watch entry
- `satellite-primitive-promotion` — if HYG-002 requires updating a knossos-altitude skill outside this repo
- `conventions` skill — git workflow standards for any PRs opened

## Required deliverables

1. **HYG-001 deliverables**:
   - Per-gate diagnostic report (file:line + workflow-run URL anchored)
   - Per-gate disposition decision (FIX/DELETE/ACCEPT)
   - Per-gate execution: workflow file edits OR ADR
   - Verification: post-remediation PR shows green-or-explicit-accept on all 3 gates

2. **HYG-002 deliverables**:
   - Updated drift-audit-discipline skill with synthesis-altitude clause
   - Cross-link from .know/scar-tissue.md SCAR-P6-001
   - Verification: grep finds bidirectional reference

## Acceptance criteria for this handoff

- [ ] HYG-001 + HYG-002 each receive a definite disposition (no "TBD" at task close)
- [ ] No scope creep — handoff items only; if other carry-forward items surface as "actually we should do this too", surface back to user rather than absorb
- [ ] Atomic commits/PRs per item (HYG-001 may decompose to 3 PRs if 3 separate disposition strategies emerge)
- [ ] User attestation gate before HYG-001 disposition execution if any of the 3 gates resolves to FIX-TO-GREEN with non-trivial code changes
- [ ] Audit-lead sign-off post-execution
