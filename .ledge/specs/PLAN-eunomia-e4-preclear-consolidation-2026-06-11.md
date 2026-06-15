---
type: spec
status: accepted
station: E4 (rationalization-executor)
rite: eunomia
procession: Pre-Clear External Corroboration & Governance Custody
authored: 2026-06-11
inputs:
  - .ledge/reviews/EUNOMIA-E3-grades-and-custody-2026-06-11.md
  - .ledge/reviews/EUNOMIA-E2a-test-surface-inventory-2026-06-11.md
  - .ledge/reviews/EUNOMIA-E2b-pipeline-inventory-2026-06-11.md
scan_anchors:
  autom8y_asana_e2_base: 49099b12   # E2 scan base
  autom8y_asana_current_main: fa265ce1  # origin/main at E4 execution time (PR #131 pyjwt CVE)
  autom8y_monorepo_main: c8c397f2
  autom8y_workflows_main: f5601acb
pv_clock_at_plan_time:
  asana_main_sha: fa265ce1bde8be1d003f39501877d17fe600b0c0
  ecs_deployment: "arn:aws:ecs:us-east-1:696318035277:task-definition/autom8y-asana-service:512 COMPLETED (sole)"
grandeur_anchor: >
  We corroborate, rite-disjoint and BEFORE the clock needs us — burning the C-grade
  CI debt on merge-safe surfaces WITHOUT EVER ROLLING AN ASANA TASK-DEF; the clock
  and anything that resets it stays the operator's.
---

# PLAN — Eunomia E4 Pre-Clear Consolidation — 2026-06-11

## Overview

E3 directive: overall grade C driven by weakest link CI pin/version hygiene.
Eight atomic changes across two waves. Wave A executes and merges in the autom8y
monorepo (merge-safe per workflow_call-only trigger receipts). Wave B authors a
held PR against autom8y-asana origin/main; NEVER merged until soak-clear 06-18.

Execution order: CHANGE-E4-001, CHANGE-E4-002 (Wave A, one PR); then
CHANGE-E4-003 through CHANGE-E4-008 (Wave B, one held PR, one commit each).

---

## SHA Verification Record (all 6 Wave A target SHAs confirmed node24)

| Action | Target SHA | Verified node era | Method |
|--------|-----------|-------------------|--------|
| actions/checkout | 93cb6efe18208431cddfb8368fd83d5badbf9bfd | node24 | gh api contents/action.yml?ref= → `using: node24` |
| aws-actions/configure-aws-credentials | e7f100cf4c008499ea8adda475de1042d6975c7b | node24 | gh api contents/action.yml?ref= → `using: node24` |
| astral-sh/setup-uv | 08807647e7069bb48b6ef5acd8ec9567f424441b | node24 | gh api contents/action.yml?ref= → `using: "node24"` |
| hashicorp/setup-terraform | dfe3c3f8fa80bc64e22b3e6e69ba21e18e90faed | node24 | gh api contents/action.yml?ref= → `using: 'node24'` |
| actions/upload-artifact | b7c566a772e6b6bfb58ed0dc250532a479d7789f | node24 | gh api contents/action.yml?ref= → `using: node24` |
| actions/create-github-app-token | bcd2ba49f89f0ab7b30ce7e9f4fa0c79b79bf6c7 | node24 | gh api contents/action.yml?ref= → `using: "node24"` |

**Note on short SHA vs full SHA**: The verified SHAs above are the full 40-char SHAs.
The E2b/E3 documents used short SHAs (e.g. `e7f100cf`). The apply-reusable file uses
full 40-char SHAs for pins (e.g. `7474bc4690e29a8392af63c5b98e7449536d5c3a`).
The change replaces with the full SHA forms from terraform-plan-reusable.yml as
canonical source (it already carries the node24 set).

---

## Wave A — autom8y monorepo (merge-safe-now, EXECUTE + MERGE under grant)

### CHANGE-E4-001

**File**: `autom8y/.github/workflows/terraform-apply-reusable.yml`
**Type**: pin-bump
**Risk class**: LOW — workflow_call-only; cannot self-fire; chain idle during freeze
**E3 anchor**: E2b#1 HIGH — 2026-06-16 node20 brownout deadline
**Dependency**: none

