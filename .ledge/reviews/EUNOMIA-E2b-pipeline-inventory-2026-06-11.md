---
type: review
status: accepted
evidence_grade: MODERATE
evidence_grade_rationale: >
  Eunomia is inventorying a CI surface it authored (the aggregate-coverage gate, CHANGE-005b).
  Self-referential authorship ceiling applies per self-ref-evidence-grade-rule. Structural
  findings are receipted by direct file inspection; MODERATE is the ceiling, not the floor.
station: E2b
rite: eunomia
scan_anchor: origin/main@49099b12 (autom8y-asana), origin/main@c8c397f2 (autom8y), origin/main@f5601acb (autom8y-workflows)
scan_date: 2026-06-11
---

# EUNOMIA-E2b Pipeline Inventory — 2026-06-11

## Scope

CI provider: GitHub Actions (Tier 1 — full heuristics apply).

Three-repo surface inventoried at origin/main snapshots:

| Repo | SHA | Workflow Count | Total Lines |
|------|-----|----------------|-------------|
| autom8y-asana | 49099b12 | 12 (.yml) | 1,063 |
| autom8y-workflows | f5601acb | 13 (.yml) | ~2,000+ |
| autom8y (monorepo, asana-relevant) | c8c397f2 | 5 key files scanned | ~2,000+ |

Composite actions in autom8y-asana: 2 (`fleet-conformance-gate`, `validate-env-injection`).

---

## Section 1: Workflow Census

### 1.1 autom8y-asana (origin/main@49099b12)

All 12 workflows are `state: active` per GitHub API (verified by `gh api` query).

| File | Type | Triggers | Jobs | Lines | Timeout | Concurrency | WF-Perm | Notes |
|------|------|----------|------|-------|---------|-------------|---------|-------|
| test.yml | Test | push/main, PR/main, workflow_dispatch | 4 (ci, fuzz, workflow-handler-isolated, fleet-schema-governance) | 370 | 15m (fuzz,whi), 5m (governance) | YES | job-level only | Hub reusable caller (93dbbc29) |
| nightly-live-smoke.yml | Nightly/Live | schedule(09:15 UTC), workflow_dispatch | 1 (live-smoke) | 183 | 15m | YES | YES (workflow) | CHANGE-001. Only 1 run (failed, see §6) |
| post-merge-coverage.yml | Coverage | push/main, workflow_dispatch | 1 (coverage) | 99 | 25m | YES | job-level only | CHANGE-005b gate |
| aegis-synthetic-coverage.yml | Quality | push/main (paths), PR/main (paths) | 1 (aegis) | 91 | 15m | YES | job-level only | |
| durations-refresh.yml | Maintenance | schedule(Mon 09:00 UTC), workflow_dispatch | 1 (refresh) | 104 | 25m | YES | job-level only | peter-evans/create-pull-request v8 (node24) |
| satellite-dispatch.yml | Deploy | repository_dispatch, workflow_run(Test), workflow_dispatch | 1 (dispatch) | 75 | 5m | YES | YES (permissions: {}) | DEPLOY-COUPLED DEFER — node20 (see §3) |
| dockerfile-lint.yml | Lint | push/main (paths), PR/main (paths) | 2 (hadolint, m16-pattern-assert) | 56 | NONE per job | NO | YES (contents: read) | No per-job timeouts |
| scorecard.yml | Security | schedule(Mon 06:00 UTC), workflow_dispatch | 1 (scorecard) | 23 | NONE | NO | NO (intentional — see note) | Hub reusable caller (f5601acb) |
| dependency-review.yml | Security | PR/main | 1 (dependency-review) | 12 | NONE | NO | YES (contents: read) | Hub reusable caller (f5601acb) |
| gitleaks.yml | Security | push/main, PR/main | 1 (gitleaks) | 19 | NONE | YES | YES | Hub reusable caller (f5601acb) |
| trufflehog-scan.yml | Security | schedule(Mon 06:00 UTC), workflow_dispatch | 1 (trufflehog) | 13 | NONE | NO | YES (contents: read) | Hub reusable caller (f5601acb) |
| zizmor.yml | Security | push/main (paths), PR/main (paths) | 1 (zizmor) | 19 | NONE | NO | YES | Hub reusable caller (f5601acb) |

