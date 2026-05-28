---
type: handoff
artifact_id: HANDOFF-sre-to-sre-crossrepo-2026-05-27
schema_version: "1.0"
source_rite: sre
target_rite: sre   # same rite, different repo (cross-repo intra-rite). platform-engineer is the sre executor agent, not a rite.
priority: critical
blocking: true
handoff_type: execution
initiative: freshness-verification-recency
created_at: 2026-05-27T20:10:00Z
status: draft
handoff_status: pending
target_repo: /Users/tomtenuta/Code/a8/repos/autom8y   # CROSS-REPO — different from the procession's home repo (autom8y-asana)
target_file: terraform/services/asana/main.tf
source_artifacts:
  - .ledge/spikes/HANDOFF-10x-dev-to-sre-2026-05-27.md
  - .ledge/decisions/ADR-006-freshness-equals-verification-recency.md
  - .ledge/reviews/QA-freshness-verification-recency-gate.md
items:
  - id: SRE-001   # implements SRE-001 from HANDOFF-10x-dev-to-sre (re-scoped: log-metric-filter, not metric alarm)
    summary: >
      Add a CloudWatch Logs metric filter + alarm in the asana service Terraform
      to page on the ERROR tier of `section_name_contract_violation` ONLY, NOT the
      first-deploy re-seed-window WARN tier. This is SRE-001, re-scoped: the signal
      is a structured LOG EVENT, not a CloudWatch metric, so it needs a
      log_metric_filter (not a bare metric alarm).
    priority: critical
    acceptance_criteria:
      - "A `aws_cloudwatch_log_metric_filter` on log group `/aws/lambda/autom8-asana-cache-warmer` (verified live: exists, zero existing metric filters) with a JSON pattern isolating the ERROR tier."
      - "Pattern semantics (locked from `progressive.py:500-522`): match event `section_name_contract_violation` AND `reseed_window = false` AND log level `error`. The WARN tier (`reseed_window=true`, first-deploy expected on ~10/11 fleet projects via `logger.warning` at progressive.py:514-522) MUST be structurally excluded so it cannot increment the metric."
      - "metric_transformation → name `SectionNameContractViolationError`, namespace `Autom8y/FreshnessProbe`, value 1, default_value 0."
      - "A `aws_cloudwatch_metric_alarm` on that metric, modeled on the existing `cache_warmer_failure_offer` (main.tf:417-444): GreaterThanOrEqualToThreshold, threshold 1, Sum, period 3600, evaluation_periods 1, `treat_missing_data = \"notBreaching\"` (the pre-emit / INSUFFICIENT_DATA-safe posture — metric does not emit until merge+deploy)."
      - "`actions_enabled = false` initially (matches the ALERT-1..ALERT-4 staging convention at main.tf:364-365 — ship suppressed, flip to true after the re-seed window is confirmed clear, ties to SRE-002)."
      - "`alarm_actions`/`ok_actions` → the platform alerts SNS topic (the `platform_alerts_topic_arn` shared remote-state output used by the existing alarms)."
      - "`terraform plan` is clean (only the two new resources added); `terraform apply` succeeds."
      - "OPEN VERIFICATION (do post-merge, before flipping actions_enabled): confirm the exact JSON key names against ONE real emitted warm log line — `autom8y-log` JSON may render the event under `event` vs `message`, level as `error` vs `ERROR`. Adjust the `$.` path keys to match. The SEMANTIC filter (event + reseed_window=false) is locked; only the field-name rendering needs confirmation."
    notes: |
      Why a log metric filter, not a metric alarm: `grep section_name_contract_violation src/`
      shows zero put_metric_data / MetricName emission — it's log-only
      (progressive.py logger.error/.warning). This differs from the existing
      `Autom8y/FreshnessProbe` MaxParquetAgeSeconds alarms (those ARE metrics via
      cloudwatch_emit.py). Do not model PLAT-001 on the metric-emit path.

      Place alongside the existing alarm block (main.tf:344-470). Warmer Lambda:
      module.cache_warmer (main.tf:255-289), function autom8-asana-cache-warmer.
      If the platform module (service-lambda-scheduled?ref=v1.0.2) does not expose
      the log group as an addressable output, reference the literal name
      `/aws/lambda/autom8-asana-cache-warmer`.
    estimated_effort: 1-2h (TF authoring + plan/apply + PR)
    dependencies: []
