---
domain: release/history
generated_at: "2026-03-15T02:15:00Z"
source_scope:
  - "./.know/release/"
generator: pipeline-monitor
source_hash: "b7c4148"
confidence: 0.90
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 0
---

# Release History

## Log

### 2026-03-15 — autom8y-asana PATCH release (fail-forward, 4 rounds)

- **Repos**: autom8y-asana (+ hotfixes to autom8y/autom8y infra)
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS (after 4 rounds, 3 inline hotfixes)
- **Duration**: ~2 hours (including 4 monitoring cycles + 3 hotfix iterations)
- **Commits released**:
  - c9273d8 — refactor(config): clean-break env var standardization
  - f42bd55 — refactor(config): apply AUTOM8Y_ org prefix to Tier 2 vars
  - b7c4148 — fix(tests): update env var names to match AUTOM8Y_ org prefix refactor
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **Chain timing (final round)**: test 4m 16s (round 2), dispatch 10s, receiver ~36m (2 retries for ECS waiter)
- **ECS deploy**: Rolling deployment, stabilized on retry 2
- **Lambda deploy**: Deployed via Terraform (first clean Lambda deploy after otel sidecar fixes)
- **Run IDs**: test=23099761881, dispatch=23100731610, receiver=23100733658
- **Fail-forward rounds**:
  - Round 1: Stage 1 failed — 13 test failures + ruff format (env vars renamed but tests not updated). Fixed in autom8y-asana.
  - Round 2: Stage 3 failed — Sigstore attestation stored in ECR not GitHub API; Terraform null aws_region. Fixed in autom8y/autom8y.
  - Round 3: Stage 3 failed — Terraform null metrics_path + scrape_interval (same root cause, more fields). Fixed in autom8y/autom8y.
  - Round 4: PASS — all 5 Satellite Receiver jobs green on retry 2.
- **Infra fixes (autom8y/autom8y)**:
  - 1686047 — fix(deploy): remove push-to-registry from attestation, add aws_region to asana otel config
  - 7d407b4 — fix(terraform): supply all optional otel sidecar fields (metrics_path, scrape_interval, collector_cpu, collector_memory)
- **Notable**: First release after AUTOM8Y_ org prefix env var standardization. ECS ServicesStable waiter timeout is a recurring transient issue (~50% of attempts). Attestation now stored on GitHub API instead of ECR. Force-with-lease used on autom8y/autom8y — remote commit 498949c may need re-application.

### 2026-03-03 (4) — autom8y-asana HOTFIX release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS (after 1 retry)
- **Duration**: ~20 min (including retry)
- **Commit released**: 394d61c — fix(cascade): add parent_gid case to DataFrameViewPlugin derived field extraction
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **Chain timing**: test 3m 50s, dispatch 13s, receiver attempt 1 failed (2m 31s), receiver attempt 2 green (~9m)
- **ECS deploy**: Rolling deployment, smoke test passed (attempt 2)
- **Run IDs**: test=22637797551, dispatch=22637942164, receiver=22637949056 (attempt 2)
- **Retry**: satellite-receiver.yml failed on transient Sigstore attestation 401 (attempt 1). Rerun via `gh run rerun --failed` succeeded on attempt 2.
- **Notable**: 4th release of the day. Sigstore flakiness flagged as SRE-scope concern. Recon skipped via cached platform profile.

### 2026-03-03 (3) — autom8y-asana P0 HOTFIX release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS
- **Duration**: 12m 21s (chain only)
- **Commit released**: a24311a — fix(cascade): use put_batch_async for gap warming instead of warm_ancestors
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **Chain timing**: test 3m 54s, dispatch 7s, receiver 8m 17s
- **ECS deploy**: Rolling deployment, smoke test passed
- **Run IDs**: test=22636195393, dispatch=22636346659, receiver=22636350887
- **Notable**: P0 hotfix for production hierarchy warmup (Step 5.3 warm_hierarchy_gaps broken). Recon skipped via cached platform profile. Third release of the day.

### 2026-03-03 (2) — autom8y-asana PATCH release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS
- **Duration**: 11.9 min (chain only)
- **Commit released**: 9606712 — fix(cascade): persist parent_gid to repair hierarchy on S3 resume
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **Chain timing**: test 4m 0s, dispatch 11s, receiver 7m 39s
- **ECS deploy**: Rolling deployment, smoke test passed
- **Run IDs**: test=22634870350, dispatch=22635032893, receiver=22635039337
- **Notable**: Clean PATCH, no blocking issues. Second release of the day.

### 2026-03-03 — autom8y-asana PATCH release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS
- **Duration**: ~2.5 hours (including CI infra fix cross-session)
- **Commits released**: 12 on origin/main (9 feature + 2 CI retry + 1 lint fix)
- **Key commit**: c141e1b (lint fix that unblocked CI)
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **ECS deploy**: Rolling deployment, smoke test passed
- **Blocking issues resolved**:
  - INFRA: Reusable workflow resolution failure (fixed via autom8y-workflows extraction)
  - LINT-001: 22 ruff UP042 StrEnum violations (15 files)
  - TEST-001: 3 entity registry ordering assertions
  - DISPATCH-001: Org secrets visibility (private → all for public repo)
- **Run IDs**: test=22630104172, dispatch=22630885109, receiver=22630902492
- **Notable**: First release after CI migration from autom8y/autom8y to autom8y/autom8y-workflows