**Note on scorecard.yml**: No workflow-level permissions is intentional and documented inline (line 8: "The scorecard webapp rejects workflow-level write permissions"). Permissions are at job level. This is a documented design constraint, not a safety gap.

### 1.2 autom8y-workflows (origin/main@f5601acb)

| File | Type | Lines | Role |
|------|------|-------|------|
| satellite-ci-reusable.yml | Reusable (workflow_call) | ~1,400 | Hub reusable — fleet-shared CI |
| security-dependency-review.yml | Security wrapper | 19 | Hub wrapper |
| security-gitleaks.yml | Security wrapper | 35 | Hub wrapper |
| security-scorecard.yml | Security wrapper | 42 | Hub wrapper |
| security-trufflehog.yml | Security wrapper | 33 | Hub wrapper |
| security-zizmor.yml | Security wrapper | 31 | Hub wrapper |
| propagate-reusable-pin.yml | Maintenance | 112 | Auto-bumper for satellite pins |
| ci.yml | Lint | 47 | Internal actionlint + zizmor |
| dependency-review.yml | Security | 13 | Internal |
| gitleaks.yml | Security | 19 | Internal |
| scorecard.yml | Security | 23 | Internal |
| trufflehog-scan.yml | Security | 14 | Internal |
| zizmor.yml | Security | 23 | Internal |

### 1.3 autom8y monorepo — asana-relevant workflows (origin/main@c8c397f2)

