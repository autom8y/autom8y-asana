---
type: audit
---
# Pipeline Inventory — autom8y-asana
**Date**: 2026-06-01
**Agent**: pipeline-cartographer
**Target**: /Users/tomtenuta/Code/a8/repos/autom8y-asana
**Downstream**: entropy-assessor

---

## 1. Scope and Target Description

- **CI Provider**: GitHub Actions (Tier 1 — full heuristics applicable)
- **Workflow files**: 11 (`.github/workflows/*.yml`)
- **Total workflow lines**: 800
- **Composite actions**: 2 (`.github/actions/fleet-conformance-gate/`, `.github/actions/validate-env-injection/`)
- **Composite action lines**: 88
- **Reusable workflow call sites in this repo**: 6 (5 to `autom8y/autom8y-workflows`, 1 architectural: `test.yml` ci job)
- **Cross-repo source read**: `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml` (1067 lines at `cbc3c58e`)
- **Trivy gate location**: autom8y monorepo (`autom8y/.github/workflows/service-build.yml:259,281,307,325`) — UV-P for this repo

---

## 2. Workflow Census

| File | Type | Triggers | Jobs | Lines | Reusable Workflow? | Notes |
|------|------|----------|------|-------|--------------------|-------|
| `test.yml` | test/lint/governance | push(main), pull_request(main), workflow_dispatch | 4 (ci, fuzz, workflow-handler-isolated, fleet-schema-governance) | 305 | YES (ci job → satellite-ci-reusable.yml@cbc3c58e) | Main CI; consumer-gate dispatch receiver |
| `post-merge-coverage.yml` | coverage | push(main), workflow_dispatch | 1 (coverage) | 99 | NO (inline) | Aggregate 80% floor enforcement post-merge |
| `aegis-synthetic-coverage.yml` | synthetic-tests | push(main)+paths, pull_request(main)+paths | 1 (aegis) | 91 | NO (inline) | Path-filtered; runs on src/** changes |
| `satellite-dispatch.yml` | deploy-trigger | repository_dispatch(sdk-published), workflow_run(Test:completed:main), workflow_dispatch | 1 (dispatch) | 65 | NO (inline) | Downstream deploy trigger to autom8y monorepo |
| `durations-refresh.yml` | ci-maintenance | schedule(Monday 09:00 UTC), workflow_dispatch | 1 (refresh) | 104 | NO (inline) | Weekly pytest-split duration update |
| `dockerfile-lint.yml` | lint | push(main)+paths, pull_request(main)+paths | 2 (hadolint matrix, m16-pattern-assert) | 56 | NO (inline) | Path-filtered; Dockerfile only |
| `dependency-review.yml` | security | pull_request(main) | 1 | 9 | YES (→ security-dependency-review.yml@44b771e5) | PR-only |
| `gitleaks.yml` | security | push(main), pull_request(main) | 1 | 19 | YES (→ security-gitleaks.yml@44b771e5) | |
| `scorecard.yml` | security | schedule(Monday 06:00 UTC), workflow_dispatch | 1 | 23 | YES (→ security-scorecard.yml@c77acb0c) | DIFFERENT SHA than other security workflows |
| `trufflehog-scan.yml` | security | schedule(Monday 06:00 UTC), workflow_dispatch | 1 | 10 | YES (→ security-trufflehog.yml@44b771e5) | |
| `zizmor.yml` | security | push(main)+paths, pull_request(main)+paths | 1 | 19 | YES (→ security-zizmor.yml@44b771e5) | Path-filtered to .github/workflows/** |

**Workflow total**: 11 files, 800 lines, 15 jobs defined across all files.

---

## 3. PR vs Main Asymmetry (ASSESS-1)

### Surface: `test.yml:64-65`

The `ci` job delegates to `satellite-ci-reusable.yml`. Within that call:

```yaml
# test.yml:64
test_markers_exclude: ${{ github.event_name == 'pull_request' && 'not integration and not benchmark and not slow and not fuzz and not worker_isolated' || 'not integration and not benchmark and not fuzz and not worker_isolated' }}
# test.yml:65
run_integration: ${{ github.event_name == 'push' }}
```

**PR vs main delta — verified**:
- PR excludes: `integration`, `benchmark`, `slow`, `fuzz`, `worker_isolated`
- Main/push excludes: `integration`, `benchmark`, `fuzz`, `worker_isolated`
- **`slow` tests (23 instances across tests/) run on push to main but NOT on PR**
- Integration tests: run on push only (`run_integration: true` on push)

**Linting asymmetry**: NONE. The `lint` job in `satellite-ci-reusable.yml:319-331` runs `ruff format --check`, `ruff check`, and `mypy --strict` unconditionally on BOTH PR and push. Branch protection requires `ci / Lint & Type Check` (confirmed via API). The 3 sequential main failures (ASSESS-1 narrative) were commit-by-commit mypy violations introduced and fixed across successive commits — not a CI gate asymmetry. The gate ran identically on PR; each commit genuinely had a lint violation.

**ASSESS-1 root clarification**: The real risk is `slow` test coverage gap on PR (23 slow tests that exercise timing/circuit-breaker edge cases). These include: `tests/unit/metrics/test_adversarial.py:401`, `tests/unit/clients/data/test_circuit_breaker.py:67`, `tests/unit/clients/data/test_insights.py:385-461`, `tests/unit/clients/data/test_cache.py:275`.

### Branch Protection (verified via GitHub API)
```
strict: true (require up-to-date before merge)
required_status_checks:
  - gitleaks / Secrets Scan
  - dependency-review / Dependency Review
  - ci / Test (shard 1/4) through (shard 4/4)
  - ci / Lint & Type Check
enforce_admins: false  <- admin bypass allowed (explains PR #69 --admin merge)
required_approving_review_count: 0
required_linear_history: true
```

NOT required: `post-merge-coverage`, `aegis`, `dockerfile-lint`, `fuzz`, `workflow-handler-isolated`, `fleet-schema-governance`.

---

## 4. Trivy Gate Configuration (ASSESS-2)

**UV-P: Trivy gate is in autom8y monorepo — OUT OF THIS REPO'S REACH**

Surface files (cross-repo, read-only observation):
- Gate location: `/Users/tomtenuta/Code/a8/repos/autom8y/.github/workflows/service-build.yml:259,281,307,325`
- `.trivyignore` location: `/Users/tomtenuta/Code/a8/repos/autom8y/.trivyignore`
- **Precedence**: The `.trivyignore` from the autom8y monorepo is COPIED into the satellite build workspace at `service-build.yml:99-103` (`cp _monorepo_policy/.trivyignore .trivyignore`). There is NO per-satellite `.trivyignore` — the monorepo is the single authority.
- **No `.trivyignore` exists in autom8y-asana repo** (confirmed: `find` returned no results).

**Exemption expiry audit** (from `/Users/tomtenuta/Code/a8/repos/autom8y/.trivyignore`):

| CVE / Rule | Approved | Review Date | Status (as of 2026-06-01) |
|---|---|---|---|
| CVE-2025-68121 | 2026-03-23 | 2026-04-22 | **EXPIRED** (40 days overdue) |
| CVE-2025-65896 | 2026-03-24 | 2026-04-23 | **EXPIRED** (39 days overdue) |
| aws-access-key-id (moto) | 2026-04-15 | 2026-05-15 | **EXPIRED** (17 days overdue) |
| CVE-2026-31789 | 2026-04-27 | 2026-05-27 | **EXPIRED** (5 days overdue) |
| gcp-service-account (openfga) | 2026-04-27 | No expiry | PERMANENT (false-positive) |

**4 of 4 time-boxed exemptions are past their 30-day review window.** There is no automated enforcement of the review cadence — the ADR-SEC-GATE-POLICY review discipline is manual-only. No scheduled CVE-DB refresh job exists that would proactively surface new CRITICAL/HIGH disclosures before a build breaks.

**The observability gap** (ASSESS-9 intersection): There is no alerting on Satellite Receiver build failures in this repo or the monorepo's Actions logs. The 4 consecutive failures (08:43-09:09 UTC 2026-06-01) would only surface via manual `gh run list`.

---

## 5. Satellite-Dispatch to Satellite-Receiver Chain (ASSESS-9 overlap)

### Surface: `satellite-dispatch.yml`

```yaml
# satellite-dispatch.yml:7-9 (trigger logic)
workflow_run:
  workflows: ["Test"]
  types: [completed]
  branches: [main]

# satellite-dispatch.yml:17-21 (skip-on-Test-fail conditional)
if: >-
  github.event_name == 'repository_dispatch' ||
  github.event_name == 'workflow_dispatch' ||
  github.event.workflow_run.conclusion == 'success'
```

**Skip-on-fail mechanism**: The `dispatch` job has an `if:` gate requiring `workflow_run.conclusion == 'success'`. If the `Test` workflow fails on main, dispatch is skipped. This is correct behavior — it prevents deploying broken code.

**Deploy chain sequence**:
1. Push to main → `Test` workflow (satellite-ci-reusable.yml)
2. `Test` completes with `success` → triggers `satellite-dispatch.yml`
3. `satellite-dispatch.yml` fires `repository_dispatch(satellite-deploy)` to `autom8y/autom8y`
4. `autom8y/autom8y` runs `service-build.yml` → Docker build + Trivy → ECS deploy

**CVE gate location**: `service-build.yml:324-325` in autom8y monorepo. The gate is: `if: inputs.skip_trivy_gate != true`.

**`permissions: {}` on satellite-dispatch.yml:12**: Correctly scoped to zero workflow-level permissions. The app token is minted explicitly for the dispatch action.

---

## 6. Consumer-Gate Semantics (ASSESS-3)

### Surface: `autom8y/.github/workflows/sdk-publish-v2.yml:523-697`

**All-5-green requirement**: The consumer-gate runs a matrix of `(sdk, satellite)` pairs. Satellites hard-coded at `sdk-publish-v2.yml:533-538`:
- autom8y-ads, autom8y-asana, autom8y-data, autom8y-scheduling, autom8y-sms

**Gate blocking logic** (`sdk-publish-v2.yml:690-697`):
```yaml
(needs.consumer-gate.result == 'success' || github.event.inputs.allow_breaking_change == 'true')
```

`allow_breaking_change` is a `workflow_dispatch` input (`sdk-publish-v2.yml:49`). When `true`, ALL consumer-gate failures are tolerated — including unrelated red from satellites that have nothing to do with the SDK being published. There is no "impacted-consumer-only" gating or zero-consumer skip mechanism.

**False-negative for zero-consumer SDKs**: If `autom8y-asana` or `autom8y-data` has pre-existing red (lint debt, DB-creds env gap), their failure blocks a zero-consumer SDK publish. The `allow_breaking_change` override is the only escape valve, and it bypasses ALL gates globally, not just the unrelated red.

**ASSESS-3 surface**: `sdk-publish-v2.yml:533-538` (hard-coded satellite list), `sdk-publish-v2.yml:690-697` (override scope). This is a UV-P for eunomia — the fix requires changes to `autom8y/sdk-publish-v2.yml`, which is cross-repo.

---

## 7. Floating Dependencies (ASSESS-4)

### A. npm transitive — Spectral rulesets

**Surface**: `autom8y-workflows/satellite-ci-reusable.yml` at local HEAD (72eaee8) uses:
```
npm install -g @stoplight/spectral-cli@6.15.0
```
This is a bare `npm install -g` — the `@stoplight/spectral-rulesets` transitive FLOATS.

**The fix** exists at `cbc3c58e` (PR #18, merged to `origin/main`):
```json
{ "dependencies": { "@stoplight/spectral-cli": "6.15.0" },
  "overrides": { "@stoplight/spectral-rulesets": "1.22.2" } }
```
autom8y-asana is correctly pinned to `cbc3c58e` which includes the fix. The local clone of autom8y-workflows is stale (72eaee8), but `origin/main` = `cbc3c58e`. Currently resolved for this satellite.

The spectral CLI is pinned globally (`@6.15.0`) but its internal rulesets transitive is now pinned via package.json overrides at the correct SHA. This is not a per-satellite fix — it's a fleet-wide control in autom8y-workflows. Any satellite NOT yet pinned to `cbc3c58e` is still exposed.

### B. `autom8y_workflows_sha` input staleness

**Surface**: `test.yml:79`
```yaml
autom8y_workflows_sha: c88caabd8d9bba883e6a42628bdc2bba6d30512b
```

This SHA is 7 commits stale vs. the `@ref` pin (`cbc3c58e`). The `autom8y_workflows_sha` input is used exclusively by the `conformance-gate` job to checkout autom8y-workflows at the caller's pinned SHA (`satellite-ci-reusable.yml:1055-1061`). Since `fleet-conformance-spec.yml` was last modified at commit `0fb7b75` (before both SHAs), the functional impact is zero — the spec is identical at both SHAs. However, the structural invariant (input SHA == @ref SHA) is violated.

### C. uv constraints — Python packages

From `pyproject.toml`:
- `hypothesis>=6.151.12` — lower-bounded only; upper float. Locked to `6.151.12` in `uv.lock:1187` (pinned via lockfile).
- `schemathesis>=4.11.0,<4.15.0` — upper-bounded (4.15.0 ceiling). Explicit version ceiling present.
- `pytest-split>=0.9.0`, `pytest-asyncio>=1.3.0`, `respx>=0.22.0`, `slowapi>=0.1.9` — all lower-bounded only; upper float. Locked in uv.lock.

**uv.lock is present** — all Python dependencies are effectively pinned at lockfile resolution time. Float in `pyproject.toml` constraints is the DECLARED range; actual version is deterministic via lockfile. This is the correct pattern.

### D. Action versions — setup-uv version skew

Three different SHAs for `astral-sh/setup-uv` across inline workflows:
- `38f3f104447c67c051c4a08e39b64a148898af3a` (v4): `aegis-synthetic-coverage.yml:40`, `durations-refresh.yml:36`, `post-merge-coverage.yml:43`
- `6b9c6063abd6010835644d4c2e1bef4cf5cd0fca` (v6): `test.yml:130` (fuzz job), `test.yml:245` (workflow-handler job)
- `08807647e7069bb48b6ef5acd8ec9567f424441b` (v8.1.0): used exclusively inside `satellite-ci-reusable.yml` (not directly in this repo's files)

Two different SHAs for `aws-actions/configure-aws-credentials` (all v4 tag, different patch SHAs):
- `7474bc4690e29a8392af63c5b98e7449536d5c3a`: `aegis-synthetic-coverage.yml:43`, `post-merge-coverage.yml:46`
- `e3dd6a429d7300a6a4c196c26e071d42e0343502`: `durations-refresh.yml:42`, `test.yml:117` (fuzz), `test.yml:232` (workflow-handler)

### E. Dockerfile base images

Base images are SHA-pinned (correct pattern):
- `python:3.12-slim@sha256:5072b08...` (`Dockerfile:60`, `Dockerfile:94`) — same SHA used in both builder and runtime stages
- `amazonlinux:2023-minimal@sha256:ab55495...` (`Dockerfile:44`) — secrets-extension stage
- `astral-sh/uv:latest@sha256:5164bf8...` (`Dockerfile:63`) — uv binary copy

`uv:latest@sha256:5164bf8...` uses the `latest` tag pointer but is SHA-pinned. The `latest` tag is irrelevant when a digest is specified. This is correct.

### F. Renovate configuration

`renovate.json` extends `github>autom8y/autom8y-workflows` (fleet-level config) and enables `github-actions` and `pep621` managers. `autom8y/autom8y` is in `ignoreDeps`. There is no fleet-level alert for "transitive major version change" — Renovate tracks direct dependencies only. The spectral-rulesets issue would NOT have been surfaced by Renovate because the transitive pin was inside `npm install -g`, not in a tracked manifest.

---

## 8. xdist Quarantine Pattern (ASSESS-5)

### Surfaces: `test.yml:61-64`, `test.yml:206-262`, `pyproject.toml:112`

**Quarantine mechanism** (two-part):

Part 1 — exclusion from main gate (`test.yml:64`):
```yaml
test_markers_exclude: ${{ github.event_name == 'pull_request' && 'not integration and not benchmark and not slow and not fuzz and not worker_isolated' || 'not integration and not benchmark and not fuzz and not worker_isolated' }}
```
`worker_isolated` is excluded from the sharded gate on BOTH PR and main/push.

Part 2 — isolated non-blocking job (`test.yml:206-262`):
```yaml
workflow-handler-isolated:
  continue-on-error: true    # test.yml:216
  timeout-minutes: 15         # test.yml:218
  # runs: pytest tests/unit/lambda_handlers/test_workflow_handler.py
  #        -p no:xdist -o addopts="" -v --no-header
```

**Observability blind spot**: A genuine warm-container-reregistration regression would now run non-blocking in `workflow-handler-isolated`. If it fails, the job is marked green by `continue-on-error: true`. There is no alerting on `continue-on-error` job failures.

**Root cause** (from `pyproject.toml:112`): `asyncio.run inside handler-style code under xdist` — the nested-event-loop SIGKILL pattern. The quarantine comment says "Remove when the production handler / test harness drops the nested-loop pattern."

**Promotion-from-quarantine criteria**: Not formalized anywhere in the codebase. No issue/ticket reference. This is indefinite quarantine.

---

## 9. Cross-Repo Artifact Dependency (ASSESS-6)

### Surface: `test.yml:151-180` (fuzz job)

When `inputs.candidate_wheel_run_id != ''` (consumer-gate dispatch mode), the fuzz job downloads `candidate-wheel` artifact from `autom8y/autom8y` run-id provided by the consumer-gate dispatch. If the upstream artifact is not found (e.g., the upstream run failed or the run-id is stale), the job exits 1 at `test.yml:172-174`.

**Artifact name mismatch**:
- `satellite-ci-reusable.yml:300`: `consumer-gate-wheel-${{ inputs.candidate_sdk_name }}-${{ github.event.repository.name }}`
- `test.yml:154` (fuzz job): `candidate-wheel`

The fuzz job in `test.yml` is a STANDALONE job, NOT routed through `satellite-ci-reusable.yml`. It uses its own artifact download with a different artifact name than the reusable workflow uses. The `sdk-publish-v2.yml` uploads `consumer-gate-wheel-{sdk}-{satellite}`, NOT `candidate-wheel`. The fuzz job's artifact download would always fail in consumer-gate dispatch mode unless a separate `candidate-wheel` artifact is uploaded by the upstream workflow.

---

## 10. Dead Code Inventory

No `if: false` jobs found across all workflow files. No commented-out step blocks found. No deprecated trigger syntax.

**Minor notes**:
- `scorecard.yml:8-9`: Comment explains intentional absence of workflow-level permissions (documentation of required OSSF Scorecard pattern, not dead code).
- `durations-refresh.yml:86-103`: `open-refresh-PR` step uses `if: steps.diff.outputs.changed == 'true'` — correct conditional, not dead code.

---

## 11. Safety Configuration Audit

### Timeout Coverage

| Workflow | Job | timeout-minutes | Notes |
|---|---|---|---|
| `test.yml` | ci (satellite-ci-reusable) | delegated (default 20; overridden: `test_timeout: 40`) | OK |
| `test.yml` | fuzz | 15 | OK |
| `test.yml` | workflow-handler-isolated | 15 | OK |
| `test.yml` | fleet-schema-governance | 5 | OK |
| `post-merge-coverage.yml` | coverage | 25 | OK |
| `aegis-synthetic-coverage.yml` | aegis | 15 | OK |
| `satellite-dispatch.yml` | dispatch | 5 | OK |
| `durations-refresh.yml` | refresh | 25 | OK |
| `dockerfile-lint.yml` | hadolint, m16-pattern-assert | NONE | MISSING |
| `dependency-review.yml` | dependency-review | delegated | Unknown (reusable) |
| `gitleaks.yml` | gitleaks | delegated | Unknown (reusable) |
| `scorecard.yml` | scorecard | delegated | Unknown (reusable) |
| `trufflehog-scan.yml` | trufflehog | delegated | Unknown (reusable) |
| `zizmor.yml` | zizmor | delegated | Unknown (reusable) |

**Timeout coverage**: 8/14 jobs have explicit `timeout-minutes` (57%). `dockerfile-lint.yml` jobs have no timeout (MISSING). 5 jobs delegate to reusable workflows.

### Concurrency Coverage

| Workflow | concurrency | cancel-in-progress |
|---|---|---|
| `test.yml` | `test-${{ github.ref }}` | true |
| `post-merge-coverage.yml` | `post-merge-coverage-${{ github.ref }}` | false (intentional) |
| `aegis-synthetic-coverage.yml` | `aegis-${{ github.ref }}` | true |
| `gitleaks.yml` | `gitleaks-${{ github.ref }}` | true |
| `durations-refresh.yml` | `durations-refresh-${{ github.ref }}` | true |
| `satellite-dispatch.yml` | NONE | N/A |
| `scorecard.yml` | NONE | N/A (scheduled, once/week) |
| `trufflehog-scan.yml` | NONE | N/A (scheduled, once/week) |
| `dockerfile-lint.yml` | NONE | N/A (path-filtered) |
| `dependency-review.yml` | NONE | N/A (PR-only) |
| `zizmor.yml` | NONE | N/A (path-filtered) |

**Concurrency coverage**: 5/11 workflows have explicit concurrency groups (45%). Omissions are defensible for single-trigger or path-filtered workflows.

### Permissions Coverage

| Workflow | Workflow-level permissions | Notes |
|---|---|---|
| `test.yml` | NONE | Jobs scope individually: `id-token: write; contents: read` |
| `post-merge-coverage.yml` | NONE | Job: `id-token: write; contents: read` |
| `aegis-synthetic-coverage.yml` | NONE | Job: `id-token: write; contents: read` |
| `satellite-dispatch.yml` | `permissions: {}` | Correct — zero workflow-level |
| `gitleaks.yml` | `contents: read; security-events: write` | Correct |
| `dockerfile-lint.yml` | `contents: read` | Correct |
| `scorecard.yml` | NONE (intentional, see comment) | Job scopes individually |
| `trufflehog-scan.yml` | NONE | Delegates to reusable |
| `dependency-review.yml` | NONE | Delegates to reusable |
| `zizmor.yml` | `contents: read; security-events: write` | Correct |
| `durations-refresh.yml` | NONE | Job: `id-token: write; contents: write; pull-requests: write` |

**Workflows with workflow-level permissions block**: 4/11 (36%). `test.yml`, `post-merge-coverage.yml`, `aegis-synthetic-coverage.yml`, `durations-refresh.yml`, `trufflehog-scan.yml` have no workflow-level `permissions:` block — GitHub defaults to `write-all` at workflow level when omitted. Jobs within those workflows do scope individually, but the absence of a workflow-level restriction is a defense-in-depth gap.

**`continue-on-error` usage**:
- `test.yml:87` (fuzz job): `continue-on-error: true` — intentional non-blocking signal
- `test.yml:216` (workflow-handler-isolated): `continue-on-error: true` — quarantine pattern, documented
- `satellite-ci-reusable.yml:666` (integration job): `continue-on-error: true` — advisory-only integration tests

---

## 12. Version Skew Report

### Reusable workflow call-site SHAs

| Caller | Called workflow | @ref SHA | SHA comment |
|---|---|---|---|
| `test.yml:45` | `satellite-ci-reusable.yml` | `cbc3c58e56f3e0adeaf57101c0400d8f5d7845ed` | origin/main HEAD |
| `dependency-review.yml:9` | `security-dependency-review.yml` | `44b771e516a49a0d964782e4bbd0f0e39b2f97a1` | grouped with 3 others |
| `gitleaks.yml:19` | `security-gitleaks.yml` | `44b771e516a49a0d964782e4bbd0f0e39b2f97a1` | same |
| `trufflehog-scan.yml:10` | `security-trufflehog.yml` | `44b771e516a49a0d964782e4bbd0f0e39b2f97a1` | same |
| `zizmor.yml:19` | `security-zizmor.yml` | `44b771e516a49a0d964782e4bbd0f0e39b2f97a1` | same |
| `scorecard.yml:21` | `security-scorecard.yml` | `c77acb0cf9e48b17f08180d54e24086016706856` | **DIFFERENT SHA** from security peers |

**scorecard.yml pins a different SHA** than the 4 security peer workflows. May be intentional (scorecard has different update cadence) but is undocumented.

### Action version skew within inline workflows

**`astral-sh/setup-uv`** — 2 distinct SHAs:
- `38f3f104447c67c051c4a08e39b64a148898af3a` (v4): `aegis-synthetic-coverage.yml:40`, `durations-refresh.yml:36`, `post-merge-coverage.yml:43`
- `6b9c6063abd6010835644d4c2e1bef4cf5cd0fca` (v6): `test.yml:130`, `test.yml:245`

**`aws-actions/configure-aws-credentials`** — 2 distinct SHAs (both tagged v4):
- `7474bc4690e29a8392af63c5b98e7449536d5c3a`: `aegis-synthetic-coverage.yml:43`, `post-merge-coverage.yml:46`
- `e3dd6a429d7300a6a4c196c26e071d42e0343502`: `durations-refresh.yml:42`, `test.yml:117`, `test.yml:232`

**`autom8y_workflows_sha` input vs @ref mismatch** (`test.yml:45,79`):
- @ref pin: `cbc3c58e` (correct: origin/main HEAD)
- `autom8y_workflows_sha` input: `c88caabd` (stale: 7 commits behind, PR #11)
- Functional impact: zero (`fleet-conformance-spec.yml` unchanged between the two SHAs)
- Structural integrity: violated (input should match @ref)

---

## 13. Stub / Dependency Consistency Analysis

**SCAR-PC-004 (api-schemas-stub)**: The `api-schemas-stub` composite action at `autom8y/.github/actions/api-schemas-stub/action.yml` is the canonical fleet-wide stub for `autom8y-api-schemas`. It is consumed by `sdk-publish-v2.yml:572` via `uses: ./.github/actions/api-schemas-stub`. The autom8y-asana repo does NOT independently maintain a stub — it uses `--no-sources` in uv commands to bypass the `[tool.uv.sources]` monorepo-relative path overrides. **No SCAR-PC-004 pattern detected in this satellite.**

**`validate-env-injection` composite action**: defined at `.github/actions/validate-env-injection/action.yml:37`, consumed by `satellite-ci-reusable.yml:471-474` (test job env injection) and `satellite-ci-reusable.yml:730-734` (convention-check). Extraction pattern working correctly — no inline duplication detected.

---

## 14. Duplication Analysis

**SCAR-PC-002 — setup sequence duplication** across inline workflows:

The 5-step pattern `checkout -> setup-python -> setup-uv -> configure-aws-credentials -> get-codeartifact-token` appears inline in:
1. `post-merge-coverage.yml:37-57`
2. `aegis-synthetic-coverage.yml:34-54`
3. `durations-refresh.yml:30-53` (with extra uv env step)
4. `test.yml:95-131` (fuzz job)
5. `test.yml:223-250` (workflow-handler-isolated job)

The `ci` job in `test.yml` correctly uses the reusable workflow. The 4 other inline jobs maintain independent copies.

**Total inline duplications of the AWS+uv setup sequence**: 5 occurrences across 4 files. The `satellite-ci-reusable.yml` already extracts this for the main `ci` job but the other 4 jobs do not benefit.

**Similarity matrix** (high confidence, structurally identical):
- `post-merge-coverage.yml:37-57` vs `aegis-synthetic-coverage.yml:34-54`: near-identical (same actions, same configure-aws-credentials SHA, different setup-uv SHA)
- `test.yml:95-131` (fuzz) vs `test.yml:223-250` (workflow-handler-isolated): structurally identical setup blocks within same file

**SCAR-PC-001 — env block duplication**: No `TF_VAR_*` blocks detected (not a Terraform repo). Not applicable.

---

## 15. Reusable Workflow Utilization

| Component | Status | Consumers |
|---|---|---|
| `satellite-ci-reusable.yml` | Correctly used | `test.yml:45` (ci job) |
| `validate-env-injection` composite | Correctly used | `satellite-ci-reusable.yml:471,731` |
| `fleet-conformance-gate` composite | Correctly used | `satellite-ci-reusable.yml:1064` |
| `security-gitleaks.yml` | Correctly delegated | `gitleaks.yml:19` |
| `security-dependency-review.yml` | Correctly delegated | `dependency-review.yml:9` |
| `security-scorecard.yml` | Correctly delegated | `scorecard.yml:21` |
| `security-trufflehog.yml` | Correctly delegated | `trufflehog-scan.yml:10` |
| `security-zizmor.yml` | Correctly delegated | `zizmor.yml:19` |

**Underutilization (SCAR-PC-005)**: `post-merge-coverage.yml`, `aegis-synthetic-coverage.yml`, `durations-refresh.yml`, `test.yml/fuzz`, `test.yml/workflow-handler-isolated` all implement the AWS+uv setup sequence inline rather than via a composite action. No composite action exists in `.github/actions/` for this setup sequence.

---

## 16. Agent-Provenance Signals

- **`test.yml` append-only growth**: The file has grown from the original `ci` job wrapper to include `fuzz`, `workflow-handler-isolated`, and `fleet-schema-governance` jobs. Each is separately motivated. Growth is organic.
- **Comment density is HIGH**: Extensive inline documentation of rationale for non-obvious choices (xdist quarantine, credential path, worker cap). Positive signal but indicates opacity without comments.
- **`autom8y_workflows_sha` staleness**: The SHA input was set at PR #24 (commit `58945166`) and not updated when the reusable workflow was re-pinned in PR #64 (commit `6700c9d8`). The re-pin updated the `@ref` but not the input SHA. Recurring pattern.

---

## 17. Raw Metrics

| Metric | Value |
|---|---|
| Workflow file count | 11 |
| Total workflow lines | 800 |
| Composite action count | 2 |
| Reusable workflow call sites | 6 |
| Jobs with explicit timeout | 8/14 (57%) |
| Workflows with explicit concurrency | 5/11 (45%) |
| Workflows with workflow-level permissions block | 4/11 (36%) |
| continue-on-error jobs | 3 (fuzz, workflow-handler-isolated, integration in reusable) |
| Action version skew (setup-uv) | 2 distinct SHAs across inline workflows (v4 vs v6) |
| Action version skew (configure-aws-credentials) | 2 distinct SHAs across inline workflows (both v4 tag) |
| Reusable workflow SHA skew count | 1 (scorecard vs 4 security peers) |
| autom8y_workflows_sha staleness | 7 commits behind @ref pin (functional impact: zero) |
| Trivy exemptions past review date | 4/4 time-boxed exemptions expired (UV-P) |
| Inline setup-sequence duplications | 5 instances across 4 files |
| Dead jobs (if: false) | 0 |
| Commented-out steps | 0 |
| Fuzz artifact name mismatch | 1 (candidate-wheel vs consumer-gate-wheel-{sdk}-{satellite}) |
| slow tests absent from PR gate | 23 tests |
| Branch protection enforce_admins | false (admin bypass allowed) |

---

## 18. ASSESS-N Surface Map

| ASSESS-N | Surface File:Line | In-repo or UV-P |
|---|---|---|
| ASSESS-1 (PR vs main test gap) | `test.yml:64` (slow marker excluded from PR); `satellite-ci-reusable.yml:319-331` (lint runs identically — no asymmetry there) | IN-REPO: `test.yml:64` |
| ASSESS-2 (Trivy CVE-acceptance cadence) | `autom8y/.github/workflows/service-build.yml:259-325`; `autom8y/.trivyignore:1-86` | UV-P — autom8y monorepo |
| ASSESS-3 (Consumer-gate false-negatives) | `autom8y/.github/workflows/sdk-publish-v2.yml:533-538,690-697` | UV-P — autom8y monorepo |
| ASSESS-4 (Floating deps) | `test.yml:79` (autom8y_workflows_sha stale); `aegis-synthetic-coverage.yml:40`, `post-merge-coverage.yml:43`, `durations-refresh.yml:36` (setup-uv v4); `test.yml:130,245` (setup-uv v6) | IN-REPO: SHA sync + action version alignment |
| ASSESS-5 (xdist quarantine) | `test.yml:61-64,206-262`; `pyproject.toml:112` | IN-REPO: CI structure is correct containment; root fix requires production handler code change |
| ASSESS-6 (Cross-repo artifact) | `test.yml:154` (artifact name `candidate-wheel` vs `consumer-gate-wheel-{sdk}-{satellite}` at `satellite-ci-reusable.yml:300`) | IN-REPO: fix artifact name in fuzz job |
| ASSESS-7 (Branch protection) | Branch protection API: `enforce_admins: false`; `required_approving_review_count: 0` | IN-REPO: GitHub repo settings |
| ASSESS-8 (Commit hook UX) | `.claude/settings.local.json:92-97` (git-conventions + attribution-guard hooks via `ari hook`) | IN-REPO: ari hook configuration (out of CI scope) |
| ASSESS-9 (Deploy-chain observability) | `satellite-dispatch.yml:17-21` (gate logic correct); observability gap = no alerting on Actions failures | UV-P: alerting infrastructure at autom8y monorepo level |
| ASSESS-10 (Test-result scope opacity) | `test.yml:64` (slow exclusion not surfaced in CI status); branch protection required checks list | IN-REPO: CI output transparency |

---

## Handoff Criteria Checklist

- [x] INVENTORY written to `.sos/wip/eunomia/pipeline-inventory-2026-06-01.md`
- [x] All sections populated or marked not-applicable
- [x] Raw metrics table has numeric values for all applicable metrics
- [x] Duplication analysis includes specific file pairs and block locations
- [x] Safety audit reports per-dimension coverage percentages
- [x] No scan areas flagged as incomplete
- [x] Version skew report includes specific file:line anchors
- [x] ASSESS-N surface map with file:line for every item