**Change specification** (six pins, one file):

| Step | Current SHA (node20) | Target SHA (node24) | Action |
|------|---------------------|---------------------|--------|
| Checkout | `34e114876b0b11c390a56381ad16ebd13914f8d5` # v4 | `93cb6efe18208431cddfb8368fd83d5badbf9bfd` # v5.0.1 (node24) | actions/checkout |
| Configure AWS credentials | `7474bc4690e29a8392af63c5b98e7449536d5c3a` # v4 | `e7f100cf4c008499ea8adda475de1042d6975c7b` # v6.2.0 (node24) | aws-actions/configure-aws-credentials |
| Setup uv | `38f3f104447c67c051c4a08e39b64a148898af3a` # v4 | `08807647e7069bb48b6ef5acd8ec9567f424441b` # v8.1.0 (node24) | astral-sh/setup-uv |
| Setup Terraform | `b9cd54a3c349d3f38e8881555d616ced269862dd` # v3 | `dfe3c3f8fa80bc64e22b3e6e69ba21e18e90faed` # v4.0.1 (node24) | hashicorp/setup-terraform |
| Upload Outputs Artifact | `ea165f8d65b6e75b540449e92b4886f43607fa02` # v4 | `b7c566a772e6b6bfb58ed0dc250532a479d7789f` # v6.0.0 (node24) | actions/upload-artifact |
| Generate token | `d72941d797fd3113feb6b93fd0dec494b13a2547` # v1 | `bcd2ba49f89f0ab7b30ce7e9f4fa0c79b79bf6c7` # v3.2.0 (node24) | actions/create-github-app-token |

**Pins NOT changed** (already node24 or composite action — no era upgrade needed):
- `extractions/setup-just@dd310ad5a97d8e7b41793f8ef055398d51ad4de6 # v2` — composite action (not node-era-dependent); left as-is per plan scope (only node20-era bumps)
- `mikefarah/yq@5a7e72a743649b1b3a47d1a1d8214f3453173c51 # v4` — composite action; left as-is
- `actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830 # v4` — node24-era cache (v4 is fine, not the brownout v3); left as-is

**Verification**: `actionlint` if available; CI lint job on the PR; no apply fires.
**Commit message**: `ci(tf-apply): bump 6 node20 pins to node24 [CHANGE-E4-001]`

---

### CHANGE-E4-002

**File**: `autom8y/.github/workflows/service-terraform.yml`
**Type**: pin-bump
**Risk class**: LOW — detect job only; same node20→node24 class as E4-001
**E3 anchor**: E2b#2 MED — detect-job checkout skew within orchestrating workflow
**Dependency**: CHANGE-E4-001 (same PR, second commit)

**Change specification** (one pin, one file):

| Step | Current SHA (node20) | Target SHA (node24) | Action |
|------|---------------------|---------------------|--------|
| Checkout (detect job) | `34e114876b0b11c390a56381ad16ebd13914f8d5` # v4 | `93cb6efe18208431cddfb8368fd83d5badbf9bfd` # v5.0.1 (node24) | actions/checkout |

**Other pins in service-terraform.yml at scan time**:
- `mikefarah/yq@5a7e72a743649b1b3a47d1a1d8214f3453173c51` — composite action; not changed

**Verification**: same as E4-001 (same PR).
**Commit message**: `ci(tf-apply): bump service-terraform detect checkout to node24 [CHANGE-E4-002]`