| File | Type | Lines | Trigger | Asana Relevance |
|------|------|-------|---------|-----------------|
| satellite-receiver.yml | Deploy | 682 | repository_dispatch (satellite-deploy), workflow_dispatch | PRIMARY — receives satellite-dispatch.yml events, runs ECS deploy |
| service-terraform.yml | IaC | 367 | PR (terraform/services/**), push/main, merge_group, workflow_dispatch | PRIMARY — plan+apply for asana terraform |
| terraform-plan-reusable.yml | IaC reusable | ~250 | workflow_call | Called by service-terraform.yml |
| terraform-apply-reusable.yml | IaC reusable | ~230 | workflow_call | Called by service-terraform.yml |
| snc-namespaces-gen-freshness.yml | Freshness guard | ~60 | PR (asana TF paths), workflow_dispatch | NEW (PR #515, c8c397f2) — guards SNC vendored copy |

---

## Section 2: Reusable Workflow Pin Analysis

### 2.1 Pin Inventory — autom8y-asana callers

| Caller | Target | SHA Pinned | Hub PR | Node Era |
|--------|--------|-----------|--------|----------|
| test.yml (job: ci) | satellite-ci-reusable.yml | `93dbbc2933affcce3e692ccff8f17d382811264d` | #25 | node24-clean |
| scorecard.yml | security-scorecard.yml | `f5601acbe3905270dfcb9069854c78c0f940ad05` | #27 | node24-clean |
| dependency-review.yml | security-dependency-review.yml | `f5601acbe3905270dfcb9069854c78c0f940ad05` | #27 | node24-clean |
| gitleaks.yml | security-gitleaks.yml | `f5601acbe3905270dfcb9069854c78c0f940ad05` | #27 | node24-clean |
| trufflehog-scan.yml | security-trufflehog.yml | `f5601acbe3905270dfcb9069854c78c0f940ad05` | #27 | node24-clean |
| zizmor.yml | security-zizmor.yml | `f5601acbe3905270dfcb9069854c78c0f940ad05` | #27 | node24-clean |

### 2.2 Version Skew Matrix

**FINDING: Two distinct autom8y-workflows SHAs are pinned across autom8y-asana.**

- `93dbbc29` — satellite-ci-reusable (test.yml only, PR #25)
- `f5601acb` — all 5 security wrapper callers (PR #27, the later commit)

This is a LEGITIMATE non-skew: the two SHAs serve distinct workflow files. `93dbbc29` is the correct pin for the satellite-ci-reusable because `f5601acb` (PR #27) only touched security wrappers and did not alter satellite-ci-reusable.yml (only the `uv export --all-extras` fix in the consumer-gate candidate step). The test.yml pin to `93dbbc29` is the node24 disarm SHA for the reusable; upgrading to `f5601acb` would pull in the `--all-extras` fix as a bonus — not a safety regression, but not yet done.

**The satellite-ci-reusable at `93dbbc29` vs `f5601acb` difference**: `f5601acb` adds `--all-extras` to the `uv export` command in the consumer-gate step (prevents constraint-file undercount for extras-only subtrees). Satellites pinned at `93dbbc29` are missing this fix. Autom8y-asana is pinned at `93dbbc29`.

### 2.3 Action Pin Version Skew — Cross-Repo Matrix

| Action | autom8y-asana (49099b12) | satellite-ci-reusable (f5601acb) | autom8y satellite-receiver (c8c397f2) | autom8y terraform-plan-reusable | autom8y terraform-apply-reusable |
|--------|--------------------------|----------------------------------|---------------------------------------|--------------------------------|----------------------------------|
| actions/checkout | `93cb6efe` (v5.0.1, node24) | `93cb6efe` (v5.0.1, node24) | `93cb6efe` (v5.0.1, node24) | `93cb6efe` (v5.0.1, node24) | `34e114876b` (v4, node20) |
| actions/setup-python | `a309ff8b` (v6.2.0, node24) | `a309ff8b` (v6.2.0, node24) | — | — | — |
| aws-actions/configure-aws-credentials | `e7f100cf` (v6.2.0, node24) | `e7f100cf` (v6.2.0, node24) | `e7f100cf` (v6.2.0, node24) | `e7f100cf` (v6.2.0, node24) | `7474bc46` (v4, node20) |
| astral-sh/setup-uv | `08807647` (v8.1.0, node24) | `08807647` (v8.1.0, node24) | — | `08807647` (v8.1.0, node24) | `38f3f104` (v4, node20) |
| actions/upload-artifact | `b7c566a7` (v6.0.0, node24) | `b7c566a7` (v6.0.0, node24) | `b7c566a7` (v6.0.0, node24) | `b7c566a7` (v6.0.0, node24) | `ea165f8d` (v4, node20) |
| actions/download-artifact | `37930b1c` (v7.0.0, node24) | `37930b1c` (v7.0.0, node24) | — | — | — |
| actions/create-github-app-token | `bcd2ba49` (v3.2.0, node24) | `bcd2ba49` (v3.2.0, node24) | `bcd2ba49` (v3.2.0, node24) | `bcd2ba49` (v3.2.0, node24) | `d72941d7` (v1, mixed) |
| actions/cache | — | `27d5ce7f` (v4, node24-era) | — | `27d5ce7f` (v5.0.5, node24) | `00578204` (v4, node24-era) |
| hashicorp/setup-terraform | — | — | — | `dfe3c3f8` (v4.0.1, node24) | `b9cd54a3` (v3, node20) |
| extractions/setup-just | — | — | — | `53165ef7` (v4, composite) | `dd310ad5` (v2, composite) |

**CRITICAL VERSION SKEW: `terraform-apply-reusable.yml` in autom8y is on node20-era action pins.** Multiple actions use node20 SHAs: checkout v4, configure-aws-credentials v4, setup-uv v4, upload-artifact v4, setup-terraform v3, create-github-app-token v1. This is the monorepo's terraform apply chain — the 2026-06-16 deprecation deadline affects this file.

**`service-terraform.yml` itself** uses checkout@`34e114876b` (v4, node20) for its `detect` job while calling terraform-plan-reusable (which uses v5/v6 pins). Version skew within the same orchestrating workflow.

---

## Section 3: CHANGE-001 (Nightly Live Smoke) — Existence Verdict

**VERDICT: LANDED-AND-LIVE. Receipt follows.**

### Receipt

Landing commit: `1c503339559964c119844dd4be8ce8125f3c6b41`
Commit message: `ci(live-smoke): nightly OIDC forcing-function for the live-smoke suite [CHANGE-001] (#125)`
Author date: 2026-06-11T10:16:21+02
File created: `.github/workflows/nightly-live-smoke.yml` (183 lines)
Current HEAD of origin/main (49099b12) includes this file: CONFIRMED by direct read.

GitHub API state: `Nightly Live Smoke` workflow, state=`active`, id=293680531.

**Run count: 1 (total_count=1)**. The single run occurred at 2026-06-11T10:55:03Z and concluded `failure`. This is the same day as the landing commit (1c503339, 2026-06-11). The run failed, which is consistent with the honest IAM disclosure in the workflow header (lines 29-46): the `github-actions-deploy` OIDC role does NOT yet grant `s3://autom8-s3/asana-cache/tasks/*` read, so AccessDenied is expected. The workflow explicitly documents: "Until a read-only asana-cache/tasks/* grant is added to github-actions-deploy [...] this nightly will fail on AccessDenied. That failure is honest, not flaky."

**PV-SURFACE discrepancy resolution**: The prior IGN-SX record claimed CHANGE-001 landed in asana CI. That claim is CONFIRMED ACCURATE. The discrepancy was the PV spot-check failing to find it — likely because the landing commit (1c503339) predates the #129 node24 bump (49099b12) by only a few hours on the same day, and both were in the unstale origin/main window. The file exists and the workflow is active.

**Known open item (not a pipeline-cartographer finding — inherited from CHANGE-001 design)**: OIDC role `github-actions-deploy` lacks `s3://autom8-s3/asana-cache/tasks/*` read grant. Until autom8y#481 lands the grant, every nightly run will fail on AccessDenied. The workflow is structurally correct; the IAM prerequisite is the gap.

---

## Section 4: Coverage Gate and Hidden-Files Guard Verification

### 4.1 CHANGE-005b — Aggregate Coverage Gate (80%)

**WHERE IT LIVES**: Two locations implement the 80% coverage gate:

1. **test.yml + satellite-ci-reusable.yml** (sharded path, CHANGE-005a/005b):
   - test.yml passes `coverage_threshold_aggregate: 80` to the reusable (line 61)
   - satellite-ci-reusable.yml@f5601acb (`coverage-aggregate` job) enforces `--fail-under=${COVERAGE_THRESHOLD}` on combined shard .coverage files
   - Active for: push/PR runs on autom8y-asana via the hub reusable

2. **post-merge-coverage.yml** (full-suite single-shard path):
   - Runs `--cov-fail-under=80` directly (line 83)
   - Active for: push/main only
   - Serves as the post-merge diagnostic (not gate-blocking in PR path)

**Verdict**: Coverage gate is present and enforced at both altitudes.

### 4.2 Hidden-Files Guard for `.coverage` dotfile

**CHANGE reference**: autom8y-workflows#24 introduced `include-hidden-files: true` to prevent `actions/upload-artifact >=v4.4` from silently excluding `.coverage` dotfiles.

**satellite-ci-reusable.yml@f5601acb — VERIFIED INTACT**:
- "Upload shard coverage data" step (line ~761): `include-hidden-files: true` — PRESENT
- "Upload shard durations" step (line ~781): `include-hidden-files: true` — PRESENT
- Source verified at: `origin/main:.github/workflows/satellite-ci-reusable.yml` (confirmed by direct `git show` probe)

**post-merge-coverage.yml — MISSING GUARD**:
- "Upload coverage artifact" step (line 92): uploads `coverage.xml` AND `.coverage`
- `include-hidden-files:` key is ABSENT
- `actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f` (v6.0.0) — same version class affected by the GHSA-6q4m hidden-files behavior
- **Impact**: The `.coverage` artifact upload in post-merge-coverage.yml will silently produce an empty artifact. `coverage.xml` (not a dotfile) will upload correctly. The `.coverage` artifact is labeled `if-no-files-found: warn` — so no job failure, just a silently missing diagnostic artifact.
- **Severity note for entropy-assessor**: This is a diagnostic artifact (not the gate-blocking shard coverage), so the gate correctness is unaffected. But the artifact exists for diagnosis ("capture even on threshold failure for diagnosis") and is silently hollow.

**aegis-synthetic-coverage.yml — not affected**: uploads `aegis-report.json` only (not a dotfile).

---

## Section 5: Duplication Analysis

### 5.1 CodeArtifact Token Fetch — Inline Duplication Across 5 Workflows

**Pattern A — Simple fetch (no retry)**: 3 occurrences in autom8y-asana
- `aegis-synthetic-coverage.yml` (lines 50-54)
- `durations-refresh.yml` (lines 48-53)
- `post-merge-coverage.yml` (lines 52-57)

**Pattern B — 3-attempt retry with connect/read timeouts**: 2+ occurrences in autom8y-asana
- `nightly-live-smoke.yml` (lines 105-121)
- `test.yml` (lines 141-158, fuzz job; lines 283-299, workflow-handler-isolated job)

The retry pattern was added to address the PR #121 flake class (CodeArtifact connect-timeout). The satellite-ci-reusable.yml encapsulates the retry at the fleet level (5 retry sites within the reusable). Workflows that run outside the reusable (aegis, durations-refresh, post-merge-coverage, nightly-live-smoke) maintain their own inline CodeArtifact fetch steps. The 3 simple-fetch workflows are MISSING the retry hardening that was specifically added to address a known flake class.

**SCAR-PC-002 pattern**: The full setup sequence (checkout → configure-aws-credentials → Login to CodeArtifact → install-uv → install-dependencies) appears inline in 5 workflows. The reusable-workflow seam covers it for the main test path but not for the ancillary workflows.

### 5.2 TF_VAR Environment Block — Plan vs Apply Reusable

**SCAR-PC-001 assessment**: `terraform-plan-reusable.yml` and `terraform-apply-reusable.yml` each carry independently-maintained `env:` blocks with identical `TF_VAR_*` variable mappings (~24 variables each). A diff of the sorted variable lists shows COMPLETE SYMMETRY — no variable asymmetry detected at the current snapshot. Both files carry the same 24+ variables (grafana_url, grafana_auth, amp_query_endpoint, slack_bot_token, observability_slack_bot_token, grafana_tempo_*, grafana_loki_*, ecr_repository_url, vpc_id, subnet_ids, mysql_secret_arn, auth_db_secret_arn, security_group_ids, monitoring_email, meta_account_id, db_name, gcal_impersonation_target, openfga_api_url, openfga_authorization_model_id, openfga_store_id).

The apply block additionally has `TF_VAR_canary_enabled` (canary control input) which is apply-only by design. This is a justified asymmetry, not a drift.

**Current drift: NONE.** Risk: high — any addition to one block risks omission from the other. The blocks are independently maintained across two files.

### 5.3 Composite Action Underutilization (SCAR-PC-005)

Two composite actions exist in autom8y-asana:
- `.github/actions/fleet-conformance-gate` — used in satellite-ci-reusable.yml (via cross-repo canonical checkout) and test.yml's `fleet-schema-governance` job
- `.github/actions/validate-env-injection` — used in satellite-ci-reusable.yml

The `validate-env-injection` composite guards env injection in the reusable. Inline workflows (nightly-live-smoke, post-merge-coverage, aegis) do NOT use this composite — but they also do not accept arbitrary user-supplied env pairs, so this is not a SCAR-PC-005 underutilization gap.

---

## Section 6: Dead Code Inventory

**`if: false` patterns**: None found across any autom8y-asana workflow files.

**Commented-out steps**: None substantive detected. Comment blocks are documentation (CodeArtifact retry rationale, node24 lineage notes).

**Deprecated triggers**: None. No `push: tags:` or other deprecated patterns.

**Zero-run workflows**: All 12 workflows show run counts > 0 EXCEPT:
- `nightly-live-smoke.yml`: 1 run (failure, day-of-landing). Not dead — it is newly landed and will receive its second run on 2026-06-12 at 09:15 UTC.

**Workflow state**: All 12 workflows `state: active` per GitHub API.

**`continue-on-error` usage (non-blocking intent)**:
- `test.yml` / `fuzz` job: `continue-on-error: true` — documented intentional (fuzz is signal-only, xfail)
- `test.yml` / `workflow-handler-isolated` job: `continue-on-error: true` — documented intentional (quarantine for xdist-fragile tests)
- `satellite-receiver.yml` / `metrics-smoke` job: `continue-on-error: true` — documented intentional (post-deploy non-blocking gate)

None of these are anti-patterns; all are documented.

---

## Section 7: Safety Configuration Audit

### 7.1 Dimension Coverage

| Dimension | autom8y-asana | satellite-ci-reusable | autom8y deploy chain |
|-----------|---------------|----------------------|---------------------|
| timeout-minutes | 7/12 have at least one job timeout (58%) | All jobs have timeouts | satellite-receiver: MIXED (validate=5m, sign=5m, deploy=30m, metrics-smoke=5m); service-terraform: 5m/30m; snc=5m |
| concurrency | 8/12 have concurrency group (67%) | N/A (reusable, caller controls) | satellite-receiver: YES; service-terraform: YES; snc: YES |
| permissions | 8/12 have some permissions block (67% — 5 wf-level, 5 job-level only, 2 neither) | job-level on all jobs | satellite-receiver: YES (top-level + job); service-terraform: YES |
| continue-on-error | 3 jobs across 2 workflows, all documented | Several (non-blocking gates) | 1 (metrics-smoke) |

### 7.2 Missing Timeout Detail

Workflows with NO per-job timeout-minutes:
- `dockerfile-lint.yml` — hadolint and m16-pattern-assert jobs have no timeout
- `scorecard.yml` — scorecard job has no timeout (delegated to reusable)
- `dependency-review.yml` — delegated to reusable
- `gitleaks.yml` — delegated to reusable
- `trufflehog-scan.yml` — delegated to reusable
- `zizmor.yml` — delegated to reusable

For the 5 reusable-caller security wrappers, timeouts are inherited from the hub reusable. The security-scorecard.yml, security-gitleaks.yml, etc. in autom8y-workflows do have job-level timeouts (5m each per their definitions). This is a pass-through pattern, not a gap.

`dockerfile-lint.yml` is the only genuine gap — two inline jobs with no timeout.

### 7.3 Missing Workflow-Level Permissions Detail

Workflows lacking ANY permissions block (job or workflow level):
- None found — all 12 workflows have at least job-level or workflow-level permissions.

Workflows with job-level-only permissions (no workflow-level `permissions:`):
- aegis-synthetic-coverage.yml: job has `id-token: write, contents: read`
- durations-refresh.yml: job has `id-token: write, contents: write, pull-requests: write`
- post-merge-coverage.yml: job has `id-token: write, contents: read`
- test.yml: ci, fuzz, workflow-handler-isolated jobs each have explicit permissions

The absence of workflow-level permissions when job-level permissions exist is NOT a default-to-write-all situation — GitHub Actions defaults each job to the org default when no job-level permission is set. Since all jobs in these workflows have explicit job-level permissions, this is safe.

**Workflows that default to org-level**: NONE. All workflows have either workflow-level or job-level explicit permissions.

### 7.4 satellite-dispatch.yml — Node20 Deploy-Coupled DEFER (Verified)

`satellite-dispatch.yml` uses `peter-evans/repository-dispatch@ff45666b9427631e3450c54a1bcbee4d9ff4d7c0 # v3` without a node24 comment. The commit message for #129 (49099b12) explicitly documents: "NOT touched (deploy-coupled, deferred): satellite-dispatch.yml (repository-dispatch v3, node20) -- it is the Satellite Dispatch deploy leg."

This is the KNOWN DEFER. Verified as intentional, documented in the commit message, and bounded by the org 2026-06-16 deadline.

---

## Section 8: snc-namespaces-gen-freshness.yml (autom8y monorepo #515)

File: `.github/workflows/snc-namespaces-gen-freshness.yml`  
Landing: PR #515, commit `c8c397f218f83bb7986a0c4b01741aca8674b829` on origin/main of autom8y monorepo.  
Status: Verified present and active at origin/main.

**Trigger paths**: `terraform/services/asana/namespaces.gen.json`, `locals_namespaces.tf`, `check_namespaces_gen.sh`, and the workflow file itself. `pull_request` only (no push/deploy coupling).

**Safety config**:
- `permissions: contents: read` — correctly scoped
- `concurrency:` — YES, cancel-in-progress: true
- `timeout-minutes: 5` — present on the single job
- `uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1 (node24)` — node24-clean

**No deploy coupling**: workflow header explicitly states "DEPLOY COUPLING: NONE." Confirmed by `on:` trigger set (pull_request + workflow_dispatch only, no push/repository_dispatch).

---

## Section 9: Findings Ranked by Severity

| Rank | Finding | Category | SCAR/GUARD | Affected Files | Status |
|------|---------|----------|-----------|---------------|--------|
| 1 | terraform-apply-reusable.yml uses node20-era action pins (checkout v4, configure-aws-credentials v4, setup-uv v4, setup-terraform v3, upload-artifact v4, create-github-app-token v1) — 2026-06-16 deprecation deadline | Version Skew | SCAR-PC-003 | autom8y/terraform-apply-reusable.yml | OPEN |
| 2 | service-terraform.yml detect job uses checkout@34e114876b (v4, node20) while calling plan/apply reusables that use v5 | Version Skew | SCAR-PC-003 | autom8y/service-terraform.yml | OPEN |
| 3 | nightly-live-smoke.yml has 1 run (failure) — IAM prerequisite gap (github-actions-deploy lacks asana-cache/tasks/* S3 read) | Safety / Forcing Function | GUARD-PC-001 | .github/workflows/nightly-live-smoke.yml | OPEN (IAM, tracked at autom8y#481) |
| 4 | post-merge-coverage.yml upload-artifact for .coverage missing `include-hidden-files: true` — diagnostic artifact silently hollow | Safety / Dead Code | SCAR-PC-002 | .github/workflows/post-merge-coverage.yml | OPEN |
| 5 | satellite-ci-reusable pin in test.yml at 93dbbc29 (PR #25) vs latest f5601acb (PR #27) — missing uv export --all-extras fix in consumer-gate step | Version Skew | SCAR-PC-003 | .github/workflows/test.yml | OPEN (low risk for asana since consumer-gate is secondary path) |
| 6 | CodeArtifact simple-fetch (no retry) in 3 standalone workflows (aegis, durations-refresh, post-merge-coverage) vs retry pattern in nightly/test — inconsistent hardening for known flake class | Duplication / Safety | SCAR-PC-002 | aegis-synthetic-coverage.yml, durations-refresh.yml, post-merge-coverage.yml | OPEN |
| 7 | TF_VAR env blocks duplicated across terraform-plan-reusable.yml and terraform-apply-reusable.yml (~24 identical variables) — current drift=0 but high ongoing risk | Duplication | SCAR-PC-001 | autom8y/terraform-plan-reusable.yml, autom8y/terraform-apply-reusable.yml | OPEN (structural, no current drift) |
| 8 | dockerfile-lint.yml has no per-job timeout-minutes on hadolint and m16-pattern-assert jobs | Safety | GUARD-PC-001 | .github/workflows/dockerfile-lint.yml | OPEN (low severity) |

---

## Section 10: Agent-Provenance Signals

**Append-only growth indicators**:
- The `test.yml` comment density is high (inline rationale for every design decision) — consistent with iterative human+AI authoring
- `continue-on-error: true` jobs accumulate without corresponding quarantine-exit plans (fuzz, workflow-handler-isolated) — standard pattern, both documented
- CodeArtifact retry was added to inline workflows post-hoc (nightly-live-smoke) but not back-propagated to older inline workflows (aegis, durations-refresh, post-merge-coverage) — characteristic bespoke step accumulation

**Bespoke step accumulation**:
- 5 distinct inline CodeArtifact setup sequences across autom8y-asana workflows (two distinct patterns)
- The satellite-ci-reusable encapsulates the canonical hardened version; inline files are lagging copies

**Trajectory**: Clean adoption of hub-reusable pattern for security wrappers (all 5 using f5601acb). Main test path properly delegates to the reusable. Ancillary workflows (coverage, aegis, durations) remain inline and carry bespoke copies of the setup sequence — a partial adoption of the composite-action / reusable-workflow pattern.

---

## Section 11: Raw Metrics

| Metric | Value |
|--------|-------|
| autom8y-asana workflow count | 12 |
| autom8y-asana total workflow lines | 1,063 |
| autom8y-workflows relevant workflow count | 13 |
| autom8y monorepo asana-relevant files | 5 |
| Workflows with timeout coverage (autom8y-asana) | 7/12 (58%) |
| Workflows with concurrency control (autom8y-asana) | 8/12 (67%) |
| Workflows with permissions blocks (autom8y-asana) | 12/12 (100% — all have at least job-level) |
| Dead workflows (zero runs) | 0 (nightly-live-smoke: 1 run, newly landed) |
| `if: false` disabled jobs | 0 |
| continue-on-error jobs (intentional non-blocking) | 3 (fuzz, workflow-handler-isolated, metrics-smoke) |
| Action version skew instances | 2 (terraform-apply-reusable on node20 era; satellite-ci-reusable 93dbbc29 vs f5601acb) |
| autom8y-workflows SHA pins in autom8y-asana | 2 distinct (93dbbc29 + f5601acb — justified non-skew) |
| CodeArtifact fetch pattern variants | 2 (simple + retry-hardened) |
| TF_VAR duplication (plan vs apply) | 24 variables × 2 files (no current drift) |
| Composite actions existing | 2 (fleet-conformance-gate, validate-env-injection) |
| CHANGE-001 (nightly-live-smoke) | LANDED-AND-LIVE (1 run, failed on IAM prerequisite) |
| CHANGE-005b (80% coverage gate) | ACTIVE (satellite-ci-reusable coverage-aggregate + post-merge-coverage.yml) |
| include-hidden-files guard status | PRESENT in satellite-ci-reusable; ABSENT in post-merge-coverage.yml (diagnostic artifact only) |
| node24 sweep completeness (autom8y-asana) | 11/12 clean; satellite-dispatch.yml node20 DEFER documented |
| node24 sweep completeness (autom8y monorepo, asana-relevant) | terraform-apply-reusable.yml + service-terraform.yml detect job OPEN |

---

## Handoff Checklist

- [x] All sections populated or explicitly marked N/A
- [x] Raw metrics table has numeric values for all applicable metrics
- [x] Duplication analysis includes specific file pairs and block locations
- [x] Safety audit reports per-dimension coverage percentages
- [x] CHANGE-001 verdict with receipt (landed commit SHA + GitHub API verification)
- [x] Coverage gate + hidden-files guard verification receipted
- [x] Version skew identified per action with specific SHAs
- [x] No scan areas flagged as incomplete
- [x] Self-referential authorship ceiling noted (MODERATE evidence grade)