provenance:
  - source: "observability-engineer determination 2026-05-27 (describe-alarms + TF resource cross-check)"
    type: artifact
    grade: strong
  - source: "autom8y/terraform/services/asana/main.tf:344-470 (existing alarm block, read at determination time)"
    type: code
    grade: strong
  - source: "src/autom8_asana/dataframes/builders/progressive.py:489-535 (emit site, branch feat/freshness-verification-recency)"
    type: code
    grade: strong
evidence_grade: strong
tradeoff_points:
  - attribute: alarm-precision-vs-completeness
    tradeoff: ERROR-tier-only filter (reseed_window=false) excludes the WARN tier entirely.
    rationale: >
      The WARN tier is expected first-deploy behavior (~10/11 fleet projects),
      self-clearing on warm cadence. Alarming on it would page on expected state.
      The structural exclusion in the metric filter pattern (not just the alarm
      threshold) is the load-bearing guarantee. [ADR-006 §Decision-7a]
---

# HANDOFF — SRE → SRE (cross-repo: autom8y infra): SRE-001 as a log-metric-filter alarm

## Why this crosses to a different REPO (same rite)

CloudWatch alarms for this service are Terraform-managed in the **`autom8y`** infra
repo (`terraform/services/asana/main.tf`), not in `autom8y-asana`. Per Pythia
routing ruling (2026-05-27): rite ⊥ repo — the rite stays **sre** (the `autom8y`
repo is already `ACTIVE_RITE=sre`, and platform-engineer is the sre rite's
implementation agent, NOT a rite). Cross-repo, intra-rite handoff: execute via a
single `/task` in the target repo, routed by sre potnia → platform-engineer. One
CC-restart (repo-root change only; no rite switch).

## Merge gating (unchanged)

**PR #67 (autom8y-asana) merge remains GATED on SRE-001 (this item).** Sequence:
SRE-001 (TF filter+alarm, `actions_enabled=false`) → merge PR #67 → deploy →
first scheduled warm → SRE-002 confirms re-seed window clears + `verification_age`
computes → flip `actions_enabled=true`.

## The one open verification

The JSON field-name rendering (`event` vs `message`, `error` vs `ERROR`) must be
confirmed against a real warm log line. This can only happen post-deploy (the new
emit code isn't live yet). So: ship the filter with the best-known field names,
keep `actions_enabled=false`, sample a real log line after first warm, correct the
pattern if needed, THEN enable actions. This is the safe ordering.

## Response

On completion append `## Response (sre)`: TF PR link, alarm ARN, plan/apply
confirmation, and the field-name verification result. Set `handoff_status: completed`.

## Response (sre) — authored, awaiting prod-env approval

- **TF authored + PR opened:** autom8y **PR #282** (https://github.com/autom8y/autom8y/pull/282), branch `feat/freshness-section-name-contract-alarm`, commit `4756198d`. Two resources: `aws_cloudwatch_log_metric_filter` (ERROR-tier-only pattern `$.event=section_name_contract_violation && $.reseed_window IS FALSE && $.level=error`) + `aws_cloudwatch_metric_alarm` (`treat_missing_data=notBreaching`, `actions_enabled=false`, alerts→`platform_alerts_topic_arn`). Log group via `module.cache_warmer.log_group_name` (v1.0.2 module exposes it).
- **Validation:** `terraform validate` + `fmt -check` clean; pre-commit `terraform_fmt` passed; NO local plan/apply (GitOps). Authored cross-repo from the autom8y-asana session via an isolated worktree.
- **Blocked at:** GitHub `production`-environment protection gate — `Plan (asana, production)` is `WAITING` on **human approval** in the GH UI (cannot be cleared by the agent). `mergeState: BLOCKED` until the plan completes. All other checks green.
- **Open verification (post-deploy):** field-name rendering (`$.event` vs `$.message`, level case, `extra` nesting) confirmed against a real warm log line before flipping `actions_enabled=true`. Guarded meanwhile by the suppression.

`handoff_status: in_progress` (TF delivered; awaiting human prod-env approval → merge → apply).
