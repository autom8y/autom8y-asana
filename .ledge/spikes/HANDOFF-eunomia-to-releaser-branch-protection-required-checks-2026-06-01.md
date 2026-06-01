---
artifact_id: HANDOFF-eunomia-to-releaser-branch-protection-required-checks-2026-06-01
schema_version: "1.0"
type: handoff
source_rite: eunomia
target_rite: releaser
handoff_type: assessment
priority: high
blocking: false
altitude: OPERATIONAL
initiative: ci-cd-test-ecosystem-rationalization-branch-protection-required-checks
created_at: "2026-06-01T16:00:00Z"
status: proposed
source_artifacts:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/pipeline-inventory-2026-06-01.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/test-inventory-2026-06-01.md
evidence_grade: strong
---

## Premise

The `main` branch protection ruleset on `autom8y-asana` does not list `ci / Lint & Type Check` among required status checks, has `enforce_admins=false`, and `required_approving_review_count=0`, allowing PRs to merge while CI is red — empirically confirmed by PR #69 merging at 2026-06-01T08:42:04Z despite a FAILURE check posted at 2026-06-01T08:31:53Z.

## Evidence

- `.sos/wip/eunomia/PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01.md` — change item B4 (branch-protection required-checks gap) with PT-alpha verdict citing PR #69 merged-while-red.
- `.sos/wip/eunomia/pipeline-inventory-2026-06-01.md` — workflow inventory enumerating `ci.yml` jobs including `Lint & Type Check`, demonstrating the check name exists and is publishable.
- `.sos/wip/eunomia/test-inventory-2026-06-01.md` — test-ecosystem inventory used to score upstream entropy; corroborates that B4 is a governance gap, not a missing-check gap.
- `.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md` — parent handoff that scoped B4 into the consolidation plan and routed it to eunomia.
- `gh api repos/autom8y/autom8y-asana/branches/main/protection` (queried 2026-06-01) — observed `required_status_checks.contexts` did not include `ci / Lint & Type Check`; `enforce_admins.enabled=false`; `required_pull_request_reviews.required_approving_review_count=0`.
- `gh api repos/autom8y/autom8y-asana/pulls/69` + check-runs query — merge_commit at 2026-06-01T08:42:04Z; `ci / Lint & Type Check` check-run conclusion=`failure` at 2026-06-01T08:31:53Z (10m 11s before merge).

## Recommended actions

Releaser owns the GitHub repo-settings surface and any Terraform-managed org-repo equivalents. Steps:

1. **Discover authoritative source**:
   - Check whether `autom8y/autom8y-asana` branch protection is managed by Terraform under `autom8y/infra` (or equivalent org-repo). If yes, edit the `github_branch_protection` resource and apply via the org's standard plan/apply flow. If no, apply via `gh api` directly.

2. **Apply branch-protection patch** (gh path):
   ```bash
   gh api -X PUT repos/autom8y/autom8y-asana/branches/main/protection \
     -H "Accept: application/vnd.github+json" \
     -f required_status_checks.strict=true \
     -F required_status_checks.contexts='["ci / Lint & Type Check","ci / Test"]' \
     -F enforce_admins=true \
     -F required_pull_request_reviews.required_approving_review_count=1 \
     -F required_pull_request_reviews.dismiss_stale_reviews=true \
     -F restrictions=null
   ```
   Adjust the `contexts` list to the canonical names emitted by `.github/workflows/ci.yml` (verify via `gh api repos/autom8y/autom8y-asana/commits/main/check-runs` against a known-green commit).

3. **Apply branch-protection patch** (Terraform path):
   Update the `github_branch_protection` resource for `main` to add `required_status_checks { contexts = [...] }`, `enforce_admins = true`, and `required_pull_request_reviews { required_approving_review_count = 1 }`. Plan, request review per org-repo conventions, apply.

4. **Post-apply verification**:
   - Re-query `gh api repos/autom8y/autom8y-asana/branches/main/protection` and assert the three fields are set.
   - Open a no-op PR that deliberately fails `Lint & Type Check` (e.g. inject a ruff violation in a throwaway branch) and confirm the merge button is disabled.

5. **Rollback plan**:
   - gh path: re-run the same `gh api -X PUT` with the prior context list (capture current state via `gh api repos/autom8y/autom8y-asana/branches/main/protection > /tmp/bp-pre.json` BEFORE step 2; restore by replaying the relevant fields).
   - Terraform path: `git revert` the `github_branch_protection` change and re-apply.
   - Emergency unblock: a repo admin can temporarily set `enforce_admins=false` to land a hotfix; document and reverse within 24h.

## Out-of-scope

Eunomia did not:
- Touch any `.github/workflows/*.yml` content (B4 is a settings-surface gap, not a workflow-content gap).
- Modify Terraform under `autom8y/infra` or any other org-repo (cross-repo edits are releaser's surface).
- Run `gh api -X PUT` against repo settings (governance write is releaser's authority).
- Re-trigger or rewrite PR #69's history (it is the evidence anchor, not a remediation target).
- Address the broader test-ecosystem entropy items A1–A3 and B1–B3 (those land via separate eunomia execution artifacts).

## Acceptance criteria

Releaser's definition-of-done:

1. `gh api repos/autom8y/autom8y-asana/branches/main/protection` returns `required_status_checks.contexts` containing at minimum `ci / Lint & Type Check` (and `ci / Test` if present and stable).
2. The same response shows `enforce_admins.enabled = true`.
3. The same response shows `required_pull_request_reviews.required_approving_review_count >= 1`.
4. A deliberately-red verification PR (lint failure) cannot be merged via the GitHub UI or `gh pr merge` while the failing check is reported.
5. The change is captured in either a Terraform commit (with apply log) or a runbook entry citing the exact `gh api` invocation and the pre-state snapshot path, so the change is reversible and auditable.
6. A release-back HANDOFF (releaser → eunomia) is filed under `.ledge/spikes/` recording the chosen path (TF vs gh), the canonical context names installed, the verification PR URL, and the pre-state snapshot location.
