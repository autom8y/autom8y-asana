---
type: review
status: completed
artifact_id: SRE-F1B-cw4-runbook-authored-2026-04-22
schema_version: "1.0"
source_rite: sre
source_agent: incident-commander
task: F1b (CW-4 scope-cardinality runbook authorship)
parent_handoff: HANDOFF-RESPONSE-10x-dev-to-sre-pr131-merged-2026-04-22
initiative: autom8y-core-aliaschoices-platformization-phase-a-post-closure-pr131-remediation
ship_gate_context: G9 CONDITIONAL-PASS (5th alarm-runbook pair residual)
emitted_at: "2026-04-22T11:05Z"
evidence_grade: strong  # runbook is reproducible from git once committed
verdict: RUNBOOK-AUTHORED
---

# SRE F1b — CW-4 Scope-Cardinality Runbook Authored

## 1. Artifact

**Path**: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-oauth-scope-cardinality.md`
**CW number**: CW-9 (runbook range) pairing with CW-4 (Terraform alarm range) per Interpretation A in `terraform/services/auth/observability/cloudwatch-alarms.tf` lines 22-55.
**Length**: ~180 lines (target ≤250; pkce-attempts.md template is ~109, device-attempts ~101, redirect-uri ~117 — this runbook is slightly longer because the metric carries four distinct hypotheses vs three in the templates, and the overflow-counter dual-signal path requires explicit documentation).

## 2. H2 Table of Contents

| Section | Topic |
|---------|-------|
| (a) | Trigger Interpretation — what fires, what it means, what it IS NOT |
| (b) | Triage Steps (10 ordered, max-10 budget consumed) |
| (c) | Escalation Threshold (6-row condition/page/SLA matrix) |
| (d) | Fix Playbook — mitigation table, revert paths, "Do NOT do" subsection, post-incident |
| (e) | Security-rite handoff trigger |
| (f) | False-positive suppression + known FP patterns seed list |

Plus: metadata header (Pager SLA, Related ADRs, Metric emitted by) and References footer.

Structural parity with template runbooks (pkce-attempts CW-6, device-attempts CW-7, redirect-uri CW-8): header-block + (a)-(f) + References. All six sections present. All cross-runbook co-fire references wired (CW-2a/CW-2b/CW-3 in body; CW-6/CW-7/CW-8 in References).

## 3. Grounding Citations

| Claim | Source | Line |
|-------|--------|------|
| `SCOPE_CARDINALITY_CAP: Final[int] = 50` | `token_exchange_cw_metrics.py` | 113 |
| In-process overflow lock | `token_exchange_cw_metrics.py::_scope_cardinality_lock` | 116 |
| `_cardinality_capped_scope()` behaviour — set membership, non-resetting | `token_exchange_cw_metrics.py` | 120 |
| Overflow warning event `token_exchange_cw_metrics_scope_cardinality_overflow` | `token_exchange_cw_metrics.py` | 138 |
| `METRIC_OAUTH_SCOPE_CARDINALITY` constant | `token_exchange_cw_metrics.py` | 162 |
| ADR-0006 two-tower (scope-gating is `/internal/*`) | `services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md` | (whole doc) |
| ADR-0007 dual-field `scope`+`scopes` | `services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md` | (whole doc) |
| CW-4 alarm currently commented-out | `terraform/services/auth/observability/cloudwatch-alarms.tf` | 405-433 |
| F1a wiring decision (shape A gauge vs shape B log-metric-filter) | Same file, CW-4 comment block | 381-394 |

## 4. Judgment Calls

Three authorship decisions required judgment beyond the template:

1. **Threshold dual-interpretation**: the CW-4 Terraform comment suggests `> 50` as the default but flags it for 7d-baseline calibration like CW-2a/CW-2b. The runbook documents BOTH — the static `> 50` (derived from `SCOPE_CARDINALITY_CAP=50` in-code) and the post-baseline `(fleet_mean + 3*stddev)` — so the runbook stays valid across the F1a threshold-finalisation lifecycle without needing an edit when observability-engineer picks.
2. **Overflow-counter as paired signal**: the source file emits BOTH a cardinality observation AND an overflow warning. Triage step 1 and step 9 make the dual-signal explicit; §(d) "Overflow counter non-zero" row instructs responders to resolve root-cause BEFORE rotating tasks (rotation clears the in-process set but masks signal). This mitigates a foot-gun specific to this metric.
3. **SEV-1 path explicitly absent**: unlike CW-6/CW-7/CW-8 which carry SEV-1 escalation rows, scope-cardinality is a correctness/cost signal, not a user-visible outage. §(c) documents this explicitly ("this runbook does NOT carry a SEV-1 path") to prevent severity-inflation anti-pattern (incident-commander DK: "Severity Inflation for Attention"). A SEV-1 only fires via co-classification through another runbook (e.g., CW-3 at SEV-1 with scope-cardinality corroborating).

## 5. Scope Boundary Respected

- Runbook authored at canonical path matching the `runbook_reference` tag in the commented-out CW-4 Terraform resource (line 431). When observability-engineer activates CW-4 in F1a, the path resolves without Terraform edit.
- **Did NOT edit** `terraform/services/auth/observability/cloudwatch-alarms.tf` (F1a scope — observability-engineer parallel dispatch).
- **Did NOT edit** any source code in `token_exchange_cw_metrics.py` (grounded FROM it, not author it).

## 6. Verdict

**RUNBOOK-AUTHORED** — F1b complete. Artifact at canonical path, structurally parity-matched to sibling runbooks, grounded in named source file + ADR references, and bounded to runbook scope (no Terraform edit, no source-code edit).

Residual F1 from G9 CONDITIONAL-PASS is now 50% closed: runbook side (F1b) done; alarm-activation side (F1a) remains with observability-engineer.

## 7. Handoff

- **To observability-engineer (F1a)**: runbook exists at the canonical path; activate CW-4 in Terraform by uncommenting lines 405-433 and finalising the wiring-shape decision (shape A gauge emission in source, OR shape B `aws_cloudwatch_log_metric_filter` on the `token_exchange_cw_metrics_scope_cardinality_overflow` log event). Either shape resolves the alarm→runbook reference without additional edit to the runbook.
- **To fleet-potnia (parent dashboard)**: G9 residual F1 may be marked 1-of-2 closed pending F1a sign-off.
