---
type: handoff
artifact_id: HANDOFF-sre-to-10x-dev-cw4-emission-wiring-2026-04-22
schema_version: "1.0"
source_rite: sre
target_rite: 10x-dev
handoff_type: execution
priority: low
blocking: false
initiative: autom8y-core-aliaschoices-platformization-phase-a
created_at: "2026-04-22T11:45Z"
status: proposed
source_artifacts:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-PR131-POSTMERGE-REREVIEW-2026-04-22.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-F1A-cw4-alarm-emission-audit-2026-04-22.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-F1B-cw4-runbook-authored-2026-04-22.md
evidence_grade: strong
items:
  - id: CW4-EMIT-001
    summary: Wire auth.oauth.scope.cardinality emission at token-exchange callsite. Declared-but-unused in token_exchange_cw_metrics.py; alarm is gated on this work.
    priority: low
    acceptance_criteria:
      - "emit_issuance_with_scope() is called from the /oauth/token success path exactly once per successful token issuance, passing the scope string set observed. Callsite MUST be in services/auth/autom8y_auth_server/routers/oauth.py (or the token-exchange service layer it delegates to)."
      - "Metric-name reconciliation: the commented alarm at terraform/services/auth/observability/cloudwatch-alarms.tf:410 binds to ScopeCardinalityObserved; the emitter constant METRIC_OAUTH_SCOPE_CARDINALITY is auth.oauth.scope.cardinality. PR MUST document which wins: (a) add ScopeCardinalityObserved as alias in token_exchange_cw_metrics.py and emit under that name, OR (b) rewire alarm to auth.oauth.scope.cardinality. SRE preference is (b) for consistency with the CW-1..CW-3 namespace, but either is acceptable if documented."
      - "Test coverage added in tests/test_oauth_server_track.py asserting emission fires on success path. Reuse existing overflow test fixtures (_reset_scope_cardinality_for_tests at token_exchange_cw_metrics.py:145)."
      - "Threshold shape decision recorded in PR: either (A) static >50 (matches SCOPE_CARDINALITY_CAP=50 in-code), or (B) rewire to log-metric-filter on token_exchange_cw_metrics_scope_cardinality_overflow as binary overflow signal. Runbook auth-oauth-scope-cardinality.md already accommodates both without edit."
      - "After merge of this PR, SRE re-activates CW-4 alarm via single-hunk uncomment at cloudwatch-alarms.tf:405-433 and removes the '# (commented)' rationale block. No further Terraform design needed."
    notes: |
      F1 residual on PR #131 ship-gate G9. Priority LOW because the alarm being commented-out costs nothing (no false positives, no gaps beyond what the four active alarms already cover). But this is the one ceremonial step from G9 CONDITIONAL-PASS-QUALIFIED → PASS.

      The gap is that emission-helper scaffolding landed in PR #131 (overflow guard, cap constant, reset-for-tests, metric-name constant) but the emitter was never called from the token-exchange success path. F1a observability-engineer audit graded this BLOCKING-for-activation but NON-REGRESSIVE for the four alarm-runbook pairs that DID ship wired.

      Secondary finding from F1a: emit_token_exchange_outcome also appears declared-but-never-called. Scope check welcome during this PR — either in-scope (wire both) or formally out-of-scope (document separate follow-up). Do not silently expand.
    dependencies: []
    estimated_effort: "2-4 hours (single callsite wiring + test + alarm-rewire decision doc)"
---

# HANDOFF — SRE → 10x-dev (CW-4 Emission Wiring)

## 1. Context

PR #131 (admin-CLI OAuth Wave 1) merged at `cedb9012` on 2026-04-22. Ship-gate G9 closed CONDITIONAL-PASS because 4 of 5 alarm-runbook pairs shipped (CW-1 replay, CW-2a PKCE, CW-2b device, CW-3 redirect-uri). The 5th — CW-4 `auth.oauth.scope.cardinality` — had the alarm commented-out and the runbook deferred.

Post-merge re-review (see source artifact `SRE-PR131-POSTMERGE-REREVIEW-2026-04-22.md`) closed the runbook side (`auth-oauth-scope-cardinality.md` authored). The alarm side depends on emission wiring, which is declared-but-never-called — a 10x-dev engineering task.

## 2. What you will do

Wire the emitter. See `items[0].acceptance_criteria` for the full contract.

## 3. What you will NOT do

- Do NOT edit `terraform/services/auth/observability/cloudwatch-alarms.tf` — SRE owns that re-activation after your PR merges.
- Do NOT edit `services/auth/runbooks/auth-oauth-scope-cardinality.md` — runbook is authored and accommodates both threshold shapes.
- Do NOT expand scope silently. If you discover that `emit_token_exchange_outcome` is also unwired, either include it in this PR (with explicit note) or surface as separate follow-up handoff.

## 4. Done criteria

- PR merged to autom8y/main with emission wired.
- SRE rite activates CW-4 alarm within one business day of your merge (single-hunk uncomment).
- G9 moves CONDITIONAL-PASS-QUALIFIED → PASS; Phase A ship-gate fully closed.

## 5. Priority posture

LOW. Non-blocking for Phase A retirement-baseline (already signed). This is the ceremonial closure, not a correctness gate.

---

*Emitted 2026-04-22T11:45Z by SRE rite. Routing: please accept or reject within 5 business days per handoff SLA.*
