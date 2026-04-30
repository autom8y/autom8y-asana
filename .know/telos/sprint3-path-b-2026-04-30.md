---
artifact_id: TELOS-sprint3-path-b-2026-04-30
schema_version: "1.0"
type: telos
artifact_type: telos-declaration
slug: sprint3-path-b-2026-04-30
rite: sre
session_id: session-20260430-203219-c8665239
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3
authored_by: main-thread (per charter §1.4 HARD prereq)
authored_at: 2026-04-30
evidence_grade: MODERATE
self_grade_ceiling_rationale: "Self-authoring telos at engagement inception; STRONG promotion requires rite-disjoint attester at verification deadline"
status: proposed
---

# TELOS DECLARATION — Sprint-3 Path B + SRE-005

## §1 Inception Anchor

```yaml
inception_anchor:
  framed_at: "2026-04-30"
  framed_by_session: session-20260430-203219-c8665239
  framed_by_charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3
  user_invocation_anchor: "2026-04-30T18:31Z"
  user_invocation_quote: "--to=sre for @potnia (agent) to orchestrate our /sprint to remediate: 1) SRE-005 M-16 Dockerfile, 2) Path B cross-repo runner (you have full authority and access to the full file tree)"
  authority_shift: "user authority grant LIFTS Sprint-2 §7.1 cross-repo gate"
```

## §2 Shipped Definition

```yaml
shipped_definition:
  user_visible_surface:
    - "CI shard p50 latency reduction observable in autom8y-asana CI run-time dashboards (gh run view --json jobs); CONDITIONAL on org-runner-tier enablement"
    - "Dockerfile lint enforcement observable in PR CI status checks via dockerfile-lint.yml workflow"
    - "Reusable workflow at autom8y/autom8y-workflows exposes runner_size parameter (back-compat: sentinel default 'standard' preserves status quo); test_workers DROPPED per A1 drift-finding (test_parallel + test_dist_strategy already parameterize parallel-execution)"
  shipped_artifacts:
    - .hadolint.yaml (commit 288a52bc)
    - .github/workflows/dockerfile-lint.yml (commit 288a52bc)
    - .ledge/decisions/ADR-013-sre-005-hadolint-2026-04-30.md (commit 288a52bc)
    - .pre-commit-config.yaml hadolint hook v2.14.0 refresh (commit 288a52bc)
    - autom8y/autom8y-workflows cross-repo PR #14 (commit 3a35dbc3; runner_size scaffold only)
    - .ledge/decisions/ADR-012-path-b-runner-size-scaffold-2026-04-30.md (Path-B re-adjudication)
  shipped_at: 2026-04-30 (B2 + scaffold PR)
  shipped_session: session-20260430-203219-c8665239
```

## §3 Verified-Realized Definition

```yaml
verified_realized_definition:
  verification_method:
    - telemetry: "post-merge CI shard p50 measurement (5-run sample on main); slowest-shard p50 vs BASELINE 447s pre-engagement"
    - cross_stream_corroboration: "eunomia rite re-discharge of VERDICT-test-perf §9.2; supplement §9.7 amendment authored by observability-engineer"
    - lint_enforcement_attestation: "dockerfile-lint.yml workflow status check fires on Dockerfile-touching PRs; failures gate merge"
  verification_deadline: "2026-05-14 (Sprint-3 close + 14d for measurement window stabilization)"
  rite_disjoint_attester: eunomia (continuing from Sprint-2 supplement §9.6 PASS-WITH-FLAGS-PRESERVED → Sprint-3 §9.7 amendment)
  promotion_threshold:
    pass_clean_promotion: ">=20% CI shard p50 reduction (post <=358s) → parent VERDICT-test-perf overall_verdict mutates PASS-WITH-FLAGS → PASS-CLEAN"
    pass_with_flags_preserved: "<20% reduction → supplement §9.7 documents partial discharge; promotion path remains open via runner-tier-enablement-pending carry-forward"
    pass_with_flags_amplified: "regression direction (post >447s) → flag amplification; route to incident-commander"
  conditional_realization:
    note: "Path B PR (scaffold-only per OQ-1 NEGATIVE) does NOT immediately move CI wallclock. Wallclock-delta verification is conditional on org-runner-tier enablement (autom8y/actions/hosted-runners shows total_count=0 at 2026-04-30T18:31Z). Realization gate: org admin authorizes ubuntu-latest-large; satellites opt-in via runner_size: 'large' input."
    realization_carry_forward: "runner-tier-enablement-pending → next /sre engagement when enablement lands"
```

## §4 Refusal Posture

```yaml
refusal_posture:
  no_soft_close: |
    Sprint-3 close MUST adjudicate one of three terminal states (PASS-CLEAN-PROMOTION, PASS-WITH-FLAGS-PRESERVED, PASS-WITH-FLAGS-AMPLIFIED) per supplement §9.7 amendment. Cannot close at PASS-CLEAN if wallclock measurement isn't possible (org enablement pending). Honest close at PASS-WITH-FLAGS-PRESERVED with carry-forward is the principled state.
  no_theatrical_canary:
    note: "A3 canary deferred under Path (c) scaffold-only adjudication. Reason: scaffold-only PR preserves runner_size: 'standard' default; behavior unchanged for satellites; canary would be theatrical (no behavior to validate). Canary fires when an actual satellite opts in (post-enablement)."
  fabricated_verification_forbidden: "If post-merge wallclock measurement cannot be obtained (org enablement gate persists past 2026-05-14 deadline), supplement §9.7 documents the structural blocker; verification status remains 'pending-org-enablement'. Cannot fabricate ≥20% delta to claim PASS-CLEAN."
```

## §5 Verification Anchor Discharge Protocol

```yaml
discharge_protocol:
  step_1: "observability-engineer dispatches at Sprint-3 close (after B2 + A2 land)"
  step_2: "Capture 5 successful main-branch CI runs post Sprint-3 PR merge"
  step_3: "Compare slowest-shard p50 against BASELINE §4 (447s pre-engagement) and Sprint-2 supplement §8 measurement (514s)"
  step_4: "Apply promotion threshold (§3 above)"
  step_5: "Author supplement §9.7 amendment (rite-disjoint from /sre; eunomia attester)"
  step_6: "If PASS-CLEAN-PROMOTION: mutate parent VERDICT-test-perf frontmatter overall_verdict"
  step_7: "If PASS-WITH-FLAGS-PRESERVED: document carry-forward (runner-tier-enablement-pending); next engagement re-fires §3 verification when enablement lands"
```

## §6 Source Manifest

| Role | Artifact | Path |
|---|---|---|
| Charter (governing) | Sprint-3 inaugural | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3.md` |
| Parent supplement (discharge target) | §9.7 amendment | `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` |
| Parent VERDICT (promotion target if PASS-CLEAN) | overall_verdict mutation | `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` |
| BASELINE (anchor) | 447s slowest-shard p50 | `.ledge/reviews/BASELINE-test-perf-2026-04-29.md` |
| OQ-1 evidence | gh API negative | gh api /orgs/autom8y/actions/hosted-runners → total_count: 0 (2026-04-30T18:31Z) |
| THIS artifact | telos declaration | `.know/telos/sprint3-path-b-2026-04-30.md` |