**Wave A PR**: one PR, two commits (E4-001 first, E4-002 second), branch
`eunomia/e4-node24-tf-apply-pins`, target `main` on autom8y monorepo.
**Trigger receipts in PR body** (required):
- terraform-apply-reusable.yml `on: workflow_call` only — merging fires nothing.
- service-terraform.yml triggers: pull_request, merge_group, push/main (paths: terraform/services/**, terraform/modules/**, terraform/shared/**, terraform/workflows/**, services.yaml). The PR's changed files are `.github/workflows/` only — no overlap with trigger paths — cannot self-fire a deploy.

---

## Wave B — autom8y-asana (ONE held PR, NEVER merged)

Worktree base: origin/main `fa265ce1` (current HEAD; includes PR #131 pyjwt CVE bump
which advanced from the E2 scan base `49099b12`; the workflow files being changed
are unaffected by the pyjwt bump — identical between the two SHAs).

Branch: `eunomia/e4-preclear-consolidation`
PR target: autom8y/autom8y-asana `main`
MERGE-FROZEN label: mandatory in PR body.

---

### CHANGE-E4-003

**File**: `tests/integration/test_workspace_switching.py`
**Type**: delete
**Risk class**: LOW — 8/8 dead-skip skeleton, zero coverage contribution, no imports
**E3 anchor**: E2a F-1 MEDIUM — 100% dead-test file
**Dependency**: none
**Precondition**: verify no file imports `test_workspace_switching` (grep confirmed: none)

**Verification**: `uv run --no-sync pytest tests/integration/ -x -o addopts="" -o asyncio_mode=auto -p no:cacheprovider` from worktree root (integration suite must pass).
**Commit message**: `eunomia(delete): remove 100% dead-skip workspace switching skeleton [CHANGE-E4-003]`

---

### CHANGE-E4-004

**File**: `tests/unit/api/test_routes_query_project_section_rows_sprint2.py`
**Type**: rename → `tests/unit/api/test_routes_query_rows_body_parameterized.py`
**Risk class**: LOW — no cross-imports; fixture name `register_project_gids_sprint2` stays intact inside file; sibling files reference it only in doc strings (not via import)
**E3 anchor**: E2a F-2 MEDIUM — sprint-tagged epoch filename
**Dependency**: CHANGE-E4-003 (sequential; both test surface)

**Rename mechanics**:
- `git mv` the file (preserves git history)
- No content changes needed (the fixture `register_project_gids_sprint2` lives inside the file and pytest discovers it by content, not filename)
- Verify: `grep -r "test_routes_query_project_section_rows_sprint2" tests/` returns only the two sibling doc-string references (not import statements)

**Verification**: `uv run --no-sync pytest tests/unit/api/test_routes_query_rows_body_parameterized.py tests/unit/api/test_routes_query_body_parameterized_build_on_miss.py tests/unit/api/test_routes_query_body_parameterized_unregistered.py -x -o addopts="" -o asyncio_mode=auto -p no:cacheprovider`
**Commit message**: `eunomia(rename): rename sprint2 epoch file to feature-describing name [CHANGE-E4-004]`

---

### CHANGE-E4-005

**File**: `.github/workflows/post-merge-coverage.yml`
**Type**: add key to upload-artifact step
**Risk class**: LOW — purely additive; fixes silent hollow artifact (gate correctness unaffected)
**E3 anchor**: E2b#4 LOW-MED — post-merge-coverage.yml .coverage upload missing include-hidden-files
**Dependency**: none (CI-only change)

**Change specification**:
In the "Upload coverage artifact" step (currently line 92), add `include-hidden-files: true` to the `with:` block alongside `name:`, `path:`, `if-no-files-found:`, `retention-days:`.

**Verification**: CI actionlint on PR.
**Commit message**: `eunomia(ci): add include-hidden-files to post-merge coverage upload [CHANGE-E4-005]`

---

### CHANGE-E4-006

**File**: `.github/workflows/test.yml`
**Type**: pin-bump
**Risk class**: LOW — reusable workflow pin bump; f5601acb verified present on autom8y-workflows main
**E3 anchor**: E2b#5 LOW — satellite-ci-reusable one rev behind (missing --all-extras fix)
**Dependency**: none

**Change specification**:
Line 51: `satellite-ci-reusable.yml@93dbbc2933affcce3e692ccff8f17d382811264d`
→ `satellite-ci-reusable.yml@f5601acbe3905270dfcb9069854c78c0f940ad05`

Line 44 comment: update PR number reference from `#25` to `#27` to reflect the new SHA.
Line 88 `autom8y_workflows_sha:` input: update from `93dbbc2933affcce3e692ccff8f17d382811264d` to `f5601acbe3905270dfcb9069854c78c0f940ad05`.

**Verification**: CI on the PR (the full test suite runs against the new pin).
**Commit message**: `eunomia(ci): bump satellite-ci-reusable pin to f5601acb [CHANGE-E4-006]`

---

### CHANGE-E4-007

**Files**: `.github/workflows/aegis-synthetic-coverage.yml`, `.github/workflows/durations-refresh.yml`, `.github/workflows/post-merge-coverage.yml`
**Type**: retry hardening (CodeArtifact token fetch)
**Risk class**: LOW — surgical behavioral change to a known-flaky network call; identical to the nightly-live-smoke.yml pattern already running in production
**E3 anchor**: E2b#6 LOW — CodeArtifact simple-fetch ×3 vs hardened retry pattern
**Dependency**: CHANGE-E4-005 (post-merge-coverage already modified; this amends it in a separate commit)

**Change specification** (canonical retry pattern from nightly-live-smoke.yml):

Replace the simple "Get CodeArtifact token" step in each of the three files:

```yaml
# BEFORE (simple, no retry):
- name: Get CodeArtifact token
  run: |
    TOKEN=$(aws codeartifact get-authorization-token \
      --domain autom8y \
      --query authorizationToken \
      --output text)
    echo "CODEARTIFACT_AUTH_TOKEN=$TOKEN" >> "$GITHUB_ENV"
```

With the hardened retry pattern (verbatim from nightly-live-smoke.yml lines 105-121):

```yaml
- name: Login to CodeArtifact
  run: |
    CODEARTIFACT_AUTH_TOKEN=""
    for attempt in 1 2 3; do
      if CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
        --domain autom8y --domain-owner 696318035277 \
        --query authorizationToken --output text \
        --cli-connect-timeout 15 --cli-read-timeout 30) && [ -n "$CODEARTIFACT_AUTH_TOKEN" ]; then
        break
      fi
      echo "::warning::CodeArtifact get-authorization-token attempt ${attempt}/3 failed (connect/read timeout or empty token) — retrying in 5s"
      CODEARTIFACT_AUTH_TOKEN=""
      [ "$attempt" -lt 3 ] && sleep 5
    done
    if [ -z "$CODEARTIFACT_AUTH_TOKEN" ]; then
      echo "::error::CodeArtifact get-authorization-token FAILED after 3 attempts — CodeArtifact unreachable or token empty"
      exit 1
    fi
    export CODEARTIFACT_AUTH_TOKEN
    echo "CODEARTIFACT_AUTH_TOKEN=$CODEARTIFACT_AUTH_TOKEN" >> "$GITHUB_ENV"
```

**Note on aegis-synthetic-coverage.yml**: it sets `UV_INDEX_AUTOM8Y_PASSWORD` from the env var in the next step inline; keep that downstream step unchanged. The hardened step writes `CODEARTIFACT_AUTH_TOKEN` to `$GITHUB_ENV`; the downstream usage pattern is compatible.

**Note on durations-refresh.yml**: it currently splits token-fetch and `UV_INDEX_AUTOM8Y_PASSWORD` export into two separate steps. Collapse into the hardened single step that writes `CODEARTIFACT_AUTH_TOKEN` to `$GITHUB_ENV` and remove the now-redundant "Configure uv for CodeArtifact" step.

**Note on post-merge-coverage.yml**: already uses `CODEARTIFACT_AUTH_TOKEN` inline via `${{ env.CODEARTIFACT_AUTH_TOKEN }}` in the install step's env block; the hardened step's `echo "CODEARTIFACT_AUTH_TOKEN=..." >> "$GITHUB_ENV"` is compatible.

**Verification**: CI actionlint + ruff on any touched python (none for this change).
**Commit message**: `eunomia(ci): harden CodeArtifact retry in 3 standalone workflows [CHANGE-E4-007]`

---

### CHANGE-E4-008

**Files**: potentially `tests/integration/cache/conftest.py` (new), `tests/integration/cache/test_warmer_preserve_enforcement.py`, `tests/integration/cache/test_warmer_preserve_serve_altitude.py`
**Type**: extract shared helpers to conftest
**Risk class**: LOW-MEDIUM — behavioral preservation required; skip with rationale if not surgical
**E3 anchor**: E2a F-3/F-4 LOW — _InMemoryStorage/_DegradedBuildStrategy/_frame helpers duplicated
**Dependency**: none

**Feasibility assessment**:
- `_frame`, `_prior_good_frame`, `_degraded_frame`: bodies are identical between both files (same default n_active=3). Extractable cleanly as module-level functions in conftest.py.
- `_DegradedBuildStrategy`: bodies are functionally identical (`__init__` + `_build_dataframe` identical). Docstrings differ but the class itself is extractable.
- `_InMemoryStorage`: enforcement file has `save_dataframe_calls: list[dict]` tracking and adds a call-log in `save_dataframe`; serve_altitude file does NOT. These are NOT identical. Options: (a) use the tracking version for both (serve_altitude tests don't assert `save_dataframe_calls` but the extra field is harmless), or (b) skip extraction with rationale. Option (a) is surgical: the tracking list is additive and carry-cost is zero for tests that don't use it.

**EXECUTE ONLY IF**: all of the following are true:
1. A conftest.py does not already exist in tests/integration/cache/ on the worktree base.
2. The extracted conftest.py contains ONLY the shared helpers (no new fixtures — pytest fixtures in conftest.py have scope implications).
3. Ruff format + check on both modified files passes cleanly.
4. The saga focal integration suite passes: `uv run --no-sync pytest tests/integration/cache/ -x -o addopts="" -o asyncio_mode=auto -p no:cacheprovider`

**SKIP CONDITION**: If extraction of `_InMemoryStorage` requires non-trivial parameterization or the conftest introduces any pytest fixture (which would affect test collection scope), skip this change and document with rationale.

**Commit message**: `eunomia(test): extract shared cache test helpers to integration/cache conftest [CHANGE-E4-008]`

**SKIP RATIONALE (if skipped)**: `_InMemoryStorage` has two structurally distinct variants (with/without save_dataframe_calls tracking); merging them with the tracking variant is additive but the builder unit file's variant (tests/unit/dataframes/builders/test_cure_recovery_fail_closed.py) cannot be included in this cross-tree extraction without introducing awkward import patterns. The E3 directive explicitly guards: "DO NOT force it; skip with a one-line rationale if it grows beyond a clean extraction."

---

## Execution Constraints

- Never stage: `.claude/ .gemini/ .know/ .knossos/ .ledge/ .sos/ .mcp.json .gitignore aegis-report.json uv.lock`
- Edit via Edit tool, never sed
- Wave A commit messages: no Co-Authored-By; subject ≤50 chars, one paren-scope, no em-dash
- Wave B commit messages: `eunomia({type}): {description} [CHANGE-E4-NNN]` format
- Wave B PR: MERGE-FROZEN label, exact operator merge command in body, DO NOT enable auto-merge
- PV-CLOCK before Wave A merge: asana_main_sha check + ECS deployment check

---

## Verification Commands

| Change | Verification | Notes |
|--------|-------------|-------|
| E4-001 | CI on Wave A PR | workflow_call-only; actionlint if available |
| E4-002 | CI on Wave A PR | same PR as E4-001 |
| E4-003 | `uv run --no-sync pytest tests/integration/ -x -o addopts="" -o asyncio_mode=auto -p no:cacheprovider` | run from worktree root |
| E4-004 | `uv run --no-sync pytest tests/unit/api/test_routes_query_rows_body_parameterized.py tests/unit/api/test_routes_query_body_parameterized_build_on_miss.py tests/unit/api/test_routes_query_body_parameterized_unregistered.py -x -o addopts="" -o asyncio_mode=auto -p no:cacheprovider` | rename correctness + sibling integrity |
| E4-005 | CI actionlint on Wave B PR | additive key; no test impact |
| E4-006 | CI on Wave B PR (full test suite runs against new pin) | behavioral parity check |
| E4-007 | CI actionlint on Wave B PR | retry pattern is identical to nightly-live-smoke |
| E4-008 | `uv run --no-sync pytest tests/integration/cache/ -x -o addopts="" -o asyncio_mode=auto -p no:cacheprovider` | if executed; saga focal suites must pass |
